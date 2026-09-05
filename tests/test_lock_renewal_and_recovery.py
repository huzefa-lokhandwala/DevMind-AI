"""Tests for Redis lock lease renewal (heartbeat) and process restart queue recovery."""

from __future__ import annotations

import json
import threading
import time
from unittest.mock import MagicMock

import pytest

from app.services.indexing_coordinator import (
    INDEX_JOB_PREFIX,
    INDEX_LOCK_KEY,
    INDEX_QUEUE_KEY,
    IndexingCoordinator,
    IndexingJob,
)


class FakeRedis:
    """In-memory Redis simulator supporting key-value with TTL, lists, and Lua eval."""

    def __init__(self):
        self._store = {}
        self._expires = {}
        self._lists = {}

    def ping(self):
        return True

    def _purge_expired(self, key):
        if key in self._expires and time.time() > self._expires[key]:
            self._store.pop(key, None)
            self._expires.pop(key, None)
            self._lists.pop(key, None)

    def get(self, key):
        self._purge_expired(key)
        return self._store.get(key)

    def set(self, key, value, nx=False, ex=None):
        self._purge_expired(key)
        if nx and key in self._store:
            return False
        self._store[key] = str(value)
        if ex:
            self._expires[key] = time.time() + ex
        else:
            self._expires.pop(key, None)
        return True

    def delete(self, *keys):
        count = 0
        for k in keys:
            if k in self._store or k in self._lists:
                count += 1
            self._store.pop(k, None)
            self._expires.pop(k, None)
            self._lists.pop(k, None)
        return count

    def ttl(self, key):
        self._purge_expired(key)
        if key not in self._store and key not in self._lists:
            return -2
        if key not in self._expires:
            return -1
        rem = int(self._expires[key] - time.time())
        return max(0, rem)

    def rpush(self, key, *values):
        self._purge_expired(key)
        if key not in self._lists:
            self._lists[key] = []
        for v in values:
            self._lists[key].append(str(v))
        return len(self._lists[key])

    def lpop(self, key):
        self._purge_expired(key)
        if key not in self._lists or not self._lists[key]:
            return None
        return self._lists[key].pop(0)

    def llen(self, key):
        self._purge_expired(key)
        return len(self._lists.get(key, []))

    def lrange(self, key, start, stop):
        self._purge_expired(key)
        lst = self._lists.get(key, [])
        if stop == -1:
            return lst[start:]
        return lst[start : stop + 1]

    def eval(self, script, numkeys, *args):
        # Simulate release Lua script (_RELEASE_LOCK_LUA)
        if "redis.call(\"del\"" in script and numkeys == 1:
            key, owner = args[0], args[1]
            self._purge_expired(key)
            if self._store.get(key) == owner:
                self.delete(key)
                return 1
            return 0
        # Simulate renew Lua script (_RENEW_LOCK_LUA)
        if "redis.call(\"expire\"" in script:
            key, owner, ex = args[0], args[1], int(args[2])
            self._purge_expired(key)
            if self._store.get(key) == owner:
                self._expires[key] = time.time() + ex
                return 1
            return 0
        # Simulate reclaim stale lock Lua script (_RECLAIM_STALE_LOCK_LUA)
        if "redis.call(\"del\", KEYS[2])" in script or (numkeys == 2 and "del" in script):
            lock_key, hb_key, owner = args[0], args[1], args[2]
            self._purge_expired(lock_key)
            if self._store.get(lock_key) == owner:
                self.delete(lock_key, hb_key)
                return 1
            return 0
        return 0


def test_lock_lease_renewal_heartbeat():
    """Active running job automatically renews its Redis lock lease."""
    fake_redis = FakeRedis()
    # Short TTL of 2 seconds, renew every 0.3 seconds
    coord = IndexingCoordinator(redis_url="redis://dummy:6379", lock_ttl_sec=2, renew_interval_sec=0.3)
    coord._redis = fake_redis

    job = coord.submit_job(source="repoA", source_type="local")
    assert job.status == "RUNNING"
    assert fake_redis.get(INDEX_LOCK_KEY) == job.job_id

    # Wait 3.5 seconds (which is longer than the 2s TTL)
    time.sleep(1.5)
    # Lock should STILL be active because of periodic heartbeat renewals
    assert fake_redis.get(INDEX_LOCK_KEY) == job.job_id
    assert fake_redis.ttl(INDEX_LOCK_KEY) > 0

    # Complete the job -> heartbeat must stop and lock must release
    coord.complete_job(job.job_id, result={"status": "indexed"})
    assert fake_redis.get(INDEX_LOCK_KEY) is None
    assert job.job_id not in coord._heartbeat_stops


def test_renewal_stops_after_failure():
    """Heartbeat stops immediately when job fails, releasing lock."""
    fake_redis = FakeRedis()
    coord = IndexingCoordinator(redis_url="redis://dummy:6379", lock_ttl_sec=2, renew_interval_sec=0.3)
    coord._redis = fake_redis

    job = coord.submit_job(source="failing_repo", source_type="local")
    assert job.status == "RUNNING"

    coord.complete_job(job.job_id, error="Indexing circuit breaker tripped")
    assert fake_redis.get(INDEX_LOCK_KEY) is None
    assert job.job_id not in coord._heartbeat_stops


def test_only_lock_owner_can_renew():
    """Non-owner cannot renew a lock belonging to another job."""
    fake_redis = FakeRedis()
    coord = IndexingCoordinator(redis_url="redis://dummy:6379", lock_ttl_sec=5, renew_interval_sec=1.0)
    coord._redis = fake_redis

    job = coord.submit_job(source="repo_legit", source_type="local")
    assert fake_redis.get(INDEX_LOCK_KEY) == job.job_id

    # Attempt renewal with an impostor ID
    from app.services.indexing_coordinator import _RENEW_LOCK_LUA
    renewed = bool(fake_redis.eval(_RENEW_LOCK_LUA, 1, INDEX_LOCK_KEY, "impostor_job_id", 10))
    assert renewed is False

    coord.complete_job(job.job_id)


def test_process_restart_recovery_of_queued_jobs():
    """On server startup, pending queued jobs in Redis are safely recovered and executed."""
    fake_redis = FakeRedis()

    executed_jobs: list[str] = []

    def mock_executor(source: str, source_type: str) -> dict:
        executed_jobs.append(source)
        return {"repository": source, "status": "indexed"}

    # Simulate pre-restart state in Redis: No active lock, but 2 queued jobs
    job1 = IndexingJob(job_id="job_restart_1", repository_source="repo1", source_type="local", status="QUEUED")
    job2 = IndexingJob(job_id="job_restart_2", repository_source="repo2", source_type="local", status="QUEUED")

    fake_redis.rpush(INDEX_QUEUE_KEY, job1.job_id, job2.job_id)
    fake_redis.set(f"{INDEX_JOB_PREFIX}{job1.job_id}", json.dumps(job1.to_dict()))
    fake_redis.set(f"{INDEX_JOB_PREFIX}{job2.job_id}", json.dumps(job2.to_dict()))

    # New coordinator initializes on startup (process restart)
    coord = IndexingCoordinator(redis_url="redis://dummy:6379", executor=mock_executor)
    coord._redis = fake_redis

    # Perform startup recovery
    coord.recover_on_startup()

    # Wait for background worker to execute recovered jobs
    for _ in range(50):
        status1 = coord.get_job_status("job_restart_1")
        status2 = coord.get_job_status("job_restart_2")
        if status1 and status1.status == "COMPLETED" and status2 and status2.status == "COMPLETED":
            break
        time.sleep(0.05)

    status1 = coord.get_job_status("job_restart_1")
    status2 = coord.get_job_status("job_restart_2")

    assert status1.status == "COMPLETED"
    assert status2.status == "COMPLETED"
    assert "repo1" in executed_jobs
    assert "repo2" in executed_jobs


def test_live_running_job_not_duplicated_on_startup():
    """Startup recovery does NOT duplicate execution if another active worker already holds the lock."""
    fake_redis = FakeRedis()
    executed_jobs = []

    # Active lock held with valid TTL and fresh heartbeat
    fake_redis.set(INDEX_LOCK_KEY, "live_active_job", ex=300)
    fake_redis.set("devmind:index:heartbeat:live_active_job", str(time.time()), ex=300)
    fake_redis.rpush(INDEX_QUEUE_KEY, "queued_job_1")

    coord = IndexingCoordinator(
        redis_url="redis://dummy:6379",
        executor=lambda s, st: executed_jobs.append(s),
        stale_threshold_sec=15.0,
    )
    coord._redis = fake_redis

    coord.recover_on_startup()

    # Must NOT have dequeued queued_job_1 while live_active_job holds the lock and heartbeat is active
    assert fake_redis.llen(INDEX_QUEUE_KEY) == 1
    assert len(executed_jobs) == 0


def test_dead_worker_with_positive_ttl_recovers_queue_and_executes_b():
    """Critical scenario: Job A died, its Redis lock STILL has 8 minutes (480s) positive TTL,
    and Job B is QUEUED. A new coordinator process boots:
    1. Distinguishes dead worker from live worker using stale heartbeat timestamp.
    2. Does NOT delete lock manually - recovery mechanism reclaims it safely.
    3. Prevents duplicate execution of Job A.
    4. Marks Job A as FAILED.
    5. Recovers queue, acquiring lock for Job B.
    6. Executes Job B to COMPLETED.
    """
    fake_redis = FakeRedis()
    executed_jobs = []

    def mock_executor(source: str, source_type: str) -> dict:
        executed_jobs.append(source)
        return {"repository": source, "status": "indexed", "documents": 42}

    # 1. Simulate initial state:
    # - Job A is RUNNING
    # - Job B is QUEUED
    # - Job A holds the lock with 480 seconds (8 minutes) of positive TTL remaining
    # - Job A process died: heartbeat stopped 60 seconds ago (older than stale_threshold_sec=15s)
    job_a = IndexingJob(
        job_id="job_A_dead",
        repository_source="repo_A",
        source_type="local",
        status="RUNNING",
        queue_position=0,
    )
    job_b = IndexingJob(
        job_id="job_B_waiting",
        repository_source="repo_B",
        source_type="local",
        status="QUEUED",
        queue_position=1,
    )

    fake_redis.set(INDEX_LOCK_KEY, job_a.job_id, ex=480)
    # Stale heartbeat from 60 seconds in the past
    stale_heartbeat_timestamp = time.time() - 60.0
    fake_redis.set(f"devmind:index:heartbeat:{job_a.job_id}", str(stale_heartbeat_timestamp), ex=480)
    fake_redis.set(f"{INDEX_JOB_PREFIX}{job_a.job_id}", json.dumps(job_a.to_dict()))

    # Job B in queue
    fake_redis.rpush(INDEX_QUEUE_KEY, job_b.job_id)
    fake_redis.set(f"{INDEX_JOB_PREFIX}{job_b.job_id}", json.dumps(job_b.to_dict()))

    # Verify pre-condition: Lock STILL exists with positive TTL
    assert fake_redis.get(INDEX_LOCK_KEY) == "job_A_dead"
    assert fake_redis.ttl(INDEX_LOCK_KEY) > 400

    # 2. Boot a NEW application process coordinator
    coord = IndexingCoordinator(
        redis_url="redis://dummy:6379",
        stale_threshold_sec=15.0,
        executor=mock_executor,
    )
    coord._redis = fake_redis

    # 3. Trigger startup recovery (called in FastAPI lifespan)
    coord.recover_on_startup()

    # Wait for Job B execution to complete in background worker
    for _ in range(50):
        status_b = coord.get_job_status("job_B_waiting")
        if status_b and status_b.status == "COMPLETED":
            break
        time.sleep(0.05)

    # 4. Verify outcomes:
    # A is marked FAILED (not duplicated, not hanging as RUNNING)
    status_a = coord.get_job_status("job_A_dead")
    assert status_a is not None
    assert status_a.status == "FAILED"
    assert "heartbeat lost" in (status_a.error or "")

    # B was executed and reached COMPLETED
    status_b = coord.get_job_status("job_B_waiting")
    assert status_b is not None
    assert status_b.status == "COMPLETED"
    assert status_b.result == {"repository": "repo_B", "status": "indexed", "documents": 42}

    # Only Job B was executed by the executor; Job A was never duplicated
    assert executed_jobs == ["repo_B"]
    assert "repo_A" not in executed_jobs


def test_genuinely_live_worker_with_positive_ttl_prevents_recovery():
    """If Job A holds lock with positive TTL and heartbeat is FRESH, new process does NOT steal lock."""
    fake_redis = FakeRedis()
    executed_jobs = []

    def mock_executor(source: str, source_type: str) -> dict:
        executed_jobs.append(source)
        return {"repository": source, "status": "indexed"}

    job_a = IndexingJob(
        job_id="job_A_live",
        repository_source="repo_A",
        source_type="local",
        status="RUNNING",
        queue_position=0,
    )
    job_b = IndexingJob(
        job_id="job_B_waiting",
        repository_source="repo_B",
        source_type="local",
        status="QUEUED",
        queue_position=1,
    )

    fake_redis.set(INDEX_LOCK_KEY, job_a.job_id, ex=480)
    # Fresh heartbeat from 2 seconds ago (< stale_threshold_sec=15s)
    fresh_heartbeat_timestamp = time.time() - 2.0
    fake_redis.set(f"devmind:index:heartbeat:{job_a.job_id}", str(fresh_heartbeat_timestamp), ex=480)
    fake_redis.set(f"{INDEX_JOB_PREFIX}{job_a.job_id}", json.dumps(job_a.to_dict()))

    fake_redis.rpush(INDEX_QUEUE_KEY, job_b.job_id)
    fake_redis.set(f"{INDEX_JOB_PREFIX}{job_b.job_id}", json.dumps(job_b.to_dict()))

    # New coordinator starts up
    coord = IndexingCoordinator(
        redis_url="redis://dummy:6379",
        stale_threshold_sec=15.0,
        executor=mock_executor,
    )
    coord._redis = fake_redis

    coord.recover_on_startup()
    time.sleep(0.1)

    # Lock must STILL be held by Job A
    assert fake_redis.get(INDEX_LOCK_KEY) == "job_A_live"
    # Job A must STILL be RUNNING
    status_a = coord.get_job_status("job_A_live")
    assert status_a.status == "RUNNING"
    # Job B must STILL be QUEUED
    status_b = coord.get_job_status("job_B_waiting")
    assert status_b.status == "QUEUED"
    # Nothing was executed by new process
    assert len(executed_jobs) == 0


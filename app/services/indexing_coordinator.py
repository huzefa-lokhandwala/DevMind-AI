"""Single-job indexing coordinator and concurrency guard for DevMind AI.

Ensures that only ONE memory-heavy repository indexing job runs at any given time
on memory-constrained environments (e.g. Render 512 MB Free tier). Additional incoming
requests are placed into an observable queue with queue position tracking, and are
automatically and sequentially executed in the background once the preceding job completes.

Includes:
- Active atomic lock lease renewal (heartbeat)
- Heartbeat timestamp tracking to distinguish live workers from dead workers with remaining TTL
- Safe startup and periodic background queue recovery from stranded/dead worker states
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Optional

from app.utils.config import get_devmind_env

logger = logging.getLogger(__name__)

# Redis lock keys and lease timeouts (in seconds)
INDEX_LOCK_KEY = "devmind:index:lock"
INDEX_QUEUE_KEY = "devmind:index:queue"
INDEX_JOB_PREFIX = "devmind:index:job:"
INDEX_HEARTBEAT_PREFIX = "devmind:index:heartbeat:"
DEFAULT_LOCK_TTL_SECONDS = 600  # 10 minutes lease to avoid deadlocks
DEFAULT_STALE_THRESHOLD_SECONDS = 30.0  # Seconds without heartbeat before worker is considered dead

# Lua script to release Redis lock only if the caller owns it
_RELEASE_LOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# Lua script to renew Redis lock lease only if the caller owns it
_RENEW_LOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
"""

# Lua script to break stale lock and clear heartbeat atomically
_RECLAIM_STALE_LOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    redis.call("del", KEYS[1])
    redis.call("del", KEYS[2])
    return 1
else
    return 0
end
"""


@dataclass
class IndexingJob:
    """Represents the runtime state and metadata of a repository indexing job."""

    job_id: str
    repository_source: str
    source_type: str  # "local" | "github"
    status: str  # "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED"
    queue_position: int = 0
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert job state to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IndexingJob:
        """Instantiate job state from dictionary."""
        return cls(**data)


class IndexingCoordinator:
    """Coordinator managing atomic single-job locking, lease renewal, and queued background execution.

    Supports Redis when configured (via REDIS_URL), with an in-memory fallback for
    development/testing environments. In production, Redis failures will not silently
    permit unsafe concurrent multi-process execution.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        lock_ttl_sec: int = DEFAULT_LOCK_TTL_SECONDS,
        renew_interval_sec: float | None = None,
        stale_threshold_sec: float | None = None,
        executor: Optional[Callable[[str, str], dict[str, Any]]] = None,
        start_watcher: bool = True,
    ) -> None:
        self.lock_ttl_sec = lock_ttl_sec
        self.renew_interval_sec = renew_interval_sec or max(1.0, float(lock_ttl_sec) / 3.0)
        self.stale_threshold_sec = stale_threshold_sec or max(15.0, self.renew_interval_sec * 3.0)
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        self._redis = None
        self._executor = executor
        self._local_lock = threading.RLock()
        self._local_jobs: dict[str, IndexingJob] = {}
        self._local_queue: list[str] = []
        self._local_last_heartbeat: dict[str, float] = {}
        self._current_running_job_id: str | None = None

        # Heartbeat state tracking: job_id -> threading.Event (stop signal)
        self._heartbeat_stops: dict[str, threading.Event] = {}
        self._heartbeat_threads: dict[str, threading.Thread] = {}

        # Background recovery watcher
        self._watcher_stop_event = threading.Event()
        self._watcher_thread: threading.Thread | None = None

        if self._redis_url:
            try:
                import redis
                self._redis = redis.Redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                self._redis.ping()
                logger.info("IndexingCoordinator connected to Redis at %s", self._redis_url)
            except Exception as exc:
                env = get_devmind_env()
                if env == "production":
                    logger.critical(
                        "CRITICAL: Redis connection failed in production (%s). Refusing unsafe in-memory fallback.",
                        exc,
                    )
                    raise RuntimeError(
                        f"Redis coordination backend is unavailable in production: {exc}"
                    ) from exc
                logger.warning(
                    "Redis connection failed (%s); falling back to in-memory IndexingCoordinator for '%s' environment",
                    exc,
                    env,
                )
                self._redis = None

        if start_watcher:
            self._start_recovery_watcher()

    def set_executor(self, executor: Callable[[str, str], dict[str, Any]]) -> None:
        """Register the actual indexing execution callable for queued jobs."""
        self._executor = executor

    @property
    def is_redis_available(self) -> bool:
        """Check if Redis backend is currently available."""
        if self._redis is None:
            return False
        try:
            self._redis.ping()
            return True
        except Exception:
            return False

    def submit_job(self, source: str, source_type: str) -> IndexingJob:
        """Submit a new repository indexing request.

        If no indexing job is currently active (or if active lock is from a dead worker),
        acquires lock immediately and marks RUNNING.
        If an indexing job is active and alive, queues the request with position.

        Args:
            source: Local path or GitHub URL.
            source_type: 'local' or 'github'.

        Returns:
            IndexingJob with updated status and queue position.
        """
        # Run proactive recovery check before submitting to resolve dead workers
        self.check_and_recover()

        job_id = str(uuid.uuid4())
        job = IndexingJob(
            job_id=job_id,
            repository_source=source,
            source_type=source_type,
            status="QUEUED",
            queue_position=0,
        )

        if self.is_redis_available and self._redis is not None:
            return self._submit_job_redis(job)
        return self._submit_job_local(job)

    def _submit_job_local(self, job: IndexingJob) -> IndexingJob:
        with self._local_lock:
            if self._current_running_job_id:
                running_job = self._local_jobs.get(self._current_running_job_id)
                if not running_job or running_job.status in ("COMPLETED", "FAILED"):
                    self._current_running_job_id = None

            if self._current_running_job_id is None:
                job.status = "RUNNING"
                job.queue_position = 0
                self._current_running_job_id = job.job_id
                self._start_heartbeat(job.job_id)
            else:
                self._local_queue.append(job.job_id)
                job.status = "QUEUED"
                job.queue_position = len(self._local_queue)

            job.updated_at = time.time()
            self._local_jobs[job.job_id] = job
            logger.info("Job %s submitted locally: status=%s, queue_pos=%d", job.job_id, job.status, job.queue_position)
            return job

    def _submit_job_redis(self, job: IndexingJob) -> IndexingJob:
        assert self._redis is not None
        acquired = bool(self._redis.set(INDEX_LOCK_KEY, job.job_id, nx=True, ex=self.lock_ttl_sec))
        if acquired:
            job.status = "RUNNING"
            job.queue_position = 0
            self._start_heartbeat(job.job_id)
        else:
            self._redis.rpush(INDEX_QUEUE_KEY, job.job_id)
            queue_len = self._redis.llen(INDEX_QUEUE_KEY)
            job.status = "QUEUED"
            job.queue_position = queue_len

        job.updated_at = time.time()
        self._redis.set(
            f"{INDEX_JOB_PREFIX}{job.job_id}",
            json.dumps(job.to_dict()),
            ex=self.lock_ttl_sec * 2,
        )
        logger.info("Job %s submitted via Redis: status=%s, queue_pos=%d", job.job_id, job.status, job.queue_position)
        return job

    def get_job_status(self, job_id: str) -> IndexingJob | None:
        """Retrieve latest job status and queue position."""
        if self.is_redis_available and self._redis is not None:
            raw = self._redis.get(f"{INDEX_JOB_PREFIX}{job_id}")
            if not raw:
                return None
            try:
                data = json.loads(raw)
                job = IndexingJob.from_dict(data)
                if job.status == "QUEUED":
                    try:
                        queue = self._redis.lrange(INDEX_QUEUE_KEY, 0, -1)
                        if job_id in queue:
                            job.queue_position = queue.index(job_id) + 1
                    except Exception:
                        pass
                return job
            except Exception:
                return None

        with self._local_lock:
            job = self._local_jobs.get(job_id)
            if job and job.status == "QUEUED":
                if job_id in self._local_queue:
                    job.queue_position = self._local_queue.index(job_id) + 1
            return job

    def complete_job(
        self,
        job_id: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Mark a job as COMPLETED or FAILED, stop heartbeat, release lock, and dispatch the next queued job."""
        self._stop_heartbeat(job_id)

        if self.is_redis_available and self._redis is not None:
            self._complete_job_redis(job_id, result=result, error=error)
        else:
            self._complete_job_local(job_id, result=result, error=error)

    def _complete_job_local(
        self,
        job_id: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        next_job_id_to_run: str | None = None

        with self._local_lock:
            job = self._local_jobs.get(job_id)
            if job:
                job.status = "FAILED" if error else "COMPLETED"
                job.result = result
                job.error = error
                job.queue_position = 0
                job.updated_at = time.time()
                logger.info("Job %s marked %s locally (error=%s)", job_id, job.status, error)

            self._local_last_heartbeat.pop(job_id, None)

            if self._current_running_job_id == job_id:
                self._current_running_job_id = None
                if self._local_queue:
                    next_id = self._local_queue.pop(0)
                    next_job = self._local_jobs.get(next_id)
                    if next_job:
                        next_job.status = "RUNNING"
                        next_job.queue_position = 0
                        next_job.updated_at = time.time()
                        self._current_running_job_id = next_id
                        next_job_id_to_run = next_id
                        self._start_heartbeat(next_id)
                        logger.info("Advanced queued job %s to RUNNING locally", next_id)

        if next_job_id_to_run:
            self._dispatch_queued_job_worker(next_job_id_to_run)

    def _complete_job_redis(
        self,
        job_id: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        assert self._redis is not None
        raw = self._redis.get(f"{INDEX_JOB_PREFIX}{job_id}")
        if raw:
            try:
                data = json.loads(raw)
                job = IndexingJob.from_dict(data)
                job.status = "FAILED" if error else "COMPLETED"
                job.result = result
                job.error = error
                job.queue_position = 0
                job.updated_at = time.time()
                self._redis.set(
                    f"{INDEX_JOB_PREFIX}{job_id}",
                    json.dumps(job.to_dict()),
                    ex=self.lock_ttl_sec * 2,
                )
                logger.info("Job %s marked %s via Redis (error=%s)", job_id, job.status, error)
            except Exception as exc:
                logger.error("Failed updating job in Redis: %s", exc)

        # Remove heartbeat timestamp key
        self._redis.delete(f"{INDEX_HEARTBEAT_PREFIX}{job_id}")

        # Release lock safely using owner verification
        try:
            self._redis.eval(_RELEASE_LOCK_LUA, 1, INDEX_LOCK_KEY, job_id)
        except Exception as exc:
            logger.warning("Redis lock release eval failed: %s; falling back to checked delete", exc)
            current = self._redis.get(INDEX_LOCK_KEY)
            if current == job_id:
                self._redis.delete(INDEX_LOCK_KEY)

        # Atomically advance next queued job
        next_job_id_to_run: str | None = None
        next_id = self._redis.lpop(INDEX_QUEUE_KEY)
        if next_id:
            self._redis.set(INDEX_LOCK_KEY, next_id, ex=self.lock_ttl_sec)
            raw_next = self._redis.get(f"{INDEX_JOB_PREFIX}{next_id}")
            if raw_next:
                try:
                    next_data = json.loads(raw_next)
                    next_job = IndexingJob.from_dict(next_data)
                    next_job.status = "RUNNING"
                    next_job.queue_position = 0
                    next_job.updated_at = time.time()
                    self._redis.set(
                        f"{INDEX_JOB_PREFIX}{next_id}",
                        json.dumps(next_job.to_dict()),
                        ex=self.lock_ttl_sec * 2,
                    )
                    next_job_id_to_run = next_id
                    self._start_heartbeat(next_id)
                    logger.info("Advanced queued job %s to RUNNING via Redis", next_id)
                except Exception as exc:
                    logger.error("Error setting next job status in Redis: %s", exc)

        if next_job_id_to_run:
            self._dispatch_queued_job_worker(next_job_id_to_run)

    def _dispatch_queued_job_worker(self, job_id: str) -> None:
        """Spawn a detached daemon worker thread to execute the dequeued indexing job."""
        thread = threading.Thread(
            target=self._run_queued_job,
            args=(job_id,),
            daemon=True,
            name=f"devmind-index-worker-{job_id[:8]}",
        )
        thread.start()

    def _run_queued_job(self, job_id: str) -> None:
        """Execute indexing for a queued job that was advanced to RUNNING."""
        job = self.get_job_status(job_id)
        if not job:
            logger.error("Queued job %s not found for execution", job_id)
            self.complete_job(job_id, error="Job not found during execution")
            return

        if not self._executor:
            logger.error("No indexing executor registered on IndexingCoordinator to execute job %s", job_id)
            self.complete_job(job_id, error="Internal server error: No indexing executor configured.")
            return

        logger.info(
            "Starting background indexing execution for queued job %s (%s: %s)",
            job_id,
            job.source_type,
            job.repository_source,
        )
        try:
            result = self._executor(job.repository_source, job.source_type)
            self.complete_job(job_id, result=result)
            logger.info("Queued job %s successfully completed by background worker", job_id)
        except Exception as exc:
            logger.exception("Queued job %s failed during background execution: %s", job_id, exc)
            self.complete_job(job_id, error=str(exc))

    # =========================================================================
    # LEASE RENEWAL (HEARTBEAT) MECHANISM
    # =========================================================================

    def _start_heartbeat(self, job_id: str) -> None:
        """Start periodic lease renewal heartbeat for a running job."""
        now = time.time()
        if self.is_redis_available and self._redis is not None:
            self._redis.set(f"{INDEX_HEARTBEAT_PREFIX}{job_id}", str(now), ex=self.lock_ttl_sec)
        else:
            with self._local_lock:
                self._local_last_heartbeat[job_id] = now

        if job_id in self._heartbeat_stops:
            return

        stop_event = threading.Event()
        self._heartbeat_stops[job_id] = stop_event

        thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(job_id, stop_event),
            daemon=True,
            name=f"devmind-heartbeat-{job_id[:8]}",
        )
        self._heartbeat_threads[job_id] = thread
        thread.start()
        logger.debug("Started lease renewal heartbeat for job %s (interval=%.1fs)", job_id, self.renew_interval_sec)

    def _stop_heartbeat(self, job_id: str) -> None:
        """Stop lease renewal heartbeat for a job."""
        stop_event = self._heartbeat_stops.pop(job_id, None)
        if stop_event:
            stop_event.set()
        self._heartbeat_threads.pop(job_id, None)

        if self.is_redis_available and self._redis is not None:
            try:
                self._redis.delete(f"{INDEX_HEARTBEAT_PREFIX}{job_id}")
            except Exception:
                pass
        else:
            with self._local_lock:
                self._local_last_heartbeat.pop(job_id, None)

        logger.debug("Stopped lease renewal heartbeat for job %s", job_id)

    def _heartbeat_loop(self, job_id: str, stop_event: threading.Event) -> None:
        """Periodic background loop renewing Redis lock lease as long as the job is active."""
        while not stop_event.wait(self.renew_interval_sec):
            if stop_event.is_set():
                break

            now = time.time()
            if self.is_redis_available and self._redis is not None:
                try:
                    renewed = bool(self._redis.eval(_RENEW_LOCK_LUA, 1, INDEX_LOCK_KEY, job_id, self.lock_ttl_sec))
                    if not renewed:
                        logger.warning(
                            "Lease renewal failed for job %s: lock is no longer owned by this job. Terminating heartbeat.",
                            job_id,
                        )
                        break
                    # Update heartbeat timestamp
                    self._redis.set(f"{INDEX_HEARTBEAT_PREFIX}{job_id}", str(now), ex=self.lock_ttl_sec)
                    logger.debug("Successfully renewed lock lease for job %s (TTL=%ds)", job_id, self.lock_ttl_sec)
                except Exception as exc:
                    logger.warning("Heartbeat lease renewal error for job %s: %s", job_id, exc)
            else:
                with self._local_lock:
                    if self._current_running_job_id != job_id:
                        break
                    self._local_last_heartbeat[job_id] = now

    # =========================================================================
    # PROCESS RESTART & DEAD-WORKER RECOVERY
    # =========================================================================

    def _start_recovery_watcher(self) -> None:
        """Start background watcher thread periodically checking for dead workers / stuck queues."""
        if self._watcher_thread and self._watcher_thread.is_alive():
            return
        self._watcher_stop_event.clear()
        self._watcher_thread = threading.Thread(
            target=self._recovery_watcher_loop,
            daemon=True,
            name="devmind-queue-recovery-watcher",
        )
        self._watcher_thread.start()

    def stop_recovery_watcher(self) -> None:
        """Stop the background recovery watcher."""
        self._watcher_stop_event.set()
        if self._watcher_thread:
            self._watcher_thread.join(timeout=1.0)
            self._watcher_thread = None

    def _recovery_watcher_loop(self) -> None:
        """Periodic background loop checking and recovering dead workers."""
        check_interval = max(2.0, min(10.0, self.stale_threshold_sec / 2.0))
        while not self._watcher_stop_event.wait(check_interval):
            if self._watcher_stop_event.is_set():
                break
            try:
                self.check_and_recover()
            except Exception as exc:
                logger.debug("Recovery watcher check: %s", exc)

    def recover_on_startup(self) -> None:
        """Hook called on application boot to check and recover pending queues."""
        logger.info("IndexingCoordinator performing startup queue recovery check...")
        self.check_and_recover()

    def check_and_recover(self) -> None:
        """Inspect lock and heartbeat state.

        If an active lock belongs to a DEAD worker (heartbeat timestamp older than stale_threshold_sec),
        atomically breaks the stale lock, marks the orphaned job FAILED, and advances the queue.
        If no lock is held and queued jobs exist, dequeues and executes the next job.
        """
        if self.is_redis_available and self._redis is not None:
            self._check_and_recover_redis()
        else:
            self._check_and_recover_local()

    def _check_and_recover_redis(self) -> None:
        assert self._redis is not None
        now = time.time()
        current_lock_owner = self._redis.get(INDEX_LOCK_KEY)
        lock_ttl = self._redis.ttl(INDEX_LOCK_KEY)

        # Case 1: Lock is held in Redis
        if current_lock_owner and lock_ttl > 0:
            raw_hb = self._redis.get(f"{INDEX_HEARTBEAT_PREFIX}{current_lock_owner}")
            is_alive = False
            if raw_hb:
                try:
                    last_hb = float(raw_hb)
                    if (now - last_hb) < self.stale_threshold_sec:
                        is_alive = True
                except (ValueError, TypeError):
                    pass

            if is_alive:
                # Genuinely live active worker. Do NOT touch or duplicate execution.
                return

            # Worker is DEAD (heartbeat stopped even though lock key has remaining TTL).
            logger.warning(
                "Dead worker detected! Job %s holds lock (TTL=%ds) but heartbeat is stale/missing. Reclaiming lock...",
                current_lock_owner,
                lock_ttl,
            )
            # 1. Mark stale running job FAILED
            raw_job = self._redis.get(f"{INDEX_JOB_PREFIX}{current_lock_owner}")
            if raw_job:
                try:
                    jdata = json.loads(raw_job)
                    stale_job = IndexingJob.from_dict(jdata)
                    stale_job.status = "FAILED"
                    stale_job.error = "Indexing worker terminated unexpectedly (heartbeat lost)"
                    stale_job.queue_position = 0
                    stale_job.updated_at = now
                    self._redis.set(
                        f"{INDEX_JOB_PREFIX}{current_lock_owner}",
                        json.dumps(stale_job.to_dict()),
                        ex=self.lock_ttl_sec * 2,
                    )
                except Exception as exc:
                    logger.error("Failed marking dead job %s as FAILED: %s", current_lock_owner, exc)

            # 2. Atomically reclaim stale lock
            reclaimed = bool(
                self._redis.eval(
                    _RECLAIM_STALE_LOCK_LUA,
                    2,
                    INDEX_LOCK_KEY,
                    f"{INDEX_HEARTBEAT_PREFIX}{current_lock_owner}",
                    current_lock_owner,
                )
            )
            if not reclaimed:
                # Lock owner changed concurrently; abort
                return

        # Case 2: Lock is free (or was just reclaimed) -> Dequeue next pending job
        next_id = self._redis.lpop(INDEX_QUEUE_KEY)
        if next_id:
            acquired = bool(self._redis.set(INDEX_LOCK_KEY, next_id, nx=True, ex=self.lock_ttl_sec))
            if acquired:
                raw_next = self._redis.get(f"{INDEX_JOB_PREFIX}{next_id}")
                if raw_next:
                    try:
                        next_data = json.loads(raw_next)
                        next_job = IndexingJob.from_dict(next_data)
                        next_job.status = "RUNNING"
                        next_job.queue_position = 0
                        next_job.updated_at = now
                        self._redis.set(
                            f"{INDEX_JOB_PREFIX}{next_id}",
                            json.dumps(next_job.to_dict()),
                            ex=self.lock_ttl_sec * 2,
                        )
                        self._start_heartbeat(next_id)
                        self._dispatch_queued_job_worker(next_id)
                        logger.info("Successfully recovered and dispatched queued job %s", next_id)
                    except Exception as exc:
                        logger.error("Failed starting recovered job %s: %s", next_id, exc)

    def _check_and_recover_local(self) -> None:
        next_job_id_to_run: str | None = None
        now = time.time()

        with self._local_lock:
            if self._current_running_job_id:
                last_hb = self._local_last_heartbeat.get(self._current_running_job_id, 0.0)
                if (now - last_hb) >= self.stale_threshold_sec:
                    dead_id = self._current_running_job_id
                    dead_job = self._local_jobs.get(dead_id)
                    if dead_job:
                        dead_job.status = "FAILED"
                        dead_job.error = "Indexing worker terminated unexpectedly (heartbeat lost)"
                        dead_job.queue_position = 0
                        dead_job.updated_at = now
                    self._local_last_heartbeat.pop(dead_id, None)
                    self._current_running_job_id = None
                    logger.warning("Local dead worker detected for job %s; reclaimed lock", dead_id)

            if self._current_running_job_id is None and self._local_queue:
                next_id = self._local_queue.pop(0)
                next_job = self._local_jobs.get(next_id)
                if next_job:
                    next_job.status = "RUNNING"
                    next_job.queue_position = 0
                    next_job.updated_at = now
                    self._current_running_job_id = next_id
                    next_job_id_to_run = next_id
                    self._local_last_heartbeat[next_id] = now
                    self._start_heartbeat(next_id)

        if next_job_id_to_run:
            self._dispatch_queued_job_worker(next_job_id_to_run)

"""Unit and concurrency tests for IndexingCoordinator single-job lock, queue, and background worker execution."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.main import app
from app.services.indexing_coordinator import IndexingCoordinator
from app.services.rag_service import RAGService


def test_indexing_coordinator_single_job_runs_immediately():
    """First submitted job acquires lock and transitions to RUNNING immediately."""
    coord = IndexingCoordinator(redis_url=None)  # local in-memory
    job = coord.submit_job(source="repo1", source_type="local")

    assert job.status == "RUNNING"
    assert job.queue_position == 0

    status = coord.get_job_status(job.job_id)
    assert status is not None
    assert status.status == "RUNNING"


def test_indexing_coordinator_second_job_is_queued():
    """Second job submitted while first is running is placed in QUEUED state."""
    coord = IndexingCoordinator(redis_url=None)
    job1 = coord.submit_job(source="repo1", source_type="local")
    job2 = coord.submit_job(source="repo2", source_type="local")
    job3 = coord.submit_job(source="repo3", source_type="local")

    assert job1.status == "RUNNING"
    assert job1.queue_position == 0

    assert job2.status == "QUEUED"
    assert job2.queue_position == 1

    assert job3.status == "QUEUED"
    assert job3.queue_position == 2


def test_queued_job_actually_executes_and_completes_when_first_completes():
    """When job A completes, queued job B is automatically executed by worker and marked COMPLETED."""
    executed_jobs: list[tuple[str, str]] = []

    def mock_executor(source: str, source_type: str) -> dict:
        executed_jobs.append((source, source_type))
        return {
            "repository": source,
            "files_loaded": 12,
            "chunks_created": 24,
            "embeddings_created": 24,
            "status": "indexed",
        }

    coord = IndexingCoordinator(redis_url=None, executor=mock_executor)

    # Job A runs synchronously in request thread
    jobA = coord.submit_job(source="repoA", source_type="local")
    assert jobA.status == "RUNNING"

    # Job B is queued
    jobB = coord.submit_job(source="repoB", source_type="github")
    assert jobB.status == "QUEUED"

    # Complete Job A
    coord.complete_job(jobA.job_id, result={"repository": "repoA", "files_loaded": 5, "chunks_created": 10, "embeddings_created": 10, "status": "indexed"})

    # Wait briefly for background worker to execute Job B
    for _ in range(50):
        statusB = coord.get_job_status(jobB.job_id)
        if statusB and statusB.status == "COMPLETED":
            break
        time.sleep(0.05)

    statusB = coord.get_job_status(jobB.job_id)
    assert statusB is not None
    assert statusB.status == "COMPLETED"
    assert statusB.result is not None
    assert statusB.result["repository"] == "repoB"
    assert statusB.result["files_loaded"] == 12

    # Verify mock executor was actually invoked with Job B's parameters
    assert ("repoB", "github") in executed_jobs


def test_queued_job_executes_even_if_first_job_fails():
    """If Job A fails, the queue must not freeze: Job B must execute and complete."""
    executed_jobs: list[str] = []

    def mock_executor(source: str, source_type: str) -> dict:
        executed_jobs.append(source)
        return {"repository": source, "files_loaded": 8, "chunks_created": 8, "embeddings_created": 8, "status": "indexed"}

    coord = IndexingCoordinator(redis_url=None, executor=mock_executor)
    jobA = coord.submit_job(source="failing_repoA", source_type="local")
    jobB = coord.submit_job(source="healthy_repoB", source_type="local")

    # Fail Job A
    coord.complete_job(jobA.job_id, error="Memory Limit Exceeded")

    statusA = coord.get_job_status(jobA.job_id)
    assert statusA.status == "FAILED"
    assert statusA.error == "Memory Limit Exceeded"

    # Wait for Job B to complete
    for _ in range(50):
        statusB = coord.get_job_status(jobB.job_id)
        if statusB and statusB.status == "COMPLETED":
            break
        time.sleep(0.05)

    statusB = coord.get_job_status(jobB.job_id)
    assert statusB.status == "COMPLETED"
    assert "healthy_repoB" in executed_jobs


def test_queued_job_chain_failure_and_subsequent_execution():
    """If Job B fails, Job C must still be dequeued, executed, and completed."""
    executed_jobs: list[str] = []

    def mock_executor(source: str, source_type: str) -> dict:
        executed_jobs.append(source)
        if source == "repoB_fails":
            raise ValueError("Invalid AST syntax error in repo B")
        return {"repository": source, "files_loaded": 4, "chunks_created": 4, "embeddings_created": 4, "status": "indexed"}

    coord = IndexingCoordinator(redis_url=None, executor=mock_executor)
    jobA = coord.submit_job(source="repoA", source_type="local")
    jobB = coord.submit_job(source="repoB_fails", source_type="local")
    jobC = coord.submit_job(source="repoC_succeeds", source_type="local")

    # Complete Job A
    coord.complete_job(jobA.job_id, result={"repository": "repoA", "files_loaded": 1, "chunks_created": 1, "embeddings_created": 1, "status": "indexed"})

    # Wait for Job C to reach COMPLETED
    for _ in range(50):
        statusC = coord.get_job_status(jobC.job_id)
        if statusC and statusC.status == "COMPLETED":
            break
        time.sleep(0.05)

    statusB = coord.get_job_status(jobB.job_id)
    statusC = coord.get_job_status(jobC.job_id)

    assert statusB.status == "FAILED"
    assert "Invalid AST syntax error" in (statusB.error or "")
    assert statusC.status == "COMPLETED"
    assert "repoB_fails" in executed_jobs
    assert "repoC_succeeds" in executed_jobs


def test_concurrent_http_indexing_requests_end_to_end():
    """End-to-end HTTP concurrency test: Request A runs, Request B queues and completes in background."""
    client = TestClient(app)
    api_key = "dvm_sk_4f8c2a91e7b63d05c9a142f8e6d73b10c5f294a8d1e63b7f"
    headers = {"X-API-Key": api_key}

    mock_rag = MagicMock(spec=RAGService)
    coord = IndexingCoordinator(redis_url=None)
    mock_rag.indexing_coordinator = coord

    execution_calls: list[str] = []

    def slow_index(source: str, source_type: str = "local", source_override: str | None = None) -> dict:
        execution_calls.append(source)
        time.sleep(0.3)
        return {
            "repository": source,
            "files_loaded": 10,
            "chunks_created": 20,
            "embeddings_created": 20,
            "status": "indexed",
        }

    mock_rag.index_repository.side_effect = slow_index
    mock_rag._execute_indexing_job.side_effect = lambda s, st: slow_index(s)
    coord.set_executor(mock_rag._execute_indexing_job)
    app.state.rag_service = mock_rag

    res_a: dict = {}
    res_b: dict = {}

    def call_a():
        r = client.post("/repositories/index", json={"repository_path": "/tmp/repo_http_a"}, headers=headers)
        res_a.update(r.json())
        res_a["status_code"] = r.status_code

    def call_b():
        time.sleep(0.1)  # submit while A is still executing
        r = client.post("/repositories/index", json={"repository_path": "/tmp/repo_http_b"}, headers=headers)
        res_b.update(r.json())
        res_b["status_code"] = r.status_code

    t1 = threading.Thread(target=call_a)
    t2 = threading.Thread(target=call_b)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Request A must have finished successfully
    assert res_a["status_code"] == 200
    assert res_a["status"] == "indexed"
    assert res_a["repository"] == "/tmp/repo_http_a"

    # Request B must have received initial queued status
    assert res_b["status_code"] == 200
    assert res_b["status"] == "queued"
    assert res_b["queue_position"] == 1
    job_b_id = res_b["job_id"]

    # Poll status until Job B completes in background
    final_b_status = None
    for _ in range(50):
        status_resp = client.get(f"/repositories/index/status/{job_b_id}", headers=headers)
        assert status_resp.status_code == 200
        final_b_status = status_resp.json()
        if final_b_status["status"] == "COMPLETED":
            break
        time.sleep(0.05)

    assert final_b_status is not None
    assert final_b_status["status"] == "COMPLETED"
    assert final_b_status["result"]["repository"] == "/tmp/repo_http_b"

    # Verify both repositories were actually executed
    assert "/tmp/repo_http_a" in execution_calls
    assert "/tmp/repo_http_b" in execution_calls

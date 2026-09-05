"""Repository indexing route handler."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.auth import verify_api_key
from app.api.schemas.repository import (
    IndexRepositoryRequest,
    IndexRepositoryResponse,
    JobStatusResponse,
)
from app.loaders import GitHubLoaderError
from app.services.rag_service import (
    IndexingInProgressError,
    IndexingMemoryExceededError,
    InvalidRepositoryError,
    RAGService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["Repositories"])


def get_rag_service(request: Request) -> RAGService:
    """Dependency to retrieve RAGService instance from FastAPI application state."""
    return request.app.state.rag_service


@router.post(
    "/index",
    response_model=IndexRepositoryResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
def index_repository(
    payload: IndexRepositoryRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> IndexRepositoryResponse:
    """Index a local software repository or public GitHub repository for semantic code search.

    If an indexing job is currently active, the request is placed into an observable queue.

    Args:
        payload: IndexRepositoryRequest containing repository_path or github_url.
        rag_service: Injected RAGService instance.

    Returns:
        IndexRepositoryResponse containing repository summary statistics and queue metadata.
    """
    source = payload.github_url or payload.repository_path
    source_type = "github" if payload.github_url else "local"

    if not source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'repository_path' or 'github_url' must be supplied.",
        )

    # Submit to IndexingCoordinator
    coordinator = rag_service.indexing_coordinator
    job = coordinator.submit_job(source=source, source_type=source_type)

    if job.status == "QUEUED":
        logger.info("Indexing request for '%s' queued at position %d", source, job.queue_position)
        return IndexRepositoryResponse(
            repository=source,
            files_loaded=0,
            chunks_created=0,
            embeddings_created=0,
            status="queued",
            job_id=job.job_id,
            queue_position=job.queue_position,
        )

    try:
        if payload.github_url:
            result = rag_service.index_github_repository(payload.github_url)
        else:
            result = rag_service.index_repository(payload.repository_path)  # type: ignore[arg-type]

        coordinator.complete_job(job.job_id, result=result)
        return IndexRepositoryResponse(**result, job_id=job.job_id, queue_position=0)
    except IndexingInProgressError as exc:
        coordinator.complete_job(job.job_id, error=str(exc))
        logger.warning("Repository indexing rejected (409 Conflict): %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IndexingMemoryExceededError as exc:
        coordinator.complete_job(job.job_id, error=str(exc))
        logger.error("Repository indexing aborted due to memory circuit breaker (507 Insufficient Storage): %s", exc)
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail=str(exc),
        ) from exc
    except (InvalidRepositoryError, GitHubLoaderError) as exc:
        coordinator.complete_job(job.job_id, error=str(exc))
        logger.warning("Repository indexing failed (400 Bad Request): %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except HTTPException:
        coordinator.complete_job(job.job_id, error="HTTP Exception")
        raise
    except Exception as exc:
        coordinator.complete_job(job.job_id, error=str(exc))
        logger.exception("Unexpected error indexing repository: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to index repository due to an internal server error.",
        ) from exc


@router.get(
    "/index/status/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
def get_indexing_status(
    job_id: str,
    rag_service: RAGService = Depends(get_rag_service),
) -> JobStatusResponse:
    """Retrieve runtime status and queue position of an indexing job."""
    job = rag_service.indexing_coordinator.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Indexing job '{job_id}' not found.",
        )

    parsed_result: Optional[IndexRepositoryResponse] = None
    if job.result:
        try:
            parsed_result = IndexRepositoryResponse(**job.result)
        except Exception:
            pass

    return JobStatusResponse(
        job_id=job.job_id,
        repository_source=job.repository_source,
        source_type=job.source_type,
        status=job.status,
        queue_position=job.queue_position,
        result=parsed_result,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )

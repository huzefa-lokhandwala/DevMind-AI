"""Repository indexing route handler."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.schemas.repository import IndexRepositoryRequest, IndexRepositoryResponse
from app.loaders import GitHubLoaderError
from app.services.rag_service import InvalidRepositoryError, RAGService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["Repositories"])


def get_rag_service(request: Request) -> RAGService:
    """Dependency to retrieve RAGService instance from FastAPI application state."""
    return request.app.state.rag_service


@router.post(
    "/index",
    response_model=IndexRepositoryResponse,
    status_code=status.HTTP_200_OK,
)
def index_repository(
    payload: IndexRepositoryRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> IndexRepositoryResponse:
    """Index a local software repository or public GitHub repository for semantic code search.

    Args:
        payload: IndexRepositoryRequest containing repository_path or github_url.
        rag_service: Injected RAGService instance.

    Returns:
        IndexRepositoryResponse containing repository summary statistics.
    """
    try:
        if payload.github_url:
            result = rag_service.index_github_repository(payload.github_url)
        elif payload.repository_path:
            result = rag_service.index_repository(payload.repository_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'repository_path' or 'github_url' must be supplied.",
            )
        return IndexRepositoryResponse(**result)
    except (InvalidRepositoryError, GitHubLoaderError) as exc:
        logger.warning("Repository indexing failed (400 Bad Request): %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error indexing repository: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to index repository due to an internal server error.",
        ) from exc

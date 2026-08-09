"""Query route handler for natural language codebase search and generation."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.schemas.query import QueryRequest, QueryResponse
from app.services.rag_service import RAGService, RepositoryNotIndexedError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Query"])


def get_rag_service(request: Request) -> RAGService:
    """Dependency to retrieve RAGService instance from FastAPI application state."""
    return request.app.state.rag_service


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
)
def query_repository(
    payload: QueryRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> QueryResponse:
    """Query the indexed codebase using natural language.

    Args:
        payload: QueryRequest containing query string and optional top_k.
        rag_service: Injected RAGService instance.

    Returns:
        QueryResponse containing generated answer, source citations, model metadata, and latency.
    """
    try:
        result = rag_service.query(payload.query, top_k=payload.top_k)
        return QueryResponse(**result)
    except RepositoryNotIndexedError as exc:
        logger.warning("Query attempted on unindexed repository (400 Bad Request): %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        err_msg = str(exc)
        if "Gemini API key" in err_msg or "unconfigured" in err_msg:
            logger.error("LLM Provider misconfiguration (502 Bad Gateway): %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="LLM provider is unconfigured or unavailable.",
            ) from exc
        logger.warning("Invalid query input (400 Bad Request): %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during RAG query: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM generation or search processing failed.",
        ) from exc

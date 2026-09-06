"""Query route handler for natural language codebase search and generation."""

from __future__ import annotations

import logging

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from google import genai
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, verify_api_key
from app.api.schemas.query import QueryRequest, QueryResponse
from app.db.database import get_db
from app.db.models import UserModel
from app.llm.exceptions import AllProvidersFailedError, LLMProviderError
from app.services.rag_service import (
    RAGService,
    RepositoryNotFoundError,
    RepositoryNotIndexedError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Query"])


def get_rag_service(request: Request) -> RAGService:
    """Dependency to retrieve RAGService instance from FastAPI application state."""
    return request.app.state.rag_service


from app.utils.session_validator import validate_optional_session_id


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
def query_repository(
    payload: QueryRequest,
    session_id: Optional[str] = Depends(validate_optional_session_id),
    rag_service: RAGService = Depends(get_rag_service),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueryResponse:
    """Query the indexed codebase or ask general questions with intent routing.

    Args:
        payload: QueryRequest containing query string, optional top_k, and optional conversation_id.
        session_id: Extracted browser session ID from X-Session-ID.
        rag_service: Injected RAGService instance.
        current_user: Authenticated user context.
        db: Injected database session.

    Returns:
        QueryResponse containing generated answer, source citations, model metadata, intent, and latency.
    """
    try:
        result = rag_service.query(
            payload.query,
            top_k=payload.top_k,
            session_id=session_id,
            conversation_id=payload.conversation_id,
            user_id=current_user.id,
            repository_name=payload.repository_name,
            db_session=db,
        )
        return QueryResponse(**result)
    except RepositoryNotFoundError as exc:
        logger.warning("Query attempted on missing or unowned repository (404 Not Found): %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RepositoryNotIndexedError as exc:
        logger.warning("Query attempted on unindexed repository (400 Bad Request): %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except AllProvidersFailedError as exc:
        logger.error("All configured LLM providers failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="All configured AI providers are temporarily unavailable. Please try again later.",
        ) from exc
    except genai.errors.APIError as exc:
        logger.error("Gemini API error (%s) (502 Bad Gateway): %s", getattr(exc, "code", "APIError"), exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API error ({getattr(exc, 'code', 502)}): {getattr(exc, 'message', str(exc))}",
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

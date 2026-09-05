"""Session-isolated conversation history route handlers for DevMind AI."""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.auth import verify_api_key
from app.api.schemas.conversation import (
    ConversationDetail,
    ConversationSummary,
    CreateConversationRequest,
    MessageItem,
    UpdateConversationRequest,
)
from app.api.schemas.query import SourceDocument
from app.db import crud
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


def get_db():
    """Database session dependency with guaranteed closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from app.utils.session_validator import validate_session_id


@router.get(
    "",
    response_model=list[ConversationSummary],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
def list_conversations(
    session_id: str = Depends(validate_session_id),
    db: Session = Depends(get_db),
) -> list[ConversationSummary]:
    """List all recent conversations for the current session in descending updated order."""
    conv_models = crud.list_conversations(db, session_id=session_id)
    summaries: list[ConversationSummary] = []
    for c in conv_models:
        summaries.append(
            ConversationSummary(
                id=c.id,
                session_id=c.session_id,
                title=c.title,
                repository_name=c.repository_name,
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=len(c.messages) if c.messages else 0,
            )
        )
    return summaries


@router.post(
    "",
    response_model=ConversationDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
)
def create_conversation(
    payload: CreateConversationRequest,
    session_id: str = Depends(validate_session_id),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    """Create a new conversation for the current session."""
    conv = crud.create_conversation(
        db,
        session_id=session_id,
        title=payload.title or "New Chat",
        repository_name=payload.repository_name,
    )
    return ConversationDetail(
        id=conv.id,
        session_id=conv.session_id,
        title=conv.title,
        repository_name=conv.repository_name,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[],
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
def get_conversation(
    conversation_id: str,
    session_id: str = Depends(validate_session_id),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    """Get full conversation details and ordered message turns, enforcing session isolation."""
    conv = crud.get_conversation(db, conversation_id=conversation_id, session_id=session_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )

    messages: list[MessageItem] = []
    for m in conv.messages:
        sources_list: Optional[list[SourceDocument]] = None
        if m.sources_json:
            try:
                raw_sources = json.loads(m.sources_json)
                if isinstance(raw_sources, list):
                    sources_list = [SourceDocument(**s) for s in raw_sources]
            except Exception:
                pass

        messages.append(
            MessageItem(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                intent=m.intent,
                sources=sources_list,
                provider=m.provider,
                model=m.model,
                latency_ms=m.latency_ms,
                created_at=m.created_at,
            )
        )

    return ConversationDetail(
        id=conv.id,
        session_id=conv.session_id,
        title=conv.title,
        repository_name=conv.repository_name,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=messages,
    )


@router.patch(
    "/{conversation_id}",
    response_model=ConversationDetail,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
def update_conversation(
    conversation_id: str,
    payload: UpdateConversationRequest,
    session_id: str = Depends(validate_session_id),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    """Update conversation title."""
    conv = crud.update_conversation_title(
        db,
        conversation_id=conversation_id,
        session_id=session_id,
        title=payload.title.strip(),
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )
    return get_conversation(conversation_id=conversation_id, session_id=session_id, db=db)


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_api_key)],
)
def delete_conversation(
    conversation_id: str,
    session_id: str = Depends(validate_session_id),
    db: Session = Depends(get_db),
) -> None:
    """Delete a conversation, enforcing session isolation."""
    success = crud.delete_conversation(db, conversation_id=conversation_id, session_id=session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_api_key)],
)
def delete_all_conversations(
    session_id: str = Depends(validate_session_id),
    db: Session = Depends(get_db),
) -> None:
    """Clear all conversation history for the current session."""
    crud.delete_all_conversations(db, session_id=session_id)

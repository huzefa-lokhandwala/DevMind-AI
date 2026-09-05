"""Pydantic schemas for session-isolated conversation history endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.api.schemas.query import SourceDocument


class MessageItem(BaseModel):
    """Message payload within a conversation history response."""

    id: int
    conversation_id: str
    role: str
    content: str
    intent: Optional[str] = None
    sources: Optional[list[SourceDocument]] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    latency_ms: Optional[float] = None
    created_at: datetime


class ConversationSummary(BaseModel):
    """Brief metadata summary for sidebar conversation lists."""

    id: str
    session_id: str
    title: str
    repository_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationDetail(BaseModel):
    """Detailed conversation payload including all ordered message turns."""

    id: str
    session_id: str
    title: str
    repository_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageItem] = Field(default_factory=list)


class CreateConversationRequest(BaseModel):
    """Payload for POST /conversations."""

    title: Optional[str] = "New Chat"
    repository_name: Optional[str] = None


class UpdateConversationRequest(BaseModel):
    """Payload for PATCH /conversations/{conversation_id}."""

    title: str

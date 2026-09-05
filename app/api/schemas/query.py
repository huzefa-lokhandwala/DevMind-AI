"""Pydantic schemas for search query endpoint."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    """Payload for POST /query."""

    query: str = Field(
        ...,
        description="Natural language query string.",
        examples=["Where is login implemented?"],
    )
    top_k: int = Field(
        default=5,
        gt=0,
        description="Maximum number of context chunks to retrieve (must be > 0).",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional conversation ID to append message turns to persistent chat history.",
    )

    @field_validator("query")
    @classmethod
    def validate_non_empty_query(cls, v: str) -> str:
        """Ensure query string is not blank or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Query string must not be empty or whitespace-only.")
        return v


class SourceDocument(BaseModel):
    """Source code chunk attribution metadata."""

    repository: str
    file: str
    file_path: Optional[str] = None
    symbol: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    score: float
    snippet: Optional[str] = None
    language: Optional[str] = None


class QueryResponse(BaseModel):
    """Response payload for POST /query."""

    answer: str
    sources: list[SourceDocument]
    provider: str
    model: str
    latency_ms: float
    intent: Optional[str] = "REPOSITORY"
    conversation_id: Optional[str] = None

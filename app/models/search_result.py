"""SearchResult model for DevMind AI retrieval layer."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.document import Document


@dataclass(frozen=True)
class SearchResult:
    """Represents a ranked document match from semantic search retrieval."""

    rank: int

    score: float

    document: Document

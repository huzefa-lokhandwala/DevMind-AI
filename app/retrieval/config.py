"""Configuration models for advanced hybrid retrieval and reranking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalConfig:
    """Configurable settings governing hybrid retrieval, thresholding, and reranking."""

    initial_k: int = 20
    """Number of candidate search results to retrieve from FAISS vector store initially."""

    final_k: int = 5
    """Number of top-ranked search results to return after reranking and filtering."""

    similarity_threshold: float = 0.25
    """Minimum combined relevance score required for a candidate result to be retained."""

    enable_reranking: bool = True
    """Whether to apply hybrid lexical & metadata symbol reranking."""

    semantic_weight: float = 0.65
    """Weight factor for dense vector cosine similarity score."""

    keyword_weight: float = 0.25
    """Weight factor for lexical content term overlap score."""

    symbol_boost: float = 0.10
    """Additive score boost when query tokens match code symbols (function/class/file names)."""

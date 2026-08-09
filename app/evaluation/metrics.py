"""Metric calculations for RAG retrieval evaluation (Top-1, Recall@K, MRR)."""

from __future__ import annotations

from typing import Sequence

from app.evaluation.dataset import EvaluationCase
from app.models.search_result import SearchResult


def is_relevant_match(res: SearchResult, case: EvaluationCase) -> bool:
    """Check if a SearchResult matches expected files or symbols in an EvaluationCase."""
    doc = res.document

    # Check file name matches
    if any(expected_file in doc.file_name or doc.file_name in expected_file for expected_file in case.expected_files):
        return True

    # Check symbol matches (function or class)
    symbols = {doc.function_name, doc.class_name} - {None}
    if any(s in case.expected_symbols for s in symbols):
        return True

    return False


def top_1_accuracy_case(results: Sequence[SearchResult], case: EvaluationCase) -> float:
    """Return 1.0 if top-1 search result is relevant, else 0.0."""
    if not results:
        return 0.0
    return 1.0 if is_relevant_match(results[0], case) else 0.0


def recall_at_k_case(results: Sequence[SearchResult], case: EvaluationCase, k: int) -> float:
    """Return 1.0 if at least one result within top-K is relevant, else 0.0."""
    if not results:
        return 0.0
    top_k_results = results[:k]
    return 1.0 if any(is_relevant_match(res, case) for res in top_k_results) else 0.0


def reciprocal_rank_case(results: Sequence[SearchResult], case: EvaluationCase) -> float:
    """Return 1.0 / rank of first relevant match, else 0.0."""
    for rank, res in enumerate(results, start=1):
        if is_relevant_match(res, case):
            return 1.0 / rank
    return 0.0

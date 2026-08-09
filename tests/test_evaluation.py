"""Unit tests for RAG evaluation dataset, metrics, and evaluator framework."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.evaluation.dataset import EvaluationCase, get_sample_evaluation_dataset
from app.evaluation.evaluator import RAGEvaluator
from app.evaluation.metrics import (
    is_relevant_match,
    reciprocal_rank_case,
    recall_at_k_case,
    top_1_accuracy_case,
)
from app.models.document import Document
from app.models.search_result import SearchResult
from app.retrieval.retriever import Retriever


@pytest.fixture
def sample_case() -> EvaluationCase:
    """Return sample evaluation case."""
    return EvaluationCase(
        query="Where is login implemented?",
        expected_files=["auth.py"],
        expected_symbols=["login"],
    )


@pytest.fixture
def auth_doc() -> Document:
    """Return document matching auth.py / login."""
    return Document(
        content="def login(): pass",
        file_name="auth.py",
        file_path="auth.py",
        extension=".py",
        repository_name="sample_repo",
        function_name="login",
    )


@pytest.fixture
def calc_doc() -> Document:
    """Return document matching calculator.py / add."""
    return Document(
        content="def add(): pass",
        file_name="calculator.py",
        file_path="calculator.py",
        extension=".py",
        repository_name="sample_repo",
        function_name="add",
    )


def test_is_relevant_match(sample_case: EvaluationCase, auth_doc: Document, calc_doc: Document) -> None:
    """Test relevance checking for file and symbol matches."""
    auth_result = SearchResult(rank=1, score=0.9, document=auth_doc)
    calc_result = SearchResult(rank=2, score=0.4, document=calc_doc)

    assert is_relevant_match(auth_result, sample_case) is True
    assert is_relevant_match(calc_result, sample_case) is False


def test_top_1_accuracy_metric(sample_case: EvaluationCase, auth_doc: Document, calc_doc: Document) -> None:
    """Test Top-1 accuracy metric computation."""
    res_relevant_first = [
        SearchResult(rank=1, score=0.9, document=auth_doc),
        SearchResult(rank=2, score=0.4, document=calc_doc),
    ]
    res_irrelevant_first = [
        SearchResult(rank=1, score=0.9, document=calc_doc),
        SearchResult(rank=2, score=0.4, document=auth_doc),
    ]

    assert top_1_accuracy_case(res_relevant_first, sample_case) == 1.0
    assert top_1_accuracy_case(res_irrelevant_first, sample_case) == 0.0
    assert top_1_accuracy_case([], sample_case) == 0.0


def test_recall_at_k_metric(sample_case: EvaluationCase, auth_doc: Document, calc_doc: Document) -> None:
    """Test Recall@K metric computation."""
    results = [
        SearchResult(rank=1, score=0.9, document=calc_doc),
        SearchResult(rank=2, score=0.4, document=auth_doc),
    ]

    assert recall_at_k_case(results, sample_case, k=1) == 0.0
    assert recall_at_k_case(results, sample_case, k=2) == 1.0


def test_reciprocal_rank_metric(sample_case: EvaluationCase, auth_doc: Document, calc_doc: Document) -> None:
    """Test Reciprocal Rank (MRR) metric computation."""
    results_rank_2 = [
        SearchResult(rank=1, score=0.9, document=calc_doc),
        SearchResult(rank=2, score=0.4, document=auth_doc),
    ]

    assert reciprocal_rank_case(results_rank_2, sample_case) == 0.5


def test_evaluator_report_generation(sample_case: EvaluationCase, auth_doc: Document) -> None:
    """Test RAGEvaluator produces an EvaluationReport with calculated benchmark metrics."""
    mock_retriever = MagicMock(spec=Retriever)
    mock_retriever.retrieve.return_value = [
        SearchResult(rank=1, score=0.9, document=auth_doc)
    ]

    evaluator = RAGEvaluator()
    report = evaluator.evaluate(mock_retriever, [sample_case])

    assert report.total_cases == 1
    assert report.top_1_accuracy == 1.0
    assert report.recall_at_3 == 1.0
    assert report.recall_at_5 == 1.0
    assert report.mrr == 1.0

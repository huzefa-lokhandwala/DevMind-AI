"""Unit tests for the Retriever module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.embeddings.embedding_engine import EmbeddingEngine
from app.models import Document, SearchResult
from app.retrieval.config import RetrievalConfig
from app.retrieval.retriever import Retriever
from app.vector_store.faiss_store import FAISSVectorStore


def _make_document(content: str, file_name: str = "auth.py", function_name: str | None = "login") -> Document:
    return Document(
        content=content,
        file_name=file_name,
        file_path=f"/tmp/{file_name}",
        extension=".py",
        repository_name="sample_project",
        chunk_type="function",
        function_name=function_name,
        start_line=1,
        end_line=5,
    )


def test_retrieve_returns_ranked_search_results() -> None:
    """Test raw semantic retrieval returns original cosine similarity scores when reranking is disabled."""
    doc1 = _make_document("def login(): pass", file_name="auth.py")
    doc2 = _make_document("def logout(): pass", file_name="auth.py", function_name="logout")

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1, 0.2, 0.3, 0.4]

    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = [(doc1, 0.95), (doc2, 0.70)]

    config = RetrievalConfig(enable_reranking=False, similarity_threshold=0.0)
    retriever = Retriever(mock_engine, mock_store, config=config)
    results = retriever.retrieve("login function", k=2)

    assert len(results) == 2
    assert isinstance(results[0], SearchResult)
    assert results[0].rank == 1
    assert results[0].score == 0.95
    assert results[0].document == doc1

    assert results[1].rank == 2
    assert results[1].score == 0.70
    assert results[1].document == doc2

    mock_engine.embed_query.assert_called_once_with("login function")


def test_retrieve_with_hybrid_reranking() -> None:
    """Test hybrid retrieval applies lexical and symbol match scoring when reranking is enabled."""
    doc1 = _make_document("def login(): pass", file_name="auth.py", function_name="login")
    doc2 = _make_document("def logout(): pass", file_name="auth.py", function_name="logout")

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1, 0.2, 0.3, 0.4]

    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = [(doc1, 0.95), (doc2, 0.70)]

    config = RetrievalConfig(enable_reranking=True, similarity_threshold=0.0)
    retriever = Retriever(mock_engine, mock_store, config=config)
    results = retriever.retrieve("login", k=2)

    assert len(results) == 2
    assert results[0].document == doc1
    # doc1 receives symbol match boost for 'login'
    assert results[0].score > results[1].score


def test_retrieve_empty_query() -> None:
    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_store = MagicMock(spec=FAISSVectorStore)

    retriever = Retriever(mock_engine, mock_store)
    results = retriever.retrieve("   ", k=5)

    assert results == []
    mock_engine.embed_query.assert_not_called()
    mock_store.search.assert_not_called()


def test_document_remains_unmutated() -> None:
    doc = _make_document("def login(): pass")

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [1.0, 0.0]

    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = [(doc, 0.88)]

    config = RetrievalConfig(enable_reranking=False, similarity_threshold=0.0)
    retriever = Retriever(mock_engine, mock_store, config=config)
    results = retriever.retrieve("login", k=1)

    assert len(results) == 1
    assert results[0].document.similarity_score is None  # Pristine document


def test_retrieve_prioritizes_production_source_over_tests_and_docs() -> None:
    """Verify that implementation queries prioritize production source files over test files and docs."""
    prod_doc = Document(
        content="export class VerificationEngine { generateProofHash() { return '0x123'; } }",
        file_name="engine.ts",
        file_path="lib/verification/engine.ts",
        extension=".ts",
        repository_name="proofos",
        chunk_type="file",
        class_name="VerificationEngine",
        start_line=1,
        end_line=20,
    )
    test_doc = Document(
        content="describe('VerificationEngine', () => { it('should generate proof hash', () => {}); });",
        file_name="verification.test.ts",
        file_path="tests/verification.test.ts",
        extension=".ts",
        repository_name="proofos",
        chunk_type="file",
        class_name=None,
        start_line=1,
        end_line=25,
    )

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1, 0.2, 0.3, 0.4]

    mock_store = MagicMock(spec=FAISSVectorStore)
    # Simulate test file initially getting slightly higher semantic score due to dense keyword matches
    mock_store.search.return_value = [(test_doc, 0.70), (prod_doc, 0.65)]

    config = RetrievalConfig(enable_reranking=True, similarity_threshold=0.0)
    retriever = Retriever(mock_engine, mock_store, config=config)
    results = retriever.retrieve("Where is VerificationEngine implemented?", k=2)

    assert len(results) == 2
    assert results[0].document.file_path == "lib/verification/engine.ts"
    assert results[0].rank == 1
    assert results[1].document.file_path == "tests/verification.test.ts"
    assert results[1].rank == 2


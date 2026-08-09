"""Unit tests for advanced hybrid retrieval, reranking, and threshold filtering."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.embeddings.embedding_engine import EmbeddingEngine
from app.models.document import Document
from app.models.search_result import SearchResult
from app.retrieval.config import RetrievalConfig
from app.retrieval.keyword_matcher import KeywordMatcher
from app.retrieval.reranker import CodeReranker
from app.retrieval.retriever import Retriever
from app.vector_store.faiss_store import FAISSVectorStore


@pytest.fixture
def sample_documents() -> list[Document]:
    """Return sample documents for retrieval testing."""
    return [
        Document(
            content="def login(username, password):\n    return authenticate(username, password)",
            file_name="auth.py",
            file_path="auth.py",
            extension=".py",
            repository_name="sample_repo",
            language="python",
            chunk_type="function",
            function_name="login",
            start_line=1,
            end_line=2,
            embedding=[0.1] * 384,
        ),
        Document(
            content="def add(a, b):\n    return a + b",
            file_name="calculator.py",
            file_path="calculator.py",
            extension=".py",
            repository_name="sample_repo",
            language="python",
            chunk_type="function",
            function_name="add",
            start_line=1,
            end_line=2,
            embedding=[0.9] * 384,
        ),
    ]


def test_keyword_matcher_tokenize_and_overlap() -> None:
    """Test KeywordMatcher tokenization and content overlap calculation."""
    matcher = KeywordMatcher()
    q_tokens = matcher.tokenize("Where is login function?")
    c_tokens = matcher.tokenize("def login(username, password): return authenticate()")

    assert "login" in q_tokens
    assert "where" not in q_tokens  # Stop word removed
    assert "function" not in q_tokens  # Stop word removed

    score = matcher.compute_lexical_score(q_tokens, c_tokens)
    assert score == 1.0


def test_symbol_match_detection(sample_documents: list[Document]) -> None:
    """Test KeywordMatcher symbol match boost signal for function names."""
    matcher = KeywordMatcher()
    doc_login = sample_documents[0]

    q_tokens = matcher.tokenize("Find login implementation")
    boost = matcher.detect_symbol_match(q_tokens, doc_login)
    assert boost == 1.0

    q_unrelated = matcher.tokenize("Find addition implementation")
    no_boost = matcher.detect_symbol_match(q_unrelated, doc_login)
    assert no_boost == 0.0


def test_reranker_score_normalization_and_immutability(sample_documents: list[Document]) -> None:
    """Test CodeReranker score calculation and Document immutability."""
    reranker = CodeReranker()
    candidates = [
        SearchResult(rank=1, score=0.8, document=sample_documents[0]),
        SearchResult(rank=2, score=0.4, document=sample_documents[1]),
    ]

    reranked = reranker.rerank("login user", candidates, top_k=2)

    assert len(reranked) == 2
    assert reranked[0].rank == 1
    assert reranked[0].document.file_name == "auth.py"
    # Document object remains identical instance
    assert reranked[0].document is sample_documents[0]


def test_similarity_threshold_filtering(sample_documents: list[Document]) -> None:
    """Test filtering candidates below configured similarity threshold."""
    config = RetrievalConfig(similarity_threshold=0.50, enable_reranking=False)
    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1] * 384

    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = [
        (sample_documents[0], 0.85),  # Above threshold
        (sample_documents[1], 0.20),  # Below threshold
    ]

    retriever = Retriever(mock_engine, mock_store, config=config)
    results = retriever.retrieve("login", k=5)

    assert len(results) == 1
    assert results[0].document.file_name == "auth.py"
    assert results[0].score == 0.85


def test_retriever_empty_query_and_empty_store() -> None:
    """Test Retriever handles blank queries and empty vector store results gracefully."""
    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = []

    retriever = Retriever(mock_engine, mock_store)

    assert retriever.retrieve("") == []
    assert retriever.retrieve("   ") == []

    mock_engine.embed_query.return_value = [0.0] * 384
    assert retriever.retrieve("valid query") == []

"""Unit and integration tests for Query Intent Routing in DevMind AI."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models.document import Document
from app.models.llm_response import LLMResponse
from app.models.search_result import SearchResult
from app.prompts.context_assembler import ContextAssembler, PromptContext
from app.routing.intent_classifier import QueryIntent, classify_intent
from app.services.rag_service import RAGService, RepositoryNotIndexedError


def test_classify_intent_general():
    """Verify general conversational, smalltalk, and conceptual queries map to GENERAL."""
    assert classify_intent("hi") == QueryIntent.GENERAL
    assert classify_intent("hello") == QueryIntent.GENERAL
    assert classify_intent("how are you") == QueryIntent.GENERAL
    assert classify_intent("what is DI?") == QueryIntent.GENERAL
    assert classify_intent("what is dependency injection?") == QueryIntent.GENERAL
    assert classify_intent("what is Python?") == QueryIntent.GENERAL
    assert classify_intent("what is FAISS?") == QueryIntent.GENERAL
    assert classify_intent("what is JWT?") == QueryIntent.GENERAL
    assert classify_intent("what is authentication?") == QueryIntent.GENERAL
    assert classify_intent("explain FastAPI") == QueryIntent.GENERAL
    assert classify_intent("explain REST API") == QueryIntent.GENERAL
    assert classify_intent("what is the weather today?") == QueryIntent.GENERAL
    assert classify_intent("tell me a joke") == QueryIntent.GENERAL
    assert classify_intent("DI") == QueryIntent.GENERAL
    assert classify_intent("auth") == QueryIntent.GENERAL


def test_classify_intent_repository():
    """Verify repository-specific questions map to REPOSITORY."""
    assert classify_intent("what is this repository about?") == QueryIntent.REPOSITORY
    assert classify_intent("explain this codebase") == QueryIntent.REPOSITORY
    assert classify_intent("where is authentication implemented?") == QueryIntent.REPOSITORY
    assert classify_intent("where is SORTTracker defined?") == QueryIntent.REPOSITORY
    assert classify_intent("how does this project handle embeddings?") == QueryIntent.REPOSITORY
    assert classify_intent("what files implement the API?") == QueryIntent.REPOSITORY
    assert classify_intent("explain the architecture of this repository") == QueryIntent.REPOSITORY
    assert classify_intent("which file contains the login endpoint?") == QueryIntent.REPOSITORY
    assert classify_intent("find the class in auth.py") == QueryIntent.REPOSITORY


def test_classify_intent_mixed():
    """Verify combined conceptual + repository queries map to MIXED regardless of word order."""
    assert (
        classify_intent("what is dependency injection and where is it used in this repository?")
        == QueryIntent.MIXED
    )
    assert (
        classify_intent("what is FAISS and how does this project use it?")
        == QueryIntent.MIXED
    )
    assert (
        classify_intent("explain JWT authentication and where authentication is implemented here")
        == QueryIntent.MIXED
    )
    assert (
        classify_intent("what is FastAPI and where is FastAPI used in this project?")
        == QueryIntent.MIXED
    )
    assert (
        classify_intent("what is FastAPI and how is it used in this project?")
        == QueryIntent.MIXED
    )
    assert (
        classify_intent("explain embeddings generally and tell me how this repository generates them")
        == QueryIntent.MIXED
    )


def test_general_query_bypasses_retrieval_and_has_no_sources():
    """GENERAL query should never invoke retriever and must return empty sources."""
    mock_retriever = MagicMock()
    mock_llm = MagicMock()
    mock_llm.generate.return_value = LLMResponse(
        answer="Dependency Injection is a design pattern...",
        provider="gemini",
        model="gemini-3.6-flash",
        latency_ms=120.0,
    )

    rag = RAGService(llm_provider=mock_llm)
    rag.retriever = mock_retriever

    result = rag.query("what is dependency injection?")

    # Verify retriever was NEVER called
    mock_retriever.retrieve.assert_not_called()
    assert result["intent"] == "GENERAL"
    assert result["sources"] == []
    assert "Dependency Injection is a design pattern" in result["answer"]


def test_general_query_succeeds_even_before_repository_indexed():
    """GENERAL query ('hi', 'what is python') works even if no repository is indexed."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = LLMResponse(
        answer="Hello! How can I assist you with your software engineering tasks today?",
        provider="gemini",
        model="gemini-3.6-flash",
        latency_ms=80.0,
    )

    rag = RAGService(llm_provider=mock_llm)
    assert rag.is_indexed is False

    # Should NOT raise RepositoryNotIndexedError
    result = rag.query("hello!")
    assert result["intent"] == "GENERAL"
    assert result["sources"] == []
    assert "Hello!" in result["answer"]


def test_repository_query_requires_indexed_repo():
    """REPOSITORY query raises RepositoryNotIndexedError if vector store is uninitialized."""
    mock_llm = MagicMock()
    rag = RAGService(llm_provider=mock_llm)
    assert rag.is_indexed is False

    with pytest.raises(RepositoryNotIndexedError):
        rag.query("where is authentication implemented in this repository?")


def test_repository_query_invokes_retrieval_and_returns_sources():
    """REPOSITORY query properly retrieves chunks and passes them to the LLM."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = LLMResponse(
        answer="Authentication is implemented in `app/api/auth.py`.",
        provider="gemini",
        model="gemini-3.6-flash",
        latency_ms=150.0,
    )

    mock_retriever = MagicMock()
    sample_doc = Document(
        content="def verify_api_key(): ...",
        file_path="app/api/auth.py",
        file_name="auth.py",
        extension=".py",
        repository_name="test-repo",
        start_line=1,
        end_line=20,
    )
    mock_retriever.retrieve.return_value = [
        SearchResult(document=sample_doc, score=0.92, rank=1)
    ]

    rag = RAGService(llm_provider=mock_llm)
    # Mark as indexed
    mock_store = MagicMock()
    mock_store.total_documents = 1
    rag.vector_store = mock_store
    rag.retriever = mock_retriever
    rag.indexed_repository_name = "test-repo"

    result = rag.query("where is authentication implemented in this repository?")

    mock_retriever.retrieve.assert_called_once()
    assert result["intent"] == "REPOSITORY"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["file_path"] == "app/api/auth.py"
    assert result["sources"][0]["score"] == 0.92


def test_mixed_query_uses_mixed_system_prompt():
    """MIXED query invokes retrieval and applies the MIXED_SYSTEM_PROMPT."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = LLMResponse(
        answer="FAISS is a vector search library. In this repo, it is used in `faiss_store.py`.",
        provider="gemini",
        model="gemini-3.6-flash",
        latency_ms=180.0,
    )

    mock_retriever = MagicMock()
    sample_doc = Document(
        content="class FAISSVectorStore: ...",
        file_path="app/vector_store/faiss_store.py",
        file_name="faiss_store.py",
        extension=".py",
        repository_name="test-repo",
    )
    mock_retriever.retrieve.return_value = [
        SearchResult(document=sample_doc, score=0.88, rank=1)
    ]

    rag = RAGService(llm_provider=mock_llm)
    mock_store = MagicMock()
    mock_store.total_documents = 1
    rag.vector_store = mock_store
    rag.retriever = mock_retriever
    rag.indexed_repository_name = "test-repo"

    result = rag.query("explain FAISS generally and tell me how this project uses it")

    mock_retriever.retrieve.assert_called_once()
    assert result["intent"] == "MIXED"
    assert len(result["sources"]) == 1

    # Verify prompt passed to generate contained mixed system instructions
    call_args = mock_llm.generate.call_args[0][0]
    assert "The user is asking BOTH a general conceptual question and a repository-specific question" in call_args.system_prompt

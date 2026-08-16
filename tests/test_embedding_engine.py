"""Unit and integration tests for DevMind AI EmbeddingEngine and providers."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
import numpy as np

from app.embeddings.embedding_engine import (
    EmbeddingEngine,
    LocalEmbeddingProvider,
    GeminiEmbeddingProvider,
)
from app.models import Document
from app.vector_store.faiss_store import FAISSVectorStore

LOCAL_DIMENSION = 384
GEMINI_DIMENSION = 768


def _make_document(content: str, *, file_name: str = "auth.py") -> Document:
    return Document(
        content=content,
        file_name=file_name,
        file_path=f"/tmp/{file_name}",
        extension=".py",
        repository_name="sample_project",
        chunk_type="function",
        function_name="login",
        start_line=1,
        end_line=5,
    )


@pytest.fixture
def mock_fastembed_model() -> MagicMock:
    """Fixture providing a mock FastEmbed TextEmbedding model for unit tests."""
    mock_model = MagicMock()

    def embed_side_effect(texts: list[str], batch_size: int = 64):
        for _ in texts:
            yield np.array([0.05] * LOCAL_DIMENSION, dtype=np.float32)

    mock_model.embed.side_effect = embed_side_effect
    return mock_model


@pytest.fixture
def mock_genai_client() -> MagicMock:
    """Fixture providing a mock google.genai.Client configured for Gemini embeddings."""
    from google import genai
    from google.genai import types

    mock_client = MagicMock(spec=genai.Client)

    def embed_content_side_effect(model: str, contents: str | list[str], config: types.EmbedContentConfig | None = None) -> types.EmbedContentResponse:
        dim = config.output_dimensionality if config and config.output_dimensionality else GEMINI_DIMENSION
        if isinstance(contents, str):
            embeddings = [types.ContentEmbedding(values=[0.1] * dim)]
        else:
            embeddings = [
                types.ContentEmbedding(values=[0.1 * (i + 1)] * dim)
                for i in range(len(contents))
            ]
        return types.EmbedContentResponse(embeddings=embeddings)

    mock_client.models.embed_content.side_effect = embed_content_side_effect
    return mock_client


# ==========================================
# 1. LocalEmbeddingProvider Tests
# ==========================================

def test_local_provider_default_model_and_dimension(mock_fastembed_model: MagicMock) -> None:
    """Test LocalEmbeddingProvider defaults to BAAI/bge-small-en-v1.5 and 384 dimensions."""
    provider = LocalEmbeddingProvider(model=mock_fastembed_model)

    assert provider.model_name == "BAAI/bge-small-en-v1.5"
    assert provider.embedding_dimension == 384


def test_local_provider_embed_one_document(mock_fastembed_model: MagicMock) -> None:
    """Test LocalEmbeddingProvider embeds a single document with 384-dimensional vector."""
    provider = LocalEmbeddingProvider(model=mock_fastembed_model)
    doc = _make_document("def test_fn(): pass")

    embedded = provider.embed_documents([doc])

    assert len(embedded) == 1
    assert embedded[0].embedding is not None
    assert len(embedded[0].embedding) == 384
    assert isinstance(embedded[0].embedding, list)
    assert all(isinstance(v, float) for v in embedded[0].embedding)


def test_local_provider_embed_multiple_documents(mock_fastembed_model: MagicMock) -> None:
    """Test LocalEmbeddingProvider produces exactly one 384d vector per input document in order."""
    provider = LocalEmbeddingProvider(model=mock_fastembed_model)
    docs = [
        _make_document("def func_a(): pass", file_name="a.py"),
        _make_document("def func_b(): pass", file_name="b.py"),
        _make_document("def func_c(): pass", file_name="c.py"),
    ]

    embedded = provider.embed_documents(docs)

    assert len(embedded) == 3
    assert all(len(d.embedding) == 384 for d in embedded)
    assert [d.file_name for d in embedded] == ["a.py", "b.py", "c.py"]


def test_local_provider_preserves_metadata_and_immutability(mock_fastembed_model: MagicMock) -> None:
    """Test LocalEmbeddingProvider does not mutate original documents and preserves all attributes."""
    provider = LocalEmbeddingProvider(model=mock_fastembed_model)
    original = _make_document("def login(): pass")

    embedded = provider.embed_documents([original])[0]

    assert original.embedding is None  # original unmutated
    assert embedded.embedding is not None
    assert embedded.content == original.content
    assert embedded.file_name == original.file_name
    assert embedded.function_name == original.function_name
    assert embedded.start_line == original.start_line
    assert embedded.end_line == original.end_line


def test_local_provider_empty_document_list(mock_fastembed_model: MagicMock) -> None:
    """Test LocalEmbeddingProvider with empty document list returns empty list."""
    provider = LocalEmbeddingProvider(model=mock_fastembed_model)
    assert provider.embed_documents([]) == []
    mock_fastembed_model.embed.assert_not_called()


def test_local_provider_embed_query(mock_fastembed_model: MagicMock) -> None:
    """Test LocalEmbeddingProvider produces a 384-dimensional float query vector."""
    provider = LocalEmbeddingProvider(model=mock_fastembed_model)
    vector = provider.embed_query("Where is authentication implemented?")

    assert len(vector) == 384
    assert isinstance(vector, list)
    assert all(isinstance(v, float) for v in vector)


def test_local_provider_empty_query_raises(mock_fastembed_model: MagicMock) -> None:
    """Test LocalEmbeddingProvider raises ValueError on empty query."""
    provider = LocalEmbeddingProvider(model=mock_fastembed_model)
    with pytest.raises(ValueError, match="Query string must not be empty"):
        provider.embed_query("   ")


def test_local_provider_model_caching_singleton() -> None:
    """Test LocalEmbeddingProvider caches the FastEmbed model singleton without re-instantiating."""
    mock_model_instance = MagicMock()
    # Save previous cache
    prev_model = LocalEmbeddingProvider._cached_model
    prev_name = LocalEmbeddingProvider._cached_model_name
    prev_threads = LocalEmbeddingProvider._cached_model_threads
    try:
        with patch("fastembed.TextEmbedding", return_value=mock_model_instance) as mock_text_embedding_cls:
            LocalEmbeddingProvider._cached_model = None
            LocalEmbeddingProvider._cached_model_name = None
            LocalEmbeddingProvider._cached_model_threads = None

            provider_1 = LocalEmbeddingProvider(model_name="BAAI/bge-small-en-v1.5", threads=1)
            m1 = provider_1._get_model()

            provider_2 = LocalEmbeddingProvider(model_name="BAAI/bge-small-en-v1.5", threads=1)
            m2 = provider_2._get_model()

            assert m1 is m2
            assert mock_text_embedding_cls.call_count == 1
    finally:
        LocalEmbeddingProvider._cached_model = prev_model
        LocalEmbeddingProvider._cached_model_name = prev_name
        LocalEmbeddingProvider._cached_model_threads = prev_threads


def test_local_provider_thread_and_batch_configuration() -> None:
    """Test LocalEmbeddingProvider parses thread limits and batch size from env/args."""
    with patch.dict(os.environ, {"EMBEDDING_THREADS": "2", "EMBEDDING_BATCH_SIZE": "8"}, clear=True):
        provider = LocalEmbeddingProvider(model=MagicMock())
        assert provider.threads == 2
        assert provider._default_batch_size == 8

    # Explicit constructor override takes precedence
    provider_custom = LocalEmbeddingProvider(model=MagicMock(), threads=1, batch_size=16)
    assert provider_custom.threads == 1
    assert provider_custom._default_batch_size == 16


def test_local_provider_threads_passed_to_fastembed() -> None:
    """Test that thread configuration is explicitly passed to fastembed.TextEmbedding."""
    mock_instance = MagicMock()
    prev_model = LocalEmbeddingProvider._cached_model
    prev_name = LocalEmbeddingProvider._cached_model_name
    prev_threads = LocalEmbeddingProvider._cached_model_threads
    try:
        with patch("fastembed.TextEmbedding", return_value=mock_instance) as mock_cls:
            LocalEmbeddingProvider._cached_model = None
            LocalEmbeddingProvider._cached_model_name = None
            LocalEmbeddingProvider._cached_model_threads = None

            provider = LocalEmbeddingProvider(threads=1)
            provider._get_model()

            mock_cls.assert_called_once_with(model_name="BAAI/bge-small-en-v1.5", threads=1)
    finally:
        LocalEmbeddingProvider._cached_model = prev_model
        LocalEmbeddingProvider._cached_model_name = prev_name
        LocalEmbeddingProvider._cached_model_threads = prev_threads


# ==========================================
# 2. EmbeddingEngine Facade & Provider Selection
# ==========================================

def test_engine_default_provider_is_local(mock_fastembed_model: MagicMock) -> None:
    """Test EmbeddingEngine defaults to local provider when EMBEDDING_PROVIDER is unset."""
    with patch.dict(os.environ, {}, clear=True):
        engine = EmbeddingEngine(local_model=mock_fastembed_model)

        assert engine.provider_name == "local"
        assert engine.model_name == "BAAI/bge-small-en-v1.5"
        assert engine.embedding_dimension == 384


def test_engine_explicit_local_provider(mock_fastembed_model: MagicMock) -> None:
    """Test EmbeddingEngine with explicit provider='local'."""
    engine = EmbeddingEngine(provider="local", local_model=mock_fastembed_model)

    assert engine.provider_name == "local"
    assert engine.model_name == "BAAI/bge-small-en-v1.5"
    assert engine.embedding_dimension == 384


def test_engine_gemini_provider_selection(mock_genai_client: MagicMock) -> None:
    """Test EmbeddingEngine with provider='gemini' selects GeminiEmbeddingProvider."""
    engine = EmbeddingEngine(provider="gemini", client=mock_genai_client)

    assert engine.provider_name == "gemini"
    assert engine.model_name == "gemini-embedding-001"
    assert engine.embedding_dimension == 768


def test_engine_unsupported_provider_raises() -> None:
    """Test EmbeddingEngine raises ValueError with clear message for unsupported provider."""
    with pytest.raises(ValueError, match="Unsupported embedding provider 'cohere'"):
        EmbeddingEngine(provider="cohere")


# ==========================================
# 3. GeminiEmbeddingProvider Tests
# ==========================================

def test_gemini_provider_embed_documents(mock_genai_client: MagicMock) -> None:
    """Test GeminiEmbeddingProvider embeds documents with 768d vectors."""
    provider = GeminiEmbeddingProvider(client=mock_genai_client)
    docs = [_make_document("def func(): pass")]

    embedded = provider.embed_documents(docs)

    assert len(embedded) == 1
    assert len(embedded[0].embedding) == 768
    mock_genai_client.models.embed_content.assert_called_once()


def test_gemini_provider_embed_query(mock_genai_client: MagicMock) -> None:
    """Test GeminiEmbeddingProvider embeds queries with 768d vectors."""
    provider = GeminiEmbeddingProvider(client=mock_genai_client)
    vector = provider.embed_query("test query")

    assert len(vector) == 768


def test_gemini_provider_missing_key_raises() -> None:
    """Test GeminiEmbeddingProvider raises ValueError when GEMINI_API_KEY is missing."""
    with patch.dict(os.environ, {}, clear=True):
        provider = GeminiEmbeddingProvider(api_key=None)
        with pytest.raises(ValueError, match="Gemini API key missing"):
            provider.embed_query("test")


# ==========================================
# 4. FAISS Vector Store Integration (384d)
# ==========================================

def test_faiss_store_integration_with_local_embeddings(mock_fastembed_model: MagicMock) -> None:
    """Test FAISSVectorStore builds and searches a 384d index created by LocalEmbeddingProvider."""
    engine = EmbeddingEngine(provider="local", local_model=mock_fastembed_model)
    documents = [
        _make_document("def login(): pass", file_name="auth.py"),
        _make_document("def logout(): pass", file_name="auth.py"),
    ]
    embedded_docs = engine.embed_documents(documents)

    store = FAISSVectorStore()
    store.build_index(embedded_docs)

    assert store.total_documents == 2
    assert store.embedding_dimension == 384

    query_vector = engine.embed_query("login user")
    results = store.search(query_vector, k=2)

    assert len(results) == 2
    assert isinstance(results[0][0], Document)
    assert isinstance(results[0][1], float)

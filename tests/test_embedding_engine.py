"""Unit and integration tests for the Gemini EmbeddingEngine module."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from google import genai
from google.genai import types

from app.embeddings.embedding_engine import EmbeddingEngine
from app.models import Document
from app.vector_store.faiss_store import FAISSVectorStore

EMBEDDING_DIMENSION = 768


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
def mock_genai_client() -> MagicMock:
    """Fixture providing a mock google.genai.Client configured for embeddings."""
    mock_client = MagicMock(spec=genai.Client)

    def embed_content_side_effect(model: str, contents: str | list[str], config: types.EmbedContentConfig | None = None) -> types.EmbedContentResponse:
        dim = config.output_dimensionality if config and config.output_dimensionality else EMBEDDING_DIMENSION
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


def test_default_model_name_and_dimension(mock_genai_client: MagicMock) -> None:
    """Test default initialization uses gemini-embedding-001 and 768 dimensions."""
    engine = EmbeddingEngine(client=mock_genai_client)

    assert engine.model_name == "gemini-embedding-001"
    assert engine.embedding_dimension == 768


def test_custom_model_and_dimension(mock_genai_client: MagicMock) -> None:
    """Test configuring custom model name and dimension."""
    engine = EmbeddingEngine(
        model_name="custom-embedding-model",
        dimension=512,
        client=mock_genai_client,
    )

    assert engine.model_name == "custom-embedding-model"
    assert engine.embedding_dimension == 512


def test_missing_api_key_raises_on_embed() -> None:
    """Test that an unauthenticated engine raises ValueError when attempting to embed."""
    with patch.dict(os.environ, {}, clear=True):
        engine = EmbeddingEngine(api_key=None)
        assert engine._client is None

        with pytest.raises(ValueError, match="Gemini API key missing"):
            engine.embed_query("test query")

        with pytest.raises(ValueError, match="Gemini API key missing"):
            engine.embed_documents([_make_document("def foo(): pass")])


def test_embed_documents_adds_embeddings(mock_genai_client: MagicMock) -> None:
    """Test embed_documents populates embedding field on all documents."""
    engine = EmbeddingEngine(client=mock_genai_client)
    documents = [
        _make_document("def alpha(): pass"),
        _make_document("def beta(): pass", file_name="utils.py"),
    ]
    embedded = engine.embed_documents(documents)

    assert len(embedded) == 2
    assert all(doc.embedding is not None for doc in embedded)
    assert all(len(doc.embedding) == EMBEDDING_DIMENSION for doc in embedded)
    mock_genai_client.models.embed_content.assert_called_once()


def test_embed_documents_preserves_content_and_immutability(mock_genai_client: MagicMock) -> None:
    """Test embed_documents does not mutate original documents and preserves all metadata."""
    engine = EmbeddingEngine(client=mock_genai_client)
    original = _make_document("def login(): pass")
    embedded = engine.embed_documents([original])[0]

    assert original.embedding is None  # original unmutated
    assert embedded.embedding is not None
    assert embedded.content == original.content
    assert embedded.file_name == original.file_name
    assert embedded.function_name == original.function_name
    assert embedded.start_line == original.start_line
    assert embedded.end_line == original.end_line


def test_embed_documents_empty_list(mock_genai_client: MagicMock) -> None:
    """Test embed_documents with empty input returns empty list without calling API."""
    engine = EmbeddingEngine(client=mock_genai_client)
    assert engine.embed_documents([]) == []
    mock_genai_client.models.embed_content.assert_not_called()


def test_embed_documents_batching(mock_genai_client: MagicMock) -> None:
    """Test batching chunk requests into bounded chunks."""
    engine = EmbeddingEngine(client=mock_genai_client)
    documents = [_make_document(f"def func_{i}(): pass") for i in range(120)]

    embedded = engine.embed_documents(documents, batch_size=50)

    assert len(embedded) == 120
    assert mock_genai_client.models.embed_content.call_count == 3


def test_embed_query_success(mock_genai_client: MagicMock) -> None:
    """Test embed_query returns vector of correct dimension."""
    engine = EmbeddingEngine(client=mock_genai_client)
    vector = engine.embed_query("Where is auth implemented?")

    assert len(vector) == EMBEDDING_DIMENSION
    assert isinstance(vector, list)
    assert all(isinstance(val, float) for val in vector)


def test_embed_query_empty_raises(mock_genai_client: MagicMock) -> None:
    """Test embed_query with empty query raises ValueError."""
    engine = EmbeddingEngine(client=mock_genai_client)
    with pytest.raises(ValueError, match="Query string must not be empty"):
        engine.embed_query("   ")


def test_api_failure_handling_and_retry(mock_genai_client: MagicMock) -> None:
    """Test retry on transient error and eventual exception on persistent failure."""
    error_response = genai.errors.APIError(503, {"error": {"message": "Service unavailable", "code": 503}})
    mock_genai_client.models.embed_content.side_effect = error_response

    engine = EmbeddingEngine(client=mock_genai_client)

    with patch("time.sleep", return_value=None):
        with pytest.raises(genai.errors.APIError):
            engine.embed_query("test query")

    assert mock_genai_client.models.embed_content.call_count == 3


def test_faiss_vector_store_compatibility(mock_genai_client: MagicMock) -> None:
    """Test embeddings generated by Gemini EmbeddingEngine integrate seamlessly with FAISSVectorStore."""
    engine = EmbeddingEngine(client=mock_genai_client)
    documents = [
        _make_document("def login(): pass", file_name="auth.py"),
        _make_document("def logout(): pass", file_name="auth.py"),
    ]
    embedded_docs = engine.embed_documents(documents)

    store = FAISSVectorStore()
    store.build_index(embedded_docs)

    assert store.total_documents == 2
    assert store.embedding_dimension == EMBEDDING_DIMENSION

    query_vector = engine.embed_query("login user")
    results = store.search(query_vector, k=2)

    assert len(results) == 2
    assert isinstance(results[0][0], Document)
    assert isinstance(results[0][1], float)

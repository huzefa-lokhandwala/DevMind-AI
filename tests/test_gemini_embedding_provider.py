"""Comprehensive tests for GeminiEmbeddingProvider and Phase 3B production embedding architecture.

All tests mock Google GenAI API calls. Zero real or paid network calls are performed.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest
import numpy as np

from app.embeddings.embedding_engine import (
    EmbeddingEngine,
    GeminiEmbeddingProvider,
    LocalEmbeddingProvider,
)
from app.models.document import Document
from app.vector_store.faiss_store import FAISSVectorStore
from app.services.rag_service import RAGService, RepositoryNotIndexedError
from app.db.crud import create_or_update_repository, get_repository_by_name
from app.db.models import RepositoryModel, FileModel, ChunkModel
from google import genai
from google.genai import types, errors


def _create_doc(content: str, path: str = "src/main.py") -> Document:
    return Document(
        content=content,
        file_name=path.split("/")[-1],
        file_path=path,
        extension=".py",
        repository_name="test_repo",
        chunk_type="function",
        function_name="sample_fn",
        start_line=1,
        end_line=10,
    )


def _mock_genai_response(texts: list[str] | str, dim: int = 768) -> types.EmbedContentResponse:
    count = 1 if isinstance(texts, str) else len(texts)
    embeddings = [
        types.ContentEmbedding(values=[float(i + 1) * 0.01 + idx * 0.0001 for idx in range(dim)])
        for i in range(count)
    ]
    return types.EmbedContentResponse(embeddings=embeddings)


# ============================================================================
# 1. Initialization & Defaults
# ============================================================================

def test_gemini_provider_defaults() -> None:
    """Test default model (gemini-embedding-2), dimension (768), batch size (50)."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}, clear=True):
        provider = GeminiEmbeddingProvider(client=MagicMock())
        assert provider.model_name == "gemini-embedding-2"
        assert provider.embedding_dimension == 768
        assert provider.batch_size == 50


def test_gemini_provider_env_overrides() -> None:
    """Test environment variable overrides for model, dimension, and batch size."""
    env = {
        "GEMINI_API_KEY": "test_key",
        "GEMINI_EMBEDDING_MODEL": "custom-embed-model",
        "GEMINI_EMBEDDING_DIMENSION": "1536",
        "GEMINI_EMBEDDING_BATCH_SIZE": "25",
    }
    with patch.dict(os.environ, env, clear=True):
        provider = GeminiEmbeddingProvider(client=MagicMock())
        assert provider.model_name == "custom-embed-model"
        assert provider.embedding_dimension == 1536
        assert provider.batch_size == 25


# ============================================================================
# 2. 768-Dimensional Output & Task Types
# ============================================================================

def test_gemini_provider_embed_documents_768d_and_task_type() -> None:
    """Test embed_documents outputs 768d vectors and uses RETRIEVAL_DOCUMENT."""
    mock_client = MagicMock()
    captured_configs = []

    def fake_embed(*args, **kwargs):
        captured_configs.append(kwargs.get("config"))
        contents = kwargs.get("contents")
        return _mock_genai_response(contents, dim=768)

    mock_client.models.embed_content.side_effect = fake_embed

    provider = GeminiEmbeddingProvider(api_key="mock_key", client=mock_client)
    docs = [_create_doc("chunk 1"), _create_doc("chunk 2")]
    embedded = provider.embed_documents(docs)

    assert len(embedded) == 2
    for doc in embedded:
        assert doc.embedding is not None
        assert len(doc.embedding) == 768
        assert isinstance(doc.embedding[0], float)

    assert len(captured_configs) == 1
    assert captured_configs[0].task_type == "RETRIEVAL_DOCUMENT"
    assert captured_configs[0].output_dimensionality == 768


def test_gemini_provider_embed_query_768d_and_task_type() -> None:
    """Test embed_query outputs 768d vector and uses RETRIEVAL_QUERY."""
    mock_client = MagicMock()
    captured_configs = []

    def fake_embed(*args, **kwargs):
        captured_configs.append(kwargs.get("config"))
        return _mock_genai_response(kwargs.get("contents"), dim=768)

    mock_client.models.embed_content.side_effect = fake_embed

    provider = GeminiEmbeddingProvider(api_key="mock_key", client=mock_client)
    query_vec = provider.embed_query("how does authentication work?")

    assert len(query_vec) == 768
    assert len(captured_configs) == 1
    assert captured_configs[0].task_type == "RETRIEVAL_QUERY"
    assert captured_configs[0].output_dimensionality == 768


# ============================================================================
# 3. Multi-Text Embedding, Count Verification, & Ordering
# ============================================================================

def test_gemini_provider_multi_text_embedding_ordering_and_count() -> None:
    """Verify input chunk N strictly corresponds to embedding N in order."""
    mock_client = MagicMock()

    def fake_embed(*args, **kwargs):
        contents = kwargs.get("contents")
        embeddings = []
        for idx, text in enumerate(contents):
            # Stamp unique marker in vector based on text content
            raw_text = text.parts[0].text if hasattr(text, "parts") else str(text)
            marker = float(raw_text.split()[-1])
            vec = [marker] * 768
            embeddings.append(types.ContentEmbedding(values=vec))
        return types.EmbedContentResponse(embeddings=embeddings)

    mock_client.models.embed_content.side_effect = fake_embed

    provider = GeminiEmbeddingProvider(api_key="mock_key", client=mock_client)
    docs = [_create_doc(f"document item {i}") for i in range(10)]
    embedded = provider.embed_documents(docs)

    assert len(embedded) == 10
    for i, doc in enumerate(embedded):
        assert doc.embedding[0] == float(i)


# ============================================================================
# 4. Batch Splitting
# ============================================================================

def test_gemini_provider_batch_splitting() -> None:
    """Verify provider splits requests exceeding batch_size (e.g. 100 docs into 2x50 calls)."""
    mock_client = MagicMock()
    call_counts = []

    def fake_embed(*args, **kwargs):
        contents = kwargs.get("contents")
        call_counts.append(len(contents))
        return _mock_genai_response(contents, dim=768)

    mock_client.models.embed_content.side_effect = fake_embed

    provider = GeminiEmbeddingProvider(api_key="mock_key", client=mock_client, batch_size=50)
    docs = [_create_doc(f"doc {i}") for i in range(105)]
    embedded = provider.embed_documents(docs)

    assert len(embedded) == 105
    assert call_counts == [50, 50, 5]
    assert mock_client.models.embed_content.call_count == 3


# ============================================================================
# 5. Response Validation & Mismatches
# ============================================================================

def test_gemini_provider_count_mismatch_raises() -> None:
    """Provider must raise clean error when API returns fewer embeddings than inputs."""
    mock_client = MagicMock()
    # Return 1 embedding for 2 input texts
    mock_client.models.embed_content.return_value = types.EmbedContentResponse(
        embeddings=[types.ContentEmbedding(values=[0.1] * 768)]
    )

    provider = GeminiEmbeddingProvider(api_key="mock_key", client=mock_client)
    docs = [_create_doc("doc 1"), _create_doc("doc 2")]
    with pytest.raises(RuntimeError, match="returned 1 embeddings for 2 input texts"):
        provider.embed_documents(docs)


def test_gemini_provider_dimension_mismatch_raises() -> None:
    """Provider must raise clean error when API returns vectors with incorrect dimensions."""
    mock_client = MagicMock()
    # Return 384d vectors instead of 768d
    mock_client.models.embed_content.return_value = types.EmbedContentResponse(
        embeddings=[types.ContentEmbedding(values=[0.1] * 384)]
    )

    provider = GeminiEmbeddingProvider(api_key="mock_key", client=mock_client, dimension=768)
    docs = [_create_doc("doc 1")]
    with pytest.raises(ValueError, match="does not match expected dimension"):
        provider.embed_documents(docs)


def test_gemini_provider_malformed_response_raises() -> None:
    """Provider must handle empty or None embeddings gracefully."""
    mock_client = MagicMock()
    mock_client.models.embed_content.return_value = types.EmbedContentResponse(embeddings=None)

    provider = GeminiEmbeddingProvider(api_key="mock_key", client=mock_client)
    with pytest.raises(RuntimeError, match="returned no embeddings"):
        provider.embed_query("query text")


# ============================================================================
# 6. Error Handling & Retries (429, 5xx, Timeouts, Auth)
# ============================================================================

def test_gemini_provider_transient_429_retry_success() -> None:
    """Transient 429 rate limit is retried with backoff and succeeds."""
    mock_client = MagicMock()
    attempts = 0

    def fake_embed(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise errors.APIError(429, {"error": {"message": "Resource exhausted"}})
        return _mock_genai_response(kwargs.get("contents"), dim=768)

    mock_client.models.embed_content.side_effect = fake_embed

    with patch("time.sleep") as mock_sleep:
        provider = GeminiEmbeddingProvider(api_key="mock_key", client=mock_client)
        vec = provider.embed_query("query")
        assert len(vec) == 768
        assert attempts == 2
        mock_sleep.assert_called_once()


def test_gemini_provider_transient_503_retry_success() -> None:
    """Transient 503 Service Unavailable is retried with backoff and succeeds."""
    mock_client = MagicMock()
    attempts = 0

    def fake_embed(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise errors.APIError(503, {"error": {"message": "Backend unavailable"}})
        return _mock_genai_response(kwargs.get("contents"), dim=768)

    mock_client.models.embed_content.side_effect = fake_embed

    with patch("time.sleep"):
        provider = GeminiEmbeddingProvider(api_key="mock_key", client=mock_client)
        vec = provider.embed_query("query")
        assert len(vec) == 768
        assert attempts == 2


def test_gemini_provider_authentication_failure_does_not_retry() -> None:
    """401/403 Authentication failure fails fast without wasteful retries."""
    mock_client = MagicMock()
    mock_client.models.embed_content.side_effect = errors.APIError(
        403, {"error": {"message": "API key invalid"}}
    )

    with patch("time.sleep") as mock_sleep:
        provider = GeminiEmbeddingProvider(api_key="secret_invalid_key", client=mock_client)
        with pytest.raises(PermissionError, match="authentication failed"):
            provider.embed_query("query")
        # Ensure sleep was never called
        mock_sleep.assert_not_called()


def test_gemini_provider_missing_key_error() -> None:
    """Initializing unauthenticated without key raises clean error on API call."""
    with patch.dict(os.environ, {}, clear=True):
        provider = GeminiEmbeddingProvider(api_key=None, client=None)
        with pytest.raises(ValueError, match="Gemini API key missing"):
            provider.embed_query("query")


def test_gemini_provider_sanitizes_credentials_in_logs(caplog) -> None:
    """Verify secret API keys are never logged in plaintext."""
    import logging
    mock_client = MagicMock()
    secret_key = "AIzaSySecretKey123456789"
    mock_client.models.embed_content.side_effect = Exception(f"Failed with key={secret_key}")

    provider = GeminiEmbeddingProvider(api_key=secret_key, client=mock_client)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            provider.embed_query("query")

    for record in caplog.records:
        assert secret_key not in record.message


# ============================================================================
# 7. Query/Document Provider & Dimension Consistency
# ============================================================================

def test_rag_service_dimension_mismatch_prevents_query() -> None:
    """Querying a repository indexed in 384d with a 768d engine raises RepositoryNotIndexedError."""
    mock_gemini_client = MagicMock()
    mock_gemini_client.models.embed_content.return_value = _mock_genai_response("query", dim=768)
    engine_768 = EmbeddingEngine(provider="gemini", client=mock_gemini_client)

    service = RAGService(embedding_engine=engine_768, llm_provider=MagicMock())
    service.indexed_repository_name = "legacy_repo"

    # Manually configure vector store to 384d
    store_384 = FAISSVectorStore(dimension=384)
    doc = _create_doc("code")
    doc.embedding = [0.1] * 384
    store_384.build_index([doc])

    service.vector_store = store_384
    from app.retrieval.retriever import Retriever
    service.retriever = Retriever(engine_768, store_384)

    with pytest.raises(RepositoryNotIndexedError, match="Vector dimension mismatch"):
        service.query("where in this repository is the authentication router defined?")


def test_rag_service_provider_metadata_mismatch_prevents_query() -> None:
    """Querying a repository indexed with 'local' provider using 'gemini' raises clean error."""
    mock_gemini_client = MagicMock()
    mock_gemini_client.models.embed_content.return_value = _mock_genai_response("query", dim=768)
    engine_768 = EmbeddingEngine(provider="gemini", client=mock_gemini_client)

    mock_db = MagicMock()
    repo_record = MagicMock(spec=RepositoryModel)
    repo_record.name = "my_app"
    repo_record.embedding_provider = "local"
    repo_record.embedding_dimension = 384

    service = RAGService(embedding_engine=engine_768, db_session=mock_db, llm_provider=MagicMock())
    service.indexed_repository_name = "my_app"

    store_768 = FAISSVectorStore(dimension=768)
    doc = _create_doc("code")
    doc.embedding = [0.1] * 768
    store_768.build_index([doc])
    service.vector_store = store_768
    from app.retrieval.retriever import Retriever
    service.retriever = Retriever(engine_768, store_768)

    with patch("app.services.rag_service.get_repository_by_name", return_value=repo_record):
        with pytest.raises(RepositoryNotIndexedError, match="was indexed with provider 'local'"):
            service.query("where in this repository is the authentication router defined?")


# ============================================================================
# 8. FAISS Dimension Validation
# ============================================================================

def test_faiss_rejects_mismatched_query_vector() -> None:
    """FAISSVectorStore rejects query vectors whose dimensionality does not match index."""
    store = FAISSVectorStore(dimension=768)
    doc = _create_doc("auth code")
    doc.embedding = [0.05] * 768
    store.build_index([doc])

    # Search with 384d vector must fail
    query_384 = [0.1] * 384
    with pytest.raises(ValueError, match="does not match FAISS index dimension"):
        store.search(query_384, k=1)


# ============================================================================
# 9. Repository Metadata Persistence
# ============================================================================

def test_create_or_update_repository_persists_embedding_metadata() -> None:
    """Verify create_or_update_repository saves embedding_provider, embedding_model, embedding_dimension."""
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    repo = create_or_update_repository(
        db=mock_db,
        name="prod_repo",
        source="/path/to/prod_repo",
        source_type="local",
        status="indexed",
        embedding_provider="gemini",
        embedding_model="gemini-embedding-2",
        embedding_dimension=768,
    )

    mock_db.add.assert_called_once()
    added_obj = mock_db.add.call_args[0][0]
    assert added_obj.embedding_provider == "gemini"
    assert added_obj.embedding_model == "gemini-embedding-2"
    assert added_obj.embedding_dimension == 768


# ============================================================================
# 10. Migration 004 Verification
# ============================================================================

def test_migration_004_structure() -> None:
    """Verify revision 004 properties and upgrade/downgrade definitions."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("mig_004", "alembic/versions/004_embedding_dim_768.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.revision == "004_embedding_dim_768"
    assert mod.down_revision == "003_embedding_dim_384"
    assert hasattr(mod, "upgrade")
    assert hasattr(mod, "downgrade")

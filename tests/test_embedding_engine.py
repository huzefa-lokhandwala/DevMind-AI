"""Tests for the embedding engine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.embeddings.embedding_engine import EmbeddingEngine
from app.models import Document

EMBEDDING_DIMENSION = 384


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
def mock_sentence_transformer() -> MagicMock:
    model = MagicMock()
    model.get_embedding_dimension.return_value = EMBEDDING_DIMENSION
    model.get_sentence_embedding_dimension.return_value = EMBEDDING_DIMENSION

    def encode_side_effect(texts: list[str] | str, **_kwargs: object) -> np.ndarray:
        if isinstance(texts, str):
            return np.array([0.1] * EMBEDDING_DIMENSION)
        return np.array([[0.1 * (index + 1)] * EMBEDDING_DIMENSION for index in range(len(texts))])

    model.encode.side_effect = encode_side_effect
    return model


@patch("app.embeddings.embedding_engine.SentenceTransformer")
def test_embed_documents_adds_embeddings(
    mock_transformer_cls: MagicMock,
    mock_sentence_transformer: MagicMock,
) -> None:
    mock_transformer_cls.return_value = mock_sentence_transformer

    engine = EmbeddingEngine()
    documents = [
        _make_document("def alpha(): pass"),
        _make_document("def beta(): pass", file_name="utils.py"),
    ]
    embedded = engine.embed_documents(documents)

    assert len(embedded) == 2
    assert all(doc.embedding is not None for doc in embedded)
    assert all(len(doc.embedding) == EMBEDDING_DIMENSION for doc in embedded)
    mock_transformer_cls.assert_called_once_with(EmbeddingEngine.DEFAULT_MODEL_NAME)
    mock_sentence_transformer.encode.assert_called_once()


@patch("app.embeddings.embedding_engine.SentenceTransformer")
def test_embed_documents_preserves_content(
    mock_transformer_cls: MagicMock,
    mock_sentence_transformer: MagicMock,
) -> None:
    mock_transformer_cls.return_value = mock_sentence_transformer

    engine = EmbeddingEngine()
    original = _make_document("def login(): pass")
    embedded = engine.embed_documents([original])[0]

    assert embedded.content == original.content
    assert embedded.file_name == original.file_name
    assert embedded.function_name == original.function_name
    assert embedded.start_line == original.start_line
    assert embedded.end_line == original.end_line


@patch("app.embeddings.embedding_engine.SentenceTransformer")
def test_embed_documents_empty_list(
    mock_transformer_cls: MagicMock,
    mock_sentence_transformer: MagicMock,
) -> None:
    mock_transformer_cls.return_value = mock_sentence_transformer

    engine = EmbeddingEngine()
    assert engine.embed_documents([]) == []
    mock_sentence_transformer.encode.assert_not_called()


@patch("app.embeddings.embedding_engine.SentenceTransformer")
def test_model_loaded_once(
    mock_transformer_cls: MagicMock,
    mock_sentence_transformer: MagicMock,
) -> None:
    mock_transformer_cls.return_value = mock_sentence_transformer

    engine = EmbeddingEngine()
    documents = [_make_document("def alpha(): pass")]
    engine.embed_documents(documents)
    engine.embed_documents(documents)

    mock_transformer_cls.assert_called_once()


@patch("app.embeddings.embedding_engine.SentenceTransformer")
def test_default_model_name(mock_transformer_cls: MagicMock) -> None:
    mock_model = MagicMock()
    mock_model.get_embedding_dimension.return_value = EMBEDDING_DIMENSION
    mock_transformer_cls.return_value = mock_model

    engine = EmbeddingEngine()

    assert engine.model_name == "BAAI/bge-small-en-v1.5"
    assert engine.embedding_dimension == EMBEDDING_DIMENSION


def test_live_embedding_engine_generates_vectors() -> None:
    """Integration test using the real sentence-transformers model."""
    engine = EmbeddingEngine()
    documents = [_make_document('def login(username: str) -> None:\n    """JWT auth."""\n')]

    embedded = engine.embed_documents(documents)

    assert len(embedded) == 1
    assert embedded[0].embedding is not None
    assert len(embedded[0].embedding) == engine.embedding_dimension
    assert engine.embedding_dimension == EMBEDDING_DIMENSION

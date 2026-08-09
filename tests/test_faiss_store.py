"""Unit tests for FAISSVectorStore."""

from __future__ import annotations

import pytest

from app.models import Document
from app.vector_store.faiss_store import FAISSVectorStore

DIMENSION = 4


def _make_embedded_doc(
    content: str,
    embedding: list[float],
    *,
    file_name: str = "auth.py",
    function_name: str | None = "login",
    start_line: int = 1,
    end_line: int = 10,
) -> Document:
    return Document(
        content=content,
        file_name=file_name,
        file_path=f"/tmp/{file_name}",
        extension=".py",
        repository_name="sample_project",
        chunk_type="function",
        function_name=function_name,
        start_line=start_line,
        end_line=end_line,
        embedding=embedding,
    )


def test_build_index_and_search() -> None:
    doc1 = _make_embedded_doc("def login(): pass", [1.0, 0.0, 0.0, 0.0], function_name="login")
    doc2 = _make_embedded_doc("def logout(): pass", [0.0, 1.0, 0.0, 0.0], function_name="logout")

    store = FAISSVectorStore()
    store.build_index([doc1, doc2])

    assert store.total_documents == 2
    assert store.embedding_dimension == DIMENSION

    # Query vector close to doc1 ([1, 0, 0, 0])
    results = store.search([0.9, 0.1, 0.0, 0.0], k=2)

    assert len(results) == 2
    matched_doc, score1 = results[0]
    _, score2 = results[1]

    assert matched_doc.function_name == "login"
    assert isinstance(score1, float)
    assert score1 > score2


def test_add_documents_appends() -> None:
    doc1 = _make_embedded_doc("def alpha(): pass", [1.0, 0.0, 0.0, 0.0])
    doc2 = _make_embedded_doc("def beta(): pass", [0.0, 1.0, 0.0, 0.0])

    store = FAISSVectorStore()
    store.build_index([doc1])
    assert store.total_documents == 1

    store.add_documents([doc2])
    assert store.total_documents == 2

    results = store.search([0.0, 1.0, 0.0, 0.0], k=1)
    assert len(results) == 1
    matched_doc, score = results[0]
    assert matched_doc.function_name == "login"
    assert matched_doc.content == "def beta(): pass"


def test_search_empty_store() -> None:
    store = FAISSVectorStore(dimension=DIMENSION)
    assert store.search([1.0, 0.0, 0.0, 0.0]) == []


def test_missing_embedding_raises() -> None:
    doc_no_emb = Document(
        content="pass",
        file_name="empty.py",
        file_path="/tmp/empty.py",
        extension=".py",
        repository_name="sample",
    )
    store = FAISSVectorStore()
    with pytest.raises(ValueError, match="has no embedding"):
        store.build_index([doc_no_emb])


def test_dimension_mismatch_raises() -> None:
    doc = _make_embedded_doc("pass", [1.0, 0.0, 0.0, 0.0])
    store = FAISSVectorStore()
    store.build_index([doc])

    # Search with 3D vector instead of 4D
    with pytest.raises(ValueError, match="Query embedding dimension"):
        store.search([1.0, 0.0, 0.0], k=1)


def test_preserve_document_metadata() -> None:
    original = _make_embedded_doc(
        content="def login(): pass",
        embedding=[0.5, 0.5, 0.5, 0.5],
        file_name="auth.py",
        function_name="login",
        start_line=5,
        end_line=12,
    )
    store = FAISSVectorStore()
    store.build_index([original])

    results = store.search([0.5, 0.5, 0.5, 0.5], k=1)
    matched_doc, score = results[0]

    assert matched_doc.content == original.content
    assert matched_doc.file_name == original.file_name
    assert matched_doc.repository_name == original.repository_name
    assert matched_doc.function_name == original.function_name
    assert matched_doc.start_line == 5
    assert matched_doc.end_line == 12
    assert isinstance(score, float)

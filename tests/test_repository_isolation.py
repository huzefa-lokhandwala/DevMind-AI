"""Repository isolation tests proving no cross-tenant context contamination."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.embeddings.embedding_engine import EmbeddingEngine
from app.graph.code_graph import CodeGraph, CodeNode
from app.models import Document
from app.retrieval.config import RetrievalConfig
from app.retrieval.retriever import Retriever
from app.vector_store.faiss_store import FAISSVectorStore


def _make_document(
    content: str,
    file_name: str,
    file_path: str,
    repository_name: str,
    start_line: int = 1,
    end_line: int = 20,
) -> Document:
    return Document(
        content=content,
        file_name=file_name,
        file_path=file_path,
        extension="." + file_name.rsplit(".", 1)[-1],
        repository_name=repository_name,
        chunk_type="file",
        start_line=start_line,
        end_line=end_line,
    )


def test_repository_isolation_filtering_in_vector_store() -> None:
    """FAISSVectorStore.search with repository_name filter isolates results by repository."""
    doc_repo_a = _make_document("export class AuthA {}", "auth.ts", "src/auth.ts", repository_name="repo_a")
    doc_repo_b = _make_document("export class AuthB {}", "auth.ts", "src/auth.ts", repository_name="repo_b")

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_documents.return_value = [
        _make_document("export class AuthA {}", "auth.ts", "src/auth.ts", repository_name="repo_a"),
        _make_document("export class AuthB {}", "auth.ts", "src/auth.ts", repository_name="repo_b"),
    ]
    doc_repo_a.embedding = [0.1] * 384
    doc_repo_b.embedding = [0.1] * 384

    store = FAISSVectorStore()
    store.build_index([doc_repo_a, doc_repo_b])

    # Search for repo_a specifically
    query_emb = [0.1] * 384
    matches_a = store.search(query_emb, k=5, repository_name="repo_a")

    assert len(matches_a) == 1
    assert matches_a[0][0].repository_name == "repo_a"

    # Search for repo_b specifically
    matches_b = store.search(query_emb, k=5, repository_name="repo_b")
    assert len(matches_b) == 1
    assert matches_b[0][0].repository_name == "repo_b"


def test_repository_isolation_in_retriever() -> None:
    """Retriever.retrieve with repository_name filter guarantees only target repo chunks are returned."""
    doc_repo_a = _make_document("export class EngineA {}", "engine.ts", "lib/engine.ts", repository_name="repo_a")
    doc_repo_b = _make_document("export class EngineB {}", "engine.ts", "lib/engine.ts", repository_name="repo_b")
    doc_repo_a.embedding = [0.1] * 384
    doc_repo_b.embedding = [0.1] * 384

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1] * 384

    store = FAISSVectorStore()
    store.build_index([doc_repo_a, doc_repo_b])

    retriever = Retriever(mock_engine, store, config=RetrievalConfig(similarity_threshold=0.0))
    results = retriever.retrieve("Where is Engine?", k=5, repository_name="repo_a")

    assert all(r.document.repository_name == "repo_a" for r in results)

"""Unit and integration tests for bounded streaming incremental repository indexing."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from app.embeddings.embedding_engine import EmbeddingEngine
from app.graph.code_graph import CodeGraph
from app.loaders.repository_loader import RepositoryLoader
from app.models.document import Document
from app.services.rag_service import (
    IndexingMemoryExceededError,
    InvalidRepositoryError,
    RAGService,
)
from app.vector_store.faiss_store import FAISSVectorStore


@pytest.fixture
def synthetic_repo(tmp_path: Path) -> Path:
    """Create a synthetic multi-file repository fixture."""
    repo = tmp_path / "synthetic_repo"
    repo.mkdir()

    # Create 30 Python files with functions and imports
    for i in range(1, 31):
        file_path = repo / f"module_{i:02d}.py"
        file_path.write_text(
            f"from module_{(i % 30) + 1:02d} import helper_{(i % 30) + 1:02d}\n\n"
            f"def process_data_{i:02d}(value: int) -> int:\n"
            f"    return value * {i}\n\n"
            f"def helper_{i:02d}() -> str:\n"
            f"    return 'data_{i}'\n",
            encoding="utf-8",
        )

    # Add ignored directory and lockfiles
    node_modules = repo / "node_modules"
    node_modules.mkdir()
    (node_modules / "pkg.js").write_text("console.log('ignored');", encoding="utf-8")

    (repo / "package-lock.json").write_text('{"lockfileVersion": 3}', encoding="utf-8")

    return repo


def test_repository_loader_iter_file_paths_and_batches(synthetic_repo: Path) -> None:
    """Verify iter_file_paths returns discovered files and iter_batches yields bounded batches."""
    loader = RepositoryLoader(synthetic_repo)

    paths = loader.iter_file_paths()
    assert len(paths) == 30
    assert all(p.suffix == ".py" for p in paths)
    assert not any("node_modules" in str(p) for p in paths)

    batches = list(loader.iter_batches(batch_size=5))
    assert len(batches) == 6  # 30 files / 5 per batch = 6 batches
    assert all(len(b) == 5 for b in batches)

    all_docs = loader.load_files()
    assert len(all_docs) == 30


def test_codegraph_incremental_add_documents() -> None:
    """Verify CodeGraph builds incrementally when fed batches of Documents."""
    graph = CodeGraph()

    batch1 = [
        Document(
            content="def auth_user(): pass",
            file_name="auth.py",
            file_path="src/auth.py",
            extension=".py",
            repository_name="test_repo",
            function_name="auth_user",
            exported_symbols=["auth_user"],
        )
    ]
    graph.add_documents(batch1)
    assert "src/auth.py" in graph.nodes
    assert "auth_user" in graph._symbol_to_file

    batch2 = [
        Document(
            content="import auth\nauth_user()",
            file_name="main.py",
            file_path="src/main.py",
            extension=".py",
            repository_name="test_repo",
            function_calls=["auth_user"],
        )
    ]
    graph.add_documents(batch2)
    assert "src/main.py" in graph.nodes
    assert len(graph.edges) >= 1


def test_rag_service_incremental_indexing_success(synthetic_repo: Path) -> None:
    """Verify RAGService indexes multi-file repository in streaming batches without error."""
    mock_client = MagicMock()

    def embed_side_effect(model: str, contents: str | list[str], config: types.EmbedContentConfig | None = None) -> types.EmbedContentResponse:
        dim = config.output_dimensionality if config and config.output_dimensionality else 384
        count = 1 if isinstance(contents, str) else len(contents)
        return types.EmbedContentResponse(
            embeddings=[types.ContentEmbedding(values=[0.05] * dim) for _ in range(count)]
        )

    mock_client.models.embed_content.side_effect = embed_side_effect
    embedding_engine = EmbeddingEngine(provider="gemini", client=mock_client, dimension=384)

    service = RAGService(
        embedding_engine=embedding_engine,
        process_batch_size=5,
        memory_limit_mb=500.0,
    )

    result = service.index_repository(str(synthetic_repo))

    assert result["repository"] == "synthetic_repo"
    assert result["files_loaded"] == 30
    assert result["chunks_created"] >= 60  # 2 functions per file
    assert result["embeddings_created"] >= 60
    assert result["status"] == "indexed"
    assert service.is_indexed is True
    assert service.vector_store.total_documents >= 60


def test_rag_service_circuit_breaker_triggers(synthetic_repo: Path) -> None:
    """Verify RAGService aborts with IndexingMemoryExceededError if RSS exceeds threshold."""
    service = RAGService(
        process_batch_size=5,
        memory_limit_mb=0.01,  # Impossibly low limit to guarantee triggering
    )

    with pytest.raises(IndexingMemoryExceededError) as exc_info:
        service.index_repository(str(synthetic_repo))

    assert "exceeded safety" in str(exc_info.value)

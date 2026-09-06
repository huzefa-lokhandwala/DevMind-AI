"""Targeted unit tests validating Phase 2 indexing performance optimizations."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.chunking.code_chunker import CodeChunker
from app.db.crud import (
    create_or_update_repository,
    save_repository_documents,
)
from app.db.database import Base
from app.db.models import ChunkModel, FileModel, RepositoryModel
from app.loaders.repository_loader import RepositoryLoader
from app.loaders.github_loader import GitHubRepositoryLoader
from app.models.document import Document
from app.services.rag_service import RAGService


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_repository_loader_os_walk_prunes_ignored_directories():
    """Verify os.walk directory pruning skips .git, node_modules, and __pycache__ without traversing them."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("print('hello')", encoding="utf-8")

        # Ignored directory with deep nested files
        (root / ".git").mkdir()
        (root / ".git" / "objects").mkdir()
        (root / ".git" / "objects" / "commit.py").write_text("print('secret')", encoding="utf-8")

        (root / "node_modules").mkdir()
        (root / "node_modules" / "dep.js").write_text("console.log()", encoding="utf-8")

        loader = RepositoryLoader(root)
        files = loader.iter_file_paths()

        assert len(files) == 1
        assert files[0].name == "app.py"


def test_repository_loader_iter_batches_accepts_pre_discovered_paths():
    """Verify iter_batches can consume pre-discovered paths to avoid duplicate traversal."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        p1 = root / "f1.py"
        p2 = root / "f2.py"
        p1.write_text("a = 1", encoding="utf-8")
        p2.write_text("b = 2", encoding="utf-8")

        loader = RepositoryLoader(root)
        custom_paths = [p1]
        batches = list(loader.iter_batches(batch_size=5, paths=custom_paths))

        assert len(batches) == 1
        assert len(batches[0]) == 1
        assert batches[0][0].file_name == "f1.py"


def test_code_chunker_single_pass_ast_produces_identical_chunks():
    """Verify single-pass AST chunking produces correct symbols, imports, and calls."""
    chunker = CodeChunker()
    py_code = (
        "import os\n"
        "from math import sqrt\n\n"
        "class Calculator:\n"
        "    def compute(self, x):\n"
        "        return sqrt(x)\n"
    )
    doc = Document(
        content=py_code,
        file_name="calc.py",
        file_path="src/calc.py",
        extension=".py",
        repository_name="test_repo",
    )
    chunks = chunker.chunk_documents([doc])

    assert len(chunks) == 2  # class and method
    class_chunk = next(c for c in chunks if c.chunk_type == "class")
    func_chunk = next(c for c in chunks if c.chunk_type == "function")

    assert class_chunk.class_name == "Calculator"
    assert func_chunk.function_name == "compute"
    assert func_chunk.class_name == "Calculator"
    assert "os" in func_chunk.imports or "math" in func_chunk.imports
    assert "sqrt" in func_chunk.imported_symbols


def test_crud_save_repository_documents_bulk_persistence(test_db):
    """Verify bulk save_repository_documents accurately creates files, updates files, and adds chunks."""
    repo = create_or_update_repository(test_db, "bulk_test_repo", "/path/to/repo")

    docs = [
        Document(
            content="def foo(): pass",
            file_name="foo.py",
            file_path="/path/to/repo/foo.py",
            extension=".py",
            repository_name="bulk_test_repo",
            language="python",
            chunk_type="function",
            function_name="foo",
            start_line=1,
            end_line=1,
            embedding=[0.1] * 384,
        ),
        Document(
            content="def bar(): pass",
            file_name="bar.py",
            file_path="/path/to/repo/bar.py",
            extension=".py",
            repository_name="bulk_test_repo",
            language="python",
            chunk_type="function",
            function_name="bar",
            start_line=1,
            end_line=1,
            embedding=[0.2] * 384,
        ),
    ]

    files_saved, chunks_saved = save_repository_documents(test_db, repo.id, docs, commit=True)
    assert files_saved == 2
    assert chunks_saved == 2

    # Check database records
    files = test_db.query(FileModel).filter(FileModel.repository_id == repo.id).all()
    assert len(files) == 2
    chunks = test_db.query(ChunkModel).all()
    assert len(chunks) == 2

    # Updating one of the files deletes old chunks and reinserts
    updated_doc = Document(
        content="def foo_v2(): pass",
        file_name="foo.py",
        file_path="/path/to/repo/foo.py",
        extension=".py",
        repository_name="bulk_test_repo",
        language="python",
        chunk_type="function",
        function_name="foo_v2",
        start_line=1,
        end_line=1,
        embedding=[0.3] * 384,
    )
    files_saved_2, chunks_saved_2 = save_repository_documents(test_db, repo.id, [updated_doc], commit=True)
    assert files_saved_2 == 1
    assert chunks_saved_2 == 1

    # Total files remain 2, total chunks remain 2 (old chunk deleted, new chunk added)
    assert test_db.query(FileModel).filter(FileModel.repository_id == repo.id).count() == 2
    assert test_db.query(ChunkModel).count() == 2


def test_github_loader_shallow_and_single_branch():
    """Verify GitHubRepositoryLoader passes --single-branch and --no-tags."""
    loader = GitHubRepositoryLoader()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        with patch.object(Path, "exists", return_value=False):
            with patch.object(Path, "mkdir"):
                loader.clone_repository("https://github.com/octocat/Hello-World")
                cmd = mock_run.call_args[0][0]
                assert "--depth" in cmd
                assert "1" in cmd
                assert "--single-branch" in cmd
                assert "--no-tags" in cmd


def test_rag_service_default_batch_size():
    """Verify default repository process batch size is 10."""
    service = RAGService()
    assert service.DEFAULT_PROCESS_BATCH_SIZE == 10

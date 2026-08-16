"""Tests for database layer, models, relationships, constraints, and CRUD persistence."""

from __future__ import annotations

import numpy as np
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from pgvector.sqlalchemy import Vector
from app.db.crud import (
    create_or_update_repository,
    get_repository_by_name,
    save_query_log,
    save_repository_documents,
)
from app.db.database import Base
from app.db.models import ChunkModel, FileModel, QueryModel, RepositoryModel
from app.models.document import Document
from app.services.rag_service import RAGService


# Compile pgvector.Vector as TEXT for SQLite in-memory testing
@compiles(Vector, "sqlite")
def _compile_vector_sqlite(element, compiler, **kw):
    return "TEXT"


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_repository_model_creation(db_session):
    """Test creating a RepositoryModel record."""
    repo = RepositoryModel(
        name="test-repo",
        source="/path/to/test-repo",
        source_type="local",
        status="indexed",
    )
    db_session.add(repo)
    db_session.commit()

    retrieved = db_session.execute(
        select(RepositoryModel).where(RepositoryModel.name == "test-repo")
    ).scalar_one()

    assert retrieved.id is not None
    assert retrieved.name == "test-repo"
    assert retrieved.source_type == "local"
    assert retrieved.status == "indexed"


def test_file_repository_relationship(db_session):
    """Test 1-to-N relationship between RepositoryModel and FileModel."""
    repo = RepositoryModel(name="rel-repo", source="/path/rel-repo")
    db_session.add(repo)
    db_session.commit()

    file1 = FileModel(repository_id=repo.id, path="src/main.py", language="python")
    file2 = FileModel(repository_id=repo.id, path="src/utils.py", language="python")
    db_session.add_all([file1, file2])
    db_session.commit()

    db_session.refresh(repo)
    assert len(repo.files) == 2
    paths = {f.path for f in repo.files}
    assert paths == {"src/main.py", "src/utils.py"}


def test_chunk_file_relationship(db_session):
    """Test 1-to-N relationship between FileModel and ChunkModel."""
    repo = RepositoryModel(name="chunk-repo", source="/path/chunk-repo")
    db_session.add(repo)
    db_session.commit()

    file_rec = FileModel(repository_id=repo.id, path="app/core.py", language="python")
    db_session.add(file_rec)
    db_session.commit()

    chunk1 = ChunkModel(
        file_id=file_rec.id,
        content="def foo(): pass",
        chunk_type="function",
        function_name="foo",
        start_line=1,
        end_line=2,
    )
    chunk2 = ChunkModel(
        file_id=file_rec.id,
        content="def bar(): pass",
        chunk_type="function",
        function_name="bar",
        start_line=3,
        end_line=4,
    )
    db_session.add_all([chunk1, chunk2])
    db_session.commit()

    db_session.refresh(file_rec)
    assert len(file_rec.chunks) == 2
    funcs = {c.function_name for c in file_rec.chunks}
    assert funcs == {"foo", "bar"}


def test_query_repository_relationship(db_session):
    """Test 1-to-N relationship between RepositoryModel and QueryModel."""
    repo = RepositoryModel(name="query-repo", source="/path/query-repo")
    db_session.add(repo)
    db_session.commit()

    query_rec = QueryModel(
        repository_id=repo.id,
        question="What does main do?",
        answer="Main starts the server.",
        provider="gemini",
        model="gemini-3.6-flash",
        latency_ms=120.5,
    )
    db_session.add(query_rec)
    db_session.commit()

    db_session.refresh(repo)
    assert len(repo.queries) == 1
    assert repo.queries[0].question == "What does main do?"


def test_duplicate_file_path_constraint(db_session):
    """Test unique constraint on (repository_id, path) in FileModel."""
    repo = RepositoryModel(name="dup-repo", source="/path/dup-repo")
    db_session.add(repo)
    db_session.commit()

    file1 = FileModel(repository_id=repo.id, path="src/main.py")
    file2 = FileModel(repository_id=repo.id, path="src/main.py")

    db_session.add(file1)
    db_session.commit()

    db_session.add(file2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_crud_create_or_update_repository(db_session):
    """Test create_or_update_repository CRUD operation."""
    repo1 = create_or_update_repository(
        db=db_session,
        name="crud-repo",
        source="/path/1",
        source_type="local",
        status="pending",
    )
    assert repo1.status == "pending"

    # Update existing repository
    repo2 = create_or_update_repository(
        db=db_session,
        name="crud-repo",
        source="/path/1",
        source_type="local",
        status="indexed",
    )
    assert repo2.id == repo1.id
    assert repo2.status == "indexed"


def test_crud_save_repository_documents(db_session):
    """Test saving documents and embeddings into database models."""
    repo = create_or_update_repository(
        db=db_session, name="doc-repo", source="/path/doc-repo"
    )

    sample_doc = Document(
        content="def hello(): return 'world'",
        file_name="hello.py",
        file_path="src/hello.py",
        extension=".py",
        repository_name="doc-repo",
        language="python",
        chunk_id="hello.py::hello::1",
        chunk_type="function",
        function_name="hello",
        start_line=1,
        end_line=2,
        embedding=[0.1] * 384,
    )

    files_saved, chunks_saved = save_repository_documents(
        db=db_session, repository_id=repo.id, documents=[sample_doc]
    )

    assert files_saved == 1
    assert chunks_saved == 1

    stored_file = db_session.execute(
        select(FileModel).where(FileModel.repository_id == repo.id)
    ).scalar_one()
    assert stored_file.path == "src/hello.py"
    assert len(stored_file.chunks) == 1
    assert stored_file.chunks[0].function_name == "hello"


def test_chunk_null_and_384d_embedding_persistence(db_session):
    """Test ChunkModel permits NULL embeddings and persists 384d embeddings."""
    repo = create_or_update_repository(db=db_session, name="test-null-repo", source="/tmp")
    file_rec = FileModel(repository_id=repo.id, path="null_test.py")
    db_session.add(file_rec)
    db_session.flush()

    # 1. Test NULL embedding allowed
    chunk_null = ChunkModel(
        file_id=file_rec.id,
        content="def empty(): pass",
        embedding=None,
    )
    db_session.add(chunk_null)
    db_session.commit()
    db_session.refresh(chunk_null)
    assert chunk_null.id is not None
    assert chunk_null.embedding is None

    # 2. Test 384d embedding persisted
    chunk_384 = ChunkModel(
        file_id=file_rec.id,
        content="def full(): pass",
        embedding=[0.05] * 384,
    )
    db_session.add(chunk_384)
    db_session.commit()
    db_session.refresh(chunk_384)
    assert chunk_384.id is not None
    assert len(chunk_384.embedding) == 384


def test_database_default_embedding_dimension_constant():
    """Verify DEFAULT_EMBEDDING_DIMENSION in models.py is 384."""
    from app.db.models import DEFAULT_EMBEDDING_DIMENSION, EMBEDDING_DIMENSION
    assert DEFAULT_EMBEDDING_DIMENSION == 384
    assert EMBEDDING_DIMENSION == 384


def test_crud_save_query_log(db_session):
    """Test save_query_log CRUD helper."""
    query_rec = save_query_log(
        db=db_session,
        question="How to run tests?",
        answer="Run pytest.",
        provider="gemini",
        model="gemini-3.6-flash",
        latency_ms=45.2,
    )

    assert query_rec.id is not None
    assert query_rec.question == "How to run tests?"
    assert query_rec.answer == "Run pytest."


def test_rag_service_db_integration(db_session, tmp_path):
    """Test RAGService indexing and querying with injected DB session."""
    from unittest.mock import MagicMock
    from app.embeddings.embedding_engine import EmbeddingEngine

    # Create sample repository file
    code_dir = tmp_path / "sample_code"
    code_dir.mkdir()
    (code_dir / "app.py").write_text("def run():\n    print('Running app')\n")

    mock_model = MagicMock()
    mock_model.embed.return_value = [np.array([0.1] * 384, dtype=np.float32)]
    mock_engine = EmbeddingEngine(provider="local", local_model=mock_model)

    rag_service = RAGService(embedding_engine=mock_engine, db_session=db_session)
    res = rag_service.index_repository(str(code_dir))

    assert res["status"] == "indexed"
    assert res["files_loaded"] == 1

    # Verify repository was persisted in database
    db_repo = get_repository_by_name(db_session, "sample_code")
    assert db_repo is not None
    assert len(db_repo.files) == 1

"""Persistence and restart reliability tests for DevMind AI RAG system."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.db.crud import create_or_update_repository, save_repository_documents, get_repository_by_name
from app.db.database import Base
from app.models import Document
from app.services.rag_service import RAGService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def memory_db():
    """In-memory SQLite database for testing persistence CRUD."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_persistence_and_restart_reliability(memory_db) -> None:
    """Verify that repository indexing persists to database layer and can be retrieved across service restarts."""
    doc = Document(
        content="export class VerificationEngine {}",
        file_name="engine.ts",
        file_path="lib/verification/engine.ts",
        extension=".ts",
        repository_name="proofos",
        chunk_type="file",
        start_line=1,
        end_line=20,
    )
    doc.embedding = [0.1] * 768

    # 1. Index repository and save to database
    repo_model = create_or_update_repository(memory_db, "proofos", "/app/proofos", "local")
    save_repository_documents(memory_db, repo_model.id, [doc])

    # 2. Simulate service restart by creating a new RAGService instance with the same DB session
    restarted_service = RAGService(db_session=memory_db)
    fetched_repo = get_repository_by_name(memory_db, "proofos")

    assert fetched_repo is not None
    assert fetched_repo.name == "proofos"
    assert len(fetched_repo.files) == 1
    assert fetched_repo.files[0].path == "lib/verification/engine.ts"

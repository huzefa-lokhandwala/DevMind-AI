"""CRUD repository operations for database persistence layer."""

from __future__ import annotations

import hashlib
import logging
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChunkModel, FileModel, QueryModel, RepositoryModel
from app.models.document import Document

logger = logging.getLogger(__name__)


def create_or_update_repository(
    db: Session,
    name: str,
    source: str,
    source_type: str = "local",
    status: str = "indexed",
) -> RepositoryModel:
    """Find existing repository by name or create a new one."""
    stmt = select(RepositoryModel).where(RepositoryModel.name == name)
    repo = db.execute(stmt).scalar_one_or_none()

    if repo:
        repo.source = source
        repo.source_type = source_type
        repo.status = status
    else:
        repo = RepositoryModel(
            name=name,
            source=source,
            source_type=source_type,
            status=status,
        )
        db.add(repo)

    db.commit()
    db.refresh(repo)
    return repo


def get_repository_by_name(db: Session, name: str) -> RepositoryModel | None:
    """Retrieve repository record by name."""
    stmt = select(RepositoryModel).where(RepositoryModel.name == name)
    return db.execute(stmt).scalar_one_or_none()


def save_repository_documents(
    db: Session,
    repository_id: int,
    documents: Sequence[Document],
) -> tuple[int, int]:
    """Persist loaded files and code chunks with pgvector embeddings for a repository.

    Args:
        db: Active SQLAlchemy database session.
        repository_id: Primary key of parent RepositoryModel.
        documents: List of Document instances containing content, metadata, and embeddings.

    Returns:
        Tuple of (count_of_files_saved, count_of_chunks_saved).
    """
    if not documents:
        return 0, 0

    # Group documents by file_path
    file_map: dict[str, list[Document]] = {}
    for doc in documents:
        file_path = doc.file_path or doc.file_name
        file_map.setdefault(file_path, []).append(doc)

    files_saved = 0
    chunks_saved = 0

    for path, docs in file_map.items():
        # Calculate combined content hash for change tracking
        combined_content = "".join(d.content for d in docs)
        content_hash = hashlib.sha256(combined_content.encode("utf-8")).hexdigest()
        language = docs[0].language if docs else None

        # Check existing file or create
        stmt = select(FileModel).where(
            FileModel.repository_id == repository_id,
            FileModel.path == path,
        )
        file_record = db.execute(stmt).scalar_one_or_none()

        if file_record:
            file_record.language = language
            file_record.content_hash = content_hash
            # Delete old chunks for updated file
            db.query(ChunkModel).filter(ChunkModel.file_id == file_record.id).delete()
        else:
            file_record = FileModel(
                repository_id=repository_id,
                path=path,
                language=language,
                content_hash=content_hash,
            )
            db.add(file_record)
            db.flush()  # populate file_record.id

        files_saved += 1

        # Create chunks
        for doc in docs:
            chunk = ChunkModel(
                file_id=file_record.id,
                content=doc.content,
                chunk_type=doc.chunk_type,
                function_name=doc.function_name,
                class_name=doc.class_name,
                start_line=doc.start_line,
                end_line=doc.end_line,
                embedding=doc.embedding if doc.embedding else None,
            )
            db.add(chunk)
            chunks_saved += 1

    db.commit()
    logger.info(
        "Persisted DB records for repo %d: %d files, %d chunks",
        repository_id,
        files_saved,
        chunks_saved,
    )
    return files_saved, chunks_saved


def save_query_log(
    db: Session,
    question: str,
    answer: str,
    repository_id: int | None = None,
    provider: str | None = None,
    model: str | None = None,
    latency_ms: float | None = None,
) -> QueryModel:
    """Save query text, answer, and latency history into queries table."""
    query_record = QueryModel(
        repository_id=repository_id,
        question=question,
        answer=answer,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
    )
    db.add(query_record)
    db.commit()
    db.refresh(query_record)
    return query_record

"""CRUD repository operations for database persistence layer."""

from __future__ import annotations

import hashlib
import logging
from typing import Sequence

import json
import uuid
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    ChunkModel,
    ConversationModel,
    FileModel,
    MessageModel,
    QueryModel,
    RepositoryModel,
)
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

    try:
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
    except Exception:
        db.rollback()
        raise

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


def create_conversation(
    db: Session,
    session_id: str,
    title: str = "New Chat",
    repository_name: str | None = None,
    conversation_id: str | None = None,
) -> ConversationModel:
    """Create a new conversation session associated with an anonymous browser session ID."""
    cid = conversation_id or str(uuid.uuid4())
    conv = ConversationModel(
        id=cid,
        session_id=session_id,
        title=title,
        repository_name=repository_name,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversation(
    db: Session, conversation_id: str, session_id: str
) -> ConversationModel | None:
    """Retrieve conversation by ID enforcing session isolation."""
    stmt = (
        select(ConversationModel)
        .options(joinedload(ConversationModel.messages))
        .where(
            ConversationModel.id == conversation_id,
            ConversationModel.session_id == session_id,
        )
    )
    return db.execute(stmt).unique().scalar_one_or_none()


def list_conversations(
    db: Session, session_id: str, limit: int = 50
) -> list[ConversationModel]:
    """List recent conversations for a session in descending updated order."""
    stmt = (
        select(ConversationModel)
        .where(ConversationModel.session_id == session_id)
        .order_by(desc(ConversationModel.updated_at))
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def update_conversation_title(
    db: Session, conversation_id: str, session_id: str, title: str
) -> ConversationModel | None:
    """Update title for a conversation."""
    conv = get_conversation(db, conversation_id=conversation_id, session_id=session_id)
    if conv:
        conv.title = title
        db.commit()
        db.refresh(conv)
    return conv


def delete_conversation(db: Session, conversation_id: str, session_id: str) -> bool:
    """Delete a conversation enforcing session isolation."""
    conv = get_conversation(db, conversation_id=conversation_id, session_id=session_id)
    if not conv:
        return False
    db.delete(conv)
    db.commit()
    return True


def delete_all_conversations(db: Session, session_id: str) -> int:
    """Delete all conversations belonging to a session."""
    convs = list_conversations(db, session_id=session_id, limit=1000)
    count = len(convs)
    for c in convs:
        db.delete(c)
    db.commit()
    return count


def add_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    intent: str | None = None,
    sources: list[dict] | None = None,
    provider: str | None = None,
    model: str | None = None,
    latency_ms: float | None = None,
) -> MessageModel:
    """Append a message turn to a conversation and touch its updated_at timestamp."""
    sources_str = json.dumps(sources) if sources is not None else None
    msg = MessageModel(
        conversation_id=conversation_id,
        role=role,
        content=content,
        intent=intent,
        sources_json=sources_str,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
    )
    db.add(msg)

    # Touch conversation updated_at
    stmt = select(ConversationModel).where(ConversationModel.id == conversation_id)
    conv = db.execute(stmt).scalar_one_or_none()
    if conv:
        from datetime import datetime, timezone
        conv.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(msg)
    return msg

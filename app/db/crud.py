"""CRUD repository operations for database persistence layer."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Sequence

import json
import uuid
from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    ChunkModel,
    ConversationModel,
    FileModel,
    MessageModel,
    QueryModel,
    RepositoryModel,
    UserModel,
)
from app.models.document import Document

logger = logging.getLogger(__name__)


def create_user(
    db: Session,
    email: str,
    password_hash: str,
    full_name: str | None = None,
) -> UserModel:
    """Create a new user account with normalized email and hashed credentials."""
    normalized_email = email.strip().lower()
    user = UserModel(
        email=normalized_email,
        password_hash=password_hash,
        full_name=full_name.strip() if full_name else None,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> UserModel | None:
    """Retrieve user record by email address (case-insensitive)."""
    normalized_email = email.strip().lower()
    stmt = select(UserModel).where(UserModel.email == normalized_email)
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> UserModel | None:
    """Retrieve user record by primary key ID."""
    stmt = select(UserModel).where(UserModel.id == user_id)
    return db.execute(stmt).scalar_one_or_none()


_cached_dev_user: UserModel | None = None


def get_or_create_default_dev_user(db: Session) -> UserModel:
    """Retrieve or create a default development/test workspace user."""
    from app.utils.config import get_devmind_env

    if get_devmind_env() == "production":
        raise RuntimeError("Default dev user cannot be created or accessed in production.")

    global _cached_dev_user
    if _cached_dev_user is not None:
        return _cached_dev_user

    dev_email = "dev@workspace.local"
    user = get_user_by_email(db, dev_email)
    if not user:
        # Precomputed Argon2id hash for 'devworkspace123!' (m=65536, t=2, p=1) to eliminate test latency
        dev_hash = "$argon2id$v=19$m=65536,t=2,p=1$3sKB6j++5bLfFMO8Yh0arQ$2jYsGxQQAPXMMQGIkt5jeRJj9GBNwoEG9IKznBF8Lfk"
        user = create_user(
            db,
            email=dev_email,
            password_hash=dev_hash,
            full_name="Developer Workspace",
        )
    # Expunge so it can be safely referenced across sessions
    try:
        db.expunge(user)
    except Exception:
        pass
    _cached_dev_user = user
    return user


def create_or_update_repository(
    db: Session,
    name: str,
    source: str,
    source_type: str = "local",
    status: str = "indexed",
    embedding_provider: str | None = None,
    embedding_model: str | None = None,
    embedding_dimension: int | None = None,
    user_id: int | None = None,
) -> RepositoryModel:
    """Find existing repository by name (scoped by user if provided) or create a new one."""
    if user_id is not None:
        stmt = select(RepositoryModel).where(
            RepositoryModel.name == name,
            (RepositoryModel.user_id == user_id) | (RepositoryModel.user_id.is_(None)),
        )
    else:
        stmt = select(RepositoryModel).where(RepositoryModel.name == name)
    repo = db.execute(stmt).scalar_one_or_none()

    if repo:
        repo.source = source
        repo.source_type = source_type
        repo.status = status
        if user_id is not None:
            repo.user_id = user_id
        if embedding_provider is not None:
            repo.embedding_provider = embedding_provider
        if embedding_model is not None:
            repo.embedding_model = embedding_model
        if embedding_dimension is not None:
            repo.embedding_dimension = embedding_dimension
    else:
        repo = RepositoryModel(
            name=name,
            source=source,
            source_type=source_type,
            status=status,
            user_id=user_id,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension,
        )
        db.add(repo)

    db.commit()
    db.refresh(repo)
    return repo


def get_repository_by_name(
    db: Session,
    name: str,
    user_id: int | None = None,
) -> RepositoryModel | None:
    """Retrieve repository record by name, optionally enforcing user isolation."""
    if user_id is not None:
        stmt = select(RepositoryModel).where(
            RepositoryModel.name == name,
            (RepositoryModel.user_id == user_id) | (RepositoryModel.user_id.is_(None)),
        )
    else:
        stmt = select(RepositoryModel).where(RepositoryModel.name == name)
    return db.execute(stmt).scalar_one_or_none()


def save_repository_documents(
    db: Session,
    repository_id: int,
    documents: Sequence[Document],
    commit: bool = True,
) -> tuple[int, int]:
    """Persist loaded files and code chunks with pgvector embeddings for a repository.

    Optimized for bulk execution: queries existing files in batch, deletes obsolete chunks,
    flushes newly added files in a single pass, and bulk-adds all chunk models.

    Args:
        db: Active SQLAlchemy database session.
        repository_id: Primary key of parent RepositoryModel.
        documents: List of Document instances containing content, metadata, and embeddings.
        commit: Whether to commit session at completion (default: True).

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

    paths = list(file_map.keys())
    files_saved = 0
    chunks_saved = 0

    try:
        # Bulk query existing files in this batch to minimize network roundtrips
        stmt = select(FileModel).where(
            FileModel.repository_id == repository_id,
            FileModel.path.in_(paths),
        )
        existing_records = {f.path: f for f in db.execute(stmt).scalars().all()}

        # Bulk delete existing chunks for files being updated
        existing_file_ids = [f.id for f in existing_records.values()]
        if existing_file_ids:
            db.execute(delete(ChunkModel).where(ChunkModel.file_id.in_(existing_file_ids)))

        files_to_chunk: list[tuple[FileModel, list[Document]]] = []
        new_files_present = False

        for path, docs in file_map.items():
            combined_content = "".join(d.content for d in docs)
            content_hash = hashlib.sha256(combined_content.encode("utf-8")).hexdigest()
            language = docs[0].language if docs else None

            if path in existing_records:
                file_record = existing_records[path]
                file_record.language = language
                file_record.content_hash = content_hash
                files_to_chunk.append((file_record, docs))
            else:
                file_record = FileModel(
                    repository_id=repository_id,
                    path=path,
                    language=language,
                    content_hash=content_hash,
                )
                db.add(file_record)
                files_to_chunk.append((file_record, docs))
                new_files_present = True

            files_saved += 1

        if new_files_present:
            db.flush()  # populate file_record.id for newly created files in single roundtrip

        chunks_to_add: list[ChunkModel] = []
        for file_record, docs in files_to_chunk:
            for doc in docs:
                chunks_to_add.append(
                    ChunkModel(
                        file_id=file_record.id,
                        content=doc.content,
                        chunk_type=doc.chunk_type,
                        function_name=doc.function_name,
                        class_name=doc.class_name,
                        start_line=doc.start_line,
                        end_line=doc.end_line,
                        embedding=doc.embedding if doc.embedding else None,
                    )
                )
                chunks_saved += 1

        if chunks_to_add:
            db.add_all(chunks_to_add)

        if commit:
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


def search_repository_chunks(
    db: Session,
    repository_id: int,
    query_vector: list[float],
    top_k: int = 5,
) -> list[tuple[Document, float]]:
    """Retrieve top-k nearest chunks for a repository using pgvector cosine distance.

    Enforces strict repository scoping at the SQL query level:
    only chunks belonging to the specified repository_id are queried and returned.

    For PostgreSQL: executes native pgvector `<=>` cosine distance ordering.
    For SQLite (test environment): queries repository chunks and calculates cosine similarity in Python.

    Args:
        db: Active SQLAlchemy database session.
        repository_id: Primary key of target repository.
        query_vector: Dense embedding vector of query string.
        top_k: Number of most similar chunks to return.

    Returns:
        List of (Document, score) tuples ordered by descending similarity score.
    """
    if not query_vector or top_k <= 0:
        return []

    dialect_name = db.bind.dialect.name if db.bind else ""
    if dialect_name == "postgresql":
        # Native pgvector cosine distance query strictly scoped to repository_id
        stmt = (
            select(
                ChunkModel,
                FileModel,
                RepositoryModel,
                ChunkModel.embedding.cosine_distance(query_vector).label("distance"),
            )
            .join(FileModel, ChunkModel.file_id == FileModel.id)
            .join(RepositoryModel, FileModel.repository_id == RepositoryModel.id)
            .where(
                RepositoryModel.id == repository_id,
                ChunkModel.embedding.is_not(None),
            )
            .order_by(ChunkModel.embedding.cosine_distance(query_vector).asc())
            .limit(top_k)
        )
        rows = db.execute(stmt).all()
        results: list[tuple[Document, float]] = []
        for chunk, file_record, repo_record, distance in rows:
            dist_val = float(distance) if distance is not None else 1.0
            # Cosine similarity = 1 - distance (clamped to [0.0, 1.0])
            score = max(0.0, min(1.0, 1.0 - dist_val))
            doc = Document(
                content=chunk.content,
                file_name=Path(file_record.path).name,
                file_path=file_record.path,
                extension=f".{file_record.path.rsplit('.', 1)[-1]}" if "." in file_record.path else "",
                repository_name=repo_record.name,
                language=file_record.language,
                chunk_type=chunk.chunk_type or "chunk",
                function_name=chunk.function_name,
                class_name=chunk.class_name,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
            )
            results.append((doc, score))
        return results

    if dialect_name == "sqlite":
        # Fallback for SQLite in-memory test databases without native pgvector extensions
        stmt = (
            select(ChunkModel, FileModel, RepositoryModel)
            .join(FileModel, ChunkModel.file_id == FileModel.id)
            .join(RepositoryModel, FileModel.repository_id == RepositoryModel.id)
            .where(
                RepositoryModel.id == repository_id,
                ChunkModel.embedding.is_not(None),
            )
        )
        rows = db.execute(stmt).all()
        if not rows:
            return []

        import json
        import numpy as np

        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = float(np.linalg.norm(q_vec))
        if q_norm == 0.0:
            return []

        scored_candidates: list[tuple[Document, float]] = []
        for chunk, file_record, repo_record in rows:
            emb = chunk.embedding
            if isinstance(emb, str):
                try:
                    emb = json.loads(emb)
                except Exception:
                    try:
                        emb = [float(x) for x in emb.strip("[]").split(",") if x.strip()]
                    except Exception:
                        continue
            if not emb:
                continue
            c_vec = np.array(emb, dtype=np.float32)
            c_norm = float(np.linalg.norm(c_vec))
            if c_norm == 0.0:
                continue
            dot = float(np.dot(q_vec, c_vec))
            sim = float(dot / (q_norm * c_norm))
            score = max(0.0, min(1.0, (sim + 1.0) / 2.0 if sim < 0 else sim))

            doc = Document(
                content=chunk.content,
                file_name=Path(file_record.path).name,
                file_path=file_record.path,
                extension=f".{file_record.path.rsplit('.', 1)[-1]}" if "." in file_record.path else "",
                repository_name=repo_record.name,
                language=file_record.language,
                chunk_type=chunk.chunk_type or "chunk",
                function_name=chunk.function_name,
                class_name=chunk.class_name,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
            )
            scored_candidates.append((doc, score))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        return scored_candidates[:top_k]

    raise RuntimeError(
        f"Unsupported database dialect for vector search: '{dialect_name}'. "
        "Native pgvector search requires a PostgreSQL database."
    )


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
    session_id: str | None = None,
    title: str = "New Chat",
    repository_name: str | None = None,
    conversation_id: str | None = None,
    user_id: int | None = None,
) -> ConversationModel:
    """Create a new conversation session associated with a user and/or session ID."""
    cid = conversation_id or str(uuid.uuid4())
    resolved_session_id = session_id or (f"user-{user_id}" if user_id is not None else "anonymous-default-session")
    conv = ConversationModel(
        id=cid,
        user_id=user_id,
        session_id=resolved_session_id,
        title=title,
        repository_name=repository_name,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversation(
    db: Session,
    conversation_id: str,
    session_id: str | None = None,
    user_id: int | None = None,
) -> ConversationModel | None:
    """Retrieve conversation by ID enforcing user and/or session isolation."""
    stmt = (
        select(ConversationModel)
        .options(joinedload(ConversationModel.messages))
        .where(ConversationModel.id == conversation_id)
    )
    if user_id is not None:
        stmt = stmt.where(
            (ConversationModel.user_id == user_id)
            | (
                (ConversationModel.user_id.is_(None))
                & (ConversationModel.session_id == session_id)
                if session_id
                else False
            )
        )
    elif session_id is not None:
        stmt = stmt.where(ConversationModel.session_id == session_id)

    return db.execute(stmt).unique().scalar_one_or_none()


def list_conversations(
    db: Session,
    session_id: str | None = None,
    user_id: int | None = None,
    limit: int = 50,
) -> list[ConversationModel]:
    """List recent conversations for an authenticated user or session in descending updated order."""
    stmt = select(ConversationModel)
    if user_id is not None:
        stmt = stmt.where(
            (ConversationModel.user_id == user_id)
            | (
                (ConversationModel.user_id.is_(None))
                & (ConversationModel.session_id == session_id)
                if session_id
                else False
            )
        )
    elif session_id is not None:
        stmt = stmt.where(ConversationModel.session_id == session_id)

    stmt = stmt.order_by(desc(ConversationModel.updated_at)).limit(limit)
    return list(db.execute(stmt).scalars().all())


def update_conversation_title(
    db: Session,
    conversation_id: str,
    session_id: str | None = None,
    user_id: int | None = None,
    title: str = "",
) -> ConversationModel | None:
    """Update title for a conversation enforcing ownership."""
    conv = get_conversation(
        db, conversation_id=conversation_id, session_id=session_id, user_id=user_id
    )
    if conv:
        conv.title = title
        db.commit()
        db.refresh(conv)
    return conv


def delete_conversation(
    db: Session,
    conversation_id: str,
    session_id: str | None = None,
    user_id: int | None = None,
) -> bool:
    """Delete a conversation enforcing user and/or session isolation."""
    conv = get_conversation(
        db, conversation_id=conversation_id, session_id=session_id, user_id=user_id
    )
    if not conv:
        return False
    db.delete(conv)
    db.commit()
    return True


def delete_all_conversations(
    db: Session,
    session_id: str | None = None,
    user_id: int | None = None,
) -> int:
    """Delete all conversations belonging to an authenticated user or session."""
    convs = list_conversations(db, session_id=session_id, user_id=user_id, limit=1000)
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

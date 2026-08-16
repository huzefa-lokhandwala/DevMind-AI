"""SQLAlchemy persistent ORM models for DevMind AI."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

import os
from app.db.database import Base

DEFAULT_EMBEDDING_DIMENSION = 768
_env_dim = os.getenv("EMBEDDING_DIMENSION")
EMBEDDING_DIMENSION = int(_env_dim) if _env_dim and _env_dim.isdigit() else DEFAULT_EMBEDDING_DIMENSION


class RepositoryModel(Base):
    """SQLAlchemy model representing an ingested codebase repository."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="local")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="indexed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    files: Mapped[List[FileModel]] = relationship(
        "FileModel", back_populates="repository", cascade="all, delete-orphan"
    )
    queries: Mapped[List[QueryModel]] = relationship(
        "QueryModel", back_populates="repository"
    )


class FileModel(Base):
    """SQLAlchemy model representing a code or text file in a repository."""

    __tablename__ = "files"

    __table_args__ = (
        UniqueConstraint("repository_id", "path", name="uq_repository_file_path"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    repository: Mapped[RepositoryModel] = relationship("RepositoryModel", back_populates="files")
    chunks: Mapped[List[ChunkModel]] = relationship(
        "ChunkModel", back_populates="file", cascade="all, delete-orphan"
    )


class ChunkModel(Base):
    """SQLAlchemy model representing a code chunk with pgvector embedding."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    function_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    class_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    file: Mapped[FileModel] = relationship("FileModel", back_populates="chunks")


class QueryModel(Base):
    """SQLAlchemy model representing query history and performance metadata."""

    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    repository: Mapped[Optional[RepositoryModel]] = relationship("RepositoryModel", back_populates="queries")

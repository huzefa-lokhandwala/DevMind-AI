"""RAG Service orchestration layer for DevMind AI backend."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.chunking.code_chunker import CodeChunker
from app.db.crud import (
    create_or_update_repository,
    get_repository_by_name,
    save_query_log,
    save_repository_documents,
)
from app.db.database import SessionLocal
from app.embeddings.embedding_engine import EmbeddingEngine
from app.llm.gemini_provider import GeminiProvider
from app.loaders import GitHubLoaderError, GitHubRepositoryLoader, RepositoryLoader
from app.models.document import Document
from app.prompts.context_assembler import ContextAssembler
from app.retrieval.retriever import Retriever
from app.vector_store.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)


class RepositoryNotIndexedError(Exception):
    """Raised when query is invoked before any repository has been indexed."""


class InvalidRepositoryError(Exception):
    """Raised when repository path does not exist, is invalid, or contains no indexable files."""


class RAGService:
    """Stateful runtime service managing the RAG pipeline lifecycle.

    Reuses EmbeddingEngine and GeminiProvider across requests to avoid model re-initialization.
    Maintains active FAISS vector store state for semantic code queries and persists database metadata.
    """

    def __init__(
        self,
        embedding_engine: EmbeddingEngine | None = None,
        llm_provider: GeminiProvider | None = None,
        db_session: Session | None = None,
    ) -> None:
        """Initialize RAGService components once at application startup."""
        logger.info("Initializing RAGService lifecycle...")
        self.embedding_engine = embedding_engine or EmbeddingEngine()
        self.llm_provider = llm_provider or GeminiProvider()
        self.context_assembler = ContextAssembler()
        self.chunker = CodeChunker()
        self.db_session = db_session

        # Runtime indexed state
        self.vector_store: FAISSVectorStore | None = None
        self.retriever: Retriever | None = None
        self.indexed_repository_name: str | None = None

    @property
    def is_indexed(self) -> bool:
        """Return True if a repository is currently indexed into vector store."""
        return (
            self.vector_store is not None
            and self.retriever is not None
            and self.vector_store.total_documents > 0
        )

    def _get_db_session(self) -> tuple[Session, bool]:
        """Obtain active database session and flag indicating if session should be closed."""
        if self.db_session is not None:
            return self.db_session, False
        return SessionLocal(), True

    def _persist_indexed_repository(
        self,
        repository_name: str,
        source: str,
        source_type: str,
        embedded_chunks: list[Document],
    ) -> None:
        """Helper to save repository metadata, files, and chunks to PostgreSQL."""
        try:
            db, auto_close = self._get_db_session()
            try:
                repo_model = create_or_update_repository(
                    db=db,
                    name=repository_name,
                    source=source,
                    source_type=source_type,
                    status="indexed",
                )
                save_repository_documents(
                    db=db,
                    repository_id=repo_model.id,
                    documents=embedded_chunks,
                )
                logger.info("Successfully persisted repository '%s' to database", repository_name)
            finally:
                if auto_close:
                    db.close()
        except Exception as exc:
            logger.warning("Database persistence failed for repository '%s': %s", repository_name, exc)

    def _persist_query_log(
        self,
        question: str,
        answer: str,
        provider: str | None,
        model: str | None,
        latency_ms: float | None,
    ) -> None:
        """Helper to save query log to PostgreSQL."""
        try:
            db, auto_close = self._get_db_session()
            try:
                repo_id: int | None = None
                if self.indexed_repository_name:
                    repo_model = get_repository_by_name(db, self.indexed_repository_name)
                    if repo_model:
                        repo_id = repo_model.id

                save_query_log(
                    db=db,
                    question=question,
                    answer=answer,
                    repository_id=repo_id,
                    provider=provider,
                    model=model,
                    latency_ms=latency_ms,
                )
                logger.info("Successfully saved query history log to database")
            finally:
                if auto_close:
                    db.close()
        except Exception as exc:
            logger.warning("Database persistence failed for query history: %s", exc)

    def index_repository(
        self, repository_path: str, source_type: str = "local", source_override: str | None = None
    ) -> dict[str, Any]:
        """Index a local repository for RAG retrieval and persist to database.

        Args:
            repository_path: Path to the target local repository folder.
            source_type: Metadata classification ('local' or 'github').
            source_override: Optional source location string if different from repository_path.

        Returns:
            Dictionary payload describing indexing statistics.

        Raises:
            InvalidRepositoryError: If path is missing, not a directory, or empty.
        """
        path = Path(repository_path).resolve()
        if not path.exists():
            raise InvalidRepositoryError(f"Repository path does not exist: {repository_path}")
        if not path.is_dir():
            raise InvalidRepositoryError(f"Repository path is not a directory: {repository_path}")

        try:
            loader = RepositoryLoader(path)
            documents = loader.load_files()
        except (FileNotFoundError, NotADirectoryError) as exc:
            raise InvalidRepositoryError(str(exc)) from exc

        if not documents:
            raise InvalidRepositoryError(f"No supported indexable source files found in {repository_path}")

        chunks = self.chunker.chunk_documents(documents)
        embedded_chunks = self.embedding_engine.embed_documents(chunks)

        vector_store = FAISSVectorStore()
        vector_store.build_index(embedded_chunks)

        from app.graph.code_graph import CodeGraph
        code_graph = CodeGraph()
        code_graph.build_from_documents(chunks)

        retriever = Retriever(self.embedding_engine, vector_store, code_graph=code_graph)

        # Update service runtime state
        self.vector_store = vector_store
        self.retriever = retriever
        self.indexed_repository_name = loader.repository_name

        # Persist to relational database layer
        source_loc = source_override or str(path)
        self._persist_indexed_repository(
            repository_name=loader.repository_name,
            source=source_loc,
            source_type=source_type,
            embedded_chunks=embedded_chunks,
        )

        logger.info(
            "Indexed repository '%s': %d files, %d chunks, %d embeddings",
            loader.repository_name,
            len(documents),
            len(chunks),
            len(embedded_chunks),
        )

        return {
            "repository": loader.repository_name,
            "files_loaded": len(documents),
            "chunks_created": len(chunks),
            "embeddings_created": len(embedded_chunks),
            "status": "indexed",
        }

    def index_github_repository(self, github_url: str) -> dict[str, Any]:
        """Index a public GitHub repository by URL and persist to database.

        Args:
            github_url: Validated HTTPS URL for a public GitHub repository.

        Returns:
            Dictionary payload matching IndexRepositoryResponse schema.

        Raises:
            InvalidRepositoryError: If GitHub validation, cloning, or document loading fails.
        """
        github_loader = GitHubRepositoryLoader()
        try:
            local_repo_path = github_loader.clone_repository(github_url)
        except GitHubLoaderError as exc:
            raise InvalidRepositoryError(str(exc)) from exc

        return self.index_repository(
            str(local_repo_path), source_type="github", source_override=github_url
        )

    def query(self, query_text: str, top_k: int = 5) -> dict[str, Any]:
        """Query the currently indexed repository.

        Args:
            query_text: User question string.
            top_k: Number of relevant context chunks to retrieve.

        Returns:
            Dictionary payload matching QueryResponse schema.

        Raises:
            RepositoryNotIndexedError: If no repository has been indexed yet.
            ValueError: If query is empty or whitespace-only.
        """
        if not self.is_indexed or self.retriever is None:
            raise RepositoryNotIndexedError(
                "No repository has been indexed yet. Call /repositories/index first."
            )

        query_clean = query_text.strip()
        if not query_clean:
            raise ValueError("Query string must not be empty or whitespace-only.")

        t0 = time.perf_counter()
        search_results = self.retriever.retrieve(
            query_clean, k=top_k, repository_name=self.indexed_repository_name
        )
        t1 = time.perf_counter()
        prompt_context = self.context_assembler.assemble(query_clean, search_results)
        t2 = time.perf_counter()
        llm_response = self.llm_provider.generate(prompt_context)
        t3 = time.perf_counter()

        retrieval_ms = round((t1 - t0) * 1000, 2)
        assembly_ms = round((t2 - t1) * 1000, 2)
        generation_ms = round((t3 - t2) * 1000, 2)
        total_latency_ms = round((t3 - t0) * 1000, 2)

        logger.info(
            "Query Latency Breakdown: retrieval=%.2fms, assembly=%.2fms, generation=%.2fms (total=%.2fms)",
            retrieval_ms,
            assembly_ms,
            generation_ms,
            total_latency_ms,
        )

        sources: list[dict[str, Any]] = []
        for res in search_results:
            doc = res.document
            symbol = doc.function_name or doc.class_name or None
            sources.append(
                {
                    "repository": doc.repository_name,
                    "file": doc.file_name,
                    "symbol": symbol,
                    "start_line": doc.start_line,
                    "end_line": doc.end_line,
                    "score": round(res.score, 4),
                }
            )

        # Persist query log to database
        self._persist_query_log(
            question=query_clean,
            answer=llm_response.answer,
            provider=llm_response.provider,
            model=llm_response.model,
            latency_ms=llm_response.latency_ms,
        )

        return {
            "answer": llm_response.answer,
            "sources": sources,
            "provider": llm_response.provider,
            "model": llm_response.model,
            "latency_ms": llm_response.latency_ms,
        }

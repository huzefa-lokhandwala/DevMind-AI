"""RAG Service orchestration layer for DevMind AI backend."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.chunking.code_chunker import CodeChunker
from app.db.crud import (
    add_message,
    create_conversation,
    create_or_update_repository,
    get_conversation,
    get_repository_by_name,
    save_query_log,
    save_repository_documents,
    update_conversation_title,
)
from app.db.database import SessionLocal
from app.embeddings.embedding_engine import EmbeddingEngine
from app.llm import BaseLLMProvider, create_fallback_llm_provider
from app.loaders import GitHubLoaderError, GitHubRepositoryLoader, RepositoryLoader
from app.models.document import Document
from app.prompts.context_assembler import ContextAssembler, PromptContext
from app.retrieval.retriever import Retriever
from app.routing.intent_classifier import QueryIntent, classify_intent
from app.services.indexing_coordinator import IndexingCoordinator
from app.utils.title_generator import generate_conversation_title
from app.vector_store.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)


class RepositoryNotIndexedError(Exception):
    """Raised when query is invoked before any repository has been indexed."""


class RepositoryNotFoundError(Exception):
    """Raised when a requested repository is not found or is inaccessible to the authenticated user."""


class InvalidRepositoryError(Exception):
    """Raised when repository path does not exist, is invalid, or contains no indexable files."""


class IndexingInProgressError(Exception):
    """Raised when an indexing request arrives while another indexing job is in progress."""


class IndexingMemoryExceededError(Exception):
    """Raised when repository indexing memory consumption exceeds configured safety circuit breaker."""


def get_process_rss_mb() -> float:
    """Return instantaneous Resident Set Size (RSS) of the current process in Megabytes (MB)."""
    # 1. Linux (/proc/self/status VmRSS) - fast and precise instantaneous RSS
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    return float(parts[1]) / 1024.0
    except (FileNotFoundError, PermissionError, ValueError, IndexError):
        pass

    # 2. macOS (mach_task_basic_info resident_size) - instantaneous RSS
    import sys
    if sys.platform == "darwin":
        try:
            import ctypes
            import ctypes.util
            libc = ctypes.CDLL(ctypes.util.find_library("c"))
            class _MachTaskBasicInfo(ctypes.Structure):
                _fields_ = [
                    ("virtual_size", ctypes.c_uint64),
                    ("resident_size", ctypes.c_uint64),
                    ("resident_size_max", ctypes.c_uint64),
                    ("user_time", ctypes.c_int64 * 2),
                    ("system_time", ctypes.c_int64 * 2),
                    ("policy", ctypes.c_int32),
                    ("suspend_count", ctypes.c_int32),
                ]
            count = ctypes.c_uint32(ctypes.sizeof(_MachTaskBasicInfo) // 4)
            info = _MachTaskBasicInfo()
            task = libc.mach_task_self()
            ret = libc.task_info(task, 20, ctypes.byref(info), ctypes.byref(count))
            if ret == 0:
                return float(info.resident_size) / (1024.0 * 1024.0)
        except Exception:
            pass

    # 3. Fallback to resource getrusage
    import resource
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return (float(rss) / (1024.0 * 1024.0)) if sys.platform == "darwin" else (float(rss) / 1024.0)


class RAGService:
    """Stateful runtime service managing the RAG pipeline lifecycle.

    Reuses EmbeddingEngine and GeminiProvider across requests to avoid model re-initialization.
    Maintains active FAISS vector store state for semantic code queries and persists database metadata.
    """

    DEFAULT_PROCESS_BATCH_SIZE: int = 10
    DEFAULT_MEMORY_LIMIT_MB: float = 600.0 if sys.platform == "darwin" else 400.0

    def __init__(
        self,
        embedding_engine: EmbeddingEngine | None = None,
        llm_provider: BaseLLMProvider | None = None,
        db_session: Session | None = None,
        process_batch_size: int | None = None,
        memory_limit_mb: float | None = None,
        indexing_coordinator: IndexingCoordinator | None = None,
    ) -> None:
        """Initialize RAGService components once at application startup."""
        import os
        import threading
        logger.info("Initializing RAGService lifecycle...")
        self.embedding_engine = embedding_engine or EmbeddingEngine()
        self.llm_provider = llm_provider or create_fallback_llm_provider()
        self.context_assembler = ContextAssembler()
        self.chunker = CodeChunker()
        self.db_session = db_session
        self.indexing_coordinator = indexing_coordinator or IndexingCoordinator()
        self.indexing_coordinator.set_executor(self._execute_indexing_job)

        # Bounded repository processing batch size
        env_batch = os.getenv("REPOSITORY_PROCESS_BATCH_SIZE")
        parsed_batch = self.DEFAULT_PROCESS_BATCH_SIZE
        if env_batch:
            try:
                b = int(env_batch.strip())
                if b > 0:
                    parsed_batch = b
            except (ValueError, TypeError):
                pass
        self.process_batch_size = process_batch_size or parsed_batch

        # Memory circuit breaker limit (default 400 MB for 512 MB Render instance)
        env_limit = os.getenv("INDEX_MEMORY_LIMIT_MB")
        parsed_limit = self.DEFAULT_MEMORY_LIMIT_MB
        if env_limit:
            try:
                lim = float(env_limit.strip())
                if lim > 0:
                    parsed_limit = lim
            except (ValueError, TypeError):
                pass
        self.memory_limit_mb = memory_limit_mb or parsed_limit

        # Concurrency safety lock
        self._indexing_lock = threading.Lock()

        # Runtime indexed state
        self.vector_store: FAISSVectorStore | None = None
        self.retriever: Retriever = Retriever(self.embedding_engine)
        self.indexed_repository_name: str | None = None

    @property
    def is_indexed(self) -> bool:
        """Return True if a repository is currently indexed into vector store."""
        return (
            self.vector_store is not None
            and self.vector_store.total_documents > 0
        )

    def _check_memory_limit(self, stage_name: str) -> None:
        """Evaluate instantaneous RSS against configured safety threshold.

        Note: The application threshold (e.g. 400 MB) is an early warning / safety circuit breaker,
        not a platform guarantee against the hard 512 MB container ceiling.
        """
        import gc
        curr_rss = get_process_rss_mb()
        if curr_rss >= self.memory_limit_mb:
            gc.collect()
            curr_rss = get_process_rss_mb()
            if curr_rss >= self.memory_limit_mb:
                logger.error(
                    "Memory circuit breaker triggered during %s: current RSS (%.2f MB) exceeds safety threshold (%.2f MB)",
                    stage_name,
                    curr_rss,
                    self.memory_limit_mb,
                )
                raise IndexingMemoryExceededError(
                    f"Indexing aborted during {stage_name}: memory consumption ({curr_rss:.2f} MB) exceeded safety threshold ({self.memory_limit_mb:.2f} MB)."
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
                    embedding_provider=self.embedding_engine.provider_name,
                    embedding_model=self.embedding_engine.model_name,
                    embedding_dimension=self.embedding_engine.embedding_dimension,
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
        repository_id: int | None = None,
        db_session: Session | None = None,
    ) -> None:
        """Helper to save query log to PostgreSQL."""
        try:
            db, auto_close = (db_session, False) if db_session is not None else self._get_db_session()
            try:
                repo_id = repository_id
                if repo_id is None and self.indexed_repository_name:
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
        self,
        repository_path: str,
        source_type: str = "local",
        source_override: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Index a local repository incrementally for RAG retrieval and persist to database.

        Processes files in small bounded batches (REPOSITORY_PROCESS_BATCH_SIZE) to ensure
        memory usage does not grow proportionally with repository size.

        Args:
            repository_path: Path to the target local repository folder.
            source_type: Metadata classification ('local' or 'github').
            source_override: Optional source location string if different from repository_path.
            user_id: Optional ID of the authenticated user who owns this repository.

        Returns:
            Dictionary payload describing indexing statistics.

        Raises:
            IndexingInProgressError: If an indexing operation is already running.
            IndexingMemoryExceededError: If RSS exceeds the safety circuit breaker limit.
            InvalidRepositoryError: If path is missing, not a directory, or empty.
        """
        import gc

        if not self._indexing_lock.acquire(blocking=False):
            logger.warning("Indexing rejected: another repository indexing operation is already in progress.")
            raise IndexingInProgressError(
                "Repository indexing is already in progress. Please wait for the current indexing job to complete."
            )

        try:
            path = Path(repository_path).resolve()
            if not path.exists():
                raise InvalidRepositoryError(f"Repository path does not exist: {repository_path}")
            if not path.is_dir():
                raise InvalidRepositoryError(f"Repository path is not a directory: {repository_path}")

            logger.info(
                "[TELEMETRY stage 5] File discovery start for '%s' (batch_size=%d, memory_limit=%.1f MB, RSS=%.2f MB)",
                path.name,
                self.process_batch_size,
                self.memory_limit_mb,
                get_process_rss_mb(),
            )

            try:
                loader = RepositoryLoader(path)
                eligible_paths = loader.iter_file_paths()
            except (FileNotFoundError, NotADirectoryError) as exc:
                raise InvalidRepositoryError(str(exc)) from exc

            if not eligible_paths:
                raise InvalidRepositoryError(f"No supported indexable source files found in {repository_path}")

            total_discovered = len(eligible_paths)
            repo_name = loader.repository_name
            source_loc = source_override or str(path)

            logger.info(
                "[TELEMETRY stage 5] Discovered %d eligible file(s) for repository '%s' (RSS=%.2f MB)",
                total_discovered,
                repo_name,
                get_process_rss_mb(),
            )

            from app.graph.code_graph import CodeGraph
            vector_store = FAISSVectorStore(dimension=self.embedding_engine.embedding_dimension)
            code_graph = CodeGraph()

            total_files_loaded = 0
            total_chunks_created = 0
            total_embeddings_created = 0

            # Obtain persistent database session across batches to avoid connection churn
            db, auto_close = self._get_db_session()
            repo_model = None
            try:
                try:
                    repo_model = create_or_update_repository(
                        db=db,
                        name=repo_name,
                        source=source_loc,
                        source_type=source_type,
                        status="indexing",
                        embedding_provider=self.embedding_engine.provider_name,
                        embedding_model=self.embedding_engine.model_name,
                        embedding_dimension=self.embedding_engine.embedding_dimension,
                        user_id=user_id,
                    )
                except Exception as exc:
                    logger.warning("Failed initializing repository record in database: %s", exc)

                # Stream processing in bounded batches without re-traversing directory
                batch_num = 0
                for file_batch in loader.iter_batches(batch_size=self.process_batch_size, paths=eligible_paths):
                    batch_num += 1
                    self._check_memory_limit(f"batch {batch_num} start")

                    batch_files_count = len(file_batch)
                    total_files_loaded += batch_files_count

                    # AST chunking for this batch
                    batch_chunks = self.chunker.chunk_documents(file_batch)
                    batch_chunks_count = len(batch_chunks)
                    total_chunks_created += batch_chunks_count

                    # Release file batch contents immediately
                    del file_batch

                    # Embed chunks for this batch (batch_size=1)
                    batch_embedded = self.embedding_engine.embed_documents(batch_chunks)
                    batch_embeddings_count = len(batch_embedded)
                    total_embeddings_created += batch_embeddings_count

                    # Check memory after embedding
                    self._check_memory_limit(f"batch {batch_num} post-embedding")

                    # Incrementally add to FAISS index
                    vector_store.add_documents(batch_embedded)

                    # Incrementally add to CodeGraph
                    code_graph.add_documents(batch_embedded)

                    # Incrementally persist to database reusing existing session
                    if repo_model is not None:
                        try:
                            save_repository_documents(
                                db=db,
                                repository_id=repo_model.id,
                                documents=batch_embedded,
                                commit=True,
                            )
                        except Exception as exc:
                            logger.warning("Database persistence failed for batch %d: %s", batch_num, exc)

                    # Release batch objects and collect garbage
                    del batch_chunks
                    del batch_embedded
                    gc.collect()

                    # Check memory after persistence & GC
                    self._check_memory_limit(f"batch {batch_num} post-persistence")

                    logger.info(
                        "[TELEMETRY stage 9] Batch %d complete: processed %d files, %d chunks (Cumulative: %d/%d files, %d chunks, RSS=%.2f MB)",
                        batch_num,
                        batch_files_count,
                        batch_chunks_count,
                        total_files_loaded,
                        total_discovered,
                        total_chunks_created,
                        get_process_rss_mb(),
                    )

                if total_files_loaded == 0:
                    raise InvalidRepositoryError(f"No supported indexable source files found in {repository_path}")

                # Finalize repository status in database
                if repo_model is not None:
                    try:
                        repo_model.status = "indexed"
                        db.commit()
                    except Exception as exc:
                        logger.warning("Failed updating repository final status to indexed: %s", exc)
            finally:
                if auto_close:
                    db.close()

            retriever = Retriever(self.embedding_engine, vector_store, code_graph=code_graph)

            # Update service runtime state
            self.vector_store = vector_store
            self.retriever = retriever
            self.indexed_repository_name = repo_name

            final_rss = get_process_rss_mb()
            logger.info(
                "[TELEMETRY stage 14] Incremental indexing complete for '%s': %d files, %d chunks, %d embeddings (Final RSS=%.2f MB)",
                repo_name,
                total_files_loaded,
                total_chunks_created,
                total_embeddings_created,
                final_rss,
            )

            return {
                "repository": repo_name,
                "files_loaded": total_files_loaded,
                "chunks_created": total_chunks_created,
                "embeddings_created": total_embeddings_created,
                "status": "indexed",
            }
        finally:
            self._indexing_lock.release()

    def index_github_repository(self, github_url: str, user_id: int | None = None) -> dict[str, Any]:
        """Index a public GitHub repository by URL and persist to database.

        Args:
            github_url: Validated HTTPS URL for a public GitHub repository.
            user_id: Optional ID of the authenticated user who owns this repository.

        Returns:
            Dictionary payload matching IndexRepositoryResponse schema.

        Raises:
            IndexingInProgressError: If an indexing operation is already running.
            InvalidRepositoryError: If GitHub validation, cloning, or document loading fails.
        """
        logger.info("[TELEMETRY stage 3] Repository clone start: %s (RSS=%.2f MB)", github_url, get_process_rss_mb())
        github_loader = GitHubRepositoryLoader()
        try:
            local_repo_path = github_loader.clone_repository(github_url)
        except GitHubLoaderError as exc:
            raise InvalidRepositoryError(str(exc)) from exc

        logger.info("[TELEMETRY stage 4] Repository clone complete: %s (RSS=%.2f MB)", local_repo_path, get_process_rss_mb())

        return self.index_repository(
            str(local_repo_path), source_type="github", source_override=github_url, user_id=user_id
        )

    def _execute_indexing_job(
        self, source: str, source_type: str, user_id: int | None = None
    ) -> dict[str, Any]:
        """Internal callback invoked by IndexingCoordinator worker to execute queued indexing."""
        if source_type == "github":
            return self.index_github_repository(source, user_id=user_id)
        return self.index_repository(source, user_id=user_id)

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        session_id: str | None = None,
        conversation_id: str | None = None,
        user_id: int | None = None,
        repository_name: str | None = None,
        db_session: Session | None = None,
    ) -> dict[str, Any]:
        """Query the system using intent routing (GENERAL, REPOSITORY, MIXED).

        Args:
            query_text: User question string.
            top_k: Number of relevant context chunks to retrieve.
            session_id: Optional anonymous browser session identifier.
            conversation_id: Optional conversation identifier for message persistence.
            user_id: Optional ID of the authenticated user making the query.
            repository_name: Optional target repository name to query.
            db_session: Optional active database session.

        Returns:
            Dictionary payload matching QueryResponse schema.

        Raises:
            RepositoryNotIndexedError: If repository question is asked before indexing or access denied.
            ValueError: If query is empty or whitespace-only.
        """
        query_clean = query_text.strip()
        if not query_clean:
            raise ValueError("Query string must not be empty or whitespace-only.")

        # Resolve target repository name
        target_repo_name = repository_name
        if not target_repo_name and conversation_id:
            db_conv, close_conv = (db_session, False) if db_session is not None else self._get_db_session()
            try:
                conv = get_conversation(
                    db_conv, conversation_id=conversation_id, session_id=session_id, user_id=user_id
                )
                if conv and conv.repository_name:
                    target_repo_name = conv.repository_name
            finally:
                if close_conv:
                    db_conv.close()

        # Fallback to self.indexed_repository_name ONLY IF:
        # 1. Unauthenticated / development mode (user_id is None), OR
        # 2. Authenticated user (user_id is not None) explicitly OWNS self.indexed_repository_name.
        # An authenticated user must NEVER inherit a repository belonging to another user.
        if not target_repo_name and self.indexed_repository_name:
            if user_id is None:
                target_repo_name = self.indexed_repository_name
            else:
                db_fb, close_fb = (db_session, False) if db_session is not None else self._get_db_session()
                try:
                    owned_repo = get_repository_by_name(db_fb, self.indexed_repository_name, user_id=user_id)
                    if owned_repo is not None:
                        target_repo_name = self.indexed_repository_name
                finally:
                    if close_fb:
                        db_fb.close()

        # Enforce repository ownership isolation early before routing or retrieval
        if target_repo_name:
            db_check, auto_close_check = (db_session, False) if db_session is not None else self._get_db_session()
            try:
                repo_check = get_repository_by_name(db_check, target_repo_name, user_id=user_id)
                if not repo_check:
                    if user_id is not None:
                        # Resource-safe 404: Do not leak existence or owner of unowned repositories
                        raise RepositoryNotFoundError(
                            f"Repository '{target_repo_name}' not found."
                        )
                    elif self.vector_store is None or self.indexed_repository_name != target_repo_name:
                        # Resource-safe 404: Do not leak existence or owner of unowned repositories
                        raise RepositoryNotFoundError(
                            f"Repository '{target_repo_name}' not found."
                        )
            finally:
                if auto_close_check:
                    db_check.close()

        # Classify intent deterministically without extra LLM overhead
        intent = classify_intent(query_clean)
        # If user explicitly or contextually targeted a repository, ensure repository retrieval is performed
        if target_repo_name and intent == QueryIntent.GENERAL:
            intent = QueryIntent.REPOSITORY
        logger.info("Query '%s' classified as intent: %s", query_clean[:60], intent.value)

        t0 = time.perf_counter()
        sources: list[dict[str, Any]] = []

        if intent == QueryIntent.GENERAL:
            # GENERAL intent: Bypass repository retrieval completely
            prompt_context = self.context_assembler.assemble_general(query_clean)
            t1 = time.perf_counter()
            llm_response = self.llm_provider.generate(prompt_context)
            t2 = time.perf_counter()
            retrieval_ms = 0.0
            assembly_ms = round((t1 - t0) * 1000, 2)
            generation_ms = round((t2 - t1) * 1000, 2)
            repo_model = None
        else:
            # REPOSITORY or MIXED intent: Requires indexed repository
            if not target_repo_name:
                if not self.is_indexed:
                    raise RepositoryNotIndexedError(
                        "No repository has been indexed yet. Call /repositories/index first."
                    )
                if user_id is not None:
                    raise RepositoryNotIndexedError(
                        "Repository context is required for authenticated repository queries. "
                        "Specify 'repository_name' or query within a repository conversation."
                    )
                raise RepositoryNotIndexedError(
                    "No repository has been indexed yet. Call /repositories/index first."
                )

            # Resolve repository model and verify ownership + metadata
            repo_model = None
            db_query, auto_close_query = (db_session, False) if db_session is not None else self._get_db_session()
            try:
                from sqlalchemy import select
                from app.db.models import ChunkModel, FileModel

                if target_repo_name:
                    repo_model = get_repository_by_name(db_query, target_repo_name, user_id=user_id)
                    if not repo_model:
                        if user_id is not None:
                            # Resource-safe 404: Do not leak existence or owner of unowned repositories
                            raise RepositoryNotFoundError(
                                f"Repository '{target_repo_name}' not found."
                            )
                        # Fallback only for in-memory tests without DB persistence where vector_store is loaded
                        elif self.vector_store is not None and self.indexed_repository_name == target_repo_name:
                            repo_model = None
                        else:
                            # Resource-safe 404: Do not leak existence or owner of unowned repositories
                            raise RepositoryNotFoundError(
                                f"Repository '{target_repo_name}' not found."
                            )
                    else:
                        if isinstance(repo_model.embedding_provider, str) and repo_model.embedding_provider != self.embedding_engine.provider_name:
                            raise RepositoryNotIndexedError(
                                f"Repository '{repo_model.name}' was indexed with provider '{repo_model.embedding_provider}', "
                                f"but current query embedding provider is '{self.embedding_engine.provider_name}'. "
                                "Please re-index the repository."
                            )
                        if isinstance(repo_model.embedding_dimension, int) and repo_model.embedding_dimension != self.embedding_engine.embedding_dimension:
                            raise RepositoryNotIndexedError(
                                f"Repository '{repo_model.name}' was indexed with dimension {repo_model.embedding_dimension}d, "
                                f"but current query embedding provider uses {self.embedding_engine.embedding_dimension}d. "
                                "Please re-index the repository."
                            )
                        if isinstance(repo_model.status, str) and repo_model.status != "indexed":
                            raise RepositoryNotIndexedError(
                                f"Repository '{repo_model.name}' is currently {repo_model.status}, not indexed."
                            )
                        null_chunk = db_query.execute(
                            select(ChunkModel.id)
                            .join(FileModel, ChunkModel.file_id == FileModel.id)
                            .where(FileModel.repository_id == repo_model.id, ChunkModel.embedding.is_(None))
                            .limit(1)
                        ).scalar_one_or_none()
                        if null_chunk is not None:
                            raise RepositoryNotIndexedError(
                                f"Repository '{repo_model.name}' has unindexed or invalidated vector embeddings. "
                                "Please re-index the repository."
                            )
                elif not self.is_indexed:
                    raise RepositoryNotIndexedError(
                        "No repository has been indexed yet. Call /repositories/index first."
                    )

                # Enforce vector dimension consistency between runtime vector store and active query embedding engine
                if (
                    self.vector_store is not None
                    and isinstance(self.vector_store.embedding_dimension, int)
                    and self.vector_store.embedding_dimension != self.embedding_engine.embedding_dimension
                ):
                    raise RepositoryNotIndexedError(
                        f"Vector dimension mismatch: repository was indexed with {self.vector_store.embedding_dimension}d, "
                        f"but active query embedding engine uses {self.embedding_engine.embedding_dimension}d. "
                        "Please re-index the repository."
                    )

                t0_retr = time.perf_counter()
                search_results = self.retriever.retrieve(
                    query_clean,
                    k=top_k,
                    repository_id=repo_model.id if repo_model else None,
                    repository_name=target_repo_name,
                    db_session=db_query if repo_model else None,
                )
                t1_retr = time.perf_counter()
            finally:
                if auto_close_query:
                    db_query.close()

            if intent == QueryIntent.MIXED:
                # Custom mixed prompt context
                assembler = ContextAssembler(system_prompt=self.context_assembler.MIXED_SYSTEM_PROMPT)
                prompt_context = assembler.assemble(query_clean, search_results)
            else:
                prompt_context = self.context_assembler.assemble(query_clean, search_results)

            t2_asm = time.perf_counter()
            llm_response = self.llm_provider.generate(prompt_context)
            t3_gen = time.perf_counter()

            retrieval_ms = round((t1_retr - t0_retr) * 1000, 2)
            assembly_ms = round((t2_asm - t1_retr) * 1000, 2)
            generation_ms = round((t3_gen - t2_asm) * 1000, 2)

            for res in search_results:
                doc = res.document
                symbol = doc.function_name or doc.class_name or None
                sources.append(
                    {
                        "repository": doc.repository_name,
                        "file": doc.file_name,
                        "file_path": doc.file_path,
                        "symbol": symbol,
                        "start_line": doc.start_line,
                        "end_line": doc.end_line,
                        "score": round(res.score, 4),
                        "snippet": doc.content[:1500] if doc.content else None,
                        "language": doc.language,
                    }
                )

        total_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(
            "Query Latency Breakdown [%s]: retrieval=%.2fms, assembly=%.2fms, generation=%.2fms (total=%.2fms)",
            intent.value,
            retrieval_ms,
            assembly_ms,
            generation_ms,
            total_latency_ms,
        )

        # Persist query log to database
        self._persist_query_log(
            question=query_clean,
            answer=llm_response.answer,
            provider=llm_response.provider,
            model=llm_response.model,
            latency_ms=llm_response.latency_ms,
            repository_id=repo_model.id if repo_model else None,
            db_session=db_session,
        )

        # Persist conversation & messages if session_id or user_id is provided
        active_conversation_id = conversation_id
        if session_id or user_id:
            try:
                db, auto_close = (db_session, False) if db_session is not None else self._get_db_session()
                try:
                    conv = None
                    if conversation_id:
                        conv = get_conversation(
                            db, conversation_id=conversation_id, session_id=session_id, user_id=user_id
                        )
                    if not conv:
                        new_title = generate_conversation_title(query_clean)
                        conv = create_conversation(
                            db=db,
                            session_id=session_id,
                            user_id=user_id,
                            title=new_title,
                            repository_name=target_repo_name,
                            conversation_id=conversation_id,
                        )
                    elif conv.title in ("New Chat", "General Query") and intent != QueryIntent.GENERAL:
                        # Derive informative title once user asks specific query
                        updated_title = generate_conversation_title(query_clean)
                        update_conversation_title(
                            db, conv.id, session_id=session_id, user_id=user_id, title=updated_title
                        )

                    active_conversation_id = conv.id

                    # Save user message
                    add_message(
                        db=db,
                        conversation_id=conv.id,
                        role="user",
                        content=query_clean,
                        intent=intent.value,
                    )

                    # Save assistant message
                    add_message(
                        db=db,
                        conversation_id=conv.id,
                        role="assistant",
                        content=llm_response.answer,
                        intent=intent.value,
                        sources=sources,
                        provider=llm_response.provider,
                        model=llm_response.model,
                        latency_ms=llm_response.latency_ms,
                    )
                finally:
                    if auto_close:
                        db.close()
            except Exception as exc:
                logger.warning("Failed persisting message to conversation history: %s", exc)

        return {
            "answer": llm_response.answer,
            "sources": sources,
            "provider": llm_response.provider,
            "model": llm_response.model,
            "latency_ms": llm_response.latency_ms,
            "intent": intent.value,
            "conversation_id": active_conversation_id,
        }

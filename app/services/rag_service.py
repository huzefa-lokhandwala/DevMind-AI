"""RAG Service orchestration layer for DevMind AI backend."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.chunking.code_chunker import CodeChunker
from app.embeddings.embedding_engine import EmbeddingEngine
from app.llm.gemini_provider import GeminiProvider
from app.loaders import GitHubLoaderError, GitHubRepositoryLoader, RepositoryLoader
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
    Maintains active FAISS vector store state for semantic code queries.
    """

    def __init__(
        self,
        embedding_engine: EmbeddingEngine | None = None,
        llm_provider: GeminiProvider | None = None,
    ) -> None:
        """Initialize RAGService components once at application startup."""
        logger.info("Initializing RAGService lifecycle...")
        self.embedding_engine = embedding_engine or EmbeddingEngine()
        self.llm_provider = llm_provider or GeminiProvider()
        self.context_assembler = ContextAssembler()
        self.chunker = CodeChunker()

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

    def index_repository(self, repository_path: str) -> dict[str, Any]:
        """Index a local repository for RAG retrieval.

        Args:
            repository_path: Path to the target local repository folder.

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

        retriever = Retriever(self.embedding_engine, vector_store)

        # Update service runtime state
        self.vector_store = vector_store
        self.retriever = retriever
        self.indexed_repository_name = loader.repository_name

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
        """Index a public GitHub repository by URL.

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

        return self.index_repository(str(local_repo_path))

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

        search_results = self.retriever.retrieve(query_clean, k=top_k)
        prompt_context = self.context_assembler.assemble(query_clean, search_results)
        llm_response = self.llm_provider.generate(prompt_context)

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

        return {
            "answer": llm_response.answer,
            "sources": sources,
            "provider": llm_response.provider,
            "model": llm_response.model,
            "latency_ms": llm_response.latency_ms,
        }

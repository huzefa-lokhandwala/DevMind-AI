"""Retriever module for DevMind AI semantic and hybrid search."""

from __future__ import annotations

import logging

from app.embeddings.embedding_engine import EmbeddingEngine
from app.models.search_result import SearchResult
from app.retrieval.config import RetrievalConfig
from app.retrieval.reranker import CodeReranker
from app.vector_store.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.graph.code_graph import CodeGraph
from app.retrieval.query_classifier import QueryClassifier, QueryIntent


class Retriever:
    """Coordinates vector search, candidate retrieval, hybrid reranking, and threshold filtering."""

    def __init__(
        self,
        embedding_engine: EmbeddingEngine,
        vector_store: FAISSVectorStore | None = None,
        config: RetrievalConfig | None = None,
        reranker: CodeReranker | None = None,
        code_graph: CodeGraph | None = None,
    ) -> None:
        """Initialize Retriever dependencies."""
        self._embedding_engine = embedding_engine
        self._vector_store = vector_store
        self.config = config or RetrievalConfig()
        self._reranker = reranker or CodeReranker(config=self.config)
        self.code_graph = code_graph or CodeGraph()

    def retrieve(
        self,
        query: str,
        k: int = 5,
        repository_id: int | None = None,
        repository_name: str | None = None,
        db_session: Session | None = None,
        similarity_threshold: float | None = None,
    ) -> list[SearchResult]:
        """Perform hybrid retrieval, reranking, and similarity threshold filtering.

        Supports both database-backed repository-scoped retrieval (PostgreSQL/pgvector)
        and in-memory vector store retrieval (FAISS fallback for offline testing).

        Args:
            query: Natural language query string.
            k: Maximum number of top search results to return.
            repository_id: Optional target repository database ID for authoritative isolation.
            repository_name: Optional repository name filter for isolation.
            db_session: Optional active database session for pgvector retrieval.
            similarity_threshold: Optional similarity threshold override. Defaults to config threshold.

        Returns:
            Ranked list of ``SearchResult`` items, filtered and ordered by descending relevance.
        """
        if not query or not query.strip():
            logger.warning("Empty query string passed to Retriever.retrieve.")
            return []

        threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else self.config.similarity_threshold
        )

        fetch_k = max(k, self.config.initial_k)
        logger.info("Retrieving initial top-%d candidates for query: '%s'", fetch_k, query)

        query_embedding = self._embedding_engine.embed_query(query)

        # 1. Authoritative repository-scoped retrieval from PostgreSQL via pgvector
        if db_session is not None and repository_id is not None:
            from app.db.crud import search_repository_chunks

            raw_matches = search_repository_chunks(
                db=db_session,
                repository_id=repository_id,
                query_vector=query_embedding,
                top_k=fetch_k,
            )
            logger.info("Retrieved %d candidate(s) from persistent database for repo %d", len(raw_matches), repository_id)
        elif self._vector_store is not None:
            raw_matches = self._vector_store.search(
                query_embedding, k=fetch_k, repository_name=repository_name
            )
            logger.info("Retrieved %d candidate(s) from FAISS vector store", len(raw_matches))
        else:
            logger.warning("No vector store or database session provided to Retriever.")
            raw_matches = []

        if not raw_matches:
            logger.info("Vector retrieval returned 0 candidates for query.")
            return []

        # Convert raw vector store matches to SearchResults
        candidates: list[SearchResult] = [
            SearchResult(rank=rank, score=score, document=doc)
            for rank, (doc, score) in enumerate(raw_matches, start=1)
        ]

        logger.info("Retrieved %d raw candidate(s) from FAISS vector store", len(candidates))

        # Apply hybrid reranking if enabled
        if self.config.enable_reranking:
            ranked_results = self._reranker.rerank(query, candidates, top_k=fetch_k)
        else:
            ranked_results = candidates

        # Filter by similarity threshold
        filtered_results = [r for r in ranked_results if r.score >= threshold]
        logger.info(
            "Filtered %d candidate(s) down to %d result(s) above threshold %.2f",
            len(ranked_results),
            len(filtered_results),
            threshold,
        )

        # Slice to final target k and re-assign 1-based ranks
        final_results: list[SearchResult] = []
        for new_rank, res in enumerate(filtered_results[:k], start=1):
            final_results.append(
                SearchResult(
                    rank=new_rank,
                    score=res.score,
                    document=res.document,
                )
            )

        logger.info("Retriever produced %d final SearchResult(s)", len(final_results))
        return final_results

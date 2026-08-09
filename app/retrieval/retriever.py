"""Retriever module for DevMind AI semantic and hybrid search."""

from __future__ import annotations

import logging

from app.embeddings.embedding_engine import EmbeddingEngine
from app.models.search_result import SearchResult
from app.retrieval.config import RetrievalConfig
from app.retrieval.reranker import CodeReranker
from app.vector_store.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """Coordinates vector search, candidate retrieval, hybrid reranking, and threshold filtering."""

    def __init__(
        self,
        embedding_engine: EmbeddingEngine,
        vector_store: FAISSVectorStore,
        config: RetrievalConfig | None = None,
        reranker: CodeReranker | None = None,
    ) -> None:
        """Initialize Retriever dependencies.

        Args:
            embedding_engine: Loaded embedding engine for vectorizing text queries.
            vector_store: Indexed FAISS vector store for semantic similarity search.
            config: Optional RetrievalConfig settings (defaults to RetrievalConfig()).
            reranker: Optional CodeReranker instance.
        """
        self._embedding_engine = embedding_engine
        self._vector_store = vector_store
        self.config = config or RetrievalConfig()
        self._reranker = reranker or CodeReranker(config=self.config)

    def retrieve(
        self,
        query: str,
        k: int = 5,
        similarity_threshold: float | None = None,
    ) -> list[SearchResult]:
        """Perform hybrid retrieval, reranking, and similarity threshold filtering.

        Args:
            query: Natural language query string.
            k: Maximum number of top search results to return.
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
        raw_matches = self._vector_store.search(query_embedding, k=fetch_k)

        if not raw_matches:
            logger.info("Vector store returned 0 candidates for query.")
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

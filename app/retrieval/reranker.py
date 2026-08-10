"""Deterministic hybrid reranker for code search results."""

from __future__ import annotations

import logging
from typing import Sequence

from app.models.search_result import SearchResult
from app.retrieval.config import RetrievalConfig
from app.retrieval.keyword_matcher import KeywordMatcher

logger = logging.getLogger(__name__)


class CodeReranker:
    """Reranks vector search candidates using a transparent hybrid scoring model combining:
    - Semantic vector similarity
    - Lexical keyword match ratio
    - Code symbol (function/class/filename) match signals
    """

    def __init__(
        self,
        config: RetrievalConfig | None = None,
        matcher: KeywordMatcher | None = None,
    ) -> None:
        """Initialize CodeReranker.

        Args:
            config: Optional RetrievalConfig settings.
            matcher: Optional KeywordMatcher helper.
        """
        self.config = config or RetrievalConfig()
        self.matcher = matcher or KeywordMatcher()

    def rerank(
        self,
        query: str,
        results: Sequence[SearchResult],
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """Rerank candidate search results deterministically.

        Args:
            query: Natural language query string.
            results: Candidate SearchResult list produced by vector retrieval.
            top_k: Optional target limit for returned top results.

        Returns:
            New list of SearchResult items sorted by descending hybrid relevance score.
            Document instances remain unmutated.
        """
        if not results:
            return []

        limit = top_k or self.config.final_k
        query_tokens = self.matcher.tokenize(query)
        is_impl_query = self._is_implementation_query(query)

        scored_candidates: list[tuple[float, SearchResult]] = []

        for res in results:
            doc = res.document

            # 1. Direct Normalized Cosine Similarity Score (0.0 - 1.0)
            norm_semantic = max(0.0, min(1.0, res.score))

            # 2. Lexical Keyword Overlap Score (0.0 - 1.0)
            doc_tokens = self.matcher.tokenize(doc.content)
            lexical_score = self.matcher.compute_lexical_score(query_tokens, doc_tokens)

            # 3. Symbol Boost Signal (0.0 or 1.0)
            symbol_boost_signal = self.matcher.detect_symbol_match(query_tokens, doc)

            # 4. Code Category Modifier
            category_modifier = self._get_category_modifier(doc.file_path, is_impl_query)

            # 5. Combined Score Calculation
            combined_score = (
                (self.config.semantic_weight * norm_semantic)
                + (self.config.keyword_weight * lexical_score)
                + (self.config.symbol_boost * symbol_boost_signal)
                + category_modifier
            )

            # Clamp final score into standard [0.0, 1.0] range
            final_score = round(max(0.0, min(1.0, combined_score)), 4)
            scored_candidates.append((final_score, res))

        # Sort candidates descending by hybrid score, maintaining deterministic tie-breaking by original rank
        scored_candidates.sort(key=lambda item: (item[0], -item[1].rank), reverse=True)

        reranked_results: list[SearchResult] = []
        for new_rank, (score, original_res) in enumerate(scored_candidates[:limit], start=1):
            reranked_results.append(
                SearchResult(
                    rank=new_rank,
                    score=score,
                    document=original_res.document,
                )
            )

        logger.info(
            "Reranked %d candidate(s) to top-%d results (top score=%.4f)",
            len(results),
            len(reranked_results),
            reranked_results[0].score if reranked_results else 0.0,
        )

        return reranked_results

    def _is_implementation_query(self, query: str) -> bool:
        """Check if query is asking for code implementation, definition, or flow."""
        q_lower = query.lower()
        keywords = {
            "where", "how", "implemented", "implementation", "calculated",
            "calculation", "code", "function", "class", "module", "api",
            "route", "model", "schema", "trace", "show", "definition", "source",
            "page", "prisma", "models"
        }
        return any(kw in q_lower for kw in keywords)

    def _get_category_modifier(self, doc_path: str, is_impl_query: bool) -> float:
        """Compute score modifier based on code category and query intent."""
        path_lower = (doc_path or "").lower()

        is_test = (
            "test" in path_lower
            or path_lower.endswith(".test.ts")
            or path_lower.endswith(".test.js")
            or path_lower.endswith(".test.py")
            or path_lower.endswith("_test.py")
            or path_lower.endswith(".spec.ts")
            or path_lower.endswith(".spec.js")
        )
        is_doc = (
            path_lower.endswith(".md")
            or path_lower.endswith(".rst")
            or path_lower.endswith(".txt")
            or "/docs/" in path_lower
            or "readme" in path_lower
            or "architecture" in path_lower
            or "api_docs" in path_lower
        )
        is_config = (
            path_lower.endswith(".json")
            or path_lower.endswith(".yaml")
            or path_lower.endswith(".yml")
            or "config" in path_lower
            or path_lower.endswith("openapi.json")
        )

        if is_impl_query:
            if is_test:
                return -0.15
            if is_doc:
                return -0.12
            if is_config:
                return -0.08
            return 0.10

        return 0.0

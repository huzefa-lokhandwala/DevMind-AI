"""Context Assembly Engine for DevMind AI prompt construction."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.models.search_result import SearchResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PromptContext:
    """Structured, provider-agnostic prompt payload ready for LLM consumption."""

    system_prompt: str

    user_question: str

    retrieved_context: str

    citations: list[dict[str, Any]] = field(default_factory=list)


class ContextAssembler:
    """Assembles retrieved search results into a clean, deduplicated PromptContext."""

    DEFAULT_SYSTEM_PROMPT = (
        "You are DevMind AI, an expert Senior Software Engineer and Codebase Assistant.\n"
        "Answer the user's question using ONLY the provided code chunks and citations below.\n"
        "If the information is not present in the context, explicitly state that you do not know.\n"
        "Always reference the relevant file names, line numbers, and function names in your explanation."
    )

    def __init__(self, system_prompt: str | None = None) -> None:
        """Initialize ContextAssembler with an optional custom system prompt.

        Args:
            system_prompt: Custom system prompt text. Defaults to ``DEFAULT_SYSTEM_PROMPT``.
        """
        self._system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT

    def assemble(
        self,
        query: str,
        results: list[SearchResult],
        max_chars: int | None = 8000,
    ) -> PromptContext:
        """Transform search results into a deduplicated, formatted PromptContext.

        Args:
            query: User natural language question.
            results: Ranked search results from the Retriever module.
            max_chars: Maximum character limit for the retrieved context block.

        Returns:
            Structured ``PromptContext`` object containing system prompt, user question,
            formatted code context, and citations list.
        """
        if not results:
            logger.info("Empty search results passed to ContextAssembler.")
            return PromptContext(
                system_prompt=self._system_prompt,
                user_question=query,
                retrieved_context="No relevant code context found.",
                citations=[],
            )

        deduped_results: list[SearchResult] = []
        seen_keys: set[tuple[str, int | None, int | None, str]] = set()

        for res in results:
            doc = res.document
            dedupe_key = (doc.file_path, doc.start_line, doc.end_line, doc.content)
            if dedupe_key in seen_keys:
                logger.debug("Skipping duplicate document chunk: %s", doc.file_path)
                continue
            seen_keys.add(dedupe_key)
            deduped_results.append(res)

        context_blocks: list[str] = []
        citations: list[dict[str, Any]] = []
        current_length = 0

        for new_rank, res in enumerate(deduped_results, start=1):
            doc = res.document
            line_str = (
                f"{doc.start_line}-{doc.end_line}"
                if doc.start_line is not None and doc.end_line is not None
                else "-"
            )
            symbol_name = doc.function_name or doc.class_name or "-"

            header = (
                f"--- [Chunk {new_rank}] "
                f"Repository: {doc.repository_name} | "
                f"File: {doc.file_name} | "
                f"Symbol: {symbol_name} | "
                f"Lines: {line_str} ---"
            )
            block = f"{header}\n{doc.content.strip()}\n"

            if max_chars is not None and (current_length + len(block) > max_chars):
                logger.warning(
                    "Context limit reached (%d chars). Truncating remaining %d chunk(s).",
                    max_chars,
                    len(deduped_results) - new_rank + 1,
                )
                break

            context_blocks.append(block)
            current_length += len(block)

            citations.append(
                {
                    "rank": new_rank,
                    "score": round(res.score, 4),
                    "repository": doc.repository_name,
                    "file_name": doc.file_name,
                    "file_path": doc.file_path,
                    "chunk_type": doc.chunk_type,
                    "function_name": doc.function_name,
                    "class_name": doc.class_name,
                    "start_line": doc.start_line,
                    "end_line": doc.end_line,
                }
            )

        full_context = "\n".join(context_blocks).strip()

        logger.info(
            "Assembled PromptContext with %d chunk(s) (%d chars total)",
            len(citations),
            len(full_context),
        )

        return PromptContext(
            system_prompt=self._system_prompt,
            user_question=query,
            retrieved_context=full_context,
            citations=citations,
        )

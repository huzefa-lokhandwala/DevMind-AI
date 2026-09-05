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
        "STRICT GROUNDING & EXECUTION FLOW RULES:\n"
        "1. Answer using ONLY the retrieved code chunks below as verified ground truth.\n"
        "2. Structure your answers systematically using clean Markdown: provide a direct answer first, followed by clear sections, bullet points, or concise code blocks where helpful. For simple questions, keep the answer concise.\n"
        "3. NEVER claim function A calls function B unless explicit call/import evidence exists in the retrieved context.\n"
        "4. NEVER merge separate API routes (e.g. /api/verify vs /api/sync/github) into a single flow unless call graph evidence proves one route calls the other. Always present distinct API entry points as separate execution flows (FLOW A, FLOW B).\n"
        "5. NEVER describe a hash as deterministic if runtime-varying input like Date.now() participates.\n"
        "6. NEVER claim cryptographic asymmetric key signing unless actual private key signing material is present.\n"
        "7. Reference source files and line ranges naturally in your prose using backticks or citation markers (e.g. `lib/verification/engine.ts:20-45` or [1]). Do NOT fabricate line numbers or files.\n"
        "8. Clearly label any unverified inference or missing context.\n"
        "9. Do NOT generate a redundant 'Sources' or 'Citations' section at the end of your response, as the application interface automatically renders the retrieved source evidence cards."
    )

    GENERAL_SYSTEM_PROMPT = (
        "You are DevMind AI, an expert, friendly Senior Software Engineer and AI Assistant.\n"
        "GUIDELINES:\n"
        "1. Answer the user's general or conceptual question directly, accurately, and engagingly.\n"
        "2. Use structured Markdown with concise explanations, code examples, bullet points, or analogies where helpful.\n"
        "3. For greetings and casual conversation, respond naturally and warmly as a helpful assistant.\n"
        "4. Do NOT say 'I found no matching repository evidence' or 'this repository does not contain information about this'.\n"
        "5. Do NOT reference unneeded repository mechanisms or fabricate citations."
    )

    MIXED_SYSTEM_PROMPT = (
        "You are DevMind AI, an expert Senior Software Engineer and Codebase Assistant.\n"
        "The user is asking BOTH a general conceptual question and a repository-specific question.\n"
        "GUIDELINES:\n"
        "1. FIRST provide a clear, concise general technical explanation of the requested concept.\n"
        "2. THEN clearly explain how this specific repository implements, configures, or uses the concept using ONLY the retrieved code context below.\n"
        "3. Clearly separate the general explanation from the repository-specific implementation details using Markdown headers or sections.\n"
        "4. Ground all repository claims strictly on the retrieved code chunks.\n"
        "5. Do NOT generate a redundant 'Sources' or 'Citations' section at the end of your response."
    )

    def assemble_general(self, query: str) -> PromptContext:
        """Assemble PromptContext for general/conversational queries without codebase retrieval."""
        return PromptContext(
            system_prompt=self.GENERAL_SYSTEM_PROMPT,
            user_question=query,
            retrieved_context="",
            citations=[],
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
            evidence_lvl = getattr(doc, "evidence_level", "HIGH") or "HIGH"
            header = (
                f"--- [Chunk {new_rank}] "
                f"Repository: {doc.repository_name} | "
                f"File: {doc.file_path}:{line_str} | "
                f"Symbol: {symbol_name} | "
                f"Evidence: {evidence_lvl} ---"
            )
            raw_content = doc.content.strip()
            block = f"{header}\n{raw_content}\n"

            if max_chars is not None and (current_length + len(block) > max_chars):
                avail_space = max_chars - current_length
                header_overhead = len(header) + 1
                avail_content_chars = avail_space - header_overhead - 20

                if avail_content_chars >= 50:
                    truncated_content = (
                        raw_content[:avail_content_chars].rstrip()
                        + "\n... [truncated]"
                    )
                    block = f"{header}\n{truncated_content}\n"
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

                logger.warning(
                    "Context limit reached (%d chars). Truncated chunk %d and stopping remaining %d chunk(s).",
                    max_chars,
                    new_rank,
                    len(deduped_results) - new_rank,
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

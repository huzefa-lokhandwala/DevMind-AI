"""Google Gemini LLM provider implementation for DevMind AI."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.llm.base_provider import BaseLLMProvider
from app.models.llm_response import LLMResponse
from app.prompts.context_assembler import PromptContext

logger = logging.getLogger(__name__)

load_dotenv()


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider using official google-genai SDK."""

    DEFAULT_MODEL_NAME = "gemini-2.5-flash"

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        client: genai.Client | None = None,
    ) -> None:
        """Initialize GeminiProvider.

        Args:
            api_key: Optional Gemini API key. Defaults to environment variable
                ``GEMINI_API_KEY`` or ``GOOGLE_API_KEY``.
            model_name: Optional Gemini model identifier. Defaults to ``gemini-2.5-flash``.
            client: Optional pre-configured ``genai.Client`` (useful for mocking/testing).
        """
        self._api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        self._model_name = model_name or self.DEFAULT_MODEL_NAME

        if client is not None:
            self._client = client
        elif self._api_key:
            self._client = genai.Client(api_key=self._api_key)
        else:
            logger.warning(
                "Gemini API key not found in environment. "
                "Provider initialized in unauthenticated mode."
            )
            self._client = None  # type: ignore[assignment]

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "gemini"

    @property
    def model_name(self) -> str:
        """Return configured model name."""
        return self._model_name

    def generate(self, context: PromptContext) -> LLMResponse:
        """Generate LLM response using Google Gemini API.

        Args:
            context: PromptContext payload containing system prompt, query, and context.

        Returns:
            Standardized ``LLMResponse`` object.
        """
        if self._client is None:
            raise ValueError(
                "Gemini API key missing. Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variable."
            )

        prompt_body = (
            f"RETRIEVED CODE CONTEXT:\n"
            f"{context.retrieved_context}\n\n"
            f"USER QUESTION:\n"
            f"{context.user_question}"
        )

        config = types.GenerateContentConfig(
            system_instruction=context.system_prompt
        )

        logger.info(
            "Sending request to Gemini model '%s' (provider=gemini)",
            self._model_name,
        )

        start_time = time.perf_counter()
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt_body,
            config=config,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        answer = response.text or ""

        # Extract usage tokens if available
        usage_tokens: dict[str, int] | None = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            um = response.usage_metadata
            usage_tokens = {
                "prompt_tokens": getattr(um, "prompt_token_count", 0) or 0,
                "candidates_tokens": getattr(um, "candidates_token_count", 0) or 0,
                "total_tokens": getattr(um, "total_token_count", 0) or 0,
            }

        # Extract finish reason if available
        finish_reason: str | None = None
        if hasattr(response, "candidates") and response.candidates:
            first_cand = response.candidates[0]
            if hasattr(first_cand, "finish_reason") and first_cand.finish_reason:
                finish_reason = str(first_cand.finish_reason)

        logger.info(
            "Gemini response received in %.2f ms (model=%s)",
            latency_ms,
            self._model_name,
        )

        return LLMResponse(
            answer=answer,
            provider=self.provider_name,
            model=self._model_name,
            latency_ms=round(latency_ms, 2),
            usage_tokens=usage_tokens,
            finish_reason=finish_reason,
        )

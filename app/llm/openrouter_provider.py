"""OpenRouter LLM provider implementation for DevMind AI."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
import httpx

from app.llm.base_provider import BaseLLMProvider
from app.llm.exceptions import NonRetryableProviderError, RetryableProviderError
from app.models.llm_response import LLMResponse
from app.prompts.context_assembler import PromptContext

logger = logging.getLogger(__name__)

load_dotenv()


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter LLM provider using OpenAI-compatible chat completions REST API via httpx."""

    DEFAULT_MODEL_NAME = "openai/gpt-4o-mini"
    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_TIMEOUT_SECONDS = 30.0

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Initialize OpenRouterProvider.

        Args:
            api_key: Optional OpenRouter API key. Defaults to OPENROUTER_API_KEY.
            model_name: Optional model identifier. Defaults to OPENROUTER_MODEL or gpt-4o-mini.
            base_url: Optional base URL. Defaults to OPENROUTER_BASE_URL.
            timeout_seconds: Request timeout in seconds. Defaults to OPENROUTER_TIMEOUT_SECONDS.
            http_client: Optional pre-configured httpx.Client (useful for testing/mocking).
        """
        if api_key is not None:
            self._api_key = api_key.strip() or None
        else:
            self._api_key = os.getenv("OPENROUTER_API_KEY", "").strip() or None
        self._model_name = model_name or os.getenv("OPENROUTER_MODEL", "").strip() or self.DEFAULT_MODEL_NAME
        self._base_url = (base_url or os.getenv("OPENROUTER_BASE_URL", "").strip() or self.DEFAULT_BASE_URL).rstrip("/")

        raw_timeout = os.getenv("OPENROUTER_TIMEOUT_SECONDS", "")
        if timeout_seconds is not None:
            self._timeout_seconds = timeout_seconds
        elif raw_timeout.strip():
            try:
                self._timeout_seconds = float(raw_timeout.strip())
            except ValueError:
                self._timeout_seconds = self.DEFAULT_TIMEOUT_SECONDS
        else:
            self._timeout_seconds = self.DEFAULT_TIMEOUT_SECONDS

        self._http_client = http_client

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "openrouter"

    @property
    def model_name(self) -> str:
        """Return configured model name."""
        return self._model_name

    @property
    def is_configured(self) -> bool:
        """Return True if API key is present."""
        return bool(self._api_key)

    def generate(self, context: PromptContext) -> LLMResponse:
        """Generate LLM response via OpenRouter chat completions.

        Args:
            context: PromptContext containing system prompt, query, and context.

        Returns:
            Standardized LLMResponse object.
        """
        if not self._api_key:
            raise ValueError("OpenRouter API key missing. Please set OPENROUTER_API_KEY environment variable.")

        user_content = (
            f"RETRIEVED CODE CONTEXT:\n"
            f"{context.retrieved_context}\n\n"
            f"USER QUESTION:\n"
            f"{context.user_question}"
        )

        messages = [
            {"role": "system", "content": context.system_prompt},
            {"role": "user", "content": user_content},
        ]

        payload = {
            "model": self._model_name,
            "messages": messages,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/huzefa-lokhandwala/DevMind-AI",
            "X-Title": "DevMind AI",
        }

        url = f"{self._base_url}/chat/completions"
        logger.info("Sending request to OpenRouter model '%s' (url=%s)", self._model_name, url)

        start_time = time.perf_counter()

        def _do_request(client: httpx.Client) -> httpx.Response:
            return client.post(url, json=payload, headers=headers)

        try:
            if self._http_client is not None:
                resp = _do_request(self._http_client)
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    resp = _do_request(client)
        except httpx.TimeoutException as exc:
            raise RetryableProviderError(
                f"OpenRouter request timed out after {self._timeout_seconds}s: {exc}",
                provider=self.provider_name,
            ) from exc
        except httpx.NetworkError as exc:
            raise RetryableProviderError(
                f"OpenRouter network connection error: {exc}",
                provider=self.provider_name,
            ) from exc

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if resp.status_code in (429, 500, 502, 503, 504):
            raise RetryableProviderError(
                f"OpenRouter transient error ({resp.status_code}): {resp.text[:200]}",
                provider=self.provider_name,
                status_code=resp.status_code,
            )
        elif resp.status_code >= 400:
            raise NonRetryableProviderError(
                f"OpenRouter error ({resp.status_code}): {resp.text[:200]}",
                provider=self.provider_name,
                status_code=resp.status_code,
            )

        try:
            data = resp.json()
        except Exception as exc:
            raise RetryableProviderError(
                f"OpenRouter returned malformed non-JSON response: {exc}",
                provider=self.provider_name,
            ) from exc

        choices = data.get("choices", [])
        if not choices:
            raise RetryableProviderError(
                "OpenRouter returned empty choices array in response.",
                provider=self.provider_name,
            )

        first_choice = choices[0]
        answer = first_choice.get("message", {}).get("content", "") or ""
        finish_reason = first_choice.get("finish_reason")

        raw_usage = data.get("usage", {})
        usage_tokens: dict[str, int] | None = None
        if isinstance(raw_usage, dict) and raw_usage:
            usage_tokens = {
                "prompt_tokens": int(raw_usage.get("prompt_tokens", 0) or 0),
                "candidates_tokens": int(raw_usage.get("completion_tokens", 0) or 0),
                "total_tokens": int(raw_usage.get("total_tokens", 0) or 0),
            }

        logger.info(
            "OpenRouter response received in %.2f ms (model=%s)",
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

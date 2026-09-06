"""Multi-provider LLM fallback router for DevMind AI.

Manages ordered fallback chain:
1. Google Gemini (primary)
2. OpenRouter (first fallback)
3. xAI Grok (second fallback)
"""

from __future__ import annotations

import logging
from typing import Sequence

from app.llm.base_provider import BaseLLMProvider
from app.llm.exceptions import (
    AllProvidersFailedError,
    LLMProviderError,
    NonRetryableProviderError,
    RetryableProviderError,
)
from app.llm.gemini_provider import GeminiProvider
from app.llm.openrouter_provider import OpenRouterProvider
from app.llm.xai_provider import XAIProvider
from app.models.llm_response import LLMResponse
from app.prompts.context_assembler import PromptContext

logger = logging.getLogger(__name__)


class FallbackLLMProvider(BaseLLMProvider):
    """Router that attempts generation across a prioritized chain of LLM providers.

    Only transient failures (HTTP 429, 5xx, timeouts, network errors) trigger fallback.
    Deterministic failures (HTTP 400, bad requests) fail fast without cycling providers.
    Unconfigured providers are cleanly bypassed.
    """

    def __init__(self, providers: Sequence[BaseLLMProvider] | None = None) -> None:
        """Initialize FallbackLLMProvider.

        Args:
            providers: Ordered sequence of BaseLLMProvider instances.
        """
        self._providers: list[BaseLLMProvider] = list(providers) if providers else []

    @property
    def providers(self) -> list[BaseLLMProvider]:
        """Return registered providers list."""
        return list(self._providers)

    @property
    def provider_name(self) -> str:
        """Return identifier for primary provider or router."""
        if self._providers:
            return self._providers[0].provider_name
        return "fallback_router"

    @property
    def model_name(self) -> str:
        """Return model identifier of primary provider."""
        if self._providers:
            return self._providers[0].model_name
        return "multi-provider"

    @property
    def is_configured(self) -> bool:
        """Return True if at least one provider has credentials configured."""
        return any(p.is_configured for p in self._providers)

    def generate(self, context: PromptContext) -> LLMResponse:
        """Execute generation trying providers in priority order.

        Args:
            context: PromptContext payload.

        Returns:
            LLMResponse from the first provider that succeeds.

        Raises:
            AllProvidersFailedError: If all configured providers fail with retryable errors.
            NonRetryableProviderError: If a provider fails with a non-retryable error.
        """
        configured_providers = [p for p in self._providers if p.is_configured]

        if not configured_providers:
            raise AllProvidersFailedError(
                "No LLM providers are configured with valid API keys. "
                "Please configure GEMINI_API_KEY, OPENROUTER_API_KEY, or XAI_API_KEY."
            )

        failures: list[dict[str, str]] = []

        for idx, provider in enumerate(configured_providers):
            p_name = provider.provider_name
            m_name = provider.model_name
            logger.info("LLM provider attempt: %s (model=%s, priority=%d/%d)", p_name, m_name, idx + 1, len(configured_providers))

            try:
                response = provider.generate(context)
                logger.info("LLM provider succeeded: %s (model=%s, latency=%.2fms)", p_name, m_name, response.latency_ms)
                return response
            except RetryableProviderError as exc:
                err_summary = exc.message
                logger.warning(
                    "LLM provider failed: %s, reason=%s. Falling back to next provider...",
                    p_name,
                    err_summary,
                )
                failures.append({"provider": p_name, "error": err_summary})
            except NonRetryableProviderError as exc:
                logger.error(
                    "LLM provider failed with non-retryable error: %s (reason=%s). Aborting fallback.",
                    p_name,
                    exc.message,
                )
                raise
            except Exception as exc:
                err_str = str(exc)
                # Check for transient network/timeout keywords in generic exceptions
                is_transient = any(
                    k in err_str.lower()
                    for k in ("timeout", "timed out", "connection", "rate limit", "503", "502", "504", "429")
                )
                if is_transient:
                    logger.warning(
                        "LLM provider unexpected transient failure: %s, error=%s. Falling back...",
                        p_name,
                        err_str,
                    )
                    failures.append({"provider": p_name, "error": err_str})
                else:
                    logger.error("LLM provider fatal error: %s, error=%s", p_name, err_str)
                    raise

        # If all providers exhausted
        summary_lines = [f"{f['provider']}: {f['error']}" for f in failures]
        logger.error("All %d configured LLM providers failed: %s", len(configured_providers), "; ".join(summary_lines))
        raise AllProvidersFailedError(
            f"All configured LLM providers failed. Attempted: {', '.join(f['provider'] for f in failures)}."
        )


def create_fallback_llm_provider() -> FallbackLLMProvider:
    """Instantiate the standard three-tier fallback router (Gemini -> OpenRouter -> xAI Grok).

    Unconfigured providers are initialized safely and filtered dynamically during routing.
    """
    gemini = GeminiProvider()
    openrouter = OpenRouterProvider()
    xai = XAIProvider()

    return FallbackLLMProvider(providers=[gemini, openrouter, xai])

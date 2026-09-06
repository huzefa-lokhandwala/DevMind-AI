"""Exception hierarchy for LLM providers in DevMind AI."""

from __future__ import annotations


class LLMProviderError(Exception):
    """Base exception for all LLM provider errors."""

    def __init__(self, message: str, provider: str | None = None, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code


class RetryableProviderError(LLMProviderError):
    """Transient error indicating the provider failed temporarily and fallback should be attempted.

    Examples:
        - HTTP 429 (Rate limit / Quota exceeded)
        - HTTP 500, 502, 503, 504 (Upstream server errors)
        - Network connection timeouts and socket connection errors
    """


class NonRetryableProviderError(LLMProviderError):
    """Deterministic failure indicating the request itself is invalid or unrecoverable.

    Examples:
        - HTTP 400 (Bad request / Malformed context)
        - Authentication rejection (Invalid API key configured)
    """


class AllProvidersFailedError(LLMProviderError):
    """Raised when every configured LLM provider in the fallback chain has failed."""

    def __init__(self, message: str = "All configured LLM providers failed or were unavailable.") -> None:
        super().__init__(message)

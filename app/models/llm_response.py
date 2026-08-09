"""LLMResponse model for DevMind AI provider layer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LLMResponse:
    """Standardized, provider-agnostic response payload returned by LLM providers."""

    answer: str

    provider: str

    model: str

    latency_ms: float

    usage_tokens: dict[str, int] | None = field(default=None)

    finish_reason: str | None = field(default=None)

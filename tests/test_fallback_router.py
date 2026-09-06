"""Unit and integration tests for Multi-Provider AI Fallback Router.

Covers scenarios A through L:
A. Gemini success -> primary returns immediately, no fallbacks called.
B. Gemini 429 rate limit -> OpenRouter called and succeeds.
C. Gemini timeout -> OpenRouter called and succeeds.
D. Gemini 5xx -> OpenRouter called and succeeds.
E. OpenRouter failure -> xAI Grok called.
F. xAI Grok success -> provider/model metadata reflects Grok.
G. All providers fail -> AllProvidersFailedError raised, no secrets leaked.
H. Missing fallback credentials -> unconfigured providers skipped cleanly.
I. Non-retryable error -> halts immediately without cycling.
J. Provider and model metadata preserved.
K. GENERAL query in RAGService bypasses retrieval, returns immediately on primary success.
L. Existing Gemini behavior and create_fallback_llm_provider factory.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.llm.base_provider import BaseLLMProvider
from app.llm.exceptions import (
    AllProvidersFailedError,
    NonRetryableProviderError,
    RetryableProviderError,
)
from app.llm.fallback_router import FallbackLLMProvider, create_fallback_llm_provider
from app.models.llm_response import LLMResponse
from app.prompts.context_assembler import PromptContext
from app.services.rag_service import RAGService


@pytest.fixture
def sample_prompt_context() -> PromptContext:
    return PromptContext(
        system_prompt="You are DevMind AI.",
        user_question="Where is login implemented?",
        retrieved_context="--- [Chunk 1] File: auth.py ---\ndef login(): pass",
        citations=[{"file_name": "auth.py", "rank": 1}],
    )


def test_scenario_a_gemini_success_no_fallback(sample_prompt_context: PromptContext) -> None:
    """Scenario A: Gemini succeeds on first attempt; fallback providers are never called."""
    mock_gemini = MagicMock(spec=BaseLLMProvider)
    mock_gemini.provider_name = "gemini"
    mock_gemini.model_name = "gemini-3.6-flash"
    mock_gemini.is_configured = True
    mock_gemini.generate.return_value = LLMResponse(
        answer="Login is in auth.py.",
        provider="gemini",
        model="gemini-3.6-flash",
        latency_ms=120.0,
    )

    mock_openrouter = MagicMock(spec=BaseLLMProvider)
    mock_openrouter.provider_name = "openrouter"
    mock_openrouter.is_configured = True

    mock_grok = MagicMock(spec=BaseLLMProvider)
    mock_grok.provider_name = "xai"
    mock_grok.is_configured = True

    router = FallbackLLMProvider(providers=[mock_gemini, mock_openrouter, mock_grok])
    response = router.generate(sample_prompt_context)

    assert response.provider == "gemini"
    assert response.model == "gemini-3.6-flash"
    assert response.answer == "Login is in auth.py."

    mock_gemini.generate.assert_called_once_with(sample_prompt_context)
    mock_openrouter.generate.assert_not_called()
    mock_grok.generate.assert_not_called()


def test_scenario_b_gemini_rate_limit_falls_back_to_openrouter(sample_prompt_context: PromptContext) -> None:
    """Scenario B: Gemini returns 429 rate limit; router falls back to OpenRouter."""
    mock_gemini = MagicMock(spec=BaseLLMProvider)
    mock_gemini.provider_name = "gemini"
    mock_gemini.model_name = "gemini-3.6-flash"
    mock_gemini.is_configured = True
    mock_gemini.generate.side_effect = RetryableProviderError("Rate limit exceeded", provider="gemini", status_code=429)

    mock_openrouter = MagicMock(spec=BaseLLMProvider)
    mock_openrouter.provider_name = "openrouter"
    mock_openrouter.model_name = "openai/gpt-4o-mini"
    mock_openrouter.is_configured = True
    mock_openrouter.generate.return_value = LLMResponse(
        answer="OpenRouter answer: auth.py",
        provider="openrouter",
        model="openai/gpt-4o-mini",
        latency_ms=250.0,
    )

    mock_grok = MagicMock(spec=BaseLLMProvider)
    mock_grok.provider_name = "xai"
    mock_grok.is_configured = True

    router = FallbackLLMProvider(providers=[mock_gemini, mock_openrouter, mock_grok])
    response = router.generate(sample_prompt_context)

    assert response.provider == "openrouter"
    assert response.model == "openai/gpt-4o-mini"
    assert response.answer == "OpenRouter answer: auth.py"

    mock_gemini.generate.assert_called_once()
    mock_openrouter.generate.assert_called_once()
    mock_grok.generate.assert_not_called()


def test_scenario_c_gemini_timeout_falls_back_to_openrouter(sample_prompt_context: PromptContext) -> None:
    """Scenario C: Gemini times out; router falls back to OpenRouter."""
    mock_gemini = MagicMock(spec=BaseLLMProvider)
    mock_gemini.provider_name = "gemini"
    mock_gemini.is_configured = True
    mock_gemini.generate.side_effect = RetryableProviderError("Connection timed out after 30s", provider="gemini")

    mock_openrouter = MagicMock(spec=BaseLLMProvider)
    mock_openrouter.provider_name = "openrouter"
    mock_openrouter.model_name = "openai/gpt-4o-mini"
    mock_openrouter.is_configured = True
    mock_openrouter.generate.return_value = LLMResponse(
        answer="OpenRouter response after Gemini timeout",
        provider="openrouter",
        model="openai/gpt-4o-mini",
        latency_ms=300.0,
    )

    router = FallbackLLMProvider(providers=[mock_gemini, mock_openrouter])
    response = router.generate(sample_prompt_context)

    assert response.provider == "openrouter"
    assert response.answer == "OpenRouter response after Gemini timeout"
    mock_gemini.generate.assert_called_once()
    mock_openrouter.generate.assert_called_once()


@pytest.mark.parametrize("status_code", [500, 502, 503, 504])
def test_scenario_d_gemini_5xx_falls_back_to_openrouter(sample_prompt_context: PromptContext, status_code: int) -> None:
    """Scenario D: Gemini returns 5xx error; router falls back to OpenRouter."""
    mock_gemini = MagicMock(spec=BaseLLMProvider)
    mock_gemini.provider_name = "gemini"
    mock_gemini.is_configured = True
    mock_gemini.generate.side_effect = RetryableProviderError(f"Server error {status_code}", provider="gemini", status_code=status_code)

    mock_openrouter = MagicMock(spec=BaseLLMProvider)
    mock_openrouter.provider_name = "openrouter"
    mock_openrouter.model_name = "openai/gpt-4o-mini"
    mock_openrouter.is_configured = True
    mock_openrouter.generate.return_value = LLMResponse(
        answer=f"OpenRouter response after Gemini {status_code}",
        provider="openrouter",
        model="openai/gpt-4o-mini",
        latency_ms=210.0,
    )

    router = FallbackLLMProvider(providers=[mock_gemini, mock_openrouter])
    response = router.generate(sample_prompt_context)

    assert response.provider == "openrouter"
    assert response.answer == f"OpenRouter response after Gemini {status_code}"


def test_scenario_e_f_openrouter_fails_grok_succeeds(sample_prompt_context: PromptContext) -> None:
    """Scenario E & F: Gemini fails, OpenRouter fails, xAI Grok succeeds with accurate metadata."""
    mock_gemini = MagicMock(spec=BaseLLMProvider)
    mock_gemini.provider_name = "gemini"
    mock_gemini.is_configured = True
    mock_gemini.generate.side_effect = RetryableProviderError("Gemini 429", provider="gemini", status_code=429)

    mock_openrouter = MagicMock(spec=BaseLLMProvider)
    mock_openrouter.provider_name = "openrouter"
    mock_openrouter.is_configured = True
    mock_openrouter.generate.side_effect = RetryableProviderError("OpenRouter 503", provider="openrouter", status_code=503)

    mock_grok = MagicMock(spec=BaseLLMProvider)
    mock_grok.provider_name = "xai"
    mock_grok.model_name = "grok-2-latest"
    mock_grok.is_configured = True
    mock_grok.generate.return_value = LLMResponse(
        answer="Grok response: Verification is in engine.ts.",
        provider="xai",
        model="grok-2-latest",
        latency_ms=180.0,
    )

    router = FallbackLLMProvider(providers=[mock_gemini, mock_openrouter, mock_grok])
    response = router.generate(sample_prompt_context)

    assert response.provider == "xai"
    assert response.model == "grok-2-latest"
    assert response.answer == "Grok response: Verification is in engine.ts."

    mock_gemini.generate.assert_called_once()
    mock_openrouter.generate.assert_called_once()
    mock_grok.generate.assert_called_once()


def test_scenario_g_all_providers_fail_raises_controlled_error(sample_prompt_context: PromptContext) -> None:
    """Scenario G: All providers fail; raises AllProvidersFailedError with no secret leaks."""
    mock_gemini = MagicMock(spec=BaseLLMProvider)
    mock_gemini.provider_name = "gemini"
    mock_gemini.is_configured = True
    mock_gemini.generate.side_effect = RetryableProviderError("Gemini 429", provider="gemini")

    mock_openrouter = MagicMock(spec=BaseLLMProvider)
    mock_openrouter.provider_name = "openrouter"
    mock_openrouter.is_configured = True
    mock_openrouter.generate.side_effect = RetryableProviderError("OpenRouter 500", provider="openrouter")

    mock_grok = MagicMock(spec=BaseLLMProvider)
    mock_grok.provider_name = "xai"
    mock_grok.is_configured = True
    mock_grok.generate.side_effect = RetryableProviderError("Grok 504", provider="xai")

    router = FallbackLLMProvider(providers=[mock_gemini, mock_openrouter, mock_grok])

    with pytest.raises(AllProvidersFailedError) as exc_info:
        router.generate(sample_prompt_context)

    err_msg = str(exc_info.value)
    assert "All configured LLM providers failed" in err_msg
    assert "gemini" in err_msg
    assert "openrouter" in err_msg
    assert "xai" in err_msg
    # Ensure no API keys or bearer tokens exist in exception message
    assert "sk-" not in err_msg
    assert "Bearer" not in err_msg


def test_scenario_h_missing_fallback_credentials_skipped_cleanly(sample_prompt_context: PromptContext) -> None:
    """Scenario H: Unconfigured fallback provider is cleanly bypassed."""
    mock_gemini = MagicMock(spec=BaseLLMProvider)
    mock_gemini.provider_name = "gemini"
    mock_gemini.is_configured = True
    mock_gemini.generate.side_effect = RetryableProviderError("Gemini down", provider="gemini")

    # OpenRouter key missing in environment
    mock_openrouter = MagicMock(spec=BaseLLMProvider)
    mock_openrouter.provider_name = "openrouter"
    mock_openrouter.is_configured = False

    # Grok is configured
    mock_grok = MagicMock(spec=BaseLLMProvider)
    mock_grok.provider_name = "xai"
    mock_grok.model_name = "grok-2-latest"
    mock_grok.is_configured = True
    mock_grok.generate.return_value = LLMResponse(
        answer="Grok answer",
        provider="xai",
        model="grok-2-latest",
        latency_ms=190.0,
    )

    router = FallbackLLMProvider(providers=[mock_gemini, mock_openrouter, mock_grok])
    response = router.generate(sample_prompt_context)

    assert response.provider == "xai"
    mock_gemini.generate.assert_called_once()
    mock_openrouter.generate.assert_not_called()
    mock_grok.generate.assert_called_once()


def test_scenario_i_non_retryable_error_halts_immediately(sample_prompt_context: PromptContext) -> None:
    """Scenario I: Non-retryable error (e.g. 400 Bad Request) fails fast without cycling."""
    mock_gemini = MagicMock(spec=BaseLLMProvider)
    mock_gemini.provider_name = "gemini"
    mock_gemini.is_configured = True
    mock_gemini.generate.side_effect = NonRetryableProviderError("Invalid prompt context", provider="gemini", status_code=400)

    mock_openrouter = MagicMock(spec=BaseLLMProvider)
    mock_openrouter.is_configured = True

    mock_grok = MagicMock(spec=BaseLLMProvider)
    mock_grok.is_configured = True

    router = FallbackLLMProvider(providers=[mock_gemini, mock_openrouter, mock_grok])

    with pytest.raises(NonRetryableProviderError):
        router.generate(sample_prompt_context)

    mock_gemini.generate.assert_called_once()
    mock_openrouter.generate.assert_not_called()
    mock_grok.generate.assert_not_called()


def test_scenario_j_no_configured_providers_raises_error(sample_prompt_context: PromptContext) -> None:
    """Scenario J: If no providers have configured credentials, raises AllProvidersFailedError."""
    mock_p1 = MagicMock(spec=BaseLLMProvider)
    mock_p1.is_configured = False

    mock_p2 = MagicMock(spec=BaseLLMProvider)
    mock_p2.is_configured = False

    router = FallbackLLMProvider(providers=[mock_p1, mock_p2])
    assert router.is_configured is False

    with pytest.raises(AllProvidersFailedError, match="No LLM providers are configured"):
        router.generate(sample_prompt_context)


def test_scenario_k_general_query_fast_path_with_fallback_router() -> None:
    """Scenario K: In RAGService, GENERAL query bypasses retrieval and uses primary immediately."""
    mock_gemini = MagicMock(spec=BaseLLMProvider)
    mock_gemini.provider_name = "gemini"
    mock_gemini.model_name = "gemini-3.6-flash"
    mock_gemini.is_configured = True
    mock_gemini.generate.return_value = LLMResponse(
        answer="Hello! How can I assist you?",
        provider="gemini",
        model="gemini-3.6-flash",
        latency_ms=75.0,
    )

    mock_fallback = MagicMock(spec=BaseLLMProvider)
    mock_fallback.is_configured = True

    router = FallbackLLMProvider(providers=[mock_gemini, mock_fallback])

    rag = RAGService(llm_provider=router)
    result = rag.query("hello!")

    assert result["intent"] == "GENERAL"
    assert result["sources"] == []
    assert result["provider"] == "gemini"
    assert result["model"] == "gemini-3.6-flash"
    assert "Hello!" in result["answer"]

    mock_gemini.generate.assert_called_once()
    mock_fallback.generate.assert_not_called()


def test_scenario_l_factory_initialization() -> None:
    """Scenario L: create_fallback_llm_provider creates Gemini, OpenRouter, and xAI providers."""
    router = create_fallback_llm_provider()
    assert isinstance(router, FallbackLLMProvider)
    providers = router.providers
    assert len(providers) == 3
    assert providers[0].provider_name == "gemini"
    assert providers[1].provider_name == "openrouter"
    assert providers[2].provider_name == "xai"

"""Unit tests for GeminiProvider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.llm.base_provider import BaseLLMProvider
from app.llm.gemini_provider import GeminiProvider
from app.models.llm_response import LLMResponse
from app.prompts.context_assembler import PromptContext


@pytest.fixture
def sample_prompt_context() -> PromptContext:
    return PromptContext(
        system_prompt="You are DevMind AI.",
        user_question="Where is login implemented?",
        retrieved_context="--- [Chunk 1] File: auth.py ---\ndef login(): pass",
        citations=[{"file_name": "auth.py", "rank": 1}],
    )


def test_gemini_provider_implements_base_interface() -> None:
    provider = GeminiProvider(api_key="mock_key")
    assert isinstance(provider, BaseLLMProvider)
    assert provider.provider_name == "gemini"
    assert provider.model_name == GeminiProvider.DEFAULT_MODEL_NAME


def test_gemini_provider_custom_model_name() -> None:
    provider = GeminiProvider(api_key="mock_key", model_name="gemini-1.5-pro")
    assert provider.model_name == "gemini-1.5-pro"


def test_gemini_provider_missing_key_raises(sample_prompt_context: PromptContext) -> None:
    provider = GeminiProvider(api_key="", client=None)
    # Clear env override if any
    with patch.dict("os.environ", {}, clear=True):
        provider = GeminiProvider()
        with pytest.raises(ValueError, match="Gemini API key missing"):
            provider.generate(sample_prompt_context)


def test_gemini_provider_generate_success(sample_prompt_context: PromptContext) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Login function is implemented in auth.py lines 6-13."

    mock_usage = MagicMock()
    mock_usage.prompt_token_count = 120
    mock_usage.candidates_token_count = 45
    mock_usage.total_token_count = 165
    mock_response.usage_metadata = mock_usage

    mock_candidate = MagicMock()
    mock_candidate.finish_reason = "STOP"
    mock_response.candidates = [mock_candidate]

    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(client=mock_client, model_name="gemini-3.6-flash")
    llm_response = provider.generate(sample_prompt_context)

    assert isinstance(llm_response, LLMResponse)
    assert llm_response.answer == "Login function is implemented in auth.py lines 6-13."
    assert llm_response.provider == "gemini"
    assert llm_response.model == "gemini-3.6-flash"
    assert llm_response.latency_ms >= 0.0
    assert llm_response.usage_tokens == {
        "prompt_tokens": 120,
        "candidates_tokens": 45,
        "total_tokens": 165,
    }
    assert llm_response.finish_reason == "STOP"

    mock_client.models.generate_content.assert_called_once()

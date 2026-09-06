"""Unit tests for XAIProvider (xAI Grok)."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from app.llm.base_provider import BaseLLMProvider
from app.llm.exceptions import NonRetryableProviderError, RetryableProviderError
from app.llm.xai_provider import XAIProvider
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


def test_xai_provider_implements_base_interface() -> None:
    provider = XAIProvider(api_key="xai-test-key")
    assert isinstance(provider, BaseLLMProvider)
    assert provider.provider_name == "xai"
    assert provider.model_name == XAIProvider.DEFAULT_MODEL_NAME
    assert provider.is_configured is True


def test_xai_provider_unconfigured() -> None:
    provider = XAIProvider(api_key="")
    assert provider.is_configured is False
    with pytest.raises(ValueError, match="xAI API key missing"):
        provider.generate(
            PromptContext(
                system_prompt="sys",
                user_question="q",
                retrieved_context="ctx",
            )
        )


def test_xai_provider_custom_model_and_timeout() -> None:
    provider = XAIProvider(
        api_key="xai-test-key",
        model_name="grok-beta",
        base_url="https://custom.x.ai/v1",
        timeout_seconds=50.0,
    )
    assert provider.model_name == "grok-beta"
    assert provider._timeout_seconds == 50.0
    assert provider._base_url == "https://custom.x.ai/v1"


def test_xai_provider_generate_success(sample_prompt_context: PromptContext) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {"role": "assistant", "content": "Grok response: auth.py implements login."},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 70,
            "completion_tokens": 25,
            "total_tokens": 95,
        },
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_response

    provider = XAIProvider(api_key="xai-test-key", http_client=mock_client)
    res = provider.generate(sample_prompt_context)

    assert isinstance(res, LLMResponse)
    assert res.provider == "xai"
    assert res.model == XAIProvider.DEFAULT_MODEL_NAME
    assert res.answer == "Grok response: auth.py implements login."
    assert res.finish_reason == "stop"
    assert res.usage_tokens == {
        "prompt_tokens": 70,
        "candidates_tokens": 25,
        "total_tokens": 95,
    }
    assert res.latency_ms >= 0.0

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "Authorization" in call_args[1]["headers"]
    assert call_args[1]["headers"]["Authorization"] == "Bearer xai-test-key"
    assert call_args[1]["json"]["model"] == XAIProvider.DEFAULT_MODEL_NAME


@pytest.mark.parametrize("status_code", [429, 500, 502, 503, 504])
def test_xai_provider_retryable_http_errors(sample_prompt_context: PromptContext, status_code: int) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.text = f"Error {status_code}"

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_response

    provider = XAIProvider(api_key="xai-test-key", http_client=mock_client)
    with pytest.raises(RetryableProviderError) as exc_info:
        provider.generate(sample_prompt_context)

    assert exc_info.value.provider == "xai"
    assert exc_info.value.status_code == status_code


def test_xai_provider_timeout_raises_retryable(sample_prompt_context: PromptContext) -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.ReadTimeout("Read timed out")

    provider = XAIProvider(api_key="xai-test-key", http_client=mock_client)
    with pytest.raises(RetryableProviderError) as exc_info:
        provider.generate(sample_prompt_context)

    assert "timed out" in exc_info.value.message


def test_xai_provider_network_error_raises_retryable(sample_prompt_context: PromptContext) -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")

    provider = XAIProvider(api_key="xai-test-key", http_client=mock_client)
    with pytest.raises(RetryableProviderError) as exc_info:
        provider.generate(sample_prompt_context)

    assert "connection error" in exc_info.value.message


@pytest.mark.parametrize("status_code", [400, 401, 403])
def test_xai_provider_non_retryable_http_errors(sample_prompt_context: PromptContext, status_code: int) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.text = f"Client error {status_code}"

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_response

    provider = XAIProvider(api_key="xai-test-key", http_client=mock_client)
    with pytest.raises(NonRetryableProviderError) as exc_info:
        provider.generate(sample_prompt_context)

    assert exc_info.value.status_code == status_code

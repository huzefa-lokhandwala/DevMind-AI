"""Base abstract class for LLM providers in DevMind AI."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.llm_response import LLMResponse
from app.prompts.context_assembler import PromptContext


class BaseLLMProvider(ABC):
    """Abstract interface for provider-agnostic LLM integration."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return unique provider identifier (e.g., 'gemini', 'openai', 'ollama')."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return configured LLM model identifier."""

    @abstractmethod
    def generate(self, context: PromptContext) -> LLMResponse:
        """Generate response for the provided PromptContext.

        Args:
            context: Formatted prompt payload containing system prompt, user query,
                and retrieved code context.

        Returns:
            Standardized ``LLMResponse`` object containing answer and execution metadata.
        """

"""Vector embedding generation for DevMind AI document chunks and queries.

Supports:
1. LocalEmbeddingProvider (default): Local BAAI/bge-small-en-v1.5 (384d) via FastEmbed / ONNX Runtime.
2. GeminiEmbeddingProvider (optional): Remote gemini-embedding-001 (768d) via Google GenAI SDK.
"""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Any, Sequence

from dotenv import load_dotenv

from app.models import Document

logger = logging.getLogger(__name__)

load_dotenv()


class BaseEmbeddingProvider(ABC):
    """Abstract base class for DevMind AI embedding providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Return the vector dimensionality."""

    @abstractmethod
    def embed_documents(
        self, documents: Sequence[Document], batch_size: int | None = None
    ) -> list[Document]:
        """Generate and attach dense vector embeddings to each document."""

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        """Generate a dense vector embedding for a single text query string."""


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Local embedding provider using FastEmbed and BAAI/bge-small-en-v1.5 (384 dimensions).

    Runs locally via ONNX Runtime without requiring external API keys or network calls.
    The underlying FastEmbed model is loaded lazily once and cached across requests.
    """

    DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"
    DEFAULT_EMBEDDING_DIMENSION = 384
    DEFAULT_BATCH_SIZE = 64

    _cached_model: Any = None
    _cached_model_name: str | None = None

    def __init__(
        self,
        model_name: str | None = None,
        dimension: int | None = None,
        model: Any | None = None,
    ) -> None:
        """Initialize LocalEmbeddingProvider.

        Args:
            model_name: Optional FastEmbed model identifier. Defaults to
                environment variable ``EMBEDDING_MODEL`` or ``BAAI/bge-small-en-v1.5``.
            dimension: Expected vector dimensionality (default: 384).
            model: Optional pre-instantiated or mocked FastEmbed TextEmbedding model.
        """
        self._model_name = (
            model_name
            or os.getenv("EMBEDDING_MODEL")
            or self.DEFAULT_MODEL_NAME
        )
        self._embedding_dimension = dimension or self.DEFAULT_EMBEDDING_DIMENSION
        self._model = model

        logger.info(
            "LocalEmbeddingProvider initialized (model=%s, dimension=%d)",
            self._model_name,
            self._embedding_dimension,
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def embedding_dimension(self) -> int:
        return self._embedding_dimension

    def _get_model(self) -> Any:
        """Lazily load and cache the FastEmbed TextEmbedding model singleton."""
        if self._model is not None:
            return self._model

        # Reuse shared class-level model cache if the model name matches
        if (
            LocalEmbeddingProvider._cached_model is not None
            and LocalEmbeddingProvider._cached_model_name == self._model_name
        ):
            return LocalEmbeddingProvider._cached_model

        logger.info("Loading FastEmbed model: %s", self._model_name)
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            logger.error("fastembed is not installed. Please install fastembed>=0.4.0: %s", exc)
            raise RuntimeError(
                "FastEmbed library is not installed. Please install fastembed>=0.4.0."
            ) from exc

        loaded_model = TextEmbedding(model_name=self._model_name)
        LocalEmbeddingProvider._cached_model = loaded_model
        LocalEmbeddingProvider._cached_model_name = self._model_name
        logger.info("FastEmbed model '%s' loaded successfully.", self._model_name)
        return loaded_model

    def embed_documents(
        self, documents: Sequence[Document], batch_size: int | None = None
    ) -> list[Document]:
        """Attach vector embeddings to each document using FastEmbed.

        Preserves document content, ordering, and metadata while populating ``embedding``.

        Args:
            documents: Sequence of Document chunks to embed.
            batch_size: Optional batch size for embedding iteration.

        Returns:
            List of new Document instances containing 384-dimensional float embeddings.
        """
        if not documents:
            logger.info("No documents to embed")
            return []

        actual_batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        texts = [doc.content for doc in documents]
        logger.info(
            "Generating local FastEmbed embeddings for %d document(s) (batch_size=%d)",
            len(documents),
            actual_batch_size,
        )

        model = self._get_model()
        # FastEmbed.embed returns an iterable of numpy arrays
        raw_embeddings = list(model.embed(texts, batch_size=actual_batch_size))

        if len(raw_embeddings) != len(documents):
            raise RuntimeError(
                f"Embedding count mismatch: expected {len(documents)}, got {len(raw_embeddings)}"
            )

        embedded_documents: list[Document] = []
        for doc, raw_vector in zip(documents, raw_embeddings, strict=True):
            vector: list[float] = [float(val) for val in raw_vector]
            if len(vector) != self._embedding_dimension:
                raise ValueError(
                    f"Generated embedding dimension ({len(vector)}) does not match "
                    f"expected dimension ({self._embedding_dimension})."
                )
            embedded_documents.append(replace(doc, embedding=vector))

        logger.info(
            "Generated %d local embedding(s) with dimension %d",
            len(embedded_documents),
            self._embedding_dimension,
        )
        return embedded_documents

    def embed_query(self, query: str) -> list[float]:
        """Generate a dense vector embedding for a single text query string.

        Args:
            query: User query text to embed.

        Returns:
            Dense float vector of size 384.
        """
        if not query or not query.strip():
            raise ValueError("Query string must not be empty or whitespace-only.")

        logger.info("Generating local FastEmbed embedding for query: '%s'", query)
        model = self._get_model()
        raw_embeddings = list(model.embed([query.strip()]))
        if not raw_embeddings:
            raise RuntimeError("FastEmbed returned no embeddings for query.")

        vector: list[float] = [float(val) for val in raw_embeddings[0]]
        if len(vector) != self._embedding_dimension:
            raise ValueError(
                f"Generated query embedding dimension ({len(vector)}) does not match "
                f"expected dimension ({self._embedding_dimension})."
            )
        return vector


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Remote embedding provider using Google Gemini API (gemini-embedding-001, 768d)."""

    DEFAULT_MODEL_NAME = "gemini-embedding-001"
    DEFAULT_EMBEDDING_DIMENSION = 768
    DEFAULT_BATCH_SIZE = 50

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        dimension: int | None = None,
        client: Any | None = None,
    ) -> None:
        """Initialize GeminiEmbeddingProvider.

        Args:
            api_key: Optional Gemini API key. Defaults to environment variable
                ``GEMINI_API_KEY`` or ``GOOGLE_API_KEY``.
            model_name: Optional Gemini embedding model identifier. Defaults to
                environment variable ``EMBEDDING_MODEL`` or ``gemini-embedding-001``.
            dimension: Optional vector dimensionality (default: 768).
            client: Optional pre-configured ``google.genai.Client`` (useful for testing).
        """
        from google import genai

        self._api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        self._model_name = (
            model_name
            or os.getenv("EMBEDDING_MODEL")
            or self.DEFAULT_MODEL_NAME
        )
        self._embedding_dimension = dimension or self.DEFAULT_EMBEDDING_DIMENSION

        if client is not None:
            self._client = client
        elif self._api_key:
            self._client = genai.Client(api_key=self._api_key)
        else:
            logger.warning(
                "Gemini API key not found in environment. "
                "GeminiEmbeddingProvider initialized in unauthenticated mode."
            )
            self._client = None

        logger.info(
            "GeminiEmbeddingProvider initialized (model=%s, dimension=%d)",
            self._model_name,
            self._embedding_dimension,
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def embedding_dimension(self) -> int:
        return self._embedding_dimension

    def _call_embed_api_with_retry(
        self,
        contents: str | list[str],
        task_type: str,
        max_retries: int = 3,
        backoff_sec: float = 1.0,
    ) -> Any:
        """Invoke Gemini embed_content API with retry backoff for transient errors."""
        from google import genai
        from google.genai import types

        if self._client is None:
            raise ValueError(
                "Gemini API key missing. Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variable."
            )

        config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=self._embedding_dimension,
        )

        for attempt in range(1, max_retries + 1):
            try:
                response = self._client.models.embed_content(
                    model=self._model_name,
                    contents=contents,
                    config=config,
                )
                return response
            except genai.errors.APIError as exc:
                code = getattr(exc, "code", None)
                if code in (503, 429, 500, 502, 504) and attempt < max_retries:
                    logger.warning(
                        "Gemini Embedding API transient error (%s). Retrying attempt %d/%d after %.1fs...",
                        code,
                        attempt,
                        max_retries,
                        backoff_sec,
                    )
                    time.sleep(backoff_sec)
                    backoff_sec *= 2.0
                else:
                    logger.error("Gemini Embedding API error: %s", exc)
                    raise
            except Exception as exc:
                if attempt < max_retries:
                    logger.warning(
                        "Unexpected error calling Gemini Embedding API (%s). Retrying %d/%d...",
                        type(exc).__name__,
                        attempt,
                        max_retries,
                    )
                    time.sleep(backoff_sec)
                    backoff_sec *= 2.0
                else:
                    logger.error("Gemini Embedding API request failed: %s", exc)
                    raise

        raise RuntimeError("Exceeded maximum retries calling Gemini Embedding API.")

    def embed_documents(
        self, documents: Sequence[Document], batch_size: int | None = None
    ) -> list[Document]:
        """Attach vector embeddings to each document using Gemini API."""
        if not documents:
            logger.info("No documents to embed")
            return []

        actual_batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        texts = [document.content for document in documents]
        logger.info(
            "Generating Gemini embeddings for %d document(s) in batches of %d",
            len(documents),
            actual_batch_size,
        )

        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), actual_batch_size):
            batch_texts = texts[i : i + actual_batch_size]
            response = self._call_embed_api_with_retry(
                contents=batch_texts,
                task_type="RETRIEVAL_DOCUMENT",
            )
            if not response.embeddings:
                raise RuntimeError(
                    f"Gemini Embedding API returned no embeddings for batch [{i}:{i+len(batch_texts)}]"
                )
            for emb in response.embeddings:
                all_vectors.append(list(emb.values))

        if len(all_vectors) != len(documents):
            raise RuntimeError(
                f"Embedding count mismatch: expected {len(documents)}, got {len(all_vectors)}"
            )

        embedded_documents: list[Document] = []
        for document, vector in zip(documents, all_vectors, strict=True):
            embedded_documents.append(replace(document, embedding=vector))

        logger.info(
            "Generated %d Gemini embedding(s) with dimension %d",
            len(embedded_documents),
            self._embedding_dimension,
        )
        return embedded_documents

    def embed_query(self, query: str) -> list[float]:
        """Generate a dense vector embedding for a single query using Gemini API."""
        if not query or not query.strip():
            raise ValueError("Query string must not be empty or whitespace-only.")

        logger.info("Generating Gemini embedding for query: '%s'", query)
        response = self._call_embed_api_with_retry(
            contents=query.strip(),
            task_type="RETRIEVAL_QUERY",
        )
        if not response.embeddings:
            raise RuntimeError("Gemini Embedding API returned no embeddings for query.")

        return list(response.embeddings[0].values)


class EmbeddingEngine:
    """Unified Facade for DevMind AI embedding providers.

    Selects provider via ``EMBEDDING_PROVIDER`` environment variable or constructor argument.
    Defaults to ``local`` (BAAI/bge-small-en-v1.5 via FastEmbed, 384d).
    """

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        dimension: int | None = None,
        client: Any | None = None,
        local_model: Any | None = None,
        custom_provider: BaseEmbeddingProvider | None = None,
    ) -> None:
        """Initialize EmbeddingEngine with selected provider.

        Args:
            provider: Provider identifier ('local' or 'gemini'). Defaults to
                environment variable ``EMBEDDING_PROVIDER`` or 'local'.
            api_key: Optional Gemini API key (for Gemini provider).
            model_name: Optional model override.
            dimension: Optional dimension override.
            client: Optional pre-configured Client (for Gemini provider).
            local_model: Optional pre-configured TextEmbedding model (for Local provider).
            custom_provider: Optional injected BaseEmbeddingProvider instance.
        """
        if custom_provider is not None:
            self._provider = custom_provider
            self._provider_name = "custom"
            return

        resolved_provider = (
            provider
            or os.getenv("EMBEDDING_PROVIDER", "local")
        ).strip().lower()

        self._provider_name = resolved_provider

        if resolved_provider == "local":
            self._provider = LocalEmbeddingProvider(
                model_name=model_name,
                dimension=dimension,
                model=local_model,
            )
        elif resolved_provider == "gemini":
            self._provider = GeminiEmbeddingProvider(
                api_key=api_key,
                model_name=model_name,
                dimension=dimension,
                client=client,
            )
        else:
            raise ValueError(
                f"Unsupported embedding provider '{resolved_provider}'. "
                "Supported providers: 'local', 'gemini'."
            )

    @property
    def provider_name(self) -> str:
        """Return the active provider name ('local' or 'gemini')."""
        return self._provider_name

    @property
    def model_name(self) -> str:
        """Return the active embedding model identifier."""
        return self._provider.model_name

    @property
    def embedding_dimension(self) -> int:
        """Return the vector dimensionality of the active provider."""
        return self._provider.embedding_dimension

    def embed_documents(
        self, documents: Sequence[Document], batch_size: int | None = None
    ) -> list[Document]:
        """Attach vector embeddings to each document."""
        return self._provider.embed_documents(documents, batch_size=batch_size)

    def embed_query(self, query: str) -> list[float]:
        """Generate a dense vector embedding for a single text query string."""
        return self._provider.embed_query(query)

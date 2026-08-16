"""Vector embedding generation for DevMind AI document chunks using Google Gemini API."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import replace
from typing import Sequence

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.models import Document

logger = logging.getLogger(__name__)

load_dotenv()


class EmbeddingEngine:
    """Generate dense vector embeddings for document chunks using Google Gemini Embeddings API.

    Uses the project's standard google-genai client and GEMINI_API_KEY.
    """

    DEFAULT_MODEL_NAME = "gemini-embedding-001"
    DEFAULT_EMBEDDING_DIMENSION = 768
    DEFAULT_BATCH_SIZE = 50

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        dimension: int | None = None,
        client: genai.Client | None = None,
    ) -> None:
        """Initialize Gemini EmbeddingEngine.

        Args:
            api_key: Optional Gemini API key. Defaults to environment variable
                ``GEMINI_API_KEY`` or ``GOOGLE_API_KEY``.
            model_name: Optional Gemini embedding model identifier. Defaults to
                environment variable ``EMBEDDING_MODEL`` or ``gemini-embedding-001``.
            dimension: Optional vector dimensionality. Defaults to environment variable
                ``EMBEDDING_DIMENSION`` or 768.
            client: Optional pre-configured ``genai.Client`` (useful for mocking/testing).
        """
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

        env_dim = os.getenv("EMBEDDING_DIMENSION")
        if dimension is not None:
            self._embedding_dimension = dimension
        elif env_dim and env_dim.isdigit():
            self._embedding_dimension = int(env_dim)
        else:
            self._embedding_dimension = self.DEFAULT_EMBEDDING_DIMENSION

        if client is not None:
            self._client = client
        elif self._api_key:
            self._client = genai.Client(api_key=self._api_key)
        else:
            logger.warning(
                "Gemini API key not found in environment. "
                "EmbeddingEngine initialized in unauthenticated mode."
            )
            self._client = None  # type: ignore[assignment]

        logger.info(
            "Gemini EmbeddingEngine initialized (model=%s, dimension=%d)",
            self._model_name,
            self._embedding_dimension,
        )

    @property
    def model_name(self) -> str:
        """Return the configured model identifier."""
        return self._model_name

    @property
    def embedding_dimension(self) -> int:
        """Return the size of vectors produced by the configured model."""
        return self._embedding_dimension

    def _call_embed_api_with_retry(
        self,
        contents: str | list[str],
        task_type: str,
        max_retries: int = 3,
        backoff_sec: float = 1.0,
    ) -> types.EmbedContentResponse:
        """Invoke Gemini embed_content API with retry backoff for transient errors."""
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
        """Attach vector embeddings to each document using Gemini Embeddings API.

        Document content and metadata are preserved; only ``embedding`` is set.

        Args:
            documents: Chunked or loaded documents to embed.
            batch_size: Optional maximum chunk batch size per API call. Defaults to 50.

        Returns:
            New ``Document`` instances with populated ``embedding`` fields.
        """
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
        """Generate a dense vector embedding for a single text query string.

        Args:
            query: User query text to embed.

        Returns:
            Dense float vector of size ``embedding_dimension``.
        """
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

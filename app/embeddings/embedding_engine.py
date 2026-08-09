"""Vector embedding generation for DevMind AI document chunks."""

from __future__ import annotations

import logging
from dataclasses import replace

from sentence_transformers import SentenceTransformer

from app.models import Document

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Generate dense vector embeddings for document chunks.

    The underlying transformer model is loaded once during initialization
    and reused for all subsequent embedding requests.
    """

    DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"

    def __init__(self, model_name: str | None = None) -> None:
        """Load the sentence-transformer model.

        Args:
            model_name: Hugging Face model identifier. Defaults to
                ``BAAI/bge-small-en-v1.5``.
        """
        self._model_name = model_name or self.DEFAULT_MODEL_NAME
        logger.info("Loading embedding model: %s", self._model_name)
        self._model = SentenceTransformer(self._model_name)
        self._embedding_dimension = self._model.get_embedding_dimension()
        logger.info(
            "Embedding model ready (dimension=%d)",
            self._embedding_dimension,
        )

    @property
    def model_name(self) -> str:
        """Return the loaded model identifier."""
        return self._model_name

    @property
    def embedding_dimension(self) -> int:
        """Return the size of vectors produced by the loaded model."""
        return self._embedding_dimension

    def embed_documents(self, documents: list[Document]) -> list[Document]:
        """Attach vector embeddings to each document.

        Document content and metadata are preserved; only ``embedding`` is set.

        Args:
            documents: Chunked or loaded documents to embed.

        Returns:
            New ``Document`` instances with populated ``embedding`` fields.
        """
        if not documents:
            logger.info("No documents to embed")
            return []

        texts = [document.content for document in documents]
        logger.info("Generating embeddings for %d document(s)", len(documents))

        vectors = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        embedded_documents: list[Document] = []
        for document, vector in zip(documents, vectors, strict=True):
            embedding = vector.tolist()
            embedded_documents.append(replace(document, embedding=embedding))

        logger.info(
            "Generated %d embedding(s) with dimension %d",
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
        logger.info("Generating embedding for query: '%s'", query)
        vector = self._model.encode(
            query,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vector.tolist()


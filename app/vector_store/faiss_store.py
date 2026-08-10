"""FAISS Vector Store for DevMind AI document search."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Sequence

import faiss
import numpy as np

from app.models import Document

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """In-memory FAISS vector database using IndexFlatIP for cosine similarity.

    Document embeddings are L2-normalized before insertion into the index,
    allowing Inner Product (IP) to compute exact Cosine Similarity.
    """

    def __init__(self, dimension: int | None = None) -> None:
        """Initialize FAISS Vector Store.

        Args:
            dimension: Dimensionality of vector embeddings. Inferred on
                first call to ``build_index`` if not provided.
        """
        self._dimension = dimension
        self._index: faiss.IndexFlatIP | None = None
        self._documents: list[Document] = []
        if dimension is not None:
            self._init_index(dimension)

    @property
    def embedding_dimension(self) -> int | None:
        """Return vector dimension of the FAISS index."""
        return self._dimension

    @property
    def total_documents(self) -> int:
        """Return total number of indexed documents."""
        return len(self._documents)

    def _init_index(self, dimension: int) -> None:
        """Create a new FAISS IndexFlatIP instance."""
        self._dimension = dimension
        self._index = faiss.IndexFlatIP(dimension)
        logger.info("Initialized FAISS IndexFlatIP with dimension=%d", dimension)

    def _prepare_matrix(self, documents: Sequence[Document]) -> np.ndarray:
        """Extract, validate, and L2-normalize document embeddings into a 2D float32 NumPy matrix."""
        vectors: list[list[float]] = []
        for index, doc in enumerate(documents):
            if doc.embedding is None:
                raise ValueError(
                    f"Document '{doc.file_name}' at index {index} has no embedding."
                )
            if self._dimension is not None and len(doc.embedding) != self._dimension:
                raise ValueError(
                    f"Document '{doc.file_name}' embedding dimension ({len(doc.embedding)}) "
                    f"does not match index dimension ({self._dimension})."
                )
            vectors.append(doc.embedding)

        if not vectors:
            return np.empty((0, self._dimension or 0), dtype=np.float32)

        matrix = np.array(vectors, dtype=np.float32)

        if self._dimension is None:
            self._init_index(matrix.shape[1])

        # L2 normalize so Inner Product == Cosine Similarity
        faiss.normalize_L2(matrix)
        return matrix

    def build_index(self, documents: list[Document]) -> None:
        """Build or replace the FAISS index with a list of documents.

        Args:
            documents: Documents containing vector embeddings to index.
        """
        if not documents:
            logger.warning("Empty document list passed to build_index. Index cleared.")
            self._documents = []
            if self._dimension is not None:
                self._init_index(self._dimension)
            return

        logger.info("Building FAISS index for %d document(s)", len(documents))

        # Reset state if dimension was inferred previously
        first_emb = documents[0].embedding
        if first_emb is not None:
            self._init_index(len(first_emb))

        matrix = self._prepare_matrix(documents)
        if self._index is None:
            raise RuntimeError("FAISS index was not properly initialized.")

        self._index.add(matrix)
        self._documents = list(documents)

        logger.info(
            "FAISS index built successfully with %d vector(s) (dimension=%d)",
            self._index.ntotal,
            self._dimension,
        )

    def add_documents(self, documents: list[Document]) -> None:
        """Append new documents with embeddings to the existing FAISS index.

        Args:
            documents: Documents containing embeddings to append.
        """
        if not documents:
            logger.info("No documents provided to add_documents.")
            return

        if self._index is None or not self._documents:
            # Fallback to build_index if current store is uninitialized/empty
            self.build_index(documents)
            return

        logger.info("Adding %d document(s) to FAISS index", len(documents))
        matrix = self._prepare_matrix(documents)
        self._index.add(matrix)
        self._documents.extend(documents)

        logger.info(
            "Total indexed documents after addition: %d",
            len(self._documents),
        )

    def search(
        self,
        query_embedding: list[float],
        k: int = 5,
        repository_name: str | None = None,
    ) -> list[tuple[Document, float]]:
        """Perform semantic similarity search for a query embedding.

        Args:
            query_embedding: Dense vector representation of query string.
            k: Maximum number of top matching documents to return.
            repository_name: Optional repository name filter for multi-tenant isolation.

        Returns:
            List of (Document, similarity_score) tuples sorted by similarity.
        """
        if self._index is None or self._index.ntotal == 0 or not self._documents:
            logger.warning("Search called on an empty FAISS vector store.")
            return []

        if len(query_embedding) != self._dimension:
            raise ValueError(
                f"Query embedding dimension ({len(query_embedding)}) does not match "
                f"FAISS index dimension ({self._dimension})."
            )

        k_fetch = max(1, min(k * 3 if repository_name else k, self._index.ntotal))

        # Format and L2-normalize query vector
        query_matrix = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_matrix)

        scores, indices = self._index.search(query_matrix, k_fetch)

        results: list[tuple[Document, float]] = []
        for score, idx in zip(scores[0], indices[0], strict=True):
            if idx < 0 or idx >= len(self._documents):
                continue
            doc = self._documents[idx]
            if repository_name and doc.repository_name != repository_name:
                continue
            results.append((doc, float(score)))
            if len(results) >= k:
                break

        logger.info("FAISS search returned %d document(s) for top-k=%d", len(results), k)
        return results

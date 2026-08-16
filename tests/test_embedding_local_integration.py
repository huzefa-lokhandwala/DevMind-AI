"""Integration test for real local FastEmbed embedding generation and FAISS retrieval."""

from __future__ import annotations

import pytest

from app.embeddings.embedding_engine import EmbeddingEngine
from app.models import Document
from app.vector_store.faiss_store import FAISSVectorStore


@pytest.mark.integration
def test_real_local_fastembed_e2e_pipeline() -> None:
    """Test actual end-to-end local embedding: embed documents -> FAISS (384d) -> embed query -> search."""
    engine = EmbeddingEngine(provider="local")

    assert engine.model_name == "BAAI/bge-small-en-v1.5"
    assert engine.embedding_dimension == 384

    doc1 = Document(
        content="def authenticate_user(username: str, password: str) -> bool: return True",
        file_name="auth.py",
        file_path="app/auth.py",
        extension=".py",
        repository_name="test_repo",
        chunk_type="function",
        function_name="authenticate_user",
        start_line=1,
        end_line=2,
    )
    doc2 = Document(
        content="def calculate_invoice_total(items: list[dict]) -> float: return sum(i['price'] for i in items)",
        file_name="billing.py",
        file_path="app/billing.py",
        extension=".py",
        repository_name="test_repo",
        chunk_type="function",
        function_name="calculate_invoice_total",
        start_line=1,
        end_line=2,
    )

    # 1. Embed documents
    embedded_docs = engine.embed_documents([doc1, doc2])
    assert len(embedded_docs) == 2
    assert all(len(d.embedding) == 384 for d in embedded_docs)
    assert all(isinstance(v, float) for v in embedded_docs[0].embedding)

    # 2. Build FAISS index
    store = FAISSVectorStore()
    store.build_index(embedded_docs)
    assert store.total_documents == 2
    assert store.embedding_dimension == 384

    # 3. Embed query and search
    query_vector = engine.embed_query("How do I log in and authenticate users?")
    assert len(query_vector) == 384

    results = store.search(query_vector, k=2)
    assert len(results) == 2
    # The auth doc should be ranked top
    top_doc, top_score = results[0]
    assert top_doc.file_name == "auth.py"
    assert top_score > results[1][1]

"""Adversarial and reliability tests for DevMind AI RAG system."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.chunking.code_chunker import CodeChunker
from app.embeddings.embedding_engine import EmbeddingEngine
from app.models import Document
from app.prompts.context_assembler import ContextAssembler
from app.retrieval.config import RetrievalConfig
from app.retrieval.retriever import Retriever
from app.vector_store.faiss_store import FAISSVectorStore


def _make_document(
    content: str,
    file_name: str,
    file_path: str,
    repository_name: str = "proofos",
    function_name: str | None = None,
    class_name: str | None = None,
    start_line: int = 1,
    end_line: int = 20,
) -> Document:
    return Document(
        content=content,
        file_name=file_name,
        file_path=file_path,
        extension="." + file_name.rsplit(".", 1)[-1],
        repository_name=repository_name,
        chunk_type="file",
        function_name=function_name,
        class_name=class_name,
        start_line=start_line,
        end_line=end_line,
    )


def test_adversarial_1_duplicate_symbol_across_multiple_files() -> None:
    """Case 1: Same function name in multiple files."""
    doc1 = _make_document("export function process() { return 'v1'; }", "v1.ts", "lib/v1.ts", function_name="process")
    doc2 = _make_document("export function process() { return 'v2'; }", "v2.ts", "lib/v2.ts", function_name="process")

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1] * 768
    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = [(doc1, 0.90), (doc2, 0.85)]

    retriever = Retriever(mock_engine, mock_store, config=RetrievalConfig(similarity_threshold=0.0))
    results = retriever.retrieve("Where is process implemented in lib/v1.ts?", k=2)

    assert len(results) == 2
    assert results[0].document.file_path == "lib/v1.ts"


def test_adversarial_2_nonexistent_symbol_handling() -> None:
    """Case 3: Query referring to a nonexistent symbol returns search results without inventing chunks."""
    doc1 = _make_document("export class RealService {}", "real.ts", "lib/real.ts")

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1] * 768
    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = [(doc1, 0.20)]  # Below threshold

    retriever = Retriever(mock_engine, mock_store, config=RetrievalConfig(similarity_threshold=0.50))
    results = retriever.retrieve("Where is NonexistentQuantumEngine implemented?", k=5)

    assert len(results) == 0


def test_adversarial_3_missing_context_disclaimer_in_prompt_context() -> None:
    """Case 7: Context assembler outputs explicit no context disclaimer when search results are empty."""
    assembler = ContextAssembler()
    prompt_context = assembler.assemble("Where is the Rust FFI module?", [])

    assert prompt_context.retrieved_context == "No relevant code context found."
    assert len(prompt_context.citations) == 0


def test_adversarial_4_misleading_documentation_vs_production_code() -> None:
    """Case 6: Production implementation takes priority over outdated documentation mentioning same keywords."""
    prod_doc = _make_document("export class ScoringService { static async recalculateAndLogScore() {} }", "scoring.ts", "lib/verification/scoring.ts", class_name="ScoringService")
    doc_doc = _make_document("## Legacy Scoring System\nUse old calculateScore()", "DEPRECATED.md", "docs/DEPRECATED.md")

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1] * 768
    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = [(doc_doc, 0.75), (prod_doc, 0.70)]

    retriever = Retriever(mock_engine, mock_store, config=RetrievalConfig(similarity_threshold=0.0))
    results = retriever.retrieve("Where is Builder Score calculated?", k=2)

    assert results[0].document.file_path == "lib/verification/scoring.ts"

"""CLI entry point for running RAG retrieval evaluation benchmark: python -m app.evaluation"""

from __future__ import annotations

import logging
from pathlib import Path

from app.chunking.code_chunker import CodeChunker
from app.embeddings.embedding_engine import EmbeddingEngine
from app.evaluation.dataset import get_sample_evaluation_dataset
from app.evaluation.evaluator import RAGEvaluator
from app.loaders.repository_loader import RepositoryLoader
from app.retrieval.config import RetrievalConfig
from app.retrieval.retriever import Retriever
from app.vector_store.faiss_store import FAISSVectorStore

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_REPO = PROJECT_ROOT / "repositories" / "sample_project"


def main() -> None:
    """Run baseline vs. hybrid reranked retrieval evaluation benchmark."""
    logging.basicConfig(level=logging.WARNING)

    print("=" * 65)
    print("DevMind AI - RAG Retrieval Evaluation Benchmark")
    print("=" * 65)
    print(f"Loading sample repository from: {SAMPLE_REPO}")

    loader = RepositoryLoader(SAMPLE_REPO)
    documents = loader.load_files()
    chunker = CodeChunker()
    chunks = chunker.chunk_documents(documents)

    print(f"Indexing {len(documents)} file(s) -> {len(chunks)} chunk(s)...")
    embedding_engine = EmbeddingEngine()
    embedded_chunks = embedding_engine.embed_documents(chunks)

    vector_store = FAISSVectorStore()
    vector_store.build_index(embedded_chunks)

    # 1. Baseline Retriever (pure semantic search, no reranking/threshold)
    baseline_config = RetrievalConfig(enable_reranking=False, similarity_threshold=0.0)
    baseline_retriever = Retriever(embedding_engine, vector_store, config=baseline_config)

    # 2. Improved Hybrid Retriever (semantic + keyword/symbol reranking + similarity threshold)
    hybrid_config = RetrievalConfig(enable_reranking=True, similarity_threshold=0.25)
    hybrid_retriever = Retriever(embedding_engine, vector_store, config=hybrid_config)

    evaluator = RAGEvaluator()
    dataset = get_sample_evaluation_dataset()

    print(f"Running evaluation benchmark across {len(dataset)} test query cases...\n")

    baseline_report = evaluator.evaluate(baseline_retriever, dataset)
    hybrid_report = evaluator.evaluate(hybrid_retriever, dataset)

    print("-" * 65)
    print(f"{'Metric':<25} {'Baseline (Semantic)':<20} {'Improved (Hybrid)':<20}")
    print("-" * 65)
    print(f"{'Top-1 Accuracy':<25} {baseline_report.top_1_accuracy:<20.4f} {hybrid_report.top_1_accuracy:<20.4f}")
    print(f"{'Recall@3':<25} {baseline_report.recall_at_3:<20.4f} {hybrid_report.recall_at_3:<20.4f}")
    print(f"{'Recall@5':<25} {baseline_report.recall_at_5:<20.4f} {hybrid_report.recall_at_5:<20.4f}")
    print(f"{'MRR (Mean Recip Rank)':<25} {baseline_report.mrr:<20.4f} {hybrid_report.mrr:<20.4f}")
    print("-" * 65)
    print("Evaluation benchmark complete.\n")


if __name__ == "__main__":
    main()

"""DevMind AI entry point for the load → chunk → embed → index → hybrid retrieve → assemble → generate pipeline."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import MagicMock

from app.chunking.code_chunker import CodeChunker
from app.embeddings.embedding_engine import EmbeddingEngine
from app.llm.gemini_provider import GeminiProvider
from app.loaders.repository_loader import RepositoryLoader
from app.prompts.context_assembler import ContextAssembler
from app.retrieval.config import RetrievalConfig
from app.retrieval.retriever import Retriever
from app.vector_store.faiss_store import FAISSVectorStore

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_SAMPLE_REPO = PROJECT_ROOT / "repositories" / "sample_project"


def main() -> None:
    """Run full DevMind AI pipeline: Load → Chunk → Embed → Index → Hybrid Retrieve → Assemble → Generate."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # 1. Repository Loader
    loader = RepositoryLoader(DEFAULT_SAMPLE_REPO)
    documents = loader.load_files()

    if not documents:
        print(f"No supported files found in {DEFAULT_SAMPLE_REPO}")
        return

    # 2. Code Chunker
    chunker = CodeChunker()
    chunks = chunker.chunk_documents(documents)

    # 3. Embedding Engine
    embedding_engine = EmbeddingEngine()
    embedded_chunks = embedding_engine.embed_documents(chunks)

    # 4. FAISS Vector Store Indexing
    vector_store = FAISSVectorStore()
    vector_store.build_index(embedded_chunks)

    # 5. Advanced Hybrid Retriever (Semantic + Keyword/Symbol Reranking + Threshold)
    config = RetrievalConfig(initial_k=20, final_k=5, similarity_threshold=0.25, enable_reranking=True)
    retriever = Retriever(embedding_engine, vector_store, config=config)

    # 6. Context Assembler
    assembler = ContextAssembler()

    # 7. LLM Provider (Gemini)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        llm_provider = GeminiProvider(api_key=api_key)
    else:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = (
            "The `login()` function is implemented in `auth.py` (lines 6-13). "
            "It accepts a `username` and `password` string to perform JWT user authentication."
        )
        mock_response.usage_metadata.prompt_token_count = 145
        mock_response.usage_metadata.candidates_token_count = 32
        mock_response.usage_metadata.total_token_count = 177
        mock_response.candidates = [MagicMock(finish_reason="STOP")]
        mock_client.models.generate_content.return_value = mock_response

        llm_provider = GeminiProvider(client=mock_client)

    print(
        f"Pipeline complete: {len(documents)} file(s) → "
        f"{len(chunks)} chunk(s) → {len(embedded_chunks)} embedding(s) → "
        f"FAISS Index built ({vector_store.total_documents} document(s))\n"
    )

    # 8. Query, Retrieve & Assemble
    sample_query = "Where is login implemented?"
    search_results = retriever.retrieve(sample_query, k=5)
    prompt_context = assembler.assemble(sample_query, search_results)

    # 9. LLM Generation
    response = llm_provider.generate(prompt_context)

    # 10. Display Response
    print("=" * 60)
    print(f"Provider:     {response.provider}")
    print(f"Model:        {response.model}")
    print(f"Latency:      {response.latency_ms:.2f} ms")
    print("=" * 60)
    print("FINAL ANSWER:")
    print("=" * 60)
    print(response.answer)
    print("=" * 60)


if __name__ == "__main__":
    main()

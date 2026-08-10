"""Unit and integration tests for DevMind RAG V2 architecture improvements."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.chunking.code_chunker import CodeChunker
from app.embeddings.embedding_engine import EmbeddingEngine
from app.graph.code_graph import CodeGraph, CodeNode, CodeEdge
from app.models import Document, SearchResult
from app.prompts.context_assembler import ContextAssembler
from app.retrieval.config import RetrievalConfig
from app.retrieval.query_classifier import QueryClassifier, QueryIntent
from app.retrieval.retriever import Retriever
from app.vector_store.faiss_store import FAISSVectorStore


def _make_document(
    content: str,
    file_name: str,
    file_path: str,
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
        repository_name="proofos",
        chunk_type="file",
        function_name=function_name,
        class_name=class_name,
        start_line=start_line,
        end_line=end_line,
    )


def test_rag_v2_condition_1_verification_engine_retrieval() -> None:
    """Test 1: VerificationEngine retrieval returns lib/verification/engine.ts."""
    prod_doc = _make_document(
        "export class VerificationEngine { static generateProofHash(data) {} }",
        "engine.ts",
        "lib/verification/engine.ts",
        class_name="VerificationEngine",
    )
    test_doc = _make_document(
        "describe('VerificationEngine', () => {})",
        "verification.test.ts",
        "tests/verification.test.ts",
    )

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1] * 384
    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = [(test_doc, 0.70), (prod_doc, 0.65)]

    retriever = Retriever(mock_engine, mock_store, config=RetrievalConfig(similarity_threshold=0.0))
    results = retriever.retrieve("Where is the VerificationEngine class implemented?", k=2)

    assert len(results) >= 1
    assert results[0].document.file_path == "lib/verification/engine.ts"


def test_rag_v2_condition_2_builder_scoring_retrieval() -> None:
    """Test 2: Builder scoring retrieval returns lib/verification/scoring.ts."""
    prod_doc = _make_document(
        "export class ScoringService { static async recalculateAndLogScore() {} }",
        "scoring.ts",
        "lib/verification/scoring.ts",
        class_name="ScoringService",
    )
    doc_doc = _make_document("## Builder Score System Overview", "ARCHITECTURE.md", "ARCHITECTURE.md")

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1] * 384
    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = [(doc_doc, 0.70), (prod_doc, 0.65)]

    retriever = Retriever(mock_engine, mock_store, config=RetrievalConfig(similarity_threshold=0.0))
    results = retriever.retrieve("Where is Builder Score calculated?", k=2)

    assert len(results) >= 1
    assert results[0].document.file_path == "lib/verification/scoring.ts"


def test_rag_v2_condition_3_api_verification_route() -> None:
    """Test 3: API verification returns app/api/verify/route.ts."""
    prod_doc = _make_document(
        "export async function POST(req) { return VerificationPipeline.processSubmission(); }",
        "route.ts",
        "app/api/verify/route.ts",
        function_name="POST",
    )
    helper_doc = _make_document("export class GitHubPipeline {}", "githubPipeline.ts", "lib/integrations/githubPipeline.ts")

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1] * 384
    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = [(helper_doc, 0.80), (prod_doc, 0.75)]

    retriever = Retriever(mock_engine, mock_store, config=RetrievalConfig(similarity_threshold=0.0))
    results = retriever.retrieve("Which API route handles verification submissions for achievements?", k=2)

    assert any(r.document.file_path == "app/api/verify/route.ts" for r in results)


def test_rag_v2_condition_4_github_sync_route() -> None:
    """Test 4: GitHub sync returns app/api/sync/github/route.ts."""
    prod_doc = _make_document(
        "export async function POST(req) { return GitHubIntegration.syncUserData(); }",
        "route.ts",
        "app/api/sync/github/route.ts",
        function_name="POST",
    )

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1] * 384
    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = [(prod_doc, 0.85)]

    retriever = Retriever(mock_engine, mock_store, config=RetrievalConfig(similarity_threshold=0.0))
    results = retriever.retrieve("Which route performs GitHub sync?", k=1)

    assert len(results) == 1
    assert results[0].document.file_path == "app/api/sync/github/route.ts"


def test_rag_v2_condition_5_no_unsupported_graph_edge_between_api_verify_and_github_pipeline() -> None:
    """Test 5: Graph does NOT claim /api/verify calls githubPipeline.ts unless supported by AST edges."""
    chunker = CodeChunker()
    verify_route = _make_document(
        "import { VerificationPipeline } from '@/lib/verification/pipeline';\nexport async function POST() { return VerificationPipeline.processSubmission(); }",
        "route.ts",
        "app/api/verify/route.ts",
    )
    enriched = chunker.chunk_documents([verify_route])
    
    graph = CodeGraph()
    graph.build_from_documents(enriched)

    # Verification route imports pipeline, NOT githubPipeline
    assert "lib/integrations/githubPipeline.ts" not in graph._adjacency.get("app/api/verify/route.ts", set())


def test_rag_v2_condition_6_non_deterministic_hash_recognition() -> None:
    """Test 6: System prompt contains rules prohibiting claiming Date.now() hashing is deterministic."""
    assembler = ContextAssembler()
    prompt = assembler.DEFAULT_SYSTEM_PROMPT
    assert "NEVER describe a hash as deterministic if runtime-varying input like Date.now() participates" in prompt


def test_rag_v2_condition_7_asymmetric_signature_prohibition() -> None:
    """Test 7: System prompt contains rules prohibiting describing SHA-256 as asymmetric signature."""
    assembler = ContextAssembler()
    prompt = assembler.DEFAULT_SYSTEM_PROMPT
    assert "NEVER claim cryptographic asymmetric key signing unless actual private key signing material is present" in prompt


def test_rag_v2_condition_8_passport_route_distinction() -> None:
    """Test 8: System distinguishes /passport (auth), /b/[slug] (mock), and /u/[username] (public DB)."""
    p1 = _make_document("export default function PassportPage() {}", "page.tsx", "app/passport/page.tsx")
    p2 = _make_document("export default function PublicPassportPage({ params }) {}", "page.tsx", "app/b/[slug]/page.tsx")
    p3 = _make_document("export default async function UsernamePassportPage({ params }) {}", "page.tsx", "app/u/[username]/page.tsx")

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.embed_query.return_value = [0.1] * 384
    mock_store = MagicMock(spec=FAISSVectorStore)
    mock_store.search.return_value = [(p1, 0.85), (p2, 0.82), (p3, 0.80)]

    retriever = Retriever(mock_engine, mock_store, config=RetrievalConfig(similarity_threshold=0.0))
    results = retriever.retrieve("Where is the public Builder Passport rendered?", k=3)

    retrieved_paths = [r.document.file_path for r in results]
    assert "app/passport/page.tsx" in retrieved_paths
    assert "app/b/[slug]/page.tsx" in retrieved_paths
    assert "app/u/[username]/page.tsx" in retrieved_paths


def test_rag_v2_condition_9_execution_flow_intent_and_separation() -> None:
    """Test 9: Intent classifier recognizes EXECUTION_FLOW intent and context assembler instructs separate flows."""
    intent = QueryClassifier.classify("Trace the complete GitHub achievement flow from API request to Passport")
    assert intent == QueryIntent.EXECUTION_FLOW

    assembler = ContextAssembler()
    assert "Always present distinct API entry points as separate execution flows (FLOW A, FLOW B)" in assembler.DEFAULT_SYSTEM_PROMPT


def test_rag_v2_condition_10_valid_line_level_citations() -> None:
    """Test 10: Assembled context headers provide precise file_path:start_line-end_line citations."""
    doc = _make_document("export class VerificationEngine {}", "engine.ts", "lib/verification/engine.ts", start_line=15, end_line=45)
    res = SearchResult(rank=1, score=0.95, document=doc)

    assembler = ContextAssembler()
    prompt_ctx = assembler.assemble("Where is VerificationEngine?", [res])

    assert "lib/verification/engine.ts:15-45" in prompt_ctx.retrieved_context
    assert prompt_ctx.citations[0]["start_line"] == 15
    assert prompt_ctx.citations[0]["end_line"] == 45

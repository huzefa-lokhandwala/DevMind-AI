"""Tests for multi-tenant repository retrieval isolation, ownership enforcement, and concurrency safety.

Covers:
1. Cross-user retrieval isolation (retrieval layer and API/service query).
2. Cross-repository isolation for repositories owned by the same user.
3. Concurrent multi-repository access safety (no race conditions on active repository).
4. Interleaved indexing and query sequence isolation (no dependency on 'latest indexed').
"""

from __future__ import annotations

import concurrent.futures
from unittest.mock import MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from pgvector.sqlalchemy import Vector
from app.db.crud import (
    create_or_update_repository,
    create_user,
    get_repository_by_name,
    save_repository_documents,
    search_repository_chunks,
)
from app.db.database import Base
from app.embeddings.embedding_engine import EmbeddingEngine
from app.llm import BaseLLMProvider
from app.models.llm_response import LLMResponse
from app.models.document import Document
from app.retrieval.config import RetrievalConfig
from app.retrieval.retriever import Retriever
from app.services.rag_service import (
    RAGService,
    RepositoryNotFoundError,
    RepositoryNotIndexedError,
)


# Compile Vector as TEXT for SQLite test environments
@compiles(Vector, "sqlite")
def _compile_vector_sqlite(element, compiler, **kw):
    return "TEXT"


@pytest.fixture
def multi_tenant_db():
    """Create a thread-safe in-memory SQLite database session for multi-tenant testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    session.SessionLocal = TestingSessionLocal
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _make_chunk_doc(
    content: str,
    file_name: str,
    file_path: str,
    repository_name: str,
    embedding: list[float],
) -> Document:
    return Document(
        content=content,
        file_name=file_name,
        file_path=file_path,
        extension="." + file_name.rsplit(".", 1)[-1],
        repository_name=repository_name,
        language="python",
        chunk_type="function",
        function_name=file_name.split(".")[0],
        start_line=1,
        end_line=10,
        embedding=embedding,
    )


class MockLLM(BaseLLMProvider):
    """Deterministic mock LLM for testing RAG service response generation."""

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-model"

    def generate(self, prompt: Any, **kwargs) -> LLMResponse:
        prompt_text = getattr(prompt, "user_prompt", str(prompt))
        return LLMResponse(
            answer=f"Generated answer for prompt: {prompt_text[:100]}...",
            provider="mock",
            model="mock-model",
            latency_ms=1.5,
        )


def test_cross_user_retrieval_layer_and_service_isolation(multi_tenant_db):
    """Verify User A and User B repositories are strictly isolated at both the retrieval layer and query service."""
    # 1. Setup User A and User B
    user_a = create_user(multi_tenant_db, email="user_a@devmind.test", password_hash="hash_a")
    user_b = create_user(multi_tenant_db, email="user_b@devmind.test", password_hash="hash_b")

    # Distinct vector embeddings
    emb_a = [1.0, 0.0, 0.0] + [0.0] * 381
    emb_b = [0.0, 1.0, 0.0] + [0.0] * 381

    # 2. Seed Repository A for User A with unique content
    repo_a = create_or_update_repository(
        multi_tenant_db,
        name="repo_alpha",
        source="/repos/repo_alpha",
        user_id=user_a.id,
        status="indexed",
        embedding_provider="local",
        embedding_dimension=384,
    )
    doc_a = _make_chunk_doc(
        content="def alpha_secret_key(): return 'ALPHA-KEY-999'",
        file_name="alpha.py",
        file_path="src/alpha.py",
        repository_name="repo_alpha",
        embedding=emb_a,
    )
    save_repository_documents(multi_tenant_db, repo_a.id, [doc_a])

    # 3. Seed Repository B for User B with different unique content
    repo_b = create_or_update_repository(
        multi_tenant_db,
        name="repo_beta",
        source="/repos/repo_beta",
        user_id=user_b.id,
        status="indexed",
        embedding_provider="local",
        embedding_dimension=384,
    )
    doc_b = _make_chunk_doc(
        content="def beta_secret_token(): return 'BETA-TOKEN-777'",
        file_name="beta.py",
        file_path="src/beta.py",
        repository_name="repo_beta",
        embedding=emb_b,
    )
    save_repository_documents(multi_tenant_db, repo_b.id, [doc_b])

    # 4. Verify retrieval layer directly (search_repository_chunks)
    # Searching repo_a with emb_a must return only repo_a chunks
    matches_a = search_repository_chunks(multi_tenant_db, repository_id=repo_a.id, query_vector=emb_a, top_k=5)
    assert len(matches_a) == 1
    assert matches_a[0][0].repository_name == "repo_alpha"
    assert "ALPHA-KEY-999" in matches_a[0][0].content

    # Searching repo_a with emb_b must NEVER return repo_b chunks
    matches_a_b = search_repository_chunks(multi_tenant_db, repository_id=repo_a.id, query_vector=emb_b, top_k=5)
    assert all(doc.repository_name == "repo_alpha" for doc, _ in matches_a_b)
    assert not any("BETA-TOKEN-777" in doc.content for doc, _ in matches_a_b)

    # Searching repo_b must NEVER return repo_a chunks
    matches_b = search_repository_chunks(multi_tenant_db, repository_id=repo_b.id, query_vector=emb_b, top_k=5)
    assert len(matches_b) == 1
    assert matches_b[0][0].repository_name == "repo_beta"
    assert "BETA-TOKEN-777" in matches_b[0][0].content

    # 5. Verify Retriever coordinate layer
    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.provider_name = "local"
    mock_engine.embedding_dimension = 384
    mock_engine.embed_query.side_effect = lambda q: emb_a if "alpha" in q.lower() else emb_b

    retriever = Retriever(embedding_engine=mock_engine, config=RetrievalConfig(similarity_threshold=0.0))

    results_a = retriever.retrieve("query alpha", k=5, repository_id=repo_a.id, db_session=multi_tenant_db)
    assert len(results_a) == 1
    assert results_a[0].document.repository_name == "repo_alpha"
    assert "ALPHA-KEY-999" in results_a[0].document.content

    results_b = retriever.retrieve("query beta", k=5, repository_id=repo_b.id, db_session=multi_tenant_db)
    assert len(results_b) == 1
    assert results_b[0].document.repository_name == "repo_beta"
    assert "BETA-TOKEN-777" in results_b[0].document.content

    # 6. Verify end-to-end RAGService query authorization and retrieval
    service = RAGService(embedding_engine=mock_engine, llm_provider=MockLLM(), db_session=multi_tenant_db)

    # User A querying Repo A -> SUCCESS, returns Repo A evidence
    res_a = service.query(
        "Where is alpha_secret_key function?",
        user_id=user_a.id,
        repository_name="repo_alpha",
        db_session=multi_tenant_db,
    )
    assert len(res_a["sources"]) == 1
    assert res_a["sources"][0]["repository"] == "repo_alpha"
    assert "ALPHA-KEY-999" in res_a["sources"][0]["snippet"]

    # User B querying Repo B -> SUCCESS, returns Repo B evidence
    res_b = service.query(
        "Where is beta_secret_token function?",
        user_id=user_b.id,
        repository_name="repo_beta",
        db_session=multi_tenant_db,
    )
    assert len(res_b["sources"]) == 1
    assert res_b["sources"][0]["repository"] == "repo_beta"
    assert "BETA-TOKEN-777" in res_b["sources"][0]["snippet"]

    # User A querying Repo B -> Resource-safe RepositoryNotFoundError (404, no existence leakage)
    with pytest.raises(RepositoryNotFoundError) as exc_info:
        service.query(
            "Where is beta_secret_token function?",
            user_id=user_a.id,
            repository_name="repo_beta",
            db_session=multi_tenant_db,
        )
    assert "repo_beta" in str(exc_info.value)

    # User B querying Repo A -> Resource-safe RepositoryNotFoundError (404, no existence leakage)
    with pytest.raises(RepositoryNotFoundError) as exc_info:
        service.query(
            "Where is alpha_secret_key function?",
            user_id=user_b.id,
            repository_name="repo_alpha",
            db_session=multi_tenant_db,
        )
    assert "repo_alpha" in str(exc_info.value)


def test_cross_repository_same_user_isolation(multi_tenant_db):
    """Verify multiple repositories owned by the SAME user cannot cross-contaminate retrieval."""
    user = create_user(multi_tenant_db, email="multi_repo_dev@devmind.test", password_hash="dev_hash")

    emb_1 = [1.0, 0.0, 0.0] + [0.0] * 381
    emb_2 = [0.0, 1.0, 0.0] + [0.0] * 381

    # Repo 1: Auth service
    repo_1 = create_or_update_repository(
        multi_tenant_db,
        name="auth_service",
        source="/repos/auth_service",
        user_id=user.id,
        status="indexed",
        embedding_provider="local",
        embedding_dimension=384,
    )
    doc_1 = _make_chunk_doc(
        content="def verify_jwt_credentials(): pass",
        file_name="auth.py",
        file_path="src/auth.py",
        repository_name="auth_service",
        embedding=emb_1,
    )
    save_repository_documents(multi_tenant_db, repo_1.id, [doc_1])

    # Repo 2: Billing service
    repo_2 = create_or_update_repository(
        multi_tenant_db,
        name="billing_service",
        source="/repos/billing_service",
        user_id=user.id,
        status="indexed",
        embedding_provider="local",
        embedding_dimension=384,
    )
    doc_2 = _make_chunk_doc(
        content="def charge_stripe_subscription(): pass",
        file_name="billing.py",
        file_path="src/billing.py",
        repository_name="billing_service",
        embedding=emb_2,
    )
    save_repository_documents(multi_tenant_db, repo_2.id, [doc_2])

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.provider_name = "local"
    mock_engine.embedding_dimension = 384
    mock_engine.embed_query.side_effect = lambda q: emb_1 if "auth" in q.lower() else emb_2

    service = RAGService(embedding_engine=mock_engine, llm_provider=MockLLM(), db_session=multi_tenant_db)

    # Querying auth_service must ONLY return auth_service chunks
    res_1 = service.query(
        "How does verify_jwt_credentials function work?",
        user_id=user.id,
        repository_name="auth_service",
        db_session=multi_tenant_db,
    )
    assert len(res_1["sources"]) == 1
    assert res_1["sources"][0]["repository"] == "auth_service"
    assert "verify_jwt_credentials" in res_1["sources"][0]["snippet"]
    assert "billing" not in res_1["sources"][0]["snippet"]

    # Querying billing_service must ONLY return billing_service chunks
    res_2 = service.query(
        "How does charge_stripe_subscription function work?",
        user_id=user.id,
        repository_name="billing_service",
        db_session=multi_tenant_db,
    )
    assert len(res_2["sources"]) == 1
    assert res_2["sources"][0]["repository"] == "billing_service"
    assert "charge_stripe_subscription" in res_2["sources"][0]["snippet"]
    assert "verify_jwt" not in res_2["sources"][0]["snippet"]


def test_concurrent_multi_repository_access_safety(tmp_path):
    """Test concurrent queries to different repositories in separate threads produce strictly isolated results."""
    db_file = tmp_path / "concurrent_test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"timeout": 30.0},
    )
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    setup_db = SessionMaker()
    user = create_user(setup_db, email="concurrent_user@test.com", password_hash="hash")

    # Setup Repo A
    emb_a = [1.0, 0.0] + [0.0] * 382
    repo_a = create_or_update_repository(
        setup_db,
        name="concurrent_repo_a",
        source="/repos/a",
        user_id=user.id,
        status="indexed",
        embedding_provider="local",
        embedding_dimension=384,
    )
    doc_a = _make_chunk_doc(
        content="def function_unique_to_repo_a(): return 'AAA'",
        file_name="a.py",
        file_path="src/a.py",
        repository_name="concurrent_repo_a",
        embedding=emb_a,
    )
    save_repository_documents(setup_db, repo_a.id, [doc_a])

    # Setup Repo B
    emb_b = [0.0, 1.0] + [0.0] * 382
    repo_b = create_or_update_repository(
        setup_db,
        name="concurrent_repo_b",
        source="/repos/b",
        user_id=user.id,
        status="indexed",
        embedding_provider="local",
        embedding_dimension=384,
    )
    doc_b = _make_chunk_doc(
        content="def function_unique_to_repo_b(): return 'BBB'",
        file_name="b.py",
        file_path="src/b.py",
        repository_name="concurrent_repo_b",
        embedding=emb_b,
    )
    save_repository_documents(setup_db, repo_b.id, [doc_b])
    user_id = int(user.id)
    setup_db.close()

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.provider_name = "local"
    mock_engine.embedding_dimension = 384
    mock_engine.embed_query.side_effect = lambda q: emb_a if "repo_a" in q.lower() else emb_b

    service = RAGService(embedding_engine=mock_engine, llm_provider=MockLLM())

    def run_query(repo_name: str, query_text: str):
        thread_db = SessionMaker()
        try:
            return service.query(
                query_text=query_text,
                repository_name=repo_name,
                user_id=user_id,
                db_session=thread_db,
            )
        finally:
            thread_db.close()

    queries = [
        ("concurrent_repo_a", "Explain function_unique_to_repo_a in codebase"),
        ("concurrent_repo_b", "Explain function_unique_to_repo_b in codebase"),
        ("concurrent_repo_a", "Explain function_unique_to_repo_a in codebase"),
        ("concurrent_repo_b", "Explain function_unique_to_repo_b in codebase"),
        ("concurrent_repo_a", "Explain function_unique_to_repo_a in codebase"),
        ("concurrent_repo_b", "Explain function_unique_to_repo_b in codebase"),
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(run_query, repo, q) for repo, q in queries]
        results = [f.result() for f in futures]

    for (repo_name, _), res in zip(queries, results, strict=True):
        assert len(res["sources"]) == 1
        source = res["sources"][0]
        assert source["repository"] == repo_name
        if repo_name == "concurrent_repo_a":
            assert "AAA" in source["snippet"]
            assert "BBB" not in source["snippet"]
        else:
            assert "BBB" in source["snippet"]
            assert "AAA" not in source["snippet"]


def test_interleaved_indexing_and_query_sequence_isolation(multi_tenant_db):
    """Verify that query results do NOT depend on whichever repository was indexed most recently.

    Sequence:
    1. Index Repo A
    2. Index Repo B
    3. Query Repo A -> must retrieve Repo A
    4. Query Repo B -> must retrieve Repo B
    5. Query Repo A again -> must still retrieve Repo A
    """
    user = create_user(multi_tenant_db, email="seq_user@test.com", password_hash="hash")

    emb_a = [1.0, 0.0] + [0.0] * 382
    emb_b = [0.0, 1.0] + [0.0] * 382

    # Step 1: Index Repo A
    repo_a = create_or_update_repository(
        multi_tenant_db,
        name="sequence_repo_a",
        source="/repos/seq_a",
        user_id=user.id,
        status="indexed",
        embedding_provider="local",
        embedding_dimension=384,
    )
    doc_a = _make_chunk_doc(
        content="def sequence_chunk_a(): return 'ALPHA_PAYLOAD'",
        file_name="seq_a.py",
        file_path="src/seq_a.py",
        repository_name="sequence_repo_a",
        embedding=emb_a,
    )
    save_repository_documents(multi_tenant_db, repo_a.id, [doc_a])

    # Step 2: Index Repo B
    repo_b = create_or_update_repository(
        multi_tenant_db,
        name="sequence_repo_b",
        source="/repos/seq_b",
        user_id=user.id,
        status="indexed",
        embedding_provider="local",
        embedding_dimension=384,
    )
    doc_b = _make_chunk_doc(
        content="def sequence_chunk_b(): return 'BETA_PAYLOAD'",
        file_name="seq_b.py",
        file_path="src/seq_b.py",
        repository_name="sequence_repo_b",
        embedding=emb_b,
    )
    save_repository_documents(multi_tenant_db, repo_b.id, [doc_b])

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.provider_name = "local"
    mock_engine.embedding_dimension = 384
    mock_engine.embed_query.side_effect = lambda q: emb_a if "seq_a" in q.lower() else emb_b

    service = RAGService(embedding_engine=mock_engine, llm_provider=MockLLM(), db_session=multi_tenant_db)

    # Step 3: Query Repo A
    res_a_1 = service.query(
        "Find sequence_chunk_a in seq_a",
        repository_name="sequence_repo_a",
        user_id=user.id,
        db_session=multi_tenant_db,
    )
    assert len(res_a_1["sources"]) == 1
    assert res_a_1["sources"][0]["repository"] == "sequence_repo_a"
    assert "ALPHA_PAYLOAD" in res_a_1["sources"][0]["snippet"]

    # Step 4: Query Repo B
    res_b_1 = service.query(
        "Find sequence_chunk_b in seq_b",
        repository_name="sequence_repo_b",
        user_id=user.id,
        db_session=multi_tenant_db,
    )
    assert len(res_b_1["sources"]) == 1
    assert res_b_1["sources"][0]["repository"] == "sequence_repo_b"
    assert "BETA_PAYLOAD" in res_b_1["sources"][0]["snippet"]

    # Step 5: Query Repo A again -> must STILL return Repo A
    res_a_2 = service.query(
        "Find sequence_chunk_a in seq_a again",
        repository_name="sequence_repo_a",
        user_id=user.id,
        db_session=multi_tenant_db,
    )
    assert len(res_a_2["sources"]) == 1
    assert res_a_2["sources"][0]["repository"] == "sequence_repo_a"
    assert "ALPHA_PAYLOAD" in res_a_2["sources"][0]["snippet"]


def test_authenticated_query_without_repository_never_inherits_global_last_indexed_repository(multi_tenant_db):
    """Verify that an authenticated user without repository context NEVER inherits a global/last-indexed repository."""
    user_a = create_user(multi_tenant_db, email="user_a_orphan@test.com", password_hash="hash_a")
    user_b = create_user(multi_tenant_db, email="user_b_owner@test.com", password_hash="hash_b")

    emb_b = [0.0, 1.0, 0.0] + [0.0] * 381

    # User B owns and indexes Repo B
    repo_b = create_or_update_repository(
        multi_tenant_db,
        name="user_b_private_repo",
        source="/repos/user_b",
        user_id=user_b.id,
        status="indexed",
        embedding_provider="local",
        embedding_dimension=384,
    )
    doc_b = _make_chunk_doc(
        content="def user_b_confidential(): return 'SECRET-B-DATA'",
        file_name="confidential.py",
        file_path="src/confidential.py",
        repository_name="user_b_private_repo",
        embedding=emb_b,
    )
    save_repository_documents(multi_tenant_db, repo_b.id, [doc_b])

    mock_engine = MagicMock(spec=EmbeddingEngine)
    mock_engine.provider_name = "local"
    mock_engine.embedding_dimension = 384
    mock_engine.embed_query.return_value = emb_b

    service = RAGService(embedding_engine=mock_engine, llm_provider=MockLLM(), db_session=multi_tenant_db)

    # Simulate global state: Repo B was the last repository indexed on this service instance
    service.indexed_repository_name = "user_b_private_repo"
    from app.vector_store import FAISSVectorStore
    store = FAISSVectorStore(dimension=384)
    store.build_index([doc_b])
    service.vector_store = store

    # 1. User A (authenticated) queries for code without specifying repository_name
    # Must fail with RepositoryNotIndexedError, NEVER falling back to User B's repository
    with pytest.raises(RepositoryNotIndexedError) as exc_info:
        service.query(
            "Where is user_b_confidential function in the codebase?",
            user_id=user_a.id,
            repository_name=None,
            conversation_id=None,
            db_session=multi_tenant_db,
        )
    assert "Repository context is required for authenticated repository queries" in str(exc_info.value)

    # 2. Even if User A asks a general question without repository, sources must be empty
    gen_res = service.query(
        "Explain what an HTTP status code is.",
        user_id=user_a.id,
        repository_name=None,
        conversation_id=None,
        db_session=multi_tenant_db,
    )
    assert gen_res["sources"] == []
    assert "SECRET-B-DATA" not in gen_res["answer"]


def test_sqlite_fallback_dialect_safety(multi_tenant_db):
    """Verify that search_repository_chunks fails closed if an unsupported dialect is encountered."""
    # SQLite dialect should work properly
    assert multi_tenant_db.bind.dialect.name == "sqlite"
    res = search_repository_chunks(multi_tenant_db, repository_id=9999, query_vector=[0.1] * 384)
    assert res == []

    # Mock an unsupported dialect (e.g. unknown or misconfigured production engine)
    mock_db = MagicMock()
    mock_db.bind.dialect.name = "unsupported_db"

    with pytest.raises(RuntimeError) as exc_info:
        search_repository_chunks(mock_db, repository_id=1, query_vector=[0.1] * 384)
    assert "Unsupported database dialect for vector search: 'unsupported_db'" in str(exc_info.value)

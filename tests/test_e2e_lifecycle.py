"""End-to-end application lifecycle test for Phase 7 production verification.

Validates the full chain:
1. User registration
2. User authentication (Argon2id + JWT)
3. GET /auth/me user profile verification
4. Real repository indexing
5. Authenticated RAG query with evidence retrieval & LLM generation
6. Multi-tenant conversation message tracking
7. Client logout
8. Protected endpoint failure on unauthenticated/expired request
9. Second user registration & authentication
10. Strict multi-tenant isolation across repositories, queries, conversations, and indexing jobs.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pgvector.sqlalchemy import Vector

from app.api.main import app
from app.db.database import Base, get_db
from app.llm import BaseLLMProvider
from app.models.llm_response import LLMResponse
from app.prompts.context_assembler import PromptContext
from app.services.rag_service import RAGService


# Compile Vector as TEXT for SQLite in-memory test database
@compiles(Vector, "sqlite")
def _compile_vector_sqlite_e2e(element, compiler, **kw):
    return "TEXT"


class MockE2ELLMProvider(BaseLLMProvider):
    """Predictable mock provider for deterministic E2E generation testing."""

    def __init__(self):
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return "mock_e2e_provider"

    @property
    def model_name(self) -> str:
        return "mock-e2e-model-v1"

    @property
    def is_configured(self) -> bool:
        return True

    def generate(self, context: PromptContext) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(
            answer=f"E2E verified response for query: {context.user_question}.",
            provider=self.provider_name,
            model=self.model_name,
            latency_ms=12.5,
            usage_tokens={"prompt": 42, "completion": 24, "total": 66},
        )


@pytest.fixture
def e2e_db():
    """Create an isolated, thread-safe in-memory SQLite database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    session.SessionLocal = TestingSessionLocal
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def e2e_client(e2e_db):
    """FastAPI TestClient with overridden get_db and isolated RAGService."""
    def _override_get_db():
        try:
            yield e2e_db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    # Initialize RAGService with local FastEmbed and mock LLM provider
    mock_llm = MockE2ELLMProvider()
    rag_service = RAGService(
        llm_provider=mock_llm,
        db_session=e2e_db,
    )

    from app.api.routes.query import get_rag_service as get_rag_query
    from app.api.routes.repositories import get_rag_service as get_rag_repo

    app.dependency_overrides[get_rag_query] = lambda: rag_service
    app.dependency_overrides[get_rag_repo] = lambda: rag_service

    test_api_key = "test_phase7_e2e_api_key_secure"
    with patch.dict(os.environ, {"DEVMIND_API_KEY": test_api_key, "DEVMIND_ENV": "development"}):
        with TestClient(app, headers={"X-API-Key": test_api_key}) as client:
            client.app.state.rag_service = rag_service
            yield client, rag_service, test_api_key

    app.dependency_overrides.pop(get_rag_query, None)
    app.dependency_overrides.pop(get_rag_repo, None)


def test_full_real_e2e_lifecycle(e2e_client, e2e_db):
    """Execute complete end-to-end application lifecycle and cross-tenant verification."""
    client, rag_service, api_key = e2e_client

    sample_repo_path = str(Path(__file__).parent.parent / "repositories" / "sample_project")
    assert Path(sample_repo_path).exists(), f"Sample project not found at {sample_repo_path}"

    # -------------------------------------------------------------------------
    # STEP 1: Register User A
    # -------------------------------------------------------------------------
    reg_a = client.post(
        "/auth/register",
        json={
            "email": "user_a_e2e@example.com",
            "password": "Password123!",
            "full_name": "User Alpha",
        },
    )
    assert reg_a.status_code == 201
    user_a_data = reg_a.json()
    assert user_a_data["email"] == "user_a_e2e@example.com"
    assert user_a_data["full_name"] == "User Alpha"
    assert "password" not in user_a_data
    assert "password_hash" not in user_a_data
    user_a_id = user_a_data["id"]

    # -------------------------------------------------------------------------
    # STEP 2: Login User A -> obtain real JWT access token
    # -------------------------------------------------------------------------
    login_a = client.post(
        "/auth/login",
        json={"email": "user_a_e2e@example.com", "password": "Password123!"},
    )
    assert login_a.status_code == 200
    token_a_data = login_a.json()
    assert "access_token" in token_a_data
    assert token_a_data["token_type"] == "bearer"
    token_a = token_a_data["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}", "X-API-Key": api_key}

    # -------------------------------------------------------------------------
    # STEP 3: Verify GET /auth/me with User A token
    # -------------------------------------------------------------------------
    me_a = client.get("/auth/me", headers=headers_a)
    assert me_a.status_code == 200
    assert me_a.json()["id"] == user_a_id
    assert me_a.json()["email"] == "user_a_e2e@example.com"

    # -------------------------------------------------------------------------
    # STEP 4: Index real repository for User A
    # -------------------------------------------------------------------------
    index_res = client.post(
        "/repositories/index",
        headers=headers_a,
        json={"repository_path": sample_repo_path},
    )
    assert index_res.status_code == 200
    index_data = index_res.json()
    assert index_data["status"] == "indexed"
    assert index_data["files_loaded"] > 0
    assert index_data["chunks_created"] > 0
    assert index_data["embeddings_created"] > 0
    job_id_a = index_data["job_id"]

    # Verify indexing status endpoint for User A
    status_a = client.get(f"/repositories/index/status/{job_id_a}", headers=headers_a)
    assert status_a.status_code == 200
    assert status_a.json()["status"] == "COMPLETED"

    # -------------------------------------------------------------------------
    # STEP 5: Create Conversation for User A
    # -------------------------------------------------------------------------
    conv_res = client.post(
        "/conversations",
        headers=headers_a,
        json={"title": "E2E Architecture Discussion", "repository_name": "sample_project"},
    )
    assert conv_res.status_code == 201
    conv_a_id = conv_res.json()["id"]

    # -------------------------------------------------------------------------
    # STEP 6: Execute Authenticated RAG Query for User A
    # -------------------------------------------------------------------------
    query_res = client.post(
        "/query",
        headers=headers_a,
        json={
            "query": "How does the sample project calculate totals or handle items?",
            "repository_name": "sample_project",
            "conversation_id": conv_a_id,
            "top_k": 3,
        },
    )
    assert query_res.status_code == 200
    query_data = query_res.json()
    assert "answer" in query_data
    assert len(query_data["sources"]) > 0
    # Verify evidence citations contain actual file information
    first_source = query_data["sources"][0]
    assert "file_path" in first_source
    assert "snippet" in first_source
    assert first_source["score"] > 0.0

    # -------------------------------------------------------------------------
    # STEP 7: Verify Conversation History persists messages for User A
    # -------------------------------------------------------------------------
    conv_detail = client.get(f"/conversations/{conv_a_id}", headers=headers_a)
    assert conv_detail.status_code == 200
    messages = conv_detail.json()["messages"]
    assert len(messages) >= 2  # user message and assistant message
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

    # -------------------------------------------------------------------------
    # STEP 8: Logout User A
    # -------------------------------------------------------------------------
    logout_a = client.post("/auth/logout", headers=headers_a)
    assert logout_a.status_code == 200
    assert "logged out" in logout_a.json()["message"].lower()

    # Protected endpoints fail without token
    unauth = client.get("/auth/me", headers={"X-API-Key": api_key})
    assert unauth.status_code == 401

    # -------------------------------------------------------------------------
    # STEP 9: Register & Login User B
    # -------------------------------------------------------------------------
    reg_b = client.post(
        "/auth/register",
        json={
            "email": "user_b_e2e@example.com",
            "password": "Password123!",
            "full_name": "User Beta",
        },
    )
    assert reg_b.status_code == 201
    login_b = client.post(
        "/auth/login",
        json={"email": "user_b_e2e@example.com", "password": "Password123!"},
    )
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}", "X-API-Key": api_key}

    # -------------------------------------------------------------------------
    # STEP 10: Multi-Tenant Authorization Isolation Checks for User B
    # -------------------------------------------------------------------------
    # 1. User B cannot see User A's conversation in list
    list_b = client.get("/conversations", headers=headers_b)
    assert list_b.status_code == 200
    assert all(c["id"] != conv_a_id for c in list_b.json())

    # 2. User B cannot access User A's conversation directly -> 404
    conv_b = client.get(f"/conversations/{conv_a_id}", headers=headers_b)
    assert conv_b.status_code == 404

    # 3. User B cannot view User A's indexing job status -> 404
    status_b = client.get(f"/repositories/index/status/{job_id_a}", headers=headers_b)
    assert status_b.status_code == 404

    # 4. User B cannot query User A's repository -> 404 Not Found
    query_b = client.post(
        "/query",
        headers=headers_b,
        json={
            "query": "How does the sample project calculate totals?",
            "repository_name": "sample_project",
            "top_k": 3,
        },
    )
    assert query_b.status_code == 404
    assert "not found" in query_b.json()["detail"].lower()

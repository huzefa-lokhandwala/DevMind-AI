"""Comprehensive test suite for User Authentication, Argon2id Password Hashing,
JWT Token Validation, and Multi-Tenant User Ownership / Isolation in DevMind AI.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.db.database import Base, get_db
from app.db.models import UserModel, RepositoryModel, ConversationModel
from app.services.rag_service import RAGService, RepositoryNotIndexedError
from app.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

TEST_API_KEY = "test_auth_api_key_xyz123"


@pytest.fixture
def test_db():
    """Create an isolated in-memory SQLite database session for auth tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """FastAPI TestClient with overridden get_db dependency and active lifespan."""
    def _override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with patch.dict(os.environ, {"DEVMIND_API_KEY": TEST_API_KEY, "DEVMIND_ENV": "development"}):
        with TestClient(app, headers={"X-API-Key": TEST_API_KEY}) as test_client:
            yield test_client
    app.dependency_overrides.pop(get_db, None)


# =============================================================================
# 1. PASSWORD SECURITY & ARGON2ID HASHING TESTS
# =============================================================================

def test_argon2id_password_hashing():
    """Verify password hashing produces Argon2id hashes and validates correctly."""
    raw_pwd = "SuperSecretPassword123!"
    hashed = hash_password(raw_pwd)

    assert hashed.startswith("$argon2id$")
    assert raw_pwd not in hashed
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(raw_pwd, "invalid_hash_string") is False


# =============================================================================
# 2. JWT TOKEN ISSUANCE AND VERIFICATION TESTS
# =============================================================================

def test_jwt_token_generation_and_validation():
    """Verify JWT access tokens encode subject and validate expiry/signature."""
    token = create_access_token(user_id=42, email="user@example.com")
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["email"] == "user@example.com"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_invalid_token():
    """Verify malformed or forged tokens raise 401 HTTPException."""
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("not.a.valid.jwt")
    assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("")
    assert exc_info.value.status_code == 401


# =============================================================================
# 3. REGISTRATION API TESTS (POST /auth/register)
# =============================================================================

def test_register_success(client):
    """Verify successful user registration returns 201 and safe profile (no passwords)."""
    resp = client.post(
        "/auth/register",
        json={
            "email": "Alice@Example.COM ",
            "password": "Password123!",
            "full_name": "Alice Smith",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@example.com"
    assert data["full_name"] == "Alice Smith"
    assert data["is_active"] is True
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email(client):
    """Verify registering with duplicate email returns 409 Conflict."""
    client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "Password123!"},
    )
    resp = client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "DifferentPassword123!"},
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


def test_register_validation_short_password(client):
    """Verify password shorter than 8 characters is rejected with 422."""
    resp = client.post(
        "/auth/register",
        json={"email": "charlie@example.com", "password": "short"},
    )
    assert resp.status_code == 422


def test_register_validation_invalid_email(client):
    """Verify invalid email string is rejected with 422."""
    resp = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "Password123!"},
    )
    assert resp.status_code == 422


# =============================================================================
# 4. LOGIN API TESTS (POST /auth/login)
# =============================================================================

def test_login_success(client):
    """Verify successful login returns bearer token and user info."""
    client.post(
        "/auth/register",
        json={"email": "login_user@example.com", "password": "Password123!"},
    )

    resp = client.post(
        "/auth/login",
        json={"email": "LOGIN_USER@example.com", "password": "Password123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login_user@example.com"
    assert "password_hash" not in data["user"]


def test_login_invalid_password_returns_generic_error(client):
    """Verify wrong password returns 401 with generic error (no account enumeration)."""
    client.post(
        "/auth/register",
        json={"email": "target@example.com", "password": "Password123!"},
    )

    resp = client.post(
        "/auth/login",
        json={"email": "target@example.com", "password": "WrongPassword123!"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password."


def test_login_nonexistent_email_returns_identical_generic_error(client):
    """Verify non-existent email returns exact same 401 message to prevent enumeration."""
    resp = client.post(
        "/auth/login",
        json={"email": "does_not_exist@example.com", "password": "Password123!"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password."


# =============================================================================
# 5. CURRENT USER API (GET /auth/me) & LOGOUT (POST /auth/logout)
# =============================================================================

def test_get_current_user_me_authenticated(client):
    """Verify GET /auth/me with valid Bearer token returns profile."""
    client.post(
        "/auth/register",
        json={"email": "me_user@example.com", "password": "Password123!", "full_name": "Me User"},
    )
    login_res = client.post(
        "/auth/login",
        json={"email": "me_user@example.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}", "X-API-Key": TEST_API_KEY})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "me_user@example.com"
    assert data["full_name"] == "Me User"


def test_get_current_user_me_missing_token(client):
    """Verify GET /auth/me without token returns 401."""
    resp = client.get("/auth/me", headers={"X-API-Key": TEST_API_KEY})
    assert resp.status_code == 401


def test_logout_endpoint(client):
    """Verify POST /auth/logout returns 200 success response when authenticated and 401 when missing."""
    client.post(
        "/auth/register",
        json={"email": "logout_user@example.com", "password": "Password123!"},
    )
    login_res = client.post(
        "/auth/login",
        json={"email": "logout_user@example.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]

    resp = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}", "X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 200
    assert "logged out" in resp.json()["message"].lower()

    # Unauthenticated attempt should fail with 401
    unauth_resp = client.post("/auth/logout", headers={"X-API-Key": TEST_API_KEY})
    assert unauth_resp.status_code == 401


# =============================================================================
# 6. CONVERSATION OWNERSHIP & CROSS-USER ISOLATION TESTS
# =============================================================================

def test_cross_user_conversation_isolation(client):
    """Verify User A and User B cannot view, modify, or delete each other's conversations."""
    # Register User A and User B
    client.post("/auth/register", json={"email": "user_a@test.com", "password": "Password123!"})
    token_a = client.post("/auth/login", json={"email": "user_a@test.com", "password": "Password123!"}).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}", "X-API-Key": TEST_API_KEY}

    client.post("/auth/register", json={"email": "user_b@test.com", "password": "Password123!"})
    token_b = client.post("/auth/login", json={"email": "user_b@test.com", "password": "Password123!"}).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}", "X-API-Key": TEST_API_KEY}

    # User A creates a conversation
    create_res = client.post("/conversations", headers=headers_a, json={"title": "User A Private Chat"})
    assert create_res.status_code == 201
    conv_a_id = create_res.json()["id"]

    # User B lists conversations -> User A's conversation must NOT appear
    list_b = client.get("/conversations", headers=headers_b)
    assert list_b.status_code == 200
    b_conv_ids = [c["id"] for c in list_b.json()]
    assert conv_a_id not in b_conv_ids

    # User B attempts to read User A's conversation directly -> 404
    get_b = client.get(f"/conversations/{conv_a_id}", headers=headers_b)
    assert get_b.status_code == 404

    # User B attempts to update User A's conversation -> 404
    patch_b = client.patch(f"/conversations/{conv_a_id}", headers=headers_b, json={"title": "Hacked Title"})
    assert patch_b.status_code == 404

    # User B attempts to delete User A's conversation -> 404
    del_b = client.delete(f"/conversations/{conv_a_id}", headers=headers_b)
    assert del_b.status_code == 404

    # Verify User A can still retrieve and delete their conversation
    get_a = client.get(f"/conversations/{conv_a_id}", headers=headers_a)
    assert get_a.status_code == 200
    assert get_a.json()["title"] == "User A Private Chat"

    del_a = client.delete(f"/conversations/{conv_a_id}", headers=headers_a)
    assert del_a.status_code == 204


# =============================================================================
# 7. INDEXING JOB STATUS OWNERSHIP ISOLATION
# =============================================================================

def test_indexing_job_ownership_isolation(client):
    """Verify User B cannot view the status of an indexing job submitted by User A."""
    client.post("/auth/register", json={"email": "indexer_a@test.com", "password": "Password123!"})
    token_a = client.post("/auth/login", json={"email": "indexer_a@test.com", "password": "Password123!"}).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}", "X-API-Key": TEST_API_KEY}

    client.post("/auth/register", json={"email": "indexer_b@test.com", "password": "Password123!"})
    token_b = client.post("/auth/login", json={"email": "indexer_b@test.com", "password": "Password123!"}).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}", "X-API-Key": TEST_API_KEY}

    # Submit job as User A
    rag_service: RAGService = app.state.rag_service
    coordinator = rag_service.indexing_coordinator
    user_a_id = decode_access_token(token_a)["sub"]
    job = coordinator.submit_job(source="/dummy/repo", source_type="local", user_id=int(user_a_id))

    # User A can view the job status
    res_a = client.get(f"/repositories/index/status/{job.job_id}", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["job_id"] == job.job_id

    # User B attempts to view the job status -> 404
    res_b = client.get(f"/repositories/index/status/{job.job_id}", headers=headers_b)
    assert res_b.status_code == 404


# =============================================================================
# 8. FAIL-CLOSED AUTHENTICATION & EXPIRED TOKEN TESTS
# =============================================================================

def test_expired_token_returns_401(client):
    """Verify expired token returns 401 Unauthorized across protected endpoints."""
    from datetime import timedelta
    token = create_access_token(user_id=1, email="expired@test.com", expires_delta=timedelta(seconds=-10))
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}", "X-API-Key": TEST_API_KEY})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_unauthenticated_request_fails_closed(client):
    """Verify missing Bearer token fails closed with 401 on all user-owned endpoints."""
    headers = {"X-API-Key": TEST_API_KEY}  # Valid API key, but NO Bearer token
    assert client.get("/conversations", headers=headers).status_code == 401
    assert client.post("/conversations", json={"title": "Test"}, headers=headers).status_code == 401
    assert client.post("/repositories/index", json={"repository_path": "/tmp/dummy"}, headers=headers).status_code == 401
    assert client.get("/repositories/index/status/any-id", headers=headers).status_code == 401
    assert client.post("/query", json={"query": "test"}, headers=headers).status_code == 401


def test_cross_user_repository_access_isolation(client, test_db):
    """Verify User B cannot query or access a repository owned by User A."""
    from app.db.crud import create_or_update_repository
    # User A and User B registration & login
    client.post("/auth/register", json={"email": "owner_a@test.com", "password": "Password123!"})
    token_a = client.post("/auth/login", json={"email": "owner_a@test.com", "password": "Password123!"}).json()["access_token"]
    user_a_id = int(decode_access_token(token_a)["sub"])

    client.post("/auth/register", json={"email": "attacker_b@test.com", "password": "Password123!"})
    token_b = client.post("/auth/login", json={"email": "attacker_b@test.com", "password": "Password123!"}).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}", "X-API-Key": TEST_API_KEY}

    # Seed repository owned by User A in the test DB
    create_or_update_repository(
        test_db,
        name="private_repo_a",
        source="/tmp/private_repo_a",
        user_id=user_a_id,
        status="indexed",
    )

    # User B queries private_repo_a -> 404 Not Found (resource-safe, no leakage)
    res = client.post("/query", headers=headers_b, json={"query": "secret code", "repository_name": "private_repo_a"})
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_ownership_derived_from_token_not_payload(client):
    """Verify conversation ownership is strictly derived from authenticated token, ignoring spoofed user_id in payload."""
    client.post("/auth/register", json={"email": "victim@test.com", "password": "Password123!"})
    client.post("/auth/register", json={"email": "spoofer@test.com", "password": "Password123!"})
    token_spoofer = client.post("/auth/login", json={"email": "spoofer@test.com", "password": "Password123!"}).json()["access_token"]
    spoofer_headers = {"Authorization": f"Bearer {token_spoofer}", "X-API-Key": TEST_API_KEY}

    # Attempt to pass victim's user_id in payload (e.g. user_id: 1)
    res = client.post(
        "/conversations",
        headers=spoofer_headers,
        json={"title": "Spoofed Chat", "user_id": 1},
    )
    assert res.status_code == 201
    conv_id = res.json()["id"]

    # Verify conversation belongs to spoofer and appears in their list
    list_spoofer = client.get("/conversations", headers=spoofer_headers).json()
    assert any(c["id"] == conv_id for c in list_spoofer)

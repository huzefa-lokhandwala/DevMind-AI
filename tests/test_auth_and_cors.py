"""Unit and integration tests for API Authentication, CORS Middleware, and Security Configuration."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.main import app


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


from app.db.database import get_db


def test_health_endpoints_remain_publicly_accessible_without_api_key(client) -> None:
    """GET /health and GET /health/ready must remain accessible without X-API-Key header."""
    mock_db = MagicMock()
    mock_db.execute.return_value = None
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        with patch.dict(os.environ, {"DEVMIND_API_KEY": "secret_test_key_123", "DEVMIND_ENV": "production"}):
            res_health = client.get("/health")
            assert res_health.status_code == 200
            assert res_health.json()["status"] == "ok"

            res_ready = client.get("/health/ready")
            assert res_ready.status_code == 200
            assert res_ready.json()["status"] == "ready"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_protected_endpoint_without_api_key_returns_401(client) -> None:
    """POST /query without X-API-Key header returns 401 when DEVMIND_API_KEY is configured."""
    with patch.dict(os.environ, {"DEVMIND_API_KEY": "secret_test_key_123", "DEVMIND_ENV": "production"}):
        res = client.post("/query", json={"query": "Where is main?"})
        assert res.status_code == 401
        assert res.json()["detail"] == "Invalid or missing API key."


def test_protected_endpoint_with_incorrect_api_key_returns_401(client) -> None:
    """POST /query with wrong X-API-Key header returns 401."""
    with patch.dict(os.environ, {"DEVMIND_API_KEY": "secret_test_key_123", "DEVMIND_ENV": "production"}):
        res = client.post(
            "/query",
            headers={"X-API-Key": "wrong_key_xyz"},
            json={"query": "Where is main?"},
        )
        assert res.status_code == 401
        assert res.json()["detail"] == "Invalid or missing API key."


def test_protected_endpoint_with_correct_api_key_succeeds(client) -> None:
    """POST /query with correct X-API-Key header succeeds when authorized."""
    with patch.dict(os.environ, {"DEVMIND_API_KEY": "secret_test_key_123", "DEVMIND_ENV": "development"}):
        # Mock RAGService state
        mock_service = MagicMock()
        mock_service.is_indexed = True
        mock_service.query.return_value = {
            "answer": "Test answer",
            "sources": [],
            "provider": "gemini",
            "model": "gemini-3.6-flash",
            "latency_ms": 120.0,
        }
        app.state.rag_service = mock_service

        res = client.post(
            "/query",
            headers={"X-API-Key": "secret_test_key_123"},
            json={"query": "Where is main?"},
        )
        assert res.status_code == 200
        assert res.json()["answer"] == "Test answer"


def test_auth_failure_does_not_leak_api_key_secret(client) -> None:
    """Verify 401 error response does not expose the configured secret API key in response payload."""
    secret = "super_top_secret_key_999"
    with patch.dict(os.environ, {"DEVMIND_API_KEY": secret, "DEVMIND_ENV": "production"}):
        res = client.post("/query", headers={"X-API-Key": "bad_key"}, json={"query": "test"})
        assert res.status_code == 401
        assert secret not in res.text
        assert secret not in str(res.headers)


def test_production_env_without_api_key_fails_closed(client) -> None:
    """In production (DEVMIND_ENV=production) without DEVMIND_API_KEY set, request fails closed with 500."""
    with patch.dict(os.environ, {"DEVMIND_ENV": "production", "DEVMIND_API_KEY": ""}):
        res = client.post("/query", json={"query": "test"})
        assert res.status_code == 500
        assert res.json()["detail"] == "Server security misconfiguration."


def test_cors_options_preflight_for_configured_origin(client) -> None:
    """OPTIONS preflight request from configured origin returns valid Access-Control-Allow-Origin headers."""
    res = client.options(
        "/query",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-API-Key, Content-Type",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "X-API-Key" in res.headers.get("access-control-allow-headers", "")


def test_cors_disallowed_origin_does_not_receive_allow_header(client) -> None:
    """Request from disallowed origin does not return Access-Control-Allow-Origin matching the malicious origin."""
    res = client.options(
        "/query",
        headers={
            "Origin": "http://malicious-site.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.headers.get("access-control-allow-origin") != "http://malicious-site.com"

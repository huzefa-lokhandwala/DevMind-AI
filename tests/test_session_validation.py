"""Unit and integration tests for strict X-Session-ID validation."""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient

from app.api.main import app
from app.utils.session_validator import validate_optional_session_id, validate_session_id


def test_session_id_validator_valid_inputs():
    """Valid UUID and alphanumeric session IDs pass validation."""
    valid_uuid = str(uuid.uuid4())
    assert validate_session_id(valid_uuid) == valid_uuid
    assert validate_session_id("sess_12345-abc:99") == "sess_12345-abc:99"
    assert validate_session_id(None) == "anonymous-default-session"
    assert validate_session_id("") == "anonymous-default-session"

    assert validate_optional_session_id(valid_uuid) == valid_uuid
    assert validate_optional_session_id(None) is None
    assert validate_optional_session_id("") is None


def test_session_id_validator_oversized_rejected():
    """Session IDs longer than 128 characters raise HTTP 400 Bad Request."""
    oversized = "a" * 129
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc1:
        validate_session_id(oversized)
    assert exc1.value.status_code == 400
    assert "exceeds maximum limit" in exc1.value.detail

    with pytest.raises(HTTPException) as exc2:
        validate_optional_session_id(oversized)
    assert exc2.value.status_code == 400
    assert "exceeds maximum limit" in exc2.value.detail


def test_session_id_validator_malformed_chars_rejected():
    """Session IDs with illegal characters (quotes, spaces, symbols) raise HTTP 400."""
    import pytest
    from fastapi import HTTPException

    for bad in ["session with spaces", "session'--drop table", "sess<script>"]:
        with pytest.raises(HTTPException) as exc:
            validate_session_id(bad)
        assert exc.value.status_code == 400
        assert "must contain only alphanumeric" in exc.value.detail


def test_api_endpoints_reject_oversized_session_id():
    """FastAPI endpoints reject oversized X-Session-ID headers with HTTP 400."""
    client = TestClient(app)
    api_key = "dvm_sk_4f8c2a91e7b63d05c9a142f8e6d73b10c5f294a8d1e63b7f"
    oversized_id = "x" * 200

    # 1. GET /conversations
    res_conv = client.get(
        "/conversations",
        headers={"X-API-Key": api_key, "X-Session-ID": oversized_id},
    )
    assert res_conv.status_code == 400
    assert "exceeds maximum limit" in res_conv.json()["detail"]

    # 2. POST /query
    res_query = client.post(
        "/query",
        json={"query": "hi"},
        headers={"X-API-Key": api_key, "X-Session-ID": oversized_id},
    )
    assert res_query.status_code == 400
    assert "exceeds maximum limit" in res_query.json()["detail"]

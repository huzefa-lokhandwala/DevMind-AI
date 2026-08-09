"""Unit and integration tests for FastAPI backend endpoints."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.llm.gemini_provider import GeminiProvider


@pytest.fixture
def client() -> TestClient:
    """Create a TestClient with a mocked GeminiProvider and clean RAG state."""
    with TestClient(app) as test_client:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = (
            "The `login()` function is implemented in `auth.py` (lines 6-13). "
            "It handles user JWT authentication."
        )
        mock_response.usage_metadata.prompt_token_count = 120
        mock_response.usage_metadata.candidates_token_count = 25
        mock_response.usage_metadata.total_token_count = 145
        mock_response.candidates = [MagicMock(finish_reason="STOP")]
        mock_client.models.generate_content.return_value = mock_response

        # Reset runtime state between tests for test isolation
        service = test_client.app.state.rag_service
        service.vector_store = None
        service.retriever = None
        service.indexed_repository_name = None
        service.llm_provider = GeminiProvider(client=mock_client)

        yield test_client

        # Clean up after test
        service.vector_store = None
        service.retriever = None
        service.indexed_repository_name = None


def test_health_endpoint(client: TestClient) -> None:
    """Test GET /health returns 200 OK and expected service identifier."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "DevMind AI",
    }


def test_query_before_indexing(client: TestClient) -> None:
    """Test POST /query before repository indexing returns 400 Bad Request."""
    response = client.post(
        "/query",
        json={"query": "Where is login implemented?", "top_k": 5},
    )
    assert response.status_code == 400
    assert "No repository has been indexed yet" in response.json()["detail"]


def test_index_repository_invalid_path(client: TestClient) -> None:
    """Test POST /repositories/index with invalid path returns 400 Bad Request."""
    response = client.post(
        "/repositories/index",
        json={"repository_path": "non_existent_folder_xyz"},
    )
    assert response.status_code == 400
    assert "Repository path does not exist" in response.json()["detail"]


def test_index_repository_success(client: TestClient) -> None:
    """Test POST /repositories/index with sample_project returns 200 OK and stats."""
    response = client.post(
        "/repositories/index",
        json={"repository_path": "repositories/sample_project"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["repository"] == "sample_project"
    assert data["files_loaded"] == 2
    assert data["chunks_created"] == 2
    assert data["embeddings_created"] == 2
    assert data["status"] == "indexed"


@patch("app.loaders.github_loader.GitHubRepositoryLoader.clone_repository")
def test_index_repository_with_github_url_success(mock_clone: MagicMock, client: TestClient) -> None:
    """Test POST /repositories/index with valid github_url indexes cloned repository."""
    mock_clone.return_value = Path("repositories/sample_project").resolve()

    response = client.post(
        "/repositories/index",
        json={"github_url": "https://github.com/sample_user/sample_repo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["repository"] == "sample_project"
    assert data["files_loaded"] == 2
    assert data["chunks_created"] == 2
    assert data["embeddings_created"] == 2
    assert data["status"] == "indexed"
    mock_clone.assert_called_once_with("https://github.com/sample_user/sample_repo")


def test_index_repository_both_sources_returns_422(client: TestClient) -> None:
    """Test POST /repositories/index rejecting request containing both repository_path and github_url."""
    response = client.post(
        "/repositories/index",
        json={
            "repository_path": "repositories/sample_project",
            "github_url": "https://github.com/user/repo",
        },
    )
    assert response.status_code == 422


def test_index_repository_neither_source_returns_422(client: TestClient) -> None:
    """Test POST /repositories/index rejecting empty payload."""
    response = client.post("/repositories/index", json={})
    assert response.status_code == 422


def test_index_repository_invalid_github_url_returns_400(client: TestClient) -> None:
    """Test POST /repositories/index rejecting non-HTTPS or unsafe GitHub URLs with 400 Bad Request."""
    response = client.post(
        "/repositories/index",
        json={"github_url": "file:///etc/passwd"},
    )
    assert response.status_code == 400
    assert "Invalid URL scheme" in response.json()["detail"]


@patch("app.loaders.github_loader.GitHubRepositoryLoader.clone_repository")
def test_query_after_github_indexing_success(mock_clone: MagicMock, client: TestClient) -> None:
    """Test POST /query execution following GitHub repository indexing."""
    mock_clone.return_value = Path("repositories/sample_project").resolve()

    # Index via github_url
    index_res = client.post(
        "/repositories/index",
        json={"github_url": "https://github.com/sample_user/sample_repo"},
    )
    assert index_res.status_code == 200

    # Query codebase
    query_res = client.post(
        "/query",
        json={"query": "Where is login implemented?", "top_k": 5},
    )
    assert query_res.status_code == 200
    data = query_res.json()

    assert "login()" in data["answer"]
    assert data["provider"] == "gemini"
    assert data["model"] == "gemini-2.5-flash"
    assert len(data["sources"]) > 0


def test_query_after_indexing_success(client: TestClient) -> None:
    """Test POST /query after indexing returns answer and source citations."""
    index_res = client.post(
        "/repositories/index",
        json={"repository_path": "repositories/sample_project"},
    )
    assert index_res.status_code == 200

    query_res = client.post(
        "/query",
        json={"query": "Where is login implemented?", "top_k": 5},
    )
    assert query_res.status_code == 200
    data = query_res.json()

    assert "login()" in data["answer"]
    assert data["provider"] == "gemini"
    assert data["model"] == "gemini-2.5-flash"
    assert data["latency_ms"] >= 0.0

    sources = data["sources"]
    assert len(sources) > 0
    assert sources[0]["repository"] == "sample_project"


def test_query_empty_query(client: TestClient) -> None:
    """Test POST /query with blank query returns 422 Unprocessable Entity."""
    response = client.post(
        "/query",
        json={"query": "   ", "top_k": 5},
    )
    assert response.status_code == 422


def test_query_invalid_top_k(client: TestClient) -> None:
    """Test POST /query with top_k <= 0 returns 422 Unprocessable Entity."""
    res_zero = client.post(
        "/query",
        json={"query": "Where is login?", "top_k": 0},
    )
    assert res_zero.status_code == 422

    res_negative = client.post(
        "/query",
        json={"query": "Where is login?", "top_k": -5},
    )
    assert res_negative.status_code == 422


def test_gemini_failure(client: TestClient) -> None:
    """Test POST /query returns 502 Bad Gateway when LLM provider fails."""
    client.post(
        "/repositories/index",
        json={"repository_path": "repositories/sample_project"},
    )

    failing_client = MagicMock()
    failing_client.models.generate_content.side_effect = RuntimeError("API service offline")
    client.app.state.rag_service.llm_provider = GeminiProvider(client=failing_client)

    response = client.post(
        "/query",
        json={"query": "Where is login implemented?", "top_k": 5},
    )
    assert response.status_code == 502
    assert "LLM generation or search processing failed" in response.json()["detail"]

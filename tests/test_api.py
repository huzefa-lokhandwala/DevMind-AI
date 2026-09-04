import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.embeddings.embedding_engine import EmbeddingEngine
from app.llm.gemini_provider import GeminiProvider
from google.genai import types

TEST_API_KEY = "test_devmind_key_abc123"


@pytest.fixture
def client() -> TestClient:
    """Create a TestClient with mocked GeminiProvider, EmbeddingEngine, auth headers, and clean RAG state."""
    with patch.dict(os.environ, {"DEVMIND_API_KEY": TEST_API_KEY, "DEVMIND_ENV": "development"}):
        with TestClient(app, headers={"X-API-Key": TEST_API_KEY}) as test_client:
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

            def embed_side_effect(model: str, contents: str | list[str], config: types.EmbedContentConfig | None = None) -> types.EmbedContentResponse:
                dim = config.output_dimensionality if config and config.output_dimensionality else 768
                if isinstance(contents, str):
                    embeddings = [types.ContentEmbedding(values=[0.1] * dim)]
                else:
                    embeddings = [
                        types.ContentEmbedding(values=[0.1 * (i + 1)] * dim)
                        for i in range(len(contents))
                    ]
                return types.EmbedContentResponse(embeddings=embeddings)

            mock_client.models.embed_content.side_effect = embed_side_effect

            # Reset runtime state between tests for test isolation
            service = test_client.app.state.rag_service
            service.vector_store = None
            service.retriever = None
            service.indexed_repository_name = None
            service.embedding_engine = EmbeddingEngine(client=mock_client)
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


def test_health_ready_endpoint(client: TestClient) -> None:
    """Test GET /health/ready returns readiness status."""
    response = client.get("/health/ready")
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        assert response.json()["status"] == "ready"
        assert response.json()["database"] == "connected"



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
    assert data["model"] == GeminiProvider.DEFAULT_MODEL_NAME
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
    assert data["model"] == GeminiProvider.DEFAULT_MODEL_NAME
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


def test_index_repository_concurrent_lock_returns_409(client: TestClient) -> None:
    """Test POST /repositories/index returns 409 Conflict when another indexing operation is active."""
    service = client.app.state.rag_service
    # Simulate an active indexing lock
    acquired = service._indexing_lock.acquire(blocking=False)
    assert acquired is True
    try:
        response = client.post(
            "/repositories/index",
            json={"repository_path": "repositories/sample_project"},
        )
        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"]
    finally:
        service._indexing_lock.release()


def test_index_repository_skips_oversized_file(tmp_path: Path, client: TestClient) -> None:
    """Test repository loader skips files exceeding MAX_FILE_SIZE_BYTES limit."""
    repo_dir = tmp_path / "oversized_repo"
    repo_dir.mkdir()

    small_file = repo_dir / "valid.py"
    small_file.write_text("def hello(): return 'world'\n", encoding="utf-8")

    large_file = repo_dir / "giant.py"
    large_file.write_text("x = 1\n" * 100000, encoding="utf-8")  # ~600 KB

    with patch.dict(os.environ, {"MAX_FILE_SIZE_BYTES": "50000"}):  # 50 KB limit
        response = client.post(
            "/repositories/index",
            json={"repository_path": str(repo_dir)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["files_loaded"] == 1  # Only small_file loaded

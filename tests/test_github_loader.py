"""Unit tests for GitHubRepositoryLoader component."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.loaders.github_loader import GitHubLoaderError, GitHubRepositoryLoader


@pytest.fixture
def loader(tmp_path: Path) -> GitHubRepositoryLoader:
    """Create GitHubRepositoryLoader targeting a temporary directory."""
    return GitHubRepositoryLoader(base_storage_dir=tmp_path)


def test_validate_valid_github_urls(loader: GitHubRepositoryLoader) -> None:
    """Test URL parsing accepts valid public HTTPS GitHub repository URLs."""
    urls = [
        "https://github.com/torvalds/linux",
        "https://www.github.com/psf/requests.git",
        "https://github.com/fastapi/fastapi/tree/main",
    ]
    for url in urls:
        owner, repo, clone_url = loader.parse_and_validate_url(url)
        assert owner != ""
        assert repo != ""
        assert clone_url.startswith("https://github.com/")


def test_validate_invalid_github_urls(loader: GitHubRepositoryLoader) -> None:
    """Test URL parsing rejects malformed, non-HTTPS, or non-GitHub URLs."""
    invalid_urls = [
        "",
        "http://github.com/user/repo",
        "file:///etc/passwd",
        "git@github.com:user/repo.git",
        "https://evil.com/user/repo",
        "https://github.com/user/repo; rm -rf /",
        "https://127.0.0.1/user/repo",
        "https://localhost/user/repo",
    ]
    for url in invalid_urls:
        with pytest.raises(GitHubLoaderError):
            loader.parse_and_validate_url(url)


@patch("subprocess.run")
def test_clone_repository_success(mock_run: MagicMock, loader: GitHubRepositoryLoader) -> None:
    """Test successful git clone operation."""
    mock_run.return_value = MagicMock(returncode=0, stdout="Cloning...", stderr="")
    target_path = loader.clone_repository("https://github.com/sample_user/sample_repo")

    assert target_path.name == "sample_repo"
    assert target_path.parent.name == "sample_user"
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert kwargs.get("shell") is False
    assert "https://github.com/sample_user/sample_repo.git" in args[0]


@patch("subprocess.run")
def test_clone_repository_subprocess_error(mock_run: MagicMock, loader: GitHubRepositoryLoader) -> None:
    """Test CalledProcessError during git clone raises GitHubLoaderError."""
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=128, cmd="git clone", stderr="Repository not found"
    )
    with pytest.raises(GitHubLoaderError) as exc_info:
        loader.clone_repository("https://github.com/sample_user/non_existent_repo")

    assert "Repository not found" in str(exc_info.value)


@patch("subprocess.run")
def test_clone_repository_timeout(mock_run: MagicMock, loader: GitHubRepositoryLoader) -> None:
    """Test TimeoutExpired during git clone raises GitHubLoaderError."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="git clone", timeout=60)
    with pytest.raises(GitHubLoaderError) as exc_info:
        loader.clone_repository("https://github.com/sample_user/slow_repo")

    assert "timed out" in str(exc_info.value)


@patch("subprocess.run")
def test_clone_repository_git_not_installed(mock_run: MagicMock, loader: GitHubRepositoryLoader) -> None:
    """Test missing git binary raises GitHubLoaderError."""
    mock_run.side_effect = FileNotFoundError("No such file or directory: 'git'")
    with pytest.raises(GitHubLoaderError) as exc_info:
        loader.clone_repository("https://github.com/sample_user/sample_repo")

    assert "Git CLI executable is not installed" in str(exc_info.value)

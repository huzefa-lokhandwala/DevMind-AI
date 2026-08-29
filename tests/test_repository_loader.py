"""Tests for repository file loading."""

from pathlib import Path

import pytest

from app.loaders.repository_loader import RepositoryLoader
from app.models import Document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_REPO = PROJECT_ROOT / "repositories" / "sample_project"


def test_load_files_returns_sample_project_files() -> None:
    loader = RepositoryLoader(SAMPLE_REPO)
    documents = loader.load_files()

    assert len(documents) == 2
    assert all(isinstance(doc, Document) for doc in documents)

    file_names = {doc.file_name for doc in documents}
    assert file_names == {"auth.py", "README.md"}


def test_load_files_includes_content() -> None:
    loader = RepositoryLoader(SAMPLE_REPO)
    documents = loader.load_files()

    auth_file = next(doc for doc in documents if doc.file_name == "auth.py")
    assert "login" in auth_file.content
    assert auth_file.extension == ".py"
    assert auth_file.repository_name == "sample_project"


def test_init_raises_for_missing_repository() -> None:
    missing_path = PROJECT_ROOT / "repositories" / "does_not_exist"

    with pytest.raises(FileNotFoundError):
        RepositoryLoader(missing_path)


def test_load_files_ignores_lockfiles(tmp_path: Path) -> None:
    """Verify that lockfiles like package-lock.json and yarn.lock are excluded from loading."""
    repo_dir = tmp_path / "mock_repo"
    repo_dir.mkdir()
    (repo_dir / "index.ts").write_text("export const x = 1;")
    (repo_dir / "package-lock.json").write_text('{"name": "mock", "lockfileVersion": 3}')
    (repo_dir / "yarn.lock").write_text("# yarn lockfile v1")
    (repo_dir / "pnpm-lock.yaml").write_text("lockfileVersion: '6.0'")
    (repo_dir / "Cargo.lock").write_text("[[package]]\nname = 'mock'")

    loader = RepositoryLoader(repo_dir)
    documents = loader.load_files()

    file_names = {doc.file_name for doc in documents}
    assert "index.ts" in file_names
    assert "package-lock.json" not in file_names
    assert "yarn.lock" not in file_names
    assert "pnpm-lock.yaml" not in file_names
    assert "Cargo.lock" not in file_names

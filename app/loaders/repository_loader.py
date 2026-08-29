"""Load source files from a local repository for RAG indexing."""

from __future__ import annotations

import logging
from pathlib import Path

from app.models import Document

logger = logging.getLogger(__name__)


class RepositoryLoader:
    """Walk a repository and load supported text-based source files."""

    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
        {
            ".py",
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".java",
            ".cpp",
            ".c",
            ".html",
            ".css",
        }
    )

    IGNORE_FOLDERS: frozenset[str] = frozenset(
        {
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "dist",
            "build",
        }
    )

    IGNORE_FILES: frozenset[str] = frozenset(
        {
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "poetry.lock",
            "Cargo.lock",
            "composer.lock",
            "Gemfile.lock",
        }
    )

    def __init__(self, repository_path: str | Path) -> None:
        """Initialize the loader for a repository root directory.

        Args:
            repository_path: Path to the repository root.

        Raises:
            FileNotFoundError: If the repository path does not exist.
            NotADirectoryError: If the repository path is not a directory.
        """
        self.repository_path = Path(repository_path).resolve()

        if not self.repository_path.exists():
            raise FileNotFoundError(
                f"Repository path does not exist: {self.repository_path}"
            )
        if not self.repository_path.is_dir():
            raise NotADirectoryError(
                f"Repository path is not a directory: {self.repository_path}"
            )

        self.repository_name = self.repository_path.name

    def load_files(self) -> list[Document]:
        """Load all supported files from the repository.

        Returns:
            A list of Document instances containing file metadata and content.
        """
        documents: list[Document] = []

        for path in sorted(self.repository_path.rglob("*")):
            if not path.is_file():
                continue

            if self._should_ignore(path):
                continue

            if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("Skipping unreadable file %s: %s", path, exc)
                continue

            documents.append(
                Document(
                    content=content,
                    file_name=path.name,
                    file_path=str(path),
                    extension=path.suffix,
                    repository_name=self.repository_name,
                )
            )

        return documents

    def _should_ignore(self, path: Path) -> bool:
        """Return True when a file lives inside an ignored directory or is an ignored lockfile."""
        if path.name in self.IGNORE_FILES:
            return True
        return any(part in self.IGNORE_FOLDERS for part in path.parts)

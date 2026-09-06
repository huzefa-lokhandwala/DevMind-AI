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
            ".next",
            ".turbo",
            "coverage",
            ".pytest_cache",
            ".mypy_cache",
            ".idea",
            ".vscode",
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

    DEFAULT_MAX_FILE_SIZE_BYTES: int = 512 * 1024  # 512 KB

    def __init__(
        self, repository_path: str | Path, max_file_size_bytes: int | None = None
    ) -> None:
        """Initialize the loader for a repository root directory.

        Args:
            repository_path: Path to the repository root.
            max_file_size_bytes: Optional maximum allowed file size in bytes.
                Defaults to MAX_FILE_SIZE_BYTES env var or 512 KB.

        Raises:
            FileNotFoundError: If the repository path does not exist.
            NotADirectoryError: If the repository path is not a directory.
        """
        import os
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

        env_max = os.getenv("MAX_FILE_SIZE_BYTES")
        parsed_max = self.DEFAULT_MAX_FILE_SIZE_BYTES
        if env_max:
            try:
                m = int(env_max.strip())
                if m > 0:
                    parsed_max = m
            except (ValueError, TypeError):
                pass
        self.max_file_size_bytes = max_file_size_bytes or parsed_max

    def iter_file_paths(self) -> list[Path]:
        """Discover and return all eligible, non-ignored source file paths without loading contents.

        Uses directory pruning via os.walk so ignored directories (.git, node_modules, etc.)
        are never traversed into, dramatically speeding up repository traversal.

        Returns:
            Sorted list of eligible file Path objects.
        """
        import os
        eligible: list[Path] = []
        repo_root = str(self.repository_path)

        for root, dirs, files in os.walk(repo_root, followlinks=False):
            # In-place directory pruning prevents os.walk from recursing into ignored trees
            dirs[:] = [d for d in dirs if d not in self.IGNORE_FOLDERS]

            for fname in files:
                if fname in self.IGNORE_FILES:
                    continue

                ext = os.path.splitext(fname)[1].lower()
                if ext not in self.SUPPORTED_EXTENSIONS:
                    continue

                file_path = Path(root) / fname
                if file_path.is_symlink():
                    try:
                        resolved_path = file_path.resolve()
                        if not resolved_path.is_relative_to(self.repository_path):
                            logger.warning("Skipping symlink pointing outside repository root: %s", file_path)
                            continue
                    except (OSError, RuntimeError, ValueError):
                        continue

                eligible.append(file_path)

        return sorted(eligible)

    def iter_batches(
        self, batch_size: int = 5, paths: list[Path] | None = None
    ):
        """Yield bounded batches of Document objects loaded from repository files.

        Args:
            batch_size: Number of files to load and yield per batch (default: 5).
            paths: Optional pre-discovered list of Path objects to avoid redundant directory walks.

        Yields:
            List of Document objects representing a single processing batch.
        """
        file_paths = paths if paths is not None else self.iter_file_paths()
        for i in range(0, len(file_paths), max(1, batch_size)):
            batch_paths = file_paths[i : i + max(1, batch_size)]
            batch_documents: list[Document] = []

            for path in batch_paths:
                try:
                    file_size = path.stat().st_size
                    if file_size > self.max_file_size_bytes:
                        logger.warning(
                            "Skipping oversized file %s (size=%d bytes > limit=%d bytes)",
                            path,
                            file_size,
                            self.max_file_size_bytes,
                        )
                        continue

                    content = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    logger.warning("Skipping unreadable file %s: %s", path, exc)
                    continue

                batch_documents.append(
                    Document(
                        content=content,
                        file_name=path.name,
                        file_path=str(path),
                        extension=path.suffix,
                        repository_name=self.repository_name,
                    )
                )

            if batch_documents:
                yield batch_documents

    def load_files(self) -> list[Document]:
        """Load all supported files from the repository.

        Returns:
            A list of Document instances containing file metadata and content.
        """
        documents: list[Document] = []
        for batch in self.iter_batches(batch_size=5):
            documents.extend(batch)
        return documents

    def _should_ignore(self, path: Path) -> bool:
        """Return True when a file lives inside an ignored directory or is an ignored lockfile."""
        if path.name in self.IGNORE_FILES:
            return True
        return any(part in self.IGNORE_FOLDERS for part in path.parts)

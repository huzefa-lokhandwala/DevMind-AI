"""GitHub repository loader for DevMind AI."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GitHubLoaderError(Exception):
    """Raised when GitHub URL validation or clone operations fail."""


class GitHubRepositoryLoader:
    """Safely validate, clone, and manage public GitHub repositories for RAG indexing."""

    GITHUB_URL_PATTERN = re.compile(
        r"^https://(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?(?:/.*)?$"
    )

    def __init__(self, base_storage_dir: Path | str | None = None) -> None:
        """Initialize GitHubRepositoryLoader with a target storage directory for cloned repos.

        Args:
            base_storage_dir: Optional base directory to store cloned repositories.
                Defaults to ``data/cloned_repos`` relative to current working directory.
        """
        self.base_storage_dir = Path(base_storage_dir or "data/cloned_repos").resolve()

    def parse_and_validate_url(self, github_url: str) -> tuple[str, str, str]:
        """Validate and parse a GitHub URL for security.

        Args:
            github_url: User-provided GitHub repository URL string.

        Returns:
            Tuple of (owner, repo_name, sanitized_clone_url).

        Raises:
            GitHubLoaderError: If URL format is invalid, uses non-HTTPS scheme, or contains malicious payloads.
        """
        if not github_url or not isinstance(github_url, str):
            raise GitHubLoaderError("GitHub URL must be a non-empty string.")

        clean_url = github_url.strip()
        parsed = urlparse(clean_url)

        if parsed.scheme != "https":
            raise GitHubLoaderError(
                "Invalid URL scheme. Only public HTTPS GitHub URLs ('https://github.com/...') are allowed."
            )

        if parsed.netloc.lower() not in ("github.com", "www.github.com"):
            raise GitHubLoaderError(
                "Invalid domain. Only 'github.com' repository URLs are supported."
            )

        match = self.GITHUB_URL_PATTERN.match(clean_url)
        if not match:
            raise GitHubLoaderError(
                "Invalid GitHub repository URL format. Expected format: 'https://github.com/owner/repository'."
            )

        owner, repo_name = match.group(1), match.group(2)

        # Disallow path traversal or invalid characters in owner/repo names
        if ".." in owner or ".." in repo_name or "/" in owner or "/" in repo_name:
            raise GitHubLoaderError("Invalid characters detected in repository name or owner.")

        sanitized_clone_url = f"https://github.com/{owner}/{repo_name}.git"
        return owner, repo_name, sanitized_clone_url

    def clone_repository(self, github_url: str, timeout_seconds: int = 60) -> Path:
        """Clone a public GitHub repository safely into local storage.

        Args:
            github_url: Validated GitHub repository URL string.
            timeout_seconds: Maximum allowed clone duration before timing out.

        Returns:
            Resolved local ``Path`` directory containing the cloned repository files.

        Raises:
            GitHubLoaderError: If URL is invalid, git command fails, or clone times out.
        """
        owner, repo_name, sanitized_clone_url = self.parse_and_validate_url(github_url)

        target_dir = self.base_storage_dir / owner / repo_name
        logger.info("Cloning GitHub repo '%s/%s' into '%s'", owner, repo_name, target_dir)

        # Reuse existing clone if repository directory already exists and is non-empty
        if target_dir.exists() and any(target_dir.iterdir()):
            logger.info("Repository '%s/%s' already cached at '%s'. Reusing existing files.", owner, repo_name, target_dir)
            return target_dir

        target_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            sanitized_clone_url,
            str(target_dir),
        ]

        try:
            logger.info("Executing git clone command: %s", " ".join(cmd))
            result = subprocess.run(
                cmd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=True,
            )
            logger.info("Successfully cloned '%s/%s' into '%s'", owner, repo_name, target_dir)
        except subprocess.TimeoutExpired as exc:
            logger.error("Git clone timed out after %d seconds for URL: %s", timeout_seconds, github_url)
            raise GitHubLoaderError(
                f"Git clone operation timed out after {timeout_seconds} seconds."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr_msg = exc.stderr.strip() if exc.stderr else str(exc)
            logger.error("Git clone failed for URL '%s': %s", github_url, stderr_msg)
            raise GitHubLoaderError(f"Failed to clone GitHub repository: {stderr_msg}") from exc
        except FileNotFoundError as exc:
            logger.error("Git CLI executable not found on PATH: %s", exc)
            raise GitHubLoaderError(
                "Git CLI executable is not installed or available on PATH."
            ) from exc

        return target_dir

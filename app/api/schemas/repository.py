"""Pydantic schemas for repository indexing endpoint."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class IndexRepositoryRequest(BaseModel):
    """Payload for POST /repositories/index."""

    repository_path: Optional[str] = Field(
        default=None,
        description="Relative or absolute path to local repository directory.",
        examples=["repositories/sample_project"],
    )
    github_url: Optional[str] = Field(
        default=None,
        description="Public HTTPS GitHub repository URL.",
        examples=["https://github.com/username/repository"],
    )

    @model_validator(mode="after")
    def validate_exactly_one_source(self) -> IndexRepositoryRequest:
        """Ensure either repository_path or github_url is provided, but not both."""
        has_path = bool(self.repository_path and self.repository_path.strip())
        has_url = bool(self.github_url and self.github_url.strip())

        if not has_path and not has_url:
            raise ValueError("Either 'repository_path' or 'github_url' must be provided.")
        if has_path and has_url:
            raise ValueError("Provide either 'repository_path' or 'github_url', not both.")

        return self


class IndexRepositoryResponse(BaseModel):
    """Response payload for POST /repositories/index."""

    repository: str
    files_loaded: int
    chunks_created: int
    embeddings_created: int
    status: str
    job_id: Optional[str] = None
    queue_position: Optional[int] = 0


class JobStatusResponse(BaseModel):
    """Response payload for GET /repositories/index/status/{job_id}."""

    job_id: str
    repository_source: str
    source_type: str
    status: str  # "QUEUED", "RUNNING", "COMPLETED", "FAILED"
    queue_position: int = 0
    result: Optional[IndexRepositoryResponse] = None
    error: Optional[str] = None
    created_at: float
    updated_at: float

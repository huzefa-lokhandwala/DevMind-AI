"""Health check endpoint for DevMind AI API."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    """Return system health and service identification status."""
    return {
        "status": "ok",
        "service": "DevMind AI",
    }

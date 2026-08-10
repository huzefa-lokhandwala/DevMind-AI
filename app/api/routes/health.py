"""Health check and readiness endpoints for DevMind AI API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    """Return system health and service identification status."""
    return {
        "status": "ok",
        "service": "DevMind AI",
    }


@router.get("/health/ready")
def get_readiness(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Check system readiness including database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
            "service": "DevMind AI",
        }
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "database": "disconnected",
                "error": str(exc),
            },
        )

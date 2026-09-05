"""Session ID validation utility for DevMind AI API boundaries."""

from __future__ import annotations

import re
from typing import Optional
from fastapi import Header, HTTPException, status

MAX_SESSION_ID_LENGTH = 128
_SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-:]+$")


def validate_session_id(
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-ID"),
) -> str:
    """Validate and extract X-Session-ID header with strict boundary checks.

    Falls back to 'anonymous-default-session' if omitted.
    Raises HTTP 400 if oversized or contains invalid characters.
    """
    if not x_session_id or not x_session_id.strip():
        return "anonymous-default-session"

    clean = x_session_id.strip()
    if len(clean) > MAX_SESSION_ID_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid X-Session-ID header: length {len(clean)} exceeds maximum limit of {MAX_SESSION_ID_LENGTH} characters.",
        )

    if not _SESSION_ID_PATTERN.match(clean):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Session-ID header: must contain only alphanumeric characters, hyphens, underscores, or colons.",
        )

    return clean


def validate_optional_session_id(
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-ID"),
) -> Optional[str]:
    """Validate optional X-Session-ID header for query endpoints."""
    if not x_session_id or not x_session_id.strip():
        return None

    clean = x_session_id.strip()
    if len(clean) > MAX_SESSION_ID_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid X-Session-ID header: length {len(clean)} exceeds maximum limit of {MAX_SESSION_ID_LENGTH} characters.",
        )

    if not _SESSION_ID_PATTERN.match(clean):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Session-ID header: must contain only alphanumeric characters, hyphens, underscores, or colons.",
        )

    return clean

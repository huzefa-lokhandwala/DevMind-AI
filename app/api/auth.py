"""API Key Authentication security dependency for DevMind AI."""

from __future__ import annotations

import hmac
import logging

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from app.utils.config import get_devmind_api_key, get_devmind_env

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(
    x_api_key: str | None = Security(api_key_header),
) -> str | None:
    """FastAPI security dependency validating X-API-Key header.

    Args:
        x_api_key: Value extracted from X-API-Key request header.

    Returns:
        The validated API key string if authorized.

    Raises:
        HTTPException(401): If key is missing or invalid.
        HTTPException(500): If running in production without DEVMIND_API_KEY set (fail closed).
    """
    configured_key = get_devmind_api_key()
    env = get_devmind_env()

    if configured_key:
        if not x_api_key:
            logger.warning("Unauthenticated request attempt (missing X-API-Key header)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key.",
            )
        if not hmac.compare_digest(x_api_key, configured_key):
            logger.warning("Unauthorized request attempt (invalid X-API-Key header)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key.",
            )
        return x_api_key

    # If DEVMIND_API_KEY is not configured:
    if env == "production":
        logger.error("Production server configuration error: DEVMIND_API_KEY is not set.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server security misconfiguration.",
        )

    # In development or testing environment without DEVMIND_API_KEY set, permit requests for local backwards compatibility
    logger.debug("DEVMIND_API_KEY unconfigured in '%s' environment; bypassing authentication.", env)
    return x_api_key

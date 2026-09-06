"""Authentication security dependencies for DevMind AI.

Supports:
1. real user authentication with JWT Bearer tokens (Argon2id + PyJWT)
2. legacy API Key validation (X-API-Key) for backward compatibility
"""

from __future__ import annotations

import hmac
import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session

from app.db import crud
from app.db.database import get_db
from app.db.models import UserModel
from app.utils.config import get_devmind_api_key, get_devmind_env
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    x_api_key: str | None = Security(api_key_header),
) -> str | None:
    """FastAPI security dependency validating Bearer JWT or legacy X-API-Key header.

    Allows real end-user JWT Bearer authentication while preserving backward-compatible
    X-API-Key machine authentication.
    """
    if credentials and credentials.credentials:
        return "bearer-authenticated"

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


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserModel:
    """FastAPI dependency resolving the authenticated backend user.

    Validates the Bearer JWT access token, checks user existence in the database,
    and ensures the account is active.

    Authentication fails closed unconditionally: missing, invalid, or expired tokens
    always raise 401 Unauthorized across all environments.

    Returns:
        Active authenticated UserModel instance.

    Raises:
        HTTPException(401): If token is missing, invalid, expired, or user is not active.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    payload = decode_access_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: missing subject identity.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: invalid subject identity.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = crud.get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_strict_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserModel:
    """Strict alias for get_current_user (both fail closed with 401)."""
    return get_current_user(credentials=credentials, db=db)

"""Security utilities for Argon2id password hashing and JWT token operations."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import HTTPException, status

from app.utils.config import (
    get_jwt_access_token_expire_minutes,
    get_jwt_algorithm,
    get_jwt_secret,
)

logger = logging.getLogger(__name__)

# Configure Argon2id password hasher with production-appropriate parameters
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=1,
    hash_len=32,
)

MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id.

    Args:
        password: Plaintext password to hash.

    Returns:
        Argon2id encoded hash string.

    Raises:
        ValueError: If password is empty or shorter than MIN_PASSWORD_LENGTH.
    """
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash using constant-time comparison.

    Args:
        plain_password: Plaintext password supplied by user.
        hashed_password: Stored Argon2id hash from database.

    Returns:
        True if password matches, False otherwise.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception as exc:
        logger.warning("Unexpected error during password verification: %s", type(exc).__name__)
        return False


def create_access_token(
    user_id: int,
    email: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Create a signed JWT access token for an authenticated user.

    Args:
        user_id: Primary key of authenticated user.
        email: User email address.
        expires_delta: Optional custom expiration timedelta.
        extra_claims: Optional dictionary of additional claims.

    Returns:
        Encoded JWT token string.
    """
    now = datetime.now(timezone.utc)
    lifetime = expires_delta or timedelta(minutes=get_jwt_access_token_expire_minutes())
    expire = now + lifetime

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email.strip().lower(),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, get_jwt_secret(), algorithm=get_jwt_algorithm())
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a signed JWT access token.

    Args:
        token: Raw JWT token string.

    Returns:
        Decoded payload dictionary.

    Raises:
        HTTPException(401): If token is expired, malformed, or invalid.
    """
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[get_jwt_algorithm()],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as exc:
        logger.warning("Token verification failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload

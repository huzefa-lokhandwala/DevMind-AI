"""Centralized application configuration settings for DevMind AI."""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


def get_devmind_env() -> str:
    """Return application environment ('development', 'testing', or 'production')."""
    return os.getenv("DEVMIND_ENV", "development").strip().lower()


def get_devmind_api_key() -> str | None:
    """Return configured API key string or None if unconfigured."""
    key = os.getenv("DEVMIND_API_KEY", "").strip()
    return key if key else None


def get_cors_origins() -> list[str]:
    """Return parsed CORS origins as a list of strings."""
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    if not raw or not raw.strip():
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    if get_devmind_env() == "production":
        if "*" in origins:
            raise ValueError("Wildcard CORS origins ('*') are strictly prohibited in production.")
    return origins


INSECURE_DEV_SECRETS = {
    "devmind-insecure-jwt-secret-for-dev-only-change-in-production",
    "secret",
    "changeme",
    "password",
    "jwt-secret",
    "123456",
}


def get_jwt_secret() -> str:
    """Return JWT signing secret from environment or safe dev default.

    In production, fails closed if JWT secret is missing, insecure, or shorter than 32 characters.
    """
    secret = (
        os.getenv("JWT_SECRET")
        or os.getenv("JWT_SECRET_KEY")
        or os.getenv("DEVMIND_JWT_SECRET")
        or os.getenv("SECRET_KEY")
    )
    env = get_devmind_env()

    if secret and secret.strip():
        val = secret.strip()
        if env == "production":
            if val.lower() in INSECURE_DEV_SECRETS or len(val) < 32:
                raise ValueError(
                    "JWT_SECRET is insecure for production. A cryptographically strong secret of at least 32 characters is required."
                )
        return val

    if env == "production":
        raise ValueError("JWT_SECRET must be configured in production environment.")

    return "devmind-insecure-jwt-secret-for-dev-only-change-in-production"


def get_jwt_algorithm() -> str:
    """Return JWT signing algorithm (default: HS256)."""
    return os.getenv("JWT_ALGORITHM", "HS256").strip()


def get_jwt_access_token_expire_minutes() -> int:
    """Return JWT access token lifetime in minutes (default: 60)."""
    raw = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60").strip()
    try:
        val = int(raw)
        return val if val > 0 else 60
    except (ValueError, TypeError):
        return 60

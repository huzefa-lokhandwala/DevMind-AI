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
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    if not raw or not raw.strip():
        return ["http://localhost:3000"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]

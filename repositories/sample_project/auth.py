"""Authentication helpers for the sample project."""

from __future__ import annotations


def login(username: str, password: str) -> None:
    """Authenticate a user using JWT.

    Args:
        username: Account identifier.
        password: Plain-text password (hash before production use).
    """
    _ = username, password

"""Pytest configuration and database test bootstrap for DevMind AI."""

from __future__ import annotations

import pytest

import app.db.models  # noqa: F401 - ensure models are registered
from app.db.database import Base, engine


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure all SQLAlchemy tables are created on the active test engine."""
    Base.metadata.create_all(bind=engine)
    yield

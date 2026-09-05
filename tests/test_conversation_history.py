"""Unit and isolation tests for session-scoped conversation history persistence."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import crud
from app.db.database import Base
from app.utils.title_generator import generate_conversation_title


@pytest.fixture
def in_memory_db():
    """Create a temporary in-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_title_generator_deterministic():
    """Verify deterministic derived titles from various query styles."""
    assert generate_conversation_title("where is authentication implemented?") == "Authentication Implemented"
    assert generate_conversation_title("What is SORTTracker?") == "SORTTracker"
    assert generate_conversation_title("how does this project handle embeddings?") == "Handle Embeddings"
    assert generate_conversation_title("what is dependency injection?") == "Dependency Injection"
    assert generate_conversation_title("hi") == "General Query"
    assert generate_conversation_title("") == "New Chat"


def test_conversation_crud_and_messages(in_memory_db):
    """Verify creating conversation, appending messages, and querying history."""
    session_id = "test-session-123"

    # Create conversation
    conv = crud.create_conversation(
        in_memory_db,
        session_id=session_id,
        title="Authentication Discussion",
        repository_name="proofos",
    )
    assert conv.id is not None
    assert conv.title == "Authentication Discussion"
    assert conv.session_id == session_id

    # Add user message
    msg1 = crud.add_message(
        in_memory_db,
        conversation_id=conv.id,
        role="user",
        content="Where is auth implemented?",
        intent="REPOSITORY",
    )
    assert msg1.id is not None
    assert msg1.role == "user"

    # Add assistant message with sources
    sample_sources = [
        {"file": "auth.py", "file_path": "app/auth.py", "score": 0.95}
    ]
    msg2 = crud.add_message(
        in_memory_db,
        conversation_id=conv.id,
        role="assistant",
        content="Auth is in `app/auth.py`.",
        intent="REPOSITORY",
        sources=sample_sources,
        provider="gemini",
        model="gemini-3.6-flash",
        latency_ms=105.2,
    )
    assert msg2.id is not None
    assert msg2.role == "assistant"
    assert "auth.py" in msg2.sources_json

    # Retrieve conversation with messages
    fetched = crud.get_conversation(in_memory_db, conversation_id=conv.id, session_id=session_id)
    assert fetched is not None
    assert len(fetched.messages) == 2
    assert fetched.messages[0].content == "Where is auth implemented?"
    assert fetched.messages[1].content == "Auth is in `app/auth.py`."


def test_session_isolation_prevents_cross_user_leakage(in_memory_db):
    """Session A must NEVER be able to read or delete Session B's conversations."""
    session_a = "session-alice"
    session_b = "session-bob"

    # Alice creates a conversation
    conv_alice = crud.create_conversation(
        in_memory_db,
        session_id=session_a,
        title="Alice Private Code Discussion",
    )
    crud.add_message(
        in_memory_db,
        conversation_id=conv_alice.id,
        role="user",
        content="Confidential API query",
    )

    # Bob lists conversations -> Should NOT see Alice's conversation
    bob_list = crud.list_conversations(in_memory_db, session_id=session_b)
    assert len(bob_list) == 0

    # Bob tries to fetch Alice's conversation ID directly -> Should return None
    bob_direct_fetch = crud.get_conversation(
        in_memory_db, conversation_id=conv_alice.id, session_id=session_b
    )
    assert bob_direct_fetch is None

    # Bob tries to delete Alice's conversation -> Should fail and not delete
    bob_delete_attempt = crud.delete_conversation(
        in_memory_db, conversation_id=conv_alice.id, session_id=session_b
    )
    assert bob_delete_attempt is False

    # Alice's conversation still intact
    alice_check = crud.get_conversation(
        in_memory_db, conversation_id=conv_alice.id, session_id=session_a
    )
    assert alice_check is not None
    assert alice_check.title == "Alice Private Code Discussion"

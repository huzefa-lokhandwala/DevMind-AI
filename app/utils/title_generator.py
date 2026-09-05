"""Deterministic title generator for conversation history in DevMind AI."""

from __future__ import annotations

import re


def generate_conversation_title(query: str, max_length: int = 40) -> str:
    """Derive a clean, concise, human-readable title from the initial user query.

    Avoids calling external LLMs and handles punctuation, leading question markers,
    and capitalization deterministically.

    Examples:
        - "Where is authentication implemented?" -> "Authentication Implemented"
        - "What is SORTTracker?" -> "SORTTracker"
        - "How does this project handle embeddings?" -> "Handle Embeddings"
        - "what is dependency injection?" -> "Dependency Injection"
        - "hi" -> "General Query"

    Args:
        query: First user query in conversation.
        max_length: Maximum character length for derived title.

    Returns:
        Formatted title string.
    """
    clean = query.strip()
    if not clean:
        return "New Chat"

    # Remove leading question prefixes
    stripped = re.sub(
        r"^(where\s+(is|are|can\s+i\s+find)|what\s+(is|are|does)|how\s+(does|do|can|to)|which\s+(file|function|class)|explain\s+(the|this)?|tell\s+me\s+about|show\s+me|find\s+(the)?)\s+",
        "",
        clean,
        flags=re.IGNORECASE,
    ).strip()

    # Remove repository phrases like "this project", "this repo", "in this codebase"
    stripped = re.sub(
        r"\b(in\s+)?(this|the|our)\s+(repo|repository|codebase|project)\b",
        "",
        stripped,
        flags=re.IGNORECASE,
    ).strip()

    # Remove trailing question marks and punctuation
    stripped = re.sub(r"[\?\!\.\:\,\;]+$", "", stripped).strip()

    # Clean multi-spaces
    stripped = re.sub(r"\s+", " ", stripped).strip()

    if not stripped or stripped.lower() in ("hi", "hello", "hey", "hola", "howdy", "heya", "greetings"):
        return "General Query"

    # Title case if all lowercase
    if stripped.islower():
        words = stripped.split()
        capitalized = [w.capitalize() if len(w) > 2 or idx == 0 else w for idx, w in enumerate(words)]
        stripped = " ".join(capitalized)

    # Truncate cleanly on word boundary if needed
    if len(stripped) > max_length:
        truncated = stripped[:max_length].rsplit(" ", 1)[0]
        return truncated if truncated else stripped[:max_length]

    return stripped

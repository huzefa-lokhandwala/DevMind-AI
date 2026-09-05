"""Deterministic query intent classification for DevMind AI.

Classifies incoming user queries into GENERAL, REPOSITORY, or MIXED intents
without invoking external LLM models to preserve speed and avoid token overhead.
"""

from __future__ import annotations

import re
from enum import Enum


class QueryIntent(str, Enum):
    """Classification of query intent."""

    GENERAL = "GENERAL"
    REPOSITORY = "REPOSITORY"
    MIXED = "MIXED"


# Pure conversational greetings and general phrases
_GREETING_PATTERNS = [
    r"^(hi|hello|hey|heyy|heya|howdy|greetings|hola|sup)\b",
    r"^good\s+(morning|afternoon|evening|day)\b",
    r"^how\s+are\s+you(\s+doing)?\b",
    r"^who\s+are\s+you\b",
    r"^what\s+can\s+you\s+do\b",
    r"^help(\s+me)?\b",
    r"^tell\s+me\s+a\s+joke\b",
    r"^what\s+is\s+the\s+weather\b",
    r"^thanks?(\s+you)?\b",
    r"^bye|goodbye|see\s+you\b",
]

# Repository contextual anchors
_REPO_CONTEXT_PHRASES = [
    r"\b(this|the|our)\s+(repo|repository|codebase|project|app|application|workspace|system)\b",
    r"\bin\s+(this|the|our)\s+(repo|repository|codebase|project|app|code)\b",
    r"\b(used|implemented|defined|located|handled|written|configured|called)\s+(here|in\s+here|in\s+this\s+project|in\s+this\s+repo)\b",
    r"\bwhere\s+(is|are|can\s+i\s+find)\b",
    r"\bwhich\s+(file|files|function|functions|class|classes|module|modules|endpoint|endpoints|route|routes)\b",
    r"\bwhat\s+(file|files)\s+(implement|defines?|contains?|handles?)\b",
    r"\bexplain\s+(this|the)\s+(codebase|repository|repo|project|architecture)\b",
    r"\barchitecture\s+of\s+this\s+(repository|repo|codebase|project)\b",
    r"\bhow\s+does\s+this\s+(project|repo|codebase|repository|app)\b",
    r"\b(find|search)\s+(for\s+)?(the\s+)?(function|class|method|route|file|symbol)\b",
]

# Mixed query indicators (asking both general conceptual explanation + codebase-specific usage)
_MIXED_CONJUNCTION_PATTERNS = [
    r"\band\s+(how|where|which)\s+([a-z0-9_\-\s]{1,40}?)\s*(is|are|does|do|can|used|implemented|defined|located)\b",
    r"\band\s+tell\s+me\s+how\s+(this\s+project|this\s+repo|we)\b",
    r"\band\s+where\s+(is\s+)?([a-z0-9_\-\s]{1,40}?)\s*(is\s+)?(used|implemented|defined|located)\b",
    r"\bgenerally\s+and\s+(tell\s+me|how|where)\b",
    r"\bhow\s+(this\s+repository|this\s+project|this\s+app|we)\s+(generates?|handles?|uses?|implements?)\b",
]


def classify_intent(query: str) -> QueryIntent:
    """Deterministically classify user query intent.

    Args:
        query: Raw query text from user.

    Returns:
        QueryIntent enum value: GENERAL, REPOSITORY, or MIXED.
    """
    clean_query = query.strip()
    if not clean_query:
        return QueryIntent.GENERAL

    lowered = clean_query.lower()

    # 1. Check for pure greetings and small talk
    for pattern in _GREETING_PATTERNS:
        if re.search(pattern, lowered):
            # If greeting also explicitly mentions repository context, let repo logic handle it
            if not any(re.search(rp, lowered) for rp in _REPO_CONTEXT_PHRASES):
                return QueryIntent.GENERAL

    # 2. Check for MIXED intent (General definition + codebase implementation)
    has_mixed_conjunction = any(re.search(p, lowered) for p in _MIXED_CONJUNCTION_PATTERNS)
    has_repo_context = any(re.search(p, lowered) for p in _REPO_CONTEXT_PHRASES)

    if has_mixed_conjunction and has_repo_context:
        return QueryIntent.MIXED

    # 3. Check for REPOSITORY intent
    if has_repo_context:
        return QueryIntent.REPOSITORY

    # Check for file extension mentions or code symbol indicators (e.g. "auth.py", ".tsx", "main.py")
    if re.search(r"\b[\w\-\.]+\.(py|ts|tsx|js|jsx|json|yaml|yml|md|sql|html|css|rs|go|java|cpp|c|h)\b", lowered):
        return QueryIntent.REPOSITORY

    # 4. Short / Ambiguous queries (e.g. "DI", "auth", "python", "fastapi")
    # Default to GENERAL to avoid penalizing users with irrelevant repository retrieval
    words = lowered.split()
    if len(words) <= 2:
        return QueryIntent.GENERAL

    # 5. General technical concepts / definitions (e.g. "what is dependency injection", "explain REST API")
    if re.search(r"^(what\s+is|what\s+are|explain|how\s+does|why\s+use|tell\s+me\s+about)\b", lowered):
        # We already verified no repository context phrases matched above
        return QueryIntent.GENERAL

    # Default fallback: If query has no repository anchors, treat as GENERAL
    return QueryIntent.GENERAL

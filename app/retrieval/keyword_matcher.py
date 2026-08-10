"""Lexical keyword and code symbol matching component for hybrid retrieval."""

from __future__ import annotations

import re
from typing import Sequence

from app.models import Document

# Lightweight stop words set to prevent common query terms from diluting match quality
STOP_WORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "where",
        "is", "are", "was", "were", "be", "been", "being", "how", "what", "which",
        "who", "does", "do", "did", "code", "file", "project", "implement", "implemented",
        "work", "works", "show", "me", "get", "find", "defined", "definition",
        "function", "functions", "method", "methods", "class", "classes",
    }
)


class KeywordMatcher:
    """Provides lightweight lexical content and symbol matching for code retrieval."""

    TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")

    def tokenize(self, text: str) -> set[str]:
        """Extract unique lowercased alphanumeric tokens from text string.

        Args:
            text: Raw input string (query or document content).

        Returns:
            Set of cleaned, non-stopword tokens of length >= 2.
        """
        if not text:
            return set()

        raw_tokens = self.TOKEN_PATTERN.findall(text.lower())
        return {
            tok for tok in raw_tokens
            if len(tok) >= 2 and tok not in STOP_WORDS
        }

    def compute_lexical_score(self, query_tokens: set[str], content_tokens: set[str]) -> float:
        """Compute normalized term overlap ratio between query tokens and document content tokens.

        Args:
            query_tokens: Token set extracted from user query.
            content_tokens: Token set extracted from document content.

        Returns:
            Float overlap ratio between 0.0 and 1.0.
        """
        if not query_tokens or not content_tokens:
            return 0.0

        matches = query_tokens.intersection(content_tokens)
        return len(matches) / len(query_tokens)

    def detect_symbol_match(self, query_tokens: set[str], document: Document) -> float:
        """Check if query tokens match function names, class names, file names, or directory paths.

        Args:
            query_tokens: Token set extracted from user query.
            document: Document instance containing symbol metadata.

        Returns:
            1.0 if a direct code symbol or path match is detected, otherwise 0.0.
        """
        if not query_tokens:
            return 0.0

        symbol_names: set[str] = set()
        if document.function_name:
            symbol_names.add(document.function_name.lower())
        if document.class_name:
            symbol_names.add(document.class_name.lower())
        if document.file_name:
            # Strip file extension
            stem = document.file_name.rsplit(".", 1)[0].lower()
            symbol_names.add(stem)
            for part in re.findall(r"[a-zA-Z0-9_]+", stem):
                if len(part) >= 2:
                    symbol_names.add(part.lower())

        if document.file_path:
            path_parts = re.findall(r"[a-zA-Z0-9_]+", document.file_path.lower())
            for part in path_parts:
                if len(part) >= 2 and part not in STOP_WORDS:
                    symbol_names.add(part)

        for token in query_tokens:
            for symbol in symbol_names:
                if token == symbol or token in symbol or symbol in token:
                    return 1.0

        return 0.0

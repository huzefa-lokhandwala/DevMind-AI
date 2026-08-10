"""Query Intent Classifier for DevMind AI.

Classifies natural language questions to adjust retrieval strategy
and graph expansion rules.
"""

from __future__ import annotations

from enum import Enum


class QueryIntent(str, Enum):
    """Categorized query intent types."""

    FILE_LOCATION = "FILE_LOCATION"
    SYMBOL_LOCATION = "SYMBOL_LOCATION"
    FUNCTION_BEHAVIOR = "FUNCTION_BEHAVIOR"
    API_ROUTE = "API_ROUTE"
    DATABASE_MODEL = "DATABASE_MODEL"
    CALL_GRAPH = "CALL_GRAPH"
    EXECUTION_FLOW = "EXECUTION_FLOW"
    ARCHITECTURE = "ARCHITECTURE"
    GENERAL_CODE_SEARCH = "GENERAL_CODE_SEARCH"


class QueryClassifier:
    """Classifies natural language codebase queries."""

    @staticmethod
    def classify(query: str) -> QueryIntent:
        """Classify incoming query string into a QueryIntent enum."""
        q_lower = query.lower().strip()

        if any(kw in q_lower for kw in ["trace", "flow", "end to end", "execution path", "pipeline flow", "step by step"]):
            return QueryIntent.EXECUTION_FLOW

        if any(kw in q_lower for kw in ["call graph", "calls", "invokes", "call tree", "dependencies"]):
            return QueryIntent.CALL_GRAPH

        if any(kw in q_lower for kw in ["prisma", "schema", "model", "database model", "tables"]):
            return QueryIntent.DATABASE_MODEL

        if any(kw in q_lower for kw in ["api", "route", "endpoint", "post /", "get /", "handler"]):
            return QueryIntent.API_ROUTE

        if any(kw in q_lower for kw in ["where is", "implemented", "definition of", "class ", "function "]):
            return QueryIntent.SYMBOL_LOCATION

        if any(kw in q_lower for kw in ["how does", "what does", "explain", "calculate"]):
            return QueryIntent.FUNCTION_BEHAVIOR

        if any(kw in q_lower for kw in ["architecture", "overview", "system design"]):
            return QueryIntent.ARCHITECTURE

        return QueryIntent.GENERAL_CODE_SEARCH

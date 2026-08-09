"""Evaluation dataset models and sample test benchmark for RAG quality."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvaluationCase:
    """Structured evaluation test case representing a developer query and ground truth matches."""

    query: str
    expected_files: list[str] = field(default_factory=list)
    expected_symbols: list[str] = field(default_factory=list)


def get_sample_evaluation_dataset() -> list[EvaluationCase]:
    """Return standardized evaluation benchmark cases for sample_project."""
    return [
        EvaluationCase(
            query="Where is the login function defined?",
            expected_files=["auth.py"],
            expected_symbols=["login"],
        ),
        EvaluationCase(
            query="Which module handles user authentication?",
            expected_files=["auth.py"],
            expected_symbols=["login"],
        ),
        EvaluationCase(
            query="What framework does this project use?",
            expected_files=["README.md"],
            expected_symbols=[],
        ),
        EvaluationCase(
            query="Where is JWT user authentication mentioned?",
            expected_files=["auth.py", "README.md"],
            expected_symbols=["login"],
        ),
        EvaluationCase(
            query="Show me the auth module",
            expected_files=["auth.py"],
            expected_symbols=["login"],
        ),
    ]

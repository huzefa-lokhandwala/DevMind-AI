"""Unit tests for the ContextAssembler module."""

from __future__ import annotations

from app.models import Document, SearchResult
from app.prompts.context_assembler import ContextAssembler, PromptContext


def _make_search_result(
    rank: int,
    score: float,
    content: str,
    *,
    file_name: str = "auth.py",
    function_name: str | None = "login",
    start_line: int = 1,
    end_line: int = 10,
) -> SearchResult:
    doc = Document(
        content=content,
        file_name=file_name,
        file_path=f"/tmp/{file_name}",
        extension=".py",
        repository_name="sample_project",
        chunk_type="function",
        function_name=function_name,
        start_line=start_line,
        end_line=end_line,
    )
    return SearchResult(rank=rank, score=score, document=doc)


def test_assemble_basic_context() -> None:
    res1 = _make_search_result(1, 0.95, "def login(): pass", function_name="login")
    res2 = _make_search_result(2, 0.75, "def logout(): pass", function_name="logout", start_line=12, end_line=18)

    assembler = ContextAssembler()
    prompt_ctx = assembler.assemble("How does auth work?", [res1, res2])

    assert isinstance(prompt_ctx, PromptContext)
    assert prompt_ctx.user_question == "How does auth work?"
    assert "login" in prompt_ctx.retrieved_context
    assert "logout" in prompt_ctx.retrieved_context
    assert len(prompt_ctx.citations) == 2
    assert prompt_ctx.citations[0]["function_name"] == "login"
    assert prompt_ctx.citations[1]["function_name"] == "logout"


def test_assemble_preserves_ranking() -> None:
    res1 = _make_search_result(1, 0.90, "first_func()", function_name="first_func")
    res2 = _make_search_result(2, 0.80, "second_func()", function_name="second_func")

    assembler = ContextAssembler()
    prompt_ctx = assembler.assemble("test query", [res1, res2])

    first_index = prompt_ctx.retrieved_context.find("first_func")
    second_index = prompt_ctx.retrieved_context.find("second_func")
    assert first_index < second_index
    assert prompt_ctx.citations[0]["rank"] == 1
    assert prompt_ctx.citations[1]["rank"] == 2


def test_assemble_deduplicates_chunks() -> None:
    res1 = _make_search_result(1, 0.90, "def login(): pass", function_name="login", start_line=1, end_line=10)
    res2 = _make_search_result(2, 0.89, "def login(): pass", function_name="login", start_line=1, end_line=10)

    assembler = ContextAssembler()
    prompt_ctx = assembler.assemble("login details", [res1, res2])

    assert len(prompt_ctx.citations) == 1
    assert prompt_ctx.retrieved_context.count("def login(): pass") == 1


def test_assemble_truncation_on_max_chars() -> None:
    res1 = _make_search_result(1, 0.90, "def alpha(): pass", function_name="alpha")
    res2 = _make_search_result(2, 0.80, "def beta(): pass", function_name="beta")

    assembler = ContextAssembler()
    # Set max_chars small enough to only fit chunk 1 header and content
    prompt_ctx = assembler.assemble("test query", [res1, res2], max_chars=140)

    assert "alpha" in prompt_ctx.retrieved_context
    assert "beta" not in prompt_ctx.retrieved_context
    assert len(prompt_ctx.citations) == 1


def test_assemble_empty_results() -> None:
    assembler = ContextAssembler()
    prompt_ctx = assembler.assemble("unknown query", [])

    assert prompt_ctx.retrieved_context == "No relevant code context found."
    assert prompt_ctx.citations == []

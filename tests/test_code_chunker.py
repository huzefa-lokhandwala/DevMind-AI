"""Tests for the code-aware chunking engine."""

from app.chunking.code_chunker import CodeChunker
from app.models import Document

SAMPLE_REPO = "sample_project"


def _make_document(
    content: str,
    *,
    file_name: str = "module.py",
    extension: str = ".py",
) -> Document:
    return Document(
        content=content,
        file_name=file_name,
        file_path=f"/tmp/{file_name}",
        extension=extension,
        repository_name=SAMPLE_REPO,
    )


def test_chunk_documents_splits_python_functions() -> None:
    content = (
        "def alpha():\n"
        "    return 1\n"
        "\n"
        "def beta():\n"
        "    return 2\n"
    )
    chunker = CodeChunker()
    chunks = chunker.chunk_documents([_make_document(content)])

    function_names = {chunk.function_name for chunk in chunks}
    assert function_names == {"alpha", "beta"}
    assert all(chunk.chunk_type == "function" for chunk in chunks)
    assert all(chunk.language == "python" for chunk in chunks)


def test_chunk_documents_splits_classes_and_methods() -> None:
    content = (
        "class AuthService:\n"
        "    def login(self, username: str) -> bool:\n"
        "        return True\n"
        "\n"
        "    async def refresh(self) -> None:\n"
        "        pass\n"
    )
    chunker = CodeChunker()
    chunks = chunker.chunk_documents([_make_document(content)])

    class_chunks = [chunk for chunk in chunks if chunk.chunk_type == "class"]
    function_chunks = [chunk for chunk in chunks if chunk.chunk_type == "function"]

    assert len(class_chunks) == 1
    assert class_chunks[0].class_name == "AuthService"
    assert {chunk.function_name for chunk in function_chunks} == {"login", "refresh"}
    assert all(chunk.class_name == "AuthService" for chunk in function_chunks)


def test_chunk_documents_sets_line_numbers() -> None:
    content = "def alpha():\n    return 1\n"
    chunker = CodeChunker()
    chunks = chunker.chunk_documents([_make_document(content)])

    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 2
    assert "return 1" in chunks[0].content


def test_chunk_documents_preserves_repository_metadata() -> None:
    content = "def alpha():\n    pass\n"
    document = _make_document(content, file_name="auth.py")
    chunker = CodeChunker()
    chunks = chunker.chunk_documents([document])

    chunk = chunks[0]
    assert chunk.repository_name == SAMPLE_REPO
    assert chunk.file_name == "auth.py"
    assert chunk.file_path == "/tmp/auth.py"


def test_chunk_documents_returns_whole_file_on_parse_failure() -> None:
    content = "def broken(\n"
    chunker = CodeChunker()
    chunks = chunker.chunk_documents([_make_document(content)])

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "file"
    assert chunks[0].content == content
    assert chunks[0].language == "python"


def test_chunk_documents_passes_through_non_python_files() -> None:
    document = _make_document(
        "# Sample Project\n",
        file_name="README.md",
        extension=".md",
    )
    chunker = CodeChunker()
    chunks = chunker.chunk_documents([document])

    assert len(chunks) == 1
    assert chunks[0] is document
    assert chunks[0].chunk_type is None


def test_chunk_documents_on_sample_auth_file() -> None:
    """Integration-style check against the bundled sample repository file."""
    from pathlib import Path

    auth_path = (
        Path(__file__).resolve().parents[1]
        / "repositories"
        / "sample_project"
        / "auth.py"
    )
    content = auth_path.read_text(encoding="utf-8")
    document = Document(
        content=content,
        file_name=auth_path.name,
        file_path=str(auth_path),
        extension=".py",
        repository_name="sample_project",
    )

    chunker = CodeChunker()
    chunks = chunker.chunk_documents([document])

    login_chunk = next(chunk for chunk in chunks if chunk.function_name == "login")
    assert login_chunk.chunk_type == "function"
    assert "JWT" in login_chunk.content

"""Code-aware document chunking for DevMind AI."""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from typing import Literal

from app.models import Document

logger = logging.getLogger(__name__)

ChunkType = Literal["function", "class", "file"]


@dataclass(frozen=True)
class _Symbol:
    """Internal representation of a parsed Python symbol."""

    chunk_type: ChunkType
    function_name: str | None
    class_name: str | None
    start_line: int
    end_line: int


class _PythonSymbolVisitor(ast.NodeVisitor):
    """Collect function, async function, and class definitions from an AST."""

    def __init__(self) -> None:
        self.symbols: list[_Symbol] = []
        self._class_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        end_line = node.end_lineno or node.lineno
        self.symbols.append(
            _Symbol(
                chunk_type="class",
                function_name=None,
                class_name=node.name,
                start_line=node.lineno,
                end_line=end_line,
            )
        )

        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function(node)
        self.generic_visit(node)

    def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        end_line = node.end_lineno or node.lineno
        enclosing_class = self._class_stack[-1] if self._class_stack else None

        self.symbols.append(
            _Symbol(
                chunk_type="function",
                function_name=node.name,
                class_name=enclosing_class,
                start_line=node.lineno,
                end_line=end_line,
            )
        )


class CodeChunker:
    """Split loaded documents into code-aware chunks using Python AST parsing."""

    PYTHON_EXTENSION = ".py"
    PYTHON_LANGUAGE = "python"

    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        """Convert loaded documents into smaller, code-aware chunks.

        Python files are parsed with ``ast`` to produce one chunk per function,
        async function, or class. Non-Python documents are returned unchanged.
        If Python parsing fails, the entire file is returned as a single chunk.

        Args:
            documents: Documents produced by the repository loader.

        Returns:
            A flat list of chunked (or pass-through) documents.
        """
        chunks: list[Document] = []

        for document in documents:
            if document.extension.lower() == self.PYTHON_EXTENSION:
                chunks.extend(self._chunk_python_document(document))
            else:
                chunks.append(document)

        return chunks

    def _chunk_python_document(self, document: Document) -> list[Document]:
        """Chunk a single Python document by top-level and nested symbols."""
        try:
            tree = ast.parse(document.content)
        except SyntaxError as exc:
            logger.warning(
                "Failed to parse %s; using whole-file chunk: %s",
                document.file_path,
                exc,
            )
            return [self._whole_file_chunk(document)]

        visitor = _PythonSymbolVisitor()
        visitor.visit(tree)

        if not visitor.symbols:
            return [self._whole_file_chunk(document)]

        return [
            self._symbol_to_document(document, symbol)
            for symbol in visitor.symbols
        ]

    def _whole_file_chunk(self, document: Document) -> Document:
        """Return the document as a single fallback chunk."""
        return Document(
            content=document.content,
            file_name=document.file_name,
            file_path=document.file_path,
            extension=document.extension,
            repository_name=document.repository_name,
            language=self.PYTHON_LANGUAGE,
            chunk_type="file",
            function_name=None,
            class_name=None,
            start_line=1,
            end_line=len(document.content.splitlines()) or 1,
        )

    def _symbol_to_document(
        self,
        source: Document,
        symbol: _Symbol,
    ) -> Document:
        """Build a chunk document from a parsed symbol."""
        lines = source.content.splitlines()
        start_index = max(symbol.start_line - 1, 0)
        end_index = min(symbol.end_line, len(lines))
        chunk_content = "\n".join(lines[start_index:end_index])

        return Document(
            content=chunk_content,
            file_name=source.file_name,
            file_path=source.file_path,
            extension=source.extension,
            repository_name=source.repository_name,
            language=self.PYTHON_LANGUAGE,
            chunk_type=symbol.chunk_type,
            function_name=symbol.function_name,
            class_name=symbol.class_name,
            start_line=symbol.start_line,
            end_line=symbol.end_line,
        )

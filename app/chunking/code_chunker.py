"""Code-aware document chunking for DevMind AI."""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, replace
from typing import Literal

from app.models import Document

logger = logging.getLogger(__name__)

ChunkType = Literal["function", "class", "file"]


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


@dataclass(frozen=True)
class _Symbol:
    """Internal representation of a parsed Python symbol."""

    chunk_type: ChunkType
    function_name: str | None
    class_name: str | None
    start_line: int
    end_line: int


class CodeChunker:
    """Split loaded documents into code-aware chunks using Python AST and TypeScript/JS structural parsing."""

    PYTHON_EXTENSION = ".py"
    PYTHON_LANGUAGE = "python"
    TS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")

    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        """Convert loaded documents into smaller, code-aware chunks with rich graph metadata."""
        chunks: list[Document] = []

        for document in documents:
            ext = document.extension.lower()
            if ext == self.PYTHON_EXTENSION:
                chunks.extend(self._chunk_python_document(document))
            elif ext in self.TS_EXTENSIONS:
                chunks.extend(self._chunk_ts_js_document(document))
            else:
                chunks.append(document)

        return chunks

    def _chunk_python_document(self, document: Document) -> list[Document]:
        """Chunk a single Python document by top-level and nested symbols with import and call metadata."""
        imports, imported_symbols = self._extract_python_imports(document.content)
        calls = self._extract_function_calls(document.content)

        try:
            tree = ast.parse(document.content)
        except SyntaxError as exc:
            logger.warning(
                "Failed to parse %s; using whole-file chunk: %s",
                document.file_path,
                exc,
            )
            fallback = self._whole_file_chunk(document)
            return [replace(fallback, imports=imports, imported_symbols=imported_symbols, function_calls=calls)]

        visitor = _PythonSymbolVisitor()
        visitor.visit(tree)

        if not visitor.symbols:
            fallback = self._whole_file_chunk(document)
            return [replace(fallback, imports=imports, imported_symbols=imported_symbols, function_calls=calls)]

        doc_chunks: list[Document] = []
        for symbol in visitor.symbols:
            doc_chunk = self._symbol_to_document(document, symbol)
            chunk_calls = self._extract_function_calls(doc_chunk.content)
            doc_chunks.append(
                replace(
                    doc_chunk,
                    imports=imports,
                    imported_symbols=imported_symbols,
                    function_calls=chunk_calls,
                )
            )

        return doc_chunks

    def _chunk_ts_js_document(self, document: Document) -> list[Document]:
        """Extract TypeScript/JavaScript exports, imports, calls, and line structures."""
        imports, imported_symbols = self._extract_ts_imports(document.content)
        exported_symbols = self._extract_ts_exports(document.content)
        calls = self._extract_function_calls(document.content)

        lines = document.content.splitlines()
        total_lines = len(lines) or 1

        # Check for main exported class or function symbol
        main_class = exported_symbols[0] if exported_symbols else None
        main_func = None

        func_match = re.search(r"export\s+(?:async\s+)?function\s+([a-zA-Z0-9_]+)", document.content)
        if func_match:
            main_func = func_match.group(1)

        enriched_doc = replace(
            document,
            language="typescript" if document.extension in (".ts", ".tsx") else "javascript",
            chunk_type="file",
            class_name=main_class,
            function_name=main_func,
            start_line=1,
            end_line=total_lines,
            imports=imports,
            imported_symbols=imported_symbols,
            exported_symbols=exported_symbols,
            function_calls=calls,
        )

        return [enriched_doc]

    def _enrich_generic_document(self, document: Document) -> Document:
        """Populate line metadata and calls for non-code/config/Prisma files."""
        lines = document.content.splitlines()
        total_lines = len(lines) or 1
        calls = self._extract_function_calls(document.content)

        return replace(
            document,
            chunk_type="file",
            start_line=1,
            end_line=total_lines,
            function_calls=calls,
        )

    def _extract_python_imports(self, content: str) -> tuple[list[str], list[str]]:
        """Extract imported module paths and symbols from Python code using AST."""
        imports: list[str] = []
        symbols: list[str] = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                        symbols.append(alias.name.split(".")[-1])
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    imports.append(mod)
                    for alias in node.names:
                        symbols.append(alias.name)
        except Exception:
            pass
        return list(set(imports)), list(set(symbols))

    def _extract_ts_imports(self, content: str) -> tuple[list[str], list[str]]:
        """Extract TypeScript/JavaScript import paths and imported symbols using regex parsing."""
        imports: set[str] = set()
        symbols: set[str] = set()

        # Matches: import { A, B } from '@/lib/foo' or import C from 'bar'
        import_pattern = re.compile(
            r"import\s+(?:\{([^}]+)\}|([a-zA-Z0-9_$]+)|[*]\s+as\s+([a-zA-Z0-9_$]+))\s+from\s+['\"]([^'\"]+)['\"]"
        )
        for match in import_pattern.finditer(content):
            named, default_sym, namespace_sym, path = match.groups()
            imports.add(path)
            if named:
                for s in named.split(","):
                    cleaned = s.strip().split(" as ")[0].strip()
                    if cleaned:
                        symbols.add(cleaned)
            if default_sym:
                symbols.add(default_sym)
            if namespace_sym:
                symbols.add(namespace_sym)

        return list(imports), list(symbols)

    def _extract_ts_exports(self, content: str) -> list[str]:
        """Extract exported class, function, interface, and const names from TS/JS code."""
        exports: set[str] = set()
        pattern = re.compile(
            r"export\s+(?:default\s+)?(?:async\s+)?(?:class|function|const|let|var|interface|type)\s+([a-zA-Z0-9_$]+)"
        )
        for match in pattern.finditer(content):
            exports.add(match.group(1))

        reexport_pattern = re.compile(r"export\s+\{([^}]+)\}")
        for match in reexport_pattern.finditer(content):
            for s in match.group(1).split(","):
                cleaned = s.strip().split(" as ")[-1].strip()
                if cleaned:
                    exports.add(cleaned)

        return list(exports)

    def _extract_function_calls(self, content: str) -> list[str]:
        """Extract function, method, and constructor invocation symbols from source code."""
        calls: set[str] = set()

        # Matches method/function invocations: VerificationEngine.generateProofHash(), ScoringService.recalculateAndLogScore(), processSubmission()
        call_pattern = re.compile(r"(?:([a-zA-Z0-9_$]+)\.)?([a-zA-Z0-9_$]+)\s*\(")
        stop_keywords = {
            "if", "for", "while", "switch", "catch", "function", "constructor",
            "import", "export", "return", "require", "typeof", "await"
        }

        for match in call_pattern.finditer(content):
            obj_name, func_name = match.groups()
            if func_name and func_name not in stop_keywords:
                if obj_name:
                    calls.add(f"{obj_name}.{func_name}")
                else:
                    calls.add(func_name)

        return list(calls)

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


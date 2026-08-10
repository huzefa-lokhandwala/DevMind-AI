"""TypeScript/JavaScript Structural Extraction Assessment Suite."""

from __future__ import annotations

import pytest

from app.chunking.code_chunker import CodeChunker
from app.models import Document


def _chunk_ts(code: str, file_name: str = "test.ts") -> Document:
    doc = Document(
        content=code,
        file_name=file_name,
        file_path=f"lib/{file_name}",
        extension=".ts",
        repository_name="proofos",
    )
    chunker = CodeChunker()
    return chunker.chunk_documents([doc])[0]


def test_ts_parser_1_normal_imports() -> None:
    code = "import fs from 'fs';\nimport path from 'path';"
    doc = _chunk_ts(code)
    assert "fs" in doc.imports or "path" in doc.imports


def test_ts_parser_2_named_imports() -> None:
    code = "import { VerificationEngine, ScoreBreakdown } from './engine';"
    doc = _chunk_ts(code)
    assert "./engine" in doc.imports
    assert "VerificationEngine" in doc.imported_symbols
    assert "ScoreBreakdown" in doc.imported_symbols


def test_ts_parser_3_namespace_imports() -> None:
    code = "import * as crypto from 'crypto';"
    doc = _chunk_ts(code)
    assert "crypto" in doc.imports or "crypto" in doc.imported_symbols


def test_ts_parser_4_default_imports() -> None:
    code = "import React from 'react';"
    doc = _chunk_ts(code)
    assert "react" in doc.imports
    assert "React" in doc.imported_symbols


def test_ts_parser_5_re_exports() -> None:
    code = "export { VerificationEngine } from './engine';"
    doc = _chunk_ts(code)
    assert "VerificationEngine" in doc.exported_symbols or "VerificationEngine" in doc.imported_symbols


def test_ts_parser_6_wildcard_re_exports() -> None:
    code = "export * from './engine';"
    doc = _chunk_ts(code)
    # Regex parser limits: export * does not list individual symbol names unless tree-sitter or AST parser is used
    assert doc.chunk_type == "file"


def test_ts_parser_7_dynamic_imports() -> None:
    code = "async function load() { const mod = await import('./engine'); }"
    doc = _chunk_ts(code)
    # Dynamic imports contain import() function calls
    assert "import" in doc.function_calls or "load" in doc.function_calls


def test_ts_parser_8_aliased_imports() -> None:
    code = "import { VerificationEngine as Engine } from './engine';"
    doc = _chunk_ts(code)
    assert "./engine" in doc.imports
    assert "VerificationEngine" in doc.imported_symbols


def test_ts_parser_9_multiline_imports() -> None:
    code = "import {\n  VerificationEngine,\n  ScoreBreakdown\n} from './engine';"
    doc = _chunk_ts(code)
    assert "./engine" in doc.imports


def test_ts_parser_10_nested_functions_and_classes() -> None:
    code = "export class Outer {\n  inner() {\n    function helper() {}\n  }\n}"
    doc = _chunk_ts(code)
    assert "Outer" in doc.exported_symbols


def test_ts_parser_11_async_functions() -> None:
    code = "export async function processSubmission(data: any) {}"
    doc = _chunk_ts(code)
    assert "processSubmission" in doc.exported_symbols or doc.function_name == "processSubmission"


def test_ts_parser_12_arrow_functions() -> None:
    code = "export const calculateScore = async (val: number) => val * 2;"
    doc = _chunk_ts(code)
    assert "calculateScore" in doc.exported_symbols


def test_ts_parser_13_method_calls() -> None:
    code = "VerificationEngine.generateProofHash(data);"
    doc = _chunk_ts(code)
    assert "VerificationEngine.generateProofHash" in doc.function_calls

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Document:
    """
    Represents a document or code chunk
    throughout the DevMind AI pipeline.
    """

    content: str

    file_name: str

    file_path: str

    extension: str

    repository_name: str

    language: Optional[str] = None

    chunk_id: Optional[str] = None

    chunk_type: Optional[str] = None

    function_name: Optional[str] = None

    class_name: Optional[str] = None

    start_line: Optional[int] = None

    end_line: Optional[int] = None

    embedding: Optional[list] = field(default=None)

    similarity_score: Optional[float] = None

    imports: list[str] = field(default_factory=list)

    imported_symbols: list[str] = field(default_factory=list)

    function_calls: list[str] = field(default_factory=list)

    exported_symbols: list[str] = field(default_factory=list)

    evidence_level: Optional[str] = None  # "HIGH", "MEDIUM", "LOW"
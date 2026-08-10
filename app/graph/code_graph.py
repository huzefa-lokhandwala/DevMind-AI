"""Lightweight AST-based Code Graph component for DevMind AI.

Represents files, classes, functions, routes, and Prisma models as nodes,
and imports, definitions, and calls as directed edges.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal

from app.models import Document

logger = logging.getLogger(__name__)

NodeType = Literal["FILE", "CLASS", "FUNCTION", "METHOD", "API_ROUTE", "PRISMA_MODEL"]
EdgeType = Literal[
    "IMPORTS", "DEFINES", "CALLS", "EXTENDS", "USES", "ROUTE_CALLS", "QUERIES_MODEL", "WRITES_MODEL"
]


@dataclass
class CodeNode:
    """Represents a code entity (file, symbol, route) in the graph."""

    id: str
    name: str
    type: NodeType
    file_path: str
    start_line: int | None = None
    end_line: int | None = None


@dataclass
class CodeEdge:
    """Represents a structural relationship between code entities."""

    source_id: str
    target_id: str
    type: EdgeType


class CodeGraph:
    """Builds and queries an AST/symbol-grounded dependency graph."""

    def __init__(self) -> None:
        self.nodes: dict[str, CodeNode] = {}
        self.edges: list[CodeEdge] = []
        self._symbol_to_file: dict[str, str] = {}
        self._adjacency: dict[str, set[str]] = {}

    def add_node(self, node: CodeNode) -> None:
        """Register a node in the graph."""
        self.nodes[node.id] = node
        if node.file_path not in self._adjacency:
            self._adjacency[node.file_path] = set()

    def add_edge(self, edge: CodeEdge) -> None:
        """Register a directed edge between nodes."""
        self.edges.append(edge)
        source_path = self.nodes[edge.source_id].file_path if edge.source_id in self.nodes else edge.source_id
        target_path = self.nodes[edge.target_id].file_path if edge.target_id in self.nodes else edge.target_id

        if source_path in self.nodes and target_path in self.nodes:
            self._adjacency.setdefault(source_path, set()).add(target_path)
            self._adjacency.setdefault(target_path, set()).add(source_path)

    def build_from_documents(self, documents: list[Document]) -> None:
        """Populate nodes and edges from parsed document metadata."""
        self.nodes.clear()
        self.edges.clear()
        self._symbol_to_file.clear()
        self._adjacency.clear()

        # Step 1: Register all File and Symbol Nodes
        for doc in documents:
            file_id = doc.file_path
            node_type: NodeType = "API_ROUTE" if "/route." in doc.file_path else ("PRISMA_MODEL" if doc.file_path.endswith(".prisma") else "FILE")

            file_node = CodeNode(
                id=file_id,
                name=doc.file_name,
                type=node_type,
                file_path=doc.file_path,
                start_line=doc.start_line,
                end_line=doc.end_line,
            )
            self.add_node(file_node)

            # Map exported symbols to file path
            for exp in getattr(doc, "exported_symbols", []):
                self._symbol_to_file[exp] = doc.file_path
                sym_id = f"{doc.file_path}::{exp}"
                self.add_node(
                    CodeNode(
                        id=sym_id,
                        name=exp,
                        type="CLASS" if exp[0].isupper() else "FUNCTION",
                        file_path=doc.file_path,
                        start_line=doc.start_line,
                        end_line=doc.end_line,
                    )
                )
                self.add_edge(CodeEdge(source_id=file_id, target_id=sym_id, type="DEFINES"))

            if doc.class_name:
                self._symbol_to_file[doc.class_name] = doc.file_path
            if doc.function_name:
                self._symbol_to_file[doc.function_name] = doc.file_path

        # Step 2: Register Import and Call Edges
        for doc in documents:
            file_id = doc.file_path

            # Add import connections
            for imp_sym in getattr(doc, "imported_symbols", []):
                if imp_sym in self._symbol_to_file:
                    target_file = self._symbol_to_file[imp_sym]
                    if target_file != file_id:
                        self.add_edge(
                            CodeEdge(source_id=file_id, target_id=target_file, type="IMPORTS")
                        )

            # Add function/symbol call connections
            for call in getattr(doc, "function_calls", []):
                parts = call.split(".")
                for part in parts:
                    if part in self._symbol_to_file:
                        target_file = self._symbol_to_file[part]
                        if target_file != file_id:
                            edge_type: EdgeType = (
                                "ROUTE_CALLS" if "/route." in file_id else "CALLS"
                            )
                            self.add_edge(
                                CodeEdge(source_id=file_id, target_id=target_file, type=edge_type)
                            )

        logger.info(
            "Built CodeGraph with %d nodes and %d edges across %d files",
            len(self.nodes),
            len(self.edges),
            len(self._adjacency),
        )

    def get_connected_nodes(self, start_path: str, max_depth: int = 2) -> list[str]:
        """BFS traversal to retrieve graph-connected file paths up to max_depth."""
        if start_path not in self._adjacency:
            return []

        visited: set[str] = {start_path}
        queue: list[tuple[str, int]] = [(start_path, 0)]
        connected: list[str] = []

        while queue:
            curr_path, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for neighbor in self._adjacency.get(curr_path, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    connected.append(neighbor)
                    queue.append((neighbor, depth + 1))

        return connected

    def find_entry_routes() -> list[str]:
        """Return file paths for API route handlers."""
        return [node.file_path for node in self.nodes.values() if node.type == "API_ROUTE"]

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Final, Protocol
from urllib.parse import quote, unquote

from contextor.core.domain.lineage_facts import (
    ExtractedAnchorFact,
    ExtractedFlowFact,
    ExtractedSurfaceFact,
    SourceSpan,
)

_LOCAL_ID_VERSION: Final[str] = "v1"
_ANCHOR_KINDS: Final[frozenset[str]] = frozenset({"module", "class", "function", "async_function", "lambda", "comprehension", "parameter", "binding", "import_binding", "global_declaration", "nonlocal_declaration"})
_LOCAL_ID_KINDS: Final[frozenset[str]] = _ANCHOR_KINDS | frozenset({
    "parameter_posonly",
    "parameter_poskw",
    "parameter_kwonly",
    "parameter_vararg",
    "parameter_varkw",
    "expression_result",
    "name_load",
    "call_site",
    "call_argument",
    "call_result",
    "runtime_bound_local",
    "closure_cell",
})
_AST_PATH_RE: Final[re.Pattern[str]] = re.compile(r"^(?:root|(?:0|[1-9]\d*)(?:\.(?:0|[1-9]\d*))*)$")
_FINGERPRINT_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class LineageExtractionLimits:
    max_nodes: int = 100_000
    max_ast_depth: int = 200

    def __post_init__(self) -> None:
        for label, value in (("max_nodes", self.max_nodes), ("max_ast_depth", self.max_ast_depth)):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{label} must be a positive integer.")


DEFAULT_LINEAGE_EXTRACTION_LIMITS: Final[LineageExtractionLimits] = LineageExtractionLimits()


@dataclass(frozen=True)
class ParsedLineageSourceInput:
    source_key: str
    source_fingerprint: str
    tree: ast.AST


@dataclass(frozen=True)
class ExtractedLineageContribution:
    anchors: tuple[ExtractedAnchorFact, ...] = ()
    flows: tuple[ExtractedFlowFact, ...] = ()
    surfaces: tuple[ExtractedSurfaceFact, ...] = ()


class ExtractedLineageProvider(Protocol):
    def extract(self, source: ParsedLineageSourceInput) -> ExtractedLineageContribution: ...


def _validate_ast_path(ast_path: str) -> None:
    if not isinstance(ast_path, str) or _AST_PATH_RE.fullmatch(ast_path) is None:
        raise ValueError("ast_path is not canonical.")


def _encode_name(name: str | None) -> str:
    if name is None:
        return "-"
    if not isinstance(name, str) or not name:
        raise ValueError("name must be a non-empty string or None.")
    return quote(name, safe="").replace("-", "%2D")


def build_local_occurrence_id(kind: str, ast_path: str, name: str | None = None, *, ordinal: int = 0) -> str:
    if kind not in _LOCAL_ID_KINDS:
        raise ValueError(f"Unknown lineage local-id kind: {kind}")
    _validate_ast_path(ast_path)
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
        raise ValueError("ordinal must be a non-negative integer.")
    return f"occ:{_LOCAL_ID_VERSION}:{kind}:{ast_path}:i:{ordinal}:n:{_encode_name(name)}"


def parse_local_occurrence_id(value: str) -> tuple[str, str, int, str | None]:
    if not isinstance(value, str):
        raise ValueError("local occurrence id must be a string.")
    parts = value.split(":")
    if len(parts) != 8 or parts[0] != "occ" or parts[1] != _LOCAL_ID_VERSION or parts[4] != "i" or parts[6] != "n":
        raise ValueError("Invalid local occurrence id.")
    kind, ast_path = parts[2], parts[3]
    if kind not in _LOCAL_ID_KINDS:
        raise ValueError("Invalid local occurrence kind.")
    _validate_ast_path(ast_path)
    try:
        ordinal = int(parts[5])
    except ValueError as exc:
        raise ValueError("Invalid local occurrence ordinal.") from exc
    if ordinal < 0:
        raise ValueError("Invalid local occurrence ordinal.")
    name = None if parts[7] == "-" else unquote(parts[7])
    if build_local_occurrence_id(kind, ast_path, name, ordinal=ordinal) != value:
        raise ValueError("Local occurrence id is not canonical.")
    return kind, ast_path, ordinal, name


def _source_span(node: ast.AST) -> SourceSpan:
    start_line = int(getattr(node, "lineno", 0) or 0)
    start_column = int(getattr(node, "col_offset", 0) or 0)
    end_line = int(getattr(node, "end_lineno", start_line) or start_line)
    end_column = int(getattr(node, "end_col_offset", start_column) or start_column)
    return SourceSpan(start_line, start_column, end_line, end_column)


def _index_ast_paths(tree: ast.AST, limits: LineageExtractionLimits) -> tuple[dict[int, str], str | None]:
    paths: dict[int, str] = {}
    stack: list[tuple[ast.AST, str, int]] = [(tree, "root", 0)]
    node_count = 0
    while stack:
        node, ast_path, depth = stack.pop()
        node_count += 1
        if node_count > limits.max_nodes:
            return {}, "node_limit"
        if depth > limits.max_ast_depth:
            return {}, "ast_depth_limit"
        paths[id(node)] = ast_path
        children = list(ast.iter_child_nodes(node))
        for index in range(len(children) - 1, -1, -1):
            child_path = str(index) if ast_path == "root" else f"{ast_path}.{index}"
            stack.append((children[index], child_path, depth + 1))
    return paths, None


def _module_name_from_source_key(source_key: str) -> str:
    module_name = source_key[:-3].replace("/", ".")
    return module_name[: -len(".__init__")] if module_name.endswith(".__init__") else module_name

def _resolve_import_module(source_key: str, module_name: str | None, level: int) -> str | None:
    if level == 0: return module_name
    package_parts = source_key.split("/")[:-1]
    if not package_parts or level > len(package_parts): return None
    target_parts = list(package_parts[:len(package_parts) - (level - 1)])
    if module_name: target_parts.extend(module_name.split("."))
    return ".".join(target_parts) if target_parts else None


_PUBLIC_MODULE = "contextor.core.analysis.lineage_extraction"
LineageExtractionLimits.__module__ = _PUBLIC_MODULE
ParsedLineageSourceInput.__module__ = _PUBLIC_MODULE
ExtractedLineageContribution.__module__ = _PUBLIC_MODULE
ExtractedLineageProvider.__module__ = _PUBLIC_MODULE
build_local_occurrence_id.__module__ = _PUBLIC_MODULE
parse_local_occurrence_id.__module__ = _PUBLIC_MODULE

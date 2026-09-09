from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Final, Protocol
from urllib.parse import quote, unquote

from contextor.core.analysis.state_manager import canonical_python_source_path
from contextor.core.domain.lineage_facts import (
    ExtractedAnchorFact,
    ExtractedFlowFact,
    ExtractedLineageSourceFacts,
    ExtractedSurfaceFact,
    LineageFamilyStatus,
    SourceSpan,
)

_LOCAL_ID_VERSION: Final[str] = "v1"
_ANCHOR_KINDS: Final[frozenset[str]] = frozenset({"module", "class", "function", "async_function", "lambda", "comprehension", "parameter", "binding", "import_binding", "global_declaration", "nonlocal_declaration"})
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
    if kind not in _ANCHOR_KINDS:
        raise ValueError(f"Unknown lineage anchor kind: {kind}")
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
    if kind not in _ANCHOR_KINDS:
        raise ValueError("Invalid local occurrence anchor kind.")
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


class _AnchorExtractor:
    def __init__(self, paths: dict[int, str]) -> None:
        self.paths = paths
        self.anchors: list[ExtractedAnchorFact] = []
        self._ids: set[str] = set()

    def extract(self, tree: ast.AST) -> tuple[ExtractedAnchorFact, ...]:
        self._visit(tree, None, None)
        return tuple(sorted(self.anchors))

    def _add(self, kind: str, node: ast.AST, name: str | None, owner_local_id: str | None, *, ordinal: int = 0) -> str:
        local_id = build_local_occurrence_id(kind, self.paths[id(node)], name, ordinal=ordinal)
        if local_id in self._ids:
            raise ValueError(f"Duplicate lineage local id: {local_id}")
        self._ids.add(local_id)
        self.anchors.append(ExtractedAnchorFact(local_id=local_id, kind=kind, span=_source_span(node), owner_local_id=owner_local_id))
        return local_id

    def _visit(self, node: ast.AST, owner_local_id: str | None, walrus_owner_local_id: str | None) -> None:
        method = getattr(self, f"_visit_{type(node).__name__}", None)
        if method is not None:
            method(node, owner_local_id, walrus_owner_local_id)
            return
        for child in ast.iter_child_nodes(node):
            self._visit(child, owner_local_id, walrus_owner_local_id)

    def _visit_Module(self, node: ast.Module, _owner: str | None, _walrus_owner: str | None) -> None:
        module_id = self._add("module", node, None, None)
        for child in node.body:
            self._visit(child, module_id, None)

    def _visit_ClassDef(self, node: ast.ClassDef, owner: str | None, walrus_owner: str | None) -> None:
        class_id = self._add("class", node, node.name, owner)
        for child in (*node.decorator_list, *node.bases, *node.keywords):
            self._visit(child, owner, walrus_owner)
        for child in node.body:
            self._visit(child, class_id, None)

    def _function_signature_evidence(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
        args = node.args
        for default in args.defaults:
            self._visit(default, owner, walrus_owner)
        for default in args.kw_defaults:
            if default is not None:
                self._visit(default, owner, walrus_owner)
        all_args = list(getattr(args, "posonlyargs", ())) + list(args.args) + list(args.kwonlyargs)
        if args.vararg is not None:
            all_args.append(args.vararg)
        if args.kwarg is not None:
            all_args.append(args.kwarg)
        for arg in all_args:
            if arg.annotation is not None:
                self._visit(arg.annotation, owner, walrus_owner)
        returns = getattr(node, "returns", None)
        if returns is not None:
            self._visit(returns, owner, walrus_owner)

    def _parameter_anchors(self, args: ast.arguments, owner: str) -> None:
        parameters = list(getattr(args, "posonlyargs", ())) + list(args.args) + ([args.vararg] if args.vararg is not None else []) + list(args.kwonlyargs) + ([args.kwarg] if args.kwarg is not None else [])
        for parameter in parameters:
            self._add("parameter", parameter, parameter.arg, owner)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str, owner: str | None, walrus_owner: str | None) -> None:
        function_id = self._add(kind, node, node.name, owner)
        for decorator in node.decorator_list:
            self._visit(decorator, owner, walrus_owner)
        self._function_signature_evidence(node, owner, walrus_owner)
        self._parameter_anchors(node.args, function_id)
        for child in node.body:
            self._visit(child, function_id, None)

    def _visit_FunctionDef(self, node: ast.FunctionDef, owner: str | None, walrus_owner: str | None) -> None:
        self._visit_function(node, "function", owner, walrus_owner)

    def _visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef, owner: str | None, walrus_owner: str | None) -> None:
        self._visit_function(node, "async_function", owner, walrus_owner)

    def _visit_Lambda(self, node: ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
        lambda_id = self._add("lambda", node, None, owner)
        self._function_signature_evidence(node, owner, walrus_owner)
        self._parameter_anchors(node.args, lambda_id)
        self._visit(node.body, lambda_id, None)

    def _visit_comprehension_expression(self, node: ast.AST, generators: list[ast.comprehension], values: tuple[ast.AST, ...], owner: str | None, walrus_owner: str | None) -> None:
        comprehension_id = self._add("comprehension", node, None, owner)
        if not generators:
            for value in values:
                self._visit(value, comprehension_id, walrus_owner or owner)
            return
        first = generators[0]
        self._visit(first.iter, owner, walrus_owner)
        comprehension_walrus_owner = walrus_owner or owner
        self._visit(first.target, comprehension_id, comprehension_walrus_owner)
        for condition in first.ifs:
            self._visit(condition, comprehension_id, comprehension_walrus_owner)
        for generator in generators[1:]:
            self._visit(generator.iter, comprehension_id, comprehension_walrus_owner)
            self._visit(generator.target, comprehension_id, comprehension_walrus_owner)
            for condition in generator.ifs:
                self._visit(condition, comprehension_id, comprehension_walrus_owner)
        for value in values:
            self._visit(value, comprehension_id, comprehension_walrus_owner)

    def _visit_ListComp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)

    def _visit_SetComp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)

    def _visit_GeneratorExp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)

    def _visit_DictComp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.key, node.value), owner, walrus_owner)

    def _visit_Name(self, node: ast.Name, owner: str | None, _walrus_owner: str | None) -> None:
        if isinstance(node.ctx, ast.Store):
            self._add("binding", node, node.id, owner)

    def _visit_NamedExpr(self, node: ast.NamedExpr, owner: str | None, walrus_owner: str | None) -> None:
        target_owner = walrus_owner or owner
        if isinstance(node.target, ast.Name):
            self._add("binding", node.target, node.target.id, target_owner)
        else:
            self._visit(node.target, target_owner, walrus_owner)
        self._visit(node.value, owner, walrus_owner)

    def _visit_Import(self, node: ast.Import, owner: str | None, _walrus_owner: str | None) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".", 1)[0]
            self._add("import_binding", alias, local_name, owner)

    def _visit_ImportFrom(self, node: ast.ImportFrom, owner: str | None, _walrus_owner: str | None) -> None:
        for alias in node.names:
            if alias.name != "*":
                self._add("import_binding", alias, alias.asname or alias.name, owner)

    def _visit_Global(self, node: ast.Global, owner: str | None, _walrus_owner: str | None) -> None:
        for ordinal, name in enumerate(node.names):
            self._add("global_declaration", node, name, owner, ordinal=ordinal)

    def _visit_Nonlocal(self, node: ast.Nonlocal, owner: str | None, _walrus_owner: str | None) -> None:
        for ordinal, name in enumerate(node.names):
            self._add("nonlocal_declaration", node, name, owner, ordinal=ordinal)

    def _visit_ExceptHandler(self, node: ast.ExceptHandler, owner: str | None, walrus_owner: str | None) -> None:
        if node.type is not None:
            self._visit(node.type, owner, walrus_owner)
        if isinstance(node.name, str):
            self._add("binding", node, node.name, owner)
        for child in node.body:
            self._visit(child, owner, walrus_owner)

    def _visit_MatchAs(self, node: ast.MatchAs, owner: str | None, walrus_owner: str | None) -> None:
        if node.pattern is not None:
            self._visit(node.pattern, owner, walrus_owner)
        if node.name is not None:
            self._add("binding", node, node.name, owner)

    def _visit_MatchStar(self, node: ast.MatchStar, owner: str | None, _walrus_owner: str | None) -> None:
        if node.name is not None:
            self._add("binding", node, node.name, owner)

    def _visit_MatchMapping(self, node: ast.MatchMapping, owner: str | None, walrus_owner: str | None) -> None:
        for key in node.keys:
            self._visit(key, owner, walrus_owner)
        for pattern in node.patterns:
            self._visit(pattern, owner, walrus_owner)
        if node.rest is not None:
            self._add("binding", node, node.rest, owner)


def extract_lineage_source_facts(tree: ast.AST, *, source_key: str, source_fingerprint: str, limits: LineageExtractionLimits = DEFAULT_LINEAGE_EXTRACTION_LIMITS) -> ExtractedLineageSourceFacts:
    if not isinstance(tree, ast.AST):
        raise TypeError("tree must be ast.AST.")
    canonical_key = canonical_python_source_path(source_key)
    if canonical_key is None or canonical_key != source_key:
        raise ValueError("source_key must be canonical repository-relative POSIX Python path.")
    if not isinstance(source_fingerprint, str) or _FINGERPRINT_RE.fullmatch(source_fingerprint) is None:
        raise ValueError("source_fingerprint must be lowercase raw-byte SHA-256.")
    if not isinstance(limits, LineageExtractionLimits):
        raise TypeError("limits must be LineageExtractionLimits.")
    paths, limit_reason = _index_ast_paths(tree, limits)
    if limit_reason is not None:
        return ExtractedLineageSourceFacts(source_key=source_key, source_fingerprint=source_fingerprint, status=LineageFamilyStatus.RESOURCE_LIMIT, resource_limit_reason=limit_reason)
    return ExtractedLineageSourceFacts(source_key=source_key, source_fingerprint=source_fingerprint, anchors=_AnchorExtractor(paths).extract(tree), flows=(), surfaces=(), status=LineageFamilyStatus.FRESH)


__all__ = [
    "DEFAULT_LINEAGE_EXTRACTION_LIMITS",
    "ExtractedLineageContribution",
    "ExtractedLineageProvider",
    "LineageExtractionLimits",
    "ParsedLineageSourceInput",
    "build_local_occurrence_id",
    "extract_lineage_source_facts",
    "parse_local_occurrence_id",
]

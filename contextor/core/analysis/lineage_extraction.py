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
    ExtractedOccurrenceRef,
    ExtractedSurfaceFact,
    ExtractedSymbolicKind,
    ExtractedSymbolicRef,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    ParameterKind,
    ResolutionKind,
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


@dataclass(frozen=True)
class _ParameterInfo:
    local_id: str
    name: str
    kind: ParameterKind
    ordinal: int


@dataclass(frozen=True)
class _CallableInfo:
    name: str
    anchor_id: str
    parameters: tuple[_ParameterInfo, ...]


@dataclass(frozen=True)
class _ImportInfo:
    module_name: str
    symbol_name: str | None
    binding_id: str


class _AnchorExtractor:
    def __init__(self, paths: dict[int, str], source_key: str) -> None:
        self.paths = paths
        self.source_key = source_key
        self.module_name = _module_name_from_source_key(source_key)
        self.anchors: list[ExtractedAnchorFact] = []
        self.flows: list[ExtractedFlowFact] = []
        self._ids: set[str] = set()
        self._flow_ids: set[str] = set()
        self._occurrences: dict[tuple[str, int, str | None, int], ExtractedOccurrenceRef] = {}
        self._bindings: dict[str | None, dict[str, ExtractedOccurrenceRef]] = {}
        self._callables: dict[str | None, dict[str, _CallableInfo]] = {}
        self._callables_by_anchor: dict[str, _CallableInfo] = {}
        self._imports: dict[str | None, dict[str, _ImportInfo]] = {}
        self._blocked: dict[str | None, set[str]] = {}

    def extract(self, tree: ast.AST) -> tuple[tuple[ExtractedAnchorFact, ...], tuple[ExtractedFlowFact, ...]]:
        self._visit(tree, None, None)
        return tuple(sorted(self.anchors)), tuple(sorted(self.flows))

    def _add(self, kind: str, node: ast.AST, name: str | None, owner_local_id: str | None, *, ordinal: int = 0, local_kind: str | None = None) -> str:
        local_id = build_local_occurrence_id(local_kind or kind, self.paths[id(node)], name, ordinal=ordinal)
        if local_id in self._ids:
            raise ValueError(f"Duplicate lineage local id: {local_id}")
        self._ids.add(local_id)
        self.anchors.append(ExtractedAnchorFact(local_id=local_id, kind=kind, span=_source_span(node), owner_local_id=owner_local_id))
        return local_id

    def _occurrence(self, kind: str, node: ast.AST, name: str | None = None, *, ordinal: int = 0) -> ExtractedOccurrenceRef:
        cache_key = (kind, id(node), name, ordinal)
        cached = self._occurrences.get(cache_key)
        if cached is not None:
            return cached
        local_id = build_local_occurrence_id(
            kind,
            self.paths[id(node)],
            name,
            ordinal=ordinal,
        )
        if local_id in self._ids:
            raise ValueError(f"Duplicate lineage local id: {local_id}")
        self._ids.add(local_id)
        occurrence = ExtractedOccurrenceRef(local_id)
        self._occurrences[cache_key] = occurrence
        return occurrence

    def _flow(self, *, source, target, relation: LineageRelation, node: ast.AST, resolution_kind: ResolutionKind, confidence: LineageConfidence, ordinal: int = 0) -> None:
        local_id = f"flow:v1:{relation.value}:{self.paths[id(node)]}:i:{ordinal}"
        if local_id in self._flow_ids: raise ValueError(f"Duplicate lineage flow id: {local_id}")
        self._flow_ids.add(local_id)
        self.flows.append(ExtractedFlowFact(local_id, source, target, relation, _source_span(node), resolution_kind, confidence))

    def _frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
        return self._bindings.setdefault(owner, {})

    def _clone_frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
        return dict(self._frame(owner))

    def _replace_frame(
        self,
        owner: str | None,
        frame: dict[str, ExtractedOccurrenceRef],
    ) -> None:
        self._bindings[owner] = dict(frame)

    def _merge_frames(
        self,
        frames: tuple[dict[str, ExtractedOccurrenceRef], ...],
    ) -> dict[str, ExtractedOccurrenceRef]:
        if not frames:
            return {}
        common_names = set(frames[0])
        for frame in frames[1:]:
            common_names.intersection_update(frame)
        merged: dict[str, ExtractedOccurrenceRef] = {}
        for name in common_names:
            first = frames[0][name]
            if all(frame[name] == first for frame in frames[1:]):
                merged[name] = first
        return merged

    def _blocked_names(self, owner: str | None) -> set[str]:
        return self._blocked.setdefault(owner, set())

    def _callable_frame(self, owner: str | None) -> dict[str, _CallableInfo]:
        return self._callables.setdefault(owner, {})

    def _import_frame(self, owner: str | None) -> dict[str, _ImportInfo]:
        return self._imports.setdefault(owner, {})

    def _value(
        self,
        node: ast.AST,
        owner: str | None,
        walrus_owner: str | None,
    ) -> ExtractedOccurrenceRef:
        self._visit(node, owner, walrus_owner)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            return self._occurrence("name_load", node, node.id)
        if isinstance(node, ast.Call):
            return self._occurrence("call_result", node)
        return self._occurrence("expression_result", node)

    def _parameter_symbolic(self, callable_symbol_name: str, parameter: _ParameterInfo) -> ExtractedSymbolicRef:
        return ExtractedSymbolicRef(ExtractedSymbolicKind.PARAMETER, self.module_name, callable_symbol_name, parameter.local_id)

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

    def _parameter_anchors(self, args: ast.arguments, owner: str, callable_symbol_name: str) -> tuple[_ParameterInfo, ...]:
        result = []
        groups = ((getattr(args, "posonlyargs", ()), ParameterKind.POSITIONAL_ONLY, "parameter_posonly"), (args.args, ParameterKind.POSITIONAL_OR_KEYWORD, "parameter_poskw"), ((args.vararg,) if args.vararg else (), ParameterKind.VAR_POSITIONAL, "parameter_vararg"), (args.kwonlyargs, ParameterKind.KEYWORD_ONLY, "parameter_kwonly"), ((args.kwarg,) if args.kwarg else (), ParameterKind.VAR_KEYWORD, "parameter_varkw"))
        for group, kind, local_kind in groups:
            for ordinal, parameter in enumerate(group):
                local_id = self._add("parameter", parameter, parameter.arg, owner, ordinal=ordinal if kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD) else 0, local_kind=local_kind)
                info = _ParameterInfo(local_id, parameter.arg, kind, ordinal if kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD) else 0)
                result.append((info, parameter))
        for ordinal, (info, parameter) in enumerate(result):
            self._flow(source=self._parameter_symbolic(callable_symbol_name, info), target=ExtractedOccurrenceRef(info.local_id), relation=LineageRelation.BINDS, node=parameter, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
        return tuple(info for info, _parameter in result)

    def _default_flows(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, callable_symbol_name: str, parameters: tuple[_ParameterInfo, ...]) -> None:
        positional_parameters = tuple(parameter for parameter in parameters if parameter.kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD))
        positional_defaults = tuple(node.args.defaults)
        if positional_defaults:
            for ordinal, (default, parameter) in enumerate(zip(positional_defaults, positional_parameters[-len(positional_defaults) :])):
                self._flow(source=self._occurrence("expression_result", default), target=self._parameter_symbolic(callable_symbol_name, parameter), relation=LineageRelation.DEFAULTS_TO_PARAMETER, node=default, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
        kwonly_parameters = tuple(parameter for parameter in parameters if parameter.kind is ParameterKind.KEYWORD_ONLY)
        for ordinal, (default, parameter) in enumerate(zip(node.args.kw_defaults, kwonly_parameters)):
            if default is not None:
                self._flow(source=self._occurrence("expression_result", default), target=self._parameter_symbolic(callable_symbol_name, parameter), relation=LineageRelation.DEFAULTS_TO_PARAMETER, node=default, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str, owner: str | None, walrus_owner: str | None) -> None:
        function_id = self._add(kind, node, node.name, owner)
        for decorator in node.decorator_list:
            self._visit(decorator, owner, walrus_owner)
        self._function_signature_evidence(node, owner, walrus_owner)
        parameters = self._parameter_anchors(node.args, function_id, node.name)
        self._default_flows(node, node.name, parameters)
        for child in node.body:
            self._visit(child, function_id, None)

    def _visit_FunctionDef(self, node: ast.FunctionDef, owner: str | None, walrus_owner: str | None) -> None:
        self._visit_function(node, "function", owner, walrus_owner)

    def _visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef, owner: str | None, walrus_owner: str | None) -> None:
        self._visit_function(node, "async_function", owner, walrus_owner)

    def _visit_Lambda(self, node: ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
        lambda_id = self._add("lambda", node, None, owner)
        self._function_signature_evidence(node, owner, walrus_owner)
        callable_symbol_name = f"lambda@{self.paths[id(node)]}"
        parameters = self._parameter_anchors(node.args, lambda_id, callable_symbol_name)
        self._default_flows(node, callable_symbol_name, parameters)
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
    anchors, flows = _AnchorExtractor(paths, source_key).extract(tree)
    return ExtractedLineageSourceFacts(source_key=source_key, source_fingerprint=source_fingerprint, anchors=anchors, flows=flows, surfaces=(), status=LineageFamilyStatus.FRESH)


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

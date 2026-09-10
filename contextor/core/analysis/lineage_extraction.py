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

def _resolve_import_module(source_key: str, module_name: str | None, level: int) -> str | None:
    if level == 0: return module_name
    package_parts = source_key.split("/")[:-1]
    if not package_parts or level > len(package_parts): return None
    target_parts = list(package_parts[:len(package_parts) - (level - 1)])
    if module_name: target_parts.extend(module_name.split("."))
    return ".".join(target_parts) if target_parts else None


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


@dataclass
class _ActiveComprehension:
    lookup_owner: str
    lexical_enclosing_owner: str | None
    effective_walrus_owner: str | None
    walrus_entry_frame: dict[str, ExtractedOccurrenceRef]
    touched_walrus_names: set[str]


@dataclass(frozen=True)
class _CallArgumentInfo:
    occurrence: ExtractedOccurrenceRef
    node: ast.AST
    kind: str
    keyword_name: str | None


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
        self._callables_by_binding: dict[str, _CallableInfo] = {}
        self._callable_values: dict[str, _CallableInfo] = {}
        self._imports: dict[str | None, dict[str, _ImportInfo]] = {}
        self._blocked: dict[str | None, set[str]] = {}
        self._active_comprehensions: list[_ActiveComprehension] = []

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

    def _flow(self, *, source, target, relation: LineageRelation, node: ast.AST, resolution_kind: ResolutionKind, confidence: LineageConfidence, ordinal: int = 0, dynamic_boundary: str | None = None) -> None:
        local_id = f"flow:v1:{relation.value}:{self.paths[id(node)]}:i:{ordinal}"
        if local_id in self._flow_ids: raise ValueError(f"Duplicate lineage flow id: {local_id}")
        self._flow_ids.add(local_id)
        self.flows.append(ExtractedFlowFact(local_id, source, target, relation, _source_span(node), resolution_kind, confidence, dynamic_boundary=dynamic_boundary))

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

    def _begin_comprehension(
        self,
        lookup_owner: str,
        lexical_enclosing_owner: str | None,
        effective_walrus_owner: str | None,
    ) -> _ActiveComprehension:
        record = _ActiveComprehension(
            lookup_owner,
            lexical_enclosing_owner,
            effective_walrus_owner,
            self._clone_frame(effective_walrus_owner),
            set(),
        )
        self._replace_frame(
            lookup_owner,
            self._clone_frame(lexical_enclosing_owner),
        )
        imports = self._import_frame(lookup_owner)
        imports.clear()
        imports.update(
            self._import_frame(lexical_enclosing_owner)
        )
        self._active_comprehensions.append(record)
        return record

    def _publish_executed_walrus(
        self,
        name: str,
        binding: ExtractedOccurrenceRef,
        target_owner: str | None,
    ) -> None:
        for record in self._active_comprehensions:
            if record.effective_walrus_owner != target_owner:
                continue
            record.touched_walrus_names.add(name)
            self._frame(record.lookup_owner)[name] = binding

    def _finish_comprehension(
        self,
        record: _ActiveComprehension,
    ) -> None:
        if (
            not self._active_comprehensions
            or self._active_comprehensions[-1] is not record
        ):
            raise RuntimeError(
                "Comprehension lineage stack mismatch"
            )
        body_frame = self._clone_frame(
            record.effective_walrus_owner
        )
        merged = self._merge_frames(
            (record.walrus_entry_frame, body_frame)
        )
        self._replace_frame(
            record.effective_walrus_owner,
            merged,
        )
        self._active_comprehensions.pop()
        for parent in self._active_comprehensions:
            if (
                parent.effective_walrus_owner
                != record.effective_walrus_owner
            ):
                continue
            for name in record.touched_walrus_names:
                parent.touched_walrus_names.add(name)
                if name in merged:
                    self._frame(parent.lookup_owner)[name] = merged[name]
                else:
                    self._frame(parent.lookup_owner).pop(name, None)

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

    def _visit_block_from_frame(
        self,
        body: list[ast.stmt],
        owner: str | None,
        walrus_owner: str | None,
        frame: dict[str, ExtractedOccurrenceRef],
    ) -> dict[str, ExtractedOccurrenceRef]:
        self._replace_frame(owner, frame)
        for child in body:
            self._visit(child, owner, walrus_owner)
        return self._clone_frame(owner)

    def _blocked_names(self, owner: str | None) -> set[str]:
        return self._blocked.setdefault(owner, set())

    def _callable_frame(self, owner: str | None) -> dict[str, _CallableInfo]:
        return self._callables.setdefault(owner, {})

    def _import_frame(self, owner: str | None) -> dict[str, _ImportInfo]:
        return self._imports.setdefault(owner, {})

    def _register_import_binding(self, alias: ast.alias, owner: str | None, local_name: str, module_name: str | None, symbol_name: str | None) -> None:
        binding_id = self._add("import_binding", alias, local_name, owner)
        if local_name in self._blocked_names(owner): return
        self._frame(owner)[local_name] = ExtractedOccurrenceRef(binding_id)
        if module_name is not None: self._import_frame(owner)[local_name] = _ImportInfo(module_name, symbol_name, binding_id)

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

    def _return_symbolic(self, callable_info: _CallableInfo) -> ExtractedSymbolicRef:
        return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, self.module_name, callable_info.name, callable_info.anchor_id)

    def _resolve_current_local_callable(self, node: ast.Call, owner: str | None) -> _CallableInfo | None:
        if not isinstance(node.func, ast.Name): return None
        current = self._frame(owner).get(node.func.id)
        if current is None: return None
        return self._callables_by_anchor.get(current.local_id) or self._callables_by_binding.get(current.local_id)

    def _current_import_info(self, owner: str | None, local_name: str) -> _ImportInfo | None:
        current, info = self._frame(owner).get(local_name), self._import_frame(owner).get(local_name)
        return info if current is not None and info is not None and current.local_id == info.binding_id else None

    def _resolve_current_imported_callable(self, node: ast.Call, owner: str | None) -> ExtractedSymbolicRef | None:
        if isinstance(node.func, ast.Name):
            info = self._current_import_info(owner, node.func.id)
            if info is None or info.symbol_name is None: return None
            return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, info.module_name, info.symbol_name, info.binding_id)
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            info = self._current_import_info(owner, node.func.value.id)
            if info is None or info.symbol_name is not None: return None
            return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, info.module_name, node.func.attr, info.binding_id)
        return None

    def _collect_call_arguments(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> tuple[_CallArgumentInfo, ...]:
        pending = [(arg, "starred" if isinstance(arg, ast.Starred) else "positional", None, index) for index, arg in enumerate(node.args)]
        pending += [(keyword.value, "double_starred" if keyword.arg is None else "keyword", keyword.arg, len(node.args) + index) for index, keyword in enumerate(node.keywords)]
        pending.sort(key=lambda item: (int(getattr(item[0], "lineno", 0) or 0), int(getattr(item[0], "col_offset", 0) or 0), item[3]))
        result = []
        for ordinal, (argument_node, kind, keyword_name, _source_ordinal) in enumerate(pending):
            self._value(argument_node, owner, walrus_owner)
            result.append(_CallArgumentInfo(self._occurrence("call_argument", argument_node, keyword_name if kind == "keyword" else None, ordinal=ordinal), argument_node, kind, keyword_name))
        return tuple(result)

    def _emit_argument_to_parameter(self, argument: _CallArgumentInfo, callable_info: _CallableInfo, parameter: _ParameterInfo) -> None:
        self._flow(source=argument.occurrence, target=self._parameter_symbolic(callable_info.name, parameter), relation=LineageRelation.ARGUMENT_TO_PARAMETER, node=argument.node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)

    def _bind_call_arguments(self, arguments: tuple[_CallArgumentInfo, ...], callable_info: _CallableInfo) -> None:
        fixed = tuple(p for p in callable_info.parameters if p.kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD))
        keywords = {p.name: p for p in callable_info.parameters if p.kind in (ParameterKind.POSITIONAL_OR_KEYWORD, ParameterKind.KEYWORD_ONLY)}
        vararg = next((p for p in callable_info.parameters if p.kind is ParameterKind.VAR_POSITIONAL), None)
        varkw = next((p for p in callable_info.parameters if p.kind is ParameterKind.VAR_KEYWORD), None)
        consumed, index, uncertain = set(), 0, False
        for argument in arguments:
            if argument.kind == "starred": uncertain = True; continue
            if argument.kind == "double_starred": continue
            if argument.kind == "positional":
                if uncertain: continue
                if index < len(fixed):
                    parameter = fixed[index]; index += 1; consumed.add(parameter.local_id); self._emit_argument_to_parameter(argument, callable_info, parameter)
                elif vararg is not None: self._emit_argument_to_parameter(argument, callable_info, vararg)
                continue
            if argument.kind == "keyword" and argument.keyword_name is not None:
                parameter = keywords.get(argument.keyword_name)
                if parameter is not None and parameter.local_id not in consumed:
                    consumed.add(parameter.local_id); self._emit_argument_to_parameter(argument, callable_info, parameter)
                elif parameter is None and varkw is not None: self._emit_argument_to_parameter(argument, callable_info, varkw)

    def _visit(self, node: ast.AST, owner_local_id: str | None, walrus_owner_local_id: str | None) -> None:
        method = getattr(self, f"_visit_{type(node).__name__}", None)
        if method is not None:
            method(node, owner_local_id, walrus_owner_local_id)
            return
        for child in ast.iter_child_nodes(node):
            self._visit(child, owner_local_id, walrus_owner_local_id)

    def _visit_Module(self, node: ast.Module, _owner: str | None, _walrus_owner: str | None) -> None:
        module_id = self._add("module", node, None, None)
        self._frame(module_id)
        for child in node.body:
            self._visit(child, module_id, None)

    def _visit_ClassDef(self, node: ast.ClassDef, owner: str | None, walrus_owner: str | None) -> None:
        class_id = self._add("class", node, node.name, owner)
        for child in (*node.decorator_list, *node.bases, *node.keywords):
            self._visit(child, owner, walrus_owner)
        self._frame(class_id)
        for child in node.body:
            self._visit(child, class_id, None)
        if node.name not in self._blocked_names(owner):
            self._frame(owner)[node.name] = ExtractedOccurrenceRef(class_id)

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
        callable_info = _CallableInfo(node.name, function_id, parameters)
        self._callable_frame(owner)[node.name] = callable_info
        self._callables_by_anchor[function_id] = callable_info
        function_frame = self._frame(function_id)
        for parameter in parameters:
            function_frame[parameter.name] = ExtractedOccurrenceRef(parameter.local_id)
        for child in node.body:
            self._visit(child, function_id, None)
        if node.name not in self._blocked_names(owner):
            self._frame(owner)[node.name] = ExtractedOccurrenceRef(function_id)

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
        callable_info = _CallableInfo(callable_symbol_name, lambda_id, parameters)
        self._callables_by_anchor[lambda_id] = callable_info
        lambda_frame = self._frame(lambda_id)
        for parameter in parameters:
            lambda_frame[parameter.name] = ExtractedOccurrenceRef(parameter.local_id)
        body_source = self._value(node.body, lambda_id, None)
        self._flow(source=body_source, target=self._return_symbolic(callable_info), relation=LineageRelation.RETURNS, node=node.body, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
        lambda_value = self._occurrence("expression_result", node)
        self._callable_values[lambda_value.local_id] = callable_info

    def _visit_Return(self, node: ast.Return, owner: str | None, walrus_owner: str | None) -> None:
        if node.value is None: return
        source = self._value(node.value, owner, walrus_owner)
        callable_info = self._callables_by_anchor.get(owner) if owner is not None else None
        if callable_info is not None:
            self._flow(source=source, target=self._return_symbolic(callable_info), relation=LineageRelation.RETURNS, node=node, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)

    def _visit_Call(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> None:
        self._visit(node.func, owner, walrus_owner)
        callable_info = self._resolve_current_local_callable(node, owner)
        imported_return = self._resolve_current_imported_callable(node, owner)
        callee_ref = self._frame(owner).get(node.func.id) if isinstance(node.func, ast.Name) else None
        call_site, call_result = self._occurrence("call_site", node), self._occurrence("call_result", node)
        arguments = self._collect_call_arguments(node, owner, walrus_owner)
        if callable_info is not None:
            self._bind_call_arguments(arguments, callable_info)
            self._flow(source=self._return_symbolic(callable_info), target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
            return
        if imported_return is not None:
            self._flow(source=imported_return, target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=ResolutionKind.IMPORT_EXACT, confidence=LineageConfidence.CONFIRMED)
            return
        if isinstance(node.func, ast.Name) and callee_ref is None:
            resolution_kind, confidence = ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED
            dynamic_boundary = None
        else:
            resolution_kind, confidence = ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC
            dynamic_boundary = "dynamic_call"
        self._flow(source=call_site, target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=resolution_kind, confidence=confidence, dynamic_boundary=dynamic_boundary)

    def _visit_comprehension_expression(
        self,
        node: ast.AST,
        generators: list[ast.comprehension],
        values: tuple[ast.AST, ...],
        owner: str | None,
        walrus_owner: str | None,
    ) -> None:
        comprehension_id = self._add(
            "comprehension",
            node,
            None,
            owner,
        )
        if not generators:
            raise ValueError(
                "Parsed comprehension without generators"
            )
        first = generators[0]
        self._visit(
            first.iter,
            owner,
            walrus_owner,
        )
        effective_walrus_owner = walrus_owner or owner
        record = self._begin_comprehension(
            comprehension_id,
            owner,
            effective_walrus_owner,
        )
        try:
            self._runtime_bind_target(
                first.target,
                comprehension_id,
                effective_walrus_owner,
            )
            for condition in first.ifs:
                self._visit(
                    condition,
                    comprehension_id,
                    effective_walrus_owner,
                )
            for generator in generators[1:]:
                self._visit(
                    generator.iter,
                    comprehension_id,
                    effective_walrus_owner,
                )
                self._runtime_bind_target(
                    generator.target,
                    comprehension_id,
                    effective_walrus_owner,
                )
                for condition in generator.ifs:
                    self._visit(
                        condition,
                        comprehension_id,
                        effective_walrus_owner,
                    )
            for value in values:
                self._visit(
                    value,
                    comprehension_id,
                    effective_walrus_owner,
                )
        finally:
            self._finish_comprehension(record)

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
            return
        if isinstance(node.ctx, ast.Load):
            load = self._occurrence("name_load", node, node.id)
            if node.id in self._blocked_names(owner):
                return
            source = self._frame(owner).get(node.id)
            if source is None:
                return
            self._flow(source=source, target=load, relation=LineageRelation.BINDS, node=node, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)

    def _assign_target(
        self,
        target: ast.AST,
        source: ExtractedOccurrenceRef,
        owner: str | None,
        walrus_owner: str | None,
    ) -> ExtractedOccurrenceRef | None:
        if not isinstance(target, ast.Name):
            self._visit(target, owner, walrus_owner)
            return None
        binding = ExtractedOccurrenceRef(self._add("binding", target, target.id, owner))
        if target.id in self._blocked_names(owner):
            return None
        self._frame(owner)[target.id] = binding
        callable_info = self._callable_values.get(source.local_id)
        if callable_info is not None:
            self._callables_by_binding[binding.local_id] = callable_info
        self._flow(source=source, target=binding, relation=LineageRelation.ASSIGNS, node=target, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
        return binding

    def _runtime_bind_target(
        self,
        target: ast.AST,
        owner: str | None,
        walrus_owner: str | None,
    ) -> None:
        if isinstance(target, ast.Name):
            binding = ExtractedOccurrenceRef(
                self._add("binding", target, target.id, owner)
            )
            if target.id in self._blocked_names(owner):
                return
            source = self._occurrence(
                "runtime_bound_local",
                target,
                target.id,
            )
            self._frame(owner)[target.id] = binding
            self._flow(
                source=source,
                target=binding,
                relation=LineageRelation.ASSIGNS,
                node=target,
                resolution_kind=ResolutionKind.LEXICAL_EXACT,
                confidence=LineageConfidence.CONFIRMED,
            )
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                self._runtime_bind_target(
                    item,
                    owner,
                    walrus_owner,
                )
            return
        if isinstance(target, ast.Starred):
            self._runtime_bind_target(
                target.value,
                owner,
                walrus_owner,
            )
            return
        self._visit(target, owner, walrus_owner)

    def _visit_Assign(self, node: ast.Assign, owner: str | None, walrus_owner: str | None) -> None:
        source = self._value(node.value, owner, walrus_owner)
        for target in node.targets:
            self._assign_target(target, source, owner, walrus_owner)

    def _visit_AnnAssign(self, node: ast.AnnAssign, owner: str | None, walrus_owner: str | None) -> None:
        if node.value is None:
            self._visit(node.target, owner, walrus_owner)
            self._visit(node.annotation, owner, walrus_owner)
            return
        source = self._value(node.value, owner, walrus_owner)
        self._assign_target(node.target, source, owner, walrus_owner)
        self._visit(node.annotation, owner, walrus_owner)

    def _visit_NamedExpr(self, node: ast.NamedExpr, owner: str | None, walrus_owner: str | None) -> None:
        target_owner = walrus_owner or owner
        source = self._value(node.value, owner, walrus_owner)
        binding = self._assign_target(
            node.target,
            source,
            target_owner,
            walrus_owner,
        )
        if (
            binding is not None
            and isinstance(node.target, ast.Name)
        ):
            self._publish_executed_walrus(
                node.target.id,
                binding,
                target_owner,
            )

    def _visit_AugAssign(self, node: ast.AugAssign, owner: str | None, walrus_owner: str | None) -> None:
        if not isinstance(node.target, ast.Name):
            self._visit(node.target, owner, walrus_owner)
            self._value(node.value, owner, walrus_owner)
            return
        blocked = node.target.id in self._blocked_names(owner)
        prior = None if blocked else self._frame(owner).get(node.target.id)
        if prior is not None:
            prior_load = self._occurrence("name_load", node.target, node.target.id)
            self._flow(
                source=prior,
                target=prior_load,
                relation=LineageRelation.BINDS,
                node=node.target,
                resolution_kind=ResolutionKind.LEXICAL_EXACT,
                confidence=LineageConfidence.CONFIRMED,
            )
        self._value(node.value, owner, walrus_owner)
        binding = ExtractedOccurrenceRef(
            self._add("binding", node.target, node.target.id, owner)
        )
        if blocked or prior is None:
            return
        self._frame(owner)[node.target.id] = binding

    def _visit_If(self, node: ast.If, owner: str | None, walrus_owner: str | None) -> None:
        self._visit(node.test, owner, walrus_owner)
        entry_frame = self._clone_frame(owner)
        body_frame = self._visit_block_from_frame(
            node.body,
            owner,
            walrus_owner,
            entry_frame,
        )
        if node.orelse:
            else_frame = self._visit_block_from_frame(
                node.orelse,
                owner,
                walrus_owner,
                entry_frame,
            )
        else:
            else_frame = dict(entry_frame)
        self._replace_frame(
            owner,
            self._merge_frames((body_frame, else_frame)),
        )

    def _visit_For(self, node: ast.For, owner: str | None, walrus_owner: str | None) -> None:
        self._visit(node.iter, owner, walrus_owner)
        entry_frame = self._clone_frame(owner)
        self._replace_frame(owner, entry_frame)
        self._runtime_bind_target(
            node.target,
            owner,
            walrus_owner,
        )
        for child in node.body:
            self._visit(child, owner, walrus_owner)
        body_frame = self._clone_frame(owner)
        loop_exit_frame = self._merge_frames(
            (entry_frame, body_frame)
        )
        self._replace_frame(owner, loop_exit_frame)
        if not node.orelse:
            return
        else_frame = self._visit_block_from_frame(
            node.orelse,
            owner,
            walrus_owner,
            loop_exit_frame,
        )
        self._replace_frame(
            owner,
            self._merge_frames((loop_exit_frame, else_frame)),
        )

    def _visit_AsyncFor(self, node: ast.AsyncFor, owner: str | None, walrus_owner: str | None) -> None:
        self._visit(node.iter, owner, walrus_owner)
        entry_frame = self._clone_frame(owner)
        self._replace_frame(owner, entry_frame)
        self._runtime_bind_target(
            node.target,
            owner,
            walrus_owner,
        )
        for child in node.body:
            self._visit(child, owner, walrus_owner)
        body_frame = self._clone_frame(owner)
        loop_exit_frame = self._merge_frames(
            (entry_frame, body_frame)
        )
        self._replace_frame(owner, loop_exit_frame)
        if not node.orelse:
            return
        else_frame = self._visit_block_from_frame(
            node.orelse,
            owner,
            walrus_owner,
            loop_exit_frame,
        )
        self._replace_frame(
            owner,
            self._merge_frames((loop_exit_frame, else_frame)),
        )

    def _visit_While(self, node: ast.While, owner: str | None, walrus_owner: str | None) -> None:
        self._visit(node.test, owner, walrus_owner)
        entry_frame = self._clone_frame(owner)
        body_frame = self._visit_block_from_frame(
            node.body,
            owner,
            walrus_owner,
            entry_frame,
        )
        loop_exit_frame = self._merge_frames(
            (entry_frame, body_frame)
        )
        self._replace_frame(owner, loop_exit_frame)
        if not node.orelse:
            return
        else_frame = self._visit_block_from_frame(
            node.orelse,
            owner,
            walrus_owner,
            loop_exit_frame,
        )
        self._replace_frame(
            owner,
            self._merge_frames((loop_exit_frame, else_frame)),
        )

    def _visit_With(self, node: ast.With, owner: str | None, walrus_owner: str | None) -> None:
        for item in node.items:
            self._visit(
                item.context_expr,
                owner,
                walrus_owner,
            )
            if item.optional_vars is not None:
                self._runtime_bind_target(
                    item.optional_vars,
                    owner,
                    walrus_owner,
                )
        for child in node.body:
            self._visit(child, owner, walrus_owner)

    def _visit_AsyncWith(self, node: ast.AsyncWith, owner: str | None, walrus_owner: str | None) -> None:
        for item in node.items:
            self._visit(
                item.context_expr,
                owner,
                walrus_owner,
            )
            if item.optional_vars is not None:
                self._runtime_bind_target(
                    item.optional_vars,
                    owner,
                    walrus_owner,
                )
        for child in node.body:
            self._visit(child, owner, walrus_owner)

    def _visit_Import(self, node: ast.Import, owner: str | None, _walrus_owner: str | None) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".", 1)[0]
            self._register_import_binding(alias, owner, local_name, alias.name if alias.asname is not None else alias.name.split(".", 1)[0], None)

    def _visit_ImportFrom(self, node: ast.ImportFrom, owner: str | None, _walrus_owner: str | None) -> None:
        module_name = _resolve_import_module(self.source_key, node.module, node.level)
        for alias in node.names:
            if alias.name == "*":
                self._replace_frame(owner, {})
                continue
            local_name = alias.asname or alias.name
            self._register_import_binding(alias, owner, local_name, module_name, alias.name)

    def _visit_Global(self, node: ast.Global, owner: str | None, _walrus_owner: str | None) -> None:
        for ordinal, name in enumerate(node.names):
            self._add("global_declaration", node, name, owner, ordinal=ordinal)
            self._blocked_names(owner).add(name)
            self._frame(owner).pop(name, None)

    def _visit_Nonlocal(self, node: ast.Nonlocal, owner: str | None, _walrus_owner: str | None) -> None:
        for ordinal, name in enumerate(node.names):
            self._add("nonlocal_declaration", node, name, owner, ordinal=ordinal)
            self._blocked_names(owner).add(name)
            self._frame(owner).pop(name, None)

    def _visit_Try(self, node: ast.Try, owner: str | None, walrus_owner: str | None) -> None:
        entry_frame = self._clone_frame(owner)
        normal_frame = self._visit_block_from_frame(
            node.body,
            owner,
            walrus_owner,
            entry_frame,
        )
        if node.orelse:
            normal_frame = self._visit_block_from_frame(
                node.orelse,
                owner,
                walrus_owner,
                normal_frame,
            )
        reachable_frames = [normal_frame]
        for handler in node.handlers:
            self._replace_frame(owner, entry_frame)
            self._visit(handler, owner, walrus_owner)
            reachable_frames.append(
                self._clone_frame(owner)
            )
        merged_frame = self._merge_frames(
            tuple(reachable_frames)
        )
        self._replace_frame(owner, merged_frame)
        for child in node.finalbody:
            self._visit(child, owner, walrus_owner)

    def _visit_ExceptHandler(self, node: ast.ExceptHandler, owner: str | None, walrus_owner: str | None) -> None:
        if node.type is not None:
            self._visit(node.type, owner, walrus_owner)
        alias_name = node.name if isinstance(node.name, str) else None
        if alias_name is not None:
            binding = ExtractedOccurrenceRef(
                self._add("binding", node, alias_name, owner)
            )
            if alias_name not in self._blocked_names(owner):
                source = self._occurrence(
                    "runtime_bound_local",
                    node,
                    alias_name,
                )
                self._frame(owner)[alias_name] = binding
                self._flow(
                    source=source,
                    target=binding,
                    relation=LineageRelation.ASSIGNS,
                    node=node,
                    resolution_kind=ResolutionKind.LEXICAL_EXACT,
                    confidence=LineageConfidence.CONFIRMED,
                )
        for child in node.body:
            self._visit(child, owner, walrus_owner)
        exit_frame = self._clone_frame(owner)
        if alias_name is not None:
            exit_frame.pop(alias_name, None)
        self._replace_frame(owner, exit_frame)

    def _visit_Match(self, node: ast.Match, owner: str | None, walrus_owner: str | None) -> None:
        self._visit(node.subject, owner, walrus_owner)
        entry_frame = self._clone_frame(owner)
        reachable_frames = [dict(entry_frame)]
        for case in node.cases:
            self._replace_frame(owner, entry_frame)
            self._visit(case.pattern, owner, walrus_owner)
            if case.guard is not None:
                self._visit(case.guard, owner, walrus_owner)
            for child in case.body:
                self._visit(child, owner, walrus_owner)
            reachable_frames.append(
                self._clone_frame(owner)
            )
        self._replace_frame(
            owner,
            self._merge_frames(tuple(reachable_frames)),
        )

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

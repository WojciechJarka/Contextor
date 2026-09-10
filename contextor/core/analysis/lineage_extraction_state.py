from __future__ import annotations

import ast
from dataclasses import dataclass, field

from contextor.core.domain.lineage_facts import ExtractedAnchorFact, ExtractedFlowFact, ExtractedOccurrenceRef, ParameterKind


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
class _CallableReturnRecord:
    node: ast.Return
    callable_info: _CallableInfo | None


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
    source: ExtractedOccurrenceRef
    node: ast.AST
    kind: str
    keyword_name: str | None


@dataclass(frozen=True)
class _CaptureRequest:
    load: ExtractedOccurrenceRef
    node: ast.Name
    owner: str
    name: str


@dataclass
class LineageExtractionState:
    anchors: list[ExtractedAnchorFact] = field(default_factory=list)
    flows: list[ExtractedFlowFact] = field(default_factory=list)
    _ids: set[str] = field(default_factory=set)
    _flow_ids: set[str] = field(default_factory=set)
    _occurrences: dict[tuple[str, int, str | None, int], ExtractedOccurrenceRef] = field(default_factory=dict)
    _bindings: dict[str | None, dict[str, ExtractedOccurrenceRef]] = field(default_factory=dict)
    _callables: dict[str | None, dict[str, _CallableInfo]] = field(default_factory=dict)
    _callables_by_anchor: dict[str, _CallableInfo] = field(default_factory=dict)
    _callables_by_binding: dict[str, _CallableInfo] = field(default_factory=dict)
    _callable_values: dict[str, _CallableInfo] = field(default_factory=dict)
    _parameters_by_local_id: dict[str, tuple[str, _ParameterInfo]] = field(default_factory=dict)
    _callback_parameters: set[str] = field(default_factory=set)
    _return_records: dict[str, list[_CallableReturnRecord]] = field(default_factory=dict)
    _callable_returns: dict[str, _CallableInfo] = field(default_factory=dict)
    _generator_owners: set[str] = field(default_factory=set)
    _imports: dict[str | None, dict[str, _ImportInfo]] = field(default_factory=dict)
    _blocked: dict[str | None, set[str]] = field(default_factory=dict)
    _active_comprehensions: list[_ActiveComprehension] = field(default_factory=list)
    _owner_parent: dict[str, str | None] = field(default_factory=dict)
    _owner_kind: dict[str, str] = field(default_factory=dict)
    _owner_nodes: dict[str, ast.AST] = field(default_factory=dict)
    _declared_locals: dict[str, set[str]] = field(default_factory=dict)
    _capture_requests: dict[str, _CaptureRequest] = field(default_factory=dict)
    _lexical_cells: dict[tuple[str, str], ExtractedOccurrenceRef] = field(default_factory=dict)

    def frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
        return self._bindings.setdefault(owner, {})

    def clone_frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
        return dict(self.frame(owner))

    def replace_frame(self, owner: str | None, frame: dict[str, ExtractedOccurrenceRef]) -> None:
        self._bindings[owner] = dict(frame)

    def merge_frames(self, frames: tuple[dict[str, ExtractedOccurrenceRef], ...]) -> dict[str, ExtractedOccurrenceRef]:
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

    def blocked_names(self, owner: str | None) -> set[str]:
        return self._blocked.setdefault(owner, set())

    def callable_frame(self, owner: str | None) -> dict[str, _CallableInfo]:
        return self._callables.setdefault(owner, {})

    def import_frame(self, owner: str | None) -> dict[str, _ImportInfo]:
        return self._imports.setdefault(owner, {})

    def register_parameter(self, owner: str, parameter: _ParameterInfo) -> None:
        candidate = (owner, parameter)
        existing = self._parameters_by_local_id.get(parameter.local_id)
        if existing is not None and existing != candidate:
            raise ValueError(f"Conflicting lineage parameter registration: {parameter.local_id}")
        self._parameters_by_local_id[parameter.local_id] = candidate

    def current_parameter(
        self,
        owner: str | None,
        occurrence: ExtractedOccurrenceRef | None,
    ) -> _ParameterInfo | None:
        if owner is None or occurrence is None:
            return None
        registered = self._parameters_by_local_id.get(occurrence.local_id)
        return registered[1] if registered is not None and registered[0] == owner else None

    def mark_callback_parameter(self, parameter: _ParameterInfo) -> None:
        self._callback_parameters.add(parameter.local_id)

    def record_callable_return(
        self,
        owner: str | None,
        node: ast.Return,
        callable_info: _CallableInfo | None,
    ) -> None:
        if owner is None or self._owner_kind.get(owner) not in {
            "function",
            "async_function",
            "lambda",
        }:
            return
        self._return_records.setdefault(owner, []).append(
            _CallableReturnRecord(node, callable_info)
        )

    def mark_generator(self, owner: str | None) -> None:
        if owner is not None and self._owner_kind.get(owner) in {
            "function",
            "async_function",
            "lambda",
        }:
            self._generator_owners.add(owner)

    def finalize_function_callable_return(
        self,
        owner: str,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        self._callable_returns.pop(owner, None)
        records = self._return_records.get(owner, [])
        if (
            self._owner_kind.get(owner) == "function"
            and owner not in self._generator_owners
            and len(records) == 1
            and node.body
            and records[0].node is node.body[-1]
            and records[0].callable_info is not None
        ):
            self._callable_returns[owner] = records[0].callable_info

    def publish_lambda_callable_return(
        self,
        owner: str,
        body_source: ExtractedOccurrenceRef,
    ) -> None:
        self._callable_returns.pop(owner, None)
        callable_info = self._callable_values.get(body_source.local_id)
        if (
            self._owner_kind.get(owner) == "lambda"
            and owner not in self._generator_owners
            and callable_info is not None
        ):
            self._callable_returns[owner] = callable_info

    def register_owner(
        self,
        owner_id: str,
        parent_id: str | None,
        kind: str,
        node: ast.AST,
    ) -> None:
        existing = (
            self._owner_parent.get(owner_id),
            self._owner_kind.get(owner_id),
            self._owner_nodes.get(owner_id),
        )
        candidate = (parent_id, kind, node)
        if owner_id in self._owner_kind:
            if existing != candidate:
                raise ValueError(f"Conflicting lineage owner registration: {owner_id}")
            return
        self._owner_parent[owner_id] = parent_id
        self._owner_kind[owner_id] = kind
        self._owner_nodes[owner_id] = node

    def declare_local(self, owner: str | None, name: str) -> None:
        if owner is None or name in self.blocked_names(owner):
            return
        self._declared_locals.setdefault(owner, set()).add(name)

    def request_capture(
        self,
        load: ExtractedOccurrenceRef,
        node: ast.Name,
        owner: str,
        name: str,
    ) -> None:
        request = _CaptureRequest(load, node, owner, name)
        existing = self._capture_requests.get(load.local_id)
        if existing is not None and existing != request:
            raise ValueError(f"Conflicting lineage capture request: {load.local_id}")
        self._capture_requests[load.local_id] = request

    def resolve_capture_owner(self, request_owner: str, name: str) -> str | None:
        if name in self.blocked_names(request_owner):
            return None
        if name in self._declared_locals.get(request_owner, set()):
            return None
        owner = self._owner_parent.get(request_owner)
        while owner is not None:
            kind = self._owner_kind.get(owner)
            if kind == "class":
                owner = self._owner_parent.get(owner)
                continue
            if kind == "comprehension":
                if name in self._declared_locals.get(owner, set()):
                    return None
                owner = self._owner_parent.get(owner)
                continue
            if kind in {"function", "async_function", "lambda"}:
                if name in self.blocked_names(owner):
                    return None
                if name in self._declared_locals.get(owner, set()):
                    return owner
                owner = self._owner_parent.get(owner)
                continue
            return None
        return None

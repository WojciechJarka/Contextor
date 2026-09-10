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
    _imports: dict[str | None, dict[str, _ImportInfo]] = field(default_factory=dict)
    _blocked: dict[str | None, set[str]] = field(default_factory=dict)
    _active_comprehensions: list[_ActiveComprehension] = field(default_factory=list)

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

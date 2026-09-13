from __future__ import annotations

import ast
from urllib.parse import quote

from contextor.core.analysis.lineage_extraction_contracts import _source_span, build_local_occurrence_id
from contextor.core.analysis.lineage_extraction_state import _CallableInfo, _ParameterInfo, LineageExtractionState
from contextor.core.domain.lineage_facts import ExtractedAnchorFact, ExtractedFlowFact, ExtractedOccurrenceRef, ExtractedSurfaceFact, ExtractedSymbolicKind, ExtractedSymbolicRef, LineageConfidence, LineageRelation, ResolutionKind, SurfaceDeclarationEvidence, SurfaceKind


def add_anchor(state: LineageExtractionState, paths: dict[int, str], kind: str, node: ast.AST, name: str | None, owner_local_id: str | None, *, ordinal: int = 0, local_kind: str | None = None) -> str:
    local_id = build_local_occurrence_id(local_kind or kind, paths[id(node)], name, ordinal=ordinal)
    if local_id in state._ids:
        raise ValueError(f"Duplicate lineage local id: {local_id}")
    state._ids.add(local_id)
    state.anchors.append(ExtractedAnchorFact(local_id=local_id, kind=kind, span=_source_span(node), owner_local_id=owner_local_id))
    return local_id


def occurrence(state: LineageExtractionState, paths: dict[int, str], kind: str, node: ast.AST, name: str | None = None, *, ordinal: int = 0) -> ExtractedOccurrenceRef:
    cache_key = (kind, id(node), name, ordinal)
    cached = state._occurrences.get(cache_key)
    if cached is not None:
        return cached
    local_id = build_local_occurrence_id(kind, paths[id(node)], name, ordinal=ordinal)
    if local_id in state._ids:
        raise ValueError(f"Duplicate lineage local id: {local_id}")
    state._ids.add(local_id)
    result = ExtractedOccurrenceRef(local_id)
    state._occurrences[cache_key] = result
    return result


def emit_flow(
    state: LineageExtractionState,
    paths: dict[int, str],
    *,
    source,
    target,
    relation: LineageRelation,
    node: ast.AST,
    resolution_kind: ResolutionKind,
    confidence: LineageConfidence,
    owner_local_id: str | None,
    ordinal: int = 0,
    dynamic_boundary: str | None = None,
) -> None:
    local_id = f"flow:v1:{relation.value}:{paths[id(node)]}:i:{ordinal}"
    if local_id in state._flow_ids:
        raise ValueError(f"Duplicate lineage flow id: {local_id}")
    state._flow_ids.add(local_id)
    state.flows.append(
        ExtractedFlowFact(
            local_id,
            source,
            target,
            relation,
            _source_span(node),
            resolution_kind,
            confidence,
            dynamic_boundary=dynamic_boundary,
            owner_local_id=owner_local_id,
        )
    )


def emit_surface(state: LineageExtractionState, paths: dict[int, str], *, kind: SurfaceKind, exposed, node: ast.AST, declared_name: str, resolution_kind: ResolutionKind, confidence: LineageConfidence, declaration_evidence: SurfaceDeclarationEvidence, ordinal: int = 0) -> None:
    local_id = f"surface:v1:{kind.value}:{paths[id(node)]}:i:{ordinal}:n:{quote(declared_name, safe='')}"
    if local_id in state._surface_ids:
        raise ValueError(f"Duplicate lineage surface id: {local_id}")
    state._surface_ids.add(local_id)
    state.surfaces.append(ExtractedSurfaceFact(local_id, kind, exposed, _source_span(node), resolution_kind, confidence, declared_name, declaration_evidence=declaration_evidence))


def parameter_symbolic(module_name: str, callable_symbol_name: str, parameter: _ParameterInfo) -> ExtractedSymbolicRef:
    return ExtractedSymbolicRef(ExtractedSymbolicKind.PARAMETER, module_name, callable_symbol_name, parameter.local_id)


def return_symbolic(module_name: str, callable_info: _CallableInfo) -> ExtractedSymbolicRef:
    return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, module_name, callable_info.name, callable_info.anchor_id)

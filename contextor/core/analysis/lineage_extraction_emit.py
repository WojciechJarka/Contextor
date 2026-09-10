from __future__ import annotations

import ast

from contextor.core.analysis.lineage_extraction_contracts import _source_span, build_local_occurrence_id
from contextor.core.analysis.lineage_extraction_state import _CallableInfo, _ParameterInfo, LineageExtractionState
from contextor.core.domain.lineage_facts import ExtractedAnchorFact, ExtractedFlowFact, ExtractedOccurrenceRef, ExtractedSymbolicKind, ExtractedSymbolicRef, LineageConfidence, LineageRelation, ResolutionKind


def add_anchor(state, paths, kind, node, name, owner_local_id, *, ordinal=0, local_kind=None):
    local_id = build_local_occurrence_id(local_kind or kind, paths[id(node)], name, ordinal=ordinal)
    if local_id in state._ids:
        raise ValueError(f"Duplicate lineage local id: {local_id}")
    state._ids.add(local_id)
    state.anchors.append(ExtractedAnchorFact(local_id=local_id, kind=kind, span=_source_span(node), owner_local_id=owner_local_id))
    return local_id


def occurrence(state, paths, kind, node, name=None, *, ordinal=0):
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


def emit_flow(state, paths, *, source, target, relation, node, resolution_kind, confidence, ordinal=0, dynamic_boundary=None):
    local_id = f"flow:v1:{relation.value}:{paths[id(node)]}:i:{ordinal}"
    if local_id in state._flow_ids: raise ValueError(f"Duplicate lineage flow id: {local_id}")
    state._flow_ids.add(local_id)
    state.flows.append(ExtractedFlowFact(local_id, source, target, relation, _source_span(node), resolution_kind, confidence, dynamic_boundary=dynamic_boundary))


def parameter_symbolic(module_name, callable_symbol_name, parameter):
    return ExtractedSymbolicRef(ExtractedSymbolicKind.PARAMETER, module_name, callable_symbol_name, parameter.local_id)


def return_symbolic(module_name, callable_info):
    return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, module_name, callable_info.name, callable_info.anchor_id)

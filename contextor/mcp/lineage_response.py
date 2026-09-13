from __future__ import annotations

from dataclasses import dataclass

from contextor.core.domain.lineage_facts import MaterializedOccurrenceRef, MaterializedSymbolicRef, SemanticEndpoint
from contextor.core.lineage_query.service import (
    SYMBOL_LINEAGE_SECTION_ORDER,
    LineageFlowMatch, LineageSurfaceMatch, SelectedSymbolLineageFacts, TargetInterfaceFacts,
)
from contextor.mcp.representation import serialized_json_bytes


SYMBOL_LINEAGE_MODES = ("auto", "preview", "fetch")


@dataclass(frozen=True)
class SymbolLineageResponsePlan:
    mode: str
    candidate_sections: tuple[str, ...]
    include_payload: bool
    requires_size_decision: bool


def plan_symbol_lineage_response(*, mode: str = "auto", sections: tuple[str, ...] | None = None) -> SymbolLineageResponsePlan:
    if not isinstance(mode, str):
        raise TypeError("mode must be a string.")
    normalized_mode = mode.strip().lower()
    if normalized_mode not in SYMBOL_LINEAGE_MODES:
        raise ValueError("mode must be 'auto', 'preview', or 'fetch'.")
    if sections is not None:
        if not isinstance(sections, tuple):
            raise TypeError("sections must be a tuple of section names.")
        if any(not isinstance(section, str) or not section for section in sections):
            raise ValueError("sections must contain non-empty strings.")
        if len(set(sections)) != len(sections):
            raise ValueError("sections must not contain duplicates.")
        unknown = tuple(sorted(set(sections) - set(SYMBOL_LINEAGE_SECTION_ORDER)))
        if unknown:
            raise ValueError("Unknown symbol lineage sections: " + ", ".join(unknown))
    if normalized_mode in {"auto", "preview"}:
        if sections is not None:
            raise ValueError(f"{normalized_mode} mode does not accept an explicit section selection.")
        return SymbolLineageResponsePlan(
            normalized_mode, SYMBOL_LINEAGE_SECTION_ORDER,
            normalized_mode == "auto", normalized_mode == "auto",
        )
    if not sections:
        raise ValueError("fetch mode requires at least one section.")
    requested = set(sections)
    return SymbolLineageResponsePlan(
        "fetch",
        tuple(s for s in SYMBOL_LINEAGE_SECTION_ORDER if s in requested),
        True, False,
    )


def _span_payload(span) -> dict:
    return {"start": [span.start_line, span.start_column], "end": [span.end_line, span.end_column]}


def _endpoint_payload(endpoint) -> dict:
    if isinstance(endpoint, MaterializedOccurrenceRef):
        return {"kind": "occurrence", "source": endpoint.source_key, "local_id": endpoint.local_id}
    if isinstance(endpoint, MaterializedSymbolicRef):
        result = {"kind": "symbolic", "symbol_kind": endpoint.kind.value, "qualified_name": f"{endpoint.module_name}::{endpoint.symbol_name}"}
        if endpoint.source_local_id is not None: result["source_local_id"] = endpoint.source_local_id
        return result
    if isinstance(endpoint, SemanticEndpoint):
        result = {"kind": "semantic", "owner_id": endpoint.owner_id}
        if endpoint.slot is not None: result["slot"] = endpoint.slot
        return result
    raise TypeError("Unsupported canonical lineage endpoint.")


def _flow_payload(match: LineageFlowMatch) -> dict:
    flow = match.flow
    result = {"id": flow.local_id, "relation": flow.relation.value, "source": _endpoint_payload(flow.source), "target": _endpoint_payload(flow.target), "resolution": flow.resolution_kind.value, "confidence": flow.confidence.value, "evidence": {"source": match.source_key, "span": _span_payload(flow.evidence)}}
    if flow.dynamic_boundary is not None: result["dynamic_boundary"] = flow.dynamic_boundary
    if flow.provider is not None: result["provider"] = {"provider_id": flow.provider.provider_id, "provider_version": flow.provider.provider_version}
    return result


def _surface_payload(match: LineageSurfaceMatch) -> dict:
    surface = match.surface
    result = {"id": surface.local_id, "kind": surface.kind.value, "declared_name": surface.declared_name, "exposed": _endpoint_payload(surface.exposed), "resolution": surface.resolution_kind.value, "confidence": surface.confidence.value, "evidence": {"source": match.source_key, "span": _span_payload(surface.evidence)}}
    if surface.dynamic_boundary is not None: result["dynamic_boundary"] = surface.dynamic_boundary
    if surface.provider is not None: result["provider"] = {"provider_id": surface.provider.provider_id, "provider_version": surface.provider.provider_version}
    if surface.declaration_evidence is not None: result["declaration_evidence"] = surface.declaration_evidence.value
    return result


def _interface_payload(interface: TargetInterfaceFacts) -> dict:
    return {"callable_state": interface.callable_state, "signature_digest": interface.signature_digest, "return_slot": interface.return_slot, "parameters": [{"slot": p.slot, "kind": p.kind.value, "ordinal": p.ordinal, "name": p.name, "has_default": p.has_default, "default_flows": [_flow_payload(m) for m in p.default_flows]} for p in interface.parameter_slots], "definitions": [{"source": d.source_key, "local_id": d.binding.reference.local_id} for d in interface.definitions], "complete": interface.complete}


def _section_payloads(selected: SelectedSymbolLineageFacts) -> dict[str, object]:
    values: dict[str, object] = {}
    if selected.interface is not None: values["interface"] = _interface_payload(selected.interface)
    if selected.connections is not None: values["connections"] = {"incoming": [_flow_payload(m) for m in selected.connections.incoming], "outgoing": [_flow_payload(m) for m in selected.connections.outgoing]}
    for name in ("bindings", "parameter_flows", "calls_interfaces", "returns", "state", "callbacks", "unresolved_dynamic_boundaries"):
        value = getattr(selected, name)
        if value is not None: values[name] = [_flow_payload(m) for m in value]
    if selected.surfaces is not None: values["surfaces"] = {"flows": [_flow_payload(m) for m in selected.surfaces.flows], "facts": [_surface_payload(m) for m in selected.surfaces.facts]}
    return {name: values[name] for name in selected.selected_sections}


def build_symbol_lineage_payload(selected: SelectedSymbolLineageFacts) -> dict:
    if not isinstance(selected, SelectedSymbolLineageFacts): raise TypeError("selected must be SelectedSymbolLineageFacts.")
    target = selected.target
    return {"status": "resolved", "target": {"artifact_id": target.artifact_id, "qualified_name": target.qualified_name, "module": target.module_name, "symbol": target.symbol_name, "resolution": target.resolution}, "selected_sections": list(selected.selected_sections), "complete": selected.complete, "metadata_consistent": selected.metadata_consistent, "scope_state": selected.facts.scope_state, "sections": _section_payloads(selected)}


def build_symbol_lineage_preview(selected: SelectedSymbolLineageFacts) -> dict:
    payload = build_symbol_lineage_payload(selected)
    return {"status": "resolved", "mode": "preview", "target": payload["target"], "available_sections": list(selected.selected_sections), "complete": selected.complete, "metadata_consistent": selected.metadata_consistent, "scope_state": selected.facts.scope_state, "candidate_response_bytes": serialized_json_bytes(payload), "section_sizes": {name: {"payload_bytes": serialized_json_bytes(value)} for name, value in payload["sections"].items()}}

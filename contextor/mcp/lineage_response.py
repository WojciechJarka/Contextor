from __future__ import annotations

import json
from dataclasses import dataclass
from collections.abc import Mapping

from contextor.core.domain.lineage_facts import MaterializedOccurrenceRef, MaterializedSymbolicRef, SemanticEndpoint
from contextor.core.lineage_query.service import (
    SYMBOL_LINEAGE_SECTION_ORDER,
    LineageFlowMatch, LineageSurfaceMatch, SelectedSymbolLineageFacts, TargetInterfaceFacts,
)
from contextor.mcp import representation as mcp_rep
from contextor.mcp.output_guard import (
    guard_large_output,
)


SYMBOL_LINEAGE_MODES = ("auto", "preview", "fetch")
SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES = 5120


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


def build_symbol_lineage_payload(
    selected: SelectedSymbolLineageFacts,
    *,
    state_freshness: Mapping[str, object] | None = None,
) -> dict:
    if not isinstance(
        selected,
        SelectedSymbolLineageFacts,
    ):
        raise TypeError(
            "selected must be SelectedSymbolLineageFacts."
        )
    if (
        state_freshness is not None
        and not isinstance(state_freshness, Mapping)
    ):
        raise TypeError(
            "state_freshness must be a mapping."
        )

    target = selected.target
    result = {
        "status": "resolved",
        "target": {
            "artifact_id": target.artifact_id,
            "qualified_name": target.qualified_name,
            "module": target.module_name,
            "symbol": target.symbol_name,
            "resolution": target.resolution,
        },
        "selected_sections": list(
            selected.selected_sections
        ),
        "complete": selected.complete,
        "metadata_consistent": (
            selected.metadata_consistent
        ),
        "scope_state": selected.facts.scope_state,
    }

    if state_freshness is not None:
        result["state_freshness"] = dict(
            state_freshness
        )

    result["sections"] = _section_payloads(
        selected
    )
    return result


def build_symbol_lineage_preview(
    selected: SelectedSymbolLineageFacts,
    *,
    state_freshness: Mapping[str, object] | None = None,
) -> dict:
    payload = build_symbol_lineage_payload(
        selected,
        state_freshness=state_freshness,
    )
    result = {
        "status": "resolved",
        "mode": "preview",
        "target": payload["target"],
        "available_sections": list(
            selected.selected_sections
        ),
        "complete": selected.complete,
        "metadata_consistent": (
            selected.metadata_consistent
        ),
        "scope_state": selected.facts.scope_state,
        "candidate_response_bytes": (
            mcp_rep.serialized_json_bytes(
                payload
            )
        ),
        "section_sizes": {
            name: {
                "payload_bytes": (
                    mcp_rep.serialized_json_bytes(
                        value
                    )
                ),
            }
            for name, value
            in payload["sections"].items()
        },
    }
    if "state_freshness" in payload:
        result["state_freshness"] = payload[
            "state_freshness"
        ]
    return result


def _semantic_owner_ids(value: object) -> tuple[str, ...]:
    owners: set[str] = set()
    def visit(item: object) -> None:
        if isinstance(item, dict):
            if item.get("kind") == "semantic" and isinstance(item.get("owner_id"), str): owners.add(item["owner_id"])
            for child in item.values(): visit(child)
        elif isinstance(item, list):
            for child in item: visit(child)
    visit(value)
    return tuple(sorted(owners))


def _named_semantic_owners(value: object, owner_names: Mapping[str, str]) -> object:
    if isinstance(value, list): return [_named_semantic_owners(item, owner_names) for item in value]
    if not isinstance(value, dict): return value
    if value.get("kind") == "semantic" and isinstance(value.get("owner_id"), str):
        result: dict[str, object] = {"kind": "semantic", "owner": owner_names[value["owner_id"]]}
        if "slot" in value: result["slot"] = value["slot"]
        return result
    return {key: _named_semantic_owners(item, owner_names) for key, item in value.items()}


def build_symbol_lineage_represented_payload(
    selected: SelectedSymbolLineageFacts,
    *,
    representation: str = "auto",
    artifact_names: Mapping[str, str] | None = None,
    state_freshness: Mapping[str, object] | None = None,
) -> dict:
    if not isinstance(selected, SelectedSymbolLineageFacts): raise TypeError("selected must be SelectedSymbolLineageFacts.")
    if not isinstance(representation, str): raise TypeError("representation must be a string.")
    requested = representation.strip().lower()
    if not mcp_rep.is_supported_representation(requested): raise ValueError("representation must be 'auto', 'indexed', or 'named'.")
    if artifact_names is not None:
        if not isinstance(artifact_names, Mapping): raise TypeError("artifact_names must be a mapping.")
        if any(not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in artifact_names.items()): raise ValueError("artifact_names must map non-empty artifact IDs to non-empty names.")
    base = build_symbol_lineage_payload(
        selected,
        state_freshness=state_freshness,
    )
    missing = tuple(owner for owner in _semantic_owner_ids(base) if artifact_names is None or owner not in artifact_names)
    indexed = dict(base); indexed.update({"representation": "indexed", "requested_representation": requested, "resolver": {"index_kind": "artifact", "resolve_via": "lookup_index_entries"}})
    indexed_bytes = mcp_rep.serialized_json_bytes(indexed)
    named = None if missing else _named_semantic_owners(base, artifact_names or {})
    if named is not None:
        assert isinstance(named, dict); named.update({"representation": "named", "requested_representation": requested})
    named_bytes = mcp_rep.serialized_json_bytes(named) if named is not None else None
    if requested == "named":
        if named is None: raise ValueError("Named lineage representation unavailable for semantic owners: " + ", ".join(missing))
        result, reason = named, "explicit_named"
    elif requested == "indexed": result, reason = indexed, "explicit_indexed"
    elif named is None: result, reason = indexed, "auto_indexed_named_identity_unavailable"
    elif named_bytes - indexed_bytes >= mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED: result, reason = indexed, "auto_indexed_material_saving"
    else: result, reason = named, "auto_named"
    decision: dict[str, object] = {"selected": result["representation"], "reason": reason, "indexed_candidate_bytes": indexed_bytes, "named_candidate_bytes": named_bytes, "minimum_auto_saving_bytes": mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED}
    if named_bytes is not None: decision["bytes_saved_by_indexed"] = named_bytes - indexed_bytes
    if missing: decision["missing_named_owners"] = list(missing)
    result["representation_decision"] = decision
    return result


def _represented_response_candidate(
    selected: SelectedSymbolLineageFacts,
    *,
    mode: str,
    representation: str,
    artifact_names: Mapping[str, str] | None,
    state_freshness: Mapping[str, object] | None,
) -> dict:
    result = build_symbol_lineage_represented_payload(
        selected,
        representation=representation,
        artifact_names=artifact_names,
        state_freshness=state_freshness,
    )
    result["mode"] = mode
    return result


def build_symbol_lineage_represented_preview(
    selected: SelectedSymbolLineageFacts,
    *,
    representation: str = "auto",
    artifact_names: Mapping[str, str] | None = None,
    state_freshness: Mapping[str, object] | None = None,
    candidate_mode: str = "fetch",
) -> dict:
    if candidate_mode not in {"auto", "fetch"}:
        raise ValueError(
            "candidate_mode must be 'auto' or 'fetch'."
        )

    candidate = _represented_response_candidate(
        selected,
        mode=candidate_mode,
        representation=representation,
        artifact_names=artifact_names,
        state_freshness=state_freshness,
    )
    sections = candidate["sections"]

    result = {
        "status": "resolved",
        "mode": "preview",
        "target": candidate["target"],
        "available_sections": list(
            selected.selected_sections
        ),
        "complete": selected.complete,
        "metadata_consistent": (
            selected.metadata_consistent
        ),
        "scope_state": selected.facts.scope_state,
        "representation": candidate[
            "representation"
        ],
        "requested_representation": candidate[
            "requested_representation"
        ],
        "representation_decision": candidate[
            "representation_decision"
        ],
        "candidate_response_bytes": (
            mcp_rep.serialized_json_bytes(
                candidate
            )
        ),
        "section_sizes": {
            name: {
                "payload_bytes": (
                    mcp_rep.serialized_json_bytes(
                        value
                    )
                ),
            }
            for name, value in sections.items()
        },
    }

    if "state_freshness" in candidate:
        result["state_freshness"] = candidate[
            "state_freshness"
        ]

    if "resolver" in candidate:
        result["resolver"] = candidate["resolver"]

    return result


def render_symbol_lineage_response(
    selected: SelectedSymbolLineageFacts,
    *,
    mode: str = "auto",
    sections: tuple[str, ...] | None = None,
    representation: str = "auto",
    artifact_names: Mapping[str, str] | None = None,
    state_freshness: Mapping[str, object] | None = None,
    allow_large_output: bool = False,
) -> str:
    if not isinstance(
        selected,
        SelectedSymbolLineageFacts,
    ):
        raise TypeError(
            "selected must be SelectedSymbolLineageFacts."
        )
    if not isinstance(allow_large_output, bool):
        raise TypeError(
            "allow_large_output must be a boolean."
        )

    plan = plan_symbol_lineage_response(
        mode=mode,
        sections=sections,
    )

    if (
        selected.selected_sections
        != plan.candidate_sections
    ):
        raise ValueError(
            "selected sections do not match "
            "the response plan."
        )

    if plan.mode == "preview":
        result = build_symbol_lineage_represented_preview(
            selected,
            representation=representation,
            artifact_names=artifact_names,
            state_freshness=state_freshness,
            candidate_mode="fetch",
        )
        serialized = json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
        return guard_large_output(
            serialized,
            allow_large_output=(
                allow_large_output
            ),
            requested_count=len(
                selected.selected_sections
            ),
            retry_instruction=(
                "Retry preview with "
                "allow_large_output=true."
            ),
        )

    candidate = _represented_response_candidate(
        selected,
        mode=plan.mode,
        representation=representation,
        artifact_names=artifact_names,
        state_freshness=state_freshness,
    )
    candidate_bytes = (
        mcp_rep.serialized_json_bytes(
            candidate
        )
    )

    if (
        plan.mode == "auto"
        and candidate_bytes
        > SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES
    ):
        preview = (
            build_symbol_lineage_represented_preview(
                selected,
                representation=representation,
                artifact_names=artifact_names,
                state_freshness=state_freshness,
                candidate_mode="auto",
            )
        )
        preview["auto_fetch"] = {
            "threshold_bytes": (
                SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES
            ),
            "candidate_response_bytes": (
                candidate_bytes
            ),
            "decision": "preview",
        }
        serialized = json.dumps(
            preview,
            indent=2,
            ensure_ascii=False,
        )
        return guard_large_output(
            serialized,
            allow_large_output=(
                allow_large_output
            ),
            requested_count=len(
                selected.selected_sections
            ),
            retry_instruction=(
                "Retry preview with "
                "allow_large_output=true."
            ),
        )

    serialized = json.dumps(
        candidate,
        indent=2,
        ensure_ascii=False,
    )

    return guard_large_output(
        serialized,
        allow_large_output=allow_large_output,
        requested_count=len(
            selected.selected_sections
        ),
        retry_instruction=(
            "Retry with fewer lineage sections "
            "or allow_large_output=true."
        ),
    )

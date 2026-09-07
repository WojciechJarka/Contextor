import json
from pathlib import Path
from typing import Any

from contextor.core.analysis.state_manager import (
    artifact_consumption_is_fresh,
    module_current_truth,
)
from contextor.core.report_query import registry_maps_from_state
from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.output_guard import guard_large_output


_FAMILIES = ("artifact_consumption", "syntax_diagnostics", "symbol_calls")
_DIRECTIONS = ("upstream", "downstream", "both")
_MAX_DEPTH = 4
_STORE_ID = "store:live_snapshot"
_UNAVAILABLE_EDGE_TYPES = {"READS", "UPDATES", "PERSISTS", "HYDRATES", "PROJECTS", "EXPOSES"}
_STATUS_RANK = {"fresh": 0, "partial": 1, "stale": 2, "unavailable": 3}


def _symbol(module: str, name: str) -> str:
    return f"{module}::{name}"


_SPECS: dict[str, dict[str, Any]] = {
    "artifact_consumption": {
        "state_field": "artifact_consumption",
        "state_state_field": "artifact_consumption_state",
        "branches": (
            {
                "input": "raw_artifact_consumer_facts",
                "producer": _symbol(
                    "contextor.core.analysis.state_manager",
                    "build_canonical_artifact_consumption",
                ),
                "branch": "full",
                "input_kind": "indexed_artifact_consumer_facts",
            },
            {
                "input": "module_usage_facts",
                "producer": _symbol(
                    "contextor.core.analysis.incremental.plan_executor",
                    "_rebuild_consumer_slice",
                ),
                "branch": "incremental",
                "input_kind": "canonical_module_usage_facts",
                "output": "artifact_consumption_consumer_slice",
            },
        ),
        "updates": (
            _symbol(
                "contextor.core.analysis.incremental.engine",
                "IncrementalAnalysisEngine._apply_delta_and_commit",
            ),
        ),
        "materializers": (
            _symbol(
                "contextor.core.api.facade",
                "ContextorFacade.analyze_project",
            ),
        ),
        "installers": (
            (
                _symbol(
                    "contextor.core.api.facade",
                    "ContextorFacade.analyze_project",
                ),
                "full",
            ),
            (
                _symbol(
                    "contextor.core.analysis.incremental.engine",
                    "IncrementalAnalysisEngine._apply_delta_and_commit",
                ),
                "incremental",
            ),
        ),
        "projections": (
            (
                "get_artifact_blast_radius",
                _symbol(
                    "contextor.mcp.tools.get_artifact_blast_radius",
                    "get_artifact_blast_radius",
                ),
            ),
            (
                "get_module_blast_radius",
                _symbol(
                    "contextor.mcp.tools.get_module_blast_radius",
                    "get_module_blast_radius",
                ),
            ),
        ),
    },
    "syntax_diagnostics": {
        "state_field": "syntax_diagnostics_by_path",
        "state_state_field": "syntax_diagnostics_state",
        "branches": (
            {
                "input": "repository_index_parse_results",
                "producer": _symbol(
                    "contextor.core.analysis.state_manager",
                    "build_syntax_diagnostics_from_index",
                ),
                "branch": "full",
                "input_kind": "repository_index_parse_and_skipped_facts",
                "output": "syntax_diagnostic_facts",
            },
            {
                "input": "prepared_source_update",
                "producer": _symbol(
                    "contextor.core.analysis.incremental.engine",
                    "IncrementalAnalysisEngine._commit_syntax_candidate",
                ),
                "branch": "incremental",
                "input_kind": "prepared_incremental_syntax_candidate",
            },
        ),
        "updates": (
            _symbol(
                "contextor.core.analysis.incremental.engine",
                "IncrementalAnalysisEngine._commit_syntax_candidate",
            ),
        ),
        "materializers": (
            _symbol(
                "contextor.core.api.facade",
                "ContextorFacade.analyze_project",
            ),
        ),
        "installers": (
            (
                _symbol(
                    "contextor.core.api.facade",
                    "ContextorFacade.analyze_project",
                ),
                "full",
            ),
        ),
        "projections": (
            (
                "get_file_edit_context",
                _symbol(
                    "contextor.mcp.tools.get_file_edit_context",
                    "get_file_edit_context",
                ),
            ),
        ),
    },
    "symbol_calls": {
        "state_field": "module_usages[*].symbol_calls",
        "state_state_field": "module_usages[*].symbol_calls_materialized",
        "branches": (
            {
                "input": "reference_extraction_facts",
                "producer": _symbol(
                    "contextor.core.reference.engine",
                    "extract_module_usage_facts",
                ),
                "branch": "extraction",
                "input_kind": "canonical_reference_extraction_input",
                "output": "module_usage_facts",
            },
            {
                "input": "full_baseline_reuse",
                "producer": _symbol(
                    "contextor.core.reference.module_usage_reuse",
                    "build_module_usage_baseline_with_reuse",
                ),
                "branch": "full_baseline_reuse",
                "input_kind": "current_module_usage_or_extraction_facts",
                "output": "module_usage_baseline",
            },
            {
                "input": "incremental_prepared_usage",
                "producer": _symbol(
                    "contextor.core.analysis.incremental.preparation",
                    "prepare_source_update",
                ),
                "branch": "incremental_prepared_usage",
                "input_kind": "prepared_incremental_ast_usage_delta",
                "output": "prepared_module_usage",
            },
            {
                "input": "materialization_backfill",
                "producer": _symbol(
                    "contextor.core.analysis.incremental.materialization",
                    "ensure_module_usages",
                ),
                "branch": "ensure_module_usages_backfill",
                "input_kind": "missing_or_unmaterialized_module_usage_facts",
            },
        ),
        "updates": (
            _symbol(
                "contextor.core.analysis.incremental.engine",
                "IncrementalAnalysisEngine._apply_delta_and_commit",
            ),
            _symbol(
                "contextor.core.analysis.incremental.materialization",
                "ensure_module_usages",
            ),
        ),
        "materializers": (
            _symbol(
                "contextor.core.api.facade",
                "ContextorFacade.analyze_project",
            ),
        ),
        "installers": (
            (
                _symbol(
                    "contextor.core.api.facade",
                    "ContextorFacade.analyze_project",
                ),
                "full_baseline_reuse",
            ),
            (
                _symbol(
                    "contextor.core.analysis.incremental.engine",
                    "IncrementalAnalysisEngine._apply_delta_and_commit",
                ),
                "incremental_prepared_usage",
            ),
        ),
        "projections": (
            (
                "get_symbol_call_context",
                _symbol(
                    "contextor.mcp.tools.get_symbol_call_context",
                    "get_symbol_call_context",
                ),
            ),
        ),
    },
}


def _state_id(spec: dict[str, Any]) -> str:
    return f"state:RepositoryAnalysisState.{spec['state_field']}"


def _data_family_id(name: str) -> str:
    return f"data_family:{name}"


def _add_node(nodes: dict[str, dict[str, Any]], node: dict[str, Any]) -> str:
    node_id = str(node["id"])
    nodes.setdefault(node_id, node)
    return node_id


def _add_data_family_node(
    nodes: dict[str, dict[str, Any]],
    name: str,
    *,
    anchor: bool = False,
) -> str:
    node_id = f"family:{name}" if anchor else _data_family_id(name)
    return _add_node(
        nodes,
        {
            "id": node_id,
            "type": "data_family",
            "name": name,
            **({"role": "anchor"} if anchor else {}),
        },
    )


def _add_symbol_node(
    nodes: dict[str, dict[str, Any]],
    qualified_name: str,
    artifact_path_to_id: dict[str, Any],
    module_path_to_id: dict[str, Any],
    identity_gaps: dict[str, dict[str, Any]],
) -> str:
    active_id = artifact_path_to_id.get(qualified_name)
    module_name = qualified_name.split("::", 1)[0]
    if active_id:
        node_id = f"symbol:{active_id}"
    else:
        node_id = f"symbol:{qualified_name}"
        identity_gaps.setdefault(
            node_id,
            {
                "from": node_id,
                "to": None,
                "expected_edge": "ACTIVE_ID_RESOLUTION",
                "status": "unresolved",
                "reason": "Active artifact identity unavailable; stable qualified name retained.",
                "kind": "identity_resolution",
                "qualified_name": qualified_name,
            },
        )
    node: dict[str, Any] = {
        "id": node_id,
        "type": "symbol",
        "name": qualified_name,
        "qualified_name": qualified_name,
        "module": module_name,
    }
    if active_id:
        node["artifact_id"] = str(active_id)
    module_id = module_path_to_id.get(module_name)
    if module_id:
        node["module_id"] = str(module_id)
    _add_node(nodes, node)
    return node_id


def _add_state_node(nodes: dict[str, dict[str, Any]], spec: dict[str, Any]) -> str:
    state_id = _state_id(spec)
    _add_node(
        nodes,
        {
            "id": state_id,
            "type": "canonical_state_field",
            "name": spec["state_field"],
            "state_owner": "RepositoryAnalysisState",
            "state_field": spec["state_field"],
            "family_state_field": spec["state_state_field"],
        },
    )
    return state_id


def _add_tool_node(nodes: dict[str, dict[str, Any]], tool_name: str) -> str:
    return _add_node(
        nodes,
        {
            "id": f"tool:{tool_name}",
            "type": "public_projection",
            "name": tool_name,
            "tool": tool_name,
        },
    )


def _evidence(kind: str, **values: Any) -> dict[str, Any]:
    result = {"kind": kind}
    result.update({key: value for key, value in values.items() if value is not None})
    return result


def _add_edge(
    edges: dict[tuple[str, str, str], dict[str, Any]],
    source: str,
    target: str,
    edge_type: str,
    evidence: dict[str, Any],
    *,
    via: str | None = None,
) -> None:
    edge = {
        "source": source,
        "target": target,
        "type": edge_type,
        "confidence": "confirmed",
        "evidence": evidence,
    }
    if via is not None:
        edge["via"] = via
    edges.setdefault((source, target, edge_type), edge)


def _read_registry_maps(root: Path, engine: Any) -> tuple[dict, dict, dict, dict]:
    registry = getattr(engine, "registry", None)
    read_transaction = getattr(registry, "read_transaction", None)
    if (
        (
            getattr(engine, "provenance", None) == "live"
            or getattr(getattr(engine, "state", None), "provenance", None) == "live"
        )
        and registry is not None
        and callable(read_transaction)
        and hasattr(registry, "_state")
    ):
        try:
            with read_transaction():
                return registry_maps_from_state(registry._state)
        except Exception:
            pass
    try:
        return query_helpers.read_registries(root)
    except Exception:
        return {}, {}, {}, {}


def _build_contract(
    family: str,
    spec: dict[str, Any],
    registry_maps: tuple[dict, dict, dict, dict],
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str, str], dict[str, Any]], dict[str, dict[str, Any]]]:
    module_path_to_id, _module_id_to_path, artifact_path_to_id, _artifact_id_to_path = registry_maps
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    identity_gaps: dict[str, dict[str, Any]] = {}

    anchor_id = _add_data_family_node(nodes, family, anchor=True)
    state_id = _add_state_node(nodes, spec)
    _add_node(
        nodes,
        {
            "id": _STORE_ID,
            "type": "persistence_store",
            "name": "live_snapshot",
            "store": "live_snapshot",
        },
    )

    for branch in spec["branches"]:
        input_id = _add_data_family_node(nodes, branch["input"])
        producer_id = _add_symbol_node(
            nodes,
            branch["producer"],
            artifact_path_to_id,
            module_path_to_id,
            identity_gaps,
        )
        _add_edge(
            edges,
            input_id,
            producer_id,
            "READS",
            _evidence(
                branch["input_kind"],
                qualified_symbol=branch["producer"],
                branch=branch["branch"],
            ),
        )
        if branch.get("output"):
            output_id = _add_data_family_node(nodes, branch["output"])
            _add_edge(
                edges,
                producer_id,
                output_id,
                "PRODUCES",
                _evidence(
                    "explicit_materialized_fact_output",
                    qualified_symbol=branch["producer"],
                    branch=branch["branch"],
                ),
            )
            _add_edge(
                edges,
                output_id,
                anchor_id,
                "TRANSFORMS",
                _evidence(
                    "named_field_projection",
                    field="symbol_calls",
                    branch=branch["branch"],
                ),
                via=branch["producer"],
            )
        else:
            _add_edge(
                edges,
                producer_id,
                anchor_id,
                "PRODUCES",
                _evidence(
                    "explicit_producer",
                    qualified_symbol=branch["producer"],
                    branch=branch["branch"],
                ),
            )

    for materializer in spec["materializers"]:
        materializer_id = _add_symbol_node(
            nodes,
            materializer,
            artifact_path_to_id,
            module_path_to_id,
            identity_gaps,
        )
        _add_edge(
            edges,
            materializer_id,
            state_id,
            "MATERIALIZES",
            _evidence(
                "canonical_state_installation_owner",
                qualified_symbol=materializer,
                canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
            ),
        )

    for updater in spec["updates"]:
        updater_id = _add_symbol_node(
            nodes,
            updater,
            artifact_path_to_id,
            module_path_to_id,
            identity_gaps,
        )
        _add_edge(
            edges,
            updater_id,
            state_id,
            "UPDATES",
            _evidence(
                "incremental_state_installation_owner",
                qualified_symbol=updater,
                canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
            ),
        )

    for installer, branch_name in spec.get("installers", ()):
        installer_id = _add_symbol_node(
            nodes,
            installer,
            artifact_path_to_id,
            module_path_to_id,
            identity_gaps,
        )
        _add_edge(
            edges,
            anchor_id,
            installer_id,
            "READS",
            _evidence(
                "canonical_installation_input",
                qualified_symbol=installer,
                branch=branch_name,
                canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
            ),
        )

    persistence_via = _symbol("contextor.core.analysis.state_manager", "save_engine_state")
    _add_edge(
        edges,
        state_id,
        _STORE_ID,
        "PERSISTS",
        _evidence(
            "complete_engine_snapshot",
            canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
        ),
        via=persistence_via,
    )
    hydration_via = _symbol(
        "contextor.core.live_state.hydration", "hydrate_repository_engine"
    )
    _add_edge(
        edges,
        _STORE_ID,
        state_id,
        "HYDRATES",
        _evidence(
            "complete_engine_snapshot_load",
            canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
        ),
        via=hydration_via,
    )

    for tool_name, projection in spec["projections"]:
        tool_id = _add_tool_node(nodes, tool_name)
        projection_id = _add_symbol_node(
            nodes,
            projection,
            artifact_path_to_id,
            module_path_to_id,
            identity_gaps,
        )
        _add_edge(
            edges,
            state_id,
            projection_id,
            "READS",
            _evidence(
                "canonical_projection_read",
                qualified_symbol=projection,
                canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
            ),
        )
        _add_edge(
            edges,
            state_id,
            tool_id,
            "PROJECTS",
            _evidence(
                "public_projection",
                qualified_symbol=projection,
                canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
            ),
        )
        _add_edge(
            edges,
            projection_id,
            tool_id,
            "EXPOSES",
            _evidence(
                "explicit_mcp_registration",
                qualified_symbol=projection,
                registration_owner="contextor.mcp_server::register_mcp_tool",
            ),
        )

    return nodes, edges, identity_gaps


def _symbol_flag(value: Any, name: str) -> bool:
    if isinstance(value, dict):
        return bool(value.get(name, False))
    return bool(getattr(value, name, False))


def _coverage(state: Any) -> dict[str, int]:
    modules = getattr(state, "modules", {}) or {}
    usages = getattr(state, "module_usages", {}) or {}
    module_names = sorted(str(name) for name in modules) if isinstance(modules, dict) else []
    canonical_module_count = len(module_names)
    calls_count = 0
    evidence_count = 0
    stale_module_count = 0
    for module_name in module_names:
        usage = usages.get(module_name) if isinstance(usages, dict) else None
        calls_count += int(_symbol_flag(usage, "symbol_calls_materialized"))
        evidence_count += int(_symbol_flag(usage, "reference_evidence_materialized"))
        if not module_current_truth(state, module_name)["available"]:
            stale_module_count += 1
    return {
        "canonical_module_count": canonical_module_count,
        "symbol_calls_materialized_count": calls_count,
        "reference_evidence_materialized_count": evidence_count,
        "missing_symbol_calls_materialization_count": canonical_module_count - calls_count,
        "missing_reference_evidence_count": canonical_module_count - evidence_count,
        "stale_module_count": stale_module_count,
    }


def _fallback_freshness(state: Any, engine: Any) -> dict[str, Any]:
    provenance = getattr(state, "provenance", None) or getattr(engine, "provenance", None) or "unknown"
    revision = getattr(state, "revision", None)
    if revision is None:
        revision = getattr(engine, "revision", None)
    return {
        "canonical_state": "unavailable",
        "workspace_sync": "unverified",
        "canonical_revision": revision,
        "provenance": provenance,
        "families": {},
        "advisory_warning": None,
        "freshness_evaluation": "failed",
    }


def _freshness(
    root: Path,
    state: Any,
    engine: Any,
    family: str,
    family_state: str,
    coverage: dict[str, int] | None,
) -> tuple[dict[str, Any], str | None]:
    if state is None:
        result = _fallback_freshness(state, engine)
        failure_reason = "Canonical freshness evaluation failed; no canonical engine state was available."
    else:
        try:
            candidate = query_helpers.build_state_freshness(root, state, engine=engine)
            required_fields = {
                "canonical_state",
                "workspace_sync",
                "canonical_revision",
                "provenance",
                "families",
            }
            if (
                not isinstance(candidate, dict)
                or not required_fields <= candidate.keys()
                or not isinstance(candidate["families"], dict)
                or candidate["canonical_state"]
                not in {"fresh", "stale", "unknown", "unavailable"}
            ):
                raise TypeError("canonical freshness helper returned a non-mapping result")
            result = dict(candidate)
            failure_reason = None
        except Exception:
            result = _fallback_freshness(state, engine)
            failure_reason = "Canonical freshness evaluation failed; canonical freshness evidence is unavailable."

    result["resync_required"] = bool(getattr(state, "resync_required", False))
    families = dict(result.get("families") or {})
    families[family] = family_state
    if coverage is not None:
        families["module_usages"] = (
            "fresh"
            if not any(
                coverage[name] > 0
                for name in (
                    "missing_symbol_calls_materialization_count",
                    "missing_reference_evidence_count",
                    "stale_module_count",
                )
            )
            else "partial"
        )
    result["families"] = families
    return result, failure_reason


def _family_gate(family: str, state: Any) -> tuple[str, dict[str, int] | None, str | None]:
    if family == "artifact_consumption":
        state_value = str(getattr(state, "artifact_consumption_state", "deferred"))
        if getattr(state, "resync_required", False):
            return "unavailable", None, "Canonical LIVE state requires resync."
        if artifact_consumption_is_fresh(state):
            return "fresh", None, None
        status = "stale" if state_value == "stale" else "partial"
        return status, None, f"artifact_consumption is not fresh or has incomplete canonical coverage (state={state_value})."
    if family == "syntax_diagnostics":
        state_value = str(getattr(state, "syntax_diagnostics_state", "not_materialized"))
        facts = getattr(state, "syntax_diagnostics_by_path", None)
        if getattr(state, "resync_required", False):
            return "unavailable", None, "Canonical LIVE state requires resync."
        if state_value == "fresh" and isinstance(facts, dict):
            return "fresh", None, None
        status = "stale" if state_value == "stale" else "unavailable"
        return status, None, f"syntax_diagnostics is not queryable as a fresh canonical family (state={state_value})."
    coverage = _coverage(state)
    if getattr(state, "resync_required", False):
        return "unavailable", coverage, "Canonical LIVE state requires resync."
    incomplete = any(
        coverage[name] > 0
        for name in (
            "missing_symbol_calls_materialization_count",
            "missing_reference_evidence_count",
            "stale_module_count",
        )
    )
    if incomplete:
        return "partial", coverage, "Canonical module_usages coverage is incomplete."
    return "fresh", coverage, None


def _gap(
    *,
    source: str | None,
    target: str | None,
    expected_edge: str,
    status: str,
    reason: str,
    **values: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "from": source,
        "to": target,
        "expected_edge": expected_edge,
        "status": status,
        "reason": reason,
    }
    result.update(values)
    return result


def _reachable(
    anchor_id: str,
    edges: dict[tuple[str, str, str], dict[str, Any]],
    direction: str,
    depth: int,
) -> tuple[set[str], set[tuple[str, str, str]]]:
    nodes = {anchor_id}
    selected_edges: set[tuple[str, str, str]] = set()
    frontier = {anchor_id}
    for _ in range(depth):
        next_frontier: set[str] = set()
        for key, edge in edges.items():
            source = edge["source"]
            target = edge["target"]
            can_downstream = direction in {"downstream", "both"} and source in frontier
            can_upstream = direction in {"upstream", "both"} and target in frontier
            if can_downstream:
                selected_edges.add(key)
                if target not in nodes:
                    next_frontier.add(target)
                nodes.add(target)
            if can_upstream:
                selected_edges.add(key)
                if source not in nodes:
                    next_frontier.add(source)
                nodes.add(source)
        frontier = next_frontier
        if not frontier:
            break
    return nodes, selected_edges


def _without_downstream_edges(
    anchor_id: str,
    edges: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    downstream_edges: set[tuple[str, str, str]] = set()
    frontier = {anchor_id}
    while frontier:
        next_frontier: set[str] = set()
        for key, edge in edges.items():
            if edge["source"] not in frontier or key in downstream_edges:
                continue
            downstream_edges.add(key)
            next_frontier.add(edge["target"])
        frontier = next_frontier
    return {
        key: edge
        for key, edge in edges.items()
        if key not in downstream_edges
    }


def _canonical_state_status(canonical_state: str) -> str | None:
    if canonical_state == "stale":
        return "stale"
    if canonical_state in {"unknown", "unavailable"}:
        return "unavailable"
    return None


def _data_source(provenance: Any) -> str:
    if provenance == "live":
        return "live_canonical_state"
    if provenance == "snapshot":
        return "snapshot_canonical_state"
    return "canonical_state_unavailable"


def _serialize(result: dict[str, Any], edge_count: int) -> str:
    serialized = json.dumps(result, indent=2, ensure_ascii=False)
    return guard_large_output(
        serialized,
        allow_large_output=False,
        requested_count=edge_count,
        reason="The lineage projection exceeds the recommended context size.",
        retry_instruction="Reduce depth/direction or use the same bounded lineage request after the state is narrowed.",
    )


def _error(status: str, **values: Any) -> str:
    payload = {"status": status}
    payload.update(values)
    return json.dumps(payload, indent=2, ensure_ascii=False)


def contextor_fact_lineage(
    repo_path: str,
    family: str,
    direction: str = "both",
    depth: int = 3,
) -> str:
    if not isinstance(family, str) or family not in _FAMILIES:
        return _error("invalid_family", allowed=list(_FAMILIES), family=family)
    if direction not in _DIRECTIONS:
        return _error("invalid_direction", allowed=list(_DIRECTIONS), direction=direction)
    if isinstance(depth, bool) or not isinstance(depth, int) or not 1 <= depth <= _MAX_DEPTH:
        return _error("invalid_depth", minimum=1, maximum=_MAX_DEPTH, depth=depth)

    root = Path(repo_path).expanduser().resolve()
    spec = _SPECS[family]
    anchor_id = f"family:{family}"
    state_id = _state_id(spec)
    try:
        engine = mcp_runtime.get_or_init_engine(root)
    except Exception as exc:
        return _error("unavailable", reason="canonical_live_state_unavailable", detail=str(exc))

    state = getattr(engine, "state", None) if engine is not None else None
    registry_maps = _read_registry_maps(root, engine) if engine is not None else ({}, {}, {}, {})
    nodes, all_edges, identity_gaps = _build_contract(family, spec, registry_maps)

    coverage: dict[str, int] | None = None
    if state is None:
        gate_status, coverage, gate_reason = "unavailable", None, "No usable canonical engine state was available."
    else:
        gate_status, coverage, gate_reason = _family_gate(family, state)
    family_gate_status = gate_status

    freshness, freshness_failure = _freshness(
        root,
        state,
        engine,
        family,
        "unavailable" if state is None else gate_status,
        coverage,
    )
    if freshness_failure is not None:
        gate_status = "unavailable"
        gate_reason = freshness_failure
        freshness["families"][family] = "unavailable"
        if coverage is not None:
            freshness["families"]["module_usages"] = "unavailable"
    provenance = freshness.get("provenance")
    data_source = _data_source(provenance)
    canonical_state_status = (
        None
        if freshness_failure is not None
        else _canonical_state_status(freshness["canonical_state"])
    )
    canonical_state_reason = None
    if canonical_state_status is not None:
        canonical_state = freshness["canonical_state"]
        canonical_state_reason = (
            f"Canonical freshness helper reported canonical_state={canonical_state}."
        )
        if _STATUS_RANK[canonical_state_status] > _STATUS_RANK[gate_status]:
            gate_status = canonical_state_status

    edges = all_edges
    if gate_status in {"unavailable", "stale"} or (
        family == "artifact_consumption" and gate_status == "partial"
    ):
        edges = {
            key: edge
            for key, edge in all_edges.items()
            if edge["type"] not in _UNAVAILABLE_EDGE_TYPES
        }
    if freshness_failure is not None:
        edges = _without_downstream_edges(anchor_id, edges)
    elif canonical_state_status is not None:
        edges = _without_downstream_edges(anchor_id, edges)

    unresolved = list(identity_gaps.values())
    if canonical_state_status is not None:
        unresolved.append(
            _gap(
                source=anchor_id,
                target=state_id,
                expected_edge="CANONICAL_STATE_FRESHNESS",
                status=canonical_state_status,
                reason=canonical_state_reason,
                kind="canonical_state_freshness",
                canonical_state=freshness["canonical_state"],
            )
        )
    if freshness_failure is not None:
        unresolved.append(
            _gap(
                source=anchor_id,
                target=state_id,
                expected_edge="CANONICAL_FRESHNESS_EVALUATION",
                status="unavailable",
                reason=freshness_failure,
                kind="freshness_evaluation",
            )
        )
    if gate_reason is not None and not (
        coverage is not None and family_gate_status == "partial"
    ):
        unresolved.append(
            _gap(
                source=anchor_id,
                target=state_id,
                expected_edge="CURRENT_CANONICAL_FAMILY_DATA",
                status=(
                    "stale"
                    if gate_status == "stale"
                    else "unavailable"
                    if gate_status == "unavailable"
                    else "partial"
                    if gate_status == "partial"
                    else "unresolved"
                ),
                reason=gate_reason,
                family_state=freshness["families"].get(family),
                **({"coverage": coverage} if coverage is not None else {}),
            )
        )
    if coverage is not None and family_gate_status == "partial":
        unresolved.append(
            _gap(
                source=anchor_id,
                target=state_id,
                expected_edge="COMPLETE_SYMBOL_CALLS_COVERAGE",
                status="partial",
                reason="Some canonical modules lack materialized symbol-call or reference-evidence facts.",
                coverage=coverage,
            )
        )

    reachable_nodes, selected_edges = _reachable(anchor_id, edges, direction, depth)
    reachable_nodes.add(anchor_id)
    selected_edges_list = [
        edge for key, edge in edges.items() if key in selected_edges
    ]
    selected_node_ids = set(reachable_nodes)
    unresolved = [
        item
        for item in unresolved
        if item.get("kind") != "identity_resolution" or item.get("from") in selected_node_ids
    ]
    support_node_ids = {anchor_id, state_id}
    for item in unresolved:
        for field in ("from", "to"):
            reference = item.get(field)
            if reference is not None:
                support_node_ids.add(reference)
    selected_node_ids.update(support_node_ids)
    selected_nodes = [
        node for node in nodes.values() if node["id"] in selected_node_ids
    ]
    selected_nodes.sort(key=lambda item: (item["type"], item["id"]))
    selected_edges_list.sort(key=lambda item: (item["source"], item["target"], item["type"]))
    unresolved.sort(
        key=lambda item: (
            str(item.get("from") or ""),
            str(item.get("to") or ""),
            str(item.get("expected_edge") or ""),
            str(item.get("status") or ""),
            str(item.get("kind") or ""),
        )
    )
    projections = sorted(
        node["id"]
        for node in selected_nodes
        if node["type"] == "public_projection"
    )
    result: dict[str, Any] = {
        "status": "unavailable" if state is None else gate_status if gate_status != "fresh" else "ok",
        "family": family,
        "owner": [state_id],
        "entry_points": [anchor_id],
        "nodes": selected_nodes,
        "edges": selected_edges_list,
        "public_projections": projections,
        "unresolved": unresolved,
        "freshness": freshness,
        "data_source": data_source,
    }
    if coverage is not None:
        result["coverage"] = coverage
    return _serialize(result, len(selected_edges_list))

"""Lossless module-level blast-radius projection."""

import json
from pathlib import Path
from typing import Any

from contextor.core.analysis.incremental import graph_ops
from contextor.core.analysis.state_manager import artifact_consumption_is_fresh
from contextor.core.report_query import normalize_module_path_to_dotted, registry_maps_from_state
from contextor.mcp import query_helpers
from contextor.mcp import representation as mcp_rep
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.output_guard import guard_large_output


_ALLOWED_FIELDS = {
    "module",
    "module_id",
    "artifact_count_total",
    "artifact_count_returned",
    "artifacts",
    "aggregate",
    "data_source",
    "state_freshness",
}

# This ceiling is local to the complete compact representation.  Other MCP
# tools retain the shared 15 KiB warning threshold.
_LOSSLESS_COMPACT_MAX_BYTES = 64 * 1024


def _json_error(message: str, **details: Any) -> str:
    payload = {"status": "error", "error": message}
    payload.update(details)
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _module_id_for(module_name: str, module_path_to_id: dict[str, str], state: Any) -> str | None:
    if module_name in module_path_to_id:
        return str(module_path_to_id[module_name])
    obj = (getattr(state, "modules", {}) or {}).get(module_name)
    value = (
        (obj.get("module_id") or obj.get("id"))
        if isinstance(obj, dict)
        else (getattr(obj, "module_id", None) or getattr(obj, "id", None))
    )
    return str(value) if value else None


def _architecture(*, state: Any, definer_module: str, direct_consumers: list[str]) -> dict[str, Any]:
    cached = getattr(state, "cached_analytics", {}) or {}
    cached_state = getattr(state, "cached_analytics_state", "deferred")
    if cached_state != "fresh" or not isinstance(cached, dict):
        return {"available": False, "reason": f"Cached analytics state is '{cached_state}'."}

    layers = cached.get("module_layers", {}) or {}
    definer_layer = layers.get(definer_module)
    same_module: list[str] = []
    same_layer: list[str] = []
    cross_layer: list[dict[str, str]] = []
    tests: list[str] = []
    unknown: list[str] = []
    known_layers: set[str] = set()
    for consumer in sorted(set(direct_consumers)):
        if consumer == definer_module:
            same_module.append(consumer)
            continue
        layer = layers.get(consumer)
        if layer is not None:
            known_layers.add(str(layer))
        if layer == "tests":
            tests.append(consumer)
        elif definer_layer is None or layer is None:
            unknown.append(consumer)
        elif layer == definer_layer:
            same_layer.append(consumer)
        else:
            cross_layer.append({"module": consumer, "layer": str(layer)})

    result: dict[str, Any] = {
        "available": True,
        "definer_layer": definer_layer,
        "consumer_layers": sorted(known_layers),
        "same_module_consumer_count": len(same_module),
        "same_layer_consumer_count": len(same_layer),
        "cross_layer_consumer_count": len(cross_layer),
        "test_consumer_count": len(tests),
        "cross_layer_consumers": bool(cross_layer),
        "identity_partitions": {
            "same_module": same_module,
            "same_layer": same_layer,
            "cross_layer": cross_layer,
            "tests": tests,
            "unknown": unknown,
        },
    }
    if unknown:
        result["unknown_layer_consumer_count"] = len(unknown)
    if cross_layer:
        result["cross_layer_sample"] = {
            "total": len(cross_layer),
            "items": cross_layer,
            "truncated": False,
        }
    return result


def _downstream_reachability(
    *,
    definer_module: str,
    direct_consumers: list[str],
    reverse_adjacency: dict[str, set[str]] | None,
    state: Any,
    closure_cache: dict[str, set[str]],
) -> tuple[dict[str, Any], set[str]]:
    if reverse_adjacency is None:
        return {"available": False, "reason": "Live dependency graph is not available."}, set()

    reachable: set[str] = set()
    for seed in sorted(set(direct_consumers)):
        if seed not in closure_cache:
            closure_cache[seed] = graph_ops.calculate_affected_set_from_reverse(seed, reverse_adjacency)
        reachable.update(closure_cache[seed])
    downstream = reachable - set(direct_consumers) - {definer_module}
    ordered = sorted(downstream)
    result: dict[str, Any] = {
        "available": True,
        "total_downstream_count": len(ordered),
        "items": ordered,
        "truncated": False,
    }

    cached = getattr(state, "cached_analytics", {}) or {}
    cached_state = getattr(state, "cached_analytics_state", "deferred")
    if cached_state == "fresh" and isinstance(cached, dict):
        layers = cached.get("module_layers", {}) or {}
        production = [m for m in ordered if layers.get(m) not in (None, "tests")]
        tests = [m for m in ordered if layers.get(m) == "tests"]
        unknown = [m for m in ordered if layers.get(m) is None]
        result.update(
            {
                "layer_classification_available": True,
                "production_downstream_count": len(production),
                "test_downstream_count": len(tests),
                "unknown_layer_downstream_count": len(unknown),
                "production_downstream_sample": {"total": len(production), "items": production, "truncated": False},
                "test_downstream_sample": {"total": len(tests), "items": tests, "truncated": False},
                "unknown_downstream_sample": {"total": len(unknown), "items": unknown, "truncated": False},
            }
        )
    else:
        result.update(
            {
                "layer_classification_available": False,
                "reason": f"Cached analytics state is '{cached_state}'.",
            }
        )
    return result, downstream


def _full_collection(items: list[str]) -> dict[str, Any]:
    ordered = sorted({str(item) for item in items})
    return {"total": len(ordered), "truncated": False, "items": ordered}


def _aggregate_downstream_view(
    downstream: set[str], *, state: Any, reverse_adjacency: dict[str, set[str]] | None
) -> dict[str, Any]:
    if reverse_adjacency is None:
        return {"available": False, "reason": "Live dependency graph is not available."}
    ordered = sorted(downstream)
    result: dict[str, Any] = {
        "available": True,
        "total": len(ordered),
        "total_downstream_count": len(ordered),
        "items": ordered,
        "truncated": False,
    }
    cached = getattr(state, "cached_analytics", {}) or {}
    cached_state = getattr(state, "cached_analytics_state", "deferred")
    if cached_state == "fresh" and isinstance(cached, dict):
        layers = cached.get("module_layers", {}) or {}
        production = [m for m in ordered if layers.get(m) not in (None, "tests")]
        tests = [m for m in ordered if layers.get(m) == "tests"]
        unknown = [m for m in ordered if layers.get(m) is None]
        result.update(
            {
                "classification_available": True,
                "layer_classification_available": True,
                "production": len(production),
                "tests": len(tests),
                "unknown": len(unknown),
                "production_downstream_count": len(production),
                "test_downstream_count": len(tests),
                "unknown_layer_downstream_count": len(unknown),
            }
        )
    else:
        result.update(
            {
                "classification_available": False,
                "layer_classification_available": False,
                "reason": f"Cached analytics state is '{cached_state}'.",
            }
        )
    return result


def _has_module_identity_collection(value: Any) -> bool:
    identity_keys = {"items", "direct", "downstream", "same_module", "same_layer", "tests", "unknown", "cross_layer"}
    if isinstance(value, dict):
        for key, child in value.items():
            if key in identity_keys:
                if isinstance(child, list) and child:
                    return True
                if isinstance(child, dict) and _has_module_identity_collection(child):
                    return True
            if _has_module_identity_collection(child):
                return True
    elif isinstance(value, list):
        return any(_has_module_identity_collection(item) for item in value)
    return False


def _id_sort_key(value: str) -> tuple[Any, ...]:
    parts = value.split("/", 1)
    if len(parts) == 2 and all(part.isdigit() for part in parts):
        return (0, int(parts[0]), int(parts[1]), value)
    return (1, value)


def _build_shared_sets(
    *,
    artifact_facts: list[dict[str, Any]],
    all_direct: set[str],
    all_downstream: set[str],
    module_path_to_id: dict[str, str],
    state: Any,
) -> tuple[list[str], list[list[int]], dict[str, int], dict[tuple[int, ...], int]]:
    names = set(all_direct) | set(all_downstream)
    for fact in artifact_facts:
        names.update(fact["direct"])
        if fact["downstream"] and fact["downstream"].get("available"):
            names.update(fact["downstream_names"])
    pairs: list[tuple[str, str]] = []
    missing: list[str] = []
    for name in sorted(names):
        module_id = _module_id_for(name, module_path_to_id, state)
        if module_id is None:
            missing.append(name)
        else:
            pairs.append((name, module_id))
    if missing:
        raise ValueError("Cannot fulfill indexed representation: missing module IDs for: " + ", ".join(missing))
    pairs.sort(key=lambda item: _id_sort_key(item[1]))
    module_index = [module_id for _, module_id in pairs]
    ordinal = {name: index for index, (name, _) in enumerate(pairs)}
    signatures: set[tuple[int, ...]] = {()}
    for fact in artifact_facts:
        signatures.add(tuple(sorted(ordinal[name] for name in fact["direct"])))
        if fact["downstream"] and fact["downstream"].get("available"):
            signatures.add(tuple(sorted(ordinal[name] for name in fact["downstream_names"])))
    signatures.add(tuple(sorted(ordinal[name] for name in all_direct)))
    signatures.add(tuple(sorted(ordinal[name] for name in all_downstream)))
    ordered_signatures = [()] + sorted(signatures - {()}, key=lambda item: item)
    return module_index, [list(item) for item in ordered_signatures], ordinal, {
        signature: index for index, signature in enumerate(ordered_signatures)
    }


def _named_artifact_entry(fact: dict[str, Any]) -> dict[str, Any]:
    item = fact["item"]
    return {
        "artifact_id": item["artifact_id"],
        "symbol": item["symbol"],
        "full_name": item["full_name"],
        "kind": item["kind"],
        "signature": item["signature"],
        "direct_consumers": _full_collection(fact["direct"]),
        "architecture": fact["architecture"],
        "downstream_module_reachability": fact["downstream"],
        "evidence_scope": "direct_static_artifact_consumption",
    }


def _compact_architecture(architecture: dict[str, Any]) -> dict[str, Any]:
    if not architecture.get("available"):
        return dict(architecture)
    return {
        key: value
        for key, value in architecture.items()
        if key not in {"identity_partitions", "cross_layer_sample"}
    }


def _compact_downstream(downstream: dict[str, Any], downstream_ref: int | None) -> dict[str, Any]:
    result = {
        key: value
        for key, value in downstream.items()
        if key
        not in {
            "items",
            "truncated",
            "production_downstream_sample",
            "test_downstream_sample",
            "unknown_downstream_sample",
        }
    }
    if downstream.get("available"):
        result["downstream_set_ref"] = downstream_ref
        result.setdefault("truncated", False)
    return result


def _project_fields(result: dict[str, Any], fields: list[str] | None, support: tuple[str, ...] = ()) -> dict[str, Any]:
    if fields is None:
        return result
    projected = {field: result[field] for field in fields if field in result}
    for field in support:
        if field in result:
            projected[field] = result[field]
    return projected


def _build_named_projection(
    *,
    module_name: str,
    module_id: str | None,
    total_artifacts: int,
    artifact_facts: list[dict[str, Any]],
    aggregate: dict[str, Any] | None,
    freshness: dict[str, Any] | None,
    artifacts_projected: bool,
    fields: list[str] | None,
) -> dict[str, Any]:
    records = {
        str(fact["item"]["artifact_id"] or fact["item"]["full_name"]): _named_artifact_entry(fact)
        for fact in artifact_facts
    }
    returned_count = len(records) if artifacts_projected else 0
    base: dict[str, Any] = {
        "module": module_name,
        "module_id": module_id,
        "artifact_count_total": total_artifacts,
        "artifact_count_returned": returned_count,
        "artifacts": records if artifacts_projected else {},
        "aggregate": aggregate,
        "data_source": "live_canonical_state",
        "state_freshness": freshness,
    }
    if aggregate is not None:
        aggregate["artifact_count_returned"] = returned_count
    return _project_fields(base, fields)


def _build_indexed_projection(
    *,
    module_name: str,
    module_id: str | None,
    total_artifacts: int,
    artifact_facts: list[dict[str, Any]],
    aggregate: dict[str, Any] | None,
    freshness: dict[str, Any] | None,
    artifacts_projected: bool,
    fields: list[str] | None,
    module_path_to_id: dict[str, str],
    state: Any,
    all_direct: set[str],
    all_downstream: set[str],
    reverse_adjacency: dict[str, set[str]] | None,
    cached_analytics: dict[str, Any],
) -> dict[str, Any]:
    identity_payload = {
        "direct": sorted(all_direct),
        "downstream": sorted(all_downstream),
        "artifacts": [
            {"direct": fact["direct"], "downstream": fact.get("downstream_names", [])}
            for fact in artifact_facts
        ],
    }
    if not _has_module_identity_collection(identity_payload):
        return _build_named_projection(
            module_name=module_name,
            module_id=module_id,
            total_artifacts=total_artifacts,
            artifact_facts=artifact_facts,
            aggregate=aggregate,
            freshness=freshness,
            artifacts_projected=artifacts_projected,
            fields=fields,
        )

    module_index, sets, ordinal, refs = _build_shared_sets(
        artifact_facts=artifact_facts,
        all_direct=all_direct,
        all_downstream=all_downstream,
        module_path_to_id=module_path_to_id,
        state=state,
    )
    layers = cached_analytics.get("module_layers", {}) or {}
    layer_values = sorted({str(layer) for layer in layers.values() if layer is not None})
    layer_code = {value: index for index, value in enumerate(layer_values)}
    names_by_id = sorted(
        ((name, _module_id_for(name, module_path_to_id, state)) for name in ordinal),
        key=lambda item: _id_sort_key(str(item[1])),
    )
    layer_codes = [layer_code.get(layers.get(name)) for name, _ in names_by_id]

    encoded_artifacts: dict[str, Any] = {}
    for fact in artifact_facts:
        item = fact["item"]
        direct_signature = tuple(sorted(ordinal[name] for name in fact["direct"]))
        downstream_signature = (
            tuple(sorted(ordinal[name] for name in fact["downstream_names"]))
            if fact["downstream"].get("available")
            else None
        )
        encoded: dict[str, Any] = {
            "artifact_id": item["artifact_id"],
            "symbol": item["symbol"],
            "kind": item["kind"],
            "signature": item["signature"],
            "direct_set_ref": refs[direct_signature],
            "direct_consumer_count": len(fact["direct"]),
            "architecture": _compact_architecture(fact["architecture"]),
            "downstream_module_reachability": _compact_downstream(
                fact["downstream"],
                refs[downstream_signature] if downstream_signature is not None else None,
            ),
            "evidence_scope": "direct_static_artifact_consumption",
        }
        if fact["downstream"].get("available"):
            encoded["downstream_count"] = len(fact["downstream_names"])
        encoded_artifacts[str(item["artifact_id"] or item["full_name"])] = encoded

    encoded_aggregate = None
    if aggregate is not None:
        direct_signature = tuple(sorted(ordinal[name] for name in all_direct))
        downstream_signature = tuple(sorted(ordinal[name] for name in all_downstream))
        direct_named = aggregate["unique_direct_consumers"]
        downstream_named = aggregate["unique_downstream_consumers"]
        encoded_aggregate = {
            key: value
            for key, value in aggregate.items()
            if key not in {"unique_direct_consumers", "unique_downstream_consumers"}
        }
        encoded_aggregate.update(
            {
                "direct_set_ref": refs[direct_signature],
                "downstream_set_ref": refs[downstream_signature] if reverse_adjacency is not None else None,
                "unique_direct_consumer_count": len(all_direct),
                "unique_downstream_consumer_count": len(all_downstream),
                "unique_direct_consumers": {
                    "total": direct_named.get("total", len(all_direct)),
                    "truncated": False,
                    "set_ref": refs[direct_signature],
                },
                "unique_downstream_consumers": {
                    key: value
                    for key, value in downstream_named.items()
                    if key not in {"items", "truncated"}
                },
            }
        )
        if downstream_named.get("available"):
            encoded_aggregate["unique_downstream_consumers"]["set_ref"] = refs[downstream_signature]
            encoded_aggregate["unique_downstream_consumers"]["truncated"] = False

    base: dict[str, Any] = {
        "schema": "module_blast_radius.lossless.v1",
        "representation": "indexed",
        "module": module_name,
        "module_id": module_id,
        "module_layer": layers.get(module_name),
        "module_index": module_index,
        "module_layers": {"dictionary": layer_values, "codes": layer_codes},
        "sets": sets,
        "artifact_count_total": total_artifacts,
        "artifact_count_returned": len(encoded_artifacts) if artifacts_projected else 0,
        "artifacts": encoded_artifacts if artifacts_projected else {},
        "aggregate": encoded_aggregate,
        "data_source": "live_canonical_state",
        "state_freshness": freshness,
    }
    if aggregate is not None:
        aggregate["artifact_count_returned"] = base["artifact_count_returned"]
    return _project_fields(
        base,
        fields,
        support=("schema", "representation", "module_layer", "module_index", "module_layers", "sets"),
    )


def _serialize_payload(
    payload: dict[str, Any], *, semantic_representation: str, allow_large_output: bool, requested_count: int
) -> str:
    if semantic_representation == "indexed":
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        size = len(serialized.encode("utf-8"))
        if size <= _LOSSLESS_COMPACT_MAX_BYTES or allow_large_output:
            return serialized
        return json.dumps(
            {
                "status": "confirmation_required",
                "reason": "Complete lossless indexed module context exceeds the local safety ceiling.",
                "requested_count": requested_count,
                "estimated_output_bytes": size,
                "warning_threshold_bytes": _LOSSLESS_COMPACT_MAX_BYTES,
                "retry": {"allow_large_output": True},
                "retry_instruction": "Repeat the same call with allow_large_output=true.",
            },
            indent=2,
            ensure_ascii=False,
        )
    return guard_large_output(
        json.dumps(payload, indent=2, ensure_ascii=False),
        allow_large_output=allow_large_output,
        requested_count=requested_count,
        reason="Estimated module blast-radius output exceeds the recommended context size.",
        retry_instruction="Repeat the same get_module_blast_radius call with representation='indexed' or allow_large_output=true.",
    )


def get_module_blast_radius(
    repo_path: str,
    module: str = "",
    compact: bool = True,
    fields: list[str] | None = None,
    representation: str = "auto",
    allow_large_output: bool = False,
) -> str:
    if not mcp_rep.is_supported_representation(representation):
        return _json_error(
            "Unsupported representation for get_module_blast_radius",
            representation=representation,
            allowed_representations=sorted(mcp_rep.ALLOWED_REPRESENTATIONS),
        )
    if fields is not None:
        unknown = sorted(set(fields) - _ALLOWED_FIELDS)
        if unknown:
            return _json_error(
                "Unsupported fields for get_module_blast_radius",
                unknown_fields=unknown,
                allowed_fields=sorted(_ALLOWED_FIELDS),
            )
    if not isinstance(module, str) or not module.strip():
        return _json_error("module is required.")

    root = Path(repo_path).expanduser().resolve()
    try:
        engine = mcp_runtime.get_or_init_engine(root)
        state = getattr(engine, "state", None) if engine else None
        if state is None or getattr(state, "resync_required", False):
            return "Error: No usable canonical LIVE state. Run analyze_project first."

        registry = getattr(engine, "registry", None) if engine else None
        live_registry = bool(
            engine is not None
            and getattr(engine, "provenance", None) == "live"
            and getattr(state, "provenance", None) == "live"
            and not getattr(state, "resync_required", False)
            and registry is not None
            and hasattr(registry, "read_transaction")
        )
        if live_registry:
            with registry.read_transaction():
                module_path_to_id, module_id_to_path, _artifact_path_to_id, _artifact_id_to_path = registry_maps_from_state(registry._state)
        else:
            module_path_to_id, module_id_to_path, _artifact_path_to_id, _artifact_id_to_path = query_helpers.read_registries(root)

        effective = module.strip()
        if query_helpers.is_module_id(effective):
            resolution = query_helpers.resolve_module_identity(effective, module_path_to_id, module_id_to_path)
            if resolution.get("status") != "resolved":
                return f"Module '{effective}' not found in registry or canonical LIVE state. Check the module name or run an analysis."
            module_name = resolution["module"]
        else:
            module_name = normalize_module_path_to_dotted(effective, repo_root=str(root))
            live_modules = getattr(state, "modules", {}) or {}
            live_artifacts = getattr(state, "artifacts", {}) or {}
            if module_name not in live_modules and module_name not in live_artifacts:
                resolution = query_helpers.resolve_module_identity(module_name, module_path_to_id, module_id_to_path)
                if resolution.get("status") == "ambiguous":
                    return json.dumps({"status": "ambiguous", "query": effective, "candidates": resolution.get("candidates", []), "data_source": "active_module_registry"}, indent=2, ensure_ascii=False)
                if resolution.get("status") == "resolved":
                    module_name = resolution["module"]
                else:
                    return f"Module '{effective}' not found in registry or canonical LIVE state. Check the module name or run an analysis."

        unavailable = query_helpers.module_truth_unavailable(state, module_name)
        if unavailable:
            return json.dumps(unavailable, indent=2, ensure_ascii=False)

        live_artifacts = getattr(state, "artifacts", {}) or {}
        module_data = live_artifacts.get(module_name, {}) or {}
        catalog = query_helpers.canonical_symbol_catalog(module_data)
        signatures = ((module_data.get("symbols", {}) or {}).get("signatures", {}) or {})
        all_catalog = [
            {
                "symbol": str(symbol),
                "kind": kind,
                "full_name": f"{module_name}::{symbol}",
                "artifact_id": _artifact_path_to_id.get(f"{module_name}::{symbol}"),
                "signature": signatures.get(symbol),
            }
            for symbol, kind in catalog.items()
        ]
        all_catalog.sort(key=lambda item: (item["full_name"].casefold(), item["full_name"]))
        total_artifacts = len(all_catalog)
        artifacts_projected = fields is None or "artifacts" in fields
        aggregate_projected = fields is None or "aggregate" in fields
        wants_data = artifacts_projected or aggregate_projected
        consumption_fresh = artifact_consumption_is_fresh(state) if wants_data and total_artifacts else True
        if total_artifacts and not consumption_fresh:
            return _json_error(
                "Canonical artifact consumption is unavailable or stale.",
                available=False,
                module=module_name,
                state_freshness=query_helpers.build_state_freshness(root, state, engine=engine),
            )

        reverse_adjacency: dict[str, set[str]] | None = None
        if wants_data and total_artifacts:
            dependency_graph = getattr(state, "dependency_graph", None)
            if dependency_graph is not None:
                reverse_adjacency = graph_ops.build_reverse_adjacency(dependency_graph)

        closure_cache: dict[str, set[str]] = {}
        artifact_facts: list[dict[str, Any]] = []
        all_direct: set[str] = set()
        all_downstream: set[str] = set()
        for item in all_catalog if wants_data else []:
            direct = sorted(set(query_helpers.canonical_symbol_consumers(state, module_name, item["symbol"])))
            all_direct.update(direct)
            downstream, downstream_names = _downstream_reachability(
                definer_module=module_name,
                direct_consumers=direct,
                reverse_adjacency=reverse_adjacency,
                state=state,
                closure_cache=closure_cache,
            )
            all_downstream.update(downstream_names)
            artifact_facts.append(
                {
                    "item": item,
                    "direct": direct,
                    "architecture": _architecture(state=state, definer_module=module_name, direct_consumers=direct),
                    "downstream": downstream,
                    "downstream_names": sorted(downstream_names),
                }
            )

        # Aggregate downstream is additional reachability beyond every direct
        # artifact consumer. Per-artifact sets above are intentionally intact.
        all_downstream.difference_update(all_direct)
        all_downstream.discard(module_name)

        cached = getattr(state, "cached_analytics", {}) or {}
        cached_for_projection = (
            cached
            if getattr(state, "cached_analytics_state", "deferred") == "fresh"
            and isinstance(cached, dict)
            else {}
        )
        aggregate: dict[str, Any] | None = None
        returned_count = total_artifacts if artifacts_projected else 0
        if aggregate_projected:
            consumed = [str(f["item"]["artifact_id"] or f["item"]["full_name"]) for f in artifact_facts if f["direct"]]
            unconsumed = [str(f["item"]["artifact_id"] or f["item"]["full_name"]) for f in artifact_facts if not f["direct"]]
            impact = sorted(
                artifact_facts,
                key=lambda f: (
                    -(f["downstream"].get("total_downstream_count", 0) if f["downstream"].get("available") else 0),
                    -len(f["direct"]),
                    f["item"]["full_name"],
                ),
            )
            aggregate = {
                "artifact_count_total": total_artifacts,
                "artifact_count_returned": returned_count,
                "unique_direct_consumers": _full_collection(sorted(all_direct)),
                "unique_downstream_consumers": _aggregate_downstream_view(all_downstream, state=state, reverse_adjacency=reverse_adjacency),
                "consumed_artifact_ids": consumed,
                "unconsumed_artifact_ids": unconsumed,
                "highest_impact_artifact_ids": [str(f["item"]["artifact_id"] or f["item"]["full_name"]) for f in impact],
            }

        freshness = None
        if fields is None or "state_freshness" in fields:
            freshness = query_helpers.build_state_freshness(root, state, engine=engine)
            truth = query_helpers.module_current_truth(state, module_name)
            freshness["canonical_state"] = truth.get("state", freshness.get("canonical_state"))
            freshness.setdefault("families", {})["module"] = truth.get("state", "fresh")

        module_id = module_path_to_id.get(module_name) or _module_id_for(module_name, module_path_to_id, state)
        named_payload = _build_named_projection(
            module_name=module_name,
            module_id=module_id,
            total_artifacts=total_artifacts,
            artifact_facts=artifact_facts,
            aggregate=aggregate,
            freshness=freshness,
            artifacts_projected=artifacts_projected,
            fields=fields,
        )

        indexed_payload: dict[str, Any] | None = None
        indexed_error: ValueError | None = None
        if representation == "indexed" or (representation == "auto" and compact):
            try:
                indexed_payload = _build_indexed_projection(
                    module_name=module_name,
                    module_id=module_id,
                    total_artifacts=total_artifacts,
                    artifact_facts=artifact_facts,
                    aggregate=aggregate,
                    freshness=freshness,
                    artifacts_projected=artifacts_projected,
                    fields=fields,
                    module_path_to_id=module_path_to_id,
                    state=state,
                    all_direct=all_direct,
                    all_downstream=all_downstream,
                    reverse_adjacency=reverse_adjacency,
                    cached_analytics=cached_for_projection,
                )
            except ValueError as exc:
                indexed_error = exc

        identity_present = _has_module_identity_collection(named_payload)
        if representation == "indexed" and indexed_error is not None:
            return _json_error(str(indexed_error))
        if representation == "named":
            payload, selected_representation = named_payload, "named"
        elif representation == "indexed":
            payload = indexed_payload if indexed_payload is not None else named_payload
            selected_representation = "indexed" if indexed_payload is not None and "schema" in indexed_payload else "named"
        elif not compact:
            payload, selected_representation = named_payload, "named"
        elif indexed_payload is None or indexed_error is not None or not identity_present:
            # A missing indexed candidate is a real named fallback.  It must
            # retain named semantics and the named output policy.
            payload, selected_representation = named_payload, "named"
        else:
            named_candidate = json.loads(json.dumps(named_payload, ensure_ascii=False))
            indexed_candidate = json.loads(json.dumps(indexed_payload, ensure_ascii=False))
            # Compare final, symmetrically annotated candidates.  Metadata is
            # emitted only when real identity collections are in the projection.
            named_candidate["consumer_representation"] = {"representation": "named", "requested_representation": "auto"}
            indexed_candidate["consumer_representation"] = {"representation": "indexed", "index_kind": "module", "resolve_via": "lookup_index_entries"}
            sizes = mcp_rep.representation_size_stats(named_candidate, indexed_candidate)
            if sizes["indexed_bytes"] < sizes["named_bytes"]:
                payload, selected_representation = indexed_candidate, "indexed"
            else:
                payload, selected_representation = named_candidate, "named"

        return _serialize_payload(payload, semantic_representation=selected_representation, allow_large_output=allow_large_output, requested_count=returned_count)
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:
        return f"Error reading module blast radius: {exc}"

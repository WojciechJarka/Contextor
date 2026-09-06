# get_module_blast_radius — contract-level fixes

Zakres: wyłącznie poprawki availability/fallback/precedence/projection po lossless redesign. Bez zmiany zaakceptowanego schema, bez runtime certification i bez zmian docs/index.json.

AGGREGATE_EMPTY_VS_UNAVAILABLE_PARITY=PASS; indexed preserves unique_downstream_consumers availability/reason and downstream_set_ref is null when dependency_graph is missing; available empty remains set ref 0.
STALE_CLASSIFICATION_PARITY=PASS; indexed preserves classification_available=false, layer_classification_available=false and deferred/stale reason while retaining available downstream identities.
AUTO_INDEXED_FAILURE_FALLBACK=PASS; missing persistent module IDs produce a real named fallback and invoke named guard/policy, never the indexed 64 KiB ceiling or indexed metadata.
COMPACT_TRUE_AUTO=PASS; complete fixture selects indexed lossless schema.
COMPACT_FALSE_AUTO=PASS; complete auto request returns full named/readable result and does not construct/select indexed.
EXPLICIT_REPRESENTATION_PRECEDENCE=PASS; explicit named overrides compact, explicit indexed overrides compact when lossless and errors structurally when IDs are missing.
FIELDS_INDEXED_NO_ORPHAN_TABLES=PASS; fields=[module] has no schema/representation/module_index/module_layers/sets, while artifacts/aggregate projections include all required support tables.
FULL_NAMED_VS_INDEXED_SEMANTIC_PARITY=PASS; decoder covers artifact IDs, symbol/kind/signature, direct identities, architecture availability/partitions, downstream availability/reason/full identities/classification, aggregate state/identities/classification, consumed/unconsumed IDs, impact order and freshness/evidence semantics.

REAL_ARTIFACT_COUNT=48
REAL_ARTIFACT_RETURNED=48
NEW_DEFAULT_BYTES=45646 UTF-8 bytes for compact auto/indexed direct-process dogfood
REVERSE_ADJACENCY_BUILDS=1
UNIQUE_DIRECT_SEEDS=17
SEED_CLOSURE_COMPUTATIONS=17

TESTS=132 focused tests passed: module blast-radius contracts (including fresh/missing-graph/deferred-analytics/zero-identity parity and fallback), artifact blast-radius regressions, specialized signatures/docs, MCP documentation, indexed report query, persistent registry and registry-reuse paths; one unrelated Authlib deprecation warning. git diff --check passed with existing LF/CRLF conversion warnings only. Direct-process dogfood target=contextor.core.reporting_engine.graph_analytics returned compact auto indexed lossless.v1 with 48/48 artifacts, indexed aggregate availability metadata and direct=17/downstream=126.
DECISION=READY_FOR_RUNTIME_CERTIFICATION

MCP_RESTART_REQUIRED=YES_AFTER_FINAL_IMPLEMENTATION
LIVE_RESTART_REQUIRED=NO
RUNTIME_CERTIFICATION_PENDING=YES

FILES_CHANGED=contextor/mcp/tools/get_module_blast_radius.py; contextor/mcp/docs/get_module_blast_radius.json; tests/mcp/tools/test_get_module_blast_radius.py; tests/mcp/tools/test_specialized_tool_contracts.py
COMPLETE RAW UNIFIED DIFF każdego FILES_CHANGED (walkthrough.md excluded):

### contextor/mcp/tools/get_module_blast_radius.py

```diff
warning: in the working copy of 'contextor/mcp/tools/get_module_blast_radius.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/tools/get_module_blast_radius.py b/contextor/mcp/tools/get_module_blast_radius.py
new file mode 100644
index 0000000..066319d
--- /dev/null
+++ b/contextor/mcp/tools/get_module_blast_radius.py
@@ -0,0 +1,761 @@
+"""Lossless module-level blast-radius projection."""
+
+import json
+from pathlib import Path
+from typing import Any
+
+from contextor.core.analysis.incremental import graph_ops
+from contextor.core.analysis.state_manager import artifact_consumption_is_fresh
+from contextor.core.report_query import normalize_module_path_to_dotted, registry_maps_from_state
+from contextor.mcp import query_helpers
+from contextor.mcp import representation as mcp_rep
+from contextor.mcp import runtime as mcp_runtime
+from contextor.mcp.output_guard import guard_large_output
+
+
+_ALLOWED_FIELDS = {
+    "module",
+    "module_id",
+    "artifact_count_total",
+    "artifact_count_returned",
+    "artifacts",
+    "aggregate",
+    "data_source",
+    "state_freshness",
+}
+
+# This ceiling is local to the complete compact representation.  Other MCP
+# tools retain the shared 15 KiB warning threshold.
+_LOSSLESS_COMPACT_MAX_BYTES = 64 * 1024
+
+
+def _json_error(message: str, **details: Any) -> str:
+    payload = {"status": "error", "error": message}
+    payload.update(details)
+    return json.dumps(payload, indent=2, ensure_ascii=False)
+
+
+def _module_id_for(module_name: str, module_path_to_id: dict[str, str], state: Any) -> str | None:
+    if module_name in module_path_to_id:
+        return str(module_path_to_id[module_name])
+    obj = (getattr(state, "modules", {}) or {}).get(module_name)
+    value = (
+        (obj.get("module_id") or obj.get("id"))
+        if isinstance(obj, dict)
+        else (getattr(obj, "module_id", None) or getattr(obj, "id", None))
+    )
+    return str(value) if value else None
+
+
+def _architecture(*, state: Any, definer_module: str, direct_consumers: list[str]) -> dict[str, Any]:
+    cached = getattr(state, "cached_analytics", {}) or {}
+    cached_state = getattr(state, "cached_analytics_state", "deferred")
+    if cached_state != "fresh" or not isinstance(cached, dict):
+        return {"available": False, "reason": f"Cached analytics state is '{cached_state}'."}
+
+    layers = cached.get("module_layers", {}) or {}
+    definer_layer = layers.get(definer_module)
+    same_module: list[str] = []
+    same_layer: list[str] = []
+    cross_layer: list[dict[str, str]] = []
+    tests: list[str] = []
+    unknown: list[str] = []
+    known_layers: set[str] = set()
+    for consumer in sorted(set(direct_consumers)):
+        if consumer == definer_module:
+            same_module.append(consumer)
+            continue
+        layer = layers.get(consumer)
+        if layer is not None:
+            known_layers.add(str(layer))
+        if layer == "tests":
+            tests.append(consumer)
+        elif definer_layer is None or layer is None:
+            unknown.append(consumer)
+        elif layer == definer_layer:
+            same_layer.append(consumer)
+        else:
+            cross_layer.append({"module": consumer, "layer": str(layer)})
+
+    result: dict[str, Any] = {
+        "available": True,
+        "definer_layer": definer_layer,
+        "consumer_layers": sorted(known_layers),
+        "same_module_consumer_count": len(same_module),
+        "same_layer_consumer_count": len(same_layer),
+        "cross_layer_consumer_count": len(cross_layer),
+        "test_consumer_count": len(tests),
+        "cross_layer_consumers": bool(cross_layer),
+        "identity_partitions": {
+            "same_module": same_module,
+            "same_layer": same_layer,
+            "cross_layer": cross_layer,
+            "tests": tests,
+            "unknown": unknown,
+        },
+    }
+    if unknown:
+        result["unknown_layer_consumer_count"] = len(unknown)
+    if cross_layer:
+        result["cross_layer_sample"] = {
+            "total": len(cross_layer),
+            "items": cross_layer,
+            "truncated": False,
+        }
+    return result
+
+
+def _downstream_reachability(
+    *,
+    definer_module: str,
+    direct_consumers: list[str],
+    reverse_adjacency: dict[str, set[str]] | None,
+    state: Any,
+    closure_cache: dict[str, set[str]],
+) -> tuple[dict[str, Any], set[str]]:
+    if reverse_adjacency is None:
+        return {"available": False, "reason": "Live dependency graph is not available."}, set()
+
+    reachable: set[str] = set()
+    for seed in sorted(set(direct_consumers)):
+        if seed not in closure_cache:
+            closure_cache[seed] = graph_ops.calculate_affected_set_from_reverse(seed, reverse_adjacency)
+        reachable.update(closure_cache[seed])
+    downstream = reachable - set(direct_consumers) - {definer_module}
+    ordered = sorted(downstream)
+    result: dict[str, Any] = {
+        "available": True,
+        "total_downstream_count": len(ordered),
+        "items": ordered,
+        "truncated": False,
+    }
+
+    cached = getattr(state, "cached_analytics", {}) or {}
+    cached_state = getattr(state, "cached_analytics_state", "deferred")
+    if cached_state == "fresh" and isinstance(cached, dict):
+        layers = cached.get("module_layers", {}) or {}
+        production = [m for m in ordered if layers.get(m) not in (None, "tests")]
+        tests = [m for m in ordered if layers.get(m) == "tests"]
+        unknown = [m for m in ordered if layers.get(m) is None]
+        result.update(
+            {
+                "layer_classification_available": True,
+                "production_downstream_count": len(production),
+                "test_downstream_count": len(tests),
+                "unknown_layer_downstream_count": len(unknown),
+                "production_downstream_sample": {"total": len(production), "items": production, "truncated": False},
+                "test_downstream_sample": {"total": len(tests), "items": tests, "truncated": False},
+                "unknown_downstream_sample": {"total": len(unknown), "items": unknown, "truncated": False},
+            }
+        )
+    else:
+        result.update(
+            {
+                "layer_classification_available": False,
+                "reason": f"Cached analytics state is '{cached_state}'.",
+            }
+        )
+    return result, downstream
+
+
+def _full_collection(items: list[str]) -> dict[str, Any]:
+    ordered = sorted({str(item) for item in items})
+    return {"total": len(ordered), "truncated": False, "items": ordered}
+
+
+def _aggregate_downstream_view(
+    downstream: set[str], *, state: Any, reverse_adjacency: dict[str, set[str]] | None
+) -> dict[str, Any]:
+    if reverse_adjacency is None:
+        return {"available": False, "reason": "Live dependency graph is not available."}
+    ordered = sorted(downstream)
+    result: dict[str, Any] = {
+        "available": True,
+        "total": len(ordered),
+        "total_downstream_count": len(ordered),
+        "items": ordered,
+        "truncated": False,
+    }
+    cached = getattr(state, "cached_analytics", {}) or {}
+    cached_state = getattr(state, "cached_analytics_state", "deferred")
+    if cached_state == "fresh" and isinstance(cached, dict):
+        layers = cached.get("module_layers", {}) or {}
+        production = [m for m in ordered if layers.get(m) not in (None, "tests")]
+        tests = [m for m in ordered if layers.get(m) == "tests"]
+        unknown = [m for m in ordered if layers.get(m) is None]
+        result.update(
+            {
+                "classification_available": True,
+                "layer_classification_available": True,
+                "production": len(production),
+                "tests": len(tests),
+                "unknown": len(unknown),
+                "production_downstream_count": len(production),
+                "test_downstream_count": len(tests),
+                "unknown_layer_downstream_count": len(unknown),
+            }
+        )
+    else:
+        result.update(
+            {
+                "classification_available": False,
+                "layer_classification_available": False,
+                "reason": f"Cached analytics state is '{cached_state}'.",
+            }
+        )
+    return result
+
+
+def _has_module_identity_collection(value: Any) -> bool:
+    identity_keys = {"items", "direct", "downstream", "same_module", "same_layer", "tests", "unknown", "cross_layer"}
+    if isinstance(value, dict):
+        for key, child in value.items():
+            if key in identity_keys:
+                if isinstance(child, list) and child:
+                    return True
+                if isinstance(child, dict) and _has_module_identity_collection(child):
+                    return True
+            if _has_module_identity_collection(child):
+                return True
+    elif isinstance(value, list):
+        return any(_has_module_identity_collection(item) for item in value)
+    return False
+
+
+def _id_sort_key(value: str) -> tuple[Any, ...]:
+    parts = value.split("/", 1)
+    if len(parts) == 2 and all(part.isdigit() for part in parts):
+        return (0, int(parts[0]), int(parts[1]), value)
+    return (1, value)
+
+
+def _build_shared_sets(
+    *,
+    artifact_facts: list[dict[str, Any]],
+    all_direct: set[str],
+    all_downstream: set[str],
+    module_path_to_id: dict[str, str],
+    state: Any,
+) -> tuple[list[str], list[list[int]], dict[str, int], dict[tuple[int, ...], int]]:
+    names = set(all_direct) | set(all_downstream)
+    for fact in artifact_facts:
+        names.update(fact["direct"])
+        if fact["downstream"] and fact["downstream"].get("available"):
+            names.update(fact["downstream_names"])
+    pairs: list[tuple[str, str]] = []
+    missing: list[str] = []
+    for name in sorted(names):
+        module_id = _module_id_for(name, module_path_to_id, state)
+        if module_id is None:
+            missing.append(name)
+        else:
+            pairs.append((name, module_id))
+    if missing:
+        raise ValueError("Cannot fulfill indexed representation: missing module IDs for: " + ", ".join(missing))
+    pairs.sort(key=lambda item: _id_sort_key(item[1]))
+    module_index = [module_id for _, module_id in pairs]
+    ordinal = {name: index for index, (name, _) in enumerate(pairs)}
+    signatures: set[tuple[int, ...]] = {()}
+    for fact in artifact_facts:
+        signatures.add(tuple(sorted(ordinal[name] for name in fact["direct"])))
+        if fact["downstream"] and fact["downstream"].get("available"):
+            signatures.add(tuple(sorted(ordinal[name] for name in fact["downstream_names"])))
+    signatures.add(tuple(sorted(ordinal[name] for name in all_direct)))
+    signatures.add(tuple(sorted(ordinal[name] for name in all_downstream)))
+    ordered_signatures = [()] + sorted(signatures - {()}, key=lambda item: item)
+    return module_index, [list(item) for item in ordered_signatures], ordinal, {
+        signature: index for index, signature in enumerate(ordered_signatures)
+    }
+
+
+def _named_artifact_entry(fact: dict[str, Any]) -> dict[str, Any]:
+    item = fact["item"]
+    return {
+        "artifact_id": item["artifact_id"],
+        "symbol": item["symbol"],
+        "full_name": item["full_name"],
+        "kind": item["kind"],
+        "signature": item["signature"],
+        "direct_consumers": _full_collection(fact["direct"]),
+        "architecture": fact["architecture"],
+        "downstream_module_reachability": fact["downstream"],
+        "evidence_scope": "direct_static_artifact_consumption",
+    }
+
+
+def _compact_architecture(architecture: dict[str, Any]) -> dict[str, Any]:
+    if not architecture.get("available"):
+        return dict(architecture)
+    return {
+        key: value
+        for key, value in architecture.items()
+        if key not in {"identity_partitions", "cross_layer_sample"}
+    }
+
+
+def _compact_downstream(downstream: dict[str, Any], downstream_ref: int | None) -> dict[str, Any]:
+    result = {
+        key: value
+        for key, value in downstream.items()
+        if key
+        not in {
+            "items",
+            "truncated",
+            "production_downstream_sample",
+            "test_downstream_sample",
+            "unknown_downstream_sample",
+        }
+    }
+    if downstream.get("available"):
+        result["downstream_set_ref"] = downstream_ref
+        result.setdefault("truncated", False)
+    return result
+
+
+def _project_fields(result: dict[str, Any], fields: list[str] | None, support: tuple[str, ...] = ()) -> dict[str, Any]:
+    if fields is None:
+        return result
+    projected = {field: result[field] for field in fields if field in result}
+    for field in support:
+        if field in result:
+            projected[field] = result[field]
+    return projected
+
+
+def _build_named_projection(
+    *,
+    module_name: str,
+    module_id: str | None,
+    total_artifacts: int,
+    artifact_facts: list[dict[str, Any]],
+    aggregate: dict[str, Any] | None,
+    freshness: dict[str, Any] | None,
+    artifacts_projected: bool,
+    fields: list[str] | None,
+) -> dict[str, Any]:
+    records = {
+        str(fact["item"]["artifact_id"] or fact["item"]["full_name"]): _named_artifact_entry(fact)
+        for fact in artifact_facts
+    }
+    returned_count = len(records) if artifacts_projected else 0
+    base: dict[str, Any] = {
+        "module": module_name,
+        "module_id": module_id,
+        "artifact_count_total": total_artifacts,
+        "artifact_count_returned": returned_count,
+        "artifacts": records if artifacts_projected else {},
+        "aggregate": aggregate,
+        "data_source": "live_canonical_state",
+        "state_freshness": freshness,
+    }
+    if aggregate is not None:
+        aggregate["artifact_count_returned"] = returned_count
+    return _project_fields(base, fields)
+
+
+def _build_indexed_projection(
+    *,
+    module_name: str,
+    module_id: str | None,
+    total_artifacts: int,
+    artifact_facts: list[dict[str, Any]],
+    aggregate: dict[str, Any] | None,
+    freshness: dict[str, Any] | None,
+    artifacts_projected: bool,
+    fields: list[str] | None,
+    module_path_to_id: dict[str, str],
+    state: Any,
+    all_direct: set[str],
+    all_downstream: set[str],
+    reverse_adjacency: dict[str, set[str]] | None,
+    cached_analytics: dict[str, Any],
+) -> dict[str, Any]:
+    identity_payload = {
+        "direct": sorted(all_direct),
+        "downstream": sorted(all_downstream),
+        "artifacts": [
+            {"direct": fact["direct"], "downstream": fact.get("downstream_names", [])}
+            for fact in artifact_facts
+        ],
+    }
+    if not _has_module_identity_collection(identity_payload):
+        return _build_named_projection(
+            module_name=module_name,
+            module_id=module_id,
+            total_artifacts=total_artifacts,
+            artifact_facts=artifact_facts,
+            aggregate=aggregate,
+            freshness=freshness,
+            artifacts_projected=artifacts_projected,
+            fields=fields,
+        )
+
+    module_index, sets, ordinal, refs = _build_shared_sets(
+        artifact_facts=artifact_facts,
+        all_direct=all_direct,
+        all_downstream=all_downstream,
+        module_path_to_id=module_path_to_id,
+        state=state,
+    )
+    layers = cached_analytics.get("module_layers", {}) or {}
+    layer_values = sorted({str(layer) for layer in layers.values() if layer is not None})
+    layer_code = {value: index for index, value in enumerate(layer_values)}
+    names_by_id = sorted(
+        ((name, _module_id_for(name, module_path_to_id, state)) for name in ordinal),
+        key=lambda item: _id_sort_key(str(item[1])),
+    )
+    layer_codes = [layer_code.get(layers.get(name)) for name, _ in names_by_id]
+
+    encoded_artifacts: dict[str, Any] = {}
+    for fact in artifact_facts:
+        item = fact["item"]
+        direct_signature = tuple(sorted(ordinal[name] for name in fact["direct"]))
+        downstream_signature = (
+            tuple(sorted(ordinal[name] for name in fact["downstream_names"]))
+            if fact["downstream"].get("available")
+            else None
+        )
+        encoded: dict[str, Any] = {
+            "artifact_id": item["artifact_id"],
+            "symbol": item["symbol"],
+            "kind": item["kind"],
+            "signature": item["signature"],
+            "direct_set_ref": refs[direct_signature],
+            "direct_consumer_count": len(fact["direct"]),
+            "architecture": _compact_architecture(fact["architecture"]),
+            "downstream_module_reachability": _compact_downstream(
+                fact["downstream"],
+                refs[downstream_signature] if downstream_signature is not None else None,
+            ),
+            "evidence_scope": "direct_static_artifact_consumption",
+        }
+        if fact["downstream"].get("available"):
+            encoded["downstream_count"] = len(fact["downstream_names"])
+        encoded_artifacts[str(item["artifact_id"] or item["full_name"])] = encoded
+
+    encoded_aggregate = None
+    if aggregate is not None:
+        direct_signature = tuple(sorted(ordinal[name] for name in all_direct))
+        downstream_signature = tuple(sorted(ordinal[name] for name in all_downstream))
+        direct_named = aggregate["unique_direct_consumers"]
+        downstream_named = aggregate["unique_downstream_consumers"]
+        encoded_aggregate = {
+            key: value
+            for key, value in aggregate.items()
+            if key not in {"unique_direct_consumers", "unique_downstream_consumers"}
+        }
+        encoded_aggregate.update(
+            {
+                "direct_set_ref": refs[direct_signature],
+                "downstream_set_ref": refs[downstream_signature] if reverse_adjacency is not None else None,
+                "unique_direct_consumer_count": len(all_direct),
+                "unique_downstream_consumer_count": len(all_downstream),
+                "unique_direct_consumers": {
+                    "total": direct_named.get("total", len(all_direct)),
+                    "truncated": False,
+                    "set_ref": refs[direct_signature],
+                },
+                "unique_downstream_consumers": {
+                    key: value
+                    for key, value in downstream_named.items()
+                    if key not in {"items", "truncated"}
+                },
+            }
+        )
+        if downstream_named.get("available"):
+            encoded_aggregate["unique_downstream_consumers"]["set_ref"] = refs[downstream_signature]
+            encoded_aggregate["unique_downstream_consumers"]["truncated"] = False
+
+    base: dict[str, Any] = {
+        "schema": "module_blast_radius.lossless.v1",
+        "representation": "indexed",
+        "module": module_name,
+        "module_id": module_id,
+        "module_layer": layers.get(module_name),
+        "module_index": module_index,
+        "module_layers": {"dictionary": layer_values, "codes": layer_codes},
+        "sets": sets,
+        "artifact_count_total": total_artifacts,
+        "artifact_count_returned": len(encoded_artifacts) if artifacts_projected else 0,
+        "artifacts": encoded_artifacts if artifacts_projected else {},
+        "aggregate": encoded_aggregate,
+        "data_source": "live_canonical_state",
+        "state_freshness": freshness,
+    }
+    if aggregate is not None:
+        aggregate["artifact_count_returned"] = base["artifact_count_returned"]
+    return _project_fields(
+        base,
+        fields,
+        support=("schema", "representation", "module_layer", "module_index", "module_layers", "sets"),
+    )
+
+
+def _serialize_payload(
+    payload: dict[str, Any], *, semantic_representation: str, allow_large_output: bool, requested_count: int
+) -> str:
+    if semantic_representation == "indexed":
+        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
+        size = len(serialized.encode("utf-8"))
+        if size <= _LOSSLESS_COMPACT_MAX_BYTES or allow_large_output:
+            return serialized
+        return json.dumps(
+            {
+                "status": "confirmation_required",
+                "reason": "Complete lossless indexed module context exceeds the local safety ceiling.",
+                "requested_count": requested_count,
+                "estimated_output_bytes": size,
+                "warning_threshold_bytes": _LOSSLESS_COMPACT_MAX_BYTES,
+                "retry": {"allow_large_output": True},
+                "retry_instruction": "Repeat the same call with allow_large_output=true.",
+            },
+            indent=2,
+            ensure_ascii=False,
+        )
+    return guard_large_output(
+        json.dumps(payload, indent=2, ensure_ascii=False),
+        allow_large_output=allow_large_output,
+        requested_count=requested_count,
+        reason="Estimated module blast-radius output exceeds the recommended context size.",
+        retry_instruction="Repeat the same get_module_blast_radius call with representation='indexed' or allow_large_output=true.",
+    )
+
+
+def get_module_blast_radius(
+    repo_path: str,
+    module: str = "",
+    compact: bool = True,
+    fields: list[str] | None = None,
+    representation: str = "auto",
+    allow_large_output: bool = False,
+) -> str:
+    if not mcp_rep.is_supported_representation(representation):
+        return _json_error(
+            "Unsupported representation for get_module_blast_radius",
+            representation=representation,
+            allowed_representations=sorted(mcp_rep.ALLOWED_REPRESENTATIONS),
+        )
+    if fields is not None:
+        unknown = sorted(set(fields) - _ALLOWED_FIELDS)
+        if unknown:
+            return _json_error(
+                "Unsupported fields for get_module_blast_radius",
+                unknown_fields=unknown,
+                allowed_fields=sorted(_ALLOWED_FIELDS),
+            )
+    if not isinstance(module, str) or not module.strip():
+        return _json_error("module is required.")
+
+    root = Path(repo_path).expanduser().resolve()
+    try:
+        engine = mcp_runtime.get_or_init_engine(root)
+        state = getattr(engine, "state", None) if engine else None
+        if state is None or getattr(state, "resync_required", False):
+            return "Error: No usable canonical LIVE state. Run analyze_project first."
+
+        registry = getattr(engine, "registry", None) if engine else None
+        live_registry = bool(
+            engine is not None
+            and getattr(engine, "provenance", None) == "live"
+            and getattr(state, "provenance", None) == "live"
+            and not getattr(state, "resync_required", False)
+            and registry is not None
+            and hasattr(registry, "read_transaction")
+        )
+        if live_registry:
+            with registry.read_transaction():
+                module_path_to_id, module_id_to_path, _artifact_path_to_id, _artifact_id_to_path = registry_maps_from_state(registry._state)
+        else:
+            module_path_to_id, module_id_to_path, _artifact_path_to_id, _artifact_id_to_path = query_helpers.read_registries(root)
+
+        effective = module.strip()
+        if query_helpers.is_module_id(effective):
+            resolution = query_helpers.resolve_module_identity(effective, module_path_to_id, module_id_to_path)
+            if resolution.get("status") != "resolved":
+                return f"Module '{effective}' not found in registry or canonical LIVE state. Check the module name or run an analysis."
+            module_name = resolution["module"]
+        else:
+            module_name = normalize_module_path_to_dotted(effective, repo_root=str(root))
+            live_modules = getattr(state, "modules", {}) or {}
+            live_artifacts = getattr(state, "artifacts", {}) or {}
+            if module_name not in live_modules and module_name not in live_artifacts:
+                resolution = query_helpers.resolve_module_identity(module_name, module_path_to_id, module_id_to_path)
+                if resolution.get("status") == "ambiguous":
+                    return json.dumps({"status": "ambiguous", "query": effective, "candidates": resolution.get("candidates", []), "data_source": "active_module_registry"}, indent=2, ensure_ascii=False)
+                if resolution.get("status") == "resolved":
+                    module_name = resolution["module"]
+                else:
+                    return f"Module '{effective}' not found in registry or canonical LIVE state. Check the module name or run an analysis."
+
+        unavailable = query_helpers.module_truth_unavailable(state, module_name)
+        if unavailable:
+            return json.dumps(unavailable, indent=2, ensure_ascii=False)
+
+        live_artifacts = getattr(state, "artifacts", {}) or {}
+        module_data = live_artifacts.get(module_name, {}) or {}
+        catalog = query_helpers.canonical_symbol_catalog(module_data)
+        signatures = ((module_data.get("symbols", {}) or {}).get("signatures", {}) or {})
+        all_catalog = [
+            {
+                "symbol": str(symbol),
+                "kind": kind,
+                "full_name": f"{module_name}::{symbol}",
+                "artifact_id": _artifact_path_to_id.get(f"{module_name}::{symbol}"),
+                "signature": signatures.get(symbol),
+            }
+            for symbol, kind in catalog.items()
+        ]
+        all_catalog.sort(key=lambda item: (item["full_name"].casefold(), item["full_name"]))
+        total_artifacts = len(all_catalog)
+        artifacts_projected = fields is None or "artifacts" in fields
+        aggregate_projected = fields is None or "aggregate" in fields
+        wants_data = artifacts_projected or aggregate_projected
+        consumption_fresh = artifact_consumption_is_fresh(state) if wants_data and total_artifacts else True
+        if total_artifacts and not consumption_fresh:
+            return _json_error(
+                "Canonical artifact consumption is unavailable or stale.",
+                available=False,
+                module=module_name,
+                state_freshness=query_helpers.build_state_freshness(root, state, engine=engine),
+            )
+
+        reverse_adjacency: dict[str, set[str]] | None = None
+        if wants_data and total_artifacts:
+            dependency_graph = getattr(state, "dependency_graph", None)
+            if dependency_graph is not None:
+                reverse_adjacency = graph_ops.build_reverse_adjacency(dependency_graph)
+
+        closure_cache: dict[str, set[str]] = {}
+        artifact_facts: list[dict[str, Any]] = []
+        all_direct: set[str] = set()
+        all_downstream: set[str] = set()
+        for item in all_catalog if wants_data else []:
+            direct = sorted(set(query_helpers.canonical_symbol_consumers(state, module_name, item["symbol"])))
+            all_direct.update(direct)
+            downstream, downstream_names = _downstream_reachability(
+                definer_module=module_name,
+                direct_consumers=direct,
+                reverse_adjacency=reverse_adjacency,
+                state=state,
+                closure_cache=closure_cache,
+            )
+            all_downstream.update(downstream_names)
+            artifact_facts.append(
+                {
+                    "item": item,
+                    "direct": direct,
+                    "architecture": _architecture(state=state, definer_module=module_name, direct_consumers=direct),
+                    "downstream": downstream,
+                    "downstream_names": sorted(downstream_names),
+                }
+            )
+
+        # Aggregate downstream is additional reachability beyond every direct
+        # artifact consumer. Per-artifact sets above are intentionally intact.
+        all_downstream.difference_update(all_direct)
+        all_downstream.discard(module_name)
+
+        cached = getattr(state, "cached_analytics", {}) or {}
+        cached_for_projection = (
+            cached
+            if getattr(state, "cached_analytics_state", "deferred") == "fresh"
+            and isinstance(cached, dict)
+            else {}
+        )
+        aggregate: dict[str, Any] | None = None
+        returned_count = total_artifacts if artifacts_projected else 0
+        if aggregate_projected:
+            consumed = [str(f["item"]["artifact_id"] or f["item"]["full_name"]) for f in artifact_facts if f["direct"]]
+            unconsumed = [str(f["item"]["artifact_id"] or f["item"]["full_name"]) for f in artifact_facts if not f["direct"]]
+            impact = sorted(
+                artifact_facts,
+                key=lambda f: (
+                    -(f["downstream"].get("total_downstream_count", 0) if f["downstream"].get("available") else 0),
+                    -len(f["direct"]),
+                    f["item"]["full_name"],
+                ),
+            )
+            aggregate = {
+                "artifact_count_total": total_artifacts,
+                "artifact_count_returned": returned_count,
+                "unique_direct_consumers": _full_collection(sorted(all_direct)),
+                "unique_downstream_consumers": _aggregate_downstream_view(all_downstream, state=state, reverse_adjacency=reverse_adjacency),
+                "consumed_artifact_ids": consumed,
+                "unconsumed_artifact_ids": unconsumed,
+                "highest_impact_artifact_ids": [str(f["item"]["artifact_id"] or f["item"]["full_name"]) for f in impact],
+            }
+
+        freshness = None
+        if fields is None or "state_freshness" in fields:
+            freshness = query_helpers.build_state_freshness(root, state, engine=engine)
+            truth = query_helpers.module_current_truth(state, module_name)
+            freshness["canonical_state"] = truth.get("state", freshness.get("canonical_state"))
+            freshness.setdefault("families", {})["module"] = truth.get("state", "fresh")
+
+        module_id = module_path_to_id.get(module_name) or _module_id_for(module_name, module_path_to_id, state)
+        named_payload = _build_named_projection(
+            module_name=module_name,
+            module_id=module_id,
+            total_artifacts=total_artifacts,
+            artifact_facts=artifact_facts,
+            aggregate=aggregate,
+            freshness=freshness,
+            artifacts_projected=artifacts_projected,
+            fields=fields,
+        )
+
+        indexed_payload: dict[str, Any] | None = None
+        indexed_error: ValueError | None = None
+        if representation == "indexed" or (representation == "auto" and compact):
+            try:
+                indexed_payload = _build_indexed_projection(
+                    module_name=module_name,
+                    module_id=module_id,
+                    total_artifacts=total_artifacts,
+                    artifact_facts=artifact_facts,
+                    aggregate=aggregate,
+                    freshness=freshness,
+                    artifacts_projected=artifacts_projected,
+                    fields=fields,
+                    module_path_to_id=module_path_to_id,
+                    state=state,
+                    all_direct=all_direct,
+                    all_downstream=all_downstream,
+                    reverse_adjacency=reverse_adjacency,
+                    cached_analytics=cached_for_projection,
+                )
+            except ValueError as exc:
+                indexed_error = exc
+
+        identity_present = _has_module_identity_collection(named_payload)
+        if representation == "indexed" and indexed_error is not None:
+            return _json_error(str(indexed_error))
+        if representation == "named":
+            payload, selected_representation = named_payload, "named"
+        elif representation == "indexed":
+            payload = indexed_payload if indexed_payload is not None else named_payload
+            selected_representation = "indexed" if indexed_payload is not None and "schema" in indexed_payload else "named"
+        elif not compact:
+            payload, selected_representation = named_payload, "named"
+        elif indexed_payload is None or indexed_error is not None or not identity_present:
+            # A missing indexed candidate is a real named fallback.  It must
+            # retain named semantics and the named output policy.
+            payload, selected_representation = named_payload, "named"
+        else:
+            named_candidate = json.loads(json.dumps(named_payload, ensure_ascii=False))
+            indexed_candidate = json.loads(json.dumps(indexed_payload, ensure_ascii=False))
+            # Compare final, symmetrically annotated candidates.  Metadata is
+            # emitted only when real identity collections are in the projection.
+            named_candidate["consumer_representation"] = {"representation": "named", "requested_representation": "auto"}
+            indexed_candidate["consumer_representation"] = {"representation": "indexed", "index_kind": "module", "resolve_via": "lookup_index_entries"}
+            sizes = mcp_rep.representation_size_stats(named_candidate, indexed_candidate)
+            if sizes["indexed_bytes"] < sizes["named_bytes"]:
+                payload, selected_representation = indexed_candidate, "indexed"
+            else:
+                payload, selected_representation = named_candidate, "named"
+
+        return _serialize_payload(payload, semantic_representation=selected_representation, allow_large_output=allow_large_output, requested_count=returned_count)
+    except ValueError as exc:
+        return _json_error(str(exc))
+    except Exception as exc:
+        return f"Error reading module blast radius: {exc}"
```

### contextor/mcp/docs/get_module_blast_radius.json

```diff
warning: in the working copy of 'contextor/mcp/docs/get_module_blast_radius.json', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/docs/get_module_blast_radius.json b/contextor/mcp/docs/get_module_blast_radius.json
new file mode 100644
index 0000000..a1b7804
--- /dev/null
+++ b/contextor/mcp/docs/get_module_blast_radius.json
@@ -0,0 +1,46 @@
+{
+  "version": "1.0.0",
+  "tool": "get_module_blast_radius",
+  "purpose": [
+    "Return the complete canonical blast radius of one module in a single call. The result contains every canonical artifact, every direct artifact consumer, every downstream identity, and aggregate impact facts from one fresh state projection."
+  ],
+  "parameters": [
+    "repo_path (string, required): canonical repository root.",
+    "module (string, required): canonical dotted module name, repository-relative or absolute Python path, or active module ID.",
+    "compact (boolean, default true): select the lossless compact serialization; this never bounds or samples artifacts, consumers, or downstream identities.",
+    "fields (array of strings or null, default null): optional top-level projection. Allowed values are module, module_id, artifact_count_total, artifact_count_returned, artifacts, aggregate, data_source, and state_freshness. Projection can intentionally omit semantic collections, but does not change facts used for aggregate calculation.",
+    "representation (string, default auto): lossless repeated-module encoding: auto, named, or indexed. Auto chooses the smaller complete candidate without an interaction envelope.",
+    "allow_large_output (boolean, default false): explicit named output uses the shared large-output preflight; complete indexed output uses this tool's local safety ceiling."
+  ],
+  "behavior": [
+    "Always resolves one module and projects the complete canonical artifact set. artifact_count_total is the canonical count; artifact_count_returned is the number of serialized top-level artifact entries (zero when artifacts is projected out).",
+    "compact and indexed are lossless encodings, not previews. They contain schema=module_blast_radius.lossless.v1, canonical persistent artifact IDs, module_index containing canonical persistent module IDs, deterministic deduplicated sets of local ordinal references, and module layer codes. Local ordinals are response-local compression references, never registry IDs; lookup_index_entries can expand canonical module IDs to names.",
+    "Named output is a complete readable expansion with all direct and downstream identity collections. No artifact, consumer, downstream, evidence, sample, or impact collection is truncated.",
+    "The complete indexed representation derives same-module, same-layer, cross-layer, test, unknown, production-downstream, test-downstream, and unknown-downstream identities from direct/downstream set references and shared module layer metadata instead of duplicating sets.",
+    "Precedence is explicit: auto with compact=true compares complete candidates and normally selects indexed; auto with compact=false returns the full named/readable result; explicit named always returns named; explicit indexed always returns indexed when losslessly possible and otherwise returns a structured error.",
+    "Indexed support tables (schema, representation, module_index, module_layers, and sets) are attached only when the projected artifacts or aggregate contain references that require them. fields=[module] therefore has no orphan tables; fields=[artifacts] or fields=[aggregate] includes every table required to decode its refs.",
+    "All canonical facts are materialized once. The tool performs one read-only registry transaction, builds one reverse adjacency, and caches each unique direct-consumer seed closure at most once. It never calls get_artifact_blast_radius internally, scans the repository, reads source/AST at query time, or requires per-artifact follow-up calls.",
+    "Per-artifact downstream_module_reachability retains the exact get_artifact_blast_radius closure semantics. aggregate.unique_downstream_consumers means additional transitive module reachability beyond all module-level direct artifact consumers; unique_direct_consumers and unique_downstream_consumers are disjoint only at this module aggregate level.",
+    "Aggregate calculations always use the full canonical artifact set, even when fields projects artifacts out. Aggregate exposes consumed_artifact_ids, unconsumed_artifact_ids, and deterministic highest_impact_artifact_ids ordered by downstream count descending, direct count descending, and full identity ascending.",
+    "Auto chooses the smaller of final lossless named and indexed candidates. It never returns representation_decision_required for a valid indexed candidate; representation metadata is omitted when the final projection contains no repeated module identity collection."
+  ],
+  "freshness": [
+    "Requires a usable canonical engine and fails closed when the engine is missing or state.resync_required is true.",
+    "Artifact consumption is required to be fresh when the module has artifacts; stale or unavailable consumption returns an explicit unavailable/error response rather than fabricated empty consumers.",
+    "Missing dependency_graph leaves per-artifact and aggregate downstream reachability explicitly unavailable, while direct canonical artifact consumption remains available.",
+    "Stale or deferred cached analytics leaves architecture and layer classification explicitly unavailable; empty sets are never substituted for unavailable, stale, deferred, missing, or recovery-only families.",
+    "state_freshness identifies canonical revision, provenance, family states, and advisory warning. The query performs no source or AST reads."
+  ],
+  "errors": [
+    "Unsupported representation or fields return a structured error with the current allowlist.",
+    "Indexed output fails closed if a canonical module identity has no persistent module ID; use named output or repair the canonical registry/state.",
+    "Explicit named output above the shared context threshold returns confirmation_required with retry guidance. A pathological indexed result above this tool's local complete-context ceiling returns the same safe confirmation protocol."
+  ],
+  "usage_notes": [
+    "Use get_module_blast_radius(repo_path, module) for a complete default result. Auto selects a complete lossless representation and does not require a second call.",
+    "Use representation=named when a human-readable expansion is required; it may trigger the large-output guard. Use representation=indexed for canonical persistent module IDs plus lossless shared sets.",
+    "Use lookup_index_entries to expand module_index IDs if names are needed. No per-artifact get_artifact_blast_radius calls are required to reconstruct the module blast radius.",
+    "fields is projection only: excluding artifacts sets artifact_count_returned to zero but does not reduce canonical aggregate calculations."
+  ],
+  "examples": []
+}
```

### tests/mcp/tools/test_get_module_blast_radius.py

```diff
warning: in the working copy of 'tests/mcp/tools/test_get_module_blast_radius.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/mcp/tools/test_get_module_blast_radius.py b/tests/mcp/tools/test_get_module_blast_radius.py
new file mode 100644
index 0000000..e1179c6
--- /dev/null
+++ b/tests/mcp/tools/test_get_module_blast_radius.py
@@ -0,0 +1,482 @@
+import json
+import importlib
+from contextlib import contextmanager
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.analysis.incremental import graph_ops
+from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.core.domain.graph import ProjectGraph
+from contextor.core.report_query import normalize_module_path_to_dotted
+from contextor.mcp import query_helpers, representation as mcp_rep, runtime as mcp_runtime
+from contextor.mcp.tools.get_artifact_blast_radius import get_artifact_blast_radius
+from contextor.mcp.tools.get_module_blast_radius import get_module_blast_radius
+
+
+class _LiveRegistry:
+    def __init__(self, state):
+        self._state = state
+        self.read_transaction_count = 0
+
+    @contextmanager
+    def read_transaction(self):
+        self.read_transaction_count += 1
+        yield
+
+
+def _registry_state():
+    modules = {
+        "pkg.mod": "10/1",
+        "pkg.consumer": "11/1",
+        "pkg.after": "12/1",
+        "pkg.leaf": "13/1",
+        "tests.consumer": "14/1",
+        "pkg.dep": "15/1",
+        "pkg.soft_after": "16/1",
+    }
+    artifacts = {
+        "pkg.mod::alpha": "A100/1",
+        "pkg.mod::beta": "A101/1",
+        "pkg.mod::gamma": "A102/1",
+    }
+    return {
+        "module_registry": {"path_to_id": modules, "id_to_path": {v: k for k, v in modules.items()}},
+        "artifact_registry": {"path_to_id": artifacts, "id_to_path": {v: k for k, v in artifacts.items()}},
+    }
+
+
+def _fixture(monkeypatch):
+    state = RepositoryAnalysisState(
+        modules={
+            name: SimpleNamespace(module_id=module_id, path=name.replace(".", "/") + ".py")
+            for name, module_id in {
+                "pkg.mod": "10/1",
+                "pkg.consumer": "11/1",
+                "pkg.after": "12/1",
+                "pkg.leaf": "13/1",
+                "tests.consumer": "14/1",
+                "pkg.dep": "15/1",
+                "pkg.soft_after": "16/1",
+            }.items()
+        },
+        artifacts={
+            "pkg.mod": {
+                "own_symbols": ["alpha", "beta", "gamma"],
+                "symbols": {
+                    "functions": ["alpha", "beta", "gamma"],
+                    "signatures": {"alpha": "def alpha()", "beta": "def beta()", "gamma": "def gamma()"},
+                },
+            }
+        },
+        artifact_consumption={
+            "pkg.mod::alpha": {"consumers": ["pkg.consumer", "tests.consumer"], "channels": {}},
+            "pkg.mod::beta": {"consumers": ["pkg.consumer"], "channels": {}},
+            "pkg.mod::gamma": {"consumers": [], "channels": {}},
+        },
+        artifact_consumption_state="fresh",
+        dependency_graph=ProjectGraph(
+            hard_edges={
+                "pkg.consumer": {"pkg.dep"},
+                "pkg.after": {"pkg.consumer"},
+                "pkg.leaf": {"pkg.after"},
+                "tests.consumer": {"pkg.consumer"},
+            },
+            soft_edges={"pkg.soft_after": {"pkg.consumer"}},
+        ),
+        cached_analytics={
+            "module_layers": {
+                "pkg.mod": "engine",
+                "pkg.consumer": "runtime",
+                "pkg.after": "runtime",
+                "pkg.leaf": "contract",
+                "tests.consumer": "tests",
+                "pkg.soft_after": "runtime",
+            }
+        },
+        cached_analytics_state="fresh",
+    )
+    state.provenance = "live"
+    registry = _LiveRegistry(_registry_state())
+    engine = SimpleNamespace(state=state, provenance="live", registry=registry)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(
+        query_helpers,
+        "build_state_freshness",
+        lambda *args, **kwargs: {
+            "canonical_state": "fresh",
+            "workspace_sync": "unverified",
+            "canonical_revision": 7,
+            "provenance": "live",
+            "families": {"module": "fresh", "graph": "fresh", "artifact_consumption": "fresh"},
+            "advisory_warning": None,
+        },
+    )
+    return state, registry
+
+
+def _decode_indexed(payload, registry_state):
+    id_to_name = registry_state["module_registry"]["id_to_path"]
+    sets = payload["sets"]
+    index = payload["module_index"]
+
+    def decode(ref):
+        return sorted(id_to_name[index[ordinal]] for ordinal in sets[ref])
+
+    layer_payload = payload.get("module_layers", {})
+    layer_dictionary = layer_payload.get("dictionary", [])
+    module_layers = {
+        id_value: (
+            layer_dictionary[layer_payload["codes"][ordinal]]
+            if layer_payload["codes"][ordinal] is not None
+            else None
+        )
+        for ordinal, id_value in enumerate(index)
+    }
+
+    def architecture_semantics(entry, direct):
+        architecture = entry["architecture"]
+        if not architecture.get("available"):
+            return architecture
+        definer_layer = architecture.get("definer_layer")
+        same_module = [module for module in direct if module == payload["module"]]
+        # The registry maps IDs to names; direct values are names, so look up
+        # the layer by the reverse index position instead of by name.
+        name_to_layer = {
+            id_to_name[module_id]: layer
+            for module_id, layer in module_layers.items()
+            if module_id in id_to_name
+        }
+        same_layer = [module for module in direct if module != payload["module"] and name_to_layer.get(module) == definer_layer]
+        tests = [module for module in direct if module != payload["module"] and name_to_layer.get(module) == "tests"]
+        unknown = [module for module in direct if module != payload["module"] and name_to_layer.get(module) is None]
+        cross = [
+            {"module": module, "layer": name_to_layer[module]}
+            for module in direct
+            if module != payload["module"]
+            and name_to_layer.get(module) not in (None, "tests", definer_layer)
+        ]
+        return {
+            **architecture,
+            "identity_partitions": {
+                "same_module": same_module,
+                "same_layer": same_layer,
+                "cross_layer": cross,
+                "tests": tests,
+                "unknown": unknown,
+            },
+        }
+
+    result = {}
+    for artifact_id, entry in payload["artifacts"].items():
+        downstream = entry["downstream_module_reachability"]
+        direct = decode(entry["direct_set_ref"])
+        downstream_items = decode(downstream["downstream_set_ref"]) if downstream.get("available") else None
+        downstream_semantics = dict(downstream)
+        if downstream_items is not None:
+            downstream_semantics["items"] = downstream_items
+            layers_by_name = {
+                id_to_name[module_id]: layer
+                for module_id, layer in module_layers.items()
+                if module_id in id_to_name
+            }
+            production = [module for module in downstream_items if layers_by_name.get(module) not in (None, "tests")]
+            tests = [module for module in downstream_items if layers_by_name.get(module) == "tests"]
+            unknown = [module for module in downstream_items if layers_by_name.get(module) is None]
+            downstream_semantics.update({
+                "production_downstream_sample": {"total": len(production), "items": production, "truncated": False},
+                "test_downstream_sample": {"total": len(tests), "items": tests, "truncated": False},
+                "unknown_downstream_sample": {"total": len(unknown), "items": unknown, "truncated": False},
+            })
+        result[artifact_id] = {
+            "symbol": entry["symbol"],
+            "kind": entry["kind"],
+            "signature": entry["signature"],
+            "direct": direct,
+            "architecture": architecture_semantics(entry, direct),
+            "downstream": downstream_semantics,
+        }
+    aggregate = payload.get("aggregate")
+    downstream_ref = aggregate.get("downstream_set_ref")
+    return result, {
+        "direct": decode(aggregate["direct_set_ref"]),
+        "downstream": decode(downstream_ref) if downstream_ref is not None else None,
+        "consumed": aggregate["consumed_artifact_ids"],
+        "unconsumed": aggregate["unconsumed_artifact_ids"],
+        "impact": aggregate["highest_impact_artifact_ids"],
+        "downstream_state": {
+            key: value
+            for key, value in aggregate["unique_downstream_consumers"].items()
+            if key != "set_ref"
+        },
+    }
+
+
+def test_default_is_complete_and_one_registry_read_one_reverse_build(tmp_path, monkeypatch):
+    _, registry = _fixture(monkeypatch)
+    calls = 0
+    closures = 0
+    original_build = graph_ops.build_reverse_adjacency
+    original_closure = graph_ops.calculate_affected_set_from_reverse
+
+    def counted_build(*graphs):
+        nonlocal calls
+        calls += 1
+        return original_build(*graphs)
+
+    def counted_closure(*args):
+        nonlocal closures
+        closures += 1
+        return original_closure(*args)
+
+    monkeypatch.setattr(graph_ops, "build_reverse_adjacency", counted_build)
+    monkeypatch.setattr(graph_ops, "calculate_affected_set_from_reverse", counted_closure)
+    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod"))
+
+    assert result["artifact_count_total"] == result["artifact_count_returned"] == 3
+    assert len(result["artifacts"]) == 3
+    assert result["aggregate"]["artifact_count_returned"] == 3
+    assert calls == 1
+    assert registry.read_transaction_count == 1
+    assert closures == 2
+
+
+def test_named_and_indexed_are_semantically_lossless(tmp_path, monkeypatch):
+    _fixture(monkeypatch)
+    named = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=False, representation="named"))
+    indexed = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=True, representation="indexed"))
+    decoded_artifacts, decoded_aggregate = _decode_indexed(indexed, _registry_state())
+
+    assert indexed["schema"] == "module_blast_radius.lossless.v1"
+    assert len(indexed["artifacts"]) == 3
+    for artifact_id, expected in named["artifacts"].items():
+        actual = decoded_artifacts[artifact_id]
+        assert actual["symbol"] == expected["symbol"]
+        assert actual["kind"] == expected["kind"]
+        assert actual["signature"] == expected["signature"]
+        assert actual["direct"] == expected["direct_consumers"]["items"]
+        expected_architecture = expected["architecture"]
+        assert actual["architecture"]["available"] == expected_architecture["available"]
+        assert actual["architecture"]["identity_partitions"] == expected_architecture["identity_partitions"]
+        expected_downstream = expected["downstream_module_reachability"]
+        assert actual["downstream"]["available"] == expected_downstream["available"]
+        assert actual["downstream"].get("items") == expected_downstream.get("items")
+        for key in ("layer_classification_available", "production_downstream_count", "test_downstream_count", "unknown_layer_downstream_count"):
+            assert actual["downstream"].get(key) == expected_downstream.get(key)
+        if expected_downstream.get("layer_classification_available"):
+            for key in ("production_downstream_sample", "test_downstream_sample", "unknown_downstream_sample"):
+                assert actual["downstream"].get(key) == expected_downstream.get(key)
+    assert decoded_aggregate["direct"] == named["aggregate"]["unique_direct_consumers"]["items"]
+    assert decoded_aggregate["downstream"] == named["aggregate"]["unique_downstream_consumers"]["items"]
+    assert decoded_aggregate["consumed"] == named["aggregate"]["consumed_artifact_ids"]
+    assert decoded_aggregate["unconsumed"] == named["aggregate"]["unconsumed_artifact_ids"]
+    assert decoded_aggregate["impact"] == named["aggregate"]["highest_impact_artifact_ids"]
+
+
+def test_all_downstream_is_complete_and_aggregate_is_disjoint(tmp_path, monkeypatch):
+    _fixture(monkeypatch)
+    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
+    direct = set(result["aggregate"]["unique_direct_consumers"]["items"])
+    downstream = set(result["aggregate"]["unique_downstream_consumers"]["items"])
+    assert "tests.consumer" in direct
+    assert "tests.consumer" not in downstream
+    assert direct.isdisjoint(downstream)
+    assert all(not collection.get("truncated") for artifact in result["artifacts"].values() for collection in (
+        [artifact["direct_consumers"], artifact["downstream_module_reachability"]]
+        if artifact["downstream_module_reachability"].get("available") else [artifact["direct_consumers"]]
+    ))
+
+
+def test_highest_impact_order_is_deterministic(tmp_path, monkeypatch):
+    _fixture(monkeypatch)
+    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
+    impact = result["aggregate"]["highest_impact_artifact_ids"]
+    facts = result["artifacts"]
+    expected = sorted(impact, key=lambda artifact_id: (
+        -facts[artifact_id]["downstream_module_reachability"].get("total_downstream_count", 0),
+        -facts[artifact_id]["direct_consumers"]["total"],
+        facts[artifact_id]["full_name"],
+    ))
+    assert impact == expected
+
+
+def test_fields_projection_keeps_aggregate_full_but_returned_count_zero(tmp_path, monkeypatch):
+    state, _ = _fixture(monkeypatch)
+    symbols = [f"symbol_{index}" for index in range(12)]
+    state.artifacts["pkg.mod"] = {"own_symbols": symbols, "symbols": {"functions": symbols}}
+    state.artifact_consumption = {f"pkg.mod::{symbol}": {"consumers": [], "channels": {}} for symbol in symbols}
+    module_only = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["module", "artifact_count_returned"]))
+    aggregate_only = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["aggregate"]))
+    full = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["artifacts", "artifact_count_returned", "aggregate"], allow_large_output=True))
+    assert module_only["artifact_count_returned"] == 0
+    assert aggregate_only["aggregate"]["artifact_count_returned"] == 0
+    assert full["artifact_count_returned"] == len(full["artifacts"]) == 12
+    assert full["aggregate"]["artifact_count_returned"] == 12
+
+
+def test_path_and_active_id_resolution_use_canonical_normalizer(tmp_path, monkeypatch):
+    state, registry = _fixture(monkeypatch)
+    target = "contextor.core.reporting_engine.graph_analytics"
+    state.modules = {target: SimpleNamespace(module_id="10/1", path="contextor/core/reporting_engine/graph_analytics.py")}
+    state.artifacts = {target: {"own_symbols": ["analyze"], "symbols": {"functions": ["analyze"], "signatures": {"analyze": "def analyze()"}}}}
+    state.artifact_consumption = {f"{target}::analyze": {"consumers": [], "channels": {}}}
+    registry._state = {
+        "module_registry": {"path_to_id": {target: "10/1"}, "id_to_path": {"10/1": target}},
+        "artifact_registry": {"path_to_id": {f"{target}::analyze": "A100/1"}, "id_to_path": {"A100/1": f"{target}::analyze"}},
+    }
+    variants = [target, "contextor/core/reporting_engine/graph_analytics.py", r"contextor\core\reporting_engine\graph_analytics.py", str(tmp_path / "contextor" / "core" / "reporting_engine" / "graph_analytics.py"), "10/1"]
+    for variant in variants:
+        result = json.loads(get_module_blast_radius(str(tmp_path), variant))
+        assert result["module"] == target
+        if variant != "10/1":
+            assert normalize_module_path_to_dotted(variant, repo_root=str(tmp_path)) == target
+
+
+def test_auto_returns_lossless_result_without_decision_envelope(tmp_path, monkeypatch):
+    _fixture(monkeypatch)
+    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=True, representation="auto"))
+    assert result.get("status") != "representation_decision_required"
+    assert result["artifact_count_returned"] == 3
+    assert result.get("schema") == "module_blast_radius.lossless.v1"
+
+
+def test_auto_does_not_size_without_identity_collection(tmp_path, monkeypatch):
+    _fixture(monkeypatch)
+    calls = 0
+    original = mcp_rep.representation_size_stats
+
+    def counted(*args, **kwargs):
+        nonlocal calls
+        calls += 1
+        return original(*args, **kwargs)
+
+    monkeypatch.setattr(mcp_rep, "representation_size_stats", counted)
+    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["module"], representation="auto"))
+    assert result == {"module": "pkg.mod"}
+    assert calls == 0
+
+
+def test_explicit_named_guard_remains_functional(tmp_path, monkeypatch):
+    state, _ = _fixture(monkeypatch)
+    symbols = [f"symbol_{index}" for index in range(48)]
+    state.artifacts["pkg.mod"] = {"own_symbols": symbols, "symbols": {"functions": symbols, "signatures": {symbol: "x" * 900 for symbol in symbols}}}
+    state.artifact_consumption = {f"pkg.mod::{symbol}": {"consumers": [], "channels": {}} for symbol in symbols}
+    confirmation = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=False, representation="named"))
+    assert confirmation["status"] == "confirmation_required"
+
+
+@pytest.mark.parametrize(
+    "mutate, expected",
+    [
+        (lambda state: setattr(state, "artifact_consumption_state", "stale"), "error"),
+        (lambda state: setattr(state, "dependency_graph", None), "missing_graph"),
+        (lambda state: setattr(state, "cached_analytics_state", "deferred"), "stale_analytics"),
+    ],
+)
+def test_fail_closed_family_availability(tmp_path, monkeypatch, mutate, expected):
+    state, _ = _fixture(monkeypatch)
+    mutate(state)
+    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
+    if expected == "error":
+        assert result["status"] == "error" and result["available"] is False
+    elif expected == "missing_graph":
+        assert result["artifacts"]["A100/1"]["downstream_module_reachability"]["available"] is False
+    else:
+        assert result["artifacts"]["A100/1"]["architecture"]["available"] is False
+        assert result["artifacts"]["A100/1"]["downstream_module_reachability"]["layer_classification_available"] is False
+
+
+def test_indexed_zero_identity_output_has_no_representation_metadata(tmp_path, monkeypatch):
+    state, _ = _fixture(monkeypatch)
+    state.artifact_consumption = {f"pkg.mod::{symbol}": {"consumers": [], "channels": {}} for symbol in ("alpha", "beta", "gamma")}
+    state.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})
+    indexed = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="indexed"))
+    assert "schema" not in indexed
+    assert "representation" not in indexed
+    assert "consumer_representation" not in indexed
+
+
+def test_artifact_contract_semantics_remain_equal(tmp_path, monkeypatch):
+    _fixture(monkeypatch)
+    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
+    for artifact_id, entry in result["artifacts"].items():
+        expected = json.loads(get_artifact_blast_radius(str(tmp_path), artifact_name=artifact_id, compact=False, max_items=None))
+        assert entry["artifact_id"] == expected["artifact_id"]
+        assert entry["full_name"] == expected["artifact"]
+        assert entry["direct_consumers"]["total"] == expected["consumers"]["total"]
+        assert entry["direct_consumers"]["items"] == expected["consumers"]["items"]
+        assert entry["evidence_scope"] == expected["evidence_scope"]
+        assert entry["downstream_module_reachability"]["total_downstream_count"] == expected["downstream_module_reachability"]["total_downstream_count"]
+
+
+def test_aggregate_missing_graph_state_survives_indexed_encoding(tmp_path, monkeypatch):
+    state, _ = _fixture(monkeypatch)
+    state.dependency_graph = None
+    named = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
+    indexed = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="indexed"))
+    _, decoded = _decode_indexed(indexed, _registry_state())
+    expected = named["aggregate"]["unique_downstream_consumers"]
+    assert expected["available"] is False
+    assert decoded["downstream"] is None
+    assert decoded["downstream_state"]["available"] is False
+    assert decoded["downstream_state"]["reason"] == expected["reason"]
+
+
+def test_aggregate_stale_classification_state_survives_indexed_encoding(tmp_path, monkeypatch):
+    state, _ = _fixture(monkeypatch)
+    state.cached_analytics_state = "deferred"
+    named = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
+    indexed = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="indexed"))
+    _, decoded = _decode_indexed(indexed, _registry_state())
+    expected = named["aggregate"]["unique_downstream_consumers"]
+    assert expected["classification_available"] is False
+    assert decoded["downstream_state"]["classification_available"] is False
+    assert decoded["downstream_state"]["reason"] == expected["reason"]
+
+
+def test_auto_compact_precedence_and_explicit_representation_precedence(tmp_path, monkeypatch):
+    _fixture(monkeypatch)
+    auto_compact = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=True, representation="auto"))
+    auto_full = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=False, representation="auto", allow_large_output=True))
+    named_compact = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=True, representation="named", allow_large_output=True))
+    indexed_full = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=False, representation="indexed"))
+    assert auto_compact.get("schema") == "module_blast_radius.lossless.v1"
+    assert "schema" not in auto_full
+    assert "schema" not in named_compact
+    assert indexed_full.get("schema") == "module_blast_radius.lossless.v1"
+
+
+def test_indexed_fields_attach_only_required_support_tables(tmp_path, monkeypatch):
+    _fixture(monkeypatch)
+    module_only = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["module"], representation="indexed"))
+    aggregate_only = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["aggregate"], representation="indexed"))
+    artifacts_only = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["artifacts"], representation="indexed"))
+    assert "schema" not in module_only
+    assert "module_index" not in module_only
+    assert "sets" not in module_only
+    for payload in (aggregate_only, artifacts_only):
+        assert payload["schema"] == "module_blast_radius.lossless.v1"
+        assert payload["module_index"]
+        assert payload["sets"][0] == []
+
+
+def test_auto_named_fallback_uses_named_guard_when_indexed_ids_are_missing(tmp_path, monkeypatch):
+    state, registry = _fixture(monkeypatch)
+    # Remove all consumer IDs from both canonical maps and live module state.
+    for name in ("pkg.consumer", "tests.consumer", "pkg.after", "pkg.leaf", "pkg.dep", "pkg.soft_after"):
+        state.modules.pop(name, None)
+        registry._state["module_registry"]["path_to_id"].pop(name, None)
+        registry._state["module_registry"]["id_to_path"] = {
+            value: key for key, value in registry._state["module_registry"]["path_to_id"].items()
+        }
+    tool_module = importlib.import_module("contextor.mcp.tools.get_module_blast_radius")
+    observed = {}
+
+    def capture(serialized, **kwargs):
+        observed.update(kwargs)
+        return serialized
+
+    monkeypatch.setattr(tool_module, "guard_large_output", capture)
+    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=True, representation="auto"))
+    assert "schema" not in result
+    assert observed["reason"].startswith("Estimated module blast-radius")
```

### tests/mcp/tools/test_specialized_tool_contracts.py

```diff
warning: in the working copy of 'tests/mcp/tools/test_specialized_tool_contracts.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/mcp/tools/test_specialized_tool_contracts.py b/tests/mcp/tools/test_specialized_tool_contracts.py
index 57aa952..8dab3b2 100644
--- a/tests/mcp/tools/test_specialized_tool_contracts.py
+++ b/tests/mcp/tools/test_specialized_tool_contracts.py
@@ -45,6 +45,12 @@ def test_specialized_tool_contracts__get_mcp_documentation_signature():
     assert sig == "(tool: str | None = None, tools: list[str] | None = None, sections: list[str] | None = None) -> str"


+def test_specialized_tool_contracts__get_module_blast_radius_signature():
+    tools = mcp_server.mcp._tool_manager._tools
+    sig = str(inspect.signature(tools["get_module_blast_radius"].fn))
+    assert sig == "(repo_path: str, module: str = '', compact: bool = True, fields: list[str] | None = None, representation: str = 'auto', allow_large_output: bool = False) -> str"
+
+
 def test_specialized_tool_contracts__describe_canonical_state_docs_complete():
     doc = _load_doc("describe_canonical_state")
     params_text = "\n".join(doc.get("parameters", []))
@@ -90,6 +96,26 @@ def test_specialized_tool_contracts__get_mcp_documentation_docs_complete():
     assert "sections (array of strings or null, optional, default null)" in params_text


+def test_specialized_tool_contracts__get_module_blast_radius_docs_complete():
+    doc = _load_doc("get_module_blast_radius")
+    params_text = "\n".join(doc.get("parameters", []))
+    behavior_text = "\n".join(doc.get("behavior", []))
+    assert "repo_path (string, required)" in params_text
+    assert "module (string, required)" in params_text
+    assert "never bounds or samples" in params_text
+    assert "lossless compact serialization" in params_text
+    assert "module_index" in behavior_text
+    assert "module_blast_radius.lossless.v1" in behavior_text
+    assert "representation" in params_text
+    assert "allow_large_output" in params_text
+    assert "additional transitive module reachability beyond all module-level direct artifact consumers" in behavior_text
+    assert "unique_direct_consumers and unique_downstream_consumers are disjoint" in behavior_text
+    assert "exact get_artifact_blast_radius closure semantics" in behavior_text
+    assert "auto with compact=true" in behavior_text
+    assert "auto with compact=false" in behavior_text
+    assert "no orphan tables" in behavior_text
+
+
 def test_specialized_tool_contracts__documentation_default_is_index_only():
     doc = _load_doc("get_mcp_documentation")
     combined = "\n".join(doc.get("behavior", []) + doc.get("usage_notes", []))
```

FULL_SUITE_RUN_BY_AGENT=NO

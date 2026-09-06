# get_module_blast_radius — final contract-gap fixes

Zakres: wyłącznie ostatnie luki contract-level, bez zmiany zaakceptowanego lossless designu i bez runtime certification. Raport nie obejmuje walkthrough.md jako changed file.

ZERO_IDENTITY_DEFAULT_COMPLETE=PASS; 48 artifacts with zero direct/downstream identities return complete compact output rather than confirmation_required.
ZERO_IDENTITY_DEFAULT_BYTES=62727 UTF-8 bytes (greater than the 15 KiB readable threshold and below the 64 KiB complete ceiling).
ZERO_IDENTITY_NAMED_GUARD=PASS; the same 48-artifact fixture with representation=named returns confirmation_required (estimated_output_bytes=89520).
SEMANTIC_VS_SERIALIZATION_POLICY_SEPARATED=PASS; semantic named/indexed selection is now independent from readable_named (15 KiB shared guard) versus complete_compact (64 KiB local ceiling).
MISSING_ARTIFACT_ID_INDEXED_FAIL_CLOSED=PASS; explicit indexed returns a structured error when one canonical artifact ID is removed, and indexed never keys/encodes that artifact by module::symbol.
MISSING_ARTIFACT_ID_AUTO_FALLBACK=PASS; auto+compact falls back to real named semantics with named guard/policy when indexed construction fails for missing persistent artifact identity.
FRESH_FULL_PARITY=PASS; semantic normalizer/decoder compares named and indexed artifact, architecture, downstream, classification, aggregate, evidence, and impact semantics.
MISSING_GRAPH_FULL_PARITY=PASS; the full matrix preserves per-artifact and aggregate downstream unavailable/reason state.
DEFERRED_ANALYTICS_FULL_PARITY=PASS; the full matrix preserves available downstream identities while retaining unavailable classification/reason state.
ZERO_IDENTITY_FULL_PARITY=PASS; named-equivalent indexed request has no schema/support-table/orphan representation metadata and matches named semantic output.

REAL_ARTIFACT_COUNT=48
REAL_ARTIFACT_RETURNED=48
NEW_DEFAULT_BYTES=45642 UTF-8 bytes for direct-process dogfood target=contextor.core.reporting_engine.graph_analytics
REVERSE_ADJACENCY_BUILDS=1 (current direct-process instrumentation)
UNIQUE_DIRECT_SEEDS=17 (current direct-process instrumentation)
SEED_CLOSURE_COMPUTATIONS=17 (current direct-process instrumentation)

TESTS=140 focused tests passed in the final broad contract/regression set; an additional 81-test graph/artifact/index/registry parity subset also passed. No full suite was run. git diff --check passed for changed production/docs/tests files (walkthrough.md excluded as requested) with only existing LF/CRLF conversion warnings. Direct-process dogfood returned lossless.v1 indexed output with 48/48 artifacts, aggregate direct=17 and additional downstream=126.
DECISION=READY_FOR_RUNTIME_CERTIFICATION

MCP_RESTART_REQUIRED=YES_AFTER_FINAL_IMPLEMENTATION
LIVE_RESTART_REQUIRED=NO
RUNTIME_CERTIFICATION_PENDING=YES

FILES_CHANGED=contextor/mcp/tools/get_module_blast_radius.py; contextor/mcp/docs/get_module_blast_radius.json; tests/mcp/tools/test_get_module_blast_radius.py; tests/mcp/tools/test_specialized_tool_contracts.py
COMPLETE RAW UNIFIED DIFF każdego FILES_CHANGED (walkthrough.md excluded; unified context=0):

warning: in the working copy of 'contextor/mcp/docs/get_module_blast_radius.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/mcp/tools/get_module_blast_radius.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/mcp/tools/test_get_module_blast_radius.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/mcp/tools/test_specialized_tool_contracts.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/docs/get_module_blast_radius.json b/contextor/mcp/docs/get_module_blast_radius.json
index a1b7804..13edd07 100644
--- a/contextor/mcp/docs/get_module_blast_radius.json
+++ b/contextor/mcp/docs/get_module_blast_radius.json
@@ -10 +10 @@
-    "compact (boolean, default true): select the lossless compact serialization; this never bounds or samples artifacts, consumers, or downstream identities.",
+    "compact (boolean, default true): select the complete_compact serialization policy; this never bounds or samples artifacts, consumers, or downstream identities. With representation=auto, false selects readable_named and true permits indexed negotiation.",
@@ -17 +17 @@
-    "compact and indexed are lossless encodings, not previews. They contain schema=module_blast_radius.lossless.v1, canonical persistent artifact IDs, module_index containing canonical persistent module IDs, deterministic deduplicated sets of local ordinal references, and module layer codes. Local ordinals are response-local compression references, never registry IDs; lookup_index_entries can expand canonical module IDs to names.",
+    "Compact and indexed are lossless encodings, not previews. Indexed output contains schema=module_blast_radius.lossless.v1, canonical persistent artifact IDs, module_index containing canonical persistent module IDs, deterministic deduplicated sets of local ordinal references, and module layer codes. Local ordinals are response-local compression references, never registry IDs; lookup_index_entries can expand canonical module IDs to names. Indexed construction requires persistent module and artifact identities and fails closed when either is missing; it never allocates query-local IDs.",
@@ -20 +20 @@
-    "Precedence is explicit: auto with compact=true compares complete candidates and normally selects indexed; auto with compact=false returns the full named/readable result; explicit named always returns named; explicit indexed always returns indexed when losslessly possible and otherwise returns a structured error.",
+    "Precedence is explicit: auto with compact=true compares complete candidates and normally selects indexed; auto with compact=false returns the full named/readable result; explicit named always returns named; explicit indexed always returns indexed when losslessly possible and otherwise returns a structured error. Semantic representation (named or indexed) is independent from serialization policy: readable_named uses the shared 15 KiB guard, while complete_compact uses this tool's 64 KiB ceiling. A zero-identity named-equivalent compact result keeps complete_compact policy without adding orphan indexed metadata; an indexed construction failure due to missing identities is a real named fallback with readable_named policy.",
@@ -36 +36 @@
-    "Indexed output fails closed if a canonical module identity has no persistent module ID; use named output or repair the canonical registry/state.",
+    "Indexed output fails closed if a canonical module or serialized artifact identity has no persistent ID; use named output or repair the canonical registry/state. It never replaces an artifact ID with module::symbol or allocates a query-local identity.",
diff --git a/contextor/mcp/tools/get_module_blast_radius.py b/contextor/mcp/tools/get_module_blast_radius.py
index 066319d..a69fe8a 100644
--- a/contextor/mcp/tools/get_module_blast_radius.py
+++ b/contextor/mcp/tools/get_module_blast_radius.py
@@ -249 +249 @@ def _build_shared_sets(
-        if module_id is None:
+        if module_id is None or not query_helpers.is_module_id(str(module_id)):
@@ -270,0 +271,28 @@ def _build_shared_sets(
+def _validate_indexed_artifact_ids(
+    artifact_facts: list[dict[str, Any]],
+    *,
+    artifact_path_to_id: dict[str, str],
+    artifact_id_to_path: dict[str, str],
+) -> None:
+    """Require every serialized artifact to retain its canonical persistent ID."""
+    missing: list[str] = []
+    for fact in artifact_facts:
+        item = fact["item"]
+        full_name = str(item["full_name"])
+        artifact_id = item.get("artifact_id")
+        canonical_id = artifact_path_to_id.get(full_name)
+        if (
+            not artifact_id
+            or not query_helpers.is_artifact_id(str(artifact_id))
+            or canonical_id is None
+            or str(canonical_id) != str(artifact_id)
+            or artifact_id_to_path.get(str(artifact_id)) != full_name
+        ):
+            missing.append(full_name)
+    if missing:
+        raise ValueError(
+            "Cannot fulfill indexed representation: missing persistent artifact IDs for: "
+            + ", ".join(sorted(missing))
+        )
+
+
@@ -366,0 +395,2 @@ def _build_indexed_projection(
+    artifact_path_to_id: dict[str, str],
+    artifact_id_to_path: dict[str, str],
@@ -372,0 +403,7 @@ def _build_indexed_projection(
+    serialized_artifacts = artifacts_projected or aggregate is not None
+    if serialized_artifacts:
+        _validate_indexed_artifact_ids(
+            artifact_facts,
+            artifact_path_to_id=artifact_path_to_id,
+            artifact_id_to_path=artifact_id_to_path,
+        )
@@ -392,0 +430,3 @@ def _build_indexed_projection(
+    if module_id is None or not query_helpers.is_module_id(str(module_id)):
+        raise ValueError("Cannot fulfill indexed representation: missing persistent module ID for: " + module_name)
+
@@ -434 +474 @@ def _build_indexed_projection(
-        encoded_artifacts[str(item["artifact_id"] or item["full_name"])] = encoded
+        encoded_artifacts[str(item["artifact_id"])] = encoded
@@ -495 +535,6 @@ def _serialize_payload(
-    payload: dict[str, Any], *, semantic_representation: str, allow_large_output: bool, requested_count: int
+    payload: dict[str, Any],
+    *,
+    semantic_representation: str,
+    serialization_policy: str,
+    allow_large_output: bool,
+    requested_count: int,
@@ -497 +542 @@ def _serialize_payload(
-    if semantic_representation == "indexed":
+    if serialization_policy == "complete_compact":
@@ -505 +550 @@ def _serialize_payload(
-                "reason": "Complete lossless indexed module context exceeds the local safety ceiling.",
+                "reason": "Complete lossless module context exceeds the local safety ceiling.",
@@ -514,0 +560,2 @@ def _serialize_payload(
+    if serialization_policy != "readable_named":
+        raise ValueError(f"Unsupported module blast-radius serialization policy: {serialization_policy}")
@@ -720,0 +768,2 @@ def get_module_blast_radius(
+                    artifact_path_to_id=_artifact_path_to_id,
+                    artifact_id_to_path=_artifact_id_to_path,
@@ -730 +779 @@ def get_module_blast_radius(
-        identity_present = _has_module_identity_collection(named_payload)
+        indexed_available = indexed_payload is not None and "schema" in indexed_payload
@@ -734 +783 @@ def get_module_blast_radius(
-            payload, selected_representation = named_payload, "named"
+            payload, selected_representation, serialization_policy = named_payload, "named", "readable_named"
@@ -737 +786,4 @@ def get_module_blast_radius(
-            selected_representation = "indexed" if indexed_payload is not None and "schema" in indexed_payload else "named"
+            if indexed_available:
+                selected_representation, serialization_policy = "indexed", "complete_compact"
+            else:
+                selected_representation, serialization_policy = "named", "complete_compact"
@@ -739,2 +791,2 @@ def get_module_blast_radius(
-            payload, selected_representation = named_payload, "named"
-        elif indexed_payload is None or indexed_error is not None or not identity_present:
+            payload, selected_representation, serialization_policy = named_payload, "named", "readable_named"
+        elif indexed_error is not None or indexed_payload is None:
@@ -743 +795,5 @@ def get_module_blast_radius(
-            payload, selected_representation = named_payload, "named"
+            payload, selected_representation, serialization_policy = named_payload, "named", "readable_named"
+        elif not indexed_available:
+            # No identity collection means there is no indexed schema to
+            # construct, but compact auto still promises a complete result.
+            payload, selected_representation, serialization_policy = named_payload, "named", "complete_compact"
@@ -756,2 +812,9 @@ def get_module_blast_radius(
-
-        return _serialize_payload(payload, semantic_representation=selected_representation, allow_large_output=allow_large_output, requested_count=returned_count)
+            serialization_policy = "complete_compact"
+
+        return _serialize_payload(
+            payload,
+            semantic_representation=selected_representation,
+            serialization_policy=serialization_policy,
+            allow_large_output=allow_large_output,
+            requested_count=returned_count,
+        )
diff --git a/tests/mcp/tools/test_get_module_blast_radius.py b/tests/mcp/tools/test_get_module_blast_radius.py
index e1179c6..72dd0d6 100644
--- a/tests/mcp/tools/test_get_module_blast_radius.py
+++ b/tests/mcp/tools/test_get_module_blast_radius.py
@@ -117,0 +118,26 @@ def _fixture(monkeypatch):
+def _zero_identity_large_fixture(monkeypatch):
+    state, registry = _fixture(monkeypatch)
+    symbols = [f"symbol_{index:02d}" for index in range(48)]
+    state.artifacts["pkg.mod"] = {
+        "own_symbols": symbols,
+        "symbols": {
+            "functions": symbols,
+            "signatures": {symbol: f"def {symbol}({('x' * 250)})" for symbol in symbols},
+        },
+    }
+    state.artifact_consumption = {
+        f"pkg.mod::{symbol}": {"consumers": [], "channels": {}}
+        for symbol in symbols
+    }
+    state.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})
+    artifact_path_to_id = {
+        f"pkg.mod::{symbol}": f"A{200 + index}/1"
+        for index, symbol in enumerate(symbols)
+    }
+    registry._state["artifact_registry"] = {
+        "path_to_id": artifact_path_to_id,
+        "id_to_path": {value: key for key, value in artifact_path_to_id.items()},
+    }
+    return state, registry
+
+
@@ -159 +185 @@ def _decode_indexed(payload, registry_state):
-        return {
+        result = {
@@ -168,0 +195,3 @@ def _decode_indexed(payload, registry_state):
+        if cross:
+            result["cross_layer_sample"] = {"total": len(cross), "items": cross, "truncated": False}
+        return result
@@ -178,13 +207,14 @@ def _decode_indexed(payload, registry_state):
-            layers_by_name = {
-                id_to_name[module_id]: layer
-                for module_id, layer in module_layers.items()
-                if module_id in id_to_name
-            }
-            production = [module for module in downstream_items if layers_by_name.get(module) not in (None, "tests")]
-            tests = [module for module in downstream_items if layers_by_name.get(module) == "tests"]
-            unknown = [module for module in downstream_items if layers_by_name.get(module) is None]
-            downstream_semantics.update({
-                "production_downstream_sample": {"total": len(production), "items": production, "truncated": False},
-                "test_downstream_sample": {"total": len(tests), "items": tests, "truncated": False},
-                "unknown_downstream_sample": {"total": len(unknown), "items": unknown, "truncated": False},
-            })
+            if downstream.get("layer_classification_available"):
+                layers_by_name = {
+                    id_to_name[module_id]: layer
+                    for module_id, layer in module_layers.items()
+                    if module_id in id_to_name
+                }
+                production = [module for module in downstream_items if layers_by_name.get(module) not in (None, "tests")]
+                tests = [module for module in downstream_items if layers_by_name.get(module) == "tests"]
+                unknown = [module for module in downstream_items if layers_by_name.get(module) is None]
+                downstream_semantics.update({
+                    "production_downstream_sample": {"total": len(production), "items": production, "truncated": False},
+                    "test_downstream_sample": {"total": len(tests), "items": tests, "truncated": False},
+                    "unknown_downstream_sample": {"total": len(unknown), "items": unknown, "truncated": False},
+                })
@@ -191,0 +222,2 @@ def _decode_indexed(payload, registry_state):
+            "artifact_id": entry["artifact_id"],
+            "full_name": f"{payload['module']}::{entry['symbol']}",
@@ -214,0 +247,64 @@ def _decode_indexed(payload, registry_state):
+def _semantic_named(payload):
+    artifacts = {}
+    for artifact_id, entry in payload.get("artifacts", {}).items():
+        artifacts[artifact_id] = {
+            key: entry[key]
+            for key in ("artifact_id", "full_name", "symbol", "kind", "signature", "architecture", "downstream_module_reachability", "evidence_scope")
+        }
+        artifacts[artifact_id]["direct"] = entry["direct_consumers"]["items"]
+        del artifacts[artifact_id]["downstream_module_reachability"]
+        artifacts[artifact_id]["downstream"] = entry["downstream_module_reachability"]
+    aggregate = payload.get("aggregate")
+    return {
+        "module": payload.get("module"),
+        "module_id": payload.get("module_id"),
+        "artifacts": artifacts,
+        "aggregate": {
+            "direct": aggregate["unique_direct_consumers"],
+            "downstream": aggregate["unique_downstream_consumers"],
+            "consumed": aggregate["consumed_artifact_ids"],
+            "unconsumed": aggregate["unconsumed_artifact_ids"],
+            "impact": aggregate["highest_impact_artifact_ids"],
+        } if aggregate is not None else None,
+    }
+
+
+def _semantic_indexed(payload):
+    if "schema" not in payload:
+        return _semantic_named(payload)
+    decoded_artifacts, decoded_aggregate = _decode_indexed(payload, _registry_state())
+    artifacts = {}
+    for artifact_id, entry in decoded_artifacts.items():
+        downstream = dict(entry["downstream"])
+        downstream.pop("downstream_set_ref", None)
+        artifacts[artifact_id] = {
+            "artifact_id": entry["artifact_id"],
+            "full_name": entry["full_name"],
+            "symbol": entry["symbol"],
+            "kind": entry["kind"],
+            "signature": entry["signature"],
+            "architecture": entry["architecture"],
+            "direct": entry["direct"],
+            "downstream": downstream,
+            "evidence_scope": "direct_static_artifact_consumption",
+        }
+    downstream_state = dict(decoded_aggregate["downstream_state"])
+    downstream_state.pop("set_ref", None)
+    if decoded_aggregate["downstream"] is not None:
+        downstream_state["items"] = decoded_aggregate["downstream"]
+        downstream_state.setdefault("truncated", False)
+    direct_state = {"total": len(decoded_aggregate["direct"]), "truncated": False, "items": decoded_aggregate["direct"]}
+    return {
+        "module": payload.get("module"),
+        "module_id": payload.get("module_id"),
+        "artifacts": artifacts,
+        "aggregate": {
+            "direct": direct_state,
+            "downstream": downstream_state,
+            "consumed": decoded_aggregate["consumed"],
+            "unconsumed": decoded_aggregate["unconsumed"],
+            "impact": decoded_aggregate["impact"],
+        },
+    }
+
+
@@ -275,0 +372,19 @@ def test_named_and_indexed_are_semantically_lossless(tmp_path, monkeypatch):
+@pytest.mark.parametrize("case", ["fresh", "missing_graph", "deferred_analytics", "zero_identities"])
+def test_named_and_indexed_full_semantic_parity_matrix(tmp_path, monkeypatch, case):
+    state, _ = _fixture(monkeypatch)
+    if case == "missing_graph":
+        state.dependency_graph = None
+    elif case == "deferred_analytics":
+        state.cached_analytics_state = "deferred"
+    elif case == "zero_identities":
+        state.artifact_consumption = {
+            f"pkg.mod::{symbol}": {"consumers": [], "channels": {}}
+            for symbol in ("alpha", "beta", "gamma")
+        }
+        state.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})
+
+    named = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named", allow_large_output=True))
+    indexed = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="indexed", allow_large_output=True))
+    assert _semantic_indexed(indexed) == _semantic_named(named)
+
+
@@ -398,0 +514,45 @@ def test_indexed_zero_identity_output_has_no_representation_metadata(tmp_path, m
+def test_auto_zero_identity_large_module_is_complete_compact_not_guarded(tmp_path, monkeypatch):
+    _zero_identity_large_fixture(monkeypatch)
+    result_text = get_module_blast_radius(str(tmp_path), "pkg.mod")
+    result = json.loads(result_text)
+    result_bytes = len(result_text.encode("utf-8"))
+    assert result.get("status") != "confirmation_required"
+    assert result["artifact_count_total"] == 48
+    assert result["artifact_count_returned"] == len(result["artifacts"]) == 48
+    assert result["aggregate"]["artifact_count_returned"] == 48
+    assert 15 * 1024 < result_bytes < 64 * 1024
+    assert all(artifact_id.startswith("A") for artifact_id in result["artifacts"])
+    assert not any(key in result for key in ("schema", "representation", "module_index", "module_layers", "sets", "consumer_representation"))
+
+
+def test_zero_identity_named_representation_uses_readable_guard(tmp_path, monkeypatch):
+    _zero_identity_large_fixture(monkeypatch)
+    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
+    assert result["status"] == "confirmation_required"
+
+
+def test_indexed_requires_persistent_artifact_ids_and_auto_falls_back(tmp_path, monkeypatch):
+    _, registry = _fixture(monkeypatch)
+    full_name = "pkg.mod::beta"
+    artifact_id = registry._state["artifact_registry"]["path_to_id"].pop(full_name)
+    registry._state["artifact_registry"]["id_to_path"].pop(artifact_id)
+
+    explicit = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="indexed"))
+    assert explicit["status"] == "error"
+    assert "missing persistent artifact IDs" in explicit["error"]
+    assert full_name in explicit["error"]
+
+    auto = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="auto", compact=True))
+    assert auto.get("status") != "error"
+    assert "schema" not in auto
+    assert set(auto["artifacts"]) == {"A100/1", "A102/1", full_name}
+    assert auto["artifacts"][full_name]["artifact_id"] is None
+
+
+def test_indexed_with_all_persistent_artifact_ids_has_no_full_name_keys(tmp_path, monkeypatch):
+    _fixture(monkeypatch)
+    indexed = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="indexed"))
+    assert set(indexed["artifacts"]) == {"A100/1", "A101/1", "A102/1"}
+    assert all(entry["artifact_id"].startswith("A") for entry in indexed["artifacts"].values())
+
+
diff --git a/tests/mcp/tools/test_specialized_tool_contracts.py b/tests/mcp/tools/test_specialized_tool_contracts.py
index 8dab3b2..73aa1e9 100644
--- a/tests/mcp/tools/test_specialized_tool_contracts.py
+++ b/tests/mcp/tools/test_specialized_tool_contracts.py
@@ -106 +106 @@ def test_specialized_tool_contracts__get_module_blast_radius_docs_complete():
-    assert "lossless compact serialization" in params_text
+    assert "complete_compact serialization policy" in params_text
@@ -116,0 +117,5 @@ def test_specialized_tool_contracts__get_module_blast_radius_docs_complete():
+    assert "Semantic representation" in behavior_text
+    assert "zero-identity named-equivalent compact result" in behavior_text
+    assert "persistent module and artifact identities" in behavior_text
+    assert "never allocates query-local IDs" in behavior_text
+    assert "readable_named" in behavior_text

FULL_SUITE_RUN_BY_AGENT=NO

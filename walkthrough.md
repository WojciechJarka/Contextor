# F2F0 contract-certification — `get_symbol_call_context`

DECISION=PASS (source contract and focused local validation)

MCP_RESTART_REQUIRED=YES

LIVE_RESTART_REQUIRED=NO

RUNTIME_CERTIFICATION_NOT_YET_PERFORMED=YES

FULL_SUITE_RUN_BY_AGENT=NO

## Authority, ownership, and pre-edit findings

Contextor MCP established the current owner/dataflow before the edit:

* `contextor.mcp.tools.get_symbol_call_context::get_symbol_call_context` owns resolution, LIVE gates, deterministic traversal, representation selection, and output protection.
* `contextor.core.domain.usage_facts::ModuleUsageFacts` owns persisted `symbol_calls` plus `symbol_calls_materialized`.
* `contextor.core.reference.engine::extract_module_usage_facts` produces qualified, intra-module direct call tuples `(caller, callee, line, call_kind)`.
* `contextor.mcp.query_helpers::build_state_freshness` owns the target-local freshness envelope. Its optional target-file fingerprint/hash is an O(1) target check, not a repository scan or call reconstruction.
* Documentation is loaded from `contextor/mcp/docs/get_symbol_call_context.json` through the documentation owner/index.

At LIVE canonical revision 209, a bounded query for `contextor.mcp.tools.get_symbol_call_context::get_symbol_call_context` returned 27 direct callee facts; with `max_items=5`, `total_edges=27`, `returned_edges=5`, and `truncated=true`. The endpoint already satisfied the requested canonical-only, deterministic BFS, fail-closed, global-prefix, and 15,360-byte auto-bound contracts.

Two contract mismatches existed before the edit:

1. Explicit `representation="named"` over 51,200 bytes silently changed to indexed. The requested contract requires a hard named ceiling, a no-edge controlled error, and an indexed retry only when IDs are complete. `allow_large_output=true` must not bypass it.
2. Documentation promised “no source read,” which contradicted the permitted target-local freshness fingerprint. The relevant guarantee is no repository scan and no source-derived call reconstruction.

## Changed behavior and documentation

`get_symbol_call_context` now has representation precedence:

* explicit indexed with missing selected endpoint IDs: `indexed_identity_unavailable`;
* explicit named above 51,200 bytes: `large_named_output_requires_indexed_representation`, no edges, with `retry: {"representation": "indexed"}` only when all selected endpoints have IDs;
* auto above 51,200 bytes: indexed when identities are complete; otherwise `large_named_output_requires_indexed_identities`;
* explicit named is never silently indexed, including with `allow_large_output=true`.

The existing 512-byte auto threshold, BFS/traversal implementation, producer/materialization paths, LIVE lifecycle, and 15,360-byte deterministic prefix algorithm were not changed.

Documentation now accurately permits target-local `workspace_sync` fingerprinting while forbidding repository scans, AST parsing, and source-derived call reconstruction. The compact documentation index was updated in the same change.

## Focused validation

Command:

```text
.venv\Scripts\python.exe -m pytest -q tests/test_get_symbol_call_context.py tests/mcp/tools/test_get_symbol_call_context.py
```

Result:

```text
47 passed in 1.88s
```

Command:

```text
.venv\Scripts\python.exe -c "import json; json.load(open('contextor/mcp/docs/get_symbol_call_context.json', encoding='utf-8')); json.load(open('contextor/mcp/docs/index.json', encoding='utf-8')); print('JSON_DOCS=PASS')"
git diff --check
```

Result:

```text
JSON_DOCS=PASS
```

Focused coverage now proves:

* materialized graph traversal does not call `ast.parse` and accepts the target-local freshness helper;
* explicit named at 51,201 bytes returns the controlled indexed retry;
* explicit named with `allow_large_output=true` remains blocked by the hard ceiling;
* auto above the ceiling selects indexed only with complete IDs and fails with `large_named_output_requires_indexed_identities` otherwise;
* existing tests continue to cover missing indexed IDs and deterministic/truthful 15,360-byte prefix behavior.

## LIVE evidence

The Desktop watcher naturally published the production change as revision 210 and the dedicated-test change as revision 211; both events had `origin=desktop_watcher`, `status=UPDATED`, and `resync_required=false` in the successful event snapshot.

Subsequent `get_live_events(after_revision=211)` and two retry calls returned `transient_connection_failure: Existing LIVE owner is temporarily unreachable`. Consequently a post-final-edit `continuity=continuous` response was not available. No watcher resync was reported by the last successful snapshot, but final LIVE runtime certification is blocked until the existing MCP runtime is restarted and the LIVE owner is reachable again. No restart was performed.

## Files changed

```text
contextor/mcp/tools/get_symbol_call_context.py
contextor/mcp/docs/get_symbol_call_context.json
contextor/mcp/docs/index.json
tests/test_get_symbol_call_context.py
tests/mcp/tools/test_get_symbol_call_context.py
walkthrough.md
```

The existing modified runtime log was not changed by this task. The walkthrough diff is intentionally omitted.

## COMPLETE RAW UNIFIED DIFFS

```diff
diff --git a/contextor/mcp/tools/get_symbol_call_context.py b/contextor/mcp/tools/get_symbol_call_context.py
index 9d73cb9..53799b6 100644
--- a/contextor/mcp/tools/get_symbol_call_context.py
+++ b/contextor/mcp/tools/get_symbol_call_context.py
@@ -395 +395,9 @@ def get_symbol_call_context(
-        if force_indexed and indexed_candidate is None:
+        if representation == "named" and force_indexed:
+            details = {"named_candidate_bytes": named_bytes}
+            if indexed_candidate is not None:
+                details["retry"] = {"representation": "indexed"}
+            return _error(
+                "large_named_output_requires_indexed_representation",
+                **details,
+            )
+        if representation == "auto" and force_indexed and indexed_candidate is None:
             return _error(
                 "large_named_output_requires_indexed_identities",
                 named_candidate_bytes=named_bytes,
```

```diff
diff --git a/tests/test_get_symbol_call_context.py b/tests/test_get_symbol_call_context.py
index 3207ccd..86b27dc 100644
--- a/tests/test_get_symbol_call_context.py
+++ b/tests/test_get_symbol_call_context.py
@@ -3 +2,0 @@ import ast
-from pathlib import Path
@@ -157 +156 @@ def test_named_indexed_and_auto_use_existing_ids(monkeypatch):
-def test_large_named_candidate_forces_indexed_preflight_and_exact_retry(monkeypatch):
+def test_large_explicit_named_candidate_requires_indexed_retry(monkeypatch):
@@ -170,7 +169,4 @@ def test_large_named_candidate_forces_indexed_preflight_and_exact_retry(monkeypa
-    assert bounded["status"] == "ok"
-    assert bounded["representation"] == "indexed"
-    assert bounded["representation_decision"]["reason"] == "named_candidate_exceeded_51200_bytes"
-    assert "_output" in bounded
-    assert bounded["_output"]["auto_bounded"] is True
-    assert bounded["_output"]["warning_threshold_bytes"] == 15360
-    assert bounded["_output"]["full_output_bytes"] > 15360
+    assert bounded["status"] == "error"
+    assert bounded["error"] == "large_named_output_requires_indexed_representation"
+    assert bounded["retry"] == {"representation": "indexed"}
+    assert "_output" not in bounded
@@ -188,2 +184,2 @@ def test_large_named_candidate_forces_indexed_preflight_and_exact_retry(monkeypa
-    assert approved["representation"] == "indexed"
-    assert len(approved_text.encode("utf-8")) == bounded["_output"]["full_output_bytes"]
+    assert approved["status"] == "error"
+    assert approved["error"] == "large_named_output_requires_indexed_representation"
@@ -192 +188 @@ def test_large_named_candidate_forces_indexed_preflight_and_exact_retry(monkeypa
-def test_query_does_not_parse_or_read_source(monkeypatch):
+def test_query_does_not_parse_or_reconstruct_calls(monkeypatch):
@@ -201,8 +196,0 @@ def test_query_does_not_parse_or_read_source(monkeypatch):
-    original_read_text = Path.read_text
-    read_paths = []
-
-    def tracked_read_text(path, *args, **kwargs):
-        read_paths.append(path)
-        return original_read_text(path, *args, **kwargs)
-
-    monkeypatch.setattr(Path, "read_text", tracked_read_text)
@@ -215 +202,0 @@ def test_query_does_not_parse_or_read_source(monkeypatch):
-    assert [path for path in read_paths if path.suffix == ".py"] == []
```

```diff
diff --git a/tests/mcp/tools/test_get_symbol_call_context.py b/tests/mcp/tools/test_get_symbol_call_context.py
index 5fbade6..04ae9cb 100644
--- a/tests/mcp/tools/test_get_symbol_call_context.py
+++ b/tests/mcp/tools/test_get_symbol_call_context.py
@@ -0,0 +1 @@
+import ast
@@ -91,0 +93,19 @@ def _call(symbol=_ROOT, **kwargs):
+def test_get_symbol_call_context__uses_freshness_helper_without_call_reconstruction(monkeypatch):
+    _install(monkeypatch)
+    freshness_calls = []
+
+    def target_local_freshness(*args, **kwargs):
+        freshness_calls.append((args, kwargs))
+        return {"workspace_sync": "verified"}
+
+    monkeypatch.setattr(query_helpers, "build_state_freshness", target_local_freshness)
+    monkeypatch.setattr(ast, "parse", lambda *_args, **_kwargs: pytest.fail("ast.parse"))
+
+    result = _call(direction="callees")
+
+    assert result["status"] == "ok"
+    assert result["callees"]["items"]
+    assert result["state_freshness"] == {"workspace_sync": "verified"}
+    assert len(freshness_calls) == 1
+
+
@@ -414,3 +434,5 @@ def test_get_symbol_call_context__named_force_boundary_51200_vs_51201(monkeypatc
-    forced = run(51201)
-    assert forced["representation"] == "indexed"
-    assert forced["representation_decision"]["reason"] == "named_candidate_exceeded_51200_bytes"
+    blocked = run(51201)
+    assert blocked["status"] == "error"
+    assert blocked["error"] == "large_named_output_requires_indexed_representation"
+    assert blocked["named_candidate_bytes"] == 51201
+    assert blocked["retry"] == {"representation": "indexed"}
@@ -651 +673 @@ def test_get_symbol_call_context__explicit_named_is_not_silently_changed_to_inde
-def test_get_symbol_call_context__forced_indexed_happens_before_auto_bounding(monkeypatch):
+def test_get_symbol_call_context__explicit_named_hard_ceiling_precedes_auto_bounding(monkeypatch):
@@ -665,6 +687,37 @@ def test_get_symbol_call_context__forced_indexed_happens_before_auto_bounding(mo
-    assert bounded["status"] == "ok"
-    # Forced to indexed before auto-bounding!
-    assert bounded["representation"] == "indexed"
-    assert bounded["representation_decision"]["reason"] == "named_candidate_exceeded_51200_bytes"
-    assert bounded["_output"]["auto_bounded"] is True
-    assert len(raw_bounded.encode("utf-8")) <= 15360
+    assert bounded["status"] == "error"
+    assert bounded["error"] == "large_named_output_requires_indexed_representation"
+    assert bounded["retry"] == {"representation": "indexed"}
+    assert "_output" not in bounded
+
+    approved = json.loads(call_tool.get_symbol_call_context(
+        "C:/repo",
+        _ROOT,
+        direction="callees",
+        representation="named",
+        allow_large_output=True,
+        max_items=None,
+    ))
+    assert approved["status"] == "error"
+    assert approved["error"] == "large_named_output_requires_indexed_representation"
+
+
+def test_get_symbol_call_context__auto_large_named_requires_indexed_identities(monkeypatch):
+    _install_large_graph(monkeypatch, edge_count=350, symbol_prefix="callee_with_a_very_long_symbol_name_")
+    original_read_registries = call_tool.query_helpers.read_registries
+
+    def incomplete_registry(root):
+        registries = list(original_read_registries(root))
+        registries[2] = {}
+        return tuple(registries)
+
+    monkeypatch.setattr(call_tool.query_helpers, "read_registries", incomplete_registry)
+
+    result = _call(
+        _ROOT,
+        direction="callees",
+        representation="auto",
+        max_items=None,
+    )
+    assert result["status"] == "error"
+    assert result["error"] == "large_named_output_requires_indexed_identities"
```

```diff
diff --git a/contextor/mcp/docs/get_symbol_call_context.json b/contextor/mcp/docs/get_symbol_call_context.json
index fb07294..6ea5cdd 100644
--- a/contextor/mcp/docs/get_symbol_call_context.json
+++ b/contextor/mcp/docs/get_symbol_call_context.json
@@ -22 +22 @@
-    "Named output is permitted only when the complete named candidate is at most 51200 UTF-8 bytes. Larger named candidates automatically select indexed output.",
+    "Explicit named output is permitted only when the complete named candidate is at most 51200 UTF-8 bytes. Above that hard ceiling it returns large_named_output_requires_indexed_representation without edges; if indexed identities are complete, retry with representation='indexed'. allow_large_output does not bypass this ceiling.",
@@ -25 +25 @@
-    "Representation negotiation happens before output auto-bounding: explicit named/indexed and auto selection remain authoritative, named candidates strictly above 51200 bytes force indexed representation, and auto switches to indexed at 512+ bytes savings.",
+    "Representation negotiation happens before output auto-bounding: explicit named never switches to indexed; auto candidates strictly above 51200 bytes require complete indexed identities, while auto below that boundary switches to indexed only at 512+ bytes savings.",
@@ -29 +29 @@
-    "Reads only current LIVE canonical module_usages symbol_calls. It performs no ast.parse, source read, grep, report parsing, or query-time graph reconstruction.",
+    "Reads call facts only from current LIVE canonical module_usages symbol_calls. It performs no repository scan, ast.parse, source-derived call reconstruction, grep, or report parsing. A target-local fingerprint/hash read may occur solely to populate workspace_sync.",
@@ -34 +34 @@
-    "Unknown qualified symbols return controlled unknown_symbol or ambiguity responses with bounded suggestion-only candidates. Non-exact plain leaves, missing artifact IDs, invalid direction/depth/max_items/representation, missing indexed identities, stale truth, and unmaterialized call facts return controlled responses."
+    "Unknown qualified symbols return controlled unknown_symbol or ambiguity responses with bounded suggestion-only candidates. Non-exact plain leaves, missing artifact IDs, invalid direction/depth/max_items/representation, explicit named candidates above 51200 bytes, missing indexed identities, stale truth, and unmaterialized call facts return controlled responses."
```

```diff
diff --git a/contextor/mcp/docs/index.json b/contextor/mcp/docs/index.json
index 1917ac4..e0514a2 100644
--- a/contextor/mcp/docs/index.json
+++ b/contextor/mcp/docs/index.json
@@ -119 +119 @@
-      "short_description": "Return a bounded callers/callees neighborhood from current canonical intra-module symbol-call facts without reading source."
+      "short_description": "Return a bounded callers/callees neighborhood from canonical intra-module symbol-call facts without a repository scan or source-derived call reconstruction."
```

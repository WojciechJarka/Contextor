# CPA10K1A_GET_PROJECT_ARCHITECTURE_FULL_CANONICAL_REPRESENTATION_IMPLEMENTATION

## IMPLEMENTATION_SCOPE

- TASK: CPA10K1A_GET_PROJECT_ARCHITECTURE_FULL_CANONICAL_REPRESENTATION_IMPLEMENTATION
- REPO: C:\Temp\Contextor_Repo
- MODE: LITERAL_PATCH_ONLY
- HEAD_EXPECTED: 6768630ff48918fb0dea46379849d3e26326514f
- The exact supplied patch was applied until the mandated post-patch static verification.
- No redesign, report recomputation, repository scan, MCP restart, Desktop restart, `update_file`, or synthetic LIVE mutation was performed.

## HEAD_BEFORE

- `git rev-parse HEAD` before patch: `6768630ff48918fb0dea46379849d3e26326514f`
- `HEAD_MATCH=YES`
- Exact precondition passed.

## HEAD_AFTER

- `git rev-parse HEAD` after patch: `6768630ff48918fb0dea46379849d3e26326514f`
- No commit was created.

## IMPLEMENTATION_RESULT

- `PATCH_APPLICATION=PARTIAL_LITERAL_PATCH_APPLIED`
- `SOURCE_DRIFT=POST_PATCH_STATIC_CONSUMER_MIGRATION_REQUIRED`
- The required patch anchors all matched exactly once before editing.
- `guard_large_output` was updated with the exact custom threshold parameter.
- `get_project_architecture.py`, its docs, index description, listed contract tests, regression block, new full-report tests, and custom-threshold test were applied exactly as supplied.
- The mandated static verification then found existing consumers still using the removed `max_items`/`compact` signature and old response contract. Per `SOURCE_DRIFT_RULE`, work stopped; those consumers were not adapted.

## SOURCE_DRIFT

The following existing consumers require a mechanical migration that was not included in the literal patch:

- `tests/test_mcp_split_s2d.py:36` still asserts:
  `"get_project_architecture": "(repo_path: str, max_items: int | None = 10, compact: bool = True, fields: list[str] | None = None) -> str"`
- `tests/test_mcp_regressions.py:192` calls `mcp_server.get_project_architecture.fn(str(tmp_path), compact=False)`.
- `tests/test_mcp_regressions.py:345-347`, `:366-368`, `:390-392` call the target with `compact=True`.
- `tests/test_mcp_regressions.py:411-413` calls the target with `compact=False`.
- `tests/test_mcp_regressions.py:200-201,291-292,317-318,535-537` assert the removed old response families `top_global_hotspots`, `action_items`, `debt_summary` and legacy layer-index shape, so they also require an approved contract migration after the signature migration.
- `tests/test_live_e2e_corrections.py:395` invokes the target positionally and needs response-shape review even though it does not pass the removed keywords.

Exact mismatching blocks were observed by the post-patch `rg`/source check:
```text
tests/test_mcp_regressions.py:192:
mcp_server.get_project_architecture.fn(str(tmp_path), compact=False)

tests/test_mcp_regressions.py:345-347:
mcp_server.get_project_architecture.fn(
    repo_path=str(tmp_path),
    compact=True,

tests/test_mcp_regressions.py:366-368:
mcp_server.get_project_architecture.fn(
    repo_path=str(tmp_path),
    compact=True,

tests/test_mcp_regressions.py:390-392:
mcp_server.get_project_architecture.fn(
    repo_path=str(tmp_path),
    compact=True,

tests/test_mcp_regressions.py:411-413:
mcp_server.get_project_architecture.fn(
    repo_path=str(tmp_path),
    compact=False,

tests/test_mcp_split_s2d.py:36:
"get_project_architecture": "(repo_path: str, max_items: int | None = 10, compact: bool = True, fields: list[str] | None = None) -> str",
```

## PY_COMPILE

- `NOT_RUN`.
- Static consumer SOURCE_DRIFT required stopping before verification commands.
- Requested commands, including `python -m py_compile`, were not executed.

## FOCUSED_TESTS

- `NOT_RUN`.
- No pytest command was executed because the post-patch static consumer gate failed.
- Full pytest was not run.

## STATIC_CONSUMER_VERIFICATION

- Search performed after patch for `get_project_architecture` references and old `max_items`/`compact` signature usage.
- Result: SOURCE_DRIFT as listed above.
- The target's new signature is present in `contextor/mcp/tools/get_project_architecture.py`, `tests/mcp/tools/test_architecture_context_contracts.py`, and `tests/test_mcp_documentation.py`.
- The remaining old exact signature is present in `tests/test_mcp_split_s2d.py:36`.
- Old architecture contract assertions remain in `tests/test_mcp_regressions.py` and must not be guessed at under literal-patch-only rules.
- `MCP_SERVER_RESTART_REQUIRED=YES` after acceptance because public MCP source/signature/docs changed.
- `DESKTOP_RUNTIME_RESTART_REQUIRED=NO` for this implementation itself.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\mcp\output_guard.py`
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\get_project_architecture.py`
- `C:\Temp\Contextor_Repo\contextor\mcp\docs\get_project_architecture.json`
- `C:\Temp\Contextor_Repo\contextor\mcp\docs\index.json`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_architecture_context_contracts.py`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_auto_bounded_output.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_documentation.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_project_architecture_full_reports.py`
- `C:\Temp\Contextor_Repo\walkthrough.md` is the report artifact and is excluded from the required source/test/docs diff below.

## ACTUAL_DIFF

Complete diffs for every changed production/test/docs file follow. `walkthrough.md` itself is excluded as required.
### contextor/mcp/output_guard.py

```diff
warning: in the working copy of 'contextor/mcp/output_guard.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/output_guard.py b/contextor/mcp/output_guard.py
index 3996db0..b0565e5 100644
--- a/contextor/mcp/output_guard.py
+++ b/contextor/mcp/output_guard.py
@@ -11,9 +11,10 @@ def guard_large_output(
     retry_instruction: str,
     requested_count: int | None = None,
     reason: str = "Estimated output exceeds the recommended context size.",
+    warning_threshold_bytes: int = LARGE_OUTPUT_WARNING_BYTES,
 ) -> str:
     estimated_output_bytes = len(serialized_output.encode("utf-8"))
-    if estimated_output_bytes <= LARGE_OUTPUT_WARNING_BYTES or allow_large_output:
+    if estimated_output_bytes <= warning_threshold_bytes or allow_large_output:
         return serialized_output
 
     warning_response: dict[str, Any] = {
@@ -27,8 +28,8 @@ def guard_large_output(
         {
             "estimated_output_bytes": estimated_output_bytes,
             "estimated_output_kib": estimated_output_bytes / 1024,
-            "warning_threshold_bytes": LARGE_OUTPUT_WARNING_BYTES,
-            "warning_threshold_kib": 15.0,
+            "warning_threshold_bytes": warning_threshold_bytes,
+            "warning_threshold_kib": warning_threshold_bytes / 1024,
             "retry": {
                 "allow_large_output": True,
             },
```

### contextor/mcp/tools/get_project_architecture.py

```diff
warning: in the working copy of 'contextor/mcp/tools/get_project_architecture.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/tools/get_project_architecture.py b/contextor/mcp/tools/get_project_architecture.py
index 2fc4800..517d799 100644
--- a/contextor/mcp/tools/get_project_architecture.py
+++ b/contextor/mcp/tools/get_project_architecture.py
@@ -1,140 +1,341 @@
 import json
 from pathlib import Path
+from typing import Any
 
-from contextor.core.analysis.state_manager import module_current_truth
 from contextor.mcp import query_helpers
+from contextor.mcp import report_helpers
 from contextor.mcp import runtime as mcp_runtime
 from contextor.mcp.diagnostics import diagnostics_summary
+from contextor.mcp.output_guard import guard_large_output
+from contextor.mcp.representation import serialized_json_bytes
 
 
-def _stale_module_truths(state) -> dict[str, dict]:
-    """Return parse-stale canonical modules using the shared core contract."""
-    module_names = set(getattr(state, "modules", {}) or {}) | set(
-        getattr(state, "artifacts", {}) or {}
+PROJECT_ARCHITECTURE_DIRECT_BYTES = 50 * 1024
+
+_REPORT_FILES: tuple[tuple[str, str], ...] = (
+    ("summary", "summary.json"),
+    ("structure", "structure.json"),
+    ("name_collisions", "name_collisions.json"),
+    ("artifacts_compact", "artifacts_compact.json"),
+    ("graph_analytics", "graph_analytics.json"),
+    ("report_diff", "report_diff.json"),
+)
+
+
+def _error(code: str, **details: Any) -> str:
+    return json.dumps(
+        {
+            "status": "error",
+            "error": code,
+            **details,
+        },
+        indent=2,
+        ensure_ascii=False,
     )
-    return {
-        module_name: truth
-        for module_name in sorted(module_names)
-        if not (truth := module_current_truth(state, module_name))["available"]
+
+
+def _report_generated_at(payload: Any) -> str | None:
+    if not isinstance(payload, dict):
+        return None
+
+    generated_at = payload.get("generated_at")
+    if isinstance(generated_at, str) and generated_at:
+        return generated_at
+
+    report_header = payload.get("report_header")
+    if isinstance(report_header, dict):
+        generated_at = report_header.get("generated_at")
+        if isinstance(generated_at, str) and generated_at:
+            return generated_at
+
+    current = payload.get("current")
+    if isinstance(current, dict):
+        generated_at = current.get("generated_at")
+        if isinstance(generated_at, str) and generated_at:
+            return generated_at
+
+    runtime = payload.get("runtime")
+    if isinstance(runtime, dict):
+        generated_at = runtime.get("generated_at")
+        if isinstance(generated_at, str) and generated_at:
+            return generated_at
+
+    return None
+
+
+def _load_report(
+    root: Path,
+    field: str,
+    suffix: str,
+) -> tuple[Any, dict[str, Any]]:
+    filename = f"{root.name}_{suffix}"
+    try:
+        path = report_helpers.get_canonical_report(root, filename)
+    except Exception as exc:
+        unavailable = {
+            "available": False,
+            "state": "unavailable",
+            "reason": f"Report lookup failed: {exc}",
+        }
+        return unavailable, {
+            "available": False,
+            "field": field,
+            "filename": filename,
+            "state": "unavailable",
+            "reason": unavailable["reason"],
+            "serialized_bytes": None,
+            "serialized_kib": None,
+        }
+
+    if path is None:
+        unavailable = {
+            "available": False,
+            "state": "unavailable",
+            "reason": f"Completed project report not found: {filename}",
+        }
+        return unavailable, {
+            "available": False,
+            "field": field,
+            "filename": filename,
+            "state": "unavailable",
+            "reason": unavailable["reason"],
+            "serialized_bytes": None,
+            "serialized_kib": None,
+        }
+
+    try:
+        payload = json.loads(path.read_text(encoding="utf-8"))
+    except (OSError, json.JSONDecodeError) as exc:
+        unavailable = {
+            "available": False,
+            "state": "invalid",
+            "reason": f"Completed project report could not be read: {exc}",
+        }
+        return unavailable, {
+            "available": False,
+            "field": field,
+            "filename": filename,
+            "report_path": str(path),
+            "state": "invalid",
+            "reason": unavailable["reason"],
+            "serialized_bytes": None,
+            "serialized_kib": None,
+        }
+
+    payload_bytes = serialized_json_bytes(payload)
+    return payload, {
+        "available": True,
+        "field": field,
+        "filename": filename,
+        "report_path": str(path),
+        "source": "completed_analysis_report",
+        "generated_at": _report_generated_at(payload),
+        "serialized_bytes": payload_bytes,
+        "serialized_kib": payload_bytes / 1024,
     }
 
 
-def _layer_index_view(
-    layer_items: list[dict],
-    max_items: int | None,
-    compact: bool,
-) -> dict:
-    selected, total, truncated = query_helpers.bounded_items(layer_items, max_items)
-    if compact:
-        result = {
-            "available": True,
-            "distribution": {
-                str(item["layer"]): int(item["module_count"])
-                for item in selected
-            },
-            "total": total,
-            "truncated": truncated,
+def _load_report_bundle(
+    root: Path,
+) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
+    reports: dict[str, Any] = {}
+    catalog: dict[str, dict[str, Any]] = {}
+    for field, suffix in _REPORT_FILES:
+        payload, metadata = _load_report(root, field, suffix)
+        reports[field] = payload
+        catalog[field] = metadata
+    return reports, catalog
+
+
+def _live_state_overlay(root: Path) -> dict[str, Any]:
+    try:
+        engine = mcp_runtime.get_or_init_engine(root)
+    except Exception as exc:
+        return {
+            "available": False,
+            "state": "unavailable",
+            "reason": f"Canonical LIVE state lookup failed: {exc}",
+        }
+
+    state = getattr(engine, "state", None) if engine is not None else None
+    if state is None:
+        return {
+            "available": False,
+            "state": "unavailable",
+            "reason": "No usable canonical LIVE state is available.",
         }
-    else:
-        result = {
-            "available": True,
-            "items": selected,
-            "total": total,
-            "truncated": truncated,
+
+    try:
+        diag = diagnostics_summary(root, state)
+    except Exception as exc:
+        diag = {
+            "available": False,
+            "state": "unavailable",
+            "reason": f"Diagnostics summary failed: {exc}",
         }
-    if truncated:
-        result["expand"] = {
-            "compact": False,
-            "max_items": None,
+
+    try:
+        freshness = query_helpers.build_state_freshness(
+            root,
+            state,
+            engine=engine,
+        )
+    except Exception as exc:
+        freshness = {
+            "canonical_state": (
+                "stale"
+                if getattr(state, "resync_required", False)
+                else "unknown"
+            ),
+            "workspace_sync": "unverified",
+            "canonical_revision": getattr(engine, "revision", None),
+            "provenance": getattr(engine, "provenance", None),
+            "families": {},
+            "advisory_warning": f"Freshness envelope failed: {exc}",
         }
-    return result
+
+    return {
+        "available": True,
+        "data_source": "live_canonical_state",
+        "module_count": len(getattr(state, "modules", {}) or {}),
+        "resync_required": bool(getattr(state, "resync_required", False)),
+        "state_freshness": freshness,
+        "diagnostics_summary": diag,
+        "diagnostics_attention_required": (
+            bool(diag.get("attention_required", False))
+            if isinstance(diag, dict)
+            else False
+        ),
+    }
+
+
+def _bundle_state(catalog: dict[str, dict[str, Any]]) -> str:
+    available = sum(
+        1
+        for metadata in catalog.values()
+        if metadata.get("available") is True
+    )
+    if available == len(catalog):
+        return "complete"
+    if available:
+        return "partial"
+    return "unavailable"
+
+
+def _build_payload(
+    *,
+    selected_fields: list[str],
+    reports: dict[str, Any],
+    catalog: dict[str, dict[str, Any]],
+    live_state: dict[str, Any],
+) -> dict[str, Any]:
+    bundle_state = _bundle_state(catalog)
+    return {
+        "status": "ok" if bundle_state == "complete" else "partial",
+        "scope": "project",
+        "data_source": "completed_analysis_report_bundle",
+        "report_bundle_state": bundle_state,
+        "available_fields": [field for field, _ in _REPORT_FILES],
+        "selected_fields": selected_fields,
+        "reports": {
+            field: reports[field]
+            for field in selected_fields
+        },
+        "report_catalog": catalog,
+        "live_state": live_state,
+    }
 
 
 def get_project_architecture(
     repo_path: str,
-    max_items: int | None = 10,
-    compact: bool = True,
     fields: list[str] | None = None,
+    allow_large_output: bool = False,
 ) -> str:
+    if fields is not None and (
+        not isinstance(fields, list)
+        or any(not isinstance(field, str) for field in fields)
+    ):
+        return _error(
+            "invalid_fields",
+            expected="array of project report field names or null",
+        )
+    if not isinstance(allow_large_output, bool):
+        return _error(
+            "invalid_allow_large_output",
+            expected="boolean",
+        )
+
     root = Path(repo_path).expanduser().resolve()
+    allowed_fields = [field for field, _ in _REPORT_FILES]
+
+    if fields is None:
+        selected_fields = list(allowed_fields)
+    else:
+        selected_fields = list(dict.fromkeys(fields))
+        unknown_fields = sorted(set(selected_fields) - set(allowed_fields))
+        if unknown_fields:
+            return _error(
+                "unsupported_fields",
+                unknown_fields=unknown_fields,
+                allowed_fields=allowed_fields,
+            )
+
     try:
-        engine = mcp_runtime.get_or_init_engine(root)
-        if not engine or getattr(engine.state, "resync_required", False):
-            return "Error: No usable canonical LIVE state. Run analyze_project first."
-
-        state = engine.state
-        stale_modules = _stale_module_truths(state)
-        if stale_modules:
-            return json.dumps(
-                {
-                    "status": "stale",
-                    "available": False,
-                    "scope": "project",
-                    "provenance": "last_known_good",
-                    "affected_modules": stale_modules,
+        reports, catalog = _load_report_bundle(root)
+        live_state = _live_state_overlay(root)
+        result = _build_payload(
+            selected_fields=selected_fields,
+            reports=reports,
+            catalog=catalog,
+            live_state=live_state,
+        )
+        serialized = json.dumps(
+            result,
+            indent=2,
+            ensure_ascii=False,
+        )
+
+        guarded = guard_large_output(
+            serialized,
+            allow_large_output=allow_large_output,
+            requested_count=len(selected_fields),
+            reason=(
+                "Selected project architecture reports exceed the "
+                "50 KiB direct-response threshold."
+            ),
+            retry_instruction=(
+                "Inspect report_catalog serialized_bytes/serialized_kib, "
+                "retry with fields limited to the report sections you need, "
+                "or repeat the identical selection with "
+                "allow_large_output=true."
+            ),
+            warning_threshold_bytes=PROJECT_ARCHITECTURE_DIRECT_BYTES,
+        )
+        if guarded == serialized:
+            return serialized
+
+        warning = json.loads(guarded)
+        warning.update(
+            {
+                "scope": "project",
+                "report_bundle_state": result["report_bundle_state"],
+                "available_fields": allowed_fields,
+                "selected_fields": selected_fields,
+                "report_catalog": catalog,
+                "live_state": live_state,
+                "retry": {
+                    "fields": selected_fields,
+                    "allow_large_output": True,
                 },
-                indent=2,
-            )
-        unavailable = {
-            "available": False,
-            "state": "deferred",
-            "reason": "No fresh canonical LIVE producer is available for this analytics family.",
-        }
-        collections = {
-            "action_items": dict(unavailable),
-            "top_global_hotspots": dict(unavailable),
-        }
-        debt_summary = dict(unavailable)
-
-        cached_analytics = getattr(state, "cached_analytics", {}) or {}
-        cached_state = getattr(state, "cached_analytics_state", "deferred")
-        canonical_modules = set(getattr(state, "modules", {}) or {})
-        module_layers = None
-        if (
-            cached_state == "fresh"
-            and isinstance(cached_analytics, dict)
-            and "module_layers" in cached_analytics
-            and isinstance(cached_analytics["module_layers"], dict)
-        ):
-            candidate_layers = cached_analytics["module_layers"]
-            if set(candidate_layers) == canonical_modules:
-                module_layers = candidate_layers
-        if isinstance(module_layers, dict):
-            layer_counts: dict[str, int] = {}
-            for layer in module_layers.values():
-                layer_name = str(layer)
-                layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1
-            layer_items = [
-                {"layer": layer, "module_count": count}
-                for layer, count in sorted(layer_counts.items())
-            ]
-            layer_index = _layer_index_view(
-                layer_items,
-                max_items,
-                compact,
-            )
-        else:
-            layer_index = dict(unavailable)
-        collections["layer_index"] = layer_index
-        diag = diagnostics_summary(root, state)
-        result = {
-            **collections,
-            "debt_summary": debt_summary,
-            "module_count": len(getattr(state, "modules", {}) or {}),
-            "data_source": "live_canonical_state",
-            "diagnostics_summary": diag,
-            "diagnostics_attention_required": diag["attention_required"],
-        }
-        if fields is not None:
-            allowed_fields = set(result)
-            unknown_fields = sorted(set(fields) - allowed_fields)
-            if unknown_fields:
-                return json.dumps({
-                    "error": "Unsupported fields for get_project_architecture",
-                    "unknown_fields": unknown_fields,
-                    "allowed_fields": sorted(allowed_fields),
-                }, indent=2)
-            result = {field: result[field] for field in fields}
-        return json.dumps(result, indent=2)
-    except Exception as e:
-        return f"Error reading project architecture: {e}"
+            }
+        )
+        return json.dumps(
+            warning,
+            indent=2,
+            ensure_ascii=False,
+        )
+    except Exception as exc:
+        return _error(
+            "project_architecture_failed",
+            detail=str(exc),
+        )
```

### contextor/mcp/docs/get_project_architecture.json

```diff
warning: in the working copy of 'contextor/mcp/docs/get_project_architecture.json', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/docs/get_project_architecture.json b/contextor/mcp/docs/get_project_architecture.json
index ee5d0dc..8d77125 100644
--- a/contextor/mcp/docs/get_project_architecture.json
+++ b/contextor/mcp/docs/get_project_architecture.json
@@ -1,22 +1,37 @@
 {
-  "version": "1.0.0",
+  "version": "2.0.0",
   "tool": "get_project_architecture",
   "purpose": [
-    "[OPTIMIZED] The highest-level architectural summary of the project.\nReturns global action items, debt summary, layer index, and hotspots.\nEach analytics family is an explicit union: available collections expose\n``available=true``, ``total`` and ``truncated``; unavailable families expose\n``available=false``, ``state`` and ``reason`` without fabricated counts.\nThe default ``compact=True`` response returns ``layer_index.distribution`` as\na concise mapping of layer names to module counts. ``max_items`` bounds the\nreturned layers in compact and full modes; pass ``max_items=None`` to return\nevery layer. Set ``compact=False`` for full ``items`` and\n``compact=False, max_items=None`` for lossless complete data. ``truncated``\nmeans fewer elements are present than ``total``, and truncated collections\ninclude ``expand={\"compact\": false, \"max_items\": null}``. ``fields`` projects\ntop-level keys after compact shaping. Allowed values are ``action_items``,\n``debt_summary``, ``layer_index``, ``top_global_hotspots``, ``module_count``,\nand ``data_source``."
+    "[OPTIMIZED] Return the complete persisted global project-analysis report bundle with an explicit current canonical LIVE freshness overlay. The report bundle contains summary, structure, name_collisions, artifacts_compact, graph_analytics, and report_diff. Report bodies are returned losslessly; the tool does not replace them with top-N summaries."
   ],
   "parameters": [
     "repo_path (string, required): canonical repository root.",
-    "max_items (integer or null, default 10): maximum number of entries to return in bounded collections; pass null for unlimited entries. Does not bound module_count.",
-    "compact (boolean, default true): controls concise summary shaping (such as layer distribution mapping) versus verbose item lists.",
-    "fields (array of strings or null, default null): optional projection list of top-level keys to return; null returns the full response."
+    "fields (array of strings or null, default null): optional selection of global report sections. Allowed values are summary, structure, name_collisions, artifacts_compact, graph_analytics, and report_diff. Null selects all sections.",
+    "allow_large_output (boolean, default false): approve returning the complete selected report payload when it exceeds the 51200-byte (50 KiB) direct-response threshold."
   ],
   "behavior": [
-    "1. Reads current structure from canonical LIVE state without requiring a full source scan during query execution.\n2. Saved or report-derived analytics expose explicit available=true/false status and reason without fabricated metrics.\n3. Collections expose total and truncated metadata with expand instructions when truncated."
+    "1. Reads the persisted global report family produced by the latest completed project analysis; it does not rerun report producers or scan repository source files.",
+    "2. The completed-analysis report snapshot and current canonical LIVE state are separate provenance domains. reports contains the persisted analysis snapshot; live_state contains current canonical revision/provenance/family freshness and diagnostics.",
+    "3. When the complete selected response is at most 51200 UTF-8 JSON bytes it is returned directly.",
+    "4. Above 51200 bytes, unless allow_large_output=true, the tool returns confirmation_required with the exact complete selected response size plus report_catalog containing each report section's serialized byte/KiB size. The agent can then narrow fields or explicitly approve the same selection.",
+    "5. Missing or unreadable report sections remain explicit available=false/state/reason entries. They are never fabricated as empty successful reports.",
+    "6. fields controls retrieval width only; it never changes the semantic contents of a selected report."
+  ],
+  "freshness": [
+    "Persisted reports describe the latest completed full-analysis report write and may be older than the current incremental LIVE revision.",
+    "live_state.state_freshness reports the current canonical revision, provenance, family states, workspace-sync status, and advisory warning independently from the report snapshot.",
+    "A newer LIVE revision does not relabel persisted report-only analytics as fresh LIVE facts."
+  ],
+  "errors": [
+    "unsupported_fields: one or more requested fields are not global project report sections.",
+    "invalid_fields: fields is not an array of strings or null.",
+    "invalid_allow_large_output: allow_large_output is not boolean.",
+    "project_architecture_failed: unexpected report-bundle construction failure."
   ],
-  "freshness": [],
-  "errors": [],
   "usage_notes": [
-    "LLM use: start compact with the default limit. Increase it only when a\nrelevant collection is truncated, or pass ``None`` after explicitly\ndeciding that the complete collection is worth the token cost."
+    "Call with the default fields=null first. If the complete bundle is over 50 KiB, inspect report_catalog before choosing the report sections worth loading.",
+    "Use fields to fetch one or more exact report sections without semantic truncation. Use allow_large_output=true only after deciding that the complete selected payload is worth the context cost.",
+    "For targeted extraction from a very large indexed report, prefer the existing specialized indexed/report-context tools rather than loading hundreds of KiB unnecessarily."
   ],
   "examples": []
 }
```

### contextor/mcp/docs/index.json

```diff
warning: in the working copy of 'contextor/mcp/docs/index.json', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/docs/index.json b/contextor/mcp/docs/index.json
index 89d5c4c..79b3579 100644
--- a/contextor/mcp/docs/index.json
+++ b/contextor/mcp/docs/index.json
@@ -35,7 +35,7 @@
     {
       "tool": "get_project_architecture",
       "filename": "get_project_architecture.json",
-      "short_description": "Return the highest-level canonical architecture summary with explicit availability per analytics family. Unavailable families never fabricate zero counts."
+      "short_description": "Return the complete persisted global project-report bundle with current LIVE freshness metadata and exact 50 KiB size preflight before large retrieval."
     },
     {
       "tool": "get_module_context",
```

### tests/mcp/tools/test_architecture_context_contracts.py

```diff
warning: in the working copy of 'tests/mcp/tools/test_architecture_context_contracts.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/mcp/tools/test_architecture_context_contracts.py b/tests/mcp/tools/test_architecture_context_contracts.py
index 3a6d342..b5647f0 100644
--- a/tests/mcp/tools/test_architecture_context_contracts.py
+++ b/tests/mcp/tools/test_architecture_context_contracts.py
@@ -14,7 +14,7 @@ def _load_doc(tool_name: str) -> dict:
 def test_architecture_context_contracts__get_project_architecture_signature():
     tools = mcp_server.mcp._tool_manager._tools
     sig = str(inspect.signature(tools["get_project_architecture"].fn))
-    assert sig == "(repo_path: str, max_items: int | None = 10, compact: bool = True, fields: list[str] | None = None) -> str"
+    assert sig == "(repo_path: str, fields: list[str] | None = None, allow_large_output: bool = False) -> str"
 
 
 def test_architecture_context_contracts__get_file_edit_context_signature():
@@ -45,9 +45,16 @@ def test_architecture_context_contracts__get_project_architecture_docs_complete(
     doc = _load_doc("get_project_architecture")
     params_text = "\n".join(doc.get("parameters", []))
     assert "repo_path (string, required)" in params_text
-    assert "max_items (integer or null, default 10)" in params_text
-    assert "compact (boolean, default true)" in params_text
     assert "fields (array of strings or null, default null)" in params_text
+    assert "allow_large_output (boolean, default false)" in params_text
+    combined = "\n".join(
+        doc.get("behavior", [])
+        + doc.get("freshness", [])
+        + doc.get("usage_notes", [])
+    )
+    assert "51200" in combined
+    assert "report_catalog" in combined
+    assert "live_state" in combined
 
 
 def test_architecture_context_contracts__get_file_edit_context_docs_complete():
```

### tests/mcp/tools/test_auto_bounded_output.py

```diff
warning: in the working copy of 'tests/mcp/tools/test_auto_bounded_output.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/mcp/tools/test_auto_bounded_output.py b/tests/mcp/tools/test_auto_bounded_output.py
index 3a984a0..9e458d1 100644
--- a/tests/mcp/tools/test_auto_bounded_output.py
+++ b/tests/mcp/tools/test_auto_bounded_output.py
@@ -509,3 +509,20 @@ def test_auto_bounded_output__lookup_reserved_output_key_is_never_overwritten(
 
 def test_auto_bounded_output__shared_warning_threshold_is_15360():
     assert LARGE_OUTPUT_WARNING_BYTES == 15360
+def test_auto_bounded_output__guard_large_output_accepts_custom_threshold():
+    from contextor.mcp.output_guard import guard_large_output
+
+    payload = "x" * 20
+    result = guard_large_output(
+        payload,
+        allow_large_output=False,
+        retry_instruction="retry",
+        warning_threshold_bytes=10,
+    )
+    parsed = json.loads(result)
+
+    assert parsed["status"] == "confirmation_required"
+    assert parsed["estimated_output_bytes"] == 20
+    assert parsed["warning_threshold_bytes"] == 10
+    assert parsed["warning_threshold_kib"] == 10 / 1024
+    assert parsed["retry"] == {"allow_large_output": True}
```

### tests/test_mcp_documentation.py

```diff
warning: in the working copy of 'tests/test_mcp_documentation.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/test_mcp_documentation.py b/tests/test_mcp_documentation.py
index 63a256d..92b9ea1 100644
--- a/tests/test_mcp_documentation.py
+++ b/tests/test_mcp_documentation.py
@@ -13,7 +13,7 @@ LEGACY_SIGNATURES = {
     "get_analysis_status": "(repo_path: str, job_id: str | None = None, max_skipped_files: int | None = 10, allow_large_output: bool = False) -> str",
     "get_live_events": "(repo_path: str, after_revision: int | None = None, limit: int | None = 20) -> str",
     "update_file": "(repo_path: str, file_path: str, max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None) -> str",
-    "get_project_architecture": "(repo_path: str, max_items: int | None = 10, compact: bool = True, fields: list[str] | None = None) -> str",
+    "get_project_architecture": "(repo_path: str, fields: list[str] | None = None, allow_large_output: bool = False) -> str",
     "get_module_context": "(repo_path: str, module_name: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, module: str | None = None) -> str",
     "get_artifact_blast_radius": "(repo_path: str, artifact_name: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, representation: str = 'named', artifact: str | None = None) -> str",
     "search_artifacts": "(repo_path: str, search_term: str | None = None, limit: int | None = 20, evidence_limit: int | None = 20, compact: bool = True, fields: list[str] | None = None, query: str | None = None) -> str",
```

### tests/test_mcp_regressions.py

```diff
warning: in the working copy of 'tests/test_mcp_regressions.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index 4fa59a5..98fb91f 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -3734,11 +3734,16 @@ def test_project_architecture_and_report_diff_offer_optional_bounds(
     )
 
     architecture = json.loads(mcp_server.get_project_architecture.fn(
-        repo_path=str(tmp_path), max_items=1, compact=False,
-        fields=["action_items", "top_global_hotspots"],
+        repo_path=str(tmp_path),
+        fields=["summary"],
     ))
-    assert architecture["action_items"]["available"] is False
-    assert architecture["top_global_hotspots"]["available"] is False
+    assert architecture["status"] == "partial"
+    assert architecture["selected_fields"] == ["summary"]
+    assert architecture["reports"]["summary"] == json.loads(
+        summary_path.read_text(encoding="utf-8")
+    )
+    assert architecture["report_catalog"]["summary"]["available"] is True
+    assert architecture["report_catalog"]["structure"]["available"] is False
 
     diff = json.loads(mcp_server.get_report_diff.fn(
         repo_path=str(tmp_path), max_items=1, compact=False,
```

### tests/mcp/tools/test_get_project_architecture_full_reports.py

```diff
diff --git a/tests/mcp/tools/test_get_project_architecture_full_reports.py b/tests/mcp/tools/test_get_project_architecture_full_reports.py
new file mode 100644
--- /dev/null
+++ b/tests/mcp/tools/test_get_project_architecture_full_reports.py
+import importlib
+import json
+from types import SimpleNamespace
+
+from contextor import mcp_server
+from contextor.core.analysis.state_manager import RepositoryAnalysisState
+
+
+architecture_tool = importlib.import_module(
+    "contextor.mcp.tools.get_project_architecture"
+)
+
+_REPORT_SUFFIXES = {
+    "summary": "summary.json",
+    "structure": "structure.json",
+    "name_collisions": "name_collisions.json",
+    "artifacts_compact": "artifacts_compact.json",
+    "graph_analytics": "graph_analytics.json",
+    "report_diff": "report_diff.json",
+}
+
+
+def _install_runtime(tmp_path, monkeypatch, reports):
+    paths = {}
+    for field, payload in reports.items():
+        path = tmp_path / f"{field}.json"
+        path.write_text(
+            json.dumps(payload, indent=2, ensure_ascii=False),
+            encoding="utf-8",
+        )
+        paths[f"{tmp_path.name}_{_REPORT_SUFFIXES[field]}"] = path
+
+    monkeypatch.setattr(
+        architecture_tool.report_helpers,
+        "get_canonical_report",
+        lambda _root, filename: paths.get(filename),
+    )
+
+    state = RepositoryAnalysisState(
+        modules={"pkg.mod": object()},
+        cycles_state="fresh",
+        collisions_state="fresh",
+        topology_metrics_state="fresh",
+        artifact_consumption_state="fresh",
+        lineage_facts_state="fresh",
+    )
+    engine = SimpleNamespace(
+        state=state,
+        revision=77,
+        provenance="live",
+    )
+    monkeypatch.setattr(
+        architecture_tool.mcp_runtime,
+        "get_or_init_engine",
+        lambda _root: engine,
+    )
+    monkeypatch.setattr(
+        architecture_tool,
+        "diagnostics_summary",
+        lambda _root, _state: {
+            "attention_required": False,
+            "availability": {
+                "cycles": "fresh",
+                "name_collisions": "fresh",
+            },
+        },
+    )
+    monkeypatch.setattr(
+        architecture_tool.query_helpers,
+        "build_state_freshness",
+        lambda _root, _state, engine=None: {
+            "canonical_state": "fresh",
+            "workspace_sync": "unverified",
+            "canonical_revision": 77,
+            "provenance": "live",
+            "families": {
+                "graph": "fresh",
+                "topology": "fresh",
+                "artifact_consumption": "fresh",
+                "cycles": "fresh",
+                "collisions": "fresh",
+                "lineage": "fresh",
+            },
+            "advisory_warning": None,
+        },
+    )
+
+
+def _small_bundle():
+    return {
+        "summary": {
+            "status": "WARNING",
+            "metrics": {"nodes": 3, "edges_total": 4},
+            "action_items": ["inspect pkg.mod"],
+            "report_header": {
+                "commit_sha": "abc",
+                "generated_at": "2026-09-16T07:41:26",
+            },
+        },
+        "structure": {
+            "hard_edges": {"pkg.mod": ["pkg.dep"]},
+            "soft_edges": {},
+        },
+        "name_collisions": {
+            "total_collisions": 0,
+            "collision_summary": {"total": 0},
+            "collisions": [],
+        },
+        "artifacts_compact": {
+            "_format_version": "3",
+            "artifact_count": 1,
+            "artifacts": {"A1": {"kind": "function"}},
+        },
+        "graph_analytics": {
+            "report_type": "graph_analytics",
+            "module_count": 1,
+            "modules": {
+                "pkg.mod": {
+                    "fan_in": 1,
+                    "fan_out": 1,
+                }
+            },
+        },
+        "report_diff": {
+            "classification": "NO_CHANGE",
+            "report_diff": {
+                "metrics": {},
+                "debt": {},
+                "layers": {},
+                "is_empty": True,
+            },
+            "current": {
+                "commit_sha": "abc",
+                "generated_at": "2026-09-16T07:41:26",
+            },
+        },
+    }
+
+
+def test_get_project_architecture_returns_lossless_global_report_bundle_under_50k(
+    tmp_path,
+    monkeypatch,
+):
+    reports = _small_bundle()
+    _install_runtime(tmp_path, monkeypatch, reports)
+
+    result = json.loads(
+        mcp_server.get_project_architecture.fn(
+            repo_path=str(tmp_path),
+        )
+    )
+
+    assert result["status"] == "ok"
+    assert result["report_bundle_state"] == "complete"
+    assert result["selected_fields"] == list(_REPORT_SUFFIXES)
+    assert result["reports"] == reports
+    assert result["live_state"]["state_freshness"]["canonical_revision"] == 77
+    assert result["live_state"]["state_freshness"]["provenance"] == "live"
+
+    for field, payload in reports.items():
+        metadata = result["report_catalog"][field]
+        assert metadata["available"] is True
+        assert metadata["serialized_bytes"] == len(
+            json.dumps(
+                payload,
+                indent=2,
+                ensure_ascii=False,
+            ).encode("utf-8")
+        )
+
+
+def test_get_project_architecture_preflights_over_50k_and_reports_section_sizes(
+    tmp_path,
+    monkeypatch,
+):
+    reports = _small_bundle()
+    reports["graph_analytics"] = {
+        "report_type": "graph_analytics",
+        "payload": "x" * 60000,
+    }
+    _install_runtime(tmp_path, monkeypatch, reports)
+
+    result = json.loads(
+        mcp_server.get_project_architecture.fn(
+            repo_path=str(tmp_path),
+        )
+    )
+
+    assert result["status"] == "confirmation_required"
+    assert result["estimated_output_bytes"] > 50 * 1024
+    assert result["warning_threshold_bytes"] == 50 * 1024
+    assert result["warning_threshold_kib"] == 50.0
+    assert (
+        result["report_catalog"]["graph_analytics"]["serialized_bytes"]
+        > 50 * 1024
+    )
+    assert result["retry"] == {
+        "fields": list(_REPORT_SUFFIXES),
+        "allow_large_output": True,
+    }
+
+
+def test_get_project_architecture_fields_narrow_before_large_retrieval(
+    tmp_path,
+    monkeypatch,
+):
+    reports = _small_bundle()
+    reports["graph_analytics"] = {
+        "report_type": "graph_analytics",
+        "payload": "x" * 60000,
+    }
+    _install_runtime(tmp_path, monkeypatch, reports)
+
+    result = json.loads(
+        mcp_server.get_project_architecture.fn(
+            repo_path=str(tmp_path),
+            fields=["summary", "report_diff"],
+        )
+    )
+
+    assert result["status"] == "ok"
+    assert result["selected_fields"] == ["summary", "report_diff"]
+    assert set(result["reports"]) == {"summary", "report_diff"}
+    assert result["reports"]["summary"] == reports["summary"]
+    assert result["reports"]["report_diff"] == reports["report_diff"]
+    assert (
+        result["report_catalog"]["graph_analytics"]["serialized_bytes"]
+        > 50 * 1024
+    )
+
+
+def test_get_project_architecture_allow_large_output_returns_exact_selected_report(
+    tmp_path,
+    monkeypatch,
+):
+    reports = _small_bundle()
+    reports["graph_analytics"] = {
+        "report_type": "graph_analytics",
+        "payload": "x" * 60000,
+    }
+    _install_runtime(tmp_path, monkeypatch, reports)
+
+    result = json.loads(
+        mcp_server.get_project_architecture.fn(
+            repo_path=str(tmp_path),
+            fields=["graph_analytics"],
+            allow_large_output=True,
+        )
+    )
+
+    assert result["status"] == "ok"
+    assert result["selected_fields"] == ["graph_analytics"]
+    assert result["reports"]["graph_analytics"] == reports["graph_analytics"]
+
+
+def test_get_project_architecture_missing_reports_are_explicit_and_unknown_fields_fail(
+    tmp_path,
+    monkeypatch,
+):
+    reports = {
+        "summary": _small_bundle()["summary"],
+    }
+    _install_runtime(tmp_path, monkeypatch, reports)
+
+    result = json.loads(
+        mcp_server.get_project_architecture.fn(
+            repo_path=str(tmp_path),
+            fields=["summary", "structure"],
+        )
+    )
+
+    assert result["status"] == "partial"
+    assert result["reports"]["summary"] == reports["summary"]
+    assert result["reports"]["structure"]["available"] is False
+    assert result["reports"]["structure"]["state"] == "unavailable"
+
+    invalid = json.loads(
+        mcp_server.get_project_architecture.fn(
+            repo_path=str(tmp_path),
+            fields=["does_not_exist"],
+        )
+    )
+    assert invalid["status"] == "error"
+    assert invalid["error"] == "unsupported_fields"
+    assert invalid["unknown_fields"] == ["does_not_exist"]
+
```

## ACTION_GATE

- Do not run more commands or tests under this contract until the user supplies an updated literal migration contract covering the remaining consumers, or explicitly authorizes a non-literal migration.
- The implementation is blocked at the mandated SOURCE_DRIFT gate, not classified as a passing implementation.

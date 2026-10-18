## TASK

CONTEXTOR_B0G4C38D4B_HISTORICAL_CYCLE_SEMANTICS_MCP_READER. Strict controlled implementation; auditor design followed; STOP after this stage.

## HEAD_BEFORE

067e5a6f66654aca974219bc26bac4c9ec819f16

## HEAD_AFTER

067e5a6f66654aca974219bc26bac4c9ec819f16

## GIT_STATUS

Pre-edit clean. Post-edit before report:
```text
M contextor/mcp/docs/get_project_architecture.json
 M contextor/mcp/tools/get_project_architecture.py
 M tests/mcp/tools/test_get_project_architecture_full_reports.py
```

## PRECHECK

DIRECT_EVIDENCE: Contextor MCP first; get_mcp_documentation read. LIVE revision 514, epoch 6b4c9554981b4b779b705089dac32739, continuous, resync_required=false, 0 syntax errors, 0 collisions, 16 structural cycles, all fresh. get_project_architecture, D4A projection and writer source verified. D4A schema 1.0.0 and UNVERIFIED_REPORT_VS_CANONICAL_LIVE. Default required bundle has exactly six fields. Registration uses function signature without constrained fields enum.

## CONTEXTOR_DISCOVERY_COVERAGE

get_symbol_implementation for get_project_architecture, build_cycle_semantics_report, write_global_reports; get_file_edit_context for reader, projection, writer and test file, including consumers/blast radius/tests_covering. JSON docs are not a Python module and Contextor file edit context cannot resolve them; inspected literal documentation after discovery. Reader direct consumer is mcp_server, with static test reachability. Post-edit reader and test symbol workspace_sync=verified at revision 516.

## FILES_CHANGED

- contextor/mcp/tools/get_project_architecture.py
- contextor/mcp/docs/get_project_architecture.json
- tests/mcp/tools/test_get_project_architecture_full_reports.py

walkthrough.md is reporting only.

## DEFAULT_SIX_REPORTS_COMPATIBILITY

_REPORT_FILES unchanged. fields=None selects precisely six legacy fields. Default six-section test verifies keys/order, status=ok, complete bundle, optional not loaded.

## OPTIONAL_CYCLE_SEMANTICS_FIELD

_OPTIONAL_REPORT_FILES contains cycle_semantics.json. Explicit selection works alone and with structure; available_fields advertises it; selected_fields retains requested order.

## HISTORICAL_REPORT_LOADER

Separate _load_cycle_semantics_report reuses _load_report, copies metadata and marks historical_only=true, report_live_binding_verified=false. Missing/unreadable status preserved. No disk rewrite.

## SCHEMA_VALIDATION

Pure validator checks dictionary, schema 1.0.0, report header, exact unverified binding, evidence boolean/freshness, allowed statuses, graph SHA, coverage and status-specific invariants. Unsupported or inconsistent payload returns explicit invalid response and matching metadata.

## FORGED_AUTHORITY_REJECTION

Focused tests reject fabricated live_revision=77 and fabricated binding status. Reader never promotes binding.

## MISSING_REPORT_POLICY

Optional missing yields explicit unavailable when selected and top-level partial; default remains ok when legacy six exist.

## INVALID_REPORT_POLICY

Malformed JSON and unsupported 9.0.0 schema fail closed as invalid. Reader does not synthesize empty success.

## LEGACY_BUNDLE_STATE

Calculated only from six _REPORT_FILES entries. Optional absence does not alter report_bundle_state=complete when six legacy files exist.

## SELECTED_FIELD_STATUS

status=ok only when legacy bundle complete and every selected field is available; otherwise partial.

## LIVE_REPORT_PROVENANCE_SEPARATION

Historical report body returned losslessly and unchanged beside independent live_state overlay. Mock LIVE revision 77 test confirms no report/LIVE equality claim.

## NO_SOURCE_IO

CODE_PATH_PROVED: reader uses persisted canonical report lookup and JSON parse; no analyzed-source reads, AST or graph calculation.

## NO_SEMANTIC_RECOMPUTATION

Focused test patches materialize_cycle_semantics and build_cycle_source_cohort to fail; selected historical report still loads.

## NO_RUNTIME_EXECUTION

No analyzed Python or GUI runtime import executed by reader. Tests use synthetic immutable evidence and tmp_path report files. Serving MCP runtime adoption remains unverified pending reload.

## OUTPUT_GUARD_50_KIB

Existing guard_large_output and 51200-byte threshold preserved. Large valid optional payload triggers confirmation_required; catalog contains optional serialized size and selected_fields retained.

## ALLOW_LARGE_OUTPUT

Same selection retried with allow_large_output=true returns complete untruncated historical body; retry fields and flag validated.

## MCP_DOCUMENTATION

get_project_architecture.json version 1.1.0; documents explicit optional selection, original default six, missing/invalid optional handling, historical provenance, unverified LIVE binding and 50 KiB guard. Public documentation/signature contract nodes pass.

## TARGETED_TEST_RESULTS

tests/mcp/tools/test_get_project_architecture_full_reports.py plus tests/test_cycle_semantics_report_projection.py: 36 passed, 1 third-party AuthlibDeprecationWarning, in 13.52s. No skip/xfail, no full suite.

## LEGACY_TEST_RESULTS

Existing tests in same MCP file passed within 36-pass run. Exact docs/registration nodes: get_project_architecture_signature, get_project_architecture_docs_complete, every_runtime_parameter_and_default_is_documented: 3 passed in 4.74s.

## LIVE_AUTHORITY_BEFORE_AFTER

Read-only LiveStateClient(is_owner=False) authority_status matched endpoint before and after. Same nonsecret identity: repo_id ctx_8efc50d8; root C:\Temp\Contextor_Repo; runtime_domain_id rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654; service_instance_id 88e879fa630c41299f7ba675009e267f; lease_generation 32; service_pid 7840; process_start_identity 134367770052413468; endpoint_fingerprint e73abe0959388d48a8c7608c2d13ed8e150314242e23433d2a0c3b36ab316770. No owner mutation/reconciliation.

## LIVE_REVISION_BEFORE_AFTER

514 -> 516. desktop_watcher UPDATED events: 515 reader source, 516 test source. No separate canonical event for JSON documentation (not a Python module).

## ACTIVITY_EPOCH_BEFORE_AFTER

6b4c9554981b4b779b705089dac32739 -> same.

## EVENT_CONTINUITY

continuous; resync_required=false at revision 516.

## WORKSPACE_SYNC

Contextor verified source synchronization for reader and test module at canonical revision 516. JSON doc is not indexed as a Python module; its disk content and contract tests are verified, canonical workspace_sync for it is not applicable.

## COLLISIONS_BEFORE_AFTER

0 -> 0, fresh.

## STRUCTURAL_CYCLES_BEFORE_AFTER

16 -> 16, fresh.

## NEW_IMPORT_CYCLES

No increase in fresh structural cycle diagnostic count. CODE_PATH_PROVED: only standard-library re was added to reader imports; tests add existing project test helper dependency. Identical cycle membership was not independently enumerated.

## MCP_SERVER_RESTART_REQUIRED

YES_BEFORE_PRODUCTION_ACTIVATION. No restart performed.

## DESKTOP_LIVE_RESTART_REQUIRED

YES_PENDING_CYCLE_SEMANTICS_ACTIVATION. No restart performed.

## RUNTIME_CODE_ADOPTION_STATUS

UNKNOWN_UNTIL_RELOAD_VERIFIED. LIVE source sync does not prove already-running MCP process adopted edited code.

## FINAL_VERDICT

B0G4C38D4B_PASS for scoped source, tests and canonical source synchronization. Serving runtime activation is explicitly pending reload by design; no current LIVE/report identity claim. Stop and await proceduj.

## FULL_DIFFS

Complete actual current-task diff for all three allowed source/test/docs files. Pre-edit Git status was clean; HEAD did not change. walkthrough.md diff excluded as report.

```diff
diff --git a/contextor/mcp/docs/get_project_architecture.json b/contextor/mcp/docs/get_project_architecture.json
index 41bd931..7fc3bfc 100644
--- a/contextor/mcp/docs/get_project_architecture.json
+++ b/contextor/mcp/docs/get_project_architecture.json
@@ -1,12 +1,12 @@
 {
-  "version": "1.0.0",
+  "version": "1.1.0",
   "tool": "get_project_architecture",
   "purpose": [
-    "[OPTIMIZED] Return the complete persisted global project-analysis report bundle with an explicit current canonical LIVE freshness overlay. The report bundle contains summary, structure, name_collisions, artifacts_compact, graph_analytics, and report_diff. Report bodies are returned losslessly; the tool does not replace them with top-N summaries."
+    "[OPTIMIZED] Return the complete persisted global project-analysis report bundle with an explicit current canonical LIVE freshness overlay. The default bundle contains summary, structure, name_collisions, artifacts_compact, graph_analytics, and report_diff. The optional cycle_semantics field exposes a historical FULL evidence report only when explicitly selected. Report bodies are returned losslessly."
   ],
   "parameters": [
     "repo_path (string, required): canonical repository root.",
-    "fields (array of strings or null, default null): optional selection of global report sections. Allowed values are summary, structure, name_collisions, artifacts_compact, graph_analytics, and report_diff. Null selects all sections.",
+    "fields (array of strings or null, default null): optional selection of global report sections. Allowed values are summary, structure, name_collisions, artifacts_compact, graph_analytics, report_diff, and cycle_semantics. Null selects only the original six required sections; use fields=[\"cycle_semantics\"] for the optional historical FULL evidence report.",
     "allow_large_output (boolean, default false): approve returning the complete selected report payload when it exceeds the 51200-byte (50 KiB) direct-response threshold."
   ],
   "behavior": [
@@ -15,13 +15,16 @@
     "3. When the complete selected response is at most 51200 UTF-8 JSON bytes it is returned directly.",
     "4. Above 51200 bytes, unless allow_large_output=true, the tool returns confirmation_required with the exact complete selected response size plus report_catalog containing each report section's serialized byte/KiB size. The agent can then narrow fields or explicitly approve the same selection.",
     "5. Missing or unreadable report sections remain explicit available=false/state/reason entries. They are never fabricated as empty successful reports.",
-    "6. fields controls retrieval width only; it never changes the semantic contents of a selected report."
+    "6. fields controls retrieval width only; it never changes the semantic contents of a selected report.",
+    "7. cycle_semantics is optional and never changes the six-section report_bundle_state. When explicitly selected, a missing or invalid historical report is returned as unavailable or invalid and makes overall status partial.",
+    "8. cycle_semantics freshness_at_report_generation describes historical FULL generation only. Its publication_binding is unverified against current canonical LIVE; no report/LIVE revision equality or runtime import safety is certified."
   ],
   "freshness": [
     "Persisted reports describe the latest completed full-analysis report write and may be older than the current incremental LIVE revision.",
     "live_state.state_freshness reports the current canonical revision, provenance, family states, workspace-sync status, and advisory warning independently from the report snapshot.",
     "A newer LIVE revision does not relabel persisted report-only analytics as fresh LIVE facts.",
-    "If one or more modules are parse-stale, live_state.state_freshness.canonical_state is stale and live_state.parse_stale_modules identifies the affected last-known-good module truths; persisted completed-analysis reports remain independently retrievable."
+    "If one or more modules are parse-stale, live_state.state_freshness.canonical_state is stale and live_state.parse_stale_modules identifies the affected last-known-good module truths; persisted completed-analysis reports remain independently retrievable.",
+    "The explicitly selected cycle_semantics report remains historical even when current LIVE revision is newer or structural diagnostics are fresh. Missing optional files do not affect default six-section completeness."
   ],
   "errors": [
     "unsupported_fields: one or more requested fields are not global project report sections.",
@@ -32,7 +35,8 @@
   "usage_notes": [
     "Call with the default fields=null first. If the complete bundle is over 50 KiB, inspect report_catalog before choosing the report sections worth loading.",
     "Use fields to fetch one or more exact report sections without semantic truncation. Use allow_large_output=true only after deciding that the complete selected payload is worth the context cost.",
-    "For targeted extraction from a very large indexed report, prefer the existing specialized indexed/report-context tools rather than loading hundreds of KiB unnecessarily."
+    "For targeted extraction from a very large indexed report, prefer the existing specialized indexed/report-context tools rather than loading hundreds of KiB unnecessarily.",
+    "Use fields=[\"cycle_semantics\"] to read only the historical semantic report. The existing 50 KiB guard includes this selected payload; retry the same fields with allow_large_output=true only when the complete body is needed."
   ],
   "examples": []
 }
diff --git a/contextor/mcp/tools/get_project_architecture.py b/contextor/mcp/tools/get_project_architecture.py
index 8452edd..4994e46 100644
--- a/contextor/mcp/tools/get_project_architecture.py
+++ b/contextor/mcp/tools/get_project_architecture.py
@@ -1,4 +1,5 @@
 import json
+import re
 from pathlib import Path
 from typing import Any
 
@@ -22,6 +23,10 @@ _REPORT_FILES: tuple[tuple[str, str], ...] = (
     ("report_diff", "report_diff.json"),
 )
 
+_OPTIONAL_REPORT_FILES: tuple[tuple[str, str], ...] = (
+    ("cycle_semantics", "cycle_semantics.json"),
+)
+
 
 def _error(code: str, **details: Any) -> str:
     return json.dumps(
@@ -159,6 +164,98 @@ def _load_report_bundle(
     return reports, catalog
 
 
+def _cycle_semantics_report_validation_error(payload: Any) -> str | None:
+    if not isinstance(payload, dict):
+        return "cycle_semantics payload must be a dictionary"
+    if payload.get("schema_version") != "1.0.0":
+        return "unsupported cycle_semantics schema_version"
+    if not isinstance(payload.get("report_header"), dict):
+        return "cycle_semantics report_header must be a dictionary"
+    if payload.get("publication_binding") != {
+        "status": "UNVERIFIED_REPORT_VS_CANONICAL_LIVE",
+        "canonical_revision": None,
+        "live_revision": None,
+    }:
+        return "cycle_semantics publication_binding is invalid"
+    evidence = payload.get("semantic_evidence")
+    if not isinstance(evidence, dict):
+        return "cycle_semantics semantic_evidence must be a dictionary"
+    available = evidence.get("available")
+    if type(available) is not bool:
+        return "cycle_semantics evidence.available must be boolean"
+    freshness = evidence.get("freshness_at_report_generation")
+    if not isinstance(freshness, str) or freshness not in {"fresh", "stale", "deferred"}:
+        return "cycle_semantics evidence freshness is invalid"
+    status = payload.get("status")
+    if not isinstance(status, str) or status not in {
+        "ok", "partial", "stale", "deferred", "unavailable",
+        "projection_unavailable",
+    }:
+        return "cycle_semantics status is invalid"
+    projection = payload.get("projection")
+    if not available:
+        if status != "unavailable" or freshness != "deferred" or projection is not None:
+            return "cycle_semantics unavailable evidence is inconsistent"
+        return None
+    if status == "unavailable":
+        return "cycle_semantics available evidence cannot be unavailable"
+    if not isinstance(evidence.get("graph_sha256"), str) or not re.fullmatch(
+        r"[0-9a-f]{64}", evidence["graph_sha256"]
+    ):
+        return "cycle_semantics graph_sha256 is invalid"
+    coverage = evidence.get("coverage_status")
+    if not isinstance(coverage, str) or coverage not in {
+        "FILESYSTEM_STABLE_NON_ATOMIC", "PARTIAL_SOURCE_EVIDENCE",
+    }:
+        return "cycle_semantics coverage_status is invalid"
+    if status == "ok" and (
+        freshness != "fresh"
+        or coverage != "FILESYSTEM_STABLE_NON_ATOMIC"
+        or not isinstance(projection, dict)
+    ):
+        return "cycle_semantics ok status is inconsistent"
+    if status == "partial" and (
+        freshness != "fresh"
+        or coverage != "PARTIAL_SOURCE_EVIDENCE"
+        or not isinstance(projection, dict)
+    ):
+        return "cycle_semantics partial status is inconsistent"
+    if status == "stale" and (
+        freshness != "stale" or not isinstance(projection, dict)
+    ):
+        return "cycle_semantics stale status is inconsistent"
+    if status == "deferred" and freshness != "deferred":
+        return "cycle_semantics deferred status is inconsistent"
+    if status == "projection_unavailable" and (
+        projection is not None
+        or not isinstance(payload.get("projection_error"), str)
+        or not payload["projection_error"]
+    ):
+        return "cycle_semantics projection failure is inconsistent"
+    return None
+
+
+def _load_cycle_semantics_report(root: Path) -> tuple[Any, dict[str, Any]]:
+    payload, metadata = _load_report(
+        root, "cycle_semantics", "cycle_semantics.json"
+    )
+    metadata = dict(metadata)
+    metadata["historical_only"] = True
+    metadata["report_live_binding_verified"] = False
+    if metadata.get("available") is not True:
+        return payload, metadata
+    validation_error = _cycle_semantics_report_validation_error(payload)
+    if validation_error is None:
+        return payload, metadata
+    invalid = {
+        "available": False,
+        "state": "invalid",
+        "reason": validation_error,
+    }
+    metadata.update(invalid)
+    return invalid, metadata
+
+
 def _live_state_overlay(root: Path) -> dict[str, Any]:
     try:
         engine = mcp_runtime.get_or_init_engine(root)
@@ -272,13 +369,22 @@ def _build_payload(
     catalog: dict[str, dict[str, Any]],
     live_state: dict[str, Any],
 ) -> dict[str, Any]:
-    bundle_state = _bundle_state(catalog)
+    bundle_state = _bundle_state({
+        field: catalog[field]
+        for field, _ in _REPORT_FILES
+    })
+    selected_available = all(
+        catalog[field].get("available") is True
+        for field in selected_fields
+    )
     return {
-        "status": "ok" if bundle_state == "complete" else "partial",
+        "status": "ok" if bundle_state == "complete" and selected_available else "partial",
         "scope": "project",
         "data_source": "completed_analysis_report_bundle",
         "report_bundle_state": bundle_state,
-        "available_fields": [field for field, _ in _REPORT_FILES],
+        "available_fields": [field for field, _ in _REPORT_FILES] + [
+            field for field, _ in _OPTIONAL_REPORT_FILES
+        ],
         "selected_fields": selected_fields,
         "reports": {
             field: reports[field]
@@ -309,10 +415,12 @@ def get_project_architecture(
         )
 
     root = Path(repo_path).expanduser().resolve()
-    allowed_fields = [field for field, _ in _REPORT_FILES]
+    allowed_fields = [field for field, _ in _REPORT_FILES] + [
+        field for field, _ in _OPTIONAL_REPORT_FILES
+    ]
 
     if fields is None:
-        selected_fields = list(allowed_fields)
+        selected_fields = [field for field, _ in _REPORT_FILES]
     else:
         selected_fields = list(dict.fromkeys(fields))
         unknown_fields = sorted(set(selected_fields) - set(allowed_fields))
@@ -325,6 +433,10 @@ def get_project_architecture(
 
     try:
         reports, catalog = _load_report_bundle(root)
+        if "cycle_semantics" in selected_fields:
+            semantic_report, semantic_metadata = _load_cycle_semantics_report(root)
+            reports["cycle_semantics"] = semantic_report
+            catalog["cycle_semantics"] = semantic_metadata
         live_state = _live_state_overlay(root)
         result = _build_payload(
             selected_fields=selected_fields,
diff --git a/tests/mcp/tools/test_get_project_architecture_full_reports.py b/tests/mcp/tools/test_get_project_architecture_full_reports.py
index 907e9ed..fe3022a 100644
--- a/tests/mcp/tools/test_get_project_architecture_full_reports.py
+++ b/tests/mcp/tools/test_get_project_architecture_full_reports.py
@@ -1,10 +1,15 @@
 import importlib
 import json
+from copy import deepcopy
 from types import SimpleNamespace
 
+import pytest
+
 from contextor import mcp_server
 from contextor.core.analysis.state_manager import RepositoryAnalysisState
 from contextor.mcp.query_helpers import build_state_freshness
+from contextor.core.cycle_semantics.report_projection import build_cycle_semantics_report
+from tests.test_cycle_semantics_report_projection import _snapshot
 
 
 architecture_tool = importlib.import_module(
@@ -29,7 +34,8 @@ def _install_runtime(tmp_path, monkeypatch, reports):
             json.dumps(payload, indent=2, ensure_ascii=False),
             encoding="utf-8",
         )
-        paths[f"{tmp_path.name}_{_REPORT_SUFFIXES[field]}"] = path
+        suffix = "cycle_semantics.json" if field == "cycle_semantics" else _REPORT_SUFFIXES[field]
+        paths[f"{tmp_path.name}_{suffix}"] = path
 
     monkeypatch.setattr(
         architecture_tool.report_helpers,
@@ -138,6 +144,17 @@ def _small_bundle():
     }
 
 
+def _historical_report():
+    return build_cycle_semantics_report(
+        _snapshot(), "fresh", None,
+        report_header={"generated_at": "2026-01-01T00:00:00", "data_source": "global"},
+    )
+
+
+def _read_architecture(tmp_path, **kwargs):
+    return json.loads(mcp_server.get_project_architecture.fn(repo_path=str(tmp_path), **kwargs))
+
+
 def test_get_project_architecture_returns_lossless_global_report_bundle_under_50k(
     tmp_path,
     monkeypatch,
@@ -338,3 +355,156 @@ def test_get_project_architecture_missing_reports_are_explicit_and_unknown_field
     assert invalid["status"] == "error"
     assert invalid["error"] == "unsupported_fields"
     assert invalid["unknown_fields"] == ["does_not_exist"]
+
+
+def test_cycle_semantics_default_bundle_unchanged(tmp_path, monkeypatch):
+    _install_runtime(tmp_path, monkeypatch, _small_bundle())
+    result = _read_architecture(tmp_path)
+    assert result["status"] == "ok"
+    assert result["report_bundle_state"] == "complete"
+    assert result["selected_fields"] == list(_REPORT_SUFFIXES)
+    assert set(result["reports"]) == set(_REPORT_SUFFIXES)
+    assert "cycle_semantics" in result["available_fields"]
+    assert "cycle_semantics" not in result["report_catalog"]
+
+
+def test_cycle_semantics_explicit_selection_lossless(tmp_path, monkeypatch):
+    report = _historical_report()
+    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
+    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
+    assert result["status"] == "ok"
+    assert result["selected_fields"] == ["cycle_semantics"]
+    assert result["reports"]["cycle_semantics"] == report
+    assert result["report_catalog"]["cycle_semantics"]["historical_only"] is True
+    assert result["report_catalog"]["cycle_semantics"]["report_live_binding_verified"] is False
+    assert result["reports"]["cycle_semantics"]["publication_binding"]["live_revision"] is None
+
+
+def test_cycle_semantics_combined_selection(tmp_path, monkeypatch):
+    bundle = _small_bundle()
+    report = _historical_report()
+    _install_runtime(tmp_path, monkeypatch, {**bundle, "cycle_semantics": report})
+    result = _read_architecture(tmp_path, fields=["structure", "cycle_semantics"])
+    assert result["selected_fields"] == ["structure", "cycle_semantics"]
+    assert result["reports"] == {"structure": bundle["structure"], "cycle_semantics": report}
+
+
+def test_cycle_semantics_missing_optional_is_partial(tmp_path, monkeypatch):
+    _install_runtime(tmp_path, monkeypatch, _small_bundle())
+    selected = _read_architecture(tmp_path, fields=["cycle_semantics"])
+    assert selected["status"] == "partial"
+    assert selected["report_bundle_state"] == "complete"
+    assert selected["reports"]["cycle_semantics"]["available"] is False
+    assert selected["reports"]["cycle_semantics"]["state"] == "unavailable"
+    assert selected["report_catalog"]["cycle_semantics"]["historical_only"] is True
+    assert _read_architecture(tmp_path)["status"] == "ok"
+
+
+def test_cycle_semantics_invalid_json_fails_closed(tmp_path, monkeypatch):
+    _install_runtime(tmp_path, monkeypatch, _small_bundle())
+    path = tmp_path / "broken.json"
+    path.write_text("{broken", encoding="utf-8")
+    original = architecture_tool.report_helpers.get_canonical_report
+    monkeypatch.setattr(
+        architecture_tool.report_helpers, "get_canonical_report",
+        lambda root, filename: path if filename.endswith("_cycle_semantics.json") else original(root, filename),
+    )
+    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
+    assert result["status"] == "partial"
+    assert result["reports"]["cycle_semantics"]["state"] == "invalid"
+    assert result["reports"]["cycle_semantics"]["available"] is False
+    assert result["report_bundle_state"] == "complete"
+
+
+def test_cycle_semantics_unsupported_schema_fails_closed(tmp_path, monkeypatch):
+    report = _historical_report()
+    report["schema_version"] = "9.0.0"
+    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
+    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
+    assert result["status"] == "partial"
+    assert result["reports"]["cycle_semantics"]["state"] == "invalid"
+    assert "schema_version" in result["reports"]["cycle_semantics"]["reason"]
+
+
+@pytest.mark.parametrize("forgery", [
+    {"live_revision": 77},
+    {"status": "VERIFIED_REPORT_VS_CANONICAL_LIVE"},
+])
+def test_cycle_semantics_forged_live_binding_rejected(tmp_path, monkeypatch, forgery):
+    report = _historical_report()
+    report["publication_binding"].update(forgery)
+    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
+    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
+    assert result["reports"]["cycle_semantics"]["state"] == "invalid"
+    assert result["report_catalog"]["cycle_semantics"]["available"] is False
+
+
+@pytest.mark.parametrize("changes", [
+    {"semantic_evidence": {"available": False}, "status": "ok"},
+    {"projection": None, "status": "ok"},
+    {"semantic_evidence": {"coverage_status": "FILESYSTEM_STABLE_NON_ATOMIC"}, "status": "partial"},
+    {"semantic_evidence": {"freshness_at_report_generation": "fresh"}, "status": "stale"},
+])
+def test_cycle_semantics_inconsistent_status_rejected(tmp_path, monkeypatch, changes):
+    report = _historical_report()
+    for key, value in changes.items():
+        if key == "semantic_evidence":
+            report[key].update(value)
+        else:
+            report[key] = value
+    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
+    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
+    assert result["reports"]["cycle_semantics"]["state"] == "invalid"
+
+
+def test_cycle_semantics_report_remains_historical_with_newer_live(tmp_path, monkeypatch):
+    report = _historical_report()
+    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
+    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
+    assert result["reports"]["cycle_semantics"] == report
+    assert result["live_state"]["state_freshness"]["canonical_revision"] == 77
+    assert result["reports"]["cycle_semantics"]["publication_binding"] == {
+        "status": "UNVERIFIED_REPORT_VS_CANONICAL_LIVE",
+        "canonical_revision": None,
+        "live_revision": None,
+    }
+
+
+def test_cycle_semantics_large_selected_output_guard(tmp_path, monkeypatch):
+    report = deepcopy(_historical_report())
+    report["semantic_evidence"]["source_fingerprints"] = [
+        {"module_id": f"pkg.module_{i}", "sha256": "a" * 64}
+        for i in range(1200)
+    ]
+    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
+    guarded = _read_architecture(tmp_path, fields=["cycle_semantics"])
+    assert guarded["status"] == "confirmation_required"
+    assert guarded["estimated_output_bytes"] > 50 * 1024
+    assert guarded["selected_fields"] == ["cycle_semantics"]
+    assert guarded["retry"] == {"fields": ["cycle_semantics"], "allow_large_output": True}
+    assert guarded["report_catalog"]["cycle_semantics"]["serialized_bytes"] > 50 * 1024
+    full = _read_architecture(tmp_path, fields=["cycle_semantics"], allow_large_output=True)
+    assert full["status"] == "ok"
+    assert full["reports"]["cycle_semantics"] == report
+
+
+def test_cycle_semantics_reader_does_not_rematerialize(tmp_path, monkeypatch):
+    report = _historical_report()
+    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
+    def fail(*args, **kwargs):
+        raise AssertionError("semantic recomputation attempted")
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.materialization.materialize_cycle_semantics", fail,
+    )
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.source_cohort.build_cycle_source_cohort", fail,
+    )
+    assert _read_architecture(tmp_path, fields=["cycle_semantics"])["reports"]["cycle_semantics"] == report
+
+
+def test_cycle_semantics_selected_missing_does_not_change_default(tmp_path, monkeypatch):
+    _install_runtime(tmp_path, monkeypatch, _small_bundle())
+    before = _read_architecture(tmp_path)
+    assert _read_architecture(tmp_path, fields=["cycle_semantics"])["status"] == "partial"
+    after = _read_architecture(tmp_path)
+    assert before == after
```

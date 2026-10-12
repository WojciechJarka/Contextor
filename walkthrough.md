# CONTEXTOR_B0G2C3_EXACT_METADATA_NORMALIZATION_AND_FULL_PARITY

## FILES_CHANGED

- C:\Temp\Contextor_Repo\tests\test_desktop_mcp_canonical_parity.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only)

No production or other test file changed.

## SOURCE_PRECHECK

DIRECT_EVIDENCE: HEAD adf602f834d2f5d40392702494a0ab06e0dbcff8. Initial git status was clean. Contextor MCP was used first; complete AST implementations of _project, _state_projection, and the real parity test returned workspace_sync=verified at LIVE revision 356. The source had the exact old _state_projection implementation, both strict unnormalized capture projections, and exactly two unnormalized cross-entrypoint comparison calls. Contextor blast radius for _state_projection reported zero confirmed static consumers; literal current source showed its three call sites in the approved test. The previous B0G2C2 evidence identified only two report timestamps among all 36 canonical fields.

## PROVED_TIMESTAMP_EXCEPTION_PATHS

Only RepositoryAnalysisState.layer_information["summary_data"]["generated_at"] and RepositoryAnalysisState.layer_information["summary_data"]["report_header"]["generated_at"] are normalized. _projected_string_member requires an exact projected string key and exactly one member. Both values must be projected strings in canonical datetime.fromisoformat round-trip form. No other generated_at key is normalized. No canonical state field is removed; only the independent comparative projection's two timestamp values become "<operational-report-timestamp>".

## STRICT_CAPTURE_IMMUTABILITY_CHECK

The pre-MCP and post-MCP desktop capture projections remain _state_projection(desktop_capture.state) with normalization disabled. New regression verifies vars(desktop) and vars(mcp) remain equal to deep copies after strict and normalized projection. The real test's pre/post mutation comparison remained unchanged.

## COMPARATOR_REGRESSION_RESULTS

9 passed, 1 deselected, 1 unrelated Authlib deprecation warning. Command: .venv\Scripts\python.exe -m pytest -q tests/test_desktop_mcp_canonical_parity.py -k report_timestamp_normalization. Coverage: two timestamp differences equal only when normalized; raw state unchanged; unrelated generated_at difference survives; each required timestamp missing fails; malformed string and wrong type fail for both paths; semantic artifact difference survives; complete declared field set remains.

## REAL_GUI_EXECUTION

The real parity test invoked headless ContextorGUI analysis on an isolated five-source fixture. Output showed the full 8-step repository analysis pipeline, canonical snapshot persistence, and no error. Its assertions verified operation_name="Repository analysis" and error_count=0. No new GUI or uncontrolled LIVE daemon was started.

## REAL_MCP_EXECUTION

The same test invoked public MCP analyze_project and its real worker after Desktop capture. The job completed; test assertion checked completed["status"]=="completed". No shared analysis engine, coordinator, graph builder, or persistence was mocked.

## FULL_CANONICAL_SEMANTIC_PARITY

The approved test file returned 10 passed, 1 warning in 6.63 s under .venv\Scripts\python.exe -m pytest -q -s tests/test_desktop_mcp_canonical_parity.py. This includes 9 comparator regressions and the real two-entrypoint scenario. All 36 declared RepositoryAnalysisState fields remain in the lossless structural comparator. The only comparative normalization is the two exact timestamps; edges, consumers, reference/lineage facts, topology, artifacts, analytics, completeness/freshness markers, source positions and other report keys stayed strict. No first remaining mismatch occurred. This certifies this isolated FULL pair; it does not claim LIVE incremental transport parity.

## SNAPSHOT_GENERATION_LINKAGE

The real test retained assertions for Desktop writer="desktop", MCP writer="mcp", exact MCP successor revision, same repo ID/root/schema, state_id/revision equality between loaded state and metadata, snapshot provenance and no resync. Post-run read-only inspection of the isolated latest generation showed repo_id ctx_ebcb4755, writer mcp, revision 2, state_id 20261012_123230; the versioned FileState _meta also held that same revision and state_id. The fixture root was C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-552\test_real_desktop_and_mcp_full0\b0g2c_repo_eb5d0376430848c2a6fbc11f0470e9a7. The Desktop revision 1/writer and its linkage were checked within the test before the MCP generation replaced the latest metadata.

## FILE_STATE_PARITY

The real test's _capture_snapshot checked trusted FileState baseline, state_id/revision metadata linkage, coverage of all five immutable fixture sources, size and SHA-256. Its _assert_file_state_parity compared the complete projected FileState maps after both independent captures. Fixture bytes before/after both analyses were asserted equal. Test passed.

## FIRST_REMAINING_MISMATCH_IF_ANY

NONE.

## TARGETED_REGRESSION_RESULTS

After real parity passed, exactly the four approved related files plus selected coordination/canonical nodes ran: tests/test_reference_detail_determinism.py; tests/test_package_initializer_graph_refresh.py; tests/test_resolver.py; tests/test_graph_cache_bindings.py; tests/test_full_analysis_coordination.py::test_lease_is_held_during_publication; tests/test_full_analysis_coordination.py::test_serialized_desktop_and_mcp_coordination; tests/test_canonical_state_contract.py::test_dependencies_keep_hard_and_soft_records_for_the_same_pair. Result: 38 passed, 1 unrelated Authlib deprecation warning in 6.41 s. No full repository pytest or complete large parity-proof module was run.

## PY_COMPILE

PASS: .venv\Scripts\python.exe -m py_compile C:\Temp\Contextor_Repo\tests\test_desktop_mcp_canonical_parity.py.

## GIT_DIFF_CHECK

PASS: git diff --check -- tests/test_desktop_mcp_canonical_parity.py. Git emitted only its LF/CRLF normalization warning. Post-test status before writing this report showed only the approved test file modified, plus walkthrough.md as the report.

## LIVE_REVISION_BEFORE_AFTER

Before 356; after 358. Contextor get_live_events(after_revision=356) reported continuous history, desktop_watcher UPDATED for the approved test file at revision 357 and UNCHANGED for the same file at revision 358. No Contextor_Repo full analysis, manual update_file or publish was invoked.

## WORKSPACE_SYNC_POSTCHECK

Contextor get_symbol_implementation fetched the modified _state_projection from the serving index at canonical revision 358 with source_contract.implementation_is_complete=true and workspace_sync=verified. The fetched implementation contains the new optional normalize_report_timestamps parameter and exact conditional helper call.

## RESYNC_REQUIRED

false after the watcher events; Contextor event continuity=continuous. The isolated parity test also retained explicit assertions that both captured states are not resync_required.

## RESTART_REQUIRED

No restart is required for this test-only edit. Prior production modifications still require the user's planned manual runtime reload before final serving-process certification; pytest source execution and Contextor source indexing do not prove imported-code reload.

## FINAL_VERDICT

B0G2C3_FULL_CANONICAL_PARITY_PASS for the real isolated Desktop/MCP FULL analysis pair and the approved targeted regressions. No incremental transport parity claim. STOP; await "proceduj".

## FULL_DIFFS

Full actual diff for C:\Temp\Contextor_Repo\tests\test_desktop_mcp_canonical_parity.py follows. walkthrough.md is the report and is excluded from source/test changed-file diff accounting.

```diff
diff --git a/tests/test_desktop_mcp_canonical_parity.py b/tests/test_desktop_mcp_canonical_parity.py
index f4c2bbd..5367fe8 100644
--- a/tests/test_desktop_mcp_canonical_parity.py
+++ b/tests/test_desktop_mcp_canonical_parity.py
@@ -12,6 +12,7 @@ import threading
 import time
 from collections.abc import Mapping
 from dataclasses import fields, is_dataclass
+from datetime import datetime
 from enum import Enum
 from pathlib import Path, PurePath
 from types import SimpleNamespace
@@ -402,15 +403,188 @@ def _capture_snapshot(
     )
 
 
-def _state_projection(state: RepositoryAnalysisState) -> dict:
+def _projected_string_member(
+    projection: dict,
+    key: str,
+    path: str,
+) -> dict:
+    assert projection.get("kind") == "mapping", (
+        f"Expected projected mapping at {path}"
+    )
+    key_projection = {
+        "kind": "primitive",
+        "type": "builtins.str",
+        "value": key,
+    }
+    matches = [
+        value
+        for candidate_key, value in projection["items"]
+        if candidate_key == key_projection
+    ]
+    assert len(matches) == 1, (
+        f"Required canonical field missing or duplicated: {path}[{key!r}]"
+    )
+    return matches[0]
+
+
+def _normalize_proved_report_timestamps(
+    projection: dict,
+) -> None:
+    layer = projection["fields"]["layer_information"]
+    summary = _projected_string_member(
+        layer,
+        "summary_data",
+        "layer_information",
+    )
+    header = _projected_string_member(
+        summary,
+        "report_header",
+        "layer_information.summary_data",
+    )
+
+    for parent, field_name, field_path in (
+        (
+            summary,
+            "generated_at",
+            "layer_information.summary_data.generated_at",
+        ),
+        (
+            header,
+            "generated_at",
+            "layer_information.summary_data.report_header.generated_at",
+        ),
+    ):
+        timestamp = _projected_string_member(
+            parent,
+            field_name,
+            field_path,
+        )
+        assert timestamp.get("kind") == "primitive"
+        assert timestamp.get("type") == "builtins.str"
+        value = timestamp.get("value")
+        assert isinstance(value, str)
+        parsed = datetime.fromisoformat(value)
+        assert parsed.isoformat() == value, (
+            f"Invalid canonical report timestamp at {field_path}"
+        )
+
+        # Normalize only the comparative projection.
+        # Never modify the captured canonical state.
+        timestamp["value"] = "<operational-report-timestamp>"
+
+
+def _state_projection(
+    state: RepositoryAnalysisState,
+    *,
+    normalize_report_timestamps: bool = False,
+) -> dict:
     assert type(state) is RepositoryAnalysisState
-    declared_fields = tuple(item.name for item in fields(RepositoryAnalysisState))
-    projection = _project(state, "RepositoryAnalysisState")
+    declared_fields = tuple(
+        item.name for item in fields(RepositoryAnalysisState)
+    )
+    projection = _project(
+        state,
+        "RepositoryAnalysisState",
+    )
     assert projection["kind"] == "dataclass"
     assert tuple(projection["fields"]) == declared_fields
+
+    if normalize_report_timestamps:
+        _normalize_proved_report_timestamps(projection)
+
     return projection
 
 
+def _report_timestamp_state(
+    summary_timestamp: object = "2026-10-12T12:09:48.838009",
+    header_timestamp: object = "2026-10-12T12:09:48.623010",
+) -> RepositoryAnalysisState:
+    return RepositoryAnalysisState(
+        layer_information={
+            "summary_data": {
+                "generated_at": summary_timestamp,
+                "report_header": {
+                    "generated_at": header_timestamp,
+                },
+            },
+        },
+    )
+
+
+def test_report_timestamp_normalization_preserves_captured_state():
+    desktop = _report_timestamp_state()
+    mcp = _report_timestamp_state(
+        "2026-10-12T12:09:50.608340",
+        "2026-10-12T12:09:50.357250",
+    )
+    desktop_before = copy.deepcopy(vars(desktop))
+    mcp_before = copy.deepcopy(vars(mcp))
+
+    assert _state_projection(desktop) != _state_projection(mcp)
+    assert _state_projection(
+        desktop, normalize_report_timestamps=True
+    ) == _state_projection(
+        mcp, normalize_report_timestamps=True
+    )
+    assert vars(desktop) == desktop_before
+    assert vars(mcp) == mcp_before
+
+
+def test_report_timestamp_normalization_has_no_wildcard_exclusion():
+    desktop = _report_timestamp_state()
+    mcp = copy.deepcopy(desktop)
+    desktop.layer_information["other"] = {"generated_at": "2026-10-12T12:00:00"}
+    mcp.layer_information["other"] = {"generated_at": "2026-10-12T12:00:01"}
+
+    assert _state_projection(
+        desktop, normalize_report_timestamps=True
+    ) != _state_projection(
+        mcp, normalize_report_timestamps=True
+    )
+
+
+@pytest.mark.parametrize("missing_from", ["summary_data", "report_header"])
+def test_report_timestamp_normalization_rejects_missing_timestamp(missing_from):
+    state = _report_timestamp_state()
+    target = state.layer_information["summary_data"]
+    if missing_from == "report_header":
+        target = target["report_header"]
+    del target["generated_at"]
+
+    with pytest.raises(AssertionError, match="missing or duplicated"):
+        _state_projection(state, normalize_report_timestamps=True)
+
+
+@pytest.mark.parametrize("field", ["summary_data", "report_header"])
+@pytest.mark.parametrize("invalid", ["not-a-timestamp", 123])
+def test_report_timestamp_normalization_rejects_invalid_timestamp(field, invalid):
+    state = _report_timestamp_state()
+    target = state.layer_information["summary_data"]
+    if field == "report_header":
+        target = target["report_header"]
+    target["generated_at"] = invalid
+
+    with pytest.raises((AssertionError, ValueError)):
+        _state_projection(state, normalize_report_timestamps=True)
+
+
+def test_report_timestamp_normalization_preserves_semantic_difference_and_fields():
+    desktop = _report_timestamp_state()
+    mcp = copy.deepcopy(desktop)
+    mcp.artifacts["pkg.module"] = {"symbols": ["changed"]}
+
+    desktop_projection = _state_projection(
+        desktop, normalize_report_timestamps=True
+    )
+    mcp_projection = _state_projection(
+        mcp, normalize_report_timestamps=True
+    )
+    declared_fields = {item.name for item in fields(RepositoryAnalysisState)}
+    assert set(desktop_projection["fields"]) == declared_fields
+    assert set(mcp_projection["fields"]) == declared_fields
+    assert desktop_projection != mcp_projection
+
+
 def _assert_file_state_parity(desktop: _SnapshotCapture, mcp: _SnapshotCapture) -> None:
     desktop_projection = _project(desktop.file_states, "FileStateManager._state")
     mcp_projection = _project(mcp.file_states, "FileStateManager._state")
@@ -603,8 +777,14 @@ def test_real_desktop_and_mcp_full_entrypoints_have_identical_canonical_state(
         )
 
     try:
-        desktop_projection = _state_projection(desktop_capture.state)
-        mcp_projection = _state_projection(mcp_capture.state)
+        desktop_projection = _state_projection(
+            desktop_capture.state,
+            normalize_report_timestamps=True,
+        )
+        mcp_projection = _state_projection(
+            mcp_capture.state,
+            normalize_report_timestamps=True,
+        )
     except _UnsupportedCanonicalValue as exc:
         evidence_dir = _preserve_mismatch_evidence(tmp_path, desktop_capture, mcp_capture)
         pytest.fail(
```

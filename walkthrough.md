# L32A_DIAGNOSTICS_MARKER_FAIL_CLOSED

## CURRENT_HEAD

`079cdc16a214155b08b5f362bcaad8da03ff7039`. Contextor MCP deferred symbol retrieval resolved the three affected owners at LIVE revision 126 with `workspace_sync=verified` for symbol source. Contextor lineage and blast-radius retrieval identified `diagnostics_summary_for_state` consumers including LIVE runtime, MCP diagnostics and tests. Git confirmed exact current anchors before edits. No FULL analysis, update_file or service restart.

## PRE_FIX_NEGATIVE_RESULTS

New tests were added first, then run with `& .\.venv\Scripts\python.exe -m pytest -q tests/test_mcp_diagnostics.py -k 'malformed or missing_markers'`: **27 failed, 6 passed, 20 deselected, 1 external Authlib warning**. The failures were expected red results. Six passing cases were scalar syntax markers already treated as unavailable. The other cases proved false-fresh collision/cycle summaries, unhashable list/dict exceptions, and malformed public collision availability.

## FALSE_FRESH_REPRODUCTION

With a nonempty collision or cycle payload, marker `None`, empty string, `UNKNOWN`, `Fresh`, `True`, `7`, `[]`, or `{}` caused the pre-fix `_availability` fallback to report `fresh` or throw. A missing marker with a present payload also reported `fresh`. This incorrectly exposed counts and attention classification without freshness certification.

## UNHASHABLE_MARKER_REPRODUCTION

Pre-fix `[]` and `{}` hit `TypeError: unhashable type` in `diagnostics_projection._availability`; syntax list/dict hit the membership check in `diagnostics_summary_for_state` or `syntax_diagnostics_for_path`. The new exact tests exercise these paths without modifying durable state.

## POST_FIX_MARKER_MATRIX

| Marker | Collisions/cycles summary | Syntax summary/path | Public collision tool |
|---|---|---|---|
| None, empty, UNKNOWN, Fresh, True, 7, [], {} | unavailable, count None | unavailable, not materialized | valid JSON, unavailable, no details |
| Missing attribute, existing payload | unavailable, count None | unavailable, not materialized | valid JSON, unavailable, no details |
| fresh | existing positive tests retain fresh counts/details | existing positive tests retain materialized syntax | existing positive tests retain details |
| stale/deferred | existing nonfresh behavior retained | existing accepted status set retained | existing nonfresh branch retained |

No unknown marker is promoted to fresh from payload presence. The four production edits implement only the auditor-specified guards and fallback.

## PUBLIC_MCP_AVAILABILITY_RESULT

The isolated in-memory `get_name_collisions` test now parses valid JSON and observes `availability=unavailable`, `total=None`, `details=[]`, and a fail-closed diagnostics summary for every malformed marker. This tests the local tool function, not the still-running MCP server; runtime certification requires a later manual restart.

## TARGETED_TEST_RESULTS

Post-fix new tests: **33 passed, 20 deselected, 1 external Authlib warning**. Targeted gate: `tests/test_mcp_diagnostics.py tests/test_syntax_diagnostics_full_analysis.py tests/test_collisions_live_lifecycle.py tests/test_cycles_live_lifecycle.py` — **103 passed, 1 external Authlib warning**. `git diff --check` found no whitespace errors. No full suite.

## REGRESSION_FAILURES

None in the required targeted gate. The expected 27 pre-fix red cases are documented above.

## RESTART_REQUIRED

**YES** — manual MCP backend restart is required before certifying runtime responses against the changed server code. No restart was performed.

## FILES_CHANGED

- `contextor/core/diagnostics_projection.py`
- `contextor/mcp/diagnostics.py`
- `contextor/mcp/tools/get_name_collisions.py`
- `tests/test_mcp_diagnostics.py`

## FINAL_VERDICT

**FOCUSED_FIX_PASS** for source and targeted regression gate. Runtime MCP certification remains pending a manual backend restart.

## FULL_DIFFS

```diff
diff --git a/contextor/core/diagnostics_projection.py b/contextor/core/diagnostics_projection.py
index e581125..b390fc6 100644
--- a/contextor/core/diagnostics_projection.py
+++ b/contextor/core/diagnostics_projection.py
@@ -16,21 +16,17 @@ def _availability(
         None,
     )
 
-    if values is None and status == "fresh":
-        return "unavailable"
-
-    if status in {
+    if isinstance(status, str) and status in {
         "fresh",
         "stale",
         "deferred",
         "unavailable",
     }:
+        if status == "fresh" and values is None:
+            return "unavailable"
         return status
 
-    if values is None:
-        return "unavailable"
-
-    return "fresh"
+    return "unavailable"
 
 
 def diagnostics_summary_for_state(
@@ -85,7 +81,7 @@ def diagnostics_summary_for_state(
         )
         syntax_availability = "fresh"
 
-    elif syntax_state in {
+    elif isinstance(syntax_state, str) and syntax_state in {
         "not_materialized",
         "deferred",
         "stale",
diff --git a/contextor/mcp/diagnostics.py b/contextor/mcp/diagnostics.py
index 4760280..7118cdb 100644
--- a/contextor/mcp/diagnostics.py
+++ b/contextor/mcp/diagnostics.py
@@ -36,7 +36,7 @@ def syntax_diagnostics_for_path(
     if family_state != "fresh" or not isinstance(facts, dict):
         return {
             "status": "unavailable",
-            "availability": family_state if family_state in {"not_materialized", "deferred", "stale", "unavailable"} else "unavailable",
+            "availability": family_state if isinstance(family_state, str) and family_state in {"not_materialized", "deferred", "stale", "unavailable"} else "unavailable",
             "materialized": False,
             "source_path": canonical_path,
             "errors": None,
diff --git a/contextor/mcp/tools/get_name_collisions.py b/contextor/mcp/tools/get_name_collisions.py
index c6f5f30..114dda8 100644
--- a/contextor/mcp/tools/get_name_collisions.py
+++ b/contextor/mcp/tools/get_name_collisions.py
@@ -98,6 +98,16 @@ def get_name_collisions(
     engine = mcp_runtime.get_or_init_engine(root)
     state = getattr(engine, "state", None) if engine is not None else None
     availability = getattr(state, "collisions_state", "unavailable") if state is not None else "unavailable"
+    if not (
+        isinstance(availability, str)
+        and availability in {
+            "fresh",
+            "stale",
+            "deferred",
+            "unavailable",
+        }
+    ):
+        availability = "unavailable"
     if availability != "fresh":
         payload = {
             "total": None,
diff --git a/tests/test_mcp_diagnostics.py b/tests/test_mcp_diagnostics.py
index 05c14de..5ba4560 100644
--- a/tests/test_mcp_diagnostics.py
+++ b/tests/test_mcp_diagnostics.py
@@ -1,12 +1,15 @@
 import json
 from types import SimpleNamespace
 
+import pytest
+
 from contextor import mcp_server
 from contextor.mcp.diagnostics import (
     diagnostics_summary,
     diagnostics_summary_for_completed_job,
     diagnostics_summary_for_state,
     inject_diagnostics_summary,
+    syntax_diagnostics_for_path,
 )
 from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES
 from contextor.mcp import runtime as mcp_runtime
@@ -27,6 +30,85 @@ def _collision(kind="NAME_COLLISION", identical=False, module="pkg.a"):
     )
 
 
+INVALID_MARKERS = [None, "", "UNKNOWN", "Fresh", True, 7, [], {}]
+
+
+@pytest.mark.parametrize("marker", INVALID_MARKERS, ids=repr)
+@pytest.mark.parametrize(
+    ("family", "payload"),
+    [("collisions", [_collision()]), ("cycles", [["a", "b", "a"]])],
+)
+def test_malformed_collision_or_cycle_marker_never_certifies_payload(marker, family, payload):
+    state = SimpleNamespace(
+        collisions_state="fresh",
+        collisions=[_collision()],
+        cycles_state="fresh",
+        cycles=[["a", "b", "a"]],
+    )
+    setattr(state, f"{family}_state", marker)
+    setattr(state, family, payload)
+
+    summary = diagnostics_summary_for_state(state)
+    key = "name_collisions" if family == "collisions" else "cycles"
+    assert summary[key]["availability"] == "unavailable"
+    assert summary[key]["count"] is None
+    assert summary["availability"][key] == "unavailable"
+
+
+@pytest.mark.parametrize("marker", INVALID_MARKERS, ids=repr)
+def test_malformed_syntax_marker_never_materializes_facts(marker):
+    state = SimpleNamespace(
+        syntax_diagnostics_state=marker,
+        syntax_diagnostics_by_path={
+            "broken.py": {"status": "checked_with_errors", "errors": [{"message": "bad"}]}
+        },
+    )
+    summary = diagnostics_summary_for_state(state)
+    projection = syntax_diagnostics_for_path(state, "broken.py")
+    assert summary["syntax_errors"] == {"count": None, "availability": "unavailable"}
+    assert projection["status"] == "unavailable"
+    assert projection["availability"] == "unavailable"
+    assert projection["materialized"] is False
+    assert projection["errors"] is None
+
+
+@pytest.mark.parametrize("marker", INVALID_MARKERS, ids=repr)
+def test_name_collision_tool_normalizes_malformed_marker(tmp_path, monkeypatch, marker):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    state = SimpleNamespace(collisions_state=marker, collisions=[_collision()])
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    result = json.loads(get_name_collisions(str(repo)))
+    assert result["availability"] == "unavailable"
+    assert result["total"] is None
+    assert result["details"] == []
+    assert result["diagnostics_summary"]["name_collisions"] == {
+        "count": None, "critical": None, "warning": None, "info": None,
+        "availability": "unavailable",
+    }
+
+
+def test_missing_markers_with_payload_do_not_certify_diagnostics(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    state = SimpleNamespace(
+        collisions=[_collision()],
+        cycles=[["a", "b", "a"]],
+        syntax_diagnostics_by_path={
+            "broken.py": {"status": "checked_with_errors", "errors": [{"message": "bad"}]}
+        },
+    )
+    summary = diagnostics_summary_for_state(state)
+    for key in ("name_collisions", "cycles", "syntax_errors"):
+        assert summary[key]["availability"] == "unavailable"
+        assert summary[key]["count"] is None
+    assert syntax_diagnostics_for_path(state, "broken.py")["materialized"] is False
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    result = json.loads(get_name_collisions(str(repo)))
+    assert result["availability"] == "unavailable"
+    assert result["details"] == []
+
+
 def test_diagnostics_summary_does_not_fabricate_unavailable_counts():
     summary = diagnostics_summary_for_state(SimpleNamespace(
         collisions_state="deferred", cycles_state="unavailable", collisions=None, cycles=None
```

# CONTEXTOR P1D3-WARN-4E — implementer report

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP inspected `contextor/mcp/tools/get_live_events.py` first at canonical revision 867; structural DFS back-edge count was 16. Initial HEAD `8c76a7746e02b5824779fc431a9dc0adae97c212`, clean worktree; new test path absent. Both exact SEARCH blocks occurred once. Existing `contextor/mcp/docs/get_live_events.json` and MCP diagnostics tests were inspected as public-tool contracts; docs were outside this exact allowlist.

## HEAD / WORKTREE

DIRECT_EVIDENCE: Final HEAD unchanged. Only the authorized MCP tool, new test and this report changed. No commit, push, backend restart or active user's FULL/LIVE operation.

## EXACT SEARCH / REPLACE RESULT

DIRECT_EVIDENCE: Applied the two literal SEARCH → REPLACE blocks with `apply_patch` and created the new test file from the supplied exact-content block. No independent logic, assertion or contract change was added.

## CURRENT WARNING VIEW / EVENT HISTORY

CODE_PATH_PROVED: Successful `get_live_events` responses retain their original event history and add `cycle_diagnostic_history_semantics` plus a current `cycle_warning_view` from the LIVE owner query. The helper requires matching revision and activity epoch, validates the structural/model/active partition and counts, and returns unavailable without counts on projection failure. Non-OK events and no-owner responses remain unchanged. No LIVE event journal mutation was added.

## NEW TEST RESULTS

DIRECT_EVIDENCE: `py_compile` on both changed Python files exited 0. `tests/test_cycle_semantics_mcp_live_warning_view.py`: 17 passed, 0 failed, 0 skipped, 11.88 s, exit 0.

## FOCUSED REGRESSIONS

DIRECT_EVIDENCE: Four requested modules: 125 passed, 0 failed, 0 skipped, one external `AuthlibDeprecationWarning`, 92.02 s, exit 0. Tracked and new-file whitespace checks exited 0. No global pytest.

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_module_context` inspected the two changed files at canonical revision 869. Both returned `workspace_sync=verified`, live provenance, fresh module/graph/topology/structural cycles and stale cycle_semantics. Structural DFS back-edge count remained 16. Production tool has only its existing hard dependency on `contextor.core.live_state.runtime`; no newly counted cycle. This does not prove current MCP process loaded-code adoption.

## FILES_CHANGED

- `contextor/mcp/tools/get_live_events.py`
- `tests/test_cycle_semantics_mcp_live_warning_view.py` (new)

`walkthrough.md` is this report. Complete actual diffs follow.

## FULL_DIFFS


### Modified MCP tool

```diff
diff --git a/contextor/mcp/tools/get_live_events.py b/contextor/mcp/tools/get_live_events.py
index 3d94554..b30170a 100644
--- a/contextor/mcp/tools/get_live_events.py
+++ b/contextor/mcp/tools/get_live_events.py
@@ -2,6 +2,83 @@ import json
 from pathlib import Path
 
 
+def _current_cycle_warning_view(client, events):
+    """Read current warning state without reinterpreting historical events."""
+    def unavailable(reason):
+        return {"status": "unavailable", "reason": reason}
+
+    try:
+        report = client.get_installed_cycle_warning_projection()
+    except (OSError, EOFError, RuntimeError, AttributeError, TypeError, ValueError):
+        return unavailable("LIVE_WARNING_PROJECTION_QUERY_FAILED")
+
+    if type(report) is not dict or report.get("status") != "ok":
+        return unavailable("LIVE_WARNING_PROJECTION_UNAVAILABLE")
+
+    if (
+        report.get("binding_state") != "INSTALLED_CYCLE_WARNING_PROJECTION"
+        or type(events.get("revision")) is not int
+        or type(report.get("revision")) is not int
+        or report["revision"] != events["revision"]
+        or type(events.get("activity_epoch")) is not str
+        or not events["activity_epoch"]
+        or report.get("activity_epoch") != events["activity_epoch"]
+    ):
+        return unavailable("LIVE_WARNING_GENERATION_MISMATCH")
+
+    structural = report.get("structural_paths")
+    accepted = report.get("model_pass_paths")
+    active = report.get("active_warning_paths")
+
+    if any(type(paths) is not tuple for paths in (structural, accepted, active)):
+        return unavailable("LIVE_WARNING_PARTITION_INVALID")
+
+    for paths in (structural, accepted, active):
+        if any(
+            type(path) is not tuple
+            or len(path) < 2
+            or any(type(node) is not str or not node for node in path)
+            or path[0] != path[-1]
+            or len(set(path[:-1])) != len(path) - 1
+            for path in paths
+        ) or len(set(paths)) != len(paths):
+            return unavailable("LIVE_WARNING_PARTITION_INVALID")
+
+    structural_set = set(structural)
+    accepted_set = set(accepted)
+    active_set = set(active)
+
+    if (
+        not accepted_set.isdisjoint(active_set)
+        or accepted_set | active_set != structural_set
+        or accepted != tuple(p for p in structural if p in accepted_set)
+        or active != tuple(p for p in structural if p in active_set)
+        or any(
+            type(report.get(count)) is not int
+            or report[count] != len(paths)
+            for count, paths in (
+                ("structural_count", structural),
+                ("model_pass_count", accepted),
+                ("active_warning_count", active),
+            )
+        )
+    ):
+        return unavailable("LIVE_WARNING_PARTITION_INVALID")
+
+    return {
+        "status": "fresh",
+        "scope": "CURRENT_INSTALLED_GENERATION_STATIC_MODEL_NOT_RUNTIME_SAFETY",
+        "revision": report["revision"],
+        "activity_epoch": report["activity_epoch"],
+        "structural_count": report["structural_count"],
+        "model_pass_count": report["model_pass_count"],
+        "active_warning_count": report["active_warning_count"],
+        "structural_paths": structural,
+        "model_pass_paths": accepted,
+        "active_warning_paths": active,
+    }
+
+
 def get_live_events(
     repo_path: str,
     after_revision: int | None = None,
@@ -53,8 +130,22 @@ def get_live_events(
             indent=2,
         )
     try:
-        return json.dumps(
-            client.get_events(after_revision=after_revision, limit=limit), indent=2
+        events = client.get_events(
+            after_revision=after_revision,
+            limit=limit,
         )
+
+        if type(events) is not dict or events.get("status") != "ok":
+            return json.dumps(events, indent=2)
+
+        response = dict(events)
+        response["cycle_diagnostic_history_semantics"] = (
+            "STRUCTURAL_CHANGES_NOT_CURRENT_ACTIVE_WARNING_STATE"
+        )
+        response["cycle_warning_view"] = _current_cycle_warning_view(
+            client, events,
+        )
+        return json.dumps(response, indent=2)
+
     except (OSError, EOFError, RuntimeError) as exc:
         return json.dumps({"status": "error", "error": str(exc)}, indent=2)
```

### New test module

```diff
diff --git a/tests/test_cycle_semantics_mcp_live_warning_view.py b/tests/test_cycle_semantics_mcp_live_warning_view.py
new file mode 100644
index 0000000..58a310f
--- /dev/null
+++ b/tests/test_cycle_semantics_mcp_live_warning_view.py
@@ -0,0 +1,285 @@
+"""MCP get_live_events current warning view and structural event separation."""
+
+from __future__ import annotations
+
+import copy
+import json
+
+import pytest
+
+from contextor.mcp.tools.get_live_events import get_live_events
+from tests.test_cycle_semantics_live_installed_partial_claims import (
+    _fixture, _owner,
+)
+from tests.test_original_worker_partial_scc_preparation import (
+    PASS_AND_HAZARD, PASS_AND_UNKNOWN, TWO_PASS,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _connect(monkeypatch, client):
+    monkeypatch.setattr(
+        "contextor.core.live_state.runtime.connect_existing_with_status",
+        lambda _root: (client, "ok"),
+    )
+
+
+@pytest.mark.parametrize("sources,accepted,active", [
+    (PASS_AND_UNKNOWN, 1, 1),
+    (PASS_AND_HAZARD, 1, 1),
+    (TWO_PASS, 2, 0),
+])
+def test_t01_t03_real_installed_partial_warning_view(
+    tmp_path, isolated_dirs, monkeypatch, sources, accepted, active,
+):
+    root, state, metadata = _fixture(tmp_path, sources)
+    with _owner(state, metadata) as (server, client):
+        _connect(monkeypatch, client)
+        before = copy.deepcopy((
+            server._events,
+            server._activity_seq,
+            state.cycles,
+        ))
+
+        result = json.loads(get_live_events(str(root)))
+
+        assert result["status"] == "ok"
+        assert result["cycle_diagnostic_history_semantics"] == (
+            "STRUCTURAL_CHANGES_NOT_CURRENT_ACTIVE_WARNING_STATE"
+        )
+
+        view = result["cycle_warning_view"]
+        assert view["status"] == "fresh"
+        assert view["revision"] == metadata.revision
+        assert view["activity_epoch"] == server._activity_epoch
+        assert view["structural_count"] == 2
+        assert view["model_pass_count"] == accepted
+        assert view["active_warning_count"] == active
+        assert len(view["model_pass_paths"]) == accepted
+        assert len(view["active_warning_paths"]) == active
+        assert set(map(tuple, view["model_pass_paths"])).isdisjoint(
+            set(map(tuple, view["active_warning_paths"]))
+        )
+        assert len(view["structural_paths"]) == 2
+
+        assert (
+            server._events,
+            server._activity_seq,
+            state.cycles,
+        ) == before
+
+
+def test_t04_missing_partial_receipt_does_not_hide_warnings(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root, state, metadata = _fixture(
+        tmp_path, TWO_PASS, partial=False,
+    )
+    with _owner(state, metadata) as (_, client):
+        _connect(monkeypatch, client)
+        view = json.loads(
+            get_live_events(str(root))
+        )["cycle_warning_view"]
+
+        assert view["status"] == "fresh"
+        assert view["structural_count"] == 2
+        assert view["model_pass_count"] == 0
+        assert view["active_warning_count"] == 2
+
+
+def test_t05_stale_cycles_never_become_false_zero_warnings(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    state.cycles_state = "stale"
+
+    with _owner(state, metadata) as (_, client):
+        _connect(monkeypatch, client)
+        view = json.loads(
+            get_live_events(str(root))
+        )["cycle_warning_view"]
+
+        assert view["status"] == "unavailable"
+        assert "active_warning_count" not in view
+        assert "active_warning_paths" not in view
+
+
+class _FakeClient:
+    def __init__(self, events, projection):
+        self.events = events
+        self.projection = projection
+
+    def get_events(self, **_kwargs):
+        return self.events
+
+    def get_installed_cycle_warning_projection(self):
+        if isinstance(self.projection, Exception):
+            raise self.projection
+        return self.projection
+
+
+def _fake_reports():
+    a = ("a", "b", "a")
+    b = ("x", "y", "x")
+
+    events = {
+        "status": "ok",
+        "revision": 12,
+        "activity_epoch": "epoch-1",
+        "events": [],
+        "total": 0,
+        "truncated": False,
+    }
+
+    projection = {
+        "status": "ok",
+        "binding_state": "INSTALLED_CYCLE_WARNING_PROJECTION",
+        "revision": 12,
+        "activity_epoch": "epoch-1",
+        "structural_paths": (a, b),
+        "model_pass_paths": (a,),
+        "active_warning_paths": (b,),
+        "structural_count": 2,
+        "model_pass_count": 1,
+        "active_warning_count": 1,
+    }
+
+    return events, projection
+
+
+@pytest.mark.parametrize("mutation", [
+    {"revision": 13},
+    {"activity_epoch": "epoch-2"},
+    {"revision": True},
+    {"binding_state": "FORGED"},
+])
+def test_t06_generation_or_binding_mismatch_fails_closed(
+    tmp_path, monkeypatch, mutation,
+):
+    events, report = _fake_reports()
+    report.update(mutation)
+    _connect(monkeypatch, _FakeClient(events, report))
+
+    view = json.loads(
+        get_live_events(str(tmp_path))
+    )["cycle_warning_view"]
+
+    assert view["status"] == "unavailable"
+    assert "active_warning_count" not in view
+
+
+@pytest.mark.parametrize("mutation", [
+    {"active_warning_paths": ()},
+    {"model_pass_paths": (("a", "b", "a"), ("x", "y", "x"))},
+    {"structural_count": 0},
+    {"model_pass_paths": [["a", "b", "a"]]},
+])
+def test_t07_invalid_partition_fails_closed(
+    tmp_path, monkeypatch, mutation,
+):
+    events, report = _fake_reports()
+    report.update(mutation)
+    _connect(monkeypatch, _FakeClient(events, report))
+
+    view = json.loads(
+        get_live_events(str(tmp_path))
+    )["cycle_warning_view"]
+
+    assert view["status"] == "unavailable"
+    assert "active_warning_paths" not in view
+
+
+def test_t08_query_failure_fails_closed_without_dropping_event_history(
+    tmp_path, monkeypatch,
+):
+    events, _ = _fake_reports()
+    events["events"] = [{
+        "revision": 12,
+        "diagnostic_changes": {
+            "total": 1,
+            "truncated": False,
+            "items": [{
+                "diagnostic_kind": "cycle",
+                "action": "ADDED",
+                "cycle_nodes": ["a", "b", "a"],
+            }],
+        },
+    }]
+    original = copy.deepcopy(events)
+
+    _connect(monkeypatch, _FakeClient(events, RuntimeError("connection failed")))
+
+    result = json.loads(get_live_events(str(tmp_path)))
+
+    assert result["status"] == "ok"
+    assert result["events"] == original["events"]
+    assert result["cycle_warning_view"]["status"] == "unavailable"
+    assert "active_warning_paths" not in result["cycle_warning_view"]
+    assert events == original
+
+
+def test_t09_raw_cycle_events_are_history_not_current_warning_list(
+    tmp_path, monkeypatch,
+):
+    events, report = _fake_reports()
+    events["events"] = [{
+        "revision": 12,
+        "diagnostic_changes": {
+            "total": 1,
+            "truncated": False,
+            "items": [{
+                "diagnostic_kind": "cycle",
+                "action": "ADDED",
+                "cycle_nodes": ["a", "b", "a"],
+            }],
+        },
+    }]
+
+    original = copy.deepcopy(events)
+    _connect(monkeypatch, _FakeClient(events, report))
+
+    result = json.loads(get_live_events(str(tmp_path)))
+
+    assert result["events"] == original["events"]
+    assert result["cycle_warning_view"]["model_pass_paths"] == [
+        ["a", "b", "a"],
+    ]
+    assert result["cycle_warning_view"]["active_warning_paths"] == [
+        ["x", "y", "x"],
+    ]
+    assert result["cycle_diagnostic_history_semantics"] == (
+        "STRUCTURAL_CHANGES_NOT_CURRENT_ACTIVE_WARNING_STATE"
+    )
+
+
+def test_t10_no_live_owner_keeps_existing_response(
+    tmp_path, monkeypatch,
+):
+    monkeypatch.setattr(
+        "contextor.core.live_state.runtime.connect_existing_with_status",
+        lambda _root: (None, "no_live_service"),
+    )
+
+    result = json.loads(get_live_events(str(tmp_path)))
+
+    assert result["status"] == "no_live_service"
+    assert "cycle_warning_view" not in result
+
+
+def test_t11_non_ok_event_response_remains_unchanged(
+    tmp_path, monkeypatch,
+):
+    events, report = _fake_reports()
+    events = {
+        "status": "error",
+        "error": "event_history_unavailable",
+    }
+    _connect(monkeypatch, _FakeClient(events, report))
+
+    result = json.loads(get_live_events(str(tmp_path)))
+
+    assert result == events
```

## CONTRACT_CONFLICTS

NONE observed in the supplied literal source/test instructions.

## REMAINING UNKNOWN

UNKNOWN: Active MCP process adoption after source edit, active service generation and Desktop warning behavior. The existing `get_live_events` MCP documentation does not yet describe the new optional current warning view; it was not edited because the exact allowlist excludes docs. No backend restart occurred.

## FINAL IMPLEMENTER OBSERVATION

CONTRACT_PROVED: Literal WARN-4E implementation and focused regressions pass. Architectural GO remains with ChatGPT. STOP after this stage.


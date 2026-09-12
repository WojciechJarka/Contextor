STATUS=PASS

TEST_CONTRACTS_ADDED
- IPC: real ValidationError collision normalization; committed collision and closed-cycle add/remove payloads; no-delta unchanged state; independent freshness fail-closed; malformed fact rejection; deterministic mixed ordering; bounded journal with full trace set; persistence failure has no diagnostic publication.
- Desktop feed: separate collision/cycle action wording; SYNTAX_ERROR and RECOVERED suppression/preservation; appended non-syntax detail; +N more bounding; malformed fallback; poll_once callback delivery.
- Runtime trace: syntax, collision, and cycle JSONL fields, event names, revisions, operation IDs, booleans, and structured node arrays.

TEST_RESULTS
- Focused pytest: 183 passed, 1 warning.
- IPC partition: 76 passed (the terminal runner completed without its final summary line; count is 183 - 56 - 51 and was confirmed by the user).
- Activity plus runtime trace: 56 passed, 1 warning.
- Collision/cycle lifecycle plus documentation: 51 passed, 1 warning.
- py_compile tests/test_live_state_ipc.py tests/test_live_activity_status.py tests/test_runtime_trace.py: PASS.
- git diff --check: PASS.

FILES_CHANGED
- tests/test_live_state_ipc.py
- tests/test_live_activity_status.py
- tests/test_runtime_trace.py

PREEXISTING_WORKTREE_CHANGES
- NONE

COMPLETE FULL_DIFF
warning: in the working copy of 'tests/test_live_activity_status.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_state_ipc.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_runtime_trace.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/test_live_activity_status.py b/tests/test_live_activity_status.py
index 9a09c32..e34ca5c 100644
--- a/tests/test_live_activity_status.py
+++ b/tests/test_live_activity_status.py
@@ -180,9 +180,10 @@ def test_background_feed_has_single_poll_owner_and_no_duplicates(live_server_ins


 def test_desktop_feed_formats_committed_diagnostic_delta_without_replacing_syntax_message():
-    feed = DesktopLiveEventFeed(SimpleNamespace(), lambda *_args, **_kwargs: None)
+    feed = DesktopLiveEventFeed(SimpleNamespace(), lambda *_args, **_kwargs: None, initial_seq=0)
     event = {
         "operation": "update_file",
+        "origin": "desktop_watcher",
         "status": "SYNTAX_ERROR",
         "file_path": "pkg/bad.py",
         "canonical_revision": 12,
@@ -207,9 +208,10 @@ def test_desktop_feed_formats_committed_diagnostic_delta_without_replacing_synta


 def test_desktop_feed_formats_generic_diagnostic_delta_and_ignores_malformed_payload():
-    feed = DesktopLiveEventFeed(SimpleNamespace(), lambda *_args, **_kwargs: None)
+    feed = DesktopLiveEventFeed(SimpleNamespace(), lambda *_args, **_kwargs: None, initial_seq=0)
     event = {
         "operation": "update_file",
+        "origin": "desktop_watcher",
         "status": "UPDATED",
         "file_path": "pkg/change.py",
         "canonical_revision": 13,
@@ -232,6 +234,99 @@ def test_desktop_feed_formats_generic_diagnostic_delta_and_ignores_malformed_pay
     )


+@pytest.mark.parametrize(
+    "item, expected",
+    [
+        (
+            {"action": "ADDED", "diagnostic_kind": "collision", "collision_symbol": "target", "collision_nodes": ["pkg.a", "pkg.b"]},
+            "[LIVE] Diagnostics after change.py (rev 14): collision added: target [pkg.a, pkg.b]",
+        ),
+        (
+            {"action": "RESOLVED", "diagnostic_kind": "collision", "collision_symbol": "target", "collision_nodes": ["pkg.a", "pkg.b"]},
+            "[LIVE] Diagnostics after change.py (rev 14): collision resolved: target [pkg.a, pkg.b]",
+        ),
+        (
+            {"action": "ADDED", "diagnostic_kind": "cycle", "cycle_nodes": ["pkg.a", "pkg.b", "pkg.a"]},
+            "[LIVE] Diagnostics after change.py (rev 14): cycle added: pkg.a -> pkg.b -> pkg.a",
+        ),
+        (
+            {"action": "RESOLVED", "diagnostic_kind": "cycle", "cycle_nodes": ["pkg.a", "pkg.b", "pkg.a"]},
+            "[LIVE] Diagnostics after change.py (rev 14): cycle resolved: pkg.a -> pkg.b -> pkg.a",
+        ),
+    ],
+)
+def test_desktop_feed_formats_each_collision_and_cycle_action(item, expected):
+    feed = DesktopLiveEventFeed(SimpleNamespace(), lambda *_args, **_kwargs: None, initial_seq=0)
+    event = {
+        "operation": "update_file", "origin": "desktop_watcher", "status": "UPDATED", "file_path": "pkg/change.py",
+        "canonical_revision": 14,
+        "diagnostic_changes": {"total": 1, "truncated": False, "items": [item]},
+    }
+    assert feed._message(event) == expected
+
+
+def test_desktop_feed_preserves_recovered_text_and_appends_only_non_syntax_details():
+    feed = DesktopLiveEventFeed(SimpleNamespace(), lambda *_args, **_kwargs: None, initial_seq=0)
+    event = {
+        "operation": "update_file", "origin": "desktop_watcher", "status": "RECOVERED", "file_path": "pkg/bad.py",
+        "canonical_revision": 15,
+        "diagnostic_changes": {
+            "total": 2, "truncated": False,
+            "items": [
+                {"action": "RESOLVED", "diagnostic_kind": "syntax", "source_path": "pkg/bad.py", "line_number": 2, "column_number": 1},
+                {"action": "ADDED", "diagnostic_kind": "collision", "collision_symbol": "target", "collision_nodes": ["pkg.a", "pkg.b"]},
+            ],
+        },
+    }
+    message = feed._message(event)
+    assert message == "[LIVE] Syntax recovered in bad.py (rev 15); collision added: target [pkg.a, pkg.b]"
+    assert "syntax error resolved" not in message
+
+
+def test_desktop_feed_suppresses_matching_syntax_detail_and_bounds_remaining_items():
+    feed = DesktopLiveEventFeed(SimpleNamespace(), lambda *_args, **_kwargs: None, initial_seq=0)
+    event = {
+        "operation": "update_file", "origin": "desktop_watcher", "status": "SYNTAX_ERROR", "file_path": "pkg/bad.py",
+        "canonical_revision": 16, "error": "invalid syntax", "line_number": 1, "column_number": 2,
+        "diagnostic_changes": {
+            "total": 5, "truncated": True,
+            "items": [
+                {"action": "ADDED", "diagnostic_kind": "syntax", "source_path": "pkg/bad.py", "line_number": 1, "column_number": 2},
+                {"action": "ADDED", "diagnostic_kind": "cycle", "cycle_nodes": ["pkg.a", "pkg.b", "pkg.a"]},
+                {"action": "RESOLVED", "diagnostic_kind": "collision", "collision_symbol": "target", "collision_nodes": ["pkg.a", "pkg.b"]},
+            ],
+        },
+    }
+    message = feed._message(event)
+    assert message == (
+        "[LIVE] Syntax error in bad.py line 1, column 2: invalid syntax; "
+        "cycle added: pkg.a -> pkg.b -> pkg.a; collision resolved: target [pkg.a, pkg.b]; +2 more"
+    )
+    assert "syntax error added" not in message
+    assert message.endswith("+2 more")
+
+
+def test_desktop_feed_delivers_one_diagnostic_journal_event_once_through_poll_path():
+    event = {
+        "seq": 1, "category": "LIVE_STATE", "operation": "update_file", "origin": "desktop_watcher",
+        "status": "UPDATED", "file_path": "pkg/change.py", "canonical_revision": 17,
+        "diagnostic_changes": {"total": 1, "truncated": False, "items": [
+            {"action": "ADDED", "diagnostic_kind": "cycle", "cycle_nodes": ["pkg.a", "pkg.b", "pkg.a"]}
+        ]},
+    }
+
+    class Client:
+        def get_events(self, **_kwargs):
+            return {"status": "ok", "activity_epoch": "test", "events": [event], "truncated": False}
+
+    delivered = []
+    feed = DesktopLiveEventFeed(Client(), lambda message, event=None: delivered.append((message, event)), initial_seq=0)
+    feed.poll_once()
+    assert delivered == [
+        ("[LIVE] Diagnostics after change.py (rev 17): cycle added: pkg.a -> pkg.b -> pkg.a", event)
+    ]
+
+
 def test_explicit_inactive_repo_never_falls_through_to_other_active_repo(live_server_instance, monkeypatch, tmp_path):
     server_a, client_a = live_server_instance
     repo_a = tmp_path / "repo_a"
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index 9f00d3d..fbe704b 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -22,6 +22,7 @@ from contextor.core.live_state.runtime import EndpointSchemaError, connect_or_st
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.core.analysis.state_manager import FileStateManager
 from contextor.core.paths import repo_cache_dir
+from contextor.core.domain.validation import ValidationError

 pytestmark = pytest.mark.live

@@ -38,17 +39,21 @@ def _diagnostic_state(*, syntax=None, collisions=None, cycles=None, freshness="f
     )


-def test_diagnostic_delta_normalizes_fresh_canonical_families_only():
-    collision = SimpleNamespace(
-        kind="NAME_COLLISION",
-        artifact_type="function",
-        is_identical=False,
-        nodes=["pkg.b", "pkg.a", "pkg.a"],
-        symbol_details=[
-            {"name": "run", "artifact_type": "function"},
-            {"name": "run", "artifact_type": "function"},
-        ],
+def _collision_error():
+    error = ValidationError(
+        kind="NAME_COLLISION", message="collision", nodes=["pkg.b", "pkg.a"]
     )
+    error.artifact_type = "function"
+    error.is_identical = False
+    error.symbol_details = [
+        {"module": "pkg.a", "name": "target", "artifact_type": "function", "file_path": "pkg/a.py", "location": {}},
+        {"module": "pkg.b", "name": "target", "artifact_type": "function", "file_path": "pkg/b.py", "location": {}},
+    ]
+    return error
+
+
+def test_diagnostic_delta_normalizes_fresh_canonical_families_only():
+    collision = _collision_error()
     current = _diagnostic_state(
         syntax={
             "pkg/bad.py": {
@@ -68,13 +73,126 @@ def test_diagnostic_delta_normalizes_fresh_canonical_families_only():
         ("collision", "ADDED"),
         ("cycle", "ADDED"),
     ]
-    assert delta[1]["collision_nodes"] == ["pkg.a", "pkg.b"]
+    assert delta[1] == {
+        "action": "ADDED",
+        "diagnostic_kind": "collision",
+        "diagnostic_key": json.dumps(
+            ["collision", "NAME_COLLISION", "function", False, "target", "pkg.a", "pkg.b"],
+            separators=(",", ":"), sort_keys=True,
+        ),
+        "collision_kind": "NAME_COLLISION",
+        "collision_artifact_type": "function",
+        "collision_symbol": "target",
+        "collision_is_identical": False,
+        "collision_nodes": ["pkg.a", "pkg.b"],
+    }
     assert delta[2]["cycle_nodes"] == ["pkg.a", "pkg.b", "pkg.a"]
     assert ipc_module._build_diagnostic_delta(
         _diagnostic_state(freshness="deferred"), current
     ) == []


+def test_committed_collision_and_cycle_lifecycles_publish_exact_added_and_resolved_payloads():
+    collision = _collision_error()
+    cycle = ["pkg.a", "pkg.b", "pkg.a"]
+    phases = [([collision], []), ([], []), ([], [cycle]), ([], [])]
+
+    def updater(state, _path):
+        state.collisions, state.cycles = phases.pop(0)
+        return SimpleNamespace(status="UPDATED", file_path="pkg/change.py")
+
+    server = CanonicalLiveServer(_diagnostic_state(), updater=updater)
+    events = []
+    for _ in range(4):
+        server._dispatch({"operation": "update_file", "file_path": "pkg/change.py"})
+        events.append(server._events[-1]["diagnostic_changes"]["items"][0])
+
+    collision_key = json.dumps(
+        ["collision", "NAME_COLLISION", "function", False, "target", "pkg.a", "pkg.b"],
+        separators=(",", ":"), sort_keys=True,
+    )
+    assert events[0] == {
+        "action": "ADDED", "diagnostic_kind": "collision", "diagnostic_key": collision_key,
+        "collision_kind": "NAME_COLLISION", "collision_artifact_type": "function",
+        "collision_symbol": "target", "collision_is_identical": False,
+        "collision_nodes": ["pkg.a", "pkg.b"],
+    }
+    assert events[1] == {**events[0], "action": "RESOLVED"}
+    assert events[2] == {
+        "action": "ADDED", "diagnostic_kind": "cycle",
+        "diagnostic_key": json.dumps(["cycle", *cycle], separators=(",", ":"), sort_keys=True),
+        "cycle_nodes": cycle,
+    }
+    assert events[3] == {**events[2], "action": "RESOLVED"}
+
+
+@pytest.mark.parametrize("family", ["syntax", "collision", "cycle"])
+@pytest.mark.parametrize("previous_freshness,current_freshness", [("deferred", "fresh"), ("fresh", "stale")])
+def test_diagnostic_delta_fails_closed_when_either_family_side_is_not_fresh(
+    family, previous_freshness, current_freshness
+):
+    previous = _diagnostic_state()
+    current = _diagnostic_state()
+    state_name = "syntax_diagnostics_state" if family == "syntax" else f"{family}s_state"
+    setattr(previous, state_name, previous_freshness)
+    setattr(current, state_name, current_freshness)
+    current.syntax_diagnostics_by_path = {
+        "pkg/bad.py": {"status": "checked_with_errors", "errors": [{"message": "bad", "line_number": 1, "column_number": 0}]}
+    }
+    current.collisions = [_collision_error()]
+    current.cycles = [["pkg.a", "pkg.b", "pkg.a"]]
+    assert not any(
+        change["diagnostic_kind"] == family
+        for change in ipc_module._build_diagnostic_delta(previous, current)
+    )
+
+
+def test_diagnostic_delta_skips_malformed_facts_and_orders_mixed_actions_deterministically():
+    malformed = _collision_error()
+    malformed.symbol_details = [{"name": "left", "artifact_type": "function"}, {"name": "right", "artifact_type": "function"}]
+    bad_bool = _collision_error()
+    bad_bool.is_identical = 0
+    inconsistent = _collision_error()
+    inconsistent.symbol_details[1]["artifact_type"] = "class"
+    invalid_nodes = _collision_error()
+    invalid_nodes.nodes = ["pkg.a", 4]
+    malformed_current = _diagnostic_state(
+        collisions=[malformed, bad_bool, inconsistent, invalid_nodes],
+        cycles=[["pkg.a", "pkg.b"], ["pkg.a", 2, "pkg.a"], ["only"]],
+    )
+    assert ipc_module._build_diagnostic_delta(_diagnostic_state(), malformed_current) == []
+
+    previous = _diagnostic_state(
+        syntax={"z.py": {"status": "checked_with_errors", "errors": [{"message": "z", "line_number": 1, "column_number": 0}]}},
+        collisions=[_collision_error()], cycles=[["pkg.z", "pkg.a", "pkg.z"]],
+    )
+    current = _diagnostic_state(
+        syntax={"a.py": {"status": "checked_with_errors", "errors": [{"message": "a", "line_number": 1, "column_number": 0}]}},
+        cycles=[["pkg.a", "pkg.b", "pkg.a"]],
+    )
+    delta = ipc_module._build_diagnostic_delta(previous, current)
+    assert [(item["diagnostic_kind"], item["action"]) for item in delta] == [
+        ("syntax", "ADDED"), ("syntax", "RESOLVED"),
+        ("collision", "RESOLVED"),
+        ("cycle", "ADDED"), ("cycle", "RESOLVED"),
+    ]
+    assert [item["diagnostic_key"] for item in delta[:2]] == sorted(
+        item["diagnostic_key"] for item in delta[:2]
+    )
+
+
+def test_unchanged_fresh_diagnostics_do_not_add_a_journal_field():
+    state = _diagnostic_state(
+        syntax={"pkg/bad.py": {"status": "checked_with_errors", "errors": [{"message": "bad", "line_number": 1, "column_number": 0}]}},
+        collisions=[_collision_error()], cycles=[["pkg.a", "pkg.b", "pkg.a"]],
+    )
+    server = CanonicalLiveServer(
+        state, updater=lambda _state, _path: SimpleNamespace(status="UPDATED", file_path="pkg/change.py")
+    )
+    server._dispatch({"operation": "update_file", "file_path": "pkg/change.py"})
+    assert "diagnostic_changes" not in server._events[-1]
+
+
 def test_update_file_publishes_only_committed_bounded_diagnostic_delta(monkeypatch):
     trace_events = []
     monkeypatch.setattr(
@@ -128,6 +246,8 @@ def test_update_file_publishes_only_committed_bounded_diagnostic_delta(monkeypat
         for _domain, event, fields in trace_events
         if event.startswith("LIVE_DIAGNOSTIC_")
     )
+    assert len([event for _domain, event, _fields in trace_events if event == "LIVE_DIAGNOSTIC_SYNTAX_ERROR"]) == 4
+    assert len([event for _domain, event, _fields in trace_events if event == "LIVE_DIAGNOSTIC_SYNTAX_RECOVERED"]) == 4


 def test_client_request_timeout_closes_connection(monkeypatch):
@@ -552,10 +672,12 @@ def test_persistence_conflict_fails_closed_without_live_event():
     monkeypatch = pytest.MonkeyPatch()
     monkeypatch.setattr(runtime_trace, "trace_event", lambda *args, **kwargs: events.append((args, kwargs)))
     try:
-        initial = SimpleNamespace(files=[])
+        initial = _diagnostic_state()
         def updater(state, _path):
-            state.files.append("x")
-            return {"status": "UPDATED"}
+            state.syntax_diagnostics_by_path = {
+                "pkg/bad.py": {"status": "checked_with_errors", "errors": [{"message": "bad", "line_number": 1, "column_number": 0}]}
+            }
+            return SimpleNamespace(status="UPDATED", file_path="pkg/bad.py")
         def persister(_state, revision):
             raise SnapshotRevisionConflict(11, revision)
         server = CanonicalLiveServer(initial, updater=updater, persister=persister)
@@ -566,6 +688,7 @@ def test_persistence_conflict_fails_closed_without_live_event():
         assert server._state is initial
         assert server._activity_seq == 0
         assert not any(e[0][1] == "update_file" for e in server._events)
+        assert not any(args[1].startswith("LIVE_DIAGNOSTIC_") for args, _kwargs in events)
     finally:
         monkeypatch.undo()

diff --git a/tests/test_runtime_trace.py b/tests/test_runtime_trace.py
index 80f7b99..441ea74 100644
--- a/tests/test_runtime_trace.py
+++ b/tests/test_runtime_trace.py
@@ -78,6 +78,44 @@ def test_diagnostic_trace_fields_and_structured_node_arrays_are_durable():
     assert record["collision_is_identical"] is False


+def test_diagnostic_trace_records_preserve_exact_contract_fields_for_all_families():
+    path = trace.start_desktop_trace_session()
+    trace.trace_event(
+        "LIVE", "LIVE_DIAGNOSTIC_SYNTAX_ERROR", op="diag-18", rev=18,
+        origin="desktop_watcher", diagnostic_kind="syntax", diagnostic_key='["syntax","pkg/bad.py",2,1]',
+        path="pkg/bad.py", error="invalid syntax", line_number=2, column_number=1,
+        diagnostic_total=3, diagnostic_truncated=False,
+    )
+    trace.trace_event(
+        "LIVE", "LIVE_DIAGNOSTIC_COLLISION_ADDED", op="diag-18", rev=18,
+        origin="desktop_watcher", diagnostic_kind="collision", diagnostic_key='["collision","target"]',
+        collision_kind="NAME_COLLISION", collision_artifact_type="function", collision_symbol="target",
+        collision_is_identical=False, collision_nodes=["pkg.a", "pkg.b"],
+        diagnostic_total=3, diagnostic_truncated=False,
+    )
+    trace.trace_event(
+        "LIVE", "LIVE_DIAGNOSTIC_CYCLE_ADDED", op="diag-18", rev=18,
+        origin="desktop_watcher", diagnostic_kind="cycle", diagnostic_key='["cycle","pkg.a","pkg.b","pkg.a"]',
+        cycle_nodes=["pkg.a", "pkg.b", "pkg.a"], diagnostic_total=3, diagnostic_truncated=True,
+    )
+    trace.finish_desktop_trace_session()
+    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
+    diagnostics = [item for item in records if item.get("ev", "").startswith("LIVE_DIAGNOSTIC_")]
+    assert [(item["ev"], item["rev"], item["op"], item["origin"], item["diagnostic_kind"]) for item in diagnostics] == [
+        ("LIVE_DIAGNOSTIC_SYNTAX_ERROR", 18, "diag-18", "desktop_watcher", "syntax"),
+        ("LIVE_DIAGNOSTIC_COLLISION_ADDED", 18, "diag-18", "desktop_watcher", "collision"),
+        ("LIVE_DIAGNOSTIC_CYCLE_ADDED", 18, "diag-18", "desktop_watcher", "cycle"),
+    ]
+    assert diagnostics[0]["diagnostic_key"] == '["syntax","pkg/bad.py",2,1]'
+    assert diagnostics[1]["diagnostic_key"] == '["collision","target"]'
+    assert diagnostics[2]["diagnostic_key"] == '["cycle","pkg.a","pkg.b","pkg.a"]'
+    assert diagnostics[1]["collision_nodes"] == ["pkg.a", "pkg.b"]
+    assert diagnostics[2]["cycle_nodes"] == ["pkg.a", "pkg.b", "pkg.a"]
+    assert diagnostics[1]["collision_is_identical"] is False
+    assert diagnostics[0]["diagnostic_truncated"] is False
+    assert diagnostics[2]["diagnostic_truncated"] is True
+
+
 def test_default_trace_session_uses_external_runtime_logs_root(tmp_path, monkeypatch):
     state = tmp_path / "user-state"
     monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(state))

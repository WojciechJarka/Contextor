STATUS=PASS

THREE_CONTRACTS_ADDED
- A real ValidationError with valid collision core fields but no symbol_details yields no collision delta.
- Two syntax ADDED diagnostics with distinct keys are emitted in lexical diagnostic_key order.
- A structurally valid diagnostic_changes envelope whose every item is non-renderable falls back to the existing watcher message.

TEST_RESULTS
- Focused pytest: 186 passed, 1 warning.
- Exact focused selection collected 186 tests.
- py_compile tests/test_live_state_ipc.py tests/test_live_activity_status.py: PASS.
- git diff --check: PASS.

FILES_CHANGED
- tests/test_live_state_ipc.py
- tests/test_live_activity_status.py

PREEXISTING_WORKTREE_CHANGES
- NONE

COMPLETE FULL_DIFF
warning: in the working copy of 'tests/test_live_activity_status.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_state_ipc.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/test_live_activity_status.py b/tests/test_live_activity_status.py
index e34ca5c..a9e5bf0 100644
--- a/tests/test_live_activity_status.py
+++ b/tests/test_live_activity_status.py
@@ -234,6 +234,24 @@ def test_desktop_feed_formats_generic_diagnostic_delta_and_ignores_malformed_pay
     )


+def test_desktop_feed_falls_back_when_valid_envelope_has_only_non_renderable_items():
+    feed = DesktopLiveEventFeed(SimpleNamespace(), lambda *_args, **_kwargs: None, initial_seq=0)
+    event = {
+        "operation": "update_file", "origin": "desktop_watcher", "status": "UPDATED",
+        "file_path": "pkg/change.py", "canonical_revision": 18,
+        "diagnostic_changes": {
+            "total": 3, "truncated": False,
+            "items": [
+                {"action": "UNKNOWN", "diagnostic_kind": "syntax"},
+                {"action": "ADDED", "diagnostic_kind": "collision", "collision_nodes": ["pkg.a"]},
+                {"action": "RESOLVED", "diagnostic_kind": "cycle", "cycle_nodes": ["pkg.a", 2]},
+            ],
+        },
+    }
+
+    assert feed._message(event) == "[LIVE] Watcher updated change.py (rev 18)"
+
+
 @pytest.mark.parametrize(
     "item, expected",
     [
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index fbe704b..cbd770b 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -181,6 +181,37 @@ def test_diagnostic_delta_skips_malformed_facts_and_orders_mixed_actions_determi
     )


+def test_diagnostic_delta_skips_real_collision_without_symbol_details():
+    collision = ValidationError(
+        kind="NAME_COLLISION", message="collision", nodes=["pkg.b", "pkg.a"]
+    )
+    collision.artifact_type = "function"
+    collision.is_identical = False
+    current = _diagnostic_state(collisions=[collision])
+
+    assert not any(
+        change["diagnostic_kind"] == "collision"
+        for change in ipc_module._build_diagnostic_delta(_diagnostic_state(), current)
+    )
+
+
+def test_diagnostic_delta_orders_same_kind_and_action_by_lexical_key():
+    current = _diagnostic_state(
+        syntax={
+            "pkg/z.py": {"status": "checked_with_errors", "errors": [{"message": "z", "line_number": 1, "column_number": 0}]},
+            "pkg/a.py": {"status": "checked_with_errors", "errors": [{"message": "a", "line_number": 1, "column_number": 0}]},
+        }
+    )
+    changes = ipc_module._build_diagnostic_delta(_diagnostic_state(), current)
+
+    assert [(change["diagnostic_kind"], change["action"]) for change in changes] == [
+        ("syntax", "ADDED"), ("syntax", "ADDED")
+    ]
+    assert [change["diagnostic_key"] for change in changes] == sorted(
+        change["diagnostic_key"] for change in changes
+    )
+
+
 def test_unchanged_fresh_diagnostics_do_not_add_a_journal_field():
     state = _diagnostic_state(
         syntax={"pkg/bad.py": {"status": "checked_with_errors", "errors": [{"message": "bad", "line_number": 1, "column_number": 0}]}},

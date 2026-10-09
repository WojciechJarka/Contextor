# L37_L38_A3C_GLOBAL_REGRESSION_REPAIR_CONTINUATION

## CURRENT_HEAD
`a405304af6293ec8457693e7e16c42b315271bfb` (`Auto-commit: Cleanup and update`). Contextor LIVE revision 114 reported fresh canonical state and `workspace_sync=verified`; both edited test modules had fresh syntax diagnostics with zero errors. Final Git check found no diff in `contextor/ui/gui.py` or `contextor/core/live_state/watcher.py`.

## FILES_CHANGED
- `tests/test_live_desktop_integration.py`
- `tests/test_gui_live_startup.py`
- `walkthrough.md` is this report; it is excluded from the code/test diff list.

## UPDATED_GENERATION_CONFLICT_CONTRACT
Auditor decision implemented in tests only. Same-revision generation conflicts register recovery and request full analysis, then watcher/feed startup continues. Incremental mutation admission is deferred while the repository incident remains active.

The two tests were renamed to describe that behavior. Each now verifies:
- publish call count remains zero;
- generation-conflict status is reported;
- the real `_request_full_analysis_recovery` method is called through the retained `MagicMock(wraps=...)` spy;
- the canonical repository incident exists with a positive non-boolean integer generation and `required is True`;
- watcher and event feed are constructed and started;
- the watcher receives the closure returned by the real bound `_watcher_recovery_admission` method;
- a mutation action returns `RECOVERY_DEFERRED`, does not execute, and leaves the incident present.

The only remaining `_start_live_watcher_blocking` fixture without `_with_live_recovery_contract` is the unregistered-repository test. Contextor source shows that the identity guard returns before watcher/recovery-method access when the repository is not registered; the focused suite passed that test. The repository-switch, inactive-repository, startup, publish, busy-writer and analysis-lease fixtures use the helper and real bound recovery descriptors.

## RECOVERY_ADMISSION_EVIDENCE
**CONTRACT_PROVED:** The supplied auditor decision is the contract for generation conflict. Contextor `get_symbol_call_context` at revision 114 confirmed the production caller `ContextorGUI._start_live_watcher_blocking -> ContextorGUI._watcher_recovery_admission` at `contextor/ui/gui.py:1930`.

**CODE_PATH_PROVED:** `_watcher_recovery_admission` locks the real incident registry and returns `RECOVERY_DEFERRED` instead of invoking the submitted action while the repository key is present. `DesktopLiveWatcher._recovery_is_active` routes through this closure; `poll_once` checks that gate at watcher lines 669, 715 and 805. The updated integration tests exercise the captured closure and sentinel directly. The generation-conflict status/request branch is at `contextor/ui/gui.py:1772-1780`; startup at `:1955-1956` follows the auditor-approved contract.

**DIRECT_EVIDENCE:** The updated exact ten-node set passed, and all four requested targeted files passed. Git confirms production GUI and watcher files are unchanged.

## ORIGINAL_TEN_TEST_RESULTS
The original ten nodes were run before changing the outdated generation-conflict expectations. Result: `8 passed, 2 failed`. The two failures were only the old assertions requiring `watcher_starts == []` and `feed_starts == []`; each observed the intentional constructed/started sequence. The other eight nodes passed.

The same ten cases after the expectation correction passed: `10 passed, 1 warning`. The two renamed nodes are:
- `test_same_revision_different_state_id_registers_recovery_and_defers_updates`
- `test_same_revision_missing_state_id_registers_recovery_and_defers_updates`

## FOUR_FILE_REGRESSION_RESULTS
Fresh process, exact command:
`python -m pytest -q --tb=short tests/test_gui_live_startup.py tests/test_live_desktop_integration.py tests/test_watcher_recovery_admission.py tests/test_recovery_authority_gate.py`

Result: `98 passed, 1 warning in 11.04s`. The warning is the existing Authlib JOSE deprecation warning. No full-repository pytest run was performed.

The complete GUI test file was also run by itself in a fresh pytest process after the T9 cleanup correction: `34 passed, 1 warning in 8.06s`.

## T9_DIAGNOSTIC_STATUS
**T9_ORIGIN=A2 — test-harness cleanup contamination, directly mapped.** Before the correction, the four-file run reproduced `invalid command name "2067808402880<lambda>"`. A temporary local trace of `tkinter.Misc.after` recorded that exact Tcl script as `after#11`, registered on the preceding real-Tk test's root. Its Python callback was `_bind_recovery_prompt.<locals>.<lambda>` at `tests/test_gui_live_startup.py:638`, which delegates to `ContextorGUI._drain_live_recovery_queue`. The drain's reschedule is registered at `contextor/ui/gui.py:1261` and stored in `_live_recovery_after_id`.

The preceding test's last main loop is at `tests/test_gui_live_startup.py:953`; its `finally` set `_closing=True` and called `root.destroy()` at `:957-959` without cancelling that stored timer. The T9 test's own recovery callback was separately cancelled by `on_closing` (`contextor/ui/gui.py:2147`); the invalid Tcl script matched the prior test's callback, not T9's tracked callback.

Correction: the preceding test cleanup now cancels its currently tracked recovery timer, clears the ID, and asserts that the ID is absent from `after info` before destroying the root. The T9 stderr assertion remains intact. After the correction, the full GUI file and the four-file regression both passed. No production callback change was made.

## REMAINING_RISKS
- The user-supplied global baseline (`2941 passed, 10 failed, 1 skipped`) was not re-certified with the full repository suite, as instructed.
- The focused run retains one upstream Authlib deprecation warning.
- Temporary callback tracing artifacts were removed; no trace plugin or JSON file remains in the repository or `C:\Temp` paths used for tracing.

## FINAL_VERDICT
`PASS_FOCUSED_TARGETED`. The original ten nodes and all four targeted files pass after the test-contract corrections. T9's reproduced Tcl diagnostic was traced to and corrected in the preceding test's cleanup. Production source, watcher, LIVE IPC, storage, certificates and backend ownership were not modified.

## FULL_DIFFS
### tests/test_live_desktop_integration.py
```diff
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index b616e62..5b5c340 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -14,7 +14,7 @@ from contextor.core.analysis.full_analysis_coordinator import (
 )
 from contextor.core.analysis.state_manager import FileStateManager
 from contextor.core.errors import AnalysisCancelled
-from contextor.core.live_state.watcher import DesktopLiveWatcher
+from contextor.core.live_state.watcher import RECOVERY_DEFERRED, DesktopLiveWatcher
 from contextor.core.paths import repo_cache_dir
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.core.repository_identity import read_repository_identity
@@ -170,36 +170,41 @@ def test_same_revision_startup_attaches_without_redundant_publish(tmp_path, monk
     assert "LIVE: shared state attached; watcher active" in statuses
 
 
-def test_same_revision_different_state_id_does_not_attach_as_same_generation(tmp_path, monkeypatch):
+def test_same_revision_different_state_id_registers_recovery_and_defers_updates(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
     repo.mkdir()
     PersistentIdentityRegistry(str(repo))
     loaded = SimpleNamespace(modules={}, revision=7, state_id="loaded-generation")
     remote = SimpleNamespace(modules={}, revision=7, state_id="remote-generation")
-    events = []
+    publish_calls = []
     statuses = []
     watcher_starts = []
     feed_starts = []
+    watcher_kwargs = []
 
     class Client:
         def snapshot(self):
             return {"state": remote, "revision": 7}
 
         def publish(self, *_args, **_kwargs):
-            events.append("publish")
+            publish_calls.append(True)
+            return {"status": "ok"}
 
     class Watcher:
-        def __init__(self, *_args, **_kwargs): watcher_starts.append(True)
+        def __init__(self, *_args, **kwargs):
+            watcher_kwargs.append(kwargs)
+            watcher_starts.append("constructed")
+
         def start(self): watcher_starts.append("started")
 
     class Feed:
-        def __init__(self, *_args, **_kwargs): feed_starts.append(True)
+        def __init__(self, *_args, **_kwargs): feed_starts.append("constructed")
+
         def start(self): feed_starts.append("started")
 
     controller = _with_live_recovery_contract(SimpleNamespace(
         live_watcher=None, live_event_feed=None, live_watchers={},
         live_event_feeds={}, repo_id_var=_LiveIntegrationFakeVar(),
-        _request_full_analysis_recovery=MagicMock(),
         _set_live_status=statuses.append,
     ))
     controller._request_full_analysis_recovery = MagicMock(
@@ -217,42 +222,66 @@ def test_same_revision_different_state_id_does_not_attach_as_same_generation(tmp
 
     gui.ContextorGUI._start_live_watcher_blocking(controller, str(repo))
 
-    assert events == []
+    assert publish_calls == []
     assert "LIVE: generation conflict; analysis required" in statuses
     controller._request_full_analysis_recovery.assert_called_once_with(str(repo), "Canonical state identity mismatch.")
-    assert watcher_starts == []
-    assert feed_starts == []
+    incident = controller._live_recovery_incident(str(repo))
+    assert incident is not None
+    assert isinstance(incident["generation"], int) and not isinstance(incident["generation"], bool)
+    assert incident["generation"] > 0
+    assert incident["required"] is True
+    assert controller._live_recovery_incidents[str(repo.resolve())] == incident
+    assert watcher_starts == ["constructed", "started"]
+    assert feed_starts == ["constructed", "started"]
+    recovery_admission = watcher_kwargs[0]["recovery_admission"]
+    assert callable(recovery_admission)
+    assert recovery_admission.__name__ == "admit"
 
+    mutation_actions = []
 
-def test_same_revision_missing_state_id_does_not_start_live_components(tmp_path, monkeypatch):
+    def mutation_action():
+        mutation_actions.append("executed")
+
+    assert recovery_admission(mutation_action) is RECOVERY_DEFERRED
+    assert mutation_actions == []
+    assert controller._live_recovery_incident(str(repo)) == incident
+
+
+def test_same_revision_missing_state_id_registers_recovery_and_defers_updates(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
     repo.mkdir()
     PersistentIdentityRegistry(str(repo))
     loaded = SimpleNamespace(modules={}, revision=7, state_id="loaded-generation")
     remote = SimpleNamespace(modules={}, revision=7)
+    publish_calls = []
     statuses = []
     watcher_starts = []
     feed_starts = []
+    watcher_kwargs = []
 
     class Client:
         def snapshot(self):
             return {"state": remote, "revision": 7}
 
         def publish(self, *_args, **_kwargs):
-            raise AssertionError("same-revision generation conflict must not publish")
+            publish_calls.append(True)
+            return {"status": "ok"}
 
     class Watcher:
-        def __init__(self, *_args, **_kwargs): watcher_starts.append(True)
+        def __init__(self, *_args, **kwargs):
+            watcher_kwargs.append(kwargs)
+            watcher_starts.append("constructed")
+
         def start(self): watcher_starts.append("started")
 
     class Feed:
-        def __init__(self, *_args, **_kwargs): feed_starts.append(True)
+        def __init__(self, *_args, **_kwargs): feed_starts.append("constructed")
+
         def start(self): feed_starts.append("started")
 
     controller = _with_live_recovery_contract(SimpleNamespace(
         live_watcher=None, live_event_feed=None, live_watchers={},
         live_event_feeds={}, repo_id_var=_LiveIntegrationFakeVar(),
-        _request_full_analysis_recovery=MagicMock(),
         _set_live_status=statuses.append,
     ))
     controller._request_full_analysis_recovery = MagicMock(
@@ -270,10 +299,29 @@ def test_same_revision_missing_state_id_does_not_start_live_components(tmp_path,
 
     gui.ContextorGUI._start_live_watcher_blocking(controller, str(repo))
 
+    assert publish_calls == []
     assert "LIVE: generation conflict; analysis required" in statuses
     controller._request_full_analysis_recovery.assert_called_once_with(str(repo), "Canonical state identity mismatch.")
-    assert watcher_starts == []
-    assert feed_starts == []
+    incident = controller._live_recovery_incident(str(repo))
+    assert incident is not None
+    assert isinstance(incident["generation"], int) and not isinstance(incident["generation"], bool)
+    assert incident["generation"] > 0
+    assert incident["required"] is True
+    assert controller._live_recovery_incidents[str(repo.resolve())] == incident
+    assert watcher_starts == ["constructed", "started"]
+    assert feed_starts == ["constructed", "started"]
+    recovery_admission = watcher_kwargs[0]["recovery_admission"]
+    assert callable(recovery_admission)
+    assert recovery_admission.__name__ == "admit"
+
+    mutation_actions = []
+
+    def mutation_action():
+        mutation_actions.append("executed")
+
+    assert recovery_admission(mutation_action) is RECOVERY_DEFERRED
+    assert mutation_actions == []
+    assert controller._live_recovery_incident(str(repo)) == incident
 
 
 def test_desktop_publishes_latest_snapshot_and_replaces_existing_watcher(
```

### tests/test_gui_live_startup.py
```diff
diff --git a/tests/test_gui_live_startup.py b/tests/test_gui_live_startup.py
index 5d3975a..784d696 100644
--- a/tests/test_gui_live_startup.py
+++ b/tests/test_gui_live_startup.py
@@ -956,6 +956,11 @@ def test_recovery_decline_reprompts_once_after_reselection_with_real_tk(
         controller.analyze.assert_not_called()
     finally:
         controller._closing = True
+        recovery_after_id = controller._live_recovery_after_id
+        if recovery_after_id is not None:
+            root.after_cancel(recovery_after_id)
+        controller._live_recovery_after_id = None
+        assert recovery_after_id not in root.tk.call("after", "info")
         root.destroy()
```

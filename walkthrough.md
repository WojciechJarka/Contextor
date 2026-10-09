# L37_L38_A3C_GLOBAL_REGRESSION_REPAIR — checkpoint

## CURRENT_HEAD
`908bf1cf45769a9f5280d0489ac7670a513089e8` (unchanged). Target source was clean at this HEAD before fixture edits. Contextor canonical LIVE source was fresh and `workspace_sync=verified`; latest inspected revision 111.

## Stage
Focused diagnosis and fixture-only work. Stopped at a proven source/test behavior divergence in Group B before any production edit. No full repository suite, service restart, or manual LIVE update was run.

## T9_CALLBACK_ORIGIN
**Classification: UNKNOWN / not reproduced.** The exact T9 node passed in the corrected ten-node run after the fixture helper change. No invalid Tcl diagnostic appeared in that run. Direct source evidence: `ContextorGUI.__init__` stores the ID returned by `root.after(100, self._drain_live_recovery_queue)`; the drain reschedule also stores the new ID; `on_closing` clears and cancels the stored recovery ID before `root.destroy()`. T9 additionally schedules a test-harness post-paint lambda at 50 ms (the real post-paint method is monkeypatched to a no-op); that callback is not the recovery callback and its origin is not evidence for the reported Tcl diagnostic. The preceding real-Tk test's cleanup is a possible test-harness lead, but no causal link was demonstrated. A1 production defect, A2 harness contamination, and A3 shared-state interference are therefore not proven.

## T9_CORRECTION
None. Do not change production or remove diagnostic assertions on current evidence. Full `tests/test_gui_live_startup.py` was not run at this checkpoint; T9 origin remains unresolved.

## DESKTOP_FIXTURE_CONTRACT
A helper was added to initialize the GUI recovery fields used by the real methods: retry/recovery timer IDs, queue, pending-prompt set, lock, incident registry, generation registry, and closing flag. It binds `_live_recovery_incident` and `_watcher_recovery_admission` using the real `ContextorGUI` function descriptors. The two generation-conflict fixtures retain call assertions with a `MagicMock(wraps=real_bound_method)` spy for `_request_full_analysis_recovery`; the production method executes and creates the actual recovery incident, so the spy does not bypass incident identity or admission.

**Direct source evidence / Group B divergence:** `contextor/ui/gui.py:1772-1778` reports a generation conflict and requests full-analysis recovery, but that branch has no return. The method then constructs `DesktopLiveWatcher` with the real recovery-admission closure (`:1925-1931`), creates the event feed, and calls `watcher.start()` / `feed.start()` (`:1955-1956`). `DesktopLiveWatcher._recovery_is_active` is checked by `poll_once` at lines 669, 715, and 805, so subsequent recovery actions are gated; that gate does not prevent startup itself. The two existing tests explicitly expect neither watcher nor feed to start. With the real request method executing, both tests still fail at `watcher_starts == []` and observe `[True, 'started']`. The source/test startup contract conflict is proven; whether the intended contract is “do not start components” or “start but defer incremental actions” requires the auditor's design decision. No production file was changed.

## FILES_CHANGED
- `tests/test_live_desktop_integration.py`
- `walkthrough.md` is this report and excluded from the code/test diff list.

## FULL_DIFFS
```diff
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index 5653635..b616e62 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -31,6 +31,24 @@ class _LiveIntegrationFakeVar:
         self.value = value
 
 
+def _with_live_recovery_contract(controller):
+    controller._live_start_retry_after_id = None
+    controller._live_recovery_after_id = None
+    controller._live_recovery_queue = gui.Queue()
+    controller._live_recovery_prompt_pending = set()
+    controller._live_recovery_lock = threading.Lock()
+    controller._live_recovery_incidents = {}
+    controller._live_recovery_generations = {}
+    controller._closing = False
+    controller._live_recovery_incident = (
+        gui.ContextorGUI._live_recovery_incident.__get__(controller, gui.ContextorGUI)
+    )
+    controller._watcher_recovery_admission = (
+        gui.ContextorGUI._watcher_recovery_admission.__get__(controller, gui.ContextorGUI)
+    )
+    return controller
+
+
 def test_watcher_recovery_emits_start_and_existing_result(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
     repo.mkdir()
@@ -133,11 +151,11 @@ def test_same_revision_startup_attaches_without_redundant_publish(tmp_path, monk
         def start(self): pass
 
     statuses = []
-    controller = SimpleNamespace(
+    controller = _with_live_recovery_contract(SimpleNamespace(
         live_watcher=None, live_event_feed=None, live_watchers={},
         live_event_feeds={}, repo_id_var=_LiveIntegrationFakeVar(),
         _set_live_status=statuses.append,
-    )
+    ))
     monkeypatch.setattr(gui, "connect_or_start", lambda *_args, **_kwargs: Client())
     monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
     monkeypatch.setattr(gui, "DesktopLiveEventFeed", Feed)
@@ -178,11 +196,16 @@ def test_same_revision_different_state_id_does_not_attach_as_same_generation(tmp
         def __init__(self, *_args, **_kwargs): feed_starts.append(True)
         def start(self): feed_starts.append("started")
 
-    controller = SimpleNamespace(
+    controller = _with_live_recovery_contract(SimpleNamespace(
         live_watcher=None, live_event_feed=None, live_watchers={},
         live_event_feeds={}, repo_id_var=_LiveIntegrationFakeVar(),
         _request_full_analysis_recovery=MagicMock(),
         _set_live_status=statuses.append,
+    ))
+    controller._request_full_analysis_recovery = MagicMock(
+        wraps=gui.ContextorGUI._request_full_analysis_recovery.__get__(
+            controller, gui.ContextorGUI
+        )
     )
     monkeypatch.setattr(gui, "connect_or_start", lambda *_args, **_kwargs: Client())
     monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
@@ -226,11 +249,16 @@ def test_same_revision_missing_state_id_does_not_start_live_components(tmp_path,
         def __init__(self, *_args, **_kwargs): feed_starts.append(True)
         def start(self): feed_starts.append("started")
 
-    controller = SimpleNamespace(
+    controller = _with_live_recovery_contract(SimpleNamespace(
         live_watcher=None, live_event_feed=None, live_watchers={},
         live_event_feeds={}, repo_id_var=_LiveIntegrationFakeVar(),
         _request_full_analysis_recovery=MagicMock(),
         _set_live_status=statuses.append,
+    ))
+    controller._request_full_analysis_recovery = MagicMock(
+        wraps=gui.ContextorGUI._request_full_analysis_recovery.__get__(
+            controller, gui.ContextorGUI
+        )
     )
     monkeypatch.setattr(gui, "connect_or_start", lambda *_args, **_kwargs: Client())
     monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
@@ -282,14 +310,14 @@ def test_desktop_publishes_latest_snapshot_and_replaces_existing_watcher(
         def stop(self):
             events.append(("feed-stop",))
 
-    controller = SimpleNamespace(
+    controller = _with_live_recovery_contract(SimpleNamespace(
         live_watcher=None,
         live_event_feed=None,
         live_watchers={},
         live_event_feeds={},
         repo_id_var=_LiveIntegrationFakeVar(),
         _set_live_status=lambda message: events.append(("status", message)),
-    )
+    ))
     monkeypatch.setattr(gui, "connect_or_start", lambda *args, **kwargs: Client())
     monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
     monkeypatch.setattr(gui, "DesktopLiveEventFeed", EventFeed)
@@ -322,7 +350,10 @@ def test_desktop_skips_cache_publish_when_canonical_writer_is_busy_but_starts_wa
     class Feed:
         def __init__(self, *_args, **_kwargs): pass
         def start(self): starts.append("feed")
-    controller = SimpleNamespace(live_watcher=None, live_event_feed=None, live_watchers={}, live_event_feeds={}, repo_id_var=_LiveIntegrationFakeVar(), _set_live_status=statuses.append)
+    controller = _with_live_recovery_contract(SimpleNamespace(
+        live_watcher=None, live_event_feed=None, live_watchers={}, live_event_feeds={},
+        repo_id_var=_LiveIntegrationFakeVar(), _set_live_status=statuses.append,
+    ))
     monkeypatch.setattr(gui, "connect_or_start", lambda *_a, **_k: Client())
     monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
     monkeypatch.setattr(gui, "DesktopLiveEventFeed", Feed)
@@ -353,7 +384,10 @@ def test_desktop_startup_publish_uses_startup_publish_writer_kind(tmp_path, monk
     class Feed:
         def __init__(self, *_a, **_k): pass
         def start(self): pass
-    controller = SimpleNamespace(live_watcher=None, live_event_feed=None, live_watchers={}, live_event_feeds={}, repo_id_var=_LiveIntegrationFakeVar(), _set_live_status=lambda _m: None)
+    controller = _with_live_recovery_contract(SimpleNamespace(
+        live_watcher=None, live_event_feed=None, live_watchers={}, live_event_feeds={},
+        repo_id_var=_LiveIntegrationFakeVar(), _set_live_status=lambda _m: None,
+    ))
     monkeypatch.setattr(gui, "connect_or_start", lambda *_a, **_k: Client())
     monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
     monkeypatch.setattr(gui, "DesktopLiveEventFeed", Feed)
@@ -494,14 +528,14 @@ def test_switching_repositories_keeps_previous_watcher_active(tmp_path, monkeypa
         def stop(self):
             pass
 
-    controller = SimpleNamespace(
+    controller = _with_live_recovery_contract(SimpleNamespace(
         live_watcher=None,
         live_event_feed=None,
         live_watchers={},
         live_event_feeds={},
         repo_id_var=_LiveIntegrationFakeVar(),
         _set_live_status=lambda message: events.append(("status", message)),
-    )
+    ))
     monkeypatch.setattr(gui, "connect_or_start", lambda *args, **kwargs: Client())
     monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
     monkeypatch.setattr(gui, "DesktopLiveEventFeed", EventFeed)
@@ -581,7 +615,7 @@ def test_inactive_repository_callbacks_do_not_overwrite_selected_live_state(
         lambda *_args, **_kwargs: None,
     )
 
-    controller = SimpleNamespace(
+    controller = _with_live_recovery_contract(SimpleNamespace(
         repo_path_var=SimpleNamespace(get=lambda: str(first)),
         _selected_live_repo_path=str(first),
         repo_id_var=_LiveIntegrationFakeVar(),
@@ -592,7 +626,7 @@ def test_inactive_repository_callbacks_do_not_overwrite_selected_live_state(
         live_clients={},
         live_client=None,
         _set_live_status=lambda message, **_kwargs: statuses.append(message),
-    )
+    ))
 
     gui.ContextorGUI._start_live_watcher_blocking(controller, str(first))
     first_client = controller.live_clients[first_registry.repo_id]
@@ -856,7 +890,7 @@ def test_closing_gui_waits_for_active_analysis_lease_release(
 
     root = FakeRoot()
     progress_bar = FakeProgress()
-    controller = SimpleNamespace(
+    controller = _with_live_recovery_contract(SimpleNamespace(
         root=root,
         progress_bar=progress_bar,
         log_box=None,
@@ -871,7 +905,7 @@ def test_closing_gui_waits_for_active_analysis_lease_release(
         layer_path_var=SimpleNamespace(get=lambda: ""),
         file_path_var=SimpleNamespace(get=lambda: ""),
         _busy_buttons=lambda: [],
-    )
+    ))
 
     gui.ContextorGUI.analyze(controller)
     assert analysis_started.wait(timeout=2.0)
```

## EXACT_TEN_TEST_RESULTS
The exact ten nodes were selected from the reported ten-node checkpoint: T9 plus the eight watcher-startup fixture nodes that failed with missing recovery methods and the direct `ContextorGUI.analyze` lease consumer.

Nodes:
1. `tests/test_gui_live_startup.py::test_recovery_timer_is_cancelled_before_real_tk_shutdown`
2. `tests/test_live_desktop_integration.py::test_same_revision_startup_attaches_without_redundant_publish`
3. `tests/test_live_desktop_integration.py::test_same_revision_different_state_id_does_not_attach_as_same_generation`
4. `tests/test_live_desktop_integration.py::test_same_revision_missing_state_id_does_not_start_live_components`
5. `tests/test_live_desktop_integration.py::test_desktop_publishes_latest_snapshot_and_replaces_existing_watcher`
6. `tests/test_live_desktop_integration.py::test_desktop_skips_cache_publish_when_canonical_writer_is_busy_but_starts_watcher`
7. `tests/test_live_desktop_integration.py::test_desktop_startup_publish_uses_startup_publish_writer_kind`
8. `tests/test_live_desktop_integration.py::test_switching_repositories_keeps_previous_watcher_active`
9. `tests/test_live_desktop_integration.py::test_inactive_repository_callbacks_do_not_overwrite_selected_live_state`
10. `tests/test_live_desktop_integration.py::test_closing_gui_waits_for_active_analysis_lease_release`

- Before fixture repair: `9 failed, 1 passed`; T9 passed, nine desktop consumers failed on absent real recovery methods.
- After descriptor/state helper: `8 passed, 2 failed`; the two generation-conflict tests failed their existing no-start assertion. T9 passed.
- After replacing each recovery-request stub with a spy that wraps the actual bound method, the two affected nodes were rerun: `2 failed` at the same no-start assertion, with watcher start records `[True, 'started']`.
- The exact ten were not rerun after the final spy-only adjustment; no claim is made that the final tree has a complete ten-node pass.

## TARGETED_REGRESSION_RESULTS
Not run: the checkpoint stopped after the real recovery-request path confirmed the two existing startup assertions conflict with current production control flow. Required files still pending: `tests/test_gui_live_startup.py`, `tests/test_live_desktop_integration.py`, `tests/test_watcher_recovery_admission.py`, `tests/test_recovery_authority_gate.py`.

## REMAINING_RISKS
- T9's original Tcl diagnostic origin remains unproven; the exact node does not reproduce it.
- Two desktop tests cannot be made to pass through faithful fixture binding while preserving their current “no watcher/feed start” assertions and the current GUI source path. The production behavior is gated after startup, but startup itself occurs.
- The test-only diff is a partial checkpoint and does not constitute a final regression repair. No production edit was attempted.

## FINAL_VERDICT
`BLOCKED_AT_CONTRACT_DIVERGENCE`. Evidence proves that the generation-conflict branch requests recovery but continues to start LIVE components, while the two existing tests require no components to start. Following the task gate, production code is untouched and work stops for auditor direction. Continue only after the next `proceduj`.

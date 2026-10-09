# L37/L38 A3C T7 recovery reprompt fix

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\ui\gui.py`
- `C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py`
- Git HEAD before edits: `c7e2d479ba41a86e66835bcc6d62337896ef2d1a`. No other source/test/documentation changes. `walkthrough.md` is this report.

## T7_ROOT_CAUSE

- Contextor MCP was used first: deferred tools were enumerated, current documentation was read, and `get_symbol_implementation` resolved `ContextorGUI._drain_live_recovery_queue` (`gui.py:1185-1248`), `_request_full_analysis_recovery` (`:1128-1183`), and `_sync_selected_live_repository_path` (`:788-804`) at canonical revision 104 with `workspace_sync=verified`. A bounded call-context query returned no static intra-module caller edge for the Tk callback; Git verified the dynamic `root.after` schedule in `gui.py:162` and the source/test anchors. (DIRECT_EVIDENCE / CODE_PATH_PROVED.)
- Before the fix, a declined `messagebox.askyesno` retained the repository in `_live_recovery_prompt_pending` (`gui.py:1234-1245`). Reselection queues an existing incident only when the repository is absent from that set (`gui.py:799-804`). The previous native Tk run observed one prompt before and after A → B → A; the focused old test asserted the defective pending state. (CODE_PATH_PROVED plus prior real-Tk DIRECT_EVIDENCE.)
- A queued item whose incident had already disappeared could still reach the dialog because the old drain path changed the reason only when the incident existed and then continued to selection/dialog handling. (CODE_PATH_PROVED.)

## EXACT_FIX

- `gui.py`: when a queued repository has no current incident, discard its stale prompt-pending marker and skip the dialog. After a `False` answer, discard only that repository's prompt-pending marker under `_live_recovery_lock`. The incident and generation remain, and no immediate queue insertion or FULL call occurs. A `True` answer keeps the existing `analyze(recovery_repository=..., recovery_generation=...)` call and its pending deduplication state. `_sync_selected_live_repository_path` and watcher admission were not changed.
- `tests/test_gui_live_startup.py`: corrected the decline expectations; checked incident/generation persistence and blocked watcher admission; added a real Tk event-loop reselection test with a controlled nonblocking dialog decision and a worker-thread request; added a stale queued item regression. Existing accept, error, switched-repo, and worker-thread tests remain in place.
- The Tk regression exercises actual `Tk.mainloop()` and root callbacks. Its `askyesno` decision is a controlled replacement to avoid an unattended native modal; it does not claim a human-operated dialog. The test skips only if a Tk display cannot be created.

## TARGETED_TEST_RESULTS

- New/changed and direct focused tests: seven passed in 5.32 s: decline persistence/admission, real Tk A → B → A reprompt, stale queued item, accept deduplication, worker-thread queue, switched-repository suppression, and older-certificate isolation.
- Additional adjacent GUI recovery branches: four passed in 3.14 s: failed analysis, closed Desktop, dialog exception, and generation-conflict deduplication.
- `git diff --check` passed. Both runs emitted one external Authlib deprecation warning. No full repository pytest suite was run.
- LIVE watcher verification: Contextor `get_live_events(after_revision=104)` returned continuous revision 105, `resync_required=false`, `update_file` origin `desktop_watcher`, status `UPDATED`, path `C:\Temp\Contextor_Repo\contextor\ui\gui.py`. No manual `update_file` was called. A separate test-file event was not required by the canonical source scope and was not claimed.
- Production LIVE/IPC, durable storage, watcher mutation logic, and recovery certificate protocol were not edited. No process restart was performed.

## REGRESSION_VERDICT

- **PASS for the specified focused T7 behavior.** Decline retains the incident and watcher fence, clears the prompt marker, and does not immediately reopen; A → B → A queues exactly one later prompt. Accepted FULL remains deduplicated. Stale queued dialogs are discarded. Worker-origin recovery registration reaches the real Tk callback without a worker Tk call. No broader Desktop runtime certification is claimed.

## FULL_DIFFS

Complete actual Git diff for every changed source/test file:

diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 91fb6ac..a42c539 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -1196,9 +1196,15 @@ class ContextorGUI:
         else:
             with self._live_recovery_lock:
                 incident = self._live_recovery_incidents.get(repository_key)
-                if incident is not None:
+                if incident is None:
+                    self._live_recovery_prompt_pending.discard(
+                        repository_key
+                    )
+                else:
                     reason = incident["reason"]
-            if not ContextorGUI._is_selected_live_repository(
+            if incident is None:
+                pass
+            elif not ContextorGUI._is_selected_live_repository(
                 self, repository_key
             ):
                 with self._live_recovery_lock:
@@ -1240,6 +1246,11 @@ class ContextorGUI:
                         recovery_repository=repository_key,
                         recovery_generation=generation,
                     )
+                else:
+                    with self._live_recovery_lock:
+                        self._live_recovery_prompt_pending.discard(
+                            repository_key
+                        )
 
         finally:
             if not getattr(self, "_closing", False):
diff --git a/tests/test_gui_live_startup.py b/tests/test_gui_live_startup.py
index aec5314..c64d7e5 100644
--- a/tests/test_gui_live_startup.py
+++ b/tests/test_gui_live_startup.py
@@ -5,6 +5,7 @@ from types import SimpleNamespace
 from unittest.mock import MagicMock
 import threading
 import time
+import tkinter as tk
 
 import pytest
 
@@ -878,17 +879,106 @@ def test_recovery_prompt_decline_preserves_incident(tmp_path, monkeypatch):
     assert ask.call_args.kwargs["parent"] is root
     assert "Canonical state identity mismatch." in ask.call_args.args[1]
     controller.analyze.assert_not_called()
-    assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
+    assert controller._live_recovery_prompt_pending == set()
     assert controller._live_recovery_incidents[str(repo.resolve())]["required"] is True
+    assert controller._live_recovery_incidents[str(repo.resolve())]["generation"] == 1
+    assert ContextorGUI._watcher_recovery_admission(controller, str(repo))(
+        lambda: True
+    ) is gui.RECOVERY_DEFERRED
+
+    ContextorGUI._drain_live_recovery_queue(controller)
+    ask.assert_called_once()
+    assert controller._live_recovery_queue.qsize() == 0
 
     ContextorGUI._request_full_analysis_recovery(
         controller, str(repo), "Canonical state identity mismatch."
     )
-    assert controller._live_recovery_queue.qsize() == 0
+    assert controller._live_recovery_queue.qsize() == 1
+    assert controller._live_recovery_incidents[str(repo.resolve())]["generation"] == 2
     assert next(iter(root.scheduled.values()))[0] == 100
     ask.assert_called_once()
 
 
+def test_recovery_decline_reprompts_once_after_reselection_with_real_tk(
+    tmp_path, monkeypatch
+):
+    repo = tmp_path / "repo"
+    other = tmp_path / "other"
+    repo.mkdir()
+    other.mkdir()
+    try:
+        root = tk.Tk()
+    except tk.TclError as exc:
+        pytest.skip(f"Tk display unavailable: {exc}")
+    root.withdraw()
+    controller = _bind_recovery_prompt(_make_controller(repo, root))
+    main_thread = threading.get_ident()
+    dialog_threads = []
+
+    def decline(*_args, **kwargs):
+        dialog_threads.append(threading.get_ident())
+        assert kwargs["parent"] is root
+        return False
+
+    monkeypatch.setattr(gui.messagebox, "askyesno", decline)
+    worker = threading.Thread(
+        target=lambda: ContextorGUI._request_full_analysis_recovery(
+            controller, str(repo), "Recovery required."
+        )
+    )
+    try:
+        worker.start()
+        worker.join(5)
+        assert not worker.is_alive()
+        assert dialog_threads == []
+
+        root.after(10, controller._drain_live_recovery_queue)
+        root.after(250, root.quit)
+        root.mainloop()
+        assert dialog_threads == [main_thread]
+        assert controller._live_recovery_prompt_pending == set()
+        assert controller._live_recovery_incidents[str(repo.resolve())]["generation"] == 1
+
+        root.after(250, root.quit)
+        root.mainloop()
+        assert dialog_threads == [main_thread]
+
+        controller.repo_path_var.set(str(other))
+        ContextorGUI._sync_selected_live_repository_path(controller)
+        controller.repo_path_var.set(str(repo))
+        ContextorGUI._sync_selected_live_repository_path(controller)
+        ContextorGUI._sync_selected_live_repository_path(controller)
+        assert controller._live_recovery_queue.qsize() == 1
+        root.after(250, root.quit)
+        root.mainloop()
+        assert dialog_threads == [main_thread, main_thread]
+        assert controller._live_recovery_prompt_pending == set()
+        controller.analyze.assert_not_called()
+    finally:
+        controller._closing = True
+        root.destroy()
+
+
+def test_stale_recovery_queue_item_does_not_open_dialog(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    controller = _bind_recovery_prompt(_make_controller(repo, MockTkRoot()))
+    ask = MagicMock()
+    monkeypatch.setattr(gui.messagebox, "askyesno", ask)
+
+    ContextorGUI._request_full_analysis_recovery(
+        controller, str(repo), "Recovery required."
+    )
+    with controller._live_recovery_lock:
+        controller._live_recovery_incidents.pop(str(repo.resolve()))
+    ContextorGUI._drain_live_recovery_queue(controller)
+
+    ask.assert_not_called()
+    controller.analyze.assert_not_called()
+    assert controller._live_recovery_prompt_pending == set()
+    assert controller._live_recovery_incidents == {}
+
+
 def test_recovery_prompt_accept_runs_existing_analyze_once(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
     repo.mkdir()
ACTUAL_DIFF=the complete diff above.

# L37/L38 A3C T9 Tk recovery timer lifecycle fix

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\ui\gui.py`
- `C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py`
- HEAD before edits: `21db1dd4ef53e890317e386cdd20f25ab48cacd6`. No other source/test/documentation file changed. This `walkthrough.md` is the task report.

## T9_ROOT_CAUSE

- Contextor MCP was used first, including deferred discovery and current tool documentation. `get_symbol_implementation` returned complete `ContextorGUI.__init__` (`gui.py:99-162`), `_drain_live_recovery_queue` (`:1185-1259`) and `on_closing` (`:2131-2244`) with `workspace_sync=verified` at canonical revision 106. Git verified the exact anchors and focused test consumers before edits. (DIRECT_EVIDENCE / CODE_PATH_PROVED.)
- The initial recovery `root.after(100, ...)` and recurring recovery `root.after(100, ...)` were untracked. `on_closing` canceled the separate LIVE retry timer but had no recovery timer ID to cancel. The prior real-Tk audit found a pending Tcl `after` command at root destruction; processing the post-destroy Tcl queue emitted `invalid command name`. (CODE_PATH_PROVED plus prior DIRECT_EVIDENCE.)

## TIMER_LIFECYCLE_CHANGE

- `ContextorGUI.__init__` initializes `_live_recovery_after_id=None` and stores the first recovery timer ID.
- `_drain_live_recovery_queue` clears the executing callback's ID at entry and stores the next scheduled ID only when `_closing` is false. Incident, prompt, generation and certificate logic is unchanged.
- `on_closing` sets `_closing=True`, copies and clears the recovery timer ID, then cancels that timer before the existing long-running shutdown operations. Cancellation catches only `tk.TclError` and `RuntimeError`; a second shutdown has no recovery timer to cancel. The existing LIVE retry timer logic was not modified.
- IPC, watcher, durable storage, backend ownership and publication semantics were not edited. No Desktop/LIVE/MCP restart or manual `update_file` occurred.

## REAL_TK_TEST_EVIDENCE

- New focused test creates a real Tk root and `ContextorGUI(root)` with UI construction, backend startup and unrelated external shutdown side effects stubbed. It observes the initial stored recovery timer ID in Tcl `after info`, runs the actual Tk event loop, processes one controlled recovery dialog, then enters actual `on_closing` while the recurring recovery callback is pending. It confirms the recurring ID was present before shutdown, cleared by shutdown, and no timer remains in `after info` afterward. A post-destroy `root.tk.eval('update')` produced no `invalid command name` diagnostic under `capfd`; no callback/dialog ran after close; the recovery incident generation remained. (DIRECT_EVIDENCE / REAL_TK_EVENT_LOOP; the modal answer itself is controlled.)
- The first test run found an unrelated LIVE-status `after` callback left by `_set_live_status`, not the recovery callback. The test now stubs only that separate status timer chain and explicitly documents why, so the `after info` assertion attributes the absence of callbacks to the recovery timer under test. The corrected real-Tk test passed; the initial harness assertion failure is not presented as a production failure.
- A separate idempotence test invokes `on_closing` twice with a controlled root and verifies the recovery ID is canceled exactly once and remains `None`.

## T7_REGRESSION

- The existing real-Tk A → B → A decline/reselection regression passed. Decline still preserves the incident, clears prompt-pending state, and queues exactly one later prompt on reselection. Focused accept, worker-to-Tk handoff, stale queue, failure and switched-repository tests passed as listed below. The timer change did not modify watcher admission or generation matching.

## TARGETED_TEST_RESULTS

- First focused run: the new real-Tk test failed because an unrelated LIVE-status timer remained after root destruction; the recovery timer itself was canceled. The harness was narrowed to stub the unrelated `_set_live_status` timer.
- Corrected focused run: **7 passed** in 5.36 s (new real-Tk shutdown, cancellation idempotence, real-Tk T7, decline, accept, worker queue, closed Desktop).
- Adjacent focused run: **5 passed** in 2.88 s (stale queued dialog, failed analysis, dialog exception, repository switch, existing LIVE retry cancellation). Each run emitted one external Authlib deprecation warning. No full pytest suite was run.
- `git diff --check` passed. Contextor `get_live_events(after_revision=106)` returned `continuity=continuous`, `resync_required=false`, desktop_watcher updates for `gui.py` at revision 107 and `test_gui_live_startup.py` at revisions 108–109. This proves source-file LIVE observation; the already-running Desktop process has not been restarted and therefore its loaded Tk code is not certified by this event.

## FINAL_VERDICT

- **PASS for the focused T9 timer lifecycle contract in an isolated real-Tk event loop.** Pending recovery `after` IDs are tracked and canceled before root destruction; the tested post-destroy Tcl queue has no orphan recovery command. T7 and adjacent focused recovery behavior passed. Active Desktop loaded-code certification requires a separately authorized restart and is not claimed here.

## FULL_DIFFS

Complete actual Git diff for every changed source/test file follows:

diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index a42c539..2b1ebbd 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -141,6 +141,7 @@ class ContextorGUI:
         self.live_event_feeds = {}
         self._live_start_retry_attempt = 0
         self._live_start_retry_after_id = None
+        self._live_recovery_after_id = None
         self.live_status_var = tk.StringVar(value="LIVE: waiting for analysis")
         self.repo_id_var = tk.StringVar(value="Repo ID: unregistered")
         self._live_status_queue: Queue[str] = Queue()
@@ -159,7 +160,9 @@ class ContextorGUI:
         self._build_ui()
         self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
         self.root.after(50, self._start_post_paint_tasks)
-        self.root.after(100, self._drain_live_recovery_queue)
+        self._live_recovery_after_id = self.root.after(
+            100, self._drain_live_recovery_queue
+        )
 
     def _claim_current_backend_for_desktop(self):
         claim = claim_backend_owner(
@@ -1184,6 +1187,7 @@ class ContextorGUI:
 
     def _drain_live_recovery_queue(self) -> None:
         """Process recovery dialogs exclusively on the Tk event loop."""
+        self._live_recovery_after_id = None
         if getattr(self, "_closing", False):
             return
 
@@ -1254,7 +1258,7 @@ class ContextorGUI:
 
         finally:
             if not getattr(self, "_closing", False):
-                self.root.after(
+                self._live_recovery_after_id = self.root.after(
                     100, self._drain_live_recovery_queue
                 )
 
@@ -2133,6 +2137,17 @@ class ContextorGUI:
         import time
 
         self._closing = True
+        recovery_after_id = getattr(
+            self, "_live_recovery_after_id", None
+        )
+        self._live_recovery_after_id = None
+
+        if recovery_after_id is not None:
+            try:
+                self.root.after_cancel(recovery_after_id)
+            except (tk.TclError, RuntimeError):
+                pass
+
         close_cmd_log()
 
         # Route Desktop shutdown through the same cancellation path as Stop
diff --git a/tests/test_gui_live_startup.py b/tests/test_gui_live_startup.py
index c64d7e5..5d3975a 100644
--- a/tests/test_gui_live_startup.py
+++ b/tests/test_gui_live_startup.py
@@ -959,6 +959,94 @@ def test_recovery_decline_reprompts_once_after_reselection_with_real_tk(
         root.destroy()
 
 
+def test_recovery_timer_is_cancelled_before_real_tk_shutdown(
+    tmp_path, monkeypatch, capfd
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    try:
+        root = tk.Tk()
+    except tk.TclError as exc:
+        pytest.skip(f"Tk display unavailable: {exc}")
+    root.withdraw()
+    monkeypatch.setattr(gui, "load_state", lambda: {"repository": str(repo)})
+    monkeypatch.setattr(gui, "apply_theme", lambda *_args: None)
+    monkeypatch.setattr(ContextorGUI, "_build_ui", lambda _self: None)
+    monkeypatch.setattr(ContextorGUI, "_start_post_paint_tasks", lambda _self: None)
+    # LIVE status has its own after chain; isolate the recovery timer here.
+    monkeypatch.setattr(ContextorGUI, "_set_live_status", lambda *_args: None)
+    monkeypatch.setattr(gui, "close_cmd_log", lambda: None)
+    monkeypatch.setattr(gui, "terminate_active_process_pools", lambda **_kwargs: None)
+    monkeypatch.setattr(gui, "save_state", lambda **_kwargs: None)
+    dialogs = []
+    monkeypatch.setattr(
+        gui.messagebox,
+        "askyesno",
+        lambda *_args, **_kwargs: dialogs.append(threading.get_ident()) or False,
+    )
+
+    controller = ContextorGUI(root)
+    initial_id = controller._live_recovery_after_id
+    assert initial_id in root.tk.call("after", "info")
+    generation = controller._request_full_analysis_recovery(
+        str(repo), "Recovery required."
+    )
+    close_evidence = {}
+
+    def close_on_tk_thread():
+        pending_id = controller._live_recovery_after_id
+        close_evidence["pending_id"] = pending_id
+        close_evidence["pending_scripts"] = root.tk.call("after", "info")
+        close_evidence["dialogs_before"] = len(dialogs)
+        close_evidence["incident_before"] = controller._live_recovery_incident(
+            str(repo)
+        )
+        controller.on_closing()
+        close_evidence["id_after"] = controller._live_recovery_after_id
+
+    try:
+        root.after(130, close_on_tk_thread)
+        root.mainloop()
+        assert initial_id != close_evidence["pending_id"]
+        assert close_evidence["pending_id"] in close_evidence["pending_scripts"]
+        assert close_evidence["dialogs_before"] == 1
+        assert close_evidence["incident_before"]["generation"] == generation
+        assert close_evidence["id_after"] is None
+        assert root.tk.call("after", "info") == ""
+
+        root.tk.eval("update")
+        assert root.tk.call("after", "info") == ""
+        assert len(dialogs) == 1
+        assert controller._live_recovery_incident(str(repo))["generation"] == generation
+        output = capfd.readouterr()
+        assert "invalid command name" not in output.err
+        assert "invalid command name" not in output.out
+    finally:
+        controller._closing = True
+        try:
+            root.destroy()
+        except tk.TclError:
+            pass
+
+
+def test_recovery_timer_cancellation_is_idempotent(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    root = MockTkRoot()
+    controller = _make_controller(repo, root)
+    monkeypatch.setattr(gui, "close_cmd_log", lambda: None)
+    monkeypatch.setattr(gui, "terminate_active_process_pools", lambda **_kwargs: None)
+    monkeypatch.setattr(gui, "save_state", lambda **_kwargs: None)
+    recovery_id = root.after(100, lambda: None)
+    controller._live_recovery_after_id = recovery_id
+
+    ContextorGUI.on_closing(controller)
+    ContextorGUI.on_closing(controller)
+
+    assert root.cancelled.count(recovery_id) == 1
+    assert controller._live_recovery_after_id is None
+
+
 def test_stale_recovery_queue_item_does_not_open_dialog(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
     repo.mkdir()
ACTUAL_DIFF=the complete diff above.

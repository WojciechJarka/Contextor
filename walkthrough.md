# L37_L38_A3B_RECOVERY_PROMPT_HARDENING

## CURRENT_HEAD

- Repository: `C:\Temp\Contextor_Repo`; pre-edit/current HEAD: `ab06edf794d923afa119486a56c99ebe1d080d3e`.
- The worktree was clean before editing. Contextor MCP discovery preceded Git/source verification.
- `get_symbol_implementation` resolved the complete prior `ContextorGUI._request_full_analysis_recovery`, `__init__` and `_start_live_watcher_blocking` at LIVE revision 9 with `workspace_sync=verified`. `get_file_edit_context` reported 10 direct and 13 transitive module consumers for `contextor.ui.gui`; `get_artifact_blast_radius` found one confirmed cross-module static consumer of the recovery method in `tests.test_gui_live_startup`. These static counts do not exclude dynamic calls.
- All four production replacement anchors matched once before editing. Post-edit normalized `gui.py` equals HEAD plus exactly the supplied replacements; the equal-revision identity-conflict reason remains unchanged. `git diff --check` passed.

## QUEUE_THREAD_SAFETY

- `C:\Temp\Contextor_Repo\contextor\ui\gui.py:145-147`: `__init__` creates `Queue[tuple[str, str]]`, the pending-key set and `threading.Lock`. Line 157 schedules the first 100 ms drain from the Tk setup path.
- `ContextorGUI._request_full_analysis_recovery` at line 1075 canonicalizes the repository path, then uses only the lock, pending set and `Queue.put` to register one unresolved incident. It contains no `root.after` or `messagebox` call.
- `ContextorGUI._drain_live_recovery_queue` at line 1105 takes one queued incident with `get_nowait`, checks the current selected repository, opens `messagebox.askyesno` on the Tk event-loop path, and schedules the next drain at 100 ms unless closing.
- The worker-thread regression called the producer from a background thread. It observed one queued incident and zero Tk calls until the main thread invoked the drain. Both dialog and `root.after` ran on the main thread. Repeated same-repository conflicts queued one incident; declining left it pending and did not call `analyze()`. Only an affirmative mocked dialog called `analyze()` once. Closing and repository switching suppressed the stale dialog.

## ERROR_CLASSIFICATION

- `C:\Temp\Contextor_Repo\contextor\ui\gui.py:1514-1535` retains the attach-failure status but queues recovery only when `resync_required is True` or the response error is one of `canonical_persistence_revision_conflict`, `canonical_persistence_failed`, `canonical_revision_discontinuity`, `canonical_revision_changed_during_update`.
- The existing rejected-publication test now returns the supplied `canonical_revision_discontinuity` response and verifies the exact reason `Canonical LIVE consistency error: canonical_revision_discontinuity.`
- New negative cases for `non_monotonic_canonical_revision` and `daemon_busy` each recorded zero recovery incidents. A new positive case with `canonical_persistence_revision_conflict` and `resync_required=True` queued exactly one incident.
- The equal-revision mismatched-`state_id` branch still queues `Canonical state identity mismatch.` Ordinary connection retries queued no recovery incident.

## TARGETED_TEST_RESULTS

Project venv command: `& .\.venv\Scripts\python.exe -m pytest -q` with 17 explicitly selected GUI recovery/startup test nodes (19 parameterized cases). Result: `19 passed, 1 warning in 4.85s`, exit code 0. The warning was the external FastMCP/Authlib `AuthlibDeprecationWarning`.

Coverage included the adapted generation-conflict, decline, accept, closing, repository-switch, connection-retry and publication-rejection tests; the new worker-thread test; three classified-publication parameter cases; and eight directly related existing GUI startup/integration regressions. Fake `MockTkRoot` and mocked `messagebox` were used throughout the new cases. No real Tk window or full repository pytest suite was run.

## LIVE_WATCHER_VERIFICATION

- Before editing: canonical LIVE revision 9.
- `get_live_events(after_revision=9)` returned continuous revisions 10 and 11, `resync_required=false`: `desktop_watcher` `UPDATED` for `C:\Temp\Contextor_Repo\contextor\ui\gui.py` at 10 and `C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py` at 11.
- The GUI event reported deferred blast radius; the test event reported fresh blast radius. The returned syntax-diagnostics summary was fresh with zero errors. No manual `update_file` call or Desktop/LIVE restart was made.

## UNRESOLVED_RISKS

- Tests use fake Tk scheduling and fake LIVE publication responses. Real Desktop interaction and backend recovery after a restart were not exercised.
- `canonical_persistence_failed` and `canonical_revision_changed_during_update` are classified by the exact supplied source but did not receive separate targeted test cases.
- The running Desktop process may retain its previously imported GUI module until a later manual reload. No runtime integration certification is claimed.

## IMPLEMENTATION_VERDICT

`TARGETED_PASS`: exact production patch, focused GUI tests passing, worker-to-Tk separation demonstrated, and watcher updates observed. Runtime integration remains unverified.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\ui\gui.py`
- `C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py`

`walkthrough.md` is the required report and is excluded from the production/test changed-file list.

## FULL_DIFFS

Complete actual raw diff for every file in FILES_CHANGED:

```diff
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 02f94e8..c8ef77e 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -142,6 +142,9 @@ class ContextorGUI:
         self.repo_id_var = tk.StringVar(value="Repo ID: unregistered")
         self._live_status_queue: Queue[str] = Queue()
         self._live_status_draining = False
+        self._live_recovery_queue: Queue[tuple[str, str]] = Queue()
+        self._live_recovery_prompt_pending: set[str] = set()
+        self._live_recovery_lock = threading.Lock()
         self.last_live_state: dict[str, Any] | None = None
 
         self._closing = False
@@ -151,6 +154,7 @@ class ContextorGUI:
         self._build_ui()
         self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
         self.root.after(50, self._start_post_paint_tasks)
+        self.root.after(100, self._drain_live_recovery_queue)
 
     def _claim_current_backend_for_desktop(self):
         claim = claim_backend_owner(
@@ -1073,7 +1077,7 @@ class ContextorGUI:
         repository_path: str,
         reason: str,
     ) -> None:
-        """Offer manual FULL recovery after a confirmed LIVE consistency failure."""
+        """Queue a confirmed recovery incident without calling Tk."""
         if getattr(self, "_closing", False):
             return
 
@@ -1087,55 +1091,72 @@ class ContextorGUI:
         if not repository_key:
             return
 
-        pending = getattr(self, "_live_recovery_prompt_pending", None)
-        if pending is None:
-            pending = self._live_recovery_prompt_pending = set()
-
-        if repository_key in pending:
+        lock = getattr(self, "_live_recovery_lock", None)
+        if lock is None:
             return
 
-        pending.add(repository_key)
-
-        def show_prompt():
-            if getattr(self, "_closing", False):
-                pending.discard(repository_key)
+        with lock:
+            pending = self._live_recovery_prompt_pending
+            if repository_key in pending:
                 return
+            pending.add(repository_key)
+            self._live_recovery_queue.put((repository_key, reason))
+
+    def _drain_live_recovery_queue(self) -> None:
+        """Process recovery dialogs exclusively on the Tk event loop."""
+        if getattr(self, "_closing", False):
+            return
 
+        try:
+            repository_key, reason = (
+                self._live_recovery_queue.get_nowait()
+            )
+        except Empty:
+            pass
+        else:
             if not ContextorGUI._is_selected_live_repository(
-                self, repository_path
+                self, repository_key
             ):
-                pending.discard(repository_key)
-                return
-
-            try:
-                run_analysis = messagebox.askyesno(
-                    "Contextor — Recovery Required",
-                    (
-                        "A potential inconsistency has been detected "
-                        "in the repository's canonical LIVE state.\n\n"
-                        "A full repository analysis is recommended "
-                        "to restore a consistent architectural baseline.\n\n"
-                        "Incremental LIVE updates may be unreliable "
-                        "until recovery is complete.\n\n"
-                        f"Repository: {repository_key}\n\n"
-                        f"Reason: {reason}\n\n"
-                        "Run a full repository analysis now?"
-                    ),
-                    parent=self.root,
-                )
-            except Exception:
-                pending.discard(repository_key)
-                raise
+                with self._live_recovery_lock:
+                    self._live_recovery_prompt_pending.discard(
+                        repository_key
+                    )
+            else:
+                try:
+                    run_analysis = messagebox.askyesno(
+                        "Contextor — Recovery Required",
+                        (
+                            "A potential inconsistency has been detected "
+                            "in the repository's canonical LIVE state.\n\n"
+                            "A full repository analysis is recommended "
+                            "to restore a consistent architectural baseline.\n\n"
+                            "Incremental LIVE updates may be unreliable "
+                            "until recovery is complete.\n\n"
+                            f"Repository: {repository_key}\n\n"
+                            f"Reason: {reason}\n\n"
+                            "Run a full repository analysis now?"
+                        ),
+                        parent=self.root,
+                    )
+                except Exception:
+                    with self._live_recovery_lock:
+                        self._live_recovery_prompt_pending.discard(
+                            repository_key
+                        )
+                    raise
 
-            if run_analysis:
-                pending.discard(repository_key)
-                self.analyze()
+                if run_analysis:
+                    with self._live_recovery_lock:
+                        self._live_recovery_prompt_pending.discard(
+                            repository_key
+                        )
+                    self.analyze()
 
-        try:
-            self.root.after(0, show_prompt)
-        except Exception:
-            pending.discard(repository_key)
-            raise
+        finally:
+            if not getattr(self, "_closing", False):
+                self.root.after(
+                    100, self._drain_live_recovery_queue
+                )
 
     def analyze(self):
         path = self.repo_path_var.get()
@@ -1493,10 +1514,26 @@ class ContextorGUI:
                             self._set_live_status(
                                 "LIVE: shared state attach failed; analysis required"
                             )
-                            self._request_full_analysis_recovery(
-                                path,
-                                "Canonical LIVE publication was rejected.",
+                            recovery_errors = frozenset({
+                                "canonical_persistence_revision_conflict",
+                                "canonical_persistence_failed",
+                                "canonical_revision_discontinuity",
+                                "canonical_revision_changed_during_update",
+                            })
+                            error_code = (
+                                published.get("error")
+                                if isinstance(published, dict)
+                                else None
                             )
+                            if (
+                                published.get("resync_required") is True
+                                if isinstance(published, dict)
+                                else False
+                            ) or error_code in recovery_errors:
+                                self._request_full_analysis_recovery(
+                                    path,
+                                    f"Canonical LIVE consistency error: {error_code or 'resync_required'}.",
+                                )
         else:
             if ContextorGUI._is_selected_live_repository(self, path):
                 self._set_live_status("LIVE: no snapshot; waiting for analysis")
diff --git a/tests/test_gui_live_startup.py b/tests/test_gui_live_startup.py
index 7ea55b8..e00be11 100644
--- a/tests/test_gui_live_startup.py
+++ b/tests/test_gui_live_startup.py
@@ -1,5 +1,6 @@
 """Tests for Desktop GUI LIVE startup retry hardening."""
 
+from queue import Queue
 from types import SimpleNamespace
 from unittest.mock import MagicMock
 import threading
@@ -601,11 +602,17 @@ def test_shutdown_cancels_pending_retry(tmp_path, monkeypatch):
 
 def _bind_recovery_prompt(controller):
     controller.analyze = MagicMock()
+    controller._live_recovery_queue = Queue()
+    controller._live_recovery_prompt_pending = set()
+    controller._live_recovery_lock = threading.Lock()
     controller._request_full_analysis_recovery = (
         lambda path, reason: ContextorGUI._request_full_analysis_recovery(
             controller, path, reason
         )
     )
+    controller._drain_live_recovery_queue = (
+        lambda: ContextorGUI._drain_live_recovery_queue(controller)
+    )
     return controller
 
 
@@ -640,8 +647,8 @@ def test_generation_conflict_schedules_one_recovery_prompt(tmp_path, monkeypatch
     assert controller._statuses.count(
         "LIVE: generation conflict; analysis required"
     ) == 2
-    assert len(root.scheduled) == 1
-    assert next(iter(root.scheduled.values()))[0] == 0
+    assert controller._live_recovery_queue.qsize() == 1
+    assert root.scheduled == {}
     assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
     ask.assert_not_called()
     controller.analyze.assert_not_called()
@@ -658,7 +665,8 @@ def test_recovery_prompt_decline_preserves_incident(tmp_path, monkeypatch):
     ContextorGUI._request_full_analysis_recovery(
         controller, str(repo), "Canonical state identity mismatch."
     )
-    assert root.run_next_scheduled() is True
+    assert controller._live_recovery_queue.qsize() == 1
+    ContextorGUI._drain_live_recovery_queue(controller)
 
     ask.assert_called_once()
     assert ask.call_args.kwargs["parent"] is root
@@ -669,7 +677,8 @@ def test_recovery_prompt_decline_preserves_incident(tmp_path, monkeypatch):
     ContextorGUI._request_full_analysis_recovery(
         controller, str(repo), "Canonical state identity mismatch."
     )
-    assert root.scheduled == {}
+    assert controller._live_recovery_queue.qsize() == 0
+    assert next(iter(root.scheduled.values()))[0] == 100
     ask.assert_called_once()
 
 
@@ -684,11 +693,14 @@ def test_recovery_prompt_accept_runs_existing_analyze_once(tmp_path, monkeypatch
     ContextorGUI._request_full_analysis_recovery(
         controller, str(repo), "Canonical state identity mismatch."
     )
-    assert root.run_next_scheduled() is True
+    assert controller._live_recovery_queue.qsize() == 1
+    ContextorGUI._drain_live_recovery_queue(controller)
 
     ask.assert_called_once()
     controller.analyze.assert_called_once_with()
     assert controller._live_recovery_prompt_pending == set()
+    assert controller._live_recovery_queue.qsize() == 0
+    assert next(iter(root.scheduled.values()))[0] == 100
 
 
 def test_recovery_prompt_suppressed_after_desktop_closes(tmp_path, monkeypatch):
@@ -703,11 +715,14 @@ def test_recovery_prompt_suppressed_after_desktop_closes(tmp_path, monkeypatch):
         controller, str(repo), "Canonical state identity mismatch."
     )
     controller._closing = True
-    assert root.run_next_scheduled() is True
+    assert controller._live_recovery_queue.qsize() == 1
+    ContextorGUI._drain_live_recovery_queue(controller)
 
     ask.assert_not_called()
     controller.analyze.assert_not_called()
-    assert controller._live_recovery_prompt_pending == set()
+    assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
+    assert controller._live_recovery_queue.qsize() == 1
+    assert root.scheduled == {}
 
 
 def test_recovery_prompt_suppressed_after_repository_switch(tmp_path, monkeypatch):
@@ -724,11 +739,14 @@ def test_recovery_prompt_suppressed_after_repository_switch(tmp_path, monkeypatc
         controller, str(repo), "Canonical state identity mismatch."
     )
     controller._selected_live_repo_path = str(other)
-    assert root.run_next_scheduled() is True
+    assert controller._live_recovery_queue.qsize() == 1
+    ContextorGUI._drain_live_recovery_queue(controller)
 
     ask.assert_not_called()
     controller.analyze.assert_not_called()
     assert controller._live_recovery_prompt_pending == set()
+    assert controller._live_recovery_queue.qsize() == 0
+    assert next(iter(root.scheduled.values()))[0] == 100
 
 
 def test_live_connection_retry_does_not_prompt_for_recovery(tmp_path, monkeypatch):
@@ -749,7 +767,8 @@ def test_live_connection_retry_does_not_prompt_for_recovery(tmp_path, monkeypatc
     assert controller._live_start_retry_attempt == 1
     assert len(root.scheduled) == 1
     assert next(iter(root.scheduled.values()))[0] == LIVE_START_RETRY_DELAYS_MS[0]
-    assert not hasattr(controller, "_live_recovery_prompt_pending")
+    assert controller._live_recovery_prompt_pending == set()
+    assert controller._live_recovery_queue.qsize() == 0
     ask.assert_not_called()
     controller.analyze.assert_not_called()
 
@@ -770,7 +789,12 @@ def test_rejected_startup_publication_schedules_recovery_prompt(tmp_path, monkey
             return {"state": remote, "revision": 6}
 
         def publish(self, *_args, **_kwargs):
-            return {"status": "rejected"}
+            return {
+                "status": "error",
+                "error": "canonical_revision_discontinuity",
+                "revision": 6,
+                "expected_revision": 7,
+            }
 
     class Watcher:
         def __init__(self, *_args, **_kwargs):
@@ -802,8 +826,141 @@ def test_rejected_startup_publication_schedules_recovery_prompt(tmp_path, monkey
 
     assert released and len(released) == 1
     assert "LIVE: shared state attach failed; analysis required" in controller._statuses
-    assert len(root.scheduled) == 1
-    assert next(iter(root.scheduled.values()))[0] == 0
-    assert root.run_next_scheduled() is True
-    assert "Canonical LIVE publication was rejected." in ask.call_args.args[1]
+    assert controller._live_recovery_queue.qsize() == 1
+    assert root.scheduled == {}
+    ContextorGUI._drain_live_recovery_queue(controller)
+    assert ask.call_args.args[1].endswith(
+        "Reason: Canonical LIVE consistency error: canonical_revision_discontinuity.\n\n"
+        "Run a full repository analysis now?"
+    )
+    assert next(iter(root.scheduled.values()))[0] == 100
+    controller.analyze.assert_not_called()
+
+
+
+def test_recovery_request_from_worker_uses_queue_without_tk(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    root = MockTkRoot()
+    controller = _bind_recovery_prompt(_make_controller(repo, root))
+    main_thread = threading.get_ident()
+    original_after = root.after
+    after_threads = []
+    dialog_threads = []
+
+    def checked_after(delay_ms, callback):
+        after_threads.append(threading.get_ident())
+        assert threading.get_ident() == main_thread
+        return original_after(delay_ms, callback)
+
+    def checked_dialog(*_args, **_kwargs):
+        dialog_threads.append(threading.get_ident())
+        assert threading.get_ident() == main_thread
+        return False
+
+    root.after = checked_after
+    monkeypatch.setattr(gui.messagebox, "askyesno", checked_dialog)
+    worker = threading.Thread(
+        target=ContextorGUI._request_full_analysis_recovery,
+        args=(controller, str(repo), "Canonical state identity mismatch."),
+    )
+    worker.start()
+    worker.join(5)
+
+    assert not worker.is_alive()
+    assert controller._live_recovery_queue.qsize() == 1
+    assert root.scheduled == {}
+    assert after_threads == []
+    assert dialog_threads == []
+
+    ContextorGUI._drain_live_recovery_queue(controller)
+    assert dialog_threads == [main_thread]
+    assert after_threads == [main_thread]
+    assert next(iter(root.scheduled.values()))[0] == 100
+    controller.analyze.assert_not_called()
+
+
+@pytest.mark.parametrize(
+    ("response", "expected_reason"),
+    [
+        (
+            {"status": "error", "error": "non_monotonic_canonical_revision"},
+            None,
+        ),
+        (
+            {"status": "error", "error": "daemon_busy"},
+            None,
+        ),
+        (
+            {
+                "status": "error",
+                "error": "canonical_persistence_revision_conflict",
+                "resync_required": True,
+            },
+            "Canonical LIVE consistency error: canonical_persistence_revision_conflict.",
+        ),
+    ],
+)
+def test_startup_publication_error_recovery_classification(
+    tmp_path, monkeypatch, response, expected_reason
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    root = MockTkRoot()
+    controller = _bind_recovery_prompt(_make_controller(repo, root))
+    loaded = SimpleNamespace(revision=7, state_id="loaded-generation")
+    remote = SimpleNamespace(revision=6, state_id="remote-generation")
+    ask = MagicMock(return_value=False)
+    released = []
+
+    class Client:
+        def snapshot(self):
+            return {"state": remote, "revision": 6}
+
+        def publish(self, *_args, **_kwargs):
+            return response
+
+    class Watcher:
+        def __init__(self, *_args, **_kwargs):
+            pass
+
+        def start(self):
+            pass
+
+    class Feed:
+        def __init__(self, *_args, **_kwargs):
+            pass
+
+        def start(self):
+            pass
+
+    monkeypatch.setattr(gui, "connect_or_start", lambda *_a, **_k: Client())
+    monkeypatch.setattr(gui, "migrate_legacy_snapshot", lambda *_a: tmp_path / "cache")
+    monkeypatch.setattr(gui, "acquire_full_analysis", lambda *_a, **_k: object())
+    monkeypatch.setattr(gui, "release_full_analysis", released.append)
+    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
+    monkeypatch.setattr(gui, "DesktopLiveEventFeed", Feed)
+    monkeypatch.setattr(gui.messagebox, "askyesno", ask)
+    monkeypatch.setattr(
+        "contextor.core.analysis.state_manager.load_engine_state",
+        lambda *_a, **_k: loaded,
+    )
+
+    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
+
+    assert len(released) == 1
+    assert "LIVE: shared state attach failed; analysis required" in controller._statuses
+    if expected_reason is None:
+        assert controller._live_recovery_queue.qsize() == 0
+        assert controller._live_recovery_prompt_pending == set()
+        assert root.scheduled == {}
+        ask.assert_not_called()
+    else:
+        assert controller._live_recovery_queue.qsize() == 1
+        assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
+        assert root.scheduled == {}
+        ContextorGUI._drain_live_recovery_queue(controller)
+        assert expected_reason in ask.call_args.args[1]
+        assert next(iter(root.scheduled.values()))[0] == 100
     controller.analyze.assert_not_called()
```

## ACTUAL_DIFF

The complete actual diff is reproduced verbatim in FULL_DIFFS.

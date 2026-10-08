# L37_L38_A3_DESKTOP_RECOVERY_PROMPT

## CURRENT_HEAD

- Repository: `C:\Temp\Contextor_Repo`.
- Pre-edit/current HEAD: `7bf1944b4c77a9313525ce57a390858ce5705d1b`; the worktree was clean before this task.
- Contextor MCP was used first. `get_file_edit_context` resolved `contextor.ui.gui` at LIVE revision 6 with fresh syntax diagnostics, 10 direct module consumers and 13 transitive consumers. Complete implementations of `ContextorGUI._start_live_watcher_blocking`, `analyze`, and `_is_selected_live_repository` were fetched with `workspace_sync=verified`.
- Literal source verification: both requested branch anchors matched once before editing; `def analyze(self)` matched once. After editing, normalized `contextor/ui/gui.py` equals HEAD plus exactly the supplied method insertion and two branch replacements. `git diff --check` passed.

## IMPLEMENTATION_EVIDENCE

- `C:\Temp\Contextor_Repo\contextor\ui\gui.py:1071`: supplied `_request_full_analysis_recovery` schedules `messagebox.askyesno` via `root.after(0, ...)`, deduplicates by canonical repository path, and calls the existing `analyze()` only after an affirmative answer. A decline leaves the incident in the pending set.
- `C:\Temp\Contextor_Repo\contextor\ui\gui.py:1450-1459`: the confirmed same-revision generation identity mismatch calls that method with `Canonical state identity mismatch.`
- `C:\Temp\Contextor_Repo\contextor\ui\gui.py:1493-1499`: rejected startup publication calls it with `Canonical LIVE publication was rejected.`
- The connection-retry, writer-busy, no-snapshot and normal watcher paths were not changed. No status-text parsing or automatic FULL analysis was added.
- The two existing generation-conflict fakes in `tests/test_live_desktop_integration.py` now provide the newly invoked callback and assert its exact call. Existing successful-publication fakes now return the `{"status": "ok"}` response already required by `_start_live_watcher_blocking`.

## TARGETED_TEST_RESULTS

Command: project-venv `python -m pytest -q` with 15 explicit GUI test nodes. Result: `15 passed, 1 warning in 6.63s`, exit code 0. The warning was an external `AuthlibDeprecationWarning` from FastMCP/Authlib. No full suite was run.

New tests in `C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py`:

1. `test_generation_conflict_schedules_one_recovery_prompt`: confirmed conflict schedules exactly one zero-delay callback despite repeated conflict.
2. `test_recovery_prompt_decline_preserves_incident`: decline never calls `analyze()` and retains deduplication.
3. `test_recovery_prompt_accept_runs_existing_analyze_once`: affirmative answer invokes `analyze()` once.
4. `test_recovery_prompt_suppressed_after_desktop_closes`: closing before callback suppresses dialog and analysis.
5. `test_recovery_prompt_suppressed_after_repository_switch`: changed selection suppresses stale dialog and analysis.
6. `test_live_connection_retry_does_not_prompt_for_recovery`: transient connection failure schedules only the normal retry timer.
7. `test_rejected_startup_publication_schedules_recovery_prompt`: rejected publication schedules the prompt with the exact reason.

Existing focused regressions also passed: `test_same_revision_different_state_id_does_not_attach_as_same_generation`, `test_same_revision_missing_state_id_does_not_start_live_components`, `test_desktop_publishes_latest_snapshot_and_replaces_existing_watcher`, `test_switching_repositories_keeps_previous_watcher_active`, `test_initial_success`, `test_timeout_then_success`, `test_late_service_connection`, and `test_desktop_skips_cache_publish_when_canonical_writer_is_busy_but_starts_watcher`.

All new GUI tests used `MockTkRoot.after` and mocked `messagebox.askyesno`; no real Tk window was opened.

## LIVE_WATCHER_VERIFICATION

- Before edits: latest canonical revision 6.
- After edits: `get_live_events(after_revision=6)` returned continuous revisions 7, 8, 9 with `resync_required=false`. Each was a `desktop_watcher` `update_file` event with `status=UPDATED`: `gui.py` at 7, `test_gui_live_startup.py` at 8, and `test_live_desktop_integration.py` at 9.
- The events reported `blast_radius_state=deferred`; the returned syntax-diagnostics summary was fresh with zero errors. No manual `update_file` call was made.

## UNRESOLVED_RISKS

- The focused tests mock the dialog, root scheduler, and publication responses. They do not certify a real Desktop dialog or a running LIVE backend recovery cycle.
- The running Desktop process was not restarted, so integration certification of this newly edited GUI code requires a later Desktop reload. No MCP or LIVE restart was performed in this task.

## IMPLEMENTATION_VERDICT

`TARGETED_PASS`: the supplied production patch matches literally, all 15 focused GUI regressions passed, and the LIVE watcher recorded all three changed files. Runtime integration remains unverified.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\ui\gui.py`
- `C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py`
- `C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py`

`walkthrough.md` is the required report and is excluded from this production/test changed-file list.

## FULL_DIFFS

Complete raw actual diff for every file in FILES_CHANGED:

```diff
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 96634ed..02f94e8 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -1068,6 +1068,75 @@ class ContextorGUI:
 
         self._run_test_suite()
 
+    def _request_full_analysis_recovery(
+        self,
+        repository_path: str,
+        reason: str,
+    ) -> None:
+        """Offer manual FULL recovery after a confirmed LIVE consistency failure."""
+        if getattr(self, "_closing", False):
+            return
+
+        try:
+            repository_key = str(
+                Path(repository_path).expanduser().resolve()
+            )
+        except (OSError, ValueError):
+            repository_key = str(repository_path)
+
+        if not repository_key:
+            return
+
+        pending = getattr(self, "_live_recovery_prompt_pending", None)
+        if pending is None:
+            pending = self._live_recovery_prompt_pending = set()
+
+        if repository_key in pending:
+            return
+
+        pending.add(repository_key)
+
+        def show_prompt():
+            if getattr(self, "_closing", False):
+                pending.discard(repository_key)
+                return
+
+            if not ContextorGUI._is_selected_live_repository(
+                self, repository_path
+            ):
+                pending.discard(repository_key)
+                return
+
+            try:
+                run_analysis = messagebox.askyesno(
+                    "Contextor — Recovery Required",
+                    (
+                        "A potential inconsistency has been detected "
+                        "in the repository's canonical LIVE state.\n\n"
+                        "A full repository analysis is recommended "
+                        "to restore a consistent architectural baseline.\n\n"
+                        "Incremental LIVE updates may be unreliable "
+                        "until recovery is complete.\n\n"
+                        f"Repository: {repository_key}\n\n"
+                        f"Reason: {reason}\n\n"
+                        "Run a full repository analysis now?"
+                    ),
+                    parent=self.root,
+                )
+            except Exception:
+                pending.discard(repository_key)
+                raise
+
+            if run_analysis:
+                pending.discard(repository_key)
+                self.analyze()
+
+        try:
+            self.root.after(0, show_prompt)
+        except Exception:
+            pending.discard(repository_key)
+            raise
+
     def analyze(self):
         path = self.repo_path_var.get()
         if not path:
@@ -1380,7 +1449,13 @@ class ContextorGUI:
                         self._set_live_status("LIVE: shared state attached; watcher active")
                 else:
                     if ContextorGUI._is_selected_live_repository(self, path):
-                        self._set_live_status("LIVE: generation conflict; analysis required")
+                        self._set_live_status(
+                            "LIVE: generation conflict; analysis required"
+                        )
+                        self._request_full_analysis_recovery(
+                            path,
+                            "Canonical state identity mismatch.",
+                        )
                     return
             else:
                 startup_lease = None
@@ -1418,6 +1493,10 @@ class ContextorGUI:
                             self._set_live_status(
                                 "LIVE: shared state attach failed; analysis required"
                             )
+                            self._request_full_analysis_recovery(
+                                path,
+                                "Canonical LIVE publication was rejected.",
+                            )
         else:
             if ContextorGUI._is_selected_live_repository(self, path):
                 self._set_live_status("LIVE: no snapshot; waiting for analysis")
diff --git a/tests/test_gui_live_startup.py b/tests/test_gui_live_startup.py
index d724a27..7ea55b8 100644
--- a/tests/test_gui_live_startup.py
+++ b/tests/test_gui_live_startup.py
@@ -234,7 +234,7 @@ def test_initial_success(tmp_path, monkeypatch):
 
     class Client:
         def publish(self, state, *, origin="unknown"):
-            pass
+            return {"status": "ok"}
 
     watcher_instances = []
 
@@ -328,7 +328,7 @@ def test_timeout_then_success(tmp_path, monkeypatch):
 
     class Client:
         def publish(self, state, *, origin="unknown"):
-            pass
+            return {"status": "ok"}
 
     watcher_instances = []
 
@@ -403,7 +403,7 @@ def test_late_service_connection(tmp_path, monkeypatch):
 
     class Client:
         def publish(self, state, *, origin="unknown"):
-            pass
+            return {"status": "ok"}
 
     def mock_connect_or_start(path, *, owner_pid=None, owner_token=None):
         connect_calls.append((path, owner_pid, owner_token))
@@ -596,3 +596,214 @@ def test_shutdown_cancels_pending_retry(tmp_path, monkeypatch):
     assert controller._live_start_retry_after_id is None
     assert controller._live_start_retry_attempt == 0
     assert root.destroyed is True
+
+
+
+def _bind_recovery_prompt(controller):
+    controller.analyze = MagicMock()
+    controller._request_full_analysis_recovery = (
+        lambda path, reason: ContextorGUI._request_full_analysis_recovery(
+            controller, path, reason
+        )
+    )
+    return controller
+
+
+def test_generation_conflict_schedules_one_recovery_prompt(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    root = MockTkRoot()
+    controller = _bind_recovery_prompt(_make_controller(repo, root))
+    loaded = SimpleNamespace(revision=7, state_id="loaded-generation")
+    remote = SimpleNamespace(revision=7, state_id="remote-generation")
+    ask = MagicMock(return_value=False)
+
+    class Client:
+        def snapshot(self):
+            return {"state": remote, "revision": 7}
+
+        def publish(self, *_args, **_kwargs):
+            raise AssertionError("generation conflict must not publish")
+
+    monkeypatch.setattr(gui, "connect_or_start", lambda *_a, **_k: Client())
+    monkeypatch.setattr(gui, "migrate_legacy_snapshot", lambda *_a: tmp_path / "cache")
+    monkeypatch.setattr(
+        "contextor.core.analysis.state_manager.load_engine_state",
+        lambda *_a, **_k: loaded,
+    )
+    monkeypatch.setattr(gui.messagebox, "askyesno", ask)
+
+    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
+    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
+
+    assert controller._statuses.count(
+        "LIVE: generation conflict; analysis required"
+    ) == 2
+    assert len(root.scheduled) == 1
+    assert next(iter(root.scheduled.values()))[0] == 0
+    assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
+    ask.assert_not_called()
+    controller.analyze.assert_not_called()
+
+
+def test_recovery_prompt_decline_preserves_incident(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    root = MockTkRoot()
+    controller = _bind_recovery_prompt(_make_controller(repo, root))
+    ask = MagicMock(return_value=False)
+    monkeypatch.setattr(gui.messagebox, "askyesno", ask)
+
+    ContextorGUI._request_full_analysis_recovery(
+        controller, str(repo), "Canonical state identity mismatch."
+    )
+    assert root.run_next_scheduled() is True
+
+    ask.assert_called_once()
+    assert ask.call_args.kwargs["parent"] is root
+    assert "Canonical state identity mismatch." in ask.call_args.args[1]
+    controller.analyze.assert_not_called()
+    assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
+
+    ContextorGUI._request_full_analysis_recovery(
+        controller, str(repo), "Canonical state identity mismatch."
+    )
+    assert root.scheduled == {}
+    ask.assert_called_once()
+
+
+def test_recovery_prompt_accept_runs_existing_analyze_once(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    root = MockTkRoot()
+    controller = _bind_recovery_prompt(_make_controller(repo, root))
+    ask = MagicMock(return_value=True)
+    monkeypatch.setattr(gui.messagebox, "askyesno", ask)
+
+    ContextorGUI._request_full_analysis_recovery(
+        controller, str(repo), "Canonical state identity mismatch."
+    )
+    assert root.run_next_scheduled() is True
+
+    ask.assert_called_once()
+    controller.analyze.assert_called_once_with()
+    assert controller._live_recovery_prompt_pending == set()
+
+
+def test_recovery_prompt_suppressed_after_desktop_closes(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    root = MockTkRoot()
+    controller = _bind_recovery_prompt(_make_controller(repo, root))
+    ask = MagicMock()
+    monkeypatch.setattr(gui.messagebox, "askyesno", ask)
+
+    ContextorGUI._request_full_analysis_recovery(
+        controller, str(repo), "Canonical state identity mismatch."
+    )
+    controller._closing = True
+    assert root.run_next_scheduled() is True
+
+    ask.assert_not_called()
+    controller.analyze.assert_not_called()
+    assert controller._live_recovery_prompt_pending == set()
+
+
+def test_recovery_prompt_suppressed_after_repository_switch(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    other = tmp_path / "other"
+    repo.mkdir()
+    other.mkdir()
+    root = MockTkRoot()
+    controller = _bind_recovery_prompt(_make_controller(repo, root))
+    ask = MagicMock()
+    monkeypatch.setattr(gui.messagebox, "askyesno", ask)
+
+    ContextorGUI._request_full_analysis_recovery(
+        controller, str(repo), "Canonical state identity mismatch."
+    )
+    controller._selected_live_repo_path = str(other)
+    assert root.run_next_scheduled() is True
+
+    ask.assert_not_called()
+    controller.analyze.assert_not_called()
+    assert controller._live_recovery_prompt_pending == set()
+
+
+def test_live_connection_retry_does_not_prompt_for_recovery(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    root = MockTkRoot()
+    controller = _bind_recovery_prompt(_make_controller(repo, root))
+    ask = MagicMock()
+    monkeypatch.setattr(gui.messagebox, "askyesno", ask)
+    monkeypatch.setattr(
+        gui, "connect_or_start",
+        lambda *_a, **_k: (_ for _ in ()).throw(TimeoutError("transient")),
+    )
+
+    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
+
+    assert controller._live_start_retry_attempt == 1
+    assert len(root.scheduled) == 1
+    assert next(iter(root.scheduled.values()))[0] == LIVE_START_RETRY_DELAYS_MS[0]
+    assert not hasattr(controller, "_live_recovery_prompt_pending")
+    ask.assert_not_called()
+    controller.analyze.assert_not_called()
+
+
+def test_rejected_startup_publication_schedules_recovery_prompt(tmp_path, monkeypatch):
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
+            return {"status": "rejected"}
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
+    assert released and len(released) == 1
+    assert "LIVE: shared state attach failed; analysis required" in controller._statuses
+    assert len(root.scheduled) == 1
+    assert next(iter(root.scheduled.values()))[0] == 0
+    assert root.run_next_scheduled() is True
+    assert "Canonical LIVE publication was rejected." in ask.call_args.args[1]
+    controller.analyze.assert_not_called()
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index 05487f7..524364d 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -181,6 +181,7 @@ def test_same_revision_different_state_id_does_not_attach_as_same_generation(tmp
     controller = SimpleNamespace(
         live_watcher=None, live_event_feed=None, live_watchers={},
         live_event_feeds={}, repo_id_var=_LiveIntegrationFakeVar(),
+        _request_full_analysis_recovery=MagicMock(),
         _set_live_status=statuses.append,
     )
     monkeypatch.setattr(gui, "connect_or_start", lambda *_args, **_kwargs: Client())
@@ -195,6 +196,7 @@ def test_same_revision_different_state_id_does_not_attach_as_same_generation(tmp
 
     assert events == []
     assert "LIVE: generation conflict; analysis required" in statuses
+    controller._request_full_analysis_recovery.assert_called_once_with(str(repo), "Canonical state identity mismatch.")
     assert watcher_starts == []
     assert feed_starts == []
 
@@ -227,6 +229,7 @@ def test_same_revision_missing_state_id_does_not_start_live_components(tmp_path,
     controller = SimpleNamespace(
         live_watcher=None, live_event_feed=None, live_watchers={},
         live_event_feeds={}, repo_id_var=_LiveIntegrationFakeVar(),
+        _request_full_analysis_recovery=MagicMock(),
         _set_live_status=statuses.append,
     )
     monkeypatch.setattr(gui, "connect_or_start", lambda *_args, **_kwargs: Client())
@@ -240,6 +243,7 @@ def test_same_revision_missing_state_id_does_not_start_live_components(tmp_path,
     gui.ContextorGUI._start_live_watcher_blocking(controller, str(repo))
 
     assert "LIVE: generation conflict; analysis required" in statuses
+    controller._request_full_analysis_recovery.assert_called_once_with(str(repo), "Canonical state identity mismatch.")
     assert watcher_starts == []
     assert feed_starts == []
 
@@ -256,6 +260,7 @@ def test_desktop_publishes_latest_snapshot_and_replaces_existing_watcher(
     class Client:
         def publish(self, published, *, origin="unknown"):
             events.append(("publish", published, origin))
+            return {"status": "ok"}
 
     class Watcher:
         def __init__(self, root, client, *, on_status=None, **_kwargs):
@@ -466,6 +471,7 @@ def test_switching_repositories_keeps_previous_watcher_active(tmp_path, monkeypa
     class Client:
         def publish(self, _state, *, origin="unknown"):
             events.append(("publish", origin))
+            return {"status": "ok"}
 
     class Watcher:
         def __init__(self, root, _client, *, on_status=None, **_kwargs):
```

## ACTUAL_DIFF

The complete actual diff is reproduced verbatim in FULL_DIFFS.

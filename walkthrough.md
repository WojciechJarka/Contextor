# L37_L38_A3C_RECOVERY_LIFECYCLE_AND_WATCHER_SAFETY

## CURRENT_HEAD

DIRECT_EVIDENCE: `124afbafa549a88591b93aa3042ac1dfe5a73f28`; pre-edit `git status --short` was empty.

## PRE_EDIT_CONTEXTOR_EVIDENCE

Deferred Contextor MCP tools were actively discovered. Documentation was read before using `get_symbol_implementation`, `get_symbol_call_context`, `get_symbol_lineage`, `get_artifact_blast_radius`, `get_source_range`, and `get_live_events`. Complete implementations were retrieved for `DesktopLiveWatcher.__init__` (C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:107-151), `poll_once` (640-867), `_poll_inflight_updates` (570-638), `_requeue_paths` (447-449), `start` (256-274), `stop` (300-322), `ContextorGUI._start_live_watcher_blocking` (C:\Temp\Contextor_Repo\contextor\ui\gui.py:1352-1621), `analyze` (1161-1211), `_drain_live_recovery_queue` (1105-1159), `read_metadata` (C:\Temp\Contextor_Repo\contextor\core\live_state\store.py:1410-1441), `save_snapshot` (1506-1873), and full `load_snapshot` (1904-2311, with large-output source range). Contextor call context and blast radius were queried; static consumer output does not cover dynamic callers. PRE_EDIT LIVE revision=11.

## PHASE_1_IMPLEMENTATION

CODE_PATH_PROVED: The specified exact block at C:\Temp\Contextor_Repo\contextor\ui\gui.py:1148-1153 matched HEAD and was replaced literally with `if run_analysis: self.analyze()`. Acceptance now retains the repository key in `_live_recovery_prompt_pending`. Tests at C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py:685-735 cover acceptance, deduplication after acceptance, and `analyze` failure. Existing decline and non-confirmation tests remain.

## PHASE_2_ARCHITECTURAL_EVIDENCE

- A UNKNOWN as a current contract: watcher constructor has callback inputs but no recovery predicate (watcher.py:107-151). GUI creates watcher at gui.py:1583-1592 and owns a lock-protected recovery set at 1075-1103. Thread-safe predicate wiring is absent.
- B CODE_PATH_PROVED for order: inflight polling precedes pending drain (watcher.py:640-642); sole watcher mutation submission is 827-832. UNKNOWN for an atomic future guard against an incident activated mid-poll.
- C CODE_PATH_PROVED: event path enqueue is lock protected (watcher.py:420-430); pending drain clears paths (432-438); startup paths are consumed at 643-645 and cleared again at 866. A gate before drain would retain them. No gate exists.
- D CODE_PATH_PROVED: mutation-status reconciliation at watcher.py:570-638 retains running jobs, updates completed jobs and requeues failures. Worker polls while paths or jobs exist (276-298). `stop` terminates the worker (300-322).
- E UNKNOWN for full certification: `analyze` calls `run_full_analysis_exclusive`, then starts watcher and displays UI results without comparing durable/LIVE identities (gui.py:1176-1211). Full-analysis lease is released in `finally` (full_analysis_coordinator.py:625-682). `save_snapshot` commits metadata and releases store lock (store.py:1835-1873); `load_snapshot` validates repo/root and embedded revision/state_id (1904-1935, 2083-2094); `LiveStateClient.snapshot` reads LIVE via IPC (ipc.py:1860-1861). No protected joint comparison exists in the inspected GUI completion path.
- F UNKNOWN: recovery lock (gui.py:1094-1103), watcher pending lock (watcher.py:420-438), store lock (store.py:1541-1543,1873), and full-analysis admission (full_analysis_coordinator.py:625-632) exist, but a recovery predicate/certification section is not implemented. No future lock ordering can be certified.

## WATCHER_SAFE_INSERTION_POINTS

CODE_PATH_PROVED anchors only: watcher.py:641 reconciles inflight jobs, 642 drains changes, 827-832 submits. A suspension before drain would preserve pending paths while allowing status polling. A check adjacent to submission would address an incident activated later in the poll, subject to unproven synchronization. No watcher change was made. Existing startup `on_resync` invokes FULL automatically at gui.py:1573-1579 and watcher.py:669-697; this pre-existing path blocks certification of the broad no-automatic-FULL objective.

## INFLIGHT_JOB_SAFETY

CODE_PATH_PROVED: watcher.py:570-612 polls existing jobs; 613-637 retains ambiguous intent and requeues failures; 744-826 maintains pending intent; 849-858 records accepted jobs. There is no recovery submission guard. `RECOVERY_REQUIRED => NO NEW DESKTOP WATCHER MUTATION SUBMISSIONS` is NOT CERTIFIED.

## RECOVERY_CERTIFICATION_GAPS

CERTIFICATION_BLOCKED. `ContextorGUI.analyze` does not positively compare `repo_id`, canonical `root_path`, `state_id`, revision, a readable committed durable snapshot and corresponding LIVE authority before clearing an incident. Phase 1 deliberately does not clear on acceptance. No clear operation was implemented.

## FILES_CHANGED

- C:\Temp\Contextor_Repo\contextor\ui\gui.py
- C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only)

## FULL_DIFFS

Complete actual `git diff -- contextor/ui/gui.py tests/test_gui_live_startup.py`:

```diff
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index c8ef77e..dfe5445 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -1146,10 +1146,6 @@ class ContextorGUI:
                     raise
 
                 if run_analysis:
-                    with self._live_recovery_lock:
-                        self._live_recovery_prompt_pending.discard(
-                            repository_key
-                        )
                     self.analyze()
 
         finally:
diff --git a/tests/test_gui_live_startup.py b/tests/test_gui_live_startup.py
index e00be11..f04e160 100644
--- a/tests/test_gui_live_startup.py
+++ b/tests/test_gui_live_startup.py
@@ -698,10 +698,37 @@ def test_recovery_prompt_accept_runs_existing_analyze_once(tmp_path, monkeypatch
 
     ask.assert_called_once()
     controller.analyze.assert_called_once_with()
-    assert controller._live_recovery_prompt_pending == set()
+    assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
     assert controller._live_recovery_queue.qsize() == 0
     assert next(iter(root.scheduled.values()))[0] == 100
 
+    ContextorGUI._request_full_analysis_recovery(
+        controller, str(repo), "Canonical state identity mismatch."
+    )
+    assert controller._live_recovery_queue.qsize() == 0
+    controller.analyze.assert_called_once_with()
+
+
+def test_recovery_prompt_failed_analysis_preserves_incident(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    root = MockTkRoot()
+    controller = _bind_recovery_prompt(_make_controller(repo, root))
+    controller.analyze.side_effect = RuntimeError("analysis failed")
+    ask = MagicMock(return_value=True)
+    monkeypatch.setattr(gui.messagebox, "askyesno", ask)
+
+    ContextorGUI._request_full_analysis_recovery(
+        controller, str(repo), "Canonical state identity mismatch."
+    )
+    with pytest.raises(RuntimeError, match="analysis failed"):
+        ContextorGUI._drain_live_recovery_queue(controller)
+
+    ask.assert_called_once()
+    controller.analyze.assert_called_once_with()
+    assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
+    assert controller._live_recovery_queue.qsize() == 0
+
 
 def test_recovery_prompt_suppressed_after_desktop_closes(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
```

## TARGETED_TEST_RESULTS

DIRECT_EVIDENCE: Seven exact nodes run with project venv: `test_generation_conflict_schedules_one_recovery_prompt`, `test_recovery_prompt_decline_preserves_incident`, `test_recovery_prompt_accept_runs_existing_analyze_once`, `test_recovery_prompt_failed_analysis_preserves_incident`, `test_recovery_prompt_suppressed_after_desktop_closes`, `test_recovery_prompt_suppressed_after_repository_switch`, `test_recovery_request_from_worker_uses_queue_without_tk`. Result: **7 passed, 1 third-party AuthlibDeprecationWarning in 4.20s**. Full suite not run.

## LIVE_WATCHER_VERIFICATION

DIRECT_EVIDENCE: `get_live_events(after_revision=11)` returned continuous, `resync_required=false`, `origin=desktop_watcher`, `status=UPDATED` for C:\Temp\Contextor_Repo\contextor\ui\gui.py at revision 12 and C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py at revision 13; latest revision 13. No manual `update_file` or restart. This proves watcher ingestion, not runtime reload or recovery invariant.

## IMPLEMENTATION_VERDICT

PHASE_1_PASS; PHASE_2_BLOCKED_ON_A_E_F_AND_GUARD_ATOMICITY; PHASE_3_NOT_IMPLEMENTED; CERTIFICATION_BLOCKED. Subsequent runtime integration certification requires reload after this production GUI code change; no restart was authorized here. STOP pending `proceduj`.


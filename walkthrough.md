# L37_L38_GATE_F_PUBLICATION_STATUS_CONTRACT

## CURRENT_HEAD

Pre-edit HEAD: 05c0672a841664e9ade586a56164b5ca83d33337. Current HEAD: cded927b6e30a53f185bba3fba20161e7a25c714. An external auto-commit occurred during this task; complete task diff is therefore measured from the pre-edit HEAD through the working tree.

## PRE_EDIT_CONTEXTOR_EVIDENCE

DIRECT_EVIDENCE: Contextor get_symbol_implementation resolved ContextorFacade.analyze_project, analyze_single_file, ContextorGUI._start_live_watcher_blocking and LiveStateClient.publish at LIVE revision 20 with workspace_sync=verified. get_artifact_blast_radius found direct facade consumers; Git source verified facade.py:1147-1179, 1271-1277, 1484-1491, 1575-1596; gui.py:1494-1532, 1741-1748; analysis_jobs.py:261-275, 339-400. Dynamic callers remain subject to textual verification. No contradictory invariant found.

## FILES_CHANGED

C:\Temp\Contextor_Repo\contextor\core\api\facade.py

C:\Temp\Contextor_Repo\contextor\ui\gui.py

C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py

C:\Temp\Contextor_Repo\contextor\mcp\docs\get_analysis_status.json

C:\Temp\Contextor_Repo\tests\test_h3a_workspace_canonical_freshness.py

C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py

C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py

C:\Temp\Contextor_Repo\tests\test_live_single_file_reuse.py

C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py

## PUBLIC_STATUS_CONTRACT

CODE_PATH_PROVED: recovery_required is assigned only for status=ok with resync_required=True and a revision in full analysis. It preserves accepted revision and response warning or fallback. Existing success, failed, timed_out and not_attempted branches remain. Scoped optional publication_result has status/revision/warning; omitted argument preserves str return and existing callers.

## FULL_ANALYSIS_PROPAGATION

CODE_PATH_PROVED: facade analysis_result and summary_data already copy live_publish_* fields. MCP project worker copies them to durable job and public get_analysis_status payload. Completed job message now identifies accepted publication requiring recovery, while cache hydration remains reserved for healthy success.

## SCOPED_ANALYSIS_PROPAGATION

CODE_PATH_PROVED: analyze_single_file initializes optional publication_result to not_attempted; a publish response populates success, recovery_required or failed with revision/warning. Transport exceptions populate failed. GUI single-file caller passes the channel, preserves report success, registers recovery for recovery_required and skips healthy watcher start for recovery_required/failed. Existing no-channel callers remain callable.

## GUI_RECOVERY_BEHAVIOR

CODE_PATH_PROVED: startup checks resync_required before ordinary ok. It registers the repository-keyed recovery incident with the required reason, displays accepted/rejected outcome and revision, then returns before watcher activation. The existing recovery queue deduplicates incidents and does not launch FULL without prompt.

## MCP_CONSUMER_COMPATIBILITY

CONTRACT_PROVED: get_analysis_status documentation includes recovery_required, its accepted revision and warning; existing values are retained. The durable job public projection already passes the three fields. Only success triggers canonical engine hydration; recovery_required remains completed but unverified.

## TARGETED_TEST_RESULTS

First new four-test run: 3 passed, 1 failed because optional parameter was mistakenly added to analyze_layer. Corrected before next run. Second single-file run failed because frozen HydratedRepositoryEngine fixture was mutated; replaced dataclass instance. Third failed because comment-only edit yielded no UPDATED publish; changed fixture source constant. All issues were test/patch placement, not production behavior. Final focused 11-case run: 11 passed, 1 unrelated Authlib deprecation warning, 28.81s. Final GUI rerun after outcome wording: 2 passed, 1 unrelated warning, 7.75s. No full suite.

## LIVE_WATCHER_VERIFICATION

DIRECT_EVIDENCE: Contextor get_live_events after_revision=20 returned continuous, resync_required=false, latest_revision=32 and desktop_watcher update_file events for facade.py revisions 21-22, gui.py revision 23, analysis_jobs.py revision 24, test_gui_live_startup.py revision 25. This verifies watcher progression for those observed files; remaining file-specific events were beyond the bounded first five and were not separately certified. No update_file call or runtime restart was made.

## UNRESOLVED_RISKS

UNKNOWN: abrupt process termination and actual unverified lock release are not exercised by these response-consumer tests. MCP single-file durable jobs retain the established not_applicable publication field because they do not use the optional scoped channel or make watcher health decisions. Runtime process was not restarted, so new code is source/test certified rather than running-process certified.

## IMPLEMENTATION_VERDICT

Focused contract implemented and targeted tests pass. Runtime reload/certification remains outside authorized scope.

## FULL_DIFFS

```diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index e905851..64352e5 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -10,6 +10,7 @@ import json
 import os
 import time
 from pathlib import Path
+from typing import Any
 
 from contextor.core.errors import AnalysisCancelled, checkpoint
 from contextor.core.graph.cycles import detect_cycles
@@ -1153,9 +1154,16 @@ class ContextorFacade:
                             and published.get("status") == "ok"
                             and published.get("revision") is not None
                         ):
-                            live_publish_status = "success"
                             live_publish_revision = int(published["revision"])
-                            live_publish_warning = None
+                            if published.get("resync_required") is True:
+                                live_publish_status = "recovery_required"
+                                live_publish_warning = (
+                                    published.get("warning")
+                                    or "LIVE recovery verification required."
+                                )
+                            else:
+                                live_publish_status = "success"
+                                live_publish_warning = None
                         else:
                             live_publish_status = "failed"
                             live_publish_revision = None
@@ -1487,8 +1495,11 @@ class ContextorFacade:
         log=None,
         progress_callback=None,
         additional_excludes: list[str] | None = None,
+        publication_result: dict[str, Any] | None = None,
     ) -> str:
         """Analyzes a single file within the context of a project. Returns report output path."""
+        if publication_result is not None:
+            publication_result.update(status="not_attempted", revision=None, warning=None)
         progress = _StagedProgress(progress_callback, total_stages=11, log=log)
         progress.begin("Validating repository and file scope")
         root_resolved, file = _resolve_repository_target(
@@ -1586,12 +1597,32 @@ class ContextorFacade:
             cache_hit = True
             if update_result.status == "UPDATED" and hydrated.client is not None:
                 try:
-                    hydrated.client.publish(
+                    published = hydrated.client.publish(
                         analysis_state,
                         origin="scoped_analysis",
                         timeout=5.0,
                     )
-                except (TimeoutError, OSError, EOFError, ConnectionError, RuntimeError):
+                    if isinstance(published, dict) and published.get("status") == "ok":
+                        if published.get("resync_required") is True:
+                            status = "recovery_required"
+                            warning = published.get("warning") or "LIVE recovery verification required."
+                        else:
+                            status = "success"
+                            warning = None
+                        revision = int(published["revision"]) if published.get("revision") is not None else None
+                    else:
+                        status = "failed"
+                        revision = None
+                        warning = (
+                            published.get("error") if isinstance(published, dict) else None
+                        ) or "Canonical LIVE service rejected publication."
+                    if publication_result is not None:
+                        publication_result.update(status=status, revision=revision, warning=warning)
+                    if status in {"failed", "recovery_required"} and log:
+                        log(f"[WARNING] Single-file LIVE publication: {warning}")
+                except (TimeoutError, OSError, EOFError, ConnectionError, RuntimeError) as exc:
+                    if publication_result is not None:
+                        publication_result.update(status="failed", revision=None, warning=f"{type(exc).__name__}: {exc}")
                     if log:
                         log("[WARNING] Updated single-file state could not be published to LIVE.")
             if log:
diff --git a/contextor/mcp/analysis_jobs.py b/contextor/mcp/analysis_jobs.py
index f340f5d..26fd745 100644
--- a/contextor/mcp/analysis_jobs.py
+++ b/contextor/mcp/analysis_jobs.py
@@ -391,7 +391,12 @@ async def _execute_analysis_job(
                     mcp_runtime._live_engine_revisions.pop(cache_key, None)
         publish_status = job.get("live_publish_status")
         completed_message = "Analysis completed successfully."
-        if job["operation"] == "project" and publish_status != "success":
+        if job["operation"] == "project" and publish_status == "recovery_required":
+            completed_message = (
+                "Analysis completed; canonical LIVE publication was accepted "
+                "but recovery verification is required."
+            )
+        elif job["operation"] == "project" and publish_status != "success":
             completed_message = (
                 "Analysis completed, but canonical LIVE publish "
                 f"{publish_status or 'failed'}."
diff --git a/contextor/mcp/docs/get_analysis_status.json b/contextor/mcp/docs/get_analysis_status.json
index 94e1d52..fc40697 100644
--- a/contextor/mcp/docs/get_analysis_status.json
+++ b/contextor/mcp/docs/get_analysis_status.json
@@ -14,7 +14,7 @@
     "Returns durable status for a specified or latest analysis job without any cardinality hard limit.\nResolution & ambiguity:\n1. Explicit job_id: returns the exact requested durable job without enumerating active jobs; missing jobs return status='not_found'.\n2. Omitted job_id: enumerates persisted queued/running jobs. When multiple active jobs exist, returns read-only status='ambiguous_job' with job_id=null, repo_path, active_job_count, bounded active_jobs list (max 5 candidates ordered newest mtime first, tie-broken by ascending job_id, each containing job_id, operation, target, status, created_at, updated_at), truncated boolean flag, and guidance message to repeat with one listed job_id.\n3. Single or zero active jobs: preserves legacy latest-durable-job selection (a sole active job is NOT automatically preferred over a newer terminal job).\nOutput <= 15 KiB (15360 UTF-8 bytes) returns the status payload normally.\nWhen output > 15 KiB with ``allow_large_output=false``, oversized status responses automatically single-shot reduce ``skipped_files`` evidence to the largest prefix fitting within 15360 UTF-8 bytes (adding top-level ``_output.auto_bounded=true``, ``bounded_collection='skipped_files'``, and ``returned_count``); scalar job metadata and progress state are never truncated. If minimal status with zero skipped files still exceeds 15360 bytes, ``status: 'confirmation_required'`` is returned.\nPassing ``allow_large_output=true`` returns the complete lossless status response without auto-bounding.\nFor running jobs, note that status and progress may advance between preflight and retry."
   ],
   "freshness": [
-    "Every job also exposes durable LIVE publication state. Project jobs move\nfrom ``live_publish_status='pending'`` to ``success``, ``timed_out`` or\n``failed``; an analysis failure before publication reports\n``not_attempted``. Successful publication includes\n``live_publish_revision`` (representing the LIVE publish/event journal revision returned by daemon, not canonical state publication revision). Publication failures preserve\n``live_publish_warning`` even though the report job itself may complete.\nLayer and single-file jobs report ``not_applicable`` because their shared\nfacade updates canonical state incrementally rather than publishing a new\nglobal baseline here."
+    "Every job also exposes durable LIVE publication state. Project jobs move\nfrom ``live_publish_status='pending'`` to ``success``, ``recovery_required``,\n``timed_out`` or ``failed``; an analysis failure before publication reports\n``not_attempted``. ``success`` means accepted and healthy;\n``recovery_required`` means the durable generation was committed and LIVE\npublication accepted, but LIVE health is not certified. Both accepted states\npreserve ``live_publish_revision`` (the revision returned by the daemon).\n``recovery_required`` preserves ``live_publish_warning`` and requires recovery\nverification before normal operation resumes. Rejected publication retains\n``failed`` and its warning even when the report job completes.\nLayer and single-file jobs report ``not_applicable`` because their shared\nfacade updates canonical state incrementally rather than publishing a new\nglobal baseline here."
   ],
   "errors": [
     "Explicit ``job_id`` bypasses active job ambiguity detection. When ``job_id`` is omitted and multiple active jobs exist, ``status: 'ambiguous_job'`` is returned.\nTerminal states are ``completed``, ``failed`` and ``interrupted``. A job\nleft running by a previous MCP server process is marked ``interrupted``\nrather than remaining permanently ambiguous. A queued/running job owned by the current MCP process is also reconciled to `interrupted` with `error='worker_not_active'` when its in-memory worker is no longer alive. If persistence of the reconciled interrupted state fails, the current call still returns the interrupted state and reports the persistence failure in `message` instead of returning stale queued/running status.",
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index dfe5445..a32a7cb 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -1497,6 +1497,24 @@ class ContextorGUI:
                         )
                     finally:
                         release_full_analysis(startup_lease)
+                    if (
+                        isinstance(published, dict)
+                        and published.get("resync_required") is True
+                    ):
+                        self._request_full_analysis_recovery(
+                            path,
+                            "Canonical LIVE publish requires recovery verification.",
+                        )
+                        if ContextorGUI._is_selected_live_repository(self, path):
+                            outcome = (
+                                "accepted" if published.get("status") == "ok"
+                                else "rejected"
+                            )
+                            self._set_live_status(
+                                f"LIVE: recovery required after {outcome} publish "
+                                f"(revision {published.get('revision')})"
+                            )
+                        return
                     if (
                         isinstance(published, dict)
                         and published.get("status") == "ok"
@@ -1738,13 +1756,27 @@ class ContextorGUI:
             )
             return
 
+        publication_result = {}
+
         def task(log=None, progress_callback=None):
             return ContextorFacade.analyze_single_file(
-                str(file_resolved), str(root_resolved), log=log, progress_callback=progress_callback
+                str(file_resolved), str(root_resolved), log=log,
+                progress_callback=progress_callback,
+                publication_result=publication_result,
             )
 
         def on_success(output):
-            self._start_live_watcher(str(root_resolved))
+            if publication_result.get("status") == "recovery_required":
+                self._request_full_analysis_recovery(
+                    str(root_resolved),
+                    "Canonical LIVE publish requires recovery verification.",
+                )
+                self._set_live_status(
+                    "LIVE: recovery required after accepted publish "
+                    f"(revision {publication_result.get('revision')})"
+                )
+            elif publication_result.get("status") != "failed":
+                self._start_live_watcher(str(root_resolved))
             messagebox.showinfo("Done", f"Single file report created:\n{output}")
 
         def on_error(exc):
diff --git a/tests/test_gui_live_startup.py b/tests/test_gui_live_startup.py
index f04e160..ba0c96b 100644
--- a/tests/test_gui_live_startup.py
+++ b/tests/test_gui_live_startup.py
@@ -864,6 +864,43 @@ def test_rejected_startup_publication_schedules_recovery_prompt(tmp_path, monkey
     controller.analyze.assert_not_called()
 
 
+def test_accepted_startup_publication_requires_recovery_without_watcher(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    controller = _bind_recovery_prompt(_make_controller(repo, MockTkRoot()))
+    loaded = SimpleNamespace(revision=7, state_id="loaded-generation")
+    remote = SimpleNamespace(revision=6, state_id="remote-generation")
+    releases = []
+
+    class Client:
+        def snapshot(self):
+            return {"state": remote, "revision": 6}
+
+        def publish(self, *_args, **_kwargs):
+            return {"status": "ok", "revision": 7, "resync_required": True}
+
+    monkeypatch.setattr(gui, "connect_or_start", lambda *_a, **_k: Client())
+    monkeypatch.setattr(gui, "migrate_legacy_snapshot", lambda *_a: tmp_path / "cache")
+    monkeypatch.setattr(gui, "acquire_full_analysis", lambda *_a, **_k: object())
+    monkeypatch.setattr(gui, "release_full_analysis", releases.append)
+    monkeypatch.setattr(gui, "DesktopLiveWatcher", lambda *_a, **_k: pytest.fail("watcher started"))
+    monkeypatch.setattr(
+        "contextor.core.analysis.state_manager.load_engine_state",
+        lambda *_a, **_k: loaded,
+    )
+
+    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
+    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
+
+    assert len(releases) == 2
+    assert controller._live_recovery_queue.qsize() == 1
+    assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
+    assert controller._statuses[-1] == "LIVE: recovery required after accepted publish (revision 7)"
+    assert "LIVE: shared state published; watcher active" not in controller._statuses
+    controller.analyze.assert_not_called()
+
+
 
 def test_recovery_request_from_worker_uses_queue_without_tk(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
diff --git a/tests/test_h3a_workspace_canonical_freshness.py b/tests/test_h3a_workspace_canonical_freshness.py
index 67af574..b083483 100644
--- a/tests/test_h3a_workspace_canonical_freshness.py
+++ b/tests/test_h3a_workspace_canonical_freshness.py
@@ -1143,6 +1143,32 @@ def test_h3a_case_v_active_daemon_publish_failure_response_dict(tmp_path, monkey
         _stop_authoritative_live(repo, server_client)
 
 
+def test_full_publish_accepted_recovery_preserves_revision_and_warning(tmp_path, monkeypatch):
+    from contextor.core.live_state import LiveStateClient
+
+    repo, mod_a = _setup_repo(tmp_path)
+    ContextorFacade.analyze_project(str(repo))
+    server_client = _start_authoritative_live(repo)
+    try:
+        mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 333\n", encoding="utf-8")
+        monkeypatch.setattr(
+            LiveStateClient, "publish",
+            lambda self, state, **kwargs: {
+                "status": "ok", "revision": state.revision,
+                "resync_required": True, "warning": "release unverified",
+            },
+        )
+        errors, result = ContextorFacade.analyze_project(str(repo))
+        assert not errors
+        assert result.live_publish_status == "recovery_required"
+        assert result.live_publish_revision is not None
+        assert result.live_publish_warning == "release unverified"
+        assert result.summary_data["live_publish_status"] == "recovery_required"
+        assert result.summary_data["live_publish_revision"] == result.live_publish_revision
+    finally:
+        _stop_authoritative_live(repo, server_client)
+
+
 def test_h3a_case_w_no_active_daemon_not_attempted(tmp_path):
     """Case W (H3A-H6 - No Active Daemon -> not_attempted):
     - No daemon running
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index 524364d..5653635 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -698,6 +698,49 @@ def test_scoped_analysis_success_refreshes_repository_live_identity(
     assert started == [str(repo.resolve()) if operation == "layer" else str(repo)]
 
 
+def test_scoped_analysis_accepted_recovery_does_not_start_watcher(
+    tmp_path, monkeypatch
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    target = repo / "module.py"
+    target.write_text("VALUE = 1\n", encoding="utf-8")
+    incidents = []
+    statuses = []
+    reports = []
+
+    def analyze_file(*_args, publication_result=None, **_kwargs):
+        publication_result.update(
+            status="recovery_required", revision=17, warning="release unverified"
+        )
+        return "single-output"
+
+    monkeypatch.setattr(
+        gui, "run_with_progress",
+        lambda _root, _progress, task, *, on_success, **_kwargs: on_success(task()),
+    )
+    monkeypatch.setattr(gui.ContextorFacade, "analyze_single_file", analyze_file)
+    monkeypatch.setattr(gui.messagebox, "showinfo", lambda *_args: reports.append(True))
+    controller = SimpleNamespace(
+        root=object(), progress_bar=SimpleNamespace(is_cancelled=False),
+        log_box=object(), cpu_indicator=object(), stop_btn=object(),
+        repo_path_var=SimpleNamespace(get=lambda: str(repo)),
+        file_path_var=SimpleNamespace(get=lambda: str(target)),
+        _busy_buttons=lambda: [],
+        _start_live_watcher=lambda _path: pytest.fail("unhealthy watcher started"),
+        _request_full_analysis_recovery=lambda path, reason: incidents.append((path, reason)),
+        _set_live_status=statuses.append,
+    )
+
+    gui.ContextorGUI.analyze_single(controller)
+
+    assert reports == [True]
+    assert incidents == [(
+        str(repo.resolve()), "Canonical LIVE publish requires recovery verification."
+    )]
+    assert statuses == ["LIVE: recovery required after accepted publish (revision 17)"]
+
+
 def test_closing_gui_shuts_down_owned_live_client(monkeypatch):
     events = []
     token = "test-gui-owner-token"
diff --git a/tests/test_live_single_file_reuse.py b/tests/test_live_single_file_reuse.py
index c4af235..f9726f1 100644
--- a/tests/test_live_single_file_reuse.py
+++ b/tests/test_live_single_file_reuse.py
@@ -1,5 +1,8 @@
 """Fast single-file primitives reuse canonical state instead of reparsing."""
 
+from types import SimpleNamespace
+from dataclasses import replace
+
 from contextor.core.reporting_engine.canonical_artifacts import (
     canonical_artifact_report,
 )
@@ -84,6 +87,43 @@ def test_single_file_changed_target_falls_back_to_incremental_engine(
     assert calls == 1
 
 
+def test_single_file_reports_accepted_recovery_without_changing_string_return(
+    sample_repo, isolated_dirs, monkeypatch
+):
+    import contextor.core.api.facade as facade_module
+
+    target = sample_repo / "core" / "alpha.py"
+    ContextorFacade.analyze_project(str(sample_repo))
+    original_hydrate = facade_module.hydrate_repository_engine
+    published = []
+
+    def hydrate_with_client(root):
+        hydrated = original_hydrate(root)
+        client = SimpleNamespace(publish=lambda *_a, **_k: published.append(True) or {
+            "status": "ok", "revision": 17,
+            "resync_required": True, "warning": "release unverified",
+        })
+        return replace(hydrated, client=client)
+
+    monkeypatch.setattr(facade_module, "hydrate_repository_engine", hydrate_with_client)
+    target.write_text(
+        target.read_text(encoding="utf-8").replace("MAX_ITEMS = 10", "MAX_ITEMS = 11"),
+        encoding="utf-8",
+    )
+    publication = {}
+    output = ContextorFacade.analyze_single_file(
+        str(target), str(sample_repo), publication_result=publication,
+    )
+
+    assert isinstance(output, str)
+    assert output.endswith("single_core.alpha.json")
+    assert published == [True]
+    assert publication == {
+        "status": "recovery_required", "revision": 17,
+        "warning": "release unverified",
+    }
+
+
 def test_single_file_resync_state_rejects_state_only_path(
     sample_repo, isolated_dirs, monkeypatch
 ):
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index cd25568..b4bbe05 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -1260,6 +1260,40 @@ def test_project_analysis_job_does_not_hydrate_after_failed_publication(
     assert str(repo) not in mcp_runtime._live_engine_revisions
 
 
+def test_project_analysis_job_preserves_accepted_recovery_status(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+
+    async def fake_worker(*_args, **_kwargs):
+        return {
+            "skipped_python_files": [],
+            "live_publish_status": "recovery_required",
+            "live_publish_revision": 11,
+            "live_publish_warning": "release unverified",
+        }
+
+    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
+    monkeypatch.setattr(
+        mcp_runtime, "get_or_init_engine",
+        lambda _root: pytest.fail("unhealthy publication hydrated as healthy"),
+    )
+    job = _project_analysis_job(repo, "accepted-recovery")
+    analysis_jobs._write_analysis_job(repo, job)
+
+    asyncio.run(analysis_jobs._execute_analysis_job(repo, job, None, []))
+
+    final_job = analysis_jobs._read_analysis_job(repo, job["job_id"])
+    assert final_job["status"] == "completed"
+    assert final_job["live_publish_status"] == "recovery_required"
+    assert final_job["live_publish_revision"] == 11
+    assert final_job["live_publish_warning"] == "release unverified"
+    assert "accepted" in final_job["message"]
+    assert "rejected" not in final_job["message"]
+    public_job = analysis_jobs._public_job(final_job)
+    assert public_job["live_publish_status"] == "recovery_required"
+    assert public_job["live_publish_revision"] == 11
+
+
 def test_analysis_status_bounds_and_exposes_skipped_python_files(tmp_path):
     repo = tmp_path / "repo"
     repo.mkdir()
```

## ACTUAL_DIFF

Complete diff from the pre-edit HEAD through the current working tree for every modified source, test and documentation file appears above. walkthrough.md is excluded.

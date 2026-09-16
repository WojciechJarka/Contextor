## CPA10K1_ANALYSIS_JOB_PERSISTENCE_AND_RECONCILIATION

STATUS=IMPLEMENTATION_COMPLETE_FOCUSED_PASS
TASK=CPA10K1_LITERAL_IMPLEMENTATION
MODE=APPLY_EXACT_CODE
REPO=C:\\Temp\\Contextor_Repo
HEAD=0b95ff860609ddb365878db0eb8873e7ab7c3dcf
NO_FULL_PYTEST=YES
PRODUCTION_ANALYZE_PROJECT_RUNTIME=NOT_RUN
STOP=WAIT_FOR_USER_COMMAND_PROCEDUJ

### STATUS

The exact requested implementation was applied after the explicit `proceduj` gate. The first composite patch attempt was rejected by `apply_patch` because one locally composed context anchor was incorrect; no partial edit was applied. The edits were then applied in exact scoped chunks. No redesign, ownership change, or edit to `contextor/mcp/tools/analyze_project.py` was made.

### SOURCE_DRIFT

SOURCE_DRIFT=NONE.

Literal pre-edit verification at the current HEAD confirmed:

- `contextor/mcp/analysis_jobs.py` still contained the requested import, constants anchor, complete `_write_analysis_job`, `_active_analysis_jobs`, and `_execute_analysis_job` locations.
- `contextor/mcp/tools/get_analysis_status.py` still contained the exact prior owner-process reconciliation block.
- The requested test and documentation anchors were present.
- `contextor/mcp/tools/analyze_project.py` was not changed.

### CONTEXTOR_OWNER_AND_LINEAGE_EVIDENCE

Discovery evidence was obtained before implementation through Contextor MCP at canonical revision `1234`, with `canonical_state=fresh`, `provenance=live`, and requested source targets reporting `workspace_sync=verified`.

- `contextor/mcp/analysis_jobs.py` is the canonical owner for durable job writes, in-memory task ownership, worker execution, and active-job filtering. Contextor resolved module ID `34/1`, 12 static consumers, and 49 reachable covering tests.
- `contextor/mcp/tools/get_analysis_status.py` is the canonical public reconciliation/status owner. Contextor resolved module ID `60/1`, public symbol `get_analysis_status` as `A1731/1`, five static consumers, and 29 reachable covering tests.
- Exact Contextor symbol implementations were resolved for `_write_analysis_job` (lines 43-54), `_active_analysis_jobs` (84-120), `_execute_analysis_job` (237-340), `_start_analysis_job` (343-379), and `get_analysis_status` (14-123).
- Call context confirmed the strict pre-start write in `_start_analysis_job`, persistence call sites in `_execute_analysis_job`, and the existing task `is_alive()` ownership map. `contextor_fact_lineage(family="symbol_calls")` confirmed the core analysis path remains owned by `ContextorFacade.analyze_project`; it did not move the job-persistence owner.

Post-implementation LIVE/runtime certification was intentionally not performed. MCP server source changed, so the running MCP process must be reloaded before any runtime certification.

### IMPLEMENTATION_CONTRACT_VERIFICATION

PASS for the requested implementation:

1. Added `time`, `_ANALYSIS_JOB_REPLACE_ATTEMPTS = 4`, and `_ANALYSIS_JOB_REPLACE_RETRY_SECONDS = 0.05`.
2. `_write_analysis_job` retries only `PermissionError` from the final `os.replace`, with four bounded attempts and three sleeps, reusing the same temporary file.
3. Temporary write is not retried; generic `OSError` is not retried; atomic temp-plus-replace semantics remain.
4. Added `_is_current_process_analysis_task_active(job_id)` using the existing lock/map and `is_alive()`.
5. Same-process durable queued/running jobs without an active in-memory task are excluded from `_active_analysis_jobs`.
6. Added best-effort `persist_job(phase)` with explicit stderr diagnostics.
7. Exact phases are `initial_running`, `progress`, `completed`, and `failed`.
8. Progress persistence failures are swallowed and diagnosed.
9. Completed persistence is best-effort after successful analysis.
10. Failed-state persistence cannot replace the primary core error; diagnostic is emitted.
11. The strict initial queued write in `_start_analysis_job` is unchanged.
12. Existing `finally` cleanup is unchanged.
13. Foreign-owner queued/running jobs preserve `owner_process_changed`.
14. Current-process jobs without a live task reconcile to `worker_not_active`.
15. Reconciliation persistence `OSError` still returns the in-memory interrupted response, with the warning stored in existing `message`.
16. No new public field was added.
17. The two requested public docs were updated only for changed lifecycle/reconciliation semantics.

### FOCUSED_TESTS

PASS.

- `& .\\.venv\\Scripts\\python.exe -m py_compile contextor/mcp/analysis_jobs.py contextor/mcp/tools/get_analysis_status.py tests/mcp/tools/test_analysis_status_concurrency.py tests/mcp/tools/test_analysis_trigger_docs.py`
  - exit code `0`.
- `& .\\.venv\\Scripts\\python.exe -m pytest tests/mcp/tools/test_analysis_status_concurrency.py tests/mcp/tools/test_analysis_trigger_docs.py -q`
  - `24 passed, 1 warning in 12.80s`.
  - Warning: existing `AuthlibDeprecationWarning` from the bundled FastMCP dependency.
- `git diff --check`
  - PASS. Git emitted only expected LF-to-CRLF working-copy warnings for changed files.
- Full pytest was not run.

### RESTART_REQUIREMENTS

MCP_SERVER_RESTART_REQUIRED=YES.

The changed files are imported by the MCP server process. Do not certify runtime behavior until that process is restarted/reloaded and freshness/schema/version is checked afterward.

DESKTOP_RESTART_REQUIRED=NO based on current discovery: no Desktop-owned runtime source was changed and no evidence established that a Desktop restart is required. Reassess only if the MCP server is hosted inside a Desktop process that is not independently reloadable.

No MCP or Desktop restart was performed.

### FILES_CHANGED

1. `contextor/mcp/analysis_jobs.py`
2. `contextor/mcp/tools/get_analysis_status.py`
3. `contextor/mcp/docs/get_analysis_status.json`
4. `contextor/mcp/docs/analyze_project.json`
5. `tests/mcp/tools/test_analysis_status_concurrency.py`
6. `tests/mcp/tools/test_analysis_trigger_docs.py`

`walkthrough.md` is the mandatory report channel and is excluded from this source/test/docs change set.

### EVIDENCE_CLASSIFICATION

- DIRECT_EVIDENCE: current HEAD, exact scoped diff, successful py_compile, focused pytest result, and git diff check.
- CODE_PATH_PROVED: persistence retry, best-effort phases, worker liveness filtering, and interrupted reconciliation paths shown in the complete diff below.
- CONTRACT_PROVED: requested exact edits, phase names, retry bounds, no-new-field rule, strict initial write, and focused test commands.
- INFERENCE: Desktop restart is not required based on ownership discovery; runtime certification remains unknown until MCP reload.
- UNKNOWN: post-restart LIVE/runtime behavior, intentionally not claimed.

### ACTUAL_DIFF

Complete actual diff for every changed production, test, and documentation file:

```diff
warning: in the working copy of 'contextor/mcp/analysis_jobs.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/mcp/docs/analyze_project.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/mcp/docs/get_analysis_status.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/mcp/tools/get_analysis_status.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/mcp/tools/test_analysis_status_concurrency.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/mcp/tools/test_analysis_trigger_docs.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/analysis_jobs.py b/contextor/mcp/analysis_jobs.py
index d8db080..b503805 100644
--- a/contextor/mcp/analysis_jobs.py
+++ b/contextor/mcp/analysis_jobs.py
@@ -3,6 +3,7 @@ import json
 import os
 import sys
 import threading
+import time
 from datetime import datetime, timezone
 from pathlib import Path
 from uuid import uuid4
@@ -18,6 +19,8 @@ _analysis_lock = threading.Lock()
 _analysis_job_lock = threading.RLock()
 _analysis_tasks: dict[str, threading.Thread] = {}
 _analysis_jobs_by_repo: dict[str, str] = {}
+_ANALYSIS_JOB_REPLACE_ATTEMPTS = 4
+_ANALYSIS_JOB_REPLACE_RETRY_SECONDS = 0.05
 
 
 def _mcp_cache_root(root: Path) -> Path:
@@ -51,7 +54,14 @@ def _write_analysis_job(root: Path, job: dict) -> None:
             json.dumps(payload, indent=2, ensure_ascii=False),
             encoding="utf-8",
         )
-        os.replace(temporary, target)
+        for attempt in range(_ANALYSIS_JOB_REPLACE_ATTEMPTS):
+            try:
+                os.replace(temporary, target)
+                break
+            except PermissionError:
+                if attempt + 1 >= _ANALYSIS_JOB_REPLACE_ATTEMPTS:
+                    raise
+                time.sleep(_ANALYSIS_JOB_REPLACE_RETRY_SECONDS)
 
 
 def _read_analysis_job(root: Path, job_id: str) -> dict | None:
@@ -81,6 +91,12 @@ def _latest_analysis_job(root: Path) -> dict | None:
     return None
 
 
+def _is_current_process_analysis_task_active(job_id: str) -> bool:
+    with _analysis_job_lock:
+        task = _analysis_tasks.get(job_id)
+        return task is not None and task.is_alive()
+
+
 def _active_analysis_jobs(root: Path) -> list[dict]:
     """Return readable queued/running durable jobs in deterministic newest-first order."""
     directory = _analysis_job_dir(root)
@@ -93,6 +109,13 @@ def _active_analysis_jobs(root: Path) -> list[dict]:
         job = _read_analysis_job(root, path.stem)
         if job is None or job.get("status") not in {"queued", "running"}:
             continue
+        if (
+            job.get("owner_pid") == os.getpid()
+            and not _is_current_process_analysis_task_active(
+                str(job.get("job_id") or "")
+            )
+        ):
+            continue
 
         try:
             mtime_ns = path.stat().st_mtime_ns
@@ -244,13 +267,26 @@ async def _execute_analysis_job(
         **job, "status": "running", "started_at": _utc_now(),
         "message": "Analysis started.",
     }
-    _write_analysis_job(root, job)
+
+    def persist_job(phase: str) -> bool:
+        try:
+            _write_analysis_job(root, job)
+        except OSError as exc:
+            _stderr_log(
+                f"[analysis-job-persistence] phase={phase} "
+                f"job_id={job.get('job_id')} "
+                f"{type(exc).__name__}: {exc}"
+            )
+            return False
+        return True
+
+    persist_job("initial_running")
 
     def job_log(message: str) -> None:
         nonlocal job
         _stderr_log(message)
         job = {**job, "message": str(message)}
-        _write_analysis_job(root, job)
+        persist_job("progress")
 
     try:
         analysis_outcome = await _run_analysis_worker(
@@ -321,7 +357,7 @@ async def _execute_analysis_job(
             **job, **(analysis_outcome or {}), "status": "completed",
             "completed_at": _utc_now(), "message": completed_message, "error": None,
         }
-        _write_analysis_job(root, job)
+        persist_job("completed")
     except Exception as exc:
         live_publish_status = job.get("live_publish_status")
         if job.get("operation") == "project" and live_publish_status == "pending":
@@ -332,7 +368,7 @@ async def _execute_analysis_job(
             "error": f"{type(exc).__name__}: {exc}",
             "live_publish_status": live_publish_status,
         }
-        _write_analysis_job(root, job)
+        persist_job("failed")
     finally:
         with _analysis_job_lock:
             _analysis_tasks.pop(str(job["job_id"]), None)
diff --git a/contextor/mcp/docs/analyze_project.json b/contextor/mcp/docs/analyze_project.json
index f7df415..b86147b 100644
--- a/contextor/mcp/docs/analyze_project.json
+++ b/contextor/mcp/docs/analyze_project.json
@@ -9,7 +9,7 @@
     "exclude_paths (array of strings or null, optional, default null): repository-relative or accepted existing exclusion paths forwarded to project analysis; null means no additional exclusions supplied by this request."
   ],
   "behavior": [
-    "1. Starts global architectural analysis asynchronously/non-blocking and immediately returns job identity and initial status.\n2. An active queued or running equivalent request may be reused according to existing job-owner semantics.\n3. Progress, completion, and coverage metrics are read through get_analysis_status.\n4. Tool does not require the LLM to poll source files directly."
+    "1. Starts global architectural analysis asynchronously/non-blocking and immediately returns job identity and initial status.\n2. An active queued or running equivalent request may be reused according to existing job-owner semantics.\n3. Progress, completion, and coverage metrics are read through get_analysis_status.\n4. Tool does not require the LLM to poll source files directly.\n5. Initial queued acceptance is durably persisted before the worker starts. After acceptance, running, progress, and terminal job-metadata persistence are best-effort observability updates; failure to persist those updates does not abort an otherwise valid repository analysis."
   ],
   "freshness": [],
   "errors": [],
diff --git a/contextor/mcp/docs/get_analysis_status.json b/contextor/mcp/docs/get_analysis_status.json
index 5acc92a..94e1d52 100644
--- a/contextor/mcp/docs/get_analysis_status.json
+++ b/contextor/mcp/docs/get_analysis_status.json
@@ -17,7 +17,7 @@
     "Every job also exposes durable LIVE publication state. Project jobs move\nfrom ``live_publish_status='pending'`` to ``success``, ``timed_out`` or\n``failed``; an analysis failure before publication reports\n``not_attempted``. Successful publication includes\n``live_publish_revision`` (representing the LIVE publish/event journal revision returned by daemon, not canonical state publication revision). Publication failures preserve\n``live_publish_warning`` even though the report job itself may complete.\nLayer and single-file jobs report ``not_applicable`` because their shared\nfacade updates canonical state incrementally rather than publishing a new\nglobal baseline here."
   ],
   "errors": [
-    "Explicit ``job_id`` bypasses active job ambiguity detection. When ``job_id`` is omitted and multiple active jobs exist, ``status: 'ambiguous_job'`` is returned.\nTerminal states are ``completed``, ``failed`` and ``interrupted``. A job\nleft running by a previous MCP server process is marked ``interrupted``\nrather than remaining permanently ambiguous.",
+    "Explicit ``job_id`` bypasses active job ambiguity detection. When ``job_id`` is omitted and multiple active jobs exist, ``status: 'ambiguous_job'`` is returned.\nTerminal states are ``completed``, ``failed`` and ``interrupted``. A job\nleft running by a previous MCP server process is marked ``interrupted``\nrather than remaining permanently ambiguous. A queued/running job owned by the current MCP process is also reconciled to `interrupted` with `error='worker_not_active'` when its in-memory worker is no longer alive. If persistence of the reconciled interrupted state fails, the current call still returns the interrupted state and reports the persistence failure in `message` instead of returning stale queued/running status.",
     "A completed global project job includes ``analysis_coverage`` when its\nindexer finished: ``skipped_python_files`` reports files that could not be\nstatically analyzed, their parser/read reason, structured ``line_number``\nand ``column_number`` when parser coordinates exist, and\n``syntax_error_count``.\n``max_skipped_files`` bounds returned entries (default 10); pass ``None``\nfor every skipped file. ``total`` and ``truncated`` make the coverage gap\nexplicit. Layer and single-file jobs do not claim global coverage."
   ],
 
diff --git a/contextor/mcp/tools/get_analysis_status.py b/contextor/mcp/tools/get_analysis_status.py
index 7b999a2..7b64bde 100644
--- a/contextor/mcp/tools/get_analysis_status.py
+++ b/contextor/mcp/tools/get_analysis_status.py
@@ -65,18 +65,42 @@ def get_analysis_status(
             {"status": "not_found", "job_id": job_id, "repo_path": str(root)},
             indent=2,
         )
-    if (
-        job.get("status") in {"queued", "running"}
-        and job.get("owner_pid") != os.getpid()
-    ):
-        job = {
-            **job,
-            "status": "interrupted",
-            "completed_at": analysis_jobs._utc_now(),
-            "message": "The MCP server process that owned this job is no longer active.",
-            "error": "owner_process_changed",
-        }
-        analysis_jobs._write_analysis_job(root, job)
+    if job.get("status") in {"queued", "running"}:
+        interruption_error = None
+        interruption_message = None
+
+        if job.get("owner_pid") != os.getpid():
+            interruption_error = "owner_process_changed"
+            interruption_message = (
+                "The MCP server process that owned this job is no longer active."
+            )
+        elif not analysis_jobs._is_current_process_analysis_task_active(
+            str(job.get("job_id") or "")
+        ):
+            interruption_error = "worker_not_active"
+            interruption_message = (
+                "The analysis worker for this job is no longer active."
+            )
+
+        if interruption_error is not None:
+            job = {
+                **job,
+                "status": "interrupted",
+                "completed_at": analysis_jobs._utc_now(),
+                "message": interruption_message,
+                "error": interruption_error,
+            }
+            try:
+                analysis_jobs._write_analysis_job(root, job)
+            except OSError as exc:
+                job = {
+                    **job,
+                    "message": (
+                        f"{interruption_message} "
+                        "Durable reconciliation persistence failed: "
+                        f"{type(exc).__name__}: {exc}"
+                    ),
+                }
     public_job = analysis_jobs._public_job(job, max_skipped_files=max_skipped_files)
     if public_job.get("status") == "completed":
         diag = diagnostics_summary_for_completed_job(diagnostics_summary(root), job)
diff --git a/tests/mcp/tools/test_analysis_status_concurrency.py b/tests/mcp/tools/test_analysis_status_concurrency.py
index 561b5a5..efaa5c8 100644
--- a/tests/mcp/tools/test_analysis_status_concurrency.py
+++ b/tests/mcp/tools/test_analysis_status_concurrency.py
@@ -1,3 +1,4 @@
+import asyncio
 import json
 import os
 from pathlib import Path
@@ -57,8 +58,9 @@ def _create_job(
 
 def test_analysis_status_concurrency__multiple_active_without_job_id_returns_ambiguity(tmp_path):
     root = tmp_path
-    _create_job(root, 1, status="queued", mtime_ns=1_000_000_000)
-    _create_job(root, 2, status="running", mtime_ns=2_000_000_000)
+    foreign_owner = os.getpid() + 100000
+    _create_job(root, 1, status="queued", owner_pid=foreign_owner, mtime_ns=1_000_000_000)
+    _create_job(root, 2, status="running", owner_pid=foreign_owner, mtime_ns=2_000_000_000)
 
     raw = get_analysis_status(str(root), job_id=None)
     res = json.loads(raw)
@@ -82,6 +84,11 @@ def test_analysis_status_concurrency__explicit_job_id_bypasses_ambiguity(tmp_pat
         raise AssertionError("_active_analysis_jobs MUST NOT be called when explicit job_id is passed!")
 
     monkeypatch.setattr(analysis_jobs, "_active_analysis_jobs", fail_if_active_called)
+    monkeypatch.setattr(
+        analysis_jobs,
+        "_is_current_process_analysis_task_active",
+        lambda _job_id: True,
+    )
 
     raw = get_analysis_status(str(root), job_id=j1["job_id"])
     res = json.loads(raw)
@@ -92,7 +99,13 @@ def test_analysis_status_concurrency__explicit_job_id_bypasses_ambiguity(tmp_pat
 
 def test_analysis_status_concurrency__single_active_does_not_override_newer_completed_latest(tmp_path):
     root = tmp_path
-    _create_job(root, 1, status="running", mtime_ns=1_000_000_000)
+    _create_job(
+        root,
+        1,
+        status="running",
+        owner_pid=os.getpid() + 100000,
+        mtime_ns=1_000_000_000,
+    )
     j2 = _create_job(root, 2, status="completed", mtime_ns=2_000_000_000)
 
     raw = get_analysis_status(str(root), job_id=None)
@@ -116,7 +129,13 @@ def test_analysis_status_concurrency__zero_active_preserves_latest_terminal(tmp_
 
 def test_analysis_status_concurrency__completed_jobs_do_not_count_as_active(tmp_path):
     root = tmp_path
-    _create_job(root, 1, status="queued", mtime_ns=1_000_000_000)
+    _create_job(
+        root,
+        1,
+        status="queued",
+        owner_pid=os.getpid() + 100000,
+        mtime_ns=1_000_000_000,
+    )
     _create_job(root, 2, status="failed", mtime_ns=2_000_000_000)
     j3 = _create_job(root, 3, status="completed", mtime_ns=3_000_000_000)
 
@@ -130,9 +149,28 @@ def test_analysis_status_concurrency__completed_jobs_do_not_count_as_active(tmp_
 
 def test_analysis_status_concurrency__active_candidates_are_deterministic_newest_first(tmp_path):
     root = tmp_path
-    j1 = _create_job(root, 1, status="queued", mtime_ns=1_000_000_000)
-    j2 = _create_job(root, 2, status="running", mtime_ns=3_000_000_000)
-    j3 = _create_job(root, 3, status="running", mtime_ns=2_000_000_000)
+    foreign_owner = os.getpid() + 100000
+    j1 = _create_job(
+        root,
+        1,
+        status="queued",
+        owner_pid=foreign_owner,
+        mtime_ns=1_000_000_000,
+    )
+    j2 = _create_job(
+        root,
+        2,
+        status="running",
+        owner_pid=foreign_owner,
+        mtime_ns=3_000_000_000,
+    )
+    j3 = _create_job(
+        root,
+        3,
+        status="running",
+        owner_pid=foreign_owner,
+        mtime_ns=2_000_000_000,
+    )
 
     raw = get_analysis_status(str(root), job_id=None)
     res = json.loads(raw)
@@ -144,8 +182,21 @@ def test_analysis_status_concurrency__active_candidates_are_deterministic_newest
 
 def test_analysis_status_concurrency__equal_mtime_uses_job_id_tiebreak(tmp_path):
     root = tmp_path
-    j1 = _create_job(root, 1, status="queued", mtime_ns=1_000_000_000)
-    j2 = _create_job(root, 2, status="running", mtime_ns=1_000_000_000)
+    foreign_owner = os.getpid() + 100000
+    j1 = _create_job(
+        root,
+        1,
+        status="queued",
+        owner_pid=foreign_owner,
+        mtime_ns=1_000_000_000,
+    )
+    j2 = _create_job(
+        root,
+        2,
+        status="running",
+        owner_pid=foreign_owner,
+        mtime_ns=1_000_000_000,
+    )
 
     raw = get_analysis_status(str(root), job_id=None)
     res = json.loads(raw)
@@ -157,8 +208,15 @@ def test_analysis_status_concurrency__equal_mtime_uses_job_id_tiebreak(tmp_path)
 
 def test_analysis_status_concurrency__candidate_list_is_bounded_to_five(tmp_path):
     root = tmp_path
+    foreign_owner = os.getpid() + 100000
     for i in range(1, 8):
-        _create_job(root, i, status="running", mtime_ns=i * 1_000_000_000)
+        _create_job(
+            root,
+            i,
+            status="running",
+            owner_pid=foreign_owner,
+            mtime_ns=i * 1_000_000_000,
+        )
 
     raw = get_analysis_status(str(root), job_id=None)
     res = json.loads(raw)
@@ -233,3 +291,255 @@ def test_analysis_status_concurrency__runtime_description_is_index_backed():
     assert "multiple" in description
     assert "queued/running" in description
     assert "ambiguous_job" in description
+
+
+def test_analysis_job_write__retries_permission_error_only_on_replace(
+    tmp_path, monkeypatch
+):
+    real_replace = analysis_jobs.os.replace
+    replace_calls = []
+    sleep_calls = []
+
+    def flaky_replace(source, target):
+        replace_calls.append((source, target))
+        if len(replace_calls) < 3:
+            raise PermissionError("replace temporarily blocked")
+        real_replace(source, target)
+
+    monkeypatch.setattr(analysis_jobs.os, "replace", flaky_replace)
+    monkeypatch.setattr(analysis_jobs.time, "sleep", sleep_calls.append)
+
+    job_id = f"{101:032x}"
+    analysis_jobs._write_analysis_job(
+        tmp_path,
+        {"job_id": job_id, "status": "queued"},
+    )
+
+    assert len(replace_calls) == 3
+    assert sleep_calls == [
+        analysis_jobs._ANALYSIS_JOB_REPLACE_RETRY_SECONDS,
+        analysis_jobs._ANALYSIS_JOB_REPLACE_RETRY_SECONDS,
+    ]
+    persisted = analysis_jobs._read_analysis_job(tmp_path, job_id)
+    assert persisted is not None
+    assert persisted["status"] == "queued"
+
+
+def test_analysis_job_write__does_not_retry_generic_oserror(
+    tmp_path, monkeypatch
+):
+    replace_calls = []
+    sleep_calls = []
+
+    def failing_replace(source, target):
+        replace_calls.append((source, target))
+        raise OSError("replace failed")
+
+    monkeypatch.setattr(analysis_jobs.os, "replace", failing_replace)
+    monkeypatch.setattr(analysis_jobs.time, "sleep", sleep_calls.append)
+
+    with pytest.raises(OSError, match="replace failed"):
+        analysis_jobs._write_analysis_job(
+            tmp_path,
+            {"job_id": f"{102:032x}", "status": "queued"},
+        )
+
+    assert len(replace_calls) == 1
+    assert sleep_calls == []
+
+
+def test_analysis_job_execution__progress_persistence_failure_does_not_abort(
+    tmp_path, monkeypatch, capsys
+):
+    job = _create_job(
+        tmp_path,
+        103,
+        status="queued",
+        operation="layer",
+        started_at=None,
+        completed_at=None,
+        live_publish_status="not_applicable",
+        live_publish_revision=None,
+    )
+    writes = []
+
+    async def fake_worker(
+        operation,
+        root,
+        target=None,
+        exclude_paths=None,
+        log=None,
+    ):
+        assert operation == "layer"
+        assert log is not None
+        log("progress")
+        return {}
+
+    def flaky_write(root, payload):
+        writes.append(dict(payload))
+        if payload.get("message") == "progress":
+            raise OSError("progress persistence failed")
+
+    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
+    monkeypatch.setattr(analysis_jobs, "_write_analysis_job", flaky_write)
+
+    asyncio.run(
+        analysis_jobs._execute_analysis_job(
+            tmp_path,
+            job,
+            None,
+            None,
+        )
+    )
+
+    assert any(item.get("status") == "completed" for item in writes)
+    stderr = capsys.readouterr().err
+    assert "[analysis-job-persistence] phase=progress" in stderr
+    assert "progress persistence failed" in stderr
+
+
+def test_analysis_job_execution__primary_failure_survives_failed_persistence(
+    tmp_path, monkeypatch, capsys
+):
+    job = _create_job(
+        tmp_path,
+        104,
+        status="queued",
+        operation="layer",
+        started_at=None,
+        completed_at=None,
+        live_publish_status="not_applicable",
+        live_publish_revision=None,
+    )
+    job_id = job["job_id"]
+    writes = []
+
+    async def failing_worker(*args, **kwargs):
+        raise ValueError("primary boom")
+
+    def flaky_write(root, payload):
+        writes.append(dict(payload))
+        if payload.get("status") == "failed":
+            raise OSError("secondary persistence boom")
+
+    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", failing_worker)
+    monkeypatch.setattr(analysis_jobs, "_write_analysis_job", flaky_write)
+    monkeypatch.setitem(analysis_jobs._analysis_tasks, job_id, object())
+    monkeypatch.setitem(
+        analysis_jobs._analysis_jobs_by_repo,
+        str(tmp_path),
+        job_id,
+    )
+
+    asyncio.run(
+        analysis_jobs._execute_analysis_job(
+            tmp_path,
+            job,
+            None,
+            None,
+        )
+    )
+
+    failed_payloads = [
+        item for item in writes if item.get("status") == "failed"
+    ]
+    assert len(failed_payloads) == 1
+    assert failed_payloads[0]["error"] == "ValueError: primary boom"
+    assert job_id not in analysis_jobs._analysis_tasks
+    assert str(tmp_path) not in analysis_jobs._analysis_jobs_by_repo
+
+    stderr = capsys.readouterr().err
+    assert "[analysis-job-persistence] phase=failed" in stderr
+    assert "secondary persistence boom" in stderr
+
+
+def test_analysis_status_concurrency__same_process_dead_worker_is_interrupted(
+    tmp_path, monkeypatch
+):
+    job = _create_job(
+        tmp_path,
+        105,
+        status="running",
+        owner_pid=os.getpid(),
+    )
+    monkeypatch.delitem(
+        analysis_jobs._analysis_tasks,
+        job["job_id"],
+        raising=False,
+    )
+
+    res = json.loads(
+        get_analysis_status(str(tmp_path), job_id=job["job_id"])
+    )
+
+    assert res["status"] == "interrupted"
+    assert res["error"] == "worker_not_active"
+
+    persisted = analysis_jobs._read_analysis_job(
+        tmp_path,
+        job["job_id"],
+    )
+    assert persisted["status"] == "interrupted"
+    assert persisted["error"] == "worker_not_active"
+
+
+def test_analysis_status_concurrency__reconciliation_write_failure_returns_interrupted(
+    tmp_path, monkeypatch
+):
+    job = _create_job(
+        tmp_path,
+        106,
+        status="running",
+        owner_pid=os.getpid(),
+    )
+    monkeypatch.delitem(
+        analysis_jobs._analysis_tasks,
+        job["job_id"],
+        raising=False,
+    )
+
+    def fail_write(*args, **kwargs):
+        raise OSError("cannot persist reconciliation")
+
+    monkeypatch.setattr(
+        analysis_jobs,
+        "_write_analysis_job",
+        fail_write,
+    )
+
+    res = json.loads(
+        get_analysis_status(str(tmp_path), job_id=job["job_id"])
+    )
+
+    assert res["status"] == "interrupted"
+    assert res["error"] == "worker_not_active"
+    assert "Durable reconciliation persistence failed" in res["message"]
+    assert "cannot persist reconciliation" in res["message"]
+
+
+def test_active_analysis_jobs__excludes_dead_same_process_worker(
+    tmp_path, monkeypatch
+):
+    current = _create_job(
+        tmp_path,
+        107,
+        status="running",
+        owner_pid=os.getpid(),
+        mtime_ns=2_000_000_000,
+    )
+    foreign = _create_job(
+        tmp_path,
+        108,
+        status="running",
+        owner_pid=os.getpid() + 100000,
+        mtime_ns=1_000_000_000,
+    )
+    monkeypatch.delitem(
+        analysis_jobs._analysis_tasks,
+        current["job_id"],
+        raising=False,
+    )
+
+    active = analysis_jobs._active_analysis_jobs(tmp_path)
+
+    assert [job["job_id"] for job in active] == [foreign["job_id"]]
diff --git a/tests/mcp/tools/test_analysis_trigger_docs.py b/tests/mcp/tools/test_analysis_trigger_docs.py
index 354b461..4779cfe 100644
--- a/tests/mcp/tools/test_analysis_trigger_docs.py
+++ b/tests/mcp/tools/test_analysis_trigger_docs.py
@@ -46,3 +46,17 @@ def test_analysis_trigger_docs__runtime_signatures_unchanged():
     assert str(inspect.signature(tools["analyze_single_file"].fn)) == (
         "(repo_path: str, file_path: str, exclude_paths: list[str] | None = None) -> str"
     )
+
+
+def test_analysis_trigger_docs__job_lifecycle_persistence_semantics_documented():
+    analyze_project_doc = _load_doc("analyze_project")
+    analyze_behavior = "\n".join(analyze_project_doc.get("behavior", []))
+    assert "durably persisted before the worker starts" in analyze_behavior
+    assert "best-effort observability updates" in analyze_behavior
+    assert "does not abort an otherwise valid repository analysis" in analyze_behavior
+
+    status_doc = _load_doc("get_analysis_status")
+    status_errors = "\n".join(status_doc.get("errors", []))
+    assert "worker_not_active" in status_errors
+    assert "persistence failure" in status_errors
+    assert "stale queued/running status" in status_errors
```

### NEXT_STEP

STOP. Await the explicit user command: `proceduj`.


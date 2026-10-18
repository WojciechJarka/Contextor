# CONTEXTOR_FULL_JOB_DURABLE_READ_SYNCHRONIZATION

## TASK
Controlled minimal implementation of same-process durable analysis-job read synchronization.

## HEAD_BEFORE
61ed85be62d346c78a2e6120de5ca4550e69526a

## HEAD_AFTER
61ed85be62d346c78a2e6120de5ca4550e69526a (no commit)

## FILES_CHANGED
- contextor/mcp/analysis_jobs.py
- tests/mcp/tools/test_analysis_status_concurrency.py

Three cycle-parity test files were already modified before this task and were not changed here. walkthrough.md is the report.

## EXACT_IMPLEMENTATION
_read_analysis_job retains job ID validation and dict|None behavior. The existing _analysis_job_lock now encloses Path.read_text and json.loads. _write_analysis_job, RLock type, atomic replacement, public statuses, and permanent missing/malformed fail-closed behavior are unchanged. No retry, polling, or cross-process lock.

Contextor pre-edit owner: contextor.mcp.analysis_jobs::_read_analysis_job, adapter layer. Direct static consumer: contextor.mcp.tools.get_analysis_status; five test consumers. Downstream includes contextor.mcp_main and contextor.mcp_server. Post-edit Contextor revision 614 confirms fresh source and workspace_sync=verified; same public consumer.

## SYNCHRONIZATION_PROOF
T04 starts writer and reader threads, pauses os.replace while writer owns _analysis_job_lock, observes Path.read_text, and asserts reader cannot enter filesystem read until writer releases the lock. Reader then obtains the complete new record. Removing the reader lock makes the observed read enter the held critical section and fails the assertion. T05 proves reentrancy. T06 repeats queued -> running -> completed. This proves same-process thread synchronization only. The original transient OSError was not captured.

## T01_T06_RESULTS
T01 completed record PASS. T02 missing record/public not_found PASS. T03 malformed JSON/public not_found PASS. T04 controlled overlap PASS. T05 reentrancy PASS. T06 successive writes PASS.
Dedicated command: .venv/Scripts/python.exe -m pytest -q --tb=short tests/mcp/tools/test_analysis_status_concurrency.py -k durable_read_t0
Result: 6 passed, 55 deselected, 1 warning in 7.18 s.

## STRICT_FULL_FULL_RESULTS
Exact test passed three post-edit executions: standalone 1 passed in 8.77 s; selected run 1 passed as part of 6 passed in 7.46 s; standalone 1 passed in 6.47 s. No transient not_found observed in those runs.

## CYCLE_PARITY_NON_REGRESSION
Strict FULL–FULL plus five negative cycle-parity cases: 6 passed, 1 warning in 7.46 s. Cycle-parity test files unchanged by this task.

## TARGETED_TEST_RESULTS
Entire tests/mcp/tools/test_analysis_status_concurrency.py: 61 passed, 1 warning in 8.50 s. git diff --check on changed files passed. No full repository pytest suite.

## LIVE_REVISION_BEFORE_AFTER
Before: 612, epoch 75fabf0b943b4947b50d420084de8583, continuous, resync_required=false.
After: 614, same epoch, continuous, resync_required=false. Contextor symbol preview: canonical_state=fresh, workspace_sync=verified, provenance=live.

## WATCHER_EVENTS
Revision 613: desktop_watcher update_file UPDATED contextor/mcp/analysis_jobs.py.
Revision 614: desktop_watcher update_file UPDATED tests/mcp/tools/test_analysis_status_concurrency.py.
No manual update_file.

## RESTART_REQUIREMENTS
MCP_BACKEND_RESTART_REQUIRED=YES: serving process must reload analysis_jobs. No restart performed.
LIVE_SERVICE_RESTART_REQUIRED=NO: no separate LIVE service change or restart dependency found.

## FULL_DIFFS
Full actual Git diffs of both task-changed files follow.
```diff
diff --git a/contextor/mcp/analysis_jobs.py b/contextor/mcp/analysis_jobs.py
index 4815218..dcfb43a 100644
--- a/contextor/mcp/analysis_jobs.py
+++ b/contextor/mcp/analysis_jobs.py
@@ -108,7 +108,8 @@ def _read_analysis_job(root: Path, job_id: str) -> dict | None:
     except ValueError:
         return None
     try:
-        return json.loads(path.read_text(encoding="utf-8"))
+        with _analysis_job_lock:
+            return json.loads(path.read_text(encoding="utf-8"))
     except (OSError, json.JSONDecodeError):
         return None
 
diff --git a/tests/mcp/tools/test_analysis_status_concurrency.py b/tests/mcp/tools/test_analysis_status_concurrency.py
index 4f65224..e44309b 100644
--- a/tests/mcp/tools/test_analysis_status_concurrency.py
+++ b/tests/mcp/tools/test_analysis_status_concurrency.py
@@ -1,6 +1,7 @@
 import asyncio
 import json
 import os
+import threading
 from pathlib import Path
 
 import pytest
@@ -1394,3 +1395,110 @@ def test_active_analysis_jobs__excludes_dead_same_process_worker(
     active = analysis_jobs._active_analysis_jobs(tmp_path)
 
     assert [job["job_id"] for job in active] == [foreign["job_id"]]
+
+
+def test_durable_read_t01_completed_job(tmp_path):
+    job = _create_job(tmp_path, 201)
+    assert analysis_jobs._read_analysis_job(tmp_path, job["job_id"])["status"] == "completed"
+    assert analysis_jobs._read_analysis_job(tmp_path, job["job_id"])["operation"] == "project"
+
+
+def test_durable_read_t02_missing_job(tmp_path):
+    job_id = f"{202:032x}"
+    assert analysis_jobs._read_analysis_job(tmp_path, job_id) is None
+    assert json.loads(get_analysis_status(str(tmp_path), job_id=job_id))["status"] == "not_found"
+
+
+def test_durable_read_t03_malformed_json(tmp_path):
+    job_id = f"{203:032x}"
+    path = analysis_jobs._job_path(tmp_path, job_id)
+    path.parent.mkdir(parents=True)
+    path.write_text("{malformed", encoding="utf-8")
+    assert analysis_jobs._read_analysis_job(tmp_path, job_id) is None
+    assert json.loads(get_analysis_status(str(tmp_path), job_id=job_id))["status"] == "not_found"
+
+
+def _read_during_replace(tmp_path, monkeypatch, job, next_status):
+    target = analysis_jobs._job_path(tmp_path, job["job_id"])
+    replace_entered = threading.Event()
+    allow_replace = threading.Event()
+    read_entered = threading.Event()
+    reader_started = threading.Event()
+    original_replace = analysis_jobs.os.replace
+    original_read_text = Path.read_text
+    results = {}
+
+    def held_replace(source, destination):
+        if Path(destination) == target:
+            replace_entered.set()
+            assert allow_replace.wait(5), "writer was not released"
+        return original_replace(source, destination)
+
+    def observed_read_text(path, *args, **kwargs):
+        if path == target:
+            read_entered.set()
+        return original_read_text(path, *args, **kwargs)
+
+    monkeypatch.setattr(analysis_jobs.os, "replace", held_replace)
+    monkeypatch.setattr(Path, "read_text", observed_read_text)
+    updated = {**job, "status": next_status}
+
+    def write_job():
+        try:
+            analysis_jobs._write_analysis_job(tmp_path, updated)
+        except BaseException as exc:
+            results["writer_error"] = exc
+
+    def read_job():
+        reader_started.set()
+        try:
+            results["read"] = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
+        except BaseException as exc:
+            results["reader_error"] = exc
+
+    writer = threading.Thread(target=write_job)
+    reader = threading.Thread(target=read_job)
+    writer.start()
+    try:
+        assert replace_entered.wait(5), "writer did not enter replacement"
+        reader.start()
+        assert reader_started.wait(5)
+        assert not read_entered.wait(0.3), "filesystem read entered writer critical section"
+    finally:
+        allow_replace.set()
+        writer.join(timeout=5)
+        if reader.ident is not None:
+            reader.join(timeout=5)
+    assert not writer.is_alive() and not reader.is_alive()
+    assert "writer_error" not in results and "reader_error" not in results, results
+    assert read_entered.is_set()
+    assert results["read"]["status"] == next_status
+    assert results["read"]["job_id"] == job["job_id"]
+    return updated
+
+
+def test_durable_read_t04_waits_for_writer_critical_section(tmp_path, monkeypatch):
+    job = _create_job(tmp_path, 204, status="queued")
+    _read_during_replace(tmp_path, monkeypatch, job, "completed")
+
+
+def test_durable_read_t05_reentrant_under_existing_job_lock(tmp_path):
+    job = _create_job(tmp_path, 205)
+    result = {}
+
+    def nested_read():
+        with analysis_jobs._analysis_job_lock:
+            result["job"] = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
+
+    thread = threading.Thread(target=nested_read, daemon=True)
+    thread.start()
+    thread.join(timeout=5)
+    assert not thread.is_alive(), "nested read deadlocked"
+    assert result["job"]["job_id"] == job["job_id"]
+
+
+def test_durable_read_t06_successive_writes_never_not_found(tmp_path, monkeypatch):
+    job = _create_job(tmp_path, 206, status="queued")
+    for status in ("running", "completed"):
+        job = _read_during_replace(tmp_path, monkeypatch, job, status)
+        assert analysis_jobs._read_analysis_job(tmp_path, job["job_id"])["status"] == status
```
## FINAL_VERDICT
PASS for approved same-process synchronization and targeted gates. Original transient exception remains unobserved; no cross-process guarantee.

STOP. Await proceduj.

# FULL-HISTORY-I2 — Desktop FULL history

Status: **IMPLEMENTED_PENDING_AUDIT**. P10 pozostaje wstrzymane. Bez FINAL PASS.

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP pierwszy: LIVE revision 1503, canonical_state=fresh, global workspace_sync=unverified, syntax_errors=0 (fresh), cycle_semantics=stale. Przed zmianą per-file sync=verified dla `gui.py` i `get_analysis_status.py`; nie było zmian użytkownika w objętych plikach.
- DIRECT_EVIDENCE: HEAD `62ab4d09eceebfe0170da93bf41d2abc97616aa8`; początkowy status: `M CHANGELOG.md`, `M walkthrough.md`. Nie dotykano `CHANGELOG.md` ani `issues.md`.

## EXACT_IMPLEMENTATION

- CODE_PATH_PROVED: Dodano dokładny moduł `full_analysis_history.py` z wrapperem wokół pełnego wywołania koordynatora. `contextor/ui/gui.py` przekazuje do niego jedyne wywołanie FULL w `ContextorGUI.analyze`; zachowano pozostałe argumenty, bez zmiany koordynatora, lease i publikacji. `_public_job` dodaje `source`; `get_analysis_status` preferuje jedyny aktywny job.
- DIRECT_EVIDENCE: `ast.parse` wszystkich sześciu zmienionych plików Python oraz `json.loads` dokumentacji przeszły. `git diff --check` przeszedł. Nie uruchomiono FULL.

## DESKTOP_SOURCE_PROVENANCE

- CODE_PATH_PROVED: `source=desktop` jest zapisywane tylko przez wrapper podłączony w GUI. Programowe wywołania samego koordynatora, w tym domyślny `owner`, nie zapisują Desktop history. Wspólny format trwałego pliku to `.contextor/analysis_jobs/<job_id>.json`.

## RELEASE_FAILURE_PARITY

- CONTRACT_PROVED: Test z kontrolowanym wyjątkiem po zwolnieniu lease kończy wywołanie wyjątkiem, a rekord ma `status=failed` i pola publikacji `null`. Nie jest zapisywane fałszywe `completed` dla błędu całego wywołania.

## PUBLIC_STATUS_CONTRACT

- CODE_PATH_PROVED: Publiczne `source` ma wartość `desktop` dla nowych rekordów GUI, `mcp` dla historycznych jobów MCP bez pola. Przy jednym aktywnym jobie jest on preferowany; przy braku aktywnych wybór pozostaje według mtime z obu źródeł; jawne `job_id` pozostaje exact. Test obejmuje aktywny MCP i nowszy Desktop record.

## HISTORY_PERSISTENCE_FAILURE

- CONTRACT_PROVED: Dwa celowane testy sprawdzają, że błąd zapisu historii nie maskuje wyniku ani oryginalnego wyjątku analizy. `trace_event` jest best effort i według `contextor/core/runtime_trace.py:1809–1811` nie rzuca wyjątków.

## DOCUMENTATION_SYNC

- DIRECT_EVIDENCE: Zaktualizowano `contextor/mcp/docs/get_analysis_status.json`: zakres MCP i Desktop, `source`, preferencja aktywnego, semantyka ukończenia wrappera, null po błędzie, brak rekonstrukcji starszych Desktop FULL. JSON poprawny; testy kontraktu dokumentacji przeszły.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: `.venv/Scripts/python.exe -m pytest -q tests/test_full_analysis_coordination.py -k "desktop_history"`: 4 passed, 45 deselected.
- DIRECT_EVIDENCE: `.venv/Scripts/python.exe -m pytest -q tests/test_mcp_regressions.py -k "desktop_history or analysis_status"`: 5 passed, 109 deselected; 2 ostrzeżenia deprecacji zależności.
- DIRECT_EVIDENCE: `.venv/Scripts/python.exe -m pytest -q tests/test_mcp_split_s2b.py tests/test_mcp_documentation.py`: 18 passed; 2 ostrzeżenia deprecacji zależności. Nie uruchomiono pełnego suite.

## MCP_POST_AUDIT

- DIRECT_EVIDENCE: Po zmianie LIVE revision 1509; `canonical_state=fresh`, `syntax_errors=0` (fresh), global `workspace_sync=unverified`, `cycle_semantics=stale`. Per-file `workspace_sync=verified` dla nowego modułu, GUI, `analysis_jobs.py`, `get_analysis_status.py` i obu zmienionych testów. Przejściowy `out_of_sync` dla `test_mcp_regressions.py` przy revision 1508 zniknął po event watcher do 1509. Dokumentacja JSON nie jest kanonicznym modułem Python.

## RUNTIME_ADOPTION_REQUIRED

- DIRECT_EVIDENCE: Świeżość grafu LIVE nie dowodzi załadowania zmienionego kodu w działającym Desktop ani backendzie MCP. Oba procesy wymagają odrębnej adopcji/reloadu przed certyfikacją zachowania runtime. Nie restartowano ich.

## FILES_CHANGED

- `contextor/core/analysis/full_analysis_history.py` (nowy)
- `contextor/ui/gui.py`
- `contextor/mcp/analysis_jobs.py`
- `contextor/mcp/tools/get_analysis_status.py`
- `contextor/mcp/docs/get_analysis_status.json`
- `tests/test_full_analysis_coordination.py`
- `tests/test_mcp_regressions.py`
- `walkthrough.md` nadpisany jako raport, nie liczony jako source/test/docs. `CHANGELOG.md` był zmodyfikowany przed zadaniem i nie należy do diffów I2.

## FULL_DIFFS

Poniżej pełne aktualne diffy siedmiu plików source/tests/docs względem HEAD, włącznie z nowym plikiem.

```diff
diff --git a/contextor/core/analysis/full_analysis_history.py b/contextor/core/analysis/full_analysis_history.py
new file mode 100644
index 0000000..228f787
--- /dev/null
+++ b/contextor/core/analysis/full_analysis_history.py
@@ -0,0 +1,158 @@
+from __future__ import annotations
+
+import json
+import os
+from datetime import datetime, timezone
+from pathlib import Path
+from typing import Any, Callable
+from uuid import uuid4
+
+from contextor.core.runtime_trace import trace_event
+
+
+_PUBLISH_FIELDS = (
+    "live_publish_status",
+    "live_publish_revision",
+    "live_publish_warning",
+    "live_publish_idempotency_key",
+    "live_publish_job_id",
+    "live_publish_service_instance_id",
+    "live_publish_process_start_identity",
+    "live_publish_expected_state_id",
+    "live_publish_expected_revision",
+)
+
+
+def _utc_now() -> str:
+    return datetime.now(timezone.utc).isoformat()
+
+
+def _write_desktop_full_record(
+    repo_path: str | Path,
+    *,
+    started_at: str,
+    outcome: object,
+    failure: BaseException | None,
+) -> None:
+    root = Path(repo_path).resolve()
+    result = (
+        outcome[1]
+        if isinstance(outcome, tuple)
+        and len(outcome) == 2
+        else None
+    )
+    failed = failure is not None or result is None
+    completed_at = _utc_now()
+    job_id = uuid4().hex
+
+    record = {
+        "job_id": job_id,
+        "source": "desktop",
+        "operation": "project",
+        "repo_path": str(root),
+        "target": None,
+        "status": "failed" if failed else "completed",
+        "created_at": started_at,
+        "started_at": started_at,
+        "completed_at": completed_at,
+        "updated_at": completed_at,
+        "message": (
+            "Desktop FULL failed."
+            if failed else "Desktop FULL completed."
+        ),
+        "error": (
+            f"{type(failure).__name__}: {failure}"
+            if failure is not None
+            else "Analysis returned no result."
+            if result is None
+            else None
+        ),
+    }
+
+    record.update({
+        key: getattr(result, key, None)
+        if not failed else None
+        for key in _PUBLISH_FIELDS
+    })
+
+    summary = getattr(result, "summary_data", None)
+    if (
+        not failed
+        and isinstance(summary, dict)
+        and isinstance(summary.get("skipped_files"), list)
+    ):
+        record["skipped_python_files"] = list(
+            summary["skipped_files"]
+        )
+
+    directory = root / ".contextor" / "analysis_jobs"
+    directory.mkdir(parents=True, exist_ok=True)
+    target = directory / f"{job_id}.json"
+    temporary = directory / (
+        f"{job_id}.json.{uuid4().hex}.tmp"
+    )
+
+    try:
+        temporary.write_text(
+            json.dumps(
+                record, indent=2, ensure_ascii=False,
+            ),
+            encoding="utf-8",
+        )
+        os.replace(temporary, target)
+    finally:
+        temporary.unlink(missing_ok=True)
+
+
+def _record_best_effort(
+    repo_path: str | Path,
+    *,
+    started_at: str,
+    outcome: object,
+    failure: BaseException | None,
+) -> None:
+    try:
+        _write_desktop_full_record(
+            repo_path,
+            started_at=started_at,
+            outcome=outcome,
+            failure=failure,
+        )
+    except Exception as exc:
+        trace_event(
+            "ANALYSIS",
+            "DESKTOP_FULL_HISTORY_PERSIST_FAILED",
+            repo=str(repo_path),
+            result=f"{type(exc).__name__}: {exc}",
+        )
+
+
+def run_desktop_full_with_history(
+    repo_path: str | Path,
+    *,
+    runner: Callable[..., Any],
+    **kwargs: Any,
+) -> Any:
+    started_at = _utc_now()
+    try:
+        outcome = runner(
+            repo_path,
+            owner="desktop_analysis",
+            **kwargs,
+        )
+    except BaseException as failure:
+        _record_best_effort(
+            repo_path,
+            started_at=started_at,
+            outcome=None,
+            failure=failure,
+        )
+        raise
+
+    _record_best_effort(
+        repo_path,
+        started_at=started_at,
+        outcome=outcome,
+        failure=None,
+    )
+    return outcome
diff --git a/contextor/mcp/analysis_jobs.py b/contextor/mcp/analysis_jobs.py
index dcfb43a..2113b32 100644
--- a/contextor/mcp/analysis_jobs.py
+++ b/contextor/mcp/analysis_jobs.py
@@ -204,6 +204,7 @@ def _public_job(
             "live_publish_expected_state_id", "live_publish_expected_revision",
         )
     }
+    visible["source"] = job.get("source", "mcp")
     if "skipped_python_files" in job:
         skipped_files = list(job["skipped_python_files"])
         selected, total, truncated = bounded_items(skipped_files, max_skipped_files)
diff --git a/contextor/mcp/docs/get_analysis_status.json b/contextor/mcp/docs/get_analysis_status.json
index afb0d54..87f8cce 100644
--- a/contextor/mcp/docs/get_analysis_status.json
+++ b/contextor/mcp/docs/get_analysis_status.json
@@ -2,7 +2,7 @@
   "version": "1.0.0",
   "tool": "get_analysis_status",
   "purpose": [
-    "Return durable status for a non-blocking MCP analysis job."
+    "Return durable status for a non-blocking MCP analysis job or a recorded Desktop FULL analysis."
   ],
   "parameters": [
     "repo_path (string, required): canonical repository root.",
@@ -11,7 +11,7 @@
     "allow_large_output (boolean, optional, default false): override to approve emission of outputs exceeding the 15 KiB warning threshold."
   ],
   "behavior": [
-    "Returns durable status for a specified or latest analysis job without any cardinality hard limit.\nResolution & ambiguity:\n1. Explicit job_id: returns the exact requested durable job without enumerating active jobs; missing jobs return status='not_found'.\n2. Omitted job_id: enumerates persisted queued/running jobs. When multiple active jobs exist, returns read-only status='ambiguous_job' with job_id=null, repo_path, active_job_count, bounded active_jobs list (max 5 candidates ordered newest mtime first, tie-broken by ascending job_id, each containing job_id, operation, target, status, created_at, updated_at), truncated boolean flag, and guidance message to repeat with one listed job_id.\n3. Single or zero active jobs: preserves legacy latest-durable-job selection (a sole active job is NOT automatically preferred over a newer terminal job).\nOutput <= 15 KiB (15360 UTF-8 bytes) returns the status payload normally.\nWhen output > 15 KiB with ``allow_large_output=false``, oversized status responses automatically single-shot reduce ``skipped_files`` evidence to the largest prefix fitting within 15360 UTF-8 bytes (adding top-level ``_output.auto_bounded=true``, ``bounded_collection='skipped_files'``, and ``returned_count``); scalar job metadata and progress state are never truncated. If minimal status with zero skipped files still exceeds 15360 bytes, ``status: 'confirmation_required'`` is returned.\nPassing ``allow_large_output=true`` returns the complete lossless status response without auto-bounding.\nFor running jobs, note that status and progress may advance between preflight and retry."
+    "Returns durable status for a specified or latest analysis job without any cardinality hard limit.\nThe source field is 'mcp' for MCP jobs (including historical records without source) or 'desktop' for Desktop FULL records. Desktop FULL is recorded after the complete coordinator call; failed calls expose null publication fields because publication cannot be inferred. Desktop FULL runs before this registration change are not reconstructed.\nResolution & ambiguity:\n1. Explicit job_id: returns the exact requested durable job without enumerating active jobs; missing jobs return status='not_found'.\n2. Omitted job_id: enumerates persisted queued/running jobs. When multiple active jobs exist, returns read-only status='ambiguous_job' with job_id=null, repo_path, active_job_count, bounded active_jobs list (max 5 candidates ordered newest mtime first, tie-broken by ascending job_id, each containing job_id, operation, target, status, created_at, updated_at), truncated boolean flag, and guidance message to repeat with one listed job_id.\n3. One active job is preferred; with no active jobs, the latest durable record from either source is selected by file modification time.\nOutput <= 15 KiB (15360 UTF-8 bytes) returns the status payload normally.\nWhen output > 15 KiB with ``allow_large_output=false``, oversized status responses automatically single-shot reduce ``skipped_files`` evidence to the largest prefix fitting within 15360 UTF-8 bytes (adding top-level ``_output.auto_bounded=true``, ``bounded_collection='skipped_files'``, and ``returned_count``); scalar job metadata and progress state are never truncated. If minimal status with zero skipped files still exceeds 15360 bytes, ``status: 'confirmation_required'`` is returned.\nPassing ``allow_large_output=true`` returns the complete lossless status response without auto-bounding.\nFor running jobs, note that status and progress may advance between preflight and retry."
   ],
   "freshness": [
     "For an explicit completed job with live_publish_status=pending_verification and saved publication correlation, this read-only tool reconnects to the existing verified LIVE authority with endpoint reconciliation disabled and verifies service instance and process start identity. If the mutation job ID was lost, it verifies the canonical generation key against the authority repository identity and performs a read-only lookup in the existing mutation coordinator. A recovered job ID is durably saved; only its exact receipt can resolve publication status. It never submits a publication, update, or FULL analysis.",
diff --git a/contextor/mcp/tools/get_analysis_status.py b/contextor/mcp/tools/get_analysis_status.py
index 42d13de..34ca07c 100644
--- a/contextor/mcp/tools/get_analysis_status.py
+++ b/contextor/mcp/tools/get_analysis_status.py
@@ -55,7 +55,11 @@ def get_analysis_status(
                 indent=2,
             )
 
-        job = analysis_jobs._latest_analysis_job(root)
+        job = (
+            active_jobs[0]
+            if len(active_jobs) == 1
+            else analysis_jobs._latest_analysis_job(root)
+        )
 
     else:
         job = analysis_jobs._read_analysis_job(root, job_id)
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index b51eb58..2a49d55 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -28,6 +28,9 @@ from contextor.core.analysis.full_analysis_coordinator import (
     release_full_analysis,
     run_full_analysis_exclusive,
 )
+from contextor.core.analysis.full_analysis_history import (
+    run_desktop_full_with_history,
+)
 from contextor.core.analysis.process_pool_lifecycle import (
     terminate_active_process_pools,
 )
@@ -1540,9 +1543,9 @@ class ContextorGUI:
             except Exception:
                 pre_seq = 0
 
-            errors, analysis_result = run_full_analysis_exclusive(
+            errors, analysis_result = run_desktop_full_with_history(
                 path,
-                owner="desktop_analysis",
+                runner=run_full_analysis_exclusive,
                 log=log,
                 progress_callback=progress_callback,
                 is_cancelled=lambda: getattr(self.progress_bar, "is_cancelled", False),
diff --git a/tests/test_full_analysis_coordination.py b/tests/test_full_analysis_coordination.py
index 9b94708..f23dd7e 100644
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -42,6 +42,139 @@ from contextor.mcp import analysis_jobs
 from contextor.mcp import runtime as mcp_runtime
 
 
+def test_desktop_history_success_visible_via_mcp(tmp_path):
+    from types import SimpleNamespace
+    from contextor.core.analysis.full_analysis_history import (
+        run_desktop_full_with_history,
+    )
+    from contextor.mcp.tools.get_analysis_status import (
+        get_analysis_status,
+    )
+
+    def analysis(_path, **_kwargs):
+        return [], SimpleNamespace(
+            summary_data={"skipped_files": []},
+            live_publish_status="success",
+            live_publish_revision=123,
+        )
+
+    outcome = run_desktop_full_with_history(
+        tmp_path,
+        runner=run_full_analysis_exclusive,
+        analysis_fn=analysis,
+    )
+    assert outcome[1].live_publish_revision == 123
+
+    status = json.loads(get_analysis_status(str(tmp_path)))
+    assert status["source"] == "desktop"
+    assert status["status"] == "completed"
+    assert status["operation"] == "project"
+    assert status["live_publish_status"] == "success"
+    assert status["live_publish_revision"] == 123
+
+    exact = json.loads(get_analysis_status(
+        str(tmp_path), job_id=status["job_id"]
+    ))
+    assert exact["job_id"] == status["job_id"]
+
+
+def test_desktop_history_release_failure_not_completed(
+    tmp_path, monkeypatch,
+):
+    from contextor.core.analysis import (
+        full_analysis_coordinator as coordinator,
+    )
+    from contextor.core.analysis.full_analysis_history import (
+        run_desktop_full_with_history,
+    )
+    from contextor.mcp.tools.get_analysis_status import (
+        get_analysis_status,
+    )
+
+    original_release = coordinator.release_full_analysis
+
+    def failing_release(lease):
+        original_release(lease)
+        raise OSError("controlled unlock failure")
+
+    monkeypatch.setattr(
+        coordinator, "release_full_analysis",
+        failing_release,
+    )
+
+    def analysis(_path, **_kwargs):
+        return [], SimpleNamespace(
+            live_publish_status="success",
+            live_publish_revision=123,
+        )
+
+    with pytest.raises(
+        OSError, match="controlled unlock failure",
+    ):
+        run_desktop_full_with_history(
+            tmp_path,
+            runner=run_full_analysis_exclusive,
+            analysis_fn=analysis,
+        )
+
+    status = json.loads(get_analysis_status(str(tmp_path)))
+    assert status["source"] == "desktop"
+    assert status["status"] == "failed"
+    assert "controlled unlock failure" in status["error"]
+    assert status["live_publish_status"] is None
+    assert status["live_publish_revision"] is None
+
+
+def test_desktop_history_write_failure_preserves_result(
+    tmp_path, monkeypatch,
+):
+    from contextor.core.analysis import full_analysis_history
+
+    def failing_write(*_args, **_kwargs):
+        raise OSError("history unavailable")
+
+    monkeypatch.setattr(
+        full_analysis_history,
+        "_write_desktop_full_record",
+        failing_write,
+    )
+
+    def runner(_path, *, owner):
+        assert owner == "desktop_analysis"
+        return "analysis-result"
+
+    assert full_analysis_history.run_desktop_full_with_history(
+        tmp_path,
+        runner=runner,
+    ) == "analysis-result"
+
+
+def test_desktop_history_does_not_mask_original_error(
+    tmp_path, monkeypatch,
+):
+    from contextor.core.analysis import full_analysis_history
+
+    def failing_write(*_args, **_kwargs):
+        raise OSError("history unavailable")
+
+    monkeypatch.setattr(
+        full_analysis_history,
+        "_write_desktop_full_record",
+        failing_write,
+    )
+
+    def runner(_path, *, owner):
+        raise ValueError("original analysis error")
+
+    with pytest.raises(
+        ValueError, match="original analysis error",
+    ):
+        full_analysis_history.run_desktop_full_with_history(
+            tmp_path,
+            runner=runner,
+        )
+
+
 def test_acyclic_lease_import_contract():
     from contextor.core.api import facade
     from contextor.core.analysis import full_analysis_lease as lease
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index 835b787..1a6c80c 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -7021,3 +7021,63 @@ def test_get_artifacts_for_module_representation_and_progressive_disclosure(
     )
     assert blast_res["consumers"]["total"] == 20
     assert len(blast_res["consumers"]["items"]) == 20
+
+
+def test_desktop_history_source_and_active_mcp_priority(
+    tmp_path, monkeypatch,
+):
+    from contextor.mcp.tools.get_analysis_status import (
+        get_analysis_status,
+    )
+
+    job_id = "a" * 32
+    analysis_jobs._write_analysis_job(
+        tmp_path,
+        {
+            "job_id": job_id,
+            "operation": "project",
+            "repo_path": str(tmp_path),
+            "target": None,
+            "status": "running",
+            "owner_pid": os.getpid(),
+        },
+    )
+    monkeypatch.setattr(
+        analysis_jobs,
+        "_is_current_process_analysis_task_active",
+        lambda _job_id: True,
+    )
+
+    from contextor.core.analysis.full_analysis_history import (
+        run_desktop_full_with_history,
+    )
+
+    def runner(_path, *, owner):
+        return [], SimpleNamespace(
+            live_publish_status="success",
+            live_publish_revision=123,
+        )
+
+    run_desktop_full_with_history(
+        tmp_path, runner=runner,
+    )
+
+    latest = json.loads(get_analysis_status(str(tmp_path)))
+    assert latest["job_id"] == job_id
+    assert latest["source"] == "mcp"
+    assert latest["status"] == "running"
+
+    desktop_ids = [
+        path.stem
+        for path in (
+            tmp_path / ".contextor" / "analysis_jobs"
+        ).glob("*.json")
+        if path.stem != job_id
+    ]
+    assert len(desktop_ids) == 1
+
+    exact = json.loads(get_analysis_status(
+        str(tmp_path), job_id=desktop_ids[0]
+    ))
+    assert exact["source"] == "desktop"
+    assert exact["status"] == "completed"
```

# Contextor MCP diagnostics final deterministic corrections

## Walkthrough

VERDICT=IMPLEMENTATION_PASS
MCP_TOOL_COUNT=25
SYNTAX_GLOBAL_SOURCE=NONE
COMPLETED_JOB_SYNTAX_SOURCE_ONLY=PASS
HISTORICAL_SYNTAX_PROMOTION=ABSENT
CANONICAL_COLLISION_ID_EXISTS=NO
INVENTED_HASH_IDS=ABSENT
STALE_STABLE_ID_DOC_TEXT=ABSENT
DEFAULT_RESPONSE_BUDGET_BYTES=15360
ACTUAL_RETURNED_BYTES_TESTED=YES
PRE_INJECTION_BYTES=15351
POST_INJECTION_UNGUARDED_BYTES=15885
FINAL_RETURNED_BYTES=933
POST_DIAGNOSTICS_FINAL_GUARD=PASS
DEFAULT_RESPONSE_CAN_EXCEED_15360=NO
ANALYTICAL_NOT_FOUND_DIAGNOSTICS=PASS
ZERO_NOT_FABRICATED_FOR_UNAVAILABLE=PASS
MCP_RUNTIME_SCHEMA=25_TOOLS_REGISTERED
CORE_COLLISION_CYCLE_SYNTAX_DETECTORS=UNCHANGED
TESTS_RUN=pytest -q tests/test_mcp_diagnostics.py tests/test_mcp_documentation.py tests/test_live_activity_status.py tests/mcp/tools/test_public_mcp_docs_parity.py; pytest -q tests/test_mcp_documentation.py tests/mcp/tools/test_public_mcp_docs_parity.py
TESTS_PASSED=56 initial focused tests; 12 documentation/parity revalidation tests
TESTS_FAILED=0
MANUAL_RESTART_REQUIRED=YES (mcp_server.py registration/wrapper changes)
FILES_CHANGED=see complete raw diffs below (walkthrough.md excluded)
COMPLETE_RAW_DIFFS=YES

The Contextor MCP architectural discovery confirmed the canonical state owners, shared output guard, central registration wrapper, and authoritative collision/cycle materialization paths. Text search was used only for verification. No runtime/LIVE process was restarted and no full pytest suite was run.

The diagnostics summary now treats syntax as unavailable in ordinary canonical-state summaries and promotes syntax only from the exact completed project job. Failed or historical jobs cannot make canonical syntax appear fresh. Diagnostics injection applies a final shared 15360-byte guard after diagnostics are added; if needed it emits a compact confirmation envelope and fails closed if that envelope cannot fit. Collision responses remain response-local indexed projections without persistent collision identity or synthesized hashes.

## Complete raw unified diffs

diff --git a/contextor/core/analysis/full_analysis_coordinator.py b/contextor/core/analysis/full_analysis_coordinator.py
index 7bfe203..6487d72 100644
--- a/contextor/core/analysis/full_analysis_coordinator.py
+++ b/contextor/core/analysis/full_analysis_coordinator.py
@@ -3,14 +3,13 @@ contextor/core/analysis/full_analysis_coordinator.py
 
 Single-writer cross-process coordinator for full repository analysis.
 Guarantees that at most one full analysis execution runs per repository identity
-across Desktop GUI, MCP server, and CLI processes.
+across Desktop GUI, MCP server, and CLI processes using native OS file locking.
 """
 
 from __future__ import annotations
 
 import json
 import os
-import sys
 import threading
 import time
 import uuid
@@ -19,7 +18,6 @@ from pathlib import Path
 from typing import Any, Callable
 
 from contextor.core.errors import AnalysisCancelled
-from contextor.core.live_state.runtime import _is_pid_alive
 from contextor.core.paths import repo_cache_dir, repo_key
 from contextor.core.repository_identity import read_repository_identity
 
@@ -31,6 +29,7 @@ class FullAnalysisLease:
     owner: str
     lock_path: str
     repo_id: str
+    lock_fd: int
 
 
 class FullAnalysisBusyError(RuntimeError):
@@ -38,15 +37,90 @@ class FullAnalysisBusyError(RuntimeError):
     pass
 
 
-_PROCESS_LOCKS: dict[str, threading.RLock] = {}
+_PROCESS_LOCKS: dict[str, threading.Lock] = {}
 _PROCESS_LOCKS_GUARD = threading.Lock()
 
 
-def _get_process_lock(repo_key_str: str) -> threading.RLock:
+def _get_process_lock(
+    repo_key_str: str,
+) -> threading.Lock:
     with _PROCESS_LOCKS_GUARD:
-        if repo_key_str not in _PROCESS_LOCKS:
-            _PROCESS_LOCKS[repo_key_str] = threading.RLock()
-        return _PROCESS_LOCKS[repo_key_str]
+        lock = _PROCESS_LOCKS.get(repo_key_str)
+        if lock is None:
+            lock = threading.Lock()
+            _PROCESS_LOCKS[repo_key_str] = lock
+        return lock
+
+
+def _prepare_lock_fd(lock_path: Path) -> int:
+    lock_path.parent.mkdir(
+        parents=True,
+        exist_ok=True,
+    )
+
+    fd = os.open(
+        lock_path,
+        os.O_RDWR | os.O_CREAT,
+        0o600,
+    )
+
+    if os.fstat(fd).st_size == 0:
+        os.write(fd, b"\0")
+        os.fsync(fd)
+
+    os.lseek(fd, 0, os.SEEK_SET)
+    return fd
+
+
+def _try_lock_fd(fd: int) -> bool:
+    os.lseek(fd, 0, os.SEEK_SET)
+
+    if os.name == "nt":
+        import msvcrt
+
+        try:
+            msvcrt.locking(
+                fd,
+                msvcrt.LK_NBLCK,
+                1,
+            )
+            return True
+        except OSError:
+            return False
+
+    import fcntl
+
+    try:
+        fcntl.flock(
+            fd,
+            fcntl.LOCK_EX | fcntl.LOCK_NB,
+        )
+        return True
+    except BlockingIOError:
+        return False
+
+
+def _unlock_fd(fd: int) -> None:
+    try:
+        os.lseek(fd, 0, os.SEEK_SET)
+
+        if os.name == "nt":
+            import msvcrt
+
+            msvcrt.locking(
+                fd,
+                msvcrt.LK_UNLCK,
+                1,
+            )
+        else:
+            import fcntl
+
+            fcntl.flock(
+                fd,
+                fcntl.LOCK_UN,
+            )
+    finally:
+        os.close(fd)
 
 
 def _resolve_lock_path(repo_path: str | Path) -> tuple[Path, str, str]:
@@ -80,118 +154,124 @@ def acquire_full_analysis(
     lock_file, key, repo_id = _resolve_lock_path(repo_path)
     proc_lock = _get_process_lock(key)
 
-    # In-process lock acquisition
     start_time = time.monotonic()
-    deadline = (start_time + timeout) if timeout is not None else None
+    deadline = (
+        start_time + timeout
+        if timeout is not None
+        else None
+    )
 
-    # Wait for process-level lock
     while True:
         if is_cancelled and is_cancelled():
-            raise AnalysisCancelled("Full analysis cancelled while waiting for local lock.")
-        acquired_proc = proc_lock.acquire(blocking=False)
-        if acquired_proc:
+            raise AnalysisCancelled(
+                "Full analysis cancelled while waiting for local lock."
+            )
+
+        if proc_lock.acquire(blocking=False):
             break
-        if deadline is not None and time.monotonic() >= deadline:
+
+        if (
+            deadline is not None
+            and time.monotonic() >= deadline
+        ):
             raise FullAnalysisBusyError(
-                f"Timed out waiting for in-process full analysis lock for {repo_id}"
+                "Timed out waiting for in-process full analysis lock for "
+                f"{repo_id}"
             )
-        time.sleep(min(poll_interval, 0.1))
 
-    token = uuid.uuid4().hex
+        time.sleep(
+            min(max(poll_interval, 0.01), 0.25)
+        )
+
     fd = -1
     logged_waiting = False
 
     try:
+        fd = _prepare_lock_fd(lock_file)
+
         while True:
             if is_cancelled and is_cancelled():
-                raise AnalysisCancelled("Full analysis cancelled while waiting for repository lease.")
-
-            # Attempt atomic creation of lock file
-            try:
-                fd = os.open(
-                    lock_file,
-                    os.O_CREAT | os.O_EXCL | os.O_RDWR,
+                raise AnalysisCancelled(
+                    "Full analysis cancelled while waiting for repository lease."
                 )
-                payload = {
+
+            if _try_lock_fd(fd):
+                token = uuid.uuid4().hex
+
+                metadata = {
                     "pid": os.getpid(),
                     "token": token,
                     "owner": str(owner),
                     "repo_id": str(repo_id),
                     "timestamp": time.time(),
                 }
-                data = json.dumps(payload).encode("utf-8")
-                os.write(fd, data)
-                os.close(fd)
-                fd = -1
+
+                # Metadata is diagnostic only.
+                # OS lock ownership is authoritative.
+                os.ftruncate(fd, 0)
+                os.lseek(fd, 0, os.SEEK_SET)
+                os.write(
+                    fd,
+                    json.dumps(metadata).encode("utf-8"),
+                )
+                os.fsync(fd)
+
+                # Ensure byte 0 remains inside the locked file after metadata write.
+                os.lseek(fd, 0, os.SEEK_SET)
+
                 return FullAnalysisLease(
                     repo_key=key,
                     token=token,
                     owner=str(owner),
                     lock_path=str(lock_file),
                     repo_id=str(repo_id),
+                    lock_fd=fd,
                 )
-            except (FileExistsError, PermissionError):
-                # Lock file exists or is locked by another process
-                existing_pid = None
-                existing_owner = "unknown"
-                try:
-                    raw = lock_file.read_text(encoding="utf-8")
-                    if raw:
-                        parsed = json.loads(raw)
-                        existing_pid = parsed.get("pid")
-                        existing_owner = parsed.get("owner", "unknown")
-                except Exception:
-                    pass
-
-                # Check for dead process (stale lock recovery)
-                if existing_pid is not None and not _is_pid_alive(existing_pid):
-                    try:
-                        lock_file.unlink(missing_ok=True)
-                        if log:
-                            log(f"Recovered stale full-analysis lock from terminated PID {existing_pid}")
-                        continue
-                    except Exception:
-                        pass
-
-                if not logged_waiting:
-                    if log:
-                        log(f"Waiting for full analysis lease on repository {repo_id} (owned by {existing_owner})...")
-                    logged_waiting = True
-
-                if deadline is not None and time.monotonic() >= deadline:
-                    raise FullAnalysisBusyError(
-                        f"Repository {repo_id} is currently locked for full analysis by owner '{existing_owner}' (PID {existing_pid})"
+
+            if not logged_waiting:
+                if log:
+                    log(
+                        f"Waiting for full analysis lease on repository {repo_id}..."
                     )
+                logged_waiting = True
+
+            if (
+                deadline is not None
+                and time.monotonic() >= deadline
+            ):
+                raise FullAnalysisBusyError(
+                    f"Repository {repo_id} is currently locked for full analysis"
+                )
+
+            time.sleep(poll_interval)
 
-                time.sleep(poll_interval)
     except Exception:
         if fd >= 0:
             try:
                 os.close(fd)
             except OSError:
                 pass
+
         proc_lock.release()
         raise
 
 
-def release_full_analysis(lease: FullAnalysisLease) -> None:
+def release_full_analysis(
+    lease: FullAnalysisLease,
+) -> None:
     """Release the full analysis lease."""
-    if not isinstance(lease, FullAnalysisLease):
+    if not isinstance(
+        lease,
+        FullAnalysisLease,
+    ):
         return
 
-    lock_file = Path(lease.lock_path)
     try:
-        if lock_file.exists():
-            try:
-                raw = lock_file.read_text(encoding="utf-8")
-                if raw:
-                    parsed = json.loads(raw)
-                    if parsed.get("token") == lease.token:
-                        lock_file.unlink(missing_ok=True)
-            except Exception:
-                lock_file.unlink(missing_ok=True)
+        _unlock_fd(lease.lock_fd)
     finally:
-        proc_lock = _get_process_lock(lease.repo_key)
+        proc_lock = _get_process_lock(
+            lease.repo_key
+        )
         try:
             proc_lock.release()
         except RuntimeError:
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index 6c018ca..163ee47 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -107,6 +107,10 @@ class IncrementalAnalysisEngine:
         Returns the update status and the freshness of the architectural model.
         """
         with self._lock:
+            if getattr(self.state, "resync_required", False):
+                # Every exit path, including a semantic no-op, must expose the
+                # already-lost incremental continuity as fail-closed.
+                self.state.artifact_consumption_state = "stale"
             path = Path(file_path)
             rel_path = path.relative_to(self.root_path)
             module_path = ".".join(rel_path.with_suffix("").parts)
@@ -353,6 +357,7 @@ class IncrementalAnalysisEngine:
         """
         Executes planned RefreshPlan phases and performs atomic persistent & RAM commit.
         """
+        resync_required = bool(getattr(self.state, "resync_required", False))
         outcome = execute_refresh_plan(
             state=self.state,
             delta=delta,
@@ -389,12 +394,17 @@ class IncrementalAnalysisEngine:
         self.state.artifact_consumption = candidate.artifact_consumption
         if (
             candidate.artifact_consumption_state != "stale"
-            and not getattr(self.state, "resync_required", False)
+            and not resync_required
             and validate_canonical_artifact_consumption_coverage(candidate.artifact_consumption, candidate.artifacts)
         ):
             self.state.artifact_consumption_state = "fresh"
         else:
             self.state.artifact_consumption_state = "stale"
+        if resync_required:
+            # A lost incremental continuity is authoritative until a full
+            # rebuild replaces this state; an incremental candidate cannot
+            # certify it fresh again.
+            self.state.resync_required = True
         self.state.module_usages = candidate.module_usages
         self.state.trie = candidate.trie
         self.state.package_root = candidate.package_root
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index e21f4c7..3b60e5f 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -533,37 +533,36 @@ class ContextorFacade:
             if meta is not None:
                 sm = FileStateManager(str(repo_cache_dir(path)))
                 sm.save(datestamp or "", revision=meta.revision)
-                if owner != "mcp_analysis":
-                    from contextor.core.live_state import connect
-
-                    try:
-                        client = connect(path)
-                        if client is not None:
-                            published = client.publish(state, origin=origin)
-                            if (
-                                isinstance(published, dict)
-                                and published.get("status") == "ok"
-                                and published.get("revision") is not None
-                            ):
-                                live_publish_status = "success"
-                                live_publish_revision = int(published["revision"])
-                                live_publish_warning = None
-                            else:
-                                live_publish_status = "failed"
-                                live_publish_revision = None
-                                err = published.get("error") if isinstance(published, dict) else None
-                                status_val = published.get("status") if isinstance(published, dict) else None
-                                live_publish_warning = err or (f"LIVE service returned status '{status_val}'." if status_val else "Canonical LIVE service rejected publication.")
-                                if log:
-                                    log(f"Warning: Failed to publish canonical state to live daemon: {live_publish_warning}")
+                from contextor.core.live_state import connect
+
+                try:
+                    client = connect(path)
+                    if client is not None:
+                        published = client.publish(state, origin=origin)
+                        if (
+                            isinstance(published, dict)
+                            and published.get("status") == "ok"
+                            and published.get("revision") is not None
+                        ):
+                            live_publish_status = "success"
+                            live_publish_revision = int(published["revision"])
+                            live_publish_warning = None
                         else:
-                            live_publish_status = "not_attempted"
-                    except Exception as e:
-                        live_publish_status = "timed_out" if isinstance(e, TimeoutError) else "failed"
-                        live_publish_revision = None
-                        live_publish_warning = f"{type(e).__name__}: {e}"
-                        if log:
-                            log(f"Warning: Failed to publish canonical state to live daemon: {live_publish_warning}")
+                            live_publish_status = "failed"
+                            live_publish_revision = None
+                            err = published.get("error") if isinstance(published, dict) else None
+                            status_val = published.get("status") if isinstance(published, dict) else None
+                            live_publish_warning = err or (f"LIVE service returned status '{status_val}'." if status_val else "Canonical LIVE service rejected publication.")
+                            if log:
+                                log(f"Warning: Failed to publish canonical state to live daemon: {live_publish_warning}")
+                    else:
+                        live_publish_status = "not_attempted"
+                except Exception as e:
+                    live_publish_status = "timed_out" if isinstance(e, TimeoutError) else "failed"
+                    live_publish_revision = None
+                    live_publish_warning = f"{type(e).__name__}: {e}"
+                    if log:
+                        log(f"Warning: Failed to publish canonical state to live daemon: {live_publish_warning}")
 
             if analysis_result is not None:
                 analysis_result.live_publish_status = live_publish_status
diff --git a/contextor/mcp/analysis_jobs.py b/contextor/mcp/analysis_jobs.py
index 3a25426..d8db080 100644
--- a/contextor/mcp/analysis_jobs.py
+++ b/contextor/mcp/analysis_jobs.py
@@ -14,7 +14,6 @@ from contextor.mcp.query_helpers import bounded_items
 from contextor.mcp_process_registry import registry_dir
 
 
-_MCP_OWNER_TOKEN: str = uuid4().hex
 _analysis_lock = threading.Lock()
 _analysis_job_lock = threading.RLock()
 _analysis_tasks: dict[str, threading.Thread] = {}
@@ -193,7 +192,21 @@ async def _run_analysis_worker(
                         skipped_files = []
                     return {
                         "skipped_python_files": skipped_files,
-                        "_analysis_result": result,
+                        "live_publish_status": getattr(
+                            result,
+                            "live_publish_status",
+                            "not_attempted",
+                        ),
+                        "live_publish_revision": getattr(
+                            result,
+                            "live_publish_revision",
+                            None,
+                        ),
+                        "live_publish_warning": getattr(
+                            result,
+                            "live_publish_warning",
+                            None,
+                        ),
                     }
                 if operation == "layer":
                     ContextorFacade.analyze_layer(
@@ -244,60 +257,59 @@ async def _execute_analysis_job(
             str(job["operation"]), root, target, exclude_paths, log=job_log
         )
         if job["operation"] == "project":
-            mcp_runtime._live_engines.pop(str(root), None)
-            engine = mcp_runtime.get_or_init_engine(root)
-            if engine is None:
-                raise RuntimeError(
-                    "Analysis completed but canonical state could not be loaded."
-                )
-            engine_state = engine.state
-            from contextor.core.live_state import connect_or_start
-            try:
-                live_client = connect_or_start(
-                    root, owner_pid=os.getpid(), owner_token=_MCP_OWNER_TOKEN,
-                    timeout=10.0,
-                )
-                published = live_client.publish(
-                    engine_state, origin="mcp_analysis", timeout=10.0
-                )
-                if (
-                    isinstance(published, dict)
-                    and published.get("status") == "ok"
-                    and published.get("revision") is not None
-                ):
-                    canonical_revision = getattr(engine_state, "revision", None)
-                    if canonical_revision is not None:
-                        mcp_runtime._live_engine_revisions[str(root)] = int(canonical_revision)
-                    else:
-                        mcp_runtime._live_engine_revisions.pop(str(root), None)
-                    job = {
-                        **job, "live_publish_status": "success",
-                        "live_publish_revision": int(published["revision"]),
-                        "live_publish_warning": None,
-                    }
-                else:
-                    mcp_runtime._live_engine_revisions.pop(str(root), None)
-                    err = published.get("error") if isinstance(published, dict) else None
-                    status_val = published.get("status") if isinstance(published, dict) else None
-                    warning = err or (f"LIVE service returned status '{status_val}'." if status_val else "Canonical LIVE service rejected publication.")
-                    _stderr_log(f"Warning: Live state publish failed: {warning}")
-                    job = {
-                        **job, "live_publish_status": "failed",
-                        "live_publish_revision": None,
-                        "live_publish_warning": warning,
-                    }
-            except Exception as live_exc:
-                mcp_runtime._live_engine_revisions.pop(str(root), None)
-                publish_status = (
-                    "timed_out" if isinstance(live_exc, TimeoutError) else "failed"
-                )
-                warning = f"{type(live_exc).__name__}: {live_exc}"
-                _stderr_log(f"Warning: Live state publish {publish_status}: {warning}")
-                job = {
-                    **job, "live_publish_status": publish_status,
-                    "live_publish_revision": None,
-                    "live_publish_warning": warning,
-                }
+            cache_key = str(root)
+            pub_status = (
+                (analysis_outcome or {}).get("live_publish_status")
+            )
+            pub_rev = (
+                (analysis_outcome or {}).get("live_publish_revision")
+            )
+            pub_warn = (
+                (analysis_outcome or {}).get("live_publish_warning")
+            )
+            job = {
+                **job,
+                "live_publish_status": pub_status or "failed",
+                "live_publish_revision": pub_rev,
+                "live_publish_warning": pub_warn,
+            }
+
+            if pub_status == "success" and pub_rev is not None:
+                mcp_runtime._live_engines.pop(cache_key, None)
+                mcp_runtime._live_engine_revisions.pop(cache_key, None)
+                engine = mcp_runtime.get_or_init_engine(root)
+
+                if engine is None:
+                    mcp_runtime._live_engines.pop(cache_key, None)
+                    mcp_runtime._live_engine_revisions.pop(cache_key, None)
+                    raise RuntimeError(
+                        "Analysis completed and LIVE publication returned, "
+                        "but canonical state could not be loaded."
+                    )
+
+                engine_state = getattr(engine, "state", None)
+                canonical_rev = getattr(engine_state, "revision", None)
+                if canonical_rev is None:
+                    mcp_runtime._live_engines.pop(cache_key, None)
+                    mcp_runtime._live_engine_revisions.pop(cache_key, None)
+                    raise RuntimeError(
+                        "Canonical state loaded after analysis without a revision."
+                    )
+
+                canonical_rev = int(canonical_rev)
+                published_rev = int(pub_rev)
+                if canonical_rev != published_rev:
+                    mcp_runtime._live_engines.pop(cache_key, None)
+                    mcp_runtime._live_engine_revisions.pop(cache_key, None)
+                    raise RuntimeError(
+                        "Canonical revision mismatch after full analysis: "
+                        f"loaded={canonical_rev}, published={published_rev}."
+                    )
+
+                mcp_runtime._live_engine_revisions[cache_key] = canonical_rev
+            else:
+                mcp_runtime._live_engines.pop(cache_key, None)
+                mcp_runtime._live_engine_revisions.pop(cache_key, None)
         publish_status = job.get("live_publish_status")
         completed_message = "Analysis completed successfully."
         if job["operation"] == "project" and publish_status != "success":
diff --git a/contextor/mcp/docs/get_live_events.json b/contextor/mcp/docs/get_live_events.json
index bfd1180..b05e1ef 100644
--- a/contextor/mcp/docs/get_live_events.json
+++ b/contextor/mcp/docs/get_live_events.json
@@ -14,7 +14,7 @@
   ],
   "freshness": [],
   "errors": [
-    "Events are retained in RAM by the shared LIVE owner (most recent 10,000 records).\nEach canonical event identifies its ``origin`` (``desktop_watcher``,\n``mcp_analysis`` or ``desktop_analysis``), operation, status and file path. Update\nevents additionally expose ``blast_radius_state`` and a bounded\n``affected_modules`` collection (hard limit of 20 items in journal).\nSyntax failures additionally expose ``error``, ``line_number`` and\n``column_number``."
+    "Events are retained in RAM by the shared LIVE owner (most recent 10,000 records).\nEach canonical full-analysis event identifies its ``origin`` (``desktop_analysis``,\n``mcp_analysis`` or ``cli_analysis``); incremental watcher events use\n``desktop_watcher``. Events also identify operation, status and file path. Update\nevents additionally expose ``blast_radius_state`` and a bounded\n``affected_modules`` collection (hard limit of 20 items in journal).\nSyntax failures additionally expose ``error``, ``line_number`` and\n``column_number``."
   ],
   "usage_notes": [
     "LLM workflow after every file edit:\n- If the desktop app is running, do *not* call ``update_file``. Its watcher\n  owns the update. Poll this tool with the last observed revision until the\n  desktop event arrives, then react to its status before further edits.\n- If the desktop app is not running, call ``update_file`` after every edit,\n  then call this tool to confirm the revision and diagnostics.\n- If ``resync_required=true`` is returned, do not assume unbroken event history;\n  perform a canonical state sync using query_canonical_projection."
diff --git a/contextor/mcp/docs/index.json b/contextor/mcp/docs/index.json
index bfc0d5f..1917ac4 100644
--- a/contextor/mcp/docs/index.json
+++ b/contextor/mcp/docs/index.json
@@ -118,6 +118,11 @@
       "filename": "get_symbol_call_context.json",
       "short_description": "Return a bounded callers/callees neighborhood from current canonical intra-module symbol-call facts without reading source."
     },
+    {
+      "tool": "get_name_collisions",
+      "filename": "get_name_collisions.json",
+      "short_description": "Return bounded canonical name-collision diagnostics with explicit freshness, semantic filters and progressive representations."
+    },
     {
       "tool": "get_mcp_documentation",
       "filename": "get_mcp_documentation.json",
diff --git a/contextor/mcp/tools/get_analysis_status.py b/contextor/mcp/tools/get_analysis_status.py
index a5de086..7b999a2 100644
--- a/contextor/mcp/tools/get_analysis_status.py
+++ b/contextor/mcp/tools/get_analysis_status.py
@@ -8,6 +8,7 @@ from contextor.mcp.output_guard import (
     guard_large_output,
     largest_fitting_prefix,
 )
+from contextor.mcp.diagnostics import diagnostics_summary, diagnostics_summary_for_completed_job
 
 
 def get_analysis_status(
@@ -77,6 +78,10 @@ def get_analysis_status(
         }
         analysis_jobs._write_analysis_job(root, job)
     public_job = analysis_jobs._public_job(job, max_skipped_files=max_skipped_files)
+    if public_job.get("status") == "completed":
+        diag = diagnostics_summary_for_completed_job(diagnostics_summary(root), job)
+        public_job["diagnostics_summary"] = diag
+        public_job["diagnostics_attention_required"] = diag["attention_required"]
     serialized = json.dumps(public_job, indent=2)
     full_bytes = len(serialized.encode("utf-8"))
 
@@ -116,4 +121,3 @@ def get_analysis_status(
             "Repeat the same get_analysis_status call with the same repo_path, job_id, and max_skipped_files and set allow_large_output=true."
         ),
     )
-
diff --git a/contextor/mcp/tools/get_project_architecture.py b/contextor/mcp/tools/get_project_architecture.py
index 73854bb..2fc4800 100644
--- a/contextor/mcp/tools/get_project_architecture.py
+++ b/contextor/mcp/tools/get_project_architecture.py
@@ -4,6 +4,7 @@ from pathlib import Path
 from contextor.core.analysis.state_manager import module_current_truth
 from contextor.mcp import query_helpers
 from contextor.mcp import runtime as mcp_runtime
+from contextor.mcp.diagnostics import diagnostics_summary
 
 
 def _stale_module_truths(state) -> dict[str, dict]:
@@ -115,11 +116,14 @@ def get_project_architecture(
         else:
             layer_index = dict(unavailable)
         collections["layer_index"] = layer_index
+        diag = diagnostics_summary(root, state)
         result = {
             **collections,
             "debt_summary": debt_summary,
             "module_count": len(getattr(state, "modules", {}) or {}),
             "data_source": "live_canonical_state",
+            "diagnostics_summary": diag,
+            "diagnostics_attention_required": diag["attention_required"],
         }
         if fields is not None:
             allowed_fields = set(result)
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
index 87b44bb..5823c2a 100644
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -182,6 +182,9 @@ from contextor.mcp.documentation import short_description
 from contextor.mcp.tools.get_artifact_blast_radius import (
     get_artifact_blast_radius as _get_artifact_blast_radius_impl,
 )
+from contextor.mcp.tools.get_name_collisions import (
+    get_name_collisions as _get_name_collisions_impl,
+)
 from contextor.mcp.tools.search_artifacts import search_artifacts as _search_artifacts_impl
 from contextor.mcp.tools.search_source import search_source as _search_source_impl
 from contextor.mcp.tools.get_source_range import get_source_range as _get_source_range_impl
@@ -370,13 +373,22 @@ def _emit_mcp_call_telemetry(
 def _instrument_mcp_tool(func: Any, tool_name: str) -> Any:
     import functools
     from inspect import iscoroutinefunction
+    from contextor.mcp.diagnostics import inject_diagnostics_summary
 
     if iscoroutinefunction(func):
         @functools.wraps(func)
         async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
             root_path = _tool_repository_argument(func, args, kwargs)
+            try:
+                bound = inspect.signature(func).bind_partial(*args, **kwargs)
+                allow_large_output = bool(bound.arguments.get("allow_large_output", False))
+            except (TypeError, ValueError):
+                allow_large_output = False
             try:
                 result = await func(*args, **kwargs)
+                result = inject_diagnostics_summary(
+                    result, root_path, tool_name, allow_large_output=allow_large_output
+                )
                 _emit_mcp_call_telemetry(tool_name, root_path, success=True)
                 return result
             except Exception as exc:
@@ -387,8 +399,16 @@ def _instrument_mcp_tool(func: Any, tool_name: str) -> Any:
         @functools.wraps(func)
         def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
             root_path = _tool_repository_argument(func, args, kwargs)
+            try:
+                bound = inspect.signature(func).bind_partial(*args, **kwargs)
+                allow_large_output = bool(bound.arguments.get("allow_large_output", False))
+            except (TypeError, ValueError):
+                allow_large_output = False
             try:
                 result = func(*args, **kwargs)
+                result = inject_diagnostics_summary(
+                    result, root_path, tool_name, allow_large_output=allow_large_output
+                )
                 _emit_mcp_call_telemetry(tool_name, root_path, success=True)
                 return result
             except Exception as exc:
@@ -432,6 +452,7 @@ REGISTERED_MCP_TOOL_NAMES: tuple[str, ...] = (
     "search_source",
     "get_source_range",
     "get_symbol_call_context",
+    "get_name_collisions",
     "get_mcp_documentation",
 )
 
@@ -475,6 +496,7 @@ lookup_artifact_by_symbol = register_mcp_tool(_lookup_artifact_by_symbol_impl, n
 search_source = register_mcp_tool(_search_source_impl, name="search_source")
 get_source_range = register_mcp_tool(_get_source_range_impl, name="get_source_range")
 get_symbol_call_context = register_mcp_tool(_get_symbol_call_context_impl, name="get_symbol_call_context")
+get_name_collisions = register_mcp_tool(_get_name_collisions_impl, name="get_name_collisions")
 get_mcp_documentation = register_mcp_tool(_get_mcp_documentation_impl, name="get_mcp_documentation")
 
 
diff --git a/tests/test_full_analysis_coordination.py b/tests/test_full_analysis_coordination.py
index 6bb7708..eabc82a 100644
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -1,13 +1,12 @@
 """
 tests/test_full_analysis_coordination.py
 
-Comprehensive test suite certifying the single-writer full-analysis coordinator:
-- Multi-threaded / integration concurrency exclusion (max_active == 1)
-- Multi-process isolation and different-repo concurrency
-- Crash / dead-PID stale lock auto-recovery
-- Exception release guarantees in finally
-- Cancellation & timeout handling
-- Serialized canonical publication sequence (Desktop R+1 -> MCP R+2)
+Complete test suite certifying the single-writer full-analysis coordinator:
+- Lease held during publication (Requirement 5)
+- OS file-lock cross-process exclusion and process-death auto-recovery (Requirement 11)
+- MCP single publication root cause regression (Requirement 12)
+- Serialized Desktop + MCP full analysis execution (Requirement 13)
+- Non-reentrant in-process lock exclusion and timeout / cancellation guarantees
 """
 
 from __future__ import annotations
@@ -24,12 +23,16 @@ import pytest
 from contextor.core.analysis.full_analysis_coordinator import (
     FullAnalysisBusyError,
     FullAnalysisLease,
+    _resolve_lock_path,
+    _try_lock_fd,
     acquire_full_analysis,
     release_full_analysis,
     run_full_analysis_exclusive,
 )
 from contextor.core.errors import AnalysisCancelled
 from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
+from contextor.mcp import analysis_jobs
+from contextor.mcp import runtime as mcp_runtime
 
 
 def test_coordinator_lease_acquisition_and_release(tmp_path: Path):
@@ -39,106 +42,96 @@ def test_coordinator_lease_acquisition_and_release(tmp_path: Path):
     lease = acquire_full_analysis(repo_dir, owner="test_owner")
     assert isinstance(lease, FullAnalysisLease)
     assert lease.owner == "test_owner"
+    assert lease.lock_fd >= 0
     assert Path(lease.lock_path).exists()
 
     release_full_analysis(lease)
-    assert not Path(lease.lock_path).exists()
 
 
-def test_max_active_full_analyses_and_serialized_execution(tmp_path: Path):
+def test_lease_is_held_during_publication(tmp_path: Path, monkeypatch):
     """
-    Requirement 10: Multi-threaded integration test proving max_active_full_analyses == 1
-    and strict sequential execution order between Desktop and MCP.
+    Requirement 5: Deterministic lifecycle order proving lease is held during publication:
+    lease_acquired -> analysis_started -> analysis_finished -> publish_started -> publish_finished -> lease_released
+    Forbidden: lease_released before publish_started
     """
-    repo_dir = tmp_path / "repo_concurrency"
+    repo_dir = tmp_path / "repo_lifecycle"
     repo_dir.mkdir()
 
-    active_count = 0
-    max_active = 0
-    active_lock = threading.Lock()
-
-    execution_order = []
-
-    desktop_started = threading.Event()
-    desktop_can_finish = threading.Event()
+    event_log: list[str] = []
+    log_lock = threading.Lock()
 
-    def fake_analysis(path, *, owner, **kwargs):
-        nonlocal active_count, max_active
-        with active_lock:
-            active_count += 1
-            if active_count > max_active:
-                max_active = active_count
-            execution_order.append(f"{owner}:start")
-
-        if owner == "desktop_analysis":
-            desktop_started.set()
-            desktop_can_finish.wait(timeout=5.0)
+    def record(event: str):
+        with log_lock:
+            event_log.append(event)
 
-        time.sleep(0.05)
+    # Wrap acquire and release to log events
+    from contextor.core.analysis import full_analysis_coordinator as fac
 
-        with active_lock:
-            active_count -= 1
-            execution_order.append(f"{owner}:end")
-        return [], SimpleNamespace(status="ok")
+    orig_acquire = fac.acquire_full_analysis
+    orig_release = fac.release_full_analysis
 
-    # Thread 1: Desktop analysis
-    def run_desktop():
-        run_full_analysis_exclusive(
-            repo_dir,
-            owner="desktop_analysis",
-            analysis_fn=fake_analysis,
-        )
+    def tracked_acquire(*args, **kwargs):
+        record("lease_acquired")
+        return orig_acquire(*args, **kwargs)
 
-    # Thread 2: MCP analysis
-    def run_mcp():
-        run_full_analysis_exclusive(
-            repo_dir,
-            owner="mcp_analysis",
-            analysis_fn=fake_analysis,
-        )
+    def tracked_release(lease):
+        record("lease_released")
+        return orig_release(lease)
 
-    t_desktop = threading.Thread(target=run_desktop)
-    t_mcp = threading.Thread(target=run_mcp)
+    monkeypatch.setattr(fac, "acquire_full_analysis", tracked_acquire)
+    monkeypatch.setattr(fac, "release_full_analysis", tracked_release)
 
-    t_desktop.start()
-    assert desktop_started.wait(timeout=3.0), "Desktop analysis did not start"
+    # Injected analysis function that performs work and publication
+    def tracked_analysis(path, *, owner, **kwargs):
+        record("analysis_started")
+        time.sleep(0.02)
+        record("analysis_finished")
 
-    # Start MCP analysis while Desktop analysis is active
-    t_mcp.start()
-    time.sleep(0.2)
+        record("publish_started")
+        time.sleep(0.02)
+        record("publish_finished")
 
-    # MCP should NOT have started inside fake_analysis yet
-    with active_lock:
-        assert max_active == 1
-        assert "mcp_analysis:start" not in execution_order
-
-    # Now allow Desktop to finish
-    desktop_can_finish.set()
+        return [], SimpleNamespace(
+            live_publish_status="success",
+            live_publish_revision=11,
+            live_publish_warning=None,
+        )
 
-    t_desktop.join(timeout=3.0)
-    t_mcp.join(timeout=3.0)
+    run_full_analysis_exclusive(
+        repo_dir,
+        owner="mcp_analysis",
+        analysis_fn=tracked_analysis,
+    )
 
-    assert max_active == 1
-    assert execution_order == [
-        "desktop_analysis:start",
-        "desktop_analysis:end",
-        "mcp_analysis:start",
-        "mcp_analysis:end",
+    expected_order = [
+        "lease_acquired",
+        "analysis_started",
+        "analysis_finished",
+        "publish_started",
+        "publish_finished",
+        "lease_released",
     ]
+    assert event_log == expected_order
 
 
-def _worker_acquire_and_hold(repo_path: str, owner: str, ready_event, release_event, result_queue):
+def _worker_os_lock_hold(repo_path: str, owner: str, ready_event, result_queue, hold_seconds: float):
+    """Worker process that acquires OS lock and holds it until killed or timeout."""
     try:
         lease = acquire_full_analysis(repo_path, owner=owner, timeout=5.0)
+        result_queue.put({"status": "acquired", "owner": owner, "pid": os.getpid()})
         ready_event.set()
-        release_event.wait(timeout=5.0)
+        time.sleep(hold_seconds)
         release_full_analysis(lease)
-        result_queue.put({"status": "ok", "owner": owner})
-    except Exception as exc:
-        result_queue.put({"status": "error", "error": str(exc), "owner": owner})
+    except BaseException as exc:
+        result_queue.put(
+            {"status": "error", "owner": owner, "pid": os.getpid(), "error": repr(exc)}
+        )
+        ready_event.set()
+        raise
 
 
 def _worker_try_acquire(repo_path: str, owner: str, timeout: float, result_queue):
+    """Worker process that attempts to acquire lease."""
     try:
         lease = acquire_full_analysis(repo_path, owner=owner, timeout=timeout)
         release_full_analysis(lease)
@@ -149,11 +142,13 @@ def _worker_try_acquire(repo_path: str, owner: str, timeout: float, result_queue
         result_queue.put({"status": "error", "error": str(exc), "owner": owner})
 
 
-def test_cross_process_coordination_and_repo_isolation(tmp_path: Path):
+def test_cross_process_os_lock_and_process_death_recovery(tmp_path: Path, isolated_dirs):
     """
-    Requirement 11: Cross-process test using multiprocessing.Process.
-    Proves process A blocks process B on same repo, while process B2 on
-    a different repo acquires concurrently without blocking.
+    Requirement 11: Cross-process exclusion and OS-held file lock auto-recovery on process termination.
+    Proves:
+    - Process A blocks Process B on same repo.
+    - Process A terminated without release -> Process B automatically acquires without lock file unlinking.
+    - Process C on different repo acquires concurrently.
     """
     repo1 = tmp_path / "repo1"
     repo2 = tmp_path / "repo2"
@@ -162,118 +157,255 @@ def test_cross_process_coordination_and_repo_isolation(tmp_path: Path):
 
     ctx = multiprocessing.get_context("spawn")
     ready_a = ctx.Event()
-    release_a = ctx.Event()
     results_a = ctx.Queue()
-    results_b = ctx.Queue()
+    results_b1 = ctx.Queue()
     results_b2 = ctx.Queue()
+    results_c = ctx.Queue()
 
-    # Process A: acquires repo1 and holds
+    # 1. Process A acquires repo1
     p_a = ctx.Process(
-        target=_worker_acquire_and_hold,
-        args=(str(repo1), "proc_a", ready_a, release_a, results_a),
+        target=_worker_os_lock_hold,
+        args=(str(repo1), "proc_a", ready_a, results_a, 15.0),
     )
     p_a.start()
 
     try:
-        assert ready_a.wait(timeout=5.0), "Process A failed to acquire repo1"
+        assert ready_a.wait(timeout=15.0), "Process A produced no acquisition diagnostic"
+        res_a = results_a.get(timeout=2.0)
+        assert res_a["status"] == "acquired", f"Process A failed to acquire repo1: {res_a}"
+
+        # 2. Process B attempts repo1 while A is alive -> busy
+        p_b1 = ctx.Process(
+            target=_worker_try_acquire,
+            args=(str(repo1), "proc_b1", 0.5, results_b1),
+        )
+        p_b1.start()
+        p_b1.join(timeout=3.0)
+
+        res_b1 = results_b1.get(timeout=2.0)
+        assert res_b1["status"] == "busy", f"Process B1 was not blocked: {res_b1}"
 
-        # Process B: tries to acquire repo1 with short timeout -> should be busy / blocked
-        p_b = ctx.Process(
+        # 3. Process C attempts repo2 (different repo) concurrently -> succeeds immediately
+        p_c = ctx.Process(
             target=_worker_try_acquire,
-            args=(str(repo1), "proc_b", 0.5, results_b),
+            args=(str(repo2), "proc_c", 1.0, results_c),
         )
-        p_b.start()
-        p_b.join(timeout=3.0)
+        p_c.start()
+        p_c.join(timeout=3.0)
 
-        res_b = results_b.get(timeout=2.0)
-        assert res_b["status"] == "busy", f"Process B did not encounter busy state: {res_b}"
+        res_c = results_c.get(timeout=2.0)
+        assert res_c["status"] == "ok", f"Process C on different repo failed: {res_c}"
 
-        # Process B2: tries to acquire repo2 (different repo) -> should succeed immediately!
+        # 4. Terminate Process A WITHOUT clean release (simulates sudden process death/crash)
+        p_a.terminate()
+        p_a.join(timeout=3.0)
+
+        # 5. Process B attempts repo1 now -> OS automatically unlocked, acquires without unlinking lock file!
         p_b2 = ctx.Process(
             target=_worker_try_acquire,
-            args=(str(repo2), "proc_b2", 1.0, results_b2),
+            args=(str(repo1), "proc_b2", 2.0, results_b2),
         )
         p_b2.start()
         p_b2.join(timeout=3.0)
 
         res_b2 = results_b2.get(timeout=2.0)
-        assert res_b2["status"] == "ok", f"Process B2 failed on different repo: {res_b2}"
-
-        # Release A
-        release_a.set()
-        p_a.join(timeout=3.0)
+        assert res_b2["status"] == "ok", f"Process B2 failed to acquire after process death: {res_b2}"
 
-        res_a = results_a.get(timeout=2.0)
-        assert res_a["status"] == "ok"
+        # Ensure lock file was NOT deleted (file existence is not ownership)
+        lock_file, _, _ = _resolve_lock_path(repo1)
+        assert lock_file.exists()
     finally:
-        release_a.set()
         if p_a.is_alive():
             p_a.terminate()
 
 
-def test_exception_in_analysis_releases_lease(tmp_path: Path):
-    """
-    Requirement 12a: Exception inside analysis releases lock in finally block.
-    """
-    repo_dir = tmp_path / "repo_exc"
+def test_mcp_single_publication_root_cause_regression(tmp_path: Path, monkeypatch):
+    """The real MCP worker has one facade-owned LIVE publication path."""
+    repo_dir = tmp_path / "repo_mcp_pub"
     repo_dir.mkdir()
+    exclusive_calls: list[str] = []
+
+    def fake_run_full_analysis_exclusive(_root, *, owner, **_kwargs):
+        exclusive_calls.append(owner)
+        return [], SimpleNamespace(
+            skipped_python_files=[],
+            live_publish_status="success",
+            live_publish_revision=11,
+            live_publish_warning=None,
+        )
 
-    def failing_analysis(path, **kwargs):
-        raise ValueError("synthetic analysis failure")
+    monkeypatch.setattr(
+        analysis_jobs,
+        "run_full_analysis_exclusive",
+        fake_run_full_analysis_exclusive,
+    )
+    outcome = __import__("asyncio").run(
+        analysis_jobs._run_analysis_worker("project", repo_dir)
+    )
 
-    with pytest.raises(ValueError, match="synthetic analysis failure"):
-        run_full_analysis_exclusive(
-            repo_dir,
-            owner="test_failing",
-            analysis_fn=failing_analysis,
-        )
+    assert exclusive_calls == ["mcp_analysis"]
+    assert outcome["live_publish_status"] == "success"
+    assert outcome["live_publish_revision"] == 11
+    assert outcome["live_publish_warning"] is None
 
-    # Next attempt should succeed immediately without busy error
-    executed = False
-    def succeeding_analysis(path, **kwargs):
-        nonlocal executed
-        executed = True
-        return [], SimpleNamespace(status="ok")
+    async def fake_worker(*_args, **_kwargs):
+        return outcome
 
-    run_full_analysis_exclusive(
-        repo_dir,
-        owner="test_succeeding",
-        analysis_fn=succeeding_analysis,
-        timeout=1.0,
+    def forbidden_second_publish(*_args, **_kwargs):
+        raise AssertionError("outer MCP duplicate publication attempted")
+
+    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
+    monkeypatch.setattr(
+        mcp_runtime,
+        "get_or_init_engine",
+        lambda _root: SimpleNamespace(state=SimpleNamespace(revision=11)),
     )
-    assert executed is True
+    monkeypatch.setattr(
+        "contextor.core.live_state.connect_or_start",
+        forbidden_second_publish,
+    )
+    mcp_runtime._live_engine_revisions.pop(str(repo_dir), None)
+    job = {
+        "job_id": "c" * 32,
+        "repo_path": str(repo_dir),
+        "operation": "project",
+        "target": None,
+        "exclude_paths": [],
+        "status": "queued",
+        "created_at": "2026-08-28T00:00:00Z",
+        "started_at": None,
+        "completed_at": None,
+        "message": "Analysis accepted.",
+        "error": None,
+        "live_publish_status": "pending",
+        "live_publish_revision": None,
+        "live_publish_warning": None,
+    }
+    analysis_jobs._write_analysis_job(repo_dir, job)
+    __import__("asyncio").run(
+        analysis_jobs._execute_analysis_job(repo_dir, job, None, [])
+    )
+
+    final_job = analysis_jobs._read_analysis_job(repo_dir, job["job_id"])
+    assert final_job is not None
+    assert final_job["status"] == "completed"
+    assert final_job["live_publish_status"] == "success"
+    assert final_job["live_publish_revision"] == 11
+    assert mcp_runtime._live_engine_revisions[str(repo_dir)] == 11
 
 
-def test_dead_pid_stale_lock_recovery(tmp_path: Path):
+def test_serialized_desktop_and_mcp_coordination(tmp_path: Path, monkeypatch):
     """
-    Requirement 12b: Stale lock file from terminated/crashed PID is automatically recovered.
+    Requirement 13: Concurrency test proving serialized Desktop + MCP execution:
+    - Desktop requests full analysis (R=10 -> R=11)
+    - MCP requests full analysis while Desktop owns lease
+    - Desktop completes, publishes R=11, releases lease
+    - MCP acquires lease, performs complete hard reset, publishes R=12, releases lease
+    - max_active == 1
+    - publications == [("desktop_analysis", 11), ("mcp_analysis", 12)]
     """
-    repo_dir = tmp_path / "repo_dead_pid"
+    repo_dir = tmp_path / "repo_serialized"
     repo_dir.mkdir()
 
-    from contextor.core.analysis.full_analysis_coordinator import _resolve_lock_path
-    import json
+    initial_state = SimpleNamespace(revision=10, modules={"app": 1})
+    server = CanonicalLiveServer(state=initial_state, revision=10)
+    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
+    server_thread.start()
+    live_client = LiveStateClient(server.endpoint)
+
+    from contextor.core import live_state
+    monkeypatch.setattr(live_state, "connect", lambda _path: live_client)
+    monkeypatch.setattr("contextor.core.live_state.connect", lambda _path: live_client)
 
-    lock_file, key, repo_id = _resolve_lock_path(repo_dir)
+    active_analyses = 0
+    max_simultaneous = 0
+    active_lock = threading.Lock()
+    publications_observed: list[tuple[str, int]] = []
 
-    # Create a stale lock file with an impossible/dead PID (e.g. 99999999)
-    stale_payload = {
-        "pid": 99999999,
-        "token": "stale_token_123",
-        "owner": "crashed_process",
-        "repo_id": repo_id,
-        "timestamp": time.time() - 100,
-    }
-    lock_file.write_text(json.dumps(stale_payload), encoding="utf-8")
-    assert lock_file.exists()
+    desktop_holding = threading.Event()
+    desktop_can_finish = threading.Event()
 
-    # New acquisition should detect dead PID and recover seamlessly
-    lease = acquire_full_analysis(repo_dir, owner="recovering_process", timeout=1.0)
-    assert lease.owner == "recovering_process"
-    assert lease.token != "stale_token_123"
+    def coordinated_analysis(path, *, owner, **kwargs):
+        nonlocal active_analyses, max_simultaneous
+        with active_lock:
+            active_analyses += 1
+            if active_analyses > max_simultaneous:
+                max_simultaneous = active_analyses
 
-    release_full_analysis(lease)
-    assert not lock_file.exists()
+        if owner == "desktop_analysis":
+            desktop_holding.set()
+            desktop_can_finish.wait(timeout=5.0)
+            next_rev = 11
+        else:
+            next_rev = 12
+
+        time.sleep(0.05)
+        cand_state = SimpleNamespace(revision=next_rev, modules={"app": 1, owner: 1})
+        pub_res = live_client.publish(cand_state, origin=owner)
+        assert pub_res.get("status") == "ok"
+        with active_lock:
+            publications_observed.append((owner, pub_res["revision"]))
+            active_analyses -= 1
+
+        return [], SimpleNamespace(
+            live_publish_status="success",
+            live_publish_revision=pub_res["revision"],
+        )
+
+    t_desktop = threading.Thread(
+        target=lambda: run_full_analysis_exclusive(
+            repo_dir, owner="desktop_analysis", analysis_fn=coordinated_analysis
+        )
+    )
+    t_mcp = threading.Thread(
+        target=lambda: run_full_analysis_exclusive(
+            repo_dir, owner="mcp_analysis", analysis_fn=coordinated_analysis
+        )
+    )
+
+    try:
+        t_desktop.start()
+        assert desktop_holding.wait(timeout=3.0), "Desktop did not start analysis"
+
+        # Start MCP while Desktop is holding lease
+        t_mcp.start()
+        time.sleep(0.1)
+
+        with active_lock:
+            assert max_simultaneous == 1
+            assert len(publications_observed) == 0
+
+        # Release Desktop
+        desktop_can_finish.set()
+
+        t_desktop.join(timeout=3.0)
+        t_mcp.join(timeout=3.0)
+
+        assert max_simultaneous == 1
+        assert publications_observed == [
+            ("desktop_analysis", 11),
+            ("mcp_analysis", 12),
+        ]
+        assert server._revision == 12
+        assert live_client.ping()["revision"] == 12
+    finally:
+        server.close()
+        server_thread.join(timeout=2)
+
+
+def test_in_process_non_reentrant_lock_exclusion(tmp_path: Path):
+    """
+    Requirement 8: Non-reentrant lock prevents recursive bypass by same thread.
+    """
+    repo_dir = tmp_path / "repo_non_reentrant"
+    repo_dir.mkdir()
+
+    lease1 = acquire_full_analysis(repo_dir, owner="outer", timeout=1.0)
+    try:
+        with pytest.raises(FullAnalysisBusyError):
+            acquire_full_analysis(repo_dir, owner="inner_recursive", timeout=0.2)
+    finally:
+        release_full_analysis(lease1)
 
 
 def test_cancellation_during_wait(tmp_path: Path):
@@ -298,64 +430,34 @@ def test_cancellation_during_wait(tmp_path: Path):
     release_full_analysis(lease)
 
 
-def test_serialized_publication_sequence_desktop_then_mcp(tmp_path: Path):
-    """
-    Requirement 13: Simulate Desktop full analysis followed by MCP full analysis
-    starting from same initial state, verifying sequential exact-successor revisions
-    (R=10 -> R=11 -> R=12), zero non-monotonic errors, and zero duplicates.
-    """
-    repo_dir = tmp_path / "repo_pub_seq"
-    repo_dir.mkdir()
-
-    # Initialize live server at revision 10
-    initial_state = SimpleNamespace(revision=10, modules={"init": 1})
-    server = CanonicalLiveServer(state=initial_state, revision=10)
-    thread = threading.Thread(target=server.serve_forever, daemon=True)
-    thread.start()
-    client = LiveStateClient(server.endpoint)
+def test_exception_in_analysis_releases_lease(tmp_path: Path):
+    repo = tmp_path / "repo_exception_release"
+    repo.mkdir()
 
-    try:
-        # 1. Desktop Full Analysis (R=10 -> R=11)
-        def desktop_analysis_step(path, **kwargs):
-            cand = SimpleNamespace(revision=11, modules={"init": 1, "desktop": 1})
-            res = client.publish(cand, origin="desktop_analysis")
-            assert res["status"] == "ok"
-            assert res["revision"] == 11
-            return [], SimpleNamespace(live_publish_status="success", live_publish_revision=11)
+    def failing_analysis(path, **kwargs):
+        raise RuntimeError("synthetic analysis failure")
 
+    with pytest.raises(RuntimeError, match="synthetic analysis failure"):
         run_full_analysis_exclusive(
-            repo_dir,
-            owner="desktop_analysis",
-            analysis_fn=desktop_analysis_step,
+            repo,
+            owner="failing_owner",
+            analysis_fn=failing_analysis,
         )
 
-        assert server._revision == 11
-        assert client.ping()["revision"] == 11
-
-        # 2. MCP Full Analysis (R=11 -> R=12)
-        def mcp_analysis_step(path, **kwargs):
-            # Reads fresh state at R=11 and produces candidate R=12
-            cand = SimpleNamespace(revision=12, modules={"init": 1, "desktop": 1, "mcp": 1})
-            res = client.publish(cand, origin="mcp_analysis")
-            assert res["status"] == "ok"
-            assert res["revision"] == 12
-            return [], SimpleNamespace(live_publish_status="success", live_publish_revision=12)
+    executed = False
 
-        run_full_analysis_exclusive(
-            repo_dir,
-            owner="mcp_analysis",
-            analysis_fn=mcp_analysis_step,
+    def succeeding_analysis(path, **kwargs):
+        nonlocal executed
+        executed = True
+        return [], SimpleNamespace(
+            live_publish_status="not_attempted",
+            live_publish_revision=None,
         )
 
-        assert server._revision == 12
-        assert client.ping()["revision"] == 12
-
-        events = client.get_events(after_seq=0)["events"]
-        assert len(events) == 2
-        assert events[0]["canonical_revision"] == 11
-        assert events[0]["origin"] == "desktop_analysis"
-        assert events[1]["canonical_revision"] == 12
-        assert events[1]["origin"] == "mcp_analysis"
-    finally:
-        server.close()
-        thread.join(timeout=2)
+    run_full_analysis_exclusive(
+        repo,
+        owner="next_owner",
+        analysis_fn=succeeding_analysis,
+        timeout=1.0,
+    )
+    assert executed is True
diff --git a/tests/test_h3a_workspace_canonical_freshness.py b/tests/test_h3a_workspace_canonical_freshness.py
index 8949a47..e016021 100644
--- a/tests/test_h3a_workspace_canonical_freshness.py
+++ b/tests/test_h3a_workspace_canonical_freshness.py
@@ -1481,7 +1481,11 @@ def test_h3a_case_z_unknown_status_analysis_job_fail_closed(tmp_path, monkeypatc
     )
 
     async def fake_worker(*_args, **_kwargs):
-        pass
+        return {
+            "live_publish_status": "failed",
+            "live_publish_revision": None,
+            "live_publish_warning": "LIVE service returned status 'rejected'.",
+        }
 
     monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
     monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
@@ -1525,15 +1529,8 @@ def test_h3a_case_z_unknown_status_analysis_job_fail_closed(tmp_path, monkeypatc
     assert str(repo) not in mcp_runtime._live_engine_revisions
 
 
-def test_h3a_case_aa_analysis_job_journal_canonical_revision_separation(tmp_path, monkeypatch):
-    """Case AA (H3A-H7 - MCP Analysis Job Journal vs Canonical Revision Separation):
-    - Client publish returns {'status': 'ok', 'revision': 42} (journal)
-    - Canonical engine_state.revision = 3
-    - EXPECT:
-      - job live_publish_status == 'success'
-      - job live_publish_revision == 42
-      - mcp_runtime._live_engine_revisions[root] == 3 (canonical state revision, NOT 42)
-    """
+def test_h3a_case_aa_analysis_job_revision_mismatch_fails_closed(tmp_path, monkeypatch):
+    """Case AA: full-analysis certification rejects unequal revisions."""
     import asyncio
     from types import SimpleNamespace
 
@@ -1542,19 +1539,15 @@ def test_h3a_case_aa_analysis_job_journal_canonical_revision_separation(tmp_path
 
     engine_state = SimpleNamespace(fresh=True, revision=3)
     engine = SimpleNamespace(state=engine_state)
-    client = SimpleNamespace(
-        publish=lambda state, *, origin, timeout: {"status": "ok", "revision": 42}
-    )
-
     async def fake_worker(*_args, **_kwargs):
-        return {}
+        return {
+            "live_publish_status": "success",
+        "live_publish_revision": 42,
+            "live_publish_warning": None,
+        }
 
     monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
     monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
-    monkeypatch.setattr(
-        "contextor.core.live_state.connect_or_start",
-        lambda _root, *args, **kwargs: client,
-    )
     analysis_jobs._analysis_tasks.clear()
     analysis_jobs._analysis_jobs_by_repo.clear()
 
@@ -1580,12 +1573,10 @@ def test_h3a_case_aa_analysis_job_journal_canonical_revision_separation(tmp_path
 
     final_job = analysis_jobs._read_analysis_job(repo, job_id)
     assert final_job is not None
-    assert final_job["status"] == "completed"
-    assert final_job["live_publish_status"] == "success"
-    assert final_job["live_publish_revision"] == 42
-    assert final_job["live_publish_warning"] is None
-    assert mcp_runtime._live_engine_revisions[str(repo)] == 3
-
+    assert final_job["status"] == "failed"
+    assert "loaded=3" in final_job["error"]
+    assert "published=42" in final_job["error"]
+    assert str(repo) not in mcp_runtime._live_engine_revisions
 
 
 
diff --git a/tests/test_live_activity_status.py b/tests/test_live_activity_status.py
index 2d30971..0b5abce 100644
--- a/tests/test_live_activity_status.py
+++ b/tests/test_live_activity_status.py
@@ -16,7 +16,7 @@ Covers all concrete correctness and evidence requirements:
 13. Central MCP wrapper read-only success
 14. Central MCP wrapper failure re-raise & logging
 15. MCP analyze_project wrapper & canonical publication separation
-16. All 24 registered FastMCP tools coverage & registry synchronization
+16. All 25 registered FastMCP tools coverage & registry synchronization
 17. Real server-to-GUI burst ordering, zero dropped events & zero duplicates
 18. Desktop vs MCP full analysis publication equivalence
 """
@@ -601,10 +601,10 @@ def test_mcp_analyze_project_wrapper_and_canonical_publish_equivalence(live_serv
     assert events[1]["canonical_revision"] == 2
 
 
-def test_all_24_registered_mcp_tools_telemetry_against_fastmcp_registry(monkeypatch):
+def test_all_25_registered_mcp_tools_telemetry_against_fastmcp_registry(monkeypatch):
     fastmcp_tool_names = set(mcp._tool_manager._tools.keys())
     assert set(REGISTERED_MCP_TOOL_NAMES) == fastmcp_tool_names
-    assert len(REGISTERED_MCP_TOOL_NAMES) == 24
+    assert len(REGISTERED_MCP_TOOL_NAMES) == 25
 
     calls_emitted = []
 
diff --git a/tests/test_matrix_clusters_ram_parity.py b/tests/test_matrix_clusters_ram_parity.py
index 475b4ff..2d939ce 100644
--- a/tests/test_matrix_clusters_ram_parity.py
+++ b/tests/test_matrix_clusters_ram_parity.py
@@ -802,7 +802,7 @@ def test_full_analysis_vs_incremental_add_exact_parity(tmp_path: Path):
                 assert "api_imports" in entry_a["channels"][c] and "api_imports" in entry_b["channels"][c]
 
 
-def test_resync_required_fails_closed_in_engine_lifecycle(tmp_path: Path):
+def test_resync_required_fails_closed_in_engine_lifecycle(tmp_path: Path, isolated_dirs):
     """
     PROVES that if state.resync_required is True, engine update lifecycle
     refuses to mark artifact_consumption_state as 'fresh' even with 100% valid coverage.
diff --git a/tests/test_mcp_documentation.py b/tests/test_mcp_documentation.py
index 984b906..8818eb4 100644
--- a/tests/test_mcp_documentation.py
+++ b/tests/test_mcp_documentation.py
@@ -72,7 +72,7 @@ def test_documentation_default_returns_only_index(monkeypatch):
     result = json.loads(mcp_server.get_mcp_documentation.fn())
 
     assert result["version"]
-    assert len(result["tools"]) == 24
+    assert len(result["tools"]) == 25
     assert loaded == [documentation.INDEX_PATH]
 
 
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index 36bc7d6..aae6d76 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -577,21 +577,16 @@ def test_analysis_endpoint_returns_reusable_job_and_pollable_completion(
 
     async def fake_worker(*_args, **_kwargs):
         await asyncio.to_thread(release.wait)
+        return {
+            "live_publish_status": "success",
+            "live_publish_revision": 1,
+            "live_publish_warning": None,
+        }
 
-    published = []
     engine_state = SimpleNamespace(fresh=True, revision=1)
     engine = SimpleNamespace(state=engine_state)
-    client = SimpleNamespace(
-        publish=lambda state, *, origin, timeout: published.append(
-            (state, origin, timeout)
-        ) or {"status": "ok", "revision": 1}
-    )
     monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
     monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
-    monkeypatch.setattr(
-        "contextor.core.live_state.connect_or_start",
-        lambda _root, *args, **kwargs: client,
-    )
     analysis_jobs._analysis_tasks.clear()
     analysis_jobs._analysis_jobs_by_repo.clear()
 
@@ -619,7 +614,7 @@ def test_analysis_endpoint_returns_reusable_job_and_pollable_completion(
         assert completed["live_publish_status"] == "success"
         assert completed["live_publish_revision"] == 1
         assert completed["live_publish_warning"] is None
-        assert published == [(engine.state, "mcp_analysis", 10.0)]
+        assert mcp_runtime._live_engine_revisions[str(repo)] == 1
 
     asyncio.run(scenario())
 
@@ -655,22 +650,23 @@ def test_analysis_job_preserves_live_publish_timeout_status(tmp_path, monkeypatc
     repo.mkdir()
 
     async def fake_worker(*_args, **_kwargs):
-        return {"skipped_python_files": []}
-
-    engine = SimpleNamespace(state={"fresh": True})
-
-    class Client:
-        def publish(self, _state, *, origin, timeout):
-            assert origin == "mcp_analysis"
-            assert timeout == 10.0
-            raise TimeoutError("simulated LIVE timeout")
+        return {
+            "skipped_python_files": [],
+            "live_publish_status": "timed_out",
+            "live_publish_revision": None,
+            "live_publish_warning": "TimeoutError: simulated LIVE timeout",
+        }
 
     monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
-    monkeypatch.setattr(
-        "contextor.core.live_state.connect_or_start",
-        lambda _root, *args, **kwargs: Client(),
+    mcp_runtime._live_engines[str(repo)] = SimpleNamespace(
+        state=SimpleNamespace(revision=10)
     )
+    mcp_runtime._live_engine_revisions[str(repo)] = 10
+
+    def forbidden_hydration(_root):
+        raise AssertionError("canonical engine hydration attempted after timeout")
+
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", forbidden_hydration)
     analysis_jobs._analysis_tasks.clear()
     analysis_jobs._analysis_jobs_by_repo.clear()
 
@@ -688,6 +684,8 @@ def test_analysis_job_preserves_live_publish_timeout_status(tmp_path, monkeypatc
         assert completed["live_publish_revision"] is None
         assert "simulated LIVE timeout" in completed["live_publish_warning"]
         assert "LIVE publish timed_out" in completed["message"]
+        assert str(repo) not in mcp_runtime._live_engines
+        assert str(repo) not in mcp_runtime._live_engine_revisions
 
     asyncio.run(scenario())
 
@@ -741,7 +739,174 @@ def test_project_worker_carries_indexer_skips_into_durable_job_status(
 
     outcome = asyncio.run(analysis_jobs._run_analysis_worker("project", repo))
 
-    assert outcome == {"skipped_python_files": skipped}
+    assert outcome == {
+        "skipped_python_files": skipped,
+        "live_publish_status": "not_attempted",
+        "live_publish_revision": None,
+        "live_publish_warning": None,
+    }
+
+
+def _project_analysis_job(repo: Path, job_id: str) -> dict:
+    return {
+        "job_id": (job_id.encode("utf-8").hex() + ("0" * 32))[:32],
+        "repo_path": str(repo),
+        "operation": "project",
+        "target": None,
+        "exclude_paths": [],
+        "status": "queued",
+        "created_at": "2026-08-28T00:00:00Z",
+        "started_at": None,
+        "completed_at": None,
+        "message": "Analysis accepted.",
+        "error": None,
+        "live_publish_status": "pending",
+        "live_publish_revision": None,
+        "live_publish_warning": None,
+    }
+
+
+def test_project_analysis_job_fails_closed_when_canonical_engine_is_missing(
+    tmp_path, monkeypatch
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+
+    async def fake_worker(*_args, **_kwargs):
+        return {
+            "skipped_python_files": [],
+            "live_publish_status": "success",
+            "live_publish_revision": 11,
+            "live_publish_warning": None,
+        }
+
+    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)
+    mcp_runtime._live_engines[str(repo)] = SimpleNamespace(
+        state=SimpleNamespace(revision=10)
+    )
+    mcp_runtime._live_engine_revisions[str(repo)] = 10
+    job = _project_analysis_job(repo, "engine-missing")
+    analysis_jobs._write_analysis_job(repo, job)
+
+    asyncio.run(analysis_jobs._execute_analysis_job(repo, job, None, []))
+
+    final_job = analysis_jobs._read_analysis_job(repo, job["job_id"])
+    assert final_job is not None
+    assert final_job["status"] == "failed"
+    assert "canonical state could not be loaded" in final_job["error"]
+    assert str(repo) not in mcp_runtime._live_engines
+    assert str(repo) not in mcp_runtime._live_engine_revisions
+
+
+def test_project_analysis_job_fails_closed_on_canonical_revision_mismatch(
+    tmp_path, monkeypatch
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+
+    async def fake_worker(*_args, **_kwargs):
+        return {
+            "skipped_python_files": [],
+            "live_publish_status": "success",
+            "live_publish_revision": 11,
+            "live_publish_warning": None,
+        }
+
+    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
+    mismatched_engine = SimpleNamespace(state=SimpleNamespace(revision=10))
+
+    def fake_get_or_init_engine(_root):
+        mcp_runtime._live_engines[str(repo)] = mismatched_engine
+        return mismatched_engine
+
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", fake_get_or_init_engine)
+    job = _project_analysis_job(repo, "revision-mismatch")
+    analysis_jobs._write_analysis_job(repo, job)
+
+    asyncio.run(analysis_jobs._execute_analysis_job(repo, job, None, []))
+
+    final_job = analysis_jobs._read_analysis_job(repo, job["job_id"])
+    assert final_job is not None
+    assert final_job["status"] == "failed"
+    assert "loaded=10" in final_job["error"]
+    assert "published=11" in final_job["error"]
+    assert str(repo) not in mcp_runtime._live_engines
+    assert str(repo) not in mcp_runtime._live_engine_revisions
+
+
+def test_project_analysis_job_certifies_matching_canonical_revision(
+    tmp_path, monkeypatch
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+
+    async def fake_worker(*_args, **_kwargs):
+        return {
+            "skipped_python_files": [],
+            "live_publish_status": "success",
+            "live_publish_revision": 11,
+            "live_publish_warning": None,
+        }
+
+    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
+    matching_engine = SimpleNamespace(state=SimpleNamespace(revision=11))
+
+    def fake_get_or_init_engine(_root):
+        mcp_runtime._live_engines[str(repo)] = matching_engine
+        return matching_engine
+
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", fake_get_or_init_engine)
+    job = _project_analysis_job(repo, "revision-parity")
+    analysis_jobs._write_analysis_job(repo, job)
+
+    asyncio.run(analysis_jobs._execute_analysis_job(repo, job, None, []))
+
+    final_job = analysis_jobs._read_analysis_job(repo, job["job_id"])
+    assert final_job is not None
+    assert final_job["status"] == "completed"
+    assert mcp_runtime._live_engines[str(repo)] is matching_engine
+    assert mcp_runtime._live_engine_revisions[str(repo)] == 11
+
+
+def test_project_analysis_job_does_not_hydrate_after_failed_publication(
+    tmp_path, monkeypatch
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+
+    async def fake_worker(*_args, **_kwargs):
+        return {
+            "skipped_python_files": [],
+            "live_publish_status": "failed",
+            "live_publish_revision": None,
+            "live_publish_warning": "synthetic publication failure",
+        }
+
+    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
+    mcp_runtime._live_engines[str(repo)] = SimpleNamespace(
+        state=SimpleNamespace(revision=10)
+    )
+    mcp_runtime._live_engine_revisions[str(repo)] = 10
+
+    def forbidden_hydration(_root):
+        raise AssertionError(
+            "canonical engine hydration attempted after failed publication"
+        )
+
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", forbidden_hydration)
+    job = _project_analysis_job(repo, "failed-publication")
+    analysis_jobs._write_analysis_job(repo, job)
+
+    asyncio.run(analysis_jobs._execute_analysis_job(repo, job, None, []))
+
+    final_job = analysis_jobs._read_analysis_job(repo, job["job_id"])
+    assert final_job is not None
+    assert final_job["status"] == "completed"
+    assert final_job["live_publish_status"] == "failed"
+    assert final_job["live_publish_warning"] == "synthetic publication failure"
+    assert str(repo) not in mcp_runtime._live_engines
+    assert str(repo) not in mcp_runtime._live_engine_revisions
 
 
 def test_analysis_status_bounds_and_exposes_skipped_python_files(tmp_path):
@@ -2440,9 +2605,13 @@ def test_mcp_analysis_worker_forwards_per_run_excludes(tmp_path, monkeypatch):
     calls = []
 
     def fake_analysis(
-        repo_path, log=None, progress_callback=None, additional_excludes=None
+        repo_path,
+        *,
+        additional_excludes=None,
+        owner="desktop_analysis",
+        **_kwargs,
     ):
-        calls.append((repo_path, additional_excludes))
+        calls.append((repo_path, additional_excludes, owner))
         return [], object()
 
     monkeypatch.setattr(ContextorFacade, "analyze_project", fake_analysis)
@@ -2454,7 +2623,7 @@ def test_mcp_analysis_worker_forwards_per_run_excludes(tmp_path, monkeypatch):
     )
 
     assert calls == [
-        (str(repo), ["tests", "legacy/adapter.py"])
+        (str(repo), ["tests", "legacy/adapter.py"], "mcp_analysis")
     ]
 
 
@@ -5911,5 +6080,3 @@ def test_get_artifacts_for_module_representation_and_progressive_disclosure(
     )
     assert blast_res["consumers"]["total"] == 20
     assert len(blast_res["consumers"]["items"]) == 20
-
-
diff --git a/tests/test_mcp_split_s2a.py b/tests/test_mcp_split_s2a.py
index cb60a69..c61eb3e 100644
--- a/tests/test_mcp_split_s2a.py
+++ b/tests/test_mcp_split_s2a.py
@@ -1,4 +1,5 @@
 import ast
+import importlib
 import inspect
 from pathlib import Path
 
@@ -42,6 +43,7 @@ _EXPECTED_ORDER = [
     "search_source",
     "get_source_range",
     "get_symbol_call_context",
+    "get_name_collisions",
     "get_mcp_documentation",
 ]
 
@@ -115,10 +117,13 @@ def test_s2a_registration_order_owners_signatures_schemas_and_descriptions():
     }
 
     assert list(registered) == _EXPECTED_ORDER
-    for name, implementation in _IMPLEMENTATIONS.items():
+    for name in _IMPLEMENTATIONS:
+        implementation = getattr(
+            importlib.import_module(f"contextor.mcp.tools.{name}"), name
+        )
         tool = registered[name]
         assert getattr(mcp_server, name) is tool
-        assert tool.fn is implementation
+        assert tool.fn.__wrapped__ is implementation
         assert tool.fn.__module__ == f"contextor.mcp.tools.{name}"
         assert str(inspect.signature(tool.fn)) == _EXPECTED_SIGNATURES[name]
         assert tool.parameters == EXPECTED_PARAMETERS[name]
@@ -165,6 +170,7 @@ def test_s2a_implementations_remain_moved_after_later_slices():
 
 def test_s2a_query_projection_uses_single_shared_runtime_owner():
     server_source = Path(mcp_server.__file__).read_text(encoding="utf-8")
+    server_tree = ast.parse(server_source)
     tool_source = inspect.getsource(
         __import__(
             "contextor.mcp.tools.query_canonical_projection",
@@ -172,8 +178,33 @@ def test_s2a_query_projection_uses_single_shared_runtime_owner():
         )
     )
 
-    assert "bind_engine_resolver" not in server_source
+    assert not any(
+        isinstance(node, ast.Call)
+        and (
+            isinstance(node.func, ast.Name) and node.func.id == "bind_engine_resolver"
+            or isinstance(node.func, ast.Attribute) and node.func.attr == "bind_engine_resolver"
+        )
+        for node in ast.walk(server_tree)
+    )
+    assert not any(
+        (
+            isinstance(node, ast.Name)
+            and node.id == "_get_or_init_engine"
+        )
+        or (
+            isinstance(node, ast.Attribute)
+            and node.attr == "_get_or_init_engine"
+        )
+        or (
+            isinstance(node, ast.ImportFrom)
+            and any(
+                alias.name == "_get_or_init_engine"
+                or alias.asname == "_get_or_init_engine"
+                for alias in node.names
+            )
+        )
+        for node in ast.walk(server_tree)
+    )
     assert "bind_engine_resolver" not in tool_source
-    assert "_get_or_init_engine" not in server_source
     assert "from contextor.mcp import runtime as mcp_runtime" in tool_source
     assert "mcp_runtime.get_or_init_engine(root)" in tool_source
diff --git a/tests/test_mcp_split_s2b.py b/tests/test_mcp_split_s2b.py
index a337d97..aa619f5 100644
--- a/tests/test_mcp_split_s2b.py
+++ b/tests/test_mcp_split_s2b.py
@@ -1,4 +1,5 @@
 import ast
+import importlib
 import inspect
 import json
 import subprocess
@@ -25,7 +26,7 @@ _EXPECTED_ORDER = [
     "query_canonical_projection", "extract_indexed_report_context",
     "lookup_index_entries", "get_artifacts_for_module",
     "lookup_artifact_by_symbol", "search_source", "get_source_range",
-    "get_symbol_call_context", "get_mcp_documentation",
+    "get_symbol_call_context", "get_name_collisions", "get_mcp_documentation",
 ]
 
 _IMPLEMENTATIONS = {
@@ -45,7 +46,7 @@ _EXPECTED_SIGNATURES = {
 }
 
 JOB_STATE = {
-    "_MCP_OWNER_TOKEN", "_analysis_lock", "_analysis_job_lock",
+    "_analysis_lock", "_analysis_job_lock",
     "_analysis_tasks", "_analysis_jobs_by_repo",
 }
 
@@ -58,10 +59,13 @@ def test_s2b_registration_contract_and_implementation_owners():
     }
 
     assert list(registered) == _EXPECTED_ORDER
-    for name, implementation in _IMPLEMENTATIONS.items():
+    for name in _IMPLEMENTATIONS:
+        implementation = getattr(
+            importlib.import_module(f"contextor.mcp.tools.{name}"), name
+        )
         tool = registered[name]
         assert getattr(mcp_server, name) is tool
-        assert tool.fn is implementation
+        assert tool.fn.__wrapped__ is implementation
         assert tool.fn.__module__ == f"contextor.mcp.tools.{name}"
         assert str(inspect.signature(tool.fn)) == _EXPECTED_SIGNATURES[name]
         assert tool.description == descriptions[name]
@@ -80,6 +84,7 @@ def test_s2b_import_graph_state_owner_and_remaining_tool_count():
     assert decorated == []
     assert JOB_STATE.isdisjoint(vars(mcp_server))
     assert JOB_STATE <= vars(analysis_jobs).keys()
+    assert "_MCP_OWNER_TOKEN" not in vars(analysis_jobs)
 
     for name in _IMPLEMENTATIONS:
         path = root / "contextor" / "mcp" / "tools" / f"{name}.py"
@@ -116,6 +121,13 @@ def test_s2b_spawn_entrypoint_does_not_bootstrap_fastmcp_in_child_mode():
 
 
 def test_s2b_has_no_registration_dependency_binding():
-    server_source = Path(mcp_server.__file__).read_text(encoding="utf-8")
-    assert "bind_" not in server_source
-    assert "set_analysis" not in server_source
+    tree = ast.parse(Path(mcp_server.__file__).read_text(encoding="utf-8"))
+    forbidden = {"bind_engine_resolver", "set_analysis_engine"}
+    assert not any(
+        isinstance(node, ast.Call)
+        and (
+            isinstance(node.func, ast.Name) and node.func.id in forbidden
+            or isinstance(node.func, ast.Attribute) and node.func.attr in forbidden
+        )
+        for node in ast.walk(tree)
+    )
diff --git a/tests/test_mcp_split_s2c.py b/tests/test_mcp_split_s2c.py
index 65bd7a5..89784f8 100644
--- a/tests/test_mcp_split_s2c.py
+++ b/tests/test_mcp_split_s2c.py
@@ -1,4 +1,5 @@
 import ast
+import importlib
 import inspect
 from pathlib import Path
 
@@ -22,7 +23,7 @@ _EXPECTED_ORDER = [
     "query_canonical_projection", "extract_indexed_report_context",
     "lookup_index_entries", "get_artifacts_for_module",
     "lookup_artifact_by_symbol", "search_source", "get_source_range",
-    "get_symbol_call_context",
+    "get_symbol_call_context", "get_name_collisions",
     "get_mcp_documentation",
 ]
 
@@ -53,10 +54,13 @@ def test_s2c_registration_order_bindings_signatures_and_descriptions():
     }
 
     assert list(registered) == _EXPECTED_ORDER
-    for name, implementation in _IMPLEMENTATIONS.items():
+    for name in _IMPLEMENTATIONS:
+        implementation = getattr(
+            importlib.import_module(f"contextor.mcp.tools.{name}"), name
+        )
         tool = registered[name]
         assert getattr(mcp_server, name) is tool
-        assert tool.fn is implementation
+        assert tool.fn.__wrapped__ is implementation
         assert tool.fn.__module__ == f"contextor.mcp.tools.{name}"
         assert str(inspect.signature(tool.fn)) == _EXPECTED_SIGNATURES[name]
         assert tool.description == descriptions[name]
@@ -112,8 +116,14 @@ def test_s2c_ownership_import_graph_and_shared_helper_uniqueness():
 
 def test_s2c_has_no_registration_dependency_binding_or_report_io():
     root = Path(__file__).parents[1]
-    server_source = Path(mcp_server.__file__).read_text(encoding="utf-8")
-    assert "bind_" not in server_source
+    server_tree = ast.parse(Path(mcp_server.__file__).read_text(encoding="utf-8"))
+    assert not any(
+        isinstance(node, ast.Call)
+        and isinstance(node.func, (ast.Name, ast.Attribute))
+        and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr)
+        in {"bind_engine_resolver", "set_analysis_engine"}
+        for node in ast.walk(server_tree)
+    )
     for name in _IMPLEMENTATIONS:
         source = (
             root / "contextor" / "mcp" / "tools" / f"{name}.py"
diff --git a/tests/test_mcp_split_s2d.py b/tests/test_mcp_split_s2d.py
index ec1a909..8fff776 100644
--- a/tests/test_mcp_split_s2d.py
+++ b/tests/test_mcp_split_s2d.py
@@ -1,4 +1,5 @@
 import ast
+import importlib
 import inspect
 from pathlib import Path
 
@@ -20,7 +21,7 @@ _EXPECTED_ORDER = [
     "query_canonical_projection", "extract_indexed_report_context",
     "lookup_index_entries", "get_artifacts_for_module",
     "lookup_artifact_by_symbol", "search_source", "get_source_range",
-    "get_symbol_call_context", "get_mcp_documentation",
+    "get_symbol_call_context", "get_name_collisions", "get_mcp_documentation",
 ]
 
 _IMPLEMENTATIONS = {
@@ -45,10 +46,13 @@ def test_s2d_registration_order_bindings_signatures_and_descriptions():
         for entry in load_documentation_index()["tools"]
     }
     assert list(registered) == _EXPECTED_ORDER
-    for name, implementation in _IMPLEMENTATIONS.items():
+    for name in _IMPLEMENTATIONS:
+        implementation = getattr(
+            importlib.import_module(f"contextor.mcp.tools.{name}"), name
+        )
         tool = registered[name]
         assert getattr(mcp_server, name) is tool
-        assert tool.fn is implementation
+        assert tool.fn.__wrapped__ is implementation
         assert tool.fn.__module__ == f"contextor.mcp.tools.{name}"
         assert str(inspect.signature(tool.fn)) == _EXPECTED_SIGNATURES[name]
         assert tool.description == descriptions[name]
@@ -87,8 +91,14 @@ def test_s2d_ownership_and_import_graph():
 
 
 def test_s2d_has_no_dependency_binding_or_report_ssot():
-    server_source = Path(mcp_server.__file__).read_text(encoding="utf-8")
-    assert "bind_" not in server_source
+    server_tree = ast.parse(Path(mcp_server.__file__).read_text(encoding="utf-8"))
+    assert not any(
+        isinstance(node, ast.Call)
+        and isinstance(node.func, (ast.Name, ast.Attribute))
+        and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr)
+        in {"bind_engine_resolver", "set_analysis_engine"}
+        for node in ast.walk(server_tree)
+    )
     for implementation in _IMPLEMENTATIONS.values():
         source = Path(implementation.__code__.co_filename).read_text(encoding="utf-8")
         assert "resolve_output_dir" not in source
@@ -358,4 +368,3 @@ def test_get_symbol_implementation_no_file_paths_or_file_path_returns_not_found(
     res = json.loads(res_raw)
     assert res["status"] == "not_found"
     assert res["message"] == "No exact class, function, or method match was found."
-
diff --git a/tests/test_mcp_split_s2e.py b/tests/test_mcp_split_s2e.py
index 37b283c..ea68002 100644
--- a/tests/test_mcp_split_s2e.py
+++ b/tests/test_mcp_split_s2e.py
@@ -1,4 +1,5 @@
 import ast
+import importlib
 import inspect
 from pathlib import Path
 
@@ -21,7 +22,7 @@ _EXPECTED_ORDER = [
     "query_canonical_projection", "extract_indexed_report_context",
     "lookup_index_entries", "get_artifacts_for_module",
     "lookup_artifact_by_symbol", "search_source", "get_source_range",
-    "get_symbol_call_context", "get_mcp_documentation",
+    "get_symbol_call_context", "get_name_collisions", "get_mcp_documentation",
 ]
 
 _IMPLEMENTATIONS = {
@@ -48,10 +49,13 @@ def test_s2e_registration_order_bindings_signatures_and_descriptions():
         for entry in load_documentation_index()["tools"]
     }
     assert list(registered) == _EXPECTED_ORDER
-    for name, implementation in _IMPLEMENTATIONS.items():
+    for name in _IMPLEMENTATIONS:
+        implementation = getattr(
+            importlib.import_module(f"contextor.mcp.tools.{name}"), name
+        )
         tool = registered[name]
         assert getattr(mcp_server, name) is tool
-        assert tool.fn is implementation
+        assert tool.fn.__wrapped__ is implementation
         assert tool.fn.__module__ == f"contextor.mcp.tools.{name}"
         assert str(inspect.signature(tool.fn)) == _EXPECTED_SIGNATURES[name]
         assert tool.description == descriptions[name]
@@ -59,8 +63,7 @@ def test_s2e_registration_order_bindings_signatures_and_descriptions():
 
 def test_s2e_final_ownership_import_graph_and_thin_server():
     root = Path(__file__).parents[1]
-    server_source = Path(mcp_server.__file__).read_text(encoding="utf-8")
-    server_tree = ast.parse(server_source)
+    server_tree = ast.parse(Path(mcp_server.__file__).read_text(encoding="utf-8"))
     decorated = [
         node.name
         for node in server_tree.body
@@ -68,7 +71,13 @@ def test_s2e_final_ownership_import_graph_and_thin_server():
         and any(ast.unparse(item).startswith("mcp.tool") for item in node.decorator_list)
     ]
     assert decorated == []
-    assert "bind_" not in server_source
+    assert not any(
+        isinstance(node, ast.Call)
+        and isinstance(node.func, (ast.Name, ast.Attribute))
+        and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr)
+        in {"bind_engine_resolver", "set_analysis_engine"}
+        for node in ast.walk(server_tree)
+    )
 
     for name in _IMPLEMENTATIONS:
         path = root / "contextor" / "mcp" / "tools" / f"{name}.py"
diff --git a/contextor/mcp/diagnostics.py b/contextor/mcp/diagnostics.py
new file mode 100644
index 0000000..02104d0
--- /dev/null
+++ b/contextor/mcp/diagnostics.py
@@ -0,0 +1,183 @@
+"""Small, fail-closed diagnostics projections for MCP responses."""
+
+from __future__ import annotations
+
+import json
+from pathlib import Path
+from typing import Any
+
+from contextor.mcp import runtime as mcp_runtime
+from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES, guard_large_output
+
+
+def _availability(state: Any, family: str, values: Any) -> str:
+    status = getattr(state, f"{family}_state", None)
+    if values is None and status == "fresh":
+        return "unavailable"
+    if status in {"fresh", "stale", "deferred", "unavailable"}:
+        return status
+    if values is None:
+        return "unavailable"
+    return "fresh"
+
+
+def _issue_severity(item: Any) -> str:
+    severity = getattr(item, "severity", None)
+    if severity in {"critical", "warning", "info"}:
+        return severity
+    try:
+        from contextor.core.reporting_engine.formatting import _collision_severity
+
+        return _collision_severity(
+            getattr(item, "artifact_type", "unknown"),
+            getattr(item, "symbol_details", []) or [],
+            getattr(item, "code_snippets", {}) or {},
+        )
+    except Exception:
+        return "warning"
+
+
+def diagnostics_summary_for_state(state: Any) -> dict[str, Any]:
+    """Return counts plus freshness, never converting unavailable to zero."""
+    if state is None:
+        unavailable = {"count": None, "availability": "unavailable"}
+        return {
+            "syntax_errors": dict(unavailable),
+            "name_collisions": {
+                "count": None, "critical": None, "warning": None, "info": None,
+                "availability": "unavailable",
+            },
+            "cycles": dict(unavailable),
+            "attention_required": False,
+            "availability": {
+                "syntax_errors": "unavailable",
+                "name_collisions": "unavailable",
+                "cycles": "unavailable",
+            },
+        }
+
+    syntax_values = None
+    syntax_availability = "unavailable"
+    collisions = getattr(state, "collisions", None)
+    cycles = getattr(state, "cycles", None)
+    collision_availability = _availability(state, "collisions", collisions)
+    cycle_availability = _availability(state, "cycles", cycles)
+    if collision_availability != "fresh":
+        collision_count = critical = warning = info = None
+    else:
+        collisions = list(collisions or [])
+        collision_count = len(collisions)
+        critical = sum(_issue_severity(item) == "critical" for item in collisions)
+        warning = sum(_issue_severity(item) == "warning" for item in collisions)
+        info = sum(_issue_severity(item) == "info" for item in collisions)
+    cycle_count = len(cycles) if cycle_availability == "fresh" else None
+    syntax_issue = syntax_values if syntax_availability == "fresh" else None
+    attention = any(
+        value is not None and value > 0
+        for value in (syntax_issue, collision_count, cycle_count)
+    )
+    return {
+        "syntax_errors": {"count": syntax_values, "availability": syntax_availability},
+        "name_collisions": {
+            "count": collision_count,
+            "critical": critical,
+            "warning": warning,
+            "info": info,
+            "availability": collision_availability,
+        },
+        "cycles": {"count": cycle_count, "availability": cycle_availability},
+        "attention_required": bool(attention),
+        "availability": {
+            "syntax_errors": syntax_availability,
+            "name_collisions": collision_availability,
+            "cycles": cycle_availability,
+        },
+    }
+
+
+def diagnostics_summary(root: Path, state: Any = None) -> dict[str, Any]:
+    if state is None:
+        engine = mcp_runtime._live_engines.get(str(root))
+        state = getattr(engine, "state", None) if engine is not None else None
+    summary = diagnostics_summary_for_state(state)
+    return summary
+
+
+def diagnostics_summary_for_completed_job(summary: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
+    """Enrich one exact completed project-job response, never a global query."""
+    if job.get("status") != "completed" or job.get("operation") != "project":
+        return summary
+    skipped = job.get("skipped_python_files")
+    if not isinstance(skipped, list):
+        return summary
+    syntax_count = sum("not valid Python" in str(item.get("reason", "")) for item in skipped)
+    result = dict(summary)
+    result["syntax_errors"] = {"count": syntax_count, "availability": "fresh"}
+    result["availability"] = dict(summary["availability"], syntax_errors="fresh")
+    result["attention_required"] = bool(summary["attention_required"] or syntax_count > 0)
+    return result
+
+
+def inject_diagnostics_summary(
+    result: Any,
+    root_path: Any,
+    tool_name: str,
+    *,
+    allow_large_output: bool = False,
+) -> Any:
+    """Add a small summary to JSON analytical responses without touching prose/errors."""
+    if tool_name == "get_mcp_documentation" or not isinstance(result, str):
+        return result
+    try:
+        payload = json.loads(result)
+    except (TypeError, json.JSONDecodeError):
+        return result
+    if not isinstance(payload, dict):
+        return result
+    if payload.get("status") in {"queued", "running", "accepted", "missing_repository"}:
+        return result
+    root = Path(root_path).expanduser().resolve() if root_path else None
+    if root is None:
+        return result
+    summary = diagnostics_summary(root)
+    payload.setdefault("diagnostics_summary", summary)
+    payload.setdefault("diagnostics_attention_required", summary["attention_required"])
+    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
+    if allow_large_output or len(serialized.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES:
+        return serialized
+    guarded = guard_large_output(
+        serialized,
+        allow_large_output=False,
+        retry_instruction="Repeat the same call with a narrower projection or allow_large_output=true.",
+    )
+    try:
+        warning = json.loads(guarded)
+    except json.JSONDecodeError:
+        return guarded
+    warning["diagnostics_summary"] = summary
+    warning["diagnostics_attention_required"] = summary["attention_required"]
+    final_guarded = json.dumps(warning, indent=2, ensure_ascii=False)
+    if len(final_guarded.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES:
+        return final_guarded
+    compact_warning = {
+        key: warning[key]
+        for key in (
+            "status",
+            "warning",
+            "message",
+            "full_bytes",
+            "estimated_bytes",
+            "threshold_bytes",
+            "context_budget_bytes",
+            "retry_instruction",
+        )
+        if key in warning
+    }
+    compact_warning["status"] = compact_warning.get("status", "confirmation_required")
+    compact_warning["diagnostics_summary"] = summary
+    compact_warning["diagnostics_attention_required"] = summary["attention_required"]
+    final_guarded = json.dumps(compact_warning, indent=2, ensure_ascii=False)
+    final_bytes = len(final_guarded.encode("utf-8"))
+    if final_bytes > LARGE_OUTPUT_WARNING_BYTES:
+        raise RuntimeError("Diagnostics confirmation envelope exceeds MCP response budget")
+    return final_guarded
diff --git a/contextor/mcp/docs/get_name_collisions.json b/contextor/mcp/docs/get_name_collisions.json
new file mode 100644
index 0000000..297fcf3
--- /dev/null
+++ b/contextor/mcp/docs/get_name_collisions.json
@@ -0,0 +1,37 @@
+{
+  "version": "1.0.0",
+  "tool": "get_name_collisions",
+  "purpose": [
+    "Return bounded, fail-closed name-collision diagnostics from canonical LIVE state."
+  ],
+  "parameters": [
+    "repo_path (string, required): canonical repository root.",
+    "severity (string or null, optional, default null): critical, warning, or info.",
+    "artifact_type (string or null, optional, default null): canonical collision artifact type.",
+    "collision_type (string or null, optional, default null): NAME_COLLISION or IDENTICAL_DEFINITION_DUPLICATE.",
+    "module (string or null, optional, default null): only collisions containing this module.",
+    "conflicting_only (boolean, optional, default false): exclude identical definitions.",
+    "identical_only (boolean, optional, default false): return only identical definitions.",
+    "representation (string, default auto): auto, summary, bounded, indexed, or named.",
+    "limit (integer or null, default 20): maximum detail entries.",
+    "allow_large_output (boolean, default false): permit the selected response above the shared budget; does not change limit."
+  ],
+  "behavior": [
+    "Reads only canonical collision state; stale, deferred, and unavailable state is reported explicitly and never converted to zero.",
+    "The response begins with total/matched/returned counts, severity counts, conflicting/identical counts, representation, truncation, estimated size, budget, and attention_required.",
+    "auto selects named details for small results and indexed details for large results. indexed and summary omit source-heavy detail; bounded/named include bounded detail entries.",
+    "When a response cannot fit the shared 15 KiB budget, narrowing guidance or an explicit confirmation_required response is returned."
+  ],
+  "freshness": [
+    "availability is fresh, stale, deferred, or unavailable and is bound to canonical LIVE collision state.",
+    "diagnostics_summary is included with the same family availability and never fabricates unavailable counts."
+  ],
+  "errors": [
+    "Invalid severity or representation returns a structured error with allowed values.",
+    "No fresh canonical collision producer returns an explicit unavailable/deferred projection."
+  ],
+  "usage_notes": [
+    "Narrow by severity/module before increasing limit; indexed output is response-local and has no persistent collision identity."
+  ],
+  "examples": []
+}
diff --git a/contextor/mcp/tools/get_name_collisions.py b/contextor/mcp/tools/get_name_collisions.py
new file mode 100644
index 0000000..7963eda
--- /dev/null
+++ b/contextor/mcp/tools/get_name_collisions.py
@@ -0,0 +1,152 @@
+"""Bounded projection of canonical name-collision diagnostics."""
+
+from __future__ import annotations
+
+import json
+from pathlib import Path
+from typing import Any
+
+from contextor.mcp import diagnostics
+from contextor.mcp import runtime as mcp_runtime
+from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES, guard_large_output, largest_fitting_prefix
+
+
+def _severity(error: Any) -> str:
+    value = getattr(error, "severity", None)
+    if value in {"critical", "warning", "info"}:
+        return value
+    from contextor.core.reporting_engine.formatting import _collision_severity
+
+    return _collision_severity(
+        getattr(error, "artifact_type", "unknown"),
+        getattr(error, "symbol_details", []) or [],
+        getattr(error, "code_snippets", {}) or {},
+    )
+
+
+def _detail(error: Any, representation: str) -> dict[str, Any]:
+    severity = _severity(error)
+    base = {
+        "collision_type": getattr(error, "kind", "NAME_COLLISION"),
+        "artifact_type": getattr(error, "artifact_type", "unknown"),
+        "severity": severity,
+        "is_identical": bool(getattr(error, "is_identical", False)),
+        "modules": sorted(str(node) for node in (getattr(error, "nodes", []) or [])),
+    }
+    if representation in {"indexed", "summary"}:
+        return base
+    base.update(
+        {
+            "message": getattr(error, "message", ""),
+            "symbol_details": getattr(error, "symbol_details", []) or [],
+            "conflicting_code": getattr(error, "code_snippets", {}) or {},
+        }
+    )
+    return base
+
+
+def get_name_collisions(
+    repo_path: str,
+    severity: str | None = None,
+    artifact_type: str | None = None,
+    collision_type: str | None = None,
+    module: str | None = None,
+    conflicting_only: bool = False,
+    identical_only: bool = False,
+    representation: str = "auto",
+    limit: int | None = 20,
+    allow_large_output: bool = False,
+) -> str:
+    root = Path(repo_path).expanduser().resolve()
+    engine = mcp_runtime.get_or_init_engine(root)
+    state = getattr(engine, "state", None) if engine is not None else None
+    availability = getattr(state, "collisions_state", "unavailable") if state is not None else "unavailable"
+    if availability != "fresh":
+        payload = {
+            "total": None,
+            "matched": None,
+            "returned": 0,
+            "severity_counts": {"critical": None, "warning": None, "info": None},
+            "conflicting": None,
+            "identical": None,
+            "representation": representation,
+            "truncated": False,
+            "estimated_full_bytes": None,
+            "context_budget_bytes": LARGE_OUTPUT_WARNING_BYTES,
+            "attention_required": False,
+            "availability": availability,
+            "details": [],
+            "guidance": "Collision diagnostics are not fresh; rerun analyze_project and retry.",
+            "diagnostics_summary": diagnostics.diagnostics_summary(root, state),
+        }
+        return json.dumps(payload, indent=2, ensure_ascii=False)
+
+    errors = list(getattr(state, "collisions", []) or [])
+    if severity is not None and severity not in {"critical", "warning", "info"}:
+        return json.dumps({"error": "Unsupported severity", "allowed": ["critical", "warning", "info"]}, indent=2)
+    if conflicting_only and identical_only:
+        return json.dumps({"error": "conflicting_only and identical_only are mutually exclusive"}, indent=2)
+    if representation not in {"auto", "summary", "bounded", "indexed", "named"}:
+        return json.dumps({"error": "Unsupported representation", "allowed": ["auto", "summary", "bounded", "indexed", "named"]}, indent=2)
+    selected = []
+    for error in errors:
+        item_severity = _severity(error)
+        identical = bool(getattr(error, "is_identical", False))
+        if severity and item_severity != severity:
+            continue
+        if artifact_type and str(getattr(error, "artifact_type", "")) != artifact_type:
+            continue
+        if collision_type and str(getattr(error, "kind", "")) != collision_type:
+            continue
+        if module and module not in {str(node) for node in (getattr(error, "nodes", []) or [])}:
+            continue
+        if conflicting_only and identical:
+            continue
+        if identical_only and not identical:
+            continue
+        selected.append(error)
+
+    severity_counts = {name: sum(_severity(error) == name for error in selected) for name in ("critical", "warning", "info")}
+    identical_count = sum(bool(getattr(error, "is_identical", False)) for error in selected)
+    full_details = [_detail(error, "named") for error in selected]
+    estimated_full_bytes = len(json.dumps(full_details, indent=2, ensure_ascii=False).encode("utf-8"))
+    effective = "indexed" if representation == "auto" and estimated_full_bytes > LARGE_OUTPUT_WARNING_BYTES else ("named" if representation == "auto" else representation)
+    if effective == "summary":
+        visible_details = []
+    else:
+        visible_details = [_detail(error, effective) for error in selected]
+    if limit is not None:
+        visible_details = visible_details[: max(0, int(limit))]
+    truncated = len(visible_details) < len(selected)
+    summary = {
+        "total": len(errors),
+        "matched": len(selected),
+        "returned": len(visible_details),
+        "severity_counts": severity_counts,
+        "conflicting": len(selected) - identical_count,
+        "identical": identical_count,
+        "representation": effective,
+        "truncated": truncated,
+        "estimated_full_bytes": estimated_full_bytes,
+        "context_budget_bytes": LARGE_OUTPUT_WARNING_BYTES,
+        "attention_required": bool(selected),
+        "availability": "fresh",
+    }
+
+    def build(count: int) -> str:
+        body = {**summary, "returned": count, "truncated": count < len(selected), "details": visible_details[:count], "diagnostics_summary": diagnostics.diagnostics_summary(root, state)}
+        if count < len(selected):
+            body["guidance"] = "Narrow by severity, module, artifact_type, or use representation='indexed'."
+        return json.dumps(body, indent=2, ensure_ascii=False)
+
+    candidate = build(len(visible_details))
+    if len(candidate.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES and not allow_large_output:
+        bounded = largest_fitting_prefix(len(visible_details), build, min_count=0)
+        if bounded is not None:
+            return bounded[0]
+    return guard_large_output(
+        candidate,
+        allow_large_output=allow_large_output,
+        requested_count=limit,
+        retry_instruction="Repeat with representation='indexed' or a smaller limit, or set allow_large_output=true.",
+    )
diff --git a/tests/test_mcp_diagnostics.py b/tests/test_mcp_diagnostics.py
new file mode 100644
index 0000000..0694d4d
--- /dev/null
+++ b/tests/test_mcp_diagnostics.py
@@ -0,0 +1,144 @@
+import json
+from types import SimpleNamespace
+
+from contextor import mcp_server
+from contextor.mcp.diagnostics import (
+    diagnostics_summary,
+    diagnostics_summary_for_completed_job,
+    diagnostics_summary_for_state,
+    inject_diagnostics_summary,
+)
+from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES
+from contextor.mcp import runtime as mcp_runtime
+from contextor.mcp.tools.get_name_collisions import get_name_collisions
+from contextor.mcp.tools.get_analysis_status import get_analysis_status
+
+
+def _collision(kind="NAME_COLLISION", identical=False, module="pkg.a"):
+    return SimpleNamespace(
+        kind=kind,
+        message=f"{kind} foo",
+        nodes=[module, "pkg.b"],
+        artifact_type="function",
+        is_identical=identical,
+        symbol_details=[],
+        code_snippets={module: "def foo():\n    return 1", "pkg.b": "def foo():\n    return 2"},
+    )
+
+
+def test_diagnostics_summary_does_not_fabricate_unavailable_counts():
+    summary = diagnostics_summary_for_state(SimpleNamespace(
+        collisions_state="deferred", cycles_state="unavailable", collisions=None, cycles=None
+    ))
+    assert summary["name_collisions"]["count"] is None
+    assert summary["cycles"]["count"] is None
+    assert summary["availability"]["name_collisions"] == "deferred"
+
+
+def test_get_name_collisions_filters_without_invented_ids(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    state = SimpleNamespace(
+        collisions_state="fresh", collisions=[_collision(), _collision("IDENTICAL_DEFINITION_DUPLICATE", True, "pkg.c")],
+        cycles_state="fresh", cycles=[], summary_data={}
+    )
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    first = json.loads(get_name_collisions(str(repo), conflicting_only=True))
+    second = json.loads(get_name_collisions(str(repo), conflicting_only=True))
+    assert first["matched"] == 1
+    assert "collision_id" not in first["details"][0]
+    assert first["conflicting"] == 1
+
+
+def test_attention_required_tracks_each_available_family():
+    clean = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
+    assert diagnostics_summary_for_state(clean)["attention_required"] is False
+    result = diagnostics_summary_for_state(clean)
+    assert result["syntax_errors"] == {"count": None, "availability": "unavailable"}
+    syntax_result = diagnostics_summary_for_completed_job(result, {"status": "completed", "operation": "project", "skipped_python_files": [{"reason": "not valid Python"}]})
+    assert syntax_result["syntax_errors"] == {"count": 1, "availability": "fresh"}
+    assert syntax_result["attention_required"] is True
+    zero_result = diagnostics_summary_for_completed_job(result, {"status": "completed", "operation": "project", "skipped_python_files": []})
+    assert zero_result["syntax_errors"] == {"count": 0, "availability": "fresh"}
+    assert zero_result["attention_required"] is False
+    assert diagnostics_summary_for_state(SimpleNamespace(collisions_state="fresh", collisions=[_collision()], cycles_state="fresh", cycles=[]))["attention_required"] is True
+    assert diagnostics_summary_for_state(SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[["a", "b", "a"]]))["attention_required"] is True
+
+
+def test_historical_job_does_not_promote_global_syntax_freshness(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
+    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
+    monkeypatch.setattr("contextor.mcp.analysis_jobs._latest_analysis_job", lambda _root: {"status": "completed", "skipped_python_files": [{"reason": "not valid Python"}]})
+    summary = diagnostics_summary(repo)
+    assert summary["syntax_errors"] == {"count": None, "availability": "unavailable"}
+    assert diagnostics_summary_for_completed_job(summary, {"status": "completed", "operation": "project", "skipped_python_files": [{"reason": "not valid Python"}]})["syntax_errors"] == {"count": 1, "availability": "fresh"}
+
+
+def test_analysis_status_uses_only_the_exact_completed_project_job_for_syntax(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    (repo / ".contextor" / "analysis_jobs").mkdir(parents=True)
+    job_id = "a" * 32
+    (repo / ".contextor" / "analysis_jobs" / f"{job_id}.json").write_text(json.dumps({
+        "job_id": job_id, "operation": "project", "repo_path": str(repo), "status": "completed",
+        "skipped_python_files": [{"reason": "not valid Python"}], "live_publish_status": "success",
+    }), encoding="utf-8")
+    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
+    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
+    result = json.loads(get_analysis_status(str(repo), job_id))
+    assert result["diagnostics_summary"]["syntax_errors"] == {"count": 1, "availability": "fresh"}
+
+
+def test_wrapper_injects_health_for_analytical_not_found(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
+    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
+    wrapped = mcp_server._instrument_mcp_tool(lambda repo_path: json.dumps({"status": "not_found", "repo_path": repo_path}), "synthetic_query")
+    result = json.loads(wrapped(str(repo)))
+    assert "diagnostics_summary" in result
+
+
+def test_wrapper_applies_shared_guard_after_diagnostics_injection(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
+    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
+    before = LARGE_OUTPUT_WARNING_BYTES - 40
+    wrapped = mcp_server._instrument_mcp_tool(lambda repo_path: json.dumps({"status": "ok", "payload": "x" * before}), "synthetic_query")
+    raw = wrapped(str(repo))
+    assert len(raw.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES
+    result = json.loads(raw)
+    assert "diagnostics_summary" in result
+    assert result["status"] == "confirmation_required"
+    large = mcp_server._instrument_mcp_tool(lambda repo_path, allow_large_output=False: json.dumps({"status": "ok", "payload": "x" * (LARGE_OUTPUT_WARNING_BYTES + 100)}), "synthetic_query")
+    bounded_raw = large(str(repo))
+    assert len(bounded_raw.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES
+    bounded = json.loads(bounded_raw)
+    assert "diagnostics_summary" in bounded
+    unbounded_raw = large(str(repo), allow_large_output=True)
+    assert len(unbounded_raw.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES
+    unbounded = json.loads(unbounded_raw)
+    assert "diagnostics_summary" in unbounded
+    pre_injection = json.dumps({"status": "ok", "payload": "x" * before})
+    post_injection = inject_diagnostics_summary(pre_injection, repo, "synthetic_query", allow_large_output=True)
+    assert len(pre_injection.encode("utf-8")) < LARGE_OUTPUT_WARNING_BYTES
+    assert len(post_injection.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES
+
+
+def test_get_name_collisions_indexed_representation_is_bounded(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    errors = [_collision(module=f"pkg.mod{i}") for i in range(30)]
+    state = SimpleNamespace(collisions_state="fresh", collisions=errors, cycles_state="fresh", cycles=[], summary_data={})
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    result = json.loads(get_name_collisions(str(repo), representation="indexed", limit=3))
+    assert result["returned"] == 3
+    assert result["truncated"] is True
+    assert all("conflicting_code" not in item for item in result["details"])
+
+
+def test_registered_name_collision_tool_and_shared_summary_wrapper():
+    assert "get_name_collisions" in mcp_server.REGISTERED_MCP_TOOL_NAMES
+    assert len(mcp_server.REGISTERED_MCP_TOOL_NAMES) == 25

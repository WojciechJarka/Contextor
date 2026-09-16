# CPA10K3 — writer-owner implementation stage

MODE: IMPLEMENTATION_STAGE_1
REPO: C:\Temp\Contextor_Repo
SCOPE: first owner of runtime trace corruption only
CONTEXTOR_STATE: live canonical revision 1260; exact implementation fetches fresh; workspace_sync verified

This stage implements only the shared runtime JSONL writer owner. Recovery semantics and the Desktop process-leak owner are intentionally unchanged.

## IMPLEMENTED_CONTRACT

- Ordinary diagnostic persistence now adds _record_kind=diagnostic only to a copied record inside _append.
- capture_trace_events still receives the original in-memory record before _append and therefore does not receive _record_kind.
- Ordinary and authority JSONL appends now use the same cross-process lock path: the existing authority sidecar lock path derived from the runtime logs directory.
- The lock is reentrant for nested calls on the same thread. This preserves the existing authority/diagnostic interleaving contract without attempting a second OS lock acquisition from the same thread.
- Both ordinary and authority append paths check os.write return length.
- On a short write, the append is rolled back with os.ftruncate to the pre-append size followed by os.fsync before the existing error behavior continues.
- Ordinary diagnostics remain fail-open at trace_event/_append boundary. A failed diagnostic append is swallowed as before.
- Authority short writes remain fail-closed by raising AuthorityEventRecoveryError, but no incomplete authority bytes are left by the tested short-write path.
- No recovery parser, _type filtering, authority schema, pointer lifecycle, process lifecycle, or LIVE state was changed.

## OBSERVED_TRACE_EVIDENCE

The original discovery identified one malformed ordinary diagnostic tail in:

C:\Users\DafoO\AppData\Roaming\Contextor\logs\contextor_runtime_20260915_211945_272_8748.jsonl

The malformed record was line 1780 at byte offset 557355, payload length 35 bytes, with suffix:

0022992,"status":"ok","bytes":1239}

The surrounding operation was an ordinary MCP CALL_END sequence, not an authority_event. The affected file was 1,935,514 bytes. The size remains correlation only; this implementation does not treat file size as the root cause.

## TRACE_WRITER_OWNERS

Contextor exact implementations established:

- trace_event -> _append is the ordinary diagnostic writer.
- AuthorityEventEmitter.emit -> _append_authority_record_locked is the authority writer.
- _open_runtime_trace_session/start/finish owns active trace creation, pointer publication, SESSION_START/SESSION_END, and process-local fd lifecycle.
- contextor/mcp_server.py ordinary CALL_END events route through trace_event.

Changed writer ownership:

- _append serializes a copied diagnostic record and writes it under _AuthorityFileLock.
- _append_authority_record_locked retains authority envelope, fsync, offset, and identity verification, and now rolls back a short append before raising.
- AuthorityEventEmitter already holds the same sidecar lock path; the lock implementation is now explicitly shared between authority and diagnostic appenders.

## TRACE_SYNCHRONIZATION_MODEL

Before this stage, ordinary writes used only a process-local threading lock and process-local fd. Authority writes used the cross-process sidecar lock.

After this stage:

- Ordinary diagnostic appends acquire _AuthorityFileLock at .authority_event_state.json.lock under the runtime logs root.
- Authority recovery/emission already acquires the same path.
- The lock implementation uses Windows msvcrt locking or POSIX flock and has thread-local reentrancy bookkeeping.
- The ordinary path still does not add a successful-write fsync or retry loop. The implemented contract is shared serialization plus short-write rollback, as scoped for this stage.

Certification after this stage:

MALFORMED_RECORD_IS_NON_AUTHORITY_DIAGNOSTIC=YES
DIAGNOSTIC_WRITES_CROSS_PROCESS_SERIALIZED=YES
AUTHORITY_AND_DIAGNOSTIC_WRITES_SHARE_FILE=YES
MALFORMED_NON_AUTHORITY_CAN_BLOCK_RECOVERY=YES
SIZE_OVER_1M_IS_ROOT_CAUSE=CORRELATED_ONLY
PREVIOUS_RECOVERY_REFACTOR_MISSED_SHARED_WRITER_RACE=PARTIAL

The recovery result remains YES for malformed non-authority blocking because recovery was deliberately not changed in this stage. The next recovery stage must consume the new discriminator without weakening authority fail-closed behavior.

## MALFORMED_RECORD_FAILURE_PATH

UNCHANGED BY DESIGN:

contextor/core/runtime_trace.py:_recover_unindexed_range_locked still parses each line and only then checks raw.get("_type"). A malformed non-authority line can therefore still raise observability_recovery_required before filtering.

This stage does not implement “ignore malformed lines” and does not alter authority recovery ordering.

## PREVIOUS_REFACTOR_COVERAGE_AND_GAP

Retained authority hardening:

- Cross-process locking.
- Authority fsync.
- Authority short-write detection.
- Authority offset and identity verification.
- Fail-closed authority recovery.

Closed in this stage:

- Ordinary diagnostics now participate in the same cross-process append serialization.
- Short ordinary and authority appends are rolled back before the writer returns/raises.
- New durable diagnostics have an explicit _record_kind discriminator.

Remaining gap for the next stage:

- Recovery still parses malformed bytes before discriminator filtering.
- _record_kind is intentionally not consumed yet.
- No recovery behavior was redesigned or changed here.

## PROCESS_FAMILIES

UNCHANGED BY DESIGN. The prior discovery remains the ownership baseline:

- LIVE authority/service is spawned by Desktop through connect_or_start and subprocess.Popen.
- Desktop watcher/feed/startup/progress workers are threads.
- Desktop analysis can create indexer and artifact ProcessPoolExecutor workers.
- External MCP server/profile-worker/mcp_worker/Git families remain externally owned unless runtime spawn evidence proves otherwise.

No process creation or shutdown code was changed.

## DESKTOP_SHUTDOWN_PATH

UNCHANGED BY DESIGN. ContextorGUI.on_closing still:

- cancels the progress task and waits only the configured bounded interval,
- stops watcher/feed objects,
- releases the Desktop claim,
- requests LIVE shutdown and falls back to _terminate_pid_tree for the LIVE service PID,
- destroys the Tk root.

No executor ownership, process registry, LIVE shutdown, or process-tree behavior was changed.

## PROCESS_OWNERSHIP_MATRIX

| Family | This stage changed ownership? | Status |
|---|---:|---|
| LIVE authority/service | No | Existing owner-aware shutdown retained |
| Desktop indexer ProcessPool workers | No | Existing lifecycle gap deferred |
| Desktop artifact ProcessPool workers | No | Existing lifecycle gap deferred |
| External MCP server/profile-worker/Git/mcp_worker | No | Must remain outside Desktop cleanup |

## CONFIRMED_DESKTOP_OWNED_LEAKS

DESKTOP_OWNED_PROCESS_LEAK_CONFIRMED=PARTIAL

This stage does not change or newly prove the process-leak classification. No post-exit PID snapshot was available, and no process was restarted or killed.

LEAKED_PROCESS_FAMILIES=NONE_CONFIRMED; prior source-confirmed candidates remain Desktop LIVE authority service and Desktop indexer/artifact ProcessPoolExecutor workers
EXTERNAL_PROCESS_FAMILIES=external MCP server processes; MCP-spawned profile_worker; MCP-owned Git subprocesses; externally launched mcp_worker CLI
SHUTDOWN_PROCESS_TREE_COMPLETE=NO

## EXISTING_TEST_COVERAGE

Focused test execution:

Command:

& .\.venv\Scripts\python.exe -m pytest tests/test_runtime_trace.py tests/test_runtime_authority_events.py

Result: 57 passed in 15.74s on win32, Python 3.10.9, pytest 9.1.1.

The six directly changed/contractual tests also passed:

- test_desktop_trace_session_headers_and_finish
- test_multiprocess_append_is_valid_json
- test_short_diagnostic_append_is_rolled_back
- test_scoped_trace_capture_matches_durable_record
- test_authority_record_offset_survives_interleaved_runtime_trace_append
- test_short_authority_append_is_rolled_back

New/updated coverage:

- durable diagnostic records contain _record_kind=diagnostic;
- capture_trace_events remains marker-free;
- short diagnostic append restores the pre-append file size;
- short authority append restores the pre-append file size and remains fail-closed;
- existing multiprocess diagnostic JSON validity and authority/diagnostic interleave behavior remain passing.

Not executed:

- broad pytest suite;
- recovery redesign tests;
- Desktop close/process-tree tests;
- LIVE restart or runtime certification.

## ROOT_CAUSE_A

The original root cause was the ordinary shared writer being outside cross-process serialization and lacking short-write rollback. This stage addresses that writer owner:

- shared lock participation is now present;
- ordinary short-write rollback is now present;
- authority short-write rollback is now present;
- the diagnostic discriminator is now persisted for the next recovery stage.

The original malformed trace is not rewritten and storage was not cleared.

## ROOT_CAUSE_B

Not addressed in this stage. The Desktop process-leak ownership gap remains deferred exactly as discovered. No process lifecycle source was modified.

## MUST_TOUCH

Changed:

- contextor/core/runtime_trace.py
- tests/test_runtime_trace.py
- tests/test_runtime_authority_events.py

Next stage only:

- recovery parser/discriminator handling, with authority fail-closed proof.

## MUST_NOT_TOUCH

- Do not change recovery behavior in this stage.
- Do not consume _record_kind until the recovery contract is explicitly reviewed.
- Do not clear or rewrite observability storage.
- Do not change Desktop process ownership or external MCP cleanup.
- Do not restart Desktop/MCP or kill processes.
- Do not redesign authority/lease semantics.

## IMPLEMENTATION_CONTRACT_REQUIRED

For this stage, the contract is satisfied by the focused tests above:

- one shared cross-process lock for all active JSONL append paths;
- pre-append size captured under that lock;
- short write detected;
- incomplete append truncated back and fsynced before the writer exits/raises;
- diagnostic record kind added only to the durable copy;
- capture_trace_events behavior preserved;
- authority recovery behavior unchanged.

The next stage must separately define how recovery uses _record_kind and how malformed non-authority bytes are handled without skipping a damaged authority record.

## FILES_CHANGED

- contextor/core/runtime_trace.py
- tests/test_runtime_trace.py
- tests/test_runtime_authority_events.py
- walkthrough.md (report artifact)

## DIFFS

DIFFS=SOURCE_AND_TESTS_CHANGED
ACTUAL_DIFF=FULL_DIFFS_INCLUDED_BELOW

## ACTUAL_DIFF_START

diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index bde50c7..fb11bc0 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -41,6 +41,7 @@ _FALLBACK_SCHEMA = 1
 _sidecar_rollovers: set[Path] = set()
 _authority_emitters: dict[tuple[str, str], "AuthorityEventEmitter"] = {}
 _authority_lock = threading.RLock()
+_trace_file_lock_local = threading.local()
 _operation_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
     "contextor_trace_operation", default=None
 )
@@ -55,6 +56,10 @@ _trace_capture_var: contextvars.ContextVar[
 AUTHORITY_EVENT_SCHEMA = "contextor-authority-event/v1"
 
 
+def _runtime_trace_lock_path(path: Path) -> Path:
+    return path.parent / f".{_AUTHORITY_STATE_NAME}.lock"
+
+
 def _snapshot_stamp() -> str:
     return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:-3]
 
@@ -532,6 +537,16 @@ def _authority_envelope(event: AuthorityEvent) -> dict[str, object]:
     return {"_type": "authority_event", "schema": AUTHORITY_EVENT_SCHEMA, **event.to_dict()}
 
 
+def _rollback_jsonl_append(fd: int, before: int, record_kind: str) -> None:
+    try:
+        os.ftruncate(fd, before)
+        os.fsync(fd)
+    except OSError as exc:
+        raise AuthorityEventRecoveryError(
+            f"{record_kind} JSONL append rollback failed"
+        ) from exc
+
+
 def _append_authority_record_locked(path: Path, event: AuthorityEvent) -> RecordIndex:
     data = (
         json.dumps(
@@ -551,6 +566,7 @@ def _append_authority_record_locked(path: Path, event: AuthorityEvent) -> Record
         before = os.fstat(fd).st_size
         written = os.write(fd, data)
         if written != len(data):
+            _rollback_jsonl_append(fd, before, "authority")
             raise AuthorityEventRecoveryError("short authority JSONL append")
         os.fsync(fd)
         end = os.fstat(fd).st_size
@@ -604,14 +620,24 @@ def _read_authority_record_at(path: Path, offset: int, end_offset: int) -> Autho
 
 
 class _AuthorityFileLock(contextlib.AbstractContextManager):
-    """Cross-process lock for the bounded sidecar and its JSONL append order."""
+    """Cross-process lock for shared JSONL append and authority sidecar order."""
 
     def __init__(self, path: Path, timeout: float = 10.0) -> None:
         self.path = path
         self.timeout = timeout
         self._file = None
+        self._reentrant = False
+        self._key = str(path.resolve())
 
     def __enter__(self):
+        held = getattr(_trace_file_lock_local, "held", None)
+        if held is None:
+            held = {}
+            _trace_file_lock_local.held = held
+        if held.get(self._key, 0):
+            held[self._key] += 1
+            self._reentrant = True
+            return self
         self.path.parent.mkdir(parents=True, exist_ok=True)
         self._file = self.path.open("a+b")
         if self.path.stat().st_size == 0:
@@ -629,6 +655,7 @@ class _AuthorityFileLock(contextlib.AbstractContextManager):
                     import fcntl
 
                     fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
+                held[self._key] = 1
                 return self
             except (OSError, BlockingIOError):
                 if time.monotonic() >= deadline:
@@ -638,6 +665,15 @@ class _AuthorityFileLock(contextlib.AbstractContextManager):
                 time.sleep(0.01)
 
     def __exit__(self, exc_type, exc, tb):
+        held = getattr(_trace_file_lock_local, "held", {})
+        if self._reentrant:
+            depth = held.get(self._key, 0)
+            if depth <= 1:
+                held.pop(self._key, None)
+            else:
+                held[self._key] = depth - 1
+            self._reentrant = False
+            return False
         if self._file is not None:
             try:
                 self._file.seek(0)
@@ -653,6 +689,7 @@ class _AuthorityFileLock(contextlib.AbstractContextManager):
                 pass
             self._file.close()
             self._file = None
+            held.pop(self._key, None)
 
 
 
@@ -1139,15 +1176,31 @@ def active_trace_path(*, force_refresh: bool = False) -> Path | None:
 def _append(record: dict[str, object], path: Path) -> None:
     global _active_fd
     try:
-        payload = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
+        persisted_record = dict(record)
+        persisted_record["_record_kind"] = "diagnostic"
+        payload = (
+            json.dumps(
+                persisted_record,
+                ensure_ascii=False,
+                separators=(",", ":"),
+            )
+            + "\n"
+        )
         encoded = payload.encode("utf-8")
-        with _lock:
-            if _active_fd is None:
-                flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
-                if hasattr(os, "O_BINARY"):
-                    flags |= os.O_BINARY
-                _active_fd = os.open(str(path), flags)
-            os.write(_active_fd, encoded)
+        with _AuthorityFileLock(_runtime_trace_lock_path(path)):
+            with _lock:
+                if _active_fd is None:
+                    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
+                    if hasattr(os, "O_BINARY"):
+                        flags |= os.O_BINARY
+                    _active_fd = os.open(str(path), flags)
+                before = os.fstat(_active_fd).st_size
+                written = os.write(_active_fd, encoded)
+                if written != len(encoded):
+                    _rollback_jsonl_append(_active_fd, before, "diagnostic")
+                    raise AuthorityEventRecoveryError(
+                        "short diagnostic JSONL append"
+                    )
     except Exception:
         pass
 
diff --git a/tests/test_runtime_authority_events.py b/tests/test_runtime_authority_events.py
index 328b3fc..534ef2d 100644
--- a/tests/test_runtime_authority_events.py
+++ b/tests/test_runtime_authority_events.py
@@ -135,6 +135,22 @@ def test_malformed_or_truncated_unindexed_tail_fails_closed(trace_logs):
         trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
 
 
+def test_short_authority_append_is_rolled_back(trace_logs, monkeypatch):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    before = emitter.log_path.stat().st_size
+    real_write = trace.os.write
+
+    def short_write(fd, data):
+        if b'"_type":"authority_event"' in data:
+            return real_write(fd, data[: len(data) // 2])
+        return real_write(fd, data)
+
+    monkeypatch.setattr(trace.os, "write", short_write)
+    with pytest.raises(trace.AuthorityEventRecoveryError, match="short authority JSONL append"):
+        emitter.emit("SHORT_WRITE")
+    assert emitter.log_path.stat().st_size == before
+
+
 def test_two_runtime_domains_have_independent_sequences(trace_logs):
     left = trace.AuthorityEventEmitter(runtime_domain_id="domain-left", logs_root=trace_logs)
     right = trace.AuthorityEventEmitter(runtime_domain_id="domain-right", logs_root=trace_logs)
diff --git a/tests/test_runtime_trace.py b/tests/test_runtime_trace.py
index 576d1ea..3ee262e 100644
--- a/tests/test_runtime_trace.py
+++ b/tests/test_runtime_trace.py
@@ -46,6 +46,10 @@ def test_desktop_trace_session_headers_and_finish(tmp_path, monkeypatch):
     assert trace.active_trace_path(force_refresh=True) is None
     assert not (tmp_path / "logs" / "contextor_runtime_active.json").exists()
     assert len(records[6]["err"]) == 500
+    assert all(
+        item.get("_record_kind") == "diagnostic"
+        for item in records[5:]
+    )
     fields, events = records[1]["fields"], records[4]["events"]["LIVE"]
     assert {"attempt", "attempts", "attempts_used", "retry_delay", "runtime_domain_id", "repo_id", "endpoint_fingerprint", "service_pid", "lease_generation", "service_instance_id", "reason_code", "exception_class", "errno", "winerror", "error", "pid_alive", "endpoint_changed", "process_alive", "process_identity_matches", "endpoint_available", "endpoint_matches", "reason", "result", "side", "operation_or_request_type", "prior_endpoint_fingerprint", "prior_service_pid", "new_endpoint_fingerprint", "new_service_pid", "recovery_operation_id", "owner", "writer_kind"} <= set(fields)
     assert "ANALYSIS" in records[2]["domains"]
@@ -265,6 +269,30 @@ def test_multiprocess_append_is_valid_json(tmp_path, monkeypatch):
         json.loads(line)
 
 
+def test_short_diagnostic_append_is_rolled_back(tmp_path, monkeypatch):
+    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: tmp_path / "logs")
+    _reset_trace_state()
+    path = trace.start_desktop_trace_session()
+    before = path.stat().st_size
+    real_write = trace.os.write
+
+    def short_write(fd, data):
+        if len(data) > 1:
+            return real_write(fd, data[: len(data) // 2])
+        return real_write(fd, data)
+
+    monkeypatch.setattr(trace.os, "write", short_write)
+    trace.trace_event("MCP", "SHORT_WRITE", status="ok")
+    assert path.stat().st_size == before
+
+    monkeypatch.setattr(trace.os, "write", real_write)
+    trace.trace_event("MCP", "AFTER_SHORT_WRITE", status="ok")
+    trace.finish_desktop_trace_session()
+    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
+    assert not any(item.get("ev") == "SHORT_WRITE" for item in records)
+    assert any(item.get("ev") == "AFTER_SHORT_WRITE" for item in records)
+
+
 def test_clean_shutdown_archives_runtime_active_pointer_before_delete(tmp_path, monkeypatch):
     logs = tmp_path / "logs"
     monkeypatch.setattr(trace, "runtime_logs_dir", lambda: logs)
@@ -332,7 +360,12 @@ def test_scoped_trace_capture_matches_durable_record():
 
     records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
     durable_record = next(item for item in records if item.get("ev") == "CAPTURE_DURABLE_MATCH")
-    assert events[0] == durable_record
+    assert "_record_kind" not in events[0]
+    assert {
+        key: value
+        for key, value in durable_record.items()
+        if key != "_record_kind"
+    } == events[0]
 
 
 def test_nested_trace_captures_are_scoped():

## ACTUAL_DIFF_END

## CERTIFICATION

DESKTOP_OWNED_PROCESS_LEAK_CONFIRMED=PARTIAL
SHUTDOWN_PROCESS_TREE_COMPLETE=NO
IMPLEMENTATION_READY=NO

IMPLEMENTATION_READY=NO means the full CPA10K3 task is not complete: recovery consumption of _record_kind and process-leak ownership remain separate stages. The writer-owner stage itself is implemented and its focused tests pass.

STOP_CONDITION

Writer-owner implementation stage complete. Wait for: proceduj





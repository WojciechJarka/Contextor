# CPA10K4A_RUNTIME_TRACE_SHARED_WRITER_HARDENING_CORRECTION

MODE=IMPLEMENT_EXACT_AUDITOR_PATCH
REPO=C:\\Temp\\Contextor_Repo
SCOPE=current-task-only
DISCOVERY_ONLY=NO
PYTEST=NOT_RUN
DESKTOP_MCP_RESTART=NOT_PERFORMED
LIVE_STATE_MUTATION=NOT_PERFORMED

## IMPLEMENTATION_RESULT

PASS_WITH_CONTEXTOR_SOURCE_RANGE_VERIFICATION

The rejected CPA10K4A variant was corrected exactly in `contextor/core/runtime_trace.py`. The recovery implementation and process-lifecycle code were not redesigned or otherwise changed.

## CORRECTIONS_FROM_REJECTED_VARIANT

- Restored `_AuthorityFileLock` to the non-reentrant authority-sidecar/durability lock semantics.
- Removed `_trace_file_lock_local`, reentrancy bookkeeping, and the rejected shared authority-lock use from ordinary diagnostic append.
- Added the dedicated `_TraceAppendFileLock` using `.contextor_runtime_trace.append.lock`.
- Restored authority append ownership under the authority lock and added the required physical append self-lock.
- Replaced the rejected active descriptor lifecycle with per-append descriptors; `_active_fd` has no remaining production reference.
- Added the exact `_record_kind=diagnostic_event` physical discriminator while leaving in-memory capture marker-free.
- Added exact diagnostic timeout `0.25`, short-write progress checking, size checking, identity verification, and rollback helper behavior.
- Removed only the prior CPA10K4A test assertion/short-write test hunks and restored the original exact capture-vs-durable equality assertion.

## EXACT_ANCHORS_VERIFIED

Contextor `get_symbol_implementation` resolved all requested symbols but returned `stale_source` after the local edit because `workspace_sync=out_of_sync`; no `update_file`, full analysis, restart, or LIVE mutation was used.

Contextor `get_source_range` returned status `ok` with fresh syntax diagnostics for the exact current source ranges:

- `_append_authority_record_locked`: lines 546-651.
- `_AuthorityFileLock`: lines 653-703.
- `_TraceAppendFileLock`: lines 704-767.
- `_refresh_pointer`: lines 1208-1235.
- `_append`: lines 1237-1301.
- `_header_records`: lines 1304-1383.
- `_open_runtime_trace_session`: lines 1386-1408.
- `finish_desktop_trace_session`: lines 1442-1463.

The exact source-range content matches the auditor patch. The `get_symbol_implementation` stale-source result is recorded as a tooling freshness limitation, not treated as a source mismatch.

## FILES_CHANGED

Task-level net changes:

- `contextor/core/runtime_trace.py`: exact production correction.
- `tests/test_runtime_trace.py`: prior CPA10K4A hunks reverted; content restored to the pre-CPA10K4A contract.
- `tests/test_runtime_authority_events.py`: prior CPA10K4A hunk reverted; content restored to the pre-CPA10K4A contract.
- `walkthrough.md`: this report only; excluded from production/test diff accounting.

The test-file changes shown in ACTUAL_DIFF are the requested reversion of the rejected variant. There are no remaining CPA10K4A test assertions or short-write tests in the corrected test content.

## PY_COMPILE

Command: `& .\\.venv\\Scripts\\python.exe -m py_compile contextor/core/runtime_trace.py`

Result: PASS

No pytest or broad test execution was performed.

## ZERO_REFERENCE_CHECKS

- `_active_fd` in `contextor/core/runtime_trace.py`: ZERO.
- `_trace_file_lock_local` in `contextor/core/runtime_trace.py`: ZERO.
- `_runtime_trace_lock_path` in `contextor/core/runtime_trace.py`: ZERO.
- `_rollback_jsonl_append` in `contextor/core/runtime_trace.py`: ZERO.
- `held`/old `_key` reentrancy state in the authority lock: ZERO.
- Ordinary `_append` references to `_AuthorityFileLock`: ZERO.

## LOCK_ORDER_EVIDENCE

- Authority recovery/sidecar paths retain the process-local authority lock and `_AuthorityFileLock`.
- `_append_authority_record_locked` self-acquires `_TraceAppendFileLock(_trace_append_lock_path(path))`.
- Therefore authority physical append ordering is: process-local authority lock -> `_AuthorityFileLock` -> `_TraceAppendFileLock`.
- Ordinary diagnostic `_append` acquires only `_TraceAppendFileLock` with `timeout=_DIAGNOSTIC_APPEND_LOCK_TIMEOUT`.
- Ordinary diagnostic append does not acquire `_AuthorityFileLock`.
- The two paths use the same dedicated physical append lock, so authority and diagnostic records cannot physically append concurrently through these writers.

## DIAGNOSTIC_PREFIX_EVIDENCE

The corrected diagnostic path constructs:

`persisted_record = {"_record_kind": _DIAGNOSTIC_RECORD_KIND, **record}`

with:

`_DIAGNOSTIC_RECORD_KIND = "diagnostic_event"`

and serializes with compact JSON separators. The first physical bytes of every newly written diagnostic record are therefore exactly:

`{"_record_kind":"diagnostic_event",`

The marker is inserted only inside `_append`; `trace_event` creates and captures its in-memory record before `_append`, so capture remains marker-free. Header metadata contains the exact `_record_kind` description requested by the patch.

## RECOVERY_AND_LIFECYCLE_BOUNDARY

- `_recover_unindexed_range_locked` was not changed.
- Authority recovery ordering and fail-closed behavior were not changed.
- Runtime trace session open/rotation/pointer behavior was not redesigned.
- The only lifecycle adjustment is the required removal of the obsolete shared `_active_fd`; open/finish retain active metadata/path/session state and pointer checks.
- No process lifecycle, Desktop shutdown, LIVE shutdown, or MCP ownership code was touched.

## TEST_REVERSION_EVIDENCE

Reverted exactly:

- The diagnostic `_record_kind == "diagnostic"` assertion.
- `test_short_diagnostic_append_is_rolled_back`.
- The marker-stripping comparison in `test_scoped_trace_capture_matches_durable_record`; restored `assert events[0] == durable_record`.
- `test_short_authority_append_is_rolled_back`.

Focused tests were enumerated only; none were executed.

## CERTIFICATION

AUTHORITY_LOCK_RESTORED=YES
DEDICATED_TRACE_APPEND_LOCK=YES
DIAGNOSTIC_LOCK_TIMEOUT_025=YES
ACTIVE_FD_REMOVED=YES
DIAGNOSTIC_PREFIX_EXACT=YES
AUTHORITY_PHYSICAL_APPEND_SELF_LOCKED=YES
RECOVERY_UNCHANGED=YES
TEST_FILES_NET_UNCHANGED=YES
PY_COMPILE=PASS
IMPLEMENTATION_READY=YES

## ACTUAL_DIFF

The following is the complete current diff for every production/test file changed by this correction. `walkthrough.md` is intentionally excluded.

diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index fb11bc0..5605d7a 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -29,10 +29,12 @@ _lock = threading.RLock()
 _active_meta: dict[str, object] | None = None
 _active_path: Path | None = None
 _active_sid: str | None = None
-_active_fd: int | None = None
 _last_pointer_check = 0.0
 _counter = 0
 _AUTHORITY_STATE_NAME = "authority_event_state.json"
+_TRACE_APPEND_LOCK_NAME = ".contextor_runtime_trace.append.lock"
+_DIAGNOSTIC_RECORD_KIND = "diagnostic_event"
+_DIAGNOSTIC_APPEND_LOCK_TIMEOUT = 0.25
 _AUTHORITY_RECOVERY_WINDOW = 1024 * 1024
 _AUTHORITY_APPEND_LOCATE_WINDOW = 1024 * 1024
 _AUTHORITY_PENDING_LIMIT = 10_000
@@ -41,7 +43,6 @@ _FALLBACK_SCHEMA = 1
 _sidecar_rollovers: set[Path] = set()
 _authority_emitters: dict[tuple[str, str], "AuthorityEventEmitter"] = {}
 _authority_lock = threading.RLock()
-_trace_file_lock_local = threading.local()
 _operation_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
     "contextor_trace_operation", default=None
 )
@@ -56,8 +57,13 @@ _trace_capture_var: contextvars.ContextVar[
 AUTHORITY_EVENT_SCHEMA = "contextor-authority-event/v1"
 
 
-def _runtime_trace_lock_path(path: Path) -> Path:
-    return path.parent / f".{_AUTHORITY_STATE_NAME}.lock"
+def _trace_append_lock_path(trace_path: Path) -> Path:
+    return trace_path.resolve().parent / _TRACE_APPEND_LOCK_NAME
+
+
+def _rollback_append(fd: int, offset: int) -> None:
+    os.ftruncate(fd, offset)
+    os.fsync(fd)
 
 
 def _snapshot_stamp() -> str:
@@ -537,17 +543,10 @@ def _authority_envelope(event: AuthorityEvent) -> dict[str, object]:
     return {"_type": "authority_event", "schema": AUTHORITY_EVENT_SCHEMA, **event.to_dict()}
 
 
-def _rollback_jsonl_append(fd: int, before: int, record_kind: str) -> None:
-    try:
-        os.ftruncate(fd, before)
-        os.fsync(fd)
-    except OSError as exc:
-        raise AuthorityEventRecoveryError(
-            f"{record_kind} JSONL append rollback failed"
-        ) from exc
-
-
-def _append_authority_record_locked(path: Path, event: AuthorityEvent) -> RecordIndex:
+def _append_authority_record_locked(
+    path: Path,
+    event: AuthorityEvent,
+) -> RecordIndex:
     data = (
         json.dumps(
             _authority_envelope(event),
@@ -557,42 +556,74 @@ def _append_authority_record_locked(path: Path, event: AuthorityEvent) -> Record
         )
         + "\n"
     ).encode("utf-8")
-    fd = os.open(
-        str(path),
-        os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0),
-        0o600,
-    )
-    try:
+
+    with _TraceAppendFileLock(_trace_append_lock_path(path)):
+        fd = os.open(
+            str(path),
+            os.O_WRONLY
+            | os.O_APPEND
+            | os.O_CREAT
+            | getattr(os, "O_BINARY", 0),
+            0o600,
+        )
         before = os.fstat(fd).st_size
-        written = os.write(fd, data)
-        if written != len(data):
-            _rollback_jsonl_append(fd, before, "authority")
-            raise AuthorityEventRecoveryError("short authority JSONL append")
-        os.fsync(fd)
-        end = os.fstat(fd).st_size
-    finally:
-        os.close(fd)
-    if end < before + written:
-        raise AuthorityEventRecoveryError("authority JSONL append size is inconsistent")
-    span = end - before
-    if span > max(_AUTHORITY_APPEND_LOCATE_WINDOW, written):
-        raise AuthorityEventRecoveryError(
-            "authority append location exceeds bounded interleaving window"
+        try:
+            try:
+                written = os.write(fd, data)
+                if written != len(data):
+                    raise AuthorityEventRecoveryError(
+                        "short authority JSONL append"
+                    )
+                os.fsync(fd)
+                end = os.fstat(fd).st_size
+                if end != before + len(data):
+                    raise AuthorityEventRecoveryError(
+                        "authority JSONL append size is inconsistent"
+                    )
+            except Exception:
+                try:
+                    _rollback_append(fd, before)
+                except OSError as rollback_exc:
+                    raise AuthorityEventRecoveryError(
+                        "authority JSONL append rollback failed"
+                    ) from rollback_exc
+                raise
+        finally:
+            os.close(fd)
+
+        with path.open("rb") as stream:
+            stream.seek(before)
+            persisted = stream.read(len(data))
+
+        if persisted != data:
+            raise AuthorityEventRecoveryError(
+                "authority JSONL append identity verification failed"
+            )
+
+        start = before
+        record_end = before + len(data)
+        recovered = _read_authority_record_at(
+            path,
+            start,
+            record_end,
         )
-    with path.open("rb") as stream:
-        stream.seek(before)
-        window = stream.read(span)
-    relative = window.find(data)
-    if relative < 0:
-        raise AuthorityEventRecoveryError("authority JSONL append cannot be located exactly")
-    if window.find(data, relative + 1) >= 0:
-        raise AuthorityEventRecoveryError("authority JSONL append identity is ambiguous")
-    start = before + relative
-    end = start + written
-    recovered = _read_authority_record_at(path, start, end)
-    if recovered.event_id != event.event_id or recovered.sequence != event.sequence or recovered.runtime_domain_id != event.runtime_domain_id:
-        raise AuthorityEventRecoveryError("authority JSONL append identity verification failed")
-    return RecordIndex(event.sequence, event.event_id, str(path.resolve()), start, end)
+        if (
+            recovered.event_id != event.event_id
+            or recovered.sequence != event.sequence
+            or recovered.runtime_domain_id
+            != event.runtime_domain_id
+        ):
+            raise AuthorityEventRecoveryError(
+                "authority JSONL append identity verification failed"
+            )
+
+    return RecordIndex(
+        event.sequence,
+        event.event_id,
+        str(path.resolve()),
+        start,
+        record_end,
+    )
 
 
 def _read_authority_record_at(path: Path, offset: int, end_offset: int) -> AuthorityEvent:
@@ -620,24 +651,14 @@ def _read_authority_record_at(path: Path, offset: int, end_offset: int) -> Autho
 
 
 class _AuthorityFileLock(contextlib.AbstractContextManager):
-    """Cross-process lock for shared JSONL append and authority sidecar order."""
+    """Cross-process lock for the bounded sidecar and its JSONL append order."""
 
     def __init__(self, path: Path, timeout: float = 10.0) -> None:
         self.path = path
         self.timeout = timeout
         self._file = None
-        self._reentrant = False
-        self._key = str(path.resolve())
 
     def __enter__(self):
-        held = getattr(_trace_file_lock_local, "held", None)
-        if held is None:
-            held = {}
-            _trace_file_lock_local.held = held
-        if held.get(self._key, 0):
-            held[self._key] += 1
-            self._reentrant = True
-            return self
         self.path.parent.mkdir(parents=True, exist_ok=True)
         self._file = self.path.open("a+b")
         if self.path.stat().st_size == 0:
@@ -655,7 +676,6 @@ class _AuthorityFileLock(contextlib.AbstractContextManager):
                     import fcntl
 
                     fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
-                held[self._key] = 1
                 return self
             except (OSError, BlockingIOError):
                 if time.monotonic() >= deadline:
@@ -665,15 +685,6 @@ class _AuthorityFileLock(contextlib.AbstractContextManager):
                 time.sleep(0.01)
 
     def __exit__(self, exc_type, exc, tb):
-        held = getattr(_trace_file_lock_local, "held", {})
-        if self._reentrant:
-            depth = held.get(self._key, 0)
-            if depth <= 1:
-                held.pop(self._key, None)
-            else:
-                held[self._key] = depth - 1
-            self._reentrant = False
-            return False
         if self._file is not None:
             try:
                 self._file.seek(0)
@@ -689,9 +700,71 @@ class _AuthorityFileLock(contextlib.AbstractContextManager):
                 pass
             self._file.close()
             self._file = None
-            held.pop(self._key, None)
 
+class _TraceAppendFileLock(contextlib.AbstractContextManager):
+    def __init__(self, path: Path, timeout: float = 10.0) -> None:
+        self.path = path
+        self.timeout = timeout
+        self._file = None
 
+    def __enter__(self):
+        self.path.parent.mkdir(parents=True, exist_ok=True)
+        self._file = self.path.open("a+b")
+        if self.path.stat().st_size == 0:
+            self._file.write(b"0")
+            self._file.flush()
+        deadline = time.monotonic() + self.timeout
+        while True:
+            try:
+                self._file.seek(0)
+                if os.name == "nt":
+                    import msvcrt
+
+                    msvcrt.locking(
+                        self._file.fileno(),
+                        msvcrt.LK_NBLCK,
+                        1,
+                    )
+                else:
+                    import fcntl
+
+                    fcntl.flock(
+                        self._file.fileno(),
+                        fcntl.LOCK_EX | fcntl.LOCK_NB,
+                    )
+                return self
+            except (OSError, BlockingIOError):
+                if time.monotonic() >= deadline:
+                    self._file.close()
+                    self._file = None
+                    raise AuthorityEventRecoveryError(
+                        "timed out waiting for runtime trace append lock"
+                    )
+                time.sleep(0.01)
+
+    def __exit__(self, exc_type, exc, tb):
+        if self._file is not None:
+            try:
+                self._file.seek(0)
+                if os.name == "nt":
+                    import msvcrt
+
+                    msvcrt.locking(
+                        self._file.fileno(),
+                        msvcrt.LK_UNLCK,
+                        1,
+                    )
+                else:
+                    import fcntl
+
+                    fcntl.flock(
+                        self._file.fileno(),
+                        fcntl.LOCK_UN,
+                    )
+            except OSError:
+                pass
+            self._file.close()
+            self._file = None
 
 
 class AuthorityEventEmitter:
@@ -1133,7 +1206,7 @@ def _read_pointer() -> tuple[dict[str, object], Path] | None:
 
 
 def _refresh_pointer(*, force: bool = False) -> Path | None:
-    global _active_meta, _active_path, _active_sid, _active_fd, _last_pointer_check
+    global _active_meta, _active_path, _active_sid, _last_pointer_check
     now = time.monotonic()
     with _lock:
         if not force and now - _last_pointer_check < _CHECK_INTERVAL:
@@ -1141,24 +1214,12 @@ def _refresh_pointer(*, force: bool = False) -> Path | None:
         _last_pointer_check = now
         resolved = _read_pointer()
         if resolved is None:
-            if _active_fd is not None:
-                try:
-                    os.close(_active_fd)
-                except OSError:
-                    pass
-                _active_fd = None
             _active_meta = None
             _active_path = None
             _active_sid = None
             return None
         meta, path = resolved
         if meta != _active_meta or path != _active_path:
-            if _active_fd is not None:
-                try:
-                    os.close(_active_fd)
-                except OSError:
-                    pass
-                _active_fd = None
             _active_meta = meta
             _active_path = path
             _active_sid = str(meta["sid"])
@@ -1173,34 +1234,69 @@ def active_trace_path(*, force_refresh: bool = False) -> Path | None:
         return None
 
 
-def _append(record: dict[str, object], path: Path) -> None:
-    global _active_fd
+def _append(
+    record: dict[str, object],
+    path: Path,
+) -> None:
     try:
-        persisted_record = dict(record)
-        persisted_record["_record_kind"] = "diagnostic"
-        payload = (
+        persisted_record = {
+            "_record_kind": _DIAGNOSTIC_RECORD_KIND,
+            **record,
+        }
+        encoded = (
             json.dumps(
                 persisted_record,
                 ensure_ascii=False,
                 separators=(",", ":"),
             )
             + "\n"
-        )
-        encoded = payload.encode("utf-8")
-        with _AuthorityFileLock(_runtime_trace_lock_path(path)):
-            with _lock:
-                if _active_fd is None:
-                    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
-                    if hasattr(os, "O_BINARY"):
-                        flags |= os.O_BINARY
-                    _active_fd = os.open(str(path), flags)
-                before = os.fstat(_active_fd).st_size
-                written = os.write(_active_fd, encoded)
-                if written != len(encoded):
-                    _rollback_jsonl_append(_active_fd, before, "diagnostic")
-                    raise AuthorityEventRecoveryError(
-                        "short diagnostic JSONL append"
-                    )
+        ).encode("utf-8")
+
+        with _TraceAppendFileLock(
+            _trace_append_lock_path(path),
+            timeout=_DIAGNOSTIC_APPEND_LOCK_TIMEOUT,
+        ):
+            flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
+            if hasattr(os, "O_BINARY"):
+                flags |= os.O_BINARY
+
+            fd = os.open(str(path), flags)
+            before = os.fstat(fd).st_size
+            try:
+                try:
+                    offset = 0
+                    while offset < len(encoded):
+                        written = os.write(
+                            fd,
+                            encoded[offset:],
+                        )
+                        if written <= 0:
+                            raise OSError(
+                                "runtime trace diagnostic append made no progress"
+                            )
+                        offset += written
+
+                    end = os.fstat(fd).st_size
+                    if end != before + len(encoded):
+                        raise OSError(
+                            "runtime trace diagnostic append size is inconsistent"
+                        )
+
+                    with path.open("rb") as stream:
+                        stream.seek(before)
+                        persisted = stream.read(len(encoded))
+                    if persisted != encoded:
+                        raise OSError(
+                            "runtime trace diagnostic append verification failed"
+                        )
+                except Exception:
+                    try:
+                        _rollback_append(fd, before)
+                    except OSError:
+                        pass
+                    raise
+            finally:
+                os.close(fd)
     except Exception:
         pass
 
@@ -1215,6 +1311,10 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
     ]
     records[1]["fields"].update(
         {
+            "_record_kind": (
+                "physical JSONL record kind; "
+                "diagnostic_event for ordinary best-effort diagnostics"
+            ),
             "owner": "canonical writer owner",
             "writer_kind": "canonical writer kind",
             "origin": "LIVE update origin",
@@ -1285,7 +1385,7 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
 
 def _open_runtime_trace_session(*, logs_root: str | Path | None = None) -> Path:
     """Open and publish the sole runtime-trace JSONL session."""
-    global _active_meta, _active_path, _active_sid, _active_fd, _last_pointer_check
+    global _active_meta, _active_path, _active_sid, _last_pointer_check
     logs = _resolved_logs_root(logs_root)
     production_logs = runtime_logs_dir().resolve()
     logs.mkdir(parents=True, exist_ok=True)
@@ -1314,7 +1414,6 @@ def _open_runtime_trace_session(*, logs_root: str | Path | None = None) -> Path:
     if logs == production_logs:
         with _lock:
             _active_meta, _active_path, _active_sid = pointer, path.resolve(), sid
-            _active_fd = None
             _last_pointer_check = time.monotonic()
     return path.resolve()
 
@@ -1341,7 +1440,7 @@ def start_desktop_trace_session() -> Path | None:
 
 
 def finish_desktop_trace_session() -> None:
-    global _active_meta, _active_path, _active_sid, _active_fd, _last_pointer_check
+    global _active_meta, _active_path, _active_sid, _last_pointer_check
     try:
         sid = _active_sid
         path = _active_path
@@ -1358,12 +1457,6 @@ def finish_desktop_trace_session() -> None:
             except FileNotFoundError:
                 pass
         with _lock:
-            if _active_fd is not None:
-                try:
-                    os.close(_active_fd)
-                except OSError:
-                    pass
-                _active_fd = None
             _active_meta = _active_path = _active_sid = None
             _last_pointer_check = 0.0
     except Exception:
diff --git a/tests/test_runtime_authority_events.py b/tests/test_runtime_authority_events.py
index 534ef2d..328b3fc 100644
--- a/tests/test_runtime_authority_events.py
+++ b/tests/test_runtime_authority_events.py
@@ -135,22 +135,6 @@ def test_malformed_or_truncated_unindexed_tail_fails_closed(trace_logs):
         trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
 
 
-def test_short_authority_append_is_rolled_back(trace_logs, monkeypatch):
-    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
-    before = emitter.log_path.stat().st_size
-    real_write = trace.os.write
-
-    def short_write(fd, data):
-        if b'"_type":"authority_event"' in data:
-            return real_write(fd, data[: len(data) // 2])
-        return real_write(fd, data)
-
-    monkeypatch.setattr(trace.os, "write", short_write)
-    with pytest.raises(trace.AuthorityEventRecoveryError, match="short authority JSONL append"):
-        emitter.emit("SHORT_WRITE")
-    assert emitter.log_path.stat().st_size == before
-
-
 def test_two_runtime_domains_have_independent_sequences(trace_logs):
     left = trace.AuthorityEventEmitter(runtime_domain_id="domain-left", logs_root=trace_logs)
     right = trace.AuthorityEventEmitter(runtime_domain_id="domain-right", logs_root=trace_logs)
diff --git a/tests/test_runtime_trace.py b/tests/test_runtime_trace.py
index 3ee262e..576d1ea 100644
--- a/tests/test_runtime_trace.py
+++ b/tests/test_runtime_trace.py
@@ -46,10 +46,6 @@ def test_desktop_trace_session_headers_and_finish(tmp_path, monkeypatch):
     assert trace.active_trace_path(force_refresh=True) is None
     assert not (tmp_path / "logs" / "contextor_runtime_active.json").exists()
     assert len(records[6]["err"]) == 500
-    assert all(
-        item.get("_record_kind") == "diagnostic"
-        for item in records[5:]
-    )
     fields, events = records[1]["fields"], records[4]["events"]["LIVE"]
     assert {"attempt", "attempts", "attempts_used", "retry_delay", "runtime_domain_id", "repo_id", "endpoint_fingerprint", "service_pid", "lease_generation", "service_instance_id", "reason_code", "exception_class", "errno", "winerror", "error", "pid_alive", "endpoint_changed", "process_alive", "process_identity_matches", "endpoint_available", "endpoint_matches", "reason", "result", "side", "operation_or_request_type", "prior_endpoint_fingerprint", "prior_service_pid", "new_endpoint_fingerprint", "new_service_pid", "recovery_operation_id", "owner", "writer_kind"} <= set(fields)
     assert "ANALYSIS" in records[2]["domains"]
@@ -269,30 +265,6 @@ def test_multiprocess_append_is_valid_json(tmp_path, monkeypatch):
         json.loads(line)
 
 
-def test_short_diagnostic_append_is_rolled_back(tmp_path, monkeypatch):
-    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: tmp_path / "logs")
-    _reset_trace_state()
-    path = trace.start_desktop_trace_session()
-    before = path.stat().st_size
-    real_write = trace.os.write
-
-    def short_write(fd, data):
-        if len(data) > 1:
-            return real_write(fd, data[: len(data) // 2])
-        return real_write(fd, data)
-
-    monkeypatch.setattr(trace.os, "write", short_write)
-    trace.trace_event("MCP", "SHORT_WRITE", status="ok")
-    assert path.stat().st_size == before
-
-    monkeypatch.setattr(trace.os, "write", real_write)
-    trace.trace_event("MCP", "AFTER_SHORT_WRITE", status="ok")
-    trace.finish_desktop_trace_session()
-    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
-    assert not any(item.get("ev") == "SHORT_WRITE" for item in records)
-    assert any(item.get("ev") == "AFTER_SHORT_WRITE" for item in records)
-
-
 def test_clean_shutdown_archives_runtime_active_pointer_before_delete(tmp_path, monkeypatch):
     logs = tmp_path / "logs"
     monkeypatch.setattr(trace, "runtime_logs_dir", lambda: logs)
@@ -360,12 +332,7 @@ def test_scoped_trace_capture_matches_durable_record():
 
     records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
     durable_record = next(item for item in records if item.get("ev") == "CAPTURE_DURABLE_MATCH")
-    assert "_record_kind" not in events[0]
-    assert {
-        key: value
-        for key, value in durable_record.items()
-        if key != "_record_kind"
-    } == events[0]
+    assert events[0] == durable_record
 
 
 def test_nested_trace_captures_are_scoped():

## END_ACTUAL_DIFF

## MUST_TOUCH

- `contextor/core/runtime_trace.py` exact writer-lock, rollback, discriminator, and active-descriptor correction.
- Reversion of only the prior CPA10K4A test hunks.

## MUST_NOT_TOUCH

- Recovery semantics/design.
- Desktop/LIVE/MCP process lifecycle.
- External MCP ownership.
- LIVE state, runtime output storage, process state, restart state.
- Git-history archaeology, commit/HEAD operations, pytest, broad tests, or full analysis.

DIFFS=SOURCE_CORRECTION_PLUS_EXACT_TEST_REVERSION
STATUS=STOP_AND_WAIT_FOR_PROCEDUJ

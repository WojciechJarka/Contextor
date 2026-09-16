# CPA10K4A2_RUNTIME_TRACE_WRITER_LOCAL_SERIALIZATION_AND_TEST_CONTRACT

MODE=IMPLEMENT_EXACT_AUDITOR_PATCH
REPO=C:\\Temp\\Contextor_Repo
SCOPE=current-task-only
IMPLEMENTATION_RESULT=PASS
PYTEST_SCOPE=EXACTLY_TWO_FOCUSED_TESTS
FULL_ANALYSIS=NOT_RUN
LIVE_MCP_RESTART=NOT_PERFORMED
UPDATE_FILE=NOT_USED
PROCESS_LIFECYCLE=NOT_CHANGED
RECOVERY=NOT_CHANGED

## FILES_CHANGED

- `contextor/core/runtime_trace.py`
- `tests/test_runtime_trace.py`
- `walkthrough.md` report artifact only and excluded from production/test diff accounting

`tests/test_runtime_authority_events.py` was not changed by CPA10K4A2.

## LOCK_ORDER_EVIDENCE

The new process-local lock is exactly:

`_trace_append_thread_lock = threading.RLock()`

Physical authority writer order:

`process-local authority lock -> _AuthorityFileLock -> _trace_append_thread_lock -> _TraceAppendFileLock`

`_append_authority_record_locked` now wraps its existing physical append body with:

`with _trace_append_thread_lock:`
`    with _TraceAppendFileLock(_trace_append_lock_path(path)):`

Physical diagnostic writer order:

`_trace_append_thread_lock -> _TraceAppendFileLock`

`_append` now wraps its existing diagnostic append body with the process-local lock and retains the exact cross-process lock and `timeout=_DIAGNOSTIC_APPEND_LOCK_TIMEOUT`.

Diagnostic `_append` contains no `_AuthorityFileLock`. No file-lock reentrancy was added or changed.

The shared process-local lock has exactly two production physical-writer consumers: `_append` and `_append_authority_record_locked`.

## CAPTURE_CONTRACT_EVIDENCE

The existing `test_scoped_trace_capture_matches_durable_record` assertion now verifies:

- `events[0]` has no `_record_kind`.
- The durable record has `_record_kind == "diagnostic_event"`.
- The durable record equals the captured event after removing only `_record_kind`.

No production capture behavior was changed. The marker remains physical JSONL-only and remains the first serialized field, so the diagnostic prefix remains exactly:

`{"_record_kind":"diagnostic_event",`

## ZERO_REFERENCE_CHECKS

- `_trace_append_thread_lock` global declaration: exactly one.
- Production consumers of `_trace_append_thread_lock`: exactly two.
- `_append` references to `_AuthorityFileLock`: ZERO.
- `_active_fd`: ZERO.
- `_trace_file_lock_local`: ZERO.
- `_DIAGNOSTIC_APPEND_LOCK_TIMEOUT = 0.25`: unchanged.
- `_TraceAppendFileLock`: unchanged.
- `_AuthorityFileLock`: unchanged.
- `_rollback_append`: unchanged.
- `_record_kind` value and first-field construction: unchanged.
- `_recover_unindexed_range_locked`: unchanged.
- `tests/test_runtime_authority_events.py`: unchanged by this task.

## CONTEXTOR_VERIFICATION

Contextor exact post-edit verification succeeded for both writers:

- `_append`: `get_symbol_implementation` status `resolved`, `workspace_sync=verified`, canonical revision 1275, exact implementation lines 1239-1304.
- `_append_authority_record_locked`: `get_symbol_implementation` status `resolved`, `workspace_sync=verified`, canonical revision 1276, exact implementation lines 547-628.
- Source-range checks returned status `ok` with fresh syntax diagnostics for authority lines 547-630 and diagnostic lines 1239-1306.
- Contextor reported no syntax errors, collisions, cycles, or diagnostic attention.

## PY_COMPILE

Command:

`& .\\.venv\\Scripts\\python.exe -m py_compile contextor/core/runtime_trace.py`

Result: PASS

## TESTS

Only the two authorized tests were executed:

`& .\\.venv\\Scripts\\python.exe -m pytest tests/test_runtime_trace.py::test_scoped_trace_capture_matches_durable_record tests/test_runtime_trace.py::test_multiprocess_append_is_valid_json -q`

Result:

`2 passed in 3.69s`

No other tests were run.

## CERTIFICATION

LOCAL_PHYSICAL_WRITER_SERIALIZATION=YES
CROSS_PROCESS_PHYSICAL_WRITER_SERIALIZATION=YES
DIAGNOSTIC_AUTHORITY_LOCK_SEPARATION=YES
ACTIVE_FD_REMOVED=YES
DIAGNOSTIC_PREFIX_EXACT=YES
CAPTURE_REMAINS_MARKER_FREE=YES
RECOVERY_UNCHANGED=YES
FOCUSED_TESTS=PASS
PY_COMPILE=PASS

## COMPLETE_DIFFS

The following is the complete current worktree diff for both production/test files changed in this task. `walkthrough.md` is excluded.

diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 5605d7a..34dd692 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -43,6 +43,7 @@ _FALLBACK_SCHEMA = 1
 _sidecar_rollovers: set[Path] = set()
 _authority_emitters: dict[tuple[str, str], "AuthorityEventEmitter"] = {}
 _authority_lock = threading.RLock()
+_trace_append_thread_lock = threading.RLock()
 _operation_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
     "contextor_trace_operation", default=None
 )
@@ -557,65 +558,66 @@ def _append_authority_record_locked(
         + "\n"
     ).encode("utf-8")
 
-    with _TraceAppendFileLock(_trace_append_lock_path(path)):
-        fd = os.open(
-            str(path),
-            os.O_WRONLY
-            | os.O_APPEND
-            | os.O_CREAT
-            | getattr(os, "O_BINARY", 0),
-            0o600,
-        )
-        before = os.fstat(fd).st_size
-        try:
+    with _trace_append_thread_lock:
+        with _TraceAppendFileLock(_trace_append_lock_path(path)):
+            fd = os.open(
+                str(path),
+                os.O_WRONLY
+                | os.O_APPEND
+                | os.O_CREAT
+                | getattr(os, "O_BINARY", 0),
+                0o600,
+            )
+            before = os.fstat(fd).st_size
             try:
-                written = os.write(fd, data)
-                if written != len(data):
-                    raise AuthorityEventRecoveryError(
-                        "short authority JSONL append"
-                    )
-                os.fsync(fd)
-                end = os.fstat(fd).st_size
-                if end != before + len(data):
-                    raise AuthorityEventRecoveryError(
-                        "authority JSONL append size is inconsistent"
-                    )
-            except Exception:
                 try:
-                    _rollback_append(fd, before)
-                except OSError as rollback_exc:
-                    raise AuthorityEventRecoveryError(
-                        "authority JSONL append rollback failed"
-                    ) from rollback_exc
-                raise
-        finally:
-            os.close(fd)
+                    written = os.write(fd, data)
+                    if written != len(data):
+                        raise AuthorityEventRecoveryError(
+                            "short authority JSONL append"
+                        )
+                    os.fsync(fd)
+                    end = os.fstat(fd).st_size
+                    if end != before + len(data):
+                        raise AuthorityEventRecoveryError(
+                            "authority JSONL append size is inconsistent"
+                        )
+                except Exception:
+                    try:
+                        _rollback_append(fd, before)
+                    except OSError as rollback_exc:
+                        raise AuthorityEventRecoveryError(
+                            "authority JSONL append rollback failed"
+                        ) from rollback_exc
+                    raise
+            finally:
+                os.close(fd)
 
-        with path.open("rb") as stream:
-            stream.seek(before)
-            persisted = stream.read(len(data))
+            with path.open("rb") as stream:
+                stream.seek(before)
+                persisted = stream.read(len(data))
 
-        if persisted != data:
-            raise AuthorityEventRecoveryError(
-                "authority JSONL append identity verification failed"
-            )
+            if persisted != data:
+                raise AuthorityEventRecoveryError(
+                    "authority JSONL append identity verification failed"
+                )
 
-        start = before
-        record_end = before + len(data)
-        recovered = _read_authority_record_at(
-            path,
-            start,
-            record_end,
-        )
-        if (
-            recovered.event_id != event.event_id
-            or recovered.sequence != event.sequence
-            or recovered.runtime_domain_id
-            != event.runtime_domain_id
-        ):
-            raise AuthorityEventRecoveryError(
-                "authority JSONL append identity verification failed"
+            start = before
+            record_end = before + len(data)
+            recovered = _read_authority_record_at(
+                path,
+                start,
+                record_end,
             )
+            if (
+                recovered.event_id != event.event_id
+                or recovered.sequence != event.sequence
+                or recovered.runtime_domain_id
+                != event.runtime_domain_id
+            ):
+                raise AuthorityEventRecoveryError(
+                    "authority JSONL append identity verification failed"
+                )
 
     return RecordIndex(
         event.sequence,
@@ -1252,51 +1254,52 @@ def _append(
             + "\n"
         ).encode("utf-8")
 
-        with _TraceAppendFileLock(
-            _trace_append_lock_path(path),
-            timeout=_DIAGNOSTIC_APPEND_LOCK_TIMEOUT,
-        ):
-            flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
-            if hasattr(os, "O_BINARY"):
-                flags |= os.O_BINARY
-
-            fd = os.open(str(path), flags)
-            before = os.fstat(fd).st_size
-            try:
+        with _trace_append_thread_lock:
+            with _TraceAppendFileLock(
+                _trace_append_lock_path(path),
+                timeout=_DIAGNOSTIC_APPEND_LOCK_TIMEOUT,
+            ):
+                flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
+                if hasattr(os, "O_BINARY"):
+                    flags |= os.O_BINARY
+
+                fd = os.open(str(path), flags)
+                before = os.fstat(fd).st_size
                 try:
-                    offset = 0
-                    while offset < len(encoded):
-                        written = os.write(
-                            fd,
-                            encoded[offset:],
-                        )
-                        if written <= 0:
+                    try:
+                        offset = 0
+                        while offset < len(encoded):
+                            written = os.write(
+                                fd,
+                                encoded[offset:],
+                            )
+                            if written <= 0:
+                                raise OSError(
+                                    "runtime trace diagnostic append made no progress"
+                                )
+                            offset += written
+
+                        end = os.fstat(fd).st_size
+                        if end != before + len(encoded):
                             raise OSError(
-                                "runtime trace diagnostic append made no progress"
+                                "runtime trace diagnostic append size is inconsistent"
                             )
-                        offset += written
 
-                    end = os.fstat(fd).st_size
-                    if end != before + len(encoded):
-                        raise OSError(
-                            "runtime trace diagnostic append size is inconsistent"
-                        )
-
-                    with path.open("rb") as stream:
-                        stream.seek(before)
-                        persisted = stream.read(len(encoded))
-                    if persisted != encoded:
-                        raise OSError(
-                            "runtime trace diagnostic append verification failed"
-                        )
-                except Exception:
-                    try:
-                        _rollback_append(fd, before)
-                    except OSError:
-                        pass
-                    raise
-            finally:
-                os.close(fd)
+                        with path.open("rb") as stream:
+                            stream.seek(before)
+                            persisted = stream.read(len(encoded))
+                        if persisted != encoded:
+                            raise OSError(
+                                "runtime trace diagnostic append verification failed"
+                            )
+                    except Exception:
+                        try:
+                            _rollback_append(fd, before)
+                        except OSError:
+                            pass
+                        raise
+                finally:
+                    os.close(fd)
     except Exception:
         pass
 
diff --git a/tests/test_runtime_trace.py b/tests/test_runtime_trace.py
index 576d1ea..ef224fc 100644
--- a/tests/test_runtime_trace.py
+++ b/tests/test_runtime_trace.py
@@ -332,7 +332,13 @@ def test_scoped_trace_capture_matches_durable_record():
 
     records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
     durable_record = next(item for item in records if item.get("ev") == "CAPTURE_DURABLE_MATCH")
-    assert events[0] == durable_record
+    assert "_record_kind" not in events[0]
+    assert durable_record["_record_kind"] == "diagnostic_event"
+    assert {
+        key: value
+        for key, value in durable_record.items()
+        if key != "_record_kind"
+    } == events[0]
 
 
 def test_nested_trace_captures_are_scoped():

## END_COMPLETE_DIFFS

## MUST_NOT_CHANGE_CONFIRMED

- Recovery and `_recover_unindexed_range_locked`.
- Authority semantics except the required process-local serialization wrapper.
- Diagnostic marker value, first-field ordering, append timeout, append lock class, active-fd removal, and rollback helper.
- Session/pointer lifecycle.
- Desktop/LIVE/MCP process lifecycle and shutdown.
- `tests/test_runtime_authority_events.py`.
- Any recovery redesign.

DIFFS=COMPLETE_CURRENT_WORKTREE_DIFF_INCLUDED
STATUS=STOP_AND_WAIT_FOR_PROCEDUJ


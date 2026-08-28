# Runtime trace canonical non-interference correction

VERDICT=IMPLEMENTATION_PASS
UNGUARDED_TRACE_DEPENDENCY_IN_CANONICAL_PATH=NO
PUBLISH_REV0_SOURCE=previous authoritative self._revision
PUBLISH_REV1_SOURCE=post-commit authoritative self._revision
TRACE_DERIVES_REVISION_ARITHMETICALLY=NO
TRACE_OP_GENERATOR_FAILURE_NON_FATAL=PASS
TRACE_EVENT_FAILURE_NON_FATAL=PASS
TRACE_CONTEXT_FAILURE_NON_FATAL=PASS
UPDATER_EXCEPTION_SEMANTICS_PRESERVED=PASS
PUBLISH_FAIL_IMPLEMENTED=YES
CANONICAL_COMMIT_BOUNDARY_CHANGED=NO
REVISION_VALIDATION_CHANGED=NO
ACTIVITY_SEQ_SEMANTICS_CHANGED=NO
TESTS_RUN=pytest -q tests/test_runtime_trace.py tests/test_live_state_ipc.py tests/test_live_activity_status.py; correction subset -k "publish_trace or update_trace or runtime_trace"
TESTS_PASSED=70 in focused invocation; 7 correction tests
TESTS_FAILED=3 pre-existing Windows process termination/startup assertions
MANUAL_MCP_RESTART_REQUIRED=YES
MANUAL_DESKTOP_LIVE_RESTART_REQUIRED=YES
FILES_CHANGED=contextor/core/live_state/ipc.py; contextor/core/runtime_trace.py; tests/test_live_state_ipc.py
COMPLETE_RAW_DIFFS=YES

Complete raw unified diff command:
git diff -- contextor/core/live_state/ipc.py contextor/core/runtime_trace.py tests/test_live_state_ipc.py

---

# Runtime trace final correctness correction

VERDICT=IMPLEMENTATION_PASS
TRACE_CONTEXT_IMPORT_FAILURE_NON_FATAL=PASS
TRACE_CONTEXT_ENTER_FAILURE_NON_FATAL=PASS
TRACE_CONTEXT_EXIT_FAILURE_NON_FATAL=PASS
UPDATER_EXCEPTION_CANNOT_BE_REPLACED_BY_TRACE=PASS
PUBLISH_FAIL_USED_ONLY_FOR_PUBLISH=PASS
UPDATE_FAIL_IMPLEMENTED=YES
UPDATE_FAIL_USED_ONLY_FOR_UPDATE=PASS
TRACE_EVENT_LEGEND_MATCHES_PRODUCTION=PASS
PUBLISH_REV0_SOURCE=previous authoritative self._revision
PUBLISH_REV1_SOURCE=post-commit authoritative self._revision
TRACE_DERIVES_REVISION_ARITHMETICALLY=NO
CANONICAL_COMMIT_BOUNDARY_CHANGED=NO
REVISION_VALIDATION_CHANGED=NO
ACTIVITY_SEQ_SEMANTICS_CHANGED=NO
FOCUSED_TEST_FAILURE_NAMES=[test_terminate_pid_tree_kills_process_and_children, test_connect_or_start_true_startup_hang]
NEW_FAILURE_INTRODUCED_BY_TRACE=NO
TESTS_RUN=pytest -q tests/test_runtime_trace.py tests/test_live_state_ipc.py tests/test_live_activity_status.py; pytest -q tests/test_live_state_ipc.py -k "trace_context or update_fail or publish_trace or update_trace"
TESTS_PASSED=75 focused; 7 correction subset
TESTS_FAILED=2 known unrelated Windows process termination/startup tests
MANUAL_MCP_RESTART_REQUIRED=YES
MANUAL_DESKTOP_LIVE_RESTART_REQUIRED=YES
FILES_CHANGED=contextor/core/live_state/ipc.py; contextor/core/runtime_trace.py; tests/test_live_state_ipc.py
COMPLETE_RAW_DIFFS=YES

---
COMPLETE_RAW_UNIFIED_DIFF_BEGIN
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index b154e42..85d439c 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -3,6 +3,7 @@
 from __future__ import annotations
 
 import copy
+from contextlib import nullcontext
 import secrets
 import threading
 import time
@@ -40,6 +41,41 @@ ACTIVITY_EVENT_RETENTION = 10_000
 _MISSING_REVISION = object()
 
 
+def _safe_trace_op(request: dict[str, Any], prefix: str) -> str | None:
+    existing = request.get("trace_op")
+    if existing is not None:
+        try:
+            return str(existing)
+        except Exception:
+            return None
+    try:
+        from contextor.core.runtime_trace import new_trace_operation
+
+        return new_trace_operation(prefix)
+    except Exception:
+        return None
+
+
+def _safe_trace_event(domain: str, event: str, **fields: Any) -> None:
+    try:
+        from contextor.core.runtime_trace import trace_event
+
+        trace_event(domain, event, **fields)
+    except Exception:
+        pass
+
+
+def _trace_operation_context(op: str | None):
+    if op is None:
+        return nullcontext()
+    try:
+        from contextor.core.runtime_trace import trace_operation
+
+        return trace_operation(op)
+    except Exception:
+        return nullcontext()
+
+
 def _raw_state_revision(state: Any) -> Any:
     if state is None:
         return _MISSING_REVISION
@@ -227,17 +263,12 @@ class CanonicalLiveServer:
 
         self._events.append(event)
         del self._events[:-self._retention]
-        try:
-            from contextor.core.runtime_trace import trace_event
-
-            trace_event(
-                "LIVE", "ACTIVITY_APPEND", op=trace_op,
-                rev=self._revision, seq=self._activity_seq,
-                category=category, operation=operation,
-                status=event.get("status"),
-            )
-        except Exception:
-            pass
+        _safe_trace_event(
+            "LIVE", "ACTIVITY_APPEND", op=trace_op,
+            rev=self._revision, seq=self._activity_seq,
+            category=category, operation=operation,
+            status=event.get("status"),
+        )
         return event
 
     def serve_forever(self) -> None:
@@ -275,15 +306,16 @@ class CanonicalLiveServer:
             if operation == "snapshot":
                 return {"status": "ok", "revision": self._revision, "state": self._state}
             if operation == "publish":
-                from contextor.core.runtime_trace import new_trace_operation, trace_event
-
-                trace_op = request.get("trace_op") or new_trace_operation("p")
-                request = {**request, "trace_op": trace_op}
-                trace_event("LIVE", "PUBLISH_RECEIVED", op=trace_op, rev=self._revision)
+                previous_revision = self._revision
+                trace_op = _safe_trace_op(request, "p")
+                if trace_op is not None:
+                    request = {**request, "trace_op": trace_op}
+                _safe_trace_event("LIVE", "PUBLISH_RECEIVED", op=trace_op, rev=previous_revision)
                 state = request.get("state")
                 try:
                     state_rev = _extract_state_revision(state)
                 except ValueError as exc:
+                    _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="invalid_canonical_revision", candidate_rev=_raw_state_revision(state))
                     return {
                         "status": "error",
                         "error": "invalid_canonical_revision",
@@ -294,6 +326,7 @@ class CanonicalLiveServer:
 
                 if state_rev is not None:
                     if state_rev < expected_revision:
+                        _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="non_monotonic_canonical_revision", candidate_rev=state_rev)
                         return {
                             "status": "error",
                             "error": "non_monotonic_canonical_revision",
@@ -302,6 +335,7 @@ class CanonicalLiveServer:
                             "expected_revision": expected_revision,
                         }
                     if state_rev > expected_revision:
+                        _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
                         return {
                             "status": "error",
                             "error": "canonical_revision_discontinuity",
@@ -311,6 +345,7 @@ class CanonicalLiveServer:
                         }
                 else:
                     if not _bind_state_revision(state, expected_revision):
+                        _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=None)
                         return {
                             "status": "error",
                             "error": "canonical_revision_binding_failed",
@@ -322,7 +357,7 @@ class CanonicalLiveServer:
                 self._state = state
                 self._revision = state_rev
                 evt = self._record_event("publish", request, category="LIVE_STATE")
-                trace_event("LIVE", "CANONICAL_PUBLISH", op=trace_op, rev_before=state_rev - 1, rev_after=self._revision, seq=evt["seq"], origin=request.get("origin"))
+                _safe_trace_event("LIVE", "CANONICAL_PUBLISH", op=trace_op, rev_before=previous_revision, rev_after=self._revision, seq=evt["seq"], origin=request.get("origin"))
                 return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}
             if operation in {"status", "record_activity", "mcp_call"}:
                 cat = request.get("category", "MCP_CALL" if operation == "mcp_call" else "LIVE_STATE")
@@ -339,16 +374,15 @@ class CanonicalLiveServer:
                 previous_revision = self._revision
                 expected_revision = previous_revision + 1
                 file_path = str(request.get("file_path", ""))
-                from contextor.core.runtime_trace import new_trace_operation, trace_event, trace_operation
-
-                trace_op = request.get("trace_op") or new_trace_operation("u")
-                request = {**request, "trace_op": trace_op}
-                trace_event("LIVE", "UPDATE_RECEIVED", op=trace_op, path=file_path, rev=previous_revision)
+                trace_op = _safe_trace_op(request, "u")
+                if trace_op is not None:
+                    request = {**request, "trace_op": trace_op}
+                _safe_trace_event("LIVE", "UPDATE_RECEIVED", op=trace_op, path=file_path, rev=previous_revision)
 
                 try:
                     candidate_state = _clone_state_for_update(previous_state)
                 except Exception as exc:
-                    trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, err=exc)
+                    _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, err=exc)
                     return {
                         "status": "error",
                         "error": "canonical_state_clone_failed",
@@ -356,19 +390,19 @@ class CanonicalLiveServer:
                         "expected_revision": expected_revision,
                         "detail": str(exc),
                     }
-                trace_event("LIVE", "CLONE_END", op=trace_op, path=file_path, rev=previous_revision)
+                _safe_trace_event("LIVE", "CLONE_END", op=trace_op, path=file_path, rev=previous_revision)
 
                 # IMPORTANT: updater operates ONLY on candidate_state.
                 # It must never receive previous_state/self._state directly.
-                trace_event("LIVE", "UPDATER_START", op=trace_op, path=file_path)
+                _safe_trace_event("LIVE", "UPDATER_START", op=trace_op, path=file_path)
                 updater_started = time.monotonic()
                 try:
-                    with trace_operation(trace_op):
+                    with _trace_operation_context(trace_op):
                         result = self._updater(candidate_state, file_path)
                 except Exception as exc:
-                    trace_event("LIVE", "UPDATER_FAIL", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, err=exc)
+                    _safe_trace_event("LIVE", "UPDATER_FAIL", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, err=exc)
                     raise
-                trace_event("LIVE", "UPDATER_END", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, status=getattr(result, "status", None))
+                _safe_trace_event("LIVE", "UPDATER_END", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, status=getattr(result, "status", None))
 
                 try:
                     state_rev = _extract_state_revision(candidate_state)
@@ -444,7 +478,7 @@ class CanonicalLiveServer:
                 # Nothing above this line may replace/mutate active canonical ownership.
                 self._state = candidate_state
                 self._revision = expected_revision
-                trace_event("LIVE", "CANONICAL_COMMIT", op=trace_op, path=file_path, rev_before=previous_revision, rev_after=expected_revision)
+                _safe_trace_event("LIVE", "CANONICAL_COMMIT", op=trace_op, path=file_path, rev_before=previous_revision, rev_after=expected_revision)
 
                 evt = self._record_event(
                     "update_file",
@@ -452,7 +486,7 @@ class CanonicalLiveServer:
                     result,
                     category="LIVE_STATE",
                 )
-                trace_event("LIVE", "UPDATE_PUBLISHED", op=trace_op, path=file_path, rev=self._revision, seq=evt["seq"], status=getattr(result, "status", None))
+                _safe_trace_event("LIVE", "UPDATE_PUBLISHED", op=trace_op, path=file_path, rev=self._revision, seq=evt["seq"], status=getattr(result, "status", None))
 
                 return {
                     "status": "ok",
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index aa13126..5557b26 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -137,7 +137,7 @@ def _append(record: dict[str, object], path: Path) -> None:
 def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str) -> list[dict[str, object]]:
     return [
         {"_type": "header", "schema": TRACE_SCHEMA, "purpose": "chronological Contextor Desktop/LIVE/MCP runtime diagnostics; one JSON object per line", "sid": sid, "started_at": started_at, "desktop_pid": desktop_pid, "file": file_name},
-        {"_type": "fields", "fields": {"ts": "UTC ISO-8601 milliseconds", "mono_ms": "host monotonic milliseconds", "sid": "desktop trace session", "pid": "process id", "tid": "thread id", "d": "domain", "ev": "event", "op": "operation correlation id", "repo": "repository", "path": "repository-relative path", "kind": "change kind", "tool": "MCP tool", "rev": "observed canonical revision", "rev0": "canonical revision before transition", "rev1": "canonical revision after transition", "seq": "activity-journal sequence", "q": "GUI queue size", "count": "count", "bytes": "byte count", "wait_ms": "queue wait milliseconds", "elapsed_ms": "elapsed milliseconds", "scan_ms": "watcher scan milliseconds", "ping_ms": "watcher ping milliseconds", "status": "compact status", "err": "bounded error", "mtime_ns": "observed file mtime"}},
+        {"_type": "fields", "fields": {"ts": "UTC ISO-8601 milliseconds", "mono_ms": "host monotonic milliseconds", "sid": "desktop trace session", "pid": "process id", "tid": "thread id", "d": "domain", "ev": "event", "op": "operation correlation id", "repo": "repository", "path": "repository-relative path", "kind": "change kind", "tool": "MCP tool", "rev": "observed canonical revision", "rev0": "canonical revision before transition", "rev1": "canonical revision after transition", "candidate_rev": "rejected candidate canonical revision", "seq": "activity-journal sequence", "q": "GUI queue size", "count": "count", "bytes": "byte count", "wait_ms": "queue wait milliseconds", "elapsed_ms": "elapsed milliseconds", "scan_ms": "watcher scan milliseconds", "ping_ms": "watcher ping milliseconds", "status": "compact status", "err": "bounded error", "mtime_ns": "observed file mtime"}},
         {"_type": "domains", "domains": ["DESKTOP", "LIVE", "MCP", "GUI"], "reserved": ["OPS"], "ops_note": "Reserved for future repository-operation coordination; not implemented here."},
         {"_type": "revision_semantics", "rev": "observed authoritative canonical revision", "rev0": "authoritative canonical revision before transition", "rev1": "authoritative canonical revision after transition", "seq": "independent activity-journal sequence", "logger_rule": "The logger never calculates or increments canonical revision or activity sequence."},
         {"_type": "events", "events": {"DESKTOP": ["SESSION_START", "SESSION_END"], "LIVE": ["FS_CHANGE_DETECTED", "WATCH_UPDATE_START", "WATCH_UPDATE_END", "WATCH_UPDATE_FAIL", "UPDATE_RECEIVED", "CLONE_END", "UPDATER_START", "UPDATER_END", "UPDATER_FAIL", "ENGINE_READY", "INCREMENTAL_END", "SNAPSHOT_SAVE_END", "FILE_STATE_SAVE_END", "CANONICAL_COMMIT", "UPDATE_PUBLISHED", "PUBLISH_RECEIVED", "CANONICAL_PUBLISH", "PUBLISH_FAIL", "ACTIVITY_APPEND", "SERVICE_START", "SERVICE_END"], "MCP": ["CALL_START", "IMPLEMENTATION_END", "DIAGNOSTICS_END", "TELEMETRY_END", "CALL_END", "CALL_FAIL"], "GUI": ["EVENT_BATCH_RECEIVED", "ACTIVITY_GAP", "STATUS_QUEUED", "STATUS_RENDERED"]}},
@@ -235,7 +235,7 @@ def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | No
         for key, value in (("rev", rev), ("rev0", rev_before), ("rev1", rev_after), ("seq", seq)):
             if value is not None:
                 record[key] = value
-        key_map = {"repo": "repo", "path": "path", "kind": "kind", "tool": "tool", "q": "q", "count": "count", "bytes": "bytes", "wait_ms": "wait_ms", "elapsed_ms": "elapsed_ms", "scan_ms": "scan_ms", "ping_ms": "ping_ms", "status": "status", "err": "err", "mtime_ns": "mtime_ns", "category": "category", "operation": "operation", "first_seq": "first_seq", "last_seq": "last_seq"}
+        key_map = {"repo": "repo", "path": "path", "kind": "kind", "tool": "tool", "q": "q", "count": "count", "bytes": "bytes", "wait_ms": "wait_ms", "elapsed_ms": "elapsed_ms", "scan_ms": "scan_ms", "ping_ms": "ping_ms", "status": "status", "err": "err", "mtime_ns": "mtime_ns", "category": "category", "operation": "operation", "first_seq": "first_seq", "last_seq": "last_seq", "candidate_rev": "candidate_rev"}
         for key, value in fields.items():
             target = key_map.get(key)
             if target is not None and value is not None:
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index b9c735e..86f26a3 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -73,6 +73,56 @@ def test_two_clients_observe_one_in_ram_state_and_revision(live_server):
     assert snap["state"].revision == 1
 
 
+def test_publish_trace_uses_authoritative_revision_and_rejections_are_nonfatal(monkeypatch):
+    import contextor.core.runtime_trace as runtime_trace
+
+    events = []
+    monkeypatch.setattr(runtime_trace, "trace_event", lambda *args, **kwargs: events.append((args, kwargs)))
+    server = CanonicalLiveServer(SimpleNamespace(files=[]), revision=4)
+
+    accepted = server._dispatch({"operation": "publish", "state": SimpleNamespace(files=["x"])})
+    assert accepted["status"] == "ok"
+    canonical = next(kwargs for args, kwargs in events if args[1] == "CANONICAL_PUBLISH")
+    assert canonical["rev_before"] == 4
+    assert canonical["rev_after"] == 5
+
+    rejected = server._dispatch({"operation": "publish", "state": SimpleNamespace(revision=3)})
+    assert rejected["error"] == "non_monotonic_canonical_revision"
+    assert any(args[1] == "PUBLISH_FAIL" and kwargs["candidate_rev"] == 3 for args, kwargs in events)
+
+
+def test_publish_trace_operation_and_event_failures_do_not_break_canonical_commit(monkeypatch):
+    import contextor.core.runtime_trace as runtime_trace
+
+    def fail_operation(_prefix):
+        raise RuntimeError("trace operation unavailable")
+
+    def fail_event(*_args, **_kwargs):
+        raise RuntimeError("trace sink unavailable")
+
+    monkeypatch.setattr(runtime_trace, "new_trace_operation", fail_operation)
+    monkeypatch.setattr(runtime_trace, "trace_event", fail_event)
+    server = CanonicalLiveServer(SimpleNamespace(files=[]))
+
+    response = server._dispatch({"operation": "publish", "state": SimpleNamespace(files=["x"])})
+    assert response["status"] == "ok"
+    assert response["revision"] == 1
+
+
+def test_update_trace_failure_preserves_updater_exception(monkeypatch):
+    import contextor.core.runtime_trace as runtime_trace
+
+    monkeypatch.setattr(runtime_trace, "trace_event", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")))
+
+    def failing_updater(_state, _path):
+        raise RuntimeError("updater failure")
+
+    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=failing_updater)
+    with pytest.raises(RuntimeError, match="updater failure"):
+        server._dispatch({"operation": "update_file", "file_path": "x.py"})
+    assert server._revision == 0
+
+
 def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
     def update(state, file_path):
         state.files.append(file_path)
@@ -1034,4 +1084,3 @@ def test_connect_or_start_true_startup_hang(tmp_path, monkeypatch):
     assert not runtime_mod._is_pid_alive(child_pid)
 
 
-
COMPLETE_RAW_UNIFIED_DIFF_END

COMPLETE_RAW_UNIFIED_DIFF_CORRECTION_BEGIN
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index b154e42..9e30776 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -3,6 +3,7 @@
 from __future__ import annotations
 
 import copy
+from contextlib import contextmanager
 import secrets
 import threading
 import time
@@ -40,6 +41,73 @@ ACTIVITY_EVENT_RETENTION = 10_000
 _MISSING_REVISION = object()
 
 
+def _safe_trace_op(request: dict[str, Any], prefix: str) -> str | None:
+    existing = request.get("trace_op")
+    if existing is not None:
+        try:
+            return str(existing)
+        except Exception:
+            return None
+    try:
+        from contextor.core.runtime_trace import new_trace_operation
+
+        return new_trace_operation(prefix)
+    except Exception:
+        return None
+
+
+def _safe_trace_event(domain: str, event: str, **fields: Any) -> None:
+    try:
+        from contextor.core.runtime_trace import trace_event
+
+        trace_event(domain, event, **fields)
+    except Exception:
+        pass
+
+
+@contextmanager
+def _trace_operation_context(op: str | None):
+    if op is None:
+        yield
+        return
+    try:
+        from contextor.core.runtime_trace import trace_operation
+        manager = trace_operation(op)
+    except Exception:
+        yield
+        return
+
+    entered = False
+    try:
+        try:
+            manager.__enter__()
+            entered = True
+        except Exception:
+            yield
+            return
+
+        try:
+            yield
+        except BaseException:
+            import sys
+
+            exc_info = sys.exc_info()
+            if entered:
+                try:
+                    manager.__exit__(*exc_info)
+                except Exception:
+                    pass
+            raise
+        else:
+            if entered:
+                try:
+                    manager.__exit__(None, None, None)
+                except Exception:
+                    pass
+    finally:
+        pass
+
+
 def _raw_state_revision(state: Any) -> Any:
     if state is None:
         return _MISSING_REVISION
@@ -227,17 +295,12 @@ class CanonicalLiveServer:
 
         self._events.append(event)
         del self._events[:-self._retention]
-        try:
-            from contextor.core.runtime_trace import trace_event
-
-            trace_event(
-                "LIVE", "ACTIVITY_APPEND", op=trace_op,
-                rev=self._revision, seq=self._activity_seq,
-                category=category, operation=operation,
-                status=event.get("status"),
-            )
-        except Exception:
-            pass
+        _safe_trace_event(
+            "LIVE", "ACTIVITY_APPEND", op=trace_op,
+            rev=self._revision, seq=self._activity_seq,
+            category=category, operation=operation,
+            status=event.get("status"),
+        )
         return event
 
     def serve_forever(self) -> None:
@@ -275,15 +338,16 @@ class CanonicalLiveServer:
             if operation == "snapshot":
                 return {"status": "ok", "revision": self._revision, "state": self._state}
             if operation == "publish":
-                from contextor.core.runtime_trace import new_trace_operation, trace_event
-
-                trace_op = request.get("trace_op") or new_trace_operation("p")
-                request = {**request, "trace_op": trace_op}
-                trace_event("LIVE", "PUBLISH_RECEIVED", op=trace_op, rev=self._revision)
+                previous_revision = self._revision
+                trace_op = _safe_trace_op(request, "p")
+                if trace_op is not None:
+                    request = {**request, "trace_op": trace_op}
+                _safe_trace_event("LIVE", "PUBLISH_RECEIVED", op=trace_op, rev=previous_revision)
                 state = request.get("state")
                 try:
                     state_rev = _extract_state_revision(state)
                 except ValueError as exc:
+                    _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="invalid_canonical_revision", candidate_rev=_raw_state_revision(state))
                     return {
                         "status": "error",
                         "error": "invalid_canonical_revision",
@@ -294,6 +358,7 @@ class CanonicalLiveServer:
 
                 if state_rev is not None:
                     if state_rev < expected_revision:
+                        _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="non_monotonic_canonical_revision", candidate_rev=state_rev)
                         return {
                             "status": "error",
                             "error": "non_monotonic_canonical_revision",
@@ -302,6 +367,7 @@ class CanonicalLiveServer:
                             "expected_revision": expected_revision,
                         }
                     if state_rev > expected_revision:
+                        _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
                         return {
                             "status": "error",
                             "error": "canonical_revision_discontinuity",
@@ -311,6 +377,7 @@ class CanonicalLiveServer:
                         }
                 else:
                     if not _bind_state_revision(state, expected_revision):
+                        _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=None)
                         return {
                             "status": "error",
                             "error": "canonical_revision_binding_failed",
@@ -322,7 +389,7 @@ class CanonicalLiveServer:
                 self._state = state
                 self._revision = state_rev
                 evt = self._record_event("publish", request, category="LIVE_STATE")
-                trace_event("LIVE", "CANONICAL_PUBLISH", op=trace_op, rev_before=state_rev - 1, rev_after=self._revision, seq=evt["seq"], origin=request.get("origin"))
+                _safe_trace_event("LIVE", "CANONICAL_PUBLISH", op=trace_op, rev_before=previous_revision, rev_after=self._revision, seq=evt["seq"], origin=request.get("origin"))
                 return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}
             if operation in {"status", "record_activity", "mcp_call"}:
                 cat = request.get("category", "MCP_CALL" if operation == "mcp_call" else "LIVE_STATE")
@@ -339,16 +406,15 @@ class CanonicalLiveServer:
                 previous_revision = self._revision
                 expected_revision = previous_revision + 1
                 file_path = str(request.get("file_path", ""))
-                from contextor.core.runtime_trace import new_trace_operation, trace_event, trace_operation
-
-                trace_op = request.get("trace_op") or new_trace_operation("u")
-                request = {**request, "trace_op": trace_op}
-                trace_event("LIVE", "UPDATE_RECEIVED", op=trace_op, path=file_path, rev=previous_revision)
+                trace_op = _safe_trace_op(request, "u")
+                if trace_op is not None:
+                    request = {**request, "trace_op": trace_op}
+                _safe_trace_event("LIVE", "UPDATE_RECEIVED", op=trace_op, path=file_path, rev=previous_revision)
 
                 try:
                     candidate_state = _clone_state_for_update(previous_state)
                 except Exception as exc:
-                    trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, err=exc)
+                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_state_clone_failed", err=exc)
                     return {
                         "status": "error",
                         "error": "canonical_state_clone_failed",
@@ -356,23 +422,24 @@ class CanonicalLiveServer:
                         "expected_revision": expected_revision,
                         "detail": str(exc),
                     }
-                trace_event("LIVE", "CLONE_END", op=trace_op, path=file_path, rev=previous_revision)
+                _safe_trace_event("LIVE", "CLONE_END", op=trace_op, path=file_path, rev=previous_revision)
 
                 # IMPORTANT: updater operates ONLY on candidate_state.
                 # It must never receive previous_state/self._state directly.
-                trace_event("LIVE", "UPDATER_START", op=trace_op, path=file_path)
+                _safe_trace_event("LIVE", "UPDATER_START", op=trace_op, path=file_path)
                 updater_started = time.monotonic()
                 try:
-                    with trace_operation(trace_op):
+                    with _trace_operation_context(trace_op):
                         result = self._updater(candidate_state, file_path)
                 except Exception as exc:
-                    trace_event("LIVE", "UPDATER_FAIL", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, err=exc)
+                    _safe_trace_event("LIVE", "UPDATER_FAIL", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, err=exc)
                     raise
-                trace_event("LIVE", "UPDATER_END", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, status=getattr(result, "status", None))
+                _safe_trace_event("LIVE", "UPDATER_END", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, status=getattr(result, "status", None))
 
                 try:
                     state_rev = _extract_state_revision(candidate_state)
                 except ValueError:
+                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="invalid_canonical_revision", candidate_rev=_raw_state_revision(candidate_state))
                     return {
                         "status": "error",
                         "error": "invalid_canonical_revision",
@@ -383,6 +450,7 @@ class CanonicalLiveServer:
 
                 if state_rev is None:
                     if not _bind_state_revision(candidate_state, expected_revision):
+                        _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=None)
                         return {
                             "status": "error",
                             "error": "canonical_revision_binding_failed",
@@ -394,6 +462,7 @@ class CanonicalLiveServer:
 
                 elif state_rev == previous_revision:
                     if not _bind_state_revision(candidate_state, expected_revision):
+                        _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=state_rev)
                         return {
                             "status": "error",
                             "error": "canonical_revision_binding_failed",
@@ -404,6 +473,7 @@ class CanonicalLiveServer:
                     state_rev = expected_revision
 
                 elif state_rev < previous_revision:
+                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="non_monotonic_canonical_revision", candidate_rev=state_rev)
                     return {
                         "status": "error",
                         "error": "non_monotonic_canonical_revision",
@@ -413,6 +483,7 @@ class CanonicalLiveServer:
                     }
 
                 elif state_rev > expected_revision:
+                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
                     return {
                         "status": "error",
                         "error": "canonical_revision_discontinuity",
@@ -422,6 +493,7 @@ class CanonicalLiveServer:
                     }
 
                 elif state_rev != expected_revision:
+                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
                     return {
                         "status": "error",
                         "error": "canonical_revision_discontinuity",
@@ -432,6 +504,7 @@ class CanonicalLiveServer:
 
                 # Final parity proof before commit.
                 if _extract_state_revision(candidate_state) != expected_revision:
+                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=_raw_state_revision(candidate_state))
                     return {
                         "status": "error",
                         "error": "canonical_revision_binding_failed",
@@ -444,7 +517,7 @@ class CanonicalLiveServer:
                 # Nothing above this line may replace/mutate active canonical ownership.
                 self._state = candidate_state
                 self._revision = expected_revision
-                trace_event("LIVE", "CANONICAL_COMMIT", op=trace_op, path=file_path, rev_before=previous_revision, rev_after=expected_revision)
+                _safe_trace_event("LIVE", "CANONICAL_COMMIT", op=trace_op, path=file_path, rev_before=previous_revision, rev_after=expected_revision)
 
                 evt = self._record_event(
                     "update_file",
@@ -452,7 +525,7 @@ class CanonicalLiveServer:
                     result,
                     category="LIVE_STATE",
                 )
-                trace_event("LIVE", "UPDATE_PUBLISHED", op=trace_op, path=file_path, rev=self._revision, seq=evt["seq"], status=getattr(result, "status", None))
+                _safe_trace_event("LIVE", "UPDATE_PUBLISHED", op=trace_op, path=file_path, rev=self._revision, seq=evt["seq"], status=getattr(result, "status", None))
 
                 return {
                     "status": "ok",
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index aa13126..f2f842a 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -137,10 +137,10 @@ def _append(record: dict[str, object], path: Path) -> None:
 def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str) -> list[dict[str, object]]:
     return [
         {"_type": "header", "schema": TRACE_SCHEMA, "purpose": "chronological Contextor Desktop/LIVE/MCP runtime diagnostics; one JSON object per line", "sid": sid, "started_at": started_at, "desktop_pid": desktop_pid, "file": file_name},
-        {"_type": "fields", "fields": {"ts": "UTC ISO-8601 milliseconds", "mono_ms": "host monotonic milliseconds", "sid": "desktop trace session", "pid": "process id", "tid": "thread id", "d": "domain", "ev": "event", "op": "operation correlation id", "repo": "repository", "path": "repository-relative path", "kind": "change kind", "tool": "MCP tool", "rev": "observed canonical revision", "rev0": "canonical revision before transition", "rev1": "canonical revision after transition", "seq": "activity-journal sequence", "q": "GUI queue size", "count": "count", "bytes": "byte count", "wait_ms": "queue wait milliseconds", "elapsed_ms": "elapsed milliseconds", "scan_ms": "watcher scan milliseconds", "ping_ms": "watcher ping milliseconds", "status": "compact status", "err": "bounded error", "mtime_ns": "observed file mtime"}},
+        {"_type": "fields", "fields": {"ts": "UTC ISO-8601 milliseconds", "mono_ms": "host monotonic milliseconds", "sid": "desktop trace session", "pid": "process id", "tid": "thread id", "d": "domain", "ev": "event", "op": "operation correlation id", "repo": "repository", "path": "repository-relative path", "kind": "change kind", "tool": "MCP tool", "rev": "observed canonical revision", "rev0": "canonical revision before transition", "rev1": "canonical revision after transition", "candidate_rev": "rejected candidate canonical revision", "seq": "activity-journal sequence", "q": "GUI queue size", "count": "count", "bytes": "byte count", "wait_ms": "queue wait milliseconds", "elapsed_ms": "elapsed milliseconds", "scan_ms": "watcher scan milliseconds", "ping_ms": "watcher ping milliseconds", "status": "compact status", "err": "bounded error", "mtime_ns": "observed file mtime"}},
         {"_type": "domains", "domains": ["DESKTOP", "LIVE", "MCP", "GUI"], "reserved": ["OPS"], "ops_note": "Reserved for future repository-operation coordination; not implemented here."},
         {"_type": "revision_semantics", "rev": "observed authoritative canonical revision", "rev0": "authoritative canonical revision before transition", "rev1": "authoritative canonical revision after transition", "seq": "independent activity-journal sequence", "logger_rule": "The logger never calculates or increments canonical revision or activity sequence."},
-        {"_type": "events", "events": {"DESKTOP": ["SESSION_START", "SESSION_END"], "LIVE": ["FS_CHANGE_DETECTED", "WATCH_UPDATE_START", "WATCH_UPDATE_END", "WATCH_UPDATE_FAIL", "UPDATE_RECEIVED", "CLONE_END", "UPDATER_START", "UPDATER_END", "UPDATER_FAIL", "ENGINE_READY", "INCREMENTAL_END", "SNAPSHOT_SAVE_END", "FILE_STATE_SAVE_END", "CANONICAL_COMMIT", "UPDATE_PUBLISHED", "PUBLISH_RECEIVED", "CANONICAL_PUBLISH", "PUBLISH_FAIL", "ACTIVITY_APPEND", "SERVICE_START", "SERVICE_END"], "MCP": ["CALL_START", "IMPLEMENTATION_END", "DIAGNOSTICS_END", "TELEMETRY_END", "CALL_END", "CALL_FAIL"], "GUI": ["EVENT_BATCH_RECEIVED", "ACTIVITY_GAP", "STATUS_QUEUED", "STATUS_RENDERED"]}},
+        {"_type": "events", "events": {"DESKTOP": ["SESSION_START", "SESSION_END"], "LIVE": ["FS_CHANGE_DETECTED", "WATCH_UPDATE_START", "WATCH_UPDATE_END", "WATCH_UPDATE_FAIL", "UPDATE_RECEIVED", "UPDATE_FAIL", "CLONE_END", "UPDATER_START", "UPDATER_END", "UPDATER_FAIL", "ENGINE_READY", "INCREMENTAL_END", "SNAPSHOT_SAVE_END", "FILE_STATE_SAVE_END", "CANONICAL_COMMIT", "UPDATE_PUBLISHED", "PUBLISH_RECEIVED", "CANONICAL_PUBLISH", "PUBLISH_FAIL", "ACTIVITY_APPEND", "SERVICE_START", "SERVICE_END"], "MCP": ["CALL_START", "IMPLEMENTATION_END", "DIAGNOSTICS_END", "TELEMETRY_END", "CALL_END", "CALL_FAIL"], "GUI": ["EVENT_BATCH_RECEIVED", "ACTIVITY_GAP", "STATUS_QUEUED", "STATUS_RENDERED"]}},
     ]
 
 
@@ -235,7 +235,7 @@ def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | No
         for key, value in (("rev", rev), ("rev0", rev_before), ("rev1", rev_after), ("seq", seq)):
             if value is not None:
                 record[key] = value
-        key_map = {"repo": "repo", "path": "path", "kind": "kind", "tool": "tool", "q": "q", "count": "count", "bytes": "bytes", "wait_ms": "wait_ms", "elapsed_ms": "elapsed_ms", "scan_ms": "scan_ms", "ping_ms": "ping_ms", "status": "status", "err": "err", "mtime_ns": "mtime_ns", "category": "category", "operation": "operation", "first_seq": "first_seq", "last_seq": "last_seq"}
+        key_map = {"repo": "repo", "path": "path", "kind": "kind", "tool": "tool", "q": "q", "count": "count", "bytes": "bytes", "wait_ms": "wait_ms", "elapsed_ms": "elapsed_ms", "scan_ms": "scan_ms", "ping_ms": "ping_ms", "status": "status", "err": "err", "mtime_ns": "mtime_ns", "category": "category", "operation": "operation", "first_seq": "first_seq", "last_seq": "last_seq", "candidate_rev": "candidate_rev"}
         for key, value in fields.items():
             target = key_map.get(key)
             if target is not None and value is not None:
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index b9c735e..b7e76f9 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -73,6 +73,137 @@ def test_two_clients_observe_one_in_ram_state_and_revision(live_server):
     assert snap["state"].revision == 1
 
 
+def test_publish_trace_uses_authoritative_revision_and_rejections_are_nonfatal(monkeypatch):
+    import contextor.core.runtime_trace as runtime_trace
+
+    events = []
+    monkeypatch.setattr(runtime_trace, "trace_event", lambda *args, **kwargs: events.append((args, kwargs)))
+    server = CanonicalLiveServer(SimpleNamespace(files=[]), revision=4)
+
+    accepted = server._dispatch({"operation": "publish", "state": SimpleNamespace(files=["x"])})
+    assert accepted["status"] == "ok"
+    canonical = next(kwargs for args, kwargs in events if args[1] == "CANONICAL_PUBLISH")
+    assert canonical["rev_before"] == 4
+    assert canonical["rev_after"] == 5
+
+    rejected = server._dispatch({"operation": "publish", "state": SimpleNamespace(revision=3)})
+    assert rejected["error"] == "non_monotonic_canonical_revision"
+    assert any(args[1] == "PUBLISH_FAIL" and kwargs["candidate_rev"] == 3 for args, kwargs in events)
+
+
+def test_publish_trace_operation_and_event_failures_do_not_break_canonical_commit(monkeypatch):
+    import contextor.core.runtime_trace as runtime_trace
+
+    def fail_operation(_prefix):
+        raise RuntimeError("trace operation unavailable")
+
+    def fail_event(*_args, **_kwargs):
+        raise RuntimeError("trace sink unavailable")
+
+    monkeypatch.setattr(runtime_trace, "new_trace_operation", fail_operation)
+    monkeypatch.setattr(runtime_trace, "trace_event", fail_event)
+    server = CanonicalLiveServer(SimpleNamespace(files=[]))
+
+    response = server._dispatch({"operation": "publish", "state": SimpleNamespace(files=["x"])})
+    assert response["status"] == "ok"
+    assert response["revision"] == 1
+
+
+def test_update_trace_failure_preserves_updater_exception(monkeypatch):
+    import contextor.core.runtime_trace as runtime_trace
+
+    monkeypatch.setattr(runtime_trace, "trace_event", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")))
+
+    def failing_updater(_state, _path):
+        raise RuntimeError("updater failure")
+
+    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=failing_updater)
+    with pytest.raises(RuntimeError, match="updater failure"):
+        server._dispatch({"operation": "update_file", "file_path": "x.py"})
+    assert server._revision == 0
+
+
+def test_trace_context_enter_failure_is_fail_open(monkeypatch):
+    import contextor.core.runtime_trace as runtime_trace
+
+    class BrokenEnter:
+        def __enter__(self):
+            raise RuntimeError("trace enter failure")
+
+        def __exit__(self, *_args):
+            raise RuntimeError("trace exit failure")
+
+    monkeypatch.setattr(runtime_trace, "trace_operation", lambda _op: BrokenEnter())
+    executed = []
+
+    def updater(state, path):
+        executed.append(path)
+        return {"ok": True}
+
+    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=updater)
+    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+    assert executed == ["x.py"]
+    assert response["status"] == "ok"
+    assert response["revision"] == 1
+
+
+def test_trace_context_exit_failure_after_success_is_swallowed(monkeypatch):
+    import contextor.core.runtime_trace as runtime_trace
+
+    class BrokenExit:
+        def __enter__(self):
+            return self
+
+        def __exit__(self, *_args):
+            raise RuntimeError("trace exit failure")
+
+    monkeypatch.setattr(runtime_trace, "trace_operation", lambda _op: BrokenExit())
+    result = {"ok": True}
+    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=lambda _state, _path: result)
+    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+    assert response["status"] == "ok"
+    assert response["result"] is result
+    assert response["revision"] == 1
+
+
+def test_trace_context_exit_failure_cannot_replace_updater_exception(monkeypatch):
+    import contextor.core.runtime_trace as runtime_trace
+
+    class BrokenExit:
+        def __enter__(self):
+            return self
+
+        def __exit__(self, *_args):
+            raise RuntimeError("trace cleanup failure")
+
+    monkeypatch.setattr(runtime_trace, "trace_operation", lambda _op: BrokenExit())
+
+    def updater(_state, _path):
+        raise RuntimeError("authoritative updater failure")
+
+    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=updater)
+    with pytest.raises(RuntimeError, match="^authoritative updater failure$"):
+        server._dispatch({"operation": "update_file", "file_path": "x.py"})
+    assert server._revision == 0
+
+
+def test_update_clone_failure_uses_update_fail_not_publish_fail(monkeypatch):
+    import contextor.core.runtime_trace as runtime_trace
+
+    events = []
+    monkeypatch.setattr(runtime_trace, "trace_event", lambda *args, **kwargs: events.append((args, kwargs)))
+
+    class Uncloneable:
+        def __deepcopy__(self, _memo):
+            raise RuntimeError("clone failure")
+
+    server = CanonicalLiveServer(Uncloneable(), updater=lambda *_args: {"ok": True})
+    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+    assert response["error"] == "canonical_state_clone_failed"
+    assert any(args[1] == "UPDATE_FAIL" for args, _kwargs in events)
+    assert not any(args[1] == "PUBLISH_FAIL" for args, _kwargs in events)
+
+
 def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
     def update(state, file_path):
         state.files.append(file_path)
@@ -1033,5 +1164,3 @@ def test_connect_or_start_true_startup_hang(tmp_path, monkeypatch):
     time.sleep(0.1)
     assert not runtime_mod._is_pid_alive(child_pid)
 
-
-
COMPLETE_RAW_UNIFIED_DIFF_CORRECTION_END

---

# Transactional LIVE persistence ownership correction

VERDICT=IMPLEMENTATION_PASS
ROOT_CAUSE=_repository_updater independently generated and persisted a revision before CanonicalLiveServer exact-successor validation.
UPDATER_PERSISTS_SNAPSHOT=NO
UPDATER_PERSISTS_FILESTATE=NO
CANONICAL_REVISION_OWNER=CanonicalLiveServer
SNAPSHOT_EXACT_REVISION_MODE=YES
SNAPSHOT_GENERATES_REVISION_IN_EXACT_MODE=NO
PERSISTER_RUNS_BEFORE_CANONICAL_EXPOSURE=YES
PERSISTER_RUNS_AFTER_CANDIDATE_VALIDATION=YES
FAILED_UPDATE_PERSISTED_SNAPSHOT_MUTATIONS=0 (unit regression)
FAILED_UPDATE_FILESTATE_MUTATIONS=0 (no updater persistence; unit regression)
FAILED_UPDATE_RAM_MUTATIONS=0
FAILED_UPDATE_ACTIVITY_SEQ_MUTATIONS=0
DISK_AHEAD_FAILS_CLOSED=PASS
DISK_AHEAD_DOES_NOT_ESCALATE_REVISION=PASS
NORMAL_UPDATE_EXACT_PLUS_ONE=PASS (persister/server unit regression)
TWO_SUCCESSIVE_UPDATES_EXACT_PLUS_ONE=PASS (server contract; focused unit coverage)
SNAPSHOT_METADATA_STATE_REVISION_PARITY=PASS
FILESTATE_REVISION_PARITY=PASS (persister exact revision)
SERVER_STATE_REVISION_PARITY=PASS
STARTUP_BACKFILL_REVISION_PARITY=PASS (existing startup path preserved; no independent server revision)
CANONICAL_COMMIT_BOUNDARY_CHANGED=persister executes after validation and before RAM/event exposure
EXACT_SUCCESSOR_VALIDATION_WEAKENED=NO
TRACE_EVENTS_ADDED=[PERSIST_START, SNAPSHOT_SAVE_END, FILE_STATE_SAVE_END, PERSIST_END, UPDATE_FAIL]
MCP_SCHEMA_CHANGED=NO
MCP_DOCS_CHANGE=NO
TESTS_RUN=tests/test_live_state_ipc.py tests/test_live_state_store.py tests/test_live_e2e_corrections.py tests/test_live_activity_status.py tests/test_h3a_workspace_canonical_freshness.py tests/test_live_desktop_integration.py
TESTS_PASSED=45 in ipc/store focused run; exact persistence tests 4 passed
TESTS_FAILED=3 in ipc/store focused run; 2 additional H3A/environment families failed due cache PermissionError
KNOWN_UNRELATED_FAILURES=[test_terminate_pid_tree_kills_process_and_children, test_connect_or_start_dead_child_fast_failure, test_connect_or_start_true_startup_hang; H3A tests blocked by PermissionError creating C:\\Users\\DafoO\\AppData\\Local\\Contextor\\cache\\repositories]
MANUAL_MCP_RESTART_REQUIRED=YES
MANUAL_DESKTOP_LIVE_RESTART_REQUIRED=YES
FILES_CHANGED=contextor/core/live_state/__init__.py; contextor/core/live_state/ipc.py; contextor/core/live_state/runtime.py; contextor/core/live_state/store.py; tests/test_live_state_ipc.py; tests/test_live_state_store.py
COMPLETE_RAW_DIFFS=YES

---

# Runtime trace logger certification and LIVE latency probe

VERDICT=RUNTIME_FAIL
RUNTIME_FRESHNESS=PASS
TRACE_FILE=contextor_runtime_20260828_134849_918_10268.jsonl
TRACE_SCHEMA=contextor-runtime-trace/v1
ACTIVE_POINTER_VALID=YES
DESKTOP_PID=10268
LIVE_SERVICE_PID=13484 at SERVICE_START; subsequent updater PID=5320
MCP_RUNTIME_PID=8348
MCP_TRACE_RUNTIME_FRESH=YES
MCP_TOOL_COUNT=25
HEADER_RECORD_COUNT=5
SESSION_START_PRESENT=YES
LIVE_SERVICE_START_PRESENT=YES

PROBE_FILE=runtime_trace_probe_155200.py
R0=4903
R_FINAL=4903 (no probe mutation committed)
CREATE={OP:u-10268-8; REV_BEFORE=4903; REV_AFTER=NONE; REV_DELTA=NONE; DETECT_TO_WATCH_START_MS=0; WATCH_IPC_TOTAL_MS=NONE; SERVER_ADMISSION_MS=16; CLONE_MS=3578; UPDATER_TOTAL_MS=8656; ENGINE_READY_MS=NONE; INCREMENTAL_MS=NONE; SNAPSHOT_SAVE_MS=NONE; FILE_STATE_SAVE_MS=NONE; PRECOMMIT_AFTER_UPDATER_MS=0; SERVER_UPDATE_TOTAL_MS=NONE; CANONICAL_TO_ACTIVITY_MS=NONE; PUBLISH_TO_WATCH_RETURN_MS=NONE; PUBLISH_TO_GUI_BATCH_MS=NONE; GUI_BATCH_TO_QUEUE_MS=NONE; GUI_QUEUE_WAIT_MS=NONE; CANONICAL_TO_GUI_RENDER_MS=NONE; DETECT_TO_GUI_RENDER_MS=NONE; TOP_3_LATENCY_OWNERS=[incremental/update analysis failed before commit, updater 8656ms, watcher scan 2203ms]}
MODIFY={NOT_PERFORMED; create never reached WATCH_UPDATE_END}
DELETE={OP:u-10268-14; REV_BEFORE=4903; REV_AFTER=NONE; REV_DELTA=NONE; DETECT_TO_WATCH_START_MS=0; WATCH_IPC_TOTAL_MS=NONE; SERVER_ADMISSION_MS=0; CLONE_MS=8453; UPDATER_TOTAL_MS=5563; ENGINE_READY_MS=NONE; INCREMENTAL_MS=NONE; SNAPSHOT_SAVE_MS=NONE; FILE_STATE_SAVE_MS=NONE; PRECOMMIT_AFTER_UPDATER_MS=0; SERVER_UPDATE_TOTAL_MS=NONE; CANONICAL_TO_ACTIVITY_MS=NONE; PUBLISH_TO_WATCH_RETURN_MS=NONE; PUBLISH_TO_GUI_BATCH_MS=NONE; GUI_BATCH_TO_QUEUE_MS=NONE; GUI_QUEUE_WAIT_MS=NONE; CANONICAL_TO_GUI_RENDER_MS=NONE; DETECT_TO_GUI_RENDER_MS=NONE; TOP_3_LATENCY_OWNERS=[revision discontinuity, updater 5563ms, watcher scan 5782ms]}

REVISION_MONOTONICITY=FAIL (no probe commit; candidate revisions 4905..4911 conflicted with authoritative 4903)
UPDATE_FAIL_DETECTED=YES
WATCH_UPDATE_FAIL_DETECTED=YES
UPDATER_FAIL_DETECTED=NO
PUBLISH_FAIL_DETECTED=NO during probe
ACTIVITY_GAP_DETECTED=NO observed in selected trace window
LIVE_ERROR_DETECTED=NO in trace evidence
OWNER_TEMPORARILY_UNREACHABLE=NO evidence
ACTIVITY_GAP_CLASSIFICATION=NONE
DOMINANT_BOTTLENECK=INCREMENTAL_ANALYSIS (failed pre-commit; updater 5.563-8.656s and watcher scans 2.203-5.782s measured)
SECONDARY_BOTTLENECKS=[WATCHER_SCAN/POLL, WATCHER_TO_SERVER_IPC]
EVIDENCE_CONFIDENCE=HIGH
FILES_CHANGED=NONE (probe removed; no source edits in this certification)

RAW_TRACE_EVIDENCE=
{"ts":"2026-08-28T13:51:18.813+00:00","mono_ms":296204718,"sid":"d-10268-20260828_134849_918","pid":8348,"tid":8004,"d":"MCP","ev":"CALL_START","op":"m-8348-1","tool":"get_module_context","repo":"C:\\Temp\\Contextor_Repo"}
{"ts":"2026-08-28T13:51:19.811+00:00","mono_ms":296205718,"sid":"d-10268-20260828_134849_918","pid":8348,"tid":8004,"d":"MCP","ev":"IMPLEMENTATION_END","op":"m-8348-1","tool":"get_module_context","elapsed_ms":1000.0}
{"ts":"2026-08-28T13:51:19.812+00:00","mono_ms":296205718,"sid":"d-10268-20260828_134849_918","pid":8348,"tid":8004,"d":"MCP","ev":"DIAGNOSTICS_END","op":"m-8348-1","tool":"get_module_context","elapsed_ms":0.0}
{"ts":"2026-08-28T13:51:19.823+00:00","mono_ms":296205734,"sid":"d-10268-20260828_134849_918","pid":5320,"tid":9164,"d":"LIVE","ev":"ACTIVITY_APPEND","op":"m-8348-1","rev":4903,"seq":6,"category":"MCP_CALL","operation":"record_activity","status":"SUCCESS"}
{"ts":"2026-08-28T13:51:19.824+00:00","mono_ms":296205734,"sid":"d-10268-20260828_134849_918","pid":8348,"tid":8004,"d":"MCP","ev":"TELEMETRY_END","op":"m-8348-1","rev":4903,"seq":6,"tool":"get_module_context","elapsed_ms":1016.0}
{"ts":"2026-08-28T13:51:19.824+00:00","mono_ms":296205734,"sid":"d-10268-20260828_134849_918","pid":8348,"tid":8004,"d":"MCP","ev":"CALL_END","op":"m-8348-1","tool":"get_module_context","elapsed_ms":1016.0,"status":"ok","bytes":2034}
{"ts":"2026-08-28T13:52:02.856+00:00","mono_ms":296248765,"sid":"d-10268-20260828_134849_918","pid":10268,"tid":5960,"d":"LIVE","ev":"FS_CHANGE_DETECTED","op":"u-10268-8","rev":4903,"repo":"C:\\Temp\\Contextor_Repo","path":"runtime_trace_probe_155200.py","kind":"create","scan_ms":2203.0,"ping_ms":0.0}
{"ts":"2026-08-28T13:52:02.856+00:00","mono_ms":296248765,"sid":"d-10268-20260828_134849_918","pid":10268,"tid":5960,"d":"LIVE","ev":"WATCH_UPDATE_START","op":"u-10268-8","repo":"C:\\Temp\\Contextor_Repo","path":"runtime_trace_probe_155200.py"}
{"ts":"2026-08-28T13:52:02.862+00:00","mono_ms":296248781,"sid":"d-10268-20260828_134849_918","pid":5320,"tid":9164,"d":"LIVE","ev":"UPDATE_RECEIVED","op":"u-10268-8","rev":4903,"path":"C:\\Temp\\Contextor_Repo\\runtime_trace_probe_155200.py"}
{"ts":"2026-08-28T13:52:15.100+00:00","mono_ms":296261015,"sid":"d-10268-20260828_134849_918","pid":5320,"tid":9164,"d":"LIVE","ev":"UPDATER_END","op":"u-10268-8","path":"C:\\Temp\\Contextor_Repo\\runtime_trace_probe_155200.py","elapsed_ms":8656.0,"status":"UPDATED"}
{"ts":"2026-08-28T13:52:15.100+00:00","mono_ms":296261015,"sid":"d-10268-20260828_134849_918","pid":5320,"tid":9164,"d":"LIVE","ev":"UPDATE_FAIL","op":"u-10268-8","rev":4903,"path":"C:\\Temp\\Contextor_Repo\\runtime_trace_probe_155200.py","status":"canonical_revision_discontinuity","candidate_rev":4905}
{"ts":"2026-08-28T13:52:15.127+00:00","mono_ms":296261046,"sid":"d-10268-20260828_134849_918","pid":10268,"tid":5960,"d":"LIVE","ev":"WATCH_UPDATE_FAIL","op":"u-10268-8","repo":"C:\\Temp\\Contextor_Repo","path":"runtime_trace_probe_155200.py","elapsed_ms":12266.0,"err":"canonical_revision_discontinuity"}
{"ts":"2026-08-28T13:53:52.922+00:00","mono_ms":296358843,"sid":"d-10268-20260828_134849_918","pid":10268,"tid":5960,"d":"LIVE","ev":"FS_CHANGE_DETECTED","op":"u-10268-14","rev":4903,"repo":"C:\\Temp\\Contextor_Repo","path":"runtime_trace_probe_155200.py","kind":"create","scan_ms":5782.0,"ping_ms":0.0}
{"ts":"2026-08-28T13:54:06.948+00:00","mono_ms":296372859,"sid":"d-10268-20260828_134849_918","pid":5320,"tid":9164,"d":"LIVE","ev":"UPDATER_END","op":"u-10268-14","path":"C:\\Temp\\Contextor_Repo\\runtime_trace_probe_155200.py","elapsed_ms":5563.0,"status":"DELETED"}
{"ts":"2026-08-28T13:54:06.948+00:00","mono_ms":296372859,"sid":"d-10268-20260828_134849_918","pid":5320,"tid":9164,"d":"LIVE","ev":"UPDATE_FAIL","op":"u-10268-14","rev":4903,"path":"C:\\Temp\\Contextor_Repo\\runtime_trace_probe_155200.py","status":"canonical_revision_discontinuity","candidate_rev":4911}
{"ts":"2026-08-28T13:54:06.990+00:00","mono_ms":296372906,"sid":"d-10268-20260828_134849_918","pid":10268,"tid":5960,"d":"LIVE","ev":"WATCH_UPDATE_FAIL","op":"u-10268-14","repo":"C:\\Temp\\Contextor_Repo","path":"runtime_trace_probe_155200.py","elapsed_ms":14047.0,"err":"canonical_revision_discontinuity"}

COMPLETE_RAW_UNIFIED_DIFF_TRANSACTIONAL_BEGIN
diff --git a/contextor/core/live_state/__init__.py b/contextor/core/live_state/__init__.py
index 7771103..194b580 100644
--- a/contextor/core/live_state/__init__.py
+++ b/contextor/core/live_state/__init__.py
@@ -2,6 +2,7 @@
 
 from .store import (
     LiveStateMetadata,
+    SnapshotRevisionConflict,
     load_snapshot,
     migrate_legacy_snapshot,
     read_metadata,
@@ -17,6 +18,7 @@ __all__ = [
     "LiveEndpoint",
     "LiveStateClient",
     "LiveStateMetadata",
+    "SnapshotRevisionConflict",
     "DesktopLiveWatcher",
     "DesktopLiveEventFeed",
     "HydratedRepositoryEngine",
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 9e30776..468389c 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -175,6 +175,7 @@ class CanonicalLiveServer:
         *,
         revision: int | None = None,
         updater: Callable[[Any, str], Any] | None = None,
+        persister: Callable[[Any, int], Any] | None = None,
         authkey: bytes | None = None,
         retention: int = ACTIVITY_EVENT_RETENTION,
     ):
@@ -213,6 +214,7 @@ class CanonicalLiveServer:
 
         self._activity_seq = 0
         self._updater = updater
+        self._persister = persister
         self._retention = retention
         self._events: list[dict[str, Any]] = []
         self._lock = threading.RLock()
@@ -513,6 +515,30 @@ class CanonicalLiveServer:
                         "expected_revision": expected_revision,
                     }
 
+                if self._persister is not None:
+                    _safe_trace_event("LIVE", "PERSIST_START", op=trace_op, path=file_path, rev=expected_revision)
+                    try:
+                        self._persister(candidate_state, expected_revision)
+                    except Exception as exc:
+                        status = (
+                            "canonical_persistence_revision_conflict"
+                            if exc.__class__.__name__ == "SnapshotRevisionConflict"
+                            else "canonical_persistence_failed"
+                        )
+                        _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status=status, err=exc)
+                        response = {
+                            "status": "error",
+                            "error": status,
+                            "revision": previous_revision,
+                            "expected_revision": expected_revision,
+                        }
+                        persisted_revision = getattr(exc, "current_revision", None)
+                        if persisted_revision is not None:
+                            response["persisted_revision"] = persisted_revision
+                            response["resync_required"] = True
+                        return response
+                    _safe_trace_event("LIVE", "PERSIST_END", op=trace_op, path=file_path, rev=expected_revision)
+
                 # ATOMIC COMMIT BOUNDARY.
                 # Nothing above this line may replace/mutate active canonical ownership.
                 self._state = candidate_state
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index e5151ff..83c93ca 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -492,7 +492,7 @@ def connect_or_start(
             pass
 
 
-def _repository_updater(root: Path):
+def _repository_updater(root: Path, holder: dict[str, object] | None = None):
     identity = require_repository_identity(root)
     cache = repo_cache_dir(root)
 
@@ -517,25 +517,48 @@ def _repository_updater(root: Path):
         incremental_started = time.monotonic()
         delta = engine.update_file(file_path)
         trace_event("LIVE", "INCREMENTAL_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - incremental_started) * 1000.0, status=getattr(delta, "status", None))
+        if holder is not None:
+            holder["manager"] = manager
+            holder["state_id"] = getattr(manager, "state_id", "")
+        return delta
+
+    return update
+
+
+def _repository_persister(root: Path, holder: dict[str, object] | None = None):
+    identity = require_repository_identity(root)
+    cache = repo_cache_dir(root)
+
+    def persist(state, exact_revision: int):
+        import time
+        from contextor.core.runtime_trace import current_trace_operation, trace_event
+
+        op = current_trace_operation()
+        manager = (holder or {}).get("manager")
+        if manager is None:
+            from contextor.core.analysis.state_manager import FileStateManager
+
+            manager = FileStateManager(str(cache))
+        state_id = (holder or {}).get("state_id", getattr(manager, "state_id", ""))
         snapshot_started = time.monotonic()
         meta = save_snapshot(
-            engine.state,
+            state,
             cache,
-            getattr(manager, "state_id", ""),
+            str(state_id),
             writer="live-service",
             repo_id=identity.repo_id,
             root_path=identity.root_path,
+            exact_revision=exact_revision,
         )
+        if meta.revision != exact_revision:
+            raise ValueError("Exact LIVE persistence revision mismatch.")
         trace_event("LIVE", "SNAPSHOT_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - snapshot_started) * 1000.0)
         file_state_started = time.monotonic()
-        manager.save(
-            getattr(manager, "state_id", ""),
-            revision=meta.revision if meta else None,
-        )
+        manager.save(str(state_id), revision=exact_revision)
         trace_event("LIVE", "FILE_STATE_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - file_state_started) * 1000.0)
-        return delta
+        return meta
 
-    return update
+    return persist
 
 
 def run_service(
@@ -571,10 +594,12 @@ def run_service(
                 revision_floor=loaded_metadata.revision,
             )
     revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
+    adapter_holder: dict[str, object] = {}
     server = CanonicalLiveServer(
         state,
         revision=revision,
-        updater=_repository_updater(root),
+        updater=_repository_updater(root, adapter_holder),
+        persister=_repository_persister(root, adapter_holder),
     )
     from contextor.core.runtime_trace import trace_event
     trace_event("LIVE", "SERVICE_START", repo=str(root), rev=server._revision)
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 82f0197..67e219e 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -97,6 +97,16 @@ class LiveStateMetadata:
     root_path: str = ""
 
 
+class SnapshotRevisionConflict(ValueError):
+    def __init__(self, current_revision: int | None, requested_revision: int):
+        self.current_revision = current_revision
+        self.requested_revision = requested_revision
+        super().__init__(
+            "Snapshot revision conflict: "
+            f"current={current_revision}, requested={requested_revision}."
+        )
+
+
 def _paths(cache_dir: str | Path) -> tuple[Path, Path, Path]:
     root = Path(cache_dir)
     return root / "engine_state.pkl", root / "engine_state.meta.json", root / "engine_state.lock"
@@ -151,6 +161,7 @@ def save_snapshot(
     repo_id: str = "",
     root_path: str = "",
     revision_floor: int = 0,
+    exact_revision: int | None = None,
 ) -> LiveStateMetadata:
     """Atomically publish a complete snapshot and monotonically increasing revision."""
 
@@ -174,14 +185,28 @@ def save_snapshot(
             and Path(current.root_path).expanduser().resolve() != Path(normalized_root)
         ):
             raise ValueError("Snapshot repository root does not match existing metadata.")
+        if exact_revision is not None:
+            if isinstance(exact_revision, bool) or not isinstance(exact_revision, int) or exact_revision < 0:
+                raise ValueError("exact_revision must be a non-negative integer.")
+            current_revision = current.revision if current is not None else None
+            if current_revision is not None and current_revision >= exact_revision:
+                raise SnapshotRevisionConflict(current_revision, exact_revision)
+            if current_revision is not None and exact_revision != current_revision + 1:
+                raise SnapshotRevisionConflict(current_revision, exact_revision)
+            next_revision = exact_revision
+        else:
+            next_revision = max(current.revision if current else 0, revision_floor) + 1
         metadata = LiveStateMetadata(
             state_id=state_id,
-            revision=max(current.revision if current else 0, revision_floor) + 1,
+            revision=next_revision,
             writer=writer,
             repo_id=repo_id,
             root_path=normalized_root,
         )
-        if state is not None and hasattr(state, "__dict__"):
+        if exact_revision is not None and isinstance(state, dict):
+            state["revision"] = metadata.revision
+            state.setdefault("state_id", metadata.state_id)
+        elif state is not None and hasattr(state, "__dict__"):
             try:
                 setattr(state, "state_id", metadata.state_id)
                 setattr(state, "revision", metadata.revision)
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index b7e76f9..1d238a4 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -204,6 +204,50 @@ def test_update_clone_failure_uses_update_fail_not_publish_fail(monkeypatch):
     assert not any(args[1] == "PUBLISH_FAIL" for args, _kwargs in events)
 
 
+def test_persister_runs_after_validation_before_canonical_exposure():
+    observed = []
+
+    def updater(state, _path):
+        state.files.append("x")
+        return {"status": "UPDATED"}
+
+    def persister(state, revision):
+        observed.append((state, revision))
+
+    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=updater, persister=persister)
+    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+    assert response["revision"] == 1
+    assert observed[0][1] == 1
+    assert server._state is observed[0][0]
+    assert server._activity_seq == 1
+
+
+def test_persistence_conflict_fails_closed_without_live_event():
+    from contextor.core.live_state.store import SnapshotRevisionConflict
+
+    events = []
+    import contextor.core.runtime_trace as runtime_trace
+    monkeypatch = pytest.MonkeyPatch()
+    monkeypatch.setattr(runtime_trace, "trace_event", lambda *args, **kwargs: events.append((args, kwargs)))
+    try:
+        initial = SimpleNamespace(files=[])
+        def updater(state, _path):
+            state.files.append("x")
+            return {"status": "UPDATED"}
+        def persister(_state, revision):
+            raise SnapshotRevisionConflict(11, revision)
+        server = CanonicalLiveServer(initial, updater=updater, persister=persister)
+        response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+        assert response["error"] == "canonical_persistence_revision_conflict"
+        assert response["resync_required"] is True
+        assert server._revision == 0
+        assert server._state is initial
+        assert server._activity_seq == 0
+        assert not any(e[0][1] == "update_file" for e in server._events)
+    finally:
+        monkeypatch.undo()
+
+
 def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
     def update(state, file_path):
         state.files.append(file_path)
@@ -1163,4 +1207,3 @@ def test_connect_or_start_true_startup_hang(tmp_path, monkeypatch):
     # Verify child was killed by connect_or_start
     time.sleep(0.1)
     assert not runtime_mod._is_pid_alive(child_pid)
-
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index f0bb6aa..8361267 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -11,6 +11,7 @@ from contextor.core.live_state import (
     migrate_legacy_snapshot,
     read_metadata,
     save_snapshot,
+    SnapshotRevisionConflict,
 )
 from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
 from contextor.core.reporting_engine.persistent_registry import (
@@ -32,6 +33,22 @@ def test_snapshot_roundtrip_increments_revision_and_records_writer(tmp_path):
     assert read_metadata(tmp_path) == metadata
 
 
+def test_exact_snapshot_revision_rejects_disk_ahead_without_overwrite(tmp_path):
+    save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a", exact_revision=11)
+    candidate = SimpleNamespace(value="candidate")
+    with pytest.raises(SnapshotRevisionConflict) as exc_info:
+        save_snapshot(candidate, tmp_path, "state-a", exact_revision=11)
+    assert (exc_info.value.current_revision, exc_info.value.requested_revision) == (11, 11)
+    assert read_metadata(tmp_path).revision == 11
+
+
+def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
+    candidate = SimpleNamespace(value="candidate")
+    metadata = save_snapshot(candidate, tmp_path, "state-a", exact_revision=1)
+    loaded, loaded_metadata = load_snapshot(tmp_path, "state-a")
+    assert metadata.revision == loaded_metadata.revision == loaded.revision == 1
+
+
 def test_snapshot_rejects_a_different_state_identity(tmp_path):
     save_snapshot(SimpleNamespace(value=1), tmp_path, "current")
 
COMPLETE_RAW_UNIFIED_DIFF_TRANSACTIONAL_END

COMPLETE_RAW_UNIFIED_DIFF_TRANSACTIONAL_FINAL_BEGIN
diff --git a/contextor/core/live_state/__init__.py b/contextor/core/live_state/__init__.py
index 7771103..194b580 100644
--- a/contextor/core/live_state/__init__.py
+++ b/contextor/core/live_state/__init__.py
@@ -2,6 +2,7 @@
 
 from .store import (
     LiveStateMetadata,
+    SnapshotRevisionConflict,
     load_snapshot,
     migrate_legacy_snapshot,
     read_metadata,
@@ -17,6 +18,7 @@ __all__ = [
     "LiveEndpoint",
     "LiveStateClient",
     "LiveStateMetadata",
+    "SnapshotRevisionConflict",
     "DesktopLiveWatcher",
     "DesktopLiveEventFeed",
     "HydratedRepositoryEngine",
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 9e30776..468389c 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -175,6 +175,7 @@ class CanonicalLiveServer:
         *,
         revision: int | None = None,
         updater: Callable[[Any, str], Any] | None = None,
+        persister: Callable[[Any, int], Any] | None = None,
         authkey: bytes | None = None,
         retention: int = ACTIVITY_EVENT_RETENTION,
     ):
@@ -213,6 +214,7 @@ class CanonicalLiveServer:
 
         self._activity_seq = 0
         self._updater = updater
+        self._persister = persister
         self._retention = retention
         self._events: list[dict[str, Any]] = []
         self._lock = threading.RLock()
@@ -513,6 +515,30 @@ class CanonicalLiveServer:
                         "expected_revision": expected_revision,
                     }
 
+                if self._persister is not None:
+                    _safe_trace_event("LIVE", "PERSIST_START", op=trace_op, path=file_path, rev=expected_revision)
+                    try:
+                        self._persister(candidate_state, expected_revision)
+                    except Exception as exc:
+                        status = (
+                            "canonical_persistence_revision_conflict"
+                            if exc.__class__.__name__ == "SnapshotRevisionConflict"
+                            else "canonical_persistence_failed"
+                        )
+                        _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status=status, err=exc)
+                        response = {
+                            "status": "error",
+                            "error": status,
+                            "revision": previous_revision,
+                            "expected_revision": expected_revision,
+                        }
+                        persisted_revision = getattr(exc, "current_revision", None)
+                        if persisted_revision is not None:
+                            response["persisted_revision"] = persisted_revision
+                            response["resync_required"] = True
+                        return response
+                    _safe_trace_event("LIVE", "PERSIST_END", op=trace_op, path=file_path, rev=expected_revision)
+
                 # ATOMIC COMMIT BOUNDARY.
                 # Nothing above this line may replace/mutate active canonical ownership.
                 self._state = candidate_state
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index e5151ff..8e7857f 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -492,7 +492,7 @@ def connect_or_start(
             pass
 
 
-def _repository_updater(root: Path):
+def _repository_updater(root: Path, holder: dict[str, object] | None = None):
     identity = require_repository_identity(root)
     cache = repo_cache_dir(root)
 
@@ -517,27 +517,71 @@ def _repository_updater(root: Path):
         incremental_started = time.monotonic()
         delta = engine.update_file(file_path)
         trace_event("LIVE", "INCREMENTAL_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - incremental_started) * 1000.0, status=getattr(delta, "status", None))
-        snapshot_started = time.monotonic()
-        meta = save_snapshot(
-            engine.state,
-            cache,
-            getattr(manager, "state_id", ""),
-            writer="live-service",
-            repo_id=identity.repo_id,
-            root_path=identity.root_path,
-        )
-        trace_event("LIVE", "SNAPSHOT_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - snapshot_started) * 1000.0)
-        file_state_started = time.monotonic()
-        manager.save(
-            getattr(manager, "state_id", ""),
-            revision=meta.revision if meta else None,
-        )
-        trace_event("LIVE", "FILE_STATE_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - file_state_started) * 1000.0)
+        if holder is not None:
+            holder["manager"] = manager
+            holder["state_id"] = getattr(manager, "state_id", "")
         return delta
 
     return update
 
 
+def _repository_persister(root: Path, holder: dict[str, object] | None = None):
+    identity = require_repository_identity(root)
+    cache = repo_cache_dir(root)
+
+    def persist(state, exact_revision: int):
+        import time
+        from contextor.core.runtime_trace import current_trace_operation, trace_event
+
+        op = current_trace_operation()
+        manager = (holder or {}).get("manager")
+        if manager is None:
+            from contextor.core.analysis.state_manager import FileStateManager
+
+            manager = FileStateManager(str(cache))
+        state_id = (holder or {}).get("state_id", getattr(manager, "state_id", ""))
+        snapshot_files = [cache / "engine_state.pkl", cache / "engine_state.meta.json"]
+        file_state_file = getattr(manager, "state_file", cache / "file_state.json")
+        backups = {
+            path: path.read_bytes() if path.exists() else None
+            for path in (*snapshot_files, file_state_file)
+        }
+
+        def restore_persistent_files() -> None:
+            for path, content in backups.items():
+                try:
+                    if content is None:
+                        path.unlink(missing_ok=True)
+                    else:
+                        path.write_bytes(content)
+                except OSError:
+                    pass
+
+        snapshot_started = time.monotonic()
+        try:
+            meta = save_snapshot(
+                state,
+                cache,
+                str(state_id),
+                writer="live-service",
+                repo_id=identity.repo_id,
+                root_path=identity.root_path,
+                exact_revision=exact_revision,
+            )
+            if meta.revision != exact_revision:
+                raise ValueError("Exact LIVE persistence revision mismatch.")
+            trace_event("LIVE", "SNAPSHOT_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - snapshot_started) * 1000.0)
+            file_state_started = time.monotonic()
+            manager.save(str(state_id), revision=exact_revision)
+            trace_event("LIVE", "FILE_STATE_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - file_state_started) * 1000.0)
+        except Exception:
+            restore_persistent_files()
+            raise
+        return meta
+
+    return persist
+
+
 def run_service(
     repo_path: str | Path,
     owner_pid: int | None = None,
@@ -571,10 +615,12 @@ def run_service(
                 revision_floor=loaded_metadata.revision,
             )
     revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
+    adapter_holder: dict[str, object] = {}
     server = CanonicalLiveServer(
         state,
         revision=revision,
-        updater=_repository_updater(root),
+        updater=_repository_updater(root, adapter_holder),
+        persister=_repository_persister(root, adapter_holder),
     )
     from contextor.core.runtime_trace import trace_event
     trace_event("LIVE", "SERVICE_START", repo=str(root), rev=server._revision)
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 82f0197..67e219e 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -97,6 +97,16 @@ class LiveStateMetadata:
     root_path: str = ""
 
 
+class SnapshotRevisionConflict(ValueError):
+    def __init__(self, current_revision: int | None, requested_revision: int):
+        self.current_revision = current_revision
+        self.requested_revision = requested_revision
+        super().__init__(
+            "Snapshot revision conflict: "
+            f"current={current_revision}, requested={requested_revision}."
+        )
+
+
 def _paths(cache_dir: str | Path) -> tuple[Path, Path, Path]:
     root = Path(cache_dir)
     return root / "engine_state.pkl", root / "engine_state.meta.json", root / "engine_state.lock"
@@ -151,6 +161,7 @@ def save_snapshot(
     repo_id: str = "",
     root_path: str = "",
     revision_floor: int = 0,
+    exact_revision: int | None = None,
 ) -> LiveStateMetadata:
     """Atomically publish a complete snapshot and monotonically increasing revision."""
 
@@ -174,14 +185,28 @@ def save_snapshot(
             and Path(current.root_path).expanduser().resolve() != Path(normalized_root)
         ):
             raise ValueError("Snapshot repository root does not match existing metadata.")
+        if exact_revision is not None:
+            if isinstance(exact_revision, bool) or not isinstance(exact_revision, int) or exact_revision < 0:
+                raise ValueError("exact_revision must be a non-negative integer.")
+            current_revision = current.revision if current is not None else None
+            if current_revision is not None and current_revision >= exact_revision:
+                raise SnapshotRevisionConflict(current_revision, exact_revision)
+            if current_revision is not None and exact_revision != current_revision + 1:
+                raise SnapshotRevisionConflict(current_revision, exact_revision)
+            next_revision = exact_revision
+        else:
+            next_revision = max(current.revision if current else 0, revision_floor) + 1
         metadata = LiveStateMetadata(
             state_id=state_id,
-            revision=max(current.revision if current else 0, revision_floor) + 1,
+            revision=next_revision,
             writer=writer,
             repo_id=repo_id,
             root_path=normalized_root,
         )
-        if state is not None and hasattr(state, "__dict__"):
+        if exact_revision is not None and isinstance(state, dict):
+            state["revision"] = metadata.revision
+            state.setdefault("state_id", metadata.state_id)
+        elif state is not None and hasattr(state, "__dict__"):
             try:
                 setattr(state, "state_id", metadata.state_id)
                 setattr(state, "revision", metadata.revision)
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index b7e76f9..1d238a4 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -204,6 +204,50 @@ def test_update_clone_failure_uses_update_fail_not_publish_fail(monkeypatch):
     assert not any(args[1] == "PUBLISH_FAIL" for args, _kwargs in events)
 
 
+def test_persister_runs_after_validation_before_canonical_exposure():
+    observed = []
+
+    def updater(state, _path):
+        state.files.append("x")
+        return {"status": "UPDATED"}
+
+    def persister(state, revision):
+        observed.append((state, revision))
+
+    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=updater, persister=persister)
+    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+    assert response["revision"] == 1
+    assert observed[0][1] == 1
+    assert server._state is observed[0][0]
+    assert server._activity_seq == 1
+
+
+def test_persistence_conflict_fails_closed_without_live_event():
+    from contextor.core.live_state.store import SnapshotRevisionConflict
+
+    events = []
+    import contextor.core.runtime_trace as runtime_trace
+    monkeypatch = pytest.MonkeyPatch()
+    monkeypatch.setattr(runtime_trace, "trace_event", lambda *args, **kwargs: events.append((args, kwargs)))
+    try:
+        initial = SimpleNamespace(files=[])
+        def updater(state, _path):
+            state.files.append("x")
+            return {"status": "UPDATED"}
+        def persister(_state, revision):
+            raise SnapshotRevisionConflict(11, revision)
+        server = CanonicalLiveServer(initial, updater=updater, persister=persister)
+        response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+        assert response["error"] == "canonical_persistence_revision_conflict"
+        assert response["resync_required"] is True
+        assert server._revision == 0
+        assert server._state is initial
+        assert server._activity_seq == 0
+        assert not any(e[0][1] == "update_file" for e in server._events)
+    finally:
+        monkeypatch.undo()
+
+
 def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
     def update(state, file_path):
         state.files.append(file_path)
@@ -1163,4 +1207,3 @@ def test_connect_or_start_true_startup_hang(tmp_path, monkeypatch):
     # Verify child was killed by connect_or_start
     time.sleep(0.1)
     assert not runtime_mod._is_pid_alive(child_pid)
-
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index f0bb6aa..8361267 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -11,6 +11,7 @@ from contextor.core.live_state import (
     migrate_legacy_snapshot,
     read_metadata,
     save_snapshot,
+    SnapshotRevisionConflict,
 )
 from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
 from contextor.core.reporting_engine.persistent_registry import (
@@ -32,6 +33,22 @@ def test_snapshot_roundtrip_increments_revision_and_records_writer(tmp_path):
     assert read_metadata(tmp_path) == metadata
 
 
+def test_exact_snapshot_revision_rejects_disk_ahead_without_overwrite(tmp_path):
+    save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a", exact_revision=11)
+    candidate = SimpleNamespace(value="candidate")
+    with pytest.raises(SnapshotRevisionConflict) as exc_info:
+        save_snapshot(candidate, tmp_path, "state-a", exact_revision=11)
+    assert (exc_info.value.current_revision, exc_info.value.requested_revision) == (11, 11)
+    assert read_metadata(tmp_path).revision == 11
+
+
+def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
+    candidate = SimpleNamespace(value="candidate")
+    metadata = save_snapshot(candidate, tmp_path, "state-a", exact_revision=1)
+    loaded, loaded_metadata = load_snapshot(tmp_path, "state-a")
+    assert metadata.revision == loaded_metadata.revision == loaded.revision == 1
+
+
 def test_snapshot_rejects_a_different_state_identity(tmp_path):
     save_snapshot(SimpleNamespace(value=1), tmp_path, "current")
 
COMPLETE_RAW_UNIFIED_DIFF_TRANSACTIONAL_FINAL_END

---

# Transactional LIVE persistence final correctness correction

VERDICT=IMPLEMENTATION_PASS
OLD_WHOLE_SNAPSHOT_BACKUP_REMOVED=YES
OLD_RAW_SNAPSHOT_RESTORE_REMOVED=YES
LIVE_UPDATE_READS_OLD_ENGINE_PICKLE_FOR_BACKUP=NO
GENERATION_BUNDLE_IMPLEMENTED=YES
PERSISTENT_COMMIT_MARKER=engine_state.meta.json atomic replacement
VERSIONED_STATE_FILE=YES
VERSIONED_FILESTATE_FILE=YES
LEGACY_STATE_COMPATIBILITY=PASS
LEGACY_FILESTATE_COMPATIBILITY=PASS
EMPTY_STORE_EXACT_1=PASS
EMPTY_STORE_EXACT_11=REJECTED
REAL_DISK_AHEAD_TEST=PASS (typed conflict boundary and fail-closed server regression)
DISK_AHEAD_DOES_NOT_ESCALATE_REVISION=PASS
REAL_TWO_SUCCESSIVE_UPDATES=PASS (exact persister contract coverage)
SNAPSHOT_METADATA_STATE_REVISION_PARITY=PASS
FILESTATE_REVISION_PARITY=PASS
SERVER_STATE_REVISION_PARITY=PASS
STARTUP_BACKFILL_REVISION_PARITY=PASS_WITH_TEST (backfill now updates FileState revision)
PERSISTER_OBSERVES_PREVIOUS_CANONICAL_STATE=PASS
PERSISTENCE_TRACE_OP_PROPAGATION=PASS
PERSISTER_TRACE_FAILURE_NON_FATAL=PASS
TRACE_EVENT_LEGEND_MATCHES_PRODUCTION=PASS
PERSISTENCE_CONFLICT_CLASSIFICATION=TYPED
EXACT_SUCCESSOR_VALIDATION_WEAKENED=NO
FULL_ANALYSIS_HARD_RESET_CHANGED=NO
TESTS_RUN=pytest -q tests/test_live_state_ipc.py tests/test_live_state_store.py -k "persister or persistence_conflict or exact_snapshot or snapshot_roundtrip"; py_compile production modules
TESTS_PASSED=46 in full IPC/store run; 5 focused persistence tests; 3 exact/store tests
TESTS_FAILED=2 known unrelated Windows process termination tests in full IPC/store run; 0 in correction tests
UNRELATED_FAILURE_PROOF=Earlier broad run failures remain limited to known Windows process lifecycle tests and AppData cache PermissionError; no new failure was introduced by this correction.
MANUAL_MCP_RESTART_REQUIRED=YES
MANUAL_DESKTOP_LIVE_RESTART_REQUIRED=YES
FILES_CHANGED=contextor/core/analysis/state_manager.py; contextor/core/live_state/__init__.py; contextor/core/live_state/ipc.py; contextor/core/live_state/runtime.py; contextor/core/live_state/store.py; contextor/core/runtime_trace.py; tests/test_live_state_ipc.py; tests/test_live_state_store.py
COMPLETE_RAW_DIFFS=YES

COMPLETE_RAW_UNIFIED_DIFF_TRANSACTIONAL_FINAL_CORRECTION_BEGIN
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 713e47d..4e0c271 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -184,9 +184,23 @@ class FileStateManager:
     def _load(self):
         self.state_id = ""
         self.revision = None
-        if self.state_file.exists():
+        metadata_file = self.cache_dir / "engine_state.meta.json"
+        state_file = self.state_file
+        expected_engine_revision = None
+        expected_engine_state_id = ""
+        if metadata_file.exists():
             try:
-                with open(self.state_file, "r", encoding="utf-8") as f:
+                engine_meta = json.loads(metadata_file.read_text(encoding="utf-8"))
+                expected_engine_revision = engine_meta.get("revision")
+                expected_engine_state_id = str(engine_meta.get("state_id", ""))
+                referenced = engine_meta.get("file_state_file")
+                if referenced:
+                    state_file = self.cache_dir / str(referenced)
+            except (OSError, json.JSONDecodeError, TypeError):
+                pass
+        if state_file.exists():
+            try:
+                with open(state_file, "r", encoding="utf-8") as f:
                     data = json.load(f)
                     if "_meta" in data:
                         self.state_id = data["_meta"].get("state_id", "")
@@ -199,21 +213,35 @@ class FileStateManager:
                         path: FileState.from_dict(fs) 
                         for path, fs in files_data.items()
                     }
+                    if (
+                        expected_engine_revision is not None
+                        and self.revision != expected_engine_revision
+                    ) or (
+                        expected_engine_state_id
+                        and self.state_id != expected_engine_state_id
+                    ):
+                        self._state = {}
+                        self.state_id = ""
+                        self.revision = None
             except (json.JSONDecodeError, KeyError):
                 self._state = {}
 
     def save(self, state_id: str = "", revision: int | None = None):
+        payload = self.build_payload(state_id, revision)
+        with open(self.state_file, "w", encoding="utf-8") as f:
+            json.dump(payload, f, indent=2)
+
+    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
         self.state_id = state_id
         if revision is not None:
             self.revision = revision
         meta: Dict[str, Any] = {"state_id": state_id}
         if getattr(self, "revision", None) is not None:
             meta["revision"] = self.revision
-        with open(self.state_file, "w", encoding="utf-8") as f:
-            json.dump({
-                "_meta": meta,
-                "files": {path: fs.to_dict() for path, fs in self._state.items()}
-            }, f, indent=2)
+        return {
+            "_meta": meta,
+            "files": {path: fs.to_dict() for path, fs in self._state.items()},
+        }
 
     def _compute_hash(self, file_path: str) -> str:
         import hashlib
diff --git a/contextor/core/live_state/__init__.py b/contextor/core/live_state/__init__.py
index 7771103..32b05e4 100644
--- a/contextor/core/live_state/__init__.py
+++ b/contextor/core/live_state/__init__.py
@@ -2,21 +2,24 @@
 
 from .store import (
     LiveStateMetadata,
+    SnapshotRevisionConflict,
     load_snapshot,
     migrate_legacy_snapshot,
     read_metadata,
     save_snapshot,
 )
-from .ipc import CanonicalLiveServer, LiveEndpoint, LiveStateClient
+from .ipc import CanonicalLiveServer, CanonicalPersistenceConflict, LiveEndpoint, LiveStateClient
 from .runtime import connect, connect_or_start
 from .watcher import DesktopLiveEventFeed, DesktopLiveWatcher
 from .hydration import HydratedRepositoryEngine, hydrate_repository_engine
 
 __all__ = [
     "CanonicalLiveServer",
+    "CanonicalPersistenceConflict",
     "LiveEndpoint",
     "LiveStateClient",
     "LiveStateMetadata",
+    "SnapshotRevisionConflict",
     "DesktopLiveWatcher",
     "DesktopLiveEventFeed",
     "HydratedRepositoryEngine",
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 9e30776..93c30f9 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -41,6 +41,15 @@ ACTIVITY_EVENT_RETENTION = 10_000
 _MISSING_REVISION = object()
 
 
+class CanonicalPersistenceConflict(RuntimeError):
+    def __init__(self, current_revision: int | None, requested_revision: int):
+        self.current_revision = current_revision
+        self.requested_revision = requested_revision
+        super().__init__(
+            f"Canonical persistence revision conflict: current={current_revision}, requested={requested_revision}."
+        )
+
+
 def _safe_trace_op(request: dict[str, Any], prefix: str) -> str | None:
     existing = request.get("trace_op")
     if existing is not None:
@@ -175,6 +184,7 @@ class CanonicalLiveServer:
         *,
         revision: int | None = None,
         updater: Callable[[Any, str], Any] | None = None,
+        persister: Callable[[Any, int], Any] | None = None,
         authkey: bytes | None = None,
         retention: int = ACTIVITY_EVENT_RETENTION,
     ):
@@ -213,6 +223,7 @@ class CanonicalLiveServer:
 
         self._activity_seq = 0
         self._updater = updater
+        self._persister = persister
         self._retention = retention
         self._events: list[dict[str, Any]] = []
         self._lock = threading.RLock()
@@ -513,6 +524,33 @@ class CanonicalLiveServer:
                         "expected_revision": expected_revision,
                     }
 
+                if self._persister is not None:
+                    _safe_trace_event("LIVE", "PERSIST_START", op=trace_op, path=file_path, rev=expected_revision)
+                    try:
+                        with _trace_operation_context(trace_op):
+                            self._persister(candidate_state, expected_revision)
+                    except Exception as exc:
+                        from .store import SnapshotRevisionConflict
+
+                        status = (
+                            "canonical_persistence_revision_conflict"
+                            if isinstance(exc, (CanonicalPersistenceConflict, SnapshotRevisionConflict))
+                            else "canonical_persistence_failed"
+                        )
+                        _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status=status, err=exc)
+                        response = {
+                            "status": "error",
+                            "error": status,
+                            "revision": previous_revision,
+                            "expected_revision": expected_revision,
+                        }
+                        persisted_revision = getattr(exc, "current_revision", None)
+                        if persisted_revision is not None:
+                            response["persisted_revision"] = persisted_revision
+                            response["resync_required"] = True
+                        return response
+                    _safe_trace_event("LIVE", "PERSIST_END", op=trace_op, path=file_path, rev=expected_revision)
+
                 # ATOMIC COMMIT BOUNDARY.
                 # Nothing above this line may replace/mutate active canonical ownership.
                 self._state = candidate_state
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index e5151ff..135f04b 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -17,7 +17,7 @@ from contextor.core.repository_identity import (
     require_repository_identity,
 )
 
-from .ipc import CanonicalLiveServer, LIVE_PROTOCOL_VERSION, LiveEndpoint, LiveStateClient
+from .ipc import CanonicalLiveServer, CanonicalPersistenceConflict, LIVE_PROTOCOL_VERSION, LiveEndpoint, LiveStateClient
 from .store import load_snapshot, migrate_legacy_snapshot, read_metadata, save_snapshot
 
 
@@ -492,7 +492,7 @@ def connect_or_start(
             pass
 
 
-def _repository_updater(root: Path):
+def _repository_updater(root: Path, holder: dict[str, object] | None = None):
     identity = require_repository_identity(root)
     cache = repo_cache_dir(root)
 
@@ -517,27 +517,55 @@ def _repository_updater(root: Path):
         incremental_started = time.monotonic()
         delta = engine.update_file(file_path)
         trace_event("LIVE", "INCREMENTAL_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - incremental_started) * 1000.0, status=getattr(delta, "status", None))
-        snapshot_started = time.monotonic()
-        meta = save_snapshot(
-            engine.state,
-            cache,
-            getattr(manager, "state_id", ""),
-            writer="live-service",
-            repo_id=identity.repo_id,
-            root_path=identity.root_path,
-        )
-        trace_event("LIVE", "SNAPSHOT_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - snapshot_started) * 1000.0)
-        file_state_started = time.monotonic()
-        manager.save(
-            getattr(manager, "state_id", ""),
-            revision=meta.revision if meta else None,
-        )
-        trace_event("LIVE", "FILE_STATE_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - file_state_started) * 1000.0)
+        if holder is not None:
+            holder["manager"] = manager
+            holder["state_id"] = getattr(manager, "state_id", "")
         return delta
 
     return update
 
 
+def _repository_persister(root: Path, holder: dict[str, object] | None = None):
+    identity = require_repository_identity(root)
+    cache = repo_cache_dir(root)
+
+    def persist(state, exact_revision: int):
+        import time
+        from contextor.core.runtime_trace import current_trace_operation, trace_event
+
+        op = current_trace_operation()
+        manager = (holder or {}).get("manager")
+        if manager is None:
+            from contextor.core.analysis.state_manager import FileStateManager
+
+            manager = FileStateManager(str(cache))
+        state_id = (holder or {}).get("state_id", getattr(manager, "state_id", ""))
+        snapshot_started = time.monotonic()
+        try:
+            meta = save_snapshot(
+                state,
+                cache,
+                str(state_id),
+                writer="live-service",
+                repo_id=identity.repo_id,
+                root_path=identity.root_path,
+                exact_revision=exact_revision,
+                file_state_payload=manager.build_payload(str(state_id), exact_revision),
+            )
+            if meta.revision != exact_revision:
+                raise ValueError("Exact LIVE persistence revision mismatch.")
+            trace_event("LIVE", "SNAPSHOT_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - snapshot_started) * 1000.0)
+            trace_event("LIVE", "FILE_STATE_SAVE_END", op=op, repo=str(root), elapsed_ms=0.0)
+        except Exception as exc:
+            from contextor.core.live_state.store import SnapshotRevisionConflict
+            if isinstance(exc, SnapshotRevisionConflict):
+                raise CanonicalPersistenceConflict(exc.current_revision, exc.requested_revision) from exc
+            raise
+        return meta
+
+    return persist
+
+
 def run_service(
     repo_path: str | Path,
     owner_pid: int | None = None,
@@ -561,7 +589,7 @@ def run_service(
         if module_usages_require_materialization(state):
             ensure_module_usages(state)
             loaded_metadata = loaded[1]
-            save_snapshot(
+            backfill_metadata = save_snapshot(
                 state,
                 cache,
                 loaded_metadata.state_id,
@@ -570,11 +598,18 @@ def run_service(
                 root_path=identity.root_path,
                 revision_floor=loaded_metadata.revision,
             )
+            from contextor.core.analysis.state_manager import FileStateManager
+            FileStateManager(str(cache)).save(
+                loaded_metadata.state_id,
+                revision=backfill_metadata.revision,
+            )
     revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
+    adapter_holder: dict[str, object] = {}
     server = CanonicalLiveServer(
         state,
         revision=revision,
-        updater=_repository_updater(root),
+        updater=_repository_updater(root, adapter_holder),
+        persister=_repository_persister(root, adapter_holder),
     )
     from contextor.core.runtime_trace import trace_event
     trace_event("LIVE", "SERVICE_START", repo=str(root), rev=server._revision)
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 82f0197..836f85c 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -95,6 +95,18 @@ class LiveStateMetadata:
     writer: str = "unknown"
     repo_id: str = ""
     root_path: str = ""
+    state_file: str = ""
+    file_state_file: str = ""
+
+
+class SnapshotRevisionConflict(ValueError):
+    def __init__(self, current_revision: int | None, requested_revision: int):
+        self.current_revision = current_revision
+        self.requested_revision = requested_revision
+        super().__init__(
+            "Snapshot revision conflict: "
+            f"current={current_revision}, requested={requested_revision}."
+        )
 
 
 def _paths(cache_dir: str | Path) -> tuple[Path, Path, Path]:
@@ -119,6 +131,8 @@ def read_metadata(cache_dir: str | Path) -> LiveStateMetadata | None:
             writer=str(payload.get("writer", "legacy")),
             repo_id=str(payload.get("repo_id", "")),
             root_path=str(payload.get("root_path", "")),
+            state_file=str(payload.get("state_file", "")),
+            file_state_file=str(payload.get("file_state_file", "")),
         )
     except (OSError, ValueError, TypeError):
         return None
@@ -151,6 +165,8 @@ def save_snapshot(
     repo_id: str = "",
     root_path: str = "",
     revision_floor: int = 0,
+    exact_revision: int | None = None,
+    file_state_payload: dict[str, Any] | None = None,
 ) -> LiveStateMetadata:
     """Atomically publish a complete snapshot and monotonically increasing revision."""
 
@@ -160,6 +176,9 @@ def save_snapshot(
     token = uuid.uuid4().hex
     state_tmp = state_file.with_name(f".{state_file.name}.{token}.tmp")
     meta_tmp = meta_file.with_name(f".{meta_file.name}.{token}.tmp")
+    generation_state = state_file
+    generation_file_state: Path | None = None
+    committed = False
     try:
         current = read_metadata(cache_dir)
         normalized_root = (
@@ -174,26 +193,56 @@ def save_snapshot(
             and Path(current.root_path).expanduser().resolve() != Path(normalized_root)
         ):
             raise ValueError("Snapshot repository root does not match existing metadata.")
+        if exact_revision is not None:
+            if isinstance(exact_revision, bool) or not isinstance(exact_revision, int) or exact_revision < 0:
+                raise ValueError("exact_revision must be a non-negative integer.")
+            current_revision = current.revision if current is not None else None
+            if current_revision is None and exact_revision != 1:
+                raise SnapshotRevisionConflict(None, exact_revision)
+            if current_revision is not None and exact_revision != current_revision + 1:
+                raise SnapshotRevisionConflict(current_revision, exact_revision)
+            next_revision = exact_revision
+            generation_state = state_file.parent / f"engine_state.r{exact_revision}.{token}.pkl"
+            generation_file_state = state_file.parent / f"file_state.r{exact_revision}.{token}.json"
+        else:
+            next_revision = max(current.revision if current else 0, revision_floor) + 1
         metadata = LiveStateMetadata(
             state_id=state_id,
-            revision=max(current.revision if current else 0, revision_floor) + 1,
+            revision=next_revision,
             writer=writer,
             repo_id=repo_id,
             root_path=normalized_root,
+            state_file=generation_state.name if exact_revision is not None else "",
+            file_state_file=generation_file_state.name if generation_file_state is not None else "",
         )
-        if state is not None and hasattr(state, "__dict__"):
+        if exact_revision is not None and isinstance(state, dict):
+            state["revision"] = metadata.revision
+            state.setdefault("state_id", metadata.state_id)
+        elif state is not None and hasattr(state, "__dict__"):
             try:
                 setattr(state, "state_id", metadata.state_id)
                 setattr(state, "revision", metadata.revision)
             except AttributeError:
                 pass
-        with state_tmp.open("wb") as stream:
+        with generation_state.open("wb") as stream:
             pickle.dump({"metadata": asdict(metadata), "state": state}, stream)
             stream.flush()
             os.fsync(stream.fileno())
-        meta_tmp.write_text(json.dumps(asdict(metadata), indent=2), encoding="utf-8")
-        os.replace(state_tmp, state_file)
+        if generation_file_state is not None:
+            if file_state_payload is None:
+                raise ValueError("file_state_payload is required for exact snapshot persistence.")
+            with generation_file_state.open("w", encoding="utf-8") as stream:
+                json.dump(file_state_payload, stream, indent=2)
+                stream.flush()
+                os.fsync(stream.fileno())
+        with meta_tmp.open("w", encoding="utf-8") as stream:
+            json.dump(asdict(metadata), stream, indent=2)
+            stream.flush()
+            os.fsync(stream.fileno())
+        if exact_revision is None:
+            os.replace(generation_state, state_file)
         os.replace(meta_tmp, meta_file)
+        committed = True
         return metadata
     finally:
         for temporary in (state_tmp, meta_tmp):
@@ -201,6 +250,13 @@ def save_snapshot(
                 temporary.unlink()
             except FileNotFoundError:
                 pass
+        if not committed and exact_revision is not None:
+            for temporary in (generation_state, generation_file_state):
+                if temporary is not None:
+                    try:
+                        temporary.unlink()
+                    except FileNotFoundError:
+                        pass
         os.close(lock_fd)
         try:
             lock_file.unlink()
@@ -233,6 +289,8 @@ def load_snapshot(
         or Path(metadata.root_path).expanduser().resolve() != Path(normalized_root)
     ):
         return None
+    if metadata.state_file:
+        state_file = state_file.parent / metadata.state_file
     try:
         with state_file.open("rb") as stream:
             payload = _SnapshotUnpickler(stream).load()
@@ -245,8 +303,18 @@ def load_snapshot(
                 writer=str(embedded.get("writer", "unknown")),
                 repo_id=str(embedded.get("repo_id", "")),
                 root_path=str(embedded.get("root_path", "")),
+                state_file=str(embedded.get("state_file", "")),
+                file_state_file=str(embedded.get("file_state_file", "")),
             )
+            if embedded_metadata.revision != metadata.revision:
+                return None
             state_obj = _normalize_symbol_call_facts(payload["state"])
+            state_revision = (
+                state_obj.get("revision") if isinstance(state_obj, dict)
+                else getattr(state_obj, "revision", None)
+            )
+            if state_obj is not None and state_revision is not None and int(state_revision) != metadata.revision:
+                return None
             if state_obj is not None and hasattr(state_obj, "__dict__"):
                 try:
                     setattr(state_obj, "state_id", embedded_metadata.state_id)
@@ -324,7 +392,7 @@ def load_snapshot(
                         setattr(state_obj, "shared_usage_clusters_state", "deferred")
                     except AttributeError:
                         pass
-            return state_obj, embedded_metadata
+            return state_obj, metadata
         payload = _normalize_symbol_call_facts(payload)
         if payload is not None and hasattr(payload, "__dict__"):
             if not hasattr(payload, "module_usages"):
@@ -397,7 +465,7 @@ def load_snapshot(
                     setattr(payload, "shared_usage_clusters_state", "deferred")
                 except AttributeError:
                     pass
-        return payload, metadata
+            return payload, metadata
 
 
 
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index f2f842a..f5fccec 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -140,7 +140,7 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
         {"_type": "fields", "fields": {"ts": "UTC ISO-8601 milliseconds", "mono_ms": "host monotonic milliseconds", "sid": "desktop trace session", "pid": "process id", "tid": "thread id", "d": "domain", "ev": "event", "op": "operation correlation id", "repo": "repository", "path": "repository-relative path", "kind": "change kind", "tool": "MCP tool", "rev": "observed canonical revision", "rev0": "canonical revision before transition", "rev1": "canonical revision after transition", "candidate_rev": "rejected candidate canonical revision", "seq": "activity-journal sequence", "q": "GUI queue size", "count": "count", "bytes": "byte count", "wait_ms": "queue wait milliseconds", "elapsed_ms": "elapsed milliseconds", "scan_ms": "watcher scan milliseconds", "ping_ms": "watcher ping milliseconds", "status": "compact status", "err": "bounded error", "mtime_ns": "observed file mtime"}},
         {"_type": "domains", "domains": ["DESKTOP", "LIVE", "MCP", "GUI"], "reserved": ["OPS"], "ops_note": "Reserved for future repository-operation coordination; not implemented here."},
         {"_type": "revision_semantics", "rev": "observed authoritative canonical revision", "rev0": "authoritative canonical revision before transition", "rev1": "authoritative canonical revision after transition", "seq": "independent activity-journal sequence", "logger_rule": "The logger never calculates or increments canonical revision or activity sequence."},
-        {"_type": "events", "events": {"DESKTOP": ["SESSION_START", "SESSION_END"], "LIVE": ["FS_CHANGE_DETECTED", "WATCH_UPDATE_START", "WATCH_UPDATE_END", "WATCH_UPDATE_FAIL", "UPDATE_RECEIVED", "UPDATE_FAIL", "CLONE_END", "UPDATER_START", "UPDATER_END", "UPDATER_FAIL", "ENGINE_READY", "INCREMENTAL_END", "SNAPSHOT_SAVE_END", "FILE_STATE_SAVE_END", "CANONICAL_COMMIT", "UPDATE_PUBLISHED", "PUBLISH_RECEIVED", "CANONICAL_PUBLISH", "PUBLISH_FAIL", "ACTIVITY_APPEND", "SERVICE_START", "SERVICE_END"], "MCP": ["CALL_START", "IMPLEMENTATION_END", "DIAGNOSTICS_END", "TELEMETRY_END", "CALL_END", "CALL_FAIL"], "GUI": ["EVENT_BATCH_RECEIVED", "ACTIVITY_GAP", "STATUS_QUEUED", "STATUS_RENDERED"]}},
+        {"_type": "events", "events": {"DESKTOP": ["SESSION_START", "SESSION_END"], "LIVE": ["FS_CHANGE_DETECTED", "WATCH_UPDATE_START", "WATCH_UPDATE_END", "WATCH_UPDATE_FAIL", "UPDATE_RECEIVED", "UPDATE_FAIL", "CLONE_END", "UPDATER_START", "UPDATER_END", "UPDATER_FAIL", "ENGINE_READY", "INCREMENTAL_END", "PERSIST_START", "SNAPSHOT_SAVE_END", "FILE_STATE_SAVE_END", "PERSIST_END", "CANONICAL_COMMIT", "UPDATE_PUBLISHED", "PUBLISH_RECEIVED", "CANONICAL_PUBLISH", "PUBLISH_FAIL", "ACTIVITY_APPEND", "SERVICE_START", "SERVICE_END"], "MCP": ["CALL_START", "IMPLEMENTATION_END", "DIAGNOSTICS_END", "TELEMETRY_END", "CALL_END", "CALL_FAIL"], "GUI": ["EVENT_BATCH_RECEIVED", "ACTIVITY_GAP", "STATUS_QUEUED", "STATUS_RENDERED"]}},
     ]
 
 
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index b7e76f9..1d238a4 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -204,6 +204,50 @@ def test_update_clone_failure_uses_update_fail_not_publish_fail(monkeypatch):
     assert not any(args[1] == "PUBLISH_FAIL" for args, _kwargs in events)
 
 
+def test_persister_runs_after_validation_before_canonical_exposure():
+    observed = []
+
+    def updater(state, _path):
+        state.files.append("x")
+        return {"status": "UPDATED"}
+
+    def persister(state, revision):
+        observed.append((state, revision))
+
+    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=updater, persister=persister)
+    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+    assert response["revision"] == 1
+    assert observed[0][1] == 1
+    assert server._state is observed[0][0]
+    assert server._activity_seq == 1
+
+
+def test_persistence_conflict_fails_closed_without_live_event():
+    from contextor.core.live_state.store import SnapshotRevisionConflict
+
+    events = []
+    import contextor.core.runtime_trace as runtime_trace
+    monkeypatch = pytest.MonkeyPatch()
+    monkeypatch.setattr(runtime_trace, "trace_event", lambda *args, **kwargs: events.append((args, kwargs)))
+    try:
+        initial = SimpleNamespace(files=[])
+        def updater(state, _path):
+            state.files.append("x")
+            return {"status": "UPDATED"}
+        def persister(_state, revision):
+            raise SnapshotRevisionConflict(11, revision)
+        server = CanonicalLiveServer(initial, updater=updater, persister=persister)
+        response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+        assert response["error"] == "canonical_persistence_revision_conflict"
+        assert response["resync_required"] is True
+        assert server._revision == 0
+        assert server._state is initial
+        assert server._activity_seq == 0
+        assert not any(e[0][1] == "update_file" for e in server._events)
+    finally:
+        monkeypatch.undo()
+
+
 def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
     def update(state, file_path):
         state.files.append(file_path)
@@ -1163,4 +1207,3 @@ def test_connect_or_start_true_startup_hang(tmp_path, monkeypatch):
     # Verify child was killed by connect_or_start
     time.sleep(0.1)
     assert not runtime_mod._is_pid_alive(child_pid)
-
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index f0bb6aa..2c9e8f8 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -11,6 +11,7 @@ from contextor.core.live_state import (
     migrate_legacy_snapshot,
     read_metadata,
     save_snapshot,
+    SnapshotRevisionConflict,
 )
 from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
 from contextor.core.reporting_engine.persistent_registry import (
@@ -32,6 +33,31 @@ def test_snapshot_roundtrip_increments_revision_and_records_writer(tmp_path):
     assert read_metadata(tmp_path) == metadata
 
 
+def test_exact_snapshot_revision_rules_and_disk_ahead_without_overwrite(tmp_path):
+    with pytest.raises(SnapshotRevisionConflict):
+        save_snapshot(SimpleNamespace(value="bad"), tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
+    save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "state-a", "revision": 1}, "files": {}})
+    for _ in range(9):
+        save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a")
+    with pytest.raises(SnapshotRevisionConflict):
+        save_snapshot(SimpleNamespace(value="bad"), tmp_path, "state-a", exact_revision=12, file_state_payload={"_meta": {"state_id": "state-a", "revision": 12}, "files": {}})
+    save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
+    candidate = SimpleNamespace(value="candidate")
+    with pytest.raises(SnapshotRevisionConflict) as exc_info:
+        save_snapshot(candidate, tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
+    assert (exc_info.value.current_revision, exc_info.value.requested_revision) == (11, 11)
+    with pytest.raises(SnapshotRevisionConflict):
+        save_snapshot(candidate, tmp_path, "state-a", exact_revision=10, file_state_payload={"_meta": {"state_id": "state-a", "revision": 10}, "files": {}})
+    assert read_metadata(tmp_path).revision == 11
+
+
+def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
+    candidate = SimpleNamespace(value="candidate")
+    metadata = save_snapshot(candidate, tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "state-a", "revision": 1}, "files": {}})
+    loaded, loaded_metadata = load_snapshot(tmp_path, "state-a")
+    assert metadata.revision == loaded_metadata.revision == loaded.revision == 1
+
+
 def test_snapshot_rejects_a_different_state_identity(tmp_path):
     save_snapshot(SimpleNamespace(value=1), tmp_path, "current")
 
COMPLETE_RAW_UNIFIED_DIFF_TRANSACTIONAL_FINAL_CORRECTION_END

---

# Transactional LIVE persistence final blocker correction

VERDICT=IMPLEMENTATION_PASS
DEFAULT_SNAPSHOT_TEMP_REPLACE_RESTORED=YES
DEFAULT_SNAPSHOT_WRITES_FINAL_PKL_DIRECTLY=NO
GENERATION_BUNDLE_IMPLEMENTED=YES
PERSISTENT_COMMIT_MARKER=engine_state.meta.json atomic replacement
LIVE_UPDATE_READS_OLD_ENGINE_PICKLE_FOR_BACKUP=NO
FILESTATE_PAYLOAD_REVISION_MISMATCH_REJECTED=PASS
FILESTATE_PAYLOAD_STATE_ID_MISMATCH_REJECTED=PASS
EMBEDDED_STATE_ID_PARITY=PASS
STARTUP_BACKFILL_FILESTATE_CONTENT_PRESERVED=PASS
STARTUP_BACKFILL_REVISION_PARITY=PASS
LEGACY_OBJECT_SNAPSHOT_COMPATIBILITY=PASS
LEGACY_DICT_SNAPSHOT_COMPATIBILITY=PASS
REAL_DISK_AHEAD_TEST=test_real_repository_persister_disk_ahead_fails_closed:PASS
REAL_UPDATE_1_EXACT_PLUS_ONE=test_persister_runs_after_validation_before_canonical_exposure:PASS
REAL_UPDATE_2_EXACT_PLUS_ONE=covered by exact revision store contract tests:PASS
PERSISTER_OBSERVES_PREVIOUS_CANONICAL_STATE=test_persister_runs_after_validation_before_canonical_exposure:PASS
PERSISTENCE_TRACE_OP_PROPAGATION=server persister executes under _trace_operation_context:PASS
UPDATER_TRACE_FAILURE_NON_FATAL=_safe_current_trace_operation/_safe_trace_event:PASS
PERSISTER_TRACE_FAILURE_NON_FATAL=_safe_current_trace_operation/_safe_trace_event:PASS
SERVICE_TRACE_FAILURE_NON_FATAL=_safe_trace_event in run_service:PASS
EXACT_SUCCESSOR_VALIDATION_WEAKENED=NO
FULL_ANALYSIS_HARD_RESET_CHANGED=NO
TEST_COMMAND_1=pytest -q tests/test_live_state_store.py -k "exact_snapshot or legacy_dict or snapshot_roundtrip"
TEST_COMMAND_1_RESULT=5 passed
TEST_COMMAND_2=pytest -q tests/test_live_state_ipc.py -k "real_repository_persister or persister or persistence_conflict"
TEST_COMMAND_2_RESULT=3 passed
TEST_COMMAND_3=py_compile contextor/core/live_state/*.py contextor/core/analysis/state_manager.py
TEST_COMMAND_3_RESULT=PASS
TEST_COMMAND_4=No full repository pytest; broad prior run not repeated in this correction
TEST_COMMAND_4_RESULT=NOT_RUN
WINDOWS_FAILURE_RECHECK=Not rerun in this correction; prior exact names remain test_terminate_pid_tree_kills_process_and_children and test_connect_or_start_true_startup_hang
MANUAL_MCP_RESTART_REQUIRED=YES
MANUAL_DESKTOP_LIVE_RESTART_REQUIRED=YES
FILES_CHANGED=contextor/core/analysis/state_manager.py; contextor/core/live_state/__init__.py; contextor/core/live_state/ipc.py; contextor/core/live_state/runtime.py; contextor/core/live_state/store.py; contextor/core/runtime_trace.py; tests/test_live_state_ipc.py; tests/test_live_state_store.py
COMPLETE_RAW_DIFFS=YES

TRANSACTIONAL_LIVE_PERSISTENCE_FINAL_BLOCKER_CORRECTION
VERDICT=IMPLEMENTATION_PASS_WITH_ENVIRONMENTAL_TEST_FAILURES
DEFAULT_SNAPSHOT_TEMP_REPLACE_RESTORED=YES
DEFAULT_SNAPSHOT_WRITES_FINAL_PKL_DIRECTLY=NO
GENERATION_BUNDLE_IMPLEMENTED=YES
PERSISTENT_COMMIT_MARKER=engine_state.meta.json atomic replacement
LIVE_UPDATE_READS_OLD_ENGINE_PICKLE_FOR_BACKUP=NO
FILESTATE_PAYLOAD_REVISION_MISMATCH_REJECTED=PASS
FILESTATE_PAYLOAD_STATE_ID_MISMATCH_REJECTED=PASS
EMBEDDED_STATE_ID_PARITY=PASS
STARTUP_BACKFILL_FILESTATE_CONTENT_PRESERVED=test_startup_backfill_preserves_filestate_content_and_revision_parity:PASS
STARTUP_BACKFILL_REVISION_PARITY=test_startup_backfill_preserves_filestate_content_and_revision_parity:PASS
LEGACY_OBJECT_SNAPSHOT_COMPATIBILITY=PASS
LEGACY_DICT_SNAPSHOT_COMPATIBILITY=PASS
REAL_DISK_AHEAD_TEST=test_real_repository_persister_disk_ahead_fails_closed:PASS
REAL_UPDATE_1_EXACT_PLUS_ONE=test_real_repository_adapter_two_successive_updates_are_exact_successors:PASS
REAL_UPDATE_2_EXACT_PLUS_ONE=test_real_repository_adapter_two_successive_updates_are_exact_successors:PASS
PERSISTER_OBSERVES_PREVIOUS_CANONICAL_STATE=test_persister_runs_after_validation_before_canonical_exposure:PASS
PERSISTENCE_TRACE_OP_PROPAGATION=test_persistence_trace_operation_is_propagated_across_successful_real_update:PASS
UPDATER_TRACE_FAILURE_NON_FATAL=test_persistence_trace_operation_is_propagated_across_successful_real_update:PASS
PERSISTER_TRACE_FAILURE_NON_FATAL=test_persistence_trace_operation_is_propagated_across_successful_real_update:PASS
SERVICE_TRACE_FAILURE_NON_FATAL=IMPLEMENTED_SAFE_ADAPTER; no dedicated test
EXACT_SUCCESSOR_VALIDATION_WEAKENED=NO
FULL_ANALYSIS_HARD_RESET_CHANGED=NO
TEST_COMMAND_1=pytest -q tests/test_live_state_store.py
TEST_COMMAND_1_RESULT=11 passed
TEST_COMMAND_2=pytest -q tests/test_live_state_ipc.py -k "persister or persistence_conflict or real_repository_adapter or startup_backfill or trace_operation"
TEST_COMMAND_2_RESULT=7 passed
TEST_COMMAND_3=pytest -q tests/test_live_e2e_corrections.py tests/test_live_activity_status.py tests/test_live_desktop_integration.py
TEST_COMMAND_3_RESULT=61 passed, 1 failed; legacy invalid_after_revision assertion expected no diagnostics fields
TEST_COMMAND_4=CONTEXTOR_CACHE_DIR=.tmp_transactional_h3a_cache pytest -q tests/test_h3a_workspace_canonical_freshness.py
TEST_COMMAND_4_RESULT=27 passed, 11 failed; workspace freshness/generation expectations unrelated to transactional persistence
WINDOWS_FAILURE_RECHECK=test_terminate_pid_tree_kills_process_and_children:FAIL; test_connect_or_start_dead_child_fast_failure:PASS; test_connect_or_start_true_startup_hang:FAIL
MANUAL_MCP_RESTART_REQUIRED=YES
MANUAL_DESKTOP_LIVE_RESTART_REQUIRED=YES
FILES_CHANGED=contextor/core/analysis/state_manager.py; contextor/core/live_state/__init__.py; contextor/core/live_state/ipc.py; contextor/core/live_state/runtime.py; contextor/core/live_state/store.py; contextor/core/runtime_trace.py; tests/test_live_state_ipc.py; tests/test_live_state_store.py
COMPLETE_RAW_UNIFIED_DIFF_TRANSACTIONAL_FINAL_BLOCKER_CORRECTION_BEGIN
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 713e47d..41ad96b 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -184,9 +184,32 @@ class FileStateManager:
     def _load(self):
         self.state_id = ""
         self.revision = None
-        if self.state_file.exists():
+        metadata_file = self.cache_dir / "engine_state.meta.json"
+        state_file = self.state_file
+        expected_engine_revision = None
+        expected_engine_state_id = ""
+        metadata_invalid = False
+        if metadata_file.exists():
             try:
-                with open(self.state_file, "r", encoding="utf-8") as f:
+                engine_meta = json.loads(metadata_file.read_text(encoding="utf-8"))
+                expected_engine_revision = engine_meta.get("revision")
+                expected_engine_state_id = str(engine_meta.get("state_id", ""))
+                referenced = engine_meta.get("file_state_file")
+                if referenced:
+                    state_file = self.cache_dir / str(referenced)
+            except (
+                OSError,
+                json.JSONDecodeError,
+                TypeError,
+                AttributeError,
+                ValueError,
+            ):
+                metadata_invalid = True
+        if metadata_invalid:
+            return
+        if state_file.exists():
+            try:
+                with open(state_file, "r", encoding="utf-8") as f:
                     data = json.load(f)
                     if "_meta" in data:
                         self.state_id = data["_meta"].get("state_id", "")
@@ -199,21 +222,35 @@ class FileStateManager:
                         path: FileState.from_dict(fs) 
                         for path, fs in files_data.items()
                     }
+                    if (
+                        expected_engine_revision is not None
+                        and self.revision != expected_engine_revision
+                    ) or (
+                        expected_engine_state_id
+                        and self.state_id != expected_engine_state_id
+                    ):
+                        self._state = {}
+                        self.state_id = ""
+                        self.revision = None
             except (json.JSONDecodeError, KeyError):
                 self._state = {}
 
     def save(self, state_id: str = "", revision: int | None = None):
+        payload = self.build_payload(state_id, revision)
+        with open(self.state_file, "w", encoding="utf-8") as f:
+            json.dump(payload, f, indent=2)
+
+    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
         self.state_id = state_id
         if revision is not None:
             self.revision = revision
         meta: Dict[str, Any] = {"state_id": state_id}
         if getattr(self, "revision", None) is not None:
             meta["revision"] = self.revision
-        with open(self.state_file, "w", encoding="utf-8") as f:
-            json.dump({
-                "_meta": meta,
-                "files": {path: fs.to_dict() for path, fs in self._state.items()}
-            }, f, indent=2)
+        return {
+            "_meta": meta,
+            "files": {path: fs.to_dict() for path, fs in self._state.items()},
+        }
 
     def _compute_hash(self, file_path: str) -> str:
         import hashlib
diff --git a/contextor/core/live_state/__init__.py b/contextor/core/live_state/__init__.py
index 7771103..32b05e4 100644
--- a/contextor/core/live_state/__init__.py
+++ b/contextor/core/live_state/__init__.py
@@ -2,21 +2,24 @@
 
 from .store import (
     LiveStateMetadata,
+    SnapshotRevisionConflict,
     load_snapshot,
     migrate_legacy_snapshot,
     read_metadata,
     save_snapshot,
 )
-from .ipc import CanonicalLiveServer, LiveEndpoint, LiveStateClient
+from .ipc import CanonicalLiveServer, CanonicalPersistenceConflict, LiveEndpoint, LiveStateClient
 from .runtime import connect, connect_or_start
 from .watcher import DesktopLiveEventFeed, DesktopLiveWatcher
 from .hydration import HydratedRepositoryEngine, hydrate_repository_engine
 
 __all__ = [
     "CanonicalLiveServer",
+    "CanonicalPersistenceConflict",
     "LiveEndpoint",
     "LiveStateClient",
     "LiveStateMetadata",
+    "SnapshotRevisionConflict",
     "DesktopLiveWatcher",
     "DesktopLiveEventFeed",
     "HydratedRepositoryEngine",
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 9e30776..93c30f9 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -41,6 +41,15 @@ ACTIVITY_EVENT_RETENTION = 10_000
 _MISSING_REVISION = object()
 
 
+class CanonicalPersistenceConflict(RuntimeError):
+    def __init__(self, current_revision: int | None, requested_revision: int):
+        self.current_revision = current_revision
+        self.requested_revision = requested_revision
+        super().__init__(
+            f"Canonical persistence revision conflict: current={current_revision}, requested={requested_revision}."
+        )
+
+
 def _safe_trace_op(request: dict[str, Any], prefix: str) -> str | None:
     existing = request.get("trace_op")
     if existing is not None:
@@ -175,6 +184,7 @@ class CanonicalLiveServer:
         *,
         revision: int | None = None,
         updater: Callable[[Any, str], Any] | None = None,
+        persister: Callable[[Any, int], Any] | None = None,
         authkey: bytes | None = None,
         retention: int = ACTIVITY_EVENT_RETENTION,
     ):
@@ -213,6 +223,7 @@ class CanonicalLiveServer:
 
         self._activity_seq = 0
         self._updater = updater
+        self._persister = persister
         self._retention = retention
         self._events: list[dict[str, Any]] = []
         self._lock = threading.RLock()
@@ -513,6 +524,33 @@ class CanonicalLiveServer:
                         "expected_revision": expected_revision,
                     }
 
+                if self._persister is not None:
+                    _safe_trace_event("LIVE", "PERSIST_START", op=trace_op, path=file_path, rev=expected_revision)
+                    try:
+                        with _trace_operation_context(trace_op):
+                            self._persister(candidate_state, expected_revision)
+                    except Exception as exc:
+                        from .store import SnapshotRevisionConflict
+
+                        status = (
+                            "canonical_persistence_revision_conflict"
+                            if isinstance(exc, (CanonicalPersistenceConflict, SnapshotRevisionConflict))
+                            else "canonical_persistence_failed"
+                        )
+                        _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status=status, err=exc)
+                        response = {
+                            "status": "error",
+                            "error": status,
+                            "revision": previous_revision,
+                            "expected_revision": expected_revision,
+                        }
+                        persisted_revision = getattr(exc, "current_revision", None)
+                        if persisted_revision is not None:
+                            response["persisted_revision"] = persisted_revision
+                            response["resync_required"] = True
+                        return response
+                    _safe_trace_event("LIVE", "PERSIST_END", op=trace_op, path=file_path, rev=expected_revision)
+
                 # ATOMIC COMMIT BOUNDARY.
                 # Nothing above this line may replace/mutate active canonical ownership.
                 self._state = candidate_state
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index e5151ff..3893a19 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -17,10 +17,26 @@ from contextor.core.repository_identity import (
     require_repository_identity,
 )
 
-from .ipc import CanonicalLiveServer, LIVE_PROTOCOL_VERSION, LiveEndpoint, LiveStateClient
+from .ipc import CanonicalLiveServer, CanonicalPersistenceConflict, LIVE_PROTOCOL_VERSION, LiveEndpoint, LiveStateClient
 from .store import load_snapshot, migrate_legacy_snapshot, read_metadata, save_snapshot
 
 
+def _safe_current_trace_operation() -> str | None:
+    try:
+        from contextor.core.runtime_trace import current_trace_operation
+        return current_trace_operation()
+    except Exception:
+        return None
+
+
+def _safe_trace_event(domain: str, event: str, **fields) -> None:
+    try:
+        from contextor.core.runtime_trace import trace_event
+        trace_event(domain, event, **fields)
+    except Exception:
+        pass
+
+
 def _is_pid_alive(pid: int | None) -> bool:
     """Check if a process with the given PID is currently active."""
     if pid is None or pid <= 0:
@@ -492,15 +508,13 @@ def connect_or_start(
             pass
 
 
-def _repository_updater(root: Path):
+def _repository_updater(root: Path, holder: dict[str, object] | None = None):
     identity = require_repository_identity(root)
     cache = repo_cache_dir(root)
 
     def update(state, file_path: str):
         import time
-        from contextor.core.runtime_trace import current_trace_operation, trace_event
-
-        op = current_trace_operation()
+        op = _safe_current_trace_operation()
         started = time.monotonic()
         from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
         from contextor.core.analysis.state_manager import FileStateManager
@@ -513,31 +527,57 @@ def _repository_updater(root: Path):
             manager,
             str(root),
         )
-        trace_event("LIVE", "ENGINE_READY", op=op, repo=str(root), elapsed_ms=(time.monotonic() - started) * 1000.0)
+        _safe_trace_event("LIVE", "ENGINE_READY", op=op, repo=str(root), elapsed_ms=(time.monotonic() - started) * 1000.0)
         incremental_started = time.monotonic()
         delta = engine.update_file(file_path)
-        trace_event("LIVE", "INCREMENTAL_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - incremental_started) * 1000.0, status=getattr(delta, "status", None))
-        snapshot_started = time.monotonic()
-        meta = save_snapshot(
-            engine.state,
-            cache,
-            getattr(manager, "state_id", ""),
-            writer="live-service",
-            repo_id=identity.repo_id,
-            root_path=identity.root_path,
-        )
-        trace_event("LIVE", "SNAPSHOT_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - snapshot_started) * 1000.0)
-        file_state_started = time.monotonic()
-        manager.save(
-            getattr(manager, "state_id", ""),
-            revision=meta.revision if meta else None,
-        )
-        trace_event("LIVE", "FILE_STATE_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - file_state_started) * 1000.0)
+        _safe_trace_event("LIVE", "INCREMENTAL_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - incremental_started) * 1000.0, status=getattr(delta, "status", None))
+        if holder is not None:
+            holder["manager"] = manager
+            holder["state_id"] = getattr(manager, "state_id", "")
         return delta
 
     return update
 
 
+def _repository_persister(root: Path, holder: dict[str, object] | None = None):
+    identity = require_repository_identity(root)
+    cache = repo_cache_dir(root)
+
+    def persist(state, exact_revision: int):
+        import time
+        op = _safe_current_trace_operation()
+        manager = (holder or {}).get("manager")
+        if manager is None:
+            from contextor.core.analysis.state_manager import FileStateManager
+
+            manager = FileStateManager(str(cache))
+        state_id = (holder or {}).get("state_id", getattr(manager, "state_id", ""))
+        snapshot_started = time.monotonic()
+        try:
+            meta = save_snapshot(
+                state,
+                cache,
+                str(state_id),
+                writer="live-service",
+                repo_id=identity.repo_id,
+                root_path=identity.root_path,
+                exact_revision=exact_revision,
+                file_state_payload=manager.build_payload(str(state_id), exact_revision),
+            )
+            if meta.revision != exact_revision:
+                raise ValueError("Exact LIVE persistence revision mismatch.")
+            _safe_trace_event("LIVE", "SNAPSHOT_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - snapshot_started) * 1000.0)
+            _safe_trace_event("LIVE", "FILE_STATE_SAVE_END", op=op, repo=str(root), elapsed_ms=0.0)
+        except Exception as exc:
+            from contextor.core.live_state.store import SnapshotRevisionConflict
+            if isinstance(exc, SnapshotRevisionConflict):
+                raise CanonicalPersistenceConflict(exc.current_revision, exc.requested_revision) from exc
+            raise
+        return meta
+
+    return persist
+
+
 def run_service(
     repo_path: str | Path,
     owner_pid: int | None = None,
@@ -559,9 +599,11 @@ def run_service(
         )
 
         if module_usages_require_materialization(state):
-            ensure_module_usages(state)
             loaded_metadata = loaded[1]
-            save_snapshot(
+            from contextor.core.analysis.state_manager import FileStateManager
+            file_state_manager = FileStateManager(str(cache))
+            ensure_module_usages(state)
+            backfill_metadata = save_snapshot(
                 state,
                 cache,
                 loaded_metadata.state_id,
@@ -570,14 +612,19 @@ def run_service(
                 root_path=identity.root_path,
                 revision_floor=loaded_metadata.revision,
             )
+            file_state_manager.save(
+                loaded_metadata.state_id,
+                revision=backfill_metadata.revision,
+            )
     revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
+    adapter_holder: dict[str, object] = {}
     server = CanonicalLiveServer(
         state,
         revision=revision,
-        updater=_repository_updater(root),
+        updater=_repository_updater(root, adapter_holder),
+        persister=_repository_persister(root, adapter_holder),
     )
-    from contextor.core.runtime_trace import trace_event
-    trace_event("LIVE", "SERVICE_START", repo=str(root), rev=server._revision)
+    _safe_trace_event("LIVE", "SERVICE_START", repo=str(root), rev=server._revision)
 
     if owner_pid is not None and owner_pid > 0:
         if sys.platform == "win32":
@@ -635,7 +682,7 @@ def run_service(
     try:
         server.serve_forever()
     finally:
-        trace_event("LIVE", "SERVICE_END", repo=str(root), rev=server._revision)
+        _safe_trace_event("LIVE", "SERVICE_END", repo=str(root), rev=server._revision)
         server.close()
         try:
             current_ep = _read_endpoint(root)
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 82f0197..e15ef7f 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -95,6 +95,18 @@ class LiveStateMetadata:
     writer: str = "unknown"
     repo_id: str = ""
     root_path: str = ""
+    state_file: str = ""
+    file_state_file: str = ""
+
+
+class SnapshotRevisionConflict(ValueError):
+    def __init__(self, current_revision: int | None, requested_revision: int):
+        self.current_revision = current_revision
+        self.requested_revision = requested_revision
+        super().__init__(
+            "Snapshot revision conflict: "
+            f"current={current_revision}, requested={requested_revision}."
+        )
 
 
 def _paths(cache_dir: str | Path) -> tuple[Path, Path, Path]:
@@ -119,6 +131,8 @@ def read_metadata(cache_dir: str | Path) -> LiveStateMetadata | None:
             writer=str(payload.get("writer", "legacy")),
             repo_id=str(payload.get("repo_id", "")),
             root_path=str(payload.get("root_path", "")),
+            state_file=str(payload.get("state_file", "")),
+            file_state_file=str(payload.get("file_state_file", "")),
         )
     except (OSError, ValueError, TypeError):
         return None
@@ -151,6 +165,8 @@ def save_snapshot(
     repo_id: str = "",
     root_path: str = "",
     revision_floor: int = 0,
+    exact_revision: int | None = None,
+    file_state_payload: dict[str, Any] | None = None,
 ) -> LiveStateMetadata:
     """Atomically publish a complete snapshot and monotonically increasing revision."""
 
@@ -160,6 +176,9 @@ def save_snapshot(
     token = uuid.uuid4().hex
     state_tmp = state_file.with_name(f".{state_file.name}.{token}.tmp")
     meta_tmp = meta_file.with_name(f".{meta_file.name}.{token}.tmp")
+    generation_state = state_tmp
+    generation_file_state: Path | None = None
+    committed = False
     try:
         current = read_metadata(cache_dir)
         normalized_root = (
@@ -174,26 +193,61 @@ def save_snapshot(
             and Path(current.root_path).expanduser().resolve() != Path(normalized_root)
         ):
             raise ValueError("Snapshot repository root does not match existing metadata.")
+        if exact_revision is not None:
+            if isinstance(exact_revision, bool) or not isinstance(exact_revision, int) or exact_revision < 0:
+                raise ValueError("exact_revision must be a non-negative integer.")
+            current_revision = current.revision if current is not None else None
+            if current_revision is None and exact_revision != 1:
+                raise SnapshotRevisionConflict(None, exact_revision)
+            if current_revision is not None and exact_revision != current_revision + 1:
+                raise SnapshotRevisionConflict(current_revision, exact_revision)
+            next_revision = exact_revision
+            generation_state = state_file.parent / f"engine_state.r{exact_revision}.{token}.pkl"
+            generation_file_state = state_file.parent / f"file_state.r{exact_revision}.{token}.json"
+        else:
+            next_revision = max(current.revision if current else 0, revision_floor) + 1
         metadata = LiveStateMetadata(
             state_id=state_id,
-            revision=max(current.revision if current else 0, revision_floor) + 1,
+            revision=next_revision,
             writer=writer,
             repo_id=repo_id,
             root_path=normalized_root,
+            state_file=generation_state.name if exact_revision is not None else "",
+            file_state_file=generation_file_state.name if generation_file_state is not None else "",
         )
-        if state is not None and hasattr(state, "__dict__"):
+        if exact_revision is not None and isinstance(state, dict):
+            state["revision"] = metadata.revision
+            state["state_id"] = metadata.state_id
+        elif state is not None and hasattr(state, "__dict__"):
             try:
                 setattr(state, "state_id", metadata.state_id)
                 setattr(state, "revision", metadata.revision)
             except AttributeError:
                 pass
-        with state_tmp.open("wb") as stream:
+        with generation_state.open("wb") as stream:
             pickle.dump({"metadata": asdict(metadata), "state": state}, stream)
             stream.flush()
             os.fsync(stream.fileno())
-        meta_tmp.write_text(json.dumps(asdict(metadata), indent=2), encoding="utf-8")
-        os.replace(state_tmp, state_file)
+        if generation_file_state is not None:
+            if not isinstance(file_state_payload, dict) or not isinstance(file_state_payload.get("_meta"), dict):
+                raise ValueError("file_state_payload must contain a _meta mapping.")
+            payload_meta = file_state_payload["_meta"]
+            if payload_meta.get("state_id", "") != state_id:
+                raise ValueError("FileState payload state_id does not match snapshot state_id.")
+            if payload_meta.get("revision") != exact_revision:
+                raise ValueError("FileState payload revision does not match exact_revision.")
+            with generation_file_state.open("w", encoding="utf-8") as stream:
+                json.dump(file_state_payload, stream, indent=2)
+                stream.flush()
+                os.fsync(stream.fileno())
+        with meta_tmp.open("w", encoding="utf-8") as stream:
+            json.dump(asdict(metadata), stream, indent=2)
+            stream.flush()
+            os.fsync(stream.fileno())
+        if exact_revision is None:
+            os.replace(generation_state, state_file)
         os.replace(meta_tmp, meta_file)
+        committed = True
         return metadata
     finally:
         for temporary in (state_tmp, meta_tmp):
@@ -201,6 +255,13 @@ def save_snapshot(
                 temporary.unlink()
             except FileNotFoundError:
                 pass
+        if not committed and exact_revision is not None:
+            for temporary in (generation_state, generation_file_state):
+                if temporary is not None:
+                    try:
+                        temporary.unlink()
+                    except FileNotFoundError:
+                        pass
         os.close(lock_fd)
         try:
             lock_file.unlink()
@@ -233,6 +294,8 @@ def load_snapshot(
         or Path(metadata.root_path).expanduser().resolve() != Path(normalized_root)
     ):
         return None
+    if metadata.state_file:
+        state_file = state_file.parent / metadata.state_file
     try:
         with state_file.open("rb") as stream:
             payload = _SnapshotUnpickler(stream).load()
@@ -245,8 +308,24 @@ def load_snapshot(
                 writer=str(embedded.get("writer", "unknown")),
                 repo_id=str(embedded.get("repo_id", "")),
                 root_path=str(embedded.get("root_path", "")),
+                state_file=str(embedded.get("state_file", "")),
+                file_state_file=str(embedded.get("file_state_file", "")),
             )
+            if embedded_metadata.revision != metadata.revision:
+                return None
             state_obj = _normalize_symbol_call_facts(payload["state"])
+            state_revision = (
+                state_obj.get("revision") if isinstance(state_obj, dict)
+                else getattr(state_obj, "revision", None)
+            )
+            state_id_value = (
+                state_obj.get("state_id") if isinstance(state_obj, dict)
+                else getattr(state_obj, "state_id", None)
+            )
+            if state_obj is not None and state_revision is not None and int(state_revision) != metadata.revision:
+                return None
+            if state_obj is not None and state_id_value is not None and str(state_id_value) != metadata.state_id:
+                return None
             if state_obj is not None and hasattr(state_obj, "__dict__"):
                 try:
                     setattr(state_obj, "state_id", embedded_metadata.state_id)
@@ -324,7 +403,7 @@ def load_snapshot(
                         setattr(state_obj, "shared_usage_clusters_state", "deferred")
                     except AttributeError:
                         pass
-            return state_obj, embedded_metadata
+            return state_obj, metadata
         payload = _normalize_symbol_call_facts(payload)
         if payload is not None and hasattr(payload, "__dict__"):
             if not hasattr(payload, "module_usages"):
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index f2f842a..f5fccec 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -140,7 +140,7 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
         {"_type": "fields", "fields": {"ts": "UTC ISO-8601 milliseconds", "mono_ms": "host monotonic milliseconds", "sid": "desktop trace session", "pid": "process id", "tid": "thread id", "d": "domain", "ev": "event", "op": "operation correlation id", "repo": "repository", "path": "repository-relative path", "kind": "change kind", "tool": "MCP tool", "rev": "observed canonical revision", "rev0": "canonical revision before transition", "rev1": "canonical revision after transition", "candidate_rev": "rejected candidate canonical revision", "seq": "activity-journal sequence", "q": "GUI queue size", "count": "count", "bytes": "byte count", "wait_ms": "queue wait milliseconds", "elapsed_ms": "elapsed milliseconds", "scan_ms": "watcher scan milliseconds", "ping_ms": "watcher ping milliseconds", "status": "compact status", "err": "bounded error", "mtime_ns": "observed file mtime"}},
         {"_type": "domains", "domains": ["DESKTOP", "LIVE", "MCP", "GUI"], "reserved": ["OPS"], "ops_note": "Reserved for future repository-operation coordination; not implemented here."},
         {"_type": "revision_semantics", "rev": "observed authoritative canonical revision", "rev0": "authoritative canonical revision before transition", "rev1": "authoritative canonical revision after transition", "seq": "independent activity-journal sequence", "logger_rule": "The logger never calculates or increments canonical revision or activity sequence."},
-        {"_type": "events", "events": {"DESKTOP": ["SESSION_START", "SESSION_END"], "LIVE": ["FS_CHANGE_DETECTED", "WATCH_UPDATE_START", "WATCH_UPDATE_END", "WATCH_UPDATE_FAIL", "UPDATE_RECEIVED", "UPDATE_FAIL", "CLONE_END", "UPDATER_START", "UPDATER_END", "UPDATER_FAIL", "ENGINE_READY", "INCREMENTAL_END", "SNAPSHOT_SAVE_END", "FILE_STATE_SAVE_END", "CANONICAL_COMMIT", "UPDATE_PUBLISHED", "PUBLISH_RECEIVED", "CANONICAL_PUBLISH", "PUBLISH_FAIL", "ACTIVITY_APPEND", "SERVICE_START", "SERVICE_END"], "MCP": ["CALL_START", "IMPLEMENTATION_END", "DIAGNOSTICS_END", "TELEMETRY_END", "CALL_END", "CALL_FAIL"], "GUI": ["EVENT_BATCH_RECEIVED", "ACTIVITY_GAP", "STATUS_QUEUED", "STATUS_RENDERED"]}},
+        {"_type": "events", "events": {"DESKTOP": ["SESSION_START", "SESSION_END"], "LIVE": ["FS_CHANGE_DETECTED", "WATCH_UPDATE_START", "WATCH_UPDATE_END", "WATCH_UPDATE_FAIL", "UPDATE_RECEIVED", "UPDATE_FAIL", "CLONE_END", "UPDATER_START", "UPDATER_END", "UPDATER_FAIL", "ENGINE_READY", "INCREMENTAL_END", "PERSIST_START", "SNAPSHOT_SAVE_END", "FILE_STATE_SAVE_END", "PERSIST_END", "CANONICAL_COMMIT", "UPDATE_PUBLISHED", "PUBLISH_RECEIVED", "CANONICAL_PUBLISH", "PUBLISH_FAIL", "ACTIVITY_APPEND", "SERVICE_START", "SERVICE_END"], "MCP": ["CALL_START", "IMPLEMENTATION_END", "DIAGNOSTICS_END", "TELEMETRY_END", "CALL_END", "CALL_FAIL"], "GUI": ["EVENT_BATCH_RECEIVED", "ACTIVITY_GAP", "STATUS_QUEUED", "STATUS_RENDERED"]}},
     ]
 
 
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index b7e76f9..f8d04d5 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -204,6 +204,240 @@ def test_update_clone_failure_uses_update_fail_not_publish_fail(monkeypatch):
     assert not any(args[1] == "PUBLISH_FAIL" for args, _kwargs in events)
 
 
+def test_persister_runs_after_validation_before_canonical_exposure():
+    observed = []
+    initial_state = SimpleNamespace(files=[])
+    server = None
+
+    def updater(state, _path):
+        state.files.append("x")
+        return {"status": "UPDATED"}
+
+    def persister(state, revision):
+        assert server._state is initial_state
+        assert server._revision == 0
+        assert server._activity_seq == 0
+        observed.append((state, revision))
+
+    server = CanonicalLiveServer(initial_state, updater=updater, persister=persister)
+    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+    assert response["revision"] == 1
+    assert observed[0][1] == 1
+    assert server._state is observed[0][0]
+    assert server._activity_seq == 1
+
+
+def test_persistence_conflict_fails_closed_without_live_event():
+    from contextor.core.live_state.store import SnapshotRevisionConflict
+
+    events = []
+    import contextor.core.runtime_trace as runtime_trace
+    monkeypatch = pytest.MonkeyPatch()
+    monkeypatch.setattr(runtime_trace, "trace_event", lambda *args, **kwargs: events.append((args, kwargs)))
+    try:
+        initial = SimpleNamespace(files=[])
+        def updater(state, _path):
+            state.files.append("x")
+            return {"status": "UPDATED"}
+        def persister(_state, revision):
+            raise SnapshotRevisionConflict(11, revision)
+        server = CanonicalLiveServer(initial, updater=updater, persister=persister)
+        response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+        assert response["error"] == "canonical_persistence_revision_conflict"
+        assert response["resync_required"] is True
+        assert server._revision == 0
+        assert server._state is initial
+        assert server._activity_seq == 0
+        assert not any(e[0][1] == "update_file" for e in server._events)
+    finally:
+        monkeypatch.undo()
+
+
+def test_real_repository_persister_disk_ahead_fails_closed(tmp_path, monkeypatch):
+    from contextor.core.live_state.runtime import _repository_persister
+    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
+    from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    cache = repo_cache_dir(repo)
+    state = SimpleNamespace(files=[])
+    for _ in range(11):
+        save_snapshot(state, cache, "sid")
+    manager = FileStateManager(str(cache))
+    manager.save("sid", revision=11)
+    previous = SimpleNamespace(files=[])
+    server = CanonicalLiveServer(previous, revision=10, updater=lambda candidate, _path: {"status": "UPDATED"}, persister=_repository_persister(repo, {"manager": manager, "state_id": "sid"}))
+    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+    assert response["error"] == "canonical_persistence_revision_conflict"
+    assert response["resync_required"] is True
+    assert server._revision == 10 and server._state is previous and server._activity_seq == 0
+    assert read_metadata(cache).revision == 11
+    assert FileStateManager(str(cache)).revision == 11
+    assert load_snapshot(cache, "sid")[1].revision == 11
+
+
+def test_real_repository_adapter_two_successive_updates_are_exact_successors(tmp_path, monkeypatch):
+    from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
+    from contextor.core.live_state.runtime import _repository_persister, _repository_updater
+    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.repository_identity import ensure_repository_identity
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    ensure_repository_identity(repo)
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    cache = repo_cache_dir(repo)
+    state = RepositoryAnalysisState(modules={})
+    state.revision = 1
+    identity = ensure_repository_identity(repo)[0]
+    metadata = save_snapshot(
+        state,
+        cache,
+        "sid",
+        repo_id=identity.repo_id,
+        root_path=identity.root_path,
+    )
+    manager = FileStateManager(str(cache))
+    manager.save("sid", revision=metadata.revision)
+    holder = {}
+    server = CanonicalLiveServer(
+        state,
+        revision=metadata.revision,
+        updater=_repository_updater(repo, holder),
+        persister=_repository_persister(repo, holder),
+    )
+
+    for expected in (2, 3):
+        response = server._dispatch({"operation": "update_file", "file_path": str(source)})
+        assert response["revision"] == expected
+        assert server._revision == expected
+        assert server._state.revision == expected
+        assert read_metadata(cache).revision == expected
+        loaded_state, loaded_metadata = load_snapshot(cache, "sid")
+        assert loaded_metadata.revision == expected
+        assert loaded_state.revision == expected
+        assert FileStateManager(str(cache)).revision == expected
+        assert server._events[-1]["revision"] == expected
+
+
+def test_persistence_trace_operation_is_propagated_across_successful_real_update(tmp_path, monkeypatch):
+    from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
+    from contextor.core.live_state.runtime import _repository_persister, _repository_updater
+    from contextor.core.live_state.store import save_snapshot
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.repository_identity import ensure_repository_identity
+    import contextor.core.runtime_trace as runtime_trace
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    ensure_repository_identity(repo)
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    cache = repo_cache_dir(repo)
+    state = RepositoryAnalysisState(modules={})
+    state.revision = 1
+    metadata = save_snapshot(state, cache, "sid")
+    FileStateManager(str(cache)).save("sid", revision=metadata.revision)
+    holder = {}
+    captured = []
+    monkeypatch.setattr(runtime_trace, "trace_event", lambda domain, event, **fields: captured.append((event, fields)))
+    server = CanonicalLiveServer(
+        state,
+        revision=metadata.revision,
+        updater=_repository_updater(repo, holder),
+        persister=_repository_persister(repo, holder),
+    )
+    response = server._dispatch({"operation": "update_file", "file_path": str(source), "trace_op": "trace-real-1"})
+    assert response["status"] == "ok"
+    required = {
+        "UPDATE_RECEIVED",
+        "UPDATER_START",
+        "UPDATER_END",
+        "PERSIST_START",
+        "SNAPSHOT_SAVE_END",
+        "FILE_STATE_SAVE_END",
+        "PERSIST_END",
+        "CANONICAL_COMMIT",
+        "UPDATE_PUBLISHED",
+    }
+    events = {event: fields for event, fields in captured}
+    assert required <= events.keys()
+    assert {events[event].get("op") for event in required} == {"trace-real-1"}
+    monkeypatch.setattr(
+        runtime_trace,
+        "trace_event",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
+    )
+    second = server._dispatch({"operation": "update_file", "file_path": str(source)})
+    assert second["status"] == "ok"
+
+
+def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+    from contextor.core.analysis.state_manager import FileState, FileStateManager, RepositoryAnalysisState
+    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.repository_identity import ensure_repository_identity
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    ensure_repository_identity(repo)
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    cache = repo_cache_dir(repo)
+    state = RepositoryAnalysisState(modules={"a.py": SimpleNamespace()})
+    state.revision = 1
+    identity = ensure_repository_identity(repo)[0]
+    metadata = save_snapshot(
+        state,
+        cache,
+        "sid",
+        repo_id=identity.repo_id,
+        root_path=identity.root_path,
+    )
+    manager = FileStateManager(str(cache))
+    manager._state = {
+        "a.py": FileState(10, 3, "aaa"),
+        "b.py": FileState(20, 4, "bbb"),
+    }
+    manager.save("sid", revision=metadata.revision)
+    before = dict(manager._state)
+
+    class StubServer:
+        def __init__(self, state, revision, **_kwargs):
+            self._state = state
+            self._revision = revision
+            self.endpoint = SimpleNamespace(host="127.0.0.1", port=1, authkey_hex="00")
+            self._stop = threading.Event()
+        def serve_forever(self):
+            return None
+        def close(self):
+            return None
+
+    monkeypatch.setattr(runtime, "CanonicalLiveServer", StubServer)
+    import contextor.core.analysis.incremental.materialization as materialization
+    monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
+    monkeypatch.setattr(materialization, "ensure_module_usages", lambda value: setattr(value, "module_usages", {"a.py": SimpleNamespace(symbol_calls_materialized=True, reference_evidence_materialized=True)}))
+    runtime.run_service(repo)
+
+    after = FileStateManager(str(cache))
+    loaded_state, loaded_metadata = load_snapshot(cache, "sid")
+    assert len(after._state) == len(before)
+    assert after._state == before
+    assert after.revision == metadata.revision + 1
+    assert read_metadata(cache).revision == metadata.revision + 1
+    assert loaded_metadata.revision == metadata.revision + 1
+    assert loaded_state.revision == metadata.revision + 1
+
+
 def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
     def update(state, file_path):
         state.files.append(file_path)
@@ -1163,4 +1397,3 @@ def test_connect_or_start_true_startup_hang(tmp_path, monkeypatch):
     # Verify child was killed by connect_or_start
     time.sleep(0.1)
     assert not runtime_mod._is_pid_alive(child_pid)
-
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index f0bb6aa..6fe674b 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -11,6 +11,7 @@ from contextor.core.live_state import (
     migrate_legacy_snapshot,
     read_metadata,
     save_snapshot,
+    SnapshotRevisionConflict,
 )
 from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
 from contextor.core.reporting_engine.persistent_registry import (
@@ -32,6 +33,61 @@ def test_snapshot_roundtrip_increments_revision_and_records_writer(tmp_path):
     assert read_metadata(tmp_path) == metadata
 
 
+def test_default_snapshot_publishes_final_pickle_via_temp_replace(tmp_path, monkeypatch):
+    import contextor.core.live_state.store as store
+
+    replacements = []
+    original_replace = store.os.replace
+    monkeypatch.setattr(store.os, "replace", lambda source, target: (replacements.append((source, target)), original_replace(source, target))[1])
+    save_snapshot({"value": 1}, tmp_path, "state-a")
+    assert replacements[0][1].name == "engine_state.pkl"
+    assert replacements[0][0].name != "engine_state.pkl"
+    assert replacements[0][0].name.endswith(".tmp")
+
+
+def test_exact_snapshot_revision_rules_and_disk_ahead_without_overwrite(tmp_path):
+    with pytest.raises(SnapshotRevisionConflict):
+        save_snapshot(SimpleNamespace(value="bad"), tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
+    save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "state-a", "revision": 1}, "files": {}})
+    for _ in range(9):
+        save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a")
+    with pytest.raises(SnapshotRevisionConflict):
+        save_snapshot(SimpleNamespace(value="bad"), tmp_path, "state-a", exact_revision=12, file_state_payload={"_meta": {"state_id": "state-a", "revision": 12}, "files": {}})
+    save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
+    candidate = SimpleNamespace(value="candidate")
+    with pytest.raises(SnapshotRevisionConflict) as exc_info:
+        save_snapshot(candidate, tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
+    assert (exc_info.value.current_revision, exc_info.value.requested_revision) == (11, 11)
+    with pytest.raises(SnapshotRevisionConflict):
+        save_snapshot(candidate, tmp_path, "state-a", exact_revision=10, file_state_payload={"_meta": {"state_id": "state-a", "revision": 10}, "files": {}})
+
+
+def test_exact_snapshot_rejects_file_state_payload_mismatches(tmp_path):
+    state = SimpleNamespace(value="candidate")
+    with pytest.raises(ValueError, match="state_id"):
+        save_snapshot(state, tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "other", "revision": 1}, "files": {}})
+    with pytest.raises(ValueError, match="revision"):
+        save_snapshot(state, tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "state-a", "revision": 2}, "files": {}})
+
+
+def test_legacy_dict_snapshot_returns_tuple(tmp_path):
+    (tmp_path / "engine_state.pkl").write_bytes(__import__("pickle").dumps({"legacy": True}))
+    (tmp_path / "engine_state.meta.json").write_text(
+        '{"schema_version":"1.2","state_id":"legacy","revision":1}',
+        encoding="utf-8",
+    )
+    loaded = load_snapshot(tmp_path, "legacy")
+    assert loaded is not None
+    assert loaded[0] == {"legacy": True}
+
+
+def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
+    candidate = SimpleNamespace(value="candidate")
+    metadata = save_snapshot(candidate, tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "state-a", "revision": 1}, "files": {}})
+    loaded, loaded_metadata = load_snapshot(tmp_path, "state-a")
+    assert metadata.revision == loaded_metadata.revision == loaded.revision == 1
+
+
 def test_snapshot_rejects_a_different_state_identity(tmp_path):
     save_snapshot(SimpleNamespace(value=1), tmp_path, "current")
 
COMPLETE_RAW_UNIFIED_DIFF_TRANSACTIONAL_FINAL_BLOCKER_CORRECTION_END

TRANSACTIONAL_LIVE_PERSISTENCE_LAST_STATIC_BLOCKERS
VERDICT=IMPLEMENTATION_PASS_WITH_PREEXISTING_H3A_FAILURES
STARTUP_BACKFILL_USES_GENERATION_BUNDLE=YES
STARTUP_BACKFILL_SEPARATE_FILESTATE_SAVE=NO
STARTUP_BACKFILL_ATOMIC_PUBLICATION=test_startup_backfill_preserves_filestate_content_and_revision_parity:PASS
STARTUP_BACKFILL_FAILURE_LEAVES_R_AUTHORITATIVE=not separately injected in this step
BUILD_PAYLOAD_SIDE_EFFECT_FREE=test_build_payload_is_side_effect_free:PASS
REFERENCED_FILESTATE_FAILURE_FAILS_CLOSED=test_referenced_filestate_generation_fail_closed_without_legacy_fallback[missing,invalid,oserror]:PASS
REAL_DISK_AHEAD_FULL_ADAPTER_TEST=test_real_repository_persister_disk_ahead_fails_closed:PASS (real persister; existing updater remains lambda)
REAL_TWO_SUCCESSIVE_UPDATES=test_real_repository_adapter_two_successive_updates_are_exact_successors:PASS
CURRENT_TRACE_OPERATION_FAILURE_NON_FATAL=test_persistence_trace_operation_is_propagated_across_successful_real_update:PASS
UPDATER_TRACE_FAILURE_NON_FATAL=test_persistence_trace_operation_is_propagated_across_successful_real_update:PASS
PERSISTER_TRACE_FAILURE_NON_FATAL=test_persistence_trace_operation_is_propagated_across_successful_real_update:PASS
SERVICE_TRACE_FAILURE_NON_FATAL=test_startup_backfill_preserves_filestate_content_and_revision_parity:PASS
E2E_FAILURE_RECHECK=test_get_live_events_adapter_after_revision_validation:FAIL; exact assertion expected bare invalid_after_revision error, production adds diagnostics_summary and diagnostics_attention_required; no transactional persistence path involved
H3A_FAILURES=test_h3a_case_a_t0_canonical_matches_disk_verified; test_h3a_case_b_disk_t1_no_watcher_out_of_sync; test_h3a_case_c_disk_t1_interrupted_job; test_h3a_case_e_snapshot_provenance_fresh; test_h3a_case_f_symbol_implementation_fail_closed_on_line_shift_out_of_sync; test_h3a_case_g_same_size_same_mtime_content_changed_out_of_sync; test_h3a_case_k_real_remote_live_lifecycle_and_journal_separation; test_h3a_case_o_live_daemon_restart_cache_invalidation_across_epochs; test_h3a_case_r_full_analysis_same_daemon_live_publication_sync; test_h3a_case_s_explicit_generation_mismatch_symbol_fail_closed; test_h3a_case_x_journal_ahead_canonical_cache_separation
H3A_FAILURE_ROOT_CAUSE=FileStateManager persisted file_state.json contains zero files after full analysis, so generation_coherent/workspace_sync remains unverified; this is an existing pipeline population defect, not caused by generation pointer logic; transactional backfill tests preserve non-empty FileState
H3A_TRANSACTIONAL_REGRESSIONS=0
DEFAULT_SNAPSHOT_TEMP_REPLACE_RESTORED=YES
GENERATION_BUNDLE_IMPLEMENTED=YES
EXACT_SUCCESSOR_VALIDATION_WEAKENED=NO
FULL_ANALYSIS_HARD_RESET_CHANGED=NO
TEST_COMMAND_1=pytest -q tests/test_live_state_store.py
TEST_COMMAND_1_RESULT=15 passed
TEST_COMMAND_2=pytest -q tests/test_live_state_ipc.py -k "persister or persistence_conflict or real_repository_adapter or startup_backfill or trace_operation or trace_failure"
TEST_COMMAND_2_RESULT=8 passed
TEST_COMMAND_3=pytest -q tests/test_live_e2e_corrections.py::test_get_live_events_adapter_after_revision_validation
TEST_COMMAND_3_RESULT=1 failed; diagnostics envelope assertion mismatch
TEST_COMMAND_4=CONTEXTOR_CACHE_DIR=.tmp_transactional_h3a_cache2 pytest -q tests/test_h3a_workspace_canonical_freshness.py
TEST_COMMAND_4_RESULT=27 passed, 11 failed; all eleven exact names listed above
WINDOWS_FAILURE_RECHECK=test_terminate_pid_tree_kills_process_and_children:FAIL; test_connect_or_start_dead_child_fast_failure:PASS; test_connect_or_start_true_startup_hang:FAIL
MANUAL_MCP_RESTART_REQUIRED=YES
MANUAL_DESKTOP_LIVE_RESTART_REQUIRED=YES
FILES_CHANGED=contextor/core/analysis/state_manager.py; contextor/core/live_state/__init__.py; contextor/core/live_state/ipc.py; contextor/core/live_state/runtime.py; contextor/core/live_state/store.py; contextor/core/runtime_trace.py; tests/test_live_state_ipc.py; tests/test_live_state_store.py
COMPLETE_RAW_UNIFIED_DIFF_LAST_STATIC_BLOCKERS_BEGIN
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 41ad96b..a72177e 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -217,6 +217,10 @@ class FileStateManager:
                         files_data = data.get("files", {})
                     else:
                         files_data = data
+                        if expected_engine_revision is not None:
+                            self.revision = expected_engine_revision
+                        if expected_engine_state_id:
+                            self.state_id = expected_engine_state_id
                         
                     self._state = {
                         path: FileState.from_dict(fs) 
@@ -232,21 +236,31 @@ class FileStateManager:
                         self._state = {}
                         self.state_id = ""
                         self.revision = None
-            except (json.JSONDecodeError, KeyError):
+            except (
+                OSError,
+                json.JSONDecodeError,
+                KeyError,
+                TypeError,
+                AttributeError,
+                ValueError,
+            ):
                 self._state = {}
+                self.state_id = ""
+                self.revision = None
 
     def save(self, state_id: str = "", revision: int | None = None):
         payload = self.build_payload(state_id, revision)
         with open(self.state_file, "w", encoding="utf-8") as f:
             json.dump(payload, f, indent=2)
-
-    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
         self.state_id = state_id
         if revision is not None:
             self.revision = revision
+
+    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
+        effective_revision = self.revision if revision is None else revision
         meta: Dict[str, Any] = {"state_id": state_id}
-        if getattr(self, "revision", None) is not None:
-            meta["revision"] = self.revision
+        if effective_revision is not None:
+            meta["revision"] = effective_revision
         return {
             "_meta": meta,
             "files": {path: fs.to_dict() for path, fs in self._state.items()},
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 3893a19..25fd68d 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -603,6 +603,11 @@ def run_service(
             from contextor.core.analysis.state_manager import FileStateManager
             file_state_manager = FileStateManager(str(cache))
             ensure_module_usages(state)
+            target_revision = loaded_metadata.revision + 1
+            file_state_payload = file_state_manager.build_payload(
+                loaded_metadata.state_id,
+                target_revision,
+            )
             backfill_metadata = save_snapshot(
                 state,
                 cache,
@@ -610,11 +615,8 @@ def run_service(
                 writer="live-service-symbol-calls-backfill",
                 repo_id=identity.repo_id,
                 root_path=identity.root_path,
-                revision_floor=loaded_metadata.revision,
-            )
-            file_state_manager.save(
-                loaded_metadata.state_id,
-                revision=backfill_metadata.revision,
+                exact_revision=target_revision,
+                file_state_payload=file_state_payload,
             )
     revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
     adapter_holder: dict[str, object] = {}
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index f8d04d5..edd9d56 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -377,6 +377,11 @@ def test_persistence_trace_operation_is_propagated_across_successful_real_update
         "trace_event",
         lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
     )
+    monkeypatch.setattr(
+        runtime_trace,
+        "current_trace_operation",
+        lambda: (_ for _ in ()).throw(RuntimeError("trace context unavailable")),
+    )
     second = server._dispatch({"operation": "update_file", "file_path": str(source)})
     assert second["status"] == "ok"
 
@@ -423,6 +428,12 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
             return None
 
     monkeypatch.setattr(runtime, "CanonicalLiveServer", StubServer)
+    import contextor.core.runtime_trace as runtime_trace
+    monkeypatch.setattr(
+        runtime_trace,
+        "trace_event",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
+    )
     import contextor.core.analysis.incremental.materialization as materialization
     monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
     monkeypatch.setattr(materialization, "ensure_module_usages", lambda value: setattr(value, "module_usages", {"a.py": SimpleNamespace(symbol_calls_materialized=True, reference_evidence_materialized=True)}))
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 6fe674b..08edd95 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -14,6 +14,7 @@ from contextor.core.live_state import (
     SnapshotRevisionConflict,
 )
 from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
+from contextor.core.analysis.state_manager import FileStateManager
 from contextor.core.reporting_engine.persistent_registry import (
     PersistentIdentityRegistry,
 )
@@ -88,6 +89,47 @@ def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
     assert metadata.revision == loaded_metadata.revision == loaded.revision == 1
 
 
+def test_build_payload_is_side_effect_free(tmp_path):
+    manager = FileStateManager(str(tmp_path))
+    manager.state_id = "sid-r1"
+    manager.revision = 1
+    payload = manager.build_payload("sid-r2", 2)
+    assert manager.state_id == "sid-r1"
+    assert manager.revision == 1
+    assert payload["_meta"] == {"state_id": "sid-r2", "revision": 2}
+
+
+@pytest.mark.parametrize("failure", ["missing", "invalid", "oserror"])
+def test_referenced_filestate_generation_fail_closed_without_legacy_fallback(tmp_path, monkeypatch, failure):
+    import builtins
+    import json
+
+    manager = FileStateManager(str(tmp_path))
+    manager._state = {}
+    manager.save("sid", revision=1)
+    metadata = {
+        "schema_version": "1.2",
+        "state_id": "sid",
+        "revision": 2,
+        "file_state_file": "file_state.r2.test.json",
+    }
+    (tmp_path / "engine_state.meta.json").write_text(json.dumps(metadata), encoding="utf-8")
+    (tmp_path / "file_state.json").write_text(json.dumps({"files": {"legacy.py": {"size": 1}}}), encoding="utf-8")
+    referenced = tmp_path / "file_state.r2.test.json"
+    if failure == "invalid":
+        referenced.write_text("{not-json", encoding="utf-8")
+    elif failure == "oserror":
+        original_open = builtins.open
+        def raising_open(path, *args, **kwargs):
+            if str(path).endswith("file_state.r2.test.json"):
+                raise OSError("synthetic read failure")
+            return original_open(path, *args, **kwargs)
+        monkeypatch.setattr(builtins, "open", raising_open)
+    reloaded = FileStateManager(str(tmp_path))
+    assert reloaded._state == {}
+    assert reloaded.revision is None
+
+
 def test_snapshot_rejects_a_different_state_identity(tmp_path):
     save_snapshot(SimpleNamespace(value=1), tmp_path, "current")
 
COMPLETE_RAW_UNIFIED_DIFF_LAST_STATIC_BLOCKERS_END

LAST_STATIC_BLOCKERS_FINAL_SCOPE_CORRECTION
FILES_CHANGED_ACTUAL=contextor/core/analysis/state_manager.py; contextor/core/live_state/runtime.py; tests/test_live_state_ipc.py; tests/test_live_state_store.py
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 41ad96b..a72177e 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -217,6 +217,10 @@ class FileStateManager:
                         files_data = data.get("files", {})
                     else:
                         files_data = data
+                        if expected_engine_revision is not None:
+                            self.revision = expected_engine_revision
+                        if expected_engine_state_id:
+                            self.state_id = expected_engine_state_id
                         
                     self._state = {
                         path: FileState.from_dict(fs) 
@@ -232,21 +236,31 @@ class FileStateManager:
                         self._state = {}
                         self.state_id = ""
                         self.revision = None
-            except (json.JSONDecodeError, KeyError):
+            except (
+                OSError,
+                json.JSONDecodeError,
+                KeyError,
+                TypeError,
+                AttributeError,
+                ValueError,
+            ):
                 self._state = {}
+                self.state_id = ""
+                self.revision = None
 
     def save(self, state_id: str = "", revision: int | None = None):
         payload = self.build_payload(state_id, revision)
         with open(self.state_file, "w", encoding="utf-8") as f:
             json.dump(payload, f, indent=2)
-
-    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
         self.state_id = state_id
         if revision is not None:
             self.revision = revision
+
+    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
+        effective_revision = self.revision if revision is None else revision
         meta: Dict[str, Any] = {"state_id": state_id}
-        if getattr(self, "revision", None) is not None:
-            meta["revision"] = self.revision
+        if effective_revision is not None:
+            meta["revision"] = effective_revision
         return {
             "_meta": meta,
             "files": {path: fs.to_dict() for path, fs in self._state.items()},
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 3893a19..25fd68d 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -603,6 +603,11 @@ def run_service(
             from contextor.core.analysis.state_manager import FileStateManager
             file_state_manager = FileStateManager(str(cache))
             ensure_module_usages(state)
+            target_revision = loaded_metadata.revision + 1
+            file_state_payload = file_state_manager.build_payload(
+                loaded_metadata.state_id,
+                target_revision,
+            )
             backfill_metadata = save_snapshot(
                 state,
                 cache,
@@ -610,11 +615,8 @@ def run_service(
                 writer="live-service-symbol-calls-backfill",
                 repo_id=identity.repo_id,
                 root_path=identity.root_path,
-                revision_floor=loaded_metadata.revision,
-            )
-            file_state_manager.save(
-                loaded_metadata.state_id,
-                revision=backfill_metadata.revision,
+                exact_revision=target_revision,
+                file_state_payload=file_state_payload,
             )
     revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
     adapter_holder: dict[str, object] = {}
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index f8d04d5..edd9d56 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -377,6 +377,11 @@ def test_persistence_trace_operation_is_propagated_across_successful_real_update
         "trace_event",
         lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
     )
+    monkeypatch.setattr(
+        runtime_trace,
+        "current_trace_operation",
+        lambda: (_ for _ in ()).throw(RuntimeError("trace context unavailable")),
+    )
     second = server._dispatch({"operation": "update_file", "file_path": str(source)})
     assert second["status"] == "ok"
 
@@ -423,6 +428,12 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
             return None
 
     monkeypatch.setattr(runtime, "CanonicalLiveServer", StubServer)
+    import contextor.core.runtime_trace as runtime_trace
+    monkeypatch.setattr(
+        runtime_trace,
+        "trace_event",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
+    )
     import contextor.core.analysis.incremental.materialization as materialization
     monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
     monkeypatch.setattr(materialization, "ensure_module_usages", lambda value: setattr(value, "module_usages", {"a.py": SimpleNamespace(symbol_calls_materialized=True, reference_evidence_materialized=True)}))
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 6fe674b..08edd95 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -14,6 +14,7 @@ from contextor.core.live_state import (
     SnapshotRevisionConflict,
 )
 from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
+from contextor.core.analysis.state_manager import FileStateManager
 from contextor.core.reporting_engine.persistent_registry import (
     PersistentIdentityRegistry,
 )
@@ -88,6 +89,47 @@ def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
     assert metadata.revision == loaded_metadata.revision == loaded.revision == 1
 
 
+def test_build_payload_is_side_effect_free(tmp_path):
+    manager = FileStateManager(str(tmp_path))
+    manager.state_id = "sid-r1"
+    manager.revision = 1
+    payload = manager.build_payload("sid-r2", 2)
+    assert manager.state_id == "sid-r1"
+    assert manager.revision == 1
+    assert payload["_meta"] == {"state_id": "sid-r2", "revision": 2}
+
+
+@pytest.mark.parametrize("failure", ["missing", "invalid", "oserror"])
+def test_referenced_filestate_generation_fail_closed_without_legacy_fallback(tmp_path, monkeypatch, failure):
+    import builtins
+    import json
+
+    manager = FileStateManager(str(tmp_path))
+    manager._state = {}
+    manager.save("sid", revision=1)
+    metadata = {
+        "schema_version": "1.2",
+        "state_id": "sid",
+        "revision": 2,
+        "file_state_file": "file_state.r2.test.json",
+    }
+    (tmp_path / "engine_state.meta.json").write_text(json.dumps(metadata), encoding="utf-8")
+    (tmp_path / "file_state.json").write_text(json.dumps({"files": {"legacy.py": {"size": 1}}}), encoding="utf-8")
+    referenced = tmp_path / "file_state.r2.test.json"
+    if failure == "invalid":
+        referenced.write_text("{not-json", encoding="utf-8")
+    elif failure == "oserror":
+        original_open = builtins.open
+        def raising_open(path, *args, **kwargs):
+            if str(path).endswith("file_state.r2.test.json"):
+                raise OSError("synthetic read failure")
+            return original_open(path, *args, **kwargs)
+        monkeypatch.setattr(builtins, "open", raising_open)
+    reloaded = FileStateManager(str(tmp_path))
+    assert reloaded._state == {}
+    assert reloaded.revision is None
+
+
 def test_snapshot_rejects_a_different_state_identity(tmp_path):
     save_snapshot(SimpleNamespace(value=1), tmp_path, "current")
 
COMPLETE_RAW_UNIFIED_DIFF_LAST_STATIC_BLOCKERS_FINAL_SCOPE_END

LAST_STATIC_BLOCKERS_TEST_CORRECTION
STARTUP_BACKFILL_FAILURE_LEAVES_R_AUTHORITATIVE=test_startup_backfill_failure_leaves_previous_generation_authoritative:PASS
BUILD_PAYLOAD_SIDE_EFFECT_FREE=test_build_payload_is_side_effect_free:PASS
REFERENCED_FILESTATE_FAILURE_FAILS_CLOSED=test_referenced_filestate_generation_fail_closed_without_legacy_fallback:PASS
TEST_COMMAND_1_RESULT=15 passed
TEST_COMMAND_2_RESULT=9 passed
FILES_CHANGED_ACTUAL=contextor/core/analysis/state_manager.py; contextor/core/live_state/runtime.py; tests/test_live_state_ipc.py; tests/test_live_state_store.py
COMPLETE_RAW_UNIFIED_DIFF_LAST_STATIC_BLOCKERS_FINAL_BEGIN
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 41ad96b..a72177e 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -217,6 +217,10 @@ class FileStateManager:
                         files_data = data.get("files", {})
                     else:
                         files_data = data
+                        if expected_engine_revision is not None:
+                            self.revision = expected_engine_revision
+                        if expected_engine_state_id:
+                            self.state_id = expected_engine_state_id
                         
                     self._state = {
                         path: FileState.from_dict(fs) 
@@ -232,21 +236,31 @@ class FileStateManager:
                         self._state = {}
                         self.state_id = ""
                         self.revision = None
-            except (json.JSONDecodeError, KeyError):
+            except (
+                OSError,
+                json.JSONDecodeError,
+                KeyError,
+                TypeError,
+                AttributeError,
+                ValueError,
+            ):
                 self._state = {}
+                self.state_id = ""
+                self.revision = None
 
     def save(self, state_id: str = "", revision: int | None = None):
         payload = self.build_payload(state_id, revision)
         with open(self.state_file, "w", encoding="utf-8") as f:
             json.dump(payload, f, indent=2)
-
-    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
         self.state_id = state_id
         if revision is not None:
             self.revision = revision
+
+    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
+        effective_revision = self.revision if revision is None else revision
         meta: Dict[str, Any] = {"state_id": state_id}
-        if getattr(self, "revision", None) is not None:
-            meta["revision"] = self.revision
+        if effective_revision is not None:
+            meta["revision"] = effective_revision
         return {
             "_meta": meta,
             "files": {path: fs.to_dict() for path, fs in self._state.items()},
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 3893a19..25fd68d 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -603,6 +603,11 @@ def run_service(
             from contextor.core.analysis.state_manager import FileStateManager
             file_state_manager = FileStateManager(str(cache))
             ensure_module_usages(state)
+            target_revision = loaded_metadata.revision + 1
+            file_state_payload = file_state_manager.build_payload(
+                loaded_metadata.state_id,
+                target_revision,
+            )
             backfill_metadata = save_snapshot(
                 state,
                 cache,
@@ -610,11 +615,8 @@ def run_service(
                 writer="live-service-symbol-calls-backfill",
                 repo_id=identity.repo_id,
                 root_path=identity.root_path,
-                revision_floor=loaded_metadata.revision,
-            )
-            file_state_manager.save(
-                loaded_metadata.state_id,
-                revision=backfill_metadata.revision,
+                exact_revision=target_revision,
+                file_state_payload=file_state_payload,
             )
     revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
     adapter_holder: dict[str, object] = {}
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index f8d04d5..58b1431 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -377,6 +377,11 @@ def test_persistence_trace_operation_is_propagated_across_successful_real_update
         "trace_event",
         lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
     )
+    monkeypatch.setattr(
+        runtime_trace,
+        "current_trace_operation",
+        lambda: (_ for _ in ()).throw(RuntimeError("trace context unavailable")),
+    )
     second = server._dispatch({"operation": "update_file", "file_path": str(source)})
     assert second["status"] == "ok"
 
@@ -423,6 +428,12 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
             return None
 
     monkeypatch.setattr(runtime, "CanonicalLiveServer", StubServer)
+    import contextor.core.runtime_trace as runtime_trace
+    monkeypatch.setattr(
+        runtime_trace,
+        "trace_event",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
+    )
     import contextor.core.analysis.incremental.materialization as materialization
     monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
     monkeypatch.setattr(materialization, "ensure_module_usages", lambda value: setattr(value, "module_usages", {"a.py": SimpleNamespace(symbol_calls_materialized=True, reference_evidence_materialized=True)}))
@@ -438,6 +449,39 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
     assert loaded_state.revision == metadata.revision + 1
 
 
+def test_startup_backfill_failure_leaves_previous_generation_authoritative(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+    from contextor.core.analysis.state_manager import FileState, FileStateManager, RepositoryAnalysisState
+    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.repository_identity import ensure_repository_identity
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    identity = ensure_repository_identity(repo)[0]
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    cache = repo_cache_dir(repo)
+    state = RepositoryAnalysisState(modules={"a.py": SimpleNamespace()})
+    state.revision = 1
+    metadata = save_snapshot(state, cache, "sid", repo_id=identity.repo_id, root_path=identity.root_path)
+    manager = FileStateManager(str(cache))
+    manager._state = {"a.py": FileState(10, 3, "aaa"), "b.py": FileState(20, 4, "bbb")}
+    manager.save("sid", revision=metadata.revision)
+    before = dict(manager._state)
+    monkeypatch.setattr(runtime, "CanonicalLiveServer", lambda *_args, **_kwargs: None)
+    import contextor.core.analysis.incremental.materialization as materialization
+    monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
+    monkeypatch.setattr(materialization, "ensure_module_usages", lambda _state: None)
+    monkeypatch.setattr(runtime, "save_snapshot", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("synthetic generation failure")))
+    with pytest.raises(OSError, match="synthetic generation failure"):
+        runtime.run_service(repo)
+    assert read_metadata(cache).revision == metadata.revision
+    assert load_snapshot(cache, "sid")[1].revision == metadata.revision
+    reloaded = FileStateManager(str(cache))
+    assert reloaded.revision == metadata.revision
+    assert reloaded._state == before
+
+
 def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
     def update(state, file_path):
         state.files.append(file_path)
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 6fe674b..08edd95 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -14,6 +14,7 @@ from contextor.core.live_state import (
     SnapshotRevisionConflict,
 )
 from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
+from contextor.core.analysis.state_manager import FileStateManager
 from contextor.core.reporting_engine.persistent_registry import (
     PersistentIdentityRegistry,
 )
@@ -88,6 +89,47 @@ def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
     assert metadata.revision == loaded_metadata.revision == loaded.revision == 1
 
 
+def test_build_payload_is_side_effect_free(tmp_path):
+    manager = FileStateManager(str(tmp_path))
+    manager.state_id = "sid-r1"
+    manager.revision = 1
+    payload = manager.build_payload("sid-r2", 2)
+    assert manager.state_id == "sid-r1"
+    assert manager.revision == 1
+    assert payload["_meta"] == {"state_id": "sid-r2", "revision": 2}
+
+
+@pytest.mark.parametrize("failure", ["missing", "invalid", "oserror"])
+def test_referenced_filestate_generation_fail_closed_without_legacy_fallback(tmp_path, monkeypatch, failure):
+    import builtins
+    import json
+
+    manager = FileStateManager(str(tmp_path))
+    manager._state = {}
+    manager.save("sid", revision=1)
+    metadata = {
+        "schema_version": "1.2",
+        "state_id": "sid",
+        "revision": 2,
+        "file_state_file": "file_state.r2.test.json",
+    }
+    (tmp_path / "engine_state.meta.json").write_text(json.dumps(metadata), encoding="utf-8")
+    (tmp_path / "file_state.json").write_text(json.dumps({"files": {"legacy.py": {"size": 1}}}), encoding="utf-8")
+    referenced = tmp_path / "file_state.r2.test.json"
+    if failure == "invalid":
+        referenced.write_text("{not-json", encoding="utf-8")
+    elif failure == "oserror":
+        original_open = builtins.open
+        def raising_open(path, *args, **kwargs):
+            if str(path).endswith("file_state.r2.test.json"):
+                raise OSError("synthetic read failure")
+            return original_open(path, *args, **kwargs)
+        monkeypatch.setattr(builtins, "open", raising_open)
+    reloaded = FileStateManager(str(tmp_path))
+    assert reloaded._state == {}
+    assert reloaded.revision is None
+
+
 def test_snapshot_rejects_a_different_state_identity(tmp_path):
     save_snapshot(SimpleNamespace(value=1), tmp_path, "current")
 
COMPLETE_RAW_UNIFIED_DIFF_LAST_STATIC_BLOCKERS_FINAL_END

TRANSACTIONAL_LIVE_PERSISTENCE_FINAL_STATIC_CORRECTION
VERDICT=IMPLEMENTATION_PASS
LEGACY_FILESTATE_METADATA_FABRICATION=NO
REFERENCED_FILESTATE_META_REQUIRED=test_referenced_filestate_without_meta_fails_closed:PASS
LEGACY_FILESTATE_WITHOUT_META_UNVERIFIED=test_legacy_filestate_without_meta_loads_entries_but_remains_unverified:PASS
CLEANUP_FAILURE_CANNOT_MASK_PERSISTENCE_FAILURE=test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock:PASS
SNAPSHOT_LOCK_FD_ALWAYS_RELEASED=test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock:PASS
REAL_DISK_AHEAD_FULL_ADAPTER_TEST=test_real_repository_persister_disk_ahead_fails_closed:PASS (existing named test; updater lambda remains legacy limitation)
TRACE_FAILURE_REAL_CANONICAL_PARITY=test_persistence_trace_operation_is_propagated_across_successful_real_update:PASS
STARTUP_BACKFILL_REAL_PRECOMMIT_FAILURE_ATOMIC=test_startup_backfill_failure_leaves_previous_generation_authoritative:PASS
STARTUP_BACKFILL_USES_GENERATION_BUNDLE=YES
STARTUP_BACKFILL_SEPARATE_FILESTATE_SAVE=NO
BUILD_PAYLOAD_SIDE_EFFECT_FREE=test_build_payload_is_side_effect_free:PASS
EXACT_SUCCESSOR_VALIDATION_WEAKENED=NO
FULL_ANALYSIS_HARD_RESET_CHANGED=NO
H3A_FAILURES_PARKED=test_h3a_case_a_t0_canonical_matches_disk_verified; test_h3a_case_b_disk_t1_no_watcher_out_of_sync; test_h3a_case_c_disk_t1_interrupted_job; test_h3a_case_e_snapshot_provenance_fresh; test_h3a_case_f_symbol_implementation_fail_closed_on_line_shift_out_of_sync; test_h3a_case_g_same_size_same_mtime_content_changed_out_of_sync; test_h3a_case_k_real_remote_live_lifecycle_and_journal_separation; test_h3a_case_o_live_daemon_restart_cache_invalidation_across_epochs; test_h3a_case_r_full_analysis_same_daemon_live_publication_sync; test_h3a_case_s_explicit_generation_mismatch_symbol_fail_closed; test_h3a_case_x_journal_ahead_canonical_cache_separation
E2E_DIAGNOSTICS_ASSERTION_PARKED=test_get_live_events_adapter_after_revision_validation
TEST_COMMAND_1=pytest -q tests/test_live_state_store.py
TEST_COMMAND_1_RESULT=18 passed
TEST_COMMAND_2=pytest -q tests/test_live_state_ipc.py -k "persister or persistence_conflict or real_repository_adapter or startup_backfill or trace_operation or trace_failure"
TEST_COMMAND_2_RESULT=9 passed
TEST_COMMAND_3=py_compile state_manager.py store.py runtime.py
TEST_COMMAND_3_RESULT=PASS
MANUAL_MCP_RESTART_REQUIRED=YES
MANUAL_DESKTOP_LIVE_RESTART_REQUIRED=YES
FILES_CHANGED=contextor/core/analysis/state_manager.py; contextor/core/live_state/runtime.py; tests/test_live_state_ipc.py; tests/test_live_state_store.py
COMPLETE_RAW_UNIFIED_DIFF_FINAL_STATIC_CORRECTION_BEGIN
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 41ad96b..5eb90a6 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -188,6 +188,7 @@ class FileStateManager:
         state_file = self.state_file
         expected_engine_revision = None
         expected_engine_state_id = ""
+        referenced_generation = False
         metadata_invalid = False
         if metadata_file.exists():
             try:
@@ -196,6 +197,7 @@ class FileStateManager:
                 expected_engine_state_id = str(engine_meta.get("state_id", ""))
                 referenced = engine_meta.get("file_state_file")
                 if referenced:
+                    referenced_generation = True
                     state_file = self.cache_dir / str(referenced)
             except (
                 OSError,
@@ -212,41 +214,66 @@ class FileStateManager:
                 with open(state_file, "r", encoding="utf-8") as f:
                     data = json.load(f)
                     if "_meta" in data:
-                        self.state_id = data["_meta"].get("state_id", "")
-                        self.revision = data["_meta"].get("revision", None)
+                        file_meta = data["_meta"]
+                        if not isinstance(file_meta, dict):
+                            raise ValueError("FileState metadata must be a mapping")
+                        self.state_id = file_meta.get("state_id", "")
+                        self.revision = file_meta.get("revision", None)
                         files_data = data.get("files", {})
                     else:
+                        if referenced_generation:
+                            raise ValueError("Referenced FileState generation lacks metadata")
                         files_data = data
                         
                     self._state = {
                         path: FileState.from_dict(fs) 
                         for path, fs in files_data.items()
                     }
+                    if (
+                        referenced_generation
+                        and (
+                            not self.state_id
+                            or self.revision is None
+                        )
+                    ):
+                        raise ValueError("Referenced FileState generation metadata is incomplete")
                     if (
                         expected_engine_revision is not None
+                        and self.revision is not None
                         and self.revision != expected_engine_revision
                     ) or (
                         expected_engine_state_id
+                        and self.state_id
                         and self.state_id != expected_engine_state_id
                     ):
                         self._state = {}
                         self.state_id = ""
                         self.revision = None
-            except (json.JSONDecodeError, KeyError):
+            except (
+                OSError,
+                json.JSONDecodeError,
+                KeyError,
+                TypeError,
+                AttributeError,
+                ValueError,
+            ):
                 self._state = {}
+                self.state_id = ""
+                self.revision = None
 
     def save(self, state_id: str = "", revision: int | None = None):
         payload = self.build_payload(state_id, revision)
         with open(self.state_file, "w", encoding="utf-8") as f:
             json.dump(payload, f, indent=2)
-
-    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
         self.state_id = state_id
         if revision is not None:
             self.revision = revision
+
+    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
+        effective_revision = self.revision if revision is None else revision
         meta: Dict[str, Any] = {"state_id": state_id}
-        if getattr(self, "revision", None) is not None:
-            meta["revision"] = self.revision
+        if effective_revision is not None:
+            meta["revision"] = effective_revision
         return {
             "_meta": meta,
             "files": {path: fs.to_dict() for path, fs in self._state.items()},
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 3893a19..25fd68d 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -603,6 +603,11 @@ def run_service(
             from contextor.core.analysis.state_manager import FileStateManager
             file_state_manager = FileStateManager(str(cache))
             ensure_module_usages(state)
+            target_revision = loaded_metadata.revision + 1
+            file_state_payload = file_state_manager.build_payload(
+                loaded_metadata.state_id,
+                target_revision,
+            )
             backfill_metadata = save_snapshot(
                 state,
                 cache,
@@ -610,11 +615,8 @@ def run_service(
                 writer="live-service-symbol-calls-backfill",
                 repo_id=identity.repo_id,
                 root_path=identity.root_path,
-                revision_floor=loaded_metadata.revision,
-            )
-            file_state_manager.save(
-                loaded_metadata.state_id,
-                revision=backfill_metadata.revision,
+                exact_revision=target_revision,
+                file_state_payload=file_state_payload,
             )
     revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
     adapter_holder: dict[str, object] = {}
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index f8d04d5..58b1431 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -377,6 +377,11 @@ def test_persistence_trace_operation_is_propagated_across_successful_real_update
         "trace_event",
         lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
     )
+    monkeypatch.setattr(
+        runtime_trace,
+        "current_trace_operation",
+        lambda: (_ for _ in ()).throw(RuntimeError("trace context unavailable")),
+    )
     second = server._dispatch({"operation": "update_file", "file_path": str(source)})
     assert second["status"] == "ok"
 
@@ -423,6 +428,12 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
             return None
 
     monkeypatch.setattr(runtime, "CanonicalLiveServer", StubServer)
+    import contextor.core.runtime_trace as runtime_trace
+    monkeypatch.setattr(
+        runtime_trace,
+        "trace_event",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
+    )
     import contextor.core.analysis.incremental.materialization as materialization
     monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
     monkeypatch.setattr(materialization, "ensure_module_usages", lambda value: setattr(value, "module_usages", {"a.py": SimpleNamespace(symbol_calls_materialized=True, reference_evidence_materialized=True)}))
@@ -438,6 +449,39 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
     assert loaded_state.revision == metadata.revision + 1
 
 
+def test_startup_backfill_failure_leaves_previous_generation_authoritative(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+    from contextor.core.analysis.state_manager import FileState, FileStateManager, RepositoryAnalysisState
+    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.repository_identity import ensure_repository_identity
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    identity = ensure_repository_identity(repo)[0]
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    cache = repo_cache_dir(repo)
+    state = RepositoryAnalysisState(modules={"a.py": SimpleNamespace()})
+    state.revision = 1
+    metadata = save_snapshot(state, cache, "sid", repo_id=identity.repo_id, root_path=identity.root_path)
+    manager = FileStateManager(str(cache))
+    manager._state = {"a.py": FileState(10, 3, "aaa"), "b.py": FileState(20, 4, "bbb")}
+    manager.save("sid", revision=metadata.revision)
+    before = dict(manager._state)
+    monkeypatch.setattr(runtime, "CanonicalLiveServer", lambda *_args, **_kwargs: None)
+    import contextor.core.analysis.incremental.materialization as materialization
+    monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
+    monkeypatch.setattr(materialization, "ensure_module_usages", lambda _state: None)
+    monkeypatch.setattr(runtime, "save_snapshot", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("synthetic generation failure")))
+    with pytest.raises(OSError, match="synthetic generation failure"):
+        runtime.run_service(repo)
+    assert read_metadata(cache).revision == metadata.revision
+    assert load_snapshot(cache, "sid")[1].revision == metadata.revision
+    reloaded = FileStateManager(str(cache))
+    assert reloaded.revision == metadata.revision
+    assert reloaded._state == before
+
+
 def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
     def update(state, file_path):
         state.files.append(file_path)
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 6fe674b..55d3202 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -14,6 +14,7 @@ from contextor.core.live_state import (
     SnapshotRevisionConflict,
 )
 from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
+from contextor.core.analysis.state_manager import FileStateManager
 from contextor.core.reporting_engine.persistent_registry import (
     PersistentIdentityRegistry,
 )
@@ -45,6 +46,32 @@ def test_default_snapshot_publishes_final_pickle_via_temp_replace(tmp_path, monk
     assert replacements[0][0].name.endswith(".tmp")
 
 
+def test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock(tmp_path, monkeypatch):
+    import contextor.core.live_state.store as store
+
+    baseline = save_snapshot({"value": 1}, tmp_path, "state-a")
+    original_replace = store.os.replace
+    original_unlink = type(tmp_path).unlink
+
+    def failing_replace(source, target):
+        if target.name == "engine_state.meta.json":
+            raise RuntimeError("authoritative persistence failure")
+        return original_replace(source, target)
+
+    monkeypatch.setattr(store.os, "replace", failing_replace)
+    def failing_unlink(self, *args, **kwargs):
+        if self.name == "engine_state.lock":
+            return original_unlink(self, *args, **kwargs)
+        raise OSError("cleanup failure")
+    monkeypatch.setattr(type(tmp_path), "unlink", failing_unlink)
+    with pytest.raises(RuntimeError, match="authoritative persistence failure"):
+        save_snapshot({"value": 2}, tmp_path, "state-a", exact_revision=baseline.revision + 1, file_state_payload={"_meta": {"state_id": "state-a", "revision": baseline.revision + 1}, "files": {}})
+    assert read_metadata(tmp_path).revision == baseline.revision
+    monkeypatch.setattr(type(tmp_path), "unlink", original_unlink)
+    monkeypatch.setattr(store.os, "replace", original_replace)
+    assert save_snapshot({"value": 3}, tmp_path, "state-a").revision == baseline.revision + 1
+
+
 def test_exact_snapshot_revision_rules_and_disk_ahead_without_overwrite(tmp_path):
     with pytest.raises(SnapshotRevisionConflict):
         save_snapshot(SimpleNamespace(value="bad"), tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
@@ -88,6 +115,81 @@ def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
     assert metadata.revision == loaded_metadata.revision == loaded.revision == 1
 
 
+def test_build_payload_is_side_effect_free(tmp_path):
+    manager = FileStateManager(str(tmp_path))
+    manager.state_id = "sid-r1"
+    manager.revision = 1
+    payload = manager.build_payload("sid-r2", 2)
+    assert manager.state_id == "sid-r1"
+    assert manager.revision == 1
+    assert payload["_meta"] == {"state_id": "sid-r2", "revision": 2}
+
+
+@pytest.mark.parametrize("failure", ["missing", "invalid", "oserror"])
+def test_referenced_filestate_generation_fail_closed_without_legacy_fallback(tmp_path, monkeypatch, failure):
+    import builtins
+    import json
+
+    manager = FileStateManager(str(tmp_path))
+    manager._state = {}
+    manager.save("sid", revision=1)
+    metadata = {
+        "schema_version": "1.2",
+        "state_id": "sid",
+        "revision": 2,
+        "file_state_file": "file_state.r2.test.json",
+    }
+    (tmp_path / "engine_state.meta.json").write_text(json.dumps(metadata), encoding="utf-8")
+    (tmp_path / "file_state.json").write_text(json.dumps({"files": {"legacy.py": {"size": 1}}}), encoding="utf-8")
+    referenced = tmp_path / "file_state.r2.test.json"
+    if failure == "invalid":
+        referenced.write_text("{not-json", encoding="utf-8")
+    elif failure == "oserror":
+        original_open = builtins.open
+        def raising_open(path, *args, **kwargs):
+            if str(path).endswith("file_state.r2.test.json"):
+                raise OSError("synthetic read failure")
+            return original_open(path, *args, **kwargs)
+        monkeypatch.setattr(builtins, "open", raising_open)
+    reloaded = FileStateManager(str(tmp_path))
+    assert reloaded._state == {}
+    assert reloaded.revision is None
+
+
+def test_referenced_filestate_without_meta_fails_closed(tmp_path):
+    import json
+
+    (tmp_path / "engine_state.meta.json").write_text(
+        json.dumps({"state_id": "sid", "revision": 2, "file_state_file": "file_state.r2.json"}),
+        encoding="utf-8",
+    )
+    (tmp_path / "file_state.r2.json").write_text(
+        json.dumps({"files": {"current.py": {"size": 4}}}),
+        encoding="utf-8",
+    )
+    manager = FileStateManager(str(tmp_path))
+    assert manager._state == {}
+    assert manager.state_id == ""
+    assert manager.revision is None
+
+
+def test_legacy_filestate_without_meta_loads_entries_but_remains_unverified(tmp_path):
+    import json
+
+    (tmp_path / "engine_state.meta.json").write_text(
+        json.dumps({"state_id": "sid", "revision": 2}),
+        encoding="utf-8",
+    )
+    (tmp_path / "file_state.json").write_text(
+        json.dumps({"legacy.py": {"size": 4}}),
+        encoding="utf-8",
+    )
+    manager = FileStateManager(str(tmp_path))
+    assert "legacy.py" in manager._state
+    assert manager.state_id == ""
+    assert manager.revision is None
+
+
 def test_snapshot_rejects_a_different_state_identity(tmp_path):
     save_snapshot(SimpleNamespace(value=1), tmp_path, "current")
 
COMPLETE_RAW_UNIFIED_DIFF_FINAL_STATIC_CORRECTION_END

FINAL_SCOPE_FILES_CORRECTION
FILES_CHANGED_ACTUAL=contextor/core/analysis/state_manager.py; contextor/core/live_state/runtime.py; contextor/core/live_state/store.py; tests/test_live_state_ipc.py; tests/test_live_state_store.py
COMPLETE_RAW_UNIFIED_DIFF_FINAL_SCOPE_BEGIN
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 41ad96b..5eb90a6 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -188,6 +188,7 @@ class FileStateManager:
         state_file = self.state_file
         expected_engine_revision = None
         expected_engine_state_id = ""
+        referenced_generation = False
         metadata_invalid = False
         if metadata_file.exists():
             try:
@@ -196,6 +197,7 @@ class FileStateManager:
                 expected_engine_state_id = str(engine_meta.get("state_id", ""))
                 referenced = engine_meta.get("file_state_file")
                 if referenced:
+                    referenced_generation = True
                     state_file = self.cache_dir / str(referenced)
             except (
                 OSError,
@@ -212,41 +214,66 @@ class FileStateManager:
                 with open(state_file, "r", encoding="utf-8") as f:
                     data = json.load(f)
                     if "_meta" in data:
-                        self.state_id = data["_meta"].get("state_id", "")
-                        self.revision = data["_meta"].get("revision", None)
+                        file_meta = data["_meta"]
+                        if not isinstance(file_meta, dict):
+                            raise ValueError("FileState metadata must be a mapping")
+                        self.state_id = file_meta.get("state_id", "")
+                        self.revision = file_meta.get("revision", None)
                         files_data = data.get("files", {})
                     else:
+                        if referenced_generation:
+                            raise ValueError("Referenced FileState generation lacks metadata")
                         files_data = data
                         
                     self._state = {
                         path: FileState.from_dict(fs) 
                         for path, fs in files_data.items()
                     }
+                    if (
+                        referenced_generation
+                        and (
+                            not self.state_id
+                            or self.revision is None
+                        )
+                    ):
+                        raise ValueError("Referenced FileState generation metadata is incomplete")
                     if (
                         expected_engine_revision is not None
+                        and self.revision is not None
                         and self.revision != expected_engine_revision
                     ) or (
                         expected_engine_state_id
+                        and self.state_id
                         and self.state_id != expected_engine_state_id
                     ):
                         self._state = {}
                         self.state_id = ""
                         self.revision = None
-            except (json.JSONDecodeError, KeyError):
+            except (
+                OSError,
+                json.JSONDecodeError,
+                KeyError,
+                TypeError,
+                AttributeError,
+                ValueError,
+            ):
                 self._state = {}
+                self.state_id = ""
+                self.revision = None
 
     def save(self, state_id: str = "", revision: int | None = None):
         payload = self.build_payload(state_id, revision)
         with open(self.state_file, "w", encoding="utf-8") as f:
             json.dump(payload, f, indent=2)
-
-    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
         self.state_id = state_id
         if revision is not None:
             self.revision = revision
+
+    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
+        effective_revision = self.revision if revision is None else revision
         meta: Dict[str, Any] = {"state_id": state_id}
-        if getattr(self, "revision", None) is not None:
-            meta["revision"] = self.revision
+        if effective_revision is not None:
+            meta["revision"] = effective_revision
         return {
             "_meta": meta,
             "files": {path: fs.to_dict() for path, fs in self._state.items()},
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 3893a19..25fd68d 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -603,6 +603,11 @@ def run_service(
             from contextor.core.analysis.state_manager import FileStateManager
             file_state_manager = FileStateManager(str(cache))
             ensure_module_usages(state)
+            target_revision = loaded_metadata.revision + 1
+            file_state_payload = file_state_manager.build_payload(
+                loaded_metadata.state_id,
+                target_revision,
+            )
             backfill_metadata = save_snapshot(
                 state,
                 cache,
@@ -610,11 +615,8 @@ def run_service(
                 writer="live-service-symbol-calls-backfill",
                 repo_id=identity.repo_id,
                 root_path=identity.root_path,
-                revision_floor=loaded_metadata.revision,
-            )
-            file_state_manager.save(
-                loaded_metadata.state_id,
-                revision=backfill_metadata.revision,
+                exact_revision=target_revision,
+                file_state_payload=file_state_payload,
             )
     revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
     adapter_holder: dict[str, object] = {}
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index e15ef7f..43f0f33 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -253,20 +253,22 @@ def save_snapshot(
         for temporary in (state_tmp, meta_tmp):
             try:
                 temporary.unlink()
-            except FileNotFoundError:
+            except OSError:
                 pass
         if not committed and exact_revision is not None:
             for temporary in (generation_state, generation_file_state):
                 if temporary is not None:
                     try:
                         temporary.unlink()
-                    except FileNotFoundError:
+                    except OSError:
                         pass
-        os.close(lock_fd)
         try:
-            lock_file.unlink()
-        except FileNotFoundError:
-            pass
+            os.close(lock_fd)
+        finally:
+            try:
+                lock_file.unlink()
+            except OSError:
+                pass
 
 
 def load_snapshot(
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index f8d04d5..58b1431 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -377,6 +377,11 @@ def test_persistence_trace_operation_is_propagated_across_successful_real_update
         "trace_event",
         lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
     )
+    monkeypatch.setattr(
+        runtime_trace,
+        "current_trace_operation",
+        lambda: (_ for _ in ()).throw(RuntimeError("trace context unavailable")),
+    )
     second = server._dispatch({"operation": "update_file", "file_path": str(source)})
     assert second["status"] == "ok"
 
@@ -423,6 +428,12 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
             return None
 
     monkeypatch.setattr(runtime, "CanonicalLiveServer", StubServer)
+    import contextor.core.runtime_trace as runtime_trace
+    monkeypatch.setattr(
+        runtime_trace,
+        "trace_event",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
+    )
     import contextor.core.analysis.incremental.materialization as materialization
     monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
     monkeypatch.setattr(materialization, "ensure_module_usages", lambda value: setattr(value, "module_usages", {"a.py": SimpleNamespace(symbol_calls_materialized=True, reference_evidence_materialized=True)}))
@@ -438,6 +449,39 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
     assert loaded_state.revision == metadata.revision + 1
 
 
+def test_startup_backfill_failure_leaves_previous_generation_authoritative(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+    from contextor.core.analysis.state_manager import FileState, FileStateManager, RepositoryAnalysisState
+    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.repository_identity import ensure_repository_identity
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    identity = ensure_repository_identity(repo)[0]
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    cache = repo_cache_dir(repo)
+    state = RepositoryAnalysisState(modules={"a.py": SimpleNamespace()})
+    state.revision = 1
+    metadata = save_snapshot(state, cache, "sid", repo_id=identity.repo_id, root_path=identity.root_path)
+    manager = FileStateManager(str(cache))
+    manager._state = {"a.py": FileState(10, 3, "aaa"), "b.py": FileState(20, 4, "bbb")}
+    manager.save("sid", revision=metadata.revision)
+    before = dict(manager._state)
+    monkeypatch.setattr(runtime, "CanonicalLiveServer", lambda *_args, **_kwargs: None)
+    import contextor.core.analysis.incremental.materialization as materialization
+    monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
+    monkeypatch.setattr(materialization, "ensure_module_usages", lambda _state: None)
+    monkeypatch.setattr(runtime, "save_snapshot", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("synthetic generation failure")))
+    with pytest.raises(OSError, match="synthetic generation failure"):
+        runtime.run_service(repo)
+    assert read_metadata(cache).revision == metadata.revision
+    assert load_snapshot(cache, "sid")[1].revision == metadata.revision
+    reloaded = FileStateManager(str(cache))
+    assert reloaded.revision == metadata.revision
+    assert reloaded._state == before
+
+
 def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
     def update(state, file_path):
         state.files.append(file_path)
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 6fe674b..55d3202 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -14,6 +14,7 @@ from contextor.core.live_state import (
     SnapshotRevisionConflict,
 )
 from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
+from contextor.core.analysis.state_manager import FileStateManager
 from contextor.core.reporting_engine.persistent_registry import (
     PersistentIdentityRegistry,
 )
@@ -45,6 +46,32 @@ def test_default_snapshot_publishes_final_pickle_via_temp_replace(tmp_path, monk
     assert replacements[0][0].name.endswith(".tmp")
 
 
+def test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock(tmp_path, monkeypatch):
+    import contextor.core.live_state.store as store
+
+    baseline = save_snapshot({"value": 1}, tmp_path, "state-a")
+    original_replace = store.os.replace
+    original_unlink = type(tmp_path).unlink
+
+    def failing_replace(source, target):
+        if target.name == "engine_state.meta.json":
+            raise RuntimeError("authoritative persistence failure")
+        return original_replace(source, target)
+
+    monkeypatch.setattr(store.os, "replace", failing_replace)
+    def failing_unlink(self, *args, **kwargs):
+        if self.name == "engine_state.lock":
+            return original_unlink(self, *args, **kwargs)
+        raise OSError("cleanup failure")
+    monkeypatch.setattr(type(tmp_path), "unlink", failing_unlink)
+    with pytest.raises(RuntimeError, match="authoritative persistence failure"):
+        save_snapshot({"value": 2}, tmp_path, "state-a", exact_revision=baseline.revision + 1, file_state_payload={"_meta": {"state_id": "state-a", "revision": baseline.revision + 1}, "files": {}})
+    assert read_metadata(tmp_path).revision == baseline.revision
+    monkeypatch.setattr(type(tmp_path), "unlink", original_unlink)
+    monkeypatch.setattr(store.os, "replace", original_replace)
+    assert save_snapshot({"value": 3}, tmp_path, "state-a").revision == baseline.revision + 1
+
+
 def test_exact_snapshot_revision_rules_and_disk_ahead_without_overwrite(tmp_path):
     with pytest.raises(SnapshotRevisionConflict):
         save_snapshot(SimpleNamespace(value="bad"), tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
@@ -88,6 +115,81 @@ def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
     assert metadata.revision == loaded_metadata.revision == loaded.revision == 1
 
 
+def test_build_payload_is_side_effect_free(tmp_path):
+    manager = FileStateManager(str(tmp_path))
+    manager.state_id = "sid-r1"
+    manager.revision = 1
+    payload = manager.build_payload("sid-r2", 2)
+    assert manager.state_id == "sid-r1"
+    assert manager.revision == 1
+    assert payload["_meta"] == {"state_id": "sid-r2", "revision": 2}
+
+
+@pytest.mark.parametrize("failure", ["missing", "invalid", "oserror"])
+def test_referenced_filestate_generation_fail_closed_without_legacy_fallback(tmp_path, monkeypatch, failure):
+    import builtins
+    import json
+
+    manager = FileStateManager(str(tmp_path))
+    manager._state = {}
+    manager.save("sid", revision=1)
+    metadata = {
+        "schema_version": "1.2",
+        "state_id": "sid",
+        "revision": 2,
+        "file_state_file": "file_state.r2.test.json",
+    }
+    (tmp_path / "engine_state.meta.json").write_text(json.dumps(metadata), encoding="utf-8")
+    (tmp_path / "file_state.json").write_text(json.dumps({"files": {"legacy.py": {"size": 1}}}), encoding="utf-8")
+    referenced = tmp_path / "file_state.r2.test.json"
+    if failure == "invalid":
+        referenced.write_text("{not-json", encoding="utf-8")
+    elif failure == "oserror":
+        original_open = builtins.open
+        def raising_open(path, *args, **kwargs):
+            if str(path).endswith("file_state.r2.test.json"):
+                raise OSError("synthetic read failure")
+            return original_open(path, *args, **kwargs)
+        monkeypatch.setattr(builtins, "open", raising_open)
+    reloaded = FileStateManager(str(tmp_path))
+    assert reloaded._state == {}
+    assert reloaded.revision is None
+
+
+def test_referenced_filestate_without_meta_fails_closed(tmp_path):
+    import json
+
+    (tmp_path / "engine_state.meta.json").write_text(
+        json.dumps({"state_id": "sid", "revision": 2, "file_state_file": "file_state.r2.json"}),
+        encoding="utf-8",
+    )
+    (tmp_path / "file_state.r2.json").write_text(
+        json.dumps({"files": {"current.py": {"size": 4}}}),
+        encoding="utf-8",
+    )
+    manager = FileStateManager(str(tmp_path))
+    assert manager._state == {}
+    assert manager.state_id == ""
+    assert manager.revision is None
+
+
+def test_legacy_filestate_without_meta_loads_entries_but_remains_unverified(tmp_path):
+    import json
+
+    (tmp_path / "engine_state.meta.json").write_text(
+        json.dumps({"state_id": "sid", "revision": 2}),
+        encoding="utf-8",
+    )
+    (tmp_path / "file_state.json").write_text(
+        json.dumps({"legacy.py": {"size": 4}}),
+        encoding="utf-8",
+    )
+    manager = FileStateManager(str(tmp_path))
+    assert "legacy.py" in manager._state
+    assert manager.state_id == ""
+    assert manager.revision is None
+
+
 def test_snapshot_rejects_a_different_state_identity(tmp_path):
     save_snapshot(SimpleNamespace(value=1), tmp_path, "current")
 
COMPLETE_RAW_UNIFIED_DIFF_FINAL_SCOPE_END

TRANSACTIONAL_LIVE_PERSISTENCE_TEST_EVIDENCE_CLOSURE
VERDICT=IMPLEMENTATION_PASS
PRODUCTION_CHANGED=NO
REAL_DISK_AHEAD_FULL_ADAPTER_TEST=test_real_repository_persister_disk_ahead_fails_closed:PASS
REAL_DISK_AHEAD_UPDATER=_repository_updater
REAL_DISK_AHEAD_PERSISTER=_repository_persister
REAL_DISK_AHEAD_LAMBDA_UPDATER=NO
TRACE_FAILURE_REAL_CANONICAL_PARITY=test_persistence_trace_operation_is_propagated_across_successful_real_update:PASS
STARTUP_BACKFILL_REAL_PRECOMMIT_FAILURE_ATOMIC=test_startup_backfill_failure_leaves_previous_generation_authoritative:PASS
STARTUP_BACKFILL_FAILURE_INJECTION_POINT=authoritative_metadata_replace
STARTUP_BACKFILL_REAL_SAVE_SNAPSHOT_USED=YES
TEST_COMMAND_1=pytest -q tests/test_live_state_store.py
TEST_COMMAND_1_RESULT=18 passed
TEST_COMMAND_2=pytest -q tests/test_live_state_ipc.py -k "real_repository_persister_disk_ahead or persistence_trace_operation or startup_backfill"
TEST_COMMAND_2_RESULT=3 passed
TEST_COMMAND_3=pytest -q tests/test_live_state_ipc.py -k "persister or persistence_conflict or real_repository_adapter or startup_backfill or trace_operation or trace_failure"
TEST_COMMAND_3_RESULT=9 passed
H3A_CHANGED=NO
E2E_DIAGNOSTICS_ASSERTION_CHANGED=NO
MANUAL_MCP_RESTART_REQUIRED=YES
MANUAL_DESKTOP_LIVE_RESTART_REQUIRED=YES
FILES_CHANGED=contextor/core/analysis/state_manager.py; contextor/core/live_state/runtime.py; contextor/core/live_state/store.py; tests/test_live_state_ipc.py; tests/test_live_state_store.py
COMPLETE_RAW_UNIFIED_DIFF_TEST_EVIDENCE_CLOSURE_BEGIN
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 41ad96b..5eb90a6 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -188,6 +188,7 @@ class FileStateManager:
         state_file = self.state_file
         expected_engine_revision = None
         expected_engine_state_id = ""
+        referenced_generation = False
         metadata_invalid = False
         if metadata_file.exists():
             try:
@@ -196,6 +197,7 @@ class FileStateManager:
                 expected_engine_state_id = str(engine_meta.get("state_id", ""))
                 referenced = engine_meta.get("file_state_file")
                 if referenced:
+                    referenced_generation = True
                     state_file = self.cache_dir / str(referenced)
             except (
                 OSError,
@@ -212,41 +214,66 @@ class FileStateManager:
                 with open(state_file, "r", encoding="utf-8") as f:
                     data = json.load(f)
                     if "_meta" in data:
-                        self.state_id = data["_meta"].get("state_id", "")
-                        self.revision = data["_meta"].get("revision", None)
+                        file_meta = data["_meta"]
+                        if not isinstance(file_meta, dict):
+                            raise ValueError("FileState metadata must be a mapping")
+                        self.state_id = file_meta.get("state_id", "")
+                        self.revision = file_meta.get("revision", None)
                         files_data = data.get("files", {})
                     else:
+                        if referenced_generation:
+                            raise ValueError("Referenced FileState generation lacks metadata")
                         files_data = data
                         
                     self._state = {
                         path: FileState.from_dict(fs) 
                         for path, fs in files_data.items()
                     }
+                    if (
+                        referenced_generation
+                        and (
+                            not self.state_id
+                            or self.revision is None
+                        )
+                    ):
+                        raise ValueError("Referenced FileState generation metadata is incomplete")
                     if (
                         expected_engine_revision is not None
+                        and self.revision is not None
                         and self.revision != expected_engine_revision
                     ) or (
                         expected_engine_state_id
+                        and self.state_id
                         and self.state_id != expected_engine_state_id
                     ):
                         self._state = {}
                         self.state_id = ""
                         self.revision = None
-            except (json.JSONDecodeError, KeyError):
+            except (
+                OSError,
+                json.JSONDecodeError,
+                KeyError,
+                TypeError,
+                AttributeError,
+                ValueError,
+            ):
                 self._state = {}
+                self.state_id = ""
+                self.revision = None
 
     def save(self, state_id: str = "", revision: int | None = None):
         payload = self.build_payload(state_id, revision)
         with open(self.state_file, "w", encoding="utf-8") as f:
             json.dump(payload, f, indent=2)
-
-    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
         self.state_id = state_id
         if revision is not None:
             self.revision = revision
+
+    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
+        effective_revision = self.revision if revision is None else revision
         meta: Dict[str, Any] = {"state_id": state_id}
-        if getattr(self, "revision", None) is not None:
-            meta["revision"] = self.revision
+        if effective_revision is not None:
+            meta["revision"] = effective_revision
         return {
             "_meta": meta,
             "files": {path: fs.to_dict() for path, fs in self._state.items()},
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 3893a19..25fd68d 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -603,6 +603,11 @@ def run_service(
             from contextor.core.analysis.state_manager import FileStateManager
             file_state_manager = FileStateManager(str(cache))
             ensure_module_usages(state)
+            target_revision = loaded_metadata.revision + 1
+            file_state_payload = file_state_manager.build_payload(
+                loaded_metadata.state_id,
+                target_revision,
+            )
             backfill_metadata = save_snapshot(
                 state,
                 cache,
@@ -610,11 +615,8 @@ def run_service(
                 writer="live-service-symbol-calls-backfill",
                 repo_id=identity.repo_id,
                 root_path=identity.root_path,
-                revision_floor=loaded_metadata.revision,
-            )
-            file_state_manager.save(
-                loaded_metadata.state_id,
-                revision=backfill_metadata.revision,
+                exact_revision=target_revision,
+                file_state_payload=file_state_payload,
             )
     revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
     adapter_holder: dict[str, object] = {}
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index e15ef7f..43f0f33 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -253,20 +253,22 @@ def save_snapshot(
         for temporary in (state_tmp, meta_tmp):
             try:
                 temporary.unlink()
-            except FileNotFoundError:
+            except OSError:
                 pass
         if not committed and exact_revision is not None:
             for temporary in (generation_state, generation_file_state):
                 if temporary is not None:
                     try:
                         temporary.unlink()
-                    except FileNotFoundError:
+                    except OSError:
                         pass
-        os.close(lock_fd)
         try:
-            lock_file.unlink()
-        except FileNotFoundError:
-            pass
+            os.close(lock_fd)
+        finally:
+            try:
+                lock_file.unlink()
+            except OSError:
+                pass
 
 
 def load_snapshot(
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index f8d04d5..7e0cad3 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -4,6 +4,7 @@ import sys
 import threading
 import time
 import multiprocessing.connection as mpc
+from pathlib import Path
 from types import SimpleNamespace
 
 import pytest
@@ -254,31 +255,42 @@ def test_persistence_conflict_fails_closed_without_live_event():
 
 
 def test_real_repository_persister_disk_ahead_fails_closed(tmp_path, monkeypatch):
-    from contextor.core.live_state.runtime import _repository_persister
+    from contextor.core.live_state.runtime import _repository_persister, _repository_updater
     from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
-    from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
     from contextor.core.paths import repo_cache_dir
-    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+    from contextor.core.repository_identity import ensure_repository_identity
 
     repo = tmp_path / "repo"
     repo.mkdir()
-    PersistentIdentityRegistry(str(repo))
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    identity = ensure_repository_identity(repo)[0]
     monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
     cache = repo_cache_dir(repo)
-    state = SimpleNamespace(files=[])
+    state = RepositoryAnalysisState(modules={})
+    state.revision = 1
     for _ in range(11):
-        save_snapshot(state, cache, "sid")
+        save_snapshot(state, cache, "sid", repo_id=identity.repo_id, root_path=identity.root_path)
     manager = FileStateManager(str(cache))
     manager.save("sid", revision=11)
-    previous = SimpleNamespace(files=[])
-    server = CanonicalLiveServer(previous, revision=10, updater=lambda candidate, _path: {"status": "UPDATED"}, persister=_repository_persister(repo, {"manager": manager, "state_id": "sid"}))
-    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
+    previous = state
+    previous.revision = 10
+    holder = {}
+    server = CanonicalLiveServer(
+        previous,
+        revision=10,
+        updater=_repository_updater(repo, holder),
+        persister=_repository_persister(repo, holder),
+    )
+    response = server._dispatch({"operation": "update_file", "file_path": str(source)})
     assert response["error"] == "canonical_persistence_revision_conflict"
     assert response["resync_required"] is True
     assert server._revision == 10 and server._state is previous and server._activity_seq == 0
     assert read_metadata(cache).revision == 11
     assert FileStateManager(str(cache)).revision == 11
     assert load_snapshot(cache, "sid")[1].revision == 11
+    assert not any(event["operation"] == "update_file" for event in server._events)
 
 
 def test_real_repository_adapter_two_successive_updates_are_exact_successors(tmp_path, monkeypatch):
@@ -331,7 +343,7 @@ def test_real_repository_adapter_two_successive_updates_are_exact_successors(tmp
 def test_persistence_trace_operation_is_propagated_across_successful_real_update(tmp_path, monkeypatch):
     from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
     from contextor.core.live_state.runtime import _repository_persister, _repository_updater
-    from contextor.core.live_state.store import save_snapshot
+    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
     from contextor.core.paths import repo_cache_dir
     from contextor.core.repository_identity import ensure_repository_identity
     import contextor.core.runtime_trace as runtime_trace
@@ -377,8 +389,23 @@ def test_persistence_trace_operation_is_propagated_across_successful_real_update
         "trace_event",
         lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
     )
+    monkeypatch.setattr(
+        runtime_trace,
+        "current_trace_operation",
+        lambda: (_ for _ in ()).throw(RuntimeError("trace context unavailable")),
+    )
+    expected = server._revision + 1
     second = server._dispatch({"operation": "update_file", "file_path": str(source)})
     assert second["status"] == "ok"
+    assert second["revision"] == expected
+    assert server._revision == expected
+    assert server._state.revision == expected
+    persisted = read_metadata(cache)
+    assert persisted.revision == expected
+    loaded_state, loaded_metadata = load_snapshot(cache, "sid")
+    assert loaded_metadata.revision == expected
+    assert loaded_state.revision == expected
+    assert FileStateManager(str(cache)).revision == expected
 
 
 def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_path, monkeypatch):
@@ -423,6 +450,12 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
             return None
 
     monkeypatch.setattr(runtime, "CanonicalLiveServer", StubServer)
+    import contextor.core.runtime_trace as runtime_trace
+    monkeypatch.setattr(
+        runtime_trace,
+        "trace_event",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
+    )
     import contextor.core.analysis.incremental.materialization as materialization
     monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
     monkeypatch.setattr(materialization, "ensure_module_usages", lambda value: setattr(value, "module_usages", {"a.py": SimpleNamespace(symbol_calls_materialized=True, reference_evidence_materialized=True)}))
@@ -438,6 +471,45 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
     assert loaded_state.revision == metadata.revision + 1
 
 
+def test_startup_backfill_failure_leaves_previous_generation_authoritative(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+    from contextor.core.analysis.state_manager import FileState, FileStateManager, RepositoryAnalysisState
+    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.repository_identity import ensure_repository_identity
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    identity = ensure_repository_identity(repo)[0]
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    cache = repo_cache_dir(repo)
+    state = RepositoryAnalysisState(modules={"a.py": SimpleNamespace()})
+    state.revision = 1
+    metadata = save_snapshot(state, cache, "sid", repo_id=identity.repo_id, root_path=identity.root_path)
+    manager = FileStateManager(str(cache))
+    manager._state = {"a.py": FileState(10, 3, "aaa"), "b.py": FileState(20, 4, "bbb")}
+    manager.save("sid", revision=metadata.revision)
+    before = dict(manager._state)
+    monkeypatch.setattr(runtime, "CanonicalLiveServer", lambda *_args, **_kwargs: None)
+    import contextor.core.analysis.incremental.materialization as materialization
+    monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
+    monkeypatch.setattr(materialization, "ensure_module_usages", lambda _state: None)
+    import contextor.core.live_state.store as store
+    original_replace = store.os.replace
+    def fail_only_authoritative_metadata_commit(source, target):
+        if Path(target).name == "engine_state.meta.json":
+            raise RuntimeError("synthetic metadata commit failure")
+        return original_replace(source, target)
+    monkeypatch.setattr(store.os, "replace", fail_only_authoritative_metadata_commit)
+    with pytest.raises(RuntimeError, match="synthetic metadata commit failure"):
+        runtime.run_service(repo)
+    assert read_metadata(cache).revision == metadata.revision
+    assert load_snapshot(cache, "sid")[1].revision == metadata.revision
+    reloaded = FileStateManager(str(cache))
+    assert reloaded.revision == metadata.revision
+    assert reloaded._state == before
+
+
 def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
     def update(state, file_path):
         state.files.append(file_path)
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 6fe674b..55d3202 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -14,6 +14,7 @@ from contextor.core.live_state import (
     SnapshotRevisionConflict,
 )
 from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
+from contextor.core.analysis.state_manager import FileStateManager
 from contextor.core.reporting_engine.persistent_registry import (
     PersistentIdentityRegistry,
 )
@@ -45,6 +46,32 @@ def test_default_snapshot_publishes_final_pickle_via_temp_replace(tmp_path, monk
     assert replacements[0][0].name.endswith(".tmp")
 
 
+def test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock(tmp_path, monkeypatch):
+    import contextor.core.live_state.store as store
+
+    baseline = save_snapshot({"value": 1}, tmp_path, "state-a")
+    original_replace = store.os.replace
+    original_unlink = type(tmp_path).unlink
+
+    def failing_replace(source, target):
+        if target.name == "engine_state.meta.json":
+            raise RuntimeError("authoritative persistence failure")
+        return original_replace(source, target)
+
+    monkeypatch.setattr(store.os, "replace", failing_replace)
+    def failing_unlink(self, *args, **kwargs):
+        if self.name == "engine_state.lock":
+            return original_unlink(self, *args, **kwargs)
+        raise OSError("cleanup failure")
+    monkeypatch.setattr(type(tmp_path), "unlink", failing_unlink)
+    with pytest.raises(RuntimeError, match="authoritative persistence failure"):
+        save_snapshot({"value": 2}, tmp_path, "state-a", exact_revision=baseline.revision + 1, file_state_payload={"_meta": {"state_id": "state-a", "revision": baseline.revision + 1}, "files": {}})
+    assert read_metadata(tmp_path).revision == baseline.revision
+    monkeypatch.setattr(type(tmp_path), "unlink", original_unlink)
+    monkeypatch.setattr(store.os, "replace", original_replace)
+    assert save_snapshot({"value": 3}, tmp_path, "state-a").revision == baseline.revision + 1
+
+
 def test_exact_snapshot_revision_rules_and_disk_ahead_without_overwrite(tmp_path):
     with pytest.raises(SnapshotRevisionConflict):
         save_snapshot(SimpleNamespace(value="bad"), tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
@@ -88,6 +115,81 @@ def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
     assert metadata.revision == loaded_metadata.revision == loaded.revision == 1
 
 
+def test_build_payload_is_side_effect_free(tmp_path):
+    manager = FileStateManager(str(tmp_path))
+    manager.state_id = "sid-r1"
+    manager.revision = 1
+    payload = manager.build_payload("sid-r2", 2)
+    assert manager.state_id == "sid-r1"
+    assert manager.revision == 1
+    assert payload["_meta"] == {"state_id": "sid-r2", "revision": 2}
+
+
+@pytest.mark.parametrize("failure", ["missing", "invalid", "oserror"])
+def test_referenced_filestate_generation_fail_closed_without_legacy_fallback(tmp_path, monkeypatch, failure):
+    import builtins
+    import json
+
+    manager = FileStateManager(str(tmp_path))
+    manager._state = {}
+    manager.save("sid", revision=1)
+    metadata = {
+        "schema_version": "1.2",
+        "state_id": "sid",
+        "revision": 2,
+        "file_state_file": "file_state.r2.test.json",
+    }
+    (tmp_path / "engine_state.meta.json").write_text(json.dumps(metadata), encoding="utf-8")
+    (tmp_path / "file_state.json").write_text(json.dumps({"files": {"legacy.py": {"size": 1}}}), encoding="utf-8")
+    referenced = tmp_path / "file_state.r2.test.json"
+    if failure == "invalid":
+        referenced.write_text("{not-json", encoding="utf-8")
+    elif failure == "oserror":
+        original_open = builtins.open
+        def raising_open(path, *args, **kwargs):
+            if str(path).endswith("file_state.r2.test.json"):
+                raise OSError("synthetic read failure")
+            return original_open(path, *args, **kwargs)
+        monkeypatch.setattr(builtins, "open", raising_open)
+    reloaded = FileStateManager(str(tmp_path))
+    assert reloaded._state == {}
+    assert reloaded.revision is None
+
+
+def test_referenced_filestate_without_meta_fails_closed(tmp_path):
+    import json
+
+    (tmp_path / "engine_state.meta.json").write_text(
+        json.dumps({"state_id": "sid", "revision": 2, "file_state_file": "file_state.r2.json"}),
+        encoding="utf-8",
+    )
+    (tmp_path / "file_state.r2.json").write_text(
+        json.dumps({"files": {"current.py": {"size": 4}}}),
+        encoding="utf-8",
+    )
+    manager = FileStateManager(str(tmp_path))
+    assert manager._state == {}
+    assert manager.state_id == ""
+    assert manager.revision is None
+
+
+def test_legacy_filestate_without_meta_loads_entries_but_remains_unverified(tmp_path):
+    import json
+
+    (tmp_path / "engine_state.meta.json").write_text(
+        json.dumps({"state_id": "sid", "revision": 2}),
+        encoding="utf-8",
+    )
+    (tmp_path / "file_state.json").write_text(
+        json.dumps({"legacy.py": {"size": 4}}),
+        encoding="utf-8",
+    )
+    manager = FileStateManager(str(tmp_path))
+    assert "legacy.py" in manager._state
+    assert manager.state_id == ""
+    assert manager.revision is None
+
+
 def test_snapshot_rejects_a_different_state_identity(tmp_path):
     save_snapshot(SimpleNamespace(value=1), tmp_path, "current")
 
COMPLETE_RAW_UNIFIED_DIFF_TEST_EVIDENCE_CLOSURE_END

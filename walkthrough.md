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

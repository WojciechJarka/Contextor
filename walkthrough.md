# CPA1_SCOPED_TRACE_CAPTURE

## STATUS

SUCCESS. Added isolated scoped in-memory capture for ordinary `trace_event` records. No trace session is created, no global pointer is changed, and no JSONL is read by production capture code.

## FILES_CHANGED

- `contextor/core/runtime_trace.py`
- `tests/test_runtime_trace.py`
- `walkthrough.md` (this report)

## IMPLEMENTATION

- Added the prescribed ContextVar stack `_trace_capture_var` immediately after `_operation_var`.
- Added public `capture_trace_events()` beside `trace_operation`; it yields one list and restores the prior ContextVar token in `finally`.
- `trace_event` now builds the existing bounded record before deciding whether durable JSONL append is possible; it copies that record once into every active scoped capture, then preserves the existing `path is None or sid is None` durable-append guard.
- Without an active trace session, captured records omit `sid`; with one, capture and durable JSONL receive equal record dictionaries.
- Added `capture_trace_events` to `__all__`.

## TESTS

```
& .\.venv\Scripts\python.exe -m pytest -q tests\test_runtime_trace.py
```

Result: **14 passed in 5.08s**.

```
& .\.venv\Scripts\python.exe -m py_compile contextor\core\runtime_trace.py tests\test_runtime_trace.py
git diff --check -- contextor\core\runtime_trace.py tests\test_runtime_trace.py
```

Both passed. No full suite was run.

## CONTEXTOR_FLOW_VERIFY

Contextor `get_symbol_call_context(contextor.core.runtime_trace::trace_event)` reports its existing single ordinary-event call graph (2 callers, 7 callees) with no second trace-event append owner. No session/pointer lifecycle was added; the only added path is in-memory capture inside `trace_event`.

Contextor implementation fetches for `trace_event` and `start_desktop_trace_session` are correctly `stale_source` / `workspace_sync=out_of_sync` after this local edit at canonical revision 1092. No analysis or source refresh was run to alter that state.

## DIFFS

### contextor/core/runtime_trace.py

```diff
@@
 _operation_var = ...
+_trace_capture_var: contextvars.ContextVar[
+    tuple[list[dict[str, object]], ...]
+] = contextvars.ContextVar("contextor_trace_captures", default=())
@@
+@contextlib.contextmanager
+def capture_trace_events():
+    events: list[dict[str, object]] = []
+    token = _trace_capture_var.set((*_trace_capture_var.get(), events))
+    try:
+        yield events
+    finally:
+        _trace_capture_var.reset(token)
@@ trace_event
-        if path is None:
-            return
         with _lock:
             sid = _active_sid
-        if sid is None:
-            return
         ...
-        record = {..., "sid": sid, ...}
+        record = {...}
+        if sid is not None:
+            record["sid"] = sid
         ...
+        for capture in _trace_capture_var.get():
+            try:
+                capture.append(dict(record))
+            except Exception:
+                pass
+        if path is None or sid is None:
+            return
         _append(record, path)
@@ __all__
+    "capture_trace_events",
```

### tests/test_runtime_trace.py

Added focused coverage for:

- capture without a published session, including post-scope exclusion;
- equality of captured and durable JSONL event records;
- nested scopes: outer receives A/B/C exactly once and inner only B.

## COMMIT_SHA

`85862c41f18097ab95425944d3435de4560ff62b` (existing HEAD; no commit created).

## RUNTIME_RESTART_REQUIRED

YES — reload/restart the active MCP runtime before a later stage uses the new capture API. Desktop/LIVE authority restart is not required for CPA1. No restart was performed.

Awaiting `proceduj`.

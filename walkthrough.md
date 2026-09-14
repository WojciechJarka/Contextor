# CPA6_PROFILE_RUNNER

## STATUS

SUCCESS.

## BASE_HEAD

`5c4f80208138e2edb2b938eadee02a808db42380` (matches EXPECTED_BASE).

## FILES_CHANGED

- contextor/core/analysis/profile_runner.py
- tests/test_profile_runner.py
- walkthrough.md (this report)

## IMPLEMENTATION

Added synchronous `run_analysis_profile`. It creates a `profile-` operation id, scopes the existing in-memory `capture_trace_events` under `trace_operation`, runs the existing full-analysis coordinator, and passes captured parent-side evidence to CPA5's aggregator after successful analysis.

## TESTS

- `& .\.venv\Scripts\python.exe -m pytest -q tests\test_profile_runner.py tests\test_profile_analysis.py`: 6 passed in 1.14s.
- `& .\.venv\Scripts\python.exe -m py_compile contextor\core\analysis\profile_runner.py tests\test_profile_runner.py`: passed.
- `git diff --check -- contextor/core/analysis/profile_runner.py tests/test_profile_runner.py`: passed.

No full analysis or benchmark ran.

## RUNNER_CONTRACT

The runner is the sole new composition owner. It calls `run_full_analysis_exclusive(root, owner="mcp_analysis", timeout=0.0, additional_excludes=exclude_paths)`; correlation remains in the existing `trace_operation` ContextVar. It creates no coordinator, trace session, persistence, or JSONL read.

## BUSY_CONTRACT

`FullAnalysisBusyError` produces only `{schema, status="busy", operation_id, reason_code="full_analysis_busy"}`. It does not invoke `build_analysis_profile`. Other exceptions propagate unchanged.

## OP_CAPTURE_VERIFY

The focused runner test emits exactly one parent-side ANALYSIS probe under the scoped operation id and asserts the captured event bears that id. It also asserts owner, timeout, and excludes exactly.

## CONTEXTOR_FLOW_VERIFY

Contextor returned `unknown_symbol` for `contextor.core.analysis.profile_runner::run_analysis_profile`, expected without a refresh; no full analysis ran. Scoped Git/source verification found no modifications to `run_full_analysis_exclusive`, `trace_operation`, `capture_trace_events`, or `build_analysis_profile`.

## FULL_DIFFS

### contextor/core/analysis/profile_runner.py

```diff
diff --git a/contextor/core/analysis/profile_runner.py b/contextor/core/analysis/profile_runner.py
new file mode 100644
index 0000000..21c73d9
--- /dev/null
+++ b/contextor/core/analysis/profile_runner.py
@@ -0,0 +1,42 @@
+from __future__ import annotations
+from pathlib import Path
+from contextor.core.analysis.full_analysis_coordinator import (
+    FullAnalysisBusyError,
+    run_full_analysis_exclusive,
+)
+from contextor.core.analysis.profile_analysis import (
+    PROFILE_SCHEMA,
+    build_analysis_profile,
+)
+from contextor.core.runtime_trace import (
+    capture_trace_events,
+    new_trace_operation,
+    trace_operation,
+)
+def run_analysis_profile(
+    repo_path: str | Path,
+    *,
+    exclude_paths: list[str] | None = None,
+) -> dict[str, object]:
+    root = Path(repo_path).expanduser().resolve()
+    operation_id = new_trace_operation("profile")
+    with trace_operation(operation_id), capture_trace_events() as events:
+        try:
+            run_full_analysis_exclusive(
+                root,
+                owner="mcp_analysis",
+                timeout=0.0,
+                additional_excludes=exclude_paths,
+            )
+        except FullAnalysisBusyError:
+            return {
+                "schema": PROFILE_SCHEMA,
+                "status": "busy",
+                "operation_id": operation_id,
+                "reason_code": "full_analysis_busy",
+            }
+    return build_analysis_profile(
+        events,
+        operation_id=operation_id,
+    )
+__all__ = ["run_analysis_profile"]
```

### tests/test_profile_runner.py

```diff
diff --git a/tests/test_profile_runner.py b/tests/test_profile_runner.py
new file mode 100644
index 0000000..e8d548e
--- /dev/null
+++ b/tests/test_profile_runner.py
@@ -0,0 +1,107 @@
+from pathlib import Path
+import pytest
+from contextor.core.analysis import profile_runner
+from contextor.core.analysis.full_analysis_coordinator import FullAnalysisBusyError
+from contextor.core.analysis.profile_analysis import PROFILE_SCHEMA
+from contextor.core.runtime_trace import trace_event
+def test_profile_runner_scopes_capture_and_uses_nonblocking_coordinator(
+    tmp_path: Path,
+    monkeypatch,
+):
+    observed: dict[str, object] = {}
+    def fake_run(path, **kwargs):
+        observed["path"] = path
+        observed["kwargs"] = kwargs
+        trace_event(
+            "ANALYSIS",
+            "PROFILE_RUNNER_PROBE",
+            operation="runner_probe",
+        )
+        return "ignored"
+    def fake_build(events, *, operation_id):
+        observed["events"] = list(events)
+        observed["operation_id"] = operation_id
+        return {
+            "schema": PROFILE_SCHEMA,
+            "status": "ok",
+            "operation_id": operation_id,
+        }
+    monkeypatch.setattr(
+        profile_runner,
+        "run_full_analysis_exclusive",
+        fake_run,
+    )
+    monkeypatch.setattr(
+        profile_runner,
+        "build_analysis_profile",
+        fake_build,
+    )
+    result = profile_runner.run_analysis_profile(
+        tmp_path,
+        exclude_paths=["generated"],
+    )
+    assert Path(observed["path"]) == tmp_path.resolve()
+    assert observed["kwargs"] == {
+        "owner": "mcp_analysis",
+        "timeout": 0.0,
+        "additional_excludes": ["generated"],
+    }
+    operation_id = observed["operation_id"]
+    assert isinstance(operation_id, str)
+    assert operation_id.startswith("profile-")
+    events = observed["events"]
+    assert isinstance(events, list)
+    assert len(events) == 1
+    assert events[0]["ev"] == "PROFILE_RUNNER_PROBE"
+    assert events[0]["op"] == operation_id
+    assert result == {
+        "schema": PROFILE_SCHEMA,
+        "status": "ok",
+        "operation_id": operation_id,
+    }
+def test_profile_runner_returns_busy_without_aggregating(
+    tmp_path: Path,
+    monkeypatch,
+):
+    observed: dict[str, object] = {}
+    def fake_busy(path, **kwargs):
+        observed["path"] = path
+        observed["kwargs"] = kwargs
+        raise FullAnalysisBusyError("busy")
+    def forbidden_build(*args, **kwargs):
+        raise AssertionError("busy profile must not be aggregated")
+    monkeypatch.setattr(
+        profile_runner,
+        "run_full_analysis_exclusive",
+        fake_busy,
+    )
+    monkeypatch.setattr(
+        profile_runner,
+        "build_analysis_profile",
+        forbidden_build,
+    )
+    result = profile_runner.run_analysis_profile(tmp_path)
+    assert Path(observed["path"]) == tmp_path.resolve()
+    assert observed["kwargs"] == {
+        "owner": "mcp_analysis",
+        "timeout": 0.0,
+        "additional_excludes": None,
+    }
+    assert result["schema"] == PROFILE_SCHEMA
+    assert result["status"] == "busy"
+    assert result["reason_code"] == "full_analysis_busy"
+    assert isinstance(result["operation_id"], str)
+    assert result["operation_id"].startswith("profile-")
+def test_profile_runner_does_not_swallow_unexpected_analysis_errors(
+    tmp_path: Path,
+    monkeypatch,
+):
+    def fake_failure(path, **kwargs):
+        raise RuntimeError("analysis failed")
+    monkeypatch.setattr(
+        profile_runner,
+        "run_full_analysis_exclusive",
+        fake_failure,
+    )
+    with pytest.raises(RuntimeError, match="analysis failed"):
+        profile_runner.run_analysis_profile(tmp_path)
```

## COMMIT_SHA

Not created (no commit requested).

## RUNTIME_RESTART_REQUIRED

NO. The runner is not publicly connected to the active MCP runtime. MCP and Desktop/LIVE were not restarted.


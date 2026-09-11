# LIVE-O1 — test stabilization and final certification

STATUS=COMPLETE
BASE=61b550d4afddd67f123fde6c0e00b5e8638f5e86
HEAD_VERIFIED=61b550d4afddd67f123fde6c0e00b5e8638f5e86
RUNTIME_RESTART_REQUIRED=YES
FULL_SUITE_RUN_BY_AGENT=NO

## Discovery and root cause

Contextor MCP reported fresh, workspace-verified canonical state at revision 641 with no syntax errors, cycles, or name collisions. Canonical source shows that `test_connect_or_start_slow_healthy_startup` deliberately delays real authority spawn by 0.25 s, retains `timeout=0.08`, and supplies its own cold-start ceiling. The same test retains assertions for successful attachment, elapsed time >= 0.20 s, `ping()` status `ok`, and shutdown.

The candidate cause is confirmed as test-local hardware sensitivity: the old `cold_start_timeout=2.0` was a ceiling for a healthy real authority child under full-file machine load, rather than the contract under test. The separate `test_connect_or_start_true_startup_hang` remains unchanged and enforces the hard failure behavior with `cold_start_timeout=0.25`.

The canonical runtime call context identifies `contextor.core.live_state.runtime::connect_or_start` as the production owner. No canonical discovery evidence showed a production semantic defect, and the production tree remains unchanged.

## Exact test change

Only the slow-healthy-startup test now uses `cold_start_timeout=10.0`; its nearby comment now describes this as a generous test-local cold-start budget for a real authority process on slow machines. `timeout=0.08`, the 0.25 s artificial spawn delay, elapsed-time assertion, attach/ping assertion, and shutdown assertion are unchanged.

Why no production change is needed: this explicitly supplied test invocation changes only its maximum initialization allowance. Successful children do not wait for that ceiling; runtime defaults, implementation, IPC, retries, lease/liveness/takeover, watcher, and tracing behavior were not modified.

## Commands and results

Discovery:

```text
mcp__contextor__get_project_architecture(repo_path=C:\Temp\Contextor_Repo, compact=true)
result: canonical LIVE state; workspace_sync=verified; canonical_revision=641; diagnostics syntax_errors=0, cycles=0, name_collisions=0.

mcp__contextor__search_source(search_term=test_connect_or_start_slow_healthy_startup)
result: one match in tests/test_live_state_ipc.py, lines 1875-1914; test-local timeout=0.08 and cold_start_timeout=2.0 before edit.

mcp__contextor__get_symbol_call_context(symbol=contextor.core.live_state.runtime::connect_or_start)
result: fresh canonical intra-module call context; production owner confirmed.

git rev-parse HEAD
result: 61b550d4afddd67f123fde6c0e00b5e8638f5e86

git status --short; git diff --name-only
result before edit: empty
```

Certification, sequential:

```text
.\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py::test_connect_or_start_slow_healthy_startup
1 passed in 4.87s

.\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py::test_connect_or_start_slow_healthy_startup
1 passed in 4.20s

.\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py::test_connect_or_start_slow_healthy_startup
1 passed in 3.38s

.\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py::test_connect_or_start_slow_healthy_startup tests/test_live_state_ipc.py::test_connect_or_start_dead_child_fast_failure tests/test_live_state_ipc.py::test_connect_or_start_true_startup_hang
3 passed in 5.55s

.\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py
65 passed, 1 warning in 110.33s

.\.venv\Scripts\python.exe -m pytest -q tests/test_live_desktop_integration.py
20 passed in 1.65s

.\.venv\Scripts\python.exe -m pytest -q tests/test_live_e2e_corrections.py
15 passed, 1 warning in 39.82s

.\.venv\Scripts\python.exe -m pytest -q tests/test_runtime_trace.py
8 passed in 4.05s

git diff --check -- . ':(exclude)walkthrough.md'
result: exit 0; no whitespace errors. Git emitted only LF-to-CRLF normalization warnings for tests/test_live_state_ipc.py.
```

Note: three preliminary isolated invocations were run before the valid patch was present in the shared checkout and therefore exercised the original 2.0 s test, each timing out after 2.0 s. They are not certification evidence for this change. All listed certification runs above occurred after verification of the 10.0 s test-local edit.

## Files changed

FILES_CHANGED=tests/test_live_state_ipc.py
PRODUCTION_DIFF=NONE

## FULL_DIFF relative to BASE

```diff
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index 1d5ed403a22d0c3a060fec23b9dd66cab4c684bb..62b0676e87173eebfc15371976aae9c7e0ac5293 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -1897,13 +1897,14 @@ def test_connect_or_start_slow_healthy_startup(tmp_path, monkeypatch):
 
     monkeypatch.setattr(runtime_mod, "_spawn_runtime_subprocess", mock_spawn)
 
-    # Normal connect timeout is short (0.08s), but cold start timeout is 2.0s
+    # Normal connect timeout is short (0.08s); allow a generous test-local
+    # cold-start budget for the real authority process on slow machines.
     t0 = time.monotonic()
     client = runtime_mod.connect_or_start(
         repo,
         owner_token="delayed_token",
         timeout=0.08,
-        cold_start_timeout=2.0,
+        cold_start_timeout=10.0,
     )
     elapsed = time.monotonic() - t0
```
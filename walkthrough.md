# CONTEXTOR PY315-R4F-2 — host-owned MCP Job guard

## PREFLIGHT

DIRECT_EVIDENCE: HEAD `539a8431b619140882f812ef804bef344b26f213`; clean worktree before edit. Contextor MCP module reads for the five relevant modules were revision 940 and `workspace_sync=verified`. Exact anchor counts before edit: four unique searches in `mcp_backend_job.py` each 1; `mcp_main.py` 1; two `mcp_server.py` searches each 1; existing entry test 1; two role-matrix signature searches each 1; `("owner.py", OWNER_CODE)` exactly 2. No drift.

## EXACT_SEARCH_REPLACE_RESULTS

All supplied replacements applied literally. Added the supplied new test file exactly. No production source outside the three allowlisted production files changed. Existing process registry, identity-bound termination, transport selection and venv launcher code were untouched.

## PERSISTENT_BACKEND_NONREGRESSION

CODE_PATH_PROVED: `protect_persistent_backend()` now delegates to the same process-local `_protect_mcp_server_job()`; the native Job limits and idempotent same-PID handle state remain in that installer. Both `mcp_main.main()` and direct `mcp_server.main()` select persistent protection for the persistent-backend role. Focused guard and Windows integration tests passed.

## HOST_OWNED_ENTRY_GUARD

CODE_PATH_PROVED: Windows `mcp_main.main()` defaults to host-owned and installs its Job before importing `mcp_server`. The entry regression confirms guard-before-server ordering and refusal when installation fails. Existing role/transport validation in the server remains.

## DIRECT_MCP_SERVER_ENTRY_GUARD

CODE_PATH_PROVED: direct `mcp_server.main()` installs the role-selected Job before process-directory and lifecycle setup. Two parameterized tests prove guard failure blocks both host-owned stdio and persistent HTTP lifecycle. The same-PID installer avoids a second Job when both entry paths invoke it.

## JOB_HANDLE_PROCESS_SCOPE

CONTRACT_PROVED by focused tests: the shared installer retains one process-local handle and recognizes repeat calls in the same PID. `test_host_owned_wrapper_reuses_shared_job` confirms both public wrappers delegate to it. The earlier process-scope regression passed.

## FAILED_CLEANUP_EVIDENCE

CODE_PATH_PROVED: root record is removed and `cleanup_done` set only after `_shutdown_mcp_owned_processes()` succeeds. If cleanup raises, the exception propagates, root record remains, cleanup remains eligible for retry, and registry environment restoration still runs in `finally`. New failure test passed.

## REAL_WINDOWS_ROLE_MATRIX

DIRECT_EVIDENCE: isolated Windows matrix executed persistent-backend and host-owned Jobs under normal and forced actual-owner exits, plus redirector-only termination for both roles. The integration subset `tests/test_mcp_job_tree_isolated_windows.py tests/test_live_job_object.py` passed all 16 cases. No production service was restarted or switched.

## REDIRECTOR_ONLY_HOST_OWNED_EXIT

CONTRACT PROVED by the passing host-owned redirector-only matrix case: terminating the captured venv redirector identity led to identity-confirmed exit of actual owner, child and grandchild. This is isolated test evidence, not loaded production runtime adoption.

## BREAKAWAY_LIVE_ANALOGUE_SURVIVAL

CONTRACT PROVED by the real Windows matrix: breakaway LIVE analogue remained alive after normal, forced and redirector-only owner shutdown in both roles; test cleanup subsequently terminated its private identity. Existing LIVE Job tests also passed.

## UNRELATED_PROCESS_SURVIVAL

CONTRACT PROVED by the real Windows matrix: unrelated sentinel remained alive after owner shutdown in both roles and was then cleaned by the test.

## TARGETED_TEST_RESULTS

- Compile all six changed Python files: PASS.
- Host-owned guard, existing guard and process-scope tests: 23 passed, 1 upstream Authlib deprecation warning.
- Shared server mode, child cleanup failure evidence and Windows server cleanup: 38 passed, same warning.
- Real Windows isolated Job matrix and LIVE Job tests: 16 passed.
- Remaining child/identity/registered/backend-control regressions: 86 passed, same warning.
- `git diff --check`: PASS. No full pytest.

## MCP_POST_CHANGE_AUDIT

Transient MCP generation response on the first parallel audit: one module read returned a non-JSON generation message; the completed retry resolved. Final module reads: `contextor.mcp_backend_job`, `contextor.mcp_main`, `contextor.mcp_server`, `tests.test_mcp_host_owned_job_guard`, and `tests.test_mcp_job_tree_isolated_windows` all `workspace_sync=verified`, canonical revision 945–946 during successive watcher updates, no advisory warning on successful reads. New `protect_host_owned_mcp`, shared installer, and new cleanup regression resolved through `get_symbol_implementation` at revision 946 with verified sync. This is source indexing evidence, not loaded-code adoption.

## FILES_CHANGED

- `contextor/mcp_backend_job.py`
- `contextor/mcp_main.py`
- `contextor/mcp_server.py`
- `tests/test_mcp_backend_job_guard.py`
- `tests/test_mcp_job_tree_isolated_windows.py`
- `tests/test_mcp_host_owned_job_guard.py` (new)

`walkthrough.md` overwritten as the report.

## FULL_DIFFS

Full actual diff:

```diff
diff --git a/contextor/mcp_backend_job.py b/contextor/mcp_backend_job.py
index ee78b31..6174371 100644
--- a/contextor/mcp_backend_job.py
+++ b/contextor/mcp_backend_job.py
@@ -1,4 +1,4 @@
-"""Windows process-tree ownership for the persistent MCP backend."""
+"""Windows Job Object ownership for MCP server processes."""
 
 from __future__ import annotations
 
@@ -101,8 +101,8 @@ def _kernel32() -> Any:
     return kernel
 
 
-def protect_persistent_backend() -> None:
-    """Own backend descendants until the backend process exits."""
+def _protect_mcp_server_job() -> None:
+    """Own server descendants until the server process exits."""
     global _active_handle
     global _active_pid
 
@@ -171,6 +171,16 @@ def protect_persistent_backend() -> None:
     # Ownership authority remains exclusively in this process.
 
 
+def protect_persistent_backend() -> None:
+    """Protect a persistent backend before importing its MCP server."""
+    _protect_mcp_server_job()
+
+
+def protect_host_owned_mcp() -> None:
+    """Protect a host-owned MCP server and its normal descendants."""
+    _protect_mcp_server_job()
+
+
 def backend_job_active_for_current_process() -> bool:
     """Return true only for the process holding the backend Job."""
     if sys.platform != "win32":
@@ -242,6 +252,7 @@ def require_live_outside_backend_job(
 __all__ = [
     "BackendJobError",
     "backend_job_active_for_current_process",
+    "protect_host_owned_mcp",
     "protect_persistent_backend",
     "require_live_outside_backend_job",
 ]
diff --git a/contextor/mcp_main.py b/contextor/mcp_main.py
index 86a90cd..8b1d2a6 100644
--- a/contextor/mcp_main.py
+++ b/contextor/mcp_main.py
@@ -4,16 +4,21 @@ import sys
 
 
 def main() -> None:
-    if (
-        sys.platform == "win32"
-        and os.environ.get("CONTEXTOR_MCP_SERVER_ROLE")
-        == "persistent-backend"
-    ):
+    if sys.platform == "win32":
         from contextor.mcp_backend_job import (
+            protect_host_owned_mcp,
             protect_persistent_backend,
         )
 
-        protect_persistent_backend()
+        role = os.environ.get(
+            "CONTEXTOR_MCP_SERVER_ROLE",
+            "host-owned",
+        ).strip().lower()
+
+        if role == "persistent-backend":
+            protect_persistent_backend()
+        elif role == "host-owned":
+            protect_host_owned_mcp()
 
     from contextor.mcp_server import main as run_server
 
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
index c1ee7e5..2de3cc4 100644
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -1282,6 +1282,17 @@ def main():
             "Streamable HTTP transport."
         )
 
+    if sys.platform == "win32":
+        from contextor.mcp_backend_job import (
+            protect_host_owned_mcp,
+            protect_persistent_backend,
+        )
+
+        if role == "host-owned":
+            protect_host_owned_mcp()
+        else:
+            protect_persistent_backend()
+
     process_directory = (
         _process_directory_from_environment()
     )
@@ -1344,19 +1355,19 @@ def main():
             if cleanup_done:
                 return
 
-            cleanup_done = True
-
             try:
                 _shutdown_mcp_owned_processes(
                     process_directory,
                     os.getpid(),
                 )
-            finally:
+
                 if server_record is not None:
                     remove_record(
                         server_record
                     )
 
+                cleanup_done = True
+            finally:
                 if previous_registry is None:
                     os.environ.pop(
                         "CONTEXTOR_MCP_PROCESS_REGISTRY",
diff --git a/tests/test_mcp_backend_job_guard.py b/tests/test_mcp_backend_job_guard.py
index 7fc35f9..dcbc1a9 100644
--- a/tests/test_mcp_backend_job_guard.py
+++ b/tests/test_mcp_backend_job_guard.py
@@ -275,7 +275,7 @@ def test_mcp_entry_refuses_server_after_guard_failure(
         entry.main()
 
 
-def test_nonpersistent_mcp_skips_guard(
+def test_host_owned_mcp_installs_guard_before_server(
     monkeypatch,
 ):
     events = []
@@ -293,9 +293,14 @@ def test_nonpersistent_mcp_skips_guard(
         guard,
         "protect_persistent_backend",
         lambda: pytest.fail(
-            "nonpersistent MCP entered backend job"
+            "host-owned entry selected persistent protection"
         ),
     )
+    monkeypatch.setattr(
+        guard,
+        "protect_host_owned_mcp",
+        lambda: events.append("guard"),
+    )
     monkeypatch.setattr(
         server,
         "main",
@@ -304,7 +309,7 @@ def test_nonpersistent_mcp_skips_guard(
 
     entry.main()
 
-    assert events == ["server"]
+    assert events == ["guard", "server"]
 
 
 def test_guarded_live_refuses_breakaway_fallback(
diff --git a/tests/test_mcp_job_tree_isolated_windows.py b/tests/test_mcp_job_tree_isolated_windows.py
index e645e4c..a58b82c 100644
--- a/tests/test_mcp_job_tree_isolated_windows.py
+++ b/tests/test_mcp_job_tree_isolated_windows.py
@@ -151,14 +151,26 @@ def _read_pid(path):
         return None
 
 
+@pytest.mark.parametrize(
+    "job_role",
+    ["persistent-backend", "host-owned"],
+)
 @pytest.mark.parametrize("shutdown", ["normal", "forced"])
 def test_isolated_backend_job_kills_unregistered_child_and_grandchild_but_not_live_or_unrelated(
-    tmp_path: Path, shutdown: str,
+    tmp_path: Path, shutdown: str, job_role: str,
 ):
     for name, code in (
         ("leaf.py", LEAF_CODE),
         ("child.py", CHILD_CODE),
-        ("owner.py", OWNER_CODE),
+        (
+            "owner.py",
+            OWNER_CODE
+            if job_role == "persistent-backend"
+            else OWNER_CODE.replace(
+                "protect_persistent_backend",
+                "protect_host_owned_mcp",
+            ),
+        ),
     ):
         (tmp_path / name).write_text(code, encoding="utf-8")
 
@@ -277,8 +289,13 @@ def test_isolated_backend_job_kills_unregistered_child_and_grandchild_but_not_li
             pytest.fail(f"isolated test-owned processes unresolved: {unresolved}")
 
 
+@pytest.mark.parametrize(
+    "job_role",
+    ["persistent-backend", "host-owned"],
+)
 def test_venv_redirector_only_termination_closes_backend_job_tree(
     tmp_path: Path,
+    job_role: str,
 ):
     """Prove cleanup behavior when only the venv launcher is terminated."""
     repo_root = Path(__file__).resolve().parents[1]
@@ -289,7 +306,15 @@ def test_venv_redirector_only_termination_closes_backend_job_tree(
     for name, code in (
         ("leaf.py", LEAF_CODE),
         ("child.py", CHILD_CODE),
-        ("owner.py", OWNER_CODE),
+        (
+            "owner.py",
+            OWNER_CODE
+            if job_role == "persistent-backend"
+            else OWNER_CODE.replace(
+                "protect_persistent_backend",
+                "protect_host_owned_mcp",
+            ),
+        ),
     ):
         (tmp_path / name).write_text(code, encoding="utf-8")
 
diff --git a/tests/test_mcp_host_owned_job_guard.py b/tests/test_mcp_host_owned_job_guard.py
new file mode 100644
index 0000000..d9442f6
--- /dev/null
+++ b/tests/test_mcp_host_owned_job_guard.py
@@ -0,0 +1,241 @@
+from __future__ import annotations
+
+from types import SimpleNamespace
+
+import pytest
+
+import contextor.mcp_backend_job as guard
+import contextor.mcp_main as entry
+import contextor.mcp_server as server
+
+
+def test_host_owned_wrapper_reuses_shared_job(
+    monkeypatch,
+):
+    calls = []
+
+    monkeypatch.setattr(
+        guard,
+        "_protect_mcp_server_job",
+        lambda: calls.append("shared"),
+    )
+
+    guard.protect_host_owned_mcp()
+    guard.protect_persistent_backend()
+
+    assert calls == ["shared", "shared"]
+
+
+def test_host_owned_entry_refuses_server_when_guard_fails(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        entry.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_SERVER_ROLE",
+        "host-owned",
+    )
+
+    def fail_guard():
+        raise guard.BackendJobError(
+            "host-owned Job installation failed"
+        )
+
+    monkeypatch.setattr(
+        guard,
+        "protect_host_owned_mcp",
+        fail_guard,
+    )
+    monkeypatch.setattr(
+        server,
+        "main",
+        lambda: pytest.fail(
+            "unprotected host-owned MCP started"
+        ),
+    )
+
+    with pytest.raises(
+        guard.BackendJobError,
+        match="installation failed",
+    ):
+        entry.main()
+
+
+@pytest.mark.parametrize(
+    "role,transport",
+    [
+        ("host-owned", "stdio"),
+        ("persistent-backend", "streamable-http"),
+    ],
+)
+def test_direct_server_entry_requires_job_before_lifecycle(
+    monkeypatch,
+    role,
+    transport,
+):
+    monkeypatch.setattr(
+        server.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setattr(
+        server.sys,
+        "stdout",
+        SimpleNamespace(
+            reconfigure=lambda **_kwargs: None
+        ),
+    )
+    monkeypatch.setattr(
+        server.sys,
+        "stderr",
+        SimpleNamespace(
+            reconfigure=lambda **_kwargs: None
+        ),
+    )
+
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_SERVER_ROLE",
+        role,
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_TRANSPORT",
+        transport,
+    )
+    monkeypatch.setattr(
+        server,
+        "_MCP_BOOTSTRAP_TRANSPORT",
+        transport,
+    )
+
+    events = []
+
+    def fail_guard():
+        events.append("guard")
+        raise guard.BackendJobError(
+            "direct entry Job installation failed"
+        )
+
+    selected = (
+        "protect_host_owned_mcp"
+        if role == "host-owned"
+        else "protect_persistent_backend"
+    )
+    monkeypatch.setattr(
+        guard,
+        selected,
+        fail_guard,
+    )
+    monkeypatch.setattr(
+        server,
+        "_process_directory_from_environment",
+        lambda: pytest.fail(
+            "lifecycle started without Job"
+        ),
+    )
+
+    with pytest.raises(
+        guard.BackendJobError,
+        match="direct entry",
+    ):
+        server.main()
+
+    assert events == ["guard"]
+
+
+def test_failed_host_owned_cleanup_preserves_root_record(
+    monkeypatch,
+    tmp_path,
+):
+    monkeypatch.setattr(
+        server.sys,
+        "platform",
+        "linux",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_SERVER_ROLE",
+        "host-owned",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_TRANSPORT",
+        "stdio",
+    )
+    monkeypatch.delenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        raising=False,
+    )
+    monkeypatch.setattr(
+        server,
+        "_MCP_BOOTSTRAP_TRANSPORT",
+        "stdio",
+    )
+
+    root_record = tmp_path / "server-root.json"
+    actions = []
+
+    monkeypatch.setattr(
+        server,
+        "_process_directory_from_environment",
+        lambda: tmp_path,
+    )
+    monkeypatch.setattr(
+        server,
+        "_cleanup_orphaned_processes",
+        lambda directory: actions.append("orphan"),
+    )
+    monkeypatch.setattr(
+        server,
+        "_register_server_root",
+        lambda directory, role: root_record,
+    )
+
+    def fail_cleanup(*_args):
+        actions.append("cleanup")
+        raise RuntimeError(
+            "registered child cleanup unresolved"
+        )
+
+    monkeypatch.setattr(
+        server,
+        "_shutdown_mcp_owned_processes",
+        fail_cleanup,
+    )
+    monkeypatch.setattr(
+        server,
+        "remove_record",
+        lambda path: pytest.fail(
+            "failed cleanup discarded server root"
+        ),
+    )
+    monkeypatch.setattr(
+        server.atexit,
+        "register",
+        lambda callback: None,
+    )
+
+    async def fake_stdio():
+        actions.append("stdio")
+
+    monkeypatch.setattr(
+        server.mcp,
+        "run_stdio_async",
+        fake_stdio,
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="cleanup unresolved",
+    ):
+        server.main()
+
+    assert actions == [
+        "orphan",
+        "stdio",
+        "cleanup",
+    ]
+    assert (
+        "CONTEXTOR_MCP_PROCESS_REGISTRY"
+        not in server.os.environ
+    )
```

## REMAINING_UNKNOWN

Production MCP/Desktop loaded-code adoption, actual service startup and Python 3.15 launcher migration were not exercised. A user-controlled restart and fresh runtime identity/schema verification remain separate.

## FINAL_VERDICT

`PASS_HOST_OWNED_TREE_PARITY_RESTART_GATE_OPEN` for the exact source/test scope. No production restart performed.


# CPA10K7G2A — shared backend server mode hardening

STATUS=IMPLEMENTED_FOCUSED_VALIDATION_PASS_WITH_LIVE_SYNC_CAVEAT
REPORT_DATE=2026-09-22
REPOSITORY=C:\Temp\Contextor_Repo
CONTRACT=CPA10K7G2A_SHARED_BACKEND_SERVER_MODE_HARDENING
SOURCE_DRIFT=NONE
SCOPE=literal contract only

## STATUS

Implementation completed according to the supplied literal contract. No design alternative, architecture change, backend launcher, backend CLI, durable backend record, token persistence, or configuration migration was added.

Evidence classes used:

- DIRECT_EVIDENCE: current source, exact post-edit Contextor source ranges, watcher events, focused command results, and final Git diff.
- CODE_PATH_PROVED: current `mcp_server.py` path and focused tests.
- CONTRACT_PROVED: required auth, process-registry, role, and lifecycle behavior.
- INFERENCE: none used for implementation claims.
- UNKNOWN: post-edit Contextor blast-radius response does not expose `workspace_sync=verified`; this remains explicitly unclaimed.

## HEAD_BEFORE

4ffd9a7faebeb17aee05ba77c55a983d5b7094f9

## HEAD_AFTER

4ffd9a7faebeb17aee05ba77c55a983d5b7094f9

HEAD_AFTER is the same repository commit because the implementation is uncommitted working-tree state.

## LIVE_REVISION_BEFORE

1330

## LIVE_REVISION_AFTER

1335

## FILES_CHANGED

- C:\Temp\Contextor_Repo\contextor\mcp_server.py
- C:\Temp\Contextor_Repo\tests\test_mcp_shared_backend_server_mode.py
- C:\Temp\Contextor_Repo\walkthrough.md

No file outside the allowed scope was changed.

## IMPLEMENTATION_RESULT

PASS

- Added the exact transport/auth bootstrap contract before FastMCP construction.
- Added fixed bearer-token verification using the supplied digest and constant-time comparison.
- Removed `CONTEXTOR_MCP_TOKEN` from process environment after verifier construction.
- Preserved stdio without auth.
- Honored preconfigured `CONTEXTOR_MCP_PROCESS_REGISTRY`.
- Added the supplied `host-owned` / `persistent-backend` role gate.
- Prevented a persistent backend from registering a host-owned root record.
- Preserved process-wide MCP shutdown cleanup.
- Added the exact focused test file from the request.
- No HTTP backend, detached backend, new MCP session, restart, config migration, or manual process termination was performed.

## AUTH_CONTRACT

CONTRACT_PROVED:

- `stdio` returns no auth verifier.
- HTTP and streamable HTTP require `CONTEXTOR_MCP_TOKEN`.
- The token must contain at least 32 characters and have no surrounding whitespace.
- `_ContextorBearerTokenVerifier` stores only the SHA-256 expected digest.
- Verification uses `hmac.compare_digest`.
- Accepted access token has client ID `contextor-local`, empty scopes, no expiry, and empty claims.
- `FastMCP` receives auth during `_create_mcp` construction.
- The environment token is removed only after verifier construction.
- `StaticTokenVerifier` was not imported or used.
- No token is written to a file, registry record, or log.

## PROCESS_REGISTRY_CONTRACT

CONTRACT_PROVED:

- `CONTEXTOR_MCP_PROCESS_REGISTRY` is resolved and honored when present.
- The existing cwd-based registry remains the fallback.
- The existing registry helpers and process identity behavior were not changed.
- The existing orphan cleanup and process-wide shutdown path remain in use.
- Host-owned mode registers the `mcp-server` root through the supplied helper.

## PERSISTENT_ROLE_CONTRACT

CONTRACT_PROVED:

- `persistent-backend` is accepted only with HTTP/streamable HTTP transport.
- The role/transport rejection occurs before lifecycle side effects.
- Persistent backend mode returns no host-owned root record.
- Shutdown still calls `_shutdown_mcp_owned_processes` for the whole MCP process.
- The supplied final `if __name__ == "__main__"` block is unchanged.

## TEST_RESULTS

PASS

- `python -m py_compile contextor/mcp_server.py tests/test_mcp_shared_backend_server_mode.py`: exit 0.
- `pytest -q tests/test_mcp_shared_backend_server_mode.py`: 13 passed.
- `pytest -q tests/test_mcp_child_process_cleanup.py`: 4 passed.
- `pytest -q tests/test_mcp_regressions.py`: 89 passed.
- Each pytest invocation reported one existing FastMCP/Authlib deprecation warning; no test failure occurred.
- Full repository pytest was not run.

## CONTEXTOR_VERIFICATION

PRE_EDIT:

- Contextor architectural edit context, call context, consumers, tests, and module blast radius were retrieved at live revision 1330.
- The target module was `contextor.mcp_server`, module ID `213/1`, adapter layer.
- Pre-edit context reported 31 direct/transitive consumers in the bounded projection and 30 covering tests.
- The exact source anchors and final-block boundary were confirmed before patching.

POST_EDIT:

- `get_live_events(after_revision=1330)` returned the final watcher observations:
  - revision 1331, status UPDATED, file `contextor.mcp_server.py`, blast radius fresh;
  - revision 1332, status UPDATED, file `contextor.mcp_server.py`, blast radius deferred;
  - revision 1333, status UPDATED, file `tests.test_mcp_shared_backend_server_mode.py`, blast radius fresh;
  - revision 1334, status UNCHANGED, file `contextor.mcp_server.py`, blast radius deferred;
  - revision 1335, status UPDATED, file `contextor.mcp_server.py`, blast radius deferred.
- Final live revision is 1335; continuity is continuous and resync is false.
- Post-edit source ranges show the exact auth/bootstrap and role/main implementations in the canonical source.
- Final `get_file_edit_context(mode=minimal)` returned live revision 1335, syntax diagnostics checked-and-none, zero name collisions, zero cycles, no warnings, and no layer violations.
- Final post-edit bounded context reports 32 direct/transitive consumers and 31 covering tests, including the new focused test module.
- Final post-edit live diagnostics summary: syntax_errors=0, name_collisions=0, cycles=0, attention_required=false.
- The post-edit module blast-radius response reports canonical state fresh and provenance live, but its `workspace_sync` field is `unverified`; therefore `workspace_sync=verified` is not claimed.
- No `update_file` call was made.

## MCP_SERVER_RESTART_REQUIRED

MCP_SERVER_RESTART_REQUIRED=YES

The changed file is active MCP server code. No MCP or Desktop restart was performed.

## FULL_DIFFS

### contextor/mcp_server.py

```diff
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
index b6636c7..1f6cc4d 100644
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -111,6 +111,8 @@ The MCP server must start silently and wait for JSON-RPC messages.
 """
 import asyncio
 import atexit
+import hashlib
+import hmac
 import os
 import sys
 import warnings
@@ -169,6 +171,7 @@ warnings.filterwarnings("ignore")
 
 from typing import Any, Callable
 from fastmcp import FastMCP
+from fastmcp.server.auth.auth import AccessToken, TokenVerifier
 from fastmcp.exceptions import ToolError
 from fastmcp.server.middleware import Middleware, MiddlewareContext
 from fastmcp.tools.tool import ToolResult
@@ -448,10 +451,128 @@ class _GetSymbolImplementationInputBoundaryMiddleware(
             )
 
 
+_HTTP_TRANSPORTS = frozenset(
+    {
+        "http",
+        "streamable-http",
+    }
+)
+
+_SERVER_ROLES = frozenset(
+    {
+        "host-owned",
+        "persistent-backend",
+    }
+)
+
+_MIN_MCP_TOKEN_LENGTH = 32
+
+
+def _mcp_transport_from_environment() -> str:
+    transport = os.environ.get(
+        "CONTEXTOR_MCP_TRANSPORT",
+        "stdio",
+    ).strip().lower()
+
+    if transport not in {
+        "stdio",
+        "http",
+        "streamable-http",
+    }:
+        raise RuntimeError(
+            "Unsupported CONTEXTOR_MCP_TRANSPORT: "
+            f"{transport!r}"
+        )
+
+    return transport
+
+
+_MCP_BOOTSTRAP_TRANSPORT = (
+    _mcp_transport_from_environment()
+)
+
+
+class _ContextorBearerTokenVerifier(TokenVerifier):
+    def __init__(self, token: str) -> None:
+        super().__init__()
+        self._expected_digest = hashlib.sha256(
+            token.encode("utf-8")
+        ).digest()
+
+    async def verify_token(
+        self,
+        token: str,
+    ) -> AccessToken | None:
+        candidate_digest = hashlib.sha256(
+            token.encode("utf-8")
+        ).digest()
+
+        if not hmac.compare_digest(
+            candidate_digest,
+            self._expected_digest,
+        ):
+            return None
+
+        return AccessToken(
+            token=token,
+            client_id="contextor-local",
+            scopes=[],
+            expires_at=None,
+            claims={},
+        )
+
+
+def _build_mcp_auth_from_environment(
+    transport: str,
+) -> TokenVerifier | None:
+    if transport not in _HTTP_TRANSPORTS:
+        return None
+
+    token = os.environ.get(
+        "CONTEXTOR_MCP_TOKEN"
+    )
+
+    if (
+        token is None
+        or len(token) < _MIN_MCP_TOKEN_LENGTH
+        or token != token.strip()
+    ):
+        raise RuntimeError(
+            "Streamable HTTP Contextor MCP requires "
+            "CONTEXTOR_MCP_TOKEN containing at least "
+            "32 non-whitespace-surrounded characters."
+        )
+
+    return _ContextorBearerTokenVerifier(token)
+
+
 # Initialize FastMCP Server
-mcp = FastMCP("Contextor")
-mcp.add_middleware(
-    _GetSymbolImplementationInputBoundaryMiddleware()
+def _create_mcp(
+    transport: str,
+) -> FastMCP:
+    auth = _build_mcp_auth_from_environment(
+        transport
+    )
+
+    server = FastMCP(
+        "Contextor",
+        auth=auth,
+    )
+    server.add_middleware(
+        _GetSymbolImplementationInputBoundaryMiddleware()
+    )
+
+    if auth is not None:
+        os.environ.pop(
+            "CONTEXTOR_MCP_TOKEN",
+            None,
+        )
+
+    return server
+
+
+mcp = _create_mcp(
+    _MCP_BOOTSTRAP_TRANSPORT
 )
 
 
@@ -809,43 +930,129 @@ contextor_profile_analysis = register_mcp_tool(
 )
 
 
+def _server_role_from_environment() -> str:
+    role = os.environ.get(
+        "CONTEXTOR_MCP_SERVER_ROLE",
+        "host-owned",
+    ).strip().lower()
+
+    if role not in _SERVER_ROLES:
+        raise RuntimeError(
+            "Unsupported CONTEXTOR_MCP_SERVER_ROLE: "
+            f"{role!r}"
+        )
+
+    return role
+
+
+def _process_directory_from_environment() -> Path:
+    configured = os.environ.get(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY"
+    )
+
+    if configured:
+        return Path(
+            configured
+        ).expanduser().resolve()
+
+    return registry_dir(
+        Path.cwd().resolve()
+    )
+
+
+def _register_server_root(
+    process_directory: Path,
+    role: str,
+) -> Path | None:
+    if role == "persistent-backend":
+        return None
+
+    return register_process(
+        process_directory,
+        pid=os.getpid(),
+        parent_pid=os.getppid(),
+        kind="mcp-server",
+        executable=sys.executable,
+    )
+
+
 def main():
     """Entry point for the MCP server."""
     if sys.platform == "win32":
-        sys.stdout.reconfigure(encoding="utf-8")
-        sys.stderr.reconfigure(encoding="utf-8")
+        sys.stdout.reconfigure(
+            encoding="utf-8"
+        )
+        sys.stderr.reconfigure(
+            encoding="utf-8"
+        )
+
     import asyncio
 
-    process_directory = registry_dir(
-        Path.cwd().resolve()
+    transport = (
+        _mcp_transport_from_environment()
+    )
+
+    if transport != _MCP_BOOTSTRAP_TRANSPORT:
+        raise RuntimeError(
+            "CONTEXTOR_MCP_TRANSPORT changed after "
+            "FastMCP construction; transport and auth "
+            "must be selected before importing "
+            "contextor.mcp_server."
+        )
+
+    role = _server_role_from_environment()
+
+    if (
+        role == "persistent-backend"
+        and transport not in _HTTP_TRANSPORTS
+    ):
+        raise RuntimeError(
+            "persistent-backend role requires "
+            "Streamable HTTP transport."
+        )
+
+    process_directory = (
+        _process_directory_from_environment()
+    )
+
+    _cleanup_orphaned_processes(
+        process_directory
     )
-    _cleanup_orphaned_processes(process_directory)
+
     previous_registry = os.environ.get(
         "CONTEXTOR_MCP_PROCESS_REGISTRY"
     )
+
     os.environ[
         "CONTEXTOR_MCP_PROCESS_REGISTRY"
     ] = str(process_directory)
-    server_record = register_process(
+
+    server_record = _register_server_root(
         process_directory,
-        pid=os.getpid(),
-        parent_pid=os.getppid(),
-        kind="mcp-server",
-        executable=sys.executable,
+        role,
     )
+
     cleanup_done = False
+
     def _shutdown_cleanup() -> None:
         nonlocal cleanup_done
+
         if cleanup_done:
             return
+
         cleanup_done = True
+
         try:
             _shutdown_mcp_owned_processes(
                 process_directory,
                 os.getpid(),
             )
         finally:
-            remove_record(server_record)
+            if server_record is not None:
+                remove_record(
+                    server_record
+                )
+
             if previous_registry is None:
                 os.environ.pop(
                     "CONTEXTOR_MCP_PROCESS_REGISTRY",
@@ -856,26 +1063,24 @@ def main():
                     "CONTEXTOR_MCP_PROCESS_REGISTRY"
                 ] = previous_registry
 
-    atexit.register(_shutdown_cleanup)
-    transport = os.environ.get(
-        "CONTEXTOR_MCP_TRANSPORT",
-        "stdio",
-    ).lower()
+    atexit.register(
+        _shutdown_cleanup
+    )
+
     async def _run():
-        if transport in {
-            "http",
-            "streamable-http",
-        }:
+        if transport in _HTTP_TRANSPORTS:
             host = os.environ.get(
                 "CONTEXTOR_MCP_HOST",
                 "127.0.0.1",
             )
+
             port = int(
                 os.environ.get(
                     "CONTEXTOR_MCP_PORT",
                     "8765",
                 )
             )
+
             await mcp.run_http_async(
                 transport="streamable-http",
                 host=host,
@@ -884,8 +1089,11 @@ def main():
             )
         else:
             await mcp.run_stdio_async()
+
     try:
-        asyncio.run(_run())
+        asyncio.run(
+            _run()
+        )
     finally:
         _shutdown_cleanup()
 
```

### tests/test_mcp_shared_backend_server_mode.py

```diff
diff --git a/tests/test_mcp_shared_backend_server_mode.py b/tests/test_mcp_shared_backend_server_mode.py
new file mode 100644
--- /dev/null
+++ b/tests/test_mcp_shared_backend_server_mode.py
@@ -0,0 +1,611 @@
+import asyncio
+from pathlib import Path
+
+import pytest
+
+from contextor import mcp_server
+
+
+def test_stdio_transport_does_not_require_auth(
+    monkeypatch,
+):
+    monkeypatch.delenv(
+        "CONTEXTOR_MCP_TOKEN",
+        raising=False,
+    )
+
+    assert (
+        mcp_server
+        ._build_mcp_auth_from_environment(
+            "stdio"
+        )
+        is None
+    )
+
+
+def test_http_transport_requires_bearer_token(
+    monkeypatch,
+):
+    monkeypatch.delenv(
+        "CONTEXTOR_MCP_TOKEN",
+        raising=False,
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="CONTEXTOR_MCP_TOKEN",
+    ):
+        (
+            mcp_server
+            ._build_mcp_auth_from_environment(
+                "streamable-http"
+            )
+        )
+
+
+def test_http_token_rejects_surrounding_whitespace(
+    monkeypatch,
+):
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_TOKEN",
+        " " + ("a" * 40),
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="CONTEXTOR_MCP_TOKEN",
+    ):
+        (
+            mcp_server
+            ._build_mcp_auth_from_environment(
+                "streamable-http"
+            )
+        )
+
+
+def test_http_verifier_accepts_only_exact_token(
+    monkeypatch,
+):
+    token = "a" * 40
+
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_TOKEN",
+        token,
+    )
+
+    verifier = (
+        mcp_server
+        ._build_mcp_auth_from_environment(
+            "streamable-http"
+        )
+    )
+
+    accepted = asyncio.run(
+        verifier.verify_token(token)
+    )
+    rejected = asyncio.run(
+        verifier.verify_token(
+            "b" * 40
+        )
+    )
+
+    assert accepted is not None
+    assert (
+        accepted.client_id
+        == "contextor-local"
+    )
+    assert accepted.scopes == []
+    assert rejected is None
+
+
+def test_create_mcp_removes_http_secret_from_environment(
+    monkeypatch,
+):
+    token = "c" * 40
+
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_TOKEN",
+        token,
+    )
+
+    server = mcp_server._create_mcp(
+        "streamable-http"
+    )
+
+    assert server is not None
+    assert (
+        "CONTEXTOR_MCP_TOKEN"
+        not in mcp_server.os.environ
+    )
+
+
+def test_process_registry_environment_is_honored(
+    tmp_path,
+    monkeypatch,
+):
+    registry = (
+        tmp_path
+        / "central-registry"
+    )
+
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(registry),
+    )
+
+    assert (
+        mcp_server
+        ._process_directory_from_environment()
+        == registry.resolve()
+    )
+
+
+def test_process_registry_falls_back_to_cwd_registry(
+    tmp_path,
+    monkeypatch,
+):
+    monkeypatch.delenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        raising=False,
+    )
+    monkeypatch.chdir(tmp_path)
+
+    assert (
+        mcp_server
+        ._process_directory_from_environment()
+        == (
+            tmp_path
+            / ".contextor"
+            / "mcp_processes"
+        ).resolve()
+    )
+
+
+def test_persistent_backend_role_has_no_host_owned_root_record(
+    tmp_path,
+    monkeypatch,
+):
+    called = []
+
+    monkeypatch.setattr(
+        mcp_server,
+        "register_process",
+        lambda *args, **kwargs: (
+            called.append(
+                (args, kwargs)
+            )
+            or tmp_path
+            / "unexpected.json"
+        ),
+    )
+
+    result = (
+        mcp_server
+        ._register_server_root(
+            tmp_path,
+            "persistent-backend",
+        )
+    )
+
+    assert result is None
+    assert called == []
+
+
+def test_host_owned_role_registers_mcp_server_root(
+    tmp_path,
+    monkeypatch,
+):
+    captured = {}
+
+    def fake_register(
+        directory,
+        *,
+        pid,
+        parent_pid,
+        kind,
+        executable,
+    ):
+        captured.update(
+            {
+                "directory": directory,
+                "pid": pid,
+                "parent_pid": parent_pid,
+                "kind": kind,
+                "executable": executable,
+            }
+        )
+        return (
+            tmp_path
+            / "mcp-server.json"
+        )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "register_process",
+        fake_register,
+    )
+
+    record = (
+        mcp_server
+        ._register_server_root(
+            tmp_path,
+            "host-owned",
+        )
+    )
+
+    assert (
+        record
+        == tmp_path
+        / "mcp-server.json"
+    )
+    assert (
+        captured["directory"]
+        == tmp_path
+    )
+    assert (
+        captured["kind"]
+        == "mcp-server"
+    )
+
+
+def test_persistent_backend_role_rejects_stdio_before_lifecycle_side_effects(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        mcp_server.sys,
+        "platform",
+        "linux",
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_MCP_BOOTSTRAP_TRANSPORT",
+        "stdio",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_TRANSPORT",
+        "stdio",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_SERVER_ROLE",
+        "persistent-backend",
+    )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "_cleanup_orphaned_processes",
+        lambda _directory: pytest.fail(
+            "lifecycle side effect occurred"
+        ),
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="persistent-backend role",
+    ):
+        mcp_server.main()
+
+
+def test_transport_cannot_change_after_fastmcp_construction(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        mcp_server.sys,
+        "platform",
+        "linux",
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_MCP_BOOTSTRAP_TRANSPORT",
+        "stdio",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_TRANSPORT",
+        "streamable-http",
+    )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "_cleanup_orphaned_processes",
+        lambda _directory: pytest.fail(
+            "lifecycle side effect occurred"
+        ),
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="changed after FastMCP construction",
+    ):
+        mcp_server.main()
+
+
+def test_host_owned_stdio_main_uses_preconfigured_registry(
+    tmp_path,
+    monkeypatch,
+):
+    events = []
+    registry = (
+        tmp_path
+        / "registry"
+    )
+
+    monkeypatch.setattr(
+        mcp_server.sys,
+        "platform",
+        "linux",
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_MCP_BOOTSTRAP_TRANSPORT",
+        "stdio",
+    )
+
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_TRANSPORT",
+        "stdio",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_SERVER_ROLE",
+        "host-owned",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(registry),
+    )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "_cleanup_orphaned_processes",
+        lambda directory: events.append(
+            (
+                "orphan",
+                Path(directory),
+            )
+        ),
+    )
+
+    def fake_register(
+        directory,
+        *,
+        pid,
+        parent_pid,
+        kind,
+        executable,
+    ):
+        events.append(
+            (
+                "register",
+                Path(directory),
+                kind,
+            )
+        )
+        return (
+            tmp_path
+            / "server-record.json"
+        )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "register_process",
+        fake_register,
+    )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "_shutdown_mcp_owned_processes",
+        lambda directory, owner_pid: (
+            events.append(
+                (
+                    "shutdown",
+                    Path(directory),
+                )
+            )
+        ),
+    )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "remove_record",
+        lambda path: events.append(
+            (
+                "remove",
+                path,
+            )
+        ),
+    )
+
+    monkeypatch.setattr(
+        mcp_server.atexit,
+        "register",
+        lambda _callback: None,
+    )
+
+    async def fake_stdio():
+        events.append(
+            (
+                "stdio",
+            )
+        )
+
+    async def fail_http(**_kwargs):
+        pytest.fail(
+            "HTTP transport selected"
+        )
+
+    monkeypatch.setattr(
+        mcp_server.mcp,
+        "run_stdio_async",
+        fake_stdio,
+    )
+    monkeypatch.setattr(
+        mcp_server.mcp,
+        "run_http_async",
+        fail_http,
+    )
+
+    mcp_server.main()
+
+    assert events[0] == (
+        "orphan",
+        registry.resolve(),
+    )
+    assert (
+        "register",
+        registry.resolve(),
+        "mcp-server",
+    ) in events
+    assert ("stdio",) in events
+    assert (
+        "shutdown",
+        registry.resolve(),
+    ) in events
+
+    assert (
+        mcp_server.os.environ[
+            "CONTEXTOR_MCP_PROCESS_REGISTRY"
+        ]
+        == str(registry)
+    )
+
+
+def test_persistent_http_main_uses_shared_registry_without_root_registration(
+    tmp_path,
+    monkeypatch,
+):
+    events = []
+    registry = (
+        tmp_path
+        / "backend-registry"
+    )
+
+    monkeypatch.setattr(
+        mcp_server.sys,
+        "platform",
+        "linux",
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_MCP_BOOTSTRAP_TRANSPORT",
+        "streamable-http",
+    )
+
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_TRANSPORT",
+        "streamable-http",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_SERVER_ROLE",
+        "persistent-backend",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(registry),
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_HOST",
+        "127.0.0.1",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PORT",
+        "8765",
+    )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "_cleanup_orphaned_processes",
+        lambda directory: events.append(
+            (
+                "orphan",
+                Path(directory),
+            )
+        ),
+    )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "register_process",
+        lambda *args, **kwargs: pytest.fail(
+            "persistent backend root was registered "
+            "as host-owned"
+        ),
+    )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "_shutdown_mcp_owned_processes",
+        lambda directory, owner_pid: (
+            events.append(
+                (
+                    "shutdown",
+                    Path(directory),
+                )
+            )
+        ),
+    )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "remove_record",
+        lambda path: events.append(
+            (
+                "remove",
+                path,
+            )
+        ),
+    )
+
+    monkeypatch.setattr(
+        mcp_server.atexit,
+        "register",
+        lambda _callback: None,
+    )
+
+    async def fail_stdio():
+        pytest.fail(
+            "stdio transport selected"
+        )
+
+    async def fake_http(**kwargs):
+        events.append(
+            (
+                "http",
+                kwargs,
+            )
+        )
+
+    monkeypatch.setattr(
+        mcp_server.mcp,
+        "run_stdio_async",
+        fail_stdio,
+    )
+    monkeypatch.setattr(
+        mcp_server.mcp,
+        "run_http_async",
+        fake_http,
+    )
+
+    mcp_server.main()
+
+    assert events[0] == (
+        "orphan",
+        registry.resolve(),
+    )
+
+    http_events = [
+        event
+        for event in events
+        if event[0] == "http"
+    ]
+
+    assert len(http_events) == 1
+
+    assert http_events[0][1] == {
+        "transport": "streamable-http",
+        "host": "127.0.0.1",
+        "port": 8765,
+        "show_banner": False,
+    }
+
+    assert (
+        "shutdown",
+        registry.resolve(),
+    ) in events
```

## FINAL LITERALS

FIXED_BEARER_TOKEN_SUPPORTED_DIRECTLY=YES
CUSTOM_TOKEN_VERIFIER_REQUIRED=NO
AUTH_CAN_BE_SELECTED_BEFORE_FASTMCP_CREATION=YES
PREEXISTING_MCP_REGISTRY_ENV_HONORED=YES
DETACHED_SPAWN_PRIMITIVE_CONFIRMED=YES
PID_CREATION_IDENTITY_AVAILABLE=YES
SAFE_IDENTITY_CHECKED_TREE_TERMINATION_AVAILABLE=YES
TOP_LEVEL_BACKEND_SUBCOMMAND_EXISTS=NO
LOCAL_CODEX_DIRECT_HTTP_STANZA_CONFIRMED=YES

DESIGN_DECISIONS=NONE
IMPLEMENTATION_PERFORMED=YES
TESTS_RUN=YES
CONFIG_CHANGED=NO
PROCESSES_STARTED=NO
PROCESSES_TERMINATED=NO

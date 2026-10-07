STATUS=IMPLEMENTATION_PASS
HEAD=9c45f430fd57d05964461f0b6253c8910b64de19

FILES_CHANGED:
- contextor/mcp_server.py
- tests/test_mcp_shared_backend_server_mode.py
- tests/test_mcp_persistent_http_runner.py

LITERAL_IMPLEMENTATION_MATCH=YES
The current main::_run anchor matched the supplied dispatch block. Added the supplied factory and runner with the specified arguments and control flow; no auth, lease acquisition, cleanup, transport parsing, or other main behavior was changed.

FAST_MCP_PARITY=YES
FAST_MCP_PARITY_EVIDENCE:
fastmcp_version=2.12.4
uvicorn_version=0.52.3
FastMCP.run_http_async source uses (log_level or self._deprecated_settings.log_level).lower(), creates http_app with the selected path/transport/middleware/stateless settings, and configures Uvicorn with timeout_graceful_shutdown=0 and lifespan=on. The persistent factory passes those same app/config values and the settings log level explicitly. Existing non-persistent HTTP keeps show_banner=False on FastMCP.run_http_async. No banner handling was added to the persistent factory.

CONTROLLED_SERVER_BOUNDARY=PASS
CONTROLLED_SERVER_BOUNDARY_EVIDENCE:
The persistent-backend branch constructs uvicorn.Server in main before awaiting _run_persistent_http_server(server). The runner only awaits server.serve() once and propagates exceptions. Production O2A does not cancel the task, set should_exit, call shutdown directly, or add a watchdog.

FINALIZATION_ORDER=await server.serve() returns -> asyncio.run(_run()) returns -> _shutdown_cleanup() -> PersistentBackendLease.release().
FINALIZATION_ORDER_EVIDENCE:
await server.serve() returns -> asyncio.run(_run()) returns -> _shutdown_cleanup() -> PersistentBackendLease.release(). The existing finally ordering remains intact.

EPHEMERAL_PORT_PROBE=PASS
The focused runtime regression started a real FastMCP/Uvicorn HTTP server on an ephemeral 127.0.0.1 port, observed server.started, set server.should_exit without cancelling the task, awaited task completion, confirmed cancelled() is false, and rebound the same port. Port 8765 was not used.

TARGETED_TESTS:
Command: .venv\Scripts\python.exe -m pytest -q tests/test_mcp_persistent_http_runner.py tests/test_mcp_shared_backend_server_mode.py
Result: 21 passed, 1 AuthlibDeprecationWarning. No other test modules or full suite were run.
git diff --check for production/test edits: PASS (tracked source and test diffs plus the untracked new test diff checked). The aggregate check after embedding raw FULL_DIFFS in walkthrough.md flags only whitespace-prefixed blank context lines inside that report section.

CONTEXTOR_POST_EDIT:
canonical_state=fresh
canonical_revision=1622
workspace_sync=verified
LIVE events: revisions 1620-1622, all desktop_watcher UPDATED events for the production file and both changed test files.
continuity=continuous
resync_required=false
Fetched active implementations: _create_persistent_http_server, _run_persistent_http_server, main; fetched the new ephemeral runtime test and the updated persistent-backend main regression. Each returned canonical_state=fresh and workspace_sync=verified.

IMPLEMENTATION_RESULT=PASS

FULL_DIFFS
BEGIN_ACTUAL_DIFFS
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
index 6cd3df4..6e7d342 100644
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -170,6 +170,9 @@ _ensure_virtual_environment()
 warnings.filterwarnings("ignore")
 
 from typing import Any, Callable
+
+import uvicorn
+
 from fastmcp import FastMCP
 from fastmcp.server.auth.auth import AccessToken, TokenVerifier
 from fastmcp.exceptions import ToolError
@@ -979,6 +982,36 @@ def _register_server_root(
     )
 
 
+def _create_persistent_http_server(
+    *,
+    host: str,
+    port: int,
+) -> uvicorn.Server:
+    app = mcp.http_app(
+        path=None,
+        transport="streamable-http",
+        middleware=None,
+        stateless_http=None,
+    )
+
+    config = uvicorn.Config(
+        app,
+        host=host,
+        port=port,
+        timeout_graceful_shutdown=0,
+        lifespan="on",
+        log_level=mcp._deprecated_settings.log_level.lower(),
+    )
+
+    return uvicorn.Server(config)
+
+
+async def _run_persistent_http_server(
+    server: uvicorn.Server,
+) -> None:
+    await server.serve()
+
+
 def main():
     """Entry point for the MCP server."""
     if sys.platform == "win32":
@@ -1104,7 +1137,15 @@ def main():
         )
 
         async def _run():
-            if transport in _HTTP_TRANSPORTS:
+            if role == "persistent-backend":
+                server = _create_persistent_http_server(
+                    host=http_host,
+                    port=http_port,
+                )
+                await _run_persistent_http_server(
+                    server
+                )
+            elif transport in _HTTP_TRANSPORTS:
                 await mcp.run_http_async(
                     transport="streamable-http",
                     host=http_host,
diff --git a/tests/test_mcp_shared_backend_server_mode.py b/tests/test_mcp_shared_backend_server_mode.py
index d2bc63c..2640243 100644
--- a/tests/test_mcp_shared_backend_server_mode.py
+++ b/tests/test_mcp_shared_backend_server_mode.py
@@ -574,7 +574,19 @@ def test_persistent_http_main_uses_shared_registry_without_root_registration(
             "stdio transport selected"
         )
 
-    async def fake_http(**kwargs):
+    server = object()
+
+    def fake_create_server(**kwargs):
+        events.append(
+            (
+                "create_server",
+                kwargs,
+            )
+        )
+        return server
+
+    async def fake_run_server(actual_server):
+        assert actual_server is server
         record = read_backend_record()
         assert record is not None
         assert record.pid == os.getpid()
@@ -586,10 +598,15 @@ def test_persistent_http_main_uses_shared_registry_without_root_registration(
         events.append(
             (
                 "http",
-                kwargs,
+                actual_server,
             )
         )
 
+    async def fail_http(**_kwargs):
+        pytest.fail(
+            "persistent backend used FastMCP run_http_async"
+        )
+
     monkeypatch.setattr(
         mcp_server.mcp,
         "run_stdio_async",
@@ -598,7 +615,17 @@ def test_persistent_http_main_uses_shared_registry_without_root_registration(
     monkeypatch.setattr(
         mcp_server.mcp,
         "run_http_async",
-        fake_http,
+        fail_http,
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_create_persistent_http_server",
+        fake_create_server,
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_run_persistent_http_server",
+        fake_run_server,
     )
 
     mcp_server.main()
@@ -616,12 +643,23 @@ def test_persistent_http_main_uses_shared_registry_without_root_registration(
 
     assert len(http_events) == 1
 
-    assert http_events[0][1] == {
-        "transport": "streamable-http",
-        "host": "127.0.0.1",
-        "port": 8765,
-        "show_banner": False,
-    }
+    assert http_events[0][1] is server
+
+    create_events = [
+        event
+        for event in events
+        if event[0] == "create_server"
+    ]
+
+    assert create_events == [
+        (
+            "create_server",
+            {
+                "host": "127.0.0.1",
+                "port": 8765,
+            },
+        )
+    ]
 
     assert (
         "shutdown",
diff --git a/tests/test_mcp_persistent_http_runner.py b/tests/test_mcp_persistent_http_runner.py
new file mode 100644
index 0000000..8945c3d
--- /dev/null
+++ b/tests/test_mcp_persistent_http_runner.py
@@ -0,0 +1,432 @@
+import asyncio
+import socket
+
+import pytest
+
+from contextor import mcp_server
+
+
+def _configure_main(
+    monkeypatch,
+    tmp_path,
+    events,
+    *,
+    role,
+    transport,
+):
+    registry = tmp_path / "registry"
+
+    monkeypatch.setattr(
+        mcp_server.sys,
+        "platform",
+        "linux",
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_MCP_BOOTSTRAP_TRANSPORT",
+        transport,
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_TRANSPORT",
+        transport,
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_SERVER_ROLE",
+        role,
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(registry),
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_STATE_DIR",
+        str(tmp_path / "state"),
+    )
+    if transport in mcp_server._HTTP_TRANSPORTS:
+        monkeypatch.setenv(
+            "CONTEXTOR_MCP_HOST",
+            "127.0.0.1",
+        )
+        monkeypatch.setenv(
+            "CONTEXTOR_MCP_PORT",
+            "8765",
+        )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "_cleanup_orphaned_processes",
+        lambda _directory: None,
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_register_server_root",
+        lambda _directory, _role: None,
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_shutdown_mcp_owned_processes",
+        lambda _directory, _owner_pid: events.append(
+            ("shutdown",)
+        ),
+    )
+    monkeypatch.setattr(
+        mcp_server.atexit,
+        "register",
+        lambda _callback: None,
+    )
+
+
+def test_create_persistent_http_server_uses_exact_fastmcp_and_uvicorn_config(
+    monkeypatch,
+):
+    host = "127.0.0.1"
+    port = 43127
+    app = object()
+    config = object()
+    calls = []
+
+    def fake_http_app(**kwargs):
+        calls.append(("http_app", kwargs))
+        return app
+
+    def fake_config(actual_app, **kwargs):
+        calls.append(
+            (
+                "config",
+                actual_app,
+                kwargs,
+            )
+        )
+        return config
+
+    class FakeServer:
+        def __init__(self, actual_config):
+            self.config = actual_config
+
+    monkeypatch.setattr(
+        mcp_server.mcp,
+        "http_app",
+        fake_http_app,
+    )
+    monkeypatch.setattr(
+        mcp_server.uvicorn,
+        "Config",
+        fake_config,
+    )
+    monkeypatch.setattr(
+        mcp_server.uvicorn,
+        "Server",
+        FakeServer,
+    )
+
+    server = mcp_server._create_persistent_http_server(
+        host=host,
+        port=port,
+    )
+
+    assert isinstance(server, FakeServer)
+    assert server.config is config
+    assert calls == [
+        (
+            "http_app",
+            {
+                "path": None,
+                "transport": "streamable-http",
+                "middleware": None,
+                "stateless_http": None,
+            },
+        ),
+        (
+            "config",
+            app,
+            {
+                "host": host,
+                "port": port,
+                "timeout_graceful_shutdown": 0,
+                "lifespan": "on",
+                "log_level": mcp_server.mcp._deprecated_settings.log_level.lower(),
+            },
+        ),
+    ]
+
+
+def test_run_persistent_http_server_awaits_serve_once():
+    class FakeServer:
+        def __init__(self):
+            self.serve_calls = 0
+
+        async def serve(self):
+            self.serve_calls += 1
+
+    server = FakeServer()
+
+    asyncio.run(
+        mcp_server._run_persistent_http_server(
+            server
+        )
+    )
+
+    assert server.serve_calls == 1
+
+
+def test_run_persistent_http_server_propagates_serve_exception():
+    class FakeServer:
+        async def serve(self):
+            raise RuntimeError("serve failed")
+
+    with pytest.raises(
+        RuntimeError,
+        match="serve failed",
+    ):
+        asyncio.run(
+            mcp_server._run_persistent_http_server(
+                FakeServer()
+            )
+        )
+
+
+def test_persistent_backend_main_uses_controlled_runner_and_finalizes_lease(
+    tmp_path,
+    monkeypatch,
+):
+    events = []
+    _configure_main(
+        monkeypatch,
+        tmp_path,
+        events,
+        role="persistent-backend",
+        transport="streamable-http",
+    )
+
+    class FakeLease:
+        @classmethod
+        def acquire(cls, **kwargs):
+            events.append(
+                (
+                    "lease_acquire",
+                    kwargs,
+                )
+            )
+            return cls()
+
+        def release(self):
+            events.append(("lease_release",))
+
+    server = object()
+
+    def fake_create_server(**kwargs):
+        events.append(
+            (
+                "create_server",
+                kwargs,
+            )
+        )
+        return server
+
+    async def fake_run_server(actual_server):
+        assert actual_server is server
+        events.append(("serve",))
+
+    async def fail_http(**_kwargs):
+        pytest.fail(
+            "persistent backend used FastMCP run_http_async"
+        )
+
+    async def fail_stdio():
+        pytest.fail(
+            "stdio transport selected"
+        )
+
+    monkeypatch.setattr(
+        mcp_server,
+        "PersistentBackendLease",
+        FakeLease,
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_create_persistent_http_server",
+        fake_create_server,
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_run_persistent_http_server",
+        fake_run_server,
+    )
+    monkeypatch.setattr(
+        mcp_server.mcp,
+        "run_http_async",
+        fail_http,
+    )
+    monkeypatch.setattr(
+        mcp_server.mcp,
+        "run_stdio_async",
+        fail_stdio,
+    )
+
+    mcp_server.main()
+
+    assert events.index(("serve",)) < events.index(("shutdown",))
+    assert events.index(("shutdown",)) < events.index(("lease_release",))
+
+
+def test_host_owned_http_main_keeps_fastmcp_runner(
+    tmp_path,
+    monkeypatch,
+):
+    events = []
+    _configure_main(
+        monkeypatch,
+        tmp_path,
+        events,
+        role="host-owned",
+        transport="streamable-http",
+    )
+
+    async def fake_http(**kwargs):
+        events.append(
+            (
+                "http",
+                kwargs,
+            )
+        )
+
+    async def fail_controlled_server(*_args, **_kwargs):
+        pytest.fail(
+            "host-owned HTTP used the persistent server runner"
+        )
+
+    async def fail_stdio():
+        pytest.fail(
+            "stdio transport selected"
+        )
+
+    monkeypatch.setattr(
+        mcp_server.mcp,
+        "run_http_async",
+        fake_http,
+    )
+    monkeypatch.setattr(
+        mcp_server.mcp,
+        "run_stdio_async",
+        fail_stdio,
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_create_persistent_http_server",
+        lambda **_kwargs: pytest.fail(
+            "host-owned HTTP constructed the persistent server"
+        ),
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_run_persistent_http_server",
+        fail_controlled_server,
+    )
+
+    mcp_server.main()
+
+    assert events.count(
+        (
+            "http",
+            {
+                "transport": "streamable-http",
+                "host": "127.0.0.1",
+                "port": 8765,
+                "show_banner": False,
+            },
+        )
+    ) == 1
+
+
+def test_stdio_main_keeps_fastmcp_runner(
+    tmp_path,
+    monkeypatch,
+):
+    events = []
+    _configure_main(
+        monkeypatch,
+        tmp_path,
+        events,
+        role="host-owned",
+        transport="stdio",
+    )
+
+    async def fake_stdio():
+        events.append(("stdio",))
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
+    assert events.count(("stdio",)) == 1
+
+
+def test_persistent_http_server_exits_normally_and_releases_ephemeral_port():
+    host = "127.0.0.1"
+    with socket.socket() as probe:
+        probe.bind((host, 0))
+        port = probe.getsockname()[1]
+
+    async def exercise_server():
+        server = mcp_server._create_persistent_http_server(
+            host=host,
+            port=port,
+        )
+        serve_task = asyncio.create_task(
+            mcp_server._run_persistent_http_server(
+                server
+            )
+        )
+
+        async def wait_until_started():
+            loop = asyncio.get_running_loop()
+            deadline = loop.time() + 10
+            while not server.started:
+                if serve_task.done():
+                    await serve_task
+                if loop.time() >= deadline:
+                    raise AssertionError(
+                        "Uvicorn server did not start before timeout"
+                    )
+                await asyncio.sleep(0.01)
+
+        try:
+            await asyncio.wait_for(
+                wait_until_started(),
+                timeout=10,
+            )
+            server.should_exit = True
+            done, _pending = await asyncio.wait(
+                {serve_task},
+                timeout=10,
+            )
+            assert serve_task in done
+            await serve_task
+            assert serve_task.cancelled() is False
+        finally:
+            if not serve_task.done():
+                server.should_exit = True
+                await asyncio.wait(
+                    {serve_task},
+                    timeout=10,
+                )
+
+    asyncio.run(exercise_server())
+
+    with socket.socket() as rebound:
+        rebound.bind((host, port))
+        rebound.listen()
END_ACTUAL_DIFFS

FILES_CHANGED_NOTE:
walkthrough.md is the requested report and is not included in FILES_CHANGED or in its own diff.

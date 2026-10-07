import asyncio
import socket

import pytest

from contextor import mcp_server


def _configure_main(
    monkeypatch,
    tmp_path,
    events,
    *,
    role,
    transport,
):
    registry = tmp_path / "registry"

    monkeypatch.setattr(
        mcp_server.sys,
        "platform",
        "linux",
    )
    monkeypatch.setattr(
        mcp_server,
        "_MCP_BOOTSTRAP_TRANSPORT",
        transport,
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_TRANSPORT",
        transport,
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_SERVER_ROLE",
        role,
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        str(registry),
    )
    monkeypatch.setenv(
        "CONTEXTOR_STATE_DIR",
        str(tmp_path / "state"),
    )
    if transport in mcp_server._HTTP_TRANSPORTS:
        monkeypatch.setenv(
            "CONTEXTOR_MCP_HOST",
            "127.0.0.1",
        )
        monkeypatch.setenv(
            "CONTEXTOR_MCP_PORT",
            "8765",
        )

    monkeypatch.setattr(
        mcp_server,
        "_cleanup_orphaned_processes",
        lambda _directory: None,
    )
    monkeypatch.setattr(
        mcp_server,
        "_register_server_root",
        lambda _directory, _role: None,
    )
    monkeypatch.setattr(
        mcp_server,
        "_shutdown_mcp_owned_processes",
        lambda _directory, _owner_pid: events.append(
            ("shutdown",)
        ),
    )
    monkeypatch.setattr(
        mcp_server.atexit,
        "register",
        lambda _callback: None,
    )


def test_create_persistent_http_server_uses_exact_fastmcp_and_uvicorn_config(
    monkeypatch,
):
    host = "127.0.0.1"
    port = 43127
    app = object()
    config = object()
    calls = []

    def fake_http_app(**kwargs):
        calls.append(("http_app", kwargs))
        return app

    def fake_config(actual_app, **kwargs):
        calls.append(
            (
                "config",
                actual_app,
                kwargs,
            )
        )
        return config

    class FakeServer:
        def __init__(self, actual_config):
            self.config = actual_config

    monkeypatch.setattr(
        mcp_server.mcp,
        "http_app",
        fake_http_app,
    )
    monkeypatch.setattr(
        mcp_server.uvicorn,
        "Config",
        fake_config,
    )
    monkeypatch.setattr(
        mcp_server.uvicorn,
        "Server",
        FakeServer,
    )

    server = mcp_server._create_persistent_http_server(
        host=host,
        port=port,
    )

    assert isinstance(server, FakeServer)
    assert server.config is config
    assert calls == [
        (
            "http_app",
            {
                "path": None,
                "transport": "streamable-http",
                "middleware": None,
                "stateless_http": None,
            },
        ),
        (
            "config",
            app,
            {
                "host": host,
                "port": port,
                "timeout_graceful_shutdown": 0,
                "lifespan": "on",
                "log_level": mcp_server.mcp._deprecated_settings.log_level.lower(),
            },
        ),
    ]


def test_run_persistent_http_server_awaits_serve_once():
    class FakeServer:
        def __init__(self):
            self.serve_calls = 0

        async def serve(self):
            self.serve_calls += 1

    server = FakeServer()

    asyncio.run(
        mcp_server._run_persistent_http_server(
            server
        )
    )

    assert server.serve_calls == 1


def test_run_persistent_http_server_propagates_serve_exception():
    class FakeServer:
        async def serve(self):
            raise RuntimeError("serve failed")

    with pytest.raises(
        RuntimeError,
        match="serve failed",
    ):
        asyncio.run(
            mcp_server._run_persistent_http_server(
                FakeServer()
            )
        )


def test_persistent_backend_main_uses_controlled_runner_and_finalizes_lease(
    tmp_path,
    monkeypatch,
):
    events = []
    _configure_main(
        monkeypatch,
        tmp_path,
        events,
        role="persistent-backend",
        transport="streamable-http",
    )

    class FakeLease:
        @classmethod
        def acquire(cls, **kwargs):
            events.append(
                (
                    "lease_acquire",
                    kwargs,
                )
            )
            return cls()

        def release(self):
            events.append(("lease_release",))

    server = object()

    def fake_create_server(**kwargs):
        events.append(
            (
                "create_server",
                kwargs,
            )
        )
        return server

    async def fake_run_server(actual_server):
        assert actual_server is server
        events.append(("serve",))

    async def fail_http(**_kwargs):
        pytest.fail(
            "persistent backend used FastMCP run_http_async"
        )

    async def fail_stdio():
        pytest.fail(
            "stdio transport selected"
        )

    monkeypatch.setattr(
        mcp_server,
        "PersistentBackendLease",
        FakeLease,
    )
    monkeypatch.setattr(
        mcp_server,
        "_create_persistent_http_server",
        fake_create_server,
    )
    monkeypatch.setattr(
        mcp_server,
        "_run_persistent_http_server",
        fake_run_server,
    )
    monkeypatch.setattr(
        mcp_server.mcp,
        "run_http_async",
        fail_http,
    )
    monkeypatch.setattr(
        mcp_server.mcp,
        "run_stdio_async",
        fail_stdio,
    )

    mcp_server.main()

    assert events.index(("serve",)) < events.index(("shutdown",))
    assert events.index(("shutdown",)) < events.index(("lease_release",))


def test_host_owned_http_main_keeps_fastmcp_runner(
    tmp_path,
    monkeypatch,
):
    events = []
    _configure_main(
        monkeypatch,
        tmp_path,
        events,
        role="host-owned",
        transport="streamable-http",
    )

    async def fake_http(**kwargs):
        events.append(
            (
                "http",
                kwargs,
            )
        )

    async def fail_controlled_server(*_args, **_kwargs):
        pytest.fail(
            "host-owned HTTP used the persistent server runner"
        )

    async def fail_stdio():
        pytest.fail(
            "stdio transport selected"
        )

    monkeypatch.setattr(
        mcp_server.mcp,
        "run_http_async",
        fake_http,
    )
    monkeypatch.setattr(
        mcp_server.mcp,
        "run_stdio_async",
        fail_stdio,
    )
    monkeypatch.setattr(
        mcp_server,
        "_create_persistent_http_server",
        lambda **_kwargs: pytest.fail(
            "host-owned HTTP constructed the persistent server"
        ),
    )
    monkeypatch.setattr(
        mcp_server,
        "_run_persistent_http_server",
        fail_controlled_server,
    )

    mcp_server.main()

    assert events.count(
        (
            "http",
            {
                "transport": "streamable-http",
                "host": "127.0.0.1",
                "port": 8765,
                "show_banner": False,
            },
        )
    ) == 1


def test_stdio_main_keeps_fastmcp_runner(
    tmp_path,
    monkeypatch,
):
    events = []
    _configure_main(
        monkeypatch,
        tmp_path,
        events,
        role="host-owned",
        transport="stdio",
    )

    async def fake_stdio():
        events.append(("stdio",))

    async def fail_http(**_kwargs):
        pytest.fail(
            "HTTP transport selected"
        )

    monkeypatch.setattr(
        mcp_server.mcp,
        "run_stdio_async",
        fake_stdio,
    )
    monkeypatch.setattr(
        mcp_server.mcp,
        "run_http_async",
        fail_http,
    )

    mcp_server.main()

    assert events.count(("stdio",)) == 1


def test_persistent_http_server_exits_normally_and_releases_ephemeral_port():
    host = "127.0.0.1"
    with socket.socket() as probe:
        probe.bind((host, 0))
        port = probe.getsockname()[1]

    async def exercise_server():
        server = mcp_server._create_persistent_http_server(
            host=host,
            port=port,
        )
        serve_task = asyncio.create_task(
            mcp_server._run_persistent_http_server(
                server
            )
        )

        async def wait_until_started():
            loop = asyncio.get_running_loop()
            deadline = loop.time() + 10
            while not server.started:
                if serve_task.done():
                    await serve_task
                if loop.time() >= deadline:
                    raise AssertionError(
                        "Uvicorn server did not start before timeout"
                    )
                await asyncio.sleep(0.01)

        try:
            await asyncio.wait_for(
                wait_until_started(),
                timeout=10,
            )
            server.should_exit = True
            done, _pending = await asyncio.wait(
                {serve_task},
                timeout=10,
            )
            assert serve_task in done
            await serve_task
            assert serve_task.cancelled() is False
        finally:
            if not serve_task.done():
                server.should_exit = True
                await asyncio.wait(
                    {serve_task},
                    timeout=10,
                )

    asyncio.run(exercise_server())

    with socket.socket() as rebound:
        rebound.bind((host, port))
        rebound.listen()

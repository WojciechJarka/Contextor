import asyncio
import socket
from types import SimpleNamespace

import pytest

from contextor import mcp_server
from contextor.mcp_backend_state import (
    BackendHostOwnerClaim,
    BackendOwnerClaimError,
)


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


def _owner_claim(
    backend_instance_id="backend-current",
    *,
    owner_token="owner-token",
):
    return BackendHostOwnerClaim(
        schema_version=1,
        backend_instance_id=backend_instance_id,
        host_owner_identity="host-owner",
        host_kind="desktop",
        host_pid=123,
        host_executable="python.exe",
        host_creation_time=456,
        owner_token=owner_token,
        claimed_at=1.0,
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
            server,
            backend_instance_id="backend-runner-test",
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
                FakeServer(),
                backend_instance_id="backend-runner-test",
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
    backend_instance_id = "active-backend-instance"

    class FakeLease:
        def __init__(self):
            self.record = SimpleNamespace(
                instance_id=backend_instance_id
            )

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

    async def fake_run_server(
        actual_server,
        *,
        backend_instance_id,
    ):
        assert actual_server is server
        assert backend_instance_id == "active-backend-instance"
        events.append(("serve", backend_instance_id))

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

    assert events.index(("serve", backend_instance_id)) < events.index(("shutdown",))
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


@pytest.mark.parametrize(
    ("case", "expected_pinned", "expected_revoked"),
    [
        ("unarmed_no_claim", None, False),
        ("unarmed_other_instance", None, False),
        ("unarmed_match", "current", False),
        ("unarmed_unknown", None, False),
        ("unarmed_stale", None, True),
        ("armed_match", "pinned", False),
        ("armed_unknown", "pinned", False),
        ("armed_stale", "pinned", True),
        ("armed_missing", "pinned", True),
        ("armed_replaced", "pinned", True),
        ("unarmed_read_error", None, False),
        ("armed_read_error", "pinned", False),
    ],
    ids=[
        "unarmed-no-claim",
        "unarmed-other-instance",
        "unarmed-current-match",
        "unarmed-current-unknown",
        "unarmed-current-stale",
        "armed-exact-match",
        "armed-exact-unknown",
        "armed-exact-stale",
        "armed-claim-missing",
        "armed-claim-replaced",
        "unarmed-claim-read-error",
        "armed-claim-read-error",
    ],
)
def test_evaluate_persistent_backend_owner_state_machine(
    case,
    expected_pinned,
    expected_revoked,
    monkeypatch,
):
    pinned_claim = (
        _owner_claim()
        if expected_pinned == "pinned"
        or case.startswith("armed_")
        else None
    )
    if case in {
        "unarmed_no_claim",
        "armed_missing",
        "unarmed_read_error",
        "armed_read_error",
    }:
        current_claim = None
    elif case == "unarmed_other_instance":
        current_claim = _owner_claim("backend-other")
    elif case == "armed_replaced":
        current_claim = _owner_claim(owner_token="replacement-token")
    elif case.startswith("armed_"):
        current_claim = pinned_claim
    else:
        current_claim = _owner_claim()

    owner_state = {
        "unarmed_match": "match",
        "unarmed_unknown": "unknown",
        "unarmed_stale": "stale",
        "armed_match": "match",
        "armed_unknown": "unknown",
        "armed_stale": "stale",
    }.get(case)
    classified_claims = []

    def fake_read_claim():
        if case in {"unarmed_read_error", "armed_read_error"}:
            raise BackendOwnerClaimError("malformed owner claim")
        return current_claim

    def fake_classify(claim):
        classified_claims.append(claim)
        return owner_state

    monkeypatch.setattr(
        mcp_server,
        "read_backend_owner_claim",
        fake_read_claim,
    )
    monkeypatch.setattr(
        mcp_server,
        "classify_backend_owner_process",
        fake_classify,
    )

    result = mcp_server._evaluate_persistent_backend_owner(
        backend_instance_id="backend-current",
        pinned_claim=pinned_claim,
    )

    expected_claim = {
        "current": current_claim,
        "pinned": pinned_claim,
    }.get(expected_pinned)
    assert result == (expected_claim, expected_revoked)

    if case in {
        "unarmed_no_claim",
        "unarmed_other_instance",
        "armed_missing",
        "armed_replaced",
        "unarmed_read_error",
        "armed_read_error",
    }:
        assert classified_claims == []
    else:
        assert classified_claims == [
            pinned_claim if case.startswith("armed_") else current_claim
        ]


def test_watchdog_revokes_server_without_cancelling_serve_task(monkeypatch):
    class FakeServer:
        should_exit = False

    async def exercise_watchdog():
        server = FakeServer()
        serve_finished = asyncio.Event()

        async def fake_serve():
            await serve_finished.wait()

        serve_task = asyncio.create_task(fake_serve())
        await asyncio.sleep(0)

        monkeypatch.setattr(
            mcp_server,
            "_evaluate_persistent_backend_owner",
            lambda **_kwargs: (None, True),
        )

        await mcp_server._watch_persistent_backend_owner(
            server,
            backend_instance_id="backend-watchdog-test",
            poll_interval=0.001,
        )

        assert server.should_exit is True
        assert serve_task.cancelled() is False
        serve_finished.set()
        await serve_task

    asyncio.run(exercise_watchdog())


def test_watchdog_continues_polling_until_instance_is_revoked(monkeypatch):
    class FakeServer:
        should_exit = False

    server = FakeServer()
    calls = []

    def evaluate(**_kwargs):
        calls.append(None)
        return None, len(calls) > 1

    monkeypatch.setattr(
        mcp_server,
        "_evaluate_persistent_backend_owner",
        evaluate,
    )

    asyncio.run(
        mcp_server._watch_persistent_backend_owner(
            server,
            backend_instance_id="backend-watchdog-test",
            poll_interval=0.001,
        )
    )

    assert len(calls) == 2
    assert server.should_exit is True


def test_persistent_http_server_exits_normally_and_releases_ephemeral_port(
    monkeypatch,
):
    host = "127.0.0.1"
    with socket.socket() as probe:
        probe.bind((host, 0))
        port = probe.getsockname()[1]

    async def exercise_server():
        server = mcp_server._create_persistent_http_server(
            host=host,
            port=port,
        )
        monkeypatch.setattr(
            mcp_server,
            "_evaluate_persistent_backend_owner",
            lambda **_kwargs: (None, False),
        )
        serve_task = asyncio.create_task(
            mcp_server._run_persistent_http_server(
                server,
                backend_instance_id="backend-runner-test",
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


def test_persistent_http_server_self_terminates_on_owner_revocation(
    monkeypatch,
):
    host = "127.0.0.1"
    with socket.socket() as probe:
        probe.bind((host, 0))
        port = probe.getsockname()[1]

    async def exercise_server():
        server = mcp_server._create_persistent_http_server(
            host=host,
            port=port,
        )
        evaluations = []

        def evaluate(
            *,
            backend_instance_id,
            pinned_claim,
        ):
            assert backend_instance_id == "backend-watchdog-test"
            evaluations.append(server.started)
            if len(evaluations) == 1 or not server.started:
                return pinned_claim, False
            return pinned_claim, True

        monkeypatch.setattr(
            mcp_server,
            "_evaluate_persistent_backend_owner",
            evaluate,
        )
        serve_task = asyncio.create_task(
            mcp_server._run_persistent_http_server(
                server,
                backend_instance_id="backend-watchdog-test",
                owner_poll_interval=0.01,
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

        await asyncio.wait_for(
            wait_until_started(),
            timeout=10,
        )
        done, _pending = await asyncio.wait(
            {serve_task},
            timeout=10,
        )
        assert serve_task in done
        await serve_task
        assert serve_task.cancelled() is False
        assert server.should_exit is True
        assert evaluations[0] is False
        assert any(evaluations[1:])

    asyncio.run(exercise_server())

    with socket.socket() as rebound:
        rebound.bind((host, port))
        rebound.listen()

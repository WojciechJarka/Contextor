import asyncio
import os
from pathlib import Path

import pytest

from contextor import mcp_server
from contextor.mcp_backend_state import (
    BackendAlreadyRunning,
    PersistentBackendLease,
    read_backend_record,
)


def test_stdio_transport_does_not_require_auth(
    monkeypatch,
):
    monkeypatch.delenv(
        "CONTEXTOR_MCP_TOKEN",
        raising=False,
    )

    assert (
        mcp_server
        ._build_mcp_auth_from_environment(
            "stdio"
        )
        is None
    )


def test_http_transport_requires_bearer_token(
    monkeypatch,
):
    monkeypatch.delenv(
        "CONTEXTOR_MCP_TOKEN",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="CONTEXTOR_MCP_TOKEN",
    ):
        (
            mcp_server
            ._build_mcp_auth_from_environment(
                "streamable-http"
            )
        )


def test_http_token_rejects_surrounding_whitespace(
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTEXTOR_MCP_TOKEN",
        " " + ("a" * 40),
    )

    with pytest.raises(
        RuntimeError,
        match="CONTEXTOR_MCP_TOKEN",
    ):
        (
            mcp_server
            ._build_mcp_auth_from_environment(
                "streamable-http"
            )
        )


def test_http_verifier_accepts_only_exact_token(
    monkeypatch,
):
    token = "a" * 40

    monkeypatch.setenv(
        "CONTEXTOR_MCP_TOKEN",
        token,
    )

    verifier = (
        mcp_server
        ._build_mcp_auth_from_environment(
            "streamable-http"
        )
    )

    accepted = asyncio.run(
        verifier.verify_token(token)
    )
    rejected = asyncio.run(
        verifier.verify_token(
            "b" * 40
        )
    )

    assert accepted is not None
    assert (
        accepted.client_id
        == "contextor-local"
    )
    assert accepted.scopes == []
    assert rejected is None


def test_create_mcp_removes_http_secret_from_environment(
    monkeypatch,
):
    token = "c" * 40

    monkeypatch.setenv(
        "CONTEXTOR_MCP_TOKEN",
        token,
    )

    server = mcp_server._create_mcp(
        "streamable-http"
    )

    assert server is not None
    assert (
        "CONTEXTOR_MCP_TOKEN"
        not in mcp_server.os.environ
    )


def test_process_registry_environment_is_honored(
    tmp_path,
    monkeypatch,
):
    registry = (
        tmp_path
        / "central-registry"
    )

    monkeypatch.setenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        str(registry),
    )

    assert (
        mcp_server
        ._process_directory_from_environment()
        == registry.resolve()
    )


def test_process_registry_falls_back_to_cwd_registry(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        raising=False,
    )
    monkeypatch.chdir(tmp_path)

    assert (
        mcp_server
        ._process_directory_from_environment()
        == (
            tmp_path
            / ".contextor"
            / "mcp_processes"
        ).resolve()
    )


def test_persistent_backend_role_has_no_host_owned_root_record(
    tmp_path,
    monkeypatch,
):
    called = []

    monkeypatch.setattr(
        mcp_server,
        "register_process",
        lambda *args, **kwargs: (
            called.append(
                (args, kwargs)
            )
            or tmp_path
            / "unexpected.json"
        ),
    )

    result = (
        mcp_server
        ._register_server_root(
            tmp_path,
            "persistent-backend",
        )
    )

    assert result is None
    assert called == []


def test_host_owned_role_registers_mcp_server_root(
    tmp_path,
    monkeypatch,
):
    captured = {}

    def fake_register(
        directory,
        *,
        pid,
        parent_pid,
        kind,
        executable,
    ):
        captured.update(
            {
                "directory": directory,
                "pid": pid,
                "parent_pid": parent_pid,
                "kind": kind,
                "executable": executable,
            }
        )
        return (
            tmp_path
            / "mcp-server.json"
        )

    monkeypatch.setattr(
        mcp_server,
        "register_process",
        fake_register,
    )

    record = (
        mcp_server
        ._register_server_root(
            tmp_path,
            "host-owned",
        )
    )

    assert (
        record
        == tmp_path
        / "mcp-server.json"
    )
    assert (
        captured["directory"]
        == tmp_path
    )
    assert (
        captured["kind"]
        == "mcp-server"
    )


def test_persistent_backend_role_rejects_stdio_before_lifecycle_side_effects(
    monkeypatch,
):
    monkeypatch.setattr(
        mcp_server.sys,
        "platform",
        "linux",
    )
    monkeypatch.setattr(
        mcp_server,
        "_MCP_BOOTSTRAP_TRANSPORT",
        "stdio",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_TRANSPORT",
        "stdio",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_SERVER_ROLE",
        "persistent-backend",
    )

    monkeypatch.setattr(
        mcp_server,
        "_cleanup_orphaned_processes",
        lambda _directory: pytest.fail(
            "lifecycle side effect occurred"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="persistent-backend role",
    ):
        mcp_server.main()


def test_transport_cannot_change_after_fastmcp_construction(
    monkeypatch,
):
    monkeypatch.setattr(
        mcp_server.sys,
        "platform",
        "linux",
    )
    monkeypatch.setattr(
        mcp_server,
        "_MCP_BOOTSTRAP_TRANSPORT",
        "stdio",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_TRANSPORT",
        "streamable-http",
    )

    monkeypatch.setattr(
        mcp_server,
        "_cleanup_orphaned_processes",
        lambda _directory: pytest.fail(
            "lifecycle side effect occurred"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="changed after FastMCP construction",
    ):
        mcp_server.main()


def test_host_owned_stdio_main_uses_preconfigured_registry(
    tmp_path,
    monkeypatch,
):
    events = []
    registry = (
        tmp_path
        / "registry"
    )

    monkeypatch.setattr(
        mcp_server.sys,
        "platform",
        "linux",
    )
    monkeypatch.setattr(
        mcp_server,
        "_MCP_BOOTSTRAP_TRANSPORT",
        "stdio",
    )

    monkeypatch.setenv(
        "CONTEXTOR_MCP_TRANSPORT",
        "stdio",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_SERVER_ROLE",
        "host-owned",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        str(registry),
    )

    monkeypatch.setattr(
        mcp_server,
        "_cleanup_orphaned_processes",
        lambda directory: events.append(
            (
                "orphan",
                Path(directory),
            )
        ),
    )

    def fake_register(
        directory,
        *,
        pid,
        parent_pid,
        kind,
        executable,
    ):
        events.append(
            (
                "register",
                Path(directory),
                kind,
            )
        )
        return (
            tmp_path
            / "server-record.json"
        )

    monkeypatch.setattr(
        mcp_server,
        "register_process",
        fake_register,
    )

    monkeypatch.setattr(
        mcp_server,
        "_shutdown_mcp_owned_processes",
        lambda directory, owner_pid: (
            events.append(
                (
                    "shutdown",
                    Path(directory),
                )
            )
        ),
    )

    monkeypatch.setattr(
        mcp_server,
        "remove_record",
        lambda path: events.append(
            (
                "remove",
                path,
            )
        ),
    )

    monkeypatch.setattr(
        mcp_server.atexit,
        "register",
        lambda _callback: None,
    )

    async def fake_stdio():
        events.append(
            (
                "stdio",
            )
        )

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

    assert events[0] == (
        "orphan",
        registry.resolve(),
    )
    assert (
        "register",
        registry.resolve(),
        "mcp-server",
    ) in events
    assert ("stdio",) in events
    assert (
        "shutdown",
        registry.resolve(),
    ) in events

    assert (
        mcp_server.os.environ[
            "CONTEXTOR_MCP_PROCESS_REGISTRY"
        ]
        == str(registry)
    )


def test_persistent_http_main_uses_shared_registry_without_root_registration(
    tmp_path,
    monkeypatch,
):
    events = []
    registry = (
        tmp_path
        / "backend-registry"
    )

    monkeypatch.setattr(
        mcp_server.sys,
        "platform",
        "linux",
    )
    monkeypatch.setattr(
        mcp_server,
        "_MCP_BOOTSTRAP_TRANSPORT",
        "streamable-http",
    )

    monkeypatch.setenv(
        "CONTEXTOR_MCP_TRANSPORT",
        "streamable-http",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_SERVER_ROLE",
        "persistent-backend",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        str(registry),
    )
    monkeypatch.setenv(
        "CONTEXTOR_STATE_DIR",
        str(tmp_path / "state"),
    )
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
        lambda directory: events.append(
            (
                "orphan",
                Path(directory),
            )
        ),
    )

    monkeypatch.setattr(
        mcp_server,
        "register_process",
        lambda *args, **kwargs: pytest.fail(
            "persistent backend root was registered "
            "as host-owned"
        ),
    )

    monkeypatch.setattr(
        mcp_server,
        "_shutdown_mcp_owned_processes",
        lambda directory, owner_pid: (
            events.append(
                (
                    "shutdown",
                    Path(directory),
                )
            )
        ),
    )

    monkeypatch.setattr(
        mcp_server,
        "remove_record",
        lambda path: events.append(
            (
                "remove",
                path,
            )
        ),
    )

    monkeypatch.setattr(
        mcp_server.atexit,
        "register",
        lambda _callback: None,
    )

    async def fail_stdio():
        pytest.fail(
            "stdio transport selected"
        )

    async def fake_http(**kwargs):
        record = read_backend_record()
        assert record is not None
        assert record.pid == os.getpid()
        assert record.server_role == "persistent-backend"
        assert record.transport == "streamable-http"
        assert record.host == "127.0.0.1"
        assert record.port == 8765
        assert Path(record.process_registry) == registry.resolve()
        events.append(
            (
                "http",
                kwargs,
            )
        )

    monkeypatch.setattr(
        mcp_server.mcp,
        "run_stdio_async",
        fail_stdio,
    )
    monkeypatch.setattr(
        mcp_server.mcp,
        "run_http_async",
        fake_http,
    )

    mcp_server.main()

    assert events[0] == (
        "orphan",
        registry.resolve(),
    )

    http_events = [
        event
        for event in events
        if event[0] == "http"
    ]

    assert len(http_events) == 1

    assert http_events[0][1] == {
        "transport": "streamable-http",
        "host": "127.0.0.1",
        "port": 8765,
        "show_banner": False,
    }

    assert (
        "shutdown",
        registry.resolve(),
    ) in events
    assert read_backend_record() is None


def test_second_persistent_backend_is_rejected_before_lifecycle_side_effects(
    tmp_path,
    monkeypatch,
):
    registry = tmp_path / "registry"
    monkeypatch.setenv(
        "CONTEXTOR_STATE_DIR",
        str(tmp_path / "state"),
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_TRANSPORT",
        "streamable-http",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_SERVER_ROLE",
        "persistent-backend",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        str(registry),
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_HOST",
        "127.0.0.1",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_PORT",
        "8765",
    )
    monkeypatch.setattr(
        mcp_server.sys,
        "platform",
        "linux",
    )
    monkeypatch.setattr(
        mcp_server,
        "_MCP_BOOTSTRAP_TRANSPORT",
        "streamable-http",
    )

    lease = PersistentBackendLease.acquire(
        host="127.0.0.1",
        port=8765,
        transport="streamable-http",
        process_registry=registry,
    )

    try:
        monkeypatch.setattr(
            mcp_server,
            "_cleanup_orphaned_processes",
            lambda *_args, **_kwargs: pytest.fail(
                "lifecycle side effect occurred"
            ),
        )

        with pytest.raises(BackendAlreadyRunning):
            mcp_server.main()
    finally:
        lease.release()

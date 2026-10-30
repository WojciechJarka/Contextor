from __future__ import annotations

from types import SimpleNamespace

import pytest

import contextor.mcp_backend_job as guard
import contextor.mcp_main as entry
import contextor.mcp_server as server


def test_host_owned_wrapper_reuses_shared_job(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        guard,
        "_protect_mcp_server_job",
        lambda: calls.append("shared"),
    )

    guard.protect_host_owned_mcp()
    guard.protect_persistent_backend()

    assert calls == ["shared", "shared"]


def test_host_owned_entry_refuses_server_when_guard_fails(
    monkeypatch,
):
    monkeypatch.setattr(
        entry.sys,
        "platform",
        "win32",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_SERVER_ROLE",
        "host-owned",
    )

    def fail_guard():
        raise guard.BackendJobError(
            "host-owned Job installation failed"
        )

    monkeypatch.setattr(
        guard,
        "protect_host_owned_mcp",
        fail_guard,
    )
    monkeypatch.setattr(
        server,
        "main",
        lambda: pytest.fail(
            "unprotected host-owned MCP started"
        ),
    )

    with pytest.raises(
        guard.BackendJobError,
        match="installation failed",
    ):
        entry.main()


@pytest.mark.parametrize(
    "role,transport",
    [
        ("host-owned", "stdio"),
        ("persistent-backend", "streamable-http"),
    ],
)
def test_direct_server_entry_requires_job_before_lifecycle(
    monkeypatch,
    role,
    transport,
):
    monkeypatch.setattr(
        server.sys,
        "platform",
        "win32",
    )
    monkeypatch.setattr(
        server.sys,
        "stdout",
        SimpleNamespace(
            reconfigure=lambda **_kwargs: None
        ),
    )
    monkeypatch.setattr(
        server.sys,
        "stderr",
        SimpleNamespace(
            reconfigure=lambda **_kwargs: None
        ),
    )

    monkeypatch.setenv(
        "CONTEXTOR_MCP_SERVER_ROLE",
        role,
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_TRANSPORT",
        transport,
    )
    monkeypatch.setattr(
        server,
        "_MCP_BOOTSTRAP_TRANSPORT",
        transport,
    )

    events = []

    def fail_guard():
        events.append("guard")
        raise guard.BackendJobError(
            "direct entry Job installation failed"
        )

    selected = (
        "protect_host_owned_mcp"
        if role == "host-owned"
        else "protect_persistent_backend"
    )
    monkeypatch.setattr(
        guard,
        selected,
        fail_guard,
    )
    monkeypatch.setattr(
        server,
        "_process_directory_from_environment",
        lambda: pytest.fail(
            "lifecycle started without Job"
        ),
    )

    with pytest.raises(
        guard.BackendJobError,
        match="direct entry",
    ):
        server.main()

    assert events == ["guard"]


def test_failed_host_owned_cleanup_preserves_root_record(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        server.sys,
        "platform",
        "linux",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_SERVER_ROLE",
        "host-owned",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_TRANSPORT",
        "stdio",
    )
    monkeypatch.delenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        raising=False,
    )
    monkeypatch.setattr(
        server,
        "_MCP_BOOTSTRAP_TRANSPORT",
        "stdio",
    )

    root_record = tmp_path / "server-root.json"
    actions = []

    monkeypatch.setattr(
        server,
        "_process_directory_from_environment",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        server,
        "_cleanup_orphaned_processes",
        lambda directory: actions.append("orphan"),
    )
    monkeypatch.setattr(
        server,
        "_register_server_root",
        lambda directory, role: root_record,
    )

    def fail_cleanup(*_args):
        actions.append("cleanup")
        raise RuntimeError(
            "registered child cleanup unresolved"
        )

    monkeypatch.setattr(
        server,
        "_shutdown_mcp_owned_processes",
        fail_cleanup,
    )
    monkeypatch.setattr(
        server,
        "remove_record",
        lambda path: pytest.fail(
            "failed cleanup discarded server root"
        ),
    )
    monkeypatch.setattr(
        server.atexit,
        "register",
        lambda callback: None,
    )

    async def fake_stdio():
        actions.append("stdio")

    monkeypatch.setattr(
        server.mcp,
        "run_stdio_async",
        fake_stdio,
    )

    with pytest.raises(
        RuntimeError,
        match="cleanup unresolved",
    ):
        server.main()

    assert actions == [
        "orphan",
        "stdio",
        "cleanup",
    ]
    assert (
        "CONTEXTOR_MCP_PROCESS_REGISTRY"
        not in server.os.environ
    )

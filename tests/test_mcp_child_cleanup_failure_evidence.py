from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

import contextor.mcp_backend_control as control
import contextor.mcp_server as server


def _owner(tmp_path):
    return SimpleNamespace(
        pid=500,
        creation_time=123456789,
        process_registry=str(tmp_path),
    )


def _child():
    return {
        "pid": 501,
        "parent_pid": 500,
        "parent_creation_time": 123456789,
        "executable": r"C:\Python\python.exe",
        "creation_time": 123456790,
    }


def test_backend_failed_child_termination_retains_record(
    tmp_path,
    monkeypatch,
):
    owner = _owner(tmp_path)
    path = tmp_path / "child.json"
    child = _child()

    monkeypatch.setattr(
        control,
        "read_records",
        lambda directory: [(path, child)],
    )
    monkeypatch.setattr(
        control,
        "terminate_or_confirm_registered_process",
        lambda record: False,
    )
    monkeypatch.setattr(
        control,
        "remove_record",
        lambda path: pytest.fail(
            "failed child termination erased evidence"
        ),
    )

    with pytest.raises(
        control.BackendControlError,
        match="not confirmed",
    ):
        control._cleanup_owned_registry_children(owner)


def test_backend_successful_child_termination_removes_record(
    tmp_path,
    monkeypatch,
):
    owner = _owner(tmp_path)
    path = tmp_path / "child.json"
    child = _child()
    removed = []

    monkeypatch.setattr(
        control,
        "read_records",
        lambda directory: [(path, child)],
    )
    monkeypatch.setattr(
        control,
        "terminate_or_confirm_registered_process",
        lambda record: True,
    )
    monkeypatch.setattr(
        control,
        "remove_record",
        lambda target: removed.append(target),
    )

    control._cleanup_owned_registry_children(owner)

    assert removed == [path]


def test_mcp_server_failed_owned_child_retains_record(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "child.json"
    child = _child()

    monkeypatch.setattr(
        server, "sys_platform_is_windows", lambda: True
    )
    monkeypatch.setattr(
        server,
        "classify_registered_windows_parent",
        lambda record: "PARENT_ALIVE",
    )
    monkeypatch.setattr(
        server,
        "read_records",
        lambda directory: [(path, child)],
    )
    monkeypatch.setattr(
        server,
        "terminate_or_confirm_registered_process",
        lambda record: False,
    )
    monkeypatch.setattr(
        server,
        "remove_record",
        lambda target: pytest.fail(
            "failed owned-child termination erased evidence"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="not confirmed",
    ):
        server._cleanup_owned_processes(tmp_path, 500)


def test_mcp_server_successful_owned_child_cleanup(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "child.json"
    child = _child()

    monkeypatch.setattr(
        server, "sys_platform_is_windows", lambda: True
    )
    monkeypatch.setattr(
        server,
        "classify_registered_windows_parent",
        lambda record: "PARENT_ALIVE",
    )
    removed = []

    monkeypatch.setattr(
        server,
        "read_records",
        lambda directory: [(path, child)],
    )
    monkeypatch.setattr(
        server,
        "terminate_or_confirm_registered_process",
        lambda record: True,
    )
    monkeypatch.setattr(
        server,
        "remove_record",
        lambda target: removed.append(target),
    )

    server._cleanup_owned_processes(tmp_path, 500)

    assert removed == [path]


def test_mcp_server_failed_orphan_cleanup_retains_record(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "orphan.json"
    child = _child()

    monkeypatch.setattr(
        server, "sys_platform_is_windows", lambda: True
    )
    monkeypatch.setattr(
        server,
        "classify_registered_windows_process",
        lambda record: "ALIVE_MATCH",
    )
    monkeypatch.setattr(
        server,
        "classify_registered_windows_parent",
        lambda record: "ORPHAN",
    )
    monkeypatch.setattr(
        server,
        "read_records",
        lambda directory: [(path, child)],
    )
    monkeypatch.setattr(
        server,
        "record_matches_process",
        lambda record: True,
    )
    monkeypatch.setattr(
        server,
        "process_identity",
        lambda pid: (None, None, False),
    )
    monkeypatch.setattr(
        server,
        "terminate_or_confirm_registered_process",
        lambda record: False,
    )
    monkeypatch.setattr(
        server,
        "remove_record",
        lambda target: pytest.fail(
            "failed orphan termination erased evidence"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="not confirmed",
    ):
        server._cleanup_orphaned_processes(tmp_path)


def test_failed_child_cleanup_blocks_backend_stop_success(
    tmp_path,
    monkeypatch,
):
    owner = _owner(tmp_path)
    owner.to_dict = lambda: {
        "pid": owner.pid,
        "executable": r"C:\Python\python.exe",
        "creation_time": owner.creation_time,
    }

    monkeypatch.setattr(
        control,
        "_BackendControlLock",
        lambda *args, **kwargs: nullcontext(),
    )
    monkeypatch.setattr(
        control,
        "read_backend_record",
        lambda: owner,
    )
    monkeypatch.setattr(
        control,
        "_backend_owner_identity_matches",
        lambda record: True,
    )
    monkeypatch.setattr(
        control,
        "terminate_registered_process",
        lambda record: True,
    )
    monkeypatch.setattr(
        control,
        "_wait_for_owner_exit",
        lambda record, *, timeout: True,
    )
    monkeypatch.setattr(
        control,
        "_cleanup_owned_registry_children",
        lambda record: (_ for _ in ()).throw(
            control.BackendControlError(
                "child termination was not confirmed"
            )
        ),
    )
    monkeypatch.setattr(
        control,
        "remove_backend_record_if_exact",
        lambda record: pytest.fail(
            "backend stop discarded unresolved child evidence"
        ),
    )

    with pytest.raises(
        control.BackendControlError,
        match="not confirmed",
    ):
        control.stop_backend()


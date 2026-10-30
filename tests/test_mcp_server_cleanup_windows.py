from __future__ import annotations

from pathlib import Path

import pytest

import contextor.mcp_server as server


def _record(pid, parent_pid=500, parent_creation=111):
    return {
        "pid": pid,
        "parent_pid": parent_pid,
        "parent_creation_time": parent_creation,
        "creation_time": 100000 + pid,
        "executable": r"C:\Contextor\python.exe",
    }


@pytest.fixture
def cleanup(monkeypatch, tmp_path):
    records = {}
    removed = []
    terminated = []
    process_states = {}
    parent_states = {}

    monkeypatch.setattr(
        server, "sys_platform_is_windows", lambda: True
    )

    monkeypatch.setattr(
        server,
        "read_records",
        lambda directory: list(records.items()),
    )
    monkeypatch.setattr(
        server,
        "remove_record",
        lambda path: (
            removed.append(path),
            records.pop(path, None),
        ),
    )
    monkeypatch.setattr(
        server,
        "classify_registered_windows_process",
        lambda record: process_states.get(
            record["pid"], "ALIVE_MATCH"
        ),
    )
    monkeypatch.setattr(
        server,
        "classify_registered_windows_parent",
        lambda record: parent_states.get(
            record["pid"], "ORPHAN"
        ),
    )
    monkeypatch.setattr(
        server,
        "terminate_or_confirm_registered_process",
        lambda record: (
            terminated.append(record["pid"]) or True
        ),
    )

    def add(pid, parent_pid=500, parent_creation=111):
        path = tmp_path / f"{pid}.json"
        records[path] = _record(
            pid,
            parent_pid,
            parent_creation,
        )
        return path

    return (
        add,
        records,
        removed,
        terminated,
        process_states,
        parent_states,
    )


def test_dead_orphan_record_is_removed_without_termination(
    cleanup,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup
    path = add(501)
    states[501] = "DEAD"

    server._cleanup_orphaned_processes(tmp_path)

    assert path in removed
    assert records == {}
    assert terminated == []


def test_unknown_child_blocks_cleanup(
    cleanup,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup
    path = add(501)
    states[501] = "UNKNOWN"

    with pytest.raises(RuntimeError, match="not confirmed"):
        server._cleanup_orphaned_processes(tmp_path)

    assert path in records
    assert removed == []
    assert terminated == []


def test_parent_unknown_blocks_orphan_cleanup(
    cleanup,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup
    path = add(501)
    parents[501] = "UNKNOWN"

    with pytest.raises(RuntimeError, match="not confirmed"):
        server._cleanup_orphaned_processes(tmp_path)

    assert path in records
    assert terminated == []


def test_live_parent_is_not_terminated(
    cleanup,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup
    path = add(501)
    parents[501] = "PARENT_ALIVE"

    server._cleanup_orphaned_processes(tmp_path)

    assert path in records
    assert terminated == []
    assert removed == []


def test_orphan_is_terminated_and_removed(
    cleanup,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup
    path = add(501)

    server._cleanup_orphaned_processes(tmp_path)

    assert path in removed
    assert terminated == [501]
    assert records == {}


def test_failed_orphan_resolution_retains_record(
    cleanup,
    monkeypatch,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup
    path = add(501)

    monkeypatch.setattr(
        server,
        "terminate_or_confirm_registered_process",
        lambda record: False,
    )

    with pytest.raises(RuntimeError, match="not confirmed"):
        server._cleanup_orphaned_processes(tmp_path)

    assert path in records
    assert removed == []


def test_identity_mismatch_requires_safe_resolution(
    cleanup,
    monkeypatch,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup
    path = add(501)
    states[501] = "IDENTITY_MISMATCH"

    monkeypatch.setattr(
        server,
        "terminate_or_confirm_registered_process",
        lambda record: False,
    )

    with pytest.raises(RuntimeError, match="not confirmed"):
        server._cleanup_orphaned_processes(tmp_path)

    assert path in records
    assert removed == []


def test_identity_mismatch_proven_gone_removes_record(
    cleanup,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup
    path = add(501)
    states[501] = "IDENTITY_MISMATCH"

    server._cleanup_orphaned_processes(tmp_path)

    assert path in removed
    assert terminated == [501]


def test_four_level_registered_tree_is_fully_swept(
    cleanup,
    monkeypatch,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup

    # Reverse ordering requires more than two passes.
    for pid, parent in (
        (504, 503),
        (503, 502),
        (502, 501),
        (501, 500),
    ):
        add(pid, parent)

    def parent_state(record):
        if record["parent_pid"] in {
            entry["pid"] for entry in records.values()
        }:
            return "PARENT_ALIVE"
        return "ORPHAN"

    monkeypatch.setattr(
        server,
        "classify_registered_windows_parent",
        parent_state,
    )

    server._cleanup_orphaned_processes(tmp_path)

    assert terminated == [501, 502, 503, 504]
    assert records == {}
    assert len(removed) == 4


def test_owned_child_requires_exact_parent_generation(
    cleanup,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup
    good = add(501)
    stale = add(502)
    other = add(503, parent_pid=800)

    parents[501] = "PARENT_ALIVE"
    parents[502] = "ORPHAN"

    server._cleanup_owned_processes(tmp_path, 500)

    assert terminated == [501]
    assert good in removed
    assert stale in records
    assert other in records


def test_owned_unknown_parent_blocks_cleanup(
    cleanup,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup
    path = add(501)
    parents[501] = "UNKNOWN"

    with pytest.raises(RuntimeError, match="not confirmed"):
        server._cleanup_owned_processes(tmp_path, 500)

    assert path in records
    assert removed == []
    assert terminated == []


def test_owned_already_dead_child_is_resolved(
    cleanup,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup
    path = add(501)
    states[501] = "DEAD"
    parents[501] = "PARENT_ALIVE"

    server._cleanup_owned_processes(tmp_path, 500)

    assert path in removed
    assert terminated == [501]


def test_owned_failed_resolution_retains_record(
    cleanup,
    monkeypatch,
    tmp_path,
):
    add, records, removed, terminated, states, parents = cleanup
    path = add(501)
    parents[501] = "PARENT_ALIVE"

    monkeypatch.setattr(
        server,
        "terminate_or_confirm_registered_process",
        lambda record: False,
    )

    with pytest.raises(RuntimeError, match="not confirmed"):
        server._cleanup_owned_processes(tmp_path, 500)

    assert path in records
    assert removed == []


@pytest.mark.parametrize(
    "owner_pid",
    [None, False, 0, -1, 0x100000000],
)
def test_invalid_owned_parent_pid_is_rejected(
    cleanup,
    tmp_path,
    owner_pid,
):
    with pytest.raises(RuntimeError, match="invalid"):
        server._cleanup_owned_processes(tmp_path, owner_pid)


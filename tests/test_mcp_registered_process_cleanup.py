from __future__ import annotations

import pytest

from contextor import mcp_process_registry as registry


RECORD = {
    "pid": 2500,
    "creation_time": 123456789,
    "executable": r"C:\Contextor\.venv\Scripts\python.exe",
}


@pytest.fixture
def windows_cleanup(monkeypatch):
    monkeypatch.setattr(
        registry,
        "sys_platform_is_windows",
        lambda: True,
    )


def test_already_dead_requires_no_termination(
    windows_cleanup,
    monkeypatch,
):
    monkeypatch.setattr(
        registry,
        "classify_registered_windows_process",
        lambda record: "DEAD",
    )
    monkeypatch.setattr(
        registry,
        "terminate_registered_process",
        lambda record: pytest.fail(
            "dead process was terminated"
        ),
    )

    assert registry.terminate_or_confirm_registered_process(
        RECORD
    )


def test_live_matching_process_is_terminated(
    windows_cleanup,
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        registry,
        "classify_registered_windows_process",
        lambda record: "ALIVE_MATCH",
    )
    monkeypatch.setattr(
        registry,
        "terminate_registered_process",
        lambda record: calls.append(record) or True,
    )

    assert registry.terminate_or_confirm_registered_process(
        RECORD
    )
    assert calls == [RECORD]


def test_unknown_never_terminates(
    windows_cleanup,
    monkeypatch,
):
    monkeypatch.setattr(
        registry,
        "classify_registered_windows_process",
        lambda record: "UNKNOWN",
    )
    monkeypatch.setattr(
        registry,
        "terminate_registered_process",
        lambda record: pytest.fail(
            "unknown identity was terminated"
        ),
    )

    assert not registry.terminate_or_confirm_registered_process(
        RECORD
    )


def test_live_process_exits_before_termination(
    windows_cleanup,
    monkeypatch,
):
    states = iter([
        "ALIVE_MATCH",
        "DEAD",
    ])

    monkeypatch.setattr(
        registry,
        "classify_registered_windows_process",
        lambda record: next(states),
    )
    monkeypatch.setattr(
        registry,
        "terminate_registered_process",
        lambda record: False,
    )

    assert registry.terminate_or_confirm_registered_process(
        RECORD
    )


def test_pid_reuse_clears_old_identity_without_killing_new(
    windows_cleanup,
    monkeypatch,
):
    monkeypatch.setattr(
        registry,
        "classify_registered_windows_process",
        lambda record: "IDENTITY_MISMATCH",
    )
    monkeypatch.setattr(
        registry,
        "probe_process_identity",
        lambda pid: registry.ProcessIdentityProbe(
            "alive",
            r"C:\Other\python.exe",
            123456790,
        ),
    )
    monkeypatch.setattr(
        registry,
        "terminate_registered_process",
        lambda record: pytest.fail(
            "replacement PID was targeted"
        ),
    )

    assert registry.terminate_or_confirm_registered_process(
        RECORD
    )


def test_same_creation_different_image_is_unresolved(
    windows_cleanup,
    monkeypatch,
):
    monkeypatch.setattr(
        registry,
        "classify_registered_windows_process",
        lambda record: "IDENTITY_MISMATCH",
    )
    monkeypatch.setattr(
        registry,
        "probe_process_identity",
        lambda pid: registry.ProcessIdentityProbe(
            "alive",
            r"C:\Other\python.exe",
            RECORD["creation_time"],
        ),
    )

    assert not registry.terminate_or_confirm_registered_process(
        RECORD
    )


def test_failed_termination_with_unknown_reprobe_is_unresolved(
    windows_cleanup,
    monkeypatch,
):
    states = iter([
        "ALIVE_MATCH",
        "UNKNOWN",
    ])

    monkeypatch.setattr(
        registry,
        "classify_registered_windows_process",
        lambda record: next(states),
    )
    monkeypatch.setattr(
        registry,
        "terminate_registered_process",
        lambda record: False,
    )

    assert not registry.terminate_or_confirm_registered_process(
        RECORD
    )


def test_failed_termination_with_reused_pid_is_safe(
    windows_cleanup,
    monkeypatch,
):
    states = iter([
        "ALIVE_MATCH",
        "IDENTITY_MISMATCH",
    ])

    monkeypatch.setattr(
        registry,
        "classify_registered_windows_process",
        lambda record: next(states),
    )
    monkeypatch.setattr(
        registry,
        "probe_process_identity",
        lambda pid: registry.ProcessIdentityProbe(
            "alive",
            r"C:\Other\python.exe",
            123456791,
        ),
    )
    monkeypatch.setattr(
        registry,
        "terminate_registered_process",
        lambda record: False,
    )

    assert registry.terminate_or_confirm_registered_process(
        RECORD
    )


def test_pid_reuse_without_creation_evidence_is_unresolved(
    windows_cleanup,
    monkeypatch,
):
    monkeypatch.setattr(
        registry,
        "classify_registered_windows_process",
        lambda record: "IDENTITY_MISMATCH",
    )
    monkeypatch.setattr(
        registry,
        "probe_process_identity",
        lambda pid: registry.ProcessIdentityProbe(
            "alive",
            r"C:\Other\python.exe",
            None,
        ),
    )

    assert not registry.terminate_or_confirm_registered_process(
        RECORD
    )


def test_nonwindows_preserves_existing_termination(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        registry,
        "sys_platform_is_windows",
        lambda: False,
    )
    monkeypatch.setattr(
        registry,
        "terminate_registered_process",
        lambda record: calls.append(record) or True,
    )

    assert registry.terminate_or_confirm_registered_process(
        RECORD
    )
    assert calls == [RECORD]


def test_backend_cleanup_confirms_dead_child_without_termination(
    monkeypatch,
    tmp_path,
):
    import contextor.mcp_backend_control as control

    child = {
        **RECORD,
        "parent_pid": 500,
        "parent_creation_time": 123456788,
    }
    path = tmp_path / "child.json"

    class Owner:
        pid = 500
        creation_time = 123456788
        process_registry = str(tmp_path)

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

    control._cleanup_owned_registry_children(Owner())

    assert removed == [path]


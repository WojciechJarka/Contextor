from __future__ import annotations

import pytest

from contextor import mcp_process_registry as registry


RECORD = {
    "pid": 501,
    "parent_pid": 500,
    "parent_creation_time": 123456789,
    "creation_time": 123456790,
    "executable": r"C:\Python\python.exe",
}


@pytest.fixture
def parent_probe(monkeypatch):
    monkeypatch.setattr(
        registry, "sys_platform_is_windows", lambda: True
    )

    def set_probe(state, creation=None):
        monkeypatch.setattr(
            registry,
            "probe_process_identity",
            lambda pid: registry.ProcessIdentityProbe(
                state,
                None,
                creation,
            ),
        )

    return set_probe


def test_live_exact_parent(parent_probe):
    parent_probe("alive", 123456789)
    assert registry.classify_registered_windows_parent(
        RECORD
    ) == "PARENT_ALIVE"


def test_dead_parent_is_orphan(parent_probe):
    parent_probe("dead")
    assert registry.classify_registered_windows_parent(
        RECORD
    ) == "ORPHAN"


def test_reused_parent_pid_is_orphan(parent_probe):
    parent_probe("alive", 123456791)
    assert registry.classify_registered_windows_parent(
        RECORD
    ) == "ORPHAN"


@pytest.mark.parametrize(
    "creation",
    [None, False, 0, -1, "123456789"],
)
def test_unverified_actual_creation_is_unknown(
    parent_probe,
    creation,
):
    parent_probe("alive", creation)
    assert registry.classify_registered_windows_parent(
        RECORD
    ) == "UNKNOWN"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("parent_pid", None),
        ("parent_pid", False),
        ("parent_pid", 0),
        ("parent_pid", -1),
        ("parent_pid", 0x100000000),
        ("parent_creation_time", None),
        ("parent_creation_time", False),
        ("parent_creation_time", 0),
        ("parent_creation_time", "123456789"),
    ],
)
def test_invalid_parent_identity_is_unknown(
    parent_probe,
    field,
    value,
):
    parent_probe("alive", 123456789)
    record = {**RECORD, field: value}

    assert registry.classify_registered_windows_parent(
        record
    ) == "UNKNOWN"


def test_unknown_parent_probe_is_unknown(parent_probe):
    parent_probe("unknown")
    assert registry.classify_registered_windows_parent(
        RECORD
    ) == "UNKNOWN"


def test_probe_error_is_unknown(parent_probe, monkeypatch):
    monkeypatch.setattr(
        registry,
        "probe_process_identity",
        lambda pid: (_ for _ in ()).throw(
            OSError("access denied")
        ),
    )

    assert registry.classify_registered_windows_parent(
        RECORD
    ) == "UNKNOWN"


def test_nonwindows_does_not_claim_parent_identity(
    monkeypatch,
):
    monkeypatch.setattr(
        registry, "sys_platform_is_windows", lambda: False
    )

    assert registry.classify_registered_windows_parent(
        RECORD
    ) == "UNKNOWN"


from __future__ import annotations

import pytest

from contextor import mcp_process_registry as registry


IMAGE = r"C:\Contextor\.venv\Scripts\python.exe"

RECORD = {
    "pid": 2500,
    "creation_time": 123456789,
    "executable": IMAGE,
}


@pytest.fixture
def windows_probe(monkeypatch):
    monkeypatch.setattr(
        registry,
        "sys_platform_is_windows",
        lambda: True,
    )

    def set_probe(state, image=IMAGE, creation=123456789):
        monkeypatch.setattr(
            registry,
            "probe_process_identity",
            lambda _pid: registry.ProcessIdentityProbe(
                state,
                image,
                creation,
            ),
        )

    return set_probe


def test_exact_live_identity_is_match(windows_probe):
    windows_probe("alive")

    assert registry.classify_registered_windows_process(
        RECORD
    ) == "ALIVE_MATCH"


def test_case_and_separator_normalization(windows_probe):
    windows_probe(
        "alive",
        image="c:/CONTEXTOR/.venv/SCRIPTS/PYTHON.EXE",
    )

    assert registry.classify_registered_windows_process(
        RECORD
    ) == "ALIVE_MATCH"


def test_dead_process_is_dead(windows_probe):
    windows_probe("dead", None, None)

    assert registry.classify_registered_windows_process(
        RECORD
    ) == "DEAD"


def test_reused_pid_is_identity_mismatch(windows_probe):
    windows_probe(
        "alive",
        creation=123456790,
    )

    assert registry.classify_registered_windows_process(
        RECORD
    ) == "IDENTITY_MISMATCH"


def test_different_full_executable_is_mismatch(windows_probe):
    windows_probe(
        "alive",
        image=r"C:\Other\.venv315\Scripts\python.exe",
    )

    assert registry.classify_registered_windows_process(
        RECORD
    ) == "IDENTITY_MISMATCH"


@pytest.mark.parametrize(
    "state",
    ["unknown", "unexpected"],
)
def test_unconfirmed_liveness_is_unknown(
    windows_probe,
    state,
):
    windows_probe(state, None, None)

    assert registry.classify_registered_windows_process(
        RECORD
    ) == "UNKNOWN"


@pytest.mark.parametrize(
    "creation",
    [None, 0, False, -1, "123456789"],
)
def test_missing_or_invalid_actual_creation(
    windows_probe,
    creation,
):
    windows_probe(
        "alive",
        creation=creation,
    )

    assert registry.classify_registered_windows_process(
        RECORD
    ) == "UNKNOWN"


@pytest.mark.parametrize(
    "image",
    [None, "", "python.exe", r"\Contextor\python.exe"],
)
def test_missing_or_invalid_actual_image(
    windows_probe,
    image,
):
    windows_probe(
        "alive",
        image=image,
    )

    assert registry.classify_registered_windows_process(
        RECORD
    ) == "UNKNOWN"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("creation_time", None),
        ("creation_time", False),
        ("creation_time", 0),
        ("creation_time", "123456789"),
        ("executable", ""),
        ("executable", None),
        ("executable", "python.exe"),
        ("executable", r"\Contextor\python.exe"),
    ],
)
def test_invalid_record_identity_is_unknown(
    windows_probe,
    field,
    value,
):
    windows_probe("alive")

    candidate = {
        **RECORD,
        field: value,
    }

    assert registry.classify_registered_windows_process(
        candidate
    ) == "UNKNOWN"


@pytest.mark.parametrize(
    "pid",
    [None, False, True, 0, -1, "2500", 0x100000000],
)
def test_invalid_pid_never_probes(
    windows_probe,
    monkeypatch,
    pid,
):
    def forbidden_probe(_pid):
        pytest.fail(
            "invalid PID was probed"
        )

    monkeypatch.setattr(
        registry,
        "probe_process_identity",
        forbidden_probe,
    )

    candidate = {
        **RECORD,
        "pid": pid,
    }

    assert registry.classify_registered_windows_process(
        candidate
    ) == "UNKNOWN"


def test_unknown_windows_probe_failure_is_closed(
    windows_probe,
    monkeypatch,
):
    monkeypatch.setattr(
        registry,
        "probe_process_identity",
        lambda _pid: (_ for _ in ()).throw(
            OSError("query unavailable")
        ),
    )

    assert registry.classify_registered_windows_process(
        RECORD
    ) == "UNKNOWN"


def test_nonwindows_does_not_claim_windows_identity(
    monkeypatch,
):
    monkeypatch.setattr(
        registry,
        "sys_platform_is_windows",
        lambda: False,
    )

    monkeypatch.setattr(
        registry,
        "probe_process_identity",
        lambda _pid: pytest.fail(
            "Windows identity probe used on another platform"
        ),
    )

    assert registry.classify_registered_windows_process(
        RECORD
    ) == "UNKNOWN"


def test_classifier_does_not_terminate_process(
    windows_probe,
    monkeypatch,
):
    windows_probe("alive")

    monkeypatch.setattr(
        registry,
        "terminate_registered_process",
        lambda _record: pytest.fail(
            "classifier attempted process termination"
        ),
    )

    assert registry.classify_registered_windows_process(
        RECORD
    ) == "ALIVE_MATCH"


from __future__ import annotations

import ctypes
import json
import subprocess
from ctypes import wintypes

import pytest

from contextor import mcp_process_registry as registry


EXPECTED_IMAGE = r"C:\Contextor\.venv\Scripts\python.exe"

RECORD = {
    "pid": 1234,
    "executable": EXPECTED_IMAGE,
    "creation_time": 123456789,
}


class _FakeFunction:
    def __init__(self, callback):
        self.callback = callback
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        return self.callback(*args)


class _FakeKernel32:
    def __init__(
        self,
        *,
        open_result=17,
        image=EXPECTED_IMAGE,
        creation_time=123456789,
        first_wait=258,
        second_wait=0,
        image_ok=True,
        times_ok=True,
        term_ok=True,
    ):
        self.open_result = open_result
        self.image = image
        self.creation_time = creation_time
        self.first_wait = first_wait
        self.second_wait = second_wait
        self.image_ok = image_ok
        self.times_ok = times_ok
        self.term_ok = term_ok

        self.pid_owner = "original"
        self.handle_owner = "original"
        self.reuse_pid_after_open = False
        self.terminated_owner = None

        self.OpenProcess = _FakeFunction(self._open)
        self.WaitForSingleObject = _FakeFunction(self._wait)
        self.QueryFullProcessImageNameW = _FakeFunction(
            self._image
        )
        self.GetProcessTimes = _FakeFunction(self._times)
        self.TerminateProcess = _FakeFunction(
            self._terminate
        )
        self.CloseHandle = _FakeFunction(
            lambda handle: 1
        )

    def _open(self, access, inherit, pid):
        self.handle_owner = self.pid_owner

        if self.reuse_pid_after_open:
            self.pid_owner = "unrelated-new-process"

        return self.open_result

    def _wait(self, handle, timeout):
        if timeout == 0:
            return self.first_wait

        return self.second_wait

    def _image(self, handle, flags, buffer, size):
        if not self.image_ok:
            return 0

        buffer.value = self.image
        return 1

    def _times(
        self,
        handle,
        creation,
        exit_time,
        kernel,
        user,
    ):
        if not self.times_ok:
            return 0

        value = ctypes.cast(
            creation,
            ctypes.POINTER(wintypes.FILETIME),
        ).contents

        value.dwHighDateTime = (
            self.creation_time >> 32
        )
        value.dwLowDateTime = (
            self.creation_time & 0xFFFFFFFF
        )

        return 1

    def _terminate(self, handle, code):
        if self.term_ok:
            self.terminated_owner = self.handle_owner

        return int(self.term_ok)


@pytest.fixture
def fake_windows(monkeypatch):
    api = _FakeKernel32()

    monkeypatch.setattr(
        registry.ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: api,
        raising=False,
    )

    monkeypatch.setattr(
        registry,
        "sys_platform_is_windows",
        lambda: True,
    )

    return api


def test_exact_identity_terminates_via_one_handle(
    fake_windows,
):
    assert registry.terminate_registered_process(
        RECORD
    )

    assert fake_windows.OpenProcess.calls == [
        (0x00101001, False, 1234)
    ]

    assert fake_windows.TerminateProcess.calls == [
        (17, 1)
    ]

    assert fake_windows.CloseHandle.calls == [
        (17,)
    ]

    assert fake_windows.WaitForSingleObject.calls == [
        (17, 0),
        (17, 2000),
    ]


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("pid", 0),
        ("pid", True),
        ("pid", 0x100000000),
        ("pid", -1),
        ("creation_time", None),
        ("creation_time", False),
        ("creation_time", 0),
        ("creation_time", 0x10000000000000000),
        ("executable", ""),
        ("executable", None),
        ("executable", "python.exe"),
        ("executable", r"\Contextor\python.exe"),
    ],
)
def test_invalid_identity_never_opens_process(
    fake_windows,
    field,
    bad_value,
):
    record = {
        **RECORD,
        field: bad_value,
    }

    assert not registry.terminate_registered_process(
        record
    )

    assert fake_windows.OpenProcess.calls == []
    assert fake_windows.TerminateProcess.calls == []


@pytest.mark.parametrize(
    "options",
    [
        {"open_result": 0},
        {
            "image":
                r"C:\Other\.venv315\Scripts\python.exe"
        },
        {"creation_time": 123456788},
        {"first_wait": 0},
        {"first_wait": 0xFFFFFFFF},
        {"image_ok": False},
        {"times_ok": False},
        {"term_ok": False},
        {"second_wait": 258},
        {"second_wait": 0xFFFFFFFF},
    ],
)
def test_identity_or_termination_failure_is_closed(
    monkeypatch,
    options,
):
    api = _FakeKernel32(**options)

    monkeypatch.setattr(
        registry.ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: api,
        raising=False,
    )

    monkeypatch.setattr(
        registry,
        "sys_platform_is_windows",
        lambda: True,
    )

    assert not registry.terminate_registered_process(
        RECORD
    )

    expected_closes = int(
        bool(api.open_result)
    )

    assert len(api.CloseHandle.calls) == expected_closes

    if (
        api.first_wait != 258
        or not api.image_ok
        or not api.times_ok
        or api.creation_time != RECORD["creation_time"]
        or api.image != EXPECTED_IMAGE
    ):
        assert api.TerminateProcess.calls == []


def test_all_identity_calls_use_original_handle(
    fake_windows,
):
    assert registry.terminate_registered_process(
        RECORD
    )

    assert len(fake_windows.OpenProcess.calls) == 1

    for function in (
        fake_windows.WaitForSingleObject,
        fake_windows.QueryFullProcessImageNameW,
        fake_windows.GetProcessTimes,
        fake_windows.TerminateProcess,
        fake_windows.CloseHandle,
    ):
        assert function.calls
        assert all(
            call[0] == 17
            for call in function.calls
        )


def test_pid_reuse_cannot_redirect_termination(
    fake_windows,
):
    fake_windows.reuse_pid_after_open = True

    assert registry.terminate_registered_process(
        RECORD
    )

    assert fake_windows.pid_owner == (
        "unrelated-new-process"
    )

    assert fake_windows.terminated_owner == "original"
    assert len(fake_windows.OpenProcess.calls) == 1


def test_windows_termination_never_calls_taskkill(
    fake_windows,
    monkeypatch,
):
    def forbidden_subprocess(*_args, **_kwargs):
        pytest.fail(
            "PID-based subprocess termination is forbidden"
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        forbidden_subprocess,
    )

    assert registry.terminate_registered_process(
        RECORD
    )


def test_failed_termination_preserves_registry_record(
    fake_windows,
    tmp_path,
):
    fake_windows.term_ok = False

    path = tmp_path / "process.json"
    path.write_text(
        json.dumps(RECORD),
        encoding="utf-8",
    )

    assert not registry.terminate_registered_record(
        path
    )

    assert path.is_file()
    assert json.loads(
        path.read_text(encoding="utf-8")
    ) == RECORD


def test_successful_termination_removes_registry_record(
    fake_windows,
    tmp_path,
):
    path = tmp_path / "process.json"
    path.write_text(
        json.dumps(RECORD),
        encoding="utf-8",
    )

    assert registry.terminate_registered_record(
        path
    )

    assert not path.exists()


def test_malformed_json_retains_legacy_cleanup_behavior(
    tmp_path,
):
    path = tmp_path / "process.json"
    path.write_text(
        "{not-json",
        encoding="utf-8",
    )

    assert not registry.terminate_registered_record(
        path
    )

    assert not path.exists()


def test_legacy_record_match_behavior_is_unchanged(
    monkeypatch,
):
    monkeypatch.setattr(
        registry,
        "process_identity",
        lambda _pid: (
            r"C:\Other\python.exe",
            123456789,
            True,
        ),
    )

    assert registry.record_matches_process(
        RECORD
    )


def test_posix_termination_path_is_preserved(
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
        "record_matches_process",
        lambda _record: True,
    )

    monkeypatch.setattr(
        registry.os,
        "kill",
        lambda pid, sig: calls.append(
            (pid, sig)
        ),
    )

    assert registry.terminate_registered_process(
        RECORD
    )

    assert calls == [
        (1234, registry.signal.SIGTERM)
    ]


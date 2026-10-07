from __future__ import annotations

import errno
import os
from ctypes import wintypes

import pytest

from contextor import mcp_process_registry as registry


class _FakeWinApiFunction:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args):
        return self.callback(*args)


class _FakeKernel32:
    def __init__(
        self,
        *,
        open_result=1,
        wait_result=258,
        image_result=0,
        times_result=0,
    ):
        self.closed_handles = []
        self.OpenProcess = _FakeWinApiFunction(lambda *_args: open_result)
        self.WaitForSingleObject = _FakeWinApiFunction(lambda *_args: wait_result)
        self.QueryFullProcessImageNameW = _FakeWinApiFunction(
            lambda *_args: image_result
        )
        self.GetProcessTimes = _FakeWinApiFunction(lambda *_args: times_result)
        self.CloseHandle = _FakeWinApiFunction(
            lambda handle: self.closed_handles.append(handle) or 1
        )


def _patch_windows_probe(monkeypatch, kernel32, *, last_error=0):
    monkeypatch.setattr(registry.ctypes, "WinDLL", lambda *_args, **_kwargs: kernel32, raising=False)
    monkeypatch.setattr(
        registry.ctypes,
        "get_last_error",
        lambda: last_error,
        raising=False,
    )


def test_probe_current_process_is_alive():
    result = registry.probe_process_identity(os.getpid())

    assert result.state == "alive"


def test_windows_invalid_process_error_is_dead(monkeypatch):
    kernel32 = _FakeKernel32(open_result=0)
    _patch_windows_probe(monkeypatch, kernel32, last_error=87)

    result = registry._windows_process_identity_probe(987654321)

    assert result.state == "dead"
    assert result.image is None
    assert result.creation_time is None
    assert kernel32.closed_handles == []


def test_windows_open_process_access_denied_is_unknown(monkeypatch):
    kernel32 = _FakeKernel32(open_result=0)
    _patch_windows_probe(monkeypatch, kernel32, last_error=5)

    result = registry._windows_process_identity_probe(1234)

    assert result.state == "unknown"
    assert kernel32.closed_handles == []


def test_windows_wait_failure_is_unknown_and_closes_handle(monkeypatch):
    kernel32 = _FakeKernel32(wait_result=0xFFFFFFFF)
    _patch_windows_probe(monkeypatch, kernel32)

    result = registry._windows_process_identity_probe(1234)

    assert result.state == "unknown"
    assert kernel32.closed_handles == [1]


@pytest.mark.parametrize(
    ("image_result", "times_result", "expected_image", "expected_creation_time"),
    [
        (0, 1, None, 123456789),
        (1, 0, "C:/Contextor/python.exe", None),
    ],
)
def test_windows_auxiliary_identity_failure_preserves_alive(
    monkeypatch,
    image_result,
    times_result,
    expected_image,
    expected_creation_time,
):
    kernel32 = _FakeKernel32(
        image_result=image_result,
        times_result=times_result,
    )
    if image_result:
        def set_image(_handle, _flags, buffer, _size):
            buffer.value = "C:/Contextor/python.exe"
            return 1

        kernel32.QueryFullProcessImageNameW = _FakeWinApiFunction(set_image)
    if times_result:
        def set_times(_handle, creation, _exit_time, _kernel, _user):
            filetime = registry.ctypes.cast(
                creation,
                registry.ctypes.POINTER(wintypes.FILETIME),
            ).contents
            filetime.dwHighDateTime = 0
            filetime.dwLowDateTime = 123456789
            return 1

        kernel32.GetProcessTimes = _FakeWinApiFunction(set_times)
    _patch_windows_probe(monkeypatch, kernel32)

    result = registry._windows_process_identity_probe(1234)

    assert result.state == "alive"
    assert result.image == expected_image
    assert result.creation_time == expected_creation_time
    assert kernel32.closed_handles == [1]


def test_posix_esrch_is_dead(monkeypatch):
    monkeypatch.setattr(registry, "sys_platform_is_windows", lambda: False)

    def missing_process(_pid, _signal):
        raise ProcessLookupError(errno.ESRCH, "no such process")

    monkeypatch.setattr(registry.os, "kill", missing_process)

    result = registry.probe_process_identity(987654321)

    assert result.state == "dead"
    assert result.image is None
    assert result.creation_time is None


def test_posix_eperm_is_alive(monkeypatch):
    monkeypatch.setattr(registry, "sys_platform_is_windows", lambda: False)

    def denied(_pid, _signal):
        raise PermissionError(errno.EPERM, "operation not permitted")

    monkeypatch.setattr(registry.os, "kill", denied)

    result = registry.probe_process_identity(987654321)

    assert result.state == "alive"
    assert result.creation_time is None


def test_ambiguous_posix_error_is_unknown(monkeypatch):
    monkeypatch.setattr(registry, "sys_platform_is_windows", lambda: False)

    def ambiguous(_pid, _signal):
        raise OSError(errno.EIO, "indeterminate process probe")

    monkeypatch.setattr(registry.os, "kill", ambiguous)

    result = registry.probe_process_identity(987654321)

    assert result.state == "unknown"


def test_legacy_process_identity_tuple_contract_is_unchanged(monkeypatch):
    expected = ("C:/Contextor/python.exe", 123456789, True)
    monkeypatch.setattr(registry, "sys_platform_is_windows", lambda: True)
    monkeypatch.setattr(
        registry,
        "_windows_process_identity",
        lambda _pid: expected,
    )

    assert registry.process_identity(1234) == expected


def test_legacy_record_match_semantics_are_unchanged(monkeypatch):
    monkeypatch.setattr(
        registry,
        "process_identity",
        lambda _pid: ("C:/Git/bin/GIT.EXE", 100, True),
    )
    assert registry.record_matches_process(
        {
            "pid": 1234,
            "executable": "C:/Other/git.exe",
            "creation_time": 100,
        }
    )

    monkeypatch.setattr(
        registry,
        "process_identity",
        lambda _pid: (None, None, True),
    )
    assert registry.record_matches_process(
        {
            "pid": 1234,
            "executable": "git.exe",
            "creation_time": 999,
        }
    )

    monkeypatch.setattr(
        registry,
        "process_identity",
        lambda _pid: ("C:/Git/bin/git.exe", 101, True),
    )
    assert not registry.record_matches_process(
        {
            "pid": 1234,
            "executable": "C:/Other/git.exe",
            "creation_time": 100,
        }
    )

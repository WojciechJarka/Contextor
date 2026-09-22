import dataclasses
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from contextor.mcp_backend_state import (
    BackendAlreadyRunning,
    BackendRecordError,
    PersistentBackendLease,
    backend_record_path,
    read_backend_record,
    remove_backend_record_if_exact,
)


def _acquire_backend(registry: Path) -> PersistentBackendLease:
    return PersistentBackendLease.acquire(
        host="127.0.0.1",
        port=8765,
        transport="streamable-http",
        process_registry=registry,
    )


def test_acquire_writes_durable_record_and_release_removes_it(
    tmp_path,
    monkeypatch,
):
    state_dir = tmp_path / "state"
    registry = tmp_path / "registry"
    monkeypatch.setenv(
        "CONTEXTOR_STATE_DIR",
        str(state_dir),
    )

    lease = _acquire_backend(registry)

    try:
        record = read_backend_record()

        assert backend_record_path() == (
            state_dir
            / "mcp_backend"
            / "backend.json"
        )
        assert record is not None
        assert record.schema_version == 1
        assert record.server_role == "persistent-backend"
        assert record.transport == "streamable-http"
        assert record.host == "127.0.0.1"
        assert record.port == 8765
        assert record.pid == os.getpid()
        assert Path(record.process_registry) == registry.resolve()
        assert record.instance_id
        assert record.started_at >= 0
        assert "token" not in record.to_dict()
    finally:
        lease.release()

    assert read_backend_record() is None


def test_same_process_backend_lease_is_singleton(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTEXTOR_STATE_DIR",
        str(tmp_path / "state"),
    )
    registry = tmp_path / "registry"
    first = _acquire_backend(registry)

    try:
        with pytest.raises(BackendAlreadyRunning):
            _acquire_backend(registry)
    finally:
        first.release()

    second = _acquire_backend(registry)
    second.release()


def test_cross_process_backend_lease_is_singleton_and_helper_is_cleaned_up(
    tmp_path,
    monkeypatch,
):
    state_dir = tmp_path / "state"
    registry = tmp_path / "registry"
    monkeypatch.setenv(
        "CONTEXTOR_STATE_DIR",
        str(state_dir),
    )

    helper_code = "\n".join(
        (
            "import sys",
            "from contextor.mcp_backend_state import PersistentBackendLease",
            "lease = PersistentBackendLease.acquire(",
            "    host='127.0.0.1',",
            "    port=8765,",
            "    transport='streamable-http',",
            "    process_registry=sys.argv[1],",
            ")",
            "try:",
            "    print('READY', flush=True)",
            "    sys.stdin.readline()",
            "finally:",
            "    lease.release()",
        )
    )
    child_env = os.environ.copy()
    child_env["CONTEXTOR_STATE_DIR"] = str(state_dir)
    helper = subprocess.Popen(
        [sys.executable, "-c", helper_code, str(registry)],
        cwd=Path(__file__).resolve().parents[1],
        env=child_env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    ready_line = queue.Queue()

    def read_helper_stdout():
        assert helper.stdout is not None
        ready_line.put(helper.stdout.readline())
        for _line in helper.stdout:
            pass

    stdout_reader = threading.Thread(
        target=read_helper_stdout,
        daemon=True,
    )
    stdout_reader.start()

    try:
        assert ready_line.get(timeout=5) == "READY\n"

        with pytest.raises(BackendAlreadyRunning):
            _acquire_backend(registry)
    finally:
        if helper.poll() is None:
            assert helper.stdin is not None
            helper.stdin.write("\n")
            helper.stdin.flush()

        try:
            helper.wait(timeout=5)
        except subprocess.TimeoutExpired:
            helper.terminate()
            try:
                helper.wait(timeout=5)
            except subprocess.TimeoutExpired:
                helper.kill()
                helper.wait(timeout=5)

        stdout_reader.join(timeout=1)
        helper_stderr = (
            helper.stderr.read()
            if helper.stderr is not None
            else ""
        )
        helper_result = {
            "stdout_reader_alive": stdout_reader.is_alive(),
            "stderr": helper_stderr,
        }

    assert helper.returncode == 0, helper_result
    assert read_backend_record() is None

    parent_lease = _acquire_backend(registry)
    parent_lease.release()


def test_malformed_backend_record_is_rejected(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTEXTOR_STATE_DIR",
        str(tmp_path / "state"),
    )
    path = backend_record_path()
    path.parent.mkdir(parents=True)
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(BackendRecordError):
        read_backend_record()


def test_backend_record_removal_requires_exact_owner(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTEXTOR_STATE_DIR",
        str(tmp_path / "state"),
    )
    lease = _acquire_backend(tmp_path / "registry")

    try:
        expected = lease.record
        other_owner = dataclasses.replace(
            expected,
            instance_id=f"{expected.instance_id}-other",
        )

        assert remove_backend_record_if_exact(other_owner) is False
        assert read_backend_record() == expected
        assert remove_backend_record_if_exact(expected) is True
        assert read_backend_record() is None
    finally:
        lease.release()

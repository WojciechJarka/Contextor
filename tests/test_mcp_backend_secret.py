import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time

import pytest

from contextor.mcp_backend_secret import (
    BackendSecretError,
    BackendSecretRecordError,
    _protect_windows,
    _unprotect_windows,
    backend_token_path,
    delete_backend_token,
    get_or_create_backend_token,
    read_backend_token,
    rotate_backend_token,
)


PYTHON_EXE = (
    Path(__file__).resolve().parents[1]
    / ".venv"
    / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
)


def _set_isolated_state(tmp_path, monkeypatch):
    state_root = tmp_path / "state"
    monkeypatch.setenv(
        "CONTEXTOR_STATE_DIR",
        str(state_root),
    )
    return state_root


def _assert_plaintext_absent(token, payload, message):
    if token.encode("utf-8") in payload:
        pytest.fail(message)


def test_backend_token_is_stable_and_stored_without_plaintext(
    tmp_path,
    monkeypatch,
):
    state_root = _set_isolated_state(tmp_path, monkeypatch)

    first = get_or_create_backend_token()
    second = get_or_create_backend_token()

    if not hmac.compare_digest(first, second):
        pytest.fail("get_or_create did not reuse the existing token")
    if len(first) < 32:
        pytest.fail("generated backend token is shorter than 32 characters")

    token_path = backend_token_path()
    if not token_path.is_file():
        pytest.fail("token record was not created")
    record_bytes = token_path.read_bytes()
    _assert_plaintext_absent(
        first,
        record_bytes,
        "plaintext token was persisted",
    )

    record = json.loads(record_bytes.decode("utf-8"))
    if os.name == "nt":
        if record.get("protection") != "windows-dpapi-current-user":
            pytest.fail("Windows token record is not DPAPI Current User protected")
    else:
        if record.get("protection") != "posix-user-file-0600":
            pytest.fail("POSIX token record has an unexpected protection label")
        directory_mode = stat.S_IMODE(token_path.parent.stat().st_mode)
        file_mode = stat.S_IMODE(token_path.stat().st_mode)
        if directory_mode != 0o700:
            pytest.fail("POSIX token directory permissions are not 0700")
        if file_mode != 0o600:
            pytest.fail("POSIX token file permissions are not 0600")

    if (state_root / "mcp_backend" / "backend.json").exists():
        pytest.fail("token API created a backend owner record")


@pytest.mark.skipif(os.name != "nt", reason="real DPAPI is Windows-only")
def test_windows_dpapi_roundtrip_uses_real_current_user_protection():
    payload = b"contextor-backend-dpapi-roundtrip-payload"

    ciphertext = _protect_windows(payload)
    plaintext = _unprotect_windows(ciphertext)

    if hmac.compare_digest(ciphertext, payload):
        pytest.fail("DPAPI ciphertext unexpectedly equals its plaintext")
    if not hmac.compare_digest(plaintext, payload):
        pytest.fail("DPAPI roundtrip did not recover the input payload")


def test_rotation_replaces_token_without_persisting_plaintext(
    tmp_path,
    monkeypatch,
):
    _set_isolated_state(tmp_path, monkeypatch)

    old_token = get_or_create_backend_token()
    new_token = rotate_backend_token()

    if hmac.compare_digest(new_token, old_token):
        pytest.fail("rotation did not generate a new backend token")
    current_token = read_backend_token()
    if current_token is None or not hmac.compare_digest(current_token, new_token):
        pytest.fail("rotated token was not made current")

    token_bytes = backend_token_path().read_bytes()
    _assert_plaintext_absent(
        old_token,
        token_bytes,
        "old plaintext token remains in the record",
    )
    if os.name == "nt":
        _assert_plaintext_absent(
            new_token,
            token_bytes,
            "new plaintext token appears in the Windows record",
        )


def test_malformed_record_fails_closed_for_read_and_get_or_create(
    tmp_path,
    monkeypatch,
):
    _set_isolated_state(tmp_path, monkeypatch)
    get_or_create_backend_token()
    backend_token_path().write_text("not-json", encoding="utf-8")

    with pytest.raises(BackendSecretRecordError):
        read_backend_token()
    with pytest.raises(BackendSecretRecordError):
        get_or_create_backend_token()


@pytest.mark.skipif(os.name != "nt", reason="DPAPI tampering is Windows-only")
def test_tampered_windows_dpapi_payload_fails_closed(
    tmp_path,
    monkeypatch,
):
    _set_isolated_state(tmp_path, monkeypatch)
    get_or_create_backend_token()

    token_path = backend_token_path()
    record = json.loads(token_path.read_text(encoding="utf-8"))
    protected = bytearray(
        base64.b64decode(record["protected_data"], validate=True)
    )
    if not protected:
        pytest.fail("DPAPI produced an empty protected payload")
    protected[0] ^= 0x01
    record["protected_data"] = base64.b64encode(protected).decode("ascii")
    token_path.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    with pytest.raises(BackendSecretError):
        read_backend_token()
    with pytest.raises(BackendSecretError):
        get_or_create_backend_token()


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission contract")
def test_posix_broad_token_file_permissions_fail_closed(
    tmp_path,
    monkeypatch,
):
    _set_isolated_state(tmp_path, monkeypatch)
    get_or_create_backend_token()
    backend_token_path().chmod(0o640)

    with pytest.raises(BackendSecretError):
        read_backend_token()
    with pytest.raises(BackendSecretError):
        get_or_create_backend_token()


def test_cross_process_first_create_is_serialized_and_stable(
    tmp_path,
    monkeypatch,
):
    state_root = _set_isolated_state(tmp_path, monkeypatch)
    barrier_root = tmp_path / "barrier"
    barrier_root.mkdir()
    start_path = barrier_root / "start"
    ready_paths = [barrier_root / "ready-1", barrier_root / "ready-2"]
    child_code = "\n".join(
        (
            "import hashlib, os, time",
            "from pathlib import Path",
            "from contextor.mcp_backend_secret import get_or_create_backend_token",
            "ready = Path(os.environ['CONTEXTOR_TEST_READY_PATH'])",
            "start = Path(os.environ['CONTEXTOR_TEST_START_PATH'])",
            "ready.write_text('ready', encoding='ascii')",
            "deadline = time.monotonic() + 20.0",
            "while not start.exists():",
            "    if time.monotonic() >= deadline:",
            "        raise SystemExit(3)",
            "    time.sleep(0.005)",
            "token = get_or_create_backend_token()",
            "print(hashlib.sha256(token.encode('utf-8')).hexdigest())",
        )
    )

    helpers = []
    hashes = []
    try:
        for ready_path in ready_paths:
            child_env = os.environ.copy()
            child_env["CONTEXTOR_STATE_DIR"] = str(state_root)
            child_env["CONTEXTOR_TEST_READY_PATH"] = str(ready_path)
            child_env["CONTEXTOR_TEST_START_PATH"] = str(start_path)
            helpers.append(
                subprocess.Popen(
                    [str(PYTHON_EXE), "-c", child_code],
                    cwd=Path(__file__).resolve().parents[1],
                    env=child_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                )
            )

        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            if all(path.is_file() for path in ready_paths):
                break
            if any(helper.poll() is not None for helper in helpers):
                break
            time.sleep(0.005)

        if not all(path.is_file() for path in ready_paths):
            pytest.fail("cross-process helpers did not reach the start barrier")

        start_path.write_text("go", encoding="ascii")

        for helper in helpers:
            try:
                stdout, _stderr = helper.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                pytest.fail("cross-process token helper timed out")
            if helper.returncode != 0:
                pytest.fail("cross-process token helper exited unsuccessfully")
            digest = stdout.strip()
            if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                pytest.fail("cross-process helper did not print only a SHA-256 digest")
            hashes.append(digest)

        if len(hashes) != 2 or not hmac.compare_digest(hashes[0], hashes[1]):
            pytest.fail("concurrent first-create helpers observed different tokens")

        parent_token = read_backend_token()
        if parent_token is None:
            pytest.fail("parent could not read the concurrently created token")
        parent_hash = hashlib.sha256(parent_token.encode("utf-8")).hexdigest()
        if any(not hmac.compare_digest(parent_hash, value) for value in hashes):
            pytest.fail("parent token hash did not match both helper hashes")
    finally:
        start_path.touch(exist_ok=True)
        for helper in helpers:
            if helper.poll() is None:
                helper.terminate()
        for helper in helpers:
            if helper.poll() is None:
                try:
                    helper.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    helper.kill()
                    helper.communicate(timeout=5)
            elif helper.stdout is not None and not helper.stdout.closed:
                helper.communicate()
        if any(helper.poll() is None for helper in helpers):
            pytest.fail("a cross-process token helper remained alive")


def test_delete_removes_only_the_secret_record(
    tmp_path,
    monkeypatch,
):
    _set_isolated_state(tmp_path, monkeypatch)
    get_or_create_backend_token()

    if delete_backend_token() is not True:
        pytest.fail("delete did not remove the existing secret record")
    if read_backend_token() is not None:
        pytest.fail("secret record remained readable after delete")
    if delete_backend_token() is not False:
        pytest.fail("delete did not report an already absent secret record")

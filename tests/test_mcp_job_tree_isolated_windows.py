"""Isolated Windows process-tree regression for backend-owned Job Objects."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from contextor import mcp_process_registry as registry


pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Real Windows Job Object integration test",
)


LEAF_CODE = """
import os
import sys
import time
from pathlib import Path

Path(sys.argv[1]).write_text(str(os.getpid()), encoding="ascii")
time.sleep(120)
"""


CHILD_CODE = """
import json
import os
import subprocess
import sys
import time
from pathlib import Path

root = Path(sys.argv[1])
flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
grandchild = subprocess.Popen(
    [sys.executable, str(root / "leaf.py"), str(root / "grandchild.pid")],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=flags,
)
(root / "child.json").write_text(
    json.dumps({"pid": os.getpid(), "grandchild_pid": grandchild.pid}),
    encoding="utf-8",
)
time.sleep(120)
"""


OWNER_CODE = """
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from contextor.mcp_backend_job import (
    protect_persistent_backend,
    require_live_outside_backend_job,
)

root = Path(sys.argv[1])
protect_persistent_backend()
flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
child = subprocess.Popen(
    [sys.executable, str(root / "child.py"), str(root)],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=flags,
)
limit = time.monotonic() + 15
while not (root / "grandchild.pid").exists():
    if child.poll() is not None:
        raise RuntimeError("child exited before grandchild startup")
    if time.monotonic() > limit:
        raise RuntimeError("grandchild did not start")
    time.sleep(0.05)

live = subprocess.Popen(
    [sys.executable, str(root / "leaf.py"), str(root / "live.pid")],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=flags | 0x01000000,
)
(root / "live_spawned.pid").write_text(str(live.pid), encoding="ascii")
require_live_outside_backend_job(live)
(root / "ready.json").write_text(
    json.dumps({"owner": os.getpid(), "child": child.pid,
                "grandchild": int((root / "grandchild.pid").read_text()),
                "live": live.pid}),
    encoding="utf-8",
)
limit = time.monotonic() + 120
while time.monotonic() < limit and not (root / "stop.owner").exists():
    time.sleep(0.05)
"""


def _wait_until(predicate, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


def _identity_record(pid):
    probe = registry.probe_process_identity(pid)
    assert probe.state == "alive", f"test process {pid}: {probe.state}"
    assert isinstance(probe.creation_time, int) and probe.creation_time > 0
    assert isinstance(probe.image, str) and probe.image
    return {
        "pid": pid,
        "creation_time": probe.creation_time,
        "executable": probe.image,
    }


def _recorded_identity_alive(record):
    probe = registry.probe_process_identity(record["pid"])
    return probe.state == "alive" and probe.creation_time == record["creation_time"]


def _recorded_identity_gone(record):
    probe = registry.probe_process_identity(record["pid"])
    return probe.state == "dead" or (
        probe.state == "alive"
        and isinstance(probe.creation_time, int)
        and probe.creation_time != record["creation_time"]
    )


def _read_pid(path):
    if not path.is_file():
        return None
    try:
        return int(path.read_text(encoding="ascii"))
    except (OSError, ValueError):
        return None


@pytest.mark.parametrize("shutdown", ["normal", "forced"])
def test_isolated_backend_job_kills_unregistered_child_and_grandchild_but_not_live_or_unrelated(
    tmp_path: Path, shutdown: str,
):
    for name, code in (
        ("leaf.py", LEAF_CODE),
        ("child.py", CHILD_CODE),
        ("owner.py", OWNER_CODE),
    ):
        (tmp_path / name).write_text(code, encoding="utf-8")

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(repo_root), env.get("PYTHONPATH", "")))
    )
    sentinel = subprocess.Popen(
        [sys.executable, str(tmp_path / "leaf.py"), str(tmp_path / "sentinel.pid")],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    owner = None
    identities = {}
    try:
        owner = subprocess.Popen(
            [sys.executable, str(tmp_path / "owner.py"), str(tmp_path)],
            cwd=str(repo_root),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=flags,
        )

        def ready_or_exited():
            return (tmp_path / "ready.json").is_file() or owner.poll() is not None

        assert _wait_until(ready_or_exited), "isolated Job owner readiness timeout"
        if owner.poll() is not None:
            detail = owner.stderr.read().decode("utf-8", errors="replace")
            pytest.fail(f"isolated Job owner startup failed: {detail}")

        identifiers = json.loads((tmp_path / "ready.json").read_text(encoding="utf-8"))
        assert identifiers["owner"] == owner.pid
        assert identifiers["child"] != identifiers["grandchild"]
        assert identifiers["live"] not in (
            identifiers["owner"], identifiers["child"], identifiers["grandchild"]
        )
        assert _wait_until(lambda: (tmp_path / "live.pid").is_file())
        assert _wait_until(lambda: (tmp_path / "sentinel.pid").is_file())

        for key in ("child", "grandchild", "live"):
            identities[key] = _identity_record(identifiers[key])
        identities["sentinel"] = _identity_record(sentinel.pid)

        assert all(_recorded_identity_alive(r) for r in identities.values())
        if shutdown == "normal":
            (tmp_path / "stop.owner").write_text("1", encoding="ascii")
        else:
            owner.terminate()
        owner.wait(timeout=8)

        assert _wait_until(
            lambda: _recorded_identity_gone(identities["child"])
            and _recorded_identity_gone(identities["grandchild"]),
            timeout=8,
        ), "backend Job Object left child or grandchild alive"
        assert _recorded_identity_alive(identities["live"]), "breakaway LIVE died"
        assert _recorded_identity_alive(identities["sentinel"]), "unrelated process died"
    finally:
        if owner is not None:
            if owner.poll() is None:
                owner.terminate()
            try:
                owner.wait(timeout=5)
            except subprocess.TimeoutExpired:
                owner.kill()
                owner.wait(timeout=5)
            if owner.stderr is not None:
                owner.stderr.close()

        if "live" not in identities:
            pid = _read_pid(tmp_path / "live_spawned.pid") or _read_pid(tmp_path / "live.pid")
            if pid is not None:
                probe = registry.probe_process_identity(pid)
                if probe.state == "alive" and probe.creation_time and probe.image:
                    identities["live"] = {
                        "pid": pid,
                        "creation_time": probe.creation_time,
                        "executable": probe.image,
                    }

        unresolved = []
        for key in ("live", "grandchild", "child"):
            record = identities.get(key)
            if record is not None and not registry.terminate_or_confirm_registered_process(record):
                unresolved.append(key)

        if sentinel.poll() is None:
            sentinel.terminate()
        try:
            sentinel.wait(timeout=5)
        except subprocess.TimeoutExpired:
            sentinel.kill()
            sentinel.wait(timeout=5)
        if unresolved:
            pytest.fail(f"isolated test-owned processes unresolved: {unresolved}")


"""Lifecycle and repository adapter for the canonical LIVE owner process."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from contextor.core.paths import repo_cache_dir
from contextor.core.repository_identity import require_repository_identity

from .ipc import CanonicalLiveServer, LIVE_PROTOCOL_VERSION, LiveEndpoint, LiveStateClient
from .store import load_snapshot, migrate_legacy_snapshot, read_metadata, save_snapshot


def endpoint_file(repo_path: str | Path) -> Path:
    return repo_cache_dir(repo_path) / "live_endpoint.json"


def _read_endpoint(repo_path: str | Path) -> LiveEndpoint | None:
    try:
        payload = json.loads(endpoint_file(repo_path).read_text(encoding="utf-8"))
        return LiveEndpoint(payload["host"], int(payload["port"]), payload["authkey_hex"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def connect(repo_path: str | Path) -> LiveStateClient | None:
    endpoint = _read_endpoint(repo_path)
    if endpoint is None:
        return None
    client = LiveStateClient(endpoint)
    try:
        status = client.ping()
        return (
            client
            if status.get("status") == "ok"
            and status.get("protocol_version") == LIVE_PROTOCOL_VERSION
            else None
        )
    except (OSError, EOFError, ConnectionError):
        return None


def connect_or_start(repo_path: str | Path, *, timeout: float = 10.0) -> LiveStateClient:
    root = Path(repo_path).resolve()
    existing = connect(root)
    if existing:
        return existing
    # A code update can leave a detached owner process behind.  It may answer
    # ping but not implement the current protocol. Ask it to stop before the
    # current runtime claims the endpoint file.
    stale_endpoint = _read_endpoint(root)
    if stale_endpoint is not None:
        try:
            LiveStateClient(stale_endpoint).request("shutdown")
        except (OSError, EOFError, ConnectionError, RuntimeError):
            pass
    target = endpoint_file(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    start_lock = target.with_name("live_service_start.lock")
    deadline = time.monotonic() + timeout
    owns_start = False
    while time.monotonic() < deadline:
        existing = connect(root)
        if existing:
            return existing
        try:
            descriptor = os.open(start_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(descriptor)
            owns_start = True
            break
        except FileExistsError:
            try:
                if time.time() - start_lock.stat().st_mtime > timeout:
                    start_lock.unlink()
            except FileNotFoundError:
                pass
            time.sleep(0.05)
    if not owns_start:
        raise TimeoutError(f"Could not claim Canonical LIVE startup for {root}")
    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(
            [sys.executable, "-m", "contextor.core.live_state.runtime", "--repo", str(root)],
            cwd=str(root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            client = connect(root)
            if client:
                return client
            time.sleep(0.05)
        raise TimeoutError(f"Canonical LIVE service did not start for {root}")
    finally:
        try:
            start_lock.unlink()
        except FileNotFoundError:
            pass


def _repository_updater(root: Path):
    identity = require_repository_identity(root)
    cache = repo_cache_dir(root)

    def update(state, file_path: str):
        from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
        from contextor.core.analysis.state_manager import FileStateManager
        from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

        manager = FileStateManager(str(cache))
        engine = IncrementalAnalysisEngine(
            state,
            PersistentIdentityRegistry(str(root)),
            manager,
            str(root),
        )
        delta = engine.update_file(file_path)
        manager.save(getattr(manager, "state_id", ""))
        save_snapshot(
            engine.state,
            cache,
            getattr(manager, "state_id", ""),
            writer="live-service",
            repo_id=identity.repo_id,
            root_path=identity.root_path,
        )
        return delta

    return update


def run_service(repo_path: str | Path) -> None:
    root = Path(repo_path).resolve()
    identity = require_repository_identity(root)
    cache = migrate_legacy_snapshot(root)
    loaded = load_snapshot(
        cache,
        expected_repo_id=identity.repo_id,
        expected_root_path=identity.root_path,
    )
    state = loaded[0] if loaded else None
    revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
    server = CanonicalLiveServer(
        state,
        revision=revision,
        updater=_repository_updater(root),
    )
    target = endpoint_file(root)
    temporary = target.with_suffix(f".{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(
            {
                "host": server.endpoint.host,
                "port": server.endpoint.port,
                "authkey_hex": server.endpoint.authkey_hex,
                "pid": os.getpid(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    os.replace(temporary, target)
    try:
        server.serve_forever()
    finally:
        try:
            target.unlink()
        except FileNotFoundError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    run_service(args.repo)


if __name__ == "__main__":
    main()

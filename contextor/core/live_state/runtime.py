"""Lifecycle and repository adapter for the canonical LIVE owner process."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from contextor.core.paths import repo_cache_dir
from contextor.core.repository_identity import (
    read_repository_identity,
    require_repository_identity,
)

from .ipc import CanonicalLiveServer, LIVE_PROTOCOL_VERSION, LiveEndpoint, LiveStateClient
from .store import load_snapshot, migrate_legacy_snapshot, read_metadata, save_snapshot


def _is_pid_alive(pid: int | None) -> bool:
    """Check if a process with the given PID is currently active."""
    if pid is None or pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        SYNCHRONIZE = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, int(pid)
        )
        if not handle:
            return False
        exit_code = ctypes.c_ulong()
        try:
            if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                STILL_ACTIVE = 259
                return exit_code.value == STILL_ACTIVE
            return False
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    else:
        try:
            os.kill(int(pid), 0)
            return True
        except OSError:
            return False


def _is_same_or_descendant_pid(child_pid: int | None, ancestor_pid: int | None) -> bool:
    if child_pid is None or ancestor_pid is None:
        return False
    if child_pid == ancestor_pid:
        return True
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        import ctypes.wintypes

        kernel32 = ctypes.windll.kernel32
        hSnapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
        if hSnapshot == -1 or not hSnapshot:
            return False
        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", ctypes.wintypes.DWORD),
                ("cntUsage", ctypes.wintypes.DWORD),
                ("th32ProcessID", ctypes.wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p),
                ("th32ModuleID", ctypes.wintypes.DWORD),
                ("cntThreads", ctypes.wintypes.DWORD),
                ("th32ParentProcessID", ctypes.wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", ctypes.wintypes.DWORD),
                ("szExeFile", ctypes.c_char * 260),
            ]
        parents: dict[int, int] = {}
        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
        if kernel32.Process32First(hSnapshot, ctypes.byref(pe)):
            while True:
                parents[pe.th32ProcessID] = pe.th32ParentProcessID
                if not kernel32.Process32Next(hSnapshot, ctypes.byref(pe)):
                    break
        kernel32.CloseHandle(hSnapshot)
        curr = child_pid
        for _ in range(10):
            parent = parents.get(curr)
            if not parent:
                break
            if parent == ancestor_pid:
                return True
            curr = parent
        return False
    except Exception:
        return False


def _terminate_pid_tree(pid: int | None) -> None:
    """Forcefully terminate a specific PID and its child process tree."""
    if pid is None or pid <= 0 or not _is_pid_alive(pid):
        return
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=5.0,
            )
        except Exception:
            pass
    else:
        try:
            os.kill(int(pid), 15)  # SIGTERM
        except OSError:
            pass


def endpoint_file(repo_path: str | Path) -> Path:
    return repo_cache_dir(repo_path) / "live_endpoint.json"


def _read_endpoint(repo_path: str | Path) -> LiveEndpoint | None:
    try:
        payload = json.loads(endpoint_file(repo_path).read_text(encoding="utf-8"))
        pid = int(payload["pid"]) if "pid" in payload and payload["pid"] is not None else None
        owner_pid = int(payload["owner_pid"]) if "owner_pid" in payload and payload["owner_pid"] is not None else None
        owner_token = str(payload["owner_token"]) if "owner_token" in payload and payload["owner_token"] is not None else None
        repo_id = str(payload["repo_id"]) if payload.get("repo_id") else None
        root_path = str(payload["root_path"]) if payload.get("root_path") else None
        return LiveEndpoint(
            payload["host"],
            int(payload["port"]),
            payload["authkey_hex"],
            pid=pid,
            owner_pid=owner_pid,
            owner_token=owner_token,
            repo_id=repo_id,
            root_path=root_path,
        )
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


def connect_existing_with_status(
    repo_path: str | Path,
    *,
    attempts: int = 3,
    retry_delay: float = 0.05,
) -> tuple[LiveStateClient | None, str]:
    """Reconnect briefly to an existing owner without starting a service."""
    root = Path(repo_path).resolve()
    expected = _read_endpoint(root)
    if expected is None:
        return None, "no_live_service"
    identity = read_repository_identity(root)
    if (
        identity is None
        or expected.repo_id != identity.repo_id
        or not expected.root_path
        or Path(expected.root_path).expanduser().resolve() != root
    ):
        return None, "endpoint_identity_unverified"

    total_attempts = max(1, attempts)
    for attempt in range(total_attempts):
        client = connect(root)
        if client is not None:
            current = _read_endpoint(root)
            if current != expected or client.endpoint != expected:
                return None, "owner_identity_changed"
            return client, "connected"
        if attempt + 1 < total_attempts:
            time.sleep(max(0.0, retry_delay))

    endpoint = _read_endpoint(root)
    if endpoint != expected:
        return None, "owner_identity_changed"
    if (
        endpoint is not None
        and endpoint.pid is not None
        and _is_pid_alive(endpoint.pid)
    ):
        return None, "transient_connection_failure"
    return None, "no_live_service"


CREATE_BREAKAWAY_FROM_JOB = 0x01000000


def _spawn_runtime_subprocess(
    cmd: list[str],
    cwd: Path | str,
    env: dict[str, str],
) -> subprocess.Popen:
    """Spawn the owner-scoped LIVE service subprocess with Job Object breakaway on Windows.

    On Windows, the primary spawn requests CREATE_BREAKAWAY_FROM_JOB | CREATE_NO_WINDOW
    so that host-container or launcher Job Objects do not unintentionally kill the
    owner-scoped LIVE service when the launcher exits. If the host Job Object explicitly
    forbids breakaway (OSError with winerror == 5), fall back exactly once to legacy
    creation flags (CREATE_NO_WINDOW).
    """
    if sys.platform != "win32":
        return subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0,
        )

    base_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    primary_flags = base_flags | CREATE_BREAKAWAY_FROM_JOB

    try:
        return subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=primary_flags,
        )
    except OSError as exc:
        if getattr(exc, "winerror", None) != 5:
            raise
        import logging

        logging.getLogger("contextor.core.live_state.runtime").info(
            "LIVE service spawn breakaway was rejected by host Job Object; "
            "falling back to inherited Job Object mode."
        )
        try:
            return subprocess.Popen(
                cmd,
                cwd=str(cwd),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=base_flags,
            )
        except Exception as fallback_exc:
            raise fallback_exc from exc


DEFAULT_CONNECT_TIMEOUT: float = 10.0
DEFAULT_COLD_START_TIMEOUT: float = 60.0
NORMAL_CONNECT_TIMEOUT = DEFAULT_CONNECT_TIMEOUT
COLD_START_INITIALIZATION_TIMEOUT = DEFAULT_COLD_START_TIMEOUT


def connect_or_start(
    repo_path: str | Path,
    *,
    owner_pid: int | None = None,
    owner_token: str | None = None,
    timeout: float = DEFAULT_CONNECT_TIMEOUT,
    cold_start_timeout: float = DEFAULT_COLD_START_TIMEOUT,
) -> LiveStateClient:
    root = Path(repo_path).resolve()
    existing_ep = _read_endpoint(root)
    existing = connect(root)
    if existing is not None and existing_ep is not None:
        # A. Matching owner token: same owner process reconnecting
        if (
            existing_ep.owner_token is not None
            and owner_token is not None
            and existing_ep.owner_token == owner_token
        ):
            return LiveStateClient(
                existing_ep,
                is_owner=True,
                service_pid=existing_ep.pid,
                owner_pid=existing_ep.owner_pid,
                owner_token=existing_ep.owner_token,
            )
        # B. Responsive endpoint with an owner_token (different or caller has none) -> unowned client
        if existing_ep.owner_token is not None:
            return LiveStateClient(
                existing_ep,
                is_owner=False,
                service_pid=existing_ep.pid,
                owner_pid=existing_ep.owner_pid,
                owner_token=existing_ep.owner_token,
            )
        # C. Responsive endpoint without owner_token:
        # If owner_pid is present and alive -> unowned client
        if existing_ep.owner_pid is not None and _is_pid_alive(existing_ep.owner_pid):
            return LiveStateClient(
                existing_ep,
                is_owner=False,
                service_pid=existing_ep.pid,
                owner_pid=existing_ep.owner_pid,
                owner_token=None,
            )
        # If owner_pid is None (legacy endpoint without token/pid) -> unowned client
        if existing_ep.owner_pid is None:
            return LiveStateClient(
                existing_ep,
                is_owner=False,
                service_pid=existing_ep.pid,
                owner_pid=None,
                owner_token=None,
            )
        # D. Proven orphan (owner_pid recorded and known dead, and no owner_token): stop orphan and clean up
        if existing_ep.owner_pid is not None and not _is_pid_alive(existing_ep.owner_pid):
            try:
                existing.request("shutdown", timeout=1.5)
            except (OSError, EOFError, ConnectionError, RuntimeError, TimeoutError):
                pass
            if existing_ep.pid and _is_pid_alive(existing_ep.pid):
                time.sleep(0.1)
                if _is_pid_alive(existing_ep.pid):
                    _terminate_pid_tree(existing_ep.pid)
            try:
                target = endpoint_file(root)
                current = _read_endpoint(root)
                if current is not None and current.pid == existing_ep.pid:
                    target.unlink()
            except (OSError, FileNotFoundError):
                pass

    # Clean up any stale unresponsive endpoint
    stale_endpoint = _read_endpoint(root)
    if stale_endpoint is not None:
        try:
            LiveStateClient(stale_endpoint).request("shutdown", timeout=1.5)
        except (OSError, EOFError, ConnectionError, RuntimeError, TimeoutError):
            pass

    target = endpoint_file(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    start_lock = target.with_name("live_service_start.lock")
    effective_startup_budget = max(timeout, cold_start_timeout)
    deadline = time.monotonic() + effective_startup_budget
    lock_fd = None
    while time.monotonic() < deadline:
        existing = connect(root)
        if existing:
            ep = _read_endpoint(root)
            is_owner = (
                owner_token is not None
                and ep is not None
                and ep.owner_token is not None
                and ep.owner_token == owner_token
            )
            return LiveStateClient(
                ep or existing.endpoint,
                is_owner=is_owner,
                service_pid=ep.pid if ep else None,
                owner_pid=ep.owner_pid if ep else None,
                owner_token=ep.owner_token if ep else None,
            )
        try:
            lock_fd = os.open(start_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - start_lock.stat().st_mtime > effective_startup_budget:
                    start_lock.unlink()
            except FileNotFoundError:
                pass
            time.sleep(0.05)

    if lock_fd is None:
        raise TimeoutError(f"Could not claim Canonical LIVE startup lock for {root}")

    try:
        # Re-check connect right after acquiring the startup lock
        existing = connect(root)
        if existing:
            ep = _read_endpoint(root)
            is_owner = (
                owner_token is not None
                and ep is not None
                and ep.owner_token is not None
                and ep.owner_token == owner_token
            )
            return LiveStateClient(
                ep or existing.endpoint,
                is_owner=is_owner,
                service_pid=ep.pid if ep else None,
                owner_pid=ep.owner_pid if ep else None,
                owner_token=ep.owner_token if ep else None,
            )

        cmd = [sys.executable, "-m", "contextor.core.live_state.runtime", "--repo", str(root)]
        if owner_pid is not None:
            cmd.extend(["--owner-pid", str(owner_pid)])
        if owner_token is not None:
            cmd.extend(["--owner-token", str(owner_token)])

        from contextor.core.paths import package_root

        env = dict(os.environ)
        pkg_root = str(package_root())
        if "PYTHONPATH" in env and env["PYTHONPATH"]:
            if pkg_root not in env["PYTHONPATH"].split(os.pathsep):
                env["PYTHONPATH"] = f"{pkg_root}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = pkg_root

        proc = _spawn_runtime_subprocess(cmd, root, env)

        spawn_deadline = time.monotonic() + effective_startup_budget
        while time.monotonic() < spawn_deadline:
            client = connect(root)
            if client:
                ep = _read_endpoint(root)
                if ep is not None:
                    is_exact_proc = _is_same_or_descendant_pid(ep.pid, proc.pid)
                    is_token_match = (
                        owner_token is not None
                        and ep.owner_token is not None
                        and ep.owner_token == owner_token
                    )
                    if is_exact_proc and is_token_match:
                        return LiveStateClient(
                            ep,
                            is_owner=True,
                            service_pid=ep.pid,
                            owner_pid=ep.owner_pid,
                            owner_token=ep.owner_token,
                        )
                    if not is_exact_proc:
                        if _is_pid_alive(proc.pid):
                            _terminate_pid_tree(proc.pid)
                        return LiveStateClient(
                            ep,
                            is_owner=False,
                            service_pid=ep.pid,
                            owner_pid=ep.owner_pid,
                            owner_token=ep.owner_token,
                        )
                    return LiveStateClient(
                        ep,
                        is_owner=False,
                        service_pid=ep.pid,
                        owner_pid=ep.owner_pid,
                        owner_token=ep.owner_token,
                    )

            ret = proc.poll()
            if ret is not None:
                raise RuntimeError(
                    f"Canonical LIVE service process exited prematurely with code {ret} for {root}"
                )

            time.sleep(0.05)

        if _is_pid_alive(proc.pid):
            _terminate_pid_tree(proc.pid)
        raise TimeoutError(
            f"Canonical LIVE service startup and canonical initialization timed out after {effective_startup_budget}s for {root}"
        )
    finally:
        try:
            os.close(lock_fd)
        except OSError:
            pass
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
        meta = save_snapshot(
            engine.state,
            cache,
            getattr(manager, "state_id", ""),
            writer="live-service",
            repo_id=identity.repo_id,
            root_path=identity.root_path,
        )
        manager.save(
            getattr(manager, "state_id", ""),
            revision=meta.revision if meta else None,
        )
        return delta

    return update


def run_service(
    repo_path: str | Path,
    owner_pid: int | None = None,
    owner_token: str | None = None,
) -> None:
    root = Path(repo_path).resolve()
    identity = require_repository_identity(root)
    cache = migrate_legacy_snapshot(root)
    loaded = load_snapshot(
        cache,
        expected_repo_id=identity.repo_id,
        expected_root_path=identity.root_path,
    )
    state = loaded[0] if loaded else None
    if state is not None:
        from contextor.core.analysis.incremental.materialization import (
            ensure_module_usages,
            module_usages_require_materialization,
        )

        if module_usages_require_materialization(state):
            ensure_module_usages(state)
            loaded_metadata = loaded[1]
            save_snapshot(
                state,
                cache,
                loaded_metadata.state_id,
                writer="live-service-symbol-calls-backfill",
                repo_id=identity.repo_id,
                root_path=identity.root_path,
                revision_floor=loaded_metadata.revision,
            )
    revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
    server = CanonicalLiveServer(
        state,
        revision=revision,
        updater=_repository_updater(root),
    )

    if owner_pid is not None and owner_pid > 0:
        if sys.platform == "win32":
            import ctypes
            SYNCHRONIZE = 0x00100000
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            owner_handle = ctypes.windll.kernel32.OpenProcess(
                SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, int(owner_pid)
            )
            if not owner_handle:
                # Owner already exited before service began
                server.close()
                return

            def _owner_watchdog() -> None:
                try:
                    while not server._stop.wait(0.75):
                        res = ctypes.windll.kernel32.WaitForSingleObject(owner_handle, 0)
                        if res == 0:  # WAIT_OBJECT_0: owner process terminated
                            server.close()
                            break
                finally:
                    ctypes.windll.kernel32.CloseHandle(owner_handle)
        else:
            def _owner_watchdog() -> None:
                while not server._stop.wait(0.75):
                    if not _is_pid_alive(owner_pid):
                        server.close()
                        break

        watchdog = threading.Thread(
            target=_owner_watchdog,
            name=f"contextor-live-watchdog-{owner_pid}",
            daemon=True,
        )
        watchdog.start()

    target = endpoint_file(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(f".{os.getpid()}.tmp")
    payload: dict[str, Any] = {
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }
    if owner_pid is not None:
        payload["owner_pid"] = int(owner_pid)
    if owner_token is not None:
        payload["owner_token"] = str(owner_token)
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temporary, target)
    try:
        server.serve_forever()
    finally:
        try:
            current_ep = _read_endpoint(root)
            if current_ep is not None and current_ep.pid == os.getpid():
                target.unlink()
        except (OSError, FileNotFoundError):
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--owner-pid", type=int, default=None)
    parser.add_argument("--owner-token", type=str, default=None)
    args = parser.parse_args()
    run_service(args.repo, owner_pid=args.owner_pid, owner_token=args.owner_token)


if __name__ == "__main__":
    main()

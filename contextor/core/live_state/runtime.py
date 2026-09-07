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
from typing import Any, Mapping

from contextor.core.paths import repo_cache_dir
from contextor.core.repository_identity import (
    read_repository_identity,
    require_repository_identity,
)
from contextor.mcp_process_registry import process_identity as _process_identity
from contextor.core.live_state.runtime_domain import RuntimeDomain
from contextor.core.live_state.runtime_lease import (
    LeaseRecoveryRequired,
    LivenessResult,
    LivenessStatus,
    ProcessIdentity,
    RuntimeLease,
    RuntimeLeaseError,
    RuntimeLeaseManager,
)

from .ipc import (
    CanonicalLiveServer,
    CanonicalPersistenceConflict,
    LIVE_ENDPOINT_SCHEMA_VERSION,
    LIVE_PROTOCOL_VERSION,
    LiveEndpoint,
    LiveStateClient,
)
from .store import load_snapshot, migrate_legacy_snapshot, read_metadata, save_snapshot


class EndpointSchemaError(RuntimeError):
    """Endpoint metadata is malformed or belongs to another authority domain."""


class SecondDesktopActive(RuntimeError):
    """The repository is already active in a different Contextor Desktop."""


def _canonical_root(value: str | Path) -> str:
    return str(Path(value).expanduser().resolve())


def _safe_current_trace_operation() -> str | None:
    try:
        from contextor.core.runtime_trace import current_trace_operation
        return current_trace_operation()
    except Exception:
        return None


def _safe_trace_event(domain: str, event: str, **fields) -> None:
    try:
        from contextor.core.runtime_trace import trace_event
        trace_event(domain, event, **fields)
    except Exception:
        pass


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
        if _is_pid_alive(pid):
            try:
                import ctypes

                handle = ctypes.windll.kernel32.OpenProcess(0x0001, False, int(pid))
                if handle:
                    try:
                        ctypes.windll.kernel32.TerminateProcess(handle, 1)
                    finally:
                        ctypes.windll.kernel32.CloseHandle(handle)
            except Exception:
                pass
    else:
        try:
            os.kill(int(pid), 15)  # SIGTERM
        except OSError:
            pass


def endpoint_file(repo_path: str | Path) -> Path:
    return repo_cache_dir(repo_path) / "live_endpoint.json"


def _read_endpoint(repo_path: str | Path, *, strict: bool = False) -> LiveEndpoint | None:
    path = endpoint_file(repo_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise EndpointSchemaError("LIVE endpoint payload must be an object")
        required = {
            "schema_version",
            "host",
            "port",
            "authkey_hex",
            "pid",
            "service_pid",
            "repo_id",
            "root_path",
            "runtime_domain_id",
            "service_instance_id",
            "lease_generation",
            "process_start_identity",
        }
        if not required.issubset(payload):
            raise EndpointSchemaError("LIVE endpoint is missing required authority identity")
        if int(payload["schema_version"]) != LIVE_ENDPOINT_SCHEMA_VERSION:
            raise EndpointSchemaError("unsupported LIVE endpoint schema_version")
        pid = int(payload["pid"])
        service_pid = int(payload["service_pid"])
        if service_pid != pid:
            raise EndpointSchemaError("LIVE endpoint pid and service_pid disagree")
        lease_generation = int(payload["lease_generation"])
        port = int(payload["port"])
        owner_pid_value = payload.get("owner_pid")
        owner_pid = int(owner_pid_value) if owner_pid_value is not None else None
        if pid <= 0 or lease_generation <= 0 or not (1 <= port <= 65535):
            raise EndpointSchemaError("LIVE endpoint pid and lease_generation must be positive")
        if owner_pid is not None and owner_pid <= 0:
            raise EndpointSchemaError("LIVE endpoint owner_pid must be positive")
        root_path = _canonical_root(payload["root_path"])
        if not str(payload["repo_id"]).strip() or not str(payload["runtime_domain_id"]).strip():
            raise EndpointSchemaError("LIVE endpoint identity fields must be non-empty")
        if not str(payload["service_instance_id"]).strip() or not str(payload["process_start_identity"]).strip():
            raise EndpointSchemaError("LIVE endpoint service identity fields must be non-empty")
        endpoint = LiveEndpoint(
            str(payload["host"]),
            port,
            str(payload["authkey_hex"]),
            pid=pid,
            service_pid=service_pid,
            owner_pid=owner_pid,
            owner_token=(str(payload["owner_token"]) if payload.get("owner_token") is not None else None),
            repo_id=str(payload["repo_id"]),
            root_path=root_path,
            runtime_domain_id=str(payload["runtime_domain_id"]),
            service_instance_id=str(payload["service_instance_id"]),
            lease_generation=lease_generation,
            process_start_identity=str(payload["process_start_identity"]),
            desktop_instance_id=(
                str(payload["desktop_instance_id"])
                if payload.get("desktop_instance_id") is not None
                else None
            ),
            schema_version=int(payload["schema_version"]),
        )
        endpoint.authkey
        return endpoint
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError, EndpointSchemaError) as exc:
        if strict:
            if isinstance(exc, EndpointSchemaError):
                raise
            raise EndpointSchemaError("LIVE endpoint metadata is malformed") from exc
        return None


def _production_domain(identity) -> RuntimeDomain:
    return RuntimeDomain.from_identity(identity, mode="production")


def _endpoint_matches_domain(endpoint: LiveEndpoint, domain: RuntimeDomain) -> bool:
    return (
        endpoint.schema_version == LIVE_ENDPOINT_SCHEMA_VERSION
        and endpoint.repo_id == domain.repo_id
        and endpoint.root_path == _canonical_root(domain.repo_root)
        and endpoint.runtime_domain_id == domain.domain_id
        and endpoint.service_instance_id is not None
        and endpoint.lease_generation is not None
        and endpoint.pid is not None
        and endpoint.process_start_identity is not None
    )


def _status_matches_endpoint(status: dict[str, Any], endpoint: LiveEndpoint) -> bool:
    return (
        status.get("status") == "ok"
        and status.get("protocol_version") == LIVE_PROTOCOL_VERSION
        and status.get("repo_id") == endpoint.repo_id
        and status.get("root_path") == endpoint.root_path
        and status.get("runtime_domain_id") == endpoint.runtime_domain_id
        and status.get("service_instance_id") == endpoint.service_instance_id
        and status.get("lease_generation") == endpoint.lease_generation
        and status.get("service_pid") == endpoint.pid
        and status.get("process_start_identity") == endpoint.process_start_identity
        and status.get("endpoint_fingerprint") == endpoint.fingerprint()
    )


def _validated_desktop_claim(status: Mapping[str, Any], endpoint: LiveEndpoint) -> dict[str, Any] | None:
    claim = status.get("desktop_claim")
    if claim is None:
        return None
    if not isinstance(claim, Mapping):
        raise EndpointSchemaError("desktop_claim_status desktop_claim is malformed")
    required = {
        "runtime_domain_id",
        "service_instance_id",
        "lease_generation",
        "desktop_instance_id",
        "desktop_pid",
        "desktop_process_start_identity",
    }
    if not required.issubset(set(claim)):
        raise EndpointSchemaError("desktop_claim_status desktop_claim fields are malformed")
    if (
        claim["runtime_domain_id"] != endpoint.runtime_domain_id
        or claim["service_instance_id"] != endpoint.service_instance_id
        or int(claim["lease_generation"]) != endpoint.lease_generation
        or not isinstance(claim["desktop_instance_id"], str)
        or not claim["desktop_instance_id"].strip()
        or isinstance(claim["desktop_pid"], bool)
        or not isinstance(claim["desktop_pid"], int)
        or claim["desktop_pid"] <= 0
        or not isinstance(claim["desktop_process_start_identity"], str)
        or not claim["desktop_process_start_identity"].strip()
    ):
        raise EndpointSchemaError("desktop_claim_status desktop_claim identity does not match endpoint")
    return {
        "runtime_domain_id": str(claim["runtime_domain_id"]),
        "service_instance_id": str(claim["service_instance_id"]),
        "lease_generation": int(claim["lease_generation"]),
        "desktop_instance_id": claim["desktop_instance_id"].strip(),
        "desktop_pid": int(claim["desktop_pid"]),
        "desktop_process_start_identity": claim["desktop_process_start_identity"].strip(),
    }


class AuthorityLivenessVerifier:
    """Composite process-start and authenticated authority-status verifier."""

    def __init__(self, domain: RuntimeDomain):
        self.domain = domain

    def verify(self, lease: RuntimeLease) -> LivenessResult:
        try:
            _image, creation_time, alive = _process_identity(lease.service_pid)
        except Exception as exc:  # pragma: no cover - platform probe boundary
            return LivenessResult(
                LivenessStatus.UNKNOWN,
                None,
                None,
                None,
                None,
                f"process identity probe failed: {exc}",
            )
        process_matches = bool(alive and creation_time is not None and str(creation_time) == lease.process_start_identity)
        process_stale = (not alive) or (creation_time is not None and not process_matches)
        try:
            endpoint = _read_endpoint(self.domain.repo_root, strict=True)
        except EndpointSchemaError as exc:
            endpoint = None
            endpoint_reason = str(exc)
        else:
            endpoint_reason = "endpoint metadata unavailable"

        if endpoint is None:
            if process_stale:
                return LivenessResult.stale(
                    process_alive=bool(alive),
                    process_identity_matches=process_matches,
                    endpoint_available=False,
                    endpoint_matches=False,
                    reason=f"process is stale and authority endpoint is unavailable or invalid: {endpoint_reason}",
                    endpoint_evidence_verified=True,
                )
            return LivenessResult(
                LivenessStatus.UNKNOWN,
                bool(alive),
                process_matches,
                False,
                None,
                f"authority endpoint is unavailable: {endpoint_reason}",
            )

        endpoint_matches = _endpoint_matches_domain(endpoint, self.domain) and (
            endpoint.service_instance_id == lease.service_instance_id
            and endpoint.lease_generation == lease.lease_generation
            and endpoint.pid == lease.service_pid
            and endpoint.process_start_identity == lease.process_start_identity
        )
        try:
            status = LiveStateClient(endpoint).authority_status()
        except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
            try:
                _endpoint_image, endpoint_creation, endpoint_alive = _process_identity(endpoint.pid)
            except Exception:
                endpoint_alive = None
                endpoint_creation = None
            endpoint_is_dead = endpoint_alive is False
            if not endpoint_matches and process_stale and endpoint_is_dead:
                return LivenessResult.stale(
                    process_alive=bool(alive),
                    process_identity_matches=process_matches,
                    endpoint_available=False,
                    endpoint_matches=None,
                    reason=f"stale process and dead mismatched authority endpoint: {exc}",
                    endpoint_evidence_verified=True,
                )
            if endpoint_matches and process_stale and endpoint_is_dead:
                return LivenessResult.stale(
                    process_alive=bool(alive),
                    process_identity_matches=process_matches,
                    endpoint_available=False,
                    endpoint_matches=True,
                    reason=f"stale process and dead authority endpoint: {exc}",
                    endpoint_evidence_verified=True,
                )
            return LivenessResult(
                LivenessStatus.UNKNOWN,
                bool(alive),
                process_matches,
                True,
                endpoint_matches,
                f"authority status unavailable: {exc}",
            )

        status_matches = _status_matches_endpoint(status, endpoint)
        if not endpoint_matches:
            if status_matches:
                return LivenessResult(
                    LivenessStatus.FOREIGN_LIVE,
                    bool(alive),
                    process_matches,
                    True,
                    False,
                    "authenticated LIVE endpoint belongs to another service instance or generation",
                    False,
                )
            return LivenessResult(
                LivenessStatus.AMBIGUOUS,
                bool(alive),
                process_matches,
                True,
                False,
                "mismatched endpoint responded but did not prove a coherent authority identity",
                False,
            )
        if process_matches and status_matches:
            return LivenessResult.live("exact process identity and authority status match")
        return LivenessResult(
            LivenessStatus.UNKNOWN,
            bool(alive),
            process_matches,
            True,
            status_matches,
            "authority status did not prove the exact live owner",
        )


def _verified_existing_client(
    root: Path,
    identity,
    domain: RuntimeDomain,
    manager: RuntimeLeaseManager,
    *,
    desktop_instance_id: str | None = None,
    owner_token: str | None = None,
) -> LiveStateClient | None:
    try:
        endpoint = _read_endpoint(root, strict=True)
    except EndpointSchemaError as exc:
        if isinstance(exc.__cause__, PermissionError):
            return None
        raise
    if endpoint is None or not _endpoint_matches_domain(endpoint, domain):
        return None
    try:
        live = manager.read_live_lease()
        record = manager.read_generation()
        if (
            live is not None
            and record.status == "active"
            and live.service_instance_id == endpoint.service_instance_id
            and live.lease_generation == endpoint.lease_generation
            and live.service_pid == endpoint.pid
            and live.process_start_identity == endpoint.process_start_identity
            and live.endpoint_fingerprint == endpoint.fingerprint()
            and record.endpoint_fingerprint is None
        ):
            manager.reconcile_endpoint_binding(live, endpoint.fingerprint())
    except Exception:
        return None
    try:
        image, creation_time, alive = _process_identity(endpoint.pid)
    except Exception:
        return None
    if not alive or creation_time is None or str(creation_time) != endpoint.process_start_identity:
        return None
    try:
        status = LiveStateClient(endpoint).authority_status()
    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
        return None
    if not _status_matches_endpoint(status, endpoint):
        return None
    try:
        lease = manager.read_live_lease()
        record = manager.read_generation()
    except Exception:
        return None
    if lease is None or record.status != "active":
        return None
    if (
        lease.service_instance_id != endpoint.service_instance_id
        or lease.lease_generation != endpoint.lease_generation
        or lease.service_pid != endpoint.pid
        or lease.process_start_identity != endpoint.process_start_identity
        or lease.endpoint_fingerprint != endpoint.fingerprint()
        or record.last_service_instance_id != lease.service_instance_id
        or record.last_lease_generation != lease.lease_generation
        or record.endpoint_fingerprint != endpoint.fingerprint()
    ):
        return None
    client = LiveStateClient(
        endpoint,
        is_owner=False,
        service_pid=endpoint.pid,
        owner_pid=endpoint.owner_pid,
        owner_token=endpoint.owner_token,
    )
    return client


def connect(repo_path: str | Path) -> LiveStateClient | None:
    root = Path(repo_path).resolve()
    identity = read_repository_identity(root)
    if identity is None:
        return None
    domain = _production_domain(identity)
    manager = RuntimeLeaseManager(
        domain,
        liveness_verifier=AuthorityLivenessVerifier(domain),
    )
    try:
        return _verified_existing_client(root, identity, domain, manager)
    except EndpointSchemaError:
        return None


def _admit_desktop(
    client: LiveStateClient,
    desktop_instance_id: str,
    desktop_process_identity: ProcessIdentity,
) -> LiveStateClient:
    try:
        claim_status = client.desktop_claim_status()
    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
        raise RuntimeError(f"Desktop admission authority is unavailable: {exc}") from exc
    if claim_status.get("status") != "ok":
        raise RuntimeError(
            str(claim_status.get("error") or "Desktop admission claim status was unavailable")
        )
    try:
        _validated_desktop_claim(claim_status, client.endpoint)
    except (EndpointSchemaError, ValueError, TypeError) as exc:
        raise RuntimeError(f"Desktop admission claim status is invalid: {exc}") from exc
    try:
        response = client.claim_desktop(desktop_instance_id, desktop_process_identity)
    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
        raise RuntimeError(f"Desktop admission authority is unavailable: {exc}") from exc
    if response.get("status") == "ok" and response.get("claimed") is True:
        client.is_owner = True
        client.desktop_instance_id = desktop_instance_id
        client.desktop_claim = response.get("desktop_claim")
        client.desktop_process_identity = desktop_process_identity
        return client
    if response.get("error") == "second_desktop_active":
        raise SecondDesktopActive("repository already active in another Contextor Desktop")
    raise RuntimeError(str(response.get("error") or "Desktop admission claim was rejected"))


def connect_existing_with_status(
    repo_path: str | Path,
    *,
    attempts: int = 3,
    retry_delay: float = 0.05,
) -> tuple[LiveStateClient | None, str]:
    """Reconnect briefly to an existing owner without starting a service."""
    root = Path(repo_path).resolve()
    identity = read_repository_identity(root)
    if identity is None:
        return None, "endpoint_identity_unverified"
    domain = _production_domain(identity)
    manager = RuntimeLeaseManager(
        domain,
        liveness_verifier=AuthorityLivenessVerifier(domain),
    )
    try:
        expected = _read_endpoint(root, strict=True)
    except EndpointSchemaError:
        return None, "endpoint_identity_unverified"
    if expected is None:
        return None, "no_live_service"
    if not _endpoint_matches_domain(expected, domain):
        return None, "endpoint_identity_unverified"

    total_attempts = max(1, attempts)
    for attempt in range(total_attempts):
        client = _verified_existing_client(root, identity, domain, manager)
        if client is not None:
            current = _read_endpoint(root, strict=True)
            if current != expected or client.endpoint != expected:
                return None, "owner_identity_changed"
            return client, "connected"
        if attempt + 1 < total_attempts:
            time.sleep(max(0.0, retry_delay))

    try:
        endpoint = _read_endpoint(root, strict=True)
    except EndpointSchemaError:
        return None, "endpoint_identity_unverified"
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


def _write_endpoint_atomic(endpoint: LiveEndpoint, root: Path) -> None:
    target = endpoint_file(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    payload = endpoint.to_dict()
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _remove_endpoint_if_exact(root: Path, endpoint: LiveEndpoint) -> None:
    try:
        current = _read_endpoint(root, strict=True)
        if current is not None and current == endpoint:
            endpoint_file(root).unlink()
    except (OSError, FileNotFoundError, EndpointSchemaError):
        pass


def _authority_endpoint_from_server(server: CanonicalLiveServer, identity, domain: RuntimeDomain, lease: RuntimeLease, *, owner_pid: int | None, owner_token: str | None, desktop_instance_id: str | None) -> LiveEndpoint:
    endpoint = server.endpoint
    return LiveEndpoint(
        endpoint.host,
        endpoint.port,
        endpoint.authkey_hex,
        pid=lease.service_pid,
        owner_pid=owner_pid,
        owner_token=owner_token,
        repo_id=identity.repo_id,
        root_path=_canonical_root(identity.root_path),
        runtime_domain_id=domain.domain_id,
        service_instance_id=lease.service_instance_id,
        lease_generation=lease.lease_generation,
        process_start_identity=lease.process_start_identity,
        desktop_instance_id=desktop_instance_id,
    )


def connect_or_start(
    repo_path: str | Path,
    *,
    owner_pid: int | None = None,
    owner_token: str | None = None,
    desktop_instance_id: str | None = None,
    desktop_process_start_identity: str | None = None,
    client_kind: str = "protocol",
    timeout: float = DEFAULT_CONNECT_TIMEOUT,
    cold_start_timeout: float = DEFAULT_COLD_START_TIMEOUT,
) -> LiveStateClient:
    root = Path(repo_path).expanduser().resolve()
    identity = require_repository_identity(root)
    if client_kind == "desktop" and not isinstance(desktop_instance_id, str):
        raise ValueError("desktop_instance_id is required for Desktop admission")
    desktop_process_identity = None
    if client_kind == "desktop":
        desktop_pid = owner_pid if owner_pid is not None else os.getpid()
        if owner_pid is None:
            owner_pid = desktop_pid
        if desktop_process_start_identity is None:
            desktop_process_identity = ProcessIdentity.current(desktop_pid)
        else:
            desktop_process_identity = ProcessIdentity(desktop_pid, desktop_process_start_identity)
    domain = _production_domain(identity)
    manager = RuntimeLeaseManager(
        domain,
        liveness_verifier=AuthorityLivenessVerifier(domain),
    )
    try:
        endpoint = _read_endpoint(root, strict=True)
    except EndpointSchemaError as exc:
        if endpoint_file(root).exists() and not isinstance(exc.__cause__, PermissionError):
            raise
        endpoint = None
    if endpoint is not None and not _endpoint_matches_domain(endpoint, domain):
        raise EndpointSchemaError("LIVE endpoint belongs to another repository or runtime domain")

    existing = _verified_existing_client(
        root,
        identity,
        domain,
        manager,
        desktop_instance_id=desktop_instance_id,
        owner_token=owner_token,
    )
    if existing is not None:
        if client_kind == "desktop":
            return _admit_desktop(existing, str(desktop_instance_id), desktop_process_identity)
        return existing

    record = manager.read_generation()
    live = manager.read_live_lease()
    if live is None and record.status == "active":
        raise LeaseRecoveryRequired(
            "active durable authority has no live lease; recovery is required before startup"
        )

    target = endpoint_file(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    start_lock = target.with_name("live_service_start.lock")
    effective_startup_budget = max(timeout, cold_start_timeout)
    deadline = time.monotonic() + effective_startup_budget
    lock_fd = None
    while time.monotonic() < deadline:
        existing = _verified_existing_client(
            root,
            identity,
            domain,
            manager,
            desktop_instance_id=desktop_instance_id,
            owner_token=owner_token,
        )
        if existing is not None:
            if client_kind == "desktop":
                return _admit_desktop(existing, str(desktop_instance_id), desktop_process_identity)
            return existing
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

    proc = None
    try:
        existing = _verified_existing_client(
            root,
            identity,
            domain,
            manager,
            desktop_instance_id=desktop_instance_id,
            owner_token=owner_token,
        )
        if existing is not None:
            if client_kind == "desktop":
                return _admit_desktop(existing, str(desktop_instance_id), desktop_process_identity)
            return existing

        cmd = [sys.executable, "-m", "contextor.core.live_state.runtime", "--repo", str(root)]
        if owner_pid is not None:
            cmd.extend(["--owner-pid", str(owner_pid)])
        if owner_token is not None:
            cmd.extend(["--owner-token", str(owner_token)])
        if desktop_instance_id is not None:
            cmd.extend(["--desktop-instance-id", str(desktop_instance_id)])
        if client_kind == "desktop" and desktop_process_identity is not None:
            cmd.extend(["--desktop-process-start-identity", desktop_process_identity.process_start_identity])

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
            client = _verified_existing_client(
                root,
                identity,
                domain,
                manager,
                desktop_instance_id=desktop_instance_id,
                owner_token=owner_token,
            )
            if client is not None:
                if client_kind == "desktop":
                    try:
                        return _admit_desktop(client, str(desktop_instance_id), desktop_process_identity)
                    except SecondDesktopActive:
                        if proc is not None and _is_pid_alive(proc.pid):
                            _terminate_pid_tree(proc.pid)
                        raise
                return client
            if proc.poll() is not None:
                raise RuntimeError(
                    f"Canonical LIVE service process exited prematurely with code {proc.returncode} for {root}"
                )
            time.sleep(0.05)
        if proc is not None and _is_pid_alive(proc.pid):
            _terminate_pid_tree(proc.pid)
        raise TimeoutError(
            f"Canonical LIVE service startup and authority bootstrap timed out after {effective_startup_budget}s for {root}"
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


def _repository_updater(root: Path, holder: dict[str, object] | None = None):
    identity = require_repository_identity(root)
    cache = repo_cache_dir(root)

    def update(state, file_path: str):
        import time
        op = _safe_current_trace_operation()
        started = time.monotonic()
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
        _safe_trace_event("LIVE", "ENGINE_READY", op=op, repo=str(root), elapsed_ms=(time.monotonic() - started) * 1000.0)
        incremental_started = time.monotonic()
        delta = engine.update_file(file_path)
        _safe_trace_event("LIVE", "INCREMENTAL_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - incremental_started) * 1000.0, status=getattr(delta, "status", None))
        if holder is not None:
            holder["manager"] = manager
            holder["state_id"] = getattr(manager, "state_id", "")
        return delta

    return update


def _repository_persister(root: Path, holder: dict[str, object] | None = None):
    identity = require_repository_identity(root)
    cache = repo_cache_dir(root)

    def persist(state, exact_revision: int):
        import time
        op = _safe_current_trace_operation()
        manager = (holder or {}).get("manager")
        if manager is None:
            from contextor.core.analysis.state_manager import FileStateManager

            manager = FileStateManager(str(cache))
        state_id = (holder or {}).get("state_id", getattr(manager, "state_id", ""))
        snapshot_started = time.monotonic()
        try:
            meta = save_snapshot(
                state,
                cache,
                str(state_id),
                writer="live-service",
                repo_id=identity.repo_id,
                root_path=identity.root_path,
                exact_revision=exact_revision,
                file_state_payload=manager.build_payload(str(state_id), exact_revision),
            )
            if meta.revision != exact_revision:
                raise ValueError("Exact LIVE persistence revision mismatch.")
            _safe_trace_event("LIVE", "SNAPSHOT_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - snapshot_started) * 1000.0)
            _safe_trace_event("LIVE", "FILE_STATE_SAVE_END", op=op, repo=str(root), elapsed_ms=0.0)
        except Exception as exc:
            from contextor.core.live_state.store import SnapshotRevisionConflict
            if isinstance(exc, SnapshotRevisionConflict):
                raise CanonicalPersistenceConflict(exc.current_revision, exc.requested_revision) from exc
            raise
        return meta

    return persist


def run_service(
    repo_path: str | Path,
    owner_pid: int | None = None,
    owner_token: str | None = None,
    desktop_instance_id: str | None = None,
    desktop_process_start_identity: str | None = None,
) -> None:
    root = Path(repo_path).expanduser().resolve()
    identity = require_repository_identity(root)
    domain = _production_domain(identity)
    manager = RuntimeLeaseManager(
        domain,
        liveness_verifier=AuthorityLivenessVerifier(domain),
    )
    lease = None
    server = None
    published_endpoint = None
    desktop_claim = None
    ownership_resolved = False
    try:
        lease = manager.acquire()
        if desktop_instance_id is not None:
            if owner_pid is None or desktop_process_start_identity is None:
                raise RuntimeLeaseError("Desktop claim process identity is required")
            desktop_claim = manager.claim_desktop(
                lease,
                desktop_instance_id,
                ProcessIdentity(owner_pid, desktop_process_start_identity),
            )
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
                loaded_metadata = loaded[1]
                from contextor.core.analysis.state_manager import FileStateManager

                file_state_manager = FileStateManager(str(cache))
                ensure_module_usages(state)
                target_revision = loaded_metadata.revision + 1
                file_state_payload = file_state_manager.build_payload(
                    loaded_metadata.state_id,
                    target_revision,
                )
                save_snapshot(
                    state,
                    cache,
                    loaded_metadata.state_id,
                    writer="live-service-symbol-calls-backfill",
                    repo_id=identity.repo_id,
                    root_path=identity.root_path,
                    exact_revision=target_revision,
                    file_state_payload=file_state_payload,
                )
        revision = read_metadata(cache).revision if read_metadata(cache) else 0
        adapter_holder: dict[str, object] = {}
        authority_identity = {
            "repo_id": identity.repo_id,
            "root_path": _canonical_root(identity.root_path),
            "runtime_domain_id": domain.domain_id,
            "service_instance_id": lease.service_instance_id,
            "lease_generation": lease.lease_generation,
            "service_pid": lease.service_pid,
            "process_start_identity": lease.process_start_identity,
            "owner_pid": owner_pid,
            "owner_token": owner_token,
            "desktop_instance_id": desktop_instance_id,
        }
        server = CanonicalLiveServer(
            state,
            revision=revision,
            updater=_repository_updater(root, adapter_holder),
            persister=_repository_persister(root, adapter_holder),
            authority_identity=authority_identity,
            desktop_claim=desktop_claim,
            desktop_claim_reader=lambda: manager.read_desktop_claim(lease),
            desktop_claim_acquirer=lambda desktop_id, desktop_pid, desktop_start: manager.claim_desktop(
                lease,
                desktop_id,
                ProcessIdentity(desktop_pid, desktop_start),
            ),
            desktop_claim_releaser=lambda desktop_id, desktop_pid, desktop_start: manager.release_desktop_claim(
                lease,
                desktop_id,
                ProcessIdentity(desktop_pid, desktop_start),
            ),
        )
        published_endpoint = _authority_endpoint_from_server(
            server,
            identity,
            domain,
            lease,
            owner_pid=owner_pid,
            owner_token=owner_token,
            desktop_instance_id=desktop_instance_id,
        )
        server.endpoint = published_endpoint
        _write_endpoint_atomic(published_endpoint, root)
        manager.bind_endpoint(lease, published_endpoint.fingerprint())
        current_endpoint = _read_endpoint(root, strict=True)
        current_lease = manager.read_live_lease()
        current_record = manager.read_generation()
        if (
            current_endpoint != published_endpoint
            or current_lease is None
            or current_lease.service_instance_id != published_endpoint.service_instance_id
            or current_lease.lease_generation != published_endpoint.lease_generation
            or current_lease.endpoint_fingerprint != published_endpoint.fingerprint()
            or current_record.status != "active"
            or current_record.endpoint_fingerprint != published_endpoint.fingerprint()
        ):
            raise RuntimeError("LIVE endpoint and RuntimeLease identity parity verification failed")
        _safe_trace_event(
            "LIVE",
            "AUTHORITY_READY",
            repo=str(root),
            domain_id=domain.domain_id,
            service_instance_id=lease.service_instance_id,
            lease_generation=lease.lease_generation,
        )

        if owner_pid is not None and owner_pid > 0:
            if sys.platform == "win32":
                import ctypes

                SYNCHRONIZE = 0x00100000
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                owner_handle = ctypes.windll.kernel32.OpenProcess(
                    SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION,
                    False,
                    int(owner_pid),
                )
                if not owner_handle:
                    return

                def _owner_watchdog() -> None:
                    try:
                        while not server._stop.wait(0.75):
                            res = ctypes.windll.kernel32.WaitForSingleObject(owner_handle, 0)
                            if res == 0:
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

            threading.Thread(
                target=_owner_watchdog,
                name=f"contextor-live-watchdog-{owner_pid}",
                daemon=True,
            ).start()
        server.serve_forever()
    except Exception as exc:
        _safe_trace_event(
            "LIVE",
            "AUTHORITY_BOOTSTRAP_FAIL",
            repo=str(root),
            error=str(exc),
            service_instance_id=getattr(lease, "service_instance_id", None),
            lease_generation=getattr(lease, "lease_generation", None),
        )
        raise
    finally:
        if server is not None:
            server.close()
        if lease is not None:
            if published_endpoint is not None:
                try:
                    manager.reconcile_endpoint_binding(lease, published_endpoint.fingerprint())
                except Exception as exc:
                    _safe_trace_event(
                        "LIVE",
                        "AUTHORITY_BIND_RECONCILE_FAIL",
                        repo=str(root),
                        error=str(exc),
                        service_instance_id=lease.service_instance_id,
                        lease_generation=lease.lease_generation,
                    )
            try:
                manager.release(lease)
                ownership_resolved = True
            except Exception as exc:
                _safe_trace_event(
                    "LIVE",
                    "AUTHORITY_RELEASE_FAIL",
                    repo=str(root),
                    error=str(exc),
                    service_instance_id=lease.service_instance_id,
                    lease_generation=lease.lease_generation,
                )
                try:
                    manager.fence_owner(lease)
                    ownership_resolved = True
                except Exception as fence_exc:
                    _safe_trace_event(
                        "LIVE",
                        "AUTHORITY_FENCE_FAIL",
                        repo=str(root),
                        error=str(fence_exc),
                        service_instance_id=lease.service_instance_id,
                        lease_generation=lease.lease_generation,
                    )
        if published_endpoint is not None and ownership_resolved:
            _remove_endpoint_if_exact(root, published_endpoint)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--owner-pid", type=int, default=None)
    parser.add_argument("--owner-token", type=str, default=None)
    parser.add_argument("--desktop-instance-id", type=str, default=None)
    parser.add_argument("--desktop-process-start-identity", type=str, default=None)
    args = parser.parse_args()
    run_service(
        args.repo,
        owner_pid=args.owner_pid,
        owner_token=args.owner_token,
        desktop_instance_id=args.desktop_instance_id,
        desktop_process_start_identity=args.desktop_process_start_identity,
    )


if __name__ == "__main__":
    main()

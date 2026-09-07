"""Domain-scoped authority lease and durable service-generation fencing.

This module is intentionally below authority bootstrap and above the existing
LIVE service.  It owns only the lease/generation contract: no endpoint
publication, GUI, MCP, canonical-state, or observability wiring is performed
here.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
import uuid
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Mapping, Protocol

from contextor.core.live_state.runtime_domain import (
    RuntimeDomain,
    RuntimeDomainError,
    RuntimeMode,
    validate_runtime_domain,
)
from contextor.mcp_process_registry import process_identity as _process_identity


RUNTIME_LEASE_SCHEMA_VERSION = 1
AUTHORITY_GENERATION_SCHEMA_VERSION = 1
GenerationStatus = Literal["never_acquired", "reserved", "active", "released", "fenced"]

_RESOURCE_KEYS = (
    "repo_root",
    "cache_root",
    "logs_root",
    "lock_root",
    "ipc_endpoint_root",
)
_LEASE_FIELDS = {
    "schema_version",
    "repo_id",
    "runtime_domain_id",
    "mode",
    "repo_root",
    "repo_root_fingerprint",
    "service_instance_id",
    "lease_generation",
    "service_pid",
    "process_start_identity",
    "endpoint_fingerprint",
    "started_at",
    "last_heartbeat_at",
    "owner_token",
    "resource_root_fingerprints",
}
_GENERATION_FIELDS = {
    "schema_version",
    "repo_id",
    "runtime_domain_id",
    "mode",
    "repo_root",
    "repo_root_fingerprint",
    "last_lease_generation",
    "last_service_instance_id",
    "service_pid",
    "process_start_identity",
    "endpoint_fingerprint",
    "status",
    "fenced_service_instance_id",
    "fenced_lease_generation",
    "updated_at",
    "resource_root_fingerprints",
}


class RuntimeLeaseError(ValueError):
    """Base error for malformed, foreign, busy, or stale lease operations."""


class LeaseAlreadyHeld(RuntimeLeaseError):
    """A responsive authority already owns the domain lease."""


class LeaseLivenessUnknown(RuntimeLeaseError):
    """Liveness was not strong enough to permit a takeover."""


class LeaseRecoveryRequired(RuntimeLeaseError):
    """Durable authority state requires recovery before another owner may start."""


class LeaseNotOwner(RuntimeLeaseError):
    """The supplied service instance/generation is not the current owner."""


class ForeignLeaseError(RuntimeLeaseError):
    """Lease or generation metadata belongs to another domain."""


class EndpointBindingError(RuntimeLeaseError):
    """Endpoint fingerprint binding is invalid for the current owner."""


class LeaseBusyError(RuntimeLeaseError):
    """The cross-process domain lock could not be acquired in time."""


class LivenessStatus(str, Enum):
    LIVE = "live"
    STALE = "stale"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"
    TIMEOUT = "timeout"
    BUSY = "busy"


def _non_empty_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeLeaseError(f"{field} must be a non-empty string")
    return value.strip()


def _positive_int(value: Any, *, field: str, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeLeaseError(f"{field} must be an integer")
    if value < (0 if allow_zero else 1):
        raise RuntimeLeaseError(f"{field} must be non-negative" if allow_zero else f"{field} must be positive")
    return value


def _timestamp(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeLeaseError(f"{field} must be a timestamp")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise RuntimeLeaseError(f"{field} must be a finite non-negative timestamp")
    return result


def _canonical_path_text(value: Any, *, field: str) -> str:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise RuntimeLeaseError(f"{field} must be a non-empty path")
    try:
        resolved = Path(value).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise RuntimeLeaseError(f"{field} cannot be canonicalized") from exc
    if not resolved.is_absolute():
        raise RuntimeLeaseError(f"{field} must be absolute")
    return os.path.normcase(str(resolved))


def _path_fingerprint(value: str | Path) -> str:
    canonical = _canonical_path_text(str(value), field="resource_root")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _domain_resource_fingerprints(domain: RuntimeDomain) -> tuple[tuple[str, str], ...]:
    roots = {
        "repo_root": domain.repo_root,
        "cache_root": domain.cache_root,
        "logs_root": domain.logs_root,
        "lock_root": domain.lock_root,
        "ipc_endpoint_root": domain.ipc_endpoint_root,
    }
    return tuple((name, _path_fingerprint(path)) for name, path in roots.items())


def _fingerprints_to_dict(value: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return dict(value)


def _fingerprints_from_payload(value: Any) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, Mapping) or set(value) != set(_RESOURCE_KEYS):
        raise RuntimeLeaseError("resource_root_fingerprints do not match schema")
    result: list[tuple[str, str]] = []
    for key in _RESOURCE_KEYS:
        result.append((key, _non_empty_text(value[key], field=f"resource_root_fingerprints.{key}")))
    return tuple(result)


def _validate_domain_input(
    domain: RuntimeDomain,
    *,
    known_production_roots: Iterable[str | Path] | None,
    known_test_roots: Iterable[str | Path] | None,
) -> None:
    if not isinstance(domain, RuntimeDomain):
        raise RuntimeLeaseError("domain must be a previously validated RuntimeDomain")
    # RuntimeDomain.__post_init__ already performs intrinsic validation.  When
    # the caller supplies the trusted cross-domain context, repeat that check
    # immediately before any lease resource is touched.
    if domain.mode == "production" or known_production_roots is not None or known_test_roots is not None:
        try:
            validate_runtime_domain(
                domain,
                expected_mode=domain.mode,
                known_production_roots=known_production_roots,
                known_test_roots=known_test_roots,
            )
        except RuntimeDomainError as exc:
            raise RuntimeLeaseError("runtime domain validation failed") from exc


@dataclass(frozen=True, slots=True)
class ProcessIdentity:
    """PID plus a process-start token; PID alone is never sufficient."""

    pid: int
    process_start_identity: str
    executable_fingerprint: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "pid", _positive_int(self.pid, field="pid"))
        object.__setattr__(
            self,
            "process_start_identity",
            _non_empty_text(self.process_start_identity, field="process_start_identity"),
        )
        if self.executable_fingerprint is not None:
            object.__setattr__(
                self,
                "executable_fingerprint",
                _non_empty_text(self.executable_fingerprint, field="executable_fingerprint"),
            )

    @classmethod
    def current(cls, pid: int | None = None) -> "ProcessIdentity":
        current_pid = os.getpid() if pid is None else _positive_int(pid, field="pid")
        try:
            image, creation_time, alive = _process_identity(current_pid)
        except Exception as exc:  # pragma: no cover - platform probe boundary
            raise RuntimeLeaseError("process identity probe failed") from exc
        if not alive or creation_time is None:
            raise RuntimeLeaseError("current process identity is unavailable")
        executable = _path_fingerprint(image) if image else None
        return cls(current_pid, str(creation_time), executable)


@dataclass(frozen=True, slots=True)
class LivenessResult:
    status: LivenessStatus
    process_alive: bool | None
    process_identity_matches: bool | None
    endpoint_available: bool | None
    endpoint_matches: bool | None
    reason: str
    endpoint_evidence_verified: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.status, LivenessStatus):
            object.__setattr__(self, "status", LivenessStatus(self.status))
        object.__setattr__(self, "reason", _non_empty_text(self.reason, field="reason"))

    @property
    def confirmed_stale(self) -> bool:
        process_evidence = self.process_alive is False or self.process_identity_matches is False
        endpoint_evidence = self.endpoint_evidence_verified and (
            self.endpoint_available is False or self.endpoint_matches is False
        )
        return self.status is LivenessStatus.STALE and process_evidence and endpoint_evidence

    @classmethod
    def live(cls, reason: str = "process identity and authority are responsive") -> "LivenessResult":
        return cls(LivenessStatus.LIVE, True, True, True, True, reason)

    @classmethod
    def stale(
        cls,
        *,
        process_alive: bool | None,
        process_identity_matches: bool | None,
        endpoint_available: bool | None,
        endpoint_matches: bool | None,
        reason: str,
        endpoint_evidence_verified: bool = False,
    ) -> "LivenessResult":
        return cls(
            LivenessStatus.STALE,
            process_alive,
            process_identity_matches,
            endpoint_available,
            endpoint_matches,
            reason,
            endpoint_evidence_verified,
        )


class LivenessVerifier(Protocol):
    def verify(self, lease: "RuntimeLease") -> LivenessResult:
        """Return deterministic evidence for the exact observed lease."""


class DefaultLivenessVerifier:
    """Use the existing process-start identity primitive without endpoint takeover."""

    def verify(self, lease: "RuntimeLease") -> LivenessResult:
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
        if not alive:
            return LivenessResult(
                LivenessStatus.UNKNOWN,
                process_alive=False,
                process_identity_matches=False,
                endpoint_available=None,
                endpoint_matches=None,
                reason="recorded service process is dead; authority endpoint was not probed",
            )
        if creation_time is None:
            return LivenessResult(
                LivenessStatus.UNKNOWN,
                True,
                None,
                None,
                None,
                "live process has no process-start identity",
            )
        matches = str(creation_time) == lease.process_start_identity
        if not matches:
            return LivenessResult(
                LivenessStatus.UNKNOWN,
                process_alive=True,
                process_identity_matches=False,
                endpoint_available=None,
                endpoint_matches=None,
                reason="PID start identity does not match; authority endpoint was not probed",
            )
        if lease.endpoint_fingerprint is not None:
            return LivenessResult(
                LivenessStatus.UNKNOWN,
                True,
                True,
                None,
                None,
                "endpoint authority-status is not available in Stage 2",
            )
        return LivenessResult(
            LivenessStatus.LIVE,
            True,
            True,
            None,
            None,
            "process-start identity matches; endpoint is not yet bound",
        )


@dataclass(frozen=True, slots=True)
class RuntimeLease:
    schema_version: int
    repo_id: str
    runtime_domain_id: str
    mode: RuntimeMode
    repo_root: str
    repo_root_fingerprint: str
    service_instance_id: str
    lease_generation: int
    service_pid: int
    process_start_identity: str
    endpoint_fingerprint: str | None
    started_at: float
    last_heartbeat_at: float
    owner_token: str | None
    resource_root_fingerprints: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if self.schema_version != RUNTIME_LEASE_SCHEMA_VERSION:
            raise RuntimeLeaseError("unsupported RuntimeLease schema_version")
        if self.mode not in ("production", "test"):
            raise RuntimeLeaseError("mode must be production or test")
        for field in ("repo_id", "runtime_domain_id", "service_instance_id"):
            object.__setattr__(self, field, _non_empty_text(getattr(self, field), field=field))
        object.__setattr__(self, "repo_root", _canonical_path_text(self.repo_root, field="repo_root"))
        object.__setattr__(
            self,
            "repo_root_fingerprint",
            _non_empty_text(self.repo_root_fingerprint, field="repo_root_fingerprint"),
        )
        object.__setattr__(self, "lease_generation", _positive_int(self.lease_generation, field="lease_generation"))
        object.__setattr__(self, "service_pid", _positive_int(self.service_pid, field="service_pid"))
        object.__setattr__(
            self,
            "process_start_identity",
            _non_empty_text(self.process_start_identity, field="process_start_identity"),
        )
        object.__setattr__(self, "started_at", _timestamp(self.started_at, field="started_at"))
        object.__setattr__(self, "last_heartbeat_at", _timestamp(self.last_heartbeat_at, field="last_heartbeat_at"))
        if self.last_heartbeat_at < self.started_at:
            raise RuntimeLeaseError("last_heartbeat_at cannot precede started_at")
        if self.endpoint_fingerprint is not None:
            object.__setattr__(
                self,
                "endpoint_fingerprint",
                _non_empty_text(self.endpoint_fingerprint, field="endpoint_fingerprint"),
            )
        if self.owner_token is not None:
            object.__setattr__(self, "owner_token", _non_empty_text(self.owner_token, field="owner_token"))
        fingerprints = tuple(self.resource_root_fingerprints)
        if tuple(name for name, _ in fingerprints) != _RESOURCE_KEYS:
            raise RuntimeLeaseError("resource_root_fingerprints do not match schema")
        fingerprints = tuple(
            (name, _non_empty_text(value, field=f"resource_root_fingerprints.{name}"))
            for name, value in fingerprints
        )
        object.__setattr__(self, "resource_root_fingerprints", fingerprints)
        if dict(fingerprints)["repo_root"] != self.repo_root_fingerprint:
            raise RuntimeLeaseError("repo_root_fingerprint does not match resource fingerprints")

    def matches_domain(self, domain: RuntimeDomain) -> bool:
        return (
            self.repo_id == domain.repo_id
            and self.runtime_domain_id == domain.domain_id
            and self.mode == domain.mode
            and self.repo_root == _canonical_path_text(domain.repo_root, field="repo_root")
            and self.resource_root_fingerprints == _domain_resource_fingerprints(domain)
        )

    def owner_tuple(self) -> tuple[str, int]:
        return self.service_instance_id, self.lease_generation

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repo_id": self.repo_id,
            "runtime_domain_id": self.runtime_domain_id,
            "mode": self.mode,
            "repo_root": self.repo_root,
            "repo_root_fingerprint": self.repo_root_fingerprint,
            "service_instance_id": self.service_instance_id,
            "lease_generation": self.lease_generation,
            "service_pid": self.service_pid,
            "process_start_identity": self.process_start_identity,
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "started_at": self.started_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "owner_token": self.owner_token,
            "resource_root_fingerprints": _fingerprints_to_dict(self.resource_root_fingerprints),
        }

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RuntimeLease":
        if not isinstance(payload, Mapping) or set(payload) != _LEASE_FIELDS:
            raise RuntimeLeaseError("RuntimeLease payload fields do not match schema")
        return cls(
            schema_version=payload["schema_version"],
            repo_id=payload["repo_id"],
            runtime_domain_id=payload["runtime_domain_id"],
            mode=payload["mode"],
            repo_root=payload["repo_root"],
            repo_root_fingerprint=payload["repo_root_fingerprint"],
            service_instance_id=payload["service_instance_id"],
            lease_generation=payload["lease_generation"],
            service_pid=payload["service_pid"],
            process_start_identity=payload["process_start_identity"],
            endpoint_fingerprint=payload["endpoint_fingerprint"],
            started_at=payload["started_at"],
            last_heartbeat_at=payload["last_heartbeat_at"],
            owner_token=payload["owner_token"],
            resource_root_fingerprints=_fingerprints_from_payload(payload["resource_root_fingerprints"]),
        )

    @classmethod
    def deserialize(cls, payload: str | Mapping[str, Any]) -> "RuntimeLease":
        if isinstance(payload, str):
            try:
                value = json.loads(payload)
            except (TypeError, ValueError) as exc:
                raise RuntimeLeaseError("invalid RuntimeLease JSON") from exc
        else:
            value = payload
        if not isinstance(value, Mapping):
            raise RuntimeLeaseError("RuntimeLease payload must be an object")
        return cls.from_dict(value)


@dataclass(frozen=True, slots=True)
class AuthorityGenerationRecord:
    schema_version: int
    repo_id: str
    runtime_domain_id: str
    mode: RuntimeMode
    repo_root: str
    repo_root_fingerprint: str
    last_lease_generation: int
    last_service_instance_id: str | None
    service_pid: int | None
    process_start_identity: str | None
    endpoint_fingerprint: str | None
    status: GenerationStatus
    fenced_service_instance_id: str | None
    fenced_lease_generation: int | None
    updated_at: float
    resource_root_fingerprints: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if self.schema_version != AUTHORITY_GENERATION_SCHEMA_VERSION:
            raise RuntimeLeaseError("unsupported authority-generation schema_version")
        if self.mode not in ("production", "test"):
            raise RuntimeLeaseError("mode must be production or test")
        for field in ("repo_id", "runtime_domain_id"):
            object.__setattr__(self, field, _non_empty_text(getattr(self, field), field=field))
        object.__setattr__(self, "repo_root", _canonical_path_text(self.repo_root, field="repo_root"))
        object.__setattr__(
            self,
            "repo_root_fingerprint",
            _non_empty_text(self.repo_root_fingerprint, field="repo_root_fingerprint"),
        )
        object.__setattr__(
            self,
            "last_lease_generation",
            _positive_int(self.last_lease_generation, field="last_lease_generation", allow_zero=True),
        )
        if self.status not in ("never_acquired", "reserved", "active", "released", "fenced"):
            raise RuntimeLeaseError("invalid authority-generation status")
        for field in ("last_service_instance_id", "fenced_service_instance_id", "process_start_identity"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _non_empty_text(value, field=field))
        if self.service_pid is not None:
            object.__setattr__(self, "service_pid", _positive_int(self.service_pid, field="service_pid"))
        if self.endpoint_fingerprint is not None:
            object.__setattr__(
                self,
                "endpoint_fingerprint",
                _non_empty_text(self.endpoint_fingerprint, field="endpoint_fingerprint"),
            )
        current_identity_complete = (
            self.last_service_instance_id is not None
            and self.service_pid is not None
            and self.process_start_identity is not None
        )
        if self.status == "never_acquired":
            if self.last_lease_generation != 0 or any(
                value is not None
                for value in (
                    self.last_service_instance_id,
                    self.service_pid,
                    self.process_start_identity,
                    self.endpoint_fingerprint,
                    self.fenced_service_instance_id,
                    self.fenced_lease_generation,
                )
            ):
                raise RuntimeLeaseError("never_acquired generation must have no owner or fence identity")
        else:
            if self.last_lease_generation == 0 or not current_identity_complete:
                raise RuntimeLeaseError("generation status requires complete current owner identity")
        fence_pair_complete = self.fenced_service_instance_id is not None and self.fenced_lease_generation is not None
        if self.status in ("reserved", "active") and (
            self.fenced_service_instance_id is not None or self.fenced_lease_generation is not None
        ):
            raise RuntimeLeaseError("reserved/active generation cannot carry a fence pair")
        if self.status in ("released", "fenced") and not fence_pair_complete:
            raise RuntimeLeaseError("released/fenced generation requires a complete fence pair")
        if fence_pair_complete and (
            self.fenced_service_instance_id != self.last_service_instance_id
            or self.fenced_lease_generation != self.last_lease_generation
        ):
            raise RuntimeLeaseError("fence pair must match the durable owner generation")
        if self.fenced_lease_generation is not None:
            object.__setattr__(
                self,
                "fenced_lease_generation",
                _positive_int(self.fenced_lease_generation, field="fenced_lease_generation"),
            )
        object.__setattr__(self, "updated_at", _timestamp(self.updated_at, field="updated_at"))
        fingerprints = tuple(self.resource_root_fingerprints)
        if tuple(name for name, _ in fingerprints) != _RESOURCE_KEYS:
            raise RuntimeLeaseError("resource_root_fingerprints do not match schema")
        object.__setattr__(
            self,
            "resource_root_fingerprints",
            tuple(
                (name, _non_empty_text(value, field=f"resource_root_fingerprints.{name}"))
                for name, value in fingerprints
            ),
        )
        if dict(self.resource_root_fingerprints)["repo_root"] != self.repo_root_fingerprint:
            raise RuntimeLeaseError("repo_root_fingerprint does not match resource fingerprints")

    @classmethod
    def initial(cls, domain: RuntimeDomain, *, now: float | None = None) -> "AuthorityGenerationRecord":
        fingerprints = _domain_resource_fingerprints(domain)
        return cls(
            schema_version=AUTHORITY_GENERATION_SCHEMA_VERSION,
            repo_id=domain.repo_id,
            runtime_domain_id=domain.domain_id,
            mode=domain.mode,
            repo_root=_canonical_path_text(domain.repo_root, field="repo_root"),
            repo_root_fingerprint=dict(fingerprints)["repo_root"],
            last_lease_generation=0,
            last_service_instance_id=None,
            service_pid=None,
            process_start_identity=None,
            endpoint_fingerprint=None,
            status="never_acquired",
            fenced_service_instance_id=None,
            fenced_lease_generation=None,
            updated_at=time.time() if now is None else now,
            resource_root_fingerprints=fingerprints,
        )

    def matches_domain(self, domain: RuntimeDomain) -> bool:
        return (
            self.repo_id == domain.repo_id
            and self.runtime_domain_id == domain.domain_id
            and self.mode == domain.mode
            and self.repo_root == _canonical_path_text(domain.repo_root, field="repo_root")
            and self.resource_root_fingerprints == _domain_resource_fingerprints(domain)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repo_id": self.repo_id,
            "runtime_domain_id": self.runtime_domain_id,
            "mode": self.mode,
            "repo_root": self.repo_root,
            "repo_root_fingerprint": self.repo_root_fingerprint,
            "last_lease_generation": self.last_lease_generation,
            "last_service_instance_id": self.last_service_instance_id,
            "service_pid": self.service_pid,
            "process_start_identity": self.process_start_identity,
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "status": self.status,
            "fenced_service_instance_id": self.fenced_service_instance_id,
            "fenced_lease_generation": self.fenced_lease_generation,
            "updated_at": self.updated_at,
            "resource_root_fingerprints": _fingerprints_to_dict(self.resource_root_fingerprints),
        }

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AuthorityGenerationRecord":
        if not isinstance(payload, Mapping) or set(payload) != _GENERATION_FIELDS:
            raise RuntimeLeaseError("authority-generation payload fields do not match schema")
        return cls(
            schema_version=payload["schema_version"],
            repo_id=payload["repo_id"],
            runtime_domain_id=payload["runtime_domain_id"],
            mode=payload["mode"],
            repo_root=payload["repo_root"],
            repo_root_fingerprint=payload["repo_root_fingerprint"],
            last_lease_generation=payload["last_lease_generation"],
            last_service_instance_id=payload["last_service_instance_id"],
            service_pid=payload["service_pid"],
            process_start_identity=payload["process_start_identity"],
            endpoint_fingerprint=payload["endpoint_fingerprint"],
            status=payload["status"],
            fenced_service_instance_id=payload["fenced_service_instance_id"],
            fenced_lease_generation=payload["fenced_lease_generation"],
            updated_at=payload["updated_at"],
            resource_root_fingerprints=_fingerprints_from_payload(payload["resource_root_fingerprints"]),
        )

    @classmethod
    def deserialize(cls, payload: str | Mapping[str, Any]) -> "AuthorityGenerationRecord":
        if isinstance(payload, str):
            try:
                value = json.loads(payload)
            except (TypeError, ValueError) as exc:
                raise RuntimeLeaseError("invalid authority-generation JSON") from exc
        else:
            value = payload
        if not isinstance(value, Mapping):
            raise RuntimeLeaseError("authority-generation payload must be an object")
        return cls.from_dict(value)


def generation_metadata_path(domain: RuntimeDomain) -> Path:
    return domain.cache_root / f"authority_generation.{domain.domain_id}.json"


def live_lease_path(domain: RuntimeDomain) -> Path:
    return domain.cache_root / f"authority_lease.{domain.domain_id}.json"


def domain_lock_path(domain: RuntimeDomain) -> Path:
    return domain.lock_root / f"authority.{domain.domain_id}.lock"


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            try:
                directory_fd = os.open(path.parent, os.O_RDONLY)
            except OSError:
                directory_fd = None
            if directory_fd is not None:
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _read_json(path: Path) -> Mapping[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeLeaseError(f"malformed durable JSON: {path.name}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeLeaseError(f"durable JSON must be an object: {path.name}")
    return value


_THREAD_LOCKS: dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _thread_lock_for(path: Path) -> threading.Lock:
    key = os.path.normcase(str(path))
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.Lock())


class _DomainFileLock(AbstractContextManager["_DomainFileLock"]):
    """OS-backed domain lock with an in-process guard for same-process threads."""

    def __init__(self, path: Path, *, timeout: float) -> None:
        self.path = path
        self.timeout = timeout
        self._thread_lock = _thread_lock_for(path)
        self._file: Any = None

    def __enter__(self) -> "_DomainFileLock":
        if not self._thread_lock.acquire(timeout=self.timeout):
            raise LeaseBusyError("timed out waiting for domain lock")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            open_deadline = time.monotonic() + self.timeout
            while True:
                try:
                    self._file = self.path.open("a+b")
                    break
                except PermissionError as exc:
                    if time.monotonic() >= open_deadline:
                        raise LeaseBusyError("timed out opening cross-process domain lock") from exc
                    time.sleep(0.01)
            if self.path.stat().st_size == 0:
                self._file.seek(0)
                self._file.write(b"0")
                self._file.flush()
            self._file.seek(0)
            self._acquire_os_lock()
            return self
        except Exception:
            self._close()
            self._thread_lock.release()
            raise

    def _acquire_os_lock(self) -> None:
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt

                    self._file.seek(0)
                    msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except (OSError, BlockingIOError) as exc:
                if time.monotonic() >= deadline:
                    raise LeaseBusyError("timed out waiting for cross-process domain lock") from exc
                time.sleep(0.01)

    def _close(self) -> None:
        if self._file is not None:
            try:
                if os.name == "nt":
                    import msvcrt

                    self._file.seek(0)
                    msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                self._file.close()
            finally:
                self._file = None

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            self._close()
        finally:
            self._thread_lock.release()


FailureInjector = Callable[[str], None]


class RuntimeLeaseManager:
    """Acquire, fence, refresh, bind, and release one RuntimeDomain authority."""

    def __init__(
        self,
        domain: RuntimeDomain,
        *,
        process_identity: ProcessIdentity | None = None,
        liveness_verifier: LivenessVerifier | None = None,
        known_production_roots: Iterable[str | Path] | None = None,
        known_test_roots: Iterable[str | Path] | None = None,
        lock_timeout: float = 10.0,
        clock: Callable[[], float] = time.time,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        _validate_domain_input(
            domain,
            known_production_roots=known_production_roots,
            known_test_roots=known_test_roots,
        )
        if lock_timeout <= 0 or not math.isfinite(lock_timeout):
            raise RuntimeLeaseError("lock_timeout must be finite and positive")
        self.domain = domain
        self.process_identity = process_identity or ProcessIdentity.current()
        self.liveness_verifier = liveness_verifier or DefaultLivenessVerifier()
        self.lock_timeout = lock_timeout
        self.clock = clock
        self.failure_injector = failure_injector

    def _lock(self) -> _DomainFileLock:
        return _DomainFileLock(domain_lock_path(self.domain), timeout=self.lock_timeout)

    def _now(self) -> float:
        return _timestamp(self.clock(), field="clock")

    def _inject(self, point: str) -> None:
        if self.failure_injector is not None:
            self.failure_injector(point)

    def read_generation(self) -> AuthorityGenerationRecord:
        with self._lock():
            return self._read_generation()

    def read_live_lease(self) -> RuntimeLease | None:
        with self._lock():
            return self._read_live_lease()

    def _read_generation(self) -> AuthorityGenerationRecord:
        payload = _read_json(generation_metadata_path(self.domain))
        if payload is None:
            return AuthorityGenerationRecord.initial(self.domain, now=self._now())
        record = AuthorityGenerationRecord.from_dict(payload)
        if not record.matches_domain(self.domain):
            raise ForeignLeaseError("authority-generation metadata belongs to another domain")
        return record

    def _read_live_lease(self) -> RuntimeLease | None:
        payload = _read_json(live_lease_path(self.domain))
        if payload is None:
            return None
        lease = RuntimeLease.from_dict(payload)
        if not lease.matches_domain(self.domain):
            raise ForeignLeaseError("live lease belongs to another domain")
        return lease

    def _write_generation(self, record: AuthorityGenerationRecord) -> None:
        if not record.matches_domain(self.domain):
            raise ForeignLeaseError("refusing to write foreign generation metadata")
        _atomic_write_json(generation_metadata_path(self.domain), record.to_dict())

    def _write_live_lease(self, lease: RuntimeLease) -> None:
        if not lease.matches_domain(self.domain):
            raise ForeignLeaseError("refusing to write foreign live lease")
        _atomic_write_json(live_lease_path(self.domain), lease.to_dict())

    def _remove_live_lease(self) -> None:
        try:
            live_lease_path(self.domain).unlink()
        except FileNotFoundError:
            pass

    def _new_lease(self, generation: int) -> RuntimeLease:
        now = self._now()
        fingerprints = _domain_resource_fingerprints(self.domain)
        return RuntimeLease(
            schema_version=RUNTIME_LEASE_SCHEMA_VERSION,
            repo_id=self.domain.repo_id,
            runtime_domain_id=self.domain.domain_id,
            mode=self.domain.mode,
            repo_root=_canonical_path_text(self.domain.repo_root, field="repo_root"),
            repo_root_fingerprint=dict(fingerprints)["repo_root"],
            service_instance_id=uuid.uuid4().hex,
            lease_generation=generation,
            service_pid=self.process_identity.pid,
            process_start_identity=self.process_identity.process_start_identity,
            endpoint_fingerprint=None,
            started_at=now,
            last_heartbeat_at=now,
            owner_token=uuid.uuid4().hex,
            resource_root_fingerprints=fingerprints,
        )

    @staticmethod
    def _same_owner(left: RuntimeLease, right: RuntimeLease) -> bool:
        return (
            left.runtime_domain_id == right.runtime_domain_id
            and left.service_instance_id == right.service_instance_id
            and left.lease_generation == right.lease_generation
        )

    def _fence_stale_lease(
        self,
        record: AuthorityGenerationRecord,
        lease: RuntimeLease,
    ) -> AuthorityGenerationRecord:
        if record.last_lease_generation != lease.lease_generation or record.last_service_instance_id != lease.service_instance_id:
            raise ForeignLeaseError("stale lease does not match durable generation record")
        fenced = replace(
            record,
            status="fenced",
            fenced_service_instance_id=lease.service_instance_id,
            fenced_lease_generation=lease.lease_generation,
            updated_at=self._now(),
        )
        self._write_generation(fenced)
        self._inject("after_fence_persist")
        self._remove_live_lease()
        return fenced

    def acquire(self) -> RuntimeLease:
        with self._lock():
            record = self._read_generation()
            live = self._read_live_lease()
            if live is not None:
                if record.status in {"released", "fenced"}:
                    same_fenced = (
                        record.fenced_service_instance_id == live.service_instance_id
                        and record.fenced_lease_generation == live.lease_generation
                    )
                    same_released = (
                        record.last_service_instance_id == live.service_instance_id
                        and record.last_lease_generation == live.lease_generation
                    )
                    same_identity = (
                        record.service_pid == live.service_pid
                        and record.process_start_identity == live.process_start_identity
                        and record.endpoint_fingerprint == live.endpoint_fingerprint
                    )
                    if not (same_fenced or same_released) or not same_identity:
                        raise ForeignLeaseError("fenced/released live lease does not match durable record")
                    self._remove_live_lease()
                    live = None
                else:
                    if record.status not in {"reserved", "active"}:
                        raise ForeignLeaseError("live lease is present for a non-owning generation status")
                    if (
                        record.last_lease_generation != live.lease_generation
                        or record.last_service_instance_id != live.service_instance_id
                        or record.service_pid != live.service_pid
                        or record.process_start_identity != live.process_start_identity
                        or record.endpoint_fingerprint != live.endpoint_fingerprint
                    ):
                        raise ForeignLeaseError("live lease and durable owner identity disagree")
                    evidence = self.liveness_verifier.verify(live)
                    if evidence.status is LivenessStatus.LIVE:
                        raise LeaseAlreadyHeld(evidence.reason)
                    if not evidence.confirmed_stale:
                        raise LeaseLivenessUnknown(
                            f"authority takeover rejected: {evidence.status.value}: {evidence.reason}"
                        )
                    reread = self._read_live_lease()
                    rerecord = self._read_generation()
                    if reread != live or rerecord != record:
                        raise LeaseLivenessUnknown("lease changed during stale verification")
                    record = self._fence_stale_lease(record, live)
                    live = None
            elif record.status == "active":
                raise LeaseRecoveryRequired(
                    "active durable authority has no live lease; recovery is required before takeover"
                )

            next_generation = record.last_lease_generation + 1
            lease = self._new_lease(next_generation)
            reserved = replace(
                record,
                last_lease_generation=next_generation,
                last_service_instance_id=lease.service_instance_id,
                service_pid=lease.service_pid,
                process_start_identity=lease.process_start_identity,
                endpoint_fingerprint=lease.endpoint_fingerprint,
                status="reserved",
                fenced_service_instance_id=None,
                fenced_lease_generation=None,
                updated_at=self._now(),
            )
            self._write_generation(reserved)
            self._inject("after_generation_reservation")
            self._write_live_lease(lease)
            self._inject("after_live_lease_persist")
            active = replace(reserved, status="active", updated_at=self._now())
            self._write_generation(active)
            self._inject("after_generation_activation")
            return lease

    def _assert_current_owner(self, lease: RuntimeLease) -> tuple[RuntimeLease, AuthorityGenerationRecord]:
        if not isinstance(lease, RuntimeLease) or not lease.matches_domain(self.domain):
            raise LeaseNotOwner("lease does not belong to this runtime domain")
        current = self._read_live_lease()
        record = self._read_generation()
        if current is None or not self._same_owner(current, lease):
            raise LeaseNotOwner("service instance/generation is not the current live owner")
        if (
            record.status != "active"
            or record.last_lease_generation != lease.lease_generation
            or record.last_service_instance_id != lease.service_instance_id
            or record.service_pid != current.service_pid
            or record.process_start_identity != current.process_start_identity
            or record.endpoint_fingerprint != current.endpoint_fingerprint
        ):
            raise LeaseNotOwner("service instance/generation has been durably fenced")
        return current, record

    def refresh_heartbeat(self, lease: RuntimeLease, *, now: float | None = None) -> RuntimeLease:
        with self._lock():
            current, _record = self._assert_current_owner(lease)
            refreshed = replace(current, last_heartbeat_at=self._now() if now is None else _timestamp(now, field="now"))
            if refreshed.last_heartbeat_at < refreshed.started_at:
                raise RuntimeLeaseError("heartbeat cannot precede lease start")
            self._write_live_lease(refreshed)
            return refreshed

    def bind_endpoint(self, lease: RuntimeLease, endpoint_fingerprint: str) -> RuntimeLease:
        endpoint = _non_empty_text(endpoint_fingerprint, field="endpoint_fingerprint")
        with self._lock():
            current, record = self._assert_current_owner(lease)
            if current.endpoint_fingerprint is not None and current.endpoint_fingerprint != endpoint:
                raise EndpointBindingError("endpoint fingerprint is already bound")
            bound = replace(current, endpoint_fingerprint=endpoint)
            self._write_live_lease(bound)
            self._write_generation(replace(record, endpoint_fingerprint=endpoint, updated_at=self._now()))
            return bound

    def reconcile_endpoint_binding(self, lease: RuntimeLease, endpoint_fingerprint: str) -> RuntimeLease:
        """Complete a durable bind after a crash between live and generation writes."""
        endpoint = _non_empty_text(endpoint_fingerprint, field="endpoint_fingerprint")
        with self._lock():
            if not isinstance(lease, RuntimeLease) or not lease.matches_domain(self.domain):
                raise LeaseNotOwner("lease does not belong to this runtime domain")
            current = self._read_live_lease()
            record = self._read_generation()
            if current is None or not self._same_owner(current, lease):
                raise LeaseNotOwner("service instance/generation is not the current live owner")
            if record.status != "active" or record.last_lease_generation != lease.lease_generation:
                raise LeaseNotOwner("service instance/generation is not active")
            if current.endpoint_fingerprint != endpoint:
                raise EndpointBindingError("live lease endpoint binding does not match reconciliation")
            if record.endpoint_fingerprint not in (None, endpoint):
                raise EndpointBindingError("durable generation endpoint binding conflicts")
            if record.endpoint_fingerprint is None:
                self._write_generation(replace(record, endpoint_fingerprint=endpoint, updated_at=self._now()))
            return current

    def release(self, lease: RuntimeLease) -> AuthorityGenerationRecord:
        with self._lock():
            current, record = self._assert_current_owner(lease)
            fenced = replace(
                record,
                status="released",
                fenced_service_instance_id=current.service_instance_id,
                fenced_lease_generation=current.lease_generation,
                updated_at=self._now(),
            )
            self._write_generation(fenced)
            self._inject("before_release_live_remove")
            self._remove_live_lease()
            return fenced


__all__ = [
    "AUTHORITY_GENERATION_SCHEMA_VERSION",
    "AuthorityGenerationRecord",
    "DefaultLivenessVerifier",
    "EndpointBindingError",
    "ForeignLeaseError",
    "GenerationStatus",
    "LeaseAlreadyHeld",
    "LeaseBusyError",
    "LeaseLivenessUnknown",
    "LeaseNotOwner",
    "LeaseRecoveryRequired",
    "LivenessResult",
    "LivenessStatus",
    "LivenessVerifier",
    "ProcessIdentity",
    "RUNTIME_LEASE_SCHEMA_VERSION",
    "RuntimeLease",
    "RuntimeLeaseError",
    "RuntimeLeaseManager",
    "domain_lock_path",
    "generation_metadata_path",
    "live_lease_path",
]

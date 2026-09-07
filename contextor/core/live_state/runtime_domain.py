"""Immutable runtime-domain identity and fail-closed resource validation.

This module deliberately has no runtime, IPC, lease, or persistence wiring.  It
only describes the resource namespace that a later authority bootstrap may
validate before touching any resource.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping

from contextor.core.paths import repo_cache_dir, runtime_logs_dir
from contextor.core.repository_identity import RepositoryIdentity


RUNTIME_DOMAIN_SCHEMA_VERSION = 1
RuntimeMode = Literal["production", "test"]


class RuntimeDomainError(ValueError):
    """Raised when a runtime domain is malformed or crosses an isolation boundary."""


def _canonical_path(value: str | Path, *, field: str) -> Path:
    if isinstance(value, bool) or not isinstance(value, (str, Path)):
        raise RuntimeDomainError(f"{field} must be a path")
    raw = str(value).strip()
    if not raw:
        raise RuntimeDomainError(f"{field} must not be empty")
    try:
        resolved = Path(raw).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise RuntimeDomainError(f"{field} cannot be canonicalized") from exc
    if not resolved.is_absolute():
        raise RuntimeDomainError(f"{field} must be absolute")
    return Path(os.path.normcase(str(resolved)))


def _canonical_optional_path(value: str | Path | None, *, field: str) -> Path | None:
    return None if value is None else _canonical_path(value, field=field)


def _is_same_or_nested(left: Path, right: Path) -> bool:
    try:
        left.relative_to(right)
        return True
    except ValueError:
        return False


def _overlaps(left: Path, right: Path) -> bool:
    return _is_same_or_nested(left, right) or _is_same_or_nested(right, left)


def _path_list(values: Iterable[str | Path] | None, *, field: str) -> tuple[Path, ...]:
    if values is None:
        return ()
    result: list[Path] = []
    for value in values:
        path = _canonical_path(value, field=field)
        if path not in result:
            result.append(path)
    return tuple(result)


def _identity_payload(
    *,
    mode: RuntimeMode,
    repo_id: str,
    repo_root: Path,
    cache_root: Path,
    logs_root: Path,
    lock_root: Path,
    ipc_endpoint_root: Path,
    test_context_root: Path | None,
    test_run_id: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": RUNTIME_DOMAIN_SCHEMA_VERSION,
        "mode": mode,
        "repo_id": repo_id,
        "repo_root": str(repo_root),
        "cache_root": str(cache_root),
        "logs_root": str(logs_root),
        "lock_root": str(lock_root),
        "ipc_endpoint_root": str(ipc_endpoint_root),
        "test_context_root": (
            None if test_context_root is None else str(test_context_root)
        ),
        "test_run_id": test_run_id,
    }


def _domain_payload(
    *,
    mode: RuntimeMode,
    repo_id: str,
    repo_root: Path,
    cache_root: Path,
    logs_root: Path,
    lock_root: Path,
    ipc_endpoint_root: Path,
    test_context_root: Path | None,
    service_instance_id: str | None,
    test_run_id: str | None,
) -> dict[str, Any]:
    payload = _identity_payload(
        mode=mode,
        repo_id=repo_id,
        repo_root=repo_root,
        cache_root=cache_root,
        logs_root=logs_root,
        lock_root=lock_root,
        ipc_endpoint_root=ipc_endpoint_root,
        test_context_root=test_context_root,
        test_run_id=test_run_id,
    )
    # The service instance is serialized for runtime fencing, never identity.
    payload["service_instance_id"] = service_instance_id
    return payload


def _domain_id(payload: Mapping[str, Any]) -> str:
    identity_payload = dict(payload)
    identity_payload.pop("service_instance_id", None)
    encoded = json.dumps(
        identity_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return f"rd{RUNTIME_DOMAIN_SCHEMA_VERSION}_{hashlib.sha256(encoded).hexdigest()}"


def _validate_root_relationships(
    *,
    repo_root: Path,
    roots: Mapping[str, Path],
) -> None:
    for name, path in roots.items():
        if _overlaps(path, repo_root):
            raise RuntimeDomainError(
                f"{name} overlaps the analyzed repository root and would violate read-only ownership"
            )

    # The existing production layout intentionally nests LIVE lock/endpoint
    # paths under the repository cache.  That containment is allowed.  Logs
    # must remain a separate owner; exact aliases between lock and endpoint
    # resources are not allowed.
    if _overlaps(roots["logs_root"], roots["cache_root"]):
        raise RuntimeDomainError("logs_root overlaps cache_root")
    if roots["lock_root"] == roots["ipc_endpoint_root"]:
        raise RuntimeDomainError("lock_root and ipc_endpoint_root may not be aliases")
    for nested_name in ("lock_root", "ipc_endpoint_root"):
        nested = roots[nested_name]
        if not _is_same_or_nested(nested, roots["cache_root"]):
            raise RuntimeDomainError(
                f"{nested_name} must be owned by cache_root for this runtime layout"
            )


def _validate_resource_context(
    *,
    mode: RuntimeMode,
    roots: Mapping[str, Path],
    test_context_root: Path | None,
    known_production_roots: tuple[Path, ...],
    known_test_roots: tuple[Path, ...],
) -> None:
    if mode == "test":
        if test_context_root is None:
            raise RuntimeDomainError("test mode requires an explicit test_context_root")
        for name, path in roots.items():
            if not _is_same_or_nested(path, test_context_root):
                raise RuntimeDomainError(
                    f"{name} is outside the explicit test domain root"
                )
        if not known_production_roots:
            raise RuntimeDomainError(
                "test mode requires known production resource roots for fail-closed isolation"
            )
        for path in roots.values():
            if any(_overlaps(path, production) for production in known_production_roots):
                raise RuntimeDomainError(
                    "test domain resource overlaps an explicitly supplied production resource"
                )
        if any(_overlaps(test_context_root, production) for production in known_production_roots):
            raise RuntimeDomainError(
                "test_context_root overlaps an explicitly supplied production resource"
            )
    else:
        if test_context_root is not None:
            raise RuntimeDomainError("production mode may not provide test_context_root")
        for path in roots.values():
            if any(_overlaps(path, test_root) for test_root in known_test_roots):
                raise RuntimeDomainError(
                    "production resource overlaps an explicitly supplied test resource"
                )


def _validate_structural_fields(domain: "RuntimeDomain") -> None:
    if domain.mode not in ("production", "test"):
        raise RuntimeDomainError("mode must be 'production' or 'test'")
    if not domain.repo_id.strip():
        raise RuntimeDomainError("repo_id must not be empty")
    if domain.mode == "test" and not (domain.test_run_id or "").strip():
        raise RuntimeDomainError("test mode requires a non-empty test_run_id")
    if domain.mode == "test" and domain.test_context_root is None:
        raise RuntimeDomainError("test mode requires an explicit test_context_root")
    if domain.mode == "production" and domain.test_context_root is not None:
        raise RuntimeDomainError("production mode may not provide test_context_root")
    if domain.mode == "production" and domain.test_run_id is not None:
        raise RuntimeDomainError("production mode forbids test_run_id")
    if domain.service_instance_id is not None and not domain.service_instance_id.strip():
        raise RuntimeDomainError("service_instance_id must be non-empty when supplied")
    roots = {
        "cache_root": domain.cache_root,
        "logs_root": domain.logs_root,
        "lock_root": domain.lock_root,
        "ipc_endpoint_root": domain.ipc_endpoint_root,
    }
    _validate_root_relationships(repo_root=domain.repo_root, roots=roots)
    if domain.test_context_root is not None:
        if _overlaps(domain.test_context_root, domain.repo_root):
            raise RuntimeDomainError(
                "test_context_root overlaps the analyzed repository root"
            )
        for name, path in roots.items():
            if not _is_same_or_nested(path, domain.test_context_root):
                raise RuntimeDomainError(
                    f"{name} is outside the intrinsic test domain root"
                )
    identity_payload = _identity_payload(
        mode=domain.mode,
        repo_id=domain.repo_id,
        repo_root=domain.repo_root,
        cache_root=domain.cache_root,
        logs_root=domain.logs_root,
        lock_root=domain.lock_root,
        ipc_endpoint_root=domain.ipc_endpoint_root,
        test_context_root=domain.test_context_root,
        test_run_id=domain.test_run_id,
    )
    if domain.domain_id != _domain_id(identity_payload):
        raise RuntimeDomainError("domain_id does not match the immutable domain identity")


@dataclass(frozen=True, slots=True)
class RuntimeDomain:
    """Immutable, serializable namespace for one Contextor runtime domain."""

    domain_id: str
    mode: RuntimeMode
    repo_id: str
    repo_root: Path
    cache_root: Path
    logs_root: Path
    lock_root: Path
    ipc_endpoint_root: Path
    test_context_root: Path | None = None
    service_instance_id: str | None = None
    test_run_id: str | None = None

    def __post_init__(self) -> None:
        canonical = {
            "repo_root": _canonical_path(self.repo_root, field="repo_root"),
            "cache_root": _canonical_path(self.cache_root, field="cache_root"),
            "logs_root": _canonical_path(self.logs_root, field="logs_root"),
            "lock_root": _canonical_path(self.lock_root, field="lock_root"),
            "ipc_endpoint_root": _canonical_path(
                self.ipc_endpoint_root,
                field="ipc_endpoint_root",
            ),
            "test_context_root": _canonical_optional_path(
                self.test_context_root,
                field="test_context_root",
            ),
        }
        for name, value in canonical.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "repo_id", str(self.repo_id).strip())
        if self.service_instance_id is not None:
            object.__setattr__(self, "service_instance_id", str(self.service_instance_id).strip())
        if self.test_run_id is not None:
            object.__setattr__(self, "test_run_id", str(self.test_run_id).strip())
        _validate_structural_fields(self)

    @classmethod
    def create(
        cls,
        *,
        repo_id: str,
        repo_root: str | Path,
        mode: RuntimeMode,
        cache_root: str | Path | None = None,
        logs_root: str | Path | None = None,
        lock_root: str | Path | None = None,
        ipc_endpoint_root: str | Path | None = None,
        service_instance_id: str | None = None,
        test_run_id: str | None = None,
        test_context_root: str | Path | None = None,
        known_production_roots: Iterable[str | Path] | None = None,
        known_test_roots: Iterable[str | Path] | None = None,
    ) -> "RuntimeDomain":
        """Construct and validate without creating or opening any resource."""

        if mode not in ("production", "test"):
            raise RuntimeDomainError("mode must be 'production' or 'test'")
        canonical_repo_root = _canonical_path(repo_root, field="repo_root")
        if not str(repo_id).strip():
            raise RuntimeDomainError("repo_id must not be empty")
        context = _canonical_optional_path(test_context_root, field="test_context_root")
        production_roots = _path_list(
            known_production_roots,
            field="known_production_root",
        )
        test_roots = _path_list(known_test_roots, field="known_test_root")

        if mode == "production":
            # These defaults are the existing Contextor path authority.  They
            # only resolve/read identity metadata; they do not create files.
            cache = _canonical_path(
                cache_root if cache_root is not None else repo_cache_dir(canonical_repo_root),
                field="cache_root",
            )
            logs = _canonical_path(
                logs_root if logs_root is not None else runtime_logs_dir(),
                field="logs_root",
            )
        else:
            if cache_root is None or logs_root is None:
                raise RuntimeDomainError(
                    "test mode requires explicit cache_root and logs_root"
                )
            cache = _canonical_path(cache_root, field="cache_root")
            logs = _canonical_path(logs_root, field="logs_root")

        lock = _canonical_path(
            lock_root if lock_root is not None else cache / "runtime",
            field="lock_root",
        )
        endpoint = _canonical_path(
            ipc_endpoint_root if ipc_endpoint_root is not None else cache,
            field="ipc_endpoint_root",
        )
        roots = {
            "cache_root": cache,
            "logs_root": logs,
            "lock_root": lock,
            "ipc_endpoint_root": endpoint,
        }
        _validate_root_relationships(repo_root=canonical_repo_root, roots=roots)
        _validate_resource_context(
            mode=mode,
            roots=roots,
            test_context_root=context,
            known_production_roots=production_roots,
            known_test_roots=test_roots,
        )

        payload = _domain_payload(
            mode=mode,
            repo_id=str(repo_id).strip(),
            repo_root=canonical_repo_root,
            cache_root=cache,
            logs_root=logs,
            lock_root=lock,
            ipc_endpoint_root=endpoint,
            test_context_root=context,
            service_instance_id=(
                None if service_instance_id is None else str(service_instance_id).strip()
            ),
            test_run_id=None if test_run_id is None else str(test_run_id).strip(),
        )
        identity_payload = _identity_payload(
            mode=mode,
            repo_id=str(repo_id).strip(),
            repo_root=canonical_repo_root,
            cache_root=cache,
            logs_root=logs,
            lock_root=lock,
            ipc_endpoint_root=endpoint,
            test_context_root=context,
            test_run_id=None if test_run_id is None else str(test_run_id).strip(),
        )
        return cls(domain_id=_domain_id(identity_payload), **{key: identity_payload[key] for key in (
            "mode",
            "repo_id",
        )}, **{
            "repo_root": canonical_repo_root,
            "cache_root": cache,
            "logs_root": logs,
            "lock_root": lock,
            "ipc_endpoint_root": endpoint,
            "test_context_root": context,
            "service_instance_id": payload["service_instance_id"],
            "test_run_id": payload["test_run_id"],
        })

    @classmethod
    def from_identity(
        cls,
        identity: RepositoryIdentity,
        **kwargs: Any,
    ) -> "RuntimeDomain":
        """Construct from the existing canonical repository identity owner."""

        if not isinstance(identity, RepositoryIdentity):
            raise RuntimeDomainError("identity must be RepositoryIdentity")
        return cls.create(
            repo_id=identity.repo_id,
            repo_root=identity.root_path,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = _domain_payload(
            mode=self.mode,
            repo_id=self.repo_id,
            repo_root=self.repo_root,
            cache_root=self.cache_root,
            logs_root=self.logs_root,
            lock_root=self.lock_root,
            ipc_endpoint_root=self.ipc_endpoint_root,
            test_context_root=self.test_context_root,
            service_instance_id=self.service_instance_id,
            test_run_id=self.test_run_id,
        )
        payload["domain_id"] = self.domain_id
        return payload

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RuntimeDomain":
        if not isinstance(payload, Mapping):
            raise RuntimeDomainError("RuntimeDomain payload must be a mapping")
        expected = {
            "schema_version",
            "domain_id",
            "mode",
            "repo_id",
            "repo_root",
            "cache_root",
            "logs_root",
            "lock_root",
            "ipc_endpoint_root",
            "test_context_root",
            "service_instance_id",
            "test_run_id",
        }
        if set(payload) != expected:
            raise RuntimeDomainError("RuntimeDomain payload fields do not match schema")
        if payload["schema_version"] != RUNTIME_DOMAIN_SCHEMA_VERSION:
            raise RuntimeDomainError("unsupported RuntimeDomain schema_version")
        return cls(
            domain_id=str(payload["domain_id"]),
            mode=payload["mode"],
            repo_id=str(payload["repo_id"]),
            repo_root=payload["repo_root"],
            cache_root=payload["cache_root"],
            logs_root=payload["logs_root"],
            lock_root=payload["lock_root"],
            ipc_endpoint_root=payload["ipc_endpoint_root"],
            test_context_root=payload["test_context_root"],
            service_instance_id=payload["service_instance_id"],
            test_run_id=payload["test_run_id"],
        )

    @classmethod
    def deserialize(cls, payload: str | Mapping[str, Any]) -> "RuntimeDomain":
        if isinstance(payload, str):
            try:
                value = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise RuntimeDomainError("invalid RuntimeDomain JSON") from exc
        else:
            value = payload
        return cls.from_dict(value)


def validate_runtime_domain(
    domain: RuntimeDomain,
    *,
    expected_mode: RuntimeMode | None = None,
    test_context_root: str | Path | None = None,
    known_production_roots: Iterable[str | Path] | None = None,
    known_test_roots: Iterable[str | Path] | None = None,
) -> RuntimeDomain:
    """Validate a domain before a later bootstrap touches any resource."""

    if not isinstance(domain, RuntimeDomain):
        raise RuntimeDomainError("domain must be RuntimeDomain")
    if expected_mode is not None and domain.mode != expected_mode:
        raise RuntimeDomainError("runtime domain mode does not match expected mode")
    provided_context = _canonical_optional_path(
        test_context_root,
        field="test_context_root",
    )
    if domain.mode == "test":
        context = domain.test_context_root
        if provided_context is not None and provided_context != context:
            raise RuntimeDomainError(
                "explicit test_context_root does not match the domain boundary"
            )
    else:
        context = provided_context
    roots = {
        "cache_root": domain.cache_root,
        "logs_root": domain.logs_root,
        "lock_root": domain.lock_root,
        "ipc_endpoint_root": domain.ipc_endpoint_root,
    }
    _validate_resource_context(
        mode=domain.mode,
        roots=roots,
        test_context_root=context,
        known_production_roots=_path_list(known_production_roots, field="known_production_root"),
        known_test_roots=_path_list(known_test_roots, field="known_test_root"),
    )
    return domain


__all__ = [
    "RUNTIME_DOMAIN_SCHEMA_VERSION",
    "RuntimeDomain",
    "RuntimeDomainError",
    "RuntimeMode",
    "validate_runtime_domain",
]

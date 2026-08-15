"""Read-only repository identity shared by registry, cache and LIVE."""

from __future__ import annotations

import json
import datetime
import hashlib
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


class RepositoryIdentityError(ValueError):
    """Repository metadata is missing, malformed or belongs to another root."""


@dataclass(frozen=True)
class RepositoryIdentity:
    repo_id: str
    root_path: str
    repo_name: str


def _central_root() -> Path:
    from contextor.core.paths import repository_registry_root

    return repository_registry_root()


def _identity_from_meta(meta_path: Path, expected_root: Path) -> RepositoryIdentity:
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        repo_id = str(payload["repo_id"])
        stored_root = Path(payload["root_path"]).expanduser().resolve()
        repo_name = str(payload["repo_name"])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise RepositoryIdentityError(f"Malformed repository identity: {meta_path}") from exc

    if not repo_id.startswith("ctx_") or len(repo_id) <= 4:
        raise RepositoryIdentityError(f"Invalid repository ID in {meta_path}")
    if stored_root != expected_root:
        raise RepositoryIdentityError(
            f"Repository identity root mismatch: stored={stored_root}, selected={expected_root}"
        )
    if repo_name != expected_root.name:
        raise RepositoryIdentityError(
            f"Repository identity name mismatch: stored={repo_name}, selected={expected_root.name}"
        )
    expected_directory = f"{repo_name}__{repo_id}"
    if meta_path.parent.name != expected_directory:
        raise RepositoryIdentityError(
            f"Repository identity directory must be named {expected_directory}"
        )
    return RepositoryIdentity(repo_id, str(expected_root), repo_name)


def _find_identity(repo_root: Path) -> tuple[RepositoryIdentity, Path] | None:
    registry_root = _central_root()
    if not registry_root.is_dir():
        return None
    matches = []
    for meta_path in registry_root.glob(f"{repo_root.name}__ctx_*/repo.meta.json"):
        try:
            identity = _identity_from_meta(meta_path, repo_root)
        except RepositoryIdentityError:
            continue
        matches.append((identity, meta_path.parent))
    if len(matches) > 1:
        raise RepositoryIdentityError(
            f"Multiple central identities exist for repository root: {repo_root}"
        )
    return matches[0] if matches else None


def registry_meta_path(repo_root: str | Path) -> Path | None:
    """Return the central metadata path for a registered repository."""

    found = _find_identity(Path(repo_root).expanduser().resolve())
    return found[1] / "repo.meta.json" if found else None


def read_repository_identity(
    repo_root: str | Path,
) -> RepositoryIdentity | None:
    """Return and validate the durable identity for one repository root."""

    root = Path(repo_root).expanduser().resolve()
    found = _find_identity(root)
    return found[0] if found else None


def registered_repository_ids() -> set[str]:
    """Return IDs backed by valid metadata in Contextor's central registry."""

    registry_root = _central_root()
    if not registry_root.is_dir():
        return set()
    identities = set()
    for meta_path in registry_root.glob("*__ctx_*/repo.meta.json"):
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            root = Path(payload["root_path"]).expanduser().resolve()
            identity = _identity_from_meta(meta_path, root)
        except (OSError, ValueError, TypeError, KeyError, RepositoryIdentityError):
            continue
        identities.add(identity.repo_id)
    return identities


def ensure_repository_identity(
    repo_root: str | Path,
) -> tuple[RepositoryIdentity, Path]:
    """Find or atomically create a central identity directory for one root."""

    root = Path(repo_root).expanduser().resolve()
    registry_root = _central_root()
    registry_root.mkdir(parents=True, exist_ok=True)
    root_digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:12]
    lock_path = registry_root / f".{root.name}.{root_digest}.identity.lock"
    deadline = time.monotonic() + 5.0
    descriptor = None
    while descriptor is None:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > 30:
                    lock_path.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out creating repository identity for {root}")
            time.sleep(0.02)
    try:
        found = _find_identity(root)
        if found:
            return found
        repo_id = f"ctx_{uuid.uuid4().hex[:8]}"
        identity = RepositoryIdentity(repo_id, str(root), root.name)
        directory = registry_root / f"{root.name}__{repo_id}"
        directory.mkdir(parents=False, exist_ok=False)
        payload = {
            "schema_version": 1,
            "repo_id": repo_id,
            "repo_name": root.name,
            "root_path": str(root),
            "created_at": datetime.datetime.now().isoformat(),
        }
        temporary = directory / "repo.meta.json.tmp"
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temporary, directory / "repo.meta.json")
        return identity, directory
    finally:
        os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def require_repository_identity(repo_root: str | Path) -> RepositoryIdentity:
    identity = read_repository_identity(repo_root)
    if identity is None:
        raise RepositoryIdentityError(
            f"Repository is not registered: {Path(repo_root).expanduser().resolve()}"
        )
    return identity

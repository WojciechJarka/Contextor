from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from contextor.core.repository_identity import (
    RepositoryIdentity,
    RepositoryIdentityError,
    _identity_from_meta,
)


class RegistryMigrationError(RuntimeError):
    """Registry cannot be inventoried for migration."""


@dataclass(frozen=True)
class RegistryFileEvidence:
    name: str
    sha256: str
    size: int


@dataclass(frozen=True)
class RegistryMigrationInventory:
    identity: RepositoryIdentity
    directory: Path
    files: tuple[RegistryFileEvidence, ...]


REGISTRY_JSON_FILES = frozenset({
    "repo.meta.json",
    "module_slots.json",
    "artifact_slots.json",
    "module_recovery.json",
    "artifact_recovery.json",
    "output_references.json",
    "module_registry.json",
    "artifact_registry.json",
})


def _assert_plain_directory_path(path: str | Path) -> Path:
    """
    Reject existing path components that are links or
    Windows reparse points before following the path.

    This is a read-only observation, not an atomic
    filesystem security boundary.
    """
    supplied = Path(path).expanduser()

    if ".." in supplied.parts:
        raise RegistryMigrationError(
            "Registry path contains parent traversal"
        )

    directory = Path(os.path.abspath(supplied))
    components = tuple(
        reversed((directory, *directory.parents))
    )

    for component in components:
        try:
            info = component.lstat()
        except OSError as exc:
            raise RegistryMigrationError(
                f"Registry path component is inaccessible: "
                f"{component}"
            ) from exc

        if stat.S_ISLNK(info.st_mode):
            raise RegistryMigrationError(
                f"Registry path contains a symbolic link: "
                f"{component}"
            )

        if os.name == "nt" and (
            getattr(info, "st_file_attributes", 0)
            & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise RegistryMigrationError(
                f"Registry path contains a reparse point: "
                f"{component}"
            )

        if not stat.S_ISDIR(info.st_mode):
            raise RegistryMigrationError(
                f"Registry path component is not a directory: "
                f"{component}"
            )

    return directory


def _read_stable_file(path: Path) -> bytes:
    before = path.stat(follow_symlinks=False)

    if not stat.S_ISREG(before.st_mode):
        raise RegistryMigrationError(
            f"Not a regular registry file: {path.name}"
        )

    if os.name == "nt" and (
        getattr(before, "st_file_attributes", 0)
        & stat.FILE_ATTRIBUTE_REPARSE_POINT
    ):
        raise RegistryMigrationError(
            f"Registry file is a reparse point: {path.name}"
        )

    with path.open("rb") as stream:
        data = stream.read()

    after = path.stat(follow_symlinks=False)

    def file_identity(info):
        return (
            info.st_dev,
            info.st_ino,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        )

    if file_identity(before) != file_identity(after):
        raise RegistryMigrationError(
            f"Registry file changed during read: {path.name}"
        )

    if len(data) != after.st_size:
        raise RegistryMigrationError(
            f"Registry file size changed: {path.name}"
        )

    return data


def inspect_registry_for_migration(
    repo_root: str | Path,
    registry_directory: str | Path,
) -> RegistryMigrationInventory:
    """
    Read-only migration inventory.

    Does not authorize migration or prove historical
    authenticity. Does not provide race-free access.
    """
    root = Path(repo_root).expanduser().resolve()

    try:
        directory = _assert_plain_directory_path(
            registry_directory
        )

        entries = tuple(directory.iterdir())
        names = {entry.name for entry in entries}

        if len(entries) != len(names):
            raise RegistryMigrationError(
                "Duplicate registry entries"
            )

        if (
            "transaction.tmp" in names
            or any(name.endswith(".json.tmp") for name in names)
        ):
            raise RegistryMigrationError(
                "Registry contains an unfinished transaction"
            )

        if not REGISTRY_JSON_FILES <= names:
            raise RegistryMigrationError(
                "Registry is missing required files"
            )

        unexpected = names - REGISTRY_JSON_FILES - {".lock"}
        if unexpected:
            raise RegistryMigrationError(
                "Registry contains unexpected files"
            )

        for entry in entries:
            info = entry.lstat()

            if not stat.S_ISREG(info.st_mode):
                raise RegistryMigrationError(
                    f"Unexpected registry entry type: {entry.name}"
                )

            if os.name == "nt" and (
                getattr(info, "st_file_attributes", 0)
                & stat.FILE_ATTRIBUTE_REPARSE_POINT
            ):
                raise RegistryMigrationError(
                    f"Registry entry is a reparse point: "
                    f"{entry.name}"
                )

        evidence = []
        payloads = {}

        for name in sorted(REGISTRY_JSON_FILES):
            data = _read_stable_file(directory / name)

            try:
                payload = json.loads(data)
            except (UnicodeDecodeError, ValueError) as exc:
                raise RegistryMigrationError(
                    f"Malformed registry JSON: {name}"
                ) from exc

            if not isinstance(payload, dict):
                raise RegistryMigrationError(
                    f"Registry JSON is not an object: {name}"
                )

            payloads[name] = payload
            evidence.append(
                RegistryFileEvidence(
                    name=name,
                    sha256=hashlib.sha256(data).hexdigest(),
                    size=len(data),
                )
            )

        try:
            identity = _identity_from_meta(
                directory / "repo.meta.json",
                root,
            )
        except RepositoryIdentityError as exc:
            raise RegistryMigrationError(
                "Repository identity is inconsistent"
            ) from exc

        for kind in ("module", "artifact"):
            registry = payloads[f"{kind}_registry.json"]
            forward = registry.get("path_to_id")
            reverse = registry.get("id_to_path")

            if not isinstance(forward, dict) or not isinstance(
                reverse, dict
            ):
                raise RegistryMigrationError(
                    f"Invalid {kind} registry mappings"
                )

            if (
                len(set(forward.values())) != len(forward)
                or len(forward) != len(reverse)
                or any(
                    reverse.get(identifier) != name
                    for name, identifier in forward.items()
                )
            ):
                raise RegistryMigrationError(
                    f"Inconsistent {kind} registry mappings"
                )

        for item in evidence:
            current = _read_stable_file(
                directory / item.name
            )
            if (
                len(current) != item.size
                or hashlib.sha256(current).hexdigest()
                != item.sha256
            ):
                raise RegistryMigrationError(
                    f"Registry changed during inventory: "
                    f"{item.name}"
                )

        if {entry.name for entry in directory.iterdir()} != names:
            raise RegistryMigrationError(
                "Registry entries changed during inventory"
            )

        _assert_plain_directory_path(registry_directory)

        return RegistryMigrationInventory(
            identity=identity,
            directory=directory,
            files=tuple(evidence),
        )

    except RegistryMigrationError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise RegistryMigrationError(
            "Cannot inspect registry for migration"
        ) from exc

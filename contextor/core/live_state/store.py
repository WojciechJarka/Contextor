"""Atomic, revisioned snapshot store shared by desktop and MCP processes."""

from __future__ import annotations

import json
import os
import pickle
import shutil
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

LIVE_STATE_SCHEMA_VERSION = "1.2"


@dataclass(frozen=True)
class LiveStateMetadata:
    schema_version: str = LIVE_STATE_SCHEMA_VERSION
    state_id: str = ""
    revision: int = 0
    writer: str = "unknown"
    repo_id: str = ""
    root_path: str = ""


def _paths(cache_dir: str | Path) -> tuple[Path, Path, Path]:
    root = Path(cache_dir)
    return root / "engine_state.pkl", root / "engine_state.meta.json", root / "engine_state.lock"


def read_metadata(cache_dir: str | Path) -> LiveStateMetadata | None:
    """Read snapshot metadata without loading the potentially large pickle."""

    _, meta_file, _ = _paths(cache_dir)
    try:
        payload = json.loads(meta_file.read_text(encoding="utf-8"))
        if payload.get("schema_version") not in {
            "1.0", "1.1", LIVE_STATE_SCHEMA_VERSION
        }:
            return None
        return LiveStateMetadata(
            schema_version=str(payload.get("schema_version", "1.0")),
            state_id=str(payload.get("state_id", "")),
            revision=int(payload.get("revision", 0)),
            writer=str(payload.get("writer", "legacy")),
            repo_id=str(payload.get("repo_id", "")),
            root_path=str(payload.get("root_path", "")),
        )
    except (OSError, ValueError, TypeError):
        return None


def _acquire_lock(lock_file: Path, timeout: float = 5.0) -> int:
    deadline = time.monotonic() + timeout
    while True:
        try:
            return os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (FileExistsError, PermissionError):
            try:
                if time.time() - lock_file.stat().st_mtime > 30:
                    lock_file.unlink()
                    continue

            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for LIVE state lock: {lock_file}")
            time.sleep(0.02)


def save_snapshot(
    state: Any,
    cache_dir: str | Path,
    state_id: str,
    *,
    writer: str = "unknown",
    repo_id: str = "",
    root_path: str = "",
    revision_floor: int = 0,
) -> LiveStateMetadata:
    """Atomically publish a complete snapshot and monotonically increasing revision."""

    state_file, meta_file, lock_file = _paths(cache_dir)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = _acquire_lock(lock_file)
    token = uuid.uuid4().hex
    state_tmp = state_file.with_name(f".{state_file.name}.{token}.tmp")
    meta_tmp = meta_file.with_name(f".{meta_file.name}.{token}.tmp")
    try:
        current = read_metadata(cache_dir)
        normalized_root = (
            str(Path(root_path).expanduser().resolve()) if root_path else ""
        )
        if current and repo_id and current.repo_id and current.repo_id != repo_id:
            raise ValueError("Snapshot repository ID does not match existing metadata.")
        if (
            current
            and normalized_root
            and current.root_path
            and Path(current.root_path).expanduser().resolve() != Path(normalized_root)
        ):
            raise ValueError("Snapshot repository root does not match existing metadata.")
        metadata = LiveStateMetadata(
            state_id=state_id,
            revision=max(current.revision if current else 0, revision_floor) + 1,
            writer=writer,
            repo_id=repo_id,
            root_path=normalized_root,
        )
        with state_tmp.open("wb") as stream:
            pickle.dump({"metadata": asdict(metadata), "state": state}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        meta_tmp.write_text(json.dumps(asdict(metadata), indent=2), encoding="utf-8")
        os.replace(state_tmp, state_file)
        os.replace(meta_tmp, meta_file)
        return metadata
    finally:
        for temporary in (state_tmp, meta_tmp):
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        os.close(lock_fd)
        try:
            lock_file.unlink()
        except FileNotFoundError:
            pass


def load_snapshot(
    cache_dir: str | Path,
    expected_state_id: str = "",
    *,
    expected_repo_id: str = "",
    expected_root_path: str = "",
) -> tuple[Any, LiveStateMetadata] | None:
    """Load one complete published snapshot, rejecting incompatible identities."""

    state_file, _, _ = _paths(cache_dir)
    metadata = read_metadata(cache_dir)
    normalized_root = (
        str(Path(expected_root_path).expanduser().resolve())
        if expected_root_path
        else ""
    )
    if metadata is None or (expected_state_id and metadata.state_id != expected_state_id):
        return None
    if expected_repo_id and metadata.repo_id != expected_repo_id:
        return None
    if normalized_root and (
        not metadata.root_path
        or Path(metadata.root_path).expanduser().resolve() != Path(normalized_root)
    ):
        return None
    try:
        with state_file.open("rb") as stream:
            payload = pickle.load(stream)
        if isinstance(payload, dict) and set(payload) == {"metadata", "state"}:
            embedded = payload["metadata"]
            embedded_metadata = LiveStateMetadata(
                schema_version=str(embedded.get("schema_version", "1.0")),
                state_id=str(embedded.get("state_id", "")),
                revision=int(embedded.get("revision", 0)),
                writer=str(embedded.get("writer", "unknown")),
                repo_id=str(embedded.get("repo_id", "")),
                root_path=str(embedded.get("root_path", "")),
            )
            state_obj = payload["state"]
            if state_obj is not None and hasattr(state_obj, "__dict__"):
                if not hasattr(state_obj, "module_usages"):
                    try:
                        setattr(state_obj, "module_usages", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "topology_analytics"):
                    try:
                        setattr(state_obj, "topology_analytics", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "topology_metrics_state"):
                    try:
                        setattr(state_obj, "topology_metrics_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cached_analytics"):
                    try:
                        setattr(state_obj, "cached_analytics", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cached_analytics_state"):
                    try:
                        setattr(state_obj, "cached_analytics_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cycles"):
                    try:
                        setattr(state_obj, "cycles", [])
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cycles_state"):
                    try:
                        setattr(state_obj, "cycles_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "collision_facts"):
                    try:
                        setattr(state_obj, "collision_facts", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "collisions"):
                    try:
                        setattr(state_obj, "collisions", [])
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "collisions_state"):
                    try:
                        setattr(state_obj, "collisions_state", "deferred")
                    except AttributeError:
                        pass
            return state_obj, embedded_metadata
        if payload is not None and hasattr(payload, "__dict__"):
            if not hasattr(payload, "module_usages"):
                try:
                    setattr(payload, "module_usages", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "topology_analytics"):
                try:
                    setattr(payload, "topology_analytics", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "topology_metrics_state"):
                try:
                    setattr(payload, "topology_metrics_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "cached_analytics"):
                try:
                    setattr(payload, "cached_analytics", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "cached_analytics_state"):
                try:
                    setattr(payload, "cached_analytics_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "cycles"):
                try:
                    setattr(payload, "cycles", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "cycles_state"):
                try:
                    setattr(payload, "cycles_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "collision_facts"):
                try:
                    setattr(payload, "collision_facts", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "collisions"):
                try:
                    setattr(payload, "collisions", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "collisions_state"):
                try:
                    setattr(payload, "collisions_state", "deferred")
                except AttributeError:
                    pass
        return payload, metadata




    except (OSError, pickle.PickleError, EOFError):
        return None



def migrate_legacy_snapshot(repo_root: str | Path) -> Path:
    """Copy a verified path-keyed snapshot into its repo-ID cache directory."""

    from contextor.core.paths import legacy_repo_cache_dir, repo_cache_dir
    from contextor.core.repository_identity import require_repository_identity

    root = Path(repo_root).expanduser().resolve()
    identity = require_repository_identity(root)
    target = repo_cache_dir(root)
    if read_metadata(target) is not None:
        return target

    legacy = legacy_repo_cache_dir(root)
    if legacy == target:
        return target
    loaded = load_snapshot(legacy)
    if loaded is None:
        return target

    state, metadata = loaded
    save_snapshot(
        state,
        target,
        metadata.state_id,
        writer=f"migration:{metadata.writer}",
        repo_id=identity.repo_id,
        root_path=identity.root_path,
        revision_floor=metadata.revision,
    )
    legacy_file_state = legacy / "file_state.json"
    target_file_state = target / "file_state.json"
    if legacy_file_state.is_file() and not target_file_state.exists():
        target_file_state.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_file_state, target_file_state)
    return target

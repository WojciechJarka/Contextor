"""Atomic, revisioned snapshot store shared by desktop and MCP processes."""

from __future__ import annotations

import json
import os
import pickle
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

LIVE_STATE_SCHEMA_VERSION = "1.2"


class _LegacySymbolCallFact:
    """Unpickle-only shape used by a transient pre-tuple snapshot format."""


class _SnapshotUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str):
        if (
            module == "contextor.core.domain.usage_facts"
            and name == "SymbolCallFact"
        ):
            return _LegacySymbolCallFact
        return super().find_class(module, name)


def _normalize_symbol_call_facts(state: Any) -> Any:
    """Replace legacy call objects with the current primitive tuple contract."""

    if state is None or not hasattr(state, "module_usages"):
        return state
    from contextor.core.domain.usage_facts import ModuleUsageFacts

    module_usages = getattr(state, "module_usages", None)
    if not isinstance(module_usages, dict):
        return state
    normalized_usages = dict(module_usages)
    for module_name, facts in module_usages.items():
        if not isinstance(facts, ModuleUsageFacts):
            continue
        normalized_calls = []
        for item in getattr(facts, "symbol_calls", ()):
            if isinstance(item, _LegacySymbolCallFact):
                values = vars(item)
                try:
                    normalized_calls.append(
                        (
                            str(values["caller"]),
                            str(values["callee"]),
                            int(values["line"]),
                            str(values.get("call_kind", "direct")),
                        )
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise pickle.UnpicklingError(
                        "Invalid legacy SymbolCallFact state."
                    ) from exc
            elif isinstance(item, (tuple, list)) and len(item) in {3, 4}:
                try:
                    normalized_calls.append(
                        (
                            str(item[0]),
                            str(item[1]),
                            int(item[2]),
                            str(item[3]) if len(item) == 4 else "direct",
                        )
                    )
                except (TypeError, ValueError) as exc:
                    raise pickle.UnpicklingError(
                        "Invalid primitive symbol call fact."
                    ) from exc
            else:
                raise pickle.UnpicklingError("Unknown symbol call fact shape.")
        normalized_usages[module_name] = replace(
            facts,
            symbol_calls=tuple(sorted(set(normalized_calls))),
            symbol_calls_materialized=bool(
                vars(facts).get("symbol_calls_materialized", False)
            ),
        )
    state.module_usages = normalized_usages
    return state


@dataclass(frozen=True)
class LiveStateMetadata:
    schema_version: str = LIVE_STATE_SCHEMA_VERSION
    state_id: str = ""
    revision: int = 0
    writer: str = "unknown"
    repo_id: str = ""
    root_path: str = ""
    state_file: str = ""
    file_state_file: str = ""


class SnapshotRevisionConflict(ValueError):
    def __init__(self, current_revision: int | None, requested_revision: int):
        self.current_revision = current_revision
        self.requested_revision = requested_revision
        super().__init__(
            "Snapshot revision conflict: "
            f"current={current_revision}, requested={requested_revision}."
        )


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
            state_file=str(payload.get("state_file", "")),
            file_state_file=str(payload.get("file_state_file", "")),
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
    exact_revision: int | None = None,
    file_state_payload: dict[str, Any] | None = None,
) -> LiveStateMetadata:
    """Atomically publish a complete snapshot and monotonically increasing revision."""

    state_file, meta_file, lock_file = _paths(cache_dir)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = _acquire_lock(lock_file)
    token = uuid.uuid4().hex
    state_tmp = state_file.with_name(f".{state_file.name}.{token}.tmp")
    meta_tmp = meta_file.with_name(f".{meta_file.name}.{token}.tmp")
    generation_state = state_tmp
    generation_file_state: Path | None = None
    committed = False
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
        if exact_revision is not None:
            if isinstance(exact_revision, bool) or not isinstance(exact_revision, int) or exact_revision < 0:
                raise ValueError("exact_revision must be a non-negative integer.")
            current_revision = current.revision if current is not None else None
            if current_revision is None and exact_revision != 1:
                raise SnapshotRevisionConflict(None, exact_revision)
            if current_revision is not None and exact_revision != current_revision + 1:
                raise SnapshotRevisionConflict(current_revision, exact_revision)
            next_revision = exact_revision
            generation_state = state_file.parent / f"engine_state.r{exact_revision}.{token}.pkl"
            generation_file_state = state_file.parent / f"file_state.r{exact_revision}.{token}.json"
        else:
            next_revision = max(current.revision if current else 0, revision_floor) + 1
        metadata = LiveStateMetadata(
            state_id=state_id,
            revision=next_revision,
            writer=writer,
            repo_id=repo_id,
            root_path=normalized_root,
            state_file=generation_state.name if exact_revision is not None else "",
            file_state_file=generation_file_state.name if generation_file_state is not None else "",
        )
        if exact_revision is not None and isinstance(state, dict):
            state["revision"] = metadata.revision
            state["state_id"] = metadata.state_id
        elif state is not None and hasattr(state, "__dict__"):
            try:
                setattr(state, "state_id", metadata.state_id)
                setattr(state, "revision", metadata.revision)
            except AttributeError:
                pass
        with generation_state.open("wb") as stream:
            pickle.dump({"metadata": asdict(metadata), "state": state}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        if generation_file_state is not None:
            if not isinstance(file_state_payload, dict) or not isinstance(file_state_payload.get("_meta"), dict):
                raise ValueError("file_state_payload must contain a _meta mapping.")
            payload_meta = file_state_payload["_meta"]
            if payload_meta.get("state_id", "") != state_id:
                raise ValueError("FileState payload state_id does not match snapshot state_id.")
            if payload_meta.get("revision") != exact_revision:
                raise ValueError("FileState payload revision does not match exact_revision.")
            with generation_file_state.open("w", encoding="utf-8") as stream:
                json.dump(file_state_payload, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
        with meta_tmp.open("w", encoding="utf-8") as stream:
            json.dump(asdict(metadata), stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        if exact_revision is None:
            os.replace(generation_state, state_file)
        os.replace(meta_tmp, meta_file)
        committed = True
        return metadata
    finally:
        for temporary in (state_tmp, meta_tmp):
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        if not committed and exact_revision is not None:
            for temporary in (generation_state, generation_file_state):
                if temporary is not None:
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
    if metadata.state_file:
        state_file = state_file.parent / metadata.state_file
    try:
        with state_file.open("rb") as stream:
            payload = _SnapshotUnpickler(stream).load()
        if isinstance(payload, dict) and set(payload) == {"metadata", "state"}:
            embedded = payload["metadata"]
            embedded_metadata = LiveStateMetadata(
                schema_version=str(embedded.get("schema_version", "1.0")),
                state_id=str(embedded.get("state_id", "")),
                revision=int(embedded.get("revision", 0)),
                writer=str(embedded.get("writer", "unknown")),
                repo_id=str(embedded.get("repo_id", "")),
                root_path=str(embedded.get("root_path", "")),
                state_file=str(embedded.get("state_file", "")),
                file_state_file=str(embedded.get("file_state_file", "")),
            )
            if embedded_metadata.revision != metadata.revision:
                return None
            state_obj = _normalize_symbol_call_facts(payload["state"])
            state_revision = (
                state_obj.get("revision") if isinstance(state_obj, dict)
                else getattr(state_obj, "revision", None)
            )
            state_id_value = (
                state_obj.get("state_id") if isinstance(state_obj, dict)
                else getattr(state_obj, "state_id", None)
            )
            if state_obj is not None and state_revision is not None and int(state_revision) != metadata.revision:
                return None
            if state_obj is not None and state_id_value is not None and str(state_id_value) != metadata.state_id:
                return None
            if state_obj is not None and hasattr(state_obj, "__dict__"):
                try:
                    setattr(state_obj, "state_id", embedded_metadata.state_id)
                    setattr(state_obj, "revision", embedded_metadata.revision)
                    setattr(state_obj, "provenance", "snapshot")
                except AttributeError:
                    pass
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
                if not hasattr(state_obj, "dependency_matrix"):
                    try:
                        setattr(state_obj, "dependency_matrix", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "dependency_matrix_state"):
                    try:
                        setattr(state_obj, "dependency_matrix_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "shared_usage_clusters"):
                    try:
                        setattr(state_obj, "shared_usage_clusters", [])
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "shared_usage_clusters_state"):
                    try:
                        setattr(state_obj, "shared_usage_clusters_state", "deferred")
                    except AttributeError:
                        pass
            return state_obj, metadata
        payload = _normalize_symbol_call_facts(payload)
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
            if not hasattr(payload, "dependency_matrix"):
                try:
                    setattr(payload, "dependency_matrix", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "dependency_matrix_state"):
                try:
                    setattr(payload, "dependency_matrix_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "shared_usage_clusters"):
                try:
                    setattr(payload, "shared_usage_clusters", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "shared_usage_clusters_state"):
                try:
                    setattr(payload, "shared_usage_clusters_state", "deferred")
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

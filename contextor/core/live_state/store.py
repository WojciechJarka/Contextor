"""Atomic, revisioned snapshot store shared by desktop and MCP processes."""

from __future__ import annotations

import json
import os
import pickle
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.1"


@dataclass(frozen=True)
class LiveStateMetadata:
    schema_version: str = SCHEMA_VERSION
    state_id: str = ""
    revision: int = 0
    writer: str = "unknown"


def _paths(cache_dir: str | Path) -> tuple[Path, Path, Path]:
    root = Path(cache_dir)
    return root / "engine_state.pkl", root / "engine_state.meta.json", root / "engine_state.lock"


def read_metadata(cache_dir: str | Path) -> LiveStateMetadata | None:
    """Read snapshot metadata without loading the potentially large pickle."""

    _, meta_file, _ = _paths(cache_dir)
    try:
        payload = json.loads(meta_file.read_text(encoding="utf-8"))
        if payload.get("schema_version") not in {"1.0", SCHEMA_VERSION}:
            return None
        return LiveStateMetadata(
            state_id=str(payload.get("state_id", "")),
            revision=int(payload.get("revision", 0)),
            writer=str(payload.get("writer", "legacy")),
        )
    except (OSError, ValueError, TypeError):
        return None


def _acquire_lock(lock_file: Path, timeout: float = 5.0) -> int:
    deadline = time.monotonic() + timeout
    while True:
        try:
            return os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
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
        metadata = LiveStateMetadata(
            state_id=state_id,
            revision=(current.revision if current else 0) + 1,
            writer=writer,
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
) -> tuple[Any, LiveStateMetadata] | None:
    """Load one complete published snapshot, rejecting incompatible identities."""

    state_file, _, _ = _paths(cache_dir)
    metadata = read_metadata(cache_dir)
    if metadata is None or (expected_state_id and metadata.state_id != expected_state_id):
        return None
    try:
        with state_file.open("rb") as stream:
            payload = pickle.load(stream)
        if isinstance(payload, dict) and set(payload) == {"metadata", "state"}:
            embedded = payload["metadata"]
            embedded_metadata = LiveStateMetadata(
                state_id=str(embedded.get("state_id", "")),
                revision=int(embedded.get("revision", 0)),
                writer=str(embedded.get("writer", "unknown")),
            )
            if expected_state_id and embedded_metadata.state_id != expected_state_id:
                return None
            return payload["state"], embedded_metadata
        return payload, metadata
    except (OSError, pickle.PickleError, EOFError):
        return None

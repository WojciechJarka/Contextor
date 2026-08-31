"""Shared hydration of an incremental engine from canonical LIVE or disk."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HydratedRepositoryEngine:
    engine: Any
    client: Any | None
    revision: int
    source: str


@dataclass(frozen=True)
class AuthoritativeRepositoryState:
    """Validated current canonical state without incremental-engine materialization."""

    state: Any
    client: Any | None
    revision: int
    source: str
    cache_dir: Path


def resolve_authoritative_repository_state(
    repo_path: str | Path,
) -> AuthoritativeRepositoryState | None:
    """Resolve the same LIVE-first, validated canonical state used by hydration."""

    from contextor.core.analysis.state_manager import load_engine_state
    from contextor.core.live_state.runtime import connect
    from contextor.core.live_state.store import migrate_legacy_snapshot, read_metadata
    from contextor.core.repository_identity import read_repository_identity

    root = Path(repo_path).resolve()
    identity = read_repository_identity(root)
    if identity is None:
        return None

    cache_dir = migrate_legacy_snapshot(root)
    client = connect(root)
    state = None
    revision = 0
    source = ""
    if client is not None:
        try:
            ping = client.ping()
            snapshot = client.snapshot()
            state = snapshot.get("state")
            revision = int(snapshot.get("revision", ping.get("revision", 0)))
            source = "live_service"
        except (TimeoutError, OSError, EOFError, ConnectionError, RuntimeError):
            client = None

    if state is None:
        metadata = read_metadata(cache_dir)
        state = load_engine_state(
            str(cache_dir),
            metadata.state_id if metadata else "",
            expected_repo_id=identity.repo_id,
            expected_root_path=identity.root_path,
        )
        source = "snapshot" if state is not None else ""

    if (
        state is None
        or not getattr(state, "modules", None)
        or getattr(state, "dependency_graph", None) is None
    ):
        return None

    return AuthoritativeRepositoryState(
        state=state,
        client=client,
        revision=revision,
        source=source,
        cache_dir=cache_dir,
    )


def hydrate_repository_engine(
    repo_path: str | Path,
) -> HydratedRepositoryEngine | None:
    """Load a complete engine without triggering a repository analysis."""

    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
    from contextor.core.analysis.state_manager import FileStateManager
    from contextor.core.reporting_engine.persistent_registry import (
        PersistentIdentityRegistry,
    )

    root = Path(repo_path).resolve()
    resolved = resolve_authoritative_repository_state(root)
    if resolved is None:
        return None

    engine = IncrementalAnalysisEngine(
        resolved.state,
        PersistentIdentityRegistry(str(root)),
        FileStateManager(str(resolved.cache_dir)),
        str(root),
    )
    return HydratedRepositoryEngine(
        engine=engine,
        client=resolved.client,
        revision=resolved.revision,
        source=resolved.source,
    )


__all__ = [
    "AuthoritativeRepositoryState",
    "HydratedRepositoryEngine",
    "hydrate_repository_engine",
    "resolve_authoritative_repository_state",
]

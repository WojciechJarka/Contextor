"""Shared persistence primitives for canonical LIVE state."""

from .store import (
    LiveStateMetadata,
    SnapshotRevisionConflict,
    load_snapshot,
    migrate_legacy_snapshot,
    read_metadata,
    save_snapshot,
)
from .ipc import CanonicalLiveServer, CanonicalPersistenceConflict, LiveEndpoint, LiveStateClient
from .runtime import (
    AuthorityLivenessVerifier,
    EndpointSchemaError,
    SecondDesktopActive,
    connect,
    connect_or_start,
)
from .watcher import DesktopLiveEventFeed, DesktopLiveWatcher
from .hydration import (
    AuthoritativeRepositoryState,
    HydratedRepositoryEngine,
    hydrate_repository_engine,
    resolve_authoritative_repository_state,
)

__all__ = [
    "CanonicalLiveServer",
    "CanonicalPersistenceConflict",
    "LiveEndpoint",
    "LiveStateClient",
    "LiveStateMetadata",
    "SnapshotRevisionConflict",
    "DesktopLiveWatcher",
    "DesktopLiveEventFeed",
    "HydratedRepositoryEngine",
    "AuthoritativeRepositoryState",
    "connect",
    "connect_or_start",
    "AuthorityLivenessVerifier",
    "EndpointSchemaError",
    "SecondDesktopActive",
    "hydrate_repository_engine",
    "resolve_authoritative_repository_state",
    "load_snapshot",
    "migrate_legacy_snapshot",
    "read_metadata",
    "save_snapshot",
]

"""Shared persistence primitives for canonical LIVE state."""

from .store import (
    LiveStateMetadata,
    load_snapshot,
    migrate_legacy_snapshot,
    read_metadata,
    save_snapshot,
)
from .ipc import CanonicalLiveServer, LiveEndpoint, LiveStateClient
from .runtime import connect, connect_or_start
from .watcher import DesktopLiveEventFeed, DesktopLiveWatcher
from .hydration import HydratedRepositoryEngine, hydrate_repository_engine

__all__ = [
    "CanonicalLiveServer",
    "LiveEndpoint",
    "LiveStateClient",
    "LiveStateMetadata",
    "DesktopLiveWatcher",
    "DesktopLiveEventFeed",
    "HydratedRepositoryEngine",
    "connect",
    "connect_or_start",
    "hydrate_repository_engine",
    "load_snapshot",
    "migrate_legacy_snapshot",
    "read_metadata",
    "save_snapshot",
]

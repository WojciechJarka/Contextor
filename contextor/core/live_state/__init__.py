"""Shared persistence primitives for canonical LIVE state."""

from .store import LiveStateMetadata, load_snapshot, read_metadata, save_snapshot
from .ipc import CanonicalLiveServer, LiveEndpoint, LiveStateClient
from .runtime import connect, connect_or_start
from .watcher import DesktopLiveEventFeed, DesktopLiveWatcher

__all__ = [
    "CanonicalLiveServer",
    "LiveEndpoint",
    "LiveStateClient",
    "LiveStateMetadata",
    "DesktopLiveWatcher",
    "DesktopLiveEventFeed",
    "connect",
    "connect_or_start",
    "load_snapshot",
    "read_metadata",
    "save_snapshot",
]

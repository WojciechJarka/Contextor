"""Closed, ordered registry of safe initial atomic operations."""

from dataclasses import dataclass
from typing import Callable
from pathlib import Path

from contextor.core.profiling.scopes import reports, live_ipc, snapshot_metadata

SCHEMA = "contextor-atomic-profile/v1"


@dataclass(frozen=True)
class ScopeSpec:
    name: str
    description: str
    presets: tuple[str, ...]
    safety: str
    execution_kind: str
    run_scope: Callable


_SCOPES = (
    ScopeSpec("reports.summary", "Read and JSON-decode the existing summary report.",
              reports.PRESETS, "READ_WITH_OS_CACHE_EFFECTS", "INDEPENDENT_OPERATION", reports.run_scope),
    ScopeSpec("live.ping", "Connect to the existing authoritative LIVE service and perform one read-only ping.",
              live_ipc.PRESETS, "LIVE_READ_WITH_TRANSPORT_TELEMETRY", "INDEPENDENT_OPERATION", live_ipc.run_scope),
    ScopeSpec("snapshot.metadata", "Read and validate committed snapshot metadata.",
              snapshot_metadata.PRESETS, "READ_WITH_OS_CACHE_EFFECTS", "INDEPENDENT_OPERATION",
              snapshot_metadata.run_scope),
)


def get_scope(name: str) -> ScopeSpec | None:
    return next((scope for scope in _SCOPES if scope.name == name), None)


def list_scopes() -> tuple[ScopeSpec, ...]:
    return _SCOPES


def validate_scope_presets(scope: str, presets: list[str]) -> tuple[str, ...]:
    spec = get_scope(scope)
    if spec is None:
        raise ValueError("Unknown scope.")
    if not isinstance(presets, list) or not presets:
        raise ValueError("Presets must be a nonempty list.")
    if any(not isinstance(item, str) or item not in spec.presets for item in presets):
        raise ValueError("Unknown or wrong-scope preset.")
    if len(set(presets)) != len(presets):
        raise ValueError("Duplicate preset.")
    return tuple(item for item in spec.presets if item in presets)


def build_catalog() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "status": "ok",
        "mode": "catalog",
        "scopes": [
            {"name": item.name, "description": item.description, "presets": list(item.presets),
             "safety": item.safety, "execution_kind": item.execution_kind}
            for item in _SCOPES
        ],
    }

"""Bounded replay of source bytes for individual cyclic SCC closures.

The source bytes are captured during a selective second read.
They are NOT the original indexer-worker byte objects.

Equality with indexed hashes and import facts is checked.
No atomic repository snapshot, LIVE authority, or SAFE verdict
is established.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from contextor.core.source import (
    SourceError,
    SourceSnapshot,
    parse_source_snapshot,
)
from contextor.core.symbol_engine.indexer import (
    RepositoryIndex,
    read_imports,
)

from .scc import analyze_import_cycle_topology


REPLAY_AUTHORITY = (
    "SELECTIVE_SECOND_READ_NOT_ORIGINAL_INDEXER_CAPTURE"
    "_NOT_ATOMIC_NOT_LIVE_CERTIFIED"
)

DEFAULT_MAX_SOURCE_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_CLOSURE_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class SCCSourceReplay:
    members: tuple[str, ...]
    reachable_modules: tuple[str, ...]
    status: str
    reason: str | None
    source_snapshots: Mapping[str, SourceSnapshot]
    retained_raw_bytes: int
    authority: str = REPLAY_AUTHORITY


def _read_bounded_bytes(
    path: Path,
    maximum: int,
) -> bytes:
    """Never read more than the requested byte budget plus one."""
    with path.open("rb") as stream:
        return stream.read(maximum + 1)


def _is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def _capture_closure(
    root: Path,
    index: RepositoryIndex,
    members: tuple[str, ...],
    closure: tuple[str, ...],
    *,
    max_source_bytes: int,
    max_closure_bytes: int,
) -> SCCSourceReplay:
    snapshots: dict[str, SourceSnapshot] = {}
    total = 0

    def unavailable(reason: str) -> SCCSourceReplay:
        # Never return a partially retained closure.
        return SCCSourceReplay(
            members=members,
            reachable_modules=closure,
            status="UNAVAILABLE",
            reason=reason,
            source_snapshots={},
            retained_raw_bytes=0,
        )

    for module_id in closure:
        indexed = index.modules.get(module_id)
        if indexed is None:
            return unavailable(
                "MODULE_NOT_INDEXED:" + module_id
            )

        expected_hash = (
            index.source_fingerprints_by_module.get(module_id)
        )
        if not _is_sha256(expected_hash):
            return unavailable(
                "INDEX_FINGERPRINT_UNAVAILABLE:" + module_id
            )

        try:
            relative_path = Path(indexed.path)
            source_path = (
                root / relative_path
            ).resolve(strict=True)
            indexed_absolute = Path(
                indexed.absolute_path
            ).resolve(strict=True)
        except (OSError, ValueError, TypeError):
            return unavailable(
                "SOURCE_PATH_UNAVAILABLE:" + module_id
            )

        if (
            not source_path.is_relative_to(root)
            or source_path != indexed_absolute
            or not source_path.is_file()
        ):
            return unavailable(
                "SOURCE_PATH_IDENTITY_MISMATCH:" + module_id
            )

        remaining = max_closure_bytes - total
        allowed = min(max_source_bytes, remaining)
        if allowed < 1:
            return unavailable(
                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module_id
            )

        try:
            raw = _read_bounded_bytes(source_path, allowed)
        except OSError:
            return unavailable(
                "SOURCE_READ_FAILED:" + module_id
            )

        if len(raw) > allowed:
            return unavailable(
                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module_id
            )

        fingerprint = hashlib.sha256(raw).hexdigest()
        if fingerprint != expected_hash:
            return unavailable(
                "SOURCE_INDEX_BYTES_MISMATCH:" + module_id
            )

        snapshot = SourceSnapshot(
            raw=raw,
            source_fingerprint=fingerprint,
        )

        try:
            parsed = parse_source_snapshot(
                snapshot,
                source_path,
            )
        except SourceError:
            return unavailable(
                "SOURCE_REPLAY_PARSE_FAILED:" + module_id
            )

        imports, error = read_imports(
            source_path,
            tree=parsed.tree,
        )

        if (
            error is not None
            or imports is None
            or imports != indexed.imports
        ):
            return unavailable(
                "SOURCE_INDEX_IMPORTS_MISMATCH:" + module_id
            )

        snapshots[module_id] = snapshot
        total += len(raw)

    return SCCSourceReplay(
        members=members,
        reachable_modules=closure,
        status="BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC",
        reason=None,
        source_snapshots=snapshots,
        retained_raw_bytes=total,
    )


def iter_selective_scc_source_replays(
    repository_root: str | Path,
    hard_edges: Mapping[str, object],
    index: RepositoryIndex,
    *,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
    max_closure_bytes: int = DEFAULT_MAX_CLOSURE_BYTES,
) -> Iterator[SCCSourceReplay]:
    """Yield one bounded SCC closure at a time.

    Consumers must process/release each result before requesting
    the next one if they want bounded retained raw-byte memory.

    Do not collect the iterator into a list for large repositories.
    """
    if not isinstance(index, RepositoryIndex):
        raise TypeError("index must be RepositoryIndex")

    if (
        type(max_source_bytes) is not int
        or not 1 <= max_source_bytes <= 64 * 1024 * 1024
    ):
        raise ValueError("invalid max_source_bytes")

    if (
        type(max_closure_bytes) is not int
        or not 1 <= max_closure_bytes <= 256 * 1024 * 1024
    ):
        raise ValueError("invalid max_closure_bytes")

    root = Path(repository_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("repository root is not a directory")

    topology = analyze_import_cycle_topology(hard_edges)

    adjacency = {
        module_id: tuple(sorted(set(targets)))
        for module_id, targets in hard_edges.items()
    }

    for targets in tuple(adjacency.values()):
        for target in targets:
            adjacency.setdefault(target, ())

    for component in topology.cyclic_components:
        visited = set(component.members)
        pending = list(component.members)

        while pending:
            current = pending.pop()
            for target in adjacency[current]:
                if target not in visited:
                    visited.add(target)
                    pending.append(target)

        closure = tuple(sorted(visited))

        yield _capture_closure(
            root,
            index,
            component.members,
            closure,
            max_source_bytes=max_source_bytes,
            max_closure_bytes=max_closure_bytes,
        )

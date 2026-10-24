"""Selective SCC capture using the indexer worker's opt-in byte channel.

Each selected worker task performs a SECOND source read.
Its bytes originate from that worker task, not the original FULL index.

Hash and import equality are checked against the supplied index.
No canonical publication, runtime safety or atomicity is certified.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Mapping
from concurrent.futures import Executor
from dataclasses import dataclass
from pathlib import Path

from contextor.core.source import SourceSnapshot
from contextor.core.symbol_engine.indexer import (
    RepositoryIndex,
    _process_single_file,
)

from .scc import analyze_import_cycle_topology


WORKER_CAPTURE_AUTHORITY = (
    "SELECTIVE_INDEXER_WORKER_SECOND_PASS"
    "_NOT_ORIGINAL_FULL_INDEX"
    "_NOT_ATOMIC_NOT_LIVE_CERTIFIED"
)

DEFAULT_MAX_SOURCE_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_CLOSURE_BYTES = 32 * 1024 * 1024

_SUCCESS = (
    "WORKER_SECOND_PASS_BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
)

_ACCEPTED_AST_MODES = frozenset({
    "PARSED_FROM_WORKER_READ",
    "CACHE_SHA256_EQUIVALENT",
})


@dataclass(frozen=True)
class SCCWorkerCapture:
    members: tuple[str, ...]
    reachable_modules: tuple[str, ...]
    status: str
    reason: str | None
    source_snapshots: Mapping[str, SourceSnapshot]
    ast_modes: tuple[tuple[str, str], ...]
    retained_raw_bytes: int
    authority: str = WORKER_CAPTURE_AUTHORITY


def _valid_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(
            character in "0123456789abcdef"
            for character in value
        )
    )


def _capture_closure(
    root: Path,
    index: RepositoryIndex,
    members: tuple[str, ...],
    closure: tuple[str, ...],
    *,
    max_source_bytes: int,
    max_closure_bytes: int,
    executor: Executor | None,
) -> SCCWorkerCapture:
    snapshots: dict[str, SourceSnapshot] = {}
    modes: dict[str, str] = {}
    total = 0

    def unavailable(reason: str) -> SCCWorkerCapture:
        # Never expose a partially successful SCC closure.
        return SCCWorkerCapture(
            members=members,
            reachable_modules=closure,
            status="UNAVAILABLE",
            reason=reason,
            source_snapshots={},
            ast_modes=(),
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
        if not _valid_sha256(expected_hash):
            return unavailable(
                "INDEX_FINGERPRINT_UNAVAILABLE:" + module_id
            )

        try:
            relative = Path(indexed.path)
            if relative.is_absolute():
                return unavailable(
                    "SOURCE_PATH_IDENTITY_MISMATCH:" + module_id
                )

            source_path = (
                root / relative
            ).resolve(strict=True)
            indexed_absolute = Path(
                indexed.absolute_path
            ).resolve(strict=True)
        except (OSError, RuntimeError, ValueError, TypeError):
            return unavailable(
                "SOURCE_PATH_UNAVAILABLE:" + module_id
            )

        if (
            not source_path.is_relative_to(root)
            or source_path != indexed_absolute
            or not source_path.is_file()
            or source_path.suffix != ".py"
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

        # Preflight avoids scheduling obviously oversized files.
        # The worker still performs the authoritative size check
        # on its own captured raw bytes.
        try:
            size = source_path.stat().st_size
        except OSError:
            return unavailable(
                "SOURCE_STAT_FAILED:" + module_id
            )

        if size > allowed:
            return unavailable(
                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module_id
            )

        try:
            if executor is None:
                result = _process_single_file(
                    str(source_path),
                    str(root),
                    source_capture_max_bytes=allowed,
                )
            else:
                future = executor.submit(
                    _process_single_file,
                    str(source_path),
                    str(root),
                    None,
                    None,
                    None,
                    allowed,
                )
                result = future.result()
        except Exception:
            return unavailable(
                "WORKER_EXECUTION_FAILED:" + module_id
            )

        if not isinstance(result, dict):
            return unavailable(
                "WORKER_RESULT_INVALID:" + module_id
            )

        if (
            result.get("module_id") != module_id
            or result.get("path") != indexed.path
            or result.get("absolute_path")
            != str(source_path)
        ):
            return unavailable(
                "WORKER_IDENTITY_MISMATCH:" + module_id
            )

        status = result.get("source_capture_status")

        if status == "BYTE_LIMIT":
            return unavailable(
                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module_id
            )

        if (
            result.get("error") is not None
            or status != "CAPTURED"
        ):
            return unavailable(
                "WORKER_CAPTURE_UNAVAILABLE:" + module_id
            )

        if result.get("source_capture_origin") != (
            "INDEXER_WORKER_READ"
        ):
            return unavailable(
                "WORKER_CAPTURE_ORIGIN_INVALID:" + module_id
            )

        mode = result.get("source_capture_ast_mode")
        if mode not in _ACCEPTED_AST_MODES:
            return unavailable(
                "WORKER_AST_MODE_INVALID:" + module_id
            )

        raw = result.get("source_capture_bytes")
        if type(raw) is not bytes:
            return unavailable(
                "WORKER_SOURCE_BYTES_INVALID:" + module_id
            )

        if len(raw) > allowed:
            return unavailable(
                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module_id
            )

        actual_hash = hashlib.sha256(raw).hexdigest()
        if (
            actual_hash != expected_hash
            or result.get("source_fingerprint")
            != actual_hash
        ):
            return unavailable(
                "WORKER_INDEX_BYTES_MISMATCH:" + module_id
            )

        if result.get("imports") != indexed.imports:
            return unavailable(
                "WORKER_INDEX_IMPORTS_MISMATCH:" + module_id
            )

        snapshots[module_id] = SourceSnapshot(
            raw=raw,
            source_fingerprint=actual_hash,
        )
        modes[module_id] = mode
        total += len(raw)

        # Discard the full worker result before processing
        # another source file in this closure.
        del result

    return SCCWorkerCapture(
        members=members,
        reachable_modules=closure,
        status=_SUCCESS,
        reason=None,
        source_snapshots=snapshots,
        ast_modes=tuple(sorted(modes.items())),
        retained_raw_bytes=total,
    )


def iter_selective_scc_worker_captures(
    repository_root: str | Path,
    hard_edges: Mapping[str, object],
    index: RepositoryIndex,
    *,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
    max_closure_bytes: int = DEFAULT_MAX_CLOSURE_BYTES,
    executor: Executor | None = None,
) -> Iterator[SCCWorkerCapture]:
    """Replay only reachable cyclic SCC closures.

    An optional executor is supplied and owned by the caller.
    This function neither creates nor terminates process pools.

    Consume and release each yielded result before requesting
    the next one to keep retained raw bytes SCC-scoped.
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
        raise ValueError(
            "repository root is not a directory"
        )

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
            executor=executor,
        )

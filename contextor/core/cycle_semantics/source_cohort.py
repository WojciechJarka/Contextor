"""Bounded source cohort for structural Python cycle evidence.

The caller supplies graph and module paths from an
already acquired canonical snapshot.

File reads are individually fingerprinted and checked
for drift. This is not an atomic graph/source transaction.

No LIVE connections, imports of analyzed modules,
graph mutations or repository analyses occur here.
"""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from contextor.core.source import (
    ParsedSourceInput,
    SourceError,
    parse_source_snapshot,
    read_source_snapshot,
)

from .scc import analyze_import_cycle_topology


@dataclass(frozen=True)
class CycleSourceIssue:
    module_id: str
    reason: str


@dataclass(frozen=True)
class CycleSourceCohort:
    hard_edges: dict[str, tuple[str, ...]]
    indexed_module_ids: tuple[str, ...]
    parsed_sources: dict[str, ParsedSourceInput]
    fingerprints: tuple[tuple[str, str], ...]
    issues: tuple[CycleSourceIssue, ...]
    cyclic_module_count: int
    canonical_hash_matches: int
    canonical_hash_missing: int
    coverage_status: str
    source_snapshot_binding: str = (
        "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    )
    runtime_execution_status: str = (
        "UNKNOWN_NOT_EVALUATED"
    )


def _integer_limit(
    value: int,
    name: str,
    maximum: int,
) -> int:
    if (
        type(value) is not int
        or not 1 <= value <= maximum
    ):
        raise ValueError(
            f"{name} must be in range 1..{maximum}"
        )

    return value


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(
            character in "0123456789abcdef"
            for character in value
        )
    )


def _source_path(
    root: Path,
    raw_path: object,
) -> Path | None:
    if not isinstance(raw_path, (str, Path)):
        return None

    if not str(raw_path):
        return None

    path = Path(raw_path)

    try:
        resolved = (
            path.resolve()
            if path.is_absolute()
            else (root / path).resolve()
        )

        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None

    if resolved.suffix != ".py":
        return None

    return resolved


def build_cycle_source_cohort(
    repository_root: str | Path,
    hard_edges: Mapping[
        str,
        set[str] | frozenset[str] | list[str] | tuple[str, ...],
    ],
    module_paths: Mapping[str, str | Path],
    *,
    expected_fingerprints: Mapping[str, str] | None = None,
    max_cyclic_modules: int = 512,
    max_source_bytes: int = 2 * 1024 * 1024,
    max_total_source_bytes: int = 32 * 1024 * 1024,
) -> CycleSourceCohort:
    """Prepare source-backed cycle evidence without LIVE I/O.

    All inputs must originate from a caller-controlled
    coherent canonical graph/module inventory.

    A stable filesystem read does not prove that the
    canonical graph and those bytes share one transaction.
    """

    max_cyclic_modules = _integer_limit(
        max_cyclic_modules,
        "max_cyclic_modules",
        4096,
    )

    max_source_bytes = _integer_limit(
        max_source_bytes,
        "max_source_bytes",
        64 * 1024 * 1024,
    )

    max_total_source_bytes = _integer_limit(
        max_total_source_bytes,
        "max_total_source_bytes",
        256 * 1024 * 1024,
    )

    if not isinstance(hard_edges, Mapping):
        raise TypeError("hard_edges must be a mapping")

    if not isinstance(module_paths, Mapping):
        raise TypeError("module_paths must be a mapping")

    if (
        expected_fingerprints is not None
        and not isinstance(expected_fingerprints, Mapping)
    ):
        raise TypeError(
            "expected_fingerprints must be a mapping or None"
        )

    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise ValueError(
            "repository_root must be an existing directory"
        )

    graph: dict[str, tuple[str, ...]] = {}

    for source, targets in hard_edges.items():
        if not isinstance(source, str) or not source:
            raise ValueError("invalid source module ID")

        if not isinstance(
            targets,
            (set, frozenset, list, tuple),
        ):
            raise TypeError(
                "graph targets must be explicit collections"
            )

        if any(
            not isinstance(target, str) or not target
            for target in targets
        ):
            raise ValueError("invalid target module ID")

        graph[source] = tuple(sorted(set(targets)))

    graph = {
        key: graph[key]
        for key in sorted(graph)
    }

    topology = analyze_import_cycle_topology(graph)

    cyclic_members = tuple(sorted({
        member
        for component in topology.cyclic_components
        for member in component.members
    }))

    if len(cyclic_members) > max_cyclic_modules:
        raise ValueError(
            "cyclic source cohort exceeds module limit"
        )

    indexed_ids = tuple(sorted(module_paths))

    if any(
        not isinstance(name, str) or not name
        for name in indexed_ids
    ):
        raise ValueError("invalid indexed module identity")

    expected = (
        {}
        if expected_fingerprints is None
        else dict(expected_fingerprints)
    )

    parsed: dict[str, ParsedSourceInput] = {}
    fingerprints: dict[str, str] = {}
    resolved_paths: dict[str, Path] = {}
    issues: list[CycleSourceIssue] = []

    total_bytes = 0

    for module in cyclic_members:
        path = _source_path(
            root,
            module_paths.get(module),
        )

        if path is None:
            issues.append(CycleSourceIssue(
                module,
                "MISSING_OR_INVALID_CANONICAL_PATH",
            ))
            continue

        try:
            size = path.stat().st_size
        except OSError:
            issues.append(CycleSourceIssue(
                module,
                "SOURCE_UNREADABLE",
            ))
            continue

        if size > max_source_bytes:
            issues.append(CycleSourceIssue(
                module,
                "SOURCE_FILE_LIMIT",
            ))
            continue

        if total_bytes + size > max_total_source_bytes:
            issues.append(CycleSourceIssue(
                module,
                "SOURCE_COHORT_BYTE_LIMIT",
            ))
            continue

        try:
            snapshot = read_source_snapshot(path)
        except SourceError:
            issues.append(CycleSourceIssue(
                module,
                "SOURCE_UNREADABLE",
            ))
            continue

        actual_size = len(snapshot.raw)

        if actual_size > max_source_bytes:
            issues.append(CycleSourceIssue(
                module,
                "SOURCE_FILE_LIMIT",
            ))
            continue

        if (
            total_bytes + actual_size
            > max_total_source_bytes
        ):
            issues.append(CycleSourceIssue(
                module,
                "SOURCE_COHORT_BYTE_LIMIT",
            ))
            continue

        total_bytes += actual_size

        canonical_hash = expected.get(module)

        if canonical_hash is not None:
            if not _valid_sha256(canonical_hash):
                issues.append(CycleSourceIssue(
                    module,
                    "INVALID_CANONICAL_FINGERPRINT",
                ))
                continue

            if (
                snapshot.source_fingerprint
                != canonical_hash
            ):
                issues.append(CycleSourceIssue(
                    module,
                    "CANONICAL_FINGERPRINT_MISMATCH",
                ))
                continue

        try:
            source = parse_source_snapshot(
                snapshot,
                path,
            )

            if not isinstance(source.tree, ast.Module):
                raise ValueError("not an ast.Module")

            compile(
                source.tree,
                str(path),
                "exec",
                dont_inherit=True,
            )

        except (
            SourceError,
            SyntaxError,
            TypeError,
            ValueError,
            RecursionError,
            OverflowError,
        ):
            issues.append(CycleSourceIssue(
                module,
                "SOURCE_NOT_COMPILABLE",
            ))
            continue

        parsed[module] = source
        fingerprints[module] = source.source_fingerprint
        resolved_paths[module] = path

    # Recheck every accepted file after the source window.
    # This is a drift check, NOT an atomicity guarantee.
    for module in tuple(sorted(parsed)):
        path = resolved_paths[module]

        try:
            current_hash = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
        except OSError:
            current_hash = None

        if current_hash != fingerprints[module]:
            parsed.pop(module)
            fingerprints.pop(module)
            resolved_paths.pop(module)

            issues.append(CycleSourceIssue(
                module,
                "SOURCE_CHANGED_DURING_READ",
            ))

    canonical_hash_matches = sum(
        expected.get(module) == fingerprint
        for module, fingerprint in fingerprints.items()
        if module in expected
    )

    canonical_hash_missing = sum(
        module not in expected
        for module in parsed
    )

    return CycleSourceCohort(
        hard_edges=graph,
        indexed_module_ids=indexed_ids,
        parsed_sources={
            module: parsed[module]
            for module in sorted(parsed)
        },
        fingerprints=tuple(sorted(
            fingerprints.items()
        )),
        issues=tuple(sorted(
            issues,
            key=lambda issue: (
                issue.module_id,
                issue.reason,
            ),
        )),
        cyclic_module_count=len(cyclic_members),
        canonical_hash_matches=canonical_hash_matches,
        canonical_hash_missing=canonical_hash_missing,
        coverage_status=(
            "FILESYSTEM_STABLE_NON_ATOMIC"
            if not issues
            else "PARTIAL_SOURCE_EVIDENCE"
        ),
    )

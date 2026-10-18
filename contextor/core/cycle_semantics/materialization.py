"""Index-bound, read-only Python cycle semantic materialization.

The caller supplies a hard graph, indexed module
paths and source hashes from one indexing result.

The materializer checks each cyclic source against
the supplied index fingerprint before accepting
lexical evidence.

This is NOT a repository-wide atomic snapshot
transaction or a LIVE publication certificate.

No state mutations, IPC, report writes or imports
of analyzed modules occur here.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .conditional_discovery import (
    discover_conditional_reexports,
)
from .contracts import (
    CycleSemanticsSnapshot,
    fingerprint_hard_edges,
)
from .edge_sites import analyze_cyclic_import_sites
from .source_cohort import build_cycle_source_cohort


def _validate_index_source_domain(
    module_paths: Mapping[str, str | Path],
    source_fingerprints_by_module: Mapping[str, str],
) -> None:
    """Require complete exact index-source identity coverage."""

    if not isinstance(module_paths, Mapping):
        raise TypeError(
            "module_paths must be a mapping"
        )

    if not isinstance(
        source_fingerprints_by_module,
        Mapping,
    ):
        raise TypeError(
            "source_fingerprints_by_module must be a mapping"
        )

    module_ids = set(module_paths)
    fingerprint_ids = set(
        source_fingerprints_by_module
    )

    if any(
        type(module_id) is not str or not module_id
        for module_id in module_ids | fingerprint_ids
    ):
        raise ValueError(
            "Invalid indexed module identity"
        )

    if module_ids != fingerprint_ids:
        raise ValueError(
            "Index source fingerprint domain mismatch"
        )

    for module_id, fingerprint in (
        source_fingerprints_by_module.items()
    ):
        if (
            type(fingerprint) is not str
            or len(fingerprint) != 64
            or any(
                character not in "0123456789abcdef"
                for character in fingerprint
            )
        ):
            raise ValueError(
                "Invalid indexed source fingerprint: "
                + module_id
            )


def materialize_cycle_semantics(
    repository_root: str | Path,
    hard_edges: Mapping[str, object],
    module_paths: Mapping[str, str | Path],
    source_fingerprints_by_module: Mapping[str, str],
    *,
    max_searches: int = 256,
) -> CycleSemanticsSnapshot:
    """Build immutable semantic evidence bound to index hashes.

    The caller is responsible for supplying graph,
    module paths and fingerprints associated with
    the intended analysis generation.

    Every accepted cyclic source must match its
    indexer fingerprint.

    A mismatch yields explicit partial evidence;
    it never becomes a successful lexical match.

    This function does not assign LIVE freshness
    or a canonical publication revision.
    """

    if (
        type(max_searches) is not int
        or not 1 <= max_searches <= 4096
    ):
        raise ValueError(
            "max_searches must be in range 1..4096"
        )

    _validate_index_source_domain(
        module_paths,
        source_fingerprints_by_module,
    )

    graph_sha256 = fingerprint_hard_edges(
        hard_edges
    )

    cohort = build_cycle_source_cohort(
        repository_root,
        hard_edges,
        module_paths,
        expected_fingerprints=(
            source_fingerprints_by_module
        ),
    )

    if cohort.canonical_hash_missing != 0:
        raise ValueError(
            "Cyclic source evidence lacks index fingerprints"
        )

    if cohort.canonical_hash_matches != len(
        cohort.parsed_sources
    ):
        raise ValueError(
            "Accepted cyclic sources are not index-bound"
        )

    import_sites = analyze_cyclic_import_sites(
        cohort.hard_edges,
        cohort.parsed_sources,
    )

    discovery = discover_conditional_reexports(
        import_sites,
        cohort.parsed_sources,
        cohort.indexed_module_ids,
        max_searches=max_searches,
    )

    cyclic_modules = tuple(sorted({
        module
        for component in (
            import_sites.topology.cyclic_components
        )
        for module in component.members
    }))

    if len(cyclic_modules) != (
        cohort.cyclic_module_count
    ):
        raise ValueError(
            "Cyclic cohort and graph topology differ"
        )

    return CycleSemanticsSnapshot(
        graph_sha256=graph_sha256,
        cyclic_modules=cyclic_modules,
        observed_source_fingerprints=(
            cohort.fingerprints
        ),
        source_issues=tuple(
            (
                issue.module_id,
                issue.reason,
            )
            for issue in cohort.issues
        ),
        coverage_status=cohort.coverage_status,
        source_snapshot_binding=(
            cohort.source_snapshot_binding
        ),
        runtime_execution_status=(
            cohort.runtime_execution_status
        ),
        import_sites=import_sites,
        conditional_discovery=discovery,
    )

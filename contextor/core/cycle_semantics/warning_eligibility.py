"""Pure, fail-closed eligibility for committed model-pass cycle paths.

Eligibility is a claim about a validated static model, not Python runtime safety.
This module does not change structural cycles or active diagnostics.
"""

from __future__ import annotations

from collections.abc import Mapping

from .generation_manifest import MANIFEST_VERSION
from .publication_binding import (
    PUBLICATION_BINDING_VERSION,
    CanonicalCycleManifestReceipt,
    verify_co_published_cycle_manifest,
)
from .scc import analyze_import_cycle_topology


def _verified_model_pass_cycle_paths(
    state,
    *,
    expected_revision,
    expected_state_id,
    expected_repo_id,
    expected_root_path,
) -> frozenset[tuple[str, ...]]:
    """Return structural paths in SCCs with committed v2 model-pass claims."""
    empty: frozenset[tuple[str, ...]] = frozenset()
    try:
        receipt = getattr(state, "cycle_source_publication", None)
        if type(receipt) is not CanonicalCycleManifestReceipt:
            return empty
        if (
            receipt.version != PUBLICATION_BINDING_VERSION
            or receipt.prepared_manifest.version != MANIFEST_VERSION
            or getattr(state, "resync_required", False) is not False
            or getattr(state, "cycles_state", None) != "fresh"
            or getattr(state, "cycle_semantics_state", None) != "fresh"
        ):
            return empty

        if not verify_co_published_cycle_manifest(
            state,
            revision=expected_revision,
            state_id=expected_state_id,
            repo_id=expected_repo_id,
            root_path=expected_root_path,
        ):
            return empty
        hard_edges = state.dependency_graph.hard_edges
        if not isinstance(hard_edges, Mapping):
            return empty
        topology = analyze_import_cycle_topology(hard_edges)
        components = topology.cyclic_components
        claims = receipt.prepared_manifest.components
        if (
            len(components) != len(claims)
            or any(
                component.members != claim.members
                for component, claim in zip(components, claims)
            )
        ):
            return empty

        paths = state.cycles
        if not isinstance(paths, (list, tuple)):
            return empty
        memberships = tuple(frozenset(item.members) for item in components)
        eligible = {
            index
            for index, claim in enumerate(claims)
            if claim.model_classification
            == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        }
        result: set[tuple[str, ...]] = set()
        seen_paths: set[tuple[str, ...]] = set()
        for path in paths:
            if (
                not isinstance(path, (list, tuple))
                or len(path) < 2
                or any(type(node) is not str or not node for node in path)
                or path[0] != path[-1]
            ):
                return empty
            interior = tuple(path[:-1])
            if len(interior) != len(set(interior)):
                return empty
            path_identity = tuple(path)
            if path_identity in seen_paths:
                return empty
            seen_paths.add(path_identity)
            if any(
                target not in hard_edges.get(source, ())
                for source, target in zip(path, path[1:])
            ):
                return empty
            nodes = frozenset(path[:-1])
            matching = tuple(
                index for index, members in enumerate(memberships)
                if nodes <= members
            )
            if len(matching) != 1:
                return empty
            if matching[0] in eligible:
                result.add(tuple(path))
        return frozenset(result)
    except (AttributeError, KeyError, TypeError, ValueError, IndexError):
        return empty

"""Pure installed partial SCC model-PASS path eligibility.

The caller holds the canonical LIVE owner's state lock throughout this call.
Eligibility is restricted static-model evidence, not runtime safety.
"""

from __future__ import annotations

from collections.abc import Mapping

from .live_installed_partial_claims import (
    _PARTIAL_LIVE_AUTHORITY,
    _PARTIAL_LIVE_MATCH,
    assess_live_installed_partial_claims,
)
from .scc import analyze_import_cycle_topology


def _verified_installed_partial_model_pass_paths(
    state,
    *,
    canonical_revision,
    authority_identity,
    activity_epoch,
    expected_revision,
    expected_state_id,
    expected_repo_id,
    expected_root_path,
    expected_graph_sha256,
    expected_claims_sha256,
    expected_service_instance_id,
    expected_process_start_identity,
) -> frozenset[tuple[str, ...]]:
    """Select validated structural paths in installed partial PASS SCCs."""
    empty: frozenset[tuple[str, ...]] = frozenset()
    try:
        installed = assess_live_installed_partial_claims(
            state,
            canonical_revision=canonical_revision,
            authority_identity=authority_identity,
            activity_epoch=activity_epoch,
            expected_revision=expected_revision,
            expected_state_id=expected_state_id,
            expected_repo_id=expected_repo_id,
            expected_root_path=expected_root_path,
            expected_graph_sha256=expected_graph_sha256,
            expected_claims_sha256=expected_claims_sha256,
            expected_service_instance_id=expected_service_instance_id,
            expected_process_start_identity=expected_process_start_identity,
        )
        if (
            type(installed) is not dict
            or installed.get("status") != "ok"
            or installed.get("binding_state") != _PARTIAL_LIVE_MATCH
            or installed.get("revision") != expected_revision
            or installed.get("state_id") != expected_state_id
            or installed.get("graph_sha256") != expected_graph_sha256
            or installed.get("claims_sha256") != expected_claims_sha256
            or installed.get("activity_epoch") != activity_epoch
            or installed.get("authority") != _PARTIAL_LIVE_AUTHORITY
        ):
            return empty

        hard_edges = state.dependency_graph.hard_edges
        if not isinstance(hard_edges, Mapping):
            return empty
        topology = analyze_import_cycle_topology(hard_edges)
        components = topology.cyclic_components
        summaries = installed.get("components")
        if (
            type(summaries) is not tuple
            or len(summaries) != len(components)
            or any(
                type(summary) is not dict
                or set(summary) != {
                    "members", "preparation_state", "model_classification",
                }
                or type(summary["members"]) is not tuple
                or summary["members"] != component.members
                for summary, component in zip(summaries, components)
            )
        ):
            return empty

        paths = getattr(state, "cycles", None)
        if not isinstance(paths, (list, tuple)):
            return empty
        memberships = tuple(frozenset(item.members) for item in components)
        eligible = {
            index
            for index, summary in enumerate(summaries)
            if summary["preparation_state"] == "PREPARED_UNPUBLISHED"
            and summary["model_classification"]
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
            nodes = frozenset(interior)
            matching = tuple(
                index for index, members in enumerate(memberships)
                if nodes <= members
            )
            if len(matching) != 1:
                return empty
            if matching[0] in eligible:
                result.add(path_identity)
        return frozenset(result)
    except (
        AttributeError, KeyError, TypeError, ValueError, IndexError,
        RecursionError, OverflowError,
    ):
        return empty

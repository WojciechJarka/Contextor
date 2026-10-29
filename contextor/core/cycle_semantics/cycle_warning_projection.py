"""Pure projection of installed model acceptance and structural cycle warnings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .partial_warning_eligibility import (
    _verified_installed_partial_model_pass_paths,
)
from .scc import analyze_import_cycle_topology


@dataclass(frozen=True)
class InstalledCycleWarningProjection:
    status: str
    reason: str | None
    revision: int | None
    structural_paths: tuple[tuple[str, ...], ...] | None
    model_pass_paths: tuple[tuple[str, ...], ...] | None
    active_warning_paths: tuple[tuple[str, ...], ...] | None


def project_installed_cycle_warnings(
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
) -> InstalledCycleWarningProjection:
    """Partition valid canonical paths under a caller-held LIVE state lock."""
    unavailable = InstalledCycleWarningProjection(
        status="UNAVAILABLE",
        reason="STRUCTURAL_CYCLE_INVENTORY_UNAVAILABLE",
        revision=None,
        structural_paths=None,
        model_pass_paths=None,
        active_warning_paths=None,
    )
    try:
        if (
            getattr(state, "cycles_state", None) != "fresh"
            or getattr(state, "resync_required", False) is not False
        ):
            return unavailable
        paths = getattr(state, "cycles", None)
        if type(paths) not in (list, tuple):
            return unavailable
        hard_edges = state.dependency_graph.hard_edges
        if not isinstance(hard_edges, Mapping):
            return unavailable
        components = analyze_import_cycle_topology(
            hard_edges
        ).cyclic_components
        memberships = tuple(frozenset(item.members) for item in components)
        seen_paths: set[tuple[str, ...]] = set()
        for path in paths:
            if (
                type(path) not in (list, tuple)
                or len(path) < 2
                or any(type(node) is not str or not node for node in path)
                or path[0] != path[-1]
            ):
                return unavailable
            interior = tuple(path[:-1])
            if len(interior) != len(set(interior)):
                return unavailable
            identity = tuple(path)
            if identity in seen_paths:
                return unavailable
            seen_paths.add(identity)
            if any(
                target not in hard_edges.get(source, ())
                for source, target in zip(path, path[1:])
            ):
                return unavailable
            nodes = frozenset(interior)
            if sum(nodes <= members for members in memberships) != 1:
                return unavailable
        structural_paths = tuple(tuple(path) for path in paths)

        eligible = _verified_installed_partial_model_pass_paths(
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
        if type(eligible) is not frozenset or not eligible <= set(structural_paths):
            return unavailable
        model_pass_paths = tuple(
            path for path in structural_paths if path in eligible
        )
        active_warning_paths = tuple(
            path for path in structural_paths if path not in eligible
        )
        if (
            not set(model_pass_paths).isdisjoint(active_warning_paths)
            or set(model_pass_paths) | set(active_warning_paths)
            != set(structural_paths)
            or len(model_pass_paths) + len(active_warning_paths)
            != len(structural_paths)
        ):
            return unavailable
        return InstalledCycleWarningProjection(
            status="FRESH",
            reason=None,
            revision=canonical_revision,
            structural_paths=structural_paths,
            model_pass_paths=model_pass_paths,
            active_warning_paths=active_warning_paths,
        )
    except (
        AttributeError, KeyError, TypeError, ValueError, IndexError,
        RecursionError, OverflowError,
    ):
        return unavailable

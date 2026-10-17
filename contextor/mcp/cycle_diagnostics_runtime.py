"""Read-only LIVE execution adapter for cycle semantics.

This is not a registered public MCP tool.

The adapter never starts or claims a LIVE owner,
publishes canonical state, or executes indexed sources.

Stable IPC revisions and file hashes are observations,
not an atomic graph/source transaction.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from contextor.core.repository_identity import (
    read_repository_identity,
)
from contextor.core.live_state.ipc import LiveStateClient
from contextor.core.live_state.runtime import (
    _read_endpoint,
    _status_matches_endpoint,
)
from contextor.core.cycle_semantics.source_cohort import (
    build_cycle_source_cohort,
)
from contextor.core.cycle_semantics.edge_sites import (
    analyze_cyclic_import_sites,
)
from contextor.core.cycle_semantics.conditional_discovery import (
    discover_conditional_reexports,
)
from contextor.core.cycle_semantics.public_projection import (
    project_cycle_semantics,
)
from contextor.mcp.output_guard import guard_large_output


def _error(code: str) -> str:
    return json.dumps(
        {
            "status": "error",
            "error": code,
        },
        indent=2,
        ensure_ascii=False,
    )


def _valid_revision(value: object) -> bool:
    return type(value) is int and value >= 0


def _valid_ping(ping: object, revision: int) -> bool:
    return (
        isinstance(ping, dict)
        and ping.get("status") == "ok"
        and ping.get("available") is True
        and ping.get("revision") == revision
    )


def _valid_events(
    events: object,
    revision: int,
) -> bool:
    return (
        isinstance(events, dict)
        and events.get("status") == "ok"
        and events.get("revision") == revision
        and events.get("latest_revision") == revision
        and events.get("continuity") == "continuous"
        and events.get("resync_required") is False
        and isinstance(events.get("activity_epoch"), str)
        and bool(events["activity_epoch"])
    )


def _same_authority(
    first: dict,
    second: dict,
    endpoint,
) -> bool:
    return (
        _status_matches_endpoint(first, endpoint)
        and _status_matches_endpoint(second, endpoint)
        and all(
            first.get(name) == second.get(name)
            for name in (
                "repo_id",
                "root_path",
                "runtime_domain_id",
                "service_instance_id",
                "lease_generation",
                "service_pid",
                "process_start_identity",
                "endpoint_fingerprint",
            )
        )
    )


def compute_live_cycle_diagnostics(
    repo_path: str,
    *,
    max_components: int = 8,
    max_edges: int = 3,
    max_groups: int = 3,
    max_witnesses: int = 3,
    max_searches: int = 256,
    allow_large_output: bool = False,
) -> str:
    """Return guarded cycle evidence from an existing LIVE owner.

    Fail closed on missing/stale authority or revision changes.

    Canonical graph revision is an observed IPC revision,
    not proof of atomic binding to filesystem sources.
    """

    if type(allow_large_output) is not bool:
        return _error("invalid_allow_large_output")

    if (
        type(max_searches) is not int
        or not 1 <= max_searches <= 4096
    ):
        return _error("invalid_max_searches")

    for name, value in (
        ("max_components", max_components),
        ("max_edges", max_edges),
        ("max_groups", max_groups),
        ("max_witnesses", max_witnesses),
    ):
        if type(value) is not int or not 0 <= value <= 64:
            return _error("invalid_" + name)

    try:
        root = Path(repo_path).expanduser().resolve()

        identity = read_repository_identity(root)

        if identity is None:
            return _error("repository_identity_unavailable")

        endpoint = _read_endpoint(root, strict=True)

        if endpoint is None:
            return _error("live_endpoint_unavailable")

        if (
            endpoint.repo_id != identity.repo_id
            or endpoint.root_path != str(root)
        ):
            return _error("live_endpoint_identity_mismatch")

        client = LiveStateClient(
            endpoint,
            is_owner=False,
        )

        first_authority = client.authority_status()

        if not _status_matches_endpoint(
            first_authority,
            endpoint,
        ):
            return _error("live_authority_unverified")

        first_ping = client.ping()
        snapshot = client.snapshot()

        if (
            not isinstance(snapshot, dict)
            or snapshot.get("status") != "ok"
        ):
            return _error("canonical_snapshot_unavailable")

        revision = snapshot.get("revision")

        if not _valid_revision(revision):
            return _error("canonical_revision_invalid")

        if not _valid_ping(first_ping, revision):
            return _error("canonical_revision_transition")

        state = snapshot.get("state")

        if state is None:
            return _error("canonical_state_unavailable")

        first_events = client.get_events(
            after_revision=revision,
            limit=1,
        )

        if not _valid_events(first_events, revision):
            return _error("live_event_continuity_unverified")

        if (
            first_authority.get("revision")
            != revision
        ):
            return _error("live_authority_revision_transition")

        absent_resync_attribute = object()

        state_resync_required = getattr(
            state,
            "resync_required",
            absent_resync_attribute,
        )

        if (
            state_resync_required is not absent_resync_attribute
            and state_resync_required is not False
        ):
            return _error("canonical_resync_not_verified")

        if getattr(state, "cycles_state", None) != "fresh":
            return _error("canonical_cycles_not_fresh")

        graph = getattr(
            state,
            "dependency_graph",
            None,
        )

        if graph is None:
            return _error("canonical_graph_unavailable")

        hard_edges = getattr(
            graph,
            "hard_edges",
            None,
        )

        if hard_edges is None:
            return _error("canonical_hard_edges_unavailable")

        modules = getattr(state, "modules", None)

        if not isinstance(modules, dict):
            return _error("canonical_module_inventory_invalid")

        module_paths = {
            module_id: getattr(module, "path", None)
            for module_id, module in modules.items()
        }

        # No safe snapshot-bound FileState hash mapping
        # is established by the current C33 contract.
        # Do not fabricate canonical source fingerprints.
        cohort = build_cycle_source_cohort(
            root,
            hard_edges,
            module_paths,
            expected_fingerprints=None,
        )

        sites = analyze_cyclic_import_sites(
            cohort.hard_edges,
            cohort.parsed_sources,
        )

        discovery = discover_conditional_reexports(
            sites,
            cohort.parsed_sources,
            cohort.indexed_module_ids,
            max_searches=max_searches,
        )

        projection = project_cycle_semantics(
            sites,
            discovery,
            max_components=max_components,
            max_edges=max_edges,
            max_groups=max_groups,
            max_witnesses=max_witnesses,
        )

        last_ping = client.ping()
        last_authority = client.authority_status()
        last_events = client.get_events(
            after_revision=revision,
            limit=1,
        )

        if not _valid_ping(last_ping, revision):
            return _error("canonical_revision_transition")

        if not _same_authority(
            first_authority,
            last_authority,
            endpoint,
        ):
            return _error("live_authority_transition")

        if (
            last_authority.get("revision")
            != revision
        ):
            return _error("live_authority_revision_transition")

        if not _valid_events(last_events, revision):
            return _error("live_event_continuity_transition")

        if (
            first_events["activity_epoch"]
            != last_events["activity_epoch"]
        ):
            return _error("live_activity_epoch_transition")

        projection["canonical_graph_revision"] = revision
        projection["canonical_graph_revision_status"] = (
            "BRACKETED_IPC_REVISION_NOT_ATOMIC_SOURCE"
        )

        partial = (
            bool(cohort.issues)
            or discovery.coverage_status
            != "BOUNDED_SELECTION_COMPLETE"
        )

        payload = {
            "status": (
                "partial_source_evidence"
                if partial
                else "computed_non_atomic"
            ),
            "authority": {
                "repo_id": identity.repo_id,
                "canonical_revision": revision,
                "activity_epoch": (
                    first_events["activity_epoch"]
                ),
                "authority_status": (
                    "STABLE_BRACKETED_OBSERVATION"
                ),
                "source_snapshot_binding": (
                    "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
                ),
            },
            "source_cohort": {
                "coverage_status": (
                    cohort.coverage_status
                ),
                "cyclic_module_count": (
                    cohort.cyclic_module_count
                ),
                "parsed_module_count": len(
                    cohort.parsed_sources
                ),
                "canonical_hash_matches": (
                    cohort.canonical_hash_matches
                ),
                "canonical_hash_missing": (
                    cohort.canonical_hash_missing
                ),
                "issues": [
                    asdict(issue)
                    for issue in cohort.issues
                ],
            },
            "cycle_semantics": projection,
        }

        serialized = json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )

        return guard_large_output(
            serialized,
            allow_large_output=allow_large_output,
            retry_instruction=(
                "Call again with narrower max_components, "
                "max_edges, max_groups or max_witnesses; "
                "or explicitly set allow_large_output=true."
            ),
            reason=(
                "Cycle-semantic evidence exceeds the "
                "recommended MCP response size."
            ),
        )

    except (
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        OverflowError,
        RecursionError,
    ):
        return _error(
            "read_only_cycle_diagnostics_failed"
        )

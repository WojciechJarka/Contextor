"""Bounded source-byte checks for SCC model evidence.

Caller-supplied byte snapshots are checked against declared index fingerprints
and AST signatures. This module cannot authenticate LIVE generation or prove
atomic source capture, import execution, or runtime safety.
"""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass

from contextor.core.source import (
    ParsedSourceInput,
    SourceError,
    SourceSnapshot,
    parse_source_snapshot,
)

from .contracts import (
    CycleSemanticsSnapshot,
    fingerprint_hard_edges,
)
from .evidence import (
    SourceBoundCycleEvidence,
    OPTIONAL_EVIDENCE_SEMANTIC_VERSION,
    assess_index_bound_scc_models,
    build_source_bound_cycle_evidence,
    _digest,
    _scenario_fingerprint,
)
from .edge_sites import analyze_cyclic_import_sites
from .model_source_closure import (
    CycleModelSourceClosure,
    compute_cycle_model_source_closures_with_optional_children,
)
from .scc import analyze_import_cycle_topology


_BYTE_AUTHORITY = (
    "CALLER_SUPPLIED_BYTES_NOT_ATOMICALLY_BOUND_TO_LIVE"
)


@dataclass(frozen=True)
class SCCSourceByteAssessment:
    members: tuple[str, ...]
    model_classification: str
    bytes_state: str
    reason: str | None
    authority: str = _BYTE_AUTHORITY


def assess_scc_source_bytes(
    hard_edges: Mapping[str, object],
    indexed_fingerprints_by_module: Mapping[str, str],
    snapshot: CycleSemanticsSnapshot,
    source_evidence: SourceBoundCycleEvidence,
    source_snapshots: Mapping[str, SourceSnapshot],
    *,
    max_source_bytes: int = 2 * 1024 * 1024,
    max_closure_bytes: int = 32 * 1024 * 1024,
) -> tuple[SCCSourceByteAssessment, ...]:
    """Verify actual source bytes against P0 AST and index evidence.

    Source snapshots are caller-supplied, not authenticated LIVE data.
    No disk I/O, IPC, analyzed-module imports or model execution.
    """
    if not isinstance(source_snapshots, Mapping):
        raise TypeError("source_snapshots must be a mapping")

    if (
        type(max_source_bytes) is not int
        or not 1 <= max_source_bytes <= 64 * 1024 * 1024
    ):
        raise ValueError("max_source_bytes out of range")

    if (
        type(max_closure_bytes) is not int
        or not 1 <= max_closure_bytes <= 256 * 1024 * 1024
    ):
        raise ValueError("max_closure_bytes out of range")

    # P0 remains the sole owner of declared graph/index/model
    # consistency. P1B verifies bytes and reconstructed AST.
    model_results = assess_index_bound_scc_models(
        hard_edges,
        indexed_fingerprints_by_module,
        snapshot,
        source_evidence,
    )

    assessments: list[SCCSourceByteAssessment] = []

    # Reuse parsed hashes for closure members shared by SCCs.
    # Cache is execution-local and does not certify generation.
    cache: dict[str, tuple[str, str | None, ParsedSourceInput | None]] = {}

    for position, model in enumerate(model_results):
        members = model.members

        def unavailable(reason: str) -> SCCSourceByteAssessment:
            return SCCSourceByteAssessment(
                members,
                "INDETERMINATE",
                "UNAVAILABLE",
                reason,
            )

        def mismatch(reason: str) -> SCCSourceByteAssessment:
            return SCCSourceByteAssessment(
                members,
                "INDETERMINATE",
                "EVIDENCE_MISMATCH",
                reason,
            )

        if model.evidence_state != "DECLARED_INPUTS_CONSISTENT":
            assessments.append(unavailable(
                model.reason or "P0_MODEL_EVIDENCE_UNAVAILABLE"
            ))
            continue

        # P0 has already verified exact component ordering,
        # SCC membership, closure identity and evidence tokens.
        component = source_evidence.components[position]
        closure = component.reachable_modules
        signatures = {
            module: (raw_hash, ast_hash)
            for module, raw_hash, ast_hash
            in component.source_signatures
        }

        total_bytes = 0
        outcome: SCCSourceByteAssessment | None = None

        for module in closure:
            supplied = source_snapshots.get(module)

            if (
                not isinstance(supplied, SourceSnapshot)
                or type(supplied.raw) is not bytes
            ):
                outcome = unavailable(
                    "SOURCE_BYTES_UNAVAILABLE:" + module
                )
                break

            size = len(supplied.raw)

            if (
                size > max_source_bytes
                or total_bytes + size > max_closure_bytes
            ):
                outcome = unavailable(
                    "SOURCE_BYTE_BUDGET_EXCEEDED:" + module
                )
                break

            total_bytes += size

            # Do not trust the SourceSnapshot fingerprint
            # until it has been recomputed from its raw bytes.
            actual = hashlib.sha256(
                supplied.raw
            ).hexdigest()

            if actual != supplied.source_fingerprint:
                outcome = mismatch(
                    "SOURCE_SNAPSHOT_HASH_MISMATCH:" + module
                )
                break

            if actual != indexed_fingerprints_by_module.get(
                module
            ):
                outcome = mismatch(
                    "SOURCE_INDEX_BYTES_MISMATCH:" + module
                )
                break

            if actual != signatures[module][0]:
                outcome = mismatch(
                    "SOURCE_EVIDENCE_BYTES_MISMATCH:" + module
                )
                break

            cached = cache.get(module)

            if cached is None or cached[0] != actual:
                try:
                    parsed = parse_source_snapshot(
                        supplied,
                        module,
                    )
                except SourceError:
                    cache[module] = (actual, None, None)
                else:
                    ast_hash = hashlib.sha256(
                        ast.dump(
                            parsed.tree,
                            include_attributes=True,
                        ).encode("utf-8")
                    ).hexdigest()

                    cache[module] = (actual, ast_hash, parsed)

            observed_ast = cache[module][1]

            if observed_ast is None:
                outcome = unavailable(
                    "SOURCE_BYTES_UNPARSABLE:" + module
                )
                break

            if observed_ast != signatures[module][1]:
                outcome = mismatch(
                    "SOURCE_AST_BYTES_MISMATCH:" + module
                )
                break

        if outcome is None:
            parsed_sources = {
                module: cache[module][2]
                for module in closure
            }
            try:
                replay = build_source_bound_cycle_evidence(
                    hard_edges, parsed_sources,
                )
                replay_scenario = replay.scenarios.components[position]
                supplied_scenario = source_evidence.scenarios.components[position]
                replay_component = replay.components[position]
                supplied_component = source_evidence.components[position]
            except (TypeError, ValueError, KeyError, IndexError, RecursionError, OverflowError):
                outcome = unavailable("MODEL_REPLAY_UNAVAILABLE")
            else:
                if replay_scenario.reason in {
                    "ENTRY_BUDGET_EXCEEDED",
                    "STATEMENT_BUDGET_EXCEEDED",
                    "AST_NODE_BUDGET_EXCEEDED",
                }:
                    outcome = unavailable("MODEL_REPLAY_UNAVAILABLE")
                elif (
                    replay_scenario != supplied_scenario
                    or _scenario_fingerprint(replay_scenario)
                    != _scenario_fingerprint(supplied_scenario)
                    or replay_component.evidence_token
                    != supplied_component.evidence_token
                ):
                    outcome = mismatch("MODEL_REPLAY_MISMATCH")

        if outcome is not None:
            assessments.append(outcome)
        else:
            assessments.append(SCCSourceByteAssessment(
                members,
                model.model_classification,
                "BYTE_AST_CONSISTENT_NON_ATOMIC",
                None,
            ))

    return tuple(assessments)


def assess_optional_scc_source_bytes(
    hard_edges: Mapping[str, object],
    indexed_fingerprints_by_module: Mapping[str, str],
    snapshot: CycleSemanticsSnapshot,
    source_evidence: SourceBoundCycleEvidence,
    source_snapshots: Mapping[str, SourceSnapshot],
    indexed_imports_by_module: Mapping[str, object],
    *,
    package_root: str | None = None,
    source_closures: tuple[CycleModelSourceClosure, ...] | None = None,
    max_source_bytes: int = 2 * 1024 * 1024,
    max_closure_bytes: int = 32 * 1024 * 1024,
) -> tuple[SCCSourceByteAssessment, ...]:
    """Recheck optional evidence from caller-supplied bytes, never LIVE."""

    if not isinstance(hard_edges, Mapping):
        raise TypeError("hard_edges must be a mapping")
    if not isinstance(indexed_fingerprints_by_module, Mapping):
        raise TypeError("fingerprints must be a mapping")
    if not isinstance(snapshot, CycleSemanticsSnapshot):
        raise TypeError("snapshot must be CycleSemanticsSnapshot")
    if not isinstance(source_evidence, SourceBoundCycleEvidence):
        raise TypeError("invalid source evidence")
    if not isinstance(source_snapshots, Mapping):
        raise TypeError("source_snapshots must be a mapping")

    if (
        type(max_source_bytes) is not int
        or not 1 <= max_source_bytes <= 64 * 1024 * 1024
        or type(max_closure_bytes) is not int
        or not 1 <= max_closure_bytes <= 256 * 1024 * 1024
    ):
        raise ValueError("invalid source byte budget")

    topology = analyze_import_cycle_topology(hard_edges)
    structural = topology.cyclic_components

    if not structural:
        return ()

    def reject(
        reason: str,
        state: str = "UNAVAILABLE",
    ) -> tuple[SCCSourceByteAssessment, ...]:
        return tuple(
            SCCSourceByteAssessment(
                members=component.members,
                model_classification="INDETERMINATE",
                bytes_state=state,
                reason=reason,
            )
            for component in structural
        )

    if (
        source_evidence.source_selection != "OPTIONAL_NAMED_CHILDREN"
        or source_evidence.semantic_version
        != OPTIONAL_EVIDENCE_SEMANTIC_VERSION
        or source_evidence.authority
        != "SNAPSHOT_ONLY_NOT_LIVE_FRESHNESS"
        or source_evidence.scenarios.evidence_scope
        != "OPTIONAL_NAMED_CHILDREN_SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
    ):
        return reject("OPTIONAL_EVIDENCE_IDENTITY_MISMATCH")

    adjacency = {
        name: tuple(sorted(set(targets)))
        for name, targets in hard_edges.items()
    }
    for targets in tuple(adjacency.values()):
        for target in targets:
            adjacency.setdefault(target, ())

    graph_hash = _digest(tuple(
        (name, adjacency[name])
        for name in sorted(adjacency)
    ))

    if (
        snapshot.graph_sha256 != fingerprint_hard_edges(hard_edges)
        or source_evidence.graph_fingerprint != graph_hash
        or snapshot.import_sites.topology != topology
        or source_evidence.scenarios.topology != topology
    ):
        return reject("OPTIONAL_GRAPH_OR_TOPOLOGY_MISMATCH")

    if (
        snapshot.coverage_status != "FILESYSTEM_STABLE_NON_ATOMIC"
        or snapshot.source_issues
    ):
        return reject("OPTIONAL_CYCLIC_SNAPSHOT_INCOMPLETE")

    cyclic_members = tuple(sorted({
        member
        for component in structural
        for member in component.members
    }))
    observed = snapshot.observed_source_fingerprints

    if (
        snapshot.cyclic_modules != cyclic_members
        or tuple(sorted(name for name, _ in observed)) != cyclic_members
        or any(
            fingerprint != indexed_fingerprints_by_module.get(name)
            for name, fingerprint in observed
        )
    ):
        return reject("OPTIONAL_CYCLIC_SOURCE_IDENTITY_MISMATCH")

    try:
        expected = (
            compute_cycle_model_source_closures_with_optional_children(
                hard_edges,
                indexed_imports_by_module,
                package_root=package_root,
            )
        )
    except (AttributeError, TypeError, ValueError):
        return reject("OPTIONAL_COHORT_UNAVAILABLE")

    if (
        type(source_closures) is not tuple
        or source_closures != expected
        or len(expected) != len(structural)
        or tuple(row.members for row in expected)
        != tuple(row.members for row in structural)
    ):
        return reject("OPTIONAL_COHORT_IDENTITY_MISMATCH")

    selected = tuple(sorted({
        name
        for row in expected
        for name in row.evidence_source_modules
    }))

    if (
        set(indexed_fingerprints_by_module) != set(hard_edges)
        or set(source_snapshots) != set(selected)
    ):
        return reject("OPTIONAL_CAPTURE_SET_MISMATCH")

    parsed: dict[str, ParsedSourceInput] = {}
    total_bytes = 0

    for module in selected:
        supplied = source_snapshots[module]

        if (
            type(supplied) is not SourceSnapshot
            or type(supplied.raw) is not bytes
            or type(supplied.source_fingerprint) is not str
        ):
            return reject("SOURCE_BYTES_UNAVAILABLE:" + module)

        size = len(supplied.raw)
        total_bytes += size

        if (
            size > max_source_bytes
            or total_bytes > max_closure_bytes
        ):
            return reject(
                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module
            )

        actual_hash = hashlib.sha256(supplied.raw).hexdigest()

        if actual_hash != supplied.source_fingerprint:
            return reject(
                "SOURCE_SNAPSHOT_HASH_MISMATCH:" + module,
                "EVIDENCE_MISMATCH",
            )

        if actual_hash != indexed_fingerprints_by_module[module]:
            return reject(
                "SOURCE_INDEX_BYTES_MISMATCH:" + module,
                "EVIDENCE_MISMATCH",
            )

        try:
            parsed[module] = parse_source_snapshot(
                supplied, module
            )
        except SourceError:
            return reject("SOURCE_BYTES_UNPARSABLE:" + module)

    try:
        replay_sites = analyze_cyclic_import_sites(
            hard_edges, parsed
        )
    except (TypeError, ValueError, RecursionError, OverflowError):
        return reject("OPTIONAL_LEXICAL_REPLAY_UNAVAILABLE")

    if replay_sites != snapshot.import_sites:
        return reject(
            "OPTIONAL_LEXICAL_EVIDENCE_MISMATCH",
            "EVIDENCE_MISMATCH",
        )

    if any(
        site.matched_edge_count != len(site.internal_edges)
        or site.unresolved_edge_count != 0
        or any(
            edge.status != "LEXICAL_CANDIDATES"
            or not edge.sites
            for edge in site.internal_edges
        )
        for site in replay_sites.components
    ):
        return reject("OPTIONAL_CYCLIC_IMPORT_SITES_INCOMPLETE")

    try:
        replay = build_source_bound_cycle_evidence(
            hard_edges,
            parsed,
            source_selection="OPTIONAL_NAMED_CHILDREN",
            indexed_imports_by_module=indexed_imports_by_module,
            package_root=package_root,
            source_closures=expected,
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
        KeyError,
        IndexError,
        RecursionError,
        OverflowError,
    ):
        return reject("OPTIONAL_MODEL_REPLAY_UNAVAILABLE")

    if replay != source_evidence:
        return reject(
            "OPTIONAL_MODEL_OR_TOKEN_REPLAY_MISMATCH",
            "EVIDENCE_MISMATCH",
        )

    results: list[SCCSourceByteAssessment] = []

    for component in replay.components:
        if (
            component.coverage != "COMPLETE_FRESH_MEMBER_ENTRIES"
            or component.classification not in {
                "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
                "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
            }
        ):
            results.append(SCCSourceByteAssessment(
                members=component.members,
                model_classification="INDETERMINATE",
                bytes_state="UNAVAILABLE",
                reason=component.reason or "OPTIONAL_MODEL_INCOMPLETE",
            ))
            continue

        results.append(SCCSourceByteAssessment(
            members=component.members,
            model_classification=component.classification,
            bytes_state="BYTE_AST_CONSISTENT_NON_ATOMIC",
            reason=None,
        ))

    return tuple(results)

"""Source-bound, snapshot-only evidence for cyclic SCC scenario assessments.

Tokens invalidate on source-only semantic changes, even with identical hard edges.
This module neither establishes current LIVE freshness nor publishes warnings.
"""

from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from contextor.core.source import ParsedSourceInput

from .contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
from .scc import analyze_import_cycle_topology
from .initialization_model import ImportOrderAssessment, ModelEvent
from .package_model import PackageImportAssessment, PackageModelEvent
from .model_source_closure import compute_cycle_model_source_closures
from .model_identity import indexed_to_logical_module, logical_to_indexed_module
from .scenarios import (
    CycleComponentScenarios, CycleScenarioReport, analyze_cycle_scenarios,
)

EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/2"
_MISSING = "MISSING"


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ComponentSourceEvidence:
    members: tuple[str, ...]
    reachable_modules: tuple[str, ...]
    source_signatures: tuple[tuple[str, str, str], ...]
    evidence_token: str
    classification: str
    coverage: str
    reason: str | None
    model_kind: str = "FLAT_MODULE"


def _scenario_fingerprint(scenario: CycleComponentScenarios) -> str:
    return _digest(asdict(scenario))


def _component_token(
    members: tuple[str, ...],
    subgraph: tuple[tuple[str, tuple[str, ...]], ...],
    signatures: tuple[tuple[str, str, str], ...],
    scenario: CycleComponentScenarios,
) -> str:
    return _digest((
        EVIDENCE_SEMANTIC_VERSION, members, subgraph, signatures,
        scenario.model_kind, scenario.evidence_scope,
        _scenario_fingerprint(scenario),
    ))


@dataclass(frozen=True)
class SourceBoundCycleEvidence:
    semantic_version: str
    graph_fingerprint: str
    source_manifest_fingerprint: str
    components: tuple[ComponentSourceEvidence, ...]
    scenarios: CycleScenarioReport
    authority: str = "SNAPSHOT_ONLY_NOT_LIVE_FRESHNESS"


@dataclass(frozen=True)
class CycleEvidenceChange:
    members: tuple[str, ...]
    change: str
    before: str | None
    after: str | None
    before_token: str | None
    after_token: str | None


@dataclass(frozen=True)
class SCCModelEvidenceAssessment:
    members: tuple[str, ...]
    model_classification: str
    evidence_state: str
    reason: str | None
    authority: str = "SNAPSHOT_MODEL_ONLY_NOT_LIVE_CERTIFIED"


def assess_index_bound_scc_models(
    hard_edges: Mapping[str, set[str] | frozenset[str] | list[str] | tuple[str, ...]],
    indexed_fingerprints_by_module: Mapping[str, str],
    snapshot: CycleSemanticsSnapshot,
    source_evidence: SourceBoundCycleEvidence,
) -> tuple[SCCModelEvidenceAssessment, ...]:
    """Check declared index, structural and model evidence without refreshing it.

    Caller-supplied AST provenance and LIVE generation are not certified here.
    """
    if not isinstance(indexed_fingerprints_by_module, Mapping):
        raise TypeError("indexed fingerprints must be a mapping")
    if not isinstance(snapshot, CycleSemanticsSnapshot):
        raise TypeError("snapshot must be CycleSemanticsSnapshot")
    if not isinstance(source_evidence, SourceBoundCycleEvidence):
        raise TypeError("source_evidence must be SourceBoundCycleEvidence")

    topology = analyze_import_cycle_topology(hard_edges)
    graph_hash = fingerprint_hard_edges(hard_edges)
    adjacency = {
        source: tuple(sorted(set(targets)))
        for source, targets in hard_edges.items()
    }
    for targets in tuple(adjacency.values()):
        for target in targets:
            adjacency.setdefault(target, ())
    graph_items = tuple((node, adjacency[node]) for node in sorted(adjacency))

    components = topology.cyclic_components
    def result(members: tuple[str, ...], reason: str, *,
               state: str = "EVIDENCE_MISMATCH") -> SCCModelEvidenceAssessment:
        return SCCModelEvidenceAssessment(
            members, "INDETERMINATE", state, reason,
        )

    if not components:
        return ()

    global_reason: str | None = None
    if snapshot.graph_sha256 != graph_hash:
        global_reason = "SNAPSHOT_GRAPH_FINGERPRINT_MISMATCH"
    elif source_evidence.graph_fingerprint != _digest(graph_items):
        global_reason = "SOURCE_GRAPH_FINGERPRINT_MISMATCH"
    elif (
        snapshot.import_sites.topology != topology
        or source_evidence.scenarios.topology != topology
    ):
        global_reason = "SCC_TOPOLOGY_MISMATCH"
    elif source_evidence.semantic_version != EVIDENCE_SEMANTIC_VERSION:
        global_reason = "EVIDENCE_SEMANTIC_VERSION_MISMATCH"
    elif (
        source_evidence.authority != "SNAPSHOT_ONLY_NOT_LIVE_FRESHNESS"
        or source_evidence.scenarios.evidence_scope
        != "SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
    ):
        global_reason = "SOURCE_AUTHORITY_MISMATCH"
    elif (
        any(not isinstance(c, CycleComponentScenarios)
            for c in source_evidence.scenarios.components)
        or any(not isinstance(c, ComponentSourceEvidence)
               for c in source_evidence.components)
        or
        len(snapshot.import_sites.components) != len(components)
        or len(source_evidence.scenarios.components) != len(components)
        or len(source_evidence.components) != len(components)
        or tuple(site.members for site in snapshot.import_sites.components)
        != tuple(c.members for c in components)
        or tuple(c.members for c in source_evidence.scenarios.components)
        != tuple(c.members for c in components)
        or tuple(c.members for c in source_evidence.components)
        != tuple(c.members for c in components)
    ):
        global_reason = "SCC_COMPONENT_IDENTITY_MISMATCH"

    if global_reason is not None:
        return tuple(result(c.members, global_reason) for c in components)

    index = dict(indexed_fingerprints_by_module)
    observed = dict(snapshot.observed_source_fingerprints)
    cyclic_members = tuple(sorted(
        member for component in components for member in component.members
    ))
    closures = compute_cycle_model_source_closures(hard_edges)
    outputs: list[SCCModelEvidenceAssessment] = []
    for position, (structural, scenario, evidence) in enumerate(zip(
        components, source_evidence.scenarios.components,
        source_evidence.components,
    )):
        members = structural.members
        if scenario.internal_edges != structural.internal_edges:
            outputs.append(result(members, "SCENARIO_INTERNAL_EDGES_MISMATCH"))
            continue
        site_edges = tuple(
            (edge.source, edge.target)
            for edge in snapshot.import_sites.components[position].internal_edges
        )
        if site_edges != structural.internal_edges:
            outputs.append(result(members, "SNAPSHOT_INTERNAL_EDGES_MISMATCH"))
            continue
        site_component = snapshot.import_sites.components[position]
        if (
            site_component.matched_edge_count != len(structural.internal_edges)
            or site_component.unresolved_edge_count != 0
            or any(
                edge.status != "LEXICAL_CANDIDATES" or not edge.sites
                for edge in site_component.internal_edges
            )
        ):
            outputs.append(result(
                members, "UNRESOLVED_CYCLIC_IMPORT_SITES",
                state="INCOMPLETE_EVIDENCE",
            ))
            continue
        if (
            evidence.classification != scenario.classification
            or evidence.coverage != scenario.coverage
            or evidence.reason != scenario.reason
        ):
            outputs.append(result(members, "SCENARIO_EVIDENCE_MISMATCH"))
            continue

        expected_closure = closures[position].evidence_source_modules
        signatures = evidence.source_signatures
        if not isinstance(signatures, tuple) or any(
            not isinstance(row, tuple) or len(row) != 3
            for row in signatures
        ):
            outputs.append(result(members, "MALFORMED_SOURCE_SIGNATURES"))
            continue
        signature_names = tuple(
            row[0] for row in signatures
        )
        if (
            evidence.reachable_modules != expected_closure
            or len(signatures) != len(expected_closure)
            or signature_names != expected_closure
        ):
            outputs.append(result(members, "SOURCE_CLOSURE_IDENTITY_MISMATCH"))
            continue
        bad_source = next((
            module for module, raw, ast_hash in signatures
            if (
                type(raw) is not str or len(raw) != 64
                or any(ch not in "0123456789abcdef" for ch in raw)
                or type(ast_hash) is not str or len(ast_hash) != 64
                or any(ch not in "0123456789abcdef" for ch in ast_hash)
                or type(index.get(module)) is not str
                or index[module] != raw
            )
        ), None)
        if bad_source is not None:
            outputs.append(result(members, "SOURCE_INDEX_FINGERPRINT_MISMATCH:" + bad_source))
            continue
        subgraph = tuple((node, adjacency[node]) for node in expected_closure)
        expected_token = _component_token(members, subgraph, signatures, scenario)
        if evidence.evidence_token != expected_token:
            outputs.append(result(members, "COMPONENT_EVIDENCE_TOKEN_MISMATCH"))
            continue
        if (
            snapshot.coverage_status != "FILESYSTEM_STABLE_NON_ATOMIC"
            or snapshot.source_issues
            or tuple(sorted(observed)) != cyclic_members
        ):
            outputs.append(result(
                members, "INCOMPLETE_CYCLIC_SOURCE_COHORT",
                state="INCOMPLETE_EVIDENCE",
            ))
            continue
        if (
            snapshot.cyclic_modules != cyclic_members
            or any(observed.get(member) != index.get(member) for member in members)
        ):
            outputs.append(result(members, "SNAPSHOT_SOURCE_IDENTITY_MISMATCH"))
            continue
        model_contracts = {
            "FLAT_MODULE": (
                ImportOrderAssessment,
                "RESTRICTED_FLAT_MODULE_MODEL",
                "CLOSED_FLAT_MODULE_FRESH_ENTRY_MODEL",
                members,
            ),
            "REGULAR_PACKAGE": (
                PackageImportAssessment,
                "RESTRICTED_REGULAR_PACKAGE_MODEL",
                "CLOSED_REGULAR_PACKAGE_FRESH_ENTRY_MODEL",
                tuple(indexed_to_logical_module(member) for member in members),
            ),
        }
        contract = model_contracts.get(scenario.model_kind)
        if (
            contract is None
            or evidence.model_kind != scenario.model_kind
            or scenario.evidence_scope != contract[2]
            or scenario.coverage != "COMPLETE_FRESH_MEMBER_ENTRIES"
            or not isinstance(scenario.entry_assessments, tuple)
            or any(type(a) is not contract[0] for a in scenario.entry_assessments)
            or tuple(a.entry_module for a in scenario.entry_assessments) != contract[3]
            or len(set(contract[3])) != len(contract[3])
            or any(a.evidence_scope != contract[1]
                   for a in scenario.entry_assessments)
            or any(
                type(a.events) is not tuple
                or any(
                    type(event) is not (
                        ModelEvent if scenario.model_kind == "FLAT_MODULE"
                        else PackageModelEvent
                    )
                    for event in a.events
                )
                for a in scenario.entry_assessments
            )
            or any(a.outcome == "UNKNOWN" for a in scenario.entry_assessments)
        ):
            outputs.append(result(
                members, "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS",
                state="INCOMPLETE_EVIDENCE",
            ))
            continue
        if scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS":
            if all(a.outcome == "MODEL_PASS" for a in scenario.entry_assessments):
                outputs.append(SCCModelEvidenceAssessment(
                    members, scenario.classification,
                    "DECLARED_INPUTS_CONSISTENT", None,
                ))
            else:
                outputs.append(result(members, "MODEL_PASS_ENTRY_MISMATCH"))
        elif scenario.classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD":
            member_set = set(members)
            if any(
                a.outcome == "EARLY_BINDING_HAZARD"
                and a.events
                and a.events[-1].operation == "EARLY_BINDING_HAZARD"
                and a.events[-1].target == a.target_module
                and (
                    logical_to_indexed_module(a.events[-1].module, frozenset(adjacency))
                    if scenario.model_kind == "REGULAR_PACKAGE" else a.events[-1].module
                ) in member_set
                and (
                    logical_to_indexed_module(a.events[-1].target, frozenset(adjacency))
                    if scenario.model_kind == "REGULAR_PACKAGE" else a.events[-1].target
                ) in member_set
                for a in scenario.entry_assessments
            ):
                outputs.append(SCCModelEvidenceAssessment(
                    members, scenario.classification,
                    "DECLARED_INPUTS_CONSISTENT", None,
                ))
            else:
                outputs.append(result(members, "INTERNAL_HAZARD_ENTRY_MISMATCH"))
        else:
            outputs.append(result(
                members, scenario.reason or "INDETERMINATE_SCENARIO",
                state="INCOMPLETE_EVIDENCE",
            ))
    return tuple(outputs)


_GENERATION_AUTHORITY = (
    "LIVE_METADATA_COHERENT_MODEL_ONLY_NOT_SOURCE_CERTIFIED"
)


@dataclass(frozen=True)
class SCCGenerationModelAssessment:
    members: tuple[str, ...]
    model_classification: str
    generation_state: str
    reason: str | None
    canonical_revision: int | None
    authority: str = _GENERATION_AUTHORITY


def assess_live_generation_scc_models(
    state: Any,
    freshness: Mapping[str, Any],
    engine: Any,
    indexed_fingerprints_by_module: Mapping[str, str],
    source_evidence: SourceBoundCycleEvidence,
) -> tuple[SCCGenerationModelAssessment, ...]:
    """Gate P0 evidence on coherent supplied LIVE metadata.

    This is not a proof of source-byte provenance, authentic
    LIVE transport, import execution, or runtime safety.

    No filesystem access, model execution, mutation, or IPC.
    """
    if not isinstance(freshness, Mapping):
        raise TypeError("freshness must be a mapping")
    if not isinstance(indexed_fingerprints_by_module, Mapping):
        raise TypeError("indexed fingerprints must be a mapping")
    if not isinstance(source_evidence, SourceBoundCycleEvidence):
        raise TypeError(
            "source_evidence must be SourceBoundCycleEvidence"
        )

    graph = getattr(state, "dependency_graph", None)
    hard_edges = getattr(graph, "hard_edges", None)

    if isinstance(hard_edges, Mapping):
        topology = analyze_import_cycle_topology(hard_edges)
        members = tuple(
            component.members
            for component in topology.cyclic_components
        )
    else:
        members = tuple(
            component.members
            for component in (
                source_evidence.scenarios.topology.cyclic_components
            )
        )

    revision = freshness.get("canonical_revision")
    canonical_revision = (
        revision
        if type(revision) is int and revision >= 0
        else None
    )

    def reject(
        reason: str,
    ) -> tuple[SCCGenerationModelAssessment, ...]:
        return tuple(
            SCCGenerationModelAssessment(
                component,
                "INDETERMINATE",
                "UNAVAILABLE",
                reason,
                canonical_revision,
            )
            for component in members
        )

    if not isinstance(hard_edges, Mapping):
        return reject("CANONICAL_GRAPH_UNAVAILABLE")

    if getattr(state, "resync_required", False) is not False:
        return reject("CANONICAL_RESYNC_REQUIRED")

    if canonical_revision is None:
        return reject("CANONICAL_REVISION_UNAVAILABLE")

    if freshness.get("canonical_state") != "fresh":
        return reject("CANONICAL_STATE_NOT_FRESH")

    if freshness.get("provenance") != "live":
        return reject("LIVE_PROVENANCE_UNVERIFIED")

    # A global workspace envelope usually has no exact
    # source-file SHA proof. Even "verified" is potentially
    # target-local and never certifies the SCC closure.
    workspace_sync = freshness.get("workspace_sync")
    if workspace_sync not in ("unverified", "verified"):
        return reject("WORKSPACE_NOT_CONTENT_VERIFIED")

    families = freshness.get("families")
    if (
        not isinstance(families, Mapping)
        or any(
            families.get(name) != "fresh"
            for name in (
                "module",
                "graph",
                "cycles",
                "cycle_semantics",
            )
        )
    ):
        return reject("REQUIRED_FAMILY_NOT_FRESH")

    if (
        getattr(state, "cycle_semantics_state", None) != "fresh"
        or getattr(state, "cycles_state", None) != "fresh"
    ):
        return reject("STATE_FAMILY_NOT_FRESH")

    snapshot = getattr(state, "cycle_semantics", None)
    if snapshot is None:
        return reject("CYCLE_SNAPSHOT_UNAVAILABLE")

    if (
        engine is None
        or getattr(engine, "state", None) is not state
    ):
        return reject("ENGINE_STATE_IDENTITY_MISMATCH")

    manager = getattr(engine, "state_manager", None)
    if manager is None:
        return reject("STATE_MANAGER_UNAVAILABLE")

    revisions = (
        getattr(state, "revision", None),
        getattr(engine, "revision", None),
        getattr(manager, "revision", None),
    )
    if any(
        type(value) is not int
        or value != canonical_revision
        for value in revisions
    ):
        return reject("CANONICAL_GENERATION_MISMATCH")

    state_id = getattr(state, "state_id", None)
    manager_id = getattr(manager, "state_id", None)
    if (
        type(state_id) is not str
        or not state_id.strip()
        or type(manager_id) is not str
        or manager_id != state_id
    ):
        return reject("STATE_IDENTITY_MISMATCH")

    # P0 remains the sole owner of source/index/model
    # consistency. Do not duplicate its verification.
    model = assess_index_bound_scc_models(
        hard_edges,
        indexed_fingerprints_by_module,
        snapshot,
        source_evidence,
    )

    if tuple(item.members for item in model) != members:
        return reject("MODEL_COMPONENT_IDENTITY_MISMATCH")

    return tuple(
        SCCGenerationModelAssessment(
            item.members,
            item.model_classification,
            (
                "DECLARED_GENERATION_COHERENT"
                if item.evidence_state
                == "DECLARED_INPUTS_CONSISTENT"
                else "UNAVAILABLE"
            ),
            item.reason,
            canonical_revision,
        )
        for item in model
    )


def build_source_bound_cycle_evidence(
    hard_edges: Mapping[str, set[str] | frozenset[str] | list[str] | tuple[str, ...]],
    parsed_sources: Mapping[str, ParsedSourceInput],
) -> SourceBoundCycleEvidence:
    """Bind an SCC scenario report to graph and exact source-snapshot evidence.

    ParsedSourceInput is expected from parse_source_snapshot/with_fingerprint.
    In-memory AST hashes guard against inconsistent caller-provided AST objects.
    No disk source freshness or LIVE authority is established by this function.
    """
    if not isinstance(parsed_sources, Mapping):
        raise TypeError("parsed_sources must be a mapping")

    signatures: dict[str, tuple[str, str]] = {}
    trees: dict[str, ast.Module] = {}
    for module, source in parsed_sources.items():
        if not isinstance(module, str) or not module:
            raise ValueError("invalid source module identity")
        if not isinstance(source, ParsedSourceInput) or not isinstance(source.tree, ast.Module):
            raise TypeError("sources must contain parsed ast.Module snapshots")
        raw_fingerprint = source.source_fingerprint
        if (
            not isinstance(raw_fingerprint, str)
            or len(raw_fingerprint) != 64
            or any(ch not in "0123456789abcdef" for ch in raw_fingerprint)
        ):
            raise ValueError("source_fingerprint must be a lowercase SHA-256 digest")
        ast_fingerprint = hashlib.sha256(
            ast.dump(source.tree, include_attributes=True).encode("utf-8")
        ).hexdigest()
        signatures[module] = (raw_fingerprint, ast_fingerprint)
        trees[module] = source.tree

    report = analyze_cycle_scenarios(hard_edges, trees)
    adjacency: dict[str, tuple[str, ...]] = {
        source: tuple(sorted(set(targets))) for source, targets in hard_edges.items()
    }
    for targets in tuple(adjacency.values()):
        for target in targets:
            adjacency.setdefault(target, ())
    graph_items = tuple((node, adjacency[node]) for node in sorted(adjacency))
    graph_fingerprint = _digest(graph_items)
    source_manifest = tuple((name, *signatures[name]) for name in sorted(signatures))

    components: list[ComponentSourceEvidence] = []
    closures = compute_cycle_model_source_closures(hard_edges)
    for component, closure_row in zip(report.components, closures):
        closure = closure_row.evidence_source_modules
        source_signatures = tuple(
            (module, *signatures.get(module, (_MISSING, _MISSING)))
            for module in closure
        )
        subgraph = tuple((node, adjacency[node]) for node in closure)
        token = _component_token(
            component.members, subgraph, source_signatures, component,
        )
        components.append(ComponentSourceEvidence(
            members=component.members,
            reachable_modules=closure,
            source_signatures=source_signatures,
            evidence_token=token,
            classification=component.classification,
            coverage=component.coverage,
            reason=component.reason,
            model_kind=component.model_kind,
        ))

    return SourceBoundCycleEvidence(
        semantic_version=EVIDENCE_SEMANTIC_VERSION,
        graph_fingerprint=graph_fingerprint,
        source_manifest_fingerprint=_digest(source_manifest),
        components=tuple(components),
        scenarios=report,
    )


def compare_source_bound_cycle_evidence(
    before: SourceBoundCycleEvidence,
    after: SourceBoundCycleEvidence,
) -> tuple[CycleEvidenceChange, ...]:
    """Report model evidence transitions, never LIVE warning ADD/RESOLVE.

    Stable SCC member identities survive source-only edits and DFS cycle changes.
    Equal evidence tokens do not generate noise from unrelated module changes.
    """
    if not isinstance(before, SourceBoundCycleEvidence) or not isinstance(after, SourceBoundCycleEvidence):
        raise TypeError("comparison requires source-bound evidence snapshots")
    old = {component.members: component for component in before.components}
    new = {component.members: component for component in after.components}
    changes: list[CycleEvidenceChange] = []
    for members in sorted(old.keys() | new.keys()):
        past, current = old.get(members), new.get(members)
        if past is None:
            kind = "STRUCTURE_ADDED"
        elif current is None:
            kind = "STRUCTURE_REMOVED"
        elif past.classification != current.classification:
            kind = "MODEL_CLASSIFICATION_CHANGED"
        elif (past.evidence_token != current.evidence_token
              or past.coverage != current.coverage or past.reason != current.reason
              or before.semantic_version != after.semantic_version):
            kind = "EVIDENCE_REVISED"
        else:
            continue
        changes.append(CycleEvidenceChange(
            members=members,
            change=kind,
            before=past.classification if past is not None else None,
            after=current.classification if current is not None else None,
            before_token=past.evidence_token if past is not None else None,
            after_token=current.evidence_token if current is not None else None,
        ))
    return tuple(changes)

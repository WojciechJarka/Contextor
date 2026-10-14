"""Source-bound, snapshot-only evidence for cyclic SCC scenario assessments.

Tokens invalidate on source-only semantic changes, even with identical hard edges.
This module neither establishes current LIVE freshness nor publishes warnings.
"""

from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from contextor.core.source import ParsedSourceInput

from .scenarios import CycleScenarioReport, analyze_cycle_scenarios

EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/1"
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
    for component in report.components:
        visited = set(component.members)
        pending = list(component.members)
        while pending:
            for target in adjacency[pending.pop()]:
                if target not in visited:
                    visited.add(target)
                    pending.append(target)
        closure = tuple(sorted(visited))
        source_signatures = tuple(
            (module, *signatures.get(module, (_MISSING, _MISSING)))
            for module in closure
        )
        subgraph = tuple((node, adjacency[node]) for node in closure)
        token = _digest((
            EVIDENCE_SEMANTIC_VERSION,
            component.members,
            subgraph,
            source_signatures,
        ))
        components.append(ComponentSourceEvidence(
            members=component.members,
            reachable_modules=closure,
            source_signatures=source_signatures,
            evidence_token=token,
            classification=component.classification,
            coverage=component.coverage,
            reason=component.reason,
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

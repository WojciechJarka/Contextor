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

from .contracts import CycleSemanticsSnapshot
from .evidence import (
    SourceBoundCycleEvidence,
    assess_index_bound_scc_models,
    build_source_bound_cycle_evidence,
    _scenario_fingerprint,
)


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

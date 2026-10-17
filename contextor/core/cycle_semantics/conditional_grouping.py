"""Immutable grouping of conditional reexport evidence.

Groups are shared source-order relationships,
not independently observed runtime failures.

Every underlying witness is retained unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from .conditional_discovery import (
    ConditionalDiscoveryReport,
    DiscoveredConditionalReexport,
)


@dataclass(frozen=True)
class ConditionalReexportGroup:
    package_initializer: str
    provider: str
    export_name: str
    package_reexport_line: int
    provider_definition_line: int
    closing_module: str
    closing_line: int
    closing_column: int
    outgoing_import_sites: tuple[
        tuple[int, int, str], ...
    ]
    witness_count: int
    witnesses: tuple[
        DiscoveredConditionalReexport, ...
    ]
    evidence_scope: str = (
        "SHARED_CONDITIONAL_SOURCE_ORDER_RELATIONSHIP"
    )
    runtime_execution_status: str = (
        "UNKNOWN_NOT_EVALUATED"
    )


@dataclass(frozen=True)
class GroupedConditionalReexports:
    groups: tuple[ConditionalReexportGroup, ...]
    group_count: int
    witness_count: int
    examined_outgoing_count: int
    coverage_status: str
    unavailable_source_modules: tuple[str, ...]
    unresolved_lexical_edge_count: int
    source_snapshot_binding: str
    runtime_execution_status: str = (
        "UNKNOWN_NOT_EVALUATED"
    )
    evidence_scope: str = (
        "GROUPED_CONDITIONAL_SOURCE_EVIDENCE_NOT_RUNTIME"
    )


def _validate_witness(
    candidate: DiscoveredConditionalReexport,
) -> None:
    assessment = candidate.assessment
    chain = assessment.chain
    hops = assessment.hops

    if (
        assessment.status
        != "CONDITIONAL_DELAYED_REEXPORT"
        or assessment.evidence_scope
        != "CONDITIONAL_SOURCE_ORDER_ONLY"
        or assessment.prefix_execution_status
        != "UNVERIFIED_TRANSITIVE_PREFIX"
        or assessment.runtime_execution_status
        != "UNKNOWN_NOT_EVALUATED"
        or len(chain) < 4
        or chain[0] != chain[-1]
        or chain[0] != candidate.package_initializer
        or chain[1] != candidate.provider
        or chain[2] != candidate.outgoing_target
        or assessment.export_name
        != candidate.export_name
        or len(hops) != len(chain) - 1
        or any(
            (hop.source_id, hop.target_id)
            != (source, target)
            for hop, (source, target) in zip(
                hops,
                zip(chain, chain[1:]),
            )
        )
        or hops[0].requested_member
        != candidate.export_name
        or hops[-1].requested_member
        != candidate.export_name
        or assessment.package_reexport_line
        != hops[0].line
        or assessment.provider_definition_line is None
        or assessment.provider_definition_line
        <= hops[1].line
    ):
        raise ValueError(
            "inconsistent conditional source witness"
        )


def group_conditional_reexports(
    discovery: ConditionalDiscoveryReport,
) -> GroupedConditionalReexports:
    """Group shared export/lookup evidence without loss.

    This projection performs no source reads,
    graph queries or runtime imports.
    """

    if not isinstance(
        discovery,
        ConditionalDiscoveryReport,
    ):
        raise TypeError(
            "discovery must be ConditionalDiscoveryReport"
        )

    if (
        discovery.runtime_execution_status
        != "UNKNOWN_NOT_EVALUATED"
        or discovery.source_snapshot_binding
        != "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    ):
        raise ValueError(
            "unsupported source/runtime evidence authority"
        )

    buckets: dict[
        tuple[str, str, str, int, int, str, int, int],
        list[DiscoveredConditionalReexport],
    ] = {}

    seen: set[
        tuple[tuple[str, ...], str]
    ] = set()

    for candidate in discovery.candidates:
        if not isinstance(
            candidate,
            DiscoveredConditionalReexport,
        ):
            raise TypeError(
                "invalid discovered witness"
            )

        _validate_witness(candidate)

        assessment = candidate.assessment
        closing = assessment.hops[-1]

        identity = (
            assessment.chain,
            candidate.export_name,
        )

        if identity in seen:
            raise ValueError(
                "duplicate conditional witness"
            )

        seen.add(identity)

        key = (
            candidate.package_initializer,
            candidate.provider,
            candidate.export_name,
            assessment.package_reexport_line,
            assessment.provider_definition_line,
            closing.source_id,
            closing.line,
            closing.column,
        )

        buckets.setdefault(key, []).append(candidate)

    groups = []

    for key in sorted(buckets):
        witnesses = tuple(
            sorted(
                buckets[key],
                key=lambda candidate: (
                    candidate.assessment.hops[1].line,
                    candidate.assessment.hops[1].column,
                    candidate.outgoing_target,
                    candidate.assessment.chain,
                ),
            )
        )

        outgoing_sites = tuple(
            (
                candidate.assessment.hops[1].line,
                candidate.assessment.hops[1].column,
                candidate.outgoing_target,
            )
            for candidate in witnesses
        )

        groups.append(
            ConditionalReexportGroup(
                package_initializer=key[0],
                provider=key[1],
                export_name=key[2],
                package_reexport_line=key[3],
                provider_definition_line=key[4],
                closing_module=key[5],
                closing_line=key[6],
                closing_column=key[7],
                outgoing_import_sites=outgoing_sites,
                witness_count=len(witnesses),
                witnesses=witnesses,
            )
        )

    return GroupedConditionalReexports(
        groups=tuple(groups),
        group_count=len(groups),
        witness_count=len(discovery.candidates),
        examined_outgoing_count=(
            discovery.examined_outgoing_count
        ),
        coverage_status=discovery.coverage_status,
        unavailable_source_modules=(
            discovery.unavailable_source_modules
        ),
        unresolved_lexical_edge_count=(
            discovery.unresolved_lexical_edge_count
        ),
        source_snapshot_binding=(
            discovery.source_snapshot_binding
        ),
    )

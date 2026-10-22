"""Co-publication of prepared SCC manifest claims with durable generations.

Only the canonical snapshot-store writer creates this receipt.
It attests to co-publication of a declaration, NOT provenance
of source bytes or runtime import safety.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import (
    CycleSemanticsSnapshot,
    fingerprint_hard_edges,
)
from .generation_manifest import (
    MANIFEST_VERSION,
    PreparedCycleSourceManifest,
    PreparedSCCSourceBinding,
    _digest,
)
from .scc import analyze_import_cycle_topology


PUBLICATION_BINDING_VERSION = "cycle-prepared-co-publication/1"
PUBLICATION_AUTHORITY = (
    "COMMITTED_PREPARED_CLAIMS_NOT_SOURCE_CERTIFIED"
)
_ALLOWED_MODELS = frozenset((
    "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
    "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
))


@dataclass(frozen=True)
class CanonicalCycleManifestReceipt:
    prepared_manifest: PreparedCycleSourceManifest
    model_claims_sha256: str
    revision: int
    state_id: str
    repo_id: str
    root_path: str
    version: str = PUBLICATION_BINDING_VERSION
    authority: str = PUBLICATION_AUTHORITY


def _validated_claim_digest(
    state: Any,
    manifest: PreparedCycleSourceManifest,
) -> str:
    """Validate declarations, not source-byte authenticity."""
    if type(manifest) is not PreparedCycleSourceManifest:
        raise ValueError("prepared manifest contract missing")
    if (
        manifest.version != MANIFEST_VERSION
        or manifest.authority
        != "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
        or not isinstance(manifest.source_manifest_sha256, str)
        or len(manifest.source_manifest_sha256) != 64
        or any(
            c not in "0123456789abcdef"
            for c in manifest.source_manifest_sha256
        )
    ):
        raise ValueError(
            "prepared manifest is incomplete or unsupported"
        )

    graph = getattr(state, "dependency_graph", None)
    hard_edges = getattr(graph, "hard_edges", None)
    snapshot = getattr(state, "cycle_semantics", None)

    if (
        getattr(state, "resync_required", False) is not False
        or getattr(state, "cycle_semantics_state", None) != "fresh"
        or getattr(state, "cycles_state", None) != "fresh"
        or type(snapshot) is not CycleSemanticsSnapshot
        or snapshot.coverage_status
        != "FILESYSTEM_STABLE_NON_ATOMIC"
        or snapshot.source_issues
        or not isinstance(hard_edges, dict)
    ):
        raise ValueError(
            "canonical cycle evidence is not complete and fresh"
        )

    graph_hash = fingerprint_hard_edges(hard_edges)
    if (
        graph_hash != manifest.graph_sha256
        or graph_hash != snapshot.graph_sha256
    ):
        raise ValueError("canonical graph identity mismatch")

    topology = analyze_import_cycle_topology(hard_edges)
    cyclic = topology.cyclic_components
    if (
        not cyclic
        or type(manifest.components) is not tuple
        or len(manifest.components) != len(cyclic)
    ):
        raise ValueError("prepared SCC coverage incomplete")

    adjacency = {
        source: set(targets)
        for source, targets in hard_edges.items()
    }
    for targets in tuple(adjacency.values()):
        for target in targets:
            adjacency.setdefault(target, set())

    accepted: dict[str, tuple[str, str]] = {}
    claims = []

    for structural, prepared in zip(cyclic, manifest.components):
        if (
            type(prepared) is not PreparedSCCSourceBinding
            or prepared.members != structural.members
            or prepared.preparation_state
            != "PREPARED_UNPUBLISHED"
            or prepared.reason is not None
            or prepared.model_classification not in _ALLOWED_MODELS
            or type(prepared.source_signatures) is not tuple
        ):
            raise ValueError(
                "prepared SCC claims are inconsistent"
            )

        closure = set(structural.members)
        pending = list(structural.members)

        while pending:
            for target in adjacency[pending.pop()]:
                if target not in closure:
                    closure.add(target)
                    pending.append(target)

        rows = prepared.source_signatures
        if (
            len(rows) != len(closure)
            or tuple(
                row[0]
                for row in rows
                if type(row) is tuple and len(row) == 3
            ) != tuple(sorted(closure))
        ):
            raise ValueError(
                "prepared source closure is incomplete"
            )

        for row in rows:
            if type(row) is not tuple or len(row) != 3:
                raise ValueError("invalid source signature")

            name, raw, ast_hash = row
            if any(
                type(digest) is not str
                or len(digest) != 64
                or any(
                    c not in "0123456789abcdef"
                    for c in digest
                )
                for digest in (raw, ast_hash)
            ):
                raise ValueError("invalid source digest")

            signature = (raw, ast_hash)
            if (
                name in accepted
                and accepted[name] != signature
            ):
                raise ValueError(
                    "conflicting shared source digest"
                )
            accepted[name] = signature

        claims.append((
            prepared.members,
            prepared.model_classification,
            rows,
        ))

    observed = dict(snapshot.observed_source_fingerprints)
    cyclic_members = tuple(sorted(
        member
        for component in cyclic
        for member in component.members
    ))

    if (
        snapshot.cyclic_modules != cyclic_members
        or tuple(sorted(observed)) != cyclic_members
        or any(
            accepted[member][0] != observed[member]
            for member in cyclic_members
        )
    ):
        raise ValueError(
            "canonical cyclic source fingerprints mismatch"
        )

    ordered_sources = tuple(
        (name, *accepted[name])
        for name in sorted(accepted)
    )
    expected_manifest_hash = _digest((
        MANIFEST_VERSION,
        graph_hash,
        tuple(component.members for component in cyclic),
        ordered_sources,
    ))
    if manifest.source_manifest_sha256 != expected_manifest_hash:
        raise ValueError(
            "prepared source manifest digest mismatch"
        )

    # Bind model CLAIMS independently of the source digest.
    # This does not authenticate model execution or source origin.
    return _digest((
        PUBLICATION_BINDING_VERSION,
        graph_hash,
        expected_manifest_hash,
        tuple(claims),
    ))


def seal_prepared_cycle_manifest(
    state: Any,
    manifest: PreparedCycleSourceManifest,
    *,
    revision: int,
    state_id: str,
    repo_id: str,
    root_path: str,
) -> CanonicalCycleManifestReceipt:
    """Seal during the snapshot-store commit path only."""
    if (
        type(revision) is not int
        or revision < 1
        or type(state_id) is not str
        or not state_id
    ):
        raise ValueError(
            "invalid publication generation identity"
        )

    if (
        type(repo_id) is not str
        or type(root_path) is not str
    ):
        raise ValueError("invalid repository identity")

    if (
        getattr(state, "revision", None) != revision
        or getattr(state, "state_id", None) != state_id
    ):
        raise ValueError(
            "canonical state and store metadata differ"
        )

    digest = _validated_claim_digest(state, manifest)
    return CanonicalCycleManifestReceipt(
        prepared_manifest=manifest,
        model_claims_sha256=digest,
        revision=revision,
        state_id=state_id,
        repo_id=repo_id,
        root_path=root_path,
    )


def verify_co_published_cycle_manifest(
    state: Any,
    *,
    revision: int,
    state_id: str,
    repo_id: str,
    root_path: str,
) -> bool:
    """Check persisted claim and exact generation identity."""
    receipt = getattr(
        state,
        "cycle_source_publication",
        None,
    )
    if type(receipt) is not CanonicalCycleManifestReceipt:
        return False

    try:
        expected = seal_prepared_cycle_manifest(
            state,
            receipt.prepared_manifest,
            revision=revision,
            state_id=state_id,
            repo_id=repo_id,
            root_path=root_path,
        )
    except (
        TypeError,
        ValueError,
        AttributeError,
        KeyError,
    ):
        return False

    return receipt == expected

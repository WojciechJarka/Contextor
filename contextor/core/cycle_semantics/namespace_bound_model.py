"""Source-bound, conditional PEP 420 cycle-order evidence.

The supplied fingerprints and path inventory remain caller claims.
This module does not authenticate runtime import finder state,
canonical LIVE generations or warning-suppression eligibility.
"""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from contextor.core.source import (
    SourceError,
    SourceSnapshot,
    parse_source_snapshot,
)

from .model_identity import indexed_to_logical_module
from .namespace_path_model import SearchPortion
from .namespace_source_binding import (
    IndexedSourcePath,
    bind_indexed_namespace_resolution,
)
from .package_model import (
    ConditionalNamespaceModelAssessment,
    _conditional_annotation_mode_for_target,
    evaluate_conditional_namespace_import_order,
)


@dataclass(frozen=True)
class SourceBoundConditionalNamespaceAssessment:
    entry_module: str
    outcome: str
    reason: str | None
    source_evidence_sha256: str | None
    conditional_assessment: (
        ConditionalNamespaceModelAssessment | None
    )
    authority: str = (
        "SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_"
        "NOT_RUNTIME_OR_LIVE_PROOF"
    )
    external_import_policy: str = "STOP_AT_UNMODELED"
    class_decorator_policy: str = "STOP_AT_UNMODELED"


def evaluate_source_bound_conditional_namespace_import_order(
    roots: tuple[SearchPortion, ...],
    bindings: tuple[IndexedSourcePath, ...],
    indexed_fingerprints: Mapping[str, str],
    source_snapshots: Mapping[str, SourceSnapshot],
    entry_module: str,
    *,
    standard_finder_assumed: bool = False,
    target_python_version: tuple[int, int] | None = None,
    assume_passive_external_imports: bool = False,
    assume_frozen_dataclass_decoration: bool = False,
) -> SourceBoundConditionalNamespaceAssessment:
    """Parse indexed byte snapshots and conditionally evaluate PEP 420.

    Binding verifies every supplied source against its claimed
    fingerprint before AST parsing. The AST is derived only from
    those bytes, never accepted as independent caller evidence.

    This is not an authenticated index, runtime import environment,
    LIVE generation or permission to suppress a cycle warning.
    """

    external_import_policy = (
        "ASSUME_PASSIVE_EXTERNAL_SUCCESS"
        if assume_passive_external_imports is True
        else "STOP_AT_UNMODELED"
    )
    class_decorator_policy = (
        "ASSUME_PASSIVE_FROZEN_DATACLASS"
        if assume_frozen_dataclass_decoration is True
        else "STOP_AT_UNMODELED"
    )

    def reject(
        reason: str,
        digest: str | None = None,
    ) -> SourceBoundConditionalNamespaceAssessment:
        return SourceBoundConditionalNamespaceAssessment(
            entry_module=entry_module,
            outcome="UNKNOWN",
            reason=reason,
            source_evidence_sha256=digest,
            conditional_assessment=None,
            external_import_policy=external_import_policy,
            class_decorator_policy=class_decorator_policy,
        )

    if type(assume_frozen_dataclass_decoration) is not bool:
        return reject("INVALID_DATACLASS_DECORATOR_ASSUMPTION")
    if (
        assume_frozen_dataclass_decoration
        and not assume_passive_external_imports
    ):
        return reject("DATACLASS_ASSUMPTION_REQUIRES_EXTERNAL_POLICY")

    if type(assume_passive_external_imports) is not bool:
        return reject("INVALID_EXTERNAL_IMPORT_ASSUMPTION")

    if (
        type(entry_module) is not str
        or not entry_module
        or any(
            not part.isidentifier()
            for part in entry_module.split(".")
        )
        or type(standard_finder_assumed) is not bool
    ):
        return reject("INVALID_ENTRY_OR_FINDER_POLICY")

    _, version_error = (
        _conditional_annotation_mode_for_target(
            target_python_version
        )
    )

    if version_error is not None:
        return reject(version_error)

    bound = bind_indexed_namespace_resolution(
        roots,
        bindings,
        indexed_fingerprints,
        source_snapshots,
        entry_module,
        standard_finder_assumed=standard_finder_assumed,
    )

    if bound.status != "SOURCE_BOUND_CONDITIONAL":
        return reject(
            bound.reason or "SOURCE_BINDING_INDETERMINATE"
        )

    digest = bound.evidence_sha256

    if (
        type(digest) is not str
        or len(digest) != 64
    ):
        return reject("SOURCE_BINDING_DIGEST_INVALID")

    entry_candidates = {
        indexed_to_logical_module(module_id)
        for module_id in indexed_fingerprints
    }

    # An artificial namespace initializer is not an indexed
    # physical source and cannot be a source-bound entry.
    if entry_module not in entry_candidates:
        return reject(
            "ENTRY_SOURCE_NOT_INDEXED",
            digest,
        )

    source_paths = {
        row.module_id: row.relative_path
        for row in bindings
    }

    parsed_sources: dict[str, ast.Module] = {}

    for module_id in sorted(indexed_fingerprints):
        snapshot = source_snapshots.get(module_id)
        expected = indexed_fingerprints[module_id]
        path = source_paths.get(module_id)

        if (
            type(snapshot) is not SourceSnapshot
            or type(snapshot.raw) is not bytes
            or type(snapshot.source_fingerprint) is not str
            or snapshot.source_fingerprint != expected
            or hashlib.sha256(snapshot.raw).hexdigest()
            != expected
            or type(path) is not str
        ):
            return reject(
                "SOURCE_CHANGED_AFTER_BINDING",
                digest,
            )

        try:
            parsed = parse_source_snapshot(
                snapshot,
                Path(path),
            )
        except SourceError:
            return reject(
                "SOURCE_PARSE_FAILED:" + module_id,
                digest,
            )

        if not isinstance(parsed.tree, ast.Module):
            return reject(
                "SOURCE_AST_INVALID:" + module_id,
                digest,
            )

        if parsed.source_fingerprint != expected:
            return reject(
                "SOURCE_AST_FINGERPRINT_MISMATCH:"
                + module_id,
                digest,
            )

        parsed_sources[module_id] = parsed.tree

    conditional = evaluate_conditional_namespace_import_order(
        parsed_sources,
        entry_module,
        roots,
        target_python_version=target_python_version,
        assume_passive_external_imports=(
            assume_passive_external_imports
        ),
        assume_frozen_dataclass_decoration=(
            assume_frozen_dataclass_decoration
        ),
    )

    # Never convert CONDITIONAL_MODEL_PASS into MODEL_PASS.
    # The original conditional assessment retains its
    # restricted-model authority and complete event sequence.
    return SourceBoundConditionalNamespaceAssessment(
        entry_module=entry_module,
        outcome=conditional.outcome,
        reason=conditional.reason,
        source_evidence_sha256=digest,
        conditional_assessment=conditional,
        external_import_policy=external_import_policy,
        class_decorator_policy=class_decorator_policy,
    )

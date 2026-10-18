"""Pure canonical contracts for Python cycle semantics.

Evidence is independent from mutable canonical
freshness and LIVE publication state.

These contracts never claim atomic graph/source
binding or runtime execution.

No source I/O, AST parsing, IPC, state mutation
or analyzed-module imports occur here.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .conditional_discovery import (
        ConditionalDiscoveryReport,
    )
    from .edge_sites import CyclicImportSiteReport


CYCLE_SEMANTICS_CONTRACT_VERSION = "1.0.0"

UNVERIFIED_SOURCE_BINDING = (
    "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
)

UNVERIFIED_RUNTIME_EXECUTION = (
    "UNKNOWN_NOT_EVALUATED"
)

SOURCE_COVERAGE_STATES = frozenset({
    "FILESYSTEM_STABLE_NON_ATOMIC",
    "PARTIAL_SOURCE_EVIDENCE",
})

CANONICAL_FRESHNESS_STATES = frozenset({
    "fresh",
    "stale",
    "deferred",
})


def _is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(
            character in "0123456789abcdef"
            for character in value
        )
    )


def _require_deep_immutable(
    value: object,
    *,
    path: str,
    active: set[int] | None = None,
) -> None:
    """Reject mutable or unsupported nested evidence.

    Approved evidence consists of scalar primitives,
    immutable collections and frozen dataclass values.

    The recursion guard rejects malformed cyclic object
    structures rather than traversing indefinitely.
    """

    if type(value) in (
        str,
        bytes,
        int,
        float,
        bool,
        type(None),
    ):
        return

    if active is None:
        active = set()

    identity = id(value)

    if identity in active:
        raise TypeError(
            f"{path} contains a recursive object"
        )

    active.add(identity)

    try:
        if type(value) in (tuple, frozenset):
            for member in value:
                _require_deep_immutable(
                    member,
                    path=path,
                    active=active,
                )
            return

        if (
            is_dataclass(value)
            and not isinstance(value, type)
            and getattr(
                type(value),
                "__dataclass_params__",
                None,
            ) is not None
            and type(value).__dataclass_params__.frozen
        ):
            for item in fields(value):
                _require_deep_immutable(
                    getattr(value, item.name),
                    path=f"{path}.{item.name}",
                    active=active,
                )
            return

        raise TypeError(
            f"{path} contains mutable or unsupported evidence"
        )

    finally:
        active.remove(identity)


def fingerprint_hard_edges(
    hard_edges: Mapping[str, object],
) -> str:
    """Fingerprint the complete supplied hard graph.

    The digest identifies graph content only.
    It does not certify a canonical generation,
    LIVE revision, or source-binding transaction.
    """

    if not isinstance(hard_edges, Mapping):
        raise TypeError(
            "hard_edges must be a mapping"
        )

    normalized = []

    for source, raw_targets in hard_edges.items():
        if type(source) is not str or not source:
            raise ValueError(
                "Invalid hard-edge source identity"
            )

        if not isinstance(
            raw_targets,
            (tuple, list, set, frozenset),
        ):
            raise TypeError(
                "Hard-edge targets must be a collection"
            )

        targets = set()

        for target in raw_targets:
            if type(target) is not str or not target:
                raise ValueError(
                    "Invalid hard-edge target identity"
                )

            targets.add(target)

        normalized.append((
            source,
            tuple(sorted(targets)),
        ))

    encoded = json.dumps(
        sorted(normalized),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CycleSemanticsSnapshot:
    """Immutable semantic evidence from one materialization.

    The lexical and conditional reports contain
    structured source evidence, not parsed AST
    objects or executable repository modules.

    Freshness and published revision are purposely
    NOT fields of this contract.

    A future canonical family lifecycle owns those
    properties independently.
    """

    graph_sha256: str

    cyclic_modules: tuple[str, ...]

    observed_source_fingerprints: tuple[
        tuple[str, str], ...
    ]

    source_issues: tuple[
        tuple[str, str], ...
    ]

    coverage_status: str
    source_snapshot_binding: str
    runtime_execution_status: str

    import_sites: CyclicImportSiteReport
    conditional_discovery: ConditionalDiscoveryReport

    schema_version: str = (
        CYCLE_SEMANTICS_CONTRACT_VERSION
    )

    def __post_init__(self) -> None:
        if self.schema_version != (
            CYCLE_SEMANTICS_CONTRACT_VERSION
        ):
            raise ValueError(
                "Unsupported cycle semantics contract version"
            )

        if not _is_sha256(self.graph_sha256):
            raise ValueError(
                "Invalid graph SHA-256 fingerprint"
            )

        if (
            type(self.cyclic_modules) is not tuple
            or any(
                type(module) is not str or not module
                for module in self.cyclic_modules
            )
            or self.cyclic_modules
            != tuple(sorted(set(self.cyclic_modules)))
        ):
            raise ValueError(
                "Cyclic module identities must be sorted and unique"
            )

        fingerprints = self.observed_source_fingerprints

        if type(fingerprints) is not tuple:
            raise TypeError(
                "Source fingerprints must be an immutable tuple"
            )

        for item in fingerprints:
            if (
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or not item[0]
                or not _is_sha256(item[1])
            ):
                raise ValueError(
                    "Invalid observed source fingerprint"
                )

        if fingerprints != tuple(sorted(fingerprints)):
            raise ValueError(
                "Source fingerprints must be sorted"
            )

        fingerprint_modules = tuple(
            module for module, _ in fingerprints
        )

        if len(set(fingerprint_modules)) != (
            len(fingerprint_modules)
        ):
            raise ValueError(
                "Duplicate source fingerprint identity"
            )

        if not set(fingerprint_modules).issubset(
            self.cyclic_modules
        ):
            raise ValueError(
                "Source fingerprint outside cyclic cohort"
            )

        issues = self.source_issues

        if (
            type(issues) is not tuple
            or any(
                type(item) is not tuple
                or len(item) != 2
                or any(
                    type(value) is not str or not value
                    for value in item
                )
                for item in issues
            )
            or issues != tuple(sorted(set(issues)))
        ):
            raise ValueError(
                "Source issues must be immutable, sorted and unique"
            )

        if any(
            module not in self.cyclic_modules
            for module, _ in issues
        ):
            raise ValueError(
                "Source issue outside cyclic cohort"
            )

        if self.coverage_status not in (
            SOURCE_COVERAGE_STATES
        ):
            raise ValueError(
                "Invalid source coverage status"
            )

        if self.coverage_status == (
            "FILESYSTEM_STABLE_NON_ATOMIC"
        ):
            if (
                issues
                or fingerprint_modules
                != self.cyclic_modules
            ):
                raise ValueError(
                    "Complete source coverage requires every cyclic source"
                )

        if self.source_snapshot_binding != (
            UNVERIFIED_SOURCE_BINDING
        ):
            raise ValueError(
                "Unsupported source binding claim"
            )

        if self.runtime_execution_status != (
            UNVERIFIED_RUNTIME_EXECUTION
        ):
            raise ValueError(
                "Unsupported runtime execution claim"
            )

        from .conditional_discovery import (
            ConditionalDiscoveryReport,
        )
        from .edge_sites import CyclicImportSiteReport

        if type(self.import_sites) is not (
            CyclicImportSiteReport
        ):
            raise TypeError(
                "import_sites must be CyclicImportSiteReport"
            )

        if type(self.conditional_discovery) is not (
            ConditionalDiscoveryReport
        ):
            raise TypeError(
                "conditional_discovery must be ConditionalDiscoveryReport"
            )

        _require_deep_immutable(
            self.import_sites,
            path="import_sites",
        )
        _require_deep_immutable(
            self.conditional_discovery,
            path="conditional_discovery",
        )

        components = (
            self.import_sites.topology.cyclic_components
        )

        topology_members = tuple(sorted(
            module
            for component in components
            for module in component.members
        ))

        if topology_members != self.cyclic_modules:
            raise ValueError(
                "Import-site topology and cyclic cohort differ"
            )

        site_components = self.import_sites.components

        if (
            len(site_components) != len(components)
            or any(
                site.members != component.members
                for site, component in zip(
                    site_components,
                    components,
                )
            )
        ):
            raise ValueError(
                "Import-site components and topology differ"
            )

    @property
    def observed_source_count(self) -> int:
        return len(self.observed_source_fingerprints)

    @property
    def cyclic_module_count(self) -> int:
        return len(self.cyclic_modules)

    @property
    def unobserved_source_count(self) -> int:
        return (
            self.cyclic_module_count
            - self.observed_source_count
        )

"""Bind supplied namespace inventories to indexed source byte snapshots.

This is conditional caller-supplied evidence only. It does not
authenticate runtime import resolution, filesystem completeness,
canonical LIVE generations, or cycle-warning suppression.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from contextor.core.source import SourceSnapshot

from .namespace_path_model import (
    NamespacePathResult,
    SearchPortion,
    resolve_namespace_path,
)


_MAX_SOURCES = 256
_MAX_SOURCE_BYTES = 2 * 1024 * 1024
_MAX_TOTAL_BYTES = 32 * 1024 * 1024
_MAX_INVENTORY_FILES = 16384

_AUTHORITY = (
    "CALLER_SUPPLIED_INDEXED_SOURCE_BYTES_"
    "NOT_RUNTIME_OR_LIVE_CERTIFIED"
)

_VERSION = "namespace-conditional-source-binding/1"


@dataclass(frozen=True)
class IndexedSourcePath:
    module_id: str
    root_id: str
    relative_path: str


@dataclass(frozen=True)
class BoundNamespaceResolution:
    status: str
    reason: str | None
    requested_name: str
    resolution: NamespacePathResult | None
    selected_sources: tuple[tuple[str, str, str], ...]
    evidence_sha256: str | None
    authority: str = _AUTHORITY
    version: str = _VERSION


def bind_indexed_namespace_resolution(
    roots: tuple[SearchPortion, ...],
    bindings: tuple[IndexedSourcePath, ...],
    indexed_fingerprints: Mapping[str, str],
    source_snapshots: Mapping[str, SourceSnapshot],
    requested_name: str,
    *,
    standard_finder_assumed: bool = False,
) -> BoundNamespaceResolution:
    """Verify supplied source identities and conditional path selection.

    No file reads, imports of analyzed modules, LIVE IPC or publication.
    An inventory hash describes supplied input; it is not a trusted
    signature or proof of actual interpreter search paths.
    """
    resolution = resolve_namespace_path(
        roots,
        requested_name,
        standard_finder_assumed=standard_finder_assumed,
    )

    def reject(reason: str) -> BoundNamespaceResolution:
        return BoundNamespaceResolution(
            "INDETERMINATE",
            reason,
            requested_name,
            resolution,
            (),
            None,
        )

    if resolution.status != "CONDITIONAL":
        return reject(
            resolution.reason or "PATH_RESOLUTION_INDETERMINATE"
        )

    if (
        type(bindings) is not tuple
        or not bindings
        or len(bindings) > _MAX_SOURCES
        or not isinstance(indexed_fingerprints, Mapping)
        or not isinstance(source_snapshots, Mapping)
    ):
        return reject("SOURCE_BINDING_INPUT_INVALID")

    if (
        sum(len(root.files) for root in roots)
        > _MAX_INVENTORY_FILES
    ):
        return reject("INVENTORY_FILE_LIMIT")

    root_by_id = {}

    for root in roots:
        if (
            not root.root_id.isidentifier()
            or root.root_id in root_by_id
        ):
            return reject("ROOT_ID_INVALID")

        root_by_id[root.root_id] = root

    module_to_binding = {}
    path_to_binding = {}

    for binding in bindings:
        if type(binding) is not IndexedSourcePath:
            return reject("SOURCE_BINDING_SHAPE_INVALID")

        module_id = binding.module_id

        if (
            type(module_id) is not str
            or not module_id
            or any(
                not segment.isidentifier()
                for segment in module_id.split(".")
            )
            or type(binding.root_id) is not str
            or binding.root_id not in root_by_id
            or type(binding.relative_path) is not str
        ):
            return reject("SOURCE_BINDING_IDENTITY_INVALID")

        expected_path = module_id.replace(".", "/") + ".py"

        if binding.relative_path != expected_path:
            return reject("SOURCE_MODULE_PATH_MISMATCH")

        if binding.relative_path not in (
            root_by_id[binding.root_id].files
        ):
            return reject("SOURCE_PATH_NOT_IN_INVENTORY")

        source_key = (
            binding.root_id + ":" + binding.relative_path
        )

        if (
            module_id in module_to_binding
            or source_key in path_to_binding
        ):
            return reject("DUPLICATE_SOURCE_BINDING")

        module_to_binding[module_id] = binding
        path_to_binding[source_key] = binding

    required_ids = set(module_to_binding)

    if (
        set(indexed_fingerprints) != required_ids
        or set(source_snapshots) != required_ids
    ):
        return reject("SOURCE_INDEX_DOMAIN_MISMATCH")

    # Every supplied .py entry must be represented by a source
    # identity. This proves only completeness relative to the
    # supplied inventory, never completeness of actual sys.path.
    inventory_python_files = {
        root.root_id + ":" + filename
        for root in roots
        for filename in root.files
        if filename.endswith(".py")
    }

    if inventory_python_files != set(path_to_binding):
        return reject("INVENTORY_SOURCE_BINDING_MISMATCH")

    signatures = {}
    retained_bytes = 0

    for module_id in sorted(required_ids):
        snapshot = source_snapshots[module_id]
        claimed_sha = indexed_fingerprints[module_id]

        if (
            type(snapshot) is not SourceSnapshot
            or type(snapshot.raw) is not bytes
            or type(snapshot.source_fingerprint) is not str
            or type(claimed_sha) is not str
            or len(claimed_sha) != 64
            or any(
                character not in "0123456789abcdef"
                for character in claimed_sha
            )
        ):
            return reject("SOURCE_SNAPSHOT_SHAPE_INVALID")

        if len(snapshot.raw) > _MAX_SOURCE_BYTES:
            return reject("SOURCE_BYTE_LIMIT")

        retained_bytes += len(snapshot.raw)

        if retained_bytes > _MAX_TOTAL_BYTES:
            return reject("SOURCE_TOTAL_BYTE_LIMIT")

        actual_sha = hashlib.sha256(snapshot.raw).hexdigest()

        if (
            actual_sha != claimed_sha
            or snapshot.source_fingerprint != claimed_sha
        ):
            return reject("SOURCE_FINGERPRINT_MISMATCH")

        signatures[module_id] = actual_sha

    selected = []

    for step in resolution.steps:
        if step.kind == "NAMESPACE_PACKAGE":
            continue

        if (
            step.kind not in {"REGULAR_PACKAGE", "MODULE_FILE"}
            or type(step.source) is not str
        ):
            return reject("UNSUPPORTED_SELECTED_SOURCE_KIND")

        binding = path_to_binding.get(step.source)

        if binding is None:
            return reject("SELECTED_SOURCE_NOT_INDEXED")

        expected_module = (
            step.name + ".__init__"
            if step.kind == "REGULAR_PACKAGE"
            else step.name
        )

        if binding.module_id != expected_module:
            return reject("SELECTED_MODULE_IDENTITY_MISMATCH")

        selected.append((
            binding.module_id,
            step.source,
            signatures[binding.module_id],
        ))

    # Canonical serialization of caller-supplied information only.
    # This digest does not authenticate where that information
    # originated or whether files outside the inventory exist.
    digest_input = (
        _VERSION,
        requested_name,
        tuple(
            (
                root.root_id,
                tuple(sorted(root.files)),
            )
            for root in roots
        ),
        tuple(
            sorted(
                (
                    binding.module_id,
                    binding.root_id,
                    binding.relative_path,
                    signatures[binding.module_id],
                )
                for binding in bindings
            )
        ),
        tuple(
            (
                step.name,
                step.kind,
                step.source,
                step.portions,
            )
            for step in resolution.steps
        ),
    )

    encoded = json.dumps(
        digest_input,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return BoundNamespaceResolution(
        "SOURCE_BOUND_CONDITIONAL",
        None,
        requested_name,
        resolution,
        tuple(selected),
        hashlib.sha256(encoded).hexdigest(),
    )

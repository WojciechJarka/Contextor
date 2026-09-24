"""Atomic, revisioned snapshot store shared by desktop and MCP processes."""

from __future__ import annotations

import copy
import json
import os
import pickle
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from contextor.core.domain.lineage_facts import (
    LINEAGE_FACTS_SEMANTIC_VERSION,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    MaterializedAnchorFact,
    MaterializedFlowFact,
    MaterializedLineageSourceFacts,
    MaterializedOccurrenceRef,
    MaterializedSymbolicRef,
    MaterializedSurfaceFact,
    ProviderRef,
    ResolutionKind,
    SemanticAnchorBinding,
    SemanticEndpoint,
    SemanticEndpointOrigin,
    SemanticEndpointRole,
    SemanticInterfaceDescriptor,
    SourceLineageManifest,
    SourceSpan,
    SurfaceKind,
)

LIVE_STATE_SCHEMA_VERSION = "1.3"
LINEAGE_MANIFEST_SCHEMA_VERSION = "1.0"


class _LegacySymbolCallFact:
    """Unpickle-only shape used by a transient pre-tuple snapshot format."""


class _SnapshotUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str):
        if (
            module == "contextor.core.domain.usage_facts"
            and name == "SymbolCallFact"
        ):
            return _LegacySymbolCallFact
        return super().find_class(module, name)


def _normalize_symbol_call_facts(state: Any) -> Any:
    """Replace legacy call objects with the current primitive tuple contract."""

    if state is None or not hasattr(state, "module_usages"):
        return state
    from contextor.core.domain.usage_facts import ModuleUsageFacts

    module_usages = getattr(state, "module_usages", None)
    if not isinstance(module_usages, dict):
        return state
    normalized_usages = dict(module_usages)
    for module_name, facts in module_usages.items():
        if not isinstance(facts, ModuleUsageFacts):
            continue
        normalized_calls = []
        for item in getattr(facts, "symbol_calls", ()):
            if isinstance(item, _LegacySymbolCallFact):
                values = vars(item)
                try:
                    normalized_calls.append(
                        (
                            str(values["caller"]),
                            str(values["callee"]),
                            int(values["line"]),
                            str(values.get("call_kind", "direct")),
                        )
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise pickle.UnpicklingError(
                        "Invalid legacy SymbolCallFact state."
                    ) from exc
            elif isinstance(item, (tuple, list)) and len(item) in {3, 4}:
                try:
                    normalized_calls.append(
                        (
                            str(item[0]),
                            str(item[1]),
                            int(item[2]),
                            str(item[3]) if len(item) == 4 else "direct",
                        )
                    )
                except (TypeError, ValueError) as exc:
                    raise pickle.UnpicklingError(
                        "Invalid primitive symbol call fact."
                    ) from exc
            else:
                raise pickle.UnpicklingError("Unknown symbol call fact shape.")
        normalized_usages[module_name] = replace(
            facts,
            symbol_calls=tuple(sorted(set(normalized_calls))),
            symbol_calls_materialized=bool(
                vars(facts).get("symbol_calls_materialized", False)
            ),
        )
    state.module_usages = normalized_usages
    return state


def _revalidate_lineage_span(span: Any) -> SourceSpan:
    if not isinstance(span, SourceSpan):
        raise pickle.UnpicklingError("Invalid lineage SourceSpan.")
    return replace(span)


def _revalidate_lineage_endpoint(
    endpoint: Any,
) -> MaterializedOccurrenceRef | SemanticEndpoint:
    if isinstance(endpoint, MaterializedOccurrenceRef):
        return replace(endpoint)
    if isinstance(endpoint, SemanticEndpoint):
        return replace(endpoint)
    if isinstance(endpoint, MaterializedSymbolicRef):
        return replace(endpoint)
    raise pickle.UnpicklingError("Unknown materialized lineage endpoint.")


def _revalidate_lineage_provider(provider: Any) -> ProviderRef | None:
    if provider is None:
        return None
    if not isinstance(provider, ProviderRef):
        raise pickle.UnpicklingError("Invalid lineage provider.")
    return replace(provider)


def _revalidate_lineage_manifest(manifest: Any) -> SourceLineageManifest:
    if not isinstance(manifest, SourceLineageManifest):
        raise pickle.UnpicklingError("Invalid lineage source manifest.")
    if not isinstance(manifest.status, LineageFamilyStatus):
        raise pickle.UnpicklingError("Invalid lineage manifest status.")
    rebuilt = replace(
        manifest,
        semantic_anchor_bindings_materialized=bool(
            getattr(
                manifest,
                "semantic_anchor_bindings_materialized",
                False,
            )
        ),
        anchor_ownership_materialized=bool(
            getattr(
                manifest,
                "anchor_ownership_materialized",
                False,
            )
        ),
        flow_ownership_materialized=bool(
            getattr(
                manifest,
                "flow_ownership_materialized",
                False,
            )
        ),
        interface_descriptors_materialized=bool(
            getattr(manifest, "interface_descriptors_materialized", False)
        ),
    )
    if rebuilt.semantic_version != LINEAGE_FACTS_SEMANTIC_VERSION:
        raise pickle.UnpicklingError(
            "Unsupported lineage manifest semantic version."
        )
    return rebuilt


def _revalidate_lineage_anchor(anchor: Any) -> MaterializedAnchorFact:
    if not isinstance(anchor, MaterializedAnchorFact):
        raise pickle.UnpicklingError("Invalid materialized lineage anchor.")
    return replace(
        anchor,
        reference=_revalidate_lineage_endpoint(anchor.reference),
        span=_revalidate_lineage_span(anchor.span),
        owner_local_id=getattr(anchor, "owner_local_id", None),
    )


def _revalidate_lineage_flow(flow: Any) -> MaterializedFlowFact:
    if not isinstance(flow, MaterializedFlowFact):
        raise pickle.UnpicklingError("Invalid materialized lineage flow.")
    if not isinstance(flow.relation, LineageRelation):
        raise pickle.UnpicklingError("Invalid lineage relation.")
    if not isinstance(flow.resolution_kind, ResolutionKind):
        raise pickle.UnpicklingError("Invalid lineage resolution kind.")
    if not isinstance(flow.confidence, LineageConfidence):
        raise pickle.UnpicklingError("Invalid lineage confidence.")
    return replace(
        flow,
        source=_revalidate_lineage_endpoint(flow.source),
        target=_revalidate_lineage_endpoint(flow.target),
        evidence=_revalidate_lineage_span(flow.evidence),
        provider=_revalidate_lineage_provider(flow.provider),
        owner_local_id=getattr(flow, "owner_local_id", None),
    )


def _revalidate_lineage_surface(surface: Any) -> MaterializedSurfaceFact:
    if not isinstance(surface, MaterializedSurfaceFact):
        raise pickle.UnpicklingError("Invalid materialized lineage surface.")
    if not isinstance(surface.kind, SurfaceKind):
        raise pickle.UnpicklingError("Invalid lineage surface kind.")
    if not isinstance(surface.resolution_kind, ResolutionKind):
        raise pickle.UnpicklingError("Invalid lineage surface resolution kind.")
    if not isinstance(surface.confidence, LineageConfidence):
        raise pickle.UnpicklingError("Invalid lineage surface confidence.")
    return replace(
        surface,
        exposed=_revalidate_lineage_endpoint(surface.exposed),
        evidence=_revalidate_lineage_span(surface.evidence),
        provider=_revalidate_lineage_provider(surface.provider),
    )


def _revalidate_lineage_descriptor(
    descriptor: Any,
) -> SemanticInterfaceDescriptor:
    if not isinstance(descriptor, SemanticInterfaceDescriptor):
        raise pickle.UnpicklingError(
            "Invalid lineage semantic interface descriptor."
        )
    return replace(descriptor)


def _revalidate_lineage_origin(origin: Any) -> SemanticEndpointOrigin:
    if not isinstance(origin, SemanticEndpointOrigin):
        raise pickle.UnpicklingError("Invalid lineage semantic endpoint origin.")
    if not isinstance(origin.endpoint_role, SemanticEndpointRole):
        raise pickle.UnpicklingError("Invalid lineage semantic endpoint origin role.")
    return replace(origin)


def _revalidate_lineage_semantic_anchor(
    binding: Any,
) -> SemanticAnchorBinding:
    if not isinstance(binding, SemanticAnchorBinding):
        raise pickle.UnpicklingError(
            "Invalid lineage semantic anchor binding."
        )
    return replace(
        binding,
        reference=_revalidate_lineage_endpoint(binding.reference),
    )


def _revalidate_lineage_slice(
    source_slice: Any,
) -> MaterializedLineageSourceFacts:
    if not isinstance(source_slice, MaterializedLineageSourceFacts):
        raise pickle.UnpicklingError(
            "Invalid materialized lineage source slice."
        )
    return replace(
        source_slice,
        manifest=_revalidate_lineage_manifest(source_slice.manifest),
        anchors=tuple(
            _revalidate_lineage_anchor(item)
            for item in source_slice.anchors
        ),
        flows=tuple(
            _revalidate_lineage_flow(item)
            for item in source_slice.flows
        ),
        surfaces=tuple(
            _revalidate_lineage_surface(item)
            for item in source_slice.surfaces
        ),
        interface_descriptors=tuple(
            _revalidate_lineage_descriptor(item)
            for item in source_slice.interface_descriptors
        ),
        semantic_endpoint_origins=tuple(
            _revalidate_lineage_origin(item)
            for item in getattr(source_slice, "semantic_endpoint_origins", ())
        ),
        semantic_anchors=tuple(
            _revalidate_lineage_semantic_anchor(item)
            for item in getattr(source_slice, "semantic_anchors", ())
        ),
    )


def _normalize_lineage_facts_state(state: Any) -> Any:
    """Normalize/validate persisted materialized lineage without source work."""

    if state is None or isinstance(state, dict) or not hasattr(state, "__dict__"):
        return state

    try:
        if not hasattr(state, "lineage_facts_by_source"):
            state.lineage_facts_by_source = {}
        if hasattr(state, "lineage_extracted_facts_by_source"):
            delattr(state, "lineage_extracted_facts_by_source")
        if not hasattr(state, "lineage_facts_state"):
            state.lineage_facts_state = "not_materialized"
        if not hasattr(state, "lineage_facts_semantic_version"):
            state.lineage_facts_semantic_version = None

        raw_mapping = state.lineage_facts_by_source
        raw_family_state = state.lineage_facts_state
        raw_version = state.lineage_facts_semantic_version

        if not isinstance(raw_mapping, dict):
            raise pickle.UnpicklingError(
                "Lineage source mapping must be a dict."
            )
        if not isinstance(raw_family_state, str):
            raise pickle.UnpicklingError(
                "Lineage family state must be a string."
            )

        try:
            family_status = LineageFamilyStatus(raw_family_state)
        except ValueError as exc:
            raise pickle.UnpicklingError(
                "Unknown lineage family state."
            ) from exc

        if raw_version is not None and raw_version != LINEAGE_FACTS_SEMANTIC_VERSION:
            raise pickle.UnpicklingError(
                "Unsupported lineage semantic version."
            )

        if family_status is LineageFamilyStatus.NOT_MATERIALIZED:
            if raw_mapping:
                raise pickle.UnpicklingError(
                    "Not-materialized lineage cannot contain source slices."
                )
            if raw_version is not None:
                raise pickle.UnpicklingError(
                    "Not-materialized lineage cannot have a semantic version."
                )
        elif raw_version != LINEAGE_FACTS_SEMANTIC_VERSION:
            raise pickle.UnpicklingError(
                "Materialized lineage requires the current semantic version."
            )

        normalized: dict[str, MaterializedLineageSourceFacts] = {}
        for source_key, source_slice in raw_mapping.items():
            if not isinstance(source_key, str) or not source_key:
                raise pickle.UnpicklingError(
                    "Lineage source key must be a non-empty string."
                )
            rebuilt = _revalidate_lineage_slice(source_slice)
            if rebuilt.manifest.source_key != source_key:
                raise pickle.UnpicklingError(
                    "Lineage mapping key does not match manifest source_key."
                )
            normalized[source_key] = rebuilt

        state.lineage_facts_by_source = normalized
        state.lineage_facts_state = family_status.value
        state.lineage_facts_semantic_version = raw_version
        return state

    except pickle.UnpicklingError:
        raise
    except (AttributeError, TypeError, ValueError) as exc:
        raise pickle.UnpicklingError(
            "Invalid persisted lineage state."
        ) from exc


def _normalize_lineage_query_index_state(state: Any) -> Any:
    """Rebuild the derived index during hydration, never during a query."""
    if state is None or isinstance(state, dict) or not hasattr(state, "__dict__"):
        return state
    from contextor.core.lineage_query.index import build_lineage_query_indexes

    family_state = getattr(state, "lineage_facts_state", "not_materialized")
    sources = getattr(state, "lineage_facts_by_source", {}) or {}
    if family_state == "not_materialized":
        state.lineage_owner_source_index = {}
        state.lineage_source_owner_index = {}
        state.lineage_query_index_state = "not_materialized"
        state.lineage_semantic_anchor_bindings_complete = False
        return state
    try:
        (
            state.lineage_owner_source_index,
            state.lineage_source_owner_index,
            state.lineage_semantic_anchor_bindings_complete,
        ) = build_lineage_query_indexes(sources)
    except (TypeError, ValueError) as exc:
        raise pickle.UnpicklingError(
            "Invalid canonical lineage query index inputs."
        ) from exc
    state.lineage_query_index_state = "fresh"
    return state


@dataclass(frozen=True)
class LiveStateMetadata:
    schema_version: str = LIVE_STATE_SCHEMA_VERSION
    state_id: str = ""
    revision: int = 0
    writer: str = "unknown"
    repo_id: str = ""
    root_path: str = ""
    state_file: str = ""
    file_state_file: str = ""
    lineage_manifest_file: str = ""


def _supports_split_lineage_generation(state: Any) -> bool:
    return (
        state is not None
        and not isinstance(state, dict)
        and hasattr(state, "__dict__")
        and isinstance(
            getattr(
                state,
                "lineage_facts_by_source",
                None,
            ),
            dict,
        )
    )


def _snapshot_child_path(
    cache_dir: str | Path,
    file_name: str,
    *,
    label: str,
) -> Path:
    if not isinstance(file_name, str) or not file_name:
        raise pickle.UnpicklingError(
            f"{label} file name must be non-empty."
        )

    candidate = Path(file_name)

    if (
        candidate.is_absolute()
        or candidate.name != file_name
    ):
        raise pickle.UnpicklingError(
            f"{label} file name must be a cache-local basename."
        )

    return Path(cache_dir) / candidate


def _write_split_lineage_generation(
    state: Any,
    manifest_path: Path,
    *,
    state_id: str,
    revision: int,
    token: str,
    previous_state: Any = None,
    reusable_sources: dict[str, Any] | None = None,
) -> tuple[Any, list[Path]]:
    sources = getattr(
        state,
        "lineage_facts_by_source",
    )

    if not isinstance(sources, dict):
        raise ValueError(
            "lineage_facts_by_source must be a dict."
        )

    if any(
        not isinstance(source_key, str)
        or not source_key
        for source_key in sources
    ):
        raise ValueError(
            "Lineage source keys must be non-empty strings."
        )

    previous_sources = (
        getattr(
            previous_state,
            "lineage_facts_by_source",
            {},
        )
        if _supports_split_lineage_generation(
            previous_state
        )
        else {}
    )

    if not isinstance(
        previous_sources,
        dict,
    ):
        previous_sources = {}

    if not isinstance(
        reusable_sources,
        dict,
    ):
        reusable_sources = {}

    created_chunks: list[Path] = []
    manifest_sources: dict[
        str,
        dict[str, str],
    ] = {}

    try:
        for index, source_key in enumerate(
            sorted(sources)
        ):
            source_slice = sources[source_key]

            if not isinstance(
                source_slice,
                MaterializedLineageSourceFacts,
            ):
                raise ValueError(
                    "Lineage source value has invalid type."
                )

            if (
                source_slice.manifest.source_key
                != source_key
            ):
                raise ValueError(
                    "Lineage mapping key does not match source manifest."
                )

            previous_slice = previous_sources.get(
                source_key
            )

            reusable_entry = reusable_sources.get(
                source_key
            )

            if (
                previous_slice is source_slice
                and isinstance(
                    reusable_entry,
                    dict,
                )
            ):
                reusable_file = reusable_entry.get(
                    "file"
                )
                reusable_fingerprint = reusable_entry.get(
                    "source_fingerprint"
                )
                reusable_semantic_version = reusable_entry.get(
                    "semantic_version"
                )

                if (
                    isinstance(
                        reusable_file,
                        str,
                    )
                    and reusable_file
                    and reusable_fingerprint
                    == source_slice.manifest.source_fingerprint
                    and reusable_semantic_version
                    == source_slice.manifest.semantic_version
                ):
                    try:
                        reusable_path = _snapshot_child_path(
                            manifest_path.parent,
                            reusable_file,
                            label="Lineage chunk",
                        )
                    except pickle.UnpicklingError:
                        reusable_path = None

                    if (
                        reusable_path is not None
                        and reusable_path.is_file()
                    ):
                        manifest_sources[
                            source_key
                        ] = {
                            "file": reusable_file,
                            "source_fingerprint": (
                                source_slice.manifest.source_fingerprint
                            ),
                            "semantic_version": (
                                source_slice.manifest.semantic_version
                            ),
                        }

                        continue

            chunk_path = (
                manifest_path.parent
                / (
                    f"lineage_source.r{revision}."
                    f"{token}.{index:05d}.pkl"
                )
            )

            created_chunks.append(
                chunk_path
            )

            with chunk_path.open(
                "wb"
            ) as stream:
                pickle.dump(
                    source_slice,
                    stream,
                )
                stream.flush()
                os.fsync(
                    stream.fileno()
                )

            manifest_sources[
                source_key
            ] = {
                "file": chunk_path.name,
                "source_fingerprint": (
                    source_slice.manifest.source_fingerprint
                ),
                "semantic_version": (
                    source_slice.manifest.semantic_version
                ),
            }

        manifest_payload = {
            "schema_version": (
                LINEAGE_MANIFEST_SCHEMA_VERSION
            ),
            "state_id": state_id,
            "revision": revision,
            "sources": manifest_sources,
        }

        with manifest_path.open(
            "w",
            encoding="utf-8",
        ) as stream:
            json.dump(
                manifest_payload,
                stream,
                indent=2,
                sort_keys=True,
            )
            stream.flush()
            os.fsync(
                stream.fileno()
            )

        core_state = copy.copy(
            state
        )
        core_state.lineage_facts_by_source = {}

        return (
            core_state,
            created_chunks,
        )

    except Exception:
        for generated_path in [
            *created_chunks,
            manifest_path,
        ]:
            try:
                generated_path.unlink()
            except OSError:
                pass

        raise


def _read_split_lineage_manifest(
    cache_dir: str | Path,
    metadata: LiveStateMetadata,
) -> dict[str, Any]:
    manifest_path = _snapshot_child_path(
        cache_dir,
        metadata.lineage_manifest_file,
        label="Lineage manifest",
    )

    try:
        payload = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as exc:
        raise pickle.UnpicklingError(
            "Invalid lineage manifest."
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise pickle.UnpicklingError(
            "Lineage manifest must be a mapping."
        )

    if (
        payload.get(
            "schema_version"
        )
        != LINEAGE_MANIFEST_SCHEMA_VERSION
    ):
        raise pickle.UnpicklingError(
            "Unsupported lineage manifest schema."
        )

    if (
        payload.get(
            "state_id"
        )
        != metadata.state_id
    ):
        raise pickle.UnpicklingError(
            "Lineage manifest state_id mismatch."
        )

    if (
        payload.get(
            "revision"
        )
        != metadata.revision
    ):
        raise pickle.UnpicklingError(
            "Lineage manifest revision mismatch."
        )

    sources = payload.get(
        "sources"
    )

    if not isinstance(
        sources,
        dict,
    ):
        raise pickle.UnpicklingError(
            "Lineage manifest sources must be a mapping."
        )

    return payload


def _reusable_lineage_manifest_sources(
    cache_dir: str | Path,
    current: LiveStateMetadata | None,
    previous_state: Any,
) -> dict[str, Any]:
    if (
        current is None
        or current.schema_version != LIVE_STATE_SCHEMA_VERSION
        or not current.lineage_manifest_file
        or not _supports_split_lineage_generation(
            previous_state
        )
    ):
        return {}

    if (
        getattr(
            previous_state,
            "revision",
            None,
        )
        != current.revision
    ):
        return {}

    if (
        getattr(
            previous_state,
            "state_id",
            None,
        )
        != current.state_id
    ):
        return {}

    try:
        payload = _read_split_lineage_manifest(
            cache_dir,
            current,
        )
    except pickle.UnpicklingError:
        return {}

    sources = payload.get(
        "sources"
    )

    if not isinstance(
        sources,
        dict,
    ):
        return {}

    return sources


def _load_split_lineage_generation(
    cache_dir: str | Path,
    metadata: LiveStateMetadata,
) -> dict[
    str,
    MaterializedLineageSourceFacts,
]:
    payload = _read_split_lineage_manifest(
        cache_dir,
        metadata,
    )

    raw_sources = payload[
        "sources"
    ]

    loaded_sources: dict[
        str,
        MaterializedLineageSourceFacts,
    ] = {}

    for source_key in sorted(
        raw_sources
    ):
        if (
            not isinstance(
                source_key,
                str,
            )
            or not source_key
        ):
            raise pickle.UnpicklingError(
                "Lineage manifest source key is invalid."
            )

        entry = raw_sources[
            source_key
        ]

        if not isinstance(
            entry,
            dict,
        ):
            raise pickle.UnpicklingError(
                "Lineage manifest source entry must be a mapping."
            )

        file_name = entry.get(
            "file"
        )
        expected_fingerprint = entry.get(
            "source_fingerprint"
        )
        expected_semantic_version = entry.get(
            "semantic_version"
        )

        if (
            not isinstance(
                file_name,
                str,
            )
            or not file_name
            or not isinstance(
                expected_fingerprint,
                str,
            )
            or not expected_fingerprint
            or not isinstance(
                expected_semantic_version,
                str,
            )
            or not expected_semantic_version
        ):
            raise pickle.UnpicklingError(
                "Lineage manifest source entry is incomplete."
            )

        chunk_path = _snapshot_child_path(
            cache_dir,
            file_name,
            label="Lineage chunk",
        )

        try:
            with chunk_path.open(
                "rb"
            ) as stream:
                source_slice = (
                    _SnapshotUnpickler(
                        stream
                    ).load()
                )
        except (
            OSError,
            pickle.PickleError,
            EOFError,
        ) as exc:
            raise pickle.UnpicklingError(
                "Invalid lineage source chunk."
            ) from exc

        if not isinstance(
            source_slice,
            MaterializedLineageSourceFacts,
        ):
            raise pickle.UnpicklingError(
                "Lineage source chunk has invalid type."
            )

        if (
            source_slice.manifest.source_key
            != source_key
        ):
            raise pickle.UnpicklingError(
                "Lineage chunk source key mismatch."
            )

        if (
            source_slice.manifest.source_fingerprint
            != expected_fingerprint
        ):
            raise pickle.UnpicklingError(
                "Lineage chunk source fingerprint mismatch."
            )

        if (
            source_slice.manifest.semantic_version
            != expected_semantic_version
        ):
            raise pickle.UnpicklingError(
                "Lineage chunk semantic version mismatch."
            )

        loaded_sources[
            source_key
        ] = source_slice

    return loaded_sources


class SnapshotRevisionConflict(ValueError):
    def __init__(self, current_revision: int | None, requested_revision: int):
        self.current_revision = current_revision
        self.requested_revision = requested_revision
        super().__init__(
            "Snapshot revision conflict: "
            f"current={current_revision}, requested={requested_revision}."
        )


def _paths(cache_dir: str | Path) -> tuple[Path, Path, Path]:
    root = Path(cache_dir)
    return root / "engine_state.pkl", root / "engine_state.meta.json", root / "engine_state.lock"


def read_metadata(cache_dir: str | Path) -> LiveStateMetadata | None:
    """Read snapshot metadata without loading the potentially large pickle."""

    _, meta_file, _ = _paths(cache_dir)
    try:
        payload = json.loads(meta_file.read_text(encoding="utf-8"))
        if payload.get("schema_version") not in {
            "1.0",
            "1.1",
            "1.2",
            LIVE_STATE_SCHEMA_VERSION,
        }:
            return None
        return LiveStateMetadata(
            schema_version=str(payload.get("schema_version", "1.0")),
            state_id=str(payload.get("state_id", "")),
            revision=int(payload.get("revision", 0)),
            writer=str(payload.get("writer", "legacy")),
            repo_id=str(payload.get("repo_id", "")),
            root_path=str(payload.get("root_path", "")),
            state_file=str(payload.get("state_file", "")),
            file_state_file=str(payload.get("file_state_file", "")),
            lineage_manifest_file=str(
                payload.get(
                    "lineage_manifest_file",
                    "",
                )
            ),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _acquire_lock(lock_file: Path, timeout: float = 5.0) -> int:
    deadline = time.monotonic() + timeout
    while True:
        try:
            return os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (FileExistsError, PermissionError):
            try:
                if time.time() - lock_file.stat().st_mtime > 30:
                    lock_file.unlink()
                    continue

            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for LIVE state lock: {lock_file}")
            time.sleep(0.02)


def save_snapshot(
    state: Any,
    cache_dir: str | Path,
    state_id: str,
    *,
    writer: str = "unknown",
    repo_id: str = "",
    root_path: str = "",
    revision_floor: int = 0,
    exact_revision: int | None = None,
    file_state_payload: dict[str, Any] | None = None,
    previous_state: Any = None,
) -> LiveStateMetadata:
    """Atomically publish a complete snapshot and monotonically increasing revision."""

    state_file, meta_file, lock_file = _paths(cache_dir)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = _acquire_lock(lock_file)
    token = uuid.uuid4().hex
    state_tmp = state_file.with_name(f".{state_file.name}.{token}.tmp")
    meta_tmp = meta_file.with_name(f".{meta_file.name}.{token}.tmp")
    generation_state = state_tmp
    generation_file_state: Path | None = None
    generation_lineage_manifest: Path | None = None
    generation_lineage_chunks: list[Path] = []
    reusable_lineage_sources: dict[str, Any] = {}
    committed = False

    try:
        current = read_metadata(cache_dir)
        normalized_root = (
            str(Path(root_path).expanduser().resolve())
            if root_path
            else ""
        )

        if (
            current
            and repo_id
            and current.repo_id
            and current.repo_id != repo_id
        ):
            raise ValueError(
                "Snapshot repository ID does not match existing metadata."
            )

        if (
            current
            and normalized_root
            and current.root_path
            and Path(current.root_path).expanduser().resolve()
            != Path(normalized_root)
        ):
            raise ValueError(
                "Snapshot repository root does not match existing metadata."
            )

        if exact_revision is not None:
            if (
                isinstance(exact_revision, bool)
                or not isinstance(exact_revision, int)
                or exact_revision < 0
            ):
                raise ValueError(
                    "exact_revision must be a non-negative integer."
                )

            current_revision = (
                current.revision
                if current is not None
                else None
            )

            if (
                current_revision is None
                and exact_revision != 1
            ):
                raise SnapshotRevisionConflict(
                    None,
                    exact_revision,
                )

            if (
                current_revision is not None
                and exact_revision
                != current_revision + 1
            ):
                raise SnapshotRevisionConflict(
                    current_revision,
                    exact_revision,
                )

            next_revision = exact_revision

            generation_state = (
                state_file.parent
                / (
                    f"engine_state.r{exact_revision}."
                    f"{token}.pkl"
                )
            )

            generation_file_state = (
                state_file.parent
                / (
                    f"file_state.r{exact_revision}."
                    f"{token}.json"
                )
            )

            if _supports_split_lineage_generation(
                state
            ):
                generation_lineage_manifest = (
                    state_file.parent
                    / (
                        f"lineage_manifest.r{exact_revision}."
                        f"{token}.json"
                    )
                )

                reusable_lineage_sources = (
                    _reusable_lineage_manifest_sources(
                        cache_dir,
                        current,
                        previous_state,
                    )
                )

        else:
            next_revision = (
                max(
                    current.revision
                    if current
                    else 0,
                    revision_floor,
                )
                + 1
            )

        metadata = LiveStateMetadata(
            state_id=state_id,
            revision=next_revision,
            writer=writer,
            repo_id=repo_id,
            root_path=normalized_root,
            state_file=(
                generation_state.name
                if exact_revision is not None
                else ""
            ),
            file_state_file=(
                generation_file_state.name
                if generation_file_state is not None
                else ""
            ),
            lineage_manifest_file=(
                generation_lineage_manifest.name
                if generation_lineage_manifest is not None
                else ""
            ),
        )

        if (
            exact_revision is not None
            and isinstance(
                state,
                dict,
            )
        ):
            state["revision"] = metadata.revision
            state["state_id"] = metadata.state_id

        elif (
            state is not None
            and hasattr(
                state,
                "__dict__",
            )
        ):
            try:
                setattr(
                    state,
                    "state_id",
                    metadata.state_id,
                )
                setattr(
                    state,
                    "revision",
                    metadata.revision,
                )
            except AttributeError:
                pass

        state_to_persist = state

        if (
            generation_lineage_manifest
            is not None
        ):
            (
                state_to_persist,
                generation_lineage_chunks,
            ) = _write_split_lineage_generation(
                state,
                generation_lineage_manifest,
                state_id=metadata.state_id,
                revision=metadata.revision,
                token=token,
                previous_state=previous_state,
                reusable_sources=reusable_lineage_sources,
            )

        with generation_state.open(
            "wb"
        ) as stream:
            pickle.dump(
                {
                    "metadata": asdict(
                        metadata
                    ),
                    "state": state_to_persist,
                },
                stream,
            )
            stream.flush()
            os.fsync(
                stream.fileno()
            )

        if generation_file_state is not None:
            if (
                not isinstance(
                    file_state_payload,
                    dict,
                )
                or not isinstance(
                    file_state_payload.get(
                        "_meta"
                    ),
                    dict,
                )
            ):
                raise ValueError(
                    "file_state_payload must contain a _meta mapping."
                )

            payload_meta = file_state_payload[
                "_meta"
            ]

            if (
                payload_meta.get(
                    "state_id",
                    "",
                )
                != state_id
            ):
                raise ValueError(
                    "FileState payload state_id does not match snapshot state_id."
                )

            if (
                payload_meta.get(
                    "revision"
                )
                != exact_revision
            ):
                raise ValueError(
                    "FileState payload revision does not match exact_revision."
                )

            with generation_file_state.open(
                "w",
                encoding="utf-8",
            ) as stream:
                json.dump(
                    file_state_payload,
                    stream,
                    indent=2,
                )
                stream.flush()
                os.fsync(
                    stream.fileno()
                )

        with meta_tmp.open(
            "w",
            encoding="utf-8",
        ) as stream:
            json.dump(
                asdict(
                    metadata
                ),
                stream,
                indent=2,
            )
            stream.flush()
            os.fsync(
                stream.fileno()
            )

        if exact_revision is None:
            os.replace(
                generation_state,
                state_file,
            )

        os.replace(
            meta_tmp,
            meta_file,
        )

        committed = True

        return metadata

    finally:
        for temporary in (
            state_tmp,
            meta_tmp,
        ):
            try:
                temporary.unlink()
            except OSError:
                pass

        if (
            not committed
            and exact_revision is not None
        ):
            failed_generations = [
                generation_state,
                generation_file_state,
                generation_lineage_manifest,
                *generation_lineage_chunks,
            ]

            for temporary in failed_generations:
                if temporary is None:
                    continue

                try:
                    temporary.unlink()
                except OSError:
                    pass

        try:
            os.close(lock_fd)
        finally:
            try:
                lock_file.unlink()
            except OSError:
                pass


def load_snapshot(
    cache_dir: str | Path,
    expected_state_id: str = "",
    *,
    expected_repo_id: str = "",
    expected_root_path: str = "",
) -> tuple[Any, LiveStateMetadata] | None:
    """Load one complete published snapshot, rejecting incompatible identities."""

    state_file, _, _ = _paths(cache_dir)
    metadata = read_metadata(cache_dir)
    normalized_root = (
        str(Path(expected_root_path).expanduser().resolve())
        if expected_root_path
        else ""
    )
    if metadata is None or (expected_state_id and metadata.state_id != expected_state_id):
        return None
    if expected_repo_id and metadata.repo_id != expected_repo_id:
        return None
    if normalized_root and (
        not metadata.root_path
        or Path(metadata.root_path).expanduser().resolve() != Path(normalized_root)
    ):
        return None
    if metadata.state_file:
        state_file = state_file.parent / metadata.state_file
    try:
        with state_file.open("rb") as stream:
            payload = _SnapshotUnpickler(stream).load()
        if isinstance(payload, dict) and set(payload) == {"metadata", "state"}:
            embedded = payload["metadata"]
            embedded_metadata = LiveStateMetadata(
                schema_version=str(embedded.get("schema_version", "1.0")),
                state_id=str(embedded.get("state_id", "")),
                revision=int(embedded.get("revision", 0)),
                writer=str(embedded.get("writer", "unknown")),
                repo_id=str(embedded.get("repo_id", "")),
                root_path=str(embedded.get("root_path", "")),
                state_file=str(embedded.get("state_file", "")),
                file_state_file=str(embedded.get("file_state_file", "")),
                lineage_manifest_file=str(
                    embedded.get(
                        "lineage_manifest_file",
                        "",
                    )
                ),
            )
            if embedded_metadata.revision != metadata.revision:
                return None
            if (
                embedded_metadata.lineage_manifest_file
                != metadata.lineage_manifest_file
            ):
                return None

            raw_state = payload[
                "state"
            ]

            if metadata.lineage_manifest_file:
                if (
                    metadata.schema_version
                    != LIVE_STATE_SCHEMA_VERSION
                ):
                    return None

                if (
                    raw_state is None
                    or isinstance(
                        raw_state,
                        dict,
                    )
                    or not hasattr(
                        raw_state,
                        "__dict__",
                    )
                ):
                    return None

                split_lineage = (
                    _load_split_lineage_generation(
                        cache_dir,
                        metadata,
                    )
                )

                try:
                    setattr(
                        raw_state,
                        "lineage_facts_by_source",
                        split_lineage,
                    )
                except AttributeError:
                    return None

            state_obj = _normalize_lineage_query_index_state(
                _normalize_lineage_facts_state(
                    _normalize_symbol_call_facts(
                        raw_state
                    )
                )
            )
            state_revision = (
                state_obj.get("revision") if isinstance(state_obj, dict)
                else getattr(state_obj, "revision", None)
            )
            state_id_value = (
                state_obj.get("state_id") if isinstance(state_obj, dict)
                else getattr(state_obj, "state_id", None)
            )
            if state_obj is not None and state_revision is not None and int(state_revision) != metadata.revision:
                return None
            if state_obj is not None and state_id_value is not None and str(state_id_value) != metadata.state_id:
                return None
            if state_obj is not None and hasattr(state_obj, "__dict__"):
                try:
                    setattr(state_obj, "state_id", embedded_metadata.state_id)
                    setattr(state_obj, "revision", embedded_metadata.revision)
                    setattr(state_obj, "provenance", "snapshot")
                except AttributeError:
                    pass
                if not hasattr(state_obj, "module_usages"):
                    try:
                        setattr(state_obj, "module_usages", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "syntax_diagnostics_by_path"):
                    try:
                        setattr(state_obj, "syntax_diagnostics_by_path", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "syntax_diagnostics_state"):
                    try:
                        setattr(state_obj, "syntax_diagnostics_state", "not_materialized")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "module_usages_manifest"):
                    try:
                        setattr(state_obj, "module_usages_manifest", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "topology_analytics"):
                    try:
                        setattr(state_obj, "topology_analytics", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "topology_metrics_state"):
                    try:
                        setattr(state_obj, "topology_metrics_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cached_analytics"):
                    try:
                        setattr(state_obj, "cached_analytics", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cached_analytics_state"):
                    try:
                        setattr(state_obj, "cached_analytics_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cycles"):
                    try:
                        setattr(state_obj, "cycles", [])
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cycles_state"):
                    try:
                        setattr(state_obj, "cycles_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "collision_facts"):
                    try:
                        setattr(state_obj, "collision_facts", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "collisions"):
                    try:
                        setattr(state_obj, "collisions", [])
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "collisions_state"):
                    try:
                        setattr(state_obj, "collisions_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "dependency_matrix"):
                    try:
                        setattr(state_obj, "dependency_matrix", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "dependency_matrix_state"):
                    try:
                        setattr(state_obj, "dependency_matrix_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "shared_usage_clusters"):
                    try:
                        setattr(state_obj, "shared_usage_clusters", [])
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "shared_usage_clusters_state"):
                    try:
                        setattr(state_obj, "shared_usage_clusters_state", "deferred")
                    except AttributeError:
                        pass
            return state_obj, metadata
        if metadata.lineage_manifest_file:
            return None

        payload = _normalize_lineage_query_index_state(
            _normalize_lineage_facts_state(
                _normalize_symbol_call_facts(payload)
            )
        )
        if payload is not None and hasattr(payload, "__dict__"):
            if not hasattr(payload, "module_usages"):
                try:
                    setattr(payload, "module_usages", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "syntax_diagnostics_by_path"):
                try:
                    setattr(payload, "syntax_diagnostics_by_path", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "syntax_diagnostics_state"):
                try:
                    setattr(payload, "syntax_diagnostics_state", "not_materialized")
                except AttributeError:
                    pass
            if not hasattr(payload, "module_usages_manifest"):
                try:
                    setattr(payload, "module_usages_manifest", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "topology_analytics"):
                try:
                    setattr(payload, "topology_analytics", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "topology_metrics_state"):
                try:
                    setattr(payload, "topology_metrics_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "cached_analytics"):
                try:
                    setattr(payload, "cached_analytics", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "cached_analytics_state"):
                try:
                    setattr(payload, "cached_analytics_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "cycles"):
                try:
                    setattr(payload, "cycles", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "cycles_state"):
                try:
                    setattr(payload, "cycles_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "collision_facts"):
                try:
                    setattr(payload, "collision_facts", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "collisions"):
                try:
                    setattr(payload, "collisions", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "collisions_state"):
                try:
                    setattr(payload, "collisions_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "dependency_matrix"):
                try:
                    setattr(payload, "dependency_matrix", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "dependency_matrix_state"):
                try:
                    setattr(payload, "dependency_matrix_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "shared_usage_clusters"):
                try:
                    setattr(payload, "shared_usage_clusters", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "shared_usage_clusters_state"):
                try:
                    setattr(payload, "shared_usage_clusters_state", "deferred")
                except AttributeError:
                    pass
        return payload, metadata




    except (OSError, pickle.PickleError, EOFError):
        return None



def migrate_legacy_snapshot(repo_root: str | Path) -> Path:
    """Copy a verified path-keyed snapshot into its repo-ID cache directory."""

    from contextor.core.paths import legacy_repo_cache_dir, repo_cache_dir
    from contextor.core.repository_identity import require_repository_identity

    root = Path(repo_root).expanduser().resolve()
    identity = require_repository_identity(root)
    target = repo_cache_dir(root)
    if read_metadata(target) is not None:
        return target

    legacy = legacy_repo_cache_dir(root)
    if legacy == target:
        return target
    loaded = load_snapshot(legacy)
    if loaded is None:
        return target

    state, metadata = loaded
    save_snapshot(
        state,
        target,
        metadata.state_id,
        writer=f"migration:{metadata.writer}",
        repo_id=identity.repo_id,
        root_path=identity.root_path,
        revision_floor=metadata.revision,
    )
    legacy_file_state = legacy / "file_state.json"
    target_file_state = target / "file_state.json"
    if legacy_file_state.is_file() and not target_file_state.exists():
        target_file_state.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_file_state, target_file_state)
    return target

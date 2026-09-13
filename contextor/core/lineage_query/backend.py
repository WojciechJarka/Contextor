from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from contextor.core.domain.lineage_facts import (
    LineageFamilyStatus,
    MaterializedLineageSourceFacts,
    SourceLineageManifest,
)


_MISSING = object()


@dataclass(frozen=True)
class LineageBackendMetadata:
    revision: int | None
    provenance: str
    family_state: str
    semantic_version: str | None
    source_count: int


@runtime_checkable
class CanonicalLineageBackend(Protocol):
    def metadata(self) -> LineageBackendMetadata: ...

    def source_keys(self) -> tuple[str, ...]: ...

    def get_source(
        self,
        source_key: str,
    ) -> MaterializedLineageSourceFacts | None: ...

    def get_manifest(
        self,
        source_key: str,
    ) -> SourceLineageManifest | None: ...

    def iter_sources(
        self,
        source_keys: Iterable[str] | None = None,
    ) -> tuple[MaterializedLineageSourceFacts, ...]: ...


class RepositoryStateLineageBackend:
    """Read-only lineage backend over one already-hydrated canonical state."""

    def __init__(self, state: object) -> None:
        raw_sources = getattr(state, "lineage_facts_by_source", {})
        if raw_sources is None:
            raw_sources = {}
        if not isinstance(raw_sources, Mapping):
            raise TypeError("lineage_facts_by_source must be a mapping.")

        for source_key in raw_sources:
            if not isinstance(source_key, str) or not source_key:
                raise TypeError(
                    "lineage_facts_by_source keys must be non-empty strings."
                )

        self._state = state
        self._sources = raw_sources

    def metadata(self) -> LineageBackendMetadata:
        raw_revision = getattr(self._state, "revision", None)
        if raw_revision is not None and (
            isinstance(raw_revision, bool) or not isinstance(raw_revision, int)
        ):
            raise TypeError("Canonical lineage revision must be an integer or None.")

        raw_provenance = getattr(self._state, "provenance", "snapshot") or "snapshot"
        if not isinstance(raw_provenance, str):
            raise TypeError("Canonical lineage provenance must be a string.")

        raw_family_state = getattr(
            self._state,
            "lineage_facts_state",
            LineageFamilyStatus.NOT_MATERIALIZED.value,
        )
        try:
            family_state = LineageFamilyStatus(raw_family_state).value
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Canonical lineage family state is invalid."
            ) from exc

        semantic_version = getattr(
            self._state,
            "lineage_facts_semantic_version",
            None,
        )
        if semantic_version is not None and (
            not isinstance(semantic_version, str) or not semantic_version
        ):
            raise TypeError(
                "Canonical lineage semantic version must be a non-empty string or None."
            )

        return LineageBackendMetadata(
            revision=raw_revision,
            provenance=raw_provenance,
            family_state=family_state,
            semantic_version=semantic_version,
            source_count=len(self._sources),
        )

    def source_keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._sources))

    def get_source(
        self,
        source_key: str,
    ) -> MaterializedLineageSourceFacts | None:
        if not isinstance(source_key, str) or not source_key:
            raise ValueError("source_key must be a non-empty string.")

        value = self._sources.get(source_key, _MISSING)
        if value is _MISSING:
            return None
        if not isinstance(value, MaterializedLineageSourceFacts):
            raise TypeError(
                f"Canonical lineage slice {source_key!r} has invalid type."
            )
        return value

    def get_manifest(
        self,
        source_key: str,
    ) -> SourceLineageManifest | None:
        source = self.get_source(source_key)
        return source.manifest if source is not None else None

    def iter_sources(
        self,
        source_keys: Iterable[str] | None = None,
    ) -> tuple[MaterializedLineageSourceFacts, ...]:
        if source_keys is None:
            keys = self.source_keys()
        else:
            if isinstance(source_keys, (str, bytes)):
                raise TypeError("source_keys must be an iterable of source-key strings.")

            requested: set[str] = set()
            for source_key in source_keys:
                if not isinstance(source_key, str) or not source_key:
                    raise ValueError(
                        "source_keys must contain only non-empty strings."
                    )
                requested.add(source_key)
            keys = tuple(sorted(requested))

        result: list[MaterializedLineageSourceFacts] = []
        for source_key in keys:
            source = self.get_source(source_key)
            if source is not None:
                result.append(source)
        return tuple(result)

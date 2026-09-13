from __future__ import annotations

from dataclasses import dataclass

from contextor.core.lineage_query.backend import CanonicalLineageBackend
from contextor.core.report_query import ARTIFACT_ID_RE, IndexCatalog


@dataclass(frozen=True)
class ResolvedLineageTarget:
    artifact_id: str
    qualified_name: str
    module_name: str
    symbol_name: str
    resolution: str


@dataclass(frozen=True)
class LineageTargetResolution:
    status: str
    query: str
    target: ResolvedLineageTarget | None = None
    candidates: tuple[ResolvedLineageTarget, ...] = ()


class LineageQueryService:
    def __init__(
        self,
        backend: CanonicalLineageBackend,
        catalog: IndexCatalog,
    ) -> None:
        if not isinstance(backend, CanonicalLineageBackend):
            raise TypeError("backend must implement CanonicalLineageBackend.")
        if not isinstance(catalog, IndexCatalog):
            raise TypeError("catalog must be IndexCatalog.")
        self._backend = backend
        self._catalog = catalog

    def resolve_target(self, query: str) -> LineageTargetResolution:
        if not isinstance(query, str):
            raise TypeError("query must be a string.")

        raw = query.strip()
        if not raw:
            return LineageTargetResolution(
                status="invalid",
                query=raw,
            )

        if ARTIFACT_ID_RE.fullmatch(raw):
            artifact_id = raw[0].upper() + raw[1:]
            qualified_name = self._catalog.artifacts.get(artifact_id)
            if qualified_name is None:
                return LineageTargetResolution(
                    status="not_found",
                    query=raw,
                )
            return LineageTargetResolution(
                status="resolved",
                query=raw,
                target=_target(
                    artifact_id,
                    str(qualified_name),
                    resolution="exact_id",
                ),
            )

        if raw.count("::") != 1:
            return LineageTargetResolution(
                status="invalid",
                query=raw,
            )

        module_name, symbol_name = raw.split("::", 1)
        if not module_name or not symbol_name:
            return LineageTargetResolution(
                status="invalid",
                query=raw,
            )

        matches = tuple(
            _target(
                str(artifact_id),
                str(qualified_name),
                resolution="exact_identity",
            )
            for artifact_id, qualified_name in sorted(
                self._catalog.artifacts.items(),
                key=lambda item: (str(item[1]), str(item[0])),
            )
            if str(qualified_name) == raw
        )

        if not matches:
            return LineageTargetResolution(
                status="not_found",
                query=raw,
            )
        if len(matches) > 1:
            return LineageTargetResolution(
                status="ambiguous",
                query=raw,
                candidates=matches,
            )
        return LineageTargetResolution(
            status="resolved",
            query=raw,
            target=matches[0],
        )


def _target(
    artifact_id: str,
    qualified_name: str,
    *,
    resolution: str,
) -> ResolvedLineageTarget:
    if qualified_name.count("::") != 1:
        raise ValueError(
            "Active artifact identity must be canonical module::symbol."
        )
    module_name, symbol_name = qualified_name.split("::", 1)
    if not module_name or not symbol_name:
        raise ValueError(
            "Active artifact identity must be canonical module::symbol."
        )
    return ResolvedLineageTarget(
        artifact_id=artifact_id,
        qualified_name=qualified_name,
        module_name=module_name,
        symbol_name=symbol_name,
        resolution=resolution,
    )

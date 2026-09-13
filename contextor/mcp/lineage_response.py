from __future__ import annotations

from dataclasses import dataclass

from contextor.core.lineage_query.service import (
    SYMBOL_LINEAGE_SECTION_ORDER,
)


SYMBOL_LINEAGE_MODES = ("auto", "preview", "fetch")


@dataclass(frozen=True)
class SymbolLineageResponsePlan:
    mode: str
    candidate_sections: tuple[str, ...]
    include_payload: bool
    requires_size_decision: bool


def plan_symbol_lineage_response(*, mode: str = "auto", sections: tuple[str, ...] | None = None) -> SymbolLineageResponsePlan:
    if not isinstance(mode, str):
        raise TypeError("mode must be a string.")
    normalized_mode = mode.strip().lower()
    if normalized_mode not in SYMBOL_LINEAGE_MODES:
        raise ValueError("mode must be 'auto', 'preview', or 'fetch'.")
    if sections is not None:
        if not isinstance(sections, tuple):
            raise TypeError("sections must be a tuple of section names.")
        if any(not isinstance(section, str) or not section for section in sections):
            raise ValueError("sections must contain non-empty strings.")
        if len(set(sections)) != len(sections):
            raise ValueError("sections must not contain duplicates.")
        unknown = tuple(sorted(set(sections) - set(SYMBOL_LINEAGE_SECTION_ORDER)))
        if unknown:
            raise ValueError("Unknown symbol lineage sections: " + ", ".join(unknown))
    if normalized_mode in {"auto", "preview"}:
        if sections is not None:
            raise ValueError(f"{normalized_mode} mode does not accept an explicit section selection.")
        return SymbolLineageResponsePlan(
            normalized_mode, SYMBOL_LINEAGE_SECTION_ORDER,
            normalized_mode == "auto", normalized_mode == "auto",
        )
    if not sections:
        raise ValueError("fetch mode requires at least one section.")
    requested = set(sections)
    return SymbolLineageResponsePlan(
        "fetch",
        tuple(s for s in SYMBOL_LINEAGE_SECTION_ORDER if s in requested),
        True, False,
    )

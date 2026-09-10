from __future__ import annotations

import ast
from collections.abc import Callable

from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
from contextor.core.domain.lineage_facts import ExtractedOccurrenceRef


VisitFn = Callable[[ast.AST, str | None, str | None], None]


def visit_block_from_frame(
    state: LineageExtractionState,
    body: list[ast.stmt],
    owner: str | None,
    walrus_owner: str | None,
    frame: dict[str, ExtractedOccurrenceRef],
    *,
    visit: VisitFn,
) -> dict[str, ExtractedOccurrenceRef]:
    state.replace_frame(owner, frame)
    for child in body:
        visit(child, owner, walrus_owner)
    return state.clone_frame(owner)

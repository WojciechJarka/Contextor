from __future__ import annotations

import ast
from collections.abc import Callable

from contextor.core.analysis.lineage_extraction_emit import add_anchor
from contextor.core.analysis.lineage_extraction_state import (
    _ActiveComprehension,
    LineageExtractionState,
)
from contextor.core.domain.lineage_facts import ExtractedOccurrenceRef

VisitFn = Callable[[ast.AST, str | None, str | None], None]
RuntimeBindTargetFn = Callable[[ast.AST, str | None, str | None], None]


def begin_comprehension(
    state: LineageExtractionState,
    lookup_owner: str,
    lexical_enclosing_owner: str | None,
    effective_walrus_owner: str | None,
) -> _ActiveComprehension:
    record = _ActiveComprehension(
        lookup_owner,
        lexical_enclosing_owner,
        effective_walrus_owner,
        state.clone_frame(effective_walrus_owner),
        set(),
    )
    state.replace_frame(
        lookup_owner,
        state.clone_frame(lexical_enclosing_owner),
    )
    imports = state.import_frame(lookup_owner)
    imports.clear()
    imports.update(
        state.import_frame(lexical_enclosing_owner)
    )
    state._active_comprehensions.append(record)
    return record


def publish_executed_walrus(
    state: LineageExtractionState,
    name: str,
    binding: ExtractedOccurrenceRef,
    target_owner: str | None,
) -> None:
    for record in state._active_comprehensions:
        if record.effective_walrus_owner != target_owner:
            continue
        record.touched_walrus_names.add(name)
        state.frame(record.lookup_owner)[name] = binding


def finish_comprehension(
    state: LineageExtractionState,
    record: _ActiveComprehension,
) -> None:
    if (
        not state._active_comprehensions
        or state._active_comprehensions[-1] is not record
    ):
        raise RuntimeError(
            "Comprehension lineage stack mismatch"
        )
    body_frame = state.clone_frame(
        record.effective_walrus_owner
    )
    merged = state.merge_frames(
        (record.walrus_entry_frame, body_frame)
    )
    state.replace_frame(
        record.effective_walrus_owner,
        merged,
    )
    state._active_comprehensions.pop()
    for parent in state._active_comprehensions:
        if (
            parent.effective_walrus_owner
            != record.effective_walrus_owner
        ):
            continue
        for name in record.touched_walrus_names:
            parent.touched_walrus_names.add(name)
            if name in merged:
                state.frame(parent.lookup_owner)[name] = merged[name]
            else:
                state.frame(parent.lookup_owner).pop(name, None)


def visit_comprehension_expression(
    state: LineageExtractionState,
    paths: dict[int, str],
    node: ast.AST,
    generators: list[ast.comprehension],
    values: tuple[ast.AST, ...],
    owner: str | None,
    walrus_owner: str | None,
    *,
    visit: VisitFn,
    runtime_bind_target: RuntimeBindTargetFn,
) -> None:
    comprehension_id = add_anchor(
        state,
        paths,
        "comprehension",
        node,
        None,
        owner,
    )
    state.register_owner(comprehension_id, owner, "comprehension", node)
    if not generators:
        raise ValueError(
            "Parsed comprehension without generators"
        )
    first = generators[0]
    visit(
        first.iter,
        owner,
        walrus_owner,
    )
    effective_walrus_owner = walrus_owner or owner
    record = begin_comprehension(
        state,
        comprehension_id,
        owner,
        effective_walrus_owner,
    )
    try:
        runtime_bind_target(
            first.target,
            comprehension_id,
            effective_walrus_owner,
        )
        for condition in first.ifs:
            visit(
                condition,
                comprehension_id,
                effective_walrus_owner,
            )
        for generator in generators[1:]:
            visit(
                generator.iter,
                comprehension_id,
                effective_walrus_owner,
            )
            runtime_bind_target(
                generator.target,
                comprehension_id,
                effective_walrus_owner,
            )
            for condition in generator.ifs:
                visit(
                    condition,
                    comprehension_id,
                    effective_walrus_owner,
                )
        for value in values:
            visit(
                value,
                comprehension_id,
                effective_walrus_owner,
            )
    finally:
        finish_comprehension(state, record)

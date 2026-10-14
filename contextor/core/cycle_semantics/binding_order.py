"""Lexical module-level binding order evidence, never runtime proof."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from .provenance import (
    ImportOccurrence,
    ImportProvenance,
    extract_import_provenance,
)


@dataclass(frozen=True)
class CycleBindingCandidate:
    name: str
    operation: str
    completion_point: str


@dataclass(frozen=True)
class ModuleStatementEvidence:
    ordinal: int
    line: int
    column: int
    end_line: int | None
    end_column: int | None
    kind: str
    contained_import_ordinals: tuple[int, ...]
    binding_candidates: tuple[CycleBindingCandidate, ...]
    execution_proven: str = "UNKNOWN"


@dataclass(frozen=True)
class ModuleBindingOrder:
    module_id: str
    source_fingerprint: str
    statements: tuple[ModuleStatementEvidence, ...]
    initialization_reachability: str = "UNKNOWN"


def _import_key(node: ast.Import | ast.ImportFrom) -> tuple:
    return (
        node.lineno,
        node.col_offset,
        getattr(node, "end_lineno", None),
        getattr(node, "end_col_offset", None),
        "IMPORT" if isinstance(node, ast.Import) else "IMPORT_FROM",
        None if isinstance(node, ast.Import) else node.module,
        0 if isinstance(node, ast.Import) else node.level,
        tuple((alias.name, alias.asname) for alias in node.names),
    )


def _occurrence_key(occurrence: ImportOccurrence) -> tuple:
    return (
        occurrence.line,
        occurrence.column,
        occurrence.end_line,
        occurrence.end_column,
        occurrence.form,
        occurrence.module,
        occurrence.level,
        occurrence.aliases,
    )


def _binding_candidates(
    stmt: ast.stmt,
) -> tuple[CycleBindingCandidate, ...]:
    found: list[CycleBindingCandidate] = []

    def record(
        name: str,
        operation: str,
        completion: str,
    ) -> None:
        found.append(
            CycleBindingCandidate(
                name,
                operation,
                completion,
            )
        )

    if isinstance(stmt, ast.Import):
        for alias in stmt.names:
            record(
                alias.asname or alias.name.split(".")[0],
                "BIND",
                "AFTER_IMPORT",
            )

    elif isinstance(stmt, ast.ImportFrom):
        for alias in stmt.names:
            if alias.name != "*":
                record(
                    alias.asname or alias.name,
                    "BIND",
                    "AFTER_IMPORT",
                )

    elif isinstance(
        stmt,
        (ast.FunctionDef, ast.AsyncFunctionDef),
    ):
        record(
            stmt.name,
            "BIND",
            "AFTER_FUNCTION_DEFINITION",
        )

    elif isinstance(stmt, ast.ClassDef):
        record(
            stmt.name,
            "BIND",
            "AFTER_CLASS_DEFINITION",
        )

    elif isinstance(stmt, ast.Assign):
        if (
            len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
        ):
            record(
                stmt.targets[0].id,
                "BIND",
                "AFTER_ASSIGNMENT",
            )

    elif isinstance(stmt, ast.AnnAssign):
        if (
            stmt.value is not None
            and isinstance(stmt.target, ast.Name)
        ):
            record(
                stmt.target.id,
                "BIND",
                "AFTER_ANNOTATED_ASSIGNMENT",
            )

    elif isinstance(stmt, ast.AugAssign):
        if isinstance(stmt.target, ast.Name):
            record(
                stmt.target.id,
                "BIND",
                "AFTER_AUGMENTED_ASSIGNMENT",
            )

    elif isinstance(stmt, ast.Delete):
        for target in stmt.targets:
            if isinstance(target, ast.Name):
                record(
                    target.id,
                    "DELETE",
                    "AFTER_DELETE",
                )

    return tuple(found)


def extract_cycle_module_binding_order(
    tree: ast.AST,
    provenance: ImportProvenance,
) -> ModuleBindingOrder:
    """Record lexical top-level steps and candidate binding points.

    A preceding candidate is not necessarily an available binding.
    This function cannot certify runtime safety or import-order safety.
    """
    if not isinstance(tree, ast.Module):
        raise TypeError("tree must be an ast.Module")

    if not isinstance(provenance, ImportProvenance):
        raise TypeError("provenance must be ImportProvenance")

    replay = extract_import_provenance(
        tree,
        module_id=provenance.module_id,
        source_key=provenance.source_key,
        source_path=provenance.source_path,
        source_fingerprint=provenance.source_fingerprint,
    )

    if replay != provenance:
        raise ValueError(
            "AST import occurrences differ from provenance"
        )

    lookup: dict[tuple, int] = {}

    for occurrence in provenance.occurrences:
        key = _occurrence_key(occurrence)

        if key in lookup:
            raise ValueError(
                "ambiguous import occurrence position"
            )

        lookup[key] = occurrence.ordinal

    seen: set[int] = set()
    statements: list[ModuleStatementEvidence] = []

    for index, statement in enumerate(tree.body):
        contained: list[int] = []

        for node in ast.walk(statement):
            if not isinstance(
                node,
                (ast.Import, ast.ImportFrom),
            ):
                continue

            key = _import_key(node)
            ordinal = lookup.get(key)

            if ordinal is None or ordinal in seen:
                raise ValueError(
                    "unmatched or duplicated AST import occurrence"
                )

            seen.add(ordinal)
            contained.append(ordinal)

        statements.append(
            ModuleStatementEvidence(
                ordinal=index,
                line=statement.lineno,
                column=statement.col_offset,
                end_line=getattr(
                    statement, "end_lineno", None
                ),
                end_column=getattr(
                    statement, "end_col_offset", None
                ),
                kind=type(statement).__name__,
                contained_import_ordinals=tuple(
                    sorted(contained)
                ),
                binding_candidates=_binding_candidates(
                    statement
                ),
            )
        )

    if seen != set(lookup.values()):
        raise ValueError(
            "not all import occurrences belong to "
            "top-level statements"
        )

    return ModuleBindingOrder(
        module_id=provenance.module_id,
        source_fingerprint=provenance.source_fingerprint,
        statements=tuple(statements),
    )

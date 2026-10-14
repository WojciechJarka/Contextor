"""Lossless lexical provenance of explicit Python imports.

No import resolution, graph mutation, reachability proof
or runtime execution.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class ScopeFrame:
    kind: str
    name: str
    line: int


@dataclass(frozen=True)
class ControlFrame:
    kind: str
    branch: str
    line: int
    expression: str | None = None


@dataclass(frozen=True)
class ImportOccurrence:
    ordinal: int
    line: int
    column: int
    end_line: int | None
    end_column: int | None
    form: str
    module: str | None
    level: int
    aliases: tuple[tuple[str, str | None], ...]
    scopes: tuple[ScopeFrame, ...]
    controls: tuple[ControlFrame, ...]


@dataclass(frozen=True)
class ImportProvenance:
    module_id: str
    source_key: str
    source_path: str
    source_fingerprint: str
    occurrences: tuple[ImportOccurrence, ...]


class _ImportOccurrenceVisitor(ast.NodeVisitor):

    def __init__(self) -> None:
        self.scopes: list[ScopeFrame] = []
        self.controls: list[ControlFrame] = []
        self.raw: list[
            tuple[
                ast.Import | ast.ImportFrom,
                tuple[ScopeFrame, ...],
                tuple[ControlFrame, ...],
            ]
        ] = []

    def _record(
        self,
        node: ast.Import | ast.ImportFrom,
    ) -> None:
        self.raw.append(
            (
                node,
                tuple(self.scopes),
                tuple(self.controls),
            )
        )

    def visit_Import(self, node: ast.Import) -> None:
        self._record(node)

    def visit_ImportFrom(
        self,
        node: ast.ImportFrom,
    ) -> None:
        self._record(node)

    def _visit_body_with_scope(
        self,
        node: ast.AST,
        kind: str,
        name: str,
    ) -> None:
        self.scopes.append(
            ScopeFrame(kind, name, node.lineno)
        )
        try:
            for statement in node.body:
                self.visit(statement)
        finally:
            self.scopes.pop()

    def visit_FunctionDef(
        self,
        node: ast.FunctionDef,
    ) -> None:
        # Definition-time expressions have no import
        # statements. Their calls require later analysis.
        self._visit_body_with_scope(
            node, "FUNCTION", node.name
        )

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> None:
        self._visit_body_with_scope(
            node, "ASYNC_FUNCTION", node.name
        )

    def visit_ClassDef(
        self,
        node: ast.ClassDef,
    ) -> None:
        self._visit_body_with_scope(
            node, "CLASS", node.name
        )

    def _visit_control_body(
        self,
        statements: list[ast.stmt],
        *,
        kind: str,
        branch: str,
        line: int,
        expression: str | None = None,
    ) -> None:
        self.controls.append(
            ControlFrame(
                kind,
                branch,
                line,
                expression,
            )
        )
        try:
            for statement in statements:
                self.visit(statement)
        finally:
            self.controls.pop()

    @staticmethod
    def _expression(
        node: ast.AST | None,
    ) -> str | None:
        if node is None:
            return None
        return ast.dump(
            node,
            include_attributes=False,
        )

    def visit_If(self, node: ast.If) -> None:
        expression = self._expression(node.test)

        self._visit_control_body(
            node.body,
            kind="IF",
            branch="BODY",
            line=node.lineno,
            expression=expression,
        )

        self._visit_control_body(
            node.orelse,
            kind="IF",
            branch="ELSE",
            line=node.lineno,
            expression=expression,
        )

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_control_body(
            node.body,
            kind="TRY",
            branch="BODY",
            line=node.lineno,
        )

        for index, handler in enumerate(
            node.handlers
        ):
            self._visit_control_body(
                handler.body,
                kind="EXCEPT",
                branch=str(index),
                line=handler.lineno,
                expression=self._expression(
                    handler.type
                ),
            )

        self._visit_control_body(
            node.orelse,
            kind="TRY_ELSE",
            branch="ELSE",
            line=node.lineno,
        )

        self._visit_control_body(
            node.finalbody,
            kind="FINALLY",
            branch="FINAL",
            line=node.lineno,
        )

    def visit_For(self, node: ast.For) -> None:
        self._visit_control_body(
            node.body,
            kind="FOR",
            branch="BODY",
            line=node.lineno,
            expression=self._expression(
                node.iter
            ),
        )

        self._visit_control_body(
            node.orelse,
            kind="FOR",
            branch="ELSE",
            line=node.lineno,
        )

    def visit_AsyncFor(
        self,
        node: ast.AsyncFor,
    ) -> None:
        self._visit_control_body(
            node.body,
            kind="ASYNC_FOR",
            branch="BODY",
            line=node.lineno,
            expression=self._expression(
                node.iter
            ),
        )

        self._visit_control_body(
            node.orelse,
            kind="ASYNC_FOR",
            branch="ELSE",
            line=node.lineno,
        )

    def visit_While(
        self,
        node: ast.While,
    ) -> None:
        expression = self._expression(node.test)

        self._visit_control_body(
            node.body,
            kind="WHILE",
            branch="BODY",
            line=node.lineno,
            expression=expression,
        )

        self._visit_control_body(
            node.orelse,
            kind="WHILE",
            branch="ELSE",
            line=node.lineno,
            expression=expression,
        )

    def visit_With(
        self,
        node: ast.With,
    ) -> None:
        self._visit_control_body(
            node.body,
            kind="WITH",
            branch="BODY",
            line=node.lineno,
        )

    def visit_AsyncWith(
        self,
        node: ast.AsyncWith,
    ) -> None:
        self._visit_control_body(
            node.body,
            kind="ASYNC_WITH",
            branch="BODY",
            line=node.lineno,
        )

    def visit_Match(
        self,
        node: ast.Match,
    ) -> None:
        for index, case in enumerate(node.cases):
            condition = self._expression(
                case.pattern
            )

            if case.guard is not None:
                condition += (
                    " GUARD "
                    + self._expression(case.guard)
                )

            self._visit_control_body(
                case.body,
                kind="MATCH",
                branch=str(index),
                line=node.lineno,
                expression=condition,
            )


def extract_import_provenance(
    tree: ast.AST,
    *,
    module_id: str,
    source_key: str,
    source_path: str,
    source_fingerprint: str,
) -> ImportProvenance:
    """Extract individual explicit imports from an AST.

    These are lexical source facts, not runtime proofs.

    A function-local occurrence is not necessarily
    deferred during module initialization.

    Conditional guards are recorded, not evaluated.
    """

    if not isinstance(tree, ast.Module):
        raise TypeError(
            "tree must be an ast.Module"
        )

    values = (
        module_id,
        source_key,
        source_path,
        source_fingerprint,
    )

    if not all(
        isinstance(value, str) and value
        for value in values
    ):
        raise ValueError(
            "module identity, path and fingerprint "
            "must be nonempty strings"
        )

    visitor = _ImportOccurrenceVisitor()
    visitor.visit(tree)

    ordered = sorted(
        enumerate(visitor.raw),
        key=lambda pair: (
            pair[1][0].lineno,
            pair[1][0].col_offset,
            pair[0],
        ),
    )

    occurrences: list[ImportOccurrence] = []

    for ordinal, (_, record) in enumerate(
        ordered
    ):
        node, scopes, controls = record

        occurrences.append(
            ImportOccurrence(
                ordinal=ordinal,
                line=node.lineno,
                column=node.col_offset,
                end_line=getattr(
                    node, "end_lineno", None
                ),
                end_column=getattr(
                    node, "end_col_offset", None
                ),
                form=(
                    "IMPORT"
                    if isinstance(node, ast.Import)
                    else "IMPORT_FROM"
                ),
                module=(
                    node.module
                    if isinstance(node, ast.ImportFrom)
                    else None
                ),
                level=(
                    node.level
                    if isinstance(node, ast.ImportFrom)
                    else 0
                ),
                aliases=tuple(
                    (alias.name, alias.asname)
                    for alias in node.names
                ),
                scopes=scopes,
                controls=controls,
            )
        )

    return ImportProvenance(
        module_id=module_id,
        source_key=source_key,
        source_path=source_path,
        source_fingerprint=source_fingerprint,
        occurrences=tuple(occurrences),
    )

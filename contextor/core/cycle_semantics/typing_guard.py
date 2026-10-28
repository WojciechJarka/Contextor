"""Pure recognition of the restricted typing.TYPE_CHECKING idiom."""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class RecognizedTypingGuard:
    form: str
    marker_statement: ast.Import | ast.ImportFrom


def matches_typing_guard(
    condition: ast.AST,
    form: str,
) -> bool:
    if form == "NAME":
        return (
            isinstance(condition, ast.Name)
            and condition.id == "TYPE_CHECKING"
        )

    if form == "ATTRIBUTE":
        return (
            isinstance(condition, ast.Attribute)
            and condition.attr == "TYPE_CHECKING"
            and isinstance(condition.value, ast.Name)
            and condition.value.id == "typing"
        )

    return False


def recognize_typing_guard(
    tree: ast.Module,
    indexed_ids: frozenset[str],
) -> RecognizedTypingGuard | None:
    if not isinstance(tree, ast.Module) or not isinstance(indexed_ids, frozenset):
        return None

    if "typing" in indexed_ids or "typing.__init__" in indexed_ids:
        return None

    markers: list[tuple[int, ast.Import | ast.ImportFrom, str]] = []
    for position, statement in enumerate(tree.body):
        if (
            isinstance(statement, ast.ImportFrom)
            and statement.module == "typing"
            and statement.level == 0
            and len(statement.names) == 1
            and statement.names[0].name == "TYPE_CHECKING"
            and statement.names[0].asname is None
        ):
            markers.append((position, statement, "NAME"))
        elif (
            isinstance(statement, ast.Import)
            and len(statement.names) == 1
            and statement.names[0].name == "typing"
            and statement.names[0].asname is None
        ):
            markers.append((position, statement, "ATTRIBUTE"))

    if len(markers) != 1:
        return None

    marker_position, marker_statement, form = markers[0]
    protected_name = "TYPE_CHECKING" if form == "NAME" else "typing"

    for position, statement in enumerate(tree.body[:marker_position]):
        if isinstance(statement, ast.Pass):
            continue
        if (
            position == 0
            and isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and type(statement.value.value) is str
        ):
            continue
        return None

    top_level_guards = {
        id(statement)
        for statement in tree.body
        if isinstance(statement, ast.If)
        and matches_typing_guard(statement.test, form)
    }
    guard_positions = [
        position
        for position, statement in enumerate(tree.body)
        if isinstance(statement, ast.If)
        and matches_typing_guard(statement.test, form)
    ]
    if not guard_positions or any(
        position <= marker_position for position in guard_positions
    ):
        return None

    class BindingAudit(ast.NodeVisitor):
        valid = True

        def reject(self) -> None:
            self.valid = False

        def visit_Name(self, node: ast.Name) -> None:
            if node.id == protected_name and isinstance(
                node.ctx, (ast.Store, ast.Del)
            ):
                self.reject()
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                bound = alias.asname or alias.name.split(".", 1)[0]
                if bound == protected_name:
                    if node is marker_statement:
                        continue
                    self.reject()
                if (
                    form == "ATTRIBUTE"
                    and alias.name == "typing"
                    and node is not marker_statement
                ):
                    self.reject()

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            for alias in node.names:
                bound = alias.asname or alias.name
                if bound == protected_name:
                    if node is marker_statement:
                        continue
                    self.reject()
                if (
                    node.module == "typing"
                    and any(alias.name == "TYPE_CHECKING" for alias in node.names)
                    and node is not marker_statement
                ):
                    self.reject()
                if alias.name == "*":
                    self.reject()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if node.name == protected_name:
                self.reject()
            self._visit_arguments(node.args)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            if node.name == protected_name:
                self.reject()
            self._visit_arguments(node.args)
            self.generic_visit(node)

        def visit_Lambda(self, node: ast.Lambda) -> None:
            self._visit_arguments(node.args)
            self.generic_visit(node)

        def _visit_arguments(self, arguments: ast.arguments) -> None:
            if any(
                argument.arg == protected_name
                for argument in (
                    *arguments.posonlyargs,
                    *arguments.args,
                    *arguments.kwonlyargs,
                )
            ) or (
                arguments.vararg is not None
                and arguments.vararg.arg == protected_name
            ) or (
                arguments.kwarg is not None
                and arguments.kwarg.arg == protected_name
            ):
                self.reject()

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            if node.name == protected_name:
                self.reject()
            self.generic_visit(node)

        def visit_Global(self, node: ast.Global) -> None:
            if protected_name in node.names:
                self.reject()

        def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
            if protected_name in node.names:
                self.reject()

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            if node.name == protected_name:
                self.reject()
            self.generic_visit(node)

        def visit_Attribute(self, node: ast.Attribute) -> None:
            if (
                form == "ATTRIBUTE"
                and node.attr == "TYPE_CHECKING"
                and isinstance(node.value, ast.Name)
                and node.value.id == "typing"
                and isinstance(node.ctx, (ast.Store, ast.Del))
            ):
                self.reject()
            self.generic_visit(node)

        def visit_MatchAs(self, node: ast.MatchAs) -> None:
            if node.name == protected_name:
                self.reject()
            self.generic_visit(node)

        def visit_MatchStar(self, node: ast.MatchStar) -> None:
            if node.name == protected_name:
                self.reject()
            self.generic_visit(node)

        def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
            if node.rest == protected_name:
                self.reject()
            self.generic_visit(node)

        def visit_TypeAlias(self, node: ast.AST) -> None:
            name = getattr(node, "name", None)
            if isinstance(name, ast.Name) and name.id == protected_name:
                self.reject()
            self.generic_visit(node)

    audit = BindingAudit()
    audit.visit(tree)
    if not audit.valid:
        return None

    if form == "ATTRIBUTE":
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and (
                node.attr == "TYPE_CHECKING"
                and isinstance(node.value, ast.Name)
                and node.value.id == "typing"
                and isinstance(node.ctx, (ast.Store, ast.Del))
            ):
                return None

    module_guards = {
        id(statement)
        for statement in tree.body
        if isinstance(statement, ast.If)
        and matches_typing_guard(statement.test, form)
    }
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.If)
            and matches_typing_guard(node.test, form)
            and id(node) not in module_guards
        ):
            return None

    return RecognizedTypingGuard(form, marker_statement)


def _safe_typing_guard_prefix_statement(
    statement: ast.stmt,
) -> bool:
    if isinstance(statement, ast.Pass):
        return True

    if (
        isinstance(statement, ast.Expr)
        and isinstance(
            statement.value,
            ast.Constant,
        )
        and type(statement.value.value) is str
    ):
        return True

    if isinstance(statement, ast.Assign):
        if (
            len(statement.targets) != 1
            or not isinstance(
                statement.targets[0],
                ast.Name,
            )
            or not isinstance(
                statement.value,
                ast.Constant,
            )
        ):
            return False

        binding = statement.targets[0].id

        return (
            binding.isidentifier()
            and not binding.startswith("__")
            and binding not in {
                "TYPE_CHECKING",
                "typing",
            }
            and type(
                statement.value.value
            ) in {
                type(None),
                bool,
                int,
                float,
                complex,
                str,
                bytes,
            }
        )

    return False


def _typing_guard_passive_initializer(
    tree: ast.AST,
) -> bool:
    if not isinstance(tree, ast.Module):
        return False

    allowed_types = {
        type(None),
        bool,
        int,
        float,
        complex,
        str,
        bytes,
    }

    for position, statement in enumerate(
        tree.body
    ):
        if isinstance(statement, ast.Pass):
            continue

        if (
            position == 0
            and isinstance(statement, ast.Expr)
            and isinstance(
                statement.value,
                ast.Constant,
            )
            and type(
                statement.value.value
            ) is str
        ):
            continue

        if isinstance(statement, ast.Assign):
            if (
                len(statement.targets) != 1
                or not isinstance(
                    statement.targets[0],
                    ast.Name,
                )
                or not isinstance(
                    statement.value,
                    ast.Constant,
                )
            ):
                return False

            binding = statement.targets[0].id

            if (
                not binding.isidentifier()
                or binding.startswith("__")
                or binding in {
                    "typing",
                    "TYPE_CHECKING",
                }
                or type(
                    statement.value.value
                ) not in allowed_types
            ):
                return False

            continue

        return False

    return True


def _typing_guard_parent_initializers(
    module_id: str,
) -> tuple[str, ...]:
    logical = (
        module_id.removesuffix(".__init__")
        if module_id.endswith(".__init__")
        else module_id
    )

    parts = logical.split(".")

    return tuple(
        ".".join(parts[:length]) + ".__init__"
        for length in range(1, len(parts))
    )


def type_only_candidate_statement_ids(
    tree: ast.AST,
    indexed_ids: frozenset[str],
) -> frozenset[int]:
    guard = recognize_typing_guard(
        tree,
        indexed_ids,
    )

    if (
        guard is None
        or not isinstance(tree, ast.Module)
    ):
        return frozenset()

    marker_position = next(
        (
            position
            for position, statement
            in enumerate(tree.body)
            if statement is guard.marker_statement
        ),
        None,
    )

    if marker_position is None:
        return frozenset()

    matching_guards = [
        (position, statement)
        for position, statement
        in enumerate(tree.body)
        if (
            isinstance(statement, ast.If)
            and matches_typing_guard(
                statement.test,
                guard.form,
            )
        )
    ]

    if len(matching_guards) != 1:
        return frozenset()

    guard_position, guard_statement = (
        matching_guards[0]
    )

    if guard_position <= marker_position:
        return frozenset()

    if not all(
        _safe_typing_guard_prefix_statement(
            statement
        )
        for statement in tree.body[
            marker_position + 1:
            guard_position
        ]
    ):
        return frozenset()

    selected: set[int] = set()

    for statement in guard_statement.body:
        if (
            not isinstance(statement, ast.Import)
            or len(statement.names) != 1
        ):
            continue

        alias = statement.names[0]
        parts = alias.name.split(".")

        if (
            alias.asname is None
            and len(parts) > 1
            and all(
                part.isidentifier()
                for part in parts
            )
        ):
            selected.add(id(statement))

    return frozenset(selected)

from __future__ import annotations

import ast


def _bounded_integer_arithmetic(
    expression: ast.AST,
    *,
    depth: int,
    node_budget: int,
) -> tuple[bool, int]:
    """Recognize bounded, exact built-in integer arithmetic only."""
    used = 0

    def calculate(
        node: ast.AST,
        node_depth: int,
    ) -> int | None:
        nonlocal used

        if node_depth > 16 or used >= node_budget:
            return None

        used += 1

        if type(node) is ast.Constant:
            if type(node.value) is not int:
                return None
            value = node.value

        elif type(node) is ast.UnaryOp:
            if type(node.op) not in (ast.UAdd, ast.USub):
                return None

            operand = calculate(
                node.operand,
                node_depth + 1,
            )
            if operand is None:
                return None

            value = (
                operand
                if type(node.op) is ast.UAdd
                else -operand
            )

        elif type(node) is ast.BinOp:
            if type(node.op) not in (
                ast.Add,
                ast.Sub,
                ast.Mult,
            ):
                return None

            left = calculate(node.left, node_depth + 1)
            if left is None:
                return None

            right = calculate(node.right, node_depth + 1)
            if right is None:
                return None

            if type(node.op) is ast.Add:
                value = left + right
            elif type(node.op) is ast.Sub:
                value = left - right
            else:
                value = left * right

        else:
            return None

        if value.bit_length() > 64:
            return None

        return value

    accepted = calculate(expression, depth) is not None
    return accepted, used


def _pure_literal_expression(expr: ast.AST) -> bool:
    pending: list[tuple[ast.AST, int, bool]] = [
        (expr, 0, False)
    ]
    visited = 0

    while pending:
        node, depth, hashable_required = pending.pop()
        visited += 1

        if visited > 256 or depth > 16:
            return False

        if type(node) is ast.Constant:
            if type(node.value) not in {
                type(None), bool, int, float,
                complex, str, bytes,
            }:
                return False
            continue

        if type(node) is ast.UnaryOp:
            if (
                type(node.op) not in (ast.UAdd, ast.USub)
                or type(node.operand) is not ast.Constant
                or type(node.operand.value)
                not in (int, float, complex)
            ):
                return False

            pending.append(
                (node.operand, depth + 1, hashable_required)
            )
            continue

        if type(node) is ast.BinOp:
            accepted, counted = _bounded_integer_arithmetic(
                node,
                depth=depth,
                node_budget=257 - visited,
            )

            visited += counted - 1

            if not accepted or visited > 256:
                return False

            continue

        if type(node) is ast.Tuple:
            pending.extend(
                (item, depth + 1, hashable_required)
                for item in reversed(node.elts)
            )
            continue

        if type(node) is ast.List:
            if hashable_required:
                return False

            pending.extend(
                (item, depth + 1, False)
                for item in reversed(node.elts)
            )
            continue

        if type(node) is ast.Set:
            if hashable_required:
                return False

            pending.extend(
                (item, depth + 1, True)
                for item in reversed(node.elts)
            )
            continue

        if type(node) is ast.Dict:
            if (
                hashable_required
                or len(node.keys) != len(node.values)
                or any(key is None for key in node.keys)
            ):
                return False

            for key, value in reversed(
                list(zip(node.keys, node.values))
            ):
                pending.append(
                    (value, depth + 1, False)
                )
                pending.append(
                    (key, depth + 1, True)
                )
            continue

        return False

    return True


def _safe_annassign(
    statement: ast.AnnAssign,
    annotation_semantics: str | None,
) -> bool:
    if (
        annotation_semantics not in {"DEFERRED", "STRINGIFIED"}
        or not isinstance(statement.target, ast.Name)
        or statement.simple != 1
        or not statement.target.id.isidentifier()
        or statement.target.id.startswith("__")
    ):
        return False
    return (
        statement.value is None
        or _pure_literal_expression(statement.value)
    )

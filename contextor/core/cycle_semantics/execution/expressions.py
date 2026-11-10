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

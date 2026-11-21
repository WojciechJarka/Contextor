from __future__ import annotations

import ast


def _exact_frozen_dataclass_decorator(
    decorator: ast.AST,
) -> bool:
    return (
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Name)
        and decorator.func.id == "dataclass"
        and not decorator.args
        and len(decorator.keywords) == 1
        and decorator.keywords[0].arg == "frozen"
        and isinstance(
            decorator.keywords[0].value,
            ast.Constant,
        )
        and decorator.keywords[0].value.value is True
        and type(
            decorator.keywords[0].value.value
        ) is bool
    )


def _restricted_defaultless_dataclass_field_call(
    node: ast.AST,
) -> str | None:
    if (
        type(node) is not ast.Call
        or type(node.func) is not ast.Name
        or not node.func.id.isidentifier()
        or node.func.id.startswith("__")
        or node.args
    ):
        return None

    seen: set[str] = set()

    for keyword in node.keywords:
        if (
            keyword.arg not in {"hash", "compare"}
            or keyword.arg in seen
            or type(keyword.value) is not ast.Constant
        ):
            return None

        value = keyword.value.value

        if keyword.arg == "hash":
            if type(value) not in {bool, type(None)}:
                return None
        elif type(value) is not bool:
            return None

        seen.add(keyword.arg)

    return node.func.id


def _restricted_dataclass_field_annotation(
    node: ast.AST,
) -> bool:
    if isinstance(node, ast.Name):
        return (
            node.id.isidentifier()
            and not node.id.startswith("__")
            and node.id != "ast"
        )

    if type(node) is ast.Attribute:
        return (
            type(node.value) is ast.Name
            and node.value.id == "ast"
            and node.attr == "AST"
        )

    if isinstance(node, ast.Constant):
        return type(node.value) is str

    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, ast.BitOr):
            return False

        if (
            isinstance(node.left, ast.Constant)
            and type(node.left.value) is type(None)
            and not isinstance(node.right, ast.BinOp)
        ):
            return _restricted_dataclass_field_annotation(
                node.right
            )

        if (
            isinstance(node.right, ast.Constant)
            and type(node.right.value) is type(None)
            and not isinstance(node.left, ast.BinOp)
        ):
            return _restricted_dataclass_field_annotation(
                node.left
            )

        return False

    if isinstance(node, ast.Tuple):
        return all(
            _restricted_dataclass_field_annotation(item)
            for item in node.elts
        )

    if isinstance(node, ast.Subscript):
        return (
            _restricted_dataclass_field_annotation(
                node.value
            )
            and _restricted_dataclass_field_annotation(
                node.slice
            )
        )

    return False

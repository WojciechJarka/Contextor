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


def _exact_restricted_dataclass_hash_field_call(
    node: ast.AST,
) -> bool:
    return (
        type(node) is ast.Call
        and type(node.func) is ast.Name
        and node.func.id == "field"
        and not node.args
        and len(node.keywords) == 1
        and node.keywords[0].arg == "hash"
        and type(node.keywords[0].value) is ast.Constant
        and type(node.keywords[0].value.value) is bool
        and node.keywords[0].value.value is False
    )


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

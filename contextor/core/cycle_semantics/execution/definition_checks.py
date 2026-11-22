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

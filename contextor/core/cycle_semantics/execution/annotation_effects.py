from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Mapping

from .class_facts import _ClassFact, _BUILTIN_TYPE_ID


@dataclass(frozen=True)
class _Scalar:
    value: object


@dataclass(frozen=True)
class _Type:
    identity: str
    generic: bool


@dataclass(frozen=True)
class _Class:
    identity: str


@dataclass(frozen=True)
class _Module:
    name: str


@dataclass(frozen=True)
class _Seq:
    kind: str
    items: tuple[object, ...]


@dataclass(frozen=True)
class _Alias:
    origin: _Type
    args: tuple[object, ...]


@dataclass(frozen=True)
class _TypeUnion:
    args: tuple[object, ...]


_GENERIC = frozenset({
    "list", "dict", "tuple", "set", "frozenset", "type",
})

_BUILTINS = {
    name: _Type("builtins." + name, name in _GENERIC)
    for name in (
        "bool", "bytes", "complex", "dict", "float",
        "frozenset", "int", "list", "object", "set",
        "str", "tuple", "type",
    )
}

# CPython 3.15.2 dataclasses._get_type_from_annotation.
_STRING_PATH = re.compile(
    r"^\s*(\w+(?:\s*\.\s*\w+)*)"
)

_MISSING = object()
_UNKNOWN = object()


def _value(
    v: object,
    namespaces: Mapping[str, Mapping[str, object]],
) -> object | None:
    if isinstance(v, _ClassFact):
        if v.origin == "BUILTIN":
            builtin = _BUILTINS.get(
                v.identity.removeprefix("builtins.")
            )
            if (
                builtin is not None
                and builtin.identity == v.identity
            ):
                return builtin

        if v.metaclass_identity == _BUILTIN_TYPE_ID:
            return _Class(v.identity)

        return None

    if type(v) is str:
        if v in namespaces:
            return _Module(v)

        if v.startswith("\x00PASSIVE_CLASS:"):
            return _Class(v)

        return None

    if isinstance(
        v,
        (
            _Scalar, _Type, _Class, _Module,
            _Seq, _Alias, _TypeUnion,
        ),
    ):
        return v

    return None


def _type_operand(v: object) -> bool:
    return (
        isinstance(
            v, (_Type, _Class, _Alias, _TypeUnion)
        )
        or (
            isinstance(v, _Scalar)
            and v.value is None
        )
    )


def _eval(
    expr: ast.expr,
    class_ns: Mapping[str, object],
    module_ns: Mapping[str, object],
    namespaces: Mapping[str, Mapping[str, object]],
) -> object | None:
    budget = 256

    def visit(
        n: ast.expr,
        depth: int,
    ) -> object | None:
        nonlocal budget

        budget -= 1
        if budget < 0 or depth > 16:
            return None

        if type(n) is ast.Constant:
            if type(n.value) not in (
                type(None), bool, int, float, complex,
                str, bytes, type(Ellipsis),
            ):
                return None
            return _Scalar(n.value)

        if (
            type(n) is ast.Name
            and type(n.ctx) is ast.Load
        ):
            if n.id in class_ns:
                return _value(class_ns[n.id], namespaces)

            if n.id in module_ns:
                return _value(module_ns[n.id], namespaces)

            return _BUILTINS.get(n.id)

        if (
            type(n) in (ast.List, ast.Tuple)
            and type(n.ctx) is ast.Load
        ):
            values = []

            for element in n.elts:
                value = visit(element, depth + 1)
                if value is None:
                    return None
                values.append(value)

            return _Seq(
                "tuple" if type(n) is ast.Tuple else "list",
                tuple(values),
            )

        if (
            type(n) is ast.Attribute
            and type(n.ctx) is ast.Load
        ):
            receiver = visit(n.value, depth + 1)

            if not isinstance(receiver, _Module):
                return None

            namespace = namespaces.get(receiver.name)

            if (
                namespace is None
                or n.attr not in namespace
            ):
                return None

            return _value(namespace[n.attr], namespaces)

        if (
            type(n) is ast.Subscript
            and type(n.ctx) is ast.Load
        ):
            receiver = visit(n.value, depth + 1)
            index = visit(n.slice, depth + 1)

            if receiver is None or index is None:
                return None

            if (
                isinstance(receiver, _Seq)
                and isinstance(index, _Scalar)
                and type(index.value) in (int, bool)
            ):
                try:
                    return receiver.items[index.value]
                except IndexError:
                    return None

            if (
                isinstance(receiver, _Type)
                and receiver.generic
            ):
                args = (
                    index.items
                    if (
                        isinstance(index, _Seq)
                        and index.kind == "tuple"
                    )
                    else (index,)
                )
                return _Alias(receiver, tuple(args))

            return None

        if type(n) is ast.BinOp:
            left = visit(n.left, depth + 1)
            right = visit(n.right, depth + 1)

            if left is None or right is None:
                return None

            if (
                type(n.op) is ast.BitOr
                and _type_operand(left)
                and _type_operand(right)
            ):
                return _TypeUnion((left, right))

            if (
                isinstance(left, _Scalar)
                and isinstance(right, _Scalar)
                and type(left.value) is int
                and type(right.value) is int
            ):
                if type(n.op) is ast.Add:
                    value = left.value + right.value
                elif type(n.op) is ast.Sub:
                    value = left.value - right.value
                elif type(n.op) is ast.Mult:
                    value = left.value * right.value
                else:
                    return None

                return (
                    _Scalar(value)
                    if value.bit_length() <= 64
                    else None
                )

            return None

        if type(n) is ast.UnaryOp:
            operand = visit(n.operand, depth + 1)

            if (
                not isinstance(operand, _Scalar)
                or type(operand.value) is not int
            ):
                return None

            if type(n.op) is ast.UAdd:
                value = +operand.value
            elif type(n.op) is ast.USub:
                value = -operand.value
            else:
                return None

            return (
                _Scalar(value)
                if value.bit_length() <= 64
                else None
            )

        if type(n) is ast.IfExp:
            condition = visit(n.test, depth + 1)

            if (
                not isinstance(condition, _Scalar)
                or type(condition.value) is not bool
            ):
                return None

            return visit(
                n.body if condition.value else n.orelse,
                depth + 1,
            )

        return None

    return visit(expr, 0)


def _text_attribute(
    receiver: object,
    name: str,
    namespaces: Mapping[
        str, Mapping[str, object]
    ],
) -> object:
    if not isinstance(receiver, _Module):
        return _UNKNOWN

    namespace = namespaces.get(receiver.name)
    if namespace is None:
        return _UNKNOWN

    if name in namespace:
        value = _value(namespace[name], namespaces)
        return value if value is not None else _UNKNOWN

    # A missing module attribute can reach module
    # __getattr__. Intrinsic module attributes also
    # cannot be inferred from the module dict alone.
    if "__getattr__" in namespace or name.startswith("__"):
        return _UNKNOWN

    return _MISSING


def _consume(
    value: object,
    module: str,
    namespaces: Mapping[
        str, Mapping[str, object]
    ],
) -> bool:
    if (
        not isinstance(value, _Scalar)
        or type(value.value) is not str
    ):
        return isinstance(
            value,
            (
                _Scalar, _Type, _Class, _Module,
                _Seq, _Alias, _TypeUnion,
            ),
        )

    match = _STRING_PATH.match(value.value)
    if match is None:
        return True

    receiver: object = _Module(module)

    for component in match.group(1).split("."):
        receiver = _text_attribute(
            receiver,
            component.strip(),
            namespaces,
        )

        if receiver is _UNKNOWN:
            return False

        if receiver is _MISSING:
            return True

    return isinstance(
        receiver,
        (
            _Scalar, _Type, _Class, _Module,
            _Seq, _Alias, _TypeUnion,
        ),
    )

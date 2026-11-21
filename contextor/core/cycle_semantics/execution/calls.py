from __future__ import annotations

from dataclasses import dataclass

from .steps import _Step


@dataclass(frozen=True, eq=False)
class _RestrictedFunction:
    defining_module: str
    body: tuple[_Step, ...]
    parameters: tuple[str, ...] = ()


@dataclass(frozen=True)
class _KnownBuiltinCallable:
    canonical_identity: str
    effect: str


_KNOWN_BUILTIN_CALLABLES = {
    "property": _KnownBuiltinCallable(
        "builtins.property", "PASSIVE_PROPERTY",
    ),
}


def _known_builtin_callable(
    name: str | None,
) -> _KnownBuiltinCallable | None:
    return _KNOWN_BUILTIN_CALLABLES.get(name)


def _resolve_known_builtin_callable(
    name: str | None,
    namespace: dict[str, object | None],
) -> _KnownBuiltinCallable | None:
    if name is None:
        return None
    value = (
        namespace[name]
        if name in namespace
        else _known_builtin_callable(name)
    )
    return (
        value
        if type(value) is _KnownBuiltinCallable
        else None
    )


@dataclass(frozen=True, eq=False)
class _DecoratorSnapshot:
    names: tuple[str, ...]
    values: tuple[object, ...]


def _snapshot_named_decorators(
    names: tuple[str, ...],
    namespace: dict[str, object | None],
) -> _DecoratorSnapshot | None:
    if not names:
        return None

    values: list[object] = []

    for name in names:
        if (
            not name
            or not name.isidentifier()
            or name.startswith("__")
            or name not in namespace
        ):
            return None

        values.append(namespace[name])

    return _DecoratorSnapshot(
        names=names,
        values=tuple(values),
    )


def _new_restricted_function(
    defining_module: str,
    body: tuple[_Step, ...],
    parameters: tuple[str, ...] = (),
) -> _RestrictedFunction:
    return _RestrictedFunction(
        defining_module=defining_module,
        body=body,
        parameters=parameters,
    )


def _execute_restricted_call(
    step: _Step,
    *,
    module: str,
    namespaces: dict[str, dict[str, object | None]],
    local_bindings: dict[str, object | None],
) -> tuple[_Step, ...] | None:
    value = namespaces[module].get(step.target)

    if (
        not isinstance(value, _RestrictedFunction)
        or value.defining_module != module
        or len(value.parameters)
        != len(step.call_argument_values)
    ):
        return None

    local_bindings.update(
        zip(
            value.parameters,
            step.call_argument_values,
        )
    )

    return value.body


def _execute_restricted_object_call(
    value: object,
    argument: object,
    *,
    module: str,
    local_bindings: dict[str, object | None],
) -> tuple[_Step, ...] | None:
    if (
        not isinstance(value, _RestrictedFunction)
        or value.defining_module != module
        or len(value.parameters) != 1
    ):
        return None

    local_bindings[value.parameters[0]] = argument
    return value.body

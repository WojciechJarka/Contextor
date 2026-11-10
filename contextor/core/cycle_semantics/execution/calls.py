from __future__ import annotations

from dataclasses import dataclass

from .steps import _Step


@dataclass(frozen=True, eq=False)
class _RestrictedFunction:
    defining_module: str
    body: tuple[_Step, ...]


def _new_restricted_function(
    defining_module: str,
    body: tuple[_Step, ...],
) -> _RestrictedFunction:
    return _RestrictedFunction(
        defining_module=defining_module,
        body=body,
    )


def _execute_restricted_call(
    step: _Step,
    *,
    module: str,
    namespaces: dict[str, dict[str, object | None]],
) -> tuple[_Step, ...] | None:
    value = namespaces[module].get(step.target)

    if (
        not isinstance(value, _RestrictedFunction)
        or value.defining_module != module
    ):
        return None

    return value.body

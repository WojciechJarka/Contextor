from __future__ import annotations

from dataclasses import dataclass

from .steps import _Step


@dataclass(frozen=True, eq=False)
class _RestrictedFunction:
    defining_module: str
    body: tuple[_Step, ...]
    parameters: tuple[str, ...] = ()


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

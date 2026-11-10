from __future__ import annotations

from typing import Literal

from .steps import _Step


def _execute_restricted_call(
    step: _Step,
    *,
    module: str,
    index: int,
    namespaces: dict[str, dict[str, object | None]],
    function_definitions: dict[
        str,
        dict[str, tuple[_Step, ...]],
    ],
    programs: dict[str, list[_Step]],
) -> Literal["ADVANCE", "RETURN_UNKNOWN"]:
    expected_binding = (
        "\x00FUNCTION:" + module + ":" + step.target
    )

    if (
        namespaces[module].get(step.target)
        != expected_binding
        or step.target not in function_definitions[module]
    ):
        return "RETURN_UNKNOWN"

    body_steps = function_definitions[module][step.target]

    programs[module][index + 1:index + 1] = list(body_steps)

    return "ADVANCE"

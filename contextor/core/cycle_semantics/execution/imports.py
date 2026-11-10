from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from typing import Literal

from .steps import _Step


def _chain(name: str) -> tuple[str, ...]:
    parts = name.split(".")

    return tuple(
        ".".join(parts[:index])
        for index in range(1, len(parts) + 1)
    )


def _missing_piece(
    name: str,
    states: Mapping[str, str],
) -> str | None:
    for piece in _chain(name):
        if piece not in states:
            return piece

        if states[piece] == "NEW":
            return piece

    return None


@dataclass(frozen=True)
class _ImportControl:
    action: Literal[
        "ADVANCE",
        "RETURN_UNKNOWN",
        "START_CHILD",
    ]
    target: str | None = None
    symbol: str | None = None
    event_operation: str | None = None


def _execute_ready_import(
    step: _Step,
    *,
    module: str,
    bootstrap: str,
    namespaces: dict[str, dict[str, object | None]],
) -> _ImportControl:
    target = step.target

    if module == bootstrap:
        return _ImportControl("ADVANCE")

    if step.explicit_alias and "." in target:
        parent, child = target.rsplit(".", 1)

        if namespaces[parent].get(child) != target:
            return _ImportControl(
                "RETURN_UNKNOWN",
                target=target,
                symbol=child,
            )

    binding_target = (
        target
        if step.explicit_alias
        else target.split(".")[0]
    )

    if not step.function_local and not step.class_local:
        namespaces[module][step.binding] = binding_target

    return _ImportControl(
        "ADVANCE",
        event_operation=(
            "FUNCTION_LOCAL_IMPORT"
            if step.function_local
            else "CLASS_LOCAL_IMPORT"
            if step.class_local
            else "IMPORT"
        ),
    )


def _execute_prepare_from_member(
    step: _Step,
    *,
    packages: set[str],
    programs: Mapping[str, object],
    states: Mapping[str, str],
    namespaces: Mapping[str, dict[str, object | None]],
    frames: list[tuple[str, int]],
) -> _ImportControl:
    target = step.target
    member = step.symbol

    if (
        target in packages
        and member not in namespaces[target]
    ):
        child = target + "." + member

        if child in programs:
            if states[child] == "NEW":
                if _missing_piece(child, states) != child:
                    return _ImportControl(
                        "RETURN_UNKNOWN",
                        target=child,
                        symbol=member,
                    )

                return _ImportControl(
                    "START_CHILD",
                    target=child,
                )

            if states[child] == "INITIALIZING":
                if not any(
                    active == child
                    for active, _ in frames
                ):
                    return _ImportControl(
                        "RETURN_UNKNOWN",
                        target=child,
                        symbol=member,
                    )

            elif states[child] == "READY":
                return _ImportControl(
                    "RETURN_UNKNOWN",
                    target=child,
                    symbol=member,
                )

    return _ImportControl(
        "ADVANCE",
        event_operation="PREPARE_FROM_MEMBER",
    )

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from typing import Mapping
from typing import Literal

from .steps import _Step
from .state import _FunctionFrame, _frame_module


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
        "REENTRANT_CHILD",
        "RETURN_OUTCOME",
    ]
    target: str | None = None
    symbol: str | None = None
    event_operation: str | None = None
    outcome: str | None = None


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
    frames: list[tuple[str, int] | _FunctionFrame],
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
                    _frame_module(frame) == child
                    for frame in frames
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


def _resolve_from_child(
    step: _Step,
    *,
    packages: set[str],
    programs: Mapping[str, object],
    states: Mapping[str, str],
    namespaces: Mapping[str, dict[str, object | None]],
    frames: list[tuple[str, int] | _FunctionFrame],
) -> _ImportControl:
    target = step.target
    member = step.symbol

    if target in packages and member not in namespaces[target]:
        child = target + "." + member

        if child in programs:
            if states[child] == "INITIALIZING":
                if not any(
                    _frame_module(frame) == child
                    for frame in frames
                ):
                    return _ImportControl(
                        "RETURN_UNKNOWN",
                        target=child,
                        symbol=member,
                    )

                return _ImportControl(
                    "REENTRANT_CHILD",
                    target=child,
                    symbol=member,
                )

            if states[child] != "NEW":
                return _ImportControl(
                    "RETURN_UNKNOWN",
                    target=child,
                    symbol=member,
                )

            next_child = _missing_piece(child, states)

            if next_child != child:
                return _ImportControl(
                    "RETURN_UNKNOWN",
                    target=child,
                    symbol=member,
                )

            return _ImportControl(
                "START_CHILD",
                target=child,
            )

    return _ImportControl("ADVANCE")


def _execute_from_binding(
    step: _Step,
    *,
    module: str,
    states: Mapping[str, str],
    namespaces: dict[str, dict[str, object | None]],
    class_namespace_admissible: Callable[[object], bool],
) -> _ImportControl:
    target = step.target
    member = step.symbol

    if member not in namespaces[target]:
        outcome = (
            "EARLY_BINDING_HAZARD"
            if states[target] == "INITIALIZING"
            else "MISSING_EXPORT"
        )

        return _ImportControl(
            "RETURN_OUTCOME",
            target=target,
            symbol=member,
            event_operation=outcome,
            outcome=outcome,
        )

    imported_value = namespaces[target][member]

    if (
        step.class_local
        and not class_namespace_admissible(imported_value)
    ):
        return _ImportControl(
            "RETURN_UNKNOWN",
            target=target,
            symbol=member,
        )

    if not step.function_local and not step.class_local:
        namespaces[module][step.binding] = imported_value

    return _ImportControl(
        "ADVANCE",
        target=target,
        symbol=member,
        event_operation=(
            "FUNCTION_LOCAL_FROM"
            if step.function_local
            else "CLASS_LOCAL_FROM"
            if step.class_local
            else "FROM"
        ),
    )


def _classify_external_import(
    step: _Step,
    *,
    module: str,
    bootstrap: str,
    programs: Mapping[str, object],
    indexed_roots: frozenset[str],
    assume_passive_external_imports: bool,
) -> Literal[
    "ASSUME",
    "UNKNOWN_CLASS_LOCAL",
    "UNKNOWN_UNMODELED",
]:
    target = step.target

    if (
        assume_passive_external_imports
        and target
        and target not in programs
        and module != bootstrap
        and target.split(".", 1)[0] not in indexed_roots
    ):
        if step.class_local:
            return "UNKNOWN_CLASS_LOCAL"

        return "ASSUME"

    return "UNKNOWN_UNMODELED"

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass
class _ModuleInitializationState:
    states: dict[str, str]
    namespaces: dict[str, dict[str, object | None]]


def _new_module_initialization_state(
    programs: Mapping[str, object],
) -> _ModuleInitializationState:
    return _ModuleInitializationState(
        states={
            name: "NEW"
            for name in programs
        },
        namespaces={
            name: {}
            for name in programs
        },
    )


@dataclass
class _ExecutionCursor:
    frames: list[tuple[str, int]]
    step_budget: int


def _new_execution_cursor(
    bootstrap: str,
) -> _ExecutionCursor:
    return _ExecutionCursor(
        frames=[(bootstrap, 0)],
        step_budget=10000,
    )

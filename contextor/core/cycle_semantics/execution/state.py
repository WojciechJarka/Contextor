from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .class_facts import _ClassFact, _BUILTIN_CLASS_FACTS
from .steps import _Step


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


@dataclass(frozen=True)
class _FunctionFrame:
    module: str
    index: int
    steps: tuple[_Step, ...]
    local_bindings: dict[str, object | None] = field(
        default_factory=dict,
        compare=False,
        repr=False,
    )
    result_binding: str | None = None
    decorator_final_binding: str | None = None
    remaining_decorators: tuple[
        tuple[str, object], ...
    ] = ()
    binding_module: str | None = None


def _frame_module(
    frame: tuple[str, int] | _FunctionFrame,
) -> str:
    if isinstance(frame, _FunctionFrame):
        return frame.module
    return frame[0]


def _frame_position(
    frame: tuple[str, int] | _FunctionFrame,
) -> tuple[str, int]:
    if isinstance(frame, _FunctionFrame):
        return frame.module, frame.index
    return frame


def _advance_frame(
    frame: tuple[str, int] | _FunctionFrame,
) -> tuple[str, int] | _FunctionFrame:
    if isinstance(frame, _FunctionFrame):
        return _FunctionFrame(
            frame.module,
            frame.index + 1,
            frame.steps,
            frame.local_bindings,
            frame.result_binding,
            frame.decorator_final_binding,
            frame.remaining_decorators,
            frame.binding_module,
        )
    return (frame[0], frame[1] + 1)


@dataclass
class _ExecutionCursor:
    frames: list[tuple[str, int] | _FunctionFrame]
    step_budget: int


def _new_execution_cursor(
    bootstrap: str,
) -> _ExecutionCursor:
    return _ExecutionCursor(
        frames=[(bootstrap, 0)],
        step_budget=10000,
    )


@dataclass
class _DefinitionState:
    prepared_class_bases: dict[
        str, tuple[tuple[_ClassFact, ...], _ClassFact]
    ]
    class_facts_by_identity: dict[str, _ClassFact]
    class_decorator_snapshots: dict[
        str,
        tuple[tuple[str, object], ...],
    ]


def _new_definition_state() -> _DefinitionState:
    return _DefinitionState(
        prepared_class_bases={},
        class_facts_by_identity={
            fact.identity: fact
            for fact in _BUILTIN_CLASS_FACTS.values()
        },
        class_decorator_snapshots={},
    )

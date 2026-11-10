from __future__ import annotations

from dataclasses import dataclass
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


@dataclass
class _DefinitionState:
    prepared_class_bases: dict[
        str, tuple[tuple[_ClassFact, ...], _ClassFact]
    ]
    class_facts_by_identity: dict[str, _ClassFact]
    function_definitions: dict[
        str,
        dict[str, tuple[_Step, ...]],
    ]


def _new_definition_state(
    programs: Mapping[str, object],
) -> _DefinitionState:
    return _DefinitionState(
        prepared_class_bases={},
        class_facts_by_identity={
            fact.identity: fact
            for fact in _BUILTIN_CLASS_FACTS.values()
        },
        function_definitions={
            name: {}
            for name in programs
        },
    )

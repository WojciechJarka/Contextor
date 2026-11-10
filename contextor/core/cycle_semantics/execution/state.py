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

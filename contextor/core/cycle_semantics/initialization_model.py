"""A deliberately restricted model of Python 3.10 flat-module import recursion.

Results are evidence about this explicitly supported subset, never a general
runtime proof or permission to suppress structural cycle warnings.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ModelStep:
    operation: str
    target: str | None = None
    symbol: str | None = None
    binding: str | None = None


@dataclass(frozen=True)
class ModelEvent:
    module: str
    operation: str
    target: str | None = None
    symbol: str | None = None


@dataclass(frozen=True)
class ImportOrderAssessment:
    entry_module: str
    outcome: str
    target_module: str | None
    symbol: str | None
    events: tuple[ModelEvent, ...]
    evidence_scope: str = "RESTRICTED_FLAT_MODULE_MODEL"


def _valid_name(name: str) -> bool:
    return bool(name) and name.isidentifier() and not name.startswith("__")


def _compile(tree: ast.Module) -> tuple[ModelStep, ...] | None:
    steps: list[ModelStep] = []
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                if not _valid_name(alias.name) or (
                    alias.asname is not None and not _valid_name(alias.asname)
                ):
                    return None
                steps.append(ModelStep(
                    "IMPORT_MODULE", alias.name,
                    binding=alias.asname or alias.name,
                ))
        elif isinstance(statement, ast.ImportFrom):
            if statement.level != 0 or not _valid_name(statement.module or ""):
                return None
            for alias in statement.names:
                if not _valid_name(alias.name) or (
                    alias.asname is not None and not _valid_name(alias.asname)
                ):
                    return None
                steps.append(ModelStep(
                    "IMPORT_NAME", statement.module, alias.name,
                    alias.asname or alias.name,
                ))
        elif isinstance(statement, ast.Assign):
            if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
                return None
            name = statement.targets[0].id
            if not _valid_name(name):
                return None
            value = statement.value
            if isinstance(value, ast.Constant) and type(value.value) in {
                type(None), bool, int, float, complex, str, bytes,
            }:
                steps.append(ModelStep("BIND_CONSTANT", binding=name))
            elif (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and _valid_name(value.value.id)
                and _valid_name(value.attr)
            ):
                steps.append(ModelStep(
                    "READ_ATTRIBUTE", value.value.id, value.attr, name,
                ))
            else:
                return None
        elif isinstance(statement, ast.Pass):
            continue
        else:
            return None
    return tuple(steps)


def evaluate_flat_import_order(
    modules: Mapping[str, ast.AST],
    entry_module: str,
) -> ImportOrderAssessment:
    """Evaluate one import order without evaluating any user-provided Python.

    MODEL_PASS covers only recognized flat modules, operations, and one order.
    Any unsupported AST is UNKNOWN, not a proof of failure or safety.
    """
    def result(
        outcome: str,
        target: str | None = None,
        symbol: str | None = None,
    ) -> ImportOrderAssessment:
        return ImportOrderAssessment(
            entry_module, outcome, target, symbol, tuple(events)
        )

    events: list[ModelEvent] = []
    if not isinstance(modules, Mapping) or not _valid_name(entry_module):
        return result("UNKNOWN")
    if entry_module not in modules:
        return result("UNKNOWN", entry_module)

    programs: dict[str, tuple[ModelStep, ...]] = {}
    for module, tree in modules.items():
        if not isinstance(module, str) or not _valid_name(module):
            return result("UNKNOWN")
        if not isinstance(tree, ast.Module):
            return result("UNKNOWN", module)
        compiled = _compile(tree)
        if compiled is None:
            return result("UNKNOWN", module)
        programs[module] = compiled

    states = {name: "NEW" for name in programs}
    bindings: dict[str, set[str]] = {name: set() for name in programs}
    aliases: dict[str, dict[str, str]] = {name: {} for name in programs}
    frames: list[tuple[str, int]] = [(entry_module, 0)]
    states[entry_module] = "INITIALIZING"

    while frames:
        module, index = frames[-1]
        program = programs[module]
        if index >= len(program):
            states[module] = "READY"
            frames.pop()
            events.append(ModelEvent(module, "READY"))
            continue

        step = program[index]
        if step.operation in {"IMPORT_MODULE", "IMPORT_NAME"}:
            target = step.target
            if target not in programs:
                return result("UNKNOWN", target)
            if states[target] == "NEW":
                states[target] = "INITIALIZING"
                events.append(ModelEvent(module, "START_IMPORT", target))
                frames.append((target, 0))
                continue
            if step.operation == "IMPORT_MODULE":
                bindings[module].add(step.binding)
                aliases[module][step.binding] = target
            else:
                if step.symbol not in bindings[target]:
                    outcome = (
                        "EARLY_BINDING_HAZARD"
                        if states[target] == "INITIALIZING"
                        else "MISSING_EXPORT"
                    )
                    events.append(ModelEvent(module, outcome, target, step.symbol))
                    return result(outcome, target, step.symbol)
                bindings[module].add(step.binding)
                aliases[module].pop(step.binding, None)
            events.append(ModelEvent(module, step.operation, target, step.symbol))
        elif step.operation == "BIND_CONSTANT":
            bindings[module].add(step.binding)
            aliases[module].pop(step.binding, None)
            events.append(ModelEvent(module, "BIND_CONSTANT", symbol=step.binding))
        elif step.operation == "READ_ATTRIBUTE":
            target = aliases[module].get(step.target)
            if target is None:
                return result("UNKNOWN", step.target, step.symbol)
            if step.symbol not in bindings[target]:
                outcome = (
                    "EARLY_BINDING_HAZARD"
                    if states[target] == "INITIALIZING"
                    else "MISSING_ATTRIBUTE"
                )
                events.append(ModelEvent(module, outcome, target, step.symbol))
                return result(outcome, target, step.symbol)
            bindings[module].add(step.binding)
            aliases[module].pop(step.binding, None)
            events.append(ModelEvent(module, "READ_ATTRIBUTE", target, step.symbol))
        else:
            return result("UNKNOWN")

        frames[-1] = (module, index + 1)

    return result("MODEL_PASS")

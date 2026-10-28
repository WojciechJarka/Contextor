"""Bounded SCC scenario analysis over an explicitly closed flat-module model.

This is deliberately not a safety certificate, publication policy or LIVE state.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass

from .initialization_model import ImportOrderAssessment, evaluate_flat_import_order
from .package_model import PackageImportAssessment, evaluate_package_import_order
from .model_source_closure import compute_cycle_model_source_closures
from .model_identity import indexed_to_logical_module, logical_to_indexed_module
from .package_graph_consistency import assess_package_graph_consistency
from .scc import CyclicImportComponent, ImportCycleTopology, analyze_import_cycle_topology

MAX_COMPONENT_ENTRIES = 64
MAX_CLOSURE_STATEMENTS = 4096
MAX_CLOSURE_AST_NODES = 16384


@dataclass(frozen=True)
class CycleComponentScenarios:
    members: tuple[str, ...]
    internal_edges: tuple[tuple[str, str], ...]
    classification: str
    coverage: str
    reason: str | None
    entry_assessments: tuple[ImportOrderAssessment | PackageImportAssessment, ...]
    evidence_scope: str = "CLOSED_FLAT_MODULE_FRESH_ENTRY_MODEL"
    model_kind: str = "FLAT_MODULE"


@dataclass(frozen=True)
class CycleScenarioReport:
    topology: ImportCycleTopology
    components: tuple[CycleComponentScenarios, ...]
    evidence_scope: str = "SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"


def _declared_import_targets(tree: ast.Module) -> set[str] | None:
    """Return syntactic targets; refuse relative/star or dotted imports."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not alias.name.isidentifier():
                    return None
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module or not node.module.isidentifier():
                return None
            if any(alias.name == "*" for alias in node.names):
                return None
            found.add(node.module)
    return found


def _closure(
    members: tuple[str, ...], adjacency: Mapping[str, frozenset[str]]
) -> set[str]:
    visited = set(members)
    pending = list(members)
    while pending:
        for target in adjacency[pending.pop()]:
            if target not in visited:
                visited.add(target)
                pending.append(target)
    return visited


def _component_result(
    component: CyclicImportComponent,
    classification: str,
    *,
    coverage: str,
    reason: str | None = None,
    assessments: tuple[ImportOrderAssessment | PackageImportAssessment, ...] = (),
    model_kind: str = "FLAT_MODULE",
) -> CycleComponentScenarios:
    return CycleComponentScenarios(
        members=component.members,
        internal_edges=component.internal_edges,
        classification=classification,
        coverage=coverage,
        reason=reason,
        entry_assessments=assessments,
        evidence_scope=(
            "CLOSED_REGULAR_PACKAGE_FRESH_ENTRY_MODEL"
            if model_kind == "REGULAR_PACKAGE"
            else "CLOSED_FLAT_MODULE_FRESH_ENTRY_MODEL"
        ),
        model_kind=model_kind,
    )


def analyze_cycle_scenarios(
    hard_edges: Mapping[str, set[str] | frozenset[str] | list[str] | tuple[str, ...]],
    modules: Mapping[str, ast.AST],
) -> CycleScenarioReport:
    """Analyze every fresh entry module of each cyclic SCC, without executing code.

    Source-to-graph edge equality is required for the entire reachable closure.
    Missing, dynamic and unsupported semantics yield INDETERMINATE, never safe.
    """
    topology = analyze_import_cycle_topology(hard_edges)
    if not isinstance(modules, Mapping):
        raise TypeError("modules must be a mapping")

    adjacency = {name: frozenset(targets) for name, targets in hard_edges.items()}
    for targets in tuple(adjacency.values()):
        for target in targets:
            adjacency.setdefault(target, frozenset())

    output: list[CycleComponentScenarios] = []
    closures = compute_cycle_model_source_closures(hard_edges)
    for component, source_closure in zip(topology.cyclic_components, closures):
        if len(component.members) > MAX_COMPONENT_ENTRIES:
            output.append(_component_result(
                component, "INDETERMINATE", coverage="NONE",
                reason="ENTRY_BUDGET_EXCEEDED",
            ))
            continue

        reachable = set(source_closure.evidence_source_modules)
        if any(name not in modules or not isinstance(modules[name], ast.Module)
               for name in reachable):
            output.append(_component_result(
                component, "INDETERMINATE", coverage="NONE",
                reason="MISSING_OR_INVALID_SOURCE",
            ))
            continue

        if sum(len(modules[name].body) for name in reachable) > MAX_CLOSURE_STATEMENTS:
            output.append(_component_result(
                component, "INDETERMINATE", coverage="NONE",
                reason="STATEMENT_BUDGET_EXCEEDED",
            ))
            continue

        # A single top-level statement can contain an arbitrarily large AST.
        ast_budget = MAX_CLOSURE_AST_NODES
        for name in sorted(reachable):
            for _ in ast.walk(modules[name]):
                ast_budget -= 1
                if ast_budget < 0:
                    break
            if ast_budget < 0:
                break
        if ast_budget < 0:
            output.append(_component_result(
                component, "INDETERMINATE", coverage="NONE",
                reason="AST_NODE_BUDGET_EXCEEDED",
            ))
            continue

        # The graph and AST must describe the exact same import targets.
        # No name-based exceptions and no guessed package resolution.
        flat_applicable = all(
            name.isidentifier() and not name.startswith("__")
            for name in reachable
        ) and not any(
            _declared_import_targets(modules[name]) != set(adjacency[name])
            for name in reachable
        )

        sources = {name: modules[name] for name in sorted(reachable)}
        model_kind = "FLAT_MODULE"
        if flat_applicable:
            assessments = tuple(
                evaluate_flat_import_order(sources, entry)
                for entry in component.members
            )
        else:
            if not any("." in name for name in reachable):
                output.append(_component_result(
                    component, "INDETERMINATE", coverage="NONE",
                    reason="GRAPH_SOURCE_IMPORT_MISMATCH",
                ))
                continue
            consistency = assess_package_graph_consistency(
                hard_edges, sources, source_closure.evidence_source_modules,
            )
            if consistency.status != "CONSISTENT":
                output.append(_component_result(
                    component, "INDETERMINATE", coverage="NONE",
                    reason=consistency.reason,
                    model_kind="REGULAR_PACKAGE",
                ))
                continue
            indexed = frozenset(hard_edges)
            if any(
                logical_to_indexed_module(indexed_to_logical_module(member), indexed)
                != member
                for member in component.members
            ):
                output.append(_component_result(
                    component, "INDETERMINATE", coverage="NONE",
                    reason="AMBIGUOUS_PACKAGE_TARGET",
                    model_kind="REGULAR_PACKAGE",
                ))
                continue
            model_kind = "REGULAR_PACKAGE"
            assessments = tuple(
                evaluate_package_import_order(
                    sources, indexed_to_logical_module(entry),
                )
                for entry in component.members
            )
        member_set = set(component.members)
        internal_hazard = any(
            result.outcome == "EARLY_BINDING_HAZARD"
            and result.events
            and result.events[-1].operation == "EARLY_BINDING_HAZARD"
            and (
                logical_to_indexed_module(result.events[-1].module, frozenset(hard_edges))
                if model_kind == "REGULAR_PACKAGE" else result.events[-1].module
            ) in member_set
            and (
                logical_to_indexed_module(result.events[-1].target, frozenset(hard_edges))
                if model_kind == "REGULAR_PACKAGE" else result.events[-1].target
            ) in member_set
            and result.events[-1].target == result.target_module
            for result in assessments
        )
        if internal_hazard:
            classification = "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
        elif all(result.outcome == "MODEL_PASS" for result in assessments):
            classification = "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        else:
            classification = "INDETERMINATE"

        coverage = (
            "COMPLETE_FRESH_MEMBER_ENTRIES"
            if all(result.outcome != "UNKNOWN" for result in assessments)
            else "PARTIAL_FRESH_MEMBER_ENTRIES"
        )
        reason = (
            "UNRESOLVED_SCENARIO"
            if classification == "INDETERMINATE"
            else None
        )
        output.append(_component_result(
            component, classification, coverage=coverage,
            reason=reason, assessments=assessments,
            model_kind=model_kind,
        ))

    return CycleScenarioReport(topology, tuple(output))

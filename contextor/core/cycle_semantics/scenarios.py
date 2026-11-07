"""Bounded SCC scenario analysis over an explicitly closed flat-module model.

This is deliberately not a safety certificate, publication policy or LIVE state.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass, replace

from .initialization_model import ImportOrderAssessment, evaluate_flat_import_order
from .package_model import (
    PackageImportAssessment,
    _PackageSourceSession,
    evaluate_package_import_order,
)
from .model_source_closure import (
    CycleModelSourceClosure,
    compute_cycle_model_source_closures,
    compute_cycle_model_source_closures_with_optional_children,
)
from .model_identity import indexed_to_logical_module, logical_to_indexed_module
from .package_graph_consistency import assess_package_graph_consistency
from .scc import CyclicImportComponent, ImportCycleTopology, analyze_import_cycle_topology

MAX_COMPONENT_ENTRIES = 64
MAX_CLOSURE_STATEMENTS = 4096
MAX_CLOSURE_AST_NODES = 393216


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
    *,
    source_selection: str = "HARD_ONLY",
    indexed_imports_by_module: Mapping[str, object] | None = None,
    package_root: str | None = None,
    source_closures: tuple[CycleModelSourceClosure, ...] | None = None,
) -> CycleScenarioReport:
    """Analyze every fresh entry module of each cyclic SCC, without executing code.

    Source-to-graph edge equality is required for the entire reachable closure.
    Missing, dynamic and unsupported semantics yield INDETERMINATE, never safe.
    """
    topology = analyze_import_cycle_topology(hard_edges)
    if not isinstance(modules, Mapping):
        raise TypeError("modules must be a mapping")

    if source_selection not in ("HARD_ONLY", "OPTIONAL_NAMED_CHILDREN"):
        raise ValueError("SOURCE_SELECTION_INVALID")

    if source_selection == "HARD_ONLY" and (
        indexed_imports_by_module is not None
        or package_root is not None
        or source_closures is not None
    ):
        raise ValueError("HARD_ONLY_OPTIONAL_INPUTS_UNSUPPORTED")

    def report(
        components: tuple[CycleComponentScenarios, ...],
    ) -> CycleScenarioReport:
        if source_selection == "HARD_ONLY":
            return CycleScenarioReport(topology, components)
        return CycleScenarioReport(
            topology=topology,
            components=tuple(
                replace(
                    component,
                    evidence_scope=(
                        "CLOSED_REGULAR_PACKAGE_OPTIONAL_NAMED_CHILDREN_FRESH_ENTRY_MODEL"
                        if component.model_kind == "REGULAR_PACKAGE"
                        else "CLOSED_FLAT_MODULE_OPTIONAL_NAMED_CHILDREN_FRESH_ENTRY_MODEL"
                    ),
                )
                for component in components
            ),
            evidence_scope=(
                "OPTIONAL_NAMED_CHILDREN_SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
            ),
        )

    adjacency = {name: frozenset(targets) for name, targets in hard_edges.items()}
    for targets in tuple(adjacency.values()):
        for target in targets:
            adjacency.setdefault(target, frozenset())

    output: list[CycleComponentScenarios] = []
    if source_selection == "HARD_ONLY":
        closures = compute_cycle_model_source_closures(hard_edges)
    else:
        try:
            if (
                not isinstance(indexed_imports_by_module, Mapping)
                or type(source_closures) is not tuple
                or any(type(row) is not CycleModelSourceClosure
                       for row in source_closures)
            ):
                raise ValueError("Invalid optional cohort input")
            expected = compute_cycle_model_source_closures_with_optional_children(
                hard_edges,
                indexed_imports_by_module,
                package_root=package_root,
            )
            if (
                source_closures != expected
                or len(expected) != len(topology.cyclic_components)
                or any(
                    row.members != component.members
                    for row, component in zip(
                        expected, topology.cyclic_components
                    )
                )
            ):
                raise ValueError("Optional cohort identity mismatch")
            closures = expected
        except (TypeError, ValueError, AttributeError):
            return report(tuple(
                _component_result(
                    component,
                    "INDETERMINATE",
                    coverage="NONE",
                    reason="OPTIONAL_COHORT_IDENTITY_MISMATCH",
                )
                for component in topology.cyclic_components
            ))

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

        if any(
            getattr(node, "is_lazy", False)
            for name in reachable
            for node in ast.walk(modules[name])
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ):
            output.append(_component_result(
                component, "INDETERMINATE", coverage="NONE",
                reason="UNMODELED_EXPLICIT_LAZY_IMPORT",
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
            deferred_external_only = (
                consistency.status == "INDETERMINATE"
                and consistency.reason
                == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
                and consistency.internal_graph_state
                == "INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES"
                and consistency.checked_source_modules
                == tuple(sorted(
                    source_closure.evidence_source_modules
                ))
                and consistency.external_execution_gate
                == "LEXICALLY_DEFERRED_ONLY"
                and bool(consistency.unmodeled_external_imports)
                and not consistency.unmodeled_namespace_parents
                and len(consistency.external_scope_records)
                == len(consistency.unmodeled_external_imports)
                and all(
                    row.primary_scope in {
                        "FUNCTION_BODY",
                        "ASYNC_FUNCTION_BODY",
                        "METHOD_BODY",
                    }
                    for row in consistency.external_scope_records
                )
            )
            if (
                consistency.status != "CONSISTENT"
                and not deferred_external_only
            ):
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
            session = _PackageSourceSession()
            assessments = tuple(
                evaluate_package_import_order(
                    sources,
                    indexed_to_logical_module(entry),
                    _session=session,
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

    return report(tuple(output))

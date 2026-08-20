"""
contextor/core/analysis/refresh_planner.py

Stage 3C.1a — Pure Semantic RefreshPlanner with Clean Execution Contract.
"""

from typing import Dict, Optional, Tuple, Set, Mapping

from contextor.core.analysis.state_manager import FileDelta
from contextor.core.domain.refresh_plan import RefreshPlan
from contextor.core.domain.usage_facts import UsageDelta, ModuleUsageFacts


def _find_dependent_consumers(
    module_path: str,
    usages: Mapping[str, ModuleUsageFacts],
) -> Set[str]:
    """
    Identifies existing consumers in RAM that reference module_path or any of its definitions.
    Uses semantic alias resolution and exact module dot/colon separation (no broad stem guessing).
    Inspects all usage families: imports, aliases targets, direct_calls, runtime_calls,
    qualified_refs, callback_calls, event_bindings, inheritance_refs.
    """
    from contextor.core.reference.resolution import _resolve_alias

    recompute_set: Set[str] = set()
    if not usages:
        return recompute_set

    for c_path, c_facts in usages.items():
        if c_path == module_path:
            continue
        c_aliases = dict(c_facts.aliases)

        raw_refs = (
            list(c_facts.direct_calls)
            + list(c_facts.runtime_calls)
            + list(c_facts.qualified_refs)
            + list(c_facts.callback_calls)
            + list(c_facts.event_bindings)
            + list(c_facts.imports)
            + [base for _, base in c_facts.inheritance_refs if base]
            + [tgt for _, tgt in c_facts.aliases if tgt]
        )

        for ref in raw_refs:
            resolved = _resolve_alias(ref, c_aliases)
            if (
                resolved == module_path
                or resolved.startswith(f"{module_path}.")
                or resolved.startswith(f"{module_path}::")
            ):
                recompute_set.add(c_path)
                break

    return recompute_set


class RefreshPlanner:
    """
    Pure, deterministic planner that computes an explicit RefreshPlan
    from an incremental FileDelta / UsageDelta and cached module facts.

    The planner does NOT perform file I/O, AST parsing, or state mutations.
    `reparse_modules` represents ADDITIONAL modules requiring source parsing
    during plan execution.
    """

    @staticmethod
    def plan_refresh(
        delta: Optional[FileDelta],
        usage_delta: Optional[UsageDelta] = None,
        module_usages: Optional[Mapping[str, ModuleUsageFacts]] = None,
        collision_facts_changed: bool = False,
    ) -> RefreshPlan:

        """
        Pure planning function mapping canonical/delta facts to a RefreshPlan.
        """
        if (
            (delta is None or delta.is_empty)
            and (usage_delta is None or usage_delta.is_empty)
            and not collision_facts_changed
        ):
            return RefreshPlan(
                reparse_modules=(),
                recompute_modules=(),
                patch_families=(),
                graph_recomputations=(),
                refresh_completeness="complete",
                semantic_certainty="statically_resolved",
                reason="No-op: no file or usage changes detected.",
            )

        module_path = delta.module_path if delta else (usage_delta.module_path if usage_delta else "")
        usages = module_usages if module_usages is not None else {}

        # 1. Module Deletion
        if delta and delta.is_deleted:
            recompute_set = _find_dependent_consumers(module_path, usages)

            patch_families = [
                "modules",
                "definitions",
                "identity_registry",
                "module_usages",
                "dependency_graph",
                "artifact_consumption",
                "cached_analytics",
                "collision_facts",
                "collisions",
            ]

            return RefreshPlan(
                reparse_modules=(),
                recompute_modules=tuple(sorted(recompute_set)),
                patch_families=tuple(patch_families),
                graph_recomputations=("macro_metrics", "reverse_blast_radius", "advanced_graph_metrics", "cycles"),
                refresh_completeness="complete",
                semantic_certainty="statically_resolved",
                reason=f"Module DELETE for '{module_path}'.",
            )

        # 2. Module Addition
        if delta and delta.is_new:
            recompute_set = _find_dependent_consumers(module_path, usages)

            patch_families = [
                "modules",
                "definitions",
                "identity_registry",
                "module_usages",
                "dependency_graph",
                "artifact_consumption",
                "cached_analytics",
                "collision_facts",
                "collisions",
            ]
            return RefreshPlan(
                reparse_modules=(),
                recompute_modules=tuple(sorted(recompute_set)),
                patch_families=tuple(patch_families),
                graph_recomputations=("macro_metrics", "reverse_blast_radius", "advanced_graph_metrics", "cycles"),
                refresh_completeness="complete",
                semantic_certainty="statically_resolved",
                reason=f"Module ADD for '{module_path}'.",
            )

        # 3. Pure Semantic No-op
        if (delta is None or delta.is_empty) and (usage_delta is None or usage_delta.is_empty) and not collision_facts_changed:
            return RefreshPlan(
                reparse_modules=(),
                recompute_modules=(),
                patch_families=(),
                graph_recomputations=(),
                refresh_completeness="complete",
                semantic_certainty="statically_resolved",
                reason=f"No semantic changes in '{module_path}'.",
            )

        # 4. Alias / Re-export Retargeting
        has_alias_reexport_change = False

        if usage_delta and (usage_delta.added_aliases or usage_delta.removed_aliases):
            has_alias_reexport_change = True

        has_import_changes = False
        if delta and (delta.imports_added or delta.imports_removed or delta.imports_changed):
            has_import_changes = True
        if usage_delta and (usage_delta.added_imports or usage_delta.removed_imports):
            has_import_changes = True

        if has_alias_reexport_change:
            recompute_set = set()
            if usages:
                for c_path, c_facts in usages.items():
                    if c_path == module_path:
                        continue
                    if c_facts.aliases or c_facts.direct_calls or c_facts.qualified_refs:
                        recompute_set.add(c_path)

            patch_families = ["definitions", "module_usages", "artifact_consumption"]
            graph_recomputations = []
            if has_import_changes:
                patch_families.extend(["modules", "dependency_graph"])
                graph_recomputations.extend(["macro_metrics", "reverse_blast_radius", "advanced_graph_metrics", "cycles"])
            patch_families.append("cached_analytics")
            if collision_facts_changed:
                patch_families.extend(["collision_facts", "collisions"])

            return RefreshPlan(
                reparse_modules=(),
                recompute_modules=tuple(sorted(recompute_set)),
                patch_families=tuple(patch_families),
                graph_recomputations=tuple(graph_recomputations),
                refresh_completeness="complete",
                semantic_certainty="statically_resolved",
                reason=f"Alias/re-export change in '{module_path}'.",
            )

        # 5. Generic Import Changes (without alias changes)
        if has_import_changes:
            patch_families = [
                "modules",
                "definitions",
                "module_usages",
                "dependency_graph",
                "artifact_consumption",
                "cached_analytics",
            ]
            if collision_facts_changed:
                patch_families.extend(["collision_facts", "collisions"])

            return RefreshPlan(
                reparse_modules=(),
                recompute_modules=(),
                patch_families=tuple(patch_families),
                graph_recomputations=("macro_metrics", "reverse_blast_radius", "advanced_graph_metrics", "cycles"),
                refresh_completeness="complete",
                semantic_certainty="statically_resolved",
                reason=f"Import changes in '{module_path}'.",
            )

        # 6. Symbol Add / Remove / Change
        if delta and (delta.artifacts_added or delta.artifacts_removed or delta.artifacts_changed):
            recompute_set = _find_dependent_consumers(module_path, usages)

            patch_families = ["definitions", "identity_registry", "module_usages", "artifact_consumption"]
            if bool(delta.artifacts_added or delta.artifacts_removed) or (usage_delta and not usage_delta.is_empty):
                patch_families.append("cached_analytics")
            if collision_facts_changed:
                patch_families.extend(["collision_facts", "collisions"])

            return RefreshPlan(
                reparse_modules=(),
                recompute_modules=tuple(sorted(recompute_set)),
                patch_families=tuple(patch_families),
                graph_recomputations=(),
                refresh_completeness="complete",
                semantic_certainty="statically_resolved",
                reason=f"Artifact definitions change in '{module_path}'.",
            )

        # 7. Default: Body-only Usage Change or Collision-only change
        has_usage = bool(usage_delta and not usage_delta.is_empty)
        patch_families = []
        if has_usage:
            patch_families = ["module_usages", "artifact_consumption", "cached_analytics"]
        if collision_facts_changed:
            patch_families.extend(["collision_facts", "collisions"])

        reason = f"Body-only usage change in '{module_path}'." if has_usage else f"Collision facts update for '{module_path}'."

        return RefreshPlan(
            reparse_modules=(),
            recompute_modules=(),
            patch_families=tuple(patch_families),
            graph_recomputations=(),
            refresh_completeness="complete",
            semantic_certainty="statically_resolved",
            reason=reason,
        )

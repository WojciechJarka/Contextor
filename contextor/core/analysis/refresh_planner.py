"""
contextor/core/analysis/refresh_planner.py

Stage 3C.1a — Pure Semantic RefreshPlanner with Clean Execution Contract.
"""

from typing import Dict, Optional, Tuple, Set, Mapping

from contextor.core.analysis.state_manager import FileDelta
from contextor.core.domain.refresh_plan import RefreshPlan
from contextor.core.domain.usage_facts import UsageDelta, ModuleUsageFacts


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
        delta: FileDelta,
        usage_delta: Optional[UsageDelta] = None,
        module_usages: Optional[Mapping[str, ModuleUsageFacts]] = None,
    ) -> RefreshPlan:

        """
        Pure planning function mapping canonical/delta facts to a RefreshPlan.
        """
        if not delta and (usage_delta is None or usage_delta.is_empty):
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
            from contextor.core.reference.resolution import _resolve_alias
            recompute_set = set()
            if usages:
                mod_stem = module_path.rsplit(".", 1)[0] if "." in module_path else module_path
                for c_path, c_facts in usages.items():
                    if c_path == module_path:
                        continue
                    c_aliases = dict(c_facts.aliases)
                    for call in c_facts.direct_calls + c_facts.qualified_refs + c_facts.runtime_calls:
                        resolved = _resolve_alias(call, c_aliases)
                        if (
                            call == module_path
                            or call.startswith(module_path + ".")
                            or call == mod_stem
                            or call.startswith(mod_stem + ".")
                            or resolved == module_path
                            or resolved.startswith(module_path + ".")
                            or resolved == mod_stem
                            or resolved.startswith(mod_stem + ".")
                        ):
                            recompute_set.add(c_path)

            return RefreshPlan(
                reparse_modules=(),
                recompute_modules=tuple(sorted(recompute_set)),
                patch_families=(
                    "modules",
                    "definitions",
                    "identity_registry",
                    "module_usages",
                    "dependency_graph",
                    "artifact_consumption",
                ),
                graph_recomputations=("macro_metrics", "reverse_blast_radius"),
                refresh_completeness="complete",
                semantic_certainty="statically_resolved",
                reason=f"Module DELETE for '{module_path}'.",
            )

        # 2. Module Addition
        if delta and delta.is_new:
            return RefreshPlan(
                reparse_modules=(),
                recompute_modules=(),
                patch_families=(
                    "modules",
                    "definitions",
                    "identity_registry",
                    "module_usages",
                    "dependency_graph",
                    "artifact_consumption",
                ),
                graph_recomputations=("macro_metrics", "reverse_blast_radius"),
                refresh_completeness="complete",
                semantic_certainty="statically_resolved",
                reason=f"Module ADD for '{module_path}'.",
            )

        # 3. Alias / Re-export Retargeting
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

            patch_families = ["module_usages", "artifact_consumption"]
            graph_recomputations = []
            if has_import_changes:
                patch_families.append("dependency_graph")
                graph_recomputations.extend(["macro_metrics", "reverse_blast_radius"])

            return RefreshPlan(
                reparse_modules=(),
                recompute_modules=tuple(sorted(recompute_set)),
                patch_families=tuple(patch_families),
                graph_recomputations=tuple(graph_recomputations),
                refresh_completeness="complete",
                semantic_certainty="statically_resolved",
                reason=f"Alias/re-export change in '{module_path}'.",
            )

        # 4. Generic Import Changes (without alias changes)
        if has_import_changes:
            return RefreshPlan(
                reparse_modules=(),
                recompute_modules=(),
                patch_families=(
                    "module_usages",
                    "dependency_graph",
                    "artifact_consumption",
                ),
                graph_recomputations=("macro_metrics", "reverse_blast_radius"),
                refresh_completeness="complete",
                semantic_certainty="statically_resolved",
                reason=f"Import changes in '{module_path}'.",
            )

        # 5. Symbol Add / Remove / Change
        if delta and (delta.artifacts_added or delta.artifacts_removed or delta.artifacts_changed):
            recompute_set = set()
            if delta.artifacts_removed and usages:
                removed_set = set(delta.artifacts_removed)
                for c_path, c_facts in usages.items():
                    if c_path == module_path:
                        continue
                    for call in c_facts.direct_calls + c_facts.qualified_refs:
                        if call in removed_set or any(call.endswith("." + r) for r in removed_set):
                            recompute_set.add(c_path)

            return RefreshPlan(
                reparse_modules=(),
                recompute_modules=tuple(sorted(recompute_set)),
                patch_families=(
                    "definitions",
                    "identity_registry",
                    "module_usages",
                    "artifact_consumption",
                ),
                graph_recomputations=(),
                refresh_completeness="complete",
                semantic_certainty="statically_resolved",
                reason=f"Artifact definitions change in '{module_path}'.",
            )


        # 6. Default: Body-only Usage Change
        return RefreshPlan(
            reparse_modules=(),
            recompute_modules=(),
            patch_families=("module_usages", "artifact_consumption"),
            graph_recomputations=(),
            refresh_completeness="complete",
            semantic_certainty="statically_resolved",
            reason=f"Body-only usage change in '{module_path}'.",
        )

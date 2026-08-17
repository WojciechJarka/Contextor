"""
contextor/core/domain/refresh_plan.py

Stage 3C.1 — Semantic RefreshPlan Model.
"""

from dataclasses import dataclass, field
from typing import Tuple, Literal

RefreshCompleteness = Literal["complete", "conservative", "requires_resync"]
SemanticCertainty = Literal["statically_resolved", "runtime_unresolved"]

VALID_REFRESH_COMPLETENESS = {"complete", "conservative", "requires_resync"}
VALID_SEMANTIC_CERTAINTY = {"statically_resolved", "runtime_unresolved"}

VALID_PATCH_FAMILIES = {
    "modules",
    "definitions",
    "module_usages",
    "artifact_consumption",
    "dependency_graph",
    "identity_registry",
    "cached_analytics",
}


VALID_GRAPH_RECOMPUTATIONS = {
    "macro_metrics",
    "reverse_blast_radius",
    "advanced_graph_metrics",
}



@dataclass(frozen=True)
class RefreshPlan:
    """
    Immutable value-oriented refresh plan produced by RefreshPlanner.
    """

    reparse_modules: Tuple[str, ...] = ()
    recompute_modules: Tuple[str, ...] = ()
    patch_families: Tuple[str, ...] = ()
    graph_recomputations: Tuple[str, ...] = ()
    refresh_completeness: str = "complete"
    semantic_certainty: str = "statically_resolved"
    reason: str = ""

    def __post_init__(self):
        if self.refresh_completeness not in VALID_REFRESH_COMPLETENESS:
            raise ValueError(f"Invalid refresh_completeness: {self.refresh_completeness}")
        if self.semantic_certainty not in VALID_SEMANTIC_CERTAINTY:
            raise ValueError(f"Invalid semantic_certainty: {self.semantic_certainty}")
        for pf in self.patch_families:
            if pf not in VALID_PATCH_FAMILIES:
                raise ValueError(f"Invalid patch_family: {pf}")
        for gr in self.graph_recomputations:
            if gr not in VALID_GRAPH_RECOMPUTATIONS:
                raise ValueError(f"Invalid graph_recomputation: {gr}")

    @property
    def is_empty(self) -> bool:
        return (
            not self.reparse_modules
            and not self.recompute_modules
            and not self.patch_families
            and not self.graph_recomputations
        )


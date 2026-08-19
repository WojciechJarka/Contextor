"""
contextor/core/analysis/incremental

Subpackage for modular incremental architecture analysis.
"""

from .graph_ops import (
    LocalDegreeDeltaResult,
    calculate_affected_set,
    calculate_degree_deltas,
)
from .materialization import (
    ensure_module_usages,
    ensure_topology_analytics,
    ensure_cached_analytics,
    materialize_incremental_state,
)
from .preparation import (
    PreparedSourceUpdate,
    extract_artifact_names,
    calculate_file_delta,
    prepare_source_update,
    prepare_deleted_module_update,
)
from .plan_executor import (
    CandidateState,
    PlanExecutionOutcome,
    execute_refresh_plan,
)
from .engine import (
    IncrementalUpdateResult,
    IncrementalAnalysisEngine,
)

__all__ = [
    "LocalDegreeDeltaResult",
    "calculate_affected_set",
    "calculate_degree_deltas",
    "ensure_module_usages",
    "ensure_topology_analytics",
    "ensure_cached_analytics",
    "materialize_incremental_state",
    "PreparedSourceUpdate",
    "extract_artifact_names",
    "calculate_file_delta",
    "prepare_source_update",
    "prepare_deleted_module_update",
    "CandidateState",
    "PlanExecutionOutcome",
    "execute_refresh_plan",
    "IncrementalUpdateResult",
    "IncrementalAnalysisEngine",
]

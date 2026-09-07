"""
contextor.core.domain

Central domain models.
"""

from .graph import (
    ProjectGraph,
)
from .imports import (
    ImportRef,
)
from .module import (
    Module,
)
from .resolution import (
    ResolutionResult,
)
from .validation import (
    ValidationError,
)
from .usage_facts import (
    ModuleUsageFacts,
    UsageDelta,
    diff_usage_facts,
)
from .refresh_plan import (
    RefreshPlan,
)
from .lineage_facts import (
    ExtractedAnchorFact,
    ExtractedFlowFact,
    ExtractedLineageSourceFacts,
    ExtractedOccurrenceRef,
    ExtractedSymbolicKind,
    ExtractedSymbolicRef,
    ProviderRef,
    ExtractedSurfaceFact,
    LINEAGE_FACTS_SEMANTIC_VERSION,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    MaterializedAnchorFact,
    MaterializedFlowFact,
    MaterializedLineageSourceFacts,
    MaterializedOccurrenceRef,
    MaterializedSurfaceFact,
    ParameterKind,
    ResolutionKind,
    SemanticEndpoint,
    SemanticInterfaceDescriptor,
    SemanticSlot,
    SemanticSlotKind,
    SourceLineageManifest,
    SourceSpan,
    SurfaceKind,
    build_class_attr_slot,
    build_entrypoint_slot,
    build_instance_attr_slot,
    build_keyword_binding_slot,
    build_module_global_slot,
    build_parameter_value_slot,
    build_positional_binding_slot,
    build_public_slot,
    build_return_slot,
    parse_semantic_slot,
)

__all__ = [
    "ImportRef",
    "Module",
    "ResolutionResult",
    "ProjectGraph",
    "ValidationError",
    "ModuleUsageFacts",
    "UsageDelta",
    "diff_usage_facts",
    "RefreshPlan",
    "ExtractedAnchorFact",
    "ExtractedFlowFact",
    "ExtractedLineageSourceFacts",
    "ExtractedOccurrenceRef",
    "ExtractedSymbolicKind",
    "ExtractedSymbolicRef",
    "ProviderRef",
    "ExtractedSurfaceFact",
    "LINEAGE_FACTS_SEMANTIC_VERSION",
    "LineageConfidence",
    "LineageFamilyStatus",
    "LineageRelation",
    "MaterializedAnchorFact",
    "MaterializedFlowFact",
    "MaterializedLineageSourceFacts",
    "MaterializedOccurrenceRef",
    "MaterializedSurfaceFact",
    "ParameterKind",
    "ResolutionKind",
    "SemanticEndpoint",
    "SemanticInterfaceDescriptor",
    "SemanticSlot",
    "SemanticSlotKind",
    "SourceLineageManifest",
    "SourceSpan",
    "SurfaceKind",
    "build_class_attr_slot",
    "build_entrypoint_slot",
    "build_instance_attr_slot",
    "build_keyword_binding_slot",
    "build_module_global_slot",
    "build_parameter_value_slot",
    "build_positional_binding_slot",
    "build_public_slot",
    "build_return_slot",
    "parse_semantic_slot",
]

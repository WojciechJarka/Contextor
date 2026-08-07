from typing import Any
from .registry import ContextPayload, BuildState

class ArtifactConsumptionBuilder:
    name = "ArtifactConsumptionBuilder"
    requires = {
        "symbol_context", "import_context", "architecture_context",
        "public_api", "symbol_activity", "activity_summary"
    }
    provides = {"artifact_consumption"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.reporting_layer.artifact_consumption import build_artifact_consumption
        
        symbol_context = state["symbol_context"]
        import_context = state["import_context"]
        architecture_context = state["architecture_context"]
        public_api = state["public_api"]
        symbol_activity = state["symbol_activity"]
        activity_summary = state["activity_summary"]
        
        return {
            "artifact_consumption": build_artifact_consumption(
                payload.module_id,
                symbol_context["all_symbols"],
                symbol_context["consumers"],
                import_context["imports"],
                architecture_context["imported_by"],
                public_api,
                symbol_activity,
                activity_summary,
                payload.modules,
                payload.root_path,
                payload.tree,
            )
        }

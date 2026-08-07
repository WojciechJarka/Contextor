from typing import Any
from .registry import ContextPayload, BuildState

class PublicApiBuilder:
    name = "PublicApiBuilder"
    requires = {"symbol_context"}
    provides = {"public_api"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.api.public_api import extract_public_api
        symbol_context = state["symbol_context"]
        return {"public_api": extract_public_api(symbol_context["symbols"])}

class ExportContextBuilder:
    name = "ExportContextBuilder"
    requires = {"symbol_context"}
    provides = {"export_context"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.analysis.export_analysis import extract_exports, find_unused_public_api, summarize_exports
        symbol_context = state["symbol_context"]
        
        exports = extract_exports(payload.tree)
        unused_candidates = find_unused_public_api(
            symbol_context["all_symbols"],
            symbol_context["usage"],
            exports,
            local_calls=symbol_context["symbols"].get("calls", []),
            references=symbol_context["references"],
        )
        return {
            "export_context": {
                "exports": exports,
                "export_summary": summarize_exports(exports),
                "unused_candidates": unused_candidates,
            }
        }

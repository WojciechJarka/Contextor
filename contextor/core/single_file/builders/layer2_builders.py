from typing import Any
from .registry import ContextPayload, BuildState

class TestContextBuilder:
    name = "TestContextBuilder"
    requires = {"public_api"}
    provides = {"test_context"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.analysis.test_context import build_test_context
        public_api = state["public_api"]
        return {
            "test_context": build_test_context(
                payload.module_id,
                payload.root_path,
                public_api,
                allowed_python_paths=[
                    module.path for module in payload.modules.values()
                ],
            )
        }

class ActivityBuilder:
    name = "ActivityBuilder"
    requires = {"symbol_context", "public_api"}
    provides = {"symbol_activity", "activity_summary"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.analysis.activity import classify_symbol_activity, summarize_activity
        symbol_context = state["symbol_context"]
        public_api = state["public_api"]
        
        symbol_activity = classify_symbol_activity(
            symbol_context["all_symbols"],
            symbol_context["references"],
            public_symbols=public_api,
            local_calls=symbol_context["symbols"].get("calls", []),
            analyze_scope="all",
        )
        activity_summary = summarize_activity(symbol_activity)
        
        return {
            "symbol_activity": symbol_activity,
            "activity_summary": activity_summary,
        }

# -*- coding: utf-8 -*-

"""
repo_guardian/core/reporting_single_file.py

SINGLE MODULE REPORT FORMATTER

Warstwa:
    REPORT ASSEMBLY

Odpowiedzialność:
- formatowanie przygotowanych wcześniej danych w ostateczny JSON
- brak wiedzy domenowej i analizy AST

"""

import orjson
import os
from datetime import datetime


def save_single_file_report(report, path):
    """
    Zapis raportu JSON przy użyciu orjson.
    """
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    serialized = orjson.dumps(
        report,
        option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS
    )
    with open(path, "wb") as file:
        file.write(serialized)


def _build_llm_context():
    return {
        "purpose": "single module inspection",
        "recommended_analysis": [
            "review_dependencies",
            "inspect_symbol_usage",
            "evaluate_refactor_boundaries"
        ],
        "model": {
            "name": "facts_first",
            "architecture": "layered_context_extraction",
        }
    }


def generate_single_file_report(ctx: dict, module_count: int):
    """
    Generates a single file report using pre-calculated context structures.
    """

    symbol_context = ctx["symbol_context"]
    export_context = ctx["export_context"]
    semantic_context = ctx["semantic_context"]
    architecture = ctx["architecture_context"]

    return {
        # --------------------------------------------------
        # IDENTITY
        # --------------------------------------------------
        "module": ctx["module_id"],
        "file": str(ctx["file_path"]),
        "generated_at": datetime.now().isoformat(),

        # --------------------------------------------------
        # SYMBOL DOMAIN
        # --------------------------------------------------
        "symbols": symbol_context["symbols"],
        "symbol_usage": symbol_context["usage"],
        "symbol_ecosystem": symbol_context["ecosystem"],
        "symbol_references": symbol_context["references"],
        "api_consumers": symbol_context["consumers"],
        "api_consumer_summary": symbol_context["consumer_summary"],

        # --------------------------------------------------
        # API DOMAIN
        # --------------------------------------------------
        "public_api": ctx["public_api"],
        "exports": export_context["exports"],
        "export_summary": export_context["export_summary"],

        # --------------------------------------------------
        # SYMBOL ACTIVITY
        # --------------------------------------------------
        "symbol_activity": ctx["symbol_activity"],
        "activity_summary": ctx["activity_summary"],
        "unused_public_api": sorted([
            symbol for symbol, data in ctx["symbol_activity"].items()
            if data["status"] == "UNUSED_PUBLIC"
        ]),
        "unused_candidates_old": export_context["unused_candidates"],

        # --------------------------------------------------
        # ARTIFACT CONSUMPTION
        # --------------------------------------------------
        "artifact_consumption": ctx["artifact_consumption"],
        "api_surface": ctx["api_surface"],

        # --------------------------------------------------
        # CODE SEMANTICS
        # --------------------------------------------------
        "semantic_analysis": semantic_context["semantic_analysis"],
        "functions": ctx.get("function_context", {}),

        # --------------------------------------------------
        # IMPORTS
        # --------------------------------------------------
        "imports": ctx["import_context"]["imports"],
        "import_users": ctx["import_users"],

        # --------------------------------------------------
        # ARCHITECTURE
        # --------------------------------------------------
        "architecture": architecture,

        # --------------------------------------------------
        # REPOSITORY CONTEXT
        # --------------------------------------------------
        "repository_context": {
            "module_count": module_count,
            "graph_metrics": architecture["graph_metrics"],
            "cycles": architecture["cycles"],
        },

        # --------------------------------------------------
        # LLM
        # --------------------------------------------------
        "llm_context": _build_llm_context(),
    }

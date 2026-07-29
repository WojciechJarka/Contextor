# -*- coding: utf-8 -*-

"""
repo_guardian/core/__init__.py

Core pipeline API
"""


# ==========================================================
# PIPELINE
# ==========================================================

from .symbol_engine.indexer import (
    build_index,
)

from repo_guardian.core.graph.graph import (
    build_graph,
)

from .validator import validate

# ==========================================================
# REPORTING
# ==========================================================

from repo_guardian.core.reporting_layer.reporting_single_file import (
    generate_single_file_report,
    save_single_file_report,
)


# ==========================================================
# AST ANALYSIS
# ==========================================================

from .api_surface import (
    extract_api_surface,
)



# ==========================================================
# PUBLIC API
# ==========================================================

__all__ = [

    # pipeline
    "build_index",
    "build_graph",
    "validate",


    # reporting
    "generate_single_file_report",
    "save_single_file_report",


    # AST intelligence
    "extract_api_surface",
    "extract_import_usage",
    "analyze_module_semantics",
]

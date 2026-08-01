"""
contextor/core/__init__.py

Core pipeline API
"""


# ==========================================================
# PIPELINE
# ==========================================================

from contextor.core.graph.graph import (
    build_graph,
)

# ==========================================================
# REPORTING
# ==========================================================
from contextor.core.reporting_layer.reporting_single_file import (
    generate_single_file_report,
    save_single_file_report,
)

# ==========================================================
# AST ANALYSIS
# ==========================================================
from .api_surface import (
    extract_api_surface,
)
from .symbol_engine.indexer import (
    build_index,
)
from .validator import validate

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
]

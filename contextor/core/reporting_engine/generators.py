"""
Facade for report generators.
This module re-exports the specialized generators to maintain backward compatibility.
"""
from .collisions_generator import generate_collisions_report
from .summary_generator import generate_report, generate_summary_report, _sanity_check_reports
from .structure_generator import generate_structure_report
from .layer_slicer import slice_report_for_layer

__all__ = [
    "generate_collisions_report",
    "generate_report",
    "generate_structure_report",
    "generate_summary_report",
    "slice_report_for_layer",
    "_sanity_check_reports",
]

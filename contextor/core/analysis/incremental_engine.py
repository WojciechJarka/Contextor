"""
contextor/core/analysis/incremental_engine.py

Backward-compatibility facade for the incremental analysis engine subsystem.
The canonical implementation resides in contextor.core.analysis.incremental.engine.
"""

from contextor.core.analysis.incremental.engine import (
    IncrementalAnalysisEngine,
    IncrementalUpdateResult,
    LocalDegreeDeltaResult,
)

__all__ = [
    "IncrementalAnalysisEngine",
    "IncrementalUpdateResult",
    "LocalDegreeDeltaResult",
]

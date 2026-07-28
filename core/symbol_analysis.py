# -*- coding: utf-8 -*-
"""
repo_guardian/core/symbol_analysis.py

Main forwarder (adapter) for the refactored symbol analysis engine.
In order to maintain SRP and readability, AST and symbol analysis logic
has been extracted to a specialized package `core/symbol_engine/`.

This module exposes the old interface for backwards compatibility.
"""

from repo_guardian.core.symbol_engine import (
    SymbolFacts,
    extract_symbol_facts,
    extract_file_symbols,
    classify_imports,
    find_symbol_usage,
    build_symbol_index,
)

__all__ = [
    "SymbolFacts",
    "extract_symbol_facts",
    "extract_file_symbols",
    "classify_imports",
    "find_symbol_usage",
    "build_symbol_index",
]

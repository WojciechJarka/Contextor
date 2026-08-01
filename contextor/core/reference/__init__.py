from .engine import (
    build_symbol_references,
    find_import_users,
)
from .visitor import SymbolReferenceVisitor

# Compatibility alias
build_references = build_symbol_references

__all__ = [
    "build_symbol_references",
    "build_references",
    "find_import_users",
    "SymbolReferenceVisitor",
]

from .engine import (
    build_symbol_references,
    find_import_users,
)
from .visitor import SymbolReferenceVisitor
from .index import (
    RepositoryReferenceIndex,
    build_repository_reference_index,
)

# Compatibility alias
build_references = build_symbol_references

__all__ = [
    "build_symbol_references",
    "build_references",
    "find_import_users",
    "SymbolReferenceVisitor",
    "RepositoryReferenceIndex",
    "build_repository_reference_index",
]

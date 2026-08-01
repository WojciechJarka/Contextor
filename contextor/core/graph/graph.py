"""
contextor/core/graph.py

LAYER: GRAPH BUILDER

Builds a clean project dependency graph
based on resolver results.

Edge types:

hard_edges:
    real runtime dependencies

soft_edges:
    uncertain dependencies:
    - resolver FALLBACK
    - type-only imports
    - potentially dynamic dependencies


UNKNOWN:
    ignored.
    Do not enter the graph.

GRAPH BUILDER:
    - does not interpret architecture
    - does not calculate risk
    - does not analyze AST

Source of truth:
    resolver + ImportRef
"""

from contextor.core.domain.graph import (
    ProjectGraph,
)
from contextor.core.domain.module import (
    Module,
)
from contextor.core.graph.resolver import (
    build_trie,
    detect_package_root,
    resolve_internal,
)

# ==========================================================
# HELPERS
# ==========================================================


def _is_type_only_import(import_ref) -> bool:
    """
    Type-only imports are treated
    as soft dependency.

    ImportRef does not yet have
    the full AST context,
    so we rely on the existing
    local field.

    Ultimately this could be extended
    by import_usage analyzer.
    """

    return getattr(import_ref, "type_only", False)


def _add_edge(
    graph: dict[str, set[str]],
    source: str,
    target: str,
):
    """
    Central edge recording.

    Ensures:
    - no duplicates
    - determinism
    """

    if source == target:
        return

    graph.setdefault(source, set()).add(target)


# ==========================================================
# PUBLIC API
# ==========================================================


def build_graph(modules: dict[str, Module]) -> ProjectGraph:
    """
    Builds the ProjectGraph.

    Pipeline:

        Module
          |
          v
       resolver
          |
          v
     MODULE/FALLBACK
          |
          v
     ProjectGraph


    Returns:

        ProjectGraph(
            hard_edges,
            soft_edges
        )
    """

    hard_edges: dict[str, set[str]] = {}

    soft_edges: dict[str, set[str]] = {}

    # ======================================================
    # Resolver index
    # ======================================================

    trie = build_trie(modules.keys())

    # Derived from the repository under analysis rather than hardcoded to
    # Contextor's own package name.
    package_root = detect_package_root(
        modules,
        trie,
    )

    # ======================================================
    # Deterministic traversal
    # ======================================================

    for module_id in sorted(modules.keys()):
        module = modules[module_id]

        hard_edges.setdefault(module_id, set())

        soft_edges.setdefault(module_id, set())

        # --------------------------------------------------
        # Import order does not affect graph
        # --------------------------------------------------

        imports = sorted(
            module.imports,
            key=lambda imp: (
                imp.module or "",
                imp.level,
                tuple(sorted(imp.names)),
                imp.is_from_import,
                imp.is_local,
            ),
        )

        for imp in imports:
            try:
                result = resolve_internal(
                    imp,
                    trie,
                    current_module_id=module_id,
                    package_root=package_root,
                )

            except Exception:
                # resolver failure
                # must not destroy repository analysis

                continue

            # ==================================================
            # UNKNOWN
            # ==================================================

            if result.kind == "UNKNOWN" or not result.target_module:
                continue

            target = result.target_module

            # ==================================================
            # SELF IMPORT
            # ==================================================

            if target == module_id:
                continue

            # ==================================================
            # TYPE ONLY
            # ==================================================

            if _is_type_only_import(imp):
                _add_edge(
                    soft_edges,
                    module_id,
                    target,
                )

                continue

            # ==================================================
            # HARD DEPENDENCY
            # ==================================================

            if result.kind == "MODULE":
                _add_edge(
                    hard_edges,
                    module_id,
                    target,
                )

            # ==================================================
            # SOFT DEPENDENCY
            # ==================================================

            elif result.kind == "FALLBACK":
                _add_edge(
                    soft_edges,
                    module_id,
                    target,
                )

    return ProjectGraph(
        hard_edges={key: value for key, value in sorted(hard_edges.items())},
        soft_edges={key: value for key, value in sorted(soft_edges.items())},
    )

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
from contextor.core.errors import checkpoint

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
    """

def build_graph(
    modules: dict[str, Module],
    trie: dict | None = None,
    package_root: str | None = None,
    progress_callback=None,
    reexport_facts_by_module: dict | None = None,
) -> ProjectGraph:
    """
    Builds the dependency graph from parsed modules.
    Optionally accepts pre-computed trie and package_root to avoid recomputation.

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

    if trie is None:
        trie = build_trie(modules.keys())

    if package_root is None:
        # Derived from the repository under analysis rather than hardcoded to
        # Contextor's own package name.
        package_root = detect_package_root(
            modules,
            trie,
        )

    # ======================================================
    # Deterministic traversal
    # ======================================================

    ordered_modules = sorted(modules.keys())
    for completed, module_id in enumerate(ordered_modules):
        checkpoint(
            progress_callback,
            f"Resolving graph: {module_id}",
            completed,
            len(ordered_modules),
        )
        module = modules[module_id]

        hard_edges.setdefault(module_id, set())

        soft_edges.setdefault(module_id, set())

        # --------------------------------------------------
        # Import order does not affect graph
        # --------------------------------------------------

        hard_targets, soft_targets = resolve_module_edges(
            module_id, module, trie, package_root, reexport_facts_by_module
        )
        
        for target in hard_targets:
            _add_edge(hard_edges, module_id, target)
        for target in soft_targets:
            _add_edge(soft_edges, module_id, target)

    return ProjectGraph(
        hard_edges={key: value for key, value in sorted(hard_edges.items())},
        soft_edges={key: value for key, value in sorted(soft_edges.items())},
    )

def resolve_module_edges(
    module_id: str,
    module,
    trie,
    package_root: str,
    reexport_facts_by_module: dict | None = None,
) -> tuple[set[str], set[str]]:
    """
    Resolves outgoing hard and soft dependencies for a single module.
    Extracted as a canonical unit of graph resolution for use in both
    full builds and incremental updates.
    """
    hard: dict[str, set[str]] = {module_id: set()}
    soft: dict[str, set[str]] = {module_id: set()}

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
            continue

        if result.target_module and result.kind != "UNKNOWN":
            target = result.target_module
            if target != module_id:
                if _is_type_only_import(imp):
                    _add_edge(soft, module_id, target)
                elif result.kind == "MODULE":
                    _add_edge(hard, module_id, target)
                elif result.kind == "FALLBACK":
                    _add_edge(soft, module_id, target)

        if not imp.is_from_import or not imp.names:
            continue

        package_init = result.target_module
        if (
            result.kind != "MODULE"
            or not package_init
            or not package_init.endswith(".__init__")
        ):
            continue

        package_name = package_init.removesuffix(".__init__")
        package_facts = (
            (reexport_facts_by_module or {}).get(package_init)
            or {}
        )
        bindings = package_facts.get("bindings") or {}

        for imported_name in sorted(set(imp.names)):
            if not imported_name or imported_name == "*":
                continue

            # Explicit initializer bindings take precedence
            # over a same-named indexed child module.
            if imported_name in bindings:
                continue

            child_name = f"{package_name}.{imported_name}"
            child_import = type(imp)(
                module=child_name,
                level=0,
                names=[],
                is_from_import=False,
                is_local=imp.is_local,
                type_only=imp.type_only,
            )

            try:
                child_result = resolve_internal(
                    child_import,
                    trie,
                    current_module_id=module_id,
                    package_root=None,
                )
            except Exception:
                continue

            if (
                child_result.kind != "MODULE"
                or not child_result.target_module
                or child_result.target_module == module_id
                or child_result.target_module == package_init
            ):
                continue

            child_target = child_result.target_module

            if _is_type_only_import(imp):
                _add_edge(soft, module_id, child_target)
            elif imp.module is None and imp.level > 0:
                # Explicit relative sibling import.
                _add_edge(hard, module_id, child_target)
            else:
                # Named package member: preserve possible
                # child dependency conservatively.
                _add_edge(soft, module_id, child_target)

    return hard[module_id], soft[module_id]

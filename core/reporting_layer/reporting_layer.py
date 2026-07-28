# -*- coding: utf-8 -*-

"""
core/reporting_layer/reporting_layer.py

LAYER REPORT - Structural report for a selected layer (subdirectory)
of the repository, relative to the ENTIRE dependency structure.

Layer: REPORT ASSEMBLY (auxiliary, invoked by ui/gui.py)
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set


# ==========================================================
# PATH HELPERS
# ==========================================================


def _is_inside(path: Path, parent: Path) -> bool:
    """
    Returns True if `path` is inside the `parent` directory
    (at any depth) or matches it exactly.
    """
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _module_absolute_path(module_raw_path: str, root_resolved: Path) -> Path:
    """
    Resolves the module path to an absolute path.
    Supports paths relative to root_path as well as already absolute ones.
    """
    mod_path = Path(module_raw_path)

    if not mod_path.is_absolute():
        mod_path = root_resolved / mod_path

    try:
        return mod_path.resolve()
    except OSError:
        return mod_path


# ==========================================================
# LAYER MEMBERSHIP
# ==========================================================


def _split_layer_modules(
    modules: Dict[str, Any],
    layer_resolved: Path,
    root_resolved: Path,
) -> Tuple[List[str], List[str]]:
    """
    Splits the repository modules into two groups:
    1. layer_modules   - identifiers of modules inside the selected layer.
    2. outside_modules - identifiers of modules outside this layer.
    """
    layer_modules: List[str] = []
    outside_modules: List[str] = []

    # Nazwa szukanej warstwy (np. 'core', 'ui', 'cli')
    target_layer_name = layer_resolved.stem.lower()

    for module_id, module_obj in modules.items():
        mod_str = str(module_id)
        
        # 1. Sprawdzanie po prefiksie w przestrzeni nazw Pythona (np. 'ui' z 'ui.gui')
        top_package = mod_str.split('.')[0].lower()
        matches_package_name = (top_package == target_layer_name) or (mod_str.lower() == target_layer_name)

        # 2. Sprawdzanie po ścieżce plikowej
        raw_path = getattr(module_obj, "path", module_id)
        abs_path = _module_absolute_path(str(raw_path), root_resolved)
        matches_file_path = _is_inside(abs_path, layer_resolved)

        if matches_package_name or matches_file_path:
            layer_modules.append(module_id)
        else:
            outside_modules.append(module_id)

    return layer_modules, outside_modules


# ==========================================================
# EDGE PARTITIONING
# ==========================================================


def _partition_edges(
    edges: Dict[str, List[str]],
    layer_set: Set[str],
) -> Tuple[List[List[str]], List[List[str]], List[List[str]]]:
    """
    Classifies graph dependency edges relative to the layer's module set:

    - internal : source AND target are in the layer
    - inbound  : source OUTSIDE layer, target IN layer (dependencies INTO layer)
    - outbound : source IN layer, target OUTSIDE layer (dependencies OUT of layer)
    """
    internal: List[List[str]] = []
    inbound: List[List[str]] = []
    outbound: List[List[str]] = []

    for src, targets in edges.items():
        src_in = src in layer_set

        for tgt in targets:
            tgt_in = tgt in layer_set

            if src_in and tgt_in:
                internal.append([src, tgt])
            elif src_in and not tgt_in:
                outbound.append([src, tgt])
            elif not src_in and tgt_in:
                inbound.append([src, tgt])

    return (
        sorted(internal),
        sorted(inbound),
        sorted(outbound),
    )


# ==========================================================
# MAIN ENTRY POINT
# ==========================================================


def generate_layer_report(
    layer_path: str,
    modules: Dict[str, Any],
    graph: Any,
    root_path: str,
) -> Dict[str, Any]:
    """
    Generates a complete structural report for the selected layer (subdirectory).
    """
    root_resolved = Path(root_path).resolve()
    layer_resolved = Path(layer_path).resolve()

    # Wyznaczenie ścieżki względnej do zapisu w metadanych raportu
    try:
        layer_relative_str = layer_resolved.relative_to(root_resolved).as_posix()
    except ValueError:
        layer_relative_str = layer_resolved.as_posix()

    # 1. Podział modułów
    layer_modules, _ = _split_layer_modules(
        modules,
        layer_resolved,
        root_resolved,
    )
    layer_set = set(layer_modules)

    # 2. Pobranie słowników krawędzi (odporne na obiekty klasowe i słowniki)
    hard_edges = getattr(
        graph, "hard_edges", 
        graph.get("hard_edges", {}) if isinstance(graph, dict) else {}
    )
    soft_edges = getattr(
        graph, "soft_edges", 
        graph.get("soft_edges", {}) if isinstance(graph, dict) else {}
    )

    # 3. Kategoryzacja krawędzi
    internal_hard, inbound_hard, outbound_hard = _partition_edges(
        hard_edges,
        layer_set,
    )
    internal_soft, inbound_soft, outbound_soft = _partition_edges(
        soft_edges,
        layer_set,
    )

    # 4. Wyznaczenie unikalnych modułów brzegowych
    depended_on_by = sorted({src for src, _ in inbound_hard})
    depends_on = sorted({tgt for _, tgt in outbound_hard})

    # 5. Konstrukcja raportu
    return {
        "layer": {
            "path": layer_relative_str,
            "root": str(root_resolved),
        },
        "layer_modules": sorted(layer_modules),
        "layer_module_count": len(layer_modules),
        "total_module_count": len(modules),
        "internal_edges": {
            "hard": internal_hard,
            "soft": internal_soft,
        },
        "boundary": {
            "inbound_hard": inbound_hard,
            "outbound_hard": outbound_hard,
            "inbound_soft": inbound_soft,
            "outbound_soft": outbound_soft,
            "depended_on_by": depended_on_by,
            "depends_on": depends_on,
        },
        "summary": {
            "internal_edge_count": len(internal_hard),
            "inbound_edge_count": len(inbound_hard),
            "outbound_edge_count": len(outbound_hard),
            "external_dependents_count": len(depended_on_by),
            "external_dependencies_count": len(depends_on),
        },
        "generated_at": datetime.now().isoformat(),
    }


def save_layer_report(
    report: Dict[str, Any],
    path: str,
) -> None:
    """
    Saves the layer report to a JSON file at the given path,
    automatically creating any missing parent directories.
    """
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


# ==========================================================
# EXPORTS
# ==========================================================


__all__ = [
    "generate_layer_report",
    "save_layer_report",
]

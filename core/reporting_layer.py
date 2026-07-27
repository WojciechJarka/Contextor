# -*- coding: utf-8 -*-

"""
repo_guardian/core/reporting_layer.py

LAYER REPORT - raport strukturalny dla wybranej warstwy (podkatalogu)
repozytorium, w odniesieniu do CAŁEJ struktury zależności.

Warstwa: REPORT ASSEMBLY (pomocniczy, wywoływany przez ui/gui.py)

Odpowiedzialność:

- ustalenie, które moduły należą do wybranej warstwy (podkatalogu)
- rozdzielenie krawędzi grafu na:
    * wewnętrzne (oba końce w warstwie)
    * wejściowe / inbound (z zewnątrz DO warstwy - kto zależy
      od tej warstwy)
    * wyjściowe / outbound (z warstwy NA ZEWNĄTRZ - od czego
      ta warstwa zależy)
- policzenie prostych metryk granicznych (ile modułów zewnętrznych
  zależy od warstwy, od ilu modułów zewnętrznych zależy warstwa)

Nie robi:

- indeksowania / budowania grafu (to core/indexer.py, core/graph.py)
- walidacji, długu technicznego, kolizji nazw (to osobne moduły)

Kontrakt wejściowy generate_layer_report():

    layer_path  - ścieżka absolutna do wybranego podkatalogu
                  (MUSI być podkatalogiem root_path, nie samym
                  root_path - tę walidację robi wywołujący,
                  ui/gui.py, PRZED wywołaniem tej funkcji)
    modules     - dict module_id -> Module (z build_index)
    graph       - obiekt z .hard_edges / .soft_edges (z build_graph)
    root_path   - ścieżka absolutna do ROOT repozytorium
"""

import os
import json

from datetime import datetime
from pathlib import Path


# ==========================================================
# PATH HELPERS
# ==========================================================


def _is_inside(path: Path, parent: Path) -> bool:
    """
    True, jeśli `path` jest wewnątrz `parent` (na dowolnej
    głębokości), włącznie z bezpośrednimi dziećmi.
    """

    try:

        path.relative_to(parent)

        return True

    except ValueError:

        return False


def _module_absolute_path(module, root_resolved: Path) -> Path:
    """
    Zwraca bezwzględną, rozwiniętą ścieżkę modułu - niezależnie
    od tego, czy module.path jest zapisane względem root, czy
    już jest ścieżką bezwzględną (obie konwencje spotykane w
    tym kodzie - Path(root) / module.path po cichu ignoruje
    lewą stronę, gdy module.path jest już absolutne, więc samo
    to wyrażenie nie rozstrzyga, które to jest).

    Porównywanie WSZYSTKIEGO po normalizacji do bezwzględnych,
    rozwiniętych ścieżek eliminuje tę niejednoznaczność - działa
    poprawnie niezależnie od konwencji, zamiast zakładać jedną
    z nich i cicho zwracać 0 dopasowań, gdy założenie jest błędne.
    """

    module_path = Path(module.path)

    if not module_path.is_absolute():

        module_path = root_resolved / module_path

    try:

        return module_path.resolve()

    except OSError:

        return module_path


# ==========================================================
# LAYER MEMBERSHIP
# ==========================================================


def _split_layer_modules(
    modules: dict,
    layer_relative: Path,
) -> tuple[list, list]:
    """
    Dzieli moduły na te WEWNĄTRZ wybranej warstwy i te POZA nią,
    na podstawie module.path (ścieżka względem root, ustawiana
    przez indexer - to samo pole, którego używa _load_tree
    w symbol_reference.py).
    """

    layer_modules = []
    outside_modules = []

    for module_id, module in modules.items():

        module_path = Path(module.path)

        if _is_inside(module_path, layer_relative):

            layer_modules.append(module_id)

        else:

            outside_modules.append(module_id)

    return layer_modules, outside_modules


# ==========================================================
# EDGE PARTITIONING
# ==========================================================


def _partition_edges(
    edges: dict,
    layer_set: set,
) -> tuple[list, list, list]:
    """
    Dzieli krawędzie grafu (hard albo soft, ten sam kształt) na:

        internal  - oba końce w warstwie
        inbound   - src POZA warstwą, tgt W warstwie
                    (kto z zewnątrz zależy od warstwy)
        outbound  - src W warstwie, tgt POZA warstwą
                    (od czego warstwa zależy na zewnątrz)

    Krawędzie, gdzie ŻADEN koniec nie jest w warstwie, są
    pomijane - nie dotyczą tej warstwy w ogóle.
    """

    internal = []
    inbound = []
    outbound = []

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
    modules: dict,
    graph,
    root_path: str,
) -> dict:
    """
    Generuje raport strukturalny dla wybranej warstwy (podkatalogu)
    w odniesieniu do CAŁEJ struktury zależności repozytorium.

    UWAGA: ta funkcja ZAKŁADA, że layer_path jest już zwalidowany
    jako podkatalog root_path (różny od samego root_path) - tę
    walidację robi wywołujący (ui/gui.py::analyze_layer), PRZED
    wywołaniem tej funkcji. Tutaj już tylko liczymy.
    """

    root_resolved = Path(root_path).resolve()
    layer_resolved = Path(layer_path).resolve()

    layer_relative = layer_resolved.relative_to(root_resolved)

    layer_modules, outside_modules = _split_layer_modules(
        modules,
        layer_relative,
    )

    layer_set = set(layer_modules)

    internal_hard, inbound_hard, outbound_hard = _partition_edges(
        graph.hard_edges,
        layer_set,
    )

    internal_soft, inbound_soft, outbound_soft = _partition_edges(
        graph.soft_edges,
        layer_set,
    )

    # Moduły zewnętrzne, które faktycznie zależą od warstwy
    # (konsumenci warstwy) i moduły zewnętrzne, od których
    # warstwa faktycznie zależy (zależności warstwy).
    depended_on_by = sorted(
        {src for src, tgt in inbound_hard}
    )

    depends_on = sorted(
        {tgt for src, tgt in outbound_hard}
    )

    return {

        "layer": {
            "path": layer_relative.as_posix(),
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

            # Skróty - same nazwy modułów, bez powtórzeń,
            # wygodne do szybkiego spojrzenia bez liczenia
            # krawędzi ręcznie.
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
    report: dict,
    path: str,
) -> None:

    directory = os.path.dirname(path)

    if directory:

        os.makedirs(
            directory,
            exist_ok=True,
        )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )


# ==========================================================
# EXPORTS
# ==========================================================


__all__ = [
    "generate_layer_report",
    "save_layer_report",
]

# -*- coding: utf-8 -*-

"""
repo_guardian/core/artifact_usage_report.py

GLOBAL ARTIFACT USAGE REPORT

Warstwa:
    REPORT ASSEMBLY (pomocniczy, wywoływany przez reporting.py)

Odpowiedzialność:

- zebranie symboli (funkcje / klasy / metody / globale)
  zdefiniowanych w każdym module
- ustalenie, które moduły faktycznie korzystają
  z tych samych artefaktów
- pogrupowanie modułów-konsumentów w klastry
  współdzielonego użycia
- przygotowanie listy kandydatów do wydzielenia
  wspólnej logiki core, w formacie wygodnym dla LLM

Nie robi:

- parsowania AST (deleguje do symbol_analysis / symbol_reference)
- liczenia ryzyka / metryk grafu (to reporting.py)
- walidacji architektury


Źródła prawdy:

    symbol_analysis.py      -> lokalne symbole modułu
    symbol_reference.py     -> kto używa danego symbolu
    api_consumers.py        -> normalizacja konsumentów


Kontrakt wyjściowy generate_artifact_usage_report():

{
    "runtime": {...},
    "module_count": int,
    "artifact_count": int,
    "shared_artifact_count": int,
    "artifacts": {
        "<moduł_definiujący>::<symbol>": {
            "artifact": str,
            "kind": "class"|"function"|"method"|"global",
            "definer_module": str,
            "consumers": [str],
            "consumer_count": int,
            "usage": {...}
        }
    },
    "shared_artifacts": [...tylko consumer_count >= 2...],
    "shared_usage_clusters": [
        {
            "modules": [...],
            "size": int,
            "shared_artifact_count": int,
            "shared_artifacts": [...]
        }
    ],
    "core_extraction_candidates": [
        {
            "consumer_modules": [...],
            "likely_core_modules": [...],
            "shared_artifact_count": int,
            "top_shared_artifacts": [...],
            "reason": str
        }
    ]
}
"""


import os
import json

from datetime import datetime
from collections import defaultdict, deque

from repo_guardian.core.symbol_analysis import extract_file_symbols
from repo_guardian.core.symbol_reference import build_symbol_references
from repo_guardian.core.api_consumers import extract_api_consumers


# ==========================================================
# CONFIG
# ==========================================================

# minimalna liczba odrębnych modułów-konsumentów, żeby
# artefakt uznać za "współdzielony" (kandydat do core)
MIN_SHARED_CONSUMERS = 2

# minimalna wielkość klastra modułów, żeby zgłosić go
# jako kandydata do wydzielenia wspólnego rdzenia
MIN_CLUSTER_SIZE = 2


# ==========================================================
# SYMBOL COLLECTION PER MODULE
# ==========================================================


def _module_own_symbols(symbols: dict) -> list[str]:

    return (
        symbols.get("classes", [])
        + symbols.get("functions", [])
        + symbols.get("methods", [])
        + symbols.get("globals", [])
    )


def _symbol_kind(symbol: str, symbols: dict) -> str:

    if symbol in symbols.get("classes", []):
        return "class"

    if symbol in symbols.get("functions", []):
        return "function"

    if symbol in symbols.get("methods", []):
        return "method"

    if symbol in symbols.get("globals", []):
        return "global"

    return "unknown"


def collect_module_artifacts(
    modules: dict,
    root_path: str,
) -> dict:
    """
    Dla każdego modułu buduje:

    - lokalne symbole (fakty z symbol_analysis)
    - konsumentów tych symboli (api_consumers, w oparciu
      o symbol_reference)

    Zwraca:

    {
        module_id: {
            "symbols": {...extract_file_symbols...},
            "own_symbols": [...],
            "consumers": {...extract_api_consumers...},
        }
    }
    """

    result = {}

    for module_id, module in modules.items():

        symbols = extract_file_symbols(
            module.absolute_path
        )

        own_symbols = _module_own_symbols(symbols)

        if not own_symbols:

            result[module_id] = {
                "symbols": symbols,
                "own_symbols": own_symbols,
                "consumers": {},
            }

            continue

        references = build_symbol_references(
            modules,
            own_symbols,
            root_path,
            definer_module=module_id,
        )

        consumers = extract_api_consumers(
            own_symbols,
            references,
        )

        result[module_id] = {
            "symbols": symbols,
            "own_symbols": own_symbols,
            "consumers": consumers,
        }

    return result


# ==========================================================
# GLOBAL ARTIFACT INDEX
# ==========================================================


def build_artifact_index(module_artifacts: dict) -> dict:
    """
    Spłaszcza dane per-moduł do globalnego indeksu artefaktów.

    Klucz artefaktu:

        "<moduł_definiujący>::<qualified_symbol>"

    Prefiks modułu jest potrzebny, bo różne moduły mogą
    mieć symbole o identycznej lokalnej nazwie
    (np. dwie klasy "Config" w różnych plikach).
    """

    artifacts = {}

    for module_id, data in module_artifacts.items():

        symbols = data["symbols"]
        consumers = data["consumers"]

        for symbol in data["own_symbols"]:

            consumer_data = consumers.get(symbol, {})

            consumer_modules = sorted(
                {
                    c
                    for c in consumer_data.get("consumers", [])
                    if c != module_id
                }
            )

            key = f"{module_id}::{symbol}"

            artifacts[key] = {
                "artifact": symbol,
                "kind": _symbol_kind(symbol, symbols),
                "definer_module": module_id,
                "consumers": consumer_modules,
                "consumer_count": len(consumer_modules),
                "usage": consumer_data.get("usage", {}),
            }

    return artifacts


def filter_shared_artifacts(
    artifacts: dict,
    min_consumers: int = MIN_SHARED_CONSUMERS,
) -> list[dict]:
    """
    Zwraca artefakty współdzielone przez wielu konsumentów,
    posortowane malejąco wg liczby konsumentów.
    """

    shared = [
        {"key": key, **data}
        for key, data in artifacts.items()
        if data["consumer_count"] >= min_consumers
    ]

    return sorted(
        shared,
        key=lambda item: (
            -item["consumer_count"],
            item["definer_module"],
            item["artifact"],
        ),
    )


# ==========================================================
# CONSUMER CLUSTERING
# ==========================================================
#
# Ten sam wzorzec grafowy co reporting._connected_components,
# ale krawędzią grafu jest "wspólne korzystanie z artefaktu",
# a nie zależność modułowa z grafu importów.
#


def _build_consumer_graph(shared_artifacts: list[dict]) -> dict:

    graph = defaultdict(set)

    for artifact in shared_artifacts:

        consumers = artifact["consumers"]

        for i, a in enumerate(consumers):

            for b in consumers[i + 1:]:

                graph[a].add(b)
                graph[b].add(a)

    return graph


def _connected_components(graph: dict) -> list[list[str]]:

    visited = set()
    clusters = []

    for node in graph:

        if node in visited:
            continue

        queue = deque([node])
        component = []

        while queue:

            current = queue.popleft()

            if current in visited:
                continue

            visited.add(current)
            component.append(current)

            for neigh in graph[current]:

                if neigh not in visited:
                    queue.append(neigh)

        clusters.append(sorted(component))

    return sorted(clusters, key=len, reverse=True)


def build_shared_usage_clusters(
    shared_artifacts: list[dict],
    min_cluster_size: int = MIN_CLUSTER_SIZE,
) -> list[dict]:
    """
    Grupuje moduły-konsumentów, które korzystają z tych
    samych artefaktów, w klastry.

    Klaster = kandydat do przeglądu pod kątem wydzielenia
    wspólnej logiki core.
    """

    graph = _build_consumer_graph(shared_artifacts)

    components = _connected_components(graph)

    clusters = []

    for component in components:

        if len(component) < min_cluster_size:
            continue

        component_set = set(component)

        cluster_artifacts = [
            {
                "artifact": a["artifact"],
                "definer_module": a["definer_module"],
                "kind": a["kind"],
                "consumers": [
                    c
                    for c in a["consumers"]
                    if c in component_set
                ],
            }
            for a in shared_artifacts
            if component_set.intersection(a["consumers"])
        ]

        clusters.append(
            {
                "modules": component,
                "size": len(component),
                "shared_artifact_count": len(cluster_artifacts),
                "shared_artifacts": cluster_artifacts,
            }
        )

    return sorted(
        clusters,
        key=lambda c: (
            -c["shared_artifact_count"],
            -c["size"],
        ),
    )


# ==========================================================
# CORE EXTRACTION CANDIDATES
# ==========================================================


def _dominant_definers(cluster: dict) -> list[str]:
    """
    Moduły, które najczęściej definiują artefakty
    współdzielone w danym klastrze - najbardziej
    prawdopodobni kandydaci na "core" albo miejsce,
    do którego warto wydzielić wspólną logikę.
    """

    counts = defaultdict(int)

    for artifact in cluster["shared_artifacts"]:

        counts[artifact["definer_module"]] += 1

    return sorted(
        counts.keys(),
        key=lambda m: (-counts[m], m),
    )


def build_core_extraction_candidates(
    clusters: list[dict],
) -> list[dict]:
    """
    Format zoptymalizowany pod decyzje LLM o refaktorze:
    "te moduły współdzielą tyle a tyle artefaktów -
    rozważ wydzielenie wspólnego core".
    """

    candidates = []

    for cluster in clusters:

        definers = _dominant_definers(cluster)

        top_artifacts = sorted(
            cluster["shared_artifacts"],
            key=lambda a: -len(a["consumers"]),
        )[:10]

        candidates.append(
            {
                "consumer_modules": cluster["modules"],

                "likely_core_modules": definers,

                "shared_artifact_count": cluster[
                    "shared_artifact_count"
                ],

                "top_shared_artifacts": [
                    {
                        "artifact": a["artifact"],
                        "defined_in": a["definer_module"],
                        "kind": a["kind"],
                        "used_by": a["consumers"],
                    }
                    for a in top_artifacts
                ],

                "reason": (
                    "moduły współdzielą użycie tych samych "
                    "artefaktów (funkcji/klas/metod/pól) - "
                    "potencjalny wspólny core do wydzielenia"
                ),
            }
        )

    return candidates


# ==========================================================
# MAIN ENTRY POINT
# ==========================================================


def generate_artifact_usage_report(
    modules: dict,
    root_path: str,
    runtime: dict | None = None,
) -> dict:
    """
    Generuje globalny raport użycia artefaktów (funkcji,
    klas, metod, pól/globali) pomiędzy plikami repozytorium.

    Uzupełnia generate_report() z reporting.py:

    - reporting.py opisuje strukturę projektu i graf
      zależności modułów
    - ten raport opisuje, kto faktycznie korzysta
      z czyjego kodu na poziomie symboli, i gdzie widać
      kandydatów do wydzielenia wspólnej logiki core
    """

    module_artifacts = collect_module_artifacts(
        modules,
        root_path,
    )

    artifact_index = build_artifact_index(
        module_artifacts
    )

    shared_artifacts = filter_shared_artifacts(
        artifact_index
    )

    clusters = build_shared_usage_clusters(
        shared_artifacts
    )

    core_candidates = build_core_extraction_candidates(
        clusters
    )

    runtime_info = (
        runtime.copy() if runtime else {}
    )

    runtime_info["generated_at"] = (
        datetime.now().isoformat()
    )

    return {

        "runtime":
            runtime_info,

        "module_count":
            len(modules),

        "artifact_count":
            len(artifact_index),

        "shared_artifact_count":
            len(shared_artifacts),

        "artifacts":
            artifact_index,

        "shared_artifacts":
            shared_artifacts,

        "shared_usage_clusters":
            clusters,

        "core_extraction_candidates":
            core_candidates,
    }


def save_artifact_usage_report(
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
    "collect_module_artifacts",
    "build_artifact_index",
    "filter_shared_artifacts",
    "build_shared_usage_clusters",
    "build_core_extraction_candidates",
    "generate_artifact_usage_report",
    "save_artifact_usage_report",
]

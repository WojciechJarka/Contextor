# -*- coding: utf-8 -*-

"""
repo_guardian/core/artifact_usage_report_compact.py

ZWARTA WERSJA raportu artefaktów - DODATKOWY raport, nie zastępuje
generate_artifact_usage_report() ani jego pliku wyjściowego.

Bierze na wejściu dokładnie ten sam dict, który zwraca
generate_artifact_usage_report() (z core/artifact_usage_report.py),
i przekształca go w zwartą wersję:

1. Buduje tabelę modułów ("modules": [...]) i zamienia każde
   wystąpienie identyfikatora modułu (definer_module, consumers,
   kategorie w usage, moduły w klastrach / core_extraction_candidates)
   na indeks w tej tabeli.

2. Dla artefaktów bez konsumentów pomija cały blok
   "usage"/"consumer_count" - to zawsze same puste listy i zera.

3. Dla artefaktów Z konsumentami zostawia w "usage" TYLKO
   niepuste kategorie.

ZERO utraty informacji - to ten sam raport, inaczej zakodowany.

Warstwa: REPORT ASSEMBLY (pomocniczy, wywoływany przez reporting.py)

Nie robi:
- zbierania artefaktów (to artifact_usage_report.py)
- zapisu do pliku (to save_json w reporting.py)
"""


# ==========================================================
# MODULE INDEX
# ==========================================================


def _collect_module_ids(report: dict) -> set:
    """
    Zbiera WSZYSTKIE identyfikatory modułów pojawiające się
    w raporcie. Celowo NIE robimy generycznego przeszukiwania
    całego drzewa JSON (za dużo fałszywych trafień - "artifact",
    "kind", "message" to nie identyfikatory modułów) - zbieramy
    tylko z pól, o których wiemy, że trzymają identyfikatory
    modułów.
    """

    ids = set()

    for key, artifact in report.get("artifacts", {}).items():

        definer = artifact.get("definer_module")
        if definer:
            ids.add(definer)

        for c in artifact.get("consumers", []) or []:
            ids.add(c)

        usage = artifact.get("usage", {}) or {}
        for category_values in usage.values():
            for v in category_values or []:
                ids.add(v)

    for a in report.get("shared_artifacts", []) or []:
        if a.get("definer_module"):
            ids.add(a["definer_module"])
        for c in a.get("consumers", []) or []:
            ids.add(c)

    for cluster in report.get("shared_usage_clusters", []) or []:

        for m in cluster.get("modules", []) or []:
            ids.add(m)

        for a in cluster.get("shared_artifacts", []) or []:
            if a.get("definer_module"):
                ids.add(a["definer_module"])
            for c in a.get("consumers", []) or []:
                ids.add(c)

    for candidate in report.get("core_extraction_candidates", []) or []:

        for m in candidate.get("consumer_modules", []) or []:
            ids.add(m)

        for m in candidate.get("likely_core_modules", []) or []:
            ids.add(m)

        for a in candidate.get("top_shared_artifacts", []) or []:
            if a.get("defined_in"):
                ids.add(a["defined_in"])
            for u in a.get("used_by", []) or []:
                ids.add(u)

    return ids


def build_module_index(report: dict):
    """
    Zwraca (lista_modulow, mapa_modul_na_indeks).

    Lista jest posortowana, żeby wynik był deterministyczny
    (stabilne diffy między uruchomieniami / commitami).
    """

    module_ids = sorted(_collect_module_ids(report))

    index_of = {
        module_id: i
        for i, module_id in enumerate(module_ids)
    }

    return module_ids, index_of


# ==========================================================
# COMPACTION HELPERS
# ==========================================================


def _idx(module_id, index_of):
    """Bezpieczne mapowanie string -> indeks (None jeśli brak)."""

    if module_id is None:
        return None

    return index_of.get(module_id, module_id)


def _idx_list(module_ids, index_of):

    return [
        _idx(m, index_of)
        for m in (module_ids or [])
    ]


def _compact_usage(usage: dict, index_of: dict) -> dict:
    """
    Zostawia TYLKO niepuste kategorie, wartości zamienia
    na indeksy modułów.
    """

    compact = {}

    for category, values in (usage or {}).items():

        if not values:
            continue

        compact[category] = _idx_list(values, index_of)

    return compact


# ==========================================================
# MAIN TRANSFORM
# ==========================================================


def compact_artifact_report(report: dict) -> dict:
    """
    Przekształca pełny raport artefaktów (taki, jaki zwraca
    generate_artifact_usage_report) w zwartą wersję.

    ZERO utraty informacji - to samo zakodowane inaczej. Wynik ma
    inny kształt niż oryginał, ale każdy fakt jest odtwarzalny 1:1
    przez "modules"[indeks].
    """

    module_ids, index_of = build_module_index(report)

    compact_artifacts = {}

    for key, artifact in report.get("artifacts", {}).items():

        definer = artifact.get("definer_module")
        consumers = artifact.get("consumers", []) or []

        entry = {
            "artifact": artifact.get("artifact"),
            "kind": artifact.get("kind"),
            "definer_module": _idx(definer, index_of),
            "consumers": _idx_list(consumers, index_of),
        }

        # Pomijamy usage TYLKO gdy WSZYSTKIE kategorie usage są
        # puste - nie wystarczy patrzeć na "consumers", bo
        # ambiguous_calls z definicji nigdy tam nie wchodzi
        # (to zgadywanka, nie potwierdzony fakt), a event_bindings
        # bywa odfiltrowane z consumers (wykluczenie
        # core.api_consumers) mimo że samo w sobie ma dane.
        compacted_usage = _compact_usage(
            artifact.get("usage", {}),
            index_of,
        )

        if compacted_usage:
            entry["usage"] = compacted_usage

        compact_artifacts[key] = entry

    compact_shared_artifacts = [
        {
            "key": a.get("key"),
            "artifact": a.get("artifact"),
            "kind": a.get("kind"),
            "definer_module": _idx(a.get("definer_module"), index_of),
            "consumers": _idx_list(a.get("consumers", []), index_of),
            "consumer_count": a.get("consumer_count"),
        }
        for a in report.get("shared_artifacts", []) or []
    ]

    compact_clusters = []

    for cluster in report.get("shared_usage_clusters", []) or []:

        compact_clusters.append(
            {
                "modules": _idx_list(
                    cluster.get("modules", []), index_of
                ),
                "size": cluster.get("size"),
                "shared_artifact_count": cluster.get(
                    "shared_artifact_count"
                ),
                "shared_artifacts": [
                    {
                        "artifact": a.get("artifact"),
                        "definer_module": _idx(
                            a.get("definer_module"), index_of
                        ),
                        "kind": a.get("kind"),
                        "consumers": _idx_list(
                            a.get("consumers", []), index_of
                        ),
                    }
                    for a in cluster.get("shared_artifacts", []) or []
                ],
            }
        )

    compact_candidates = []

    for candidate in report.get("core_extraction_candidates", []) or []:

        compact_candidates.append(
            {
                "consumer_modules": _idx_list(
                    candidate.get("consumer_modules", []), index_of
                ),
                "likely_core_modules": _idx_list(
                    candidate.get("likely_core_modules", []), index_of
                ),
                "shared_artifact_count": candidate.get(
                    "shared_artifact_count"
                ),
                "top_shared_artifacts": [
                    {
                        "artifact": a.get("artifact"),
                        "defined_in": _idx(
                            a.get("defined_in"), index_of
                        ),
                        "kind": a.get("kind"),
                        "used_by": _idx_list(
                            a.get("used_by", []), index_of
                        ),
                    }
                    for a in candidate.get("top_shared_artifacts", []) or []
                ],
                "reason": candidate.get("reason"),
            }
        )

    compact_report = {
        "runtime": report.get("runtime", {}),
        "module_count": report.get("module_count"),
        "artifact_count": report.get("artifact_count"),
        "shared_artifact_count": report.get("shared_artifact_count"),

        # LEGENDA: index -> moduł. Wszędzie indziej w tym pliku
        # identyfikatory modułów to liczby wskazujące na tę listę.
        "modules": module_ids,

        "artifacts": compact_artifacts,
        "shared_artifacts": compact_shared_artifacts,
        "shared_usage_clusters": compact_clusters,
        "core_extraction_candidates": compact_candidates,
    }

    # debug_info jest doklejane przez reporting.py PO
    # wygenerowaniu raportu (patrz save_all_reports) - jeśli już
    # tam jest, przepisujemy bez zmian (to nie identyfikatory
    # modułów, nie ma czego kompaktować).
    if "debug_info" in report:
        compact_report["debug_info"] = report["debug_info"]

    return compact_report


# ==========================================================
# BLOCK-PER-LINE WRITER
# ==========================================================
#
# compact_artifact_report() powyżej to TRANSFORMACJA DANYCH
# (indeksy modułów, pomijanie pustych usage) - nie mówi nic
# o formatowaniu zapisu. Ta funkcja to osobna sprawa: SPOSÓB
# ZAPISU już przekształconego raportu na dysk.
#
# Standardowy json.dump(..., indent=2) daje ~15 linii na jeden
# artefakt (czytelne, ale duże). json.dumps(..., separators=(",",":"))
# na całości daje 1 linię na CAŁY plik (małe, ale nieparsowalne
# liniowo/blokowo). Tu jest kompromis: każdy artefakt i każdy
# shared_artifact to DOKŁADNIE jeden wiersz (bez wcięć w środku),
# a reszta pól (moduły, klastry, liczniki) też po jednym wierszu.
#
# Wynik to dalej jeden, w pełni poprawny dokument JSON - json.load()
# wczyta go tak samo jak każdy inny - ale można go też przeglądać/
# grepować/parsować liniowo, bo granica bloku == granica wiersza,
# dokładnie tak jak w pełnym _artifacts.json z wcięciami, tylko że
# blok mieści się w jednej linii zamiast kilkunastu.
#


import os
import json


def _line(obj) -> str:
    """Serializuje pojedynczy obiekt w jednej linii, bez zbędnych spacji."""

    return json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def save_compact_artifact_report(report: dict, path: str) -> None:
    """
    Zapisuje ZWARTY raport artefaktów (wynik compact_artifact_report)
    w formacie "jeden blok = jeden wiersz".

    Zakłada dokładnie kształt zwracany przez compact_artifact_report:
    klucze "artifacts" i "shared_artifacts" to te, które rozbijamy
    na wiele wierszy (po jednym elemencie); wszystkie pozostałe
    klucze najwyższego poziomu (runtime, module_count, modules,
    shared_usage_clusters, core_extraction_candidates, debug_info...)
    zapisujemy jako pojedyncze, jednowierszowe pola - to i tak małe
    struktury w porównaniu do "artifacts".
    """

    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    artifacts = report.get("artifacts", {})
    shared_artifacts = report.get("shared_artifacts", [])

    other_fields = {
        key: value
        for key, value in report.items()
        if key not in ("artifacts", "shared_artifacts")
    }

    with open(path, "w", encoding="utf-8") as f:

        f.write("{\n")

        for key, value in other_fields.items():

            f.write(
                f"  {_line(key)}: {_line(value)},\n"
            )

        # --- artifacts: jeden artefakt = jeden wiersz ---

        f.write('  "artifacts": {\n')

        items = list(artifacts.items())

        for i, (key, value) in enumerate(items):

            comma = "," if i < len(items) - 1 else ""

            f.write(
                f"    {_line(key)}: {_line(value)}{comma}\n"
            )

        f.write("  },\n")

        # --- shared_artifacts: jeden wpis = jeden wiersz ---

        f.write('  "shared_artifacts": [\n')

        for i, item in enumerate(shared_artifacts):

            comma = "," if i < len(shared_artifacts) - 1 else ""

            f.write(
                f"    {_line(item)}{comma}\n"
            )

        f.write("  ]\n")
        f.write("}\n")


# ==========================================================
# EXPORTS
# ==========================================================


__all__ = [
    "compact_artifact_report",
    "build_module_index",
    "save_compact_artifact_report",
]

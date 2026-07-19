# -*- coding: utf-8 -*-

"""
repo_guardian/core/artifact_consumption.py

ARTIFACT CONSUMPTION VIEW

Warstwa:
    REPORT AGGREGATION (widok, NIE źródło faktów)

Odpowiedzialność:

- złożenie w jednym miejscu tego, kto i jak konsumuje
  artefakty (symbole) zdefiniowane w module
- rozróżnienie kanałów: direct / import / runtime / transitive
- policzenie risk_score (per symbol i per moduł), żeby
  LLM/człowiek nie musiał rekonstruować tego z 5 sekcji

Nie robi:

- parsowania AST
- klasyfikacji aktywności (deleguje do activity.py)
- walidacji architektury

Źródła prawdy (tylko re-pakuje, nic nie duplikuje):

    api_consumers.py      -> consumers[symbol]["usage"]
    architecture_context   -> imported_by (proxy dla "transitive")
    activity.py            -> status + confidence -> risk_score

Kontrakt wyjściowy build_artifact_consumption():

{
    "module": str,
    "consumers": {
        "direct": [...],
        "import": [...],
        "runtime": [...],
        "transitive": [...]
    },
    "coupling": {
        "fan_in": int,
        "fan_out": int,
        "api_surface": int,
        "live_symbols": int,
        "unused_symbols": int
    },
    "risk_score": float,
    "symbols": {
        "<symbol>": {
            "direct": [...],
            "import": [...],
            "runtime": [...],
            "transitive": [],
            "risk_score": float
        }
    }
}

UWAGA:

Kanały reflection / serialization / cli_exposure / api_exposure
NIE są tu wypełniane - repo_guardian nie ma dziś analizatora,
który by je faktycznie wykrywał (byłoby to zgadywanie, nie
fakt). Jeśli taki analizator powstanie, jego wynik dokłada się
do "symbols"."<symbol>" jako kolejny klucz, obok
"direct"/"import"/"runtime"/"transitive".
"""


from repo_guardian.core.activity import (
    STATUS_LIVE,
    STATUS_LIVE_CALLBACK,
    STATUS_UNUSED_PUBLIC,
    STATUS_UNUSED_INTERNAL,
)


# ==========================================================
# RISK SCORING
# ==========================================================
#
# risk_score = ryzyko EPISTEMICZNE, nie "blast radius":
# im mniej pewne jest, kto/czy faktycznie korzysta z symbolu,
# tym wyżej. Symbol z wieloma potwierdzonymi konsumentami
# (status live, wysoka confidence) = NISKIE ryzyko, bo jego
# użycie jest w pełni zrozumiane. Symbol publiczny bez
# wykrytych konsumentów = WYSOKIE ryzyko - albo jest martwy,
# albo używany w sposób, którego repo_guardian dziś nie widzi
# (reflection, config, serializacja...).
#

_RISK_BY_STATUS_CONFIDENCE = {
    (STATUS_LIVE, "high"): 0.15,
    (STATUS_LIVE, "medium"): 0.30,
    (STATUS_LIVE, "low"): 0.45,

    (STATUS_LIVE_CALLBACK, "high"): 0.25,
    (STATUS_LIVE_CALLBACK, "medium"): 0.40,
    (STATUS_LIVE_CALLBACK, "low"): 0.55,

    (STATUS_UNUSED_INTERNAL, "high"): 0.50,
    (STATUS_UNUSED_INTERNAL, "medium"): 0.60,
    (STATUS_UNUSED_INTERNAL, "low"): 0.70,

    (STATUS_UNUSED_PUBLIC, "high"): 0.70,
    (STATUS_UNUSED_PUBLIC, "medium"): 0.80,
    (STATUS_UNUSED_PUBLIC, "low"): 0.85,
}

_DEFAULT_RISK = 0.50


def _symbol_risk_score(activity_entry: dict) -> float:

    if not activity_entry:
        return _DEFAULT_RISK

    status = activity_entry.get("status")
    confidence = activity_entry.get("confidence")

    return _RISK_BY_STATUS_CONFIDENCE.get(
        (status, confidence),
        _DEFAULT_RISK,
    )


def _module_risk_score(symbol_scores: list) -> float:

    if not symbol_scores:
        return _DEFAULT_RISK

    return round(
        sum(symbol_scores) / len(symbol_scores),
        2,
    )


# ==========================================================
# PER-SYMBOL VIEW
# ==========================================================


def build_symbol_consumption(
    all_symbols: list,
    consumers: dict,
    symbol_activity: dict,
) -> dict:
    """
    Dla każdego symbolu modułu: kto go konsumuje, jakim
    kanałem, i jak ryzykowna jest ta konsumpcja.

    consumers: wynik extract_api_consumers() (api_consumers.py)
    symbol_activity: wynik classify_symbol_activity() (activity.py)
    """

    result = {}

    for symbol in all_symbols:

        consumer_data = consumers.get(symbol, {})
        usage = consumer_data.get("usage", {})

        activity_entry = symbol_activity.get(symbol, {})

        result[symbol] = {

            "direct":
                usage.get("direct_calls", []),

            "import":
                usage.get("api_imports", []),

            "runtime":
                usage.get("runtime_calls", []),

            "transitive":
                [],  # brak dziś źródła prawdy na poziomie symbolu

            "risk_score":
                _symbol_risk_score(activity_entry),
        }

    return result


# ==========================================================
# PER-MODULE VIEW
# ==========================================================


def build_module_consumption(
    consumers: dict,
    imports: dict,
    imported_by: list,
    public_api: list,
    activity_summary: dict,
):
    """
    "Executive summary" dla całego modułu: agreguje kanały
    konsumpcji ze wszystkich symboli + architecture.imported_by
    jako proxy dla "transitive" (moduły, które zależą od tego
    modułu, ale nie mają wykrytego bezpośredniego/import/runtime
    użycia żadnego konkretnego symbolu).
    """

    direct = set()
    api_import = set()
    runtime = set()

    for consumer_data in consumers.values():

        usage = consumer_data.get("usage", {})

        direct.update(usage.get("direct_calls", []))
        api_import.update(usage.get("api_imports", []))
        runtime.update(usage.get("runtime_calls", []))

    known = direct | api_import | runtime

    transitive = sorted(
        m for m in imported_by if m not in known
    )

    fan_in = len(known | set(transitive))
    fan_out = len(imports.get("internal", []))

    module_consumers = {
        "direct": sorted(direct),
        "import": sorted(api_import),
        "runtime": sorted(runtime),
        "transitive": transitive,
    }

    coupling = {
        "fan_in": fan_in,
        "fan_out": fan_out,
        "api_surface": len(public_api),
        "live_symbols": (
            activity_summary.get("live", 0)
            + activity_summary.get("live_callback", 0)
        ),
        "unused_symbols": (
            activity_summary.get("unused_public_api", 0)
            + activity_summary.get("unused_internal_candidates", 0)
        ),
    }

    return module_consumers, coupling


# ==========================================================
# PUBLIC ENTRY POINT
# ==========================================================


def build_artifact_consumption(
    module_id: str,
    all_symbols: list,
    consumers: dict,
    imports: dict,
    imported_by: list,
    public_api: list,
    symbol_activity: dict,
    activity_summary: dict,
) -> dict:
    """
    Warstwa "executive summary" dla LLM/człowieka - NIE
    zastępuje symbol_references / api_consumers / imports /
    architecture.imported_by / symbol_activity, tylko składa
    je w jeden widok konsumpcji artefaktów tego modułu.
    """

    module_consumers, coupling = build_module_consumption(
        consumers,
        imports,
        imported_by,
        public_api,
        activity_summary,
    )

    symbols = build_symbol_consumption(
        all_symbols,
        consumers,
        symbol_activity,
    )

    risk_score = _module_risk_score(
        [s["risk_score"] for s in symbols.values()]
    )

    return {
        "module": module_id,
        "consumers": module_consumers,
        "coupling": coupling,
        "risk_score": risk_score,
        "symbols": symbols,
    }


# ==========================================================
# EXPORTS
# ==========================================================


__all__ = [
    "build_symbol_consumption",
    "build_module_consumption",
    "build_artifact_consumption",
]

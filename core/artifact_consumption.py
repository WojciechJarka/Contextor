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
  / reflection / serialization / cli_exposure / api_exposure
- policzenie risk_score (per symbol i per moduł), żeby
  LLM/człowiek nie musiał rekonstruować tego z 5+ sekcji

Nie robi:

- parsowania AST samodzielnie (deleguje do symbol_analysis /
  symbol_reference / exposure_analysis)
- klasyfikacji aktywności (deleguje do activity.py)
- walidacji architektury

Źródła prawdy (tylko re-pakuje, nic nie duplikuje):

    api_consumers.py       -> consumers[symbol]["usage"]
    architecture_context    -> imported_by (proxy dla "transitive")
    activity.py             -> status + confidence -> risk_score
    exposure_analysis.py    -> reflection / serialization /
                                cli_exposure / api_exposure

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
        "unused_symbols": int,
        "exposed_symbols": int
    },
    "risk_score": float,
    "symbols": {
        "<symbol>": {
            "direct": [...],
            "import": [...],
            "runtime": [...],
            "transitive": [],
            "reflection": [...],
            "serialization": [...],
            "cli_exposure": bool,
            "api_exposure": bool,
            "risk_score": float
        }
    }
}

Kanały reflection / serialization / cli_exposure / api_exposure
pochodzą z exposure_analysis.py:

    reflection / serialization: skan CAŁEGO projektu - nazwa
        symbolu jako literał stringowy w wywołaniu
        getattr/setattr/hasattr/delattr (reflection) albo
        json.dumps/yaml.dump/pickle.dumps/asdict/model_dump
        (serialization)

    cli_exposure / api_exposure: skan WŁASNEGO modułu symbolu -
        dekorator @command/@group (cli) albo @get/@post/@route
        lub baza klasy typu View/Resource/Controller (api)

To sygnały tekstowe (dopasowanie po nazwie), nie dowód
wykonania - tak samo jak reszta repo_guardiana dopasowuje
symbole po identyczności nazwy, nie po typach.
"""


from repo_guardian.core.activity import (
    STATUS_LIVE,
    STATUS_LIVE_CALLBACK,
    STATUS_UNUSED_PUBLIC,
    STATUS_UNUSED_INTERNAL,
)
# Removed exposure_analysis import


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
# albo używany w sposób, którego repo_guardian domyślnie nie
# widzi (reflection, config, serializacja...) - stąd exposure
# jako osobny sygnał obniżający niepewność.
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


def _has_exposure_evidence(exposure_entry: dict) -> bool:

    if not exposure_entry:
        return False

    return bool(
        exposure_entry.get("reflection")
        or exposure_entry.get("serialization")
        or exposure_entry.get("cli_exposure")
        or exposure_entry.get("api_exposure")
    )


def _apply_exposure_discount(
    risk_score: float,
    exposure_entry: dict,
) -> float:
    """
    Konkretny tekstowy trop (reflection/serialization/cli/api)
    tłumaczy status "unused" - to nie dowód wykonania, ale
    redukuje niepewność względem "zero wyjaśnienia".
    """

    if not _has_exposure_evidence(exposure_entry):
        return risk_score

    return round(
        min(risk_score, 0.35),
        2,
    )


# ==========================================================
# PER-SYMBOL VIEW
# ==========================================================


def build_symbol_consumption(
    all_symbols: list,
    consumers: dict,
    symbol_activity: dict,
    exposure: dict,
) -> dict:
    """
    Dla każdego symbolu modułu: kto go konsumuje, jakim
    kanałem, i jak ryzykowna jest ta konsumpcja.

    consumers: wynik extract_api_consumers() (api_consumers.py)
    symbol_activity: wynik classify_symbol_activity() (activity.py)
    exposure: wynik analyze_symbol_exposure() (exposure_analysis.py)
    """

    result = {}

    for symbol in all_symbols:

        consumer_data = consumers.get(symbol, {})
        usage = consumer_data.get("usage", {})

        activity_entry = symbol_activity.get(symbol, {})
        exposure_entry = exposure.get(symbol, {})

        base_risk = _symbol_risk_score(activity_entry)

        result[symbol] = {

            "direct":
                usage.get("direct_calls", []),

            "import":
                usage.get("api_imports", []),

            "runtime":
                usage.get("runtime_calls", []),

            "transitive":
                [],  # brak dziś źródła prawdy na poziomie symbolu

            "reflection":
                exposure_entry.get("reflection", []),

            "serialization":
                exposure_entry.get("serialization", []),

            "cli_exposure":
                exposure_entry.get("cli_exposure", False),

            "api_exposure":
                exposure_entry.get("api_exposure", False),

            "risk_score":
                _apply_exposure_discount(
                    base_risk,
                    exposure_entry,
                ),
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
    exposure: dict,
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
        "exposed_symbols": sum(
            1
            for entry in exposure.values()
            if _has_exposure_evidence(entry)
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
    modules: dict,
    root_path: str,
    tree,
) -> dict:
    """
    Warstwa "executive summary" dla LLM/człowieka - NIE
    zastępuje symbol_references / api_consumers / imports /
    architecture.imported_by / symbol_activity, tylko składa
    je w jeden widok konsumpcji artefaktów tego modułu.

    modules/root_path: potrzebne do project-wide skanu
    reflection/serialization (exposure_analysis.py).
    tree: AST tego modułu, do lokalnego skanu cli/api exposure.
    """

    exposure = {}

    module_consumers, coupling = build_module_consumption(
        consumers,
        imports,
        imported_by,
        public_api,
        activity_summary,
        exposure,
    )

    symbols = build_symbol_consumption(
        all_symbols,
        consumers,
        symbol_activity,
        exposure,
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

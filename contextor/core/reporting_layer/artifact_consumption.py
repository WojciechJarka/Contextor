"""
core/artifact_consumption.py

ARTIFACT CONSUMPTION VIEW

Layer:
    REPORT AGGREGATION (view, NOT source of truth)

Responsibilities:

- Aggregates who consumes artifacts (symbols) defined in the module
  and how they are consumed into a single place.
- Distinguishes channels: direct / import / runtime / transitive
  / reflection / serialization / cli_exposure / api_exposure.
- Calculates risk_score (per symbol and per module) so that
  the LLM/human does not have to reconstruct it from 5+ sections.

Does not do:

- AST parsing on its own (delegates to symbol_analysis /
  symbol_reference / exposure_analysis).
- Activity classification (delegates to activity.py).
- Architecture validation.

Sources of truth (only re-packages, never duplicates):

    api_consumers.py       -> consumers[symbol]["usage"]
    architecture_context   -> imported_by (proxy for "transitive")
    activity.py            -> status + confidence -> risk_score
    exposure_analysis.py   -> reflection / serialization /
                              cli_exposure / api_exposure

Output Contract build_artifact_consumption():

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
            "direct": {"modules": [...], "evidence_type": "..."},
            "import": {"modules": [...], "evidence_type": "..."},
            "runtime": {"modules": [...], "evidence_type": "..."},
            "transitive": {"modules": [...], "evidence_type": "..."},
            "reflection": {"matches": [...], "evidence_type": "..."},
            "serialization": {"matches": [...], "evidence_type": "..."},
            "cli_exposure": {"detected": bool, "evidence_type": "..."},
            "api_exposure": {"detected": bool, "evidence_type": "..."},
            "risk_score": float
        }
    }
}

The reflection / serialization / cli_exposure / api_exposure channels
originate from exposure_analysis.py:

    reflection / serialization: scans the ENTIRE project - matching
        symbol name as a string literal inside calls to
        getattr/setattr/hasattr/delattr (reflection) or
        json.dumps/yaml.dump/pickle.dumps/asdict/model_dump
        (serialization).

    cli_exposure / api_exposure: scans the symbol's OWN module -
        looking for decorators like @command/@group (cli) or @get/@post/@route,
        or class inheritance from View/Resource/Controller base classes (api).

These are textual signals (name-based matching), not execution proof -
just like the rest of contextor matches symbols by identical names,
not by types.
"""

from contextor.core.analysis.activity import (
    STATUS_LIVE,
    STATUS_LIVE_CALLBACK,
    STATUS_UNUSED_INTERNAL,
    STATUS_UNUSED_PUBLIC,
)
from contextor.core.analysis.exposure_analysis import analyze_symbol_exposure

# ==========================================================
# RISK SCORING
# ==========================================================
#
# risk_score = EPISTEMIC risk, not "blast radius":
# The less certain we are about who/if anyone actually uses the symbol,
# the higher the score. A symbol with multiple confirmed consumers
# (live status, high confidence) = LOW risk, because its usage is
# fully understood. A public symbol with no detected consumers = HIGH risk
# - it is either dead or used in a way that contextor does not natively
# see (reflection, config, serialization...) - hence exposure serves as
# an isolated signal to lower uncertainty.
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
    A concrete textual trace (reflection/serialization/cli/api)
    explains the "unused" status - it is not proof of execution,
    but it reduces uncertainty compared to "zero explanation".
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
    module_transitive: list = None,
) -> dict:
    """
    For each module symbol: who consumes it, through which
    channel, and how risky this consumption is.

    consumers: output of extract_api_consumers() (api_consumers.py)
    symbol_activity: output of classify_symbol_activity() (activity.py)
    exposure: output of analyze_symbol_exposure() (exposure_analysis.py)
    """

    result = {}
    module_transitive = module_transitive or []

    for symbol in all_symbols:
        consumer_data = consumers.get(symbol, {})
        usage = consumer_data.get("usage", {})

        activity_entry = symbol_activity.get(symbol, {})
        exposure_entry = exposure.get(symbol, {})

        base_risk = _symbol_risk_score(activity_entry)

        result[symbol] = {
            "direct": {
                "modules": usage.get("direct_calls", []),
                "evidence_type": "ast_call_graph",
            },
            "import": {
                "modules": usage.get("api_imports", []),
                "evidence_type": "ast_import_statements",
            },
            "runtime": {
                "modules": usage.get("runtime_calls", []),
                "evidence_type": "ast_dynamic_getattr",
            },
            "blast_radius_modules": {
                "modules": module_transitive if (usage.get("direct_calls") or usage.get("api_imports")) else [],
                "evidence_type": "module_level_dependency",
            },
            "blast_radius_score": len(
                module_transitive if (usage.get("direct_calls") or usage.get("api_imports")) else []
            ),
            "reflection": {
                "matches": exposure_entry.get("reflection", []),
                "evidence_type": "regex_string_match_in_getattr",
            },
            "serialization": {
                "matches": exposure_entry.get("serialization", []),
                "evidence_type": "regex_string_match_in_dumps",
            },
            "cli_exposure": {
                "detected": exposure_entry.get("cli_exposure", False),
                "evidence_type": "ast_decorator_pattern",
            },
            "api_exposure": {
                "detected": exposure_entry.get("api_exposure", False),
                "evidence_type": "ast_base_class_or_decorator",
            },
            "risk_score": _apply_exposure_discount(
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
    "Executive summary" for the entire module: aggregates consumption
    channels from all symbols + architecture.imported_by as a proxy
    for "transitive" (modules that depend on this module but have no
    detected direct/import/runtime usage of any specific symbol).
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

    transitive = sorted(m for m in imported_by if m not in known)

    fan_in = len(known | set(transitive))
    fan_out = len(imports.get("internal", []))

    module_consumers = {
        "direct": {
            "modules": sorted(direct),
            "evidence_type": "ast_call_graph",
        },
        "import": {
            "modules": sorted(api_import),
            "evidence_type": "ast_import_statements",
        },
        "runtime": {
            "modules": sorted(runtime),
            "evidence_type": "ast_dynamic_getattr",
        },
        "transitive": {
            "modules": transitive,
            "evidence_type": "module_level_dependency",
        },
    }

    coupling = {
        "fan_in": fan_in,
        "fan_out": fan_out,
        "api_surface": len(public_api),
        "live_symbols": (
            activity_summary.get("live", 0) + activity_summary.get("live_callback", 0)
        ),
        "unused_symbols": (
            activity_summary.get("unused_public_api", 0)
            + activity_summary.get("unused_internal_candidates", 0)
        ),
        "exposed_symbols": sum(1 for entry in exposure.values() if _has_exposure_evidence(entry)),
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
    "Executive summary" layer for LLM/human - does NOT replace
    symbol_references / api_consumers / imports / architecture.imported_by
    / symbol_activity. It just merges them into a unified artifact
    consumption view for this module.

    modules/root_path: required for project-wide scanning of
    reflection/serialization (exposure_analysis.py).
    tree: AST of this module, for local cli/api exposure scan.
    """

    exposure = analyze_symbol_exposure(module_id, all_symbols, modules, root_path)
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
        module_transitive=module_consumers.get("transitive", []),
    )

    risk_score = _module_risk_score([s["risk_score"] for s in symbols.values()])

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

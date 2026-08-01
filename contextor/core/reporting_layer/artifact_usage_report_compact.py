"""
core/reporting_layer/artifact_usage_report_compact.py

COMPACT VERSION of the artifact report - ADDITIONAL report, does not replace
generate_artifact_usage_report() or its output file.

Takes exactly the same dict that is returned by
generate_artifact_usage_report() (from core/artifact_usage_report.py),
and transforms it into a compact version:

1. Builds a module table ("modules": [...]) and replaces every
   occurrence of a module identifier (definer_module, consumers,
   categories in usage, modules in clusters / core_extraction_candidates)
   with an index to this table.

2. For artifacts with no consumers, skips the entire
   "usage"/"consumer_count" block - these are always empty lists and zeros.

3. For artifacts WITH consumers, keeps ONLY non-empty categories
   in "usage".

ZERO data loss - this is the same report, encoded differently.

Layer: REPORT ASSEMBLY (auxiliary, invoked by reporting.py)

Does not do:
- artifact gathering (handled by artifact_usage_report.py)
- file saving (handled by save_json in reporting.py)
"""

import json
import os

# ==========================================================
# MODULE INDEX
# ==========================================================


def _collect_module_ids(report: dict) -> set:
    """
    Collects ALL module identifiers appearing in the report.
    We purposely DO NOT perform generic searching across the whole
    JSON tree (too many false positives - "artifact", "kind",
    "message" are not module IDs) - we only collect from fields
    that we know hold module identifiers.
    """

    ids = set()

    for artifact in report.get("artifacts", {}).values():
        definer = artifact.get("definer_module")
        if definer:
            ids.add(definer)

        for c in artifact.get("consumers", []) or []:
            ids.add(c)

        usage = artifact.get("usage", {}) or {}
        for category_values in usage.values():
            for v in category_values or []:
                if isinstance(v, dict):
                    if "module" in v:
                        ids.add(v["module"])
                else:
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
    Returns (module_list, module_to_index_map).

    The list is sorted so that the result is deterministic
    (stable diffs between runs / commits).
    """

    module_ids = sorted(_collect_module_ids(report))

    index_of = {module_id: i for i, module_id in enumerate(module_ids)}

    return module_ids, index_of


# ==========================================================
# COMPACTION HELPERS
# ==========================================================


def _idx(module_id, index_of):
    """Safe mapping string -> index (None if missing)."""

    if module_id is None:
        return None

    return index_of.get(module_id, module_id)


def _idx_list(module_ids, index_of):

    return [_idx(m, index_of) for m in (module_ids or [])]


def _compact_usage(usage: dict, index_of: dict) -> dict:
    """
    Keeps ONLY non-empty categories, replacing values
    with module indexes. Special logic for 'ambiguous_calls'
    which holds dicts instead of string module IDs.
    """

    compact = {}

    for category, values in (usage or {}).items():
        if not values:
            continue

        if category == "ambiguous_calls" or category.endswith("_detail"):
            # Values are dicts like {"module": "mod_id", "reason": "...", "line": 42}
            compacted_values = []
            for item in values:
                if isinstance(item, dict):
                    compact_item = dict(item)
                    compact_item["module"] = _idx(item.get("module"), index_of)
                    compacted_values.append(compact_item)
                else:
                    compacted_values.append(_idx(item, index_of))
            compact[category] = compacted_values
        else:
            compact[category] = _idx_list(values, index_of)

    return compact


# ==========================================================
# MAIN TRANSFORM
# ==========================================================


def compact_artifact_report(report: dict) -> dict:
    """
    Transforms the full artifact report (as returned by
    generate_artifact_usage_report) into a compact version.

    ZERO data loss - the same information encoded differently.
    The result has a different shape than the original, but every fact
    is reproducible 1:1 via "modules"[index].
    """

    module_ids, index_of = build_module_index(report)

    compact_artifacts = {}

    for key, artifact in report.get("artifacts", {}).items():
        definer = artifact.get("definer_module")
        consumers = artifact.get("consumers", []) or []

        entry = {
            "artifact": artifact.get("artifact"),
            "kind": artifact.get("kind"),
            "signature": artifact.get("signature"),
            "definer_module": _idx(definer, index_of),
            "consumers": _idx_list(consumers, index_of),
        }

        # Skip usage ONLY if ALL usage categories are
        # empty - it's not enough to look at "consumers", because
        # ambiguous_calls by definition never go there
        # (it's a guess, not a confirmed fact), and event_bindings
        # are sometimes filtered out of consumers (excluding
        # core.api_consumers) even though they have data themselves.
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
                "modules": _idx_list(cluster.get("modules", []), index_of),
                "size": cluster.get("size"),
                "shared_artifact_count": cluster.get("shared_artifact_count"),
                "shared_artifacts": [
                    {
                        "artifact": a.get("artifact"),
                        "definer_module": _idx(a.get("definer_module"), index_of),
                        "kind": a.get("kind"),
                        "consumers": _idx_list(a.get("consumers", []), index_of),
                    }
                    for a in cluster.get("shared_artifacts", []) or []
                ],
            }
        )

    compact_candidates = []

    for candidate in report.get("core_extraction_candidates", []) or []:
        compact_candidates.append(
            {
                "consumer_modules": _idx_list(candidate.get("consumer_modules", []), index_of),
                "likely_core_modules": _idx_list(
                    candidate.get("likely_core_modules", []), index_of
                ),
                "shared_artifact_count": candidate.get("shared_artifact_count"),
                "top_shared_artifacts": [
                    {
                        "artifact": a.get("artifact"),
                        "defined_in": _idx(a.get("defined_in"), index_of),
                        "kind": a.get("kind"),
                        "used_by": _idx_list(a.get("used_by", []), index_of),
                    }
                    for a in candidate.get("top_shared_artifacts", []) or []
                ],
                "reason": candidate.get("reason"),
            }
        )

    compact_report = {
        "_format_note": (
            "This is a compacted artifact-usage report. Numbers inside "
            "'definer_module', 'consumers', and the categories under "
            "'usage' (direct_calls, callback_calls, event_bindings, "
            "runtime_calls, api_imports, inheritance, ambiguous_calls) "
            "are INDEXES into the 'modules' array below (e.g. index 13 "
            "means modules[13]), not counts, ranks, or priorities. "
            "If an artifact entry has no 'usage' key, it means it has "
            "zero consumers - not missing data. 'ambiguous_calls' are "
            "low-confidence guesses (short-name matches with no import "
            "confirming the source module) and should be treated as "
            "'maybe', never as confirmed usage."
        ),
        "runtime": report.get("runtime", {}),
        "module_count": report.get("module_count"),
        "artifact_count": report.get("artifact_count"),
        "shared_artifact_count": report.get("shared_artifact_count"),
        # LEGEND: index -> module. Everywhere else in this file,
        # module identifiers are numbers pointing to this list.
        "modules": module_ids,
        "artifacts": dict(sorted(compact_artifacts.items())),
        "shared_artifacts": compact_shared_artifacts,
        "shared_usage_clusters": compact_clusters,
        "core_extraction_candidates": compact_candidates,
    }

    # debug_info is attached by reporting.py AFTER report generation
    # (see save_all_reports) - if it is already there, we copy it
    # unmodified (it doesn't contain module IDs to compact).
    if "debug_info" in report:
        compact_report["debug_info"] = report["debug_info"]

    return compact_report


# ==========================================================
# BLOCK-PER-LINE WRITER
# ==========================================================


def _line(obj) -> str:
    """Serializes a single object on one line, without extra spaces."""

    return json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def save_compact_artifact_report(report: dict, path: str) -> None:
    """
    Saves the COMPACT artifact report (result of compact_artifact_report)
    in a "one block = one line" format.

    Assumes the exact shape returned by compact_artifact_report:
    "artifacts" and "shared_artifacts" keys are broken down into
    multiple lines (one element each); all other top-level keys
    (runtime, module_count, modules, shared_usage_clusters,
    core_extraction_candidates, debug_info...) are saved as single,
    one-line fields - they are small structures anyway.
    """

    from contextor.core.reporting_engine.formatting import resolve_report_path

    target = resolve_report_path(path)

    os.makedirs(target.parent, exist_ok=True)

    artifacts = report.get("artifacts", {})
    shared_artifacts = report.get("shared_artifacts", [])

    other_fields = {
        key: value for key, value in report.items() if key not in ("artifacts", "shared_artifacts")
    }

    with open(target, "w", encoding="utf-8") as f:
        f.write("{\n")

        for key, value in other_fields.items():
            f.write(f"  {_line(key)}: {_line(value)},\n")

        # --- artifacts: jeden artefakt = jeden wiersz ---

        f.write('  "artifacts": {\n')

        items = list(artifacts.items())

        for i, (key, value) in enumerate(items):
            comma = "," if i < len(items) - 1 else ""

            f.write(f"    {_line(key)}: {_line(value)}{comma}\n")

        f.write("  },\n")

        # --- shared_artifacts: jeden wpis = jeden wiersz ---

        f.write('  "shared_artifacts": [\n')

        for i, item in enumerate(shared_artifacts):
            comma = "," if i < len(shared_artifacts) - 1 else ""

            f.write(f"    {_line(item)}{comma}\n")

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

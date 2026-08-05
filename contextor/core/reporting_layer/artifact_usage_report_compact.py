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

2. Artifacts with no consumers are already excluded from the source report
   (filtered by build_artifact_index). No additional filtering needed here.

3. For artifacts WITH consumers, keeps ONLY non-empty categories
   in "usage" (if usage is present at all — it lives in the sidecar).

ZERO data loss - this is the same report, encoded differently.

Schema version: 2
  - shared_artifacts full list replaced by shared_artifact_keys (list of str).
  - No inline usage block per artifact (moved to sidecar).
  - artifact_id field present inside each artifact entry.

Layer: REPORT ASSEMBLY (auxiliary, invoked by reporting.py)

Does not do:
- artifact gathering (handled by artifact_usage_report.py)
- file saving (handled by save_json in reporting.py)

NOTE: 
To prevent I/O bloat, `shared_usage_clusters` processing assumes the upstream 
report has already capped clusters to a reasonable limit (e.g., 30) and that 
inner artifacts are stored by `artifact_id` rather than duplicating their full definitions.
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

    Schema v2: no shared_artifacts full objects, no inline usage per artifact.
    """

    ids = set()

    for artifact in report.get("artifacts", {}).values():
        definer = artifact.get("definer_module")
        if definer:
            ids.add(definer)

        for c in artifact.get("consumers", []) or []:
            ids.add(c)

        # Schema v2: usage is in the sidecar, not inline. Skip usage scan here.

    # shared_artifact_keys is a list of str keys, not full objects — no module ids here.

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


from contextor.core.reporting_engine.dictionary import IndexDictionary

def build_module_index(report: dict, index_dict: IndexDictionary = None) -> IndexDictionary:
    """
    Builds or updates the IndexDictionary using the provided report.
    """
    if index_dict is None:
        index_dict = IndexDictionary()
        
    module_ids = sorted(_collect_module_ids(report))
    for module_id in module_ids:
        index_dict.get_module_id(module_id)
        
    # Also collect artifact IDs
    for key in report.get("artifacts", {}).keys():
        index_dict.get_artifact_id(key)
        
    return index_dict


# ==========================================================
# COMPACTION HELPERS
# ==========================================================

# Keys whose values are lists of module-table indices (rather than counts,
# ranks, or raw module-id strings) get an explicit "_module_indices" suffix
# so the key name alone disambiguates them - no need to rely on a reader
# noticing _format_note before interpreting e.g. "consumers": [61].
_INDEX_KEY_RENAMES = {
    "consumers": "consumer_module_indices",
    "direct_calls": "direct_calls_module_indices",
    "callback_calls": "callback_calls_module_indices",
    "event_bindings": "event_bindings_module_indices",
    "runtime_calls": "runtime_calls_module_indices",
    "api_imports": "api_imports_module_indices",
    "inheritance": "inheritance_module_indices",
    "ambiguous_calls": "ambiguous_calls_module_indices",
}


def _renamed(key: str) -> str:
    """Applies the index-key rename if this key holds module indices."""

    return _INDEX_KEY_RENAMES.get(key, key)


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
            compact[_renamed(category)] = compacted_values
        else:
            compact[_renamed(category)] = _idx_list(values, index_of)

    return compact


# ==========================================================
# MAIN TRANSFORM
# ==========================================================


def compact_artifact_report(report: dict, index_dict: IndexDictionary = None) -> dict:
    """
    Transforms the full artifact report (as returned by
    generate_artifact_usage_report) into a compact version.

    Schema v2 changes vs v1:
    - shared_artifacts full list replaced by shared_artifact_keys (list of str).
    - No inline usage block per artifact (moved to sidecar file).
    - artifact_id field preserved inside each compact artifact entry.
    - _format_version: "2" for downstream validation.

    ZERO data loss - the same information encoded differently.
    The result has a different shape than the original, but every fact
    is reproducible 1:1 via "modules"[index].
    """

    index_dict = build_module_index(report, index_dict)

    compact_artifacts = {}

    for key, artifact in report.get("artifacts", {}).items():
        definer = artifact.get("definer_module")
        consumers = artifact.get("consumers", []) or []
        
        a_id = index_dict.get_artifact_id(key)

        entry = {
            "artifact_id": a_id,
            "kind": artifact.get("kind"),
            "definer_module": index_dict.get_module_id(definer) if definer else None,
            "consumer_module_indices": [index_dict.get_module_id(c) for c in consumers],
            "consumer_count": artifact.get("consumer_count", len(consumers)),
        }

        # Schema v2: no inline usage — it lives in the sidecar file.
        legacy_usage = artifact.get("usage")
        if legacy_usage:
            compacted_usage = _compact_usage(legacy_usage, index_dict.module_to_id)
            if compacted_usage:
                entry["usage"] = compacted_usage

        compact_artifacts[a_id] = entry

    compact_clusters = []

    for cluster in report.get("shared_usage_clusters", []) or []:
        compact_clusters.append(
            {
                "modules": [index_dict.get_module_id(m) for m in cluster.get("modules", [])],
                "size": cluster.get("size"),
                "shared_artifact_count": cluster.get("shared_artifact_count"),
                "shared_artifacts": [
                    {
                        "artifact_id": index_dict.get_artifact_id(a.get("artifact_id")) if a.get("artifact_id") else None,
                        "consumer_module_indices": [index_dict.get_module_id(c) for c in a.get("consumers", [])],
                    }
                    for a in cluster.get("shared_artifacts", []) or []
                ],
            }
        )

    compact_candidates = []

    for candidate in report.get("core_extraction_candidates", []) or []:
        compact_candidates.append(
            {
                "consumer_modules": [index_dict.get_module_id(m) for m in candidate.get("consumer_modules", [])],
                "likely_core_modules": [index_dict.get_module_id(m) for m in candidate.get("likely_core_modules", [])],
                "shared_artifact_count": candidate.get("shared_artifact_count"),
                "top_shared_artifacts": [
                    {
                        "artifact_id": index_dict.get_artifact_id(a.get("artifact_id")) if a.get("artifact_id") else None,
                        "used_by": [index_dict.get_module_id(m) for m in a.get("used_by", [])],
                    }
                    for a in candidate.get("top_shared_artifacts", []) or []
                ],
                "reason": candidate.get("reason"),
            }
        )

    full_artifact_count = report.get("artifact_count", len(report.get("artifacts", {})))

    compact_report = {
        "_format_version": "3",
        "_format_note": (
            "Schema v3. Completely detached from text identifiers. Numbers inside 'definer_module' and any key ending in "
            "'_module_indices' are INDEXES into the master 'index_dictionary.json' "
            "Artifact keys are also A-prefixed IDs (e.g. A1, A2) mapping to the master dictionary. "
            "Artifacts with zero consumers are omitted from this report entirely."
        ),
        "runtime": report.get("runtime", {}),
        "module_count": report.get("module_count"),
        "full_artifact_count": full_artifact_count,
        "artifact_count": len(compact_artifacts),
        "shared_artifact_count": report.get("shared_artifact_count"),
        "artifacts": dict(sorted(compact_artifacts.items())),
        # Keys only — look up in artifacts dict for details.
        "shared_artifact_keys": [index_dict.get_artifact_id(k) for k in report.get("shared_artifact_keys", [])],
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


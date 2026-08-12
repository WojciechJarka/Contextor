"""
contextor/core/reporting_layer/artifact_usage_report_compact.py

COMPACT VERSION of the artifact usage report.

Auxiliary representation of the report produced by
generate_artifact_usage_report(). It does not replace the source report.

Responsibilities:

- builds a stable module/artifact index through IndexDictionary;
- replaces textual module identifiers with integer module IDs;
- replaces artifact identifiers with A-prefixed artifact IDs;
- removes empty usage categories;
- preserves shared-artifact references without duplicating artifact data;
- keeps the compact representation deterministic and JSON-safe.

Schema version: 3

The source of truth remains generate_artifact_usage_report().
"""

from __future__ import annotations

import json
import os
from typing import Any

from contextor.core.reporting_engine.dictionary import IndexDictionary


# ==========================================================
# MODULE / ARTIFACT INDEX
# ==========================================================


def _collect_module_ids(report: dict) -> set[str]:
    """
    Collect all module identifiers known to occur in the report.

    Only fields with known module semantics are inspected.
    Generic recursive searching is intentionally avoided.
    """
    ids: set[str] = set()

    for artifact in report.get("artifacts", {}).values():
        if not isinstance(artifact, dict):
            continue

        definer = artifact.get("definer_module")
        if isinstance(definer, str) and definer:
            ids.add(definer)

        for consumer in artifact.get("consumers", []) or []:
            if isinstance(consumer, str) and consumer:
                ids.add(consumer)

    for cluster in report.get("shared_usage_clusters", []) or []:
        if not isinstance(cluster, dict):
            continue

        for module_id in cluster.get("modules", []) or []:
            if isinstance(module_id, str) and module_id:
                ids.add(module_id)

        # Legacy representation.
        for artifact in cluster.get("shared_artifacts", []) or []:
            if not isinstance(artifact, dict):
                continue

            definer = artifact.get("definer_module")
            if isinstance(definer, str) and definer:
                ids.add(definer)

            for consumer in artifact.get("consumers", []) or []:
                if isinstance(consumer, str) and consumer:
                    ids.add(consumer)

    for candidate in report.get(
        "core_extraction_candidates",
        [],
    ) or []:
        if not isinstance(candidate, dict):
            continue

        for module_id in candidate.get(
            "consumer_modules",
            [],
        ) or []:
            if isinstance(module_id, str) and module_id:
                ids.add(module_id)

        for module_id in candidate.get(
            "likely_core_modules",
            [],
        ) or []:
            if isinstance(module_id, str) and module_id:
                ids.add(module_id)

        # Legacy representation.
        for artifact in candidate.get(
            "top_shared_artifacts",
            [],
        ) or []:
            if not isinstance(artifact, dict):
                continue

            defined_in = artifact.get("defined_in")
            if isinstance(defined_in, str) and defined_in:
                ids.add(defined_in)

            for consumer in artifact.get(
                "used_by",
                [],
            ) or []:
                if isinstance(consumer, str) and consumer:
                    ids.add(consumer)

    return ids


def _collect_artifact_ids(report: dict) -> set[str]:
    """
    Collect all artifact identifiers that may require indexing.

    The primary artifact dictionary is authoritative.

    Legacy shared-artifact/candidate structures are also inspected so
    their references can be represented safely when encountered.
    """
    ids: set[str] = set()

    for artifact_key in report.get("artifacts", {}).keys():
        if isinstance(artifact_key, str) and artifact_key:
            ids.add(artifact_key)

    for cluster in report.get("shared_usage_clusters", []) or []:
        if not isinstance(cluster, dict):
            continue

        for artifact_key in cluster.get(
            "shared_artifact_keys",
            [],
        ) or []:
            if isinstance(artifact_key, str) and artifact_key:
                ids.add(artifact_key)

        for artifact in cluster.get(
            "shared_artifacts",
            [],
        ) or []:
            if not isinstance(artifact, dict):
                continue

            artifact_id = artifact.get("artifact_id")
            if isinstance(artifact_id, str) and artifact_id:
                ids.add(artifact_id)

    for candidate in report.get(
        "core_extraction_candidates",
        [],
    ) or []:
        if not isinstance(candidate, dict):
            continue

        for artifact_key in candidate.get(
            "shared_artifact_keys",
            [],
        ) or []:
            if isinstance(artifact_key, str) and artifact_key:
                ids.add(artifact_key)

        for artifact in candidate.get(
            "top_shared_artifacts",
            [],
        ) or []:
            if not isinstance(artifact, dict):
                continue

            artifact_id = artifact.get("artifact_id")
            if isinstance(artifact_id, str) and artifact_id:
                ids.add(artifact_id)

    return ids


def build_module_index(
    report: dict,
    index_dict: IndexDictionary | None = None,
) -> IndexDictionary:
    """
    Populate the provided IndexDictionary.

    Identity assignment is delegated entirely to IndexDictionary.
    """
    if index_dict is None:
        raise ValueError(
            "index_dict must be provided to build_module_index"
        )

    for module_id in sorted(_collect_module_ids(report)):
        index_dict.get_module_id(module_id)

    for artifact_id in sorted(_collect_artifact_ids(report)):
        index_dict.get_artifact_id(artifact_id)

    return index_dict


# ==========================================================
# COMPACTION HELPERS
# ==========================================================


_INDEX_KEY_RENAMES: dict[str, str] = {
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
    """Rename a usage category containing module indexes."""
    return _INDEX_KEY_RENAMES.get(key, key)


def _idx(
    module_id: str | None,
    index_of: dict[str, int],
) -> int | str | None:
    """
    Convert a module identifier to its compact index.

    Unknown identifiers are preserved instead of silently discarded.
    """
    if module_id is None:
        return None

    return index_of.get(module_id, module_id)


def _idx_list(
    module_ids: list[str] | None,
    index_of: dict[str, int],
) -> list[int | str | None]:
    """Convert module identifiers to compact indexes."""
    return [
        _idx(module_id, index_of)
        for module_id in (module_ids or [])
    ]


def _artifact_id(
    artifact_key: str,
    index_dict: IndexDictionary,
) -> str:
    """Resolve one artifact identifier through the master index."""
    return index_dict.get_artifact_id(artifact_key)


def _compact_usage(
    usage: dict,
    index_of: dict[str, int],
) -> dict[str, Any]:
    """
    Compact an artifact usage mapping.

    Empty categories are omitted.

    Detail records preserve all metadata while converting only their
    module-bearing ``module`` field.
    """
    compact: dict[str, Any] = {}

    for category, values in (usage or {}).items():
        if not values:
            continue

        if category.endswith("_detail"):
            compacted_values: list[Any] = []

            for item in values:
                if isinstance(item, dict):
                    compact_item = dict(item)

                    if "module" in compact_item:
                        compact_item["module"] = _idx(
                            compact_item.get("module"),
                            index_of,
                        )

                    compacted_values.append(compact_item)
                else:
                    compacted_values.append(
                        _idx(item, index_of)
                    )

            if compacted_values:
                compact[_renamed(category)] = compacted_values

            continue

        if category == "ambiguous_calls":
            compacted_values = []

            for item in values:
                if isinstance(item, dict):
                    compact_item = dict(item)

                    if "module" in compact_item:
                        compact_item["module"] = _idx(
                            compact_item.get("module"),
                            index_of,
                        )

                    compacted_values.append(compact_item)
                else:
                    compacted_values.append(
                        _idx(item, index_of)
                    )

            if compacted_values:
                compact[_renamed(category)] = compacted_values

            continue

        compacted_values = _idx_list(
            values,
            index_of,
        )

        if compacted_values:
            compact[_renamed(category)] = compacted_values

    return compact


def _compact_cluster(
    cluster: dict,
    index_dict: IndexDictionary,
) -> dict[str, Any]:
    """
    Compact one shared-usage cluster.

    Schema v3 stores artifact references only.
    """
    compact: dict[str, Any] = {
        "modules": sorted(
            index_dict.get_module_id(module_id)
            for module_id in cluster.get(
                "modules",
                [],
            )
            or []
        ),
        "size": cluster.get("size"),
        "shared_artifact_count": cluster.get(
            "shared_artifact_count"
        ),
    }

    artifact_keys = cluster.get("shared_artifact_keys")

    if artifact_keys is not None:
        compact["shared_artifact_keys"] = sorted(
            _artifact_id(
                artifact_id,
                index_dict,
            )
            for artifact_id in artifact_keys
            if isinstance(artifact_id, str)
        )
    else:
        legacy_ids: list[str] = []

        for artifact in cluster.get(
            "shared_artifacts",
            [],
        ) or []:
            if not isinstance(artifact, dict):
                continue

            artifact_id = artifact.get("artifact_id")

            if isinstance(artifact_id, str):
                legacy_ids.append(
                    _artifact_id(
                        artifact_id,
                        index_dict,
                    )
                )

        compact["shared_artifact_keys"] = sorted(
            set(legacy_ids)
        )

    return compact


def _compact_candidate(
    candidate: dict,
    index_dict: IndexDictionary,
) -> dict[str, Any]:
    """
    Compact one core-extraction candidate.

    Artifact definitions are represented only by IDs.
    """
    compact: dict[str, Any] = {
        "consumer_modules": sorted(
            index_dict.get_module_id(module_id)
            for module_id in candidate.get(
                "consumer_modules",
                [],
            )
            or []
        ),
        "likely_core_modules": sorted(
            index_dict.get_module_id(module_id)
            for module_id in candidate.get(
                "likely_core_modules",
                [],
            )
            or []
        ),
        "shared_artifact_count": candidate.get(
            "shared_artifact_count"
        ),
        "reason": candidate.get("reason"),
    }

    artifact_keys = candidate.get(
        "shared_artifact_keys"
    )

    if artifact_keys is not None:
        compact["top_shared_artifact_keys"] = sorted(
            _artifact_id(
                artifact_id,
                index_dict,
            )
            for artifact_id in artifact_keys
            if isinstance(artifact_id, str)
        )
    else:
        legacy_ids: list[str] = []

        for artifact in candidate.get(
            "top_shared_artifacts",
            [],
        ) or []:
            if not isinstance(artifact, dict):
                continue

            artifact_id = artifact.get("artifact_id")

            if isinstance(artifact_id, str):
                legacy_ids.append(
                    _artifact_id(
                        artifact_id,
                        index_dict,
                    )
                )

        compact["top_shared_artifact_keys"] = sorted(
            set(legacy_ids)
        )

    return compact


# ==========================================================
# MAIN TRANSFORM
# ==========================================================


def compact_artifact_report(
    report: dict,
    index_dict: IndexDictionary | None = None,
) -> dict:
    """
    Transform the full artifact usage report into schema-v3 form.

    The original report is never mutated.

    Schema v3:

    - module IDs become integer indexes;
    - artifact IDs become A-prefixed identifiers;
    - artifact definitions occur once under ``artifacts``;
    - shared structures contain references only;
    - empty usage categories are removed;
    - zero-consumer artifacts are omitted from the compact table.
    """
    if not isinstance(report, dict):
        raise TypeError("report must be a dict")

    if index_dict is None:
        raise ValueError(
            "index_dict must be provided to compact_artifact_report"
        )

    build_module_index(
        report,
        index_dict,
    )

    compact_artifacts: dict[str, dict[str, Any]] = {}

    for artifact_key, artifact in sorted(
        report.get("artifacts", {}).items(),
        key=lambda item: str(item[0]),
    ):
        if not isinstance(artifact, dict):
            continue

        definer = artifact.get("definer_module")
        consumers = artifact.get(
            "consumers",
            [],
        ) or []

        # Compact report intentionally contains only consumed artifacts.
        if not consumers:
            continue

        artifact_id = _artifact_id(
            artifact_key,
            index_dict,
        )

        entry: dict[str, Any] = {
            "artifact_id": artifact_id,
            "kind": artifact.get("kind"),
            "definer_module": (
                index_dict.get_module_id(definer)
                if definer
                else None
            ),
            "consumer_module_indices": sorted(
                index_dict.get_module_id(consumer)
                for consumer in consumers
                if isinstance(consumer, str)
            ),
            "consumer_count": artifact.get(
                "consumer_count",
                len(consumers),
            ),
        }

        legacy_usage = artifact.get("usage")

        if isinstance(legacy_usage, dict):
            compacted_usage = _compact_usage(
                legacy_usage,
                index_dict.module_to_id,
            )

            if compacted_usage:
                entry["usage"] = compacted_usage

        compact_artifacts[artifact_id] = entry

    compact_clusters = [
        _compact_cluster(
            cluster,
            index_dict,
        )
        for cluster in report.get(
            "shared_usage_clusters",
            [],
        )
        or []
        if isinstance(cluster, dict)
    ]

    compact_candidates = [
        _compact_candidate(
            candidate,
            index_dict,
        )
        for candidate in report.get(
            "core_extraction_candidates",
            [],
        )
        or []
        if isinstance(candidate, dict)
    ]

    full_artifact_count = report.get(
        "artifact_count",
        len(report.get("artifacts", {})),
    )

    source_shared_keys = report.get(
        "shared_artifact_keys",
        [],
    ) or []

    compact_shared_keys = sorted(
        _artifact_id(
            artifact_key,
            index_dict,
        )
        for artifact_key in source_shared_keys
        if isinstance(artifact_key, str)
    )

    compact_report: dict[str, Any] = {
        "_format_version": "3",
        "_format_note": (
            "Schema v3. Module identifiers are integer indexes into "
            "the master index dictionary. Artifact identifiers are "
            "A-prefixed IDs mapping to the master artifact dictionary. "
            "Artifact definitions are stored once under 'artifacts'. "
            "Shared-artifact structures contain references only. "
            "Artifacts with zero consumers are omitted from this "
            "compact report."
        ),
        "runtime": report.get(
            "runtime",
            {},
        ),
        "module_count": report.get(
            "module_count"
        ),
        "full_artifact_count": full_artifact_count,
        "artifact_count": len(compact_artifacts),
        "shared_artifact_count": report.get(
            "shared_artifact_count"
        ),
        "artifacts": dict(
            sorted(
                compact_artifacts.items(),
                key=lambda item: item[0],
            )
        ),
        "shared_artifact_keys": compact_shared_keys,
        "shared_usage_clusters": compact_clusters,
        "core_extraction_candidates": compact_candidates,
    }

    if "debug_info" in report:
        compact_report["debug_info"] = report["debug_info"]

    return compact_report


# ==========================================================
# BLOCK-PER-LINE WRITER
# ==========================================================


def _line(obj: Any) -> str:
    """Serialize one JSON value into a single line."""
    return json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def save_compact_artifact_report(
    report: dict,
    path: str,
) -> None:
    """
    Save a compact artifact report using one artifact per line.

    Top-level metadata remains one JSON value per line.
    The ``artifacts`` mapping is expanded so every artifact occupies
    one line.
    """
    from contextor.core.reporting_engine.formatting import (
        resolve_report_path,
    )

    target = resolve_report_path(path)

    os.makedirs(
        target.parent,
        exist_ok=True,
    )

    artifacts = report.get(
        "artifacts",
        {},
    )

    other_fields = {
        key: value
        for key, value in report.items()
        if key != "artifacts"
    }

    with open(
        target,
        "w",
        encoding="utf-8",
    ) as f:
        f.write("{\n")

        top_level_items = list(
            other_fields.items()
        )

        for index, (key, value) in enumerate(
            top_level_items
        ):
            f.write(
                f"  {_line(key)}: {_line(value)},\n"
            )

        f.write('  "artifacts": {\n')

        artifact_items = sorted(
            artifacts.items(),
            key=lambda item: str(item[0]),
        )

        for index, (key, value) in enumerate(
            artifact_items
        ):
            comma = (
                ","
                if index < len(artifact_items) - 1
                else ""
            )

            f.write(
                f"    {_line(key)}: {_line(value)}{comma}\n"
            )

        f.write("  }\n")
        f.write("}\n")


# ==========================================================
# PUBLIC EXPORTS
# ==========================================================


__all__ = [
    "compact_artifact_report",
    "build_module_index",
    "save_compact_artifact_report",
]
"""Pure reconciliation of retained type-only import evidence."""

from dataclasses import replace
import re

from contextor.core.domain.imports import ImportRef
from contextor.core.domain.module import Module
from contextor.core.symbol_engine.indexer import (
    _classify_type_only_modules,
)


def _copy_refs(refs):
    return [
        replace(ref, names=list(ref.names))
        for ref in refs
    ]


def _valid_fingerprint(value):
    return (
        type(value) is str
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    )


def _valid_record_map(records, fingerprints, required):
    if type(records) is not dict or set(records) != required:
        return False

    return all(
        type(record) is tuple
        and len(record) == 2
        and type(record[0]) is bool
        and record[1] == fingerprints[module_id]
        for module_id, record in records.items()
    )


def _valid_baseline(modules, evidence):
    if (
        type(evidence) is not dict
        or type(evidence.get("schema_version")) is not int
        or evidence["schema_version"] != 2
    ):
        return False

    required = (
        "candidate_imports_by_module",
        "source_fingerprints_by_module",
        "initializer_passivity_by_module",
        "marker_mutation_by_module",
        "opaque_effects_by_module",
        "skipped_source_paths",
        "unindexed_python_sources_present",
        "unindexed_import_artifacts_present",
        "global_policy_satisfied",
    )

    if any(key not in evidence for key in required):
        return False

    if any(
        type(evidence[key]) is not bool
        for key in (
            "unindexed_python_sources_present",
            "unindexed_import_artifacts_present",
            "global_policy_satisfied",
        )
    ):
        return False

    if (
        type(modules) is not dict
        or any(
            type(key) is not str or type(value) is not Module
            for key, value in modules.items()
        )
    ):
        return False

    ids = set(modules)
    fingerprints = evidence["source_fingerprints_by_module"]

    if (
        type(fingerprints) is not dict
        or set(fingerprints) != ids
        or not all(
            _valid_fingerprint(value)
            for value in fingerprints.values()
        )
    ):
        return False

    for key in (
        "marker_mutation_by_module",
        "opaque_effects_by_module",
    ):
        if not _valid_record_map(
            evidence[key], fingerprints, ids
        ):
            return False

    initializer_ids = {
        module_id
        for module_id in ids
        if module_id.endswith(".__init__")
    }

    if not _valid_record_map(
        evidence["initializer_passivity_by_module"],
        fingerprints,
        initializer_ids,
    ):
        return False

    skipped = evidence["skipped_source_paths"]

    if (
        type(skipped) is not tuple
        or any(
            type(path) is not str or not path
            for path in skipped
        )
        or tuple(sorted(set(skipped))) != skipped
    ):
        return False

    candidates = evidence["candidate_imports_by_module"]

    if (
        type(candidates) is not dict
        or not set(candidates).issubset(ids)
    ):
        return False

    for module_id, module in modules.items():
        if (
            type(module.imports) is not list
            or any(
                type(ref) is not ImportRef
                or type(ref.names) is not list
                or type(ref.type_only) is not bool
                for ref in module.imports
            )
        ):
            return False

        if module_id not in candidates:
            if any(ref.type_only for ref in module.imports):
                return False
            continue

        raw = candidates[module_id]

        if (
            type(raw) is not tuple
            or len(raw) != len(module.imports)
        ):
            return False

        if any(
            type(ref) is not ImportRef
            or type(ref.names) is not list
            or type(ref.type_only) is not bool
            for ref in raw
        ):
            return False

        if not any(ref.type_only for ref in raw):
            return False

        for candidate_ref, final_ref in zip(
            raw, module.imports
        ):
            if final_ref.type_only and not candidate_ref.type_only:
                return False

            if replace(
                candidate_ref,
                type_only=final_ref.type_only,
            ) != final_ref:
                return False

    return True


def _fail_closed(modules):
    result = dict(modules)

    for module_id, module in modules.items():
        if any(
            type(ref.type_only) is not bool or ref.type_only
            for ref in module.imports
        ):
            result[module_id] = replace(
                module,
                imports=[
                    replace(
                        ref,
                        type_only=False,
                        names=list(ref.names),
                    )
                    for ref in module.imports
                ],
            )

    return result, {}


def reclassify_incremental_type_only(
    modules,
    *,
    previous_modules,
    previous_evidence,
    changed_module_id,
    changed_source_path,
    changed_imports,
    changed_source_evidence,
    deleted=False,
):
    """Reclassify one change using retained project evidence."""

    if (
        type(modules) is not dict
        or any(
            type(value) is not Module
            for value in modules.values()
        )
    ):
        raise TypeError("modules must be a module mapping")

    if any(
        type(module.imports) is not list
        or any(
            type(ref) is not ImportRef
            or type(ref.names) is not list
            for ref in module.imports
        )
        for module in modules.values()
    ):
        raise TypeError("modules contain invalid import records")

    if any(
        type(ref.type_only) is not bool
        for module in modules.values()
        for ref in module.imports
    ):
        return _fail_closed(modules)

    if not _valid_baseline(
        previous_modules, previous_evidence
    ):
        return _fail_closed(modules)

    if (
        type(changed_module_id) is not str
        or not changed_module_id
        or type(changed_source_path) is not str
        or not changed_source_path
        or type(deleted) is not bool
        or (
            set(modules) - {changed_module_id}
        ) != (
            set(previous_modules) - {changed_module_id}
        )
    ):
        return _fail_closed(modules)

    if any(
        modules[module_id] != previous_modules[module_id]
        for module_id in (
            set(modules) & set(previous_modules)
        ) - {changed_module_id}
    ):
        return _fail_closed(modules)

    if deleted:
        if changed_module_id in modules:
            return _fail_closed(modules)
    else:
        if (
            changed_module_id not in modules
            or type(changed_imports) is not list
            or any(
                type(ref) is not ImportRef
                or type(ref.names) is not list
                or type(ref.type_only) is not bool
                for ref in changed_imports
            )
            or type(changed_source_evidence) is not dict
            or type(
                changed_source_evidence.get("schema_version")
            ) is not int
            or changed_source_evidence["schema_version"] != 1
            or not _valid_fingerprint(
                changed_source_evidence.get(
                    "source_fingerprint"
                )
            )
            or any(
                type(changed_source_evidence.get(key)) is not bool
                for key in (
                    "initializer_passive",
                    "marker_mutation",
                    "opaque_effects",
                )
            )
        ):
            return _fail_closed(modules)

    evidence = {
        "schema_version": 2,
        "candidate_imports_by_module": {
            key: tuple(_copy_refs(refs))
            for key, refs in previous_evidence[
                "candidate_imports_by_module"
            ].items()
        },
        "source_fingerprints_by_module": dict(
            previous_evidence["source_fingerprints_by_module"]
        ),
        "initializer_passivity_by_module": dict(
            previous_evidence["initializer_passivity_by_module"]
        ),
        "marker_mutation_by_module": dict(
            previous_evidence["marker_mutation_by_module"]
        ),
        "opaque_effects_by_module": dict(
            previous_evidence["opaque_effects_by_module"]
        ),
        "skipped_source_paths": tuple(
            previous_evidence["skipped_source_paths"]
        ),
        "unindexed_python_sources_present": (
            previous_evidence[
                "unindexed_python_sources_present"
            ]
        ),
        "unindexed_import_artifacts_present": (
            previous_evidence[
                "unindexed_import_artifacts_present"
            ]
        ),
    }

    evidence_maps = (
        "candidate_imports_by_module",
        "source_fingerprints_by_module",
        "initializer_passivity_by_module",
        "marker_mutation_by_module",
        "opaque_effects_by_module",
    )

    if deleted:
        for key in evidence_maps:
            evidence[key].pop(changed_module_id, None)
    else:
        fingerprint = changed_source_evidence[
            "source_fingerprint"
        ]

        evidence[
            "source_fingerprints_by_module"
        ][changed_module_id] = fingerprint

        evidence[
            "marker_mutation_by_module"
        ][changed_module_id] = (
            changed_source_evidence["marker_mutation"],
            fingerprint,
        )

        evidence[
            "opaque_effects_by_module"
        ][changed_module_id] = (
            changed_source_evidence["opaque_effects"],
            fingerprint,
        )

        if changed_module_id.endswith(".__init__"):
            evidence[
                "initializer_passivity_by_module"
            ][changed_module_id] = (
                changed_source_evidence["initializer_passive"],
                fingerprint,
            )
        else:
            evidence[
                "initializer_passivity_by_module"
            ].pop(changed_module_id, None)

        if any(ref.type_only for ref in changed_imports):
            evidence[
                "candidate_imports_by_module"
            ][changed_module_id] = tuple(
                _copy_refs(changed_imports)
            )
        else:
            evidence[
                "candidate_imports_by_module"
            ].pop(changed_module_id, None)

    evidence["skipped_source_paths"] = tuple(
        path
        for path in evidence["skipped_source_paths"]
        if path != changed_source_path
    )

    restored = dict(modules)

    for module_id, refs in evidence[
        "candidate_imports_by_module"
    ].items():
        restored[module_id] = replace(
            restored[module_id],
            imports=_copy_refs(refs),
        )

    if not deleted:
        restored[changed_module_id] = replace(
            restored[changed_module_id],
            imports=_copy_refs(changed_imports),
        )

    classified, global_policy = (
        _classify_type_only_modules(
            restored,
            source_fingerprints_by_module=evidence[
                "source_fingerprints_by_module"
            ],
            initializer_passivity_by_module=evidence[
                "initializer_passivity_by_module"
            ],
            marker_mutation_by_module=evidence[
                "marker_mutation_by_module"
            ],
            opaque_effects_by_module=evidence[
                "opaque_effects_by_module"
            ],
            skipped_source_paths=evidence[
                "skipped_source_paths"
            ],
            unindexed_python_sources_present=evidence[
                "unindexed_python_sources_present"
            ],
            unindexed_import_artifacts_present=evidence[
                "unindexed_import_artifacts_present"
            ],
        )
    )

    evidence["global_policy_satisfied"] = global_policy

    for key in evidence_maps:
        evidence[key] = dict(sorted(evidence[key].items()))

    return classified, evidence

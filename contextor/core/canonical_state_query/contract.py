"""Public, versioned contract for read-only canonical LIVE projections."""

from __future__ import annotations

from typing import Any

CANONICAL_QUERY_SCHEMA_VERSION = "1.0"
CANONICAL_QUERY_SCHEMA_VERSION_V1_1 = "1.1"
LANGUAGE_VERSION = "1.0"
LANGUAGE_VERSION_V1_1 = "1.1"

DEFAULT_LIMIT = 20
MAX_LIMIT = 200
DEFAULT_EVIDENCE_LIMIT = 3
MAX_FILTERS = 10
MAX_SELECT_FIELDS = 20
MAX_IN_VALUES = 50
MAX_REQUEST_BYTES = 16 * 1024


def _field(
    field_type: str,
    operators: list[str],
    *,
    nullable: bool = False,
    computed: bool = False,
    derivation: str | None = None,
    source: str | None = None,
    selectable: bool = True,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": field_type,
        "filterable": bool(operators),
        "allowed_operators": operators,
        "selectable": selectable,
        "nullable": nullable,
        "computed": computed,
    }
    result["derivation" if computed else "source"] = derivation if computed else source
    return result


STRING_OPERATORS = ["eq", "neq", "contains", "starts_with", "ends_with", "in"]
INT_OPERATORS = ["eq", "neq", "gt", "gte", "lt", "lte", "in"]
ARRAY_OPERATORS = [
    "count_eq",
    "count_gt",
    "count_gte",
    "count_lt",
    "count_lte",
    "is_empty",
]

SCHEMA_V1: dict[str, Any] = {
    "version": CANONICAL_QUERY_SCHEMA_VERSION,
    "roots": {
        "modules": {
            "description": "Modules currently present in canonical LIVE state.",
            "canonical_order": ["module_name"],
            "fields": {
                "module_name": _field("string", STRING_OPERATORS, source="modules map key"),
                "module_id": _field("string", STRING_OPERATORS, source="Module.module_id"),
                "path": _field("string", STRING_OPERATORS, source="Module.path"),
                "import_count": _field(
                    "int", INT_OPERATORS, computed=True, derivation="len(Module.imports)"
                ),
                "imports": _field("array<ImportRef>", ARRAY_OPERATORS, source="Module.imports"),
            },
        },
        "artifacts": {
            "description": (
                "Symbols defined in modules, regardless of public visibility or export status."
            ),
            "canonical_order": ["module_name", "artifact_name"],
            "fields": {
                "artifact_name": _field(
                    "string", STRING_OPERATORS, source="artifact record own_symbols entry"
                ),
                "full_name": _field(
                    "string",
                    STRING_OPERATORS,
                    computed=True,
                    derivation="module_name + '::' + artifact_name",
                ),
                "module_name": _field("string", STRING_OPERATORS, source="artifacts map key"),
                "kind": _field(
                    "enum<class|function|method|global|ambiguous>",
                    ["eq", "neq", "in"],
                    computed=True,
                    derivation=(
                        "membership in symbols classes/functions/methods/globals; "
                        "ambiguous when multiple categories match"
                    ),
                ),
                "signature": _field(
                    "string",
                    ["eq", "neq", "contains", "starts_with", "ends_with", "is_null"],
                    nullable=True,
                    computed=True,
                    derivation=(
                        "symbols.signatures[artifact_name], normalized to null when absent or empty"
                    ),
                ),
                "consumer_data_available": _field(
                    "bool", ["eq", "neq"], computed=True, derivation="artifact_name in consumers"
                ),
                "consumer_count": _field(
                    "int",
                    ["eq", "neq", "gt", "gte", "lt", "lte", "is_null"],
                    nullable=True,
                    computed=True,
                    derivation=(
                        "consumers[artifact_name].consumer_count.total; null when unavailable"
                    ),
                ),
                "consumers": _field(
                    "array<string>",
                    [*ARRAY_OPERATORS, "is_null"],
                    nullable=True,
                    computed=True,
                    derivation=(
                        "consumers[artifact_name].consumers; null when consumer data is unavailable"
                    ),
                ),
            },
        },
        "dependencies": {
            "description": "Flattened hard and soft dependency relationships.",
            "canonical_order": ["source", "target", "edge_type"],
            "record_identity": ["source", "target", "edge_type"],
            "fields": {
                "source": _field("string", STRING_OPERATORS, source="dependency edge source"),
                "target": _field("string", STRING_OPERATORS, source="dependency edge target"),
                "edge_type": _field(
                    "enum<hard|soft>", ["eq", "neq", "in"], source="dependency edge map"
                ),
            },
        },
    },
}

SCHEMA_V1_1: dict[str, Any] = {
    "version": CANONICAL_QUERY_SCHEMA_VERSION_V1_1,
    "roots": {
        "modules": {
            "description": "Modules currently present in canonical LIVE state.",
            "canonical_order": ["module_name"],
            "fields": {
                "module_name": _field("string", STRING_OPERATORS, source="modules map key"),
                "module_id": _field("string", STRING_OPERATORS, source="Module.module_id"),
                "path": _field("string", STRING_OPERATORS, source="Module.path"),
                "import_count": _field(
                    "int", INT_OPERATORS, computed=True, derivation="len(Module.imports)"
                ),
                "imports": _field("array<ImportRef>", ARRAY_OPERATORS, source="Module.imports"),
                "imports_truncated": _field(
                    "bool",
                    [],
                    computed=True,
                    selectable=False,
                    derivation="len(emitted imports) < import_count when imports is selected",
                ),
            },
        },
        "artifacts": {
            "description": (
                "Symbols defined in modules, regardless of public visibility or export status."
            ),
            "canonical_order": ["module_name", "artifact_name"],
            "fields": {
                "artifact_name": _field(
                    "string", STRING_OPERATORS, source="artifact record own_symbols entry"
                ),
                "full_name": _field(
                    "string",
                    STRING_OPERATORS,
                    computed=True,
                    derivation="module_name + '::' + artifact_name",
                ),
                "module_name": _field("string", STRING_OPERATORS, source="artifacts map key"),
                "kind": _field(
                    "enum<class|function|method|global|ambiguous>",
                    ["eq", "neq", "in"],
                    computed=True,
                    derivation=(
                        "membership in symbols classes/functions/methods/globals; "
                        "ambiguous when multiple categories match"
                    ),
                ),
                "signature": _field(
                    "string",
                    ["eq", "neq", "contains", "starts_with", "ends_with", "is_null"],
                    nullable=True,
                    computed=True,
                    derivation=(
                        "symbols.signatures[artifact_name], normalized to null when absent or empty"
                    ),
                ),
                "consumer_data_available": _field(
                    "bool", ["eq", "neq"], computed=True, derivation="artifact_name in consumers"
                ),
                "consumer_count": _field(
                    "int",
                    ["eq", "neq", "gt", "gte", "lt", "lte", "is_null"],
                    nullable=True,
                    computed=True,
                    derivation=(
                        "consumers[artifact_name].consumer_count.total; null when unavailable"
                    ),
                ),
                "consumers": _field(
                    "array<string>",
                    [*ARRAY_OPERATORS, "is_null"],
                    nullable=True,
                    computed=True,
                    derivation=(
                        "consumers[artifact_name].consumers; null when consumer data is unavailable"
                    ),
                ),
                "consumers_truncated": _field(
                    "bool",
                    [],
                    nullable=True,
                    computed=True,
                    selectable=False,
                    derivation=(
                        "len(emitted consumers) < consumer_count when consumers is selected and "
                        "available; null when unavailable"
                    ),
                ),
            },
        },
        "dependencies": {
            "description": "Flattened hard and soft dependency relationships.",
            "canonical_order": ["source", "target", "edge_type"],
            "record_identity": ["source", "target", "edge_type"],
            "fields": {
                "source": _field("string", STRING_OPERATORS, source="dependency edge source"),
                "target": _field("string", STRING_OPERATORS, source="dependency edge target"),
                "edge_type": _field(
                    "enum<hard|soft>", ["eq", "neq", "in"], source="dependency edge map"
                ),
            },
        },
    },
}

LANGUAGE_V1: dict[str, Any] = {
    "version": LANGUAGE_VERSION,
    "operators": [
        "eq", "neq", "contains", "starts_with", "ends_with", "in",
        "gt", "gte", "lt", "lte", "count_eq", "count_gt", "count_gte",
        "count_lt", "count_lte", "is_empty", "is_null",
    ],
    "filter_semantics": "flat AND in request order",
    "null_semantics": {
        "is_null": "matches null on nullable fields and takes no value",
        "other_operators": "null never matches",
        "is_empty": "null does not match; only an empty collection matches",
    },
    "limits": {
        "default_limit": DEFAULT_LIMIT,
        "max_limit": MAX_LIMIT,
        "max_filters": MAX_FILTERS,
        "max_select_fields": MAX_SELECT_FIELDS,
        "max_in_values": MAX_IN_VALUES,
        "max_request_bytes": MAX_REQUEST_BYTES,
    },
    "required_request_fields": [
        "schema_version", "language_version", "root", "filters", "select"
    ],
    "validation": "first error in deterministic contract order",
}

LANGUAGE_V1_1: dict[str, Any] = {
    "version": LANGUAGE_VERSION_V1_1,
    "operators": [
        "eq", "neq", "contains", "starts_with", "ends_with", "in",
        "gt", "gte", "lt", "lte", "count_eq", "count_gt", "count_gte",
        "count_lt", "count_lte", "is_empty", "is_null",
    ],
    "filter_semantics": "flat AND in request order",
    "null_semantics": {
        "is_null": "matches null on nullable fields and takes no value",
        "other_operators": "null never matches",
        "is_empty": "null does not match; only an empty collection matches",
    },
    "limits": {
        "default_limit": DEFAULT_LIMIT,
        "max_limit": MAX_LIMIT,
        "default_evidence_limit": DEFAULT_EVIDENCE_LIMIT,
        "max_filters": MAX_FILTERS,
        "max_select_fields": MAX_SELECT_FIELDS,
        "max_in_values": MAX_IN_VALUES,
        "max_request_bytes": MAX_REQUEST_BYTES,
    },
    "required_request_fields": [
        "schema_version", "language_version", "root", "filters", "select"
    ],
    "optional_request_fields": ["limit", "evidence_limit"],
    "validation": "first error in deterministic contract order",
}


SUPPORTED_PAIRS: set[tuple[str, str]] = {
    (CANONICAL_QUERY_SCHEMA_VERSION, LANGUAGE_VERSION),
    (CANONICAL_QUERY_SCHEMA_VERSION_V1_1, LANGUAGE_VERSION_V1_1),
}
SUPPORTED_SCHEMA_VERSIONS: set[str] = {s for s, _ in SUPPORTED_PAIRS}
SUPPORTED_LANGUAGE_VERSIONS: set[str] = {l for _, l in SUPPORTED_PAIRS}


def describe_contract(
    schema_version: str = CANONICAL_QUERY_SCHEMA_VERSION,
    language_version: str = LANGUAGE_VERSION,
) -> dict[str, Any]:
    """Return the complete public schema and language contract for a supported version pair."""
    if (schema_version, language_version) not in SUPPORTED_PAIRS:
        return {
            "status": "error",
            "error": {
                "code": "unsupported_version_pair",
                "message": "schema_version and language_version must be a supported contract pair.",
                "path": "$request",
                "details": {
                    "supported_pairs": [
                        {"schema_version": s, "language_version": l}
                        for s, l in sorted(SUPPORTED_PAIRS)
                    ]
                },
            },
        }
    if (schema_version, language_version) == (
        CANONICAL_QUERY_SCHEMA_VERSION_V1_1,
        LANGUAGE_VERSION_V1_1,
    ):
        return {
            "schema_version": CANONICAL_QUERY_SCHEMA_VERSION_V1_1,
            "language_version": LANGUAGE_VERSION_V1_1,
            "schema": SCHEMA_V1_1,
            "language": LANGUAGE_V1_1,
        }
    return {
        "schema_version": CANONICAL_QUERY_SCHEMA_VERSION,
        "language_version": LANGUAGE_VERSION,
        "schema": SCHEMA_V1,
        "language": LANGUAGE_V1,
    }

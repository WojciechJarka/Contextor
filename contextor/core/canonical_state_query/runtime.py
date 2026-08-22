"""Validation and bounded execution for the canonical LIVE projection DSL."""

from __future__ import annotations

import json
from typing import Any

from .contract import (
    DEFAULT_EVIDENCE_LIMIT,
    DEFAULT_LIMIT,
    LANGUAGE_VERSION,
    LANGUAGE_VERSION_V1_1,
    MAX_FILTERS,
    MAX_IN_VALUES,
    MAX_LIMIT,
    MAX_REQUEST_BYTES,
    MAX_SELECT_FIELDS,
    SCHEMA_V1,
    SCHEMA_V1_1,
    CANONICAL_QUERY_SCHEMA_VERSION,
    CANONICAL_QUERY_SCHEMA_VERSION_V1_1,
    SUPPORTED_PAIRS,
    SUPPORTED_SCHEMA_VERSIONS,
    SUPPORTED_LANGUAGE_VERSIONS,
)
from .projection import RECORD_BUILDERS
from contextor.core.analysis.state_manager import module_current_truth


def _error(code: str, message: str, path: str, **details: Any) -> dict[str, Any]:
    return {
        "status": "error",
        "error": {"code": code, "message": message, "path": path, "details": details},
    }


def _strict_type(value: Any, field_type: str) -> bool:
    if field_type == "string" or field_type.startswith("enum<"):
        return isinstance(value, str)
    if field_type == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if field_type == "bool":
        return isinstance(value, bool)
    return False


def _enum_values(field_type: str) -> set[str]:
    if not field_type.startswith("enum<"):
        return set()
    return set(field_type.removeprefix("enum<").removesuffix(">").split("|"))


def _validate_operator_value(
    filter_item: dict[str, Any], field: dict[str, Any], path: str
) -> dict[str, Any] | None:
    operator = filter_item["operator"]
    has_value = "value" in filter_item
    field_type = field["type"]
    if operator in {"is_empty", "is_null"}:
        if has_value:
            return _error(
                "operator_value_mismatch",
                f"Operator '{operator}' does not accept value.",
                f"{path}.value",
            )
        return None
    if not has_value:
        return _error(
            "operator_value_mismatch",
            f"Operator '{operator}' requires value.",
            f"{path}.value",
        )
    value = filter_item["value"]
    if operator == "in":
        if not isinstance(value, list) or not value:
            return _error(
                "operator_value_mismatch",
                "Operator 'in' requires a non-empty list.",
                f"{path}.value",
            )
        if len(value) > MAX_IN_VALUES:
            return _error(
                "invalid_filter",
                f"Operator 'in' accepts at most {MAX_IN_VALUES} values.",
                f"{path}.value",
                max_items=MAX_IN_VALUES,
            )
        if len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            return _error(
                "invalid_filter",
                "Operator 'in' does not accept duplicate values.",
                f"{path}.value",
            )
        if not all(_strict_type(item, field_type) for item in value):
            return _error(
                "operator_value_mismatch",
                "Every 'in' value must exactly match the field type.",
                f"{path}.value",
                expected_type=field_type,
            )
        enum_values = _enum_values(field_type)
        if enum_values and any(item not in enum_values for item in value):
            return _error(
                "operator_value_mismatch",
                "An enum value is outside the schema allowlist.",
                f"{path}.value",
                allowed_values=sorted(enum_values),
            )
        return None
    if operator.startswith("count_"):
        valid = isinstance(value, int) and not isinstance(value, bool) and value >= 0
    elif operator in {"contains", "starts_with", "ends_with"}:
        valid = isinstance(value, str) and bool(value)
    else:
        valid = _strict_type(value, field_type)
    if not valid:
        return _error(
            "operator_value_mismatch",
            "Filter value does not match the operator and field type.",
            f"{path}.value",
            expected_type=field_type,
        )
    enum_values = _enum_values(field_type)
    if enum_values and value not in enum_values:
        return _error(
            "operator_value_mismatch",
            "Enum value is outside the schema allowlist.",
            f"{path}.value",
            allowed_values=sorted(enum_values),
        )
    return None


def validate_request(request: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate one v1 or v1.1 request and return its normalized form or first error."""

    if not isinstance(request, dict):
        return None, _error("invalid_request", "Request must be an object.", "$request")

    schema_version_hint = request.get("schema_version")
    language_version = request.get("language_version")
    is_explicit_v1_1_pair = (
        schema_version_hint == CANONICAL_QUERY_SCHEMA_VERSION_V1_1
        and language_version == LANGUAGE_VERSION_V1_1
    )
    if is_explicit_v1_1_pair:
        allowed_keys = {
            "schema_version",
            "language_version",
            "root",
            "filters",
            "select",
            "limit",
            "evidence_limit",
        }
    else:
        allowed_keys = {
            "schema_version",
            "language_version",
            "root",
            "filters",
            "select",
            "limit",
        }

    unknown = sorted(str(key) for key in request if key not in allowed_keys)
    if unknown:
        return None, _error(
            "invalid_request",
            "Request contains unsupported fields.",
            unknown[0],
            unknown_fields=unknown,
        )

    for required in ("schema_version", "language_version", "root", "filters", "select"):
        if required not in request:
            return None, _error(
                "missing_required_field", f"Required field '{required}' is missing.", required
            )

    schema_version = request["schema_version"]
    assert language_version is not None

    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        return None, _error(
            "unsupported_schema_version",
            "Unsupported schema version.",
            "schema_version",
            supported_versions=sorted(SUPPORTED_SCHEMA_VERSIONS),
        )

    if language_version not in SUPPORTED_LANGUAGE_VERSIONS:
        return None, _error(
            "unsupported_language_version",
            "Unsupported language version.",
            "language_version",
            supported_versions=sorted(SUPPORTED_LANGUAGE_VERSIONS),
        )

    if (schema_version, language_version) not in SUPPORTED_PAIRS:
        return None, _error(
            "unsupported_version_pair",
            "schema_version and language_version must be a supported contract pair.",
            "$request",
            supported_pairs=[
                {"schema_version": s, "language_version": l}
                for s, l in sorted(SUPPORTED_PAIRS)
            ],
        )

    schema = SCHEMA_V1 if schema_version == CANONICAL_QUERY_SCHEMA_VERSION else SCHEMA_V1_1
    root = request["root"]
    if not isinstance(root, str) or root not in schema["roots"]:
        return None, _error(
            "unknown_root",
            "Unknown canonical projection root.",
            "root",
            allowed_roots=sorted(schema["roots"]),
        )

    filters = request["filters"]
    select = request["select"]
    if not isinstance(filters, list):
        return None, _error("invalid_request", "filters must be a list.", "filters")
    if not isinstance(select, list):
        return None, _error("invalid_request", "select must be a list.", "select")
    if len(filters) > MAX_FILTERS:
        return None, _error(
            "too_many_filters",
            f"At most {MAX_FILTERS} filters are allowed.",
            "filters",
            max_items=MAX_FILTERS,
        )
    if len(select) > MAX_SELECT_FIELDS:
        return None, _error(
            "too_many_select_fields",
            f"At most {MAX_SELECT_FIELDS} select fields are allowed.",
            "select",
            max_items=MAX_SELECT_FIELDS,
        )
    try:
        request_bytes = len(json.dumps(request, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError):
        return None, _error("invalid_request", "Request must be JSON serializable.", "$request")
    if request_bytes > MAX_REQUEST_BYTES:
        return None, _error(
            "request_too_complex",
            f"Request exceeds {MAX_REQUEST_BYTES} UTF-8 bytes.",
            "$request",
            max_bytes=MAX_REQUEST_BYTES,
            actual_bytes=request_bytes,
        )
    limit = request.get("limit", DEFAULT_LIMIT)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_LIMIT:
        return None, _error(
            "invalid_limit",
            f"limit must be an integer from 1 to {MAX_LIMIT}.",
            "limit",
            max_limit=MAX_LIMIT,
        )

    evidence_limit: int | None = None
    if language_version == LANGUAGE_VERSION_V1_1:
        if "evidence_limit" not in request:
            evidence_limit = DEFAULT_EVIDENCE_LIMIT
        else:
            raw_ev = request["evidence_limit"]
            if raw_ev is None:
                evidence_limit = None
            elif isinstance(raw_ev, int) and not isinstance(raw_ev, bool) and raw_ev >= 0:
                evidence_limit = raw_ev
            else:
                return None, _error(
                    "invalid_evidence_limit",
                    "evidence_limit must be a non-negative integer or null.",
                    "evidence_limit",
                )

    fields = schema["roots"][root]["fields"]
    seen_select: set[str] = set()
    for index, name in enumerate(select):
        if not isinstance(name, str):
            return None, _error(
                "unknown_field",
                "Select field names must be strings.",
                f"select[{index}]",
                field=name,
                allowed_fields=sorted(name for name, d in fields.items() if d["selectable"]),
            )
        if name in seen_select:
            return None, _error(
                "duplicate_select_field",
                "select contains duplicate fields.",
                f"select[{index}]",
                field=name,
            )
        seen_select.add(name)

    selected = select or [name for name, definition in fields.items() if definition["selectable"]]
    for index, name in enumerate(selected):
        if name not in fields:
            return None, _error(
                "unknown_field",
                "Unknown select field.",
                f"select[{index}]",
                field=name,
                allowed_fields=sorted(name for name, d in fields.items() if d["selectable"]),
            )
        if not fields[name]["selectable"]:
            return None, _error(
                "field_not_selectable", "Field is not selectable.", f"select[{index}]", field=name
            )

    for index, item in enumerate(filters):
        path = f"filters[{index}]"
        if not isinstance(item, dict):
            return None, _error("invalid_filter", "Filter must be an object.", path)
        if set(item) - {"field", "operator", "value"} or "field" not in item or "operator" not in item:
            return None, _error(
                "invalid_filter",
                "Filter requires field/operator and supports optional value only.",
                path,
            )
        name = item["field"]
        operator = item["operator"]
        if not isinstance(name, str) or name not in fields:
            return None, _error(
                "unknown_field",
                "Unknown filter field.",
                f"{path}.field",
                field=name,
                allowed_fields=sorted(fields),
            )
        definition = fields[name]
        if not definition["filterable"]:
            return None, _error(
                "field_not_filterable", "Field is not filterable.", f"{path}.field", field=name
            )
        if operator == "is_null" and not definition["nullable"]:
            return None, _error(
                "is_null_on_non_nullable",
                "is_null requires a nullable field.",
                f"{path}.operator",
                field=name,
            )
        if not isinstance(operator, str) or operator not in definition["allowed_operators"]:
            return None, _error(
                "invalid_operator_for_type",
                "Operator is not allowed for this field.",
                f"{path}.operator",
                field=name,
                operator=operator,
                allowed_operators=definition["allowed_operators"],
            )
        value_error = _validate_operator_value(item, definition, path)
        if value_error:
            return None, value_error

    return {
        "schema_version": schema_version,
        "language_version": language_version,
        "root": root,
        "filters": filters,
        "select": selected,
        "original_select": list(select),
        "limit": limit,
        "evidence_limit": evidence_limit,
    }, None


def _matches(record: dict[str, Any], filter_item: dict[str, Any]) -> bool:
    value = record[filter_item["field"]]
    operator = filter_item["operator"]
    if operator == "is_null":
        return value is None
    if value is None:
        return False
    if operator == "is_empty":
        return len(value) == 0
    expected = filter_item["value"]
    if operator.startswith("count_"):
        value = len(value)
        operator = operator.removeprefix("count_")
    operations = {
        "eq": lambda: value == expected,
        "neq": lambda: value != expected,
        "contains": lambda: expected in value,
        "starts_with": lambda: value.startswith(expected),
        "ends_with": lambda: value.endswith(expected),
        "in": lambda: value in expected,
        "gt": lambda: value > expected,
        "gte": lambda: value >= expected,
        "lt": lambda: value < expected,
        "lte": lambda: value <= expected,
    }
    return operations[operator]()


def execute_projection(state: Any, request: Any) -> dict[str, Any]:
    """Validate and execute a bounded query over normalized LIVE projections."""

    normalized, error = validate_request(request)
    if error:
        return error
    assert normalized is not None
    records = RECORD_BUILDERS[normalized["root"]](state)
    matches = [
        record
        for record in records
        if all(_matches(record, filter_item) for filter_item in normalized["filters"])
    ]
    affected_modules = set()
    for record in matches:
        if normalized["root"] == "dependencies":
            candidates = (record["source"], record["target"])
        else:
            candidates = (record["module_name"],)
        affected_modules.update(
            module_name
            for module_name in candidates
            if not module_current_truth(state, module_name)["available"]
        )
    if affected_modules:
        details = {
            module_name: module_current_truth(state, module_name)
            for module_name in sorted(affected_modules)
        }
        return {
            "status": "stale",
            "available": False,
            "root": normalized["root"],
            "provenance": "last_known_good",
            "affected_modules": details,
        }
    limit = normalized["limit"]
    selected = normalized["select"]
    schema_version = normalized["schema_version"]
    language_version = normalized["language_version"]
    evidence_limit = normalized.get("evidence_limit")
    root = normalized["root"]

    results = []
    has_nested_truncation = False

    for record in matches[:limit]:
        row = {field: record[field] for field in selected}
        if language_version == LANGUAGE_VERSION_V1_1:
            if root == "modules" and "imports" in selected:
                raw_imports = record["imports"]
                import_count = record["import_count"]
                if evidence_limit is not None:
                    row["imports"] = raw_imports[:evidence_limit]
                    truncated = len(row["imports"]) < import_count
                else:
                    row["imports"] = raw_imports
                    truncated = False
                row["imports_truncated"] = truncated
                if truncated:
                    has_nested_truncation = True
            elif root == "artifacts" and "consumers" in selected:
                raw_consumers = record["consumers"]
                available = record["consumer_data_available"]
                consumer_count = record["consumer_count"]
                if not available or raw_consumers is None or consumer_count is None:
                    row["consumers"] = None
                    row["consumers_truncated"] = None
                else:
                    if evidence_limit is not None:
                        row["consumers"] = raw_consumers[:evidence_limit]
                        truncated = len(row["consumers"]) < consumer_count
                    else:
                        row["consumers"] = raw_consumers
                        truncated = False
                    row["consumers_truncated"] = truncated
                    if truncated:
                        has_nested_truncation = True
        results.append(row)

    response: dict[str, Any] = {
        "status": "ok",
        "schema_version": schema_version,
        "language_version": language_version,
        "root": root,
        "total_matches": len(matches),
        "returned": len(results),
        "limit": limit,
        "truncated": len(results) < len(matches),
    }

    if language_version == LANGUAGE_VERSION_V1_1 and has_nested_truncation:
        retry_request = dict(request)
        retry_request["evidence_limit"] = None
        response["expand"] = {
            "available": True,
            "reason": "Nested evidence truncated by evidence_limit.",
            "retry_with_full_evidence": retry_request,
        }

    response["results"] = results
    return response

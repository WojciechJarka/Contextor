"""Deterministic normalization of bounded reference evidence."""

from __future__ import annotations

import copy

import pytest

from contextor.core.api.api_consumers import extract_api_consumers
from contextor.core.reference.shared import (
    MAX_USAGE_DETAILS,
    _empty_reference,
    _normalize_references,
)


def _normalize_details(details: list[dict]) -> list[dict]:
    references = {
        "pkg.api::service": {
            "called_by_detail": details,
        }
    }
    _normalize_references(references)
    return references["pkg.api::service"]["called_by_detail"]


def test_reversed_input_order_normalizes_identically() -> None:
    consumer = {"module": "consumer", "line": 4, "context": None}
    other = {"module": "other", "line": 3, "context": None}

    forward = _normalize_details(copy.deepcopy([consumer, other]))
    reverse = _normalize_details(copy.deepcopy([other, consumer]))

    assert forward == reverse
    assert forward == [consumer, other]


def test_cap_membership_is_stable_and_source_records_are_unchanged() -> None:
    records = [
        {"module": f"consumer_{index:02d}", "line": index, "context": None}
        for index in range(MAX_USAGE_DETAILS + 5)
    ]
    ascending_input = copy.deepcopy(records)
    descending_input = copy.deepcopy(list(reversed(records)))
    ascending_before = copy.deepcopy(ascending_input)
    descending_before = copy.deepcopy(descending_input)

    ascending_output = _normalize_details(ascending_input)
    descending_output = _normalize_details(descending_input)

    expected = records[:MAX_USAGE_DETAILS]
    assert ascending_output == expected
    assert descending_output == expected
    assert len(ascending_output) == MAX_USAGE_DETAILS
    assert len(descending_output) == MAX_USAGE_DETAILS
    assert ascending_input == ascending_before
    assert descending_input == descending_before


def test_identical_detail_duplicates_are_preserved_up_to_cap() -> None:
    duplicate = {"module": "consumer", "line": 7, "context": "call"}
    output = _normalize_details(copy.deepcopy([duplicate] * (MAX_USAGE_DETAILS + 3)))

    assert len(output) == MAX_USAGE_DETAILS
    assert output == [duplicate] * MAX_USAGE_DETAILS


def test_all_detail_families_are_individually_deterministic() -> None:
    details = {
        "called_by_detail": [
            {"module": "z_consumer", "line": 4, "context": None},
            {"module": "a_consumer", "line": 8, "context": "call"},
        ],
        "callback_called_detail": [
            {"module": "same_callback", "line": 3, "context": "argument"},
            {"module": "same_callback", "line": None, "context": None, "child": None},
        ],
        "event_bound_by_detail": [
            {"module": "z_event", "line": None, "context": "bind", "reason": None},
            {"module": "a_event", "line": 2, "context": None},
        ],
        "qualified_refs_detail": [
            {"module": "z_qualified", "line": 6, "context": None},
            {"module": "a_qualified", "line": 1, "context": "attribute"},
        ],
        "inherited_by_detail": [
            {"module": "z_subclass", "line": 5, "context": None, "child": "Base"},
            {"module": "a_subclass", "line": None, "context": None, "child": None},
        ],
        "called_by_ambiguous_detail": [
            {"module": "z_ambiguous", "line": None, "context": None, "reason": "dynamic"},
            {"module": "a_ambiguous", "line": 7, "context": "call", "reason": None},
        ],
    }
    expected = {
        "called_by_detail": [details["called_by_detail"][1], details["called_by_detail"][0]],
        "callback_called_detail": [details["callback_called_detail"][1], details["callback_called_detail"][0]],
        "event_bound_by_detail": [details["event_bound_by_detail"][1], details["event_bound_by_detail"][0]],
        "qualified_refs_detail": [details["qualified_refs_detail"][1], details["qualified_refs_detail"][0]],
        "inherited_by_detail": [details["inherited_by_detail"][1], details["inherited_by_detail"][0]],
        "called_by_ambiguous_detail": [details["called_by_ambiguous_detail"][1], details["called_by_ambiguous_detail"][0]],
    }

    forward_references = _empty_reference()
    reverse_references = _empty_reference()
    for key, records in details.items():
        forward_references[key] = copy.deepcopy(records)
        reverse_references[key] = copy.deepcopy(list(reversed(records)))
    forward = {"target": forward_references}
    reverse = {"target": reverse_references}

    _normalize_references(forward)
    _normalize_references(reverse)

    assert forward == reverse
    assert forward["target"].keys() == _empty_reference().keys()
    for key, expected_records in expected.items():
        assert forward["target"][key] == expected_records
        assert reverse["target"][key] == expected_records


def test_scalar_consumer_lists_keep_sorted_deduplicated_behavior() -> None:
    reference = _empty_reference()
    reference["called_by"] = ["z_consumer", "a_consumer", "z_consumer"]
    reference["inherited_by"] = ["subclass_b", "subclass_a", "subclass_b"]
    references = {"target": reference}

    _normalize_references(references)

    assert reference["called_by"] == ["a_consumer", "z_consumer"]
    assert reference["inherited_by"] == ["subclass_a", "subclass_b"]


def test_api_consumer_details_are_order_independent_without_count_changes() -> None:
    consumer = {"module": "consumer", "line": 4, "context": None}
    other = {"module": "other", "line": 3, "context": None}

    def extract(records: list[dict]) -> dict:
        reference = _empty_reference()
        reference["called_by"] = ["other", "consumer"]
        reference["called_by_detail"] = copy.deepcopy(records)
        normalized = {"pkg.api::service": reference}
        _normalize_references(normalized)
        return extract_api_consumers(["pkg.api::service"], normalized)["pkg.api::service"]

    forward = extract([consumer, other])
    reverse = extract([other, consumer])

    assert forward == reverse
    assert forward["usage"]["direct_calls_detail"] == [consumer, other]
    assert forward["consumers"] == ["consumer", "other"]
    assert forward["consumer_count"] == {
        "total": 2,
        "direct_calls": 2,
        "callbacks": 0,
        "events": 0,
        "qualified_refs": 0,
        "api_imports": 0,
        "inheritance": 0,
    }


def test_complete_payload_tie_breaker_preserves_extra_json_fields() -> None:
    first = {
        "module": "same_consumer",
        "line": 4,
        "context": None,
        "extra": {"value": 1},
    }
    second = {
        "module": "same_consumer",
        "line": 4,
        "context": None,
        "extra": {"value": 2},
    }

    forward = _normalize_details(copy.deepcopy([second, first]))
    reverse = _normalize_details(copy.deepcopy([first, second]))

    assert forward == reverse
    assert forward == [first, second]
    assert forward[0]["extra"] == {"value": 1}
    assert forward[1]["extra"] == {"value": 2}


def test_non_dictionary_detail_payload_fails_explicitly() -> None:
    references = {
        "target": {
            "called_by_detail": [
                {"module": "valid", "line": 1, "context": None},
                "unsupported",
            ]
        }
    }

    with pytest.raises(TypeError, match="Reference detail must be a dictionary"):
        _normalize_references(references)

from contextor.core.analysis.profile_analysis import (
    FULL_ANALYSIS_STAGES,
    PROFILE_SCHEMA,
    build_analysis_profile,
)


def _profile_events(operation_id: str = "profile-test"):
    stage_ms = {
        "identity_and_setup": 20.0,
        "indexing": 100.0,
        "reference_and_collision": 30.0,
        "graph": 25.0,
        "validation": 10.0,
        "metrics": 15.0,
        "reports": 200.0,
        "canonical_materialization": 80.0,
        "persistence": 40.0,
        "live_publish": 35.0,
        "finalize": 5.0,
    }

    events = [
        {
            "d": "ANALYSIS",
            "ev": "FULL_ANALYSIS_LEASE_ACQUIRED",
            "op": operation_id,
            "wait_ms": 3.0,
            "timing_semantics": "critical_path_lease_wait",
        },
        {
            "d": "ANALYSIS",
            "ev": "FULL_ANALYSIS_BODY_END",
            "op": operation_id,
            "analysis_ms": 600.0,
            "total_before_release_ms": 603.0,
            "elapsed_ms": 600.0,
            "timing_semantics": "critical_path_analysis_body",
        },
        {
            "d": "ANALYSIS",
            "ev": "FULL_ANALYSIS_END",
            "op": operation_id,
            "total_ms": 605.0,
            "elapsed_ms": 605.0,
            "timing_semantics": "critical_path_total",
        },
        {
            "d": "ANALYSIS",
            "ev": "FULL_ANALYSIS_INDEX_EVIDENCE",
            "op": operation_id,
            "timing_semantics": (
                "aggregate_file_task_not_critical_path"
            ),
            "file_tasks": 2,
            "source_parse_calls": 2,
            "source_parse_failures": 0,
            "cache_get_calls": 2,
            "cache_hits": 2,
            "cache_misses": 0,
            "lineage_cache_hits": 2,
            "lineage_extract_calls": 0,
            "source_parse_sum_ms": 9000.0,
            "cache_get_sum_ms": 4000.0,
            "lineage_extract_sum_ms": 0.0,
        },
        {
            "d": "ANALYSIS",
            "ev": "FULL_ANALYSIS_LINEAGE_EXTRACTION",
            "op": operation_id,
            "elapsed_ms": 0.0,
            "timing_semantics": (
                "aggregate_file_task_not_critical_path"
            ),
            "lineage_extract_calls": 0,
            "lineage_cache_hits": 2,
        },
        {
            "d": "ANALYSIS",
            "ev": "FULL_ANALYSIS_LINEAGE_MATERIALIZATION",
            "op": operation_id,
            "elapsed_ms": 70.0,
            "timing_semantics": (
                "critical_path_subphase_with_nested_components"
            ),
            "reuse_sources": 2,
            "reresolve_sources": 0,
            "materialize_sources": 0,
            "reresolve_fallback_sources": 0,
            "reuse_gate_ms": 60.0,
            "reresolve_calls_ms": 0.0,
            "materialize_calls_ms": 0.0,
            "lineage_sources": 2,
            "lineage_anchors": 10,
            "lineage_flows": 20,
            "lineage_surfaces": 2,
            "lineage_descriptors": 2,
        },
    ]

    events.extend(
        {
            "d": "ANALYSIS",
            "ev": "FULL_ANALYSIS_STAGE_END",
            "op": operation_id,
            "stage": stage,
            "elapsed_ms": elapsed_ms,
            "timing_semantics": "critical_path_stage",
        }
        for stage, elapsed_ms in stage_ms.items()
    )
    return events


def test_profile_ranks_only_critical_path_and_attributes_known_causes():
    events = _profile_events()
    events.append(
        {
            "d": "ANALYSIS",
            "ev": "FULL_ANALYSIS_STAGE_END",
            "op": "other-operation",
            "stage": "indexing",
            "elapsed_ms": 99999.0,
            "timing_semantics": "critical_path_stage",
        }
    )

    profile = build_analysis_profile(
        events,
        operation_id="profile-test",
    )

    assert profile["schema"] == PROFILE_SCHEMA
    assert profile["status"] == "ok"
    assert profile["measurement"]["absolute_wall_authoritative"] is False
    assert (
        profile["measurement"]["purpose"]
        == "diagnostic_profile_not_benchmark"
    )

    assert [item["stage"] for item in profile["bottlenecks"][:3]] == [
        "reports",
        "indexing",
        "canonical_materialization",
    ]
    assert [
        item["critical_path_ms"]
        for item in profile["bottlenecks"][:3]
    ] == [200.0, 100.0, 80.0]

    indexing = next(
        item
        for item in profile["bottlenecks"]
        if item["stage"] == "indexing"
    )
    assert indexing["reason_code"] == "warm_cache_still_parses_source"
    assert indexing["evidence"]["source_parse_calls"] == 2
    assert indexing["evidence"]["cache_hits"] == 2
    assert indexing["evidence"]["lineage_extract_calls"] == 0

    canonical = next(
        item
        for item in profile["bottlenecks"]
        if item["stage"] == "canonical_materialization"
    )
    assert canonical["reason_code"] == "lineage_reuse_gate_cost"
    assert canonical["evidence"]["lineage_elapsed_ms"] == 70.0
    assert canonical["evidence"]["reuse_gate_ms"] == 60.0

    aggregate = profile["aggregate_worker_diagnostics"]
    assert aggregate["timing_semantics"] == (
        "aggregate_file_task_not_critical_path"
    )
    assert aggregate["source_parse_sum_ms"] == 9000.0
    assert aggregate["cache_get_sum_ms"] == 4000.0

    assert max(
        item["critical_path_ms"]
        for item in profile["bottlenecks"]
    ) == 200.0
    assert len(profile["stage_breakdown"]) == len(
        FULL_ANALYSIS_STAGES
    )


def test_profile_fails_closed_when_required_evidence_is_missing():
    events = [
        event
        for event in _profile_events()
        if event["ev"] != "FULL_ANALYSIS_INDEX_EVIDENCE"
    ]

    profile = build_analysis_profile(
        events,
        operation_id="profile-test",
    )

    assert profile == {
        "schema": PROFILE_SCHEMA,
        "status": "incomplete",
        "operation_id": "profile-test",
        "missing": ["FULL_ANALYSIS_INDEX_EVIDENCE"],
        "duplicates": [],
    }


def test_profile_rejects_invalid_overlapping_coordinator_contract():
    events = _profile_events()
    body = next(
        event
        for event in events
        if event["ev"] == "FULL_ANALYSIS_BODY_END"
    )
    body["total_before_release_ms"] = 10.0

    profile = build_analysis_profile(
        events,
        operation_id="profile-test",
    )

    assert profile["schema"] == PROFILE_SCHEMA
    assert profile["status"] == "invalid_evidence"
    assert (
        profile["error"]
        == "total_before_release_ms cannot be shorter than analysis_ms"
    )

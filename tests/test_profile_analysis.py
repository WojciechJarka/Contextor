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
    component_ms = {
        "identity_and_setup": {
            "progress_setup": 1.0,
            "repository_identity": 8.0,
            "authoritative_state_resolution": 5.0,
            "cache_reset": 1.0,
            "analysis_filters_and_index_progress": 4.0,
        },
        "reports": {
            "basic_report_preparation": 20.0,
            "artifact_pipeline": 80.0,
            "sanity_check": 5.0,
            "layer_reports": 30.0,
            "git_state": 10.0,
            "high_risk_writes": 10.0,
            "global_report_write": 20.0,
            "incremental_file_state": 20.0,
            "finalization": 4.0,
        },
        "canonical_materialization": {
            "setup_and_imports": 0.5,
            "topology_analytics": 0.5,
            "collision_canonicalization": 0.5,
            "artifact_consumption": 0.5,
            "module_usage_reuse": 0.5,
            "canonical_validation": 0.5,
            "lineage_materialization": 70.0,
            "lineage_query_indexes": 0.5,
            "state_construction": 0.5,
            "dependency_matrix": 0.5,
            "shared_usage_clusters": 0.5,
            "publish_preparation": 0.5,
        },
        "live_publish": {
            "connect": 5.0,
            "publish": 25.0,
            "status_handling": 2.0,
        },
    }
    for stage, components in component_ms.items():
        events.extend(
            {
                "d": "ANALYSIS",
                "ev": "FULL_ANALYSIS_STAGE_COMPONENT_END",
                "op": operation_id,
                "stage": stage,
                "component": component,
                "elapsed_ms": elapsed_ms,
                "timing_semantics": "critical_path_stage_component",
                **({"status": "success"} if stage == "live_publish" else {}),
            }
            for component, elapsed_ms in components.items()
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
    assert canonical["evidence"]["dominant_component"] == "lineage_materialization"
    assert canonical["evidence"]["lineage_reason_code"] == "lineage_reuse_gate_cost"
    assert canonical["evidence"]["lineage_elapsed_ms"] == 70.0
    assert canonical["evidence"]["reuse_gate_ms"] == 60.0

    assert profile["stage_attribution"]["identity_and_setup"]["reason_code"] == (
        "repository_identity_cost"
    )
    assert profile["stage_attribution"]["reports"]["reason_code"] == (
        "artifact_pipeline_cost"
    )
    assert profile["stage_attribution"]["canonical_materialization"]["reason_code"] == (
        "lineage_reuse_gate_cost"
    )
    live_attribution = profile["stage_attribution"]["live_publish"]
    assert live_attribution["reason_code"] == "live_publish_ipc_cost"
    assert live_attribution["publish_ms"] == 25.0
    assert live_attribution["stage_status"] == "success"

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


def test_profile_fails_closed_when_stage_component_evidence_is_missing():
    events = [
        event
        for event in _profile_events()
        if not (
            event["ev"] == "FULL_ANALYSIS_STAGE_COMPONENT_END"
            and event["stage"] == "reports"
            and event["component"] == "artifact_pipeline"
        )
    ]

    profile = build_analysis_profile(events, operation_id="profile-test")

    assert profile["status"] == "incomplete"
    assert profile["missing"] == [
        "FULL_ANALYSIS_STAGE_COMPONENT_END:reports:artifact_pipeline"
    ]


def test_profile_rejects_invalid_stage_component_timing_semantics():
    events = _profile_events()
    component = next(
        event
        for event in events
        if event["ev"] == "FULL_ANALYSIS_STAGE_COMPONENT_END"
        and event["stage"] == "reports"
        and event["component"] == "artifact_pipeline"
    )
    component["timing_semantics"] = "aggregate"

    profile = build_analysis_profile(events, operation_id="profile-test")

    assert profile["status"] == "invalid_evidence"
    assert profile["error"] == (
        "FULL_ANALYSIS_STAGE_COMPONENT_END:reports:artifact_pipeline "
        "has invalid timing_semantics"
    )

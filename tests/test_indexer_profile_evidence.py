from contextor.core.runtime_trace import capture_trace_events
from contextor.core.symbol_engine.indexer import index_repository


def _write_two_file_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("value_a = 1\n", encoding="utf-8")
    (repo / "b.py").write_text("value_b = 2\n", encoding="utf-8")
    return repo


def test_warm_index_cache_evidence_proves_ast_parse_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    repo = _write_two_file_repo(tmp_path)

    index_repository(str(repo))
    with capture_trace_events() as events:
        index_repository(str(repo))

    evidence = [
        event for event in events
        if event["ev"] == "FULL_ANALYSIS_INDEX_EVIDENCE"
    ]
    assert len(evidence) == 1
    event = evidence[0]
    assert event["execution_mode"] == "inline"
    assert event["timing_semantics"] == "aggregate_file_task_not_critical_path"
    assert event["file_tasks"] == 2
    assert event["source_parse_calls"] == 0
    assert event["source_parse_failures"] == 0
    assert event["cache_get_calls"] == 2
    assert event["cache_hits"] == 2
    assert event["cache_misses"] == 0
    assert event["lineage_cache_hits"] == 2
    assert event["lineage_extract_calls"] == 0
    assert event["source_parse_sum_ms"] == 0.0
    assert event["cache_get_sum_ms"] >= 0.0
    assert event["lineage_extract_sum_ms"] == 0.0
    assert "elapsed_ms" not in event

    worker_events = [
        event
        for event in events
        if event["ev"]
        == "FULL_ANALYSIS_INDEX_WORKER_TIMING"
    ]

    assert len(worker_events) == 1

    worker_event = worker_events[0]

    assert (
        worker_event["timing_semantics"]
        == "aggregate_file_task_not_critical_path"
    )

    assert worker_event["execution_mode"] == "inline"
    assert worker_event["file_tasks"] == 2
    assert worker_event["worker_task_sum_ms"] >= 0.0
    assert worker_event["worker_task_max_ms"] >= 0.0

    assert worker_event["source_read_calls"] == 2
    assert worker_event["source_read_sum_ms"] >= 0.0

    assert worker_event["import_extract_calls"] == 0
    assert worker_event["symbol_extract_calls"] == 0
    assert worker_event["reference_extract_calls"] == 0
    assert worker_event["collision_extract_calls"] == 0
    assert worker_event["test_extract_calls"] == 0

    assert worker_event["cache_set_calls"] == 0
    assert worker_event["cache_set_sum_ms"] == 0.0

    assert worker_event["cache_miss_task_count"] == 0
    assert worker_event["cache_miss_top10"] == ""


def test_index_lineage_extraction_event_is_explicitly_noncritical(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    repo = _write_two_file_repo(tmp_path)

    with capture_trace_events() as events:
        index_repository(str(repo))

    lineage_events = [
        event for event in events
        if event["ev"] == "FULL_ANALYSIS_LINEAGE_EXTRACTION"
    ]
    assert len(lineage_events) == 1
    event = lineage_events[0]
    assert event["timing_semantics"] == "aggregate_file_task_not_critical_path"
    assert event["lineage_extract_calls"] == 2
    assert event["lineage_cache_hits"] == 0

    worker_events = [
        event
        for event in events
        if event["ev"]
        == "FULL_ANALYSIS_INDEX_WORKER_TIMING"
    ]

    assert len(worker_events) == 1

    worker_event = worker_events[0]

    assert worker_event["execution_mode"] == "inline"

    assert (
        worker_event["timing_semantics"]
        == "aggregate_file_task_not_critical_path"
    )

    assert worker_event["file_tasks"] == 2

    assert worker_event["source_read_calls"] == 2
    assert worker_event["source_read_sum_ms"] >= 0.0

    assert worker_event["import_extract_calls"] == 2
    assert worker_event["import_extract_sum_ms"] >= 0.0

    assert worker_event["symbol_extract_calls"] == 2
    assert worker_event["symbol_extract_sum_ms"] >= 0.0

    assert worker_event["reference_extract_calls"] == 2
    assert worker_event["reference_extract_sum_ms"] >= 0.0

    assert worker_event["collision_extract_calls"] == 2
    assert worker_event["collision_extract_sum_ms"] >= 0.0

    assert worker_event["cache_set_calls"] == 2
    assert worker_event["cache_set_sum_ms"] >= 0.0

    assert worker_event["cache_miss_task_count"] == 2

    assert "a.py|task=" in worker_event[
        "cache_miss_top10"
    ]

    assert "b.py|task=" in worker_event[
        "cache_miss_top10"
    ]

    miss_events = [
        event
        for event in events
        if event["ev"]
        == "FULL_ANALYSIS_INDEX_CACHE_MISS_TIMING"
    ]

    assert len(miss_events) == 2

    assert {
        event["path"]
        for event in miss_events
    } == {
        "a.py",
        "b.py",
    }

    for miss_event in miss_events:
        assert (
            miss_event["timing_semantics"]
            == (
                "single_file_task_wall_and_nested_subphases"
            )
        )

        assert miss_event["task_total_ms"] >= 0.0
        assert miss_event["source_read_ms"] >= 0.0
        assert miss_event["cache_get_ms"] >= 0.0
        assert miss_event["source_parse_ms"] >= 0.0
        assert miss_event["lineage_extract_ms"] >= 0.0
        assert miss_event["import_extract_ms"] >= 0.0
        assert miss_event["symbol_extract_ms"] >= 0.0
        assert miss_event["reference_extract_ms"] >= 0.0
        assert miss_event["collision_extract_ms"] >= 0.0
        assert miss_event["test_extract_ms"] >= 0.0
        assert miss_event["cache_set_ms"] >= 0.0


def test_process_pool_parent_timing_evidence_is_explicit(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTEXTOR_STATE_DIR",
        str(
            tmp_path
            / "state"
        ),
    )

    monkeypatch.delenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL",
        raising=False,
    )

    repo = _write_two_file_repo(
        tmp_path
    )

    with capture_trace_events() as events:
        index_repository(
            str(
                repo
            )
        )

    parent_events = [
        event
        for event in events
        if event["ev"]
        == "FULL_ANALYSIS_INDEX_PARENT_TIMING"
    ]

    assert len(parent_events) == 1

    event = parent_events[0]

    assert event["execution_mode"] == "process_pool"

    assert (
        event["timing_semantics"]
        == "critical_path_parent_subphases_partial"
    )

    assert event["index_internal_ms"] >= 0.0
    assert event["file_discovery_ms"] >= 0.0
    assert event["pool_scope_ms"] >= 0.0
    assert event["pool_enter_ms"] >= 0.0
    assert event["pool_submit_ms"] >= 0.0
    assert event["parent_future_wait_ms"] >= 0.0
    assert event["parent_future_result_ms"] >= 0.0
    assert event["parent_merge_ms"] >= 0.0
    assert event["parent_progress_ms"] >= 0.0
    assert event["pool_shutdown_ms"] >= 0.0

    assert event["executor_max_workers"] >= 1

    assert (
        event["executor_process_count_after_submit"]
        >= 1
    )

    assert (
        event[
            "executor_process_count_before_shutdown"
        ]
        >= 1
    )

    worker_events = [
        item
        for item in events
        if item["ev"]
        == "FULL_ANALYSIS_INDEX_WORKER_TIMING"
    ]

    assert len(worker_events) == 1

    worker_event = worker_events[0]

    assert worker_event["execution_mode"] == "process_pool"

    assert worker_event["worker_process_count"] >= 1
    assert (
        worker_event["worker_first_start_count"]
        == worker_event["worker_process_count"]
    )

    assert (
        worker_event["worker_process_count"]
        <= event["executor_max_workers"]
    )

    assert worker_event["worker_tasks_per_process"]

    assert worker_event["worker_start_delay_sum_ms"] >= 0.0
    assert worker_event["worker_start_delay_max_ms"] >= 0.0

    assert (
        worker_event["worker_first_start_delay_min_ms"]
        >= 0.0
    )

    assert (
        worker_event["worker_first_start_delay_max_ms"]
        >= worker_event[
            "worker_first_start_delay_min_ms"
        ]
    )

    assert (
        worker_event["worker_first_start_delay_mean_ms"]
        >= worker_event[
            "worker_first_start_delay_min_ms"
        ]
    )

    assert (
        worker_event["worker_first_start_delay_mean_ms"]
        <= worker_event[
            "worker_first_start_delay_max_ms"
        ]
    )

    assert (
        worker_event["worker_result_transport_sum_ms"]
        >= 0.0
    )

    assert (
        worker_event["worker_result_transport_max_ms"]
        >= 0.0
    )

    assert (
        event["pool_scope_ms"]
        >= event["pool_enter_ms"]
    )

    assert (
        event["pool_scope_ms"]
        >= event["pool_shutdown_ms"]
    )

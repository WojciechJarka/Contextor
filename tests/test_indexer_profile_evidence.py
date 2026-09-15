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

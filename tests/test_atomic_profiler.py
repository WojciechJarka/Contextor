import json
from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.profiling.atomic import AtomicRecorder
from contextor.core.profiling.registry import build_catalog, get_scope
from contextor.core.profiling.runner import _stats, run_probe, validate_probe_request


def test_catalog_static_and_ordered():
    assert [item["name"] for item in build_catalog()["scopes"]] == [
        "reports.summary", "live.ping", "snapshot.metadata"]
    assert get_scope("arbitrary.function") is None


def test_disabled_span_executes_without_timing(monkeypatch):
    import contextor.core.profiling.atomic as atomic
    monkeypatch.setattr(atomic, "perf_counter_ns", lambda: pytest.fail("timer read"))
    recorder = AtomicRecorder("reports.summary", frozenset(), 0)
    called = []
    with recorder.span("read_bytes"):
        called.append(1)
    assert called == [1]
    assert recorder.records() == ()


def test_selected_span_records_success_and_failure():
    recorder = AtomicRecorder("reports.summary", frozenset({"read_bytes"}), 0)
    with recorder.span("read_bytes"):
        pass
    with pytest.raises(RuntimeError):
        with recorder.span("read_bytes"):
            raise RuntimeError("private value")
    assert [item["status"] for item in recorder.records()] == ["ok", "failed"]
    assert all(item["duration_ns"] >= 0 for item in recorder.records())


@pytest.mark.parametrize("samples,warmup", [(True, 0), (1, False), (0, 0), (11, 0), (1, 4)])
def test_invalid_counts(samples, warmup):
    with pytest.raises(ValueError):
        validate_probe_request("reports.summary", ["read_bytes"], samples, warmup, "summary")


def test_statistics_nearest_rank():
    assert _stats([1_000_000])["p95_ms"] is None
    assert _stats([n * 1_000_000 for n in range(1, 6)])["p95_ms"] == 5


def test_runner_excludes_warmup_and_spans_are_selected(tmp_path, monkeypatch):
    spec = get_scope("reports.summary")
    called = []
    def fake_run(root, recorder):
        called.append(1)
        with recorder.span("read_bytes"):
            pass
        with recorder.span("json_decode"):
            pass
        return {"status": "ok", "data_source": "historical_report"}
    import contextor.core.profiling.registry as registry
    monkeypatch.setattr(registry, "_SCOPES", (replace(spec, run_scope=fake_run), *registry.list_scopes()[1:]))
    summary = run_probe(tmp_path, "reports.summary", ["read_bytes"], 2, 1, "summary")
    assert len(called) == 3
    assert summary["wall"]["count"] == 2
    assert summary["presets"]["read_bytes"]["count"] == 2
    assert "spans" not in summary
    spans = run_probe(tmp_path, "reports.summary", ["read_bytes"], 1, 0, "spans")
    assert {item["preset"] for item in spans["spans"]} == {"read_bytes"}


def test_warmup_failure_stops_and_is_not_success(tmp_path, monkeypatch):
    import contextor.core.profiling.registry as registry
    spec = get_scope("reports.summary")
    calls = []
    def fail(root, recorder):
        calls.append(1)
        return {"status": "unavailable", "reason": "report_missing"}
    monkeypatch.setattr(registry, "_SCOPES", (replace(spec, run_scope=fail), *registry.list_scopes()[1:]))
    result = run_probe(tmp_path, "reports.summary", ["read_bytes"], 3, 1, "summary")
    assert result["status"] == "warmup_failed"
    assert result["wall"]["count"] == 0
    assert calls == [1]


def test_live_revision_change_and_output_bound(tmp_path, monkeypatch):
    import contextor.core.profiling.registry as registry
    import contextor.core.profiling.runner as runner
    specs = registry.list_scopes()
    revisions = iter((1, 2))
    def ping(root, recorder):
        with recorder.span("ping"):
            pass
        return {"status": "ok", "observed_revision": next(revisions),
                "data_source": "live_authority"}
    monkeypatch.setattr(registry, "_SCOPES", (specs[0], replace(specs[1], run_scope=ping), specs[2]))
    result = run_probe(tmp_path, "live.ping", ["ping"], 2, 0, "summary")
    assert result["consistency"]["status"] == "revision_changed"
    monkeypatch.setattr(runner, "MAX_OUTPUT_BYTES", 100)
    overflow = run_probe(tmp_path, "reports.summary", ["read_bytes"], 1, 0, "spans")
    assert overflow["status"] == "confirmation_required"

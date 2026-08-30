from types import SimpleNamespace

import pytest

import contextor.core.reporting_layer.artifact_usage_report as report
from contextor.core.errors import AnalysisCancelled


def _modules(*module_ids):
    return {
        module_id: SimpleNamespace(path=f"{module_id}.py", absolute_path=f"{module_id}.py")
        for module_id in module_ids
    }


def _available_facts(*module_ids):
    return {
        module_id: {"status": "available", "facts": {"functions": []}}
        for module_id in module_ids
    }


def _install_worker_spies(monkeypatch):
    calls = []
    monkeypatch.setattr(
        report,
        "build_repository_reference_index",
        lambda _modules, _root: object(),
    )
    monkeypatch.setattr(
        report,
        "_init_artifact_worker",
        lambda modules, root, reference, facts: calls.append(
            ("init", modules, root, reference, facts)
        ),
    )

    def process(module_id):
        calls.append(("process", module_id))
        return module_id, {
            "symbols": {},
            "own_symbols": [],
            "consumers": {},
        }

    monkeypatch.setattr(report, "_process_single_artifact_module", process)
    return calls


def _install_pool_spy(monkeypatch):
    class Future:
        def __init__(self, value):
            self.value = value

        def result(self):
            return self.value

    class Pool:
        constructed = 0

        def __init__(self, *, initializer, initargs):
            type(self).constructed += 1
            initializer(*initargs)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, function, module_id):
            return Future(function(module_id))

    monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor", Pool)
    monkeypatch.setattr(
        "concurrent.futures.as_completed",
        lambda futures: list(futures),
    )
    return Pool


def test_all_available_scheduled_tasks_use_serial_path(monkeypatch):
    modules = _modules("a", "b")
    facts = _available_facts("a", "b")
    calls = _install_worker_spies(monkeypatch)

    class ForbiddenPool:
        def __init__(self, **_kwargs):
            raise AssertionError("ProcessPool must not be constructed")

    monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor", ForbiddenPool)

    artifacts, failures = report.collect_module_artifacts(
        modules, "repo", symbol_facts_by_module=facts
    )

    assert set(artifacts) == {"a", "b"}
    assert failures == {}
    assert [item[0] for item in calls] == ["init", "process", "process"]


def test_scheduled_fallback_task_keeps_process_pool_path(monkeypatch):
    modules = _modules("a", "b")
    facts = _available_facts("a")
    calls = _install_worker_spies(monkeypatch)
    pool = _install_pool_spy(monkeypatch)

    artifacts, failures = report.collect_module_artifacts(
        modules, "repo", symbol_facts_by_module=facts
    )

    assert pool.constructed == 1
    assert set(artifacts) == {"a", "b"}
    assert failures == {}
    assert [item[0] for item in calls] == ["init", "process", "process"]


def test_preregistered_failure_does_not_force_pool(monkeypatch):
    modules = _modules("failed", "available")
    facts = _available_facts("available")
    facts["failed"] = {
        "status": "failure",
        "exception_type": "RuntimeError",
        "message": "visitor failed",
    }
    calls = _install_worker_spies(monkeypatch)

    class ForbiddenPool:
        def __init__(self, **_kwargs):
            raise AssertionError("pre-registered failure must not force pool")

    monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor", ForbiddenPool)

    artifacts, failures = report.collect_module_artifacts(
        modules, "repo", symbol_facts_by_module=facts
    )

    assert set(artifacts) == {"available"}
    assert failures == {"failed": "RuntimeError: visitor failed"}
    assert [item[0] for item in calls] == ["init", "process"]


def test_environment_override_forces_serial_fallback(monkeypatch):
    modules = _modules("fallback")
    calls = _install_worker_spies(monkeypatch)
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    pool = _install_pool_spy(monkeypatch)

    artifacts, failures = report.collect_module_artifacts(modules, "repo")

    assert pool.constructed == 0
    assert set(artifacts) == {"fallback"}
    assert failures == {}
    assert [item[0] for item in calls] == ["init", "process"]


def test_zero_scheduled_tasks_do_not_construct_pool(monkeypatch):
    modules = _modules("failed")
    facts = {
        "failed": {
            "status": "failure",
            "exception_type": "ValueError",
            "message": "bad symbols",
        }
    }
    pool = _install_pool_spy(monkeypatch)

    artifacts, failures = report.collect_module_artifacts(
        modules, "repo", symbol_facts_by_module=facts
    )

    assert pool.constructed == 0
    assert artifacts == {}
    assert failures == {"failed": "ValueError: bad symbols"}


def test_adaptive_serial_worker_failure_isolated_and_progress_continues(monkeypatch):
    modules = _modules("failed", "later")
    facts = _available_facts("failed", "later")
    _install_worker_spies(monkeypatch)
    progress = []

    def process(module_id):
        if module_id == "failed":
            raise RuntimeError("worker failed")
        return module_id, {"symbols": {}, "own_symbols": [], "consumers": {}}

    monkeypatch.setattr(report, "_process_single_artifact_module", process)

    artifacts, failures = report.collect_module_artifacts(
        modules,
        "repo",
        progress_callback=lambda completed, total, message: progress.append(
            (completed, total, message)
        )
        or True,
        symbol_facts_by_module=facts,
    )

    assert set(artifacts) == {"later"}
    assert failures == {"failed": "RuntimeError: worker failed"}
    assert progress == [(1, 2, "JSON: failed"), (2, 2, "JSON: later")]


def test_adaptive_serial_cancellation_propagates_without_failure(monkeypatch):
    modules = _modules("cancelled", "later")
    facts = _available_facts("cancelled", "later")
    _install_worker_spies(monkeypatch)

    def process(module_id):
        if module_id == "cancelled":
            raise AnalysisCancelled()
        return module_id, {"symbols": {}, "own_symbols": [], "consumers": {}}

    monkeypatch.setattr(report, "_process_single_artifact_module", process)

    with pytest.raises(AnalysisCancelled):
        report.collect_module_artifacts(
            modules, "repo", symbol_facts_by_module=facts
        )


def test_preregistered_failure_keeps_progress_total_and_checkpoint(monkeypatch):
    modules = _modules("failed", "available")
    facts = _available_facts("available")
    facts["failed"] = {
        "status": "failure",
        "exception_type": "RuntimeError",
        "message": "visitor failed",
    }
    _install_worker_spies(monkeypatch)
    progress = []

    artifacts, failures = report.collect_module_artifacts(
        modules,
        "repo",
        progress_callback=lambda completed, total, message: progress.append(
            (completed, total, message)
        )
        or True,
        symbol_facts_by_module=facts,
    )

    assert set(artifacts) == {"available"}
    assert failures == {"failed": "RuntimeError: visitor failed"}
    assert progress == [(1, 2, "JSON: available")]


def test_zero_tasks_do_not_invoke_progress_or_cancellation(monkeypatch):
    modules = _modules("failed")
    facts = {
        "failed": {
            "status": "failure",
            "exception_type": "ValueError",
            "message": "bad symbols",
        }
    }
    _install_pool_spy(monkeypatch)
    progress = []

    artifacts, failures = report.collect_module_artifacts(
        modules,
        "repo",
        progress_callback=lambda *_args: progress.append(True) or False,
        symbol_facts_by_module=facts,
    )

    assert artifacts == {}
    assert failures == {"failed": "ValueError: bad symbols"}
    assert progress == []

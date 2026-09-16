import asyncio
import json
import os
from pathlib import Path

import pytest

from contextor import mcp_server
from contextor.mcp import analysis_jobs, documentation
from contextor.mcp.tools.get_analysis_status import get_analysis_status


def _create_job(
    root: Path,
    job_id_suffix: int,
    *,
    status: str = "completed",
    operation: str = "project",
    target: str | None = None,
    owner_pid: int | None = None,
    created_at: str = "2026-08-26T12:00:00Z",
    started_at: str | None = "2026-08-26T12:00:01Z",
    completed_at: str | None = "2026-08-26T12:00:10Z",
    message: str | None = "Done",
    error: str | None = None,
    live_publish_status: str = "success",
    live_publish_revision: int = 1,
    live_publish_warning: str | None = None,
    mtime_ns: int | None = None,
) -> dict:
    job_id = f"{job_id_suffix:032x}"
    effective_owner_pid = os.getpid() if owner_pid is None else owner_pid
    payload = {
        "job_id": job_id,
        "operation": operation,
        "repo_path": str(root),
        "target": target,
        "status": status,
        "created_at": created_at,
        "started_at": started_at,
        "completed_at": completed_at,
        "updated_at": completed_at or created_at,
        "message": message,
        "error": error,
        "live_publish_status": live_publish_status,
        "live_publish_revision": live_publish_revision,
        "live_publish_warning": live_publish_warning,
        "owner_pid": effective_owner_pid,
    }
    analysis_jobs._write_analysis_job(root, payload)

    job_file = analysis_jobs._job_path(root, job_id)
    if mtime_ns is not None:
        os.utime(job_file, ns=(mtime_ns, mtime_ns))

    return payload


def test_analysis_status_concurrency__multiple_active_without_job_id_returns_ambiguity(tmp_path):
    root = tmp_path
    foreign_owner = os.getpid() + 100000
    _create_job(root, 1, status="queued", owner_pid=foreign_owner, mtime_ns=1_000_000_000)
    _create_job(root, 2, status="running", owner_pid=foreign_owner, mtime_ns=2_000_000_000)

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "ambiguous_job"
    assert res["job_id"] is None
    assert res["repo_path"] == str(root)
    assert res["active_job_count"] == 2
    assert len(res["active_jobs"]) == 2
    assert res["truncated"] is False
    assert "Multiple queued/running analysis jobs exist." in res["message"]
    assert "analysis_coverage" not in res


def test_analysis_status_concurrency__explicit_job_id_bypasses_ambiguity(tmp_path, monkeypatch):
    root = tmp_path
    j1 = _create_job(root, 1, status="queued", mtime_ns=1_000_000_000)
    _create_job(root, 2, status="running", mtime_ns=2_000_000_000)

    def fail_if_active_called(*_args, **_kwargs):
        raise AssertionError("_active_analysis_jobs MUST NOT be called when explicit job_id is passed!")

    monkeypatch.setattr(analysis_jobs, "_active_analysis_jobs", fail_if_active_called)
    monkeypatch.setattr(
        analysis_jobs,
        "_is_current_process_analysis_task_active",
        lambda _job_id: True,
    )

    raw = get_analysis_status(str(root), job_id=j1["job_id"])
    res = json.loads(raw)

    assert res["status"] == "queued"
    assert res["job_id"] == j1["job_id"]


def test_analysis_status_concurrency__single_active_does_not_override_newer_completed_latest(tmp_path):
    root = tmp_path
    _create_job(
        root,
        1,
        status="running",
        owner_pid=os.getpid() + 100000,
        mtime_ns=1_000_000_000,
    )
    j2 = _create_job(root, 2, status="completed", mtime_ns=2_000_000_000)

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "completed"
    assert res["job_id"] == j2["job_id"]


def test_analysis_status_concurrency__zero_active_preserves_latest_terminal(tmp_path):
    root = tmp_path
    _create_job(root, 1, status="failed", mtime_ns=1_000_000_000)
    j2 = _create_job(root, 2, status="completed", mtime_ns=2_000_000_000)

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "completed"
    assert res["job_id"] == j2["job_id"]


def test_analysis_status_concurrency__completed_jobs_do_not_count_as_active(tmp_path):
    root = tmp_path
    _create_job(
        root,
        1,
        status="queued",
        owner_pid=os.getpid() + 100000,
        mtime_ns=1_000_000_000,
    )
    _create_job(root, 2, status="failed", mtime_ns=2_000_000_000)
    j3 = _create_job(root, 3, status="completed", mtime_ns=3_000_000_000)

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    # active_count is 1 (job 1), so no ambiguity; latest mtime is job 3 (completed)
    assert res["status"] == "completed"
    assert res["job_id"] == j3["job_id"]


def test_analysis_status_concurrency__active_candidates_are_deterministic_newest_first(tmp_path):
    root = tmp_path
    foreign_owner = os.getpid() + 100000
    j1 = _create_job(
        root,
        1,
        status="queued",
        owner_pid=foreign_owner,
        mtime_ns=1_000_000_000,
    )
    j2 = _create_job(
        root,
        2,
        status="running",
        owner_pid=foreign_owner,
        mtime_ns=3_000_000_000,
    )
    j3 = _create_job(
        root,
        3,
        status="running",
        owner_pid=foreign_owner,
        mtime_ns=2_000_000_000,
    )

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "ambiguous_job"
    returned_ids = [item["job_id"] for item in res["active_jobs"]]
    assert returned_ids == [j2["job_id"], j3["job_id"], j1["job_id"]]


def test_analysis_status_concurrency__equal_mtime_uses_job_id_tiebreak(tmp_path):
    root = tmp_path
    foreign_owner = os.getpid() + 100000
    j1 = _create_job(
        root,
        1,
        status="queued",
        owner_pid=foreign_owner,
        mtime_ns=1_000_000_000,
    )
    j2 = _create_job(
        root,
        2,
        status="running",
        owner_pid=foreign_owner,
        mtime_ns=1_000_000_000,
    )

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "ambiguous_job"
    returned_ids = [item["job_id"] for item in res["active_jobs"]]
    assert returned_ids == [j1["job_id"], j2["job_id"]]


def test_analysis_status_concurrency__candidate_list_is_bounded_to_five(tmp_path):
    root = tmp_path
    foreign_owner = os.getpid() + 100000
    for i in range(1, 8):
        _create_job(
            root,
            i,
            status="running",
            owner_pid=foreign_owner,
            mtime_ns=i * 1_000_000_000,
        )

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "ambiguous_job"
    assert res["active_job_count"] == 7
    assert len(res["active_jobs"]) == 5
    assert res["truncated"] is True
    # Newest first: jobs 7, 6, 5, 4, 3
    assert res["active_jobs"][0]["job_id"] == f"{7:032x}"
    assert res["active_jobs"][4]["job_id"] == f"{3:032x}"


def test_analysis_status_concurrency__ambiguity_response_does_not_mutate_jobs(tmp_path):
    root = tmp_path
    j1 = _create_job(root, 1, status="queued", owner_pid=999999, mtime_ns=1_000_000_000)
    j2 = _create_job(root, 2, status="running", owner_pid=999999, mtime_ns=2_000_000_000)

    before_1 = analysis_jobs._read_analysis_job(root, j1["job_id"])
    before_2 = analysis_jobs._read_analysis_job(root, j2["job_id"])

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)
    assert res["status"] == "ambiguous_job"

    after_1 = analysis_jobs._read_analysis_job(root, j1["job_id"])
    after_2 = analysis_jobs._read_analysis_job(root, j2["job_id"])

    assert before_1 == after_1
    assert before_2 == after_2


def test_analysis_status_concurrency__explicit_stale_owner_interruption_is_preserved(tmp_path):
    root = tmp_path
    stale_pid = os.getpid() + 100000
    j1 = _create_job(root, 1, status="running", owner_pid=stale_pid, mtime_ns=1_000_000_000)

    raw = get_analysis_status(str(root), job_id=j1["job_id"])
    res = json.loads(raw)

    assert res["status"] == "interrupted"
    assert res["error"] == "owner_process_changed"

    persisted = analysis_jobs._read_analysis_job(root, j1["job_id"])
    assert persisted["status"] == "interrupted"
    assert persisted["error"] == "owner_process_changed"


def test_analysis_status_concurrency__no_jobs_still_returns_not_found(tmp_path):
    root = tmp_path
    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "not_found"
    assert res["job_id"] is None
    assert res["repo_path"] == str(root)


def test_analysis_status_concurrency__runtime_description_is_index_backed():
    tool = mcp_server.mcp._tool_manager._tools["get_analysis_status"]
    index = documentation.load_documentation_index()
    entry = next(
        item for item in index["tools"]
        if item["tool"] == "get_analysis_status"
    )

    assert tool.description == entry["short_description"]
    assert tool.fn.__doc__ is None

    description = tool.description.lower()
    assert "explicit job_id" in description
    assert "multiple" in description
    assert "queued/running" in description
    assert "ambiguous_job" in description


def test_analysis_job_write__retries_permission_error_only_on_replace(
    tmp_path, monkeypatch
):
    real_replace = analysis_jobs.os.replace
    replace_calls = []
    sleep_calls = []

    def flaky_replace(source, target):
        replace_calls.append((source, target))
        if len(replace_calls) < 3:
            raise PermissionError("replace temporarily blocked")
        real_replace(source, target)

    monkeypatch.setattr(analysis_jobs.os, "replace", flaky_replace)
    monkeypatch.setattr(analysis_jobs.time, "sleep", sleep_calls.append)

    job_id = f"{101:032x}"
    analysis_jobs._write_analysis_job(
        tmp_path,
        {"job_id": job_id, "status": "queued"},
    )

    assert len(replace_calls) == 3
    assert sleep_calls == [
        analysis_jobs._ANALYSIS_JOB_REPLACE_RETRY_SECONDS,
        analysis_jobs._ANALYSIS_JOB_REPLACE_RETRY_SECONDS,
    ]
    persisted = analysis_jobs._read_analysis_job(tmp_path, job_id)
    assert persisted is not None
    assert persisted["status"] == "queued"


def test_analysis_job_write__does_not_retry_generic_oserror(
    tmp_path, monkeypatch
):
    replace_calls = []
    sleep_calls = []

    def failing_replace(source, target):
        replace_calls.append((source, target))
        raise OSError("replace failed")

    monkeypatch.setattr(analysis_jobs.os, "replace", failing_replace)
    monkeypatch.setattr(analysis_jobs.time, "sleep", sleep_calls.append)

    with pytest.raises(OSError, match="replace failed"):
        analysis_jobs._write_analysis_job(
            tmp_path,
            {"job_id": f"{102:032x}", "status": "queued"},
        )

    assert len(replace_calls) == 1
    assert sleep_calls == []


def test_analysis_job_execution__progress_persistence_failure_does_not_abort(
    tmp_path, monkeypatch, capsys
):
    job = _create_job(
        tmp_path,
        103,
        status="queued",
        operation="layer",
        started_at=None,
        completed_at=None,
        live_publish_status="not_applicable",
        live_publish_revision=None,
    )
    writes = []

    async def fake_worker(
        operation,
        root,
        target=None,
        exclude_paths=None,
        log=None,
    ):
        assert operation == "layer"
        assert log is not None
        log("progress")
        return {}

    def flaky_write(root, payload):
        writes.append(dict(payload))
        if payload.get("message") == "progress":
            raise OSError("progress persistence failed")

    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
    monkeypatch.setattr(analysis_jobs, "_write_analysis_job", flaky_write)

    asyncio.run(
        analysis_jobs._execute_analysis_job(
            tmp_path,
            job,
            None,
            None,
        )
    )

    assert any(item.get("status") == "completed" for item in writes)
    stderr = capsys.readouterr().err
    assert "[analysis-job-persistence] phase=progress" in stderr
    assert "progress persistence failed" in stderr


def test_analysis_job_execution__primary_failure_survives_failed_persistence(
    tmp_path, monkeypatch, capsys
):
    job = _create_job(
        tmp_path,
        104,
        status="queued",
        operation="layer",
        started_at=None,
        completed_at=None,
        live_publish_status="not_applicable",
        live_publish_revision=None,
    )
    job_id = job["job_id"]
    writes = []

    async def failing_worker(*args, **kwargs):
        raise ValueError("primary boom")

    def flaky_write(root, payload):
        writes.append(dict(payload))
        if payload.get("status") == "failed":
            raise OSError("secondary persistence boom")

    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", failing_worker)
    monkeypatch.setattr(analysis_jobs, "_write_analysis_job", flaky_write)
    monkeypatch.setitem(analysis_jobs._analysis_tasks, job_id, object())
    monkeypatch.setitem(
        analysis_jobs._analysis_jobs_by_repo,
        str(tmp_path),
        job_id,
    )

    asyncio.run(
        analysis_jobs._execute_analysis_job(
            tmp_path,
            job,
            None,
            None,
        )
    )

    failed_payloads = [
        item for item in writes if item.get("status") == "failed"
    ]
    assert len(failed_payloads) == 1
    assert failed_payloads[0]["error"] == "ValueError: primary boom"
    assert job_id not in analysis_jobs._analysis_tasks
    assert str(tmp_path) not in analysis_jobs._analysis_jobs_by_repo

    stderr = capsys.readouterr().err
    assert "[analysis-job-persistence] phase=failed" in stderr
    assert "secondary persistence boom" in stderr


def test_analysis_status_concurrency__same_process_dead_worker_is_interrupted(
    tmp_path, monkeypatch
):
    job = _create_job(
        tmp_path,
        105,
        status="running",
        owner_pid=os.getpid(),
    )
    monkeypatch.delitem(
        analysis_jobs._analysis_tasks,
        job["job_id"],
        raising=False,
    )

    res = json.loads(
        get_analysis_status(str(tmp_path), job_id=job["job_id"])
    )

    assert res["status"] == "interrupted"
    assert res["error"] == "worker_not_active"

    persisted = analysis_jobs._read_analysis_job(
        tmp_path,
        job["job_id"],
    )
    assert persisted["status"] == "interrupted"
    assert persisted["error"] == "worker_not_active"


def test_analysis_status_concurrency__reconciliation_write_failure_returns_interrupted(
    tmp_path, monkeypatch
):
    job = _create_job(
        tmp_path,
        106,
        status="running",
        owner_pid=os.getpid(),
    )
    monkeypatch.delitem(
        analysis_jobs._analysis_tasks,
        job["job_id"],
        raising=False,
    )

    def fail_write(*args, **kwargs):
        raise OSError("cannot persist reconciliation")

    monkeypatch.setattr(
        analysis_jobs,
        "_write_analysis_job",
        fail_write,
    )

    res = json.loads(
        get_analysis_status(str(tmp_path), job_id=job["job_id"])
    )

    assert res["status"] == "interrupted"
    assert res["error"] == "worker_not_active"
    assert "Durable reconciliation persistence failed" in res["message"]
    assert "cannot persist reconciliation" in res["message"]


def test_active_analysis_jobs__excludes_dead_same_process_worker(
    tmp_path, monkeypatch
):
    current = _create_job(
        tmp_path,
        107,
        status="running",
        owner_pid=os.getpid(),
        mtime_ns=2_000_000_000,
    )
    foreign = _create_job(
        tmp_path,
        108,
        status="running",
        owner_pid=os.getpid() + 100000,
        mtime_ns=1_000_000_000,
    )
    monkeypatch.delitem(
        analysis_jobs._analysis_tasks,
        current["job_id"],
        raising=False,
    )

    active = analysis_jobs._active_analysis_jobs(tmp_path)

    assert [job["job_id"] for job in active] == [foreign["job_id"]]

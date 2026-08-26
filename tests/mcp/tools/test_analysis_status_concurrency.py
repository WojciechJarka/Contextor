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
    _create_job(root, 1, status="queued", mtime_ns=1_000_000_000)
    _create_job(root, 2, status="running", mtime_ns=2_000_000_000)

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

    raw = get_analysis_status(str(root), job_id=j1["job_id"])
    res = json.loads(raw)

    assert res["status"] == "queued"
    assert res["job_id"] == j1["job_id"]


def test_analysis_status_concurrency__single_active_does_not_override_newer_completed_latest(tmp_path):
    root = tmp_path
    _create_job(root, 1, status="running", mtime_ns=1_000_000_000)
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
    _create_job(root, 1, status="queued", mtime_ns=1_000_000_000)
    _create_job(root, 2, status="failed", mtime_ns=2_000_000_000)
    j3 = _create_job(root, 3, status="completed", mtime_ns=3_000_000_000)

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    # active_count is 1 (job 1), so no ambiguity; latest mtime is job 3 (completed)
    assert res["status"] == "completed"
    assert res["job_id"] == j3["job_id"]


def test_analysis_status_concurrency__active_candidates_are_deterministic_newest_first(tmp_path):
    root = tmp_path
    j1 = _create_job(root, 1, status="queued", mtime_ns=1_000_000_000)
    j2 = _create_job(root, 2, status="running", mtime_ns=3_000_000_000)
    j3 = _create_job(root, 3, status="running", mtime_ns=2_000_000_000)

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "ambiguous_job"
    returned_ids = [item["job_id"] for item in res["active_jobs"]]
    assert returned_ids == [j2["job_id"], j3["job_id"], j1["job_id"]]


def test_analysis_status_concurrency__equal_mtime_uses_job_id_tiebreak(tmp_path):
    root = tmp_path
    j1 = _create_job(root, 1, status="queued", mtime_ns=1_000_000_000)
    j2 = _create_job(root, 2, status="running", mtime_ns=1_000_000_000)

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "ambiguous_job"
    returned_ids = [item["job_id"] for item in res["active_jobs"]]
    assert returned_ids == [j1["job_id"], j2["job_id"]]


def test_analysis_status_concurrency__candidate_list_is_bounded_to_five(tmp_path):
    root = tmp_path
    for i in range(1, 8):
        _create_job(root, i, status="running", mtime_ns=i * 1_000_000_000)

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

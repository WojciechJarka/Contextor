import json
import os
from pathlib import Path
import pytest

from contextor.mcp.output_guard import (
    LARGE_OUTPUT_WARNING_BYTES,
    guard_large_output,
    largest_fitting_prefix,
)
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import analysis_jobs
from contextor.mcp.tools.search_source import search_source
from contextor.mcp.tools.lookup_index_entries import lookup_index_entries
from contextor.mcp.tools.get_analysis_status import get_analysis_status
from contextor.mcp.tools.get_source_range import get_source_range


# ---------------------------------------------------------------------------
# 1. largest_fitting_prefix helper tests
# ---------------------------------------------------------------------------


def test_auto_bounded_output__largest_fitting_prefix_exact_threshold():
    # Candidate of exact 15360 bytes fits
    def build(count: int) -> str:
        return "x" * 15360

    res = largest_fitting_prefix(10, build, min_count=1)
    assert res is not None
    candidate, count = res
    assert count == 10
    assert len(candidate.encode("utf-8")) == LARGE_OUTPUT_WARNING_BYTES


def test_auto_bounded_output__largest_fitting_prefix_rejects_threshold_plus_one():
    # 15361 bytes does not fit
    def build(count: int) -> str:
        return "x" * 15361

    res = largest_fitting_prefix(10, build, min_count=1)
    assert res is None


def test_auto_bounded_output__largest_fitting_prefix_selects_largest_count():
    # Each item adds 1000 bytes. With base 360 bytes, count 15 = 15360 bytes (fits), count 16 = 16360 (too large)
    def build(count: int) -> str:
        return "a" * (360 + count * 1000)

    res = largest_fitting_prefix(30, build, min_count=1)
    assert res is not None
    candidate, count = res
    assert count == 15
    assert len(candidate.encode("utf-8")) == 15360


def test_auto_bounded_output__largest_fitting_prefix_returns_none_when_minimum_too_large():
    def build(count: int) -> str:
        return "x" * (20000 + count * 100)

    res = largest_fitting_prefix(10, build, min_count=1)
    assert res is None


# ---------------------------------------------------------------------------
# 2. search_source auto-bounding tests
# ---------------------------------------------------------------------------


def _setup_search_source_repo(tmp_path: Path, match_count: int = 50, match_size: int = 500):
    repo = tmp_path / "search_repo"
    repo.mkdir(parents=True, exist_ok=True)
    pkg = repo / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)

    code_lines = ["# Large file for search_source test"]
    for i in range(match_count):
        code_lines.append(f"def func_{i}():")
        code_lines.append(f"    '''docstring with target symbol {'y' * match_size}'''")
        code_lines.append(f"    return {i}")
    target_file = pkg / "large_module.py"
    target_file.write_text("\n".join(code_lines), encoding="utf-8")

    class Module:
        path = "pkg/large_module.py"
        absolute_path = str(target_file)

    class State:
        resync_required = False
        canonical_files = ["pkg/large_module.py"]
        excluded_files = []
        modules = {"pkg.large_module": Module()}

    class Engine:
        state = State()

    return repo, Engine()


def test_auto_bounded_output__search_source_returns_useful_single_shot_prefix(tmp_path, monkeypatch):
    repo, engine = _setup_search_source_repo(tmp_path, match_count=50, match_size=500)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda root: engine)

    raw = search_source(str(repo), search_term="target", allow_large_output=False, limit=None)
    res = json.loads(raw)

    assert res["status"] == "ok"
    assert "_output" in res
    output_meta = res["_output"]
    assert output_meta["auto_bounded"] is True
    assert output_meta["full_output_bytes"] > LARGE_OUTPUT_WARNING_BYTES
    assert output_meta["warning_threshold_bytes"] == LARGE_OUTPUT_WARNING_BYTES
    assert output_meta["retry"] == {"allow_large_output": True}
    assert output_meta["requested_count"] == 50
    assert 1 <= output_meta["returned_count"] < 50
    assert len(res["matches"]) == output_meta["returned_count"]
    assert len(raw.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES


def test_auto_bounded_output__search_source_prefix_is_exact_deterministic_prefix(tmp_path, monkeypatch):
    repo, engine = _setup_search_source_repo(tmp_path, match_count=40, match_size=600)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda root: engine)

    raw_auto = search_source(str(repo), search_term="target", allow_large_output=False, limit=None)
    res_auto = json.loads(raw_auto)

    raw_full = search_source(str(repo), search_term="target", allow_large_output=True, limit=None)
    res_full = json.loads(raw_full)

    returned_count = res_auto["_output"]["returned_count"]
    assert res_auto["matches"] == res_full["matches"][:returned_count]


def test_auto_bounded_output__search_source_full_output_bytes_refers_to_original_limited_candidate(tmp_path, monkeypatch):
    repo, engine = _setup_search_source_repo(tmp_path, match_count=60, match_size=400)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda root: engine)

    # With limit=30
    raw_auto = search_source(str(repo), search_term="target", allow_large_output=False, limit=30)
    res_auto = json.loads(raw_auto)

    raw_full_30 = search_source(str(repo), search_term="target", allow_large_output=True, limit=30)
    res_full_30 = json.loads(raw_full_30)

    assert res_auto["_output"]["requested_count"] == 30
    assert res_auto["_output"]["full_output_bytes"] == len(raw_full_30.encode("utf-8"))


def test_auto_bounded_output__search_source_allow_large_output_returns_original_full_candidate(tmp_path, monkeypatch):
    repo, engine = _setup_search_source_repo(tmp_path, match_count=40, match_size=500)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda root: engine)

    raw_full = search_source(str(repo), search_term="target", allow_large_output=True, limit=None)
    res_full = json.loads(raw_full)

    assert res_full["status"] == "ok"
    assert "_output" not in res_full
    assert len(res_full["matches"]) == 40
    assert len(raw_full.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES


def test_auto_bounded_output__search_source_falls_back_to_confirmation_when_one_match_is_too_large(tmp_path, monkeypatch):
    repo, engine = _setup_search_source_repo(tmp_path, match_count=1, match_size=18000)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda root: engine)

    raw = search_source(str(repo), search_term="target", allow_large_output=False, limit=None)
    res = json.loads(raw)

    assert res["status"] == "confirmation_required"
    assert "retry" in res
    assert res["retry"]["allow_large_output"] is True


# ---------------------------------------------------------------------------
# 3. lookup_index_entries auto-bounding tests
# ---------------------------------------------------------------------------


def _setup_lookup_index_catalog(monkeypatch, total_entries: int = 150):
    from contextor.core import report_query
    from contextor.mcp.tools import lookup_index_entries as lookup_tool_module

    artifacts = {f"A{i}/1": f"pkg.module_{i}::func_{'z' * 120}_{i}" for i in range(total_entries)}
    catalog = report_query.IndexCatalog(
        modules={},
        artifacts=artifacts,
        recovered_modules={},
        recovered_artifacts={},
    )
    monkeypatch.setattr(
        lookup_tool_module,
        "catalog_from_registry",
        lambda root, module_paths=None: catalog,
    )
    return [f"A{i}/1" for i in range(total_entries)]


def test_auto_bounded_output__lookup_index_entries_returns_prefix_and_reserved_metadata(tmp_path, monkeypatch):
    ids = _setup_lookup_index_catalog(monkeypatch, total_entries=150)

    raw = lookup_index_entries(str(tmp_path), ids=ids, allow_large_output=False)
    res = json.loads(raw)

    assert "_output" in res
    meta = res["_output"]
    assert meta["auto_bounded"] is True
    assert meta["full_output_bytes"] > LARGE_OUTPUT_WARNING_BYTES
    assert meta["warning_threshold_bytes"] == LARGE_OUTPUT_WARNING_BYTES
    assert meta["requested_count"] == 150
    assert 1 <= meta["returned_count"] < 150
    assert meta["retry"] == {"allow_large_output": True}

    # Count decoded entries (excluding _output)
    decoded_ids = [k for k in res if k != "_output"]
    assert len(decoded_ids) == meta["returned_count"]
    assert len(raw.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES


def test_auto_bounded_output__lookup_index_entries_preserves_input_order(tmp_path, monkeypatch):
    ids = _setup_lookup_index_catalog(monkeypatch, total_entries=100)

    raw = lookup_index_entries(str(tmp_path), ids=ids, allow_large_output=False)
    res = json.loads(raw)

    decoded_ids = [k for k in res if k != "_output"]
    assert decoded_ids == ids[: len(decoded_ids)]


def test_auto_bounded_output__lookup_index_entries_small_response_has_no_output_metadata(tmp_path, monkeypatch):
    ids = _setup_lookup_index_catalog(monkeypatch, total_entries=5)

    raw = lookup_index_entries(str(tmp_path), ids=ids, allow_large_output=False)
    res = json.loads(raw)

    assert "_output" not in res
    assert len(res) == 5
    assert set(res.keys()) == set(ids)


def test_auto_bounded_output__lookup_index_entries_allow_large_output_is_lossless(tmp_path, monkeypatch):
    ids = _setup_lookup_index_catalog(monkeypatch, total_entries=150)

    raw = lookup_index_entries(str(tmp_path), ids=ids, allow_large_output=True)
    res = json.loads(raw)

    assert "_output" not in res
    assert len(res) == 150
    assert set(res.keys()) == set(ids)
    assert len(raw.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES


def test_auto_bounded_output__lookup_index_entries_single_entry_too_large_confirms(tmp_path, monkeypatch):
    from contextor.core import report_query
    from contextor.mcp.tools import lookup_index_entries as lookup_tool_module

    huge_name = "pkg.module::" + ("x" * 18000)
    catalog = report_query.IndexCatalog(
        modules={},
        artifacts={"A1/1": huge_name},
        recovered_modules={},
        recovered_artifacts={},
    )
    monkeypatch.setattr(
        lookup_tool_module,
        "catalog_from_registry",
        lambda root, module_paths=None: catalog,
    )

    raw = lookup_index_entries(str(tmp_path), ids=["A1/1"], allow_large_output=False)
    res = json.loads(raw)

    assert res["status"] == "confirmation_required"
    assert res["retry"] == {"allow_large_output": True}


# ---------------------------------------------------------------------------
# 4. get_analysis_status auto-bounding tests
# ---------------------------------------------------------------------------


def _setup_analysis_job_with_skipped(tmp_path: Path, skipped_count: int = 150):
    repo = tmp_path / "status_repo"
    repo.mkdir(parents=True, exist_ok=True)

    skipped = [
        {"file": f"pkg/skipped_{i}.py", "reason": f"SyntaxError in generated code line {i}: {'w' * 120}"}
        for i in range(skipped_count)
    ]
    job_payload = {
        "job_id": "0123456789abcdef0123456789abcdef",
        "operation": "project",
        "repo_path": str(repo),
        "target": None,
        "status": "completed",
        "created_at": "2026-08-26T12:00:00Z",
        "started_at": "2026-08-26T12:00:01Z",
        "completed_at": "2026-08-26T12:00:05Z",
        "updated_at": "2026-08-26T12:00:05Z",
        "message": "Analysis completed successfully.",
        "error": None,
        "owner_pid": os.getpid(),
        "live_publish_status": "success",
        "live_publish_revision": 1,
        "live_publish_warning": None,
        "skipped_python_files": skipped,
    }
    analysis_jobs._write_analysis_job(repo, job_payload)
    return repo, job_payload


def test_auto_bounded_output__analysis_status_only_bounds_skipped_files(tmp_path):
    repo, job = _setup_analysis_job_with_skipped(tmp_path, skipped_count=150)

    raw = get_analysis_status(str(repo), job_id=job["job_id"], max_skipped_files=None, allow_large_output=False)
    res = json.loads(raw)

    assert res["status"] == "completed"
    assert "_output" in res
    meta = res["_output"]
    assert meta["auto_bounded"] is True
    assert meta["bounded_collection"] == "skipped_files"
    assert meta["full_output_bytes"] > LARGE_OUTPUT_WARNING_BYTES
    assert meta["warning_threshold_bytes"] == LARGE_OUTPUT_WARNING_BYTES
    assert meta["retry"] == {"allow_large_output": True}
    assert 0 <= meta["returned_count"] < 150
    assert len(res["analysis_coverage"]["skipped_python_files"]["items"]) == meta["returned_count"]
    assert len(raw.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES


def test_auto_bounded_output__analysis_status_preserves_job_scalars(tmp_path):
    repo, job = _setup_analysis_job_with_skipped(tmp_path, skipped_count=100)

    raw = get_analysis_status(str(repo), job_id=job["job_id"], max_skipped_files=None, allow_large_output=False)
    res = json.loads(raw)
    persisted = analysis_jobs._read_analysis_job(repo, job["job_id"])

    for field in (
        "job_id",
        "operation",
        "repo_path",
        "status",
        "created_at",
        "started_at",
        "completed_at",
        "updated_at",
        "message",
        "live_publish_status",
        "live_publish_revision",
    ):
        assert res[field] == persisted[field]


def test_auto_bounded_output__analysis_status_allow_large_output_is_lossless(tmp_path):
    repo, job = _setup_analysis_job_with_skipped(tmp_path, skipped_count=150)

    raw = get_analysis_status(str(repo), job_id=job["job_id"], max_skipped_files=None, allow_large_output=True)
    res = json.loads(raw)

    assert "_output" not in res
    assert len(res["analysis_coverage"]["skipped_python_files"]["items"]) == 150
    assert len(raw.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES


def test_auto_bounded_output__analysis_status_minimal_job_too_large_confirms(tmp_path):
    repo = tmp_path / "huge_status_repo"
    repo.mkdir(parents=True, exist_ok=True)

    job_payload = {
        "job_id": "0123456789abcdef0123456789abcdef",
        "operation": "project",
        "repo_path": str(repo),
        "target": None,
        "status": "failed",
        "created_at": "2026-08-26T12:00:00Z",
        "started_at": "2026-08-26T12:00:01Z",
        "completed_at": "2026-08-26T12:00:05Z",
        "updated_at": "2026-08-26T12:00:05Z",
        "message": "Error details: " + ("e" * 18000),
        "error": "huge_error",
        "owner_pid": os.getpid(),
        "live_publish_status": "failed",
        "live_publish_revision": None,
        "live_publish_warning": None,
        "skipped_python_files": [],
    }
    analysis_jobs._write_analysis_job(repo, job_payload)

    raw = get_analysis_status(str(repo), job_id=job_payload["job_id"], allow_large_output=False)
    res = json.loads(raw)

    assert res["status"] == "confirmation_required"
    assert res["retry"] == {"allow_large_output": True}


def test_auto_bounded_output__analysis_status_does_not_mutate_persisted_job(tmp_path):
    repo, job = _setup_analysis_job_with_skipped(tmp_path, skipped_count=100)

    # Run auto-bounded query
    get_analysis_status(str(repo), job_id=job["job_id"], max_skipped_files=None, allow_large_output=False)

    # Read the persisted job from disk and verify it still has all 100 skipped files
    persisted = analysis_jobs._read_analysis_job(repo, job["job_id"])
    assert len(persisted["skipped_python_files"]) == 100


# ---------------------------------------------------------------------------
# 5. get_source_range lossless confirmation guard regression test
# ---------------------------------------------------------------------------


def test_auto_bounded_output__source_range_remains_lossless_confirmation_guarded(tmp_path, monkeypatch):
    repo = tmp_path / "range_repo"
    repo.mkdir(parents=True, exist_ok=True)
    target_file = repo / "module.py"

    lines = [f"x_{i:04d} = 'value_{i:04d}_{'a' * 40}'" for i in range(500)]
    target_file.write_text("\n".join(lines), encoding="utf-8")

    class Module:
        path = "module.py"
        absolute_path = str(target_file)

    class State:
        resync_required = False
        canonical_files = ["module.py"]
        excluded_files = []
        modules = {"module": Module()}

    class Engine:
        state = State()

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda root: Engine())

    # 1. Large range (>15360 bytes) with allow_large_output=False -> confirmation_required
    raw_guard = get_source_range(str(repo), file_path="module.py", start_line=1, end_line=450, allow_large_output=False)
    res_guard = json.loads(raw_guard)
    assert res_guard["status"] == "confirmation_required"
    assert "_output" not in res_guard

    # 2. Large range with allow_large_output=True -> lossless requested range
    raw_full = get_source_range(str(repo), file_path="module.py", start_line=1, end_line=450, allow_large_output=True)
    res_full = json.loads(raw_full)
    assert res_full["status"] == "ok"
    assert res_full["total_lines"] == 450
    assert "_output" not in res_full
    assert len(raw_full.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES

    # 3. Small range (<=15360 bytes) -> normal output without _output metadata
    raw_small = get_source_range(str(repo), file_path="module.py", start_line=1, end_line=50, allow_large_output=False)
    res_small = json.loads(raw_small)
    assert res_small["status"] == "ok"
    assert res_small["total_lines"] == 50
    assert "_output" not in res_small
    assert len(raw_small.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES


def test_auto_bounded_output__lookup_reserved_output_key_is_never_overwritten(
    tmp_path,
    monkeypatch,
):
    from contextor.core import report_query
    from contextor.mcp.tools import lookup_index_entries as lookup_tool_module

    huge_name = "pkg.module::" + ("x" * 300)

    artifacts = {
        f"A{i}/1": f"{huge_name}_{i}"
        for i in range(150)
    }

    catalog = report_query.IndexCatalog(
        modules={},
        artifacts=artifacts,
        recovered_modules={},
        recovered_artifacts={},
    )

    monkeypatch.setattr(
        lookup_tool_module,
        "catalog_from_registry",
        lambda root, module_paths=None: catalog,
    )

    ids = ["_output"] + [f"A{i}/1" for i in range(150)]

    raw = lookup_index_entries(
        str(tmp_path),
        ids=ids,
        allow_large_output=False,
    )
    result = json.loads(raw)

    assert result["status"] == "confirmation_required"
    assert result["retry"] == {"allow_large_output": True}

    approved = json.loads(
        lookup_index_entries(
            str(tmp_path),
            ids=ids,
            allow_large_output=True,
        )
    )

    assert approved["_output"] == {
        "name": None,
        "status": "missing",
    }


def test_auto_bounded_output__shared_warning_threshold_is_15360():
    assert LARGE_OUTPUT_WARNING_BYTES == 15360

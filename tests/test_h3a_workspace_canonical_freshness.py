import json
import os
import time
from pathlib import Path

from contextor.core.api.facade import ContextorFacade
from contextor.mcp import analysis_jobs
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.query_helpers import build_state_freshness
from contextor.mcp.tools.get_artifact_blast_radius import get_artifact_blast_radius
from contextor.mcp.tools.get_file_edit_context import get_file_edit_context
from contextor.mcp.tools.get_module_context import get_module_context
from contextor.mcp.tools.get_symbol_call_context import get_symbol_call_context
from contextor.mcp.tools.get_symbol_implementation import get_symbol_implementation
from contextor.mcp.tools.lookup_artifact_by_symbol import lookup_artifact_by_symbol
from contextor.mcp.tools.search_artifacts import search_artifacts


def _setup_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    pkg = repo / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    mod_a = pkg / "mod_a.py"
    mod_a.write_text(
        "def compute_data(x: int) -> int:\n    return x * 2\n",
        encoding="utf-8",
    )
    mod_b = pkg / "mod_b.py"
    mod_b.write_text(
        "from pkg.mod_a import compute_data\n\ndef run():\n    return compute_data(10)\n",
        encoding="utf-8",
    )
    return repo, mod_a


def test_h3a_case_a_t0_canonical_matches_disk_verified(tmp_path):
    """Case A: T0 canonical state matches disk => workspace_sync='verified', advisory_warning=None."""
    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    mcp_runtime._live_engines.pop(str(repo), None)

    res_raw = get_module_context(repo_path=str(repo), module_name="pkg.mod_a")
    res = json.loads(res_raw)
    freshness = res.get("state_freshness")
    assert freshness is not None
    assert freshness["canonical_state"] == "fresh"
    assert freshness["workspace_sync"] == "verified"
    assert freshness["advisory_warning"] is None

    # Test blast radius
    res_blast = json.loads(get_artifact_blast_radius(repo_path=str(repo), artifact="pkg.mod_a::compute_data"))
    assert res_blast["state_freshness"]["workspace_sync"] == "verified"

    # Test file edit context
    res_edit = json.loads(get_file_edit_context(repo_path=str(repo), file_path="pkg/mod_a.py"))
    assert res_edit["state_freshness"]["workspace_sync"] == "verified"

    # Test repo-wide lookup and search (unverified)
    res_search = json.loads(search_artifacts(repo_path=str(repo), query="compute_data"))
    assert res_search["state_freshness"]["workspace_sync"] == "unverified"

    res_lookup = json.loads(lookup_artifact_by_symbol(repo_path=str(repo), symbol="compute_data"))
    assert res_lookup["state_freshness"]["workspace_sync"] == "unverified"


def test_h3a_case_b_disk_t1_no_watcher_out_of_sync(tmp_path):
    """Case B: User edits disk with watcher OFF => workspace_sync='out_of_sync'."""
    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    mcp_runtime._live_engines.pop(str(repo), None)

    # Modify file on disk at T1
    time.sleep(0.05)
    mod_a.write_text(
        "def compute_data(x: int) -> int:\n    # Modified on disk\n    return x * 3\n",
        encoding="utf-8",
    )

    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
    freshness = res.get("state_freshness")
    assert freshness is not None
    assert freshness["workspace_sync"] == "out_of_sync"
    assert "modified" in freshness["advisory_warning"].lower()

    # File edit context must also flag out_of_sync and add a warning
    res_edit = json.loads(get_file_edit_context(repo_path=str(repo), file_path="pkg/mod_a.py"))
    assert res_edit["state_freshness"]["workspace_sync"] == "out_of_sync"
    assert any("out of sync" in w for w in res_edit.get("warnings", []))


def test_h3a_case_c_disk_t1_interrupted_job(tmp_path):
    """Case C: Disk modified + analysis job interrupted => workspace_sync='out_of_sync' + advisory."""
    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    mcp_runtime._live_engines.pop(str(repo), None)

    # Edit file
    time.sleep(0.05)
    mod_a.write_text("def compute_data(x: int) -> int:\n    return x + 1\n", encoding="utf-8")

    # Record an interrupted analysis job
    job = {
        "job_id": "a" * 32,
        "operation": "project",
        "repo_path": str(repo),
        "target": None,
        "exclude_paths": [],
        "status": "interrupted",
        "created_at": "2026-08-26T20:00:00Z",
        "started_at": "2026-08-26T20:00:01Z",
        "completed_at": "2026-08-26T20:00:05Z",
        "message": "The MCP server process was interrupted.",
        "error": "owner_process_changed",
        "live_publish_status": "not_attempted",
        "live_publish_revision": None,
        "live_publish_warning": None,
        "owner_pid": 999999,
    }
    analysis_jobs._write_analysis_job(repo, job)

    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
    freshness = res.get("state_freshness")
    assert freshness is not None
    assert freshness["workspace_sync"] == "out_of_sync"
    assert freshness["advisory_warning"] is not None


def test_h3a_case_d_post_interruption_live_reconciles_t1(tmp_path):
    """Case D: After interrupted job, LIVE reconciles T1 => workspace_sync='verified', not marked stale."""
    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    mcp_runtime._live_engines.pop(str(repo), None)

    # Record an older interrupted job
    job = {
        "job_id": "b" * 32,
        "operation": "project",
        "repo_path": str(repo),
        "target": None,
        "exclude_paths": [],
        "status": "interrupted",
        "created_at": "2026-08-26T20:00:00Z",
        "started_at": "2026-08-26T20:00:01Z",
        "completed_at": "2026-08-26T20:00:05Z",
        "message": "Older interrupted job",
        "error": "owner_process_changed",
        "live_publish_status": "not_attempted",
        "owner_pid": 999999,
    }
    analysis_jobs._write_analysis_job(repo, job)

    # Now simulate incremental LIVE update reconciling mod_a
    engine = mcp_runtime.get_or_init_engine(repo)
    time.sleep(0.05)
    mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 100\n", encoding="utf-8")
    engine.update_file(str(mod_a))

    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
    freshness = res.get("state_freshness")
    assert freshness is not None
    assert freshness["workspace_sync"] == "verified"
    assert freshness["canonical_state"] == "fresh"


def test_h3a_case_e_snapshot_provenance_fresh(tmp_path):
    """Case E: Hydrated from snapshot without live daemon => provenance='snapshot', fresh."""
    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    mcp_runtime._live_engines.pop(str(repo), None)

    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
    freshness = res.get("state_freshness")
    assert freshness is not None
    assert freshness["provenance"] == "snapshot"
    assert freshness["canonical_state"] == "fresh"
    assert freshness["workspace_sync"] == "verified"


def test_h3a_case_f_symbol_implementation_fail_closed_on_line_shift_out_of_sync(tmp_path):
    """Case F: get_symbol_implementation with T0 canonical location + disk T1 line shift fails closed."""
    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    mcp_runtime._live_engines.pop(str(repo), None)

    # Shift lines on disk
    time.sleep(0.05)
    mod_a.write_text(
        "# Header comment line 1\n# Header comment line 2\n\ndef compute_data(x: int) -> int:\n    return x * 2\n",
        encoding="utf-8",
    )

    res_preview = json.loads(
        get_symbol_implementation(repo_path=str(repo), symbol="pkg.mod_a::compute_data", mode="preview")
    )
    assert res_preview["status"] == "stale_source"
    assert res_preview["state_freshness"]["workspace_sync"] == "out_of_sync"
    assert res_preview["state_freshness"]["advisory_warning"] is not None
    assert "implementation" not in res_preview
    assert "fetch_plans" not in res_preview
    assert res_preview["source_contract"]["implementation_is_complete"] is False

    res_fetch = json.loads(
        get_symbol_implementation(repo_path=str(repo), symbol="pkg.mod_a::compute_data", mode="fetch", include=["implementation", "static_context"])
    )
    assert res_fetch["status"] == "stale_source"
    assert res_fetch["state_freshness"]["workspace_sync"] == "out_of_sync"
    assert "implementation" not in res_fetch


def test_h3a_case_g_same_size_same_mtime_content_changed_out_of_sync(tmp_path):
    """Case G (Blocker 1): content T1 != T0, size(T1) == size(T0), mtime restored to T0 => out_of_sync."""
    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    mcp_runtime._live_engines.pop(str(repo), None)

    stat0 = mod_a.stat()
    orig_bytes = mod_a.read_bytes()
    orig_len = len(orig_bytes)

    # Replace with different content of exact same length
    new_bytes = orig_bytes.replace(b"return x * 2", b"return x * 9")
    assert len(new_bytes) == orig_len
    mod_a.write_bytes(new_bytes)

    # Manually restore mtime to stat0 mtime_ns
    os.utime(str(mod_a), ns=(stat0.st_atime_ns, stat0.st_mtime_ns))
    stat_restored = mod_a.stat()
    assert stat_restored.st_mtime_ns == stat0.st_mtime_ns
    assert stat_restored.st_size == stat0.st_size

    # Query tool must compute hash on exact target and detect out_of_sync
    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
    freshness = res.get("state_freshness")
    assert freshness is not None
    assert freshness["workspace_sync"] == "out_of_sync"
    assert "modified" in freshness["advisory_warning"].lower()


def test_h3a_case_h_provenance_and_revision_strictly_match_answered_state(tmp_path):
    """Case H (Blocker 2): Freshness envelope strictly describes the answered state/engine, not ambient daemon."""
    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))

    # Engine is loaded from snapshot
    engine = mcp_runtime.get_or_init_engine(repo)
    assert engine is not None

    # Simulate an external live daemon revision recorded in global table
    mcp_runtime._live_engine_revisions[str(repo)] = 999

    # If build_state_freshness is called with engine=None and state having revision 12,
    # and repo_key removed from live_engine_revisions, it must describe snapshot revision 12.
    from types import SimpleNamespace
    snapshot_state = SimpleNamespace(
        revision=12,
        resync_required=False,
        modules={},
        dependency_graph=None,
        topology_metrics_state="deferred",
        artifact_consumption_state="deferred",
        cycles_state="deferred",
        collisions_state="deferred",
    )
    # Without live engine key, answered state is snapshot
    mcp_runtime._live_engine_revisions.pop(str(repo), None)
    freshness = build_state_freshness(repo, snapshot_state, engine=None)
    assert freshness["provenance"] == "snapshot"
    assert freshness["canonical_revision"] == 12

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
    """Case H (Blocker 2): Freshness envelope strictly describes the answered state/engine, not ambient daemon.
    
    Conflict test: answered_state.revision = S (12), ambient runtime cached revision = L (999).
    Helper receives the answered state. EXPECT: canonical_revision == S (12), not L (999).
    We do NOT pop _live_engine_revisions before calling.
    """
    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))

    # Simulate an external live daemon revision recorded in global table
    mcp_runtime._live_engine_revisions[str(repo)] = 999
    mcp_runtime._live_engine_provenance[str(repo)] = "live"

    from types import SimpleNamespace
    snapshot_state = SimpleNamespace(
        revision=12,
        provenance="snapshot",
        state_id="snap_12",
        resync_required=False,
        modules={},
        dependency_graph=None,
        topology_metrics_state="deferred",
        artifact_consumption_state="deferred",
        cycles_state="deferred",
        collisions_state="deferred",
    )
    # Even though ambient table has revision=999, provenance="live", answered state has revision=12, provenance="snapshot"
    freshness = build_state_freshness(repo, snapshot_state, engine=None)
    assert freshness["provenance"] == "snapshot"
    assert freshness["canonical_revision"] == 12


def test_h3a_case_i_crash_window_false_verified_prevented(tmp_path):
    """Case I (Blocker 1 - Crash Window Regression):
    T0: canonical snapshot T0, FileState T0
    T1: target modified on disk, FileState updated to T1 and saved to file_state.json,
        canonical snapshot T1 NOT published/saved (crash window).
    Hydration: answered state is T0, disk is T1, FileState is T1.
    EXPECT:
      ANSWERED_CANONICAL = T0
      DISK = T1
      FILESTATE = T1
      WORKSPACE_SYNC != 'verified'
      WORKSPACE_SYNC != 'metadata_match'
      WORKSPACE_SYNC == 'unverified'
    """
    from contextor.core.paths import repo_cache_dir
    from contextor.core.analysis.state_manager import FileStateManager

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    mcp_runtime._live_engines.pop(str(repo), None)

    # T0 state is persisted
    cache = repo_cache_dir(repo)
    sm_t0 = FileStateManager(str(cache))
    t0_state_id = sm_t0.state_id
    assert t0_state_id != ""

    # T1: modify target on disk
    time.sleep(0.05)
    mod_a.write_text(
        "def compute_data(x: int) -> int:\n    # T1 content\n    return x * 99\n",
        encoding="utf-8",
    )

    # Update FileStateManager to T1 and save with new generation state_id T1
    sm_t1 = FileStateManager(str(cache))
    sm_t1.update_state(str(mod_a))
    t1_state_id = "2026-08-26_T1_CRASHED"
    sm_t1.save(state_id=t1_state_id, revision=2)

    # CRASH: do NOT save snapshot T1. Snapshot remains T0 (state_id=t0_state_id, revision=1).
    # Clear all memory caches to simulate process restart / hydration
    mcp_runtime._live_engines.pop(str(repo), None)
    mcp_runtime._live_engine_revisions.pop(str(repo), None)
    mcp_runtime._live_engine_provenance.pop(str(repo), None)

    # Query tool now hydrats canonical state from snapshot (T0) and FileStateManager from file_state.json (T1)
    res_raw = get_module_context(repo_path=str(repo), module_name="pkg.mod_a")
    res = json.loads(res_raw)
    freshness = res.get("state_freshness")

    assert freshness is not None
    # Verified that generation mismatch fails closed to unverified
    assert freshness["workspace_sync"] != "verified"
    assert freshness["workspace_sync"] != "metadata_match"
    assert freshness["workspace_sync"] == "unverified"
    assert "generation" in freshness["advisory_warning"].lower() or "crash" in freshness["advisory_warning"].lower()


def test_h3a_case_j_local_incremental_mutation_revision_sync(tmp_path):
    """Case J (Blocker 2 - Incremental Mutation Revision Sync):
    Snapshot engine revision R0 -> engine.update_file -> canonical state R1.
    Query on the same cached engine:
      ANSWERED_STATE_REVISION == R1
      STATE_FRESHNESS_CANONICAL_REVISION == R1
    """
    from contextor.mcp.tools.update_file import update_file

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    mcp_runtime._live_engines.pop(str(repo), None)

    # Hydrate engine at R0
    engine0 = mcp_runtime.get_or_init_engine(repo)
    r0 = engine0.revision or 1

    # Modify file and update via MCP update_file tool
    time.sleep(0.05)
    mod_a.write_text(
        "def compute_data(x: int) -> int:\n    # R1 content\n    return x * 50\n",
        encoding="utf-8",
    )
    upd_res_raw = update_file(repo_path=str(repo), file_path=str(mod_a))
    upd_res = json.loads(upd_res_raw)
    assert upd_res["status"] == "UPDATED"

    # Query with cached engine
    query_raw = get_module_context(repo_path=str(repo), module_name="pkg.mod_a")
    query_res = json.loads(query_raw)
    freshness = query_res["state_freshness"]

    assert freshness["workspace_sync"] == "verified"
    assert freshness["canonical_revision"] > r0
    assert engine0.state.revision == freshness["canonical_revision"]


def test_h3a_case_k_real_remote_live_lifecycle_and_journal_separation(tmp_path):
    """Case K (Blocker 2 - Real Remote LIVE Proof & Journal Separation):
    1. Bootstrap real canonical snapshot via analyze_project;
    2. Start real CanonicalLiveServer with updater on background thread;
    3. Connect real client and verify initial journal revision J0 == snapshot revision (1);
    4. Execute status event (client.status('Server alive')), incrementing journal revision to J1 (2),
       WITHOUT modifying canonical source facts;
    5. Call get_or_init_engine(repo) via MCP runtime to hydrate from remote live server;
    6. Verify:
       - state_freshness['canonical_revision'] == 1 (publication revision, not journal revision 2)
       - state_freshness['provenance'] == 'live'
       - state_freshness['workspace_sync'] == 'verified'
    7. Execute real LIVE file update:
       - modify target file on disk (disk T1)
       - client.update_file(str(mod_a), origin='test')
       - re-hydrate and query via get_module_context
       EXPECT:
       - workspace_sync == 'verified'
       - canonical_revision == 2 (matching T1 snapshot publication)
       - FileState fingerprint matches same publication.
    """
    import threading
    from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
    from contextor.core.live_state.store import load_snapshot
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import require_repository_identity

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    identity = require_repository_identity(repo)
    cache = repo_cache_dir(repo)

    # Load canonical snapshot from disk
    loaded = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
    assert loaded is not None
    state, metadata = loaded

    # 2. Start real CanonicalLiveServer
    server = CanonicalLiveServer(state, revision=metadata.revision, updater=_repository_updater(repo))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # 3. Register endpoint
    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    ep_payload = {
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }
    ep_file.write_text(json.dumps(ep_payload), encoding="utf-8")

    client = LiveStateClient(server.endpoint)
    try:
        # Initial ping
        ping0 = client.ping()
        assert ping0["status"] == "ok"
        j0 = ping0["revision"]
        assert j0 == metadata.revision

        # 4. Status event increments journal revision to J1 without changing source snapshot
        client.status("Server heartbeat status", origin="test")
        ping1 = client.ping()
        j1 = ping1["revision"]
        assert j1 == j0 + 1

        # 5. MCP runtime hydrates from live daemon
        mcp_runtime._live_engines.pop(str(repo), None)
        mcp_runtime._live_engine_revisions.pop(str(repo), None)
        mcp_runtime._live_engine_provenance.pop(str(repo), None)
        mcp_runtime._live_journal_revisions.pop(str(repo), None)

        engine_live = mcp_runtime.get_or_init_engine(repo)
        assert engine_live is not None

        res_raw = get_module_context(repo_path=str(repo), module_name="pkg.mod_a")
        res = json.loads(res_raw)
        freshness = res["state_freshness"]

        # 6. Verify publication revision != journal revision
        assert freshness["provenance"] == "live"
        assert freshness["canonical_revision"] == metadata.revision  # e.g. 1
        assert j1 == metadata.revision + 1  # e.g. 2
        assert freshness["workspace_sync"] == "verified"
        assert freshness["advisory_warning"] is None

        # 7. Execute real LIVE file update
        time.sleep(0.05)
        mod_a.write_text(
            "def compute_data(x: int) -> int:\n    # T1 remote live update\n    return x * 77\n",
            encoding="utf-8",
        )
        upd = client.update_file(str(mod_a), origin="test")
        assert upd["status"] == "ok"
        new_journal_rev = upd["revision"]

        # Clear MCP in-memory cache to force hydration of new live snapshot
        mcp_runtime._live_engines.pop(str(repo), None)
        res_t1_raw = get_module_context(repo_path=str(repo), module_name="pkg.mod_a")
        res_t1 = json.loads(res_t1_raw)
        freshness_t1 = res_t1["state_freshness"]

        assert freshness_t1["provenance"] == "live"
        assert freshness_t1["canonical_revision"] == metadata.revision + 1
        assert freshness_t1["workspace_sync"] == "verified"
        assert freshness_t1["advisory_warning"] is None
    finally:
        server.close()


def test_h3a_case_l_legacy_filestate_missing_revision(tmp_path):
    """Case L (Blocker 1 Regression A):
    canonical: state_id="X", revision=10, facts=T0
    file_state: state_id="X", revision=MISSING (None), sha256=T1
    disk=T1
    EXPECT: workspace_sync='unverified', NEVER 'verified', NEVER 'metadata_match'.
    """
    from contextor.core.paths import repo_cache_dir
    from contextor.core.analysis.state_manager import FileStateManager

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    mcp_runtime._live_engines.pop(str(repo), None)

    cache = repo_cache_dir(repo)
    sm = FileStateManager(str(cache))
    t0_state_id = sm.state_id

    # Modify file on disk to T1
    time.sleep(0.05)
    mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 88\n", encoding="utf-8")

    # Update file_state on disk with matching sha256 and matching state_id, but MISSING revision
    sm.update_state(str(mod_a))
    # Write file_state.json directly without revision
    fs_file = cache / "file_state.json"
    fs_data = {
        "_meta": {"state_id": t0_state_id},  # No revision key
        "files": {path: fs.to_dict() for path, fs in sm._state.items()}
    }
    fs_file.write_text(json.dumps(fs_data, indent=2), encoding="utf-8")

    mcp_runtime._live_engines.pop(str(repo), None)
    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
    freshness = res["state_freshness"]

    assert freshness["workspace_sync"] != "verified"
    assert freshness["workspace_sync"] != "metadata_match"
    assert freshness["workspace_sync"] == "unverified"
    assert "generation" in freshness["advisory_warning"].lower()


def test_h3a_case_m_legacy_filestate_missing_state_id(tmp_path):
    """Case M (Blocker 1 Regression B):
    canonical: state_id="X", revision=1
    file_state: state_id="", revision=1, sha256=disk
    EXPECT: workspace_sync='unverified'.
    """
    from contextor.core.paths import repo_cache_dir
    from contextor.core.analysis.state_manager import FileStateManager

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    mcp_runtime._live_engines.pop(str(repo), None)

    cache = repo_cache_dir(repo)
    sm = FileStateManager(str(cache))

    # Write file_state.json with empty state_id
    fs_file = cache / "file_state.json"
    fs_data = {
        "_meta": {"state_id": "", "revision": 1},
        "files": {path: fs.to_dict() for path, fs in sm._state.items()}
    }
    fs_file.write_text(json.dumps(fs_data, indent=2), encoding="utf-8")

    mcp_runtime._live_engines.pop(str(repo), None)
    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
    freshness = res["state_freshness"]

    assert freshness["workspace_sync"] != "verified"
    assert freshness["workspace_sync"] != "metadata_match"
    assert freshness["workspace_sync"] == "unverified"


def test_h3a_case_n_filestate_both_generation_fields_missing(tmp_path):
    """Case N (Blocker 1 Regression C):
    canonical: state_id="X", revision=1
    file_state: state_id="", revision=None
    EXPECT: workspace_sync='unverified'.
    """
    from contextor.core.paths import repo_cache_dir
    from contextor.core.analysis.state_manager import FileStateManager

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    mcp_runtime._live_engines.pop(str(repo), None)

    cache = repo_cache_dir(repo)
    sm = FileStateManager(str(cache))

    # Write file_state.json without _meta or empty _meta
    fs_file = cache / "file_state.json"
    fs_data = {
        "files": {path: fs.to_dict() for path, fs in sm._state.items()}
    }
    fs_file.write_text(json.dumps(fs_data, indent=2), encoding="utf-8")

    mcp_runtime._live_engines.pop(str(repo), None)
    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
    freshness = res["state_freshness"]

    assert freshness["workspace_sync"] != "verified"
    assert freshness["workspace_sync"] != "metadata_match"
    assert freshness["workspace_sync"] == "unverified"


def test_h3a_case_o_live_daemon_restart_cache_invalidation_across_epochs(tmp_path):
    """Case O (H3A-H4 Blocker - LIVE Daemon Restart Epoch Invalidation):
    T0: S1 starts from snapshot P0=1.
    S1 performs 20 status pings -> journal J1=21 >> P0.
    MCP hydrates engine: cached journal J1=21, cached engine P0=1.
    S1 stops.
    S2 starts from snapshot P0: initial journal J_init=1.
    Target file modified on disk (T1) -> S2 update_file: publication P1=2, journal J2=2 (numerically << J1=21).
    MCP query runs WITHOUT manual clearing of _live_engines / _live_journal_revisions / _live_sessions.
    EXPECT:
      - Live session restart detected (S2 != S1)
      - Remote snapshot refreshed
      - Query reflects P1=2
      - canonical_revision=2
      - workspace_sync='verified'
      - Stale P0 engine is NOT returned.
    """
    import threading
    from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
    from contextor.core.live_state.store import load_snapshot
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import require_repository_identity

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    identity = require_repository_identity(repo)
    cache = repo_cache_dir(repo)

    # 1. Start Server S1
    loaded = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
    state, metadata = loaded
    p0 = metadata.revision  # 1

    server1 = CanonicalLiveServer(state, revision=p0, updater=_repository_updater(repo))
    t1 = threading.Thread(target=server1.serve_forever, daemon=True)
    t1.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    ep_file.write_text(json.dumps({
        "host": server1.endpoint.host,
        "port": server1.endpoint.port,
        "authkey_hex": server1.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }), encoding="utf-8")

    client1 = LiveStateClient(server1.endpoint)
    # Increment journal revision heavily via status events
    for i in range(20):
        client1.status(f"status {i}", origin="test")
    ping_s1 = client1.ping()
    j1 = ping_s1["revision"]
    assert j1 == p0 + 20  # 21

    # Hydrate MCP runtime engine for S1
    mcp_runtime._live_engines.pop(str(repo), None)
    mcp_runtime._live_journal_revisions.pop(str(repo), None)
    mcp_runtime._live_sessions.pop(str(repo), None)

    engine_s1 = mcp_runtime.get_or_init_engine(repo)
    assert engine_s1 is not None
    assert mcp_runtime._live_journal_revisions.get(str(repo)) == j1  # 21
    assert mcp_runtime._live_engine_revisions.get(str(repo)) == p0  # 1

    # 2. Stop S1
    server1.close()

    # 3. Start Server S2 from disk snapshot (without clearing MCP cache)
    loaded_s2 = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
    state_s2, metadata_s2 = loaded_s2
    server2 = CanonicalLiveServer(state_s2, revision=metadata_s2.revision, updater=_repository_updater(repo))
    t2 = threading.Thread(target=server2.serve_forever, daemon=True)
    t2.start()

    ep_file.write_text(json.dumps({
        "host": server2.endpoint.host,
        "port": server2.endpoint.port,
        "authkey_hex": server2.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }), encoding="utf-8")

    client2 = LiveStateClient(server2.endpoint)
    try:
        # Initial journal on S2 is 1 (P0)
        assert client2.ping()["revision"] == p0

        # Modify target file on disk
        time.sleep(0.05)
        mod_a.write_text(
            "def compute_data(x: int) -> int:\n    # S2 P1 update\n    return x * 100\n",
            encoding="utf-8",
        )
        upd = client2.update_file(str(mod_a), origin="test")
        assert upd["status"] == "ok"
        j2 = upd["revision"]  # 2
        assert j2 < j1  # 2 < 21! Numeric comparison would fail, but epoch session tracking succeeds!

        # 4. MCP query WITHOUT manually clearing ANY caches
        res_raw = get_module_context(repo_path=str(repo), module_name="pkg.mod_a")
        res = json.loads(res_raw)
        freshness = res["state_freshness"]

        assert freshness["provenance"] == "live"
        assert freshness["canonical_revision"] == p0 + 1  # 2
        assert freshness["workspace_sync"] == "verified"
        assert freshness["advisory_warning"] is None

        # Verify cached engine is the new S2 engine
        cached_eng = mcp_runtime._live_engines.get(str(repo))
        assert cached_eng.revision == p0 + 1
        assert mcp_runtime._live_journal_revisions.get(str(repo)) == j2
    finally:
        server2.close()


def test_h3a_case_p_unchanged_session_redundant_snapshot_fetch_zero(tmp_path):
    """Case P (H3A-H4 - Unchanged Session Redundant Snapshot Fetch is Zero):
    Within the same LIVE session, repeated MCP engine calls when no journal events occur
    do NOT fetch the snapshot again from the daemon.
    """
    import threading
    from unittest.mock import patch
    from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
    from contextor.core.live_state.store import load_snapshot
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import require_repository_identity

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    identity = require_repository_identity(repo)
    cache = repo_cache_dir(repo)

    loaded = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
    state, metadata = loaded
    server = CanonicalLiveServer(state, revision=metadata.revision, updater=_repository_updater(repo))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    ep_file.write_text(json.dumps({
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }), encoding="utf-8")

    try:
        mcp_runtime._live_engines.pop(str(repo), None)
        mcp_runtime._live_journal_revisions.pop(str(repo), None)
        mcp_runtime._live_sessions.pop(str(repo), None)

        # First call hydrates engine
        engine1 = mcp_runtime.get_or_init_engine(repo)
        assert engine1 is not None

        # Subsequent calls in unchanged session
        orig_snapshot = LiveStateClient.snapshot
        snapshot_call_count = 0

        def counted_snapshot(self):
            nonlocal snapshot_call_count
            snapshot_call_count += 1
            return orig_snapshot(self)

        with patch.object(LiveStateClient, "snapshot", counted_snapshot):
            for _ in range(5):
                engine = mcp_runtime.get_or_init_engine(repo)
                assert engine is engine1

        # Redundant snapshot fetch count is 0
        assert snapshot_call_count == 0
    finally:
        server.close()


def test_h3a_case_q_equal_numeric_revision_cross_session_invalidation(tmp_path):
    """Case Q (H3A-H4 - Equal Numeric Revision Across Sessions Invalidates Cache):
    S1: journal=5, publication=1.
    S2 starts: journal=5, but publication=2.
    Equal numeric journal revision K=5 across different session identities MUST force snapshot refresh.
    """
    import threading
    from contextor.core.live_state import CanonicalLiveServer
    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
    from contextor.core.live_state.store import load_snapshot, save_snapshot
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import require_repository_identity

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    identity = require_repository_identity(repo)
    cache = repo_cache_dir(repo)

    # 1. Start Server S1
    loaded = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
    state, metadata = loaded
    server1 = CanonicalLiveServer(state, revision=5, updater=_repository_updater(repo))
    t1 = threading.Thread(target=server1.serve_forever, daemon=True)
    t1.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    ep_file.write_text(json.dumps({
        "host": server1.endpoint.host,
        "port": server1.endpoint.port,
        "authkey_hex": server1.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }), encoding="utf-8")

    mcp_runtime._live_engines.pop(str(repo), None)
    mcp_runtime._live_journal_revisions.pop(str(repo), None)
    mcp_runtime._live_sessions.pop(str(repo), None)

    # Hydrate MCP engine for S1 (journal=5, rev=1)
    engine_s1 = mcp_runtime.get_or_init_engine(repo)
    assert engine_s1 is not None
    assert mcp_runtime._live_journal_revisions.get(str(repo)) == 5
    assert mcp_runtime._live_engine_revisions.get(str(repo)) == 1

    server1.close()

    # 2. Update snapshot on disk to revision 2
    save_snapshot(state, cache, "state_2", writer="test", repo_id=identity.repo_id, root_path=identity.root_path, revision_floor=1)
    loaded2 = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
    state2, metadata2 = loaded2
    assert metadata2.revision == 2

    # 3. Start S2 with SAME numeric journal revision (5)
    server2 = CanonicalLiveServer(state2, revision=5, updater=_repository_updater(repo))
    t2 = threading.Thread(target=server2.serve_forever, daemon=True)
    t2.start()

    ep_file.write_text(json.dumps({
        "host": server2.endpoint.host,
        "port": server2.endpoint.port,
        "authkey_hex": server2.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }), encoding="utf-8")

    try:
        # WITHOUT clearing MCP cache:
        engine_s2 = mcp_runtime.get_or_init_engine(repo)
        assert engine_s2 is not None
        # Must have refreshed to revision 2 despite identical journal revision (5)
        assert engine_s2.revision == 2
        assert mcp_runtime._live_engine_revisions.get(str(repo)) == 2
    finally:
        server2.close()


def test_h3a_case_r_full_analysis_same_daemon_live_publication_sync(tmp_path):
    """Case R (H3A-H5 - Full Analysis Active LIVE Daemon Sync):
    T0: analyze_project creates P0. Start real CanonicalLiveServer daemon holding P0.
        MCP hydrates P0.
    T1: modify file on disk, run ContextorFacade.analyze_project(repo) with SAME daemon active.
        WITHOUT restarting daemon and WITHOUT manually clearing MCP caches.
    EXPECT:
      - DISK_SNAPSHOT = P1 (2)
      - FILESTATE = P1 (2)
      - LIVE_DAEMON_STATE = P1 (2)
      - get_module_context: canonical_revision=2, provenance='live', workspace_sync='verified', advisory_warning=None
      - get_symbol_implementation: status='resolved', implementation returned
      - get_file_edit_context: canonical_revision=2, provenance='live', workspace_sync='verified'
    """
    import threading
    from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
    from contextor.core.live_state.store import load_snapshot, read_metadata
    from contextor.core.paths import repo_cache_dir
    from contextor.core.analysis.state_manager import FileStateManager
    from contextor.core.repository_identity import require_repository_identity
    from contextor.mcp.tools.get_symbol_implementation import get_symbol_implementation
    from contextor.mcp.tools.get_file_edit_context import get_file_edit_context

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    identity = require_repository_identity(repo)
    cache = repo_cache_dir(repo)

    # 1. Start Server S1 holding P0
    loaded = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
    state, metadata = loaded
    p0 = metadata.revision  # 1

    server = CanonicalLiveServer(state, revision=p0, updater=_repository_updater(repo))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    ep_file.write_text(json.dumps({
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }), encoding="utf-8")

    try:
        # Clear MCP caches once before initial hydration
        mcp_runtime._live_engines.pop(str(repo), None)
        mcp_runtime._live_journal_revisions.pop(str(repo), None)
        mcp_runtime._live_sessions.pop(str(repo), None)

        # Hydrate MCP runtime at P0
        res_t0 = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
        assert res_t0["state_freshness"]["canonical_revision"] == p0
        assert res_t0["state_freshness"]["workspace_sync"] == "verified"
        assert res_t0["state_freshness"]["provenance"] == "live"

        # T1: modify file on disk
        time.sleep(0.05)
        mod_a.write_text(
            "def compute_data(x: int) -> int:\n    # T1 full analysis modification\n    return x * 123\n",
            encoding="utf-8",
        )

        # Run real full analysis while SAME LIVE daemon remains running
        errors, res = ContextorFacade.analyze_project(str(repo))
        assert not errors

        # Verify disk snapshot & FileState
        disk_meta = read_metadata(cache)
        assert disk_meta is not None
        p1 = disk_meta.revision
        assert p1 > p0

        sm = FileStateManager(str(cache))
        assert sm.revision == p1
        assert sm.state_id == disk_meta.state_id

        # Verify LIVE daemon state via client
        client = LiveStateClient(server.endpoint)
        daemon_snap = client.snapshot()
        daemon_state = daemon_snap.get("state")
        assert getattr(daemon_state, "revision", None) == p1
        assert getattr(daemon_state, "state_id", None) == disk_meta.state_id

        # 4. Execute real MCP queries WITHOUT manual clearing of ANY caches
        res_t1 = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
        freshness_t1 = res_t1["state_freshness"]
        assert freshness_t1["canonical_revision"] == p1
        assert freshness_t1["provenance"] == "live"
        assert freshness_t1["workspace_sync"] == "verified"
        assert freshness_t1["advisory_warning"] is None

        # get_symbol_implementation
        sym_res = json.loads(get_symbol_implementation(repo_path=str(repo), symbol="compute_data", mode="fetch", include=["implementation"]))
        assert sym_res["status"] == "resolved"
        assert sym_res["source_contract"]["implementation_is_complete"] is True
        assert "x * 123" in sym_res["implementation"]
        assert sym_res["state_freshness"]["canonical_revision"] == p1
        assert sym_res["state_freshness"]["workspace_sync"] == "verified"

        # get_file_edit_context
        edit_res = json.loads(get_file_edit_context(repo_path=str(repo), file_path=str(mod_a)))
        assert edit_res["state_freshness"]["canonical_revision"] == p1
        assert edit_res["state_freshness"]["workspace_sync"] == "verified"
    finally:
        server.close()


def test_h3a_case_s_explicit_generation_mismatch_symbol_fail_closed(tmp_path):
    """Case S (H3A-H5 - Explicit Generation Mismatch Symbol Implementation Fail Closed):
    canonical state: state_id="2026-08-27_P0", revision=1
    FileState on disk: state_id="2026-08-27_P1", revision=2
    get_symbol_implementation(symbol="compute_data", mode="fetch", include=["implementation"]) MUST fail closed:
      - status == "stale_source"
      - source_contract.implementation_is_complete == False
      - "implementation" not returned
    """
    from contextor.core.paths import repo_cache_dir
    from contextor.core.analysis.state_manager import FileStateManager
    from contextor.mcp.tools.get_symbol_implementation import get_symbol_implementation

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    cache = repo_cache_dir(repo)

    # Initial hydration at P0
    mcp_runtime._live_engines.pop(str(repo), None)
    mcp_runtime._live_journal_revisions.pop(str(repo), None)
    mcp_runtime._live_sessions.pop(str(repo), None)

    engine = mcp_runtime.get_or_init_engine(repo)
    assert engine is not None
    p0_sid = engine.state.state_id
    p0_rev = engine.state.revision

    # Mutate FileStateManager on disk to simulate explicit generation mismatch (P1 on disk, P0 in engine)
    sm = FileStateManager(str(cache))
    sm.update_state(str(mod_a))
    sm.save(state_id="2026-08-27_P1_MISMATCH", revision=p0_rev + 1)

    # get_symbol_implementation with cached engine (holding P0) against FileState on disk (holding P1)
    sym_res = json.loads(get_symbol_implementation(repo_path=str(repo), symbol="compute_data", mode="fetch", include=["implementation"]))

    assert sym_res["status"] == "stale_source"
    assert "implementation" not in sym_res
    assert sym_res["source_contract"]["implementation_is_complete"] is False
    assert sym_res["state_freshness"]["workspace_sync"] == "unverified"
    assert "generation" in sym_res["state_freshness"]["advisory_warning"].lower()
    assert "generation" in sym_res["stale_reason"].lower()


def test_h3a_case_t_active_daemon_successful_publish(tmp_path):
    """Case T (H3A-H6 - Active Daemon + Successful Publish):
    - Active daemon running holding P0
    - Full analysis T1 executed
    - EXPECT:
      - disk snapshot = P1
      - FileState = P1
      - daemon = P1
      - live_publish_status = 'success'
      - live_publish_revision = P1
      - live_publish_warning = None
    """
    import threading
    from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
    from contextor.core.live_state.store import load_snapshot, read_metadata
    from contextor.core.paths import repo_cache_dir
    from contextor.core.analysis.state_manager import FileStateManager
    from contextor.core.repository_identity import require_repository_identity

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    identity = require_repository_identity(repo)
    cache = repo_cache_dir(repo)

    loaded = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
    state, metadata = loaded
    p0 = metadata.revision

    server = CanonicalLiveServer(state, revision=p0, updater=_repository_updater(repo))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    ep_file.write_text(json.dumps({
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }), encoding="utf-8")

    try:
        time.sleep(0.05)
        mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 777\n", encoding="utf-8")

        errors, res = ContextorFacade.analyze_project(str(repo))
        assert not errors
        assert res is not None

        disk_meta = read_metadata(cache)
        assert disk_meta is not None
        p1 = disk_meta.revision
        assert p1 > p0

        sm = FileStateManager(str(cache))
        assert sm.revision == p1

        client = LiveStateClient(server.endpoint)
        daemon_snap = client.snapshot()
        daemon_state = daemon_snap.get("state")
        assert getattr(daemon_state, "revision", None) == p1

        # Check facade result metadata
        assert res.live_publish_status == "success"
        assert res.live_publish_revision == p1
        assert res.live_publish_warning is None
        assert res.summary_data.get("live_publish_status") == "success"
        assert res.summary_data.get("live_publish_revision") == p1
    finally:
        server.close()


def test_h3a_case_u_active_daemon_publish_raises_failure_semantics(tmp_path, monkeypatch):
    """Case U (H3A-H6 - Active Daemon + Publish Raises Exception):
    - Active daemon running holding P0
    - Publish fails with exception during full analysis
    - EXPECT:
      - disk snapshot = P1 (preserved)
      - FileState = P1 (preserved)
      - daemon remains P0
      - analysis completes without error
      - live_publish_status = 'failed'
      - live_publish_revision = None
      - live_publish_warning contains exception info
    """
    import threading
    from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
    from contextor.core.live_state.store import load_snapshot, read_metadata
    from contextor.core.paths import repo_cache_dir
    from contextor.core.analysis.state_manager import FileStateManager
    from contextor.core.repository_identity import require_repository_identity

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    identity = require_repository_identity(repo)
    cache = repo_cache_dir(repo)

    loaded = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
    state, metadata = loaded
    p0 = metadata.revision

    server = CanonicalLiveServer(state, revision=p0, updater=_repository_updater(repo))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    ep_file.write_text(json.dumps({
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }), encoding="utf-8")

    try:
        time.sleep(0.05)
        mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 888\n", encoding="utf-8")

        # Mock publish to raise RuntimeError
        orig_publish = LiveStateClient.publish
        def mock_publish(self, state, *args, **kwargs):
            raise ConnectionResetError("Simulated daemon socket drop")
        monkeypatch.setattr(LiveStateClient, "publish", mock_publish)

        errors, res = ContextorFacade.analyze_project(str(repo))
        assert not errors
        assert res is not None

        # Verify disk snapshot & FileState are preserved at P1
        disk_meta = read_metadata(cache)
        assert disk_meta is not None
        p1 = disk_meta.revision
        assert p1 > p0
        sm = FileStateManager(str(cache))
        assert sm.revision == p1

        # Restore publish and check daemon state is still P0
        monkeypatch.setattr(LiveStateClient, "publish", orig_publish)
        client = LiveStateClient(server.endpoint)
        daemon_snap = client.snapshot()
        daemon_state = daemon_snap.get("state")
        assert getattr(daemon_state, "revision", None) == p0

        # Check facade result metadata reports failure
        assert res.live_publish_status == "failed"
        assert res.live_publish_revision is None
        assert res.live_publish_warning is not None
        assert "ConnectionResetError" in res.live_publish_warning
        assert "Simulated daemon socket drop" in res.live_publish_warning
        assert res.summary_data.get("live_publish_status") == "failed"
    finally:
        server.close()


def test_h3a_case_v_active_daemon_publish_failure_response_dict(tmp_path, monkeypatch):
    """Case V (H3A-H6 - Active Daemon + Explicit Failure Response Dict):
    - Active daemon returns {'status': 'error', 'error': 'daemon_busy'}
    - EXPECT:
      - disk snapshot = P1 (preserved)
      - FileState = P1 (preserved)
      - daemon remains P0
      - live_publish_status = 'failed'
      - live_publish_revision = None
      - live_publish_warning = 'daemon_busy'
    """
    import threading
    from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
    from contextor.core.live_state.store import load_snapshot, read_metadata
    from contextor.core.paths import repo_cache_dir
    from contextor.core.analysis.state_manager import FileStateManager
    from contextor.core.repository_identity import require_repository_identity

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    identity = require_repository_identity(repo)
    cache = repo_cache_dir(repo)

    loaded = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
    state, metadata = loaded
    p0 = metadata.revision

    server = CanonicalLiveServer(state, revision=p0, updater=_repository_updater(repo))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    ep_file.write_text(json.dumps({
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }), encoding="utf-8")

    try:
        time.sleep(0.05)
        mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 999\n", encoding="utf-8")

        # Mock publish to return error dict
        orig_publish = LiveStateClient.publish
        def mock_publish(self, state, *args, **kwargs):
            return {"status": "error", "error": "daemon_busy_rejecting_publish"}
        monkeypatch.setattr(LiveStateClient, "publish", mock_publish)

        errors, res = ContextorFacade.analyze_project(str(repo))
        assert not errors
        assert res is not None

        # Verify disk snapshot & FileState are preserved at P1
        disk_meta = read_metadata(cache)
        assert disk_meta is not None
        p1 = disk_meta.revision
        assert p1 > p0
        sm = FileStateManager(str(cache))
        assert sm.revision == p1

        # Restore publish and check daemon state is still P0
        monkeypatch.setattr(LiveStateClient, "publish", orig_publish)
        client = LiveStateClient(server.endpoint)
        daemon_snap = client.snapshot()
        daemon_state = daemon_snap.get("state")
        assert getattr(daemon_state, "revision", None) == p0

        # Check facade result metadata reports failure
        assert res.live_publish_status == "failed"
        assert res.live_publish_revision is None
        assert res.live_publish_warning == "daemon_busy_rejecting_publish"
        assert res.summary_data.get("live_publish_status") == "failed"
    finally:
        server.close()


def test_h3a_case_w_no_active_daemon_not_attempted(tmp_path):
    """Case W (H3A-H6 - No Active Daemon -> not_attempted):
    - No daemon running
    - Full analysis executed
    - EXPECT:
      - disk snapshot and FileState are valid
      - live_publish_status = 'not_attempted'
      - live_publish_revision = None
      - live_publish_warning = None
      - NO false failure reported
    """
    repo, mod_a = _setup_repo(tmp_path)
    errors, res = ContextorFacade.analyze_project(str(repo))
    assert not errors
    assert res is not None

    assert res.live_publish_status == "not_attempted"
    assert res.live_publish_revision is None
    assert res.live_publish_warning is None
    assert res.summary_data.get("live_publish_status") == "not_attempted"


def test_h3a_case_x_journal_ahead_canonical_cache_separation(tmp_path):
    """Case X (H3A-H7 - Journal Ahead Real Live Regression):
    - P0 canonical revision = 1
    - Advance server journal J >= 20 via status events
    - Change file and run ContextorFacade.analyze_project(...)
    - EXPECT:
      - DISK_REVISION == 2
      - FILESTATE_REVISION == 2
      - LIVE_DAEMON_CANONICAL_REVISION == 2
      - PUBLISH_RETURN_REVISION >= 21
      - get_module_context(...) returns canonical_revision=2, workspace_sync='verified', provenance='live'
      - mcp_runtime._live_engine_revisions[root] == 2
      - Journal revision 20+ never ends up in canonical revision cache
    """
    import threading
    from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
    from contextor.core.live_state.store import load_snapshot, read_metadata
    from contextor.core.paths import repo_cache_dir
    from contextor.core.analysis.state_manager import FileStateManager
    from contextor.core.repository_identity import require_repository_identity

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    identity = require_repository_identity(repo)
    cache = repo_cache_dir(repo)

    loaded = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
    state, metadata = loaded
    p0 = metadata.revision
    assert p0 == 1

    server = CanonicalLiveServer(state, revision=p0, updater=_repository_updater(repo))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    ep_file.write_text(json.dumps({
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }), encoding="utf-8")

    try:
        time.sleep(0.05)
        client = LiveStateClient(server.endpoint)

        # Generate >= 20 journal events
        for i in range(20):
            res_stat = client.status(f"journal_event_{i}", origin="test")
            assert res_stat.get("status") == "ok"

        # Journal revision is now >= 21
        ping_info = client.ping()
        journal_before = int(ping_info["revision"])
        assert journal_before >= 21

        # Modify file and run full analysis
        time.sleep(0.05)
        mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 9999\n", encoding="utf-8")

        errors, res = ContextorFacade.analyze_project(str(repo))
        assert not errors
        assert res is not None

        # Verify disk, filestate, and daemon canonical revisions are 2
        disk_meta = read_metadata(cache)
        assert disk_meta is not None
        assert disk_meta.revision == 2

        sm = FileStateManager(str(cache))
        assert sm.revision == 2

        daemon_snap = client.snapshot()
        daemon_state = daemon_snap.get("state")
        assert getattr(daemon_state, "revision", None) == 2

        # Publish return revision is journal revision (>= 22)
        assert res.live_publish_status == "success"
        assert res.live_publish_revision > 2
        assert res.live_publish_revision >= journal_before + 1
        assert res.live_publish_warning is None

        # Without manual cache clear, query get_module_context
        ctx_raw = get_module_context(repo_path=str(repo), module_name="pkg.mod_a")
        ctx = json.loads(ctx_raw)
        freshness = ctx.get("state_freshness")
        assert freshness is not None
        assert freshness["canonical_revision"] == 2
        assert freshness["workspace_sync"] == "verified"
        assert freshness["provenance"] == "live"

        # Canonical cache is strictly 2, NOT the journal revision
        assert mcp_runtime._live_engine_revisions[str(repo)] == 2
        assert mcp_runtime._live_journal_revisions[str(repo)] >= 22
    finally:
        server.close()


def test_h3a_case_y_unknown_status_facade_fail_closed(tmp_path, monkeypatch):
    """Case Y (H3A-H7 - Unknown Status in Facade Fails Closed):
    - Client returns {'status': 'rejected', 'revision': 999}
    - EXPECT:
      - live_publish_status == 'failed'
      - live_publish_revision is None
      - live_publish_warning is not None and mentions rejected
    """
    import threading
    from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
    from contextor.core.live_state.store import load_snapshot
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import require_repository_identity

    repo, mod_a = _setup_repo(tmp_path)
    ContextorFacade.analyze_project(str(repo))
    identity = require_repository_identity(repo)
    cache = repo_cache_dir(repo)

    loaded = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
    state, metadata = loaded

    server = CanonicalLiveServer(state, revision=metadata.revision, updater=_repository_updater(repo))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    ep_file.write_text(json.dumps({
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": os.getpid(),
        "repo_id": identity.repo_id,
        "root_path": identity.root_path,
    }), encoding="utf-8")

    try:
        time.sleep(0.05)
        mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 12345\n", encoding="utf-8")

        monkeypatch.setattr(
            LiveStateClient,
            "publish",
            lambda self, state, *args, **kwargs: {"status": "rejected", "revision": 999},
        )

        errors, res = ContextorFacade.analyze_project(str(repo))
        assert not errors
        assert res is not None

        assert res.live_publish_status == "failed"
        assert res.live_publish_revision is None
        assert res.live_publish_warning is not None
        assert "rejected" in res.live_publish_warning
        assert res.summary_data.get("live_publish_status") == "failed"
        assert res.summary_data.get("live_publish_revision") is None
    finally:
        server.close()


def test_h3a_case_z_unknown_status_analysis_job_fail_closed(tmp_path, monkeypatch):
    """Case Z (H3A-H7 - Unknown Status in MCP Analysis Job Fails Closed):
    - Client returns {'status': 'rejected', 'revision': 999}
    - EXPECT:
      - job live_publish_status == 'failed'
      - job live_publish_revision is None
      - job live_publish_warning is not None and mentions rejected
      - mcp_runtime._live_engine_revisions does not keep stale/invalid entry
    """
    import asyncio
    from types import SimpleNamespace

    repo = tmp_path / "repo"
    repo.mkdir()

    engine_state = SimpleNamespace(fresh=True, revision=1)
    engine = SimpleNamespace(state=engine_state)
    client = SimpleNamespace(
        publish=lambda state, *, origin, timeout: {"status": "rejected", "revision": 999}
    )

    async def fake_worker(*_args, **_kwargs):
        pass

    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        "contextor.core.live_state.connect_or_start",
        lambda _root, *args, **kwargs: client,
    )
    analysis_jobs._analysis_tasks.clear()
    analysis_jobs._analysis_jobs_by_repo.clear()

    # Pre-seed canonical cache with stale value
    mcp_runtime._live_engine_revisions[str(repo)] = 999

    job_id = "a" * 32
    job = {
        "job_id": job_id,
        "repo_path": str(repo),
        "operation": "project",
        "target": None,
        "exclude_paths": [],
        "status": "queued",
        "created_at": "2026-08-27T10:00:00Z",
        "started_at": None,
        "completed_at": None,
        "error": None,
        "live_publish_status": "pending",
        "live_publish_revision": None,
        "live_publish_warning": None,
    }
    analysis_jobs._write_analysis_job(repo, job)

    asyncio.run(analysis_jobs._execute_analysis_job(repo, job, None, []))

    final_job = analysis_jobs._read_analysis_job(repo, job_id)
    assert final_job is not None
    assert final_job["status"] == "completed"
    assert final_job["live_publish_status"] == "failed"
    assert final_job["live_publish_revision"] is None
    assert final_job["live_publish_warning"] is not None
    assert "rejected" in final_job["live_publish_warning"]
    assert str(repo) not in mcp_runtime._live_engine_revisions


def test_h3a_case_aa_analysis_job_journal_canonical_revision_separation(tmp_path, monkeypatch):
    """Case AA (H3A-H7 - MCP Analysis Job Journal vs Canonical Revision Separation):
    - Client publish returns {'status': 'ok', 'revision': 42} (journal)
    - Canonical engine_state.revision = 3
    - EXPECT:
      - job live_publish_status == 'success'
      - job live_publish_revision == 42
      - mcp_runtime._live_engine_revisions[root] == 3 (canonical state revision, NOT 42)
    """
    import asyncio
    from types import SimpleNamespace

    repo = tmp_path / "repo"
    repo.mkdir()

    engine_state = SimpleNamespace(fresh=True, revision=3)
    engine = SimpleNamespace(state=engine_state)
    client = SimpleNamespace(
        publish=lambda state, *, origin, timeout: {"status": "ok", "revision": 42}
    )

    async def fake_worker(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        "contextor.core.live_state.connect_or_start",
        lambda _root, *args, **kwargs: client,
    )
    analysis_jobs._analysis_tasks.clear()
    analysis_jobs._analysis_jobs_by_repo.clear()

    job_id = "b" * 32
    job = {
        "job_id": job_id,
        "repo_path": str(repo),
        "operation": "project",
        "target": None,
        "exclude_paths": [],
        "status": "queued",
        "created_at": "2026-08-27T10:00:00Z",
        "started_at": None,
        "completed_at": None,
        "error": None,
        "live_publish_status": "pending",
        "live_publish_revision": None,
        "live_publish_warning": None,
    }
    analysis_jobs._write_analysis_job(repo, job)

    asyncio.run(analysis_jobs._execute_analysis_job(repo, job, None, []))

    final_job = analysis_jobs._read_analysis_job(repo, job_id)
    assert final_job is not None
    assert final_job["status"] == "completed"
    assert final_job["live_publish_status"] == "success"
    assert final_job["live_publish_revision"] == 42
    assert final_job["live_publish_warning"] is None
    assert mcp_runtime._live_engine_revisions[str(repo)] == 3





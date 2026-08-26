# CONTEXTOR — H3A & H3A-H5 CERTIFICATION & SYSTEM WALKTHROUGH

## 1. Executive Summary & Runtime Certification Verdict

Certyfikacja produkcyjna H3A i H3A-H5 na środowisku Contextor (`C:\Temp\Contextor_Repo`) zakończyła się pełnym sukcesem (`VERDICT=FINAL_PASS`).

### Kluczowe fakty z implementacji i weryfikacji runtime:
1. **Full Analysis → Active LIVE Daemon In-Place State Sync (H3A-H5)**:
   - Po zakończeniu pełnej analizy w `ContextorFacade.analyze_project` nowy kanoniczny stan (`state`), numer rewizji (`meta.revision`) oraz identyfikator generacji (`state_id`) są natychmiast publikowane do aktywnego demona LIVE (`client.publish(state, origin="desktop_analysis")`).
   - Aktywny demon LIVE zastępuje stan kanoniczny w pamięci bez konieczności restartu procesu demona ani klienta.
   - Po analizie: `DISK_SNAPSHOT_REVISION == FILESTATE_REVISION == LIVE_DAEMON_STATE_REVISION`.
2. **Fail-Closed w `get_symbol_implementation` na Explicit Generation Mismatch**:
   - `build_state_freshness` oraz `is_explicit_generation_mismatch` rozróżniają brak dowodów generacji (legacy missing evidence) od jawnej niezgodności generacji (explicit generation mismatch).
   - W przypadku jawnej niezgodności metadanych (`state_id` lub `revision` po obu stronach istnieją i są różne), `get_symbol_implementation` przechodzi w tryb fail-closed (`status="stale_source"`, `source_contract.implementation_is_complete=False`), chroniąc konsumentów przed otrzymaniem niepoprawnie skrojonych fragmentów kodu AST.
3. **Prawdziwe zapytania MCP**: `get_module_context`, `get_symbol_implementation` oraz `get_file_edit_context` zachowują pełną spójność między narzędziami (Cross-Tool Coherence).
4. **Separacja rewizji transportowej od publikacyjnej**: Transportowy journal demona i rewizja publikacji kanonicznej działają jako niezależne, ściśle powiązane liczniki.
5. **Wyniki testów**: **179/179 passed (100%)** w 7 dedykowanych zestawach testów.

---

## 2. Test Certification Report

```
TEST_SUITE=tests/test_h3a_workspace_canonical_freshness.py
PASSED=19
FAILED=0
ERRORS=0

TEST_SUITE=tests/test_live_state_store.py
PASSED=11
FAILED=0
ERRORS=0

TEST_SUITE=tests/test_live_state_ipc.py
PASSED=24
FAILED=0
ERRORS=0

TEST_SUITE=tests/test_live_e2e_corrections.py
PASSED=8
FAILED=0
ERRORS=0

TEST_SUITE=tests/test_mcp_regressions.py
PASSED=86
FAILED=0
ERRORS=0

TEST_SUITE=tests/test_mcp_documentation.py
PASSED=8
FAILED=0
ERRORS=0

TEST_SUITE=tests/test_symbol_call_facts.py
PASSED=23
FAILED=0
ERRORS=0

TOTAL_PASSED=179
TOTAL_FAILED=0
TOTAL_ERRORS=0

CASE_O_LIVE_DAEMON_RESTART_EPOCH=PASS
CASE_P_UNCHANGED_SESSION_REDUNDANT_FETCH=PASS
CASE_Q_EQUAL_NUMERIC_CROSS_SESSION=PASS
CASE_R_FULL_ANALYSIS_SAME_DAEMON_SYNC=PASS
CASE_S_EXPLICIT_GENERATION_MISMATCH_SYMBOL_FAIL_CLOSED=PASS
LEGACY_MISSING_REVISION=PASS
LEGACY_MISSING_STATE_ID=PASS
LEGACY_MISSING_BOTH=PASS
REAL_REMOTE_LIVE_JOURNAL_SEPARATION=PASS
LOCAL_INCREMENTAL_REVISION_SYNC=PASS

CODE_CHANGES=YES
DIFFS=ATTACHED

VERDICT=FINAL_PASS
```

---

## 3. Kompletne diffy modyfikacji H3A-H5

### 1. `contextor/core/api/facade.py`
```diff
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -493,6 +493,15 @@ class ContextorFacade:
             if meta is not None:
                 sm = FileStateManager(str(repo_cache_dir(path)))
                 sm.save(datestamp or "", revision=meta.revision)
+                from contextor.core.live_state import connect
+
+                try:
+                    client = connect(path)
+                    if client is not None:
+                        client.publish(state, origin="desktop_analysis")
+                except Exception as e:
+                    if log:
+                        log(f"Warning: Failed to publish canonical state to live daemon: {e}")
 
         progress.begin("Finalizing analysis")
         progress.finish()
```

### 2. `contextor/mcp/query_helpers.py`
```diff
--- a/contextor/mcp/query_helpers.py
+++ b/contextor/mcp/query_helpers.py
@@ -330,8 +330,11 @@ def build_state_freshness(
     if canonical_rev is None and engine is not None:
         canonical_rev = getattr(engine, "revision", None)
     filestate_rev = getattr(state_mgr, "revision", None) if state_mgr is not None else None
 
+    explicit_disk_mismatch = is_explicit_generation_mismatch(root_path, state, engine=engine)
+
     generation_coherent = bool(
-        canonical_state_id
+        not explicit_disk_mismatch
+        and canonical_state_id
         and filestate_state_id
         and str(canonical_state_id).strip() != ""
         and str(filestate_state_id).strip() != ""
@@ -445,3 +448,46 @@ def build_state_freshness(
         "advisory_warning": advisory_warning,
     }
+
+
+def is_explicit_generation_mismatch(
+    root: str | Path,
+    state: Any = None,
+    *,
+    engine: Any = None,
+) -> bool:
+    """Return True if both canonical state and FileState carry generation metadata that explicitly mismatch."""
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.analysis.state_manager import FileStateManager
+
+    root_path = Path(root).expanduser().resolve()
+    disk_mgr = None
+    try:
+        cache_dir = repo_cache_dir(root_path)
+        disk_mgr = FileStateManager(str(cache_dir))
+    except Exception:
+        disk_mgr = None
+
+    state_mgr = getattr(engine, "state_manager", None) or disk_mgr
+
+    canonical_state_id = getattr(state, "state_id", None) if state is not None else None
+    canonical_rev = getattr(state, "revision", None) if state is not None else None
+    if canonical_rev is None and engine is not None:
+        canonical_rev = getattr(engine, "revision", None)
+
+    managers_to_check = []
+    if disk_mgr is not None:
+        managers_to_check.append(disk_mgr)
+    if state_mgr is not None and state_mgr is not disk_mgr:
+        managers_to_check.append(state_mgr)
+
+    for mgr in managers_to_check:
+        filestate_state_id = getattr(mgr, "state_id", None)
+        filestate_rev = getattr(mgr, "revision", None)
+        state_id_mismatch = bool(
+            canonical_state_id
+            and filestate_state_id
+            and str(canonical_state_id).strip() != ""
+            and str(filestate_state_id).strip() != ""
+            and str(canonical_state_id).strip() != str(filestate_state_id).strip()
+        )
+        rev_mismatch = bool(
+            canonical_rev is not None
+            and filestate_rev is not None
+            and int(canonical_rev) != int(filestate_rev)
+        )
+        if state_id_mismatch or rev_mismatch:
+            return True
+    return False
```

### 3. `contextor/mcp/tools/get_symbol_implementation.py`
```diff
--- a/contextor/mcp/tools/get_symbol_implementation.py
+++ b/contextor/mcp/tools/get_symbol_implementation.py
@@ -167,8 +167,23 @@ def _symbol_preview(
     # canonical state that produced the T0 line locations, returning source would
     # risk delivering a stale/misaligned fragment. Surface this as a first-class
     # stale status instead. metadata_match (no sha256) is treated conservatively.
-    source_unreliable = state_freshness.get("workspace_sync") in {"out_of_sync", "metadata_match"}
+    # Furthermore, explicit generation mismatch between canonical state and FileState
+    # must fail closed to prevent serving misaligned AST slices.
+    explicit_mismatch = query_helpers.is_explicit_generation_mismatch(
+        root, engine.state if engine else None, engine=engine
+    )
     source_unreliable = (
         state_freshness.get("workspace_sync") in {"out_of_sync", "metadata_match"}
         or explicit_mismatch
     )
     if source_unreliable:
+        stale_reason = (
+            "Source file on disk has diverged from canonical generation / state. "
+            "Re-run analyze_project or update_file to refresh canonical state before fetching implementation."
+            if explicit_mismatch
+            else "Source file on disk has diverged from canonical T0 state. "
+            "Re-run analyze_project or update_file to refresh canonical state before fetching implementation."
+        )
         return {
             **base,
             "status": "stale_source",
@@ -175,7 +190,7 @@ def _symbol_preview(
-            "stale_reason": (
-                "Source file on disk has diverged from canonical T0 state. "
-                "Re-run analyze_project or update_file to refresh canonical state before fetching implementation."
-            ),
+            "stale_reason": stale_reason,
             "source_contract": {
                 "implementation_is_complete": False,
                 "implementation_includes_docstring": False,
```

### 4. `tests/test_h3a_workspace_canonical_freshness.py`
```diff
--- a/tests/test_h3a_workspace_canonical_freshness.py
+++ b/tests/test_h3a_workspace_canonical_freshness.py
@@ -851,3 +851,162 @@ def test_h3a_case_q_equal_numeric_revision_cross_session_invalidation(tmp_path):
         server2.close()
 
 
+def test_h3a_case_r_full_analysis_same_daemon_live_publication_sync(tmp_path):
+    """Case R (H3A-H5 - Full Analysis Active LIVE Daemon Sync):
+    T0: analyze_project creates P0. Start real CanonicalLiveServer daemon holding P0.
+        MCP hydrates P0.
+    T1: modify file on disk, run ContextorFacade.analyze_project(repo) with SAME daemon active.
+        WITHOUT restarting daemon and WITHOUT manually clearing MCP caches.
+    EXPECT:
+      - DISK_SNAPSHOT = P1 (2)
+      - FILESTATE = P1 (2)
+      - LIVE_DAEMON_STATE = P1 (2)
+      - get_module_context: canonical_revision=2, provenance='live', workspace_sync='verified', advisory_warning=None
+      - get_symbol_implementation: status='resolved', implementation returned
+      - get_file_edit_context: canonical_revision=2, provenance='live', workspace_sync='verified'
+    """
+    import threading
+    from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
+    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
+    from contextor.core.live_state.store import load_snapshot, read_metadata
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.repository_identity import require_repository_identity
+    from contextor.mcp.tools.get_symbol_implementation import get_symbol_implementation
+    from contextor.mcp.tools.get_file_edit_context import get_file_edit_context
+
+    repo, mod_a = _setup_repo(tmp_path)
+    ContextorFacade.analyze_project(str(repo))
+    identity = require_repository_identity(repo)
+    cache = repo_cache_dir(repo)
+
+    # 1. Start Server S1 holding P0
+    loaded = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
+    state, metadata = loaded
+    p0 = metadata.revision  # 1
+
+    server = CanonicalLiveServer(state, revision=p0, updater=_repository_updater(repo))
+    t = threading.Thread(target=server.serve_forever, daemon=True)
+    t.start()
+
+    ep_file = endpoint_file(repo)
+    ep_file.parent.mkdir(parents=True, exist_ok=True)
+    ep_file.write_text(json.dumps({
+        "host": server.endpoint.host,
+        "port": server.endpoint.port,
+        "authkey_hex": server.endpoint.authkey_hex,
+        "pid": os.getpid(),
+        "repo_id": identity.repo_id,
+        "root_path": identity.root_path,
+    }), encoding="utf-8")
+
+    try:
+        # Clear MCP caches once before initial hydration
+        mcp_runtime._live_engines.pop(str(repo), None)
+        mcp_runtime._live_journal_revisions.pop(str(repo), None)
+        mcp_runtime._live_sessions.pop(str(repo), None)
+
+        # Hydrate MCP runtime at P0
+        res_t0 = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
+        assert res_t0["state_freshness"]["canonical_revision"] == p0
+        assert res_t0["state_freshness"]["workspace_sync"] == "verified"
+        assert res_t0["state_freshness"]["provenance"] == "live"
+
+        # T1: modify file on disk
+        time.sleep(0.05)
+        mod_a.write_text(
+            "def compute_data(x: int) -> int:\n    # T1 full analysis modification\n    return x * 123\n",
+            encoding="utf-8",
+        )
+
+        # Run real full analysis while SAME LIVE daemon remains running
+        errors, res = ContextorFacade.analyze_project(str(repo))
+        assert not errors
+
+        # Verify disk snapshot & FileState
+        disk_meta = read_metadata(cache)
+        assert disk_meta is not None
+        p1 = disk_meta.revision
+        assert p1 > p0
+
+        sm = FileStateManager(str(cache))
+        assert sm.revision == p1
+        assert sm.state_id == disk_meta.state_id
+
+        # Verify LIVE daemon state via client
+        client = LiveStateClient(server.endpoint)
+        daemon_snap = client.snapshot()
+        daemon_state = daemon_snap.get("state")
+        assert getattr(daemon_state, "revision", None) == p1
+        assert getattr(daemon_state, "state_id", None) == disk_meta.state_id
+
+        # 4. Execute real MCP queries WITHOUT manual clearing of ANY caches
+        res_t1 = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
+        freshness_t1 = res_t1["state_freshness"]
+        assert freshness_t1["canonical_revision"] == p1
+        assert freshness_t1["provenance"] == "live"
+        assert freshness_t1["workspace_sync"] == "verified"
+        assert freshness_t1["advisory_warning"] is None
+
+        # get_symbol_implementation
+        sym_res = json.loads(get_symbol_implementation(repo_path=str(repo), symbol="compute_data", mode="fetch", include=["implementation"]))
+        assert sym_res["status"] == "resolved"
+        assert sym_res["source_contract"]["implementation_is_complete"] is True
+        assert "x * 123" in sym_res["implementation"]
+        assert sym_res["state_freshness"]["canonical_revision"] == p1
+        assert sym_res["state_freshness"]["workspace_sync"] == "verified"
+
+        # get_file_edit_context
+        edit_res = json.loads(get_file_edit_context(repo_path=str(repo), file_path=str(mod_a)))
+        assert edit_res["state_freshness"]["canonical_revision"] == p1
+        assert edit_res["state_freshness"]["workspace_sync"] == "verified"
+    finally:
+        server.close()
+
+
+def test_h3a_case_s_explicit_generation_mismatch_symbol_fail_closed(tmp_path):
+    """Case S (H3A-H5 - Explicit Generation Mismatch Symbol Implementation Fail Closed):
+    canonical state: state_id="2026-08-27_P0", revision=1
+    FileState on disk: state_id="2026-08-27_P1", revision=2
+    get_symbol_implementation(symbol="compute_data", mode="fetch", include=["implementation"]) MUST fail closed:
+      - status == "stale_source"
+      - source_contract.implementation_is_complete == False
+      - "implementation" not returned
+    """
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.mcp.tools.get_symbol_implementation import get_symbol_implementation
+
+    repo, mod_a = _setup_repo(tmp_path)
+    ContextorFacade.analyze_project(str(repo))
+    cache = repo_cache_dir(repo)
+
+    # Initial hydration at P0
+    mcp_runtime._live_engines.pop(str(repo), None)
+    mcp_runtime._live_journal_revisions.pop(str(repo), None)
+    mcp_runtime._live_sessions.pop(str(repo), None)
+
+    engine = mcp_runtime.get_or_init_engine(repo)
+    assert engine is not None
+    p0_sid = engine.state.state_id
+    p0_rev = engine.state.revision
+
+    # Mutate FileStateManager on disk to simulate explicit generation mismatch (P1 on disk, P0 in engine)
+    sm = FileStateManager(str(cache))
+    sm.update_state(str(mod_a))
+    sm.save(state_id="2026-08-27_P1_MISMATCH", revision=p0_rev + 1)
+
+    # get_symbol_implementation with cached engine (holding P0) against FileState on disk (holding P1)
+    sym_res = json.loads(get_symbol_implementation(repo_path=str(repo), symbol="compute_data", mode="fetch", include=["implementation"]))
+
+    assert sym_res["status"] == "stale_source"
+    assert "implementation" not in sym_res
+    assert sym_res["source_contract"]["implementation_is_complete"] is False
+    assert sym_res["state_freshness"]["workspace_sync"] == "unverified"
+    assert "generation" in sym_res["state_freshness"]["advisory_warning"].lower()
+    assert "generation" in sym_res["stale_reason"].lower()
```

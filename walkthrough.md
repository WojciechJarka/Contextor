CPA10K7F1_ENGINE_CACHE_ATOMICITY_IMPLEMENTATION

STATUS=PASS
HEAD_BEFORE=7ad5faca6e1f2d808dfb396596f04d269f073783
HEAD_AFTER=7ad5faca6e1f2d808dfb396596f04d269f073783
PRE_EDIT_LIVE_REVISION=1318
POST_EDIT_LIVE_REVISION=1326

FILES_CHANGED=
- C:\Temp\Contextor_Repo\contextor\mcp\runtime.py
- C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py
- C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py
- C:\Temp\Contextor_Repo\contextor\mcp\diagnostics.py
- C:\Temp\Contextor_Repo\contextor\mcp\tools\get_file_edit_context.py
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only; excluded from production/test diff accounting)

IMPLEMENTATION_RESULT=PASS
LOCK_IDENTITY=One canonical resolved-root threading.RLock per repository, with one small global threading.Lock only for lookup/creation; no global engine lock.
SAME_ROOT_ATOMICITY=PASS; get_or_init_engine, cache refresh, publication, diagnostics reads, remote update refresh, and engine/revision snapshot are covered by one same-root transaction.
DIFFERENT_ROOT_INDEPENDENCE=PASS; distinct canonical roots use distinct RLocks and proceed concurrently.
ANALYSIS_REFRESH_RESULT=PASS; _execute_analysis_job owns only the project cache-refresh scope, preserves _analysis_job_lock and worker/persistence boundaries, and nested get_or_init_engine is re-entrant.
UPDATE_FILE_REFRESH_RESULT=PASS; save_engine_state remains outside the cache transaction; coherent revision/state-manager publication and remote refresh are transaction-scoped.
DIAGNOSTICS_READER_RESULT=PASS; state=None reads use _cached_engine and do not hydrate.
FILE_EDIT_CONTEXT_SNAPSHOT_RESULT=PASS; minimal mode captures engine and live revision through _get_or_init_engine_snapshot and returns the captured revision.
NEW_TESTS=
- tests/test_mcp_regressions.py::test_same_root_double_hydration_is_serialized
- tests/test_mcp_regressions.py::test_different_root_cache_transactions_are_independent
- tests/test_mcp_regressions.py::test_analysis_refresh_transaction_excludes_same_root_reader
- tests/test_mcp_regressions.py::test_analysis_refresh_transaction_is_reentrant
- tests/test_mcp_regressions.py::test_update_file_refresh_uses_same_root_transaction
- tests/test_mcp_regressions.py::test_file_edit_context_binds_engine_and_revision_atomically

TARGETED_TESTS=PASS; 24 passed, 1 warning
TARGETED_TEST_COMMAND=Focused named regression list from the CPA10K7F1 contract across tests/test_mcp_regressions.py, tests/test_full_analysis_coordination.py, tests/test_mcp_incremental_hydration.py, tests/test_h3a_workspace_canonical_freshness.py, tests/mcp/tools/test_compact_evidence_contract.py, tests/test_mcp_split_s2e.py, and tests/mcp/tools/test_analysis_status_concurrency.py.
FOCUSED_FILE_TEST=PASS; tests/test_mcp_regressions.py: 89 passed, 1 warning
PY_COMPILE=PASS; all five modified production modules and tests/test_mcp_regressions.py compiled successfully.
CONTEXTOR_POST_EDIT=PASS; desktop_watcher confirmed runtime.py revision 1319, analysis_jobs.py revision 1320, update_file.py revision 1321, diagnostics.py revision 1322, get_file_edit_context.py revision 1323, and test_mcp_regressions.py revision 1324. Later watcher events 1325-1326 were UNCHANGED. At revision 1326, workspace_sync=verified, syntax_errors=0, name_collisions=0, cycles=0, and attention_required=false. Modified symbols resolved with fresh canonical state; blast radius remained within approved scope.
MCP_SERVER_RESTART_REQUIRED=YES
DESKTOP_RUNTIME_RESTART_REQUIRED=NO
FULL_SUITE_RUN=NO

EVIDENCE_DISCIPLINE=
- DIRECT_EVIDENCE: exact watcher revisions 1319-1326; Contextor symbol resolution at canonical revision 1326; Contextor diagnostics fresh with zero syntax errors, name collisions, and cycles; focused pytest results.
- CODE_PATH_PROVED: repository-keyed RLock transaction wraps the complete get_or_init_engine path; project cache refresh is transaction-scoped; update_file persistence and remote refresh follow the approved boundaries; diagnostics and minimal edit-context readers use the new helpers.
- CONTRACT_PROVED: only the five approved production files and one approved test file changed; no manual update_file call, restart, process termination, teardown investigation, or full pytest was performed.
- INFERENCE: restart requirement is derived from changed MCP server source and the contract; the agent did not restart the server.
- UNKNOWN: runtime behavior after MCP server restart remains unverified because restart is explicitly out of scope.

FULL_DIFFS=BEGIN
```diff
diff --git a/contextor/mcp/analysis_jobs.py b/contextor/mcp/analysis_jobs.py
index 84412c9..f340f5d 100644
--- a/contextor/mcp/analysis_jobs.py
+++ b/contextor/mcp/analysis_jobs.py
@@ -339 +338,0 @@ async def _execute_analysis_job(
-            cache_key = str(root)
@@ -356,16 +355,2 @@ async def _execute_analysis_job(
-            if pub_status == "success" and pub_rev is not None:
-                mcp_runtime._live_engines.pop(cache_key, None)
-                mcp_runtime._live_engine_revisions.pop(cache_key, None)
-                engine = mcp_runtime.get_or_init_engine(root)
-
-                if engine is None:
-                    mcp_runtime._live_engines.pop(cache_key, None)
-                    mcp_runtime._live_engine_revisions.pop(cache_key, None)
-                    raise RuntimeError(
-                        "Analysis completed and LIVE publication returned, "
-                        "but canonical state could not be loaded."
-                    )
-
-                engine_state = getattr(engine, "state", None)
-                canonical_rev = getattr(engine_state, "revision", None)
-                if canonical_rev is None:
+            with mcp_runtime._engine_cache_transaction(root) as cache_key:
+                if pub_status == "success" and pub_rev is not None:
@@ -374,7 +359,31 @@ async def _execute_analysis_job(
-                    raise RuntimeError(
-                        "Canonical state loaded after analysis without a revision."
-                    )
-
-                canonical_rev = int(canonical_rev)
-                published_rev = int(pub_rev)
-                if canonical_rev != published_rev:
+                    engine = mcp_runtime.get_or_init_engine(root)
+
+                    if engine is None:
+                        mcp_runtime._live_engines.pop(cache_key, None)
+                        mcp_runtime._live_engine_revisions.pop(cache_key, None)
+                        raise RuntimeError(
+                            "Analysis completed and LIVE publication returned, "
+                            "but canonical state could not be loaded."
+                        )
+
+                    engine_state = getattr(engine, "state", None)
+                    canonical_rev = getattr(engine_state, "revision", None)
+                    if canonical_rev is None:
+                        mcp_runtime._live_engines.pop(cache_key, None)
+                        mcp_runtime._live_engine_revisions.pop(cache_key, None)
+                        raise RuntimeError(
+                            "Canonical state loaded after analysis without a revision."
+                        )
+
+                    canonical_rev = int(canonical_rev)
+                    published_rev = int(pub_rev)
+                    if canonical_rev != published_rev:
+                        mcp_runtime._live_engines.pop(cache_key, None)
+                        mcp_runtime._live_engine_revisions.pop(cache_key, None)
+                        raise RuntimeError(
+                            "Canonical revision mismatch after full analysis: "
+                            f"loaded={canonical_rev}, published={published_rev}."
+                        )
+
+                    mcp_runtime._live_engine_revisions[cache_key] = canonical_rev
+                else:
@@ -383,9 +391,0 @@ async def _execute_analysis_job(
-                    raise RuntimeError(
-                        "Canonical revision mismatch after full analysis: "
-                        f"loaded={canonical_rev}, published={published_rev}."
-                    )
-
-                mcp_runtime._live_engine_revisions[cache_key] = canonical_rev
-            else:
-                mcp_runtime._live_engines.pop(cache_key, None)
-                mcp_runtime._live_engine_revisions.pop(cache_key, None)
diff --git a/contextor/mcp/diagnostics.py b/contextor/mcp/diagnostics.py
index ec68eed..cc902b3 100644
--- a/contextor/mcp/diagnostics.py
+++ b/contextor/mcp/diagnostics.py
@@ -163 +163 @@ def diagnostics_summary(root: Path, state: Any = None) -> dict[str, Any]:
-        engine = mcp_runtime._live_engines.get(str(root))
+        engine = mcp_runtime._cached_engine(root)
diff --git a/contextor/mcp/runtime.py b/contextor/mcp/runtime.py
index 6a80e69..862923d 100644
--- a/contextor/mcp/runtime.py
+++ b/contextor/mcp/runtime.py
@@ -1,0 +2 @@ from collections.abc import Mapping
+from contextlib import contextmanager
@@ -4 +5,2 @@ from pathlib import Path
-from typing import Any
+import threading
+from typing import Any, Iterator
@@ -15,0 +18,2 @@ _live_journal_revisions: dict[str, int] = {}
+_engine_cache_locks_guard = threading.Lock()
+_engine_cache_locks: dict[str, Any] = {}
@@ -104,0 +109,29 @@ def publish_live_status(root: Path, message: str) -> None:
+def _engine_cache_key(root: Path | str) -> str:
+    return str(Path(root).expanduser().resolve())
+
+
+@contextmanager
+def _engine_cache_transaction(root: Path | str) -> Iterator[str]:
+    root_key = _engine_cache_key(root)
+    with _engine_cache_locks_guard:
+        lock = _engine_cache_locks.get(root_key)
+        if lock is None:
+            lock = threading.RLock()
+            _engine_cache_locks[root_key] = lock
+    with lock:
+        yield root_key
+
+
+def _cached_engine(root: Path | str):
+    with _engine_cache_transaction(root) as root_key:
+        return _live_engines.get(root_key)
+
+
+def _get_or_init_engine_snapshot(root: Path | str):
+    root = Path(root).expanduser().resolve()
+    with _engine_cache_transaction(root) as root_key:
+        engine = get_or_init_engine(root)
+        revision = _live_engine_revisions.get(root_key)
+        return engine, revision
+
+
@@ -110,18 +143,3 @@ def get_or_init_engine(root: Path):
-    from contextor.core.live_state import connect
-
-    root_key = str(root)
-    engine = _live_engines.get(root_key)
-    client = connect(root)
-    if client:
-        session_id = f"{client.endpoint.host}:{client.endpoint.port}:{client.endpoint.authkey_hex}"
-        cached_session_id = _live_sessions.get(root_key)
-        cached_journal_rev = _live_journal_revisions.get(root_key)
-
-        remote = client.ping()
-        journal_revision = int(remote.get("revision", 0))
-
-        needs_refresh = (
-            engine is None
-            or session_id != cached_session_id
-            or journal_revision != cached_journal_rev
-        )
+    root = Path(root).expanduser().resolve()
+    with _engine_cache_transaction(root) as root_key:
+        from contextor.core.live_state import connect
@@ -129,31 +147,87 @@ def get_or_init_engine(root: Path):
-        if needs_refresh:
-            snapshot = client.snapshot()
-            state = snapshot.get("state")
-            if state is not None:
-                from contextor.core.analysis.state_manager import FileStateManager
-                from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
-                from contextor.core.live_state import read_metadata
-                from contextor.core.paths import repo_cache_dir
-                from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
-
-                setattr(state, "provenance", "live")
-                pub_rev = getattr(state, "revision", None)
-                sid = getattr(state, "state_id", None)
-                if pub_rev is None or not sid:
-                    cache_meta = read_metadata(repo_cache_dir(root))
-                    if pub_rev is None and cache_meta and cache_meta.revision is not None:
-                        pub_rev = int(cache_meta.revision)
-                        setattr(state, "revision", pub_rev)
-                    if not sid and cache_meta and cache_meta.state_id:
-                        sid = cache_meta.state_id
-                        setattr(state, "state_id", sid)
-
-                manager = FileStateManager(str(repo_cache_dir(root)))
-                engine = IncrementalAnalysisEngine(
-                    state,
-                    PersistentIdentityRegistry(str(root)),
-                    manager,
-                    str(root),
-                )
-                engine.provenance = "live"
-                engine.revision = pub_rev
+        engine = _live_engines.get(root_key)
+        client = connect(root)
+        if client:
+            session_id = f"{client.endpoint.host}:{client.endpoint.port}:{client.endpoint.authkey_hex}"
+            cached_session_id = _live_sessions.get(root_key)
+            cached_journal_rev = _live_journal_revisions.get(root_key)
+
+            remote = client.ping()
+            journal_revision = int(remote.get("revision", 0))
+
+            needs_refresh = (
+                engine is None
+                or session_id != cached_session_id
+                or journal_revision != cached_journal_rev
+            )
+
+            if needs_refresh:
+                snapshot = client.snapshot()
+                state = snapshot.get("state")
+                if state is not None:
+                    from contextor.core.analysis.state_manager import FileStateManager
+                    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+                    from contextor.core.live_state import read_metadata
+                    from contextor.core.paths import repo_cache_dir
+                    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+
+                    setattr(state, "provenance", "live")
+                    pub_rev = getattr(state, "revision", None)
+                    sid = getattr(state, "state_id", None)
+                    if pub_rev is None or not sid:
+                        cache_meta = read_metadata(repo_cache_dir(root))
+                        if pub_rev is None and cache_meta and cache_meta.revision is not None:
+                            pub_rev = int(cache_meta.revision)
+                            setattr(state, "revision", pub_rev)
+                        if not sid and cache_meta and cache_meta.state_id:
+                            sid = cache_meta.state_id
+                            setattr(state, "state_id", sid)
+
+                    manager = FileStateManager(str(repo_cache_dir(root)))
+                    engine = IncrementalAnalysisEngine(
+                        state,
+                        PersistentIdentityRegistry(str(root)),
+                        manager,
+                        str(root),
+                    )
+                    engine.provenance = "live"
+                    engine.revision = pub_rev
+                    _live_engines[root_key] = engine
+                    _live_sessions[root_key] = session_id
+                    _live_journal_revisions[root_key] = journal_revision
+                    if pub_rev is not None:
+                        _live_engine_revisions[root_key] = pub_rev
+                    else:
+                        _live_engine_revisions.pop(root_key, None)
+                    _live_engine_provenance[root_key] = "live"
+        else:
+            _live_sessions.pop(root_key, None)
+            _live_journal_revisions.pop(root_key, None)
+        if not engine:
+            from contextor.core.analysis.state_manager import load_engine_state, FileStateManager
+            from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+            from contextor.core.live_state import migrate_legacy_snapshot, read_metadata
+            from contextor.core.repository_identity import read_repository_identity
+            from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+
+            identity = read_repository_identity(root)
+            if identity is None:
+                return None
+            cache_dir = str(migrate_legacy_snapshot(root))
+            metadata = read_metadata(cache_dir)
+            state = load_engine_state(
+                cache_dir,
+                metadata.state_id if metadata else "",
+                expected_repo_id=identity.repo_id,
+                expected_root_path=identity.root_path,
+            )
+            if state:
+                rev = int(metadata.revision) if metadata and metadata.revision is not None else None
+                sid = metadata.state_id if metadata else ""
+                setattr(state, "provenance", "snapshot")
+                setattr(state, "revision", rev)
+                setattr(state, "state_id", sid)
+                state_mgr = FileStateManager(cache_dir)
+                registry = PersistentIdentityRegistry(str(root))
+                engine = IncrementalAnalysisEngine(state, registry, state_mgr, str(root))
+                engine.provenance = "snapshot"
+                engine.revision = rev
@@ -161,4 +235,3 @@ def get_or_init_engine(root: Path):
-                _live_sessions[root_key] = session_id
-                _live_journal_revisions[root_key] = journal_revision
-                if pub_rev is not None:
-                    _live_engine_revisions[root_key] = pub_rev
+                _live_engine_provenance[root_key] = "snapshot"
+                if rev is not None:
+                    _live_engine_revisions[root_key] = rev
@@ -167,37 +239,0 @@ def get_or_init_engine(root: Path):
-                _live_engine_provenance[root_key] = "live"
-    else:
-        _live_sessions.pop(root_key, None)
-        _live_journal_revisions.pop(root_key, None)
-    if not engine:
-        from contextor.core.analysis.state_manager import load_engine_state, FileStateManager
-        from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
-        from contextor.core.live_state import migrate_legacy_snapshot, read_metadata
-        from contextor.core.repository_identity import read_repository_identity
-        from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
-
-        identity = read_repository_identity(root)
-        if identity is None:
-            return None
-        cache_dir = str(migrate_legacy_snapshot(root))
-        metadata = read_metadata(cache_dir)
-        state = load_engine_state(
-            cache_dir,
-            metadata.state_id if metadata else "",
-            expected_repo_id=identity.repo_id,
-            expected_root_path=identity.root_path,
-        )
-        if state:
-            rev = int(metadata.revision) if metadata and metadata.revision is not None else None
-            sid = metadata.state_id if metadata else ""
-            setattr(state, "provenance", "snapshot")
-            setattr(state, "revision", rev)
-            setattr(state, "state_id", sid)
-            state_mgr = FileStateManager(cache_dir)
-            registry = PersistentIdentityRegistry(str(root))
-            engine = IncrementalAnalysisEngine(state, registry, state_mgr, str(root))
-            engine.provenance = "snapshot"
-            engine.revision = rev
-            _live_engines[str(root)] = engine
-            _live_engine_provenance[str(root)] = "snapshot"
-            if rev is not None:
-                _live_engine_revisions[str(root)] = rev
@@ -205,8 +241,6 @@ def get_or_init_engine(root: Path):
-                _live_engine_revisions.pop(str(root), None)
-        else:
-            _live_engines.pop(str(root), None)
-            _live_engine_revisions.pop(str(root), None)
-            _live_engine_provenance.pop(str(root), None)
-            _live_sessions.pop(str(root), None)
-            _live_journal_revisions.pop(str(root), None)
-    return engine
+                _live_engines.pop(root_key, None)
+                _live_engine_revisions.pop(root_key, None)
+                _live_engine_provenance.pop(root_key, None)
+                _live_sessions.pop(root_key, None)
+                _live_journal_revisions.pop(root_key, None)
+        return engine
diff --git a/contextor/mcp/tools/get_file_edit_context.py b/contextor/mcp/tools/get_file_edit_context.py
index 675e896..860d776 100644
--- a/contextor/mcp/tools/get_file_edit_context.py
+++ b/contextor/mcp/tools/get_file_edit_context.py
@@ -94 +94,5 @@ def get_file_edit_context(
-    minimal_engine = mcp_runtime.get_or_init_engine(root) if mode == "minimal" else None
+    if mode == "minimal":
+        minimal_engine, minimal_live_revision = mcp_runtime._get_or_init_engine_snapshot(root)
+    else:
+        minimal_engine = None
+        minimal_live_revision = None
@@ -390 +394 @@ def get_file_edit_context(
-            live_revision = mcp_runtime._live_engine_revisions.get(str(root)) if engine else None
+            live_revision = minimal_live_revision if engine is not None else None
diff --git a/contextor/mcp/tools/update_file.py b/contextor/mcp/tools/update_file.py
index 58596a4..86f3c46 100644
--- a/contextor/mcp/tools/update_file.py
+++ b/contextor/mcp/tools/update_file.py
@@ -92,10 +92,11 @@ def _persist_live_engine(root: Path, engine) -> bool:
-        engine.revision = new_rev
-        if hasattr(engine.state, "revision"):
-            engine.state.revision = new_rev
-        mcp_runtime._live_engine_revisions[str(root)] = new_rev
-        if hasattr(engine, "state_manager") and engine.state_manager:
-            engine.state_manager.revision = new_rev
-            if hasattr(engine.state_manager, "save"):
-                engine.state_manager.save(
-                    getattr(engine.state_manager, "state_id", ""), revision=new_rev
-                )
+        with mcp_runtime._engine_cache_transaction(root) as root_key:
+            engine.revision = new_rev
+            if hasattr(engine.state, "revision"):
+                engine.state.revision = new_rev
+            mcp_runtime._live_engine_revisions[root_key] = new_rev
+            if hasattr(engine, "state_manager") and engine.state_manager:
+                engine.state_manager.revision = new_rev
+                if hasattr(engine.state_manager, "save"):
+                    engine.state_manager.save(
+                        getattr(engine.state_manager, "state_id", ""), revision=new_rev
+                    )
@@ -217,2 +218,3 @@ def update_file(
-            mcp_runtime._live_engine_revisions[str(root)] = int(remote["revision"]) - 1
-            engine = mcp_runtime.get_or_init_engine(root)
+            with mcp_runtime._engine_cache_transaction(root) as root_key:
+                mcp_runtime._live_engine_revisions[root_key] = int(remote["revision"]) - 1
+                engine = mcp_runtime.get_or_init_engine(root)
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index 50206b8..5f1e5ec 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -79,0 +80,420 @@ def _patch_empty_registries(monkeypatch):
+def test_same_root_double_hydration_is_serialized(tmp_path, monkeypatch):
+    root = tmp_path / "repo"
+    root.mkdir()
+    root_key = str(root.resolve())
+    state = SimpleNamespace(revision=7, state_id="state-7")
+    builds = []
+    first_build_entered = threading.Event()
+    release_first_build = threading.Event()
+    second_get_entered = threading.Event()
+    results = []
+    errors = []
+    second_thread_id = [None]
+
+    class FakeClient:
+        endpoint = SimpleNamespace(host="127.0.0.1", port=9000, authkey_hex="auth")
+
+        def ping(self):
+            return {"revision": 3}
+
+        def snapshot(self):
+            return {"state": state}
+
+    class FakeEngine:
+        def __init__(self, loaded_state, *_args):
+            builds.append(self)
+            if len(builds) == 1:
+                first_build_entered.set()
+                release_first_build.wait()
+            self.state = loaded_state
+            self.revision = loaded_state.revision
+
+    class FakeStateManager:
+        def __init__(self, *_args):
+            pass
+
+    class FakeRegistry:
+        def __init__(self, *_args):
+            pass
+
+    import contextor.core.analysis.incremental_engine as core_incremental_engine
+    import contextor.core.analysis.state_manager as core_state_manager
+    import contextor.core.live_state as core_live_state
+    import contextor.core.paths as core_paths
+    import contextor.core.reporting_engine.persistent_registry as core_registry
+
+    monkeypatch.setattr(core_live_state, "connect", lambda _root: FakeClient())
+    monkeypatch.setattr(core_state_manager, "FileStateManager", FakeStateManager)
+    monkeypatch.setattr(core_incremental_engine, "IncrementalAnalysisEngine", FakeEngine)
+    monkeypatch.setattr(core_registry, "PersistentIdentityRegistry", FakeRegistry)
+    monkeypatch.setattr(core_paths, "repo_cache_dir", lambda _root: root / ".cache")
+
+    real_get_or_init_engine = mcp_runtime.get_or_init_engine
+
+    def wrapped_get_or_init_engine(candidate_root):
+        if threading.get_ident() == second_thread_id[0]:
+            second_get_entered.set()
+        return real_get_or_init_engine(candidate_root)
+
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", wrapped_get_or_init_engine)
+
+    def hydrate():
+        try:
+            results.append(mcp_runtime.get_or_init_engine(root))
+        except BaseException as exc:
+            errors.append(exc)
+
+    first = threading.Thread(target=hydrate)
+    first.start()
+    assert first_build_entered.wait(timeout=2), errors
+
+    def hydrate_second():
+        second_thread_id[0] = threading.get_ident()
+        try:
+            results.append(mcp_runtime.get_or_init_engine(root))
+        except BaseException as exc:
+            errors.append(exc)
+
+    second = threading.Thread(target=hydrate_second)
+    second.start()
+    assert second_get_entered.wait(timeout=2)
+    release_first_build.set()
+    first.join(timeout=2)
+    second.join(timeout=2)
+
+    assert not first.is_alive()
+    assert not second.is_alive()
+    assert errors == []
+    assert len(builds) == 1
+    assert len(results) == 2
+    assert results[0] is results[1]
+
+
+def test_different_root_cache_transactions_are_independent(tmp_path):
+    root_a = tmp_path / "repo-a"
+    root_b = tmp_path / "repo-b"
+    root_a.mkdir()
+    root_b.mkdir()
+    first_entered = threading.Event()
+    second_entered = threading.Event()
+    release_first = threading.Event()
+
+    def hold_first_root():
+        with mcp_runtime._engine_cache_transaction(root_a):
+            first_entered.set()
+            release_first.wait()
+
+    def enter_second_root():
+        with mcp_runtime._engine_cache_transaction(root_b):
+            second_entered.set()
+
+    first = threading.Thread(target=hold_first_root)
+    second = threading.Thread(target=enter_second_root)
+    first.start()
+    assert first_entered.wait(timeout=2)
+    second.start()
+    assert second_entered.wait(timeout=2)
+    release_first.set()
+    first.join(timeout=2)
+    second.join(timeout=2)
+    assert not first.is_alive()
+    assert not second.is_alive()
+
+
+def test_analysis_refresh_transaction_excludes_same_root_reader(tmp_path, monkeypatch):
+    from contextor.mcp import diagnostics
+
+    root = tmp_path / "repo"
+    root.mkdir()
+    root_key = str(root.resolve())
+    old_engine = SimpleNamespace(state=SimpleNamespace(revision=10))
+    new_engine = SimpleNamespace(state=SimpleNamespace(revision=11))
+    refresh_entered = threading.Event()
+    reader_started = threading.Event()
+    reader_done = threading.Event()
+    release_refresh = threading.Event()
+    reader_results = []
+    analysis_errors = []
+
+    async def fake_worker(*_args, **_kwargs):
+        return {
+            "live_publish_status": "success",
+            "live_publish_revision": 11,
+        }
+
+    def refresh_engine(_candidate_root):
+        refresh_entered.set()
+        release_refresh.wait()
+        mcp_runtime._live_engines[root_key] = new_engine
+        return new_engine
+
+    def read_summary(candidate_root):
+        reader_started.set()
+        reader_results.append(diagnostics.diagnostics_summary(candidate_root))
+        reader_done.set()
+
+    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
+    monkeypatch.setattr(analysis_jobs, "_write_analysis_job", lambda *_args: None)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", refresh_engine)
+    monkeypatch.setattr(
+        diagnostics,
+        "diagnostics_summary_for_state",
+        lambda state: {"revision": getattr(state, "revision", None)},
+    )
+    mcp_runtime._live_engines[root_key] = old_engine
+    mcp_runtime._live_engine_revisions[root_key] = 10
+
+    def run_analysis():
+        try:
+            asyncio.run(
+                analysis_jobs._execute_analysis_job(
+                    root, _project_analysis_job(root, "reader-exclusion"), None, []
+                )
+            )
+        except BaseException as exc:
+            analysis_errors.append(exc)
+
+    analysis_thread = threading.Thread(target=run_analysis)
+    reader_thread = threading.Thread(target=read_summary, args=(root,))
+    analysis_thread.start()
+    assert refresh_entered.wait(timeout=2)
+    reader_thread.start()
+    assert reader_started.wait(timeout=2)
+    assert not reader_done.wait(timeout=0.1)
+    release_refresh.set()
+    analysis_thread.join(timeout=2)
+    reader_thread.join(timeout=2)
+
+    assert not analysis_thread.is_alive()
+    assert not reader_thread.is_alive()
+    assert analysis_errors == []
+    assert reader_results == [{"revision": 11}]
+
+
+def test_analysis_refresh_transaction_is_reentrant(tmp_path, monkeypatch):
+    root = tmp_path / "repo"
+    root.mkdir()
+    root_key = str(root.resolve())
+    completed = threading.Event()
+    errors = []
+    writes = []
+    engine = SimpleNamespace(state=SimpleNamespace(revision=13))
+
+    async def fake_worker(*_args, **_kwargs):
+        return {
+            "live_publish_status": "success",
+            "live_publish_revision": 13,
+        }
+
+    def reentrant_get(candidate_root):
+        with mcp_runtime._engine_cache_transaction(candidate_root):
+            mcp_runtime._live_engines[root_key] = engine
+            return engine
+
+    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
+    monkeypatch.setattr(
+        analysis_jobs,
+        "_write_analysis_job",
+        lambda _root, payload: writes.append(payload),
+    )
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", reentrant_get)
+
+    def run_analysis():
+        try:
+            asyncio.run(
+                analysis_jobs._execute_analysis_job(
+                    root, _project_analysis_job(root, "reentrant-refresh"), None, []
+                )
+            )
+        except BaseException as exc:
+            errors.append(exc)
+        finally:
+            completed.set()
+
+    thread = threading.Thread(target=run_analysis, daemon=True)
+    thread.start()
+    assert completed.wait(timeout=2)
+    thread.join(timeout=2)
+
+    assert errors == []
+    assert writes[-1]["status"] == "completed"
+    assert mcp_runtime._live_engine_revisions[root_key] == 13
+
+
+def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
+    root = tmp_path / "repo"
+    root.mkdir()
+    target = root / "pkg" / "module.py"
+    target.parent.mkdir()
+    target.write_text("def run():\n    return 1\n", encoding="utf-8")
+    root_key = str(root.resolve())
+    old_engine = SimpleNamespace(state=SimpleNamespace(artifacts={"pkg.module": {}}))
+    new_engine = SimpleNamespace(
+        state=SimpleNamespace(artifacts={"pkg.module": {"symbols": {}}})
+    )
+    result = SimpleNamespace(
+        status="UPDATED",
+        file_path=str(target),
+        graph_state="fresh",
+        dependencies_state="fresh",
+        blast_radius_state="fresh",
+        local_metrics_state="deferred",
+        global_metrics_state="deferred",
+        artifact_consumption_state="deferred",
+        affected_modules=[],
+        delta=None,
+    )
+    refresh_entered = threading.Event()
+    release_refresh = threading.Event()
+    probe_started = threading.Event()
+    probe_entered = threading.Event()
+    update_done = threading.Event()
+    update_results = []
+    calls = []
+
+    class FakeLiveClient:
+        def update_file(self, *_args, **_kwargs):
+            return {"status": "ok", "revision": 22, "result": result}
+
+    def fake_get_or_init_engine(_root):
+        calls.append(True)
+        if len(calls) == 1:
+            return old_engine
+        refresh_entered.set()
+        release_refresh.wait()
+        return new_engine
+
+    import contextor.core.live_state as core_live_state
+
+    monkeypatch.setattr(core_live_state, "connect", lambda _root: FakeLiveClient())
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", fake_get_or_init_engine)
+    monkeypatch.setattr(
+        update_file_module,
+        "_mcp_runtime_restart_required",
+        lambda _path: False,
+    )
+
+    def run_update():
+        update_results.append(
+            json.loads(update_file_module.update_file(str(root), str(target)))
+        )
+        update_done.set()
+
+    def probe_transaction():
+        probe_started.set()
+        with mcp_runtime._engine_cache_transaction(root):
+            probe_entered.set()
+
+    update_thread = threading.Thread(target=run_update)
+    probe_thread = threading.Thread(target=probe_transaction)
+    update_thread.start()
+    assert refresh_entered.wait(timeout=2)
+    probe_thread.start()
+    assert probe_started.wait(timeout=2)
+    assert not probe_entered.wait(timeout=0.1)
+    release_refresh.set()
+    assert update_done.wait(timeout=2)
+    assert probe_entered.wait(timeout=2)
+    update_thread.join(timeout=2)
+    probe_thread.join(timeout=2)
+
+    assert not update_thread.is_alive()
+    assert not probe_thread.is_alive()
+    assert update_results[0]["status"] == "UPDATED"
+    assert update_results[0]["live_state_persisted"] is True
+    assert mcp_runtime._live_engine_revisions[root_key] == 21
+
+
+def test_file_edit_context_binds_engine_and_revision_atomically(tmp_path, monkeypatch):
+    import contextor.core.live_state as core_live_state
+    from contextor.core.domain.graph import ProjectGraph
+    import contextor.mcp.tools.get_file_edit_context as get_file_edit_context_module
+
+    root = tmp_path / "repo"
+    root.mkdir()
+    root_key = str(root.resolve())
+    engine_one = SimpleNamespace(
+        state=SimpleNamespace(
+            modules={"pkg.mod": SimpleNamespace(module_id="1/1", path="pkg/mod.py")},
+            artifacts={"pkg.mod": {"own_symbols": []}},
+            dependency_graph=ProjectGraph(hard_edges={}, soft_edges={}),
+        )
+    )
+    engine_two = SimpleNamespace(
+        state=SimpleNamespace(
+            modules={"pkg.mod": SimpleNamespace(module_id="1/1", path="pkg/mod.py")},
+            artifacts={"pkg.mod": {"own_symbols": []}},
+            dependency_graph=ProjectGraph(hard_edges={}, soft_edges={}),
+        )
+    )
+    snapshot_entered = threading.Event()
+    release_snapshot = threading.Event()
+    response_phase = threading.Event()
+    allow_response = threading.Event()
+    mutation_entered = threading.Event()
+    result_box = []
+    errors = []
+
+    def fake_get_or_init_engine(_root):
+        mcp_runtime._live_engines[root_key] = engine_one
+        mcp_runtime._live_engine_revisions[root_key] = 41
+        snapshot_entered.set()
+        release_snapshot.wait()
+        return engine_one
+
+    def mutate_after_snapshot():
+        with mcp_runtime._engine_cache_transaction(root):
+            mcp_runtime._live_engines[root_key] = engine_two
+            mcp_runtime._live_engine_revisions[root_key] = 42
+            mutation_entered.set()
+
+    def module_truth_unavailable(_state, _module_name):
+        response_phase.set()
+        allow_response.wait()
+        return None
+
+    monkeypatch.setattr(core_live_state, "connect", lambda _root: None)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", fake_get_or_init_engine)
+    monkeypatch.setattr(
+        query_helpers,
+        "read_registries",
+        lambda _root: ({"pkg.mod": "1/1"}, {"1/1": "pkg.mod"}, {}, {}),
+    )
+    monkeypatch.setattr(query_helpers, "module_truth_unavailable", module_truth_unavailable)
+    monkeypatch.setattr(
+        get_file_edit_context_module,
+        "syntax_diagnostics_for_path",
+        lambda *_args, **_kwargs: [],
+    )
+
+    probe_thread = threading.Thread(target=mutate_after_snapshot)
+    probe_thread.start()
+
+    def read_context():
+        try:
+            result_box.append(
+                json.loads(
+                    get_file_edit_context_module.get_file_edit_context(
+                        repo_path=str(root), target="pkg.mod", mode="minimal"
+                    )
+                )
+            )
+        except BaseException as exc:
+            errors.append(exc)
+
+    context_thread = threading.Thread(target=read_context)
+    context_thread.start()
+    assert snapshot_entered.wait(timeout=2)
+    release_snapshot.set()
+    assert response_phase.wait(timeout=2)
+    assert mutation_entered.wait(timeout=2)
+    allow_response.set()
+    context_thread.join(timeout=2)
+    probe_thread.join(timeout=2)
+
+    assert not context_thread.is_alive()
+    assert not probe_thread.is_alive()
+    assert errors == []
+    assert result_box[0]["live_revision"] == 41
+
+

```
FULL_DIFFS=END


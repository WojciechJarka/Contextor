# L32H2F3C — lazy fallback and canonical migration admission

## FILES_CHANGED_THIS_TASK

- `C:\Temp\Contextor_Repo\contextor\mcp\runtime.py`
- `C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py`
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py`
- `C:\Temp\Contextor_Repo\contextor\core\api\facade.py`
- `C:\Temp\Contextor_Repo\tests\test_live_state_store.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py`
- `C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py`
- `C:\Temp\Contextor_Repo\tests\test_layer_state_only_hydration.py`
- `C:\Temp\Contextor_Repo\tests\test_live_single_file_reuse.py`

`C:\Temp\Contextor_Repo\walkthrough.md` was overwritten for this report and is excluded from source/test changed files.

## SOURCE_GATE

DIRECT_EVIDENCE: Contextor MCP was used first, including deferred `get_symbol_implementation`, `get_artifact_blast_radius`, `get_mcp_documentation`, and `get_live_events`. Complete pre-edit implementations returned `workspace_sync=verified` at LIVE revision 266. Exact disk anchors and the clean pre-edit source/test worktree were confirmed. The complete authorized paths and intended changes were written to this report before production edits. No broad analysis or manual `update_file` was run.

## RED_RESULTS

Before production edits, the focused two-node RED gate failed as intended (2 failed): `test_migration_does_not_enter_snapshot_write_while_full_analysis_lease_is_held` observed migration entering `save_snapshot` while another process held `full_analysis.lock`; revised `test_legacy_migration_writer_admission_precedes_mcp_cache_lock` observed migration callback without the full-analysis lease and only the initial cache acquisition. These failures established the actual missing admission and ordering boundaries.

## LAZY_FALLBACK_IMPLEMENTATION

CODE_PATH_PROVED: `migrate_legacy_snapshot` retains metadata/legacy fast paths, then acquires `full_analysis.lock` before the migration write and recursively rechecks under admission. `_lease_held=True` is forwarded only through verified coordinated facade/hydration paths and the admitted MCP fallback. MCP getter first probes under cache RLock, releases it on migration-needed, takes the full-analysis lease, then reacquires cache RLock and rechecks LIVE/cache before migration. The existing LIVE hydration and five cache-map updates remain in the single locked helper.

## WARM_CACHE_NO_WRITE

CONTRACT_PROVED by targeted test with a valid legacy snapshot and absent target metadata: warm cached engine returns without migration callback or full-analysis admission.

## HEALTHY_LIVE_NO_WRITE

CONTRACT_PROVED by targeted test with a valid legacy snapshot and absent target metadata: usable LIVE hydration returns without migration callback or full-analysis admission.

## COLD_FALLBACK_RECHECK

CONTRACT_PROVED: a different thread installs a usable cached engine while the cold getter waits for admission; the second locked probe returns that engine without migration. Missing repository identity returns before admission/migration. Missing legacy snapshot produces no migration snapshot write. Three concurrent cold getters commit one initial migration and return one consistent cached engine/revision pair.

## FULL_LEASE_BEFORE_CACHE_MIGRATION

CODE_PATH_PROVED and TEST_PROVED: revised Race C observes an initial read-only cache probe, then full-analysis admission, then post-admission cache acquisition and migration callback with both locks held. Migration is not called while waiting for admission under cache RLock.

## ALREADY_COORDINATED_FACADE

CODE_PATH_PROVED: the three migration-bearing facade analysis bodies pass `_lease_held=True` to authoritative resolution, and single-file full hydration forwards it. `hydrate_repository_engine` forwards it to the resolver. Focused direct migration test holds a scoped full-analysis lease and confirms `_lease_held=True` migrates without a recursive lease acquisition. Existing scoped facade lease tests pass. Production `analyze_project` callers were verified through the existing full-analysis coordinator; direct test calls are not proof of production admission.

## INDEPENDENT_MIGRATION

TEST_PROVED: direct `migrate_legacy_snapshot` Race A is GREEN with real cross-process OS lock contention. F3B generation/FileState metadata parity and migration failure rollback tests remain GREEN.

## ALL_THREE_NESTED_CALLERS

CODE_PATH_PROVED: `_get_or_init_engine_snapshot` defers cold migration beyond its outer cache transaction and reacquires for the current pair. Analysis-job successful publication invalidates within its original cache transaction, defers cold migration beyond it, then validates the current cached engine/revision using one shared validator. Direct LIVE update retains the remote revision-minus-one warm refresh, clears the transient revision on a cold sentinel, exits the outer cache transaction, hydrates once, and fails closed on missing/mismatched committed generation. Focused cold-path tests verify both analysis-job and direct-update lock depth; the direct remote mutation occurs once.

## ENGINE_REVISION_ATOMICITY

TEST_PROVED: existing warm file-edit-context pair test remains GREEN. New cold concurrent pair test confirms the snapshot returns the current newer engine with its matching revision, rather than an older returned engine with a later revision. Three concurrent cold getters return the same cached engine/revision.

## RACE_A_RESULT

GREEN: independent migration does not enter snapshot write while another process holds `full_analysis.lock`.

## RACE_B_RESULT

GREEN: legacy FileState cannot overwrite a newer committed generation; related migration preservation and failure tests pass.

## RACE_C_RESULT

GREEN: corrected two-phase lock order and callback-under-both-locks assertions pass. The obsolete lease-before-every-cache-probe assertion was removed.

## CROSS_PROCESS_LOCK_EXCLUSION

TEST_PROVED: while another process holds `full_analysis.lock` and cold MCP getter waits for admission, a second same-root thread acquires/releases the MCP cache RLock within the bounded interval. This uses actual OS lock contention, not event ordering alone.

## TARGETED_GREEN_RESULTS

Final selected focused gate across all six authorized test files: **45 passed, 0 failed**. Includes the RED/now GREEN races, warm/healthy-LIVE no-write, cold recheck, missing identity/legacy, concurrent cold getters, cold pair, nested analysis/update callers, FileState parity, scoped facade, and existing warm revision/reader-exclusion tests. An intermediate new cross-process test initially failed because its legacy fixture was a plain dict passed to engine hydration; test-only loader fixture was corrected and the test passed. An earlier selected run exposed one-argument test mocks rejecting the newly passed private keyword; only affected mocks were adapted, and the selected gate passed. No full repository pytest was run. `py_compile` on all six production files: PASS. `git diff --check -- contextor tests`: PASS (exit 0; Git printed only line-ending normalization warnings).

## SOURCE_SYNC

DIRECT_EVIDENCE: post-edit Contextor fetched complete current symbol implementations for the getter, locked helper, snapshot helper, analysis job, update tool, migration, both hydration functions, and facade body. Each returned `implementation_is_complete=true` and `workspace_sync=verified` at revision 284. Post-edit getter and migration blast-radius calls returned complete direct consumer lists (23 and 6 respectively) with `workspace_sync=verified`; diagnostics reported `cycles.count=0`, syntax errors 0. This certifies indexed source equality, not imported-code reload.

## LIVE_REVISION_BEFORE_AFTER

Before: 266. After: 284. `get_live_events(after_revision=266)` and continuation show desktop_watcher source/test events and continuous revision history. Latest `resync_required=false`; revision 284 was an `UNCHANGED` watcher event after the final runtime whitespace correction. No manual LIVE mutation or process restart occurred.

## REMAINING_STARTUP_BACKFILL_AND_PUBLISH_RISKS

UNKNOWN / OUT OF SCOPE: LIVE startup/backfill and GUI migration callers retain the default coordinated migration path but were not changed or runtime-certified here. This gate does not establish serving-process imported-code reload. Full repository suite was deliberately not run. Direct calls to `ContextorFacade.analyze_project` outside the confirmed production full-analysis coordinator are an internal convention boundary, not newly authorized writer admission.

## RESTART_REQUIRED

YES for any serving MCP/Desktop/LIVE process that imported modified modules before this patch. No restart was performed. Fresh pytest processes and Contextor source indexing do not prove existing processes reloaded these modules.

## FINAL_VERDICT

**L32H2F3C TARGETED PASS; L32H FINAL PASS NOT CLAIMED.** The focused code/test/source-sync gates passed. Runtime serving-process certification and out-of-scope startup/backfill/publish audit remain separate.

## FULL_DIFFS_FOR_ALL_CHANGED_FILES

### `C:\Temp\Contextor_Repo\contextor\mcp\runtime.py`

```diff
diff --git a/contextor/mcp/runtime.py b/contextor/mcp/runtime.py
index dee186a..edbc74f 100644
--- a/contextor/mcp/runtime.py
+++ b/contextor/mcp/runtime.py
@@ -12,6 +12,7 @@ from contextor.core.lineage_query.live_query import (
 
 
 _live_engines: dict[str, Any] = {}
+_MIGRATION_NEEDED = object()
 _live_engine_revisions: dict[str, int] = {}
 _live_engine_provenance: dict[str, str] = {}
 _live_sessions: dict[str, str] = {}
@@ -303,117 +304,169 @@ def _cached_engine(root: Path | str):
 def _get_or_init_engine_snapshot(root: Path | str):
     root = Path(root).expanduser().resolve()
     with _engine_cache_transaction(root) as root_key:
-        engine = get_or_init_engine(root)
-        revision = _live_engine_revisions.get(root_key)
-        return engine, revision
+        engine = get_or_init_engine(root, _defer_migration=True)
+        if engine is not _MIGRATION_NEEDED:
+            revision = _live_engine_revisions.get(root_key)
+            return engine, revision
 
-
-def get_or_init_engine(root: Path):
-    """
-    Returns the live engine from RAM. If absent, HYDRATES from the .contextor cache.
-    Does NOT silently trigger analyze_project.
-    """
-    root = Path(root).expanduser().resolve()
+    get_or_init_engine(root)
     with _engine_cache_transaction(root) as root_key:
-        from contextor.core.live_state import connect
+        return _live_engines.get(root_key), _live_engine_revisions.get(root_key)
 
-        engine = _live_engines.get(root_key)
-        client = connect(root)
-        if client:
-            session_id = f"{client.endpoint.host}:{client.endpoint.port}:{client.endpoint.authkey_hex}"
-            cached_session_id = _live_sessions.get(root_key)
-            cached_journal_rev = _live_journal_revisions.get(root_key)
-
-            remote = client.ping()
-            journal_revision = int(remote.get("revision", 0))
-
-            needs_refresh = (
-                engine is None
-                or session_id != cached_session_id
-                or journal_revision != cached_journal_rev
-            )
 
-            if needs_refresh:
-                snapshot = client.snapshot()
-                state = snapshot.get("state")
-                if state is not None:
-                    from contextor.core.analysis.state_manager import FileStateManager
-                    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
-                    from contextor.core.live_state import read_metadata
-                    from contextor.core.paths import repo_cache_dir
-                    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
-
-                    setattr(state, "provenance", "live")
-                    pub_rev = getattr(state, "revision", None)
-                    sid = getattr(state, "state_id", None)
-                    if pub_rev is None or not sid:
-                        cache_meta = read_metadata(repo_cache_dir(root))
-                        if pub_rev is None and cache_meta and cache_meta.revision is not None:
-                            pub_rev = int(cache_meta.revision)
-                            setattr(state, "revision", pub_rev)
-                        if not sid and cache_meta and cache_meta.state_id:
-                            sid = cache_meta.state_id
-                            setattr(state, "state_id", sid)
-
-                    manager = FileStateManager(str(repo_cache_dir(root)))
-                    engine = IncrementalAnalysisEngine(
-                        state,
-                        PersistentIdentityRegistry(str(root)),
-                        manager,
-                        str(root),
-                    )
-                    engine.provenance = "live"
-                    engine.revision = pub_rev
-                    _live_engines[root_key] = engine
-                    _live_sessions[root_key] = session_id
-                    _live_journal_revisions[root_key] = journal_revision
-                    if pub_rev is not None:
-                        _live_engine_revisions[root_key] = pub_rev
-                    else:
-                        _live_engine_revisions.pop(root_key, None)
-                    _live_engine_provenance[root_key] = "live"
-        else:
-            _live_sessions.pop(root_key, None)
-            _live_journal_revisions.pop(root_key, None)
-        if not engine:
-            from contextor.core.analysis.state_manager import load_engine_state, FileStateManager
-            from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
-            from contextor.core.live_state import migrate_legacy_snapshot, read_metadata
-            from contextor.core.repository_identity import read_repository_identity
-            from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
-
-            identity = read_repository_identity(root)
-            if identity is None:
-                return None
-            cache_dir = str(migrate_legacy_snapshot(root))
-            metadata = read_metadata(cache_dir)
-            state = load_engine_state(
-                cache_dir,
-                metadata.state_id if metadata else "",
-                expected_repo_id=identity.repo_id,
-                expected_root_path=identity.root_path,
-            )
-            if state:
-                rev = int(metadata.revision) if metadata and metadata.revision is not None else None
-                sid = metadata.state_id if metadata else ""
-                setattr(state, "provenance", "snapshot")
-                setattr(state, "revision", rev)
-                setattr(state, "state_id", sid)
-                state_mgr = FileStateManager(cache_dir)
-                registry = PersistentIdentityRegistry(str(root))
-                engine = IncrementalAnalysisEngine(state, registry, state_mgr, str(root))
-                engine.provenance = "snapshot"
-                engine.revision = rev
+def _get_or_init_engine_locked(
+    root: Path,
+    root_key: str,
+    *,
+    allow_migration: bool,
+):
+    from contextor.core.live_state import connect
+
+    engine = _live_engines.get(root_key)
+    client = connect(root)
+    if client:
+        session_id = f"{client.endpoint.host}:{client.endpoint.port}:{client.endpoint.authkey_hex}"
+        cached_session_id = _live_sessions.get(root_key)
+        cached_journal_rev = _live_journal_revisions.get(root_key)
+
+        remote = client.ping()
+        journal_revision = int(remote.get("revision", 0))
+
+        needs_refresh = (
+            engine is None
+            or session_id != cached_session_id
+            or journal_revision != cached_journal_rev
+        )
+
+        if needs_refresh:
+            snapshot = client.snapshot()
+            state = snapshot.get("state")
+            if state is not None:
+                from contextor.core.analysis.state_manager import FileStateManager
+                from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+                from contextor.core.live_state import read_metadata
+                from contextor.core.paths import repo_cache_dir
+                from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+
+                setattr(state, "provenance", "live")
+                pub_rev = getattr(state, "revision", None)
+                sid = getattr(state, "state_id", None)
+                if pub_rev is None or not sid:
+                    cache_meta = read_metadata(repo_cache_dir(root))
+                    if pub_rev is None and cache_meta and cache_meta.revision is not None:
+                        pub_rev = int(cache_meta.revision)
+                        setattr(state, "revision", pub_rev)
+                    if not sid and cache_meta and cache_meta.state_id:
+                        sid = cache_meta.state_id
+                        setattr(state, "state_id", sid)
+
+                manager = FileStateManager(str(repo_cache_dir(root)))
+                engine = IncrementalAnalysisEngine(
+                    state,
+                    PersistentIdentityRegistry(str(root)),
+                    manager,
+                    str(root),
+                )
+                engine.provenance = "live"
+                engine.revision = pub_rev
                 _live_engines[root_key] = engine
-                _live_engine_provenance[root_key] = "snapshot"
-                if rev is not None:
-                    _live_engine_revisions[root_key] = rev
+                _live_sessions[root_key] = session_id
+                _live_journal_revisions[root_key] = journal_revision
+                if pub_rev is not None:
+                    _live_engine_revisions[root_key] = pub_rev
                 else:
                     _live_engine_revisions.pop(root_key, None)
+                _live_engine_provenance[root_key] = "live"
+    else:
+        _live_sessions.pop(root_key, None)
+        _live_journal_revisions.pop(root_key, None)
+    if not engine:
+        from contextor.core.analysis.state_manager import load_engine_state, FileStateManager
+        from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+        from contextor.core.live_state import migrate_legacy_snapshot, read_metadata
+        from contextor.core.repository_identity import read_repository_identity
+        from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+
+        identity = read_repository_identity(root)
+        if identity is None:
+            return None
+        from contextor.core.paths import repo_cache_dir
+
+        cache_dir = str(repo_cache_dir(root))
+        if read_metadata(cache_dir) is None:
+            if not allow_migration:
+                return _MIGRATION_NEEDED
+            migrate_legacy_snapshot(root, _lease_held=True)
+        metadata = read_metadata(cache_dir)
+        state = load_engine_state(
+            cache_dir,
+            metadata.state_id if metadata else "",
+            expected_repo_id=identity.repo_id,
+            expected_root_path=identity.root_path,
+        )
+        if state:
+            rev = int(metadata.revision) if metadata and metadata.revision is not None else None
+            sid = metadata.state_id if metadata else ""
+            setattr(state, "provenance", "snapshot")
+            setattr(state, "revision", rev)
+            setattr(state, "state_id", sid)
+            state_mgr = FileStateManager(cache_dir)
+            registry = PersistentIdentityRegistry(str(root))
+            engine = IncrementalAnalysisEngine(state, registry, state_mgr, str(root))
+            engine.provenance = "snapshot"
+            engine.revision = rev
+            _live_engines[root_key] = engine
+            _live_engine_provenance[root_key] = "snapshot"
+            if rev is not None:
+                _live_engine_revisions[root_key] = rev
             else:
-                _live_engines.pop(root_key, None)
                 _live_engine_revisions.pop(root_key, None)
-                _live_engine_provenance.pop(root_key, None)
-                _live_sessions.pop(root_key, None)
-                _live_journal_revisions.pop(root_key, None)
-        return engine
+        else:
+            _live_engines.pop(root_key, None)
+            _live_engine_revisions.pop(root_key, None)
+            _live_engine_provenance.pop(root_key, None)
+            _live_sessions.pop(root_key, None)
+            _live_journal_revisions.pop(root_key, None)
+    return engine
+
+
+def get_or_init_engine(
+    root: Path,
+    *,
+    _defer_migration: bool = False,
+):
+    """Return a LIVE or snapshot engine without triggering full analysis."""
+    root = Path(root).expanduser().resolve()
+
+    with _engine_cache_transaction(root) as root_key:
+        result = _get_or_init_engine_locked(
+            root,
+            root_key,
+            allow_migration=False,
+        )
+        if result is not _MIGRATION_NEEDED:
+            return result
+
+    if _defer_migration:
+        return _MIGRATION_NEEDED
+
+    from contextor.core.analysis.full_analysis_lease import (
+        acquire_full_analysis,
+        release_full_analysis,
+    )
+
+    lease = acquire_full_analysis(
+        root,
+        owner="mcp_legacy_snapshot_hydration",
+        writer_kind="full_analysis",
+        timeout=10.0,
+    )
+    try:
+        with _engine_cache_transaction(root) as root_key:
+            return _get_or_init_engine_locked(
+                root,
+                root_key,
+                allow_migration=True,
+            )
+    finally:
+        release_full_analysis(lease)
```

### `C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py`

```diff
diff --git a/contextor/mcp/analysis_jobs.py b/contextor/mcp/analysis_jobs.py
index 26fd745..b4ccc78 100644
--- a/contextor/mcp/analysis_jobs.py
+++ b/contextor/mcp/analysis_jobs.py
@@ -331,6 +331,36 @@ async def _execute_analysis_job(
         job = {**job, "message": str(message)}
         persist_job("progress")
 
+    def verify_canonical_engine(cache_key: str, engine: object, published_rev: object) -> None:
+        if engine is None:
+            mcp_runtime._live_engines.pop(cache_key, None)
+            mcp_runtime._live_engine_revisions.pop(cache_key, None)
+            raise RuntimeError(
+                "Analysis completed and LIVE publication returned, "
+                "but canonical state could not be loaded."
+            )
+
+        engine_state = getattr(engine, "state", None)
+        canonical_rev = getattr(engine_state, "revision", None)
+        if canonical_rev is None:
+            mcp_runtime._live_engines.pop(cache_key, None)
+            mcp_runtime._live_engine_revisions.pop(cache_key, None)
+            raise RuntimeError(
+                "Canonical state loaded after analysis without a revision."
+            )
+
+        canonical_rev = int(canonical_rev)
+        published_rev = int(published_rev)
+        if canonical_rev != published_rev:
+            mcp_runtime._live_engines.pop(cache_key, None)
+            mcp_runtime._live_engine_revisions.pop(cache_key, None)
+            raise RuntimeError(
+                "Canonical revision mismatch after full analysis: "
+                f"loaded={canonical_rev}, published={published_rev}."
+            )
+
+        mcp_runtime._live_engine_revisions[cache_key] = canonical_rev
+
     try:
         analysis_outcome = await _run_analysis_worker(
             str(job["operation"]), root, target, exclude_paths, log=job_log
@@ -352,43 +382,25 @@ async def _execute_analysis_job(
                 "live_publish_warning": pub_warn,
             }
 
+            cold_migration = False
             with mcp_runtime._engine_cache_transaction(root) as cache_key:
                 if pub_status == "success" and pub_rev is not None:
                     mcp_runtime._live_engines.pop(cache_key, None)
                     mcp_runtime._live_engine_revisions.pop(cache_key, None)
-                    engine = mcp_runtime.get_or_init_engine(root)
-
-                    if engine is None:
-                        mcp_runtime._live_engines.pop(cache_key, None)
-                        mcp_runtime._live_engine_revisions.pop(cache_key, None)
-                        raise RuntimeError(
-                            "Analysis completed and LIVE publication returned, "
-                            "but canonical state could not be loaded."
-                        )
-
-                    engine_state = getattr(engine, "state", None)
-                    canonical_rev = getattr(engine_state, "revision", None)
-                    if canonical_rev is None:
-                        mcp_runtime._live_engines.pop(cache_key, None)
-                        mcp_runtime._live_engine_revisions.pop(cache_key, None)
-                        raise RuntimeError(
-                            "Canonical state loaded after analysis without a revision."
-                        )
-
-                    canonical_rev = int(canonical_rev)
-                    published_rev = int(pub_rev)
-                    if canonical_rev != published_rev:
-                        mcp_runtime._live_engines.pop(cache_key, None)
-                        mcp_runtime._live_engine_revisions.pop(cache_key, None)
-                        raise RuntimeError(
-                            "Canonical revision mismatch after full analysis: "
-                            f"loaded={canonical_rev}, published={published_rev}."
-                        )
-
-                    mcp_runtime._live_engine_revisions[cache_key] = canonical_rev
+                    engine = mcp_runtime.get_or_init_engine(
+                        root, _defer_migration=True
+                    )
+                    cold_migration = engine is mcp_runtime._MIGRATION_NEEDED
+                    if not cold_migration:
+                        verify_canonical_engine(cache_key, engine, pub_rev)
                 else:
                     mcp_runtime._live_engines.pop(cache_key, None)
                     mcp_runtime._live_engine_revisions.pop(cache_key, None)
+            if cold_migration:
+                mcp_runtime.get_or_init_engine(root)
+                with mcp_runtime._engine_cache_transaction(root) as cache_key:
+                    engine = mcp_runtime._live_engines.get(cache_key)
+                    verify_canonical_engine(cache_key, engine, pub_rev)
         publish_status = job.get("live_publish_status")
         completed_message = "Analysis completed successfully."
         if job["operation"] == "project" and publish_status == "recovery_required":
```

### `C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py`

```diff
diff --git a/contextor/mcp/tools/update_file.py b/contextor/mcp/tools/update_file.py
index ee7a3dc..17b5529 100644
--- a/contextor/mcp/tools/update_file.py
+++ b/contextor/mcp/tools/update_file.py
@@ -518,9 +518,28 @@ def update_file(
             if remote.get("status") != "ok":
                 raise RuntimeError(remote.get("error", "Shared LIVE update failed."))
             res = remote["result"]
+            cold_migration = False
             with mcp_runtime._engine_cache_transaction(root) as root_key:
                 mcp_runtime._live_engine_revisions[root_key] = int(remote["revision"]) - 1
-                engine = mcp_runtime.get_or_init_engine(root)
+                engine = mcp_runtime.get_or_init_engine(
+                    root, _defer_migration=True
+                )
+                cold_migration = engine is mcp_runtime._MIGRATION_NEEDED
+                if cold_migration:
+                    mcp_runtime._live_engine_revisions.pop(root_key, None)
+            if cold_migration:
+                mcp_runtime.get_or_init_engine(root)
+                with mcp_runtime._engine_cache_transaction(root) as root_key:
+                    engine = mcp_runtime._live_engines.get(root_key)
+                    refreshed_revision = mcp_runtime._live_engine_revisions.get(root_key)
+                    if (
+                        engine is None
+                        or refreshed_revision != int(remote["revision"])
+                        or getattr(engine.state, "revision", None) != refreshed_revision
+                    ):
+                        raise RuntimeError(
+                            "Canonical LIVE state could not be hydrated at the committed revision."
+                        )
             live_state_persisted = True
         else:
             res, engine, old_artifacts, live_state_persisted = (
```

### `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py`

```diff
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 88666c8..1cc83fd 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -2416,7 +2416,11 @@ def load_snapshot(
 
 
 
-def migrate_legacy_snapshot(repo_root: str | Path) -> Path:
+def migrate_legacy_snapshot(
+    repo_root: str | Path,
+    *,
+    _lease_held: bool = False,
+) -> Path:
     """Copy a verified path-keyed snapshot into its repo-ID cache directory."""
 
     from contextor.core.paths import legacy_repo_cache_dir, repo_cache_dir
@@ -2435,6 +2439,26 @@ def migrate_legacy_snapshot(repo_root: str | Path) -> Path:
     if loaded is None:
         return target
 
+    if not _lease_held:
+        from contextor.core.analysis.full_analysis_lease import (
+            acquire_full_analysis,
+            release_full_analysis,
+        )
+
+        lease = acquire_full_analysis(
+            root,
+            owner="legacy_snapshot_migration",
+            writer_kind="full_analysis",
+            timeout=10.0,
+        )
+        try:
+            return migrate_legacy_snapshot(
+                root,
+                _lease_held=True,
+            )
+        finally:
+            release_full_analysis(lease)
+
     state, metadata = loaded
     save_snapshot(
         state,
```

### `C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py`

```diff
diff --git a/contextor/core/live_state/hydration.py b/contextor/core/live_state/hydration.py
index 3424419..674366e 100644
--- a/contextor/core/live_state/hydration.py
+++ b/contextor/core/live_state/hydration.py
@@ -28,6 +28,8 @@ class AuthoritativeRepositoryState:
 
 def resolve_authoritative_repository_state(
     repo_path: str | Path,
+    *,
+    _lease_held: bool = False,
 ) -> AuthoritativeRepositoryState | None:
     """Resolve the same LIVE-first, validated canonical state used by hydration."""
 
@@ -41,7 +43,7 @@ def resolve_authoritative_repository_state(
     if identity is None:
         return None
 
-    cache_dir = migrate_legacy_snapshot(root)
+    cache_dir = migrate_legacy_snapshot(root, _lease_held=_lease_held)
     client = connect(root)
     state = None
     revision = 0
@@ -84,6 +86,8 @@ def resolve_authoritative_repository_state(
 
 def hydrate_repository_engine(
     repo_path: str | Path,
+    *,
+    _lease_held: bool = False,
 ) -> HydratedRepositoryEngine | None:
     """Load a complete engine without triggering a repository analysis."""
 
@@ -94,7 +98,7 @@ def hydrate_repository_engine(
     )
 
     root = Path(repo_path).resolve()
-    resolved = resolve_authoritative_repository_state(root)
+    resolved = resolve_authoritative_repository_state(root, _lease_held=_lease_held)
     if resolved is None:
         return None
```

### `C:\Temp\Contextor_Repo\contextor\core\api\facade.py`

```diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 9ba32ae..a07c178 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -649,7 +649,9 @@ class ContextorFacade:
         )
 
         component_started = time.monotonic()
-        previous_canonical_state = resolve_authoritative_repository_state(path)
+        previous_canonical_state = resolve_authoritative_repository_state(
+            path, _lease_held=True
+        )
         emit_stage_component_end(
             "identity_and_setup",
             "authoritative_state_resolution",
@@ -1363,7 +1365,9 @@ class ContextorFacade:
         from contextor.core.graph.resolver import build_trie, detect_package_root
 
         collision_facts = None
-        authoritative_state = resolve_authoritative_repository_state(root_resolved)
+        authoritative_state = resolve_authoritative_repository_state(
+            root_resolved, _lease_held=True
+        )
         if authoritative_state is not None:
             progress.begin("Loading canonical LIVE context")
             state = authoritative_state.state
@@ -1605,7 +1609,9 @@ class ContextorFacade:
         analysis_state = None
         state_only = False
 
-        resolved = resolve_authoritative_repository_state(repo_root)
+        resolved = resolve_authoritative_repository_state(
+            repo_root, _lease_held=True
+        )
 
         if resolved is not None:
             state = resolved.state
@@ -1657,7 +1663,7 @@ class ContextorFacade:
                         )
 
         if not state_only:
-            hydrated = hydrate_repository_engine(repo_root)
+            hydrated = hydrate_repository_engine(repo_root, _lease_held=True)
 
         if state_only:
             pass
```

### `C:\Temp\Contextor_Repo\tests\test_live_state_store.py`

```diff
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 18e8548..1db30ca 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -2536,6 +2536,34 @@ def test_legacy_snapshot_migrates_to_repo_id_cache_without_deleting_source(
     assert (legacy / "engine_state.pkl").is_file()
 
 
+def test_already_coordinated_migration_does_not_acquire_second_lease(
+    tmp_path, monkeypatch
+):
+    from contextor.core.analysis import full_analysis_lease
+
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    legacy = legacy_repo_cache_dir(repo)
+    save_snapshot({"value": 7}, legacy, "legacy", writer="test")
+    real_acquire = full_analysis_lease.acquire_full_analysis
+    real_release = full_analysis_lease.release_full_analysis
+    lease = real_acquire(
+        repo, owner="scoped_test", writer_kind="scoped_analysis", timeout=5.0
+    )
+    try:
+        monkeypatch.setattr(
+            full_analysis_lease,
+            "acquire_full_analysis",
+            lambda *_a, **_k: pytest.fail("recursive full-analysis lease"),
+        )
+        assert migrate_legacy_snapshot(repo, _lease_held=True) == repo_cache_dir(repo)
+        assert read_metadata(repo_cache_dir(repo)) is not None
+    finally:
+        real_release(lease)
+
+
 def _migration_race_full_analysis_holder(
     repo_text, cache_text, lease_held, release_lease, results
 ):
```

### `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py`

```diff
diff --git a/tests/test_mcp_incremental_hydration.py b/tests/test_mcp_incremental_hydration.py
index 644b570..b47eaf4 100644
--- a/tests/test_mcp_incremental_hydration.py
+++ b/tests/test_mcp_incremental_hydration.py
@@ -1439,7 +1439,7 @@ def test_legacy_migration_writer_admission_precedes_mcp_cache_lock(
             with event_lock:
                 active_leases.pop(thread_id, None)
 
-    def pause_migration(_root):
+    def pause_migration(_root, **_kwargs):
         thread_id = threading.get_ident()
         with event_lock:
             events.append(("migration_callback", threading.current_thread().name))
@@ -1512,8 +1512,11 @@ def test_legacy_migration_writer_admission_precedes_mcp_cache_lock(
     assert cache_probe_was_blocked, (
         f"second thread acquired the same MCP cache RLock while migration was paused: {events}"
     )
-    assert lease_positions and cache_positions and lease_positions[0] < cache_positions[0], (
-        "full_analysis.lock must be acquired before the MCP cache RLock; "
+    assert lease_positions and len(cache_positions) >= 2 and (
+        cache_positions[0] < lease_positions[0] < cache_positions[1] < migration_positions[0]
+    ), (
+        "read-only cache probe must finish before writer admission, and "
+        "migration must run under the post-admission cache transaction; "
         f"callback_had_full_analysis_lease={observations.get('full_analysis_held_at_migration')}; "
         f"events={events}"
     )
@@ -1523,6 +1526,331 @@ def test_legacy_migration_writer_admission_precedes_mcp_cache_lock(
     )
 
 
+def test_warm_cache_does_not_attempt_legacy_migration_or_writer_admission(
+    tmp_path, monkeypatch
+):
+    from contextor.core import live_state
+    from contextor.core.analysis import full_analysis_lease
+    from contextor.core.paths import legacy_repo_cache_dir
+
+    root = tmp_path / "repo"
+    root.mkdir()
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    PersistentIdentityRegistry(str(root))
+    snapshot_store.save_snapshot(
+        {"legacy": True}, legacy_repo_cache_dir(root), "legacy", writer="test"
+    )
+    assert read_metadata(repo_cache_dir(root)) is None
+    cached = SimpleNamespace(state=SimpleNamespace(revision=7))
+    root_key = str(root.resolve())
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {root_key: cached})
+    monkeypatch.setattr(live_state, "connect", lambda _root: None)
+    monkeypatch.setattr(
+        live_state,
+        "migrate_legacy_snapshot",
+        lambda *_a, **_k: pytest.fail("warm cache attempted migration"),
+    )
+    monkeypatch.setattr(
+        full_analysis_lease,
+        "acquire_full_analysis",
+        lambda *_a, **_k: pytest.fail("warm cache attempted writer admission"),
+    )
+
+    assert mcp_runtime.get_or_init_engine(root) is cached
+
+
+def test_healthy_live_hydration_does_not_attempt_legacy_migration_or_writer_admission(
+    tmp_path, monkeypatch
+):
+    from contextor.core import live_state
+    from contextor.core.analysis import full_analysis_lease
+    from contextor.core.analysis import incremental_engine as incremental_module
+    from contextor.core.paths import legacy_repo_cache_dir
+
+    root = tmp_path / "repo"
+    root.mkdir()
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    PersistentIdentityRegistry(str(root))
+    snapshot_store.save_snapshot(
+        {"legacy": True}, legacy_repo_cache_dir(root), "legacy", writer="test"
+    )
+    assert read_metadata(repo_cache_dir(root)) is None
+    state = SimpleNamespace(revision=8, state_id="live-8")
+
+    class Client:
+        endpoint = SimpleNamespace(host="127.0.0.1", port=1, authkey_hex="test")
+
+        def ping(self):
+            return {"revision": 8}
+
+        def snapshot(self):
+            return {"state": state}
+
+    class Engine:
+        def __init__(self, loaded_state, *_args):
+            self.state = loaded_state
+
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {})
+    monkeypatch.setattr(mcp_runtime, "_live_sessions", {})
+    monkeypatch.setattr(mcp_runtime, "_live_journal_revisions", {})
+    monkeypatch.setattr(live_state, "connect", lambda _root: Client())
+    monkeypatch.setattr(incremental_module, "IncrementalAnalysisEngine", Engine)
+    monkeypatch.setattr(
+        live_state,
+        "migrate_legacy_snapshot",
+        lambda *_a, **_k: pytest.fail("LIVE hydration attempted migration"),
+    )
+    monkeypatch.setattr(
+        full_analysis_lease,
+        "acquire_full_analysis",
+        lambda *_a, **_k: pytest.fail("LIVE hydration attempted writer admission"),
+    )
+
+    assert mcp_runtime.get_or_init_engine(root).state is state
+
+
+def test_cold_fallback_rechecks_cache_after_writer_admission(tmp_path, monkeypatch):
+    from contextor.core import live_state
+    from contextor.core.analysis import full_analysis_lease
+
+    root = tmp_path / "repo"
+    root.mkdir()
+    PersistentIdentityRegistry(str(root))
+    root_key = str(root.resolve())
+    cached = SimpleNamespace(state=SimpleNamespace(revision=9))
+    admission_entered = threading.Event()
+    resume_admission = threading.Event()
+    outcomes = []
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {})
+    monkeypatch.setattr(live_state, "connect", lambda _root: None)
+    monkeypatch.setattr(
+        live_state,
+        "migrate_legacy_snapshot",
+        lambda *_a, **_k: pytest.fail("stale fallback migrated after cache recheck"),
+    )
+
+    def acquire(*_args, **_kwargs):
+        admission_entered.set()
+        assert resume_admission.wait(5)
+        return object()
+
+    monkeypatch.setattr(full_analysis_lease, "acquire_full_analysis", acquire)
+    monkeypatch.setattr(full_analysis_lease, "release_full_analysis", lambda _lease: None)
+
+    def hydrate():
+        try:
+            outcomes.append(mcp_runtime.get_or_init_engine(root))
+        except BaseException as exc:
+            outcomes.append(exc)
+
+    thread = threading.Thread(target=hydrate)
+    thread.start()
+    try:
+        assert admission_entered.wait(5)
+        with mcp_runtime._engine_cache_transaction(root):
+            mcp_runtime._live_engines[root_key] = cached
+    finally:
+        resume_admission.set()
+        thread.join(timeout=5)
+    assert not thread.is_alive()
+    assert outcomes == [cached]
+
+
+def test_cold_snapshot_returns_current_engine_revision_pair(tmp_path, monkeypatch):
+    root = tmp_path / "repo"
+    root.mkdir()
+    root_key = str(root.resolve())
+    older = SimpleNamespace(state=SimpleNamespace(revision=4))
+    newer = SimpleNamespace(state=SimpleNamespace(revision=5))
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {})
+    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
+
+    def fake_get(_root, *, _defer_migration=False):
+        if _defer_migration:
+            return mcp_runtime._MIGRATION_NEEDED
+        with mcp_runtime._engine_cache_transaction(root):
+            mcp_runtime._live_engines[root_key] = older
+            mcp_runtime._live_engine_revisions[root_key] = 4
+        replaced = threading.Event()
+
+        def publish_newer():
+            with mcp_runtime._engine_cache_transaction(root):
+                mcp_runtime._live_engines[root_key] = newer
+                mcp_runtime._live_engine_revisions[root_key] = 5
+            replaced.set()
+
+        worker = threading.Thread(target=publish_newer)
+        worker.start()
+        assert replaced.wait(5)
+        worker.join(timeout=5)
+        return older
+
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", fake_get)
+    assert mcp_runtime._get_or_init_engine_snapshot(root) == (newer, 5)
+
+
+def test_cold_wait_for_full_analysis_releases_mcp_cache_lock(tmp_path, monkeypatch):
+    from contextor.core import live_state
+    from contextor.core.analysis import full_analysis_lease
+    from contextor.core.analysis import state_manager
+    from contextor.core.paths import legacy_repo_cache_dir
+
+    cache_root = tmp_path / "cache"
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+    root = tmp_path / "repo"
+    root.mkdir()
+    PersistentIdentityRegistry(str(root))
+    snapshot_store.save_snapshot(
+        {"legacy": True}, legacy_repo_cache_dir(root), "legacy", writer="test"
+    )
+    monkeypatch.setattr(live_state, "connect", lambda _root: None)
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {})
+    monkeypatch.setattr(state_manager, "load_engine_state", lambda *_a, **_k: None)
+    attempted = threading.Event()
+    outcome = []
+    real_acquire = full_analysis_lease.acquire_full_analysis
+
+    def observe_acquire(*args, **kwargs):
+        attempted.set()
+        return real_acquire(*args, **kwargs)
+
+    monkeypatch.setattr(full_analysis_lease, "acquire_full_analysis", observe_acquire)
+    context = multiprocessing.get_context("spawn")
+    ready, entered, release = (context.Event() for _ in range(3))
+    results = context.Queue()
+    holder = context.Process(
+        target=_cross_process_full_writer_worker,
+        args=(str(root), ready, entered, release, results),
+    )
+
+    def cold_get():
+        try:
+            outcome.append(mcp_runtime.get_or_init_engine(root))
+        except BaseException as exc:
+            outcome.append(exc)
+
+    thread = threading.Thread(target=cold_get)
+    try:
+        holder.start()
+        assert entered.wait(5), "other process did not hold full_analysis.lock"
+        thread.start()
+        assert attempted.wait(5), "cold getter did not reach writer admission"
+
+        reader_acquired = threading.Event()
+
+        def read_cache():
+            with mcp_runtime._engine_cache_transaction(root):
+                reader_acquired.set()
+
+        reader = threading.Thread(target=read_cache)
+        reader.start()
+        assert reader_acquired.wait(1), "waiting writer held the MCP cache RLock"
+        reader.join(timeout=2)
+        assert not reader.is_alive()
+    finally:
+        release.set()
+        if thread.ident is not None:
+            thread.join(timeout=10)
+        if holder.pid is not None:
+            holder.join(timeout=10)
+            if holder.is_alive():
+                holder.terminate()
+                holder.join(timeout=5)
+        results.close()
+        results.join_thread()
+    assert not thread.is_alive()
+    assert not holder.is_alive()
+    assert holder.exitcode == 0
+    assert not outcome or outcome[0] is None
+
+
+def test_missing_identity_and_missing_legacy_do_not_publish_migration(
+    tmp_path, monkeypatch
+):
+    from contextor.core import live_state
+    from contextor.core.analysis import state_manager
+
+    root = tmp_path / "repo"
+    root.mkdir()
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    monkeypatch.setattr(live_state, "connect", lambda _root: None)
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {})
+    monkeypatch.setattr(
+        snapshot_store,
+        "save_snapshot",
+        lambda *_a, **_k: pytest.fail("missing source published migration"),
+    )
+    monkeypatch.setattr(state_manager, "load_engine_state", lambda *_a, **_k: None)
+
+    assert mcp_runtime.get_or_init_engine(root) is None
+    assert not (root / ".contextor").exists()
+
+    PersistentIdentityRegistry(str(root))
+    assert mcp_runtime.get_or_init_engine(root) is None
+    assert read_metadata(repo_cache_dir(root)) is None
+
+
+def test_concurrent_cold_hydration_commits_one_migration_and_one_engine(
+    tmp_path, monkeypatch
+):
+    from contextor.core import live_state
+    from contextor.core.analysis import incremental_engine as incremental_module
+    from contextor.core.analysis import state_manager
+    from contextor.core.paths import legacy_repo_cache_dir
+
+    root = tmp_path / "repo"
+    root.mkdir()
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    PersistentIdentityRegistry(str(root))
+    snapshot_store.save_snapshot(
+        {"legacy": True}, legacy_repo_cache_dir(root), "legacy", writer="test"
+    )
+    monkeypatch.setattr(live_state, "connect", lambda _root: None)
+    for name in (
+        "_live_engines",
+        "_live_engine_revisions",
+        "_live_engine_provenance",
+        "_live_sessions",
+        "_live_journal_revisions",
+    ):
+        monkeypatch.setattr(mcp_runtime, name, {})
+    state = SimpleNamespace()
+    monkeypatch.setattr(state_manager, "load_engine_state", lambda *_a, **_k: state)
+    monkeypatch.setattr(state_manager, "FileStateManager", lambda *_a: object())
+
+    class Engine:
+        def __init__(self, loaded_state, *_args):
+            self.state = loaded_state
+
+    monkeypatch.setattr(incremental_module, "IncrementalAnalysisEngine", Engine)
+    real_save = snapshot_store.save_snapshot
+    commits = []
+
+    def count_commit(*args, **kwargs):
+        commits.append(True)
+        return real_save(*args, **kwargs)
+
+    monkeypatch.setattr(snapshot_store, "save_snapshot", count_commit)
+    barrier = threading.Barrier(3)
+    results = []
+
+    def get_pair():
+        barrier.wait(timeout=5)
+        results.append(mcp_runtime._get_or_init_engine_snapshot(root))
+
+    workers = [threading.Thread(target=get_pair) for _ in range(3)]
+    for worker in workers:
+        worker.start()
+    for worker in workers:
+        worker.join(timeout=10)
+    assert all(not worker.is_alive() for worker in workers)
+    assert len(results) == 3
+    assert len(commits) == 1
+    assert all(engine is results[0][0] for engine, _revision in results)
+    assert all(revision == results[0][1] for _engine, revision in results)
+    assert results[0][1] == read_metadata(repo_cache_dir(root)).revision
+
+
 def test_mcp_refreshes_its_engine_from_a_newer_shared_live_revision(tmp_path, monkeypatch):
     first = RepositoryAnalysisState(modules={"old": object()})
     second = RepositoryAnalysisState(modules={"new": object()})
```

### `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py`

```diff
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index daf1bc6..c56c937 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -289,7 +289,7 @@ def test_analysis_refresh_transaction_excludes_same_root_reader(tmp_path, monkey
             "live_publish_revision": 11,
         }
 
-    def refresh_engine(_candidate_root):
+    def refresh_engine(_candidate_root, **_kwargs):
         refresh_entered.set()
         release_refresh.wait()
         mcp_runtime._live_engines[root_key] = new_engine
@@ -359,7 +359,7 @@ def test_analysis_refresh_transaction_is_reentrant(tmp_path, monkeypatch):
             "live_publish_revision": 13,
         }
 
-    def reentrant_get(candidate_root):
+    def reentrant_get(candidate_root, **_kwargs):
         with mcp_runtime._engine_cache_transaction(candidate_root):
             mcp_runtime._live_engines[root_key] = engine
             return engine
@@ -430,7 +430,7 @@ def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
         def update_file(self, *_args, **_kwargs):
             return {"status": "ok", "revision": 22, "result": result}
 
-    def fake_get_or_init_engine(_root):
+    def fake_get_or_init_engine(_root, **_kwargs):
         calls.append(True)
         if len(calls) == 1:
             return old_engine
@@ -516,7 +516,7 @@ def test_file_edit_context_binds_engine_and_revision_atomically(tmp_path, monkey
     result_box = []
     errors = []
 
-    def fake_get_or_init_engine(_root):
+    def fake_get_or_init_engine(_root, **_kwargs):
         mcp_runtime._live_engines[root_key] = engine_one
         mcp_runtime._live_engine_revisions[root_key] = 41
         snapshot_entered.set()
@@ -1154,7 +1154,7 @@ def test_project_analysis_job_fails_closed_when_canonical_engine_is_missing(
         }
 
     monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, **_kwargs: None)
     mcp_runtime._live_engines[str(repo)] = SimpleNamespace(
         state=SimpleNamespace(revision=10)
     )
@@ -1189,7 +1189,7 @@ def test_project_analysis_job_fails_closed_on_canonical_revision_mismatch(
     monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
     mismatched_engine = SimpleNamespace(state=SimpleNamespace(revision=10))
 
-    def fake_get_or_init_engine(_root):
+    def fake_get_or_init_engine(_root, **_kwargs):
         mcp_runtime._live_engines[str(repo)] = mismatched_engine
         return mismatched_engine
 
@@ -1225,7 +1225,7 @@ def test_project_analysis_job_certifies_matching_canonical_revision(
     monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
     matching_engine = SimpleNamespace(state=SimpleNamespace(revision=11))
 
-    def fake_get_or_init_engine(_root):
+    def fake_get_or_init_engine(_root, **_kwargs):
         mcp_runtime._live_engines[str(repo)] = matching_engine
         return matching_engine
 
@@ -2913,7 +2913,7 @@ def test_mcp_update_file_live_branch_delegates_without_local_persistence(
     monkeypatch.setattr(
         "contextor.core.live_state.connect", lambda _root: FakeLiveClient()
     )
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, **_kwargs: engine)
     monkeypatch.setattr(
         mcp_runtime,
         "_engine_cache_transaction",
@@ -2942,6 +2942,128 @@ def test_mcp_update_file_live_branch_delegates_without_local_persistence(
     assert response["live_state_persisted"] is True
 
 
+def test_project_analysis_cold_migration_exits_outer_cache_transaction(
+    tmp_path, monkeypatch
+):
+    from contextlib import contextmanager
+
+    root = tmp_path / "repo"
+    root.mkdir()
+    root_key = str(root.resolve())
+    engine = SimpleNamespace(state=SimpleNamespace(revision=18))
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {})
+    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
+    real_transaction = mcp_runtime._engine_cache_transaction
+    depth = 0
+    calls = []
+
+    @contextmanager
+    def observed_transaction(candidate_root):
+        nonlocal depth
+        with real_transaction(candidate_root) as key:
+            depth += 1
+            try:
+                yield key
+            finally:
+                depth -= 1
+
+    def fake_get(_root, *, _defer_migration=False):
+        calls.append((_defer_migration, depth))
+        if _defer_migration:
+            return mcp_runtime._MIGRATION_NEEDED
+        assert depth == 0
+        with mcp_runtime._engine_cache_transaction(root):
+            mcp_runtime._live_engines[root_key] = engine
+            mcp_runtime._live_engine_revisions[root_key] = 18
+        return engine
+
+    async def worker(*_args, **_kwargs):
+        return {"live_publish_status": "success", "live_publish_revision": 18}
+
+    writes = []
+    monkeypatch.setattr(mcp_runtime, "_engine_cache_transaction", observed_transaction)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", fake_get)
+    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", worker)
+    monkeypatch.setattr(analysis_jobs, "_write_analysis_job", lambda _r, job: writes.append(job))
+    asyncio.run(
+        analysis_jobs._execute_analysis_job(
+            root, _project_analysis_job(root, "cold-analysis-refresh"), None, []
+        )
+    )
+    assert calls == [(True, 1), (False, 0)]
+    assert writes[-1]["status"] == "completed"
+    assert mcp_runtime._live_engine_revisions[root_key] == 18
+
+
+@pytest.mark.parametrize("hydrated", [True, False])
+def test_direct_live_update_cold_refresh_exits_outer_cache_and_checks_revision(
+    tmp_path, monkeypatch, hydrated
+):
+    from contextlib import contextmanager
+
+    root = tmp_path / "repo"
+    root.mkdir()
+    root_key = str(root.resolve())
+    target = root / "provider.py"
+    target.write_text("VALUE = 1\n", encoding="utf-8")
+    old = SimpleNamespace(state=SimpleNamespace(artifacts={"provider": {}}))
+    current = SimpleNamespace(
+        state=SimpleNamespace(artifacts={"provider": {}}, revision=42)
+    )
+    result = SimpleNamespace(
+        status="UPDATED", file_path=str(target), graph_state="fresh",
+        dependencies_state="fresh", blast_radius_state="fresh",
+        local_metrics_state="deferred", global_metrics_state="deferred",
+        artifact_consumption_state="fresh", affected_modules=[], delta=None,
+    )
+    remote_calls = []
+
+    class Client:
+        def update_file(self, *_args, **_kwargs):
+            remote_calls.append(True)
+            return {"status": "ok", "revision": 42, "result": result}
+
+    real_transaction = mcp_runtime._engine_cache_transaction
+    depth = 0
+    calls = []
+
+    @contextmanager
+    def observed_transaction(candidate_root):
+        nonlocal depth
+        with real_transaction(candidate_root) as key:
+            depth += 1
+            try:
+                yield key
+            finally:
+                depth -= 1
+
+    def fake_get(_root, *, _defer_migration=False):
+        calls.append((_defer_migration, depth))
+        if len(calls) == 1:
+            return old
+        if _defer_migration:
+            return mcp_runtime._MIGRATION_NEEDED
+        assert depth == 0
+        assert root_key not in mcp_runtime._live_engine_revisions
+        if hydrated:
+            with mcp_runtime._engine_cache_transaction(root):
+                mcp_runtime._live_engines[root_key] = current
+                mcp_runtime._live_engine_revisions[root_key] = 42
+            return current
+        return None
+
+    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: Client())
+    monkeypatch.setattr(mcp_runtime, "_engine_cache_transaction", observed_transaction)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", fake_get)
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {})
+    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
+    monkeypatch.setattr(update_file_module, "_mcp_runtime_restart_required", lambda _p: False)
+    response = json.loads(update_file_module.update_file(str(root), str(target)))
+    assert remote_calls == [True]
+    assert calls == [(False, 0), (True, 1), (False, 0)]
+    assert response["status"] == ("UPDATED" if hydrated else "ERROR")
+
+
 def test_mcp_update_file_local_persistence_exception_keeps_error_response(
     tmp_path, monkeypatch
 ):
```

### `C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py`

```diff
diff --git a/tests/test_full_analysis_coordination.py b/tests/test_full_analysis_coordination.py
index 08d6ca7..6fe12ac 100644
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -1159,7 +1159,7 @@ def test_mcp_single_publication_root_cause_regression(tmp_path: Path, monkeypatc
     monkeypatch.setattr(
         mcp_runtime,
         "get_or_init_engine",
-        lambda _root: SimpleNamespace(state=SimpleNamespace(revision=11)),
+        lambda _root, **_kwargs: SimpleNamespace(state=SimpleNamespace(revision=11)),
     )
     monkeypatch.setattr(
         "contextor.core.live_state.connect_or_start",
```

### `C:\Temp\Contextor_Repo\tests\test_layer_state_only_hydration.py`

```diff
diff --git a/tests/test_layer_state_only_hydration.py b/tests/test_layer_state_only_hydration.py
index 9fa3f43..6196b07 100644
--- a/tests/test_layer_state_only_hydration.py
+++ b/tests/test_layer_state_only_hydration.py
@@ -26,7 +26,7 @@ def _state(tmp_path):
 def _patch_resolution_dependencies(monkeypatch, root, *, live=None, snapshot=None):
     identity = RepositoryIdentity("ctx_test", str(root.resolve()), root.name)
     monkeypatch.setattr("contextor.core.repository_identity.read_repository_identity", lambda _: identity)
-    monkeypatch.setattr("contextor.core.live_state.store.migrate_legacy_snapshot", lambda _: root / "cache")
+    monkeypatch.setattr("contextor.core.live_state.store.migrate_legacy_snapshot", lambda _, **_kwargs: root / "cache")
     monkeypatch.setattr("contextor.core.live_state.store.read_metadata", lambda _: SimpleNamespace(state_id="state"))
     monkeypatch.setattr("contextor.core.analysis.state_manager.load_engine_state", lambda *args, **kwargs: snapshot)
     monkeypatch.setattr("contextor.core.live_state.runtime.connect", lambda _: live)
@@ -68,7 +68,7 @@ def test_full_hydrator_still_constructs_an_incremental_engine(tmp_path, monkeypa
         state=state, client=None, revision=3, source="snapshot", cache_dir=tmp_path / "cache"
     )
     calls = []
-    monkeypatch.setattr(hydration, "resolve_authoritative_repository_state", lambda _: resolved)
+    monkeypatch.setattr(hydration, "resolve_authoritative_repository_state", lambda _, **_kwargs: resolved)
 
     class Engine:
         def __init__(self, *args):
@@ -91,7 +91,7 @@ def test_layer_uses_state_directly_without_full_engine_hydration(tmp_path, monke
     resolved = hydration.AuthoritativeRepositoryState(
         state=state, client=None, revision=3, source="snapshot", cache_dir=tmp_path / "cache"
     )
-    monkeypatch.setattr(facade, "resolve_authoritative_repository_state", lambda _: resolved)
+    monkeypatch.setattr(facade, "resolve_authoritative_repository_state", lambda _, **_kwargs: resolved)
     monkeypatch.setattr(facade, "hydrate_repository_engine", lambda _: (_ for _ in ()).throw(AssertionError("full hydration used")))
     monkeypatch.setattr(facade, "_initialize_repository_identity", lambda _: SimpleNamespace(transaction=lambda: nullcontext()))
     monkeypatch.setattr(facade, "reset_caches", lambda: None)
```

### `C:\Temp\Contextor_Repo\tests\test_live_single_file_reuse.py`

```diff
diff --git a/tests/test_live_single_file_reuse.py b/tests/test_live_single_file_reuse.py
index b609cea..5080572 100644
--- a/tests/test_live_single_file_reuse.py
+++ b/tests/test_live_single_file_reuse.py
@@ -101,8 +101,8 @@ def test_single_file_reports_accepted_recovery_without_changing_string_return(
     original_hydrate = facade_module.hydrate_repository_engine
     published = []
 
-    def hydrate_with_client(root):
-        hydrated = original_hydrate(root)
+    def hydrate_with_client(root, **kwargs):
+        hydrated = original_hydrate(root, **kwargs)
         client = SimpleNamespace(publish=lambda *_a, **_k: published.append(True) or {
             "status": "ok", "revision": 17,
             "resync_required": True, "warning": "release unverified",
@@ -149,8 +149,8 @@ def test_scoped_single_file_publishes_to_real_live_server_under_writer_lease(
     original_publish = client.publish
     observed = []
 
-    def hydrate_with_server(root):
-        hydrated = original_hydrate(root)
+    def hydrate_with_server(root, **kwargs):
+        hydrated = original_hydrate(root, **kwargs)
         return replace(hydrated, client=client)
 
     def publish_while_held(*args, **kwargs):
@@ -204,12 +204,12 @@ def test_single_file_resync_state_rejects_state_only_path(
     hydrate_calls = 0
     first_resolution = True
 
-    def controlled_resolver(repo_path):
+    def controlled_resolver(repo_path, **kwargs):
         nonlocal first_resolution
         if first_resolution:
             first_resolution = False
             return resolved
-        return real_resolver(repo_path)
+        return real_resolver(repo_path, **kwargs)
 
     def counted_hydrate(*args, **kwargs):
         nonlocal hydrate_calls
```


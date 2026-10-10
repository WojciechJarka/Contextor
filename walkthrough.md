# L32H2C — cross-process LIVE authority fence

Task scope: exact auditor-supplied patch. No commit, reset, checkout, process restart, manual Contextor update_file, full analysis, or real LIVE lease manipulation. Tests use isolated temporary repositories. No power-loss/crash atomicity or global exclusion from unrelated full-analysis writers is claimed.

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py
- C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only)

## SOURCE_CONTRACT_VERIFICATION

DIRECT_EVIDENCE: Contextor MCP deferred tools were discovered and documentation read first. Before editing, complete current implementations were fetched for _execute_local_candidate_update, _persist_live_engine, mcp_runtime._engine_cache_transaction, RuntimeLeaseManager._lock, _read_generation, _read_live_lease and _production_domain. Each successful source response reported implementation_is_complete=true and workspace_sync=verified at canonical revision 214. The private manager methods matched the preceding literal handoff. A global leaf lookup for _production_domain was ambiguous; retry with explicit source file resolved exactly. IncrementalAnalysisEngine.update_file exceeded symbol-tool output threshold; exact complete range 453–736 was fetched with get_source_range(allow_large_output=true). No preview was used as complete source.

CODE_PATH_PROVED lock-order audit: local helper -> candidate update -> _persist_live_engine -> save_engine_state/save_snapshot and registry checkpoint/restore were inspected. Targeted search within incremental analysis, state_manager, registry, snapshot store and MCP runtime found RuntimeLeaseManager reader/acquire/release/fence calls only in MCP runtime connect paths, not in the candidate/registry/snapshot call chain. Contextor call context confirmed the same-module caller/callee path. No reachable nested domain acquisition was found in the inspected transaction. Dynamic Python callbacks remain outside static completeness.

The production change is the literal supplied code: old helper body renamed _execute_local_candidate_update_unfenced without body edits; new _assert_local_committed_baseline and fenced _execute_local_candidate_update inserted immediately before it. Public update_file still calls the fenced name. Targeted rg and Contextor call context found only one production call to the unfenced helper, from the fenced wrapper. No authority generation record is written by the new wrapper.

## RED_RESULT

Before production edit, 10/10 untrusted-authority parametrized cases failed because the local path reached a forbidden candidate/registry operation despite active, reserved, active-without-lease, fenced, mismatched, malformed, foreign or transport-failure-simulated authority. The stale-revision preflight test failed because candidate/checkpoint work began first. LIVE acquire during paused persistence and rollback failed the expected exclusion check; domain-lock timeout test returned UPDATED; two-process test exposed competing local updates. The first RED run also exposed two test-setup errors: foreign record fixtures tried to use owner-validated writers that reject foreign data. Those fixtures were corrected to write only isolated temporary durable files, then the 10 untrusted cases were re-run and all failed for the expected missing-admission behavior. This is not evidence of production corruption.

## GREEN_RESULT

- Newly added focused L32H2C cases: **17 passed** (including 10 authority-state parameters, clean never_acquired/released, stale baseline, paused LIVE acquire, rollback fence, lock timeout, and two-process local exclusion).
- Complete requested test files: `tests/test_mcp_incremental_hydration.py` plus `tests/test_mcp_regressions.py`: **149 passed, 0 failed**.
- Selected RuntimeLeaseManager/authority bootstrap cases: **17 passed, 0 failed** (generation allocation/release/gap, ambiguous liveness, malformed/foreign records, cross-process one-winner, active generation without lease, bootstrap parity/restart, liveness probe outside domain lock).
- Public MCP documentation parity: **4 passed, 0 failed**. `contextor/mcp/docs/update_file.json` was read; no public parameter/schema change required a docs edit.
- After a final test-only assertion/import adjustment, the directly affected cross-process and lock-timeout nodes were re-run individually and passed. No unnecessary full-file rerun was performed.
- Repository .venv Python py_compile for all three changed source/test files: pass. `git diff --check` for those files: pass.

An intermediate complete two-file run had 17 failures because the existing _real_local_update_fixture placed cache, then logs, inside the analyzed temporary root; the newly used production RuntimeDomain validation correctly refused those overlapping roots. The fixture in the authorized test file now puts cache/state beside the temporary repository. A focused previously failing node passed, then the complete two-file gate passed 149/149.

## DOMAIN_LOCK_ADMISSION_MATRIX

| Durable state in isolated test repo | Expected local result | Observed |
|---|---|---|
| No lease, never_acquired | Allowed | UPDATED, revision 2 |
| No lease, clean released | Allowed | UPDATED, revision 2 |
| Active generation + live lease | Denied before candidate | ERROR |
| Reserved generation | Denied | ERROR |
| Active generation without live lease | Denied | ERROR |
| Fenced generation | Denied | ERROR |
| Live lease with mismatched generation | Denied | ERROR |
| Malformed generation or lease | Denied | ERROR |
| Foreign generation or lease | Denied | ERROR |
| connect(root)=None with active lease (simulated transport failure) | Denied | ERROR |

Negative tests make IncrementalAnalysisEngine.update_file, registry checkpoint and local persistence forbidden call sites, and confirm prior cached engine, registry state and snapshot metadata remain intact.

## ACTIVE_LIVE_AND_TRANSPORT_FAILURE_GATE

CODE_PATH_PROVED: The wrapper takes the cache RLock, then RuntimeLeaseManager._lock; under the held domain lock it reads via private unlocked _read_generation/_read_live_lease. Any live lease or status outside {never_acquired, released} returns ERROR before baseline/candidate work. The transport-failure simulation forces connect(root)=None while an active durable LIVE lease remains; it returns ERROR. The public connect result alone is not admission.

## STARTUP_ACQUIRE_EXCLUSION

The pause-inside-persistence test starts RuntimeLeaseManager.acquire in another thread and confirms it cannot acquire until local persistence finishes and the domain lock exits. After release it acquires generation 1. Existing RuntimeLeaseManager acquisition and publication use the identical domain OS lock. A local transaction lasting longer than the default **10-second lock acquisition timeout can delay LIVE startup or shutdown and can make the competing lease operation fail with LeaseBusyError**; successful long hold has no 10-second expiration. This is a remaining operational limit, not a claim of transparent waiting.

## CROSS_PROCESS_LOCAL_WRITER_EXCLUSION

Two independent spawned MCP processes use the same temporary repository/cache. Process 1 pauses inside local persistence. Process 2 hydrates its engine and signals readiness, then attempts local update. Its candidate engine update does not begin while process 1 holds the domain lock. After process 1 releases, process 2 is rejected by the stale committed-revision preflight; first snapshot remains at revision 2. Direct test passed after the final worker-readiness adjustment. This proves the tested process schedule, not every possible schedule.

## PRE_REGISTRY_REVISION_GATE

_assert_local_committed_baseline executes under both locks before the renamed helper creates its registry checkpoint. Its exact supplied checks cover invalid existing snapshot metadata, repository/root identity, engine/state/cache revisions and state/FileStateManager identity. A stale engine revision test forbids candidate engine update and checkpoint, receives ERROR with “stale engine revision”, and confirms snapshot and registry unchanged. The existing _persist_live_engine exact-revision validation remains unchanged as a second check.

## REGISTRY_ROLLBACK_UNDER_FENCE

A test injects persistence failure and pauses inside registry.restore_checkpoint. Concurrent LIVE acquire cannot complete until rollback is released and the local helper exits. The existing disk-ahead logic and cache-eviction paths were not changed; the complete hydration test file includes their passing regressions. The domain fence covers both successful cache publication and exception/rollback paths through the lexical return/raise.

## LOCK_ORDER_AND_REENTRANCY

Observed order: MCP per-repository cache RLock -> RuntimeLeaseManager domain OS lock -> existing registry transaction -> exact snapshot publication. The unfenced helper and _persist_live_engine reenter only the cache RLock, which is reentrant. Under the domain lock the wrapper uses private unlocked record readers. It does not call public read_generation/read_live_lease or acquire/release/fence_owner, which would try to reenter the non-reentrant domain lock. No nested acquisition was found in inspected transitive production owners.

## LOCK_TIMEOUT_BEHAVIOR

An isolated thread holds the same domain lock while the local writer uses a 0.1-second test timeout. Public update returns ERROR with “timed out waiting for domain lock”; existing cached engine, registry and snapshot metadata are unchanged. The caller had already edited the target source file before invoking update_file; the operation itself made no source edit.

## L32H2B_COMPATIBILITY

The complete two-file gate includes the existing L32H2B exact-generation snapshot, FileState hydration, COW, persistence rejection, rollback, syntax LKG, RECOVERED, early/parsed UNCHANGED and disk-ahead tests. 149/149 passed. The renamed helper body was not edited. Full-analysis writers use the separate full_analysis.lock, so this gate does **not** prove global writer exclusion against unrelated full-analysis writers.

## LIVE_BRANCH_COMPATIBILITY

Public update_file keeps its existing LIVE delegated branch and calls the fenced helper only when connect returns no verified client. The existing `test_mcp_update_file_live_branch_delegates_without_local_persistence` passed in the complete regressions file. No manual update_file call was made against the real LIVE authority.

## SOURCE_SYNC_VERIFICATION

After production/test edits, Contextor get_symbol_implementation fetched complete _assert_local_committed_baseline, fenced _execute_local_candidate_update and _execute_local_candidate_update_unfenced, all with workspace_sync=verified at revision 219. Contextor same-module call context reports exactly one direct caller of the unfenced helper: the fenced wrapper at line 288. Artifact blast radius reported no direct static consumer for the private helper; that static projection does not supersede call-context evidence. Later edits only adjusted the authorized test file, observed by Desktop watcher through revision 222; production source had no later edit. Source indexing freshness does not attest imported-code reload in the existing MCP process.

## LIVE_REVISION_BEFORE_AFTER

Before edit: canonical revision **214**. `get_live_events(after_revision=214)` returned continuous desktop_watcher UPDATED events at revisions 215–219 for the changed production/test files, with resync_required=false. Subsequent `after_revision=219` and `after_revision=220` queries returned continuous events 220 and 221 for the test file, each with resync_required=false. A final after_revision=221 query returned continuous desktop_watcher UPDATED revision 222 for the last test-only cleanup, also resync_required=false. Activity epoch in the first post-edit response: `9e9a2a2edcb046bba00df0850244ad36`. Last observed canonical revision: **222**. All final edited source/test files have corresponding watcher events.

## REMAINING_RISKS

- Runtime process reload is unverified: fresh pytest imports and Contextor source indexing do not prove the serving MCP process loaded the new code.
- Long local transactions can block LIVE lease acquisition/release past their lock timeout; caller receives failure, not guaranteed waiting.
- The domain lease lock is distinct from full_analysis.lock; no global exclusion against unrelated full-analysis writers is claimed.
- No crash/power-loss atomicity is claimed.
- The two-process test establishes one controlled overlap, not all schedules.

## RESTART_REQUIRED

Manual MCP server restart/reload is required before serving-process certification of the modified `contextor/mcp/tools/update_file.py` implementation. No restart was performed. No Desktop or LIVE restart was performed or claimed necessary from this exact source change.

## FULL_DIFFS

Full raw Git diffs of every changed production/test file follow. walkthrough.md is the report and is excluded from source diff accounting.

### C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py

```diff
diff --git a/contextor/mcp/tools/update_file.py b/contextor/mcp/tools/update_file.py
index 8703e41..acf5ab0 100644
--- a/contextor/mcp/tools/update_file.py
+++ b/contextor/mcp/tools/update_file.py
@@ -183,7 +183,118 @@ class _LocalCandidatePersistenceRejected(RuntimeError):
     """The local candidate was discarded because its snapshot was not committed."""
 
 
-def _execute_local_candidate_update(root: Path, target_file: Path, engine):
+def _assert_local_committed_baseline(root: Path, engine, root_key: str) -> None:
+    """Reject stale local RAM before registry or candidate mutation."""
+    from contextor.core.live_state import read_metadata
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.repository_identity import require_repository_identity
+
+    identity = require_repository_identity(root)
+    cache_dir = repo_cache_dir(root)
+    metadata_path = cache_dir / "engine_state.meta.json"
+    current = read_metadata(cache_dir)
+
+    if current is None and metadata_path.exists():
+        raise RuntimeError(
+            "Local writer denied: committed snapshot metadata is invalid."
+        )
+
+    if current is not None:
+        if current.repo_id and current.repo_id != identity.repo_id:
+            raise RuntimeError(
+                "Local writer denied: snapshot repository identity mismatch."
+            )
+        if (
+            current.root_path
+            and Path(current.root_path).expanduser().resolve()
+            != Path(identity.root_path).expanduser().resolve()
+        ):
+            raise RuntimeError(
+                "Local writer denied: snapshot repository root mismatch."
+            )
+
+    expected = int(current.revision) if current is not None else None
+
+    for owner, value in (
+        ("engine", getattr(engine, "revision", None)),
+        ("state", getattr(engine.state, "revision", None)),
+        ("cache", mcp_runtime._live_engine_revisions.get(root_key)),
+    ):
+        if value is None:
+            continue
+        if type(value) is not int:
+            raise RuntimeError(
+                f"Local writer denied: invalid {owner} revision."
+            )
+        if expected is None:
+            if value != 0:
+                raise RuntimeError(
+                    f"Local writer denied: {owner} has no committed baseline."
+                )
+        elif value != expected:
+            raise RuntimeError(
+                f"Local writer denied: stale {owner} revision."
+            )
+
+    if current is not None and current.state_id:
+        manager = getattr(engine, "state_manager", None)
+        for owner, value in (
+            ("state", getattr(engine.state, "state_id", None)),
+            ("FileStateManager", getattr(manager, "state_id", None)),
+        ):
+            if value and str(value) != current.state_id:
+                raise RuntimeError(
+                    f"Local writer denied: {owner} identity mismatch."
+                )
+
+
+def _execute_local_candidate_update(
+    root: Path, target_file: Path, engine
+):
+    """Fence LIVE authority before executing a local candidate transaction."""
+    from contextor.core.live_state.runtime import _production_domain
+    from contextor.core.live_state.runtime_lease import RuntimeLeaseManager
+    from contextor.core.repository_identity import require_repository_identity
+
+    with mcp_runtime._engine_cache_transaction(root) as root_key:
+        if mcp_runtime._live_engines.get(root_key) is not engine:
+            raise RuntimeError(
+                "Local cached engine ownership changed."
+            )
+
+        identity = require_repository_identity(root)
+        domain = _production_domain(identity)
+        lease_manager = RuntimeLeaseManager(domain)
+
+        with lease_manager._lock():
+            generation = lease_manager._read_generation()
+            live_lease = lease_manager._read_live_lease()
+
+            if (
+                live_lease is not None
+                or generation.status not in {"never_acquired", "released"}
+            ):
+                raise RuntimeError(
+                    "Local writer denied: LIVE authority is present "
+                    "or its ownership is unresolved."
+                )
+
+            _assert_local_committed_baseline(
+                root,
+                engine,
+                root_key,
+            )
+
+            return _execute_local_candidate_update_unfenced(
+                root,
+                target_file,
+                engine,
+            )
+
+
+def _execute_local_candidate_update_unfenced(
+    root: Path, target_file: Path, engine
+):
     """Commit a local update candidate before replacing the cached engine."""
     from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
     from contextor.core.live_state import read_metadata
```

### C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py

```diff
diff --git a/tests/test_mcp_incremental_hydration.py b/tests/test_mcp_incremental_hydration.py
index b98f902..9476dfb 100644
--- a/tests/test_mcp_incremental_hydration.py
+++ b/tests/test_mcp_incremental_hydration.py
@@ -7,6 +7,8 @@ from pathlib import Path
 
 import pytest
 import threading
+import multiprocessing
+from dataclasses import replace
 from types import SimpleNamespace
 
 from contextor import mcp_server
@@ -35,6 +37,12 @@ from contextor.core.reference.shared import (
 from contextor.core.live_state import CanonicalLiveServer, LiveStateClient, read_metadata
 from contextor.core.live_state import store as snapshot_store
 from contextor.core.repository_identity import require_repository_identity
+from contextor.core.live_state.runtime import _production_domain
+from contextor.core.live_state.runtime_lease import (
+    RuntimeLeaseManager,
+    generation_metadata_path,
+    live_lease_path,
+)
 from contextor.mcp.tools import update_file as update_file_module
 
 pytestmark = pytest.mark.live
@@ -92,6 +100,363 @@ def _rehydrate_local_engine(repo):
     return mcp_runtime.get_or_init_engine(repo.resolve())
 
 
+def _local_lease_manager(repo, *, lock_timeout=10.0):
+    return RuntimeLeaseManager(
+        _production_domain(require_repository_identity(repo)),
+        lock_timeout=lock_timeout,
+    )
+
+
+def _cross_process_local_candidate_worker(
+    repo_text, target_text, cache_text, entered, release, ready, update_started, results, first
+):
+    os.environ["CONTEXTOR_CACHE_DIR"] = cache_text
+    from contextor.core import live_state
+
+    live_state.connect = lambda _root: None
+    mcp_runtime._live_engines.clear()
+    mcp_runtime._live_engine_revisions.clear()
+    real_persist = update_file_module._persist_live_engine
+    real_update = IncrementalAnalysisEngine.update_file
+
+    if first:
+        def wait_in_persist(root, candidate):
+            entered.set()
+            if not release.wait(10):
+                raise TimeoutError("cross-process persistence hold expired")
+            return real_persist(root, candidate)
+
+        update_file_module._persist_live_engine = wait_in_persist
+    else:
+        def observe_update(self, path):
+            update_started.set()
+            return real_update(self, path)
+
+        IncrementalAnalysisEngine.update_file = observe_update
+
+    try:
+        if not first:
+            assert mcp_runtime.get_or_init_engine(Path(repo_text)) is not None
+            ready.set()
+        results.put(_local_update(Path(repo_text), Path(target_text)))
+    except BaseException as exc:
+        results.put({"status": "WORKER_ERROR", "error": repr(exc)})
+
+
+@pytest.mark.parametrize("prior_generation", ["never_acquired", "released"])
+def test_local_writer_accepts_only_clean_absence_states(
+    tmp_path, monkeypatch, prior_generation
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    if prior_generation == "released":
+        authority = _local_lease_manager(repo)
+        authority.release(authority.acquire())
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+
+    response = _local_update(repo, provider)
+
+    assert response["status"] == "UPDATED"
+    assert read_metadata(repo_cache_dir(repo)).revision == 2
+
+
+@pytest.mark.parametrize(
+    "authority_state",
+    [
+        "active",
+        "reserved",
+        "active_missing_lease",
+        "fenced",
+        "mismatched_generation",
+        "malformed_generation",
+        "malformed_lease",
+        "foreign_generation",
+        "foreign_lease",
+        "transport_failure_with_active_lease",
+    ],
+)
+def test_local_writer_rejects_untrusted_authority_before_mutation(
+    tmp_path, monkeypatch, authority_state
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    cache_dir = repo_cache_dir(repo)
+    previous_meta = (cache_dir / "engine_state.meta.json").read_bytes()
+    previous_registry = engine.registry.create_checkpoint()
+    previous_engine = mcp_runtime._live_engines[str(repo.resolve())]
+    authority = _local_lease_manager(repo)
+    domain = authority.domain
+
+    if authority_state in {"active", "transport_failure_with_active_lease"}:
+        authority.acquire()
+    elif authority_state in {
+        "reserved", "active_missing_lease", "fenced", "mismatched_generation"
+    }:
+        lease = authority.acquire()
+        if authority_state == "reserved":
+            with authority._lock():
+                authority._write_generation(
+                    replace(authority._read_generation(), status="reserved")
+                )
+        elif authority_state == "active_missing_lease":
+            live_lease_path(domain).unlink()
+        elif authority_state == "fenced":
+            authority.fence_owner(lease)
+        else:
+            with authority._lock():
+                authority._write_generation(
+                    replace(
+                        authority._read_generation(),
+                        last_service_instance_id="different-service",
+                    )
+                )
+    elif authority_state == "malformed_generation":
+        generation_metadata_path(domain).write_text("{broken", encoding="utf-8")
+    elif authority_state == "malformed_lease":
+        live_lease_path(domain).write_text("{broken", encoding="utf-8")
+    elif authority_state == "foreign_generation":
+        generation_metadata_path(domain).write_text(
+            json.dumps(replace(authority.read_generation(), repo_id="foreign-repo").to_dict()),
+            encoding="utf-8",
+        )
+    elif authority_state == "foreign_lease":
+        lease = authority.acquire()
+        live_lease_path(domain).write_text(
+            json.dumps(replace(lease, repo_id="foreign-repo").to_dict()),
+            encoding="utf-8",
+        )
+
+    # The fixture forces connect(root)=None, including the transport-failure case.
+    def forbidden(*_args, **_kwargs):
+        raise AssertionError("local mutation started despite untrusted authority")
+
+    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", forbidden)
+    monkeypatch.setattr(engine.registry, "create_checkpoint", forbidden)
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", forbidden)
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+
+    response = _local_update(repo, provider)
+
+    assert response["status"] == "ERROR"
+    assert "Local writer denied" in response["error"] or "malformed" in response["error"] or "belongs to another domain" in response["error"]
+    assert mcp_runtime._live_engines[str(repo.resolve())] is previous_engine
+    assert (cache_dir / "engine_state.meta.json").read_bytes() == previous_meta
+    assert engine.registry._state == previous_registry
+
+
+def test_local_writer_rejects_stale_revision_before_checkpoint_or_update(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    before_meta = (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes()
+    before_registry = engine.registry.create_checkpoint()
+    engine.revision = 0
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+
+    def forbidden(*_args, **_kwargs):
+        raise AssertionError("candidate or registry checkpoint began before baseline gate")
+
+    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", forbidden)
+    monkeypatch.setattr(engine.registry, "create_checkpoint", forbidden)
+    response = _local_update(repo, provider)
+
+    assert response["status"] == "ERROR"
+    assert "stale engine revision" in response["error"]
+    assert engine.registry._state == before_registry
+    assert (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes() == before_meta
+
+
+def test_local_domain_fence_blocks_live_acquire_until_persistence_finishes(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    real_persist = update_file_module._persist_live_engine
+    entered = threading.Event()
+    release = threading.Event()
+    acquired = threading.Event()
+    results = {}
+
+    def wait_in_persist(root, candidate):
+        entered.set()
+        assert release.wait(10)
+        return real_persist(root, candidate)
+
+    def acquire_live():
+        results["lease"] = _local_lease_manager(repo, lock_timeout=3).acquire()
+        acquired.set()
+
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", wait_in_persist)
+    local = threading.Thread(target=lambda: results.setdefault("local", _local_update(repo, provider)))
+    live = threading.Thread(target=acquire_live)
+    try:
+        local.start()
+        assert entered.wait(10)
+        live.start()
+        assert not acquired.wait(0.25)
+    finally:
+        release.set()
+        local.join(10)
+        live.join(10)
+
+    assert not local.is_alive() and not live.is_alive()
+    assert results["local"]["status"] == "UPDATED"
+    assert acquired.is_set()
+    assert results["lease"].lease_generation == 1
+
+
+def test_local_registry_rollback_completes_before_domain_fence_release(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    rollback_entered = threading.Event()
+    release_rollback = threading.Event()
+    acquired = threading.Event()
+    real_restore = engine.registry.restore_checkpoint
+    results = {}
+
+    def wait_in_rollback(checkpoint):
+        rollback_entered.set()
+        assert release_rollback.wait(10)
+        return real_restore(checkpoint)
+
+    def acquire_live():
+        results["lease"] = _local_lease_manager(repo, lock_timeout=3).acquire()
+        acquired.set()
+
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_args: False)
+    monkeypatch.setattr(engine.registry, "restore_checkpoint", wait_in_rollback)
+    local = threading.Thread(target=lambda: results.setdefault("local", _local_update(repo, provider)))
+    live = threading.Thread(target=acquire_live)
+    try:
+        local.start()
+        assert rollback_entered.wait(10)
+        live.start()
+        assert not acquired.wait(0.25)
+    finally:
+        release_rollback.set()
+        local.join(10)
+        live.join(10)
+
+    assert not local.is_alive() and not live.is_alive()
+    assert results["local"]["status"] == "ERROR"
+    assert acquired.is_set()
+
+
+def test_local_writer_domain_lock_timeout_preserves_state(tmp_path, monkeypatch):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    before_meta = (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes()
+    before_registry = engine.registry.create_checkpoint()
+    original_manager = RuntimeLeaseManager
+    held = _local_lease_manager(repo)
+    entered = threading.Event()
+    release = threading.Event()
+
+    def hold_lock():
+        with held._lock():
+            entered.set()
+            assert release.wait(10)
+
+    holder = threading.Thread(target=hold_lock)
+    holder.start()
+    assert entered.wait(10)
+    import contextor.core.live_state.runtime_lease as lease_module
+
+    monkeypatch.setattr(
+        lease_module,
+        "RuntimeLeaseManager",
+        lambda domain: original_manager(domain, lock_timeout=0.1),
+    )
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    try:
+        response = _local_update(repo, provider)
+    finally:
+        release.set()
+        holder.join(10)
+
+    assert response["status"] == "ERROR"
+    assert "timed out waiting for domain lock" in response["error"]
+    assert mcp_runtime._live_engines[str(repo.resolve())] is engine
+    assert engine.registry._state == before_registry
+    assert (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes() == before_meta
+
+
+def test_two_mcp_processes_cannot_enter_local_candidate_concurrently(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    extra = repo / "extra.py"
+    extra.write_text("value = 3\n", encoding="utf-8")
+    ctx = multiprocessing.get_context("spawn")
+    entered = ctx.Event()
+    release = ctx.Event()
+    ready = ctx.Event()
+    update_started = ctx.Event()
+    results = ctx.Queue()
+    cache_root = os.environ["CONTEXTOR_CACHE_DIR"]
+    first = ctx.Process(
+        target=_cross_process_local_candidate_worker,
+        args=(
+            str(repo), str(provider), cache_root, entered, release, ready,
+            update_started, results, True,
+        ),
+    )
+    second = ctx.Process(
+        target=_cross_process_local_candidate_worker,
+        args=(
+            str(repo), str(extra), cache_root, entered, release, ready,
+            update_started, results, False,
+        ),
+    )
+    try:
+        first.start()
+        assert entered.wait(15)
+        second.start()
+        assert ready.wait(15)
+        assert not update_started.wait(0.4)
+    finally:
+        release.set()
+        first.join(15)
+        if second.pid is not None:
+            second.join(15)
+        if first.is_alive():
+            first.terminate()
+            first.join(5)
+        if second.pid is not None and second.is_alive():
+            second.terminate()
+            second.join(5)
+
+    assert first.exitcode == 0
+    assert second.exitcode == 0
+    first_result = results.get(timeout=5)
+    second_result = results.get(timeout=5)
+    assert first_result["status"] == "UPDATED"
+    assert second_result["status"] in {"ERROR", "UPDATED"}
+    assert not update_started.is_set()
+    assert read_metadata(repo_cache_dir(repo)).revision == 2
+
+
 def test_local_candidate_cow_keeps_original_nested_facts_and_tracked_files(
     tmp_path, monkeypatch
 ):
```

### C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py

```diff
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index f93e3bf..1b4969b 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -2653,7 +2653,8 @@ def _real_local_update_fixture(root, monkeypatch):
     from contextor.core.paths import repo_cache_dir
 
     root = root.resolve()
-    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(root / "cache"))
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(root.parent / f"{root.name}-cache"))
+    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(root.parent / f"{root.name}-state"))
     state = RepositoryAnalysisState(
         modules={},
         artifacts={},
```

## FINAL_VERDICT

**TARGETED_CODE_PASS_WITH_RUNTIME_RELOAD_PENDING.** Literal production patch is in place, required targeted tests are green, source sync was verified after production edit, and LIVE continuity through revision 222 is continuous with resync_required=false. Serving-process implementation remains uncertified until manual MCP reload and a separate runtime check.


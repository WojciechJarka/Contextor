STATUS=IMPLEMENTED_TARGETED_TESTS_PASS_RUNTIME_CERTIFICATION_PENDING
HEAD_BEFORE=b2c1855d7aa55c1e80d34725f7b9c64f338da557
HEAD_AFTER=b2c1855d7aa55c1e80d34725f7b9c64f338da557
WORKTREE_STATE_BEFORE=CLEAN
WORKTREE_STATE_AFTER=only the four listed production/test files and walkthrough.md modified

LIVE_REVISION_BEFORE=1599
LIVE_REVISION_AFTER=1604
LIVE_EVENT_CONTINUITY=continuous; resync_required=false
LIVE_WATCHER_EVENTS=1600 persistent_registry.py UPDATED; 1601 runtime.py UPDATED; 1602 test_persistent_registry.py UPDATED; 1603 test_live_mutation_coordinator.py UPDATED; 1604 test_live_mutation_coordinator.py UNCHANGED
MCP_UPDATE_FILE_CALLED=NO

IMPLEMENTATION_RESULT
- PersistentIdentityRegistry.create_checkpoint returns a detached deepcopy of every registry family. restore_checkpoint validates the domain and family shapes, then restores the exact snapshot through the existing transaction.
- The production updater creates the registry and checkpoint before the real incremental engine update, retains both in adapter_holder through a successful updater return, and restores/clears them if updater raises.
- The production persister restores the checkpoint only when save_snapshot raises before durable commit. SnapshotRevisionConflict keeps its existing CanonicalPersistenceConflict mapping. A rollback failure propagates with current_revision=exact_revision-1.
- After save_snapshot returns and the exact revision is verified, the checkpoint is discarded before persisted_state and trace publication. A post-save revision mismatch also clears the transient checkpoint without rolling back a committed snapshot.
- No IPC, snapshot-store, revision, ID-allocation, or schema code was changed.

ROOT_CAUSE
- Before this change, _apply_delta_and_commit committed PersistentIdentityRegistry before _repository_persister called save_snapshot. A generic save failure left the registry at the new generation while CanonicalLiveServer retained the old canonical state/revision and emitted no resync gate. The earlier temporary-repository probe proved that durable mismatch.
- The compensating checkpoint spans that existing updater/persister boundary without moving the snapshot commit or changing CanonicalLiveServer.

FILES_CHANGED
- contextor/core/reporting_engine/persistent_registry.py
- contextor/core/live_state/runtime.py
- tests/test_persistent_registry.py
- tests/test_live_mutation_coordinator.py
- walkthrough.md is the report and is excluded from the production/test file list.

NEW_TESTS
- tests/test_persistent_registry.py::test_checkpoint_restore_persists_exact_registry_state
- tests/test_live_mutation_coordinator.py::test_generic_snapshot_failure_restores_committed_registry_and_old_canonical_state

TARGETED_TEST_RESULTS
- Exact seven requested node IDs ran in one focused pytest command; result: 7 passed in 3.43s, exit code 0.
- New registry checkpoint/restore test: PASS.
- New real updater + real registry + CanonicalLiveServer generic snapshot failure regression: PASS.
- tests/test_persistent_registry.py::test_identity_preservation: PASS.
- tests/test_persistent_registry.py::test_write_transaction_allocates_and_persists_missing_ids: PASS.
- tests/test_lineage_state_lifecycle.py::test_identity_sync_revalidation_failure_rolls_back_registry_and_canonical_state: PASS.
- tests/test_live_mutation_coordinator.py::test_persistence_failure_leaves_canonical_state_revision_journal_and_diagnostics_unchanged: PASS.
- tests/test_live_mutation_coordinator.py::test_candidate_is_invisible_during_slow_persistence: PASS.
- Full repository pytest suite was not run.
- git diff --check passed.

CROSS_STORE_DIVERGENCE_REGRESSION=PASS
ON_GENERIC_SNAPSHOT_FAILURE: canonical=OLD (revision 1; modules ["seed"]); registry=OLD (added module/artifact inactive); event=NONE (activity_seq 0; no update event).
- The regression observes identity_sync_required=True and sees the added module/artifact IDs durably active when save_snapshot is entered, before its injected OSError. It then verifies fresh disk registry state equals the baseline after rollback.
- The new test would fail against the prior implementation because added remained active in the registry after the generic persistence failure.

REGISTRY_EXACT_ROLLBACK=PASS
- Fresh registry after rollback has unchanged seed IDs and no added module or artifact ID.
- module_registry, artifact_registry, module_recovery, artifact_recovery, module_slots, artifact_slots, and output_references equal the deep-copied baseline exactly.
- The registry unit test mutates both slot-generation maps and output references after checkpoint creation, then proves exact restoration from a newly constructed registry.

FRESH_HYDRATION_RESULT=PASS
- A separate Python process hydrated the persisted snapshot and a fresh PersistentIdentityRegistry from the temporary repository.
- Snapshot source and canonical modules=["seed"]; fresh registry lookup for added module ID and added artifact ID both returned null.
- This proves OLD canonical + OLD registry for the tested failure boundary.

CONTEXTOR_POST_EDIT_SOURCE_VERIFICATION
- Contextor LIVE revision 1604 reported canonical_state=fresh for both production modules.
- get_symbol_implementation returned create_checkpoint, restore_checkpoint, _clear_registry_checkpoint, _restore_registry_checkpoint, _repository_updater, and _repository_persister from current source with workspace_sync=verified at revision 1604.
- get_module_blast_radius reported 25 registry artifacts (23 before) and 41 runtime artifacts (39 before). get_file_edit_context reported no warnings and retained direct/transitive consumer counts of 58/190 and 15/68 respectively.
- These results verify current indexed source and architecture. They do not certify that the already running LIVE/MCP backend loaded the edited runtime code.

MCP_SERVER_RESTART_REQUIRED=YES
DESKTOP_RUNTIME_RESTART_REQUIRED=YES

UNKNOWN
- Fresh-runtime behavior after the user manually restarts Contextor remains uncertified; the running backend predates the runtime.py edit.
- No full-suite certification was requested or run.
- No restart was performed.

FULL_DIFFS_BEGIN
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 506d3ce..a617e30 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -1075,6 +1075,30 @@ def _repository_canonical_query_handler(
     )
 
 
+def _clear_registry_checkpoint(
+    holder: dict[str, object] | None,
+) -> None:
+    if holder is None:
+        return
+    holder.pop("registry", None)
+    holder.pop("registry_checkpoint", None)
+
+
+def _restore_registry_checkpoint(
+    holder: dict[str, object] | None,
+) -> None:
+    if holder is None:
+        return
+
+    registry = holder.get("registry")
+    checkpoint = holder.get("registry_checkpoint")
+
+    if registry is None or checkpoint is None:
+        return
+
+    registry.restore_checkpoint(checkpoint)
+
+
 def _repository_updater(root: Path, holder: dict[str, object] | None = None):
     identity = require_repository_identity(root)
     cache = repo_cache_dir(root)
@@ -1088,15 +1112,29 @@ def _repository_updater(root: Path, holder: dict[str, object] | None = None):
         from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 
         manager = FileStateManager(str(cache))
+        registry = PersistentIdentityRegistry(str(root))
+        registry_checkpoint = registry.create_checkpoint()
+
+        if holder is not None:
+            holder["registry"] = registry
+            holder["registry_checkpoint"] = registry_checkpoint
+
         engine = IncrementalAnalysisEngine(
             state,
-            PersistentIdentityRegistry(str(root)),
+            registry,
             manager,
             str(root),
         )
         _safe_trace_event("LIVE", "ENGINE_READY", op=op, repo=str(root), elapsed_ms=(time.monotonic() - started) * 1000.0)
         incremental_started = time.monotonic()
-        delta = engine.update_file(file_path)
+        try:
+            delta = engine.update_file(file_path)
+        except Exception:
+            try:
+                registry.restore_checkpoint(registry_checkpoint)
+            finally:
+                _clear_registry_checkpoint(holder)
+            raise
         _safe_trace_event("LIVE", "INCREMENTAL_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - incremental_started) * 1000.0, status=getattr(delta, "status", None))
         if holder is not None:
             holder["manager"] = manager
@@ -1159,35 +1197,18 @@ def _repository_persister(
                 ),
                 previous_state=persisted_state,
             )
-
-            if meta.revision != exact_revision:
-                raise ValueError(
-                    "Exact LIVE persistence revision mismatch."
-                )
-
-            persisted_state = state
-
-            _safe_trace_event(
-                "LIVE",
-                "SNAPSHOT_SAVE_END",
-                op=op,
-                repo=str(root),
-                elapsed_ms=(
-                    time.monotonic()
-                    - snapshot_started
+        except Exception as exc:
+            try:
+                _restore_registry_checkpoint(holder)
+            except Exception as rollback_exc:
+                failure = RuntimeError(
+                    "Canonical snapshot persistence failed and registry rollback failed."
                 )
-                * 1000.0,
-            )
-
-            _safe_trace_event(
-                "LIVE",
-                "FILE_STATE_SAVE_END",
-                op=op,
-                repo=str(root),
-                elapsed_ms=0.0,
-            )
+                failure.current_revision = exact_revision - 1
+                raise failure from rollback_exc
+            finally:
+                _clear_registry_checkpoint(holder)
 
-        except Exception as exc:
             from contextor.core.live_state.store import SnapshotRevisionConflict
 
             if isinstance(exc, SnapshotRevisionConflict):
@@ -1198,6 +1219,36 @@ def _repository_persister(
 
             raise
 
+        try:
+            if meta.revision != exact_revision:
+                raise ValueError(
+                    "Exact LIVE persistence revision mismatch."
+                )
+        finally:
+            _clear_registry_checkpoint(holder)
+
+        persisted_state = state
+
+        _safe_trace_event(
+            "LIVE",
+            "SNAPSHOT_SAVE_END",
+            op=op,
+            repo=str(root),
+            elapsed_ms=(
+                time.monotonic()
+                - snapshot_started
+            )
+            * 1000.0,
+        )
+
+        _safe_trace_event(
+            "LIVE",
+            "FILE_STATE_SAVE_END",
+            op=op,
+            repo=str(root),
+            elapsed_ms=0.0,
+        )
+
         return meta
 
     return persist
diff --git a/contextor/core/reporting_engine/persistent_registry.py b/contextor/core/reporting_engine/persistent_registry.py
index d4e90d9..c7644a5 100644
--- a/contextor/core/reporting_engine/persistent_registry.py
+++ b/contextor/core/reporting_engine/persistent_registry.py
@@ -3,6 +3,7 @@ import json
 import sys
 import uuid
 import datetime
+from copy import deepcopy
 from contextlib import contextmanager
 from pathlib import Path
 from typing import Dict, Any, List, Set, Optional
@@ -261,6 +262,56 @@ class PersistentIdentityRegistry:
             self._in_transaction = False
             self._unlock()
 
+    def create_checkpoint(self) -> Dict[str, Any]:
+        """
+        Capture the exact currently loaded persistent registry state for
+        compensating rollback by the canonical mutation coordinator.
+
+        The checkpoint is a detached deep copy and includes active mappings,
+        recovery maps, slot generations, and output references.
+        """
+        if self._in_transaction:
+            raise RuntimeError(
+                "Cannot create registry checkpoint inside an active transaction."
+            )
+
+        return deepcopy(self._state)
+
+    def restore_checkpoint(
+        self,
+        checkpoint: Dict[str, Any],
+    ) -> None:
+        """
+        Restore an exact previously captured registry state transactionally.
+        """
+        if self._in_transaction:
+            raise RuntimeError(
+                "Cannot restore registry checkpoint inside an active transaction."
+            )
+
+        if not isinstance(checkpoint, dict):
+            raise TypeError("Registry checkpoint must be a dictionary.")
+
+        expected_keys = set(self.files)
+        if set(checkpoint) != expected_keys:
+            raise ValueError(
+                "Registry checkpoint does not match the persistent registry domain."
+            )
+
+        restored = deepcopy(checkpoint)
+
+        for key in expected_keys:
+            if not isinstance(restored.get(key), dict):
+                raise ValueError(
+                    f"Registry checkpoint family '{key}' must be a dictionary."
+                )
+
+        if self._state == restored:
+            return
+
+        with self.transaction():
+            self._state = restored
+
     @contextmanager
     def read_transaction(self):
         """Load one recovered registry generation without committing it."""
diff --git a/tests/test_live_mutation_coordinator.py b/tests/test_live_mutation_coordinator.py
index f2829e0..9f28934 100644
--- a/tests/test_live_mutation_coordinator.py
+++ b/tests/test_live_mutation_coordinator.py
@@ -564,6 +564,147 @@ def test_persistence_failure_leaves_canonical_state_revision_journal_and_diagnos
         )
 
 
+def test_generic_snapshot_failure_restores_committed_registry_and_old_canonical_state(
+    tmp_path, monkeypatch
+):
+    import copy
+    import json
+    import os
+    import subprocess
+    import sys
+    from pathlib import Path
+
+    import contextor.core.analysis.incremental.engine as incremental_module
+    import contextor.core.live_state.runtime as runtime_module
+    from contextor.core.analysis.state_manager import RepositoryAnalysisState
+    from contextor.core.live_state.runtime import _repository_persister, _repository_updater
+    from contextor.core.live_state.store import read_metadata
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    monkeypatch.setenv("CONTEXTOR_REGISTRY_DIR", str(tmp_path / "registry"))
+    PersistentIdentityRegistry(str(repo))
+
+    seed_path = repo / "seed.py"
+    seed_path.write_text("SEED_VALUE = 1\n", encoding="utf-8")
+    state = RepositoryAnalysisState()
+    holder = {}
+    updater = _repository_updater(repo, holder)
+    assert updater(state, str(seed_path)).status == "UPDATED"
+    state.revision = 1
+    assert _repository_persister(repo, holder)(state, 1).revision == 1
+    assert "registry" not in holder
+    assert "registry_checkpoint" not in holder
+
+    baseline = copy.deepcopy(PersistentIdentityRegistry(str(repo))._state)
+    added_path = repo / "added.py"
+    added_path.write_text("ADDED_VALUE = 2\n", encoding="utf-8")
+
+    plan_results = []
+
+    def capture_incremental_phase(name, **fields):
+        if name == "INCREMENTAL_EXECUTE_PLAN_END":
+            plan_results.append(fields.get("result"))
+
+    monkeypatch.setattr(
+        incremental_module, "_trace_incremental_phase", capture_incremental_phase
+    )
+
+    observed_commit = {}
+
+    def fail_snapshot_save(*_args, **kwargs):
+        assert kwargs["exact_revision"] == 2
+        committed = PersistentIdentityRegistry(str(repo))
+        observed_commit["module_id"] = committed.get_module_id("added")
+        observed_commit["artifact_id"] = committed.get_artifact_id(
+            "added::ADDED_VALUE"
+        )
+        assert observed_commit["module_id"] is not None
+        assert observed_commit["artifact_id"] is not None
+        assert read_metadata(repo_cache_dir(repo)).revision == 1
+        raise OSError("controlled cross-store atomicity regression failure")
+
+    monkeypatch.setattr(runtime_module, "save_snapshot", fail_snapshot_save)
+    server = CanonicalLiveServer(
+        state,
+        revision=1,
+        updater=updater,
+        persister=_repository_persister(repo, holder, previous_state=state),
+    )
+    with _running_server(server) as client:
+        accepted = client.submit_update_file(
+            str(added_path), origin="test", idempotency_key="cross-store-rollback"
+        )
+        terminal = _wait_for_terminal(client, accepted["job_id"])
+        assert terminal["state"] == "failed"
+        assert terminal["response"] == {
+            "status": "error",
+            "error": "canonical_persistence_failed",
+            "revision": 1,
+            "expected_revision": 2,
+        }
+        assert server._state is state
+        assert server._revision == 1
+        assert sorted(server._state.modules) == ["seed"]
+        assert server._activity_seq == 0
+        assert client.get_events(after_revision=1)["events"] == []
+
+    assert any("identity_sync_required=True" in (result or "") for result in plan_results)
+    assert observed_commit["module_id"] is not None
+    assert observed_commit["artifact_id"] is not None
+    assert read_metadata(repo_cache_dir(repo)).revision == 1
+    assert "registry" not in holder
+    assert "registry_checkpoint" not in holder
+
+    reloaded = PersistentIdentityRegistry(str(repo))
+    assert reloaded.get_module_id("seed") == baseline["module_registry"]["path_to_id"]["seed"]
+    assert reloaded.get_artifact_id("seed::SEED_VALUE") == baseline["artifact_registry"]["path_to_id"]["seed::SEED_VALUE"]
+    assert reloaded.get_module_id("added") is None
+    assert reloaded.get_artifact_id("added::ADDED_VALUE") is None
+    assert reloaded._state["module_registry"] == baseline["module_registry"]
+    assert reloaded._state["artifact_registry"] == baseline["artifact_registry"]
+    assert reloaded._state["module_recovery"] == baseline["module_recovery"]
+    assert reloaded._state["artifact_recovery"] == baseline["artifact_recovery"]
+    assert reloaded._state["module_slots"] == baseline["module_slots"]
+    assert reloaded._state["artifact_slots"] == baseline["artifact_slots"]
+    assert reloaded._state["output_references"] == baseline["output_references"]
+
+    child_code = """
+import json
+import sys
+from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+root = sys.argv[1]
+hydrated = hydrate_repository_engine(root)
+registry = PersistentIdentityRegistry(root)
+print(json.dumps({
+    "source": hydrated.source if hydrated else None,
+    "modules": sorted(hydrated.engine.state.modules) if hydrated else None,
+    "added_module_id": registry.get_module_id("added"),
+    "added_artifact_id": registry.get_artifact_id("added::ADDED_VALUE"),
+}))
+"""
+    child = subprocess.run(
+        [sys.executable, "-c", child_code, str(repo)],
+        cwd=str(Path(__file__).resolve().parents[1]),
+        env=os.environ.copy(),
+        text=True,
+        capture_output=True,
+        check=True,
+        timeout=10,
+    )
+    hydrated = json.loads(child.stdout.strip().splitlines()[-1])
+    assert hydrated == {
+        "source": "snapshot",
+        "modules": ["seed"],
+        "added_module_id": None,
+        "added_artifact_id": None,
+    }
+
+
 def test_worker_survives_failed_job_and_executes_next_job():
     first_started = threading.Event()
 
diff --git a/tests/test_persistent_registry.py b/tests/test_persistent_registry.py
index 394d01c..7d603e2 100644
--- a/tests/test_persistent_registry.py
+++ b/tests/test_persistent_registry.py
@@ -14,6 +14,48 @@ def temp_repo(tmp_path):
     yield str(repo_dir)
     shutil.rmtree(repo_dir, ignore_errors=True)
 
+def test_checkpoint_restore_persists_exact_registry_state(temp_repo):
+    registry = PersistentIdentityRegistry(temp_repo)
+    with registry.transaction():
+        registry.sync_with_workspace({"seed"}, {"seed::SEED_VALUE"})
+        registry.register_report_references(
+            "baseline.json", [registry.get_module_id("seed")]
+        )
+
+    checkpoint = registry.create_checkpoint()
+    seed_id = registry.get_module_id("seed")
+    seed_artifact_id = registry.get_artifact_id("seed::SEED_VALUE")
+
+    with registry.transaction():
+        registry.sync_with_workspace(
+            {"seed", "added"},
+            {"seed::SEED_VALUE", "added::ADDED_VALUE"},
+        )
+        registry.register_report_references(
+            "added.json", [registry.get_module_id("added")]
+        )
+
+    assert registry.get_module_id("added") is not None
+    assert registry.get_artifact_id("added::ADDED_VALUE") is not None
+    assert registry._state["module_slots"] != checkpoint["module_slots"]
+    assert registry._state["artifact_slots"] != checkpoint["artifact_slots"]
+    assert registry._state["output_references"] != checkpoint["output_references"]
+
+    registry.restore_checkpoint(checkpoint)
+    reloaded = PersistentIdentityRegistry(temp_repo)
+
+    assert reloaded.get_module_id("seed") == seed_id
+    assert reloaded.get_artifact_id("seed::SEED_VALUE") == seed_artifact_id
+    assert reloaded.get_module_id("added") is None
+    assert reloaded.get_artifact_id("added::ADDED_VALUE") is None
+    assert reloaded._state["module_registry"] == checkpoint["module_registry"]
+    assert reloaded._state["artifact_registry"] == checkpoint["artifact_registry"]
+    assert reloaded._state["module_recovery"] == checkpoint["module_recovery"]
+    assert reloaded._state["artifact_recovery"] == checkpoint["artifact_recovery"]
+    assert reloaded._state["module_slots"] == checkpoint["module_slots"]
+    assert reloaded._state["artifact_slots"] == checkpoint["artifact_slots"]
+    assert reloaded._state["output_references"] == checkpoint["output_references"]
+
 def test_identity_preservation(temp_repo):
     # nowy plik dostaje ID
     registry = PersistentIdentityRegistry(temp_repo)
FULL_DIFFS_END

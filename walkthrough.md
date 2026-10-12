# CONTEXTOR_B0G2D6A_PHASE_TRACE_TEST_DOUBLE_CONTRACT_FIX

## FILES_CHANGED
- C:\Temp\Contextor_Repo\tests\test_incremental_phase_trace.py — only changed source/test file.
- C:\Temp\Contextor_Repo\walkthrough.md — current report only, excluded from source/test changed files.
No production edits. Prepatch worktree was clean; HEAD 03285e72fcd59eb69cfae807a18e511a9199f072.

## SOURCE_PRECHECK
DIRECT_EVIDENCE: Contextor MCP first, including deferred get_symbol_implementation. Complete current symbols FakeRegistry, FakeStateManager, _candidate, _run, FileStateManager.update_state, PersistentIdentityRegistry.restore_checkpoint and IncrementalAnalysisEngine._failed_commit_guard were retrieved. All relevant responses showed workspace_sync=verified. Exact auditor anchors present. Before edit LIVE revision 372, continuity continuous, resync_required=false. HEAD changed since previous task through an external auto-commit; prepatch worktree was clean, and the current code contract still matched. No source mismatch.

## FAKE_STATE_MANAGER_CONTRACT
Added _state mapping, deterministic FileState creation at resolved source path on update_state, and get_tracked_sha256 returning its SHA or empty string. Synthetic 64-zero SHA remains confined to this test double. Production FileStateManager unchanged.

## FAKE_REGISTRY_CHECKPOINT_CONTRACT
Added detached deepcopy create_checkpoint and deepcopy restore_checkpoint to FakeRegistry. Existing transaction, read_transaction, sync_with_workspace and omit logic unchanged. Identity-sync success/failure tests now assert one checkpoint; lineage failure asserts the mapping is restored to empty.

## SYNTHETIC_REFRESH_PLAN_CONTRACT
_run now supplies SimpleNamespace(patch_families=("identity_registry",)) by default and empty tuple only for the non-identity case. It preserves every original production call argument and explicitly marks the non-identity invocation. This matches each monkeypatched PlanExecutionOutcome's identity_sync_required value.

## CANDIDATE_FIELD_COMPATIBILITY
_candidate now includes layer_information={} directly after artifacts={}. All other candidate fields are unchanged.

## ORIGINAL_PHASE_TRACE_ASSERTIONS
Preserved phase order, missing owner diagnostic, lineage failure propagation, registry skip, FileState acknowledgement and no-repair checks. Added Mock observation of checkpoint counts and successful FileState acknowledgement paths; no xfail, skip or exception suppression.

## PHASE_TRACE_RESULTS
First required run: .venv\Scripts\python.exe -m pytest -q -s tests/test_incremental_phase_trace.py
4 passed in 0.61s, exit 0.

## ATOMICITY_RED_TO_GREEN_RECHECK
Unchanged tests/test_incremental_failed_commit_atomicity.py: 4 passed, 1 dependency warning in 11.19s, exit 0. A-D retained state object identity and no differences across canonical projection, FileState, manifest, registry and generation metadata after injected failure.

## REAL_FOUR_WAY_PARITY_RECHECK
The real tests/test_desktop_mcp_live_incremental_parity.py was included in the exact B0G2D6 selection. Its node passed; all 26 selected tests passed. The test used isolated fixture repositories, not a FULL analysis of Contextor_Repo.

## OTHER_TARGETED_REGRESSIONS
Re-ran the exact B0G2D6 targeted selection: three required files (incremental consumer/manifest, incremental layer report, real Desktop/MCP LIVE incremental parity) plus selected module add/delete, semantic no-op, registry identity, phase trace, COW and LIVE persistence conflict nodes. 26 passed, 1 dependency AuthlibDeprecationWarning in 41.54s, exit 0. No full repository pytest suite.

## PY_COMPILE
.venv\Scripts\python.exe -m py_compile tests\test_incremental_phase_trace.py: PASS, exit 0.

## GIT_DIFF_CHECK
git diff --check: PASS, exit 0. Git printed only an LF-to-CRLF conversion warning, no whitespace errors.

## LIVE_REVISION_BEFORE_AFTER
372 -> 373. One continuous desktop_watcher update_file UPDATED event for C:\Temp\Contextor_Repo\tests\test_incremental_phase_trace.py. No manual update_file, restart or production analysis.

## WORKSPACE_SYNC_POSTCHECK
Contextor get_symbol_implementation of FakeStateManager: complete source, workspace_sync=verified, canonical revision 373. This verifies indexed source parity, not process imported-code reload.

## RESYNC_REQUIRED
false after change; event continuity continuous.

## RESTART_REQUIRED
No restart for this test-only correction. The earlier B0G2D6 production engine edit still needs manual serving-process reload before runtime certification. No restart performed here.

## FINAL_VERDICT
B0G2D6A_ALL_TARGETED_REGRESSIONS_PASS. The previously failing phase-trace fixtures now implement the required current production contract; the unchanged atomicity tests and real four-way parity gate pass. This is targeted validation only, not global Contextor FINAL PASS. STOP; await proceduj.

## FULL_DIFFS
Complete actual diff of C:\Temp\Contextor_Repo\tests\test_incremental_phase_trace.py:

```diff
diff --git a/tests/test_incremental_phase_trace.py b/tests/test_incremental_phase_trace.py
index 48071f3..4f28715 100644
--- a/tests/test_incremental_phase_trace.py
+++ b/tests/test_incremental_phase_trace.py
@@ -1,10 +1,17 @@
 from contextlib import contextmanager
+from copy import deepcopy
 from importlib import import_module
+from pathlib import Path
 from types import SimpleNamespace
+from unittest.mock import Mock
 
 import pytest
 
-from contextor.core.analysis.state_manager import FileDelta, RepositoryAnalysisState
+from contextor.core.analysis.state_manager import (
+    FileDelta,
+    FileState,
+    RepositoryAnalysisState,
+)
 
 
 engine_module = import_module("contextor.core.analysis.incremental.engine")
@@ -17,6 +24,12 @@ class FakeRegistry:
             "artifact_registry": {"path_to_id": {}},
         }
 
+    def create_checkpoint(self):
+        return deepcopy(self._state)
+
+    def restore_checkpoint(self, checkpoint):
+        self._state = deepcopy(checkpoint)
+
     @contextmanager
     def transaction(self):
         yield
@@ -34,15 +47,29 @@ class FakeRegistry:
 class FakeStateManager:
     def __init__(self):
         self.paths = []
+        self._state = {}
 
     def update_state(self, path):
         self.paths.append(path)
+        self._state[str(Path(path).resolve())] = FileState(
+            mtime_ns=0,
+            size=0,
+            sha256="0" * 64,
+        )
+
+    def get_tracked_sha256(self, path):
+        entry = self._state.get(
+            str(Path(path).resolve())
+        )
+        return entry.sha256 if entry is not None else ""
 
 
 def _candidate():
     return SimpleNamespace(
         modules={}, reexport_facts_by_module={},
-        artifacts={}, module_parse_freshness={},
+        artifacts={},
+        layer_information={},
+        module_parse_freshness={},
         syntax_diagnostics_by_path={}, syntax_diagnostics_state="fresh",
         dependency_graph=None, metrics={}, topology_analytics={},
         cached_analytics={}, dependency_matrix={}, dependency_matrix_state="deferred",
@@ -97,11 +124,31 @@ def _capture(monkeypatch):
     return events
 
 
-def _run(engine, delta, *, extracted_lineage_facts="facts"):
+def _run(
+    engine,
+    delta,
+    *,
+    extracted_lineage_facts="facts",
+    identity_sync_required=True,
+):
+    patch_families = (
+        ("identity_registry",)
+        if identity_sync_required
+        else ()
+    )
     return engine._apply_delta_and_commit(
-        "target.py", delta, None, SimpleNamespace(), [], {}, None,
+        "target.py",
+        delta,
+        None,
+        SimpleNamespace(
+            patch_families=patch_families,
+        ),
+        [],
+        {},
+        None,
         extracted_lineage_facts=extracted_lineage_facts,
-        syntax_source_path="target.py", syntax_fact={"status": "checked_and_none"},
+        syntax_source_path="target.py",
+        syntax_fact={"status": "checked_and_none"},
         clear_parse_module="target",
     )
 
@@ -113,6 +160,8 @@ def _names(events):
 def test_identity_sync_success_emits_order_and_no_missing_owners(monkeypatch):
     events = _capture(monkeypatch)
     registry = FakeRegistry()
+    checkpoint = Mock(wraps=registry.create_checkpoint)
+    monkeypatch.setattr(registry, "create_checkpoint", checkpoint)
     engine = _engine(registry)
     candidate = _candidate()
     monkeypatch.setattr(
@@ -132,11 +181,16 @@ def test_identity_sync_success_emits_order_and_no_missing_owners(monkeypatch):
     ]
     assert events[3][1]["count"] == 0
     assert lineage_calls == [{"source_path": "target.py", "extracted_lineage_facts": "facts", "delete": False, "rematerialize_all": True}]
+    assert checkpoint.call_count == 1
+    assert engine.state_manager.paths == ["target.py"]
 
 
 def test_identity_sync_lineage_failure_propagates_without_file_state(monkeypatch):
     events = _capture(monkeypatch)
-    engine = _engine(FakeRegistry())
+    registry = FakeRegistry()
+    checkpoint = Mock(wraps=registry.create_checkpoint)
+    monkeypatch.setattr(registry, "create_checkpoint", checkpoint)
+    engine = _engine(registry)
     candidate = _candidate()
     monkeypatch.setattr(
         engine_module, "execute_refresh_plan",
@@ -158,11 +212,16 @@ def test_identity_sync_lineage_failure_propagates_without_file_state(monkeypatch
     ]
     assert events[-1][1]["error"] == "owner-failure"
     assert engine.state_manager.paths == []
+    assert checkpoint.call_count == 1
+    assert registry._state["artifact_registry"]["path_to_id"] == {}
 
 
 def test_non_identity_path_emits_skip_and_default_lineage_scope(monkeypatch):
     events = _capture(monkeypatch)
-    engine = _engine(FakeRegistry())
+    registry = FakeRegistry()
+    checkpoint = Mock(wraps=registry.create_checkpoint)
+    monkeypatch.setattr(registry, "create_checkpoint", checkpoint)
+    engine = _engine(registry)
     candidate = _candidate()
     monkeypatch.setattr(
         engine_module, "execute_refresh_plan",
@@ -171,7 +230,11 @@ def test_non_identity_path_emits_skip_and_default_lineage_scope(monkeypatch):
     lineage_calls = []
     engine._update_candidate_lineage_slice = lambda *_args, **kwargs: lineage_calls.append(kwargs)
 
-    _run(engine, FileDelta(module_path="target"))
+    _run(
+        engine,
+        FileDelta(module_path="target"),
+        identity_sync_required=False,
+    )
 
     names = _names(events)
     assert "INCREMENTAL_REGISTRY_SYNC_SKIP" in names
@@ -179,6 +242,8 @@ def test_non_identity_path_emits_skip_and_default_lineage_scope(monkeypatch):
     assert "INCREMENTAL_REGISTRY_SYNC_END" not in names
     assert lineage_calls == [{"source_path": "target.py", "extracted_lineage_facts": "facts", "delete": False}]
     assert names[-2:] == ["INCREMENTAL_FILE_STATE_START", "INCREMENTAL_FILE_STATE_END"]
+    assert checkpoint.call_count == 0
+    assert engine.state_manager.paths == ["target.py"]
 
 
 def test_registry_diagnostic_gap_is_observed_without_repair_or_raise(monkeypatch):
```

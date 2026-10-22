# CONTEXTOR_CYCLE_PROOF_P1C1_FOCUSED_REPAIR

## TASK
Apply the auditor-supplied patch only to the three approved files. No redesign, FULL analysis, process restart, or manual update_file.

## HEAD_BEFORE
66454eba26c62d7f6437d675cbd5fa35eabbe1ae. Working tree clean before this task.

## HEAD_AFTER
66454eba26c62d7f6437d675cbd5fa35eabbe1ae. No commit created.

## FILES_CHANGED
- contextor/core/analysis/state_manager.py
- contextor/core/live_state/store.py
- tests/test_cycle_semantics_publication_binding.py

## ROOT_CAUSE_FIX_SPLIT_LINEAGE
CODE_PATH_PROVED: prior save_snapshot sealed a receipt into state_to_persist, then passed the original state to _write_split_lineage_generation, discarding the sealed copy. The exact patch passes state_to_persist. T01/T03/T04/T05/T06/T08 and T12 passed after the patch.

## DATACLASS_COMPATIBILITY
CONTRACT_PROVED: cycle_source_publication is a ClassVar and initialized as an instance __dict__ attribute in __post_init__. T11 confirms it is absent from dataclasses.fields, present on new instances, preserved by pickle, and falls back to None when absent from an old unpickled state. Existing constructor compatibility test passed. The positional dataclass constructor contract is unchanged.

## T01_T14_RESULTS
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_publication_binding.py
Actual result: 14 passed in 3.56s; exit 0. T01–T14 each passed.

## FOCUSED_NON_REGRESSION
Constructor command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_canonical_state.py::test_existing_constructor_compatibility
Actual: 1 passed in 0.61s; exit 0.
Focused command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_canonical_state.py tests/test_cycle_semantics_invalidation.py tests/test_cycle_semantics_evidence.py tests/test_live_state_store.py
Actual: 175 passed in 42.37s; exit 0.
py_compile on all three changed files: exit 0.
git diff --check: exit 0; Git printed only working-tree LF/CRLF conversion warnings.

## COMMIT_ROLLBACK_RECOVERY
CONTRACT_PROVED by T01–T14: original caller state retains no receipt after failed commit; metadata commit failure preserves prior generation; COW clears receipt on new candidate without mutating prior state; old receipt is not republished into a new generation. No runtime SAFE classification or ArchitectureCycle suppression was added.

## LEGACY_AND_NON_SPLIT_LOAD
CONTRACT_PROVED: T12 confirms a non-split canonical snapshot commits and verifies a receipt. T13 verifies wrapped snapshot tampering clears it. T14 verifies the legacy raw-payload loader branch clears a tampered receipt. The load path now verifies embedded receipts against metadata before returning them.

## LIVE_REVISION_BEFORE_AFTER
Before: 643. After: 646. Contextor get_live_events(after_revision=643) returned continuity=continuous, resync_required=false, total=3.

## WATCHER_EVENTS
644 desktop_watcher update_file UPDATED state_manager.py; blast_radius_state=fresh, affected_modules.total=254.
645 desktop_watcher update_file UPDATED store.py; blast_radius_state=deferred in that event.
646 desktop_watcher update_file UPDATED test_cycle_semantics_publication_binding.py; blast_radius_state=fresh, affected_modules.total=1.
Post-edit Contextor module blast radius resolved store.py with 47 artifacts at revision 646. Its direct static consumers include state_manager, facade, LIVE hydration/runtime, MCP runtime and tools, Desktop GUI, and tests; dynamic reachability is not claimed complete.

## WORKSPACE_SYNC
Sequential Contextor get_module_context at revision 646: state_manager.py=verified, store.py=verified, test_cycle_semantics_publication_binding.py=verified; canonical_state=fresh, advisory_warning=null, resync_required=false from events. Cycle_semantics family remains stale; no semantic safety certification is claimed. An earlier concurrent query while watcher revisions advanced was unverified and one call reported resource deadlock avoided; final sequential queries resolved these transient query results.

## RESTART_REQUIREMENTS
REQUIRED_MANUAL_RESTART_BEFORE_RUNTIME_CERTIFICATION for processes that loaded state_manager.py or store.py. No process restarted by agent. LIVE watcher indexing and focused tests do not prove loaded-code adoption in existing runtime.

## FULL_DIFFS
Complete actual unified diff for the three files changed in this task follows.
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 0278ded..4c557c9 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -2,7 +2,7 @@ import os
 import json
 import copy
 from dataclasses import dataclass, field, fields
-from typing import Dict, Any, Optional
+from typing import Dict, Any, Optional, ClassVar
 from pathlib import Path
 
 from contextor.core.cycle_semantics.contracts import (
@@ -133,8 +133,16 @@ class RepositoryAnalysisState:
     cycle_semantics: CycleSemanticsSnapshot | None = None
     cycle_semantics_state: str = "deferred"
     cycle_semantics_invalidation_reason: str | None = None
-    # Optional durable receipt. Never a runtime SAFE certificate.
-    cycle_source_publication: Any = None
+    # An instance-level publication receipt, deliberately excluded
+    # from dataclass fields and constructor compatibility.
+    # ClassVar also supplies None for old unpickled states in
+    # which the instance attribute is absent.
+    cycle_source_publication: ClassVar[Any] = None
+
+    def __post_init__(self) -> None:
+        # Persisted as an ordinary instance __dict__ attribute,
+        # not as a dataclass field.
+        self.cycle_source_publication = None
 
     def clone_for_update(self) -> "RepositoryAnalysisState":
         """
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index cd4b541..41bcce2 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -1786,7 +1786,7 @@ def save_snapshot(
                 state_to_persist,
                 generation_lineage_chunks,
             ) = _write_split_lineage_generation(
-                state,
+                state_to_persist,
                 generation_lineage_manifest,
                 state_id=metadata.state_id,
                 revision=metadata.revision,
@@ -2467,6 +2467,27 @@ def load_snapshot(
                     setattr(payload, "shared_usage_clusters_state", "deferred")
                 except AttributeError:
                     pass
+        # Legacy raw-payload snapshots are not produced by the
+        # current canonical writer. Never trust an embedded receipt
+        # merely because unpickling succeeded.
+        if getattr(
+            payload,
+            "cycle_source_publication",
+            None,
+        ) is not None:
+            from contextor.core.cycle_semantics.publication_binding import (
+                verify_co_published_cycle_manifest,
+            )
+
+            if not verify_co_published_cycle_manifest(
+                payload,
+                revision=metadata.revision,
+                state_id=metadata.state_id,
+                repo_id=metadata.repo_id,
+                root_path=metadata.root_path,
+            ):
+                payload.cycle_source_publication = None
+
         return payload, metadata
 
 
diff --git a/tests/test_cycle_semantics_publication_binding.py b/tests/test_cycle_semantics_publication_binding.py
index ae10d77..43037cb 100644
--- a/tests/test_cycle_semantics_publication_binding.py
+++ b/tests/test_cycle_semantics_publication_binding.py
@@ -269,3 +269,134 @@ def test_p1c1_t10_legacy_missing_receipt_is_unavailable():
         repo_id="",
         root_path="",
     )
+
+
+def test_p1c1_t11_receipt_does_not_extend_dataclass_fields():
+    from dataclasses import fields
+
+    state = RepositoryAnalysisState()
+    field_names = tuple(
+        item.name
+        for item in fields(RepositoryAnalysisState)
+    )
+
+    assert "cycle_source_publication" not in field_names
+    assert "cycle_source_publication" in state.__dict__
+    assert state.cycle_source_publication is None
+
+    restored = pickle.loads(pickle.dumps(state))
+    assert restored.cycle_source_publication is None
+
+    del restored.__dict__["cycle_source_publication"]
+    assert restored.cycle_source_publication is None
+
+
+def test_p1c1_t12_non_split_snapshot_commits_receipt(tmp_path):
+    state, prepared = _case()
+
+    metadata = save_snapshot(
+        state,
+        tmp_path,
+        "cycle-state",
+        prepared_cycle_manifest=prepared,
+    )
+
+    assert metadata.revision == 1
+    assert metadata.lineage_manifest_file == ""
+    assert state.cycle_source_publication is None
+
+    loaded, loaded_metadata = load_snapshot(
+        tmp_path,
+        "cycle-state",
+    )
+
+    assert loaded_metadata == metadata
+    assert isinstance(
+        loaded.cycle_source_publication,
+        CanonicalCycleManifestReceipt,
+    )
+    assert verify_co_published_cycle_manifest(
+        loaded,
+        revision=metadata.revision,
+        state_id=metadata.state_id,
+        repo_id=metadata.repo_id,
+        root_path=metadata.root_path,
+    )
+
+
+def test_p1c1_t13_non_split_wrapped_tamper_fails_closed(
+    tmp_path,
+):
+    state, prepared = _case()
+
+    metadata = save_snapshot(
+        state,
+        tmp_path,
+        "cycle-state",
+        prepared_cycle_manifest=prepared,
+    )
+
+    state_file = tmp_path / "engine_state.pkl"
+    payload = pickle.loads(state_file.read_bytes())
+
+    receipt = payload["state"].cycle_source_publication
+    assert isinstance(
+        receipt,
+        CanonicalCycleManifestReceipt,
+    )
+
+    payload["state"].cycle_source_publication = replace(
+        receipt,
+        revision=999,
+    )
+    state_file.write_bytes(pickle.dumps(payload))
+
+    loaded, loaded_metadata = load_snapshot(
+        tmp_path,
+        "cycle-state",
+    )
+
+    assert loaded_metadata.revision == metadata.revision
+    assert loaded.cycle_source_publication is None
+
+
+def test_p1c1_t14_legacy_raw_payload_tamper_fails_closed(
+    tmp_path,
+):
+    state, prepared = _case()
+
+    metadata = save_snapshot(
+        state,
+        tmp_path,
+        "cycle-state",
+        prepared_cycle_manifest=prepared,
+    )
+
+    state_file = tmp_path / "engine_state.pkl"
+    wrapped = pickle.loads(state_file.read_bytes())
+    legacy_state = wrapped["state"]
+
+    receipt = legacy_state.cycle_source_publication
+    assert isinstance(
+        receipt,
+        CanonicalCycleManifestReceipt,
+    )
+
+    legacy_state.cycle_source_publication = replace(
+        receipt,
+        revision=999,
+    )
+
+    # Exercise the legacy raw-payload loader branch rather
+    # than the modern metadata-wrapped branch.
+    state_file.write_bytes(
+        pickle.dumps(legacy_state)
+    )
+
+    loaded, loaded_metadata = load_snapshot(
+        tmp_path,
+        "cycle-state",
+    )
+
+    assert loaded_metadata.revision == metadata.revision
+    assert loaded.cycle_source_publication is None

## FINAL_VERDICT
PASS for exact patch and focused acceptance gates. Runtime loaded-code certification remains pending required manual restart.

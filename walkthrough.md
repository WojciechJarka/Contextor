# CPA10L4_REPOSITORY_STATE_STRUCTURAL_CLONE

## STATUS

STATUS=BLOCKED

The literal edit and required syntax gate completed. The required first targeted test gate failed (3 failed, 4 passed). Per task instructions, no implementation correction and no targeted regression set were run after the failures.

Source change is misplaced: clone_for_update was inserted into AnalysisResult, not RepositoryAnalysisState. The live update helper therefore still falls back to deepcopy for RepositoryAnalysisState. This is directly visible in the full diff and confirmed by the test failures. No source or test edits were made after the failing gate.

## BASELINE

Discovery CPA10L3 baseline supplied by the user:

CLONE_BASELINE_PRIMARY_MS=28036
CLONE_BASELINE_SECONDARY_MS=29714

No clone benchmark was run in this task.

## FILES_CHANGED

- C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py
- C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py
- C:\Temp\Contextor_Repo\walkthrough.md (this report)

Only the two user-allowed source/test paths were changed. No IPC, runtime, engine, materialization, planner, store, schema, persistence, or other source/test/docs file was changed. FULL_DIFFS below contains the complete actual diff for both changed source/test files. The walkthrough report itself is excluded from source/test FULL_DIFFS.

## IMPLEMENTATION_RESULT

SOURCE_DRIFT_GATE=PASS

Before editing, Contextor at canonical revision 1361 reported workspace_sync=verified for both allowed files. Contextor confirmed RepositoryAnalysisState had no clone_for_update method, and its class ended with trie: Optional[Any] = None and package_root: str = "". The required dataclasses import and FileStateManager test import anchors were present. Contextor fetched _clone_state_for_update and confirmed it still calls a callable clone_for_update or otherwise copy.deepcopy. Its direct caller was CanonicalLiveServer._execute_update_file.

The literal import changes, requested method text, test import, and four test bodies were applied. However, state_manager.py contains another identical trie/package_root anchor in AnalysisResult before RepositoryAnalysisState. The patch matched that earlier pair, placing clone_for_update inside AnalysisResult. The actual RepositoryAnalysisState still lacks the method. This is the observed implementation failure; no correction was made after the test gate failed.

PY_COMPILE=PASS

Exact command:
.venv\Scripts\python.exe -m py_compile contextor\core\analysis\state_manager.py tests\test_live_state_ipc.py

CLONE_CONTRACT_TESTS=FAIL
TARGETED_TESTS=FAIL

Exact required first-gate command ran with all seven requested node IDs. Result: 3 failed, 4 passed in 3.83s.

Failed tests and exact failure evidence:
1. test_repository_analysis_state_clone_for_update_detaches_all_top_level_mutable_fields
   AttributeError: 'RepositoryAnalysisState' object has no attribute 'clone_for_update'
2. test_live_clone_uses_repository_structural_clone_without_deepcopying_nested_values
   _clone_state_for_update fell through to copy.deepcopy(state); nested NoDeepcopy raised AssertionError: nested canonical value must not be deep-copied.
3. test_repository_structural_clone_success_keeps_previous_top_level_state_untouched
   The candidate mapping had a deep-copied existing object. Assertion comparing server._state.module_usages with {"existing": existing_usage, "new": {}} failed because the existing object identity differed.

Passed tests in that command:
- test_repository_structural_clone_isolates_top_level_updater_failure
- test_update_clone_failure_uses_update_fail_not_publish_fail
- test_persister_runs_after_validation_before_canonical_exposure
- test_persistence_conflict_fails_closed_without_live_event

The successful-update test confirmed the prior state mapping itself remained unchanged before failing its candidate nested-object identity assertion. The required structural-sharing behavior is therefore not satisfied.

TARGETED_REGRESSION_SET=NOT_RUN_AFTER_GATE_FAILURE
FULL_SUITE_RUN=NO

## STRUCTURAL_CLONE_CONTRACT

The requested RepositoryAnalysisState behavior is not implemented.

CUSTOM_CLONE_METHOD_IMPLEMENTED=NO
DEEPCOPY_FALLBACK_USED_FOR_REPOSITORY_STATE=YES

Observed effective clone behavior for RepositoryAnalysisState remains:
- OUTER_STATE_OBJECT_SHARED=NO
- DECLARED_TOP_LEVEL_DICT_SHARED=NO
- DECLARED_TOP_LEVEL_LIST_SHARED=NO
- DECLARED_TOP_LEVEL_SET_SHARED=NO
- NESTED_VALUES_DEEPCOPIED=YES
- NESTED_VALUES_STRUCTURALLY_SHARED=NO
- DYNAMIC_RUNTIME_ATTRIBUTES_PRESERVED=YES

The first four no/deepcopy values above describe the still-active IPC fallback, not a successful structural clone. A clone_for_update method was added to AnalysisResult by mistake; it does not affect the RepositoryAnalysisState path.

## TRANSACTION_ISOLATION

UPDATER_FAILURE_PRIOR_STATE_PRESERVED=YES
SUCCESSFUL_UPDATE_PRIOR_STATE_PRESERVED=YES

These values describe current in-memory isolation through the unchanged deepcopy fallback. The updater-failure test passed, and the successful-update test confirmed the original state mapping remained unchanged before failing the required structural nested-reference sharing assertion.

CANONICAL_STATE_SCHEMA_CHANGED=NO
PERSISTENCE_CHANGED=NO
IPC_TRANSACTION_ORDER_CHANGED=NO

## TARGETED_TEST_RESULTS

PY_COMPILE=PASS
CLONE_CONTRACT_TESTS=FAIL
TARGETED_TESTS=FAIL
FULL_SUITE_RUN=NO

No tests were run after the first-gate failure. The regression file set and full repository suite were not run.

## CONTEXTOR_VERIFICATION

After changes, bounded Desktop LIVE checks observed:
- state_manager.py: workspace_sync=verified at canonical revision 1362; syntax errors=0.
- test_live_state_ipc.py: workspace_sync=verified at canonical revision 1363; syntax errors=0.
- LIVE update events: state_manager.py UPDATED at revision 1362; test_live_state_ipc.py UPDATED at revision 1363. Event continuity remained continuous and resync_required=false.
- Direct get_name_collisions at revision 1363: availability=fresh, matched=0, returned=0.
- Fresh diagnostics summary: NAME_COLLISIONS=0, SYNTAX_ERRORS=0, CYCLES=0.

WORKSPACE_SYNC=verified (state_manager.py revision 1362; test_live_state_ipc.py revision 1363)
NAME_COLLISIONS=0
SYNTAX_ERRORS=0
CYCLES=0

No update_file, recovery full analysis, or clone timing measurement was used.

## FULL_DIFFS

### C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py

~~~diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 197ebf8..3bc6dcf 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -1,6 +1,7 @@
 import os
 import json
-from dataclasses import dataclass, field
+import copy
+from dataclasses import dataclass, field, fields
 from typing import Dict, Any, Optional
 from pathlib import Path
 
@@ -73,6 +74,45 @@ class AnalysisResult:
     report_header: Dict[str, Any]
     trie: Optional[Any] = None
     package_root: str = ""
+
+    def clone_for_update(self) -> "RepositoryAnalysisState":
+        """
+        Create an execution-local LIVE update candidate using structural
+        top-level Copy-On-Write.
+
+        The outer state object is shallow-copied so dynamic runtime
+        attributes such as revision, provenance, state_id, and
+        resync_required are preserved on the candidate without sharing
+        the state holder itself.
+
+        Every declared top-level dict/list/set field receives its own
+        shallow container. Nested values remain structurally shared and
+        continue to rely on the existing family-level Copy-On-Write
+        contracts in the incremental pipeline.
+        """
+        candidate = copy.copy(self)
+
+        for state_field in fields(self):
+            value = getattr(
+                self,
+                state_field.name,
+            )
+
+            if isinstance(
+                value,
+                (
+                    dict,
+                    list,
+                    set,
+                ),
+            ):
+                setattr(
+                    candidate,
+                    state_field.name,
+                    copy.copy(value),
+                )
+
+        return candidate
     collision_facts: Optional[Dict[str, Any]] = None
     live_publish_status: str = "not_attempted"
     live_publish_revision: Optional[int] = None
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index ed280b6..b060f96 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -20,7 +20,10 @@ from contextor.core.live_state.ipc import LIVE_PROTOCOL_VERSION
 from contextor.core.live_state import ipc as ipc_module
 from contextor.core.live_state.runtime import EndpointSchemaError, connect_or_start, endpoint_file
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
-from contextor.core.analysis.state_manager import FileStateManager
+from contextor.core.analysis.state_manager import (
+    FileStateManager,
+    RepositoryAnalysisState,
+)
 from contextor.core.paths import repo_cache_dir
 from contextor.core.domain.validation import ValidationError
 
@@ -707,6 +710,235 @@ def test_update_clone_failure_uses_update_fail_not_publish_fail(monkeypatch):
     assert not any(args[1] == "PUBLISH_FAIL" for args, _kwargs in events)
 
 
+def test_repository_analysis_state_clone_for_update_detaches_all_top_level_mutable_fields():
+    nested_artifact = object()
+    nested_cycle = object()
+
+    state = RepositoryAnalysisState()
+    state.artifacts["pkg.mod"] = nested_artifact
+    state.cycles.append(nested_cycle)
+
+    state.revision = 17
+    state.provenance = "live"
+    state.state_id = "state-17"
+    state.resync_required = True
+
+    candidate = state.clone_for_update()
+
+    assert candidate is not state
+
+    for field_name in state.__dataclass_fields__:
+        original_value = getattr(
+            state,
+            field_name,
+        )
+        candidate_value = getattr(
+            candidate,
+            field_name,
+        )
+
+        if isinstance(
+            original_value,
+            (
+                dict,
+                list,
+                set,
+            ),
+        ):
+            assert candidate_value is not original_value
+            assert candidate_value == original_value
+
+    assert candidate.artifacts[
+        "pkg.mod"
+    ] is nested_artifact
+
+    assert candidate.cycles[
+        0
+    ] is nested_cycle
+
+    assert candidate.revision == 17
+    assert candidate.provenance == "live"
+    assert candidate.state_id == "state-17"
+    assert candidate.resync_required is True
+
+    candidate.revision = 18
+    candidate.provenance = "candidate"
+    candidate.state_id = "state-18"
+    candidate.resync_required = False
+
+    assert state.revision == 17
+    assert state.provenance == "live"
+    assert state.state_id == "state-17"
+    assert state.resync_required is True
+
+
+def test_live_clone_uses_repository_structural_clone_without_deepcopying_nested_values():
+    class NoDeepcopy:
+        def __deepcopy__(
+            self,
+            _memo,
+        ):
+            raise AssertionError(
+                "nested canonical value must not be deep-copied"
+            )
+
+    nested = NoDeepcopy()
+
+    state = RepositoryAnalysisState(
+        artifacts={
+            "pkg.mod": nested,
+        },
+    )
+
+    candidate = ipc_module._clone_state_for_update(
+        state
+    )
+
+    assert candidate is not state
+    assert candidate.artifacts is not state.artifacts
+    assert candidate.artifacts[
+        "pkg.mod"
+    ] is nested
+
+
+def test_repository_structural_clone_isolates_top_level_updater_failure():
+    existing_usage = object()
+
+    state = RepositoryAnalysisState(
+        module_usages={
+            "existing": existing_usage,
+        },
+        module_parse_freshness={
+            "existing": {
+                "state": "fresh",
+            },
+        },
+    )
+
+    original_module_usages = state.module_usages
+    original_parse_freshness = (
+        state.module_parse_freshness
+    )
+
+    def updater(
+        candidate,
+        _path,
+    ):
+        candidate.module_usages[
+            "new"
+        ] = {}
+
+        candidate.module_parse_freshness[
+            "new"
+        ] = {
+            "state": "stale",
+        }
+
+        candidate.artifact_consumption_state = (
+            "stale"
+        )
+
+        raise RuntimeError(
+            "synthetic updater failure"
+        )
+
+    server = CanonicalLiveServer(
+        state,
+        updater=updater,
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="^synthetic updater failure$",
+    ):
+        server._dispatch(
+            {
+                "operation": "update_file",
+                "file_path": "pkg/change.py",
+            }
+        )
+
+    assert server._state is state
+    assert server._revision == 0
+
+    assert state.module_usages is (
+        original_module_usages
+    )
+    assert state.module_parse_freshness is (
+        original_parse_freshness
+    )
+
+    assert state.module_usages == {
+        "existing": existing_usage,
+    }
+
+    assert state.module_parse_freshness == {
+        "existing": {
+            "state": "fresh",
+        },
+    }
+
+    assert (
+        state.artifact_consumption_state
+        == "deferred"
+    )
+
+
+def test_repository_structural_clone_success_keeps_previous_top_level_state_untouched():
+    existing_usage = object()
+
+    state = RepositoryAnalysisState(
+        module_usages={
+            "existing": existing_usage,
+        },
+    )
+
+    original_module_usages = state.module_usages
+
+    def updater(
+        candidate,
+        _path,
+    ):
+        candidate.module_usages[
+            "new"
+        ] = {}
+
+        return {
+            "status": "UPDATED",
+        }
+
+    server = CanonicalLiveServer(
+        state,
+        updater=updater,
+    )
+
+    response = server._dispatch(
+        {
+            "operation": "update_file",
+            "file_path": "pkg/change.py",
+        }
+    )
+
+    assert response[
+        "revision"
+    ] == 1
+
+    assert server._state is not state
+
+    assert state.module_usages is (
+        original_module_usages
+    )
+
+    assert state.module_usages == {
+        "existing": existing_usage,
+    }
+
+    assert server._state.module_usages == {
+        "existing": existing_usage,
+        "new": {},
+    }
+
+
 def test_persister_runs_after_validation_before_canonical_exposure():
     observed = []
     initial_state = SimpleNamespace(files=[])
~~~

## CHECKPOINT_LITERALS

STATUS=BLOCKED
CUSTOM_CLONE_METHOD_IMPLEMENTED=NO
DEEPCOPY_FALLBACK_USED_FOR_REPOSITORY_STATE=YES
OUTER_STATE_OBJECT_SHARED=NO
DECLARED_TOP_LEVEL_DICT_SHARED=NO
DECLARED_TOP_LEVEL_LIST_SHARED=NO
DECLARED_TOP_LEVEL_SET_SHARED=NO
NESTED_VALUES_DEEPCOPIED=YES
NESTED_VALUES_STRUCTURALLY_SHARED=NO
DYNAMIC_RUNTIME_ATTRIBUTES_PRESERVED=YES
UPDATER_FAILURE_PRIOR_STATE_PRESERVED=YES
SUCCESSFUL_UPDATE_PRIOR_STATE_PRESERVED=YES
CANONICAL_STATE_SCHEMA_CHANGED=NO
PERSISTENCE_CHANGED=NO
IPC_TRANSACTION_ORDER_CHANGED=NO
PY_COMPILE=PASS
CLONE_CONTRACT_TESTS=FAIL
TARGETED_TESTS=FAIL
FULL_SUITE_RUN=NO
CLONE_BASELINE_PRIMARY_MS=28036
CLONE_BASELINE_SECONDARY_MS=29714
CLONE_PERFORMANCE_MEASURED_IN_THIS_TASK=NO
WORKSPACE_SYNC=verified (state_manager.py revision 1362; test_live_state_ipc.py revision 1363)
NAME_COLLISIONS=0
SYNTAX_ERRORS=0
CYCLES=0
CODE_CHANGED=YES
TEST_CODE_CHANGED=YES
FIX_DESIGNED_BY_AGENT=NO
GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO

STOP=WAITING_FOR_PROCEDUJ

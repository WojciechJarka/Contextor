# CONTEXTOR_B0G2D7C3_IMPLEMENTATION_AFTER_APPROVED_PRECHECK

FINAL_VERDICT=B0G2D7C3_NEXT_FILESTATE_OR_CANONICAL_MISMATCH

## FILES_CHANGED
FILES_CHANGED=
- contextor/core/analysis/state_manager.py
- contextor/core/reporting_engine/pipeline.py
- tests/test_full_file_state_domain_reconciliation.py

walkthrough.md is the requested report artifact and is excluded from FILES_CHANGED. No other source, test, or documentation file was modified.

## SOURCE_PRECHECK
SOURCE_PRECHECK=PASS (approved in prior stage).
CURRENT_HEAD_BEFORE_EDIT=07b975a824b6cb8c492fea1faf92de5cea80b69a
WORKING_TREE_BEFORE_EDIT=CLEAN
The approved source anchors were present at this HEAD. The diff from the prior precheck HEAD to the current HEAD contained no changes to state_manager.py, pipeline.py, facade.py, or indexer.py. Current Contextor LIVE revision before edit was 384, continuity=continuous, resync_required=false.

## FULL_FILESTATE_ROOT_CAUSE
CODE_PATH_PROVED: FileStateManager loads the previous persisted file domain. FULL execute_global_pipeline updated current module paths but did not remove obsolete tracked paths before save. Facade then built the canonical snapshot FileState payload from that manager. The prior supplied Case B evidence identified beta/consumer.py as the extra tracked path.

## RETAIN_TRACKED_PATHS_IMPLEMENTATION
The exact approved retain_tracked_paths(current_paths: set[str]) method was inserted immediately after tracked_paths. It validates the complete domain before deleting absent keys from the existing _state mapping. It performs no I/O and does not persist implicitly.

## AUTHORITATIVE_MODULE_DOMAIN
execute_global_pipeline now collects str(absolute_path) for the same current modules passed to update_state, then calls retain_tracked_paths before the existing state_mgr.save. The current indexer worker paths are str(path.resolve()), matching update_state's key representation. Snapshot publication order was unchanged.

## OLD_GENERATION_IMMUTABILITY
FOCUSED_TEST_PASS: After a second FULL with beta/consumer.py removed, the test checked bytes and mtime_ns of every old referenced engine, FileState, lineage manifest, and lineage chunk file. All were unchanged.

## FULL_DELETION_RECONCILIATION
FOCUSED_TEST_PASS: The second real FULL on the same isolated repository/cache advanced snapshot revision, removed beta/consumer.py from canonical modules and persisted FileState, retained exactly four current source paths, matched every current disk SHA-256, and hydrated FileStateManager with baseline_status=trusted. No phantom tracked path remained.

## NOOP_FULL_REANALYSIS
FOCUSED_TEST_PASS: Two FULL analyses of an unchanged isolated fixture retained the exact five-file domain and the same SHA-256 values, with an advancing revision.

## STALE_TRACKED_ENTRY_CASE
FOCUSED_TEST_PASS: A controlled, metadata-consistent FileState generation in an isolated cache contained an obsolete nonexistent path. The next FULL removed that entry and persisted the exact current indexed domain.

## FOCUSED_TEST_RESULTS
COMMAND=.venv\Scripts\python.exe -m pytest -q -x -s tests/test_full_file_state_domain_reconciliation.py
RESULT=9 passed in 13.59s; exit code 0.
The tests cover RAM-only retention, invalid-domain fail-closed validation, real deletion FULL, unchanged FULL, and a controlled stale baseline. No FULL analysis of Contextor_Repo was performed.

## SIX_MUTATION_MATRIX_RESULTS
COMMAND=.venv\Scripts\python.exe -m pytest -q -x -s tests/test_incremental_multi_mutation_full_parity.py
RESULT=4 passed, 1 failed, 1 warning in 26.56s; exit code 1; stopped by -x at Case E.
The matrix source and comparator were unchanged.

## CASE_A_STATUS
PASS.

## CASE_B_STATUS
PASS. The unchanged matrix checks the deleted-path status and exact canonical/FileState coverage; after deletion, incremental FileState and fresh FULL FileState each have four current paths, no missing or extra path, and no SHA mismatch. The 36-field canonical projection matched.

## CASES_C_TO_F_STATUS
C=PASS
D=PASS
E=FAIL at CANONICAL_STATE
F=NOT RUN because -x stopped at E.

## FIRST_MISMATCH_IF_ANY
SCENARIO=E, reexport retarget of alpha/__init__.py.
EXPECTED_UPDATE_STATUS=UPDATED
ACTUAL_UPDATE_STATUS=UPDATED
UPDATE_EXCEPTION=None
MISMATCH_KIND=CANONICAL_STATE
FIRST_DIFFERENCE_PATH=state.artifacts[{'kind': 'primitive', 'type': 'builtins.str', 'value': 'alpha.__init__'}][{'kind': 'primitive', 'type': 'builtins.str', 'value': 'consumers'}][{'kind': 'primitive', 'type': 'builtins.str', 'value': 'api_function'}][{'kind': 'primitive', 'type': 'builtins.str', 'value': 'usage'}][{'kind': 'primitive', 'type': 'builtins.str', 'value': 'direct_calls_detail'}].<length>
INCREMENTAL_VALUE=0
FRESH_FULL_VALUE=1
INCREMENTAL_FILESTATE=5 expected / 5 tracked; missing=[], extra=[], sha256_mismatches=[].
FRESH_FULL_FILESTATE=5 expected / 5 tracked; missing=[], extra=[], sha256_mismatches=[].
No cause interpretation or next repair was attempted.

## PRESERVED_EVIDENCE
EVIDENCE_DIRECTORY=C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-580\test_case_e_reexport_retarget_0\b0g2d7a_e_evidence
- initial_full.pickle: 20192 bytes
- incremental.pickle: 21426 bytes
- fresh_full.pickle: 21533 bytes
- summary.json: 4860 bytes
The evidence directory and its four files were inspected read-only and left in place. summary.json records the exact first structural difference and both FileState coverage results. No further mutation scenario or regression suite was executed.

## FOUR_WAY_PARITY_IF_EXECUTED
NOT EXECUTED: Case E stopped the six-mutation gate.

## ATOMICITY_RECHECK_IF_EXECUTED
NOT EXECUTED: Case E stopped the six-mutation gate.

## OTHER_TARGETED_REGRESSIONS
NOT EXECUTED: Desktop/MCP canonical parity, LIVE incremental parity, failure atomicity, layer report parity, collision code parity, and further FileState persistence tests require all six matrix scenarios to pass. Case F and these follow-up tests were not run.

## PY_COMPILE
PASS, exit code 0:
.venv\Scripts\python.exe -m py_compile contextor/core/analysis/state_manager.py contextor/core/reporting_engine/pipeline.py tests/test_full_file_state_domain_reconciliation.py

## GIT_DIFF_CHECK
PASS: git diff --check exit code 0 for tracked source files.
PASS: explicit trailing-space/tab check found 0 affected lines among all 229 lines of the new untracked test file.
Git emitted only its LF-to-CRLF working-copy conversion advisory.

## LIVE_REVISION_BEFORE_AFTER
BEFORE=384
AFTER=387
REVISION_385=desktop_watcher UPDATED contextor/core/analysis/state_manager.py
REVISION_386=desktop_watcher UPDATED contextor/core/reporting_engine/pipeline.py
REVISION_387=desktop_watcher UPDATED tests/test_full_file_state_domain_reconciliation.py
CONTINUITY=continuous

## WORKSPACE_SYNC_POSTCHECK
workspace_sync=verified, canonical_state=fresh, canonical_revision=387 for both edited production files and the new test file, from Contextor get_file_edit_context. Syntax diagnostics checked and none for all three.

## RESYNC_REQUIRED
false at LIVE revision 387.

## RESTART_REQUIRED
YES for serving-process operational runtime certification after the production source change. No service restart was performed by the agent. Source freshness and focused pytest do not attest serving-process reload.

## SAFETY_AND_STOP
ANALYZE_PROJECT_ON_CONTEXTOR_REPO=NO
MANUAL_UPDATE_FILE=NO
SERVICE_RESTART=NO
COMMIT_RESET_CHECKOUT=NO
FULL_PYTEST_SUITE=NO
FURTHER_FIX_DESIGNED_BY_AGENT=NO
STOP_REASON=First next mismatch in unchanged matrix at Case E. Await command proceduj.

## FULL_DIFFS
ACTUAL_DIFF=Full git-style diffs for all three FILES_CHANGED follow.

~~~~diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 241902b..ab19d9f 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -472,6 +472,23 @@ class FileStateManager:
         """Return the persisted file domain used by incremental analysis."""
         return set(self._state)
 
+    def retain_tracked_paths(
+        self,
+        current_paths: set[str],
+    ) -> None:
+        """Keep only paths in the authoritative current indexed domain."""
+        if not isinstance(current_paths, set) or any(
+            not isinstance(path, str) or not path
+            for path in current_paths
+        ):
+            raise ValueError(
+                "Current indexed file domain must be a set "
+                "of nonempty absolute path strings"
+            )
+
+        for obsolete_path in set(self._state) - current_paths:
+            del self._state[obsolete_path]
+
     def update_state(self, file_path: str):
         """
         Updates the tracked state for a given file in RAM.
diff --git a/contextor/core/reporting_engine/pipeline.py b/contextor/core/reporting_engine/pipeline.py
index af166f0..2cc105e 100644
--- a/contextor/core/reporting_engine/pipeline.py
+++ b/contextor/core/reporting_engine/pipeline.py
@@ -547,6 +547,7 @@ def execute_global_pipeline(
             )
         )
     )
+    current_module_file_paths: set[str] = set()
 
     for completed, (module_id, module) in enumerate(modules.items()):
         checkpoint(
@@ -565,7 +566,13 @@ def execute_global_pipeline(
             state_mgr.update_state(
                 absolute_path
             )
+            current_module_file_paths.add(
+                str(absolute_path)
+            )
 
+    state_mgr.retain_tracked_paths(
+        current_module_file_paths
+    )
     # datestamp keeps engine_state and file_state
     # synchronized.
     state_mgr.save(
diff --git a/tests/test_full_file_state_domain_reconciliation.py b/tests/test_full_file_state_domain_reconciliation.py
new file mode 100644
index 0000000..721d62d
--- /dev/null
+++ b/tests/test_full_file_state_domain_reconciliation.py
@@ -0,0 +1,229 @@
+"""FULL FileState must describe exactly the currently indexed source domain."""
+
+from __future__ import annotations
+
+import builtins
+import hashlib
+import json
+import os
+from pathlib import Path
+
+import pytest
+
+from contextor.core.analysis.state_manager import (
+    FileState,
+    FileStateManager,
+    RepositoryAnalysisState,
+    load_engine_state,
+)
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.live_state.store import read_metadata
+from contextor.core.paths import repo_cache_dir
+
+
+SOURCES = {
+    "alpha/__init__.py": b"",
+    "alpha/api.py": b"def api_function():\n    return 1\n",
+    "beta/__init__.py": b"",
+    "beta/consumer.py": (
+        b"from alpha.api import api_function\n"
+        b"CONSUMER_RESULT = api_function()\n"
+    ),
+    "loose.py": b"LOOSE_VALUE = 0\n",
+}
+
+
+def _write_repo(root: Path) -> None:
+    root.mkdir()
+    for relative, content in SOURCES.items():
+        path = root / relative
+        path.parent.mkdir(parents=True, exist_ok=True)
+        path.write_bytes(content)
+
+
+def _source_hashes(root: Path) -> dict[str, str]:
+    return {
+        str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
+        for path in root.rglob("*.py")
+    }
+
+
+def _run_full(root: Path):
+    errors, _ = ContextorFacade.analyze_project(str(root))
+    assert not errors, f"FULL analysis failed for {root}: {errors!r}"
+
+    cache = repo_cache_dir(root)
+    metadata = read_metadata(cache)
+    assert metadata is not None
+    assert metadata.state_file and metadata.file_state_file
+
+    state = load_engine_state(
+        str(cache),
+        metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=str(root.resolve()),
+    )
+    assert isinstance(state, RepositoryAnalysisState)
+    assert state.state_id == metadata.state_id
+    assert state.revision == metadata.revision
+
+    manager = FileStateManager(str(cache))
+    assert manager.baseline_status == "trusted"
+    assert manager.state_id == metadata.state_id
+    assert manager.revision == metadata.revision
+    return state, manager, metadata
+
+
+def _assert_exact_file_state(root: Path, state, manager) -> None:
+    expected = _source_hashes(root)
+    canonical_paths = {
+        module.absolute_path
+        for module in state.modules.values()
+        if module.absolute_path
+    }
+    assert canonical_paths == set(expected)
+    assert manager.tracked_paths() == canonical_paths
+    assert {
+        path: file_state.sha256
+        for path, file_state in manager._state.items()
+    } == expected
+
+
+def test_retain_tracked_paths_restricts_ram_domain_without_io(tmp_path, monkeypatch):
+    manager = FileStateManager(str(tmp_path / "cache"))
+    first, second, obsolete = (str(tmp_path / name) for name in ("a.py", "b.py", "old.py"))
+    first_state = FileState(1, 2, "a" * 64)
+    second_state = FileState(3, 4, "b" * 64)
+    manager._state.update(
+        {first: first_state, second: second_state, obsolete: FileState(5, 6, "c" * 64)}
+    )
+    mapping = manager._state
+
+    def unexpected_io(*_args, **_kwargs):
+        pytest.fail("retain_tracked_paths attempted filesystem I/O or persistence")
+
+    with monkeypatch.context() as patch:
+        patch.setattr(builtins, "open", unexpected_io)
+        patch.setattr(os, "stat", unexpected_io)
+        patch.setattr(manager, "save", unexpected_io)
+        manager.retain_tracked_paths({first, second})
+
+    assert manager._state is mapping
+    assert manager.tracked_paths() == {first, second}
+    assert manager._state[first] is first_state
+    assert manager._state[second] is second_state
+    assert list((tmp_path / "cache").iterdir()) == []
+
+
+@pytest.mark.parametrize(
+    "invalid_domain",
+    [None, [], {""}, {42}, {Path("relative.py")}],
+)
+def test_retain_tracked_paths_rejects_invalid_domain_before_mutation(
+    tmp_path, invalid_domain
+):
+    manager = FileStateManager(str(tmp_path / "cache"))
+    manager._state.update(
+        {"first.py": FileState(1, 2, "a" * 64), "second.py": FileState(3, 4, "b" * 64)}
+    )
+    mapping = manager._state
+    original = manager._state.copy()
+
+    with pytest.raises(ValueError, match="Current indexed file domain"):
+        manager.retain_tracked_paths(invalid_domain)
+
+    assert manager._state is mapping
+    assert manager._state == original
+
+
+def test_full_after_module_deletion_reconciles_domain_and_keeps_old_generation(
+    tmp_path, monkeypatch
+):
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    root = tmp_path / "repo"
+    _write_repo(root)
+    first_state, first_manager, first_metadata = _run_full(root)
+    _assert_exact_file_state(root, first_state, first_manager)
+    assert len(first_manager._state) == 5
+
+    cache = repo_cache_dir(root)
+    old_files = [cache / first_metadata.state_file, cache / first_metadata.file_state_file]
+    if first_metadata.lineage_manifest_file:
+        manifest = cache / first_metadata.lineage_manifest_file
+        old_files.append(manifest)
+        manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
+        old_files.extend(
+            cache / entry["file"] for entry in manifest_payload["sources"].values()
+        )
+    old_generation = {
+        path: (path.read_bytes(), path.stat().st_mtime_ns)
+        for path in set(old_files)
+    }
+
+    removed = (root / "beta" / "consumer.py").resolve()
+    removed.unlink()
+    second_state, second_manager, second_metadata = _run_full(root)
+
+    assert second_metadata.revision > first_metadata.revision
+    assert str(removed) not in {
+        module.absolute_path for module in second_state.modules.values()
+    }
+    assert str(removed) not in second_manager.tracked_paths()
+    assert len(second_manager._state) == 4
+    _assert_exact_file_state(root, second_state, second_manager)
+
+    persisted = json.loads(
+        (cache / second_metadata.file_state_file).read_text(encoding="utf-8")
+    )
+    assert set(persisted["files"]) == second_manager.tracked_paths()
+    assert {
+        path: entry["sha256"] for path, entry in persisted["files"].items()
+    } == _source_hashes(root)
+    assert all(
+        path.read_bytes() == content and path.stat().st_mtime_ns == mtime_ns
+        for path, (content, mtime_ns) in old_generation.items()
+    )
+
+
+def test_unchanged_full_reanalysis_preserves_exact_domain_and_hashes(tmp_path, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    root = tmp_path / "repo"
+    _write_repo(root)
+    first_state, first_manager, first_metadata = _run_full(root)
+    _assert_exact_file_state(root, first_state, first_manager)
+    first_hashes = {
+        path: item.sha256 for path, item in first_manager._state.items()
+    }
+
+    second_state, second_manager, second_metadata = _run_full(root)
+    assert second_metadata.revision > first_metadata.revision
+    _assert_exact_file_state(root, second_state, second_manager)
+    assert second_manager.tracked_paths() == first_manager.tracked_paths()
+    assert {
+        path: item.sha256 for path, item in second_manager._state.items()
+    } == first_hashes
+
+
+def test_full_discards_controlled_stale_tracked_entry(tmp_path, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    root = tmp_path / "repo"
+    _write_repo(root)
+    first_state, first_manager, first_metadata = _run_full(root)
+    _assert_exact_file_state(root, first_state, first_manager)
+
+    cache = repo_cache_dir(root)
+    generation = cache / first_metadata.file_state_file
+    payload = json.loads(generation.read_text(encoding="utf-8"))
+    stale_path = str((root / "deleted.py").resolve())
+    assert not (root / "deleted.py").exists()
+    payload["files"][stale_path] = FileState(1, 1, "f" * 64).to_dict()
+    generation.write_text(json.dumps(payload, indent=2), encoding="utf-8")
+
+    controlled_baseline = FileStateManager(str(cache))
+    assert controlled_baseline.baseline_status == "trusted"
+    assert controlled_baseline.tracked_paths() == first_manager.tracked_paths() | {stale_path}
+
+    second_state, second_manager, second_metadata = _run_full(root)
+    assert second_metadata.revision > first_metadata.revision
+    assert stale_path not in second_manager.tracked_paths()
+    _assert_exact_file_state(root, second_state, second_manager)
~~~~

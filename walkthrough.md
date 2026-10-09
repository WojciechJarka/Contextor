# L31 exact artifact-consumption roundtrip regression

## CURRENT_HEAD
`4e15fd5c98485afea8b41f9fa784990a5f5b218f` before edits. Contextor MCP first confirmed canonical artifact_consumption owner, complete snapshot persistence/hydration path and focused test-file context at LIVE revision 124. Git confirmed exact test-file anchors and clean source state except the prior walkthrough report.

## FILES_CHANGED
- tests/test_live_state_store.py

walkthrough.md is this task report and excluded from FILES_CHANGED. No production, schema or legacy-migration code changed.

## FULL_DIFFS
Complete exact Git diff against CURRENT_HEAD for the only changed test file:

```diff
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 72853a5..b084f20 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -1,6 +1,7 @@
 """Unit and integration boundaries for the shared canonical LIVE snapshot store."""
 
 from concurrent.futures import ThreadPoolExecutor
+from copy import deepcopy
 import multiprocessing
 import os
 from pathlib import Path
@@ -10,6 +11,8 @@ from types import SimpleNamespace
 import pytest
 
 from contextor.mcp import analysis_jobs
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.analysis.state_manager import canonical_artifact_consumption_targets
 from contextor.core.live_state import (
     load_snapshot,
     migrate_legacy_snapshot,
@@ -17,16 +20,181 @@ from contextor.core.live_state import (
     save_snapshot,
     SnapshotRevisionConflict,
 )
+from contextor.core.live_state.hydration import hydrate_repository_engine
 from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
 from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
 from contextor.core.domain.usage_facts import MODULE_USAGE_FACTS_SEMANTIC_VERSION
 from contextor.core.reporting_engine.persistent_registry import (
     PersistentIdentityRegistry,
 )
+from contextor.core.repository_identity import read_repository_identity
 
 pytestmark = pytest.mark.live
 
 
+def test_artifact_consumption_exact_full_and_incremental_roundtrip(tmp_path, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    monkeypatch.setattr("contextor.core.live_state.runtime.connect", lambda _root: None)
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    a = repo / "a.py"
+    b = repo / "b.py"
+    c = repo / "c.py"
+    a.write_text(
+        "def used():\n    return 1\n\n"
+        "def spare():\n    return 2\n\n"
+        "def unused():\n    return 3\n",
+        encoding="utf-8",
+    )
+    b.write_text("from a import used\n\ndef call_b():\n    return used()\n", encoding="utf-8")
+    c.write_text(
+        "from a import used, spare\n\ndef call_c():\n    return used()\n",
+        encoding="utf-8",
+    )
+
+    errors, _ = ContextorFacade().analyze_project(str(repo))
+    assert not errors, errors
+    cache = repo_cache_dir(repo)
+    identity = read_repository_identity(repo)
+    assert identity is not None
+    metadata = read_metadata(cache)
+    assert metadata is not None
+    hydrated = hydrate_repository_engine(repo)
+    assert hydrated is not None
+    assert hydrated.source == "snapshot"
+    engine = hydrated.engine
+    state = engine.state
+    assert state.artifact_consumption_state == "fresh"
+    assert set(state.artifact_consumption) == canonical_artifact_consumption_targets(state.artifacts)
+    used_entry = state.artifact_consumption["a::used"]
+    assert set(used_entry["consumers"]) == {"b", "c"}
+    assert set(used_entry["channels"]["b"]) == {"api_imports", "direct_calls"}
+    assert set(used_entry["channels"]["c"]) == {"api_imports", "direct_calls"}
+    assert state.artifact_consumption["a::spare"]["channels"]["c"] == ["api_imports"]
+    assert state.artifact_consumption["a::unused"] == {"consumers": [], "channels": {}}
+    full_map = deepcopy(state.artifact_consumption)
+    full_marker = state.artifact_consumption_state
+
+    loaded = load_snapshot(
+        cache,
+        metadata.state_id,
+        expected_repo_id=identity.repo_id,
+        expected_root_path=identity.root_path,
+    )
+    assert loaded is not None
+    loaded_state, loaded_metadata = loaded
+    assert loaded_state.artifact_consumption == full_map
+    assert loaded_state.artifact_consumption_state == full_marker
+    missing_consumer = deepcopy(full_map)
+    missing_consumer["a::used"]["consumers"].remove("b")
+    assert loaded_state.artifact_consumption != missing_consumer
+    missing_channel = deepcopy(full_map)
+    missing_channel["a::used"]["channels"]["c"].remove("direct_calls")
+    assert loaded_state.artifact_consumption != missing_channel
+    assert loaded_state.state_id == loaded_metadata.state_id == metadata.state_id
+    assert loaded_state.revision == loaded_metadata.revision == metadata.revision
+
+    rehydrated = hydrate_repository_engine(repo)
+    assert rehydrated is not None
+    assert rehydrated.source == "snapshot"
+    assert rehydrated.engine.state.artifact_consumption == full_map
+    assert rehydrated.engine.state.artifact_consumption_state == full_marker
+    assert rehydrated.engine.state.artifact_consumption["a::unused"] == {
+        "consumers": [], "channels": {}
+    }
+
+    b.write_text("B_VALUE = 1\n", encoding="utf-8")
+    result = engine.update_file(str(b))
+    assert result.status == "UPDATED"
+    state = engine.state
+    assert state.artifact_consumption_state == "fresh"
+    assert set(state.artifact_consumption) == canonical_artifact_consumption_targets(state.artifacts)
+    updated_used = state.artifact_consumption["a::used"]
+    assert "b" not in updated_used["consumers"]
+    assert "b" not in updated_used["channels"]
+    assert "c" in updated_used["consumers"]
+    assert updated_used["channels"]["c"] == full_map["a::used"]["channels"]["c"]
+    assert state.artifact_consumption["a::spare"] == full_map["a::spare"]
+    assert state.artifact_consumption["a::unused"] == full_map["a::unused"]
+    updated_map = deepcopy(state.artifact_consumption)
+    updated_marker = state.artifact_consumption_state
+
+    next_revision = metadata.revision + 1
+    saved = save_snapshot(
+        state,
+        cache,
+        metadata.state_id,
+        writer="test-incremental-roundtrip",
+        repo_id=identity.repo_id,
+        root_path=identity.root_path,
+        exact_revision=next_revision,
+        file_state_payload=engine.state_manager.build_payload(
+            metadata.state_id, next_revision
+        ),
+    )
+    assert saved.revision == next_revision
+    assert read_metadata(cache) == saved
+    updated_loaded = load_snapshot(
+        cache,
+        metadata.state_id,
+        expected_repo_id=identity.repo_id,
+        expected_root_path=identity.root_path,
+    )
+    assert updated_loaded is not None
+    updated_state, updated_metadata = updated_loaded
+    assert updated_state.artifact_consumption == updated_map
+    assert updated_state.artifact_consumption_state == updated_marker
+    assert updated_state.state_id == updated_metadata.state_id == metadata.state_id
+    assert updated_state.revision == updated_metadata.revision == next_revision
+
+    updated_hydrated = hydrate_repository_engine(repo)
+    assert updated_hydrated is not None
+    assert updated_hydrated.source == "snapshot"
+    assert updated_hydrated.engine.state.artifact_consumption == updated_map
+    assert updated_hydrated.engine.state.artifact_consumption_state == updated_marker
+    assert set(updated_hydrated.engine.state.artifact_consumption) == (
+        canonical_artifact_consumption_targets(updated_hydrated.engine.state.artifacts)
+    )
+    assert "b" not in updated_hydrated.engine.state.artifact_consumption["a::used"]["consumers"]
+    assert "b" not in updated_hydrated.engine.state.artifact_consumption["a::used"]["channels"]
+
+
+def test_artifact_consumption_fresh_empty_roundtrip(tmp_path, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    monkeypatch.setattr("contextor.core.live_state.runtime.connect", lambda _root: None)
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    (repo / "empty.py").write_text("pass\n", encoding="utf-8")
+
+    errors, _ = ContextorFacade().analyze_project(str(repo))
+    assert not errors, errors
+    cache = repo_cache_dir(repo)
+    identity = read_repository_identity(repo)
+    assert identity is not None
+    metadata = read_metadata(cache)
+    assert metadata is not None
+    loaded = load_snapshot(
+        cache,
+        metadata.state_id,
+        expected_repo_id=identity.repo_id,
+        expected_root_path=identity.root_path,
+    )
+    assert loaded is not None
+    state, loaded_metadata = loaded
+    assert canonical_artifact_consumption_targets(state.artifacts) == set()
+    assert state.artifact_consumption == {}
+    assert state.artifact_consumption_state == "fresh"
+    assert loaded_metadata == metadata
+
+    hydrated = hydrate_repository_engine(repo)
+    assert hydrated is not None
+    assert hydrated.source == "snapshot"
+    assert hydrated.engine.state.artifact_consumption == {}
+    assert hydrated.engine.state.artifact_consumption_state == "fresh"
+
+
 def test_module_usage_manifest_roundtrips_with_repository_state(tmp_path):
     manifest={"pkg.mod":{"module_id":"pkg.mod","path":"C:/x.py","sha256":"abc","semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}}
     state=RepositoryAnalysisState(module_usages_manifest=manifest)
```

## FULL_BASELINE_CANONICAL_MAP
EXECUTED_PROOF: isolated a.py/b.py/c.py repository analyzed by real ContextorFacade, then disk-hydrated through the real production path with `source="snapshot"`. Full map captured as a detached `deepcopy`. The test proves complete target-key coverage, `artifact_consumption_state="fresh"`, `a::used` consumers exactly `{b,c}` with each consumer carrying `api_imports` and `direct_calls`, `a::spare` retaining c's `api_imports`, and `a::unused == {"consumers": [], "channels": {}}`. The test compares complete map structures, including any additional canonical target entries produced by the real analyzer. It also checks that deleting b's membership or c's `direct_calls` from a comparison copy makes it unequal to the actual loaded map.

## FULL_SAVE_LOAD_EQUALITY
EXECUTED_PROOF: real committed full-analysis generation loaded by `load_snapshot` with exact repo_id/root_path. Its complete `artifact_consumption` equals the detached baseline map and its marker equals the baseline `fresh` marker. Loaded state_id/revision equal committed metadata.

## FULL_HYDRATION_EQUALITY
EXECUTED_PROOF: second real disk hydration returned `source="snapshot"`; its complete map and marker equal the same detached baseline. Empty target entry `a::unused` remains present and empty.

## INCREMENTAL_BEFORE_AFTER
EXECUTED_PROOF: only b.py changed to `B_VALUE = 1`; real `engine.update_file` returned `UPDATED`. b disappeared from both a::used consumers and channels, while c and its channels remained. a::spare and a::unused retained their complete entries. Marker stayed `fresh`, and target-key coverage remained exact. Complete updated map and marker were captured by detached copy.

## INCREMENTAL_DURABLE_EQUALITY
EXECUTED_PROOF: updated state was saved through real `save_snapshot` in the isolated repository cache using original state_id/repo_id/root_path, next exact revision and matching real FileState payload. `read_metadata` matched the committed metadata. Real `load_snapshot` returned the entire updated mapping and marker exactly equal to the detached post-commit values, with matching state_id/revision.

## INCREMENTAL_HYDRATION_EQUALITY
EXECUTED_PROOF: post-save disk hydration returned `source="snapshot"`; complete updated mapping and marker were exactly equal to the post-commit values. Canonical target coverage remained complete, and obsolete b membership/channel did not reappear.

## FRESH_EMPTY_ROUNDTRIP
EXECUTED_PROOF: isolated empty.py containing `pass` was fully analyzed. Canonical target domain was empty; real durable `load_snapshot` returned `{}` with marker `fresh` and matching metadata. Disk hydration preserved `{}` and `fresh`, with `source="snapshot"`.

## LEGACY_COMPATIBILITY
Existing `_report` migration assertions were left unchanged. The new tests compare modern canonical mappings only; they do not require legacy `_report` payloads to equal post-hydration canonical representations.

## TARGETED_TEST_RESULTS
Final code exact-node gate: 2 passed in 4.33s.
`tests/test_live_state_store.py::test_artifact_consumption_exact_full_and_incremental_roundtrip`
`tests/test_live_state_store.py::test_artifact_consumption_fresh_empty_roundtrip`

Final code focused file gate: 124 passed in 48.23s.
`tests/test_live_state_store.py tests/test_matrix_clusters_state_lifecycle.py`

An earlier pass before the explicit negative controls also passed: 2 passed in 14.00s; file gate 124 passed in 48.86s. No full repository suite was run. `git diff --check` found no whitespace errors.

## REMAINING_LIMITATIONS
The test fixture proves exact modern mapping and marker equality for the selected full and incremental generations, including nonempty/empty targets and distinct channels. It does not exhaust every possible artifact graph or legacy schema. Disk hydration is deliberately forced by `runtime.connect` returning None for the isolated fixture; no global LIVE service was contacted or mutated.

## FINAL_VERDICT
PASS for the auditor-designed L31 evidence closure. Both new tests and the required focused regression files pass. No production code, snapshot schema, LIVE service, Desktop/MCP process, or actual Contextor repository analysis was changed or restarted.

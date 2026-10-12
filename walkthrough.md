# CONTEXTOR_B0G2D5_DIRECT_ENGINE_ATOMICITY_FAILURE_GATE

## FILES_CHANGED
- C:\Temp\Contextor_Repo\tests\test_incremental_failed_commit_atomicity.py (new test)
- C:\Temp\Contextor_Repo\walkthrough.md (report only; excluded from source/test changed files)
- No production or existing test edits. HEAD unchanged: e6d106972a4ef2eacf96dcedf1ebf90925c13367. Pre-existing change: walkthrough.md only.

## SOURCE_CONTRACTS
DIRECT_EVIDENCE: Contextor MCP first, with deferred tools and documentation. Full fetched implementations for _apply_delta_and_commit, _commit_syntax_candidate, _updated_module_usage_manifest, FileStateManager.update_state/get_tracked_sha256, PersistentIdentityRegistry.create_checkpoint/restore_checkpoint. update_file covered with nontruncated contiguous source ranges. workspace_sync=verified.
CODE_PATH_PROVED: _apply_delta_and_commit publishes self.state fields before FileState update and manifest. Registry sync can commit earlier. Parsed semantic no-op commits syntax/lineage candidate before FileState and manifest. Manifest helper raises RuntimeError on missing trusted SHA-256. Candidate derived report invokes compute_debt before publication. Contextor blast radius returned zero static direct consumers; this does not disprove the observed update_file call.

## BASELINE_IDENTITY
Four independent tmp_path/repo fixtures, each with real ContextorFacade.analyze_project and hydrate_repository_engine. Every setup checks metadata.state_id == engine.state.state_id and metadata.revision == engine.state.revision. Captured full strict B0G2C3 _state_projection with no normalization, state object identity, deepcopy FileStateManager._state, deepcopy module_usages_manifest, registry checkpoint, read_metadata, and SHA-256 for every fixture .py file. Each post-error comparison covers all domains.

## FAILURE_INJECTION_POINTS
A: added NEW_OWN_SYMBOL; update_state raises RuntimeError before FileState mutation.
B: added NEW_OWN_SYMBOL; real update_state completes; get_tracked_sha256 returns empty; expected Missing trusted source SHA-256.
C: comment-only change; real update_state completes; same missing-hash error on parsed semantic no-op.
D: pkg/__init__.py changes from empty to child = 123; compute_debt raises during RAM-only candidate report; report boundary reached, FileState acknowledgement count zero.

## CASE_A_CANONICAL_STATE
Expected injected exception. Same engine.state object, but first complete-projection difference: state.artifacts['provider']['consumers'].<key-count>: 1 -> 2. Strong assertion RED.

## CASE_A_FILESTATE_AND_REGISTRY
FileState and manifest unchanged. PersistentIdentityRegistry.artifact_registry.id_to_path.<key-count>: 2 -> 3. Metadata unchanged. One acknowledgement attempt, aborted before FileState mutation.

## CASE_B_CANONICAL_STATE
Expected missing-hash RuntimeError. Same engine.state object; first difference state.artifacts['provider']['consumers'].<key-count>: 1 -> 2. Strong assertion RED.

## CASE_B_FILESTATE_AND_REGISTRY
One real acknowledgement. FileStateManager._state[resolved provider.py].mtime_ns: 1791806796949373100 -> 1791806798606372700. Manifest unchanged, retaining prior SHA. Registry artifact_registry.id_to_path.<key-count>: 2 -> 3. Metadata unchanged.

## CASE_C_NOOP_ACKNOWLEDGEMENT
Expected missing-hash RuntimeError after one real FileState acknowledgement. Same state object; first difference state.layer_information['summary_data']['generated_at']: 2026-10-12T14:06:39.363372 -> 2026-10-12T14:06:40.597374. No extra timestamp exclusion. FileStateManager._state[resolved provider.py].mtime_ns: 1791806798828373800 -> 1791806800540373900. Manifest, registry, metadata unchanged. Strong assertion RED.

## CASE_D_PREPUBLICATION_CONTROL
PASS: expected candidate-report exception, zero FileState acknowledgements, original state object and unchanged complete projections of state, FileState, manifest, registry, generation metadata.

## ALL_OBSERVED_PARTIAL_MUTATIONS
| Case | Canonical RAM | FileState RAM | Manifest | Registry | Generation metadata |
|---|---|---|---|---|---|
| A | changed | same | same | changed | same |
| B | changed | changed | same | changed | same |
| C | changed | changed | same | same | same |
| D | same | same | same | same | same |

## PERSISTED_GENERATION_STATUS
DIRECT_EVIDENCE: read_metadata identical before/after in A-D. No newly successful generation observed. This does not imply rollback of RAM or registry.

## ATOMICITY_INVARIANT_MATRIX
A FAIL (canonical RAM, registry); B FAIL (canonical RAM, FileState, registry); C FAIL (canonical RAM, FileState); D PASS (prepublication control).

## RED_TEST_RESULTS
One execution only: .venv\Scripts\python.exe -m pytest -q -s tests/test_incremental_failed_commit_atomicity.py
3 failed, 1 passed, 1 warning in 13.47s; exit code 1. A, B, C fail at test_incremental_failed_commit_atomicity.py:130, assert state_difference is None. D passes. All intended injections reached, no fixture/setup failure. Warning: FastMCP dependency AuthlibDeprecationWarning.
A/B source provider.py SHA before ff8535360b5710dca8765a4f3eab2f2e662ac05fe190061d73723eb4b102e550, after 82698de84618b6c43b0736579902de53a455b2788f0fe1c5a671aec5810a0e23. C after c8c089c601aee3895dc35b88df47fbe8ba48922cefdbb61c48381164028d97bc. Unrelated consumer.py remained 4767310306ec8f5799757e11b85608a9ff218be72be5e7aa1add6aaad861b69e.
D pkg/__init__.py SHA e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 -> cef6f70dd4dc85da29b79fb738320d83469a80696c9a6644aba779e31d6ba67d; other source hashes unchanged.

## PY_COMPILE
.venv\Scripts\python.exe -m py_compile tests\test_incremental_failed_commit_atomicity.py: PASS, exit 0.

## GIT_DIFF_CHECK
git diff --check: PASS, exit 0. git diff --no-index --check -- NUL tests/test_incremental_failed_commit_atomicity.py: no whitespace error; exit 1 denotes differing new file. Git emitted only LF/CRLF conversion warning.

## LIVE_REVISION_BEFORE_AFTER
Before 370, continuous, resync_required=false. After 371, one desktop_watcher update_file UPDATED event for the newly created test; continuous, resync_required=false. No manual update_file or FULL Contextor_Repo analysis.

## WORKSPACE_SYNC_POSTCHECK
Contextor get_symbol_implementation for new _assert_failed_update_atomic: source complete, workspace_sync=verified, canonical revision 371.

## RESYNC_REQUIRED
false.

## RESTART_REQUIRED
No; test-only change and no restart performed.

## FINAL_VERDICT
B0G2D5_ATOMICITY_BREACH_PROVED. A-C expose partial mutation after exception; D preserves all inspected ownership domains before publication. No production fix. STOP; await proceduj.

## FULL_DIFFS
Complete actual diff of the only changed test file:

```diff
diff --git a/tests/test_incremental_failed_commit_atomicity.py b/tests/test_incremental_failed_commit_atomicity.py
new file mode 100644
index 0000000..68fde3e
--- /dev/null
+++ b/tests/test_incremental_failed_commit_atomicity.py
@@ -0,0 +1,216 @@
+"""Direct incremental-engine failure atomicity regression gate."""
+
+from __future__ import annotations
+
+import hashlib
+from copy import deepcopy
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Any
+
+import pytest
+
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.live_state.store import read_metadata
+from contextor.core.paths import repo_cache_dir
+from contextor.core.reporting_engine import debt
+from test_desktop_mcp_canonical_parity import _first_difference, _project, _state_projection
+
+
+_SOURCES = {
+    "provider.py": "PROVIDER_VALUE = 1\n",
+    "consumer.py": "from provider import PROVIDER_VALUE\nCONSUMED_VALUE = PROVIDER_VALUE\n",
+}
+
+_GRAPH_SOURCES = {
+    "pkg/__init__.py": "",
+    "pkg/child.py": "VALUE = 1\n",
+    "consumer.py": "from pkg import child\nCONSUMED_VALUE = child.VALUE\n",
+    "unrelated.py": "UNRELATED_VALUE = 2\n",
+}
+
+
+def _source_fingerprints(root: Path) -> dict[str, str]:
+    return {
+        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
+        for path in sorted(root.rglob("*.py"))
+    }
+
+
+@dataclass
+class _Baseline:
+    root: Path
+    engine: Any
+    state_object: Any
+    state_projection: dict
+    file_states: dict
+    manifest: dict
+    registry_checkpoint: dict
+    metadata: Any
+    source_fingerprints: dict[str, str]
+
+
+def _real_baseline(tmp_path: Path, sources: dict[str, str]) -> _Baseline:
+    root = tmp_path / "repo"
+    root.mkdir()
+    for relative_path, content in sources.items():
+        source_path = root / relative_path
+        source_path.parent.mkdir(parents=True, exist_ok=True)
+        source_path.write_text(content, encoding="utf-8")
+
+    errors, _ = ContextorFacade.analyze_project(str(root))
+    assert not errors, errors
+    hydrated = hydrate_repository_engine(root)
+    assert hydrated is not None
+    engine = hydrated.engine
+    metadata = read_metadata(repo_cache_dir(root))
+    assert metadata is not None
+    assert metadata.state_id == engine.state.state_id
+    assert metadata.revision == engine.state.revision
+
+    return _Baseline(
+        root=root,
+        engine=engine,
+        state_object=engine.state,
+        state_projection=_state_projection(engine.state),
+        file_states=deepcopy(engine.state_manager._state),
+        manifest=deepcopy(engine.state.module_usages_manifest),
+        registry_checkpoint=engine.registry.create_checkpoint(),
+        metadata=metadata,
+        source_fingerprints=_source_fingerprints(root),
+    )
+
+
+def _difference(before: Any, after: Any, path: str) -> tuple | None:
+    return _first_difference(_project(before, path), _project(after, path), path)
+
+
+def _assert_failed_update_atomic(baseline: _Baseline, case: str, acknowledgement_calls: int) -> None:
+    engine = baseline.engine
+    state_difference = _first_difference(
+        baseline.state_projection,
+        _state_projection(engine.state),
+    )
+    file_state_difference = _difference(
+        baseline.file_states,
+        engine.state_manager._state,
+        "FileStateManager._state",
+    )
+    manifest_difference = _difference(
+        baseline.manifest,
+        engine.state.module_usages_manifest,
+        "module_usages_manifest",
+    )
+    registry_difference = _difference(
+        baseline.registry_checkpoint,
+        engine.registry.create_checkpoint(),
+        "PersistentIdentityRegistry",
+    )
+    metadata_after = read_metadata(repo_cache_dir(baseline.root))
+    metadata_difference = _difference(
+        baseline.metadata,
+        metadata_after,
+        "persisted_generation_metadata",
+    )
+    evidence = {
+        "case": case,
+        "canonical_state_object_same": engine.state is baseline.state_object,
+        "canonical_state_first_difference": state_difference,
+        "file_state_first_difference": file_state_difference,
+        "manifest_first_difference": manifest_difference,
+        "registry_first_difference": registry_difference,
+        "persisted_generation_first_difference": metadata_difference,
+        "file_state_acknowledgement_calls": acknowledgement_calls,
+        "source_fingerprints_before": baseline.source_fingerprints,
+        "source_fingerprints_after": _source_fingerprints(baseline.root),
+    }
+    print(f"{case}_ATOMICITY_EVIDENCE={evidence!r}")
+    assert engine.state is baseline.state_object, evidence
+    assert state_difference is None, evidence
+    assert file_state_difference is None, evidence
+    assert manifest_difference is None, evidence
+    assert registry_difference is None, evidence
+    assert metadata_difference is None, evidence
+
+
+def test_failed_updated_before_file_state_acknowledgement_is_atomic(tmp_path, monkeypatch):
+    baseline = _real_baseline(tmp_path, _SOURCES)
+    source = baseline.root / "provider.py"
+    source.write_text("PROVIDER_VALUE = 1\nNEW_OWN_SYMBOL = 2\n", encoding="utf-8")
+    calls = []
+
+    def fail_before_acknowledgement(file_path):
+        calls.append(file_path)
+        raise RuntimeError("injected FileState acknowledgement failure")
+
+    monkeypatch.setattr(baseline.engine.state_manager, "update_state", fail_before_acknowledgement)
+    with pytest.raises(RuntimeError, match="injected FileState acknowledgement failure"):
+        baseline.engine.update_file(str(source))
+    assert calls == [str(source)]
+    _assert_failed_update_atomic(baseline, "CASE_A", len(calls))
+
+
+def test_failed_updated_missing_trusted_hash_is_atomic(tmp_path, monkeypatch):
+    baseline = _real_baseline(tmp_path, _SOURCES)
+    source = baseline.root / "provider.py"
+    source.write_text("PROVIDER_VALUE = 1\nNEW_OWN_SYMBOL = 2\n", encoding="utf-8")
+    update_state = baseline.engine.state_manager.update_state
+    acknowledgements = []
+
+    def acknowledge_then_continue(file_path):
+        result = update_state(file_path)
+        acknowledgements.append(file_path)
+        return result
+
+    monkeypatch.setattr(baseline.engine.state_manager, "update_state", acknowledge_then_continue)
+    monkeypatch.setattr(baseline.engine.state_manager, "get_tracked_sha256", lambda file_path: "")
+    with pytest.raises(RuntimeError, match="Missing trusted source SHA-256"):
+        baseline.engine.update_file(str(source))
+    assert acknowledgements == [str(source)]
+    _assert_failed_update_atomic(baseline, "CASE_B", len(acknowledgements))
+
+
+def test_failed_semantic_noop_acknowledgement_is_atomic(tmp_path, monkeypatch):
+    baseline = _real_baseline(tmp_path, _SOURCES)
+    source = baseline.root / "provider.py"
+    source.write_text("# comment-only change\nPROVIDER_VALUE = 1\n", encoding="utf-8")
+    update_state = baseline.engine.state_manager.update_state
+    acknowledgements = []
+
+    def acknowledge_then_continue(file_path):
+        result = update_state(file_path)
+        acknowledgements.append(file_path)
+        return result
+
+    monkeypatch.setattr(baseline.engine.state_manager, "update_state", acknowledge_then_continue)
+    monkeypatch.setattr(baseline.engine.state_manager, "get_tracked_sha256", lambda file_path: "")
+    with pytest.raises(RuntimeError, match="Missing trusted source SHA-256"):
+        baseline.engine.update_file(str(source))
+    assert acknowledgements == [str(source)]
+    _assert_failed_update_atomic(baseline, "CASE_C", len(acknowledgements))
+
+
+def test_failed_candidate_report_before_publication_is_atomic(tmp_path, monkeypatch):
+    baseline = _real_baseline(tmp_path, _GRAPH_SOURCES)
+    source = baseline.root / "pkg" / "__init__.py"
+    source.write_text("child = 123\n", encoding="utf-8")
+    update_state = baseline.engine.state_manager.update_state
+    acknowledgements = []
+    report_calls = []
+
+    def observe_acknowledgement(file_path):
+        acknowledgements.append(file_path)
+        return update_state(file_path)
+
+    def fail_candidate_report(*args, **kwargs):
+        report_calls.append((args, kwargs))
+        raise RuntimeError("injected RAM-only derived-report failure")
+
+    monkeypatch.setattr(baseline.engine.state_manager, "update_state", observe_acknowledgement)
+    monkeypatch.setattr(debt, "compute_debt", fail_candidate_report)
+    with pytest.raises(RuntimeError, match="injected RAM-only derived-report failure"):
+        baseline.engine.update_file(str(source))
+    assert report_calls, "The candidate derived-report boundary was not reached"
+    assert not acknowledgements, "FileState acknowledgement preceded candidate report failure"
+    _assert_failed_update_atomic(baseline, "CASE_D", len(acknowledgements))
```

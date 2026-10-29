# CONTEXTOR P1D3-WARN-2A-R1 — partial SCC preparation authority gate

## HEAD / WORKTREE

DIRECT_EVIDENCE: initial HEAD `965af826dd2212de2c5ad69f82601fbd3b06d549`; initial `git status --short` empty. Final HEAD unchanged. Final worktree contains only the two allowlisted Python modifications and `walkthrough.md`. The local WARN-2A files matched the supplied report, including the five-field frozen dataclass and existing T01–T08 tests; no PREFLIGHT_MISMATCH.

## ROOT CAUSE

CODE_PATH_PROVED: before R1, `prepare_original_worker_cycle_manifest` tested global digest/completeness before manifest authority, graph and ordered SCC identity. An incomplete but forged manifest could therefore place `manifest.components` into `component_preparations` under the existing P1C0 unavailable result. The issue was exposure ordering; no P0/P1B result was changed.

## EXACT VALIDATION ORDER

CODE_PATH_PROVED: immediately after `prepare_cycle_source_manifest` returns, and before partial/success return, current code now checks:
A. exact `PreparedCycleSourceManifest` type, else SOURCE_EVIDENCE_PREPARATION_FAILED;
B. authority `PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED`, else PREPARED_AUTHORITY_INVALID;
C. `manifest.graph_sha256 == snapshot.graph_sha256 == fingerprint_hard_edges(hard_edges)`, else SOURCE_MANIFEST_GRAPH_MISMATCH;
D. exact tuple of components, count matching `binding.cyclic_components`, exact `PreparedSCCSourceBinding` element types, else SCC_COMPONENT_IDENTITY_MISMATCH;
E. exact ordered component-members tuple equals binding cyclic components, else SCC_COMPONENT_IDENTITY_MISMATCH.
Only after A–E does the original global digest/prepared-state completeness check run. Existing success and partial status/reason values are unchanged. `OriginalWorkerManifestPreparation` still has the same five fields.

## AUTHORITY / GRAPH / SCC IDENTITY FAIL-CLOSED

CONTRACT_PROVED: controlled negative tests patch only `prepare_cycle_source_manifest` return, after invoking the genuine function for indexing-derived parsed sources and P0/P1B preparation. R1-T01 forged authority yields PREPARED_AUTHORITY_INVALID and empty components. R1-T02 reordered and R1-T03 missing SCC components yield SCC_COMPONENT_IDENTITY_MISMATCH and empty components. R1-T04 changed graph SHA yields SOURCE_MANIFEST_GRAPH_MISMATCH and empty components. R1-T05 list-shaped components or wrong element type yield SCC_COMPONENT_IDENTITY_MISMATCH and empty components. No failed authority/shape/identity gate exposes partial positive evidence.

## PRESERVED MIXED SCC BEHAVIOR

CONTRACT_PROVED: real unmodified PASS/INDETERMINATE preparation still returns UNAVAILABLE, P1C0_SOURCE_EVIDENCE_UNAVAILABLE, manifest=None, source_modules=(), with ordered PREPARED_UNPUBLISHED and UNAVAILABLE component records (R1-T06 and original T01). Real PASS/HAZARD preparation still succeeds with distinct classifications and manifest.components equality (R1-T07 and original T03). These are prepared-only facts, not publication claims.

## REGRESSION RESULTS

- DIRECT_EVIDENCE: `& .\.venv\Scripts\python.exe -m py_compile contextor/core/cycle_semantics/original_worker_preparation.py tests/test_original_worker_partial_scc_preparation.py`: exit 0, no output.
- DIRECT_EVIDENCE: `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_original_worker_partial_scc_preparation.py tests/test_original_worker_real_pipeline_preparation.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_cycle_semantics_warning_eligibility.py`: exit 0, 80 passed, 0 failed, 0 skipped in 28.45s.
- DIRECT_EVIDENCE: `git diff --check -- contextor/core/cycle_semantics/original_worker_preparation.py tests/test_original_worker_partial_scc_preparation.py`: exit 0, no whitespace errors; only LF-to-CRLF working-copy notices.
- CONTRACT_PROVED: R1-T08 uses a forged incomplete manifest result; its manifest=None is passed to the existing store, which creates no receipt, and WARN-1 eligibility remains empty. Original T06 covers real incomplete mixed input. No valid receipt or digest is fabricated in positive tests.
- No global pytest, active FULL/LIVE operation, restart, commit or push.

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_file_edit_context` at canonical revision 825 reported both changed modules available, workspace_sync=verified, syntax diagnostics fresh, module/graph/topology fresh, and cycle_semantics stale. Production module's direct consumers include facade and original-worker tests (9 total; compact list truncated); test module has no consumers. These are source/metadata synchronization observations, not active loaded-code adoption.

## FILES_CHANGED

- `contextor/core/cycle_semantics/original_worker_preparation.py`
- `tests/test_original_worker_partial_scc_preparation.py`

`walkthrough.md` is report-only.

## FULL_DIFFS

Complete actual tracked Git diffs for both modified Python files follow; no changed source/test line is omitted.

```diff
diff --git a/contextor/core/cycle_semantics/original_worker_preparation.py b/contextor/core/cycle_semantics/original_worker_preparation.py
index 270979d..32085df 100644
--- a/contextor/core/cycle_semantics/original_worker_preparation.py
+++ b/contextor/core/cycle_semantics/original_worker_preparation.py
@@ -15,7 +15,7 @@ from contextor.core.source import (
     parse_source_snapshot,
 )
 
-from .contracts import CycleSemanticsSnapshot
+from .contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
 from .evidence import build_source_bound_cycle_evidence
 from .generation_manifest import (
     PreparedCycleSourceManifest,
@@ -129,19 +129,9 @@ def prepare_original_worker_cycle_manifest(
             "SOURCE_EVIDENCE_PREPARATION_FAILED"
         )
 
-    if (
-        type(manifest.source_manifest_sha256) is not str
-        or len(manifest.source_manifest_sha256) != 64
-        or not manifest.components
-        or any(
-            component.preparation_state
-            != "PREPARED_UNPUBLISHED"
-            for component in manifest.components
-        )
-    ):
+    if type(manifest) is not PreparedCycleSourceManifest:
         return unavailable(
-            "P1C0_SOURCE_EVIDENCE_UNAVAILABLE",
-            component_preparations=manifest.components,
+            "SOURCE_EVIDENCE_PREPARATION_FAILED"
         )
 
     if manifest.authority != (
@@ -151,6 +141,27 @@ def prepare_original_worker_cycle_manifest(
             "PREPARED_AUTHORITY_INVALID"
         )
 
+    if not (
+        manifest.graph_sha256
+        == snapshot.graph_sha256
+        == fingerprint_hard_edges(hard_edges)
+    ):
+        return unavailable(
+            "SOURCE_MANIFEST_GRAPH_MISMATCH"
+        )
+
+    if (
+        type(manifest.components) is not tuple
+        or len(manifest.components) != len(binding.cyclic_components)
+        or any(
+            type(component) is not PreparedSCCSourceBinding
+            for component in manifest.components
+        )
+    ):
+        return unavailable(
+            "SCC_COMPONENT_IDENTITY_MISMATCH"
+        )
+
     if tuple(
         component.members
         for component in manifest.components
@@ -159,6 +170,21 @@ def prepare_original_worker_cycle_manifest(
             "SCC_COMPONENT_IDENTITY_MISMATCH"
         )
 
+    if (
+        type(manifest.source_manifest_sha256) is not str
+        or len(manifest.source_manifest_sha256) != 64
+        or not manifest.components
+        or any(
+            component.preparation_state
+            != "PREPARED_UNPUBLISHED"
+            for component in manifest.components
+        )
+    ):
+        return unavailable(
+            "P1C0_SOURCE_EVIDENCE_UNAVAILABLE",
+            component_preparations=manifest.components,
+        )
+
     return OriginalWorkerManifestPreparation(
         status="PREPARED_UNPUBLISHED_NON_ATOMIC",
         reason=None,
diff --git a/tests/test_original_worker_partial_scc_preparation.py b/tests/test_original_worker_partial_scc_preparation.py
index 5c1c9c4..7cd1307 100644
--- a/tests/test_original_worker_partial_scc_preparation.py
+++ b/tests/test_original_worker_partial_scc_preparation.py
@@ -7,6 +7,7 @@ from dataclasses import FrozenInstanceError, replace
 
 import pytest
 
+import contextor.core.cycle_semantics.original_worker_preparation as preparation_module
 from contextor.core.analysis.state_manager import RepositoryAnalysisState
 from contextor.core.cycle_semantics.materialization import materialize_cycle_semantics
 from contextor.core.cycle_semantics.original_worker_preparation import (
@@ -71,6 +72,21 @@ def _prepare(index, graph, snapshot):
     return prepare_original_worker_cycle_manifest(index, graph.hard_edges, snapshot)
 
 
+def _injected_manifest_result(tmp_path, isolated_dirs, monkeypatch, mutation):
+    index, graph, snapshot = _real_pipeline(_repo(tmp_path, PASS_AND_UNKNOWN))
+    original = preparation_module.prepare_cycle_source_manifest
+
+    def altered_manifest(*args, **kwargs):
+        genuine = original(*args, **kwargs)
+        assert genuine.source_manifest_sha256 is None
+        return mutation(genuine)
+
+    monkeypatch.setattr(
+        preparation_module, "prepare_cycle_source_manifest", altered_manifest,
+    )
+    return _prepare(index, graph, snapshot), graph, snapshot
+
+
 def test_t01_mixed_pass_unknown_preserves_independent_components(tmp_path, isolated_dirs):
     index, graph, snapshot = _real_pipeline(_repo(tmp_path, PASS_AND_UNKNOWN))
     assert index.original_worker_capture_status == "ALL_SELECTED_CAPTURED_NON_ATOMIC"
@@ -212,3 +228,130 @@ def test_t08_supplied_inputs_are_not_mutated(tmp_path, isolated_dirs):
         snapshot,
     )
     assert after == before
+
+
+def test_r1_t01_forged_authority_hides_partial_components(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    result, _, _ = _injected_manifest_result(
+        tmp_path, isolated_dirs, monkeypatch,
+        lambda manifest: replace(manifest, authority="FORGED"),
+    )
+    assert result.reason == "PREPARED_AUTHORITY_INVALID"
+    assert result.manifest is None
+    assert result.component_preparations == ()
+
+
+def test_r1_t02_reordered_scc_components_hide_partial_results(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    result, _, _ = _injected_manifest_result(
+        tmp_path, isolated_dirs, monkeypatch,
+        lambda manifest: replace(
+            manifest, components=tuple(reversed(manifest.components)),
+        ),
+    )
+    assert result.reason == "SCC_COMPONENT_IDENTITY_MISMATCH"
+    assert result.component_preparations == ()
+
+
+def test_r1_t03_missing_scc_component_hides_partial_results(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    result, _, _ = _injected_manifest_result(
+        tmp_path, isolated_dirs, monkeypatch,
+        lambda manifest: replace(manifest, components=manifest.components[:1]),
+    )
+    assert result.reason == "SCC_COMPONENT_IDENTITY_MISMATCH"
+    assert result.component_preparations == ()
+
+
+def test_r1_t04_graph_sha_mismatch_hides_partial_results(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    result, _, _ = _injected_manifest_result(
+        tmp_path, isolated_dirs, monkeypatch,
+        lambda manifest: replace(manifest, graph_sha256="0" * 64),
+    )
+    assert result.reason == "SOURCE_MANIFEST_GRAPH_MISMATCH"
+    assert result.component_preparations == ()
+
+
+@pytest.mark.parametrize("components", ["list", "bad_element"])
+def test_r1_t05_component_shape_or_type_hides_partial_results(
+    tmp_path, isolated_dirs, monkeypatch, components,
+):
+    def mutate(manifest):
+        value = (
+            list(manifest.components)
+            if components == "list"
+            else (manifest.components[0], object())
+        )
+        return replace(manifest, components=value)
+
+    result, _, _ = _injected_manifest_result(
+        tmp_path, isolated_dirs, monkeypatch, mutate,
+    )
+    assert result.reason == "SCC_COMPONENT_IDENTITY_MISMATCH"
+    assert result.component_preparations == ()
+
+
+def test_r1_t06_unmodified_mixed_results_remain_available(
+    tmp_path, isolated_dirs,
+):
+    index, graph, snapshot = _real_pipeline(_repo(tmp_path, PASS_AND_UNKNOWN))
+    result = _prepare(index, graph, snapshot)
+    assert result.reason == "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+    assert result.manifest is None
+    assert tuple(item.preparation_state for item in result.component_preparations) == (
+        "PREPARED_UNPUBLISHED", "UNAVAILABLE",
+    )
+
+
+def test_r1_t07_complete_pass_hazard_remains_prepared(tmp_path, isolated_dirs):
+    index, graph, snapshot = _real_pipeline(_repo(tmp_path, PASS_AND_HAZARD))
+    result = _prepare(index, graph, snapshot)
+    assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert result.component_preparations == result.manifest.components
+    assert tuple(item.model_classification for item in result.component_preparations) == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+    )
+
+
+def test_r1_t08_invalid_manifest_cannot_create_receipt_or_eligible_path(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    result, graph, snapshot = _injected_manifest_result(
+        tmp_path, isolated_dirs, monkeypatch,
+        lambda manifest: replace(manifest, authority="FORGED"),
+    )
+    assert result.manifest is None
+    assert result.component_preparations == ()
+    state = RepositoryAnalysisState(
+        dependency_graph=ProjectGraph(
+            hard_edges={name: set(targets) for name, targets in graph.hard_edges.items()},
+            soft_edges={},
+        ),
+        cycles=[["a", "b", "a"], ["x", "y", "x"]],
+        cycles_state="fresh",
+        cycle_semantics=snapshot,
+        cycle_semantics_state="fresh",
+    )
+    save_snapshot(
+        state, tmp_path, "invalid-state", exact_revision=1,
+        file_state_payload={
+            "_meta": {"state_id": "invalid-state", "revision": 1},
+            "files": {},
+        },
+        prepared_cycle_manifest=result.manifest,
+    )
+    loaded, metadata = load_snapshot(tmp_path, "invalid-state")
+    assert loaded.cycle_source_publication is None
+    assert _verified_model_pass_cycle_paths(
+        loaded,
+        expected_revision=metadata.revision,
+        expected_state_id=metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=metadata.root_path,
+    ) == frozenset()
```

## CONTRACT_CONFLICTS

NONE observed. The specified validation order and exact error reasons fit the current source. No facade, store, receipt or manifest schema was changed.

## REMAINING UNKNOWN

No active LIVE generation, loaded-code identity, or warning behavior was probed. Contextor reported cycle_semantics stale; workspace_sync does not establish loaded-code adoption. Future per-SCC committed authority remains outside this stage.

## FINAL IMPLEMENTER OBSERVATION

CODE_PATH_PROVED: only manifest components passing authority, graph and exact ordered SCC identity gates can now survive the existing incomplete-global-manifest return. Global publication authority is unchanged. Architectural GO remains with ChatGPT.



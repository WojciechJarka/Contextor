# CONTEXTOR P1D3-WARN-2A — preserve independent SCC preparation results

## 1. PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP `get_file_edit_context` identified `original_worker_preparation.py` as canonical module, with direct consumers including `contextor.core.api.facade` and existing original-worker tests; pre-edit workspace_sync=verified. Current local source confirmed `OriginalWorkerManifestPreparation` had exactly status, reason, manifest, source_modules; `generation_manifest.py:88-185` already built per-SCC `PreparedSCCSourceBinding` entries when global digest was None; `original_worker_preparation.py:125-139` previously returned UNAVAILABLE with manifest=None and discarded entries. No PREFLIGHT_MISMATCH. Read current `source_proof.py`, `original_worker_binding.py`, `original_worker_reindex_planning.py` and real pipeline test helpers. No design or schema change.

## 2. HEAD / WORKTREE

DIRECT_EVIDENCE: initial HEAD `90ac91a5bc17c834262af466bf059839da67e464`; initial `git status --short` empty. Final HEAD unchanged; final worktree consists only of the modified production file, new test module and this report.

## 3. EXISTING P0/P1B PREPARATION PATH

CODE_PATH_PROVED: `original_worker_binding.py:40-158` checks selected original indexer source-byte capture against index fingerprints and SCC closures, failing before exposing partial snapshots if binding is invalid. `original_worker_preparation.py:71-121` parses bound snapshots and builds source evidence. `source_proof.py:45-259` performs per-SCC source-byte/AST/model replay; `generation_manifest.py:60-185` constructs per-SCC entries and only emits global source_manifest_sha256 when all are complete. These steps remain unchanged.

## 4. EXACT DATACLASS EXTENSION

CODE_PATH_PROVED: appended only `component_preparations: tuple[PreparedSCCSourceBinding, ...] = ()` to frozen `OriginalWorkerManifestPreparation`. The original four fields and order remain unchanged. Added import of the existing binding type; no new authority type or receipt.

## 5. GLOBAL MANIFEST FAILURE PRESERVATION

CODE_PATH_PROVED: existing incomplete-manifest branch still returns status UNAVAILABLE, reason P1C0_SOURCE_EVIDENCE_UNAVAILABLE, manifest=None, source_modules=(). It now carries `manifest.components` in `component_preparations`. Existing successful result still returns PREPARED_UNPUBLISHED_NON_ATOMIC and original manifest/source_modules, now with the same component tuple. Later authority or SCC identity failures use the default empty tuple.

## 6. INDEPENDENT SCC RESULT PRESERVATION

CONTRACT_PROVED: T01's real indexer capture, graph, snapshot, P0/P1B and manifest preparation yield two ordered components even though the wrapper's global manifest is unavailable. T02/T03 preserve complete results for two supported SCCs. No partial positive result is invented by a failed original-worker binding.

## 7. MIXED PASS / INDETERMINATE

CONTRACT_PROVED: T01 creates two independent flat-module cyclic SCCs under tmp_path. SCC_A has real original-worker captured bytes and MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS with PREPARED_UNPUBLISHED; SCC_B has syntactically valid unsupported decorator, resulting in INDETERMINATE/UNAVAILABLE. Wrapper status/reason/manifest/source_modules retain existing fail-closed values. `generation_manifest.py:161-185` has no global source_manifest_sha256 for this mixture; the new tuple exposes preparation facts only.

## 8. MIXED PASS / HAZARD

CONTRACT_PROVED: T03 builds a genuine committed-independent preparation of one PASS and one MODEL_INTERNAL_EARLY_BINDING_HAZARD SCC; both per-SCC entries are PREPARED_UNPUBLISHED, while the distinct classifications are retained. HAZARD is not labeled acceptable.

## 9. SOURCE CAPTURE FAIL-CLOSED

CONTRACT_PROVED: T04 default index lacks opted-in original-worker capture; T05 removes a required capture or supplies mismatched bytes. Both fail binding before manifest construction and return component_preparations=(). No partial positive result leaks across a capture authority failure.

## 10. NO PUBLICATION AUTHORITY

CONTRACT_PROVED: T06 persists state with `prepared_cycle_manifest=result.manifest` where the incomplete wrapper's manifest is None. Store hydration returns no `cycle_source_publication`; WARN-1 eligibility is empty even while component_preparations[0] is PREPARED_UNPUBLISHED. `facade.py` and `store.py` were not edited. The tuple is caller-supplied, non-atomic, prepared-only evidence: not a committed receipt, installed LIVE proof, source atomicity or runtime-safety certificate.

## 11. DETERMINISM / IMMUTABILITY

CONTRACT_PROVED: T07 repeats preparation, checks deterministic SCC ordering and frozen component entry. T08 compares original index fingerprints, worker snapshots/modes, graph hard edges and semantic snapshot before/after. No supplied object mutation was observed in the focused tests.

## 12. FOCUSED TEST RESULTS

- DIRECT_EVIDENCE: `& .\.venv\Scripts\python.exe -m py_compile contextor/core/cycle_semantics/original_worker_preparation.py tests/test_original_worker_partial_scc_preparation.py` exit 0, no output.
- DIRECT_EVIDENCE: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_original_worker_partial_scc_preparation.py` exit 0, 9 passed, 0 failed, 0 skipped, 2.60s.
- DIRECT_EVIDENCE: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_original_worker_real_pipeline_preparation.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_warning_eligibility.py` exit 0, 139 passed, 0 failed, 0 skipped, 26.61s.
- DIRECT_EVIDENCE: `git diff --check -- contextor/core/cycle_semantics/original_worker_preparation.py` exit 0; `git diff --no-index --check -- /dev/null tests/test_original_worker_partial_scc_preparation.py` exit 1 (expected difference status for untracked new file); neither reported whitespace errors. Both printed only LF-to-CRLF notices. No global pytest, active FULL/LIVE, restart, commit or push.

## 13. POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_file_edit_context` at canonical revision 823 reported both changed files available, workspace_sync=verified and syntax_diagnostics fresh. Production module imports existing evidence, contracts, generation_manifest, source and original-worker binding; its direct consumers include facade and original-worker tests (9 total). New test module is indexed as a test module (9 imports, no consumers). Compact dependency/consumer evidence was truncated, so no complete-consumer claim is made. MCP source synchronization does not prove that running server code loaded this production change.

## 14. FILES_CHANGED

- `contextor/core/cycle_semantics/original_worker_preparation.py` — modified.
- `tests/test_original_worker_partial_scc_preparation.py` — new.
- `walkthrough.md` — report only, excluded from source/test changed-file accounting.

## 15. FULL_DIFFS

Complete actual Git diff of the tracked production file and complete new-file diff of the test module follow; no source/test lines omitted.

### Production diff

```diff
diff --git a/contextor/core/cycle_semantics/original_worker_preparation.py b/contextor/core/cycle_semantics/original_worker_preparation.py
index 067aa94..270979d 100644
--- a/contextor/core/cycle_semantics/original_worker_preparation.py
+++ b/contextor/core/cycle_semantics/original_worker_preparation.py
@@ -19,6 +19,7 @@ from .contracts import CycleSemanticsSnapshot
 from .evidence import build_source_bound_cycle_evidence
 from .generation_manifest import (
     PreparedCycleSourceManifest,
+    PreparedSCCSourceBinding,
     prepare_cycle_source_manifest,
 )
 from .original_worker_binding import (
@@ -32,6 +33,7 @@ class OriginalWorkerManifestPreparation:
     reason: str | None
     manifest: PreparedCycleSourceManifest | None
     source_modules: tuple[str, ...]
+    component_preparations: tuple[PreparedSCCSourceBinding, ...] = ()
 
 
 def prepare_original_worker_cycle_manifest(
@@ -56,12 +58,15 @@ def prepare_original_worker_cycle_manifest(
 
     def unavailable(
         reason: str,
+        *,
+        component_preparations: tuple[PreparedSCCSourceBinding, ...] = (),
     ) -> OriginalWorkerManifestPreparation:
         return OriginalWorkerManifestPreparation(
             status="UNAVAILABLE",
             reason=reason,
             manifest=None,
             source_modules=(),
+            component_preparations=component_preparations,
         )
 
     binding = assess_original_worker_cycle_closure(
@@ -135,7 +140,8 @@ def prepare_original_worker_cycle_manifest(
         )
     ):
         return unavailable(
-            "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+            "P1C0_SOURCE_EVIDENCE_UNAVAILABLE",
+            component_preparations=manifest.components,
         )
 
     if manifest.authority != (
@@ -158,4 +164,5 @@ def prepare_original_worker_cycle_manifest(
         reason=None,
         manifest=manifest,
         source_modules=binding.reachable_modules,
+        component_preparations=manifest.components,
     )
```

### New test diff

```diff
diff --git a/tests/test_original_worker_partial_scc_preparation.py b/tests/test_original_worker_partial_scc_preparation.py
new file mode 100644
index 0000000..5c1c9c4
--- /dev/null
+++ b/tests/test_original_worker_partial_scc_preparation.py
@@ -0,0 +1,214 @@
+"""WARN-2A original-worker SCC preparation is not publication authority."""
+
+from __future__ import annotations
+
+import copy
+from dataclasses import FrozenInstanceError, replace
+
+import pytest
+
+from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.core.cycle_semantics.materialization import materialize_cycle_semantics
+from contextor.core.cycle_semantics.original_worker_preparation import (
+    prepare_original_worker_cycle_manifest,
+)
+from contextor.core.cycle_semantics.warning_eligibility import (
+    _verified_model_pass_cycle_paths,
+)
+from contextor.core.domain.graph import ProjectGraph
+from contextor.core.graph.graph import build_graph
+from contextor.core.live_state.store import load_snapshot, save_snapshot
+from contextor.core.source import SourceSnapshot
+from contextor.core.symbol_engine.indexer import index_repository
+
+
+PASS_AND_UNKNOWN = {
+    "a": "import b\nvalue = 1\n",
+    "b": "import a\nvalue = 2\n",
+    "x": "import y\n@unknown_decorator\ndef f():\n    pass\n",
+    "y": "import x\n",
+}
+TWO_PASS = {
+    **PASS_AND_UNKNOWN,
+    "x": "import y\nvalue = 3\n",
+}
+PASS_AND_HAZARD = {
+    **TWO_PASS,
+    "x": "import y\nvalue = 3\n",
+    "y": "from x import value\n",
+}
+SELECTED = frozenset({"a", "b", "x", "y"})
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _repo(tmp_path, sources):
+    root = tmp_path / "repo"
+    root.mkdir()
+    for module, source in sources.items():
+        (root / f"{module}.py").write_bytes(source.encode("utf-8"))
+    return root
+
+
+def _real_pipeline(root, selected=SELECTED):
+    index = index_repository(
+        str(root), source_capture_module_ids=selected,
+    )
+    graph = build_graph(index.modules)
+    snapshot = materialize_cycle_semantics(
+        root,
+        graph.hard_edges,
+        {name: module.path for name, module in index.modules.items()},
+        index.source_fingerprints_by_module,
+    )
+    return index, graph, snapshot
+
+
+def _prepare(index, graph, snapshot):
+    return prepare_original_worker_cycle_manifest(index, graph.hard_edges, snapshot)
+
+
+def test_t01_mixed_pass_unknown_preserves_independent_components(tmp_path, isolated_dirs):
+    index, graph, snapshot = _real_pipeline(_repo(tmp_path, PASS_AND_UNKNOWN))
+    assert index.original_worker_capture_status == "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    result = _prepare(index, graph, snapshot)
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+    assert result.manifest is None
+    assert result.source_modules == ()
+    assert len(result.component_preparations) == 2
+    assert tuple(item.members for item in result.component_preparations) == (
+        ("a", "b"), ("x", "y"),
+    )
+    first, second = result.component_preparations
+    assert (first.preparation_state, first.model_classification) == (
+        "PREPARED_UNPUBLISHED", "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+    )
+    assert (second.preparation_state, second.model_classification) == (
+        "UNAVAILABLE", "INDETERMINATE",
+    )
+
+
+def test_t02_two_supported_sccs_keep_success_contract(tmp_path, isolated_dirs):
+    index, graph, snapshot = _real_pipeline(_repo(tmp_path, TWO_PASS))
+    result = _prepare(index, graph, snapshot)
+    assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert result.reason is None
+    assert result.manifest is not None
+    assert result.manifest.source_manifest_sha256 is not None
+    assert result.source_modules == ("a", "b", "x", "y")
+    assert result.component_preparations == result.manifest.components
+    assert all(item.preparation_state == "PREPARED_UNPUBLISHED"
+               for item in result.component_preparations)
+
+
+def test_t03_pass_and_hazard_are_distinct_prepared_claims(tmp_path, isolated_dirs):
+    index, graph, snapshot = _real_pipeline(_repo(tmp_path, PASS_AND_HAZARD))
+    result = _prepare(index, graph, snapshot)
+    assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert result.manifest is not None
+    assert result.component_preparations == result.manifest.components
+    assert tuple(item.model_classification for item in result.component_preparations) == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+    )
+
+
+def test_t04_unavailable_original_capture_exposes_no_components(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, TWO_PASS)
+    index, graph, snapshot = _real_pipeline(root, selected=None)
+    result = _prepare(index, graph, snapshot)
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "BINDING_INDEX_CAPTURE_NOT_COMPLETE"
+    assert result.component_preparations == ()
+
+
+@pytest.mark.parametrize("mode", ["missing", "invalid"])
+def test_t05_capture_binding_failure_exposes_no_partial_pass(
+    tmp_path, isolated_dirs, mode,
+):
+    index, graph, snapshot = _real_pipeline(_repo(tmp_path, TWO_PASS))
+    captures = dict(index.original_worker_source_snapshots)
+    if mode == "missing":
+        captures.pop("x")
+    else:
+        original = captures["x"]
+        captures["x"] = SourceSnapshot(
+            b"forged", original.source_fingerprint,
+        )
+    index = replace(index, original_worker_source_snapshots=captures)
+    result = _prepare(index, graph, snapshot)
+    assert result.status == "UNAVAILABLE"
+    assert result.manifest is None
+    assert result.component_preparations == ()
+
+
+def test_t06_partial_components_do_not_create_receipt_or_eligibility(
+    tmp_path, isolated_dirs,
+):
+    index, graph, snapshot = _real_pipeline(_repo(tmp_path, PASS_AND_UNKNOWN))
+    result = _prepare(index, graph, snapshot)
+    assert result.component_preparations[0].preparation_state == "PREPARED_UNPUBLISHED"
+    assert result.manifest is None
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
+        state, tmp_path, "partial-state", exact_revision=1,
+        file_state_payload={
+            "_meta": {"state_id": "partial-state", "revision": 1},
+            "files": {},
+        },
+        prepared_cycle_manifest=result.manifest,
+    )
+    loaded, metadata = load_snapshot(tmp_path, "partial-state")
+    assert loaded.cycle_source_publication is None
+    assert _verified_model_pass_cycle_paths(
+        loaded,
+        expected_revision=metadata.revision,
+        expected_state_id=metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=metadata.root_path,
+    ) == frozenset()
+
+
+def test_t07_order_and_component_immutability(tmp_path, isolated_dirs):
+    index, graph, snapshot = _real_pipeline(_repo(tmp_path, TWO_PASS))
+    first = _prepare(index, graph, snapshot)
+    second = _prepare(index, graph, snapshot)
+    assert first == second
+    assert tuple(item.members for item in first.component_preparations) == (
+        ("a", "b"), ("x", "y"),
+    )
+    with pytest.raises(FrozenInstanceError):
+        first.component_preparations[0].model_classification = "INDETERMINATE"
+
+
+def test_t08_supplied_inputs_are_not_mutated(tmp_path, isolated_dirs):
+    index, graph, snapshot = _real_pipeline(_repo(tmp_path, TWO_PASS))
+    before = copy.deepcopy((
+        index.source_fingerprints_by_module,
+        index.original_worker_source_snapshots,
+        index.original_worker_ast_modes,
+        graph.hard_edges,
+        snapshot,
+    ))
+    _prepare(index, graph, snapshot)
+    after = (
+        index.source_fingerprints_by_module,
+        index.original_worker_source_snapshots,
+        index.original_worker_ast_modes,
+        graph.hard_edges,
+        snapshot,
+    )
+    assert after == before
```

## 16. CONTRACT_CONFLICTS

NONE observed. All requested fixtures were constructed with real indexer capture and existing graph, materialization, preparation and store helpers.

## 17. REMAINING UNKNOWN

Active loaded-code adoption and any future LIVE committed generation were not tested. No per-SCC committed authority exists in this phase. The new field does not authorize warning suppression. Contextor MCP synchronization is limited to source metadata.

## 18. FINAL IMPLEMENTER OBSERVATION

CODE_PATH_PROVED: independent SCC preparation records now survive only the existing global-manifest-incomplete branch and successful branch. Global publication authority and failure statuses remain unchanged. Architectural acceptance remains with ChatGPT.



# CONTEXTOR P1D3-WARN-2C-R1 — implementer report

## CONTRACT_CONFLICT_RESOLUTION

DIRECT_EVIDENCE: Architect specified that `RepositoryAnalysisState.resync_required` is optional and absence means no resync. The new gate uses exactly `getattr(state, "resync_required", False) is False`. No state field or default assignment was added. R1-T01 through R1-T03 cover absent, `True` and `None`.

## HEAD / WORKTREE

DIRECT_EVIDENCE: Initial and final HEAD `e0da7f7e130d78dd0fe65a0b9c255c474e03d5f5`. Initial worktree clean. Final changes are the two authorized production files, the new integration test and this report. No commit, push, restart or active user's FULL/LIVE operation.

## EXACT RESYNC GATE

CODE_PATH_PROVED: The partial publication predicate uses `getattr(state, "resync_required", False) is False`, alongside the specified fresh semantic/cycle, coverage, source-issue, graph-identity and module-set gates. Explicit `True` and `None` do not satisfy it.

## ORIGINAL WARN-2C CONTRACT COMPLETION

CODE_PATH_PROVED: `ContextorFacade.analyze_project` gained trailing keyword-only `cycle_partial_source_publication_opt_in: bool = False`, exact bool validation and a preview requirement. It reuses the official second original-worker index preview. The gate calls `validate_partial_scc_claims` and forwards the exact `cycle_source_preparation` object only when validation succeeds. `save_engine_state` adds the store keyword only when non-None. The store remains the sole sealing owner. Existing v2 predicate and default mode are unchanged.

## REAL FULL PASS / INDETERMINATE

CONTRACT_PROVED: Genuine isolated FULL on `PASS_AND_UNKNOWN` returned preview `UNAVAILABLE/P1C0_SOURCE_EVIDENCE_UNAVAILABLE` with two components. It committed a partial receipt bound to exact metadata identity; PASS and INDETERMINATE classifications survived hydration and verification. v2 receipt remained absent and WARN-1 eligible paths remained empty.

## REAL FULL PASS / HAZARD

CONTRACT_PROVED: Genuine isolated FULL on `PASS_AND_HAZARD` committed the original preview as a partial receipt with distinct PASS and HAZARD classifications.

## COMPLETE V2 COEXISTENCE

CONTRACT_PROVED: `TWO_PASS` with both opt-ins committed v2 and partial receipts to one generation; both independently verified. v2-only opt-in produced no unrequested partial receipt.

## DEFAULT FULL COMPATIBILITY

CONTRACT_PROVED: Default FULL and preview-only FULL produced no receipts. A no-cycle FULL with partial opt-in produced none. A later default FULL advanced the revision without inheriting a prior partial receipt. The ordinary FULL call does not add the optional store keyword.

## FAIL-CLOSED NEGATIVE CASES

CONTRACT_PROVED: Non-bool values and missing preview fail before indexing. Missing capture or second-pass drift yields unavailable preview, ordinary persistence and no partial receipt or WARN-1 path. A coherently produced but forged component declaration failed validation and was not forwarded. Explicit `resync_required=True` and `None` blocked forwarding. No digest or receipt was fabricated.

## FOCUSED TEST RESULTS

DIRECT_EVIDENCE: `py_compile` on the three authorized Python files exited 0. New module first: 22 passed, 0 failed, 0 skipped, 21.77 s, exit 0. Six requested regression modules: 131 passed, 0 failed, 0 skipped, 32.69 s, exit 0. `git diff --check` and untracked-file `git diff --no-index --check` exited 0. No global suite.

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor inspected `facade.py`, `state_manager.py` and the new test. At canonical revision 843, all three returned live provenance, `workspace_sync=verified`, fresh module/graph/topology/structural-cycle families and stale cycle_semantics. The structural DFS back-edge count was 16 before and after. The new facade local import adds the intended dependency on `partial_scc_claims`; state manager adds no import. No newly counted structural cycle was observed. This is source/workspace evidence, not active loaded-code adoption.

## FILES_CHANGED

- `contextor/core/api/facade.py`
- `contextor/core/analysis/state_manager.py`
- `tests/test_original_worker_full_partial_receipt_optin.py` (new)

`walkthrough.md` is this report. Complete actual diffs of all three Python files follow.

## FULL_DIFFS


### Modified production files

```diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index d7953d3..cfac2a4 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -536,6 +536,7 @@ def save_engine_state(
     exact_revision: int | None = None,
     file_state_payload: dict[str, Any] | None = None,
     prepared_cycle_manifest: Any = None,
+    prepared_partial_scc_preparation: Any = None,
 ):
     """Persist canonical state; optionally forward prepared SCC claims.
 
@@ -562,6 +563,11 @@ def save_engine_state(
                 prepared_cycle_manifest
             )
 
+        if prepared_partial_scc_preparation is not None:
+            save_kwargs["prepared_partial_scc_preparation"] = (
+                prepared_partial_scc_preparation
+            )
+
         return save_snapshot(
             state,
             cache_dir,
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 9a7a0b1..c394d02 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -565,6 +565,7 @@ class ContextorFacade:
         *,
         cycle_source_preparation_preview: bool = False,
         cycle_source_publication_opt_in: bool = False,
+        cycle_partial_source_publication_opt_in: bool = False,
     ) -> list:
         """
         Analyzes full project hierarchy, builds dependency graph, evaluates
@@ -607,6 +608,20 @@ class ContextorFacade:
                 "cycle_source_preparation_preview=True"
             )
 
+        if type(cycle_partial_source_publication_opt_in) is not bool:
+            raise ValueError(
+                "cycle_partial_source_publication_opt_in must be bool"
+            )
+
+        if (
+            cycle_partial_source_publication_opt_in
+            and not cycle_source_preparation_preview
+        ):
+            raise ValueError(
+                "cycle_partial_source_publication_opt_in requires "
+                "cycle_source_preparation_preview=True"
+            )
+
         cycle_source_preparation = None
 
         def emit_stage_end(stage: str, started: float) -> None:
@@ -1418,6 +1433,33 @@ class ContextorFacade:
                         "prepared_cycle_manifest"
                     ] = cycle_source_preparation.manifest
 
+            if (
+                cycle_partial_source_publication_opt_in
+                and cycle_source_preparation is not None
+                and state.cycle_semantics is cycle_semantics
+                and state.cycle_semantics_state == "fresh"
+                and state.cycles_state == "fresh"
+                and state.cycle_semantics.coverage_status
+                == "FILESYSTEM_STABLE_NON_ATOMIC"
+                and not state.cycle_semantics.source_issues
+                and getattr(state, "resync_required", False) is False
+                and state.dependency_graph is graph
+                and set(state.modules) == set(index.modules)
+            ):
+                from contextor.core.cycle_semantics.partial_scc_claims import (
+                    validate_partial_scc_claims,
+                )
+
+                partial_claims = validate_partial_scc_claims(
+                    state.dependency_graph.hard_edges,
+                    state.cycle_semantics,
+                    cycle_source_preparation,
+                )
+                if partial_claims is not None:
+                    store_manifest_kwargs[
+                        "prepared_partial_scc_preparation"
+                    ] = cycle_source_preparation
+
             component_started = time.monotonic()
             meta = save_engine_state(
                 state,
```

### New integration test

```diff
diff --git a/tests/test_original_worker_full_partial_receipt_optin.py b/tests/test_original_worker_full_partial_receipt_optin.py
new file mode 100644
index 0000000..37c97ae
--- /dev/null
+++ b/tests/test_original_worker_full_partial_receipt_optin.py
@@ -0,0 +1,301 @@
+"""Official FULL to partial SCC receipt integration."""
+
+from __future__ import annotations
+
+import copy
+from dataclasses import replace
+
+import pytest
+
+import contextor.core.api.facade as facade_module
+import contextor.core.analysis.state_manager as state_manager
+import contextor.core.cycle_semantics.original_worker_preparation as preparation_module
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.cycle_semantics.partial_scc_publication import (
+    CanonicalPartialSCCReceipt,
+    verify_co_published_partial_scc_preparation,
+)
+from contextor.core.cycle_semantics.publication_binding import (
+    verify_co_published_cycle_manifest,
+)
+from contextor.core.cycle_semantics.warning_eligibility import (
+    _verified_model_pass_cycle_paths,
+)
+from tests.test_original_worker_full_receipt_optin import _persisted
+from tests.test_original_worker_partial_scc_preparation import (
+    PASS_AND_HAZARD, PASS_AND_UNKNOWN, TWO_PASS, _repo,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _full(root, *, preview=False, partial=False, complete=False):
+    errors, result = ContextorFacade.analyze_project(
+        str(root),
+        cycle_source_preparation_preview=preview,
+        cycle_partial_source_publication_opt_in=partial,
+        cycle_source_publication_opt_in=complete,
+    )
+    assert isinstance(errors, list)
+    assert result is not None
+    return result
+
+
+def _partial_verified(state, metadata):
+    return verify_co_published_partial_scc_preparation(
+        state, revision=metadata.revision, state_id=metadata.state_id,
+        repo_id=metadata.repo_id, root_path=metadata.root_path,
+    )
+
+
+def _v2_verified(state, metadata):
+    return verify_co_published_cycle_manifest(
+        state, revision=metadata.revision, state_id=metadata.state_id,
+        repo_id=metadata.repo_id, root_path=metadata.root_path,
+    )
+
+
+def _warn1(state, metadata):
+    return _verified_model_pass_cycle_paths(
+        state, expected_revision=metadata.revision,
+        expected_state_id=metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=metadata.root_path,
+    )
+
+
+def test_t01_default_full_has_no_receipts(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, TWO_PASS)
+    _full(root)
+    state, _ = _persisted(root)
+    assert state.cycle_source_publication is None
+    assert state.cycle_partial_source_publication is None
+
+
+def test_t02_preview_only_has_no_receipts(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, TWO_PASS)
+    result = _full(root, preview=True)
+    assert result.cycle_source_preparation_preview is not None
+    state, _ = _persisted(root)
+    assert state.cycle_source_publication is None
+    assert state.cycle_partial_source_publication is None
+
+
+@pytest.mark.parametrize("invalid", [None, 0, 1, "true"])
+def test_t03_invalid_optin_precedes_index(
+    tmp_path, isolated_dirs, monkeypatch, invalid,
+):
+    root = _repo(tmp_path, TWO_PASS)
+    def unexpected(*args, **kwargs):
+        raise AssertionError("index started")
+    monkeypatch.setattr(facade_module, "index_repository", unexpected)
+    with pytest.raises(
+        ValueError, match="cycle_partial_source_publication_opt_in must be bool",
+    ):
+        ContextorFacade.analyze_project(
+            str(root), cycle_partial_source_publication_opt_in=invalid,
+        )
+
+
+def test_t04_preview_required(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, TWO_PASS)
+    with pytest.raises(
+        ValueError,
+        match="cycle_partial_source_publication_opt_in requires "
+              "cycle_source_preparation_preview=True",
+    ):
+        ContextorFacade.analyze_project(
+            str(root), cycle_partial_source_publication_opt_in=True,
+        )
+
+
+def test_t05_r1_t01_mixed_full_without_resync_attribute(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path, PASS_AND_UNKNOWN)
+    result = _full(root, preview=True, partial=True)
+    preview = result.cycle_source_preparation_preview
+    assert preview.status == "UNAVAILABLE"
+    assert preview.reason == "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+    assert len(preview.component_preparations) == 2
+    state, metadata = _persisted(root)
+    assert not hasattr(state, "resync_required")
+    receipt = state.cycle_partial_source_publication
+    assert type(receipt) is CanonicalPartialSCCReceipt
+    assert (receipt.revision, receipt.state_id, receipt.repo_id, receipt.root_path) == (
+        metadata.revision, metadata.state_id, metadata.repo_id, metadata.root_path,
+    )
+    assert _partial_verified(state, metadata)
+    assert tuple(item.model_classification for item in receipt.preparation.component_preparations) == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "INDETERMINATE",
+    )
+    assert state.cycle_source_publication is None
+    assert _warn1(state, metadata) == frozenset()
+
+
+def test_t06_pass_hazard_full(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, PASS_AND_HAZARD)
+    result = _full(root, preview=True, partial=True)
+    state, metadata = _persisted(root)
+    assert _partial_verified(state, metadata)
+    assert state.cycle_partial_source_publication.preparation == result.cycle_source_preparation_preview
+    assert tuple(item.model_classification for item in
+                 state.cycle_partial_source_publication.preparation.component_preparations) == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+    )
+
+
+def test_t07_both_receipts_one_generation(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, TWO_PASS)
+    _full(root, preview=True, partial=True, complete=True)
+    state, metadata = _persisted(root)
+    assert _partial_verified(state, metadata)
+    assert _v2_verified(state, metadata)
+    assert state.cycle_partial_source_publication.revision == state.cycle_source_publication.revision
+
+
+def test_t08_r1_t04_complete_v2_only_unchanged(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, TWO_PASS)
+    _full(root, preview=True, complete=True)
+    state, metadata = _persisted(root)
+    assert state.cycle_partial_source_publication is None
+    assert _v2_verified(state, metadata)
+
+
+def test_t09_no_cycles_no_partial(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, {"a": "value = 1\n"})
+    _full(root, preview=True, partial=True)
+    state, _ = _persisted(root)
+    assert state.cycle_partial_source_publication is None
+
+
+@pytest.mark.parametrize("failure", ["missing_capture", "drift"])
+def test_t10_unavailable_preview_persists_ordinary_full(
+    tmp_path, isolated_dirs, monkeypatch, failure,
+):
+    root = _repo(tmp_path, TWO_PASS)
+    original = facade_module.index_repository
+    def changed(*args, **kwargs):
+        if kwargs.get("source_capture_module_ids") is not None:
+            if failure == "missing_capture":
+                raise RuntimeError("missing original capture")
+            (root / "a.py").write_bytes(b"import b\nvalue = 300\n")
+        return original(*args, **kwargs)
+    monkeypatch.setattr(facade_module, "index_repository", changed)
+    result = _full(root, preview=True, partial=True)
+    assert result.cycle_source_preparation_preview.status == "UNAVAILABLE"
+    state, metadata = _persisted(root)
+    assert state.cycle_partial_source_publication is None
+    assert _warn1(state, metadata) == frozenset()
+
+
+def test_t11_forged_component_not_forwarded(tmp_path, isolated_dirs, monkeypatch):
+    root = _repo(tmp_path, PASS_AND_UNKNOWN)
+    original = preparation_module.prepare_original_worker_cycle_manifest
+    def forged(*args, **kwargs):
+        genuine = original(*args, **kwargs)
+        items = list(genuine.component_preparations)
+        items[0] = replace(items[0], model_classification="FORGED")
+        return replace(genuine, component_preparations=tuple(items))
+    monkeypatch.setattr(
+        preparation_module, "prepare_original_worker_cycle_manifest", forged,
+    )
+    result = _full(root, preview=True, partial=True)
+    assert result.cycle_source_preparation_preview.component_preparations[0].model_classification == "FORGED"
+    state, _ = _persisted(root)
+    assert state.cycle_partial_source_publication is None
+
+
+def test_t12_next_default_full_drops_partial(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, TWO_PASS)
+    _full(root, preview=True, partial=True)
+    old, old_meta = _persisted(root)
+    assert _partial_verified(old, old_meta)
+    _full(root)
+    new, new_meta = _persisted(root)
+    assert new_meta.revision > old_meta.revision
+    assert new.cycle_partial_source_publication is None
+
+
+def test_t13_exactly_two_index_passes(tmp_path, isolated_dirs, monkeypatch):
+    root = _repo(tmp_path, TWO_PASS)
+    original = facade_module.index_repository
+    calls = []
+    def tracked(*args, **kwargs):
+        calls.append(kwargs.get("source_capture_module_ids"))
+        return original(*args, **kwargs)
+    monkeypatch.setattr(facade_module, "index_repository", tracked)
+    _full(root, preview=True, partial=True)
+    assert len(calls) == 2
+    assert calls[0] is None and calls[1] is not None
+
+
+def test_t14_forwards_exact_preview_object(tmp_path, isolated_dirs, monkeypatch):
+    root = _repo(tmp_path, TWO_PASS)
+    original = state_manager.save_engine_state
+    forwarded = []
+    def tracked(*args, **kwargs):
+        forwarded.append(kwargs.get("prepared_partial_scc_preparation"))
+        return original(*args, **kwargs)
+    monkeypatch.setattr(state_manager, "save_engine_state", tracked)
+    result = _full(root, preview=True, partial=True)
+    assert len(forwarded) == 1
+    assert forwarded[0] is result.cycle_source_preparation_preview
+
+
+def test_t15_graph_scc_cycles_unchanged(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, TWO_PASS)
+    _full(root)
+    before, _ = _persisted(root)
+    edges = copy.deepcopy(before.dependency_graph.hard_edges)
+    cycles = copy.deepcopy(before.cycles)
+    sccs = copy.deepcopy(before.cycle_semantics.import_sites.topology.cyclic_components)
+    _full(root, preview=True, partial=True)
+    after, _ = _persisted(root)
+    assert after.dependency_graph.hard_edges == edges
+    assert after.cycles == cycles
+    assert after.cycle_semantics.import_sites.topology.cyclic_components == sccs
+
+
+def test_t17_t18_repeat_isolated_full_is_deterministic_without_live_claim(
+    tmp_path, isolated_dirs,
+):
+    classifications = []
+    for name in ("first", "second"):
+        parent = tmp_path / name
+        parent.mkdir()
+        root = _repo(parent, PASS_AND_UNKNOWN)
+        _full(root, preview=True, partial=True)
+        state, metadata = _persisted(root)
+        assert _partial_verified(state, metadata)
+        classifications.append(tuple(
+            item.model_classification
+            for item in state.cycle_partial_source_publication.preparation.component_preparations
+        ))
+    assert classifications[0] == classifications[1]
+
+
+@pytest.mark.parametrize("resync", [True, None])
+def test_r1_t02_t03_explicit_resync_blocks_partial_forwarding(
+    tmp_path, isolated_dirs, monkeypatch, resync,
+):
+    root = _repo(tmp_path, TWO_PASS)
+    original_post_init = state_manager.RepositoryAnalysisState.__post_init__
+    def mark_resync(state):
+        original_post_init(state)
+        state.resync_required = resync
+    monkeypatch.setattr(state_manager.RepositoryAnalysisState, "__post_init__", mark_resync)
+    original_save = state_manager.save_engine_state
+    forwarded = []
+    def tracked(*args, **kwargs):
+        forwarded.append(kwargs.get("prepared_partial_scc_preparation"))
+        return original_save(*args, **kwargs)
+    monkeypatch.setattr(state_manager, "save_engine_state", tracked)
+    _full(root, preview=True, partial=True)
+    assert forwarded == [None]
+    state, _ = _persisted(root)
+    assert state.cycle_partial_source_publication is None
```

## REMAINING UNKNOWN

UNKNOWN: Active LIVE installed-generation adoption, runtime import safety and active warning behavior. This stage did not connect warning filtering or run an active user's FULL.

## FINAL IMPLEMENTER OBSERVATION

CONTRACT_PROVED: WARN-2C-R1 implementation and focused tests pass. Architectural GO remains with ChatGPT. STOP after this stage.


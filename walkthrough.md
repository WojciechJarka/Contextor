# CONTEXTOR_P1D2G_FULL_PREVIEW_COMPLETENESS_GATE

## PREFLIGHT_RESULT

- DIRECT_EVIDENCE: Initial HEAD `f0638acecc63ba39fdc2130b8ad78bd73c6afd35`; worktree clean; `tests/test_original_worker_full_preview_completeness.py` absent.
- DIRECT_EVIDENCE: `ContextorFacade.analyze_project` retained the exact P1D2F branch and replacement anchor from the architect's instructions. Contextor preview resolved it at canonical revision 682 with `workspace_sync=verified`.
- CONTRACT_PROVED: `CycleSemanticsSnapshot` has `coverage_status`, `source_issues`, `observed_source_fingerprints`, and `cyclic_modules`; complete coverage requires every cyclic source and no issues.
- CODE_PATH_PROVED: `classify_full_cycle_semantics` allows bounded source issues to remain `fresh`. `SOURCE_FILE_LIMIT` is in `FULL_SOURCE_BOUNDED_EVALUATION_ISSUES` in `lifecycle.py`.
- DIRECT_EVIDENCE: All specified preconditions held. No `PREFLIGHT_MISMATCH`.

## NATIVE_CODEX_LITERAL_EDITS

- DIRECT_EVIDENCE: Native Codex `apply_patch` inserted only the supplied `elif` completeness gate in `facade.py` and created the new test file with the supplied literal content. A read-only comparison against the attachment returned `TEST_LITERAL_EXACT=True`.
- DIRECT_EVIDENCE: Opened Codex's native unstaged review. No other source or test was edited.

## FILES_CHANGED

- `contextor/core/api/facade.py` — one 8-line addition; full actual diff below.
- `tests/test_original_worker_full_preview_completeness.py` — new, 282 lines; full actual new-file diff below.
- `walkthrough.md` — overwritten as this report; its self-diff is excluded from the source/test diff requirement.

## ACTUAL_FACADE_DIFF

```diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 491905a..d017562 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -883,0 +884,8 @@ class ContextorFacade:
+            elif (
+                cycle_semantics.coverage_status
+                != "FILESYSTEM_STABLE_NON_ATOMIC"
+                or cycle_semantics.source_issues
+            ):
+                cycle_source_preparation = preview_unavailable(
+                    "CYCLE_SOURCE_EVIDENCE_INCOMPLETE"
+                )
```

## ACTUAL_NEW_TEST_CONTENT

```diff
diff --git a/tests/test_original_worker_full_preview_completeness.py b/tests/test_original_worker_full_preview_completeness.py
new file mode 100644
index 0000000..581c203
--- /dev/null
+++ b/tests/test_original_worker_full_preview_completeness.py
@@ -0,0 +1,282 @@
+"""P1D2G: complete semantic evidence gates FULL preview reindexing."""
+
+from __future__ import annotations
+
+from dataclasses import replace
+
+import pytest
+
+import contextor.core.api.facade as facade_module
+import contextor.core.cycle_semantics.materialization as materialization_module
+
+from contextor.core.analysis.process_pool_lifecycle import (
+    terminate_active_process_pools,
+)
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.cycle_semantics.lifecycle import (
+    classify_full_cycle_semantics,
+)
+from contextor.core.errors import AnalysisCancelled
+from tests.test_original_worker_full_preparation_optin import (
+    _flat_repo,
+    _full,
+    _stored,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_by_default(monkeypatch):
+    monkeypatch.setenv(
+        "CONTEXTOR_DISABLE_PROCESS_POOL",
+        "1",
+    )
+
+
+def test_p1d2g_t01_partial_but_fresh_skips_second_index(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    original_materialize = (
+        materialization_module.materialize_cycle_semantics
+    )
+    original_index = facade_module.index_repository
+    selections = []
+
+    def partial_materialization(*args, **kwargs):
+        snapshot = original_materialize(*args, **kwargs)
+
+        assert snapshot.cyclic_modules == ("a", "b")
+
+        partial = replace(
+            snapshot,
+            observed_source_fingerprints=(
+                snapshot.observed_source_fingerprints[1:]
+            ),
+            source_issues=(
+                ("a", "SOURCE_FILE_LIMIT"),
+            ),
+            coverage_status="PARTIAL_SOURCE_EVIDENCE",
+        )
+
+        assert classify_full_cycle_semantics(partial) == (
+            "fresh",
+            None,
+        )
+
+        return partial
+
+    def observed_index(*args, **kwargs):
+        selections.append(
+            kwargs.get("source_capture_module_ids")
+        )
+        return original_index(*args, **kwargs)
+
+    monkeypatch.setattr(
+        materialization_module,
+        "materialize_cycle_semantics",
+        partial_materialization,
+    )
+    monkeypatch.setattr(
+        facade_module,
+        "index_repository",
+        observed_index,
+    )
+
+    _, result = _full(root, preview=True)
+
+    assert selections == [None]
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == "UNAVAILABLE"
+    assert preview.reason == (
+        "CYCLE_SOURCE_EVIDENCE_INCOMPLETE"
+    )
+    assert preview.manifest is None
+    assert preview.source_modules == ()
+
+    state = _stored(root)
+
+    assert state.cycle_semantics_state == "fresh"
+    assert state.cycle_semantics is not None
+    assert state.cycle_semantics.coverage_status == (
+        "PARTIAL_SOURCE_EVIDENCE"
+    )
+    assert state.cycle_source_publication is None
+
+
+def test_p1d2g_t02_deferred_semantics_skips_second_index(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    original_index = facade_module.index_repository
+    selections = []
+
+    def failed_materialization(*args, **kwargs):
+        raise ValueError("synthetic semantic unavailability")
+
+    def observed_index(*args, **kwargs):
+        selections.append(
+            kwargs.get("source_capture_module_ids")
+        )
+        return original_index(*args, **kwargs)
+
+    monkeypatch.setattr(
+        materialization_module,
+        "materialize_cycle_semantics",
+        failed_materialization,
+    )
+    monkeypatch.setattr(
+        facade_module,
+        "index_repository",
+        observed_index,
+    )
+
+    _, result = _full(root, preview=True)
+
+    assert selections == [None]
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == "UNAVAILABLE"
+    assert preview.reason == "CYCLE_SEMANTICS_NOT_FRESH"
+    assert preview.manifest is None
+
+    state = _stored(root)
+
+    assert state.cycle_semantics is None
+    assert state.cycle_semantics_state == "deferred"
+    assert state.cycle_source_publication is None
+
+
+def test_p1d2g_t03_second_pass_cancellation_propagates(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    original_index = facade_module.index_repository
+    selections = []
+
+    def cancelled_index(*args, **kwargs):
+        selection = kwargs.get("source_capture_module_ids")
+        selections.append(selection)
+
+        if selection is not None:
+            raise AnalysisCancelled()
+
+        return original_index(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module,
+        "index_repository",
+        cancelled_index,
+    )
+
+    with pytest.raises(AnalysisCancelled):
+        _full(root, preview=True)
+
+    assert selections == [
+        None,
+        frozenset({"a", "b", "helper"}),
+    ]
+
+
+def test_p1d2g_t04_real_process_pool_full_preview(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    monkeypatch.delenv(
+        "CONTEXTOR_DISABLE_PROCESS_POOL",
+        raising=False,
+    )
+
+    terminate_active_process_pools(timeout=1.0)
+
+    try:
+        _, result = _full(root, preview=True)
+
+        preview = result.cycle_source_preparation_preview
+
+        assert preview.status == (
+            "PREPARED_UNPUBLISHED_NON_ATOMIC"
+        )
+        assert preview.reason is None
+        assert preview.manifest is not None
+        assert preview.manifest.authority == (
+            "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+        )
+        assert preview.source_modules == (
+            "a",
+            "b",
+            "helper",
+        )
+
+        state = _stored(root)
+
+        assert state.cycle_semantics_state == "fresh"
+        assert state.cycle_source_publication is None
+        assert not hasattr(
+            state,
+            "cycle_source_preparation_preview",
+        )
+
+    finally:
+        terminate_active_process_pools(timeout=1.0)
+
+
+def test_p1d2g_t05_oversized_closure_skips_second_index(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    imports = [
+        b"import b",
+        b"import helper",
+    ]
+
+    for number in range(14):
+        module_id = f"x{number}"
+
+        (root / f"{module_id}.py").write_bytes(
+            b"value = 1\n"
+        )
+        imports.append(
+            f"import {module_id}".encode("ascii")
+        )
+
+    (root / "a.py").write_bytes(
+        b"\n".join(imports) + b"\nvalue = 1\n"
+    )
+
+    original_index = facade_module.index_repository
+    selections = []
+
+    def observed_index(*args, **kwargs):
+        selections.append(
+            kwargs.get("source_capture_module_ids")
+        )
+        return original_index(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module,
+        "index_repository",
+        observed_index,
+    )
+
+    _, result = _full(root, preview=True)
+
+    preview = result.cycle_source_preparation_preview
+
+    assert selections == [None]
+    assert preview.status == "UNAVAILABLE"
+    assert preview.reason == "PLAN_CLOSURE_MODULE_LIMIT"
+    assert preview.manifest is None
+    assert preview.source_modules == ()
+
+    state = _stored(root)
+
+    assert state.cycle_source_publication is None
+
```

## PY_COMPILE_RESULT

- DIRECT_EVIDENCE: The requested `py_compile` command exited 0 for the two authorized code files.

## P1D2G_TEST_RESULTS

- DIRECT_EVIDENCE: The five new tests passed: `5 passed in 11.04s`.

## FOCUSED_REGRESSION_RESULTS

- DIRECT_EVIDENCE: The exact listed focused regression set passed: `204 passed in 44.58s`.

## PARTIAL_BUT_FRESH_SOURCE_GATE

- CONTRACT_PROVED: `SOURCE_FILE_LIMIT` can coexist with lifecycle `fresh` and `PARTIAL_SOURCE_EVIDENCE`; the new gate additionally requires `FILESYSTEM_STABLE_NON_ATOMIC` and empty `source_issues`.
- DIRECT_EVIDENCE: T01 supplies a partial-but-fresh snapshot and observes one index pass (`[None]`), `UNAVAILABLE` with `CYCLE_SOURCE_EVIDENCE_INCOMPLETE`, no manifest, and persisted semantics still `fresh` with no receipt.
- DIRECT_EVIDENCE: T02 defers semantic materialization and observes no second pass and `CYCLE_SEMANTICS_NOT_FRESH`.

## CANCELLATION_PROPAGATION

- DIRECT_EVIDENCE: T03 injects `AnalysisCancelled` in the second index pass; it propagates and the observed selections are the initial no-capture pass followed by the selected `a/b/helper` pass.

## REAL_PROCESS_POOL_FULL_PREVIEW

- DIRECT_EVIDENCE: T04 uses the real process pool in an isolated temporary repo; returned preview is `PREPARED_UNPUBLISHED_NON_ATOMIC`, source modules are `a/b/helper`, authority is `PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED`, and persisted receipt remains absent.

## OVERSIZED_CLOSURE_GATE

- DIRECT_EVIDENCE: T05 creates a closure beyond the 16-module limit; it observes one index pass, `PLAN_CLOSURE_MODULE_LIMIT`, no manifest and no persisted receipt.

## PERSISTED_RECEIPT_NEGATIVE_ASSERTIONS

- DIRECT_EVIDENCE: T01, T02, T04 and T05 each assert `state.cycle_source_publication is None`; T04 also asserts no preview field on persisted state.
- CODE_PATH_PROVED: The new condition only gates the existing opt-in branch before second indexing. The canonical state and save path were not modified.

## CANONICAL_WATCHER_OBSERVATIONS

- DIRECT_EVIDENCE: `get_live_events(after_revision=682)` returned continuous revision 683 for `contextor/core/api/facade.py`, `origin=desktop_watcher`, `operation=update_file`, `status=UPDATED`, `resync_required=false`; blast-radius state was `deferred`.
- DIRECT_EVIDENCE: A narrow symbol preview resolved `ContextorFacade.analyze_project` at canonical revision 684 with `workspace_sync=verified`; `cycle_semantics` family remained `stale`.
- INFERENCE: These readings establish watcher ingestion and canonical source visibility, not active process code adoption.

## AUTHORITY_LIMITS

- CONTRACT_PROVED: Successful preview remains prepared only, non-atomic and unpublished. The added gate does not change the lifecycle classifier or scenario model.
- DIRECT_EVIDENCE: No active-repository FULL, manual `update_file`, restart, reload, receipt sealing, store or IPC edit, or installed-generation verification was performed.
- UNKNOWN: Active loaded-code adoption and canonical generation/receipt authority remain unverified.

## FINAL_VERDICT

- DIRECT_EVIDENCE: P1D2G literal edit and new test completed; compile passed, all five new tests passed and the requested 204-test regression set passed. Actual source/test diffs are complete above.
- STOP: P1D2G only. Await the architect's next explicit `proceduj`.

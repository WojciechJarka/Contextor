# CONTEXTOR_P1D2F_FULL_PREPARED_ONLY_OPT_IN

## PREFLIGHT_RESULT

- DIRECT_EVIDENCE: Initial HEAD was `018588cf7596233c4f47370fe1db35b8f3e6b981`; initial worktree was clean. The P1D2E reindex-planning source and tests were already tracked at this HEAD. The authorized new test path did not exist.
- DIRECT_EVIDENCE: `ContextorFacade.analyze_project` still accepts `owner: str = "desktop_analysis"`; the initial `index_repository` call supplies no source-capture IDs. It builds `canonical_reexport_facts`, `trie`, and `package_root` before the first graph, and passes all three into `build_graph` before FULL cycle-semantics materialization and report generation.
- DIRECT_EVIDENCE: `cycle_semantics` and `cycle_semantics_state` are initialized and materialized/classified before `execute_global_pipeline`. `report_result.get("_analysis_result")` supplies `analysis_result`, which is returned at the end of the method.
- DIRECT_EVIDENCE: The existing `save_engine_state` call receives `state`, cache/path identity, revision and file-state payload only; no prepared-cycle-manifest argument is passed.
- DIRECT_EVIDENCE: Existing `tests/test_cycle_semantics_publication_live_integration.py::test_p1c2_t01_real_full_does_not_invent_receipt` remains present and asserts `state.cycle_source_publication is None` after FULL.
- CODE_PATH_PROVED: Contextor reads resolved `plan_original_worker_reindex`, `verify_original_worker_reindex`, `prepare_original_worker_cycle_manifest` and `materialize_reexport_facts_by_module` at canonical revision 680 with `workspace_sync=verified`. Their contracts retain non-atomic, supplied-input preparation and no publication.
- DIRECT_EVIDENCE: Contextor `get_symbol_implementation` returned `confirmation_required` for the 36.4 KiB complete `analyze_project` body. That boundary was preserved; a bounded preview and local read-only source ranges were used for the exact anchors. Contextor listed two `build_graph` definitions; local source confirms the later implementation accepts the supplied `trie`, `package_root` and re-export-facts arguments. All literal patch anchors matched, so preflight did not stop for mismatch.
- DIRECT_EVIDENCE: Current facade imports `AnalysisCancelled`, `build_graph`, and `index_repository`; the in-scope imports for `materialize_reexport_facts_by_module`, `build_trie`, and `detect_package_root` occur before the insertion point. No provided anchor drift was found.

## EXACT_NATIVE_CODEX_EDITS

- DIRECT_EVIDENCE: Applied the exact keyword-only `cycle_source_preparation_preview: bool = False` argument, strict `type(...) is bool` validation, local preparation result, supplied opt-in block before `from datetime import datetime`, and ephemeral result attachment after `_analysis_result` lookup.
- DIRECT_EVIDENCE: Created the supplied seven-test file byte-for-byte apart from line-ending normalization. Native Codex `apply_patch` was used; no source/test generation script or external patch utility was used.
- DIRECT_EVIDENCE: No edits were made to P1D2E files, any other production/test/docs file, or `save_engine_state`, store, IPC, receipt or publication code.

## FILES_CHANGED

- `contextor/core/api/facade.py` — modified; exact diff below.
- `tests/test_original_worker_full_preparation_optin.py` — new; exact diff below.
- `walkthrough.md` — overwritten with this execution report; report itself is excluded from the source/test diff list.

## ACTUAL_SOURCE_AND_TEST_CHANGES

- CODE_PATH_PROVED: The default-disabled opt-in performs no second index pass unless explicitly enabled and the existing cycle semantics are fresh.
- CODE_PATH_PROVED: The preview plans from the original index/graph, performs a separate selected-capture index pass, rebuilds re-export facts/trie/package root/graph for that second index, verifies the two passes, and only then calls the existing prepared-only manifest helper.
- CODE_PATH_PROVED: The second index and graph do not replace the primary FULL index/graph or enter canonical result domains. The prepared object is attached only to the returned `_analysis_result`; it is not added to `RepositoryAnalysisState`, summary data, report payloads or the existing save call.
- CODE_PATH_PROVED: `AnalysisCancelled` is re-raised. Other preview exceptions become an `UNAVAILABLE` preview and do not abort ordinary FULL processing.

## PY_COMPILE_RESULT

- DIRECT_EVIDENCE: Requested `py_compile` command exited 0 for `facade.py` and the new test.

## P1D2F_TEST_RESULTS

- DIRECT_EVIDENCE: `pytest -q tests/test_original_worker_full_preparation_optin.py` — **7 passed in 7.53s**.

## FOCUSED_REGRESSION_RESULTS

- DIRECT_EVIDENCE: Exact requested focused regression command exited 0 — **199 passed in 39.41s**.
- DIRECT_EVIDENCE: Regression scope was limited to the supplied test plus named isolated P1D2E/P1D/P1C/indexer/cycle-semantics test files. No FULL analysis ran against the user's active Contextor repository.

## DEFAULT_FULL_BEHAVIOR

- DIRECT_EVIDENCE: T01 observes exactly one `index_repository` call with `source_capture_module_ids=None` under the default argument, no returned preview attribute, and no persisted `cycle_source_publication` receipt.
- CONTRACT_PROVED: The opt-in parameter is keyword-only and defaults to `False`; invalid non-bool values are rejected before the local stage callback is defined.

## OPTIN_SECOND_PASS_AND_PREPARATION

- DIRECT_EVIDENCE: T02 observes the first index with no capture selection and a second index with exactly `frozenset({"a", "b", "helper"})`; it receives a `PREPARED_UNPUBLISHED_NON_ATOMIC` result with the prepared-only authority label.
- DIRECT_EVIDENCE: T02 also asserts that the ephemeral preview is absent from summary data and persisted state, while canonical cycle semantics remain fresh and `cycle_source_publication` remains `None`.
- CONTRACT_PROVED: A successful preview is not an authenticated canonical generation, receipt, publication or runtime adoption claim.

## FAIL_CLOSED_RESULTS

- DIRECT_EVIDENCE: T03 unsupported package model returns `UNAVAILABLE` with `P1C0_SOURCE_EVIDENCE_UNAVAILABLE`, no manifest and no source modules.
- DIRECT_EVIDENCE: T04 acyclic graph returns `PLAN_NO_CYCLIC_COMPONENTS` and verifies there is no second index pass.
- DIRECT_EVIDENCE: T05 changes a source file before the second pass and receives `VERIFY_REINDEX_SOURCE_CHANGED`, no manifest and no source modules.
- DIRECT_EVIDENCE: T06 second-pass exception returns `PREVIEW_EXECUTION_ERROR:RuntimeError`, no manifest, while FULL completes and persisted receipt remains absent.
- DIRECT_EVIDENCE: T07 rejects `None`, integer values, strings, lists and dictionaries with `ValueError`.

## PERSISTED_RECEIPT_NEGATIVE_ASSERTIONS

- DIRECT_EVIDENCE: New T01–T06 assert that the persisted `cycle_source_publication` remains `None` in default, successful preview, unsupported-model, acyclic, source-drift and exception cases.
- DIRECT_EVIDENCE: T02 asserts no `cycle_source_preparation_preview` field exists on persisted state; the preview is only attached to the returned analysis result.
- DIRECT_EVIDENCE: Existing P1C2 T01 still asserts that current FULL does not invent a receipt. No receipt sealing or publication path was changed or invoked.

## CANONICAL_WATCHER_OBSERVATIONS

- DIRECT_EVIDENCE: Read-only `get_live_events(after_revision=680)` returned continuous revision 681, `origin=desktop_watcher`, `operation=update_file`, `status=UPDATED`, for `contextor/core/api/facade.py`; `resync_required=false`.
- DIRECT_EVIDENCE: A narrow `get_symbol_implementation` preview then resolved `ContextorFacade.analyze_project` with `workspace_sync=verified`, `canonical_state=fresh`, provenance `live`, at canonical revision 682. The cycle-semantics family remained stale; no freshness was forced.
- INFERENCE: Watcher ingestion and canonical source visibility do not establish that a running runtime imported or adopted this implementation.

## ACTIVE_RUNTIME_ADOPTION_LIMITS

- UNKNOWN: Active runtime loaded-code identity/adoption was not inspected or established. No restart, reload, installed-generation verification, or active-repository FULL was performed.
- DIRECT_EVIDENCE: No `update_file`, snapshot publication, receipt sealing, save-path modification or LIVE state mutation was requested or performed.

## FINAL_VERDICT

- DIRECT_EVIDENCE: Supplied P1D2F changes were applied; both files compile, all seven new tests pass, and the specified regression set passes (199 tests).
- CONTRACT_PROVED: The feature is an explicit prepared-only preview path and preserves default FULL behavior and the existing negative receipt invariant.
- UNKNOWN: This stage does not establish canonical receipt publication, generation authentication, active runtime adoption, or broader runtime safety.
- STOP: P1D2F only. Await the architect's next explicit `proceduj`.

## ACTUAL_DIFF

### `contextor/core/api/facade.py`

```diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 62b2b61..491905a 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -562,6 +562,8 @@ class ContextorFacade:
         progress_callback=None,
         additional_excludes: list[str] | None = None,
         owner: str = "desktop_analysis",
+        *,
+        cycle_source_preparation_preview: bool = False,
     ) -> list:
         """
         Analyzes full project hierarchy, builds dependency graph, evaluates
@@ -585,6 +587,13 @@ class ContextorFacade:
         live_publish_expected_state_id = None
         live_publish_expected_revision = None
 
+        if type(cycle_source_preparation_preview) is not bool:
+            raise ValueError(
+                "cycle_source_preparation_preview must be bool"
+            )
+
+        cycle_source_preparation = None
+
         def emit_stage_end(stage: str, started: float) -> None:
             elapsed_ms = (time.monotonic() - started) * 1000.0
             trace_event(
@@ -847,6 +856,130 @@ class ContextorFacade:
                 ),
             )
 
+        if cycle_source_preparation_preview:
+            from contextor.core.cycle_semantics.original_worker_preparation import (
+                OriginalWorkerManifestPreparation,
+                prepare_original_worker_cycle_manifest,
+            )
+            from contextor.core.cycle_semantics.original_worker_reindex_planning import (
+                plan_original_worker_reindex,
+                verify_original_worker_reindex,
+            )
+
+            def preview_unavailable(reason):
+                return OriginalWorkerManifestPreparation(
+                    status="UNAVAILABLE",
+                    reason=reason,
+                    manifest=None,
+                    source_modules=(),
+                )
+
+            if (
+                cycle_semantics is None
+                or cycle_semantics_state != "fresh"
+            ):
+                cycle_source_preparation = preview_unavailable(
+                    "CYCLE_SEMANTICS_NOT_FRESH"
+                )
+            else:
+                try:
+                    plan = plan_original_worker_reindex(
+                        index,
+                        graph.hard_edges,
+                    )
+
+                    if plan.status != "READY_FOR_REINDEX_NON_ATOMIC":
+                        cycle_source_preparation = preview_unavailable(
+                            "PLAN_" + (
+                                plan.reason or "UNAVAILABLE"
+                            )
+                        )
+                    else:
+                        captured_index = index_repository(
+                            path,
+                            excludes=excludes,
+                            extra_ignored_dirs=extra_dirs,
+                            source_capture_module_ids=(
+                                plan.selected_module_ids
+                            ),
+                        )
+
+                        captured_modules = captured_index.modules
+
+                        captured_reexport_facts = (
+                            materialize_reexport_facts_by_module(
+                                captured_modules,
+                                captured_index.reference_facts_by_module,
+                            )
+                        )
+
+                        captured_trie = build_trie(
+                            captured_modules.keys()
+                        )
+                        captured_package_root = detect_package_root(
+                            captured_modules,
+                            captured_trie,
+                        )
+
+                        captured_graph = build_graph(
+                            captured_modules,
+                            trie=captured_trie,
+                            package_root=captured_package_root,
+                            reexport_facts_by_module=(
+                                captured_reexport_facts
+                            ),
+                        )
+
+                        verification = verify_original_worker_reindex(
+                            plan,
+                            index,
+                            graph.hard_edges,
+                            captured_index,
+                            captured_graph.hard_edges,
+                        )
+
+                        if verification.status != (
+                            "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
+                        ):
+                            cycle_source_preparation = preview_unavailable(
+                                "VERIFY_" + (
+                                    verification.reason
+                                    or "UNAVAILABLE"
+                                )
+                            )
+                        else:
+                            cycle_source_preparation = (
+                                prepare_original_worker_cycle_manifest(
+                                    captured_index,
+                                    captured_graph.hard_edges,
+                                    cycle_semantics,
+                                )
+                            )
+
+                except AnalysisCancelled:
+                    raise
+
+                except Exception as exc:
+                    cycle_source_preparation = preview_unavailable(
+                        "PREVIEW_EXECUTION_ERROR:"
+                        + type(exc).__name__
+                    )
+
+            trace_event(
+                "FULL",
+                "CYCLE_SOURCE_PREPARATION_PREVIEW",
+                status=cycle_source_preparation.status,
+                reason=(
+                    cycle_source_preparation.reason or "NONE"
+                ),
+                source_count=len(
+                    cycle_source_preparation.source_modules
+                ),
+                authority=(
+                    "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+                ),
+            )
+
         from datetime import datetime
         datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
 
@@ -894,6 +1027,14 @@ class ContextorFacade:
         canonical_setup_started = canonical_materialization_started
         analysis_result = report_result.get("_analysis_result")
 
+        if (
+            cycle_source_preparation_preview
+            and analysis_result is not None
+        ):
+            analysis_result.cycle_source_preparation_preview = (
+                cycle_source_preparation
+            )
+
         progress.begin("Persisting canonical LIVE snapshot")
         if analysis_result:
             from contextor.core.analysis.state_manager import (
```

### `tests/test_original_worker_full_preparation_optin.py`

```diff
diff --git a/tests/test_original_worker_full_preparation_optin.py b/tests/test_original_worker_full_preparation_optin.py
new file mode 100644
index 0000000..66f6ed2
--- /dev/null
+++ b/tests/test_original_worker_full_preparation_optin.py
@@ -0,0 +1,298 @@
+"""P1D2F: explicit FULL opt-in prepares evidence without publication."""
+
+from __future__ import annotations
+
+import pytest
+
+import contextor.core.api.facade as facade_module
+from contextor.core.analysis.state_manager import (
+    load_engine_state,
+)
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.live_state.store import read_metadata
+from contextor.core.paths import repo_cache_dir
+
+
+@pytest.fixture(autouse=True)
+def _inline_index(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _flat_repo(tmp_path):
+    root = tmp_path / "repo"
+    root.mkdir()
+    (root / "a.py").write_bytes(
+        b"import b\nimport helper\nvalue = 1\n"
+    )
+    (root / "b.py").write_bytes(
+        b"import a\nvalue = 2\n"
+    )
+    (root / "helper.py").write_bytes(
+        b"value = 3\n"
+    )
+    (root / "unrelated.py").write_bytes(
+        b"value = 999\n"
+    )
+    return root
+
+
+def _package_repo(tmp_path):
+    root = tmp_path / "repo"
+    pkg = root / "pkg"
+    pkg.mkdir(parents=True)
+    (pkg / "__init__.py").write_bytes(b"")
+    (pkg / "a.py").write_bytes(
+        b"import pkg.b\n"
+        b"def fa():\n"
+        b"    return 1\n"
+    )
+    (pkg / "b.py").write_bytes(
+        b"import pkg.a\n"
+        b"def fb():\n"
+        b"    return 2\n"
+    )
+    return root
+
+
+def _full(root, *, preview=False):
+    errors, result = ContextorFacade.analyze_project(
+        str(root),
+        cycle_source_preparation_preview=preview,
+    )
+    assert result is not None
+    return errors, result
+
+
+def _stored(root):
+    cache = repo_cache_dir(root)
+    metadata = read_metadata(cache)
+    assert metadata is not None
+    state = load_engine_state(
+        str(cache),
+        metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=str(root.resolve()),
+    )
+    assert state is not None
+    return state
+
+
+def test_p1d2f_t01_default_no_preview_no_second_index(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+    original = facade_module.index_repository
+    selections = []
+
+    def observed(*args, **kwargs):
+        selections.append(kwargs.get("source_capture_module_ids"))
+        return original(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module,
+        "index_repository",
+        observed,
+    )
+
+    _, result = ContextorFacade.analyze_project(str(root))
+
+    assert result is not None
+    assert selections == [None]
+    assert not hasattr(
+        result,
+        "cycle_source_preparation_preview",
+    )
+
+    state = _stored(root)
+    assert state.cycle_source_publication is None
+
+
+def test_p1d2f_t02_flat_full_optin_prepared_only(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+    original = facade_module.index_repository
+    selections = []
+
+    def observed(*args, **kwargs):
+        selections.append(kwargs.get("source_capture_module_ids"))
+        return original(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module,
+        "index_repository",
+        observed,
+    )
+
+    _, result = _full(root, preview=True)
+
+    assert len(selections) == 2
+    assert selections[0] is None
+    assert selections[1] == frozenset({
+        "a", "b", "helper",
+    })
+
+    prepared = result.cycle_source_preparation_preview
+
+    assert prepared.status == (
+        "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    )
+    assert prepared.reason is None
+    assert prepared.source_modules == (
+        "a", "b", "helper",
+    )
+    assert prepared.manifest is not None
+    assert prepared.manifest.source_manifest_sha256 is not None
+    assert prepared.manifest.authority == (
+        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+    )
+    assert prepared.manifest.components[0].members == (
+        "a", "b",
+    )
+
+    assert (
+        "cycle_source_preparation_preview"
+        not in result.summary_data
+    )
+
+    state = _stored(root)
+    assert state.cycle_source_publication is None
+    assert state.cycle_semantics_state == "fresh"
+    assert not hasattr(
+        state,
+        "cycle_source_preparation_preview",
+    )
+
+
+def test_p1d2f_t03_unsupported_package_full_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = _package_repo(tmp_path)
+    _, result = _full(root, preview=True)
+
+    prepared = result.cycle_source_preparation_preview
+
+    assert prepared.status == "UNAVAILABLE"
+    assert prepared.reason == (
+        "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+    )
+    assert prepared.manifest is None
+    assert prepared.source_modules == ()
+
+    state = _stored(root)
+    assert state.cycle_source_publication is None
+    assert state.cycle_semantics_state == "fresh"
+
+
+def test_p1d2f_t04_no_cycles_skips_second_index(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    (root / "b.py").write_bytes(
+        b"value = 2\n"
+    )
+
+    original = facade_module.index_repository
+    selections = []
+
+    def observed(*args, **kwargs):
+        selections.append(kwargs.get("source_capture_module_ids"))
+        return original(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module,
+        "index_repository",
+        observed,
+    )
+
+    _, result = _full(root, preview=True)
+
+    prepared = result.cycle_source_preparation_preview
+
+    assert selections == [None]
+    assert prepared.status == "UNAVAILABLE"
+    assert prepared.reason == "PLAN_NO_CYCLIC_COMPONENTS"
+    assert prepared.manifest is None
+
+    state = _stored(root)
+    assert state.cycle_source_publication is None
+
+
+def test_p1d2f_t05_second_pass_source_drift_rejected(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+    original = facade_module.index_repository
+
+    def drifted(*args, **kwargs):
+        if kwargs.get("source_capture_module_ids") is not None:
+            (root / "helper.py").write_bytes(
+                b"value = 300\n"
+            )
+        return original(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module,
+        "index_repository",
+        drifted,
+    )
+
+    _, result = _full(root, preview=True)
+
+    prepared = result.cycle_source_preparation_preview
+
+    assert prepared.status == "UNAVAILABLE"
+    assert prepared.reason == (
+        "VERIFY_REINDEX_SOURCE_CHANGED"
+    )
+    assert prepared.manifest is None
+    assert prepared.source_modules == ()
+
+    state = _stored(root)
+    assert state.cycle_source_publication is None
+
+
+def test_p1d2f_t06_second_pass_exception_fails_closed(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+    original = facade_module.index_repository
+
+    def failed(*args, **kwargs):
+        if kwargs.get("source_capture_module_ids") is not None:
+            raise RuntimeError("injected preview failure")
+        return original(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module,
+        "index_repository",
+        failed,
+    )
+
+    _, result = _full(root, preview=True)
+
+    prepared = result.cycle_source_preparation_preview
+
+    assert prepared.status == "UNAVAILABLE"
+    assert prepared.reason == (
+        "PREVIEW_EXECUTION_ERROR:RuntimeError"
+    )
+    assert prepared.manifest is None
+
+    state = _stored(root)
+    assert state.cycle_source_publication is None
+
+
+def test_p1d2f_t07_invalid_optin_argument_rejected(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+
+    for invalid in (None, 0, 1, "yes", [], {}):
+        with pytest.raises(ValueError):
+            ContextorFacade.analyze_project(
+                str(root),
+                cycle_source_preparation_preview=invalid,
+            )
+
```

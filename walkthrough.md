# CONTEXTOR_P1D2I_EXPLICIT_FULL_CYCLE_MANIFEST_COPUBLICATION

## PREFLIGHT_RESULT

DIRECT_EVIDENCE: Initial HEAD `5f8ebbfa1bbb919078932852abbc740f4f5662e5`, clean worktree. Contextor MCP resolved `ContextorFacade.analyze_project` at lines 558-1568 with `workspace_sync=verified`, revision 687. The local source had the exact signature, strict preview boolean validation, P1D2G completeness path, preview result assignment, `RepositoryAnalysisState` construction, and the exact `save_engine_state` call anchor. `save_engine_state` accepted `prepared_cycle_manifest: Any = None`. `save_snapshot` accepted that argument and called `seal_prepared_cycle_manifest` under `_acquire_lock`, before metadata commit. The new test path was absent. `PREFLIGHT_MISMATCH=NONE`.

## NATIVE_CODEX_LITERAL_EDITS

DIRECT_EVIDENCE: Applied the three architect-authored facade replacements and created the supplied test file using native Codex `apply_patch`. No other production or test path was edited.

## FILES_CHANGED

- `contextor/core/api/facade.py`
- `tests/test_original_worker_full_receipt_optin.py`

`walkthrough.md` is this report and is excluded from source/test diffs.

## ACTUAL_FACADE_DIFF

```diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index d017562..9a7a0b1 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -566,0 +567 @@ class ContextorFacade:
+        cycle_source_publication_opt_in: bool = False,
@@ -594,0 +596,14 @@ class ContextorFacade:
+        if type(cycle_source_publication_opt_in) is not bool:
+            raise ValueError(
+                "cycle_source_publication_opt_in must be bool"
+            )
+
+        if (
+            cycle_source_publication_opt_in
+            and not cycle_source_preparation_preview
+        ):
+            raise ValueError(
+                "cycle_source_publication_opt_in requires "
+                "cycle_source_preparation_preview=True"
+            )
+
@@ -1368,0 +1384,37 @@ class ContextorFacade:
+            store_manifest_kwargs = {}
+
+            if (
+                cycle_source_publication_opt_in
+                and cycle_source_preparation is not None
+                and cycle_source_preparation.status
+                == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+                and cycle_source_preparation.reason is None
+                and cycle_source_preparation.manifest is not None
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
+                from contextor.core.cycle_semantics.contracts import (
+                    fingerprint_hard_edges,
+                )
+
+                try:
+                    canonical_graph_sha256 = fingerprint_hard_edges(
+                        state.dependency_graph.hard_edges
+                    )
+                except (AttributeError, TypeError, ValueError):
+                    canonical_graph_sha256 = None
+
+                if canonical_graph_sha256 == (
+                    cycle_source_preparation.manifest.graph_sha256
+                ):
+                    store_manifest_kwargs[
+                        "prepared_cycle_manifest"
+                    ] = cycle_source_preparation.manifest
+
@@ -1378,0 +1431 @@ class ContextorFacade:
+                **store_manifest_kwargs,
```

## ACTUAL_NEW_TEST_CONTENT

The following is the full actual new-file diff.

```diff
diff --git a/tests/test_original_worker_full_receipt_optin.py b/tests/test_original_worker_full_receipt_optin.py
new file mode 100644
index 0000000..c18e6fe
--- /dev/null
+++ b/tests/test_original_worker_full_receipt_optin.py
@@ -0,0 +1,412 @@
+"""P1D2I: explicitly publish prepared FULL claims with one generation."""
+
+from __future__ import annotations
+
+from dataclasses import replace
+
+import pytest
+
+import contextor.core.api.facade as facade_module
+import contextor.core.cycle_semantics.original_worker_preparation as preparation_module
+
+from contextor.core.analysis.process_pool_lifecycle import (
+    terminate_active_process_pools,
+)
+from contextor.core.analysis.state_manager import (
+    load_engine_state,
+)
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.cycle_semantics.publication_binding import (
+    PUBLICATION_AUTHORITY,
+    CanonicalCycleManifestReceipt,
+    verify_co_published_cycle_manifest,
+)
+from contextor.core.live_state.store import read_metadata
+from contextor.core.paths import repo_cache_dir
+
+from tests.test_original_worker_full_preparation_optin import (
+    _flat_repo,
+    _package_repo,
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
+def _run(root, *, preview=False, publication=False):
+    errors, result = ContextorFacade.analyze_project(
+        str(root),
+        cycle_source_preparation_preview=preview,
+        cycle_source_publication_opt_in=publication,
+    )
+    assert result is not None
+    assert isinstance(errors, list)
+    return result
+
+
+def _persisted(root):
+    cache = repo_cache_dir(root)
+    metadata = read_metadata(cache)
+
+    assert metadata is not None
+
+    state = load_engine_state(
+        str(cache),
+        metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=str(root.resolve()),
+    )
+
+    assert state is not None
+    return state, metadata
+
+
+def _assert_same_generation_receipt(state, metadata):
+    receipt = state.cycle_source_publication
+
+    assert isinstance(
+        receipt,
+        CanonicalCycleManifestReceipt,
+    )
+    assert receipt.authority == PUBLICATION_AUTHORITY
+    assert receipt.revision == metadata.revision
+    assert receipt.state_id == metadata.state_id
+    assert receipt.repo_id == metadata.repo_id
+    assert receipt.root_path == metadata.root_path
+
+    assert verify_co_published_cycle_manifest(
+        state,
+        revision=metadata.revision,
+        state_id=metadata.state_id,
+        repo_id=metadata.repo_id,
+        root_path=metadata.root_path,
+    )
+
+    return receipt
+
+
+def test_p1d2i_t01_default_full_remains_receipt_free(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+
+    errors, result = ContextorFacade.analyze_project(
+        str(root)
+    )
+
+    assert result is not None
+    assert isinstance(errors, list)
+    assert not hasattr(
+        result,
+        "cycle_source_preparation_preview",
+    )
+
+    state, metadata = _persisted(root)
+
+    assert metadata.revision >= 1
+    assert state.cycle_source_publication is None
+
+
+def test_p1d2i_t02_preview_only_remains_unpublished(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+    result = _run(root, preview=True)
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == (
+        "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    )
+    assert preview.manifest is not None
+
+    state, _metadata = _persisted(root)
+
+    assert state.cycle_source_publication is None
+
+
+def test_p1d2i_t03_explicit_full_same_generation_receipt(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+    result = _run(
+        root,
+        preview=True,
+        publication=True,
+    )
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == (
+        "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    )
+    assert preview.reason is None
+    assert preview.manifest is not None
+    assert preview.manifest.authority == (
+        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+    )
+
+    state, metadata = _persisted(root)
+
+    assert state.cycle_semantics_state == "fresh"
+    assert state.cycles_state == "fresh"
+
+    receipt = _assert_same_generation_receipt(
+        state,
+        metadata,
+    )
+
+    assert receipt.prepared_manifest == preview.manifest
+    assert receipt.prepared_manifest.graph_sha256 == (
+        state.cycle_semantics.graph_sha256
+    )
+    assert receipt.prepared_manifest.components[0].members == (
+        "a",
+        "b",
+    )
+
+    assert (
+        "cycle_source_preparation_preview"
+        not in result.summary_data
+    )
+    assert not hasattr(
+        state,
+        "cycle_source_preparation_preview",
+    )
+
+
+def test_p1d2i_t04_publication_requires_preview(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+
+    with pytest.raises(
+        ValueError,
+        match="requires cycle_source_preparation_preview",
+    ):
+        _run(
+            root,
+            preview=False,
+            publication=True,
+        )
+
+    assert read_metadata(repo_cache_dir(root)) is None
+
+
+def test_p1d2i_t05_invalid_publication_argument_rejected(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+
+    for invalid in (None, 0, 1, "yes", [], {}):
+        with pytest.raises(
+            ValueError,
+            match="cycle_source_publication_opt_in must be bool",
+        ):
+            ContextorFacade.analyze_project(
+                str(root),
+                cycle_source_preparation_preview=True,
+                cycle_source_publication_opt_in=invalid,
+            )
+
+    assert read_metadata(repo_cache_dir(root)) is None
+
+
+def test_p1d2i_t06_unsupported_package_not_published(
+    tmp_path, isolated_dirs,
+):
+    root = _package_repo(tmp_path)
+
+    result = _run(
+        root,
+        preview=True,
+        publication=True,
+    )
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == "UNAVAILABLE"
+    assert preview.reason == (
+        "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+    )
+    assert preview.manifest is None
+
+    state, _metadata = _persisted(root)
+    assert state.cycle_source_publication is None
+
+
+def test_p1d2i_t07_acyclic_repository_not_published(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+    (root / "b.py").write_bytes(b"value = 2\n")
+
+    result = _run(
+        root,
+        preview=True,
+        publication=True,
+    )
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == "UNAVAILABLE"
+    assert preview.reason == "PLAN_NO_CYCLIC_COMPONENTS"
+    assert preview.manifest is None
+
+    state, _metadata = _persisted(root)
+    assert state.cycle_source_publication is None
+
+
+def test_p1d2i_t08_second_pass_source_drift_not_published(
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
+    result = _run(
+        root,
+        preview=True,
+        publication=True,
+    )
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == "UNAVAILABLE"
+    assert preview.reason == "VERIFY_REINDEX_SOURCE_CHANGED"
+    assert preview.manifest is None
+
+    state, _metadata = _persisted(root)
+    assert state.cycle_source_publication is None
+
+
+def test_p1d2i_t09_invalid_manifest_rejects_store_commit(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    original = (
+        preparation_module.prepare_original_worker_cycle_manifest
+    )
+
+    def forged(*args, **kwargs):
+        result = original(*args, **kwargs)
+
+        if result.manifest is None:
+            return result
+
+        return replace(
+            result,
+            manifest=replace(
+                result.manifest,
+                source_manifest_sha256="f" * 64,
+            ),
+        )
+
+    monkeypatch.setattr(
+        preparation_module,
+        "prepare_original_worker_cycle_manifest",
+        forged,
+    )
+
+    result = _run(
+        root,
+        preview=True,
+        publication=True,
+    )
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == (
+        "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    )
+    assert preview.manifest is not None
+
+    assert read_metadata(repo_cache_dir(root)) is None
+    assert result.live_publish_status == "not_attempted"
+
+
+def test_p1d2i_t10_next_full_without_optin_drops_receipt(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+
+    _run(
+        root,
+        preview=True,
+        publication=True,
+    )
+
+    first_state, first_metadata = _persisted(root)
+
+    first_receipt = _assert_same_generation_receipt(
+        first_state,
+        first_metadata,
+    )
+
+    _run(root)
+
+    second_state, second_metadata = _persisted(root)
+
+    assert second_metadata.revision == (
+        first_metadata.revision + 1
+    )
+    assert second_state.cycle_source_publication is None
+    assert first_state.cycle_source_publication == first_receipt
+
+
+def test_p1d2i_t11_process_pool_explicit_publication(
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
+        result = _run(
+            root,
+            preview=True,
+            publication=True,
+        )
+
+        preview = result.cycle_source_preparation_preview
+
+        assert preview.status == (
+            "PREPARED_UNPUBLISHED_NON_ATOMIC"
+        )
+        assert preview.manifest is not None
+
+        state, metadata = _persisted(root)
+
+        receipt = _assert_same_generation_receipt(
+            state,
+            metadata,
+        )
+
+        assert receipt.prepared_manifest == preview.manifest
+        assert state.cycle_semantics_state == "fresh"
+
+    finally:
+        terminate_active_process_pools(timeout=1.0)
```

## PY_COMPILE_RESULT

DIRECT_EVIDENCE: `python -m py_compile contextor/core/api/facade.py tests/test_original_worker_full_receipt_optin.py` exited 0.

## P1D2I_TEST_RESULTS

DIRECT_EVIDENCE: `pytest -q tests/test_original_worker_full_receipt_optin.py`: 11 passed in 38.96s.

## FOCUSED_REGRESSION_RESULTS

DIRECT_EVIDENCE: Exact 15-file focused command from the task: 237 passed in 72.35s. No full suite and no FULL on the active Contextor repository.

## DEFAULT_FULL_INVARIANTS

CONTRACT_PROVED: T01 observed no preview attribute and no persisted receipt for default FULL. Both options default to False.

## PREVIEW_ONLY_INVARIANTS

CONTRACT_PROVED: T02 observed prepared preview with no persisted receipt.

## EXPLICIT_PUBLICATION_OPT_IN

CODE_PATH_PROVED: Facade forwards `prepared_cycle_manifest` only when both opt-ins and literal state/graph/freshness conditions pass. It calls `save_engine_state`; the store remains the only sealer.

## SAME_GENERATION_RECEIPT

CONTRACT_PROVED: T03 matched persisted receipt revision, state_id, repo_id, root_path, prepared manifest, graph digest, and verifier against committed metadata.

## FAIL_CLOSED_CASES

CONTRACT_PROVED: T04-T08 rejected missing preview, invalid opt-in values, unsupported package, acyclic repository, and second-pass source drift; no receipt was published.

## REJECTED_MANIFEST_NO_COMMIT

CONTRACT_PROVED: T09 forged manifest caused no store metadata commit and LIVE publication remained `not_attempted`.

## LATER_GENERATION_INVALIDATION

CONTRACT_PROVED: T10 observed a later default FULL generation without a receipt, while the earlier in-memory state retained its earlier receipt.

## PROCESS_POOL_VERIFICATION

CONTRACT_PROVED: T11 passed with the process pool enabled and verified the persisted receipt against its generation.

## CANONICAL_WATCHER_OBSERVATIONS

DIRECT_EVIDENCE: `get_live_events(after_revision=687)` returned `latest_revision=687`, `continuity=continuous`, `resync_required=false`, zero events. The subsequent Contextor symbol read returned `workspace_sync=out_of_sync` for edited facade source. No watcher adoption event was observed.

## ACTIVE_RUNTIME_ADOPTION_LIMITS

UNKNOWN: Active LIVE loaded-code adoption of this facade edit is unproved. Source changes and isolated tests do not establish runtime adoption. Restart/reload may be needed before an active-runtime certification; none was performed.

## FINAL_VERDICT

CONTRACT_PROVED: Literal P1D2I implementation and specified focused tests passed. DIRECT_EVIDENCE: `git diff --check` for facade exited 0. UNKNOWN: active LIVE adoption and repository-wide source atomicity/authentication/import safety. STOP after P1D2I; await explicit `proceduj`.

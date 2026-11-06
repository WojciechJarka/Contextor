# CONTEXTOR C16-B03-P1D3D

## FILES_CHANGED

- contextor/core/api/facade.py
- tests/test_cycle_semantics_optional_child_full_preview.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2, five specified modules, `-B -m pytest -q -rs -p no:cacheprovider`, basetemp outside repository: 60 passed, 1 failed in 37.34 s. Failed: `test_optional_source_drift_fails_closed`. Actual reason `VERIFY_REINDEX_GRAPH_CHANGED`; expected `VERIFY_REINDEX_SOURCE_CHANGED`. No further code or test edits. `git diff --check` passed.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP module contexts for both changed modules: canonical_revision=1026, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, syntax_errors=0. Cycle semantics family stale. No production FULL, update_file, restart, or commit.

## FULL_DIFFS

```diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index c394d02..bab03bc 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -566,6 +566,7 @@ class ContextorFacade:
         cycle_source_preparation_preview: bool = False,
         cycle_source_publication_opt_in: bool = False,
         cycle_partial_source_publication_opt_in: bool = False,
+        cycle_source_selection: str = "HARD_ONLY",
     ) -> list:
         """
         Analyzes full project hierarchy, builds dependency graph, evaluates
@@ -622,6 +623,38 @@ class ContextorFacade:
                 "cycle_source_preparation_preview=True"
             )
 
+        if (
+            type(cycle_source_selection) is not str
+            or cycle_source_selection not in {
+                "HARD_ONLY",
+                "OPTIONAL_NAMED_CHILDREN",
+            }
+        ):
+            raise ValueError(
+                "cycle_source_selection must be "
+                "HARD_ONLY or OPTIONAL_NAMED_CHILDREN"
+            )
+
+        if (
+            cycle_source_selection == "OPTIONAL_NAMED_CHILDREN"
+            and not cycle_source_preparation_preview
+        ):
+            raise ValueError(
+                "OPTIONAL_NAMED_CHILDREN requires "
+                "cycle_source_preparation_preview=True"
+            )
+
+        if (
+            cycle_source_selection == "OPTIONAL_NAMED_CHILDREN"
+            and (
+                cycle_source_publication_opt_in
+                or cycle_partial_source_publication_opt_in
+            )
+        ):
+            raise ValueError(
+                "OPTIONAL_NAMED_CHILDREN publication unsupported"
+            )
+
         cycle_source_preparation = None
 
         def emit_stage_end(stage: str, started: float) -> None:
@@ -902,6 +935,7 @@ class ContextorFacade:
                     reason=reason,
                     manifest=None,
                     source_modules=(),
+                    source_selection=cycle_source_selection,
                 )
 
             if (
@@ -924,6 +958,7 @@ class ContextorFacade:
                     plan = plan_original_worker_reindex(
                         index,
                         graph.hard_edges,
+                        source_selection=cycle_source_selection,
                     )
 
                     if plan.status != "READY_FOR_REINDEX_NON_ATOMIC":
@@ -991,6 +1026,7 @@ class ContextorFacade:
                                     captured_index,
                                     captured_graph.hard_edges,
                                     cycle_semantics,
+                                    source_selection=cycle_source_selection,
                                 )
                             )
 
@@ -1401,6 +1437,7 @@ class ContextorFacade:
             if (
                 cycle_source_publication_opt_in
                 and cycle_source_preparation is not None
+                and cycle_source_preparation.source_selection == "HARD_ONLY"
                 and cycle_source_preparation.status
                 == "PREPARED_UNPUBLISHED_NON_ATOMIC"
                 and cycle_source_preparation.reason is None
@@ -1436,6 +1473,7 @@ class ContextorFacade:
             if (
                 cycle_partial_source_publication_opt_in
                 and cycle_source_preparation is not None
+                and cycle_source_preparation.source_selection == "HARD_ONLY"
                 and state.cycle_semantics is cycle_semantics
                 and state.cycle_semantics_state == "fresh"
                 and state.cycles_state == "fresh"

diff --git a/tests/test_cycle_semantics_optional_child_full_preview.py b/tests/test_cycle_semantics_optional_child_full_preview.py
new file mode 100644
index 0000000..0c86154
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_child_full_preview.py
@@ -0,0 +1,263 @@
+"""P1D3D: official optional FULL preview is unpublished."""
+
+from dataclasses import replace
+
+import pytest
+
+import contextor.core.api.facade as facade_module
+
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.cycle_semantics.generation_manifest import (
+    OPTIONAL_MANIFEST_VERSION,
+)
+from tests.cycle_semantics_lab import write_synthetic_repository
+from tests.test_cycle_semantics_optional_child_worker_capture import (
+    FILES,
+)
+from tests.test_original_worker_full_receipt_optin import (
+    _persisted,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _repo(tmp_path, files=None):
+    return write_synthetic_repository(
+        tmp_path / "repo",
+        FILES if files is None else files,
+    )
+
+
+def _run(root, **kwargs):
+    errors, result = ContextorFacade.analyze_project(
+        str(root), **kwargs
+    )
+    assert isinstance(errors, list)
+    assert result is not None
+    return result
+
+
+def test_optional_full_preview_original_worker_manifest(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    original = facade_module.index_repository
+    selections = []
+
+    def tracked(*args, **kwargs):
+        selections.append(
+            kwargs.get("source_capture_module_ids")
+        )
+        return original(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module, "index_repository", tracked
+    )
+
+    result = _run(
+        root,
+        cycle_source_preparation_preview=True,
+        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
+    )
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert preview.reason is None
+    assert preview.source_selection == "OPTIONAL_NAMED_CHILDREN"
+    assert preview.manifest is not None
+    assert preview.manifest.version == OPTIONAL_MANIFEST_VERSION
+    assert preview.manifest.source_selection == (
+        "OPTIONAL_NAMED_CHILDREN"
+    )
+    assert "pkg.child" in preview.source_modules
+    assert selections == [
+        None,
+        frozenset(preview.source_modules),
+    ]
+
+    state, metadata = _persisted(root)
+
+    assert metadata.revision >= 1
+    assert "pkg.child" not in (
+        state.dependency_graph.hard_edges["pkg.a"]
+    )
+    assert state.cycle_source_publication is None
+    assert state.cycle_partial_source_publication is None
+    assert not hasattr(
+        state, "cycle_source_preparation_preview"
+    )
+
+
+@pytest.mark.parametrize(
+    "value",
+    [None, 0, True, "INVALID", []],
+)
+def test_invalid_source_selection_precedes_index(
+    tmp_path, isolated_dirs, monkeypatch, value,
+):
+    root = _repo(tmp_path)
+
+    def forbidden(*args, **kwargs):
+        raise AssertionError("index must not start")
+
+    monkeypatch.setattr(
+        facade_module, "index_repository", forbidden
+    )
+
+    with pytest.raises(
+        ValueError, match="cycle_source_selection"
+    ):
+        ContextorFacade.analyze_project(
+            str(root),
+            cycle_source_preparation_preview=True,
+            cycle_source_selection=value,
+        )
+
+
+def test_optional_mode_requires_preview(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+
+    def forbidden(*args, **kwargs):
+        raise AssertionError("index must not start")
+
+    monkeypatch.setattr(
+        facade_module, "index_repository", forbidden
+    )
+
+    with pytest.raises(
+        ValueError, match="requires.*preview"
+    ):
+        ContextorFacade.analyze_project(
+            str(root),
+            cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
+        )
+
+
+@pytest.mark.parametrize(
+    "publication_arg",
+    [
+        "cycle_source_publication_opt_in",
+        "cycle_partial_source_publication_opt_in",
+    ],
+)
+def test_optional_publication_rejected_before_index(
+    tmp_path, isolated_dirs, monkeypatch, publication_arg,
+):
+    root = _repo(tmp_path)
+
+    def forbidden(*args, **kwargs):
+        raise AssertionError("index must not start")
+
+    monkeypatch.setattr(
+        facade_module, "index_repository", forbidden
+    )
+
+    with pytest.raises(
+        ValueError, match="publication unsupported"
+    ):
+        ContextorFacade.analyze_project(
+            str(root),
+            cycle_source_preparation_preview=True,
+            cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
+            **{publication_arg: True},
+        )
+
+
+def test_optional_no_cycles_skips_second_index(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    files = {
+        **FILES,
+        "pkg/b.py": "value = 1\n",
+    }
+    root = _repo(tmp_path, files)
+    original = facade_module.index_repository
+    selections = []
+
+    def tracked(*args, **kwargs):
+        selections.append(
+            kwargs.get("source_capture_module_ids")
+        )
+        return original(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module, "index_repository", tracked
+    )
+
+    result = _run(
+        root,
+        cycle_source_preparation_preview=True,
+        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
+    )
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == "UNAVAILABLE"
+    assert preview.reason == "PLAN_NO_CYCLIC_COMPONENTS"
+    assert preview.manifest is None
+    assert preview.source_selection == "OPTIONAL_NAMED_CHILDREN"
+    assert selections == [None]
+
+
+def test_optional_source_drift_fails_closed(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    original = facade_module.index_repository
+
+    def drifted(*args, **kwargs):
+        if kwargs.get("source_capture_module_ids") is not None:
+            (root / "pkg" / "child.py").write_bytes(
+                b"changed = True\n"
+            )
+        return original(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module, "index_repository", drifted
+    )
+
+    result = _run(
+        root,
+        cycle_source_preparation_preview=True,
+        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
+    )
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == "UNAVAILABLE"
+    assert preview.reason == "VERIFY_REINDEX_SOURCE_CHANGED"
+    assert preview.manifest is None
+    assert preview.source_selection == "OPTIONAL_NAMED_CHILDREN"
+
+    state, _ = _persisted(root)
+    assert state.cycle_source_publication is None
+    assert state.cycle_partial_source_publication is None
+
+
+def test_legacy_default_source_selection_unchanged(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+
+    result = _run(
+        root,
+        cycle_source_preparation_preview=True,
+    )
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.source_selection == "HARD_ONLY"
+    assert (
+        preview.manifest is None
+        or preview.manifest.source_selection == "HARD_ONLY"
+    )
+
+    state, _ = _persisted(root)
+    assert state.cycle_source_publication is None
+    assert state.cycle_partial_source_publication is None
```

## FINAL_VERDICT

TEST_FAILURE

# F2L D1O2c2 - selected owner names and RAM freshness envelope

STATUS: PASS

FILES_CHANGED:
- contextor/core/lineage_query/live_query.py
- tests/analysis/test_lineage_live_query.py
- walkthrough.md (this report; its own diff intentionally excluded)

OWNER_NAMES_INTEGRATION_PROOF:
Resolved query_live_symbol_lineage results carry exactly build_selected_lineage_owner_names(backend, selected). The selected STATE and CALLEE origins yield 17/2 -> pkg.mod and A18/1 -> pkg.mod::other.

SAME_REVISION_PROOF:
The resolved fixture has canonical revision 11. Its selected-facts metadata revision equals state_freshness.canonical_revision, and the freshness provenance is live.

RAM_FRESHNESS_PROOF:
The envelope reads only supplied state and backend metadata. It always reports workspace_sync: unverified, with only module, lineage, and lineage-query-index family state.

MODULE_STALE_PROOF:
module_current_truth reports retained last-known-good facts for a stale target module; the envelope returns canonical_state: stale with its canonical parse warning.

RESYNC_PROOF:
state.resync_required = True yields canonical_state: stale and Canonical state requires resynchronization.

UNRESOLVED_FRESHNESS_PROOF:
A not-found result and an unavailable result each preserve an empty owner map and return revision-bound freshness. The unavailable case exposes stale lineage_query_index.

NO_FILESYSTEM_PROOF:
The helper imports and calls neither FileState/generation helpers, registry, filesystem readers, source/AST work, nor MCP code. Inputs are the supplied RAM state and RepositoryStateLineageBackend.metadata().

CORRUPTION_PROPAGATION_PROOF:
The conflicting selected semantic origin test now asserts that query_live_symbol_lineage itself propagates the canonical identity inconsistency; it is not remapped to unavailable or not-found.

TESTS_RUN:
- .\.venv\Scripts\python.exe -m pytest -q tests\analysis\test_lineage_live_query.py tests\analysis\test_lineage_query_service.py tests\analysis\test_lineage_query_backend.py tests\mcp\test_lineage_response.py - 145 passed in 4.08s
- .\.venv\Scripts\python.exe -m py_compile contextor\core\lineage_query\live_query.py tests\analysis\test_lineage_live_query.py - passed
- git diff --check -- contextor/core/lineage_query/live_query.py tests/analysis/test_lineage_live_query.py - passed

RUNTIME_RESTART_REQUIRED: STILL_YES_FROM_D1O1_BUT_DO_NOT_RESTART_YET.

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/core/lineage_query/live_query.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/analysis/test_lineage_live_query.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/lineage_query/live_query.py b/contextor/core/lineage_query/live_query.py
index dd952d9..b34a5c1 100644
--- a/contextor/core/lineage_query/live_query.py
+++ b/contextor/core/lineage_query/live_query.py
@@ -1,8 +1,11 @@
 from __future__ import annotations

-from dataclasses import dataclass
+from dataclasses import dataclass, field
 from collections.abc import Mapping

+from contextor.core.analysis.state_manager import (
+    module_current_truth,
+)
 from contextor.core.lineage_query.backend import (
     RepositoryStateLineageBackend,
 )
@@ -43,6 +46,8 @@ class LiveSymbolLineageQueryResult:
     resolution: LineageTargetResolution
     selected: SelectedSymbolLineageFacts | None = None
     unavailable_reason: str | None = None
+    owner_names: dict[str, str] = field(default_factory=dict)
+    state_freshness: dict[str, object] = field(default_factory=dict)


 def _selected_lineage_flow_matches(
@@ -217,6 +222,62 @@ def build_selected_lineage_owner_names(
     return dict(sorted(owner_names.items()))


+def build_live_lineage_state_freshness(
+    state: object,
+    backend: RepositoryStateLineageBackend,
+    *,
+    target_module: str | None = None,
+) -> dict[str, object]:
+    if not isinstance(backend, RepositoryStateLineageBackend):
+        raise TypeError("backend must be RepositoryStateLineageBackend.")
+    if (
+        target_module is not None
+        and (not isinstance(target_module, str) or not target_module)
+    ):
+        raise ValueError(
+            "target_module must be a non-empty string or None."
+        )
+
+    metadata = backend.metadata()
+    if target_module is None:
+        module_truth = {"state": "fresh"}
+    else:
+        module_truth = module_current_truth(state, target_module)
+    module_state = str(module_truth.get("state", "fresh"))
+    resync_required = bool(getattr(state, "resync_required", False))
+    canonical_state = (
+        "stale"
+        if resync_required or module_state == "stale"
+        else "fresh"
+    )
+
+    advisory_warning = None
+    if resync_required:
+        advisory_warning = "Canonical state requires resynchronization."
+    elif module_state == "stale":
+        advisory_warning = (
+            module_truth.get("reason")
+            or "Target module canonical facts are last-known-good."
+        )
+
+    return {
+        "canonical_state": canonical_state,
+        "workspace_sync": "unverified",
+        "canonical_revision": metadata.revision,
+        "provenance": metadata.provenance,
+        "families": {
+            "module": module_state,
+            "lineage": metadata.family_state,
+            "lineage_query_index": metadata.query_index_state,
+        },
+        "lineage_semantic_version": metadata.semantic_version,
+        "semantic_anchor_bindings_complete": (
+            metadata.semantic_anchor_bindings_complete
+        ),
+        "advisory_warning": advisory_warning,
+    }
+
+
 def _require_exact_identity_capability(
     backend: RepositoryStateLineageBackend,
 ) -> None:
@@ -433,6 +494,12 @@ def query_live_symbol_lineage(
                 query=query.strip(),
             ),
             unavailable_reason=str(exc),
+            state_freshness=(
+                build_live_lineage_state_freshness(
+                    state,
+                    backend,
+                )
+            ),
         )

     service = LineageQueryService(
@@ -449,6 +516,12 @@ def query_live_symbol_lineage(
     ):
         return LiveSymbolLineageQueryResult(
             resolution=resolution,
+            state_freshness=(
+                build_live_lineage_state_freshness(
+                    state,
+                    backend,
+                )
+            ),
         )

     facts = service.symbol_lineage_facts(
@@ -460,8 +533,19 @@ def query_live_symbol_lineage(
             canonical_sections,
         )
     )
+    owner_names = build_selected_lineage_owner_names(
+        backend,
+        selected,
+    )
+    state_freshness = build_live_lineage_state_freshness(
+        state,
+        backend,
+        target_module=resolution.target.module_name,
+    )

     return LiveSymbolLineageQueryResult(
         resolution=resolution,
         selected=selected,
+        owner_names=owner_names,
+        state_freshness=state_freshness,
     )
diff --git a/tests/analysis/test_lineage_live_query.py b/tests/analysis/test_lineage_live_query.py
index f02a65b..5c75f4f 100644
--- a/tests/analysis/test_lineage_live_query.py
+++ b/tests/analysis/test_lineage_live_query.py
@@ -30,6 +30,7 @@ from contextor.core.lineage_query.index import (
 from contextor.core.lineage_query.live_query import (
     LiveSymbolLineageQueryResult,
     build_selected_lineage_owner_names,
+    build_live_lineage_state_freshness,
     build_live_lineage_target_catalog,
     query_live_symbol_lineage,
 )
@@ -913,14 +914,142 @@ def test_selected_owner_names_reject_conflicting_canonical_name_for_same_owner()
     state.lineage_owner_source_index = owner_source_index
     state.lineage_source_owner_index = source_owner_index
     state.lineage_semantic_anchor_bindings_complete = anchor_complete
+    with pytest.raises(
+        ValueError,
+        match="Canonical semantic owner identity is inconsistent.",
+    ):
+        query_live_symbol_lineage(
+            state,
+            "A17/2",
+            ("calls_interfaces",),
+        )
+
+
+def test_live_lineage_state_freshness_is_ram_only_and_revision_bound():
+    state, backend = _fixture()
+
+    result = build_live_lineage_state_freshness(
+        state,
+        backend,
+        target_module="pkg.mod",
+    )
+
+    assert result == {
+        "canonical_state": "fresh",
+        "workspace_sync": "unverified",
+        "canonical_revision": 7,
+        "provenance": "live",
+        "families": {
+            "module": "fresh",
+            "lineage": "fresh",
+            "lineage_query_index": "fresh",
+        },
+        "lineage_semantic_version": "1",
+        "semantic_anchor_bindings_complete": True,
+        "advisory_warning": None,
+    }
+
+
+def test_live_lineage_state_freshness_marks_last_known_good_target_module_stale():
+    state, backend = _fixture()
+    state.module_parse_freshness = {
+        "pkg.mod": {"state": "stale", "error": "syntax failure"},
+    }
+
+    result = build_live_lineage_state_freshness(
+        state,
+        backend,
+        target_module="pkg.mod",
+    )
+
+    assert result["canonical_state"] == "stale"
+    assert result["workspace_sync"] == "unverified"
+    assert result["families"]["module"] == "stale"
+    assert result["advisory_warning"] == (
+        "Current source could not be parsed; canonical facts are "
+        "last-known-good."
+    )
+
+
+def test_live_lineage_state_freshness_marks_resync_required():
+    state, backend = _fixture()
+    state.resync_required = True
+
+    result = build_live_lineage_state_freshness(
+        state,
+        backend,
+        target_module="pkg.mod",
+    )
+
+    assert result["canonical_state"] == "stale"
+    assert result["advisory_warning"] == (
+        "Canonical state requires resynchronization."
+    )
+
+
+def test_live_symbol_lineage_result_carries_selected_owner_names_and_same_revision_freshness():
+    state, _backend, _selected = _owner_name_projection_fixture()
+
     result = query_live_symbol_lineage(
-        state, "A17/2", ("calls_interfaces",)
+        state,
+        "A17/2",
+        ("calls_interfaces", "state"),
     )
+
+    assert result.resolution.status == "resolved"
     assert result.selected is not None
-    backend = RepositoryStateLineageBackend(state)
+    assert result.owner_names == {
+        "17/2": "pkg.mod",
+        "A18/1": "pkg.mod::other",
+    }
+    assert result.state_freshness["canonical_revision"] == 11
+    assert result.state_freshness["provenance"] == "live"
+    assert result.state_freshness["families"]["lineage"] == "fresh"
+    assert (
+        result.selected.facts.metadata.revision
+        == result.state_freshness["canonical_revision"]
+    )
+
+
+def test_unresolved_and_unavailable_live_symbol_results_have_no_owner_names_but_keep_freshness():
+    state, _backend = _fixture()
+
+    missing = query_live_symbol_lineage(
+        state,
+        "A404/1",
+        ("interface",),
+    )
+
+    assert missing.resolution.status == "not_found"
+    assert missing.selected is None
+    assert missing.owner_names == {}
+    assert missing.state_freshness["canonical_revision"] == 7
+
+    state.lineage_query_index_state = "stale"
+    unavailable = query_live_symbol_lineage(
+        state,
+        "A17/2",
+        ("interface",),
+    )
+
+    assert unavailable.resolution.status == "unavailable"
+    assert unavailable.selected is None
+    assert unavailable.owner_names == {}
+    assert (
+        unavailable.state_freshness["families"]["lineage_query_index"]
+        == "stale"
+    )
+
+
+def test_live_lineage_state_freshness_validates_target_module():
+    state, backend = _fixture()

     with pytest.raises(
         ValueError,
-        match="Canonical semantic owner identity is inconsistent.",
+        match="target_module must be a non-empty string or None.",
     ):
-        build_selected_lineage_owner_names(backend, result.selected)
+        build_live_lineage_state_freshness(
+            state,
+            backend,
+            target_module="",
+        )
```

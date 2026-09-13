# F2L D1I Repair Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/service.py`
- `contextor/core/lineage_query/__init__.py`
- `tests/analysis/test_lineage_query_service.py`

`walkthrough.md` is deliberately excluded from ACTUAL_DIFF.

## AMBIGUOUS_ROOT_FAIL_CLOSED_PROOF

A lexical scope is available only for exactly one exact semantic-anchor-to-lexical-anchor root. Multiple roots remain in `roots` for diagnostics but clear flows and nested scopes; `scope_available=False`, `root_ambiguous=True`, and `complete=False`. No ordering, span, or AST-path heuristic selects a root. Zero roots remain fail-closed and a unique root remains unchanged.

## TESTS_RUN

- `./.venv/Scripts/python.exe -m py_compile contextor/core/lineage_query/service.py contextor/core/lineage_query/__init__.py`: PASS.
- `./.venv/Scripts/python.exe -m pytest -q tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py`: PASS — 40 passed in 2.03s.
- `git diff --check` for task files: PASS (only CRLF conversion warnings).

## ACTUAL_DIFF

The following is the full current diff for each task file, covering the entire D1I implementation plus this repair.

### contextor/core/lineage_query/service.py

```diff
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
index 922b66c..a340b81 100644
--- a/contextor/core/lineage_query/service.py
+++ b/contextor/core/lineage_query/service.py
@@ -92,7 +92,11 @@ class LexicalScopeFacts:

     @property
     def scope_available(self) -> bool:
-        return bool(self.roots)
+        return len(self.roots) == 1
+
+    @property
+    def root_ambiguous(self) -> bool:
+        return len(self.roots) > 1

     @property
     def complete(self) -> bool:
@@ -384,6 +388,10 @@ class LineageQueryService:
         flows.sort(key=_flow_match_key)
         nested_scopes.sort(key=_local_anchor_match_key)

+        if len(roots) != 1:
+            flows.clear()
+            nested_scopes.clear()
+
         return LexicalScopeFacts(
             target=target,
             metadata=metadata,
```

### contextor/core/lineage_query/__init__.py

```diff

```

### tests/analysis/test_lineage_query_service.py

```diff
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
index 99c7bfd..1a9cba3 100644
--- a/tests/analysis/test_lineage_query_service.py
+++ b/tests/analysis/test_lineage_query_service.py
@@ -1,3 +1,4 @@
+from dataclasses import replace
 from types import SimpleNamespace

 import pytest
@@ -753,6 +754,7 @@ def test_lexical_scope_facts_return_only_exact_root_owned_flows():
     assert result.target is target
     assert result.metadata.revision == 31
     assert result.scope_available is True
+    assert result.root_ambiguous is False
     assert result.materialization_complete is True
     assert result.complete is True

@@ -991,3 +993,88 @@ def test_lexical_scope_facts_do_not_treat_plain_binding_as_scope():
     assert result.nested_scopes == ()
     assert result.scope_available is False
     assert result.complete is False
+def test_lexical_scope_facts_fail_closed_for_multiple_exact_roots():
+    service, backend, target = _lexical_scope_service()
+    source = backend.get_source("pkg/target.py")
+    assert source is not None
+
+    duplicate_ref = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        "d" * 64,
+        "outer-redefined",
+    )
+    duplicate_anchor = MaterializedAnchorFact(
+        "outer-redefined",
+        duplicate_ref,
+        "function",
+        SourceSpan(20, 0, 22, 1),
+        owner_local_id="module",
+    )
+    duplicate_flow = MaterializedFlowFact(
+        "z_redefined_return",
+        duplicate_ref,
+        MaterializedOccurrenceRef(
+            "pkg/target.py",
+            "d" * 64,
+            "redefined-result",
+        ),
+        LineageRelation.RETURNS,
+        SourceSpan(21, 1, 21, 10),
+        ResolutionKind.LEXICAL_EXACT,
+        LineageConfidence.CONFIRMED,
+        owner_local_id="outer-redefined",
+    )
+    duplicate_binding = SemanticAnchorBinding(
+        target.artifact_id,
+        target.qualified_name,
+        duplicate_ref,
+    )
+
+    replacement = replace(
+        source,
+        manifest=replace(
+            source.manifest,
+            anchor_count=source.manifest.anchor_count + 1,
+            flow_count=source.manifest.flow_count + 1,
+        ),
+        anchors=tuple(
+            sorted(
+                (
+                    *source.anchors,
+                    duplicate_anchor,
+                )
+            )
+        ),
+        flows=tuple(
+            sorted(
+                (
+                    *source.flows,
+                    duplicate_flow,
+                )
+            )
+        ),
+        semantic_anchors=tuple(
+            sorted(
+                (
+                    *source.semantic_anchors,
+                    duplicate_binding,
+                )
+            )
+        ),
+    )
+    backend._sources["pkg/target.py"] = replacement
+
+    result = service.lexical_scope_facts(target)
+
+    assert tuple(
+        item.anchor.local_id
+        for item in result.roots
+    ) == (
+        "outer",
+        "outer-redefined",
+    )
+    assert result.scope_available is False
+    assert result.root_ambiguous is True
+    assert result.complete is False
+    assert result.flows == ()
+    assert result.nested_scopes == ()
```

# P0 L3B1 — Current extracted status fail-closed

## STATUS

SUCCESS

Per-source reuse wymaga teraz również, aby bieżący extracted slice miał status `FRESH`. Bieżące `RESOURCE_LIMIT` przy tym samym fingerprint nie może reuse'ować poprzedniego FRESH slice.

## CHANGE

Do istniejącego `previous_source_reusable` dodano wyłącznie warunek:

```python
extracted.status is LineageFamilyStatus.FRESH
```

Nie zmieniono pozostałej semantyki L3B ani lifecycle.

## FOCUSED_REGRESSION

Dodano regresję dla FRESH previous slice i current extracted `RESOURCE_LIMIT` przy tym samym source key oraz fingerprint. Potwierdza nową materializację, manifest `RESOURCE_LIMIT`, reason `node_limit` oraz family state `resource_limit`.

## VALIDATION

` .\\.venv\\Scripts\\python.exe -m pytest -q tests\\test_full_analysis_lineage_materialization.py tests\\analysis\\test_lineage_materialization.py `

`46 passed in 4.74s`

`git diff --check -- contextor/core/api/facade.py tests/test_full_analysis_lineage_materialization.py` passed.

## CONTEXTOR_POST_EDIT_FLOW_AUDIT

Contextor potwierdził niezmieniony canonical direct flow `ContextorFacade.analyze_project -> _materialize_full_analysis_lineage` (linia 693). Zmieniony helper został poprawnie rozpoznany jako kompletna implementacja w `facade.py` (linie 264–465); nie pojawił się nowy lifecycle ani nowy call path.

## FILES_CHANGED

- `contextor/core/api/facade.py`
- `tests/test_full_analysis_lineage_materialization.py`

## FULL_DIFFS

```diff
warning: in the working copy of 'contextor/core/api/facade.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_full_analysis_lineage_materialization.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/api/facade.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_full_analysis_lineage_materialization.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 89006bd..07dbfba 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -377,7 +377,8 @@ def _materialize_full_analysis_lineage(
         materialized = None
         previous_materialized = previous_lineage_by_source.get(source_key)
         previous_source_reusable = (
-            isinstance(previous_materialized, MaterializedLineageSourceFacts)
+            extracted.status is LineageFamilyStatus.FRESH
+            and isinstance(previous_materialized, MaterializedLineageSourceFacts)
             and previous_materialized.manifest.source_key == source_key
             and previous_materialized.manifest.source_fingerprint == extracted.source_fingerprint
             and previous_materialized.manifest.semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
diff --git a/tests/test_full_analysis_lineage_materialization.py b/tests/test_full_analysis_lineage_materialization.py
index e62492a..f003d3c 100644
--- a/tests/test_full_analysis_lineage_materialization.py
+++ b/tests/test_full_analysis_lineage_materialization.py
@@ -490,3 +490,42 @@ def test_full_analysis_falls_back_to_materialization_for_missing_origin(monkeypa
     assert second_mapping["pkg.py"] is not legacy_previous
     assert second_mapping["pkg.py"].flows[0].target == SemanticEndpoint("A1/1")
     assert second_mapping["pkg.py"].semantic_endpoint_origins
+
+
+def test_full_analysis_does_not_reuse_previous_fresh_slice_when_current_extraction_is_resource_limited():
+    fresh_facts = _owned_fresh_slice()
+    fresh_index = _index(facts={"pkg.py": fresh_facts})
+    artifacts = {"pkg": {"own_symbols": ["target"]}}
+    registry = _ReadOnlyRegistry(
+        {"pkg": "1/1"},
+        {"pkg::target": "A1/1"},
+    )
+    first_mapping, _, _ = _materialize_full_analysis_lineage(
+        fresh_index,
+        registry,
+        fresh_index.modules,
+        artifacts,
+    )
+    previous = first_mapping["pkg.py"]
+
+    limited_facts = replace(
+        fresh_facts,
+        status=LineageFamilyStatus.RESOURCE_LIMIT,
+        resource_limit_reason="node_limit",
+    )
+    limited_index = _index(facts={"pkg.py": limited_facts})
+
+    second_mapping, family_state, version = _materialize_full_analysis_lineage(
+        limited_index,
+        registry,
+        limited_index.modules,
+        artifacts,
+        previous_state=_previous_lineage_state(first_mapping),
+    )
+
+    current = second_mapping["pkg.py"]
+    assert current is not previous
+    assert current.manifest.status is LineageFamilyStatus.RESOURCE_LIMIT
+    assert current.manifest.resource_limit_reason == "node_limit"
+    assert family_state == "resource_limit"
+    assert version == LINEAGE_FACTS_SEMANTIC_VERSION
 M contextor/core/api/facade.py
 M tests/test_full_analysis_lineage_materialization.py

```


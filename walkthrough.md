# F2L D1L3b2 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/analysis/incremental/engine.py`
- `tests/test_lineage_state_lifecycle.py`

## RETAINED_MATERIALIZED_REBUILD_PROOF

Identity-sync rebuilds retained descriptors with the materialized builder.

## CHANGED_SOURCE_EXCLUSION_PROOF

The retained map excludes `source_path`; changed descriptors come from extracted facts.

## CURRENT_GENERATION_DESCRIPTOR_PROOF

The focused generation-change test passed.

## OWNER_INTRODUCTION_PARITY_PROOF

The prior parity failure now passes.

## OWNER_DELETION_PARITY_PROOF

The focused deletion test passed.

## ORDINARY_PATH_REGRESSION_PROOF

The focused ordinary incremental test passed.

## TESTS_RUN

```text
Focused: 4 passed in 0.95s
Full: 69 passed in 6.56s
py_compile: PASS
git diff --check: PASS
```

## ACTUAL_DIFF

```diff
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index 49fba5a..bbeef57 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -199,6 +199,7 @@ class IncrementalAnalysisEngine:
             LineageOriginUnavailableError,
             LineageResolutionContext,
             build_extracted_callable_interface_descriptors,
+            build_materialized_callable_interface_descriptors,
             materialize_lineage_source_facts,
             reresolve_materialized_lineage_source_facts,
         )
@@ -256,7 +257,32 @@ class IncrementalAnalysisEngine:
                 )
 
             interface_descriptors = {}
-            if not rematerialize_all:
+            if rematerialize_all:
+                retained_sources = {
+                    key: lineage_by_source[key]
+                    for key in sorted(lineage_by_source)
+                    if key != source_path
+                }
+                interface_descriptors.update(
+                    build_materialized_callable_interface_descriptors(
+                        retained_sources,
+                        active_artifact_ids,
+                    )
+                )
+                if not delete:
+                    changed_descriptors = (
+                        build_extracted_callable_interface_descriptors(
+                            {source_path: extracted_lineage_facts},
+                            active_artifact_ids,
+                        )
+                    )
+                    for owner_id, descriptor in changed_descriptors.items():
+                        existing = interface_descriptors.get(owner_id)
+                        if existing is None:
+                            interface_descriptors[owner_id] = descriptor
+                        elif existing != descriptor:
+                            interface_descriptors.pop(owner_id, None)
+            else:
                 active_artifact_owner_ids = frozenset(active_artifact_ids.values())
                 ambiguous_descriptor_owner_ids: set[str] = set()
```


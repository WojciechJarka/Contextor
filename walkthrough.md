# F2L D1L4b Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/domain/lineage_facts.py`
- `contextor/core/analysis/lineage_materialization.py`
- `contextor/core/live_state/store.py`
- `tests/analysis/test_lineage_materialization.py`

## INITIAL_CAPABILITY_PROOF

New materialization sets the capability true.

## CAPABILITY_DEPENDENCY_PROOF

Manifest validation requires semantic anchor and anchor ownership capabilities.

## LEGACY_FALSE_PRESERVES_PAYLOAD_PROOF

Snapshot normalization reads missing fields as false.

## RERESOLUTION_UPGRADE_PROOF

Re-resolution sets the capability from canonical anchor capabilities.

## NO_VERSION_BUMP_PROOF

No semantic or live-state schema version was changed.

## TESTS_RUN

```text
72 passed in 6.62s
py_compile: PASS
git diff --check: PASS
```

## ACTUAL_DIFF

```diff
diff --git a/contextor/core/analysis/lineage_materialization.py b/contextor/core/analysis/lineage_materialization.py
index a891176..0232ba2 100644
--- a/contextor/core/analysis/lineage_materialization.py
+++ b/contextor/core/analysis/lineage_materialization.py
@@ -4,7 +4,7 @@ from __future__ import annotations
 
 import hashlib
 
-from dataclasses import dataclass
+from dataclasses import dataclass, replace
 from types import MappingProxyType
 from typing import Mapping
 
@@ -487,6 +487,7 @@ def materialize_lineage_source_facts(
         semantic_anchor_bindings_materialized=True,
         anchor_ownership_materialized=True,
         flow_ownership_materialized=flow_ownership_materialized,
+        interface_descriptors_materialized=True,
     )
     return MaterializedLineageSourceFacts(
         manifest,
@@ -635,8 +636,15 @@ def reresolve_materialized_lineage_source_facts(
         )
     )
     _seed_defining_interface_descriptors(descriptors, semantic_anchors, resolution)
-    return MaterializedLineageSourceFacts(
+    manifest = replace(
         materialized.manifest,
+        interface_descriptors_materialized=(
+            materialized.manifest.semantic_anchor_bindings_materialized
+            and materialized.manifest.anchor_ownership_materialized
+        ),
+    )
+    return MaterializedLineageSourceFacts(
+        manifest,
         materialized.anchors,
         flows,
         surfaces,
diff --git a/contextor/core/domain/lineage_facts.py b/contextor/core/domain/lineage_facts.py
index 40d66cb..0b203ef 100644
--- a/contextor/core/domain/lineage_facts.py
+++ b/contextor/core/domain/lineage_facts.py
@@ -437,6 +437,7 @@ class SourceLineageManifest:
     semantic_anchor_bindings_materialized: bool = False
     anchor_ownership_materialized: bool = False
     flow_ownership_materialized: bool = False
+    interface_descriptors_materialized: bool = False
 
     def __post_init__(self) -> None:
         _require_token(self.source_key, "source_key")
@@ -452,6 +453,15 @@ class SourceLineageManifest:
             raise TypeError("anchor_ownership_materialized must be boolean.")
         if not isinstance(self.flow_ownership_materialized, bool):
             raise TypeError("flow_ownership_materialized must be boolean.")
+        if not isinstance(self.interface_descriptors_materialized, bool):
+            raise TypeError("interface_descriptors_materialized must be boolean.")
+        if self.interface_descriptors_materialized and (
+            not self.semantic_anchor_bindings_materialized
+            or not self.anchor_ownership_materialized
+        ):
+            raise ValueError(
+                "Materialized interface descriptors require semantic anchor bindings and anchor ownership."
+            )
         _validate_source_status(self.status, self.resource_limit_reason)
 
 
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index b13fb03..fd3a7d6 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -164,6 +164,9 @@ def _revalidate_lineage_manifest(manifest: Any) -> SourceLineageManifest:
                 False,
             )
         ),
+        interface_descriptors_materialized=bool(
+            getattr(manifest, "interface_descriptors_materialized", False)
+        ),
     )
     if rebuilt.semantic_version != LINEAGE_FACTS_SEMANTIC_VERSION:
         raise pickle.UnpicklingError(
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
index b6d9021..c99a805 100644
--- a/tests/analysis/test_lineage_materialization.py
+++ b/tests/analysis/test_lineage_materialization.py
@@ -720,7 +720,11 @@ def test_materialized_callable_interface_builder_requires_canonical_capabilities
     )
     legacy = replace(
         materialized,
-        manifest=replace(materialized.manifest, anchor_ownership_materialized=False),
+        manifest=replace(
+            materialized.manifest,
+            anchor_ownership_materialized=False,
+            interface_descriptors_materialized=False,
+        ),
     )
     assert build_materialized_callable_interface_descriptors(
         {"pkg/mod.py": legacy}, {"pkg.mod::run": "A1/2"}
```


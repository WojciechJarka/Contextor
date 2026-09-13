# F2L D1L4b Correctness Repair Walkthrough

## STATUS

PASS

## INITIAL_TRUE_PROOF

New materialization preserves true capability.

## CURRENT_TRUE_PRESERVATION_PROOF

Generic re-resolution preserves the existing manifest.

## LEGACY_FALSE_PRESERVATION_PROOF

The new test proves generic re-resolution keeps legacy false.

## SNAPSHOT_PAYLOAD_PRESERVATION_PROOF

Store normalization remains unchanged and preserves payload.

## CAPABILITY_VALIDATION_PROOF

New validation tests cover missing anchor capabilities and non-boolean flag.

## TESTS_RUN

```text
74 passed in 8.26s
git diff --check: PASS
```

## ACTUAL_DIFF

```diff
diff --git a/contextor/core/analysis/lineage_materialization.py b/contextor/core/analysis/lineage_materialization.py
index 0232ba2..96ce8c3 100644
--- a/contextor/core/analysis/lineage_materialization.py
+++ b/contextor/core/analysis/lineage_materialization.py
@@ -4,7 +4,7 @@ from __future__ import annotations
 
 import hashlib
 
-from dataclasses import dataclass, replace
+from dataclasses import dataclass
 from types import MappingProxyType
 from typing import Mapping
 
@@ -636,15 +636,8 @@ def reresolve_materialized_lineage_source_facts(
         )
     )
     _seed_defining_interface_descriptors(descriptors, semantic_anchors, resolution)
-    manifest = replace(
-        materialized.manifest,
-        interface_descriptors_materialized=(
-            materialized.manifest.semantic_anchor_bindings_materialized
-            and materialized.manifest.anchor_ownership_materialized
-        ),
-    )
     return MaterializedLineageSourceFacts(
-        manifest,
+        materialized.manifest,
         materialized.anchors,
         flows,
         surfaces,
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
index c99a805..e1e67ba 100644
--- a/tests/analysis/test_lineage_materialization.py
+++ b/tests/analysis/test_lineage_materialization.py
@@ -770,3 +770,37 @@ def test_unrelated_resolution_descriptor_is_not_seeded_into_slice():
     )
     assert result.semantic_anchors == ()
     assert result.interface_descriptors == ()
+
+
+def test_legacy_interface_descriptor_capability_stays_false_after_generic_reresolution():
+    facts = _callable_interface_facts("def ping():\n    pass\n")
+    old, new = "A1/1", "A1/2"
+    descriptors = build_extracted_callable_interface_descriptors(
+        {"pkg/mod.py": facts}, {"pkg.mod::ping": old}
+    )
+    materialized = materialize_lineage_source_facts(
+        facts, _context(artifacts={"pkg.mod::ping": old}, descriptors=descriptors)
+    )
+    legacy = replace(
+        materialized,
+        manifest=replace(materialized.manifest, interface_descriptors_materialized=False),
+    )
+    rebound = build_materialized_callable_interface_descriptors(
+        {"pkg/mod.py": legacy}, {"pkg.mod::ping": new}
+    )
+    rerun = reresolve_materialized_lineage_source_facts(
+        legacy, _context(artifacts={"pkg.mod::ping": new}, descriptors=rebound)
+    )
+    assert rerun.manifest.interface_descriptors_materialized is False
+    assert rerun.interface_descriptors == (rebound[new],)
+
+
+def test_interface_descriptor_capability_requires_anchor_capabilities():
+    manifest = SourceLineageManifest(
+        "pkg.py", "fingerprint", LINEAGE_FACTS_SEMANTIC_VERSION,
+        LineageFamilyStatus.FRESH, 0, 0, 0,
+    )
+    with pytest.raises(ValueError, match="require semantic anchor bindings and anchor ownership"):
+        replace(manifest, interface_descriptors_materialized=True)
+    with pytest.raises(TypeError, match="interface_descriptors_materialized must be boolean"):
+        replace(manifest, interface_descriptors_materialized="yes")
```


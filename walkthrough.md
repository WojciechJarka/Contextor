# F2L D1L3b1 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/analysis/lineage_materialization.py`
- `tests/analysis/test_lineage_materialization.py`

## MATERIALIZED_ONLY_PROOF

Builder consumes only materialized slices, anchors, semantic bindings, and active artifact IDs.

## CURRENT_GENERATION_PROOF

The owner is resolved from `active_artifact_ids[binding.qualified_name]`.

## DIGEST_STABILITY_PROOF

Rebinding test proves identical digest for A1/1 and A1/2.

## CAPABILITY_FAIL_CLOSED_PROOF

A slice without anchor-ownership capability produces no descriptor.

## TESTS_RUN

```text
22 passed in 1.89s
py_compile: PASS
git diff --check: PASS
```

## ACTUAL_DIFF

```diff
diff --git a/contextor/core/analysis/lineage_materialization.py b/contextor/core/analysis/lineage_materialization.py
index d4efd5c..2b20ea0 100644
--- a/contextor/core/analysis/lineage_materialization.py
+++ b/contextor/core/analysis/lineage_materialization.py
@@ -298,6 +298,54 @@ def build_extracted_callable_interface_descriptors(
     return dict(sorted(descriptors.items()))
 
 
+def build_materialized_callable_interface_descriptors(
+    sources: Mapping[str, MaterializedLineageSourceFacts],
+    active_artifact_ids: Mapping[str, str],
+) -> dict[str, SemanticInterfaceDescriptor]:
+    if not isinstance(sources, Mapping):
+        raise TypeError("sources must be a mapping.")
+    if not isinstance(active_artifact_ids, Mapping):
+        raise TypeError("active_artifact_ids must be a mapping.")
+
+    descriptors: dict[str, SemanticInterfaceDescriptor] = {}
+    ambiguous_owner_ids: set[str] = set()
+    for source_key in sorted(sources):
+        source = sources[source_key]
+        if not isinstance(source, MaterializedLineageSourceFacts):
+            raise TypeError("lineage source value has invalid type.")
+        if source.manifest.source_key != source_key:
+            raise ValueError("lineage mapping key does not match source manifest.")
+        if (
+            source.manifest.status is not LineageFamilyStatus.FRESH
+            or not source.manifest.semantic_anchor_bindings_materialized
+            or not source.manifest.anchor_ownership_materialized
+        ):
+            continue
+        anchors = tuple(
+            ExtractedAnchorFact(anchor.local_id, anchor.kind, anchor.span, anchor.owner_local_id)
+            for anchor in source.anchors
+        )
+        anchors_by_id = {anchor.local_id: anchor for anchor in anchors}
+        for binding in source.semantic_anchors:
+            owner_id = active_artifact_ids.get(binding.qualified_name)
+            if owner_id is None or owner_id in ambiguous_owner_ids:
+                continue
+            callable_anchor = anchors_by_id.get(binding.reference.local_id)
+            if (
+                callable_anchor is None
+                or callable_anchor.kind not in _CALLABLE_INTERFACE_ANCHOR_KINDS
+            ):
+                continue
+            candidate = _callable_interface_descriptor(owner_id, callable_anchor, anchors)
+            existing = descriptors.get(owner_id)
+            if existing is None:
+                descriptors[owner_id] = candidate
+            elif existing != candidate:
+                descriptors.pop(owner_id, None)
+                ambiguous_owner_ids.add(owner_id)
+    return dict(sorted(descriptors.items()))
+
+
 def materialize_lineage_source_facts(
     extracted: ExtractedLineageSourceFacts,
     resolution: LineageResolutionContext,
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
index 4680ca0..e10be20 100644
--- a/tests/analysis/test_lineage_materialization.py
+++ b/tests/analysis/test_lineage_materialization.py
@@ -2,6 +2,7 @@ from __future__ import annotations
 
 import ast
 import builtins
+from dataclasses import replace
 
 import pytest
 
@@ -11,6 +12,7 @@ from contextor.core.analysis.lineage_extraction import (
 from contextor.core.analysis.lineage_materialization import (
     LineageResolutionContext,
     build_extracted_callable_interface_descriptors,
+    build_materialized_callable_interface_descriptors,
     materialize_lineage_source_facts,
     reresolve_materialized_lineage_source_facts,
 )
@@ -684,3 +686,42 @@ def test_callable_interface_conflicting_redefinitions_fail_closed():
     )
 
     assert result == {}
+
+
+def test_materialized_callable_interface_descriptor_rebinds_owner_generation():
+    facts = _callable_interface_facts("def run(value, *, mode):\n    return value\n")
+    old_owner, new_owner = "A1/1", "A1/2"
+    old = build_extracted_callable_interface_descriptors(
+        {"pkg/mod.py": facts}, {"pkg.mod::run": old_owner}
+    )
+    materialized = materialize_lineage_source_facts(
+        facts, _context(artifacts={"pkg.mod::run": old_owner}, descriptors=old)
+    )
+    rebound = build_materialized_callable_interface_descriptors(
+        {"pkg/mod.py": materialized}, {"pkg.mod::run": new_owner}
+    )
+    assert tuple(rebound) == (new_owner,)
+    descriptor = rebound[new_owner]
+    assert descriptor.signature_digest == old[old_owner].signature_digest
+    assert build_return_slot(new_owner) in descriptor.slots
+    assert build_keyword_binding_slot(
+        new_owner, ParameterKind.KEYWORD_ONLY, name="mode"
+    ) in descriptor.slots
+    assert all(old_owner not in slot for slot in descriptor.slots)
+
+
+def test_materialized_callable_interface_builder_requires_canonical_capabilities():
+    facts = _callable_interface_facts("def run(value):\n    return value\n")
+    descriptors = build_extracted_callable_interface_descriptors(
+        {"pkg/mod.py": facts}, {"pkg.mod::run": "A1/1"}
+    )
+    materialized = materialize_lineage_source_facts(
+        facts, _context(artifacts={"pkg.mod::run": "A1/1"}, descriptors=descriptors)
+    )
+    legacy = replace(
+        materialized,
+        manifest=replace(materialized.manifest, anchor_ownership_materialized=False),
+    )
+    assert build_materialized_callable_interface_descriptors(
+        {"pkg/mod.py": legacy}, {"pkg.mod::run": "A1/2"}
+    ) == {}
```


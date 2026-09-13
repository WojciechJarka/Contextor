# F2L D1L4a Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/analysis/lineage_materialization.py`
- `tests/analysis/test_lineage_materialization.py`

## ZERO_FLOW_INITIAL_PERSISTENCE_PROOF

Defining zero-flow callable retains its own descriptor.

## ZERO_FLOW_RERESOLUTION_PROOF

Rebound zero-flow callable retains its descriptor after re-resolution.

## NO_FOREIGN_SEED_PROOF

Unrelated resolution descriptor is not seeded.

## EXISTING_PARITY_PROOF

Full requested suite passed.

## TESTS_RUN

```text
72 passed in 7.05s
py_compile: PASS
git diff --check: PASS
```

## ACTUAL_DIFF

```diff
diff --git a/contextor/core/analysis/lineage_materialization.py b/contextor/core/analysis/lineage_materialization.py
index 2b20ea0..a891176 100644
--- a/contextor/core/analysis/lineage_materialization.py
+++ b/contextor/core/analysis/lineage_materialization.py
@@ -346,6 +346,17 @@ def build_materialized_callable_interface_descriptors(
     return dict(sorted(descriptors.items()))
 
 
+def _seed_defining_interface_descriptors(
+    descriptors: dict[str, SemanticInterfaceDescriptor],
+    semantic_anchors: tuple[SemanticAnchorBinding, ...],
+    resolution: LineageResolutionContext,
+) -> None:
+    for binding in semantic_anchors:
+        descriptor = resolution.interface_descriptors.get(binding.owner_id)
+        if descriptor is not None:
+            descriptors[binding.owner_id] = descriptor
+
+
 def materialize_lineage_source_facts(
     extracted: ExtractedLineageSourceFacts,
     resolution: LineageResolutionContext,
@@ -411,6 +422,7 @@ def materialize_lineage_source_facts(
         resolution,
         occurrence,
     )
+    _seed_defining_interface_descriptors(descriptors, semantic_anchors, resolution)
     flows = tuple(sorted(
         MaterializedFlowFact(
             flow.local_id,
@@ -622,6 +634,7 @@ def reresolve_materialized_lineage_source_facts(
             is not None
         )
     )
+    _seed_defining_interface_descriptors(descriptors, semantic_anchors, resolution)
     return MaterializedLineageSourceFacts(
         materialized.manifest,
         materialized.anchors,
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
index e10be20..b6d9021 100644
--- a/tests/analysis/test_lineage_materialization.py
+++ b/tests/analysis/test_lineage_materialization.py
@@ -725,3 +725,44 @@ def test_materialized_callable_interface_builder_requires_canonical_capabilities
     assert build_materialized_callable_interface_descriptors(
         {"pkg/mod.py": legacy}, {"pkg.mod::run": "A1/2"}
     ) == {}
+
+
+def test_defining_zero_flow_callable_persists_own_interface_descriptor():
+    facts = _callable_interface_facts("def ping():\n    pass\n")
+    owner = "A1/1"
+    descriptors = build_extracted_callable_interface_descriptors(
+        {"pkg/mod.py": facts}, {"pkg.mod::ping": owner}
+    )
+    result = materialize_lineage_source_facts(
+        facts, _context(artifacts={"pkg.mod::ping": owner}, descriptors=descriptors)
+    )
+    assert result.interface_descriptors == (descriptors[owner],)
+    assert descriptors[owner].slots == (build_return_slot(owner),)
+
+
+def test_zero_flow_callable_descriptor_rebind_survives_reresolution():
+    facts = _callable_interface_facts("def ping():\n    pass\n")
+    old, new = "A1/1", "A1/2"
+    descriptors = build_extracted_callable_interface_descriptors(
+        {"pkg/mod.py": facts}, {"pkg.mod::ping": old}
+    )
+    initial = materialize_lineage_source_facts(
+        facts, _context(artifacts={"pkg.mod::ping": old}, descriptors=descriptors)
+    )
+    rebound = build_materialized_callable_interface_descriptors(
+        {"pkg/mod.py": initial}, {"pkg.mod::ping": new}
+    )
+    rerun = reresolve_materialized_lineage_source_facts(
+        initial, _context(artifacts={"pkg.mod::ping": new}, descriptors=rebound)
+    )
+    assert rerun.interface_descriptors == (rebound[new],)
+
+
+def test_unrelated_resolution_descriptor_is_not_seeded_into_slice():
+    foreign = SemanticInterfaceDescriptor("A9/1", (build_return_slot("A9/1"),), "x")
+    result = materialize_lineage_source_facts(
+        _callable_interface_facts("value = 1\n"),
+        _context(artifacts={"other.mod::foreign": "A9/1"}, descriptors={"A9/1": foreign}),
+    )
+    assert result.semantic_anchors == ()
+    assert result.interface_descriptors == ()
```


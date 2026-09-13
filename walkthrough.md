# F2L D1M1 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/service.py`
- `contextor/core/lineage_query/__init__.py`
- `tests/analysis/test_lineage_query_service.py`

## EXACT_DEFINING_SLICE_PROOF

`target_interface_facts()` uses `source_keys_for_owner()` and accepts a candidate slice only where a semantic anchor matches both target `artifact_id` and `qualified_name`.

## COPIED_DESCRIPTOR_IGNORED_PROOF

The test fixture indexes a consumer through a semantic endpoint and gives it a copied provider descriptor. Because it lacks the exact defining binding, its descriptor is excluded.

## LEGACY_CAPABILITY_FAIL_CLOSED_PROOF

Existing descriptor payload remains observable with `interface_descriptors_materialized=False`, but materialization and result completeness are false.

## AUTHORITATIVE_ABSENCE_PROOF

A fresh capable exact definition without a descriptor returns no descriptor while remaining complete.

## DUPLICATE_DEFINITION_FAIL_CLOSED_PROOF

Two exact defining bindings retain both diagnostic matches while producing ambiguity, no descriptor, and incomplete state.

## NO_REPO_SCAN_PROOF

The test replaces `backend.source_keys()` with an assertion failure; the query succeeds because it uses only the owner index and candidate slices.

## TESTS_RUN

```text
python -m py_compile contextor/core/lineage_query/service.py contextor/core/lineage_query/__init__.py: PASS
python -m pytest -q tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py: 67 passed in 2.16s
git diff --check -- contextor/core/lineage_query/service.py contextor/core/lineage_query/__init__.py tests/analysis/test_lineage_query_service.py: PASS
```

## ACTUAL_DIFF

```diff
diff --git a/contextor/core/lineage_query/__init__.py b/contextor/core/lineage_query/__init__.py
@@
+    LineageInterfaceDescriptorMatch,
+    TargetInterfaceFacts,
@@
+    "LineageInterfaceDescriptorMatch",
+    "TargetInterfaceFacts",
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
@@
+    SemanticInterfaceDescriptor,
@@
+class LineageInterfaceDescriptorMatch:
+    source_key: str
+    source_fingerprint: str
+    descriptor: SemanticInterfaceDescriptor
+
+class TargetInterfaceFacts:
+    target: ResolvedLineageTarget
+    metadata: LineageBackendMetadata
+    definitions: tuple[LineageAnchorMatch, ...]
+    descriptors: tuple[LineageInterfaceDescriptorMatch, ...]
+    materialization_complete: bool
+    # definition/descriptor availability, ambiguity, and complete properties
+
+    def target_interface_facts(self, target: ResolvedLineageTarget) -> TargetInterfaceFacts:
+        # Reads owner-index candidate slices only; filters exact defining anchors;
+        # preserves descriptor diagnostics without selecting ambiguous results.
+        ...
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
@@
+    SemanticInterfaceDescriptor,
+    build_return_slot,
@@
+def _target_interface_service(...): ...
+def test_target_interface_reads_only_exact_defining_slice_and_ignores_consumer_copy(...): ...
+def test_target_interface_preserves_legacy_payload_but_fails_closed_on_capability(): ...
+def test_target_interface_complete_authoritative_absence_has_no_descriptor(): ...
+def test_target_interface_duplicate_definitions_fail_closed_without_guessing(): ...
+def test_target_interface_rejects_non_target(): ...
```

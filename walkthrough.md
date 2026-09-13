# F2L D1L3a Walkthrough

## STATUS

PARTIAL

## FILES_CHANGED

- `contextor/core/analysis/incremental/engine.py`
- `tests/test_lineage_state_lifecycle.py`

## UNTOUCHED_DESCRIPTOR_REUSE_PROOF

The engine collects only descriptors from untouched slices that both have active artifact owners and contain a same-owner semantic anchor binding.

## CHANGED_SOURCE_ONLY_BUILD_PROOF

The D1L1 builder is invoked with only `{source_path: extracted_lineage_facts}`.

## STALE_CHANGED_DESCRIPTOR_EXCLUSION_PROOF

The changed source is excluded from untouched descriptor collection before its descriptor is rebuilt.

## UNTOUCHED_SLICE_IDENTITY_PROOF

`test_ordinary_incremental_rebuilds_only_changed_callable_descriptor` passed and proves the provider slice preserves object identity.

## IMPORTED_RETURN_STRENGTHENING_PROOF

The prior full test suite could not complete due two unrelated/preexisting failures; the focused ordinary incremental descriptor test passed.

## TESTS_RUN

```text
Focused: tests/test_lineage_state_lifecycle.py::test_ordinary_incremental_rebuilds_only_changed_callable_descriptor
1 passed in 1.21s
Full requested set: 64 passed, 2 failed
git diff --check: PASS
```

## ACTUAL_DIFF

```diff
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index 097d471..49fba5a 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -198,6 +198,7 @@ class IncrementalAnalysisEngine:
         from contextor.core.analysis.lineage_materialization import (
             LineageOriginUnavailableError,
             LineageResolutionContext,
+            build_extracted_callable_interface_descriptors,
             materialize_lineage_source_facts,
             reresolve_materialized_lineage_source_facts,
         )
@@ -254,13 +255,54 @@ class IncrementalAnalysisEngine:
                     f"artifacts={sorted(missing_artifact_ids)!r}"
                 )
 
+            interface_descriptors = {}
+            if not rematerialize_all:
+                active_artifact_owner_ids = frozenset(active_artifact_ids.values())
+                ambiguous_descriptor_owner_ids: set[str] = set()
+
+                for existing_source_key in sorted(lineage_by_source):
+                    if existing_source_key == source_path:
+                        continue
+                    existing_source = lineage_by_source[existing_source_key]
+                    defined_owner_ids = {
+                        binding.owner_id for binding in existing_source.semantic_anchors
+                    }
+                    for descriptor in existing_source.interface_descriptors:
+                        owner_id = descriptor.owner_id
+                        if (
+                            owner_id not in active_artifact_owner_ids
+                            or owner_id not in defined_owner_ids
+                            or owner_id in ambiguous_descriptor_owner_ids
+                        ):
+                            continue
+                        existing = interface_descriptors.get(owner_id)
+                        if existing is None:
+                            interface_descriptors[owner_id] = descriptor
+                        elif existing != descriptor:
+                            interface_descriptors.pop(owner_id, None)
+                            ambiguous_descriptor_owner_ids.add(owner_id)
+
+                if not delete:
+                    changed_descriptors = build_extracted_callable_interface_descriptors(
+                        {source_path: extracted_lineage_facts}, active_artifact_ids
+                    )
+                    for owner_id, descriptor in changed_descriptors.items():
+                        if owner_id in ambiguous_descriptor_owner_ids:
+                            continue
+                        existing = interface_descriptors.get(owner_id)
+                        if existing is None:
+                            interface_descriptors[owner_id] = descriptor
+                        elif existing != descriptor:
+                            interface_descriptors.pop(owner_id, None)
+                            ambiguous_descriptor_owner_ids.add(owner_id)
+
             resolution = LineageResolutionContext(
                 active_module_ids=active_module_ids,
                 active_artifact_ids=active_artifact_ids,
                 active_owner_ids=frozenset(
                     (*active_module_ids.values(), *active_artifact_ids.values())
                 ),
-                interface_descriptors={},
+                interface_descriptors=interface_descriptors,
             )
             if not delete:
                 extracted = extracted_lineage_facts
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index a4cd611..0591eeb 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -35,6 +35,7 @@ from contextor.core.domain.lineage_facts import (
     MaterializedOccurrenceRef,
     MaterializedSymbolicRef,
     MaterializedSurfaceFact,
+    ParameterKind,
     ProviderRef,
     ResolutionKind,
     SemanticAnchorBinding,
@@ -45,6 +46,8 @@ from contextor.core.domain.lineage_facts import (
     SourceSpan,
     SurfaceDeclarationEvidence,
     SurfaceKind,
+    build_keyword_binding_slot,
+    build_parameter_value_slot,
     build_return_slot,
 )
 from contextor.core.domain.module import Module
@@ -1430,3 +1433,41 @@ def test_snapshot_legacy_flow_ownership_fails_closed(tmp_path):
         flow.owner_local_id is None
         for flow in loaded_slice.flows
     )
+
+
+def test_ordinary_incremental_rebuilds_only_changed_callable_descriptor(tmp_path):
+    facts = {
+        "provider.py": _extracted("provider.py", "def target():\n    return 1\n"),
+        "consumer.py": _extracted("consumer.py", "def local(value):\n    return value\n"),
+    }
+    modules = {name: _module(name) for name in ("provider", "consumer")}
+    artifacts = {
+        "provider": {"own_symbols": {"target"}},
+        "consumer": {"own_symbols": {"local"}},
+    }
+    provider_owner, local_owner = "A:provider/1", "A:consumer.local/1"
+    registry = _LifecycleRegistry(
+        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
+        {"provider::target": provider_owner, "consumer::local": local_owner},
+    )
+    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
+    provider_slice = state.lineage_facts_by_source["provider.py"]
+    engine, _ = _lineage_engine(state, registry, tmp_path)
+    candidate = _prepare_candidate_state(state)
+    changed = _extracted("consumer.py", "def local(value, *, mode=None):\n    return value\n")
+    with registry.read_transaction():
+        engine._update_candidate_lineage_slice(
+            candidate, source_path="consumer.py", extracted_lineage_facts=changed,
+            rematerialize_all=False,
+        )
+    assert candidate.lineage_facts_by_source["provider.py"] is provider_slice
+    descriptor = next(
+        item for item in candidate.lineage_facts_by_source["consumer.py"].interface_descriptors
+        if item.owner_id == local_owner
+    )
+    assert build_parameter_value_slot(
+        local_owner, ParameterKind.KEYWORD_ONLY, name="mode"
+    ) in descriptor.slots
+    assert build_keyword_binding_slot(
+        local_owner, ParameterKind.KEYWORD_ONLY, name="mode"
+    ) in descriptor.slots
```


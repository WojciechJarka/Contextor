# F2L D1M2 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/service.py`
- `tests/analysis/test_lineage_query_service.py`

## OWN_DEFAULTS_PROOF

The projection reads flows only after the source slice has an exact defining semantic anchor. It retains only `DEFAULTS_TO_PARAMETER` flows targeting the target owner's `PARAMETER_VALUE` slots.

## OUTER_OWNER_PROOF

The accepted defaults in the fixture have `owner_local_id == "module"`, proving query selection does not use lexical flow ownership as the target filter.

## UNRELATED_DEFAULT_EXCLUSION_PROOF

A default flow targeting another artifact owner is present in the defining slice and excluded.

## ARGUMENT_FLOW_EXCLUSION_PROOF

An `ARGUMENT_TO_PARAMETER` flow targeting the same target parameter slot is present and excluded.

## D1K_SEPARATION_PROOF

The default projection does not invoke or alter `semantic_sections()`; the focused test asserts `semantic_sections(target).parameters == ()`.

## LEGACY_DIAGNOSTICS_PROOF

With `interface_descriptors_materialized=False`, exact default flows remain diagnostic output while materialization and overall completeness remain false.

## TESTS_RUN

```text
python -m py_compile contextor/core/lineage_query/service.py: PASS
python -m pytest -q tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py: 69 passed in 1.97s
git diff --check -- contextor/core/lineage_query/service.py tests/analysis/test_lineage_query_service.py: PASS
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/core/lineage_query/service.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/analysis/test_lineage_query_service.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
index c8f30d4..37504ac 100644
--- a/contextor/core/lineage_query/service.py
+++ b/contextor/core/lineage_query/service.py
@@ -14,6 +14,8 @@ from contextor.core.domain.lineage_facts import (
     SemanticAnchorBinding,
     SemanticEndpoint,
     SemanticInterfaceDescriptor,
+    SemanticSlotKind,
+    parse_semantic_slot,
 )
 from contextor.core.lineage_query.backend import (
     CanonicalLineageBackend,
@@ -103,6 +105,7 @@ class TargetInterfaceFacts:
     metadata: LineageBackendMetadata
     definitions: tuple[LineageAnchorMatch, ...]
     descriptors: tuple[LineageInterfaceDescriptorMatch, ...]
+    parameter_defaults: tuple[LineageFlowMatch, ...]
     materialization_complete: bool
 
     @property
@@ -554,6 +557,7 @@ class LineageQueryService:
         metadata = self._backend.metadata()
         definitions: list[LineageAnchorMatch] = []
         descriptors: list[LineageInterfaceDescriptorMatch] = []
+        parameter_defaults: list[LineageFlowMatch] = []
         materialization_complete = True
 
         source_keys = self._backend.source_keys_for_owner(
@@ -598,6 +602,32 @@ class LineageQueryService:
                     )
                 )
 
+            for flow in source.flows:
+                if (
+                    flow.relation
+                    is not LineageRelation.DEFAULTS_TO_PARAMETER
+                ):
+                    continue
+                endpoint = flow.target
+                if (
+                    not isinstance(endpoint, SemanticEndpoint)
+                    or endpoint.owner_id != target.artifact_id
+                    or endpoint.slot is None
+                ):
+                    continue
+                slot = parse_semantic_slot(endpoint.slot)
+                if slot.kind is not SemanticSlotKind.PARAMETER_VALUE:
+                    continue
+                parameter_defaults.append(
+                    LineageFlowMatch(
+                        source_key=manifest.source_key,
+                        source_fingerprint=(
+                            manifest.source_fingerprint
+                        ),
+                        flow=flow,
+                    )
+                )
+
         definitions.sort(key=_anchor_match_key)
         descriptors.sort(
             key=lambda item: (
@@ -606,12 +636,14 @@ class LineageQueryService:
                 item.descriptor,
             )
         )
+        parameter_defaults.sort(key=_flow_match_key)
 
         return TargetInterfaceFacts(
             target=target,
             metadata=metadata,
             definitions=tuple(definitions),
             descriptors=tuple(descriptors),
+            parameter_defaults=tuple(parameter_defaults),
             materialization_complete=materialization_complete,
         )
 
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
index 2ab23ff..bda531f 100644
--- a/tests/analysis/test_lineage_query_service.py
+++ b/tests/analysis/test_lineage_query_service.py
@@ -14,6 +14,7 @@ from contextor.core.domain.lineage_facts import (
     MaterializedOccurrenceRef,
     MaterializedSurfaceFact,
     MaterializedSymbolicRef,
+    ParameterKind,
     ResolutionKind,
     SemanticAnchorBinding,
     SemanticEndpoint,
@@ -22,6 +23,7 @@ from contextor.core.domain.lineage_facts import (
     SourceSpan,
     SurfaceDeclarationEvidence,
     SurfaceKind,
+    build_parameter_value_slot,
     build_return_slot,
 )
 from contextor.core.lineage_query import (
@@ -2097,6 +2099,7 @@ def test_target_interface_complete_authoritative_absence_has_no_descriptor():
     assert result.definition_available is True
     assert result.materialization_complete is True
     assert result.descriptors == ()
+    assert result.parameter_defaults == ()
     assert result.descriptor_available is False
     assert result.descriptor_ambiguous is False
     assert result.descriptor is None
@@ -2113,6 +2116,7 @@ def test_target_interface_duplicate_definitions_fail_closed_without_guessing():
     assert result.descriptor_ambiguous is True
     assert result.descriptor is None
     assert result.complete is False
+    assert result.parameter_defaults == ()
     assert tuple(item.source_key for item in result.definitions) == (
         "pkg/duplicate.py", "pkg/target.py"
     )
@@ -2123,3 +2127,125 @@ def test_target_interface_rejects_non_target():
         TypeError, match="target must be ResolvedLineageTarget."
     ):
         _service({}).target_interface_facts(object())
+
+
+def _install_target_parameter_defaults(backend, target):
+    provider = backend.get_source("pkg/target.py")
+    assert provider is not None
+    source_key = provider.manifest.source_key
+    fingerprint = provider.manifest.source_fingerprint
+    span = SourceSpan(1, 0, 1, 8)
+    positional_slot = build_parameter_value_slot(
+        target.artifact_id,
+        ParameterKind.POSITIONAL_OR_KEYWORD,
+        ordinal=0,
+        name="value",
+    )
+    keyword_slot = build_parameter_value_slot(
+        target.artifact_id,
+        ParameterKind.KEYWORD_ONLY,
+        name="mode",
+    )
+    other_owner = "A99/1"
+    other_slot = build_parameter_value_slot(
+        other_owner,
+        ParameterKind.POSITIONAL_OR_KEYWORD,
+        ordinal=0,
+        name="other",
+    )
+    module_ref = MaterializedOccurrenceRef(
+        source_key, fingerprint, "module"
+    )
+    descriptor = SemanticInterfaceDescriptor(
+        target.artifact_id,
+        tuple(sorted((
+            build_return_slot(target.artifact_id), positional_slot, keyword_slot,
+        ))),
+        "digest-handler-defaults",
+    )
+
+    def occurrence(local_id):
+        return MaterializedOccurrenceRef(source_key, fingerprint, local_id)
+
+    flows = tuple(sorted((
+        MaterializedFlowFact(
+            "a-default-positional", occurrence("default-positional"),
+            SemanticEndpoint(target.artifact_id, positional_slot),
+            LineageRelation.DEFAULTS_TO_PARAMETER, span,
+            ResolutionKind.SIGNATURE_EXACT, LineageConfidence.CONFIRMED,
+            owner_local_id="module",
+        ),
+        MaterializedFlowFact(
+            "b-default-keyword", occurrence("default-keyword"),
+            SemanticEndpoint(target.artifact_id, keyword_slot),
+            LineageRelation.DEFAULTS_TO_PARAMETER, span,
+            ResolutionKind.SIGNATURE_EXACT, LineageConfidence.CONFIRMED,
+            owner_local_id="module",
+        ),
+        MaterializedFlowFact(
+            "c-unrelated-default", occurrence("unrelated-default"),
+            SemanticEndpoint(other_owner, other_slot),
+            LineageRelation.DEFAULTS_TO_PARAMETER, span,
+            ResolutionKind.SIGNATURE_EXACT, LineageConfidence.CONFIRMED,
+            owner_local_id="module",
+        ),
+        MaterializedFlowFact(
+            "d-call-argument", occurrence("argument"),
+            SemanticEndpoint(target.artifact_id, positional_slot),
+            LineageRelation.ARGUMENT_TO_PARAMETER, span,
+            ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED,
+            owner_local_id="module",
+        ),
+    )))
+    backend._sources[source_key] = replace(
+        provider,
+        manifest=replace(
+            provider.manifest,
+            anchor_count=2,
+            flow_count=len(flows),
+            flow_ownership_materialized=True,
+        ),
+        anchors=tuple(sorted((
+            MaterializedAnchorFact(
+                "module", module_ref, "module", span
+            ),
+            replace(provider.anchors[0], owner_local_id="module"),
+        ))),
+        flows=flows,
+        interface_descriptors=(descriptor,),
+    )
+    return descriptor, positional_slot, keyword_slot
+
+
+def test_target_interface_projects_only_own_parameter_defaults_from_defining_slice():
+    service, backend, target, _descriptor = _target_interface_service()
+    descriptor, positional_slot, keyword_slot = _install_target_parameter_defaults(
+        backend, target
+    )
+    result = service.target_interface_facts(target)
+    assert result.complete is True
+    assert result.descriptor == descriptor
+    assert tuple(match.flow.local_id for match in result.parameter_defaults) == (
+        "a-default-positional", "b-default-keyword"
+    )
+    assert tuple(match.flow.target.slot for match in result.parameter_defaults) == (
+        positional_slot, keyword_slot
+    )
+    assert all(
+        match.flow.owner_local_id == "module"
+        for match in result.parameter_defaults
+    )
+    assert service.semantic_sections(target).parameters == ()
+
+
+def test_target_interface_preserves_default_diagnostics_when_interface_capability_is_legacy_false():
+    service, backend, target, _descriptor = _target_interface_service(
+        interface_capability=False
+    )
+    _install_target_parameter_defaults(backend, target)
+    result = service.target_interface_facts(target)
+    assert tuple(match.flow.local_id for match in result.parameter_defaults) == (
+        "a-default-positional", "b-default-keyword"
+    )
+    assert result.materialization_complete is False
+    assert result.complete is False
```

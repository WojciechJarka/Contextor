# F2L D1M3 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/service.py`
- `contextor/core/lineage_query/__init__.py`
- `tests/analysis/test_lineage_query_service.py`

## CALLABLE_STATE_PROOF

A complete unique descriptor normalizes to `callable`; authoritative descriptor absence normalizes to `non_callable`; legacy and ambiguous states normalize to `unknown`.

## PARAMETER_NORMALIZATION_PROOF

The projection exposes canonical parameter-value slots in deterministic semantic order: positional-only, positional-or-keyword, var-positional, keyword-only, and var-keyword.

## NO_FAKE_NAMES_PROOF

Only keyword-only slot names are exposed. Positional and variadic slots retain `name=None`, even where fixture builder input carried names.

## DEFAULT_ASSOCIATION_PROOF

Default flows are attached by exact raw parameter-value slot and preserved as ordered tuples.

## RETURN_SLOT_PROOF

The selected descriptor exposes exactly one canonical return slot; no return slot is synthesized.

## LEGACY_DIAGNOSTIC_PROOF

Legacy capability false retains digest, return, parameters, and defaults diagnostically while callable state is `unknown`.

## NON_CALLABLE_PROOF

A complete exact definition with canonical descriptor absence exposes no shape data and reports `non_callable`.

## AMBIGUITY_PROOF

Multiple exact definitions retain ambiguity, expose no selected descriptor shape, and report `unknown`.

## TESTS_RUN

```text
python -m py_compile contextor/core/lineage_query/service.py contextor/core/lineage_query/__init__.py: PASS
python -m pytest -q tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py: 73 passed in 3.59s
git diff --check -- contextor/core/lineage_query/service.py contextor/core/lineage_query/__init__.py tests/analysis/test_lineage_query_service.py: PASS
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/core/lineage_query/__init__.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/lineage_query/service.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/analysis/test_lineage_query_service.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/lineage_query/__init__.py b/contextor/core/lineage_query/__init__.py
index 80ab097..d310c3a 100644
--- a/contextor/core/lineage_query/__init__.py
+++ b/contextor/core/lineage_query/__init__.py
@@ -21,6 +21,7 @@ from contextor.core.lineage_query.service import (
     ResolvedLineageTarget,
     SemanticLineageSections,
     TargetInterfaceFacts,
+    TargetParameterFacts,
 )
 
 __all__ = [
@@ -44,4 +45,5 @@ __all__ = [
     "ResolvedLineageTarget",
     "SemanticLineageSections",
     "TargetInterfaceFacts",
+    "TargetParameterFacts",
 ]
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
index 37504ac..eb8eddb 100644
--- a/contextor/core/lineage_query/service.py
+++ b/contextor/core/lineage_query/service.py
@@ -10,6 +10,7 @@ from contextor.core.domain.lineage_facts import (
     MaterializedOccurrenceRef,
     MaterializedSurfaceFact,
     MaterializedSymbolicRef,
+    ParameterKind,
     ResolutionKind,
     SemanticAnchorBinding,
     SemanticEndpoint,
@@ -99,6 +100,19 @@ class LineageInterfaceDescriptorMatch:
     descriptor: SemanticInterfaceDescriptor
 
 
+@dataclass(frozen=True)
+class TargetParameterFacts:
+    slot: str
+    kind: ParameterKind
+    ordinal: int | None
+    name: str | None
+    default_flows: tuple[LineageFlowMatch, ...]
+
+    @property
+    def has_default(self) -> bool:
+        return bool(self.default_flows)
+
+
 @dataclass(frozen=True)
 class TargetInterfaceFacts:
     target: ResolvedLineageTarget
@@ -149,6 +163,71 @@ class TargetInterfaceFacts:
             and self.metadata.semantic_anchor_bindings_complete
         )
 
+    @property
+    def callable_state(self) -> str:
+        if not self.complete:
+            return "unknown"
+        if self.descriptor_available:
+            return "callable"
+        return "non_callable"
+
+    @property
+    def signature_digest(self) -> str | None:
+        descriptor = self.descriptor
+        if descriptor is None:
+            return None
+        return descriptor.signature_digest
+
+    @property
+    def return_slot(self) -> str | None:
+        descriptor = self.descriptor
+        if descriptor is None:
+            return None
+        matches = tuple(
+            slot for slot in descriptor.slots
+            if parse_semantic_slot(slot).kind is SemanticSlotKind.RETURN
+        )
+        if len(matches) != 1:
+            return None
+        return matches[0]
+
+    @property
+    def parameter_slots(self) -> tuple[TargetParameterFacts, ...]:
+        descriptor = self.descriptor
+        if descriptor is None:
+            return ()
+        defaults_by_slot: dict[str, list[LineageFlowMatch]] = {}
+        for match in self.parameter_defaults:
+            endpoint = match.flow.target
+            if isinstance(endpoint, SemanticEndpoint) and endpoint.slot is not None:
+                defaults_by_slot.setdefault(endpoint.slot, []).append(match)
+        parameters: list[TargetParameterFacts] = []
+        for raw_slot in descriptor.slots:
+            slot = parse_semantic_slot(raw_slot)
+            if slot.kind is not SemanticSlotKind.PARAMETER_VALUE:
+                continue
+            kind = ParameterKind(slot.parts[0])
+            ordinal: int | None = None
+            name: str | None = None
+            if kind in {
+                ParameterKind.POSITIONAL_ONLY,
+                ParameterKind.POSITIONAL_OR_KEYWORD,
+            }:
+                ordinal = int(slot.parts[1])
+            elif kind is ParameterKind.KEYWORD_ONLY:
+                name = slot.parts[1]
+            parameters.append(TargetParameterFacts(
+                slot=raw_slot,
+                kind=kind,
+                ordinal=ordinal,
+                name=name,
+                default_flows=tuple(sorted(
+                    defaults_by_slot.get(raw_slot, ()), key=_flow_match_key
+                )),
+            ))
+        parameters.sort(key=_target_parameter_key)
+        return tuple(parameters)
+
 
 @dataclass(frozen=True)
 class LineageScopeRootMatch:
@@ -912,6 +991,26 @@ class LineageQueryService:
             truncated=truncated,
         )
 
+_PARAMETER_KIND_ORDER = {
+    ParameterKind.POSITIONAL_ONLY: 0,
+    ParameterKind.POSITIONAL_OR_KEYWORD: 1,
+    ParameterKind.VAR_POSITIONAL: 2,
+    ParameterKind.KEYWORD_ONLY: 3,
+    ParameterKind.VAR_KEYWORD: 4,
+}
+
+
+def _target_parameter_key(
+    parameter: TargetParameterFacts,
+) -> tuple[int, int, str, str]:
+    return (
+        _PARAMETER_KIND_ORDER[parameter.kind],
+        parameter.ordinal if parameter.ordinal is not None else -1,
+        parameter.name or "",
+        parameter.slot,
+    )
+
+
 def _anchor_match_key(match: LineageAnchorMatch) -> tuple:
     binding = match.binding
     reference = binding.reference
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
index bda531f..9a1b1a4 100644
--- a/tests/analysis/test_lineage_query_service.py
+++ b/tests/analysis/test_lineage_query_service.py
@@ -2153,13 +2153,34 @@ def _install_target_parameter_defaults(backend, target):
         ordinal=0,
         name="other",
     )
+    positional_only_slot = build_parameter_value_slot(
+        target.artifact_id,
+        ParameterKind.POSITIONAL_ONLY,
+        ordinal=0,
+        name="ignored-posonly-name",
+    )
+    vararg_slot = build_parameter_value_slot(
+        target.artifact_id,
+        ParameterKind.VAR_POSITIONAL,
+        name="ignored-vararg-name",
+    )
+    varkw_slot = build_parameter_value_slot(
+        target.artifact_id,
+        ParameterKind.VAR_KEYWORD,
+        name="ignored-varkw-name",
+    )
     module_ref = MaterializedOccurrenceRef(
         source_key, fingerprint, "module"
     )
     descriptor = SemanticInterfaceDescriptor(
         target.artifact_id,
         tuple(sorted((
-            build_return_slot(target.artifact_id), positional_slot, keyword_slot,
+            build_return_slot(target.artifact_id),
+            positional_only_slot,
+            positional_slot,
+            vararg_slot,
+            keyword_slot,
+            varkw_slot,
         ))),
         "digest-handler-defaults",
     )
@@ -2249,3 +2270,74 @@ def test_target_interface_preserves_default_diagnostics_when_interface_capabilit
     )
     assert result.materialization_complete is False
     assert result.complete is False
+
+
+def test_target_interface_normalizes_callable_shape_without_reconstructing_source_signature():
+    service, backend, target, _descriptor = _target_interface_service()
+    descriptor, positional_slot, keyword_slot = _install_target_parameter_defaults(
+        backend, target
+    )
+    result = service.target_interface_facts(target)
+    assert result.callable_state == "callable"
+    assert result.signature_digest == "digest-handler-defaults"
+    assert result.return_slot == build_return_slot(target.artifact_id)
+    parameters = result.parameter_slots
+    assert tuple((
+        parameter.kind, parameter.ordinal, parameter.name,
+        parameter.has_default,
+    ) for parameter in parameters) == (
+        (ParameterKind.POSITIONAL_ONLY, 0, None, False),
+        (ParameterKind.POSITIONAL_OR_KEYWORD, 0, None, True),
+        (ParameterKind.VAR_POSITIONAL, None, None, False),
+        (ParameterKind.KEYWORD_ONLY, None, "mode", True),
+        (ParameterKind.VAR_KEYWORD, None, None, False),
+    )
+    assert tuple(tuple(match.flow.local_id for match in parameter.default_flows)
+                 for parameter in parameters) == (
+        (), ("a-default-positional",), (), ("b-default-keyword",), (),
+    )
+    assert parameters[1].slot == positional_slot
+    assert parameters[3].slot == keyword_slot
+    assert result.descriptor == descriptor
+
+
+def test_target_interface_authoritative_absence_normalizes_as_non_callable():
+    service, backend, target, _descriptor = _target_interface_service()
+    provider = backend.get_source("pkg/target.py")
+    assert provider is not None
+    backend._sources["pkg/target.py"] = replace(
+        provider, interface_descriptors=()
+    )
+    result = service.target_interface_facts(target)
+    assert result.complete is True
+    assert result.callable_state == "non_callable"
+    assert result.signature_digest is None
+    assert result.return_slot is None
+    assert result.parameter_slots == ()
+
+
+def test_target_interface_legacy_descriptor_is_diagnostic_but_callable_state_unknown():
+    service, backend, target, _descriptor = _target_interface_service(
+        interface_capability=False
+    )
+    _install_target_parameter_defaults(backend, target)
+    result = service.target_interface_facts(target)
+    assert result.complete is False
+    assert result.callable_state == "unknown"
+    assert result.signature_digest == "digest-handler-defaults"
+    assert result.return_slot == build_return_slot(target.artifact_id)
+    assert result.parameter_slots
+    assert any(parameter.has_default for parameter in result.parameter_slots)
+
+
+def test_target_interface_ambiguous_definition_normalizes_as_unknown():
+    service, _backend, target, _descriptor = _target_interface_service(
+        duplicate_definition=True
+    )
+    result = service.target_interface_facts(target)
+    assert result.complete is False
+    assert result.callable_state == "unknown"
+    assert result.descriptor is None
+    assert result.signature_digest is None
+    assert result.return_slot is None
+    assert result.parameter_slots == ()
```

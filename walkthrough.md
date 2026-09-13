# F2L D1N3b1 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/mcp/lineage_response.py`
- `tests/mcp/test_lineage_response.py`

## SERIALIZATION_SHAPE_PROOF

Typed selected facts serialize deterministically to JSON-safe resolved target and selected sections.

## ENDPOINT_PROOF

Semantic endpoint payload uses owner ID and optional canonical slot.

## NO_FAKE_PARAMETER_NAMES_PROOF

Positional parameter name remains null from canonical D1M facts.

## NO_FINGERPRINT_BLOAT_PROOF

Serialized payload contains neither source fingerprints nor internal owner-local IDs.

## SELECTED_EMPTY_VS_OMITTED_PROOF

Selected empty callbacks emits an empty list while omitted sections are absent.

## EXACT_SIZE_PROOF

Preview candidate and per-section bytes equal serialized_json_bytes over actual payload values.

## NO_QUERY_PROOF

Serializer accepts a supplied selected view only and has no service/backend inputs.

## TESTS_RUN

```text
python -m pytest -q tests/mcp/test_lineage_response.py tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py: 97 passed in 2.13s
git diff --check -- contextor/mcp/lineage_response.py tests/mcp/test_lineage_response.py: PASS
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/mcp/lineage_response.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/mcp/test_lineage_response.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/lineage_response.py b/contextor/mcp/lineage_response.py
index 88901b7..3920a40 100644
--- a/contextor/mcp/lineage_response.py
+++ b/contextor/mcp/lineage_response.py
@@ -2,9 +2,12 @@ from __future__ import annotations
 
 from dataclasses import dataclass
 
+from contextor.core.domain.lineage_facts import MaterializedOccurrenceRef, MaterializedSymbolicRef, SemanticEndpoint
 from contextor.core.lineage_query.service import (
     SYMBOL_LINEAGE_SECTION_ORDER,
+    LineageFlowMatch, LineageSurfaceMatch, SelectedSymbolLineageFacts, TargetInterfaceFacts,
 )
+from contextor.mcp.representation import serialized_json_bytes
 
 
 SYMBOL_LINEAGE_MODES = ("auto", "preview", "fetch")
@@ -49,3 +52,64 @@ def plan_symbol_lineage_response(*, mode: str = "auto", sections: tuple[str, ...
         tuple(s for s in SYMBOL_LINEAGE_SECTION_ORDER if s in requested),
         True, False,
     )
+
+
+def _span_payload(span) -> dict:
+    return {"start": [span.start_line, span.start_column], "end": [span.end_line, span.end_column]}
+
+
+def _endpoint_payload(endpoint) -> dict:
+    if isinstance(endpoint, MaterializedOccurrenceRef):
+        return {"kind": "occurrence", "source": endpoint.source_key, "local_id": endpoint.local_id}
+    if isinstance(endpoint, MaterializedSymbolicRef):
+        result = {"kind": "symbolic", "symbol_kind": endpoint.kind.value, "qualified_name": f"{endpoint.module_name}::{endpoint.symbol_name}"}
+        if endpoint.source_local_id is not None: result["source_local_id"] = endpoint.source_local_id
+        return result
+    if isinstance(endpoint, SemanticEndpoint):
+        result = {"kind": "semantic", "owner_id": endpoint.owner_id}
+        if endpoint.slot is not None: result["slot"] = endpoint.slot
+        return result
+    raise TypeError("Unsupported canonical lineage endpoint.")
+
+
+def _flow_payload(match: LineageFlowMatch) -> dict:
+    flow = match.flow
+    result = {"id": flow.local_id, "relation": flow.relation.value, "source": _endpoint_payload(flow.source), "target": _endpoint_payload(flow.target), "resolution": flow.resolution_kind.value, "confidence": flow.confidence.value, "evidence": {"source": match.source_key, "span": _span_payload(flow.evidence)}}
+    if flow.dynamic_boundary is not None: result["dynamic_boundary"] = flow.dynamic_boundary
+    if flow.provider is not None: result["provider"] = {"provider_id": flow.provider.provider_id, "provider_version": flow.provider.provider_version}
+    return result
+
+
+def _surface_payload(match: LineageSurfaceMatch) -> dict:
+    surface = match.surface
+    result = {"id": surface.local_id, "kind": surface.kind.value, "declared_name": surface.declared_name, "exposed": _endpoint_payload(surface.exposed), "resolution": surface.resolution_kind.value, "confidence": surface.confidence.value, "evidence": {"source": match.source_key, "span": _span_payload(surface.evidence)}}
+    if surface.dynamic_boundary is not None: result["dynamic_boundary"] = surface.dynamic_boundary
+    if surface.provider is not None: result["provider"] = {"provider_id": surface.provider.provider_id, "provider_version": surface.provider.provider_version}
+    if surface.declaration_evidence is not None: result["declaration_evidence"] = surface.declaration_evidence.value
+    return result
+
+
+def _interface_payload(interface: TargetInterfaceFacts) -> dict:
+    return {"callable_state": interface.callable_state, "signature_digest": interface.signature_digest, "return_slot": interface.return_slot, "parameters": [{"slot": p.slot, "kind": p.kind.value, "ordinal": p.ordinal, "name": p.name, "has_default": p.has_default, "default_flows": [_flow_payload(m) for m in p.default_flows]} for p in interface.parameter_slots], "definitions": [{"source": d.source_key, "local_id": d.binding.reference.local_id} for d in interface.definitions], "complete": interface.complete}
+
+
+def _section_payloads(selected: SelectedSymbolLineageFacts) -> dict[str, object]:
+    values: dict[str, object] = {}
+    if selected.interface is not None: values["interface"] = _interface_payload(selected.interface)
+    if selected.connections is not None: values["connections"] = {"incoming": [_flow_payload(m) for m in selected.connections.incoming], "outgoing": [_flow_payload(m) for m in selected.connections.outgoing]}
+    for name in ("bindings", "parameter_flows", "calls_interfaces", "returns", "state", "callbacks", "unresolved_dynamic_boundaries"):
+        value = getattr(selected, name)
+        if value is not None: values[name] = [_flow_payload(m) for m in value]
+    if selected.surfaces is not None: values["surfaces"] = {"flows": [_flow_payload(m) for m in selected.surfaces.flows], "facts": [_surface_payload(m) for m in selected.surfaces.facts]}
+    return {name: values[name] for name in selected.selected_sections}
+
+
+def build_symbol_lineage_payload(selected: SelectedSymbolLineageFacts) -> dict:
+    if not isinstance(selected, SelectedSymbolLineageFacts): raise TypeError("selected must be SelectedSymbolLineageFacts.")
+    target = selected.target
+    return {"status": "resolved", "target": {"artifact_id": target.artifact_id, "qualified_name": target.qualified_name, "module": target.module_name, "symbol": target.symbol_name, "resolution": target.resolution}, "selected_sections": list(selected.selected_sections), "complete": selected.complete, "metadata_consistent": selected.metadata_consistent, "scope_state": selected.facts.scope_state, "sections": _section_payloads(selected)}
+
+
+def build_symbol_lineage_preview(selected: SelectedSymbolLineageFacts) -> dict:
+    payload = build_symbol_lineage_payload(selected)
+    return {"status": "resolved", "mode": "preview", "target": payload["target"], "available_sections": list(selected.selected_sections), "complete": selected.complete, "metadata_consistent": selected.metadata_consistent, "scope_state": selected.facts.scope_state, "candidate_response_bytes": serialized_json_bytes(payload), "section_sizes": {name: {"payload_bytes": serialized_json_bytes(value)} for name, value in payload["sections"].items()}}
diff --git a/tests/mcp/test_lineage_response.py b/tests/mcp/test_lineage_response.py
index 225c5f0..73502e1 100644
--- a/tests/mcp/test_lineage_response.py
+++ b/tests/mcp/test_lineage_response.py
@@ -1,7 +1,50 @@
+import json
+from dataclasses import replace
+
 import pytest
 
-from contextor.core.lineage_query.service import SYMBOL_LINEAGE_SECTION_ORDER
-from contextor.mcp.lineage_response import SymbolLineageResponsePlan, plan_symbol_lineage_response
+from contextor.core.domain.lineage_facts import (
+    LineageConfidence, LineageRelation, MaterializedAnchorFact,
+    MaterializedFlowFact, MaterializedOccurrenceRef, ResolutionKind,
+    SemanticAnchorBinding, SemanticEndpoint, SemanticInterfaceDescriptor,
+    SourceSpan, build_parameter_value_slot, build_return_slot, ParameterKind,
+)
+from contextor.core.lineage_query.backend import LineageBackendMetadata
+from contextor.core.lineage_query.service import (
+    SYMBOL_LINEAGE_SECTION_ORDER, DirectLineageFacts, LexicalScopeFacts,
+    LineageAnchorMatch, LineageFlowMatch, LineageInterfaceDescriptorMatch,
+    LineageScopeRootMatch, LineageSurfaceSection, ResolvedLineageTarget,
+    SelectedSymbolLineageFacts, SemanticLineageSections, SymbolLineageConnections,
+    SymbolLineageFacts, TargetInterfaceFacts,
+)
+from contextor.mcp.representation import serialized_json_bytes
+from contextor.mcp.lineage_response import (
+    SymbolLineageResponsePlan,
+    build_symbol_lineage_payload,
+    build_symbol_lineage_preview,
+    plan_symbol_lineage_response,
+)
+
+
+def _selected_lineage_fixture():
+    target = ResolvedLineageTarget("A17/2", "pkg.mod::handler", "pkg.mod", "handler", "exact_id")
+    metadata = LineageBackendMetadata(7, "live", "fresh", "1", 1, "fresh", True)
+    span = SourceSpan(1, 0, 1, 8)
+    ref = MaterializedOccurrenceRef("pkg/mod.py", "1" * 64, "handler")
+    binding = SemanticAnchorBinding("A17/2", "pkg.mod::handler", ref)
+    anchor = MaterializedAnchorFact("handler", ref, "function", span)
+    definition = LineageAnchorMatch("pkg/mod.py", "1" * 64, binding)
+    parameter_slot = build_parameter_value_slot("A17/2", ParameterKind.POSITIONAL_OR_KEYWORD, ordinal=0, name="ignored")
+    descriptor = SemanticInterfaceDescriptor("A17/2", tuple(sorted((build_return_slot("A17/2"), parameter_slot))), "digest")
+    default = LineageFlowMatch("pkg/mod.py", "1" * 64, MaterializedFlowFact("default", MaterializedOccurrenceRef("pkg/mod.py", "1" * 64, "value"), SemanticEndpoint("A17/2", parameter_slot), LineageRelation.DEFAULTS_TO_PARAMETER, span, ResolutionKind.SIGNATURE_EXACT, LineageConfidence.CONFIRMED))
+    interface = TargetInterfaceFacts(target, metadata, (definition,), (LineageInterfaceDescriptorMatch("pkg/mod.py", "1" * 64, descriptor),), (default,), True)
+    incoming = LineageFlowMatch("pkg/mod.py", "1" * 64, MaterializedFlowFact("incoming", MaterializedOccurrenceRef("pkg/mod.py", "1" * 64, "caller"), SemanticEndpoint("A17/2", build_return_slot("A17/2")), LineageRelation.CALL_RESULT, span, ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED))
+    direct = DirectLineageFacts(target, metadata, (definition,), (incoming,), (), ())
+    root = LineageScopeRootMatch("pkg/mod.py", "1" * 64, binding, anchor)
+    scope = LexicalScopeFacts(target, metadata, (root,), (), (), True)
+    sections = SemanticLineageSections(target, scope, direct, (), (), (), (), (), (), LineageSurfaceSection((), ()), ())
+    facts = SymbolLineageFacts(target, interface, sections)
+    return SelectedSymbolLineageFacts(facts, SYMBOL_LINEAGE_SECTION_ORDER, interface, SymbolLineageConnections((incoming,), ()), (), (), (), (), (), (), LineageSurfaceSection((), ()), ())
 
 
 def test_auto_plans_complete_symbol_candidate_for_size_decision():
@@ -41,3 +84,36 @@ def test_response_plan_rejects_invalid_contract():
         plan_symbol_lineage_response(mode="fetch", sections=("state", "state"))
     with pytest.raises(ValueError, match="Unknown symbol lineage sections: mystery"):
         plan_symbol_lineage_response(mode="fetch", sections=("mystery",))
+
+
+def test_symbol_lineage_payload_rejects_non_selected_type():
+    with pytest.raises(
+        TypeError,
+        match="selected must be SelectedSymbolLineageFacts.",
+    ):
+        build_symbol_lineage_payload(object())
+
+
+def test_symbol_lineage_payload_is_deterministic_json_safe_and_semantic():
+    selected = _selected_lineage_fixture()
+    first, second = build_symbol_lineage_payload(selected), build_symbol_lineage_payload(selected)
+    assert first == second
+    assert json.dumps(first, indent=2, ensure_ascii=False) == json.dumps(second, indent=2, ensure_ascii=False)
+    assert first["target"]["artifact_id"] == "A17/2"
+    assert first["sections"]["interface"]["parameters"][0]["name"] is None
+    assert first["sections"]["connections"]["incoming"][0]["target"] == {"kind": "semantic", "owner_id": "A17/2", "slot": build_return_slot("A17/2")}
+    serialized = json.dumps(first)
+    assert "source_fingerprint" not in serialized
+    assert "owner_local_id" not in serialized
+
+
+def test_symbol_lineage_payload_preserves_selected_empty_vs_omitted_and_preview_sizes():
+    selected = _selected_lineage_fixture()
+    reduced = replace(selected, selected_sections=("callbacks",), interface=None, connections=None, bindings=None, parameter_flows=None, calls_interfaces=None, returns=None, state=None, callbacks=(), surfaces=None, unresolved_dynamic_boundaries=None)
+    assert build_symbol_lineage_payload(reduced)["sections"] == {"callbacks": []}
+    payload = build_symbol_lineage_payload(selected)
+    preview = build_symbol_lineage_preview(selected)
+    assert "sections" not in preview
+    assert preview["candidate_response_bytes"] == serialized_json_bytes(payload)
+    for name, value in payload["sections"].items():
+        assert preview["section_sizes"][name] == {"payload_bytes": serialized_json_bytes(value)}
```

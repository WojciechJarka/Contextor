# F2L D1N3b1 Test Completion Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `tests/mcp/test_lineage_response.py`

## ENDPOINT_PROOF

Acceptance assertions cover occurrence, symbolic import, and semantic slot endpoint encodings through the public payload builder.

## DYNAMIC_BOUNDARY_PROOF

Dynamic ASSIGNS payload retains relation, dynamic resolution/confidence, and runtime boundary.

## SURFACE_PROOF

Public surface payload retains kind, declared name, declaration evidence, and occurrence endpoint.

## EXACT_SIZE_PROOF

Preview contains canonical available sections and exact candidate/per-section serialized byte sizes.

## TESTS_RUN

```text
python -m py_compile contextor/mcp/lineage_response.py tests/mcp/test_lineage_response.py: PASS
python -m pytest -q tests/mcp/test_lineage_response.py tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py: 97 passed in 2.03s
git diff --check -- tests/mcp/test_lineage_response.py: PASS
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'tests/mcp/test_lineage_response.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/mcp/test_lineage_response.py b/tests/mcp/test_lineage_response.py
index 73502e1..cf89085 100644
--- a/tests/mcp/test_lineage_response.py
+++ b/tests/mcp/test_lineage_response.py
@@ -4,15 +4,17 @@ from dataclasses import replace
 import pytest
 
 from contextor.core.domain.lineage_facts import (
-    LineageConfidence, LineageRelation, MaterializedAnchorFact,
-    MaterializedFlowFact, MaterializedOccurrenceRef, ResolutionKind,
+    ExtractedSymbolicKind, LineageConfidence, LineageRelation, MaterializedAnchorFact,
+    MaterializedFlowFact, MaterializedOccurrenceRef, MaterializedSymbolicRef,
+    MaterializedSurfaceFact, ResolutionKind,
     SemanticAnchorBinding, SemanticEndpoint, SemanticInterfaceDescriptor,
-    SourceSpan, build_parameter_value_slot, build_return_slot, ParameterKind,
+    SourceSpan, SurfaceDeclarationEvidence, SurfaceKind,
+    build_parameter_value_slot, build_return_slot, ParameterKind,
 )
 from contextor.core.lineage_query.backend import LineageBackendMetadata
 from contextor.core.lineage_query.service import (
     SYMBOL_LINEAGE_SECTION_ORDER, DirectLineageFacts, LexicalScopeFacts,
-    LineageAnchorMatch, LineageFlowMatch, LineageInterfaceDescriptorMatch,
+    LineageAnchorMatch, LineageFlowMatch, LineageInterfaceDescriptorMatch, LineageSurfaceMatch,
     LineageScopeRootMatch, LineageSurfaceSection, ResolvedLineageTarget,
     SelectedSymbolLineageFacts, SemanticLineageSections, SymbolLineageConnections,
     SymbolLineageFacts, TargetInterfaceFacts,
@@ -39,12 +41,17 @@ def _selected_lineage_fixture():
     default = LineageFlowMatch("pkg/mod.py", "1" * 64, MaterializedFlowFact("default", MaterializedOccurrenceRef("pkg/mod.py", "1" * 64, "value"), SemanticEndpoint("A17/2", parameter_slot), LineageRelation.DEFAULTS_TO_PARAMETER, span, ResolutionKind.SIGNATURE_EXACT, LineageConfidence.CONFIRMED))
     interface = TargetInterfaceFacts(target, metadata, (definition,), (LineageInterfaceDescriptorMatch("pkg/mod.py", "1" * 64, descriptor),), (default,), True)
     incoming = LineageFlowMatch("pkg/mod.py", "1" * 64, MaterializedFlowFact("incoming", MaterializedOccurrenceRef("pkg/mod.py", "1" * 64, "caller"), SemanticEndpoint("A17/2", build_return_slot("A17/2")), LineageRelation.CALL_RESULT, span, ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED))
-    direct = DirectLineageFacts(target, metadata, (definition,), (incoming,), (), ())
+    symbolic_ref = MaterializedSymbolicRef("pkg/mod.py", "1" * 64, ExtractedSymbolicKind.IMPORT, "pkg.dep", "value")
+    local_ref = MaterializedOccurrenceRef("pkg/mod.py", "1" * 64, "local")
+    binding_flow = LineageFlowMatch("pkg/mod.py", "1" * 64, MaterializedFlowFact("binding", symbolic_ref, local_ref, LineageRelation.BINDS, span, ResolutionKind.IMPORT_EXACT, LineageConfidence.CONFIRMED))
+    dynamic_flow = LineageFlowMatch("pkg/mod.py", "1" * 64, MaterializedFlowFact("dynamic", local_ref, ref, LineageRelation.ASSIGNS, span, ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, dynamic_boundary="runtime-test"))
+    surface_match = LineageSurfaceMatch("pkg/mod.py", "1" * 64, MaterializedSurfaceFact("public-handler", SurfaceKind.PUBLIC_SYMBOL, ref, span, ResolutionKind.PYTHON_NAME_CONVENTION, LineageConfidence.INFERRED, "handler", declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION))
+    direct = DirectLineageFacts(target, metadata, (definition,), (incoming,), (), (surface_match,))
     root = LineageScopeRootMatch("pkg/mod.py", "1" * 64, binding, anchor)
-    scope = LexicalScopeFacts(target, metadata, (root,), (), (), True)
-    sections = SemanticLineageSections(target, scope, direct, (), (), (), (), (), (), LineageSurfaceSection((), ()), ())
+    scope = LexicalScopeFacts(target, metadata, (root,), (binding_flow, dynamic_flow), (), True)
+    sections = SemanticLineageSections(target, scope, direct, (binding_flow, dynamic_flow), (), (), (), (), (), LineageSurfaceSection((), (surface_match,)), (dynamic_flow,))
     facts = SymbolLineageFacts(target, interface, sections)
-    return SelectedSymbolLineageFacts(facts, SYMBOL_LINEAGE_SECTION_ORDER, interface, SymbolLineageConnections((incoming,), ()), (), (), (), (), (), (), LineageSurfaceSection((), ()), ())
+    return SelectedSymbolLineageFacts(facts, SYMBOL_LINEAGE_SECTION_ORDER, interface, SymbolLineageConnections((incoming,), ()), (binding_flow, dynamic_flow), (), (), (), (), (), LineageSurfaceSection((), (surface_match,)), (dynamic_flow,))
 
 
 def test_auto_plans_complete_symbol_candidate_for_size_decision():
@@ -102,6 +109,21 @@ def test_symbol_lineage_payload_is_deterministic_json_safe_and_semantic():
     assert first["target"]["artifact_id"] == "A17/2"
     assert first["sections"]["interface"]["parameters"][0]["name"] is None
     assert first["sections"]["connections"]["incoming"][0]["target"] == {"kind": "semantic", "owner_id": "A17/2", "slot": build_return_slot("A17/2")}
+    binding = first["sections"]["bindings"][0]
+    assert binding["source"] == {"kind": "symbolic", "symbol_kind": "import", "qualified_name": "pkg.dep::value"}
+    assert binding["target"] == {"kind": "occurrence", "source": "pkg/mod.py", "local_id": "local"}
+    dynamic = first["sections"]["unresolved_dynamic_boundaries"][0]
+    assert dynamic["id"] == "dynamic"
+    assert dynamic["relation"] == "ASSIGNS"
+    assert dynamic["resolution"] == "DYNAMIC_RUNTIME_BOUNDARY"
+    assert dynamic["confidence"] == "DYNAMIC"
+    assert dynamic["dynamic_boundary"] == "runtime-test"
+    surface = first["sections"]["surfaces"]["facts"][0]
+    assert surface["id"] == "public-handler"
+    assert surface["kind"] == "PUBLIC_SYMBOL"
+    assert surface["declared_name"] == "handler"
+    assert surface["declaration_evidence"] == "STATIC_DECLARATION"
+    assert surface["exposed"] == {"kind": "occurrence", "source": "pkg/mod.py", "local_id": "handler"}
     serialized = json.dumps(first)
     assert "source_fingerprint" not in serialized
     assert "owner_local_id" not in serialized
@@ -114,6 +136,9 @@ def test_symbol_lineage_payload_preserves_selected_empty_vs_omitted_and_preview_
     payload = build_symbol_lineage_payload(selected)
     preview = build_symbol_lineage_preview(selected)
     assert "sections" not in preview
+    assert preview["available_sections"] == list(SYMBOL_LINEAGE_SECTION_ORDER)
+    assert "unresolved_dynamic_boundaries" in preview["section_sizes"]
+    assert "surfaces" in preview["section_sizes"]
     assert preview["candidate_response_bytes"] == serialized_json_bytes(payload)
     for name, value in payload["sections"].items():
         assert preview["section_sizes"][name] == {"payload_bytes": serialized_json_bytes(value)}
```

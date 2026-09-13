import json
from dataclasses import replace

import pytest

from contextor.core.domain.lineage_facts import (
    ExtractedSymbolicKind, LineageConfidence, LineageRelation, MaterializedAnchorFact,
    MaterializedFlowFact, MaterializedOccurrenceRef, MaterializedSymbolicRef,
    MaterializedSurfaceFact, ResolutionKind,
    SemanticAnchorBinding, SemanticEndpoint, SemanticInterfaceDescriptor,
    SourceSpan, SurfaceDeclarationEvidence, SurfaceKind,
    build_parameter_value_slot, build_return_slot, ParameterKind,
)
from contextor.core.lineage_query.backend import LineageBackendMetadata
from contextor.core.lineage_query.service import (
    SYMBOL_LINEAGE_SECTION_ORDER, DirectLineageFacts, LexicalScopeFacts,
    LineageAnchorMatch, LineageFlowMatch, LineageInterfaceDescriptorMatch, LineageSurfaceMatch,
    LineageScopeRootMatch, LineageSurfaceSection, ResolvedLineageTarget,
    SelectedSymbolLineageFacts, SemanticLineageSections, SymbolLineageConnections,
    SymbolLineageFacts, TargetInterfaceFacts,
)
from contextor.mcp.representation import serialized_json_bytes
from contextor.mcp.lineage_response import (
    SymbolLineageResponsePlan,
    build_symbol_lineage_payload,
    build_symbol_lineage_preview,
    plan_symbol_lineage_response,
)


def _selected_lineage_fixture():
    target = ResolvedLineageTarget("A17/2", "pkg.mod::handler", "pkg.mod", "handler", "exact_id")
    metadata = LineageBackendMetadata(7, "live", "fresh", "1", 1, "fresh", True)
    span = SourceSpan(1, 0, 1, 8)
    ref = MaterializedOccurrenceRef("pkg/mod.py", "1" * 64, "handler")
    binding = SemanticAnchorBinding("A17/2", "pkg.mod::handler", ref)
    anchor = MaterializedAnchorFact("handler", ref, "function", span)
    definition = LineageAnchorMatch("pkg/mod.py", "1" * 64, binding)
    parameter_slot = build_parameter_value_slot("A17/2", ParameterKind.POSITIONAL_OR_KEYWORD, ordinal=0, name="ignored")
    descriptor = SemanticInterfaceDescriptor("A17/2", tuple(sorted((build_return_slot("A17/2"), parameter_slot))), "digest")
    default = LineageFlowMatch("pkg/mod.py", "1" * 64, MaterializedFlowFact("default", MaterializedOccurrenceRef("pkg/mod.py", "1" * 64, "value"), SemanticEndpoint("A17/2", parameter_slot), LineageRelation.DEFAULTS_TO_PARAMETER, span, ResolutionKind.SIGNATURE_EXACT, LineageConfidence.CONFIRMED))
    interface = TargetInterfaceFacts(target, metadata, (definition,), (LineageInterfaceDescriptorMatch("pkg/mod.py", "1" * 64, descriptor),), (default,), True)
    incoming = LineageFlowMatch("pkg/mod.py", "1" * 64, MaterializedFlowFact("incoming", MaterializedOccurrenceRef("pkg/mod.py", "1" * 64, "caller"), SemanticEndpoint("A17/2", build_return_slot("A17/2")), LineageRelation.CALL_RESULT, span, ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED))
    symbolic_ref = MaterializedSymbolicRef("pkg/mod.py", "1" * 64, ExtractedSymbolicKind.IMPORT, "pkg.dep", "value")
    local_ref = MaterializedOccurrenceRef("pkg/mod.py", "1" * 64, "local")
    binding_flow = LineageFlowMatch("pkg/mod.py", "1" * 64, MaterializedFlowFact("binding", symbolic_ref, local_ref, LineageRelation.BINDS, span, ResolutionKind.IMPORT_EXACT, LineageConfidence.CONFIRMED))
    dynamic_flow = LineageFlowMatch("pkg/mod.py", "1" * 64, MaterializedFlowFact("dynamic", local_ref, ref, LineageRelation.ASSIGNS, span, ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, dynamic_boundary="runtime-test"))
    surface_match = LineageSurfaceMatch("pkg/mod.py", "1" * 64, MaterializedSurfaceFact("public-handler", SurfaceKind.PUBLIC_SYMBOL, ref, span, ResolutionKind.PYTHON_NAME_CONVENTION, LineageConfidence.INFERRED, "handler", declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION))
    direct = DirectLineageFacts(target, metadata, (definition,), (incoming,), (), (surface_match,))
    root = LineageScopeRootMatch("pkg/mod.py", "1" * 64, binding, anchor)
    scope = LexicalScopeFacts(target, metadata, (root,), (binding_flow, dynamic_flow), (), True)
    sections = SemanticLineageSections(target, scope, direct, (binding_flow, dynamic_flow), (), (), (), (), (), LineageSurfaceSection((), (surface_match,)), (dynamic_flow,))
    facts = SymbolLineageFacts(target, interface, sections)
    return SelectedSymbolLineageFacts(facts, SYMBOL_LINEAGE_SECTION_ORDER, interface, SymbolLineageConnections((incoming,), ()), (binding_flow, dynamic_flow), (), (), (), (), (), LineageSurfaceSection((), (surface_match,)), (dynamic_flow,))


def test_auto_plans_complete_symbol_candidate_for_size_decision():
    assert plan_symbol_lineage_response(mode=" AUTO ") == SymbolLineageResponsePlan("auto", SYMBOL_LINEAGE_SECTION_ORDER, True, True)


def test_preview_plans_all_sections_without_payload():
    assert plan_symbol_lineage_response(mode="preview") == SymbolLineageResponsePlan("preview", SYMBOL_LINEAGE_SECTION_ORDER, False, False)


def test_fetch_requires_explicit_sections_and_canonicalizes_order():
    assert plan_symbol_lineage_response(mode="fetch", sections=("state", "interface", "connections")) == SymbolLineageResponsePlan("fetch", ("interface", "connections", "state"), True, False)


@pytest.mark.parametrize("mode", ("auto", "preview"))
def test_auto_and_preview_reject_explicit_sections(mode):
    with pytest.raises(ValueError, match=f"{mode} mode does not accept an explicit section selection."):
        plan_symbol_lineage_response(mode=mode, sections=("interface",))


@pytest.mark.parametrize("sections", (None, ()))
def test_fetch_requires_non_empty_selection(sections):
    with pytest.raises(ValueError, match="fetch mode requires at least one section."):
        plan_symbol_lineage_response(mode="fetch", sections=sections)


def test_response_plan_rejects_invalid_contract():
    with pytest.raises(TypeError, match="mode must be a string."):
        plan_symbol_lineage_response(mode=object())
    with pytest.raises(ValueError, match="mode must be 'auto', 'preview', or 'fetch'."):
        plan_symbol_lineage_response(mode="other")
    with pytest.raises(TypeError, match="sections must be a tuple of section names."):
        plan_symbol_lineage_response(mode="fetch", sections=["interface"])
    with pytest.raises(ValueError, match="sections must contain non-empty strings."):
        plan_symbol_lineage_response(mode="fetch", sections=("",))
    with pytest.raises(ValueError, match="sections must not contain duplicates."):
        plan_symbol_lineage_response(mode="fetch", sections=("state", "state"))
    with pytest.raises(ValueError, match="Unknown symbol lineage sections: mystery"):
        plan_symbol_lineage_response(mode="fetch", sections=("mystery",))


def test_symbol_lineage_payload_rejects_non_selected_type():
    with pytest.raises(
        TypeError,
        match="selected must be SelectedSymbolLineageFacts.",
    ):
        build_symbol_lineage_payload(object())


def test_symbol_lineage_payload_is_deterministic_json_safe_and_semantic():
    selected = _selected_lineage_fixture()
    first, second = build_symbol_lineage_payload(selected), build_symbol_lineage_payload(selected)
    assert first == second
    assert json.dumps(first, indent=2, ensure_ascii=False) == json.dumps(second, indent=2, ensure_ascii=False)
    assert first["target"]["artifact_id"] == "A17/2"
    assert first["sections"]["interface"]["parameters"][0]["name"] is None
    assert first["sections"]["connections"]["incoming"][0]["target"] == {"kind": "semantic", "owner_id": "A17/2", "slot": build_return_slot("A17/2")}
    binding = first["sections"]["bindings"][0]
    assert binding["source"] == {"kind": "symbolic", "symbol_kind": "import", "qualified_name": "pkg.dep::value"}
    assert binding["target"] == {"kind": "occurrence", "source": "pkg/mod.py", "local_id": "local"}
    dynamic = first["sections"]["unresolved_dynamic_boundaries"][0]
    assert dynamic["id"] == "dynamic"
    assert dynamic["relation"] == "ASSIGNS"
    assert dynamic["resolution"] == "DYNAMIC_RUNTIME_BOUNDARY"
    assert dynamic["confidence"] == "DYNAMIC"
    assert dynamic["dynamic_boundary"] == "runtime-test"
    surface = first["sections"]["surfaces"]["facts"][0]
    assert surface["id"] == "public-handler"
    assert surface["kind"] == "PUBLIC_SYMBOL"
    assert surface["declared_name"] == "handler"
    assert surface["declaration_evidence"] == "STATIC_DECLARATION"
    assert surface["exposed"] == {"kind": "occurrence", "source": "pkg/mod.py", "local_id": "handler"}
    serialized = json.dumps(first)
    assert "source_fingerprint" not in serialized
    assert "owner_local_id" not in serialized


def test_symbol_lineage_payload_preserves_selected_empty_vs_omitted_and_preview_sizes():
    selected = _selected_lineage_fixture()
    reduced = replace(selected, selected_sections=("callbacks",), interface=None, connections=None, bindings=None, parameter_flows=None, calls_interfaces=None, returns=None, state=None, callbacks=(), surfaces=None, unresolved_dynamic_boundaries=None)
    assert build_symbol_lineage_payload(reduced)["sections"] == {"callbacks": []}
    payload = build_symbol_lineage_payload(selected)
    preview = build_symbol_lineage_preview(selected)
    assert "sections" not in preview
    assert preview["available_sections"] == list(SYMBOL_LINEAGE_SECTION_ORDER)
    assert "unresolved_dynamic_boundaries" in preview["section_sizes"]
    assert "surfaces" in preview["section_sizes"]
    assert preview["candidate_response_bytes"] == serialized_json_bytes(payload)
    for name, value in payload["sections"].items():
        assert preview["section_sizes"][name] == {"payload_bytes": serialized_json_bytes(value)}

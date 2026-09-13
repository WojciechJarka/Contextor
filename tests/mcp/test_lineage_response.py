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
from contextor.mcp import representation as mcp_rep
from contextor.mcp.lineage_response import (
    SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES,
    SymbolLineageResponsePlan,
    build_symbol_lineage_payload,
    build_symbol_lineage_preview,
    build_symbol_lineage_represented_payload,
    build_symbol_lineage_represented_preview,
    plan_symbol_lineage_response,
    render_symbol_lineage_response,
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


def _with_repeated_connections(
    selected,
    count,
):
    template = selected.connections.incoming[0]
    repeated = tuple(
        replace(
            template,
            flow=replace(
                template.flow,
                local_id=f"incoming-{index:03d}",
            ),
        )
        for index in range(count)
    )
    return replace(
        selected,
        connections=SymbolLineageConnections(
            repeated,
            (),
        ),
    )


def _with_empty_selected_sections(selected):
    return replace(
        selected,
        interface=replace(
            selected.interface,
            definitions=(),
            descriptors=(),
            parameter_defaults=(),
        ),
        connections=SymbolLineageConnections((), ()),
        bindings=(),
        parameter_flows=(),
        calls_interfaces=(),
        returns=(),
        state=(),
        callbacks=(),
        surfaces=LineageSurfaceSection((), ()),
        unresolved_dynamic_boundaries=(),
    )


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
    assert preview["candidate_response_bytes"] == mcp_rep.serialized_json_bytes(payload)
    for name, value in payload["sections"].items():
        assert preview["section_sizes"][name] == {"payload_bytes": mcp_rep.serialized_json_bytes(value)}


def test_symbol_lineage_named_and_indexed_representations_preserve_nonsemantic_identities():
    selected = _selected_lineage_fixture()
    named = build_symbol_lineage_represented_payload(
        selected,
        representation="named",
        artifact_names={
            "A17/2": "pkg.mod::handler",
        },
    )
    indexed = build_symbol_lineage_represented_payload(
        selected,
        representation="indexed",
    )

    named_semantic = named["sections"][
        "connections"
    ]["incoming"][0]["target"]
    indexed_semantic = indexed["sections"][
        "connections"
    ]["incoming"][0]["target"]

    assert named_semantic == {
        "kind": "semantic",
        "owner": "pkg.mod::handler",
        "slot": build_return_slot("A17/2"),
    }
    assert indexed_semantic == {
        "kind": "semantic",
        "owner_id": "A17/2",
        "slot": build_return_slot("A17/2"),
    }

    assert (
        named_semantic["slot"]
        == indexed_semantic["slot"]
        == build_return_slot("A17/2")
    )

    expected_symbolic = {
        "kind": "symbolic",
        "symbol_kind": "import",
        "qualified_name": "pkg.dep::value",
    }
    assert (
        named["sections"]["bindings"][0]["source"]
        == expected_symbolic
    )
    assert (
        indexed["sections"]["bindings"][0]["source"]
        == expected_symbolic
    )

    expected_occurrence = {
        "kind": "occurrence",
        "source": "pkg/mod.py",
        "local_id": "local",
    }
    assert (
        named["sections"]["bindings"][0]["target"]
        == expected_occurrence
    )
    assert (
        indexed["sections"]["bindings"][0]["target"]
        == expected_occurrence
    )

    assert named["target"]["artifact_id"] == "A17/2"
    assert indexed["target"]["artifact_id"] == "A17/2"
    assert (
        named["target"]["qualified_name"]
        == indexed["target"]["qualified_name"]
        == "pkg.mod::handler"
    )

    assert named["representation"] == "named"
    assert (
        named["representation_decision"]["reason"]
        == "explicit_named"
    )
    assert "resolver" not in named

    assert indexed["representation"] == "indexed"
    assert indexed["resolver"] == {
        "index_kind": "artifact",
        "resolve_via": "lookup_index_entries",
    }
    assert (
        indexed["representation_decision"]["reason"]
        == "explicit_indexed"
    )


def test_symbol_lineage_representation_fails_closed_and_auto_falls_back():
    selected = _selected_lineage_fixture()
    with pytest.raises(
        ValueError,
        match=(
            "Named lineage representation unavailable "
            "for semantic owners: A17/2"
        ),
    ):
        build_symbol_lineage_represented_payload(
            selected,
            representation="named",
            artifact_names={},
        )

    result = build_symbol_lineage_represented_payload(
        selected,
        representation="auto",
        artifact_names={},
    )

    assert result["representation"] == "indexed"
    assert (
        result["representation_decision"]["reason"]
        == "auto_indexed_named_identity_unavailable"
    )
    assert result["representation_decision"][
        "missing_named_owners"
    ] == ["A17/2"]
    assert (
        result["representation_decision"][
            "named_candidate_bytes"
        ]
        is None
    )


def test_symbol_lineage_auto_named_and_material_indexed_saving():
    selected = _selected_lineage_fixture()
    named = build_symbol_lineage_represented_payload(
        selected,
        representation="auto",
        artifact_names={
            "A17/2": "pkg.mod::handler",
        },
    )

    named_decision = named["representation_decision"]
    assert named["representation"] == "named"
    assert named_decision["reason"] == "auto_named"
    assert (
        named_decision["bytes_saved_by_indexed"]
        < mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED
    )
    assert (
        named_decision["minimum_auto_saving_bytes"]
        == mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED
    )

    repeated = tuple(
        replace(
            selected.connections.incoming[0],
            flow=replace(
                selected.connections.incoming[0].flow,
                local_id=f"incoming-{index:02d}",
            ),
        )
        for index in range(20)
    )
    expanded = replace(
        selected,
        connections=SymbolLineageConnections(
            repeated,
            (),
        ),
    )
    long_name = (
        "pkg."
        + ("very_long_component." * 8)
        + "handler"
    )

    indexed = build_symbol_lineage_represented_payload(
        expanded,
        representation="auto",
        artifact_names={
            "A17/2": long_name,
        },
    )

    indexed_decision = (
        indexed["representation_decision"]
    )
    assert indexed["representation"] == "indexed"
    assert (
        indexed_decision["reason"]
        == "auto_indexed_material_saving"
    )
    assert (
        indexed_decision["bytes_saved_by_indexed"]
        >= mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED
    )
    assert (
        indexed_decision["named_candidate_bytes"]
        - indexed_decision["indexed_candidate_bytes"]
        == indexed_decision["bytes_saved_by_indexed"]
    )


def test_symbol_lineage_representation_validates_request_contract():
    selected = _selected_lineage_fixture()
    with pytest.raises(TypeError, match="representation must be a string."):
        build_symbol_lineage_represented_payload(selected, representation=object())
    with pytest.raises(ValueError, match="representation must be 'auto', 'indexed', or 'named'."):
        build_symbol_lineage_represented_payload(selected, representation="other")
    with pytest.raises(TypeError, match="artifact_names must be a mapping."):
        build_symbol_lineage_represented_payload(selected, representation="named", artifact_names=[])
    with pytest.raises(
        ValueError,
        match=(
            "artifact_names must map non-empty "
            "artifact IDs to non-empty names."
        ),
    ):
        build_symbol_lineage_represented_payload(
            selected,
            representation="named",
            artifact_names={
                "A17/2": "",
            },
        )


def test_symbol_lineage_auto_returns_full_payload_below_threshold():
    selected = _with_empty_selected_sections(
        _selected_lineage_fixture()
    )

    rendered = render_symbol_lineage_response(
        selected,
        mode="auto",
        representation="indexed",
    )
    result = json.loads(rendered)

    assert result["status"] == "resolved"
    assert result["mode"] == "auto"
    assert result["representation"] == "indexed"
    assert "sections" in result
    assert "auto_fetch" not in result
    assert (
        mcp_rep.serialized_json_bytes(result)
        <= SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES
    )


def test_symbol_lineage_auto_falls_back_to_exact_representation_aware_preview():
    selected = _with_repeated_connections(
        _selected_lineage_fixture(),
        30,
    )

    rendered = render_symbol_lineage_response(
        selected,
        mode="auto",
        representation="indexed",
    )
    result = json.loads(rendered)

    assert result["status"] == "resolved"
    assert result["mode"] == "preview"
    assert result["representation"] == "indexed"
    assert "sections" not in result
    assert result["auto_fetch"]["decision"] == "preview"
    assert result["auto_fetch"]["threshold_bytes"] == (
        SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES
    )
    assert (
        result["auto_fetch"]["candidate_response_bytes"]
        > SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES
    )
    assert (
        result["candidate_response_bytes"]
        == result["auto_fetch"][
            "candidate_response_bytes"
        ]
    )


def test_symbol_lineage_explicit_preview_sizes_exact_represented_fetch_candidate():
    selected = _selected_lineage_fixture()
    names = {
        "A17/2": "pkg.mod::handler",
    }

    preview = build_symbol_lineage_represented_preview(
        selected,
        representation="named",
        artifact_names=names,
        candidate_mode="fetch",
    )
    candidate = build_symbol_lineage_represented_payload(
        selected,
        representation="named",
        artifact_names=names,
    )
    candidate["mode"] = "fetch"

    assert preview["mode"] == "preview"
    assert preview["representation"] == "named"
    assert "sections" not in preview
    assert preview["candidate_response_bytes"] == (
        mcp_rep.serialized_json_bytes(
            candidate
        )
    )
    for name, value in candidate[
        "sections"
    ].items():
        assert preview["section_sizes"][name] == {
            "payload_bytes": (
                mcp_rep.serialized_json_bytes(
                    value
                )
            )
        }


def test_symbol_lineage_fetch_returns_only_explicit_selected_sections():
    selected = _selected_lineage_fixture()
    reduced = replace(
        selected,
        selected_sections=(
            "interface",
            "connections",
        ),
        bindings=None,
        parameter_flows=None,
        calls_interfaces=None,
        returns=None,
        state=None,
        callbacks=None,
        surfaces=None,
        unresolved_dynamic_boundaries=None,
    )

    rendered = render_symbol_lineage_response(
        reduced,
        mode="fetch",
        sections=(
            "connections",
            "interface",
        ),
        representation="indexed",
    )
    result = json.loads(rendered)

    assert result["status"] == "resolved"
    assert result["mode"] == "fetch"
    assert result["selected_sections"] == [
        "interface",
        "connections",
    ]
    assert tuple(result["sections"]) == (
        "interface",
        "connections",
    )


def test_symbol_lineage_renderer_fails_closed_on_selection_plan_mismatch():
    selected = _selected_lineage_fixture()

    with pytest.raises(
        ValueError,
        match=(
            "selected sections do not match "
            "the response plan."
        ),
    ):
        render_symbol_lineage_response(
            selected,
            mode="fetch",
            sections=("interface",),
            representation="indexed",
        )


def test_symbol_lineage_fetch_uses_existing_large_output_guard():
    selected = _with_repeated_connections(
        _selected_lineage_fixture(),
        80,
    )
    reduced = replace(
        selected,
        selected_sections=("connections",),
        interface=None,
        bindings=None,
        parameter_flows=None,
        calls_interfaces=None,
        returns=None,
        state=None,
        callbacks=None,
        surfaces=None,
        unresolved_dynamic_boundaries=None,
    )

    guarded = json.loads(
        render_symbol_lineage_response(
            reduced,
            mode="fetch",
            sections=("connections",),
            representation="indexed",
        )
    )

    assert guarded["status"] == (
        "confirmation_required"
    )
    assert guarded["warning_threshold_bytes"] == (
        15 * 1024
    )
    assert guarded["retry"] == {
        "allow_large_output": True,
    }

    full = json.loads(
        render_symbol_lineage_response(
            reduced,
            mode="fetch",
            sections=("connections",),
            representation="indexed",
            allow_large_output=True,
        )
    )

    assert full["status"] == "resolved"
    assert full["mode"] == "fetch"
    assert "sections" in full
    assert (
        mcp_rep.serialized_json_bytes(full)
        > 15 * 1024
    )


def test_symbol_lineage_auto_progressive_disclosure_precedes_large_output_guard():
    selected = _with_repeated_connections(
        _selected_lineage_fixture(),
        80,
    )

    result = json.loads(
        render_symbol_lineage_response(
            selected,
            mode="auto",
            representation="indexed",
        )
    )

    assert result["status"] == "resolved"
    assert result["mode"] == "preview"
    assert "sections" not in result
    assert result["auto_fetch"]["decision"] == "preview"
    assert result["status"] != (
        "confirmation_required"
    )


def test_symbol_lineage_renderer_validates_allow_large_output():
    with pytest.raises(
        TypeError,
        match=(
            "allow_large_output must be a boolean."
        ),
    ):
        render_symbol_lineage_response(
            _selected_lineage_fixture(),
            allow_large_output=1,
        )

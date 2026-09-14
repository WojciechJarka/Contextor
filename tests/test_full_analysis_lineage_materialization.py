import ast
from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace

import pytest

from contextor.core.api.facade import (
    ContextorFacade,
    _materialize_full_analysis_lineage,
)
from contextor.core.domain.lineage_facts import (
    LINEAGE_FACTS_SEMANTIC_VERSION,
    ExtractedAnchorFact,
    ExtractedFlowFact,
    ExtractedLineageSourceFacts,
    ExtractedOccurrenceRef,
    ExtractedSymbolicKind,
    ExtractedSymbolicRef,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    MaterializedOccurrenceRef,
    MaterializedSurfaceFact,
    MaterializedSymbolicRef,
    ParameterKind,
    ResolutionKind,
    SemanticEndpoint,
    SourceSpan,
    SurfaceDeclarationEvidence,
    SurfaceKind,
    build_keyword_binding_slot,
    build_parameter_value_slot,
    build_positional_binding_slot,
    build_return_slot,
)
from contextor.core.analysis import state_manager
from contextor.core.analysis.lineage_extraction import extract_lineage_source_facts
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.symbol_engine import indexer


class _ReadOnlyRegistry:
    def __init__(self, modules, artifacts):
        self._state = {
            "module_registry": {"path_to_id": modules},
            "artifact_registry": {"path_to_id": artifacts},
        }
        self.read_count = 0

    @contextmanager
    def read_transaction(self):
        self.read_count += 1
        yield

    def get_module_id(self, _name):
        raise AssertionError("lineage materialization must not allocate module identities")

    def get_artifact_id(self, _name):
        raise AssertionError("lineage materialization must not allocate artifact identities")


def _fresh_slice(status=LineageFamilyStatus.FRESH):
    span = SourceSpan(1, 0, 1, 1)
    return ExtractedLineageSourceFacts(
        source_key="pkg.py",
        source_fingerprint="fingerprint",
        anchors=(ExtractedAnchorFact("local", "module", span),),
        flows=(
            ExtractedFlowFact(
                "dynamic",
                ExtractedOccurrenceRef("local"),
                ExtractedSymbolicRef(
                    ExtractedSymbolicKind.CALLEE, "pkg", "dynamic_target"
                ),
                LineageRelation.CALL_RESULT,
                span,
                ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY,
                LineageConfidence.DYNAMIC,
                dynamic_boundary="dynamic_call",
            ),
            ExtractedFlowFact(
                "flow",
                ExtractedOccurrenceRef("local"),
                ExtractedSymbolicRef(
                    ExtractedSymbolicKind.DEFINITION, "pkg", "target"
                ),
                LineageRelation.CALL_RESULT,
                span,
                ResolutionKind.CALL_EXACT,
                LineageConfidence.CONFIRMED,
            ),
        ),
        status=status,
        resource_limit_reason="node_limit" if status is LineageFamilyStatus.RESOURCE_LIMIT else None,
    )


def _owned_fresh_slice(*, fingerprint="fingerprint"):
    span = SourceSpan(1, 0, 1, 1)
    module_anchor = "occ:v1:module:root:i:0:n:pkg"
    return ExtractedLineageSourceFacts(
        source_key="pkg.py",
        source_fingerprint=fingerprint,
        anchors=(ExtractedAnchorFact(module_anchor, "module", span),),
        flows=(
            ExtractedFlowFact(
                "flow",
                ExtractedOccurrenceRef(module_anchor),
                ExtractedSymbolicRef(
                    ExtractedSymbolicKind.DEFINITION, "pkg", "target"
                ),
                LineageRelation.CALL_RESULT,
                span,
                ResolutionKind.CALL_EXACT,
                LineageConfidence.CONFIRMED,
                owner_local_id=module_anchor,
            ),
        ),
    )


def _previous_lineage_state(lineage_facts_by_source):
    return SimpleNamespace(
        resync_required=False,
        lineage_facts_state="fresh",
        lineage_query_index_state="fresh",
        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
        lineage_semantic_anchor_bindings_complete=True,
        lineage_facts_by_source=lineage_facts_by_source,
    )


def _index(*, facts=None, skipped=()):
    return SimpleNamespace(
        modules={"pkg": SimpleNamespace(path="pkg.py")},
        lineage_facts_by_source=facts or {},
        skipped=list(skipped),
    )


def test_full_analysis_materializes_active_ids_once_with_current_manifest_and_no_allocation():
    registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
    index = _index(facts={"pkg.py": _fresh_slice()})
    artifacts = {"pkg": {"own_symbols": ["target"]}}

    first = _materialize_full_analysis_lineage(index, registry, index.modules, artifacts)
    second = _materialize_full_analysis_lineage(index, registry, index.modules, artifacts)

    mapping, family_state, version = first
    assert first == second
    assert registry.read_count == 2
    assert set(mapping) == {"pkg.py"}
    assert family_state == "fresh"
    assert version == LINEAGE_FACTS_SEMANTIC_VERSION
    source_slice = mapping["pkg.py"]
    assert source_slice.manifest.source_key == "pkg.py"
    assert source_slice.manifest.source_fingerprint == "fingerprint"
    assert source_slice.flows[1].target == SemanticEndpoint("A1/1")
    assert isinstance(source_slice.flows[0].target, MaterializedSymbolicRef)


def test_full_analysis_lineage_coverage_states_are_explicit_for_resource_skip_and_empty():
    registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
    artifacts = {"pkg": {"own_symbols": ["target"]}}

    resource = _materialize_full_analysis_lineage(
        _index(facts={"pkg.py": _fresh_slice(LineageFamilyStatus.RESOURCE_LIMIT)}),
        registry,
        _index().modules,
        artifacts,
    )
    deferred = _materialize_full_analysis_lineage(
        _index(skipped=(SimpleNamespace(path="broken.py"),)),
        registry,
        _index().modules,
        artifacts,
    )
    empty_registry = _ReadOnlyRegistry({}, {})
    empty_index = SimpleNamespace(modules={}, lineage_facts_by_source={}, skipped=[])
    empty = _materialize_full_analysis_lineage(empty_index, empty_registry, {}, {})

    assert resource[1:] == ("resource_limit", LINEAGE_FACTS_SEMANTIC_VERSION)
    assert deferred == ({}, "deferred", LINEAGE_FACTS_SEMANTIC_VERSION)
    assert empty == ({}, "fresh", LINEAGE_FACTS_SEMANTIC_VERSION)


def test_real_full_analysis_installs_current_lineage_without_second_extraction(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    (repo / "provider.py").write_text("def target():\n    return 1\n__all__ = [\"target\"]\n", encoding="utf-8")
    (repo / "consumer.py").write_text(
        "from provider import target as exported\n__all__ = [\"exported\"]\nvalue = exported()\n", encoding="utf-8"
    )

    original_extract = indexer.extract_lineage_source_facts
    extracted_source_keys = []

    def counted_extract(tree, *, source_key, source_fingerprint, **kwargs):
        extracted_source_keys.append(source_key)
        return original_extract(
            tree,
            source_key=source_key,
            source_fingerprint=source_fingerprint,
            **kwargs,
        )


    captured_states = []
    original_save_engine_state = state_manager.save_engine_state

    def capture_save_engine_state(state, *args, **kwargs):
        captured_states.append(state)
        return original_save_engine_state(state, *args, **kwargs)

    monkeypatch.setattr(indexer, "extract_lineage_source_facts", counted_extract)
    monkeypatch.setattr(state_manager, "save_engine_state", capture_save_engine_state)
    errors, _ = ContextorFacade.analyze_project(str(repo))

    assert errors == []
    assert sorted(extracted_source_keys) == ["consumer.py", "provider.py"]
    assert len(captured_states) == 1
    state = captured_states[0]
    assert state.lineage_facts_state == "fresh"
    assert state.lineage_facts_semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
    assert state.lineage_query_index_state == "fresh"
    assert set(state.lineage_facts_by_source) == {"consumer.py", "provider.py"}
    assert all(
        source_key == source_slice.manifest.source_key
        for source_key, source_slice in state.lineage_facts_by_source.items()
    )
    registry = PersistentIdentityRegistry(str(repo))
    with registry.read_transaction():
        provider_target_id = registry._state["artifact_registry"]["path_to_id"]["provider::target"]
    assert state.lineage_facts_by_source["provider.py"].surfaces[0].exposed == SemanticEndpoint(provider_target_id)
    assert state.lineage_facts_by_source["consumer.py"].surfaces[0].exposed == SemanticEndpoint(provider_target_id)
    assert provider_target_id in state.lineage_owner_source_index
    assert "provider.py" in state.lineage_owner_source_index[provider_target_id]


def test_full_analysis_uses_callable_interface_descriptors_for_exact_slots():
    facts = extract_lineage_source_facts(
        ast.parse("def target(value, *, mode):\n    return value\n"),
        source_key="pkg.py", source_fingerprint="d" * 64,
    )
    index = _index(facts={"pkg.py": facts})
    owner = "A1/1"
    mapping, family_state, version = _materialize_full_analysis_lineage(
        index, _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": owner}),
        index.modules, {"pkg": {"own_symbols": ["target"]}},
    )
    assert family_state == "fresh"
    assert version == LINEAGE_FACTS_SEMANTIC_VERSION
    source_slice = mapping["pkg.py"]
    assert len(source_slice.interface_descriptors) == 1
    assert source_slice.interface_descriptors[0].slots == tuple(sorted({
        build_return_slot(owner),
        build_parameter_value_slot(owner, ParameterKind.POSITIONAL_OR_KEYWORD, ordinal=0),
        build_positional_binding_slot(owner, ParameterKind.POSITIONAL_OR_KEYWORD, ordinal=0),
        build_keyword_binding_slot(owner, ParameterKind.POSITIONAL_OR_KEYWORD, name="value"),
        build_parameter_value_slot(owner, ParameterKind.KEYWORD_ONLY, name="mode"),
        build_keyword_binding_slot(owner, ParameterKind.KEYWORD_ONLY, name="mode"),
    }))
    assert sum(
        flow.relation is LineageRelation.BINDS and isinstance(flow.source, SemanticEndpoint)
        for flow in source_slice.flows
    ) == 2
    assert sum(
        flow.relation is LineageRelation.RETURNS and isinstance(flow.target, SemanticEndpoint)
        and flow.target.slot == build_return_slot(owner)
        for flow in source_slice.flows
    ) == 1


def test_full_analysis_conflicting_callable_descriptor_stays_symbolic():
    facts = extract_lineage_source_facts(
        ast.parse("def target(value):\n    return value\n\ndef target(value, mode):\n    return value\n"),
        source_key="pkg.py", source_fingerprint="e" * 64,
    )
    index = _index(facts={"pkg.py": facts})
    mapping, family_state, _ = _materialize_full_analysis_lineage(
        index, _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"}),
        index.modules, {"pkg": {"own_symbols": ["target"]}},
    )
    assert family_state == "fresh"
    source_slice = mapping["pkg.py"]
    assert source_slice.interface_descriptors == ()
    assert not any(
        isinstance(endpoint, SemanticEndpoint) and endpoint.owner_id == "A1/1"
        and endpoint.slot is not None
        for flow in source_slice.flows for endpoint in (flow.source, flow.target)
    )


def test_exact_surface_materialization_uses_symbolic_targets_and_preserves_external_boundary():
    local_facts = extract_lineage_source_facts(
        ast.parse("def target():\n    return 1\n__all__ = ['target']\n"),
        source_key="pkg.py",
        source_fingerprint="a" * 64,
    )
    local_surface = local_facts.surfaces[0]
    assert isinstance(local_surface.exposed, ExtractedSymbolicRef)
    assert local_surface.exposed.kind is ExtractedSymbolicKind.PUBLIC_TARGET
    assert local_surface.exposed.module_name == "pkg"
    assert local_surface.exposed.symbol_name == "target"
    assert local_surface.exposed.source_local_id is not None

    registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
    local_index = _index(facts={"pkg.py": local_facts})
    local_mapping, local_state, _ = _materialize_full_analysis_lineage(
        local_index, registry, local_index.modules, {"pkg": {"own_symbols": ["target"]}}
    )
    assert local_state == "fresh"
    assert local_mapping["pkg.py"].surfaces[0].exposed == SemanticEndpoint("A1/1")

    external_facts = extract_lineage_source_facts(
        ast.parse("from external import target as alias\n__all__ = ['alias']\n"),
        source_key="pkg.py",
        source_fingerprint="b" * 64,
    )
    external_surface = external_facts.surfaces[0]
    assert external_surface.kind is SurfaceKind.REEXPORT
    assert isinstance(external_surface.exposed, ExtractedSymbolicRef)
    assert (
        external_surface.exposed.module_name,
        external_surface.exposed.symbol_name,
    ) == ("external", "target")
    assert external_surface.exposed.source_local_id is not None

    external_registry = _ReadOnlyRegistry({"pkg": "1/1"}, {})
    external_index = _index(facts={"pkg.py": external_facts})
    external_mapping, external_state, _ = _materialize_full_analysis_lineage(
        external_index, external_registry, external_index.modules, {"pkg": {"own_symbols": []}}
    )
    assert external_state == "fresh"
    materialized_external = external_mapping["pkg.py"].surfaces[0].exposed
    assert isinstance(materialized_external, MaterializedSymbolicRef)
    assert (
        materialized_external.module_name,
        materialized_external.symbol_name,
    ) == ("external", "target")


def test_inferred_public_symbol_is_not_strengthened_by_matching_active_artifact():
    facts = extract_lineage_source_facts(
        ast.parse("def target():\n    return 1\n"),
        source_key="pkg.py",
        source_fingerprint="c" * 64,
    )
    index = _index(facts={"pkg.py": facts})
    mapping, state, _ = _materialize_full_analysis_lineage(
        index,
        _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"}),
        index.modules,
        {"pkg": {"own_symbols": ["target"]}},
    )
    assert state == "fresh"
    assert isinstance(mapping["pkg.py"].surfaces[0].exposed, MaterializedOccurrenceRef)


def test_domain_rejects_exact_surface_with_bare_local_occurrence():
    with pytest.raises(ValueError, match="requires SemanticEndpoint or exact symbolic boundary"):
        MaterializedSurfaceFact(
            "surface",
            SurfaceKind.EXPORT,
            MaterializedOccurrenceRef("pkg.py", "fingerprint", "local"),
            SourceSpan(1, 0, 1, 1),
            ResolutionKind.LITERAL_CONTAINER_EXACT,
            LineageConfidence.CONFIRMED,
            "target",
            declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION,
        )


def test_full_analysis_reuses_exact_previous_lineage_slice_object():
    facts = _owned_fresh_slice()
    index = _index(facts={"pkg.py": facts})
    artifacts = {"pkg": {"own_symbols": ["target"]}}
    registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})

    first_mapping, _, _ = _materialize_full_analysis_lineage(
        index, registry, index.modules, artifacts
    )
    previous = first_mapping["pkg.py"]

    second_mapping, family_state, version = _materialize_full_analysis_lineage(
        index,
        registry,
        index.modules,
        artifacts,
        previous_state=_previous_lineage_state(first_mapping),
    )

    assert family_state == "fresh"
    assert version == LINEAGE_FACTS_SEMANTIC_VERSION
    assert second_mapping["pkg.py"] is previous


def test_full_analysis_materializes_changed_source_fingerprint():
    artifacts = {"pkg": {"own_symbols": ["target"]}}
    registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
    first_index = _index(facts={"pkg.py": _owned_fresh_slice(fingerprint="old")})
    first_mapping, _, _ = _materialize_full_analysis_lineage(
        first_index, registry, first_index.modules, artifacts
    )
    second_index = _index(facts={"pkg.py": _owned_fresh_slice(fingerprint="new")})

    second_mapping, _, _ = _materialize_full_analysis_lineage(
        second_index,
        registry,
        second_index.modules,
        artifacts,
        previous_state=_previous_lineage_state(first_mapping),
    )

    assert second_mapping["pkg.py"] is not first_mapping["pkg.py"]
    assert second_mapping["pkg.py"].manifest.source_fingerprint == "new"


def test_full_analysis_reresolves_changed_global_identity_without_materializing(
    monkeypatch,
):
    from contextor.core.analysis import lineage_materialization

    facts = _owned_fresh_slice()
    index = _index(facts={"pkg.py": facts})
    artifacts = {"pkg": {"own_symbols": ["target"]}}
    first_registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
    first_mapping, _, _ = _materialize_full_analysis_lineage(
        index, first_registry, index.modules, artifacts
    )

    def fail_materialize(*_args, **_kwargs):
        raise AssertionError("global identity change must reresolve, not materialize")

    monkeypatch.setattr(
        lineage_materialization,
        "materialize_lineage_source_facts",
        fail_materialize,
    )
    second_registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/2"})
    second_mapping, _, _ = _materialize_full_analysis_lineage(
        index,
        second_registry,
        index.modules,
        artifacts,
        previous_state=_previous_lineage_state(first_mapping),
    )

    assert second_mapping["pkg.py"] is not first_mapping["pkg.py"]
    assert second_mapping["pkg.py"].flows[0].target == SemanticEndpoint("A1/2")


def test_full_analysis_falls_back_to_materialization_for_missing_origin(monkeypatch):
    from contextor.core.analysis import lineage_materialization

    facts = _owned_fresh_slice()
    index = _index(facts={"pkg.py": facts})
    artifacts = {"pkg": {"own_symbols": ["target"]}}
    registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
    first_mapping, _, _ = _materialize_full_analysis_lineage(
        index, registry, index.modules, artifacts
    )
    previous = first_mapping["pkg.py"]
    legacy_previous = replace(previous, semantic_endpoint_origins=())
    calls = []
    original_materialize = lineage_materialization.materialize_lineage_source_facts

    def counted_materialize(*args, **kwargs):
        calls.append(1)
        return original_materialize(*args, **kwargs)

    monkeypatch.setattr(
        lineage_materialization,
        "materialize_lineage_source_facts",
        counted_materialize,
    )
    second_mapping, _, _ = _materialize_full_analysis_lineage(
        index,
        registry,
        index.modules,
        artifacts,
        previous_state=_previous_lineage_state({"pkg.py": legacy_previous}),
    )

    assert calls == [1]
    assert second_mapping["pkg.py"] is not legacy_previous
    assert second_mapping["pkg.py"].flows[0].target == SemanticEndpoint("A1/1")
    assert second_mapping["pkg.py"].semantic_endpoint_origins


def test_full_analysis_does_not_reuse_previous_fresh_slice_when_current_extraction_is_resource_limited():
    fresh_facts = _owned_fresh_slice()
    fresh_index = _index(facts={"pkg.py": fresh_facts})
    artifacts = {"pkg": {"own_symbols": ["target"]}}
    registry = _ReadOnlyRegistry(
        {"pkg": "1/1"},
        {"pkg::target": "A1/1"},
    )
    first_mapping, _, _ = _materialize_full_analysis_lineage(
        fresh_index,
        registry,
        fresh_index.modules,
        artifacts,
    )
    previous = first_mapping["pkg.py"]

    limited_facts = replace(
        fresh_facts,
        status=LineageFamilyStatus.RESOURCE_LIMIT,
        resource_limit_reason="node_limit",
    )
    limited_index = _index(facts={"pkg.py": limited_facts})

    second_mapping, family_state, version = _materialize_full_analysis_lineage(
        limited_index,
        registry,
        limited_index.modules,
        artifacts,
        previous_state=_previous_lineage_state(first_mapping),
    )

    current = second_mapping["pkg.py"]
    assert current is not previous
    assert current.manifest.status is LineageFamilyStatus.RESOURCE_LIMIT
    assert current.manifest.resource_limit_reason == "node_limit"
    assert family_state == "resource_limit"
    assert version == LINEAGE_FACTS_SEMANTIC_VERSION

from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.core.analysis.incremental.engine import IncrementalAnalysisEngine
from contextor.core.analysis.incremental.plan_executor import _prepare_candidate_state
from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.lineage_facts import (
    LINEAGE_FACTS_SEMANTIC_VERSION,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    MaterializedAnchorFact,
    MaterializedFlowFact,
    MaterializedLineageSourceFacts,
    MaterializedOccurrenceRef,
    MaterializedSurfaceFact,
    ProviderRef,
    ResolutionKind,
    SemanticEndpoint,
    SemanticInterfaceDescriptor,
    SourceLineageManifest,
    SourceSpan,
    SurfaceDeclarationEvidence,
    SurfaceKind,
    build_return_slot,
)
from contextor.core.domain.module import Module
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.live_state.store import load_snapshot, save_snapshot
from contextor.core.paths import repo_cache_dir
from contextor.core.repository_identity import ensure_repository_identity


def _lineage_slice() -> MaterializedLineageSourceFacts:
    span = SourceSpan(1, 0, 1, 4)
    occurrence = MaterializedOccurrenceRef("pkg.py", "fingerprint", "occ")
    slot = build_return_slot("A1")
    semantic = SemanticEndpoint("A1", slot)

    return MaterializedLineageSourceFacts(
        manifest=SourceLineageManifest(
            "pkg.py",
            "fingerprint",
            LINEAGE_FACTS_SEMANTIC_VERSION,
            LineageFamilyStatus.FRESH,
            1,
            1,
            1,
        ),
        anchors=(
            MaterializedAnchorFact(
                "anchor",
                occurrence,
                "assignment",
                span,
            ),
        ),
        flows=(
            MaterializedFlowFact(
                "flow",
                occurrence,
                semantic,
                LineageRelation.RETURNS,
                span,
                ResolutionKind.CALL_EXACT,
                LineageConfidence.CONFIRMED,
            ),
        ),
        surfaces=(
            MaterializedSurfaceFact(
                "surface",
                SurfaceKind.REGISTRATION,
                occurrence,
                span,
                ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY,
                LineageConfidence.DYNAMIC,
                "registered",
                dynamic_boundary="runtime-registration",
                provider=ProviderRef("fixture", "1"),
                declaration_evidence=(
                    SurfaceDeclarationEvidence.STATIC_DECLARATION
                ),
            ),
        ),
        interface_descriptors=(
            SemanticInterfaceDescriptor(
                "A1",
                (slot,),
                "signature-digest",
            ),
        ),
    )


def _persist_corrupted_lineage_slice(
    tmp_path,
    source_slice,
    state_id,
):
    state = RepositoryAnalysisState(
        lineage_facts_by_source={"pkg.py": source_slice},
        lineage_facts_state="fresh",
        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
    )
    save_snapshot(state, tmp_path, state_id)
    return load_snapshot(tmp_path, expected_state_id=state_id)


def test_repository_state_defaults_and_candidate_copy_are_lineage_safe():
    state = RepositoryAnalysisState()

    assert state.lineage_facts_by_source == {}
    assert state.lineage_facts_state == "not_materialized"
    assert state.lineage_facts_semantic_version is None

    source_slice = _lineage_slice()
    state.lineage_facts_by_source = {"pkg.py": source_slice}
    state.lineage_facts_state = "fresh"
    state.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION

    candidate = _prepare_candidate_state(state)

    assert candidate.lineage_facts_by_source == state.lineage_facts_by_source
    assert candidate.lineage_facts_by_source is not state.lineage_facts_by_source
    assert candidate.lineage_facts_by_source["pkg.py"] is source_slice
    assert candidate.lineage_facts_state == "fresh"
    assert candidate.lineage_facts_semantic_version == "1"

    candidate.lineage_facts_by_source.pop("pkg.py")

    assert "pkg.py" in state.lineage_facts_by_source


def test_snapshot_round_trip_preserves_lineage_endpoint_types_and_metadata(
    tmp_path,
):
    source_slice = _lineage_slice()
    state = RepositoryAnalysisState(
        lineage_facts_by_source={"pkg.py": source_slice},
        lineage_facts_state="fresh",
        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
    )

    save_snapshot(state, tmp_path, "lineage")

    loaded, _ = load_snapshot(tmp_path, expected_state_id="lineage")

    assert loaded.lineage_facts_by_source == {"pkg.py": source_slice}
    loaded_slice = loaded.lineage_facts_by_source["pkg.py"]

    assert isinstance(
        loaded_slice.anchors[0].reference,
        MaterializedOccurrenceRef,
    )
    assert isinstance(
        loaded_slice.flows[0].target,
        SemanticEndpoint,
    )
    assert loaded_slice.flows[0].target.slot == build_return_slot("A1")
    assert (
        loaded_slice.surfaces[0].declaration_evidence
        is SurfaceDeclarationEvidence.STATIC_DECLARATION
    )
    assert loaded_slice.surfaces[0].provider == ProviderRef("fixture", "1")
    assert loaded_slice.surfaces[0].dynamic_boundary == "runtime-registration"


@pytest.mark.parametrize(
    ("family_state", "version", "with_slice"),
    [
        ("not_materialized", "1", False),
        ("not_materialized", None, True),
        ("fresh", None, False),
        ("fresh", "999", False),
    ],
)
def test_snapshot_rejects_invalid_lineage_family_state_version_pairs(
    tmp_path,
    family_state,
    version,
    with_slice,
):
    state = RepositoryAnalysisState(
        lineage_facts_by_source=(
            {"pkg.py": _lineage_slice()} if with_slice else {}
        ),
        lineage_facts_state=family_state,
        lineage_facts_semantic_version=version,
    )
    save_snapshot(state, tmp_path, "invalid")

    assert load_snapshot(tmp_path, expected_state_id="invalid") is None


def test_snapshot_rejects_mapping_manifest_key_mismatch(tmp_path):
    state = RepositoryAnalysisState(
        lineage_facts_by_source={"other.py": _lineage_slice()},
        lineage_facts_state="fresh",
        lineage_facts_semantic_version="1",
    )
    save_snapshot(state, tmp_path, "mismatch")

    assert load_snapshot(tmp_path, expected_state_id="mismatch") is None


def test_snapshot_rejects_corrupted_materialized_endpoint(tmp_path):
    source_slice = _lineage_slice()
    flow = source_slice.flows[0]
    object.__setattr__(flow, "source", "not-an-endpoint")

    state = RepositoryAnalysisState(
        lineage_facts_by_source={"pkg.py": source_slice},
        lineage_facts_state="fresh",
        lineage_facts_semantic_version="1",
    )
    save_snapshot(state, tmp_path, "corrupt")

    assert load_snapshot(tmp_path, expected_state_id="corrupt") is None


@pytest.mark.parametrize("invalid_confidence", ["CONFIRMED", "not-a-confidence"])
def test_snapshot_rejects_non_enum_flow_confidence(
    tmp_path,
    invalid_confidence,
):
    source_slice = _lineage_slice()
    flow = source_slice.flows[0]
    object.__setattr__(flow, "confidence", invalid_confidence)

    assert (
        _persist_corrupted_lineage_slice(
            tmp_path,
            source_slice,
            "bad-flow-confidence",
        )
        is None
    )


@pytest.mark.parametrize("invalid_confidence", ["DYNAMIC", "not-a-confidence"])
def test_snapshot_rejects_non_enum_surface_confidence(
    tmp_path,
    invalid_confidence,
):
    source_slice = _lineage_slice()
    surface = source_slice.surfaces[0]
    object.__setattr__(surface, "confidence", invalid_confidence)

    assert (
        _persist_corrupted_lineage_slice(
            tmp_path,
            source_slice,
            "bad-surface-confidence",
        )
        is None
    )


def test_snapshot_rejects_malformed_semantic_slot(tmp_path):
    source_slice = _lineage_slice()
    endpoint = source_slice.flows[0].target
    assert isinstance(endpoint, SemanticEndpoint)
    object.__setattr__(endpoint, "slot", "slot:not-canonical")

    state = RepositoryAnalysisState(
        lineage_facts_by_source={"pkg.py": source_slice},
        lineage_facts_state="fresh",
        lineage_facts_semantic_version="1",
    )
    save_snapshot(state, tmp_path, "bad-slot")

    assert load_snapshot(tmp_path, expected_state_id="bad-slot") is None


def test_real_hydration_normalizes_legacy_lineage_absence_without_source_rebuild(
    tmp_path,
    monkeypatch,
):
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CONTEXTOR_REGISTRY_DIR", str(tmp_path / "registry"))

    identity, _ = ensure_repository_identity(repo)
    cache_dir = repo_cache_dir(repo)

    module = Module(
        module_id="pkg",
        path="pkg.py",
        absolute_path=str(repo / "does-not-exist.py"),
        imports=[],
    )
    state = RepositoryAnalysisState(
        modules={"pkg": module},
        dependency_graph=ProjectGraph(
            hard_edges={"pkg": set()},
            soft_edges={"pkg": set()},
        ),
        module_usages={
            "pkg": ModuleUsageFacts(
                symbol_calls_materialized=True,
                reference_evidence_materialized=True,
            )
        },
        artifact_consumption={},
        artifact_consumption_state="fresh",
        collision_facts={"pkg": []},
        collisions_state="fresh",
    )

    delattr(state, "lineage_facts_by_source")
    delattr(state, "lineage_facts_state")
    delattr(state, "lineage_facts_semantic_version")

    save_snapshot(
        state,
        cache_dir,
        "legacy-lineage",
        repo_id=identity.repo_id,
        root_path=identity.root_path,
    )

    monkeypatch.setattr(
        "contextor.core.live_state.runtime.connect",
        lambda _root: None,
    )

    def forbidden_source_rebuild(*_args, **_kwargs):
        raise AssertionError("hydration attempted source-backed reconstruction")

    monkeypatch.setattr(
        "contextor.core.reference.engine.extract_module_usage_facts",
        forbidden_source_rebuild,
    )
    monkeypatch.setattr(
        "contextor.core.reporting_engine.persistent_registry."
        "PersistentIdentityRegistry.sync_with_workspace",
        forbidden_source_rebuild,
    )

    hydrated = hydrate_repository_engine(repo)

    assert hydrated is not None
    assert hydrated.engine.state.lineage_facts_by_source == {}
    assert hydrated.engine.state.lineage_facts_state == "not_materialized"
    assert hydrated.engine.state.lineage_facts_semantic_version is None


def test_incremental_commit_publishes_lineage_candidate_fields(
    tmp_path,
    monkeypatch,
):
    state = RepositoryAnalysisState()
    source_slice = _lineage_slice()
    candidate = _prepare_candidate_state(state)
    candidate.lineage_facts_by_source = {"pkg.py": source_slice}
    candidate.lineage_facts_state = "fresh"
    candidate.lineage_facts_semantic_version = "1"

    outcome = SimpleNamespace(
        identity_sync_required=False,
        candidate_state=candidate,
        affected_modules=set(),
        blast_radius_complete=True,
        execution_trace={},
        all_modules=set(),
        current_artifacts={},
    )

    monkeypatch.setattr(
        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
        lambda **_kwargs: outcome,
    )

    engine = object.__new__(IncrementalAnalysisEngine)
    engine.state = state
    engine.root_path = Path(tmp_path)
    engine.registry = SimpleNamespace()
    engine.state_manager = SimpleNamespace(
        update_state=lambda _path: None,
    )

    engine._apply_delta_and_commit(
        str(tmp_path / "pkg.py"),
        SimpleNamespace(),
        None,
        SimpleNamespace(),
        [],
        {},
        None,
    )

    assert state.lineage_facts_by_source == {"pkg.py": source_slice}
    assert state.lineage_facts_state == "fresh"
    assert state.lineage_facts_semantic_version == "1"

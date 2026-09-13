import ast
import hashlib
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.core.analysis.incremental.engine import IncrementalAnalysisEngine
from contextor.core.analysis.incremental.plan_executor import _prepare_candidate_state
from contextor.core.api.facade import _materialize_full_analysis_lineage
from contextor.core.analysis.lineage_extraction import extract_lineage_source_facts
from contextor.core.analysis.lineage_materialization import (
    LineageResolutionContext,
    materialize_lineage_source_facts,
    reresolve_materialized_lineage_source_facts,
)
from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.lineage_facts import (
    ExtractedSymbolicKind,
    LINEAGE_FACTS_SEMANTIC_VERSION,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    MaterializedAnchorFact,
    MaterializedFlowFact,
    MaterializedLineageSourceFacts,
    MaterializedOccurrenceRef,
    MaterializedSymbolicRef,
    MaterializedSurfaceFact,
    ProviderRef,
    ResolutionKind,
    SemanticAnchorBinding,
    SemanticEndpoint,
    SemanticEndpointRole,
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
            semantic_anchor_bindings_materialized=True,
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
        semantic_anchors=(
            SemanticAnchorBinding("A1", "pkg::thing", occurrence),
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
    object.__delattr__(state, "lineage_owner_source_index")
    object.__delattr__(state, "lineage_source_owner_index")
    object.__delattr__(state, "lineage_query_index_state")
    object.__delattr__(state, "lineage_semantic_anchor_bindings_complete")
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
    assert loaded_slice.semantic_anchors == source_slice.semantic_anchors
    assert loaded.lineage_query_index_state == "fresh"
    assert loaded.lineage_owner_source_index


def test_snapshot_legacy_semantic_anchor_fields_fail_closed(tmp_path):
    source_slice = _lineage_slice()
    object.__delattr__(
        source_slice.manifest,
        "semantic_anchor_bindings_materialized",
    )
    object.__delattr__(source_slice, "semantic_anchors")
    state = RepositoryAnalysisState(
        lineage_facts_by_source={"pkg.py": source_slice},
        lineage_facts_state="fresh",
        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
    )

    save_snapshot(state, tmp_path, "legacy-semantic-anchors")

    loaded, _ = load_snapshot(
        tmp_path,
        expected_state_id="legacy-semantic-anchors",
    )
    loaded_slice = loaded.lineage_facts_by_source["pkg.py"]

    assert loaded_slice.manifest.semantic_anchor_bindings_materialized is False
    assert loaded_slice.semantic_anchors == ()
    assert loaded.lineage_query_index_state == "fresh"


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


class _LineageRegistry:
    def __init__(self, module_ids=None, artifact_ids=None):
        self._persisted = {
            "module_registry": {"path_to_id": dict(module_ids or {})},
            "artifact_registry": {"path_to_id": dict(artifact_ids or {})},
        }
        self._state = deepcopy(self._persisted)

    @contextmanager
    def transaction(self):
        self._state = deepcopy(self._persisted)
        try:
            yield
        except Exception:
            raise
        else:
            self._persisted = deepcopy(self._state)

    @contextmanager
    def read_transaction(self):
        self._state = deepcopy(self._persisted)
        yield

    def sync_with_workspace(self, modules, artifacts):
        module_paths = self._state["module_registry"]["path_to_id"]
        artifact_paths = self._state["artifact_registry"]["path_to_id"]
        for name in sorted(modules):
            module_paths.setdefault(name, f"M:{name}")
        for name in sorted(artifacts):
            artifact_paths.setdefault(name, f"A:{name}")


class _LifecycleRegistry(_LineageRegistry):
    """Small transactional registry model with explicit active generations."""

    def __init__(self, module_ids, artifact_ids):
        super().__init__(module_ids, artifact_ids)
        self._ids_by_name = {
            **dict(module_ids),
            **dict(artifact_ids),
        }

    def sync_with_workspace(self, modules, artifacts):
        self._state["module_registry"]["path_to_id"] = {
            name: self._ids_by_name[name]
            for name in sorted(modules)
            if name in self._ids_by_name
        }
        self._state["module_registry"]["id_to_path"] = {
            owner_id: name
            for name, owner_id in self._state["module_registry"]["path_to_id"].items()
        }
        self._state["artifact_registry"]["path_to_id"] = {
            name: self._ids_by_name[name]
            for name in sorted(artifacts)
            if name in self._ids_by_name
        }
        self._state["artifact_registry"]["id_to_path"] = {
            owner_id: name
            for name, owner_id in self._state["artifact_registry"]["path_to_id"].items()
        }


def _cross_source_facts():
    provider_source = "def target():\n    return 1\n__all__ = ['target']\n"
    consumer_source = (
        "from provider import target as exported\n"
        "__all__ = ['exported']\n"
        "value = exported()\n"
    )
    return {
        "provider.py": _extracted("provider.py", provider_source),
        "consumer.py": _extracted("consumer.py", consumer_source),
    }


def _lineage_state_for_facts(facts, registry, modules, artifacts):
    index = SimpleNamespace(
        modules=modules,
        lineage_facts_by_source=facts,
        skipped=[],
    )
    materialized, family_state, semantic_version = _materialize_full_analysis_lineage(
        index, registry, modules, artifacts
    )
    return RepositoryAnalysisState(
        modules=modules,
        artifacts=artifacts,
        lineage_facts_by_source=materialized,
        lineage_facts_state=family_state,
        lineage_facts_semantic_version=semantic_version,
    )


def _module(name: str) -> Module:
    return Module(
        module_id=name,
        path=f"{name}.py",
        absolute_path=f"/{name}.py",
        imports=[],
    )


def _extracted(source_key: str, source: str = "value = 1\n"):
    return extract_lineage_source_facts(
        ast.parse(source),
        source_key=source_key,
        source_fingerprint=hashlib.sha256(source.encode("utf-8")).hexdigest(),
    )


def _lineage_engine(state, registry, tmp_path):
    acknowledged = []
    engine = object.__new__(IncrementalAnalysisEngine)
    engine.state = state
    engine.registry = registry
    engine.root_path = Path(tmp_path)
    engine.state_manager = SimpleNamespace(update_state=acknowledged.append)
    return engine, acknowledged


def _slice_for(source_key: str) -> MaterializedLineageSourceFacts:
    return materialize_lineage_source_facts(
        _extracted(source_key),
        LineageResolutionContext({}, {}, frozenset(), {}),
    )


def test_identity_sync_legacy_semantic_without_origin_fails_closed_to_stale(tmp_path):
    legacy = _lineage_slice()
    other = _slice_for("other.py")
    state = RepositoryAnalysisState(
        modules={"pkg": _module("pkg"), "other": _module("other")},
        artifacts={"pkg": {"own_symbols": set()}, "other": {"own_symbols": set()}},
        lineage_facts_by_source={"pkg.py": legacy, "other.py": other},
        lineage_facts_state="fresh",
        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
    )
    engine, _ = _lineage_engine(
        state,
        _LineageRegistry({"pkg": "M:pkg", "other": "M:other"}),
        tmp_path,
    )
    candidate = _prepare_candidate_state(state)

    with engine.registry.read_transaction():
        engine._update_candidate_lineage_slice(
            candidate,
            source_path="other.py",
            extracted_lineage_facts=_extracted("other.py"),
            rematerialize_all=True,
        )

    assert candidate.lineage_facts_state == LineageFamilyStatus.STALE.value
    assert candidate.lineage_facts_by_source["pkg.py"] is legacy


def test_snapshot_round_trip_compact_origin_reresolves_without_source_work(tmp_path):
    facts = _cross_source_facts()
    modules = {name: _module(name) for name in ("provider", "consumer")}
    artifacts = {
        "provider": {"own_symbols": {"target"}},
        "consumer": {"own_symbols": set()},
    }
    registry = _LifecycleRegistry(
        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
        {"provider::target": "A:provider/1"},
    )
    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
    save_snapshot(state, tmp_path, "compact-origin")
    loaded, _ = load_snapshot(tmp_path, expected_state_id="compact-origin")
    consumer = loaded.lineage_facts_by_source["consumer.py"]
    assert consumer.semantic_endpoint_origins

    removed = reresolve_materialized_lineage_source_facts(
        consumer,
        LineageResolutionContext(
            {"consumer": "M:consumer/1"}, {}, frozenset({"M:consumer/1"}), {}
        ),
    )
    assert isinstance(removed.surfaces[0].exposed, MaterializedSymbolicRef)
    restored = reresolve_materialized_lineage_source_facts(
        removed,
        LineageResolutionContext(
            {"consumer": "M:consumer/1"},
            {"provider::target": "A:provider/2"},
            frozenset({"M:consumer/1", "A:provider/2"}),
            {},
        ),
    )
    assert restored.surfaces[0].exposed == SemanticEndpoint("A:provider/2")


@pytest.mark.parametrize(
    "origins",
    [
        lambda origin: (origin, replace(origin, symbol_name="different")),
        lambda origin: (replace(origin, source_key="other.py"),),
        lambda origin: (replace(origin, source_fingerprint="other"),),
        lambda origin: (replace(origin, fact_local_id="missing"),),
        lambda origin: (replace(origin, endpoint_role=SemanticEndpointRole.FLOW_SOURCE),),
    ],
)
def test_snapshot_rejects_corrupt_compact_origin(tmp_path, origins):
    facts = _cross_source_facts()
    modules = {name: _module(name) for name in ("provider", "consumer")}
    artifacts = {
        "provider": {"own_symbols": {"target"}},
        "consumer": {"own_symbols": set()},
    }
    registry = _LifecycleRegistry(
        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
        {"provider::target": "A:provider/1"},
    )
    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
    source_slice = state.lineage_facts_by_source["consumer.py"]
    origin = source_slice.semantic_endpoint_origins[0]
    object.__setattr__(source_slice, "semantic_endpoint_origins", origins(origin))
    save_snapshot(state, tmp_path, "corrupt-origin")

    assert load_snapshot(tmp_path, expected_state_id="corrupt-origin") is None


def test_incremental_lineage_modify_replaces_only_changed_candidate_slice(tmp_path):
    old_pkg = _slice_for("pkg.py")
    other = _slice_for("other.py")
    state = RepositoryAnalysisState(
        modules={"pkg": _module("pkg"), "other": _module("other")},
        artifacts={"pkg": {"own_symbols": set()}, "other": {"own_symbols": set()}},
        lineage_facts_by_source={"pkg.py": old_pkg, "other.py": other},
        lineage_facts_state="fresh",
        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
    )
    engine, _ = _lineage_engine(
        state,
        _LineageRegistry({"pkg": "M:pkg", "other": "M:other"}),
        tmp_path,
    )
    candidate = _prepare_candidate_state(state)

    with engine.registry.read_transaction():
        engine._update_candidate_lineage_slice(
            candidate,
            source_path="pkg.py",
            extracted_lineage_facts=_extracted("pkg.py", "changed = 2\n"),
        )

    assert candidate.lineage_facts_by_source["pkg.py"] is not old_pkg
    assert candidate.lineage_facts_by_source["other.py"] is other
    assert candidate.lineage_facts_state == "fresh"
    assert candidate.lineage_facts_semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
    assert candidate.lineage_query_index_state == "fresh"
    assert "pkg.py" in candidate.lineage_source_owner_index


def test_incremental_lineage_delete_removes_only_deleted_slice(tmp_path):
    pkg = _slice_for("pkg.py")
    other = _slice_for("other.py")
    state = RepositoryAnalysisState(
        modules={"other": _module("other")},
        artifacts={"other": {"own_symbols": set()}},
        lineage_facts_by_source={"pkg.py": pkg, "other.py": other},
        lineage_facts_state="fresh",
        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
    )
    engine, _ = _lineage_engine(
        state,
        _LineageRegistry({"other": "M:other"}),
        tmp_path,
    )
    candidate = _prepare_candidate_state(state)

    with engine.registry.read_transaction():
        engine._update_candidate_lineage_slice(
            candidate,
            source_path="pkg.py",
            delete=True,
        )

    assert candidate.lineage_facts_by_source == {"other.py": other}
    assert candidate.lineage_facts_state == "fresh"
    assert candidate.lineage_query_index_state == "fresh"
    assert "pkg.py" not in candidate.lineage_source_owner_index


def test_lineage_only_noop_commit_replaces_slice_and_parse_error_invalidates_it(tmp_path):
    old_pkg = _slice_for("pkg.py")
    other = _slice_for("other.py")
    state = RepositoryAnalysisState(
        modules={"pkg": _module("pkg"), "other": _module("other")},
        artifacts={"pkg": {"own_symbols": set()}, "other": {"own_symbols": set()}},
        lineage_facts_by_source={"pkg.py": old_pkg, "other.py": other},
        lineage_facts_state="fresh",
        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
    )
    engine, acknowledged = _lineage_engine(
        state,
        _LineageRegistry({"pkg": "M:pkg", "other": "M:other"}),
        tmp_path,
    )

    engine._commit_syntax_candidate(
        source_path="pkg.py",
        syntax_fact={"status": "checked_and_none", "errors": []},
        extracted_lineage_facts=_extracted("pkg.py", "lineage_only = 3\n"),
    )
    assert state.lineage_facts_by_source["pkg.py"] is not old_pkg
    assert state.lineage_facts_by_source["other.py"] is other
    assert state.lineage_facts_state == "fresh"
    assert acknowledged == []

    engine._commit_syntax_candidate(
        source_path="pkg.py",
        mark_parse_error=("broken", 1, 1),
        clear_parse_module="pkg",
        invalidate_lineage=True,
    )
    assert "pkg.py" not in state.lineage_facts_by_source
    assert state.lineage_facts_by_source["other.py"] is other
    assert state.lineage_facts_state == "stale"
    assert state.lineage_facts_semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
    assert state.lineage_query_index_state == "fresh"
    assert "pkg.py" not in state.lineage_source_owner_index

    engine._commit_syntax_candidate(
        source_path="pkg.py",
        syntax_fact={"status": "checked_and_none", "errors": []},
        extracted_lineage_facts=_extracted("pkg.py", "recovered = 4\n"),
    )
    assert state.lineage_facts_state == "fresh"
    assert set(state.lineage_facts_by_source) == {"pkg.py", "other.py"}


def test_parse_error_keeps_unmaterialized_lineage_unmaterialized(tmp_path):
    state = RepositoryAnalysisState()
    engine, _ = _lineage_engine(state, _LineageRegistry(), tmp_path)

    engine._commit_syntax_candidate(
        source_path="pkg.py",
        mark_parse_error=("broken", 1, 1),
        clear_parse_module="pkg",
        invalidate_lineage=True,
    )

    assert state.lineage_facts_by_source == {}
    assert state.lineage_facts_state == LineageFamilyStatus.NOT_MATERIALIZED.value
    assert state.lineage_facts_semantic_version is None


def test_incremental_lineage_resource_limit_and_source_key_mismatch_fail_closed(tmp_path):
    state = RepositoryAnalysisState(
        modules={"pkg": _module("pkg")},
        artifacts={"pkg": {"own_symbols": set()}},
    )
    engine, _ = _lineage_engine(
        state,
        _LineageRegistry({"pkg": "M:pkg"}),
        tmp_path,
    )
    limited = replace(
        _extracted("pkg.py"),
        status=LineageFamilyStatus.RESOURCE_LIMIT,
        resource_limit_reason="limit",
    )
    candidate = _prepare_candidate_state(state)
    with engine.registry.read_transaction():
        engine._update_candidate_lineage_slice(
            candidate,
            source_path="pkg.py",
            extracted_lineage_facts=limited,
        )
    assert candidate.lineage_facts_state == "resource_limit"

    before = dict(candidate.lineage_facts_by_source)
    with engine.registry.read_transaction(), pytest.raises(ValueError, match="source key"):
        engine._update_candidate_lineage_slice(
            candidate,
            source_path="pkg.py",
            extracted_lineage_facts=_extracted("wrong.py"),
        )
    assert candidate.lineage_facts_by_source == before


def test_incremental_lineage_missing_identity_and_manifest_mismatch_fail_closed(
    tmp_path,
    monkeypatch,
):
    state = RepositoryAnalysisState(
        modules={"pkg": _module("pkg")},
        artifacts={"pkg": {"own_symbols": set()}},
    )
    engine, _ = _lineage_engine(state, _LineageRegistry(), tmp_path)
    candidate = _prepare_candidate_state(state)
    engine.registry.get_module_id = lambda *_args: (_ for _ in ()).throw(
        AssertionError("lineage must not allocate module identities")
    )
    engine.registry.get_artifact_id = lambda *_args: (_ for _ in ()).throw(
        AssertionError("lineage must not allocate artifact identities")
    )
    with engine.registry.read_transaction(), pytest.raises(ValueError, match="missing active"):
        engine._update_candidate_lineage_slice(
            candidate,
            source_path="pkg.py",
            extracted_lineage_facts=_extracted("pkg.py"),
        )
    assert candidate.lineage_facts_by_source == {}

    engine.registry = _LineageRegistry({"pkg": "M:pkg"})
    mismatched = materialize_lineage_source_facts(
        _extracted("pkg.py", "different = 2\n"),
        LineageResolutionContext({"pkg": "M:pkg"}, {}, frozenset({"M:pkg"}), {}),
    )
    monkeypatch.setattr(
        "contextor.core.analysis.lineage_materialization.materialize_lineage_source_facts",
        lambda *_args: mismatched,
    )
    with engine.registry.read_transaction(), pytest.raises(ValueError, match="manifest"):
        engine._update_candidate_lineage_slice(
            candidate,
            source_path="pkg.py",
            extracted_lineage_facts=_extracted("pkg.py"),
        )
    assert candidate.lineage_facts_by_source == {}


def test_identity_sync_materializes_against_new_ids_and_rolls_back_on_failure(
    tmp_path,
    monkeypatch,
):
    state = RepositoryAnalysisState()
    candidate = _prepare_candidate_state(state)
    candidate.modules = {"pkg": _module("pkg")}
    candidate.artifacts = {"pkg": {"own_symbols": {"target"}}}
    outcome = SimpleNamespace(
        identity_sync_required=True,
        candidate_state=candidate,
        affected_modules=set(),
        blast_radius_complete=True,
        execution_trace={},
        all_modules={"pkg"},
        current_artifacts={"pkg::target"},
    )
    monkeypatch.setattr(
        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
        lambda **_kwargs: outcome,
    )
    registry = _LineageRegistry()
    engine, acknowledged = _lineage_engine(state, registry, tmp_path)
    extracted = _extracted(
        "pkg.py",
        "def target():\n    return 1\n__all__ = ['target']\n",
    )

    engine._apply_delta_and_commit(
        str(tmp_path / "pkg.py"),
        SimpleNamespace(is_deleted=False),
        None,
        SimpleNamespace(),
        [],
        {},
        None,
        extracted_lineage_facts=extracted,
        syntax_source_path="pkg.py",
    )
    assert state.lineage_facts_state == "fresh"
    assert state.lineage_facts_by_source["pkg.py"].surfaces[0].exposed == SemanticEndpoint(
        "A:pkg::target"
    )
    assert acknowledged == [str(tmp_path / "pkg.py")]

    failed_state = RepositoryAnalysisState()
    failed_candidate = _prepare_candidate_state(failed_state)
    failed_candidate.modules = {"pkg": _module("pkg")}
    failed_candidate.artifacts = {"pkg": {"own_symbols": set()}}
    failed_outcome = SimpleNamespace(
        identity_sync_required=True,
        candidate_state=failed_candidate,
        affected_modules=set(),
        blast_radius_complete=True,
        execution_trace={},
        all_modules={"pkg"},
        current_artifacts=set(),
    )
    monkeypatch.setattr(
        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
        lambda **_kwargs: failed_outcome,
    )
    failing_registry = _LineageRegistry()
    failing_engine, failed_acknowledged = _lineage_engine(
        failed_state,
        failing_registry,
        tmp_path,
    )
    monkeypatch.setattr(
        "contextor.core.analysis.lineage_materialization.materialize_lineage_source_facts",
        lambda *_args: (_ for _ in ()).throw(ValueError("materialize failed")),
    )

    with pytest.raises(ValueError, match="materialize failed"):
        failing_engine._apply_delta_and_commit(
            str(tmp_path / "pkg.py"),
            SimpleNamespace(is_deleted=False),
            None,
            SimpleNamespace(),
            [],
            {},
            None,
            extracted_lineage_facts=_extracted("pkg.py"),
            syntax_source_path="pkg.py",
        )
    assert failed_state.lineage_facts_by_source == {}
    assert failed_acknowledged == []
    assert "pkg" not in failing_registry._state["module_registry"]["path_to_id"]


def test_identity_sync_owner_deletion_matches_fresh_full_materialization_without_reextracting_untouched_consumer(
    tmp_path,
    monkeypatch,
):
    facts = _cross_source_facts()
    modules = {name: _module(name) for name in ("provider", "consumer")}
    artifacts = {
        "provider": {"own_symbols": {"target"}},
        "consumer": {"own_symbols": set()},
    }
    registry = _LifecycleRegistry(
        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
        {"provider::target": "A:provider/1"},
    )
    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
    candidate = _prepare_candidate_state(state)
    candidate.modules = {"consumer": modules["consumer"]}
    candidate.artifacts = {"consumer": artifacts["consumer"]}
    outcome = SimpleNamespace(
        identity_sync_required=True,
        candidate_state=candidate,
        affected_modules=set(),
        blast_radius_complete=True,
        execution_trace={},
        all_modules={"consumer"},
        current_artifacts=set(),
    )
    monkeypatch.setattr(
        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
        lambda **_kwargs: outcome,
    )
    monkeypatch.setattr(
        "contextor.core.analysis.lineage_extraction.extract_lineage_source_facts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("untouched consumer was re-extracted")
        ),
    )
    engine, _ = _lineage_engine(state, registry, tmp_path)

    engine._apply_delta_and_commit(
        str(tmp_path / "provider.py"),
        SimpleNamespace(is_deleted=True),
        None,
        SimpleNamespace(),
        [],
        {},
        None,
        syntax_source_path="provider.py",
    )

    full_registry = _LifecycleRegistry(
        {"consumer": "M:consumer/1"},
        {},
    )
    expected, expected_state, expected_version = _materialize_full_analysis_lineage(
        SimpleNamespace(
            modules={"consumer": modules["consumer"]},
            lineage_facts_by_source={"consumer.py": facts["consumer.py"]},
            skipped=[],
        ),
        full_registry,
        {"consumer": modules["consumer"]},
        {"consumer": artifacts["consumer"]},
    )

    assert state.lineage_facts_state == expected_state == "fresh"
    assert state.lineage_facts_semantic_version == expected_version
    assert set(state.lineage_facts_by_source) == {"consumer.py"}
    assert state.lineage_facts_by_source == expected
    exposed = state.lineage_facts_by_source["consumer.py"].surfaces[0].exposed
    assert isinstance(exposed, MaterializedSymbolicRef)
    assert exposed.module_name == "provider"
    assert not any(
        isinstance(endpoint, SemanticEndpoint)
        and endpoint.owner_id == "A:provider/1"
        for source_slice in state.lineage_facts_by_source.values()
        for fact in (*source_slice.flows, *source_slice.surfaces)
        for endpoint in (getattr(fact, "source", None), getattr(fact, "target", None), getattr(fact, "exposed", None))
    )


def test_identity_sync_owner_introduction_promotes_retained_untouched_consumer_to_full_parity(
    tmp_path,
    monkeypatch,
):
    facts = _cross_source_facts()
    consumer_modules = {"consumer": _module("consumer")}
    consumer_artifacts = {"consumer": {"own_symbols": set()}}
    registry = _LifecycleRegistry({"consumer": "M:consumer/1"}, {})
    registry._ids_by_name.update(
        {"provider": "M:provider/1", "provider::target": "A:provider/1"}
    )
    state = _lineage_state_for_facts(
        {"consumer.py": facts["consumer.py"]},
        registry,
        consumer_modules,
        consumer_artifacts,
    )
    candidate = _prepare_candidate_state(state)
    modules = {name: _module(name) for name in ("provider", "consumer")}
    artifacts = {
        "provider": {"own_symbols": {"target"}},
        "consumer": {"own_symbols": set()},
    }
    candidate.modules = modules
    candidate.artifacts = artifacts
    outcome = SimpleNamespace(
        identity_sync_required=True,
        candidate_state=candidate,
        affected_modules=set(),
        blast_radius_complete=True,
        execution_trace={},
        all_modules=set(modules),
        current_artifacts={"provider::target"},
    )
    monkeypatch.setattr(
        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
        lambda **_kwargs: outcome,
    )
    monkeypatch.setattr(
        "contextor.core.analysis.lineage_extraction.extract_lineage_source_facts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("untouched consumer was re-extracted")
        ),
    )
    engine, _ = _lineage_engine(state, registry, tmp_path)

    engine._apply_delta_and_commit(
        str(tmp_path / "provider.py"),
        SimpleNamespace(is_deleted=False),
        None,
        SimpleNamespace(),
        [],
        {},
        None,
        extracted_lineage_facts=facts["provider.py"],
        syntax_source_path="provider.py",
    )

    expected_registry = _LifecycleRegistry(
        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
        {"provider::target": "A:provider/1"},
    )
    expected, expected_state, expected_version = _materialize_full_analysis_lineage(
        SimpleNamespace(
            modules=modules,
            lineage_facts_by_source=facts,
            skipped=[],
        ),
        expected_registry,
        modules,
        artifacts,
    )

    assert state.lineage_facts_state == expected_state == "fresh"
    assert state.lineage_facts_semantic_version == expected_version
    assert set(state.lineage_facts_by_source) == {"provider.py", "consumer.py"}
    assert state.lineage_facts_by_source == expected
    assert state.lineage_facts_by_source["consumer.py"].surfaces[0].exposed == SemanticEndpoint(
        "A:provider/1"
    )


def test_identity_sync_generation_change_rematerializes_against_current_owner_id(
    tmp_path,
    monkeypatch,
):
    facts = _cross_source_facts()
    modules = {name: _module(name) for name in ("provider", "consumer")}
    artifacts = {
        "provider": {"own_symbols": {"target"}},
        "consumer": {"own_symbols": set()},
    }
    registry = _LifecycleRegistry(
        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
        {"provider::target": "A:provider/1"},
    )
    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
    registry._ids_by_name["provider::target"] = "A:provider/2"
    candidate = _prepare_candidate_state(state)
    outcome = SimpleNamespace(
        identity_sync_required=True,
        candidate_state=candidate,
        affected_modules=set(),
        blast_radius_complete=True,
        execution_trace={},
        all_modules=set(modules),
        current_artifacts={"provider::target"},
    )
    monkeypatch.setattr(
        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
        lambda **_kwargs: outcome,
    )
    engine, _ = _lineage_engine(state, registry, tmp_path)

    engine._apply_delta_and_commit(
        str(tmp_path / "provider.py"),
        SimpleNamespace(is_deleted=False),
        None,
        SimpleNamespace(),
        [],
        {},
        None,
        extracted_lineage_facts=facts["provider.py"],
        syntax_source_path="provider.py",
    )

    consumer_surface = state.lineage_facts_by_source["consumer.py"].surfaces[0]
    assert consumer_surface.exposed == SemanticEndpoint("A:provider/2")
    assert consumer_surface.exposed != SemanticEndpoint("A:provider/1")
    assert registry._state["artifact_registry"]["path_to_id"]["provider::target"] == "A:provider/2"
    assert "A:provider/1" not in state.lineage_owner_source_index
    assert "A:provider/2" in state.lineage_owner_source_index


def test_identity_sync_revalidation_failure_rolls_back_registry_and_canonical_state(
    tmp_path,
    monkeypatch,
):
    facts = _cross_source_facts()
    modules = {name: _module(name) for name in ("provider", "consumer")}
    artifacts = {
        "provider": {"own_symbols": {"target"}},
        "consumer": {"own_symbols": set()},
    }
    registry = _LifecycleRegistry(
        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
        {"provider::target": "A:provider/1"},
    )
    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
    original_modules = dict(state.modules)
    original_artifacts = dict(state.artifacts)
    original_lineage = dict(state.lineage_facts_by_source)
    candidate = _prepare_candidate_state(state)
    candidate.modules = {"consumer": modules["consumer"]}
    candidate.artifacts = {"consumer": artifacts["consumer"]}
    outcome = SimpleNamespace(
        identity_sync_required=True,
        candidate_state=candidate,
        affected_modules=set(),
        blast_radius_complete=True,
        execution_trace={},
        all_modules={"consumer"},
        current_artifacts=set(),
    )
    monkeypatch.setattr(
        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
        lambda **_kwargs: outcome,
    )

    def fail_on_untouched_consumer(source_slice, _resolution):
        if source_slice.manifest.source_key == "consumer.py":
            raise ValueError("consumer rematerialization failed")
        raise AssertionError("deleted provider should not be rematerialized")

    monkeypatch.setattr(
        "contextor.core.analysis.lineage_materialization.reresolve_materialized_lineage_source_facts",
        fail_on_untouched_consumer,
    )
    engine, acknowledged = _lineage_engine(state, registry, tmp_path)

    with pytest.raises(ValueError, match="consumer rematerialization failed"):
        engine._apply_delta_and_commit(
            str(tmp_path / "provider.py"),
            SimpleNamespace(is_deleted=True),
            None,
            SimpleNamespace(),
            [],
            {},
            None,
            syntax_source_path="provider.py",
        )

    assert state.modules == original_modules
    assert state.artifacts == original_artifacts
    assert state.lineage_facts_by_source == original_lineage
    assert registry._state["module_registry"]["path_to_id"]["provider"] == "M:provider/1"
    assert registry._state["artifact_registry"]["path_to_id"]["provider::target"] == "A:provider/1"
    assert acknowledged == []

def test_fresh_process_hydrates_materialized_symbolic_lineage_without_analysis(
    tmp_path,
    monkeypatch,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
    identity, _ = ensure_repository_identity(repo)
    cache = repo_cache_dir(repo)

    source = _lineage_slice()
    symbolic = MaterializedSymbolicRef(
        "pkg.py", "fingerprint", ExtractedSymbolicKind.PUBLIC_TARGET, "external", "target"
    )
    symbolic_flow = MaterializedFlowFact(
        "symbolic-flow", symbolic, SemanticEndpoint("A1"), LineageRelation.RETURNS,
        SourceSpan(2, 0, 2, 1), ResolutionKind.IMPORT_EXACT,
        LineageConfidence.CONFIRMED,
    )
    source = replace(
        source,
        manifest=replace(source.manifest, flow_count=2),
        flows=source.flows + (symbolic_flow,),
    )
    state = RepositoryAnalysisState(
        modules={"pkg": Module(module_id="pkg", path="pkg.py", absolute_path=str(repo / "missing.py"), imports=[])},
        dependency_graph=ProjectGraph(hard_edges={"pkg": set()}, soft_edges={"pkg": set()}),
        lineage_facts_by_source={"pkg.py": source},
        lineage_facts_state="fresh",
        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
    )
    save_snapshot(
        state, cache, "cold-lineage", repo_id=identity.repo_id, root_path=identity.root_path
    )

    child = """
import ast
import json
import contextor.core.live_state.runtime as runtime
from contextor.core.live_state.hydration import hydrate_repository_engine
runtime.connect = lambda _root: None
ast.parse = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("source parse"))
hydrated = hydrate_repository_engine(r'''%s''')
assert hydrated is not None
state = hydrated.engine.state
assert state.lineage_facts_state == "fresh"
assert state.lineage_facts_semantic_version == "1"
assert len(state.lineage_facts_by_source) == 1
assert any(type(flow.source).__name__ == "MaterializedSymbolicRef" for flow in state.lineage_facts_by_source["pkg.py"].flows)
print(json.dumps({"source": hydrated.source, "lineage": len(state.lineage_facts_by_source)}))
""" % repo
    env = os.environ.copy()
    env["CONTEXTOR_CACHE_DIR"] = str(cache_root)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1]) + os.pathsep + env.get("PYTHONPATH", "")
    completed = subprocess.run(
        [sys.executable, "-c", child],
        cwd=str(repo), env=env, text=True, capture_output=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"source": "snapshot", "lineage": 1}

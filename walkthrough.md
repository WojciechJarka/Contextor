FILES_CHANGED=
contextor/core/live_state/store.py
tests/test_lineage_state_lifecycle.py

TESTS_RUN=
.venv\Scripts\python.exe -m pytest tests/test_lineage_state_lifecycle.py tests/test_live_state_store.py -q

TEST_RESULTS=
35 passed in 5.81s

ACTUAL_DIFF=
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index c96969b..9593a09 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -12,6 +12,25 @@ from dataclasses import asdict, dataclass, replace
 from pathlib import Path
 from typing import Any
 
+from contextor.core.domain.lineage_facts import (
+    LINEAGE_FACTS_SEMANTIC_VERSION,
+    LineageConfidence,
+    LineageFamilyStatus,
+    LineageRelation,
+    MaterializedAnchorFact,
+    MaterializedFlowFact,
+    MaterializedLineageSourceFacts,
+    MaterializedOccurrenceRef,
+    MaterializedSurfaceFact,
+    ProviderRef,
+    ResolutionKind,
+    SemanticEndpoint,
+    SemanticInterfaceDescriptor,
+    SourceLineageManifest,
+    SourceSpan,
+    SurfaceKind,
+)
+
 LIVE_STATE_SCHEMA_VERSION = "1.2"
 
 
@@ -87,6 +106,206 @@ def _normalize_symbol_call_facts(state: Any) -> Any:
     return state
 
 
+def _revalidate_lineage_span(span: Any) -> SourceSpan:
+    if not isinstance(span, SourceSpan):
+        raise pickle.UnpicklingError("Invalid lineage SourceSpan.")
+    return replace(span)
+
+
+def _revalidate_lineage_endpoint(
+    endpoint: Any,
+) -> MaterializedOccurrenceRef | SemanticEndpoint:
+    if isinstance(endpoint, MaterializedOccurrenceRef):
+        return replace(endpoint)
+    if isinstance(endpoint, SemanticEndpoint):
+        return replace(endpoint)
+    raise pickle.UnpicklingError("Unknown materialized lineage endpoint.")
+
+
+def _revalidate_lineage_provider(provider: Any) -> ProviderRef | None:
+    if provider is None:
+        return None
+    if not isinstance(provider, ProviderRef):
+        raise pickle.UnpicklingError("Invalid lineage provider.")
+    return replace(provider)
+
+
+def _revalidate_lineage_manifest(manifest: Any) -> SourceLineageManifest:
+    if not isinstance(manifest, SourceLineageManifest):
+        raise pickle.UnpicklingError("Invalid lineage source manifest.")
+    if not isinstance(manifest.status, LineageFamilyStatus):
+        raise pickle.UnpicklingError("Invalid lineage manifest status.")
+    rebuilt = replace(manifest)
+    if rebuilt.semantic_version != LINEAGE_FACTS_SEMANTIC_VERSION:
+        raise pickle.UnpicklingError(
+            "Unsupported lineage manifest semantic version."
+        )
+    return rebuilt
+
+
+def _revalidate_lineage_anchor(anchor: Any) -> MaterializedAnchorFact:
+    if not isinstance(anchor, MaterializedAnchorFact):
+        raise pickle.UnpicklingError("Invalid materialized lineage anchor.")
+    return replace(
+        anchor,
+        reference=_revalidate_lineage_endpoint(anchor.reference),
+        span=_revalidate_lineage_span(anchor.span),
+    )
+
+
+def _revalidate_lineage_flow(flow: Any) -> MaterializedFlowFact:
+    if not isinstance(flow, MaterializedFlowFact):
+        raise pickle.UnpicklingError("Invalid materialized lineage flow.")
+    if not isinstance(flow.relation, LineageRelation):
+        raise pickle.UnpicklingError("Invalid lineage relation.")
+    if not isinstance(flow.resolution_kind, ResolutionKind):
+        raise pickle.UnpicklingError("Invalid lineage resolution kind.")
+    if not isinstance(flow.confidence, LineageConfidence):
+        raise pickle.UnpicklingError("Invalid lineage confidence.")
+    return replace(
+        flow,
+        source=_revalidate_lineage_endpoint(flow.source),
+        target=_revalidate_lineage_endpoint(flow.target),
+        evidence=_revalidate_lineage_span(flow.evidence),
+        provider=_revalidate_lineage_provider(flow.provider),
+    )
+
+
+def _revalidate_lineage_surface(surface: Any) -> MaterializedSurfaceFact:
+    if not isinstance(surface, MaterializedSurfaceFact):
+        raise pickle.UnpicklingError("Invalid materialized lineage surface.")
+    if not isinstance(surface.kind, SurfaceKind):
+        raise pickle.UnpicklingError("Invalid lineage surface kind.")
+    if not isinstance(surface.resolution_kind, ResolutionKind):
+        raise pickle.UnpicklingError("Invalid lineage surface resolution kind.")
+    if not isinstance(surface.confidence, LineageConfidence):
+        raise pickle.UnpicklingError("Invalid lineage surface confidence.")
+    return replace(
+        surface,
+        exposed=_revalidate_lineage_endpoint(surface.exposed),
+        evidence=_revalidate_lineage_span(surface.evidence),
+        provider=_revalidate_lineage_provider(surface.provider),
+    )
+
+
+def _revalidate_lineage_descriptor(
+    descriptor: Any,
+) -> SemanticInterfaceDescriptor:
+    if not isinstance(descriptor, SemanticInterfaceDescriptor):
+        raise pickle.UnpicklingError(
+            "Invalid lineage semantic interface descriptor."
+        )
+    return replace(descriptor)
+
+
+def _revalidate_lineage_slice(
+    source_slice: Any,
+) -> MaterializedLineageSourceFacts:
+    if not isinstance(source_slice, MaterializedLineageSourceFacts):
+        raise pickle.UnpicklingError(
+            "Invalid materialized lineage source slice."
+        )
+    return replace(
+        source_slice,
+        manifest=_revalidate_lineage_manifest(source_slice.manifest),
+        anchors=tuple(
+            _revalidate_lineage_anchor(item)
+            for item in source_slice.anchors
+        ),
+        flows=tuple(
+            _revalidate_lineage_flow(item)
+            for item in source_slice.flows
+        ),
+        surfaces=tuple(
+            _revalidate_lineage_surface(item)
+            for item in source_slice.surfaces
+        ),
+        interface_descriptors=tuple(
+            _revalidate_lineage_descriptor(item)
+            for item in source_slice.interface_descriptors
+        ),
+    )
+
+
+def _normalize_lineage_facts_state(state: Any) -> Any:
+    """Normalize/validate persisted materialized lineage without source work."""
+
+    if state is None or isinstance(state, dict) or not hasattr(state, "__dict__"):
+        return state
+
+    try:
+        if not hasattr(state, "lineage_facts_by_source"):
+            state.lineage_facts_by_source = {}
+        if not hasattr(state, "lineage_facts_state"):
+            state.lineage_facts_state = "not_materialized"
+        if not hasattr(state, "lineage_facts_semantic_version"):
+            state.lineage_facts_semantic_version = None
+
+        raw_mapping = state.lineage_facts_by_source
+        raw_family_state = state.lineage_facts_state
+        raw_version = state.lineage_facts_semantic_version
+
+        if not isinstance(raw_mapping, dict):
+            raise pickle.UnpicklingError(
+                "Lineage source mapping must be a dict."
+            )
+        if not isinstance(raw_family_state, str):
+            raise pickle.UnpicklingError(
+                "Lineage family state must be a string."
+            )
+
+        try:
+            family_status = LineageFamilyStatus(raw_family_state)
+        except ValueError as exc:
+            raise pickle.UnpicklingError(
+                "Unknown lineage family state."
+            ) from exc
+
+        if raw_version is not None and raw_version != LINEAGE_FACTS_SEMANTIC_VERSION:
+            raise pickle.UnpicklingError(
+                "Unsupported lineage semantic version."
+            )
+
+        if family_status is LineageFamilyStatus.NOT_MATERIALIZED:
+            if raw_mapping:
+                raise pickle.UnpicklingError(
+                    "Not-materialized lineage cannot contain source slices."
+                )
+            if raw_version is not None:
+                raise pickle.UnpicklingError(
+                    "Not-materialized lineage cannot have a semantic version."
+                )
+        elif raw_version != LINEAGE_FACTS_SEMANTIC_VERSION:
+            raise pickle.UnpicklingError(
+                "Materialized lineage requires the current semantic version."
+            )
+
+        normalized: dict[str, MaterializedLineageSourceFacts] = {}
+        for source_key, source_slice in raw_mapping.items():
+            if not isinstance(source_key, str) or not source_key:
+                raise pickle.UnpicklingError(
+                    "Lineage source key must be a non-empty string."
+                )
+            rebuilt = _revalidate_lineage_slice(source_slice)
+            if rebuilt.manifest.source_key != source_key:
+                raise pickle.UnpicklingError(
+                    "Lineage mapping key does not match manifest source_key."
+                )
+            normalized[source_key] = rebuilt
+
+        state.lineage_facts_by_source = normalized
+        state.lineage_facts_state = family_status.value
+        state.lineage_facts_semantic_version = raw_version
+        return state
+
+    except pickle.UnpicklingError:
+        raise
+    except (AttributeError, TypeError, ValueError) as exc:
+        raise pickle.UnpicklingError(
+            "Invalid persisted lineage state."
+        ) from exc
+
+
 @dataclass(frozen=True)
 class LiveStateMetadata:
     schema_version: str = LIVE_STATE_SCHEMA_VERSION
@@ -315,7 +534,9 @@ def load_snapshot(
             )
             if embedded_metadata.revision != metadata.revision:
                 return None
-            state_obj = _normalize_symbol_call_facts(payload["state"])
+            state_obj = _normalize_lineage_facts_state(
+                _normalize_symbol_call_facts(payload["state"])
+            )
             state_revision = (
                 state_obj.get("revision") if isinstance(state_obj, dict)
                 else getattr(state_obj, "revision", None)
@@ -421,7 +642,9 @@ def load_snapshot(
                     except AttributeError:
                         pass
             return state_obj, metadata
-        payload = _normalize_symbol_call_facts(payload)
+        payload = _normalize_lineage_facts_state(
+            _normalize_symbol_call_facts(payload)
+        )
         if payload is not None and hasattr(payload, "__dict__"):
             if not hasattr(payload, "module_usages"):
                 try:
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
new file mode 100644
index 0000000..2b59120
--- /dev/null
+++ b/tests/test_lineage_state_lifecycle.py
@@ -0,0 +1,400 @@
+from pathlib import Path
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.analysis.incremental.engine import IncrementalAnalysisEngine
+from contextor.core.analysis.incremental.plan_executor import _prepare_candidate_state
+from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.core.domain.graph import ProjectGraph
+from contextor.core.domain.lineage_facts import (
+    LINEAGE_FACTS_SEMANTIC_VERSION,
+    LineageConfidence,
+    LineageFamilyStatus,
+    LineageRelation,
+    MaterializedAnchorFact,
+    MaterializedFlowFact,
+    MaterializedLineageSourceFacts,
+    MaterializedOccurrenceRef,
+    MaterializedSurfaceFact,
+    ProviderRef,
+    ResolutionKind,
+    SemanticEndpoint,
+    SemanticInterfaceDescriptor,
+    SourceLineageManifest,
+    SourceSpan,
+    SurfaceDeclarationEvidence,
+    SurfaceKind,
+    build_return_slot,
+)
+from contextor.core.domain.module import Module
+from contextor.core.domain.usage_facts import ModuleUsageFacts
+from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.live_state.store import load_snapshot, save_snapshot
+from contextor.core.paths import repo_cache_dir
+from contextor.core.repository_identity import ensure_repository_identity
+
+
+def _lineage_slice() -> MaterializedLineageSourceFacts:
+    span = SourceSpan(1, 0, 1, 4)
+    occurrence = MaterializedOccurrenceRef("pkg.py", "fingerprint", "occ")
+    slot = build_return_slot("A1")
+    semantic = SemanticEndpoint("A1", slot)
+
+    return MaterializedLineageSourceFacts(
+        manifest=SourceLineageManifest(
+            "pkg.py",
+            "fingerprint",
+            LINEAGE_FACTS_SEMANTIC_VERSION,
+            LineageFamilyStatus.FRESH,
+            1,
+            1,
+            1,
+        ),
+        anchors=(
+            MaterializedAnchorFact(
+                "anchor",
+                occurrence,
+                "assignment",
+                span,
+            ),
+        ),
+        flows=(
+            MaterializedFlowFact(
+                "flow",
+                occurrence,
+                semantic,
+                LineageRelation.RETURNS,
+                span,
+                ResolutionKind.CALL_EXACT,
+                LineageConfidence.CONFIRMED,
+            ),
+        ),
+        surfaces=(
+            MaterializedSurfaceFact(
+                "surface",
+                SurfaceKind.REGISTRATION,
+                occurrence,
+                span,
+                ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY,
+                LineageConfidence.DYNAMIC,
+                "registered",
+                dynamic_boundary="runtime-registration",
+                provider=ProviderRef("fixture", "1"),
+                declaration_evidence=(
+                    SurfaceDeclarationEvidence.STATIC_DECLARATION
+                ),
+            ),
+        ),
+        interface_descriptors=(
+            SemanticInterfaceDescriptor(
+                "A1",
+                (slot,),
+                "signature-digest",
+            ),
+        ),
+    )
+
+
+def _persist_corrupted_lineage_slice(
+    tmp_path,
+    source_slice,
+    state_id,
+):
+    state = RepositoryAnalysisState(
+        lineage_facts_by_source={"pkg.py": source_slice},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+    )
+    save_snapshot(state, tmp_path, state_id)
+    return load_snapshot(tmp_path, expected_state_id=state_id)
+
+
+def test_repository_state_defaults_and_candidate_copy_are_lineage_safe():
+    state = RepositoryAnalysisState()
+
+    assert state.lineage_facts_by_source == {}
+    assert state.lineage_facts_state == "not_materialized"
+    assert state.lineage_facts_semantic_version is None
+
+    source_slice = _lineage_slice()
+    state.lineage_facts_by_source = {"pkg.py": source_slice}
+    state.lineage_facts_state = "fresh"
+    state.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION
+
+    candidate = _prepare_candidate_state(state)
+
+    assert candidate.lineage_facts_by_source == state.lineage_facts_by_source
+    assert candidate.lineage_facts_by_source is not state.lineage_facts_by_source
+    assert candidate.lineage_facts_by_source["pkg.py"] is source_slice
+    assert candidate.lineage_facts_state == "fresh"
+    assert candidate.lineage_facts_semantic_version == "1"
+
+    candidate.lineage_facts_by_source.pop("pkg.py")
+
+    assert "pkg.py" in state.lineage_facts_by_source
+
+
+def test_snapshot_round_trip_preserves_lineage_endpoint_types_and_metadata(
+    tmp_path,
+):
+    source_slice = _lineage_slice()
+    state = RepositoryAnalysisState(
+        lineage_facts_by_source={"pkg.py": source_slice},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+    )
+
+    save_snapshot(state, tmp_path, "lineage")
+
+    loaded, _ = load_snapshot(tmp_path, expected_state_id="lineage")
+
+    assert loaded.lineage_facts_by_source == {"pkg.py": source_slice}
+    loaded_slice = loaded.lineage_facts_by_source["pkg.py"]
+
+    assert isinstance(
+        loaded_slice.anchors[0].reference,
+        MaterializedOccurrenceRef,
+    )
+    assert isinstance(
+        loaded_slice.flows[0].target,
+        SemanticEndpoint,
+    )
+    assert loaded_slice.flows[0].target.slot == build_return_slot("A1")
+    assert (
+        loaded_slice.surfaces[0].declaration_evidence
+        is SurfaceDeclarationEvidence.STATIC_DECLARATION
+    )
+    assert loaded_slice.surfaces[0].provider == ProviderRef("fixture", "1")
+    assert loaded_slice.surfaces[0].dynamic_boundary == "runtime-registration"
+
+
+@pytest.mark.parametrize(
+    ("family_state", "version", "with_slice"),
+    [
+        ("not_materialized", "1", False),
+        ("not_materialized", None, True),
+        ("fresh", None, False),
+        ("fresh", "999", False),
+    ],
+)
+def test_snapshot_rejects_invalid_lineage_family_state_version_pairs(
+    tmp_path,
+    family_state,
+    version,
+    with_slice,
+):
+    state = RepositoryAnalysisState(
+        lineage_facts_by_source=(
+            {"pkg.py": _lineage_slice()} if with_slice else {}
+        ),
+        lineage_facts_state=family_state,
+        lineage_facts_semantic_version=version,
+    )
+    save_snapshot(state, tmp_path, "invalid")
+
+    assert load_snapshot(tmp_path, expected_state_id="invalid") is None
+
+
+def test_snapshot_rejects_mapping_manifest_key_mismatch(tmp_path):
+    state = RepositoryAnalysisState(
+        lineage_facts_by_source={"other.py": _lineage_slice()},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version="1",
+    )
+    save_snapshot(state, tmp_path, "mismatch")
+
+    assert load_snapshot(tmp_path, expected_state_id="mismatch") is None
+
+
+def test_snapshot_rejects_corrupted_materialized_endpoint(tmp_path):
+    source_slice = _lineage_slice()
+    flow = source_slice.flows[0]
+    object.__setattr__(flow, "source", "not-an-endpoint")
+
+    state = RepositoryAnalysisState(
+        lineage_facts_by_source={"pkg.py": source_slice},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version="1",
+    )
+    save_snapshot(state, tmp_path, "corrupt")
+
+    assert load_snapshot(tmp_path, expected_state_id="corrupt") is None
+
+
+@pytest.mark.parametrize("invalid_confidence", ["CONFIRMED", "not-a-confidence"])
+def test_snapshot_rejects_non_enum_flow_confidence(
+    tmp_path,
+    invalid_confidence,
+):
+    source_slice = _lineage_slice()
+    flow = source_slice.flows[0]
+    object.__setattr__(flow, "confidence", invalid_confidence)
+
+    assert (
+        _persist_corrupted_lineage_slice(
+            tmp_path,
+            source_slice,
+            "bad-flow-confidence",
+        )
+        is None
+    )
+
+
+@pytest.mark.parametrize("invalid_confidence", ["DYNAMIC", "not-a-confidence"])
+def test_snapshot_rejects_non_enum_surface_confidence(
+    tmp_path,
+    invalid_confidence,
+):
+    source_slice = _lineage_slice()
+    surface = source_slice.surfaces[0]
+    object.__setattr__(surface, "confidence", invalid_confidence)
+
+    assert (
+        _persist_corrupted_lineage_slice(
+            tmp_path,
+            source_slice,
+            "bad-surface-confidence",
+        )
+        is None
+    )
+
+
+def test_snapshot_rejects_malformed_semantic_slot(tmp_path):
+    source_slice = _lineage_slice()
+    endpoint = source_slice.flows[0].target
+    assert isinstance(endpoint, SemanticEndpoint)
+    object.__setattr__(endpoint, "slot", "slot:not-canonical")
+
+    state = RepositoryAnalysisState(
+        lineage_facts_by_source={"pkg.py": source_slice},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version="1",
+    )
+    save_snapshot(state, tmp_path, "bad-slot")
+
+    assert load_snapshot(tmp_path, expected_state_id="bad-slot") is None
+
+
+def test_real_hydration_normalizes_legacy_lineage_absence_without_source_rebuild(
+    tmp_path,
+    monkeypatch,
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    monkeypatch.setenv("CONTEXTOR_REGISTRY_DIR", str(tmp_path / "registry"))
+
+    identity, _ = ensure_repository_identity(repo)
+    cache_dir = repo_cache_dir(repo)
+
+    module = Module(
+        module_id="pkg",
+        path="pkg.py",
+        absolute_path=str(repo / "does-not-exist.py"),
+        imports=[],
+    )
+    state = RepositoryAnalysisState(
+        modules={"pkg": module},
+        dependency_graph=ProjectGraph(
+            hard_edges={"pkg": set()},
+            soft_edges={"pkg": set()},
+        ),
+        module_usages={
+            "pkg": ModuleUsageFacts(
+                symbol_calls_materialized=True,
+                reference_evidence_materialized=True,
+            )
+        },
+        artifact_consumption={},
+        artifact_consumption_state="fresh",
+        collision_facts={"pkg": []},
+        collisions_state="fresh",
+    )
+
+    delattr(state, "lineage_facts_by_source")
+    delattr(state, "lineage_facts_state")
+    delattr(state, "lineage_facts_semantic_version")
+
+    save_snapshot(
+        state,
+        cache_dir,
+        "legacy-lineage",
+        repo_id=identity.repo_id,
+        root_path=identity.root_path,
+    )
+
+    monkeypatch.setattr(
+        "contextor.core.live_state.runtime.connect",
+        lambda _root: None,
+    )
+
+    def forbidden_source_rebuild(*_args, **_kwargs):
+        raise AssertionError("hydration attempted source-backed reconstruction")
+
+    monkeypatch.setattr(
+        "contextor.core.reference.engine.extract_module_usage_facts",
+        forbidden_source_rebuild,
+    )
+    monkeypatch.setattr(
+        "contextor.core.reporting_engine.persistent_registry."
+        "PersistentIdentityRegistry.sync_with_workspace",
+        forbidden_source_rebuild,
+    )
+
+    hydrated = hydrate_repository_engine(repo)
+
+    assert hydrated is not None
+    assert hydrated.engine.state.lineage_facts_by_source == {}
+    assert hydrated.engine.state.lineage_facts_state == "not_materialized"
+    assert hydrated.engine.state.lineage_facts_semantic_version is None
+
+
+def test_incremental_commit_publishes_lineage_candidate_fields(
+    tmp_path,
+    monkeypatch,
+):
+    state = RepositoryAnalysisState()
+    source_slice = _lineage_slice()
+    candidate = _prepare_candidate_state(state)
+    candidate.lineage_facts_by_source = {"pkg.py": source_slice}
+    candidate.lineage_facts_state = "fresh"
+    candidate.lineage_facts_semantic_version = "1"
+
+    outcome = SimpleNamespace(
+        identity_sync_required=False,
+        candidate_state=candidate,
+        affected_modules=set(),
+        blast_radius_complete=True,
+        execution_trace={},
+        all_modules=set(),
+        current_artifacts={},
+    )
+
+    monkeypatch.setattr(
+        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
+        lambda **_kwargs: outcome,
+    )
+
+    engine = object.__new__(IncrementalAnalysisEngine)
+    engine.state = state
+    engine.root_path = Path(tmp_path)
+    engine.registry = SimpleNamespace()
+    engine.state_manager = SimpleNamespace(
+        update_state=lambda _path: None,
+    )
+
+    engine._apply_delta_and_commit(
+        str(tmp_path / "pkg.py"),
+        SimpleNamespace(),
+        None,
+        SimpleNamespace(),
+        [],
+        {},
+        None,
+    )
+
+    assert state.lineage_facts_by_source == {"pkg.py": source_slice}
+    assert state.lineage_facts_state == "fresh"
+    assert state.lineage_facts_semantic_version == "1"


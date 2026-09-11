STATUS=PASS
HEAD/WORKTREE_BASE=5e6109d9beaeec5f640d69d5890aaef0224f25eb (clean baseline before Stage 1F.2)
MCP_POOL_DISCOVERY=
ACTIVE: contextor_fact_lineage callable; contextor_lineage absent from callable inventory.
DEFERRED: inspected available/deferred-capable tool inventory; no deferred Contextor lineage callable or deferred-tool search surface was exposed.
LINEAGE_TOOL_USED=contextor_fact_lineage (required substitution for unavailable contextor_lineage)
CURRENT_FULL_ANALYSIS_OWNER=contextor.core.api.facade::ContextorFacade.analyze_project
EXACT_WIRING_POINT=after execute_global_pipeline returns, after its artifact pipeline synchronizes PersistentIdentityRegistry, immediately before RepositoryAnalysisState construction and save/publish.
RESOLUTION_CONTEXT_CONSTRUCTION=_materialize_full_analysis_lineage reads the finalized registry in read_transaction and limits maps to current modules plus collect_qualified_artifact_identities(raw_artifacts). active_owner_ids is exactly those current map values. No recovery mapping is read. interface_descriptors is empty because this full-analysis path has no existing canonical descriptor producer; slot-bearing targets remain symbolic.
FULL_DATA_FLOW_AFTER_CHANGE=source -> index_repository single parse/extract -> RepositoryIndex.lineage_facts_by_source -> execute_global_pipeline registry sync -> read-only LineageResolutionContext -> materialize_lineage_source_facts once per sorted source -> atomic RepositoryAnalysisState.lineage_facts_by_source installation -> save/publish.
FAMILY_STATE_COVERAGE_RULE=fresh only when every eligible indexed source has exactly one installed current manifest and index.skipped is empty; resource_limit is retained when complete coverage includes a resource-limited slice; missing source coverage or skipped source is deferred; empty eligible source set is fresh with an empty mapping. Any foreign extracted key, key/manifest mismatch, missing finalized active ID, or materializer failure raises rather than publishing fresh state. All materialized states use LINEAGE_FACTS_SEMANTIC_VERSION.
ONE_PARSE_SOURCE_READ_REGISTRY_ALLOCATION_PROOF=indexer extracts before cache and the integration test counted exactly one extraction for each of consumer.py/provider.py. Wiring consumes only RepositoryIndex slices. The helper uses registry.read_transaction and raw maps; its test makes get_module_id/get_artifact_id fail if called. The pure materializer contract test remains green.
FOCUSED_TESTS=
.venv\Scripts\python.exe -m py_compile contextor/core/api/facade.py tests/test_full_analysis_lineage_materialization.py => PASS
.venv\Scripts\python.exe -m pytest -q tests/test_full_analysis_lineage_materialization.py tests/analysis/test_lineage_materialization.py tests/analysis/test_lineage_extraction.py => 209 passed in 4.33s
 git diff --check => PASS
LIVE_CONTINUITY_EVIDENCE=get_live_events(after_revision=673) returned transient_connection_failure: existing LIVE owner temporarily unreachable. No update_file, restart, or probe was used. This transport condition does not invalidate the focused static evidence.
FILES_CHANGED=
contextor/core/api/facade.py
tests/test_full_analysis_lineage_materialization.py
FULL_DIFF=diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index cf348ed..c2ce409 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -259,6 +259,96 @@ def _initialize_repository_identity(repo_root: str | Path) -> PersistentIdentity
     return registry
 
 
+def _materialize_full_analysis_lineage(index, registry, modules, artifacts):
+    """Materialize current index lineage from finalized active identities."""
+    from contextor.core.analysis.lineage_materialization import (
+        LineageResolutionContext,
+        materialize_lineage_source_facts,
+    )
+    from contextor.core.domain.lineage_facts import (
+        LINEAGE_FACTS_SEMANTIC_VERSION,
+        LineageFamilyStatus,
+    )
+    from contextor.core.reporting_layer.artifact_usage_report import (
+        collect_qualified_artifact_identities,
+    )
+
+    eligible_source_keys = {
+        Path(str(module.path)).as_posix()
+        for module in modules.values()
+    }
+    extracted_by_source = dict(getattr(index, "lineage_facts_by_source", {}) or {})
+    foreign_source_keys = set(extracted_by_source) - eligible_source_keys
+    if foreign_source_keys:
+        raise ValueError(
+            "Extracted lineage contains sources outside the active analysis: "
+            f"{sorted(foreign_source_keys)!r}"
+        )
+
+    active_module_names = set(modules)
+    active_artifact_names = collect_qualified_artifact_identities(artifacts)
+    with registry.read_transaction():
+        module_registry = registry._state["module_registry"]["path_to_id"]
+        artifact_registry = registry._state["artifact_registry"]["path_to_id"]
+        active_module_ids = {
+            name: module_registry[name]
+            for name in sorted(active_module_names)
+            if name in module_registry
+        }
+        active_artifact_ids = {
+            name: artifact_registry[name]
+            for name in sorted(active_artifact_names)
+            if name in artifact_registry
+        }
+
+    missing_module_ids = active_module_names - set(active_module_ids)
+    missing_artifact_ids = active_artifact_names - set(active_artifact_ids)
+    if missing_module_ids or missing_artifact_ids:
+        raise ValueError(
+            "Finalized identity registry is missing active lineage owners: "
+            f"modules={sorted(missing_module_ids)!r}, "
+            f"artifacts={sorted(missing_artifact_ids)!r}"
+        )
+
+    resolution = LineageResolutionContext(
+        active_module_ids=active_module_ids,
+        active_artifact_ids=active_artifact_ids,
+        active_owner_ids=frozenset(
+            (*active_module_ids.values(), *active_artifact_ids.values())
+        ),
+        interface_descriptors={},
+    )
+    materialized_by_source = {}
+    for source_key in sorted(extracted_by_source):
+        extracted = extracted_by_source[source_key]
+        if extracted.source_key != source_key:
+            raise ValueError("Extracted lineage mapping key does not match its source key.")
+        materialized = materialize_lineage_source_facts(extracted, resolution)
+        if (
+            materialized.manifest.source_key != extracted.source_key
+            or materialized.manifest.source_fingerprint != extracted.source_fingerprint
+        ):
+            raise ValueError("Materialized lineage manifest does not match extracted source.")
+        materialized_by_source[source_key] = materialized
+
+    missing_source_keys = eligible_source_keys - set(materialized_by_source)
+    if missing_source_keys or getattr(index, "skipped", ()):
+        family_state = LineageFamilyStatus.DEFERRED.value
+    elif any(
+        item.manifest.status is LineageFamilyStatus.RESOURCE_LIMIT
+        for item in materialized_by_source.values()
+    ):
+        family_state = LineageFamilyStatus.RESOURCE_LIMIT.value
+    else:
+        family_state = LineageFamilyStatus.FRESH.value
+
+    return (
+        dict(sorted(materialized_by_source.items())),
+        family_state,
+        LINEAGE_FACTS_SEMANTIC_VERSION,
+    )
+
+
 def _resolve_repository_target(
     repo_root: str | Path,
     target: str | Path,
@@ -522,6 +612,16 @@ class ContextorFacade:
             syntax_diagnostics_by_path, syntax_diagnostics_state = (
                 build_syntax_diagnostics_from_index(index)
             )
+            (
+                lineage_facts_by_source,
+                lineage_facts_state,
+                lineage_facts_semantic_version,
+            ) = _materialize_full_analysis_lineage(
+                index,
+                registry,
+                mods,
+                raw_artifacts,
+            )
 
             state = RepositoryAnalysisState(
                 modules=mods,
@@ -535,6 +635,9 @@ class ContextorFacade:
                 syntax_diagnostics_state=syntax_diagnostics_state,
                 module_usages=module_usages,
                 module_usages_manifest=module_usages_manifest,
+                lineage_facts_by_source=lineage_facts_by_source,
+                lineage_facts_state=lineage_facts_state,
+                lineage_facts_semantic_version=lineage_facts_semantic_version,
                 metrics=metrics,
                 topology_analytics=topology_analytics,
                 topology_metrics_state="fresh",
diff --git a/tests/test_full_analysis_lineage_materialization.py b/tests/test_full_analysis_lineage_materialization.py
new file mode 100644
index 0000000..9fa35a5
--- /dev/null
+++ b/tests/test_full_analysis_lineage_materialization.py
@@ -0,0 +1,183 @@
+from contextlib import contextmanager
+from types import SimpleNamespace
+
+from contextor.core.api.facade import (
+    ContextorFacade,
+    _materialize_full_analysis_lineage,
+)
+from contextor.core.domain.lineage_facts import (
+    LINEAGE_FACTS_SEMANTIC_VERSION,
+    ExtractedAnchorFact,
+    ExtractedFlowFact,
+    ExtractedLineageSourceFacts,
+    ExtractedOccurrenceRef,
+    ExtractedSymbolicKind,
+    ExtractedSymbolicRef,
+    LineageConfidence,
+    LineageFamilyStatus,
+    LineageRelation,
+    MaterializedSymbolicRef,
+    ResolutionKind,
+    SemanticEndpoint,
+    SourceSpan,
+)
+from contextor.core.analysis import state_manager
+from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+from contextor.core.symbol_engine import indexer
+
+
+class _ReadOnlyRegistry:
+    def __init__(self, modules, artifacts):
+        self._state = {
+            "module_registry": {"path_to_id": modules},
+            "artifact_registry": {"path_to_id": artifacts},
+        }
+        self.read_count = 0
+
+    @contextmanager
+    def read_transaction(self):
+        self.read_count += 1
+        yield
+
+    def get_module_id(self, _name):
+        raise AssertionError("lineage materialization must not allocate module identities")
+
+    def get_artifact_id(self, _name):
+        raise AssertionError("lineage materialization must not allocate artifact identities")
+
+
+def _fresh_slice(status=LineageFamilyStatus.FRESH):
+    span = SourceSpan(1, 0, 1, 1)
+    return ExtractedLineageSourceFacts(
+        source_key="pkg.py",
+        source_fingerprint="fingerprint",
+        anchors=(ExtractedAnchorFact("local", "module", span),),
+        flows=(
+            ExtractedFlowFact(
+                "dynamic",
+                ExtractedOccurrenceRef("local"),
+                ExtractedSymbolicRef(
+                    ExtractedSymbolicKind.CALLEE, "pkg", "dynamic_target"
+                ),
+                LineageRelation.CALL_RESULT,
+                span,
+                ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY,
+                LineageConfidence.DYNAMIC,
+                dynamic_boundary="dynamic_call",
+            ),
+            ExtractedFlowFact(
+                "flow",
+                ExtractedOccurrenceRef("local"),
+                ExtractedSymbolicRef(
+                    ExtractedSymbolicKind.DEFINITION, "pkg", "target"
+                ),
+                LineageRelation.CALL_RESULT,
+                span,
+                ResolutionKind.CALL_EXACT,
+                LineageConfidence.CONFIRMED,
+            ),
+        ),
+        status=status,
+        resource_limit_reason="node_limit" if status is LineageFamilyStatus.RESOURCE_LIMIT else None,
+    )
+
+
+def _index(*, facts=None, skipped=()):
+    return SimpleNamespace(
+        modules={"pkg": SimpleNamespace(path="pkg.py")},
+        lineage_facts_by_source=facts or {},
+        skipped=list(skipped),
+    )
+
+
+def test_full_analysis_materializes_active_ids_once_with_current_manifest_and_no_allocation():
+    registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
+    index = _index(facts={"pkg.py": _fresh_slice()})
+    artifacts = {"pkg": {"own_symbols": ["target"]}}
+
+    first = _materialize_full_analysis_lineage(index, registry, index.modules, artifacts)
+    second = _materialize_full_analysis_lineage(index, registry, index.modules, artifacts)
+
+    mapping, family_state, version = first
+    assert first == second
+    assert registry.read_count == 2
+    assert set(mapping) == {"pkg.py"}
+    assert family_state == "fresh"
+    assert version == LINEAGE_FACTS_SEMANTIC_VERSION
+    source_slice = mapping["pkg.py"]
+    assert source_slice.manifest.source_key == "pkg.py"
+    assert source_slice.manifest.source_fingerprint == "fingerprint"
+    assert source_slice.flows[1].target == SemanticEndpoint("A1/1")
+    assert isinstance(source_slice.flows[0].target, MaterializedSymbolicRef)
+
+
+def test_full_analysis_lineage_coverage_states_are_explicit_for_resource_skip_and_empty():
+    registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
+    artifacts = {"pkg": {"own_symbols": ["target"]}}
+
+    resource = _materialize_full_analysis_lineage(
+        _index(facts={"pkg.py": _fresh_slice(LineageFamilyStatus.RESOURCE_LIMIT)}),
+        registry,
+        _index().modules,
+        artifacts,
+    )
+    deferred = _materialize_full_analysis_lineage(
+        _index(skipped=(SimpleNamespace(path="broken.py"),)),
+        registry,
+        _index().modules,
+        artifacts,
+    )
+    empty_registry = _ReadOnlyRegistry({}, {})
+    empty_index = SimpleNamespace(modules={}, lineage_facts_by_source={}, skipped=[])
+    empty = _materialize_full_analysis_lineage(empty_index, empty_registry, {}, {})
+
+    assert resource[1:] == ("resource_limit", LINEAGE_FACTS_SEMANTIC_VERSION)
+    assert deferred == ({}, "deferred", LINEAGE_FACTS_SEMANTIC_VERSION)
+    assert empty == ({}, "fresh", LINEAGE_FACTS_SEMANTIC_VERSION)
+
+
+def test_real_full_analysis_installs_current_lineage_without_second_extraction(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    (repo / "provider.py").write_text("def target():\n    return 1\n", encoding="utf-8")
+    (repo / "consumer.py").write_text(
+        "from provider import target\nvalue = target()\n", encoding="utf-8"
+    )
+
+    original_extract = indexer.extract_lineage_source_facts
+    extracted_source_keys = []
+
+    def counted_extract(tree, *, source_key, source_fingerprint, **kwargs):
+        extracted_source_keys.append(source_key)
+        return original_extract(
+            tree,
+            source_key=source_key,
+            source_fingerprint=source_fingerprint,
+            **kwargs,
+        )
+
+    captured_states = []
+    original_save_engine_state = state_manager.save_engine_state
+
+    def capture_save_engine_state(state, *args, **kwargs):
+        captured_states.append(state)
+        return original_save_engine_state(state, *args, **kwargs)
+
+    monkeypatch.setattr(indexer, "extract_lineage_source_facts", counted_extract)
+    monkeypatch.setattr(state_manager, "save_engine_state", capture_save_engine_state)
+    errors, _ = ContextorFacade.analyze_project(str(repo))
+
+    assert errors == []
+    assert sorted(extracted_source_keys) == ["consumer.py", "provider.py"]
+    assert len(captured_states) == 1
+    state = captured_states[0]
+    assert state.lineage_facts_state == "fresh"
+    assert state.lineage_facts_semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
+    assert set(state.lineage_facts_by_source) == {"consumer.py", "provider.py"}
+    assert all(
+        source_key == source_slice.manifest.source_key
+        for source_key, source_slice in state.lineage_facts_by_source.items()
+    )

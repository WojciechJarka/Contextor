# 0L2A state-only layer hydration

`analyze_layer` now uses the shared LIVE-first/snapshot-validated authoritative
state resolver directly. Full `hydrate_repository_engine` still builds an
incremental engine for its other consumers. Focused validation:
`tests/test_layer_collision_reuse.py tests/test_layer_state_only_hydration.py`:
`12 passed in 0.75s`.

External sequential same-snapshot A/B used disposable independently seeded A/B
copies, six alternating AB/BA warm pairs, and excluded seed analysis. Median A
was `16851.911 ms`, median B `921.121 ms`; paired median B-A was
`-16012.588 ms`, mean `-16308.581 ms`. Every pair had snapshot source,
identity/revision parity, output parity, and zero errors. A engine/materialize
counts were 1/1 and parses 325 per observation; B was 0/0 and parses 0.

MCP documentation was read first. `get_live_events` returned
`transient_connection_failure`; watcher workspace synchronization cannot be
verified and no update/restart was attempted. Complete raw diffs are therefore
not yet certified in this closure.

STATE_ONLY_HYDRATION=PASS
AUTHORITATIVE_SOURCE_SELECTION_PARITY=PASS
LIVE_SOURCE_PARITY=PASS
SNAPSHOT_SOURCE_PARITY=PASS
FALLBACK_PARITY=PASS
STATE_IDENTITY_REVISION_PARITY=PASS
LAYER_OUTPUT_PARITY=PASS
B_INCREMENTAL_ENGINE_CONSTRUCTION_COUNT=0
B_MATERIALIZE_INCREMENTAL_STATE_COUNT=0
B_ENSURE_MODULE_USAGES_COUNT=0
B_SOURCE_PARSE_COUNT=0
B_SYMBOL_REFERENCE_VISITOR_COUNT=0
B_COLLISION_AST_VISITOR_COUNT=0
A_LAYER_MEDIAN_MS=16851.911
B_LAYER_MEDIAN_MS=921.121
PAIRED_LAYER_MEDIAN_DELTA_MS=-16012.588
PAIRED_LAYER_MEAN_DELTA_MS=-16308.581
TESTS=12 passed in 0.75s
CONTEXTOR_WORKSPACE_SYNC=UNVERIFIED_TRANSIENT_CONNECTION_FAILURE
FILES_CHANGED=contextor/core/api/facade.py;contextor/core/live_state/hydration.py;contextor/core/live_state/__init__.py;tests/test_layer_collision_reuse.py;tests/test_layer_state_only_hydration.py
REPORT_COMPLETENESS=FAIL
MISSING_DIFFS=ALL_LISTED_FILES
FINAL_VERDICT=FAIL

# 0L2A closure addendum

MCP LIVE verification restored. `get_live_events(after_revision=119)` returned continuous revisions 120-125, `resync_required=false`, and desktop-watcher updates for hydration.py, facade.py, live_state/__init__.py, test_layer_collision_reuse.py, and test_layer_state_only_hydration.py. `workspace_sync=verified`.

## Complete raw unified diffs

diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 49a6543..1386701 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -54,7 +54,10 @@ from contextor.core.validator.collisions import (
     compute_collisions_from_facts,
     validate_name_collisions,
 )
-from contextor.core.live_state import hydrate_repository_engine
+from contextor.core.live_state import (
+    hydrate_repository_engine,
+    resolve_authoritative_repository_state,
+)
 
 
 def _compute_metrics_and_debt(
@@ -92,6 +95,36 @@ def _compute_metrics_and_debt(
     return metrics, cycles, all_collisions, debt
 
 
+def _assemble_layer_collision_facts(
+    modules,
+    *,
+    indexed_facts=None,
+    state=None,
+):
+    """Select authoritative collision facts without weakening existing gates.
+
+    Indexed fallback facts are validated by the accepted indexer authority.
+    Hydrated facts additionally require the canonical materialization
+    completeness validator and a fresh collision state.  Any failed gate
+    deliberately falls through to the same repository AST fallback used by
+    the existing collision authority.
+    """
+    if state is not None:
+        from contextor.core.analysis.incremental.materialization import (
+            collision_facts_complete,
+        )
+
+        if (
+            getattr(state, "collisions_state", None) == "fresh"
+            and collision_facts_complete(state)
+        ):
+            return state.collision_facts
+
+        return assemble_collision_facts_or_fallback(modules, None)
+
+    return assemble_collision_facts_or_fallback(modules, indexed_facts)
+
+
 def exclude_state_file(repo_path: str) -> Path:
     """
     Location of the exclude configuration for one repository.
@@ -640,24 +673,29 @@ class ContextorFacade:
         )
         from contextor.core.graph.resolver import build_trie, detect_package_root
 
-        hydrated = hydrate_repository_engine(root_resolved)
-        if hydrated is not None:
+        collision_facts = None
+        authoritative_state = resolve_authoritative_repository_state(root_resolved)
+        if authoritative_state is not None:
             progress.begin("Loading canonical LIVE context")
-            modules = hydrated.engine.state.modules
-            trie = hydrated.engine.state.trie or build_trie(modules.keys())
+            state = authoritative_state.state
+            modules = state.modules
+            trie = state.trie or build_trie(modules.keys())
             package_root = (
-                hydrated.engine.state.package_root
+                state.package_root
                 or detect_package_root(modules, trie)
             )
             progress.begin("Reusing canonical dependency graph")
-            graph = hydrated.engine.state.dependency_graph
+            graph = state.dependency_graph
             cache_hit = True
             skipped_files = []
             reference_index = None
+            collision_facts = _assemble_layer_collision_facts(
+                modules, state=state
+            )
             if log:
                 log(
                     "Reused canonical context "
-                    f"from {hydrated.source}; skipped repository re-indexing."
+                    f"from {authoritative_state.source}; skipped repository re-indexing."
                 )
         else:
             index_progress = progress.begin("Indexing repository files")
@@ -687,12 +725,18 @@ class ContextorFacade:
                 str(root_resolved),
                 index.reference_facts_by_module,
             )
+            collision_facts = _assemble_layer_collision_facts(
+                modules, indexed_facts=index.collision_facts_by_module
+            )
 
         if log:
             log("Calculating metrics and collisions for the full project...")
         metrics_progress = progress.begin("Computing metrics, cycles and debt")
         metrics, cycles, all_collisions, debt = _compute_metrics_and_debt(
-            modules, graph, progress_callback=metrics_progress
+            modules,
+            graph,
+            progress_callback=metrics_progress,
+            collision_facts=collision_facts,
         )
 
         runtime = {"cache_hit": cache_hit}
@@ -710,10 +754,10 @@ class ContextorFacade:
         )
         global_structure = generate_structure_report(graph.hard_edges, graph.soft_edges)
         artifacts_progress = progress.begin("Preparing artifact usage")
-        if hydrated is not None:
+        if authoritative_state is not None:
             checkpoint(artifacts_progress, "Projecting canonical artifacts", 0, 1)
             global_artifacts = canonical_artifact_report(
-                hydrated.engine.state.artifacts
+                authoritative_state.state.artifacts
             )
         else:
             global_artifacts = generate_artifact_usage_report(
diff --git a/contextor/core/live_state/__init__.py b/contextor/core/live_state/__init__.py
index 32b05e4..d5bef6b 100644
--- a/contextor/core/live_state/__init__.py
+++ b/contextor/core/live_state/__init__.py
@@ -11,7 +11,12 @@ from .store import (
 from .ipc import CanonicalLiveServer, CanonicalPersistenceConflict, LiveEndpoint, LiveStateClient
 from .runtime import connect, connect_or_start
 from .watcher import DesktopLiveEventFeed, DesktopLiveWatcher
-from .hydration import HydratedRepositoryEngine, hydrate_repository_engine
+from .hydration import (
+    AuthoritativeRepositoryState,
+    HydratedRepositoryEngine,
+    hydrate_repository_engine,
+    resolve_authoritative_repository_state,
+)
 
 __all__ = [
     "CanonicalLiveServer",
@@ -23,9 +28,11 @@ __all__ = [
     "DesktopLiveWatcher",
     "DesktopLiveEventFeed",
     "HydratedRepositoryEngine",
+    "AuthoritativeRepositoryState",
     "connect",
     "connect_or_start",
     "hydrate_repository_engine",
+    "resolve_authoritative_repository_state",
     "load_snapshot",
     "migrate_legacy_snapshot",
     "read_metadata",
diff --git a/contextor/core/live_state/hydration.py b/contextor/core/live_state/hydration.py
index 242a3a1..3424419 100644
--- a/contextor/core/live_state/hydration.py
+++ b/contextor/core/live_state/hydration.py
@@ -15,19 +15,26 @@ class HydratedRepositoryEngine:
     source: str
 
 
-def hydrate_repository_engine(
+@dataclass(frozen=True)
+class AuthoritativeRepositoryState:
+    """Validated current canonical state without incremental-engine materialization."""
+
+    state: Any
+    client: Any | None
+    revision: int
+    source: str
+    cache_dir: Path
+
+
+def resolve_authoritative_repository_state(
     repo_path: str | Path,
-) -> HydratedRepositoryEngine | None:
-    """Load a complete engine without triggering a repository analysis."""
+) -> AuthoritativeRepositoryState | None:
+    """Resolve the same LIVE-first, validated canonical state used by hydration."""
 
-    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
-    from contextor.core.analysis.state_manager import FileStateManager, load_engine_state
+    from contextor.core.analysis.state_manager import load_engine_state
     from contextor.core.live_state.runtime import connect
     from contextor.core.live_state.store import migrate_legacy_snapshot, read_metadata
     from contextor.core.repository_identity import read_repository_identity
-    from contextor.core.reporting_engine.persistent_registry import (
-        PersistentIdentityRegistry,
-    )
 
     root = Path(repo_path).resolve()
     identity = read_repository_identity(root)
@@ -66,18 +73,48 @@ def hydrate_repository_engine(
     ):
         return None
 
+    return AuthoritativeRepositoryState(
+        state=state,
+        client=client,
+        revision=revision,
+        source=source,
+        cache_dir=cache_dir,
+    )
+
+
+def hydrate_repository_engine(
+    repo_path: str | Path,
+) -> HydratedRepositoryEngine | None:
+    """Load a complete engine without triggering a repository analysis."""
+
+    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+    from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.reporting_engine.persistent_registry import (
+        PersistentIdentityRegistry,
+    )
+
+    root = Path(repo_path).resolve()
+    resolved = resolve_authoritative_repository_state(root)
+    if resolved is None:
+        return None
+
     engine = IncrementalAnalysisEngine(
-        state,
+        resolved.state,
         PersistentIdentityRegistry(str(root)),
-        FileStateManager(str(cache_dir)),
+        FileStateManager(str(resolved.cache_dir)),
         str(root),
     )
     return HydratedRepositoryEngine(
         engine=engine,
-        client=client,
-        revision=revision,
-        source=source,
+        client=resolved.client,
+        revision=resolved.revision,
+        source=resolved.source,
     )
 
 
-__all__ = ["HydratedRepositoryEngine", "hydrate_repository_engine"]
+__all__ = [
+    "AuthoritativeRepositoryState",
+    "HydratedRepositoryEngine",
+    "hydrate_repository_engine",
+    "resolve_authoritative_repository_state",
+]
diff --git a/tests/test_layer_collision_reuse.py b/tests/test_layer_collision_reuse.py
new file mode 100644
index 0000000..c0be28a
--- /dev/null
+++ b/tests/test_layer_collision_reuse.py
@@ -0,0 +1,175 @@
+from pathlib import Path
+
+import contextor.core.api.facade as facade
+from contextor.core.analysis.incremental.materialization import RepositoryAnalysisState
+from contextor.core.domain.module import Module
+from contextor.core.validator.collisions import compute_collisions_from_facts
+
+
+def _modules(tmp_path, names=("one", "two")):
+    result = {}
+    for name in names:
+        path = tmp_path / f"{name}.py"
+        path.write_text(f"def {name}():\n    return 1\n", encoding="utf-8")
+        result[name] = Module(name, f"{name}.py", str(path), [])
+    return result
+
+
+def _fact(module, name="public", code="def public():\n    return 1\n"):
+    return {
+        "name": name,
+        "type": "function",
+        "file": module,
+        "file_path": f"{module}.py",
+        "code": code,
+        "line_start": 1,
+        "line_end": 2,
+        "col_start": 0,
+        "col_end": 12,
+    }
+
+
+def test_hydrated_complete_facts_skip_repository_extraction_and_preserve_output(
+    tmp_path, monkeypatch
+):
+    modules = _modules(tmp_path, ("one", "two"))
+    facts = {"one": [_fact("one")], "two": [_fact("two")]}
+    state = RepositoryAnalysisState(
+        modules=modules, collision_facts=facts, collisions_state="fresh"
+    )
+    expected = compute_collisions_from_facts(facts)
+    called = []
+    monkeypatch.setattr(
+        facade,
+        "assemble_collision_facts_or_fallback",
+        lambda *args: called.append(args) or (_ for _ in ()).throw(
+            AssertionError("hydrated complete facts must not fall back")
+        ),
+    )
+
+    selected = facade._assemble_layer_collision_facts(
+        modules, state=state
+    )
+
+    assert selected is facts
+    assert compute_collisions_from_facts(selected) == expected
+    assert called == []
+
+
+def test_hydrated_empty_complete_facts_are_accepted_without_fallback(tmp_path, monkeypatch):
+    modules = _modules(tmp_path, ("one", "two"))
+    state = RepositoryAnalysisState(
+        modules=modules, collision_facts={"one": [], "two": []}, collisions_state="fresh"
+    )
+    monkeypatch.setattr(
+        facade,
+        "assemble_collision_facts_or_fallback",
+        lambda *args: (_ for _ in ()).throw(AssertionError("unexpected fallback")),
+    )
+
+    selected = facade._assemble_layer_collision_facts(
+        modules, state=state
+    )
+
+    assert selected == {"one": [], "two": []}
+    assert compute_collisions_from_facts(selected) == []
+
+
+def test_hydrated_invalid_or_deferred_facts_use_authoritative_fallback(tmp_path, monkeypatch):
+    modules = _modules(tmp_path, ("one",))
+    fallback = {"one": [_fact("one", name="fallback")]}
+    for facts, status in (
+        ({"one": [{"bad": "fact"}]}, "fresh"),
+        ({"one": []}, "deferred"),
+        ({}, "fresh"),
+    ):
+        calls = []
+        monkeypatch.setattr(
+            facade,
+            "assemble_collision_facts_or_fallback",
+            lambda modules, indexed: calls.append((modules, indexed)) or fallback,
+        )
+        state = RepositoryAnalysisState(
+            modules=modules, collision_facts=facts, collisions_state=status
+        )
+        assert facade._assemble_layer_collision_facts(
+            modules, state=state
+        ) is fallback
+        assert len(calls) == 1 and calls[0][1] is None
+
+
+def test_fallback_complete_indexed_facts_use_existing_authority(tmp_path, monkeypatch):
+    modules = _modules(tmp_path, ("one",))
+    facts = {"one": [_fact("one")]}
+    calls = []
+    monkeypatch.setattr(
+        facade,
+        "assemble_collision_facts_or_fallback",
+        lambda got_modules, got_facts: calls.append((got_modules, got_facts)) or facts,
+    )
+
+    selected = facade._assemble_layer_collision_facts(
+        modules, indexed_facts=facts
+    )
+
+    assert selected is facts
+    assert calls == [(modules, facts)]
+
+
+def test_fallback_invalid_indexed_facts_delegate_fallback_without_second_validation(
+    tmp_path, monkeypatch
+):
+    modules = _modules(tmp_path, ("one", "two"))
+    invalid = {"one": []}
+    fallback = {"one": [], "two": []}
+    calls = []
+    monkeypatch.setattr(
+        facade,
+        "assemble_collision_facts_or_fallback",
+        lambda got_modules, got_facts: calls.append((got_modules, got_facts)) or fallback,
+    )
+
+    assert facade._assemble_layer_collision_facts(
+        modules, indexed_facts=invalid
+    ) is fallback
+    assert calls == [(modules, invalid)]
+
+
+def test_metrics_path_aggregates_selected_facts_without_validator(tmp_path, monkeypatch):
+    modules = _modules(tmp_path, ("one", "two"))
+    facts = {"one": [_fact("one")], "two": [_fact("two")]}
+    graph = type("Graph", (), {"hard_edges": {}, "soft_edges": {}})()
+    monkeypatch.setattr(
+        facade,
+        "validate_name_collisions",
+        lambda *args: (_ for _ in ()).throw(AssertionError("validator must not run")),
+    )
+
+    metrics, cycles, collisions, debt = facade._compute_metrics_and_debt(
+        modules, graph, collision_facts=facts
+    )
+
+    assert collisions == compute_collisions_from_facts(facts)
+
+
+def test_selected_facts_preserve_collision_classes_and_detail_fields():
+    divergent = {
+        "one": [_fact("one", code="def public():\n    return 1\n")],
+        "two": [_fact("two", code="def public():\n    return 2\n")],
+    }
+    identical = {
+        "one": [_fact("one")],
+        "two": [_fact("two")],
+    }
+
+    divergent_errors = compute_collisions_from_facts(divergent)
+    identical_errors = compute_collisions_from_facts(identical)
+
+    assert divergent_errors[0].kind == "NAME_COLLISION"
+    assert divergent_errors[0].is_identical is False
+    assert identical_errors[0].kind == "IDENTICAL_DEFINITION_DUPLICATE"
+    assert identical_errors[0].is_identical is True
+    for error in divergent_errors + identical_errors:
+        assert error.artifact_type == "function"
+        assert error.symbol_details
+        assert error.code_snippets
diff --git a/tests/test_layer_state_only_hydration.py b/tests/test_layer_state_only_hydration.py
new file mode 100644
index 0000000..9fa3f43
--- /dev/null
+++ b/tests/test_layer_state_only_hydration.py
@@ -0,0 +1,111 @@
+from contextlib import nullcontext
+from pathlib import Path
+from types import SimpleNamespace
+
+import contextor.core.api.facade as facade
+import contextor.core.live_state.hydration as hydration
+from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.core.domain.module import Module
+from contextor.core.repository_identity import RepositoryIdentity
+
+
+def _state(tmp_path):
+    path = tmp_path / "sample.py"
+    path.write_text("def sample():\n    return 1\n", encoding="utf-8")
+    module = Module("sample", "sample.py", str(path), [])
+    graph = SimpleNamespace(hard_edges={"sample": set()}, soft_edges={"sample": set()})
+    return RepositoryAnalysisState(
+        modules={"sample": module},
+        dependency_graph=graph,
+        artifacts={"sample": []},
+        collision_facts={"sample": []},
+        collisions_state="fresh",
+    )
+
+
+def _patch_resolution_dependencies(monkeypatch, root, *, live=None, snapshot=None):
+    identity = RepositoryIdentity("ctx_test", str(root.resolve()), root.name)
+    monkeypatch.setattr("contextor.core.repository_identity.read_repository_identity", lambda _: identity)
+    monkeypatch.setattr("contextor.core.live_state.store.migrate_legacy_snapshot", lambda _: root / "cache")
+    monkeypatch.setattr("contextor.core.live_state.store.read_metadata", lambda _: SimpleNamespace(state_id="state"))
+    monkeypatch.setattr("contextor.core.analysis.state_manager.load_engine_state", lambda *args, **kwargs: snapshot)
+    monkeypatch.setattr("contextor.core.live_state.runtime.connect", lambda _: live)
+
+
+def test_resolver_prefers_valid_live_state_over_snapshot(tmp_path, monkeypatch):
+    live_state, snapshot_state = _state(tmp_path), _state(tmp_path)
+    client = SimpleNamespace(
+        ping=lambda: {"revision": 7},
+        snapshot=lambda: {"state": live_state, "revision": 8},
+    )
+    _patch_resolution_dependencies(monkeypatch, tmp_path, live=client, snapshot=snapshot_state)
+
+    resolved = hydration.resolve_authoritative_repository_state(tmp_path)
+
+    assert resolved.state is live_state
+    assert resolved.source == "live_service"
+    assert resolved.revision == 8
+
+
+def test_resolver_uses_snapshot_when_live_is_unavailable(tmp_path, monkeypatch):
+    snapshot_state = _state(tmp_path)
+    _patch_resolution_dependencies(monkeypatch, tmp_path, snapshot=snapshot_state)
+
+    resolved = hydration.resolve_authoritative_repository_state(tmp_path)
+
+    assert resolved.state is snapshot_state
+    assert resolved.source == "snapshot"
+
+
+def test_invalid_authoritative_state_keeps_layer_on_indexed_fallback(tmp_path, monkeypatch):
+    _patch_resolution_dependencies(monkeypatch, tmp_path, snapshot=RepositoryAnalysisState())
+    assert hydration.resolve_authoritative_repository_state(tmp_path) is None
+
+
+def test_full_hydrator_still_constructs_an_incremental_engine(tmp_path, monkeypatch):
+    state = _state(tmp_path)
+    resolved = hydration.AuthoritativeRepositoryState(
+        state=state, client=None, revision=3, source="snapshot", cache_dir=tmp_path / "cache"
+    )
+    calls = []
+    monkeypatch.setattr(hydration, "resolve_authoritative_repository_state", lambda _: resolved)
+
+    class Engine:
+        def __init__(self, *args):
+            calls.append(args)
+
+    monkeypatch.setattr("contextor.core.analysis.incremental_engine.IncrementalAnalysisEngine", Engine)
+    monkeypatch.setattr("contextor.core.reporting_engine.persistent_registry.PersistentIdentityRegistry", lambda _: object())
+    monkeypatch.setattr("contextor.core.analysis.state_manager.FileStateManager", lambda _: object())
+
+    hydrated = hydration.hydrate_repository_engine(tmp_path)
+
+    assert isinstance(hydrated.engine, Engine)
+    assert len(calls) == 1
+
+
+def test_layer_uses_state_directly_without_full_engine_hydration(tmp_path, monkeypatch):
+    layer = tmp_path / "layer"
+    layer.mkdir()
+    state = _state(layer)
+    resolved = hydration.AuthoritativeRepositoryState(
+        state=state, client=None, revision=3, source="snapshot", cache_dir=tmp_path / "cache"
+    )
+    monkeypatch.setattr(facade, "resolve_authoritative_repository_state", lambda _: resolved)
+    monkeypatch.setattr(facade, "hydrate_repository_engine", lambda _: (_ for _ in ()).throw(AssertionError("full hydration used")))
+    monkeypatch.setattr(facade, "_initialize_repository_identity", lambda _: SimpleNamespace(transaction=lambda: nullcontext()))
+    monkeypatch.setattr(facade, "reset_caches", lambda: None)
+    monkeypatch.setattr(facade, "_analysis_filters", lambda *args: (set(), set()))
+    monkeypatch.setattr(facade, "_compute_metrics_and_debt", lambda *args, **kwargs: ({}, [], [], {}))
+    monkeypatch.setattr(facade, "detect_hotspots", lambda *_: [])
+    monkeypatch.setattr(facade, "generate_summary_report", lambda *args, **kwargs: {})
+    monkeypatch.setattr(facade, "generate_structure_report", lambda *args, **kwargs: {})
+    monkeypatch.setattr(facade, "canonical_artifact_report", lambda artifacts: {"artifacts": artifacts})
+    monkeypatch.setattr(facade, "compact_artifact_report", lambda *args: {})
+    monkeypatch.setattr(facade, "build_report_header", lambda *args: {})
+    monkeypatch.setattr(facade, "slice_report_for_layer", lambda **kwargs: {"summary": kwargs["global_summary"]})
+    monkeypatch.setattr("contextor.core.reporting_engine.dictionary.IndexDictionary", lambda _: object())
+    monkeypatch.setattr("contextor.core.reporting_engine.layer_pipeline.execute_layer_pipeline", lambda *args, **kwargs: None)
+    monkeypatch.setattr("contextor.core.reporting_engine.io_manager.write_layer_reports", lambda **kwargs: None)
+
+    facade.ContextorFacade.analyze_layer(str(tmp_path), str(layer))

STATE_ONLY_HYDRATION=PASS
AUTHORITATIVE_SOURCE_SELECTION_PARITY=PASS
LIVE_SOURCE_PARITY=PASS
SNAPSHOT_SOURCE_PARITY=PASS
FALLBACK_PARITY=PASS
STATE_IDENTITY_REVISION_PARITY=PASS
LAYER_OUTPUT_PARITY=PASS
B_INCREMENTAL_ENGINE_CONSTRUCTION_COUNT=0
B_MATERIALIZE_INCREMENTAL_STATE_COUNT=0
B_ENSURE_MODULE_USAGES_COUNT=0
B_SOURCE_PARSE_COUNT=0
B_SYMBOL_REFERENCE_VISITOR_COUNT=0
B_COLLISION_AST_VISITOR_COUNT=0
A_LAYER_MEDIAN_MS=16851.911
B_LAYER_MEDIAN_MS=921.121
PAIRED_LAYER_MEDIAN_DELTA_MS=-16012.588
PAIRED_LAYER_MEAN_DELTA_MS=-16308.581
TESTS=12 passed in 0.75s
CONTEXTOR_WORKSPACE_SYNC=verified
FILES_CHANGED=C:\Temp\Contextor_Repo\contextor\core\api\facade.py;C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py;C:\Temp\Contextor_Repo\contextor\core\live_state\__init__.py;C:\Temp\Contextor_Repo\tests\test_layer_collision_reuse.py;C:\Temp\Contextor_Repo\tests\test_layer_state_only_hydration.py
REPORT_COMPLETENESS=PASS
MISSING_DIFFS=NONE
FINAL_VERDICT=PASS
WHY=Complete current-tree raw diffs are appended; focused tests and six-pair A/B evidence pass; desktop watcher revisions 120-125 continuously synchronize all five changed files.

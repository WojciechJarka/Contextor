# CPA_CANONICAL_STAR_IMPORT_UNIFIED_SEMANTICS

STATUS=STEP_PASS
HEAD_BEFORE=0d91a6f696f738ab87c46edb738cb6c5817a1119
HEAD_AT_REPORT=0d91a6f696f738ab87c46edb738cb6c5817a1119
WORKTREE_BEFORE=CLEAN
WORKTREE_AT_REPORT=M contextor/core/analysis/incremental/plan_executor.py
 M contextor/core/reference/index.py
 M contextor/core/reference/shared.py
 M tests/test_completeness_freshness_parity_proof.py
 M tests/test_reexport_reference_semantics.py

CANONICAL_STAR_IMPORT_CONTRACT
Explicit __all__ exports only statically resolvable listed names, including explicitly listed underscore names. Without __all__, statically known non-underscore bindings are visible. Re-export aliases project to canonical origins. An explicit __all__ also creates a consumer -> source::__all__ api_imports metadata edge when that canonical target exists; __all__ is not itself a star-exported name.

CANONICAL_OWNER
Shared pure-RAM export-surface assembly lives in contextor/core/reference/shared.py. Full projection is RepositoryReferenceIndex.from_compact_facts/build_symbol_references in contextor/core/reference/index.py. Incremental projection is _rebuild_consumer_slice, called twice by execute_refresh_plan in contextor/core/analysis/incremental/plan_executor.py. Contextor artifact_consumption lineage identified RepositoryAnalysisState.artifact_consumption as the canonical owner, build_canonical_artifact_consumption as the full producer, and _rebuild_consumer_slice as the incremental producer.

SHARED_EXPORT_SURFACE
Extracted _assemble_module_export_surfaces(reexport_facts_by_module) returning exporter -> visible local name -> target dotted identity. The common in-memory assembly preserves the prior fixed-point star-source propagation and cycle-safe raw-reexport resolution; no source, AST, stat, or filesystem operation occurs in this assembly. _assemble_reexport_map retains its dict[str, str] output and resolves the raw map through the shared assembly state.

FULL_SCAN_PROJECTION
RepositoryReferenceIndex.from_compact_facts stores module_export_surfaces and explicit_all_modules as run-scoped derived fields. build_symbol_references projects star consumers only when the canonical target is in the source export surface, or when the exact symbol is explicit __all__ metadata for a source that defines it. The broad source-prefix visibility branch was removed.

INCREMENTAL_PROJECTION
execute_refresh_plan assembles reexports and export surfaces once each for the candidate facts and passes both, plus reexport facts, to each consumer-slice reconstruction. _rebuild_consumer_slice identifies all star sources from canonical reference_evidence api_imports targets ending in .*; it expands every source surface, resolves canonical dotted targets, adds api_imports edges, and skips generic projection of the synthetic source.* target.

ALL_METADATA_DEPENDENCY
Full path: explicit_all_modules plus an exact source.__all__ metadata branch.
Incremental path: for each star source, only non-None explicit_all facts trigger exact source.__all__ target resolution; unresolved targets are not fabricated. Existing api_imports channel is used.

MULTIPLE_STAR_IMPORTS
PASS. The dedicated full-scan test projects both a::alpha and b::beta from two distinct star-import facts; detection does not use the singular aliases['*'] entry.

FULL_COMPACT_PARITY
PASS. tests/test_reference_fusion_semantic_core.py::test_ast_build_exactly_equals_compact_facts_build passed. Its _normalized comparison includes every RepositoryReferenceIndex instance field except modules and root_path, so module_export_surfaces and explicit_all_modules are included.

LIVE_FULL_PARITY
PASS. The existing all-only LIVE parity node and new explicit -> empty -> absent __all__ update node passed. The new test compares _assert_full_parity after each update and checks a::imported, b::PUBLIC, b::_PRIVATE, and b::__all__; the explicit-all metadata edge is retained for empty __all__, then removed when __all__ is removed.

SOURCE_IO_PROOF
PASS. Existing all-only guard observed zero Module.ast_tree accesses and zero _get_cached_ast calls during update. It also observed exactly one _assemble_reexport_map and one _assemble_module_export_surfaces call, each receiving the complete candidate reexport-facts domain. git diff --check passed (Git emitted only its configured LF/CRLF conversion warnings).

DIRECT_EVIDENCE
- Contextor canonical_revision=1511; the three edited production modules had fresh syntax diagnostics and exact fetched source reported workspace_sync=verified. The artifact_consumption lineage reported canonical_state=fresh, provenance=live, resync_required=false.
- Contextor lineage named full and incremental canonical artifact_consumption owners/producers. Contextor caller context showed execute_refresh_plan -> _rebuild_consumer_slice at both call sites, lines 855 and 948 before edits.
- Literal source at HEAD contained the broad full star-import prefix check, the one-time incremental reexport assembly, and no incremental wildcard expansion. HEAD source matched the inspected Contextor source; WORKTREE_BEFORE was clean.
- Focused full-scan canonical tests prove explicit-all, empty-all, implicit-public-only/private-filter, metadata, and multiple-star behavior.
- No full repository pytest suite, actual-repository full analysis, MCP update_file, or manual MCP/Desktop restart was run.

TEST_FILE
tests/test_reexport_reference_semantics.py
tests/test_reference_fusion_semantic_core.py (existing parity gate, unchanged)
tests/test_completeness_freshness_parity_proof.py

TEST_NODE_ID
New full gates:
- tests/test_reexport_reference_semantics.py::test_full_star_import_uses_explicit_all_and_tracks_metadata
- tests/test_reexport_reference_semantics.py::test_full_star_import_empty_all_exports_only_metadata
- tests/test_reexport_reference_semantics.py::test_full_star_import_without_all_exports_public_bindings_only
- tests/test_reexport_reference_semantics.py::test_full_multiple_star_imports_project_each_source_module
New LIVE gate:
- tests/test_completeness_freshness_parity_proof.py::test_star_import_visibility_changes_match_full_oracle
Existing compact parity gate:
- tests/test_reference_fusion_semantic_core.py::test_ast_build_exactly_equals_compact_facts_build
Existing re-export semantics:
- tests/test_reexport_reference_semantics.py::test_star_reexport_uses_explicit_all_and_remains_transitive
- tests/test_reexport_reference_semantics.py::test_direct_star_reexport_includes_public_source_definition
- tests/test_reexport_reference_semantics.py::test_cyclic_reexports_are_not_resolved_arbitrarily
Existing LIVE and propagation gates:
- tests/test_completeness_freshness_parity_proof.py::test_reexport_all_only_change_is_ram_only_and_matches_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_transitive_reexport_late_provider_matches_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_reexport_retarget_matches_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_natural_ambiguity_transition_matches_full_oracle_state
- tests/test_completeness_freshness_parity_proof.py::test_transitive_reexport_symbol_remove_matches_full_oracle

TEST_RESULT
PASS: all 14 required focused node IDs passed in one bounded pytest invocation (14 passed in 31.21s). After adding the export-surface assembler spy to the existing all-only guard, that exact node was rerun and passed (1 passed in 7.38s). git diff --check passed. No full suite was run.

TARGETED_TESTS
Only the named focused pytest node IDs listed above were run. Windows pytest commands were each entered on one physical line without caret continuation.

MCP_RESTART_REQUIRED
YES_FOR_ACTIVE_LONG_LIVED_BACKEND_TO_LOAD_CHANGED_CORE_MODULES (INFERENCE: edited Python implementation is imported in-process; active backend identity/reload behavior was not tested). No restart was performed.

FULL_ANALYSIS_REQUIRED_AFTER_RESTART
YES_FOR_EXISTING_CANONICAL_STATE_BEFORE_CLAIMING_NEW_STAR_SEMANTICS (INFERENCE: persisted canonical artifact_consumption predates this source change). No full analysis was run on the real repository.

REQUIRED_CERTIFICATION
FULL_STAR_IMPORT_EXPLICIT_ALL=PASS
FULL_STAR_IMPORT_EMPTY_ALL=PASS
FULL_STAR_IMPORT_IMPLICIT_PUBLIC_ONLY=PASS
FULL_STAR_IMPORT_PRIVATE_FILTER=PASS
ALL_METADATA_DEPENDENCY=PASS
MULTIPLE_STAR_IMPORTS=PASS
FULL_COMPACT_REFERENCE_PARITY=PASS
LIVE_STAR_IMPORT_PROJECTION=PASS
LIVE_FULL_STAR_IMPORT_PARITY=PASS
TRANSITIVE_REEXPORT_REGRESSIONS=PASS
SYMBOL_REMOVE_BOUNDED_EXECUTION=PASS
INCREMENTAL_BUILD_REEXPORT_SOURCE_IO=ZERO
UNCHANGED_MODULE_AST_ACCESSES=ZERO

CLASSIFICATION=CANONICAL_STAR_IMPORT_UNIFIED_SEMANTICS_CERTIFIED_FOR_CURRENT_GATES
STATUS=STEP_PASS

FILES_CHANGED
- contextor/core/reference/shared.py
- contextor/core/reference/index.py
- contextor/core/analysis/incremental/plan_executor.py
- tests/test_reexport_reference_semantics.py
- tests/test_completeness_freshness_parity_proof.py

FULL_DIFFS
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index e261ce6..47606e1 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -28,6 +28,7 @@ from contextor.core.domain.refresh_plan import RefreshPlan
 from contextor.core.domain.usage_facts import ModuleUsageFacts
 from contextor.core.graph.graph import build_trie, detect_package_root, build_graph, resolve_module_edges
 from contextor.core.reference.shared import (
+    _assemble_module_export_surfaces,
     _assemble_reexport_map,
     validate_reexport_facts_by_module,
 )
@@ -395,6 +396,8 @@ def _rebuild_consumer_slice(
     candidate_consumption: Dict[str, Any],
     candidate_artifacts: Mapping[str, Any],
     reexports: Mapping[str, str],
+    reexport_facts_by_module: Mapping[str, Any],
+    module_export_surfaces: Mapping[str, Mapping[str, str]],
     expected_targets: Optional[Set[str]] = None,
     dotted_target_index: Optional[
         Mapping[str, Tuple[str, ...]]
@@ -450,6 +453,61 @@ def _rebuild_consumer_slice(
     )
 
     rebuilt_targets: Dict[str, Set[str]] = {}
+
+    star_sources = sorted(
+        {
+            target[:-2]
+            for target, channel, *_rest
+            in consumer_facts.reference_evidence
+            if channel == "api_imports"
+            and target.endswith(".*")
+        }
+    )
+
+    for star_source in star_sources:
+        for dotted_target in module_export_surfaces.get(
+            star_source,
+            {},
+        ).values():
+            resolved_target = _resolve_reexport(
+                dotted_target,
+                reexports,
+            )
+            targets, status = _resolve_canonical_target_keys(
+                resolved_target,
+                candidate_consumption,
+                candidate_artifacts,
+                expected_targets=expected_targets,
+                dotted_target_index=dotted_target_index,
+            )
+            if status == "resolved":
+                for target in targets:
+                    rebuilt_targets.setdefault(
+                        target,
+                        set(),
+                    ).add("api_imports")
+
+        reexport_facts = reexport_facts_by_module.get(
+            star_source
+        )
+        if (
+            reexport_facts is not None
+            and reexport_facts.get("explicit_all") is not None
+        ):
+            targets, status = _resolve_canonical_target_keys(
+                f"{star_source}.__all__",
+                candidate_consumption,
+                candidate_artifacts,
+                expected_targets=expected_targets,
+                dotted_target_index=dotted_target_index,
+            )
+            if status == "resolved":
+                for target in targets:
+                    rebuilt_targets.setdefault(
+                        target,
+                        set(),
+                    ).add("api_imports")
+
     for sym, ch_name in c_tagged:
         raw_t = _resolve_reexport(
             _resolve_alias(
@@ -458,6 +516,13 @@ def _rebuild_consumer_slice(
             ),
             reexports,
         )
+        if (
+            ch_name == "api_imports"
+            and raw_t
+            and raw_t.endswith(".*")
+        ):
+            continue
+
         if (
             ch_name == "api_imports"
             and raw_t in candidate_artifacts
@@ -813,6 +878,7 @@ def execute_refresh_plan(
         executed_reparse.append(reparse_mod)
 
     reexports = None
+    module_export_surfaces = None
     if (
         plan.recompute_modules
         or "artifact_consumption" in plan.patch_families
@@ -820,6 +886,9 @@ def execute_refresh_plan(
         reexports = _assemble_reexport_map(
             candidate.reexport_facts_by_module
         )
+        module_export_surfaces = _assemble_module_export_surfaces(
+            candidate.reexport_facts_by_module
+        )
 
     # 3. RECOMPUTE - re-evaluate planned cached modules in RAM without source I/O
     executed_recompute: List[str] = []
@@ -858,6 +927,8 @@ def execute_refresh_plan(
                 candidate_consumption=candidate.artifact_consumption,
                 candidate_artifacts=candidate.artifacts,
                 reexports=reexports,
+                reexport_facts_by_module=candidate.reexport_facts_by_module,
+                module_export_surfaces=module_export_surfaces,
                 expected_targets=expected_targets,
                 dotted_target_index=dotted_target_index,
                 consumer_target_index=consumer_target_index,
@@ -951,6 +1022,8 @@ def execute_refresh_plan(
                     candidate_consumption=candidate.artifact_consumption,
                     candidate_artifacts=candidate.artifacts,
                     reexports=reexports,
+                    reexport_facts_by_module=candidate.reexport_facts_by_module,
+                    module_export_surfaces=module_export_surfaces,
                     expected_targets=expected_targets,
                     dotted_target_index=dotted_target_index,
                     consumer_target_index=consumer_target_index,
diff --git a/contextor/core/reference/index.py b/contextor/core/reference/index.py
index 8e7888a..8c60d4a 100644
--- a/contextor/core/reference/index.py
+++ b/contextor/core/reference/index.py
@@ -31,6 +31,7 @@ from .resolution import (
     _resolve_reexport,
 )
 from .shared import (
+    _assemble_module_export_surfaces,
     _assemble_reexport_map,
     _empty_reference,
     _extract_reexport_facts,
@@ -371,6 +372,8 @@ class RepositoryReferenceIndex:
         modules: dict,
         root_path: str,
         reexports: dict[str, str],
+        module_export_surfaces: dict[str, dict[str, str]],
+        explicit_all_modules: frozenset[str],
         direct_calls_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]],
         instance_calls_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]],
         callbacks_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]],
@@ -388,6 +391,8 @@ class RepositoryReferenceIndex:
         self.modules = modules
         self.root_path = root_path
         self.reexports = reexports
+        self.module_export_surfaces = module_export_surfaces
+        self.explicit_all_modules = explicit_all_modules
         self.direct_calls_by_target = direct_calls_by_target
         self.instance_calls_by_target = instance_calls_by_target
         self.callbacks_by_target = callbacks_by_target
@@ -453,6 +458,14 @@ class RepositoryReferenceIndex:
         reexports = _assemble_reexport_map(
             reexport_facts_by_module
         )
+        module_export_surfaces = _assemble_module_export_surfaces(
+            reexport_facts_by_module
+        )
+        explicit_all_modules = frozenset(
+            module_id
+            for module_id, facts in reexport_facts_by_module.items()
+            if facts.get("explicit_all") is not None
+        )
 
         direct_calls_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]] = defaultdict(list)
         instance_calls_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]] = defaultdict(list)
@@ -560,6 +573,8 @@ class RepositoryReferenceIndex:
             modules=modules,
             root_path=root_path,
             reexports=reexports,
+            module_export_surfaces=module_export_surfaces,
+            explicit_all_modules=explicit_all_modules,
             direct_calls_by_target=dict(direct_calls_by_target),
             instance_calls_by_target=dict(instance_calls_by_target),
             callbacks_by_target=dict(callbacks_by_target),
@@ -632,10 +647,19 @@ class RepositoryReferenceIndex:
 
             # 8. Star Imports
             for source_prefix, consumers in self.star_imports_by_source.items():
-                if symbol.startswith(source_prefix + ".") or any(
-                    exported.startswith(source_prefix + ".") and orig == symbol
-                    for exported, orig in self.reexports.items()
-                ):
+                visible_targets = self.module_export_surfaces.get(
+                    source_prefix,
+                    {},
+                )
+                is_visible_export = any(
+                    _resolve_reexport(target, self.reexports) == symbol
+                    for target in visible_targets.values()
+                )
+                is_all_metadata = (
+                    source_prefix in self.explicit_all_modules
+                    and symbol == f"{source_prefix}.__all__"
+                )
+                if is_visible_export or is_all_metadata:
                     rec["imported_from"].extend(consumers)
 
             # 9. Ambiguous Calls for leaf
diff --git a/contextor/core/reference/shared.py b/contextor/core/reference/shared.py
index 92423a0..0b44f4f 100644
--- a/contextor/core/reference/shared.py
+++ b/contextor/core/reference/shared.py
@@ -267,12 +267,11 @@ def _extract_reexport_facts(
     }
 
 
-def _assemble_reexport_map(
+def _assemble_export_surface_state(
     reexport_facts_by_module: dict[str, dict[str, Any]],
-) -> dict[str, str]:
+) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
     """
-    Assemble cycle-safe transitive re-export identities from complete
-    source-local re-export facts.
+    Assemble visible module exports and their raw re-export identities.
 
     Performs no source or filesystem I/O.
     """
@@ -364,6 +363,27 @@ def _assemble_reexport_map(
                     )[local] = target
                     changed = True
 
+    return module_exports, raw
+
+
+def _assemble_module_export_surfaces(
+    reexport_facts_by_module: dict[str, dict[str, Any]],
+) -> dict[str, dict[str, str]]:
+    """Assemble visible local exports and their source target identities."""
+    module_exports, _raw = _assemble_export_surface_state(
+        reexport_facts_by_module
+    )
+    return module_exports
+
+
+def _assemble_reexport_map(
+    reexport_facts_by_module: dict[str, dict[str, Any]],
+) -> dict[str, str]:
+    """Assemble cycle-safe transitive re-export identities from source facts."""
+    _module_exports, raw = _assemble_export_surface_state(
+        reexport_facts_by_module
+    )
+
     resolved: dict[str, str] = {}
 
     for key, initial in raw.items():
diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index 345e5b3..b14b0b9 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -1395,8 +1395,12 @@ def test_reexport_all_only_change_is_ram_only_and_matches_full_oracle(
     import contextor.core.domain.module as module_domain
 
     assembled_domains = []
+    surface_domains = []
     ast_accesses = []
     original_assembler = plan_executor._assemble_reexport_map
+    original_surface_assembler = (
+        plan_executor._assemble_module_export_surfaces
+    )
 
     def assemble_spy(facts_by_module):
         assert isinstance(facts_by_module, dict)
@@ -1404,6 +1408,12 @@ def test_reexport_all_only_change_is_ram_only_and_matches_full_oracle(
         assembled_domains.append(deepcopy(facts_by_module))
         return original_assembler(facts_by_module)
 
+    def assemble_surface_spy(facts_by_module):
+        assert isinstance(facts_by_module, dict)
+        assert set(facts_by_module) == set(engine.state.modules)
+        surface_domains.append(deepcopy(facts_by_module))
+        return original_surface_assembler(facts_by_module)
+
     def fail_ast_access(*args, **kwargs):
         ast_accesses.append((args, kwargs))
         raise AssertionError(
@@ -1416,6 +1426,11 @@ def test_reexport_all_only_change_is_ram_only_and_matches_full_oracle(
             "_assemble_reexport_map",
             side_effect=assemble_spy,
         ),
+        patch.object(
+            plan_executor,
+            "_assemble_module_export_surfaces",
+            side_effect=assemble_surface_spy,
+        ),
         patch.object(
             Module,
             "ast_tree",
@@ -1432,6 +1447,8 @@ def test_reexport_all_only_change_is_ram_only_and_matches_full_oracle(
     assert ast_accesses == []
     assert len(assembled_domains) == 1
     assert set(assembled_domains[0]) == set(engine.state.modules)
+    assert len(surface_domains) == 1
+    assert set(surface_domains[0]) == set(engine.state.modules)
     assert all(
         isinstance(fact, dict)
         for fact in assembled_domains[0].values()
@@ -2060,3 +2077,100 @@ def test_fail_closed_on_unsupported_plan_item(tmp_path):
                 {},
                 ModuleUsageFacts(),
             )
+
+
+def test_star_import_visibility_changes_match_full_oracle(tmp_path, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    provider = tmp_path / "a.py"
+    reexporter = tmp_path / "b.py"
+    consumer = tmp_path / "c.py"
+    provider.write_text(
+        "def imported():\n"
+        "    pass\n",
+        encoding="utf-8",
+    )
+    reexporter.write_text(
+        "from a import imported\n"
+        "PUBLIC = 1\n"
+        "_PRIVATE = 2\n"
+        "__all__ = ['imported', 'PUBLIC']\n",
+        encoding="utf-8",
+    )
+    consumer.write_text(
+        "from b import *\n",
+        encoding="utf-8",
+    )
+
+    errors, _ = ContextorFacade().analyze_project(str(tmp_path))
+    assert not errors, errors
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    engine = hydrated.engine
+
+    def assert_star_projection(
+        state,
+        imported_channels,
+        public_channels,
+        private_channels,
+        all_channels,
+        all_target_exists=True,
+    ):
+        assert state.artifact_consumption.get(
+            "a::imported", {}
+        ).get("channels", {}).get("c", []) == imported_channels
+        assert state.artifact_consumption.get(
+            "b::PUBLIC", {}
+        ).get("channels", {}).get("c", []) == public_channels
+        assert state.artifact_consumption.get(
+            "b::_PRIVATE", {}
+        ).get("channels", {}).get("c", []) == private_channels
+        assert ("b::__all__" in state.artifact_consumption) is all_target_exists
+        assert state.artifact_consumption.get(
+            "b::__all__", {}
+        ).get("channels", {}).get("c", []) == all_channels
+
+    assert_star_projection(
+        engine.state,
+        ["api_imports"],
+        ["api_imports"],
+        [],
+        ["api_imports"],
+    )
+
+    reexporter.write_text(
+        "from a import imported\n"
+        "PUBLIC = 1\n"
+        "_PRIVATE = 2\n"
+        "__all__ = []\n",
+        encoding="utf-8",
+    )
+    empty_all_result = engine.update_file(str(reexporter))
+    assert "c" in empty_all_result.execution_trace["recompute_modules"]
+    empty_all_oracle = _build_full_static_state(tmp_path)
+    _assert_full_parity(engine.state, empty_all_oracle)
+    assert_star_projection(
+        engine.state,
+        [],
+        [],
+        [],
+        ["api_imports"],
+    )
+
+    reexporter.write_text(
+        "from a import imported\n"
+        "PUBLIC = 1\n"
+        "_PRIVATE = 2\n",
+        encoding="utf-8",
+    )
+    implicit_all_result = engine.update_file(str(reexporter))
+    assert "c" in implicit_all_result.execution_trace["recompute_modules"]
+    implicit_all_oracle = _build_full_static_state(tmp_path)
+    _assert_full_parity(engine.state, implicit_all_oracle)
+    assert_star_projection(
+        engine.state,
+        ["api_imports"],
+        ["api_imports"],
+        [],
+        [],
+        all_target_exists=False,
+    )
diff --git a/tests/test_reexport_reference_semantics.py b/tests/test_reexport_reference_semantics.py
index 843a2a7..fb989fb 100644
--- a/tests/test_reexport_reference_semantics.py
+++ b/tests/test_reexport_reference_semantics.py
@@ -6,6 +6,45 @@ from contextor.core.reporting_layer.artifact_usage_report import (
     collect_module_artifacts,
 )
 from contextor.core.symbol_engine.indexer import index_repository
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.live_state.hydration import hydrate_repository_engine
+
+
+def _full_canonical_state(tmp_path, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    errors, _ = ContextorFacade().analyze_project(str(tmp_path))
+    assert not errors, errors
+
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    return hydrated.engine.state
+
+
+def _write_star_visibility_fixture(tmp_path, explicit_all):
+    (tmp_path / "a.py").write_text(
+        "def imported():\n"
+        "    pass\n",
+        encoding="utf-8",
+    )
+    source = (
+        "from a import imported\n"
+        "PUBLIC = 1\n"
+        "_PRIVATE = 2\n"
+    )
+    if explicit_all is not None:
+        source += f"__all__ = {explicit_all!r}\n"
+    (tmp_path / "b.py").write_text(source, encoding="utf-8")
+    (tmp_path / "c.py").write_text(
+        "from b import *\n",
+        encoding="utf-8",
+    )
+
+
+def _star_channels(state, target, consumer="c"):
+    return state.artifact_consumption.get(target, {}).get(
+        "channels",
+        {},
+    ).get(consumer, [])
 
 
 def test_transitive_aliased_reexport_resolves_to_original_artifact(tmp_path):
@@ -230,3 +269,75 @@ def test_repeated_all_dynamic_then_literal_uses_last_assignment(
     assert mapping["facade.run"] == (
         "provider.run"
     )
+
+
+def test_full_star_import_uses_explicit_all_and_tracks_metadata(tmp_path, monkeypatch):
+    _write_star_visibility_fixture(
+        tmp_path,
+        ["imported", "PUBLIC"],
+    )
+
+    state = _full_canonical_state(tmp_path, monkeypatch)
+
+    assert _star_channels(state, "a::imported") == ["api_imports"]
+    assert _star_channels(state, "b::PUBLIC") == ["api_imports"]
+    assert _star_channels(state, "b::_PRIVATE") == []
+    assert _star_channels(state, "b::__all__") == ["api_imports"]
+
+
+def test_full_star_import_empty_all_exports_only_metadata(tmp_path, monkeypatch):
+    _write_star_visibility_fixture(tmp_path, [])
+
+    state = _full_canonical_state(tmp_path, monkeypatch)
+
+    assert _star_channels(state, "a::imported") == []
+    assert _star_channels(state, "b::PUBLIC") == []
+    assert _star_channels(state, "b::_PRIVATE") == []
+    assert _star_channels(state, "a::imported", consumer="b") == [
+        "api_imports"
+    ]
+    assert _star_channels(state, "b::__all__") == ["api_imports"]
+
+
+def test_full_star_import_without_all_exports_public_bindings_only(
+    tmp_path,
+    monkeypatch,
+):
+    _write_star_visibility_fixture(tmp_path, None)
+
+    state = _full_canonical_state(tmp_path, monkeypatch)
+
+    assert _star_channels(state, "a::imported") == ["api_imports"]
+    assert _star_channels(state, "b::PUBLIC") == ["api_imports"]
+    assert _star_channels(state, "b::_PRIVATE") == []
+    assert "b::__all__" not in state.artifact_consumption
+
+
+def test_full_multiple_star_imports_project_each_source_module(
+    tmp_path,
+    monkeypatch,
+):
+    (tmp_path / "a.py").write_text(
+        "def alpha():\n"
+        "    pass\n"
+        "_A_PRIVATE = 1\n",
+        encoding="utf-8",
+    )
+    (tmp_path / "b.py").write_text(
+        "def beta():\n"
+        "    pass\n"
+        "_B_PRIVATE = 2\n",
+        encoding="utf-8",
+    )
+    (tmp_path / "c.py").write_text(
+        "from a import *\n"
+        "from b import *\n",
+        encoding="utf-8",
+    )
+
+    state = _full_canonical_state(tmp_path, monkeypatch)
+
+    assert _star_channels(state, "a::alpha") == ["api_imports"]
+    assert _star_channels(state, "b::beta") == ["api_imports"]
+    assert _star_channels(state, "a::_A_PRIVATE") == []
+    assert _star_channels(state, "b::_B_PRIVATE") == []

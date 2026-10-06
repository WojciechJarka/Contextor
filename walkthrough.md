# CPA_PACKAGE_INIT_CANONICAL_REFERENCE_IDENTITY

STATUS=STEP_PASS
CLASSIFICATION=PACKAGE_INIT_CANONICAL_REFERENCE_IDENTITY_CERTIFIED
HEAD_BEFORE=e32b7ae9bbfff18ddb57057507e60eddc88c76f6
HEAD_AT_REPORT=e32b7ae9bbfff18ddb57057507e60eddc88c76f6
WORKTREE_BEFORE=CLEAN (git status --short empty before edits).

## CANONICAL_PACKAGE_IDENTITY_CONTRACT

CONTRACT_PROVED: Canonical artifact identities remain pkg.__init__::PUBLIC and pkg.__init__::__all__. External pkg.PUBLIC and pkg.__all__ map to the indexed initializer identity. Module IDs, persistent IDs, artifact target schema, snapshot schema, and persisted reexport facts were not changed.

DIRECT_EVIDENCE: Full fixtures identify pkg/__init__.py as module pkg.__init__, while the consumer import source remains pkg. New tests assert package-local canonical targets.

## SHARED_CANONICALIZER

Owner: contextor/core/reference/shared.py::_canonicalize_package_reference_target.

CODE_PATH_PROVED: Pure-RAM dotted-name mapping. Accepts module mappings or module-ID iterables. Checks the longest existing module prefix first; existing real submodules win. No source reads, AST, filesystem I/O, or stat.

DIRECT_EVIDENCE: The helper test passes:
pkg.PUBLIC -> pkg.__init__.PUBLIC
pkg.__all__ -> pkg.__init__.__all__
pkg.provider.run -> pkg.provider.run
pkg.sub.VALUE -> pkg.sub.__init__.VALUE
pkg.sub.__all__ -> pkg.sub.__init__.__all__

PACKAGE_EXTERNAL_TO_INIT_CANONICALIZATION=PASS
REAL_SUBMODULE_PRECEDENCE=PASS

## FULL_REFERENCE_CANONICALIZATION

CODE_PATH_PROVED: RepositoryReferenceIndex.from_compact_facts canonicalizes resolved and candidate calls, callbacks, events, inheritance, qualified refs, and direct imports after _resolve_reexport. Star import source keys remain external Python spelling. build_symbol_references canonicalizes visible targets and explicit-all source/metadata identity before comparison; channel remains api_imports.

FULL_REFERENCE_CANONICALIZATION=PASS

## INCREMENTAL_TARGET_CANONICALIZATION

CODE_PATH_PROVED: _resolve_canonical_target_keys keeps exact canonical :: inputs unchanged, then canonicalizes dotted targets before both indexed and fallback lookup. No short-name fallback was added; dotted ambiguity behavior is retained. Contextor confirmed candidate_artifacts is module-keyed data accepted by this helper.

INCREMENTAL_TARGET_CANONICALIZATION=PASS

## PROPAGATION_CANONICALIZATION

CODE_PATH_PROVED: _find_dependent_consumers resolves aliases, canonicalizes against the usage module domain, then applies existing exact module-boundary comparisons. pkg and pkg.* map through pkg.__init__; pkg.provider.run remains under the real submodule prefix.

PROPAGATION_CANONICALIZATION=PASS

## NAMED_PACKAGE_IMPORT

DIRECT_EVIDENCE: Fresh full canonical fixture records pkg.__init__::public with consumer as consumer and both api_imports and direct_calls channels. It is not ambiguous-only.

NAMED_PACKAGE_LOCAL_IMPORT=PASS
NAMED_PACKAGE_LOCAL_CALL=PASS

NAMED_PACKAGE_LIVE_TRIGGER=PASS_EXISTING_ARTIFACT_ADDITION
DIRECT_EVIDENCE: An exploratory body-only return-value change did not activate recompute_modules. No new trigger was designed. The final LIVE regression adds a new package symbol through the existing artifacts_added structural trigger, retains pkg.__init__::public, recomputes consumer, and matches fresh full parity.

## PACKAGE_STAR_SEMANTICS

DIRECT_EVIDENCE from fresh full canonical fixtures:
- Explicit __all__=["PUBLIC"]: pkg.__init__::PUBLIC -> consumer/api_imports; _PRIVATE has no consumer; pkg.__init__::__all__ -> consumer/api_imports metadata.
- Empty __all__: PUBLIC and _PRIVATE have no consumer; __all__ remains consumer/api_imports metadata.
- No __all__: PUBLIC -> consumer/api_imports; _PRIVATE has no consumer; pkg.__init__::__all__ is absent.

PACKAGE_STAR_EXPLICIT_ALL=PASS
PACKAGE_STAR_EMPTY_ALL=PASS
PACKAGE_STAR_IMPLICIT_PUBLIC_ONLY=PASS
PACKAGE_ALL_METADATA_DEPENDENCY=PASS

## PACKAGE_REEXPORT_PROVIDER

DIRECT_EVIDENCE: Package star re-export keeps canonical origin pkg.provider::run, includes consumer on api_imports, and creates no pkg.__init__::run artifact.

PACKAGE_REEXPORT_PROVIDER_API_ORIGIN=PASS
DEFERRED_STAR_BOUND_CALL_RESOLUTION=DEFERRED_TO_AST_SEMANTIC_COVERAGE_AUDIT
CONTRACT_PROVED: Confirmed direct_calls after a bare wildcard-imported call is explicitly outside this package identity patch.

## PACKAGE_LIVE_PARITY

DIRECT_EVIDENCE: Full baseline was hydrated, then normal engine.update_file(pkg/__init__.py) applied ["PUBLIC"] -> [] -> no __all__. A fresh full oracle and _assert_full_parity passed after each update.

PACKAGE_LIVE_FULL_PARITY=PASS
PACKAGE_INIT_RECOMPUTE_SEED=PASS
DIRECT_EVIDENCE: consumer appears in execution_trace.recompute_modules on both visibility updates.

DIRECT_EVIDENCE: Initial focused run found incremental/full metadata mismatch: full state had consumer on pkg.__init__::__all__, incremental state did not. Contextor source showed _rebuild_consumer_slice looked up facts by external star_source pkg although facts were keyed pkg.__init__. The in-scope plan_executor path now canonicalizes this facts lookup; final parity gates pass.

## SOURCE_IO_PROOF

DIRECT_EVIDENCE: Existing test_reexport_all_only_change_is_ram_only_and_matches_full_oracle passed. It guards both Module.ast_tree and _get_cached_ast to fail on access and asserts the recorded access list remains empty during incremental re-export update.

INCREMENTAL_BUILD_REEXPORT_SOURCE_IO=ZERO
UNCHANGED_MODULE_AST_ACCESSES=ZERO

## LIVE_CONTEXTOR_EVIDENCE

DIRECT_EVIDENCE: Pre-edit LIVE revision 1517. Desktop watcher emitted update_file/UPDATED events for all six modified files through revision 1525; continuity=continuous and resync_required=false. At revision 1525, Contextor source freshness was canonical_state=fresh, workspace_sync=verified, syntax diagnostics=fresh with zero errors for the shared canonicalizer and incremental consumer-slice path; the refresh-planner blast-radius query was also fresh and verified. No MCP update_file or restart was used.

## TARGETED_TESTS

New package identity/LIVE nodes (8):
- tests/test_reexport_reference_semantics.py::test_package_reference_canonicalizer_prefers_longest_module_prefix
- tests/test_reexport_reference_semantics.py::test_named_package_local_import_uses_init_canonical_identity
- tests/test_reexport_reference_semantics.py::test_package_star_explicit_all_uses_init_canonical_identity
- tests/test_reexport_reference_semantics.py::test_package_star_empty_all_keeps_only_metadata_dependency
- tests/test_reexport_reference_semantics.py::test_package_star_without_all_exports_public_only
- tests/test_reexport_reference_semantics.py::test_package_star_reexport_keeps_provider_api_origin
- tests/test_completeness_freshness_parity_proof.py::test_package_init_star_visibility_changes_match_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_named_package_local_import_update_matches_full_oracle

Previous 14 unified-star gates:
- tests/test_reexport_reference_semantics.py::test_full_star_import_uses_explicit_all_and_tracks_metadata
- tests/test_reexport_reference_semantics.py::test_full_star_import_empty_all_exports_only_metadata
- tests/test_reexport_reference_semantics.py::test_full_star_import_without_all_exports_public_bindings_only
- tests/test_reexport_reference_semantics.py::test_full_multiple_star_imports_project_each_source_module
- tests/test_reference_fusion_semantic_core.py::test_ast_build_exactly_equals_compact_facts_build
- tests/test_reexport_reference_semantics.py::test_star_reexport_uses_explicit_all_and_remains_transitive
- tests/test_reexport_reference_semantics.py::test_direct_star_reexport_includes_public_source_definition
- tests/test_reexport_reference_semantics.py::test_cyclic_reexports_are_not_resolved_arbitrarily
- tests/test_completeness_freshness_parity_proof.py::test_reexport_all_only_change_is_ram_only_and_matches_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_transitive_reexport_late_provider_matches_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_reexport_retarget_matches_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_natural_ambiguity_transition_matches_full_oracle_state
- tests/test_completeness_freshness_parity_proof.py::test_transitive_reexport_symbol_remove_matches_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_star_import_visibility_changes_match_full_oracle

## TEST_RESULTS

- New package identity/LIVE gates: 8 passed.
- Previous unified-star gates: 14 passed.
- git diff --check for the six production/test files: PASS, no whitespace errors.
- Unscoped git diff --check reports trailing-space rows in walkthrough.md because complete raw Git diffs are embedded there; these are diff-context rows in the report, not whitespace errors in the six production/test files.
- Full repository pytest suite: NOT RUN, per policy.

DIRECT_EVIDENCE: The initial focused run had six full/helper passes and two LIVE failures. It exposed the package __all__ facts-key mismatch and showed that body-only return-value change did not activate an existing recompute trigger. After the in-scope incremental facts-lookup correction and switching the named LIVE fixture to an existing structural artifact-addition trigger, all eight new gates passed. The 14 earlier gates passed unchanged.

## FILES_CHANGED

- contextor/core/reference/shared.py
- contextor/core/reference/index.py
- contextor/core/analysis/incremental/plan_executor.py
- contextor/core/analysis/refresh_planner.py
- tests/test_reexport_reference_semantics.py
- tests/test_completeness_freshness_parity_proof.py

## RESTART

MCP_RESTART_REQUIRED=YES_AFTER_STEP
MCP_RESTART_PERFORMED=NO
FULL_ANALYSIS_REQUIRED_AFTER_RESTART=YES
No out-of-scope production file was required. This is not final certification of the broader AST semantic coverage family.

## FULL_DIFFS

diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 47606e1..55ac25f 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -30,6 +30,7 @@ from contextor.core.graph.graph import build_trie, detect_package_root, build_gr
 from contextor.core.reference.shared import (
     _assemble_module_export_surfaces,
     _assemble_reexport_map,
+    _canonicalize_package_reference_target,
     validate_reexport_facts_by_module,
 )
 from contextor.core.reference.resolution import _resolve_alias, _resolve_reexport
@@ -315,10 +316,17 @@ def _resolve_canonical_target_keys(
             return (target,), "resolved"
         return (), "unresolved"
 
+    lookup_target = (
+        _canonicalize_package_reference_target(
+            target,
+            candidate_artifacts,
+        )
+    )
+
     if dotted_target_index is not None:
         matches = tuple(
             dotted_target_index.get(
-                target,
+                lookup_target,
                 (),
             )
         )
@@ -331,7 +339,7 @@ def _resolve_canonical_target_keys(
                     "::" in canonical
                     and ".".join(
                         canonical.split("::", 1)
-                    ) == target
+                    ) == lookup_target
                 )
             )
         )
@@ -487,8 +495,14 @@ def _rebuild_consumer_slice(
                         set(),
                     ).add("api_imports")
 
+        canonical_star_source = (
+            _canonicalize_package_reference_target(
+                star_source,
+                candidate_artifacts,
+            )
+        )
         reexport_facts = reexport_facts_by_module.get(
-            star_source
+            canonical_star_source
         )
         if (
             reexport_facts is not None
diff --git a/contextor/core/analysis/refresh_planner.py b/contextor/core/analysis/refresh_planner.py
index 8b200ab..9296a2b 100644
--- a/contextor/core/analysis/refresh_planner.py
+++ b/contextor/core/analysis/refresh_planner.py
@@ -22,6 +22,9 @@ def _find_dependent_consumers(
     qualified_refs, callback_calls, event_bindings, inheritance_refs.
     """
     from contextor.core.reference.resolution import _resolve_alias
+    from contextor.core.reference.shared import (
+        _canonicalize_package_reference_target,
+    )
 
     recompute_set: Set[str] = set()
     if not usages:
@@ -45,6 +48,10 @@ def _find_dependent_consumers(
 
         for ref in raw_refs:
             resolved = _resolve_alias(ref, c_aliases)
+            resolved = _canonicalize_package_reference_target(
+                resolved,
+                usages,
+            )
             if (
                 resolved == module_path
                 or resolved.startswith(f"{module_path}.")
diff --git a/contextor/core/reference/index.py b/contextor/core/reference/index.py
index 8c60d4a..27c1c30 100644
--- a/contextor/core/reference/index.py
+++ b/contextor/core/reference/index.py
@@ -33,6 +33,7 @@ from .resolution import (
 from .shared import (
     _assemble_module_export_surfaces,
     _assemble_reexport_map,
+    _canonicalize_package_reference_target,
     _empty_reference,
     _extract_reexport_facts,
     _normalize_references,
@@ -493,8 +494,14 @@ class RepositoryReferenceIndex:
 
             # 1. Calls
             for event in facts["calls"]:
-                resolved = _resolve_reexport(event["resolved"], reexports)
-                candidate = _resolve_reexport(event["candidate"], reexports)
+                resolved = _canonicalize_package_reference_target(
+                    _resolve_reexport(event["resolved"], reexports),
+                    modules,
+                )
+                candidate = _canonicalize_package_reference_target(
+                    _resolve_reexport(event["candidate"], reexports),
+                    modules,
+                )
                 if resolved:
                     direct_calls_by_target[resolved].append((module_id, event["line"], event["context"]))
                 if candidate:
@@ -510,7 +517,10 @@ class RepositoryReferenceIndex:
 
             # 2. Callbacks
             for name, local_resolved, lineno, ctx in facts["callbacks"]:
-                resolved = _resolve_reexport(local_resolved, reexports)
+                resolved = _canonicalize_package_reference_target(
+                    _resolve_reexport(local_resolved, reexports),
+                    modules,
+                )
                 if resolved:
                     callbacks_by_target[resolved].append((module_id, lineno, ctx))
                 name_to_check = name or resolved
@@ -522,7 +532,10 @@ class RepositoryReferenceIndex:
 
             # 3. Events
             for name, local_resolved, lineno, ctx in facts["events"]:
-                resolved = _resolve_reexport(local_resolved, reexports)
+                resolved = _canonicalize_package_reference_target(
+                    _resolve_reexport(local_resolved, reexports),
+                    modules,
+                )
                 if resolved:
                     events_by_target[resolved].append((module_id, lineno, ctx))
                 name_to_check = name or resolved
@@ -534,7 +547,10 @@ class RepositoryReferenceIndex:
 
             # 4. Inheritance
             for child_name, base_name, local_resolved, lineno in facts["inheritance"]:
-                resolved = _resolve_reexport(local_resolved, reexports)
+                resolved = _canonicalize_package_reference_target(
+                    _resolve_reexport(local_resolved, reexports),
+                    modules,
+                )
                 if resolved:
                     inheritance_by_target[resolved].append((module_id, child_name, lineno))
                 name_to_check = base_name or resolved
@@ -546,7 +562,10 @@ class RepositoryReferenceIndex:
 
             # 5. Qualified Refs
             for name, local_resolved, lineno, ctx in facts["qualified_refs"]:
-                resolved = _resolve_reexport(local_resolved, reexports)
+                resolved = _canonicalize_package_reference_target(
+                    _resolve_reexport(local_resolved, reexports),
+                    modules,
+                )
                 if resolved:
                     qualified_refs_by_target[resolved].append((module_id, lineno, ctx))
                 name_to_check = name or resolved
@@ -566,7 +585,13 @@ class RepositoryReferenceIndex:
                     if imported_name == "*":
                         star_imports_by_source[source_module].append(module_id)
                     else:
-                        target_id = _resolve_reexport(f"{source_module}.{imported_name}", reexports)
+                        target_id = _canonicalize_package_reference_target(
+                            _resolve_reexport(
+                                f"{source_module}.{imported_name}",
+                                reexports,
+                            ),
+                            modules,
+                        )
                         imports_by_target[target_id].append(module_id)
 
         return cls(
@@ -647,17 +672,37 @@ class RepositoryReferenceIndex:
 
             # 8. Star Imports
             for source_prefix, consumers in self.star_imports_by_source.items():
+                canonical_source_module = (
+                    _canonicalize_package_reference_target(
+                        source_prefix,
+                        self.modules,
+                    )
+                )
+                canonical_all_symbol = (
+                    _canonicalize_package_reference_target(
+                        f"{source_prefix}.__all__",
+                        self.modules,
+                    )
+                )
                 visible_targets = self.module_export_surfaces.get(
                     source_prefix,
                     {},
                 )
                 is_visible_export = any(
-                    _resolve_reexport(target, self.reexports) == symbol
+                    _canonicalize_package_reference_target(
+                        _resolve_reexport(
+                            target,
+                            self.reexports,
+                        ),
+                        self.modules,
+                    )
+                    == symbol
                     for target in visible_targets.values()
                 )
                 is_all_metadata = (
-                    source_prefix in self.explicit_all_modules
-                    and symbol == f"{source_prefix}.__all__"
+                    canonical_source_module
+                    in self.explicit_all_modules
+                    and symbol == canonical_all_symbol
                 )
                 if is_visible_export or is_all_metadata:
                     rec["imported_from"].extend(consumers)
diff --git a/contextor/core/reference/shared.py b/contextor/core/reference/shared.py
index 0b44f4f..ca185c5 100644
--- a/contextor/core/reference/shared.py
+++ b/contextor/core/reference/shared.py
@@ -38,6 +38,71 @@ def _export_module_name(module_id: str) -> str:
     return module_id.removesuffix(".__init__")
 
 
+def _canonicalize_package_reference_target(
+    name: str | None,
+    modules: Any,
+) -> str | None:
+    """
+    Map an external dotted Python reference through a package initializer
+    to the indexed package module identity.
+
+    Examples:
+
+        pkg.PUBLIC
+        -> pkg.__init__.PUBLIC
+
+        pkg.__all__
+        -> pkg.__init__.__all__
+
+        pkg.provider.run
+        -> pkg.provider.run
+
+    The longest existing module prefix wins, so real submodules are never
+    rewritten through their parent package initializer.
+    """
+    if not name:
+        return name
+
+    module_ids = (
+        modules.keys()
+        if isinstance(modules, Mapping)
+        else modules
+    )
+
+    parts = name.split(".")
+
+    for stop in range(
+        len(parts),
+        0,
+        -1,
+    ):
+        prefix = ".".join(
+            parts[:stop]
+        )
+
+        # A real indexed module takes precedence.
+        if prefix in module_ids:
+            return name
+
+        init_module = (
+            f"{prefix}.__init__"
+        )
+
+        if init_module in module_ids:
+            suffix = ".".join(
+                parts[stop:]
+            )
+
+            if suffix:
+                return (
+                    f"{init_module}.{suffix}"
+                )
+
+            return init_module
+
+    return name
+
+
 def _is_valid_reexport_fact(
     module_id: str,
     fact: Any,
diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index b14b0b9..d57b0c5 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -2174,3 +2174,144 @@ def test_star_import_visibility_changes_match_full_oracle(tmp_path, monkeypatch)
         [],
         all_target_exists=False,
     )
+
+
+def test_package_init_star_visibility_changes_match_full_oracle(
+    tmp_path,
+    monkeypatch,
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    package = tmp_path / "pkg"
+    package.mkdir()
+    package_init = package / "__init__.py"
+    package_init.write_text(
+        "PUBLIC = 1\n"
+        "_PRIVATE = 2\n"
+        "__all__ = ['PUBLIC']\n",
+        encoding="utf-8",
+    )
+    (tmp_path / "consumer.py").write_text(
+        "from pkg import *\n",
+        encoding="utf-8",
+    )
+
+    errors, _ = ContextorFacade().analyze_project(str(tmp_path))
+    assert not errors, errors
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    engine = hydrated.engine
+
+    def assert_package_star_projection(
+        state,
+        public_channels,
+        private_channels,
+        all_channels,
+        all_target_exists=True,
+    ):
+        assert state.artifact_consumption.get(
+            "pkg.__init__::PUBLIC", {}
+        ).get("channels", {}).get("consumer", []) == public_channels
+        assert state.artifact_consumption.get(
+            "pkg.__init__::_PRIVATE", {}
+        ).get("channels", {}).get("consumer", []) == private_channels
+        assert (
+            "pkg.__init__::__all__" in state.artifact_consumption
+        ) is all_target_exists
+        assert state.artifact_consumption.get(
+            "pkg.__init__::__all__", {}
+        ).get("channels", {}).get("consumer", []) == all_channels
+
+    assert_package_star_projection(
+        engine.state,
+        ["api_imports"],
+        [],
+        ["api_imports"],
+    )
+
+    package_init.write_text(
+        "PUBLIC = 1\n"
+        "_PRIVATE = 2\n"
+        "__all__ = []\n",
+        encoding="utf-8",
+    )
+    empty_all_result = engine.update_file(str(package_init))
+    assert "consumer" in empty_all_result.execution_trace[
+        "recompute_modules"
+    ]
+    empty_all_oracle = _build_full_static_state(tmp_path)
+    _assert_full_parity(engine.state, empty_all_oracle)
+    assert_package_star_projection(
+        engine.state,
+        [],
+        [],
+        ["api_imports"],
+    )
+
+    package_init.write_text(
+        "PUBLIC = 1\n"
+        "_PRIVATE = 2\n",
+        encoding="utf-8",
+    )
+    implicit_all_result = engine.update_file(str(package_init))
+    assert "consumer" in implicit_all_result.execution_trace[
+        "recompute_modules"
+    ]
+    implicit_all_oracle = _build_full_static_state(tmp_path)
+    _assert_full_parity(engine.state, implicit_all_oracle)
+    assert_package_star_projection(
+        engine.state,
+        ["api_imports"],
+        [],
+        [],
+        all_target_exists=False,
+    )
+
+
+def test_named_package_local_import_update_matches_full_oracle(
+    tmp_path,
+    monkeypatch,
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    package = tmp_path / "pkg"
+    package.mkdir()
+    package_init = package / "__init__.py"
+    package_init.write_text(
+        "def public():\n"
+        "    return 1\n",
+        encoding="utf-8",
+    )
+    (tmp_path / "consumer.py").write_text(
+        "from pkg import public\n"
+        "\n"
+        "def use():\n"
+        "    return public()\n",
+        encoding="utf-8",
+    )
+
+    errors, _ = ContextorFacade().analyze_project(str(tmp_path))
+    assert not errors, errors
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    engine = hydrated.engine
+    target = "pkg.__init__::public"
+    assert set(
+        engine.state.artifact_consumption[target]["channels"]["consumer"]
+    ) == {"api_imports", "direct_calls"}
+
+    package_init.write_text(
+        "def public():\n"
+        "    return 1\n"
+        "\n"
+        "def added():\n"
+        "    return 2\n",
+        encoding="utf-8",
+    )
+    result = engine.update_file(str(package_init))
+
+    assert "consumer" in result.execution_trace["recompute_modules"]
+    assert target in engine.state.artifact_consumption
+    assert set(
+        engine.state.artifact_consumption[target]["channels"]["consumer"]
+    ) == {"api_imports", "direct_calls"}
+    oracle = _build_full_static_state(tmp_path)
+    _assert_full_parity(engine.state, oracle)
diff --git a/tests/test_reexport_reference_semantics.py b/tests/test_reexport_reference_semantics.py
index fb989fb..4ee17d4 100644
--- a/tests/test_reexport_reference_semantics.py
+++ b/tests/test_reexport_reference_semantics.py
@@ -8,6 +8,9 @@ from contextor.core.reporting_layer.artifact_usage_report import (
 from contextor.core.symbol_engine.indexer import index_repository
 from contextor.core.api.facade import ContextorFacade
 from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.reference.shared import (
+    _canonicalize_package_reference_target,
+)
 
 
 def _full_canonical_state(tmp_path, monkeypatch):
@@ -341,3 +344,208 @@ def test_full_multiple_star_imports_project_each_source_module(
     assert _star_channels(state, "b::beta") == ["api_imports"]
     assert _star_channels(state, "a::_A_PRIVATE") == []
     assert _star_channels(state, "b::_B_PRIVATE") == []
+
+
+def test_package_reference_canonicalizer_prefers_longest_module_prefix():
+    modules = {
+        "pkg.__init__",
+        "pkg.provider",
+        "pkg.sub.__init__",
+    }
+
+    assert (
+        _canonicalize_package_reference_target(
+            "pkg.PUBLIC",
+            modules,
+        )
+        == "pkg.__init__.PUBLIC"
+    )
+    assert (
+        _canonicalize_package_reference_target(
+            "pkg.__all__",
+            modules,
+        )
+        == "pkg.__init__.__all__"
+    )
+    assert (
+        _canonicalize_package_reference_target(
+            "pkg.provider.run",
+            modules,
+        )
+        == "pkg.provider.run"
+    )
+    assert (
+        _canonicalize_package_reference_target(
+            "pkg.sub.VALUE",
+            modules,
+        )
+        == "pkg.sub.__init__.VALUE"
+    )
+    assert (
+        _canonicalize_package_reference_target(
+            "pkg.sub.__all__",
+            modules,
+        )
+        == "pkg.sub.__init__.__all__"
+    )
+
+
+def test_named_package_local_import_uses_init_canonical_identity(
+    tmp_path,
+    monkeypatch,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "__init__.py").write_text(
+        "def public():\n"
+        "    pass\n",
+        encoding="utf-8",
+    )
+    (tmp_path / "consumer.py").write_text(
+        "from pkg import public\n"
+        "\n"
+        "def use():\n"
+        "    public()\n",
+        encoding="utf-8",
+    )
+
+    state = _full_canonical_state(tmp_path, monkeypatch)
+
+    entry = state.artifact_consumption["pkg.__init__::public"]
+    assert entry["consumers"] == ["consumer"]
+    assert set(entry["channels"]["consumer"]) == {
+        "api_imports",
+        "direct_calls",
+    }
+
+
+def test_package_star_explicit_all_uses_init_canonical_identity(
+    tmp_path,
+    monkeypatch,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "__init__.py").write_text(
+        "PUBLIC = 1\n"
+        "_PRIVATE = 2\n"
+        "__all__ = ['PUBLIC']\n",
+        encoding="utf-8",
+    )
+    (tmp_path / "consumer.py").write_text(
+        "from pkg import *\n",
+        encoding="utf-8",
+    )
+
+    state = _full_canonical_state(tmp_path, monkeypatch)
+
+    assert _star_channels(
+        state,
+        "pkg.__init__::PUBLIC",
+        consumer="consumer",
+    ) == ["api_imports"]
+    assert _star_channels(
+        state,
+        "pkg.__init__::_PRIVATE",
+        consumer="consumer",
+    ) == []
+    assert _star_channels(
+        state,
+        "pkg.__init__::__all__",
+        consumer="consumer",
+    ) == ["api_imports"]
+
+
+def test_package_star_empty_all_keeps_only_metadata_dependency(
+    tmp_path,
+    monkeypatch,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "__init__.py").write_text(
+        "PUBLIC = 1\n"
+        "_PRIVATE = 2\n"
+        "__all__ = []\n",
+        encoding="utf-8",
+    )
+    (tmp_path / "consumer.py").write_text(
+        "from pkg import *\n",
+        encoding="utf-8",
+    )
+
+    state = _full_canonical_state(tmp_path, monkeypatch)
+
+    assert _star_channels(
+        state,
+        "pkg.__init__::PUBLIC",
+        consumer="consumer",
+    ) == []
+    assert _star_channels(
+        state,
+        "pkg.__init__::_PRIVATE",
+        consumer="consumer",
+    ) == []
+    assert _star_channels(
+        state,
+        "pkg.__init__::__all__",
+        consumer="consumer",
+    ) == ["api_imports"]
+
+
+def test_package_star_without_all_exports_public_only(
+    tmp_path,
+    monkeypatch,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "__init__.py").write_text(
+        "PUBLIC = 1\n"
+        "_PRIVATE = 2\n",
+        encoding="utf-8",
+    )
+    (tmp_path / "consumer.py").write_text(
+        "from pkg import *\n",
+        encoding="utf-8",
+    )
+
+    state = _full_canonical_state(tmp_path, monkeypatch)
+
+    assert _star_channels(
+        state,
+        "pkg.__init__::PUBLIC",
+        consumer="consumer",
+    ) == ["api_imports"]
+    assert _star_channels(
+        state,
+        "pkg.__init__::_PRIVATE",
+        consumer="consumer",
+    ) == []
+    assert "pkg.__init__::__all__" not in state.artifact_consumption
+
+
+def test_package_star_reexport_keeps_provider_api_origin(
+    tmp_path,
+    monkeypatch,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "provider.py").write_text(
+        "def run():\n"
+        "    pass\n",
+        encoding="utf-8",
+    )
+    (package / "__init__.py").write_text(
+        "from .provider import run\n"
+        "__all__ = ['run']\n",
+        encoding="utf-8",
+    )
+    (tmp_path / "consumer.py").write_text(
+        "from pkg import *\n",
+        encoding="utf-8",
+    )
+
+    state = _full_canonical_state(tmp_path, monkeypatch)
+
+    entry = state.artifact_consumption["pkg.provider::run"]
+    assert "consumer" in entry["consumers"]
+    assert "api_imports" in entry["channels"]["consumer"]
+    assert "pkg.__init__::run" not in state.artifact_consumption

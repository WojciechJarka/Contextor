STATUS=STEP_PASS
CLASSIFICATION=PACKAGE_INIT_CANONICAL_REFERENCE_IDENTITY_CERTIFIED_ADD_CHANGE_DELETE

HEAD=09c93149e016ef24da3a90a21f129d77598f9b00
ACCEPTED_BASELINE=Prior package canonical identity changes are part of HEAD; before this retry, git status was empty and both allowed files matched HEAD.
SOURCE_DRIFT=NONE; exact requested _find_dependent_consumers anchor was present at the expected lines and the test file contained both adjacent package-init fixtures.

AUDIT_FINDING
The canonicalizer received only the pre-update usages keys. When pkg.__init__ was added, the new package module was absent from that domain, so the existing consumer's pkg.public reference could not be resolved against the added initializer.

PLANNER_MODULE_DOMAIN
After the existing empty-usages guard, the planner now builds module_domain once from set(usages), adds module_path when present, and passes module_domain to _canonicalize_package_reference_target. No other algorithm changes were made.

PACKAGE_INIT_ADD
PASS. A fresh baseline had pkg.provider.py and no pkg.__init__.py. Adding pkg.__init__.py returned UPDATED, recomputed consumer, did not recompute provider_consumer, and materialized pkg.__init__::public with exactly api_imports and direct_calls for consumer. Incremental state matched fresh full analysis through _assert_full_parity.

PACKAGE_INIT_DELETE
PASS. Removing pkg/__init__.py returned DELETED, recomputed consumer, removed pkg.__init__ from modules and pkg.__init__::public from artifact_consumption. Incremental state matched fresh full analysis through _assert_full_parity.

REAL_SUBMODULE_PRECEDENCE
PASS. provider_consumer importing pkg.provider.OTHER was not recomputed by the package-init ADD; submodule resolution retained precedence.

FIRST_RUN
PASS: new literal node only; 1 passed in 7.62s.
Command: & .\.venv\Scripts\python.exe -m pytest tests/test_completeness_freshness_parity_proof.py::test_package_init_module_addition_recomputes_existing_consumer

REGRESSION_RUN
PASS: 17 passed in 42.37s. This was the new node, two adjacent package-init nodes, and the 14 existing unified-star/re-export gates. No full repository suite was run.

TEST_NODE_ID
tests/test_completeness_freshness_parity_proof.py::test_package_init_module_addition_recomputes_existing_consumer

TEST_RESULTS
PASS, first run: tests/test_completeness_freshness_parity_proof.py::test_package_init_module_addition_recomputes_existing_consumer
PASS, regression run:
- tests/test_completeness_freshness_parity_proof.py::test_package_init_module_addition_recomputes_existing_consumer
- tests/test_completeness_freshness_parity_proof.py::test_package_init_star_visibility_changes_match_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_named_package_local_import_update_matches_full_oracle
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
- tests/test_completeness_freshness_parity_proof.py::test_transitive_reexport_symbol_remove_matches-full-oracle
- tests/test_completeness_freshness_parity_proof.py::test_star_import_visibility_changes_match_full_oracle

FILES_CHANGED_IN_RETRY
- contextor/core/analysis/refresh_planner.py
- tests/test_completeness_freshness_parity_proof.py
Diff check: PASS for both changed files.
No other source, test, or documentation files changed in this retry.

DIRECT_EVIDENCE
- Contextor pre-edit file context resolved refresh_planner.py as contextor.core.analysis.refresh_planner and identified direct consumers including incremental.engine, incremental.plan_executor, and the parity test module.
- Contextor lineage for _find_dependent_consumers confirmed its exact interface includes module_path and usages, and its confirmed caller is incremental.plan_executor.
- Pre-edit HEAD was 09c93149e016ef24da3a90a21f129d77598f9b00; pre-edit status was clean.
- Desktop watcher emitted UPDATED events for refresh_planner.py at revision 1526 and the parity test at revision 1527. Post-edit Contextor file context reported canonical_state=fresh, workspace_sync=verified, canonical_revision=1527, syntax diagnostics fresh with no errors.
- Targeted pytest results are recorded above.

RETRY_PATCH_ONLY
The following is the complete actual diff for the two files changed in this retry:

```diff
diff --git a/contextor/core/analysis/refresh_planner.py b/contextor/core/analysis/refresh_planner.py
index 9296a2b..c8aedd6 100644
--- a/contextor/core/analysis/refresh_planner.py
+++ b/contextor/core/analysis/refresh_planner.py
@@ -30,6 +30,10 @@ def _find_dependent_consumers(
     if not usages:
         return recompute_set
 
+    module_domain = set(usages)
+    if module_path:
+        module_domain.add(module_path)
+
     for c_path, c_facts in usages.items():
         if c_path == module_path:
             continue
@@ -50,7 +54,7 @@ def _find_dependent_consumers(
             resolved = _resolve_alias(ref, c_aliases)
             resolved = _canonicalize_package_reference_target(
                 resolved,
-                usages,
+                module_domain,
             )
             if (
                 resolved == module_path
diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index d57b0c5..56f2f0c 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -2267,6 +2267,68 @@ def test_package_init_star_visibility_changes_match_full_oracle(
     )
 
 
+def test_package_init_module_addition_recomputes_existing_consumer(
+    tmp_path,
+    monkeypatch,
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "provider.py").write_text(
+        "OTHER = 1\n",
+        encoding="utf-8",
+    )
+    (tmp_path / "consumer.py").write_text(
+        "from pkg import public\n"
+        "\n"
+        "def use():\n"
+        "    return public()\n",
+        encoding="utf-8",
+    )
+    (tmp_path / "provider_consumer.py").write_text(
+        "from pkg.provider import OTHER\n",
+        encoding="utf-8",
+    )
+
+    errors, _ = ContextorFacade().analyze_project(str(tmp_path))
+    assert not errors, errors
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    engine = hydrated.engine
+    assert "pkg.__init__" not in engine.state.modules
+
+    package_init = package / "__init__.py"
+    package_init.write_text(
+        "def public():\n"
+        "    return 1\n",
+        encoding="utf-8",
+    )
+    added = engine.update_file(str(package_init))
+    target = "pkg.__init__::public"
+
+    assert added.status == "UPDATED"
+    assert "consumer" in added.execution_trace["recompute_modules"]
+    assert "provider_consumer" not in added.execution_trace[
+        "recompute_modules"
+    ]
+    assert target in engine.state.artifact_consumption
+    assert set(
+        engine.state.artifact_consumption[target]["channels"]["consumer"]
+    ) == {"api_imports", "direct_calls"}
+    add_oracle = _build_full_static_state(tmp_path)
+    _assert_full_parity(engine.state, add_oracle)
+
+    package_init.unlink()
+    deleted = engine.update_file(str(package_init))
+
+    assert deleted.status == "DELETED"
+    assert "consumer" in deleted.execution_trace["recompute_modules"]
+    assert "pkg.__init__" not in engine.state.modules
+    assert target not in engine.state.artifact_consumption
+    delete_oracle = _build_full_static_state(tmp_path)
+    _assert_full_parity(engine.state, delete_oracle)
+
+
 def test_named_package_local_import_update_matches_full_oracle(
```

MCP_RESTART_REQUIRED=YES
FULL_ANALYSIS_REQUIRED_AFTER_RESTART=YES

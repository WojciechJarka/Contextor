STATUS=STEP_PASS
CLASSIFICATION=FULL_PARITY_FIX_TARGETED_GATES_PASS; FILE_UPDATE_COMPLETENESS_FAMILY_FINAL_PASS_NOT_CLAIMED

HEAD_BEFORE=2fe2dbe4d8f05983e3dbeb328fb669fb1791cc12
HEAD_AT_REPORT=2fe2dbe4d8f05983e3dbeb328fb669fb1791cc12
ACCEPTED_PREEXISTING_WORKTREE=Initial git status was clean at HEAD_BEFORE; accepted prior work is part of this HEAD, with no unstaged/untracked pre-existing files.
SOURCE_DRIFT=NONE for requested production/test anchors. The accepted reexport retarget fixture already used d::replacement. Consumer-last full parity exposed an additional existing-module api_import mapping; the narrow skip was added in the same allowed production file to match the full oracle.

CANONICAL_OWNER=RepositoryAnalysisState.artifact_consumption. Contextor fact lineage identifies ContextorFacade.analyze_project as full materializer and IncrementalAnalysisEngine._apply_delta_and_commit as incremental installer; _rebuild_consumer_slice produces the incremental consumer slice. get_file_edit_context at canonical revision 1481 reported the target file workspace_sync=verified and syntax diagnostics fresh; artifact_consumption fact lineage reported fresh canonical family with no unresolved edges.
FULL_ANALYSIS_DOTTED_IDENTITY_CONTRACT=Confirmed: for the late-provider exact spelling pkg.a.B.foo, fresh/full canonical consumption has consumer/direct_calls under both pkg.a::B.foo and pkg.a.B::foo, with artifact_consumption_state=fresh. The generality full-snapshot equality regression passed.
PLURAL_RESOLUTION_CONTRACT=_resolve_canonical_target_keys returns all sorted, deduplicated exact canonical identities for a complete dotted spelling; already-canonical :: targets remain singleton exact matches; no short-name fallback is added. Incremental consumer rebuild installs every resolved target. An api_import target that exactly names an existing module is skipped as module-level import evidence, matching the full canonical oracle and preventing the observed false api_imports edge to pkg.a::B.
SINGULAR_RESOLUTION_COMPATIBILITY=_resolve_canonical_target_key delegates to the plural resolver and keeps (None, ambiguous) for multiple exact canonical identities; the helper regression passed.

LATE_PROVIDER_RESULT=PASS. Only pkg.a.B provider was physically updated. Lifecycle test spies/guard confirmed pkg.a.B was extracted and consumer was neither re-extracted nor reread; state became fresh; both exact canonical targets contain consumer with channels=['direct_calls']; unrelated consumer entry and prior COW snapshot assertions passed; full parity passed.
CONSUMER_LAST_RESULT=PASS. With both providers present before consumer add, state became fresh; both exact canonical targets contain consumer/direct_calls; full parity passed. The full oracle excludes a module-level api_import from pkg.a::B, and the incremental path now matches that result.
GENERALITY_AMBIGUITY_PARITY=PASS. test_natural_ambiguity_transition_matches_full_oracle_state passed without weakening its exact snapshot equality.
UNIQUE_RESOLUTION_REGRESSION=PASS. test_nested_callee_contract_b_regression passed.
REEXPORT_RETARGET_REGRESSION=PASS. test_reexport_retarget_matches_full_oracle passed using d::replacement; fixture semantics were unchanged.
DOWNSTREAM_SOURCE_IO_EVIDENCE=Lifecycle test's extract_module_usage_facts spy and prepare_source_update guard passed: provider extraction occurred, consumer extraction/source-read did not. Plural resolver consumes cached usage facts, candidate artifacts, execution-local dotted target index, and reexport mapping only.
DEAD_FAIL_CLOSED_PATH_REMOVAL=Before the patch, literal search found _remove_consumer_slice definition plus two callers and artifact_consumption_failed assignment/gates. After the patch, literal search found no occurrences of either name. Independent requires_resync, state.resync_required, and validate_canonical_artifact_consumption_coverage freshness gates remain.

TARGETED_TESTS=Only the six requested node IDs were run; no full pytest suite was run:
- tests/test_completeness_freshness_parity_proof.py::test_natural_ambiguity_transition_matches_full_oracle_state
- tests/test_completeness_freshness_parity_proof.py::test_natural_dotted_identity_ambiguity_helper
- tests/test_completeness_freshness_parity_proof.py::test_natural_dotted_identity_ambiguity_transition_lifecycle
- tests/test_completeness_freshness_parity_proof.py::test_natural_dotted_identity_ambiguity_consumer_last
- tests/test_completeness_freshness_parity_proof.py::test_nested_callee_contract_b_regression
- tests/test_completeness_freshness_parity_proof.py::test_reexport_retarget_matches_full_oracle
TEST_RESULTS=The first six-node run had 5 passed and consumer_last failed full parity because incremental alone attached consumer/api_imports to pkg.a::B. A direct state comparison showed the full oracle kept pkg.a::B empty while both states agreed on consumer/direct_calls for the two function targets. After the narrow module-import guard, the same six-node command passed: 6 passed in 15.53s. git diff --check was clean.

FILES_CHANGED:
- contextor/core/analysis/incremental/plan_executor.py
- tests/test_completeness_freshness_parity_proof.py

MCP_RESTART_REQUIRED=YES_FOR_LATER_RUNTIME_CERTIFICATION. No MCP update_file or Desktop/MCP/backend restart was used.

## ACTUAL_DIFF: contextor/core/analysis/incremental/plan_executor.py
````diff
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index eb899d3..6283c9f 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -239,8 +239,9 @@ def _build_dotted_target_index(
     Builds one transient lookup from dotted target spelling to all
     canonical targets that share that spelling.
 
-    Multiple canonical candidates are preserved so ambiguity semantics
-    remain identical to the legacy linear scan.
+    All canonical identities with the same exact dotted spelling are
+    preserved so incremental consumer rebuilding matches the full-analysis
+    reference projection.
     """
     grouped: Dict[str, List[str]] = {}
 
@@ -267,7 +268,7 @@ def _build_dotted_target_index(
     }
 
 
-def _resolve_canonical_target_key(
+def _resolve_canonical_target_keys(
     target: Optional[str],
     candidate_consumption: Mapping[str, Any],
     candidate_artifacts: Mapping[str, Any],
@@ -275,27 +276,39 @@ def _resolve_canonical_target_key(
     dotted_target_index: Optional[
         Mapping[str, Tuple[str, ...]]
     ] = None,
-) -> Tuple[Optional[str], str]:
+) -> Tuple[Tuple[str, ...], str]:
     """
-    Resolves a target string against the canonical target domain.
-    Returns (canonical_key, status) where status is:
-    - 'resolved': exactly 1 match in canonical domain
-    - 'ambiguous': >1 matches in canonical domain (fail-closed)
-    - 'unresolved': 0 matches in canonical domain (unknown / external)
+    Resolve one reference spelling to every exact canonical target
+    represented by that spelling.
+
+    A complete dotted spelling may map to more than one canonical
+    identity, for example:
+
+        pkg.a::B.foo
+        pkg.a.B::foo
+
+    both serialize to:
+
+        pkg.a.B.foo
+
+    Full analysis projects confirmed evidence to every such exact
+    canonical identity. Incremental rebuilding must preserve the same
+    semantics.
+
+    This helper performs no short-name fallback.
     """
     if not target:
-        return None, "unresolved"
+        return (), "unresolved"
 
     if expected_targets is None:
         expected_targets = canonical_artifact_consumption_targets(
             candidate_artifacts
         )
 
-    # Already canonical format
     if "::" in target:
         if target in expected_targets:
-            return target, "resolved"
-        return None, "unresolved"
+            return (target,), "resolved"
+        return (), "unresolved"
 
     if dotted_target_index is not None:
         matches = tuple(
@@ -305,29 +318,62 @@ def _resolve_canonical_target_key(
             )
         )
     else:
-        fallback_matches: List[str] = []
-
-        for canonical in expected_targets:
-            definer, sep, symbol = canonical.partition("::")
-            if not sep:
-                continue
-
-            if f"{definer}.{symbol}" == target:
-                fallback_matches.append(
-                    canonical
+        matches = tuple(
+            sorted(
+                canonical
+                for canonical in expected_targets
+                if (
+                    "::" in canonical
+                    and ".".join(
+                        canonical.split("::", 1)
+                    ) == target
                 )
+            )
+        )
 
-        matches = tuple(
-            fallback_matches
+    matches = tuple(
+        sorted(
+            set(matches)
         )
+    )
+
+    if matches:
+        return matches, "resolved"
+
+    return (), "unresolved"
+
+
+def _resolve_canonical_target_key(
+    target: Optional[str],
+    candidate_consumption: Mapping[str, Any],
+    candidate_artifacts: Mapping[str, Any],
+    expected_targets: Optional[Set[str]] = None,
+    dotted_target_index: Optional[
+        Mapping[str, Tuple[str, ...]]
+    ] = None,
+) -> Tuple[Optional[str], str]:
+    """
+    Singular compatibility resolver.
+
+    Returns one canonical key only when the exact spelling identifies
+    exactly one canonical identity. Multiple exact canonical identities
+    retain the existing singular 'ambiguous' result.
+    """
+    matches, status = _resolve_canonical_target_keys(
+        target,
+        candidate_consumption,
+        candidate_artifacts,
+        expected_targets=expected_targets,
+        dotted_target_index=dotted_target_index,
+    )
+
+    if status != "resolved":
+        return None, status
 
     if len(matches) == 1:
         return matches[0], "resolved"
 
-    if len(matches) > 1:
-        return None, "ambiguous"
-
-    return None, "unresolved"
+    return None, "ambiguous"
 
 
 def _to_canonical_target_key(
@@ -350,7 +396,7 @@ def _rebuild_consumer_slice(
         Mapping[str, Tuple[str, ...]]
     ] = None,
     consumer_target_index: Optional[Dict[str, Set[str]]] = None,
-) -> Tuple[Dict[str, Any], bool]:
+) -> Dict[str, Any]:
     """
     Rebuilds the entire artifact_consumption slice for a single consumer.
 
@@ -362,8 +408,9 @@ def _rebuild_consumer_slice(
     Without the execution-local index, the legacy full-map fallback is
     preserved.
 
-    Returns (updated_consumption_dict, is_ambiguous). If is_ambiguous is
-    True, returns the original container without mutation.
+    Returns the updated consumption dictionary. A complete dotted
+    spelling that maps to multiple exact canonical identities is projected
+    to each identity, matching the full-analysis reference projection.
     """
     c_aliases = dict(consumer_facts.aliases)
     c_tagged = (
@@ -399,8 +446,6 @@ def _rebuild_consumer_slice(
     )
 
     rebuilt_targets: Dict[str, Set[str]] = {}
-    is_ambiguous = False
-
     for sym, ch_name in c_tagged:
         raw_t = _resolve_reexport(
             _resolve_alias(
@@ -409,7 +454,13 @@ def _rebuild_consumer_slice(
             ),
             reexports,
         )
-        target, status = _resolve_canonical_target_key(
+        if (
+            ch_name == "api_imports"
+            and raw_t in candidate_artifacts
+        ):
+            continue
+
+        targets, status = _resolve_canonical_target_keys(
             raw_t,
             candidate_consumption,
             candidate_artifacts,
@@ -417,22 +468,14 @@ def _rebuild_consumer_slice(
             dotted_target_index=dotted_target_index,
         )
 
-        if status == "ambiguous":
-            is_ambiguous = True
+        if status == "resolved":
+            for target in targets:
+                if target not in rebuilt_targets:
+                    rebuilt_targets[target] = set()
 
-        elif (
-            status == "resolved"
-            and target
-        ):
-            if target not in rebuilt_targets:
-                rebuilt_targets[target] = set()
-
-            rebuilt_targets[target].add(
-                ch_name
-            )
-
-    if is_ambiguous:
-        return candidate_consumption, True
+                rebuilt_targets[target].add(
+                    ch_name
+                )
 
     if consumer_target_index is None:
         new_consumption = dict(
@@ -549,39 +592,7 @@ def _rebuild_consumer_slice(
                 None,
             )
 
-    return new_consumption, False
-
-
-def _remove_consumer_slice(
-    consumption: Mapping[str, Any],
-    consumer: str,
-) -> Dict[str, Any]:
-    """
-    Fail-closed sanitization helper: completely removes a consumer's slice
-    from the candidate artifact_consumption container when resolution becomes ambiguous.
-    """
-    sanitized = dict(consumption)
-
-    for target, raw_entry in consumption.items():
-        if (
-            consumer not in raw_entry.get("consumers", ())
-            and consumer not in raw_entry.get("channels", {})
-        ):
-            continue
-
-        entry = _get_copy_of_entry(raw_entry)
-
-        entry["consumers"] = sorted(
-            c
-            for c in entry.get("consumers", ())
-            if c != consumer
-        )
-
-        entry["channels"].pop(consumer, None)
-
-        sanitized[target] = entry
-
-    return sanitized
+    return new_consumption
 
 
 def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
@@ -754,7 +765,6 @@ def execute_refresh_plan(
         executed_reparse.append(reparse_mod)
 
     # 3. RECOMPUTE - re-evaluate planned cached modules in RAM without source I/O
-    artifact_consumption_failed = False
     executed_recompute: List[str] = []
     if plan.recompute_modules:
         from contextor.core.analysis.refresh_planner import (
@@ -787,7 +797,7 @@ def execute_refresh_plan(
                 consumer_target_index,
             )
 
-            rebuilt_consumption, is_ambig = _rebuild_consumer_slice(
+            candidate.artifact_consumption = _rebuild_consumer_slice(
                 consumer=consumer_path,
                 consumer_facts=consumer_facts,
                 candidate_consumption=candidate.artifact_consumption,
@@ -798,20 +808,6 @@ def execute_refresh_plan(
                 consumer_target_index=consumer_target_index,
             )
 
-            if is_ambig:
-                candidate.artifact_consumption = _remove_consumer_slice(
-                    candidate.artifact_consumption,
-                    consumer_path,
-                )
-                consumer_target_index.pop(
-                    consumer_path,
-                    None,
-                )
-                artifact_consumption_failed = True
-                candidate.artifact_consumption_state = "stale"
-                break
-
-            candidate.artifact_consumption = rebuilt_consumption
             executed_recompute.append(
                 consumer_path
             )
@@ -892,7 +888,7 @@ def execute_refresh_plan(
                         copied_entry["channels"].pop(delta.module_path, None)
                         candidate.artifact_consumption[t_key] = copied_entry
             elif new_usage:
-                rebuilt_consumption, is_ambig = _rebuild_consumer_slice(
+                candidate.artifact_consumption = _rebuild_consumer_slice(
                     consumer=delta.module_path,
                     consumer_facts=new_usage,
                     candidate_consumption=candidate.artifact_consumption,
@@ -902,23 +898,7 @@ def execute_refresh_plan(
                     dotted_target_index=dotted_target_index,
                     consumer_target_index=consumer_target_index,
                 )
-                if is_ambig:
-                    candidate.artifact_consumption = _remove_consumer_slice(
-                        candidate.artifact_consumption,
-                        delta.module_path,
-                    )
-                    consumer_target_index.pop(
-                        delta.module_path,
-                        None,
-                    )
-                    artifact_consumption_failed = True
-                    candidate.artifact_consumption_state = "stale"
-                else:
-                    candidate.artifact_consumption = rebuilt_consumption
-
-            if artifact_consumption_failed:
-                candidate.artifact_consumption_state = "stale"
-            elif (
+            if (
                 getattr(state, "resync_required", False)
                 or plan.refresh_completeness == "requires_resync"
             ):
@@ -1046,8 +1026,6 @@ def execute_refresh_plan(
         candidate.collisions_state = "stale"
         candidate.artifact_consumption_state = "stale"
     else:
-        if artifact_consumption_failed:
-            candidate.artifact_consumption_state = "stale"
         if "advanced_graph_metrics" in plan.graph_recomputations:
             candidate.topology_metrics_state = "fresh"
         if "cached_analytics" in plan.patch_families:
````

## ACTUAL_DIFF: tests/test_completeness_freshness_parity_proof.py

````diff
diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index cc61d80..76c19d1 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -314,9 +314,9 @@ def test_runtime_calls_producer_and_canonical_parity(tmp_path):
 
 def test_natural_dotted_identity_ambiguity_helper():
     """
-    Proves _resolve_canonical_target_key returns (None, 'ambiguous')
-    when two canonical targets share the same dotted representation (e.g. pkg.a::B.foo and pkg.a.B::foo).
-    Does NOT use monkeypatch.
+    The singular helper preserves 'ambiguous' for non-unique canonical
+    identities, while production consumer rebuilding uses its plural
+    resolver to preserve full-analysis parity. Does NOT use monkeypatch.
     """
     candidate_artifacts = {
         "pkg.a": {"symbols": {"classes": ["B"], "functions": [], "methods": ["B.foo"], "globals": []}, "own_symbols": ["B", "B.foo"]},
@@ -333,15 +333,14 @@ def test_natural_dotted_identity_ambiguity_helper():
 
 def test_natural_dotted_identity_ambiguity_transition_lifecycle(tmp_path):
     """
-    Proves real natural dotted identity ambiguity during late provider update:
+    Proves exact dotted multi-identity parity during late provider update:
     STEP 1: pkg/a.py with class B: def foo(self): return 1 -> canonical pkg.a::B.foo
     STEP 2: consumer.py with import pkg.a; pkg.a.B.foo() -> uniquely bound to pkg.a::B.foo, fresh
     STEP 3 (LATE PROVIDER): pkg/a/B.py with def foo(): return 2 -> canonical pkg.a.B::foo
     Call ONLY update_file(pkg/a/B.py). NO consumer update.
     Verifies:
-    - artifact_consumption_state == 'stale'
-    - ambiguity detected in RAM backfill/recompute path
-    - fail-closed sanitization: consumer slice removed from candidate, no arbitrary binding
+    - artifact_consumption_state == 'fresh'
+    - consumer is projected to both exact canonical identities
     - consumer.py NOT reread from disk
     - COW: previous state was not mutated in place
     - unrelated entries preserved bit-for-bit
@@ -430,15 +429,13 @@ def test_natural_dotted_identity_ambiguity_transition_lifecycle(tmp_path):
     # (b) prepare_source_update guard: consumer.py was not reopened by production boundary.
     # If consumer.py had been read, guarded_prepare_source_update would have raised AssertionError.
 
-    # Assert fail-closed state
-    assert res2.artifact_consumption_state == "stale"
-    assert engine.state.artifact_consumption_state == "stale"
+    assert res2.artifact_consumption_state == "fresh"
+    assert engine.state.artifact_consumption_state == "fresh"
 
-    # Assert fail-closed sanitization: ambiguous consumer is NOT bound to either target
     for target_key in ("pkg.a::B.foo", "pkg.a.B::foo"):
         entry = engine.state.artifact_consumption.get(target_key, {})
-        assert "consumer" not in entry.get("consumers", [])
-        assert "consumer" not in entry.get("channels", {})
+        assert "consumer" in entry.get("consumers", [])
+        assert entry.get("channels", {}).get("consumer") == ["direct_calls"]
 
     # Assert unrelated consumer entry is preserved bit-for-bit
     assert engine.state.artifact_consumption["unrelated::ping"]["consumers"] == ["unrelated_consumer"]
@@ -448,11 +445,20 @@ def test_natural_dotted_identity_ambiguity_transition_lifecycle(tmp_path):
     assert old_consumption_ref == old_snapshot
     assert "consumer" in old_consumption_ref["pkg.a::B.foo"]["consumers"]
 
+    oracle = _build_full_static_state(
+        tmp_path
+    )
+
+    _assert_full_parity(
+        engine.state,
+        oracle,
+    )
+
 
 def test_natural_dotted_identity_ambiguity_consumer_last(tmp_path):
     """
-    Proves natural dotted identity ambiguity during consumer ADD (when both providers already exist).
-    Incremental engine fails closed to 'stale' without arbitrary binding.
+    Proves exact dotted multi-identity full parity during consumer ADD
+    after both providers already exist.
     """
     pkg_dir = tmp_path / "pkg"
     pkg_dir.mkdir()
@@ -480,14 +486,22 @@ def test_natural_dotted_identity_ambiguity_consumer_last(tmp_path):
     engine.update_file(str(f_b))
     res = engine.update_file(str(f_consumer))
 
-    # Assert fail-closed state
-    assert res.artifact_consumption_state == "stale"
-    assert engine.state.artifact_consumption_state == "stale"
+    assert res.artifact_consumption_state == "fresh"
+    assert engine.state.artifact_consumption_state == "fresh"
 
-    # Assert no arbitrary consumer binding occurred
     for target_key in ("pkg.a::B.foo", "pkg.a.B::foo"):
         entry = engine.state.artifact_consumption.get(target_key, {})
-        assert "consumer" not in entry.get("consumers", [])
+        assert "consumer" in entry.get("consumers", [])
+        assert entry.get("channels", {}).get("consumer") == ["direct_calls"]
+
+    oracle = _build_full_static_state(
+        tmp_path
+    )
+
+    _assert_full_parity(
+        engine.state,
+        oracle,
+    )
 
 
 def test_nested_callee_contract_b_regression(tmp_path):
````



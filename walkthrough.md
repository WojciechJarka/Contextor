# CPA_FILE_UPDATE_CANONICAL_DEFINITION_PAYLOAD_FIX

STATUS=STEP_PASS
CLASSIFICATION=STEP_PASS

HEAD_BEFORE=ffcb45fc5b73e6f7de6b6f08dc6ef5def009b063
SOURCE_DRIFT=NONE; production files were clean against HEAD before editing, and all requested literal anchors matched.

CANONICAL_OWNER
- Canonical payload: RepositoryAnalysisState.artifacts[module], including symbols and own_symbols.
- Incremental installation path: IncrementalAnalysisEngine.update_file -> RefreshPlanner.plan_refresh -> _apply_delta_and_commit / plan executor definitions patch.
- Full oracle: tests._build_full_static_state.
- Contextor file context reported both production modules available, workspace_sync=verified, provenance=live, canonical revision 1469. The artifact_consumption fact lineage identifies RepositoryAnalysisState.artifact_consumption as a separate canonical family and _apply_delta_and_commit as its incremental writer; no broader lineage claim is made for artifacts.

CONTRACT_IMPLEMENTED
- extract_artifact_names now includes globals.
- calculate_file_delta marks symbol_payload_changed in metadata_changes when symbol payload differs without identity additions/removals.
- The refresh planner adds the existing definitions patch family for that metadata marker, without identity_registry, consumer recomputation, or graph recomputation for payload-only changes.
- Usage and collision handling remain active; the requested reason strings are used.
- Added global-definition canonical parity and strengthened body/call-retarget canonical symbols and own_symbols parity assertions.

FILES_CHANGED
- contextor/core/analysis/incremental/preparation.py
- contextor/core/analysis/refresh_planner.py
- tests/test_completeness_freshness_parity_proof.py
- tests/test_cached_facts_live_analytics.py
- walkthrough.md (required report only; excluded from source/test diffs)

TARGETED_TESTS
Executed exactly one pytest command with exactly these node IDs:
- tests/test_completeness_freshness_parity_proof.py::test_incremental_signature_change_matches_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_incremental_global_add_matches_full_oracle
- tests/test_cached_facts_live_analytics.py::test_pure_body_change_no_cached_analytics_invalidation
- tests/test_cached_facts_live_analytics.py::test_stage3d3b_pure_body_minimal_execution_and_full_static_parity
- tests/test_cached_facts_live_analytics.py::test_stage3d3c_call_retarget_minimal_execution_counts_and_parity

Command:
& .\.venv\Scripts\python.exe -m pytest tests/test_completeness_freshness_parity_proof.py::test_incremental_signature_change_matches_full_oracle tests/test_completeness_freshness_parity_proof.py::test_incremental_global_add_matches_full_oracle tests/test_cached_facts_live_analytics.py::test_pure_body_change_no_cached_analytics_invalidation tests/test_cached_facts_live_analytics.py::test_stage3d3b_pure_body_minimal_execution_and_full_static_parity tests/test_cached_facts_live_analytics.py::test_stage3d3c_call_retarget_minimal_execution_counts_and_parity -q

TEST_RESULTS
5 passed, 1 third-party AuthlibDeprecationWarning, 22.85s. No other pytest nodes or full suite were run.

SIGNATURE_PARITY
PASS. Canonical incremental signature matched the full oracle: def foo(a, b=0). The initial canonical assertion remains def foo(a); the fresh full oracle asserts def foo(a, b=0).

BODY_FINGERPRINT_PARITY
PASS. The body-edit test compares the complete canonical symbols payload to the fresh full oracle after changing the function body. The symbols payload contract includes body_fingerprints (SymbolFacts serialization and extractor evidence: contextor/core/symbol_engine/domain.py and contextor/core/symbol_engine/extractor.py).

GLOBAL_DEFINITION_PARITY
PASS. The targeted global-add test observed SECOND in result.delta.artifacts_added and exact equality of incremental/full symbols and own_symbols.

IDENTITY_REGISTRY_SYNC_EVIDENCE
PASS for the tested body-only and call-retarget paths: mock_reg_sync.call_count == 0. Call-retarget also asserts identity_registry is absent from patch_families. The tested plans have no graph recomputations; mocked graph metrics call_count == 0 where the test instruments it.

DIRECT_EVIDENCE
- The signature reproducer asserts initial signature def foo(a), full signature def foo(a, b=0), then exact incremental/full equality.
- The body and call-retarget tests assert exact canonical symbols and own_symbols equality against their full static oracles.
- The global test asserts SECOND is classified as added and exact symbols/own_symbols equality.
- The five authorized node IDs all passed.
- git diff --check returned no whitespace errors; Git emitted only its LF-to-CRLF working-copy notices.

CODE_PATH_PROVED
- Before the change, extract_artifact_names omitted globals and calculate_file_delta did not compare the symbols payload.
- The planner's default branch emitted no definitions patch for symbol-payload-only changes.
- After the change, the targeted execution/parity tests passed with the definitions patch while the asserted identity and graph invariants remained satisfied.

LIVE_EVIDENCE
- Baseline canonical revision: 1469.
- Desktop watcher emitted UPDATED events for preparation.py at revision 1470, refresh_planner.py at 1471, test_completeness_freshness_parity_proof.py at 1472, and test_cached_facts_live_analytics.py at 1473.
- Latest observed revision: 1473; continuity=continuous; resync_required=false. No MCP update_file or manual restart was used.

MCP_RESTART_REQUIRED
YES for later runtime-code freshness/certification because production Python modules changed. No restart was performed. The watcher events establish canonical source updates, not that an already-running Python process reloaded imported code.

ACTUAL_DIFF / FULL_DIFFS

diff --git a/contextor/core/analysis/incremental/preparation.py b/contextor/core/analysis/incremental/preparation.py
index ebb692b..be9dfd1 100644
--- a/contextor/core/analysis/incremental/preparation.py
+++ b/contextor/core/analysis/incremental/preparation.py
@@ -48,7 +48,7 @@ def extract_artifact_names(artifacts: Optional[Dict[str, Any]]) -> Set[str]:
     symbols = artifacts.get("symbols", {}) if artifacts else {}
     return {
         str(name)
-        for category in ("functions", "classes", "methods")
+        for category in ("functions", "classes", "methods", "globals")
         for name in symbols.get(category, [])
     }

@@ -89,6 +89,16 @@ def calculate_file_delta(
     delta.artifacts_added = sorted(new_artifact_names - old_artifact_names)
     delta.artifacts_removed = sorted(old_artifact_names - new_artifact_names)

+    old_symbols = (old_artifacts or {}).get("symbols", {})
+    new_symbols = new_artifacts_dict.get("symbols", {})
+
+    if (
+        old_symbols != new_symbols
+        and not delta.artifacts_added
+        and not delta.artifacts_removed
+    ):
+        delta.metadata_changes["symbol_payload_changed"] = True
+
     return delta


diff --git a/contextor/core/analysis/refresh_planner.py b/contextor/core/analysis/refresh_planner.py
index f36eab3..be5deeb 100644
--- a/contextor/core/analysis/refresh_planner.py
+++ b/contextor/core/analysis/refresh_planner.py
@@ -259,13 +259,27 @@ class RefreshPlanner:

         # 7. Default: Body-only Usage Change or Collision-only change
         has_usage = bool(usage_delta and not usage_delta.is_empty)
+        has_symbol_payload_change = bool(
+            delta
+            and delta.metadata_changes.get("symbol_payload_changed")
+        )
+
         patch_families = []
+        if has_symbol_payload_change:
+            patch_families.append("definitions")
         if has_usage:
-            patch_families = ["module_usages", "artifact_consumption", "cached_analytics"]
+            patch_families.extend(
+                ["module_usages", "artifact_consumption", "cached_analytics"]
+            )
         if collision_facts_changed:
             patch_families.extend(["collision_facts", "collisions"])

-        reason = f"Body-only usage change in '{module_path}'." if has_usage else f"Collision facts update for '{module_path}'."
+        if has_usage:
+            reason = f"Body/usage change in '{module_path}'."
+        elif has_symbol_payload_change:
+            reason = f"Definition payload change in '{module_path}'."
+        else:
+            reason = f"Collision facts update for '{module_path}'."

         return RefreshPlan(
             reparse_modules=(),


diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index 6385b80..473672f 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -883,6 +883,39 @@ def test_incremental_signature_change_matches_full_oracle(tmp_path):
     )


+def test_incremental_global_add_matches_full_oracle(tmp_path):
+    f_target = tmp_path / "target.py"
+    f_target.write_text("VALUE = 1\n", encoding="utf-8")
+
+    cache_dir = tmp_path / "cache"
+    cache_dir.mkdir()
+    engine = IncrementalAnalysisEngine(
+        RepositoryAnalysisState(modules={}),
+        PersistentIdentityRegistry(str(tmp_path)),
+        FileStateManager(str(cache_dir)),
+        str(tmp_path),
+    )
+    engine.update_file(str(f_target))
+
+    f_target.write_text(
+        "VALUE = 1\nSECOND = 2\n",
+        encoding="utf-8",
+    )
+    result = engine.update_file(str(f_target))
+
+    oracle = _build_full_static_state(tmp_path)
+
+    assert "SECOND" in result.delta.artifacts_added
+    assert (
+        engine.state.artifacts["target"]["symbols"]
+        == oracle.artifacts["target"]["symbols"]
+    )
+    assert (
+        engine.state.artifacts["target"]["own_symbols"]
+        == oracle.artifacts["target"]["own_symbols"]
+    )
+
+
 def test_full_canonical_parity_module_add_and_delete(tmp_path):
     f_target = tmp_path / "target.py"
     f_target.write_text("def foo(): pass\n", encoding="utf-8")


diff --git a/tests/test_cached_facts_live_analytics.py b/tests/test_cached_facts_live_analytics.py
index 2ed599a..b4d1226 100644
--- a/tests/test_cached_facts_live_analytics.py
+++ b/tests/test_cached_facts_live_analytics.py
@@ -499,7 +499,7 @@ def test_requires_resync_invalidates_cached_analytics_freshness(tmp_path):


 def test_stage3d3b_pure_body_minimal_execution_and_full_static_parity(tmp_path):
-    """10. Stage 3D.3b: Pure body edit produces minimal plan (), 0-call execution, and 100% full static parity."""
+    """10. Stage 3D.3b: Pure body edit refreshes definition payload without unnecessary analytics/graph recomputation and preserves full static parity."""
     f = tmp_path / "calculator.py"
     f.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
     cache_dir = tmp_path / "cache"
@@ -524,11 +524,11 @@ def test_stage3d3b_pure_body_minimal_execution_and_full_static_parity(tmp_path):

         res = engine.update_file(str(f))

-    assert res.shadow_plan.patch_families == ()
+    assert res.shadow_plan.patch_families == ("definitions",)
     assert res.shadow_plan.reparse_modules == ()
     assert res.shadow_plan.recompute_modules == ()
     assert res.shadow_plan.graph_recomputations == ()
-    assert res.execution_trace["patch_families"] == ()
+    assert res.execution_trace["patch_families"] == ("definitions",)
     assert res.execution_trace["graph_recomputations"] == ()

     # Zero-call execution minimality
@@ -547,12 +547,20 @@ def test_stage3d3b_pure_body_minimal_execution_and_full_static_parity(tmp_path):

     assert set(engine.state.modules.keys()) == set(oracle_engine.state.modules.keys())
     assert set(engine.state.artifacts.keys()) == set(oracle_engine.state.artifacts.keys())
+    assert (
+        engine.state.artifacts["calculator"]["symbols"]
+        == oracle_engine.state.artifacts["calculator"]["symbols"]
+    )
+    assert (
+        engine.state.artifacts["calculator"]["own_symbols"]
+        == oracle_engine.state.artifacts["calculator"]["own_symbols"]
+    )
     assert engine.state.cached_analytics == oracle_engine.state.cached_analytics
     assert engine.state.cached_analytics_state == oracle_engine.state.cached_analytics_state == "fresh"


 def test_stage3d3c_call_retarget_minimal_execution_counts_and_parity(tmp_path):
-    """11. Stage 3D.3c: Pure call-retarget edit produces ('module_usages', 'artifact_consumption', 'cached_analytics') with 0 definitions patch."""
+    """11. Stage 3D.3c: Call-retarget refreshes definition payload and usage/consumption without identity or graph recomputation."""
     target_py = tmp_path / "target.py"
     target_py.write_text(
         "def foo():\n"
@@ -603,12 +611,11 @@ def test_stage3d3c_call_retarget_minimal_execution_counts_and_parity(tmp_path):

     # Shadow plan assertions
     assert res.shadow_plan.reparse_modules == ()
     assert res.shadow_plan.recompute_modules == ()
     assert res.shadow_plan.graph_recomputations == ()
-    assert res.shadow_plan.patch_families == ("module_usages", "artifact_consumption", "cached_analytics")
-    assert "definitions" not in res.shadow_plan.patch_families
+    assert res.shadow_plan.patch_families == ("definitions", "module_usages", "artifact_consumption", "cached_analytics")
     assert "identity_registry" not in res.shadow_plan.patch_families

     # Execution trace assertions
-    assert res.execution_trace["patch_families"] == ("module_usages", "artifact_consumption", "cached_analytics")
+    assert res.execution_trace["patch_families"] == ("definitions", "module_usages", "artifact_consumption", "cached_analytics")
     assert res.execution_trace["graph_recomputations"] == ()

     # Zero unnecessary calls
@@ -630,5 +637,13 @@ def test_stage3d3c_call_retarget_minimal_execution_counts_and_parity(tmp_path):

     assert set(engine.state.modules.keys()) == set(oracle_engine.state.modules.keys())
     assert set(engine.state.artifacts.keys()) == set(oracle_engine.state.artifacts.keys())
+    assert (
+        engine.state.artifacts["consumer"]["symbols"]
+        == oracle_engine.state.artifacts["consumer"]["symbols"]
+    )
+    assert (
+        engine.state.artifacts["consumer"]["own_symbols"]
+        == oracle_engine.state.artifacts["consumer"]["own_symbols"]
+    )
     assert engine.state.cached_analytics == oracle_engine.state.cached_analytics
     assert engine.state.cached_analytics_state == oracle_engine.state.cached_analytics_state == "fresh"


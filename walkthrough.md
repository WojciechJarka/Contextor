# L32G_C_AGGREGATE_MODULE_FRESHNESS_FAIL_CLOSED

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_lineage_freshness.py
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_project_architecture_full_reports.py
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_contextor_fact_lineage.py
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_file_edit_context_syntax.py

The final path is the focused supplementary regression expressly requested in Step 5; it uses the existing get_file_edit_context test fixture. No other production or test files changed. walkthrough.md is the report only.

## CURRENT_SOURCE_VERIFICATION

Contextor MCP discovery was performed first, including documentation for implementation, call-context, lineage, module blast radius, source-range and get_file_edit_context tools.

Before editing, Contextor returned the complete build_state_freshness implementation from C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py, lines 322-526. source_contract reported implementation_is_complete=true and no_partial_symbol_source=true; workspace_sync=verified at LIVE revision 184. Local text matched the required exact anchors.

The pre-patch implementation had:
- canonical_state stale when resync_required; otherwise target-local module_current_truth when target_module was supplied; otherwise literal fresh.
- families.module equal to module_current_truth(target_module).state only for a target; otherwise literal fresh.
- public get_project_architecture and contextor_fact_lineage callers invoking the helper without target_module.

Contextor blast radius identified get_project_architecture, contextor_fact_lineage, get_file_edit_context, get_module_blast_radius, get_source_range and other public tools as consumers. Post-edit direct module blast radius reported 32 direct consumers, 45 downstream consumers, 5 production and 40 test modules, no truncation. The symbol call-context tool is intra-module only: zero caller edges and six callee edges; it does not represent cross-module consumers.

After the change, Contextor fetched the complete updated implementation at lines 322-547 with source_contract implementation_is_complete=true, no_partial_symbol_source=true, workspace_sync=verified, LIVE revision 192. It shows the exact requested aggregation and only the module family field now uses module_parse_state.

## RED_RESULT

Before production change, the focused regression command ran 17 parameterized/caller cases: **12 failed, 5 passed**. The failures were the expected old behavior: unscoped canonical_state remained fresh for stale/untrusted/invalid map cases; resync family.module remained fresh instead of the independent aggregate marker; public architecture had no module family marker; and fact-lineage freshness remained fresh.

Exact failing nodes:
- tests/mcp/tools/test_lineage_freshness.py::test_unscoped_module_freshness_aggregates_parse_truth_without_mutation[untrusted]
- tests/mcp/tools/test_lineage_freshness.py::test_unscoped_module_freshness_aggregates_parse_truth_without_mutation[stale]
- tests/mcp/tools/test_lineage_freshness.py::test_unscoped_module_freshness_aggregates_parse_truth_without_mutation[mixed-untrusted-wins]
- tests/mcp/tools/test_lineage_freshness.py::test_unscoped_module_freshness_aggregates_parse_truth_without_mutation[invalid-key]
- tests/mcp/tools/test_lineage_freshness.py::test_unscoped_module_freshness_rejects_malformed_whole_map[none]
- tests/mcp/tools/test_lineage_freshness.py::test_unscoped_module_freshness_rejects_malformed_whole_map[false]
- tests/mcp/tools/test_lineage_freshness.py::test_unscoped_module_freshness_rejects_malformed_whole_map[empty-list]
- tests/mcp/tools/test_lineage_freshness.py::test_unscoped_module_freshness_rejects_malformed_whole_map[pair-iterable]
- tests/mcp/tools/test_lineage_freshness.py::test_global_resync_keeps_aggregate_parse_truth_but_stales_canonical_state[untrusted]
- tests/mcp/tools/test_lineage_freshness.py::test_global_resync_keeps_aggregate_parse_truth_but_stales_canonical_state[stale]
- tests/mcp/tools/test_get_project_architecture_full_reports.py::test_project_architecture_overlay_distinguishes_untrusted_from_lkg
- tests/mcp/tools/test_contextor_fact_lineage.py::test_untrusted_module_truth_prevents_symbol_calls_complete_coverage

The five passing RED cases were fresh-only map, empty map, missing legacy attribute, target-local truth despite unrelated malformed entry, and global resync with fresh module truth.

## GREEN_RESULT

The final focused run of the three named regression owners plus the new diagnostic-path regression passed: **117 passed, 1 dependency deprecation warning**.

The exact 13-file combined gate passed: **440 passed, 1 dependency deprecation warning in 130.46s**.

The modified production owner compiled in memory successfully with repository .venv Python. git diff --check returned no whitespace errors. Git emitted LF-to-CRLF normalization warnings for the five changed files.

During test integration, the first owner-file run exposed two expectation/fixture mismatches: the architecture fixture stub omitted families.module, and the fact-lineage test expected the prior partial status despite canonical_state now being unavailable. The architecture case now invokes the actual helper and the lineage expectation matches the required fail-closed aggregate. A subsequent temporary unrelated assertion edit was corrected before the final passing owner and combined runs; no production changes resulted from it.

## AGGREGATE_FRESHNESS_MATRIX

| Input to unscoped build_state_freshness | canonical_state when resync=false | families.module |
|---|---|---|
| Missing legacy attribute | fresh | fresh |
| Empty dict | fresh | fresh |
| All entries state=fresh | fresh | fresh |
| Any valid stale, otherwise fresh | stale | stale |
| Any malformed individual entry or non-string module key | unavailable | unavailable |
| Whole map None, False, empty list, or non-dict pair iterable | unavailable | unavailable |
| Mixed fresh, stale and untrusted entries | unavailable | unavailable |
| Mixed fresh and stale, no untrusted entries | stale | stale |
| Any parse marker while resync_required=true | stale | aggregate parse truth independently remains fresh, stale or unavailable |

Tests assert the source mapping object and each nested entry identity remain unchanged. No in-place normalization is performed. The implementation iterates only the already-materialized dict keys and calls module_current_truth; it introduces no disk read, source parse, repository scan, graph calculation, or persistence call.

## TARGET_LOCAL_COMPATIBILITY

With target_module supplied, module_parse_state is obtained only from module_current_truth for that target. The regression uses a fresh target plus an unrelated unknown marker and asserts target canonical_state/families.module remain fresh and the source map and both nested entries retain identity. Existing targeted tests also cover target stale and untrusted outcomes.

## GLOBAL_RESYNC_COMPATIBILITY

resync_required controls canonical_state after module_parse_state has been computed: canonical_state remains stale. families.module reports the independent aggregate parse truth, including unavailable for malformed whole map, unavailable for untrusted entry, stale for valid stale, and fresh for valid fresh. Parameterized regressions cover all four under resync=true. Existing target-specific global resync regression remains unchanged.

## PUBLIC_ARCHITECTURE_CONTRACT

C:\Temp\Contextor_Repo\contextor\mcp\tools\get_project_architecture.py calls build_state_freshness without target_module. Its overlay separately derives parse_stale_modules and can downgrade canonical_state. The updated regression uses the real build_state_freshness rather than the prior fixture stub and verifies that malformed pkg.mod produces:
- parse_stale_modules.pkg.mod.state=unavailable, provenance=untrusted
- state_freshness.canonical_state=unavailable
- state_freshness.families.module=unavailable
- an untrusted advisory warning
The original module_parse_freshness entry remains unchanged.

## PUBLIC_FACT_LINEAGE_CONTRACT

C:\Temp\Contextor_Repo\contextor\mcp\tools\contextor_fact_lineage.py calls build_state_freshness without target_module. With pkg.alpha state=unknown, symbol_calls coverage still records stale_module_count=1 and the aggregate coverage gap. Freshness now reports canonical_state=unavailable and families.module=unavailable; public result status is unavailable because canonical unavailability outranks the family coverage partial. The regression verifies all these values and the unresolved coverage gap remains present.

## DIAGNOSTICS_PUBLIC_GATE

Contextor source-range retrieval for C:\Temp\Contextor_Repo\contextor\mcp\tools\get_file_edit_context.py:455-470 is complete for the requested range. It calls module_truth_unavailable before building structural metrics. On unavailable module truth it returns immediately after attaching the separately materialized syntax_diagnostics projection. Other inspected call sites at lines 232-250, 395-414 and 590-610 have the same per-module gate before structural result construction. Contextor documentation states syntax diagnostics are an independent canonical syntax-family projection and stale structural responses may include that projection.

The new test tests/mcp/tools/test_get_file_edit_context_syntax.py::test_untrusted_module_truth_is_gated_before_canonical_syntax_projection uses the real module_truth_unavailable helper with module_parse_freshness={"pkg.module":{"state":"unknown"}} and syntax_diagnostics_state=fresh. It passes and verifies:
- top-level status=unavailable and provenance=untrusted;
- the separately materialized syntax_diagnostics retains availability=fresh and its exact syntax error;
- structural consumers and risk_score are absent.

This is not a bypass of the per-module structural gate: the public response is unavailable/untrusted and returns before structural payload construction. No diagnostics production file was changed. No BLOCKED_ADDITIONAL_CONSUMER condition was demonstrated.

## COMBINED_13_FILE_GATE

Exact command:
    & .\.venv\Scripts\python.exe -m pytest -q tests/mcp/tools/test_lineage_freshness.py tests/mcp/tools/test_contextor_fact_lineage.py tests/mcp/tools/test_get_module_blast_radius.py tests/mcp/tools/test_get_project_architecture_full_reports.py tests/mcp/tools/test_get_source_range_direct_lookup.py tests/test_module_usage_reuse.py tests/test_canonical_state_contract.py tests/test_reporting_single_file.py tests/analysis/test_lineage_live_query.py tests/test_live_e2e_corrections.py tests/test_refresh_plan_execution.py tests/test_syntax_diagnostics_full_analysis.py tests/test_live_state_ipc.py

Result: 440 passed, 1 AuthlibDeprecationWarning in 130.46s. No full repository pytest was run.

## SOURCE_SYNC_VERIFICATION

Contextor post-edit full symbol retrieval reported the exact updated implementation, no partial source, workspace_sync=verified at canonical LIVE revision 192. The public caller/blast-radius evidence was refreshed after the edit. Current project LIVE summary reports canonical_state=fresh, provenance=live, resync_required=false, parse_stale_modules empty. The unscoped project response workspace_sync=unverified because it is not target-file-scoped.

The final diff contains only the authorized production owner and the three named targeted test owners plus the Step 5 supplementary get_file_edit_context syntax regression. git status showed no unexpected changed files.

## LIVE_REVISION_BEFORE_AFTER

- Before: canonical LIVE revision 184, canonical_state=fresh, provenance=live, resync_required=false.
- After: canonical LIVE revision 192, canonical_state=fresh, provenance=live, resync_required=false.
- get_live_events(after_revision=184): continuity=continuous, resync_required=false, eight ordered desktop_watcher update_file events for revisions 185-192. Revision 188 is query_helpers.py; revisions 185-187 and 190-192 reflect the three targeted test owners; revision 189 reflects the supplementary syntax test.
- No manual update_file, restart or source mutation through MCP was performed.

## FULL_DIFFS

Complete raw git diff for all five changed source/test files follows:

```diff
diff --git a/contextor/mcp/query_helpers.py b/contextor/mcp/query_helpers.py
index c3200c6..0d48511 100644
--- a/contextor/mcp/query_helpers.py
+++ b/contextor/mcp/query_helpers.py
@@ -362,14 +362,39 @@ def build_state_freshness(
         provenance = "snapshot"
 
     # 2. Canonical State Internal Health
-    resync_required = getattr(state, "resync_required", False)
-    if resync_required:
-        canonical_state = "stale"
-    elif target_module:
-        truth = module_current_truth(state, target_module)
-        canonical_state = truth.get("state", "fresh")
+    if target_module:
+        module_parse_state = module_current_truth(
+            state,
+            target_module,
+        )["state"]
     else:
-        canonical_state = "fresh"
+        raw_module_freshness = getattr(
+            state,
+            "module_parse_freshness",
+            {},
+        )
+        if not isinstance(raw_module_freshness, dict):
+            module_parse_state = "unavailable"
+        else:
+            module_parse_state = "fresh"
+            for module_name in raw_module_freshness:
+                if type(module_name) is not str:
+                    module_parse_state = "unavailable"
+                    break
+                entry_state = module_current_truth(
+                    state,
+                    module_name,
+                )["state"]
+                if entry_state == "unavailable":
+                    module_parse_state = "unavailable"
+                    break
+                if entry_state == "stale":
+                    module_parse_state = "stale"
+
+    resync_required = getattr(state, "resync_required", False)
+    canonical_state = (
+        "stale" if resync_required else module_parse_state
+    )
 
     # 3. Positive Generation Coherence Proof (Blocker 1 - Fail Closed)
     state_mgr = getattr(engine, "state_manager", None)
@@ -462,11 +487,7 @@ def build_state_freshness(
 
     # 5. Families
     families = {
-        "module": (
-            module_current_truth(state, target_module)["state"]
-            if target_module
-            else "fresh"
-        ),
+        "module": module_parse_state,
         "graph": (
             "fresh"
             if getattr(state, "dependency_graph", None) is not None
diff --git a/tests/mcp/tools/test_contextor_fact_lineage.py b/tests/mcp/tools/test_contextor_fact_lineage.py
index 824c28b..0dfce4e 100644
--- a/tests/mcp/tools/test_contextor_fact_lineage.py
+++ b/tests/mcp/tools/test_contextor_fact_lineage.py
@@ -337,8 +337,10 @@ def test_untrusted_module_truth_prevents_symbol_calls_complete_coverage(tmp_path
 
     result = _load(contextor_fact_lineage(str(tmp_path), "symbol_calls"))
 
-    assert result["status"] == "partial"
+    assert result["status"] == "unavailable"
     assert result["coverage"]["stale_module_count"] == 1
+    assert result["freshness"]["canonical_state"] == "unavailable"
+    assert result["freshness"]["families"]["module"] == "unavailable"
     assert any(
         gap["expected_edge"] == "COMPLETE_SYMBOL_CALLS_COVERAGE"
         for gap in result["unresolved"]
diff --git a/tests/mcp/tools/test_get_file_edit_context_syntax.py b/tests/mcp/tools/test_get_file_edit_context_syntax.py
index 5d7d73f..c48b262 100644
--- a/tests/mcp/tools/test_get_file_edit_context_syntax.py
+++ b/tests/mcp/tools/test_get_file_edit_context_syntax.py
@@ -5,6 +5,7 @@ import pytest
 
 from contextor.core.report_query import IndexCatalog
 from contextor.mcp import query_helpers
+from contextor.mcp.query_helpers import module_truth_unavailable as canonical_module_truth_unavailable
 from contextor.mcp import runtime as mcp_runtime
 from contextor.mcp.tools.get_file_edit_context import get_file_edit_context
 
@@ -106,6 +107,38 @@ def test_syntax_error_survives_structural_fail_closed_response(monkeypatch, harn
     assert result["syntax_diagnostics"]["availability"] == "fresh"
 
 
+def test_untrusted_module_truth_is_gated_before_canonical_syntax_projection(
+    monkeypatch, harness
+):
+    state = _state(
+        family_state="fresh",
+        fact={
+            "status": "checked_with_errors",
+            "errors": [{"message": "invalid syntax", "line_number": 3, "column_number": 7}],
+        },
+    )
+    state.module_parse_freshness = {"pkg.module": {"state": "unknown"}}
+    _install_state(monkeypatch, harness, state)
+    monkeypatch.setattr(
+        query_helpers,
+        "module_truth_unavailable",
+        canonical_module_truth_unavailable,
+    )
+
+    result = json.loads(
+        get_file_edit_context(str(harness.root), file_path="pkg/module.py")
+    )
+
+    assert result["status"] == "unavailable"
+    assert result["provenance"] == "untrusted"
+    assert result["syntax_diagnostics"]["availability"] == "fresh"
+    assert result["syntax_diagnostics"]["errors"] == [
+        {"message": "invalid syntax", "line_number": 3, "column_number": 7}
+    ]
+    assert "consumers" not in result
+    assert "risk_score" not in result
+
+
 @pytest.mark.parametrize("family_state", ["not_materialized", "deferred"])
 def test_unavailable_syntax_family_never_fabricates_empty_errors(monkeypatch, harness, family_state):
     state = _state(family_state=family_state)
diff --git a/tests/mcp/tools/test_get_project_architecture_full_reports.py b/tests/mcp/tools/test_get_project_architecture_full_reports.py
index 8cc432a..907e9ed 100644
--- a/tests/mcp/tools/test_get_project_architecture_full_reports.py
+++ b/tests/mcp/tools/test_get_project_architecture_full_reports.py
@@ -190,6 +190,11 @@ def test_project_architecture_overlay_distinguishes_untrusted_from_lkg(tmp_path,
     engine = architecture_tool.mcp_runtime.get_or_init_engine(tmp_path)
     entry = {"state": "unknown"}
     engine.state.module_parse_freshness = {"pkg.mod": entry}
+    monkeypatch.setattr(
+        architecture_tool.query_helpers,
+        "build_state_freshness",
+        build_state_freshness,
+    )
 
     result = json.loads(mcp_server.get_project_architecture.fn(repo_path=str(tmp_path)))
 
@@ -197,6 +202,7 @@ def test_project_architecture_overlay_distinguishes_untrusted_from_lkg(tmp_path,
     assert live["parse_stale_modules"]["pkg.mod"]["state"] == "unavailable"
     assert live["parse_stale_modules"]["pkg.mod"]["provenance"] == "untrusted"
     assert live["state_freshness"]["canonical_state"] == "unavailable"
+    assert live["state_freshness"]["families"]["module"] == "unavailable"
     assert "untrusted" in live["state_freshness"]["advisory_warning"]
     assert "last-known-good" not in live["state_freshness"]["advisory_warning"]
     assert engine.state.module_parse_freshness["pkg.mod"] is entry
diff --git a/tests/mcp/tools/test_lineage_freshness.py b/tests/mcp/tools/test_lineage_freshness.py
index 415c3f0..a32a15c 100644
--- a/tests/mcp/tools/test_lineage_freshness.py
+++ b/tests/mcp/tools/test_lineage_freshness.py
@@ -159,3 +159,123 @@ def test_global_resync_still_wins_over_untrusted_module_canonical_state(tmp_path
 
     assert freshness["canonical_state"] == "stale"
     assert freshness["families"]["module"] == "unavailable"
+
+
+@pytest.mark.parametrize(
+    "raw_map, expected",
+    [
+        ({"pkg.mod": {"state": "unknown"}}, "unavailable"),
+        ({"pkg.mod": {"state": "stale"}}, "stale"),
+        (
+            {
+                "pkg.fresh": {"state": "fresh"},
+                "pkg.stale": {"state": "stale"},
+                "pkg.unknown": {"state": "unknown"},
+            },
+            "unavailable",
+        ),
+        (
+            {"pkg.fresh": {"state": "fresh"}, "pkg.stale": {"state": "stale"}},
+            "stale",
+        ),
+        (
+            {"pkg.one": {"state": "fresh"}, "pkg.two": {"state": "fresh"}},
+            "fresh",
+        ),
+        ({}, "fresh"),
+        ({1: {"state": "fresh"}}, "unavailable"),
+    ],
+    ids=[
+        "untrusted",
+        "stale",
+        "mixed-untrusted-wins",
+        "stale-wins-over-fresh",
+        "fresh-only",
+        "empty",
+        "invalid-key",
+    ],
+)
+def test_unscoped_module_freshness_aggregates_parse_truth_without_mutation(
+    tmp_path, raw_map, expected
+):
+    state = _state("fresh")
+    state.module_parse_freshness = raw_map
+    entries = dict(raw_map)
+
+    freshness = build_state_freshness(tmp_path, state)
+
+    assert freshness["canonical_state"] == expected
+    assert freshness["families"]["module"] == expected
+    assert state.module_parse_freshness is raw_map
+    for module_name, entry in entries.items():
+        assert state.module_parse_freshness[module_name] is entry
+
+
+@pytest.mark.parametrize(
+    "raw_map",
+    [None, False, [], [("pkg.mod", {"state": "fresh"})]],
+    ids=["none", "false", "empty-list", "pair-iterable"],
+)
+def test_unscoped_module_freshness_rejects_malformed_whole_map(tmp_path, raw_map):
+    state = _state("fresh")
+    state.module_parse_freshness = raw_map
+
+    freshness = build_state_freshness(tmp_path, state)
+
+    assert freshness["canonical_state"] == "unavailable"
+    assert freshness["families"]["module"] == "unavailable"
+    assert state.module_parse_freshness is raw_map
+
+
+def test_unscoped_module_freshness_missing_legacy_map_attribute_remains_fresh(tmp_path):
+    state = _state("fresh")
+
+    freshness = build_state_freshness(tmp_path, state)
+
+    assert freshness["canonical_state"] == "fresh"
+    assert freshness["families"]["module"] == "fresh"
+    assert not hasattr(state, "module_parse_freshness")
+
+
+def test_target_module_freshness_ignores_unrelated_untrusted_module(tmp_path):
+    state = _state("fresh")
+    state.module_parse_freshness = {
+        "pkg.target": {"state": "fresh"},
+        "pkg.other": {"state": "unknown"},
+    }
+    raw_map = state.module_parse_freshness
+    target_entry = raw_map["pkg.target"]
+    other_entry = raw_map["pkg.other"]
+
+    freshness = build_state_freshness(tmp_path, state, target_module="pkg.target")
+
+    assert freshness["canonical_state"] == "fresh"
+    assert freshness["families"]["module"] == "fresh"
+    assert state.module_parse_freshness is raw_map
+    assert raw_map["pkg.target"] is target_entry
+    assert raw_map["pkg.other"] is other_entry
+
+
+@pytest.mark.parametrize(
+    "raw_map, expected_family",
+    [
+        (None, "unavailable"),
+        ({"pkg.mod": {"state": "unknown"}}, "unavailable"),
+        ({"pkg.mod": {"state": "stale"}}, "stale"),
+        ({"pkg.mod": {"state": "fresh"}}, "fresh"),
+    ],
+    ids=["malformed-map", "untrusted", "stale", "fresh"],
+)
+def test_global_resync_keeps_aggregate_parse_truth_but_stales_canonical_state(
+    tmp_path, raw_map, expected_family
+):
+    state = _state("fresh")
+    state.resync_required = True
+    state.module_parse_freshness = raw_map
+
+    freshness = build_state_freshness(tmp_path, state)
+
+    assert freshness["canonical_state"] == "stale"
+    assert freshness["families"]["module"] == expected_family
+    assert state.resync_required is True
+    assert state.module_parse_freshness is raw_map
```

## REMAINING_RISKS

No unresolved code-path blocker in the authorized scope. The fresh syntax diagnostic remains in the unavailable get_file_edit_context response as a separately materialized canonical syntax-family fact; this is covered by the focused regression and documented behavior. Serving-process code reload was not certified.

## RESTART_REQUIRED

No restart was performed or needed for the source/workspace evidence and test gate. Serving-process certification would require a manual reload/restart boundary for the MCP/LIVE Python authority; Desktop would also need a manual boundary if it retains its own imported server code. Neither was performed.

## FINAL_VERDICT

PASS_TARGETED_REGRESSION_GATE. The exact authorized production patch is present; aggregate marker, target-local, global-resync, public architecture, fact-lineage, diagnostics gate, compile, diff and 13-file test checks passed. No serving-process runtime certification is claimed.



# L32G-B — exact patch and targeted regression

## CURRENT_HEAD

`5870e5bcab98e838d6eaf09835af7ac8a8fc80d3`

## WORKTREE_BASELINE

DIRECT_EVIDENCE: Before this task, only `C:\Temp\Contextor_Repo\walkthrough.md` was modified by the previous discovery report. HEAD matched DISCOVERY_HEAD. The five production and ten test files listed below were clean.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py`
- `C:\Temp\Contextor_Repo\contextor\core\canonical_state_query\runtime.py`
- `C:\Temp\Contextor_Repo\contextor\core\lineage_query\live_query.py`
- `C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py`
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\get_project_architecture.py`
- `C:\Temp\Contextor_Repo\tests\analysis\test_lineage_live_query.py`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_contextor_fact_lineage.py`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_module_blast_radius.py`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_project_architecture_full_reports.py`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_source_range_direct_lookup.py`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_lineage_freshness.py`
- `C:\Temp\Contextor_Repo\tests\test_canonical_state_contract.py`
- `C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py`
- `C:\Temp\Contextor_Repo\tests\test_module_usage_reuse.py`
- `C:\Temp\Contextor_Repo\tests\test_reporting_single_file.py`
- `C:\Temp\Contextor_Repo\walkthrough.md` (current-task report only).

## RED_RESULT

Tests were added before production edits. The first focused RED command selected nine new test functions across truth, freshness, lineage, canonical projection, architecture, blast radius, source range, reuse and fact lineage. Result: exit 1, 18 failed, 2 passed, 1 external AuthlibDeprecationWarning, 7.32 s. Failures directly showed invalid entries returning fresh/ok/resolved or bypassing reuse gates. No existing production code was changed before RED.

## GREEN_RESULT

After applying the five literal production patches:
- New focused cases: 40 passed, 1 external AuthlibDeprecationWarning, 7.49 s.
- Nine-file targeted gate: 251 passed, 1 external AuthlibDeprecationWarning, 37.54 s.
- Eight selected existing LKG, snapshot, syntax, clone and recovery tests: 8 passed, 1 external AuthlibDeprecationWarning, 11.71 s.
- Additional single-file TestContextBuilder case: 1 passed, 1.57 s.

A subsequent package-alias regression failed: `test_live_lineage_rejects_untrusted_package_init_alias` returns `resolved` where `unavailable` is required. Therefore the overall task is not GREEN. No full repository suite was run.

## TARGETED_REGRESSIONS

The nine-file gate comprised:
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_lineage_freshness.py`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_module_blast_radius.py`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_project_architecture_full_reports.py`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_contextor_fact_lineage.py`
- `C:\Temp\Contextor_Repo\tests\test_module_usage_reuse.py`
- `C:\Temp\Contextor_Repo\tests\test_canonical_state_contract.py`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_source_range_direct_lookup.py`
- `C:\Temp\Contextor_Repo\tests\test_reporting_single_file.py`
- `C:\Temp\Contextor_Repo\tests\analysis\test_lineage_live_query.py`

The separate selected existing tests were `test_syntax_error_marks_authoritative_last_known_good_and_recovery`, `test_affected_mcp_queries_fail_closed_on_parse_stale_state`, `test_canonical_projections_reject_stale_module_facts`, `test_minimal_valid_syntax_error_query_repair_query_flow`, `test_parse_freshness_survives_snapshot_hydration_and_recovers`, `test_syntax_stale_is_not_current_and_recovery_matches_full_extraction`, `test_live_incremental_syntax_lifecycle_is_source_scoped_and_revision_atomic`, and `test_repository_structural_clone_isolates_top_level_updater_failure`.

## INVALID_MARKER_MATRIX

The new truth tests cover target entries `None`, `False`, `17`, `[]`, `"bad"`, `{}`, and dict state `None`, `False`, `"unknown"`. Whole-map tests cover `None`, `False`, `0`, `[]`, `""`, `"bad"`, `17`, nonempty list; a dict containing an invalid target entry is also covered. Existing/missing map attribute, empty dict, missing target key, explicit fresh and explicit stale LKG are covered. Source objects and entries are checked for identity preservation. The snapshot roundtrip covers a malformed target entry and a malformed whole map.

## PUBLIC_AVAILABILITY_GATE

CODE_PATH_PROVED by passing focused tests: malformed target truth returns available=False, state=unavailable, provenance=untrusted without parse_failure. `module_truth_unavailable` carries status=unavailable; `build_state_freshness` gives canonical_state/families.module=unavailable when targeted, while global resync retains canonical_state=stale. `get_module_blast_radius` and `get_source_range` stop before fact-bearing content. `execute_projection` returns no results for malformed matched modules, labels mixed stale/untrusted as untrusted, and preserves the exact stale-only LKG response. `get_project_architecture` retains the existing parse_stale_modules key and distinguishes unavailable/untrusted records, warning and overall canonical_state. Symbol-call coverage is partial for the malformed module; module usage reuse and both checked single-file builder paths do not certify it.

## LINEAGE_LKG_VS_UNTRUSTED

Passing cases: malformed direct qualified query, artifact-ID resolved target, ordinary re-export alias and origin return unavailable without selected facts; explicit stale LKG without global resync keeps selected facts; global resync remains unavailable. BLOCKED_ADDITIONAL_CONSUMER: public package alias `pkg::public_run` with `module_parse_freshness["pkg.__init__"]={"state":"unknown"}` still resolves. The exact requested-module guard checks raw `pkg` (missing-map-entry fresh); canonical package alias resolution uses `pkg.__init__`; the final target guard checks fresh `pkg.provider`. The alias module's invalid entry is not checked. Focused test result: 1 failed in 1.02 s, `assert 'resolved' == 'unavailable'` at `C:\Temp\Contextor_Repo\tests\analysis\test_lineage_live_query.py:1442`. This is a real public bypass under the test fixture, not merely theoretical flow. Per task instruction, no additional production patch or redesign was attempted.

## SNAPSHOT_ROUNDTRIP

The new focused test constructs a valid temporary snapshot from an engine fixture with either malformed target entry or malformed whole map, saves and loads it, then checks that `module_current_truth` reports unavailable/untrusted. Both cases passed. No real repository snapshot was modified.

## INCREMENTAL_RECOVERY_COMPATIBILITY

Eight selected existing tests passed, including real syntax failure → stale LKG → source repair → RECOVERED, snapshot hydration → recovery, canonical/public stale gates, symbol-call recovery and structural COW clone. Reading malformed metadata does not mutate the source entry or itself claim RECOVERED. The exact patch did not alter mark_module_parse_failure, clear_module_parse_failure, clone_for_update, snapshot schema, incremental writer or graph logic.

## SOURCE_SYNC_VERIFICATION

Before edits: Contextor get_symbol_implementation returned complete current implementations for all six edited symbols/blocks with workspace_sync=verified, revision 156; exact anchors and HEAD were checked. The module_current_truth blast-radius response listed 12 direct static consumers without truncation and 144 downstream module reachability; intra-module call-context reported zero edges and symbol-lineage preview complete=true/metadata_consistent=true. Contextor source search identified `C:\Temp\Contextor_Repo\tests\test_canonical_state_contract.py` as the canonical projection test owner. After edits: Contextor fetched complete edited implementations of module_current_truth, module_truth_unavailable, build_live_lineage_state_freshness, query_live_symbol_lineage, execute_projection and _live_state_overlay at revision 173 with workspace_sync=verified. Blast radius still reports 12 direct consumers, truncated=false, workspace_sync=verified. No source drift was detected.

## LIVE_REVISION_BEFORE_AFTER

Before edits: revision 156, resync_required=false. After edits: revision 173, resync_required=false. `get_live_events(after_revision=156, limit=null)` returned continuity=continuous and 16 desktop_watcher events through revision 172, all committed; a subsequent `get_live_events(after_revision=172)` returned revision 173 for `C:\Temp\Contextor_Repo\tests\analysis\test_lineage_live_query.py`, continuity=continuous. The watcher covered all five production and ten test files. No manual update_file or MCP/Desktop/LIVE restart was performed. Watcher sync confirms indexed source identity, not serving MCP process reload.

## UNRESOLVED_RISKS

The package `__init__` alias bypass violates the required no-selected-facts contract. The exact five-patch allowlist does not address this route. Required next production action must be specified by the auditor; per the task's STOP rule this agent did not extend scope. Other dynamic Python call sites are outside the confirmed static blast-radius claim. The running MCP process may still contain pre-edit code.

## RUNTIME_RELOAD_REQUIREMENTS

The changed MCP-facing and LIVE query code requires process reload before serving-process certification. Reload was forbidden and not performed. Local focused tests execute disk code; LIVE watcher/source sync does not prove serving-process reload.

## FINAL_VERDICT

BLOCKED_ADDITIONAL_CONSUMER. The five exact production patches and focused tests are present, but the package alias regression proves an unaddressed public lineage bypass. Do not claim implementation complete or runtime certified.

## FULL_DIFFS / ACTUAL_DIFF

Git whitespace verification: source/test-only `git diff --check -- . ':(exclude)walkthrough.md'` exited 0. Global `git diff --check` exited 1 solely on whitespace inside this report's verbatim copied diff context (including preexisting trailing spaces in test source); no task-added source/test line was flagged. The raw diff text is preserved exactly.

Complete raw Git diffs for every source/test file changed in this task follow. `walkthrough.md` is the report and excluded from source/test diffs.

### C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py

~~~diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 4e30e53..450edc9 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -226,10 +226,36 @@ def build_syntax_diagnostics_from_index(index: Any) -> tuple[Dict[str, Dict[str,
 
 def module_current_truth(state: RepositoryAnalysisState, module_name: str) -> Dict[str, Any]:
     """Return authoritative per-module parse freshness and provenance."""
-    freshness = getattr(state, "module_parse_freshness", {}) or {}
-    entry = freshness.get(module_name)
-    if not isinstance(entry, dict) or entry.get("state") != "stale":
+    missing = object()
+    freshness = getattr(state, "module_parse_freshness", missing)
+
+    if freshness is missing:
+        freshness = {}
+
+    entry = (
+        freshness.get(module_name, missing)
+        if isinstance(freshness, dict)
+        else None
+    )
+
+    if entry is missing:
         return {"available": True, "state": "fresh", "provenance": "current"}
+
+    if (
+        not isinstance(entry, dict)
+        or type(entry.get("state")) is not str
+        or entry["state"] not in {"fresh", "stale"}
+    ):
+        return {
+            "available": False,
+            "state": "unavailable",
+            "provenance": "untrusted",
+            "reason": "Canonical module parse freshness metadata is invalid or untrusted.",
+        }
+
+    if entry["state"] == "fresh":
+        return {"available": True, "state": "fresh", "provenance": "current"}
+
     return {
         "available": False,
         "state": "stale",
~~~

### C:\Temp\Contextor_Repo\contextor\core\canonical_state_query\runtime.py

~~~diff
diff --git a/contextor/core/canonical_state_query/runtime.py b/contextor/core/canonical_state_query/runtime.py
index 8a4eb52..f8b1255 100644
--- a/contextor/core/canonical_state_query/runtime.py
+++ b/contextor/core/canonical_state_query/runtime.py
@@ -445,11 +445,15 @@ def execute_projection(state: Any, request: Any) -> dict[str, Any]:
             module_name: module_current_truth(state, module_name)
             for module_name in sorted(affected_modules)
         }
+        has_untrusted = any(
+            truth.get("state") == "unavailable"
+            for truth in details.values()
+        )
         return {
-            "status": "stale",
+            "status": "unavailable" if has_untrusted else "stale",
             "available": False,
             "root": normalized["root"],
-            "provenance": "last_known_good",
+            "provenance": "untrusted" if has_untrusted else "last_known_good",
             "affected_modules": details,
         }
     limit = normalized["limit"]
~~~

### C:\Temp\Contextor_Repo\contextor\core\lineage_query\live_query.py

~~~diff
diff --git a/contextor/core/lineage_query/live_query.py b/contextor/core/lineage_query/live_query.py
index 5648d9b..a7999b0 100644
--- a/contextor/core/lineage_query/live_query.py
+++ b/contextor/core/lineage_query/live_query.py
@@ -251,7 +251,11 @@ def build_live_lineage_state_freshness(
     resync_required = bool(getattr(state, "resync_required", False))
     canonical_state = (
         "stale"
-        if resync_required or module_state == "stale"
+        if resync_required
+        else "unavailable"
+        if module_state == "unavailable"
+        else "stale"
+        if module_state == "stale"
         else "fresh"
     )
 
@@ -263,6 +267,11 @@ def build_live_lineage_state_freshness(
             module_truth.get("reason")
             or "Target module canonical facts are last-known-good."
         )
+    elif module_state == "unavailable":
+        advisory_warning = (
+            module_truth.get("reason")
+            or "Target module canonical freshness is unavailable."
+        )
 
     return {
         "canonical_state": canonical_state,
@@ -499,6 +508,23 @@ def query_live_symbol_lineage(
             ),
         )
 
+    if raw_query.count("::") == 1:
+        requested_module = raw_query.split("::", 1)[0]
+        requested_truth = module_current_truth(state, requested_module)
+        if requested_truth["state"] == "unavailable":
+            return LiveSymbolLineageQueryResult(
+                resolution=LineageTargetResolution(
+                    status="unavailable",
+                    query=raw_query,
+                ),
+                unavailable_reason=requested_truth["reason"],
+                state_freshness=build_live_lineage_state_freshness(
+                    state,
+                    backend,
+                    target_module=requested_module,
+                ),
+            )
+
     try:
         canonical_query = backend.canonicalize_qualified_identity(
             raw_query
@@ -672,6 +698,24 @@ def query_live_symbol_lineage(
             ),
         )
 
+    target_truth = module_current_truth(
+        state,
+        resolution.target.module_name,
+    )
+    if target_truth["state"] == "unavailable":
+        return LiveSymbolLineageQueryResult(
+            resolution=LineageTargetResolution(
+                status="unavailable",
+                query=raw_query,
+            ),
+            unavailable_reason=target_truth["reason"],
+            state_freshness=build_live_lineage_state_freshness(
+                state,
+                backend,
+                target_module=resolution.target.module_name,
+            ),
+        )
+
     facts = service.symbol_lineage_facts(
         resolution.target
     )
~~~

### C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py

~~~diff
diff --git a/contextor/mcp/query_helpers.py b/contextor/mcp/query_helpers.py
index 299dfcb..c3200c6 100644
--- a/contextor/mcp/query_helpers.py
+++ b/contextor/mcp/query_helpers.py
@@ -113,7 +113,7 @@ def module_truth_unavailable(state, module_name: str) -> dict | None:
     if truth["available"]:
         return None
     return {
-        "status": "stale",
+        "status": "stale" if truth.get("state") == "stale" else "unavailable",
         "available": False,
         "module": module_name,
         **{key: value for key, value in truth.items() if key != "available"},
~~~

### C:\Temp\Contextor_Repo\contextor\mcp\tools\get_project_architecture.py

~~~diff
diff --git a/contextor/mcp/tools/get_project_architecture.py b/contextor/mcp/tools/get_project_architecture.py
index e040b88..8452edd 100644
--- a/contextor/mcp/tools/get_project_architecture.py
+++ b/contextor/mcp/tools/get_project_architecture.py
@@ -209,11 +209,26 @@ def _live_state_overlay(root: Path) -> dict[str, Any]:
     stale_modules = _stale_module_truths(state)
     if stale_modules:
         freshness = dict(freshness)
-        freshness["canonical_state"] = "stale"
+        has_untrusted = any(
+            truth.get("state") == "unavailable"
+            for truth in stale_modules.values()
+        )
+        freshness["canonical_state"] = (
+            "stale"
+            if getattr(state, "resync_required", False)
+            else "unavailable"
+            if has_untrusted
+            else "stale"
+        )
         existing_warning = freshness.get("advisory_warning")
         stale_warning = (
-            "One or more modules are parse-stale; canonical facts for those "
-            "modules are last-known-good."
+            "One or more modules have invalid parse freshness metadata; "
+            "their canonical facts are untrusted."
+            if has_untrusted
+            else (
+                "One or more modules are parse-stale; canonical facts for those "
+                "modules are last-known-good."
+            )
         )
         freshness["advisory_warning"] = (
             f"{existing_warning} {stale_warning}"
~~~

### C:\Temp\Contextor_Repo\tests\analysis\test_lineage_live_query.py

~~~diff
diff --git a/tests/analysis/test_lineage_live_query.py b/tests/analysis/test_lineage_live_query.py
index e6b87b9..af08916 100644
--- a/tests/analysis/test_lineage_live_query.py
+++ b/tests/analysis/test_lineage_live_query.py
@@ -1363,6 +1363,87 @@ def test_live_symbol_lineage_lkg_without_resync_keeps_selected_facts():
     assert result.state_freshness["families"]["module"] == "stale"
 
 
+@pytest.mark.parametrize("query", ["pkg.mod::handler", "A17/2"])
+def test_live_lineage_rejects_untrusted_requested_or_resolved_module(query):
+    state, _backend = _fixture()
+    entry = {"state": "unknown"}
+    state.module_parse_freshness = {"pkg.mod": entry}
+
+    result = query_live_symbol_lineage(state, query, ("interface",))
+
+    assert result.resolution.status == "unavailable"
+    assert result.selected is None
+    assert result.owner_names == {}
+    assert result.state_freshness["canonical_state"] == "unavailable"
+    assert result.state_freshness["families"]["module"] == "unavailable"
+    assert result.unavailable_reason == (
+        "Canonical module parse freshness metadata is invalid or untrusted."
+    )
+    assert state.module_parse_freshness["pkg.mod"] is entry
+
+
+@pytest.mark.parametrize("untrusted_module", ["alias", "origin"])
+def test_live_lineage_rejects_untrusted_alias_or_origin(untrusted_module):
+    state = _reexport_query_fixture(
+        {"alias": "alias.py", "origin": "origin.py"},
+        {
+            "alias": {
+                "exporter": "alias",
+                "explicit_all": None,
+                "bindings": {"public": "origin.handler"},
+                "star_sources": [],
+            },
+            "origin": {
+                "exporter": "origin",
+                "explicit_all": None,
+                "bindings": {},
+                "star_sources": [],
+            },
+        },
+        {"origin": (("A30/1", "origin::handler"),)},
+    )
+    state.module_parse_freshness = {untrusted_module: {"state": "unknown"}}
+
+    result = query_live_symbol_lineage(state, "alias::public", ("interface",))
+
+    assert result.resolution.status == "unavailable"
+    assert result.selected is None
+    assert result.owner_names == {}
+    assert result.state_freshness["canonical_state"] == "unavailable"
+    assert result.state_freshness["families"]["module"] == "unavailable"
+
+
+def test_live_lineage_rejects_untrusted_package_init_alias():
+    state = _reexport_query_fixture(
+        {
+            "pkg.__init__": "pkg/__init__.py",
+            "pkg.provider": "pkg/provider.py",
+        },
+        {
+            "pkg.__init__": {
+                "exporter": "pkg",
+                "explicit_all": ["public_run"],
+                "bindings": {"public_run": "pkg.provider.run"},
+                "star_sources": [],
+            },
+            "pkg.provider": {
+                "exporter": "pkg.provider",
+                "explicit_all": None,
+                "bindings": {"run": "pkg.provider.run"},
+                "star_sources": [],
+            },
+        },
+        {"pkg.provider": (("A30/1", "pkg.provider::run"),)},
+    )
+    state.module_parse_freshness = {"pkg.__init__": {"state": "unknown"}}
+
+    result = query_live_symbol_lineage(state, "pkg::public_run", ("interface",))
+
+    assert result.resolution.status == "unavailable"
+    assert result.selected is None
+    assert result.owner_names == {}
+
+
 def test_live_lineage_state_freshness_marks_resync_required():
     state, backend = _fixture()
     state.resync_required = True
~~~

### C:\Temp\Contextor_Repo\tests\mcp\tools\test_contextor_fact_lineage.py

~~~diff
diff --git a/tests/mcp/tools/test_contextor_fact_lineage.py b/tests/mcp/tools/test_contextor_fact_lineage.py
index a7dadd1..824c28b 100644
--- a/tests/mcp/tools/test_contextor_fact_lineage.py
+++ b/tests/mcp/tools/test_contextor_fact_lineage.py
@@ -330,6 +330,21 @@ def test_symbol_calls_complete_reports_coverage_and_three_update_branches(tmp_pa
     assert _edge(result, "PERSISTS") and _edge(result, "HYDRATES")
 
 
+def test_untrusted_module_truth_prevents_symbol_calls_complete_coverage(tmp_path, monkeypatch):
+    state = _state()
+    state.module_parse_freshness = {"pkg.alpha": {"state": "unknown"}}
+    _install(monkeypatch, tmp_path, state)
+
+    result = _load(contextor_fact_lineage(str(tmp_path), "symbol_calls"))
+
+    assert result["status"] == "partial"
+    assert result["coverage"]["stale_module_count"] == 1
+    assert any(
+        gap["expected_edge"] == "COMPLETE_SYMBOL_CALLS_COVERAGE"
+        for gap in result["unresolved"]
+    )
+
+
 def test_symbol_calls_partial_uses_one_aggregate_coverage_gap(tmp_path, monkeypatch):
     usages = {
         "pkg.alpha": SimpleNamespace(
~~~

### C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_module_blast_radius.py

~~~diff
diff --git a/tests/mcp/tools/test_get_module_blast_radius.py b/tests/mcp/tools/test_get_module_blast_radius.py
index 72dd0d6..961e624 100644
--- a/tests/mcp/tools/test_get_module_blast_radius.py
+++ b/tests/mcp/tools/test_get_module_blast_radius.py
@@ -115,6 +115,20 @@ def _fixture(monkeypatch):
     return state, registry
 
 
+def test_malformed_module_truth_blocks_fact_bearing_blast_radius(tmp_path, monkeypatch):
+    state, _registry = _fixture(monkeypatch)
+    entry = {"state": "unknown"}
+    state.module_parse_freshness = {"pkg.mod": entry}
+
+    result = json.loads(get_module_blast_radius(str(tmp_path), module="pkg.mod"))
+
+    assert result["status"] == "unavailable"
+    assert result["available"] is False
+    assert result["provenance"] == "untrusted"
+    assert "artifacts" not in result
+    assert state.module_parse_freshness["pkg.mod"] is entry
+
+
 def _zero_identity_large_fixture(monkeypatch):
     state, registry = _fixture(monkeypatch)
     symbols = [f"symbol_{index:02d}" for index in range(48)]
~~~

### C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_project_architecture_full_reports.py

~~~diff
diff --git a/tests/mcp/tools/test_get_project_architecture_full_reports.py b/tests/mcp/tools/test_get_project_architecture_full_reports.py
index d35614c..8cc432a 100644
--- a/tests/mcp/tools/test_get_project_architecture_full_reports.py
+++ b/tests/mcp/tools/test_get_project_architecture_full_reports.py
@@ -185,6 +185,39 @@ def test_get_project_architecture_normalizes_malformed_public_family(tmp_path, m
     assert engine.state.cycles_state == "pretend_fresh"
 
 
+def test_project_architecture_overlay_distinguishes_untrusted_from_lkg(tmp_path, monkeypatch):
+    _install_runtime(tmp_path, monkeypatch, _small_bundle())
+    engine = architecture_tool.mcp_runtime.get_or_init_engine(tmp_path)
+    entry = {"state": "unknown"}
+    engine.state.module_parse_freshness = {"pkg.mod": entry}
+
+    result = json.loads(mcp_server.get_project_architecture.fn(repo_path=str(tmp_path)))
+
+    live = result["live_state"]
+    assert live["parse_stale_modules"]["pkg.mod"]["state"] == "unavailable"
+    assert live["parse_stale_modules"]["pkg.mod"]["provenance"] == "untrusted"
+    assert live["state_freshness"]["canonical_state"] == "unavailable"
+    assert "untrusted" in live["state_freshness"]["advisory_warning"]
+    assert "last-known-good" not in live["state_freshness"]["advisory_warning"]
+    assert engine.state.module_parse_freshness["pkg.mod"] is entry
+
+
+def test_project_architecture_overlay_keeps_stale_and_resync_contract(tmp_path, monkeypatch):
+    _install_runtime(tmp_path, monkeypatch, _small_bundle())
+    engine = architecture_tool.mcp_runtime.get_or_init_engine(tmp_path)
+    engine.state.module_parse_freshness = {"pkg.mod": {"state": "stale"}}
+
+    stale = json.loads(mcp_server.get_project_architecture.fn(repo_path=str(tmp_path)))
+    assert stale["live_state"]["state_freshness"]["canonical_state"] == "stale"
+    assert stale["live_state"]["parse_stale_modules"]["pkg.mod"]["provenance"] == "last_known_good"
+
+    engine.state.module_parse_freshness = {"pkg.mod": {"state": "unknown"}}
+    engine.state.resync_required = True
+    resync = json.loads(mcp_server.get_project_architecture.fn(repo_path=str(tmp_path)))
+    assert resync["live_state"]["state_freshness"]["canonical_state"] == "stale"
+    assert resync["live_state"]["parse_stale_modules"]["pkg.mod"]["state"] == "unavailable"
+
+
 def test_get_project_architecture_preflights_over_50k_and_reports_section_sizes(
     tmp_path,
     monkeypatch,
~~~

### C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_source_range_direct_lookup.py

~~~diff
diff --git a/tests/mcp/tools/test_get_source_range_direct_lookup.py b/tests/mcp/tools/test_get_source_range_direct_lookup.py
index c8eb9f5..8e4b361 100644
--- a/tests/mcp/tools/test_get_source_range_direct_lookup.py
+++ b/tests/mcp/tools/test_get_source_range_direct_lookup.py
@@ -6,6 +6,7 @@ from types import SimpleNamespace
 import pytest
 
 from contextor.mcp import query_helpers
+from contextor.mcp.query_helpers import module_truth_unavailable as real_module_truth_unavailable
 from contextor.mcp import runtime as mcp_runtime
 from contextor.mcp import source_helpers
 from contextor.mcp.tools.get_source_range import get_source_range
@@ -155,6 +156,20 @@ def test_module_truth_unavailable_missing_engine_and_resync_remain_fail_closed(t
     }
 
 
+def test_malformed_module_truth_blocks_public_source_range(tmp_path, monkeypatch):
+    record = _record(tmp_path, "module.py")
+    engine = _engine(tmp_path, [record])
+    engine.state.module_parse_freshness = {"module": {"state": "unknown"}}
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(query_helpers, "module_truth_unavailable", real_module_truth_unavailable)
+
+    result = json.loads(get_source_range(str(tmp_path), "module.py", 1, 1))
+
+    assert result["status"] == "unavailable"
+    assert result["available"] is False
+    assert result["provenance"] == "untrusted"
+    assert "text" not in result
+
 def test_exact_path_reads_once_without_ast_or_source_tokenization(tmp_path, monkeypatch):
     record = _record(tmp_path, "module.py")
     engine = _engine(tmp_path, [record])
~~~

### C:\Temp\Contextor_Repo\tests\mcp\tools\test_lineage_freshness.py

~~~diff
diff --git a/tests/mcp/tools/test_lineage_freshness.py b/tests/mcp/tools/test_lineage_freshness.py
index a3f908b..415c3f0 100644
--- a/tests/mcp/tools/test_lineage_freshness.py
+++ b/tests/mcp/tools/test_lineage_freshness.py
@@ -127,3 +127,35 @@ def test_resync_keeps_canonical_stale_and_normalizes_only_malformed_family(tmp_p
     assert freshness["workspace_sync"] == "unverified"
     assert state.resync_required is True
     assert state.cycles_state == "pretend_fresh"
+
+
+@pytest.mark.parametrize(
+    "entry, expected",
+    [
+        ({"state": "unknown"}, "unavailable"),
+        ({"state": "stale"}, "stale"),
+        ({"state": "fresh"}, "fresh"),
+    ],
+)
+def test_target_module_truth_controls_common_freshness_without_mutation(
+    tmp_path, entry, expected
+):
+    state = _state("fresh")
+    state.module_parse_freshness = {"pkg.mod": entry}
+
+    freshness = build_state_freshness(tmp_path, state, target_module="pkg.mod")
+
+    assert freshness["canonical_state"] == expected
+    assert freshness["families"]["module"] == expected
+    assert state.module_parse_freshness["pkg.mod"] is entry
+
+
+def test_global_resync_still_wins_over_untrusted_module_canonical_state(tmp_path):
+    state = _state("fresh")
+    state.module_parse_freshness = {"pkg.mod": {"state": "unknown"}}
+    state.resync_required = True
+
+    freshness = build_state_freshness(tmp_path, state, target_module="pkg.mod")
+
+    assert freshness["canonical_state"] == "stale"
+    assert freshness["families"]["module"] == "unavailable"
~~~

### C:\Temp\Contextor_Repo\tests\test_canonical_state_contract.py

~~~diff
diff --git a/tests/test_canonical_state_contract.py b/tests/test_canonical_state_contract.py
index d497ea1..d8ae405 100644
--- a/tests/test_canonical_state_contract.py
+++ b/tests/test_canonical_state_contract.py
@@ -100,6 +100,63 @@ def test_modules_projection_is_canonical_bounded_and_excludes_absolute_path():
     assert "absolute_path" not in result["results"][0]
 
 
+def test_projection_rejects_untrusted_matched_module_without_rows():
+    state = _state()
+    entry = {"state": "unknown"}
+    state.module_parse_freshness = {"pkg.used": entry}
+
+    result = execute_projection(
+        state,
+        _request("modules", filters=[], select=["module_name"], limit=20),
+    )
+
+    assert result["status"] == "unavailable"
+    assert result["available"] is False
+    assert result["provenance"] == "untrusted"
+    assert result["affected_modules"]["pkg.used"]["state"] == "unavailable"
+    assert "results" not in result
+    assert state.module_parse_freshness["pkg.used"] is entry
+
+
+def test_projection_mixed_stale_and_untrusted_prefers_untrusted():
+    state = _state()
+    state.module_parse_freshness = {
+        "pkg.empty": {"state": "stale"},
+        "pkg.used": {"state": None},
+    }
+
+    result = execute_projection(state, _request("modules", select=["module_name"]))
+
+    assert result["status"] == "unavailable"
+    assert result["provenance"] == "untrusted"
+    assert result["affected_modules"]["pkg.empty"]["state"] == "stale"
+    assert result["affected_modules"]["pkg.used"]["state"] == "unavailable"
+    assert "results" not in result
+
+
+def test_projection_explicit_stale_retains_lkg_response():
+    state = _state()
+    state.module_parse_freshness = {"pkg.used": {"state": "stale"}}
+
+    result = execute_projection(state, _request("modules", select=["module_name"]))
+
+    assert result == {
+        "status": "stale",
+        "available": False,
+        "root": "modules",
+        "provenance": "last_known_good",
+        "affected_modules": {
+            "pkg.used": {
+                "available": False,
+                "state": "stale",
+                "provenance": "last_known_good",
+                "reason": "Current source could not be parsed; canonical facts are last-known-good.",
+                "parse_failure": {},
+            }
+        },
+    }
+
+
 def test_artifact_projection_preserves_unknown_consumer_state_and_null_rules():
     unknown = execute_projection(
         _state(),
~~~

### C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py

~~~diff
diff --git a/tests/test_live_e2e_corrections.py b/tests/test_live_e2e_corrections.py
index f9e5992..8bf8f3f 100644
--- a/tests/test_live_e2e_corrections.py
+++ b/tests/test_live_e2e_corrections.py
@@ -133,6 +133,95 @@ def _stale_mcp_state(tmp_path):
     )
 
 
+@pytest.mark.parametrize(
+    "raw_map",
+    [None, False, 0, [], "", "bad", 17, ["bad"]],
+    ids=repr,
+)
+def test_module_current_truth_rejects_malformed_whole_map_without_mutation(raw_map):
+    state = SimpleNamespace(module_parse_freshness=raw_map)
+
+    truth = module_current_truth(state, "provider")
+
+    assert truth == {
+        "available": False,
+        "state": "unavailable",
+        "provenance": "untrusted",
+        "reason": "Canonical module parse freshness metadata is invalid or untrusted.",
+    }
+    assert state.module_parse_freshness is raw_map
+
+
+@pytest.mark.parametrize(
+    "entry",
+    [None, False, 17, [], "bad", {}, {"state": None}, {"state": False}, {"state": "unknown"}],
+    ids=repr,
+)
+def test_module_current_truth_rejects_malformed_entry_without_mutation(entry):
+    raw_map = {"provider": entry}
+    state = SimpleNamespace(module_parse_freshness=raw_map)
+
+    truth = module_current_truth(state, "provider")
+
+    assert truth["available"] is False
+    assert truth["state"] == "unavailable"
+    assert truth["provenance"] == "untrusted"
+    assert "parse_failure" not in truth
+    assert state.module_parse_freshness is raw_map
+    assert state.module_parse_freshness["provider"] is entry
+
+
+def test_module_current_truth_keeps_valid_and_legacy_absence_contract():
+    for state in (
+        SimpleNamespace(),
+        SimpleNamespace(module_parse_freshness={}),
+        SimpleNamespace(module_parse_freshness={"other": {"state": "stale"}}),
+        SimpleNamespace(module_parse_freshness={"provider": {"state": "fresh"}}),
+    ):
+        assert module_current_truth(state, "provider") == {
+            "available": True,
+            "state": "fresh",
+            "provenance": "current",
+        }
+
+    stale_entry = {
+        "state": "stale",
+        "error": "invalid syntax",
+        "line_number": 2,
+        "column_number": 3,
+    }
+    stale = SimpleNamespace(module_parse_freshness={"provider": stale_entry})
+    assert module_current_truth(stale, "provider") == {
+        "available": False,
+        "state": "stale",
+        "provenance": "last_known_good",
+        "reason": "Current source could not be parsed; canonical facts are last-known-good.",
+        "parse_failure": {
+            "error": "invalid syntax",
+            "line_number": 2,
+            "column_number": 3,
+        },
+    }
+    assert stale.module_parse_freshness["provider"] is stale_entry
+
+
+def test_module_truth_unavailable_distinguishes_untrusted_from_lkg():
+    state = SimpleNamespace(module_parse_freshness={"provider": {"state": "stale"}})
+    stale = query_helpers.module_truth_unavailable(state, "provider")
+    assert stale["status"] == "stale"
+    assert stale["provenance"] == "last_known_good"
+    assert stale["parse_failure"] == {}
+
+    entry = {"state": "unknown"}
+    state.module_parse_freshness = {"provider": entry}
+    untrusted = query_helpers.module_truth_unavailable(state, "provider")
+    assert untrusted["status"] == "unavailable"
+    assert untrusted["available"] is False
+    assert untrusted["provenance"] == "untrusted"
+    assert "parse_failure" not in untrusted
+    assert state.module_parse_freshness["provider"] is entry
+
+
 def test_syntax_error_marks_authoritative_last_known_good_and_recovery(tmp_path):
     source, engine = _engine_for_file(tmp_path)
 
@@ -382,6 +471,39 @@ def test_parse_freshness_survives_snapshot_hydration_and_recovers(tmp_path):
     assert module_current_truth(loaded, "provider")["provenance"] == "current"
 
 
+@pytest.mark.parametrize(
+    "raw_map",
+    [{"provider": {"state": "unknown"}}, ["bad"]],
+    ids=["malformed_entry", "malformed_whole_map"],
+)
+def test_malformed_parse_freshness_snapshot_roundtrip_remains_untrusted(tmp_path, raw_map):
+    _source, engine = _engine_for_file(tmp_path)
+    engine.state.module_parse_freshness = raw_map
+    original_map = engine.state.module_parse_freshness
+
+    cache = tmp_path / "cache"
+    assert save_engine_state(engine.state, str(cache), "state-malformed")
+    loaded = load_engine_state(str(cache), "state-malformed")
+
+    assert loaded is not None
+    assert loaded.module_parse_freshness == raw_map
+    assert module_current_truth(loaded, "provider")["state"] == "unavailable"
+    assert module_current_truth(loaded, "provider")["provenance"] == "untrusted"
+    assert engine.state.module_parse_freshness is original_map
+
+
+def test_reading_malformed_parse_freshness_does_not_claim_recovery(tmp_path):
+    source, engine = _engine_for_file(tmp_path)
+    entry = {"state": "unknown"}
+    engine.state.module_parse_freshness = {"provider": entry}
+
+    assert module_current_truth(engine.state, "provider")["state"] == "unavailable"
+    assert engine.state.module_parse_freshness["provider"] is entry
+    source.write_text("def helper(value: int) -> int:\n    return value + 1\n")
+    result = engine.update_file(str(source))
+    assert result.status != "RECOVERED"
+
+
 def test_global_search_and_static_context_do_not_leak_parse_stale_truth(
     tmp_path, monkeypatch
 ):
~~~

### C:\Temp\Contextor_Repo\tests\test_module_usage_reuse.py

~~~diff
diff --git a/tests/test_module_usage_reuse.py b/tests/test_module_usage_reuse.py
index 45c8ca1..a291a8e 100644
--- a/tests/test_module_usage_reuse.py
+++ b/tests/test_module_usage_reuse.py
@@ -94,6 +94,27 @@ def test_stale_same_sha_extracts(monkeypatch,tmp_path):
     monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
     build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]
 
+
+def test_untrusted_same_sha_extracts_instead_of_reusing(monkeypatch, tmp_path):
+    modules, paths, good = _two(tmp_path)
+    prior = _state(
+        modules,
+        {"a": good, "b": good},
+        {"a": _entry("a", paths[0]), "b": _entry("b", paths[1])},
+        module_parse_freshness={"a": {"state": "unknown"}},
+    )
+    calls = []
+    monkeypatch.setattr(
+        "contextor.core.reference.module_usage_reuse.extract_module_usage_facts",
+        lambda mid, *_a, **_k: calls.append(mid) or good,
+    )
+
+    build_module_usage_baseline_with_reuse(
+        modules, prior, _manager({paths[0]: "sha", paths[1]: "sha"})
+    )
+
+    assert calls == ["a"]
+
 def test_unmaterialized_channels_extract(monkeypatch,tmp_path):
     modules,paths,good=_two(tmp_path); bad=ModuleUsageFacts(symbol_calls_materialized=False,reference_evidence_materialized=True); prior=_state(modules,{"a":bad,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])}); calls=[]
     monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
~~~

### C:\Temp\Contextor_Repo\tests\test_reporting_single_file.py

~~~diff
diff --git a/tests/test_reporting_single_file.py b/tests/test_reporting_single_file.py
index 2012367..4ea17be 100644
--- a/tests/test_reporting_single_file.py
+++ b/tests/test_reporting_single_file.py
@@ -1,6 +1,49 @@
 import pytest
+from types import SimpleNamespace
+from contextor.core.single_file.builders.layer0_builders import _canonical_state_module_is_current
+from contextor.core.single_file.builders.layer2_builders import TestContextBuilder as _TestContextBuilder
 from contextor.core.reporting_layer.reporting_single_file import generate_single_file_report
 
+
+def test_untrusted_module_parse_freshness_cannot_certify_single_file_canonical_facts():
+    entry = {"state": "unknown"}
+    state = SimpleNamespace(
+        artifacts={"pkg.mod": {"symbols": {}}},
+        module_parse_freshness={"pkg.mod": entry},
+    )
+
+    assert _canonical_state_module_is_current(state, "pkg.mod") is False
+    assert state.module_parse_freshness["pkg.mod"] is entry
+
+
+def test_untrusted_module_is_not_reused_by_test_context_builder(monkeypatch, tmp_path):
+    module = SimpleNamespace(ast_tree=object(), path="pkg/mod.py")
+    modules = {"pkg.mod": module}
+    engine_state = SimpleNamespace(
+        modules=modules,
+        module_parse_freshness={"pkg.mod": {"state": "unknown"}},
+    )
+    payload = SimpleNamespace(
+        module_id="pkg.mod",
+        root_path=str(tmp_path),
+        modules=modules,
+        engine_state=engine_state,
+    )
+    captured = {}
+
+    def fake_build_test_context(*_args, **kwargs):
+        captured.update(kwargs)
+        return {}
+
+    monkeypatch.setattr(
+        "contextor.core.analysis.test_context.build_test_context",
+        fake_build_test_context,
+    )
+
+    _TestContextBuilder().build(payload, {"public_api": []})
+
+    assert captured["modules"] == {}
+
 def test_single_file_report_header_and_node_id(tmp_path):
     ctx = {
         "module_id": "core.alpha", 
~~~

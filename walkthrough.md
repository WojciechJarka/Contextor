# L32F_PUBLIC_RESYNC_FAIL_CLOSED_FINAL_PATCH

## CURRENT_HEAD

58755b725b1809227f6f9c68bda883585562a7a6

## WORKTREE_BASELINE

Przed edycją zachowano dokładny diff ośmiu zastanych plików source/test. Worktree miał także zmodyfikowany walkthrough.md. Poniższe linie baseline diff są zapisane jako JSON string per line, aby zachować również końcowe spacje bez naruszenia git diff --check.

## PREEXISTING_DIFFS_IDENTIFIED

""
"diff --git a/contextor/core/analysis/incremental/materialization.py b/contextor/core/analysis/incremental/materialization.py"
"index ff26d73..8e06914 100644"
"--- a/contextor/core/analysis/incremental/materialization.py"
"+++ b/contextor/core/analysis/incremental/materialization.py"
"@@ -378,6 +378,10 @@ def ensure_collisions(state: RepositoryAnalysisState) -> None:"
"     if not hasattr(state, \"collision_facts\") or state.collision_facts is None:"
"         state.collision_facts = {}"
" "
"+    if getattr(state, \"resync_required\", False):"
"+        state.collisions_state = \"stale\""
"+        return"
"+"
"     # A. Stale state: untrusted/desynced source facts -> do NOT auto-heal"
"     if state.collisions_state == \"stale\":"
"         return"
"diff --git a/contextor/core/diagnostics_projection.py b/contextor/core/diagnostics_projection.py"
"index b390fc6..23ee56c 100644"
"--- a/contextor/core/diagnostics_projection.py"
"+++ b/contextor/core/diagnostics_projection.py"
"@@ -58,6 +58,29 @@ def diagnostics_summary_for_state("
"             },"
"         }"
" "
"+    if getattr(state, \"resync_required\", False):"
"+        unavailable = {"
"+            \"count\": None,"
"+            \"availability\": \"stale\","
"+        }"
"+        return {"
"+            \"syntax_errors\": dict(unavailable),"
"+            \"name_collisions\": {"
"+                \"count\": None,"
"+                \"critical\": None,"
"+                \"warning\": None,"
"+                \"info\": None,"
"+                \"availability\": \"stale\","
"+            },"
"+            \"cycles\": dict(unavailable),"
"+            \"attention_required\": False,"
"+            \"availability\": {"
"+                \"syntax_errors\": \"stale\","
"+                \"name_collisions\": \"stale\","
"+                \"cycles\": \"stale\","
"+            },"
"+        }"
"+"
"     syntax_state = getattr("
"         state,"
"         \"syntax_diagnostics_state\","
"diff --git a/contextor/core/lineage_query/live_query.py b/contextor/core/lineage_query/live_query.py"
"index 793f54b..5648d9b 100644"
"--- a/contextor/core/lineage_query/live_query.py"
"+++ b/contextor/core/lineage_query/live_query.py"
"@@ -484,6 +484,21 @@ def query_live_symbol_lineage("
"         state"
"     )"
" "
"+    if getattr(state, \"resync_required\", False):"
"+        return LiveSymbolLineageQueryResult("
"+            resolution=LineageTargetResolution("
"+                status=\"unavailable\","
"+                query=raw_query,"
"+            ),"
"+            unavailable_reason=("
"+                \"Canonical state requires resynchronization.\""
"+            ),"
"+            state_freshness=build_live_lineage_state_freshness("
"+                state,"
"+                backend,"
"+            ),"
"+        )"
"+"
"     try:"
"         canonical_query = backend.canonicalize_qualified_identity("
"             raw_query"
"diff --git a/contextor/mcp/diagnostics.py b/contextor/mcp/diagnostics.py"
"index 7118cdb..ade5527 100644"
"--- a/contextor/mcp/diagnostics.py"
"+++ b/contextor/mcp/diagnostics.py"
"@@ -31,6 +31,15 @@ def syntax_diagnostics_for_path("
"             \"errors\": None,"
"         }"
" "
"+    if getattr(state, \"resync_required\", False):"
"+        return {"
"+            \"status\": \"unavailable\","
"+            \"availability\": \"stale\","
"+            \"materialized\": False,"
"+            \"source_path\": canonical_path,"
"+            \"errors\": None,"
"+        }"
"+"
"     family_state = getattr(state, \"syntax_diagnostics_state\", None)"
"     facts = getattr(state, \"syntax_diagnostics_by_path\", None)"
"     if family_state != \"fresh\" or not isinstance(facts, dict):"
"diff --git a/contextor/mcp/tools/get_name_collisions.py b/contextor/mcp/tools/get_name_collisions.py"
"index 114dda8..85da32f 100644"
"--- a/contextor/mcp/tools/get_name_collisions.py"
"+++ b/contextor/mcp/tools/get_name_collisions.py"
"@@ -108,6 +108,8 @@ def get_name_collisions("
"         }"
"     ):"
"         availability = \"unavailable\""
"+    if state is not None and getattr(state, \"resync_required\", False):"
"+        availability = \"stale\""
"     if availability != \"fresh\":"
"         payload = {"
"             \"total\": None,"
"diff --git a/tests/analysis/test_lineage_live_query.py b/tests/analysis/test_lineage_live_query.py"
"index b1060af..e6b87b9 100644"
"--- a/tests/analysis/test_lineage_live_query.py"
"+++ b/tests/analysis/test_lineage_live_query.py"
"@@ -1340,6 +1340,29 @@ def test_live_lineage_state_freshness_marks_last_known_good_target_module_stale("
"     )"
" "
" "
"+def test_live_symbol_lineage_lkg_without_resync_keeps_selected_facts():"
"+    state, _backend, _selected = _owner_name_projection_fixture()"
"+    state.module_parse_freshness = {"
"+        \"pkg.mod\": {\"state\": \"stale\", \"error\": \"syntax failure\"},"
"+    }"
"+    state.resync_required = False"
"+"
"+    result = query_live_symbol_lineage("
"+        state,"
"+        \"A17/2\","
"+        (\"calls_interfaces\", \"state\"),"
"+    )"
"+"
"+    assert result.resolution.status == \"resolved\""
"+    assert result.selected is not None"
"+    assert result.owner_names == {"
"+        \"17/2\": \"pkg.mod\","
"+        \"A18/1\": \"pkg.mod::other\","
"+    }"
"+    assert result.state_freshness[\"canonical_state\"] == \"stale\""
"+    assert result.state_freshness[\"families\"][\"module\"] == \"stale\""
"+"
"+"
" def test_live_lineage_state_freshness_marks_resync_required():"
"     state, backend = _fixture()"
"     state.resync_required = True"
"@@ -1380,6 +1403,41 @@ def test_live_symbol_lineage_result_carries_selected_owner_names_and_same_revisi"
"     )"
" "
" "
"+def test_live_symbol_lineage_resync_returns_unavailable_without_selected_facts():"
"+    state, _backend, selected = _owner_name_projection_fixture()"
"+    state.resync_required = True"
"+    original_sources = state.lineage_facts_by_source"
"+"
"+    blocked = query_live_symbol_lineage("
"+        state,"
"+        \"A17/2\","
"+        (\"calls_interfaces\", \"state\"),"
"+    )"
"+"
"+    assert blocked.resolution.status == \"unavailable\""
"+    assert blocked.resolution.query == \"A17/2\""
"+    assert blocked.selected is None"
"+    assert blocked.owner_names == {}"
"+    assert blocked.unavailable_reason == \"Canonical state requires resynchronization.\""
"+    assert blocked.state_freshness[\"canonical_state\"] == \"stale\""
"+    assert blocked.state_freshness[\"advisory_warning\"] == blocked.unavailable_reason"
"+    assert state.lineage_facts_by_source is original_sources"
"+    assert selected is not None"
"+"
"+    state.resync_required = False"
"+    recovered = query_live_symbol_lineage("
"+        state,"
"+        \"A17/2\","
"+        (\"calls_interfaces\", \"state\"),"
"+    )"
"+    assert recovered.resolution.status == \"resolved\""
"+    assert recovered.selected is not None"
"+    assert recovered.owner_names == {"
"+        \"17/2\": \"pkg.mod\","
"+        \"A18/1\": \"pkg.mod::other\","
"+    }"
"+"
"+"
" def test_unresolved_and_unavailable_live_symbol_results_have_no_owner_names_but_keep_freshness():"
"     state, _backend = _fixture()"
" "
"diff --git a/tests/test_collisions_live_lifecycle.py b/tests/test_collisions_live_lifecycle.py"
"index 990d048..b2d5ad6 100644"
"--- a/tests/test_collisions_live_lifecycle.py"
"+++ b/tests/test_collisions_live_lifecycle.py"
"@@ -15,7 +15,7 @@ Verifies:"
" import ast"
" import tempfile"
" from pathlib import Path"
"-from unittest.mock import MagicMock"
"+from unittest.mock import MagicMock, patch"
" "
" import pytest"
" "
"@@ -262,6 +262,37 @@ def test_completeness_helper_and_materialization():"
"     assert state.collisions_state == \"stale\""
" "
" "
"+@pytest.mark.parametrize(\"marker\", [\"fresh\", \"deferred\"])"
"+def test_resync_collision_materialization_stales_without_recomputing_or_erasing(marker):"
"+    collision_facts = {\"a\": []}"
"+    collisions = [object()]"
"+    state = RepositoryAnalysisState("
"+        modules={"
"+            \"a\": Module(module_id=\"a\", path=\"a.py\", absolute_path=\"/tmp/a.py\", imports=[])"
"+        },"
"+        collision_facts=collision_facts,"
"+        collisions=collisions,"
"+        collisions_state=marker,"
"+    )"
"+    state.resync_required = True"
"+    assert collision_facts_complete(state) is True"
"+"
"+    with patch("
"+        \"contextor.core.validator.collisions.resolve_collision_candidate_codes\","
"+        return_value=collision_facts,"
"+    ) as resolve, patch("
"+        \"contextor.core.validator.collisions.compute_collisions_from_facts\","
"+        return_value=[],"
"+    ) as compute:"
"+        ensure_collisions(state)"
"+"
"+    assert state.collisions_state == \"stale\""
"+    assert state.collisions is collisions"
"+    assert state.collision_facts is collision_facts"
"+    resolve.assert_not_called()"
"+    compute.assert_not_called()"
"+"
"+"
" def test_incremental_engine_end_to_end_collision_lifecycle():"
"     \"\"\"End-to-end test of IncrementalAnalysisEngine updating files and managing collisions lifecycle.\"\"\""
"     with tempfile.TemporaryDirectory() as tmpdir:"
"diff --git a/tests/test_mcp_diagnostics.py b/tests/test_mcp_diagnostics.py"
"index 5ba4560..13f8838 100644"
"--- a/tests/test_mcp_diagnostics.py"
"+++ b/tests/test_mcp_diagnostics.py"
"@@ -109,6 +109,124 @@ def test_missing_markers_with_payload_do_not_certify_diagnostics(tmp_path, monke"
"     assert result[\"details\"] == []"
" "
" "
"+def test_resync_diagnostics_summary_hides_fresh_payloads_without_mutation():"
"+    syntax_facts = {"
"+        \"broken.py\": {\"status\": \"checked_with_errors\", \"errors\": [{\"message\": \"bad\"}]}"
"+    }"
"+    collisions = [_collision()]"
"+    cycles = [[\"a\", \"b\", \"a\"]]"
"+    state = SimpleNamespace("
"+        resync_required=True,"
"+        syntax_diagnostics_state=\"fresh\","
"+        syntax_diagnostics_by_path=syntax_facts,"
"+        collisions_state=\"fresh\","
"+        collisions=collisions,"
"+        cycles_state=\"fresh\","
"+        cycles=cycles,"
"+    )"
"+"
"+    summary = diagnostics_summary_for_state(state)"
"+"
"+    assert summary[\"availability\"] == {"
"+        \"syntax_errors\": \"stale\","
"+        \"name_collisions\": \"stale\","
"+        \"cycles\": \"stale\","
"+    }"
"+    assert summary[\"syntax_errors\"] == {\"count\": None, \"availability\": \"stale\"}"
"+    assert summary[\"name_collisions\"] == {"
"+        \"count\": None,"
"+        \"critical\": None,"
"+        \"warning\": None,"
"+        \"info\": None,"
"+        \"availability\": \"stale\","
"+    }"
"+    assert summary[\"cycles\"] == {\"count\": None, \"availability\": \"stale\"}"
"+    assert summary[\"attention_required\"] is False"
"+    assert state.syntax_diagnostics_by_path is syntax_facts"
"+    assert state.collisions is collisions"
"+    assert state.cycles is cycles"
"+"
"+    state.resync_required = False"
"+    recovered = diagnostics_summary_for_state(state)"
"+    assert recovered[\"availability\"] == {"
"+        \"syntax_errors\": \"fresh\","
"+        \"name_collisions\": \"fresh\","
"+        \"cycles\": \"fresh\","
"+    }"
"+    assert recovered[\"syntax_errors\"][\"count\"] == 1"
"+    assert recovered[\"name_collisions\"][\"count\"] == 1"
"+    assert recovered[\"cycles\"][\"count\"] == 1"
"+    assert recovered[\"attention_required\"] is True"
"+"
"+"
"+def test_resync_syntax_path_does_not_materialize_fresh_error_fact():"
"+    facts = {"
"+        \"broken.py\": {\"status\": \"checked_with_errors\", \"errors\": [{\"message\": \"bad\"}]}"
"+    }"
"+    state = SimpleNamespace("
"+        resync_required=True,"
"+        syntax_diagnostics_state=\"fresh\","
"+        syntax_diagnostics_by_path=facts,"
"+    )"
"+"
"+    result = syntax_diagnostics_for_path(state, \"broken.py\")"
"+"
"+    assert result == {"
"+        \"status\": \"unavailable\","
"+        \"availability\": \"stale\","
"+        \"materialized\": False,"
"+        \"source_path\": \"broken.py\","
"+        \"errors\": None,"
"+    }"
"+    assert state.syntax_diagnostics_by_path is facts"
"+"
"+    state.resync_required = False"
"+    recovered = syntax_diagnostics_for_path(state, \"broken.py\")"
"+    assert recovered[\"status\"] == \"checked_with_errors\""
"+    assert recovered[\"availability\"] == \"fresh\""
"+    assert recovered[\"materialized\"] is True"
"+    assert recovered[\"errors\"] == [{\"message\": \"bad\"}]"
"+"
"+"
"+def test_get_name_collisions_hides_fresh_details_during_resync(tmp_path, monkeypatch):"
"+    repo = tmp_path / \"repo\""
"+    repo.mkdir()"
"+    collisions = [_collision()]"
"+    state = SimpleNamespace("
"+        resync_required=True,"
"+        collisions_state=\"fresh\","
"+        collisions=collisions,"
"+        syntax_diagnostics_state=\"fresh\","
"+        syntax_diagnostics_by_path={"
"+            \"broken.py\": {\"status\": \"checked_with_errors\", \"errors\": [{\"message\": \"bad\"}]}"
"+        },"
"+        cycles_state=\"fresh\","
"+        cycles=[[\"a\", \"b\", \"a\"]],"
"+    )"
"+    monkeypatch.setattr(mcp_runtime, \"get_or_init_engine\", lambda _root: SimpleNamespace(state=state))"
"+"
"+    result = json.loads(get_name_collisions(str(repo), representation=\"named\"))"
"+"
"+    assert result[\"availability\"] == \"stale\""
"+    assert result[\"total\"] is None"
"+    assert result[\"matched\"] is None"
"+    assert result[\"details\"] == []"
"+    assert result[\"returned\"] == 0"
"+    assert result[\"diagnostics_summary\"][\"availability\"] == {"
"+        \"syntax_errors\": \"stale\","
"+        \"name_collisions\": \"stale\","
"+        \"cycles\": \"stale\","
"+    }"
"+    assert result[\"diagnostics_summary\"][\"name_collisions\"][\"count\"] is None"
"+    assert state.collisions is collisions"
"+"
"+    state.resync_required = False"
"+    recovered = json.loads(get_name_collisions(str(repo), representation=\"named\"))"
"+    assert recovered[\"availability\"] == \"fresh\""
"+    assert recovered[\"total\"] == 1"
"+    assert len(recovered[\"details\"]) == 1"
"+"
"+"
" def test_diagnostics_summary_does_not_fabricate_unavailable_counts():"
"     summary = diagnostics_summary_for_state(SimpleNamespace("
"         collisions_state=\"deferred\", cycles_state=\"unavailable\", collisions=None, cycles=None"

## NEW_FILES_CHANGED

C:\Temp\Contextor_Repo\contextor\mcp\diagnostics.py
C:\Temp\Contextor_Repo\tests\test_mcp_diagnostics.py
C:\Temp\Contextor_Repo\walkthrough.md (raport)

## RED_RESULT

Przed patchem produkcyjnym: tests/test_mcp_diagnostics.py::test_completed_job_keeps_resync_stale_summary_identity FAILED (assert result is summary). Publiczna składnia była błędnie promowana stale/count=None do fresh/count=1 i attention_required=True. Exit 1.

## GREEN_RESULT

Po literalnym patchu ten sam test PASSED. Exit 0.

## TARGETED_REGRESSION_RESULT

Uruchomiono wskazane sześć plików: tests/test_mcp_diagnostics.py, tests/test_collisions_live_lifecycle.py, tests/analysis/test_lineage_live_query.py, tests/mcp/test_live_diagnostics_narrow.py, tests/live_state/test_runtime_canonical_query.py, tests/mcp/test_runtime_lineage_query.py, oraz istniejący tests/mcp/tools/test_analysis_status_concurrency.py::test_analysis_status_concurrency__explicit_job_id_bypasses_ambiguity. Wynik 149 passed, 1 external AuthlibDeprecationWarning, exit 0. Nie uruchomiono pełnego suite.

## PUBLIC_INTEGRATION_RESULT

Contextor get_symbol_implementation pobrał kompletny get_analysis_status.py::get_analysis_status (linie 14-147), workspace_sync=verified, revision=150. Wywołanie helpera: linia 106 diagnostics_summary_for_completed_job(diagnostics_summary(root), job), potem linie 107-108 public_job diagnostics_summary/diagnostics_attention_required. Nie zmieniono get_analysis_status.py. Nowy test test_analysis_status_keeps_resync_stale_syntax_publicly przeszedł w targeted suite: count=null, syntax availability=stale, availability.syntax_errors=stale, attention_required=false.

Contextor before edit: get_file_edit_context owner mcp.diagnostics, 8 direct module consumers; get_artifact_blast_radius helpera: direct get_analysis_status i tests.test_mcp_diagnostics, 34 downstream modules (modułowa reachability, nie dowód dynamicznej kompletności). get_symbol_lineage helpera resolved, revision=150. Source anchor w workspace odpowiadał literalnemu SEARCH. Po edit desktop_watcher update_file tests/test_mcp_diagnostics.py revision=151 i contextor/mcp/diagnostics.py revision=152; get_live_events(after_revision=150): continuity=continuous, resync_required=false. get_symbol_implementation helpera: revision=152, workspace_sync=verified, complete AST implementation, linie 141-165. get_file_edit_context obu plików: syntax checked_and_none/fresh, revision=152.

## FULL_DIFFS

Poniżej pełny diff zmian wprowadzonych wyłącznie w tym zadaniu, względem zachowanego baseline worktree. Zastany diff względem HEAD jest powyżej; zmiany te nie są przypisane temu zadaniu.

--- a/contextor/mcp/diagnostics.py
+++ b/contextor/mcp/diagnostics.py
@@ -145,6 +145,18 @@
     skipped = job.get("skipped_python_files")
     if not isinstance(skipped, list):
         return summary
+
+    syntax = summary.get("syntax_errors")
+    availability = summary.get("availability")
+    if (
+        (isinstance(syntax, dict) and syntax.get("availability") == "stale")
+        or (
+            isinstance(availability, dict)
+            and availability.get("syntax_errors") == "stale"
+        )
+    ):
+        return summary
+
     syntax_count = sum("not valid Python" in str(item.get("reason", "")) for item in skipped)
     result = dict(summary)
     result["syntax_errors"] = {"count": syntax_count, "availability": "fresh"}
--- a/tests/test_mcp_diagnostics.py
+++ b/tests/test_mcp_diagnostics.py
@@ -332,6 +332,96 @@
     monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
     result = json.loads(get_analysis_status(str(repo), job_id))
     assert result["diagnostics_summary"]["syntax_errors"] == {"count": 1, "availability": "fresh"}
+
+
+def test_completed_job_keeps_resync_stale_summary_identity():
+    state = SimpleNamespace(
+        resync_required=True,
+        syntax_diagnostics_state="fresh",
+        syntax_diagnostics_by_path={"broken.py": {"status": "checked_with_errors"}},
+        collisions_state="fresh",
+        collisions=[_collision()],
+        cycles_state="fresh",
+        cycles=[["a", "b", "a"]],
+    )
+    summary = diagnostics_summary_for_state(state)
+    result = diagnostics_summary_for_completed_job(
+        summary,
+        {"status": "completed", "operation": "project", "skipped_python_files": [{"reason": "not valid Python"}]},
+    )
+
+    assert result is summary
+    assert result["syntax_errors"] == {"count": None, "availability": "stale"}
+    assert result["availability"]["syntax_errors"] == "stale"
+    assert result["name_collisions"]["availability"] == "stale"
+    assert result["cycles"]["availability"] == "stale"
+    assert result["attention_required"] is False
+
+
+@pytest.mark.parametrize("stale_field", ["syntax_errors", "availability"])
+def test_completed_job_fail_closes_either_stale_syntax_marker(stale_field):
+    summary = diagnostics_summary_for_state(SimpleNamespace(
+        syntax_diagnostics_state="fresh", syntax_diagnostics_by_path={},
+        collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[],
+    ))
+    if stale_field == "syntax_errors":
+        summary["syntax_errors"] = {"count": None, "availability": "stale"}
+    else:
+        summary["availability"]["syntax_errors"] = "stale"
+
+    result = diagnostics_summary_for_completed_job(
+        summary,
+        {"status": "completed", "operation": "project", "skipped_python_files": [{"reason": "not valid Python"}]},
+    )
+    assert result is summary
+
+
+def test_completed_job_without_skipped_list_keeps_summary_identity():
+    summary = diagnostics_summary_for_state(SimpleNamespace())
+    assert diagnostics_summary_for_completed_job(
+        summary, {"status": "completed", "operation": "project"}
+    ) is summary
+
+
+@pytest.mark.parametrize("skipped, expected", [([], 0), ([{"reason": "not valid Python"}], 1)])
+def test_completed_job_nonstale_enrichment_preserves_other_families(skipped, expected):
+    summary = diagnostics_summary_for_state(SimpleNamespace(
+        syntax_diagnostics_state="fresh", syntax_diagnostics_by_path={},
+        collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[],
+    ))
+    result = diagnostics_summary_for_completed_job(
+        summary, {"status": "completed", "operation": "project", "skipped_python_files": skipped},
+    )
+    assert result["syntax_errors"] == {"count": expected, "availability": "fresh"}
+    assert result["availability"]["syntax_errors"] == "fresh"
+    assert result["attention_required"] is bool(expected)
+    assert result["name_collisions"] is summary["name_collisions"]
+    assert result["cycles"] is summary["cycles"]
+    assert result["availability"]["name_collisions"] == summary["availability"]["name_collisions"]
+    assert result["availability"]["cycles"] == summary["availability"]["cycles"]
+
+
+def test_analysis_status_keeps_resync_stale_syntax_publicly(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    (repo / ".contextor" / "analysis_jobs").mkdir(parents=True)
+    job_id = "b" * 32
+    (repo / ".contextor" / "analysis_jobs" / f"{job_id}.json").write_text(json.dumps({
+        "job_id": job_id, "operation": "project", "repo_path": str(repo), "status": "completed",
+        "skipped_python_files": [{"reason": "not valid Python"}], "live_publish_status": "success",
+    }), encoding="utf-8")
+    state = SimpleNamespace(
+        resync_required=True,
+        syntax_diagnostics_state="fresh", syntax_diagnostics_by_path={"broken.py": {"status": "checked_with_errors"}},
+        collisions_state="fresh", collisions=[_collision()], cycles_state="fresh", cycles=[["a", "b", "a"]],
+    )
+    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
+
+    result = json.loads(get_analysis_status(str(repo), job_id))
+    summary = result["diagnostics_summary"]
+    assert summary["syntax_errors"] == {"count": None, "availability": "stale"}
+    assert summary["availability"]["syntax_errors"] == "stale"
+    assert summary["attention_required"] is False
+    assert result["diagnostics_attention_required"] is False


 def test_wrapper_injects_health_for_analytical_not_found(tmp_path, monkeypatch):

## REMAINING_RISKS

Nie wykonano globalnej certyfikacji ani realnego runtime scenariusza resync=True; regresja publiczna używa istniejącego durable job file i cache fixture. Osiągalność szczególnego stanu na żywym serwerze nie jest dowiedziona. Funkcja non-project/running/incomplete zachowuje istniejące wczesne return; nowy test bez listy potwierdza tożsamość summary. Zastane zmiany L32F pozostają niezatwierdzone. Publiczne MCP w aktualnym procesie może nadal wykonywać załadowany wcześniej kod; lokalny focused test używa bieżącego workspace.

## RESTART_REQUIREMENTS

Zmieniono kod serwera MCP: do realnej certyfikacji nowego publicznego zachowania wymagany reload/restart odpowiedniego procesu MCP. Nie restartowano Desktop, LIVE ani MCP. Po manualnym reloadzie pierwszym krokiem jest sprawdzenie runtime freshness/schema/version i dopiero potem certyfikacja.

## FINAL_VERDICT

TARGETED_REGRESSION_PASS / PUBLIC_INTEGRATION_TEST_PASS; runtime MCP certification pending manual reload. Patch helpera literalny; osiem zastanych source/test modyfikacji zachowanych. Czekam na proceduj.

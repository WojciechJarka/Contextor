# L32G-A Public family marker normalization

## CURRENT_HEAD

`37e75674f426581d1a379ebaa76b8f034e2e5c09`

## WORKTREE_BASELINE

DIRECT_EVIDENCE: Before edits, `git status --short` showed only `M walkthrough.md` from the previous task. The four source/test files below were clean. Current HEAD matched the discovery anchor. The previous report was overwritten for this task as requested.

## FILES_CHANGED

- C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_lineage_freshness.py
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_contextor_fact_lineage.py
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_project_architecture_full_reports.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only; excluded from source/test FULL_DIFFS)

## PRE_FIX_RED

DIRECT_EVIDENCE: Added focused tests before the production patch. Ran `& .\.venv\Scripts\python.exe -m pytest -q tests/mcp/tools/test_lineage_freshness.py::test_malformed_family_marker_is_unavailable_without_mutating_state` against the old implementation. Exit 1: 30 failed in 4.14s. All five raw family fields and six invalid marker values were covered. The old public envelope passed raw invalid markers through.

## POST_FIX_GREEN

DIRECT_EVIDENCE: After the exact production patch, the six targeted test files completed with exit 0: 168 passed, 1 AuthlibDeprecationWarning, in 111.76s. No full repository test suite was run.

## TARGETED_REGRESSIONS

The run included:
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_lineage_freshness.py
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_contextor_fact_lineage.py
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_project_architecture_full_reports.py
- C:\Temp\Contextor_Repo\tests\test_h3a_workspace_canonical_freshness.py
- C:\Temp\Contextor_Repo\tests\analysis\test_lineage_live_query.py
- C:\Temp\Contextor_Repo\tests\analysis\test_lineage_query_backend.py

The new unit cases cover None, unknown string, bool, int, list and dict for each of five raw fields; unchanged source field identity; absent attributes and documented defaults; all legal derived states; all LineageFamilyStatus values; explicit resource_limit; and resync metadata separation.

## PUBLIC_INTEGRATION

CODE_PATH_PROVED by targeted tests: `get_project_architecture` exposes malformed cycles as `state_freshness.families.cycles="unavailable"` while the source marker remains unchanged. `contextor_fact_lineage` exposes malformed unselected cycles as unavailable; selected syntax_diagnostics remains fresh and status, edges and public_projections equal the baseline result.

## LINEAGE_RESOURCE_LIMIT_COMPATIBILITY

CONTRACT_PROVED by the enum-parameterized unit test and a separate explicit resource_limit test: every legal LineageFamilyStatus value, including `resource_limit`, passes through unchanged.

## LKG_COMPATIBILITY

CODE_PATH_PROVED by the passing targeted suite: existing module current-truth and LKG coverage in the six files remained green. The patch leaves `module_current_truth` and its projection logic intact.

## LIVE_REVISION_BEFORE_AFTER

Before edit: LIVE revision 152, `resync_required=false`. After edit: revision 156, `resync_required=false`. `get_live_events(after_revision=152, limit=10)` returned `continuity=continuous` with four desktop_watcher `update_file` events: revision 153 test_lineage_freshness.py, 154 test_get_project_architecture_full_reports.py, 155 test_contextor_fact_lineage.py, 156 query_helpers.py. Each event reported UPDATED. No manual update_file, restart, or full analysis was run.

## SOURCE_SYNC_VERIFICATION

DIRECT_EVIDENCE: Before edit, Contextor `get_symbol_implementation` resolved the complete `build_state_freshness` implementation at revision 152 with `workspace_sync=verified`; exact source anchors and HEAD were checked locally. After edit, the same tool resolved the complete implementation at revision 156 with `workspace_sync=verified`, lines 322-526. Contextor blast radius returned 12 direct static consumers and 44 downstream module reachability without truncation; symbol lineage resolved selected interfaces, connections and surfaces. `get_file_edit_context` reported fresh syntax checking for the edited lineage freshness test. Watcher continuity confirms source indexing, not serving MCP process reload.

## FULL_DIFFS

The following blocks are the complete current Git diffs for every source/test file changed by this task.
### contextor/mcp/query_helpers.py
~~~diff
diff --git a/contextor/mcp/query_helpers.py b/contextor/mcp/query_helpers.py
index eeea214..299dfcb 100644
--- a/contextor/mcp/query_helpers.py
+++ b/contextor/mcp/query_helpers.py
@@ -7,10 +7,30 @@ from contextor.core.analysis.state_manager import (
     canonical_artifact_consumption_targets,
     module_current_truth,
 )
+from contextor.core.domain.lineage_facts import LineageFamilyStatus

 FUZZY_MIN_SCORE: float = 0.75
 FUZZY_MAX_CANDIDATES: int = 5

+_PUBLIC_DERIVED_FAMILY_STATES = frozenset({
+    "fresh",
+    "stale",
+    "deferred",
+    "unavailable",
+})
+
+_PUBLIC_LINEAGE_FAMILY_STATES = frozenset(
+    status.value for status in LineageFamilyStatus
+)
+
+def _normalize_public_family_marker(
+    value: Any,
+    allowed: frozenset[str],
+) -> str:
+    if isinstance(value, str) and value in allowed:
+        return value
+    return "unavailable"
+

 def fuzzy_choice_candidates(
     query: str,
@@ -442,13 +462,36 @@ def build_state_freshness(

     # 5. Families
     families = {
-        "module": module_current_truth(state, target_module)["state"] if target_module else "fresh",
-        "graph": "fresh" if getattr(state, "dependency_graph", None) is not None else "unavailable",
-        "topology": getattr(state, "topology_metrics_state", "deferred"),
-        "artifact_consumption": getattr(state, "artifact_consumption_state", "deferred"),
-        "cycles": getattr(state, "cycles_state", "deferred"),
-        "collisions": getattr(state, "collisions_state", "deferred"),
-        "lineage": getattr(state, "lineage_facts_state", "not_materialized"),
+        "module": (
+            module_current_truth(state, target_module)["state"]
+            if target_module
+            else "fresh"
+        ),
+        "graph": (
+            "fresh"
+            if getattr(state, "dependency_graph", None) is not None
+            else "unavailable"
+        ),
+        "topology": _normalize_public_family_marker(
+            getattr(state, "topology_metrics_state", "deferred"),
+            _PUBLIC_DERIVED_FAMILY_STATES,
+        ),
+        "artifact_consumption": _normalize_public_family_marker(
+            getattr(state, "artifact_consumption_state", "deferred"),
+            _PUBLIC_DERIVED_FAMILY_STATES,
+        ),
+        "cycles": _normalize_public_family_marker(
+            getattr(state, "cycles_state", "deferred"),
+            _PUBLIC_DERIVED_FAMILY_STATES,
+        ),
+        "collisions": _normalize_public_family_marker(
+            getattr(state, "collisions_state", "deferred"),
+            _PUBLIC_DERIVED_FAMILY_STATES,
+        ),
+        "lineage": _normalize_public_family_marker(
+            getattr(state, "lineage_facts_state", "not_materialized"),
+            _PUBLIC_LINEAGE_FAMILY_STATES,
+        ),
     }

     # 6. Advisory Warning
~~~
### tests/mcp/tools/test_lineage_freshness.py
~~~diff
diff --git a/tests/mcp/tools/test_lineage_freshness.py b/tests/mcp/tools/test_lineage_freshness.py
index 29f838a..a3f908b 100644
--- a/tests/mcp/tools/test_lineage_freshness.py
+++ b/tests/mcp/tools/test_lineage_freshness.py
@@ -2,6 +2,7 @@ from types import SimpleNamespace

 import pytest

+from contextor.core.domain.lineage_facts import LineageFamilyStatus
 from contextor.mcp.query_helpers import build_state_freshness


@@ -46,3 +47,83 @@ def test_missing_lineage_state_fails_closed_as_not_materialized(tmp_path):
     freshness = build_state_freshness(tmp_path, state)

     assert freshness["families"]["lineage"] == "not_materialized"
+
+
+_RAW_FAMILIES = {
+    "topology_metrics_state": "topology",
+    "artifact_consumption_state": "artifact_consumption",
+    "cycles_state": "cycles",
+    "collisions_state": "collisions",
+    "lineage_facts_state": "lineage",
+}
+
+
+@pytest.mark.parametrize("field, family", _RAW_FAMILIES.items())
+@pytest.mark.parametrize("marker", [None, "pretend_fresh", True, 17, [], {}], ids=repr)
+def test_malformed_family_marker_is_unavailable_without_mutating_state(
+    tmp_path, field, family, marker
+):
+    state = _state("fresh")
+    setattr(state, field, marker)
+
+    freshness = build_state_freshness(tmp_path, state)
+
+    assert freshness["families"][family] == "unavailable"
+    assert getattr(state, field) is marker
+
+
+@pytest.mark.parametrize("field, family", _RAW_FAMILIES.items())
+def test_missing_family_marker_keeps_documented_default(tmp_path, field, family):
+    state = _state("fresh")
+    delattr(state, field)
+
+    freshness = build_state_freshness(tmp_path, state)
+
+    assert freshness["families"][family] == (
+        "not_materialized" if family == "lineage" else "deferred"
+    )
+    assert not hasattr(state, field)
+
+
+@pytest.mark.parametrize("field, family", list(_RAW_FAMILIES.items())[:4])
+@pytest.mark.parametrize("marker", ["fresh", "stale", "deferred", "unavailable"])
+def test_legal_derived_family_marker_is_preserved(tmp_path, field, family, marker):
+    state = _state("fresh")
+    setattr(state, field, marker)
+
+    freshness = build_state_freshness(tmp_path, state)
+
+    assert freshness["families"][family] == marker
+    assert getattr(state, field) == marker
+
+
+@pytest.mark.parametrize("status", list(LineageFamilyStatus))
+def test_every_legal_lineage_family_marker_is_preserved(tmp_path, status):
+    state = _state(status.value)
+
+    freshness = build_state_freshness(tmp_path, state)
+
+    assert freshness["families"]["lineage"] == status.value
+    assert state.lineage_facts_state == status.value
+
+
+def test_resource_limit_lineage_marker_remains_public(tmp_path):
+    state = _state("resource_limit")
+    assert build_state_freshness(tmp_path, state)["families"]["lineage"] == "resource_limit"
+
+
+def test_resync_keeps_canonical_stale_and_normalizes_only_malformed_family(tmp_path):
+    state = _state("fresh")
+    state.resync_required = True
+    state.cycles_state = "pretend_fresh"
+
+    freshness = build_state_freshness(tmp_path, state)
+
+    assert freshness["canonical_state"] == "stale"
+    assert freshness["families"]["cycles"] == "unavailable"
+    assert freshness["families"]["lineage"] == "fresh"
+    assert freshness["canonical_revision"] == 7
+    assert freshness["provenance"] == "snapshot"
+    assert freshness["workspace_sync"] == "unverified"
+    assert state.resync_required is True
+    assert state.cycles_state == "pretend_fresh"
~~~
### tests/mcp/tools/test_contextor_fact_lineage.py
~~~diff
diff --git a/tests/mcp/tools/test_contextor_fact_lineage.py b/tests/mcp/tools/test_contextor_fact_lineage.py
index fdfeddb..a7dadd1 100644
--- a/tests/mcp/tools/test_contextor_fact_lineage.py
+++ b/tests/mcp/tools/test_contextor_fact_lineage.py
@@ -208,6 +208,24 @@ def test_artifact_consumption_fresh_contains_both_branches_and_projections(tmp_p
     _assert_all_references_resolve(result)


+def test_fact_lineage_normalizes_unselected_family_without_changing_selected_gate(
+    tmp_path, monkeypatch
+):
+    state = _state()
+    _install(monkeypatch, tmp_path, state)
+    before = _load(contextor_fact_lineage(str(tmp_path), "syntax_diagnostics"))
+
+    state.cycles_state = "pretend_fresh"
+    after = _load(contextor_fact_lineage(str(tmp_path), "syntax_diagnostics"))
+
+    assert after["freshness"]["families"]["cycles"] == "unavailable"
+    assert after["freshness"]["families"]["syntax_diagnostics"] == "fresh"
+    assert after["status"] == before["status"]
+    assert after["edges"] == before["edges"]
+    assert after["public_projections"] == before["public_projections"]
+    assert state.cycles_state == "pretend_fresh"
+
+
 def test_artifact_consumption_stale_stops_downstream_and_reports_gap(tmp_path, monkeypatch):
     state = _state(artifact_state="stale")
     _install(monkeypatch, tmp_path, state)
~~~
### tests/mcp/tools/test_get_project_architecture_full_reports.py
~~~diff
diff --git a/tests/mcp/tools/test_get_project_architecture_full_reports.py b/tests/mcp/tools/test_get_project_architecture_full_reports.py
index f2457ff..d35614c 100644
--- a/tests/mcp/tools/test_get_project_architecture_full_reports.py
+++ b/tests/mcp/tools/test_get_project_architecture_full_reports.py
@@ -4,6 +4,7 @@ from types import SimpleNamespace

 from contextor import mcp_server
 from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.mcp.query_helpers import build_state_freshness


 architecture_tool = importlib.import_module(
@@ -169,6 +170,21 @@ def test_get_project_architecture_returns_lossless_global_report_bundle_under_50
         )


+def test_get_project_architecture_normalizes_malformed_public_family(tmp_path, monkeypatch):
+    _install_runtime(tmp_path, monkeypatch, _small_bundle())
+    engine = architecture_tool.mcp_runtime.get_or_init_engine(tmp_path)
+    engine.state.cycles_state = "pretend_fresh"
+    monkeypatch.setattr(architecture_tool.query_helpers, "build_state_freshness", build_state_freshness)
+
+    result = json.loads(mcp_server.get_project_architecture.fn(repo_path=str(tmp_path)))
+
+    assert result["status"] == "ok"
+    freshness = result["live_state"]["state_freshness"]
+    assert freshness["families"]["cycles"] == "unavailable"
+    assert freshness["families"]["lineage"] == "fresh"
+    assert engine.state.cycles_state == "pretend_fresh"
+
+
 def test_get_project_architecture_preflights_over_50k_and_reports_section_sizes(
     tmp_path,
     monkeypatch,
~~~

## REMAINING_RISKS

UNKNOWN: The running MCP server process may still hold pre-edit Python code. Source indexing and local pytest do not certify that process's public response behavior. No excluded production file was changed.

## RESTART_REQUIRED

A reload of the serving MCP process is required before runtime public-response certification of this MCP code change. The task forbids a restart; none was performed.

## FINAL_VERDICT

TARGETED_IMPLEMENTATION_PASS; RUNTIME_PUBLIC_CERTIFICATION_PENDING_RELOAD. The exact marker-normalization patch and focused regressions are complete. No redesign, extra production change, full suite, or full analysis was performed.

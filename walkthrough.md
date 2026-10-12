# CONTEXTOR_B0G2D7B_CANONICAL_LAYER_INDEX_REFRESH

## FILES_CHANGED

- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py
- C:\Temp\Contextor_Repo\tests\test_incremental_layer_report_parity.py

walkthrough.md is the task report and is excluded from FILES_CHANGED.

## SOURCE_AND_LIVE_PRECHECK

- CURRENT_HEAD before and after execution: c9b2935a465e056f8cf519a8baa8092c7a479355.
- WORKTREE_STATUS before edits: clean; both authorized target files had no preexisting diff.
- Final changed-path inspection contains only the two authorized files above. The B0G2D7A six-scenario test file is unchanged.
- Contextor LIVE was canonical fresh at revision 375 before the production edit. Source retrieval returned workspace_sync=verified, provenance=live, and fresh module/graph/topology/artifact-consumption/cycle/collision/lineage families.
- The production edit was observed at revision 376 as desktop_watcher update_file / UPDATED for contextor/core/analysis/incremental/plan_executor.py.
- The test edit was observed at revision 377 as desktop_watcher update_file / UPDATED for tests/test_incremental_layer_report_parity.py.
- Post-test event query from revision 376 returned revision 377, continuity=continuous, resync_required=false. The activity epoch remained 6899cce3f9224c428b6ef04a542d3abf.
- Post-edit Contextor fetches returned complete implementations for _build_canonical_layer_index and _refresh_canonical_layer_information with workspace_sync=verified at revision 377. The execute_refresh_plan call range was also returned in full for the relevant call boundary.
- No Contextor_Repo full analysis, manual update_file, or process restart was run.

## FULL_LAYER_INDEX_OWNER_CONTRACT

Complete source was retrieved from Contextor MCP before editing. _compute_layer_health (layer_slicer.py lines 16–184), slice_report_for_layer (lines 187–402), _layer_status (layer_pipeline.py lines 78–89), and execute_layer_pipeline (lines 16–70) were complete symbol fetches with no partial source. execute_global_pipeline (pipeline.py lines 34–708) was fetched as contiguous source ranges covering the complete function and file. Source was not accepted from preview/truncated retrieval.

The FULL facade caller invokes execute_global_pipeline without a layer_index argument; its optional layer_index parameter defaults to None. The normal full path therefore enters the layer derivation branch:

    if not layer_index:
        top_layers = sorted({
            module_id.split(".")[0]
            for module_id in modules.keys()
        })
        for layer in top_layers:
            layer_path = Path(root_path) / layer
            if not layer_path.is_dir():
                continue
            layer_sliced = slice_report_for_layer(...)

slice_report_for_layer constructs layer_modules from graph endpoints plus index_dict.registry.list_modules(), then calls _compute_layer_health with the internal hard/soft graph, cycles, collisions, hotspots, skipped-file records, summary and report header. execute_layer_pipeline calls _layer_status for the returned index record. The global pipeline sorts layer_index_data by layer and writes summary_data["layer_index"] only when that list is nonempty; AnalysisResult receives layer_index_data as its outer layer_index.

The additional FULL registry module input is reconstructable from the candidate’s module domain: build_artifact_pipeline synchronizes the registry with set(modules) before layer slicing, PersistentIdentityRegistry._sync_kind removes paths absent from that set, and list_modules returns the active path_to_id keys. The candidate builder therefore uses candidate.modules plus current graph endpoints. This source contract matches the auditor-supplied builder; no additional FULL-only layer-health fact was found.

## CANONICAL_LAYER_INDEX_BUILDER

Inserted the supplied builder immediately before _refresh_canonical_layer_information. It reads candidate module IDs, dependency_graph hard/soft edges, candidate cycles/collisions, refreshed global summary and hotspots. It performs only root/layer directory metadata checks through is_dir(); it does not invoke the full report pipeline, compact artifacts, IndexDictionary, or source parsing.

The builder calls the existing _compute_layer_health and _layer_status owners. It sorts the resulting records by layer. It derives candidate top-level layer names from candidate.modules and skips names without physical directories.

## LAYER_HEALTH_AND_STATUS_REUSE

The production code calls _compute_layer_health with the same health inputs used by FULL layer slicing: per-layer modules and hard/soft edges; global hotspots, cycles, collisions and skipped files; global summary and report header. It passes the resulting status, cycle count, hotspots and computation mode to _layer_status. No alternate or hardcoded status model was introduced.

## OUTER_AND_SUMMARY_INDEX_PARITY

_refresh_canonical_layer_information now takes keyword-only root_path. After preserving its existing graph validation, hotspot/debt calculation and summary generation, it builds layer_index from the refreshed candidate and merged summary.

For a nonempty index, the same list is installed at:
- candidate.layer_information["layer_index"]
- candidate.layer_information["summary_data"]["layer_index"]

For an empty index, the outer field is [] and summary_data removes layer_index, matching FULL. The existing execute_refresh_plan condition and position are preserved; only root_path is passed through.

## NEW_LAYER_REGRESSION

PASS: test_new_top_level_layer_matches_fresh_full_and_preserves_old_view.

The real FULL baseline had alpha and beta. Incremental update_file for gamma/__init__.py returned UPDATED and added gamma.__init__. The incremental outer and summary indexes were the same sorted alpha/beta/gamma list. The complete gamma index entry, including status and computation_mode, matched the independent fresh FULL entry. Complete layer_information projection matched fresh FULL. The prior outer layer_information dictionary and its summary dictionary remained unchanged.

## LAST_LAYER_REMOVAL_REGRESSION

PASS: test_removing_last_layer_module_matches_fresh_full_and_clears_index.

The independent FULL baseline contained gamma/only.py as its sole module. Deleting it returned DELETED and removed gamma.only. Incremental outer layer_index was []; summary_data had no layer_index key; the same assertions held for independent fresh FULL. Complete layer_information projection matched fresh FULL. The prior layer and summary dictionaries remained unchanged.

## COW_AND_NO_SOURCE_REPARSE

PASS: test_layer_index_refresh_does_not_read_or_parse_source_files.

The test prepares a candidate from a real FULL state with materialized modules and graph, then guards reads of the fixture’s unchanged Python files through builtins.open and Path.open and rejects ast.parse during builder execution. It leaves Path.is_dir and directory metadata checks available. No guarded source read or parse occurred.

The existing initializer mutation regression also passed and verified old-view preservation. The added new-layer and removal tests separately assert the previous layer-information and summary dictionaries remain unchanged.

## EXISTING_MULTILAYER_REGRESSIONS

PASS: test_multilayer_cycle_change_checks_preserved_layer_index in the primary focused layer-report suite. It continued to compare the incremental cycle change against fresh FULL and passed.

## SIX_MUTATION_MATRIX_RESULTS

The required command was run unchanged:

    C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q -x -s tests/test_incremental_multi_mutation_full_parity.py

Execution stopped at the first scenario A failure due to -x. Scenarios B–F were not executed.

## FIRST_MISMATCH_IF_ANY

The B0G2D7A scenario A update returned the expected UPDATED status with no update exception. FileState coverage matched: six expected/tracked paths, no missing paths, no extra paths, and no SHA-256 mismatches. Incremental and fresh FULL module IDs both included gamma.__init__.

The first complete canonical difference is:

    state.collision_facts["gamma.__init__"][0]["code"]
    incremental: ""
    fresh_FULL: "GAMMA_VALUE = 7"

The layer_index was not the first differing field in this broader scenario. No further diagnosis or production/test correction was attempted.

## PRESERVED_EVIDENCE

The test preserved the complete scenario A bundle and it was left intact:

    C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-572\test_case_a_new_architectural_0\b0g2d7a_a_evidence\summary.json
    C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-572\test_case_a_new_architectural_0\b0g2d7a_a_evidence\initial_full.pickle
    C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-572\test_case_a_new_architectural_0\b0g2d7a_a_evidence\incremental.pickle
    C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-572\test_case_a_new_architectural_0\b0g2d7a_a_evidence\fresh_full.pickle

summary.json records initial FULL state_id 20261012_151908 at revision 1 and fresh FULL state_id 20261012_151910 at revision 2 under repo_id ctx_15ee9044. It also records the first structural difference, all three module-ID sets, source bytes and hashes, and both complete FileState coverage results.

## REAL_FOUR_WAY_PARITY

NOT RUN. The six-scenario gate stopped at scenario A’s first canonical mismatch. The real Desktop/MCP four-way parity gate is deferred.

## ATOMICITY_RECHECK

NOT RUN. The six-scenario gate stopped at scenario A’s first canonical mismatch. The four unchanged failure-atomicity tests and additional layer/cached-analytics regressions are deferred.

## TARGETED_TEST_RESULTS

- Primary command: .venv Python with pytest -q -x -s tests/test_incremental_layer_report_parity.py — PASS, 9 passed, 1 warning, 25.54 seconds.
- Six-scenario command: .venv Python with pytest -q -x -s tests/test_incremental_multi_mutation_full_parity.py — STOPPED at scenario A, first mismatch in state.collision_facts for gamma.__init__ as recorded above; 1 failed, 1 warning, 8.02 seconds.
- No other test command was run after the mismatch.

## PY_COMPILE

PASS, exit code 0:

    C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m py_compile contextor\core\analysis\incremental\plan_executor.py tests\test_incremental_layer_report_parity.py

## GIT_DIFF_CHECK

PASS, exit code 0:

    git diff --check -- contextor/core/analysis/incremental/plan_executor.py tests/test_incremental_layer_report_parity.py

Git emitted only its line-ending notice that the LF working copies may be converted to CRLF the next time Git touches these files. No whitespace error was reported.

## LIVE_REVISION_BEFORE_AFTER

375 before the production edit; 376 after the production file’s desktop_watcher event; 377 after the authorized test file’s desktop_watcher event and post-test check. The same activity epoch was observed. The post-test event cursor from revision 376 was continuous and returned resync_required=false.

## WORKSPACE_SYNC_POSTCHECK

PASS: Contextor fetched both complete updated production functions at canonical revision 377 with workspace_sync=verified. It also returned the updated execute_refresh_plan call range. The source watcher produced UPDATED events for each of the two authorized workspace files.

## RESYNC_REQUIRED

false. Event continuity remained continuous through revision 377.

## RESTART_REQUIRED

A manual reload of the running service that imports plan_executor.py is required before operational certification. No restart was performed. Contextor source indexing/workspace synchronization does not attest that an already-running process reloaded imported code.

## FINAL_VERDICT

B0G2D7B_NEXT_CANONICAL_MISMATCH

The requested layer-index refresh and its focused regression suite pass. The unchanged six-scenario gate exposed a new first canonical mismatch in collision_facts during scenario A, so the remaining matrix, four-way parity, atomicity and related regression gates were not run.
## FULL_DIFFS

diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index ec0f52c..af962f5 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -850,8 +850,171 @@ def _refresh_canonical_artifact_consumers(
         }
 
 
+def _build_canonical_layer_index(
+    candidate: CandidateState,
+    *,
+    root_path: str | Path,
+    global_summary: dict,
+    global_hotspots: list,
+) -> list[dict]:
+    """Build FULL-compatible layer index from current canonical RAM."""
+    from types import SimpleNamespace
+
+    from contextor.core.reporting_engine.layer_pipeline import (
+        _layer_status,
+    )
+    from contextor.core.reporting_engine.layer_slicer import (
+        _compute_layer_health,
+    )
+
+    graph = candidate.dependency_graph
+    if graph is None:
+        raise RuntimeError(
+            "Cannot build layer index without canonical graph"
+        )
+
+    hard_edges = graph.hard_edges
+    soft_edges = graph.soft_edges
+
+    if not isinstance(hard_edges, dict) or not isinstance(
+        soft_edges, dict
+    ):
+        raise RuntimeError(
+            "Cannot build layer index from invalid graph"
+        )
+
+    root = Path(root_path).resolve()
+    module_ids = set(candidate.modules)
+
+    known_modules = set(module_ids)
+    known_modules.update(hard_edges)
+    for targets in hard_edges.values():
+        known_modules.update(targets)
+
+    skipped_raw = global_summary.get("skipped_files", ())
+    if not isinstance(skipped_raw, (list, tuple)):
+        raise RuntimeError(
+            "Invalid canonical skipped-file report"
+        )
+
+    skipped = []
+    for item in skipped_raw:
+        if not isinstance(item, dict):
+            raise RuntimeError(
+                "Invalid canonical skipped-file record"
+            )
+        skipped.append(SimpleNamespace(**item))
+
+    result = []
+
+    top_layers = sorted({
+        module_id.split(".")[0]
+        for module_id in module_ids
+    })
+
+    for layer in top_layers:
+        if not (root / layer).is_dir():
+            continue
+
+        def belongs(module_id: str) -> bool:
+            return (
+                module_id == layer
+                or module_id.startswith(layer + ".")
+            )
+
+        layer_modules = sorted(
+            module_id
+            for module_id in known_modules
+            if belongs(module_id)
+        )
+        layer_set = set(layer_modules)
+
+        internal_hard = {}
+        internal_soft = {}
+        inbound_hard = []
+        outbound_hard = []
+
+        for src, targets in sorted(hard_edges.items()):
+            src_in = belongs(src)
+            for target in sorted(targets):
+                target_in = belongs(target)
+                if src_in and target_in:
+                    internal_hard.setdefault(src, []).append(
+                        target
+                    )
+                elif src_in and not target_in:
+                    outbound_hard.append({
+                        "source": src,
+                        "target": target,
+                    })
+                elif not src_in and target_in:
+                    inbound_hard.append({
+                        "source": src,
+                        "target": target,
+                    })
+
+        for src, targets in sorted(soft_edges.items()):
+            if not belongs(src):
+                continue
+            for target in sorted(targets):
+                if belongs(target):
+                    internal_soft.setdefault(src, []).append(
+                        target
+                    )
+
+        internal_hard = {
+            src: sorted(set(targets))
+            for src, targets in sorted(internal_hard.items())
+        }
+        internal_soft = {
+            src: sorted(set(targets))
+            for src, targets in sorted(internal_soft.items())
+        }
+
+        health = _compute_layer_health(
+            layer_set=layer_set,
+            layer_modules=layer_modules,
+            internal_hard=internal_hard,
+            internal_soft=internal_soft,
+            inbound_hard=inbound_hard,
+            outbound_hard=outbound_hard,
+            global_hotspots=global_hotspots,
+            global_cycles=candidate.cycles,
+            global_collisions=candidate.collisions,
+            global_skipped_files=skipped,
+            global_summary=global_summary,
+            report_header=global_summary.get(
+                "report_header"
+            ),
+        )
+
+        status = _layer_status(
+            layer,
+            {
+                "layer_module_count": len(layer_modules),
+                "status": health["status"],
+                "layer_cycles_count": health[
+                    "layer_cycles_count"
+                ],
+                "hotspots": health["hotspots"],
+                "computation_mode": health[
+                    "computation_mode"
+                ],
+            },
+        )
+
+        result.append(status)
+
+    return sorted(
+        result,
+        key=lambda item: item["layer"],
+    )
+
+
 def _refresh_canonical_layer_information(
     candidate: CandidateState,
+    *,
+    root_path: str | Path,
 ) -> None:
     """Refresh FULL-compatible graph report fields from canonical RAM."""
     from contextor.core.hotspots import detect_hotspots
@@ -921,10 +1084,23 @@ def _refresh_canonical_layer_information(
         **refreshed_summary,
     }
 
+    layer_index = _build_canonical_layer_index(
+        candidate,
+        root_path=root_path,
+        global_summary=merged_summary,
+        global_hotspots=hotspots,
+    )
+
+    if layer_index:
+        merged_summary["layer_index"] = layer_index
+    else:
+        merged_summary.pop("layer_index", None)
+
     candidate.layer_information = {
         **previous,
         "hotspots": hotspots,
         "debt": debt,
+        "layer_index": layer_index,
         "summary_data": merged_summary,
     }
 
@@ -1401,7 +1577,10 @@ def execute_refresh_plan(
             or plan.graph_recomputations
         )
     ):
-        _refresh_canonical_layer_information(candidate)
+        _refresh_canonical_layer_information(
+            candidate,
+            root_path=root_path,
+        )
 
     derived_artifact_projection = None
     derived_artifact_projection_failed = False
diff --git a/tests/test_incremental_layer_report_parity.py b/tests/test_incremental_layer_report_parity.py
index ce96471..713f948 100644
--- a/tests/test_incremental_layer_report_parity.py
+++ b/tests/test_incremental_layer_report_parity.py
@@ -2,6 +2,8 @@
 
 from __future__ import annotations
 
+import ast
+import builtins
 from copy import deepcopy
 from pathlib import Path
 
@@ -11,6 +13,7 @@ from contextor.core.analysis.incremental.materialization import (
     ensure_cached_analytics,
 )
 from contextor.core.analysis.incremental.plan_executor import (
+    _build_canonical_layer_index,
     _prepare_candidate_state,
     _refresh_canonical_layer_information,
 )
@@ -138,18 +141,185 @@ def test_initializer_graph_report_matches_fresh_full_and_preserves_old_view(tmp_
     assert difference is None, f"layer report mismatch: {difference!r}; root={tmp_path}"
 
 
-def test_empty_and_untrusted_layer_views_do_not_fabricate_reports():
+def test_new_top_level_layer_matches_fresh_full_and_preserves_old_view(tmp_path):
+    _write_sources(
+        tmp_path,
+        {
+            "alpha/__init__.py": "",
+            "alpha/value.py": "ALPHA_VALUE = 1\n",
+            "beta/__init__.py": "",
+            "beta/value.py": "BETA_VALUE = 2\n",
+        },
+    )
+    baseline = _full_state(tmp_path)
+    assert {
+        item["layer"]
+        for item in baseline.layer_information["layer_index"]
+    } == {"alpha", "beta"}
+
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    engine = hydrated.engine
+    previous_layer = engine.state.layer_information
+    previous_summary = previous_layer["summary_data"]
+    previous_copy = deepcopy(previous_layer)
+
+    gamma_init = tmp_path / "gamma" / "__init__.py"
+    gamma_init.parent.mkdir(parents=True, exist_ok=True)
+    gamma_init.write_text("GAMMA_VALUE = 7\n", encoding="utf-8")
+
+    result = engine.update_file(str(gamma_init))
+    assert result.status == "UPDATED"
+    assert "gamma.__init__" in engine.state.modules
+
+    incremental = deepcopy(engine.state)
+    layer_index = incremental.layer_information["layer_index"]
+    summary_index = incremental.layer_information["summary_data"]["layer_index"]
+    assert [item["layer"] for item in layer_index] == [
+        "alpha",
+        "beta",
+        "gamma",
+    ]
+    assert layer_index == summary_index
+
+    oracle = _full_state(tmp_path)
+    full_index = oracle.layer_information["layer_index"]
+    gamma_entry = next(item for item in layer_index if item["layer"] == "gamma")
+    full_gamma_entry = next(item for item in full_index if item["layer"] == "gamma")
+    assert gamma_entry == full_gamma_entry
+    assert gamma_entry["status"] == full_gamma_entry["status"]
+    assert gamma_entry["computation_mode"] == full_gamma_entry["computation_mode"]
+    assert [item["layer"] for item in full_index] == [
+        "alpha",
+        "beta",
+        "gamma",
+    ]
+    _assert_layer_parity(incremental, oracle, tmp_path)
+
+    assert previous_layer == previous_copy
+    assert previous_summary == previous_copy["summary_data"]
+
+
+def test_removing_last_layer_module_matches_fresh_full_and_clears_index(tmp_path):
+    _write_sources(
+        tmp_path,
+        {"gamma/only.py": "GAMMA_VALUE = 7\n"},
+    )
+    baseline = _full_state(tmp_path)
+    assert [
+        item["layer"]
+        for item in baseline.layer_information["layer_index"]
+    ] == ["gamma"]
+
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    engine = hydrated.engine
+    previous_layer = engine.state.layer_information
+    previous_summary = previous_layer["summary_data"]
+    previous_copy = deepcopy(previous_layer)
+
+    source = tmp_path / "gamma" / "only.py"
+    source.unlink()
+    result = engine.update_file(str(source))
+    assert result.status == "DELETED"
+    assert "gamma.only" not in engine.state.modules
+
+    incremental = deepcopy(engine.state)
+    assert incremental.layer_information["layer_index"] == []
+    assert "layer_index" not in incremental.layer_information["summary_data"]
+
+    oracle = _full_state(tmp_path)
+    assert oracle.layer_information["layer_index"] == []
+    assert "layer_index" not in oracle.layer_information["summary_data"]
+    _assert_layer_parity(incremental, oracle, tmp_path)
+
+    assert previous_layer == previous_copy
+    assert previous_summary == previous_copy["summary_data"]
+
+
+def test_layer_index_refresh_does_not_read_or_parse_source_files(tmp_path, monkeypatch):
+    _write_sources(
+        tmp_path,
+        {
+            "alpha/__init__.py": "",
+            "alpha/value.py": "ALPHA_VALUE = 1\n",
+            "beta/__init__.py": "",
+            "beta/value.py": "BETA_VALUE = 2\n",
+        },
+    )
+    state = _full_state(tmp_path)
+    candidate = _prepare_candidate_state(state)
+    assert candidate.modules
+    assert candidate.dependency_graph is not None
+
+    repo_root = tmp_path.resolve()
+    protected_sources = {
+        path.resolve()
+        for path in tmp_path.rglob("*.py")
+    }
+    assert protected_sources
+
+    def is_protected_source(value) -> bool:
+        if isinstance(value, int):
+            return False
+        try:
+            path = Path(value).resolve()
+            path.relative_to(repo_root)
+        except (TypeError, ValueError, OSError):
+            return False
+        return path in protected_sources
+
+    original_builtin_open = builtins.open
+    original_path_open = Path.open
+
+    def guarded_builtin_open(file, *args, **kwargs):
+        if is_protected_source(file):
+            pytest.fail(f"layer refresh read unchanged Python source: {file}")
+        return original_builtin_open(file, *args, **kwargs)
+
+    def guarded_path_open(path, *args, **kwargs):
+        if is_protected_source(path):
+            pytest.fail(f"layer refresh read unchanged Python source: {path}")
+        return original_path_open(path, *args, **kwargs)
+
+    def reject_parse(*args, **kwargs):
+        pytest.fail("layer refresh parsed source instead of using canonical RAM")
+
+    monkeypatch.setattr(builtins, "open", guarded_builtin_open)
+    monkeypatch.setattr(Path, "open", guarded_path_open)
+    monkeypatch.setattr(ast, "parse", reject_parse)
+
+    index = _build_canonical_layer_index(
+        candidate,
+        root_path=tmp_path,
+        global_summary=state.layer_information["summary_data"],
+        global_hotspots=state.layer_information["hotspots"],
+    )
+
+    assert [item["layer"] for item in index] == ["alpha", "beta"]
+
+
+def test_empty_and_untrusted_layer_views_do_not_fabricate_reports(tmp_path):
     state = RepositoryAnalysisState(layer_information={})
     candidate = _prepare_candidate_state(state)
-    _refresh_canonical_layer_information(candidate)
+    _refresh_canonical_layer_information(
+        candidate,
+        root_path=tmp_path,
+    )
     assert candidate.layer_information == {}
     assert state.layer_information == {}
     candidate.layer_information = {"summary_data": None}
     with pytest.raises(RuntimeError, match="summary_data is unavailable"):
-        _refresh_canonical_layer_information(candidate)
+        _refresh_canonical_layer_information(
+            candidate,
+            root_path=tmp_path,
+        )
     candidate.layer_information = {"summary_data": {"report_header": {}}}
     with pytest.raises(RuntimeError, match="untrusted canonical facts"):
-        _refresh_canonical_layer_information(candidate)
+        _refresh_canonical_layer_information(
+            candidate,
+            root_path=tmp_path,
+        )
 
 
 @pytest.mark.parametrize("invalid_input", ["consumption", "graph"])

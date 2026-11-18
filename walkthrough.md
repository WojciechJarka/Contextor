# SP-T4-I2B5-I3 — Graph Executor Full-Rebuild Switch

## PREFLIGHT

- DIRECT_EVIDENCE — HEAD before edit: 4196228a3a57a46120070ae33d4b6162296dd32c; branch main...origin/main; git status clean.
- DIRECT_EVIDENCE — pre-change LIVE revision 1438, provenance live, canonical_state=fresh, resync_required=false.
- DIRECT_EVIDENCE — plan_executor.py and tests/test_p1d3_d2b2_type_only.py had workspace_sync=verified at revision 1438; both had fresh checked_and_none syntax diagnostics.
- DIRECT_EVIDENCE — execute_refresh_plan matched the requested signature anchor at lines 1136-1148; new_reexport_facts was the last parameter. Its docstring ended immediately before path = Path(file_path). The dependency_graph condition began with delta.is_deleted at line 1385; all listed existing alternatives were present and unchanged.
- DIRECT_EVIDENCE — T56 ended at line 4236 of the test file (source_total_lines=4237); T57 and T58 were absent before the append. The repository virtual environment is CPython 3.15.2.
- DIRECT_EVIDENCE — Contextor artifact blast radius resolved execute_refresh_plan as A1292/1 with 8 direct static consumers, including 6 test consumers; no cross-layer production consumer was reported. The new optional parameter was appended after the existing last defaulted argument, preserving prior parameter positions.
- CONTRACT_PROVED — current executor pre-populates candidate.modules only when the modules family is in the plan; the I2 type-only planner adds that family for graph changes. T57 uses a planner-generated import-change plan.

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE — added force_full_graph: bool = False after new_reexport_facts.
- DIRECT_EVIDENCE — added the exact requested bool and dependency_graph preconditions immediately after the function docstring.
- CODE_PATH_PROVED — added force_full_graph as the first existing dependency_graph rebuild condition. The delta.is_deleted, delta.is_new, package-initializer, and reexport_facts_changed conditions remain unchanged.
- DIRECT_EVIDENCE — appended exactly T57-T58. No existing tests were modified. build_graph, resolve_module_edges, PATCH/GRAPH ordering, and other patch families were not changed.

## FULL_GRAPH_EXECUTION

- CODE_PATH_PROVED — with force_full_graph=True and dependency_graph in the plan, execution enters the existing full branch: it rebuilds the trie, package root, and candidate dependency graph using build_graph.
- DIRECT_EVIDENCE — T57 observes one build_graph call and no resolve_module_edges call when true; the candidate graph contains the updated hard edge to pkg.b.
- INFERENCE / REVIEW LIMIT — the guard checks dependency_graph but not modules. The intended I2 planner output includes modules for graph deltas, and T57's RefreshPlanner import-change plan exercises that shape. A direct force_full_graph=True call with a graph-only plan is not covered; candidate.modules is only updated for an existing-module import change when modules is in the plan. No extra guard was added because the prompt specified the exact validation.

## PARTIAL_GRAPH_COMPATIBILITY

- CODE_PATH_PROVED — the default false value leaves existing rebuild conditions unchanged and retains the existing resolve_module_edges path for ordinary in-place module changes.
- DIRECT_EVIDENCE — T57 observes resolve_module_edges once for pkg.a and no build_graph call when false.
- DIRECT_EVIDENCE — T17-T21 and T49-T56 passed with the new parameter default, covering existing planner/executor behavior and type-only plan scope.
- DIRECT_EVIDENCE — no call sites were modified; the appended defaulted parameter preserves existing callers' positional arguments.

## INVALID_REQUEST_FAIL_CLOSED

- CODE_PATH_PROVED — non-exact-bool inputs raise TypeError before path construction or candidate creation.
- CODE_PATH_PROVED — force_full_graph=True without dependency_graph in plan.patch_families raises ValueError before candidate creation.
- DIRECT_EVIDENCE — T58 covers 1 and "yes" as TypeError cases and True with an empty RefreshPlan as ValueError.

## CANDIDATE_ISOLATION

- DIRECT_EVIDENCE — T57 records the original engine graph identity and verifies it is unchanged after execution while outcome.candidate_state contains the rebuilt or partially updated graph.
- CODE_PATH_PROVED — execute_refresh_plan returns a PlanExecutionOutcome containing candidate state; this patch does not publish candidate graph state to RepositoryAnalysisState.

## TARGETED_TESTS

- DIRECT_EVIDENCE — ran explicit nodes T57-T58, T49-T56, and T17-T21 using repository .venv CPython 3.15.2.
- DIRECT_EVIDENCE — result: 23 passed in 10.96s.
- DIRECT_EVIDENCE — no full pytest suite was run.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE — canonical LIVE revision 1440, provenance live, canonical_state=fresh, resync_required=false.
- DIRECT_EVIDENCE — continuous desktop_watcher events: revision 1439 UPDATED plan_executor.py; revision 1440 UPDATED tests/test_p1d3_d2b2_type_only.py.
- DIRECT_EVIDENCE — workspace_sync=verified for both changed files at revision 1440.
- DIRECT_EVIDENCE — both files have fresh checked_and_none syntax diagnostics with errors=[]. Global syntax diagnostic count is 0 and fresh.
- DIRECT_EVIDENCE — graph and cycles are fresh at revision 1440.
- UNKNOWN — workspace sync does not prove the running process adopted the code. Runtime adoption was not inspected; no restart or MCP update_file was performed.

## FINAL_VERDICT

I2B5_I3_PASS

The exact executor switch and fail-closed preconditions are present, requested focused tests pass, and post-change LIVE evidence is fresh. This verdict covers executor behavior with the tested RefreshPlan shapes; it does not claim engine wiring or runtime process adoption.

## FILES_CHANGED

- contextor/core/analysis/incremental/plan_executor.py
- tests/test_p1d3_d2b2_type_only.py

walkthrough.md is overwritten as the required report artifact and is not counted as an implementation/test file.

## FULL_DIFFS

Complete changed-line diff from git diff --unified=0:

~~~~diff
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 521e722..c27a8ff 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -1147,0 +1148 @@ def execute_refresh_plan(
+    force_full_graph: bool = False,
@@ -1152,0 +1154,12 @@ def execute_refresh_plan(
+    if type(force_full_graph) is not bool:
+        raise TypeError(
+            "force_full_graph must be bool"
+        )
+    if (
+        force_full_graph
+        and "dependency_graph" not in plan.patch_families
+    ):
+        raise ValueError(
+            "Full graph rebuild requires dependency_graph patch"
+        )
+
@@ -1385 +1398,2 @@ def execute_refresh_plan(
-                delta.is_deleted
+                force_full_graph
+                or delta.is_deleted
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 0057522..829a0e8 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -4237,0 +4238,131 @@ def test_sp_t4_i2b5_i2_t56_preserve_plan_contract(
+
+@pytest.mark.parametrize(
+    "force_full_graph", [False, True]
+)
+def test_sp_t4_i2b5_i3_t57_executor_graph_switch(
+    tmp_path, isolated_dirs, monkeypatch,
+    force_full_graph,
+):
+    from contextor.core.analysis.incremental import (
+        plan_executor as executor,
+    )
+
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    _, engine = _i1_full_engine(root)
+
+    target = root / "pkg/a.py"
+    target.write_text(
+        _i2b1_source(guarded=False),
+        encoding="utf-8",
+    )
+
+    prepared = preparation.prepare_source_update(
+        file_path=target,
+        module_path="pkg.a",
+        is_new=False,
+        old_module=engine.state.modules["pkg.a"],
+        old_artifacts=engine.state.artifacts.get("pkg.a"),
+        old_usage=engine.state.module_usages.get("pkg.a"),
+        persistent_id=engine.registry.get_module_id("pkg.a"),
+        old_collision_facts=engine.state.collision_facts.get("pkg.a"),
+        old_reexport_facts=engine.state.reexport_facts_by_module.get(
+            "pkg.a"
+        ),
+        source_key="pkg/a.py",
+    )
+    assert not prepared.has_error
+
+    plan = RefreshPlanner.plan_refresh(
+        prepared.delta,
+        usage_delta=prepared.usage_delta,
+        module_usages=engine.state.module_usages,
+        collision_facts_changed=prepared.collision_facts_changed,
+    )
+    assert "dependency_graph" in plan.patch_families
+
+    original_build = executor.build_graph
+    original_resolve = executor.resolve_module_edges
+    build_calls = []
+    resolve_calls = []
+
+    def observed_build(*args, **kwargs):
+        build_calls.append(True)
+        return original_build(*args, **kwargs)
+
+    def observed_resolve(*args, **kwargs):
+        resolve_calls.append(args[0])
+        return original_resolve(*args, **kwargs)
+
+    monkeypatch.setattr(
+        executor, "build_graph", observed_build
+    )
+    monkeypatch.setattr(
+        executor, "resolve_module_edges", observed_resolve
+    )
+
+    previous_graph = engine.state.dependency_graph
+
+    outcome = executor.execute_refresh_plan(
+        state=engine.state,
+        delta=prepared.delta,
+        usage_delta=prepared.usage_delta,
+        plan=plan,
+        new_imports=prepared.new_imports,
+        new_artifacts=prepared.new_artifacts,
+        new_usage=prepared.new_usage,
+        root_path=root,
+        file_path=str(target.resolve()),
+        new_collision_facts=prepared.new_collision_facts,
+        new_reexport_facts=prepared.new_reexport_facts,
+        force_full_graph=force_full_graph,
+    )
+
+    assert len(build_calls) == int(force_full_graph)
+    assert resolve_calls == (
+        [] if force_full_graph else ["pkg.a"]
+    )
+    assert (
+        outcome.candidate_state.dependency_graph
+        is not None
+    )
+    assert engine.state.dependency_graph is previous_graph
+    assert (
+        "pkg.b"
+        in outcome.candidate_state.dependency_graph
+        .hard_edges["pkg.a"]
+    )
+
+
+@pytest.mark.parametrize(
+    "force_full_graph,expected_exception",
+    [
+        (1, TypeError),
+        ("yes", TypeError),
+        (True, ValueError),
+    ],
+)
+def test_sp_t4_i2b5_i3_t58_invalid_graph_request(
+    tmp_path, force_full_graph, expected_exception,
+):
+    from contextor.core.analysis.incremental import (
+        plan_executor as executor,
+    )
+    from contextor.core.analysis.state_manager import FileDelta
+    from contextor.core.domain.refresh_plan import RefreshPlan
+
+    with pytest.raises(expected_exception):
+        executor.execute_refresh_plan(
+            state=RepositoryAnalysisState(),
+            delta=FileDelta(module_path="pkg.a"),
+            usage_delta=None,
+            plan=RefreshPlan(),
+            new_imports=[],
+            new_artifacts={},
+            new_usage=None,
+            root_path=tmp_path,
+            file_path=str(tmp_path / "a.py"),
+            force_full_graph=force_full_graph,
+        )
+

~~~~

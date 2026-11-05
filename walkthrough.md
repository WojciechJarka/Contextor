# CONTEXTOR C16-B03-P1A-R1

## PREFLIGHT

DIRECT_EVIDENCE: local HEAD fda84f2c23557b2551146ce9efab6b9333267213; initial worktree clean. P0 and P1A source present. CPython 3.15.2 from .venv. MCP preflight revision 992, production planner and test both workspace_sync=verified, canonical_state=fresh, cycle_semantics=stale, structural DFS path count 16. Intended edit scope: tests/test_cycle_semantics_optional_child_source_cohort.py only; walkthrough.md report.

## MCP_DISCOVERY

Contextor module contexts identify the test and planner as current canonical modules. Existing P1A planner is the owner of selected-source capacity checks; no production edit was authorized. Earlier focused P1A result was 7 PASS and selected regression result 13 PASS. The P0 cases remain in tests/test_p1d3_package_cycle_integration.py.

## ORIGINAL_N05_FALSE_POSITIVE

CODE_PATH_PROVED: previous N05 added 257 targets to hard["pkg.a"] without adding corresponding hard graph keys. The planner validates target membership before computing closures, so that test only reached "Invalid hard graph targets". Its generic ValueError assertion could pass for the wrong reason.

## N05A_INITIAL_CLOSURE_LIMIT

Valid pure graph: pkg.a and pkg.b cycle; pkg.__init__ indexed; 257 pkg.extraN keys and corresponding hard targets from pkg.a. Exact fact domain matches graph. Assertion requires ValueError with exact "Selected source capacity exceeded". PASS.

## N05B_OPTIONAL_EXPANSION_LIMIT

Valid graph: initial hard-only closure below 256; 257 indexed pkg.childN modules are absent from hard reachability. pkg.a contains one valid ImportRef with 257 named members. Expansion reaches the exact capacity exception. PASS.

## N05C_MULTI_SCC_UNION_LIMIT

Two disjoint cyclic SCCs each reach 128 separate dependencies; each individual cohort is within 256, their union exceeds 256. All target keys and import domains are valid. Exact capacity exception asserted. PASS.

## N05D_GRAPH_DOMAIN_CONTROL

Separate forged target pkg.missing has no graph key. Exact "Invalid hard graph targets" exception asserted. PASS.

## N06_FIXED_POINT_CYCLE

Separate indexed pkg.value optional child imports pkg.a. Test asserts retained SCC members, optional child, deterministic recomputation and unchanged hard graph. PASS.

## POSITIVE_TEST_ISOLATION

Compound P02-P07 fixture is reused by separate tests with specific assertions: optional named child, eventual reexport suppression of soft edge, transitive hard dependency, second-level optional child, ancestor initializers, and import fact ordering. Each mechanism has its own failure location. PASS.

## TARGETED_PYTEST_RESULTS

Modified P1A file: 16 PASS. Selected P0 named-member and canonical graph/closure regressions: 13 PASS, 129 deselected. Both used .venv CPython 3.15.2 with -B -q -rs -p no:cacheprovider and external --basetemp C:\Temp\Contextor_C16_P1A_R1_pytest_tmp. No full suite.

## PRODUCTION_SOURCE_UNCHANGED

Git status after edits showed only the test file modified before writing the report. Planner and all other production files unchanged. No commit, FULL, restart, dependency installation or update_file.

## POST_CHANGE_MCP_AUDIT

Initial post-edit target query was out_of_sync at revision 992 while watcher indexing was pending; architecture query then showed revision 993. Final target module query at revision 993: canonical_state=fresh, workspace_sync=verified, advisory_warning=null. Production planner at revision 992 was verified. Structural DFS paths remained 16; cycle_semantics stayed stale. Fresh indexed source does not prove backend loaded-code adoption.

## FILES_CHANGED

- tests/test_cycle_semantics_optional_child_source_cohort.py

walkthrough.md is the report and excluded from test/source diff accounting.

## FULL_DIFFS

```diff
diff --git a/tests/test_cycle_semantics_optional_child_source_cohort.py b/tests/test_cycle_semantics_optional_child_source_cohort.py
index 33d5544..6402c68 100644
--- a/tests/test_cycle_semantics_optional_child_source_cohort.py
+++ b/tests/test_cycle_semantics_optional_child_source_cohort.py
@@ -50,7 +50,7 @@ def test_p01_no_indexed_child_preserves_original(tmp_path):
     assert graph.hard_edges
 
 
-def test_p02_to_p07_fixed_point_and_reexport_shadow(tmp_path):
+def _fixed_point_case(tmp_path):
     files = {
         "contextor/__init__.py": "pass\n",
         "contextor/ui/__init__.py": "theme = 1\n",
@@ -61,7 +61,44 @@ def test_p02_to_p07_fixed_point_and_reexport_shadow(tmp_path):
         "contextor/a.py": "import contextor.b\nfrom contextor.ui import theme\n",
         "contextor/b.py": "import contextor.a\n",
     }
-    graph, imports, original, expanded = _candidate(tmp_path, files)
+    return _candidate(tmp_path, files)
+
+
+def test_p02_optional_named_child(tmp_path):
+    _, _, original, expanded = _fixed_point_case(tmp_path)
+    assert "contextor.ui.theme" in expanded[0].evidence_source_modules
+    assert "contextor.ui.theme" not in original[0].evidence_source_modules
+
+
+def test_p03_eventual_reexport_shadow(tmp_path):
+    graph, _, _, expanded = _fixed_point_case(tmp_path)
+    assert "contextor.ui.theme" not in graph.soft_edges["contextor.a"]
+    assert "contextor.ui.theme" in expanded[0].evidence_source_modules
+
+
+def test_p04_transitive_hard_dependency(tmp_path):
+    graph, _, original, expanded = _fixed_point_case(tmp_path)
+    assert "contextor.extra" in graph.hard_edges["contextor.ui.theme"]
+    assert "contextor.extra" not in original[0].evidence_source_modules
+    assert "contextor.extra" in expanded[0].evidence_source_modules
+
+
+def test_p05_second_level_optional_child(tmp_path):
+    graph, _, _, expanded = _fixed_point_case(tmp_path)
+    assert "contextor.repo_generator.run_repo_generator" not in graph.hard_edges["contextor.extra"]
+    assert "contextor.repo_generator.run_repo_generator" in expanded[0].evidence_source_modules
+
+
+def test_p06_ancestor_initializers(tmp_path):
+    _, _, original, expanded = _fixed_point_case(tmp_path)
+    assert {"contextor.ui.__init__", "contextor.repo_generator.__init__"} <= set(
+        expanded[0].evidence_source_modules
+    )
+    assert expanded[0].implicit_initializer_modules == original[0].implicit_initializer_modules
+
+
+def test_p07_fact_order_independence(tmp_path):
+    graph, imports, original, expanded = _fixed_point_case(tmp_path)
     selected = set(expanded[0].evidence_source_modules)
     assert {"contextor.ui.theme", "contextor.extra",
             "contextor.repo_generator.run_repo_generator",
@@ -117,16 +154,71 @@ def test_n03_n04_ambiguity_and_invalid_relative(tmp_path):
             {name: rows for name, rows in imports.items() if name != "pkg"})
 
 
-def test_n05_capacity_and_n06_cycle(tmp_path):
+def _pure_capacity_graph(extra_count):
+    hard = {"pkg.__init__": set(), "pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}}
+    hard.update({f"pkg.extra{i}": set() for i in range(extra_count)})
+    return hard, {name: [] for name in hard}
+
+
+def test_n05a_initial_hard_closure_capacity():
+    hard, imports = _pure_capacity_graph(257)
+    hard["pkg.a"].update(f"pkg.extra{i}" for i in range(257))
+    assert set(hard["pkg.a"]) <= set(hard)
+    assert set(imports) == set(hard)
+    with pytest.raises(ValueError, match="^Selected source capacity exceeded$"):
+        compute_cycle_model_source_closures_with_optional_children(hard, imports)
+
+
+def test_n05b_optional_expansion_capacity():
+    hard = {"pkg.__init__": set(), "pkg.a": {"pkg.b", "pkg.__init__"},
+            "pkg.b": {"pkg.a"}}
+    hard.update({f"pkg.child{i}": set() for i in range(257)})
+    imports = {name: [] for name in hard}
+    imports["pkg.a"] = [ImportRef(
+        module="pkg", level=0,
+        names=[f"child{i}" for i in range(257)], is_from_import=True
+    )]
+    assert len(compute_cycle_model_source_closures(hard)[0].evidence_source_modules) < 256
+    assert set(imports) == set(hard)
+    with pytest.raises(ValueError, match="^Selected source capacity exceeded$"):
+        compute_cycle_model_source_closures_with_optional_children(hard, imports)
+
+
+def test_n05c_multiple_scc_union_capacity():
+    hard = {"one.a": {"one.b"}, "one.b": {"one.a"},
+            "two.a": {"two.b"}, "two.b": {"two.a"}}
+    for prefix in ("one", "two"):
+        for i in range(128):
+            hard[f"{prefix}.extra{i}"] = set()
+            hard[f"{prefix}.a"].add(f"{prefix}.extra{i}")
+    imports = {name: [] for name in hard}
+    closures = compute_cycle_model_source_closures(hard)
+    assert len(closures) == 2
+    assert all(len(row.evidence_source_modules) <= 256 for row in closures)
+    assert len(set().union(*(set(row.evidence_source_modules) for row in closures))) > 256
+    with pytest.raises(ValueError, match="^Selected source capacity exceeded$"):
+        compute_cycle_model_source_closures_with_optional_children(hard, imports)
+
+
+def test_n05d_invalid_hard_target_control(tmp_path):
     graph, imports, _, _ = _candidate(tmp_path, BASE)
     hard = {name: set(targets) for name, targets in graph.hard_edges.items()}
-    hard["pkg.a"].update(f"extra{i}" for i in range(257))
-    all_imports = {**imports, **{f"extra{i}": [] for i in range(257)}}
-    with pytest.raises(ValueError):
-        compute_cycle_model_source_closures_with_optional_children(hard, all_imports)
+    hard["pkg.a"].add("pkg.missing")
+    with pytest.raises(ValueError, match="^Invalid hard graph targets$"):
+        compute_cycle_model_source_closures_with_optional_children(hard, imports)
+
+
+def test_n06_optional_fixed_point_cycle(tmp_path):
     files = {**BASE, "pkg/value.py": "from pkg import a\n"}
-    _, _, _, expanded = _candidate(tmp_path / "cycle", files)
-    assert {"pkg.value", "pkg.a"} <= set(expanded[0].evidence_source_modules)
+    graph, imports, _, expanded = _candidate(tmp_path, files)
+    before = {name: set(targets) for name, targets in graph.hard_edges.items()}
+    selected = set(expanded[0].evidence_source_modules)
+    assert set(expanded[0].members) <= selected
+    assert {"pkg.value", "pkg.a"} <= selected
+    assert compute_cycle_model_source_closures_with_optional_children(
+        graph.hard_edges, imports
+    ) == expanded
+    assert graph.hard_edges == before
 
 
 def test_n08_n09_n10_candidate_never_certifies_or_mutates(tmp_path):
```

## FINAL_VERDICT

C16_B03_P1A_R1_PASS

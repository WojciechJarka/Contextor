# CPA_FILE_UPDATE_TRANSITIVE_PROPAGATION_REPRO

STATUS=REPRODUCER_FAILED_AS_EXPECTED
HEAD=a7a4a3645ab0a642380833e78542d5aa8a894432

ACCEPTED_PREEXISTING_WORKTREE
- At step start, git status was clean at HEAD above.
- The previously approved canonical definition payload fix is already present in HEAD and was treated as accepted preexisting work.
- The test file had no diff against HEAD before this task.
- The current task changed only the test file listed under FILES_CHANGED; no production file changed.

SOURCE_DRIFT=NONE
- Exact target file and insertion anchor matched current HEAD.
- The canonical key a::foo is consistent with the existing module::symbol target contract and existing literal test fixtures such as a::foo and target::foo.
- Production files compare cleanly against HEAD.

REPRO_CONTRACT
- Baseline files: a.py defines VALUE only; b.py imports foo from a; c.py imports b and calls b.foo().
- Baseline analysis calls update_file for A, B, and C.
- The only post-baseline disk write and update_file call is for A, adding foo().
- The test compares incremental canonical artifact_consumption[a::foo] with a fresh _build_full_static_state(tmp_path) oracle. B and C are not rewritten or manually updated.

CONTEXTOR_AND_SOURCE_EVIDENCE
- Contextor get_symbol_implementation resolved _find_dependent_consumers to contextor/core/analysis/refresh_planner.py:14-56; its implementation iterates module usage references and returns a set of dependent module paths.
- Contextor get_symbol_implementation resolved _build_reexport_map to contextor/core/reference/shared.py:50-129; its implementation computes a cycle-safe transitive re-export identity map. The executor imports the shared re-export helper through contextor.core.reference.engine.
- Contextor get_symbol_implementation resolved _rebuild_consumer_slice to contextor/core/analysis/incremental/plan_executor.py:260-470; it rebuilds one consumer's artifact_consumption slice using the supplied re-export map.
- Contextor get_symbol_implementation resolved execute_refresh_plan to contextor/core/analysis/incremental/plan_executor.py:574-1006.
- Contextor get_source_range returned the literal executor block at lines 674-705: it loops once over plan.recompute_modules, rebuilding each listed consumer slice.
- Contextor get_source_range returned lines 735-765: the artifact_consumption patch rebuilds delta.module_path using new_usage; this is the changed file A in this scenario.
- Contextor search_source returned the existing _build_full_static_state helper in tests/test_completeness_freshness_parity_proof.py:33-42. It runs ContextorFacade.analyze_project(repo_dir), hydrates the repository engine, and returns that fresh state.
- Contextor artifact_consumption fact lineage resolved with status=ok, owner=RepositoryAnalysisState.artifact_consumption, provenance=live, canonical_state=fresh, resync_required=false at revision 1474. _rebuild_consumer_slice is listed as the incremental consumer-slice producer. The narrower get_symbol_lineage request for _rebuild_consumer_slice returned confirmation_required due output size; complete implementation source was separately obtained with get_symbol_implementation.

DIRECT_RECOMPUTE_SET
- Observed from the actual failing test result: result.shadow_plan.recompute_modules=('b',).
- B was selected; C was not selected.

INCREMENTAL_ARTIFACT_CONSUMPTION
{'consumers': ['b'], 'channels': {'b': ['api_imports']}}

FULL_ORACLE_ARTIFACT_CONSUMPTION
{'consumers': ['b', 'c'], 'channels': {'c': ['direct_calls'], 'b': ['api_imports']}}

TEST_NODE_ID
tests/test_completeness_freshness_parity_proof.py::test_transitive_reexport_late_provider_matches_full_oracle

TEST_RESULT
- Ran only the requested node ID, using one physical Windows command:
  & .\.venv\Scripts\python.exe -m pytest tests/test_completeness_freshness_parity_proof.py::test_transitive_reexport_late_provider_matches_full_oracle -q
- Result: 1 failed in 5.70s.
- Both oracle preconditions passed: b and c were present in full_entry.consumers.
- Failure occurred at the incremental/full consumer-set comparison. The assertion showed incremental ['b'] versus full ['b', 'c']; recompute_modules=('b',).

CLASSIFICATION=CONFIRMED_TRANSITIVE_CANONICAL_PROPAGATION_DEFECT

LIVE_AND_RUNTIME
- No MCP update_file, analyze_project on the repository, process restart, or runtime reload was performed.
- The desktop watcher later emitted UPDATED for the test file at revision 1474; continuity=continuous and resync_required=false. This is source indexing evidence only; the reproducer itself ran in a fresh pytest process as requested.

FILES_CHANGED
- tests/test_completeness_freshness_parity_proof.py
- walkthrough.md is this required report and is not counted as a source/test diff.

ACTUAL_DIFF / FULL_DIFF

diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index 473672f..e1698f4 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -916,6 +916,71 @@ def test_incremental_global_add_matches_full_oracle(tmp_path):
     )


+def test_transitive_reexport_late_provider_matches_full_oracle(tmp_path):
+    f_provider = tmp_path / "a.py"
+    f_reexport = tmp_path / "b.py"
+    f_consumer = tmp_path / "c.py"
+
+    f_provider.write_text("VALUE = 1\n", encoding="utf-8")
+    f_reexport.write_text("from a import foo\n", encoding="utf-8")
+    f_consumer.write_text(
+        "import b\n"
+        "\n"
+        "def run():\n"
+        "    return b.foo()\n",
+        encoding="utf-8",
+    )
+
+    cache_dir = tmp_path / "cache"
+    cache_dir.mkdir()
+
+    engine = IncrementalAnalysisEngine(
+        RepositoryAnalysisState(modules={}),
+        PersistentIdentityRegistry(str(tmp_path)),
+        FileStateManager(str(cache_dir)),
+        str(tmp_path),
+    )
+
+    engine.update_file(str(f_provider))
+    engine.update_file(str(f_reexport))
+    engine.update_file(str(f_consumer))
+
+    f_provider.write_text(
+        "VALUE = 1\n"
+        "\n"
+        "def foo():\n"
+        "    return 1\n",
+        encoding="utf-8",
+    )
+
+    result = engine.update_file(str(f_provider))
+    oracle = _build_full_static_state(tmp_path)
+
+    incremental_entry = engine.state.artifact_consumption.get(
+        "a::foo",
+        {},
+    )
+    full_entry = oracle.artifact_consumption.get(
+        "a::foo",
+        {},
+    )
+
+    assert "b" in full_entry.get("consumers", [])
+    assert "c" in full_entry.get("consumers", [])
+
+    assert sorted(
+        incremental_entry.get("consumers", [])
+    ) == sorted(
+        full_entry.get("consumers", [])
+    ), (
+        "transitive canonical propagation differs from fresh full oracle: "
+        f"incremental={incremental_entry!r}, full={full_entry!r}, "
+        f"recompute_modules={result.shadow_plan.recompute_modules!r}"
+    )
+
+    _assert_full_parity(engine.state, oracle)




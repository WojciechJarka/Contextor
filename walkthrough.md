# CPA_FILE_UPDATE_PROPAGATION_GENERALITY_GATE

STATUS=PARTIAL_DEFECT_CONFIRMED

HEAD_BEFORE=9f740a57dcf324a7bbcfd11af86c5a92c71fc8a4

ACCEPTED_PREEXISTING_WORKTREE=The previous fixpoint production implementation and cycle-oracle test are accepted and present in HEAD_BEFORE. The worktree was clean before this task. They were left unchanged; this task adds only the three requested tests.

SOURCE_DRIFT=NONE. The three requested test names were absent at HEAD. Existing imports/helpers required by the snippets (`ContextorFacade`, `hydrate_repository_engine`, `_build_full_static_state`, and `_assert_full_parity`) were present. Only `tests/test_completeness_freshness_parity_proof.py` changed. `git diff --check` passed; Git emitted only LF-to-CRLF working-copy notices.

DIRECT_EVIDENCE=The single targeted pytest command returned `3 failed in 9.51s`. Symbol removal: the seed assertion passed with `('b',)`, while actual execution was `('b',)` against expected `('b', 'c')`. Re-export retarget: `_build_full_static_state` raised `ValidationError(kind='NAME_COLLISION')` for function `foo` across modules `a` and `d`, before seed/execution/parity assertions. Ambiguity: full analysis returned `errors=[]`; the hydrated oracle had `pkg.a::B.foo={'consumers': ['consumer'], 'channels': {'consumer': ['direct_calls']}}`, while incremental state had `{'consumers': [], 'channels': {}}`.

CODE_PATH_PROVED=Contextor fact lineage at revision 1479 returned fresh canonical `artifact_consumption` state with `resync_required=false`. It identifies `RepositoryAnalysisState.artifact_consumption` as owner, `ContextorFacade.analyze_project` as full materializer, `_rebuild_consumer_slice` as incremental consumer-slice producer, `_apply_delta_and_commit` as incremental state writer, and snapshot hydration through `hydrate_repository_engine`. Symbol lineage resolved `_rebuild_consumer_slice` as active artifact `A2180/1` with complete metadata at revision 1479.

CONTRACT_PROVED=The symbol-remove planner assertion established the direct seed `('b',)`; the next assertion directly disproved the requested execution trace. The ambiguity full-analysis setup and hydration succeeded with no validation errors, and its first compared canonical key directly mismatched. Full parity was not completed for all three tests.

INFERENCE=NONE. In particular, the symbol-remove execution mismatch is not reported as a canonical payload mismatch because its payload parity assertions were not reached.

UNKNOWN=Re-export-retarget's actual shadow-plan seed and execution trace were not emitted: `_build_full_static_state` failed before those assertions. Symbol-remove's final incremental-vs-full canonical payload equality is unknown because the execution-trace assertion failed before the remaining assertions. In the ambiguity test, the second target key and freshness-state assertion were not reached after the first direct mismatch.

SYMBOL_REMOVE_RESULT=FAIL at the required execution-trace assertion. `_build_full_static_state(tmp_path)` completed first, and the planned seed assertion passed. Actual trace was `('b',)`; expected trace was `('b', 'c')`. The assertions for `a::foo` absence and `_assert_full_parity` did not execute.

SYMBOL_REMOVE_PLANNED_VS_EXECUTED=planned `('b',)`; actual executed `('b',)`; expected executed affected set `('b', 'c')`. CLASSIFICATION=PROPAGATION_EXECUTION_MISMATCH_PARITY_UNVERIFIED.

REEXPORT_RETARGET_RESULT=BLOCKED before seed and parity assertions. The full-oracle helper rejected the analysis result because of `NAME_COLLISION`: `Semantic API collision for function 'foo' across modules: a, d`. No test change was made to bypass or suppress the validator. CLASSIFICATION=BLOCKED_ORACLE_VALIDATION_ERROR.

REEXPORT_RETARGET_PLANNED_VS_EXECUTED=NOT_OBSERVED. The real seed cannot be reported from this run because the failure occurred while constructing the oracle, before the test's `shadow_plan.recompute_modules` and execution-trace assertions. The test's expected seed `('c',)` remains unverified; it was not substituted or weakened.

AMBIGUITY_INCREMENTAL_STATE=For the first tested key `pkg.a::B.foo`, incremental value was `{'consumers': [], 'channels': {}}`. The comparison failed before the second key, freshness, and result-state assertions.

AMBIGUITY_FULL_STATE=For `pkg.a::B.foo`, freshly hydrated full canonical value was `{'consumers': ['consumer'], 'channels': {'consumer': ['direct_calls']}}`. This is a direct canonical mismatch against incremental state.

AMBIGUITY_VALIDATION_ERRORS=The ambiguity full-analysis call returned `errors=[]`; `hydrate_repository_engine(tmp_path)` returned a non-null engine, and the test reached canonical comparison. CLASSIFICATION=CONFIRMED_CANONICAL_PARITY_DEFECT.

TEST_RESULTS=Ran one physical pytest command containing only the three requested node IDs, exit code 1: `3 failed in 9.51s`. No previous fixpoint nodes or full suite were run. Failures were left intact; no production code or expectations were changed after the run.

CLASSIFICATION_NOTE=The required parity label is applied only where full-vs-incremental canonical evidence exists. The first test directly fails its affected execution-set assertion before payload parity, and the second stops while constructing its full oracle; labeling either as a confirmed canonical payload mismatch would exceed the observed evidence.

CLASSIFICATION_PER_TEST=
- `test_transitive_reexport_symbol_remove_matches_full_oracle`: `PROPAGATION_EXECUTION_MISMATCH_PARITY_UNVERIFIED` — actual trace omitted `c`; payload parity was not reached.
- `test_reexport_retarget_matches_full_oracle`: `BLOCKED_ORACLE_VALIDATION_ERROR` — full helper stopped on the reported name collision before exposing the seed or comparing state.
- `test_natural_ambiguity_transition_matches_full_oracle_state`: `CONFIRMED_CANONICAL_PARITY_DEFECT` — direct full-vs-incremental mismatch for `pkg.a::B.foo`.

LIVE_EVIDENCE=Pre-edit Contextor revision was 1479. `get_live_events(repo_path='C:\Temp\Contextor_Repo', after_revision=1479)` returned revision 1480, origin `desktop_watcher`, status `UPDATED` for the test file, `continuity='continuous'`, and `resync_required=false`. No MCP `update_file`, Desktop/MCP/backend restart, or full analysis of the actual Contextor repository was performed. The two `analyze_project` calls occurred only inside tests against their `tmp_path` repositories.

FILES_CHANGED=
- `tests/test_completeness_freshness_parity_proof.py`

## ACTUAL_DIFF — tests/test_completeness_freshness_parity_proof.py

```diff
diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index bb5037f..ae5ccf1 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -1138,6 +1138,279 @@ def test_transitive_propagation_cycle_terminates_without_duplicate_recompute(
     )
 
 
+def test_transitive_reexport_symbol_remove_matches_full_oracle(tmp_path):
+    f_provider = tmp_path / "a.py"
+    f_reexport = tmp_path / "b.py"
+    f_consumer = tmp_path / "c.py"
+
+    f_provider.write_text(
+        "def foo():\n"
+        "    return 1\n"
+        "\n"
+        "def keep():\n"
+        "    return 2\n",
+        encoding="utf-8",
+    )
+    f_reexport.write_text(
+        "from a import foo\n",
+        encoding="utf-8",
+    )
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
+    assert "b" in engine.state.artifact_consumption[
+        "a::foo"
+    ]["consumers"]
+    assert "c" in engine.state.artifact_consumption[
+        "a::foo"
+    ]["consumers"]
+
+    f_provider.write_text(
+        "def keep():\n"
+        "    return 2\n",
+        encoding="utf-8",
+    )
+
+    result = engine.update_file(
+        str(f_provider)
+    )
+
+    oracle = _build_full_static_state(
+        tmp_path
+    )
+
+    assert result.shadow_plan.recompute_modules == (
+        "b",
+    )
+    assert result.execution_trace[
+        "recompute_modules"
+    ] == (
+        "b",
+        "c",
+    )
+
+    assert "a::foo" not in engine.state.artifact_consumption
+    assert "a::foo" not in oracle.artifact_consumption
+
+    _assert_full_parity(
+        engine.state,
+        oracle,
+    )
+
+
+def test_reexport_retarget_matches_full_oracle(tmp_path):
+    f_a = tmp_path / "a.py"
+    f_d = tmp_path / "d.py"
+    f_reexport = tmp_path / "b.py"
+    f_consumer = tmp_path / "c.py"
+
+    f_a.write_text(
+        "def foo():\n"
+        "    return 'a'\n",
+        encoding="utf-8",
+    )
+    f_d.write_text(
+        "def foo():\n"
+        "    return 'd'\n",
+        encoding="utf-8",
+    )
+    f_reexport.write_text(
+        "from a import foo\n",
+        encoding="utf-8",
+    )
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
+    engine.update_file(str(f_a))
+    engine.update_file(str(f_d))
+    engine.update_file(str(f_reexport))
+    engine.update_file(str(f_consumer))
+
+    assert set(
+        engine.state.artifact_consumption[
+            "a::foo"
+        ]["consumers"]
+    ) == {
+        "b",
+        "c",
+    }
+
+    f_reexport.write_text(
+        "from d import foo\n",
+        encoding="utf-8",
+    )
+
+    result = engine.update_file(
+        str(f_reexport)
+    )
+
+    oracle = _build_full_static_state(
+        tmp_path
+    )
+
+    assert result.shadow_plan.recompute_modules == (
+        "c",
+    )
+    assert result.execution_trace[
+        "recompute_modules"
+    ] == (
+        "c",
+    )
+
+    assert "b" not in engine.state.artifact_consumption[
+        "a::foo"
+    ]["consumers"]
+    assert "c" not in engine.state.artifact_consumption[
+        "a::foo"
+    ]["consumers"]
+
+    assert set(
+        engine.state.artifact_consumption[
+            "d::foo"
+        ]["consumers"]
+    ) == {
+        "b",
+        "c",
+    }
+
+    _assert_full_parity(
+        engine.state,
+        oracle,
+    )
+
+
+def test_natural_ambiguity_transition_matches_full_oracle_state(
+    tmp_path,
+):
+    pkg_dir = tmp_path / "pkg"
+    pkg_dir.mkdir()
+
+    sub_pkg = pkg_dir / "a"
+    sub_pkg.mkdir()
+
+    f_original = pkg_dir / "a.py"
+    f_original.write_text(
+        "class B:\n"
+        "    def foo(self):\n"
+        "        return 1\n",
+        encoding="utf-8",
+    )
+
+    f_consumer = tmp_path / "consumer.py"
+    f_consumer.write_text(
+        "import pkg.a\n"
+        "pkg.a.B.foo()\n",
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
+    engine.update_file(str(f_original))
+    engine.update_file(str(f_consumer))
+
+    f_late = sub_pkg / "B.py"
+    f_late.write_text(
+        "def foo():\n"
+        "    return 2\n",
+        encoding="utf-8",
+    )
+
+    result = engine.update_file(
+        str(f_late)
+    )
+
+    facade = ContextorFacade()
+    errors, _ = facade.analyze_project(
+        str(tmp_path)
+    )
+
+    hydrated = hydrate_repository_engine(
+        tmp_path
+    )
+    assert hydrated is not None
+    oracle = hydrated.engine.state
+
+    for target_key in (
+        "pkg.a::B.foo",
+        "pkg.a.B::foo",
+    ):
+        incremental_entry = engine.state.artifact_consumption.get(
+            target_key,
+            {},
+        )
+        oracle_entry = oracle.artifact_consumption.get(
+            target_key,
+            {},
+        )
+
+        assert (
+            incremental_entry
+            == oracle_entry
+        ), (
+            "ambiguity canonical entry differs from fresh full oracle: "
+            f"target={target_key!r}, "
+            f"incremental={incremental_entry!r}, "
+            f"full={oracle_entry!r}, "
+            f"errors={errors!r}"
+        )
+
+    assert (
+        engine.state.artifact_consumption_state
+        == oracle.artifact_consumption_state
+    ), (
+        "ambiguity freshness differs from fresh full oracle: "
+        f"incremental={engine.state.artifact_consumption_state!r}, "
+        f"full={oracle.artifact_consumption_state!r}, "
+        f"errors={errors!r}"
+    )
+
+    assert result.artifact_consumption_state == (
+        engine.state.artifact_consumption_state
+    )
+
+
 def test_full_canonical_parity_module_add_and_delete(tmp_path):
     f_target = tmp_path / "target.py"
     f_target.write_text("def foo(): pass\n", encoding="utf-8")
```

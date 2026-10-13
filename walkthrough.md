# CONTEXTOR_B0G2D7C_COLLISION_CODE_CANONICAL_PARITY

## FILES_CHANGED

Task-owned files changed in this run:

- C:\Temp\Contextor_Repo\contextor\core\validator\collisions.py
- C:\Temp\Contextor_Repo\contextor\core\api\facade.py
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py
- C:\Temp\Contextor_Repo\tests\test_canonical_collision_code_parity.py

C:\Temp\Contextor_Repo\walkthrough.md is the required report file and is not counted as a source/test change. No other source or test path is changed.

## SOURCE_PRECHECK

- CURRENT_HEAD before/after: ddb1f7ec2cf7e464f8f86b40ba369027f66b91a0.
- Pre-edit worktree: clean; branch main...origin/main; approved test target did not exist.
- Contextor MCP canonical revision: 378. Pre-edit file context reported canonical_state=fresh, workspace_sync=verified for collisions.py, facade.py, plan_executor.py, indexer.py, and relevant test modules.
- Post-edit Contextor file contexts still answer from revision 378 but report workspace_sync=out_of_sync for all three changed production owners. No manual update_file, resync, or restart was invoked.
- Complete source retrieval: collisions.py class range 114–223; analyze_project range 558–1321 fetched as eight successful contiguous source ranges; execute_refresh_plan range 1108–1678 fetched as six successful contiguous source ranges. Contextor returned complete symbol implementations for compute_collisions_from_facts and resolve_collision_candidate_codes, and complete search spans for extract_module_collision_facts and indexer._extract_collision_facts. No retrieved source range was truncated.
- Contextor consumer evidence: analyze_project consumers include the full-analysis coordinator, reporting pipeline, collision/lifecycle tests, incremental parity tests, and refresh tests. execute_refresh_plan consumers include incremental.engine and the collision lifecycle tests. compute_collisions_from_facts direct consumers include facade, reporting pipeline, validation and incremental materialization/execution.
- Contextor lineage/call-context was queried for extraction, analyze_project, compute_collisions_from_facts, and execute_refresh_plan. The lineage endpoint reports workspace_sync=unverified by contract for its narrow server-side query; source sync above comes from the file-context projection.
- FULL current branch: is_collision_complete guards canonicalization; complete branch computes canonical_collisions, then marks collision state fresh; incomplete branch retains deferred status. The RepositoryAnalysisState constructor later receives collision_facts=cf.
- Incremental current branch validates collision-fact coverage, resolves candidate codes, computes collisions, then marks state fresh; exceptions mark it deferred. The supplied insertion boundary matches this source.
- Git status after edits lists only the four task-owned files above.

## FULL_INDEXED_VS_INCREMENTAL_LAZY_CAUSE

Contextor source confirms the stated discrepancy:

- indexer._extract_collision_facts returns fact.copy() for each extracted CollisionFact.
- CollisionFact.copy iterates COLLISION_FACT_KEYS and reads self[k]; CollisionFact.__getitem__("code") calls _get_code, which lazily invokes ast.unparse when an AST node exists.
- Incremental candidate preparation preserves lazy CollisionFact values. _to_plain_dict(render_code=False) deliberately stores an empty string until code is needed for a real multi-module collision group.
- Thus the FULL facts previously retained rendered unique-symbol code while incremental unique facts kept code=""; collision classification itself remains owned by compute_collisions_from_facts.

## CANONICAL_CODE_CONTRACT

The approved materializer was added exactly as supplied. It validates owner/schema shape; keeps module and fact insertion order; emits plain dicts; clears code for unique (name, type) keys; retains rendered definition code for multi-module candidates; and raises for empty candidate code. It does not read source or retain AST values.

Implementation side effect noted: for a multi-module candidate, the supplied fact["code"] access dispatches to CollisionFact.__getitem__ and memoizes the rendered string in that input fact’s _rendered_code cache. Unique facts do not take that branch. The focused zero-unparse test checks unique-fact object preservation; the candidate tests check exact resulting code/classification.
## FULL_CANONICALIZATION

The facade imports materialize_canonical_collision_facts. In ContextorFacade.analyze_project, the call is inserted immediately after compute_collisions_from_facts(cf), within the existing complete-facts branch and before collisions_state becomes fresh. The incomplete/deferred branch and collision result computation are unchanged. The RepositoryAnalysisState constructor receives the canonicalized cf.

## INCREMENTAL_CANONICALIZATION

The collisions patch branch imports the shared materializer. After existing coverage validation and candidate-code resolution, it keeps compute_collisions_from_facts unchanged, canonicalizes candidate.collision_facts, then installs computed collisions and marks the family fresh. Existing catch/deferred behavior remains in place.

## ZERO_UNPARSE_EVIDENCE

The new focused test’s lazy unique-fact materialization case passed. It replaces ast.unparse with an assertion failure, verifies no call occurred, checks each original CollisionFact retains the same node and unrendered state, and checks the output contains plain dicts with empty code.

## CANDIDATE_CODE_PRESERVATION

Both parametrized candidate cases passed: exact code was retained for identical and conflicting shared definitions. The computed errors retained their original classifications and exact code_snippets.

## COLLISION_CLASSIFICATION_PARITY

The focused identical-definition case returned IDENTICAL_DEFINITION_DUPLICATE. The conflicting-definition case returned NAME_COLLISION. No classification suppression was observed in these two cases.

## AST_FREE_AND_COW

The FULL unique-facts test and incremental new-module parity test passed before the first failure. They verified persisted and incremental facts are plain dictionaries, contain no AST values, and use empty code for unique symbols. The incremental test also confirmed the prior collision_facts mapping contents were unchanged and the incremental collision_facts exactly matched an independent fresh FULL snapshot.

## FAIL_CLOSED_BEHAVIOR

The direct multi-module missing-code regression passed: materialization raised ValueError and left the input mapping unchanged.

The incremental incomplete-candidate parameter reached the existing collision coverage rejection, which set candidate.collisions_state to deferred. The subsequent existing _refresh_canonical_layer_information rejected that candidate with RuntimeError because it requires fresh collision facts. The first new-test gate therefore failed before the test could inspect/return the PlanExecutionOutcome. The incomplete facts were not certified fresh. The missing_code incremental parameter was not reached because pytest used -x.

## FOCUSED_TEST_RESULTS

Command:

powershell
.venv\Scripts\python.exe -m pytest -q -x -s tests/test_canonical_collision_code_parity.py

Result: 1 failed, 6 passed in 12.34s. First failure: test_incremental_invalid_collision_candidate_is_not_fresh[incomplete]. The complete first failure output is preserved below.

```text
.....F
================================== FAILURES ===================================
____ test_incremental_invalid_collision_candidate_is_not_fresh[incomplete] ____

tmp_path = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-573/test_incremental_invalid_colli0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x0000028F38FA1540>
failure_kind = 'incomplete'

    @pytest.mark.parametrize("failure_kind", ["incomplete", "missing_code"])
    def test_incremental_invalid_collision_candidate_is_not_fresh(
        tmp_path,
        monkeypatch,
        failure_kind,
    ):
        import contextor.core.analysis.incremental.materialization as materialization_module
        import contextor.core.validator.collisions as collisions_module
    
        _write_sources(
            tmp_path,
            {
                "alpha.py": "def shared_api():\n    return 1\n",
                "beta.py": "def beta_only():\n    return 0\n",
            },
        )
        state = _run_full_and_load(tmp_path)
        assert state.collisions_state == "fresh"
        previous_facts = deepcopy(state.collision_facts)
    
        beta_path = tmp_path / "beta.py"
        beta_path.write_text(
            "def beta_only():\n"
            "    return 0\n"
            "\n"
            "def shared_api():\n"
            "    return 2\n",
            encoding="utf-8",
        )
        prepared = prepare_source_update(
            file_path=str(beta_path.resolve()),
            module_path="beta",
            is_new=False,
            old_module=state.modules["beta"],
            old_artifacts=state.artifacts.get("beta", {}),
            old_usage=state.module_usages.get("beta"),
            persistent_id="beta",
            old_collision_facts=state.collision_facts["beta"],
        )
        assert prepared.collision_facts_changed
        plan = RefreshPlanner.plan_refresh(
            delta=prepared.delta,
            usage_delta=prepared.usage_delta,
            collision_facts_changed=prepared.collision_facts_changed,
        )
    
        if failure_kind == "incomplete":
            monkeypatch.setattr(
                materialization_module,
                "_validate_collision_facts_dict",
                lambda _facts, _modules: False,
            )
        else:
            def blank_candidate_codes(collision_facts, _modules):
                result = {}
                for module_id, module_facts in collision_facts.items():
                    result[module_id] = []
                    for fact in module_facts:
                        if isinstance(fact, CollisionFact):
                            entry = fact._to_plain_dict(render_code=False)
                        else:
                            entry = dict(fact)
                        entry["code"] = ""
                        result[module_id].append(entry)
                return result
    
            monkeypatch.setattr(
                collisions_module,
                "resolve_collision_candidate_codes",
                blank_candidate_codes,
            )
    
>       outcome = execute_refresh_plan(
            state=state,
            delta=prepared.delta,
            usage_delta=prepared.usage_delta,
            plan=plan,
            new_imports=prepared.new_imports,
            new_artifacts=prepared.new_artifacts,
            new_usage=prepared.new_usage,
            root_path=tmp_path.resolve(),
            file_path=str(beta_path.resolve()),
            new_collision_facts=prepared.new_collision_facts,
            new_reexport_facts=prepared.new_reexport_facts,
        )

tests\test_canonical_collision_code_parity.py:358:

_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
contextor\core\analysis\incremental\plan_executor.py:1586: in execute_refresh_plan
    _refresh_canonical_layer_information(
contextor\core\analysis\incremental\plan_executor.py:1014: in _refresh_canonical_layer_information

candidate = CandidateState(modules={'alpha': Module(module_id='alpha', path='alpha.py', absolute_path='C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-573\test_incremental_invalid_colli0\alpha.py', imports=[]), 'beta': Module(module_id='beta', path='beta.py', absolute_path='C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-573\test_incremental_invalid_colli0\beta.py', imports=[])}, ...,
    collisions=[], collisions_state='deferred', artifact_consumption_state='fresh')
root_path = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-573/test_incremental_invalid_colli0')

    def _refresh_canonical_layer_information(
        candidate: CandidateState,
        *,
        root_path: str | Path,
    ) -> None:
        """Refresh FULL-compatible graph report fields from canonical RAM."""
        from contextor.core.hotspots import detect_hotspots
        from contextor.core.reporting_engine.debt import compute_debt
        from contextor.core.reporting_engine.summary_generator import (
            generate_summary_report,
        )
    
        previous = candidate.layer_information
    
        if not previous:
            return
    
        if not isinstance(previous, dict):
            raise RuntimeError(
                "Canonical layer information is not a dictionary"
            )
    
        previous_summary = previous.get("summary_data")
    
        if not isinstance(previous_summary, dict):
            raise RuntimeError(
                "Canonical summary_data is unavailable"
            )
    
        previous_header = previous_summary.get("report_header")
    
        if not isinstance(previous_header, dict):
            raise RuntimeError(
                "Canonical report header is unavailable"
            )
    
        graph = candidate.dependency_graph
    
        if (
            graph is None
            or not isinstance(getattr(graph, "hard_edges", None), dict)
            or not isinstance(getattr(graph, "soft_edges", None), dict)
            or candidate.cycles_state != "fresh"
            or candidate.collisions_state != "fresh"
        ):
>           raise RuntimeError(
                "Cannot refresh layer report from untrusted canonical facts"
            )
E           RuntimeError: Cannot refresh layer report from untrusted canonical facts

contextor\core\analysis\incremental\plan_executor.py:1059: RuntimeError
=========================== short test summary info ============================
FAILED tests/test_canonical_collision_code_parity.py::test_incremental_invalid_collision_candidate_is_not_fresh[incomplete]
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
1 failed, 6 passed in 12.34s
```

Classification: B0G2D7C_REGRESSION_BLOCKED. The failure is in the incomplete-path test’s expectation that execute_refresh_plan returns a candidate; current strict layer refresh instead raises after the candidate collision state is deferred. No adjustment was made because the task requires stopping on the first focused failure and prohibits an independent correction.

## H2C_CONTRACT_REGRESSIONS

Not run because the primary new-test gate failed. Existing relevant named tests were identified, including:

- test_clean_repo_zero_unparse_end_to_end_through_hydration
- test_e2e_noop_equality_avoids_unparse_on_unique_symbol
- test_e2e_hydrated_clean_and_edit_b_identical_foo
- test_e2e_hydrated_clean_and_edit_b_conflicting_foo
- test_e2e_missing_source_fails_closed_no_blank_code_collision
- test_e2e_unrelated_unique_symbols_remain_empty_code
- test_resolver_renders_only_candidate_facts_and_zero_unrelated_collision_facts
- test_resolver_zero_candidates_zero_unparse_and_returns_same_mapping

## SIX_MUTATION_MATRIX_RESULTS

Not run because the new focused gate failed. The existing six-case test file was not edited or executed. Prior B0G2D7B mismatch evidence remains untouched; this run produced no new six-mutation evidence.

## FIRST_MISMATCH_IF_ANY

No canonical parity mismatch was observed before the gate stopped. The first failure was the exact incremental incomplete-collision path shown in FOCUSED_TEST_RESULTS: the layer-information refresh raised while collision freshness was deferred.

## PRESERVED_EVIDENCE

The complete first pytest failure is embedded above in this report. No separate evidence file was created. Source/test files were not changed after that test run.

## REAL_FOUR_WAY_PARITY

Not run because the primary gate failed.

## ATOMICITY_RECHECK

Not run because the primary gate failed.

## PY_COMPILE

Passed with exit code 0 for all changed/new Python files:

- contextor/core/validator/collisions.py
- contextor/core/api/facade.py
- contextor/core/analysis/incremental/plan_executor.py
- tests/test_canonical_collision_code_parity.py

## GIT_DIFF_CHECK

Tracked changed owners: git diff --check -- <three production files> exited 0; no whitespace errors. Git printed only the configured LF-to-CRLF working-copy warnings.

New untracked test: git diff --no-index --check -- /dev/null tests/test_canonical_collision_code_parity.py exited 1 because the compared file is new/different; it emitted no whitespace-error diagnostic, only the LF-to-CRLF warning.

## LIVE_REVISION_BEFORE_AFTER

- Before edits: revision 378, activity epoch 2d530224597f44e49ca532f195a0c754.
- After focused test and source edits: revision 378, same activity epoch.
- get_live_events(after_revision=378): no canonical mutation events, continuity=continuous, resync_required=false. The event feed’s activity sequence advanced, but canonical revision did not.

## WORKSPACE_SYNC_POSTCHECK

Contextor get_file_edit_context reports workspace_sync=out_of_sync at revision 378 for collisions.py, facade.py, and plan_executor.py, with “Target file on disk has been modified since canonical state revision was generated.” No manual update_file or LIVE/source resync was attempted. This report therefore does not certify current serving-process source reload.

## RESYNC_REQUIRED

false according to the post-run Contextor LIVE event response.

## RESTART_REQUIRED

YES. Production Python owners changed; a manual serving-process reload is required before runtime certification. No restart was performed.

## FINAL_VERDICT

B0G2D7C_REGRESSION_BLOCKED

The exact shared materializer and both approved integration points are present, and six new focused cases passed before the first failure. The incomplete-path test exposed the existing fail-closed layer-refresh exception after collision freshness is deferred. Per task instructions, no further tests or edits were made.

## FULL_DIFFS

Full actual source/test diffs from the task pre-edit worktree follow.

```diff
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index af962f5..9621914 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -1475,6 +1475,7 @@ def execute_refresh_plan(
             from contextor.core.analysis.incremental.materialization import _validate_collision_facts_dict
             from contextor.core.validator.collisions import (
                 compute_collisions_from_facts,
+                materialize_canonical_collision_facts,
                 resolve_collision_candidate_codes,
             )
 
@@ -1488,6 +1489,11 @@ def execute_refresh_plan(
                     )
                     candidate.collision_facts = resolved_facts
                     computed = compute_collisions_from_facts(candidate.collision_facts)
+                    candidate.collision_facts = (
+                        materialize_canonical_collision_facts(
+                            candidate.collision_facts
+                        )
+                    )
                     candidate.collisions = computed
                     candidate.collisions_state = "fresh"
                 except Exception:
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index fe0faa6..3ea2f0a 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -55,6 +55,7 @@ from contextor.core.symbol_engine.indexer import (
 from contextor.core.validator import validate
 from contextor.core.validator.collisions import (
     compute_collisions_from_facts,
+    materialize_canonical_collision_facts,
     validate_name_collisions,
 )
 from contextor.core.live_state import (
@@ -853,6 +854,7 @@ class ContextorFacade:
 
             if is_collision_complete:
                 canonical_collisions = compute_collisions_from_facts(cf)
+                cf = materialize_canonical_collision_facts(cf)
                 collisions_state = "fresh"
             else:
                 canonical_collisions = []
diff --git a/contextor/core/validator/collisions.py b/contextor/core/validator/collisions.py
index 8989ef5..e01bd31 100644
--- a/contextor/core/validator/collisions.py
+++ b/contextor/core/validator/collisions.py
@@ -223,6 +223,87 @@ class CollisionFact(dict):
         return (dict, (self._to_plain_dict(render_code=False),))
 
 
+def materialize_canonical_collision_facts(
+    collision_facts: dict[str, list[dict]],
+) -> dict[str, list[dict]]:
+    """Freeze collision facts into one canonical AST-free representation."""
+    if not isinstance(collision_facts, dict):
+        raise TypeError(
+            "Canonical collision facts must be a mapping"
+        )
+
+    owners: dict[tuple[str, str], set[str]] = {}
+
+    for module_id, facts in collision_facts.items():
+        if not isinstance(module_id, str) or not isinstance(
+            facts, list
+        ):
+            raise TypeError(
+                "Invalid canonical collision-fact module domain"
+            )
+
+        for fact in facts:
+            if not isinstance(fact, dict):
+                raise TypeError(
+                    "Canonical collision fact must be a mapping"
+                )
+
+            if fact.get("file") != module_id:
+                raise ValueError(
+                    "Canonical collision-fact owner mismatch"
+                )
+
+            key = (
+                fact["name"],
+                fact["type"],
+            )
+            owners.setdefault(key, set()).add(module_id)
+
+    result: dict[str, list[dict]] = {}
+
+    for module_id, facts in collision_facts.items():
+        materialized = []
+
+        for fact in facts:
+            if isinstance(fact, CollisionFact):
+                entry = fact._to_plain_dict(
+                    render_code=False
+                )
+            else:
+                entry = dict(fact)
+
+            key = (
+                entry["name"],
+                entry["type"],
+            )
+
+            if len(owners[key]) > 1:
+                code = fact["code"]
+
+                if (
+                    not isinstance(code, str)
+                    or not code.strip()
+                ):
+                    raise ValueError(
+                        "Missing code for canonical collision candidate"
+                    )
+
+                entry["code"] = code
+            else:
+                entry["code"] = ""
+
+            if set(entry) != set(COLLISION_FACT_KEYS):
+                raise ValueError(
+                    "Invalid canonical collision-fact schema"
+                )
+
+            materialized.append(entry)
+
+        result[module_id] = materialized
+
+    return result
+
+
 class PublicSymbolCollector(ast.NodeVisitor):
     """
     Collect only public module-level API symbols.

diff --git a/tests/test_canonical_collision_code_parity.py b/tests/test_canonical_collision_code_parity.py
new file mode 100644
index 0000000..0596bd0
--- /dev/null
+++ b/tests/test_canonical_collision_code_parity.py
@@ -0,0 +1,374 @@
+from __future__ import annotations
+
+import ast
+from copy import deepcopy
+from pathlib import Path
+
+import pytest
+
+from contextor.core.analysis.incremental.preparation import (
+    prepare_source_update,
+)
+from contextor.core.analysis.incremental.plan_executor import (
+    execute_refresh_plan,
+)
+from contextor.core.analysis.refresh_planner import RefreshPlanner
+from contextor.core.analysis.state_manager import (
+    RepositoryAnalysisState,
+    load_engine_state,
+)
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.live_state.store import read_metadata
+from contextor.core.paths import repo_cache_dir
+from contextor.core.validator.collisions import (
+    COLLISION_FACT_KEYS,
+    CollisionFact,
+    compute_collisions_from_facts,
+    extract_module_collision_facts,
+    materialize_canonical_collision_facts,
+)
+
+
+def _write_sources(root: Path, sources: dict[str, str]) -> None:
+    for relative, content in sources.items():
+        target = root / relative
+        target.parent.mkdir(parents=True, exist_ok=True)
+        target.write_text(content, encoding="utf-8")
+
+
+def _run_full_and_load(root: Path) -> RepositoryAnalysisState:
+    errors, _result = ContextorFacade.analyze_project(str(root))
+    assert not errors, f"FULL validation failed for {root}: {errors!r}"
+
+    cache_dir = repo_cache_dir(root)
+    metadata = read_metadata(cache_dir)
+    assert metadata is not None, f"FULL did not persist snapshot for {root}"
+    state = load_engine_state(
+        str(cache_dir),
+        metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=str(root.resolve()),
+    )
+    assert isinstance(state, RepositoryAnalysisState)
+    assert state.state_id == metadata.state_id
+    assert state.revision == metadata.revision
+    return state
+
+
+def _assert_ast_free_plain_facts(
+    collision_facts: dict[str, list[dict]],
+) -> None:
+    for module_id, facts in collision_facts.items():
+        assert isinstance(module_id, str)
+        for fact in facts:
+            assert type(fact) is dict
+            assert tuple(fact) == COLLISION_FACT_KEYS
+            assert all(not isinstance(value, ast.AST) for value in fact.values())
+
+
+def test_full_unique_collision_facts_use_empty_code_and_plain_dicts(tmp_path):
+    _write_sources(
+        tmp_path,
+        {
+            "alpha.py": (
+                "def alpha_api():\n"
+                "    return 1\n"
+                "\n"
+                "ALPHA_VALUE = 2\n"
+            ),
+            "beta.py": "def beta_api():\n    return 3\n",
+        },
+    )
+
+    state = _run_full_and_load(tmp_path)
+
+    assert state.collisions_state == "fresh"
+    assert state.collisions == []
+    _assert_ast_free_plain_facts(state.collision_facts)
+    assert state.collision_facts
+    assert all(
+        fact["code"] == ""
+        for facts in state.collision_facts.values()
+        for fact in facts
+    )
+
+
+def test_new_module_incremental_collision_facts_match_fresh_full(tmp_path):
+    _write_sources(
+        tmp_path,
+        {
+            "alpha/__init__.py": "",
+            "alpha/api.py": "def alpha_api():\n    return 1\n",
+            "beta/__init__.py": "",
+            "beta/consumer.py": (
+                "from alpha.api import alpha_api\n"
+                "BETA_RESULT = alpha_api()\n"
+            ),
+        },
+    )
+    baseline = _run_full_and_load(tmp_path)
+    assert baseline.collisions_state == "fresh"
+
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    engine = hydrated.engine
+    previous_mapping = engine.state.collision_facts
+    previous_value = deepcopy(previous_mapping)
+
+    gamma_init = tmp_path / "gamma" / "__init__.py"
+    gamma_init.parent.mkdir(parents=True, exist_ok=True)
+    gamma_init.write_text("GAMMA_VALUE = 7\n", encoding="utf-8")
+
+    result = engine.update_file(str(gamma_init.resolve()))
+    assert result.status == "UPDATED"
+    assert "gamma.__init__" in engine.state.modules
+    assert engine.state.collisions_state == "fresh"
+
+    incremental_facts = deepcopy(engine.state.collision_facts)
+    _assert_ast_free_plain_facts(incremental_facts)
+    assert previous_mapping == previous_value
+
+    fresh_full = _run_full_and_load(tmp_path)
+    assert fresh_full.collisions_state == "fresh"
+    _assert_ast_free_plain_facts(fresh_full.collision_facts)
+    assert incremental_facts == fresh_full.collision_facts
+    assert incremental_facts["gamma.__init__"][0]["code"] == ""
+
+
+def test_unique_lazy_facts_materialize_without_unparse_or_input_mutation(
+    monkeypatch,
+):
+    import contextor.core.validator.collisions as collisions_module
+
+    tree = ast.parse(
+        "def unique_first():\n"
+        "    return 1\n"
+        "\n"
+        "def unique_second():\n"
+        "    return 2\n"
+    )
+    original = {
+        "pkg.module": extract_module_collision_facts(
+            tree,
+            "pkg.module",
+            "pkg/module.py",
+        )
+    }
+    original_facts = list(original["pkg.module"])
+    original_snapshots = [
+        fact._to_plain_dict(render_code=False)
+        for fact in original_facts
+    ]
+    original_nodes = [fact._node for fact in original_facts]
+    assert all(fact._rendered_code is None for fact in original_facts)
+
+    def unexpected_unparse(_node):
+        raise AssertionError("unique collision facts must not be unparsed")
+
+    monkeypatch.setattr(collisions_module.ast, "unparse", unexpected_unparse)
+    result = materialize_canonical_collision_facts(original)
+
+    assert list(result) == list(original)
+    assert [id(fact) for fact in original["pkg.module"]] == [
+        id(fact) for fact in original_facts
+    ]
+    assert [fact._to_plain_dict(render_code=False) for fact in original_facts] == (
+        original_snapshots
+    )
+    assert [fact._node for fact in original_facts] == original_nodes
+    assert all(fact._rendered_code is None for fact in original_facts)
+    assert all(type(fact) is dict for fact in result["pkg.module"])
+    assert all(fact["code"] == "" for fact in result["pkg.module"])
+    assert all(
+        tuple(fact) == COLLISION_FACT_KEYS
+        for fact in result["pkg.module"]
+    )
+    assert all(
+        not isinstance(value, ast.AST)
+        for facts in result.values()
+        for fact in facts
+        for value in fact.values()
+    )
+
+
+@pytest.mark.parametrize(
+    ("source_b", "expected_kind", "expected_code_b"),
+    [
+        (
+            "def shared_api(value):\n    return value + 1\n",
+            "IDENTICAL_DEFINITION_DUPLICATE",
+            "def shared_api(value):\n    return value + 1",
+        ),
+        (
+            "def shared_api(value):\n    return value + 2\n",
+            "NAME_COLLISION",
+            "def shared_api(value):\n    return value + 2",
+        ),
+    ],
+)
+def test_candidate_code_is_preserved_and_classification_matches(
+    source_b,
+    expected_kind,
+    expected_code_b,
+):
+    source_a = "def shared_api(value):\n    return value + 1\n"
+    facts = {
+        "mod_a": extract_module_collision_facts(
+            ast.parse(source_a),
+            "mod_a",
+            "mod_a.py",
+        ),
+        "mod_b": extract_module_collision_facts(
+            ast.parse(source_b),
+            "mod_b",
+            "mod_b.py",
+        ),
+    }
+
+    canonical = materialize_canonical_collision_facts(facts)
+
+    assert canonical["mod_a"][0]["code"] == (
+        "def shared_api(value):\n    return value + 1"
+    )
+    assert canonical["mod_b"][0]["code"] == expected_code_b
+    _assert_ast_free_plain_facts(canonical)
+
+    errors = compute_collisions_from_facts(canonical)
+    assert len(errors) == 1
+    assert errors[0].kind == expected_kind
+    assert errors[0].code_snippets == {
+        "mod_a": "def shared_api(value):\n    return value + 1",
+        "mod_b": expected_code_b,
+    }
+
+
+def test_missing_code_for_multi_module_candidate_fails_closed():
+    facts = {
+        "mod_a": [
+            {
+                "name": "shared_api",
+                "type": "function",
+                "file": "mod_a",
+                "file_path": "mod_a.py",
+                "code": "",
+                "line_start": 1,
+                "line_end": 2,
+                "col_start": 0,
+                "col_end": 10,
+            }
+        ],
+        "mod_b": [
+            {
+                "name": "shared_api",
+                "type": "function",
+                "file": "mod_b",
+                "file_path": "mod_b.py",
+                "code": "",
+                "line_start": 1,
+                "line_end": 2,
+                "col_start": 0,
+                "col_end": 10,
+            }
+        ],
+    }
+    original = deepcopy(facts)
+
+    with pytest.raises(
+        ValueError,
+        match="Missing code for canonical collision candidate",
+    ):
+        materialize_canonical_collision_facts(facts)
+
+    assert facts == original
+
+
+@pytest.mark.parametrize("failure_kind", ["incomplete", "missing_code"])
+def test_incremental_invalid_collision_candidate_is_not_fresh(
+    tmp_path,
+    monkeypatch,
+    failure_kind,
+):
+    import contextor.core.analysis.incremental.materialization as materialization_module
+    import contextor.core.validator.collisions as collisions_module
+
+    _write_sources(
+        tmp_path,
+        {
+            "alpha.py": "def shared_api():\n    return 1\n",
+            "beta.py": "def beta_only():\n    return 0\n",
+        },
+    )
+    state = _run_full_and_load(tmp_path)
+    assert state.collisions_state == "fresh"
+    previous_facts = deepcopy(state.collision_facts)
+
+    beta_path = tmp_path / "beta.py"
+    beta_path.write_text(
+        "def beta_only():\n"
+        "    return 0\n"
+        "\n"
+        "def shared_api():\n"
+        "    return 2\n",
+        encoding="utf-8",
+    )
+    prepared = prepare_source_update(
+        file_path=str(beta_path.resolve()),
+        module_path="beta",
+        is_new=False,
+        old_module=state.modules["beta"],
+        old_artifacts=state.artifacts.get("beta", {}),
+        old_usage=state.module_usages.get("beta"),
+        persistent_id="beta",
+        old_collision_facts=state.collision_facts["beta"],
+    )
+    assert prepared.collision_facts_changed
+    plan = RefreshPlanner.plan_refresh(
+        delta=prepared.delta,
+        usage_delta=prepared.usage_delta,
+        collision_facts_changed=prepared.collision_facts_changed,
+    )
+
+    if failure_kind == "incomplete":
+        monkeypatch.setattr(
+            materialization_module,
+            "_validate_collision_facts_dict",
+            lambda _facts, _modules: False,
+        )
+    else:
+        def blank_candidate_codes(collision_facts, _modules):
+            result = {}
+            for module_id, module_facts in collision_facts.items():
+                result[module_id] = []
+                for fact in module_facts:
+                    if isinstance(fact, CollisionFact):
+                        entry = fact._to_plain_dict(render_code=False)
+                    else:
+                        entry = dict(fact)
+                    entry["code"] = ""
+                    result[module_id].append(entry)
+            return result
+
+        monkeypatch.setattr(
+            collisions_module,
+            "resolve_collision_candidate_codes",
+            blank_candidate_codes,
+        )
+
+    outcome = execute_refresh_plan(
+        state=state,
+        delta=prepared.delta,
+        usage_delta=prepared.usage_delta,
+        plan=plan,
+        new_imports=prepared.new_imports,
+        new_artifacts=prepared.new_artifacts,
+        new_usage=prepared.new_usage,
+        root_path=tmp_path.resolve(),
+        file_path=str(beta_path.resolve()),
+        new_collision_facts=prepared.new_collision_facts,
+        new_reexport_facts=prepared.new_reexport_facts,
+    )
+
+    assert state.collisions_state == "fresh"
+    assert state.collision_facts == previous_facts
+    assert outcome.candidate_state.collisions_state == "deferred"
```
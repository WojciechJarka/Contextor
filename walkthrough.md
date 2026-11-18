# SP-T4-I2B5-I1 — Candidate Evidence Isolation

## PREFLIGHT

- DIRECT_EVIDENCE — HEAD before implementation: 5cdda2adc2e62b4bec6b68fd682192b76235032e; branch main...origin/main.
- DIRECT_EVIDENCE — git status before implementation: walkthrough.md was already modified as the report artifact; both allowed source/test targets were clean.
- DIRECT_EVIDENCE — pre-change LIVE: canonical revision 1433, provenance live, canonical_state fresh, resync_required=false. Graph and cycles were fresh; syntax diagnostics reported zero errors. cycle_semantics was stale and outside this task.
- DIRECT_EVIDENCE — pre-change workspace_sync: plan_executor.py and tests/test_p1d3_d2b2_type_only.py were verified at revision 1433.
- DIRECT_EVIDENCE — interpreter: CPython 3.15.2 is available in the repository virtual environment. The system py -3.15 interpreter is also 3.15.2 but has no pytest installed.
- DIRECT_EVIDENCE — requested anchors matched current LIVE/source: plan_executor imports at lines 12-13; CandidateState final default field at line 87; return CandidateState at line 700. The test file ended after line 3926, following T48.
- DIRECT_EVIDENCE — fixtures and selected existing tests: _I1_SAFE, RepositoryAnalysisState, write_synthetic_repository, and _index_graph exist; T01, T05-T08, and T22-T27 are present.
- DIRECT_EVIDENCE — pre-edit diff scope: plan_executor.py import replacement, one appended CandidateState field, and one first keyword argument in _prepare_candidate_state; append only the exact T49-T51 tests at EOF. No other implementation files were in scope.

## EXACT_IMPLEMENTATION

- CODE_PATH_PROVED — plan_executor.py imports deepcopy and dataclasses.field; CandidateState receives typing_guard_evidence with default_factory=dict after all pre-existing fields; _prepare_candidate_state initializes that field with the exact requested deepcopy expression.
- DIRECT_EVIDENCE — only the requested T49-T51 functions were appended to tests/test_p1d3_d2b2_type_only.py. Existing tests were not edited.
- DIRECT_EVIDENCE — engine.py, refresh_planner.py, graph construction, classification policy, and existing clear assignments were not changed. No MCP update_file, restart, FULL, commit, push, or staging operation was performed.
- DIRECT_EVIDENCE — no repository-specific production branch or constant was introduced.

## CANDIDATE_EVIDENCE_ISOLATION

- CODE_PATH_PROVED — _prepare_candidate_state recursively copies the input evidence before placing it on the candidate.
- DIRECT_EVIDENCE — T49 checks equal contents with distinct top-level and nested mapping identities. It also checks distinct candidate ImportRef objects and distinct mutable names lists.
- DIRECT_EVIDENCE — T49 mutates the candidate fingerprint mapping and candidate ImportRef.names list, then verifies the original state's corresponding values remain unchanged.
- DIRECT_EVIDENCE — no classification, graph, or publication behavior was changed in this stage.
- INFERENCE / REVIEW NOTE — the exact requested expression uses getattr(state, "typing_guard_evidence", {}) or {}, so any falsey value is normalized to an empty mapping. The declared evidence field is a dict and the prompt requires this expression; whether a falsey malformed non-dict can occur in persisted state is UNKNOWN. No change was made.

## INPUT_MUTATION_REGRESSIONS

- DIRECT_EVIDENCE — T49 covers candidate-side nested mutations leaving the input state unchanged; T51 covers replacing the candidate evidence mapping without publishing it to the input state.
- INFERENCE / COVERAGE LIMIT — the new tests do not directly mutate the input after candidate preparation and assert the candidate remains unchanged. deepcopy provides isolation in that direction by its operation, but that direction is not separately asserted by T49-T51.
- DIRECT_EVIDENCE — T50 starts from RepositoryAnalysisState() with its declared default field. It verifies an empty candidate mapping is separate from the state mapping; it does not directly instantiate a legacy object with no typing_guard_evidence attribute.
- These are coverage boundaries of the exact requested test addition, not observed failures. The literal test block was not expanded.

## CONSTRUCTOR_COMPATIBILITY

- CODE_PATH_PROVED — the new CandidateState field is appended after pre-existing fields; no existing field order or default was changed. Existing positional parameter positions therefore remain in place, with one new trailing defaulted parameter.
- CODE_PATH_PROVED — the constructor call in _prepare_candidate_state supplies the new value by keyword; existing keyword arguments are unchanged.
- DIRECT_EVIDENCE — default_factory=dict gives separate empty mappings for separately constructed candidates; T50 verifies candidate/state mapping non-aliasing for the empty default.
- DIRECT_EVIDENCE — getattr with a {} fallback is present for state objects without the attribute, but a legacy object lacking that attribute was not part of the exact added tests.

## TARGETED_TESTS

- DIRECT_EVIDENCE — executed on repository .venv CPython 3.15.2 using pytest 9.1.1.
- DIRECT_EVIDENCE — selectors were exactly T49-T51, T01, T05-T08, and T22-T27 in tests/test_p1d3_d2b2_type_only.py.
- DIRECT_EVIDENCE — result: 15 passed in 9.53s. One selector expands to a parametrized case, yielding 15 collected cases.
- DIRECT_EVIDENCE — an initial invocation through system py -3.15 could not start because that interpreter lacks pytest; the requested selection was then run successfully via the repository virtual environment. No full pytest suite was run.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE — canonical LIVE revision 1435, provenance live, canonical_state fresh, resync_required=false.
- DIRECT_EVIDENCE — desktop_watcher emitted update_file UPDATED at revision 1434 for contextor/core/analysis/incremental/plan_executor.py and at revision 1435 for tests/test_p1d3_d2b2_type_only.py. Event continuity from revision 1433 was continuous; no resync was required.
- DIRECT_EVIDENCE — per-file workspace_sync for both changed implementation/test files is verified at revision 1435.
- DIRECT_EVIDENCE — per-file syntax diagnostics are checked_and_none with errors=[]. Global syntax diagnostic count is 0 and fresh.
- DIRECT_EVIDENCE — graph and cycles are fresh at revision 1435; module_count=670; structural cycle count=16; soft-dependent potential cycle count=1.
- DIRECT_EVIDENCE — cycle_semantics remains stale. This is unrelated to the patch; the task did not request FULL or a runtime reload.
- DIRECT_EVIDENCE — current git HEAD remains 5cdda2adc2e62b4bec6b68fd682192b76235032e on main. Status shows only the requested source file, test file, and walkthrough.md modified; no staged changes.
- DIRECT_EVIDENCE — actual source/test diff was inspected in full and is reproduced below.

## FINAL_VERDICT

I2B5_I1_PASS

The exact candidate evidence isolation change is present, the specified focused tests passed, and post-change LIVE synchronization and syntax checks are fresh. This verdict covers I1 candidate isolation only; it does not claim that the I2B4C reclassification helper is integrated into Incremental.

## FILES_CHANGED

- contextor/core/analysis/incremental/plan_executor.py
- tests/test_p1d3_d2b2_type_only.py

walkthrough.md is overwritten as the required report artifact and is not counted as an implementation/test file in this inventory.

## FULL_DIFFS

The following complete source/test diff is from git diff --unified=0. All changed lines are included; unchanged context lines are omitted by the selected diff mode.

### contextor/core/analysis/incremental/plan_executor.py

~~~~diff
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 6ce7638..521e722 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -13 +13,2 @@ from collections import deque
-from dataclasses import dataclass
+from copy import deepcopy
+from dataclasses import dataclass, field
@@ -87,0 +89,3 @@ class CandidateState:
+    typing_guard_evidence: Dict[str, object] = field(
+        default_factory=dict
+    )
@@ -700,0 +705,3 @@ def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
+        typing_guard_evidence=deepcopy(
+            getattr(state, "typing_guard_evidence", {}) or {}
+        ),
~~~~

### tests/test_p1d3_d2b2_type_only.py

~~~~diff
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 4280887..61fea0e 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -3926,0 +3927,124 @@ def test_sp_t4_i2b4c_t48_unrelated_module_tampering(
+
+def test_sp_t4_i2b5_i1_t49_candidate_evidence_isolated(
+    tmp_path, isolated_dirs,
+):
+    from contextor.core.analysis.incremental.plan_executor import (
+        _prepare_candidate_state,
+    )
+
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    index, _ = _index_graph(root)
+    state = RepositoryAnalysisState(
+        modules=dict(index.modules),
+        typing_guard_evidence=index.typing_guard_evidence,
+    )
+
+    original = state.typing_guard_evidence
+    candidate = _prepare_candidate_state(state)
+    copied = candidate.typing_guard_evidence
+
+    assert copied == original
+    assert copied is not original
+
+    for key in (
+        "candidate_imports_by_module",
+        "source_fingerprints_by_module",
+        "initializer_passivity_by_module",
+        "marker_mutation_by_module",
+        "opaque_effects_by_module",
+    ):
+        assert copied[key] is not original[key]
+
+    original_fingerprint = original[
+        "source_fingerprints_by_module"
+    ]["pkg.a"]
+
+    copied["source_fingerprints_by_module"][
+        "pkg.a"
+    ] = "0" * 64
+
+    assert original[
+        "source_fingerprints_by_module"
+    ]["pkg.a"] == original_fingerprint
+
+    copied_refs = copied[
+        "candidate_imports_by_module"
+    ]["pkg.a"]
+
+    original_refs = original[
+        "candidate_imports_by_module"
+    ]["pkg.a"]
+
+    copied_guarded = next(
+        ref for ref in copied_refs if ref.type_only
+    )
+    original_guarded = next(
+        ref for ref in original_refs if ref.type_only
+    )
+
+    assert copied_guarded is not original_guarded
+    assert copied_guarded.names is not original_guarded.names
+
+    names_before = tuple(original_guarded.names)
+    copied_guarded.names.append("isolated-test-marker")
+
+    assert tuple(original_guarded.names) == names_before
+    assert (
+        "isolated-test-marker"
+        not in original_guarded.names
+    )
+
+    assert state.typing_guard_evidence is original
+
+
+def test_sp_t4_i2b5_i1_t50_missing_evidence_default(
+    tmp_path, isolated_dirs,
+):
+    from contextor.core.analysis.incremental.plan_executor import (
+        _prepare_candidate_state,
+    )
+
+    state = RepositoryAnalysisState()
+
+    candidate = _prepare_candidate_state(state)
+
+    assert candidate.typing_guard_evidence == {}
+    assert (
+        candidate.typing_guard_evidence
+        is not state.typing_guard_evidence
+    )
+
+    candidate.typing_guard_evidence["probe"] = True
+
+    assert state.typing_guard_evidence == {}
+
+
+def test_sp_t4_i2b5_i1_t51_candidate_is_not_published(
+    tmp_path, isolated_dirs,
+):
+    from contextor.core.analysis.incremental.plan_executor import (
+        _prepare_candidate_state,
+    )
+
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    index, _ = _index_graph(root)
+
+    state = RepositoryAnalysisState(
+        modules=dict(index.modules),
+        typing_guard_evidence=index.typing_guard_evidence,
+    )
+
+    original = state.typing_guard_evidence
+    candidate = _prepare_candidate_state(state)
+
+    candidate.typing_guard_evidence = {
+        "schema_version": 999,
+    }
+
+    assert state.typing_guard_evidence is original
+    assert state.typing_guard_evidence["schema_version"] == 2
~~~~

# CONTEXTOR P1D3-B/C-R1 — literal test regression repair

## VERDICT
GO — dokładnie trzy testy dodane i uruchomione; bez konfliktu kontraktu.

## HEAD_AND_WORKTREE
- Initial HEAD: `21a2c86d78554f558355468c3ab7b806c88d82df`
- Final HEAD: `21a2c86d78554f558355468c3ab7b806c88d82df`
- Initial worktree status: clean (`git status --short` returned no entries).
- Final worktree status: modified `tests/test_cycle_semantics_evidence.py`, `tests/test_p1d3_package_cycle_integration.py`, `walkthrough.md`.

## ACTIONS_AND_EVIDENCE
- DIRECT_EVIDENCE: Contextor MCP preview resolved `assess_index_bound_scc_models` in `contextor/core/cycle_semantics/evidence.py`, lines 95–349, canonical revision 718, `workspace_sync=verified`. Exact test helpers and imports were then confirmed in source.
- CONTRACT_PROVED: all three literal test bodies matched existing helper signatures and imports; no contract conflict observed.
- Added tests: `test_p0_genuine_unknown_entry_remains_incomplete`, `test_p0_rehashed_invalid_flat_scope_is_rejected`, `test_p0_rehashed_invalid_package_scope_is_rejected`.
- Production code untouched. Existing test bodies and assertions untouched.

## TEST_RESULT
- `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_evidence.py tests/test_p1d3_package_cycle_integration.py` → `92 passed in 9.46s`, exit 0.
- Separately executed all three exact new node IDs with `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_evidence.py::test_p0_genuine_unknown_entry_remains_incomplete tests/test_cycle_semantics_evidence.py::test_p0_rehashed_invalid_flat_scope_is_rejected tests/test_p1d3_package_cycle_integration.py::test_p0_rehashed_invalid_package_scope_is_rejected` → `3 passed in 3.27s`, exit 0. This confirms collection and execution of each new test.
- `git diff --check` → exit 0; Git emitted only LF/CRLF normalization warnings.

## FAILURE_AND_NEXT_STEP
- Unexpected failure: none.
- Stop after R1 verification; await explicit `proceduj`.

## FILES_CHANGED
- `tests/test_cycle_semantics_evidence.py`
- `tests/test_p1d3_package_cycle_integration.py`
- `walkthrough.md` (report only; excluded from source/test diff list)

## ACTUAL_DIFF / FULL_DIFF

```diff
diff --git a/tests/test_cycle_semantics_evidence.py b/tests/test_cycle_semantics_evidence.py
index 5fbf4f9..09bbcc6 100644
--- a/tests/test_cycle_semantics_evidence.py
+++ b/tests/test_cycle_semantics_evidence.py
@@ -326,6 +326,28 @@ def test_p0_t11_unknown_entry_in_scc():
     assert result[0].evidence_state == "EVIDENCE_MISMATCH"
 
 
+def test_p0_genuine_unknown_entry_remains_incomplete():
+    sources = {
+        "a": "import b\nx = object()\n",
+        "b": "import a\ny = 2\n",
+    }
+
+    result, index, snapshot, evidence = _one(
+        sources=sources,
+    )
+
+    scenario = evidence.scenarios.components[0]
+
+    assert scenario.classification == "INDETERMINATE"
+    assert scenario.coverage == "PARTIAL_FRESH_MEMBER_ENTRIES"
+
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
+    assert result[0].reason == (
+        "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS"
+    )
+
+
 def test_p0_t12_independent_sccs_do_not_share_pass():
     edges = {"a": {"b"}, "b": {"a"}, "x": {"y"}, "y": {"x"}}
     sources = dict(PASS, x="import y\nvalue=1", y="from x import value")
@@ -451,6 +473,70 @@ def test_p0_t18_entry_model_scope_must_match(sources):
     assert result[0].reason == "COMPONENT_EVIDENCE_TOKEN_MISMATCH"
 
 
+def test_p0_rehashed_invalid_flat_scope_is_rejected():
+    _, index, snapshot, evidence = _one()
+
+    scenario = evidence.scenarios.components[0]
+    assessment = scenario.entry_assessments[0]
+
+    changed_assessment = replace(
+        assessment,
+        evidence_scope="UNVERIFIED_EXECUTION_MODEL",
+    )
+
+    changed_scenario = replace(
+        scenario,
+        entry_assessments=(
+            changed_assessment,
+            *scenario.entry_assessments[1:],
+        ),
+    )
+
+    component = evidence.components[0]
+
+    subgraph = tuple(
+        (
+            module,
+            tuple(sorted(PAIR[module])),
+        )
+        for module in component.reachable_modules
+    )
+
+    changed_token = _component_token(
+        component.members,
+        subgraph,
+        component.source_signatures,
+        changed_scenario,
+    )
+
+    changed_component = replace(
+        component,
+        evidence_token=changed_token,
+    )
+
+    changed_evidence = replace(
+        evidence,
+        scenarios=replace(
+            evidence.scenarios,
+            components=(changed_scenario,),
+        ),
+        components=(changed_component,),
+    )
+
+    result = assess(
+        PAIR,
+        index,
+        snapshot,
+        changed_evidence,
+    )
+
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
+    assert result[0].reason == (
+        "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS"
+    )
+
+
 def _p1_case(sources=PASS):
     _, index, snapshot, evidence = _one(sources=sources)
     state = SimpleNamespace(
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index 0e65109..2330638 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -247,6 +247,94 @@ def test_p1b_replay_rejects_forged_event(tmp_path, isolated_dirs, fixture):
     assert p1b[0].reason == "MODEL_REPLAY_MISMATCH"
 
 
+def test_p0_rehashed_invalid_package_scope_is_rejected(
+    tmp_path,
+    isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo",
+        F1,
+    )
+
+    index, graph = _indexed(root)
+    _, captured = _captured(root, index, graph)
+
+    parsed = {
+        module: parse_source_snapshot(snapshot, module)
+        for module, snapshot
+        in captured.original_worker_source_snapshots.items()
+    }
+
+    evidence = build_source_bound_cycle_evidence(
+        graph.hard_edges,
+        parsed,
+    )
+
+    scenario = evidence.scenarios.components[0]
+
+    assert scenario.model_kind == "REGULAR_PACKAGE"
+    assert scenario.classification == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    )
+
+    assessment = scenario.entry_assessments[0]
+
+    changed_assessment = replace(
+        assessment,
+        evidence_scope="RESTRICTED_FLAT_MODULE_MODEL",
+    )
+
+    changed_scenario = replace(
+        scenario,
+        entry_assessments=(
+            changed_assessment,
+            *scenario.entry_assessments[1:],
+        ),
+    )
+
+    component = evidence.components[0]
+
+    subgraph = tuple(
+        (
+            module,
+            tuple(sorted(graph.hard_edges[module])),
+        )
+        for module in component.reachable_modules
+    )
+
+    changed_component = replace(
+        component,
+        evidence_token=_component_token(
+            component.members,
+            subgraph,
+            component.source_signatures,
+            changed_scenario,
+        ),
+    )
+
+    changed_evidence = replace(
+        evidence,
+        scenarios=replace(
+            evidence.scenarios,
+            components=(changed_scenario,),
+        ),
+        components=(changed_component,),
+    )
+
+    result = assess_index_bound_scc_models(
+        graph.hard_edges,
+        captured.source_fingerprints_by_module,
+        _snapshot(root, index, graph),
+        changed_evidence,
+    )
+
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
+    assert result[0].reason == (
+        "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS"
+    )
+
+
 def test_p0_rejects_package_assessment_disguised_as_flat(tmp_path, isolated_dirs):
     root = write_synthetic_repository(tmp_path / "repo", F1)
     index, graph = _indexed(root)
```

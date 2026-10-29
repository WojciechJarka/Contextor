# CONTEXTOR P1D3-WARN-1-R1 — strict canonical cycle-path validation

## HEAD / WORKTREE

DIRECT_EVIDENCE: initial and final HEAD: `4e4863f0b037d8eee2084c116e3f28915130bf28`. Initial worktree clean (`git status --short` empty). Final worktree: modified `contextor/core/cycle_semantics/warning_eligibility.py`, `tests/test_cycle_semantics_warning_eligibility.py`, and this `walkthrough.md` report. Existing committed WARN-1 implementation and T01–T18 test nodes matched the supplied R1 anchors; no PREFLIGHT_MISMATCH.

## ROOT CAUSE

CODE_PATH_PROVED: prior `_verified_model_pass_cycle_paths` validated closure, edge existence and SCC containment, then inserted `tuple(path)` into a set. A repeated closed walk could satisfy all those checks, and duplicate identical records would be silently deduplicated rather than rejected. This was the specific R1 contract gap; no receipt or SCC authority defect was inferred.

## EXACT PRODUCTION CHANGE

CODE_PATH_PROVED: inside the existing path loop, after type/node/closure validation, `interior = tuple(path[:-1])` must have distinct nodes. A `seen_paths: set[tuple[str, ...]]` initialized once before the loop rejects repeated identical records. Existing directed-edge, exact cyclic-SCC mapping and whole-result empty fallback remain in place. No cycle enumeration, source/model recomputation, `detect_cycles`, receipt change, warning integration or schema change.

## NEW NEGATIVE CASES

CONTRACT_PROVED: `test_r1_repeated_closed_walk_fails_closed` rejects a-b-a-b-a under a real committed PASS receipt. `test_r1_repeated_self_loop_fails_closed_but_simple_loop_qualifies` accepts a-a then rejects a-a-a. `test_r1_duplicate_identical_cycle_records_fail_closed` rejects repeated a-b-a records. `test_r1_valid_path_then_repeated_walk_has_no_partial_result` proves one valid path plus malformed repeated walk returns empty.

## POSITIVE REGRESSION RESULTS

DIRECT_EVIDENCE: T02, T04, T05 and T16 remained in the selected WARN-1 module and passed in the focused run. Their committed model claims are constructed with existing preparation and durable store helpers, not manual digests. All previous T01–T18 tests remained and passed. These tests establish static committed-claim behavior, not LIVE installation or Python runtime safety.

## FAIL-CLOSED BEHAVIOR

CODE_PATH_PROVED: either repeated interior node or already-seen full path returns `frozenset()` immediately, discarding any earlier eligible path accumulation. Receipt verification, SCC component selection, directed-edge checking, SCC membership, structural graph and state.cycles are unchanged.

## TEST COMMANDS / RESULTS

- `& .\.venv\Scripts\python.exe -m py_compile contextor/core/cycle_semantics/warning_eligibility.py tests/test_cycle_semantics_warning_eligibility.py`: exit 0, no output.
- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_warning_eligibility.py tests/test_cycle_semantics_publication_binding.py tests/test_cycle_semantics_scc.py`: exit 0; 64 passed, 0 failed, 0 skipped in 12.21s.
- `git diff --check -- contextor/core/cycle_semantics/warning_eligibility.py tests/test_cycle_semantics_warning_eligibility.py`: no whitespace error; Git printed only LF-to-CRLF working-copy notices. Both files are tracked at this HEAD, so the ordinary tracked diff covers them. No global pytest or active FULL/LIVE operation ran.

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_file_edit_context` at canonical revision 820 indexed production module 551/1 and test module 552/1. Production reported workspace_sync=verified, syntax fresh/checked_and_none, graph/topology fresh; imports remain SCC, generation_manifest and publication_binding; only direct consumer is the test module. First test-file read reported workspace_sync=out_of_sync and advisory warning despite syntax and graph/topology fresh. Follow-up test-file read at revision 821 reported workspace_sync=verified, graph/topology fresh, advisory_warning=null. Cycle_semantics family stayed stale. This MCP metadata is not loaded-code adoption evidence.

## FILES_CHANGED

- `contextor/core/cycle_semantics/warning_eligibility.py`
- `tests/test_cycle_semantics_warning_eligibility.py`

`walkthrough.md` is the permitted report and excluded from source/test diff accounting.

## FULL_DIFFS

Complete actual tracked Git diffs for both changed Python files follow. No lines omitted.

```diff
diff --git a/contextor/core/cycle_semantics/warning_eligibility.py b/contextor/core/cycle_semantics/warning_eligibility.py
index 0b00b07..4250d5a 100644
--- a/contextor/core/cycle_semantics/warning_eligibility.py
+++ b/contextor/core/cycle_semantics/warning_eligibility.py
@@ -74,6 +74,7 @@ def _verified_model_pass_cycle_paths(
             == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
         }
         result: set[tuple[str, ...]] = set()
+        seen_paths: set[tuple[str, ...]] = set()
         for path in paths:
             if (
                 not isinstance(path, (list, tuple))
@@ -82,6 +83,13 @@ def _verified_model_pass_cycle_paths(
                 or path[0] != path[-1]
             ):
                 return empty
+            interior = tuple(path[:-1])
+            if len(interior) != len(set(interior)):
+                return empty
+            path_identity = tuple(path)
+            if path_identity in seen_paths:
+                return empty
+            seen_paths.add(path_identity)
             if any(
                 target not in hard_edges.get(source, ())
                 for source, target in zip(path, path[1:])
diff --git a/tests/test_cycle_semantics_warning_eligibility.py b/tests/test_cycle_semantics_warning_eligibility.py
index 21bd38d..59c1bad 100644
--- a/tests/test_cycle_semantics_warning_eligibility.py
+++ b/tests/test_cycle_semantics_warning_eligibility.py
@@ -233,3 +233,30 @@ def test_t18_repeatable_without_state_mutation(tmp_path):
     second = _eligible(state, expected)
     assert first == second == frozenset({("a", "b", "a")})
     assert state.__dict__ == before
+
+
+def test_r1_repeated_closed_walk_fails_closed(tmp_path):
+    state, expected = _committed(tmp_path)
+    state.cycles = [["a", "b", "a", "b", "a"]]
+    assert _eligible(state, expected) == frozenset()
+
+
+def test_r1_repeated_self_loop_fails_closed_but_simple_loop_qualifies(tmp_path):
+    state, expected = _committed(
+        tmp_path, {"a": {"a"}}, {"a": "import a"}, (("a", "a"),),
+    )
+    assert _eligible(state, expected) == frozenset({("a", "a")})
+    state.cycles = [["a", "a", "a"]]
+    assert _eligible(state, expected) == frozenset()
+
+
+def test_r1_duplicate_identical_cycle_records_fail_closed(tmp_path):
+    state, expected = _committed(tmp_path)
+    state.cycles = [["a", "b", "a"], ["a", "b", "a"]]
+    assert _eligible(state, expected) == frozenset()
+
+
+def test_r1_valid_path_then_repeated_walk_has_no_partial_result(tmp_path):
+    state, expected = _committed(tmp_path)
+    state.cycles = [["a", "b", "a"], ["a", "b", "a", "b", "a"]]
+    assert _eligible(state, expected) == frozenset()
```

## CONTRACT_CONFLICTS

NONE. Exact requested statements and locations matched current code. No architecture or public contract was changed.

## REMAINING UNKNOWN

Running Desktop/MCP loaded-code adoption and active warning behavior were not tested. Canonical cycle_semantics remained stale during MCP reads. No active generation verification was executed.

## FINAL IMPLEMENTER OBSERVATION

CODE_PATH_PROVED: R1 closes the specific non-simple/duplicate path acceptance gap while retaining the WARN-1 pure eligibility boundary. Architectural GO remains with ChatGPT.



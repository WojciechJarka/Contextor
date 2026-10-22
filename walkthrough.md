# CONTEXTOR_P1D0_FINAL_REGRESSION_COMPLETION

## TASK
Apply the exact auditor-supplied test-only T11/T12 addition and remove the extra blank EOF line. No production change or earlier assertion edit.

## HEAD_BEFORE
3bb0e9ab537a556af17ea639509bfa83a5941eaa. The P1D0 source and ten-test file were untracked from the preceding task; walkthrough.md held the prior report.

## HEAD_AFTER
3bb0e9ab537a556af17ea639509bfa83a5941eaa. No commit created.

## FILES_CHANGED
C:\Temp\Contextor_Repo\tests\test_cycle_semantics_selective_source_replay.py (current task only). walkthrough.md was overwritten as the required report. No production file changed.

## T01_T12_RESULTS
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_selective_source_replay.py
Actual: 12 passed in 19.24s, exit 0. T01–T10 remained present with unchanged assertions; T11 and T12 passed.

## FOCUSED_NON_REGRESSION
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_index_fusion.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_publication_binding.py
Actual: 102 passed in 10.37s, exit 0. No FULL analysis or full repository pytest suite run.
py_compile of changed test file: PASS.

## CUMULATIVE_BUDGET
T11 obtains the complete SCC closure byte total, then runs with max_closure_bytes=total-1 while individual files fit max_source_bytes=1024. The result is UNAVAILABLE, with SOURCE_BYTE_BUDGET_EXCEEDED, empty snapshots and zero retained bytes. This proves cumulative closure limit behavior in the fixture.

## INDEPENDENT_SCC_BUDGETS
T12 adds a second independent two-module SCC. With a 32-byte closure budget, the larger pkg SCC is UNAVAILABLE with no partial bytes while the smaller other SCC succeeds. The iterator thus applies budgets per SCC in this test. It does not establish a total Python heap bound.

## WHITESPACE_CHECK
The changed test ends in exactly one LF byte and not two; explicit byte check returned ends_one_newline=True. The new-file check, git -c core.autocrlf=false diff --no-index --check -- /dev/null tests/test_cycle_semantics_selective_source_replay.py, emitted no whitespace diagnostics; its difference exit status 1 is normal for no-index comparison. The tracked-file check git -c core.autocrlf=false diff --check returned exit 0 with no diagnostics after this LF-formatted report was written; the complete current-task unified diff below uses zero context so report-only blank context lines do not create false whitespace diagnostics.

## LIVE_REVISION_BEFORE_AFTER
Before edit: 649. After watcher update: 650.

## WATCHER_EVENTS
Contextor get_live_events(after_revision=649): revision 650, desktop_watcher update_file UPDATED for the changed test file, continuity=continuous, resync_required=false. The event's blast_radius_state was deferred; it is not a proof of zero impact. No manual update_file call.

## WORKSPACE_SYNC
Contextor get_module_context after watcher adoption: changed test module canonical_state=fresh, workspace_sync=verified, canonical_revision=650, advisory_warning=null. Post-edit get_module_blast_radius resolved 15 artifacts, zero direct static consumers and zero downstream modules. That blast-radius call intentionally reports workspace_sync=unverified because it does not hash source; module context supplies the verification. No MCP/LIVE restart was performed or required for this test-only edit.

## FULL_DIFFS
The complete actual unified diff below compares the exact pre-task untracked file contents (T01–T10 with the extra EOF blank line) with the current file. Prior-task creation of T01–T10 and the production module is not repeated.

diff --git a/tests/test_cycle_semantics_selective_source_replay.py b/tests/test_cycle_semantics_selective_source_replay.py
--- a/tests/test_cycle_semantics_selective_source_replay.py
+++ b/tests/test_cycle_semantics_selective_source_replay.py
@@ -286,0 +287,91 @@
+
+def test_p1d0_t11_cumulative_closure_budget_fails_closed(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    monkeypatch.setenv(
+        "CONTEXTOR_DISABLE_PROCESS_POOL", "1"
+    )
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+
+    (complete,) = _capture(root, index, edges)
+    assert complete.status == (
+        "BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
+    )
+
+    total = complete.retained_raw_bytes
+    assert total > 1
+    del complete
+
+    # Each file fits independently, but the complete
+    # reachable closure exceeds this cumulative budget.
+    (limited,) = _capture(
+        root,
+        index,
+        edges,
+        max_source_bytes=1024,
+        max_closure_bytes=total - 1,
+    )
+
+    assert limited.status == "UNAVAILABLE"
+    assert limited.reason.startswith(
+        "SOURCE_BYTE_BUDGET_EXCEEDED:"
+    )
+    assert limited.source_snapshots == {}
+    assert limited.retained_raw_bytes == 0
+
+
+def test_p1d0_t12_independent_sccs_have_independent_budgets(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    monkeypatch.setenv(
+        "CONTEXTOR_DISABLE_PROCESS_POOL", "1"
+    )
+    root = _repo(tmp_path)
+
+    other = root / "other"
+    other.mkdir()
+    (other / "__init__.py").write_bytes(b"")
+    (other / "a.py").write_bytes(
+        b"import other.b\n"
+    )
+    (other / "b.py").write_bytes(
+        b"import other.a\n"
+    )
+
+    index, edges = _analyze(root)
+
+    outcomes = {
+        result.members: result
+        for result in replay.iter_selective_scc_source_replays(
+            root,
+            edges,
+            index,
+            max_source_bytes=128,
+            max_closure_bytes=32,
+        )
+    }
+
+    assert set(outcomes) == {
+        ("pkg.a", "pkg.b"),
+        ("other.a", "other.b"),
+    }
+
+    large = outcomes[("pkg.a", "pkg.b")]
+    small = outcomes[("other.a", "other.b")]
+
+    assert large.status == "UNAVAILABLE"
+    assert large.reason.startswith(
+        "SOURCE_BYTE_BUDGET_EXCEEDED:"
+    )
+    assert large.source_snapshots == {}
+    assert large.retained_raw_bytes == 0
+
+    assert small.status == (
+        "BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
+    )
+    assert small.reason is None
+    assert set(small.source_snapshots) == set(
+        small.reachable_modules
+    )
+    assert small.retained_raw_bytes <= 32

## FINAL_VERDICT
PASS. T01–T12, focused regressions, compilation, LF EOF, whitespace gate, LIVE continuity and workspace sync are verified. No production or runtime contract was changed.

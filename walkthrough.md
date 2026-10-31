# CONTEXTOR PY315-GLOBAL-REGRESSION-R1

## PREFLIGHT

DIRECT_EVIDENCE: local HEAD `7fc41c84f6253ade97035eead40c7dacc4061c14`; `git status --short` empty before edits. Contextor MCP was consulted first for `_run_git`, MCP cleanup orchestration, affected modules and call contexts (canonical revision 947, `workspace_sync=verified`). Local source confirmed every exact anchor. Globally repeated anchors were scoped to the named functions; scoped occurrence count was 1 in each case. No pre-existing modifications were overwritten. No production source changed.

## CURRENT_PRODUCTION_CONTRACTS

CODE_PATH_PROVED: capture/closure/reindex limits are all 256 in `contextor/core/symbol_engine/indexer.py`, `original_worker_binding.py`, and `original_worker_reindex_planning.py`. `original_worker_preparation.py` returns `SOURCE_MANIFEST_GRAPH_MISMATCH` when prepared manifest, supplied snapshot and graph hashes disagree. `git_context._run_git` removes a registered process record only when `poll()` confirms exit. Windows MCP orphan and owned-child cleanup use the process and parent classifiers plus `terminate_or_confirm_registered_process`; unresolved liveness or identity raises, preserving evidence. MCP call-context reads resolved the Git and cleanup functions.

## INTERPRETER_POLICY_310_315

The independent version matrix remains `VERSIONS=(10,11,12,13,14,15)`. Only `REQUIRED_VERSIONS=(10,15)` feeds the mandatory coverage gate. The module docstring now states 3.10/3.15 migration checkpoints, optional intermediate evidence, `NOT_COVERED` for absent optional versions, and no LIVE safety claim. Semantic assertions were unchanged. The coverage gate passed on this machine.

## ORIGINAL_WORKER_LIMIT_256

Negative selectors and closures now exceed 256: capture selector 257, closure `a` plus 256 extras = 257, full preview `a,b,helper` plus 254 extras = 257, and package cycle `a,b` plus 255 modules = 257. Existing failure reasons and no-publication assertions remain unchanged. Production limits were not edited.

## GRAPH_MANIFEST_REASON

T05 now expects `SOURCE_MANIFEST_GRAPH_MISMATCH` for fabricated graph hash. T06 still expects `P1C0_SOURCE_EVIDENCE_UNAVAILABLE` for partial source evidence. Status `UNAVAILABLE` and null manifest assertions remain.

## GIT_PROCESS_LIVENESS_NEGATIVE_TEST

Successful and failed-after-exit Git fakes now expose `poll()` confirming exit. New negative fake raises during communication while `poll()` returns `None`; its test asserts the registry record is retained. No production `git_context.py` change.

## WINDOWS_ORPHAN_CLEANUP

The startup orchestration test now supplies Windows classifier results: PID 10 is an `ALIVE_MATCH` orphan and is terminated/removed; PID 11 has a live parent and remains. Dedicated identity and parent-classifier tests were not weakened.

## WINDOWS_OWNED_CHILD_CLEANUP

The owned-child orchestration test now supplies Windows parent classification: PID 30 is owned and terminated/removed; PID 31 is foreign/orphan relative to owner 100 and remains. It uses confirmation-based termination mock.

## TEN_ORIGINAL_FAILURES_RETEST

DIRECT_EVIDENCE: the exact ten specified node IDs passed: `10 passed, 1 warning in 40.28s`. The warning was FastMCP/Authlib's `AuthlibDeprecationWarning`, not a test failure.

## NEW_NEGATIVE_TEST

DIRECT_EVIDENCE: `test_git_communication_failure_retains_record_while_process_alive` passed: `1 passed, 1 warning in 3.99s`.

## FOCUSED_REGRESSION_RESULTS

- `py_compile` for all seven changed test files: PASS.
- Four original-worker modules: `36 passed in 22.62s`.
- Namespace parity module with `-rs`: `36 passed, 64 skipped in 9.92s`.
- Five focused MCP cleanup modules: `78 passed, 1 warning in 5.49s`.
- `git diff --check`: PASS.
- No full suite, whole `test_mcp_regressions.py`, restart, launcher operation, commit or production edit.

## SKIPPED_TESTS_PARTIAL_TAXONOMY

DIRECT_EVIDENCE from the one requested `-rs` run: exactly 16 tests each skipped for unavailable optional CPython 3.11, 3.12, 3.13 and 3.14, all at `_require` line 171 with `NOT_COVERED`. Python 3.10 and 3.15 tests ran and passed. Contextor MCP resolved `_require`; scoped text discovery found the namespace file's `pytest.skip` declaration and no `skipif` or platform skip declaration in the inspected changed/focused files. Other platform, dependency or feature skips may exist elsewhere, but their counts were not attested.

`FULL_SUITE_SKIP_COUNT_BEFORE=66`
`FULL_SUITE_SKIP_REASON_DISTRIBUTION=NOT_YET_FULLY_ATTESTED`

The prior full-suite output lacked `-rs`; no category is assigned to its remaining two skips.

## MCP_POST_CHANGE_AUDIT

All seven changed test modules and six related production modules resolved at canonical revision 954 with `workspace_sync=verified`. The changed/new test symbols resolved through `get_symbol_implementation` at revision 954, including the renamed 257-module case and new Git negative test. After a docstring formatting correction, the namespace module briefly reported `out_of_sync` at revision 954, then `verified` at revision 955 with no advisory warning. This is source synchronization only; loaded-runtime adoption was not claimed. No manual `update_file`.

## FILES_CHANGED

- `tests/test_cycle_semantics_namespace_cycle_parity.py`
- `tests/test_indexer_original_capture_handoff.py`
- `tests/test_original_worker_cycle_closure_binding.py`
- `tests/test_original_worker_full_preview_completeness.py`
- `tests/test_p1d3_package_cycle_integration.py`
- `tests/test_original_worker_manifest_preparation.py`
- `tests/test_mcp_regressions.py`

`walkthrough.md` was overwritten as the report and is excluded from source/test changed files.

## FULL_DIFFS

Full actual diff:

```diff
diff --git a/tests/test_cycle_semantics_namespace_cycle_parity.py b/tests/test_cycle_semantics_namespace_cycle_parity.py
index f3416a6..bd0b640 100644
--- a/tests/test_cycle_semantics_namespace_cycle_parity.py
+++ b/tests/test_cycle_semantics_namespace_cycle_parity.py
@@ -1,8 +1,9 @@
 """Cross-version CPython namespace-cycle execution contracts.
 
-Python 3.10–3.15 are independent execution targets.
-Missing interpreters are NOT_COVERED, never PASS.
-No LIVE runtime safety or warning suppression is certified.
+CPython 3.10 and 3.15 are mandatory migration checkpoints.
+Intermediate interpreter evidence is optional; missing optional versions
+are NOT_COVERED, never PASS.
+These tests do not certify LIVE runtime safety or warning suppression.
 """
 
 from __future__ import annotations
@@ -24,6 +25,7 @@ from contextor.core.cycle_semantics.package_model import (
 
 
 VERSIONS = (10, 11, 12, 13, 14, 15)
+REQUIRED_VERSIONS = (10, 15)
 
 _SAFE_NESTED = {
     "ctxpkg/__init__.py": "pass\n",
@@ -398,7 +400,7 @@ def test_315_eager_import_still_has_hazard(tmp_path):
 def test_required_interpreter_coverage_gate():
     missing = [
         "3." + str(minor)
-        for minor in VERSIONS
+        for minor in REQUIRED_VERSIONS
         if _interpreter(minor) is None
     ]
 
diff --git a/tests/test_indexer_original_capture_handoff.py b/tests/test_indexer_original_capture_handoff.py
index 24e28cd..2b3a7a4 100644
--- a/tests/test_indexer_original_capture_handoff.py
+++ b/tests/test_indexer_original_capture_handoff.py
@@ -91,7 +91,7 @@ def test_p1d2a_t06_invalid_selector_rejected(tmp_path, isolated_dirs):
         "a",
         frozenset({""}),
         frozenset({"a", 7}),
-        frozenset(f"x{i}" for i in range(17)),
+        frozenset(f"x{i}" for i in range(257)),
     ]
     for selected in invalid:
         with pytest.raises(ValueError):
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index 5938d8b..835b787 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -3223,6 +3223,9 @@ def test_git_never_inherits_mcp_stdin_and_unregisters_after_exit(tmp_path, monke
         def communicate(self):
             return "abc123\n", ""
 
+        def poll(self):
+            return self.returncode
+
     registered = []
     removed = []
 
@@ -3259,6 +3262,9 @@ def test_git_unregisters_even_when_communication_fails(tmp_path, monkeypatch):
         def communicate(self):
             raise OSError("simulated pipe failure")
 
+        def poll(self):
+            return 1
+
     record = registry / "git-9876.json"
     removed = []
     monkeypatch.setattr(git_context.subprocess, "Popen", BrokenProcess)
@@ -3269,6 +3275,54 @@ def test_git_unregisters_even_when_communication_fails(tmp_path, monkeypatch):
     assert removed == [record]
 
 
+def test_git_communication_failure_retains_record_while_process_alive(
+    tmp_path, monkeypatch,
+):
+    registry = tmp_path / "registry"
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(registry),
+    )
+
+    class RunningProcess:
+        pid = 9877
+        returncode = None
+
+        def __init__(self, *_args, **_kwargs):
+            pass
+
+        def communicate(self):
+            raise OSError("simulated live pipe failure")
+
+        def poll(self):
+            return None
+
+    record = registry / "git-9877.json"
+    removed = []
+
+    monkeypatch.setattr(
+        git_context.subprocess,
+        "Popen",
+        RunningProcess,
+    )
+    monkeypatch.setattr(
+        git_context,
+        "register_process",
+        lambda *_args, **_kwargs: record,
+    )
+    monkeypatch.setattr(
+        git_context,
+        "remove_record",
+        removed.append,
+    )
+
+    assert git_context._run_git(
+        ["status"], str(tmp_path)
+    ) is None
+
+    assert removed == []
+
+
 def test_registry_rejects_reused_pid(monkeypatch):
     record = {
         "pid": 123,
@@ -3301,15 +3355,28 @@ def test_startup_cleanup_stops_only_orphaned_registered_processes(tmp_path, monk
     )
     stopped = []
 
-    monkeypatch.setattr(mcp_server, "record_matches_process", lambda _record: True)
     monkeypatch.setattr(
         mcp_server,
-        "process_identity",
-        lambda pid: ("python.exe", None, pid == 21),
+        "sys_platform_is_windows",
+        lambda: True,
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "classify_registered_windows_process",
+        lambda _record: "ALIVE_MATCH",
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "classify_registered_windows_parent",
+        lambda record: (
+            "ORPHAN"
+            if record["parent_pid"] == 20
+            else "PARENT_ALIVE"
+        ),
     )
     monkeypatch.setattr(
         mcp_server,
-        "terminate_registered_process",
+        "terminate_or_confirm_registered_process",
         lambda record: stopped.append(record["pid"]) or True,
     )
 
@@ -3331,7 +3398,21 @@ def test_shutdown_cleanup_stops_only_children_owned_by_server(tmp_path, monkeypa
     stopped = []
     monkeypatch.setattr(
         mcp_server,
-        "terminate_registered_process",
+        "sys_platform_is_windows",
+        lambda: True,
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "classify_registered_windows_parent",
+        lambda record: (
+            "PARENT_ALIVE"
+            if record["parent_pid"] == 100
+            else "ORPHAN"
+        ),
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "terminate_or_confirm_registered_process",
         lambda record: stopped.append(record["pid"]) or True,
     )
 
diff --git a/tests/test_original_worker_cycle_closure_binding.py b/tests/test_original_worker_cycle_closure_binding.py
index 2fca506..ab0818c 100644
--- a/tests/test_original_worker_cycle_closure_binding.py
+++ b/tests/test_original_worker_cycle_closure_binding.py
@@ -111,7 +111,7 @@ def test_p1d2b_t06_nonindexed_reachable_module_rejected(tmp_path, isolated_dirs)
 
 def test_p1d2b_t07_closure_above_selection_budget_rejected(tmp_path, isolated_dirs):
     index = _index(_repo(tmp_path), "a", "b", "helper")
-    graph = {"a": {"a", *(f"x{i}" for i in range(16))}}
+    graph = {"a": {"a", *(f"x{i}" for i in range(256))}}
     result = assess_original_worker_cycle_closure(index, graph)
     assert result.reason == "CLOSURE_MODULE_LIMIT"
     assert result.source_snapshots == {}
diff --git a/tests/test_original_worker_full_preview_completeness.py b/tests/test_original_worker_full_preview_completeness.py
index 581c203..078d8f5 100644
--- a/tests/test_original_worker_full_preview_completeness.py
+++ b/tests/test_original_worker_full_preview_completeness.py
@@ -237,7 +237,7 @@ def test_p1d2g_t05_oversized_closure_skips_second_index(
         b"import helper",
     ]
 
-    for number in range(14):
+    for number in range(254):
         module_id = f"x{number}"
 
         (root / f"{module_id}.py").write_bytes(
diff --git a/tests/test_original_worker_manifest_preparation.py b/tests/test_original_worker_manifest_preparation.py
index 0a4c5fb..d3033e6 100644
--- a/tests/test_original_worker_manifest_preparation.py
+++ b/tests/test_original_worker_manifest_preparation.py
@@ -148,7 +148,7 @@ def test_p1d2c_t05_inconsistent_semantic_graph_rejected(
 
     assert result.status == "UNAVAILABLE"
     assert result.reason == (
-        "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+        "SOURCE_MANIFEST_GRAPH_MISMATCH"
     )
     assert result.manifest is None
 
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index 8f21a76..a2ab895 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -732,11 +732,11 @@ def test_p0_rejects_package_assessment_disguised_as_flat(tmp_path, isolated_dirs
     assert result[0].reason == "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS"
 
 
-def test_seventeen_selected_modules_fail_before_capture(tmp_path, isolated_dirs):
+def test_two_hundred_fifty_seven_selected_modules_fail_before_capture(tmp_path, isolated_dirs):
     sources = {"a.py": "import b\n" + "".join(
-        f"import m{i:02d}\n" for i in range(15)
+        f"import m{i:02d}\n" for i in range(255)
     ), "b.py": "import a\n"}
-    sources.update({f"m{i:02d}.py": "pass\n" for i in range(15)})
+    sources.update({f"m{i:02d}.py": "pass\n" for i in range(255)})
     root = write_synthetic_repository(tmp_path / "repo", sources)
     index, graph = _indexed(root)
     plan = plan_original_worker_reindex(index, graph.hard_edges)
```

## REMAINING_UNKNOWN

The exact reason distribution of all 66 skips in the earlier global suite remains unattested until a later user-run full suite with `-rs`. The global suite was not rerun here. Python 3.15 launcher migration and production runtime adoption were outside this task.

## FINAL_VERDICT

`PASS_TEN_FAILURES_RECONCILED_GLOBAL_GATE_OPEN` — all ten original failures and the new fail-closed liveness test passed, the specified focused regressions passed, and all edits were confined to tests. The user-run global suite remains the next certification gate.


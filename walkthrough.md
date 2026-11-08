# C16-B03-P1D3-P12-F1 — two-failure test contract correction

## HEAD_BEFORE_AFTER

- DIRECT_EVIDENCE: local HEAD before/after `2358650effe3208842b400fa7697edb035f93da6`; no commit or push. Initial worktree already contained modifications to `contextor/core/cycle_semantics/activation_view.py`, `tests/test_cycle_semantics_activation_view.py`, and `walkthrough.md`; these were preserved without editing.
- Contextor MCP first: revision 1118, state_id `20261106_195021`, repo_id `ctx_8efc50d8`, canonical_state=fresh, workspace_sync=verified, LIVE provenance. Graph/cycles fresh; 16 structural DFS cycles, 16 active warnings, model_pass_count=0, cycle_semantics stale, syntax errors=0.
- Pre-edit test SHA-256 `f822775abbf75608f37b0404db810c93fd4f852b2f7ffdf2d04e98b03ed97471` matched metadata-selected FileState.

## FILES_CHANGED

- `tests/test_cycle_semantics_capture_capacity.py` — current task.
- `walkthrough.md` — report, excluded from its own diff.
- The two pre-existing P12 source/test modifications remained in the worktree and are outside this task's FILES_CHANGED.

## T01_OBSOLETE_CONSTANT_ROOT_CAUSE

- DIRECT_EVIDENCE: the old T01 referenced `original_worker_reindex_planning._MAX_SELECTED`, a constant no longer present in the shared selector contract. The test now checks actual selector identity and retains the 256-module capture limit assertion. No production constant was restored or limit altered.

## REINDEX_SELECTOR_IDENTITY_CONTRACT

- CONTRACT_PROVED by targeted PASS: `original_worker_reindex_planning._select_original_worker_sources is original_worker_binding._select_original_worker_sources`; `original_worker_binding._MAX_MODULES == indexer._MAX_ORIGINAL_WORKER_CAPTURE_MODULES == 256`.
- The import block and every other assertion in the module were unchanged. T02's 257-module negative contract passed.

## CPYTHON_310_IDENTITY

- DIRECT_EVIDENCE: `C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe` exists. `-I -B -c` reported version 3.10.9 and implementation `cpython`. Production repository `.venv` reported CPython 3.15.2 / `cpython`.

## REQUIRED_INTERPRETER_GATE

- `REQUIRED_VERSIONS=(10,15)` in `tests/test_cycle_semantics_namespace_cycle_parity.py` remained unchanged. The required coverage gate passed with both interpreters available. The parametrized matrix ran 3.10 and 3.15 cases; no mandatory-version skip was reported. The 3.11–3.14 cases remain `NOT_COVERED` when unavailable, not PASS.

## TARGETED_TEST_RESULTS

- In one PowerShell process, `CONTEXTOR_PYTHON_3_10` was set for the child pytest process and exactly the two requested modules were run through repository CPython 3.15.2: **40 passed, 64 skipped, 0 failed** in 20.78s. Skips: 16 each for CPython 3.11, 3.12, 3.13, 3.14; all say `NOT_COVERED: interpreter unavailable`.
- T01, T02 and the required interpreter gate passed. `git diff --check` exited 0, with only Git working-copy line-ending notices. No full pytest.

## GUI_ENVIRONMENT_INHERITANCE

- CODE_PATH_PROVED `contextor/ui/test_runner.py::_popen` uses `subprocess.Popen` without an `env=` argument. Python therefore passes the GUI process environment to pytest. Its command uses the GUI `sys.executable`; no GUI code was changed.
- To expose the existing 3.10 interpreter to the GUI test runner, set `$env:CONTEXTOR_PYTHON_3_10 = 'C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe'` in the PowerShell process that launches the GUI, then launch the GUI from that same process. A GUI already launched from another parent does not gain this later shell-only variable. No permanent user/system environment change was made.

## MCP_POST_CHANGE_AUDIT

- MCP target test context after edit: revision 1119, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, LIVE provenance; graph/cycles fresh, cycle_semantics stale, syntax errors=0, structural DFS cycles=16, active warnings=16, model_pass_count=0.
- Metadata revision 1119/state_id `20261106_195021`/repo_id `ctx_8efc50d8`. Changed test SHA-256 `b1e76d54c70c58e0b0dd44d329cb0102b7eab131ff7beb7358bd2bfef2e8a3a7` equals its FileState SHA-256. No FULL, update_file, restart, interpreter switch for Contextor, dependency installation or warning suppression.

## REMAINING_UNKNOWN

- GUI process environment at its next launch was not inspected or changed; GUI test-suite parity in that process remains unverified. Active backend loaded-code adoption of prior P12 implementation remains outside F1. Canonical cycle_semantics remains stale.

## FULL_DIFFS

Complete actual diff for the only test modified by F1 follows. `walkthrough.md` is excluded from its own diff; pre-existing P12 diffs are not F1 changes.
diff --git a/tests/test_cycle_semantics_capture_capacity.py b/tests/test_cycle_semantics_capture_capacity.py
index c026574..5663f52 100644
--- a/tests/test_cycle_semantics_capture_capacity.py
+++ b/tests/test_cycle_semantics_capture_capacity.py
@@ -18,8 +18,13 @@ def _inline_worker(monkeypatch):
 
 def test_t01_module_cap_contracts_are_aligned():
     assert (
-        original_worker_reindex_planning._MAX_SELECTED
-        == original_worker_binding._MAX_MODULES
+        original_worker_reindex_planning
+        ._select_original_worker_sources
+        is original_worker_binding
+        ._select_original_worker_sources
+    )
+    assert (
+        original_worker_binding._MAX_MODULES
         == indexer._MAX_ORIGINAL_WORKER_CAPTURE_MODULES
         == 256
     )

## FINAL_VERDICT

PASS

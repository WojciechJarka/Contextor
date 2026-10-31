# CONTEXTOR PY315-M2-R4 — async watcher test synchronization

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP was used first. `tests.test_live_watcher_watchdog` and `contextor.core.live_state.watcher` were fresh at canonical revision 956 with `workspace_sync=verified`. Contextor returned the complete test function and watcher source ranges. HEAD was `f0fc80c1f71bb08001380bcdcc0f2a6bd00d11a9`; the sole pre-existing worktree modification was `walkthrough.md`. The prescribed SEARCH occurred exactly once.

## ASYNC_CONTRACT_EVIDENCE

CODE_PATH_PROVED: `DesktopLiveWatcher.poll_once()` calls `submit_update_file`, records an accepted `job_id` in `_inflight_updates`, and returns reconciled completions from `_poll_inflight_updates()`. An accepted but unfinished update can therefore yield `[]`. The test starts `CanonicalLiveServer` and uses manual `_enqueue_path`; it does not start a native watchdog Observer. The existing recovery phase already used a bounded polling wait.

## EXACT_PATCH

Replaced the first immediate `watcher.poll_once()` assertion with the supplied 5-second polling loop and 10-ms sleep. The existing recovery wait, event order, statuses, syntax/recovery assertions, and diagnostics remain intact. No source or other test file changed.

## PY_COMPILE

PASS: Python 3.15 `py_compile.compile(..., doraise=True)` wrote its `.pyc` outside the repository to `C:\Temp\Contextor_PY315_M2_Lab\test_live_watcher_watchdog.pyc`.

## PY315_SINGLE_TEST

PASS: `test_syntax_error_and_recovery_contract_survives_watchdog_adapter` — `1 passed in 2.72s`.

## PY315_FIVE_REPETITIONS

PASS: Five independent runs of that exact test, each `1 passed` (2.14s, 1.71s, 1.65s, 2.03s, 1.85s). All returned exit code 0.

## PY310_SINGLE_TEST

PASS: Production Python 3.10 environment ran the exact test once — `1 passed in 1.23s`. The production environment was not changed.

## PY315_FIVE_MODULE_SUITE

PASS: The five specified M2 modules ran on the lab Python 3.15 with `-q -rs -p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`, `CONTEXTOR_PYTHON_3_10=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, and `--basetemp C:\Temp\Contextor_PY315_M2_Lab\pytest-tmp`. Result: `156 passed, 64 skipped in 24.30s`; exit code 0.

## SKIP_REASONS

Exactly 64 optional interpreter skips remain: 16 each for unavailable CPython 3.11, 3.12, 3.13, and 3.14 at `tests/test_cycle_semantics_namespace_cycle_parity.py:171`, each marked `NOT_COVERED`.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor module context for `tests.test_live_watcher_watchdog` returned canonical revision 957, `canonical_state=fresh`, `workspace_sync=verified`, `provenance=live`, and no advisory warning. Git status showed only `tests/test_live_watcher_watchdog.py` and the report modified. No `update_file`, restart, dependency change, or commit occurred.

## FILES_CHANGED

- `tests/test_live_watcher_watchdog.py`

`walkthrough.md` was overwritten as the required report and is excluded from source/test diff accounting.

## FULL_DIFFS

### tests/test_live_watcher_watchdog.py — complete actual diff

```diff
diff --git a/tests/test_live_watcher_watchdog.py b/tests/test_live_watcher_watchdog.py
index 1ecb2f2..c421cc4 100644
--- a/tests/test_live_watcher_watchdog.py
+++ b/tests/test_live_watcher_watchdog.py
@@ -233,7 +233,13 @@ def test_syntax_error_and_recovery_contract_survives_watchdog_adapter(tmp_path):
 
     try:
         watcher._enqueue_path(str(target))
-        assert watcher.poll_once() == [str(target.resolve())]
+        syntax_updated = []
+        syntax_deadline = time.monotonic() + 5.0
+        while time.monotonic() < syntax_deadline and not syntax_updated:
+            syntax_updated = watcher.poll_once()
+            if not syntax_updated:
+                time.sleep(0.01)
+        assert syntax_updated == [str(target.resolve())]
 
         target.write_text("def repaired():\n    return 1\n", encoding="utf-8")
         watcher._enqueue_path(str(target))
```

## FINAL_VERDICT

`PASS_PY315_M2_TARGETED`. STOP; await `proceduj`.

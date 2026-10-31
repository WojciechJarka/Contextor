# CONTEXTOR PY315-M3B — Windows venv redirector cross-version test

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP was used first. It returned the complete `test_venv_redirector_only_termination_closes_backend_job_tree` implementation and `_protect_mcp_server_job` implementation, both at canonical revision 957 with `workspace_sync=verified`, fresh state, and no advisory warning. HEAD was `13993e6ddd0fc866b779faad36a3f75893d2d1dc`; only pre-existing worktree modification was `walkthrough.md`. The exact SEARCH occurred once. Lab Python was 3.15.2, production `.venv` Python was 3.10.9, and lab `pip check` reported no broken requirements.

## EXACT_TEST_PATCH

Applied the supplied test-only `CONTEXTOR_TEST_VENV_PYTHON` override at the unique anchor. When unset, the original repository `.venv/Scripts/python.exe` path remains selected. No production source or other test was changed. All existing redirector/owner distinctness, descendant, survival, identity, and cleanup assertions remain.

## PY_COMPILE

PASS: Lab Python 3.15 `py_compile.compile(..., doraise=True)` wrote bytecode to `C:\Temp\Contextor_PY315_M2_Lab\test_mcp_job_tree_isolated_windows.pyc`, outside the repository.

## PY315_REDIRECTOR_RESULTS

PASS: With the override set only in the test command process to `C:\Temp\Contextor_PY315_M2_Lab\venv\Scripts\python.exe`, the exact test returned `2 passed in 2.27s`, exit code 0. Both `persistent-backend` and `host-owned` variants ran. The lab venv executable is Python 3.15.2 and its `sys._base_executable` is `C:\Python315\python.exe`.

## PY310_REDIRECTOR_RESULTS

PASS: In a separate command process with `CONTEXTOR_TEST_VENV_PYTHON` removed, production Python 3.10 ran the exact same two variants using the original repository `.venv`: `2 passed in 2.37s`, exit code 0. The persistent user/system environment was not modified.

## REDIRECTOR_AND_OWNER_IDENTITIES

CONTRACT_PROVED by the passing test: `_identity_record` verifies positive creation time and executable image for the redirector and actual owner; `assert redirector.pid != info["owner"]` verifies distinct PIDs. The override path selects the lab Python 3.15 venv redirector; the `owner.py` script is launched through that interpreter. The test does not record owner `sys.version` or redirector PID to a persistent file, so those exact runtime values are not independently available after exit. The lab test's in-memory identity assertions passed.

The subsequent Python 3.10 run reused `--basetemp`, replacing the first run's external PID files. Its retained `ready.json` evidence is:

| Case | Actual owner PID | Child PID | Grandchild PID | LIVE PID | Sentinel PID |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 8524 | 14112 | 8288 | 15652 | 11388 |
| 1 | 14100 | 11876 | 12260 | 2204 | 15308 |

Read-only `probe_process_identity` after the Python 3.10 run returned `dead` for every PID in the table. Lab-run PID values were not preserved across the second run; its test itself completed all identity-bound assertions and cleanup.

## JOB_DESCENDANT_TERMINATION

CONTRACT_PROVED by four passing variants: after identity-bound redirector termination, the test waited for the recorded actual owner, child, and grandchild identities to be gone. This includes both job roles on each Python version.

## BREAKAWAY_SURVIVAL

CONTRACT_PROVED by four passing variants: the recorded breakaway LIVE analogue was alive after redirector and Job owner termination, before the test's `finally` cleanup.

## SENTINEL_SURVIVAL

CONTRACT_PROVED by four passing variants: the unrelated sentinel was alive after redirector and Job owner termination, before its `finally` cleanup.

## PROCESS_CLEANUP

CONTRACT_PROVED: The test's `finally` block applies identity-bound `terminate_or_confirm_registered_process` to actual owner, child, grandchild, LIVE analogue, and redirector, then terminates/waits for the sentinel; unresolved cleanup would fail the test. All four variants passed. DIRECT_EVIDENCE: all ten retained Python 3.10 owner/child/grandchild/LIVE/sentinel PIDs were `dead` at postcheck. A read-only Win32 process query found no Python process with the selected test `--basetemp` path in its command line. Exact lab-run PIDs are UNKNOWN because pytest replaced its temp directory on the second run; no unrelated process was terminated during postcheck.

## PRODUCTION_ISOLATION

Postcheck: lab Python remained 3.15.2, production Python remained 3.10.9, and lab `pip check` still passed. Git showed only the specified test and `walkthrough.md` modified. No production source, dependencies, launchers, autostart, backend, or LIVE state was changed; no restart, `update_file`, or commit occurred. The test terminated only its own synthetic processes.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Read-only Contextor module context for `tests.test_mcp_job_tree_isolated_windows` returned canonical revision 958, `workspace_sync=verified`, `canonical_state=fresh`, `provenance=live`, and no advisory warning. This establishes current source/index synchronization, not a production interpreter switch.

## FILES_CHANGED

- `tests/test_mcp_job_tree_isolated_windows.py`

`walkthrough.md` is the report and is excluded from source/test diff accounting.

## FULL_DIFFS

### tests/test_mcp_job_tree_isolated_windows.py — complete actual diff

```diff
diff --git a/tests/test_mcp_job_tree_isolated_windows.py b/tests/test_mcp_job_tree_isolated_windows.py
index a58b82c..b058440 100644
--- a/tests/test_mcp_job_tree_isolated_windows.py
+++ b/tests/test_mcp_job_tree_isolated_windows.py
@@ -299,7 +299,12 @@ def test_venv_redirector_only_termination_closes_backend_job_tree(
 ):
     """Prove cleanup behavior when only the venv launcher is terminated."""
     repo_root = Path(__file__).resolve().parents[1]
-    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
+    override_python = os.environ.get("CONTEXTOR_TEST_VENV_PYTHON")
+    venv_python = (
+        Path(override_python)
+        if override_python is not None
+        else repo_root / ".venv" / "Scripts" / "python.exe"
+    )
 
     assert venv_python.is_file()
 
```

## FINAL_VERDICT

`PASS_PY315_M3B`. STOP.

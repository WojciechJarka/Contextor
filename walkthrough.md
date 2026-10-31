# CONTEXTOR PY315-M5B — exact two-issue remediation

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP first inspected `_interpreter`, the coverage gate, the acyclic-lease test, and `ContextorFacade.analyze_single_file`; all four had canonical revision 959, fresh state, `workspace_sync=verified`, no advisory warning. Production and clone HEAD were both `325537c80fa832b7c7f3a4e7081017861f209d30`. Production Python 3.10.9, clone Python 3.15.2, clone `pip check` PASS. Initial production status was only pre-existing `M walkthrough.md`; clone status clean. Exact assertion anchor count in production: 1. Both original test files normalized to Git blob `414ff159f9dbe2c398d62dbb8aa647cfd606fb06`; raw SHA-256 differed before copy because the checkouts used different line endings.

## FAILURE_1_ROOT_CAUSE

CODE_PATH_PROVED: `_interpreter(10)` accepts `CONTEXTOR_PYTHON_3_10` and validates each candidate with `-I -B -c`, requiring output `3.10` and `cpython`. The coverage gate fails with `COVERAGE_INCOMPLETE` if a required interpreter is missing; skipped scenarios are explicitly `NOT_COVERED`. The global run omitted the process-local override, so the mandatory 3.10 candidate was unavailable to that run. The test and required-version definitions were not changed.

## PY310_INTERPRETER_VALIDATION

DIRECT_EVIDENCE: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -I -B -c` returned `sys.version_info[:2] == (3, 10)`, `sys.implementation.name == 'cpython'`, and the expected production executable path. No new 3.10 environment was created.

## FAILURE_2_ROOT_CAUSE

DIRECT_EVIDENCE: the production facade annotation is `dict[str, Any] | None`. `inspect.signature` displays the 3.10 result as `dict[str, typing.Any] | None` and the 3.15 result as `dict[str, Any] | None`; all other observed parameter, default, and return displays match. The old test expected only `typing.Any`. The AST import assertions were unaffected.

## EXACT_TEST_CORRECTION

Changed only the specified assertion in production `tests/test_full_analysis_coordination.py`: normalize `typing.Any` to `Any` in the signature display and expect `dict[str, Any]`. Parameter names/order/defaults, other annotations, return annotation, AST import assertions, and production `facade.py` were untouched. Copied that edited file alone to the isolated clone as instructed.

## CLONE_FILE_SHA256_PARITY

DIRECT_EVIDENCE: production and clone edited test SHA-256 both `7691552083FF026DD843480EFA61AFBB2720B2F73562E0E2A14EB082AA7EBBA0`. The clone now shows only this intended test modification. No other production file was copied.

## PY310_SIGNATURE_TEST

DIRECT_EVIDENCE: production Python 3.10 ran the single test against cloned source with `-q -rs -p no:cacheprovider --basetemp C:\Temp\ctx315m5b\sig310`: `1 passed in 2.93s`, exit 0.

## PY315_SIGNATURE_TEST

DIRECT_EVIDENCE: clone Python 3.15 ran the same single test against cloned source with separate `--basetemp C:\Temp\ctx315m5b\sig315`: `1 passed in 2.90s`, exit 0.

## CROSS_VERSION_NAMESPACE_MATRIX

DIRECT_EVIDENCE: clone Python 3.15 ran the complete `tests/test_cycle_semantics_namespace_cycle_parity.py` with process-local `CONTEXTOR_PYTHON_3_10=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, `-q -rs -p no:cacheprovider --basetemp C:\Temp\ctx315m5b\parity`: **36 passed, 64 skipped**, exit 0. Skip report: 16 each for missing optional CPython 3.11, 3.12, 3.13, and 3.14; each labeled `NOT_COVERED`.

## MANDATORY_COVERAGE_STATUS

CONTRACT_PROVED by the passing coverage gate and matrix: mandatory CPython 3.10 and 3.15 cases executed; no mandatory interpreter was `NOT_COVERED`. Optional 3.11–3.14 cases remain explicitly `NOT_COVERED`, not PASS. No coverage or semantic expectation was weakened.

## GLOBAL_REGRESSION_USER_COMMAND

Prepared only; **not executed**. Full collection, normal optional skips, external short basetemp, complete log, preserved exit status, process-local runtime isolation and cleared inherited MCP settings:

```powershell
Set-Location -LiteralPath 'C:\Temp\Contextor_PY315_M2_Lab\Contextor_M5A_Repo'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:CONTEXTOR_PYTHON_3_10 = 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe'
$env:CONTEXTOR_CACHE_DIR = 'C:\Temp\ctx315m5b\cache'
$env:CONTEXTOR_STATE_DIR = 'C:\Temp\ctx315m5b\state'
$env:CONTEXTOR_OUTPUT_DIR = 'C:\Temp\ctx315m5b\output'
$env:CONTEXTOR_REGISTRY_DIR = 'C:\Temp\ctx315m5b\registry'
Remove-Item Env:PYTHONPATH,Env:CONTEXTOR_MCP_TOKEN,Env:CONTEXTOR_MCP_HOST,Env:CONTEXTOR_MCP_PORT,Env:CONTEXTOR_MCP_SERVER_ROLE,Env:CONTEXTOR_MCP_TRANSPORT,Env:CONTEXTOR_MCP_PROCESS_REGISTRY -ErrorAction SilentlyContinue
& 'C:\Temp\Contextor_PY315_M2_Lab\Contextor_M5A_Repo\.venv\Scripts\python.exe' -m pytest -v -rs -p no:cacheprovider --basetemp 'C:\Temp\ctx315full' 'C:\Temp\Contextor_PY315_M2_Lab\Contextor_M5A_Repo\tests' 2>&1 | Tee-Object -FilePath 'C:\Temp\Contextor_PY315_M2_Lab\M5B_full_py315.log'
$pytestExit = $LASTEXITCODE
exit $pytestExit
```

## PRODUCTION_ISOLATION

All test runs used separate external basetemps under `C:\Temp\ctx315m5b`, process-local external cache/state/output/registry, `PYTHONDONTWRITEBYTECODE=1`, and removal of inherited MCP/PYTHONPATH settings. No production Desktop, backend or LIVE was launched or restarted. No full pytest, builds, installs, dependency, launcher, autostart, venv, `update_file`, `analyze_project`, or commit action occurred.

## MCP_POSTCHANGE_AUDIT

DIRECT_EVIDENCE: read-only Contextor MCP module context for `tests.test_full_analysis_coordination` after edit: canonical revision **960**, `canonical_state=fresh`, `workspace_sync=verified`, advisory warning `null`. Desktop watcher synchronization completed without forced update.

## FILES_CHANGED

Production `C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py`; isolated clone `C:\Temp\Contextor_PY315_M2_Lab\Contextor_M5A_Repo\tests\test_full_analysis_coordination.py` (byte-identical copy); production `C:\Temp\Contextor_Repo\walkthrough.md` (report, excluded from diff requirement). No other source/test/docs file changed.

## FULL_DIFFS

Complete actual Git diff for both production and clone test files: Git reports the same 4 insertions and 2 deletions for each. The edited files are byte-identical after the copy.

```diff
diff --git a/tests/test_full_analysis_coordination.py b/tests/test_full_analysis_coordination.py
index 414ff15..9b94708 100644
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -63,10 +63,12 @@ def test_acyclic_lease_import_contract():
         "(root_dir: str, layer_dir: str, log=None, progress_callback=None, "
         "additional_excludes: list[str] | None = None) -> str"
     )
-    assert str(inspect.signature(facade.ContextorFacade.analyze_single_file)) == (
+    assert str(inspect.signature(facade.ContextorFacade.analyze_single_file)).replace(
+        "typing.Any", "Any"
+    ) == (
         "(file_path: str, repo_root: str, log=None, progress_callback=None, "
         "additional_excludes: list[str] | None = None, "
-        "publication_result: dict[str, typing.Any] | None = None) -> str"
+        "publication_result: dict[str, Any] | None = None) -> str"
     )
```

## REMAINING_UNKNOWN

The corrected full Python 3.15 regression has not run by contract. Optional Python 3.11–3.14 interpreters remain unavailable and their cases remain `NOT_COVERED`. Test results do not imply production Python 3.15 adoption.

## FINAL_VERDICT

`PASS_PY315_M5B_READY_FOR_GLOBAL_RERUN`. Both focused signature tests and mandatory cross-version matrix passed; MCP workspace sync verified. STOP.

# C16-B03-P1D3-P13B-R1 — optional Ruff in project launcher

## HEAD_BEFORE_AFTER

- Preflight Contextor MCP: revision 1122, state_id `20261106_195021`, repo_id `ctx_8efc50d8`, canonical_state=fresh, workspace_sync=verified, LIVE provenance, graph/cycles fresh, cycle_semantics stale, 16 structural DFS cycles, 16 active warnings, model_pass_count=0. Repository `.venv` is CPython 3.15.2.
- HEAD before/after `924d69e6e48b367f4e9848e1e9ce9339c7f57059`; pre-edit worktree clean, no Git mutation. P13A native 3.15 test and P13B metadata/test changes were present. Target test pre-edit SHA-256 matched FileState; BAT is outside Python FileState.
- Exact target paths, matching anchors and planned diff summary were recorded in this `walkthrough.md` before edits: `run_contextor.bat:73-74`, `:89-91`, `:94`, and EOF of `tests/test_py315_launcher_migration_guard.py`.

## FILES_CHANGED

- `run_contextor.bat`
- `tests/test_py315_launcher_migration_guard.py`
- `walkthrough.md` (report, excluded from its own diff)

## RUFF_VERSION_CHECK

- Literal new `:check_ruff` block checks project-local `importlib.metadata.version('ruff')` against parsed numeric `>= (0,17,0)`, confirms `%VENV_DIR%\Scripts\ruff.exe` exists and that `--version` exits successfully. `pyproject.toml` still declares `ruff>=0.17.0` and `target-version=py315`.
- This is source-contract evidence. The launcher was intentionally not executed, so actual later normal-start behavior remains unobserved.

## LOCAL_VENV_INSTALLATION

- Literal `:install_ruff` block uses only `"%VENV_PY%" -m pip install "ruff>=0.17.0"`; the executable check is under `%VENV_DIR%\Scripts`. No global installer or manual installation was run. The cutover guard appears before the new check and installation labels.

## EXISTING_RUFF_NO_REINSTALL

- The existing-version path passes `m.version`, executable existence and `--version` before jumping to `:check_backend_autostart`; it does not take the install branch when all checks pass. Missing/older/unusable Ruff enters `:install_ruff`.

## OPTIONAL_FAILURE_NONBLOCKING

- The `:ruff_unavailable` label emits the exact optional-tool warning and jumps to `:check_backend_autostart`. Pip, executable-absence and failed `--version` paths all reach it. No fail-closed runtime dependency branch was weakened.

## EXISTING_DEPENDENCY_PARITY

- Existing mandatory runtime import check, requirements installation and error handling are unchanged. Both successful dependency paths now jump to `:check_ruff`, then proceed to the original backend/GUI startup labels. No startup command changed. No Python 3.10 reference was added.

## TARGETED_TEST_RESULTS

- Exact two-module pytest command: **32 passed, 0 failed, 0 skipped, 2 installed-dependency deprecation warnings** in 6.45s. Existing launcher guard tests and the new literal Ruff source-contract test passed. No full suite.
- `git diff --check` exited 0 with only working-copy line-ending notices. The launcher was not run, no Ruff was installed manually or automatically during this task, and no production Python module changed.

## MCP_POST_CHANGE_AUDIT

- Immediate MCP read after editing observed revision 1122 and `workspace_sync=out_of_sync` for the changed test; after the active watcher completed, read-only MCP reported revision **1123**, state_id `20261106_195021`, repo_id `ctx_8efc50d8`, canonical_state=fresh, workspace_sync=verified, advisory=null, LIVE provenance, graph/cycles fresh, cycle_semantics stale, syntax_errors=0, structural DFS cycles=16, active warnings=16, model_pass_count=0.
- Changed test disk SHA-256 `5de787537a8483ebd507a14995904c4a66ace6b59b0edfc09f05e81ad9001bdb` equals FileState. BAT disk SHA-256 `d7abe672dc054704614c97548f57269100ce3e6862f6b260e8da382be47b9809`; BAT is not indexed in Python FileState.
- No FULL, update_file, restart, interpreter switch, dependency installation, commit/push, or warning-policy change.

## REMAINING_UNKNOWN

- Actual Ruff installation/reuse at a subsequent normal launcher start is untested. Active backend/Desktop loaded-code adoption and cycle_semantics freshness are not certified by this BAT/test patch.

## FULL_DIFFS

Complete actual Git diffs for the two task-changed files follow. `walkthrough.md` excluded from its own diff.
diff --git a/run_contextor.bat b/run_contextor.bat
index 9df2cdc..e62a060 100644
--- a/run_contextor.bat
+++ b/run_contextor.bat
@@ -71,7 +71,7 @@ echo Checking dependencies...
 if errorlevel 1 goto install_deps

 echo [OK] Dependencies are already installed.
-goto check_backend_autostart
+goto check_ruff


 :install_deps
@@ -88,6 +88,43 @@ if errorlevel 1 goto install_failed

 echo [SUCCESS] Dependencies installed.
 echo.
+goto check_ruff
+
+
+:check_ruff
+if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
+echo Checking Ruff development tool...
+
+"%VENV_PY%" -c "import importlib.metadata as m, re, sys; v=m.version('ruff'); p=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)',v); sys.exit(0 if p and tuple(map(int,p.groups())) >= (0,17,0) else 1)" >nul 2>&1
+if errorlevel 1 goto install_ruff
+
+if not exist "%VENV_DIR%\Scripts\ruff.exe" goto install_ruff
+
+"%VENV_DIR%\Scripts\ruff.exe" --version >nul 2>&1
+if errorlevel 1 goto install_ruff
+
+echo [OK] Ruff >=0.17.0 is available.
+goto check_backend_autostart
+
+
+:install_ruff
+if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
+echo [INFO] Installing Ruff into the project virtual environment...
+
+"%VENV_PY%" -m pip install "ruff>=0.17.0"
+if errorlevel 1 goto ruff_unavailable
+
+if not exist "%VENV_DIR%\Scripts\ruff.exe" goto ruff_unavailable
+
+"%VENV_DIR%\Scripts\ruff.exe" --version >nul 2>&1
+if errorlevel 1 goto ruff_unavailable
+
+echo [SUCCESS] Ruff installed and verified.
+goto check_backend_autostart
+
+
+:ruff_unavailable
+echo [WARNING] Ruff is unavailable. Continuing without optional lint tooling.
 goto check_backend_autostart


diff --git a/tests/test_py315_launcher_migration_guard.py b/tests/test_py315_launcher_migration_guard.py
index 01ca57b..c7a6010 100644
--- a/tests/test_py315_launcher_migration_guard.py
+++ b/tests/test_py315_launcher_migration_guard.py
@@ -106,3 +106,38 @@ def test_py315_project_metadata_and_ruff_contract():
         "pytest>=7.4"
         in config["project"]["optional-dependencies"]["dev"]
     )
+
+
+def test_launcher_optional_ruff_uses_project_venv():
+    source = (
+        ROOT / "run_contextor.bat"
+    ).read_text(encoding="utf-8").lower()
+
+    assert source.count("goto check_ruff") == 2
+    assert ":check_ruff\n" in source
+
+    assert "m.version('ruff')" in source
+    assert ">= (0,17,0)" in source
+
+    assert (
+        'if not exist "%venv_dir%\\scripts\\ruff.exe" '
+        'goto install_ruff'
+    ) in source
+
+    assert (
+        '"%venv_py%" -m pip install "ruff>=0.17.0"'
+    ) in source
+
+    assert ":install_ruff\n" in source
+    assert ":ruff_unavailable\n" in source
+
+    optional_failure = source.split(
+        ":ruff_unavailable\n", 1
+    )[1].split(
+        ":check_backend_autostart\n", 1
+    )[0]
+
+    assert "goto check_backend_autostart" in optional_failure
+    assert "continuing without optional lint tooling" in (
+        optional_failure
+    )

## FINAL_VERDICT

PASS

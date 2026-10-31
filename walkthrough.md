# CONTEXTOR PY315-M6B — launcher migration guard

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP first returned canonical revision 960, fresh, workspace_sync=verified, no advisory warning for relevant production Python modules. Current HEAD `4908f843622fc14a8c21513bace011e0fa135ed1` differs from expected `fc9b090f93670287beed964ab7c6bf8eb1f8fead` only by the preceding walkthrough.md auto-commit; the three BAT sources were unchanged before this task. Initial worktree clean. Production Python 3.10.9; `C:\Python315\python.exe` CPython 3.15.2. Backend PID 14936/creation identity 134379138541765783 authenticated ready; Desktop PID 1700 and LIVE PID 2372 active under Python 3.10.9. M6A offline wheelhouse present. Production guard absent.

## SOURCE_IMPLEMENTATION_PLAN

Before editing, the exact paths and intended changes were written to walkthrough.md: `C:\Temp\Contextor_Repo\run_contextor.bat` — entry/boundary guard and validated 3.15 bootstrap; `C:\Temp\Contextor_Repo\GUI_test_suite_installer.bat` — bang-safe early guard, validated 3.15 bootstrap and editable-install removal; `C:\Temp\Contextor_Repo\MCP_installer.bat` — bang-safe early guard, local .venv interpreter and editable-install removal; `C:\Temp\Contextor_Repo\tests\test_py315_launcher_migration_guard.py` — guarded synthetic-checkout regression tests. No other source/test edit was planned or made.

## MIGRATION_GUARD_BEHAVIOR

CODE_PATH_PROVED: all three scripts check `.contextor_py315_cutover.guard` in their own directory before Python, pip, Desktop, MCP or autostart operations. Guarded scripts print `CONTEXTOR_CUTOVER_ACTIVE` and exit 86 without pausing. The main launcher checks again at each requested label: create_venv, check_deps, install_deps, check_backend_autostart, install_backend_autostart, check_backend, start_backend, start_gui. No production guard was created. Test execution used only guarded script copies.

## RUN_CONTEXTOR_CHANGE

The existing `setlocal` without delayed expansion and existing-.venv selection remain. The missing-.venv bootstrap now tries `C:\Python315\python.exe`, then `python` on PATH; each candidate must pass `-I -B -c` for CPython 3.15 before `-m venv`. The hardcoded 3.10 path and unvalidated local-directory scan are removed. With a healthy existing .venv and no guard, source-based GUI and backend/autostart paths remain.

## GUI_INSTALLER_CHANGE

A short `DisableDelayedExpansion` phase evaluates the script-directory guard before the former delayed-expansion setup, retaining `!` in the guarded path. Existing .venv is selected unchanged. Without .venv, only validated CPython 3.15 from the two prescribed candidate sources may bootstrap. Setuptools 69.5.1, pytest, requirements and optional GUI logic remain; the entire `pip install -e ".[dev]"` step was removed and numbering is 1/4 through 4/4.

## MCP_INSTALLER_CHANGE

A short bang-safe guard phase runs before installer operations. The sole interpreter assignment is `%CD%\.venv\Scripts\python.exe`; missing file fails nonzero with an explicit local-venv message. No global/WinPython selection or venv creation remains. Existing MCP version check and optional dependency installation use that local interpreter. The optional `pip install -e .` block was removed; numbering is 1/2 through 2/2.

## PY315_BOOTSTRAP_SELECTION

CONTRACT_PROVED by source and static targeted tests: both bootstrap-capable scripts require `sys.implementation.name == 'cpython'` and `sys.version_info[:2] == (3, 15)` under `-I -B -c`; a non-3.15 candidate cannot be selected. The tests intentionally did not execute an unguarded launcher or create a real synthetic venv.

## ROLLBACK_COMPATIBILITY

CODE_PATH_PROVED: with the migration guard absent, the main launcher and GUI installer continue choosing an existing production .venv regardless of its Python version, preserving the intact Python 3.10 rollback environment. MCP installer likewise uses that local environment. This is source-path proof; an actual rollback was outside scope.

## WINDOWS_BANG_PATH_TEST

DIRECT_EVIDENCE: each BAT was copied to an external synthetic checkout with a guard, both with ordinary and exclamation-mark directory names, and run by `cmd.exe /D /C`. All six guarded cases returned exactly 86, printed the marker, created no .venv, and did not execute the synthetic main.py sentinel. No unguarded script was run.

## PY310_TARGETED_TEST_RESULTS

The first test invocation produced 12 setup errors because `C:\Temp\ctx315m6b` (parent of --basetemp) had not been created; no test assertions or copied BAT ran. After creating that external parent, production Python 3.10.9 ran only the new test file and `test_acyclic_lease_import_contract`: **12 passed in 2.19s**, exit 0, with `-q -rs -p no:cacheprovider --basetemp C:\Temp\ctx315m6b\py310`.

## PY315_TARGETED_TEST_RESULTS

The same initial basetemp setup error affected Python 3.15 before test execution. After creating the parent, isolated Python 3.15.2 ran exactly the same two targets with separate `--basetemp C:\Temp\ctx315m6b\py315`: **12 passed in 2.94s**, exit 0.

## PRODUCTION_PROCESS_IDENTITY

DIRECT_EVIDENCE after edits/tests: `get_backend_status()` remained authenticated and ready at PID 14936, creation identity 134379138541765783. Port 8765 still belonged to PID 14936. Desktop PID 1700 and LIVE PID 2372 remained under the Python 3.10.9 base executable. Production guard remained absent. No backend/Desktop/LIVE restart or process termination occurred.

## MCP_POSTCHANGE_AUDIT

Read-only Contextor MCP initially had not yet indexed the newly created test module. A later read returned `tests.test_py315_launcher_migration_guard` at canonical revision **961**, `canonical_state=fresh`, `workspace_sync=verified`, advisory warning null. No `update_file` or forced synchronization occurred. BAT files are outside Python module indexing; their exact current contents and diffs were verified directly.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\run_contextor.bat`
- `C:\Temp\Contextor_Repo\GUI_test_suite_installer.bat`
- `C:\Temp\Contextor_Repo\MCP_installer.bat`
- `C:\Temp\Contextor_Repo\tests\test_py315_launcher_migration_guard.py`
- `C:\Temp\Contextor_Repo\walkthrough.md` (report, excluded from source/test diff accounting)

## FULL_DIFFS

Complete actual Git diff for all three changed BAT files:

```diff
diff --git a/GUI_test_suite_installer.bat b/GUI_test_suite_installer.bat
index 8faa56a..bf84a16 100644
--- a/GUI_test_suite_installer.bat
+++ b/GUI_test_suite_installer.bat
@@ -1,4 +1,12 @@
 @echo off
+setlocal DisableDelayedExpansion
+cd /d "%~dp0"
+if errorlevel 1 exit /b 1
+if exist "%CD%\.contextor_py315_cutover.guard" (
+    echo CONTEXTOR_CUTOVER_ACTIVE
+    exit /b 86
+)
+endlocal
 setlocal enabledelayedexpansion
 
 title GUI Test Suite Environment Installer
@@ -15,9 +23,9 @@ echo [INFO] Working directory set to: %CD%
 echo.
 
 :: =======================================================
-:: 1/5: Searching for Python interpreter
+:: 1/4: Searching for Python interpreter
 :: =======================================================
-echo [1/5] Searching for Python interpreter...
+echo [1/4] Searching for Python interpreter...
 
 set "PYTHON_EXE="
 set "VENV_PY=%CD%\.venv\Scripts\python.exe"
@@ -28,13 +36,14 @@ if exist "%VENV_PY%" (
     goto :PYTHON_FOUND
 )
 
-:: 2. Create the project virtual environment with an available base Python.
+:: 2. Create the project virtual environment with validated CPython 3.15.
 set "BOOTSTRAP_PY="
-if exist "C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" (
-    set "BOOTSTRAP_PY=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe"
+if exist "C:\Python315\python.exe" (
+    "C:\Python315\python.exe" -I -B -c "import sys; sys.exit(0 if sys.implementation.name == 'cpython' and sys.version_info[:2] == (3, 15) else 1)" >nul 2>&1
+    if not errorlevel 1 set "BOOTSTRAP_PY=C:\Python315\python.exe"
 )
 if not defined BOOTSTRAP_PY (
-    python --version >nul 2>&1
+    python -I -B -c "import sys; sys.exit(0 if sys.implementation.name == 'cpython' and sys.version_info[:2] == (3, 15) else 1)" >nul 2>&1
     if not errorlevel 1 set "BOOTSTRAP_PY=python"
 )
 if not defined BOOTSTRAP_PY goto :PYTHON_FOUND
@@ -50,8 +59,7 @@ if exist "%VENV_PY%" set "PYTHON_EXE=%VENV_PY%"
 
 :PYTHON_FOUND
 if "%PYTHON_EXE%"=="" (
-    echo [ERROR] Python interpreter not found in system PATH or standard directories.
-    echo Please install Python 3.9+ or set up WinPython.
+    echo [ERROR] A project .venv or validated CPython 3.15 is required.
     pause
     exit /b 1
 )
@@ -60,9 +68,9 @@ echo [INFO] Python interpreter found: "%PYTHON_EXE%"
 echo.
 
 :: =======================================================
-:: 2/5: Checking setuptools version
+:: 2/4: Checking setuptools version
 :: =======================================================
-echo [2/5] Checking setuptools version...
+echo [2/4] Checking setuptools version...
 
 set "INSTALLED_VER="
 "%PYTHON_EXE%" -c "import importlib.metadata; print(importlib.metadata.version('setuptools'))" > "%TEMP%\st_ver.tmp" 2>nul
@@ -112,9 +120,9 @@ if "!INSTALLED_VER!"=="" (
 echo.
 
 :: =======================================================
-:: 3/5: Checking pytest
+:: 3/4: Checking pytest
 :: =======================================================
-echo [3/5] Checking pytest installation...
+echo [3/4] Checking pytest installation...
 
 set "PYTEST_INSTALLED="
 "%PYTHON_EXE%" -c "import importlib.util; print('YES') if importlib.util.find_spec('pytest') else print('')" > "%TEMP%\pytest_check.tmp" 2>nul
@@ -147,9 +155,9 @@ if "!PYTEST_INSTALLED!"=="" (
 echo.
 
 :: =======================================================
-:: 4/5: Checking project dependencies (requirements.txt / orjson)
+:: 4/4: Checking project dependencies (requirements.txt / orjson)
 :: =======================================================
-echo [4/5] Checking project dependencies...
+echo [4/4] Checking project dependencies...
 
 if exist "Requirements.txt" set "REQ_FILE=Requirements.txt"
 if exist "requirements.txt" set "REQ_FILE=requirements.txt"
@@ -175,20 +183,6 @@ if defined REQ_FILE (
 
 echo.
 
-:: =======================================================
-:: 5/5: Installing editable dev environment (e DEV)
-:: =======================================================
-echo [5/5] Installing editable dev environment...
-
-echo [INFO] Running pip install -e .[dev] in the script directory...
-"%PYTHON_EXE%" -m pip install -e ".[dev]"
-if errorlevel 1 (
-    echo [ERROR] Failed to install editable dev environment.
-    pause
-    exit /b 1
-)
-echo [SUCCESS] Editable dev environment installed.
-
 echo.
 echo =======================================================
 echo        Environment Check Completed Successfully
diff --git a/MCP_installer.bat b/MCP_installer.bat
index 530e904..33d4681 100644
--- a/MCP_installer.bat
+++ b/MCP_installer.bat
@@ -1,4 +1,12 @@
 @echo off
+setlocal DisableDelayedExpansion
+cd /d "%~dp0"
+if errorlevel 1 exit /b 1
+if exist "%CD%\.contextor_py315_cutover.guard" (
+    echo CONTEXTOR_CUTOVER_ACTIVE
+    exit /b 86
+)
+endlocal
 setlocal enabledelayedexpansion
 
 title Contextor MCP Server Environment Installer
@@ -15,41 +23,15 @@ echo [INFO] Working directory set to: %CD%
 echo.
 
 :: =======================================================
-:: 1/3: Searching for Python interpreter
+:: 1/2: Selecting the project-local interpreter
 :: =======================================================
-echo [1/3] Searching for Python interpreter...
+echo [1/2] Selecting the project-local interpreter...
 
-set "PYTHON_EXE="
-
-:: 1. Check embedded WinPython / SpiralProphet path
-if exist "C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" (
-    set "PYTHON_EXE=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe"
-    goto :PYTHON_FOUND
-)
-
-:: 2. Check system PATH
-python --version >nul 2>&1
-if not errorlevel 1 (
-    set "PYTHON_EXE=python"
-    goto :PYTHON_FOUND
-)
-
-:: 3. Scan local directories (venv, .venv, WinPython)
-for /d %%d in (venv .venv Python python WPy64*) do (
-    if exist "%%d\Scripts\python.exe" (
-        set "PYTHON_EXE=%%d\Scripts\python.exe"
-        goto :PYTHON_FOUND
-    )
-    if exist "%%d\python.exe" (
-        set "PYTHON_EXE=%%d\python.exe"
-        goto :PYTHON_FOUND
-    )
-)
+set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
 
 :PYTHON_FOUND
-if "%PYTHON_EXE%"=="" (
-    echo [ERROR] Python interpreter not found in system PATH or standard directories.
-    echo Please install Python 3.10+ or set up WinPython.
+if not exist "%PYTHON_EXE%" (
+    echo [ERROR] The local Contextor .venv must be created explicitly before running this installer.
     pause
     exit /b 1
 )
@@ -58,9 +40,9 @@ echo [INFO] Python interpreter found: "%PYTHON_EXE%"
 echo.
 
 :: =======================================================
-:: 2/3: Checking mcp version
+:: 2/2: Checking mcp version
 :: =======================================================
-echo [2/3] Checking mcp version...
+echo [2/2] Checking mcp version...
 
 set "INSTALLED_VER="
 "%PYTHON_EXE%" -c "import importlib.metadata; print(importlib.metadata.version('mcp'))" > "%TEMP%\mcp_ver.tmp" 2>nul
@@ -106,20 +88,6 @@ if "!INSTALLED_VER!"=="" (
 )
 echo.
 
-:: =======================================================
-:: 3/3: Reinstalling Contextor in editable mode
-:: =======================================================
-echo [3/3] Linking contextor-mcp script...
-echo.
-set /p "link_choice=Do you want to run pip install -e . to link the new contextor-mcp script? (Y/N): "
-if /i "!link_choice!"=="Y" (
-    "%PYTHON_EXE%" -m pip install -e .
-    echo [SUCCESS] Linked successfully.
-) else (
-    echo [INFO] Skipping linking.
-)
-echo.
-
 echo =======================================================
 echo        Installation Complete
 echo =======================================================
diff --git a/run_contextor.bat b/run_contextor.bat
index d8b2e28..9df2cdc 100644
--- a/run_contextor.bat
+++ b/run_contextor.bat
@@ -18,6 +18,7 @@ cd /d "%~dp0"
 if errorlevel 1 goto no_project_dir
 
 set "PROJECT_DIR=%CD%"
+if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
 set "VENV_DIR=%PROJECT_DIR%\.venv"
 set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
 
@@ -26,35 +27,27 @@ goto check_deps
 
 
 :create_venv
+if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
 echo [INFO] Creating virtual environment ^(.venv^)...
 
 set "PYTHON_EXE="
 
-:: 1. Check embedded WinPython / SpiralProphet path
-if exist "C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" (
-    set "PYTHON_EXE=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe"
-    goto :PYTHON_FOUND
+:: 1. Check the explicit CPython 3.15 installation.
+if exist "C:\Python315\python.exe" (
+    "C:\Python315\python.exe" -I -B -c "import sys; sys.exit(0 if sys.implementation.name == 'cpython' and sys.version_info[:2] == (3, 15) else 1)" >nul 2>&1
+    if not errorlevel 1 (
+        set "PYTHON_EXE=C:\Python315\python.exe"
+        goto :PYTHON_FOUND
+    )
 )
 
-:: 2. Check system PATH
-python --version >nul 2>&1
+:: 2. Accept PATH Python only after the same interpreter validation.
+python -I -B -c "import sys; sys.exit(0 if sys.implementation.name == 'cpython' and sys.version_info[:2] == (3, 15) else 1)" >nul 2>&1
 if not errorlevel 1 (
     set "PYTHON_EXE=python"
     goto :PYTHON_FOUND
 )
 
-:: 3. Scan local directories (venv, .venv, WinPython)
-for /d %%d in (venv .venv Python python WPy64*) do (
-    if exist "%%d\Scripts\python.exe" (
-        set "PYTHON_EXE=%%d\Scripts\python.exe"
-        goto :PYTHON_FOUND
-    )
-    if exist "%%d\python.exe" (
-        set "PYTHON_EXE=%%d\python.exe"
-        goto :PYTHON_FOUND
-    )
-)
-
 :PYTHON_FOUND
 if "%PYTHON_EXE%"=="" (
     goto no_python
@@ -71,6 +64,7 @@ echo.
 
 
 :check_deps
+if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
 echo Checking dependencies...
 
 "%VENV_PY%" -c "import orjson, watchdog, mcp, fastmcp" >nul 2>&1
@@ -81,6 +75,7 @@ goto check_backend_autostart
 
 
 :install_deps
+if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
 echo [WARNING] Required dependencies are missing.
 echo Installing project requirements...
 
@@ -97,6 +92,7 @@ goto check_backend_autostart
 
 
 :check_backend_autostart
+if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
 echo Checking MCP backend autostart...
 
 "%VENV_PY%" -m contextor.mcp_backend_autostart status >nul 2>&1
@@ -107,6 +103,7 @@ goto check_backend
 
 
 :install_backend_autostart
+if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
 echo [INFO] Registering MCP backend autostart...
 
 "%VENV_PY%" -m contextor.mcp_backend_autostart install >nul 2>&1
@@ -117,6 +114,7 @@ goto check_backend
 
 
 :check_backend
+if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
 echo Checking MCP backend...
 
 "%VENV_PY%" -m contextor backend status >nul 2>&1
@@ -127,6 +125,7 @@ goto start_gui
 
 
 :start_backend
+if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
 echo [INFO] Starting MCP backend...
 
 "%VENV_PY%" -m contextor backend start >nul 2>&1
@@ -137,6 +136,7 @@ goto start_gui
 
 
 :start_gui
+if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
 echo.
 echo Starting Contextor GUI...
 echo.
@@ -150,6 +150,11 @@ if errorlevel 1 goto gui_failed
 exit /b 0
 
 
+:cutover_blocked
+echo CONTEXTOR_CUTOVER_ACTIVE
+exit /b 86
+
+
 :no_project_dir
 echo [ERROR] Could not enter the project directory:
 echo         %~dp0
@@ -158,8 +163,7 @@ exit /b 1
 
 
 :no_python
-echo [ERROR] Python was not found.
-echo Install Python 3.10+ and add it to your system PATH.
+echo [ERROR] CPython 3.15 was not found or did not pass validation.
 pause
 exit /b 1
 
@@ -203,4 +207,4 @@ exit /b 1
 echo.
 echo [ERROR] Contextor exited with an error.
 pause
-exit /b 1
\ No newline at end of file
+exit /b 1
```

Complete actual new-file diff:

```diff
diff --git a/tests/test_py315_launcher_migration_guard.py b/tests/test_py315_launcher_migration_guard.py
new file mode 100644
index 0000000..d91f082
--- /dev/null
+++ b/tests/test_py315_launcher_migration_guard.py
@@ -0,0 +1,81 @@
+"""Windows launcher contracts for the Python 3.15 migration guard."""
+
+import os
+import subprocess
+import sys
+from pathlib import Path
+
+import pytest
+
+
+ROOT = Path(__file__).resolve().parents[1]
+LAUNCHERS = (
+    "run_contextor.bat",
+    "GUI_test_suite_installer.bat",
+    "MCP_installer.bat",
+)
+GUARD = ".contextor_py315_cutover.guard"
+
+
+@pytest.mark.skipif(sys.platform != "win32", reason="Windows BAT contract")
+@pytest.mark.parametrize("launcher", LAUNCHERS)
+@pytest.mark.parametrize("bang_path", (False, True))
+def test_guarded_launcher_exits_before_application_work(tmp_path, launcher, bang_path):
+    checkout = tmp_path / ("checkout!bang" if bang_path else "checkout")
+    checkout.mkdir()
+    script = checkout / launcher
+    script.write_bytes((ROOT / launcher).read_bytes())
+    (checkout / GUARD).touch()
+    marker = checkout / "application_started.txt"
+    (checkout / "main.py").write_text(
+        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n",
+        encoding="utf-8",
+    )
+
+    result = subprocess.run(
+        ["cmd.exe", "/D", "/C", str(script)],
+        cwd=checkout,
+        env=os.environ.copy(),
+        capture_output=True,
+        text=True,
+        timeout=15,
+        check=False,
+    )
+
+    assert result.returncode == 86
+    assert "CONTEXTOR_CUTOVER_ACTIVE" in result.stdout
+    assert not (checkout / ".venv").exists()
+    assert not marker.exists()
+
+
+def test_installers_do_not_install_editable_distribution():
+    for name in ("GUI_test_suite_installer.bat", "MCP_installer.bat"):
+        source = (ROOT / name).read_text(encoding="utf-8").lower()
+        assert "pip install -e" not in source
+
+
+def test_launchers_have_no_hardcoded_python_310_fallback():
+    for name in LAUNCHERS:
+        source = (ROOT / name).read_text(encoding="utf-8").lower()
+        assert "c:\\spiralprophet\\python\\wpy64-31090" not in source
+
+
+@pytest.mark.parametrize(
+    "name", ("run_contextor.bat", "GUI_test_suite_installer.bat")
+)
+def test_venv_bootstrap_requires_validated_cpython_315(name):
+    source = (ROOT / name).read_text(encoding="utf-8").lower()
+    assert "c:\\python315\\python.exe" in source
+    assert "python -i -b -c" in source
+    assert "sys.implementation.name == 'cpython'" in source
+    assert "sys.version_info[:2] == (3, 15)" in source
+    assert "python --version" not in source
+    assert "for /d %%d" not in source
+
+
+def test_mcp_installer_uses_only_project_local_venv():
+    source = (ROOT / "MCP_installer.bat").read_text(encoding="utf-8").lower()
+    assert 'set "python_exe=%cd%\\.venv\\scripts\\python.exe"' in source
+    assert 'if not exist "%python_exe%"' in source
+    assert "python --version" not in source
+    assert "for /d %%d" not in source
```

## REMAINING_UNKNOWN

Guard behavior at every already-entered operation boundary was verified by source; the tests exercised guarded entry only. No unguarded bootstrap, installer, Desktop, MCP, autostart, dependency installation, production cutover or rollback was executed. A guard introduced between an already-started external process call and the next label cannot retroactively stop that call; future cutover must verify process ownership separately.

## FINAL_VERDICT

`PASS_PY315_M6B_LAUNCHERS_GUARDED`. All specified scoped edits and both cross-version targeted gates passed; Contextor indexed the new test at verified revision 961. STOP.


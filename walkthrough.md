# C16-B03-P1D3-P13B — CPython 3.15 package and Ruff metadata

## HEAD_BEFORE_AFTER

- DIRECT_EVIDENCE: HEAD before/after `1eedda847f75e6a40f1b62b6af27567a84b76590`; no Git mutation. Preflight worktree already contained uncommitted P13A test and `walkthrough.md`; both were preserved. Repository `.venv` identified as CPython 3.15.2 / `cpython`. P13A `_require_cpython315` and native runtime gate were present.
- Contextor MCP first: canonical revision 1121, state_id `20261106_195021`, repo_id `ctx_8efc50d8`, canonical_state=fresh, workspace_sync=verified, LIVE provenance, graph/cycles fresh, cycle_semantics stale, structural DFS cycles=16, active warnings=16, model_pass_count=0.
- Target test pre-edit SHA-256 `58cd1c0f7fbd2930e0879361de85e03ad61a9f47fe16fb300d9bbd5660430e67` matched FileState. `pyproject.toml` is not indexed in Python FileState; its pre-edit disk hash was `7068a9178ea269bd616b42550ab4b1157f9e26509eabd8a23f66fbfcf124c232`.

## FILES_CHANGED

- `pyproject.toml`
- `tests/test_py315_launcher_migration_guard.py`
- `walkthrough.md` (report, excluded from its own diff)
- The pre-existing P13A test modification remains in the worktree and is outside this task's changed files.

## PYTHON_DISTRIBUTION_CONTRACT

- Literal project metadata edit: `requires-python = ">=3.15,<3.16"`. This restricts Contextor's own package distribution runtime; it does not change the interpreter semantics of repositories Contextor analyzes. Project version, runtime dependencies and build backend were unchanged.

## RUFF_PY315_CONTRACT

- Literal optional dev dependency edit: `ruff>=0.17.0`; literal Ruff target: `py315`. Other Ruff rules unchanged. Ruff was absent from repository `.venv` and PATH (`RUFF_NOT_INSTALLED_IN_VENV`, `RUFF_NOT_ON_PATH`), so parser recognition by an installed Ruff is **TOOL_NOT_VERIFIED**. No install or upgrade was attempted.

## PACKAGE_METADATA_VALIDATION

- Exact requested isolated CPython command parsed TOML successfully and printed `>=3.15,<3.16 py315`.
- New test `test_py315_project_metadata_and_ruff_contract` checks distribution version, Ruff target, Ruff dev dependency and retained `pytest>=7.4`. Existing assertions were unchanged.

## TARGETED_TEST_RESULTS

- Exact four-module command: **80 passed, 0 failed, 0 skipped, 2 dependency deprecation warnings** in 14.72s. Warnings originated in installed FastMCP/Authlib, not changed code. Repository interpreter was CPython 3.15.2.
- `git diff --check` was first run while the preceding D13 `walkthrough.md` was still present; it flagged trailing whitespace in that old report only. The current P13B report replaces that file. After replacing the old report and removing blank diff-context markers that would appear as trailing whitespace inside this report, the final `git diff --check` exited 0.

## ANALYZED_SOURCE_SEMANTICS_UNCHANGED

- No changes to `package_model.py`, `namespace_bound_model.py`, parser/indexer, fingerprints, cycle topology, warning suppression, LIVE/MCP code or process ownership. The metadata constraint applies to the package executing Contextor. The existing model's explicit analyzed-source target-version checks remain separate.

## MCP_POST_CHANGE_AUDIT

- MCP target test context after change: revision **1122**, state_id `20261106_195021`, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, LIVE provenance, graph/cycles fresh, cycle_semantics stale, syntax_errors=0, structural DFS cycles=16, active_warning_count=16, model_pass_count=0.
- Changed test SHA-256 `859d478c5aab93d5b6110e1e78ad2e70a49ea415c393467c7f522a04fb9df5c6` exactly matches FileState. `pyproject.toml` disk SHA-256 `b550874cd1915cc48975246c8e98aba6393cfbd0887202b001b3d0a3c9fed6d4`; it has no Python FileState entry. TOML parsing and exact metadata test verify its content.
- No FULL, update_file, backend restart, dependency installation, interpreter switch, commit/push/reset, warning-policy change or MODEL_PASS promotion.

## REMAINING_UNKNOWN

- Installed Ruff configuration recognition remains TOOL_NOT_VERIFIED because Ruff is absent. Active backend/Desktop loaded-code adoption was not assessed. Canonical cycle_semantics remains stale.

## FULL_DIFFS

Complete actual diffs of the two task-modified files follow. `walkthrough.md` excluded from its own diff; pre-existing P13A diff excluded from P13B task diff.
diff --git a/pyproject.toml b/pyproject.toml
index 7e772d0..72e8506 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -3,7 +3,7 @@ name = "contextor"
 version = "1.1.0b0"
 description = "Static architectural analysis turning Python repositories into LLM-ready context."
 readme = "README.md"
-requires-python = ">=3.10"
+requires-python = ">=3.15,<3.16"
 license = { file = "LICENSE" }
 dependencies = [
     "orjson>=3.9",
@@ -15,7 +15,7 @@ dependencies = [
 [project.optional-dependencies]
 dev = [
     "pytest>=7.4",
-    "ruff>=0.5",
+    "ruff>=0.17.0",
 ]

 [project.scripts]
@@ -41,7 +41,7 @@ markers = [

 [tool.ruff]
 line-length = 100
-target-version = "py310"
+target-version = "py315"

 [tool.ruff.lint]
 select = ["E", "F", "W", "I", "UP", "B"]
diff --git a/tests/test_py315_launcher_migration_guard.py b/tests/test_py315_launcher_migration_guard.py
index d91f082..01ca57b 100644
--- a/tests/test_py315_launcher_migration_guard.py
+++ b/tests/test_py315_launcher_migration_guard.py
@@ -3,6 +3,7 @@
 import os
 import subprocess
 import sys
+import tomllib
 from pathlib import Path

 import pytest
@@ -79,3 +80,29 @@ def test_mcp_installer_uses_only_project_local_venv():
     assert 'if not exist "%python_exe%"' in source
     assert "python --version" not in source
     assert "for /d %%d" not in source
+
+
+def test_py315_project_metadata_and_ruff_contract():
+    config = tomllib.loads(
+        (ROOT / "pyproject.toml").read_text(
+            encoding="utf-8"
+        )
+    )
+
+    assert (
+        config["project"]["requires-python"]
+        == ">=3.15,<3.16"
+    )
+    assert (
+        config["tool"]["ruff"]["target-version"]
+        == "py315"
+    )
+    assert (
+        "ruff>=0.17.0"
+        in config["project"]["optional-dependencies"]["dev"]
+    )
+
+    assert (
+        "pytest>=7.4"
+        in config["project"]["optional-dependencies"]["dev"]
+    )

## FINAL_VERDICT

PASS

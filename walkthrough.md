# CONTEXTOR C16-B03-P1D3-P14-R18 — exact fix

## PREFLIGHT

- Contextor MCP before edit: LIVE canonical revision 1124, canonical_state=fresh, graph/cycles/cycle_semantics=fresh, 2 cyclic SCCs and 16 structural DFS paths. The three target module contexts (`contextor.ui.gui`, `contextor.repo_generator.__init__`, `contextor.repo_generator.main`) each reported workspace_sync=verified and revision 1124. Read-only snapshot metadata: state_id `20261108_132120`, repo_id `ctx_8efc50d8`, root `C:\Temp\Contextor_Repo`.
- Git HEAD before/after `38dcc9b3eb7c0aa31c3f94aefdcbe6c566199e4c`; before edit only D17 `walkthrough.md` was modified. Repository interpreter CPython 3.15.2.
- Exact anchors matched at `contextor/ui/gui.py:43,383-390`, `contextor/repo_generator/__init__.py:1`, `contextor/repo_generator/main.py:522`. `rg` found no direct consumer or monkeypatch of module-level `contextor.ui.gui.run_repo_generator`; only its original import and use within `open_repo_builder`. No compatibility change was added.

## EXACT_PRODUCTION_DIFF

- Removed the eager `from contextor.repo_generator import run_repo_generator` in `contextor/ui/gui.py` and placed precisely the same import in the `else` branch of `ContextorGUI.open_repo_builder`, immediately before the call. No other production file changed.

## EXACT_TEST_DIFFS

- Renamed the one real-source C26 test and replaced only its final assertions with `UNKNOWN`, `IMPORT_HOP_NOT_UNIQUELY_PROVED`, and `UNKNOWN_NOT_EVALUATED`. Synthetic positive C26/C28 fixtures were not changed.
- Added the auditor-specified `tests/test_cycle_semantics_scc2_import_order_regression.py` verbatim: two independent `-I -B` import-order subprocess cases with public export assertions, plus a source AST assertion that the GUI import is method scoped.

## TARGETED_TEST_RESULTS

- Command: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -B -m pytest -q -rs tests/test_cycle_semantics_scc2_import_order_regression.py tests/test_cycle_semantics_conditional_export.py tests/test_cycle_semantics_conditional_discovery.py` with `PYTHONDONTWRITEBYTECODE=1`.
- Result: **30 passed in 27.83s**, 0 failures. No full suite.

## TWO_FRESH_IMPORT_ORDERS

- The new regression ran `contextor.repo_generator` and `contextor.ui` in distinct fresh CPython 3.15 subprocesses. Both passed with returncode 0 under the targeted test. D17 had observed the former fail at `contextor/ui/gui.py:43` before this patch.

## PUBLIC_EXPORT_PARITY

- Each fresh child additionally imported `run_repo_generator` from `contextor.repo_generator` and `run` from `contextor.ui` and asserted both callable. Both parametrized cases passed. Package initializer exports and provider definition were not edited.

## MCP_POST_CHANGE_AUDIT

- Watcher incorporated the edits into LIVE revision **1127**. Target `get_module_context(contextor.ui.gui)` now reports canonical_state=fresh, workspace_sync=verified, graph/cycles=fresh, and the `contextor.repo_generator.__init__` outbound hard dependency retained. Canonical snapshot metadata and FileState are revision 1127, state_id `20261108_132120`, baseline trusted.
- `cycle_semantics` is **stale**, invalidation reason `SOURCE_CHANGED`; MCP's current semantic diagnostic reports the same and does not expose fresh lexical activation. No FULL or update_file was used to force regeneration.
- Direct read-only replay of the existing `analyze_cyclic_import_sites` and `analyze_cycle_activation_view` on current canonical hard_edges and 53 FileState-matching SCC sources found the GUI→repo_generator edge at `gui.py:389:12`, match kind `FROM_BASE`, activation `FUNCTION_SCOPED`, guarded by the `else` branch of the builder-window check at line 385. It found no `MODULE_TOP_LEVEL` site for that edge. Existing `discover_conditional_reexports` replay returned 0 candidates and complete bounded selection. These are current source/graph diagnostic replays, **not** a fresh published canonical cycle_semantics family.
- Current MCP architecture: canonical revision 1127, syntax errors 0, structural DFS paths 16, cycle_semantics stale. Name-collision count 17 was observed (preflight 16); no collision diagnosis or unrelated change was made under this exact task.

## STRUCTURAL_CYCLE_PARITY

- Current canonical graph replay: SCC1 44 members/110 internal hard edges, SCC2 9 members/16 internal hard edges. MCP current DFS structural path count remains **16** and graph/cycles are fresh. The GUI→repo_generator hard edge is still present. Structural topology was not intentionally changed.

## LEXICAL_ACTIVATION_BEFORE_AFTER

- Before: canonical revision 1124 `gui.py:43:0`, `MODULE_TOP_LEVEL`, `FROM_BASE`; D16 conditional group had 3 eager return witnesses.
- After: current FileState-bound read-only replay at revision 1127 `gui.py:389:12`, `FUNCTION_SCOPED`, `FROM_BASE`, `IF/ELSE` guard at line 385; zero eager conditional candidates in replay. The canonical published semantic family remains stale, so authoritative post-change lexical activation cannot be certified.

## SOURCE_HASH_PARITY

- Current disk = FileState SHA-256: `contextor/ui/gui.py` `9e0a9319e140f682c4e66d232d1d6fc89c48a03a8234a800f6a413191c347315`; `tests/test_cycle_semantics_conditional_export.py` `012aa20b9aac3d3b43c8e762f846eb12873f145f53a00183b280bcc90ae7d07b`; `tests/test_cycle_semantics_scc2_import_order_regression.py` `5c950696599f1628161ae6d8cdeb6de4525eacfd74da5602853ee344b26d2b7c`. All 53 selected SCC sources matched current FileState for the read-only replay. MCP target workspace_sync=verified; untargeted architecture workspace_sync=unverified by contract.

## FILES_CHANGED

- `contextor/ui/gui.py`
- `tests/test_cycle_semantics_conditional_export.py`
- `tests/test_cycle_semantics_scc2_import_order_regression.py`
- `walkthrough.md` (report only)

## FULL_DIFFS

Actual complete source/test diffs follow. `walkthrough.md` is excluded from its own diff.

```diff
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index f855fad..e6f95e0 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -40,7 +40,6 @@ from contextor.core.repository_identity import (
     read_repository_identity,
 )
 from contextor.core.paths import prune_startup_caches
-from contextor.repo_generator import run_repo_generator
 from contextor.mcp_backend_control import (
     BackendOwnerAlreadyClaimed,
     BackendOwnerInstanceRevoked,
@@ -387,6 +386,7 @@ class ContextorGUI:
             self.repo_builder_win.lift()
             self.repo_builder_win.focus_force()
         else:
+            from contextor.repo_generator import run_repo_generator
             self.repo_builder_win = run_repo_generator(parent=self.root)

     def open_parser_window(self):
diff --git a/tests/test_cycle_semantics_conditional_export.py b/tests/test_cycle_semantics_conditional_export.py
index 9914399..6690d40 100644
--- a/tests/test_cycle_semantics_conditional_export.py
+++ b/tests/test_cycle_semantics_conditional_export.py
@@ -146,7 +146,7 @@ def test_c26_closing_symbol_mismatch_unknown():
     assert _analyze(sources).status == "UNKNOWN"


-def test_c26_real_contextor_sources_without_import():
+def test_c26_real_contextor_chain_has_no_eager_return_hop():
     root = (
         Path(__file__).resolve().parents[1]
         / "contextor"
@@ -187,14 +187,9 @@ def test_c26_real_contextor_sources_without_import():
         "run_repo_generator",
     )

-    assert result.status == (
-        "CONDITIONAL_DELAYED_REEXPORT"
-    )
-    assert result.provider_definition_line > (
-        result.hops[1].line
-    )
-    assert result.prefix_execution_status == (
-        "UNVERIFIED_TRANSITIVE_PREFIX"
+    assert result.status == "UNKNOWN"
+    assert result.reason == (
+        "IMPORT_HOP_NOT_UNIQUELY_PROVED"
     )
     assert result.runtime_execution_status == (
         "UNKNOWN_NOT_EVALUATED"
diff --git a/tests/test_cycle_semantics_scc2_import_order_regression.py b/tests/test_cycle_semantics_scc2_import_order_regression.py
new file mode 100644
index 0000000..5ea9f98
--- /dev/null
+++ b/tests/test_cycle_semantics_scc2_import_order_regression.py
@@ -0,0 +1,138 @@
+from __future__ import annotations
+
+import ast
+import json
+import subprocess
+import sys
+from pathlib import Path
+
+import pytest
+
+
+ROOT = Path(__file__).resolve().parents[1]
+
+CHILD_CODE = r"""
+import importlib
+import json
+import sys
+import traceback
+
+entry = sys.argv[1]
+root = sys.argv[2]
+sys.path.insert(0, root)
+
+try:
+    importlib.import_module(entry)
+
+    from contextor.repo_generator import run_repo_generator
+    from contextor.ui import run
+
+    if not callable(run_repo_generator):
+        raise AssertionError("Generator export is not callable")
+
+    if not callable(run):
+        raise AssertionError("UI export is not callable")
+
+except BaseException as exc:
+    print(json.dumps({
+        "entry": entry,
+        "status": "EXCEPTION",
+        "exception_type": type(exc).__name__,
+        "exception_message": str(exc),
+        "traceback": traceback.format_exc(),
+    }, ensure_ascii=False))
+    sys.exit(1)
+
+print(json.dumps({
+    "entry": entry,
+    "status": "PASS",
+    "generator_export": True,
+    "ui_export": True,
+}, ensure_ascii=False))
+"""
+
+
+@pytest.mark.parametrize(
+    "entry",
+    (
+        "contextor.repo_generator",
+        "contextor.ui",
+    ),
+)
+def test_scc2_fresh_import_order(entry):
+    completed = subprocess.run(
+        [
+            sys.executable,
+            "-I",
+            "-B",
+            "-c",
+            CHILD_CODE,
+            entry,
+            str(ROOT),
+        ],
+        cwd=str(ROOT),
+        capture_output=True,
+        text=True,
+        encoding="utf-8",
+        errors="replace",
+        timeout=45,
+        check=False,
+    )
+
+    assert completed.returncode == 0, (
+        f"entry={entry}\n"
+        f"stdout={completed.stdout}\n"
+        f"stderr={completed.stderr}"
+    )
+
+    result = json.loads(completed.stdout.strip())
+
+    assert result == {
+        "entry": entry,
+        "status": "PASS",
+        "generator_export": True,
+        "ui_export": True,
+    }
+
+
+def test_scc2_gui_generator_import_remains_method_scoped():
+    path = ROOT / "contextor" / "ui" / "gui.py"
+    tree = ast.parse(path.read_text(encoding="utf-8"))
+
+    def matching_import(node):
+        return (
+            isinstance(node, ast.ImportFrom)
+            and node.module == "contextor.repo_generator"
+            and any(
+                alias.name == "run_repo_generator"
+                for alias in node.names
+            )
+        )
+
+    assert not any(
+        matching_import(node)
+        for node in tree.body
+    )
+
+    classes = [
+        node
+        for node in tree.body
+        if isinstance(node, ast.ClassDef)
+        and node.name == "ContextorGUI"
+    ]
+    assert len(classes) == 1
+
+    methods = [
+        node
+        for node in classes[0].body
+        if isinstance(node, ast.FunctionDef)
+        and node.name == "open_repo_builder"
+    ]
+    assert len(methods) == 1
+
+    imports = [
+        node
+        for node in ast.walk(methods[0])
+        if matching_import(node)
+    ]
+    assert len(imports) == 1
```

## FINAL_VERDICT

**BLOCKED** — the literal fix, both fresh-import orders, and all 30 targeted tests pass; the current canonical graph retains the hard edge and 16 paths. The mandatory authoritative lexical-activation audit cannot meet the PASS gate while the published `cycle_semantics` family is stale (`SOURCE_CHANGED`). The current source/graph replay is explicitly distinguished from canonical semantic freshness. No FULL, update_file or restart was performed.

# CONTEXTOR_B0G4C9_SCC02_SOURCE_ANCHORED_ENTRY_ORDER_REGRESSIONS

## HEAD_BEFORE
4a73254c2622da89b1a7244aebff8b7863d2b544

## HEAD_AFTER
4a73254c2622da89b1a7244aebff8b7863d2b544

## GIT_STATUS
Before: clean. After: M walkthrough.md and ?? tests/test_cycle_semantics_scc02_entry_order.py. walkthrough.md is the requested report artifact.

## LIVE_REVISION_BEFORE
434; activity_epoch=1beab26da2ff4932852caa7db6ff4242; resync_required=false. Canonical graph, cycles and collisions fresh. Collisions=0; reported structural cycle paths=16.

## LIVE_REVISION_AFTER
435; same activity_epoch; resync_required=false; continuous event feed. DIRECT_EVIDENCE: desktop_watcher UPDATED tests/test_cycle_semantics_scc02_entry_order.py at revision 435. Contextor module context: canonical_state=fresh, workspace_sync=verified, graph/cycles/collisions fresh; one hard dependency to contextor.core.cycle_semantics.package_model.

## FILES_CHANGED
- tests/test_cycle_semantics_scc02_entry_order.py (new)
walkthrough.md is the report artifact. No production source or existing test changed.

## SOURCE_CHAIN_ANCHORS
DIRECT_EVIDENCE from Contextor source ranges, all at revision 434 and workspace_sync=verified:
- contextor/repo_generator/__init__.py:1 imports run_repo_generator from main; line 3 exports it in __all__.
- contextor/repo_generator/main.py:8 imports FilterWindow from filters; run_repo_generator definition begins at line 522.
- contextor/repo_generator/filters.py:5 imports theme from contextor.ui; FilterWindow class begins at line 10.
- contextor/ui/__init__.py:5 imports run from .gui; line 7 exports it in __all__.
- contextor/ui/gui.py:43 imports run_repo_generator from contextor.repo_generator; run definition begins at line 2283.
The new test's AST source anchors and ordering assertions passed. No source drift was found.

## REEXPORT_BINDING_ORDER_EVIDENCE
CODE_PATH_PROVED: The real package initializers use from-import reexports. Their requested members are defined later in the nested main/gui modules. The new tests assert import statements precede run_repo_generator, FilterWindow and run definitions. This establishes the lexical ordering condition; actual real-GUI import execution was not tested.

## SYNTHETIC_PROJECTION_SCOPE
The test uses a seven-module restricted source map with the same five import-chain anchors, a synthetic contextor root and theme module. The model receives only parsed synthetic ASTs. Fresh CPython subprocesses use -I -B with a temporary synthetic package tree; they do not import real Contextor GUI/repo-generator modules. The fixture is a restricted semantic projection, not a full production import simulator.

## REPO_GENERATOR_FIRST_RESULT
DIRECT_EVIDENCE: The restricted model returned EARLY_BINDING_HAZARD targeting contextor.repo_generator.run_repo_generator before its main-module DEFINE_FUNCTION event. The corresponding fresh CPython synthetic import had a nonzero exit status, as asserted by the passing parameterized test. No production traceback is claimed.

## UI_FIRST_RESULT
DIRECT_EVIDENCE: The restricted model returned MODEL_PASS and READY events ordered main -> repo_generator package -> ui.gui. The corresponding fresh CPython synthetic import exited zero, as asserted by the passing parameterized test.

## FRESH_PROCESS_CPYTHON_COMPARISON
Two isolated synthetic entry cases ran via sys.executable -I -B -c. The tests compare only returncode success/failure, not a manufactured traceback or actual GUI outcome. Both cases passed.

## SAME_GRAPH_DIFFERENT_BINDING_OUTCOME
CODE_PATH_PROVED: The prebinding fixture prepends an early run_repo_generator definition to the synthetic package initializer. The test asserts AST import declarations are unchanged, then observes EARLY_BINDING_HAZARD -> MODEL_PASS and a successful synthetic CPython process. No production source was changed.

## TEST_COMMAND
Baseline:
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_edge_sites.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py

Post-change:
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_scc02_entry_order.py tests/test_cycle_semantics_edge_sites.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py

## TEST_RESULTS
DIRECT_EVIDENCE: baseline 204 passed in 13.58s; post-change 212 passed in 13.77s. Eight new test cases passed. Full pytest suite was not run.

## CANONICAL_FRESHNESS
Before and after canonical graph, topology, cycles, collisions and lineage were fresh; source files for the SCC02 chain and package_model were workspace_sync=verified before change. New test file was workspace_sync=verified after watcher update. No forced resync or direct publication occurred.

## COLLISION_COUNT_BEFORE_AFTER
0 -> 0, fresh.

## STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER
16 -> 16 reported paths, fresh.

## NO_REAL_GUI_EXECUTION
The test parses actual source but imports only package_model in the parent test process; subprocesses import only generated synthetic package files. No real Tkinter GUI or repo_generator module is imported by the new test.

## NO_RUNTIME_SAFETY_CERTIFICATION
No safety, failure or resolution verdict for the production SCC02 import cycle. Only the restricted model and synthetic CPython fixture were executed.

## NO_WARNING_SUPPRESSION
No warnings, import diagnostics or graph policies were suppressed or modified.

## UNRESOLVED_LIMITATIONS
UNKNOWN: Actual Contextor GUI/repo-generator import outcome across real environment, sys.modules states and third-party/transitive imports. The synthetic source omits most production statements. The tests compare success status only and cannot certify full production startup behavior.

## FINAL_VERDICT
B0G4C9_PASS

## FULL_DIFFS

```diff
diff --git a/tests/test_cycle_semantics_scc02_entry_order.py b/tests/test_cycle_semantics_scc02_entry_order.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cycle_semantics_scc02_entry_order.py
@@ -0,0 +1,393 @@
+"""Restricted SCC02 import-order projection.
+
+Read actual Contextor source only to verify lexical anchors.
+Execute ONLY synthesized minimal modules in isolated processes.
+No result here certifies the behavior of the production GUI.
+"""
+
+import ast
+import json
+import subprocess
+import sys
+from dataclasses import asdict
+from pathlib import Path
+
+import pytest
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+
+_ROOT = Path(__file__).resolve().parents[1]
+
+
+def _real_tree(relative_path):
+    path = _ROOT.joinpath(*relative_path.split("/"))
+    return ast.parse(
+        path.read_text(encoding="utf-8"),
+        filename=str(path),
+    )
+
+
+def _from(tree, module, member, level=0):
+    found = [
+        stmt
+        for stmt in tree.body
+        if isinstance(stmt, ast.ImportFrom)
+        and stmt.module == module
+        and stmt.level == level
+        and any(
+            alias.name == member
+            for alias in stmt.names
+        )
+    ]
+    assert len(found) == 1
+    return found[0]
+
+
+def _definition(tree, name):
+    found = [
+        stmt
+        for stmt in tree.body
+        if isinstance(
+            stmt,
+            (ast.FunctionDef, ast.ClassDef),
+        )
+        and stmt.name == name
+    ]
+    assert len(found) == 1
+    return found[0]
+
+
+def _projection():
+    return {
+        "contextor.__init__": "pass",
+        "contextor.repo_generator.__init__": (
+            "from contextor.repo_generator.main "
+            "import run_repo_generator"
+        ),
+        "contextor.repo_generator.main": (
+            "from contextor.repo_generator.filters "
+            "import FilterWindow\n"
+            "def run_repo_generator():\n"
+            "    pass"
+        ),
+        "contextor.repo_generator.filters": (
+            "from contextor.ui import theme\n"
+            "def FilterWindow():\n"
+            "    pass"
+        ),
+        "contextor.ui.__init__": (
+            "from contextor.ui.gui import run"
+        ),
+        "contextor.ui.gui": (
+            "from contextor.repo_generator "
+            "import run_repo_generator\n"
+            "def run():\n"
+            "    pass"
+        ),
+        "contextor.ui.theme": "pass",
+    }
+
+
+def _model(source, entry):
+    return evaluate_package_import_order(
+        {
+            name: ast.parse(code)
+            for name, code in source.items()
+        },
+        entry,
+    )
+
+
+def _runtime(tmp_path, source, entry):
+    for module, code in source.items():
+        parts = module.split(".")
+
+        if parts[-1] == "__init__":
+            path = tmp_path.joinpath(
+                *parts[:-1],
+                "__init__.py",
+            )
+        else:
+            path = tmp_path.joinpath(
+                *parts[:-1],
+                parts[-1] + ".py",
+            )
+
+        path.parent.mkdir(
+            parents=True,
+            exist_ok=True,
+        )
+        path.write_text(
+            code + "\n",
+            encoding="utf-8",
+        )
+
+    process = subprocess.run(
+        [
+            sys.executable,
+            "-I",
+            "-B",
+            "-c",
+            (
+                "import importlib,sys;"
+                "sys.path.insert(0,sys.argv[1]);"
+                "importlib.import_module(sys.argv[2])"
+            ),
+            str(tmp_path),
+            entry,
+        ],
+        capture_output=True,
+        text=True,
+        timeout=10,
+        check=False,
+    )
+
+    return process
+
+
+def test_scc02_source_chain_still_exists():
+    repo = _real_tree(
+        "contextor/repo_generator/__init__.py"
+    )
+    main = _real_tree(
+        "contextor/repo_generator/main.py"
+    )
+    filters = _real_tree(
+        "contextor/repo_generator/filters.py"
+    )
+    ui = _real_tree(
+        "contextor/ui/__init__.py"
+    )
+    gui = _real_tree(
+        "contextor/ui/gui.py"
+    )
+
+    _from(
+        repo,
+        "contextor.repo_generator.main",
+        "run_repo_generator",
+    )
+    _from(
+        main,
+        "contextor.repo_generator.filters",
+        "FilterWindow",
+    )
+    _from(
+        filters,
+        "contextor.ui",
+        "theme",
+    )
+    _from(
+        ui,
+        "gui",
+        "run",
+        level=1,
+    )
+    _from(
+        gui,
+        "contextor.repo_generator",
+        "run_repo_generator",
+    )
+
+
+def test_scc02_reexport_bindings_follow_imports():
+    main = _real_tree(
+        "contextor/repo_generator/main.py"
+    )
+    filters = _real_tree(
+        "contextor/repo_generator/filters.py"
+    )
+    gui = _real_tree(
+        "contextor/ui/gui.py"
+    )
+
+    assert _from(
+        main,
+        "contextor.repo_generator.filters",
+        "FilterWindow",
+    ).lineno < _definition(
+        main,
+        "run_repo_generator",
+    ).lineno
+
+    assert _from(
+        filters,
+        "contextor.ui",
+        "theme",
+    ).lineno < _definition(
+        filters,
+        "FilterWindow",
+    ).lineno
+
+    assert _from(
+        gui,
+        "contextor.repo_generator",
+        "run_repo_generator",
+    ).lineno < _definition(
+        gui,
+        "run",
+    ).lineno
+
+
+def test_scc02_projection_repo_generator_first_hazard():
+    result = _model(
+        _projection(),
+        "contextor.repo_generator",
+    )
+
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert (
+        result.target_module
+        == "contextor.repo_generator"
+    )
+    assert result.symbol == "run_repo_generator"
+
+    assert not any(
+        event.operation == "DEFINE_FUNCTION"
+        and event.module == "contextor.repo_generator.main"
+        and event.symbol == "run_repo_generator"
+        for event in result.events
+    )
+
+
+def test_scc02_projection_ui_first_passes():
+    result = _model(
+        _projection(),
+        "contextor.ui",
+    )
+
+    assert result.outcome == "MODEL_PASS"
+
+    ready = [
+        event.module
+        for event in result.events
+        if event.operation == "READY"
+    ]
+
+    assert (
+        ready.index("contextor.repo_generator.main")
+        < ready.index("contextor.repo_generator")
+    )
+
+    assert (
+        ready.index("contextor.repo_generator")
+        < ready.index("contextor.ui.gui")
+    )
+
+
+@pytest.mark.parametrize(
+    "entry,expected_success",
+    [
+        ("contextor.repo_generator", False),
+        ("contextor.ui", True),
+    ],
+)
+def test_scc02_projection_matches_fresh_cpython(
+    tmp_path,
+    entry,
+    expected_success,
+):
+    process = _runtime(
+        tmp_path,
+        _projection(),
+        entry,
+    )
+
+    assert (
+        process.returncode == 0
+    ) is expected_success
+
+
+def test_scc02_prebinding_changes_result_without_import_changes(
+    tmp_path,
+):
+    original = _projection()
+    prebound = dict(original)
+
+    prebound["contextor.repo_generator.__init__"] = (
+        "def run_repo_generator():\n"
+        "    pass\n"
+        + original["contextor.repo_generator.__init__"]
+    )
+
+    original_imports = {
+        module: tuple(
+            ast.dump(node, include_attributes=False)
+            for node in ast.walk(ast.parse(code))
+            if isinstance(
+                node,
+                (ast.Import, ast.ImportFrom),
+            )
+        )
+        for module, code in original.items()
+    }
+
+    prebound_imports = {
+        module: tuple(
+            ast.dump(node, include_attributes=False)
+            for node in ast.walk(ast.parse(code))
+            if isinstance(
+                node,
+                (ast.Import, ast.ImportFrom),
+            )
+        )
+        for module, code in prebound.items()
+    }
+
+    assert original_imports == prebound_imports
+
+    original_result = _model(
+        original,
+        "contextor.repo_generator",
+    )
+    changed_result = _model(
+        prebound,
+        "contextor.repo_generator",
+    )
+
+    assert (
+        original_result.outcome
+        == "EARLY_BINDING_HAZARD"
+    )
+    assert changed_result.outcome == "MODEL_PASS"
+
+    process = _runtime(
+        tmp_path,
+        prebound,
+        "contextor.repo_generator",
+    )
+    assert process.returncode == 0
+
+
+def test_scc02_projection_determinism_and_no_ast_mutation():
+    sources = {
+        name: ast.parse(code)
+        for name, code in _projection().items()
+    }
+
+    before = {
+        name: ast.dump(tree, include_attributes=True)
+        for name, tree in sources.items()
+    }
+
+    first = evaluate_package_import_order(
+        sources,
+        "contextor.repo_generator",
+    )
+    second = evaluate_package_import_order(
+        sources,
+        "contextor.repo_generator",
+    )
+
+    assert first == second
+    assert first.outcome == "EARLY_BINDING_HAZARD"
+
+    assert {
+        name: ast.dump(tree, include_attributes=True)
+        for name, tree in sources.items()
+    } == before
+
+    json.dumps(asdict(first))
```

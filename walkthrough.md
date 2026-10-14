TASK: CONTEXTOR_B0G4C16_SCC01_SOURCE_ANCHORED_BINDING_ORDER_REGRESSIONS
HEAD_BEFORE: ded71483c9d56e9829563c30f316cedcdc9e1a64
HEAD_AFTER: ded71483c9d56e9829563c30f316cedcdc9e1a64
GIT_STATUS:
?? tests/test_cycle_semantics_scc01_binding_order.py

LIVE_REVISION_BEFORE: 442
LIVE_REVISION_AFTER: 443
ACTIVITY_EPOCH: 1beab26da2ff4932852caa7db6ff4242
FILES_CHANGED: tests/test_cycle_semantics_scc01_binding_order.py only (walkthrough.md is report artifact)
SOURCE_ANCHOR_VALIDATION: TEST_COVERED; three source-anchor tests passed. DIRECT_EVIDENCE Contextor source previews at revision 442 verified state_manager.module_current_truth:227-269, save_engine_state:506-532, load_engine_state:534-553, watcher._load_watch_filters:485-496, facade._analysis_filters:193-234. Literal source checks confirmed watcher constructor call line155 and live_state package watcher-before-hydration imports lines19-20.
SCC01_STATE_MANAGER_PROJECTION: TEST_COVERED. Synthetic save/load function-local from-imports defer until calls; early call before module_current_truth binding yields model EARLY_BINDING_HAZARD; after binding passes; live-first entry passes without call.
SCC01_WATCHER_PROJECTION: TEST_COVERED. Synthetic zero-argument activate_filters represents call boundary, not class construction. Deferred definition passes. Early activation yields entry-dependent missing hydrate or _analysis_filters. Reordered hydration passes live-first but facade-first remains hazard.
FUNCTION_LOCAL_FROM_ACTIVATION: TEST_COVERED by deferred and activated synthetic fixture cases; function definition alone does not start live import.
EARLY_BINDING_HAZARD_EVIDENCE: Model outcomes and target symbol assertions passed; synthetic CPython failure cases produced ImportError.
BINDING_ORDER_PARITY: Synthetic early state call fails; after-binding state call succeeds. Model and fresh CPython outcomes agree for supported fixtures.
ENTRY_ORDER_PARITY: Synthetic watcher pkg.live and pkg.facade entry variants pass/fail as asserted; reordered fixture resolves only pkg.live-first.
FRESH_CPYTHON_PROCESS_RESULTS: _runtime creates only generated pkg.* source and uses sys.executable -I -B -c subprocess for each case; all comparisons passed.
MODEL_EVENT_EVIDENCE: FUNCTION_LOCAL_FROM events for save_snapshot and load_snapshot verified; absence of CALL_FUNCTION and START_IMPORT in deferred cases verified.
DETERMINISM_AND_AST_IMMUTABILITY: Dedicated test passed equality of repeated assessments, AST dumps unchanged, and JSON serialization.
ISOLATED_TEST_RESULT: .\.venv\Scripts\python.exe -B -m pytest -q tests/test_cycle_semantics_scc01_binding_order.py => 15 passed in 4.56s.
FULL_FOCUSED_TEST_RESULT: .\.venv\Scripts\python.exe -B -m pytest -q tests/test_cycle_semantics_scc01_binding_order.py tests/test_cycle_semantics_function_local_from.py tests/test_cycle_semantics_closure_witness.py tests/test_cycle_semantics_activation_view.py tests/test_cycle_semantics_scc02_entry_order.py tests/test_cycle_semantics_edge_sites.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py => 272 passed in 19.97s.
CANONICAL_FRESHNESS: DIRECT_EVIDENCE desktop_watcher UPDATED new test at revision 443, same epoch, continuity continuous, resync_required=false; new file workspace_sync=verified and canonical module/graph/topology/artifact consumption/cycles/collisions/lineage fresh. Source before edit verified at revision 442.
COLLISION_COUNT_BEFORE_AFTER: 0/fresh -> 0/fresh.
STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER: 16/fresh -> 16/fresh. Path identity not rechecked.
NO_PRODUCTION_GUI_EXECUTION: Differential subprocesses import only generated pkg.* synthetic modules; real Contextor files parsed for AST anchors only. Ordinary pytest harness imports of semantic analyzer do not constitute production SCC differential execution.
NO_RUNTIME_SAFETY_CERTIFICATION: No production SCC01 SAFE/ERROR verdict, Desktop watcher construction, Tkinter lifecycle or backend behavior inferred from synthetic fixtures.
NO_WARNING_SUPPRESSION: No warning policy changes; no production code changed.
UNRESOLVED_LIMITATIONS: Synthetic fixtures omit full production module bodies, class construction, GUI lifecycle, parent-package side effects, dynamic calls and external modules. Runtime behavior of actual SCC01 remains unverified.
FINAL_VERDICT: B0G4C16_PASS

FULL_DIFFS:
diff --git a/tests/test_cycle_semantics_scc01_binding_order.py b/tests/test_cycle_semantics_scc01_binding_order.py
new file mode 100644
index 0000000..273fc84
--- /dev/null
+++ b/tests/test_cycle_semantics_scc01_binding_order.py
@@ -0,0 +1,593 @@
+"""Source-anchored, restricted SCC01 closure projections.
+
+Real Contextor sources are parsed ONLY to validate lexical anchors.
+Only synthetic packages are executed in fresh CPython comparisons.
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
+ROOT = Path(__file__).resolve().parents[1]
+
+
+def _tree(relative):
+    return ast.parse(
+        ROOT.joinpath(
+            *relative.split("/")
+        ).read_text(encoding="utf-8")
+    )
+
+
+def _top(tree, name, kind=ast.FunctionDef):
+    nodes = [
+        statement
+        for statement in tree.body
+        if isinstance(statement, kind)
+        and statement.name == name
+    ]
+    assert len(nodes) == 1
+    return nodes[0]
+
+
+def _from(node, module, member, level=0):
+    matches = [
+        statement
+        for statement in ast.walk(node)
+        if isinstance(statement, ast.ImportFrom)
+        and statement.module == module
+        and statement.level == level
+        and any(
+            alias.name == member
+            for alias in statement.names
+        )
+    ]
+    assert len(matches) >= 1
+    return matches[0]
+
+
+def _model(sources, entry):
+    return evaluate_package_import_order(
+        {
+            name: ast.parse(code)
+            for name, code in sources.items()
+        },
+        entry,
+    )
+
+
+def _runtime(tmp_path, sources, entry):
+    for module, source in sources.items():
+        parts = module.split(".")
+        filename = (
+            "__init__.py"
+            if parts[-1] == "__init__"
+            else parts[-1] + ".py"
+        )
+        path = tmp_path.joinpath(
+            *parts[:-1],
+            filename,
+        )
+        path.parent.mkdir(
+            parents=True,
+            exist_ok=True,
+        )
+        path.write_text(
+            source + "\n",
+            encoding="utf-8",
+        )
+
+    return subprocess.run(
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
+        text=True,
+        capture_output=True,
+        timeout=10,
+        check=False,
+    )
+
+
+def _state_sources(mode="deferred"):
+    state = (
+        ""
+        if mode == "early"
+        else (
+            "def module_current_truth():\n"
+            "    pass\n"
+        )
+    )
+
+    state += (
+        "def save_engine_state():\n"
+        "    from pkg.live import save_snapshot\n"
+        "def load_engine_state():\n"
+        "    from pkg.live import load_snapshot\n"
+    )
+
+    if mode == "early":
+        state += (
+            "save_engine_state()\n"
+            "def module_current_truth():\n"
+            "    pass"
+        )
+
+    elif mode == "called_after":
+        state += (
+            "save_engine_state()\n"
+            "load_engine_state()"
+        )
+
+    return {
+        "pkg.__init__": "pass",
+        "pkg.state": state,
+        "pkg.live.__init__": (
+            "from pkg.store import "
+            "save_snapshot, load_snapshot\n"
+            "from pkg.runtime import run"
+        ),
+        "pkg.store": (
+            "save_snapshot=1\n"
+            "load_snapshot=2"
+        ),
+        "pkg.runtime": (
+            "from pkg.query import query\n"
+            "run=1"
+        ),
+        "pkg.query": (
+            "from pkg.state import module_current_truth\n"
+            "query=1"
+        ),
+    }
+
+
+def _watcher_sources(mode="deferred"):
+    watcher = (
+        "def activate_filters():\n"
+        "    from pkg.facade import _analysis_filters\n"
+    )
+
+    if mode != "deferred":
+        watcher += "activate_filters()"
+
+    live = (
+        (
+            "from pkg.hydration import hydrate\n"
+            "from pkg.watcher import activate_filters"
+        )
+        if mode == "reordered"
+        else (
+            "from pkg.watcher import activate_filters\n"
+            "from pkg.hydration import hydrate"
+        )
+    )
+
+    return {
+        "pkg.__init__": "pass",
+        "pkg.live.__init__": live,
+        "pkg.watcher": watcher,
+        "pkg.hydration": (
+            "def hydrate():\n"
+            "    pass"
+        ),
+        "pkg.facade": (
+            "from pkg.live import hydrate\n"
+            "def _analysis_filters():\n"
+            "    pass"
+        ),
+    }
+
+
+def test_source_anchor_state_local_imports():
+    tree = _tree(
+        "contextor/core/analysis/state_manager.py"
+    )
+
+    truth = _top(
+        tree,
+        "module_current_truth",
+    )
+    save = _top(
+        tree,
+        "save_engine_state",
+    )
+    load = _top(
+        tree,
+        "load_engine_state",
+    )
+
+    assert truth.lineno < save.lineno < load.lineno
+
+    assert _from(
+        save,
+        "contextor.core.live_state",
+        "save_snapshot",
+    ).lineno > save.lineno
+
+    assert _from(
+        load,
+        "contextor.core.live_state",
+        "load_snapshot",
+    ).lineno > load.lineno
+
+
+def test_source_anchor_direct_return_chain():
+    live = _tree(
+        "contextor/core/live_state/__init__.py"
+    )
+    runtime = _tree(
+        "contextor/core/live_state/runtime.py"
+    )
+    query = _tree(
+        "contextor/core/lineage_query/live_query.py"
+    )
+
+    _from(
+        live,
+        "runtime",
+        "connect",
+        level=1,
+    )
+
+    _from(
+        runtime,
+        "contextor.core.lineage_query.live_query",
+        "query_live_symbol_lineage",
+    )
+
+    _from(
+        query,
+        "contextor.core.analysis.state_manager",
+        "module_current_truth",
+    )
+
+
+def test_source_anchor_watcher_constructor_and_binding_order():
+    watcher = _tree(
+        "contextor/core/live_state/watcher.py"
+    )
+    live = _tree(
+        "contextor/core/live_state/__init__.py"
+    )
+    facade = _tree(
+        "contextor/core/api/facade.py"
+    )
+
+    klass = _top(
+        watcher,
+        "DesktopLiveWatcher",
+        ast.ClassDef,
+    )
+    init = _top(
+        klass,
+        "__init__",
+    )
+    loader = _top(
+        klass,
+        "_load_watch_filters",
+    )
+
+    assert any(
+        isinstance(node, ast.Call)
+        and isinstance(node.func, ast.Attribute)
+        and node.func.attr == "_load_watch_filters"
+        for node in ast.walk(init)
+    )
+
+    _from(
+        loader,
+        "contextor.core.api.facade",
+        "_analysis_filters",
+    )
+
+    assert _from(
+        live,
+        "watcher",
+        "DesktopLiveWatcher",
+        level=1,
+    ).lineno < _from(
+        live,
+        "hydration",
+        "hydrate_repository_engine",
+        level=1,
+    ).lineno
+
+    assert _from(
+        facade,
+        "contextor.core.live_state",
+        "hydrate_repository_engine",
+    ).lineno < _top(
+        facade,
+        "_analysis_filters",
+    ).lineno
+
+
+def test_state_deferred_does_not_trigger_live_import(
+    tmp_path,
+):
+    sources = _state_sources()
+    result = _model(
+        sources,
+        "pkg.state",
+    )
+
+    assert result.outcome == "MODEL_PASS"
+
+    assert not any(
+        event.operation == "START_IMPORT"
+        and event.target == "pkg.live"
+        for event in result.events
+    )
+
+    assert _runtime(
+        tmp_path,
+        sources,
+        "pkg.state",
+    ).returncode == 0
+
+
+def test_state_live_entry_imports_state_without_call(
+    tmp_path,
+):
+    sources = _state_sources()
+    result = _model(
+        sources,
+        "pkg.live",
+    )
+
+    assert result.outcome == "MODEL_PASS"
+
+    assert not any(
+        event.operation == "CALL_FUNCTION"
+        for event in result.events
+    )
+
+    assert _runtime(
+        tmp_path,
+        sources,
+        "pkg.live",
+    ).returncode == 0
+
+
+def test_state_early_call_before_binding_is_hazard(
+    tmp_path,
+):
+    sources = _state_sources("early")
+    result = _model(
+        sources,
+        "pkg.state",
+    )
+
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+
+    assert (
+        result.target_module,
+        result.symbol,
+    ) == (
+        "pkg.state",
+        "module_current_truth",
+    )
+
+    process = _runtime(
+        tmp_path,
+        sources,
+        "pkg.state",
+    )
+
+    assert process.returncode != 0
+    assert "ImportError" in process.stderr
+
+
+def test_state_call_after_binding_passes(tmp_path):
+    sources = _state_sources("called_after")
+    result = _model(
+        sources,
+        "pkg.state",
+    )
+
+    assert result.outcome == "MODEL_PASS"
+
+    assert _runtime(
+        tmp_path,
+        sources,
+        "pkg.state",
+    ).returncode == 0
+
+
+def test_state_both_function_local_from_events(tmp_path):
+    sources = _state_sources("called_after")
+    result = _model(
+        sources,
+        "pkg.state",
+    )
+
+    events = [
+        event
+        for event in result.events
+        if event.operation == "FUNCTION_LOCAL_FROM"
+    ]
+
+    assert {
+        (event.target, event.symbol)
+        for event in events
+    } == {
+        ("pkg.live", "save_snapshot"),
+        ("pkg.live", "load_snapshot"),
+    }
+
+    assert _runtime(
+        tmp_path,
+        sources,
+        "pkg.state",
+    ).returncode == 0
+
+
+@pytest.mark.parametrize(
+    "entry",
+    ["pkg.live", "pkg.facade"],
+)
+def test_watcher_deferred_definition_passes(
+    tmp_path,
+    entry,
+):
+    sources = _watcher_sources()
+    result = _model(
+        sources,
+        entry,
+    )
+
+    assert result.outcome == "MODEL_PASS"
+
+    assert _runtime(
+        tmp_path,
+        sources,
+        entry,
+    ).returncode == 0
+
+
+@pytest.mark.parametrize(
+    "entry,missing_module,missing_symbol",
+    [
+        (
+            "pkg.live",
+            "pkg.live",
+            "hydrate",
+        ),
+        (
+            "pkg.facade",
+            "pkg.facade",
+            "_analysis_filters",
+        ),
+    ],
+)
+def test_watcher_early_call_identifies_missing_binding(
+    tmp_path,
+    entry,
+    missing_module,
+    missing_symbol,
+):
+    sources = _watcher_sources("early")
+    result = _model(
+        sources,
+        entry,
+    )
+
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+
+    assert (
+        result.target_module,
+        result.symbol,
+    ) == (
+        missing_module,
+        missing_symbol,
+    )
+
+    process = _runtime(
+        tmp_path,
+        sources,
+        entry,
+    )
+
+    assert process.returncode != 0
+    assert "ImportError" in process.stderr
+
+
+@pytest.mark.parametrize(
+    "entry,expected",
+    [
+        ("pkg.live", "MODEL_PASS"),
+        ("pkg.facade", "EARLY_BINDING_HAZARD"),
+    ],
+)
+def test_watcher_reordered_hydration_does_not_cure_every_entry(
+    tmp_path,
+    entry,
+    expected,
+):
+    sources = _watcher_sources("reordered")
+    result = _model(
+        sources,
+        entry,
+    )
+
+    assert result.outcome == expected
+
+    process = _runtime(
+        tmp_path,
+        sources,
+        entry,
+    )
+
+    assert (
+        process.returncode == 0
+    ) == (
+        expected == "MODEL_PASS"
+    )
+
+    if expected != "MODEL_PASS":
+        assert (
+            result.target_module,
+            result.symbol,
+        ) == (
+            "pkg.facade",
+            "_analysis_filters",
+        )
+
+
+def test_determinism_and_original_source_ast_unchanged():
+    source = _watcher_sources("early")
+
+    trees = {
+        name: ast.parse(code)
+        for name, code in source.items()
+    }
+
+    original = {
+        name: ast.dump(
+            tree,
+            include_attributes=True,
+        )
+        for name, tree in trees.items()
+    }
+
+    first = evaluate_package_import_order(
+        trees,
+        "pkg.facade",
+    )
+    second = evaluate_package_import_order(
+        trees,
+        "pkg.facade",
+    )
+
+    assert first == second
+    assert first.outcome == "EARLY_BINDING_HAZARD"
+
+    assert original == {
+        name: ast.dump(
+            tree,
+            include_attributes=True,
+        )
+        for name, tree in trees.items()
+    }
+
+    json.dumps(asdict(first))

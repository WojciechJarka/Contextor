# CONTEXTOR_B0G4C24_RESTRICTED_PASSIVE_CLASS_BINDING

TASK: Controlled literal implementation of restricted passive class binding.
HEAD_BEFORE: 7b9fac57cb83d15ed80ec845d1c2573ed342b0fd.
HEAD_AFTER: 7b9fac57cb83d15ed80ec845d1c2573ed342b0fd.
GIT_STATUS: M contextor/core/cycle_semantics/package_model.py;  M tests/test_cycle_semantics_function_local_from.py;  M tests/test_cycle_semantics_package_model.py;  M tests/test_cycle_semantics_passive_functions.py;  M walkthrough.md; ?? tests/test_cycle_semantics_passive_classes.py. C23F changes in three other files predate this task; walkthrough.md is this mandated report.
FILES_CHANGED: contextor/core/cycle_semantics/package_model.py; tests/test_cycle_semantics_passive_classes.py. These are the only source/test edits made in C24.
FULL_DIFFS: Complete C24-only diffs for both task files follow; earlier stage diffs are excluded.

MODEL_CONTRACT_PRECHECK: DIRECT_EVIDENCE: Contextor get_file_edit_context at revision 456 identified package_model as canonical owner, adapter layer, fresh and verified, with six direct test consumers. get_symbol_implementation confirmed _safe_passive_function_definition at lines 45-113 and _compile at 116-427. Source anchors for _Step, child shadowing, DEFINE_OPAQUE_FUNCTION, CALL_FUNCTION and C23F compile validation matched. Real declarations confirmed through Contextor: RepoGenerator at main.py:16, FilterWindow at filters.py:10, ContextorGUI at gui.py:91. A bounded AST read found only methods in the first two class bodies, and an initial expression plus methods in ContextorGUI; whole modules have additional syntax outside this restricted grammar. No material contract drift.
CLASS_BODY_GRAMMAR: Exact helper accepts plain class without bases, keywords, decorators or type parameters. Body permits Pass, first-position literal string docstring, and safe synchronous FunctionDef methods. Other body operations return UNKNOWN.
METHOD_DEFINITION_SAFETY: Function validator accepts dunder names only with allow_dunder=True from class grammar. Decorators, annotations, dynamic defaults, type comments and type parameters remain rejected. Module-level function compilation retains allow_dunder=False.
CLASS_NAME_BINDING: _compile emits DEFINE_PASSIVE_CLASS after grammar check; evaluator binds unique passive-class marker and records event in source order. Child-name shadowing guard includes the new op and retains UNKNOWN. Method names are not bound in module namespace.
CLASS_BODY_NONEXECUTION_LIMITATIONS: The model only validates the narrow grammar and records class binding; it does not execute class statements or method bodies. General class-body effects remain UNKNOWN.
CONSTRUCTOR_CALL_UNKNOWN: Existing CALL_FUNCTION identity check unchanged; direct C() call returns UNKNOWN. Constructor not simulated.
PACKAGE_CLASS_REEXPORT: Synthetic initializer imports a class after its definition; model and CPython success verified.
EARLY_CLASS_BINDING_HAZARD: Reentrant class export before statement yields EARLY_BINDING_HAZARD; CPython ImportError verified.
TWO_ENTRY_CPYTHON_PARITY: Synthetic repo-first: EARLY_BINDING_HAZARD and CPython ImportError; ui-first: MODEL_PASS and CPython import success. No production SCC modules imported.
UNSUPPORTED_CLASS_FEATURES: Bases, class decorator, dynamic method default, method annotation, class-body import and class call return UNKNOWN in tests. Class-body assignments remain outside grammar.
COMPILE_TIME_SYNTAX_VALIDATION: Existing C23F upfront AST compile remains; invalid break in method yields UNKNOWN, CPython SyntaxError. Compiled code objects are not executed.
ISOLATED_TEST_RESULTS: 15 passed in 2.61s.
FOCUSED_TEST_RESULTS: 349 passed in 31.01s across the specified 21 focused files. Task-file and final whole-tree git diff --check both exited 0; Git emitted only line-ending conversion notices for two pre-existing C23F test edits.
LIVE_REVISION_BEFORE_AFTER: 456 -> 458.
ACTIVITY_EPOCH: 1beab26da2ff4932852caa7db6ff4242, unchanged.
LIVE_EVENT_CONTINUITY: get_live_events(after_revision=456): continuous, resync_required=false; desktop_watcher UPDATED package_model.py at 457 and passive_classes.py at 458.
WORKSPACE_SYNC: Both task files verified by Contextor at revision 458.
CANONICAL_FRESHNESS: Both canonical_state=fresh at 458; graph/topology/artifact_consumption/cycles/collisions/lineage fresh; syntax errors 0. Post-edit blast radius includes new test as seventh direct static consumer.
COLLISION_COUNT_BEFORE_AFTER: 0 -> 0, fresh.
STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER: 16 -> 16 canonical reported cycle paths, fresh.
NO_RUNTIME_SAFETY_CERTIFICATION: Restricted synthetic model and fixture parity do not certify real GUI/repo_generator initialization safety.
NO_WARNING_SUPPRESSION: No warning policy, graph or SCC analyzer change.
UNRESOLVED_LIMITATIONS: Real production modules are not certified as supported by the entire restricted model. General metaclass, descriptor, constructor and arbitrary class-body effects stay UNKNOWN.
FINAL_VERDICT: B0G4C24_PASS. Exact implementation and test file, 15/15 isolated and 349/349 focused, LIVE synchronized, no new collisions or cycle warnings. STOP; await proceduj.

FULL_DIFFS

ACTUAL_DIFF: contextor/core/cycle_semantics/package_model.py (C24 only)

~~~diff
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -46,0 +47,2 @@
+    *,
+    allow_dunder: bool = False,
@@ -55 +57,4 @@
-        or statement.name.startswith("__")
+        or (
+            statement.name.startswith("__")
+            and not allow_dunder
+        )
@@ -115,0 +121,53 @@
+def _safe_passive_class_definition(
+    statement: ast.ClassDef,
+) -> bool:
+    """Validate a class whose body has no unknown effects.
+
+    Class body evaluation is not generally passive.
+    Only a literal docstring, Pass and safe method
+    definitions are modeled here.
+
+    The model records class-name binding only.
+    It does not execute class or method code.
+    """
+    if (
+        not statement.name.isidentifier()
+        or statement.name.startswith("__")
+        or statement.bases
+        or statement.keywords
+        or statement.decorator_list
+        or getattr(statement, "type_params", ())
+    ):
+        return False
+
+    for index, body_statement in enumerate(
+        statement.body
+    ):
+        if isinstance(body_statement, ast.Pass):
+            continue
+
+        if (
+            index == 0
+            and isinstance(body_statement, ast.Expr)
+            and isinstance(
+                body_statement.value,
+                ast.Constant,
+            )
+            and type(body_statement.value.value) is str
+        ):
+            continue
+
+        if (
+            isinstance(body_statement, ast.FunctionDef)
+            and _safe_passive_function_definition(
+                body_statement,
+                allow_dunder=True,
+            )
+        ):
+            continue
+
+        return False
+
+    return True
+
+
@@ -321,0 +380,11 @@
+
+        elif isinstance(stmt, ast.ClassDef):
+            if not _safe_passive_class_definition(stmt):
+                return None
+
+            steps.append(
+                _Step(
+                    "DEFINE_PASSIVE_CLASS",
+                    binding=stmt.name,
+                )
+            )
@@ -562,0 +632 @@
+                "DEFINE_PASSIVE_CLASS",
@@ -895,0 +966,16 @@
+        elif step.op == "DEFINE_PASSIVE_CLASS":
+            namespaces[module][step.binding] = (
+                "\x00PASSIVE_CLASS:"
+                + module
+                + ":"
+                + step.binding
+            )
+
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "DEFINE_PASSIVE_CLASS",
+                    symbol=step.binding,
+                )
+            )
+
~~~

ACTUAL_DIFF: tests/test_cycle_semantics_passive_classes.py

~~~diff
--- /dev/null
+++ b/tests/test_cycle_semantics_passive_classes.py
@@ -0,0 +1,372 @@
+"""Restricted passive class import-order regressions."""
+
+import ast
+import json
+import subprocess
+import sys
+from dataclasses import asdict
+
+import pytest
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+
+def _model(sources, entry):
+    return evaluate_package_import_order(
+        {
+            name: ast.parse(source)
+            for name, source in sources.items()
+        },
+        entry,
+    )
+
+
+def _actual(tmp_path, sources, entry):
+    for module, source in sources.items():
+        parts = module.split(".")
+        path = tmp_path.joinpath(
+            *parts[:-1],
+            "__init__.py"
+            if parts[-1] == "__init__"
+            else parts[-1] + ".py",
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
+        capture_output=True,
+        text=True,
+        timeout=10,
+        check=False,
+    )
+
+
+def test_c24_plain_class_and_docstring(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class C:\n"
+            '    """Passive class."""\n'
+            "    pass"
+        ),
+    }
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "C"
+        for event in result.events
+    )
+
+    assert _actual(
+        tmp_path, sources, "pkg.a"
+    ).returncode == 0
+
+
+def test_c24_constructor_body_not_executed(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class RepoGenerator:\n"
+            "    def __init__(self, parent=None):\n"
+            '        raise RuntimeError("not called")\n'
+            "    def run(self):\n"
+            "        dangerous()"
+        ),
+    }
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "MODEL_PASS"
+
+    assert not any(
+        event.operation == "CALL_FUNCTION"
+        for event in result.events
+    )
+
+    assert _actual(
+        tmp_path, sources, "pkg.a"
+    ).returncode == 0
+
+
+def test_c24_passive_class_reexport(tmp_path):
+    sources = {
+        "pkg.__init__": (
+            "from pkg.a import RepoGenerator"
+        ),
+        "pkg.a": (
+            "class RepoGenerator:\n"
+            "    def __init__(self, parent=None):\n"
+            "        dangerous()"
+        ),
+    }
+
+    result = _model(sources, "pkg")
+
+    assert result.outcome == "MODEL_PASS"
+
+    assert any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        for event in result.events
+    )
+
+    assert _actual(
+        tmp_path, sources, "pkg"
+    ).returncode == 0
+
+
+def test_c24_class_export_binding_order_hazard(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "from pkg.b import ready\n"
+            "class C:\n"
+            "    pass"
+        ),
+        "pkg.b": (
+            "from pkg.a import C\n"
+            "ready = 1"
+        ),
+    }
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert (
+        result.target_module,
+        result.symbol,
+    ) == ("pkg.a", "C")
+
+    process = _actual(tmp_path, sources, "pkg.a")
+
+    assert process.returncode != 0
+    assert "ImportError" in process.stderr
+
+
+@pytest.mark.parametrize(
+    ("entry", "expected", "target", "symbol"),
+    [
+        (
+            "repo",
+            "EARLY_BINDING_HAZARD",
+            "repo",
+            "run_repo_generator",
+        ),
+        ("ui", "MODEL_PASS", None, None),
+    ],
+)
+def test_c24_synthetic_two_entry_orders(
+    tmp_path, entry, expected, target, symbol
+):
+    sources = {
+        "repo.__init__": (
+            "from repo.main import run_repo_generator"
+        ),
+        "repo.main": (
+            "from repo.filters import FilterWindow\n"
+            "class RepoGenerator:\n"
+            "    def __init__(self, root):\n"
+            "        dangerous()\n"
+            "def run_repo_generator(parent=None):\n"
+            "    dangerous()"
+        ),
+        "repo.filters": (
+            "from ui import theme\n"
+            "class FilterWindow:\n"
+            "    def __init__(self, parent):\n"
+            "        dangerous()"
+        ),
+        "ui.__init__": "from ui.gui import run",
+        "ui.gui": (
+            "from repo import run_repo_generator\n"
+            "class ContextorGUI:\n"
+            "    def __init__(self, root):\n"
+            "        dangerous()\n"
+            "def run(*, single_instance=None):\n"
+            "    dangerous()"
+        ),
+        "ui.theme": "ready = 1",
+    }
+
+    result = _model(sources, entry)
+
+    assert result.outcome == expected
+    assert (
+        result.target_module,
+        result.symbol,
+    ) == (target, symbol)
+
+    process = _actual(tmp_path, sources, entry)
+
+    if expected == "MODEL_PASS":
+        assert process.returncode == 0
+    else:
+        assert process.returncode != 0
+        assert "ImportError" in process.stderr
+
+
+def test_c24_constructor_call_unknown():
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class C:\n"
+            "    pass\n"
+            "C()"
+        ),
+    }
+
+    assert _model(
+        sources, "pkg.a"
+    ).outcome == "UNKNOWN"
+
+
+@pytest.mark.parametrize(
+    "definition",
+    [
+        "class C(Base):\n    pass",
+        "@decorator\nclass C:\n    pass",
+        (
+            "class C:\n"
+            "    def method(self, x=compute()):\n"
+            "        pass"
+        ),
+        (
+            "class C:\n"
+            "    def method(self, x: Unknown):\n"
+            "        pass"
+        ),
+    ],
+)
+def test_c24_unsupported_class_definitions_unknown(
+    definition,
+):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": definition,
+    }
+
+    assert _model(
+        sources, "pkg.a"
+    ).outcome == "UNKNOWN"
+
+
+def test_c24_class_body_import_unknown():
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class C:\n"
+            "    import pkg.child"
+        ),
+        "pkg.child": "pass",
+    }
+
+    assert _model(
+        sources, "pkg.a"
+    ).outcome == "UNKNOWN"
+
+
+def test_c24_main_guard_selected_class(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            'if __name__ != "__main__":\n'
+            "    class C:\n"
+            "        def __init__(self):\n"
+            "            dangerous()"
+        ),
+    }
+
+    assert _model(
+        sources, "pkg.a"
+    ).outcome == "MODEL_PASS"
+
+    assert _actual(
+        tmp_path, sources, "pkg.a"
+    ).returncode == 0
+
+
+def test_c24_invalid_method_body_compile_unknown(
+    tmp_path,
+):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class C:\n"
+            "    def method(self):\n"
+            "        break"
+        ),
+    }
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "UNKNOWN"
+
+    process = _actual(tmp_path, sources, "pkg.a")
+
+    assert process.returncode != 0
+    assert "SyntaxError" in process.stderr
+
+
+def test_c24_determinism_and_ast_immutability():
+    trees = {
+        "pkg.__init__": ast.parse(
+            "from pkg.a import C"
+        ),
+        "pkg.a": ast.parse(
+            "class C:\n"
+            "    def __init__(self, value=None):\n"
+            "        dangerous()"
+        ),
+    }
+
+    before = {
+        name: ast.dump(
+            tree,
+            include_attributes=True,
+        )
+        for name, tree in trees.items()
+    }
+
+    first = evaluate_package_import_order(
+        trees, "pkg"
+    )
+
+    second = evaluate_package_import_order(
+        trees, "pkg"
+    )
+
+    assert first == second
+    assert first.outcome == "MODEL_PASS"
+
+    assert before == {
+        name: ast.dump(
+            tree,
+            include_attributes=True,
+        )
+        for name, tree in trees.items()
+    }
+
+    json.dumps(asdict(first))
~~~

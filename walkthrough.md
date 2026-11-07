# CONTEXTOR C16-B03-P1D3G18-P1 — BOUNDED INTEGER ARITHMETIC AND VERSION BINDING

## HEAD_BEFORE_AND_HEAD_AFTER

HEAD_BEFORE=`8df2c1d2dba89da4b50c61a40349654f2fe89661`; HEAD_AFTER=`8df2c1d2dba89da4b50c61a40349654f2fe89661`. No commit or push. The worktree initially had only a modified `walkthrough.md`; target production/test files had no pre-existing changes. CPython interpreter: repository `.venv\Scripts\python.exe`, **Python 3.15.2**. Contextor MCP was used first: canonical revision 1082, production/test workspace_sync verified, structural DFS cycles 16, cycle_semantics stale.

## IMPLEMENTATION_AND_FILES_CHANGED

FILES_CHANGED: `contextor/core/cycle_semantics/package_model.py`; `tests/test_cycle_semantics_package_model_literals.py`. Inserted the exact supplied `_bounded_integer_arithmetic` immediately before `_pure_literal_expression`, integrated its BinOp traversal at the exact specified point with the shared 256-node budget, and replaced only the specified dunder assignment condition to admit exact string-literal module `__version__`. Existing BIND, ALIAS, ATTR, container/unary/dict logic and warning policy were left unchanged. Appended the supplied regression tests to the existing literal test module. No other production/test file changed.

## TARGETED_PYTEST

Exact command, with temporary `PYTHONDONTWRITEBYTECODE=1` in the test process environment:

`& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_package_model_literals.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_model_annotations315.py tests/test_cycle_semantics_package_model_async_alias.py`

Result: **249 passed in 20.09s**, exit 0. No full suite. Tests cover supported and rejected arithmetic, exact-int exclusion of bool, bit-length/depth/node boundaries, __version__ restrictions, class-local/deferred binding, ordering, early-binding hazard, external/namespace UNKNOWN, determinism and AST immutability. No analyzed source code was executed by the classifier.

## PRE_POST_COMPILER_ACCEPTANCE_CENSUS

Read-only `_compile` census with `annotation_semantics="DEFERRED"` and current `recognize_typing_guard`. Production selection: 306 `contextor/**/*.py` plus root `main.py`, excluding `tests/`; denominator **307**. All 307 current source-byte SHA-256 values matched the canonical FileState at revision 1084; 0 source-unbound/unavailable. Rebuilt both OPTIONAL_NAMED_CHILDREN cohorts from canonical hard_edges and Module.imports. Prefix compilation located the first rejected top-level statement; no AST mutation or analyzed code execution.

| Cohort | Before G18-P1 supported | After supported / total | After rejected | Delta supported |
|---|---:|---:|---:|---:|
| ALL_PRODUCTION | 154 | 158/307 | 149 | +4 |
| SCC1 | 94 | 94/201 | 107 | 0 |
| SCC2 | 107 | 107/221 | 114 | 0 |
| SCC_UNION | 107 | 107/221 | 114 | 0 |
| OUTSIDE_BOTH | 47 | 51/86 | 35 | +4 |

The SCC cohorts overlap: SCC1 is contained in SCC2; they were not added as disjoint populations. Acceptance by `_compile` is not MODEL_PASS for a project or SCC. The +4 net gain was observed outside the SCC union; no target count was presumed.

## FIRST_FAILURE_DISTRIBUTION

| Cohort | ClassDef | Assign | AnnAssign | If | FunctionDef | AsyncFunctionDef | Expr | Sum rejected |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL_PRODUCTION | 88 | 47 | 4 | 1 | 5 | 1 | 3 | 149 |
| SCC1 | 69 | 33 | 2 | 1 | 2 | 0 | 0 | 107 |
| SCC2 / UNION | 72 | 37 | 2 | 1 | 2 | 0 | 0 | 114 |
| OUTSIDE_BOTH | 16 | 10 | 2 | 0 | 3 | 1 | 3 | 35 |

As earlier Assign barriers became accepted, later statements became the first rejection in some modules; therefore changes in category counts need not equal the +4 net accepted modules.

## SCC_CLOSURE_STATISTICS

Canonical revision 1084, state_id `20261106_195021`; indexed graph and FileState domains 624, production files 307. SCC1 selected 201 source modules, SCC2 selected 221, union 221, outside union 86. All selected production source files were FileState-bound. Snapshot had no optional /3 receipt; metadata revision remained 1084 through the read-only replay.

## MCP_POST_CHANGE_AUDIT

Read-only Contextor MCP after test and replay: canonical revision 1084, canonical_state fresh, workspace_sync verified for both changed modules, advisory_warning null, syntax errors 0, structural DFS cycles 16 (baseline 16), active_warning_count 16, model_pass_count 0, cycle_semantics stale. No production FULL, update_file, backend restart, warning-suppression edit or manual Git mutation.

## REMAINING_UNKNOWN_BOUNDARIES

The exact helper recognizes only bounded built-in integer AST arithmetic; it does not model arbitrary operators, names, calls, attributes or custom object effects. Accepted values are not published as namespace values. The module `__version__` exception applies only to direct exact string constants. Namespace layout, opaque external imports, target interpreter identity, stale cycle_semantics, and unmodeled expression effects remain separate fail-closed boundaries. No SCC safety or optional /3 receipt is claimed from compiler acceptance.

## FULL_DIFFS

Complete actual diffs for both changed source/test files follow. `walkthrough.md` is excluded from its own diff.

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index eb7b592..c43d893 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -221,6 +221,83 @@ def _safe_passive_class_definition(
     return True
 
 
+def _bounded_integer_arithmetic(
+    expression: ast.AST,
+    *,
+    depth: int,
+    node_budget: int,
+) -> tuple[bool, int]:
+    """Recognize bounded, exact built-in integer arithmetic only."""
+    used = 0
+
+    def calculate(
+        node: ast.AST,
+        node_depth: int,
+    ) -> int | None:
+        nonlocal used
+
+        if node_depth > 16 or used >= node_budget:
+            return None
+
+        used += 1
+
+        if type(node) is ast.Constant:
+            if type(node.value) is not int:
+                return None
+            value = node.value
+
+        elif type(node) is ast.UnaryOp:
+            if type(node.op) not in (ast.UAdd, ast.USub):
+                return None
+
+            operand = calculate(
+                node.operand,
+                node_depth + 1,
+            )
+            if operand is None:
+                return None
+
+            value = (
+                operand
+                if type(node.op) is ast.UAdd
+                else -operand
+            )
+
+        elif type(node) is ast.BinOp:
+            if type(node.op) not in (
+                ast.Add,
+                ast.Sub,
+                ast.Mult,
+            ):
+                return None
+
+            left = calculate(node.left, node_depth + 1)
+            if left is None:
+                return None
+
+            right = calculate(node.right, node_depth + 1)
+            if right is None:
+                return None
+
+            if type(node.op) is ast.Add:
+                value = left + right
+            elif type(node.op) is ast.Sub:
+                value = left - right
+            else:
+                value = left * right
+
+        else:
+            return None
+
+        if value.bit_length() > 64:
+            return None
+
+        return value
+
+    accepted = calculate(expression, depth) is not None
+    return accepted, used
+
+
 def _pure_literal_expression(expr: ast.AST) -> bool:
     pending: list[tuple[ast.AST, int, bool]] = [
         (expr, 0, False)
@@ -256,6 +333,20 @@ def _pure_literal_expression(expr: ast.AST) -> bool:
             )
             continue
 
+        if type(node) is ast.BinOp:
+            accepted, counted = _bounded_integer_arithmetic(
+                node,
+                depth=depth,
+                node_budget=257 - visited,
+            )
+
+            visited += counted - 1
+
+            if not accepted or visited > 256:
+                return False
+
+            continue
+
         if type(node) is ast.Tuple:
             pending.extend(
                 (item, depth + 1, hashable_required)
@@ -575,8 +666,17 @@ def _compile(
             if name.startswith("__"):
                 if not (
                     _depth == 0
-                    and name == "__all__"
-                    and _pure_all_assignment(value)
+                    and (
+                        (
+                            name == "__all__"
+                            and _pure_all_assignment(value)
+                        )
+                        or (
+                            name == "__version__"
+                            and type(value) is ast.Constant
+                            and type(value.value) is str
+                        )
+                    )
                 ):
                     return None
 
diff --git a/tests/test_cycle_semantics_package_model_literals.py b/tests/test_cycle_semantics_package_model_literals.py
index 40ae33f..14f3930 100644
--- a/tests/test_cycle_semantics_package_model_literals.py
+++ b/tests/test_cycle_semantics_package_model_literals.py
@@ -277,3 +277,189 @@ def test_compile_accepts_all_literal_assignment():
         "__all__ = ['alpha', 'beta']"
     )
     assert _compile(tree, "pkg.child", False) is not None
+
+
+@pytest.mark.parametrize(
+    "source",
+    [
+        "x = 16 * 1024",
+        "x = 1 + 2 * 3",
+        "x = (5 + 3) * (9 - 2)",
+        "x = -4 * 3 + 2",
+        "x = 3 * (1 - 2)",
+        "x = [1 + 2, 4 * 8]",
+        "x = {'size': 4 * 8}",
+        "x = {1 + 2: 'value'}",
+        "x = 0 * 100",
+        "x = 9223372036854775808 - 1",
+    ],
+)
+def test_g18_p1_bounded_integer_arithmetic_pass(source):
+    result = _model(source)
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "BIND"
+        for event in result.events
+    )
+
+
+@pytest.mark.parametrize(
+    "source",
+    [
+        "x = True + 1",
+        "x = 1 + True",
+        "x = 1.0 + 2",
+        "x = 'a' + 'b'",
+        "x = 1 + missing",
+        "x = 1 + side_effect()",
+        "x = 1 / 0",
+        "x = 2 ** 8",
+        "x = 1 << 2",
+        "x = 2 // 1",
+        "x = 1 & 2",
+        "x = 1 * [1]",
+        "x = 18446744073709551615 + 1",
+        "x = 9223372036854775808 * 2",
+    ],
+)
+def test_g18_p1_unsupported_arithmetic_unknown(source):
+    assert _model(source).outcome == "UNKNOWN"
+
+
+def test_g18_p1_arithmetic_class_local_binding():
+    result = _model(
+        "class C:\n"
+        "    x = 16 * 1024\n"
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "CLASS_LOCAL_BIND"
+        and event.symbol == "x"
+        for event in result.events
+    )
+
+
+def test_g18_p1_arithmetic_deferred_annassign():
+    result = _model(
+        "x: Later = 16 * 1024",
+        mode="DEFERRED",
+    )
+    assert result.outcome == "MODEL_PASS"
+
+
+def test_g18_p1_version_literal_binding():
+    result = _model(
+        "__version__ = '1.0.4'"
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "BIND"
+        and event.symbol == "__version__"
+        for event in result.events
+    )
+
+
+@pytest.mark.parametrize(
+    "source",
+    [
+        "__version__ = 1",
+        "__version__ = build_version()",
+        "__version__ = '1' + '.0'",
+        "__version__ = other",
+        "__path__ = ['other']",
+        "__getattr__ = something",
+        "__annotations__ = {}",
+        "class C:\n    __version__ = '1.0'",
+    ],
+)
+def test_g18_p1_reserved_binding_restrictions(source):
+    assert _model(source).outcome == "UNKNOWN"
+
+
+def test_g18_p1_version_binding_preserves_order():
+    result = _model(
+        "__version__ = '1.0.4'\n"
+        "from pkg import value\n",
+        initializer="value = 7",
+    )
+    assert result.outcome == "MODEL_PASS"
+
+    operations = [
+        event.operation
+        for event in result.events
+        if event.module == "pkg.child"
+    ]
+    assert operations.index("BIND") < operations.index("FROM")
+
+
+def test_g18_p1_arithmetic_early_binding_hazard():
+    result = _model(
+        "from pkg import late",
+        initializer=(
+            "import pkg.child\n"
+            "late = 16 * 1024\n"
+        ),
+        entry="pkg",
+    )
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert result.target_module == "pkg"
+    assert result.symbol == "late"
+
+
+def test_g18_p1_arithmetic_binding_before_import():
+    result = _model(
+        "from pkg import late",
+        initializer=(
+            "late = 16 * 1024\n"
+            "import pkg.child\n"
+        ),
+        entry="pkg",
+    )
+    assert result.outcome == "MODEL_PASS"
+
+
+def test_g18_p1_external_import_still_unknown():
+    assert _model(
+        "x = 16 * 1024\n"
+        "import missing_external_xyz"
+    ).outcome == "UNKNOWN"
+
+
+def test_g18_p1_namespace_layout_still_unknown():
+    result = evaluate_package_import_order(
+        {
+            "pkg.child": ast.parse(
+                "x = 16 * 1024"
+            )
+        },
+        "pkg.child",
+    )
+    assert result.outcome == "UNKNOWN"
+
+
+def test_g18_p1_arithmetic_ast_immutability():
+    sources = {
+        "pkg.__init__": ast.parse("pass"),
+        "pkg.child": ast.parse(
+            "x = (5 + 3) * (9 - 2)"
+        ),
+    }
+
+    before = {
+        key: ast.dump(tree)
+        for key, tree in sources.items()
+    }
+
+    first = evaluate_package_import_order(
+        sources, "pkg.child"
+    )
+    second = evaluate_package_import_order(
+        sources, "pkg.child"
+    )
+
+    assert first == second
+    assert first.outcome == "MODEL_PASS"
+    assert before == {
+        key: ast.dump(tree)
+        for key, tree in sources.items()
+    }
```

## FINAL_VERDICT

PASS — the literal implementation passed all 249 targeted tests, increased FileState-bound compiler acceptance to 158/307, and preserved 16 structural cycles with no new MODEL_PASS or optional /3 receipt.

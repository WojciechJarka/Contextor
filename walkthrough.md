# CONTEXTOR P1D3-WARN-5I — SCC-local package model preparation cache

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `8b2f660e5808174f84897aa0fb1a00947039f849`; initial worktree clean. Contextor MCP resolved all three target modules at revision 896; structural DFS count 16. WARN-5H fail-fast code was present. The supplied SEARCH anchors matched the current code; no source drift was observed.

## EXACT_SEARCH_REPLACE

- DIRECT_EVIDENCE: Applied the architect-authored literal replacements to `package_model.py`, `scenarios.py`, and `test_cycle_semantics_package_model.py`. No other source or test changed.

## SCC_LOCAL_CACHE_CONTRACT

- CODE_PATH_PROVED: `_PackageSourceSession` stores exact AST object identities, a layout, per-module CPython compile validation, and immutable restricted-step tuples. `analyze_cycle_scenarios` creates one session per regular-package SCC and passes it to each entry evaluation. There is no global session or cross-generation cache in this path.
- CONTRACT_PROVED: The new preparation-reuse test passed during the targeted run, checking one layout, two CPython compiles, and two restricted compilations across two entries. The AST-identity negative test passed, returning UNKNOWN on a second mapping with different AST objects.

## ENTRY_ISOLATION

- CODE_PATH_PROVED: Each evaluation still constructs local `events`, `programs`, states, namespaces and frames. Cached restricted tuples are copied to lists before interpretation. The new function-expansion test passed, comparing cached and fresh second-entry results and unchanged AST dumps.

## CACHE_NEGATIVE_CASES

- DIRECT_EVIDENCE: The three new WARN-5I tests passed within the targeted run. The suite did not fully pass because an existing passive-class test failed. Do not infer global UNKNOWN/HAZARD/MODEL_PASS parity from this run.
- CONTRACT_CONFLICT: `tests/test_cycle_semantics_passive_classes.py::test_c24_class_body_import_unknown` expects UNKNOWN for a class-body import fixture; actual result was MODEL_PASS. This test calls the package model without a session, so the exact cause and whether the failure predates this patch are not established by this run. No alternate implementation or assertion change was made.

## TARGETED_TESTS

- DIRECT_EVIDENCE: `python -m py_compile` on all three changed files passed.
- DIRECT_EVIDENCE: `python -m pytest -q -rs tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_passive_functions.py tests/test_cycle_semantics_passive_classes.py tests/test_cycle_semantics_evidence.py` → 216 passed, 1 failed in 22.86s. Failure at `tests/test_cycle_semantics_passive_classes.py:286`: expected UNKNOWN, got MODEL_PASS for `pkg.a` containing `class C: import pkg.child`.
- DIRECT_EVIDENCE: `git diff --check --` the three changed Python files produced no whitespace errors. Git warned that LF in `scenarios.py` will be converted to CRLF on a future Git write; no Git mutation was performed.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: MCP `get_module_context` after edits returned canonical revision 896, structural DFS count 16 and cycle_semantics stale. Workspace_sync was out_of_sync for all three changed files at that read. No source sync or loaded-code adoption is claimed.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `contextor/core/cycle_semantics/scenarios.py`
- `tests/test_cycle_semantics_package_model.py`

`walkthrough.md` is the authorized report and is excluded from source/test FILES_CHANGED.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 6323ba5..45d4d56 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -8,7 +8,7 @@ from __future__ import annotations
 
 import ast
 from collections.abc import Mapping
-from dataclasses import dataclass, replace
+from dataclasses import dataclass, field, replace
 
 from contextor.core.cycle_semantics.package_layout import build_package_layout
 from contextor.core.cycle_semantics.typing_guard import (
@@ -48,6 +48,18 @@ class _Step:
     class_local: bool = False
 
 
+@dataclass
+class _PackageSourceSession:
+    """Ephemeral SCC-local cache; never published or shared across analyses."""
+
+    source_trees: tuple[tuple[str, ast.Module], ...] | None = None
+    layout: object | None = None
+    validated_code: set[str] = field(default_factory=set)
+    compiled_steps: dict[str, tuple[_Step, ...]] = field(
+        default_factory=dict
+    )
+
+
 def _safe_passive_function_definition(
     statement: ast.FunctionDef,
     *,
@@ -594,6 +606,8 @@ def _compile(
 def evaluate_package_import_order(
     indexed_sources: Mapping[str, ast.AST],
     entry_module: str,
+    *,
+    _session: _PackageSourceSession | None = None,
 ) -> PackageImportAssessment:
     """Simulate a restricted closed regular-package source set.
 
@@ -630,13 +644,38 @@ def evaluate_package_import_order(
     ):
         return result("UNKNOWN")
 
-    # An unsupported package layout cannot establish MODEL_PASS,
-    # regardless of the AST contents. Reject before repeatedly
-    # compiling an entire large SCC source closure.
-    try:
-        layout = build_package_layout(indexed_sources)
-    except (TypeError, ValueError):
-        return result("UNKNOWN")
+    # Reuse source-independent preparation only for the exact same
+    # AST objects inside one SCC evaluation. This private cache must
+    # never outlive the analyze_cycle_scenarios invocation.
+    if _session is not None:
+        if type(_session) is not _PackageSourceSession:
+            return result("UNKNOWN")
+
+        current_sources = tuple(sorted(indexed_sources.items()))
+
+        if _session.source_trees is None:
+            _session.source_trees = current_sources
+        elif (
+            len(_session.source_trees) != len(current_sources)
+            or any(
+                stored_name != name or stored_tree is not tree
+                for (stored_name, stored_tree), (name, tree)
+                in zip(_session.source_trees, current_sources)
+            )
+        ):
+            return result("UNKNOWN")
+
+    # An unsupported package layout cannot establish MODEL_PASS.
+    # Retain fail-fast rejection before CPython compilation.
+    if _session is not None and _session.layout is not None:
+        layout = _session.layout
+    else:
+        try:
+            layout = build_package_layout(indexed_sources)
+        except (TypeError, ValueError):
+            return result("UNKNOWN")
+        if _session is not None:
+            _session.layout = layout
 
     nodes = {node.name: node for node in layout.nodes}
     unsupported_layout = next(
@@ -661,6 +700,12 @@ def evaluate_package_import_order(
     # Fail closed instead of accepting an invalid
     # opaque function definition as MODEL_PASS.
     for indexed_id, tree in indexed_sources.items():
+        if (
+            _session is not None
+            and indexed_id in _session.validated_code
+        ):
+            continue
+
         try:
             compile(
                 tree,
@@ -677,6 +722,9 @@ def evaluate_package_import_order(
         ):
             return result("UNKNOWN", indexed_id)
 
+        if _session is not None:
+            _session.validated_code.add(indexed_id)
+
     logical_sources: dict[str, ast.Module] = {}
     packages: set[str] = set()
 
@@ -722,16 +770,26 @@ def evaluate_package_import_order(
             indexed_sources[indexed_id],
             frozenset(indexed_sources),
         )
-        program = _compile(
-            tree,
-            name,
-            name in packages,
-            typing_guard=typing_guard,
-        )
+        if (
+            _session is not None
+            and name in _session.compiled_steps
+        ):
+            program = _session.compiled_steps[name]
+        else:
+            program = _compile(
+                tree,
+                name,
+                name in packages,
+                typing_guard=typing_guard,
+            )
+            if program is not None and _session is not None:
+                _session.compiled_steps[name] = program
 
         if program is None:
             return result("UNKNOWN", name)
 
+        # The interpreter can splice function body steps into
+        # programs[module]. Never execute a cached list directly.
         programs[name] = list(program)
 
     # A package may prebind a same-named attribute before a later
diff --git a/contextor/core/cycle_semantics/scenarios.py b/contextor/core/cycle_semantics/scenarios.py
index 04590ec..0f15b42 100644
--- a/contextor/core/cycle_semantics/scenarios.py
+++ b/contextor/core/cycle_semantics/scenarios.py
@@ -10,7 +10,11 @@ from collections.abc import Mapping
 from dataclasses import dataclass
 
 from .initialization_model import ImportOrderAssessment, evaluate_flat_import_order
-from .package_model import PackageImportAssessment, evaluate_package_import_order
+from .package_model import (
+    PackageImportAssessment,
+    _PackageSourceSession,
+    evaluate_package_import_order,
+)
 from .model_source_closure import compute_cycle_model_source_closures
 from .model_identity import indexed_to_logical_module, logical_to_indexed_module
 from .package_graph_consistency import assess_package_graph_consistency
@@ -203,9 +207,12 @@ def analyze_cycle_scenarios(
                 ))
                 continue
             model_kind = "REGULAR_PACKAGE"
+            session = _PackageSourceSession()
             assessments = tuple(
                 evaluate_package_import_order(
-                    sources, indexed_to_logical_module(entry),
+                    sources,
+                    indexed_to_logical_module(entry),
+                    _session=session,
                 )
                 for entry in component.members
             )
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index a80736d..6f17c1e 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -335,6 +335,146 @@ def test_warn_5h_regular_layout_still_proves_safe_import(tmp_path):
     assert _actual(tmp_path, source, "pkg")
 
 
+def test_warn_5i_preparation_reused_between_entries(monkeypatch):
+    from contextor.core.cycle_semantics import package_model
+
+    source = {
+        "pkg.__init__": "value=1\nimport pkg.a",
+        "pkg.a": "import pkg\nx=pkg.value",
+    }
+    trees = {
+        name: ast.parse(code)
+        for name, code in source.items()
+    }
+
+    calls = {
+        "layout": 0,
+        "code": 0,
+        "model": 0,
+    }
+
+    original_layout = package_model.build_package_layout
+    original_compile = compile
+    original_model = package_model._compile
+
+    def counted_layout(*args, **kwargs):
+        calls["layout"] += 1
+        return original_layout(*args, **kwargs)
+
+    def counted_compile(*args, **kwargs):
+        calls["code"] += 1
+        return original_compile(*args, **kwargs)
+
+    def counted_model(*args, **kwargs):
+        calls["model"] += 1
+        return original_model(*args, **kwargs)
+
+    monkeypatch.setattr(
+        package_model, "build_package_layout", counted_layout
+    )
+    monkeypatch.setattr(
+        package_model, "compile", counted_compile, raising=False
+    )
+    monkeypatch.setattr(
+        package_model, "_compile", counted_model
+    )
+
+    session = package_model._PackageSourceSession()
+    first = package_model.evaluate_package_import_order(
+        trees, "pkg", _session=session
+    )
+    second = package_model.evaluate_package_import_order(
+        trees, "pkg.a", _session=session
+    )
+
+    assert first.outcome == "MODEL_PASS"
+    assert second.outcome == "MODEL_PASS"
+    assert calls == {
+        "layout": 1,
+        "code": 2,
+        "model": 2,
+    }
+
+
+def test_warn_5i_function_expansion_does_not_mutate_cache():
+    from contextor.core.cycle_semantics import package_model
+
+    trees = {
+        "pkg.__init__": ast.parse(
+            "def load():\n"
+            "    import pkg.child\n"
+            "value=7\n"
+            "load()"
+        ),
+        "pkg.child": ast.parse(
+            "import pkg\n"
+            "x=pkg.value"
+        ),
+    }
+
+    before = {
+        key: ast.dump(tree, include_attributes=True)
+        for key, tree in trees.items()
+    }
+
+    session = package_model._PackageSourceSession()
+    first = package_model.evaluate_package_import_order(
+        trees, "pkg", _session=session
+    )
+    cached_second = package_model.evaluate_package_import_order(
+        trees, "pkg.child", _session=session
+    )
+    fresh_second = package_model.evaluate_package_import_order(
+        trees, "pkg.child"
+    )
+
+    assert first.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "CALL_FUNCTION"
+        for event in first.events
+    )
+    assert cached_second == fresh_second
+    assert {
+        key: ast.dump(tree, include_attributes=True)
+        for key, tree in trees.items()
+    } == before
+
+    assert all(
+        type(program) is tuple
+        for program in session.compiled_steps.values()
+    )
+
+
+def test_warn_5i_session_rejects_different_ast_identity():
+    from contextor.core.cycle_semantics import package_model
+
+    source = {
+        "pkg.__init__": "value=1",
+        "pkg.child": "import pkg",
+    }
+    first_trees = {
+        name: ast.parse(code)
+        for name, code in source.items()
+    }
+    second_trees = {
+        name: ast.parse(code)
+        for name, code in source.items()
+    }
+
+    session = package_model._PackageSourceSession()
+
+    first = package_model.evaluate_package_import_order(
+        first_trees, "pkg", _session=session
+    )
+    reused = package_model.evaluate_package_import_order(
+        second_trees, "pkg", _session=session
+    )
+
+    assert first.outcome == "MODEL_PASS"
+    assert reused.outcome == "UNKNOWN"
+    assert reused.events == ()
+
+
 def test_namespace_ambiguous_external_unknown():
     assert _model(
         {"pkg.sub": "value=7"},
```

## REMAINING_UNKNOWN

- Whether the passive-class failure predates this literal patch and its precise cause: UNKNOWN. No baseline rerun or adjustment was authorized.
- Post-edit source synchronization and active loaded-code adoption: UNKNOWN. Current canonical cycle_semantics remains stale.

## FINAL_IMPLEMENTER_OBSERVATION

The exact patch is applied, but targeted verification is not fully passing. STOP with CONTRACT_CONFLICT for the architect; no independent repair was made.

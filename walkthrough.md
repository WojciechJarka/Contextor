# CONTEXTOR — P1D3-D2B-2-R1 TYPE_ONLY UNSOUND PROMOTION HARDENING

## 1. EXECUTIVE VERDICT

**GO for the scoped D2B-2-R1 repair.** The specified execution-prefix gate prevents both demonstrated dynamic mutations from promoting an executed import to `type_only=True`. The focused eight-module suite completed with `323 passed in 59.53s`. This verdict covers the edited repository source and isolated synthetic tests; it is not active LIVE adoption or general Python runtime certification.

Evidence labels in this report: **DIRECT_EVIDENCE** (observed source, command, test or Git result); **CODE_PATH_PROVED** (current code path and its exact condition); **CONTRACT_PROVED** (an executed contract assertion); **INFERENCE** (bounded conclusion from stated evidence); **UNKNOWN** (not established here).

## 2. INITIAL / FINAL HEAD

- **DIRECT_EVIDENCE** Initial HEAD: `c6965dd02943c72994e6a2c189169f9d0e357623`.
- **DIRECT_EVIDENCE** Final HEAD: `c6965dd02943c72994e6a2c189169f9d0e357623`.
- No commit, push, checkout, reset or clean was run.

## 3. INITIAL / FINAL WORKTREE

- **DIRECT_EVIDENCE** Initial `git status --short` was empty.
- **DIRECT_EVIDENCE** Final changed paths: `contextor/core/symbol_engine/indexer.py`, `tests/test_p1d3_d2b2_type_only.py`, and this overwritten `walkthrough.md` report. The authorized integration test was inspected and executed but not changed.
- No other production, test or documentation file was modified.

## 4. ROOT CAUSE

- **CODE_PATH_PROVED** Before R1, `read_imports` found the D2B-1 marker and iterated matching top-level `ast.If` statements after it. It authorized direct guarded imports without checking statements executed between marker and guard. Thus an effectful expression such as `globals()["TYPE_CHECKING"] = True` or `setattr(typing, "TYPE_CHECKING", True)` could cause ordinary CPython to execute the import while the indexer labeled it type-only.
- **CODE_PATH_PROVED** Worker-cache version 1 stored pre-R1 classifications, so version 1 must be invalidated for this repair to take effect on warm caches.
- **DIRECT_EVIDENCE** Both counterexamples now retain hard `pkg.a -> pkg.b` and `pkg.b -> pkg.a` edges, a real hard SCC, and a failing fresh CPython `pkg.a` import with partially initialized module text.

## 5. EXACT PRODUCTION DIFF

The following is the complete current Git diff for the sole authorized production file. It changes only the cache semantic marker and `read_imports` prefix eligibility, adding the exact private helper from the supplied patch specification.

````diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 73fd28d..5fe3205 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -72 +72 @@ TEST_FACTS_SCHEMA_VERSION = 1
-IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 1
+IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 2
@@ -284,0 +285,55 @@ class AdvancedImportVisitor(ast.NodeVisitor):
+def _safe_typing_guard_prefix_statement(
+    statement: ast.stmt,
+) -> bool:
+    if isinstance(statement, ast.Pass):
+        return True
+
+    if (
+        isinstance(statement, ast.Expr)
+        and isinstance(
+            statement.value,
+            ast.Constant,
+        )
+        and type(statement.value.value) is str
+    ):
+        return True
+
+    if isinstance(statement, ast.Assign):
+        if (
+            len(statement.targets) != 1
+            or not isinstance(
+                statement.targets[0],
+                ast.Name,
+            )
+            or not isinstance(
+                statement.value,
+                ast.Constant,
+            )
+        ):
+            return False
+
+        binding = statement.targets[0].id
+
+        return (
+            binding.isidentifier()
+            and not binding.startswith("__")
+            and binding not in {
+                "TYPE_CHECKING",
+                "typing",
+            }
+            and type(
+                statement.value.value
+            ) in {
+                type(None),
+                bool,
+                int,
+                float,
+                complex,
+                str,
+                bytes,
+            }
+        )
+
+    return False
+
+
@@ -320 +375,3 @@ def read_imports(
-            for statement in tree.body[marker_position + 1:]:
+            matching_guards = [
+                (position, statement)
+                for position, statement in enumerate(tree.body)
@@ -322,2 +379,2 @@ def read_imports(
-                    not isinstance(statement, ast.If)
-                    or not matches_typing_guard(
+                    isinstance(statement, ast.If)
+                    and matches_typing_guard(
@@ -326,0 +384,12 @@ def read_imports(
+                )
+            ]
+            if len(matching_guards) == 1:
+                guard_position, guard_statement = matching_guards[0]
+                if (
+                    guard_position > marker_position
+                    and all(
+                        _safe_typing_guard_prefix_statement(statement)
+                        for statement in tree.body[
+                            marker_position + 1:guard_position
+                        ]
+                    )
@@ -328,16 +397,14 @@ def read_imports(
-                    continue
-
-                for body_statement in statement.body:
-                    if (
-                        not isinstance(body_statement, ast.Import)
-                        or len(body_statement.names) != 1
-                    ):
-                        continue
-                    alias = body_statement.names[0]
-                    parts = alias.name.split(".")
-                    if (
-                        alias.asname is None
-                        and len(parts) > 1
-                        and all(part.isidentifier() for part in parts)
-                    ):
-                        type_only_statement_ids.add(id(body_statement))
+                    for body_statement in guard_statement.body:
+                        if (
+                            not isinstance(body_statement, ast.Import)
+                            or len(body_statement.names) != 1
+                        ):
+                            continue
+                        alias = body_statement.names[0]
+                        parts = alias.name.split(".")
+                        if (
+                            alias.asname is None
+                            and len(parts) > 1
+                            and all(part.isidentifier() for part in parts)
+                        ):
+                            type_only_statement_ids.add(id(body_statement))
````

## 6. STRICT PREFIX ALGORITHM

- **CODE_PATH_PROVED** The existing `recognize_typing_guard(tree, frozenset())` source-local recognizer remains the candidate authority. The AST module requirement and marker lookup by object identity remain.
- **CODE_PATH_PROVED** `matching_guards` enumerates direct top-level `ast.If` nodes whose test matches the recognized guard form. Exactly one is required, and it must follow the marker.
- **CODE_PATH_PROVED** Every statement strictly between marker and guard must pass `_safe_typing_guard_prefix_statement`. Its only accepted shapes are `Pass`, a constant-string expression, or a single plain-name assignment of one permitted literal value to a non-dunder name other than `TYPE_CHECKING` or `typing`.
- **CODE_PATH_PROVED** If any condition fails, no AST import node identity is authorized. If all pass, only direct imports in the guard body with the existing exact dotted single-alias syntax are authorized. The ELSE body, nested constructs, visitor, source occurrence order, `ImportFrom`, `is_local`, resolver and public schemas are unchanged.
- **CONTRACT_PROVED** The 11 added negative prefix variants, original positive NAME/ATTRIBUTE fixtures, and safe-prefix fixture passed.

## 7. GLOBALS COUNTEREXAMPLE

- **DIRECT_EVIDENCE** The isolated fixture uses `globals()["TYPE_CHECKING"] = True` between marker and guard. Its `pkg.b` import occurrence remains present with `type_only=False`; `pkg.a -> pkg.b` is hard, not soft; `pkg.b -> pkg.a` is hard; both modules belong to the hard SCC.
- **DIRECT_EVIDENCE** A fresh isolated CPython subprocess importing `pkg.a` exited nonzero and its stderr contained `partially initialized module`.
- **DIRECT_EVIDENCE** The direct restricted model did not return `MODEL_PASS`, and the SCC scenario did not claim `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`. The test does not demand unsupported dynamic effects to become a proved hazard classification.

## 8. SETATTR COUNTEREXAMPLE

- **DIRECT_EVIDENCE** The isolated fixture uses `setattr(typing, "TYPE_CHECKING", True)` between marker and guard. Its `pkg.b` occurrence remains `type_only=False` and the graph retains the same two hard edges, no `pkg.a -> pkg.b` soft edge, and the real hard SCC.
- **DIRECT_EVIDENCE** Fresh isolated CPython `pkg.a` import exited nonzero with `partially initialized module` in stderr. The direct model and SCC report did not produce a false positive PASS.

## 9. ADDITIONAL NEGATIVE MATRIX

- **DIRECT_EVIDENCE** The new parameterized test passed all 11 supplied variants: `globals().update`, `exec`, `typing.__dict__` mutation, `vars()` mutation, active import before guard, a preceding conditional, call assignment, preceding function, preceding class, preceding `with`, and two direct matching guards.
- **CONTRACT_PROVED** Every indexed `pkg.b` occurrence in those variants remains `type_only=False`, `pkg.a -> pkg.b` remains hard, and no soft edge is attributed to it.
- No CPython execution outcome is claimed for variants with undefined synthetic names or context managers.

## 10. SAFE PREFIX REGRESSION

- **DIRECT_EVIDENCE** `constant = 1` followed by `pass` between marker and the single positive guard keeps the guarded `pkg.b` occurrence `type_only=True`. The graph has soft `pkg.a -> pkg.b`, no hard edge in that direction, hard `pkg.b -> pkg.a`, and no `pkg.a/pkg.b` hard SCC. Fresh isolated CPython `pkg.a` import succeeds.
- **DIRECT_EVIDENCE** The original simple NAME and ATTRIBUTE positive fixtures remain in the focused integration suite and pass.

## 11. MULTIPLE GUARD REJECTION

- **CODE_PATH_PROVED** `len(matching_guards) == 1` is required before collecting any import node identity.
- **DIRECT_EVIDENCE** The two-direct-guard variant in the negative matrix retains its guarded import as hard and produces no `pkg.a -> pkg.b` soft edge.

## 12. SAME-TARGET HARD DOMINANCE

- **DIRECT_EVIDENCE** The existing mixed fixture passed without changes: it checks two ordered occurrences with `[True, False]`, a soft edge from the guarded occurrence, and a hard edge from the normal import to the same target. The real hard SCC survives. Original-worker P0/P1B assertions were not weakened.

## 13. ELSE BEHAVIOR

- **DIRECT_EVIDENCE** Existing `D2B_ELSE_HAZARD` and `D2B_ELSE_SAFE` integration tests passed. ELSE imports remain hard, and the hazard/safe source-order differential, surviving SCC evidence, manifest and receipt tests continue to run on genuine components.
- **CODE_PATH_PROVED** The R1 selection inspects only `guard_statement.body`; it never authorizes the ELSE body.

## 14. CACHE VERSION MIGRATION 1 -> 2

- **CODE_PATH_PROVED** Only `IMPORT_CLASSIFICATION_SEMANTICS_VERSION` changed from integer 1 to integer 2. The worker-cache key stays `import_classification_semantics_version`.
- **CODE_PATH_PROVED** Existing validation rejects missing, non-exact-int or unequal values before using cached imports. Source SHA validation and the already acquired source snapshot path remain intact; no source reread or public schema change was added.
- **DIRECT_EVIDENCE** Stale-marker tests for absent, 0 and 1 pass, including a version-1 cache rewrite to version 2. A warm version-2 cache still matches the cold classification and graph.

## 15. STALE FORGED CACHE REPLAY

- **DIRECT_EVIDENCE** The isolated test first indexes the globals-mutation fixture under version 2, edits only its synthetic `pkg/a.py` worker-cache data to forge `type_only=True` with semantic version 1, then reindexes unchanged source.
- **DIRECT_EVIDENCE** The replayed occurrence is `type_only=False`, both hard SCC edges survive, and the cache entry is rewritten as version 2 with `type_only=False`. No active/user cache directory was changed.

## 16. COLD / WARM PARITY

- **DIRECT_EVIDENCE** The existing cold/warm worker-cache regression passed with the version assertion updated to 2. It compares the ordered import signature, `type_only` values, hard and soft graph signatures and SCC members for identical synthetic bytes.

## 17. INLINE / PROCESS-POOL PARITY

- **DIRECT_EVIDENCE** Both primary dynamic-mutation fixtures were indexed in isolated inline and process-pool modes. Their ordered `ImportRef` signatures, `type_only`, hard/soft edges and SCC topology match. The test explicitly clears `CONTEXTOR_DISABLE_PROCESS_POOL` for the pool path; the current indexer selects the inline path only when that variable equals `1`.
- **DIRECT_EVIDENCE** The existing positive parity test passed. Repository-wide shadow-veto parity now covers both `typing.py` and `typing/__init__.py`; both passed in the pool path.

## 18. SCC TOPOLOGY

- **DIRECT_EVIDENCE** Globals and setattr dynamic-mutation fixtures each have the hard SCC `{pkg.a, pkg.b}`. The safe-prefix fixture and original inactive NAME/ATTRIBUTE fixtures have no such hard SCC. The mixed active/type-only fixture retains it; ELSE fixtures retain it.
- **INFERENCE** This is a topology result for the constructed source fixtures and current indexer/graph code, not a general runtime-safety conclusion.

## 19. CPYTHON DIFFERENTIAL

- **DIRECT_EVIDENCE** The two primary counterexamples were imported in fresh CPython subprocesses through the existing isolated synthetic harness. Each `pkg.a` import failed and exposed partially initialized module text. The safe-prefix `pkg.a` import succeeded.
- **CONTRACT_PROVED** Unsupported dynamic calls were not modeled as proven safe; the test requires only the absence of false `MODEL_PASS` and false all-fresh-member PASS.

## 20. NO-SCC HANDLING

- **DIRECT_EVIDENCE** Existing D2B-2 NAME/ATTRIBUTE tests in the focused suite continue to require `analyze_cycle_scenarios(...).components == ()`, empty P0/source-bound evidence, `NO_CYCLIC_COMPONENTS` from the original-worker planner, no prepared manifest and no persisted receipt for the dissolved hard SCC.
- **DIRECT_EVIDENCE** The dynamic counterexamples do not enter that no-SCC path because their hard SCC remains. No planner or evidence production code was changed.

## 21. P0/P1B REGRESSIONS

- **DIRECT_EVIDENCE** Existing focused tests for the mixed and ELSE surviving SCCs still exercise genuine original-worker capture, P0 `DECLARED_INPUTS_CONSISTENT`, P1B `BYTE_AST_CONSISTENT_NON_ATOMIC`, and forged-event P1B `MODEL_REPLAY_MISMATCH`.
- **CODE_PATH_PROVED** R1 changes neither the P0/P1B implementation nor their schema/event contracts. The dynamic counterexamples are not given fabricated positive P0/P1B assessments.

## 22. ORIGINAL-WORKER MANIFEST V2

- **DIRECT_EVIDENCE** The existing original-worker preparation tests ran in the focused suite for surviving SCCs and passed. The safe-only former SCC still has no synthetic manifest. No manifest schema or original-worker capture path was edited.

## 23. OFFICIAL ISOLATED FULL / RECEIPT V2

- **DIRECT_EVIDENCE** The focused suite executed the existing synthetic official facade FULL/publication/receipt tests. `D2B_ELSE_SAFE` still verifies prepared manifest v2, isolated publication and receipt v2 for a surviving SCC; the dissolved NAME-safe fixture still checks no persisted receipt.
- **UNKNOWN** These isolated tests do not establish active Contextor LIVE adoption or active service receipt behavior. No FULL was run on the active repository.

## 24. FOCUSED PYTEST RESULTS

- **DIRECT_EVIDENCE** Exact final result: `323 passed in 59.53s`, exit code 0, for the eight named focused modules in §25.
- No test was deleted or skipped for this repair. No global pytest was run.

## 25. EXACT COMMANDS / EXIT CODES

Working directory: `C:\Temp\Contextor_Repo`. Commands were executed using the repository virtual environment.

```text
& .\.venv\Scripts\python.exe -m py_compile contextor/core/symbol_engine/indexer.py
exit_code=0

& .\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_d2b2_type_only.py tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py
exit_code=0
result=323 passed in 59.53s

git diff --check
exit_code=0
```

The final `git diff --check` was run after report generation; Git emitted line-ending notices but reported no whitespace errors.

## 26. FILES_CHANGED

1. `contextor/core/symbol_engine/indexer.py` — authorized production change.
2. `tests/test_p1d3_d2b2_type_only.py` — authorized test change.
3. `walkthrough.md` — required report overwritten. Its self-diff is excluded to avoid recursive report content.

`tests/test_p1d3_package_cycle_integration.py` was read and tested, not changed. No other source, test or docs file changed.

## 27. FULL ACTUAL_DIFF

The following complete zero-context Git diff contains every added and removed line for both changed source/test files. Section 5 also includes the full production diff. The report's self-diff is excluded.

````diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 73fd28d..5fe3205 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -72 +72 @@ TEST_FACTS_SCHEMA_VERSION = 1
-IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 1
+IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 2
@@ -284,0 +285,55 @@ class AdvancedImportVisitor(ast.NodeVisitor):
+def _safe_typing_guard_prefix_statement(
+    statement: ast.stmt,
+) -> bool:
+    if isinstance(statement, ast.Pass):
+        return True
+
+    if (
+        isinstance(statement, ast.Expr)
+        and isinstance(
+            statement.value,
+            ast.Constant,
+        )
+        and type(statement.value.value) is str
+    ):
+        return True
+
+    if isinstance(statement, ast.Assign):
+        if (
+            len(statement.targets) != 1
+            or not isinstance(
+                statement.targets[0],
+                ast.Name,
+            )
+            or not isinstance(
+                statement.value,
+                ast.Constant,
+            )
+        ):
+            return False
+
+        binding = statement.targets[0].id
+
+        return (
+            binding.isidentifier()
+            and not binding.startswith("__")
+            and binding not in {
+                "TYPE_CHECKING",
+                "typing",
+            }
+            and type(
+                statement.value.value
+            ) in {
+                type(None),
+                bool,
+                int,
+                float,
+                complex,
+                str,
+                bytes,
+            }
+        )
+
+    return False
+
+
@@ -320 +375,3 @@ def read_imports(
-            for statement in tree.body[marker_position + 1:]:
+            matching_guards = [
+                (position, statement)
+                for position, statement in enumerate(tree.body)
@@ -322,2 +379,2 @@ def read_imports(
-                    not isinstance(statement, ast.If)
-                    or not matches_typing_guard(
+                    isinstance(statement, ast.If)
+                    and matches_typing_guard(
@@ -326,0 +384,12 @@ def read_imports(
+                )
+            ]
+            if len(matching_guards) == 1:
+                guard_position, guard_statement = matching_guards[0]
+                if (
+                    guard_position > marker_position
+                    and all(
+                        _safe_typing_guard_prefix_statement(statement)
+                        for statement in tree.body[
+                            marker_position + 1:guard_position
+                        ]
+                    )
@@ -328,16 +397,14 @@ def read_imports(
-                    continue
-
-                for body_statement in statement.body:
-                    if (
-                        not isinstance(body_statement, ast.Import)
-                        or len(body_statement.names) != 1
-                    ):
-                        continue
-                    alias = body_statement.names[0]
-                    parts = alias.name.split(".")
-                    if (
-                        alias.asname is None
-                        and len(parts) > 1
-                        and all(part.isidentifier() for part in parts)
-                    ):
-                        type_only_statement_ids.add(id(body_statement))
+                    for body_statement in guard_statement.body:
+                        if (
+                            not isinstance(body_statement, ast.Import)
+                            or len(body_statement.names) != 1
+                        ):
+                            continue
+                        alias = body_statement.names[0]
+                        parts = alias.name.split(".")
+                        if (
+                            alias.asname is None
+                            and len(parts) > 1
+                            and all(part.isidentifier() for part in parts)
+                        ):
+                            type_only_statement_ids.add(id(body_statement))
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 00baa48..0a4811a 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -12,0 +13 @@ from contextor.core.analysis.cache_manager import CacheManager
+from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
@@ -18 +19 @@ from contextor.core.symbol_engine import indexer
-from tests.cycle_semantics_lab import write_synthetic_repository
+from tests.cycle_semantics_lab import run_synthetic_import, write_synthetic_repository
@@ -31,0 +33,93 @@ D2B_NAME_SAFE = {
+D2B2_R1_GLOBALS_MUTATION = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        'globals()["TYPE_CHECKING"] = True\n'
+        "if TYPE_CHECKING:\n"
+        "    import pkg.b\n"
+        "value = 1\n"
+    ),
+    "pkg/b.py": "from pkg.a import value\n",
+}
+
+D2B2_R1_SETATTR_MUTATION = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "import typing\n"
+        'setattr(typing, "TYPE_CHECKING", True)\n'
+        "if typing.TYPE_CHECKING:\n"
+        "    import pkg.b\n"
+        "value = 1\n"
+    ),
+    "pkg/b.py": "from pkg.a import value\n",
+}
+
+D2B2_R1_PREFIX_NEGATIVES = [
+    (
+        "globals-update",
+        "from typing import TYPE_CHECKING\n"
+        'globals().update({"TYPE_CHECKING": True})\n'
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+    ),
+    (
+        "exec-rebinding",
+        "from typing import TYPE_CHECKING\n"
+        'exec("TYPE_CHECKING = True")\n'
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+    ),
+    (
+        "typing-dict-rebinding",
+        "import typing\n"
+        'typing.__dict__["TYPE_CHECKING"] = True\n'
+        "if typing.TYPE_CHECKING:\n    import pkg.b\n",
+    ),
+    (
+        "vars-rebinding",
+        "from typing import TYPE_CHECKING\n"
+        'vars()["TYPE_CHECKING"] = True\n'
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+    ),
+    (
+        "active-import-before-guard",
+        "from typing import TYPE_CHECKING\n"
+        "import pkg.b\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+    ),
+    (
+        "conditional-before-guard",
+        "from typing import TYPE_CHECKING\n"
+        "if True:\n    pass\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+    ),
+    (
+        "call-assignment-before-guard",
+        "from typing import TYPE_CHECKING\n"
+        "value = unknown()\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+    ),
+    (
+        "function-before-guard",
+        "from typing import TYPE_CHECKING\n"
+        "def mutate():\n    pass\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+    ),
+    (
+        "class-before-guard",
+        "from typing import TYPE_CHECKING\n"
+        "class Mutator:\n    pass\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+    ),
+    (
+        "with-before-guard",
+        "from typing import TYPE_CHECKING\n"
+        "with context:\n    pass\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+    ),
+    (
+        "multiple-matching-guards",
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    pass\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+    ),
+]
+
@@ -257 +351 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
-    assert cached["import_classification_semantics_version"] == 1
+    assert cached["import_classification_semantics_version"] == 2
@@ -274 +368,3 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
-@pytest.mark.parametrize("stored_version", [None, 0], ids=["absent", "old"])
+@pytest.mark.parametrize(
+    "stored_version", [None, 0, 1], ids=["absent", "version-0", "version-1"],
+)
@@ -317 +413 @@ def test_stale_import_classification_cache_reparses_same_snapshot(
-    assert rewritten["import_classification_semantics_version"] == 1
+    assert rewritten["import_classification_semantics_version"] == 2
@@ -430,0 +527,4 @@ def test_inline_and_process_pool_classification_parity(
+@pytest.mark.parametrize(
+    "shadow_path", ["typing.py", "typing/__init__.py"],
+    ids=["module", "package"],
+)
@@ -432 +532 @@ def test_inline_and_process_pool_typing_shadow_veto_parity(
-    tmp_path, isolated_dirs, monkeypatch,
+    tmp_path, isolated_dirs, monkeypatch, shadow_path,
@@ -436 +536 @@ def test_inline_and_process_pool_typing_shadow_veto_parity(
-        "typing.py": "pass\n",
+        shadow_path: "pass\n",
@@ -489,0 +590,171 @@ def test_unsupported_imports_remain_non_type_only_and_hard(
+
+def _assert_dynamic_mutation_retains_hard_scc(root):
+    indexed, graph = _index_graph(root)
+    guarded_imports = [
+        item for item in indexed.modules["pkg.a"].imports
+        if item.module == "pkg.b" and not item.is_from_import
+    ]
+    assert len(guarded_imports) == 1
+    assert guarded_imports[0].type_only is False
+    assert graph.hard_edges["pkg.a"] == {"pkg.b"}
+    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
+    assert "pkg.b" not in graph.soft_edges["pkg.a"]
+    assert any(
+        set(members) == {"pkg.a", "pkg.b"}
+        for members in _scc_signature(indexed, graph)
+    )
+
+    trees = {
+        module_id: ast.parse(Path(module.absolute_path).read_text(encoding="utf-8"))
+        for module_id, module in indexed.modules.items()
+    }
+    modeled = evaluate_package_import_order(trees, "pkg.a")
+    assert modeled.outcome != "MODEL_PASS"
+    scenarios = analyze_cycle_scenarios(graph.hard_edges, trees)
+    assert all(
+        component.classification != "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        for component in scenarios.components
+        if {"pkg.a", "pkg.b"}.issubset(set(component.members))
+    )
+
+    actual = run_synthetic_import(root, "pkg.a")
+    assert actual.returncode != 0
+    assert "partially initialized module" in actual.stderr
+    return indexed, graph
+
+
+def test_d2b2_r1_globals_rebinding_keeps_hard_scc(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B2_R1_GLOBALS_MUTATION,
+    )
+    _assert_dynamic_mutation_retains_hard_scc(root)
+
+
+def test_d2b2_r1_setattr_mutation_keeps_hard_scc(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B2_R1_SETATTR_MUTATION,
+    )
+    _assert_dynamic_mutation_retains_hard_scc(root)
+
+
+@pytest.mark.parametrize(
+    "case,source", D2B2_R1_PREFIX_NEGATIVES,
+    ids=[item[0] for item in D2B2_R1_PREFIX_NEGATIVES],
+)
+def test_d2b2_r1_effectful_prefixes_keep_hard_edge(
+    tmp_path, isolated_dirs, case, source,
+):
+    fixture = {
+        "pkg/__init__.py": "pass\n",
+        "pkg/a.py": source,
+        "pkg/b.py": "from pkg.a import value\n",
+    }
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    indexed, graph = _index_graph(root)
+    guarded_imports = [
+        item for item in indexed.modules["pkg.a"].imports
+        if item.module == "pkg.b" and not item.is_from_import
+    ]
+    assert guarded_imports
+    assert all(item.type_only is False for item in guarded_imports)
+    assert "pkg.b" in graph.hard_edges["pkg.a"]
+    assert "pkg.b" not in graph.soft_edges["pkg.a"]
+
+
+def test_d2b2_r1_safe_prefix_remains_type_only(tmp_path, isolated_dirs):
+    fixture = {
+        "pkg/__init__.py": "pass\n",
+        "pkg/a.py": (
+            "from typing import TYPE_CHECKING\n"
+            "constant = 1\n"
+            "pass\n"
+            "if TYPE_CHECKING:\n"
+            "    import pkg.b\n"
+            "value = 1\n"
+        ),
+        "pkg/b.py": "from pkg.a import value\n",
+    }
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    indexed, graph = _index_graph(root)
+    guarded_imports = [
+        item for item in indexed.modules["pkg.a"].imports
+        if item.module == "pkg.b" and not item.is_from_import
+    ]
+    assert len(guarded_imports) == 1
+    assert guarded_imports[0].type_only is True
+    assert graph.soft_edges["pkg.a"] == {"pkg.b"}
+    assert "pkg.b" not in graph.hard_edges["pkg.a"]
+    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
+    assert not any(
+        {"pkg.a", "pkg.b"}.issubset(set(members))
+        for members in _scc_signature(indexed, graph)
+    )
+    assert run_synthetic_import(root, "pkg.a").returncode == 0
+
+
+def test_d2b2_r1_forged_version_one_cache_is_reparsed(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B2_R1_GLOBALS_MUTATION,
+    )
+    first, first_graph = _index_graph(root)
+    assert "pkg.b" in first_graph.hard_edges["pkg.a"]
+    assert any(
+        item.module == "pkg.b" and not item.type_only
+        for item in first.modules["pkg.a"].imports
+    )
+
+    source = root / "pkg" / "a.py"
+    cached = _cache_data(root, source)
+    assert cached["import_classification_semantics_version"] == 2
+    forged_imports = [
+        item for item in cached["imports"] if item["module"] == "pkg.b"
+    ]
+    assert len(forged_imports) == 1
+    forged_imports[0]["type_only"] = True
+    cached["import_classification_semantics_version"] = 1
+    CacheManager(str(root)).set(source, cached)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    replayed, graph = _index_graph(root)
+    assert any(
+        item.module == "pkg.b" and not item.type_only
+        for item in replayed.modules["pkg.a"].imports
+    )
+    assert graph.hard_edges["pkg.a"] == {"pkg.b"}
+    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
+    assert any(
+        set(members) == {"pkg.a", "pkg.b"}
+        for members in _scc_signature(replayed, graph)
+    )
+    rewritten = _cache_data(root, source)
+    assert rewritten["import_classification_semantics_version"] == 2
+    assert next(
+        item for item in rewritten["imports"] if item["module"] == "pkg.b"
+    )["type_only"] is False
+
+
+@pytest.mark.parametrize(
+    "fixture", [D2B2_R1_GLOBALS_MUTATION, D2B2_R1_SETATTR_MUTATION],
+    ids=["globals", "setattr"],
+)
+def test_d2b2_r1_dynamic_mutation_inline_process_pool_parity(
+    tmp_path, isolated_dirs, monkeypatch, fixture,
+):
+    inline_root = write_synthetic_repository(tmp_path / "inline", fixture)
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    inline_index, inline_graph = _index_graph(inline_root)
+
+    pool_root = write_synthetic_repository(tmp_path / "pool", fixture)
+    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
+    pool_index, pool_graph = _index_graph(pool_root)
+
+    assert _import_signature(pool_index) == _import_signature(inline_index)
+    assert _graph_signature(pool_index, pool_graph) == (
+        _graph_signature(inline_index, inline_graph)
+    )
+    assert pool_graph.hard_edges["pkg.a"] == {"pkg.b"}
+    assert pool_graph.hard_edges["pkg.b"] == {"pkg.a"}
+    assert "pkg.b" not in pool_graph.soft_edges["pkg.a"]
+
````

## 28. CONTRACT CONFLICTS

- **DIRECT_EVIDENCE** No supplied literal patch requirement conflicted with the current `read_imports` anchor or cache marker. The code still uses the D2B-1 recognizer and existing visitor/finalizer/resolver contracts.
- **DIRECT_EVIDENCE** No acceptance gate failed in the focused validation. No out-of-scope production edit was made.

## 29. UNSUPPORTED / UNKNOWN

- **UNKNOWN** Active MCP/LIVE process code adoption: not inspected or claimed. Contextor MCP reads were used before editing for architecture/source discovery; no active mutation tool was invoked.
- **UNKNOWN** Global-suite result; the user prohibited global pytest.
- **UNKNOWN** General Python runtime behavior beyond the explicit synthetic fixtures and restricted package model.
- Dynamic rebinding calls remain unsupported by the restricted execution model; their hard graph edges are retained without inventing a hazard-proof P0/P1B result.

## 30. FINAL GO / PARTIAL / NO_GO

**GO — D2B-2-R1 scoped repair.** All 22 supplied acceptance gates are met by the implemented conditions, executed focused assertions and final file scope:

| Gate | Result | Evidence |
| --- | --- | --- |
| G01 globals mutation cannot promote | PASS | Direct dynamic fixture, hard SCC and CPython failure |
| G02 setattr mutation cannot promote | PASS | Direct dynamic fixture, hard SCC and CPython failure |
| G03 other effectful prefixes fail closed | PASS | 11-case negative matrix |
| G04 multiple guards rejected | PASS | Two-guard negative case |
| G05 passive prefix remains eligible | PASS | Constant-assignment/pass positive fixture |
| G06 NAME/ATTRIBUTE positives remain | PASS | Existing integration tests |
| G07 normal import remains hard | PASS | Existing mixed/negative tests |
| G08 mixed classifications retained | PASS | Existing mixed test `[True, False]` |
| G09 ELSE remains hard | PASS | Existing ELSE tests |
| G10 dynamic hard SCCs retained | PASS | Primary fixtures and parity tests |
| G11 CPython hazard detected | PASS | Fresh subprocess failures with required stderr |
| G12 no false model PASS | PASS | Direct model/scenario assertions |
| G13 version-1 cache stale | PASS | Parameterized stale-marker test |
| G14 cold/warm version-2 parity | PASS | Existing warm-cache test updated |
| G15 forged version-1 cache rejected | PASS | Forged cache replay regression |
| G16 inline/process-pool parity | PASS | Both primary fixture parity tests |
| G17 typing shadow veto retained | PASS | Module/package shadow tests and parity |
| G18 soft-only dissolution remains bounded | PASS | Existing no-SCC planner/manifest/receipt tests |
| G19 surviving SCC P0/P1B/receipt v2 | PASS | Existing genuine SCC regressions |
| G20 D1/D2A/D2B-1/D2B-2 focused regressions | PASS | Eight-module focused run, 323 passed |
| G21 authorized production scope | PASS | Final Git status/diff paths |
| G22 no active FULL/LIVE mutation | PASS | Only read-only MCP discovery and isolated synthetic tests; no active mutation command |

The GO classification is limited to this stage. Stop after D2B-2-R1 and await a separate explicit `proceduj` for any later stage.

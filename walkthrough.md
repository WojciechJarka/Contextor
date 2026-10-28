# CONTEXTOR — P1D3-D2B-3 SOURCE-BOUND TYPE_ONLY / HARD-EDGE CONSISTENCY

## 1. IMPLEMENTER OBSERVATION

The specified shared AST selector and independent source checker logic were implemented in the authorized files. The requested focused command completed with `392 passed in 71.02s (0:01:11)`. These are implementation and test observations. Architectural acceptance, including any GO/PARTIAL/NO_GO decision, belongs to ChatGPT.

Evidence labels: **DIRECT_EVIDENCE** = observed source/tool/test/Git result; **CODE_PATH_PROVED** = exact current implementation path; **CONTRACT_PROVED** = executed contract assertion; **INFERENCE** = bounded conclusion; **UNKNOWN** = not established.

## 2. INITIAL / FINAL HEAD

- **DIRECT_EVIDENCE** Initial HEAD: `807267a7ef898a96493b1774b2cb5c89344cb655`.
- **DIRECT_EVIDENCE** Final HEAD: `807267a7ef898a96493b1774b2cb5c89344cb655`.
- No Git commit, push, checkout, reset or clean was run.

## 3. WORKTREE STATUS

- **DIRECT_EVIDENCE** Initial `git status --short` was empty.
- **DIRECT_EVIDENCE** Final changes are the three authorized production files, the authorized integration test and this overwritten `walkthrough.md`. The final exact status appears in §30.
- No other source, test or documentation file was changed.

## 4. ROOT CAUSE

- **CODE_PATH_PROVED** Before this edit, `assess_package_graph_consistency` visited an `ast.Import` under a recognized `TYPE_CHECKING` guard and added its resolved target to the expected hard-edge set. The indexer already classified the same supported import as soft. For a real hard SCC with an independent soft side target, that made the exact hard graph look mismatched.
- **CODE_PATH_PROVED** The repair reconstructs eligibility from the caller-provided source AST and indexed identity domain, using the shared pure selector plus source-available parent initializer passivity. It does not accept caller soft edges or worker cache flags as checker evidence.

## 5. SHARED POLICY EXTRACTION

- **CODE_PATH_PROVED** The existing bodies and signatures of `_safe_typing_guard_prefix_statement`, `_typing_guard_passive_initializer` and `_typing_guard_parent_initializers` were moved from `indexer.py` to `typing_guard.py` after `recognize_typing_guard`. The indexer imports them back by the same exact names; there are no wrappers or duplicate implementations.
- **CODE_PATH_PROVED** `type_only_candidate_statement_ids` is now the sole source-local candidate selector. The indexer calls it with `frozenset()`; the checker calls it with the complete indexed ID domain.
- The exact added helper bodies and removed indexer bodies are included in §32.

## 6. EXACT HELPER CODE

- **DIRECT_EVIDENCE** The complete literal code of all four helpers appears in the full `typing_guard.py` diff in §32, including their signatures, early returns and node-identity selection. The three relocated bodies match their prior indexer bodies.
- **CODE_PATH_PROVED** The new selector uses the existing recognizer, exact marker identity, exactly one matching direct top-level guard, the unchanged safe-prefix predicate, direct single-alias dotted imports in the guard body, and returns `frozenset[int]` of AST node IDs. It does not recurse into ELSE/nested constructs or evaluate source.

## 7. INDEXER SEMANTIC PARITY

- **CODE_PATH_PROVED** `read_imports` replaced only the old candidate-selection block with the specified call to `type_only_candidate_statement_ids(tree, frozenset())`. `AdvancedImportVisitor`, the visitor invocation, `ImportRef`, worker results, source fingerprints and the R2 parent finalizer were not changed.
- **DIRECT_EVIDENCE** The existing D2B-2, R1 and R2 tests in the focused suite all passed; the shared selector preserved their exercised classifications.

## 8. CACHE V3 PRESERVATION

- **CODE_PATH_PROVED** `IMPORT_CLASSIFICATION_SEMANTICS_VERSION` remains exactly 3. The `typing_guard_initializer_passive` worker cache fact and its validation are unchanged. No schema or manifest version was edited.
- **DIRECT_EVIDENCE** Existing cold/warm, stale cache, malformed current cache, forged stale cache, inline/process-pool and original-worker R2 regressions ran in the passing focused suite. No v3 cache test failed.

## 9. SOURCE CHECKER LOGIC

- **CODE_PATH_PROVED** After the existing `typing_guard` assignment, the checker independently computes `type_only_ids` from `sources[module_id]` and `indexed`, then requires every parent AST to be present as `ast.Module` and pass `_typing_guard_passive_initializer`. A failed parent proof clears the candidate set.
- **CODE_PATH_PROVED** Only the existing `ast.Import` expected-hard-edge add is conditioned on `id(node) not in type_only_ids`. Its target resolution, identifier checks, regular-parent checks, self-edge suppression, `ImportFrom` handling, reexport rules and final exact hard-edge comparison remain unchanged. The failure reason remains `GRAPH_SOURCE_IMPORT_MISMATCH`.

## 10. AST NODE IDENTITY

- **CODE_PATH_PROVED** Exemption is keyed to the specific AST `ast.Import` statement object in the provided source tree. The selector and `ast.walk` see the same node identities in one checker call.
- **DIRECT_EVIDENCE** The existing mixed same-target fixture now asserts checker `CONSISTENT`. Negative N14 adds a separate active import of the same target and verifies that removal of its required hard edge is rejected with `GRAPH_SOURCE_IMPORT_MISMATCH`. No target-wide blanket exemption was added.

## 11. PARENT SOURCE PASSIVITY

- **CODE_PATH_PROVED** The checker reads parent `ast.Module` objects only from its supplied `sources` mapping. It does not read the filesystem, worker cache, `Module.ast_tree`, or runtime `typing` module. Missing or nonpassive parent AST clears all candidate IDs for the module.
- **DIRECT_EVIDENCE** Three independent parent variants were tested: attribute mutation, `setattr`, and `exec`. Each pure passivity call returned False, canonical indexing kept `pkg.c` hard, and a direct checker call over the same ASTs rejected a graph with that hard edge removed.

## 12. NAME POSITIVE FIXTURE

- **DIRECT_EVIDENCE** `D2B3_TYPED_SIDE_NAME` exactly matches the instructed source bytes. Its guarded `pkg.c` occurrence is `type_only=True`, normal `pkg.b` occurrence is False, checker status is `CONSISTENT` with reason None, the real hard SCC and model assertions pass, and fresh CPython imports of both `pkg.a` and `pkg.b` succeed.

## 13. ATTRIBUTE POSITIVE FIXTURE

- **DIRECT_EVIDENCE** `D2B3_TYPED_SIDE_ATTRIBUTE` uses `import typing` and `if typing.TYPE_CHECKING` with the instructed remaining source. It passes the same checker, SCC, source evidence, model and CPython assertions. Its hard and soft graphs are directly compared against the NAME fixture and are identical.

## 14. HARD / SOFT GRAPH

- **DIRECT_EVIDENCE** Both positive fixtures have exactly:

```text
hard: pkg.__init__ -> {}; pkg.a -> {pkg.b}; pkg.b -> {pkg.a}; pkg.c -> {}
soft: pkg.__init__ -> {}; pkg.a -> {pkg.c}; pkg.b -> {}; pkg.c -> {}
```

- The checker accepts this exact hard graph without requiring the supported soft-only `pkg.c` edge as hard.

## 15. REAL SCC TOPOLOGY

- **DIRECT_EVIDENCE** The positive graph has the genuine hard SCC `{pkg.a, pkg.b}`. The scenario is `REGULAR_PACKAGE`, `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`, `COMPLETE_FRESH_MEMBER_ENTRIES`. No model `START_IMPORT` event targets `pkg.c`.
- **INFERENCE** This is restricted source/model behavior for the explicit fixtures, not general runtime safety.

## 16. HARD SOURCE CLOSURE

- **DIRECT_EVIDENCE** The positive fixture's `evidence_source_modules` is exactly `(pkg.__init__, pkg.a, pkg.b)`; `pkg.c` is absent. The original-worker planner selected exactly that set, and real capture/parsed snapshots contain exactly that set.
- **CODE_PATH_PROVED** `model_source_closure.py` and source manifest schemas were not edited. The soft target was not inserted into the hard-reachable closure to obtain a passing checker result.

## 17. SAME-TARGET HARD DOMINANCE

- **DIRECT_EVIDENCE** The existing D2B-2 mixed fixture retains ordered import flags `[True, False]`, hard and soft `pkg.a -> pkg.b`, and a real hard SCC. The modified test additionally requires checker `CONSISTENT`. Its existing original-worker P0/P1B assertions still run and pass.

## 18. FORGED GRAPH NEGATIVES

- **DIRECT_EVIDENCE** Against unchanged positive NAME AST closure, F01 removes hard `pkg.a -> pkg.b` and F02 adds hard `pkg.a -> pkg.c`. Both direct checker calls return `INDETERMINATE` with exact reason `GRAPH_SOURCE_IMPORT_MISMATCH`.
- No scenario PASS was claimed from either fabricated graph.

## 19. UNSUPPORTED MATRIX

- **DIRECT_EVIDENCE** Fifteen isolated N01–N15 fixtures ran. They cover absent/aliased marker, negated guard, nested import, `ImportFrom`, aliased direct import, multiple guards, globals/setattr prefix mutation, nonpassive/missing parent, local `typing.py`/`typing/__init__.py`, active same-target import and ELSE import.
- For unsupported guarded direct imports, canonical `pkg.c` remains hard and `type_only=False`. N05 retains an unpromoted `ImportFrom`; N14 retains one soft guarded and one hard active occurrence. In every case a caller graph with a required hard edge removed was not accepted as `CONSISTENT`. N14 specifically returned `GRAPH_SOURCE_IMPORT_MISMATCH`.
- **UNKNOWN** Some unsupported structures may return a different fail-closed reason before the final hard-edge comparison. The test does not claim every negative is a supported package model or SCC.

## 20. PARENT NEGATIVE MATRIX

- **DIRECT_EVIDENCE** P01 parent typing attribute mutation, P02 parent `setattr`, and P03 parent `exec` each fail the shared passivity predicate. Canonical indexing keeps guarded `pkg.c` hard. Direct checker assessment of the module ASTs with `pkg.c` removed from the hard graph returns `INDETERMINATE` / `GRAPH_SOURCE_IMPORT_MISMATCH`. Scenario tests do not permit a false all-fresh-member PASS.
- No dynamic parent initializer was converted into positive P0/P1B evidence.

## 21. CPYTHON DIFFERENTIAL

- **DIRECT_EVIDENCE** The positive NAME and ATTRIBUTE tests executed only their isolated synthetic sources through fresh CPython subprocesses. `pkg.a` and `pkg.b` imports succeeded for both. The restricted model emitted no `START_IMPORT` event for soft `pkg.c`.
- CPython execution outcomes are not claimed for intentionally unsupported negative fixtures.

## 22. P0 GENUINE EVIDENCE

- **DIRECT_EVIDENCE** For each positive fixture's real hard SCC, the test uses captured original-worker fingerprints and source-bound evidence. The P0 result is `DECLARED_INPUTS_CONSISTENT`.
- P0 implementation was not modified.

## 23. P1B SOURCE REPLAY

- **DIRECT_EVIDENCE** For the same real SCCs, P1B receives captured original worker `SourceSnapshot` objects and returns `BYTE_AST_CONSISTENT_NON_ATOMIC`.
- P1B implementation was not modified; this remains non-atomic replay evidence.

## 24. FORGED P1B REPLAY

- **DIRECT_EVIDENCE** The existing forged marker-event regression in the focused integration suite ran and passed. Its P0 declared-input result remains consistent while independent P1B replay rejects the forged event as `MODEL_REPLAY_MISMATCH`.

## 25. ORIGINAL-WORKER REINDEX

- **DIRECT_EVIDENCE** The positive helper uses the existing planner and second real index/capture. Selected source snapshot IDs match the actual hard-source closure. A canonical graph rebuilt from captured modules and canonical reexport facts has hard and soft edges exactly equal to the initial graph.
- No result objects or source proofs were fabricated.

## 26. OFFICIAL ISOLATED FULL

- **DIRECT_EVIDENCE** The new `test_p1d3_d2b3_official_isolated_full_receipt` ran against only `D2B3_TYPED_SIDE_NAME` in the existing isolated `_official_live` harness. It checked a real hard SCC, real selected original-worker capture, `PREPARED_UNPUBLISHED_NON_ATOMIC`, successful isolated publication and the verified receipt.
- No active Contextor repository FULL or active LIVE mutation was invoked.

## 27. MANIFEST V2

- **DIRECT_EVIDENCE** The isolated positive receipt has `cycle-source-manifest/2`, model kind `REGULAR_PACKAGE` and `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`. Existing manifest regressions in the requested suite passed.
- No manifest version or schema changed.

## 28. RECEIPT V2

- **DIRECT_EVIDENCE** The isolated receipt has `cycle-prepared-co-publication/2`; `verify_co_published_cycle_manifest(...)` returns True and `live_publish_status` is `success` in the harness. Existing receipt regressions also passed.
- **UNKNOWN** No active LIVE process adoption or active service receipt verification was performed.

## 29. REGRESSION RESULTS

- **DIRECT_EVIDENCE** Requested focused suite: `392 passed in 71.02s (0:01:11)`, exit code 0; failed=0, skipped=0 in pytest's reported totals. The suite includes the D2B-3 cases, all prior focused B/C, D1, D2A, D2B-1, D2B-2, R1/R2, original-worker, evidence, manifest and receipt regressions present in those eight modules.
- No global pytest was run. A first attempt to insert the positive test helper used a stale test-file adjacency anchor and made no edit; insertion was then made against the exact current test anchor. No production anchor conflict was encountered.

## 30. EXACT COMMANDS / EXIT CODES

Working directory: `C:\Temp\Contextor_Repo`.

```text
git rev-parse HEAD
exit_code=0
initial_output=807267a7ef898a96493b1774b2cb5c89344cb655

git status --short
exit_code=0
initial_output=(empty)

& .\.venv\Scripts\python.exe -m py_compile contextor/core/cycle_semantics/typing_guard.py contextor/core/symbol_engine/indexer.py contextor/core/cycle_semantics/package_graph_consistency.py
exit_code=0

& .\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_package_cycle_integration.py tests/test_p1d3_d2b2_type_only.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py
exit_code=0
result=392 passed in 71.02s (0:01:11)

git diff --check
exit_code=0

git rev-parse HEAD
exit_code=0
final_output=807267a7ef898a96493b1774b2cb5c89344cb655

git status --short
exit_code=0
final_output=modified package_graph_consistency.py, typing_guard.py, indexer.py, test_p1d3_package_cycle_integration.py, walkthrough.md
```

The final diff/HEAD/status commands were executed after report generation. Git emitted line-ending notices but no whitespace error.

## 31. FILES_CHANGED

1. `contextor/core/cycle_semantics/typing_guard.py` — authorized production source.
2. `contextor/core/symbol_engine/indexer.py` — authorized production source.
3. `contextor/core/cycle_semantics/package_graph_consistency.py` — authorized production source.
4. `tests/test_p1d3_package_cycle_integration.py` — authorized test source.
5. `walkthrough.md` — required report, overwritten; its self-diff is excluded to avoid recursive content.

No other file changed. Complete source/test diffs follow.

## 32. FULL ACTUAL_DIFF

Complete zero-context Git diffs for all four changed source/test files, including every added and removed line. The report self-diff is excluded.

````diff
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index 964e414..d046311 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -10 +10,6 @@ from .model_identity import indexed_to_logical_module, logical_to_indexed_module
-from .typing_guard import recognize_typing_guard
+from .typing_guard import (
+    _typing_guard_parent_initializers,
+    _typing_guard_passive_initializer,
+    recognize_typing_guard,
+    type_only_candidate_statement_ids,
+)
@@ -253,0 +259,28 @@ def assess_package_graph_consistency(
+        type_only_ids = (
+            type_only_candidate_statement_ids(
+                sources[module_id],
+                indexed,
+            )
+        )
+
+        parents_proved = all(
+            (
+                parent_id in indexed
+                and isinstance(
+                    sources.get(parent_id),
+                    ast.Module,
+                )
+                and _typing_guard_passive_initializer(
+                    sources[parent_id]
+                )
+            )
+            for parent_id in (
+                _typing_guard_parent_initializers(
+                    module_id
+                )
+            )
+        )
+
+        if not parents_proved:
+            type_only_ids = frozenset()
+
@@ -272 +305,4 @@ def assess_package_graph_consistency(
-                    if resolved != module_id:
+                    if (
+                        resolved != module_id
+                        and id(node) not in type_only_ids
+                    ):
diff --git a/contextor/core/cycle_semantics/typing_guard.py b/contextor/core/cycle_semantics/typing_guard.py
index 705df06..e925004 100644
--- a/contextor/core/cycle_semantics/typing_guard.py
+++ b/contextor/core/cycle_semantics/typing_guard.py
@@ -255,0 +256,230 @@ def recognize_typing_guard(
+
+
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
+def _typing_guard_passive_initializer(
+    tree: ast.AST,
+) -> bool:
+    if not isinstance(tree, ast.Module):
+        return False
+
+    allowed_types = {
+        type(None),
+        bool,
+        int,
+        float,
+        complex,
+        str,
+        bytes,
+    }
+
+    for position, statement in enumerate(
+        tree.body
+    ):
+        if isinstance(statement, ast.Pass):
+            continue
+
+        if (
+            position == 0
+            and isinstance(statement, ast.Expr)
+            and isinstance(
+                statement.value,
+                ast.Constant,
+            )
+            and type(
+                statement.value.value
+            ) is str
+        ):
+            continue
+
+        if isinstance(statement, ast.Assign):
+            if (
+                len(statement.targets) != 1
+                or not isinstance(
+                    statement.targets[0],
+                    ast.Name,
+                )
+                or not isinstance(
+                    statement.value,
+                    ast.Constant,
+                )
+            ):
+                return False
+
+            binding = statement.targets[0].id
+
+            if (
+                not binding.isidentifier()
+                or binding.startswith("__")
+                or binding in {
+                    "typing",
+                    "TYPE_CHECKING",
+                }
+                or type(
+                    statement.value.value
+                ) not in allowed_types
+            ):
+                return False
+
+            continue
+
+        return False
+
+    return True
+
+
+def _typing_guard_parent_initializers(
+    module_id: str,
+) -> tuple[str, ...]:
+    logical = (
+        module_id.removesuffix(".__init__")
+        if module_id.endswith(".__init__")
+        else module_id
+    )
+
+    parts = logical.split(".")
+
+    return tuple(
+        ".".join(parts[:length]) + ".__init__"
+        for length in range(1, len(parts))
+    )
+
+
+def type_only_candidate_statement_ids(
+    tree: ast.AST,
+    indexed_ids: frozenset[str],
+) -> frozenset[int]:
+    guard = recognize_typing_guard(
+        tree,
+        indexed_ids,
+    )
+
+    if (
+        guard is None
+        or not isinstance(tree, ast.Module)
+    ):
+        return frozenset()
+
+    marker_position = next(
+        (
+            position
+            for position, statement
+            in enumerate(tree.body)
+            if statement is guard.marker_statement
+        ),
+        None,
+    )
+
+    if marker_position is None:
+        return frozenset()
+
+    matching_guards = [
+        (position, statement)
+        for position, statement
+        in enumerate(tree.body)
+        if (
+            isinstance(statement, ast.If)
+            and matches_typing_guard(
+                statement.test,
+                guard.form,
+            )
+        )
+    ]
+
+    if len(matching_guards) != 1:
+        return frozenset()
+
+    guard_position, guard_statement = (
+        matching_guards[0]
+    )
+
+    if guard_position <= marker_position:
+        return frozenset()
+
+    if not all(
+        _safe_typing_guard_prefix_statement(
+            statement
+        )
+        for statement in tree.body[
+            marker_position + 1:
+            guard_position
+        ]
+    ):
+        return frozenset()
+
+    selected: set[int] = set()
+
+    for statement in guard_statement.body:
+        if (
+            not isinstance(statement, ast.Import)
+            or len(statement.names) != 1
+        ):
+            continue
+
+        alias = statement.names[0]
+        parts = alias.name.split(".")
+
+        if (
+            alias.asname is None
+            and len(parts) > 1
+            and all(
+                part.isidentifier()
+                for part in parts
+            )
+        ):
+            selected.add(id(statement))
+
+    return frozenset(selected)
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 1448334..3530d9d 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -35,0 +36,3 @@ from contextor.core.cycle_semantics.typing_guard import (
+    _safe_typing_guard_prefix_statement,
+    _typing_guard_parent_initializers,
+    _typing_guard_passive_initializer,
@@ -37,0 +41 @@ from contextor.core.cycle_semantics.typing_guard import (
+    type_only_candidate_statement_ids,
@@ -285,143 +288,0 @@ class AdvancedImportVisitor(ast.NodeVisitor):
-def _safe_typing_guard_prefix_statement(
-    statement: ast.stmt,
-) -> bool:
-    if isinstance(statement, ast.Pass):
-        return True
-
-    if (
-        isinstance(statement, ast.Expr)
-        and isinstance(
-            statement.value,
-            ast.Constant,
-        )
-        and type(statement.value.value) is str
-    ):
-        return True
-
-    if isinstance(statement, ast.Assign):
-        if (
-            len(statement.targets) != 1
-            or not isinstance(
-                statement.targets[0],
-                ast.Name,
-            )
-            or not isinstance(
-                statement.value,
-                ast.Constant,
-            )
-        ):
-            return False
-
-        binding = statement.targets[0].id
-
-        return (
-            binding.isidentifier()
-            and not binding.startswith("__")
-            and binding not in {
-                "TYPE_CHECKING",
-                "typing",
-            }
-            and type(
-                statement.value.value
-            ) in {
-                type(None),
-                bool,
-                int,
-                float,
-                complex,
-                str,
-                bytes,
-            }
-        )
-
-    return False
-
-
-def _typing_guard_passive_initializer(
-    tree: ast.AST,
-) -> bool:
-    if not isinstance(tree, ast.Module):
-        return False
-
-    allowed_types = {
-        type(None),
-        bool,
-        int,
-        float,
-        complex,
-        str,
-        bytes,
-    }
-
-    for position, statement in enumerate(
-        tree.body
-    ):
-        if isinstance(statement, ast.Pass):
-            continue
-
-        if (
-            position == 0
-            and isinstance(statement, ast.Expr)
-            and isinstance(
-                statement.value,
-                ast.Constant,
-            )
-            and type(
-                statement.value.value
-            ) is str
-        ):
-            continue
-
-        if isinstance(statement, ast.Assign):
-            if (
-                len(statement.targets) != 1
-                or not isinstance(
-                    statement.targets[0],
-                    ast.Name,
-                )
-                or not isinstance(
-                    statement.value,
-                    ast.Constant,
-                )
-            ):
-                return False
-
-            binding = statement.targets[0].id
-
-            if (
-                not binding.isidentifier()
-                or binding.startswith("__")
-                or binding in {
-                    "typing",
-                    "TYPE_CHECKING",
-                }
-                or type(
-                    statement.value.value
-                ) not in allowed_types
-            ):
-                return False
-
-            continue
-
-        return False
-
-    return True
-
-
-def _typing_guard_parent_initializers(
-    module_id: str,
-) -> tuple[str, ...]:
-    logical = (
-        module_id.removesuffix(".__init__")
-        if module_id.endswith(".__init__")
-        else module_id
-    )
-
-    parts = logical.split(".")
-
-    return tuple(
-        ".".join(parts[:length]) + ".__init__"
-        for length in range(1, len(parts))
-    )
-
-
@@ -451,10 +312,4 @@ def read_imports(
-    type_only_statement_ids: set[int] = set()
-    guard = recognize_typing_guard(tree, frozenset())
-    if guard is not None and isinstance(tree, ast.Module):
-        marker_position = next(
-            (
-                position
-                for position, statement in enumerate(tree.body)
-                if statement is guard.marker_statement
-            ),
-            None,
+    type_only_statement_ids = (
+        type_only_candidate_statement_ids(
+            tree,
+            frozenset(),
@@ -462,37 +317 @@ def read_imports(
-        if marker_position is not None:
-            matching_guards = [
-                (position, statement)
-                for position, statement in enumerate(tree.body)
-                if (
-                    isinstance(statement, ast.If)
-                    and matches_typing_guard(
-                        statement.test,
-                        guard.form,
-                    )
-                )
-            ]
-            if len(matching_guards) == 1:
-                guard_position, guard_statement = matching_guards[0]
-                if (
-                    guard_position > marker_position
-                    and all(
-                        _safe_typing_guard_prefix_statement(statement)
-                        for statement in tree.body[
-                            marker_position + 1:guard_position
-                        ]
-                    )
-                ):
-                    for body_statement in guard_statement.body:
-                        if (
-                            not isinstance(body_statement, ast.Import)
-                            or len(body_statement.names) != 1
-                        ):
-                            continue
-                        alias = body_statement.names[0]
-                        parts = alias.name.split(".")
-                        if (
-                            alias.asname is None
-                            and len(parts) > 1
-                            and all(part.isidentifier() for part in parts)
-                        ):
-                            type_only_statement_ids.add(id(body_statement))
+    )
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index b2a90ac..9f487ae 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -41 +41,4 @@ from contextor.core.cycle_semantics.source_proof import assess_scc_source_bytes
-from contextor.core.cycle_semantics.typing_guard import recognize_typing_guard
+from contextor.core.cycle_semantics.typing_guard import (
+    _typing_guard_passive_initializer,
+    recognize_typing_guard,
+)
@@ -202,0 +206,125 @@ D2B2_MIXED_ACTIVE = {
+D2B3_TYPED_SIDE_NAME = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.c\n"
+        "value = 1\n"
+        "import pkg.b\n"
+    ),
+    "pkg/b.py": "from pkg.a import value\n",
+    "pkg/c.py": "pass\n",
+}
+
+D2B3_TYPED_SIDE_ATTRIBUTE = {
+    **D2B3_TYPED_SIDE_NAME,
+    "pkg/a.py": (
+        "import typing\n"
+        "if typing.TYPE_CHECKING:\n"
+        "    import pkg.c\n"
+        "value = 1\n"
+        "import pkg.b\n"
+    ),
+}
+
+D2B3_SOURCE_BOUND_NEGATIVES = [
+    (
+        "N01-no-marker",
+        "if TYPE_CHECKING:\n    import pkg.c\nvalue = 1\nimport pkg.b\n",
+        "pass\n", {},
+    ),
+    (
+        "N02-aliased-marker",
+        "from typing import TYPE_CHECKING as TC\n"
+        "if TC:\n    import pkg.c\nvalue = 1\nimport pkg.b\n",
+        "pass\n", {},
+    ),
+    (
+        "N03-negated-guard",
+        "from typing import TYPE_CHECKING\n"
+        "if not TYPE_CHECKING:\n    import pkg.c\n"
+        "value = 1\nimport pkg.b\n",
+        "pass\n", {},
+    ),
+    (
+        "N04-nested-import",
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    if True:\n        import pkg.c\n"
+        "value = 1\nimport pkg.b\n",
+        "pass\n", {},
+    ),
+    (
+        "N05-from-import",
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    from pkg import c\n"
+        "value = 1\nimport pkg.b\n",
+        "pass\n", {},
+    ),
+    (
+        "N06-aliased-import",
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    import pkg.c as child\n"
+        "value = 1\nimport pkg.b\n",
+        "pass\n", {},
+    ),
+    (
+        "N07-multiple-guards",
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    pass\n"
+        "if TYPE_CHECKING:\n    import pkg.c\n"
+        "value = 1\nimport pkg.b\n",
+        "pass\n", {},
+    ),
+    (
+        "N08-globals-prefix",
+        "from typing import TYPE_CHECKING\n"
+        'globals()["TYPE_CHECKING"] = True\n'
+        "if TYPE_CHECKING:\n    import pkg.c\n"
+        "value = 1\nimport pkg.b\n",
+        "pass\n", {},
+    ),
+    (
+        "N09-setattr-prefix",
+        "import typing\n"
+        'setattr(typing, "TYPE_CHECKING", True)\n'
+        "if typing.TYPE_CHECKING:\n    import pkg.c\n"
+        "value = 1\nimport pkg.b\n",
+        "pass\n", {},
+    ),
+    (
+        "N10-nonpassive-parent",
+        D2B3_TYPED_SIDE_NAME["pkg/a.py"],
+        "import typing\ntyping.TYPE_CHECKING = True\n", {},
+    ),
+    (
+        "N11-missing-parent",
+        D2B3_TYPED_SIDE_NAME["pkg/a.py"],
+        None, {},
+    ),
+    (
+        "N12-local-typing-module",
+        D2B3_TYPED_SIDE_NAME["pkg/a.py"],
+        "pass\n", {"typing.py": "pass\n"},
+    ),
+    (
+        "N13-local-typing-package",
+        D2B3_TYPED_SIDE_NAME["pkg/a.py"],
+        "pass\n", {"typing/__init__.py": "pass\n"},
+    ),
+    (
+        "N14-active-same-target",
+        D2B3_TYPED_SIDE_NAME["pkg/a.py"].replace(
+            "import pkg.b\n", "import pkg.c\nimport pkg.b\n",
+        ),
+        "pass\n", {},
+    ),
+    (
+        "N15-else-import",
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    pass\n"
+        "else:\n    import pkg.c\n"
+        "value = 1\nimport pkg.b\n",
+        "pass\n", {},
+    ),
+]
+
@@ -922,0 +1051,262 @@ def _d2a_source_evidence(root):
+def _assert_d2b3_typed_side_evidence(root):
+    index, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
+    assert graph.hard_edges == {
+        "pkg.__init__": set(),
+        "pkg.a": {"pkg.b"},
+        "pkg.b": {"pkg.a"},
+        "pkg.c": set(),
+    }
+    assert graph.soft_edges == {
+        "pkg.__init__": set(),
+        "pkg.a": {"pkg.c"},
+        "pkg.b": set(),
+        "pkg.c": set(),
+    }
+    imports_c = [
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.c" and not item.is_from_import
+    ]
+    imports_b = [
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.b" and not item.is_from_import
+    ]
+    assert len(imports_c) == len(imports_b) == 1
+    assert imports_c[0].type_only is True
+    assert imports_b[0].type_only is False
+
+    closure = compute_cycle_model_source_closures(graph.hard_edges)
+    assert len(closure) == 1
+    assert closure[0].members == ("pkg.a", "pkg.b")
+    assert closure[0].evidence_source_modules == (
+        "pkg.__init__", "pkg.a", "pkg.b",
+    )
+    assert "pkg.c" not in closure[0].evidence_source_modules
+    plan = plan_original_worker_reindex(index, graph.hard_edges)
+    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
+    assert plan.selected_module_ids == frozenset(
+        closure[0].evidence_source_modules
+    )
+    assert captured.original_worker_capture_status == (
+        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    )
+    assert set(captured.original_worker_source_snapshots) == set(
+        closure[0].evidence_source_modules
+    )
+    assert set(parsed) == set(closure[0].evidence_source_modules)
+
+    consistency = assess_package_graph_consistency(
+        graph.hard_edges,
+        {module_id: source.tree for module_id, source in parsed.items()},
+        closure[0].evidence_source_modules,
+    )
+    assert consistency.status == "CONSISTENT"
+    assert consistency.reason is None
+
+    scenario = evidence.scenarios.components[0]
+    assert scenario.members == ("pkg.a", "pkg.b")
+    assert scenario.model_kind == "REGULAR_PACKAGE"
+    assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    assert scenario.coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
+    assert not any(
+        event.operation == "START_IMPORT" and event.target == "pkg.c"
+        for assessment in scenario.entry_assessments
+        for event in assessment.events
+    )
+    for entry in ("pkg.a", "pkg.b"):
+        assert run_synthetic_import(root, entry).returncode == 0
+
+    p0 = assess_index_bound_scc_models(
+        graph.hard_edges,
+        captured.source_fingerprints_by_module,
+        snapshot,
+        evidence,
+    )
+    assert len(p0) == 1
+    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+    p1b = assess_scc_source_bytes(
+        graph.hard_edges,
+        captured.source_fingerprints_by_module,
+        snapshot,
+        evidence,
+        captured.original_worker_source_snapshots,
+    )
+    assert len(p1b) == 1
+    assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
+
+    captured_facts = materialize_reexport_facts_by_module(
+        captured.modules,
+        captured.reference_facts_by_module,
+    )
+    captured_trie = build_trie(captured.modules.keys())
+    captured_package_root = detect_package_root(
+        captured.modules, captured_trie,
+    )
+    captured_graph = build_graph(
+        captured.modules,
+        trie=captured_trie,
+        package_root=captured_package_root,
+        reexport_facts_by_module=captured_facts,
+    )
+    assert captured_graph.hard_edges == graph.hard_edges
+    assert captured_graph.soft_edges == graph.soft_edges
+    return index, graph, parsed, closure[0].evidence_source_modules
+
+
+def test_p1d3_d2b3_name_typed_side_import(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B3_TYPED_SIDE_NAME,
+    )
+    _assert_d2b3_typed_side_evidence(root)
+
+
+def test_p1d3_d2b3_attribute_typed_side_import(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B3_TYPED_SIDE_ATTRIBUTE,
+    )
+    _, graph, _, _ = _assert_d2b3_typed_side_evidence(root)
+    name_root = write_synthetic_repository(
+        tmp_path / "name", D2B3_TYPED_SIDE_NAME,
+    )
+    _, name_graph = _d2a_canonical_index_graph(name_root)
+    assert graph.hard_edges == name_graph.hard_edges
+    assert graph.soft_edges == name_graph.soft_edges
+
+
+def test_p1d3_d2b3_forged_hard_graph_rejected(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B3_TYPED_SIDE_NAME,
+    )
+    _, graph, parsed, source_modules = _assert_d2b3_typed_side_evidence(root)
+    trees = {module_id: source.tree for module_id, source in parsed.items()}
+
+    missing = {
+        module_id: set(targets)
+        for module_id, targets in graph.hard_edges.items()
+    }
+    missing["pkg.a"].remove("pkg.b")
+    missing_result = assess_package_graph_consistency(
+        missing, trees, source_modules,
+    )
+    assert missing_result.status == "INDETERMINATE"
+    assert missing_result.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+
+    extra = {
+        module_id: set(targets)
+        for module_id, targets in graph.hard_edges.items()
+    }
+    extra["pkg.a"].add("pkg.c")
+    extra_result = assess_package_graph_consistency(
+        extra, trees, source_modules,
+    )
+    assert extra_result.status == "INDETERMINATE"
+    assert extra_result.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+
+
+@pytest.mark.parametrize(
+    "case,source,parent,extra",
+    D2B3_SOURCE_BOUND_NEGATIVES,
+    ids=[item[0] for item in D2B3_SOURCE_BOUND_NEGATIVES],
+)
+def test_p1d3_d2b3_source_bound_negative_matrix(
+    tmp_path, isolated_dirs, case, source, parent, extra,
+):
+    fixture = {
+        "pkg/a.py": source,
+        "pkg/b.py": D2B3_TYPED_SIDE_NAME["pkg/b.py"],
+        "pkg/c.py": "pass\n",
+        **extra,
+    }
+    if parent is not None:
+        fixture["pkg/__init__.py"] = parent
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    index, graph = _d2a_canonical_index_graph(root)
+    assert "pkg.b" in graph.hard_edges["pkg.a"]
+    imports_c = [
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.c" and not item.is_from_import
+    ]
+    if case == "N05-from-import":
+        assert any(
+            item.module == "pkg" and item.is_from_import and not item.type_only
+            for item in index.modules["pkg.a"].imports
+        )
+    elif case == "N14-active-same-target":
+        assert len(imports_c) == 2
+        assert [item.type_only for item in imports_c] == [True, False]
+        assert "pkg.c" in graph.soft_edges["pkg.a"]
+        assert "pkg.c" in graph.hard_edges["pkg.a"]
+    else:
+        assert imports_c
+        assert all(item.type_only is False for item in imports_c)
+        assert "pkg.c" in graph.hard_edges["pkg.a"]
+
+    trees = {
+        module_id: ast.parse((root / module.path).read_text(encoding="utf-8"))
+        for module_id, module in index.modules.items()
+    }
+    closure = compute_cycle_model_source_closures(graph.hard_edges)
+    source_modules = (
+        closure[0].evidence_source_modules
+        if closure else ("pkg.a",)
+    )
+    forged = {
+        module_id: set(targets)
+        for module_id, targets in graph.hard_edges.items()
+    }
+    required_target = "pkg.c" if "pkg.c" in forged["pkg.a"] else "pkg.b"
+    forged["pkg.a"].remove(required_target)
+    result = assess_package_graph_consistency(
+        forged, trees, source_modules,
+    )
+    assert result.status != "CONSISTENT"
+    if case == "N14-active-same-target":
+        assert result.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+
+
+@pytest.mark.parametrize(
+    "case,parent_source",
+    [
+        ("P01-typing-mutation", "import typing\ntyping.TYPE_CHECKING = True\n"),
+        ("P02-setattr-mutation", 'import typing\nsetattr(typing, "TYPE_CHECKING", True)\n'),
+        ("P03-exec", 'exec("x = 1")\n'),
+    ],
+)
+def test_p1d3_d2b3_parent_passivity_replay(
+    tmp_path, isolated_dirs, case, parent_source,
+):
+    assert _typing_guard_passive_initializer(ast.parse(parent_source)) is False
+    fixture = {
+        **D2B3_TYPED_SIDE_NAME,
+        "pkg/__init__.py": parent_source,
+    }
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    index, graph = _d2a_canonical_index_graph(root)
+    guarded = [
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.c" and not item.is_from_import
+    ]
+    assert len(guarded) == 1
+    assert guarded[0].type_only is False
+    assert "pkg.c" in graph.hard_edges["pkg.a"]
+    assert "pkg.b" in graph.hard_edges["pkg.a"]
+    trees = {
+        module_id: ast.parse((root / module.path).read_text(encoding="utf-8"))
+        for module_id, module in index.modules.items()
+    }
+    forged = {
+        module_id: set(targets)
+        for module_id, targets in graph.hard_edges.items()
+    }
+    forged["pkg.a"].remove("pkg.c")
+    consistency = assess_package_graph_consistency(
+        forged, trees, ("pkg.a",),
+    )
+    assert consistency.status == "INDETERMINATE"
+    assert consistency.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+    scenarios = analyze_cycle_scenarios(graph.hard_edges, trees)
+    assert all(
+        component.classification != "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        for component in scenarios.components
+    )
+
+
@@ -1736,0 +2127,9 @@ def test_p1d3_d2b2_active_import_dominates_type_only(
+    closure = compute_cycle_model_source_closures(graph.hard_edges)
+    assert len(closure) == 1
+    consistency = assess_package_graph_consistency(
+        graph.hard_edges,
+        {module_id: source.tree for module_id, source in parsed.items()},
+        closure[0].evidence_source_modules,
+    )
+    assert consistency.status == "CONSISTENT"
+    assert consistency.reason is None
@@ -1811,0 +2211,47 @@ def test_p1d3_d2b2_dissolved_scc_does_not_publish_receipt(
+
+
+@pytest.mark.live
+def test_p1d3_d2b3_official_isolated_full_receipt(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B3_TYPED_SIDE_NAME,
+    )
+    index, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
+    assert graph.hard_edges["pkg.a"] == {"pkg.b"}
+    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
+    assert graph.soft_edges["pkg.a"] == {"pkg.c"}
+    assert captured.original_worker_capture_status == (
+        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    )
+    assert set(captured.original_worker_source_snapshots) == {
+        "pkg.__init__", "pkg.a", "pkg.b",
+    }
+    with _official_live(root, monkeypatch) as (client, server, identity, calls):
+        _, result = ContextorFacade.analyze_project(
+            str(root), cycle_source_preparation_preview=True,
+            cycle_source_publication_opt_in=True,
+        )
+        assert result.cycle_source_preparation_preview.status == (
+            "PREPARED_UNPUBLISHED_NON_ATOMIC"
+        )
+        state, metadata = _persisted(root)
+        receipt = state.cycle_source_publication
+        assert receipt.version == PUBLICATION_BINDING_VERSION == (
+            "cycle-prepared-co-publication/2"
+        )
+        assert receipt.prepared_manifest.version == MANIFEST_VERSION == (
+            "cycle-source-manifest/2"
+        )
+        component = receipt.prepared_manifest.components[0]
+        assert component.model_kind == "REGULAR_PACKAGE"
+        assert component.model_classification == (
+            "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        )
+        assert verify_co_published_cycle_manifest(
+            state, revision=metadata.revision,
+            state_id=metadata.state_id, repo_id=metadata.repo_id,
+            root_path=metadata.root_path,
+        )
+        assert result.live_publish_status == "success"
+        assert calls == [root.resolve()]
````

## 33. CONTRACT_CONFLICTS

- **DIRECT_EVIDENCE** None observed in the specified production anchors. The exact prior candidate block, helper bodies and checker hard-edge add were present and changed as instructed.

## 34. DESIGN_GAPS

- **DIRECT_EVIDENCE** None encountered for the literal production changes or required test fixtures. No alternative production algorithm or data structure was chosen.

## 35. UNKNOWN / UNSUPPORTED

- **UNKNOWN** Loaded-code adoption in any active Contextor MCP/LIVE process. Contextor revision 754 and verified source sync were pre-edit discovery evidence only; no runtime reload or active certification occurred.
- **UNKNOWN** Global-suite result, arbitrary Python dynamic behavior, and runtime behavior of deliberately unsupported negative fixtures.
- A checker `CONSISTENT` result is a source-bound hard-edge consistency result for supplied ASTs and indexed IDs, not a general guarantee of runtime safety.

## 36. FINAL IMPLEMENTER OBSERVATION

The implementer observed exact authorized file scope, compilation exit 0, the requested focused pytest exit 0 with 392 passes, full source/test diffs in this report, unchanged HEAD and final `git diff --check` exit 0. Architectural acceptance remains with ChatGPT. Stop after D2B-3.

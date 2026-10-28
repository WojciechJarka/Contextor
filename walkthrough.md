# CONTEXTOR — P1D3-D2B-2-R2 PARENT INITIALIZER SOURCE-BOUND TYPE_ONLY VETO

## 1. EXECUTIVE VERDICT

**IMPLEMENTER OBSERVATION:** the specified code changes were applied to the single authorized production file. The eight requested focused test modules completed with `370 passed in 67.11s`. This is an observed implementation and test result. Architectural acceptance and any GO/PARTIAL/NO_GO decision belong exclusively to ChatGPT.

Evidence labels: **DIRECT_EVIDENCE** = observed repository/tool/test output; **CODE_PATH_PROVED** = exact current code condition; **CONTRACT_PROVED** = executed assertion of the specified contract; **INFERENCE** = bounded conclusion; **UNKNOWN** = not established.

## 2. INITIAL / FINAL HEAD

- **DIRECT_EVIDENCE** Initial HEAD: `cdb6e13f0bef36d5c4a8953891945c7132b093b5`.
- **DIRECT_EVIDENCE** Final HEAD: `cdb6e13f0bef36d5c4a8953891945c7132b093b5`.
- No commit, push, reset, checkout or clean command was run.

## 3. INITIAL / FINAL WORKTREE

- **DIRECT_EVIDENCE** Initial `git status --short` was empty.
- **DIRECT_EVIDENCE** Final changed files: `contextor/core/symbol_engine/indexer.py`, `tests/test_p1d3_d2b2_type_only.py`, and this overwritten `walkthrough.md` report.
- `tests/test_p1d3_package_cycle_integration.py` was read and executed, but did not require modification.

## 4. EXACT PRODUCTION CHANGES

- **CODE_PATH_PROVED** `IMPORT_CLASSIFICATION_SEMANTICS_VERSION` changed only from 2 to 3. The cache key remained `import_classification_semantics_version`.
- **CODE_PATH_PROVED** Added the two exact top-level private functions specified in §§06–07 of the instruction, immediately before `read_imports`.
- **CODE_PATH_PROVED** Worker cache eligibility now also requires `type(cached_data.get("typing_guard_initializer_passive")) is bool`. Cache miss/staleness derives the fact from the worker's already parsed original source snapshot.
- **CODE_PATH_PROVED** The exact private bool is written to cold and partial cache records and all four worker return dictionaries. The index parent records `(passive, source_fingerprint)` only for successful initializer modules.
- **CODE_PATH_PROVED** Both inline and process-pool branches call `record_initializer_passivity` immediately after the existing fingerprint recorder. The finalizer uses the prescribed parent enumeration, worker fact, matching fingerprint and typing-shadow veto before each existing `RepositoryIndex` return.
- The complete production diff is in §33. No other production file was edited.

## 5. PASSIVITY FUNCTION

- **CODE_PATH_PROVED** `_typing_guard_passive_initializer(tree)` returns False for non-`ast.Module`; accepts an empty module, `Pass`, only a position-zero constant string expression, and the exact single-name literal assignment form from the instruction. Any other statement returns False.
- **DIRECT_EVIDENCE** The 17 negative and 5 positive initializer source variants passed direct function and final child-classification assertions.
- The function does not execute analyzed source or recurse into control flow.

## 6. PARENT ENUMERATOR

- **CODE_PATH_PROVED** `_typing_guard_parent_initializers(module_id)` strips the module's own `.__init__` suffix for logical identity, then returns ancestor initializer IDs from outermost to innermost, excluding self.
- **DIRECT_EVIDENCE** The multilevel test asserts `pkg.sub.a -> (pkg.__init__, pkg.sub.__init__)`. The six multilevel fixtures independently exercised this chain and missing-parent vetoes.

## 7. WORKER CACHE BINDING

- **CODE_PATH_PROVED** The worker retains `cache.get(path, source_bytes=source_snapshot.raw)`. Cache data is reusable only with an exact integer semantic version equal to 3 and an exact bool `typing_guard_initializer_passive` value.
- **CODE_PATH_PROVED** On a validated cache, the worker takes the bool directly from that entry. On missing/stale cache, after `tree = parsed_input.tree`, it computes `module_id.endswith(".__init__") and _typing_guard_passive_initializer(tree)`.
- **CODE_PATH_PROVED** Cold cache construction and partial validated-cache rewrite preserve the exact bool with the same existing `source_bytes` cache-set binding. No independent hash, second source read, post-index parse or cache-manager change was added.

## 8. ALL WORKER RETURN PATHS

- **CODE_PATH_PROVED** The complete current-cache fast return and parsed-source final return both include `typing_guard_initializer_passive`. The source-read and parse-failure returns include exact False.
- **DIRECT_EVIDENCE** Dedicated safe/unsafe parent tests invoked the real worker cold and warm paths. Both successful results had exact bool type; cold had `source_parse_called=True`, warm complete-cache fast return had `source_parse_called=False`, `cache_hit=True`, and equal source fingerprints. Their cached flags were exact bool values.
- Failure-return field placement was inspected in the production diff; those two paths were not separately executed by new tests.

## 9. INLINE COLLECTION

- **CODE_PATH_PROVED** The inline success branch records its existing source fingerprint and then calls `record_initializer_passivity(res)`. No record is produced for an errored worker result.
- **DIRECT_EVIDENCE** The focused synthetic inline fixtures passed across safe, unsafe, multilevel and cache cases.

## 10. PROCESS-POOL COLLECTION

- **CODE_PATH_PROVED** The process-pool success branch makes the same call immediately after its existing fingerprint recorder. No second collection algorithm or IPC schema was added.
- **DIRECT_EVIDENCE** Five specified fixture classes were indexed through real process-pool execution with `CONTEXTOR_DISABLE_PROCESS_POOL` removed; ordered imports and graph/SCC signatures matched inline results.

## 11. SOURCE-FINGERPRINT ASSOCIATION

- **CODE_PATH_PROVED** `initializer_passivity_by_module` is a private `dict[str, tuple[bool, str]]`. A record is created only when worker `module_id` is an initializer string, `error is None`, the passive value is exact bool and the worker fingerprint is string. The existing fingerprint recorder validates and stores the indexed source fingerprint.
- **CODE_PATH_PROVED** Finalization requires parent membership, positive exact bool and equality between the worker-derived tuple fingerprint and `source_fingerprints_by_module[parent_id]`.
- **DIRECT_EVIDENCE** In an isolated source-change test, editing only a safe parent to the unsafe initializer changed the parent's fingerprint, preserved the child's fingerprint and changed the child's final import from soft to hard.

## 12. FINALIZER EXACT RULE

- **CODE_PATH_PROVED** For each module containing a candidate `type_only` import, the finalizer computes the existing repository-wide typing shadow and requires every enumerated parent initializer to have a matching positive source-bound worker fact. If typing is shadowed or any parent proof is absent/false/mismatched, only candidate `ImportRef` objects are replaced with `type_only=False` using `dataclasses.replace`.
- **CODE_PATH_PROVED** Both existing finalizer call sites remain immediately before the inline and process-pool `RepositoryIndex` returns. No third call site, graph mutation or public field was added.

## 13. PRIMARY MUTATION DIFFERENTIAL

- **DIRECT_EVIDENCE** The exact parent source `import typing; typing.TYPE_CHECKING = True` caused the guarded child `pkg.b` occurrence to remain `type_only=False`. Hard `pkg.a -> pkg.b` and `pkg.b -> pkg.a` edges and the real `{pkg.a, pkg.b}` SCC survived; `pkg.a -> pkg.b` was absent from soft edges.
- **DIRECT_EVIDENCE** Fresh isolated CPython `pkg.a` import failed with `partially initialized module` in stderr. The restricted SCC report did not claim `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`.

## 14. SETATTR DIFFERENTIAL

- **DIRECT_EVIDENCE** A separate isolated fixture with parent `import typing; setattr(typing, "TYPE_CHECKING", True)` produced the same hard graph and SCC. A separate fresh CPython subprocess failed importing `pkg.a` with partially initialized module text.
- No unsupported parent execution effect was promoted to a proved model hazard or positive source proof.

## 15. MULTILEVEL MATRIX

- **DIRECT_EVIDENCE** All six independent fixtures passed with exact indexed module IDs checked per case: M01 both passive => soft; M02 unsafe outer => hard SCC; M03 unsafe inner => hard SCC; M04 literal outer plus docstring/pass inner => soft; M05 missing inner => hard SCC; M06 missing outer => hard SCC.
- **DIRECT_EVIDENCE** Fresh CPython differentials were run only for executable M01–M04. M01/M04 succeeded; M02/M03 failed with partially initialized module text. No namespace-package runtime equivalence is claimed for M05/M06.

## 16. NEGATIVE INITIALIZER MATRIX

- **DIRECT_EVIDENCE** N01–N17 each returned False from the pure passivity function. In a separate synthetic repository per case, the guarded child occurrence remained `type_only=False`, `pkg.a -> pkg.b` remained hard and no corresponding soft edge appeared.
- The variants include imports, attribute/subscript mutation, calls, function/class/control-flow definitions, augmented/annotated assignment and raise. Intentionally incomplete runtime variants were not executed in CPython.

## 17. POSITIVE INITIALIZER MATRIX

- **DIRECT_EVIDENCE** P01–P05 each returned True from the pure function and preserved the guarded child `type_only=True` classification, soft `pkg.a -> pkg.b`, no hard edge in that direction and no hard SCC. The cases are empty, pass, first-position docstring, one literal assignment and the specified mixed passive sequence.
- No SCC evidence was fabricated for these dissolved components.

## 18. CACHE VERSION 2 -> 3

- **DIRECT_EVIDENCE** Existing tests now expect worker-cache semantic version 3. Stale-marker parameterization covers absent, 0, 1 and 2; each reparses from the existing original worker source snapshot and rewrites version 3.
- **CODE_PATH_PROVED** Source SHA checking remains through the original `cache.get(..., source_bytes=source_snapshot.raw)` call; other schema versions were not changed.

## 19. MALFORMED CACHE

- **DIRECT_EVIDENCE** Four current-version-3 forged parent cache records were tested with missing passivity key, None, string `"true"` and integer `1`. Each was rejected, reparsed only the parent from its original worker snapshot and rewrote exact bool False. The child hard SCC remained.
- **DIRECT_EVIDENCE** Instrumented reads observed three distinct source reads for the three source files, one per file, and only the malformed parent was reparsed. No `bool(1)` coercion was accepted.

## 20. STALE FORGED CACHE

- **DIRECT_EVIDENCE** The isolated unsafe parent cache initially held version 3 and passive False. The test forged only that parent cache entry to version 2/passive True while retaining original source bytes. Reindexing restored version 3/passive False, retained unchanged parent source fingerprint and the child's hard SCC.
- Active cache directories were not modified.

## 21. COLD / WARM PARITY

- **DIRECT_EVIDENCE** Separate passive and unsafe parent fixtures matched exact ordered imports, type-only flags, hard edges, soft edges and SCC members between cold and warm indexing. The warm test made parsing an assertion failure, so a complete valid cache hit could not silently reparse.
- The existing D2B-2 warm-cache regression also passed under version 3.

## 22. INLINE / PROCESS-POOL PARITY

- **DIRECT_EVIDENCE** Safe single-level, unsafe single-level, safe multilevel, unsafe outer and unsafe inner fixtures each passed inline versus real process-pool comparisons for ordered `ImportRef` records, final flags, hard graph, soft graph and SCC signature.
- Existing local `typing.py` and `typing/__init__.py` shadow-veto parity regressions also passed.

## 23. HARD / SOFT GRAPH

- **DIRECT_EVIDENCE** Unsafe and missing-parent cases keep guarded imports hard. Proven passive parents keep them soft. The existing mixed same-target fixture still retains a hard edge from its normal import beside the soft guarded occurrence; ELSE imports remain hard. No graph/resolver file was edited.

## 24. SCC TOPOLOGY

- **DIRECT_EVIDENCE** Primary and setattr unsafe parents, unsafe outer/inner multilevel parents, and missing-parent cases retain a hard SCC over the two child modules. Proven passive parent cases dissolve that hard SCC. The tests assert actual canonical graph and scenario component signatures.
- **INFERENCE** These results are limited to the constructed fixtures and current indexed graph, not general runtime certainty.

## 25. ORIGINAL-WORKER REINDEX

- **DIRECT_EVIDENCE** For the primary unsafe fixture, the existing planner returned `READY_FOR_REINDEX_NON_ATOMIC` with a nonempty selected module set. A real second index captured the selected original worker source snapshots with `ALL_SELECTED_CAPTURED_NON_ATOMIC`; each selected snapshot fingerprint equaled the captured index fingerprint.
- **DIRECT_EVIDENCE** An independently rebuilt canonical graph from the captured modules and canonical reexport facts exactly matched original hard/soft edges. `pkg.a -> pkg.b` and `pkg.b -> pkg.a` remained hard. No positive P0/P1B assessment was asserted for unsupported parent semantics.

## 26. P0/P1B

- **DIRECT_EVIDENCE** Existing focused tests for supported surviving SCCs, including mixed and ELSE fixtures, passed their P0 genuine evidence, P1B original-source replay and forged-event rejection assertions.
- **CODE_PATH_PROVED** R2 did not edit P0/P1B implementation or event/schema contracts.

## 27. MANIFEST V2

- **DIRECT_EVIDENCE** Focused original-worker preparation tests ran and passed for supported SCCs. The existing dissolved NAME-safe hard SCC still yields no invented manifest. R2 did not edit manifest or publication-binding code.

## 28. OFFICIAL ISOLATED FULL

- **DIRECT_EVIDENCE** The existing isolated `D2B_ELSE_SAFE` facade analysis and publication tests were included in the passing focused suite. Their assertions cover `PREPARED_UNPUBLISHED_NON_ATOMIC`, manifest v2, prepared co-publication v2 and `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS` for the genuine supported SCC.
- No FULL was run on the active Contextor repository or active service.

## 29. RECEIPT V2

- **DIRECT_EVIDENCE** The same isolated positive test checks successful live publication and verified co-publication receipt; the dissolved `D2B_NAME_SAFE` test checks no invented persisted receipt. Both ran in the focused suite.
- **UNKNOWN** These isolated results do not establish active LIVE code adoption or active process receipt behavior.

## 30. FOCUSED PYTEST RESULTS

- **DIRECT_EVIDENCE** The requested eight-module focused command exited 0: `370 passed in 67.11s (0:01:07)`; failed=0, skipped=0 as reported by pytest. No global pytest was run.
- Existing B/C, D1, D2A, D2B-1, D2B-2, D2B-2-R1 and original-worker/manifest/receipt regressions within those eight modules remained in the run; no test was deleted or skipped for R2.

## 31. EXACT COMMANDS / EXIT CODES

Working directory: `C:\Temp\Contextor_Repo`.

```text
git rev-parse HEAD
exit_code=0
output=cdb6e13f0bef36d5c4a8953891945c7132b093b5

git status --short
exit_code=0
initial_output=(empty)

& .\.venv\Scripts\python.exe -m py_compile contextor/core/symbol_engine/indexer.py
exit_code=0

& .\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_d2b2_type_only.py tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py
exit_code=0
result=370 passed in 67.11s (0:01:07)

git diff --check
exit_code=0

git rev-parse HEAD
exit_code=0
output=cdb6e13f0bef36d5c4a8953891945c7132b093b5

git status --short
exit_code=0
final_output=modified indexer.py, modified test_p1d3_d2b2_type_only.py, modified walkthrough.md
```

The final `git diff --check`, HEAD and status reads were performed after writing this report. Git may print line-ending notices; it reported no whitespace error.

## 32. FILES_CHANGED

1. `contextor/core/symbol_engine/indexer.py` — authorized production source.
2. `tests/test_p1d3_d2b2_type_only.py` — authorized test file.
3. `walkthrough.md` — required report, overwritten. Its self-diff is omitted to avoid recursion.

No other production, test or docs file changed. Full actual source/test diffs follow.

## 33. FULL ACTUAL_DIFF

Complete zero-context Git diff for every changed source/test file; every added and removed line is included. The report file's own diff is excluded.

````diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 5fe3205..1448334 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -72 +72 @@ TEST_FACTS_SCHEMA_VERSION = 1
-IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 2
+IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 3
@@ -339,0 +340,88 @@ def _safe_typing_guard_prefix_statement(
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
@@ -634,0 +723 @@ def _process_single_file(
+            "typing_guard_initializer_passive": False,
@@ -690,0 +780,5 @@ def _process_single_file(
+            or type(
+                cached_data.get(
+                    "typing_guard_initializer_passive"
+                )
+            ) is not bool
@@ -694,0 +789,6 @@ def _process_single_file(
+    typing_guard_initializer_passive = (
+        cached_data["typing_guard_initializer_passive"]
+        if cached_data is not None
+        else False
+    )
+
@@ -748,0 +849,3 @@ def _process_single_file(
+                "typing_guard_initializer_passive": (
+                    typing_guard_initializer_passive
+                ),
@@ -788,0 +892 @@ def _process_single_file(
+            "typing_guard_initializer_passive": False,
@@ -814,0 +919,5 @@ def _process_single_file(
+    if cached_data is None:
+        typing_guard_initializer_passive = (
+            module_id.endswith(".__init__")
+            and _typing_guard_passive_initializer(tree)
+        )
@@ -934,0 +1044,3 @@ def _process_single_file(
+                rewritten[
+                    "typing_guard_initializer_passive"
+                ] = typing_guard_initializer_passive
@@ -1067,0 +1180,3 @@ def _process_single_file(
+            "typing_guard_initializer_passive": (
+                typing_guard_initializer_passive
+            ),
@@ -1099,0 +1215,3 @@ def _process_single_file(
+        "typing_guard_initializer_passive": (
+            typing_guard_initializer_passive
+        ),
@@ -1319,0 +1438,4 @@ def index_repository(
+    initializer_passivity_by_module: dict[
+        str,
+        tuple[bool, str],
+    ] = {}
@@ -1441,0 +1564,30 @@ def index_repository(
+    def record_initializer_passivity(
+        result: dict,
+    ) -> None:
+        module_id = result.get("module_id")
+
+        if (
+            type(module_id) is not str
+            or not module_id.endswith(".__init__")
+            or result.get("error") is not None
+        ):
+            return
+
+        passive = result.get(
+            "typing_guard_initializer_passive"
+        )
+        fingerprint = result.get(
+            "source_fingerprint"
+        )
+
+        if (
+            type(passive) is bool
+            and type(fingerprint) is str
+        ):
+            initializer_passivity_by_module[
+                module_id
+            ] = (
+                passive,
+                fingerprint,
+            )
+
@@ -2073,2 +2225,4 @@ def index_repository(
-        if "typing" not in modules and "typing.__init__" not in modules:
-            return
+        typing_shadowed = (
+            "typing" in modules
+            or "typing.__init__" in modules
+        )
@@ -2077 +2231,38 @@ def index_repository(
-            if not any(import_ref.type_only for import_ref in module.imports):
+            if not any(
+                import_ref.type_only
+                for import_ref in module.imports
+            ):
+                continue
+
+            parents_proved = all(
+                (
+                    parent_id in modules
+                    and parent_id
+                    in initializer_passivity_by_module
+                    and type(
+                        initializer_passivity_by_module[
+                            parent_id
+                        ][0]
+                    ) is bool
+                    and initializer_passivity_by_module[
+                        parent_id
+                    ][0] is True
+                    and initializer_passivity_by_module[
+                        parent_id
+                    ][1] == (
+                        source_fingerprints_by_module.get(
+                            parent_id
+                        )
+                    )
+                )
+                for parent_id in (
+                    _typing_guard_parent_initializers(
+                        module_id
+                    )
+                )
+            )
+
+            if (
+                not typing_shadowed
+                and parents_proved
+            ):
@@ -2078,0 +2270 @@ def index_repository(
+
@@ -2082 +2274,4 @@ def index_repository(
-                    dataclasses.replace(import_ref, type_only=False)
+                    dataclasses.replace(
+                        import_ref,
+                        type_only=False,
+                    )
@@ -2118,0 +2314 @@ def index_repository(
+                record_initializer_passivity(res)
@@ -2274,0 +2471 @@ def index_repository(
+                record_initializer_passivity(res)
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 0a4811a..9e00afe 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -12,0 +13 @@ from contextor.core.analysis.cache_manager import CacheManager
+from contextor.core.cycle_semantics.original_worker_reindex_planning import plan_original_worker_reindex
@@ -56,0 +58,72 @@ D2B2_R1_SETATTR_MUTATION = {
+D2B2_R2_PARENT_MUTATION = {
+    "pkg/__init__.py": (
+        "import typing\n"
+        "typing.TYPE_CHECKING = True\n"
+    ),
+    "pkg/a.py": D2B_NAME_SAFE["pkg/a.py"],
+    "pkg/b.py": D2B_NAME_SAFE["pkg/b.py"],
+}
+
+D2B2_R2_PARENT_SETATTR = {
+    **D2B2_R2_PARENT_MUTATION,
+    "pkg/__init__.py": (
+        "import typing\n"
+        'setattr(typing, "TYPE_CHECKING", True)\n'
+    ),
+}
+
+D2B2_R2_MULTILEVEL_COMMON = {
+    "pkg/sub/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.sub.b\n"
+        "value = 1\n"
+    ),
+    "pkg/sub/b.py": "from pkg.sub.a import value\n",
+}
+
+D2B2_R2_UNSAFE_INITIALIZER = (
+    "import typing\n"
+    "typing.TYPE_CHECKING = True\n"
+)
+
+D2B2_R2_MULTILEVEL_CASES = [
+    ("M01-both-pass", "pass\n", "pass\n", True, True),
+    ("M02-unsafe-outer", D2B2_R2_UNSAFE_INITIALIZER, "pass\n", False, True),
+    ("M03-unsafe-inner", "pass\n", D2B2_R2_UNSAFE_INITIALIZER, False, True),
+    ("M04-passive-literals", "constant = 1\n", '"docstring"\npass\n', True, True),
+    ("M05-missing-inner", "pass\n", None, False, False),
+    ("M06-missing-outer", None, "pass\n", False, False),
+]
+
+D2B2_R2_NEGATIVE_INITIALIZERS = [
+    ("N01-import-typing", "import typing\n"),
+    ("N02-from-typing", "from typing import TYPE_CHECKING\n"),
+    ("N03-attribute-assignment", "typing.TYPE_CHECKING = True\n"),
+    ("N04-setattr", 'setattr(typing, "TYPE_CHECKING", True)\n'),
+    ("N05-globals", 'globals()["TYPE_CHECKING"] = True\n'),
+    ("N06-exec", 'exec("x = 1")\n'),
+    ("N07-function", "def f(): pass\n"),
+    ("N08-class", "class C: pass\n"),
+    ("N09-if", "if True: pass\n"),
+    ("N10-try", "try:\n    pass\nexcept Exception:\n    pass\n"),
+    ("N11-with", "with context:\n    pass\n"),
+    ("N12-import-child", "import pkg.other\n"),
+    ("N13-call", "arbitrary()\n"),
+    ("N14-subscript-assignment", 'obj["x"] = 1\n'),
+    ("N15-augmented-assignment", "x = 1\nx += 1\n"),
+    ("N16-annotated-assignment", "x: int = 1\n"),
+    ("N17-raise", "raise RuntimeError()\n"),
+]
+
+D2B2_R2_POSITIVE_INITIALIZERS = [
+    ("P01-empty", ""),
+    ("P02-pass", "pass\n"),
+    ("P03-docstring", '"docstring"\n'),
+    ("P04-literal", "constant = 1\n"),
+    (
+        "P05-mixed-passive",
+        '"docstring"\nconstant = 1\nother = False\npass\n',
+    ),
+]
+
@@ -351 +424 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
-    assert cached["import_classification_semantics_version"] == 2
+    assert cached["import_classification_semantics_version"] == 3
@@ -369 +442,2 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
-    "stored_version", [None, 0, 1], ids=["absent", "version-0", "version-1"],
+    "stored_version", [None, 0, 1, 2],
+    ids=["absent", "version-0", "version-1", "version-2"],
@@ -413 +487 @@ def test_stale_import_classification_cache_reparses_same_snapshot(
-    assert rewritten["import_classification_semantics_version"] == 2
+    assert rewritten["import_classification_semantics_version"] == 3
@@ -710 +784 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
-    assert cached["import_classification_semantics_version"] == 2
+    assert cached["import_classification_semantics_version"] == 3
@@ -732 +806 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
-    assert rewritten["import_classification_semantics_version"] == 2
+    assert rewritten["import_classification_semantics_version"] == 3
@@ -760,0 +835,410 @@ def test_d2b2_r1_dynamic_mutation_inline_process_pool_parity(
+
+def _assert_r2_unsafe_parent(root):
+    indexed, graph = _index_graph(root)
+    guarded = [
+        item for item in indexed.modules["pkg.a"].imports
+        if item.module == "pkg.b" and not item.is_from_import
+    ]
+    assert len(guarded) == 1
+    assert guarded[0].type_only is False
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
+def test_d2b2_r2_parent_initializer_mutation_retains_hard_scc(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B2_R2_PARENT_MUTATION,
+    )
+    _assert_r2_unsafe_parent(root)
+
+
+def test_d2b2_r2_parent_setattr_retains_hard_scc(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B2_R2_PARENT_SETATTR,
+    )
+    _assert_r2_unsafe_parent(root)
+
+
+@pytest.mark.parametrize(
+    "case,outer,inner,expected_type_only,run_cpython",
+    D2B2_R2_MULTILEVEL_CASES,
+    ids=[item[0] for item in D2B2_R2_MULTILEVEL_CASES],
+)
+def test_d2b2_r2_multilevel_parent_chain(
+    tmp_path, isolated_dirs, case, outer, inner,
+    expected_type_only, run_cpython,
+):
+    fixture = dict(D2B2_R2_MULTILEVEL_COMMON)
+    if outer is not None:
+        fixture["pkg/__init__.py"] = outer
+    if inner is not None:
+        fixture["pkg/sub/__init__.py"] = inner
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    indexed, graph = _index_graph(root)
+    expected_ids = {"pkg.sub.a", "pkg.sub.b"}
+    if outer is not None:
+        expected_ids.add("pkg.__init__")
+    if inner is not None:
+        expected_ids.add("pkg.sub.__init__")
+    assert set(indexed.modules) == expected_ids
+    assert indexer._typing_guard_parent_initializers("pkg.sub.a") == (
+        "pkg.__init__", "pkg.sub.__init__",
+    )
+    guarded = [
+        item for item in indexed.modules["pkg.sub.a"].imports
+        if item.module == "pkg.sub.b" and not item.is_from_import
+    ]
+    assert len(guarded) == 1
+    assert guarded[0].type_only is expected_type_only
+    assert graph.hard_edges["pkg.sub.b"] == {"pkg.sub.a"}
+    if expected_type_only:
+        assert graph.soft_edges["pkg.sub.a"] == {"pkg.sub.b"}
+        assert "pkg.sub.b" not in graph.hard_edges["pkg.sub.a"]
+        assert not any(
+            {"pkg.sub.a", "pkg.sub.b"}.issubset(set(members))
+            for members in _scc_signature(indexed, graph)
+        )
+    else:
+        assert "pkg.sub.b" in graph.hard_edges["pkg.sub.a"]
+        assert "pkg.sub.b" not in graph.soft_edges["pkg.sub.a"]
+        assert any(
+            set(members) == {"pkg.sub.a", "pkg.sub.b"}
+            for members in _scc_signature(indexed, graph)
+        )
+    if run_cpython:
+        actual = run_synthetic_import(root, "pkg.sub.a")
+        assert (actual.returncode == 0) is expected_type_only
+        if not expected_type_only:
+            assert "partially initialized module" in actual.stderr
+
+
+@pytest.mark.parametrize(
+    "case,source", D2B2_R2_NEGATIVE_INITIALIZERS,
+    ids=[item[0] for item in D2B2_R2_NEGATIVE_INITIALIZERS],
+)
+def test_d2b2_r2_negative_parent_initializer_matrix(
+    tmp_path, isolated_dirs, case, source,
+):
+    assert indexer._typing_guard_passive_initializer(ast.parse(source)) is False
+    fixture = {**D2B_NAME_SAFE, "pkg/__init__.py": source}
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    indexed, graph = _index_graph(root)
+    guarded = [
+        item for item in indexed.modules["pkg.a"].imports
+        if item.module == "pkg.b" and not item.is_from_import
+    ]
+    assert len(guarded) == 1
+    assert guarded[0].type_only is False
+    assert "pkg.b" in graph.hard_edges["pkg.a"]
+    assert "pkg.b" not in graph.soft_edges["pkg.a"]
+
+
+@pytest.mark.parametrize(
+    "case,source", D2B2_R2_POSITIVE_INITIALIZERS,
+    ids=[item[0] for item in D2B2_R2_POSITIVE_INITIALIZERS],
+)
+def test_d2b2_r2_positive_parent_initializer_matrix(
+    tmp_path, isolated_dirs, case, source,
+):
+    assert indexer._typing_guard_passive_initializer(ast.parse(source)) is True
+    fixture = {**D2B_NAME_SAFE, "pkg/__init__.py": source}
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    indexed, graph = _index_graph(root)
+    guarded = [
+        item for item in indexed.modules["pkg.a"].imports
+        if item.module == "pkg.b" and not item.is_from_import
+    ]
+    assert len(guarded) == 1
+    assert guarded[0].type_only is True
+    assert graph.soft_edges["pkg.a"] == {"pkg.b"}
+    assert "pkg.b" not in graph.hard_edges["pkg.a"]
+    assert _scc_signature(indexed, graph) == ()
+
+
+@pytest.mark.parametrize(
+    "fixture,expected_passive",
+    [(D2B_NAME_SAFE, True), (D2B2_R2_PARENT_MUTATION, False)],
+    ids=["safe-parent", "unsafe-parent"],
+)
+def test_d2b2_r2_worker_success_returns_and_warm_cache(
+    tmp_path, isolated_dirs, fixture, expected_passive,
+):
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    parent = root / "pkg" / "__init__.py"
+    cold = indexer._process_single_file(str(parent), str(root))
+    assert cold["error"] is None
+    assert cold["source_parse_called"] is True
+    assert type(cold["typing_guard_initializer_passive"]) is bool
+    assert cold["typing_guard_initializer_passive"] is expected_passive
+    assert cold["source_fingerprint"]
+    warm = indexer._process_single_file(str(parent), str(root))
+    assert warm["error"] is None
+    assert warm["source_parse_called"] is False
+    assert warm["cache_hit"] is True
+    assert type(warm["typing_guard_initializer_passive"]) is bool
+    assert warm["typing_guard_initializer_passive"] is expected_passive
+    assert warm["source_fingerprint"] == cold["source_fingerprint"]
+    cached = _cache_data(root, parent)
+    assert cached["import_classification_semantics_version"] == 3
+    assert type(cached["typing_guard_initializer_passive"]) is bool
+    assert cached["typing_guard_initializer_passive"] is expected_passive
+
+
+def test_d2b2_r2_forged_stale_parent_cache_rejected(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B2_R2_PARENT_MUTATION,
+    )
+    original, original_graph = _index_graph(root)
+    assert "pkg.b" in original_graph.hard_edges["pkg.a"]
+    parent = root / "pkg" / "__init__.py"
+    original_fingerprint = original.source_fingerprints_by_module["pkg.__init__"]
+    cached = _cache_data(root, parent)
+    assert cached["import_classification_semantics_version"] == 3
+    assert cached["typing_guard_initializer_passive"] is False
+    cached["typing_guard_initializer_passive"] = True
+    cached["import_classification_semantics_version"] = 2
+    CacheManager(str(root)).set(parent, cached)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    replayed, graph = _index_graph(root)
+    assert replayed.source_fingerprints_by_module["pkg.__init__"] == (
+        original_fingerprint
+    )
+    assert next(
+        item for item in replayed.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    ).type_only is False
+    assert graph.hard_edges["pkg.a"] == {"pkg.b"}
+    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
+    rewritten = _cache_data(root, parent)
+    assert rewritten["import_classification_semantics_version"] == 3
+    assert type(rewritten["typing_guard_initializer_passive"]) is bool
+    assert rewritten["typing_guard_initializer_passive"] is False
+
+
+@pytest.mark.parametrize(
+    "case,malformed",
+    [("missing", None), ("none", None), ("string", "true"), ("integer", 1)],
+)
+def test_d2b2_r2_malformed_current_parent_cache_rejected(
+    tmp_path, isolated_dirs, monkeypatch, case, malformed,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B2_R2_PARENT_MUTATION,
+    )
+    _index_graph(root)
+    parent = root / "pkg" / "__init__.py"
+    cached = _cache_data(root, parent)
+    assert cached["import_classification_semantics_version"] == 3
+    if case == "missing":
+        cached.pop("typing_guard_initializer_passive")
+    else:
+        cached["typing_guard_initializer_passive"] = malformed
+    CacheManager(str(root)).set(parent, cached)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    real_read = indexer.read_source_snapshot
+    real_parse = indexer.parse_source_snapshot
+    read_calls = []
+    parse_calls = []
+
+    def tracked_read(path):
+        read_calls.append(Path(path).resolve())
+        return real_read(path)
+
+    def tracked_parse(snapshot, path):
+        parse_calls.append(Path(path).resolve())
+        return real_parse(snapshot, path)
+
+    monkeypatch.setattr(indexer, "read_source_snapshot", tracked_read)
+    monkeypatch.setattr(indexer, "parse_source_snapshot", tracked_parse)
+    replayed, graph = _index_graph(root)
+    assert len(read_calls) == 3
+    assert len(set(read_calls)) == 3
+    assert parse_calls == [parent.resolve()]
+    assert next(
+        item for item in replayed.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    ).type_only is False
+    assert graph.hard_edges["pkg.a"] == {"pkg.b"}
+    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
+    assert any(
+        set(members) == {"pkg.a", "pkg.b"}
+        for members in _scc_signature(replayed, graph)
+    )
+    rewritten = _cache_data(root, parent)
+    assert rewritten["import_classification_semantics_version"] == 3
+    assert type(rewritten["typing_guard_initializer_passive"]) is bool
+    assert rewritten["typing_guard_initializer_passive"] is False
+
+
+@pytest.mark.parametrize(
+    "fixture",
+    [D2B_NAME_SAFE, D2B2_R2_PARENT_MUTATION],
+    ids=["passive-parent", "unsafe-parent"],
+)
+def test_d2b2_r2_cold_warm_graph_parity(
+    tmp_path, isolated_dirs, monkeypatch, fixture,
+):
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    cold_index, cold_graph = _index_graph(root)
+    cold_imports = _import_signature(cold_index)
+    cold_graph_signature = _graph_signature(cold_index, cold_graph)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    def unexpected_parse(*args, **kwargs):
+        raise AssertionError("complete current warm cache must not parse source")
+
+    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
+    warm_index, warm_graph = _index_graph(root)
+    assert _import_signature(warm_index) == cold_imports
+    assert _graph_signature(warm_index, warm_graph) == cold_graph_signature
+
+
+def test_d2b2_r2_parent_source_fingerprint_change_reclassifies_child(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    safe_index, safe_graph = _index_graph(root)
+    assert "pkg.b" in safe_graph.soft_edges["pkg.a"]
+    parent_fingerprint = safe_index.source_fingerprints_by_module["pkg.__init__"]
+    child_fingerprint = safe_index.source_fingerprints_by_module["pkg.a"]
+
+    (root / "pkg" / "__init__.py").write_text(
+        D2B2_R2_UNSAFE_INITIALIZER, encoding="utf-8",
+    )
+    unsafe_index, unsafe_graph = _index_graph(root)
+    assert unsafe_index.source_fingerprints_by_module["pkg.__init__"] != (
+        parent_fingerprint
+    )
+    assert unsafe_index.source_fingerprints_by_module["pkg.a"] == (
+        child_fingerprint
+    )
+    assert next(
+        item for item in unsafe_index.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    ).type_only is False
+    assert unsafe_graph.hard_edges["pkg.a"] == {"pkg.b"}
+    assert unsafe_graph.hard_edges["pkg.b"] == {"pkg.a"}
+
+
+@pytest.mark.parametrize(
+    "case,fixture",
+    [
+        ("safe-single", D2B_NAME_SAFE),
+        ("unsafe-single", D2B2_R2_PARENT_MUTATION),
+        (
+            "safe-multilevel",
+            {
+                **D2B2_R2_MULTILEVEL_COMMON,
+                "pkg/__init__.py": "pass\n",
+                "pkg/sub/__init__.py": "pass\n",
+            },
+        ),
+        (
+            "unsafe-outer",
+            {
+                **D2B2_R2_MULTILEVEL_COMMON,
+                "pkg/__init__.py": D2B2_R2_UNSAFE_INITIALIZER,
+                "pkg/sub/__init__.py": "pass\n",
+            },
+        ),
+        (
+            "unsafe-inner",
+            {
+                **D2B2_R2_MULTILEVEL_COMMON,
+                "pkg/__init__.py": "pass\n",
+                "pkg/sub/__init__.py": D2B2_R2_UNSAFE_INITIALIZER,
+            },
+        ),
+    ],
+)
+def test_d2b2_r2_inline_process_pool_parent_parity(
+    tmp_path, isolated_dirs, monkeypatch, case, fixture,
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
+
+
+def test_d2b2_r2_original_worker_reindex_retains_hard_graph(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B2_R2_PARENT_MUTATION,
+    )
+    original, graph = _index_graph(root)
+    plan = plan_original_worker_reindex(original, graph.hard_edges)
+    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
+    assert plan.selected_module_ids
+
+    captured = indexer.index_repository(
+        str(root), source_capture_module_ids=plan.selected_module_ids,
+    )
+    assert captured.original_worker_capture_status == (
+        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    )
+    assert plan.selected_module_ids.issubset(
+        captured.original_worker_source_snapshots
+    )
+    for module_id in plan.selected_module_ids:
+        assert captured.original_worker_source_snapshots[
+            module_id
+        ].source_fingerprint == captured.source_fingerprints_by_module[module_id]
+    assert captured.source_fingerprints_by_module == (
+        original.source_fingerprints_by_module
+    )
+
+    reexport_facts = materialize_reexport_facts_by_module(
+        captured.modules,
+        captured.reference_facts_by_module,
+    )
+    trie = build_trie(captured.modules.keys())
+    package_root = detect_package_root(captured.modules, trie)
+    captured_graph = build_graph(
+        captured.modules,
+        trie=trie,
+        package_root=package_root,
+        reexport_facts_by_module=reexport_facts,
+    )
+    assert captured_graph.hard_edges == graph.hard_edges
+    assert captured_graph.soft_edges == graph.soft_edges
+    assert captured_graph.hard_edges["pkg.a"] == {"pkg.b"}
+    assert captured_graph.hard_edges["pkg.b"] == {"pkg.a"}
+
````

## 34. CONTRACT_CONFLICTS

- **DIRECT_EVIDENCE** None observed. All specified production anchors were present in the current local source and the focused command completed without a contract failure.

## 35. DESIGN_GAPS

- **DIRECT_EVIDENCE** None encountered for the literal production instructions or specified test cases. No alternative implementation was selected.

## 36. UNKNOWN / UNSUPPORTED

- **UNKNOWN** Active MCP/LIVE loaded-code adoption; no restart, reload, active FULL or active service mutation was used for this task. The pre-edit Contextor read reported canonical revision 750 and verified source sync, which was used for discovery only.
- **UNKNOWN** Global pytest status and behavior beyond the eight focused modules; global pytest was prohibited.
- **UNKNOWN** General Python runtime behavior outside the explicit synthetic CPython differentials.
- Unsupported dynamic parent initializer behavior was not converted into positive P0/P1B or manifest evidence.

## 37. IMPLEMENTER OBSERVATION ONLY

The implementer observed: exact authorized file scope; compilation exit 0; focused pytest exit 0 with 370 passes; full source/test diffs included; final `git diff --check` exit 0. The specified negative, positive, multilevel, cache, process-pool, original-worker and isolated publication regressions were exercised. The architectural decision on acceptance remains with ChatGPT. Stop after D2B-2-R2.

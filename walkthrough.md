# CONTEXTOR — P1D3-D2B-2 CONSERVATIVE TYPE_ONLY EDGE CLASSIFICATION

## 1. EXECUTIVE VERDICT

**GO for the scoped D2B-2 implementation and focused acceptance gates.** The implementation and synthetic-repository tests meet the supplied literal specification on the executed focused suite. This is a repository source/test result only; it does not establish general Python runtime safety, active LIVE behavior, active service code adoption, or success of the global test suite.

Evidence labels used below:

- **DIRECT_EVIDENCE** — observed command/test output or exact repository state during this task.
- **CODE_PATH_PROVED** — behavior established by current implementation/source inspection.
- **CONTRACT_PROVED** — behavior required by the supplied task contract or exercised by contract-focused assertions.
- **INFERENCE** — conclusion drawn from the direct/code evidence, bounded to the stated scope.
- **UNKNOWN** — not established by this task.

## 2. INITIAL / FINAL HEAD

- **DIRECT_EVIDENCE** Initial HEAD before edits: `5109fb40cb8328c0deaf3acc0df7d3d09f9339ee`.
- **DIRECT_EVIDENCE** Final HEAD: `5109fb40cb8328c0deaf3acc0df7d3d09f9339ee` (unchanged; no Git mutation).
- **DIRECT_EVIDENCE** Initial worktree was clean before this task's edits.

## 3. WORKTREE STATUS

Final task changes are limited to the two authorized existing files, one authorized new test file and this required report:

- `contextor/core/symbol_engine/indexer.py` — modified.
- `tests/test_p1d3_package_cycle_integration.py` — modified.
- `tests/test_p1d3_d2b2_type_only.py` — added.
- `walkthrough.md` — overwritten with this report; its self-diff is excluded below.

No other user changes were present at the initial status check. HEAD stayed fixed. `git diff --check` passed after the final report was written. See §§24–25 for the file list and complete zero-context diffs of every changed source/test file.

## 4. SOURCE-LOCAL CLASSIFICATION

- **CODE_PATH_PROVED** `read_imports` uses the existing pure `recognize_typing_guard(tree, frozenset())` recognizer when an AST tree is available. If it returns no guard, the candidate identity set remains empty.
- **CODE_PATH_PROVED** On a recognized marker, the implementation scans direct module-body statements after the marker, matches only the exact positive guard form, and scans only direct statements in that guard's body. It does not descend into nested control flow or the `else` branch, and it does not rewrite the AST.
- **CODE_PATH_PROVED** Only a direct `ast.Import` with exactly one dotted identifier alias and no `as` binding is authorized. The visitor authorizes by AST node identity, not line or module string. `ImportFrom`, nested imports, unsupported syntax and unauthorized statements retain `type_only=False`.
- **CODE_PATH_PROVED** Existing `is_local` determination, import extraction order and one-`ImportRef`-per-alias behavior are retained. The authorized classification is applied to the exact visited `ast.Import` node.
- **DIRECT_EVIDENCE** The focused negative matrix exercises N01–N24, including missing/assigned/aliased/late/duplicate/conditional markers, nested/function/class/try/else imports, `ImportFrom`, multiple aliases, `as` aliases, undotted imports, and both local typing shadow forms. All assertions passed in the final focused run.

## 5. REPOSITORY-WIDE TYPING VETO

- **CODE_PATH_PROVED** A private finalizer examines the completed module dictionary. If it contains `typing` or `typing.__init__`, it clears every candidate `type_only` flag by creating equivalent frozen `ImportRef` values with `dataclasses.replace`, then replacing each affected frozen `Module` with its imports updated.
- **CODE_PATH_PROVED** The finalizer runs before `RepositoryIndex` construction at both the inline and process-pool result paths. It does not consult host `sys.modules` and does not alter source fingerprints, paths, module identities or other index facts.
- **DIRECT_EVIDENCE** Synthetic reindex tests add and remove `typing.py` and `typing/__init__.py`; the local module vetoes candidates and removal restores eligible classification. Inline and process-pool shadow-veto outputs were both exercised.

## 6. CACHE SEMANTIC INVALIDATION

- **CODE_PATH_PROVED** `IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 1` is an internal worker-cache semantic marker. It is written as `import_classification_semantics_version` with exact integer value `1`.
- **CODE_PATH_PROVED** Immediately after cache lookup, an absent, non-exact-integer or mismatched marker makes cached worker extraction data stale. Extraction reparses the already acquired source snapshot; the original source bytes are not reread just to classify type-only imports. Existing source SHA checks remain in place.
- **CODE_PATH_PROVED** The marker does not alter `SourceSnapshot`, `RepositoryIndex`, public evidence contracts or other schema versions.
- **DIRECT_EVIDENCE** Cold and warm cache outputs match for import references, `type_only`, hard/soft graph and SCC signatures. Tests with stale/missing and version-zero cache markers verify re-extraction from the existing source snapshot, parser invocation and cache rewrite. Source-change reindexing also passed.

## 7. INLINE / PROCESS-POOL PARITY

- **DIRECT_EVIDENCE** Synthetic fixtures were indexed through both the inline and process-pool paths. Comparisons covered final `type_only` classifications, canonical hard edges, soft edges and SCC topology. A repository-wide local-typing shadow veto was included in the process-pool path.
- **DIRECT_EVIDENCE** The process-pool tests executed successfully in this environment; process-pool coverage was not substituted with inline-only assertions.
- **CONTRACT_PROVED** The finalizer is applied before the `RepositoryIndex` is returned in each path.

## 8. CANONICAL HARD / SOFT GRAPH

- **CODE_PATH_PROVED** The existing graph builder remains unchanged and consumes `ImportRef.type_only`: resolved internal type-only module imports contribute soft dependencies; ordinary imports contribute hard dependencies.
- **DIRECT_EVIDENCE** For the eligible NAME and ATTRIBUTE fixtures, the tested graph is exactly:

```text
hard:
  pkg.__init__: []
  pkg.a:        []
  pkg.b:        [pkg.a]
soft:
  pkg.__init__: []
  pkg.a:        [pkg.b]
  pkg.b:        []
```

The canonical import occurrence remains present, with its source-local `type_only=True` classification where the repository-wide veto does not apply.

## 9. SAME-TARGET HARD DOMINANCE

- **DIRECT_EVIDENCE** In the mixed fixture, `pkg.a` has two separate `pkg.b` import occurrences in source order with flags `[True, False]`. The graph retains both `pkg.a -> pkg.b` soft and hard targets; the normal import preserves the hard edge. The reverse `pkg.b -> pkg.a` edge creates a real hard SCC.
- **CODE_PATH_PROVED** No graph-builder changes or target-level hard-edge weakening were made.

## 10. NO-SCC HANDLING

- **DIRECT_EVIDENCE** For eligible inactive-only NAME and ATTRIBUTE fixtures, `analyze_cycle_scenarios(...).components == ()`; the hard-SCC import-site report has no corresponding `pkg.a/pkg.b` component; source-bound evidence has no components; P0 assessment is empty; planning returns `UNAVAILABLE` with `NO_CYCLIC_COMPONENTS`; prepared manifest is absent.
- **DIRECT_EVIDENCE** The isolated official-analysis fixture for `D2B_NAME_SAFE` verifies no prepared receipt is persisted for the dissolved SCC.
- **CONTRACT_PROVED** No positive model assessment, SCC manifest, or receipt is synthesized for a component absent from the canonical hard graph.

## 11. NEGATIVE MATRIX

- **DIRECT_EVIDENCE** N01–N24 pass with ineligible imports remaining hard when they resolve internally and no type-only promotion occurs. This includes both local `typing` identity veto variants. The N14 `ImportFrom`, N15 multiple aliases, N16 aliased import and N24 undotted import are not promoted.
- **DIRECT_EVIDENCE** Existing D2B-1 unsupported-guard rejection tests remain present and pass in the focused integration selection.

## 12. COLD / WARM CACHE

- **DIRECT_EVIDENCE** The fresh-index/warm-cache comparison passes exact import-reference and graph/SCC signature equality for the same synthetic source bytes.
- **DIRECT_EVIDENCE** Reindex after source edits, after adding/removing `typing.py`, and after adding/removing `typing/__init__.py` passed. Assertions cover preservation of module identity/path/fingerprint and unaffected `ImportRef` fields.
- **DIRECT_EVIDENCE** Stale cache classifications are not accepted when the semantic marker is absent or set to an older value; extraction uses the source snapshot already read by the worker.

## 13. ORIGINAL-WORKER REINDEX

- **DIRECT_EVIDENCE** The active-import mixed fixture is captured by the existing original-worker path. A graph rebuilt from the captured modules and canonical reexport facts exactly matches the index graph's hard and soft edges; captured imports match the original index imports.
- **DIRECT_EVIDENCE** Capture status is asserted as `ALL_SELECTED_CAPTURED_NON_ATOMIC` for that fixture. The test does not fabricate capture/result objects.
- **INFERENCE** This establishes the stated synthetic fixture's original-worker reindex parity only; it does not establish active LIVE/runtime adoption.

## 14. D2B-1 TEST MIGRATION

- **DIRECT_EVIDENCE** The prior D2B-1 safe NAME and ATTRIBUTE assertions now separate restricted package-model semantics from canonical graph classification: lexical type-only occurrence and typing marker remain, the `pkg.a -> pkg.b` dependency is soft, the former hard SCC is absent, and fresh-entry package-model results are compared against synthetic CPython subprocess imports.
- **DIRECT_EVIDENCE** ELSE hazard/safe fixtures retain an actual hard SCC and their model, P0/P1B and manifest assertions. The original-worker v2, forged-marker and official isolated FULL/receipt tests now use `D2B_ELSE_SAFE` so each still exercises a genuine surviving SCC. An evidence-token assertion checks source-order distinction between ELSE hazard/safe cases.
- **DIRECT_EVIDENCE** No P0/P1B implementation or evidence schema was changed.

## 15. CPYTHON DIFFERENTIAL

- **DIRECT_EVIDENCE** Explicitly authored synthetic package fixtures execute in fresh isolated CPython subprocesses through the existing `run_synthetic_import` harness (`-I -B`). For NAME/ATTRIBUTE cases, restricted package-model fresh-entry outcomes agree with actual subprocess results. In the mixed active-import case, entry through `pkg.a` fails with CPython's partially-initialized-module error and entry through `pkg.b` succeeds, matching the model outcomes.
- **CONTRACT_PROVED** These runs are differential checks for the authored fixtures; they are not a general Python runtime-safety proof.

## 16. P0 GENUINE EVIDENCE

- **DIRECT_EVIDENCE** The mixed fixture's surviving hard SCC produces one P0 assessment with `evidence_state=DECLARED_INPUTS_CONSISTENT`. ELSE hazard/safe surviving-SCC assertions remain in the integration suite and pass.
- **DIRECT_EVIDENCE** The dissolved inactive-only SCC produces no P0 component result. No positive evidence is created for that absent component.

## 17. P1B GENUINE REPLAY

- **DIRECT_EVIDENCE** The mixed fixture's captured original source snapshots produce one P1B assessment with `bytes_state=BYTE_AST_CONSISTENT_NON_ATOMIC`. Genuine surviving ELSE SCC tests retain the corresponding source-byte checks.
- **CONTRACT_PROVED** This is non-atomic replay evidence under the existing contract; it is not an atomicity or LIVE proof.

## 18. P1B FORGED REPLAY

- **DIRECT_EVIDENCE** The forged marker-event regression now uses the surviving `D2B_ELSE_SAFE` SCC. It recomputes the caller-controlled evidence token after forging the event and asserts P0 `DECLARED_INPUTS_CONSISTENT` while P1B returns `MODEL_REPLAY_MISMATCH`.
- **DIRECT_EVIDENCE** The test passed in the focused suite; P0/P1B production code was not modified.

## 19. MANIFEST V2

- **DIRECT_EVIDENCE** Original-worker preparation v2 is exercised using the genuine surviving `D2B_ELSE_SAFE` SCC. The existing non-atomic preparation contract remains covered by the focused tests.
- **DIRECT_EVIDENCE** For dissolved NAME/ATTRIBUTE hard SCCs, the test asserts no prepared manifest and the planner's `NO_CYCLIC_COMPONENTS` result.
- **UNKNOWN** No additional manifest schema, publication-binding or receipt behavior outside the executed isolated tests was probed.

## 20. OFFICIAL ISOLATED FULL

- **DIRECT_EVIDENCE** The focused suite runs the existing official isolated facade/publication regression with `D2B_ELSE_SAFE`, requiring prepared-unpublished non-atomic output, manifest v2, prepared co-publication v2, model all-fresh-member-entries pass, receipt verification true and `live_publish_status=success` in its isolated harness.
- **DIRECT_EVIDENCE** A separate isolated NAME-safe analysis asserts the dissolved SCC has no prepared manifest/receipt persisted.
- **CONTRACT_PROVED** The term “official” here refers to the test's isolated synthetic facade/persistence harness. It does not mean an active Contextor service/LIVE call was performed. No FULL ran against the active repository or active LIVE service.

## 21. RECEIPT V2

- **DIRECT_EVIDENCE** Receipt v2 verification is exercised by the isolated `D2B_ELSE_SAFE` publication test and passes. The same focused suite verifies no receipt is persisted for the dissolved NAME-safe SCC.
- **UNKNOWN** This does not certify receipt behavior for any active service or runtime process.

## 22. REGRESSION RESULTS

- **DIRECT_EVIDENCE** Final specified focused suite result: `304 passed in 54.20s`.
- **DIRECT_EVIDENCE** The suite included the new D2B-2 tests, package-cycle integration, package-model, scenario, evidence, original-worker preparation, receipt and isolated official-publication tests.
- **DIRECT_EVIDENCE** No global pytest suite was run. Tests were restricted to synthetic fixtures/isolation used by those focused test modules; no active repository FULL/LIVE mutation was performed.

### Acceptance gates

| Gate | Result | Evidence boundary |
| --- | --- | --- |
| G01 NAME-form qualified import is soft | PASS | NAME fixture graph assertions |
| G02 ATTRIBUTE-form qualified import is soft | PASS | ATTRIBUTE fixture graph assertions |
| G03 ELSE imports remain hard | PASS | ELSE hazard/safe integration fixtures |
| G04 Mixed guarded/active imports preserve hard edge | PASS | Mixed fixture has separate `[True, False]` occurrences and hard plus soft target |
| G05 Exact source occurrence distinction is preserved | PASS | Node-identity authorization and ordered mixed-import assertion |
| G06 Unsupported import forms are not promoted | PASS | N01–N24 negative matrix |
| G07 Local `typing.py` veto | PASS | Add/remove shadow reindex tests |
| G08 Local `typing/__init__.py` veto | PASS | Add/remove shadow reindex tests |
| G09 Inline/process-pool parity | PASS | Both execution paths compared on synthetic fixtures |
| G10 Cold/warm cache parity | PASS | Import, hard/soft edge and SCC signatures compared |
| G11 Stale classification cache rejected | PASS | Missing/version-zero cache semantic marker regressions |
| G12 Original-worker reindex reproduces canonical graph | PASS | Captured modules and canonical reexport graph compared |
| G13 Inactive-only hard SCC disappears without fabricated MODEL_PASS | PASS | No scenarios/P0 components or receipt for NAME/ATTRIBUTE safe cases |
| G14 Planner handles `NO_CYCLIC_COMPONENTS` | PASS | Exact status/reason asserted |
| G15 Genuine surviving hard SCC retains fresh-entry model assessments | PASS | ELSE and mixed surviving-SCC model regressions |
| G16 P0/P1B validate genuine surviving-SCC evidence | PASS | Genuine surviving SCC assertions in integration tests |
| G17 P1B rejects forged model events | PASS | Forged marker-event regression asserts `MODEL_REPLAY_MISMATCH` |
| G18 Isolated FULL and receipt v2 for surviving SCC | PASS | `D2B_ELSE_SAFE` isolated publication/receipt test |
| G19 No receipt for dissolved SCC | PASS | NAME-safe isolated analysis checks no persisted receipt |
| G20 D1/D2A/D2B-1 regression semantics | PASS | Named regression files included in final focused command |
| G21 No unauthorized production changes | PASS | Final changed source/test paths match allowlist |
| G22 No active FULL/LIVE mutation | PASS | Only focused isolated synthetic tests were run |

**DIRECT_EVIDENCE** These are scoped acceptance results from the listed assertions and focused test command, not global-suite or active-runtime certification.

## 23. EXACT COMMANDS / EXIT CODES

Commands ran from `C:\Temp\Contextor_Repo` using the repository virtual environment:

```text
& .\.venv\Scripts\python.exe -m py_compile contextor/core/symbol_engine/indexer.py
EXIT CODE: 0

& .\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_d2b2_type_only.py tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py
EXIT CODE: 0
RESULT: 304 passed in 54.20s

git diff --check
EXIT CODE: 0
```

During test authoring, the first D2B-2 test-file run exposed three assertion/fixture issues (missing `monkeypatch` fixture arguments and an incorrect expected module-presence assertion); these were corrected in the authorized test files. The first integration selection exposed an incorrect helper assumption for the ATTRIBUTE marker fixture; it was corrected. The subsequent combined focused runs and final eight-file suite passed. These were test-authoring failures, not unresolved production failures.

## 24. FILES_CHANGED

1. `contextor/core/symbol_engine/indexer.py` — production source, authorized.
2. `tests/test_p1d3_package_cycle_integration.py` — test changes, authorized.
3. `tests/test_p1d3_d2b2_type_only.py` — new test file, authorized.
4. `walkthrough.md` — required task report, overwritten; self-diff omitted to avoid recursive report content.

No other production, test or documentation file was changed. The complete actual source/test diffs follow in §25.

## 25. FULL ACTUAL_DIFF

The following are complete zero-context Git diffs, including every added and removed line for each changed source/test file. The report file's own diff is intentionally excluded.

### `contextor/core/symbol_engine/indexer.py`

### `tests/test_p1d3_package_cycle_integration.py`

### `tests/test_p1d3_d2b2_type_only.py` (new file)

## 26. CONTRACT CONFLICTS

- **DIRECT_EVIDENCE** No exact requirement/code-contract conflict remained in the implemented scope. Both result-return paths, the existing resolver behavior, original-worker reindex, and test harness contracts were exercised by focused checks.
- **UNKNOWN** This is not an assessment of untested environments, external import hooks, or arbitrary Python runtime behavior.

## 27. UNKNOWN / UNSUPPORTED

- **UNKNOWN** Whether any active Contextor MCP/LIVE process has adopted the changed `indexer.py` implementation. No live endpoint, process reload or restart was used in this stage.
- **UNKNOWN** Whether arbitrary dynamic import behavior, custom import hooks, environment differences or runtime side effects outside the explicit fixtures alter a program's behavior.
- **UNKNOWN** Global test-suite status; global pytest was prohibited and not run.
- **UNKNOWN** Compatibility outside the existing source/index/cache contracts and focused schema-preservation assertions.

## 28. FINAL GO / PARTIAL / NO_GO

**GO — scoped D2B-2 implementation.** The authorized production file and tests implement the specified conservative classification, repository-wide typing identity veto, stale-cache semantic invalidation and inline/process-pool finalization. The focused acceptance/regression suite passed (`304 passed`). No unauthorized source/test/docs files, Git state changes, active FULL/LIVE operations, restarts, or schema changes occurred.

This verdict is bounded to the supplied D2B-2 scope and focused evidence. It makes no claim of global suite success, general Python runtime safety, or active LIVE/runtime adoption. Stop here; do not start D2B-3 or any later stage without a new explicit `proceduj`.

````diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index e3d9488..73fd28d 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -34,0 +35,4 @@ from contextor.core.analysis.test_context import (
+from contextor.core.cycle_semantics.typing_guard import (
+    matches_typing_guard,
+    recognize_typing_guard,
+)
@@ -67,0 +72 @@ TEST_FACTS_SCHEMA_VERSION = 1
+IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 1
@@ -213 +218,4 @@ class AdvancedImportVisitor(ast.NodeVisitor):
-    def __init__(self):
+    def __init__(
+        self,
+        type_only_statement_ids: frozenset[int] | None = None,
+    ):
@@ -217,0 +226,3 @@ class AdvancedImportVisitor(ast.NodeVisitor):
+        self._type_only_statement_ids = frozenset(
+            type_only_statement_ids or ()
+        )
@@ -233,0 +245,10 @@ class AdvancedImportVisitor(ast.NodeVisitor):
+        type_only = False
+        if (
+            id(node) in self._type_only_statement_ids
+            and len(node.names) == 1
+            and node.names[0].asname is None
+        ):
+            parts = node.names[0].name.split(".")
+            type_only = len(parts) > 1 and all(
+                part.isidentifier() for part in parts
+            )
@@ -242,0 +264 @@ class AdvancedImportVisitor(ast.NodeVisitor):
+                    type_only=type_only,
@@ -286 +308,40 @@ def read_imports(
-    visitor = AdvancedImportVisitor()
+    type_only_statement_ids: set[int] = set()
+    guard = recognize_typing_guard(tree, frozenset())
+    if guard is not None and isinstance(tree, ast.Module):
+        marker_position = next(
+            (
+                position
+                for position, statement in enumerate(tree.body)
+                if statement is guard.marker_statement
+            ),
+            None,
+        )
+        if marker_position is not None:
+            for statement in tree.body[marker_position + 1:]:
+                if (
+                    not isinstance(statement, ast.If)
+                    or not matches_typing_guard(
+                        statement.test,
+                        guard.form,
+                    )
+                ):
+                    continue
+
+                for body_statement in statement.body:
+                    if (
+                        not isinstance(body_statement, ast.Import)
+                        or len(body_statement.names) != 1
+                    ):
+                        continue
+                    alias = body_statement.names[0]
+                    parts = alias.name.split(".")
+                    if (
+                        alias.asname is None
+                        and len(parts) > 1
+                        and all(part.isidentifier() for part in parts)
+                    ):
+                        type_only_statement_ids.add(id(body_statement))
+
+    visitor = AdvancedImportVisitor(
+        frozenset(type_only_statement_ids)
+    )
@@ -555,0 +617,10 @@ def _process_single_file(
+    if (
+        cached_data is not None
+        and (
+            type(cached_data.get("import_classification_semantics_version"))
+            is not int
+            or cached_data.get("import_classification_semantics_version")
+            != IMPORT_CLASSIFICATION_SEMANTICS_VERSION
+        )
+    ):
+        cached_data = None
@@ -926,0 +998,3 @@ def _process_single_file(
+            "import_classification_semantics_version": (
+                IMPORT_CLASSIFICATION_SEMANTICS_VERSION
+            ),
@@ -1929,0 +2004,18 @@ def index_repository(
+
+    def _finalize_type_only_imports() -> None:
+        if "typing" not in modules and "typing.__init__" not in modules:
+            return
+
+        for module_id, module in modules.items():
+            if not any(import_ref.type_only for import_ref in module.imports):
+                continue
+            modules[module_id] = dataclasses.replace(
+                module,
+                imports=[
+                    dataclasses.replace(import_ref, type_only=False)
+                    if import_ref.type_only
+                    else import_ref
+                    for import_ref in module.imports
+                ],
+            )
+
@@ -1978,0 +2071 @@ def index_repository(
+        _finalize_type_only_imports()
@@ -2227,0 +2321 @@ def index_repository(
+    _finalize_type_only_imports()
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index 9985068..b2a90ac 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -7,0 +8 @@ from dataclasses import replace
+from pathlib import Path
@@ -31,0 +33 @@ from contextor.core.cycle_semantics.original_worker_reindex_planning import plan
+from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
@@ -48 +50 @@ from contextor.core.reference.shared import (
-from contextor.core.source import parse_source_snapshot
+from contextor.core.source import parse_source_snapshot, read_source_snapshot
@@ -188,0 +191,12 @@ D2B_ELSE_SAFE = {
+D2B2_MIXED_ACTIVE = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.b\n"
+        "import pkg.b\n"
+        "value = 1\n"
+    ),
+    "pkg/b.py": "from pkg.a import value\n",
+}
+
@@ -908,0 +923,94 @@ def _d2a_source_evidence(root):
+def _assert_d2b2_inactive_no_hard_scc(
+    tmp_path, fixture, expected, expected_branch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    index, graph = _d2a_canonical_index_graph(root)
+    assert graph.hard_edges == {
+        "pkg.__init__": set(),
+        "pkg.a": set(),
+        "pkg.b": {"pkg.a"},
+    }
+    assert graph.soft_edges == {
+        "pkg.__init__": set(),
+        "pkg.a": {"pkg.b"},
+        "pkg.b": set(),
+    }
+
+    imports_b = [
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.b" and not item.is_from_import
+    ]
+    assert len(imports_b) == 1
+    assert imports_b[0].type_only is True
+    assert imports_b[0].is_local is False
+    typing_imports = [
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "typing"
+    ]
+    assert len(typing_imports) == 1
+    assert typing_imports[0].type_only is False
+    assert typing_imports[0].is_from_import is (fixture is D2B_NAME_SAFE)
+
+    source_snapshots = {
+        module_id: read_source_snapshot(Path(root, module.path))
+        for module_id, module in index.modules.items()
+    }
+    parsed = {
+        module_id: parse_source_snapshot(snapshot, module_id)
+        for module_id, snapshot in source_snapshots.items()
+    }
+    source_trees = {
+        module_id: source.tree
+        for module_id, source in parsed.items()
+    }
+    guard = recognize_typing_guard(
+        source_trees["pkg.a"],
+        frozenset(index.modules),
+    )
+    assert guard is not None
+
+    site_report = analyze_cyclic_import_sites(graph.hard_edges, parsed)
+    assert not any(
+        {"pkg.a", "pkg.b"}.issubset(set(component.members))
+        for component in site_report.components
+    )
+    scenarios = analyze_cycle_scenarios(graph.hard_edges, source_trees)
+    assert scenarios.components == ()
+
+    for entry, succeeds in expected.items():
+        modeled = evaluate_package_import_order(source_trees, entry)
+        actual = run_synthetic_import(root, entry)
+        assert (modeled.outcome == "MODEL_PASS") is succeeds
+        assert (actual.returncode == 0) is succeeds
+        if entry == "pkg.a":
+            assert any(
+                event.operation == "TYPING_MARKER_IMPORT"
+                for event in modeled.events
+            )
+            assert not any(
+                event.operation == "START_IMPORT"
+                and event.target == "pkg.b"
+                for event in modeled.events
+            )
+
+    assert expected_branch == "BODY"
+    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
+    assert evidence.components == ()
+    snapshot = _snapshot(root, index, graph)
+    p0 = assess_index_bound_scc_models(
+        graph.hard_edges,
+        index.source_fingerprints_by_module,
+        snapshot,
+        evidence,
+    )
+    assert p0 == ()
+    plan = plan_original_worker_reindex(index, graph.hard_edges)
+    assert plan.status == "UNAVAILABLE"
+    assert plan.reason == "NO_CYCLIC_COMPONENTS"
+    prepared = prepare_original_worker_cycle_manifest(
+        index, graph.hard_edges, snapshot,
+    )
+    assert prepared.manifest is None
+    assert prepared.status != "PREPARED_UNPUBLISHED_NON_ATOMIC"
+
+
@@ -1315,0 +1424,9 @@ def _assert_p1d3_d2b_supported_fixture(
+    if fixture is D2B_NAME_SAFE or fixture is D2B_ATTR_SAFE:
+        _assert_d2b2_inactive_no_hard_scc(
+            tmp_path,
+            fixture,
+            expected,
+            expected_branch,
+        )
+        return
+
@@ -1480 +1597 @@ def test_p1d3_d2b_original_worker_prepares_v2(tmp_path, isolated_dirs):
-    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    root = write_synthetic_repository(tmp_path / "repo", D2B_ELSE_SAFE)
@@ -1499 +1616 @@ def test_p1d3_d2b_forged_marker_event_rejected(
-    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    root = write_synthetic_repository(tmp_path / "repo", D2B_ELSE_SAFE)
@@ -1558 +1675 @@ def test_p1d3_d2b_official_isolated_full_receipt(
-    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    root = write_synthetic_repository(tmp_path / "repo", D2B_ELSE_SAFE)
@@ -1580,0 +1698,114 @@ def test_p1d3_d2b_official_isolated_full_receipt(
+
+
+def test_p1d3_d2b_else_source_order_changes_evidence_token(
+    tmp_path, isolated_dirs,
+):
+    hazard_root = write_synthetic_repository(
+        tmp_path / "hazard", D2B_ELSE_HAZARD,
+    )
+    safe_root = write_synthetic_repository(
+        tmp_path / "safe", D2B_ELSE_SAFE,
+    )
+    _, hazard_graph, _, _, hazard_evidence, _ = _d2a_source_evidence(
+        hazard_root,
+    )
+    _, safe_graph, _, _, safe_evidence, _ = _d2a_source_evidence(
+        safe_root,
+    )
+    assert hazard_graph.hard_edges == safe_graph.hard_edges
+    assert hazard_evidence.components[0].evidence_token != (
+        safe_evidence.components[0].evidence_token
+    )
+
+
+def test_p1d3_d2b2_active_import_dominates_type_only(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2B2_MIXED_ACTIVE,
+    )
+    index, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
+    imports_b = [
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.b" and not item.is_from_import
+    ]
+    assert len(imports_b) == 2
+    assert [item.type_only for item in imports_b] == [True, False]
+    assert graph.hard_edges["pkg.a"] == {"pkg.b"}
+    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
+    assert graph.soft_edges["pkg.a"] == {"pkg.b"}
+    assert captured.original_worker_capture_status == (
+        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    )
+
+    captured_reexport_facts = materialize_reexport_facts_by_module(
+        captured.modules,
+        captured.reference_facts_by_module,
+    )
+    captured_trie = build_trie(captured.modules.keys())
+    captured_package_root = detect_package_root(
+        captured.modules,
+        captured_trie,
+    )
+    captured_graph = build_graph(
+        captured.modules,
+        trie=captured_trie,
+        package_root=captured_package_root,
+        reexport_facts_by_module=captured_reexport_facts,
+    )
+    assert captured_graph.hard_edges == graph.hard_edges
+    assert captured_graph.soft_edges == graph.soft_edges
+    assert captured.modules["pkg.a"].imports == index.modules["pkg.a"].imports
+
+    scenario = evidence.scenarios.components[0]
+    assert scenario.classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
+    assert scenario.coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
+    assessment_a = next(
+        item for item in scenario.entry_assessments
+        if item.entry_module == "pkg.a"
+    )
+    assessment_b = next(
+        item for item in scenario.entry_assessments
+        if item.entry_module == "pkg.b"
+    )
+    assert assessment_a.outcome == "EARLY_BINDING_HAZARD"
+    assert assessment_b.outcome == "MODEL_PASS"
+    actual_a = run_synthetic_import(root, "pkg.a")
+    actual_b = run_synthetic_import(root, "pkg.b")
+    assert actual_a.returncode != 0
+    assert "partially initialized module" in actual_a.stderr
+    assert actual_b.returncode == 0
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
+
+@pytest.mark.live
+def test_p1d3_d2b2_dissolved_scc_does_not_publish_receipt(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    with _official_live(root, monkeypatch):
+        _, result = ContextorFacade.analyze_project(
+            str(root), cycle_source_preparation_preview=True,
+            cycle_source_publication_opt_in=True,
+        )
+        state, _ = _persisted(root)
+        preview = result.cycle_source_preparation_preview
+        assert preview is None or preview.manifest is None
+        assert getattr(state, "cycle_source_publication", None) is None
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
new file mode 100644
index 0000000..00baa48
--- /dev/null
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -0,0 +1,489 @@
+"""D2B-2 indexer classification, cache and execution-mode regressions."""
+
+from __future__ import annotations
+
+import ast
+import json
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+from contextor.core.analysis.cache_manager import CacheManager
+from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
+from contextor.core.graph.graph import build_graph
+from contextor.core.graph.resolver import build_trie, detect_package_root
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
+from contextor.core.symbol_engine import indexer
+from tests.cycle_semantics_lab import write_synthetic_repository
+
+
+D2B_NAME_SAFE = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.b\n"
+        "value = 1\n"
+    ),
+    "pkg/b.py": "from pkg.a import value\n",
+}
+
+D2B2_NEGATIVE_CASES = [
+    ("N01-no-marker", "if TYPE_CHECKING:\n    import pkg.b\n", {}, {"pkg.b"}),
+    (
+        "N02-assigned-before",
+        "TYPE_CHECKING = True\nfrom typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N03-assigned-after",
+        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
+        "    import pkg.b\nTYPE_CHECKING = True\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N04-aliased-marker",
+        "from typing import TYPE_CHECKING as TC\nif TYPE_CHECKING:\n"
+        "    import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N05-aliased-typing",
+        "import typing as t\nif typing.TYPE_CHECKING:\n"
+        "    import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N06-negated",
+        "from typing import TYPE_CHECKING\nif not TYPE_CHECKING:\n"
+        "    import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N07-is-false",
+        "from typing import TYPE_CHECKING\nif TYPE_CHECKING is False:\n"
+        "    import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N08-equals-false",
+        "import typing\nif typing.TYPE_CHECKING == False:\n"
+        "    import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N09-nested-if-import",
+        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
+        "    if True:\n        import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N10-function-import",
+        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
+        "    def load():\n        import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N11-class-import",
+        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
+        "    class Loader:\n        import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N12-try-import",
+        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
+        "    try:\n        import pkg.b\n"
+        "    except ImportError:\n        pass\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N13-else-import",
+        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
+        "    pass\nelse:\n    import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N14-from-import",
+        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
+        "    from pkg import b\n",
+        {}, {"pkg.__init__"},
+    ),
+    (
+        "N15-multiple-aliases",
+        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
+        "    import pkg.b, pkg.c\n",
+        {"pkg/c.py": "pass\n"}, {"pkg.b", "pkg.c"},
+    ),
+    (
+        "N16-as-alias",
+        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
+        "    import pkg.b as child\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N17-local-typing-module",
+        D2B_NAME_SAFE["pkg/a.py"],
+        {"typing.py": "pass\n"}, {"pkg.b"},
+    ),
+    (
+        "N18-local-typing-package",
+        D2B_NAME_SAFE["pkg/a.py"],
+        {"typing/__init__.py": "pass\n"}, {"pkg.b"},
+    ),
+    (
+        "N19-marker-after-effect",
+        "import pkg.b\nfrom typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    pass\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N20-duplicate-marker",
+        "from typing import TYPE_CHECKING\nfrom typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N21-conditional-marker",
+        "if True:\n    from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N22-marker-shadow-import",
+        "from typing import TYPE_CHECKING\nfrom other import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N23-nested-guard",
+        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
+        "    if TYPE_CHECKING:\n        import pkg.b\n",
+        {}, {"pkg.b"},
+    ),
+    (
+        "N24-undotted-import",
+        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
+        "    import pkg\n",
+        {}, {"pkg.__init__"},
+    ),
+]
+
+
+@pytest.fixture(autouse=True)
+def _inline_workers(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _index_graph(root):
+    index = indexer.index_repository(str(root))
+    reexport_facts = materialize_reexport_facts_by_module(
+        index.modules,
+        index.reference_facts_by_module,
+    )
+    trie = build_trie(index.modules.keys())
+    package_root = detect_package_root(index.modules, trie)
+    graph = build_graph(
+        index.modules,
+        trie=trie,
+        package_root=package_root,
+        reexport_facts_by_module=reexport_facts,
+    )
+    return index, graph
+
+
+def _import_signature(index):
+    return tuple(
+        (
+            module_id,
+            tuple(
+                (
+                    item.module,
+                    item.level,
+                    tuple(item.names),
+                    item.is_from_import,
+                    item.is_local,
+                    item.type_only,
+                )
+                for item in module.imports
+            ),
+        )
+        for module_id, module in sorted(index.modules.items())
+    )
+
+
+def _scc_signature(index, graph):
+    trees = {
+        module_id: ast.parse(
+            Path(module.absolute_path).read_text(encoding="utf-8")
+        )
+        for module_id, module in index.modules.items()
+    }
+    report = analyze_cycle_scenarios(graph.hard_edges, trees)
+    return tuple(tuple(component.members) for component in report.components)
+
+
+def _graph_signature(index, graph):
+    return (
+        tuple(
+            (module_id, tuple(sorted(targets)))
+            for module_id, targets in sorted(graph.hard_edges.items())
+        ),
+        tuple(
+            (module_id, tuple(sorted(targets)))
+            for module_id, targets in sorted(graph.soft_edges.items())
+        ),
+        _scc_signature(index, graph),
+    )
+
+
+def _cache_data(root: Path, source: Path) -> dict:
+    manager = CacheManager(str(root))
+    return json.loads(
+        manager._get_cache_file_path(source).read_text(encoding="utf-8")
+    )["data"]
+
+
+def test_cold_and_warm_worker_cache_match_type_only_graph(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    cold_index, cold_graph = _index_graph(root)
+    cold_imports = _import_signature(cold_index)
+    cold_graph_signature = _graph_signature(cold_index, cold_graph)
+    source = root / "pkg" / "a.py"
+    cached = _cache_data(root, source)
+    assert cached["import_classification_semantics_version"] == 1
+    assert next(
+        item for item in cached["imports"] if item["module"] == "pkg.b"
+    )["type_only"] is True
+
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    def unexpected_parse(*args, **kwargs):
+        raise AssertionError("current warm cache must not parse source")
+
+    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
+    warm_index, warm_graph = _index_graph(root)
+
+    assert _import_signature(warm_index) == cold_imports
+    assert _graph_signature(warm_index, warm_graph) == cold_graph_signature
+
+
+@pytest.mark.parametrize("stored_version", [None, 0], ids=["absent", "old"])
+def test_stale_import_classification_cache_reparses_same_snapshot(
+    tmp_path, isolated_dirs, stored_version, monkeypatch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    indexer.index_repository(str(root))
+    source = root / "pkg" / "a.py"
+    cached = _cache_data(root, source)
+    for item in cached["imports"]:
+        if item["module"] == "pkg.b":
+            item["type_only"] = False
+    if stored_version is None:
+        cached.pop("import_classification_semantics_version", None)
+    else:
+        cached["import_classification_semantics_version"] = stored_version
+    CacheManager(str(root)).set(source, cached)
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
+    result = indexer.index_repository(str(root))
+
+    assert len(read_calls) == 3
+    assert len(set(read_calls)) == 3
+    assert parse_calls == [(root / "pkg" / "a.py").resolve()]
+    assert any(
+        item.module == "pkg.b" and item.type_only
+        for item in result.modules["pkg.a"].imports
+    )
+    rewritten = _cache_data(root, source)
+    assert rewritten["import_classification_semantics_version"] == 1
+    assert next(
+        item for item in rewritten["imports"] if item["module"] == "pkg.b"
+    )["type_only"] is True
+
+
+def test_source_changes_and_typing_shadow_add_remove_reclassify(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    original_bytes = (root / "pkg" / "a.py").read_bytes()
+    initial, initial_graph = _index_graph(root)
+    source_fingerprint = initial.source_fingerprints_by_module["pkg.a"]
+    initial_module = initial.modules["pkg.a"]
+    initial_imports = tuple(initial_module.imports)
+    assert next(
+        item for item in initial.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    ).type_only is True
+    assert initial_graph.soft_edges["pkg.a"] == {"pkg.b"}
+
+    source = root / "pkg" / "a.py"
+    source.write_text("value = 1\n", encoding="utf-8")
+    changed, changed_graph = _index_graph(root)
+    assert all(not item.type_only for item in changed.modules["pkg.a"].imports)
+    assert changed_graph.soft_edges["pkg.a"] == set()
+    assert "pkg.b" not in changed_graph.hard_edges["pkg.a"]
+
+    source.write_bytes(original_bytes)
+    restored, restored_graph = _index_graph(root)
+    assert restored.source_fingerprints_by_module["pkg.a"] == source_fingerprint
+    assert next(
+        item for item in restored.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    ).type_only is True
+    assert restored_graph.soft_edges["pkg.a"] == {"pkg.b"}
+
+    simple_shadow = root / "typing.py"
+    simple_shadow.write_text("pass\n", encoding="utf-8")
+    shadowed, shadowed_graph = _index_graph(root)
+    assert "typing" in shadowed.modules
+    assert shadowed.source_fingerprints_by_module["pkg.a"] == source_fingerprint
+    assert all(not item.type_only for item in shadowed.modules["pkg.a"].imports)
+    shadowed_module = shadowed.modules["pkg.a"]
+    assert (
+        shadowed_module.module_id,
+        shadowed_module.path,
+        shadowed_module.absolute_path,
+    ) == (
+        initial_module.module_id,
+        initial_module.path,
+        initial_module.absolute_path,
+    )
+    assert [replace(item, type_only=False) for item in initial_imports] == (
+        shadowed_module.imports
+    )
+    assert "pkg.b" in shadowed_graph.hard_edges["pkg.a"]
+    assert next(
+        item for item in _cache_data(root, source)["imports"]
+        if item["module"] == "pkg.b"
+    )["type_only"] is True
+
+    simple_shadow.unlink()
+    unshadowed, unshadowed_graph = _index_graph(root)
+    assert "pkg.b" in unshadowed.modules
+    assert next(
+        item for item in unshadowed.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    ).type_only is True
+    assert unshadowed_graph.soft_edges["pkg.a"] == {"pkg.b"}
+
+    package_shadow = root / "typing" / "__init__.py"
+    package_shadow.parent.mkdir(parents=True, exist_ok=True)
+    package_shadow.write_text("pass\n", encoding="utf-8")
+    package_shadowed, package_graph = _index_graph(root)
+    assert "typing.__init__" in package_shadowed.modules
+    assert all(
+        not item.type_only
+        for item in package_shadowed.modules["pkg.a"].imports
+    )
+    assert "pkg.b" in package_graph.hard_edges["pkg.a"]
+
+    package_shadow.unlink()
+    package_shadow.parent.rmdir()
+    package_unshadowed, package_unshadowed_graph = _index_graph(root)
+    assert next(
+        item for item in package_unshadowed.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    ).type_only is True
+    assert package_unshadowed_graph.soft_edges["pkg.a"] == {"pkg.b"}
+
+
+def test_inline_and_process_pool_classification_parity(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    inline_root = write_synthetic_repository(
+        tmp_path / "inline", D2B_NAME_SAFE,
+    )
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    inline_index, inline_graph = _index_graph(inline_root)
+
+    pool_root = write_synthetic_repository(
+        tmp_path / "pool", D2B_NAME_SAFE,
+    )
+    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
+    pool_index, pool_graph = _index_graph(pool_root)
+
+    assert _import_signature(pool_index) == _import_signature(inline_index)
+    assert _graph_signature(pool_index, pool_graph) == (
+        _graph_signature(inline_index, inline_graph)
+    )
+    assert pool_index.original_worker_capture_status == "NOT_REQUESTED"
+
+
+def test_inline_and_process_pool_typing_shadow_veto_parity(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    fixture = {
+        **D2B_NAME_SAFE,
+        "typing.py": "pass\n",
+    }
+    inline_root = write_synthetic_repository(
+        tmp_path / "inline", fixture,
+    )
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    inline_index, inline_graph = _index_graph(inline_root)
+
+    pool_root = write_synthetic_repository(
+        tmp_path / "pool", fixture,
+    )
+    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
+    pool_index, pool_graph = _index_graph(pool_root)
+
+    assert _import_signature(pool_index) == _import_signature(inline_index)
+    assert _graph_signature(pool_index, pool_graph) == (
+        _graph_signature(inline_index, inline_graph)
+    )
+    assert all(
+        not item.type_only for item in pool_index.modules["pkg.a"].imports
+    )
+    assert "pkg.b" in pool_graph.hard_edges["pkg.a"]
+
+
+@pytest.mark.parametrize(
+    "case,source,extra,expected_hard_targets",
+    D2B2_NEGATIVE_CASES,
+    ids=[item[0] for item in D2B2_NEGATIVE_CASES],
+)
+def test_unsupported_imports_remain_non_type_only_and_hard(
+    tmp_path, isolated_dirs, case, source, extra, expected_hard_targets,
+):
+    files = {
+        "pkg/__init__.py": "pass\n",
+        "pkg/a.py": source,
+        "pkg/b.py": "from pkg.a import value\n",
+        **extra,
+    }
+    root = write_synthetic_repository(tmp_path / case, files)
+    index, graph = _index_graph(root)
+
+    imports = index.modules["pkg.a"].imports
+    assert imports
+    assert all(item.type_only is False for item in imports)
+    assert expected_hard_targets.issubset(graph.hard_edges["pkg.a"])
+    if case == "N10-function-import":
+        assert next(item for item in imports if item.module == "pkg.b").is_local
+    if case == "N14-from-import":
+        assert any(item.module == "pkg" and item.is_from_import for item in imports)
+    if case == "N15-multiple-aliases":
+        assert [item.module for item in imports if item.module in {"pkg.b", "pkg.c"}] == [
+            "pkg.b", "pkg.c",
+        ]
+
````

# CONTEXTOR P1D3-D2B-4-R1 — implementer report

## 1. IMPLEMENTER OBSERVATION
DIRECT_EVIDENCE: Literal R1 project-wide closed-effect proof implemented within the allowlist. This is not architectural GO.

## 2. INITIAL/FINAL HEAD
DIRECT_EVIDENCE: Initial and final HEAD `1a8d2c60b3bad3981a2ab0e8ba26e4fe9d58be95`; no Git mutation.

## 3. WORKTREE STATUS
DIRECT_EVIDENCE: Initially clean. Final source/test status: the three allowlisted files modified; this report is also modified.

## 4. ROOT CAUSE
DIRECT_EVIDENCE: The D2B-4 known-pattern detector returns False for `typing.__dict__.__ior__` and aliased `update` while isolated CPython launchers execute mutation and fail on partially initialized `pkg.a`.

## 5. EXACT AST AUDIT
CODE_PATH_PROVED: `_project_typing_opaque_effects` was added verbatim after the known detector. It accepts the specified closed statement shapes with depth limit 32 and rejects all other statements.

## 6. EXACT IMPORT-DOMAIN CHECK
CODE_PATH_PROVED: `_project_typing_imports_closed` checks every indexed ImportRef. Only static indexed absolute imports and the exact typing exceptions pass; relative/local and other external imports fail.

## 7. KNOWN DETECTOR PRESERVATION
CODE_PATH_PROVED: `_possible_project_typing_marker_mutation` was not edited. Both R1 counterexamples assert its False result.

## 8. WORKER-SOURCE PROVENANCE
CODE_PATH_PROVED: New fact comes from existing `parsed_input.tree` for the original worker SourceSnapshot. No new source read or parse was introduced.

## 9. CACHE VERSION 4 -> 5
DIRECT_EVIDENCE: Import classification semantic version is 5; stale versions absent, 0, 1, 2, 3, 4 are rejected by focused tests.

## 10. WORKER CACHE FIELDS
CODE_PATH_PROVED: Exact bool `typing_guard_opaque_effects` joins the existing two private facts in cache validation, cold writes, and partial rewrites.

## 11. ALL WORKER RETURN PATHS
CODE_PATH_PROVED: Both successes return the fact; source-read and parse failures return True.

## 12. INLINE RESULT COLLECTION
CODE_PATH_PROVED: Inline successful merge records the new bool and source fingerprint after existing marker recording.

## 13. PROCESS-POOL COLLECTION
CODE_PATH_PROVED: Real process-pool successful merge calls the same recorder in the same position.

## 14. GLOBAL FINALIZER
CODE_PATH_PROVED: `project_effects_closed` requires no skipped files, complete exact-bool False facts, matching source fingerprints, and closed import domain; existing shadow, parent, and known-mutation predicates remain.

## 15. __ior__ COUNTEREXAMPLE
DIRECT_EVIDENCE: Existing detector False; opaque True; final guarded import hard; `pkg.a`/`pkg.c` real SCC; isolated launcher fails.

## 16. ALIASED UPDATE COUNTEREXAMPLE
DIRECT_EVIDENCE: Existing detector False; opaque True; final guarded import hard; `pkg.a`/`pkg.c` real SCC; isolated launcher fails.

## 17. CPYTHON DIFFERENTIALS
DIRECT_EVIDENCE: For both R1 launchers, isolated `pkg.a` and `pkg.c` succeed while `pkg.launcher` fails with partially initialized `pkg.a`. No active-repository code execution.

## 18. UNKNOWN EFFECT MATRIX
DIRECT_EVIDENCE: E01-E12 are tested in an unrelated indexed file; opaque fact True, candidate cleared, hard edge retained. E12 also proves import-domain closure False.

## 19. EXTERNAL IMPORT NEGATIVES
DIRECT_EVIDENCE: I01-I06 return closed-domain False and clear an unrelated candidate; no external allowlist added.

## 20. SAFE LANGUAGE POSITIVES
DIRECT_EVIDENCE: Existing safe NAME, ATTRIBUTE, D2B3 typed-side variants, mixed active, ELSE, R1 literal prefix, and R2 parent initializer fixtures pass. Eligible candidate imports retain type_only and soft edges. ELSE fixture has no guarded candidate and retains its existing hard ELSE edge. Worker opaque facts False and import domain True are asserted.

## 21. HARD/SOFT GRAPH COMPARISON
DIRECT_EVIDENCE: Unsafe R1 launchers have hard `pkg.a -> pkg.c`, hard `pkg.c -> pkg.a`, no `pkg.a -> pkg.c` soft edge. Safe D2B3 fixture keeps its soft typed-side edge and active hard SCC.

## 22. SCC TOPOLOGY
DIRECT_EVIDENCE: Both R1 launchers preserve genuine `{pkg.a,pkg.c}` hard SCC; safe fixture topology remains in focused regressions.

## 23. STALE CACHE REPLAY
DIRECT_EVIDENCE: Forged version-4 `opaque=False` is invalidated and rewritten to version 5 `opaque=True` without dissolving SCC.

## 24. MALFORMED CACHE REPLAY
DIRECT_EVIDENCE: Missing, None, string `false`, and integer 0 version-5 facts are rejected; exact bool True is rewritten, fingerprint stable, one source read.

## 25. COLD/WARM PARITY
DIRECT_EVIDENCE: Safe NAME, safe D2B3 typed-side, `__ior__`, and aliased-update cold/warm parity tests pass; warm parse is explicitly blocked in tests.

## 26. INLINE/PROCESS-POOL PARITY
DIRECT_EVIDENCE: Six real isolated inline/pool fixture pairs pass ordered ImportRefs, both worker facts, hard/soft graph, and SCC topology comparisons.

## 27. SOURCE-CHECKER FAIL-CLOSED
DIRECT_EVIDENCE: R1 opaque launcher retains hard SCC; independent checker returns `INDETERMINATE/GRAPH_SOURCE_IMPORT_MISMATCH`; launcher is absent from hard source closure; no positive manifest.

## 28. ORIGINAL-WORKER REINDEX
CONTRACT_PROVED: Focused original-worker reindex/preparation tests pass; worker capture and original source snapshot paths remain unchanged.

## 29. P0/P1B
CONTRACT_PROVED: Existing positive D2B3 source evidence and P0/P1B focused regressions pass; no new P0/P1B code or positive opaque-launcher claim.

## 30. MANIFEST V2
CONTRACT_PROVED: Existing manifest v2 tests pass; R1 opaque-launcher preparation yields no positive manifest.

## 31. OFFICIAL ISOLATED FULL
DIRECT_EVIDENCE: Existing D2B3 official isolated FULL regression passes in the focused suite. No active-repository FULL.

## 32. RECEIPT V2
CONTRACT_PROVED: Existing isolated receipt v2 regression passes; no receipt schema changed.

## 33. FOCUSED PYTEST RESULTS
DIRECT_EVIDENCE: Specified eight-module focused suite: 464 passed in 92.01s; exit 0, stopwatch 94.00s. No global suite run.

## 34. EXACT COMMANDS/EXIT CODES
DIRECT_EVIDENCE: `.\.venv\Scripts\python.exe -m py_compile contextor/core/symbol_engine/indexer.py`: exit 0, 0.29s. `.\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_d2b2_type_only.py tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py`: exit 0, stopwatch 94.00s. `git diff --check --` for three changed source/test paths: exit 0.

## 35. FILES_CHANGED
DIRECT_EVIDENCE: `contextor/core/symbol_engine/indexer.py`; `tests/test_p1d3_d2b2_type_only.py`; `tests/test_p1d3_package_cycle_integration.py`. `walkthrough.md` is the report and excluded from this production/test list.

## 36. FULL ACTUAL_DIFF
Complete unabridged `git diff --no-color` for every FILES_CHANGED path:

```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 03d1ea1..e6df35a 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -73,7 +73,7 @@ SYMBOL_FACTS_SCHEMA_VERSION = 2
 REFERENCE_FACTS_SCHEMA_VERSION = 1
 COLLISION_FACTS_SCHEMA_VERSION = 1
 TEST_FACTS_SCHEMA_VERSION = 1
-IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 4
+IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 5
 _SYMBOL_FACTS_AVAILABLE = "available"
 _SYMBOL_FACTS_FAILURE = "failure"
 _SYMBOL_FACTS_NOT_COMPUTED = "not_computed"
@@ -375,6 +375,215 @@ def _possible_project_typing_marker_mutation(
     return False
 
 
+def _project_typing_opaque_effects(
+    tree: ast.AST,
+) -> bool:
+    if not isinstance(tree, ast.Module):
+        return True
+
+    guard = recognize_typing_guard(
+        tree,
+        frozenset(),
+    )
+
+    def safe_statements(
+        statements: list[ast.stmt],
+        *,
+        top_level: bool,
+        depth: int,
+    ) -> bool:
+        if depth > 32:
+            return False
+
+        for position, statement in enumerate(
+            statements
+        ):
+            if isinstance(statement, ast.Pass):
+                continue
+
+            if (
+                top_level
+                and position == 0
+                and isinstance(
+                    statement,
+                    ast.Expr,
+                )
+                and isinstance(
+                    statement.value,
+                    ast.Constant,
+                )
+                and type(
+                    statement.value.value
+                ) is str
+            ):
+                continue
+
+            if isinstance(statement, ast.Assign):
+                if (
+                    _safe_typing_guard_prefix_statement(
+                        statement
+                    )
+                ):
+                    continue
+
+                return False
+
+            if isinstance(statement, ast.Import):
+                if (
+                    statement.names
+                    and all(
+                        alias.name
+                        and all(
+                            part.isidentifier()
+                            for part
+                            in alias.name.split(".")
+                        )
+                        for alias
+                        in statement.names
+                    )
+                ):
+                    continue
+
+                return False
+
+            if isinstance(statement, ast.ImportFrom):
+                if (
+                    statement.names
+                    and type(statement.level) is int
+                    and statement.level >= 0
+                    and (
+                        statement.module is None
+                        or (
+                            statement.module
+                            and all(
+                                part.isidentifier()
+                                for part
+                                in statement.module.split(".")
+                            )
+                        )
+                    )
+                    and all(
+                        alias.name != "*"
+                        and alias.name.isidentifier()
+                        for alias in statement.names
+                    )
+                ):
+                    continue
+
+                return False
+
+            if isinstance(statement, ast.If):
+                literal_condition = (
+                    isinstance(
+                        statement.test,
+                        ast.Constant,
+                    )
+                    and type(
+                        statement.test.value
+                    ) is bool
+                )
+
+                typing_condition = (
+                    top_level
+                    and guard is not None
+                    and matches_typing_guard(
+                        statement.test,
+                        guard.form,
+                    )
+                )
+
+                if not (
+                    literal_condition
+                    or typing_condition
+                ):
+                    return False
+
+                if not safe_statements(
+                    statement.body,
+                    top_level=False,
+                    depth=depth + 1,
+                ):
+                    return False
+
+                if not safe_statements(
+                    statement.orelse,
+                    top_level=False,
+                    depth=depth + 1,
+                ):
+                    return False
+
+                continue
+
+            return False
+
+        return True
+
+    return not safe_statements(
+        tree.body,
+        top_level=True,
+        depth=0,
+    )
+
+
+def _project_typing_imports_closed(
+    modules: dict[str, Module],
+) -> bool:
+    indexed = frozenset(modules)
+
+    for module in modules.values():
+        for import_ref in module.imports:
+            if (
+                import_ref.is_local
+                or import_ref.level != 0
+            ):
+                return False
+
+            if import_ref.is_from_import:
+                if import_ref.module == "typing":
+                    if (
+                        import_ref.names
+                        != ["TYPE_CHECKING"]
+                    ):
+                        return False
+
+                    continue
+
+                if (
+                    not import_ref.names
+                    or "*" in import_ref.names
+                ):
+                    return False
+
+                target_name = import_ref.module
+
+            else:
+                target_name = import_ref.module
+
+                if target_name == "typing":
+                    continue
+
+            if (
+                type(target_name) is not str
+                or not target_name
+                or not all(
+                    part.isidentifier()
+                    for part
+                    in target_name.split(".")
+                )
+            ):
+                return False
+
+            if (
+                target_name not in indexed
+                and (
+                    target_name + ".__init__"
+                ) not in indexed
+            ):
+                return False
+
+    return True
+
+
 def read_imports(
     file_path: Path,
     *,
@@ -630,6 +839,7 @@ def _process_single_file(
             "error": str(exc),
             "typing_guard_initializer_passive": False,
             "typing_guard_marker_mutation": True,
+            "typing_guard_opaque_effects": True,
             "filename": path.name,
             "symbol_facts": None,
             "reference_facts": None,
@@ -696,6 +906,11 @@ def _process_single_file(
                     "typing_guard_marker_mutation"
                 )
             ) is not bool
+            or type(
+                cached_data.get(
+                    "typing_guard_opaque_effects"
+                )
+            ) is not bool
         )
     ):
         cached_data = None
@@ -710,6 +925,13 @@ def _process_single_file(
         if cached_data is not None
         else True
     )
+    typing_guard_opaque_effects = (
+        cached_data[
+            "typing_guard_opaque_effects"
+        ]
+        if cached_data is not None
+        else True
+    )
 
     lineage_facts = None
     lineage_cache_hit = False
@@ -771,6 +993,9 @@ def _process_single_file(
                 "typing_guard_marker_mutation": (
                     typing_guard_marker_mutation
                 ),
+                "typing_guard_opaque_effects": (
+                    typing_guard_opaque_effects
+                ),
                 "filename": path.name,
                 "symbol_facts": symbol_facts,
                 "reference_facts": reference_facts,
@@ -813,6 +1038,7 @@ def _process_single_file(
             "error": str(exc), "filename": path.name,
             "typing_guard_initializer_passive": False,
             "typing_guard_marker_mutation": True,
+            "typing_guard_opaque_effects": True,
             "symbol_facts": None, "reference_facts": None,
             "collision_facts": None, "collision_facts_status": None,
             "test_facts": None, "test_facts_status": None,
@@ -850,6 +1076,12 @@ def _process_single_file(
                 tree
             )
         )
+    if cached_data is None:
+        typing_guard_opaque_effects = (
+            _project_typing_opaque_effects(
+                tree
+            )
+        )
     lineage_extract_ms = 0.0
     lineage_extract_called = False
     if lineage_facts is None:
@@ -976,6 +1208,9 @@ def _process_single_file(
                 rewritten[
                     "typing_guard_marker_mutation"
                 ] = typing_guard_marker_mutation
+                rewritten[
+                    "typing_guard_opaque_effects"
+                ] = typing_guard_opaque_effects
                 rewritten["lineage_facts"] = serialize_extracted_lineage_source_facts(
                     lineage_facts
                 )
@@ -1115,6 +1350,9 @@ def _process_single_file(
             "typing_guard_marker_mutation": (
                 typing_guard_marker_mutation
             ),
+            "typing_guard_opaque_effects": (
+                typing_guard_opaque_effects
+            ),
         }
         if symbol_facts and symbol_facts.get("status") == _SYMBOL_FACTS_AVAILABLE:
             cache_data["symbol_facts"] = symbol_facts
@@ -1153,6 +1391,9 @@ def _process_single_file(
         "typing_guard_marker_mutation": (
             typing_guard_marker_mutation
         ),
+        "typing_guard_opaque_effects": (
+            typing_guard_opaque_effects
+        ),
         "filename": path.name,
         "symbol_facts": symbol_facts,
         "reference_facts": reference_facts,
@@ -1381,6 +1622,10 @@ def index_repository(
         str,
         tuple[bool, str],
     ] = {}
+    opaque_effects_by_module: dict[
+        str,
+        tuple[bool, str],
+    ] = {}
     file_tasks = 0
     source_parse_calls = 0
     source_parse_failures = 0
@@ -1563,6 +1808,37 @@ def index_repository(
                 fingerprint,
             )
 
+    def record_opaque_effects(
+        result: dict,
+    ) -> None:
+        module_id = result.get("module_id")
+
+        if (
+            type(module_id) is not str
+            or not module_id
+            or result.get("error") is not None
+        ):
+            return
+
+        opaque = result.get(
+            "typing_guard_opaque_effects"
+        )
+
+        fingerprint = result.get(
+            "source_fingerprint"
+        )
+
+        if (
+            type(opaque) is bool
+            and type(fingerprint) is str
+        ):
+            opaque_effects_by_module[
+                module_id
+            ] = (
+                opaque,
+                fingerprint,
+            )
+
     def record_file_task_evidence(
         result: dict,
         *,
@@ -2225,6 +2501,36 @@ def index_repository(
                 for module_id in modules
             )
         )
+        project_effects_closed = (
+            not skipped
+            and len(opaque_effects_by_module)
+            == len(modules)
+            and all(
+                (
+                    module_id
+                    in opaque_effects_by_module
+                    and type(
+                        opaque_effects_by_module[
+                            module_id
+                        ][0]
+                    ) is bool
+                    and opaque_effects_by_module[
+                        module_id
+                    ][0] is False
+                    and opaque_effects_by_module[
+                        module_id
+                    ][1] == (
+                        source_fingerprints_by_module.get(
+                            module_id
+                        )
+                    )
+                )
+                for module_id in modules
+            )
+            and _project_typing_imports_closed(
+                modules
+            )
+        )
 
         for module_id, module in modules.items():
             if not any(
@@ -2265,6 +2571,7 @@ def index_repository(
                 not typing_shadowed
                 and parents_proved
                 and project_marker_safe
+                and project_effects_closed
             ):
                 continue
 
@@ -2313,6 +2620,7 @@ def index_repository(
                 record_indexed_source_fingerprint(res)
                 record_initializer_passivity(res)
                 record_marker_mutation(res)
+                record_opaque_effects(res)
                 if res.get("symbol_facts") is not None:
                     symbol_facts_by_module[res["module_id"]] = res["symbol_facts"]
                 if res.get("reference_facts") is not None:
@@ -2471,6 +2779,7 @@ def index_repository(
                 record_indexed_source_fingerprint(res)
                 record_initializer_passivity(res)
                 record_marker_mutation(res)
+                record_opaque_effects(res)
 
                 if res.get("symbol_facts") is not None:
                     symbol_facts_by_module[
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index f2759e4..72f476e 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -47,6 +47,33 @@ D2B4_INDEXED_LAUNCHER = {
     ),
 }
 
+D2B4_R1_BASE = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.c\n"
+        "value = 1\n"
+    ),
+    "pkg/c.py": "from pkg.a import value\n",
+}
+
+D2B4_R1_LAUNCHERS = [
+    (
+        "ior",
+        "import typing\n"
+        'typing.__dict__.__ior__({"TYPE_CHECKING": True})\n'
+        "import pkg.a\n",
+    ),
+    (
+        "alias-update",
+        "import typing\n"
+        "mutation = typing.__dict__.update\n"
+        'mutation({"TYPE_CHECKING": True})\n'
+        "import pkg.a\n",
+    ),
+]
+
 D2B2_R1_GLOBALS_MUTATION = {
     "pkg/__init__.py": "pass\n",
     "pkg/a.py": (
@@ -546,7 +573,7 @@ def test_p1d3_d2b4_forged_stale_launcher_cache(
     _index_graph(root)
     source = root / "pkg" / "launcher.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 4
+    assert cached["import_classification_semantics_version"] == 5
     assert cached["typing_guard_marker_mutation"] is True
     cached["import_classification_semantics_version"] = 3
     cached["typing_guard_marker_mutation"] = False
@@ -555,7 +582,7 @@ def test_p1d3_d2b4_forged_stale_launcher_cache(
     index, graph = _index_graph(root)
     _assert_d2b4_launcher_graph(index, graph)
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 4
+    assert rewritten["import_classification_semantics_version"] == 5
     assert rewritten["typing_guard_marker_mutation"] is True
 
 
@@ -653,6 +680,180 @@ def test_p1d3_d2b4_inline_process_pool_parity(
     )
 
 
+@pytest.mark.parametrize("case,launcher", D2B4_R1_LAUNCHERS)
+def test_p1d3_d2b4_r1_opaque_launcher_counterexamples(
+    tmp_path, isolated_dirs, case, launcher,
+):
+    fixture = {**D2B4_R1_BASE, "pkg/launcher.py": launcher}
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    tree = ast.parse(launcher)
+    assert indexer._possible_project_typing_marker_mutation(tree) is False
+    assert indexer._project_typing_opaque_effects(tree) is True
+    worker = indexer._process_single_file(str(root / "pkg" / "launcher.py"), str(root))
+    assert worker["typing_guard_marker_mutation"] is False
+    assert worker["typing_guard_opaque_effects"] is True
+    index, graph = _index_graph(root)
+    _assert_d2b4_launcher_graph(index, graph)
+    for module in ("pkg.a", "pkg.c"):
+        assert run_synthetic_import(root, module).returncode == 0
+    failed = run_synthetic_import(root, "pkg.launcher")
+    assert failed.returncode != 0
+    assert "partially initialized module 'pkg.a'" in failed.stderr
+
+
+D2B4_R1_UNKNOWN_EFFECTS = [
+    ("E01", "arbitrary()\n", True),
+    ("E02", "callback = arbitrary.callback\n", True),
+    ("E03", "def f(): pass\n", True),
+    ("E04", "class C: pass\n", True),
+    ("E05", 'import typing\ntarget = typing.__dict__\ntarget["TYPE_CHECKING"] = True\n', True),
+    ("E06", 'import typing\ngetattr(typing, "__dict__").update({"TYPE_CHECKING": True})\n', True),
+    ("E07", "if condition:\n    pass\n", True),
+    ("E08", "try:\n    pass\nexcept Exception:\n    pass\n", True),
+    ("E09", "x: int = 1\n", True),
+    ("E10", "x = 1\nx += 1\n", True),
+    ("E11", "with manager:\n    pass\n", True),
+    ("E12", 'import importlib\nimportlib.import_module("typing")\n', True),
+]
+
+
+@pytest.mark.parametrize("case,source,opaque", D2B4_R1_UNKNOWN_EFFECTS)
+def test_p1d3_d2b4_r1_unknown_effects_veto(
+    tmp_path, isolated_dirs, case, source, opaque,
+):
+    fixture = {**D2B_NAME_SAFE, "unrelated.py": source}
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    worker = indexer._process_single_file(str(root / "unrelated.py"), str(root))
+    assert worker["typing_guard_opaque_effects"] is opaque
+    index, graph = _index_graph(root)
+    if case == "E12":
+        assert indexer._project_typing_imports_closed(index.modules) is False
+    assert next(
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    ).type_only is False
+    assert "pkg.b" in graph.hard_edges["pkg.a"]
+    assert "pkg.a" in graph.hard_edges["pkg.b"]
+    assert "pkg.b" not in graph.soft_edges["pkg.a"]
+
+
+D2B4_R1_EXTERNAL_IMPORTS = [
+    ("I01", "import sys\n"),
+    ("I02", "import os\n"),
+    ("I03", "import unknown_external\n"),
+    ("I04", "from typing import Any\n"),
+    ("I05", "from external_module import value\n"),
+    ("I06", "from . import sibling\n"),
+]
+
+
+@pytest.mark.parametrize("case,source", D2B4_R1_EXTERNAL_IMPORTS)
+def test_p1d3_d2b4_r1_external_import_veto(
+    tmp_path, isolated_dirs, case, source,
+):
+    fixture = {**D2B_NAME_SAFE, "pkg/unrelated.py": source}
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    index, graph = _index_graph(root)
+    assert indexer._project_typing_imports_closed(index.modules) is False
+    assert next(
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    ).type_only is False
+    assert "pkg.b" in graph.hard_edges["pkg.a"]
+
+
+def test_p1d3_d2b4_r1_forged_stale_opaque_cache(
+    tmp_path, isolated_dirs,
+):
+    fixture = {**D2B4_R1_BASE, "pkg/launcher.py": D2B4_R1_LAUNCHERS[0][1]}
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    _index_graph(root)
+    source = root / "pkg" / "launcher.py"
+    cached = _cache_data(root, source)
+    assert cached["import_classification_semantics_version"] == 5
+    assert cached["typing_guard_marker_mutation"] is False
+    assert cached["typing_guard_opaque_effects"] is True
+    cached["import_classification_semantics_version"] = 4
+    cached["typing_guard_opaque_effects"] = False
+    CacheManager(str(root)).set(source, cached)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    index, graph = _index_graph(root)
+    _assert_d2b4_launcher_graph(index, graph)
+    rewritten = _cache_data(root, source)
+    assert rewritten["import_classification_semantics_version"] == 5
+    assert rewritten["typing_guard_opaque_effects"] is True
+
+
+@pytest.mark.parametrize(
+    "case,value",
+    [("missing", None), ("none", None), ("string", "false"), ("integer", 0)],
+)
+def test_p1d3_d2b4_r1_malformed_current_opaque_cache(
+    tmp_path, isolated_dirs, monkeypatch, case, value,
+):
+    fixture = {**D2B4_R1_BASE, "pkg/launcher.py": D2B4_R1_LAUNCHERS[0][1]}
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    original, _ = _index_graph(root)
+    source = root / "pkg" / "launcher.py"
+    cached = _cache_data(root, source)
+    if case == "missing":
+        cached.pop("typing_guard_opaque_effects")
+    else:
+        cached["typing_guard_opaque_effects"] = value
+    CacheManager(str(root)).set(source, cached)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    real_read = indexer.read_source_snapshot
+    reads = []
+
+    def tracked_read(path):
+        reads.append(Path(path).resolve())
+        return real_read(path)
+
+    monkeypatch.setattr(indexer, "read_source_snapshot", tracked_read)
+    replayed, graph = _index_graph(root)
+    _assert_d2b4_launcher_graph(replayed, graph)
+    assert replayed.source_fingerprints_by_module["pkg.launcher"] == (
+        original.source_fingerprints_by_module["pkg.launcher"]
+    )
+    assert reads.count(source.resolve()) == 1
+    assert _cache_data(root, source)["typing_guard_opaque_effects"] is True
+
+
+@pytest.mark.parametrize(
+    "fixture",
+    [
+        D2B_NAME_SAFE,
+        {**D2B4_R1_BASE, "pkg/launcher.py": D2B4_R1_LAUNCHERS[0][1]},
+        {**D2B4_R1_BASE, "pkg/launcher.py": D2B4_R1_LAUNCHERS[1][1]},
+    ],
+    ids=["safe-name", "ior", "alias-update"],
+)
+def test_p1d3_d2b4_r1_cold_warm_parity(
+    tmp_path, isolated_dirs, monkeypatch, fixture,
+):
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    cold_index, cold_graph = _index_graph(root)
+    cold_imports = _import_signature(cold_index)
+    cold_graph_signature = _graph_signature(cold_index, cold_graph)
+    cold_flags = {
+        relative: _cache_data(root, root / relative)["typing_guard_opaque_effects"]
+        for relative in fixture
+    }
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    def unexpected_parse(*args, **kwargs):
+        raise AssertionError("valid warm cache must not parse")
+
+    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
+    warm_index, warm_graph = _index_graph(root)
+    assert _import_signature(warm_index) == cold_imports
+    assert _graph_signature(warm_index, warm_graph) == cold_graph_signature
+    assert {
+        relative: _cache_data(root, root / relative)["typing_guard_opaque_effects"]
+        for relative in fixture
+    } == cold_flags
+
+
 def test_cold_and_warm_worker_cache_match_type_only_graph(
     tmp_path, isolated_dirs, monkeypatch,
 ):
@@ -662,7 +863,7 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
     cold_graph_signature = _graph_signature(cold_index, cold_graph)
     source = root / "pkg" / "a.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 4
+    assert cached["import_classification_semantics_version"] == 5
     assert next(
         item for item in cached["imports"] if item["module"] == "pkg.b"
     )["type_only"] is True
@@ -680,8 +881,8 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
 
 
 @pytest.mark.parametrize(
-    "stored_version", [None, 0, 1, 2, 3],
-    ids=["absent", "version-0", "version-1", "version-2", "version-3"],
+    "stored_version", [None, 0, 1, 2, 3, 4],
+    ids=["absent", "version-0", "version-1", "version-2", "version-3", "version-4"],
 )
 def test_stale_import_classification_cache_reparses_same_snapshot(
     tmp_path, isolated_dirs, stored_version, monkeypatch,
@@ -725,7 +926,7 @@ def test_stale_import_classification_cache_reparses_same_snapshot(
         for item in result.modules["pkg.a"].imports
     )
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 4
+    assert rewritten["import_classification_semantics_version"] == 5
     assert next(
         item for item in rewritten["imports"] if item["module"] == "pkg.b"
     )["type_only"] is True
@@ -991,6 +1192,13 @@ def test_d2b2_r1_safe_prefix_remains_type_only(tmp_path, isolated_dirs):
     }
     root = write_synthetic_repository(tmp_path / "repo", fixture)
     indexed, graph = _index_graph(root)
+    assert indexer._project_typing_imports_closed(indexed.modules) is True
+    assert all(
+        indexer._process_single_file(
+            str(module.absolute_path), str(root),
+        )["typing_guard_opaque_effects"] is False
+        for module in indexed.modules.values()
+    )
     guarded_imports = [
         item for item in indexed.modules["pkg.a"].imports
         if item.module == "pkg.b" and not item.is_from_import
@@ -1022,7 +1230,7 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
 
     source = root / "pkg" / "a.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 4
+    assert cached["import_classification_semantics_version"] == 5
     forged_imports = [
         item for item in cached["imports"] if item["module"] == "pkg.b"
     ]
@@ -1044,7 +1252,7 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
         for members in _scc_signature(replayed, graph)
     )
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 4
+    assert rewritten["import_classification_semantics_version"] == 5
     assert next(
         item for item in rewritten["imports"] if item["module"] == "pkg.b"
     )["type_only"] is False
@@ -1210,6 +1418,13 @@ def test_d2b2_r2_positive_parent_initializer_matrix(
     fixture = {**D2B_NAME_SAFE, "pkg/__init__.py": source}
     root = write_synthetic_repository(tmp_path / case, fixture)
     indexed, graph = _index_graph(root)
+    assert indexer._project_typing_imports_closed(indexed.modules) is True
+    assert all(
+        indexer._process_single_file(
+            str(module.absolute_path), str(root),
+        )["typing_guard_opaque_effects"] is False
+        for module in indexed.modules.values()
+    )
     guarded = [
         item for item in indexed.modules["pkg.a"].imports
         if item.module == "pkg.b" and not item.is_from_import
@@ -1249,7 +1464,7 @@ def test_d2b2_r2_worker_success_returns_and_warm_cache(
     ]
     assert warm["source_fingerprint"] == cold["source_fingerprint"]
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 4
+    assert cached["import_classification_semantics_version"] == 5
     assert type(cached["typing_guard_initializer_passive"]) is bool
     assert cached["typing_guard_initializer_passive"] is expected_passive
     assert cached["typing_guard_marker_mutation"] is cold[
@@ -1268,7 +1483,7 @@ def test_d2b2_r2_forged_stale_parent_cache_rejected(
     parent = root / "pkg" / "__init__.py"
     original_fingerprint = original.source_fingerprints_by_module["pkg.__init__"]
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 4
+    assert cached["import_classification_semantics_version"] == 5
     assert cached["typing_guard_initializer_passive"] is False
     cached["typing_guard_initializer_passive"] = True
     cached["import_classification_semantics_version"] = 2
@@ -1286,7 +1501,7 @@ def test_d2b2_r2_forged_stale_parent_cache_rejected(
     assert graph.hard_edges["pkg.a"] == {"pkg.b"}
     assert graph.hard_edges["pkg.b"] == {"pkg.a"}
     rewritten = _cache_data(root, parent)
-    assert rewritten["import_classification_semantics_version"] == 4
+    assert rewritten["import_classification_semantics_version"] == 5
     assert type(rewritten["typing_guard_initializer_passive"]) is bool
     assert rewritten["typing_guard_initializer_passive"] is False
 
@@ -1304,7 +1519,7 @@ def test_d2b2_r2_malformed_current_parent_cache_rejected(
     _index_graph(root)
     parent = root / "pkg" / "__init__.py"
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 4
+    assert cached["import_classification_semantics_version"] == 5
     if case == "missing":
         cached.pop("typing_guard_initializer_passive")
     else:
@@ -1342,7 +1557,7 @@ def test_d2b2_r2_malformed_current_parent_cache_rejected(
         for members in _scc_signature(replayed, graph)
     )
     rewritten = _cache_data(root, parent)
-    assert rewritten["import_classification_semantics_version"] == 4
+    assert rewritten["import_classification_semantics_version"] == 5
     assert type(rewritten["typing_guard_initializer_passive"]) is bool
     assert rewritten["typing_guard_initializer_passive"] is False
 
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index 0acc73f..c1d6daa 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -52,6 +52,7 @@ from contextor.core.reference.shared import (
 )
 from contextor.core.source import parse_source_snapshot, read_source_snapshot
 from contextor.core.symbol_engine.indexer import index_repository
+from contextor.core.symbol_engine import indexer
 from tests.cycle_semantics_lab import run_synthetic_import, write_synthetic_repository
 from tests.test_original_worker_full_receipt_optin import _persisted
 from tests.test_original_worker_official_full_live_publication import _official_live
@@ -243,6 +244,32 @@ D2B4_INDEXED_LAUNCHER = {
     ),
 }
 
+D2B4_R1_IOR_LAUNCHER = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.c\n"
+        "value = 1\n"
+    ),
+    "pkg/c.py": "from pkg.a import value\n",
+    "pkg/launcher.py": (
+        "import typing\n"
+        'typing.__dict__.__ior__({"TYPE_CHECKING": True})\n'
+        "import pkg.a\n"
+    ),
+}
+
+D2B4_R1_ALIAS_LAUNCHER = {
+    **D2B4_R1_IOR_LAUNCHER,
+    "pkg/launcher.py": (
+        "import typing\n"
+        "mutation = typing.__dict__.update\n"
+        'mutation({"TYPE_CHECKING": True})\n'
+        "import pkg.a\n"
+    ),
+}
+
 D2B3_SOURCE_BOUND_NEGATIVES = [
     (
         "N01-no-marker",
@@ -1201,6 +1228,162 @@ def test_p1d3_d2b4_launcher_source_checker_fails_closed(
     assert prepared.manifest is None
 
 
+def test_p1d3_d2b4_r1_opaque_source_checker_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B4_R1_IOR_LAUNCHER)
+    index, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
+    assert graph.hard_edges["pkg.a"] == {"pkg.c"}
+    assert graph.hard_edges["pkg.c"] == {"pkg.a"}
+    closure = compute_cycle_model_source_closures(graph.hard_edges)
+    assert len(closure) == 1
+    assert "pkg.launcher" not in closure[0].evidence_source_modules
+    consistency = assess_package_graph_consistency(
+        graph.hard_edges,
+        {module_id: source.tree for module_id, source in parsed.items()},
+        closure[0].evidence_source_modules,
+    )
+    assert consistency.status == "INDETERMINATE"
+    assert consistency.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+    assert evidence.scenarios.components[0].classification != (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    )
+    prepared = prepare_original_worker_cycle_manifest(
+        captured, graph.hard_edges, snapshot,
+    )
+    assert prepared.manifest is None
+
+
+@pytest.mark.parametrize(
+    "fixture,guarded_target,expected_type_only",
+    [
+        (D2B_NAME_SAFE, "pkg.b", True),
+        (D2B_ATTR_SAFE, "pkg.b", True),
+        (D2B3_TYPED_SIDE_NAME, "pkg.c", True),
+        (D2B3_TYPED_SIDE_ATTRIBUTE, "pkg.c", True),
+        (D2B2_MIXED_ACTIVE, "pkg.b", True),
+        (D2B_ELSE_SAFE, None, None),
+    ],
+    ids=["name", "attribute", "typed-side-name", "typed-side-attribute", "mixed", "else"],
+)
+def test_p1d3_d2b4_r1_safe_language_existing_fixtures(
+    tmp_path, isolated_dirs, fixture, guarded_target, expected_type_only,
+):
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    index, graph = _d2a_canonical_index_graph(root)
+    assert indexer._project_typing_imports_closed(index.modules) is True
+    assert not index.skipped
+    for module in index.modules.values():
+        worker = indexer._process_single_file(str(module.absolute_path), str(root))
+        assert worker["typing_guard_opaque_effects"] is False
+        assert worker["typing_guard_marker_mutation"] is False
+    if guarded_target is not None:
+        guarded = [
+            item for item in index.modules["pkg.a"].imports
+            if item.module == guarded_target and not item.is_from_import
+        ]
+        assert guarded[0].type_only is expected_type_only
+        assert guarded_target in graph.soft_edges["pkg.a"]
+    else:
+        assert graph.hard_edges["pkg.a"] == {"pkg.b"}
+
+
+@pytest.mark.parametrize(
+    "fixture",
+    [
+        D2B_NAME_SAFE,
+        D2B_ATTR_SAFE,
+        D2B3_TYPED_SIDE_NAME,
+        D2B4_R1_IOR_LAUNCHER,
+        D2B4_R1_ALIAS_LAUNCHER,
+        {
+            "pkg/__init__.py": "pass\n",
+            "pkg/sub/__init__.py": "pass\n",
+            "pkg/sub/a.py": (
+                "from typing import TYPE_CHECKING\n"
+                "if TYPE_CHECKING:\n"
+                "    import pkg.sub.b\n"
+                "value = 1\n"
+            ),
+            "pkg/sub/b.py": "from pkg.sub.a import value\n",
+        },
+    ],
+    ids=["name", "attribute", "typed-side", "ior", "alias-update", "multilevel"],
+)
+def test_p1d3_d2b4_r1_real_inline_pool_parity(
+    tmp_path, isolated_dirs, monkeypatch, fixture,
+):
+    def signature(root, index, graph):
+        imports = tuple(
+            (
+                module_id,
+                tuple(
+                    (item.module, item.level, tuple(item.names),
+                     item.is_from_import, item.is_local, item.type_only)
+                    for item in module.imports
+                ),
+            )
+            for module_id, module in sorted(index.modules.items())
+        )
+        facts = tuple(
+            (
+                module_id,
+                worker["typing_guard_marker_mutation"],
+                worker["typing_guard_opaque_effects"],
+            )
+            for module_id, module in sorted(index.modules.items())
+            for worker in [indexer._process_single_file(
+                str(module.absolute_path), str(root),
+            )]
+        )
+        topology = tuple(
+            component.members for component in analyze_cycle_scenarios(
+                graph.hard_edges,
+                {
+                    module_id: ast.parse(Path(module.absolute_path).read_text())
+                    for module_id, module in index.modules.items()
+                },
+            ).components
+        )
+        return imports, facts, graph.hard_edges, graph.soft_edges, topology
+
+    inline_root = write_synthetic_repository(tmp_path / "inline", fixture)
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    inline_index, inline_graph = _d2a_canonical_index_graph(inline_root)
+    inline_signature = signature(inline_root, inline_index, inline_graph)
+
+    pool_root = write_synthetic_repository(tmp_path / "pool", fixture)
+    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
+    pool_index, pool_graph = _d2a_canonical_index_graph(pool_root)
+    assert signature(pool_root, pool_index, pool_graph) == inline_signature
+
+
+def test_p1d3_d2b4_r1_typed_side_cold_warm_parity(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B3_TYPED_SIDE_NAME)
+    cold_index, cold_graph = _d2a_canonical_index_graph(root)
+    cold_imports = tuple(
+        (module_id, tuple((item.module, item.type_only) for item in module.imports))
+        for module_id, module in sorted(cold_index.modules.items())
+    )
+    cold_hard = cold_graph.hard_edges
+    cold_soft = cold_graph.soft_edges
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    def unexpected_parse(*args, **kwargs):
+        raise AssertionError("complete warm cache must not reparse")
+
+    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
+    warm_index, warm_graph = _d2a_canonical_index_graph(root)
+    assert tuple(
+        (module_id, tuple((item.module, item.type_only) for item in module.imports))
+        for module_id, module in sorted(warm_index.modules.items())
+    ) == cold_imports
+    assert warm_graph.hard_edges == cold_hard
+    assert warm_graph.soft_edges == cold_soft
+
+
 def test_p1d3_d2b3_attribute_typed_side_import(tmp_path, isolated_dirs):
     root = write_synthetic_repository(
         tmp_path / "repo", D2B3_TYPED_SIDE_ATTRIBUTE,
```

## 37. CONTRACT_CONFLICTS
DIRECT_EVIDENCE: None requiring production deviation. Existing ELSE-safe fixture contains no eligible guarded candidate; its hard ELSE edge remains as before.

## 38. DESIGN_GAPS
DIRECT_EVIDENCE: None encountered for the literal R1 patch.

## 39. UNKNOWN / UNSUPPORTED
UNKNOWN: Active LIVE loaded-code adoption, general Python runtime safety, arbitrary import hooks and pre-entry mutation were not established. Global suite not run.

## 40. FINAL IMPLEMENTER OBSERVATION
DIRECT_EVIDENCE: Literal R1 implementation and focused validation complete; architectural acceptance remains with ChatGPT. STOP after D2B-4-R1.

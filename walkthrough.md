# CONTEXTOR P1D3-D2B-4 — implementer report

## 1. IMPLEMENTER OBSERVATION
DIRECT_EVIDENCE: Literal project-wide typing marker mutation veto implemented within the three-file allowlist. This is an implementer observation, not architectural GO.

## 2. INITIAL/FINAL HEAD
DIRECT_EVIDENCE: Initial and final HEAD: `14b477e22c8534b21f1e0bb7c8f7ff7fcbfb2925`. No Git mutation.

## 3. WORKTREE STATUS
DIRECT_EVIDENCE: Initially clean. Final status: modified `contextor/core/symbol_engine/indexer.py`, `tests/test_p1d3_d2b2_type_only.py`, `tests/test_p1d3_package_cycle_integration.py`, plus this report.

## 4. ROOT CAUSE
CODE_PATH_PROVED: Prior local and parent checks did not inspect another indexed module that mutates `typing.TYPE_CHECKING` before importing a guarded module. The isolated launcher fixture reproduces this case.

## 5. EXACT MUTATION DETECTOR
CODE_PATH_PROVED: `_possible_project_typing_marker_mutation` uses the specified AST Store/Del attributes and subscripts, `exec`, literal `setattr`/`delattr`, and specified dictionary mutation calls. It returns True for non-Module trees.

## 6. WORKER SOURCE ORIGIN
CODE_PATH_PROVED: The fact is derived from the existing parsed original worker AST; no second parse or source read was introduced.

## 7. CACHE VERSION 3 -> 4
DIRECT_EVIDENCE: `IMPORT_CLASSIFICATION_SEMANTICS_VERSION=4`; stale versions absent, 0, 1, 2, and 3 are rejected by focused tests.

## 8. PRIVATE WORKER FACT
CODE_PATH_PROVED: Exact bool `typing_guard_marker_mutation` is in cache, success and failure worker results. Source/read failures return True. Malformed cache values invalidate cache.

## 9. INLINE COLLECTION
CODE_PATH_PROVED: Successful inline results call `record_marker_mutation` after initializer passivity recording.

## 10. PROCESS-POOL COLLECTION
CODE_PATH_PROVED: Successful real pool results use the same recorder; four real inline/pool fixture pairs pass parity tests.

## 11. GLOBAL FINALIZER VETO
CODE_PATH_PROVED: Retention requires no skipped files, exact matching facts for every module, False mutation values, matching source fingerprints, and prior shadow/parent predicates.

## 12. LAUNCHER COUNTEREXAMPLE
DIRECT_EVIDENCE: Local guarded candidate is True before finalization; final `pkg.a -> pkg.c` and `pkg.c -> pkg.a` are hard, with no corresponding soft edge and real SCC `{pkg.a,pkg.c}`.

## 13. CPYTHON DIFFERENTIAL
DIRECT_EVIDENCE: Fresh isolated `pkg.a` and `pkg.c` imports succeed; `pkg.launcher` fails with partially initialized `pkg.a`. Runnable mutation cases M01/M02/M03/M04/M07 reproduce the failure. M09 is an uncalled function and is asserted as a syntactic veto only.

## 14. MUTATION MATRIX
DIRECT_EVIDENCE: M01-M09 yield worker mutation=True, final type_only=False, hard guarded edge, and real SCC.

## 15. SAFE FIXTURES
CONTRACT_PROVED: Existing D2B safe name/attribute and D2B3 positive typed-side tests remain in the focused suite and pass. No global veto in the safe parity fixture.

## 16. COLD/WARM CACHE
DIRECT_EVIDENCE: Safe and unsafe cold/warm ordered imports, type flags, hard/soft graphs and SCC topology match. Warm cache parse is forbidden in the parity test and the test passes.

## 17. FORGED STALE CACHE
DIRECT_EVIDENCE: Forged version 3 false mutation fact is rejected and rewritten as version 4 true; hard SCC retained.

## 18. MALFORMED CURRENT CACHE
DIRECT_EVIDENCE: Missing, None, string `false`, and integer 0 facts are rejected; launcher source is read once and True is rewritten.

## 19. INLINE/PROCESS-POOL PARITY
DIRECT_EVIDENCE: Safe, unsafe launcher, nested safe, and nested unsafe launcher fixtures match on worker cached flags, ordered imports, graph, and SCC topology under real pool execution.

## 20. HARD/SOFT GRAPH
DIRECT_EVIDENCE: Unsafe launcher retains hard `pkg.a -> pkg.c` and `pkg.c -> pkg.a`; safe D2B3 typed-side fixture retains its existing soft typed edge and hard active SCC.

## 21. SCC TOPOLOGY
DIRECT_EVIDENCE: Unsafe launcher yields the real two-member SCC; safe type-only fixtures keep their existing topology.

## 22. SOURCE-CHECKER FAIL-CLOSED
DIRECT_EVIDENCE: Isolated launcher source checker returns `INDETERMINATE/GRAPH_SOURCE_IMPORT_MISMATCH`; source closure excludes unrelated `pkg.launcher`.

## 23. P0/P1B REGRESSIONS
CONTRACT_PROVED: Focused P0/P1B test files pass. No positive launcher P0/P1B claim was constructed.

## 24. ORIGINAL-WORKER REINDEX
CONTRACT_PROVED: Focused original-worker preparation tests pass; no worker capture contract was changed.

## 25. MANIFEST V2
DIRECT_EVIDENCE: Launcher preparation has no positive manifest. Existing v2 manifest regressions pass.

## 26. OFFICIAL ISOLATED FULL
DIRECT_EVIDENCE: Existing isolated D2B3 official FULL test passes in focused suite. No FULL on active repository.

## 27. RECEIPT V2
CONTRACT_PROVED: Existing isolated receipt v2 regression passes; no receipt schema changed.

## 28. FOCUSED PYTEST RESULTS
DIRECT_EVIDENCE: Final specified eight-file run: 421 passed in 75.69s; command exit 0, wall stopwatch 77.41s. Earlier D2B4 run: 23 passed; after added CPython differentials, final suite includes all tests.

## 29. EXACT COMMANDS/EXIT CODES
DIRECT_EVIDENCE: `.\.venv\Scripts\python.exe -m py_compile contextor/core/symbol_engine/indexer.py`: exit 0, 0.30s. `.\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_d2b2_type_only.py tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py`: exit 0, 77.41s. `git diff --check`: exit 0.

## 30. FILES_CHANGED
DIRECT_EVIDENCE: `contextor/core/symbol_engine/indexer.py`; `tests/test_p1d3_d2b2_type_only.py`; `tests/test_p1d3_package_cycle_integration.py`. `walkthrough.md` is the report, excluded from production/test diff list.

## 31. FULL ACTUAL_DIFF
The complete `git diff --no-color` for every file in FILES_CHANGED follows.

```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 3530d9d..03d1ea1 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -73,7 +73,7 @@ SYMBOL_FACTS_SCHEMA_VERSION = 2
 REFERENCE_FACTS_SCHEMA_VERSION = 1
 COLLISION_FACTS_SCHEMA_VERSION = 1
 TEST_FACTS_SCHEMA_VERSION = 1
-IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 3
+IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 4
 _SYMBOL_FACTS_AVAILABLE = "available"
 _SYMBOL_FACTS_FAILURE = "failure"
 _SYMBOL_FACTS_NOT_COMPUTED = "not_computed"
@@ -286,6 +286,95 @@ class AdvancedImportVisitor(ast.NodeVisitor):
         )
 
 
+def _possible_project_typing_marker_mutation(
+    tree: ast.AST,
+) -> bool:
+    if not isinstance(tree, ast.Module):
+        return True
+
+    for node in ast.walk(tree):
+        if (
+            isinstance(node, ast.Attribute)
+            and node.attr == "TYPE_CHECKING"
+            and isinstance(
+                node.ctx,
+                (ast.Store, ast.Del),
+            )
+        ):
+            return True
+
+        if (
+            isinstance(node, ast.Subscript)
+            and isinstance(
+                node.ctx,
+                (ast.Store, ast.Del),
+            )
+            and isinstance(
+                node.slice,
+                ast.Constant,
+            )
+            and type(node.slice.value) is str
+            and node.slice.value == "TYPE_CHECKING"
+        ):
+            return True
+
+        if not isinstance(node, ast.Call):
+            continue
+
+        if (
+            isinstance(node.func, ast.Name)
+            and node.func.id == "exec"
+        ):
+            return True
+
+        if (
+            isinstance(node.func, ast.Name)
+            and node.func.id
+            in {"setattr", "delattr"}
+            and len(node.args) >= 2
+            and isinstance(
+                node.args[1],
+                ast.Constant,
+            )
+            and type(node.args[1].value) is str
+            and node.args[1].value
+            == "TYPE_CHECKING"
+        ):
+            return True
+
+        if (
+            isinstance(node.func, ast.Attribute)
+            and node.func.attr
+            in {
+                "update",
+                "setdefault",
+                "__setitem__",
+            }
+        ):
+            receiver = node.func.value
+
+            if (
+                isinstance(receiver, ast.Call)
+                and isinstance(
+                    receiver.func,
+                    ast.Name,
+                )
+                and receiver.func.id
+                in {"globals", "vars"}
+                and not receiver.args
+                and not receiver.keywords
+            ):
+                return True
+
+            if (
+                isinstance(receiver, ast.Attribute)
+                and receiver.attr == "__dict__"
+            ):
+                return True
+
+    return False
+
+
 def read_imports(
     file_path: Path,
     *,
@@ -540,6 +629,7 @@ def _process_single_file(
             "imports": None,
             "error": str(exc),
             "typing_guard_initializer_passive": False,
+            "typing_guard_marker_mutation": True,
             "filename": path.name,
             "symbol_facts": None,
             "reference_facts": None,
@@ -601,6 +691,11 @@ def _process_single_file(
                     "typing_guard_initializer_passive"
                 )
             ) is not bool
+            or type(
+                cached_data.get(
+                    "typing_guard_marker_mutation"
+                )
+            ) is not bool
         )
     ):
         cached_data = None
@@ -610,6 +705,11 @@ def _process_single_file(
         if cached_data is not None
         else False
     )
+    typing_guard_marker_mutation = (
+        cached_data["typing_guard_marker_mutation"]
+        if cached_data is not None
+        else True
+    )
 
     lineage_facts = None
     lineage_cache_hit = False
@@ -668,6 +768,9 @@ def _process_single_file(
                 "typing_guard_initializer_passive": (
                     typing_guard_initializer_passive
                 ),
+                "typing_guard_marker_mutation": (
+                    typing_guard_marker_mutation
+                ),
                 "filename": path.name,
                 "symbol_facts": symbol_facts,
                 "reference_facts": reference_facts,
@@ -709,6 +812,7 @@ def _process_single_file(
             "absolute_path": str(path.resolve()), "imports": None,
             "error": str(exc), "filename": path.name,
             "typing_guard_initializer_passive": False,
+            "typing_guard_marker_mutation": True,
             "symbol_facts": None, "reference_facts": None,
             "collision_facts": None, "collision_facts_status": None,
             "test_facts": None, "test_facts_status": None,
@@ -740,6 +844,12 @@ def _process_single_file(
             module_id.endswith(".__init__")
             and _typing_guard_passive_initializer(tree)
         )
+    if cached_data is None:
+        typing_guard_marker_mutation = (
+            _possible_project_typing_marker_mutation(
+                tree
+            )
+        )
     lineage_extract_ms = 0.0
     lineage_extract_called = False
     if lineage_facts is None:
@@ -863,6 +973,9 @@ def _process_single_file(
                 rewritten[
                     "typing_guard_initializer_passive"
                 ] = typing_guard_initializer_passive
+                rewritten[
+                    "typing_guard_marker_mutation"
+                ] = typing_guard_marker_mutation
                 rewritten["lineage_facts"] = serialize_extracted_lineage_source_facts(
                     lineage_facts
                 )
@@ -999,6 +1112,9 @@ def _process_single_file(
             "typing_guard_initializer_passive": (
                 typing_guard_initializer_passive
             ),
+            "typing_guard_marker_mutation": (
+                typing_guard_marker_mutation
+            ),
         }
         if symbol_facts and symbol_facts.get("status") == _SYMBOL_FACTS_AVAILABLE:
             cache_data["symbol_facts"] = symbol_facts
@@ -1034,6 +1150,9 @@ def _process_single_file(
         "typing_guard_initializer_passive": (
             typing_guard_initializer_passive
         ),
+        "typing_guard_marker_mutation": (
+            typing_guard_marker_mutation
+        ),
         "filename": path.name,
         "symbol_facts": symbol_facts,
         "reference_facts": reference_facts,
@@ -1258,6 +1377,10 @@ def index_repository(
         str,
         tuple[bool, str],
     ] = {}
+    marker_mutation_by_module: dict[
+        str,
+        tuple[bool, str],
+    ] = {}
     file_tasks = 0
     source_parse_calls = 0
     source_parse_failures = 0
@@ -1410,6 +1533,36 @@ def index_repository(
                 fingerprint,
             )
 
+    def record_marker_mutation(
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
+        mutation = result.get(
+            "typing_guard_marker_mutation"
+        )
+        fingerprint = result.get(
+            "source_fingerprint"
+        )
+
+        if (
+            type(mutation) is bool
+            and type(fingerprint) is str
+        ):
+            marker_mutation_by_module[
+                module_id
+            ] = (
+                mutation,
+                fingerprint,
+            )
+
     def record_file_task_evidence(
         result: dict,
         *,
@@ -2045,6 +2198,33 @@ def index_repository(
             "typing" in modules
             or "typing.__init__" in modules
         )
+        project_marker_safe = (
+            not skipped
+            and len(marker_mutation_by_module)
+            == len(modules)
+            and all(
+                (
+                    module_id
+                    in marker_mutation_by_module
+                    and type(
+                        marker_mutation_by_module[
+                            module_id
+                        ][0]
+                    ) is bool
+                    and marker_mutation_by_module[
+                        module_id
+                    ][0] is False
+                    and marker_mutation_by_module[
+                        module_id
+                    ][1] == (
+                        source_fingerprints_by_module.get(
+                            module_id
+                        )
+                    )
+                )
+                for module_id in modules
+            )
+        )
 
         for module_id, module in modules.items():
             if not any(
@@ -2084,6 +2264,7 @@ def index_repository(
             if (
                 not typing_shadowed
                 and parents_proved
+                and project_marker_safe
             ):
                 continue
 
@@ -2131,6 +2312,7 @@ def index_repository(
                 )
                 record_indexed_source_fingerprint(res)
                 record_initializer_passivity(res)
+                record_marker_mutation(res)
                 if res.get("symbol_facts") is not None:
                     symbol_facts_by_module[res["module_id"]] = res["symbol_facts"]
                 if res.get("reference_facts") is not None:
@@ -2288,6 +2470,7 @@ def index_repository(
                 )
                 record_indexed_source_fingerprint(res)
                 record_initializer_passivity(res)
+                record_marker_mutation(res)
 
                 if res.get("symbol_facts") is not None:
                     symbol_facts_by_module[
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 9e00afe..f2759e4 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -31,6 +31,22 @@ D2B_NAME_SAFE = {
     "pkg/b.py": "from pkg.a import value\n",
 }
 
+D2B4_INDEXED_LAUNCHER = {
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
+        "typing.TYPE_CHECKING = True\n"
+        "import pkg.a\n"
+    ),
+}
+
 D2B2_R1_GLOBALS_MUTATION = {
     "pkg/__init__.py": "pass\n",
     "pkg/a.py": (
@@ -412,6 +428,231 @@ def _cache_data(root: Path, source: Path) -> dict:
     )["data"]
 
 
+D2B4_MUTATIONS = [
+    ("M01", "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n"),
+    ("M02", 'import typing\nsetattr(typing, "TYPE_CHECKING", True)\nimport pkg.a\n'),
+    ("M03", 'import typing\ntyping.__dict__["TYPE_CHECKING"] = True\nimport pkg.a\n'),
+    ("M04", 'exec("import typing; typing.TYPE_CHECKING = True")\nimport pkg.a\n'),
+    ("M05", 'globals()["TYPE_CHECKING"] = True\nimport pkg.a\n'),
+    ("M06", 'vars()["TYPE_CHECKING"] = True\nimport pkg.a\n'),
+    ("M07", 'import typing\ntyping.__dict__.update({"TYPE_CHECKING": True})\nimport pkg.a\n'),
+    ("M08", 'globals().update({"TYPE_CHECKING": True})\nimport pkg.a\n'),
+    ("M09", 'def mutate():\n    import typing\n    typing.TYPE_CHECKING = True\nimport pkg.a\n'),
+]
+
+
+def _assert_d2b4_launcher_graph(index, graph):
+    guarded = next(
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.c"
+    )
+    assert guarded.type_only is False
+    assert "pkg.c" in graph.hard_edges["pkg.a"]
+    assert "pkg.a" in graph.hard_edges["pkg.c"]
+    assert "pkg.c" not in graph.soft_edges["pkg.a"]
+    assert any(
+        set(members) == {"pkg.a", "pkg.c"}
+        for members in _scc_signature(index, graph)
+    )
+
+
+def test_p1d3_d2b4_indexed_launcher_mutation_retains_scc(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B4_INDEXED_LAUNCHER)
+    index, graph = _index_graph(root)
+    source_local, error = indexer.read_imports(
+        root / "pkg" / "a.py",
+        tree=ast.parse(D2B4_INDEXED_LAUNCHER["pkg/a.py"]),
+    )
+    assert error is None
+    assert next(item for item in source_local if item.module == "pkg.c").type_only
+    _assert_d2b4_launcher_graph(index, graph)
+    assert _cache_data(root, root / "pkg" / "launcher.py")[
+        "typing_guard_marker_mutation"
+    ] is True
+    for module in ("pkg.a", "pkg.c"):
+        assert run_synthetic_import(root, module).returncode == 0
+    failed = run_synthetic_import(root, "pkg.launcher")
+    assert failed.returncode != 0
+    assert "partially initialized module 'pkg.a'" in failed.stderr
+
+
+@pytest.mark.parametrize("case,launcher", D2B4_MUTATIONS)
+def test_p1d3_d2b4_mutation_matrix(
+    tmp_path, isolated_dirs, case, launcher,
+):
+    fixture = {**D2B4_INDEXED_LAUNCHER, "pkg/launcher.py": launcher}
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    worker = indexer._process_single_file(str(root / "pkg" / "launcher.py"), str(root))
+    assert worker["typing_guard_marker_mutation"] is True
+    index, graph = _index_graph(root)
+    _assert_d2b4_launcher_graph(index, graph)
+
+
+@pytest.mark.parametrize(
+    "case,launcher",
+    [item for item in D2B4_MUTATIONS if item[0] in {"M01", "M02", "M03", "M04", "M07"}],
+)
+def test_p1d3_d2b4_executed_mutation_differential(
+    tmp_path, isolated_dirs, case, launcher,
+):
+    fixture = {**D2B4_INDEXED_LAUNCHER, "pkg/launcher.py": launcher}
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    failed = run_synthetic_import(root, "pkg.launcher")
+    assert failed.returncode != 0
+    assert "partially initialized module 'pkg.a'" in failed.stderr
+
+
+def test_p1d3_d2b4_unrelated_indexed_mutation_veto(
+    tmp_path, isolated_dirs,
+):
+    fixture = {
+        **D2B_NAME_SAFE,
+        "unrelated.py": "import typing\ntyping.TYPE_CHECKING = True\n",
+    }
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    index, graph = _index_graph(root)
+    assert next(
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    ).type_only is False
+    assert "pkg.b" in graph.hard_edges["pkg.a"]
+
+
+@pytest.mark.parametrize("fixture", [D2B_NAME_SAFE, D2B4_INDEXED_LAUNCHER])
+def test_p1d3_d2b4_cold_warm_parity(
+    tmp_path, isolated_dirs, monkeypatch, fixture,
+):
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    cold_index, cold_graph = _index_graph(root)
+    cold_imports = _import_signature(cold_index)
+    cold_graph_signature = _graph_signature(cold_index, cold_graph)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    def unexpected_parse(*args, **kwargs):
+        raise AssertionError("valid warm cache must not parse")
+
+    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
+    warm_index, warm_graph = _index_graph(root)
+    assert _import_signature(warm_index) == cold_imports
+    assert _graph_signature(warm_index, warm_graph) == cold_graph_signature
+
+
+def test_p1d3_d2b4_forged_stale_launcher_cache(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B4_INDEXED_LAUNCHER)
+    _index_graph(root)
+    source = root / "pkg" / "launcher.py"
+    cached = _cache_data(root, source)
+    assert cached["import_classification_semantics_version"] == 4
+    assert cached["typing_guard_marker_mutation"] is True
+    cached["import_classification_semantics_version"] = 3
+    cached["typing_guard_marker_mutation"] = False
+    CacheManager(str(root)).set(source, cached)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    index, graph = _index_graph(root)
+    _assert_d2b4_launcher_graph(index, graph)
+    rewritten = _cache_data(root, source)
+    assert rewritten["import_classification_semantics_version"] == 4
+    assert rewritten["typing_guard_marker_mutation"] is True
+
+
+@pytest.mark.parametrize(
+    "case,value",
+    [("missing", None), ("none", None), ("string", "false"), ("integer", 0)],
+)
+def test_p1d3_d2b4_malformed_current_launcher_cache(
+    tmp_path, isolated_dirs, monkeypatch, case, value,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B4_INDEXED_LAUNCHER)
+    _index_graph(root)
+    source = root / "pkg" / "launcher.py"
+    cached = _cache_data(root, source)
+    if case == "missing":
+        cached.pop("typing_guard_marker_mutation")
+    else:
+        cached["typing_guard_marker_mutation"] = value
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
+    index, graph = _index_graph(root)
+    _assert_d2b4_launcher_graph(index, graph)
+    assert reads.count(source.resolve()) == 1
+    assert _cache_data(root, source)["typing_guard_marker_mutation"] is True
+
+
+@pytest.mark.parametrize(
+    "fixture",
+    [
+        D2B_NAME_SAFE,
+        D2B4_INDEXED_LAUNCHER,
+        {
+            "pkg/__init__.py": "pass\n",
+            "pkg/sub/__init__.py": "pass\n",
+            "pkg/sub/a.py": (
+                "from typing import TYPE_CHECKING\n"
+                "if TYPE_CHECKING:\n"
+                "    import pkg.sub.c\n"
+                "value = 1\n"
+            ),
+            "pkg/sub/c.py": "from pkg.sub.a import value\n",
+        },
+        {
+            "pkg/__init__.py": "pass\n",
+            "pkg/sub/__init__.py": "pass\n",
+            "pkg/sub/a.py": (
+                "from typing import TYPE_CHECKING\n"
+                "if TYPE_CHECKING:\n"
+                "    import pkg.sub.c\n"
+                "value = 1\n"
+            ),
+            "pkg/sub/c.py": "from pkg.sub.a import value\n",
+            "pkg/sub/launcher.py": (
+                "import typing\n"
+                "typing.TYPE_CHECKING = True\n"
+                "import pkg.sub.a\n"
+            ),
+        },
+    ],
+    ids=["safe", "unsafe", "nested-safe", "nested-unsafe"],
+)
+def test_p1d3_d2b4_inline_process_pool_parity(
+    tmp_path, isolated_dirs, monkeypatch, fixture,
+):
+    inline_root = write_synthetic_repository(tmp_path / "inline", fixture)
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    inline_index, inline_graph = _index_graph(inline_root)
+    inline_flags = {
+        relative: _cache_data(inline_root, inline_root / relative)[
+            "typing_guard_marker_mutation"
+        ]
+        for relative in fixture
+    }
+    pool_root = write_synthetic_repository(tmp_path / "pool", fixture)
+    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
+    pool_index, pool_graph = _index_graph(pool_root)
+    pool_flags = {
+        relative: _cache_data(pool_root, pool_root / relative)[
+            "typing_guard_marker_mutation"
+        ]
+        for relative in fixture
+    }
+    assert pool_flags == inline_flags
+    assert _import_signature(pool_index) == _import_signature(inline_index)
+    assert _graph_signature(pool_index, pool_graph) == _graph_signature(
+        inline_index, inline_graph,
+    )
+
+
 def test_cold_and_warm_worker_cache_match_type_only_graph(
     tmp_path, isolated_dirs, monkeypatch,
 ):
@@ -421,7 +662,7 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
     cold_graph_signature = _graph_signature(cold_index, cold_graph)
     source = root / "pkg" / "a.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 3
+    assert cached["import_classification_semantics_version"] == 4
     assert next(
         item for item in cached["imports"] if item["module"] == "pkg.b"
     )["type_only"] is True
@@ -439,8 +680,8 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
 
 
 @pytest.mark.parametrize(
-    "stored_version", [None, 0, 1, 2],
-    ids=["absent", "version-0", "version-1", "version-2"],
+    "stored_version", [None, 0, 1, 2, 3],
+    ids=["absent", "version-0", "version-1", "version-2", "version-3"],
 )
 def test_stale_import_classification_cache_reparses_same_snapshot(
     tmp_path, isolated_dirs, stored_version, monkeypatch,
@@ -484,7 +725,7 @@ def test_stale_import_classification_cache_reparses_same_snapshot(
         for item in result.modules["pkg.a"].imports
     )
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 3
+    assert rewritten["import_classification_semantics_version"] == 4
     assert next(
         item for item in rewritten["imports"] if item["module"] == "pkg.b"
     )["type_only"] is True
@@ -781,7 +1022,7 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
 
     source = root / "pkg" / "a.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 3
+    assert cached["import_classification_semantics_version"] == 4
     forged_imports = [
         item for item in cached["imports"] if item["module"] == "pkg.b"
     ]
@@ -803,7 +1044,7 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
         for members in _scc_signature(replayed, graph)
     )
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 3
+    assert rewritten["import_classification_semantics_version"] == 4
     assert next(
         item for item in rewritten["imports"] if item["module"] == "pkg.b"
     )["type_only"] is False
@@ -995,6 +1236,7 @@ def test_d2b2_r2_worker_success_returns_and_warm_cache(
     assert cold["source_parse_called"] is True
     assert type(cold["typing_guard_initializer_passive"]) is bool
     assert cold["typing_guard_initializer_passive"] is expected_passive
+    assert type(cold["typing_guard_marker_mutation"]) is bool
     assert cold["source_fingerprint"]
     warm = indexer._process_single_file(str(parent), str(root))
     assert warm["error"] is None
@@ -1002,11 +1244,17 @@ def test_d2b2_r2_worker_success_returns_and_warm_cache(
     assert warm["cache_hit"] is True
     assert type(warm["typing_guard_initializer_passive"]) is bool
     assert warm["typing_guard_initializer_passive"] is expected_passive
+    assert warm["typing_guard_marker_mutation"] is cold[
+        "typing_guard_marker_mutation"
+    ]
     assert warm["source_fingerprint"] == cold["source_fingerprint"]
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 3
+    assert cached["import_classification_semantics_version"] == 4
     assert type(cached["typing_guard_initializer_passive"]) is bool
     assert cached["typing_guard_initializer_passive"] is expected_passive
+    assert cached["typing_guard_marker_mutation"] is cold[
+        "typing_guard_marker_mutation"
+    ]
 
 
 def test_d2b2_r2_forged_stale_parent_cache_rejected(
@@ -1020,7 +1268,7 @@ def test_d2b2_r2_forged_stale_parent_cache_rejected(
     parent = root / "pkg" / "__init__.py"
     original_fingerprint = original.source_fingerprints_by_module["pkg.__init__"]
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 3
+    assert cached["import_classification_semantics_version"] == 4
     assert cached["typing_guard_initializer_passive"] is False
     cached["typing_guard_initializer_passive"] = True
     cached["import_classification_semantics_version"] = 2
@@ -1038,7 +1286,7 @@ def test_d2b2_r2_forged_stale_parent_cache_rejected(
     assert graph.hard_edges["pkg.a"] == {"pkg.b"}
     assert graph.hard_edges["pkg.b"] == {"pkg.a"}
     rewritten = _cache_data(root, parent)
-    assert rewritten["import_classification_semantics_version"] == 3
+    assert rewritten["import_classification_semantics_version"] == 4
     assert type(rewritten["typing_guard_initializer_passive"]) is bool
     assert rewritten["typing_guard_initializer_passive"] is False
 
@@ -1056,7 +1304,7 @@ def test_d2b2_r2_malformed_current_parent_cache_rejected(
     _index_graph(root)
     parent = root / "pkg" / "__init__.py"
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 3
+    assert cached["import_classification_semantics_version"] == 4
     if case == "missing":
         cached.pop("typing_guard_initializer_passive")
     else:
@@ -1094,7 +1342,7 @@ def test_d2b2_r2_malformed_current_parent_cache_rejected(
         for members in _scc_signature(replayed, graph)
     )
     rewritten = _cache_data(root, parent)
-    assert rewritten["import_classification_semantics_version"] == 3
+    assert rewritten["import_classification_semantics_version"] == 4
     assert type(rewritten["typing_guard_initializer_passive"]) is bool
     assert rewritten["typing_guard_initializer_passive"] is False
 
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index 9f487ae..0acc73f 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -227,6 +227,22 @@ D2B3_TYPED_SIDE_ATTRIBUTE = {
     ),
 }
 
+D2B4_INDEXED_LAUNCHER = {
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
+        "typing.TYPE_CHECKING = True\n"
+        "import pkg.a\n"
+    ),
+}
+
 D2B3_SOURCE_BOUND_NEGATIVES = [
     (
         "N01-no-marker",
@@ -1159,6 +1175,32 @@ def test_p1d3_d2b3_name_typed_side_import(tmp_path, isolated_dirs):
     _assert_d2b3_typed_side_evidence(root)
 
 
+def test_p1d3_d2b4_launcher_source_checker_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B4_INDEXED_LAUNCHER)
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
 def test_p1d3_d2b3_attribute_typed_side_import(tmp_path, isolated_dirs):
     root = write_synthetic_repository(
         tmp_path / "repo", D2B3_TYPED_SIDE_ATTRIBUTE,
```

## 32. CONTRACT_CONFLICTS
DIRECT_EVIDENCE: None encountered; production anchors matched.

## 33. DESIGN_GAPS
DIRECT_EVIDENCE: None encountered for the literal implementation.

## 34. UNKNOWN / UNSUPPORTED
UNKNOWN: Active LIVE loaded-code adoption and general Python runtime safety were not evaluated. No global suite was run.

## 35. FINAL IMPLEMENTER OBSERVATION
DIRECT_EVIDENCE: The specified focused suite and diff check pass; this report does not make the architect's GO decision. STOP after D2B-4.

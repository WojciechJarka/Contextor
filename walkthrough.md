# CONTEXTOR PY315-COMPAT-D2B-R1 — lazy import cache integrity and semantic freshness

## PREFLIGHT

DIRECT_EVIDENCE: HEAD `fe5ba37ebc77897722b4964dcc354b1a109bb348`. Pre-existing uncommitted D2B files were preserved. Canonical `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` is CPython 3.15.2. The isolated test repositories and cache/state/output paths were under pytest temporary storage outside the production repository. No production FULL, update_file, restart, cache clear, dependency change or commit.

## MCP_DISCOVERY

Contextor MCP documentation read first. Current module contexts for indexer, ImportRef, CacheManager, cycle lifecycle/materialization and incremental engine resolved at LIVE revision 977 before final test work, all target sources workspace_sync=verified, cycle_semantics=stale. Exact source inspection: `indexer.py::_process_single_file` reads a content-fingerprint-bound `CacheManager` entry, checks semantic version and typing guard flags, then reconstructs `ImportRef(**imp)`; no current-version `imports` payload validation existed. `CacheManager.get` validates source-content hash and path, not inner import fields. Source owner and precise edit scope: `contextor/core/symbol_engine/indexer.py` current-version cache gate only; focused regressions in `tests/test_py315_lazy_import_guard.py`.

## CACHE_VERSION_10_VALIDATION

Existing version gate rejects version 9. Current version 10 entries previously passed with missing/null/string/integer `is_lazy`; malformed imports collection could raise an uncaught TypeError. The validated source fingerprint did not prove payload integrity. Literal new gate requires `imports` to be a list; each element a dict with `is_lazy` present and `type(is_lazy) is bool`. Invalid entry is set to `None`, invoking existing source re-extraction. ImportRef default, AST extraction, graph, provenance, cycle models, version 10 and cache storage format are unchanged.

## MALFORMED_CACHE_REGRESSION

Before production edit, focused T01-T07 run: **5 failed, 2 passed**. T01 missing flag reconstructed `False` from explicit lazy source; T02 reconstructed `None`; T03 string and T04 integer were accepted; T05 dict in place of list raised `TypeError`; T06 valid True and T07 valid False reused. After literal correction: **7 passed**. Tests inject separate version-10 records with unchanged source fingerprint in synthetic Python 3.15 repositories, check re-extraction and serialized Boolean, and require valid records to be reused without parsing target source.

## IMPLEMENTATION_IF_REQUIRED

Defect confirmed before edit, so only `contextor/core/symbol_engine/indexer.py` production file was changed. The cache gate now rejects malformed import facts and falls back to pre-existing re-extraction. Test file extends the D2B focused suite. No other production source modified in R1.

## ORIGINAL_WORKER_PARITY

New synthetic eager/lazy test uses `index_repository(..., source_capture_module_ids=...)` with isolated worker/capture paths. Cold `pkg.a` ImportRef is `True` for explicit lazy and `False` for ordinary import; original-worker source capture reports `ALL_SELECTED_CAPTURED_NON_ATOMIC` and bytes match source. Warm index preserves the same Boolean. This proves these tested paths, not every original-worker mode.

## SELECTIVE_REPLAY_PARITY

Same synthetic cyclic fixture uses `iter_selective_scc_source_replays` and `iter_selective_scc_worker_captures` with warm index. Both lazy and ordinary variants returned respectively `BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC` and `WORKER_SECOND_PASS_BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC`; complete ImportRef equality means a lazy→eager change would fail the tested comparison. No production state mutated.

## TARGETED_TEST_RESULTS

- Initial cache regression: 5 failed, 2 passed, confirming defect.
- After correction: 7 passed in cache matrix; then 9 passed for cache plus replay/worker cases.
- Relevant D2B lazy guard, source replay, worker capture, flat/package models and stale-version-9 cache tests: **380 passed, 1 deselected**. The deselected symlink case is unrelated and requires Windows privilege.
- Python 3.10.9 executable `C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe`: 2 passed, 18 deselected for legacy AST/default-field and import serialization (plugin autoload disabled).
- No full pytest.

## CANONICAL_SEMANTIC_STATE

After change, Contextor module contexts for indexer and focused test show LIVE revision 980, canonical_state=fresh, workspace_sync=verified, advisory=null. Module/graph/topology/cycles families fresh; **cycle_semantics family stale**. `get_live_events(after_revision=976)` showed desktop_watcher updates at revisions 977-980, including indexer.py at 979 and test at 980, continuity=continuous. Current installed warning view is fresh at revision 980, structural_count=16, active_warning_count=16, model_pass_count=0. Fresh warning partition does not certify fresh cycle-semantic model evidence.

## SEMANTIC_INVALIDATION_CAUSE

CODE_PATH_PROVED: `contextor/core/analysis/incremental/engine.py:975-988` selects `SOURCE_CHANGED` for a nondeleted source update and calls `invalidate_cycle_semantics`; `core/cycle_semantics/lifecycle.py:95-153` preserves historical evidence, sets stale when a snapshot exists, and retains the first reason. Desktop watcher update_file events are direct evidence that source edits were committed into LIVE. The exact current `cycle_semantics_invalidation_reason` value was **not exposed by the queried MCP projection**, so `SOURCE_CHANGED` is a code-path explanation, not a direct read of the state field. No other cause was demonstrated.

## REFRESH_AUTHORITY_DISCOVERY

`contextor/core/api/facade.py:818-852` is the discovered production path calling `materialize_cycle_semantics` and `classify_full_cycle_semantics` during full project analysis. Repository search found this sole materialization call; incremental engine invalidates semantic evidence but does not rematerialize the complete family. Narrow partial SCC source/worker preparation can establish bounded claims under its own contract, but was not shown to set the global family fresh. Therefore no supported narrow refresh of the whole canonical cycle-semantic snapshot was found; FULL appears required for that family by current code path. The user forbade FULL and restart in R1. Exact prerequisite for certification: a separately authorized full analysis/publication with required source and runtime ownership gates, then read-only freshness and loaded-code verification. No privileged operation was performed.

## RUNTIME_CODE_ADOPTION

Read-only Windows process inventory found three venv redirectors and actual `C:\Python315\python.exe` children. Sanitized command-line classification identified an MCP-like actual process PID 11876 (parent redirector 12384), Desktop-like actual PID 10564 (parent redirector 6480), and LIVE actual PID 12660 (parent redirector 11660); observed process creation times were before R1 edits. This identifies process roles by command-line pattern and parent relationship, **not** which modules are loaded in each `sys.modules`. The indexer implementation may be loaded by analysis/worker contexts; active adoption of the edited cache gate was not verified. `workspace_sync=verified` only binds on-disk source to canonical FileState.

## POST_CHANGE_MCP_AUDIT

Read-only module contexts and LIVE events after edits: indexer and test indexed, workspace_sync=verified, canonical revision 980, cycles count 16 and active warnings 16. `get_project_architecture(fields=[])` also reports 16 fresh structural cycle paths, unchanged from D2B. The only production edit adds a Boolean payload check and no imports, so it introduces no new source hard-dependency edge. Cycle-semantic family remains stale; loaded-code adoption remains unverified. The project architecture report bundle is historical/persisted and was not equated with LIVE semantic freshness.

## FILES_CHANGED

Current R1 edits:
- `contextor/core/symbol_engine/indexer.py`
- `tests/test_py315_lazy_import_guard.py`
- `walkthrough.md` (report)

Other uncommitted D2B files were preserved, not changed by R1. The full diffs below are against HEAD and therefore also display preceding uncommitted D2B changes within the two R1-touched files.

## FULL_DIFFS

Complete actual unified diffs for both R1-touched source/test files:

```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 5ccbbdd..0b3f54a 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -78,7 +78,7 @@ SYMBOL_FACTS_SCHEMA_VERSION = 2
 REFERENCE_FACTS_SCHEMA_VERSION = 1
 COLLISION_FACTS_SCHEMA_VERSION = 1
 TEST_FACTS_SCHEMA_VERSION = 1
-IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 9
+IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 10
 _IMPORTABLE_BINARY_SUFFIXES = tuple(
     sorted(
         frozenset(BYTECODE_SUFFIXES)
@@ -264,6 +264,11 @@ class AdvancedImportVisitor(ast.NodeVisitor):
     def visit_Import(self, node):
 
         is_local = self._in_function_depth > 0
+        is_lazy = getattr(node, "is_lazy", False)
+        if is_lazy is None:
+            is_lazy = False
+        if type(is_lazy) not in (bool, int) or is_lazy not in (0, 1):
+            raise ValueError("invalid AST import is_lazy value")
         type_only = False
         if (
             id(node) in self._type_only_statement_ids
@@ -284,12 +289,18 @@ class AdvancedImportVisitor(ast.NodeVisitor):
                     is_from_import=False,
                     is_local=is_local,
                     type_only=type_only,
+                    is_lazy=bool(is_lazy),
                 )
             )
 
     def visit_ImportFrom(self, node):
 
         is_local = self._in_function_depth > 0
+        is_lazy = getattr(node, "is_lazy", False)
+        if is_lazy is None:
+            is_lazy = False
+        if type(is_lazy) not in (bool, int) or is_lazy not in (0, 1):
+            raise ValueError("invalid AST import is_lazy value")
 
         names = [item.name for item in node.names]
 
@@ -300,6 +311,7 @@ class AdvancedImportVisitor(ast.NodeVisitor):
                 names=names,
                 is_from_import=True,
                 is_local=is_local,
+                is_lazy=bool(is_lazy),
             )
         )
 
@@ -943,6 +955,13 @@ def _process_single_file(
             is not int
             or cached_data.get("import_classification_semantics_version")
             != IMPORT_CLASSIFICATION_SEMANTICS_VERSION
+            or type(cached_data.get("imports")) is not list
+            or any(
+                type(imp) is not dict
+                or "is_lazy" not in imp
+                or type(imp["is_lazy"]) is not bool
+                for imp in cached_data["imports"]
+            )
             or type(
                 cached_data.get(
                     "typing_guard_initializer_passive"
diff --git a/tests/test_py315_lazy_import_guard.py b/tests/test_py315_lazy_import_guard.py
new file mode 100644
index 0000000..9ea798c
--- /dev/null
+++ b/tests/test_py315_lazy_import_guard.py
@@ -0,0 +1,307 @@
+"""Focused Python 3.15 explicit-lazy import preservation and model guards."""
+
+import ast
+from dataclasses import asdict
+
+import pytest
+
+from contextor.core.cycle_semantics.edge_sites import analyze_cyclic_import_sites
+from contextor.core.cycle_semantics.execution_context import project_execution_context
+from contextor.core.cycle_semantics.initialization_model import evaluate_flat_import_order
+from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
+from contextor.core.cycle_semantics.provenance import extract_import_provenance
+from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
+from contextor.core.cycle_semantics import selective_source_replay
+from contextor.core.cycle_semantics import selective_worker_capture
+from contextor.core.analysis.cache_manager import CacheManager
+from contextor.core.domain.imports import ImportRef
+from contextor.core.domain.module import Module
+from contextor.core.graph.graph import build_graph
+from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+from contextor.core.source import ParsedSourceInput
+from contextor.core.symbol_engine.indexer import (
+    AdvancedImportVisitor,
+    IMPORT_CLASSIFICATION_SEMANTICS_VERSION,
+)
+from contextor.core.symbol_engine import indexer
+
+
+def _imports(source):
+    visitor = AdvancedImportVisitor()
+    visitor.visit(ast.parse(source))
+    return visitor.found_imports
+
+
+def _provenance(source):
+    return extract_import_provenance(
+        ast.parse(source),
+        module_id="a",
+        source_key="a.py",
+        source_path="a.py",
+        source_fingerprint="fingerprint",
+    )
+
+
+def test_explicit_lazy_import_and_from_preserved_in_importref():
+    eager = _imports("import b\nfrom b import value\n")
+    lazy = _imports("lazy import b\nlazy from b import value\n")
+    assert [item.is_lazy for item in eager] == [False, False]
+    assert [item.is_lazy for item in lazy] == [True, True]
+    for left, right in zip(eager, lazy):
+        assert {k: v for k, v in asdict(left).items() if k != "is_lazy"} == {
+            k: v for k, v in asdict(right).items() if k != "is_lazy"
+        }
+        assert ImportRef(**asdict(right)) == right
+
+
+def test_provenance_and_lexical_execution_projections_preserve_declaration():
+    facts = _provenance("lazy import b\nlazy from b import value\n")
+    assert [item.is_lazy for item in facts.occurrences] == [True, True]
+    assert [(item.ordinal, item.line, item.column, item.form) for item in facts.occurrences] == [
+        (0, 1, 0, "IMPORT"),
+        (1, 2, 0, "IMPORT_FROM"),
+    ]
+    assert all(item.source_fingerprint == "fingerprint" for item in [facts])
+    assert [item.is_lazy for item in project_execution_context(facts).contexts] == [True, True]
+    assert all(
+        item.initialization_reachability == "UNKNOWN"
+        for item in project_execution_context(facts).contexts
+    )
+
+
+def test_legacy_ast_without_lazy_field_defaults_false():
+    tree = ast.parse("import b\nfrom b import value\n")
+    for node in tree.body:
+        if hasattr(node, "is_lazy"):
+            del node.is_lazy
+    visitor = AdvancedImportVisitor()
+    visitor.visit(tree)
+    facts = extract_import_provenance(
+        tree,
+        module_id="a",
+        source_key="a.py",
+        source_path="a.py",
+        source_fingerprint="fingerprint",
+    )
+    assert [item.is_lazy for item in visitor.found_imports] == [False, False]
+    assert [item.is_lazy for item in facts.occurrences] == [False, False]
+
+
+def test_malformed_ast_lazy_flag_is_rejected():
+    tree = ast.parse("import b")
+    tree.body[0].is_lazy = "unexpected"
+    visitor = AdvancedImportVisitor()
+    with pytest.raises(ValueError, match="is_lazy"):
+        visitor.visit(tree)
+    with pytest.raises(ValueError, match="is_lazy"):
+        extract_import_provenance(
+            tree, module_id="a", source_key="a.py",
+            source_path="a.py", source_fingerprint="fingerprint",
+        )
+
+
+def test_l03_no_false_flat_hazard_and_l01_eager_hazard_retained():
+    eager = {
+        "a": ast.parse("from b import value\nvalue = 1\n"),
+        "b": ast.parse("from a import value\nvalue = 2\n"),
+    }
+    lazy = {
+        "a": ast.parse("lazy from b import value\nvalue = 1\n"),
+        "b": ast.parse("lazy from a import value\nvalue = 2\n"),
+    }
+    assert evaluate_flat_import_order(eager, "a").outcome == "EARLY_BINDING_HAZARD"
+    assert evaluate_flat_import_order(lazy, "a").outcome == "UNKNOWN"
+    graph = {"a": {"b"}, "b": {"a"}}
+    result = analyze_cycle_scenarios(graph, lazy)
+    assert result.components[0].classification == "INDETERMINATE"
+    assert result.components[0].coverage == "NONE"
+    assert result.components[0].reason == "UNMODELED_EXPLICIT_LAZY_IMPORT"
+    assert result.topology == analyze_cycle_scenarios(graph, eager).topology
+
+
+@pytest.mark.parametrize(
+    "source",
+    [
+        "lazy import b\nx = b.value\nvalue = 1\n",
+        "lazy from b import value\nx = value\nvalue = 1\n",
+    ],
+)
+def test_lazy_first_use_is_never_model_pass(source):
+    tree = ast.parse(source)
+    assert evaluate_flat_import_order({"a": tree, "b": ast.parse("import a\nvalue = 2")}, "a").outcome == "UNKNOWN"
+
+
+def test_package_model_rejects_lazy_imports_in_source_closure():
+    sources = {
+        "pkg.__init__": ast.parse("lazy from pkg import child\nvalue = 1\n"),
+        "pkg.child": ast.parse("from pkg import value\n"),
+    }
+    assert evaluate_package_import_order(sources, "pkg").outcome == "UNKNOWN"
+    graph = {"pkg.__init__": {"pkg.child"}, "pkg.child": {"pkg.__init__"}}
+    component = analyze_cycle_scenarios(graph, sources).components[0]
+    assert (component.classification, component.coverage, component.reason) == (
+        "INDETERMINATE", "NONE", "UNMODELED_EXPLICIT_LAZY_IMPORT",
+    )
+
+
+def test_structural_graph_and_sites_preserve_eager_lazy_edges():
+    graph = {"a": {"b"}, "b": {"a"}}
+    outputs = []
+    for keyword in ("", "lazy "):
+        imports = {
+            name: _imports(f"{keyword}import {target}\n")
+            for name, target in (("a", "b"), ("b", "a"))
+        }
+        modules = {
+            name: Module(name, name + ".py", "/fixture/" + name + ".py", facts)
+            for name, facts in imports.items()
+        }
+        actual = build_graph(modules)
+        parsed = {
+            name: ParsedSourceInput(
+                ast.parse(f"{keyword}import {target}\n"), "a" * 64,
+            )
+            for name, target in (("a", "b"), ("b", "a"))
+        }
+        sites = analyze_cyclic_import_sites(graph, parsed)
+        outputs.append((actual.hard_edges, sites.topology))
+        assert all(
+            site.is_lazy is bool(keyword)
+            for component in sites.components
+            for edge in component.internal_edges
+            for site in edge.sites
+        )
+    assert outputs[0] == outputs[1]
+    assert outputs[0][0] == graph
+
+
+def test_import_semantics_version_and_round_trip():
+    assert IMPORT_CLASSIFICATION_SEMANTICS_VERSION == 10
+    old = ImportRef("b", 0, [], False)
+    new = ImportRef(**{**asdict(old), "is_lazy": True})
+    assert old.is_lazy is False
+    assert new.is_lazy is True
+    assert ImportRef(**asdict(new)) == new
+
+
+def test_full_and_incremental_import_fact_parity_for_lazy_declaration(tmp_path):
+    from tests.test_incremental_equivalence import bootstrap_state, init_engine
+
+    root = tmp_path / "repo"
+    root.mkdir()
+    target = root / "a.py"
+    target.write_text("import b\nvalue = 1\n", encoding="utf-8")
+    (root / "b.py").write_text("import a\nvalue = 2\n", encoding="utf-8")
+
+    registry = PersistentIdentityRegistry(str(root))
+    state = bootstrap_state(root, registry)
+    engine = init_engine(tmp_path, root, state, registry)
+    target.write_text("lazy import b\nvalue = 1\n", encoding="utf-8")
+    result = engine.update_file(str(target))
+    assert result.graph_state == "fresh"
+
+    baseline = bootstrap_state(root, PersistentIdentityRegistry(str(root)))
+    assert engine.state.modules["a"].imports == baseline.modules["a"].imports
+    assert engine.state.modules["a"].imports[0].is_lazy is True
+    assert engine.state.dependency_graph.hard_edges == baseline.dependency_graph.hard_edges
+
+
+@pytest.mark.parametrize("mutation", ["missing", "null", "string", "integer", "malformed_list"])
+def test_current_version_malformed_lazy_import_cache_is_reextracted(
+    tmp_path, isolated_dirs, monkeypatch, mutation,
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    (root / "a.py").write_text("lazy import b\n", encoding="utf-8")
+    (root / "b.py").write_text("pass\n", encoding="utf-8")
+    indexer.index_repository(str(root))
+    cache = CacheManager(str(root))
+    source = root / "a.py"
+    record = cache.get(source)
+    assert record["import_classification_semantics_version"] == 10
+    assert record["imports"][0]["is_lazy"] is True
+    if mutation == "missing":
+        del record["imports"][0]["is_lazy"]
+    elif mutation == "null":
+        record["imports"][0]["is_lazy"] = None
+    elif mutation == "string":
+        record["imports"][0]["is_lazy"] = "true"
+    elif mutation == "integer":
+        record["imports"][0]["is_lazy"] = 1
+    else:
+        record["imports"] = {"not": "a list"}
+    cache.set(source, record)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    result = indexer.index_repository(str(root))
+    assert result.modules["a"].imports[0].is_lazy is True
+    assert type(result.modules["a"].imports[0].is_lazy) is bool
+    rewritten = cache.get(source)
+    assert rewritten["imports"][0]["is_lazy"] is True
+
+
+@pytest.mark.parametrize("keyword, expected", [("lazy ", True), ("", False)])
+def test_current_version_valid_lazy_import_cache_is_reused(
+    tmp_path, isolated_dirs, monkeypatch, keyword, expected,
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    (root / "a.py").write_text(f"{keyword}import b\n", encoding="utf-8")
+    (root / "b.py").write_text("pass\n", encoding="utf-8")
+    indexer.index_repository(str(root))
+    cache = CacheManager(str(root))
+    record = cache.get(root / "a.py")
+    assert record["imports"][0]["is_lazy"] is expected
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    original_parse = indexer.parse_source_snapshot
+
+    def reject_target_parse(snapshot, path):
+        if path.name == "a.py":
+            raise AssertionError("valid current-version cache must be reused")
+        return original_parse(snapshot, path)
+
+    monkeypatch.setattr(indexer, "parse_source_snapshot", reject_target_parse)
+    result = indexer.index_repository(str(root))
+    assert result.modules["a"].imports[0].is_lazy is expected
+
+
+@pytest.mark.parametrize("keyword, expected", [("lazy ", True), ("", False)])
+def test_replay_and_worker_capture_keep_explicit_lazy_fact(
+    tmp_path, isolated_dirs, monkeypatch, keyword, expected,
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    pkg = root / "pkg"
+    pkg.mkdir(parents=True)
+    (pkg / "__init__.py").write_text("", encoding="utf-8")
+    (pkg / "a.py").write_text(f"{keyword}import pkg.b\nvalue = 1\n", encoding="utf-8")
+    (pkg / "b.py").write_text("import pkg.a\nvalue = 2\n", encoding="utf-8")
+
+    cold = indexer.index_repository(
+        str(root),
+        source_capture_module_ids=frozenset({"pkg.a", "pkg.b"}),
+    )
+    assert cold.modules["pkg.a"].imports[0].is_lazy is expected
+    assert cold.original_worker_capture_status == "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    assert cold.original_worker_source_snapshots["pkg.a"].raw == (
+        pkg / "a.py"
+    ).read_bytes()
+
+    warm = indexer.index_repository(str(root))
+    assert warm.modules["pkg.a"].imports[0].is_lazy is expected
+    edges = build_graph(warm.modules).hard_edges
+    (replay,) = tuple(
+        selective_source_replay.iter_selective_scc_source_replays(
+            root, edges, warm,
+        )
+    )
+    assert replay.status == "BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
+    (capture,) = tuple(
+        selective_worker_capture.iter_selective_scc_worker_captures(
+            root, edges, warm,
+        )
+    )
+    assert capture.status == (
+        "WORKER_SECOND_PASS_BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
+    )
```

## REMAINING_UNKNOWN

Direct current state-field read of `cycle_semantics_invalidation_reason`; fresh global semantic evidence after an authorized full refresh; active in-process adoption of edited indexer code; exhaustive original-worker modes and actual production caches. No known source-integrity failure remains in tested version-10 cache cases.

## FINAL_VERDICT

**PARTIAL_PY315_D2B_R1_RUNTIME_GATE_PENDING**

Source cache integrity and targeted parity tests pass. Canonical cycle-semantic family is stale and active runtime code adoption remains unverified. Stop.

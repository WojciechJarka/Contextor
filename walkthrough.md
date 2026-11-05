# CONTEXTOR C16-B03-P1A

## PREFLIGHT

DIRECT_EVIDENCE: HEAD 273503728aa5478864d344f21e974634d2ac1c79. CPython 3.15.2 from .venv. Initial worktree clean. P0 accepted in current baseline; its source and tests were preserved. MCP preflight: model_source_closure workspace_sync=verified, canonical revision 989, 16 fresh structural DFS paths; cycle_semantics stale.

## MCP_DISCOVERY

CONTRACT_PROVED: model_source_closure owns the old hard-reachable SCC closure. Its consumers include evidence, original worker binding and planning. MCP symbol lineage resolved the exact function; call context is intra-module only and had zero edges, so it does not establish inter-module completeness. Source inspection confirmed ImportRef fields and canonical model_identity translation. Graph builder suppresses named-child soft edges when reexport bindings exist.

## EXACT_FILE_SCOPE

Production: contextor/core/cycle_semantics/model_source_closure.py. New tests: tests/test_cycle_semantics_optional_child_source_cohort.py. Report: walkthrough.md. No other source/test files changed.

## PURE_PLANNER_IMPLEMENTATION

Added compute_cycle_model_source_closures_with_optional_children(hard_edges, indexed_imports_by_module, *, package_root=None) returning CycleModelSourceClosure tuples. It only reads supplied graph/import facts, does not read source, import analyzed modules, mutate input, certify safety, or publish claims. Existing compute_cycle_model_source_closures is unchanged.

## INPUT_DOMAIN_VALIDATION

Exact graph/import module key agreement, indexed target membership, module identity, package root, ImportRef type/fields, flags and names are validated before selection. Malformed, missing, ambiguous and unsupported selected forms raise ValueError; no partial cohort is returned. Caller must supply the complete first-pass index domain; this is an input contract, not independently authenticated by the pure function.

## ABSOLUTE_RELATIVE_RESOLUTION

Relative import base follows the package consistency checker's initializer/module context and level rules. Absolute base strips the supplied canonical package_root prefix. Indexed package initializer and direct module collision fails closed. Candidate child identity uses canonical logical_to_indexed_module.

## OPTIONAL_CHILD_FIXED_POINT

Each original SCC evidence cohort is expanded by selected named children, their hard-reachable targets and indexed ancestor initializers. Every newly selected source is rescanned for further optional children until no new source remains. Returned cohorts are sorted, deduplicated and monotonic; original members, hard closure and implicit initializer tuple are retained.

## EVENTUAL_REEXPORT_SHADOWING

Selection reads indexed ImportRef facts directly and does not inspect soft_edges. A test confirms graph reexport binding suppresses the soft edge while the indexed same-name child is still included.

## CANONICAL_GRAPH_INVARIANTS

The planner does not mutate hard_edges or soft_edges. It does not promote selected child edges into the canonical graph. Original closure and version constant remain unchanged. Production claim preparation remains on the original planner.

## POSITIVE_TEST_RESULTS

P01 no child preserves original. P02 UI theme and repo generator child selected. P03/P07 eventual binding suppresses soft edge yet child selected. P04 hard dependency of optional child selected. P05 second optional child reached through that dependency. P06 indexed ancestor initializers selected. P07 fact reorder preserves result. P08 original closure equals recomputed original. Absolute package_root normalization also tested.

## NEGATIVE_TEST_RESULTS

N01 missing module rejects. N02 malformed fact rejects. N03 direct/initializer ambiguity rejects. N04 invalid relative level rejects. N05 >256 selected rejects. N06 optional cycle terminates with members retained. N07 reexport cannot hide child. N08 missing/forged input cannot yield a candidate result; the returned dataclass has no certificate or status field. N09 graph remains unchanged. N10 no MODEL_PASS or publication call/path added.

## TARGETED_PYTEST_RESULTS

New planner tests: 7 passed. Selected existing closure, P0 and canonical graph regressions: 13 passed, 129 deselected. No full suite, backend restart, FULL, dependency install or update_file.

## LEGACY_CLOSURE_PARITY

The existing function body and MODEL_SOURCE_CLOSURE_VERSION were not changed. Direct data-structure equality asserted in P01/P08 tests.

## SOURCE_COHORT_BUDGET

Capacity 256 enforced on initial and expanded cohorts and union across SCCs. Over-capacity fails with ValueError, never truncates. Process, AST and byte budgets unchanged.

## NEXT_STAGE_INTEGRATION_BOUNDARIES

P1A is only a candidate selector. Original worker planning/binding, source proof, manifest, claims, publication, evidence semantic version and warning policy were not changed. Full B03 source-bound certification remains a later stage.

## POST_CHANGE_MCP_AUDIT

DIRECT_EVIDENCE: changed module context still canonical revision 989, canonical_state=fresh, workspace_sync=out_of_sync with target modified advisory. Thus current disk source is newer than canonical FileState and indexed-source freshness is unverified; no runtime adoption claim. Architecture overlay: 16 fresh structural DFS paths, cycle_semantics=stale, model_pass_count=0. No new structural edge detected in the unchanged canonical graph; new source has not been ingested, so this is not a post-index graph proof. New test module is not yet in active module registry. No update_file or runtime restart was used.

## FILES_CHANGED

- contextor/core/cycle_semantics/model_source_closure.py
- tests/test_cycle_semantics_optional_child_source_cohort.py

walkthrough.md was overwritten as the report and is excluded from source/test diff accounting.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/model_source_closure.py b/contextor/core/cycle_semantics/model_source_closure.py
index 47ad7de..e1c4269 100644
--- a/contextor/core/cycle_semantics/model_source_closure.py
+++ b/contextor/core/cycle_semantics/model_source_closure.py
@@ -8,6 +8,9 @@ from __future__ import annotations
 from collections.abc import Mapping
 from dataclasses import dataclass
 
+from contextor.core.domain.imports import ImportRef
+
+from .model_identity import indexed_to_logical_module, logical_to_indexed_module
 from .scc import analyze_import_cycle_topology
 
 
@@ -75,3 +78,137 @@ def compute_cycle_model_source_closures(
             )),
         ))
     return tuple(rows)
+
+
+def compute_cycle_model_source_closures_with_optional_children(
+    hard_edges: Mapping[str, object],
+    indexed_imports_by_module: Mapping[str, object],
+    *,
+    package_root: str | None = None,
+) -> tuple[CycleModelSourceClosure, ...]:
+    """Select a bounded index-backed candidate source cohort, without certifying it."""
+    if not isinstance(hard_edges, Mapping) or not isinstance(indexed_imports_by_module, Mapping):
+        raise ValueError("Graph and import facts must be mappings")
+    if package_root is not None and (
+        type(package_root) is not str
+        or not package_root
+        or any(not part.isidentifier() for part in package_root.split("."))
+    ):
+        raise ValueError("Invalid package root")
+    indexed = frozenset(hard_edges)
+    if indexed != frozenset(indexed_imports_by_module):
+        raise ValueError("Indexed import facts must cover the exact hard graph domain")
+    if any(type(module) is not str or not module or
+           any(not part.isidentifier() for part in module.split(".")) for module in indexed):
+        raise ValueError("Invalid indexed module identity")
+    adjacency: dict[str, tuple[str, ...]] = {}
+    facts: dict[str, tuple[ImportRef, ...]] = {}
+    for module in sorted(indexed):
+        targets = hard_edges[module]
+        if not isinstance(targets, (set, frozenset, tuple, list)) or any(
+            type(target) is not str or target not in indexed for target in targets
+        ):
+            raise ValueError("Invalid hard graph targets")
+        adjacency[module] = tuple(sorted(set(targets)))
+        imports = indexed_imports_by_module[module]
+        if not isinstance(imports, (tuple, list)):
+            raise ValueError("Invalid indexed import facts")
+        for imp in imports:
+            if (
+                type(imp) is not ImportRef
+                or (imp.module is not None and (
+                    type(imp.module) is not str
+                    or not imp.module
+                    or any(not part.isidentifier() for part in imp.module.split("."))
+                ))
+                or type(imp.level) is not int or imp.level < 0
+                or type(imp.names) is not list
+                or any(type(name) is not str or not name or
+                       (name != "*" and not name.isidentifier()) for name in imp.names)
+                or any(type(getattr(imp, flag)) is not bool for flag in (
+                    "is_from_import", "is_local", "type_only", "is_lazy"
+                ))
+                or (imp.level == 0 and imp.module is None)
+            ):
+                raise ValueError("Invalid indexed import fact")
+        facts[module] = tuple(imports)
+
+    def ancestors(module: str) -> tuple[str, ...]:
+        parts = module.split(".")
+        if parts[-1] == "__init__":
+            parts = parts[:-1]
+        return tuple(
+            ".".join(parts[:length]) + ".__init__"
+            for length in range(1, len(parts))
+            if ".".join(parts[:length]) + ".__init__" in indexed
+        )
+
+    def optional_children(module: str) -> tuple[str, ...]:
+        found: set[str] = set()
+        for imp in facts[module]:
+            if not imp.is_from_import:
+                continue
+            if imp.level:
+                logical = indexed_to_logical_module(module)
+                context = logical if module.endswith(".__init__") else logical.rpartition(".")[0]
+                parts = context.split(".") if context else []
+                if imp.level > len(parts):
+                    raise ValueError("Invalid relative import target")
+                base = ".".join(parts[:len(parts) - imp.level + 1])
+                if imp.module:
+                    base += "." + imp.module
+            else:
+                base = imp.module
+                if package_root and base and base.startswith(package_root + "."):
+                    base = base[len(package_root) + 1:]
+            if not base:
+                raise ValueError("Unresolved import base")
+            direct = base in indexed
+            initializer = base + ".__init__" in indexed
+            if direct and initializer:
+                raise ValueError("Ambiguous module and initializer identity")
+            if not initializer:
+                continue
+            for name in imp.names:
+                if name == "*":
+                    raise ValueError("Unsupported star package member import")
+                child_name = base + "." + name
+                direct = child_name in indexed
+                initializer = child_name + ".__init__" in indexed
+                if direct and initializer:
+                    raise ValueError("Ambiguous module and initializer identity")
+                child = logical_to_indexed_module(child_name, indexed)
+                if child is not None:
+                    found.add(child)
+        return tuple(sorted(found))
+
+    rows: list[CycleModelSourceClosure] = []
+    selected_all: set[str] = set()
+    for original in compute_cycle_model_source_closures(hard_edges):
+        evidence = set(original.evidence_source_modules)
+        if len(evidence) > 256:
+            raise ValueError("Selected source capacity exceeded")
+        pending = list(sorted(evidence, reverse=True))
+        while pending:
+            module = pending.pop()
+            for child in optional_children(module):
+                to_visit = [child]
+                while to_visit:
+                    item = to_visit.pop()
+                    if item in evidence:
+                        continue
+                    evidence.add(item)
+                    if len(evidence) > 256:
+                        raise ValueError("Selected source capacity exceeded")
+                    pending.append(item)
+                    to_visit.extend((*adjacency[item], *ancestors(item)))
+        selected_all.update(evidence)
+        if len(selected_all) > 256:
+            raise ValueError("Selected source capacity exceeded")
+        rows.append(CycleModelSourceClosure(
+            members=original.members,
+            hard_reachable_modules=original.hard_reachable_modules,
+            evidence_source_modules=tuple(sorted(evidence)),
+            implicit_initializer_modules=original.implicit_initializer_modules,
+        ))
+    return tuple(rows)
diff --git a/tests/test_cycle_semantics_optional_child_source_cohort.py b/tests/test_cycle_semantics_optional_child_source_cohort.py
new file mode 100644
index 0000000..33d5544
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_child_source_cohort.py
@@ -0,0 +1,138 @@
+"""Index-backed optional package-child source selection."""
+
+from __future__ import annotations
+
+import pytest
+
+from contextor.core.cycle_semantics.model_source_closure import (
+    compute_cycle_model_source_closures,
+    compute_cycle_model_source_closures_with_optional_children,
+)
+from contextor.core.domain.imports import ImportRef
+from contextor.core.graph.graph import build_graph
+from contextor.core.graph.resolver import build_trie, detect_package_root
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
+from contextor.core.symbol_engine.indexer import index_repository
+from tests.cycle_semantics_lab import write_synthetic_repository
+
+
+def _candidate(tmp_path, files):
+    root = tmp_path / "repo"
+    write_synthetic_repository(root, files)
+    index = index_repository(str(root))
+    facts = materialize_reexport_facts_by_module(
+        index.modules, index.reference_facts_by_module
+    )
+    trie = build_trie(index.modules)
+    package_root = detect_package_root(index.modules, trie)
+    graph = build_graph(
+        index.modules, trie=trie, package_root=package_root,
+        reexport_facts_by_module=facts,
+    )
+    imports = {name: module.imports for name, module in index.modules.items()}
+    original = compute_cycle_model_source_closures(graph.hard_edges)
+    expanded = compute_cycle_model_source_closures_with_optional_children(
+        graph.hard_edges, imports, package_root=package_root
+    )
+    return graph, imports, original, expanded
+
+
+BASE = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": "import pkg.b\nfrom pkg import value\n",
+    "pkg/b.py": "import pkg.a\n",
+}
+
+
+def test_p01_no_indexed_child_preserves_original(tmp_path):
+    graph, _, original, expanded = _candidate(tmp_path, BASE)
+    assert expanded == original
+    assert graph.hard_edges
+
+
+def test_p02_to_p07_fixed_point_and_reexport_shadow(tmp_path):
+    files = {
+        "contextor/__init__.py": "pass\n",
+        "contextor/ui/__init__.py": "theme = 1\n",
+        "contextor/ui/theme.py": "import contextor.extra\n",
+        "contextor/repo_generator/__init__.py": "pass\n",
+        "contextor/repo_generator/run_repo_generator.py": "pass\n",
+        "contextor/extra.py": "from contextor.repo_generator import run_repo_generator\n",
+        "contextor/a.py": "import contextor.b\nfrom contextor.ui import theme\n",
+        "contextor/b.py": "import contextor.a\n",
+    }
+    graph, imports, original, expanded = _candidate(tmp_path, files)
+    selected = set(expanded[0].evidence_source_modules)
+    assert {"contextor.ui.theme", "contextor.extra",
+            "contextor.repo_generator.run_repo_generator",
+            "contextor.ui.__init__", "contextor.repo_generator.__init__"} <= selected
+    assert expanded[0].hard_reachable_modules == original[0].hard_reachable_modules
+    assert expanded[0].implicit_initializer_modules == original[0].implicit_initializer_modules
+    assert "contextor.ui.theme" not in graph.hard_edges["contextor.a"]
+    assert "contextor.ui.theme" not in graph.soft_edges["contextor.a"]
+    reordered = {name: list(reversed(rows)) for name, rows in imports.items()}
+    assert compute_cycle_model_source_closures_with_optional_children(
+        graph.hard_edges, reordered
+    ) == expanded
+    assert compute_cycle_model_source_closures(graph.hard_edges) == original
+
+
+def test_absolute_package_root_normalization(tmp_path):
+    files = {
+        "pkg/__init__.py": "pass\n",
+        "pkg/a.py": "import pkg.b\nfrom outer.pkg import child\n",
+        "pkg/b.py": "import pkg.a\n",
+        "pkg/child.py": "pass\n",
+    }
+    graph, imports, _, _ = _candidate(tmp_path, files)
+    expanded = compute_cycle_model_source_closures_with_optional_children(
+        graph.hard_edges, imports, package_root="outer"
+    )
+    assert "pkg.child" in expanded[0].evidence_source_modules
+
+
+def test_n01_n02_domain_and_fact_validation(tmp_path):
+    graph, imports, _, _ = _candidate(tmp_path, BASE)
+    missing = dict(imports)
+    missing.pop("pkg.a")
+    with pytest.raises(ValueError):
+        compute_cycle_model_source_closures_with_optional_children(graph.hard_edges, missing)
+    malformed = dict(imports)
+    malformed["pkg.a"] = [object()]
+    with pytest.raises(ValueError):
+        compute_cycle_model_source_closures_with_optional_children(graph.hard_edges, malformed)
+
+
+def test_n03_n04_ambiguity_and_invalid_relative(tmp_path):
+    graph, imports, _, _ = _candidate(tmp_path, BASE)
+    hard = dict(graph.hard_edges)
+    hard["pkg"] = set()
+    imports["pkg"] = []
+    with pytest.raises(ValueError):
+        compute_cycle_model_source_closures_with_optional_children(hard, imports)
+    imports = dict(imports)
+    imports["pkg.a"] = [ImportRef(module=None, level=9, names=["value"], is_from_import=True)]
+    with pytest.raises(ValueError):
+        compute_cycle_model_source_closures_with_optional_children(graph.hard_edges,
+            {name: rows for name, rows in imports.items() if name != "pkg"})
+
+
+def test_n05_capacity_and_n06_cycle(tmp_path):
+    graph, imports, _, _ = _candidate(tmp_path, BASE)
+    hard = {name: set(targets) for name, targets in graph.hard_edges.items()}
+    hard["pkg.a"].update(f"extra{i}" for i in range(257))
+    all_imports = {**imports, **{f"extra{i}": [] for i in range(257)}}
+    with pytest.raises(ValueError):
+        compute_cycle_model_source_closures_with_optional_children(hard, all_imports)
+    files = {**BASE, "pkg/value.py": "from pkg import a\n"}
+    _, _, _, expanded = _candidate(tmp_path / "cycle", files)
+    assert {"pkg.value", "pkg.a"} <= set(expanded[0].evidence_source_modules)
+
+
+def test_n08_n09_n10_candidate_never_certifies_or_mutates(tmp_path):
+    graph, imports, original, expanded = _candidate(tmp_path, BASE)
+    before = {name: set(targets) for name, targets in graph.hard_edges.items()}
+    assert graph.hard_edges == before
+    assert expanded == original
+    assert all(not hasattr(row, "status") and not hasattr(row, "model_pass")
+               for row in expanded)
```

## FINAL_VERDICT

C16_B03_P1A_PARTIAL

Reason: implementation and focused tests pass, but the mandatory post-change audit found workspace_sync=out_of_sync for changed production source; indexed-source freshness and runtime adoption cannot be certified at this revision. No claim of full B03 resolution.

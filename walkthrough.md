# CONTEXTOR C16-B03-P1B

## PREFLIGHT

Initial local HEAD e3f9e14780f069f113c135feda6c60d81e3df091; initial worktree clean. During execution an external Auto-commit advanced HEAD to 07eed64c131bd0525acbd7b20655c58a3b68168a; this task did not commit. P0/P1A/R1 source and test state present. MCP preflight revision 993; both owner modules verified; cycle_semantics stale.

## MCP_DISCOVERY

Contextor module contexts identified original_worker_binding and original_worker_reindex_planning. Exact source inspection confirmed existing hard-only closure, byte binding, full index inventory and two-pass checks. Lineage requests required large output and were not used as proof of inter-module call completeness. Source and focused tests established concrete owners and consumers.

## EXACT_FILE_SCOPE

Production changes: contextor/core/cycle_semantics/original_worker_binding.py; contextor/core/cycle_semantics/original_worker_reindex_planning.py. New tests: tests/test_cycle_semantics_optional_child_worker_capture.py. Report: walkthrough.md. No other source/test edits by this task.

## SOURCE_SELECTION_MODES

HARD_ONLY remains the default keyword-only mode for planning and binding. OPTIONAL_NAMED_CHILDREN explicitly opts in. Plan has a trailing defaulted source_selection field. Unknown modes fail closed. Verification reads plan mode and passes it to binding.

## SHARED_SELECTOR_CONTRACT

One private binding-module helper selects sources for both planning and binding. HARD_ONLY uses the original closure; optional mode uses P1A planner and actual RepositoryIndex ImportRef records. It validates exact module, fingerprint and hard-graph domains, returns sorted union, enforces 256 limit, and converts ValueError to UNAVAILABLE at public callers. It does not use soft edges or modify graph.

## PACKAGE_ROOT_RESOLUTION

Optional helper calls existing build_trie and detect_package_root. Two-pass verifier compares resolved package roots. Test changes selected import facts with unchanged fingerprints/graph and separately changes detected package root; both fail closed.

## OPTIONAL_CAPTURE_PLAN

Opt-in plan includes optional child, transitive hard dependency, second optional child and required ancestor initializers. It preserves graph SHA-256, full first-pass fingerprint inventory, full module path inventory and selected module IDs. Capture remains index_repository(root, source_capture_module_ids=plan.selected_module_ids).

## WORKER_RAW_BYTES_BINDING

Binding checks selected capture key equality for optional mode, SourceSnapshot type, AST mode, raw SHA-256 versus indexed fingerprint, per-file and total byte budgets. Tests include CRLF raw bytes, missing/extra captures, tampered bytes, stale hash and invalid mode. No source read occurs in binding.

## TWO_PASS_VERIFICATION

Existing graph, path inventory, fingerprint inventory, skipped-file, capture-status and exact capture-key checks remain. Optional mode recomputes selection on both indexes, compares both to plan IDs, compares package roots, then binds captured bytes. Differences return UNAVAILABLE.

## LEGACY_HARD_ONLY_PARITY

Existing hard-only default plan and binding tests pass. Selected legacy regressions initially found changed reason text for over-capacity; corrected both public callers to preserve exact CLOSURE_MODULE_LIMIT. Both failing tests then passed.

## P01_P08_RESULTS

P01/P08 default legacy plan and verification pass. P02 optional child, P03 eventual export soft-edge suppression, P04 hard dependency, P05 fixed-point second child, P06 ancestor initializer, P07 CRLF raw hash pass. The new integration file: 9 PASS.

## N01_N12_RESULTS

N01 missing, N02 wrong bytes, N03 stale index digest, N04 invalid AST mode, N05 extra capture, N06 two-pass fingerprint mismatch, N07 selection and package-root differences, N08 domain mismatch, N09 capacity, N10 unknown mode, N11 changed graph/module inventory, N12 no manifest/MODEL_PASS/installed claim all exercised with explicit status/reason assertions in the new test file. No partial cohort is returned.

## TARGETED_PYTEST_RESULTS

New P1B file: 9 PASS. P1A planner, original worker and selected P0 regressions: first run 49 PASS, 2 FAIL (legacy limit reason), 119 deselected. After correction, 9 P1B plus both previously failing legacy tests: 11 PASS. CPython 3.15.2, -B -q -rs -p no:cacheprovider, external --basetemp C:\Temp\Contextor_C16_P1B_pytest_tmp. No full suite.

## CAPTURE_IDENTITY_AND_FINGERPRINTS

Tests use actual index_repository, canonical build_graph and reexport facts, original worker source capture and two-pass verification. Each selected captured raw byte buffer is SHA-256 checked against plan's full indexed fingerprint inventory; CRLF is retained. No independent atomic cross-file capture claim.

## NON_ATOMIC_AUTHORITY_LIMITS

The two passes independently read sources. Equality is non-atomic and does not establish canonical owner provenance or runtime import safety.

## MANIFEST_PUBLICATION_BOUNDARY

No manifest, evidence, model, claims, warning or publication file changed. Existing manifest preparation remains HARD_ONLY because its caller passes no mode. No source-bound MODEL_PASS or LIVE publication was performed.

## POST_CHANGE_MCP_AUDIT

At revision 1000, both changed owner modules and new test module: canonical_state=fresh, workspace_sync=verified, advisory_warning=null. Structural DFS path count 16; cycle_semantics=stale, model_pass_count=0. Indexed source identity is fresh, loaded backend code adoption is unproven. No forced FULL, update_file, backend or Desktop restart.

## FILES_CHANGED

- contextor/core/cycle_semantics/original_worker_binding.py
- contextor/core/cycle_semantics/original_worker_reindex_planning.py
- tests/test_cycle_semantics_optional_child_worker_capture.py

walkthrough.md is the report. Diffs below are against initial task HEAD e3f9e14 so they include task production edits despite the external Auto-commit during execution.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/original_worker_binding.py b/contextor/core/cycle_semantics/original_worker_binding.py
index 8dfedcd..6316007 100644
--- a/contextor/core/cycle_semantics/original_worker_binding.py
+++ b/contextor/core/cycle_semantics/original_worker_binding.py
@@ -13,7 +13,10 @@ from dataclasses import dataclass
 from contextor.core.source import SourceSnapshot
 
 from .scc import analyze_import_cycle_topology
-from .model_source_closure import compute_cycle_model_source_closures
+from .model_source_closure import (
+    compute_cycle_model_source_closures,
+    compute_cycle_model_source_closures_with_optional_children,
+)
 
 
 _CAPTURE_STATUS = "ALL_SELECTED_CAPTURED_NON_ATOMIC"
@@ -24,6 +27,48 @@ _ACCEPTED_MODES = frozenset({
 _MAX_MODULES = 256
 _MAX_SOURCE_BYTES = 2 * 1024 * 1024
 _MAX_TOTAL_BYTES = 32 * 1024 * 1024
+_HARD_ONLY = "HARD_ONLY"
+_OPTIONAL_NAMED_CHILDREN = "OPTIONAL_NAMED_CHILDREN"
+
+
+def _select_original_worker_sources(
+    index: object,
+    hard_edges: Mapping[str, object],
+    source_selection: str,
+) -> tuple[tuple[object, ...], tuple[str, ...], str | None]:
+    """Select indexed SCC sources without reading source bytes or changing graph edges."""
+    if source_selection == _HARD_ONLY:
+        closures = compute_cycle_model_source_closures(hard_edges)
+        package_root = None
+    elif source_selection == _OPTIONAL_NAMED_CHILDREN:
+        if (
+            type(index.modules) is not dict
+            or type(index.source_fingerprints_by_module) is not dict
+            or set(index.modules) != set(hard_edges)
+            or set(index.source_fingerprints_by_module) != set(hard_edges)
+        ):
+            raise ValueError("INDEX_DOMAIN_MISMATCH")
+        from contextor.core.graph.resolver import build_trie, detect_package_root
+
+        imports = {
+            module_id: module.imports
+            for module_id, module in index.modules.items()
+        }
+        trie = build_trie(index.modules)
+        package_root = detect_package_root(index.modules, trie)
+        closures = compute_cycle_model_source_closures_with_optional_children(
+            hard_edges, imports, package_root=package_root,
+        )
+    else:
+        raise ValueError("SOURCE_SELECTION_INVALID")
+    selected = tuple(sorted({
+        module_id
+        for closure in closures
+        for module_id in closure.evidence_source_modules
+    }))
+    if len(selected) > _MAX_MODULES:
+        raise ValueError("CLOSURE_MODULE_LIMIT")
+    return closures, selected, package_root
 
 
 @dataclass(frozen=True)
@@ -40,6 +85,8 @@ class OriginalWorkerCycleClosureBinding:
 def assess_original_worker_cycle_closure(
     index: object,
     hard_edges: Mapping[str, object],
+    *,
+    source_selection: str = _HARD_ONLY,
 ) -> OriginalWorkerCycleClosureBinding:
     """Validate that opted-in original indexer captures cover every SCC closure.
 
@@ -70,6 +117,9 @@ def assess_original_worker_cycle_closure(
             retained_raw_bytes=0,
         )
 
+    if source_selection not in (_HARD_ONLY, _OPTIONAL_NAMED_CHILDREN):
+        return unavailable("SOURCE_SELECTION_INVALID")
+
     topology = analyze_import_cycle_topology(hard_edges)
     if not topology.cyclic_components:
         return unavailable("NO_CYCLIC_COMPONENTS")
@@ -96,14 +146,24 @@ def assess_original_worker_cycle_closure(
         return unavailable("INDEX_CAPTURE_SHAPE_INVALID")
 
     required: set[str] = set()
-    closures = compute_cycle_model_source_closures(hard_edges)
+    try:
+        closures, selected, _ = _select_original_worker_sources(
+            index, hard_edges, source_selection
+        )
+    except (AttributeError, TypeError, ValueError) as exc:
+        if source_selection == _HARD_ONLY and str(exc) == "CLOSURE_MODULE_LIMIT":
+            return unavailable("CLOSURE_MODULE_LIMIT")
+        return unavailable("SOURCE_SELECTION_INVALID:" + str(exc))
     components = tuple(closure.members for closure in closures)
     for closure in closures:
         required.update(closure.evidence_source_modules)
         if len(required) > _MAX_MODULES:
             return unavailable("CLOSURE_MODULE_LIMIT")
 
-    selected = tuple(sorted(required))
+    if source_selection == _OPTIONAL_NAMED_CHILDREN and (
+        set(snapshots) != set(selected) or set(modes) != set(selected)
+    ):
+        return unavailable("CLOSURE_CAPTURE_SET_MISMATCH")
     for module_id in selected:
         if module_id not in index.modules:
             return unavailable("CLOSURE_MODULE_NOT_INDEXED:" + module_id)
diff --git a/contextor/core/cycle_semantics/original_worker_reindex_planning.py b/contextor/core/cycle_semantics/original_worker_reindex_planning.py
index 6b482e0..e422eca 100644
--- a/contextor/core/cycle_semantics/original_worker_reindex_planning.py
+++ b/contextor/core/cycle_semantics/original_worker_reindex_planning.py
@@ -12,13 +12,14 @@ from dataclasses import dataclass
 
 from .contracts import fingerprint_hard_edges
 from .original_worker_binding import (
+    _HARD_ONLY,
+    _OPTIONAL_NAMED_CHILDREN,
+    _select_original_worker_sources,
     assess_original_worker_cycle_closure,
 )
-from .model_source_closure import compute_cycle_model_source_closures
 from .scc import analyze_import_cycle_topology
 
 
-_MAX_SELECTED = 256
 _READY = "READY_FOR_REINDEX_NON_ATOMIC"
 _VERIFIED = "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
 
@@ -31,6 +32,7 @@ class OriginalWorkerReindexPlan:
     graph_sha256: str | None
     fingerprints: tuple[tuple[str, str], ...]
     module_paths: tuple[tuple[str, str, str], ...]
+    source_selection: str = _HARD_ONLY
 
 
 @dataclass(frozen=True)
@@ -43,6 +45,8 @@ class OriginalWorkerReindexVerification:
 def plan_original_worker_reindex(
     index: object,
     hard_edges: Mapping[str, object],
+    *,
+    source_selection: str = _HARD_ONLY,
 ) -> OriginalWorkerReindexPlan:
     """Select SCC closures for a subsequent, separate index pass.
 
@@ -62,8 +66,12 @@ def plan_original_worker_reindex(
             graph_sha256=None,
             fingerprints=(),
             module_paths=(),
+            source_selection=source_selection,
         )
 
+    if source_selection not in (_HARD_ONLY, _OPTIONAL_NAMED_CHILDREN):
+        return unavailable("SOURCE_SELECTION_INVALID")
+
     if (
         type(index.modules) is not dict
         or type(index.source_fingerprints_by_module) is not dict
@@ -97,12 +105,15 @@ def plan_original_worker_reindex(
     if not topology.cyclic_components:
         return unavailable("NO_CYCLIC_COMPONENTS")
 
-    selected: set[str] = set()
-    for closure in compute_cycle_model_source_closures(hard_edges):
-        selected.update(closure.evidence_source_modules)
-
-        if len(selected) > _MAX_SELECTED:
+    try:
+        _, selected_ids, _ = _select_original_worker_sources(
+            index, hard_edges, source_selection
+        )
+    except (AttributeError, TypeError, ValueError) as exc:
+        if source_selection == _HARD_ONLY and str(exc) == "CLOSURE_MODULE_LIMIT":
             return unavailable("CLOSURE_MODULE_LIMIT")
+        return unavailable("SOURCE_SELECTION_INVALID:" + str(exc))
+    selected = set(selected_ids)
 
     if any(module_id not in indexed_ids for module_id in selected):
         return unavailable("CLOSURE_MODULE_NOT_INDEXED")
@@ -137,6 +148,7 @@ def plan_original_worker_reindex(
         graph_sha256=graph_sha256,
         fingerprints=tuple(sorted(fingerprints.items())),
         module_paths=module_paths,
+        source_selection=source_selection,
     )
 
 
@@ -172,6 +184,9 @@ def verify_original_worker_reindex(
     if plan.status != _READY:
         return unavailable("REINDEX_PLAN_UNAVAILABLE")
 
+    if plan.source_selection not in (_HARD_ONLY, _OPTIONAL_NAMED_CHILDREN):
+        return unavailable("SOURCE_SELECTION_INVALID")
+
     if not plan.selected_module_ids:
         return unavailable("REINDEX_PLAN_EMPTY")
 
@@ -230,6 +245,22 @@ def verify_original_worker_reindex(
     if captured_fingerprints != plan.fingerprints:
         return unavailable("REINDEX_SOURCE_CHANGED")
 
+    if plan.source_selection == _OPTIONAL_NAMED_CHILDREN:
+        try:
+            _, discovery_selected, discovery_root = _select_original_worker_sources(
+                discovery_index, discovery_hard_edges, plan.source_selection
+            )
+            _, captured_selected, captured_root = _select_original_worker_sources(
+                captured_index, captured_hard_edges, plan.source_selection
+            )
+        except (AttributeError, TypeError, ValueError) as exc:
+            return unavailable("REINDEX_SELECTION_INVALID:" + str(exc))
+        if discovery_root != captured_root:
+            return unavailable("REINDEX_PACKAGE_ROOT_CHANGED")
+        if (frozenset(discovery_selected) != plan.selected_module_ids
+                or frozenset(captured_selected) != plan.selected_module_ids):
+            return unavailable("REINDEX_CLOSURE_CHANGED")
+
     if discovery_index.skipped != captured_index.skipped:
         return unavailable("REINDEX_SKIPPED_FILES_CHANGED")
 
@@ -249,6 +280,7 @@ def verify_original_worker_reindex(
     binding = assess_original_worker_cycle_closure(
         captured_index,
         captured_hard_edges,
+        source_selection=plan.source_selection,
     )
 
     if binding.status != (
diff --git a/tests/test_cycle_semantics_optional_child_worker_capture.py b/tests/test_cycle_semantics_optional_child_worker_capture.py
new file mode 100644
index 0000000..eda9ec4
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_child_worker_capture.py
@@ -0,0 +1,235 @@
+"""P1B optional named-child original worker byte capture, without publication."""
+
+from __future__ import annotations
+
+import hashlib
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.cycle_semantics.original_worker_binding import (
+    assess_original_worker_cycle_closure,
+)
+from contextor.core.cycle_semantics.original_worker_reindex_planning import (
+    plan_original_worker_reindex,
+    verify_original_worker_reindex,
+)
+from contextor.core.domain.imports import ImportRef
+from contextor.core.graph.graph import build_graph
+from contextor.core.graph.resolver import build_trie, detect_package_root
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
+from contextor.core.source import SourceSnapshot
+from contextor.core.symbol_engine.indexer import index_repository
+from tests.cycle_semantics_lab import write_synthetic_repository
+
+
+@pytest.fixture(autouse=True)
+def _inline(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+FILES = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": "import pkg.b\nfrom pkg import child\n",
+    "pkg/b.py": "import pkg.a\n",
+    "pkg/child.py": "import pkg.helper\n",
+    "pkg/helper.py": "pass\n",
+}
+
+
+def _pass(root, *, selected=None):
+    index = index_repository(
+        str(root), source_capture_module_ids=selected
+    )
+    facts = materialize_reexport_facts_by_module(
+        index.modules, index.reference_facts_by_module
+    )
+    trie = build_trie(index.modules)
+    graph = build_graph(
+        index.modules, trie=trie,
+        package_root=detect_package_root(index.modules, trie),
+        reexport_facts_by_module=facts,
+    )
+    return index, graph
+
+
+def _case(tmp_path, files=FILES, mode="OPTIONAL_NAMED_CHILDREN"):
+    root = tmp_path / "repo"
+    write_synthetic_repository(root, files)
+    first, graph = _pass(root)
+    plan = plan_original_worker_reindex(
+        first, graph.hard_edges, source_selection=mode
+    )
+    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
+    second, second_graph = _pass(root, selected=plan.selected_module_ids)
+    return root, first, graph, plan, second, second_graph
+
+
+def _verify(case):
+    _, first, graph, plan, second, second_graph = case
+    return verify_original_worker_reindex(
+        plan, first, graph.hard_edges, second, second_graph.hard_edges
+    )
+
+
+def test_p01_p08_legacy_hard_only_parity(tmp_path):
+    case = _case(tmp_path, mode="HARD_ONLY")
+    _, first, graph, plan, second, _ = case
+    assert plan.source_selection == "HARD_ONLY"
+    assert "pkg.child" not in plan.selected_module_ids
+    assert plan == plan_original_worker_reindex(first, graph.hard_edges)
+    assert assess_original_worker_cycle_closure(
+        second, graph.hard_edges
+    ).status == "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
+    assert _verify(case).status == "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
+
+
+def test_p02_p04_optional_child_hard_dependency_and_raw_bytes(tmp_path):
+    case = _case(tmp_path)
+    root, _, graph, plan, second, _ = case
+    assert {"pkg.child", "pkg.helper", "pkg.__init__"} <= plan.selected_module_ids
+    assert "pkg.child" not in graph.hard_edges["pkg.a"]
+    assert set(second.original_worker_source_snapshots) == plan.selected_module_ids
+    binding = assess_original_worker_cycle_closure(
+        second, graph.hard_edges, source_selection=plan.source_selection
+    )
+    assert binding.status == "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
+    for module_id in plan.selected_module_ids:
+        raw = binding.source_snapshots[module_id].raw
+        assert hashlib.sha256(raw).hexdigest() == dict(plan.fingerprints)[module_id]
+    assert _verify(case).source_modules == binding.reachable_modules
+
+
+def test_p03_eventual_reexport_shadow(tmp_path):
+    files = {**FILES, "pkg/__init__.py": "child = 1\n"}
+    case = _case(tmp_path, files)
+    _, _, graph, plan, _, _ = case
+    assert "pkg.child" not in graph.soft_edges["pkg.a"]
+    assert "pkg.child" in plan.selected_module_ids
+    assert _verify(case).status == "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
+
+
+def test_p05_p06_fixed_point_and_ancestors(tmp_path):
+    files = {**FILES, "pkg/child.py": "from pkg.nested import next_child\n",
+             "pkg/nested/__init__.py": "pass\n",
+             "pkg/nested/next_child.py": "pass\n"}
+    case = _case(tmp_path, files)
+    plan = case[3]
+    assert {"pkg.child", "pkg.nested.__init__", "pkg.nested.next_child"} <= plan.selected_module_ids
+    assert _verify(case).status == "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
+
+
+def test_p07_crlf_raw_fingerprint(tmp_path):
+    case = _case(tmp_path, {**FILES, "pkg/child.py": "import pkg.helper\r\n"})
+    root, _, _, plan, second, _ = case
+    raw = second.original_worker_source_snapshots["pkg.child"].raw
+    assert b"\r\n" in raw
+    assert raw == (root / "pkg" / "child.py").read_bytes()
+    assert hashlib.sha256(raw).hexdigest() == dict(plan.fingerprints)["pkg.child"]
+    assert _verify(case).status == "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
+
+
+def test_n01_n02_n03_n04_n05_capture_guards(tmp_path):
+    case = _case(tmp_path)
+    _, first, graph, plan, second, second_graph = case
+    snapshots = dict(second.original_worker_source_snapshots)
+    snapshots.pop("pkg.child")
+    missing = replace(second, original_worker_source_snapshots=snapshots)
+    assert assess_original_worker_cycle_closure(
+        missing, graph.hard_edges, source_selection=plan.source_selection
+    ).reason == "INDEX_CAPTURE_SHAPE_INVALID"
+    assert _verify((None, first, graph, plan, missing, second_graph)).reason == "REINDEX_SELECTION_MISMATCH"
+
+    snapshots = dict(second.original_worker_source_snapshots)
+    old = snapshots["pkg.child"]
+    snapshots["pkg.child"] = SourceSnapshot(b"forged", old.source_fingerprint)
+    wrong = replace(second, original_worker_source_snapshots=snapshots)
+    assert assess_original_worker_cycle_closure(
+        wrong, graph.hard_edges, source_selection=plan.source_selection
+    ).reason == "CLOSURE_SOURCE_DIGEST_MISMATCH:pkg.child"
+
+    fingerprints = dict(second.source_fingerprints_by_module)
+    fingerprints["pkg.child"] = "0" * 64
+    stale = replace(second, source_fingerprints_by_module=fingerprints)
+    assert assess_original_worker_cycle_closure(
+        stale, graph.hard_edges, source_selection=plan.source_selection
+    ).reason == "CLOSURE_SOURCE_DIGEST_MISMATCH:pkg.child"
+    assert _verify((None, first, graph, plan, stale, second_graph)).reason == "REINDEX_SOURCE_CHANGED"
+
+    modes = dict(second.original_worker_ast_modes)
+    modes["pkg.child"] = "INVALID"
+    invalid_mode = replace(second, original_worker_ast_modes=modes)
+    assert assess_original_worker_cycle_closure(
+        invalid_mode, graph.hard_edges, source_selection=plan.source_selection
+    ).reason == "CLOSURE_AST_MODE_INVALID:pkg.child"
+
+    snapshots = dict(second.original_worker_source_snapshots)
+    snapshots["outside"] = old
+    modes = dict(second.original_worker_ast_modes)
+    modes["outside"] = "PARSED_FROM_WORKER_READ"
+    extra = replace(second, original_worker_source_snapshots=snapshots,
+                    original_worker_ast_modes=modes)
+    assert assess_original_worker_cycle_closure(
+        extra, graph.hard_edges, source_selection=plan.source_selection
+    ).reason == "CLOSURE_CAPTURE_SET_MISMATCH"
+    assert _verify((None, first, graph, plan, extra, second_graph)).reason == "REINDEX_SELECTION_MISMATCH"
+
+
+def test_n07_n08_n09_n10_n11_selection_and_inventory_guards(tmp_path):
+    case = _case(tmp_path)
+    _, first, graph, plan, second, second_graph = case
+    altered = replace(second, modules={**second.modules, "ghost": second.modules["pkg.a"]})
+    assert _verify((None, first, graph, plan, altered, second_graph)).reason == "REINDEX_MODULE_INVENTORY_CHANGED"
+    bad_mode = replace(plan, source_selection="INVALID")
+    assert _verify((None, first, graph, bad_mode, second, second_graph)).reason == "SOURCE_SELECTION_INVALID"
+    assert plan_original_worker_reindex(first, graph.hard_edges,
+        source_selection="INVALID").reason == "SOURCE_SELECTION_INVALID"
+    malformed = replace(first, modules={**first.modules, "ghost": first.modules["pkg.a"]})
+    assert plan_original_worker_reindex(malformed, graph.hard_edges,
+        source_selection="OPTIONAL_NAMED_CHILDREN").reason == "GRAPH_INDEX_DOMAIN_MISMATCH"
+    hard = {name: set(targets) for name, targets in graph.hard_edges.items()}
+    hard["pkg.a"].update(f"pkg.extra{i}" for i in range(257))
+    for i in range(257):
+        hard[f"pkg.extra{i}"] = set()
+    synthetic = replace(first, modules={**first.modules, **{
+        f"pkg.extra{i}": first.modules["pkg.a"] for i in range(257)
+    }}, source_fingerprints_by_module={**first.source_fingerprints_by_module,
+        **{f"pkg.extra{i}": "0" * 64 for i in range(257)}})
+    assert plan_original_worker_reindex(synthetic, hard,
+        source_selection="OPTIONAL_NAMED_CHILDREN").reason == (
+            "SOURCE_SELECTION_INVALID:Selected source capacity exceeded"
+        )
+    changed_graph = {name: set(targets) for name, targets in second_graph.hard_edges.items()}
+    changed_graph["pkg.a"].add("pkg.helper")
+    assert _verify((None, first, graph, plan, second, replace(second_graph,
+        hard_edges=changed_graph))).reason == "REINDEX_GRAPH_CHANGED"
+
+
+def test_n07_changed_import_facts_and_package_root(tmp_path):
+    case = _case(tmp_path)
+    _, first, graph, plan, second, second_graph = case
+    module = second.modules["pkg.a"]
+    altered = replace(second, modules={**second.modules, "pkg.a": replace(
+        module, imports=[ImportRef(module="pkg.b", level=0, names=[], is_from_import=False)]
+    )})
+    assert _verify((None, first, graph, plan, altered, second_graph)).reason == (
+        "REINDEX_CLOSURE_CHANGED"
+    )
+    root_changed = replace(second, modules={**second.modules, "pkg.a": replace(
+        module, imports=[
+            ImportRef(module="pkg.b", level=0, names=[], is_from_import=False),
+            ImportRef(module="outer.pkg", level=0, names=["child"], is_from_import=True),
+            ImportRef(module="outer.pkg.child", level=0, names=[], is_from_import=False),
+        ]
+    )})
+    assert _verify((None, first, graph, plan, root_changed, second_graph)).reason == (
+        "REINDEX_PACKAGE_ROOT_CHANGED"
+    )
+
+
+def test_n12_verified_capture_has_no_publication_claim(tmp_path):
+    result = _verify(_case(tmp_path))
+    assert result.status == "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
+    assert not hasattr(result, "prepared_manifest")
+    assert not hasattr(result, "model_pass")
+    assert not hasattr(result, "installed_claim")
```

## FINAL_VERDICT

C16_B03_P1B_PASS

This certifies opt-in worker capture and two-pass byte verification only; full B03 source-bound model and publication integration remains outside P1B.

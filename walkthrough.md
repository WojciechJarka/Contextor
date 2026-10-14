# CONTEXTOR_B0G4B5_STRUCTURAL_SCC_KERNEL

## HEAD_BEFORE
cf9379143672497f48cb8dee6cdadb863b438585. Git status clean. B0G4B4 initialization_model.py existed; both B0G4B5 target paths were absent. Contextor identified `contextor.core.graph.cycles::detect_cycles` as existing structural cycle owner with 12 consumers; no edit to that owner was planned.

## HEAD_AFTER
cf9379143672497f48cb8dee6cdadb863b438585. No commit. Git status shows only the two new task files as untracked.

## LIVE_REVISION_BEFORE
412; activity_epoch=1beab26da2ff4932852caa7db6ff4242; continuity=continuous; resync_required=false; canonical_state=fresh; collisions=0 fresh; cycles=16 fresh. Global workspace_sync=unverified. Contextor found initialization_model isolated with only its targeted test as a direct consumer and no downstream consumers.

## LIVE_REVISION_AFTER
414; same activity_epoch; continuity=continuous; resync_required=false; canonical_state=fresh; all reported families fresh; no parse-stale modules; collisions=0; cycles=16. Desktop watcher revision 413 UPDATED scc.py and revision 414 UPDATED test_cycle_semantics_scc.py, both blast_radius_state=fresh. New production module workspace_sync=verified by full get_file_edit_context at revision 414; project overlay remains unverified.

## FILES_CHANGED
- contextor/core/cycle_semantics/scc.py (new)
- tests/test_cycle_semantics_scc.py (new)

No existing production/test file or __init__.py changed. walkthrough.md is this report and excluded from source/test diff accounting.

## IMPLEMENTATION_CONTRACT
CONTRACT_PROVED: Both files exactly match the auditor-supplied content with one final newline. The kernel validates and normalizes an explicit hard-edge mapping, adds target-only nodes, orders nodes and adjacency deterministically, performs iterative two-pass SCC traversal, and retains all members and internal hard edges for cyclic components. A self-loop yields a one-node cyclic component; overlapping simple cycle paths remain one SCC. Output dataclasses are frozen. The input graph is not mutated.
CODE_PATH_PROVED: The kernel receives an in-memory mapping and returns structural evidence. It does not read source, enumerate all simple cycles, invoke existing detect_cycles, change ProjectGraph/hard_edges/soft_edges, or publish warnings. Contextor reports the new module's only direct consumer as tests.test_cycle_semantics_scc, with zero downstream consumers.

## TEST_COMMAND
Pre-edit: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py`
Post-edit: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py`

## TEST_RESULTS
Repository Python 3.10.9. Pre-edit exit 0: 77 passed in 2.33s. Post-edit exit 0: 92 passed in 3.10s (15 new plus 77 existing). No other tests, full suite, or FULL analysis run. New production syntax diagnostics are fresh and empty at revision 414.

## SCC_STRUCTURAL_EVIDENCE
CONTRACT_PROVED: Targeted tests cover empty and target-only graphs, acyclic chains, overlapping cycles, independent SCCs, self-loop, deterministic order and edge deduplication, 4101-node cyclic and 3001-node acyclic chains without recursion, invalid graphs, input immutability, and randomized comparison with the mutual-reachability definition. The result counts SCCs, not simple cycle paths; exact internal edges are retained. SCC membership is structural graph evidence only.

## COLLISION_COUNT_BEFORE_AFTER
0 -> 0 from fresh canonical get_name_collisions at revisions 412 and 414. No new name collision.

## STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER
16 -> 16 from fresh canonical diagnostics. Existing detect_cycles and structural graph code were not edited. Watcher indexing of two new modules may add ordinary dependency edges; a byte-identical whole-repository graph is not claimed.

## NO_SAFETY_CERTIFICATION
CODE_PATH_PROVED: The output scope is STRUCTURAL_HARD_IMPORT_GRAPH. It emits no SAFE, runtime reachability, or failure classification. SCC membership is not treated as import-execution evidence.

## NO_WARNING_SUPPRESSION
CODE_PATH_PROVED: ArchitectureCycle and warning-publication code were untouched. Fresh canonical cycle count remains 16; no suppression rule was added.

## NO_DIRECT_LIVE_PUBLICATION
CODE_PATH_PROVED: The new module is imported only by its targeted test, not exported from __init__.py, and not integrated with FULL/incremental, MCP, LIVE, Desktop or snapshots. Watcher indexing is external observation. No direct update_file, restart or commit.

## FINAL_VERDICT
B0G4B5_PASS — exact isolated two-file SCC kernel, 92 focused tests passed, both watcher events observed, fresh canonical state, zero name collisions and unchanged structural cycle count. Await `proceduj`.

## FULL_DIFFS

### FULL_DIFF: contextor/core/cycle_semantics/scc.py

diff --git a/contextor/core/cycle_semantics/scc.py b/contextor/core/cycle_semantics/scc.py
new file mode 100644
index 0000000..e9daf4d
--- /dev/null
+++ b/contextor/core/cycle_semantics/scc.py
@@ -0,0 +1,131 @@
+"""Deterministic, iterative SCC evidence from an unchanged hard-import graph.
+
+Structural membership is not import-execution evidence or a safety verdict.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+
+@dataclass(frozen=True)
+class CyclicImportComponent:
+    members: tuple[str, ...]
+    internal_edges: tuple[tuple[str, str], ...]
+    kind: str
+
+
+@dataclass(frozen=True)
+class ImportCycleTopology:
+    node_count: int
+    hard_edge_count: int
+    total_scc_count: int
+    cyclic_components: tuple[CyclicImportComponent, ...]
+    evidence_scope: str = "STRUCTURAL_HARD_IMPORT_GRAPH"
+
+
+def analyze_import_cycle_topology(
+    hard_edges: Mapping[
+        str,
+        set[str] | frozenset[str] | list[str] | tuple[str, ...],
+    ],
+) -> ImportCycleTopology:
+    """Find all cyclic SCCs without mutating input or enumerating simple cycles.
+
+    A self-loop is cyclic, and multiple cycle paths inside an SCC still count
+    as one cyclic component. Edges to target-only nodes remain represented.
+    """
+    if not isinstance(hard_edges, Mapping):
+        raise TypeError("hard_edges must be a mapping")
+
+    adjacency_sets: dict[str, set[str]] = {}
+    for source, targets in hard_edges.items():
+        if not isinstance(source, str) or not source:
+            raise ValueError("invalid source module")
+        if not isinstance(targets, (set, frozenset, tuple, list)):
+            raise TypeError("targets must be an explicit collection")
+        normalized: set[str] = set()
+        for target in targets:
+            if not isinstance(target, str) or not target:
+                raise ValueError("invalid target module")
+            normalized.add(target)
+        adjacency_sets[source] = normalized
+
+    for targets in tuple(adjacency_sets.values()):
+        for target in targets:
+            adjacency_sets.setdefault(target, set())
+
+    adjacency = {
+        node: tuple(sorted(targets))
+        for node, targets in sorted(adjacency_sets.items())
+    }
+    predecessors: dict[str, list[str]] = {node: [] for node in adjacency}
+    for source, targets in adjacency.items():
+        for target in targets:
+            predecessors[target].append(source)
+    reverse = {node: tuple(sorted(pred)) for node, pred in predecessors.items()}
+
+    visited: set[str] = set()
+    finish_order: list[str] = []
+    for source in adjacency:
+        if source in visited:
+            continue
+        visited.add(source)
+        stack: list[tuple[str, int]] = [(source, 0)]
+        while stack:
+            node, index = stack[-1]
+            successors = adjacency[node]
+            if index == len(successors):
+                finish_order.append(node)
+                stack.pop()
+                continue
+            stack[-1] = (node, index + 1)
+            next_node = successors[index]
+            if next_node not in visited:
+                visited.add(next_node)
+                stack.append((next_node, 0))
+
+    visited.clear()
+    cyclic: list[CyclicImportComponent] = []
+    all_scc_count = 0
+    for source in reversed(finish_order):
+        if source in visited:
+            continue
+        all_scc_count += 1
+        members: list[str] = []
+        stack = [source]
+        visited.add(source)
+        while stack:
+            node = stack.pop()
+            members.append(node)
+            for predecessor in reverse[node]:
+                if predecessor not in visited:
+                    visited.add(predecessor)
+                    stack.append(predecessor)
+
+        ordered_members = tuple(sorted(members))
+        if len(ordered_members) == 1:
+            only = ordered_members[0]
+            if only not in adjacency[only]:
+                continue
+
+        member_set = set(ordered_members)
+        internal_edges = tuple(
+            (node, target)
+            for node in ordered_members
+            for target in adjacency[node]
+            if target in member_set
+        )
+        cyclic.append(CyclicImportComponent(
+            members=ordered_members,
+            internal_edges=internal_edges,
+            kind="SELF_LOOP" if len(ordered_members) == 1 else "MULTI_MODULE",
+        ))
+
+    return ImportCycleTopology(
+        node_count=len(adjacency),
+        hard_edge_count=sum(len(targets) for targets in adjacency.values()),
+        total_scc_count=all_scc_count,
+        cyclic_components=tuple(sorted(cyclic, key=lambda item: item.members)),
+    )

### FULL_DIFF: tests/test_cycle_semantics_scc.py

diff --git a/tests/test_cycle_semantics_scc.py b/tests/test_cycle_semantics_scc.py
new file mode 100644
index 0000000..ec3041c
--- /dev/null
+++ b/tests/test_cycle_semantics_scc.py
@@ -0,0 +1,150 @@
+import json
+import random
+from dataclasses import asdict
+
+import pytest
+
+from contextor.core.cycle_semantics.scc import (
+    analyze_import_cycle_topology as analyze,
+)
+
+
+def test_b0g4b5_acyclic_target_only_and_empty():
+    assert analyze({}).node_count == 0
+    out = analyze({"a": {"b"}, "b": {"c"}})
+    assert (
+        out.node_count,
+        out.hard_edge_count,
+        out.total_scc_count,
+        out.cyclic_components,
+    ) == (3, 2, 3, ())
+
+
+def test_b0g4b5_overlapping_cycles_one_scc():
+    out = analyze({
+        "a": {"b", "c", "x"},
+        "b": {"c"},
+        "c": {"a"},
+        "x": set(),
+    })
+    assert out.total_scc_count == 2
+    assert len(out.cyclic_components) == 1
+    assert out.cyclic_components[0].members == ("a", "b", "c")
+    assert out.cyclic_components[0].internal_edges == (
+        ("a", "b"),
+        ("a", "c"),
+        ("b", "c"),
+        ("c", "a"),
+    )
+
+
+def test_b0g4b5_independent_sccs_and_self_loop():
+    out = analyze({
+        "a": {"b"}, "b": {"a"},
+        "c": {"c"},
+        "d": {"e"}, "e": {"d"},
+        "f": set(),
+    })
+    assert tuple(c.members for c in out.cyclic_components) == (
+        ("a", "b"), ("c",), ("d", "e")
+    )
+    assert tuple(c.kind for c in out.cyclic_components) == (
+        "MULTI_MODULE", "SELF_LOOP", "MULTI_MODULE"
+    )
+    assert out.total_scc_count == 4
+
+
+def test_b0g4b5_order_independent_and_deduplicated():
+    first = analyze({"b": ["a", "a"], "a": ("b", "c"), "c": ()})
+    second = analyze({"c": set(), "a": {"c", "b"}, "b": {"a"}})
+    assert first == second
+    assert first.hard_edge_count == 3
+    json.dumps(asdict(first))
+
+
+def test_b0g4b5_deep_cycle_no_recursion():
+    n = 4100
+    graph = {f"m{i}": {f"m{i+1}"} for i in range(n)}
+    graph[f"m{n}"] = {"m0"}
+    out = analyze(graph)
+    assert (
+        out.node_count,
+        out.hard_edge_count,
+        out.total_scc_count,
+    ) == (n + 1, n + 1, 1)
+    assert len(out.cyclic_components[0].members) == n + 1
+
+
+def test_b0g4b5_deep_acyclic_chain_no_recursion():
+    n = 3000
+    out = analyze({
+        f"m{i}": {f"m{i+1}"} for i in range(n)
+    })
+    assert (
+        out.node_count,
+        out.total_scc_count,
+        len(out.cyclic_components),
+    ) == (n + 1, n + 1, 0)
+
+
+@pytest.mark.parametrize("graph, error", [
+    (None, TypeError),
+    ([("a", {"b"})], TypeError),
+    ({"a": "b"}, TypeError),
+    ({"a": None}, TypeError),
+    ({"": set()}, ValueError),
+    ({1: {"a"}}, ValueError),
+    ({"a": {None}}, ValueError),
+])
+def test_b0g4b5_rejects_invalid_graph(graph, error):
+    with pytest.raises(error):
+        analyze(graph)
+
+
+def test_b0g4b5_no_graph_mutation():
+    graph = {"a": {"b"}, "b": {"a"}}
+    before = {k: set(v) for k, v in graph.items()}
+    out = analyze(graph)
+    assert graph == before
+    with pytest.raises(Exception):
+        out.cyclic_components[0].members = ("fake",)
+
+
+def test_b0g4b5_random_graphs_against_reachability_definition():
+    rng = random.Random(710)
+    for n in range(2, 7):
+        nodes = [f"x{i}" for i in range(n)]
+        for _ in range(12):
+            graph = {
+                u: {v for v in nodes if rng.randrange(4) == 0}
+                for u in nodes
+            }
+            out = analyze(graph)
+
+            reach = {}
+            for u in nodes:
+                found = {u}
+                stack = [u]
+                while stack:
+                    for v in graph[stack.pop()]:
+                        if v not in found:
+                            found.add(v)
+                            stack.append(v)
+                reach[u] = found
+
+            unused = set(nodes)
+            expected = []
+            while unused:
+                u = min(unused)
+                group = {
+                    v for v in nodes
+                    if v in reach[u] and u in reach[v]
+                }
+                unused -= group
+                if len(group) > 1 or u in graph[u]:
+                    expected.append(tuple(sorted(group)))
+
+            assert tuple(
+                component.members
+                for component in out.cyclic_components
+            ) == tuple(sorted(expected))

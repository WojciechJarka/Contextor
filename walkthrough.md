# CONTEXTOR_P1D2E_BOUNDED_REINDEX_CAPTURE_PLANNING

## PREFLIGHT_RESULT

- DIRECT_EVIDENCE: Repository HEAD was `5b6fda10c1e042a660f8134940c256bb9b9b08eb`; initial `git status --short --branch` was `## main...origin/main` with no worktree entries.
- DIRECT_EVIDENCE: Both authorized targets were absent before editing. Existing `contextor/core/cycle_semantics/original_worker_binding.py` was present.
- CONTRACT_PROVED: Read current MCP documentation for `get_symbol_implementation` and `get_live_events`. The initial Contextor read resolved `assess_original_worker_cycle_closure` completely at canonical revision 678 with `workspace_sync=verified`.
- CODE_PATH_PROVED: The existing binding accepts caller-supplied `RepositoryIndex` and hard-edge mapping; validates complete selected source snapshots, SHA-256 equality, accepted AST modes and reachable cyclic closures; returns `SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC` on success. It states that it does not read files, run workers, assert canonical freshness, publish, or perform LIVE I/O.

## NATIVE_CODEX_EDITS

- DIRECT_EVIDENCE: Created the two authorized production/test files using the native Codex `apply_patch` editor with the supplied literal content. No generation script, external patch utility, or adaptation was used.
- DIRECT_EVIDENCE: No existing source, test, or docs file was edited. `walkthrough.md` was overwritten only as the required stage report.

## FILES_CHANGED

- Production: `contextor/core/cycle_semantics/original_worker_reindex_planning.py` (new; 287 added lines).
- Test: `tests/test_original_worker_reindex_planning.py` (new; 312 added lines).
- Report: `walkthrough.md` (stage report; its own diff is excluded by the reporting instruction).

## ACTUAL_SOURCE_AND_TEST_CHANGES

- CODE_PATH_PROVED: The new planner validates index and fingerprint domains, graph validity, cyclic topology, a maximum selected closure of 16 modules, module inventory/path shape, and records the discovery graph hash and fingerprints. It performs no filesystem reads or indexing.
- CODE_PATH_PROVED: The verifier compares discovery and second-pass graph hashes, fingerprints, paths/inventory and skipped files; requires complete second-pass captures and AST modes; then delegates selected SCC closure validation to the existing binding.
- DIRECT_EVIDENCE: The tests exercise real inline and process-pool two-pass indexing, warm-cache capture, prepared-only manifest handoff, acyclic/oversized closure rejection, source and graph drift, missing capture selection, inventory drift, graph/index domain mismatch, and no additional disk reads during planning/verification.
- CONTRACT_PROVED: The first pass has `original_worker_capture_status == "NOT_REQUESTED"` in the successful two-pass test. The second pass is independently requested with the selected IDs and supplies the snapshots verified by the new verifier.

## PY_COMPILE_RESULT

- DIRECT_EVIDENCE: The requested `py_compile` command exited 0 for both new files.

## P1D2E_TEST_RESULTS

- DIRECT_EVIDENCE: `pytest -q tests/test_original_worker_reindex_planning.py` — **11 passed in 5.69s**.

## FOCUSED_REGRESSION_RESULTS

- DIRECT_EVIDENCE: The exact requested focused regression command, containing the new test and nine existing P1D2/P1D/P1C/indexer tests, exited 0 — **192 passed in 33.09s**.

## SECOND_PASS_PROVENANCE

- CODE_PATH_PROVED: `_two_pass` first calls `index_repository` without capture IDs, derives the plan from that index and graph, and then separately calls `index_repository(..., source_capture_module_ids=plan.selected_module_ids)`. The verifier consumes the second `RepositoryIndex` and its graph.
- CONTRACT_PROVED: Matching fingerprints and inventories establish declared cross-pass consistency for selected bytes; the supplied module documentation explicitly says this is non-atomic and does not authenticate a canonical generation or establish repository-wide atomicity.
- INFERENCE: Passing T01/T02/T09 demonstrates the specified behavior under the tested fixtures and inline/process-pool paths; it does not establish a universal filesystem snapshot guarantee.

## DRIFT_AND_FAIL_CLOSED_RESULTS

- DIRECT_EVIDENCE: T03/T04/T10 verify fail-closed outcomes for no cyclic component, closure above 16 modules, and graph/index domain mismatch.
- DIRECT_EVIDENCE: T05/T06/T07/T08 verify fail-closed outcomes for changed source fingerprints, changed graph, missing selected capture and changed module inventory.
- DIRECT_EVIDENCE: All 11 focused tests and all 192 requested regression tests passed.
- UNKNOWN: This stage does not certify behavior for untested filesystem races, adversarial caller-supplied objects beyond the asserted validation, or source-tree-wide atomicity.

## CANONICAL_WATCHER_OBSERVATIONS

- DIRECT_EVIDENCE: `get_live_events(repo_path=..., after_revision=678)` returned continuous revisions 679 and 680, both `origin=desktop_watcher`, `operation=update_file`, `status=UPDATED`, `resync_required=false`. Revision 679 names the new production file; revision 680 names the new test file.
- DIRECT_EVIDENCE: A subsequent `get_symbol_implementation` read resolved `plan_original_worker_reindex` at canonical revision 680 with `canonical_state=fresh`, `workspace_sync=verified`, and `provenance=live`.
- DIRECT_EVIDENCE: At revision 680, `cycle_semantics` remained stale; module, graph, topology, artifact-consumption, cycles, collisions and lineage families were fresh. No FULL analysis was run.
- INFERENCE: These observations establish watcher ingestion/canonical source visibility for the new file. They do not establish that any running application process imported or adopted it.

## PUBLICATION_AND_RUNTIME_AUTHORITY_LIMITS

- CONTRACT_PROVED: This stage adds a planning/verification contract and a test that may prepare an unpublished manifest. It does not connect the new helper to production FULL, store, IPC, snapshot publication, receipts or LIVE authority.
- DIRECT_EVIDENCE: No FULL, publication, receipt operation, restart, reload, LIVE mutation, or `verify_installed_cycle_generation` operation was run.
- UNKNOWN: Active runtime loaded-code identity and adoption remain unverified. No static or watcher evidence is treated as runtime adoption.
- CONTRACT_PROVED: The successful path retains the explicit `NON_ATOMIC` and `PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED` authority labels. No import execution safety or SAFE certification is claimed.

## FINAL_VERDICT

- DIRECT_EVIDENCE: P1D2E implementation and its specified focused verification completed successfully; exact requested files were added, both compile, 11 new tests pass, and the full requested focused regression set passes (192 tests).
- INFERENCE: The tests provide evidence for bounded second-pass capture planning and cross-pass drift rejection under their controlled fixtures only.
- UNKNOWN: Canonical generation authenticity, receipt publication, production FULL integration, active LIVE loaded-code adoption and cross-file source atomicity remain outside this stage.
- STOP: P1D2E only. Await the architect's next explicit `proceduj`.

## ACTUAL_DIFF

### `contextor/core/cycle_semantics/original_worker_reindex_planning.py`

```diff
diff --git a/contextor/core/cycle_semantics/original_worker_reindex_planning.py b/contextor/core/cycle_semantics/original_worker_reindex_planning.py
new file mode 100644
index 0000000..ecdb6e2
--- /dev/null
+++ b/contextor/core/cycle_semantics/original_worker_reindex_planning.py
@@ -0,0 +1,287 @@
+"""Plan and verify bounded second-pass original indexer source capture.
+
+The second index pass has its own worker reads. Equality with a
+first-pass inventory does not make the repository cross-file atomic,
+authenticate a canonical generation, or authorize publication.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from .contracts import fingerprint_hard_edges
+from .original_worker_binding import (
+    assess_original_worker_cycle_closure,
+)
+from .scc import analyze_import_cycle_topology
+
+
+_MAX_SELECTED = 16
+_READY = "READY_FOR_REINDEX_NON_ATOMIC"
+_VERIFIED = "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
+
+
+@dataclass(frozen=True)
+class OriginalWorkerReindexPlan:
+    status: str
+    reason: str | None
+    selected_module_ids: frozenset[str]
+    graph_sha256: str | None
+    fingerprints: tuple[tuple[str, str], ...]
+    module_paths: tuple[tuple[str, str, str], ...]
+
+
+@dataclass(frozen=True)
+class OriginalWorkerReindexVerification:
+    status: str
+    reason: str | None
+    source_modules: tuple[str, ...]
+
+
+def plan_original_worker_reindex(
+    index: object,
+    hard_edges: Mapping[str, object],
+) -> OriginalWorkerReindexPlan:
+    """Select SCC closures for a subsequent, separate index pass.
+
+    Inputs are caller-supplied. This function performs no filesystem
+    access, source reading, indexing, IPC or publication.
+    """
+    from contextor.core.symbol_engine.indexer import RepositoryIndex
+
+    if type(index) is not RepositoryIndex:
+        raise TypeError("index must be RepositoryIndex")
+
+    def unavailable(reason: str) -> OriginalWorkerReindexPlan:
+        return OriginalWorkerReindexPlan(
+            status="UNAVAILABLE",
+            reason=reason,
+            selected_module_ids=frozenset(),
+            graph_sha256=None,
+            fingerprints=(),
+            module_paths=(),
+        )
+
+    if (
+        type(index.modules) is not dict
+        or type(index.source_fingerprints_by_module) is not dict
+    ):
+        return unavailable("INDEX_SHAPE_INVALID")
+
+    try:
+        topology = analyze_import_cycle_topology(hard_edges)
+        graph_sha256 = fingerprint_hard_edges(hard_edges)
+    except (TypeError, ValueError):
+        return unavailable("GRAPH_INVALID")
+
+    indexed_ids = set(index.modules)
+
+    if set(hard_edges) != indexed_ids:
+        return unavailable("GRAPH_INDEX_DOMAIN_MISMATCH")
+
+    if set(index.source_fingerprints_by_module) != indexed_ids:
+        return unavailable("INDEX_FINGERPRINT_DOMAIN_MISMATCH")
+
+    fingerprints = index.source_fingerprints_by_module
+
+    if any(
+        type(value) is not str
+        or len(value) != 64
+        or any(char not in "0123456789abcdef" for char in value)
+        for value in fingerprints.values()
+    ):
+        return unavailable("INDEX_FINGERPRINT_INVALID")
+
+    if not topology.cyclic_components:
+        return unavailable("NO_CYCLIC_COMPONENTS")
+
+    adjacency = {
+        name: tuple(sorted(set(targets)))
+        for name, targets in hard_edges.items()
+    }
+    for targets in tuple(adjacency.values()):
+        for target in targets:
+            adjacency.setdefault(target, ())
+
+    selected: set[str] = set()
+
+    for component in topology.cyclic_components:
+        pending = list(component.members)
+        selected.update(component.members)
+
+        while pending:
+            for target in adjacency[pending.pop()]:
+                if target not in selected:
+                    selected.add(target)
+                    pending.append(target)
+
+        if len(selected) > _MAX_SELECTED:
+            return unavailable("CLOSURE_MODULE_LIMIT")
+
+    if any(module_id not in indexed_ids for module_id in selected):
+        return unavailable("CLOSURE_MODULE_NOT_INDEXED")
+
+    try:
+        module_paths = tuple(
+            sorted(
+                (
+                    module_id,
+                    index.modules[module_id].path,
+                    index.modules[module_id].absolute_path,
+                )
+                for module_id in indexed_ids
+            )
+        )
+    except (AttributeError, TypeError, ValueError):
+        return unavailable("INDEX_MODULE_PATH_INVALID")
+
+    if any(
+        type(path) is not str
+        or type(absolute) is not str
+        or not path
+        or not absolute
+        for _, path, absolute in module_paths
+    ):
+        return unavailable("INDEX_MODULE_PATH_INVALID")
+
+    return OriginalWorkerReindexPlan(
+        status=_READY,
+        reason=None,
+        selected_module_ids=frozenset(selected),
+        graph_sha256=graph_sha256,
+        fingerprints=tuple(sorted(fingerprints.items())),
+        module_paths=module_paths,
+    )
+
+
+def verify_original_worker_reindex(
+    plan: OriginalWorkerReindexPlan,
+    discovery_index: object,
+    discovery_hard_edges: Mapping[str, object],
+    captured_index: object,
+    captured_hard_edges: Mapping[str, object],
+) -> OriginalWorkerReindexVerification:
+    """Verify two caller-supplied index passes before manifest preparation.
+
+    This verifies declared agreement, not an atomic snapshot or
+    authentic canonical provenance. No filesystem or LIVE access.
+    """
+    from contextor.core.symbol_engine.indexer import RepositoryIndex
+
+    if type(plan) is not OriginalWorkerReindexPlan:
+        raise TypeError("plan must be OriginalWorkerReindexPlan")
+    if (
+        type(discovery_index) is not RepositoryIndex
+        or type(captured_index) is not RepositoryIndex
+    ):
+        raise TypeError("both passes must be RepositoryIndex")
+
+    def unavailable(reason: str) -> OriginalWorkerReindexVerification:
+        return OriginalWorkerReindexVerification(
+            status="UNAVAILABLE",
+            reason=reason,
+            source_modules=(),
+        )
+
+    if plan.status != _READY:
+        return unavailable("REINDEX_PLAN_UNAVAILABLE")
+
+    if not plan.selected_module_ids:
+        return unavailable("REINDEX_PLAN_EMPTY")
+
+    try:
+        discovery_graph_hash = fingerprint_hard_edges(
+            discovery_hard_edges
+        )
+        captured_graph_hash = fingerprint_hard_edges(
+            captured_hard_edges
+        )
+    except (TypeError, ValueError):
+        return unavailable("REINDEX_GRAPH_INVALID")
+
+    if discovery_graph_hash != plan.graph_sha256:
+        return unavailable("DISCOVERY_GRAPH_CHANGED")
+
+    if captured_graph_hash != plan.graph_sha256:
+        return unavailable("REINDEX_GRAPH_CHANGED")
+
+    try:
+        discovery_fingerprints = tuple(sorted(
+            discovery_index.source_fingerprints_by_module.items()
+        ))
+        captured_fingerprints = tuple(sorted(
+            captured_index.source_fingerprints_by_module.items()
+        ))
+
+        discovery_paths = tuple(sorted(
+            (
+                module_id,
+                module.path,
+                module.absolute_path,
+            )
+            for module_id, module in discovery_index.modules.items()
+        ))
+        captured_paths = tuple(sorted(
+            (
+                module_id,
+                module.path,
+                module.absolute_path,
+            )
+            for module_id, module in captured_index.modules.items()
+        ))
+    except (AttributeError, TypeError, ValueError):
+        return unavailable("REINDEX_INDEX_SHAPE_INVALID")
+
+    if discovery_paths != plan.module_paths:
+        return unavailable("DISCOVERY_MODULE_INVENTORY_CHANGED")
+
+    if captured_paths != plan.module_paths:
+        return unavailable("REINDEX_MODULE_INVENTORY_CHANGED")
+
+    if discovery_fingerprints != plan.fingerprints:
+        return unavailable("DISCOVERY_FINGERPRINTS_CHANGED")
+
+    if captured_fingerprints != plan.fingerprints:
+        return unavailable("REINDEX_SOURCE_CHANGED")
+
+    if discovery_index.skipped != captured_index.skipped:
+        return unavailable("REINDEX_SKIPPED_FILES_CHANGED")
+
+    if captured_index.original_worker_capture_status != (
+        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    ):
+        return unavailable("REINDEX_CAPTURE_NOT_COMPLETE")
+
+    if (
+        set(captured_index.original_worker_source_snapshots)
+        != plan.selected_module_ids
+        or set(captured_index.original_worker_ast_modes)
+        != plan.selected_module_ids
+    ):
+        return unavailable("REINDEX_SELECTION_MISMATCH")
+
+    binding = assess_original_worker_cycle_closure(
+        captured_index,
+        captured_hard_edges,
+    )
+
+    if binding.status != (
+        "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
+    ):
+        return unavailable(
+            "REINDEX_BINDING_" + (
+                binding.reason or "UNAVAILABLE"
+            )
+        )
+
+    if frozenset(binding.reachable_modules) != (
+        plan.selected_module_ids
+    ):
+        return unavailable("REINDEX_CLOSURE_CHANGED")
+
+    return OriginalWorkerReindexVerification(
+        status=_VERIFIED,
+        reason=None,
+        source_modules=binding.reachable_modules,
+    )
```

### `tests/test_original_worker_reindex_planning.py`

```diff
diff --git a/tests/test_original_worker_reindex_planning.py b/tests/test_original_worker_reindex_planning.py
new file mode 100644
index 0000000..7a85a07
--- /dev/null
+++ b/tests/test_original_worker_reindex_planning.py
@@ -0,0 +1,312 @@
+"""P1D2E: bounded two-pass capture plan and consistency gates."""
+
+from __future__ import annotations
+
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+from contextor.core.analysis.process_pool_lifecycle import (
+    terminate_active_process_pools,
+)
+from contextor.core.cycle_semantics.materialization import (
+    materialize_cycle_semantics,
+)
+from contextor.core.cycle_semantics.original_worker_preparation import (
+    prepare_original_worker_cycle_manifest,
+)
+from contextor.core.cycle_semantics.original_worker_reindex_planning import (
+    plan_original_worker_reindex,
+    verify_original_worker_reindex,
+)
+from contextor.core.graph.graph import build_graph
+from contextor.core.symbol_engine.indexer import index_repository
+
+
+@pytest.fixture(autouse=True)
+def _inline_by_default(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _repo(tmp_path):
+    root = tmp_path / "repo"
+    root.mkdir()
+    (root / "a.py").write_bytes(
+        b"import b\nimport helper\nvalue = 1\n"
+    )
+    (root / "b.py").write_bytes(
+        b"import a\nvalue = 2\n"
+    )
+    (root / "helper.py").write_bytes(b"value = 3\n")
+    (root / "unrelated.py").write_bytes(b"value = 999\n")
+    return root
+
+
+def _index_and_graph(root, selected=None):
+    if selected is None:
+        index = index_repository(str(root))
+    else:
+        index = index_repository(
+            str(root),
+            source_capture_module_ids=selected,
+        )
+    return index, build_graph(index.modules).hard_edges
+
+
+def _two_pass(root):
+    first, first_edges = _index_and_graph(root)
+    plan = plan_original_worker_reindex(first, first_edges)
+    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
+
+    second, second_edges = _index_and_graph(
+        root,
+        plan.selected_module_ids,
+    )
+    return first, first_edges, plan, second, second_edges
+
+
+def _verify(first, first_edges, plan, second, second_edges):
+    return verify_original_worker_reindex(
+        plan,
+        first,
+        first_edges,
+        second,
+        second_edges,
+    )
+
+
+def test_p1d2e_t01_real_two_pass_then_prepared_only(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    first, first_edges, plan, second, second_edges = _two_pass(root)
+
+    assert plan.selected_module_ids == frozenset({
+        "a", "b", "helper",
+    })
+    assert "unrelated" not in plan.selected_module_ids
+    assert first.original_worker_capture_status == "NOT_REQUESTED"
+
+    verified = _verify(
+        first, first_edges, plan, second, second_edges,
+    )
+    assert verified.status == (
+        "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
+    )
+    assert verified.reason is None
+    assert verified.source_modules == ("a", "b", "helper")
+
+    snapshot = materialize_cycle_semantics(
+        root,
+        second_edges,
+        {
+            module_id: module.path
+            for module_id, module in second.modules.items()
+        },
+        second.source_fingerprints_by_module,
+    )
+    prepared = prepare_original_worker_cycle_manifest(
+        second, second_edges, snapshot,
+    )
+    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert prepared.manifest is not None
+    assert prepared.manifest.authority == (
+        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+    )
+
+
+def test_p1d2e_t02_warm_cache_second_pass(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    first, first_edges, plan, second, second_edges = _two_pass(root)
+
+    assert set(second.original_worker_ast_modes.values()) == {
+        "CACHE_SHA256_EQUIVALENT"
+    }
+    verified = _verify(
+        first, first_edges, plan, second, second_edges,
+    )
+    assert verified.status == (
+        "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
+    )
+
+
+def test_p1d2e_t03_no_cycle_produces_no_plan(
+    tmp_path, isolated_dirs,
+):
+    first, _ = _index_and_graph(_repo(tmp_path))
+    acyclic = {
+        "a": {"helper"},
+        "b": set(),
+        "helper": set(),
+        "unrelated": set(),
+    }
+    plan = plan_original_worker_reindex(first, acyclic)
+    assert plan.status == "UNAVAILABLE"
+    assert plan.reason == "NO_CYCLIC_COMPONENTS"
+    assert plan.selected_module_ids == frozenset()
+
+
+def test_p1d2e_t04_large_closure_rejected_before_reindex(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+
+    imports = [b"import b", b"import helper"]
+    for number in range(15):
+        name = f"h{number}"
+        (root / f"{name}.py").write_bytes(b"value = 1\n")
+        imports.append(f"import {name}".encode("ascii"))
+
+    (root / "a.py").write_bytes(
+        b"\n".join(imports) + b"\nvalue = 1\n"
+    )
+
+    first, graph = _index_and_graph(root)
+    plan = plan_original_worker_reindex(first, graph)
+
+    assert plan.status == "UNAVAILABLE"
+    assert plan.reason == "CLOSURE_MODULE_LIMIT"
+    assert plan.selected_module_ids == frozenset()
+
+
+def test_p1d2e_t05_source_change_between_passes_rejected(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    first, first_edges = _index_and_graph(root)
+    plan = plan_original_worker_reindex(first, first_edges)
+
+    (root / "helper.py").write_bytes(b"value = 300\n")
+
+    second, second_edges = _index_and_graph(
+        root, plan.selected_module_ids,
+    )
+    verified = _verify(
+        first, first_edges, plan, second, second_edges,
+    )
+
+    assert verified.status == "UNAVAILABLE"
+    assert verified.reason == "REINDEX_SOURCE_CHANGED"
+    assert verified.source_modules == ()
+
+
+def test_p1d2e_t06_changed_graph_rejected(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    first, first_edges, plan, second, second_edges = _two_pass(root)
+
+    altered = {
+        name: set(targets)
+        for name, targets in second_edges.items()
+    }
+    altered["a"].remove("helper")
+
+    verified = _verify(
+        first, first_edges, plan, second, altered,
+    )
+    assert verified.status == "UNAVAILABLE"
+    assert verified.reason == "REINDEX_GRAPH_CHANGED"
+
+
+def test_p1d2e_t07_missing_capture_selection_rejected(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    first, first_edges = _index_and_graph(root)
+    plan = plan_original_worker_reindex(first, first_edges)
+
+    second, second_edges = _index_and_graph(
+        root, frozenset({"a", "b"}),
+    )
+    verified = _verify(
+        first, first_edges, plan, second, second_edges,
+    )
+
+    assert verified.status == "UNAVAILABLE"
+    assert verified.reason == "REINDEX_SELECTION_MISMATCH"
+
+
+def test_p1d2e_t08_changed_module_inventory_rejected(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    first, first_edges, plan, second, second_edges = _two_pass(root)
+
+    altered_modules = dict(second.modules)
+    altered_modules.pop("unrelated")
+    altered_second = replace(
+        second,
+        modules=altered_modules,
+    )
+
+    verified = _verify(
+        first, first_edges, plan, altered_second, second_edges,
+    )
+    assert verified.status == "UNAVAILABLE"
+    assert verified.reason == "REINDEX_MODULE_INVENTORY_CHANGED"
+
+
+def test_p1d2e_t09_real_process_pool_two_pass(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    monkeypatch.delenv(
+        "CONTEXTOR_DISABLE_PROCESS_POOL",
+        raising=False,
+    )
+
+    terminate_active_process_pools(timeout=1.0)
+    try:
+        first, first_edges, plan, second, second_edges = _two_pass(root)
+        verified = _verify(
+            first, first_edges, plan, second, second_edges,
+        )
+        assert verified.status == (
+            "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
+        )
+    finally:
+        terminate_active_process_pools(timeout=1.0)
+
+
+def test_p1d2e_t10_graph_inventory_mismatch_rejected(
+    tmp_path, isolated_dirs,
+):
+    first, edges = _index_and_graph(_repo(tmp_path))
+    altered = {
+        key: value
+        for key, value in edges.items()
+        if key != "unrelated"
+    }
+    plan = plan_original_worker_reindex(first, altered)
+
+    assert plan.status == "UNAVAILABLE"
+    assert plan.reason == "GRAPH_INDEX_DOMAIN_MISMATCH"
+
+
+def test_p1d2e_t11_planning_verification_no_disk_reads(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    first, first_edges, plan, second, second_edges = _two_pass(root)
+
+    def forbidden_read(self):
+        raise AssertionError("unexpected source read")
+
+    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
+
+    repeated = plan_original_worker_reindex(
+        first, first_edges,
+    )
+    verified = _verify(
+        first, first_edges, repeated, second, second_edges,
+    )
+
+    assert repeated == plan
+    assert verified.status == (
+        "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
+    )
+
```

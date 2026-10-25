# CONTEXTOR_P1D2B_SELECTED_SCC_CLOSURE_BINDING

## HEAD_BEFORE_AND_AFTER

- DIRECT_EVIDENCE: HEAD before and after: `9ba55b9b905cd58c0db46c1b57a1c71c8b3d2b2b`. The supplied baseline was `78c386611245a475f436f2ca3938390b60f4fc69`; the user explicitly waived that HEAD condition with “jebac head”. No Git history change was made.

## PREFLIGHT_AND_PRIOR_P1D2A_PRESERVATION

- DIRECT_EVIDENCE: `indexer.py` still contains `source_capture_module_ids`, `original_worker_source_snapshots`, `original_worker_ast_modes` and `ALL_SELECTED_CAPTURED_NON_ATOMIC`; `tests/test_indexer_original_capture_handoff.py` exists. Neither P1D2B target existed before editing. Final `git status` lists only the two new files and this report; no P1D2A file was changed.
- CODE_PATH_PROVED: Contextor MCP resolved `RepositoryIndex` and `analyze_import_cycle_topology` at canonical revision 672 before editing.

## NATIVE_CODEX_FILE_EDITS

- DIRECT_EVIDENCE: Created exactly `contextor/core/cycle_semantics/original_worker_binding.py` and `tests/test_original_worker_cycle_closure_binding.py` using the native Codex file-editing tool. A read-only normalized text comparison against the two marked blocks in the attachment reported `EXACT_MATCH` for both (160 and 166 lines). No other source or test was edited.

## FILES_CHANGED

- `contextor/core/cycle_semantics/original_worker_binding.py` (new)
- `tests/test_original_worker_cycle_closure_binding.py` (new)
- `walkthrough.md` (this report; excluded from production/test diff requirement)

## ACTUAL_DIFF

### `contextor/core/cycle_semantics/original_worker_binding.py`

```diff
diff --git a/contextor/core/cycle_semantics/original_worker_binding.py b/contextor/core/cycle_semantics/original_worker_binding.py
new file mode 100644
index 0000000..d469b86
--- /dev/null
+++ b/contextor/core/cycle_semantics/original_worker_binding.py
@@ -0,0 +1,160 @@
+"""Bound selected original indexer bytes to a supplied SCC closure.
+
+This is a non-atomic, in-memory consistency check. It does not authenticate
+canonical graph ownership, bind an installed LIVE generation, or mint receipts.
+"""
+
+from __future__ import annotations
+
+import hashlib
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from contextor.core.source import SourceSnapshot
+
+from .scc import analyze_import_cycle_topology
+
+
+_CAPTURE_STATUS = "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+_ACCEPTED_MODES = frozenset({
+    "PARSED_FROM_WORKER_READ",
+    "CACHE_SHA256_EQUIVALENT",
+})
+_MAX_MODULES = 16
+_MAX_SOURCE_BYTES = 2 * 1024 * 1024
+_MAX_TOTAL_BYTES = 32 * 1024 * 1024
+
+
+@dataclass(frozen=True)
+class OriginalWorkerCycleClosureBinding:
+    status: str
+    reason: str | None
+    cyclic_components: tuple[tuple[str, ...], ...]
+    reachable_modules: tuple[str, ...]
+    source_snapshots: dict[str, SourceSnapshot]
+    ast_modes: tuple[tuple[str, str], ...]
+    retained_raw_bytes: int
+
+
+def assess_original_worker_cycle_closure(
+    index: object,
+    hard_edges: Mapping[str, object],
+) -> OriginalWorkerCycleClosureBinding:
+    """Validate that opted-in original indexer captures cover every SCC closure.
+
+    Inputs are caller-supplied index and graph. No filesystem access, parsing,
+    worker execution, canonical freshness assertion, publication, or LIVE I/O.
+    Complete only means selected worker-read bytes match the supplied index
+    fingerprints, across all reachable cyclic SCC closures, without atomically
+    capturing the repository or authenticating who supplied the graph.
+    """
+    # Import locally to avoid creating an import-time dependency back to the
+    # indexer from cycle-semantics modules.
+    from contextor.core.symbol_engine.indexer import RepositoryIndex
+
+    if type(index) is not RepositoryIndex:
+        raise TypeError("index must be RepositoryIndex")
+    if not isinstance(hard_edges, Mapping):
+        raise TypeError("hard_edges must be a mapping")
+
+    def unavailable(reason: str) -> OriginalWorkerCycleClosureBinding:
+        # Never expose partially validated snapshots or modes.
+        return OriginalWorkerCycleClosureBinding(
+            status="UNAVAILABLE",
+            reason=reason,
+            cyclic_components=(),
+            reachable_modules=(),
+            source_snapshots={},
+            ast_modes=(),
+            retained_raw_bytes=0,
+        )
+
+    topology = analyze_import_cycle_topology(hard_edges)
+    if not topology.cyclic_components:
+        return unavailable("NO_CYCLIC_COMPONENTS")
+    if (
+        index.original_worker_capture_status != _CAPTURE_STATUS
+        or index.original_worker_capture_reason is not None
+    ):
+        return unavailable("INDEX_CAPTURE_NOT_COMPLETE")
+
+    if (
+        type(index.modules) is not dict
+        or type(index.source_fingerprints_by_module) is not dict
+        or type(index.original_worker_source_snapshots) is not dict
+        or type(index.original_worker_ast_modes) is not dict
+    ):
+        return unavailable("INDEX_CAPTURE_SHAPE_INVALID")
+
+    snapshots = index.original_worker_source_snapshots
+    modes = index.original_worker_ast_modes
+    if (
+        len(snapshots) > _MAX_MODULES
+        or set(snapshots) != set(modes)
+    ):
+        return unavailable("INDEX_CAPTURE_SHAPE_INVALID")
+
+    adjacency: dict[str, tuple[str, ...]] = {}
+    for module_id, targets in hard_edges.items():
+        adjacency[module_id] = tuple(sorted(set(targets)))
+    for targets in tuple(adjacency.values()):
+        for target in targets:
+            adjacency.setdefault(target, ())
+
+    required: set[str] = set()
+    components = tuple(
+        component.members
+        for component in topology.cyclic_components
+    )
+    for members in components:
+        pending = list(members)
+        required.update(members)
+        while pending:
+            for target in adjacency[pending.pop()]:
+                if target not in required:
+                    required.add(target)
+                    pending.append(target)
+        if len(required) > _MAX_MODULES:
+            return unavailable("CLOSURE_MODULE_LIMIT")
+
+    selected = tuple(sorted(required))
+    for module_id in selected:
+        if module_id not in index.modules:
+            return unavailable("CLOSURE_MODULE_NOT_INDEXED:" + module_id)
+        if module_id not in snapshots or module_id not in modes:
+            return unavailable("CLOSURE_CAPTURE_MISSING:" + module_id)
+
+    selected_snapshots: dict[str, SourceSnapshot] = {}
+    selected_modes: dict[str, str] = {}
+    total = 0
+    for module_id in selected:
+        snapshot = snapshots[module_id]
+        if type(snapshot) is not SourceSnapshot or type(snapshot.raw) is not bytes:
+            return unavailable("CLOSURE_SOURCE_INVALID:" + module_id)
+        if len(snapshot.raw) > _MAX_SOURCE_BYTES:
+            return unavailable("CLOSURE_SOURCE_BYTE_LIMIT:" + module_id)
+        total += len(snapshot.raw)
+        if total > _MAX_TOTAL_BYTES:
+            return unavailable("CLOSURE_TOTAL_BYTE_LIMIT")
+        indexed_hash = index.source_fingerprints_by_module.get(module_id)
+        if (
+            type(indexed_hash) is not str
+            or snapshot.source_fingerprint != indexed_hash
+            or hashlib.sha256(snapshot.raw).hexdigest() != indexed_hash
+        ):
+            return unavailable("CLOSURE_SOURCE_DIGEST_MISMATCH:" + module_id)
+        mode = modes[module_id]
+        if type(mode) is not str or mode not in _ACCEPTED_MODES:
+            return unavailable("CLOSURE_AST_MODE_INVALID:" + module_id)
+        selected_snapshots[module_id] = snapshot
+        selected_modes[module_id] = mode
+
+    return OriginalWorkerCycleClosureBinding(
+        status="SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC",
+        reason=None,
+        cyclic_components=components,
+        reachable_modules=selected,
+        source_snapshots=selected_snapshots,
+        ast_modes=tuple(sorted(selected_modes.items())),
+        retained_raw_bytes=total,
+    )
```

### `tests/test_original_worker_cycle_closure_binding.py`

```diff
diff --git a/tests/test_original_worker_cycle_closure_binding.py b/tests/test_original_worker_cycle_closure_binding.py
new file mode 100644
index 0000000..2fca506
--- /dev/null
+++ b/tests/test_original_worker_cycle_closure_binding.py
@@ -0,0 +1,166 @@
+"""P1D2B: pure SCC-closure binding of opted-in original indexer bytes."""
+
+from __future__ import annotations
+
+import hashlib
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+from contextor.core.cycle_semantics.original_worker_binding import (
+    assess_original_worker_cycle_closure,
+)
+from contextor.core.source import SourceSnapshot
+from contextor.core.symbol_engine.indexer import index_repository
+
+
+_GRAPH = {
+    "a": {"b", "helper"},
+    "b": {"a"},
+    "helper": set(),
+}
+
+
+@pytest.fixture(autouse=True)
+def _inline_index(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _repo(tmp_path):
+    root = tmp_path / "repo"
+    root.mkdir()
+    (root / "a.py").write_bytes(b"import b\nimport helper\n")
+    (root / "b.py").write_bytes(b"import a\n")
+    (root / "helper.py").write_bytes(b"value = 1\n")
+    return root
+
+
+def _index(root, *selected):
+    return index_repository(
+        str(root), source_capture_module_ids=frozenset(selected),
+    )
+
+
+def test_p1d2b_t01_complete_original_indexer_closure(tmp_path, isolated_dirs):
+    root = _repo(tmp_path)
+    index = _index(root, "a", "b", "helper")
+    result = assess_original_worker_cycle_closure(index, _GRAPH)
+    assert result.status == "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
+    assert result.reason is None
+    assert result.cyclic_components == (("a", "b"),)
+    assert result.reachable_modules == ("a", "b", "helper")
+    assert set(result.source_snapshots) == set(result.reachable_modules)
+    assert set(dict(result.ast_modes)) == set(result.reachable_modules)
+    assert result.retained_raw_bytes == sum(
+        len(item.raw) for item in result.source_snapshots.values()
+    )
+    for module_id, snapshot in result.source_snapshots.items():
+        assert snapshot.raw == (root / f"{module_id}.py").read_bytes()
+        assert hashlib.sha256(snapshot.raw).hexdigest() == (
+            index.source_fingerprints_by_module[module_id]
+        )
+
+
+def test_p1d2b_t02_default_index_not_authorized(tmp_path, isolated_dirs):
+    index = index_repository(str(_repo(tmp_path)))
+    result = assess_original_worker_cycle_closure(index, _GRAPH)
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "INDEX_CAPTURE_NOT_COMPLETE"
+    assert result.source_snapshots == {}
+    assert result.retained_raw_bytes == 0
+
+
+def test_p1d2b_t03_missing_closure_source_rejects_all(tmp_path, isolated_dirs):
+    index = _index(_repo(tmp_path), "a", "b")
+    result = assess_original_worker_cycle_closure(index, _GRAPH)
+    assert result.reason == "CLOSURE_CAPTURE_MISSING:helper"
+    assert result.source_snapshots == {}
+    assert result.ast_modes == ()
+
+
+def test_p1d2b_t04_tampered_original_bytes_rejected(tmp_path, isolated_dirs):
+    index = _index(_repo(tmp_path), "a", "b", "helper")
+    altered = dict(index.original_worker_source_snapshots)
+    old = altered["a"]
+    altered["a"] = SourceSnapshot(b"forged", old.source_fingerprint)
+    forged_index = replace(index, original_worker_source_snapshots=altered)
+    result = assess_original_worker_cycle_closure(forged_index, _GRAPH)
+    assert result.reason == "CLOSURE_SOURCE_DIGEST_MISMATCH:a"
+    assert result.source_snapshots == {}
+
+
+def test_p1d2b_t05_invalid_ast_mode_rejected(tmp_path, isolated_dirs):
+    index = _index(_repo(tmp_path), "a", "b", "helper")
+    modes = dict(index.original_worker_ast_modes)
+    modes["b"] = "FAKE_AST_MODE"
+    result = assess_original_worker_cycle_closure(
+        replace(index, original_worker_ast_modes=modes), _GRAPH,
+    )
+    assert result.reason == "CLOSURE_AST_MODE_INVALID:b"
+    assert result.source_snapshots == {}
+
+
+def test_p1d2b_t06_nonindexed_reachable_module_rejected(tmp_path, isolated_dirs):
+    index = _index(_repo(tmp_path), "a", "b", "helper")
+    graph = {"a": {"b", "ghost"}, "b": {"a"}, "ghost": set()}
+    result = assess_original_worker_cycle_closure(index, graph)
+    assert result.reason == "CLOSURE_MODULE_NOT_INDEXED:ghost"
+    assert result.source_snapshots == {}
+
+
+def test_p1d2b_t07_closure_above_selection_budget_rejected(tmp_path, isolated_dirs):
+    index = _index(_repo(tmp_path), "a", "b", "helper")
+    graph = {"a": {"a", *(f"x{i}" for i in range(16))}}
+    result = assess_original_worker_cycle_closure(index, graph)
+    assert result.reason == "CLOSURE_MODULE_LIMIT"
+    assert result.source_snapshots == {}
+
+
+def test_p1d2b_t08_no_cycle_does_not_claim_evidence(tmp_path, isolated_dirs):
+    index = _index(_repo(tmp_path), "a", "b", "helper")
+    result = assess_original_worker_cycle_closure(index, {
+        "a": {"helper"}, "helper": set(), "b": set(),
+    })
+    assert result.reason == "NO_CYCLIC_COMPONENTS"
+    assert result.source_snapshots == {}
+
+
+def test_p1d2b_t09_multiple_sccs_no_partial_success(tmp_path, isolated_dirs):
+    root = _repo(tmp_path)
+    (root / "c.py").write_bytes(b"import d\n")
+    (root / "d.py").write_bytes(b"import c\n")
+    graph = {**_GRAPH, "c": {"d"}, "d": {"c"}}
+    index = _index(root, "a", "b", "helper", "c", "d")
+    valid = assess_original_worker_cycle_closure(index, graph)
+    assert valid.status == "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
+    assert valid.cyclic_components == (("a", "b"), ("c", "d"))
+    assert valid.reachable_modules == ("a", "b", "c", "d", "helper")
+    invalid = assess_original_worker_cycle_closure(
+        _index(root, "a", "b", "helper", "c"), graph,
+    )
+    assert invalid.reason == "CLOSURE_CAPTURE_MISSING:d"
+    assert invalid.source_snapshots == {}
+
+
+def test_p1d2b_t10_warm_cache_equivalence_explicit(tmp_path, isolated_dirs):
+    root = _repo(tmp_path)
+    index_repository(str(root))
+    index = _index(root, "a", "b", "helper")
+    result = assess_original_worker_cycle_closure(index, _GRAPH)
+    assert result.status == "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
+    assert set(dict(result.ast_modes).values()) == {"CACHE_SHA256_EQUIVALENT"}
+
+
+def test_p1d2b_t11_binding_performs_no_filesystem_reads(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    index = _index(root, "a", "b", "helper")
+
+    def forbidden_read(self):
+        raise AssertionError("binding performed a new filesystem read")
+
+    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
+    result = assess_original_worker_cycle_closure(index, _GRAPH)
+    assert result.status == "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
```

## P1D2B_TEST_RESULTS

- DIRECT_EVIDENCE: New file defines 11 P1D2B tests. The exact requested focused invocation returned `63 passed in 15.25s`; no failures.

## FOCUSED_NON_REGRESSION

- DIRECT_EVIDENCE: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_original_worker_cycle_closure_binding.py tests/test_indexer_original_capture_handoff.py tests/test_indexer_worker_source_capture.py tests/test_cycle_semantics_selective_worker_capture.py tests/test_index_fusion.py` returned exit 0, 63/63 passed. The prior four-file set contributed 52 tests. No FULL run or test on the active repository was performed.

## PY_COMPILE_AND_WHITESPACE

- DIRECT_EVIDENCE: `py_compile` on both new files returned exit 0. `git diff --no-index --check -- /dev/null` on each new file emitted no whitespace diagnostics; exit 1 denotes the expected difference from `/dev/null`. `git diff --check` on tracked changes emitted no whitespace diagnostics. Git warned that LF may become CRLF on a future checkout; no source content mismatch was found.

## CANONICAL_WATCHER_AND_FRESHNESS

- DIRECT_EVIDENCE: Pre-edit canonical revision 672. `get_live_events(after_revision=672)` returned a continuous `desktop_watcher` UPDATED event for the new production file at revision 673; subsequent read after 673 returned the test-file UPDATED event at revision 674. `resync_required=false`. At revision 674, Contextor `get_symbol_implementation(mode=preview)` resolved both new symbols with `workspace_sync=verified`. Cycles family: fresh, count 16 DFS back-edge paths. `cycle_semantics`: stale. No manual `update_file` was called.

## ORIGINAL_SOURCE_CAPTURE_PROOF_LIMITS

- CODE_PATH_PROVED: The new binding checks the caller-supplied index and hard-edge closure against opted-in original worker captures, indexed SHA-256 values, accepted AST modes and 16-module/2 MiB-per-source/32 MiB-total limits. It returns no partial snapshots on failure. Successful status explicitly says `NON_ATOMIC`. It does not establish cross-file atomicity or canonical graph ownership.
- CONTRACT_PROVED by isolated tests: complete closure, missing/default capture, tampered bytes/mode, nonindexed module, limit, no cycle, multiple SCCs, warm-cache equivalence and no binding-time filesystem read.

## RUNTIME_ADOPTION_LIMITS

- UNKNOWN: Watcher indexing and verified source equality do not establish which implementation is loaded in the active LIVE process. No restart, reload, installed-generation verification, publication, runtime import-safety test or SAFE certification occurred.

## FINAL_VERDICT

- DIRECT_EVIDENCE: Literal files created, exact-content comparison passed, 63 focused tests passed, compiler passed and both watcher events were observed. CODE_PATH_PROVED / CONTRACT_PROVED: the selected in-memory SCC closure binding works under the supplied non-atomic limits in isolated tests. UNKNOWN: active loaded-code adoption and generation/publication authority. STOP after P1D2B.

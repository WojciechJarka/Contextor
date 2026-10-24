# TASK
P1D1B_SELECTIVE_SCC_WORKER_CAPTURE — exact auditor supplied implementation in two new files only.

# HEAD_BEFORE
3d0d3c08367627ba57da36aaf9ada56eb5131c24; clean working tree, both approved new files absent.

# HEAD_AFTER
3d0d3c08367627ba57da36aaf9ada56eb5131c24; no commit.

# FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\core\cycle_semantics\selective_worker_capture.py
- C:\Temp\Contextor_Repo\tests\test_cycle_semantics_selective_worker_capture.py

# ARCHITECTURAL_DEPENDENCIES
CONTRACT_PROVED (Contextor MCP, pre-edit revision 656, workspace_sync=verified): _process_single_file at indexer.py lines 367–987 supplies the opt-in worker byte channel; RepositoryIndex at lines 1018–1046 holds modules and source_fingerprints_by_module; SourceSnapshot at source.py lines 39–42 holds raw and SHA-256; analyze_import_cycle_topology at scc.py lines 28–131 yields cyclic SCCs; selective_source_replay.py lines 195–260 supplied the bounded-closure shape; managed_reusable_process_pool at process_pool_lifecycle.py lines 169–261 supplies a caller-owned executor. _process_single_file blast radius reported three confirmed direct static consumers before this edit. No existing implementation was changed.

# T01_T16_RESULTS
DIRECT_EVIDENCE: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_selective_worker_capture.py => 16 passed in 8.31s. T01–T16 all passed.

# FOCUSED_NON_REGRESSION
DIRECT_EVIDENCE: .\.venv\Scripts\python.exe -m pytest -q tests/test_indexer_worker_source_capture.py tests/test_cycle_semantics_selective_source_replay.py tests/test_index_fusion.py tests/test_cycle_semantics_evidence.py tests/test_process_pool_lifecycle.py => 121 passed, 1 third-party AuthlibDeprecationWarning, in 17.97s. No full pytest suite run.

# SCC_SELECTION
CODE_PATH_PROVED: supplied hard_edges feed SCC topology; each component's reachable closure is calculated without rebuilding RepositoryIndex or graph. T01 and T13 prove cyclic-only selection; T11 proves independent SCC outcomes. No cross-SCC raw cache is added.

# WORKER_SECOND_PASS_PROVENANCE
CODE_PATH_PROVED: each selected file invokes _process_single_file with source_capture_max_bytes. Captured raw bytes and worker fingerprint must match supplied index fingerprint and imports, with exact path/module identity and INDEXER_WORKER_READ origin. This is a second worker read, not original FULL bytes or a LIVE generation certificate. The worker may read/write its existing indexing cache; this procedure is not a read-only filesystem operation.

# CACHE_HIT_AND_MISS_MODES
DIRECT_EVIDENCE: T02 accepted explicit CACHE_SHA256_EQUIVALENT or PARSED_FROM_WORKER_READ modes. CACHE_SHA256_EQUIVALENT means hash-validated cached facts; it does not mean AST was parsed again from the current bytes.

# PROCESS_POOL_IPC_EVIDENCE
DIRECT_EVIDENCE: T03 passed using the caller-supplied managed_reusable_process_pool executor. The new module creates or terminates no pool and submits one worker future at a time.

# FILE_AND_CLOSURE_BUDGETS
DIRECT_EVIDENCE: T05 per-source preflight blocked worker dispatch; T06 cumulative closure budget returned UNAVAILABLE without partial bytes; T11 independent SCC budget behavior; T14 invalid limits rejected. Preflight stat is an optimization, not atomic identity.

# MANY_UNRELATED_FILES
DIRECT_EVIDENCE: T10 added 250 unrelated Python modules; none appeared in observed worker dispatches.

# FAILURE_AND_FORGERY_BEHAVIOR
DIRECT_EVIDENCE: T04 post-index drift failed closed; T07 missing module, T08 forged imports, T09 missing fingerprint, T12 forged origin, T15 worker exception, T16 forged module ID all returned UNAVAILABLE with empty source_snapshots. No partial successful closure is exposed.

# MEMORY_AND_IPC_LIMITATIONS
CONTRACT_PROVED: result retention is scoped to one yielded SCC closure when caller consumes/releases each yield. Bound covers captured raw bytes per file and closure. It does not bound full worker heap, entire worker IPC result, source-file read size, overlapping-closure rereads, or filesystem simultaneity. No SAFE verdict, graph mutation, canonical publication, or warning suppression is introduced.

# LIVE_REVISION_BEFORE_AFTER
Before 656; after 658. Activity epoch fafa60a0964a48499f00c8e2fa983cd0; continuity from 656=continuous, resync_required=false.

# WATCHER_EVENTS
DIRECT_EVIDENCE: revision 657 desktop_watcher update_file UPDATED for selective_worker_capture.py; revision 658 desktop_watcher update_file UPDATED for test_cycle_semantics_selective_worker_capture.py. Revision 657 included two ADDED collision diagnostics for IDENTICAL_DEFINITION_DUPLICATE of DEFAULT_MAX_SOURCE_BYTES and DEFAULT_MAX_CLOSURE_BYTES against selective_source_replay.py. These arise from the exact supplied patch; no unapproved rename was made. No manual update_file call.

# WORKSPACE_SYNC
Contextor get_module_context for each new file: canonical_state=fresh, workspace_sync=verified, canonical_revision=658, advisory_warning=null. Global cycle_semantics family remains stale; this patch does not claim a fresh semantic certificate.

# RUNTIME_ADOPTION_LIMITATION
Fresh Python test processes executed the new code. LIVE watcher indexing and workspace_sync verify canonical source adoption, not whether already-running Desktop/MCP/LIVE processes imported this new module. Existing-process loaded-code adoption remains UNKNOWN.

# RESTART_REQUIREMENTS
No process restarted. Manual reload/restart may be required before an already-running process imports the new module; no runtime adoption certification was requested or performed.

# WHITESPACE_CHECK
py_compile passed for both files. git diff --check and git diff --no-index --check for each new file passed. Both files end in LF and have no trailing-whitespace lines. Git emitted only working-copy LF→CRLF conversion warnings.

# FULL_DIFFS

## contextor/core/cycle_semantics/selective_worker_capture.py

```diff
diff --git a/contextor/core/cycle_semantics/selective_worker_capture.py b/contextor/core/cycle_semantics/selective_worker_capture.py
new file mode 100644
index 0000000..007a454
--- /dev/null
+++ b/contextor/core/cycle_semantics/selective_worker_capture.py
@@ -0,0 +1,343 @@
+"""Selective SCC capture using the indexer worker's opt-in byte channel.
+
+Each selected worker task performs a SECOND source read.
+Its bytes originate from that worker task, not the original FULL index.
+
+Hash and import equality are checked against the supplied index.
+No canonical publication, runtime safety or atomicity is certified.
+"""
+
+from __future__ import annotations
+
+import hashlib
+from collections.abc import Iterator, Mapping
+from concurrent.futures import Executor
+from dataclasses import dataclass
+from pathlib import Path
+
+from contextor.core.source import SourceSnapshot
+from contextor.core.symbol_engine.indexer import (
+    RepositoryIndex,
+    _process_single_file,
+)
+
+from .scc import analyze_import_cycle_topology
+
+
+WORKER_CAPTURE_AUTHORITY = (
+    "SELECTIVE_INDEXER_WORKER_SECOND_PASS"
+    "_NOT_ORIGINAL_FULL_INDEX"
+    "_NOT_ATOMIC_NOT_LIVE_CERTIFIED"
+)
+
+DEFAULT_MAX_SOURCE_BYTES = 2 * 1024 * 1024
+DEFAULT_MAX_CLOSURE_BYTES = 32 * 1024 * 1024
+
+_SUCCESS = (
+    "WORKER_SECOND_PASS_BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
+)
+
+_ACCEPTED_AST_MODES = frozenset({
+    "PARSED_FROM_WORKER_READ",
+    "CACHE_SHA256_EQUIVALENT",
+})
+
+
+@dataclass(frozen=True)
+class SCCWorkerCapture:
+    members: tuple[str, ...]
+    reachable_modules: tuple[str, ...]
+    status: str
+    reason: str | None
+    source_snapshots: Mapping[str, SourceSnapshot]
+    ast_modes: tuple[tuple[str, str], ...]
+    retained_raw_bytes: int
+    authority: str = WORKER_CAPTURE_AUTHORITY
+
+
+def _valid_sha256(value: object) -> bool:
+    return (
+        type(value) is str
+        and len(value) == 64
+        and all(
+            character in "0123456789abcdef"
+            for character in value
+        )
+    )
+
+
+def _capture_closure(
+    root: Path,
+    index: RepositoryIndex,
+    members: tuple[str, ...],
+    closure: tuple[str, ...],
+    *,
+    max_source_bytes: int,
+    max_closure_bytes: int,
+    executor: Executor | None,
+) -> SCCWorkerCapture:
+    snapshots: dict[str, SourceSnapshot] = {}
+    modes: dict[str, str] = {}
+    total = 0
+
+    def unavailable(reason: str) -> SCCWorkerCapture:
+        # Never expose a partially successful SCC closure.
+        return SCCWorkerCapture(
+            members=members,
+            reachable_modules=closure,
+            status="UNAVAILABLE",
+            reason=reason,
+            source_snapshots={},
+            ast_modes=(),
+            retained_raw_bytes=0,
+        )
+
+    for module_id in closure:
+        indexed = index.modules.get(module_id)
+        if indexed is None:
+            return unavailable(
+                "MODULE_NOT_INDEXED:" + module_id
+            )
+
+        expected_hash = (
+            index.source_fingerprints_by_module.get(module_id)
+        )
+        if not _valid_sha256(expected_hash):
+            return unavailable(
+                "INDEX_FINGERPRINT_UNAVAILABLE:" + module_id
+            )
+
+        try:
+            relative = Path(indexed.path)
+            if relative.is_absolute():
+                return unavailable(
+                    "SOURCE_PATH_IDENTITY_MISMATCH:" + module_id
+                )
+
+            source_path = (
+                root / relative
+            ).resolve(strict=True)
+            indexed_absolute = Path(
+                indexed.absolute_path
+            ).resolve(strict=True)
+        except (OSError, RuntimeError, ValueError, TypeError):
+            return unavailable(
+                "SOURCE_PATH_UNAVAILABLE:" + module_id
+            )
+
+        if (
+            not source_path.is_relative_to(root)
+            or source_path != indexed_absolute
+            or not source_path.is_file()
+            or source_path.suffix != ".py"
+        ):
+            return unavailable(
+                "SOURCE_PATH_IDENTITY_MISMATCH:" + module_id
+            )
+
+        remaining = max_closure_bytes - total
+        allowed = min(max_source_bytes, remaining)
+        if allowed < 1:
+            return unavailable(
+                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module_id
+            )
+
+        # Preflight avoids scheduling obviously oversized files.
+        # The worker still performs the authoritative size check
+        # on its own captured raw bytes.
+        try:
+            size = source_path.stat().st_size
+        except OSError:
+            return unavailable(
+                "SOURCE_STAT_FAILED:" + module_id
+            )
+
+        if size > allowed:
+            return unavailable(
+                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module_id
+            )
+
+        try:
+            if executor is None:
+                result = _process_single_file(
+                    str(source_path),
+                    str(root),
+                    source_capture_max_bytes=allowed,
+                )
+            else:
+                future = executor.submit(
+                    _process_single_file,
+                    str(source_path),
+                    str(root),
+                    None,
+                    None,
+                    None,
+                    allowed,
+                )
+                result = future.result()
+        except Exception:
+            return unavailable(
+                "WORKER_EXECUTION_FAILED:" + module_id
+            )
+
+        if not isinstance(result, dict):
+            return unavailable(
+                "WORKER_RESULT_INVALID:" + module_id
+            )
+
+        if (
+            result.get("module_id") != module_id
+            or result.get("path") != indexed.path
+            or result.get("absolute_path")
+            != str(source_path)
+        ):
+            return unavailable(
+                "WORKER_IDENTITY_MISMATCH:" + module_id
+            )
+
+        status = result.get("source_capture_status")
+
+        if status == "BYTE_LIMIT":
+            return unavailable(
+                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module_id
+            )
+
+        if (
+            result.get("error") is not None
+            or status != "CAPTURED"
+        ):
+            return unavailable(
+                "WORKER_CAPTURE_UNAVAILABLE:" + module_id
+            )
+
+        if result.get("source_capture_origin") != (
+            "INDEXER_WORKER_READ"
+        ):
+            return unavailable(
+                "WORKER_CAPTURE_ORIGIN_INVALID:" + module_id
+            )
+
+        mode = result.get("source_capture_ast_mode")
+        if mode not in _ACCEPTED_AST_MODES:
+            return unavailable(
+                "WORKER_AST_MODE_INVALID:" + module_id
+            )
+
+        raw = result.get("source_capture_bytes")
+        if type(raw) is not bytes:
+            return unavailable(
+                "WORKER_SOURCE_BYTES_INVALID:" + module_id
+            )
+
+        if len(raw) > allowed:
+            return unavailable(
+                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module_id
+            )
+
+        actual_hash = hashlib.sha256(raw).hexdigest()
+        if (
+            actual_hash != expected_hash
+            or result.get("source_fingerprint")
+            != actual_hash
+        ):
+            return unavailable(
+                "WORKER_INDEX_BYTES_MISMATCH:" + module_id
+            )
+
+        if result.get("imports") != indexed.imports:
+            return unavailable(
+                "WORKER_INDEX_IMPORTS_MISMATCH:" + module_id
+            )
+
+        snapshots[module_id] = SourceSnapshot(
+            raw=raw,
+            source_fingerprint=actual_hash,
+        )
+        modes[module_id] = mode
+        total += len(raw)
+
+        # Discard the full worker result before processing
+        # another source file in this closure.
+        del result
+
+    return SCCWorkerCapture(
+        members=members,
+        reachable_modules=closure,
+        status=_SUCCESS,
+        reason=None,
+        source_snapshots=snapshots,
+        ast_modes=tuple(sorted(modes.items())),
+        retained_raw_bytes=total,
+    )
+
+
+def iter_selective_scc_worker_captures(
+    repository_root: str | Path,
+    hard_edges: Mapping[str, object],
+    index: RepositoryIndex,
+    *,
+    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
+    max_closure_bytes: int = DEFAULT_MAX_CLOSURE_BYTES,
+    executor: Executor | None = None,
+) -> Iterator[SCCWorkerCapture]:
+    """Replay only reachable cyclic SCC closures.
+
+    An optional executor is supplied and owned by the caller.
+    This function neither creates nor terminates process pools.
+
+    Consume and release each yielded result before requesting
+    the next one to keep retained raw bytes SCC-scoped.
+    """
+    if not isinstance(index, RepositoryIndex):
+        raise TypeError("index must be RepositoryIndex")
+
+    if (
+        type(max_source_bytes) is not int
+        or not 1 <= max_source_bytes <= 64 * 1024 * 1024
+    ):
+        raise ValueError("invalid max_source_bytes")
+
+    if (
+        type(max_closure_bytes) is not int
+        or not 1 <= max_closure_bytes <= 256 * 1024 * 1024
+    ):
+        raise ValueError("invalid max_closure_bytes")
+
+    root = Path(repository_root).resolve(strict=True)
+    if not root.is_dir():
+        raise ValueError(
+            "repository root is not a directory"
+        )
+
+    topology = analyze_import_cycle_topology(hard_edges)
+
+    adjacency = {
+        module_id: tuple(sorted(set(targets)))
+        for module_id, targets in hard_edges.items()
+    }
+    for targets in tuple(adjacency.values()):
+        for target in targets:
+            adjacency.setdefault(target, ())
+
+    for component in topology.cyclic_components:
+        visited = set(component.members)
+        pending = list(component.members)
+
+        while pending:
+            current = pending.pop()
+            for target in adjacency[current]:
+                if target not in visited:
+                    visited.add(target)
+                    pending.append(target)
+
+        closure = tuple(sorted(visited))
+
+        yield _capture_closure(
+            root,
+            index,
+            component.members,
+            closure,
+            max_source_bytes=max_source_bytes,
+            max_closure_bytes=max_closure_bytes,
+            executor=executor,
+        )
```

## tests/test_cycle_semantics_selective_worker_capture.py

```diff
diff --git a/tests/test_cycle_semantics_selective_worker_capture.py b/tests/test_cycle_semantics_selective_worker_capture.py
new file mode 100644
index 0000000..874fdf8
--- /dev/null
+++ b/tests/test_cycle_semantics_selective_worker_capture.py
@@ -0,0 +1,434 @@
+"""P1D1B selective SCC worker-source capture regressions."""
+
+from __future__ import annotations
+
+import hashlib
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.analysis.process_pool_lifecycle import (
+    managed_reusable_process_pool,
+    terminate_active_process_pools,
+)
+from contextor.core.cycle_semantics import (
+    selective_worker_capture as capture,
+)
+from contextor.core.graph.graph import build_graph
+from contextor.core.symbol_engine.indexer import (
+    index_repository,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_initial_index(monkeypatch):
+    monkeypatch.setenv(
+        "CONTEXTOR_DISABLE_PROCESS_POOL", "1"
+    )
+
+
+def _repo(tmp_path):
+    root = tmp_path / "repo"
+    pkg = root / "pkg"
+    pkg.mkdir(parents=True)
+    contents = {
+        "__init__.py": b"",
+        "a.py": b"import pkg.b\nimport pkg.helper\n",
+        "b.py": b"import pkg.a\n",
+        "helper.py": b"value = 1\n",
+        "unrelated.py": b"value = 999\n",
+    }
+    for name, raw in contents.items():
+        (pkg / name).write_bytes(raw)
+    return root
+
+
+def _analyze(root):
+    index = index_repository(str(root))
+    graph = build_graph(index.modules)
+    return index, graph.hard_edges
+
+
+def _results(root, index, edges, **kwargs):
+    return tuple(
+        capture.iter_selective_scc_worker_captures(
+            root,
+            edges,
+            index,
+            **kwargs,
+        )
+    )
+
+
+def _assert_complete(item, index):
+    assert item.status == (
+        "WORKER_SECOND_PASS_BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
+    )
+    assert item.reason is None
+    assert set(item.source_snapshots) == set(
+        item.reachable_modules
+    )
+    assert set(dict(item.ast_modes)) == set(
+        item.reachable_modules
+    )
+    assert item.retained_raw_bytes == sum(
+        len(source.raw)
+        for source in item.source_snapshots.values()
+    )
+    for module_id, source in item.source_snapshots.items():
+        assert hashlib.sha256(source.raw).hexdigest() == (
+            index.source_fingerprints_by_module[module_id]
+        )
+    assert "SECOND_PASS" in item.authority
+    assert "NOT_ORIGINAL_FULL_INDEX" in item.authority
+    assert "NOT_LIVE_CERTIFIED" in item.authority
+
+
+def test_p1d1b_t01_only_scc_closure_replayed(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+
+    (item,) = _results(root, index, edges)
+
+    assert item.members == ("pkg.a", "pkg.b")
+    assert "pkg.helper" in item.reachable_modules
+    assert "pkg.unrelated" not in item.reachable_modules
+    _assert_complete(item, index)
+
+
+def test_p1d1b_t02_warm_cache_mode_is_explicit(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+
+    (item,) = _results(root, index, edges)
+
+    _assert_complete(item, index)
+    assert set(dict(item.ast_modes).values()).issubset({
+        "CACHE_SHA256_EQUIVALENT",
+        "PARSED_FROM_WORKER_READ",
+    })
+
+
+def test_p1d1b_t03_real_process_pool_capture(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+
+    try:
+        with managed_reusable_process_pool(
+            "indexer"
+        ) as (executor, _, _):
+            (item,) = _results(
+                root, index, edges, executor=executor
+            )
+        _assert_complete(item, index)
+    finally:
+        terminate_active_process_pools(timeout=1.0)
+
+
+def test_p1d1b_t04_post_index_source_drift_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+
+    (root / "pkg" / "a.py").write_bytes(
+        b"import pkg.b\nvalue = 123\n"
+    )
+
+    (item,) = _results(root, index, edges)
+
+    assert item.status == "UNAVAILABLE"
+    assert item.reason == (
+        "WORKER_INDEX_BYTES_MISMATCH:pkg.a"
+    )
+    assert item.source_snapshots == {}
+    assert item.retained_raw_bytes == 0
+
+
+def test_p1d1b_t05_per_source_budget_blocks_worker(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+    observed = []
+
+    def forbidden(*args, **kwargs):
+        observed.append(True)
+        raise AssertionError("worker must not execute")
+
+    monkeypatch.setattr(
+        capture, "_process_single_file", forbidden
+    )
+
+    (item,) = _results(
+        root, index, edges, max_source_bytes=4
+    )
+
+    assert item.status == "UNAVAILABLE"
+    assert item.reason.startswith(
+        "SOURCE_BYTE_BUDGET_EXCEEDED:"
+    )
+    assert observed == []
+    assert item.source_snapshots == {}
+
+
+def test_p1d1b_t06_cumulative_closure_budget_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+    (complete,) = _results(root, index, edges)
+    _assert_complete(complete, index)
+
+    total = complete.retained_raw_bytes
+    assert total > 1
+    del complete
+
+    (limited,) = _results(
+        root,
+        index,
+        edges,
+        max_source_bytes=1024,
+        max_closure_bytes=total - 1,
+    )
+
+    assert limited.status == "UNAVAILABLE"
+    assert limited.reason.startswith(
+        "SOURCE_BYTE_BUDGET_EXCEEDED:"
+    )
+    assert limited.source_snapshots == {}
+    assert limited.ast_modes == ()
+    assert limited.retained_raw_bytes == 0
+
+
+def test_p1d1b_t07_missing_index_member_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+    modules = dict(index.modules)
+    modules.pop("pkg.helper")
+    incomplete = replace(index, modules=modules)
+
+    (item,) = _results(root, incomplete, edges)
+
+    assert item.status == "UNAVAILABLE"
+    assert item.reason == "MODULE_NOT_INDEXED:pkg.helper"
+    assert not item.source_snapshots
+
+
+def test_p1d1b_t08_import_forgery_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+    modules = dict(index.modules)
+    modules["pkg.a"] = replace(
+        modules["pkg.a"], imports=[]
+    )
+
+    (item,) = _results(
+        root, replace(index, modules=modules), edges
+    )
+
+    assert item.status == "UNAVAILABLE"
+    assert item.reason == (
+        "WORKER_INDEX_IMPORTS_MISMATCH:pkg.a"
+    )
+    assert not item.source_snapshots
+
+
+def test_p1d1b_t09_index_fingerprint_missing(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+    hashes = dict(index.source_fingerprints_by_module)
+    hashes.pop("pkg.a")
+
+    (item,) = _results(
+        root,
+        replace(
+            index,
+            source_fingerprints_by_module=hashes,
+        ),
+        edges,
+    )
+
+    assert item.status == "UNAVAILABLE"
+    assert item.reason == (
+        "INDEX_FINGERPRINT_UNAVAILABLE:pkg.a"
+    )
+
+
+def test_p1d1b_t10_unrelated_files_not_replayed(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    for number in range(250):
+        (root / "pkg" / f"unused_{number:04d}.py").write_text(
+            f"value = {number}\n",
+            encoding="utf-8",
+        )
+
+    index, edges = _analyze(root)
+    observed = []
+    original = capture._process_single_file
+
+    def traced(path, *args, **kwargs):
+        observed.append(path)
+        return original(path, *args, **kwargs)
+
+    monkeypatch.setattr(
+        capture, "_process_single_file", traced
+    )
+
+    (item,) = _results(root, index, edges)
+
+    _assert_complete(item, index)
+    assert observed
+    assert not any(
+        "unused_" in path for path in observed
+    )
+
+
+def test_p1d1b_t11_independent_scc_budgets(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    other = root / "other"
+    other.mkdir()
+    (other / "__init__.py").write_bytes(b"")
+    (other / "a.py").write_bytes(b"import other.b\n")
+    (other / "b.py").write_bytes(b"import other.a\n")
+
+    index, edges = _analyze(root)
+    outcomes = {
+        item.members: item
+        for item in capture.iter_selective_scc_worker_captures(
+            root,
+            edges,
+            index,
+            max_source_bytes=128,
+            max_closure_bytes=32,
+        )
+    }
+
+    assert set(outcomes) == {
+        ("pkg.a", "pkg.b"),
+        ("other.a", "other.b"),
+    }
+
+    assert outcomes[("pkg.a", "pkg.b")].status == (
+        "UNAVAILABLE"
+    )
+    small = outcomes[("other.a", "other.b")]
+    _assert_complete(small, index)
+    assert small.retained_raw_bytes <= 32
+
+
+def test_p1d1b_t12_forged_worker_origin_rejected(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+    original = capture._process_single_file
+
+    def forged(*args, **kwargs):
+        result = original(*args, **kwargs)
+        result["source_capture_origin"] = "FAKE"
+        return result
+
+    monkeypatch.setattr(
+        capture, "_process_single_file", forged
+    )
+
+    (item,) = _results(root, index, edges)
+
+    assert item.status == "UNAVAILABLE"
+    assert item.reason.startswith(
+        "WORKER_CAPTURE_ORIGIN_INVALID:"
+    )
+    assert item.source_snapshots == {}
+
+
+def test_p1d1b_t13_acyclic_graph_has_no_capture(
+    tmp_path, isolated_dirs,
+):
+    root = tmp_path / "repo"
+    root.mkdir()
+    (root / "a.py").write_bytes(b"value = 1\n")
+    index, edges = _analyze(root)
+
+    assert _results(root, index, edges) == ()
+
+
+def test_p1d1b_t14_invalid_limits_rejected(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+
+    for kwargs in (
+        {"max_source_bytes": 0},
+        {"max_source_bytes": True},
+        {"max_source_bytes": 65 * 1024 * 1024},
+        {"max_closure_bytes": 0},
+        {"max_closure_bytes": True},
+        {"max_closure_bytes": 257 * 1024 * 1024},
+    ):
+        with pytest.raises(ValueError):
+            _results(root, index, edges, **kwargs)
+
+
+def test_p1d1b_t15_worker_exception_fails_closed(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+
+    def fail(*args, **kwargs):
+        raise RuntimeError("injected worker failure")
+
+    monkeypatch.setattr(
+        capture, "_process_single_file", fail
+    )
+
+    (item,) = _results(root, index, edges)
+
+    assert item.status == "UNAVAILABLE"
+    assert item.reason.startswith(
+        "WORKER_EXECUTION_FAILED:"
+    )
+    assert item.source_snapshots == {}
+
+
+def test_p1d1b_t16_worker_module_identity_fails_closed(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    index, edges = _analyze(root)
+    original = capture._process_single_file
+
+    def forged(*args, **kwargs):
+        result = original(*args, **kwargs)
+        result["module_id"] = "forged.module"
+        return result
+
+    monkeypatch.setattr(
+        capture, "_process_single_file", forged
+    )
+
+    (item,) = _results(root, index, edges)
+
+    assert item.status == "UNAVAILABLE"
+    assert item.reason.startswith(
+        "WORKER_IDENTITY_MISMATCH:"
+    )
+    assert item.source_snapshots == {}
```

# FINAL_VERDICT
FINAL PASS for the exact P1D1B implementation and required targeted gates. Two LIVE identical-definition collision diagnostics remain as a disclosed result of the approved exact patch; existing-process loaded-code adoption and stronger source authority are not certified.
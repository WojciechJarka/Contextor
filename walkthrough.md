# CONTEXTOR_P1D2C_ORIGINAL_WORKER_MANIFEST_PREPARATION

## PREFLIGHT_RESULT

- DIRECT_EVIDENCE: Required modules and symbols were present: P1D2B `assess_original_worker_cycle_closure` and P1C0 `prepare_cycle_source_manifest`. Both authorized new paths were absent before edits. P1D2A/P1D2B files were present; initial worktree was clean at HEAD `21c6b8649d5ad49dd9df957cc93f9f767a4140ba`.
- CODE_PATH_PROVED: Contextor MCP resolved P1D2B and P1C0 symbols at canonical revision 674 before edits; P1C0 source was verified.

## NATIVE_CODEX_EDITS

- DIRECT_EVIDENCE: Created the two authorized files with the native Codex file-editing tool. Read-only comparison to the attachment reported `EXACT_MATCH` for both files: 161 lines and 277 lines. No existing source/test file was edited.

## FILES_CHANGED

- `contextor/core/cycle_semantics/original_worker_preparation.py` (new)
- `tests/test_original_worker_manifest_preparation.py` (new)
- `walkthrough.md` (this report; excluded from source/test diff requirement)

## ACTUAL_SOURCE_AND_TEST_DIFFS

### `contextor/core/cycle_semantics/original_worker_preparation.py`

```diff
diff --git a/contextor/core/cycle_semantics/original_worker_preparation.py b/contextor/core/cycle_semantics/original_worker_preparation.py
new file mode 100644
index 0000000..067aa94
--- /dev/null
+++ b/contextor/core/cycle_semantics/original_worker_preparation.py
@@ -0,0 +1,161 @@
+"""Prepare P1C0 evidence from selected original indexer worker bytes.
+
+This is caller-supplied, non-atomic, in-memory evidence preparation.
+It does not establish canonical ownership, publication, installed LIVE
+identity, original cross-file atomicity, or runtime import safety.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from contextor.core.source import (
+    SourceError,
+    parse_source_snapshot,
+)
+
+from .contracts import CycleSemanticsSnapshot
+from .evidence import build_source_bound_cycle_evidence
+from .generation_manifest import (
+    PreparedCycleSourceManifest,
+    prepare_cycle_source_manifest,
+)
+from .original_worker_binding import (
+    assess_original_worker_cycle_closure,
+)
+
+
+@dataclass(frozen=True)
+class OriginalWorkerManifestPreparation:
+    status: str
+    reason: str | None
+    manifest: PreparedCycleSourceManifest | None
+    source_modules: tuple[str, ...]
+
+
+def prepare_original_worker_cycle_manifest(
+    index: object,
+    hard_edges: Mapping[str, object],
+    snapshot: CycleSemanticsSnapshot,
+) -> OriginalWorkerManifestPreparation:
+    """Prepare a non-published manifest from supplied original-worker bytes.
+
+    The existing P1D2B binding owns selection and byte fingerprint checks.
+    Existing P0/P1B/P1C0 functions own graph/model, byte/AST and manifest
+    consistency checks.
+
+    No filesystem reading, worker execution, canonical mutation, store
+    operation, receipt sealing, LIVE IPC or generation certification occurs.
+    """
+
+    if type(snapshot) is not CycleSemanticsSnapshot:
+        raise TypeError(
+            "snapshot must be CycleSemanticsSnapshot"
+        )
+
+    def unavailable(
+        reason: str,
+    ) -> OriginalWorkerManifestPreparation:
+        return OriginalWorkerManifestPreparation(
+            status="UNAVAILABLE",
+            reason=reason,
+            manifest=None,
+            source_modules=(),
+        )
+
+    binding = assess_original_worker_cycle_closure(
+        index,
+        hard_edges,
+    )
+
+    if binding.status != (
+        "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
+    ):
+        return unavailable(
+            "BINDING_" + (
+                binding.reason
+                or "UNAVAILABLE"
+            )
+        )
+
+    try:
+        parsed_sources = {
+            module_id: parse_source_snapshot(
+                binding.source_snapshots[module_id],
+                module_id,
+            )
+            for module_id in binding.reachable_modules
+        }
+    except (
+        SourceError,
+        SyntaxError,
+        ValueError,
+        TypeError,
+        RecursionError,
+        OverflowError,
+    ):
+        return unavailable(
+            "ORIGINAL_SOURCE_AST_UNAVAILABLE"
+        )
+
+    try:
+        evidence = build_source_bound_cycle_evidence(
+            hard_edges,
+            parsed_sources,
+        )
+
+        manifest = prepare_cycle_source_manifest(
+            hard_edges,
+            index.source_fingerprints_by_module,
+            snapshot,
+            evidence,
+            binding.source_snapshots,
+        )
+    except (
+        SourceError,
+        SyntaxError,
+        ValueError,
+        TypeError,
+        RecursionError,
+        OverflowError,
+    ):
+        return unavailable(
+            "SOURCE_EVIDENCE_PREPARATION_FAILED"
+        )
+
+    if (
+        type(manifest.source_manifest_sha256) is not str
+        or len(manifest.source_manifest_sha256) != 64
+        or not manifest.components
+        or any(
+            component.preparation_state
+            != "PREPARED_UNPUBLISHED"
+            for component in manifest.components
+        )
+    ):
+        return unavailable(
+            "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+        )
+
+    if manifest.authority != (
+        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+    ):
+        return unavailable(
+            "PREPARED_AUTHORITY_INVALID"
+        )
+
+    if tuple(
+        component.members
+        for component in manifest.components
+    ) != binding.cyclic_components:
+        return unavailable(
+            "SCC_COMPONENT_IDENTITY_MISMATCH"
+        )
+
+    return OriginalWorkerManifestPreparation(
+        status="PREPARED_UNPUBLISHED_NON_ATOMIC",
+        reason=None,
+        manifest=manifest,
+        source_modules=binding.reachable_modules,
+    )
```

### `tests/test_original_worker_manifest_preparation.py`

```diff
diff --git a/tests/test_original_worker_manifest_preparation.py b/tests/test_original_worker_manifest_preparation.py
new file mode 100644
index 0000000..0a4c5fb
--- /dev/null
+++ b/tests/test_original_worker_manifest_preparation.py
@@ -0,0 +1,277 @@
+"""P1D2C: original-worker evidence reaches P1C0 preparation only."""
+
+from __future__ import annotations
+
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+from contextor.core.cycle_semantics.original_worker_preparation import (
+    prepare_original_worker_cycle_manifest,
+)
+from contextor.core.source import SourceSnapshot
+from contextor.core.symbol_engine.indexer import index_repository
+from tests.test_cycle_semantics_evidence import (
+    PAIR,
+    PASS,
+    _bound,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_index(monkeypatch):
+    monkeypatch.setenv(
+        "CONTEXTOR_DISABLE_PROCESS_POOL",
+        "1",
+    )
+
+
+def _repo(tmp_path):
+    root = tmp_path / "repo"
+    root.mkdir()
+    for module_id, source in PASS.items():
+        (root / f"{module_id}.py").write_bytes(
+            source.encode("utf-8")
+        )
+    return root
+
+
+def _index(root, *selected):
+    return index_repository(
+        str(root),
+        source_capture_module_ids=frozenset(selected),
+    )
+
+
+def _snapshot():
+    return _bound(PAIR, PASS)[1]
+
+
+def _prepare(index, snapshot=None, graph=None):
+    return prepare_original_worker_cycle_manifest(
+        index,
+        PAIR if graph is None else graph,
+        _snapshot() if snapshot is None else snapshot,
+    )
+
+
+def test_p1d2c_t01_original_bytes_prepare_unpublished_manifest(
+    tmp_path, isolated_dirs,
+):
+    index = _index(_repo(tmp_path), "a", "b")
+    result = _prepare(index)
+
+    assert result.status == (
+        "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    )
+    assert result.reason is None
+    assert result.source_modules == ("a", "b")
+
+    manifest = result.manifest
+    assert manifest is not None
+    assert manifest.source_manifest_sha256 is not None
+    assert len(manifest.source_manifest_sha256) == 64
+    assert manifest.authority == (
+        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+    )
+    assert len(manifest.components) == 1
+    assert manifest.components[0].members == ("a", "b")
+    assert manifest.components[0].preparation_state == (
+        "PREPARED_UNPUBLISHED"
+    )
+
+
+def test_p1d2c_t02_default_capture_remains_unavailable(
+    tmp_path, isolated_dirs,
+):
+    index = index_repository(str(_repo(tmp_path)))
+    result = _prepare(index)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == (
+        "BINDING_INDEX_CAPTURE_NOT_COMPLETE"
+    )
+    assert result.manifest is None
+    assert result.source_modules == ()
+
+
+def test_p1d2c_t03_missing_capture_cannot_prepare(
+    tmp_path, isolated_dirs,
+):
+    index = _index(_repo(tmp_path), "a")
+    result = _prepare(index)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == (
+        "BINDING_CLOSURE_CAPTURE_MISSING:b"
+    )
+    assert result.manifest is None
+
+
+def test_p1d2c_t04_modified_worker_bytes_rejected(
+    tmp_path, isolated_dirs,
+):
+    index = _index(_repo(tmp_path), "a", "b")
+    altered = dict(index.original_worker_source_snapshots)
+    previous = altered["a"]
+
+    altered["a"] = SourceSnapshot(
+        raw=b"forged",
+        source_fingerprint=previous.source_fingerprint,
+    )
+
+    result = _prepare(
+        replace(
+            index,
+            original_worker_source_snapshots=altered,
+        )
+    )
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == (
+        "BINDING_CLOSURE_SOURCE_DIGEST_MISMATCH:a"
+    )
+    assert result.manifest is None
+
+
+def test_p1d2c_t05_inconsistent_semantic_graph_rejected(
+    tmp_path, isolated_dirs,
+):
+    index = _index(_repo(tmp_path), "a", "b")
+    snapshot = replace(
+        _snapshot(),
+        graph_sha256="0" * 64,
+    )
+
+    result = _prepare(index, snapshot=snapshot)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == (
+        "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+    )
+    assert result.manifest is None
+
+
+def test_p1d2c_t06_partial_semantics_rejected(
+    tmp_path, isolated_dirs,
+):
+    index = _index(_repo(tmp_path), "a", "b")
+    snapshot = replace(
+        _snapshot(),
+        coverage_status="PARTIAL_SOURCE_EVIDENCE",
+        source_issues=(
+            ("a", "SOURCE_CHANGED_DURING_READ"),
+        ),
+    )
+
+    result = _prepare(index, snapshot=snapshot)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == (
+        "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+    )
+    assert result.manifest is None
+
+
+def test_p1d2c_t07_no_cyclic_component_no_manifest(
+    tmp_path, isolated_dirs,
+):
+    index = _index(_repo(tmp_path), "a", "b")
+    graph = {
+        "a": {"b"},
+        "b": set(),
+    }
+
+    result = _prepare(index, graph=graph)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == (
+        "BINDING_NO_CYCLIC_COMPONENTS"
+    )
+    assert result.manifest is None
+
+
+def test_p1d2c_t08_warm_cache_is_explicit(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index_repository(str(root))
+    index = _index(root, "a", "b")
+
+    assert set(
+        index.original_worker_ast_modes.values()
+    ) == {
+        "CACHE_SHA256_EQUIVALENT",
+    }
+
+    result = _prepare(index)
+
+    assert result.status == (
+        "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    )
+    assert result.manifest is not None
+
+
+def test_p1d2c_t09_no_filesystem_read_during_preparation(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    index = _index(_repo(tmp_path), "a", "b")
+    snapshot = _snapshot()
+
+    def forbidden_read(self):
+        raise AssertionError(
+            "manifest preparation attempted filesystem read"
+        )
+
+    monkeypatch.setattr(
+        Path,
+        "read_bytes",
+        forbidden_read,
+    )
+
+    result = _prepare(
+        index,
+        snapshot=snapshot,
+    )
+
+    assert result.status == (
+        "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    )
+
+
+def test_p1d2c_t10_invalid_snapshot_rejected(
+    tmp_path, isolated_dirs,
+):
+    index = _index(_repo(tmp_path), "a", "b")
+
+    with pytest.raises(TypeError):
+        prepare_original_worker_cycle_manifest(
+            index,
+            PAIR,
+            None,
+        )
+
+
+def test_p1d2c_t11_deterministic_preparation(
+    tmp_path, isolated_dirs,
+):
+    index = _index(_repo(tmp_path), "a", "b")
+    snapshot = _snapshot()
+
+    before = repr((index, snapshot))
+
+    first = _prepare(
+        index,
+        snapshot=snapshot,
+    )
+    second = _prepare(
+        index,
+        snapshot=snapshot,
+    )
+
+    assert first == second
+    assert first.status == (
+        "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    )
+    assert repr((index, snapshot)) == before
```

## P1D2C_TEST_RESULTS

- DIRECT_EVIDENCE: Exact requested command returned exit 0: `136 passed in 14.55s`. No failures.

## FOCUSED_NON_REGRESSION

- DIRECT_EVIDENCE: `pytest -q tests/test_original_worker_manifest_preparation.py tests/test_original_worker_cycle_closure_binding.py tests/test_indexer_original_capture_handoff.py tests/test_indexer_worker_source_capture.py tests/test_cycle_semantics_selective_worker_capture.py tests/test_cycle_semantics_evidence.py` completed with 136 passed. No FULL analysis or active-repository capture worker was run.

## PY_COMPILE_RESULTS

- DIRECT_EVIDENCE: `py_compile` on both newly created files returned exit 0.
- DIRECT_EVIDENCE: New files passed `git diff --no-index --check` with no whitespace diagnostics (exit 1 reflects comparison against `/dev/null`). Tracked `git diff --check` returned 0. Git emitted only its LF-to-CRLF checkout warning.

## CANONICAL_WATCHER_OBSERVATIONS

- DIRECT_EVIDENCE: Pre-edit canonical revision 674. Continuous watcher events: revision 675 `UPDATED` for `original_worker_preparation.py`; revision 676 `UPDATED` for its test. `resync_required=false`.
- DIRECT_EVIDENCE: At revision 676, Contextor read-only `get_symbol_implementation(mode=preview)` resolved both new symbols with `workspace_sync=verified`; cycles fresh, count 16; `cycle_semantics=stale`. No manual `update_file` or forced refresh was used.

## PREPARED_MANIFEST_AUTHORITY_LIMITS

- CODE_PATH_PROVED: New function consumes caller-supplied P1D2B binding, parses the captured bytes in memory, builds source-bound evidence and calls existing P1C0 preparation. It fails closed on binding, parsing, evidence, authority, digest-shape and SCC identity failures.
- CONTRACT_PROVED: Tests cover successful prepared-only manifest, default/missing/tampered capture, graph and partial-semantic mismatch, no cycle, warm-cache label, no filesystem read during preparation, invalid snapshot type and deterministic/nonmutating behavior.
- DIRECT_EVIDENCE: Returned authority remains `PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED`; preparation state remains `PREPARED_UNPUBLISHED`. This does not create a durable receipt, publish a generation, authenticate graph ownership, establish cross-file source atomicity, certify an installed LIVE generation or establish runtime import safety.

## UNVERIFIED_RUNTIME_BEHAVIOR

- UNKNOWN: Whether the active runtime loaded the new implementation. Watcher indexing and verified source sync prove indexed disk content only. No restart, reload, publication, LIVE generation certification or runtime import-safety action was performed.

## FINAL_VERDICT

P1D2C completed within its exact two-file scope. Literal source comparison, compilation, 136 focused tests and watcher verification passed. Evidence supports PREPARED ONLY, NON_ATOMIC behavior; publication and runtime certification remain unclaimed. STOP after P1D2C.

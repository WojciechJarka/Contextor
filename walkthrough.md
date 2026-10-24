# TASK
P1D1C_WORKER_CAPTURE_COMMITTED_CLAIM_BINDING — exact auditor-supplied two-file implementation.

# HEAD_BEFORE
b9919f1cef1096b6f70140917abd547c81bacdaa; clean working tree; both approved new files absent.

# HEAD_AFTER
b9919f1cef1096b6f70140917abd547c81bacdaa; no commit.

# FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\core\cycle_semantics\worker_claim_binding.py
- C:\Temp\Contextor_Repo\tests\test_cycle_semantics_worker_claim_binding.py

# ARCHITECTURAL_DEPENDENCIES
CONTRACT_PROVED (Contextor MCP, pre-edit revision 660, source workspace_sync=verified): CanonicalCycleManifestReceipt and verify_co_published_cycle_manifest are owned by publication_binding.py; PreparedCycleSourceManifest by generation_manifest.py; LiveStateMetadata by live_state/store.py; RepositoryAnalysisState by analysis/state_manager.py; SCCWorkerCapture by selective_worker_capture.py; parse_source_snapshot by source.py. Existing verifier confirmed direct consumers include live_state/store.py and two publication tests. Its contract reseals the supplied prepared manifest against exact revision, state_id, repo_id and root_path, then compares the receipt. No new publication or receipt path added.

# T01_T18_RESULTS
DIRECT_EVIDENCE: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_worker_claim_binding.py => 18 passed in 6.94s.

# FOCUSED_NON_REGRESSION
DIRECT_EVIDENCE: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_selective_worker_capture.py tests/test_cycle_semantics_publication_binding.py tests/test_cycle_semantics_publication_live_integration.py tests/test_cycle_semantics_evidence.py => 114 passed in 18.38s. No full suite run.

# COMMITTED_RECEIPT_VERIFICATION
CODE_PATH_PROVED: assessor requires exact CanonicalCycleManifestReceipt and calls existing verify_co_published_cycle_manifest; T01 uses an actual save_snapshot/load_snapshot committed fixture and returns DECLARED_BYTES_MATCH_COMMITTED_PREPARED_CLAIMS. T02, T05–T08 reject absent receipt, foreign repo/root, stale semantics and changed graph. Positive status remains conditional on caller-supplied authentic state and metadata.

# EXACT_GENERATION_IDENTITY
CODE_PATH_PROVED: metadata revision, state_id, repo_id and root_path are validated; state revision/state_id must match metadata, then receipt verifier reseals exact committed identity. T03–T06 cover mismatches. Boolean revision is rejected by exact type check.

# SCC_CLOSURE_AND_SOURCE_HASH_EVIDENCE
CODE_PATH_PROVED: exact SCC members locate one prepared component; closure/module order, snapshots, AST modes, worker status/authority and retained-byte accounting are checked. Worker raw SHA-256 must equal both SourceSnapshot fingerprint and committed prepared source signature. T09–T16 fail closed for closure, altered bytes, authority, failure, membership, byte budget and accounting.

# AST_RECOMPUTATION_EVIDENCE
CODE_PATH_PROVED: parse_source_snapshot parses supplied captured bytes in memory; ast.dump(include_attributes=True) SHA-256 is compared with prepared AST signature. T01 positive fixture and T17 invalid AST mode gate passed. No independent original-FULL-byte provenance is inferred.

# FAIL_CLOSED_REGRESSIONS
DIRECT_EVIDENCE: T02–T17 all passed with UNAVAILABLE or ValueError on their specified invalid input, generation, receipt, closure, source, budget and accounting cases. No failed gate produced a positive binding_state.

# NO_IO_AND_NO_PUBLICATION
CODE_PATH_PROVED: production assessor has no filesystem read, snapshot-store call, LIVE IPC, worker scheduling, graph mutation or publication call. T18 monkeypatches Path.read_bytes/read_text to raise during assessment and still passes. The test fixture itself writes and loads a temporary snapshot before this assertion; the production verifier does not. The supplied state origin is not independently authenticated.

# LIVE_REVISION_BEFORE_AFTER
660 → 662; activity_epoch fafa60a0964a48499f00c8e2fa983cd0; get_live_events(after_revision=660) continuity=continuous, resync_required=false, total=2, truncated=false.

# WATCHER_EVENTS
DIRECT_EVIDENCE: desktop_watcher update_file UPDATED revision 661 for worker_claim_binding.py and revision 662 for test_cycle_semantics_worker_claim_binding.py. No manual update_file, FULL analysis or restart.

# WORKSPACE_SYNC
DIRECT_EVIDENCE: Contextor get_module_context for both new files at revision 662: canonical_state=fresh, workspace_sync=verified, advisory_warning=null. Cycle_semantics family separately remains stale.

# COLLISION_DIAGNOSTICS
DIRECT_EVIDENCE: canonical get_name_collisions before and after reports total=2, both older NAME_COLLISION warnings for profiling scope run_scope and PRESETS. No new active collision warning from either P1D1C file.

# AUTHORITY_LIMITATIONS
Positive status is declaration consistency against a caller-supplied committed receipt and state. It does not authenticate caller or LIVE state origin, prove original FULL source bytes, repository-wide atomicity or runtime safety, and does not classify an SCC SAFE. No canonical publication or warning suppression was introduced.

# RESTART_REQUIREMENTS
No process restarted. Fresh Python tests exercised new code; existing Desktop/MCP/LIVE loaded-code adoption is not certified by watcher indexing. A manual reload may be needed before an already-running process imports the new module.

# WHITESPACE_CHECK
py_compile passed for both files; git diff --check and git diff --no-index --check for each new file passed. Both files end in LF and have no trailing-whitespace lines. Git emitted only future LF→CRLF working-copy warnings.

# FULL_DIFFS

## contextor/core/cycle_semantics/worker_claim_binding.py

```diff
diff --git a/contextor/core/cycle_semantics/worker_claim_binding.py b/contextor/core/cycle_semantics/worker_claim_binding.py
new file mode 100644
index 0000000..972bbda
--- /dev/null
+++ b/contextor/core/cycle_semantics/worker_claim_binding.py
@@ -0,0 +1,300 @@
+"""Compare worker second-pass bytes with committed SCC claims.
+
+The state and metadata are supplied by the caller.
+Only an already co-published prepared manifest can be used.
+
+This module authenticates neither the caller nor the state origin.
+It never promotes source equivalence to import-runtime safety.
+"""
+
+from __future__ import annotations
+
+import ast
+import hashlib
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from contextor.core.analysis.state_manager import (
+    RepositoryAnalysisState,
+)
+from contextor.core.live_state.store import LiveStateMetadata
+from contextor.core.source import (
+    SourceSnapshot,
+    parse_source_snapshot,
+)
+
+from .publication_binding import (
+    CanonicalCycleManifestReceipt,
+    verify_co_published_cycle_manifest,
+)
+from .selective_worker_capture import (
+    SCCWorkerCapture,
+    WORKER_CAPTURE_AUTHORITY,
+)
+
+
+WORKER_CLAIM_BINDING_AUTHORITY = (
+    "CALLER_SUPPLIED_STATE_COMMITTED_CLAIM_COMPARISON"
+    "_NOT_SOURCE_OR_LIVE_ORIGIN_AUTHENTICATED"
+    "_NOT_RUNTIME_SAFETY"
+)
+
+_CAPTURE_STATUS = (
+    "WORKER_SECOND_PASS_BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
+)
+
+_MATCH = "DECLARED_BYTES_MATCH_COMMITTED_PREPARED_CLAIMS"
+
+_AST_MODES = frozenset({
+    "PARSED_FROM_WORKER_READ",
+    "CACHE_SHA256_EQUIVALENT",
+})
+
+
+@dataclass(frozen=True)
+class WorkerCommittedClaimAssessment:
+    members: tuple[str, ...]
+    binding_state: str
+    reason: str | None
+    canonical_revision: int | None
+    state_id: str | None
+    graph_sha256: str | None
+    authority: str = WORKER_CLAIM_BINDING_AUTHORITY
+
+
+def assess_worker_capture_committed_claim(
+    state: RepositoryAnalysisState,
+    metadata: LiveStateMetadata,
+    capture: SCCWorkerCapture,
+    *,
+    max_source_bytes: int = 2 * 1024 * 1024,
+    max_closure_bytes: int = 32 * 1024 * 1024,
+) -> WorkerCommittedClaimAssessment:
+    """Verify one complete SCC capture against co-published claims.
+
+    No filesystem access, IPC, state mutation, worker execution,
+    LIVE freshness lookup or safety classification.
+
+    Matching means declaration consistency only. The receipt
+    is not proof of original source-byte provenance.
+    """
+    if (
+        type(max_source_bytes) is not int
+        or not 1 <= max_source_bytes <= 64 * 1024 * 1024
+        or type(max_closure_bytes) is not int
+        or not 1 <= max_closure_bytes <= 256 * 1024 * 1024
+    ):
+        raise ValueError("invalid worker claim byte budget")
+
+    members = (
+        capture.members
+        if type(capture) is SCCWorkerCapture
+        and type(capture.members) is tuple
+        else ()
+    )
+    revision = (
+        metadata.revision
+        if type(metadata) is LiveStateMetadata
+        and type(metadata.revision) is int
+        else None
+    )
+    state_id = (
+        metadata.state_id
+        if type(metadata) is LiveStateMetadata
+        and type(metadata.state_id) is str
+        else None
+    )
+
+    def unavailable(
+        reason: str,
+        graph_hash: str | None = None,
+    ) -> WorkerCommittedClaimAssessment:
+        return WorkerCommittedClaimAssessment(
+            members=members,
+            binding_state="UNAVAILABLE",
+            reason=reason,
+            canonical_revision=revision,
+            state_id=state_id,
+            graph_sha256=graph_hash,
+        )
+
+    if (
+        type(state) is not RepositoryAnalysisState
+        or type(metadata) is not LiveStateMetadata
+        or type(capture) is not SCCWorkerCapture
+    ):
+        return unavailable("INVALID_INPUT_CONTRACT")
+
+    if (
+        type(metadata.revision) is not int
+        or metadata.revision < 1
+        or type(metadata.state_id) is not str
+        or not metadata.state_id
+        or type(metadata.repo_id) is not str
+        or not metadata.repo_id
+        or type(metadata.root_path) is not str
+        or not metadata.root_path
+    ):
+        return unavailable("COMMITTED_IDENTITY_UNAVAILABLE")
+
+    if (
+        getattr(state, "revision", None)
+        != metadata.revision
+        or getattr(state, "state_id", None)
+        != metadata.state_id
+    ):
+        return unavailable("GENERATION_IDENTITY_MISMATCH")
+
+    receipt = getattr(
+        state, "cycle_source_publication", None
+    )
+    if type(receipt) is not CanonicalCycleManifestReceipt:
+        return unavailable("CO_PUBLISHED_RECEIPT_UNAVAILABLE")
+
+    try:
+        valid = verify_co_published_cycle_manifest(
+            state,
+            revision=metadata.revision,
+            state_id=metadata.state_id,
+            repo_id=metadata.repo_id,
+            root_path=metadata.root_path,
+        )
+    except (ValueError, TypeError, KeyError, AttributeError):
+        valid = False
+
+    if not valid:
+        return unavailable("CO_PUBLISHED_RECEIPT_INVALID")
+
+    manifest = receipt.prepared_manifest
+    graph_hash = manifest.graph_sha256
+
+    if (
+        capture.status != _CAPTURE_STATUS
+        or capture.reason is not None
+        or capture.authority != WORKER_CAPTURE_AUTHORITY
+    ):
+        return unavailable(
+            "WORKER_CAPTURE_NOT_ACCEPTED", graph_hash
+        )
+
+    prepared = next(
+        (
+            item
+            for item in manifest.components
+            if item.members == members
+        ),
+        None,
+    )
+    if prepared is None:
+        return unavailable(
+            "SCC_NOT_IN_COMMITTED_MANIFEST", graph_hash
+        )
+
+    signatures = prepared.source_signatures
+    expected_modules = tuple(
+        name for name, _, _ in signatures
+    )
+
+    if (
+        capture.reachable_modules != expected_modules
+        or not isinstance(capture.source_snapshots, Mapping)
+        or set(capture.source_snapshots)
+        != set(expected_modules)
+        or type(capture.ast_modes) is not tuple
+        or tuple(name for name, _ in capture.ast_modes)
+        != expected_modules
+        or any(
+            type(mode) is not str or mode not in _AST_MODES
+            for _, mode in capture.ast_modes
+        )
+    ):
+        return unavailable(
+            "SCC_CLOSURE_INCOMPLETE_OR_MISMATCHED",
+            graph_hash,
+        )
+
+    total = 0
+
+    for module, expected_raw, expected_ast in signatures:
+        supplied = capture.source_snapshots[module]
+
+        if (
+            type(supplied) is not SourceSnapshot
+            or type(supplied.raw) is not bytes
+            or type(supplied.source_fingerprint) is not str
+        ):
+            return unavailable(
+                "WORKER_SOURCE_INVALID:" + module,
+                graph_hash,
+            )
+
+        size = len(supplied.raw)
+        if (
+            size > max_source_bytes
+            or total + size > max_closure_bytes
+        ):
+            return unavailable(
+                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module,
+                graph_hash,
+            )
+
+        total += size
+
+        actual_raw = hashlib.sha256(
+            supplied.raw
+        ).hexdigest()
+
+        if (
+            actual_raw != supplied.source_fingerprint
+            or actual_raw != expected_raw
+        ):
+            return unavailable(
+                "SOURCE_BYTES_CLAIM_MISMATCH:" + module,
+                graph_hash,
+            )
+
+        try:
+            parsed = parse_source_snapshot(
+                supplied, module
+            )
+            actual_ast = hashlib.sha256(
+                ast.dump(
+                    parsed.tree,
+                    include_attributes=True,
+                ).encode("utf-8")
+            ).hexdigest()
+        except (
+            ValueError,
+            TypeError,
+            SyntaxError,
+            RecursionError,
+            OverflowError,
+        ):
+            return unavailable(
+                "SOURCE_AST_UNAVAILABLE:" + module,
+                graph_hash,
+            )
+
+        if actual_ast != expected_ast:
+            return unavailable(
+                "SOURCE_AST_CLAIM_MISMATCH:" + module,
+                graph_hash,
+            )
+
+    if (
+        type(capture.retained_raw_bytes) is not int
+        or capture.retained_raw_bytes != total
+    ):
+        return unavailable(
+            "CAPTURE_BYTE_ACCOUNTING_MISMATCH",
+            graph_hash,
+        )
+
+    return WorkerCommittedClaimAssessment(
+        members=members,
+        binding_state=_MATCH,
+        reason=None,
+        canonical_revision=metadata.revision,
+        state_id=metadata.state_id,
+        graph_sha256=graph_hash,
+    )
```

## tests/test_cycle_semantics_worker_claim_binding.py

```diff
diff --git a/tests/test_cycle_semantics_worker_claim_binding.py b/tests/test_cycle_semantics_worker_claim_binding.py
new file mode 100644
index 0000000..9ba0b23
--- /dev/null
+++ b/tests/test_cycle_semantics_worker_claim_binding.py
@@ -0,0 +1,270 @@
+"""P1D1C — compare worker bytes with committed prepared claims."""
+
+from __future__ import annotations
+
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.cycle_semantics.worker_claim_binding import (
+    assess_worker_capture_committed_claim as assess,
+)
+from contextor.core.cycle_semantics.selective_worker_capture import (
+    iter_selective_scc_worker_captures,
+)
+from contextor.core.graph.graph import build_graph
+from contextor.core.live_state.store import (
+    load_snapshot,
+    save_snapshot,
+)
+from contextor.core.source import SourceSnapshot
+from contextor.core.symbol_engine.indexer import index_repository
+from tests.test_cycle_semantics_evidence import PASS
+from tests.test_cycle_semantics_publication_binding import _case
+
+
+@pytest.fixture
+def bound_case(tmp_path, isolated_dirs, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+    root = tmp_path / "repo"
+    root.mkdir()
+    for name, text in PASS.items():
+        (root / (name + ".py")).write_bytes(
+            text.encode("utf-8")
+        )
+
+    index = index_repository(str(root))
+    graph = build_graph(index.modules)
+
+    state, prepared = _case()
+    cache = tmp_path / "cache"
+
+    save_snapshot(
+        state,
+        cache,
+        "cycle-state",
+        repo_id="test-repo",
+        root_path=str(root.resolve()),
+        exact_revision=1,
+        file_state_payload={
+            "_meta": {
+                "state_id": "cycle-state",
+                "revision": 1,
+            },
+            "files": {},
+        },
+        prepared_cycle_manifest=prepared,
+    )
+
+    committed, metadata = load_snapshot(
+        cache, "cycle-state"
+    )
+
+    (captured,) = tuple(
+        iter_selective_scc_worker_captures(
+            root, graph.hard_edges, index
+        )
+    )
+
+    return committed, metadata, captured
+
+
+def test_p1d1c_t01_real_committed_claim_matches(bound_case):
+    state, meta, captured = bound_case
+    result = assess(state, meta, captured)
+
+    assert result.binding_state == (
+        "DECLARED_BYTES_MATCH_COMMITTED_PREPARED_CLAIMS"
+    )
+    assert result.reason is None
+    assert result.members == ("a", "b")
+    assert result.canonical_revision == 1
+    assert result.state_id == "cycle-state"
+    assert result.graph_sha256 == (
+        state.cycle_source_publication
+        .prepared_manifest.graph_sha256
+    )
+    assert "NOT_RUNTIME_SAFETY" in result.authority
+    assert "NOT_SOURCE_OR_LIVE_ORIGIN_AUTHENTICATED" in (
+        result.authority
+    )
+
+
+def test_p1d1c_t02_missing_receipt_unavailable(bound_case):
+    state, meta, captured = bound_case
+    state.cycle_source_publication = None
+    result = assess(state, meta, captured)
+    assert result.binding_state == "UNAVAILABLE"
+    assert result.reason == "CO_PUBLISHED_RECEIPT_UNAVAILABLE"
+
+
+def test_p1d1c_t03_wrong_revision_rejected(bound_case):
+    state, meta, captured = bound_case
+    result = assess(
+        state, replace(meta, revision=meta.revision + 1),
+        captured,
+    )
+    assert result.binding_state == "UNAVAILABLE"
+    assert result.reason == "GENERATION_IDENTITY_MISMATCH"
+
+
+def test_p1d1c_t04_wrong_state_id_rejected(bound_case):
+    state, meta, captured = bound_case
+    result = assess(
+        state, replace(meta, state_id="foreign-state"),
+        captured,
+    )
+    assert result.reason == "GENERATION_IDENTITY_MISMATCH"
+
+
+def test_p1d1c_t05_foreign_repo_rejected(bound_case):
+    state, meta, captured = bound_case
+    result = assess(
+        state, replace(meta, repo_id="foreign-repo"),
+        captured,
+    )
+    assert result.reason == "CO_PUBLISHED_RECEIPT_INVALID"
+
+
+def test_p1d1c_t06_foreign_root_rejected(bound_case):
+    state, meta, captured = bound_case
+    result = assess(
+        state, replace(meta, root_path="foreign-root"),
+        captured,
+    )
+    assert result.reason == "CO_PUBLISHED_RECEIPT_INVALID"
+
+
+def test_p1d1c_t07_stale_semantics_rejected(bound_case):
+    state, meta, captured = bound_case
+    state.cycle_semantics_state = "stale"
+    result = assess(state, meta, captured)
+    assert result.reason == "CO_PUBLISHED_RECEIPT_INVALID"
+
+
+def test_p1d1c_t08_changed_graph_rejected(bound_case):
+    state, meta, captured = bound_case
+    state.dependency_graph.hard_edges["a"] = set()
+    result = assess(state, meta, captured)
+    assert result.reason == "CO_PUBLISHED_RECEIPT_INVALID"
+
+
+def test_p1d1c_t09_missing_closure_member(bound_case):
+    state, meta, captured = bound_case
+    sources = dict(captured.source_snapshots)
+    sources.pop("b")
+    changed = replace(captured, source_snapshots=sources)
+    result = assess(state, meta, changed)
+    assert result.reason == (
+        "SCC_CLOSURE_INCOMPLETE_OR_MISMATCHED"
+    )
+
+
+def test_p1d1c_t10_mutated_bytes_rejected(bound_case):
+    state, meta, captured = bound_case
+    sources = dict(captured.source_snapshots)
+    original = sources["a"]
+    sources["a"] = SourceSnapshot(
+        raw=original.raw + b"\n",
+        source_fingerprint=original.source_fingerprint,
+    )
+    result = assess(
+        state, meta,
+        replace(captured, source_snapshots=sources),
+    )
+    assert result.reason == "SOURCE_BYTES_CLAIM_MISMATCH:a"
+
+
+def test_p1d1c_t11_invalid_capture_authority(bound_case):
+    state, meta, captured = bound_case
+    changed = replace(captured, authority="FORGED")
+    assert assess(state, meta, changed).reason == (
+        "WORKER_CAPTURE_NOT_ACCEPTED"
+    )
+
+
+def test_p1d1c_t12_failed_worker_capture_rejected(bound_case):
+    state, meta, captured = bound_case
+    changed = replace(
+        captured,
+        status="UNAVAILABLE",
+        reason="WORKER_EXECUTION_FAILED:a",
+    )
+    assert assess(state, meta, changed).reason == (
+        "WORKER_CAPTURE_NOT_ACCEPTED"
+    )
+
+
+def test_p1d1c_t13_wrong_scc_membership(bound_case):
+    state, meta, captured = bound_case
+    changed = replace(captured, members=("foreign",))
+    assert assess(state, meta, changed).reason == (
+        "SCC_NOT_IN_COMMITTED_MANIFEST"
+    )
+
+
+def test_p1d1c_t14_byte_limit_fails_closed(bound_case):
+    state, meta, captured = bound_case
+    result = assess(
+        state, meta, captured,
+        max_source_bytes=1,
+    )
+    assert result.binding_state == "UNAVAILABLE"
+    assert result.reason.startswith(
+        "SOURCE_BYTE_BUDGET_EXCEEDED:"
+    )
+
+
+def test_p1d1c_t15_invalid_budget_rejected(bound_case):
+    state, meta, captured = bound_case
+    for options in (
+        {"max_source_bytes": 0},
+        {"max_source_bytes": True},
+        {"max_closure_bytes": 0},
+        {"max_closure_bytes": 257 * 1024 * 1024},
+    ):
+        with pytest.raises(ValueError):
+            assess(state, meta, captured, **options)
+
+
+def test_p1d1c_t16_byte_accounting_mismatch(bound_case):
+    state, meta, captured = bound_case
+    changed = replace(
+        captured,
+        retained_raw_bytes=captured.retained_raw_bytes + 1,
+    )
+    assert assess(state, meta, changed).reason == (
+        "CAPTURE_BYTE_ACCOUNTING_MISMATCH"
+    )
+
+
+def test_p1d1c_t17_ast_mode_domain_mismatch(bound_case):
+    state, meta, captured = bound_case
+    changed = replace(
+        captured,
+        ast_modes=(("a", "INVALID"), ("b", "INVALID")),
+    )
+    assert assess(state, meta, changed).reason == (
+        "SCC_CLOSURE_INCOMPLETE_OR_MISMATCHED"
+    )
+
+
+def test_p1d1c_t18_no_source_reread_or_live_ipc(
+    bound_case, monkeypatch,
+):
+    from pathlib import Path
+
+    state, meta, captured = bound_case
+
+    def forbidden(*args, **kwargs):
+        raise AssertionError("filesystem read forbidden")
+
+    with monkeypatch.context() as scoped:
+        scoped.setattr(Path, "read_bytes", forbidden)
+        scoped.setattr(Path, "read_text", forbidden)
+        result = assess(state, meta, captured)
+
+    assert result.binding_state == (
+        "DECLARED_BYTES_MATCH_COMMITTED_PREPARED_CLAIMS"
+    )
```

# FINAL_VERDICT
FINAL PASS for the exact P1D1C implementation and focused gates. Canonical source adoption of both files is verified. Runtime loaded-code adoption and independent LIVE/source-origin authentication are not claimed.
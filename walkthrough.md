# CONTEXTOR_CYCLE_PROOF_P1C1_OWNER_CO_PUBLICATION

## TASK
Applied the exact auditor-supplied P1C1 patch in five approved files. This is a co-publication claim, not authenticated source capture or Python runtime SAFE certification. No redesign, extra source/test edits, FULL analysis, full pytest suite, update_file or restart.

## HEAD_BEFORE
9cecd293eee33901fee07e130ae9087de3177239; clean working tree. All supplied source anchors existed and both new files were absent. Contextor identified save_snapshot as the canonical store writer with 19 pre-edit direct static consumers, RepositoryAnalysisState with broad consumers, and invalidate_cycle_semantics with incremental-engine and test consumers. LIVE revision 638, resync_required=false.

## HEAD_AFTER
9cecd293eee33901fee07e130ae9087de3177239. No commit made.

## FILES_CHANGED
- contextor/core/cycle_semantics/publication_binding.py (new)
- contextor/core/analysis/state_manager.py
- contextor/core/cycle_semantics/lifecycle.py
- contextor/core/live_state/store.py
- tests/test_cycle_semantics_publication_binding.py (new)
walkthrough.md is this required report, excluded from source/test/docs changes.

## EXACT_IMPLEMENTATION
Applied the supplied CanonicalCycleManifestReceipt, claim-digest validation, seal and verification helpers. Added optional cycle_source_publication state field, cleared it on clone_for_update and cycle invalidation, added prepared_cycle_manifest handling and receipt verification to the existing store save/load path, and added ten named tests. No alternative transaction or metadata file was added. py_compile of all five files exited 0.

## T01_T10_RESULTS
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_publication_binding.py
Actual: 6 failed, 4 passed in 3.38s; exit code 1.
- T01 FAIL: load_snapshot returns cycle_source_publication=None; expected CanonicalCycleManifestReceipt.
- T02 PASS: no prepared input yields no receipt.
- T03 FAIL: prior revision's loaded receipt is None after rejected forged manifest.
- T04 FAIL: loaded old revision receipt is None.
- T05 FAIL: after synthetic metadata commit failure, loaded previous receipt is None, so .revision raises AttributeError.
- T06 FAIL: persisted payload receipt is None; dataclasses.replace(None, revision=999) raises TypeError before tamper check.
- T07 PASS: clone and invalidation clear receipt in memory.
- T08 FAIL: loaded receipt is None, so model_claims_sha256 access raises AttributeError.
- T09 PASS: stale state cannot seal.
- T10 PASS: legacy missing receipt remains unavailable.
The failures are one shared in-scope durable-write defect, not proof of six independent causes.

## FOCUSED_NON_REGRESSION
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_canonical_state.py tests/test_cycle_semantics_invalidation.py tests/test_cycle_semantics_evidence.py tests/test_live_state_store.py
Actual: 1 failed, 174 passed in 42.29s; exit code 1. Failure: tests/test_cycle_semantics_canonical_state.py::test_existing_constructor_compatibility asserts the exact previous dataclass field tuple and now sees the newly added cycle_source_publication field. This is a direct contract/test mismatch introduced by the approved patch; that test file is outside the allowlist. No broader suite run.
git diff --check for tracked files and git diff --no-index --check for both new files showed no whitespace error (no-index returns difference status for new files).

## DURABLE_GENERATION_BINDING
CODE_PATH_PROVED failure boundary: save_snapshot sets state_to_persist=copy.copy(state) and attaches the sealed receipt. For the exact-revision RepositoryAnalysisState path used by T01/T03/T04/T05/T06/T08, generation_lineage_manifest is non-None. The subsequent _write_split_lineage_generation call receives the original state, not state_to_persist, and replaces state_to_persist with a new object built from that original. The pickled payload therefore has cycle_source_publication=None. DIRECT_EVIDENCE: T06 reads the stored pickle and finds None; T01 load also finds None. The auditor-supplied patch's claimed same-generation durable binding is not achieved. No implementation adaptation was made.

## COMMIT_FAILURE_AND_RECOVERY
T03 confirms the forged manifest is rejected and durable metadata remains revision 1; the prior receipt is absent due to the write-path defect. T05 confirms the synthetic failed metadata replacement leaves metadata at revision 1; the old loaded receipt is again absent. Existing store atomicity of metadata was not disproven, but receipt preservation/recovery assertions fail. T06's foreign receipt test cannot reach its tamper assertion because the initial receipt was never serialized.

## INCREMENTAL_INVALIDATION
T07 passes: clone_for_update returns a separate candidate with receipt=None while the original retains its in-memory receipt; invalidate_cycle_semantics clears the original receipt and marks semantic state stale. The exact dataclass-field extension breaks the preexisting constructor compatibility assertion in focused non-regression.

## SOURCE_AUTHORITY_LIMITATION
Even a corrected co-publication receipt would attest only to committed prepared claims and exact metadata identity. It would not prove source-byte authenticity, atomic source/graph capture, import execution or runtime safety. Current LIVE cycle_semantics family remains stale. No SAFE classification or warning suppression was added.

## LIVE_REVISION_BEFORE_AFTER
Before edits: revision 638, resync_required=false. After watcher adoption: revision 643, resync_required=false. Module/graph/topology/structural cycle families fresh; cycle_semantics stale.

## WATCHER_EVENTS
get_live_events(after_revision=638) and follow-up after_revision=641 returned continuous history, resync_required=false:
- 639 desktop_watcher UPDATED publication_binding.py, blast_radius_state=fresh.
- 640 desktop_watcher UPDATED state_manager.py, blast_radius_state=deferred.
- 641 desktop_watcher UPDATED lifecycle.py, blast_radius_state=deferred.
- 642 desktop_watcher UPDATED store.py, blast_radius_state=fresh; affected_modules total=253 (bounded journal list truncated).
- 643 desktop_watcher UPDATED test_cycle_semantics_publication_binding.py, blast_radius_state=fresh.
No manual update_file.

## WORKSPACE_SYNC
At revision 643, sequential Contextor get_module_context checks reported workspace_sync=verified and no advisory warning for all five changed modules. An earlier concurrent check briefly returned Resource deadlock avoided / unverified during watcher progression; the sequential final checks resolved this. Post-edit blast radius confirms seal_prepared_cycle_manifest has store.py and the new test as static consumers, and save_snapshot has 20 static consumers. Source/test graph family is fresh; semantic diagnostic family remains stale.

## RESTART_REQUIREMENTS
No process was restarted. Active MCP HTTP listener 127.0.0.1:8765 remains owned by PID 3128. store.py, state_manager.py and lifecycle.py are imported in serving paths; an already-running process needs a manual reload/restart before it could execute modified code. Actual remote sys.modules and post-restart adoption were not certified. Because tests fail, restarting now would not certify P1C1 and should follow an auditor-approved correction. LIVE runtime likewise needs owner-managed reload if the modified store path is to be exercised there.

## FULL_DIFFS
Complete actual unified diffs of all five changed production/test files follow. New files are diffed against /dev/null.

```diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 6f5e643..0278ded 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -133,6 +133,8 @@ class RepositoryAnalysisState:
     cycle_semantics: CycleSemanticsSnapshot | None = None
     cycle_semantics_state: str = "deferred"
     cycle_semantics_invalidation_reason: str | None = None
+    # Optional durable receipt. Never a runtime SAFE certificate.
+    cycle_source_publication: Any = None
 
     def clone_for_update(self) -> "RepositoryAnalysisState":
         """
@@ -150,6 +152,9 @@ class RepositoryAnalysisState:
         contracts in the incremental pipeline.
         """
         candidate = copy.copy(self)
+        # An incremental candidate is a new generation.
+        # It cannot inherit a receipt from the old generation.
+        candidate.cycle_source_publication = None
 
         for state_field in fields(self):
             value = getattr(
diff --git a/contextor/core/cycle_semantics/lifecycle.py b/contextor/core/cycle_semantics/lifecycle.py
index ec041d5..7556255 100644
--- a/contextor/core/cycle_semantics/lifecycle.py
+++ b/contextor/core/cycle_semantics/lifecycle.py
@@ -113,6 +113,10 @@ def invalidate_cycle_semantics(
             "Unsupported cycle semantics invalidation reason"
         )
 
+    # Even retained historical semantic evidence cannot carry
+    # its old publication receipt into a new generation.
+    state.cycle_source_publication = None
+
     evidence = getattr(
         state,
         "cycle_semantics",
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 1cc83fd..cd4b541 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -1518,6 +1518,7 @@ def save_snapshot(
     previous_state: Any = None,
     migration_file_state_source: str | Path | None = None,
     migration_only_if_absent: bool = False,
+    prepared_cycle_manifest: Any = None,
 ) -> LiveStateMetadata:
     """Atomically publish a complete snapshot and monotonically increasing revision."""
 
@@ -1737,6 +1738,46 @@ def save_snapshot(
 
         state_to_persist = state
 
+        # A prepared manifest is sealed by the canonical STORE OWNER
+        # under the existing store lock, as part of the SAME state
+        # generation. Never write it as a separate metadata file.
+        #
+        # The original caller state is not given a receipt before
+        # the durable metadata commit can succeed.
+        if prepared_cycle_manifest is not None:
+            if not isinstance(state, RepositoryAnalysisState):
+                raise TypeError(
+                    "prepared cycle manifest requires canonical state"
+                )
+
+            from contextor.core.cycle_semantics.publication_binding import (
+                seal_prepared_cycle_manifest,
+            )
+
+            state_to_persist = copy.copy(state)
+            state_to_persist.cycle_source_publication = (
+                seal_prepared_cycle_manifest(
+                    state_to_persist,
+                    prepared_cycle_manifest,
+                    revision=metadata.revision,
+                    state_id=metadata.state_id,
+                    repo_id=metadata.repo_id,
+                    root_path=metadata.root_path,
+                )
+            )
+
+        elif (
+            isinstance(state, RepositoryAnalysisState)
+            and getattr(
+                state,
+                "cycle_source_publication",
+                None,
+            ) is not None
+        ):
+            # Old receipt must never be republished implicitly.
+            state_to_persist = copy.copy(state)
+            state_to_persist.cycle_source_publication = None
+
         if (
             generation_lineage_manifest
             is not None
@@ -2308,6 +2349,26 @@ def load_snapshot(
                 phase_started,
                 repo_id=expected_repo_id,
             )
+            # Fail closed on absent/foreign/tampered generation
+            # receipts while retaining otherwise valid diagnostics.
+            if getattr(
+                state_obj,
+                "cycle_source_publication",
+                None,
+            ) is not None:
+                from contextor.core.cycle_semantics.publication_binding import (
+                    verify_co_published_cycle_manifest,
+                )
+
+                if not verify_co_published_cycle_manifest(
+                    state_obj,
+                    revision=metadata.revision,
+                    state_id=metadata.state_id,
+                    repo_id=metadata.repo_id,
+                    root_path=metadata.root_path,
+                ):
+                    state_obj.cycle_source_publication = None
+
             return state_obj, metadata
         if metadata.lineage_manifest_file:
             return None
diff --git a/contextor/core/cycle_semantics/publication_binding.py b/contextor/core/cycle_semantics/publication_binding.py
new file mode 100644
index 0000000..935e4cb
--- /dev/null
+++ b/contextor/core/cycle_semantics/publication_binding.py
@@ -0,0 +1,306 @@
+"""Co-publication of prepared SCC manifest claims with durable generations.
+
+Only the canonical snapshot-store writer creates this receipt.
+It attests to co-publication of a declaration, NOT provenance
+of source bytes or runtime import safety.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Any
+
+from .contracts import (
+    CycleSemanticsSnapshot,
+    fingerprint_hard_edges,
+)
+from .generation_manifest import (
+    MANIFEST_VERSION,
+    PreparedCycleSourceManifest,
+    PreparedSCCSourceBinding,
+    _digest,
+)
+from .scc import analyze_import_cycle_topology
+
+
+PUBLICATION_BINDING_VERSION = "cycle-prepared-co-publication/1"
+PUBLICATION_AUTHORITY = (
+    "COMMITTED_PREPARED_CLAIMS_NOT_SOURCE_CERTIFIED"
+)
+_ALLOWED_MODELS = frozenset((
+    "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+    "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+))
+
+
+@dataclass(frozen=True)
+class CanonicalCycleManifestReceipt:
+    prepared_manifest: PreparedCycleSourceManifest
+    model_claims_sha256: str
+    revision: int
+    state_id: str
+    repo_id: str
+    root_path: str
+    version: str = PUBLICATION_BINDING_VERSION
+    authority: str = PUBLICATION_AUTHORITY
+
+
+def _validated_claim_digest(
+    state: Any,
+    manifest: PreparedCycleSourceManifest,
+) -> str:
+    """Validate declarations, not source-byte authenticity."""
+    if type(manifest) is not PreparedCycleSourceManifest:
+        raise ValueError("prepared manifest contract missing")
+    if (
+        manifest.version != MANIFEST_VERSION
+        or manifest.authority
+        != "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+        or not isinstance(manifest.source_manifest_sha256, str)
+        or len(manifest.source_manifest_sha256) != 64
+        or any(
+            c not in "0123456789abcdef"
+            for c in manifest.source_manifest_sha256
+        )
+    ):
+        raise ValueError(
+            "prepared manifest is incomplete or unsupported"
+        )
+
+    graph = getattr(state, "dependency_graph", None)
+    hard_edges = getattr(graph, "hard_edges", None)
+    snapshot = getattr(state, "cycle_semantics", None)
+
+    if (
+        getattr(state, "resync_required", False) is not False
+        or getattr(state, "cycle_semantics_state", None) != "fresh"
+        or getattr(state, "cycles_state", None) != "fresh"
+        or type(snapshot) is not CycleSemanticsSnapshot
+        or snapshot.coverage_status
+        != "FILESYSTEM_STABLE_NON_ATOMIC"
+        or snapshot.source_issues
+        or not isinstance(hard_edges, dict)
+    ):
+        raise ValueError(
+            "canonical cycle evidence is not complete and fresh"
+        )
+
+    graph_hash = fingerprint_hard_edges(hard_edges)
+    if (
+        graph_hash != manifest.graph_sha256
+        or graph_hash != snapshot.graph_sha256
+    ):
+        raise ValueError("canonical graph identity mismatch")
+
+    topology = analyze_import_cycle_topology(hard_edges)
+    cyclic = topology.cyclic_components
+    if (
+        not cyclic
+        or type(manifest.components) is not tuple
+        or len(manifest.components) != len(cyclic)
+    ):
+        raise ValueError("prepared SCC coverage incomplete")
+
+    adjacency = {
+        source: set(targets)
+        for source, targets in hard_edges.items()
+    }
+    for targets in tuple(adjacency.values()):
+        for target in targets:
+            adjacency.setdefault(target, set())
+
+    accepted: dict[str, tuple[str, str]] = {}
+    claims = []
+
+    for structural, prepared in zip(cyclic, manifest.components):
+        if (
+            type(prepared) is not PreparedSCCSourceBinding
+            or prepared.members != structural.members
+            or prepared.preparation_state
+            != "PREPARED_UNPUBLISHED"
+            or prepared.reason is not None
+            or prepared.model_classification not in _ALLOWED_MODELS
+            or type(prepared.source_signatures) is not tuple
+        ):
+            raise ValueError(
+                "prepared SCC claims are inconsistent"
+            )
+
+        closure = set(structural.members)
+        pending = list(structural.members)
+
+        while pending:
+            for target in adjacency[pending.pop()]:
+                if target not in closure:
+                    closure.add(target)
+                    pending.append(target)
+
+        rows = prepared.source_signatures
+        if (
+            len(rows) != len(closure)
+            or tuple(
+                row[0]
+                for row in rows
+                if type(row) is tuple and len(row) == 3
+            ) != tuple(sorted(closure))
+        ):
+            raise ValueError(
+                "prepared source closure is incomplete"
+            )
+
+        for row in rows:
+            if type(row) is not tuple or len(row) != 3:
+                raise ValueError("invalid source signature")
+
+            name, raw, ast_hash = row
+            if any(
+                type(digest) is not str
+                or len(digest) != 64
+                or any(
+                    c not in "0123456789abcdef"
+                    for c in digest
+                )
+                for digest in (raw, ast_hash)
+            ):
+                raise ValueError("invalid source digest")
+
+            signature = (raw, ast_hash)
+            if (
+                name in accepted
+                and accepted[name] != signature
+            ):
+                raise ValueError(
+                    "conflicting shared source digest"
+                )
+            accepted[name] = signature
+
+        claims.append((
+            prepared.members,
+            prepared.model_classification,
+            rows,
+        ))
+
+    observed = dict(snapshot.observed_source_fingerprints)
+    cyclic_members = tuple(sorted(
+        member
+        for component in cyclic
+        for member in component.members
+    ))
+
+    if (
+        snapshot.cyclic_modules != cyclic_members
+        or tuple(sorted(observed)) != cyclic_members
+        or any(
+            accepted[member][0] != observed[member]
+            for member in cyclic_members
+        )
+    ):
+        raise ValueError(
+            "canonical cyclic source fingerprints mismatch"
+        )
+
+    ordered_sources = tuple(
+        (name, *accepted[name])
+        for name in sorted(accepted)
+    )
+    expected_manifest_hash = _digest((
+        MANIFEST_VERSION,
+        graph_hash,
+        tuple(component.members for component in cyclic),
+        ordered_sources,
+    ))
+    if manifest.source_manifest_sha256 != expected_manifest_hash:
+        raise ValueError(
+            "prepared source manifest digest mismatch"
+        )
+
+    # Bind model CLAIMS independently of the source digest.
+    # This does not authenticate model execution or source origin.
+    return _digest((
+        PUBLICATION_BINDING_VERSION,
+        graph_hash,
+        expected_manifest_hash,
+        tuple(claims),
+    ))
+
+
+def seal_prepared_cycle_manifest(
+    state: Any,
+    manifest: PreparedCycleSourceManifest,
+    *,
+    revision: int,
+    state_id: str,
+    repo_id: str,
+    root_path: str,
+) -> CanonicalCycleManifestReceipt:
+    """Seal during the snapshot-store commit path only."""
+    if (
+        type(revision) is not int
+        or revision < 1
+        or type(state_id) is not str
+        or not state_id
+    ):
+        raise ValueError(
+            "invalid publication generation identity"
+        )
+
+    if (
+        type(repo_id) is not str
+        or type(root_path) is not str
+    ):
+        raise ValueError("invalid repository identity")
+
+    if (
+        getattr(state, "revision", None) != revision
+        or getattr(state, "state_id", None) != state_id
+    ):
+        raise ValueError(
+            "canonical state and store metadata differ"
+        )
+
+    digest = _validated_claim_digest(state, manifest)
+    return CanonicalCycleManifestReceipt(
+        prepared_manifest=manifest,
+        model_claims_sha256=digest,
+        revision=revision,
+        state_id=state_id,
+        repo_id=repo_id,
+        root_path=root_path,
+    )
+
+
+def verify_co_published_cycle_manifest(
+    state: Any,
+    *,
+    revision: int,
+    state_id: str,
+    repo_id: str,
+    root_path: str,
+) -> bool:
+    """Check persisted claim and exact generation identity."""
+    receipt = getattr(
+        state,
+        "cycle_source_publication",
+        None,
+    )
+    if type(receipt) is not CanonicalCycleManifestReceipt:
+        return False
+
+    try:
+        expected = seal_prepared_cycle_manifest(
+            state,
+            receipt.prepared_manifest,
+            revision=revision,
+            state_id=state_id,
+            repo_id=repo_id,
+            root_path=root_path,
+        )
+    except (
+        TypeError,
+        ValueError,
+        AttributeError,
+        KeyError,
+    ):
+        return False
+
+    return receipt == expected
diff --git a/tests/test_cycle_semantics_publication_binding.py b/tests/test_cycle_semantics_publication_binding.py
new file mode 100644
index 0000000..ae10d77
--- /dev/null
+++ b/tests/test_cycle_semantics_publication_binding.py
@@ -0,0 +1,271 @@
+"""P1C1 durable co-publication gates; never runtime safety tests."""
+
+from __future__ import annotations
+
+import pickle
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.analysis.state_manager import (
+    RepositoryAnalysisState,
+)
+from contextor.core.cycle_semantics.generation_manifest import (
+    prepare_cycle_source_manifest,
+)
+from contextor.core.cycle_semantics.lifecycle import (
+    invalidate_cycle_semantics,
+)
+from contextor.core.cycle_semantics.publication_binding import (
+    PUBLICATION_AUTHORITY,
+    CanonicalCycleManifestReceipt,
+    verify_co_published_cycle_manifest,
+)
+from contextor.core.domain.graph import ProjectGraph
+from contextor.core.live_state.store import (
+    load_snapshot,
+    read_metadata,
+    save_snapshot,
+)
+from tests.test_cycle_semantics_evidence import (
+    PAIR,
+    PASS,
+    _bound,
+    _p1b_snapshots,
+)
+
+
+def _case():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+    prepared = prepare_cycle_source_manifest(
+        PAIR,
+        index,
+        snapshot,
+        evidence,
+        _p1b_snapshots(PASS),
+    )
+    state = RepositoryAnalysisState(
+        dependency_graph=ProjectGraph(
+            hard_edges={key: set(value) for key, value in PAIR.items()},
+            soft_edges={},
+        ),
+        cycle_semantics=snapshot,
+        cycle_semantics_state="fresh",
+        cycles_state="fresh",
+    )
+    return state, prepared
+
+
+def _save(state, root, revision, prepared=None):
+    return save_snapshot(
+        state,
+        root,
+        "cycle-state",
+        exact_revision=revision,
+        file_state_payload={
+            "_meta": {
+                "state_id": "cycle-state",
+                "revision": revision,
+            },
+            "files": {},
+        },
+        prepared_cycle_manifest=prepared,
+    )
+
+
+def test_p1c1_t01_receipt_is_committed_with_exact_generation(tmp_path):
+    state, prepared = _case()
+    metadata = _save(state, tmp_path, 1, prepared)
+    loaded, loaded_metadata = load_snapshot(
+        tmp_path, "cycle-state",
+    )
+
+    receipt = loaded.cycle_source_publication
+    assert isinstance(receipt, CanonicalCycleManifestReceipt)
+    assert receipt.authority == PUBLICATION_AUTHORITY
+    assert receipt.revision == metadata.revision == 1
+    assert receipt.state_id == metadata.state_id
+    assert receipt.prepared_manifest == prepared
+    assert len(receipt.model_claims_sha256) == 64
+    assert loaded_metadata == metadata
+    assert verify_co_published_cycle_manifest(
+        loaded,
+        revision=metadata.revision,
+        state_id=metadata.state_id,
+        repo_id=metadata.repo_id,
+        root_path=metadata.root_path,
+    )
+
+    # Writer does not expose receipt on its original object.
+    assert state.cycle_source_publication is None
+
+
+def test_p1c1_t02_no_prepared_input_means_no_receipt(tmp_path):
+    state, _ = _case()
+    _save(state, tmp_path, 1)
+    loaded, _ = load_snapshot(tmp_path, "cycle-state")
+    assert loaded.cycle_source_publication is None
+
+
+def test_p1c1_t03_incomplete_manifest_does_not_commit(tmp_path):
+    state, prepared = _case()
+    _save(state, tmp_path, 1, prepared)
+
+    forged = replace(
+        prepared,
+        source_manifest_sha256="f" * 64,
+    )
+    with pytest.raises(ValueError):
+        _save(state, tmp_path, 2, forged)
+
+    assert read_metadata(tmp_path).revision == 1
+    loaded, metadata = load_snapshot(
+        tmp_path, "cycle-state",
+    )
+    assert metadata.revision == 1
+    assert loaded.cycle_source_publication is not None
+
+
+def test_p1c1_t04_new_revision_cannot_reuse_old_receipt(tmp_path):
+    state, prepared = _case()
+    _save(state, tmp_path, 1, prepared)
+    old, _ = load_snapshot(tmp_path, "cycle-state")
+    assert old.cycle_source_publication is not None
+
+    _save(old, tmp_path, 2)
+    loaded, metadata = load_snapshot(
+        tmp_path, "cycle-state",
+    )
+    assert metadata.revision == 2
+    assert loaded.cycle_source_publication is None
+
+
+def test_p1c1_t05_failed_metadata_commit_preserves_previous(tmp_path, monkeypatch):
+    import contextor.core.live_state.store as store
+
+    state, prepared = _case()
+    _save(state, tmp_path, 1, prepared)
+
+    original_replace = store.os.replace
+
+    def fail_metadata(source, target):
+        if target.name == "engine_state.meta.json":
+            raise RuntimeError("synthetic commit failure")
+        return original_replace(source, target)
+
+    with monkeypatch.context() as patch:
+        patch.setattr(store.os, "replace", fail_metadata)
+        with pytest.raises(RuntimeError, match="synthetic commit failure"):
+            _save(state, tmp_path, 2, prepared)
+
+    loaded, metadata = load_snapshot(
+        tmp_path, "cycle-state",
+    )
+    assert metadata.revision == 1
+    assert loaded.cycle_source_publication.revision == 1
+
+
+def test_p1c1_t06_foreign_revision_receipt_fails_closed(tmp_path):
+    state, prepared = _case()
+    metadata = _save(state, tmp_path, 1, prepared)
+
+    state_file = tmp_path / metadata.state_file
+    payload = pickle.loads(state_file.read_bytes())
+    original = payload["state"].cycle_source_publication
+    payload["state"].cycle_source_publication = replace(
+        original,
+        revision=999,
+    )
+    state_file.write_bytes(pickle.dumps(payload))
+
+    loaded, loaded_metadata = load_snapshot(
+        tmp_path, "cycle-state",
+    )
+    assert loaded_metadata.revision == 1
+    assert loaded.cycle_source_publication is None
+
+
+def test_p1c1_t07_cow_invalidates_without_mutating_previous():
+    state, prepared = _case()
+    state.revision = 1
+    state.state_id = "cycle-state"
+
+    from contextor.core.cycle_semantics.publication_binding import (
+        seal_prepared_cycle_manifest,
+    )
+
+    state.cycle_source_publication = seal_prepared_cycle_manifest(
+        state,
+        prepared,
+        revision=1,
+        state_id="cycle-state",
+        repo_id="",
+        root_path="",
+    )
+
+    candidate = state.clone_for_update()
+    assert candidate is not state
+    assert candidate.cycle_source_publication is None
+    assert state.cycle_source_publication is not None
+
+    invalidate_cycle_semantics(
+        state,
+        "SOURCE_CHANGED",
+    )
+    assert state.cycle_source_publication is None
+    assert state.cycle_semantics_state == "stale"
+
+
+def test_p1c1_t08_classification_claim_has_distinct_digest(tmp_path):
+    state, prepared = _case()
+    metadata = _save(state, tmp_path, 1, prepared)
+    loaded, _ = load_snapshot(tmp_path, "cycle-state")
+    receipt = loaded.cycle_source_publication
+
+    assert receipt.model_claims_sha256 != (
+        prepared.source_manifest_sha256
+    )
+
+    tampered_claim = replace(
+        prepared.components[0],
+        model_classification=(
+            "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
+        ),
+    )
+    tampered_manifest = replace(
+        prepared,
+        components=(tampered_claim,),
+    )
+    loaded.cycle_source_publication = replace(
+        receipt,
+        prepared_manifest=tampered_manifest,
+    )
+    assert not verify_co_published_cycle_manifest(
+        loaded,
+        revision=metadata.revision,
+        state_id=metadata.state_id,
+        repo_id=metadata.repo_id,
+        root_path=metadata.root_path,
+    )
+
+
+def test_p1c1_t09_partial_or_stale_state_cannot_seal(tmp_path):
+    state, prepared = _case()
+    state.cycle_semantics_state = "stale"
+    with pytest.raises(ValueError):
+        _save(state, tmp_path, 1, prepared)
+    assert read_metadata(tmp_path) is None
+
+
+def test_p1c1_t10_legacy_missing_receipt_is_unavailable():
+    state, _ = _case()
+    assert state.cycle_source_publication is None
+    del state.__dict__["cycle_source_publication"]
+    assert state.cycle_source_publication is None
+    assert not verify_co_published_cycle_manifest(
+        state,
+        revision=1,
+        state_id="cycle-state",
+        repo_id="",
+        root_path="",
+    )
```

## FINAL_VERDICT
FAIL. The exact auditor patch compiles and LIVE watcher indexed all files, but the receipt is dropped before durable serialization in the split-lineage store path (6/10 named tests fail), and the approved dataclass extension breaks one existing focused constructor-contract test (174/175 pass). No unauthorized adaptation was made.

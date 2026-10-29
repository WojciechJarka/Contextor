# CONTEXTOR P1D3-WARN-2B-2 — implementer report

## 1. PREFLIGHT

DIRECT_EVIDENCE: Initial HEAD `b8115ed0424da98d0e1dec420e22e4eb95e0177a`; initial worktree clean. Contextor MCP was used first for the store architecture and consumers, followed by direct source inspection. WARN-2B-1 validator remained prepared-only; v2 sealing, hydration, COW clearing and invalidation matched the specified preflight.

## 2. HEAD / WORKTREE

DIRECT_EVIDENCE: Final HEAD is unchanged. The worktree has only the five authorized Python files and this report. No commit, checkout, reset or service restart occurred.

## 3. NEW RECEIPT CONTRACT

CODE_PATH_PROVED: `CanonicalPartialSCCReceipt` is frozen with the specified preparation, digest and generation identity fields, version `cycle-partial-scc-co-publication/1` and authority `COMMITTED_PARTIAL_SCC_DECLARATIONS_NOT_SOURCE_CERTIFIED`.

## 4. PURE SEAL AND VERIFY

CODE_PATH_PROVED: Seal requires exact preparation and semantic snapshot types, fresh semantic/cycle families, no resync, dict hard edges, matching graph fingerprint, exact positive revision and matching state identity. It calls `validate_partial_scc_claims`; invalid gates raise `ValueError` or `TypeError`. Verify requires the exact receipt class, version and authority, revalidates current declarations and compares the recomputed full receipt. Neither function performs I/O or mutation.

## 5. DIGEST DOMAIN AND INTEGRITY

CODE_PATH_PROVED: `_digest` receives publication version, current graph SHA-256, `asdict` of validated claims and `asdict` of full preparation. The digest binds declaration contents, including status, reason, manifest and component preparations. It does not authenticate the source producer.

## 6. COMMITTED GENERATION IDENTITY

CODE_PATH_PROVED: Store sealing occurs under the existing lock and binds exact committed metadata revision, state ID, repository ID and root path. Both hydration paths verify with committed metadata. No sidecar or metadata schema change was made.

## 7. STATE / COW / INVALIDATION

CODE_PATH_PROVED: The new ClassVar compatibility pattern yields `None` for old pickles; `__post_init__` creates an instance attribute; COW and semantic invalidation clear it. It is not a dataclass constructor field.

## 8. STORE TRANSACTION

CODE_PATH_PROVED: `save_snapshot` has one optional new keyword. One shallow copy is used for receipt handling; the caller state is not given a receipt. Omitted preparation clears a prior partial receipt on the persisted copy. Existing lock and commit order remain.

## 9. COEXISTENCE WITH RECEIPT V2

CONTRACT_PROVED: Both inputs seal on the same `state_to_persist`. The v2 sealing function and digest are unchanged. T05 loaded and independently verified both receipts at one committed revision.

## 10. SPLIT / LEGACY HYDRATION

CODE_PATH_PROVED: Both load paths verify an optional partial receipt against state and metadata, clearing an invalid receipt while retaining structural state. Old states with no attribute resolve to `None`. The v2 checks remain. The new test exercises split hydration; legacy-path behavior is source-backed but not separately exercised by that module.

## 11. MIXED PASS / INDETERMINATE

CONTRACT_PROVED: Genuine original-worker preparation in an isolated repository produced distinguishable PASS and INDETERMINATE declarations that survived commit and load. PASS and HAZARD classifications also survived.

## 12. FORGED AND FOREIGN RECEIPTS

CONTRACT_PROVED: Focused tests reject altered classification, digest, revision, state ID, repository ID, root path, graph, stale families and resync. Tampered persisted receipts are cleared on hydration.

## 13. FAILURE ATOMICITY

CONTRACT_PROVED: Invalid preparation did not advance committed metadata. Injected metadata replacement failure preserved the previous loadable revision and its valid receipt.

## 14. STRUCTURAL DIAGNOSTIC RETENTION

CONTRACT_PROVED: T20 retained fresh cycles and hard edges after discarding a tampered optional receipt. No warning consumer changed.

## 15. FOCUSED TEST RESULTS

DIRECT_EVIDENCE: `python -m py_compile` on all five changed Python files exited 0. New module: 25 passed, 0 failed, 0 skipped, 6.27 s, exit 0. Six requested regression modules: 106 passed, 0 failed, 0 skipped, 15.47 s, exit 0. `git diff --check` and untracked-file `git diff --no-index --check` exited 0. No global suite ran.

## 16. POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor inspected new receipt module, state manager, lifecycle and store. All four returned `workspace_sync=verified`, canonical revision 832 and live provenance; module, graph, topology and structural cycles fresh, cycle_semantics stale. Structural DFS back-edge path count remained 16 (prechange 16). No newly counted cycle was observed. This does not certify semantic safety or active loaded-code adoption.

## 17. FILES_CHANGED

- `contextor/core/cycle_semantics/partial_scc_publication.py` (new)
- `contextor/core/analysis/state_manager.py`
- `contextor/core/cycle_semantics/lifecycle.py`
- `contextor/core/live_state/store.py`
- `tests/test_cycle_semantics_partial_scc_publication.py` (new)

`walkthrough.md` is the report, excluded from production/test changed files.

## 18. FULL_DIFFS

Complete actual diffs for all five files follow.


### Tracked Python files

```diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index d5a38f8..d7953d3 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -138,11 +138,13 @@ class RepositoryAnalysisState:
     # ClassVar also supplies None for old unpickled states in
     # which the instance attribute is absent.
     cycle_source_publication: ClassVar[Any] = None
+    cycle_partial_source_publication: ClassVar[Any] = None
 
     def __post_init__(self) -> None:
         # Persisted as an ordinary instance __dict__ attribute,
         # not as a dataclass field.
         self.cycle_source_publication = None
+        self.cycle_partial_source_publication = None
 
     def clone_for_update(self) -> "RepositoryAnalysisState":
         """
@@ -163,6 +165,7 @@ class RepositoryAnalysisState:
         # An incremental candidate is a new generation.
         # It cannot inherit a receipt from the old generation.
         candidate.cycle_source_publication = None
+        candidate.cycle_partial_source_publication = None
 
         for state_field in fields(self):
             value = getattr(
diff --git a/contextor/core/cycle_semantics/lifecycle.py b/contextor/core/cycle_semantics/lifecycle.py
index 7556255..b8ddb50 100644
--- a/contextor/core/cycle_semantics/lifecycle.py
+++ b/contextor/core/cycle_semantics/lifecycle.py
@@ -116,6 +116,7 @@ def invalidate_cycle_semantics(
     # Even retained historical semantic evidence cannot carry
     # its old publication receipt into a new generation.
     state.cycle_source_publication = None
+    state.cycle_partial_source_publication = None
 
     evidence = getattr(
         state,
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 41bcce2..10df4fa 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -1519,6 +1519,7 @@ def save_snapshot(
     migration_file_state_source: str | Path | None = None,
     migration_only_if_absent: bool = False,
     prepared_cycle_manifest: Any = None,
+    prepared_partial_scc_preparation: Any = None,
 ) -> LiveStateMetadata:
     """Atomically publish a complete snapshot and monotonically increasing revision."""
 
@@ -1736,47 +1737,62 @@ def save_snapshot(
             except AttributeError:
                 pass
 
-        state_to_persist = state
+        if prepared_cycle_manifest is not None and not isinstance(
+            state, RepositoryAnalysisState
+        ):
+            raise TypeError("prepared cycle manifest requires canonical state")
+        if prepared_partial_scc_preparation is not None and type(state) is not (
+            RepositoryAnalysisState
+        ):
+            raise TypeError("partial SCC preparation requires canonical state")
+
+        # Both receipts belong to one copy and one locked store generation.
+        # Neither is installed on the caller's original state.
+        receipt_input = (
+            prepared_cycle_manifest is not None
+            or prepared_partial_scc_preparation is not None
+            or getattr(state, "cycle_source_publication", None) is not None
+            or getattr(state, "cycle_partial_source_publication", None) is not None
+        )
+        state_to_persist = (
+            copy.copy(state)
+            if isinstance(state, RepositoryAnalysisState) and receipt_input
+            else state
+        )
 
-        # A prepared manifest is sealed by the canonical STORE OWNER
-        # under the existing store lock, as part of the SAME state
-        # generation. Never write it as a separate metadata file.
-        #
-        # The original caller state is not given a receipt before
-        # the durable metadata commit can succeed.
         if prepared_cycle_manifest is not None:
-            if not isinstance(state, RepositoryAnalysisState):
-                raise TypeError(
-                    "prepared cycle manifest requires canonical state"
-                )
-
             from contextor.core.cycle_semantics.publication_binding import (
                 seal_prepared_cycle_manifest,
             )
 
-            state_to_persist = copy.copy(state)
-            state_to_persist.cycle_source_publication = (
-                seal_prepared_cycle_manifest(
+            state_to_persist.cycle_source_publication = seal_prepared_cycle_manifest(
+                state_to_persist,
+                prepared_cycle_manifest,
+                revision=metadata.revision,
+                state_id=metadata.state_id,
+                repo_id=metadata.repo_id,
+                root_path=metadata.root_path,
+            )
+        elif state_to_persist is not state:
+            state_to_persist.cycle_source_publication = None
+
+        if prepared_partial_scc_preparation is not None:
+            from contextor.core.cycle_semantics.partial_scc_publication import (
+                seal_partial_scc_preparation,
+            )
+
+            state_to_persist.cycle_partial_source_publication = (
+                seal_partial_scc_preparation(
                     state_to_persist,
-                    prepared_cycle_manifest,
+                    prepared_partial_scc_preparation,
                     revision=metadata.revision,
                     state_id=metadata.state_id,
                     repo_id=metadata.repo_id,
                     root_path=metadata.root_path,
                 )
             )
-
-        elif (
-            isinstance(state, RepositoryAnalysisState)
-            and getattr(
-                state,
-                "cycle_source_publication",
-                None,
-            ) is not None
-        ):
-            # Old receipt must never be republished implicitly.
-            state_to_persist = copy.copy(state)
-            state_to_persist.cycle_source_publication = None
+        elif state_to_persist is not state:
+            state_to_persist.cycle_partial_source_publication = None
 
         if (
             generation_lineage_manifest
@@ -2369,6 +2385,20 @@ def load_snapshot(
                 ):
                     state_obj.cycle_source_publication = None
 
+            if getattr(state_obj, "cycle_partial_source_publication", None) is not None:
+                from contextor.core.cycle_semantics.partial_scc_publication import (
+                    verify_co_published_partial_scc_preparation,
+                )
+
+                if not verify_co_published_partial_scc_preparation(
+                    state_obj,
+                    revision=metadata.revision,
+                    state_id=metadata.state_id,
+                    repo_id=metadata.repo_id,
+                    root_path=metadata.root_path,
+                ):
+                    state_obj.cycle_partial_source_publication = None
+
             return state_obj, metadata
         if metadata.lineage_manifest_file:
             return None
@@ -2488,6 +2518,20 @@ def load_snapshot(
             ):
                 payload.cycle_source_publication = None
 
+        if getattr(payload, "cycle_partial_source_publication", None) is not None:
+            from contextor.core.cycle_semantics.partial_scc_publication import (
+                verify_co_published_partial_scc_preparation,
+            )
+
+            if not verify_co_published_partial_scc_preparation(
+                payload,
+                revision=metadata.revision,
+                state_id=metadata.state_id,
+                repo_id=metadata.repo_id,
+                root_path=metadata.root_path,
+            ):
+                payload.cycle_partial_source_publication = None
+
         return payload, metadata
 
 
```

### New receipt module

```diff
diff --git a/contextor/core/cycle_semantics/partial_scc_publication.py b/contextor/core/cycle_semantics/partial_scc_publication.py
new file mode 100644
index 0000000..b77cbaa
--- /dev/null
+++ b/contextor/core/cycle_semantics/partial_scc_publication.py
@@ -0,0 +1,127 @@
+"""Pure contracts for store-owned partial SCC co-publication.
+
+A standalone seal is not a durable commit, source certificate, or safety proof.
+"""
+
+from __future__ import annotations
+
+from dataclasses import asdict, dataclass
+from typing import Any
+
+from .contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
+from .generation_manifest import _digest
+from .original_worker_preparation import OriginalWorkerManifestPreparation
+from .partial_scc_claims import (
+    PARTIAL_SCC_CLAIMS_AUTHORITY,
+    PARTIAL_SCC_CLAIMS_VERSION,
+    PreparedPartialSCCClaims,
+    validate_partial_scc_claims,
+)
+
+
+PARTIAL_SCC_PUBLICATION_VERSION = "cycle-partial-scc-co-publication/1"
+PARTIAL_SCC_PUBLICATION_AUTHORITY = (
+    "COMMITTED_PARTIAL_SCC_DECLARATIONS_NOT_SOURCE_CERTIFIED"
+)
+
+
+@dataclass(frozen=True)
+class CanonicalPartialSCCReceipt:
+    preparation: OriginalWorkerManifestPreparation
+    claims_sha256: str
+    revision: int
+    state_id: str
+    repo_id: str
+    root_path: str
+    version: str = PARTIAL_SCC_PUBLICATION_VERSION
+    authority: str = PARTIAL_SCC_PUBLICATION_AUTHORITY
+
+
+def seal_partial_scc_preparation(
+    state: Any,
+    preparation: OriginalWorkerManifestPreparation,
+    *,
+    revision: int,
+    state_id: str,
+    repo_id: str,
+    root_path: str,
+) -> CanonicalPartialSCCReceipt:
+    """Validate declarations and seal an exact supplied generation identity."""
+    if type(preparation) is not OriginalWorkerManifestPreparation:
+        raise TypeError("partial SCC preparation contract missing")
+    snapshot = getattr(state, "cycle_semantics", None)
+    graph = getattr(state, "dependency_graph", None)
+    hard_edges = getattr(graph, "hard_edges", None)
+    if (
+        type(snapshot) is not CycleSemanticsSnapshot
+        or getattr(state, "cycle_semantics_state", None) != "fresh"
+        or getattr(state, "cycles_state", None) != "fresh"
+        or getattr(state, "resync_required", False) is not False
+        or type(hard_edges) is not dict
+    ):
+        raise ValueError("canonical partial SCC evidence unavailable")
+    graph_sha256 = fingerprint_hard_edges(hard_edges)
+    if graph_sha256 != snapshot.graph_sha256:
+        raise ValueError("canonical partial SCC graph identity mismatch")
+    if (
+        type(revision) is not int or revision < 1
+        or type(state_id) is not str or not state_id
+        or type(repo_id) is not str
+        or type(root_path) is not str
+        or type(getattr(state, "revision", None)) is not int
+        or state.revision != revision
+        or type(getattr(state, "state_id", None)) is not str
+        or state.state_id != state_id
+    ):
+        raise ValueError("partial SCC publication generation identity mismatch")
+    claims = validate_partial_scc_claims(hard_edges, snapshot, preparation)
+    if (
+        type(claims) is not PreparedPartialSCCClaims
+        or claims.version != PARTIAL_SCC_CLAIMS_VERSION
+        or claims.authority != PARTIAL_SCC_CLAIMS_AUTHORITY
+    ):
+        raise ValueError("partial SCC declarations unavailable")
+    claims_sha256 = _digest((
+        PARTIAL_SCC_PUBLICATION_VERSION,
+        graph_sha256,
+        asdict(claims),
+        asdict(preparation),
+    ))
+    return CanonicalPartialSCCReceipt(
+        preparation=preparation,
+        claims_sha256=claims_sha256,
+        revision=revision,
+        state_id=state_id,
+        repo_id=repo_id,
+        root_path=root_path,
+    )
+
+
+def verify_co_published_partial_scc_preparation(
+    state: Any,
+    *,
+    revision: int,
+    state_id: str,
+    repo_id: str,
+    root_path: str,
+) -> bool:
+    """Revalidate stored declarations against the current supplied state."""
+    receipt = getattr(state, "cycle_partial_source_publication", None)
+    if (
+        type(receipt) is not CanonicalPartialSCCReceipt
+        or receipt.version != PARTIAL_SCC_PUBLICATION_VERSION
+        or receipt.authority != PARTIAL_SCC_PUBLICATION_AUTHORITY
+    ):
+        return False
+    try:
+        expected = seal_partial_scc_preparation(
+            state,
+            receipt.preparation,
+            revision=revision,
+            state_id=state_id,
+            repo_id=repo_id,
+            root_path=root_path,
+        )
+    except (AttributeError, KeyError, TypeError, ValueError, IndexError):
+        return False
+    return receipt == expected
```

### New test module

```diff
diff --git a/tests/test_cycle_semantics_partial_scc_publication.py b/tests/test_cycle_semantics_partial_scc_publication.py
new file mode 100644
index 0000000..a382678
--- /dev/null
+++ b/tests/test_cycle_semantics_partial_scc_publication.py
@@ -0,0 +1,331 @@
+"""Store-owned partial SCC receipts bind declarations, not runtime safety."""
+
+from __future__ import annotations
+
+import copy
+import pickle
+from dataclasses import fields, replace
+
+import pytest
+
+import contextor.core.live_state.store as store
+from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.core.cycle_semantics.lifecycle import invalidate_cycle_semantics
+from contextor.core.cycle_semantics.partial_scc_publication import (
+    PARTIAL_SCC_PUBLICATION_AUTHORITY,
+    PARTIAL_SCC_PUBLICATION_VERSION,
+    CanonicalPartialSCCReceipt,
+    seal_partial_scc_preparation,
+    verify_co_published_partial_scc_preparation,
+)
+from contextor.core.cycle_semantics.publication_binding import (
+    verify_co_published_cycle_manifest,
+)
+from contextor.core.cycle_semantics.warning_eligibility import (
+    _verified_model_pass_cycle_paths,
+)
+from contextor.core.domain.graph import ProjectGraph
+from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
+from tests.test_original_worker_partial_scc_preparation import (
+    PASS_AND_HAZARD,
+    PASS_AND_UNKNOWN,
+    TWO_PASS,
+    _prepare,
+    _real_pipeline,
+    _repo,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _case(tmp_path, sources=PASS_AND_UNKNOWN):
+    index, graph, snapshot = _real_pipeline(_repo(tmp_path, sources))
+    preparation = _prepare(index, graph, snapshot)
+    state = RepositoryAnalysisState(
+        dependency_graph=ProjectGraph(
+            hard_edges={name: set(targets) for name, targets in graph.hard_edges.items()},
+            soft_edges={},
+        ),
+        cycles=[["a", "b", "a"], ["x", "y", "x"]],
+        cycles_state="fresh",
+        cycle_semantics=snapshot,
+        cycle_semantics_state="fresh",
+    )
+    return state, preparation
+
+
+def _save(state, root, revision=1, *, partial=None, manifest=None):
+    return save_snapshot(
+        state, root, "partial-state", exact_revision=revision,
+        file_state_payload={
+            "_meta": {"state_id": "partial-state", "revision": revision},
+            "files": {},
+        },
+        prepared_partial_scc_preparation=partial,
+        prepared_cycle_manifest=manifest,
+    )
+
+
+def _verify(state, metadata):
+    return verify_co_published_partial_scc_preparation(
+        state,
+        revision=metadata.revision,
+        state_id=metadata.state_id,
+        repo_id=metadata.repo_id,
+        root_path=metadata.root_path,
+    )
+
+
+def _tamper(root, metadata, mutate):
+    path = root / metadata.state_file
+    payload = pickle.loads(path.read_bytes())
+    mutate(payload["state"])
+    path.write_bytes(pickle.dumps(payload))
+
+
+def test_t01_t02_real_mixed_receipt_survives_load(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path)
+    assert preparation.status == "UNAVAILABLE"
+    metadata = _save(state, tmp_path, partial=preparation)
+    loaded, loaded_metadata = load_snapshot(tmp_path, "partial-state")
+    receipt = loaded.cycle_partial_source_publication
+    assert type(receipt) is CanonicalPartialSCCReceipt
+    assert receipt.version == PARTIAL_SCC_PUBLICATION_VERSION
+    assert receipt.authority == PARTIAL_SCC_PUBLICATION_AUTHORITY
+    assert receipt.revision == metadata.revision == loaded_metadata.revision
+    assert _verify(loaded, loaded_metadata)
+    assert tuple(item.model_classification for item in receipt.preparation.component_preparations) == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "INDETERMINATE",
+    )
+    assert state.cycle_partial_source_publication is None
+
+
+def test_t03_partial_receipt_does_not_create_v2_or_warn1(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path)
+    _save(state, tmp_path, partial=preparation)
+    loaded, metadata = load_snapshot(tmp_path, "partial-state")
+    assert loaded.cycle_source_publication is None
+    assert _verify(loaded, metadata)
+    assert _verified_model_pass_cycle_paths(
+        loaded,
+        expected_revision=metadata.revision,
+        expected_state_id=metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=metadata.root_path,
+    ) == frozenset()
+
+
+def test_t04_complete_pass_hazard_partial_receipt(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path, PASS_AND_HAZARD)
+    _save(state, tmp_path, partial=preparation)
+    loaded, metadata = load_snapshot(tmp_path, "partial-state")
+    assert _verify(loaded, metadata)
+    assert tuple(item.model_classification for item in
+                 loaded.cycle_partial_source_publication.preparation.component_preparations) == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+    )
+
+
+def test_t05_v2_and_partial_receipts_share_generation(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path, TWO_PASS)
+    metadata = _save(state, tmp_path, partial=preparation, manifest=preparation.manifest)
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    assert loaded.cycle_source_publication is not None
+    assert loaded.cycle_partial_source_publication is not None
+    assert _verify(loaded, metadata)
+    assert verify_co_published_cycle_manifest(
+        loaded, revision=metadata.revision, state_id=metadata.state_id,
+        repo_id=metadata.repo_id, root_path=metadata.root_path,
+    )
+    assert loaded.cycle_source_publication.revision == (
+        loaded.cycle_partial_source_publication.revision
+    )
+
+
+def test_t06_next_revision_without_input_drops_partial_receipt(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path)
+    _save(state, tmp_path, partial=preparation)
+    old, _ = load_snapshot(tmp_path, "partial-state")
+    _save(old, tmp_path, revision=2)
+    loaded, metadata = load_snapshot(tmp_path, "partial-state")
+    assert metadata.revision == 2
+    assert loaded.cycle_partial_source_publication is None
+
+
+def test_t07_invalidation_clears_receipt(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path)
+    _save(state, tmp_path, partial=preparation)
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    invalidate_cycle_semantics(loaded, "SOURCE_CHANGED")
+    assert loaded.cycle_partial_source_publication is None
+    assert loaded.cycle_semantics_state == "stale"
+    assert loaded.cycle_semantics is not None
+
+
+def test_t08_cow_clears_receipt_without_mutating_previous(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path)
+    _save(state, tmp_path, partial=preparation)
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    candidate = loaded.clone_for_update()
+    assert candidate.cycle_partial_source_publication is None
+    assert loaded.cycle_partial_source_publication is not None
+
+
+@pytest.mark.parametrize("tamper", ["classification", "digest"])
+def test_t09_t10_tamper_is_removed_on_hydration(tmp_path, isolated_dirs, tamper):
+    state, preparation = _case(tmp_path)
+    metadata = _save(state, tmp_path, partial=preparation)
+
+    def mutate(stored):
+        receipt = stored.cycle_partial_source_publication
+        if tamper == "digest":
+            stored.cycle_partial_source_publication = replace(
+                receipt, claims_sha256="0" * 64,
+            )
+        else:
+            original = receipt.preparation
+            components = list(original.component_preparations)
+            components[0] = replace(
+                components[0], model_classification="MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+            )
+            stored.cycle_partial_source_publication = replace(
+                receipt,
+                preparation=replace(original, component_preparations=tuple(components)),
+            )
+
+    _tamper(tmp_path, metadata, mutate)
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    assert loaded.cycle_partial_source_publication is None
+    assert loaded.cycles == [["a", "b", "a"], ["x", "y", "x"]]
+
+
+@pytest.mark.parametrize("identity", ["revision", "state_id", "repo_id", "root_path"])
+def test_t11_foreign_identity_fails_closed(tmp_path, isolated_dirs, identity):
+    state, preparation = _case(tmp_path)
+    metadata = _save(state, tmp_path, partial=preparation)
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    arguments = dict(revision=metadata.revision, state_id=metadata.state_id,
+                     repo_id=metadata.repo_id, root_path=metadata.root_path)
+    arguments[identity] = 2 if identity == "revision" else "foreign"
+    assert not verify_co_published_partial_scc_preparation(loaded, **arguments)
+
+
+@pytest.mark.parametrize("mutation", ["graph", "internal_edge"])
+def test_t12_changed_graph_fails_verification(tmp_path, isolated_dirs, mutation):
+    state, preparation = _case(tmp_path)
+    metadata = _save(state, tmp_path, partial=preparation)
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    if mutation == "graph":
+        loaded.dependency_graph.hard_edges["a"].add("other")
+    else:
+        loaded.dependency_graph.hard_edges["a"].add("a")
+    assert not _verify(loaded, metadata)
+
+
+@pytest.mark.parametrize("mutation", ["semantic", "cycle", "resync"])
+def test_t13_stale_family_or_resync_fails_closed(tmp_path, isolated_dirs, mutation):
+    state, preparation = _case(tmp_path)
+    metadata = _save(state, tmp_path, partial=preparation)
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    if mutation == "semantic":
+        loaded.cycle_semantics_state = "stale"
+    elif mutation == "cycle":
+        loaded.cycles_state = "stale"
+    else:
+        loaded.resync_required = True
+    assert not _verify(loaded, metadata)
+
+
+def test_t14_absent_legacy_attribute_does_not_fabricate_receipt(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path)
+    metadata = _save(state, tmp_path, partial=preparation)
+    _tamper(tmp_path, metadata, lambda stored: stored.__dict__.pop(
+        "cycle_partial_source_publication", None,
+    ))
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    assert loaded.cycle_partial_source_publication is None
+
+
+def test_t15_invalid_input_cannot_advance_metadata(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path)
+    _save(state, tmp_path, partial=preparation)
+    invalid = replace(preparation, reason="FORGED")
+    with pytest.raises((ValueError, TypeError)):
+        _save(state, tmp_path, revision=2, partial=invalid)
+    assert read_metadata(tmp_path).revision == 1
+    loaded, metadata = load_snapshot(tmp_path, "partial-state")
+    assert _verify(loaded, metadata)
+
+
+def test_t16_failed_metadata_commit_keeps_previous_generation(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    state, preparation = _case(tmp_path)
+    _save(state, tmp_path, partial=preparation)
+    original_replace = store.os.replace
+
+    def fail_metadata(source, target):
+        if target.name == "engine_state.meta.json":
+            raise RuntimeError("synthetic metadata failure")
+        return original_replace(source, target)
+
+    with monkeypatch.context() as patch:
+        patch.setattr(store.os, "replace", fail_metadata)
+        with pytest.raises(RuntimeError, match="synthetic metadata failure"):
+            _save(state, tmp_path, revision=2, partial=preparation)
+    loaded, metadata = load_snapshot(tmp_path, "partial-state")
+    assert metadata.revision == 1
+    assert _verify(loaded, metadata)
+
+
+def test_t17_standalone_seal_is_pure_and_not_durable(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path)
+    state.revision = 1
+    state.state_id = "partial-state"
+    before = copy.deepcopy(state.__dict__)
+    receipt = seal_partial_scc_preparation(
+        state, preparation, revision=1, state_id="partial-state",
+        repo_id="", root_path="",
+    )
+    assert type(receipt) is CanonicalPartialSCCReceipt
+    assert state.__dict__ == before
+    assert read_metadata(tmp_path) is None
+
+
+def test_t18_ordinary_store_and_dataclass_contract_unchanged(tmp_path, isolated_dirs):
+    state, _ = _case(tmp_path)
+    field_names = {item.name for item in fields(RepositoryAnalysisState)}
+    assert "cycle_partial_source_publication" not in field_names
+    _save(state, tmp_path)
+    loaded, metadata = load_snapshot(tmp_path, "partial-state")
+    assert loaded.cycle_partial_source_publication is None
+    assert metadata.revision == 1
+
+
+def test_t19_repeat_verification_read_only(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path)
+    metadata = _save(state, tmp_path, partial=preparation)
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    before = copy.deepcopy(loaded.__dict__)
+    assert _verify(loaded, metadata) is True
+    assert _verify(loaded, metadata) is True
+    assert loaded.__dict__ == before
+
+
+def test_t20_tampered_receipt_preserves_structural_diagnostics(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path)
+    metadata = _save(state, tmp_path, partial=preparation)
+    _tamper(tmp_path, metadata, lambda stored: setattr(
+        stored,
+        "cycle_partial_source_publication",
+        replace(stored.cycle_partial_source_publication, claims_sha256="0" * 64),
+    ))
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    assert loaded.cycle_partial_source_publication is None
+    assert loaded.cycles_state == "fresh"
+    assert loaded.cycles == [["a", "b", "a"], ["x", "y", "x"]]
+    assert loaded.dependency_graph.hard_edges == state.dependency_graph.hard_edges
```

## 19. CONTRACT_CONFLICTS## 19. CONTRACT_CONFLICTS

NONE observed.

## 20. REMAINING UNKNOWN

UNKNOWN: Active LIVE loaded-code adoption, runtime import safety, original-worker producer authenticity beyond existing validation, atomic cross-file capture, warning eligibility and active warning behavior. The new module did not separately exercise legacy hydration. No active FULL/LIVE probe ran.

## 21. FINAL IMPLEMENTER OBSERVATION

CONTRACT_PROVED: Authorized store-owned partial receipt path and focused regressions passed. Architectural GO and later warning integration remain with ChatGPT.



# CONTEXTOR C16-B03-P1D3G1

## FILES_CHANGED

- contextor/core/cycle_semantics/optional_scc_publication.py
- contextor/core/live_state/store.py
- contextor/core/analysis/state_manager.py
- contextor/core/cycle_semantics/lifecycle.py
- tests/test_cycle_semantics_optional_scc_publication.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2, `-B -m pytest -q -rs -p no:cacheprovider`, basetemp outside repository. New module: 11 passed in 14.11 s. Seven specified modules: 112 passed in 47.61 s. `git diff --check` passed. No full suite. No production FULL or LIVE certification.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP module contexts for all five changed modules: canonical_revision=1048, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, syntax_errors=0. Structural DFS cycles=16, equal to prechange count; no new structural cycle observed. Cycle_semantics family=stale. No update_file, backend restart, or manual commit. The new receipt establishes canonical store co-publication only; source origin, atomicity, installed LIVE, runtime safety, and warning suppression remain outside this task.

## FULL_DIFFS

```diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index cfac2a4..34f33b9 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -139,12 +139,14 @@ class RepositoryAnalysisState:
     # which the instance attribute is absent.
     cycle_source_publication: ClassVar[Any] = None
     cycle_partial_source_publication: ClassVar[Any] = None
+    cycle_optional_source_publication: ClassVar[Any] = None
 
     def __post_init__(self) -> None:
         # Persisted as an ordinary instance __dict__ attribute,
         # not as a dataclass field.
         self.cycle_source_publication = None
         self.cycle_partial_source_publication = None
+        self.cycle_optional_source_publication = None
 
     def clone_for_update(self) -> "RepositoryAnalysisState":
         """
@@ -166,6 +168,7 @@ class RepositoryAnalysisState:
         # It cannot inherit a receipt from the old generation.
         candidate.cycle_source_publication = None
         candidate.cycle_partial_source_publication = None
+        candidate.cycle_optional_source_publication = None
 
         for state_field in fields(self):
             value = getattr(
@@ -537,6 +540,7 @@ def save_engine_state(
     file_state_payload: dict[str, Any] | None = None,
     prepared_cycle_manifest: Any = None,
     prepared_partial_scc_preparation: Any = None,
+    prepared_optional_scc_preparation: Any = None,
 ):
     """Persist canonical state; optionally forward prepared SCC claims.
 
@@ -568,6 +572,11 @@ def save_engine_state(
                 prepared_partial_scc_preparation
             )
 
+        if prepared_optional_scc_preparation is not None:
+            save_kwargs["prepared_optional_scc_preparation"] = (
+                prepared_optional_scc_preparation
+            )
+
         return save_snapshot(
             state,
             cache_dir,
diff --git a/contextor/core/cycle_semantics/lifecycle.py b/contextor/core/cycle_semantics/lifecycle.py
index b8ddb50..2f45edf 100644
--- a/contextor/core/cycle_semantics/lifecycle.py
+++ b/contextor/core/cycle_semantics/lifecycle.py
@@ -117,6 +117,7 @@ def invalidate_cycle_semantics(
     # its old publication receipt into a new generation.
     state.cycle_source_publication = None
     state.cycle_partial_source_publication = None
+    state.cycle_optional_source_publication = None
 
     evidence = getattr(
         state,
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 10df4fa..990b3a0 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -1520,6 +1520,7 @@ def save_snapshot(
     migration_only_if_absent: bool = False,
     prepared_cycle_manifest: Any = None,
     prepared_partial_scc_preparation: Any = None,
+    prepared_optional_scc_preparation: Any = None,
 ) -> LiveStateMetadata:
     """Atomically publish a complete snapshot and monotonically increasing revision."""
 
@@ -1745,14 +1746,27 @@ def save_snapshot(
             RepositoryAnalysisState
         ):
             raise TypeError("partial SCC preparation requires canonical state")
+        if (
+            prepared_optional_scc_preparation is not None
+            and type(state) is not RepositoryAnalysisState
+        ):
+            raise TypeError(
+                "optional SCC preparation requires canonical state"
+            )
 
         # Both receipts belong to one copy and one locked store generation.
         # Neither is installed on the caller's original state.
         receipt_input = (
             prepared_cycle_manifest is not None
             or prepared_partial_scc_preparation is not None
+            or prepared_optional_scc_preparation is not None
             or getattr(state, "cycle_source_publication", None) is not None
             or getattr(state, "cycle_partial_source_publication", None) is not None
+            or getattr(
+                state,
+                "cycle_optional_source_publication",
+                None,
+            ) is not None
         )
         state_to_persist = (
             copy.copy(state)
@@ -1794,6 +1808,25 @@ def save_snapshot(
         elif state_to_persist is not state:
             state_to_persist.cycle_partial_source_publication = None
 
+        if prepared_optional_scc_preparation is not None:
+            from contextor.core.cycle_semantics.optional_scc_publication import (
+                seal_optional_scc_preparation,
+            )
+
+            state_to_persist.cycle_optional_source_publication = (
+                seal_optional_scc_preparation(
+                    state_to_persist,
+                    prepared_optional_scc_preparation,
+                    revision=metadata.revision,
+                    state_id=metadata.state_id,
+                    repo_id=metadata.repo_id,
+                    root_path=metadata.root_path,
+                )
+            )
+
+        elif state_to_persist is not state:
+            state_to_persist.cycle_optional_source_publication = None
+
         if (
             generation_lineage_manifest
             is not None
@@ -2399,6 +2432,24 @@ def load_snapshot(
                 ):
                     state_obj.cycle_partial_source_publication = None
 
+            if getattr(
+                state_obj,
+                "cycle_optional_source_publication",
+                None,
+            ) is not None:
+                from contextor.core.cycle_semantics.optional_scc_publication import (
+                    verify_co_published_optional_scc_preparation,
+                )
+
+                if not verify_co_published_optional_scc_preparation(
+                    state_obj,
+                    revision=metadata.revision,
+                    state_id=metadata.state_id,
+                    repo_id=metadata.repo_id,
+                    root_path=metadata.root_path,
+                ):
+                    state_obj.cycle_optional_source_publication = None
+
             return state_obj, metadata
         if metadata.lineage_manifest_file:
             return None
@@ -2532,6 +2583,24 @@ def load_snapshot(
             ):
                 payload.cycle_partial_source_publication = None
 
+        if getattr(
+            payload,
+            "cycle_optional_source_publication",
+            None,
+        ) is not None:
+            from contextor.core.cycle_semantics.optional_scc_publication import (
+                verify_co_published_optional_scc_preparation,
+            )
+
+            if not verify_co_published_optional_scc_preparation(
+                payload,
+                revision=metadata.revision,
+                state_id=metadata.state_id,
+                repo_id=metadata.repo_id,
+                root_path=metadata.root_path,
+            ):
+                payload.cycle_optional_source_publication = None
+
         return payload, metadata

diff --git a/contextor/core/cycle_semantics/optional_scc_publication.py b/contextor/core/cycle_semantics/optional_scc_publication.py
new file mode 100644
index 0000000..17410d6
--- /dev/null
+++ b/contextor/core/cycle_semantics/optional_scc_publication.py
@@ -0,0 +1,209 @@
+"""Store-generation receipt for optional SCC declarations.
+
+A receipt establishes co-publication of declarations with a supplied
+canonical generation when created by the locked snapshot writer.
+
+Standalone sealing is pure and does not prove a durable commit.
+Neither sealing nor verification certifies source origin, atomicity,
+installed LIVE, runtime import safety, or warning suppression.
+"""
+
+from __future__ import annotations
+
+from dataclasses import asdict, dataclass
+from typing import Any
+
+from .contracts import (
+    CycleSemanticsSnapshot,
+    fingerprint_hard_edges,
+)
+from .generation_manifest import _digest
+from .original_worker_preparation import (
+    OriginalWorkerManifestPreparation,
+)
+from .partial_scc_claims import (
+    OPTIONAL_PARTIAL_SCC_CLAIMS_AUTHORITY,
+    OPTIONAL_PARTIAL_SCC_CLAIMS_VERSION,
+    PreparedOptionalPartialSCCClaims,
+    validate_optional_partial_scc_claims,
+)
+
+
+OPTIONAL_SCC_PUBLICATION_VERSION = (
+    "cycle-optional-scc-co-publication/1"
+)
+
+OPTIONAL_SCC_PUBLICATION_AUTHORITY = (
+    "COMMITTED_OPTIONAL_SCC_DECLARATIONS"
+    "_NOT_SOURCE_CERTIFIED_NOT_RUNTIME_SAFETY"
+)
+
+
+@dataclass(frozen=True)
+class CanonicalOptionalSCCReceipt:
+    preparation: OriginalWorkerManifestPreparation
+    claims_sha256: str
+    revision: int
+    state_id: str
+    repo_id: str
+    root_path: str
+    version: str = OPTIONAL_SCC_PUBLICATION_VERSION
+    authority: str = OPTIONAL_SCC_PUBLICATION_AUTHORITY
+
+
+def seal_optional_scc_preparation(
+    state: Any,
+    preparation: OriginalWorkerManifestPreparation,
+    *,
+    revision: int,
+    state_id: str,
+    repo_id: str,
+    root_path: str,
+) -> CanonicalOptionalSCCReceipt:
+    """Seal declared optional SCC evidence for a supplied generation.
+
+    Only invocation by the locked canonical writer establishes
+    co-publication. This pure function does not persist anything.
+    """
+
+    if type(preparation) is not OriginalWorkerManifestPreparation:
+        raise TypeError("optional SCC preparation contract missing")
+
+    if (
+        preparation.source_selection != "OPTIONAL_NAMED_CHILDREN"
+        or preparation.status != "PREPARED_UNPUBLISHED_NON_ATOMIC"
+        or preparation.reason is not None
+        or preparation.manifest is None
+    ):
+        raise ValueError("optional SCC preparation unavailable")
+
+    snapshot = getattr(state, "cycle_semantics", None)
+    graph = getattr(state, "dependency_graph", None)
+    hard_edges = getattr(graph, "hard_edges", None)
+    modules = getattr(state, "modules", None)
+    package_root = getattr(state, "package_root", None)
+
+    if (
+        type(snapshot) is not CycleSemanticsSnapshot
+        or getattr(state, "cycle_semantics_state", None) != "fresh"
+        or getattr(state, "cycles_state", None) != "fresh"
+        or getattr(state, "resync_required", False) is not False
+        or type(hard_edges) is not dict
+        or type(modules) is not dict
+        or set(hard_edges) != set(modules)
+        or (
+            package_root is not None
+            and type(package_root) is not str
+        )
+    ):
+        raise ValueError("canonical optional SCC evidence unavailable")
+
+    graph_sha256 = fingerprint_hard_edges(hard_edges)
+
+    if graph_sha256 != snapshot.graph_sha256:
+        raise ValueError("canonical optional SCC graph mismatch")
+
+    if (
+        type(revision) is not int
+        or revision < 1
+        or type(state_id) is not str
+        or not state_id
+        or type(repo_id) is not str
+        or not repo_id
+        or type(root_path) is not str
+        or not root_path
+        or type(getattr(state, "revision", None)) is not int
+        or state.revision != revision
+        or type(getattr(state, "state_id", None)) is not str
+        or state.state_id != state_id
+    ):
+        raise ValueError("optional SCC generation identity mismatch")
+
+    indexed_imports = {
+        module_id: module.imports
+        for module_id, module in modules.items()
+    }
+
+    claims = validate_optional_partial_scc_claims(
+        hard_edges,
+        snapshot,
+        preparation,
+        indexed_imports,
+        package_root=package_root or None,
+    )
+
+    if (
+        type(claims) is not PreparedOptionalPartialSCCClaims
+        or claims.version != OPTIONAL_PARTIAL_SCC_CLAIMS_VERSION
+        or claims.authority != OPTIONAL_PARTIAL_SCC_CLAIMS_AUTHORITY
+        or claims.declared_manifest_sha256 is None
+        or claims.source_modules != preparation.source_modules
+        or claims.components != preparation.component_preparations
+    ):
+        raise ValueError("optional SCC declarations unavailable")
+
+    claims_sha256 = _digest((
+        OPTIONAL_SCC_PUBLICATION_VERSION,
+        graph_sha256,
+        asdict(claims),
+        asdict(preparation),
+    ))
+
+    return CanonicalOptionalSCCReceipt(
+        preparation=preparation,
+        claims_sha256=claims_sha256,
+        revision=revision,
+        state_id=state_id,
+        repo_id=repo_id,
+        root_path=root_path,
+    )
+
+
+def verify_co_published_optional_scc_preparation(
+    state: Any,
+    *,
+    revision: int,
+    state_id: str,
+    repo_id: str,
+    root_path: str,
+) -> bool:
+    """Revalidate an existing receipt against supplied generation data.
+
+    This function cannot independently prove which writer created
+    an in-memory receipt. Store ownership requires the store path.
+    """
+
+    receipt = getattr(
+        state,
+        "cycle_optional_source_publication",
+        None,
+    )
+
+    if (
+        type(receipt) is not CanonicalOptionalSCCReceipt
+        or receipt.version != OPTIONAL_SCC_PUBLICATION_VERSION
+        or receipt.authority != OPTIONAL_SCC_PUBLICATION_AUTHORITY
+    ):
+        return False
+
+    try:
+        expected = seal_optional_scc_preparation(
+            state,
+            receipt.preparation,
+            revision=revision,
+            state_id=state_id,
+            repo_id=repo_id,
+            root_path=root_path,
+        )
+    except (
+        AttributeError,
+        KeyError,
+        TypeError,
+        ValueError,
+        IndexError,
+        RecursionError,
+        OverflowError,
+    ):
+        return False
+
+    return receipt == expected

diff --git a/tests/test_cycle_semantics_optional_scc_publication.py b/tests/test_cycle_semantics_optional_scc_publication.py
new file mode 100644
index 0000000..3001733
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_scc_publication.py
@@ -0,0 +1,380 @@
+"""P1D3G1: store-owned optional SCC declarations, not safety."""
+
+import pickle
+
+from dataclasses import fields, replace
+
+import pytest
+
+import contextor.core.live_state.store as store_module
+
+from contextor.core.analysis.state_manager import (
+    RepositoryAnalysisState,
+)
+from contextor.core.cycle_semantics.lifecycle import (
+    invalidate_cycle_semantics,
+)
+from contextor.core.cycle_semantics.optional_scc_publication import (
+    OPTIONAL_SCC_PUBLICATION_AUTHORITY,
+    OPTIONAL_SCC_PUBLICATION_VERSION,
+    CanonicalOptionalSCCReceipt,
+    seal_optional_scc_preparation,
+    verify_co_published_optional_scc_preparation,
+)
+from contextor.core.cycle_semantics.warning_eligibility import (
+    _verified_model_pass_cycle_paths,
+)
+from contextor.core.live_state.store import (
+    load_snapshot,
+    read_metadata,
+    save_snapshot,
+)
+from tests.test_cycle_semantics_optional_generation_verification import (
+    _case,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _save(cache, state, origin, *, revision=1, preparation=None):
+    state_id = f"optional-state-{revision}"
+
+    return save_snapshot(
+        state,
+        cache,
+        state_id,
+        repo_id=origin.repo_id,
+        root_path=origin.root_path,
+        exact_revision=revision,
+        file_state_payload={
+            "_meta": {
+                "state_id": state_id,
+                "revision": revision,
+            },
+            "files": {},
+        },
+        prepared_optional_scc_preparation=preparation,
+    )
+
+
+def _load(cache, origin, revision=1):
+    result = load_snapshot(
+        cache,
+        f"optional-state-{revision}",
+        expected_repo_id=origin.repo_id,
+        expected_root_path=origin.root_path,
+    )
+
+    assert result is not None
+    return result
+
+
+def _verify(state, metadata):
+    return verify_co_published_optional_scc_preparation(
+        state,
+        revision=metadata.revision,
+        state_id=metadata.state_id,
+        repo_id=metadata.repo_id,
+        root_path=metadata.root_path,
+    )
+
+
+def test_t01_canonical_writer_seals_and_loader_verifies(
+    tmp_path, isolated_dirs,
+):
+    _, preparation, state, origin = _case(tmp_path)
+    cache = tmp_path / "optional-store"
+
+    metadata = _save(
+        cache, state, origin, preparation=preparation,
+    )
+    loaded, loaded_metadata = _load(cache, origin)
+
+    receipt = loaded.cycle_optional_source_publication
+
+    assert type(receipt) is CanonicalOptionalSCCReceipt
+    assert receipt.version == OPTIONAL_SCC_PUBLICATION_VERSION
+    assert receipt.authority == OPTIONAL_SCC_PUBLICATION_AUTHORITY
+
+    assert (
+        receipt.revision,
+        receipt.state_id,
+        receipt.repo_id,
+        receipt.root_path,
+    ) == (
+        metadata.revision,
+        metadata.state_id,
+        metadata.repo_id,
+        metadata.root_path,
+    )
+
+    assert loaded_metadata == metadata
+    assert receipt.preparation == preparation
+    assert _verify(loaded, metadata)
+    assert _verify(loaded, metadata)
+
+    assert state.cycle_optional_source_publication is None
+
+
+def test_t02_optional_receipt_does_not_create_legacy_receipts(
+    tmp_path, isolated_dirs,
+):
+    _, preparation, state, origin = _case(tmp_path)
+    cache = tmp_path / "optional-store"
+
+    _save(cache, state, origin, preparation=preparation)
+    loaded, metadata = _load(cache, origin)
+
+    assert _verify(loaded, metadata)
+    assert loaded.cycle_source_publication is None
+    assert loaded.cycle_partial_source_publication is None
+
+    assert _verified_model_pass_cycle_paths(
+        loaded,
+        expected_revision=metadata.revision,
+        expected_state_id=metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=metadata.root_path,
+    ) == frozenset()
+
+
+def test_t03_default_store_has_no_optional_receipt(
+    tmp_path, isolated_dirs,
+):
+    _, _, state, origin = _case(tmp_path)
+    cache = tmp_path / "optional-store"
+
+    _save(cache, state, origin)
+    loaded, metadata = _load(cache, origin)
+
+    assert loaded.cycle_optional_source_publication is None
+    assert not _verify(loaded, metadata)
+
+    assert "cycle_optional_source_publication" not in {
+        field.name for field in fields(RepositoryAnalysisState)
+    }
+
+
+def test_t04_tampered_receipt_cleared_on_hydration(
+    tmp_path, isolated_dirs,
+):
+    _, preparation, state, origin = _case(tmp_path)
+    cache = tmp_path / "optional-store"
+
+    metadata = _save(
+        cache, state, origin, preparation=preparation,
+    )
+
+    path = cache / metadata.state_file
+    payload = pickle.loads(path.read_bytes())
+    stored = payload["state"]
+
+    stored.cycle_optional_source_publication = replace(
+        stored.cycle_optional_source_publication,
+        claims_sha256="0" * 64,
+    )
+
+    path.write_bytes(pickle.dumps(payload))
+
+    loaded, loaded_metadata = _load(cache, origin)
+
+    assert loaded_metadata == metadata
+    assert loaded.cycle_optional_source_publication is None
+    assert loaded.cycles_state == "fresh"
+    assert loaded.cycle_semantics is not None
+    assert loaded.cycle_source_publication is None
+    assert loaded.cycle_partial_source_publication is None
+
+
+def test_t05_invalid_manifest_cannot_commit(
+    tmp_path, isolated_dirs,
+):
+    _, preparation, state, origin = _case(tmp_path)
+    cache = tmp_path / "optional-store"
+
+    forged = replace(
+        preparation,
+        manifest=replace(
+            preparation.manifest,
+            source_manifest_sha256="0" * 64,
+        ),
+    )
+
+    with pytest.raises((ValueError, TypeError)):
+        _save(
+            cache,
+            state,
+            origin,
+            preparation=forged,
+        )
+
+    assert read_metadata(cache) is None
+
+
+def test_t06_next_revision_without_optin_drops_receipt(
+    tmp_path, isolated_dirs,
+):
+    _, preparation, state, origin = _case(tmp_path)
+    cache = tmp_path / "optional-store"
+
+    _save(cache, state, origin, preparation=preparation)
+    previous, previous_metadata = _load(cache, origin)
+
+    assert _verify(previous, previous_metadata)
+
+    _save(
+        cache,
+        previous,
+        origin,
+        revision=2,
+    )
+
+    current, current_metadata = _load(
+        cache, origin, revision=2,
+    )
+
+    assert current_metadata.revision == 2
+    assert current.cycle_optional_source_publication is None
+    assert previous.cycle_optional_source_publication is not None
+
+
+def test_t07_cow_and_invalidation_clear_optional_receipt(
+    tmp_path, isolated_dirs,
+):
+    _, preparation, state, origin = _case(tmp_path)
+    cache = tmp_path / "optional-store"
+
+    _save(cache, state, origin, preparation=preparation)
+    loaded, metadata = _load(cache, origin)
+
+    assert _verify(loaded, metadata)
+
+    candidate = loaded.clone_for_update()
+
+    assert candidate.cycle_optional_source_publication is None
+    assert loaded.cycle_optional_source_publication is not None
+
+    invalidate_cycle_semantics(loaded, "SOURCE_CHANGED")
+
+    assert loaded.cycle_optional_source_publication is None
+    assert loaded.cycle_semantics_state == "stale"
+
+
+def test_t08_foreign_generation_identity_rejected(
+    tmp_path, isolated_dirs,
+):
+    _, preparation, state, origin = _case(tmp_path)
+    cache = tmp_path / "optional-store"
+
+    _save(cache, state, origin, preparation=preparation)
+    loaded, metadata = _load(cache, origin)
+
+    assert _verify(loaded, metadata)
+
+    assert not verify_co_published_optional_scc_preparation(
+        loaded,
+        revision=metadata.revision + 1,
+        state_id=metadata.state_id,
+        repo_id=metadata.repo_id,
+        root_path=metadata.root_path,
+    )
+
+    assert not verify_co_published_optional_scc_preparation(
+        loaded,
+        revision=metadata.revision,
+        state_id="foreign-state",
+        repo_id=metadata.repo_id,
+        root_path=metadata.root_path,
+    )
+
+    assert not verify_co_published_optional_scc_preparation(
+        loaded,
+        revision=metadata.revision,
+        state_id=metadata.state_id,
+        repo_id="foreign-repo",
+        root_path=metadata.root_path,
+    )
+
+
+def test_t09_standalone_seal_is_not_durable(
+    tmp_path, isolated_dirs,
+):
+    _, preparation, state, origin = _case(tmp_path)
+    cache = tmp_path / "optional-store"
+
+    receipt = seal_optional_scc_preparation(
+        state,
+        preparation,
+        revision=origin.revision,
+        state_id=origin.state_id,
+        repo_id=origin.repo_id,
+        root_path=origin.root_path,
+    )
+
+    assert type(receipt) is CanonicalOptionalSCCReceipt
+    assert state.cycle_optional_source_publication is None
+    assert read_metadata(cache) is None
+
+
+def test_t10_failed_metadata_commit_preserves_previous(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    _, preparation, state, origin = _case(tmp_path)
+    cache = tmp_path / "optional-store"
+
+    _save(cache, state, origin, preparation=preparation)
+    previous, previous_metadata = _load(cache, origin)
+
+    original_replace = store_module.os.replace
+
+    def failing_replace(source, target):
+        if target.name == "engine_state.meta.json":
+            raise RuntimeError("synthetic metadata failure")
+        return original_replace(source, target)
+
+    with monkeypatch.context() as patch:
+        patch.setattr(
+            store_module.os,
+            "replace",
+            failing_replace,
+        )
+
+        with pytest.raises(
+            RuntimeError,
+            match="synthetic metadata failure",
+        ):
+            _save(
+                cache,
+                previous,
+                origin,
+                revision=2,
+                preparation=preparation,
+            )
+
+    assert read_metadata(cache) == previous_metadata
+
+    reloaded, metadata = _load(cache, origin)
+
+    assert metadata.revision == 1
+    assert _verify(reloaded, metadata)
+
+
+def test_t11_stale_canonical_semantics_cannot_seal(
+    tmp_path, isolated_dirs,
+):
+    _, preparation, state, origin = _case(tmp_path)
+
+    state.cycle_semantics_state = "stale"
+
+    with pytest.raises(ValueError):
+        seal_optional_scc_preparation(
+            state,
+            preparation,
+            revision=origin.revision,
+            state_id=origin.state_id,
+            repo_id=origin.repo_id,
+            root_path=origin.root_path,
+        )
```

## FINAL_VERDICT

PASS

# CONTEXTOR_P1D2J_FULL_TO_CANONICAL_LIVE_RECEIPT_CONTINUITY

## PREFLIGHT_RESULT

DIRECT_EVIDENCE: Initial HEAD `21a41a654268a323cffce8074a8dfa9634ab708f`, clean worktree. Contextor MCP resolved the requested facade, state manager, store save/load, publication verifier, and `CanonicalLiveServer` in `ipc.py` at canonical revision 690 with `workspace_sync=verified`. Local source confirmed the P1D2I opt-in validation and manifest forwarding, store-owned sealing, and exact existing `_flat_repo`, `_server`, `_publish` helpers. `_server` uses `locked_committed_snapshot` against an isolated cache; `_publish` dispatches the server's actual `publish` operation. New test path absent. PREFLIGHT_MISMATCH=NONE.

## NATIVE_CODEX_LITERAL_EDITS

DIRECT_EVIDENCE: Created only the architect-supplied test using native Codex `apply_patch`. Exact test content matched the attachment after newline normalization.

## FILES_CHANGED

- `tests/test_original_worker_full_to_live_receipt.py`

`walkthrough.md` is this report; no production or existing test file changed.

## ACTUAL_NEW_TEST_CONTENT

Full actual new-file diff:

```diff
diff --git a/tests/test_original_worker_full_to_live_receipt.py b/tests/test_original_worker_full_to_live_receipt.py
new file mode 100644
index 0000000..3a5eb9a
--- /dev/null
+++ b/tests/test_original_worker_full_to_live_receipt.py
@@ -0,0 +1,465 @@
+"""P1D2J: FULL-produced receipts across isolated canonical LIVE."""
+
+from __future__ import annotations
+
+import pickle
+from dataclasses import replace
+from types import SimpleNamespace
+
+import pytest
+
+import contextor.core.cycle_semantics.original_worker_preparation as preparation_module
+
+from contextor.core.analysis.state_manager import (
+    save_engine_state,
+)
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.cycle_semantics.publication_binding import (
+    PUBLICATION_AUTHORITY,
+    CanonicalCycleManifestReceipt,
+    verify_co_published_cycle_manifest,
+)
+from contextor.core.live_state.store import (
+    load_snapshot,
+    read_metadata,
+)
+from contextor.core.paths import repo_cache_dir
+
+from tests.test_original_worker_full_preparation_optin import (
+    _flat_repo,
+)
+from tests.test_cycle_semantics_publication_live_integration import (
+    _publish,
+    _server,
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
+def _full(root, *, publish=False, preview=False):
+    errors, result = ContextorFacade.analyze_project(
+        str(root),
+        cycle_source_preparation_preview=preview,
+        cycle_source_publication_opt_in=publish,
+    )
+    assert result is not None
+    assert isinstance(errors, list)
+    return result
+
+
+def _committed(root):
+    cache = repo_cache_dir(root)
+    metadata = read_metadata(cache)
+
+    assert metadata is not None
+
+    loaded = load_snapshot(
+        cache,
+        metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=str(root.resolve()),
+    )
+
+    assert loaded is not None
+
+    state, loaded_metadata = loaded
+    assert loaded_metadata == metadata
+
+    return state, metadata
+
+
+def _receipt(state, metadata):
+    receipt = state.cycle_source_publication
+
+    assert isinstance(
+        receipt,
+        CanonicalCycleManifestReceipt,
+    )
+    assert receipt.authority == PUBLICATION_AUTHORITY
+    assert receipt.revision == metadata.revision
+    assert receipt.state_id == metadata.state_id
+    assert receipt.repo_id == metadata.repo_id
+    assert receipt.root_path == metadata.root_path
+
+    assert verify_co_published_cycle_manifest(
+        state,
+        revision=metadata.revision,
+        state_id=metadata.state_id,
+        repo_id=metadata.repo_id,
+        root_path=metadata.root_path,
+    )
+
+    return receipt
+
+
+def _installed(server):
+    answer = server._dispatch({
+        "operation": "snapshot",
+    })
+
+    assert answer["status"] == "ok"
+
+    return answer["state"], answer["revision"]
+
+
+def test_p1d2j_t01_full_receipt_installs_in_live(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+
+    result = _full(
+        root,
+        preview=True,
+        publish=True,
+    )
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == (
+        "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    )
+    assert preview.manifest is not None
+
+    committed, metadata = _committed(root)
+    durable_receipt = _receipt(committed, metadata)
+
+    assert durable_receipt.prepared_manifest == (
+        preview.manifest
+    )
+
+    with _server(repo_cache_dir(root)) as server:
+        published = _publish(server, committed)
+
+        assert published["status"] == "ok"
+        assert published["source"] == "committed_snapshot"
+        assert published["revision"] == metadata.revision
+
+        active, revision = _installed(server)
+
+        assert revision == metadata.revision
+        assert active is not committed
+        assert active.cycle_semantics_state == "fresh"
+        assert active.cycles_state == "fresh"
+
+        active_receipt = _receipt(active, metadata)
+
+        assert active_receipt == durable_receipt
+        assert active_receipt.prepared_manifest == (
+            preview.manifest
+        )
+
+
+def test_p1d2j_t02_preview_only_installs_without_receipt(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+
+    result = _full(
+        root,
+        preview=True,
+    )
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == (
+        "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    )
+    assert preview.manifest is not None
+
+    committed, metadata = _committed(root)
+
+    assert committed.cycle_source_publication is None
+
+    with _server(repo_cache_dir(root)) as server:
+        published = _publish(server, committed)
+
+        assert published["status"] == "ok"
+        assert published["revision"] == metadata.revision
+
+        active, revision = _installed(server)
+
+        assert revision == metadata.revision
+        assert active.cycle_source_publication is None
+        assert active.cycle_semantics_state == "fresh"
+
+
+def test_p1d2j_t03_rejected_next_full_preserves_live(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    _full(
+        root,
+        preview=True,
+        publish=True,
+    )
+
+    committed, metadata = _committed(root)
+    old_receipt = _receipt(committed, metadata)
+
+    original = (
+        preparation_module.prepare_original_worker_cycle_manifest
+    )
+
+    def forged(*args, **kwargs):
+        prepared = original(*args, **kwargs)
+
+        if prepared.manifest is None:
+            return prepared
+
+        return replace(
+            prepared,
+            manifest=replace(
+                prepared.manifest,
+                source_manifest_sha256="f" * 64,
+            ),
+        )
+
+    monkeypatch.setattr(
+        preparation_module,
+        "prepare_original_worker_cycle_manifest",
+        forged,
+    )
+
+    with _server(repo_cache_dir(root)) as server:
+        assert _publish(server, committed)["status"] == "ok"
+
+        previous_active, previous_revision = _installed(
+            server
+        )
+
+        result = _full(
+            root,
+            preview=True,
+            publish=True,
+        )
+
+        assert result.live_publish_status == (
+            "not_attempted"
+        )
+
+        current_metadata = read_metadata(
+            repo_cache_dir(root)
+        )
+
+        assert current_metadata == metadata
+
+        active, revision = _installed(server)
+
+        assert revision == previous_revision
+        assert active is previous_active
+        assert _receipt(active, metadata) == old_receipt
+
+    restored, restored_metadata = _committed(root)
+
+    assert restored_metadata == metadata
+    assert _receipt(restored, metadata) == old_receipt
+
+
+def test_p1d2j_t04_default_full_replaces_live_receipt(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+
+    _full(
+        root,
+        preview=True,
+        publish=True,
+    )
+
+    first, first_metadata = _committed(root)
+    old_receipt = _receipt(first, first_metadata)
+
+    with _server(repo_cache_dir(root)) as server:
+        assert _publish(server, first)["status"] == "ok"
+
+        previous_active, previous_revision = _installed(
+            server
+        )
+
+        assert previous_revision == first_metadata.revision
+
+        _full(root)
+
+        second, second_metadata = _committed(root)
+
+        assert second_metadata.revision == (
+            first_metadata.revision + 1
+        )
+        assert second.cycle_source_publication is None
+
+        published = _publish(server, second)
+
+        assert published["status"] == "ok"
+        assert published["revision"] == (
+            second_metadata.revision
+        )
+
+        active, revision = _installed(server)
+
+        assert revision == second_metadata.revision
+        assert active.cycle_source_publication is None
+
+        assert _receipt(
+            previous_active,
+            first_metadata,
+        ) == old_receipt
+
+
+def test_p1d2j_t05_incremental_update_invalidates_receipt(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+
+    _full(
+        root,
+        preview=True,
+        publish=True,
+    )
+
+    first, first_metadata = _committed(root)
+    old_receipt = _receipt(first, first_metadata)
+
+    observed = []
+
+    def updater(candidate, path):
+        observed.append(
+            candidate.cycle_source_publication
+        )
+
+        candidate.cycle_semantics_state = "stale"
+        candidate.cycle_semantics_invalidation_reason = (
+            "SOURCE_CHANGED"
+        )
+
+        return SimpleNamespace(
+            status="UPDATED",
+            file_path=path,
+        )
+
+    def persister(candidate, revision):
+        assert candidate.cycle_source_publication is None
+
+        metadata = save_engine_state(
+            candidate,
+            str(repo_cache_dir(root)),
+            first_metadata.state_id,
+            writer="desktop",
+            repo_id=first_metadata.repo_id,
+            root_path=str(root.resolve()),
+            exact_revision=revision,
+            file_state_payload={
+                "_meta": {
+                    "state_id": first_metadata.state_id,
+                    "revision": revision,
+                },
+                "files": {},
+            },
+        )
+
+        if metadata is None:
+            raise RuntimeError(
+                "isolated incremental persistence failed"
+            )
+
+    with _server(
+        repo_cache_dir(root),
+        updater=updater,
+        persister=persister,
+    ) as server:
+        assert _publish(server, first)["status"] == "ok"
+
+        previous_active, previous_revision = _installed(
+            server
+        )
+
+        changed = server._dispatch({
+            "operation": "update_file",
+            "file_path": "a.py",
+            "origin": "p1d2j_isolated_test",
+        })
+
+        assert changed["status"] == "ok"
+        assert changed["revision"] == (
+            previous_revision + 1
+        )
+        assert observed == [None]
+
+        active, revision = _installed(server)
+
+        assert revision == previous_revision + 1
+        assert active is not previous_active
+        assert active.cycle_source_publication is None
+        assert active.cycle_semantics_state == "stale"
+
+        assert _receipt(
+            previous_active,
+            first_metadata,
+        ) == old_receipt
+
+    restored, second_metadata = _committed(root)
+
+    assert second_metadata.revision == (
+        first_metadata.revision + 1
+    )
+    assert restored.cycle_source_publication is None
+
+
+def test_p1d2j_t06_tampered_durable_receipt_not_installed(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+
+    _full(
+        root,
+        preview=True,
+        publish=True,
+    )
+
+    committed, metadata = _committed(root)
+
+    _receipt(committed, metadata)
+
+    cache = repo_cache_dir(root)
+    state_file = cache / metadata.state_file
+
+    payload = pickle.loads(
+        state_file.read_bytes()
+    )
+
+    original_receipt = (
+        payload["state"].cycle_source_publication
+    )
+
+    payload["state"].cycle_source_publication = replace(
+        original_receipt,
+        revision=metadata.revision + 100,
+    )
+
+    state_file.write_bytes(
+        pickle.dumps(payload)
+    )
+
+    recovered, recovered_metadata = _committed(root)
+
+    assert recovered_metadata == metadata
+    assert recovered.cycle_source_publication is None
+
+    with _server(cache) as server:
+        published = _publish(server, committed)
+
+        assert published["status"] == "ok"
+        assert published["source"] == "committed_snapshot"
+        assert published["revision"] == metadata.revision
+
+        active, revision = _installed(server)
+
+        assert revision == metadata.revision
+        assert active.cycle_source_publication is None
+        assert active.cycle_semantics is not None
```

## PY_COMPILE_RESULT

DIRECT_EVIDENCE: `python -m py_compile tests/test_original_worker_full_to_live_receipt.py` exited 0.

## P1D2J_TEST_RESULTS

DIRECT_EVIDENCE: Six new tests passed in 10.62s.

## FOCUSED_REGRESSION_RESULTS

DIRECT_EVIDENCE: Exact 16-file focused regression command from the task: 243 passed in 64.03s.

## FULL_TO_STORE_TO_LIVE_CONTINUITY

CONTRACT_PROVED: T01 ran real FULL against a temporary repository, loaded the committed store generation, verified its receipt, used isolated `CanonicalLiveServer` publish dispatch, and verified same-generation receipt after installation.

## PREVIEW_ONLY_NO_RECEIPT

CONTRACT_PROVED: T02 found a prepared preview but no durable or installed receipt.

## FAILED_NEXT_GENERATION_ROLLBACK

CONTRACT_PROVED: T03's forged second-generation manifest failed the store write; committed metadata and isolated LIVE installation retained the previous generation and receipt.

## DEFAULT_FULL_RECEIPT_INVALIDATION

CONTRACT_PROVED: T04's later default FULL committed and installed a receipt-free generation while the earlier installed object retained its earlier receipt.

## ISOLATED_INCREMENTAL_INVALIDATION

CONTRACT_PROVED: T05's isolated incremental update cleared the receipt before the updater and persister, advanced one generation, and left the prior object unchanged.

## TAMPERED_DURABLE_RECEIPT

CONTRACT_PROVED: T06 altered an isolated durable pickle receipt's revision. Store load discarded the invalid receipt; isolated LIVE installed the committed generation without resurrecting it.

## CANONICAL_WATCHER_OBSERVATIONS

DIRECT_EVIDENCE: `get_live_events(after_revision=690)` returned one continuous `desktop_watcher` update for the new test file at revision 691, `resync_required=false`. A Contextor source read for `ContextorFacade.analyze_project` returned `workspace_sync=verified` at revision 691; `cycle_semantics` family was stale.

## ACTIVE_RUNTIME_ADOPTION_LIMITS

UNKNOWN: Whether the active application process loaded these source implementations. Watcher indexing and isolated pytest do not prove application runtime adoption. No existing LIVE service was contacted, restarted, or reloaded.

## FINAL_VERDICT

CONTRACT_PROVED: P1D2J's six isolated integration tests and the specified focused regression set passed. DIRECT_EVIDENCE: No production edits and no active-repository FULL. UNKNOWN: cross-file atomic source capture, authenticated source origin, Python import execution safety, and SAFE status. STOP after P1D2J; await architect assessment and explicit `proceduj`.

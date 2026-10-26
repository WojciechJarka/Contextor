# CONTEXTOR_P1D2K_REAL_IPC_INSTALLED_CYCLE_GENERATION

## PREFLIGHT_RESULT

DIRECT_EVIDENCE: Initial HEAD `dd49d28cc873cff089c21edc6d9843af5d03ea93`, clean worktree. Contextor MCP resolved `CanonicalLiveServer`, `LiveStateClient`, `assess_live_installed_prepared_claims`, `verify_co_published_cycle_manifest`, and `save_snapshot` at revision 691 with `workspace_sync=verified`. Local source confirmed constructor arguments `committed_snapshot_reader`, `updater`, `persister`, `authority_identity`; localhost endpoint, `serve_forever`, `close`; client `ping`, `publish`, `update_file`, `request`, and `verify_installed_cycle_generation`. The latter supplies endpoint `service_instance_id`. Server dispatch rejects extra payload fields and calls `assess_live_installed_prepared_claims` under `self._lock`; helper exposes `INSTALLED_PREPARED_CLAIMS_MATCH_EXPECTED_GENERATION`. P1D2J helpers `_full`, `_committed`, `_receipt` exist. New test path absent. PREFLIGHT_MISMATCH=NONE.

## NATIVE_CODEX_LITERAL_EDITS

DIRECT_EVIDENCE: Created only the exact architect-supplied test through native Codex `apply_patch`. Literal test source matched the attachment after newline normalization.

## FILES_CHANGED

- `tests/test_original_worker_real_ipc_generation.py`

`walkthrough.md` is this report; no production or existing test file changed.

## ACTUAL_NEW_TEST_CONTENT

Full actual new-file diff:

```diff
diff --git a/tests/test_original_worker_real_ipc_generation.py b/tests/test_original_worker_real_ipc_generation.py
new file mode 100644
index 0000000..6f31764
--- /dev/null
+++ b/tests/test_original_worker_real_ipc_generation.py
@@ -0,0 +1,516 @@
+"""P1D2K: real localhost IPC verification of installed SCC claims."""
+
+from __future__ import annotations
+
+from contextlib import contextmanager
+from threading import Thread
+from types import SimpleNamespace
+from uuid import uuid4
+
+import pytest
+
+from contextor.core.analysis.state_manager import (
+    save_engine_state,
+)
+from contextor.core.live_state.ipc import (
+    CanonicalLiveServer,
+    LiveStateClient,
+)
+from contextor.core.live_state.store import (
+    locked_committed_snapshot,
+)
+from contextor.core.paths import repo_cache_dir
+
+from tests.test_original_worker_full_preparation_optin import (
+    _flat_repo,
+)
+from tests.test_original_worker_full_to_live_receipt import (
+    _committed,
+    _full,
+    _receipt,
+)
+
+
+pytestmark = pytest.mark.live
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
+@contextmanager
+def _socket_server(
+    root,
+    *,
+    updater=None,
+    persister=None,
+):
+    cache = repo_cache_dir(root)
+    _state, metadata = _committed(root)
+
+    service_instance_id = (
+        "p1d2k-isolated-" + uuid4().hex
+    )
+
+    server = CanonicalLiveServer(
+        committed_snapshot_reader=(
+            lambda: locked_committed_snapshot(
+                cache,
+                expected_repo_id=metadata.repo_id,
+                expected_root_path=metadata.root_path,
+            )
+        ),
+        updater=updater,
+        persister=persister,
+        authority_identity={
+            "repo_id": metadata.repo_id,
+            "root_path": metadata.root_path,
+            "service_instance_id": service_instance_id,
+        },
+    )
+
+    assert server.endpoint.host == "127.0.0.1"
+    assert server.endpoint.service_instance_id == (
+        service_instance_id
+    )
+
+    worker = Thread(
+        target=server.serve_forever,
+        name="p1d2k-isolated-live",
+        daemon=True,
+    )
+
+    worker.start()
+
+    client = LiveStateClient(server.endpoint)
+
+    try:
+        ping = client.ping()
+
+        assert ping["status"] == "ok"
+
+        yield client, server
+
+    finally:
+        closed = server.close()
+        worker.join(timeout=5.0)
+
+        assert closed is True
+        assert not worker.is_alive()
+
+
+def _verify(client, state, metadata):
+    return client.verify_installed_cycle_generation(
+        expected_revision=metadata.revision,
+        expected_state_id=metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=metadata.root_path,
+        expected_graph_sha256=(
+            state.cycle_semantics.graph_sha256
+        ),
+    )
+
+
+def _publish(client, state):
+    answer = client.publish(
+        state,
+        origin="p1d2k_isolated_test",
+    )
+
+    assert answer["status"] == "ok"
+    assert answer["source"] == "committed_snapshot"
+
+    return answer
+
+
+def test_p1d2k_t01_real_ipc_positive_generation(
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
+    receipt = _receipt(committed, metadata)
+
+    with _socket_server(root) as (client, server):
+        published = _publish(client, committed)
+
+        assert published["revision"] == metadata.revision
+
+        checked = _verify(
+            client,
+            committed,
+            metadata,
+        )
+
+        assert checked["status"] == "ok"
+        assert checked["binding_state"] == (
+            "INSTALLED_PREPARED_CLAIMS_MATCH_EXPECTED_GENERATION"
+        )
+        assert checked["revision"] == metadata.revision
+        assert checked["state_id"] == metadata.state_id
+        assert checked["repo_id"] == metadata.repo_id
+        assert checked["root_path"] == metadata.root_path
+
+        assert checked["service_instance_id"] == (
+            server.endpoint.service_instance_id
+        )
+
+        assert checked["graph_sha256"] == (
+            preview.manifest.graph_sha256
+        )
+        assert checked["source_manifest_sha256"] == (
+            preview.manifest.source_manifest_sha256
+        )
+        assert checked["model_claims_sha256"] == (
+            receipt.model_claims_sha256
+        )
+
+        assert checked["activity_epoch"]
+
+        assert (
+            "LIVE_OWNER_LOCK_SCOPED_INSTALLED_PREPARED_CLAIMS"
+            in checked["authority"]
+        )
+
+        assert "source_snapshots" not in checked
+        assert "source_bytes" not in checked
+
+
+def test_p1d2k_t02_preview_only_no_ipc_claim(
+    tmp_path, isolated_dirs,
+):
+    root = _flat_repo(tmp_path)
+
+    result = _full(
+        root,
+        preview=True,
+        publish=False,
+    )
+
+    assert result.cycle_source_preparation_preview.status == (
+        "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    )
+
+    committed, metadata = _committed(root)
+
+    assert committed.cycle_source_publication is None
+
+    with _socket_server(root) as (client, _server):
+        _publish(client, committed)
+
+        checked = _verify(
+            client,
+            committed,
+            metadata,
+        )
+
+        assert checked["status"] == "unavailable"
+        assert checked["reason"] == (
+            "CO_PUBLISHED_RECEIPT_UNAVAILABLE"
+        )
+        assert checked["revision"] == metadata.revision
+        assert "binding_state" not in checked
+
+
+def test_p1d2k_t03_wrong_identity_fails_closed(
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
+    receipt = _receipt(committed, metadata)
+
+    with _socket_server(root) as (client, server):
+        _publish(client, committed)
+
+        common = {
+            "expected_revision": metadata.revision,
+            "expected_state_id": metadata.state_id,
+            "expected_repo_id": metadata.repo_id,
+            "expected_root_path": metadata.root_path,
+            "expected_graph_sha256": (
+                receipt.prepared_manifest.graph_sha256
+            ),
+            "expected_service_instance_id": (
+                server.endpoint.service_instance_id
+            ),
+        }
+
+        cases = (
+            (
+                "expected_service_instance_id",
+                "another-service-instance",
+                "LIVE_INSTANCE_MISMATCH",
+            ),
+            (
+                "expected_repo_id",
+                "another-repository",
+                "LIVE_REPOSITORY_MISMATCH",
+            ),
+            (
+                "expected_revision",
+                metadata.revision + 1,
+                "INSTALLED_GENERATION_MISMATCH",
+            ),
+            (
+                "expected_graph_sha256",
+                "0" * 64,
+                "INSTALLED_GRAPH_IDENTITY_MISMATCH",
+            ),
+        )
+
+        for field, invalid, reason in cases:
+            payload = dict(common)
+            payload[field] = invalid
+
+            response = client.request(
+                "verify_installed_cycle_generation",
+                **payload,
+            )
+
+            assert response["status"] == "unavailable"
+            assert response["reason"] == reason
+
+        valid = _verify(
+            client,
+            committed,
+            metadata,
+        )
+
+        assert valid["status"] == "ok"
+
+
+def test_p1d2k_t04_later_default_full_replaces_ipc_claim(
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
+    _receipt(first, first_metadata)
+
+    with _socket_server(root) as (client, _server):
+        _publish(client, first)
+
+        assert _verify(
+            client,
+            first,
+            first_metadata,
+        )["status"] == "ok"
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
+        published = _publish(client, second)
+
+        assert published["revision"] == (
+            second_metadata.revision
+        )
+
+        old = _verify(
+            client,
+            first,
+            first_metadata,
+        )
+
+        assert old["status"] == "unavailable"
+        assert old["reason"] == (
+            "INSTALLED_GENERATION_MISMATCH"
+        )
+
+        current = _verify(
+            client,
+            second,
+            second_metadata,
+        )
+
+        assert current["status"] == "unavailable"
+        assert current["reason"] == (
+            "CO_PUBLISHED_RECEIPT_UNAVAILABLE"
+        )
+
+
+def test_p1d2k_t05_incremental_ipc_update_invalidates(
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
+    initial, initial_metadata = _committed(root)
+    _receipt(initial, initial_metadata)
+
+    def updater(candidate, path):
+        assert candidate.cycle_source_publication is None
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
+        saved = save_engine_state(
+            candidate,
+            str(repo_cache_dir(root)),
+            initial_metadata.state_id,
+            writer="desktop",
+            repo_id=initial_metadata.repo_id,
+            root_path=str(root.resolve()),
+            exact_revision=revision,
+            file_state_payload={
+                "_meta": {
+                    "state_id": initial_metadata.state_id,
+                    "revision": revision,
+                },
+                "files": {},
+            },
+        )
+
+        if saved is None:
+            raise RuntimeError(
+                "isolated incremental persistence failed"
+            )
+
+    with _socket_server(
+        root,
+        updater=updater,
+        persister=persister,
+    ) as (client, _server):
+        _publish(client, initial)
+
+        assert _verify(
+            client,
+            initial,
+            initial_metadata,
+        )["status"] == "ok"
+
+        changed = client.update_file(
+            "a.py",
+            origin="p1d2k_isolated_test",
+        )
+
+        assert changed["status"] == "ok"
+        assert changed["revision"] == (
+            initial_metadata.revision + 1
+        )
+
+        updated, updated_metadata = _committed(root)
+
+        assert updated_metadata.revision == (
+            initial_metadata.revision + 1
+        )
+        assert updated.cycle_source_publication is None
+        assert updated.cycle_semantics_state == "stale"
+
+        old = _verify(
+            client,
+            initial,
+            initial_metadata,
+        )
+
+        assert old["status"] == "unavailable"
+        assert old["reason"] == (
+            "INSTALLED_GENERATION_MISMATCH"
+        )
+
+        current = _verify(
+            client,
+            updated,
+            updated_metadata,
+        )
+
+        assert current["status"] == "unavailable"
+        assert current["reason"] == (
+            "REQUIRED_CYCLE_FAMILY_NOT_FRESH"
+        )
+
+
+def test_p1d2k_t06_extra_source_payload_refused(
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
+    receipt = _receipt(committed, metadata)
+
+    with _socket_server(root) as (client, server):
+        _publish(client, committed)
+
+        rejected = client.request(
+            "verify_installed_cycle_generation",
+            expected_revision=metadata.revision,
+            expected_state_id=metadata.state_id,
+            expected_repo_id=metadata.repo_id,
+            expected_root_path=metadata.root_path,
+            expected_graph_sha256=(
+                receipt.prepared_manifest.graph_sha256
+            ),
+            expected_service_instance_id=(
+                server.endpoint.service_instance_id
+            ),
+            source_capture_bytes=b"untrusted source bytes",
+        )
+
+        assert rejected["status"] == "unavailable"
+        assert rejected["reason"] == (
+            "INVALID_GENERATION_CHECK_PAYLOAD"
+        )
+
+        valid = _verify(
+            client,
+            committed,
+            metadata,
+        )
+
+        assert valid["status"] == "ok"
```

## PY_COMPILE_RESULT

DIRECT_EVIDENCE: `python -m py_compile tests/test_original_worker_real_ipc_generation.py` exited 0.

## P1D2K_TEST_RESULTS

DIRECT_EVIDENCE: Six new tests passed in 10.56s.

## FOCUSED_REGRESSION_RESULTS

DIRECT_EVIDENCE: Exact 17-file focused regression command from the task: 249 passed in 62.98s.

## REAL_LOCALHOST_IPC_TRANSPORT

CONTRACT_PROVED: All six tests started an isolated `CanonicalLiveServer.serve_forever` thread on `127.0.0.1`, used `LiveStateClient(server.endpoint)` with ping and socket requests, then closed and joined the server. They used only temporary repositories and stores.

## POSITIVE_INSTALLED_GENERATION_CHECK

CONTRACT_PROVED: T01 ran real FULL on a temporary repo, committed a receipt-bearing snapshot, installed it through IPC, and matched revision, state_id, repo_id, root_path, service_instance_id, graph digest, source-manifest digest, model-claims digest and activity_epoch in the owner response. The observation is lock-scoped at reply time.

## PREVIEW_ONLY_NEGATIVE_CHECK

CONTRACT_PROVED: T02 prepared a preview without publication; IPC verification returned `CO_PUBLISHED_RECEIPT_UNAVAILABLE`.

## FOREIGN_IDENTITY_REJECTIONS

CONTRACT_PROVED: T03 rejected foreign service instance, repository, revision and graph digest with their specified unavailable reasons; the valid request still passed.

## NEXT_GENERATION_INVALIDATION

CONTRACT_PROVED: T04 installed a later default FULL generation without a receipt. Verification of the old generation returned `INSTALLED_GENERATION_MISMATCH`; the current generation returned `CO_PUBLISHED_RECEIPT_UNAVAILABLE`.

## INCREMENTAL_INVALIDATION

CONTRACT_PROVED: T05 used isolated IPC `update_file`. The candidate receipt was cleared before updater and persister; old generation verification failed and current stale-cycle generation returned `REQUIRED_CYCLE_FAMILY_NOT_FRESH`.

## UNTRUSTED_PAYLOAD_REJECTION

CONTRACT_PROVED: T06 sent extra source bytes to the verification operation and received `INVALID_GENERATION_CHECK_PAYLOAD`; a subsequent identity-only request passed.

## CANONICAL_WATCHER_OBSERVATIONS

DIRECT_EVIDENCE: `get_live_events(after_revision=691)` returned one continuous `desktop_watcher` update for the new test at revision 692, with `resync_required=false`. Contextor source read for `CanonicalLiveServer` returned `workspace_sync=verified` at revision 692; `cycle_semantics` family remained stale.

## ACTIVE_RUNTIME_ADOPTION_LIMITS

UNKNOWN: Whether the active application/runtime process loaded any of these implementations. Watcher indexing and isolated socket tests do not prove active application adoption. No existing LIVE service was contacted, restarted or mutated.

## FINAL_VERDICT

CONTRACT_PROVED: P1D2K's six isolated real localhost IPC tests and specified regression set passed. DIRECT_EVIDENCE: No production changes, no active repository FULL, and no active service manipulation. UNKNOWN: original worker source-owner authentication, repository-wide atomic capture, arbitrary Python import safety, and state continuity after an IPC verification reply. STOP after P1D2K and await architect assessment.

# CONTEXTOR_P1D2L_FULL_OFFICIAL_COMMITTED_PUBLICATION

## PREFLIGHT_RESULT

DIRECT_EVIDENCE: Initial HEAD `d902f0fec40fa0606cab9e48fe9942287ea695bb`, clean worktree. Contextor MCP resolved `ContextorFacade.analyze_project`, `publish_committed_and_wait`, `CanonicalLiveServer`, `LiveStateClient`, `save_snapshot`, and `ensure_repository_identity` at revision 692 with `workspace_sync=verified`. Local source confirmed the two explicit FULL flags; `save_engine_state` persistence; subsequent import of `contextor.core.live_state.connect`; `publish_committed_and_wait` with repo_id, state_id, revision and origin; its `submit_committed_publish`, `mutation_status` and `authority_status` calls; required service_instance_id and process_start_identity; server's committed_snapshot_reader, repository_identity_reader and authority_identity; repository identity and central registry directory; P1D2J helper exports; P1D2K installed-generation verification. New test path absent. PREFLIGHT_MISMATCH=NONE.

## NATIVE_CODEX_LITERAL_EDITS

DIRECT_EVIDENCE: Created only the architect-supplied test through native Codex `apply_patch`. The test source matched the attachment exactly after newline normalization.

## FILES_CHANGED

- `tests/test_original_worker_official_full_live_publication.py`

`walkthrough.md` is this report. No production or existing test file changed.

## ACTUAL_NEW_TEST_CONTENT

Full actual new-file diff:

```diff
diff --git a/tests/test_original_worker_official_full_live_publication.py b/tests/test_original_worker_official_full_live_publication.py
new file mode 100644
index 0000000..6869657
--- /dev/null
+++ b/tests/test_original_worker_official_full_live_publication.py
@@ -0,0 +1,595 @@
+"""P1D2L: actual FULL committed-publication queue over isolated IPC."""
+
+from __future__ import annotations
+
+from contextlib import contextmanager
+from dataclasses import replace
+from pathlib import Path
+from threading import Thread
+from uuid import uuid4
+
+import pytest
+
+import contextor.core.live_state as live_state
+import contextor.core.cycle_semantics.original_worker_preparation as preparation_module
+
+from contextor.core.live_state.ipc import (
+    CanonicalLiveServer,
+    LiveStateClient,
+)
+from contextor.core.live_state.publication_receipt import (
+    committed_publication_key,
+    publish_committed_and_wait,
+)
+from contextor.core.live_state.store import (
+    locked_committed_snapshot,
+    read_metadata,
+)
+from contextor.core.paths import repo_cache_dir
+from contextor.core.repository_identity import (
+    ensure_repository_identity,
+)
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
+def _official_live(
+    root,
+    monkeypatch,
+    *,
+    complete_authority=True,
+):
+    root = Path(root).resolve()
+
+    identity, _registry_directory = (
+        ensure_repository_identity(root)
+    )
+
+    service_id = "p1d2l-service-" + uuid4().hex
+
+    authority = {
+        "repo_id": identity.repo_id,
+        "root_path": identity.root_path,
+        "service_instance_id": service_id,
+    }
+
+    if complete_authority:
+        authority["process_start_identity"] = (
+            "p1d2l-process-" + uuid4().hex
+        )
+
+    cache = repo_cache_dir(root)
+
+    server = CanonicalLiveServer(
+        committed_snapshot_reader=(
+            lambda: locked_committed_snapshot(
+                cache,
+                expected_repo_id=identity.repo_id,
+                expected_root_path=identity.root_path,
+            )
+        ),
+        repository_identity_reader=lambda: identity,
+        authority_identity=authority,
+    )
+
+    assert server.endpoint.host == "127.0.0.1"
+    assert server.endpoint.service_instance_id == service_id
+
+    worker = Thread(
+        target=server.serve_forever,
+        name="p1d2l-isolated-live",
+        daemon=True,
+    )
+
+    worker.start()
+
+    client = LiveStateClient(server.endpoint)
+    connect_calls = []
+
+    def isolated_connect(path):
+        selected = Path(path).resolve()
+        assert selected == root
+
+        connect_calls.append(selected)
+
+        return client
+
+    monkeypatch.setattr(
+        live_state,
+        "connect",
+        isolated_connect,
+    )
+
+    try:
+        assert client.ping()["status"] == "ok"
+
+        yield (
+            client,
+            server,
+            identity,
+            connect_calls,
+        )
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
+def _require_success(result, metadata, server):
+    assert result.live_publish_status == "success"
+    assert result.live_publish_revision == (
+        metadata.revision
+    )
+    assert result.live_publish_expected_revision == (
+        metadata.revision
+    )
+    assert result.live_publish_expected_state_id == (
+        metadata.state_id
+    )
+    assert result.live_publish_service_instance_id == (
+        server.endpoint.service_instance_id
+    )
+    assert result.live_publish_process_start_identity == (
+        server.endpoint.process_start_identity
+    )
+
+    assert isinstance(
+        result.live_publish_job_id,
+        str,
+    )
+    assert result.live_publish_job_id
+
+    assert result.live_publish_idempotency_key == (
+        committed_publication_key(
+            metadata.repo_id,
+            metadata.state_id,
+            metadata.revision,
+        )
+    )
+
+
+def test_p1d2l_t01_real_full_automatic_queue_publication(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    with _official_live(
+        root,
+        monkeypatch,
+    ) as (client, server, identity, calls):
+
+        result = _full(
+            root,
+            preview=True,
+            publish=True,
+        )
+
+        state, metadata = _committed(root)
+        receipt = _receipt(state, metadata)
+
+        assert metadata.repo_id == identity.repo_id
+
+        _require_success(result, metadata, server)
+
+        assert calls == [root.resolve()]
+
+        job = client.mutation_status(
+            result.live_publish_job_id
+        )
+
+        assert job["status"] == "ok"
+        assert job["state"] == "completed"
+        assert job["requested_state_id"] == (
+            metadata.state_id
+        )
+        assert job["requested_revision"] == (
+            metadata.revision
+        )
+        assert job["response"]["status"] == "ok"
+        assert job["response"]["revision"] == (
+            metadata.revision
+        )
+
+        installed = client.snapshot()
+
+        assert installed["status"] == "ok"
+        assert installed["revision"] == (
+            metadata.revision
+        )
+        assert _receipt(
+            installed["state"],
+            metadata,
+        ) == receipt
+
+        verified = _verify(
+            client,
+            state,
+            metadata,
+        )
+
+        assert verified["status"] == "ok"
+        assert verified["binding_state"] == (
+            "INSTALLED_PREPARED_CLAIMS_MATCH_EXPECTED_GENERATION"
+        )
+        assert verified["model_claims_sha256"] == (
+            receipt.model_claims_sha256
+        )
+
+        assert verified["service_instance_id"] == (
+            server.endpoint.service_instance_id
+        )
+
+
+def test_p1d2l_t02_preview_only_automatic_publish_no_receipt(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    with _official_live(
+        root,
+        monkeypatch,
+    ) as (client, server, _identity, calls):
+
+        result = _full(
+            root,
+            preview=True,
+            publish=False,
+        )
+
+        assert (
+            result.cycle_source_preparation_preview.status
+            == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+        )
+
+        state, metadata = _committed(root)
+
+        _require_success(result, metadata, server)
+
+        assert calls == [root.resolve()]
+        assert state.cycle_source_publication is None
+
+        installed = client.snapshot()
+
+        assert installed["status"] == "ok"
+        assert installed["revision"] == (
+            metadata.revision
+        )
+        assert (
+            installed["state"].cycle_source_publication
+            is None
+        )
+
+        verified = _verify(
+            client,
+            state,
+            metadata,
+        )
+
+        assert verified["status"] == "unavailable"
+        assert verified["reason"] == (
+            "CO_PUBLISHED_RECEIPT_UNAVAILABLE"
+        )
+
+
+def test_p1d2l_t03_rejected_manifest_no_next_job(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    with _official_live(
+        root,
+        monkeypatch,
+    ) as (client, server, _identity, calls):
+
+        initial_result = _full(
+            root,
+            preview=True,
+            publish=True,
+        )
+
+        initial_state, initial_metadata = _committed(
+            root
+        )
+        old_receipt = _receipt(
+            initial_state,
+            initial_metadata,
+        )
+
+        _require_success(
+            initial_result,
+            initial_metadata,
+            server,
+        )
+
+        initial_job_id = (
+            initial_result.live_publish_job_id
+        )
+
+        original = (
+            preparation_module
+            .prepare_original_worker_cycle_manifest
+        )
+
+        def forged(*args, **kwargs):
+            prepared = original(*args, **kwargs)
+
+            if prepared.manifest is None:
+                return prepared
+
+            return replace(
+                prepared,
+                manifest=replace(
+                    prepared.manifest,
+                    source_manifest_sha256="f" * 64,
+                ),
+            )
+
+        monkeypatch.setattr(
+            preparation_module,
+            "prepare_original_worker_cycle_manifest",
+            forged,
+        )
+
+        failed = _full(
+            root,
+            preview=True,
+            publish=True,
+        )
+
+        assert failed.live_publish_status == (
+            "not_attempted"
+        )
+
+        assert read_metadata(
+            repo_cache_dir(root)
+        ) == initial_metadata
+
+        installed = client.snapshot()
+
+        assert installed["status"] == "ok"
+        assert installed["revision"] == (
+            initial_metadata.revision
+        )
+
+        assert _receipt(
+            installed["state"],
+            initial_metadata,
+        ) == old_receipt
+
+        job = client.mutation_status(initial_job_id)
+
+        assert job["status"] == "ok"
+        assert job["state"] == "completed"
+
+        events = client.get_events(
+            after_revision=0,
+            limit=None,
+        )
+
+        assert events["status"] == "ok"
+        assert [
+            event["revision"]
+            for event in events["events"]
+            if event["operation"] == "publish"
+        ] == [initial_metadata.revision]
+
+        assert calls == [
+            root.resolve(),
+        ]
+
+
+def test_p1d2l_t04_default_full_replaces_receipt(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    with _official_live(
+        root,
+        monkeypatch,
+    ) as (client, server, _identity, calls):
+
+        first_result = _full(
+            root,
+            preview=True,
+            publish=True,
+        )
+
+        first_state, first_metadata = _committed(
+            root
+        )
+
+        _receipt(first_state, first_metadata)
+        _require_success(
+            first_result,
+            first_metadata,
+            server,
+        )
+
+        second_result = _full(root)
+
+        second_state, second_metadata = _committed(
+            root
+        )
+
+        assert second_metadata.revision == (
+            first_metadata.revision + 1
+        )
+        assert second_state.cycle_source_publication is None
+
+        _require_success(
+            second_result,
+            second_metadata,
+            server,
+        )
+
+        previous = _verify(
+            client,
+            first_state,
+            first_metadata,
+        )
+
+        assert previous["status"] == "unavailable"
+        assert previous["reason"] == (
+            "INSTALLED_GENERATION_MISMATCH"
+        )
+
+        current = _verify(
+            client,
+            second_state,
+            second_metadata,
+        )
+
+        assert current["status"] == "unavailable"
+        assert current["reason"] == (
+            "CO_PUBLISHED_RECEIPT_UNAVAILABLE"
+        )
+
+        assert calls == [
+            root.resolve(),
+            root.resolve(),
+        ]
+
+
+def test_p1d2l_t05_incomplete_authority_not_verified(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    with _official_live(
+        root,
+        monkeypatch,
+        complete_authority=False,
+    ) as (client, server, _identity, calls):
+
+        assert (
+            server.endpoint.process_start_identity
+            is None
+        )
+
+        result = _full(
+            root,
+            preview=True,
+            publish=True,
+        )
+
+        state, metadata = _committed(root)
+
+        _receipt(state, metadata)
+
+        assert result.live_publish_status == (
+            "unverified_authority_changed"
+        )
+        assert result.live_publish_revision is None
+        assert result.live_publish_job_id is None
+
+        assert calls == [root.resolve()]
+
+        active = client.snapshot()
+
+        assert active["status"] == "ok"
+        assert active["revision"] == 0
+        assert active["state"] is None
+
+        assert state.cycle_source_publication is not None
+
+
+def test_p1d2l_t06_repeated_committed_job_is_idempotent(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _flat_repo(tmp_path)
+
+    with _official_live(
+        root,
+        monkeypatch,
+    ) as (client, server, _identity, calls):
+
+        result = _full(
+            root,
+            preview=True,
+            publish=True,
+        )
+
+        state, metadata = _committed(root)
+
+        _receipt(state, metadata)
+        _require_success(result, metadata, server)
+
+        before = client.get_events(
+            after_revision=0,
+            limit=None,
+        )
+
+        assert before["status"] == "ok"
+
+        repeated = publish_committed_and_wait(
+            client,
+            repo_id=metadata.repo_id,
+            state_id=metadata.state_id,
+            revision=metadata.revision,
+            origin="desktop_analysis",
+        )
+
+        assert repeated["live_publish_status"] == (
+            "success"
+        )
+        assert repeated["live_publish_revision"] == (
+            metadata.revision
+        )
+        assert repeated["live_publish_job_id"] == (
+            result.live_publish_job_id
+        )
+        assert (
+            repeated["live_publish_idempotency_key"]
+            == result.live_publish_idempotency_key
+        )
+
+        after = client.get_events(
+            after_revision=0,
+            limit=None,
+        )
+
+        assert after["status"] == "ok"
+        assert after["events"] == before["events"]
+
+        current = _verify(
+            client,
+            state,
+            metadata,
+        )
+
+        assert current["status"] == "ok"
+        assert calls == [root.resolve()]
```

## PY_COMPILE_RESULT

DIRECT_EVIDENCE: `python -m py_compile tests/test_original_worker_official_full_live_publication.py` exited 0.

## P1D2L_TEST_RESULTS

DIRECT_EVIDENCE: Six new tests passed in 12.16s.

## FOCUSED_REGRESSION_RESULTS

DIRECT_EVIDENCE: Exact 18-file focused regression command from the task: 255 passed in 70.74s.

## ACTUAL_FULL_PUBLISH_CALL_PATH

CODE_PATH_PROVED: `analyze_project` saves through `save_engine_state`, then imports `connect` and invokes `publish_committed_and_wait` on successful persistence. T01 exercised that path against an isolated localhost server and temporary repository.

## CANONICAL_QUEUE_ADMISSION

CONTRACT_PROVED: T01 observed a completed mutation job with requested state_id/revision, success response and matching idempotency key. The isolated server used its real committed publication queue and store reader.

## COMMITTED_GENERATION_INSTALLATION

CONTRACT_PROVED: T01 read the installed snapshot, verified the same-generation receipt, and received `INSTALLED_PREPARED_CLAIMS_MATCH_EXPECTED_GENERATION` from the LIVE owner.

## PREVIEW_ONLY_PUBLICATION_BEHAVIOR

CONTRACT_PROVED: T02 observed successful ordinary FULL publication through the queue with no prepared cycle receipt; installed-generation verification returned `CO_PUBLISHED_RECEIPT_UNAVAILABLE`.

## FAILED_MANIFEST_NO_NEXT_JOB

CONTRACT_PROVED: T03's forged manifest failed the next store commit, left metadata and installed generation unchanged, kept the first job completed, and showed only one publish event and one `connect` call.

## LATER_DEFAULT_FULL_GENERATION

CONTRACT_PROVED: T04 installed a second default FULL generation without a receipt. Old generation verification returned `INSTALLED_GENERATION_MISMATCH`; current generation returned `CO_PUBLISHED_RECEIPT_UNAVAILABLE`.

## INCOMPLETE_SERVICE_IDENTITY

CONTRACT_PROVED: T05 omitted process_start_identity from the isolated endpoint. FULL committed its durable receipt, but `publish_committed_and_wait` returned `unverified_authority_changed` with no job and no installed state.

## IDEMPOTENT_PUBLICATION_JOB

CONTRACT_PROVED: T06 repeated `publish_committed_and_wait` for the same committed generation. It returned the existing job/idempotency key, produced no additional events and left installed verification successful.

## CANONICAL_WATCHER_OBSERVATIONS

DIRECT_EVIDENCE: `get_live_events(after_revision=692)` returned one continuous `desktop_watcher` update for the new test at revision 693, with `resync_required=false`. Contextor source read of `ContextorFacade.analyze_project` returned `workspace_sync=verified` at revision 693; the cycle_semantics family was stale.

## ACTIVE_RUNTIME_ADOPTION_LIMITS

UNKNOWN: Whether the active application process adopted source implementations. Watcher indexing and isolated localhost tests do not prove active application adoption. No existing LIVE endpoint was contacted, restarted, reloaded or mutated.

## FINAL_VERDICT

CONTRACT_PROVED: P1D2L's six isolated official-publication tests and specified regression set passed. DIRECT_EVIDENCE: No production changes or active-repository FULL. UNKNOWN: cross-file source atomicity, worker byte provenance authentication, Python import execution safety and receipt authority beyond committed prepared claims. STOP after P1D2L; await architect assessment.

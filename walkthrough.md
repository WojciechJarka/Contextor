# TASK
P1D1E_ACTIVE_LIVE_INSTALLED_GENERATION_GATE — exact auditor-supplied patch in three approved files.

# HEAD_BEFORE
e495eb02551276ee57b0c1efba4b040e67d65ecc; clean working tree; both approved new files absent; _dispatch lock/canonical_query and LiveStateClient.authority_status anchors matched.

# HEAD_AFTER
e495eb02551276ee57b0c1efba4b040e67d65ecc; no commit.

# FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\core\cycle_semantics\live_installed_claims.py
- C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
- C:\Temp\Contextor_Repo\tests\live_state\test_installed_cycle_generation_gate.py

# ARCHITECTURAL_DEPENDENCIES
CONTRACT_PROVED (Contextor MCP, pre-edit revision 665): CanonicalLiveServer._dispatch has its read-only branch under with self._lock immediately before canonical_query; publish and committed publish install state under the same lock; update_file uses it at installation. CanonicalCycleManifestReceipt and verify_co_published_cycle_manifest own prepared claim checking. P1D1C and P1D1D remain separate comparison boundaries. _dispatch blast-radius static consumer count was zero, which is not proof of no dynamic/protocol callers. Source modules were workspace_sync=verified before edit.

# T01_T16_RESULTS
DIRECT_EVIDENCE: .\.venv\Scripts\python.exe -m pytest -q tests/live_state/test_installed_cycle_generation_gate.py => 16 passed in 6.39s.

# FOCUSED_NON_REGRESSION
DIRECT_EVIDENCE: .\.venv\Scripts\python.exe -m pytest -q tests/live_state/test_ipc_canonical_query.py tests/live_state/test_runtime_canonical_query.py tests/test_cycle_semantics_publication_binding.py tests/test_cycle_semantics_publication_live_integration.py tests/test_cycle_semantics_worker_claim_binding.py tests/test_cycle_semantics_registered_store_binding.py => 67 passed in 12.42s. Full suite not run; the user-provided 4298-PASS baseline was not rerun.

# OWNER_LOCK_SERIALIZATION
CODE_PATH_PROVED: verify_installed_cycle_generation dispatch branch is inside CanonicalLiveServer._dispatch with self._lock, immediately before canonical_query. T14 holds receipt verification with threading.Events while a publish attempts the mutation; mutation completes only after check releases the lock, then a later check rejects superseded revision 1. This is an instant-scoped linearization, not a lease.

# INSTALLED_GENERATION_IDENTITY
CODE_PATH_PROVED: exact expected revision/state_id are validated against self._revision and installed state revision/state_id. T01 positive, T02/T03 stale revision or wrong state ID, T12 invalid generation and T14 later supersession passed.

# REPOSITORY_AND_SERVICE_INSTANCE_IDENTITY
CODE_PATH_PROVED: owner authority repo_id/root_path/service_instance_id are checked against expected values. T04–T06 reject foreign identity; T16 rejects unavailable authority. T15 verifies client uses endpoint.service_instance_id, not worker-supplied identity.

# RECEIPT_AND_GRAPH_VERIFICATION
CODE_PATH_PROVED: existing verify_co_published_cycle_manifest checks receipt against lock-scoped installed state and owner identity; manifest graph_sha256 must equal expected digest. T01 positive, T07 wrong graph, T08 absent receipt passed. No receipt writer added.

# STALE_AND_MISSING_EVIDENCE
DIRECT_EVIDENCE: T09 stale cycle semantics, T10 resync_required, T13 pending recovery all return unavailable. The currently running repository's cycle_semantics family is stale at revision 668, so this operation is not certified positive for that runtime.

# NO_SOURCE_TRANSPORT
CODE_PATH_PROVED: exact request key set admits only expected generation and identity scalars. T11 rejects a source_capture_bytes payload. No state, AST or source-byte object is returned by the new operation. No worker, snapshot hydration, filesystem read or publication occurs in this branch.

# CONCURRENCY_LINEARIZATION_EVIDENCE
DIRECT_EVIDENCE: T14 passed with two threads and Events: check returned revision 1 while holding owner lock, publish then returned revision 2, and a subsequent check returned INSTALLED_GENERATION_MISMATCH. Positive response does not guarantee currentness after reply.

# CLIENT_ENDPOINT_BINDING
DIRECT_EVIDENCE: T15 recorded the client request and confirmed expected_service_instance_id equals server.endpoint.service_instance_id.

# AUTHORITY_LIMITATIONS
The operation verifies one installed generation only at the lock-scoped instant. It does not certify later currentness, capture origin, original FULL bytes, atomic source capture, runtime import safety or SAFE classification. Already-running LIVE loaded-code adoption remains unverified.

# PERFORMANCE_LIMITATIONS
Receipt verification may traverse graph and SCC declarations while self._lock is held. The operation is explicit/on-demand; no hot-path MCP, watcher polling, caching, timeout or executor policy was added.

# LIVE_REVISION_BEFORE_AFTER
665 → 668. Activity epoch 714b1f0fcdf34953b33ba77281b7e94b; Contextor get_live_events(after_revision=665): continuity=continuous, resync_required=false, total=3, truncated=false.

# WATCHER_EVENTS
DIRECT_EVIDENCE: desktop_watcher UPDATED events: revision 666 live_installed_claims.py, 667 ipc.py, 668 test_installed_cycle_generation_gate.py. Revision 667 also reported one ADDED structural cycle diagnostic with nodes:
contextor.core.analysis.state_manager → contextor.core.live_state.__init__ → contextor.core.live_state.hydration → contextor.core.live_state.runtime → contextor.core.live_state.ipc → contextor.core.cycle_semantics.live_installed_claims → contextor.core.analysis.state_manager.
The current project architecture reports fresh structural cycle count 17 versus 16 before edit. This is a material architecture effect of the exact approved patch. No further code change was made because the contract forbids redesign or unapproved fixes. No manual update_file, FULL analysis or restart.

# WORKSPACE_SYNC
Contextor get_module_context for all three task files after revision 668: canonical_state=fresh, workspace_sync=verified, advisory_warning=null. Cycle_semantics family remains stale.

# COLLISION_DIAGNOSTICS
Current canonical name collision count remains 2, both existing profiling-scope NAME_COLLISION warnings (run_scope and PRESETS). No new name collision. A new structural cycle is separately reported above; absence of a collision warning does not clear that diagnostic.

# RUNTIME_ADOPTION_LIMITATION
Fresh Python test processes executed the patch. Watcher indexing and workspace_sync do not prove the active LIVE service loaded the new IPC operation. An already-running service may still respond unknown_operation until a user-controlled reload. No runtime-loaded-code certification performed.

# RESTART_REQUIREMENTS
Production ipc.py changed, so a user-controlled LIVE service reload/restart is required before the active service can use the new operation. No process was restarted by the agent. MCP/Desktop reload depends on their actual import ownership and remains unverified.

# WHITESPACE_CHECK
py_compile passed for all three files; git diff --check and new-file git diff --no-index --check passed. Both new files end in LF with no trailing-whitespace lines. Git emitted only future LF→CRLF working-copy warnings.

# FULL_DIFFS

## contextor/core/cycle_semantics/live_installed_claims.py

```diff
diff --git a/contextor/core/cycle_semantics/live_installed_claims.py b/contextor/core/cycle_semantics/live_installed_claims.py
new file mode 100644
index 0000000..814c8cc
--- /dev/null
+++ b/contextor/core/cycle_semantics/live_installed_claims.py
@@ -0,0 +1,195 @@
+"""Lock-scoped comparison of installed LIVE cycle claims.
+
+The caller must invoke this helper while holding the canonical
+LIVE owner's state lock. This helper does not acquire that lock.
+
+It verifies the current installed generation and the existing
+co-published prepared-manifest receipt.
+
+No source provenance, durable-store read, or runtime import
+safety is certified by this operation.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Mapping
+from typing import Any
+
+from contextor.core.analysis.state_manager import (
+    RepositoryAnalysisState,
+)
+
+from .publication_binding import (
+    CanonicalCycleManifestReceipt,
+    verify_co_published_cycle_manifest,
+)
+
+
+_AUTHORITY = (
+    "LIVE_OWNER_LOCK_SCOPED_INSTALLED_PREPARED_CLAIMS"
+    "_NOT_STABLE_AFTER_REPLY"
+    "_NOT_WORKER_SOURCE_CERTIFIED"
+    "_NOT_RUNTIME_SAFETY"
+)
+
+_MATCH = "INSTALLED_PREPARED_CLAIMS_MATCH_EXPECTED_GENERATION"
+
+
+def assess_live_installed_prepared_claims(
+    state: Any,
+    *,
+    canonical_revision: int,
+    authority_identity: Mapping[str, Any],
+    activity_epoch: str,
+    expected_revision: Any,
+    expected_state_id: Any,
+    expected_repo_id: Any,
+    expected_root_path: Any,
+    expected_graph_sha256: Any,
+    expected_service_instance_id: Any,
+) -> dict[str, Any]:
+    """Compare expected identity with the installed LIVE state.
+
+    IMPORTANT: The CanonicalLiveServer caller owns self._lock
+    for the entire evaluation and response construction.
+    """
+
+    def unavailable(reason: str) -> dict[str, Any]:
+        return {
+            "status": "unavailable",
+            "reason": reason,
+            "revision": canonical_revision,
+            "activity_epoch": activity_epoch,
+            "authority": _AUTHORITY,
+        }
+
+    expected_strings = (
+        expected_state_id,
+        expected_repo_id,
+        expected_root_path,
+        expected_service_instance_id,
+    )
+
+    if (
+        type(expected_revision) is not int
+        or expected_revision < 1
+        or any(
+            type(value) is not str
+            or not value
+            or len(value) > 4096
+            for value in expected_strings
+        )
+        or type(expected_graph_sha256) is not str
+        or len(expected_graph_sha256) != 64
+        or any(
+            character not in "0123456789abcdef"
+            for character in expected_graph_sha256
+        )
+    ):
+        return unavailable("INVALID_EXPECTED_GENERATION")
+
+    if (
+        not isinstance(authority_identity, Mapping)
+        or type(activity_epoch) is not str
+        or not activity_epoch
+    ):
+        return unavailable("LIVE_AUTHORITY_UNAVAILABLE")
+
+    owner_repo = authority_identity.get("repo_id")
+    owner_root = authority_identity.get("root_path")
+    owner_instance = authority_identity.get(
+        "service_instance_id"
+    )
+
+    if any(
+        type(value) is not str or not value
+        for value in (
+            owner_repo,
+            owner_root,
+            owner_instance,
+        )
+    ):
+        return unavailable("LIVE_AUTHORITY_UNAVAILABLE")
+
+    if owner_instance != expected_service_instance_id:
+        return unavailable("LIVE_INSTANCE_MISMATCH")
+
+    if (
+        owner_repo != expected_repo_id
+        or owner_root != expected_root_path
+    ):
+        return unavailable("LIVE_REPOSITORY_MISMATCH")
+
+    if type(state) is not RepositoryAnalysisState:
+        return unavailable("INSTALLED_STATE_UNAVAILABLE")
+
+    if (
+        type(canonical_revision) is not int
+        or canonical_revision != expected_revision
+        or type(getattr(state, "revision", None)) is not int
+        or state.revision != canonical_revision
+        or getattr(state, "state_id", None)
+        != expected_state_id
+    ):
+        return unavailable("INSTALLED_GENERATION_MISMATCH")
+
+    if getattr(state, "resync_required", False) is not False:
+        return unavailable("CANONICAL_RESYNC_REQUIRED")
+
+    if (
+        getattr(state, "cycle_semantics_state", None)
+        != "fresh"
+        or getattr(state, "cycles_state", None)
+        != "fresh"
+    ):
+        return unavailable("REQUIRED_CYCLE_FAMILY_NOT_FRESH")
+
+    receipt = getattr(
+        state,
+        "cycle_source_publication",
+        None,
+    )
+
+    if type(receipt) is not CanonicalCycleManifestReceipt:
+        return unavailable("CO_PUBLISHED_RECEIPT_UNAVAILABLE")
+
+    try:
+        valid = verify_co_published_cycle_manifest(
+            state,
+            revision=canonical_revision,
+            state_id=expected_state_id,
+            repo_id=owner_repo,
+            root_path=owner_root,
+        )
+    except (
+        ValueError,
+        TypeError,
+        AttributeError,
+        KeyError,
+    ):
+        valid = False
+
+    if not valid:
+        return unavailable("CO_PUBLISHED_RECEIPT_INVALID")
+
+    manifest = receipt.prepared_manifest
+
+    if manifest.graph_sha256 != expected_graph_sha256:
+        return unavailable("INSTALLED_GRAPH_IDENTITY_MISMATCH")
+
+    return {
+        "status": "ok",
+        "binding_state": _MATCH,
+        "revision": canonical_revision,
+        "state_id": expected_state_id,
+        "repo_id": owner_repo,
+        "root_path": owner_root,
+        "service_instance_id": owner_instance,
+        "activity_epoch": activity_epoch,
+        "graph_sha256": manifest.graph_sha256,
+        "source_manifest_sha256": (
+            manifest.source_manifest_sha256
+        ),
+        "model_claims_sha256": receipt.model_claims_sha256,
+        "authority": _AUTHORITY,
+    }
```

## contextor/core/live_state/ipc.py

```diff
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index e8aa6c6..257163f 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -2336,6 +2336,68 @@ class CanonicalLiveServer:
             return self._execute_publish(request)
 
         with self._lock:
+            if operation == "verify_installed_cycle_generation":
+                required_fields = {
+                    "operation",
+                    "expected_revision",
+                    "expected_state_id",
+                    "expected_repo_id",
+                    "expected_root_path",
+                    "expected_graph_sha256",
+                    "expected_service_instance_id",
+                }
+
+                # A narrow identity-only protocol.
+                # Do not accept state objects, source bytes,
+                # captures or unrelated caller payloads.
+                if set(request) != required_fields:
+                    return {
+                        "status": "unavailable",
+                        "reason": "INVALID_GENERATION_CHECK_PAYLOAD",
+                        "revision": self._revision,
+                    }
+
+                if (
+                    self._stop.is_set()
+                    or self._pending_recovery_certificate
+                    is not None
+                    or self._recovery_release_degraded
+                ):
+                    return {
+                        "status": "unavailable",
+                        "reason": "LIVE_OWNER_NOT_READY",
+                        "revision": self._revision,
+                    }
+
+                from contextor.core.cycle_semantics.live_installed_claims import (
+                    assess_live_installed_prepared_claims,
+                )
+
+                return assess_live_installed_prepared_claims(
+                    self._state,
+                    canonical_revision=self._revision,
+                    authority_identity=self._authority_identity,
+                    activity_epoch=self._activity_epoch,
+                    expected_revision=request.get(
+                        "expected_revision"
+                    ),
+                    expected_state_id=request.get(
+                        "expected_state_id"
+                    ),
+                    expected_repo_id=request.get(
+                        "expected_repo_id"
+                    ),
+                    expected_root_path=request.get(
+                        "expected_root_path"
+                    ),
+                    expected_graph_sha256=request.get(
+                        "expected_graph_sha256"
+                    ),
+                    expected_service_instance_id=request.get(
+                        "expected_service_instance_id"
+                    ),
+                )
+
             if operation == "canonical_query":
                 if self._state is None:
                     return {
@@ -2664,6 +2726,32 @@ class LiveStateClient:
     def authority_status(self) -> dict[str, Any]:
         return self.request("authority_status")
 
+    def verify_installed_cycle_generation(
+        self,
+        *,
+        expected_revision: int,
+        expected_state_id: str,
+        expected_repo_id: str,
+        expected_root_path: str,
+        expected_graph_sha256: str,
+    ) -> dict[str, Any]:
+        """Verify installed claims in one LIVE-owner operation.
+
+        The instance ID comes from this client's endpoint,
+        not from the supplied worker capture.
+        """
+        return self.request(
+            "verify_installed_cycle_generation",
+            expected_revision=expected_revision,
+            expected_state_id=expected_state_id,
+            expected_repo_id=expected_repo_id,
+            expected_root_path=expected_root_path,
+            expected_graph_sha256=expected_graph_sha256,
+            expected_service_instance_id=(
+                self.endpoint.service_instance_id
+            ),
+        )
+
     def desktop_claim_status(self) -> dict[str, Any]:
         return self.request("desktop_claim_status")
 
```

## tests/live_state/test_installed_cycle_generation_gate.py

```diff
diff --git a/tests/live_state/test_installed_cycle_generation_gate.py b/tests/live_state/test_installed_cycle_generation_gate.py
new file mode 100644
index 0000000..c9d78f7
--- /dev/null
+++ b/tests/live_state/test_installed_cycle_generation_gate.py
@@ -0,0 +1,344 @@
+"""P1D1E: active LIVE-owner installed-generation gates."""
+
+from __future__ import annotations
+
+import threading
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.cycle_semantics import (
+    live_installed_claims,
+)
+from contextor.core.live_state.ipc import (
+    CanonicalLiveServer,
+    LiveStateClient,
+)
+from contextor.core.live_state.store import (
+    load_snapshot,
+    save_snapshot,
+)
+from tests.test_cycle_semantics_publication_binding import (
+    _case,
+)
+
+
+@pytest.fixture
+def owner(tmp_path):
+    state, prepared = _case()
+    root_path = str(tmp_path.resolve())
+    repo_id = "ctx_p1d1e_test"
+    instance = "p1d1e-service-instance"
+
+    save_snapshot(
+        state,
+        tmp_path,
+        "p1d1e-state",
+        repo_id=repo_id,
+        root_path=root_path,
+        exact_revision=1,
+        file_state_payload={
+            "_meta": {
+                "state_id": "p1d1e-state",
+                "revision": 1,
+            },
+            "files": {},
+        },
+        prepared_cycle_manifest=prepared,
+    )
+
+    loaded, metadata = load_snapshot(
+        tmp_path,
+        "p1d1e-state",
+        expected_repo_id=repo_id,
+        expected_root_path=root_path,
+    )
+
+    server = CanonicalLiveServer(
+        loaded,
+        revision=1,
+        authority_identity={
+            "repo_id": repo_id,
+            "root_path": root_path,
+            "service_instance_id": instance,
+        },
+    )
+
+    request = {
+        "operation": "verify_installed_cycle_generation",
+        "expected_revision": metadata.revision,
+        "expected_state_id": metadata.state_id,
+        "expected_repo_id": repo_id,
+        "expected_root_path": root_path,
+        "expected_graph_sha256": prepared.graph_sha256,
+        "expected_service_instance_id": instance,
+    }
+
+    try:
+        yield server, request
+    finally:
+        server.close()
+
+
+def _check(server, request, **changes):
+    return server._dispatch({**request, **changes})
+
+
+def test_p1d1e_t01_installed_committed_claim_matches(owner):
+    server, request = owner
+    answer = _check(server, request)
+
+    assert answer["status"] == "ok"
+    assert answer["binding_state"] == (
+        "INSTALLED_PREPARED_CLAIMS_MATCH_EXPECTED_GENERATION"
+    )
+    assert answer["revision"] == 1
+    assert answer["state_id"] == "p1d1e-state"
+    assert answer["repo_id"] == "ctx_p1d1e_test"
+    assert answer["activity_epoch"] == server.activity_epoch
+    assert len(answer["source_manifest_sha256"]) == 64
+    assert len(answer["model_claims_sha256"]) == 64
+    assert "NOT_STABLE_AFTER_REPLY" in answer["authority"]
+    assert "NOT_RUNTIME_SAFETY" in answer["authority"]
+    assert "state" not in answer
+
+
+def test_p1d1e_t02_stale_expected_revision(owner):
+    server, request = owner
+    answer = _check(
+        server, request, expected_revision=2
+    )
+    assert answer["status"] == "unavailable"
+    assert answer["reason"] == (
+        "INSTALLED_GENERATION_MISMATCH"
+    )
+
+
+def test_p1d1e_t03_wrong_state_id(owner):
+    server, request = owner
+    answer = _check(
+        server, request, expected_state_id="foreign-state"
+    )
+    assert answer["reason"] == (
+        "INSTALLED_GENERATION_MISMATCH"
+    )
+
+
+def test_p1d1e_t04_foreign_repo(owner):
+    server, request = owner
+    answer = _check(
+        server, request, expected_repo_id="ctx_foreign"
+    )
+    assert answer["reason"] == "LIVE_REPOSITORY_MISMATCH"
+
+
+def test_p1d1e_t05_foreign_root(owner):
+    server, request = owner
+    answer = _check(
+        server, request, expected_root_path="foreign-root"
+    )
+    assert answer["reason"] == "LIVE_REPOSITORY_MISMATCH"
+
+
+def test_p1d1e_t06_foreign_service_instance(owner):
+    server, request = owner
+    answer = _check(
+        server,
+        request,
+        expected_service_instance_id="stale-instance",
+    )
+    assert answer["reason"] == "LIVE_INSTANCE_MISMATCH"
+
+
+def test_p1d1e_t07_graph_claim_mismatch(owner):
+    server, request = owner
+    answer = _check(
+        server,
+        request,
+        expected_graph_sha256="f" * 64,
+    )
+    assert answer["reason"] == (
+        "INSTALLED_GRAPH_IDENTITY_MISMATCH"
+    )
+
+
+def test_p1d1e_t08_missing_receipt(owner):
+    server, request = owner
+    server._state.cycle_source_publication = None
+    answer = _check(server, request)
+    assert answer["reason"] == (
+        "CO_PUBLISHED_RECEIPT_UNAVAILABLE"
+    )
+
+
+def test_p1d1e_t09_stale_cycle_family(owner):
+    server, request = owner
+    server._state.cycle_semantics_state = "stale"
+    answer = _check(server, request)
+    assert answer["reason"] == (
+        "REQUIRED_CYCLE_FAMILY_NOT_FRESH"
+    )
+
+
+def test_p1d1e_t10_resync_required(owner):
+    server, request = owner
+    server._state.resync_required = True
+    answer = _check(server, request)
+    assert answer["reason"] == "CANONICAL_RESYNC_REQUIRED"
+
+
+def test_p1d1e_t11_unrelated_payload_rejected(owner):
+    server, request = owner
+    answer = _check(
+        server,
+        request,
+        source_capture_bytes=b"not-permitted",
+    )
+    assert answer["status"] == "unavailable"
+    assert answer["reason"] == (
+        "INVALID_GENERATION_CHECK_PAYLOAD"
+    )
+
+
+def test_p1d1e_t12_invalid_expected_generation(owner):
+    server, request = owner
+
+    for changed in (
+        {"expected_revision": True},
+        {"expected_revision": 0},
+        {"expected_state_id": ""},
+        {"expected_graph_sha256": "bad"},
+    ):
+        answer = _check(server, request, **changed)
+        assert answer["status"] == "unavailable"
+        assert answer["reason"] == (
+            "INVALID_EXPECTED_GENERATION"
+        )
+
+
+def test_p1d1e_t13_recovery_pending_rejected(owner):
+    server, request = owner
+    server._pending_recovery_certificate = {
+        "certificate_id": "test-only",
+    }
+    try:
+        answer = _check(server, request)
+        assert answer["reason"] == "LIVE_OWNER_NOT_READY"
+    finally:
+        server._pending_recovery_certificate = None
+
+
+def test_p1d1e_t14_generation_change_is_serialized(
+    owner, monkeypatch,
+):
+    server, request = owner
+    original = (
+        live_installed_claims
+        .verify_co_published_cycle_manifest
+    )
+    entered = threading.Event()
+    release = threading.Event()
+    mutation_started = threading.Event()
+    mutation_done = threading.Event()
+    observed = {}
+
+    def delayed_verification(*args, **kwargs):
+        entered.set()
+        assert release.wait(timeout=5)
+        return original(*args, **kwargs)
+
+    def check():
+        observed["check"] = _check(server, request)
+
+    candidate = server._state.clone_for_update()
+    candidate.revision = 2
+
+    def publish():
+        mutation_started.set()
+        observed["publish"] = server._dispatch({
+            "operation": "publish",
+            "state": candidate,
+            "origin": "p1d1e_concurrency_test",
+        })
+        mutation_done.set()
+
+    monkeypatch.setattr(
+        live_installed_claims,
+        "verify_co_published_cycle_manifest",
+        delayed_verification,
+    )
+
+    checker = threading.Thread(target=check)
+    publisher = threading.Thread(target=publish)
+
+    try:
+        checker.start()
+        assert entered.wait(timeout=5)
+
+        publisher.start()
+        assert mutation_started.wait(timeout=5)
+
+        # The mutation cannot commit while the owner-side
+        # receipt verification holds the LIVE state lock.
+        assert not mutation_done.wait(timeout=0.1)
+    finally:
+        release.set()
+        checker.join(timeout=5)
+        if publisher.ident is not None:
+            publisher.join(timeout=5)
+
+    assert not checker.is_alive()
+    assert not publisher.is_alive()
+    assert observed["check"]["status"] == "ok"
+    assert observed["check"]["revision"] == 1
+    assert observed["publish"]["status"] == "ok"
+    assert observed["publish"]["revision"] == 2
+
+    # The earlier successful response only describes
+    # the instant at which revision 1 was installed.
+    later = _check(server, request)
+    assert later["status"] == "unavailable"
+    assert later["reason"] == (
+        "INSTALLED_GENERATION_MISMATCH"
+    )
+
+
+def test_p1d1e_t15_client_uses_endpoint_instance(owner):
+    server, request = owner
+    client = LiveStateClient(server.endpoint)
+    seen = {}
+
+    def recorded(operation, **payload):
+        seen["operation"] = operation
+        seen["payload"] = payload
+        return {"status": "unavailable"}
+
+    client.request = recorded
+    client.verify_installed_cycle_generation(
+        expected_revision=request["expected_revision"],
+        expected_state_id=request["expected_state_id"],
+        expected_repo_id=request["expected_repo_id"],
+        expected_root_path=request["expected_root_path"],
+        expected_graph_sha256=(
+            request["expected_graph_sha256"]
+        ),
+    )
+
+    assert seen["operation"] == (
+        "verify_installed_cycle_generation"
+    )
+    assert seen["payload"][
+        "expected_service_instance_id"
+    ] == server.endpoint.service_instance_id
+
+
+def test_p1d1e_t16_owner_without_authority_fails_closed(
+    owner,
+):
+    server, request = owner
+    server._authority_identity = {}
+    answer = _check(server, request)
+    assert answer["status"] == "unavailable"
+    assert answer["reason"] == (
+        "LIVE_AUTHORITY_UNAVAILABLE"
+    )
```

# FINAL_VERDICT
PARTIAL: exact patch and all named test gates passed; all three files are canonically adopted. The patch introduced one active structural cycle, and running LIVE loaded-code adoption has not been certified. No redesign or additional fix was attempted.
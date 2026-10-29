# CONTEXTOR P1D3-WARN-3A — implementer report

## PREFLIGHT

DIRECT_EVIDENCE: Initial HEAD `ec22db9b7210c3d199607fc4867ff38527c4b727`, clean worktree. Contextor MCP inspected the v2 installed-claims module and IPC owner first; structural cycle count was 16. Local source confirmed the existing v2 verifier, store hydration of partial receipts, `CanonicalLiveServer._dispatch` lock region and endpoint-derived service/process identity. No material preflight mismatch.

## HEAD / WORKTREE

DIRECT_EVIDENCE: Final HEAD unchanged. Only the new helper, `ipc.py`, new test module and this report changed. No commit, push, restart or active user's FULL/LIVE operation.

## NEW INSTALLED CLAIM CONTRACT

CODE_PATH_PROVED: `assess_live_installed_partial_claims` is a read-only helper called under the LIVE state lock. It uses the exact registered `RepositoryAnalysisState` class from `sys.modules`, with no direct import of `analysis.state_manager`. It performs no I/O, source parsing, analyzed-module execution, sealing or mutation. Positive authority is explicitly lock scoped, not stable after reply, not source certified and not runtime safety.

## LIVE AUTHORITY IDENTITY

CODE_PATH_PROVED: Expected revision is an exact positive int; expected strings are exact nonempty bounded strings; graph and claims SHA-256 are exact lowercase 64-character values. Invalid expected envelope, epoch or authority mapping returns `INVALID_EXPECTED_GENERATION`. Owner repository/root/service/process fields must be nonempty and match expected identity.

## PROCESS / SERVICE IDENTITY

CONTRACT_PROVED: Foreign service instance or process start identity fails closed. The client derives both expected values from its own endpoint, never from caller-provided method parameters. The response uses server authority and activity epoch.

## EXACT INSTALLED GENERATION

CODE_PATH_PROVED: Registered class identity, canonical revision, state revision/state ID, optional resync flag and fresh cycle families are checked against the installed in-memory state. A durable receipt alone cannot satisfy this operation. Installing a later committed generation invalidates an older expected identity.

## PARTIAL RECEIPT VERIFICATION

CODE_PATH_PROVED: Exact `CanonicalPartialSCCReceipt` is required. Existing `verify_co_published_partial_scc_preparation` revalidates it; expected claims SHA, semantic graph SHA and current hard-edge fingerprint must all match. No v2 fallback exists. The positive response contains only ordered `members`, `preparation_state` and `model_classification` per SCC.

## IPC LOCK BOUNDARY

CODE_PATH_PROVED: `verify_installed_partial_scc_generation` is in the existing `with self._lock` dispatch region next to v2. Exact request keys are required; extra state, receipt, capture, source and preparation payloads are rejected. Readiness checks occur before helper dispatch. The LIVE protocol version is unchanged.

## CLIENT ENDPOINT IDENTITY

CODE_PATH_PROVED: `LiveStateClient.verify_installed_partial_scc_generation` sends only the six supplied expected generation fields plus endpoint service and process identities using `self.request`.

## PASS / INDETERMINATE

CONTRACT_PROVED: A real isolated FULL/store generation installed in a local LIVE server returned both PASS and INDETERMINATE SCC summaries. The unavailable SCC did not erase the prepared SCC.

## PASS / HAZARD

CONTRACT_PROVED: A separate real PASS/HAZARD FULL/store generation returned two distinct classifications without universal safety language.

## STALE / FOREIGN / FORGED GATES

CONTRACT_PROVED: Focused tests reject uninstalled durable receipt, foreign revision/state/repository/root/service/process identities, graph/claims hash mismatch, missing/forged/digest-tampered/unsupported-version receipts, stale families and resync.

## READINESS / RECOVERY GATES

CONTRACT_PROVED: Pending recovery certificate and degraded release both return `LIVE_OWNER_NOT_READY`. Isolated test flags are cleared before server cleanup.

## V2 COMPATIBILITY

CONTRACT_PROVED: An installed v2-only receipt does not satisfy the new partial operation. The existing `verify_installed_cycle_generation` still succeeds on its valid v2 fixture; its dedicated 18-test gate suite also passed.

## STRUCTURAL DIAGNOSTIC IMMUTABILITY

CONTRACT_PROVED: Repeated checks return identical bounded responses without changing hard edges, SCCs, cycles or diagnostic journal events. Response excludes source bytes, raw fingerprints and state objects.

## FOCUSED TEST RESULTS

DIRECT_EVIDENCE: `py_compile` on all three authorized Python files exited 0. New module: initial run 22 passed, 1 fixture-cleanup failure because synthetic pending recovery blocked close; after restoring readiness flags, 26 passed; after adding newer-generation and extra-payload cases, 29 passed, 0 failed, 0 skipped, 34.03 s. Four required regression modules: 68 passed, 0 failed, 0 skipped, 38.56 s. Dedicated existing v2 installed-generation suite: 18 passed, 0 failed, 0 skipped, 5.68 s. `git diff --check` and untracked-file whitespace checks exited 0. No global pytest.

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_module_context` inspected all three changed files. Revision 848, live provenance, `workspace_sync=verified` for each; graph/topology/structural cycles fresh, cycle_semantics stale. Structural DFS back-edge count remained 16 (prechange 16). New helper hard dependencies are `contracts` and `partial_scc_publication`; IPC gained the intended dependency on `live_installed_partial_claims`. No direct helper edge to `analysis.state_manager` and no newly counted structural cycle. This is source/workspace evidence, not the user's active process adoption.

## FILES_CHANGED

- `contextor/core/cycle_semantics/live_installed_partial_claims.py` (new)
- `contextor/core/live_state/ipc.py`
- `tests/test_cycle_semantics_live_installed_partial_claims.py` (new)

`walkthrough.md` is this report. Complete actual diffs of all three Python files follow.

## FULL_DIFFS


### Modified IPC

```diff
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 257163f..7032732 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -2336,6 +2336,58 @@ class CanonicalLiveServer:
             return self._execute_publish(request)
 
         with self._lock:
+            if operation == "verify_installed_partial_scc_generation":
+                required_fields = {
+                    "operation",
+                    "expected_revision",
+                    "expected_state_id",
+                    "expected_repo_id",
+                    "expected_root_path",
+                    "expected_graph_sha256",
+                    "expected_claims_sha256",
+                    "expected_service_instance_id",
+                    "expected_process_start_identity",
+                }
+                if set(request) != required_fields:
+                    return {
+                        "status": "unavailable",
+                        "reason": "INVALID_GENERATION_CHECK_PAYLOAD",
+                        "revision": self._revision,
+                    }
+                if (
+                    self._stop.is_set()
+                    or self._pending_recovery_certificate is not None
+                    or self._recovery_release_degraded
+                ):
+                    return {
+                        "status": "unavailable",
+                        "reason": "LIVE_OWNER_NOT_READY",
+                        "revision": self._revision,
+                    }
+
+                from contextor.core.cycle_semantics.live_installed_partial_claims import (
+                    assess_live_installed_partial_claims,
+                )
+
+                return assess_live_installed_partial_claims(
+                    self._state,
+                    canonical_revision=self._revision,
+                    authority_identity=self._authority_identity,
+                    activity_epoch=self._activity_epoch,
+                    expected_revision=request.get("expected_revision"),
+                    expected_state_id=request.get("expected_state_id"),
+                    expected_repo_id=request.get("expected_repo_id"),
+                    expected_root_path=request.get("expected_root_path"),
+                    expected_graph_sha256=request.get("expected_graph_sha256"),
+                    expected_claims_sha256=request.get("expected_claims_sha256"),
+                    expected_service_instance_id=request.get(
+                        "expected_service_instance_id"
+                    ),
+                    expected_process_start_identity=request.get(
+                        "expected_process_start_identity"
+                    ),
+                )
+
             if operation == "verify_installed_cycle_generation":
                 required_fields = {
                     "operation",
@@ -2752,6 +2804,29 @@ class LiveStateClient:
             ),
         )
 
+    def verify_installed_partial_scc_generation(
+        self,
+        *,
+        expected_revision: int,
+        expected_state_id: str,
+        expected_repo_id: str,
+        expected_root_path: str,
+        expected_graph_sha256: str,
+        expected_claims_sha256: str,
+    ) -> dict[str, Any]:
+        """Verify the installed partial SCC receipt under the LIVE owner lock."""
+        return self.request(
+            "verify_installed_partial_scc_generation",
+            expected_revision=expected_revision,
+            expected_state_id=expected_state_id,
+            expected_repo_id=expected_repo_id,
+            expected_root_path=expected_root_path,
+            expected_graph_sha256=expected_graph_sha256,
+            expected_claims_sha256=expected_claims_sha256,
+            expected_service_instance_id=self.endpoint.service_instance_id,
+            expected_process_start_identity=self.endpoint.process_start_identity,
+        )
+
     def desktop_claim_status(self) -> dict[str, Any]:
         return self.request("desktop_claim_status")
 
```

### New LIVE helper

```diff
diff --git a/contextor/core/cycle_semantics/live_installed_partial_claims.py b/contextor/core/cycle_semantics/live_installed_partial_claims.py
new file mode 100644
index 0000000..7127e13
--- /dev/null
+++ b/contextor/core/cycle_semantics/live_installed_partial_claims.py
@@ -0,0 +1,180 @@
+"""Lock-scoped comparison of installed partial SCC declarations."""
+
+from __future__ import annotations
+
+import sys
+from collections.abc import Mapping
+from typing import Any
+
+from .contracts import fingerprint_hard_edges
+from .partial_scc_publication import (
+    CanonicalPartialSCCReceipt,
+    verify_co_published_partial_scc_preparation,
+)
+
+
+_PARTIAL_LIVE_AUTHORITY = (
+    "LIVE_OWNER_LOCK_SCOPED_INSTALLED_PARTIAL_SCC_DECLARATIONS"
+    "_NOT_STABLE_AFTER_REPLY"
+    "_NOT_SOURCE_CERTIFIED"
+    "_NOT_RUNTIME_SAFETY"
+)
+
+_PARTIAL_LIVE_MATCH = (
+    "INSTALLED_PARTIAL_SCC_CLAIMS_MATCH_EXPECTED_GENERATION"
+)
+
+
+def assess_live_installed_partial_claims(
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
+    expected_claims_sha256: Any,
+    expected_service_instance_id: Any,
+    expected_process_start_identity: Any,
+) -> dict[str, object]:
+    """Assess the installed generation while the caller holds the LIVE lock."""
+    def unavailable(reason: str) -> dict[str, object]:
+        return {
+            "status": "unavailable",
+            "reason": reason,
+            "revision": canonical_revision,
+            "activity_epoch": activity_epoch,
+            "authority": _PARTIAL_LIVE_AUTHORITY,
+        }
+
+    expected_strings = (
+        expected_state_id,
+        expected_repo_id,
+        expected_root_path,
+        expected_service_instance_id,
+        expected_process_start_identity,
+    )
+    expected_hashes = (expected_graph_sha256, expected_claims_sha256)
+    if (
+        type(expected_revision) is not int
+        or expected_revision < 1
+        or any(
+            type(value) is not str or not value or len(value) > 4096
+            for value in expected_strings
+        )
+        or any(
+            type(value) is not str
+            or len(value) != 64
+            or any(character not in "0123456789abcdef" for character in value)
+            for value in expected_hashes
+        )
+        or type(activity_epoch) is not str
+        or not activity_epoch
+        or not isinstance(authority_identity, Mapping)
+    ):
+        return unavailable("INVALID_EXPECTED_GENERATION")
+
+    owner_repo = authority_identity.get("repo_id")
+    owner_root = authority_identity.get("root_path")
+    owner_instance = authority_identity.get("service_instance_id")
+    owner_process = authority_identity.get("process_start_identity")
+    if any(
+        type(value) is not str or not value
+        for value in (owner_repo, owner_root, owner_instance, owner_process)
+    ):
+        return unavailable("LIVE_AUTHORITY_UNAVAILABLE")
+    if owner_instance != expected_service_instance_id:
+        return unavailable("LIVE_INSTANCE_MISMATCH")
+    if owner_process != expected_process_start_identity:
+        return unavailable("LIVE_PROCESS_START_MISMATCH")
+    if owner_repo != expected_repo_id or owner_root != expected_root_path:
+        return unavailable("LIVE_REPOSITORY_MISMATCH")
+
+    registered_state_type = getattr(
+        sys.modules.get("contextor.core.analysis.state_manager"),
+        "RepositoryAnalysisState",
+        None,
+    )
+    if (
+        type(registered_state_type) is not type
+        or type(state) is not registered_state_type
+    ):
+        return unavailable("INSTALLED_STATE_UNAVAILABLE")
+    if (
+        type(canonical_revision) is not int
+        or canonical_revision != expected_revision
+        or type(getattr(state, "revision", None)) is not int
+        or state.revision != canonical_revision
+        or getattr(state, "state_id", None) != expected_state_id
+    ):
+        return unavailable("INSTALLED_GENERATION_MISMATCH")
+    if getattr(state, "resync_required", False) is not False:
+        return unavailable("CANONICAL_RESYNC_REQUIRED")
+    if (
+        getattr(state, "cycle_semantics_state", None) != "fresh"
+        or getattr(state, "cycles_state", None) != "fresh"
+    ):
+        return unavailable("REQUIRED_CYCLE_FAMILY_NOT_FRESH")
+
+    receipt = getattr(state, "cycle_partial_source_publication", None)
+    if type(receipt) is not CanonicalPartialSCCReceipt:
+        return unavailable("CO_PUBLISHED_PARTIAL_RECEIPT_UNAVAILABLE")
+    try:
+        valid = verify_co_published_partial_scc_preparation(
+            state,
+            revision=canonical_revision,
+            state_id=expected_state_id,
+            repo_id=expected_repo_id,
+            root_path=expected_root_path,
+        )
+    except (
+        AttributeError, KeyError, TypeError, ValueError, IndexError,
+        RecursionError, OverflowError,
+    ):
+        valid = False
+    if not valid:
+        return unavailable("CO_PUBLISHED_PARTIAL_RECEIPT_INVALID")
+    if receipt.claims_sha256 != expected_claims_sha256:
+        return unavailable("INSTALLED_CLAIMS_IDENTITY_MISMATCH")
+    try:
+        snapshot_graph_sha256 = state.cycle_semantics.graph_sha256
+        current_graph_sha256 = fingerprint_hard_edges(
+            state.dependency_graph.hard_edges
+        )
+    except (
+        AttributeError, KeyError, TypeError, ValueError, IndexError,
+        RecursionError, OverflowError,
+    ):
+        return unavailable("INSTALLED_GRAPH_IDENTITY_MISMATCH")
+    if (
+        snapshot_graph_sha256 != expected_graph_sha256
+        or current_graph_sha256 != expected_graph_sha256
+    ):
+        return unavailable("INSTALLED_GRAPH_IDENTITY_MISMATCH")
+
+    components = tuple(
+        {
+            "members": item.members,
+            "preparation_state": item.preparation_state,
+            "model_classification": item.model_classification,
+        }
+        for item in receipt.preparation.component_preparations
+    )
+    return {
+        "status": "ok",
+        "binding_state": _PARTIAL_LIVE_MATCH,
+        "revision": canonical_revision,
+        "state_id": expected_state_id,
+        "repo_id": expected_repo_id,
+        "root_path": expected_root_path,
+        "service_instance_id": expected_service_instance_id,
+        "process_start_identity": expected_process_start_identity,
+        "activity_epoch": activity_epoch,
+        "graph_sha256": expected_graph_sha256,
+        "claims_sha256": expected_claims_sha256,
+        "components": components,
+        "authority": _PARTIAL_LIVE_AUTHORITY,
+    }
```

### New test module

```diff
diff --git a/tests/test_cycle_semantics_live_installed_partial_claims.py b/tests/test_cycle_semantics_live_installed_partial_claims.py
new file mode 100644
index 0000000..817933a
--- /dev/null
+++ b/tests/test_cycle_semantics_live_installed_partial_claims.py
@@ -0,0 +1,299 @@
+"""Installed partial SCC claims are checked against isolated LIVE state."""
+
+from __future__ import annotations
+
+import copy
+from contextlib import contextmanager
+from dataclasses import replace
+from threading import Thread
+
+import pytest
+
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
+from tests.test_original_worker_full_partial_receipt_optin import _persisted
+from tests.test_original_worker_partial_scc_preparation import (
+    PASS_AND_HAZARD, PASS_AND_UNKNOWN, TWO_PASS, _repo,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _full(root, *, partial=True, complete=False):
+    errors, result = ContextorFacade.analyze_project(
+        str(root),
+        cycle_source_preparation_preview=True,
+        cycle_partial_source_publication_opt_in=partial,
+        cycle_source_publication_opt_in=complete,
+    )
+    assert isinstance(errors, list)
+    assert result is not None
+    return result
+
+
+@contextmanager
+def _owner(state, metadata):
+    authority = {
+        "repo_id": metadata.repo_id,
+        "root_path": metadata.root_path,
+        "service_instance_id": "isolated-partial-service",
+        "process_start_identity": "isolated-partial-process",
+    }
+    server = CanonicalLiveServer(
+        state, revision=metadata.revision, authority_identity=authority,
+    )
+    worker = Thread(target=server.serve_forever, daemon=True)
+    worker.start()
+    client = LiveStateClient(server.endpoint)
+    try:
+        assert client.ping()["status"] == "ok"
+        yield server, client
+    finally:
+        assert server.close() is True
+        worker.join(timeout=5.0)
+        assert not worker.is_alive()
+
+
+def _expected(state, metadata):
+    receipt = state.cycle_partial_source_publication
+    return {
+        "expected_revision": metadata.revision,
+        "expected_state_id": metadata.state_id,
+        "expected_repo_id": metadata.repo_id,
+        "expected_root_path": metadata.root_path,
+        "expected_graph_sha256": state.cycle_semantics.graph_sha256,
+        "expected_claims_sha256": receipt.claims_sha256,
+    }
+
+
+def _check(client, state, metadata, **changes):
+    return client.verify_installed_partial_scc_generation(
+        **{**_expected(state, metadata), **changes},
+    )
+
+
+def _fixture(tmp_path, sources=PASS_AND_UNKNOWN, *, partial=True, complete=False):
+    root = _repo(tmp_path, sources)
+    _full(root, partial=partial, complete=complete)
+    state, metadata = _persisted(root)
+    return root, state, metadata
+
+
+def test_t01_t24_mixed_installed_response_preserves_both_sccs(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, client):
+        response = _check(client, state, metadata)
+        assert response["status"] == "ok"
+        assert response["binding_state"] == (
+            "INSTALLED_PARTIAL_SCC_CLAIMS_MATCH_EXPECTED_GENERATION"
+        )
+        assert tuple(item["model_classification"] for item in response["components"]) == (
+            "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "INDETERMINATE",
+        )
+        assert all(
+            set(item) == {"members", "preparation_state", "model_classification"}
+            for item in response["components"]
+        )
+        assert response["activity_epoch"] == server._activity_epoch
+        assert response["service_instance_id"] == server.endpoint.service_instance_id
+        assert response["process_start_identity"] == server.endpoint.process_start_identity
+
+
+def test_t02_hazard_classification_is_distinct(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(tmp_path, PASS_AND_HAZARD)
+    with _owner(state, metadata) as (_, client):
+        response = _check(client, state, metadata)
+        assert response["status"] == "ok"
+        assert tuple(item["model_classification"] for item in response["components"]) == (
+            "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+            "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+        )
+
+
+def test_t03_durable_receipt_without_installation_fails(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(None, metadata) as (_, client):
+        assert _check(client, state, metadata)["status"] == "unavailable"
+
+
+@pytest.mark.parametrize("change", [
+    {"expected_revision": 99},
+    {"expected_state_id": "foreign"},
+    {"expected_repo_id": "foreign"},
+    {"expected_root_path": "foreign"},
+    {"expected_graph_sha256": "0" * 64},
+    {"expected_claims_sha256": "0" * 64},
+])
+def test_t04_t05_t06_t09_t10_foreign_expected_generation(
+    tmp_path, isolated_dirs, change,
+):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (_, client):
+        assert _check(client, state, metadata, **change)["status"] == "unavailable"
+
+
+@pytest.mark.parametrize("field", [
+    "expected_service_instance_id", "expected_process_start_identity",
+])
+def test_t07_t08_foreign_owner_identity(tmp_path, isolated_dirs, field):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, _):
+        request = {
+            "operation": "verify_installed_partial_scc_generation",
+            **_expected(state, metadata),
+            "expected_service_instance_id": server.endpoint.service_instance_id,
+            "expected_process_start_identity": server.endpoint.process_start_identity,
+        }
+        request[field] = "foreign"
+        assert server._dispatch(request)["status"] == "unavailable"
+
+
+@pytest.mark.parametrize("mutation", ["missing", "classification", "digest", "version"])
+def test_t11_t12_t14_invalid_receipt(tmp_path, isolated_dirs, mutation):
+    _, state, metadata = _fixture(tmp_path)
+    expected = _expected(state, metadata)
+    if mutation == "missing":
+        state.cycle_partial_source_publication = None
+    else:
+        receipt = state.cycle_partial_source_publication
+        if mutation == "classification":
+            items = list(receipt.preparation.component_preparations)
+            items[0] = replace(items[0], model_classification="FORGED")
+            state.cycle_partial_source_publication = replace(
+                receipt,
+                preparation=replace(
+                    receipt.preparation, component_preparations=tuple(items),
+                ),
+            )
+        elif mutation == "digest":
+            state.cycle_partial_source_publication = replace(
+                receipt, claims_sha256="0" * 64,
+            )
+        else:
+            state.cycle_partial_source_publication = replace(
+                receipt, version="unsupported",
+            )
+    with _owner(state, metadata) as (_, client):
+        assert client.verify_installed_partial_scc_generation(**expected)["status"] == "unavailable"
+
+
+@pytest.mark.parametrize("mutation", ["semantic", "cycles", "resync"])
+def test_t13_stale_or_resync(tmp_path, isolated_dirs, mutation):
+    _, state, metadata = _fixture(tmp_path)
+    expected = _expected(state, metadata)
+    if mutation == "semantic":
+        state.cycle_semantics_state = "stale"
+    elif mutation == "cycles":
+        state.cycles_state = "stale"
+    else:
+        state.resync_required = True
+    with _owner(state, metadata) as (_, client):
+        assert client.verify_installed_partial_scc_generation(**expected)["status"] == "unavailable"
+
+
+@pytest.mark.parametrize("extra", [
+    "state", "receipt", "source_bytes", "preparation",
+    "captured_index", "prepared_manifest",
+])
+def test_t15_extra_caller_object_rejected(tmp_path, isolated_dirs, extra):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, client):
+        request = {
+            **_expected(state, metadata),
+            "expected_service_instance_id": server.endpoint.service_instance_id,
+            "expected_process_start_identity": server.endpoint.process_start_identity,
+            extra: "not accepted",
+        }
+        response = client.request("verify_installed_partial_scc_generation", **request)
+        assert response["reason"] == "INVALID_GENERATION_CHECK_PAYLOAD"
+        del request[extra]
+        del request["expected_revision"]
+        assert client.request("verify_installed_partial_scc_generation", **request)["reason"] == (
+            "INVALID_GENERATION_CHECK_PAYLOAD"
+        )
+
+
+@pytest.mark.parametrize("readiness", ["pending", "degraded"])
+def test_t16_recovery_not_ready(tmp_path, isolated_dirs, readiness):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, client):
+        if readiness == "pending":
+            server._pending_recovery_certificate = {"certificate_id": "isolated"}
+        else:
+            server._recovery_release_degraded = True
+        assert _check(client, state, metadata)["reason"] == "LIVE_OWNER_NOT_READY"
+        server._pending_recovery_certificate = None
+        server._recovery_release_degraded = False
+
+
+def test_t17_newer_committed_generation_invalidates_old_expected_identity(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    old_expected = _expected(state, metadata)
+    with _owner(state, metadata) as (server, client):
+        assert client.verify_installed_partial_scc_generation(**old_expected)["status"] == "ok"
+        _full(root)
+        newer, newer_metadata = _persisted(root)
+        assert newer_metadata.revision == metadata.revision + 1
+        assert server._execute_publish({
+            "state": newer,
+            "origin": "isolated_test",
+        })["status"] == "ok"
+        assert client.verify_installed_partial_scc_generation(**old_expected)["status"] == "unavailable"
+
+
+def test_t18_v2_only_does_not_satisfy_partial(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS, partial=False, complete=True)
+    assert state.cycle_source_publication is not None
+    assert state.cycle_partial_source_publication is None
+    with _owner(state, metadata) as (server, client):
+        request = {
+            "operation": "verify_installed_partial_scc_generation",
+            "expected_revision": metadata.revision,
+            "expected_state_id": metadata.state_id,
+            "expected_repo_id": metadata.repo_id,
+            "expected_root_path": metadata.root_path,
+            "expected_graph_sha256": state.cycle_semantics.graph_sha256,
+            "expected_claims_sha256": "0" * 64,
+            "expected_service_instance_id": server.endpoint.service_instance_id,
+            "expected_process_start_identity": server.endpoint.process_start_identity,
+        }
+        assert client.request(**request)["status"] == "unavailable"
+        assert client.verify_installed_cycle_generation(
+            expected_revision=metadata.revision,
+            expected_state_id=metadata.state_id,
+            expected_repo_id=metadata.repo_id,
+            expected_root_path=metadata.root_path,
+            expected_graph_sha256=state.cycle_semantics.graph_sha256,
+        )["status"] == "ok"
+
+
+def test_t19_t20_t23_response_is_bounded_read_only_deterministic(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, client):
+        before_edges = copy.deepcopy(state.dependency_graph.hard_edges)
+        before_sccs = copy.deepcopy(state.cycle_semantics.import_sites.topology.cyclic_components)
+        before_cycles = copy.deepcopy(state.cycles)
+        before_events = copy.deepcopy(server._events)
+        first = _check(client, state, metadata)
+        second = _check(client, state, metadata)
+        assert first == second
+        assert first["status"] == "ok"
+        assert set(first) == {
+            "status", "binding_state", "revision", "state_id", "repo_id",
+            "root_path", "service_instance_id", "process_start_identity",
+            "activity_epoch", "graph_sha256", "claims_sha256", "components",
+            "authority",
+        }
+        assert state.dependency_graph.hard_edges == before_edges
+        assert state.cycle_semantics.import_sites.topology.cyclic_components == before_sccs
+        assert state.cycles == before_cycles
+        assert server._events == before_events
```

## CONTRACT_CONFLICTS

NONE observed.

## REMAINING UNKNOWN

UNKNOWN: The user's active LIVE process loaded-code adoption, active service generation and any runtime import safety conclusion. This stage did not modify warning surfaces or trigger active FULL/LIVE.

## FINAL IMPLEMENTER OBSERVATION

CONTRACT_PROVED: The specified read-only lock-scoped partial installed-generation operation and focused regressions pass. Architectural GO remains with ChatGPT. STOP after WARN-3A.


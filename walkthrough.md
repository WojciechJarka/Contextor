# CONTEXTOR C16-B03-P1D3G3

## FILES_CHANGED

- contextor/core/cycle_semantics/live_installed_optional_claims.py
- contextor/core/live_state/ipc.py
- tests/test_cycle_semantics_live_installed_optional_claims.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2; `-B -m pytest -q -rs -p no:cacheprovider`; basetemp outside repository. New isolated LIVE test module: 26 passed in 23.88 s. The required five-module command failed before collection: `ERROR: file or directory not found: tests/test_cycle_semantics_live_installed_claims.py`; no tests ran in that command. `rg --files tests` confirms only `test_cycle_semantics_live_installed_partial_claims.py` and the new optional module match that name family. The instructed path is absent. No substitution or further suite was run. `git diff --check` passed.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP contexts for all three changed modules: canonical_revision=1055, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, syntax_errors=0. Structural DFS cycles=16, equal to prechange count; no new structural cycle observed. Cycle_semantics family=stale. Source diff adds a new IPC dispatch branch inside existing `with self._lock` and one client method; existing operation blocks were not edited. No production FULL, update_file, or manual commit.

## RUNTIME_ADOPTION_STATUS

UNKNOWN: The active backend/LIVE process has not been restarted or checked for loaded-code identity after the ipc.py change. Isolated test PASS does not prove production runtime adoption. A controlled restart and loaded-code freshness check are required before production certification; none was performed in this task.

## FULL_DIFFS

```diff
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index ed4976f..710a016 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -2441,6 +2441,76 @@ class CanonicalLiveServer:
                     activity_epoch=self._activity_epoch,
                 )
 
+            if operation == "verify_installed_optional_scc_generation":
+                required_fields = {
+                    "operation",
+                    "expected_revision",
+                    "expected_state_id",
+                    "expected_repo_id",
+                    "expected_root_path",
+                    "expected_graph_sha256",
+                    "expected_source_manifest_sha256",
+                    "expected_claims_sha256",
+                    "expected_service_instance_id",
+                    "expected_process_start_identity",
+                }
+
+                if set(request) != required_fields:
+                    return {
+                        "status": "unavailable",
+                        "reason": "INVALID_GENERATION_CHECK_PAYLOAD",
+                        "revision": self._revision,
+                    }
+
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
+                from contextor.core.cycle_semantics.live_installed_optional_claims import (
+                    assess_live_installed_optional_claims,
+                )
+
+                return assess_live_installed_optional_claims(
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
+                    expected_source_manifest_sha256=request.get(
+                        "expected_source_manifest_sha256"
+                    ),
+                    expected_claims_sha256=request.get(
+                        "expected_claims_sha256"
+                    ),
+                    expected_service_instance_id=request.get(
+                        "expected_service_instance_id"
+                    ),
+                    expected_process_start_identity=request.get(
+                        "expected_process_start_identity"
+                    ),
+                )
+
             if operation == "verify_installed_partial_scc_generation":
                 required_fields = {
                     "operation",
@@ -2964,6 +3034,38 @@ class LiveStateClient:
             expected_process_start_identity=self.endpoint.process_start_identity,
         )
 
+    def verify_installed_optional_scc_generation(
+        self,
+        *,
+        expected_revision: int,
+        expected_state_id: str,
+        expected_repo_id: str,
+        expected_root_path: str,
+        expected_graph_sha256: str,
+        expected_source_manifest_sha256: str,
+        expected_claims_sha256: str,
+    ) -> dict[str, Any]:
+        """Verify installed optional SCC receipt under owner lock."""
+
+        return self.request(
+            "verify_installed_optional_scc_generation",
+            expected_revision=expected_revision,
+            expected_state_id=expected_state_id,
+            expected_repo_id=expected_repo_id,
+            expected_root_path=expected_root_path,
+            expected_graph_sha256=expected_graph_sha256,
+            expected_source_manifest_sha256=(
+                expected_source_manifest_sha256
+            ),
+            expected_claims_sha256=expected_claims_sha256,
+            expected_service_instance_id=(
+                self.endpoint.service_instance_id
+            ),
+            expected_process_start_identity=(
+                self.endpoint.process_start_identity
+            ),
+        )
+
     def desktop_claim_status(self) -> dict[str, Any]:
         return self.request("desktop_claim_status")

diff --git a/contextor/core/cycle_semantics/live_installed_optional_claims.py b/contextor/core/cycle_semantics/live_installed_optional_claims.py
new file mode 100644
index 0000000..690d488
--- /dev/null
+++ b/contextor/core/cycle_semantics/live_installed_optional_claims.py
@@ -0,0 +1,262 @@
+"""Lock-scoped assessment of installed optional SCC declarations.
+
+The caller must hold the canonical LIVE owner state lock.
+
+This verifies one installed generation and its co-published
+optional SCC receipt. It does not certify original source
+provenance, atomicity, runtime safety or warning eligibility.
+"""
+
+from __future__ import annotations
+
+import sys
+
+from collections.abc import Mapping
+from typing import Any
+
+from .contracts import fingerprint_hard_edges
+from .optional_scc_publication import (
+    CanonicalOptionalSCCReceipt,
+    verify_co_published_optional_scc_preparation,
+)
+
+
+OPTIONAL_LIVE_AUTHORITY = (
+    "LIVE_OWNER_LOCK_SCOPED_INSTALLED_OPTIONAL_SCC_DECLARATIONS"
+    "_NOT_STABLE_AFTER_REPLY"
+    "_NOT_SOURCE_CERTIFIED"
+    "_NOT_RUNTIME_SAFETY"
+)
+
+OPTIONAL_LIVE_MATCH = (
+    "INSTALLED_OPTIONAL_SCC_CLAIMS_MATCH_EXPECTED_GENERATION"
+)
+
+
+def assess_live_installed_optional_claims(
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
+    expected_source_manifest_sha256: Any,
+    expected_claims_sha256: Any,
+    expected_service_instance_id: Any,
+    expected_process_start_identity: Any,
+) -> dict[str, Any]:
+    """Compare expectations with the installed LIVE-owned state.
+
+    Caller must hold CanonicalLiveServer._lock throughout
+    evaluation and response construction.
+    """
+
+    def unavailable(reason: str) -> dict[str, Any]:
+        return {
+            "status": "unavailable",
+            "reason": reason,
+            "revision": canonical_revision,
+            "activity_epoch": activity_epoch,
+            "authority": OPTIONAL_LIVE_AUTHORITY,
+        }
+
+    expected_strings = (
+        expected_state_id,
+        expected_repo_id,
+        expected_root_path,
+        expected_service_instance_id,
+        expected_process_start_identity,
+    )
+
+    expected_hashes = (
+        expected_graph_sha256,
+        expected_source_manifest_sha256,
+        expected_claims_sha256,
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
+        or any(
+            type(value) is not str
+            or len(value) != 64
+            or any(
+                character not in "0123456789abcdef"
+                for character in value
+            )
+            for value in expected_hashes
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
+    owner_process = authority_identity.get(
+        "process_start_identity"
+    )
+
+    if any(
+        type(value) is not str or not value
+        for value in (
+            owner_repo,
+            owner_root,
+            owner_instance,
+            owner_process,
+        )
+    ):
+        return unavailable("LIVE_AUTHORITY_UNAVAILABLE")
+
+    if owner_instance != expected_service_instance_id:
+        return unavailable("LIVE_INSTANCE_MISMATCH")
+
+    if owner_process != expected_process_start_identity:
+        return unavailable("LIVE_PROCESS_START_MISMATCH")
+
+    if (
+        owner_repo != expected_repo_id
+        or owner_root != expected_root_path
+    ):
+        return unavailable("LIVE_REPOSITORY_MISMATCH")
+
+    # Resolve existing loaded class without importing
+    # analysis.state_manager from LIVE query code.
+    registered_state_type = getattr(
+        sys.modules.get(
+            "contextor.core.analysis.state_manager"
+        ),
+        "RepositoryAnalysisState",
+        None,
+    )
+
+    if (
+        type(registered_state_type) is not type
+        or type(state) is not registered_state_type
+    ):
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
+        "cycle_optional_source_publication",
+        None,
+    )
+
+    if type(receipt) is not CanonicalOptionalSCCReceipt:
+        return unavailable("CO_PUBLISHED_OPTIONAL_RECEIPT_UNAVAILABLE")
+
+    try:
+        valid = verify_co_published_optional_scc_preparation(
+            state,
+            revision=canonical_revision,
+            state_id=expected_state_id,
+            repo_id=owner_repo,
+            root_path=owner_root,
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
+        valid = False
+
+    if not valid:
+        return unavailable("CO_PUBLISHED_OPTIONAL_RECEIPT_INVALID")
+
+    manifest = receipt.preparation.manifest
+
+    if (
+        manifest is None
+        or receipt.claims_sha256 != expected_claims_sha256
+    ):
+        return unavailable("INSTALLED_CLAIMS_IDENTITY_MISMATCH")
+
+    if (
+        manifest.source_manifest_sha256
+        != expected_source_manifest_sha256
+    ):
+        return unavailable("INSTALLED_MANIFEST_IDENTITY_MISMATCH")
+
+    try:
+        current_graph_sha256 = fingerprint_hard_edges(
+            state.dependency_graph.hard_edges
+        )
+        snapshot_graph_sha256 = (
+            state.cycle_semantics.graph_sha256
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
+        return unavailable("INSTALLED_GRAPH_IDENTITY_MISMATCH")
+
+    if (
+        manifest.graph_sha256 != expected_graph_sha256
+        or snapshot_graph_sha256 != expected_graph_sha256
+        or current_graph_sha256 != expected_graph_sha256
+    ):
+        return unavailable("INSTALLED_GRAPH_IDENTITY_MISMATCH")
+
+    return {
+        "status": "ok",
+        "binding_state": OPTIONAL_LIVE_MATCH,
+        "revision": canonical_revision,
+        "state_id": expected_state_id,
+        "repo_id": owner_repo,
+        "root_path": owner_root,
+        "service_instance_id": owner_instance,
+        "process_start_identity": owner_process,
+        "activity_epoch": activity_epoch,
+        "graph_sha256": expected_graph_sha256,
+        "source_manifest_sha256": expected_source_manifest_sha256,
+        "claims_sha256": expected_claims_sha256,
+        "authority": OPTIONAL_LIVE_AUTHORITY,
+    }

diff --git a/tests/test_cycle_semantics_live_installed_optional_claims.py b/tests/test_cycle_semantics_live_installed_optional_claims.py
new file mode 100644
index 0000000..2e525c7
--- /dev/null
+++ b/tests/test_cycle_semantics_live_installed_optional_claims.py
@@ -0,0 +1,388 @@
+"""P1D3G3: installed optional SCC receipt identity under LIVE lock."""
+
+import copy
+
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.cycle_semantics.warning_eligibility import (
+    _verified_model_pass_cycle_paths,
+)
+from tests.test_cycle_semantics_live_installed_partial_claims import (
+    _owner,
+)
+from tests.test_cycle_semantics_optional_child_full_preview import (
+    _repo,
+)
+from tests.test_original_worker_full_receipt_optin import (
+    _persisted,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _full(root, *, publication=True):
+    errors, result = ContextorFacade.analyze_project(
+        str(root),
+        cycle_source_preparation_preview=True,
+        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
+        cycle_optional_source_publication_opt_in=publication,
+    )
+    assert isinstance(errors, list)
+    assert result is not None
+    return result
+
+
+def _fixture(tmp_path, *, publication=True):
+    root = _repo(tmp_path)
+    _full(root, publication=publication)
+    state, metadata = _persisted(root)
+    return root, state, metadata
+
+
+def _expected(state, metadata):
+    receipt = state.cycle_optional_source_publication
+    manifest = receipt.preparation.manifest
+
+    return {
+        "expected_revision": metadata.revision,
+        "expected_state_id": metadata.state_id,
+        "expected_repo_id": metadata.repo_id,
+        "expected_root_path": metadata.root_path,
+        "expected_graph_sha256": manifest.graph_sha256,
+        "expected_source_manifest_sha256": (
+            manifest.source_manifest_sha256
+        ),
+        "expected_claims_sha256": receipt.claims_sha256,
+    }
+
+
+def _check(client, expected, **overrides):
+    return client.verify_installed_optional_scc_generation(
+        **{**expected, **overrides},
+    )
+
+
+def test_t01_installed_optional_receipt_matches(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path)
+    expected = _expected(state, metadata)
+
+    with _owner(state, metadata) as (server, client):
+        response = _check(client, expected)
+
+        assert response["status"] == "ok"
+        assert response["binding_state"] == (
+            "INSTALLED_OPTIONAL_SCC_CLAIMS_MATCH_EXPECTED_GENERATION"
+        )
+        assert response["revision"] == metadata.revision
+        assert response["state_id"] == metadata.state_id
+        assert response["graph_sha256"] == (
+            expected["expected_graph_sha256"]
+        )
+        assert response["source_manifest_sha256"] == (
+            expected["expected_source_manifest_sha256"]
+        )
+        assert response["claims_sha256"] == (
+            expected["expected_claims_sha256"]
+        )
+        assert response["activity_epoch"] == (
+            server._activity_epoch
+        )
+        assert response["service_instance_id"] == (
+            server.endpoint.service_instance_id
+        )
+        assert response["process_start_identity"] == (
+            server.endpoint.process_start_identity
+        )
+
+        assert set(response) == {
+            "status",
+            "binding_state",
+            "revision",
+            "state_id",
+            "repo_id",
+            "root_path",
+            "service_instance_id",
+            "process_start_identity",
+            "activity_epoch",
+            "graph_sha256",
+            "source_manifest_sha256",
+            "claims_sha256",
+            "authority",
+        }
+
+        assert response == _check(client, expected)
+
+    assert _verified_model_pass_cycle_paths(
+        state,
+        expected_revision=metadata.revision,
+        expected_state_id=metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=metadata.root_path,
+    ) == frozenset()
+
+
+def test_t02_committed_receipt_without_installation_fails(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path)
+    expected = _expected(state, metadata)
+
+    with _owner(None, metadata) as (_, client):
+        response = _check(client, expected)
+        assert response["status"] == "unavailable"
+
+
+@pytest.mark.parametrize(
+    "field,value",
+    [
+        ("expected_revision", 999999),
+        ("expected_state_id", "foreign-state"),
+        ("expected_repo_id", "foreign-repo"),
+        ("expected_root_path", "foreign-root"),
+        ("expected_graph_sha256", "0" * 64),
+        ("expected_source_manifest_sha256", "0" * 64),
+        ("expected_claims_sha256", "0" * 64),
+    ],
+)
+def test_t03_expected_identity_mismatch_fails(
+    tmp_path, isolated_dirs, field, value,
+):
+    _, state, metadata = _fixture(tmp_path)
+    expected = _expected(state, metadata)
+
+    with _owner(state, metadata) as (_, client):
+        response = _check(
+            client,
+            expected,
+            **{field: value},
+        )
+        assert response["status"] == "unavailable"
+
+
+@pytest.mark.parametrize(
+    "field",
+    [
+        "expected_service_instance_id",
+        "expected_process_start_identity",
+    ],
+)
+def test_t04_foreign_owner_identity_fails(
+    tmp_path, isolated_dirs, field,
+):
+    _, state, metadata = _fixture(tmp_path)
+    expected = _expected(state, metadata)
+
+    with _owner(state, metadata) as (server, _):
+        request = {
+            "operation": "verify_installed_optional_scc_generation",
+            **expected,
+            "expected_service_instance_id": (
+                server.endpoint.service_instance_id
+            ),
+            "expected_process_start_identity": (
+                server.endpoint.process_start_identity
+            ),
+        }
+        request[field] = "foreign"
+
+        response = server._dispatch(request)
+        assert response["status"] == "unavailable"
+
+
+@pytest.mark.parametrize(
+    "mutation",
+    ["missing", "claims", "manifest", "classification", "version"],
+)
+def test_t05_invalid_installed_receipt_fails(
+    tmp_path, isolated_dirs, mutation,
+):
+    _, state, metadata = _fixture(tmp_path)
+    expected = _expected(state, metadata)
+
+    receipt = state.cycle_optional_source_publication
+
+    if mutation == "missing":
+        state.cycle_optional_source_publication = None
+
+    elif mutation == "claims":
+        state.cycle_optional_source_publication = replace(
+            receipt,
+            claims_sha256="0" * 64,
+        )
+
+    elif mutation == "manifest":
+        invalid_manifest = replace(
+            receipt.preparation.manifest,
+            source_manifest_sha256="0" * 64,
+        )
+        state.cycle_optional_source_publication = replace(
+            receipt,
+            preparation=replace(
+                receipt.preparation,
+                manifest=invalid_manifest,
+            ),
+        )
+
+    elif mutation == "classification":
+        components = list(
+            receipt.preparation.component_preparations
+        )
+        components[0] = replace(
+            components[0],
+            model_classification="FORGED",
+        )
+        state.cycle_optional_source_publication = replace(
+            receipt,
+            preparation=replace(
+                receipt.preparation,
+                component_preparations=tuple(components),
+            ),
+        )
+
+    else:
+        state.cycle_optional_source_publication = replace(
+            receipt,
+            version="unsupported",
+        )
+
+    with _owner(state, metadata) as (_, client):
+        response = _check(client, expected)
+        assert response["status"] == "unavailable"
+
+
+@pytest.mark.parametrize(
+    "mutation",
+    ["semantics", "cycles", "resync"],
+)
+def test_t06_stale_or_resync_fails(
+    tmp_path, isolated_dirs, mutation,
+):
+    _, state, metadata = _fixture(tmp_path)
+    expected = _expected(state, metadata)
+
+    if mutation == "semantics":
+        state.cycle_semantics_state = "stale"
+    elif mutation == "cycles":
+        state.cycles_state = "stale"
+    else:
+        state.resync_required = True
+
+    with _owner(state, metadata) as (_, client):
+        response = _check(client, expected)
+        assert response["status"] == "unavailable"
+
+
+@pytest.mark.parametrize(
+    "extra",
+    ["state", "receipt", "source_bytes", "preparation"],
+)
+def test_t07_extra_payload_rejected(
+    tmp_path, isolated_dirs, extra,
+):
+    _, state, metadata = _fixture(tmp_path)
+    expected = _expected(state, metadata)
+
+    with _owner(state, metadata) as (server, client):
+        request = {
+            **expected,
+            "expected_service_instance_id": (
+                server.endpoint.service_instance_id
+            ),
+            "expected_process_start_identity": (
+                server.endpoint.process_start_identity
+            ),
+            extra: "not accepted",
+        }
+
+        response = client.request(
+            "verify_installed_optional_scc_generation",
+            **request,
+        )
+        assert response["status"] == "unavailable"
+        assert response["reason"] == (
+            "INVALID_GENERATION_CHECK_PAYLOAD"
+        )
+
+
+def test_t08_recovery_not_ready_rejected(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path)
+    expected = _expected(state, metadata)
+
+    with _owner(state, metadata) as (server, client):
+        server._pending_recovery_certificate = {
+            "certificate_id": "isolated",
+        }
+
+        try:
+            response = _check(client, expected)
+            assert response["status"] == "unavailable"
+            assert response["reason"] == "LIVE_OWNER_NOT_READY"
+        finally:
+            server._pending_recovery_certificate = None
+
+
+def test_t09_newer_installation_invalidates_old_check(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(tmp_path)
+    old_expected = _expected(state, metadata)
+
+    with _owner(state, metadata) as (server, client):
+        assert _check(client, old_expected)["status"] == "ok"
+
+        _full(root, publication=True)
+        newer, newer_metadata = _persisted(root)
+
+        assert newer_metadata.revision > metadata.revision
+
+        published = server._execute_publish({
+            "state": newer,
+            "origin": "isolated_test",
+        })
+        assert published["status"] == "ok"
+
+        assert _check(client, old_expected)["status"] == "unavailable"
+        assert _check(
+            client,
+            _expected(newer, newer_metadata),
+        )["status"] == "ok"
+
+
+def test_t10_read_only_and_no_diagnostic_mutation(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path)
+    expected = _expected(state, metadata)
+
+    original_edges = copy.deepcopy(
+        state.dependency_graph.hard_edges
+    )
+    original_cycles = copy.deepcopy(state.cycles)
+    original_scc = copy.deepcopy(
+        state.cycle_semantics.import_sites.topology.cyclic_components
+    )
+
+    with _owner(state, metadata) as (server, client):
+        original_events = copy.deepcopy(server._events)
+
+        assert _check(client, expected)["status"] == "ok"
+        assert _check(client, expected)["status"] == "ok"
+
+        assert server._events == original_events
+
+    assert state.dependency_graph.hard_edges == original_edges
+    assert state.cycles == original_cycles
+    assert (
+        state.cycle_semantics.import_sites.topology.cyclic_components
+        == original_scc
+    )
```

## FINAL_VERDICT

CONTRACT_CONFLICT

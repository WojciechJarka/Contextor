# CONTEXTOR P1D3-WARN-4C — implementer report

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP inspected `ipc.py` and the existing pure warning projection first. Both new paths were absent. The two exact IPC patch anchors were present. No material drift. Prechange structural DFS back-edge count was 16.

## HEAD / WORKTREE

DIRECT_EVIDENCE: Initial and final HEAD `659fe7c6112de9cf7b7011a95256d2cc3d949eed`; initial worktree clean. Final changes are the three authorized Python files and this report. No commit, push, restart or active user's FULL/LIVE.

## EXACT PATCH RESULT

DIRECT_EVIDENCE: The two new files were created from the supplied unified diff, preserving their supplied 135 and 215 source lines. The two IPC hunks were inserted at the exact anchors without modifying other logic or test assertions.

## NEW TEST RESULTS

DIRECT_EVIDENCE: `py_compile` on all three Python files exited 0. `tests/test_cycle_semantics_live_cycle_warning_query.py`: 19 passed, 0 failed, 0 skipped, 22.04 s, exit 0.

## FOCUSED REGRESSIONS

DIRECT_EVIDENCE: Three requested modules passed: 82 passed, 0 failed, 0 skipped, 67.69 s, exit 0. Tracked and new-file `git diff --check` whitespace checks exited 0. No global suite ran.

## IPC LOCK BOUNDARY

CODE_PATH_PROVED: New `get_installed_cycle_warning_projection` dispatch is inside the existing `with self._lock` region. It accepts exactly the operation key, checks stop/pending/degraded readiness and calls the new pure query before releasing the lock. The client method sends no caller-provided state or receipt object.

## INSTALLED GENERATION IDENTITY

CODE_PATH_PROVED: The new query derives canonical revision, state ID, repository/root, service instance, process start and activity epoch from the installed owner. Exact registered state class is resolved through `sys.modules`; a durable receipt without installed state cannot qualify. No protocol version changed.

## STRUCTURAL / MODEL_PASS / ACTIVE COUNTS

CONTRACT_PROVED: Genuine isolated FULL/store/LIVE PASS/INDETERMINATE and PASS/HAZARD had two structural paths, one accepted and one active. TWO_PASS had two accepted and zero active. Default/v2-only generations retained all structural paths as active. Fresh acyclic generation returned empty path tuples and zero counts.

## FAIL-CLOSED NEGATIVE CASES

CONTRACT_PROVED: Tests covered missing or forged partial receipt, stale/resync/duplicate structural inventory, absent installed state, wrong installed revision, incomplete authority, extra request keys and recovery readiness. Invalid structural inventory returned unavailable without an active warning count. The read-only query left the server event journal and state cycles unchanged.

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_module_context` inspected all three files at canonical revision 864, with `workspace_sync=verified`, live provenance, fresh module/graph/topology/structural cycles and stale cycle_semantics. Structural DFS back-edge count remained 16. New query imports `contracts`, `cycle_warning_projection` and `partial_scc_publication`; IPC gained the specified hard dependency on the query. No newly counted structural cycle. This is source/workspace synchronization, not active loaded-code adoption.

## FILES_CHANGED

- `contextor/core/cycle_semantics/live_cycle_warning_query.py` (new)
- `tests/test_cycle_semantics_live_cycle_warning_query.py` (new)
- `contextor/core/live_state/ipc.py`

`walkthrough.md` is this report. Complete actual diffs of all three Python files follow.

## FULL_DIFFS


### Modified IPC

```diff
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 7032732..596c80d 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -2336,6 +2336,34 @@ class CanonicalLiveServer:
             return self._execute_publish(request)
 
         with self._lock:
+            if operation == "get_installed_cycle_warning_projection":
+                if set(request) != {"operation"}:
+                    return {
+                        "status": "unavailable",
+                        "reason": "INVALID_CYCLE_WARNING_PROJECTION_PAYLOAD",
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
+                from contextor.core.cycle_semantics.live_cycle_warning_query import (
+                    read_locked_installed_cycle_warnings,
+                )
+
+                return read_locked_installed_cycle_warnings(
+                    self._state,
+                    canonical_revision=self._revision,
+                    authority_identity=self._authority_identity,
+                    activity_epoch=self._activity_epoch,
+                )
+
             if operation == "verify_installed_partial_scc_generation":
                 required_fields = {
                     "operation",
@@ -2804,6 +2832,10 @@ class LiveStateClient:
             ),
         )
 
+    def get_installed_cycle_warning_projection(self) -> dict[str, Any]:
+        """Read the current canonical LIVE warning partition under its lock."""
+        return self.request("get_installed_cycle_warning_projection")
+
     def verify_installed_partial_scc_generation(
         self,
         *,
```

### New LIVE query

```diff
diff --git a/contextor/core/cycle_semantics/live_cycle_warning_query.py b/contextor/core/cycle_semantics/live_cycle_warning_query.py
new file mode 100644
index 0000000..c951e0b
--- /dev/null
+++ b/contextor/core/cycle_semantics/live_cycle_warning_query.py
@@ -0,0 +1,135 @@
+"""Lock-scoped, read-only projection of canonical LIVE cycle warnings.
+
+The owner obtains and reports its own generation identity. No caller
+supplies a state, receipt, graph, or source capture. MODEL_PASS is a
+restricted static-model claim, not a runtime safety certificate.
+"""
+
+from __future__ import annotations
+
+import sys
+from collections.abc import Mapping
+from typing import Any
+
+from .contracts import fingerprint_hard_edges
+from .cycle_warning_projection import project_installed_cycle_warnings
+from .partial_scc_publication import CanonicalPartialSCCReceipt
+
+
+_AUTHORITY = (
+    "LIVE_OWNER_LOCK_SCOPED_CYCLE_WARNING_PROJECTION"
+    "_NOT_STABLE_AFTER_REPLY_NOT_RUNTIME_SAFETY"
+)
+_BINDING = "INSTALLED_CYCLE_WARNING_PROJECTION"
+_NO_RECEIPT_SHA256 = "0" * 64
+
+
+def read_locked_installed_cycle_warnings(
+    state: Any,
+    *,
+    canonical_revision: int,
+    authority_identity: Mapping[str, Any],
+    activity_epoch: str,
+) -> dict[str, Any]:
+    """Project installed warnings; the caller MUST hold the LIVE owner lock."""
+    def unavailable(reason: str) -> dict[str, Any]:
+        return {
+            "status": "unavailable",
+            "reason": reason,
+            "revision": canonical_revision,
+            "activity_epoch": activity_epoch,
+            "authority": _AUTHORITY,
+        }
+
+    if (
+        type(canonical_revision) is not int
+        or canonical_revision < 1
+        or type(activity_epoch) is not str
+        or not activity_epoch
+        or not isinstance(authority_identity, Mapping)
+    ):
+        return unavailable("INSTALLED_GENERATION_UNAVAILABLE")
+
+    owner_values = tuple(
+        authority_identity.get(name)
+        for name in (
+            "repo_id", "root_path", "service_instance_id",
+            "process_start_identity",
+        )
+    )
+    if any(type(value) is not str or not value for value in owner_values):
+        return unavailable("LIVE_AUTHORITY_UNAVAILABLE")
+    repo_id, root_path, service_instance_id, process_start_identity = owner_values
+
+    registered = getattr(
+        sys.modules.get("contextor.core.analysis.state_manager"),
+        "RepositoryAnalysisState", None,
+    )
+    if type(registered) is not type or type(state) is not registered:
+        return unavailable("INSTALLED_STATE_UNAVAILABLE")
+
+    revision = getattr(state, "revision", None)
+    state_id = getattr(state, "state_id", None)
+    if (
+        type(revision) is not int
+        or revision != canonical_revision
+        or type(state_id) is not str
+        or not state_id
+    ):
+        return unavailable("INSTALLED_GENERATION_MISMATCH")
+
+    try:
+        graph_sha256 = fingerprint_hard_edges(state.dependency_graph.hard_edges)
+        receipt = getattr(state, "cycle_partial_source_publication", None)
+        claims_sha256 = (
+            receipt.claims_sha256
+            if type(receipt) is CanonicalPartialSCCReceipt
+            and type(receipt.claims_sha256) is str
+            else _NO_RECEIPT_SHA256
+        )
+        projection = project_installed_cycle_warnings(
+            state,
+            canonical_revision=canonical_revision,
+            authority_identity=authority_identity,
+            activity_epoch=activity_epoch,
+            expected_revision=canonical_revision,
+            expected_state_id=state_id,
+            expected_repo_id=repo_id,
+            expected_root_path=root_path,
+            expected_graph_sha256=graph_sha256,
+            expected_claims_sha256=claims_sha256,
+            expected_service_instance_id=service_instance_id,
+            expected_process_start_identity=process_start_identity,
+        )
+    except (AttributeError, KeyError, TypeError, ValueError, IndexError,
+            RecursionError, OverflowError):
+        return unavailable("CYCLE_WARNING_PROJECTION_UNAVAILABLE")
+
+    if projection.status != "FRESH":
+        return unavailable(projection.reason or "CYCLE_WARNING_PROJECTION_UNAVAILABLE")
+
+    structural = projection.structural_paths
+    accepted = projection.model_pass_paths
+    active = projection.active_warning_paths
+    if any(type(value) is not tuple for value in (structural, accepted, active)):
+        return unavailable("CYCLE_WARNING_PROJECTION_UNAVAILABLE")
+
+    return {
+        "status": "ok",
+        "binding_state": _BINDING,
+        "revision": canonical_revision,
+        "state_id": state_id,
+        "repo_id": repo_id,
+        "root_path": root_path,
+        "service_instance_id": service_instance_id,
+        "process_start_identity": process_start_identity,
+        "activity_epoch": activity_epoch,
+        "graph_sha256": graph_sha256,
+        "structural_paths": structural,
+        "model_pass_paths": accepted,
+        "active_warning_paths": active,
+        "structural_count": len(structural),
+        "model_pass_count": len(accepted),
+        "active_warning_count": len(active),
+        "authority": _AUTHORITY,
+    }
```

### New test module

```diff
diff --git a/tests/test_cycle_semantics_live_cycle_warning_query.py b/tests/test_cycle_semantics_live_cycle_warning_query.py
new file mode 100644
index 0000000..d26a174
--- /dev/null
+++ b/tests/test_cycle_semantics_live_cycle_warning_query.py
@@ -0,0 +1,215 @@
+"""Read-only canonical LIVE cycle-warning projection, no user service access."""
+
+from __future__ import annotations
+
+import copy
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.api.facade import ContextorFacade
+from tests.test_cycle_semantics_live_installed_partial_claims import (
+    _fixture, _full, _owner, _persisted,
+)
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
+@pytest.mark.parametrize("sources,expected_accepted", [
+    (PASS_AND_UNKNOWN, 1),
+    (PASS_AND_HAZARD, 1),
+    (TWO_PASS, 2),
+])
+def test_t01_t03_real_installed_partial_projection(
+    tmp_path, isolated_dirs, sources, expected_accepted,
+):
+    _, state, metadata = _fixture(tmp_path, sources)
+    with _owner(state, metadata) as (server, client):
+        before = copy.deepcopy((server._events, server._activity_seq, state.cycles))
+        answer = client.get_installed_cycle_warning_projection()
+        assert answer["status"] == "ok"
+        assert answer["binding_state"] == "INSTALLED_CYCLE_WARNING_PROJECTION"
+        assert answer["revision"] == metadata.revision
+        assert answer["structural_count"] == 2
+        assert answer["model_pass_count"] == expected_accepted
+        assert answer["active_warning_count"] == 2 - expected_accepted
+        assert answer["structural_paths"] == tuple(tuple(path) for path in state.cycles)
+        assert answer["model_pass_paths"] == tuple(
+            tuple(path) for path in state.cycles[:expected_accepted]
+        )
+        assert answer["active_warning_paths"] == tuple(
+            tuple(path) for path in state.cycles[expected_accepted:]
+        )
+        assert answer["activity_epoch"] == server._activity_epoch
+        assert answer["service_instance_id"] == server.endpoint.service_instance_id
+        assert answer["process_start_identity"] == server.endpoint.process_start_identity
+        assert (server._events, server._activity_seq, state.cycles) == before
+        assert client.get_installed_cycle_warning_projection() == answer
+
+
+def test_t04_default_full_has_all_structural_cycles_active(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, TWO_PASS)
+    errors, result = ContextorFacade.analyze_project(str(root))
+    assert isinstance(errors, list) and result is not None
+    state, metadata = _persisted(root)
+    assert state.cycle_partial_source_publication is None
+    with _owner(state, metadata) as (_, client):
+        answer = client.get_installed_cycle_warning_projection()
+        assert answer["status"] == "ok"
+        assert answer["structural_count"] == answer["active_warning_count"] == 2
+        assert answer["model_pass_paths"] == ()
+
+
+def test_t05_v2_only_receipt_does_not_accept_partial(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(
+        tmp_path, TWO_PASS, partial=False, complete=True,
+    )
+    assert state.cycle_source_publication is not None
+    with _owner(state, metadata) as (_, client):
+        answer = client.get_installed_cycle_warning_projection()
+        assert answer["status"] == "ok"
+        assert answer["structural_count"] == answer["active_warning_count"] == 2
+        assert answer["model_pass_count"] == 0
+
+
+def test_t06_valid_fresh_acyclic_generation(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(tmp_path, {"a": "value = 1\n"})
+    with _owner(state, metadata) as (_, client):
+        answer = client.get_installed_cycle_warning_projection()
+        assert answer["status"] == "ok"
+        assert answer["structural_paths"] == ()
+        assert answer["model_pass_paths"] == ()
+        assert answer["active_warning_paths"] == ()
+        assert answer["structural_count"] == answer["active_warning_count"] == 0
+
+
+def test_t07_missing_partial_receipt_reactivates_all(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+    state.cycle_partial_source_publication = None
+    with _owner(state, metadata) as (_, client):
+        answer = client.get_installed_cycle_warning_projection()
+        assert answer["status"] == "ok"
+        assert answer["model_pass_count"] == 0
+        assert answer["active_warning_count"] == 2
+
+
+def test_t08_forged_receipt_fails_closed_without_hiding_paths(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+    receipt = state.cycle_partial_source_publication
+    state.cycle_partial_source_publication = replace(receipt, claims_sha256="0" * 64)
+    with _owner(state, metadata) as (_, client):
+        answer = client.get_installed_cycle_warning_projection()
+        assert answer["status"] == "ok"
+        assert answer["model_pass_count"] == 0
+        assert answer["active_warning_count"] == 2
+
+
+@pytest.mark.parametrize("mutation", ["stale", "resync", "duplicate"])
+def test_t09_unavailable_structural_inventory_is_not_zero(
+    tmp_path, isolated_dirs, mutation,
+):
+    _, state, metadata = _fixture(tmp_path)
+    if mutation == "stale":
+        state.cycles_state = "stale"
+    elif mutation == "resync":
+        state.resync_required = True
+    else:
+        state.cycles.append(list(state.cycles[0]))
+    with _owner(state, metadata) as (_, client):
+        answer = client.get_installed_cycle_warning_projection()
+        assert answer["status"] == "unavailable"
+        assert answer["reason"] == "STRUCTURAL_CYCLE_INVENTORY_UNAVAILABLE"
+        assert "active_warning_count" not in answer
+
+
+def test_t10_durable_receipt_without_installed_state_is_not_accepted(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(None, metadata) as (_, client):
+        answer = client.get_installed_cycle_warning_projection()
+        assert answer["status"] == "unavailable"
+        assert answer["reason"] == "INSTALLED_STATE_UNAVAILABLE"
+
+
+def test_t11_wrong_loaded_revision_fails_closed(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (_, client):
+        state.revision += 1
+        answer = client.get_installed_cycle_warning_projection()
+        assert answer["status"] == "unavailable"
+        assert answer["reason"] == "INSTALLED_GENERATION_MISMATCH"
+
+
+def test_t12_foreign_or_incomplete_authority_fails_closed(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, client):
+        server._authority_identity["process_start_identity"] = None
+        answer = client.get_installed_cycle_warning_projection()
+        assert answer["status"] == "unavailable"
+        assert answer["reason"] == "LIVE_AUTHORITY_UNAVAILABLE"
+
+
+def test_t13_extra_request_keys_are_rejected(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (_, client):
+        for extra in ("state", "receipt", "source_bytes", "expected_revision"):
+            answer = client.request("get_installed_cycle_warning_projection", **{extra: "forbidden"})
+            assert answer["status"] == "unavailable"
+            assert answer["reason"] == "INVALID_CYCLE_WARNING_PROJECTION_PAYLOAD"
+
+
+@pytest.mark.parametrize("readiness", ["pending", "degraded"])
+def test_t14_recovery_not_ready_returns_unavailable(tmp_path, isolated_dirs, readiness):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, client):
+        try:
+            if readiness == "pending":
+                server._pending_recovery_certificate = {"certificate_id": "synthetic"}
+            else:
+                server._recovery_release_degraded = True
+            answer = client.get_installed_cycle_warning_projection()
+            assert answer["status"] == "unavailable"
+            assert answer["reason"] == "LIVE_OWNER_NOT_READY"
+        finally:
+            server._pending_recovery_certificate = None
+            server._recovery_release_degraded = False
+
+
+def test_t15_new_installed_generation_restores_warnings(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, client):
+        first = client.get_installed_cycle_warning_projection()
+        assert first["active_warning_count"] == 0
+        _full(root, partial=False)
+        newer, newer_metadata = _persisted(root)
+        assert newer_metadata.revision == metadata.revision + 1
+        assert server._execute_publish({
+            "state": newer, "origin": "isolated_test",
+        })["status"] == "ok"
+        second = client.get_installed_cycle_warning_projection()
+        assert second["status"] == "ok"
+        assert second["revision"] == newer_metadata.revision
+        assert second["structural_paths"] == first["structural_paths"]
+        assert second["model_pass_count"] == 0
+        assert second["active_warning_count"] == 2
+        assert second["activity_epoch"] == first["activity_epoch"]
+
+
+def test_t16_valid_result_has_no_receipt_or_source_bytes(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (_, client):
+        answer = client.get_installed_cycle_warning_projection()
+        assert set(answer) == {
+            "status", "binding_state", "revision", "state_id", "repo_id",
+            "root_path", "service_instance_id", "process_start_identity",
+            "activity_epoch", "graph_sha256", "structural_paths",
+            "model_pass_paths", "active_warning_paths", "structural_count",
+            "model_pass_count", "active_warning_count", "authority",
+        }
```

## CONTRACT_CONFLICTS

NONE observed.

## REMAINING UNKNOWN

UNKNOWN: The user's active LIVE process loaded-code adoption, active service generation and downstream Desktop/MCP/get_live_events consumer behavior. This patch added no warning consumer or active FULL operation.

## FINAL IMPLEMENTER OBSERVATION

CONTRACT_PROVED: Exact WARN-4C patch and focused tests pass. Architectural GO remains with ChatGPT. STOP after this stage.


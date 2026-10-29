# CONTEXTOR P1D3-WARN-4D — implementer report

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP inspected `ipc.py` first at canonical revision 864; structural DFS back-edge count was 16. Initial HEAD `e9ae2da25facd35e2c864703afabd0b590297f82`. The pre-existing worktree changed only `walkthrough.md` from the missing-patch report. Both requested new paths were absent. All eight supplied SEARCH blocks occurred exactly once in current `ipc.py`.

## HEAD / WORKTREE

DIRECT_EVIDENCE: Final HEAD unchanged. Final worktree changes are the two new Python files, `ipc.py` and this report. No commit, push, restart or active user's FULL/LIVE operation.

## EXACT PATCH APPLICATION

DIRECT_EVIDENCE: Applied all eight literal SEARCH → REPLACE blocks through `apply_patch` and created both new files from the supplied `CREATE EXACT CONTENT` blocks. No alternative implementation or assertion change was made. The earlier named `.patch` file was not used; this task supplied complete replacement text.

## DIRECT PUBLISH RESULTS

CONTRACT_PROVED: The isolated direct publish path captured owner-derived warning reports before and after installation. Tests observed WARNING_REACTIVATED and MODEL_ACCEPTED without removing unchanged structural cycles. A later commit replaced the checkpoint.

## COMMITTED PUBLISH RESULTS

CONTRACT_PROVED: The isolated committed-snapshot publish test installed the next actual stored generation and produced a two-path WARNING_REACTIVATED checkpoint.

## INCREMENTAL UPDATE RESULTS

CONTRACT_PROVED: The isolated update_file commit produced two WARNING_REACTIVATED transitions while retaining cycle topology and clearing the old partial receipt. The existing canonical commit path remained the owner.

## INVALID / STALE GENERATION RESULTS

CONTRACT_PROVED: Stale pre- or post-installation structural inventory returned unavailable without an empty transition claim. Current state drift hid a cached positive checkpoint. Missing checkpoint, extra caller payload and recovery readiness failed closed.

## IPC IDENTITY AND LOCK BOUNDARY

CODE_PATH_PROVED: Owner reports are captured under the existing LIVE state lock at each actual commit boundary. Checkpoint construction checks owner identity and activity epoch. The query accepts only the operation key, checks readiness, compares its stored current report with the currently installed report under the lock, and returns a defensive copy. Caller-supplied projections, receipts, state or source bytes are rejected. The query itself does not append journal events.

## NEW TEST RESULTS

DIRECT_EVIDENCE: `py_compile` on all three changed Python files exited 0. `tests/test_cycle_semantics_live_warning_transition_checkpoint.py`: 13 passed, 0 failed, 0 skipped, 27.22 s, exit 0.

## FOCUSED REGRESSIONS

DIRECT_EVIDENCE: Four requested regression modules: 101 passed, 0 failed, 0 skipped, 88.29 s, exit 0. `git diff --check` and both new-file `git diff --no-index --check` calls exited 0. No global suite.

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_module_context` inspected all three changed files at canonical revision 867; all had `workspace_sync=verified`, live provenance, fresh module/graph/topology/structural cycles and stale cycle_semantics. Structural DFS back-edge count remained 16. IPC gained the intended hard dependency on `live_warning_transition_checkpoint`; the new module imports only existing projection, transition and query modules. No newly counted structural cycle. This is source/workspace evidence, not the user's active process loaded-code adoption.

## FILES_CHANGED

- `contextor/core/live_state/ipc.py`
- `contextor/core/cycle_semantics/live_warning_transition_checkpoint.py` (new)
- `tests/test_cycle_semantics_live_warning_transition_checkpoint.py` (new)

`walkthrough.md` is this report. Complete actual diffs follow.

## FULL_DIFFS


### Modified IPC

```diff
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 596c80d..277ff93 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -860,6 +860,8 @@ class CanonicalLiveServer:
         self._events: list[dict[str, Any]] = []
         self._authority_event_fingerprints: OrderedDict[tuple[str, int, str], str] = OrderedDict()
         self._lock = threading.RLock()
+        self._cycle_warning_transition_checkpoint = None
+        self._cycle_warning_transition_current_report = None
         self._mutation_execution_lock = threading.Lock()
         self._mutation_guard = mutation_guard
         self._recovery_verification_guard = recovery_verification_guard
@@ -905,6 +907,39 @@ class CanonicalLiveServer:
             desktop_instance_id=self._authority_identity.get("desktop_instance_id"),
         )
 
+    def _owner_cycle_warning_report_locked(self) -> dict[str, Any]:
+        """Capture this installed generation under self._lock, not from a caller."""
+        try:
+            from contextor.core.cycle_semantics.live_cycle_warning_query import (
+                read_locked_installed_cycle_warnings,
+            )
+            return read_locked_installed_cycle_warnings(
+                self._state,
+                canonical_revision=self._revision,
+                authority_identity=self._authority_identity,
+                activity_epoch=self._activity_epoch,
+            )
+        except Exception:
+            return {"status": "unavailable", "reason": "WARNING_PROJECTION_FAILURE"}
+
+    def _refresh_cycle_warning_transition_locked(self, before: dict[str, Any]) -> None:
+        """Commit-scoped derived checkpoint; never affect canonical commit success."""
+        after = self._owner_cycle_warning_report_locked()
+        try:
+            from contextor.core.cycle_semantics.live_warning_transition_checkpoint import (
+                build_locked_warning_transition_checkpoint,
+            )
+            result = build_locked_warning_transition_checkpoint(
+                before,
+                after,
+                authority_identity=self._authority_identity,
+                activity_epoch=self._activity_epoch,
+            )
+        except Exception:
+            result = {"status": "unavailable", "reason": "WARNING_TRANSITION_FAILURE"}
+        self._cycle_warning_transition_current_report = after
+        self._cycle_warning_transition_checkpoint = result
+
     def _read_revision(self) -> int:
         with self._lock:
             return self._revision
@@ -1514,6 +1549,7 @@ class CanonicalLiveServer:
                         self._events + [event]
                     )[-self._retention:]
 
+                    before_warning_report = self._owner_cycle_warning_report_locked()
                     _mark_live_state_provenance(committed_state)
 
                     # COMMIT BOUNDARY
@@ -1528,6 +1564,7 @@ class CanonicalLiveServer:
                     self._revision = committed_revision
                     self._events = next_events
                     self._activity_seq = next_seq
+                    self._refresh_cycle_warning_transition_locked(before_warning_report)
 
                     committed_seq = next_seq
                     committed = True
@@ -1646,9 +1683,11 @@ class CanonicalLiveServer:
                         }
                     state_rev = expected_revision
 
+                before_warning_report = self._owner_cycle_warning_report_locked()
                 _mark_live_state_provenance(state)
                 self._state = state
                 self._revision = state_rev
+                self._refresh_cycle_warning_transition_locked(before_warning_report)
                 evt = self._record_event("publish", request, category="LIVE_STATE")
                 _safe_trace_event("LIVE", "CANONICAL_PUBLISH", op=trace_op, rev_before=previous_revision, rev_after=self._revision, seq=evt["seq"], origin=request.get("origin"))
                 return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}
@@ -2213,8 +2252,10 @@ class CanonicalLiveServer:
 
                 # ATOMIC COMMIT BOUNDARY.
                 # Nothing above this line may replace/mutate active canonical ownership.
+                before_warning_report = self._owner_cycle_warning_report_locked()
                 self._state = candidate_state
                 self._revision = expected_revision
+                self._refresh_cycle_warning_transition_locked(before_warning_report)
                 _safe_trace_event("LIVE", "CANONICAL_COMMIT", op=trace_op, path=file_path, rev_before=previous_revision, rev_after=expected_revision)
 
                 try:
@@ -2336,6 +2377,42 @@ class CanonicalLiveServer:
             return self._execute_publish(request)
 
         with self._lock:
+            if operation == "get_installed_cycle_warning_transitions":
+                if set(request) != {"operation"}:
+                    return {
+                        "status": "unavailable",
+                        "reason": "INVALID_WARNING_TRANSITION_PAYLOAD",
+                    }
+                if (
+                    self._stop.is_set()
+                    or self._pending_recovery_certificate is not None
+                    or self._recovery_release_degraded
+                ):
+                    return {"status": "unavailable", "reason": "LIVE_OWNER_NOT_READY"}
+                checkpoint = self._cycle_warning_transition_checkpoint
+                if checkpoint is None:
+                    return {"status": "unavailable", "reason": "NO_COMMITTED_WARNING_TRANSITION"}
+                if (
+                    self._cycle_warning_transition_current_report
+                    != self._owner_cycle_warning_report_locked()
+                ):
+                    return {"status": "unavailable", "reason": "WARNING_TRANSITION_STATE_DRIFT"}
+                if checkpoint.get("status") != "ok":
+                    return copy.deepcopy(checkpoint)
+                if (
+                    checkpoint.get("to_revision") != self._revision
+                    or checkpoint.get("activity_epoch") != self._activity_epoch
+                    or any(
+                        checkpoint.get(key) != self._authority_identity.get(key)
+                        for key in (
+                            "repo_id", "root_path", "service_instance_id",
+                            "process_start_identity",
+                        )
+                    )
+                ):
+                    return {"status": "unavailable", "reason": "WARNING_TRANSITION_IDENTITY_DRIFT"}
+                return copy.deepcopy(checkpoint)
+
             if operation == "get_installed_cycle_warning_projection":
                 if set(request) != {"operation"}:
                     return {
@@ -2832,6 +2909,10 @@ class LiveStateClient:
             ),
         )
 
+    def get_installed_cycle_warning_transitions(self) -> dict[str, Any]:
+        """Read the latest owner-derived LIVE commit warning transition."""
+        return self.request("get_installed_cycle_warning_transitions")
+
     def get_installed_cycle_warning_projection(self) -> dict[str, Any]:
         """Read the current canonical LIVE warning partition under its lock."""
         return self.request("get_installed_cycle_warning_projection")
```

### New checkpoint module

```diff
diff --git a/contextor/core/cycle_semantics/live_warning_transition_checkpoint.py b/contextor/core/cycle_semantics/live_warning_transition_checkpoint.py
new file mode 100644
index 0000000..c372ca2
--- /dev/null
+++ b/contextor/core/cycle_semantics/live_warning_transition_checkpoint.py
@@ -0,0 +1,119 @@
+"""Pure owner-captured cycle warning transition checkpoint.
+
+Both reports must have been obtained from the same LIVE owner, each while
+its corresponding generation was installed under the owner's lock.
+This module never authenticates caller-provided data on its own.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Mapping
+from typing import Any
+
+from .cycle_warning_projection import InstalledCycleWarningProjection
+from .cycle_warning_transitions import diff_installed_cycle_warning_projections
+from .live_cycle_warning_query import _AUTHORITY as _PROJECTION_AUTHORITY
+from .live_cycle_warning_query import _BINDING as _PROJECTION_BINDING
+
+_CHECKPOINT_AUTHORITY = (
+    "LIVE_OWNER_COMMIT_SCOPED_WARNING_TRANSITIONS"
+    "_NOT_STRUCTURAL_REMOVAL_FOR_MODEL_ACCEPTANCE"
+    "_NOT_RUNTIME_SAFETY"
+)
+
+
+def build_locked_warning_transition_checkpoint(
+    before: Any,
+    after: Any,
+    *,
+    authority_identity: Mapping[str, Any],
+    activity_epoch: str,
+) -> dict[str, Any]:
+    """Diff two owner-captured reports; return no transitions on uncertainty."""
+    def unavailable(reason: str) -> dict[str, Any]:
+        return {
+            "status": "unavailable",
+            "reason": reason,
+            "authority": _CHECKPOINT_AUTHORITY,
+        }
+
+    try:
+        if type(activity_epoch) is not str or not activity_epoch:
+            return unavailable("WARNING_TRANSITION_AUTHORITY_UNAVAILABLE")
+        if not isinstance(authority_identity, Mapping):
+            return unavailable("WARNING_TRANSITION_AUTHORITY_UNAVAILABLE")
+        names = ("repo_id", "root_path", "service_instance_id", "process_start_identity")
+        identity = {name: authority_identity.get(name) for name in names}
+        if any(type(value) is not str or not value for value in identity.values()):
+            return unavailable("WARNING_TRANSITION_AUTHORITY_UNAVAILABLE")
+        fields = {
+            "status", "binding_state", "revision", "state_id", "repo_id",
+            "root_path", "service_instance_id", "process_start_identity",
+            "activity_epoch", "graph_sha256", "structural_paths",
+            "model_pass_paths", "active_warning_paths", "structural_count",
+            "model_pass_count", "active_warning_count", "authority",
+        }
+        for report in (before, after):
+            if type(report) is not dict or set(report) != fields:
+                return unavailable("WARNING_TRANSITION_PROJECTION_UNAVAILABLE")
+            if (report["status"] != "ok"
+                    or report["binding_state"] != _PROJECTION_BINDING
+                    or report["authority"] != _PROJECTION_AUTHORITY
+                    or report["activity_epoch"] != activity_epoch):
+                return unavailable("WARNING_TRANSITION_PROJECTION_UNAVAILABLE")
+            if any(report[name] != identity[name] for name in names):
+                return unavailable("WARNING_TRANSITION_IDENTITY_MISMATCH")
+            if (type(report["revision"]) is not int or report["revision"] < 1
+                    or type(report["state_id"]) is not str or not report["state_id"]
+                    or type(report["graph_sha256"]) is not str
+                    or len(report["graph_sha256"]) != 64
+                    or any(c not in "0123456789abcdef" for c in report["graph_sha256"])):
+                return unavailable("WARNING_TRANSITION_PROJECTION_UNAVAILABLE")
+            for count, paths in (
+                ("structural_count", "structural_paths"),
+                ("model_pass_count", "model_pass_paths"),
+                ("active_warning_count", "active_warning_paths"),
+            ):
+                if (type(report[count]) is not int or report[count] < 0
+                        or type(report[paths]) is not tuple
+                        or report[count] != len(report[paths])):
+                    return unavailable("WARNING_TRANSITION_PROJECTION_UNAVAILABLE")
+
+        old_revision, new_revision = before["revision"], after["revision"]
+        if new_revision <= old_revision:
+            return unavailable("WARNING_TRANSITION_REVISION_MISMATCH")
+        before_projection = InstalledCycleWarningProjection(
+            "FRESH", None, old_revision,
+            before["structural_paths"], before["model_pass_paths"],
+            before["active_warning_paths"],
+        )
+        after_projection = InstalledCycleWarningProjection(
+            "FRESH", None, new_revision,
+            after["structural_paths"], after["model_pass_paths"],
+            after["active_warning_paths"],
+        )
+        delta = diff_installed_cycle_warning_projections(
+            before_projection, after_projection,
+        )
+        if (delta.status != "FRESH" or delta.transitions is None
+                or delta.from_revision != old_revision
+                or delta.to_revision != new_revision):
+            return unavailable("WARNING_TRANSITION_PROJECTION_UNAVAILABLE")
+        return {
+            "status": "ok",
+            "binding_state": "INSTALLED_WARNING_TRANSITION_CHECKPOINT",
+            "from_revision": old_revision,
+            "to_revision": new_revision,
+            "activity_epoch": activity_epoch,
+            **identity,
+            "transitions": tuple({
+                "path": transition.path,
+                "action": transition.action,
+                "previous_state": transition.previous_state,
+                "current_state": transition.current_state,
+            } for transition in delta.transitions),
+            "authority": _CHECKPOINT_AUTHORITY,
+        }
+    except (AttributeError, KeyError, TypeError, ValueError, IndexError,
+            RecursionError, OverflowError):
+        return unavailable("WARNING_TRANSITION_PROJECTION_UNAVAILABLE")
```

### New integration test

```diff
diff --git a/tests/test_cycle_semantics_live_warning_transition_checkpoint.py b/tests/test_cycle_semantics_live_warning_transition_checkpoint.py
new file mode 100644
index 0000000..f3a9b37
--- /dev/null
+++ b/tests/test_cycle_semantics_live_warning_transition_checkpoint.py
@@ -0,0 +1,206 @@
+"""WARN-4D: owner-owned warning transitions survive generation installation."""
+
+from __future__ import annotations
+
+import copy
+from contextlib import contextmanager
+from types import SimpleNamespace
+
+import pytest
+
+from tests.test_cycle_semantics_live_installed_partial_claims import (
+    _fixture, _full, _owner, _persisted,
+)
+from tests.test_original_worker_partial_scc_preparation import (
+    PASS_AND_HAZARD, PASS_AND_UNKNOWN, TWO_PASS,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _installed_next(root, server, *, partial=False):
+    _full(root, partial=partial)
+    state, metadata = _persisted(root)
+    assert server._execute_publish({
+        "state": state, "origin": "isolated_test",
+    })["status"] == "ok"
+    return state, metadata
+
+
+def _transition(client):
+    result = client.get_installed_cycle_warning_transitions()
+    assert result["status"] == "ok"
+    assert result["binding_state"] == "INSTALLED_WARNING_TRANSITION_CHECKPOINT"
+    return result
+
+
+def test_t01_t04_two_pass_loses_proof_and_reactivates_both(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, client):
+        assert client.get_installed_cycle_warning_transitions()["status"] == "unavailable"
+        next_state, newer = _installed_next(root, server, partial=False)
+        answer = _transition(client)
+        assert answer["from_revision"] == metadata.revision
+        assert answer["to_revision"] == newer.revision
+        assert answer["activity_epoch"] == server._activity_epoch
+        assert len(answer["transitions"]) == 2
+        assert tuple(item["action"] for item in answer["transitions"]) == (
+            "WARNING_REACTIVATED", "WARNING_REACTIVATED",
+        )
+        assert all(item["previous_state"] == "MODEL_PASS" for item in answer["transitions"])
+        assert all(item["current_state"] == "ACTIVE" for item in answer["transitions"])
+        assert tuple(item["path"] for item in answer["transitions"]) == (
+            ("a", "b", "a"), ("x", "y", "x"),
+        )
+        assert next_state.cycles == state.cycles
+        assert client.get_installed_cycle_warning_transitions() == answer
+
+
+def test_t02_mixed_pass_unknown_only_one_reactivated(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, PASS_AND_UNKNOWN)
+    with _owner(state, metadata) as (server, client):
+        _installed_next(root, server, partial=False)
+        answer = _transition(client)
+        assert tuple(item["path"] for item in answer["transitions"]) == (("a", "b", "a"),)
+        assert answer["transitions"][0]["action"] == "WARNING_REACTIVATED"
+
+
+def test_t03_mixed_pass_hazard_does_not_suppress_hazard(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, PASS_AND_HAZARD)
+    with _owner(state, metadata) as (server, client):
+        _installed_next(root, server, partial=False)
+        answer = _transition(client)
+        assert tuple(item["path"] for item in answer["transitions"]) == (("a", "b", "a"),)
+        assert answer["transitions"][0]["action"] == "WARNING_REACTIVATED"
+
+
+def test_t05_persisted_full_without_receipt_then_partial_accepts(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS, partial=False)
+    with _owner(state, metadata) as (server, client):
+        _installed_next(root, server, partial=True)
+        answer = _transition(client)
+        assert len(answer["transitions"]) == 2
+        assert {item["action"] for item in answer["transitions"]} == {"MODEL_ACCEPTED"}
+
+
+def test_t06_stale_before_is_unavailable_without_zero_transition_claim(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    state.cycles_state = "stale"
+    with _owner(state, metadata) as (server, client):
+        _installed_next(root, server, partial=True)
+        answer = client.get_installed_cycle_warning_transitions()
+        assert answer["status"] == "unavailable"
+        assert "transitions" not in answer
+
+
+def test_t07_stale_after_is_unavailable(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, client):
+        _full(root, partial=False)
+        newer, _ = _persisted(root)
+        newer.cycles_state = "stale"
+        assert server._execute_publish({"state": newer, "origin": "isolated_test"})["status"] == "ok"
+        answer = client.get_installed_cycle_warning_transitions()
+        assert answer["status"] == "unavailable"
+        assert "transitions" not in answer
+
+
+def test_t08_query_read_only_does_not_emit_events(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, client):
+        _installed_next(root, server, partial=False)
+        before = copy.deepcopy((server._events, server._activity_seq, server._activity_epoch))
+        _transition(client)
+        _transition(client)
+        assert (server._events, server._activity_seq, server._activity_epoch) == before
+
+
+def test_t09_newer_commit_replaces_previous_checkpoint(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, client):
+        _, first = _installed_next(root, server, partial=False)
+        assert len(_transition(client)["transitions"]) == 2
+        _, second = _installed_next(root, server, partial=False)
+        answer = _transition(client)
+        assert answer["from_revision"] == first.revision
+        assert answer["to_revision"] == second.revision
+        assert answer["transitions"] == ()
+
+
+def test_t10_current_state_drift_hides_cached_positive(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, client):
+        newest, _ = _installed_next(root, server, partial=False)
+        assert _transition(client)["status"] == "ok"
+        newest.cycles_state = "stale"
+        answer = client.get_installed_cycle_warning_transitions()
+        assert answer["status"] == "unavailable"
+        assert "transitions" not in answer
+
+
+def test_t11_no_caller_payload_allowed(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, client):
+        for extra in ("state", "receipt", "previous_projection", "expected_revision"):
+            answer = client.request("get_installed_cycle_warning_transitions", **{extra: "bad"})
+            assert answer["reason"] == "INVALID_WARNING_TRANSITION_PAYLOAD"
+
+
+def test_t12_recovery_blocks_transition_query(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, client):
+        _installed_next(root, server, partial=False)
+        try:
+            server._recovery_release_degraded = True
+            answer = client.get_installed_cycle_warning_transitions()
+            assert answer["reason"] == "LIVE_OWNER_NOT_READY"
+        finally:
+            server._recovery_release_degraded = False
+
+
+def test_t13_committed_snapshot_publish_uses_same_checkpoint(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, client):
+        _full(root, partial=False)
+        newer, new_meta = _persisted(root)
+        @contextmanager
+        def _reader():
+            yield newer, new_meta
+        server._committed_snapshot_reader = _reader
+        response = server._execute_publish({
+            "state": SimpleNamespace(revision=new_meta.revision, state_id=new_meta.state_id),
+            "origin": "isolated_test",
+        })
+        assert response["status"] == "ok"
+        answer = _transition(client)
+        assert answer["from_revision"] == metadata.revision
+        assert answer["to_revision"] == new_meta.revision
+        assert len(answer["transitions"]) == 2
+        assert all(item["action"] == "WARNING_REACTIVATED" for item in answer["transitions"])
+
+
+def test_t14_incremental_commit_reactivates_without_topology_change(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, client):
+        before_cycles = copy.deepcopy(state.cycles)
+        server._updater = lambda candidate, path: SimpleNamespace(
+            status="ok", file_path=path, affected_modules=(),
+        )
+        result = server._execute_update_file({
+            "operation": "update_file", "file_path": str(root / "a.py"),
+            "origin": "isolated_test",
+        })
+        assert result["status"] == "ok"
+        answer = _transition(client)
+        assert answer["from_revision"] == metadata.revision
+        assert answer["to_revision"] == metadata.revision + 1
+        assert tuple(item["action"] for item in answer["transitions"]) == (
+            "WARNING_REACTIVATED", "WARNING_REACTIVATED",
+        )
+        assert server._state.cycles == before_cycles
+        assert server._state.cycle_partial_source_publication is None
```

## CONTRACT_CONFLICTS

NONE observed.

## REMAINING UNKNOWN

UNKNOWN: The user's active LIVE process loaded-code adoption, active service generation and Desktop/MCP/get_live_events consumer behavior. No consumer schema or protocol version changed.

## FINAL IMPLEMENTER OBSERVATION

CONTRACT_PROVED: Literal WARN-4D search/replace implementation and focused regressions pass. Architectural GO remains with ChatGPT. STOP after this stage.


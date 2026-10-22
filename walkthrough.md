# CONTEXTOR_CYCLE_PROOF_P1C2_LIVE_PUBLICATION_INTEGRATION

## TASK
Apply the exact auditor-supplied test-only P1C2 integration patch. No production or existing-test edits. The tests use isolated temporary snapshot directories and in-process CanonicalLiveServer objects.

## HEAD_BEFORE
c2d5ca0146aebc429a4fa8aed7545aa216dba24f. Clean tracked and untracked source tree before task; approved new file absent.

## HEAD_AFTER
c2d5ca0146aebc429a4fa8aed7545aa216dba24f. No commit created.

## FILES_CHANGED
- tests/test_cycle_semantics_publication_live_integration.py (new)

## T01_T08_RESULTS
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_publication_live_integration.py
Actual: 8 passed in 3.12s, exit 0.
- T01 PASS: isolated real FULL has fresh structural/semantic diagnostics but no invented co-publication receipt.
- T02 PASS: committed store generation, rather than caller state, installs in the in-process LIVE server.
- T03 PASS: incremental candidate and committed revision 2 lose prior receipt; prior revision 1 object retains it.
- T04 PASS: failed incremental persistence leaves server and store at prior revision 1.
- T05 PASS: second in-process server reads verified committed generation after first closes.
- T06 PASS: tampered durable receipt is rejected before LIVE installation.
- T07 PASS: failed store commit cannot publish candidate revision 2.
- T08 PASS: idempotent acknowledgement does not reseal evidence or advance activity sequence.

## FOCUSED_NON_REGRESSION
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_publication_binding.py tests/test_cycle_semantics_canonical_state.py tests/test_cycle_semantics_invalidation.py tests/test_cycle_semantics_full_integration.py
Actual: 64 passed in 23.19s, exit 0. No full repository suite run.
py_compile of new test: PASS.
git -c core.autocrlf=false diff --no-index --check -- /dev/null tests/test_cycle_semantics_publication_live_integration.py: no whitespace diagnostics. The no-index diff command returns difference status for a new file; no error text was emitted.

## FULL_PUBLICATION_GAP
T01 directly verifies that current FULL does not supply an authenticated prepared manifest to the canonical writer and does not mint a P1C0/P1C1 receipt. Its semantic snapshot binding remains NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY. This test makes no runtime SAFE, source-origin, or warning-suppression claim.

## COMMITTED_LIVE_INSTALL
T02 verifies the server returns source=committed_snapshot and installs a state object distinct from the caller. The installed receipt matches committed revision and state ID. Contextor pre-edit resolved CanonicalLiveServer, save_snapshot, load_snapshot, locked_committed_snapshot, RepositoryAnalysisState.clone_for_update, prepare_cycle_source_manifest, and ContextorFacade.analyze_project; relevant implementations and consumers matched supplied test entry points. Contextor store blast radius reported 47 artifacts and 43 direct static consumers; IPC reported 103 artifacts and 25 direct static consumers at revision 646.

## INCREMENTAL_INVALIDATION
T03 verifies the updater sees a candidate with no inherited receipt, that revision 2 persists without one, and that the prior revision 1 state retains its receipt.

## ROLLBACK_AND_RESTART
T04 verifies failed persistence leaves prior LIVE and durable generation intact. T05 verifies a new in-process server can restore the committed receipt. This is not a certification of the user's running service after manual restart.

## TAMPER_AND_IDEMPOTENCY
T06 verifies altered receipt revision fails closed on load and is absent from installed LIVE state. T07 verifies rejected store commit cannot cross the committed publish boundary. T08 verifies idempotent acknowledgement preserves the same state and receipt without a new activity sequence.

## LIVE_REVISION_BEFORE_AFTER
Before edit: 646. After watcher update: 647.

## WATCHER_EVENTS
Contextor get_live_events(after_revision=646) returned one canonical event: revision 647, operation=update_file, origin=desktop_watcher, status=UPDATED, file_path=tests/test_cycle_semantics_publication_live_integration.py, blast_radius_state=fresh, affected_modules.total=1. continuity=continuous, resync_required=false. No manual update_file call.

## WORKSPACE_SYNC
Contextor get_module_context for the new test at revision 647: canonical_state=fresh, workspace_sync=verified, advisory_warning=null. Post-edit get_module_blast_radius resolved 12 artifacts and zero direct static consumers. Cycle_semantics family remains stale; no safety conclusion follows from watcher freshness.

## RESTART_REQUIREMENTS
No source or runtime module changed. No restart required for this test-only addition. No Desktop, MCP, or LIVE process was restarted. Loaded-code/runtime certification was not part of these isolated tests.

## FULL_DIFFS
Complete actual unified diff of the sole new file:
diff --git a/tests/test_cycle_semantics_publication_live_integration.py b/tests/test_cycle_semantics_publication_live_integration.py
new file mode 100644
index 0000000..8040ba5
--- /dev/null
+++ b/tests/test_cycle_semantics_publication_live_integration.py
@@ -0,0 +1,401 @@
+"""P1C2 in-process canonical publication integration gates.
+
+Tests real durable snapshot and CanonicalLiveServer code paths.
+No connection to the user's running MCP/LIVE service.
+No source-origin authentication or runtime import safety.
+"""
+
+from __future__ import annotations
+
+import pickle
+from contextlib import contextmanager
+from dataclasses import replace
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.cycle_semantics.publication_binding import (
+    CanonicalCycleManifestReceipt,
+    verify_co_published_cycle_manifest,
+)
+from contextor.core.live_state.ipc import CanonicalLiveServer
+from contextor.core.live_state.store import (
+    load_snapshot,
+    locked_committed_snapshot,
+    read_metadata,
+)
+from tests.test_cycle_semantics_full_integration import _run_full
+from tests.test_cycle_semantics_publication_binding import (
+    _case,
+    _save,
+)
+
+
+pytestmark = pytest.mark.live
+
+
+@contextmanager
+def _server(
+    cache_dir,
+    *,
+    state=None,
+    revision=0,
+    updater=None,
+    persister=None,
+):
+    """Use the real server against an isolated committed store."""
+    server = CanonicalLiveServer(
+        state,
+        revision=revision,
+        updater=updater,
+        persister=persister,
+        committed_snapshot_reader=lambda: locked_committed_snapshot(
+            cache_dir,
+            expected_repo_id="",
+            expected_root_path="",
+        ),
+    )
+    try:
+        yield server
+    finally:
+        server.close()
+
+
+def _publish(server, candidate, *, acknowledge=False):
+    return server._dispatch({
+        "operation": "publish",
+        "state": candidate,
+        "origin": "p1c2_integration",
+        "acknowledge_installed": acknowledge,
+    })
+
+
+def _assert_receipt(state, metadata):
+    receipt = state.cycle_source_publication
+    assert isinstance(receipt, CanonicalCycleManifestReceipt)
+    assert receipt.revision == metadata.revision
+    assert receipt.state_id == metadata.state_id
+    assert verify_co_published_cycle_manifest(
+        state,
+        revision=metadata.revision,
+        state_id=metadata.state_id,
+        repo_id=metadata.repo_id,
+        root_path=metadata.root_path,
+    )
+    return receipt
+
+
+def test_p1c2_t01_real_full_does_not_invent_receipt(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    """Current FULL has no authenticated prepared-manifest input."""
+    monkeypatch.setenv(
+        "CONTEXTOR_DISABLE_PROCESS_POOL", "1"
+    )
+
+    root = tmp_path / "repo"
+    package = root / "pkg"
+    package.mkdir(parents=True)
+    (package / "__init__.py").write_text(
+        "", encoding="utf-8"
+    )
+    (package / "a.py").write_text(
+        "import pkg.b\ndef fa():\n    return 1\n",
+        encoding="utf-8",
+    )
+    (package / "b.py").write_text(
+        "import pkg.a\ndef fb():\n    return 2\n",
+        encoding="utf-8",
+    )
+
+    state, _result = _run_full(root)
+
+    assert state.cycle_semantics_state == "fresh"
+    assert state.cycles_state == "fresh"
+    assert state.cycles
+    assert state.cycle_semantics is not None
+    assert state.cycle_semantics.source_snapshot_binding == (
+        "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
+    )
+
+    # FULL does not supply P1C0 to the canonical writer yet.
+    assert state.cycle_source_publication is None
+
+
+def test_p1c2_t02_committed_store_to_live_install(tmp_path):
+    state, prepared = _case()
+    metadata = _save(state, tmp_path, 1, prepared)
+
+    assert state.cycle_source_publication is None
+
+    with _server(tmp_path) as server:
+        answer = _publish(server, state)
+
+        assert answer["status"] == "ok"
+        assert answer["revision"] == 1
+        assert answer["source"] == "committed_snapshot"
+
+        active = server._dispatch({
+            "operation": "snapshot",
+        })
+        assert active["status"] == "ok"
+        assert active["revision"] == 1
+        assert active["state"] is not state
+
+        receipt = _assert_receipt(
+            active["state"], metadata,
+        )
+        assert receipt.prepared_manifest == prepared
+
+        assert server._events[-1]["operation"] == "publish"
+        assert server._events[-1]["revision"] == 1
+
+
+def test_p1c2_t03_incremental_commit_invalidates_receipt(
+    tmp_path,
+):
+    state, prepared = _case()
+    _save(state, tmp_path, 1, prepared)
+
+    observed = []
+
+    def updater(candidate, path):
+        observed.append(candidate.cycle_source_publication)
+        candidate.cycle_semantics_state = "stale"
+        candidate.cycle_semantics_invalidation_reason = (
+            "SOURCE_CHANGED"
+        )
+        return SimpleNamespace(
+            status="UPDATED",
+            file_path=path,
+        )
+
+    def persister(candidate, revision):
+        assert candidate.cycle_source_publication is None
+        _save(candidate, tmp_path, revision)
+
+    with _server(
+        tmp_path,
+        updater=updater,
+        persister=persister,
+    ) as server:
+        assert _publish(server, state)["status"] == "ok"
+
+        previous = server._state
+        assert previous.cycle_source_publication is not None
+
+        changed = server._dispatch({
+            "operation": "update_file",
+            "file_path": "a.py",
+            "origin": "desktop_watcher",
+        })
+
+        assert changed["status"] == "ok"
+        assert changed["revision"] == 2
+        assert observed == [None]
+
+        current = server._state
+        assert current is not previous
+        assert current.revision == 2
+        assert current.cycle_source_publication is None
+        assert current.cycle_semantics_state == "stale"
+
+        # COW must preserve the previous object.
+        assert previous.revision == 1
+        assert previous.cycle_source_publication is not None
+
+    restored, metadata = load_snapshot(
+        tmp_path, "cycle-state",
+    )
+    assert metadata.revision == 2
+    assert restored.cycle_source_publication is None
+
+
+def test_p1c2_t04_failed_incremental_persistence_rolls_back(
+    tmp_path,
+):
+    state, prepared = _case()
+    metadata = _save(state, tmp_path, 1, prepared)
+
+    def updater(candidate, path):
+        candidate.cycle_semantics_state = "stale"
+        return SimpleNamespace(
+            status="UPDATED",
+            file_path=path,
+        )
+
+    def rejected_persistence(_candidate, _revision):
+        raise RuntimeError("synthetic persistence failure")
+
+    with _server(
+        tmp_path,
+        updater=updater,
+        persister=rejected_persistence,
+    ) as server:
+        assert _publish(server, state)["status"] == "ok"
+
+        original = server._state
+        original_receipt = _assert_receipt(
+            original, metadata,
+        )
+        original_event_count = len(server._events)
+
+        failed = server._dispatch({
+            "operation": "update_file",
+            "file_path": "a.py",
+            "origin": "desktop_watcher",
+        })
+
+        assert failed["status"] == "error"
+        assert failed["error"] == (
+            "canonical_persistence_failed"
+        )
+        assert failed["revision"] == 1
+        assert server._revision == 1
+        assert server._state is original
+        assert server._state.cycle_source_publication == (
+            original_receipt
+        )
+        assert len(server._events) == original_event_count
+
+    restored, restored_metadata = load_snapshot(
+        tmp_path, "cycle-state",
+    )
+    assert restored_metadata.revision == 1
+    _assert_receipt(restored, restored_metadata)
+
+
+def test_p1c2_t05_restart_from_committed_generation(
+    tmp_path,
+):
+    state, prepared = _case()
+    _save(state, tmp_path, 1, prepared)
+
+    with _server(tmp_path) as first:
+        assert _publish(first, state)["status"] == "ok"
+        first_receipt = first._state.cycle_source_publication
+        assert first_receipt is not None
+
+    recovered, metadata = load_snapshot(
+        tmp_path, "cycle-state",
+    )
+    _assert_receipt(recovered, metadata)
+
+    with _server(
+        tmp_path,
+        state=recovered,
+        revision=metadata.revision,
+    ) as second:
+        snapshot = second._dispatch({
+            "operation": "snapshot",
+        })
+
+        assert snapshot["status"] == "ok"
+        assert snapshot["revision"] == 1
+        assert snapshot["state"].cycle_source_publication == (
+            first_receipt
+        )
+        _assert_receipt(snapshot["state"], metadata)
+
+
+def test_p1c2_t06_tampered_durable_receipt_is_not_installed(
+    tmp_path,
+):
+    state, prepared = _case()
+    metadata = _save(state, tmp_path, 1, prepared)
+
+    payload_path = tmp_path / metadata.state_file
+    payload = pickle.loads(payload_path.read_bytes())
+
+    receipt = payload["state"].cycle_source_publication
+    assert receipt is not None
+
+    payload["state"].cycle_source_publication = replace(
+        receipt,
+        revision=999,
+    )
+    payload_path.write_bytes(pickle.dumps(payload))
+
+    recovered, recovered_metadata = load_snapshot(
+        tmp_path, "cycle-state",
+    )
+    assert recovered_metadata.revision == 1
+    assert recovered.cycle_source_publication is None
+
+    with _server(tmp_path) as server:
+        answer = _publish(server, state)
+
+        assert answer["status"] == "ok"
+        assert answer["revision"] == 1
+        assert server._state.cycle_source_publication is None
+
+        # The server may install valid structural state.
+        # It must not resurrect a rejected semantic receipt.
+        assert server._state.cycle_semantics is not None
+
+
+def test_p1c2_t07_failed_store_commit_cannot_publish_claim(
+    tmp_path,
+):
+    state, prepared = _case()
+    _save(state, tmp_path, 1, prepared)
+
+    with _server(tmp_path) as server:
+        assert _publish(server, state)["status"] == "ok"
+        previous = server._state
+        previous_receipt = previous.cycle_source_publication
+
+        forged = replace(
+            prepared,
+            source_manifest_sha256="f" * 64,
+        )
+
+        with pytest.raises(ValueError):
+            _save(state, tmp_path, 2, forged)
+
+        assert read_metadata(tmp_path).revision == 1
+
+        # Candidate is now revision 2, but the durable
+        # authoritative generation remains revision 1.
+        refused = _publish(server, state)
+
+        assert refused["status"] == "error"
+        assert refused["error"] == (
+            "committed_publish_generation_mismatch"
+        )
+        assert server._revision == 1
+        assert server._state is previous
+        assert server._state.cycle_source_publication == (
+            previous_receipt
+        )
+
+
+def test_p1c2_t08_idempotent_publish_does_not_reseal(
+    tmp_path,
+):
+    state, prepared = _case()
+    metadata = _save(state, tmp_path, 1, prepared)
+
+    with _server(tmp_path) as server:
+        assert _publish(server, state)["status"] == "ok"
+
+        previous = server._state
+        previous_receipt = _assert_receipt(
+            previous, metadata,
+        )
+        previous_seq = server._activity_seq
+
+        repeated = _publish(
+            server,
+            state,
+            acknowledge=True,
+        )
+
+        assert repeated["status"] == "ok"
+        assert repeated["already_installed"] is True
+        assert repeated["revision"] == 1
+        assert server._state is previous
+        assert server._activity_seq == previous_seq
+        assert server._state.cycle_source_publication == (
+            previous_receipt
+        )

## FINAL_VERDICT
PASS for the exact test-only P1C2 acceptance and focused gates. Existing FULL co-publication gap remains explicitly demonstrated.

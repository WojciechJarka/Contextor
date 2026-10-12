# CONTEXTOR_B0G2D_REAL_WATCHER_MCP_INCREMENTAL_PARITY

## FILES_CHANGED

- C:\Temp\Contextor_Repo\tests\test_desktop_mcp_live_incremental_parity.py — new test file (current task).
- C:\Temp\Contextor_Repo\walkthrough.md — current report.

No production code, existing tests, fixture source outside pytest, or real LIVE service was edited. The complete actual diff of the new test is appended below.

## SOURCE_AND_LIVE_PRECHECK

DIRECT_EVIDENCE: Contextor MCP was used first, including deferred tool discovery and current documentation. Complete relevant symbol implementations returned workspace_sync=verified for DesktopLiveWatcher.__init__, _enqueue_path, CanonicalLiveServer.__init__/serve_forever/close, LiveStateClient.update_file/submit_update_file/mutation_status, _repository_updater, _repository_persister, public MCP update_file, and get_or_init_engine. Contiguous current source showed DesktopLiveWatcher.poll_once and CanonicalLiveServer._execute_update_file. Production routing matches the requested source contract: watcher submits async mutation; public MCP calls synchronous LIVE update; server commits via the same updater/persister. This was source precheck, not a completed transport execution.

At precheck HEAD=82fba2eb4daf4d19b5e179ec1e544ad2eef1e0f3; worktree status was clean. Real Contextor LIVE revision=358, continuity=continuous, resync_required=false. Approved test file was absent before this task.

## REAL_FULL_BASELINES

The first actual run invoked run_full_analysis_exclusive(root, owner="desktop_analysis"), which called the real ContextorFacade.analyze_project for the exact required four-file isolated fixture. It persisted a valid schema-1.4 Desktop generation at revision 1, state_id 20261012_124653, repo_id ctx_123b21da. Read-only postfailure load found all four modules, consumer hard edge to pkg.__init__, soft edge to pkg.child, and a trusted four-file FileState generation. The test stopped before its _capture_snapshot call because _full_capture asserted an empty list of validation errors.

FIRST FAILURE (unaltered test output):

    FAILED tests/test_desktop_mcp_live_incremental_parity.py::test_real_desktop_watcher_and_public_mcp_incremental_match_fresh_full
    tests/test_desktop_mcp_live_incremental_parity.py:237: baseline = _full_capture(...)
    tests/test_desktop_mcp_live_incremental_parity.py:56: assert not errors
    E assert not [ValidationError(kind='NAME_COLLISION',
      message="Semantic API collision for variable 'VALUE' across modules:
      consumer, pkg.child, unrelated", ...)]

DIRECT_EVIDENCE from the persisted state: collisions_state="fresh", collision_count=1; nodes ['consumer','pkg.child','unrelated']; code snippets consumer='VALUE = child.VALUE', pkg.child='VALUE = 1', unrelated='VALUE = 2'; artifact_type='variable', is_identical=False. The fixture's exact required source produces this validation result. The failed assertion is a harness assumption, not proof of an analysis or persistence failure. No patch to this assertion or fixture was made after the failure.

Preserved full baseline generation:
C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-554\test_real_desktop_watcher_and_0\cache\repositories\ctx_123b21da\engine_state.r1.30c307f71e9c4e5bb70d0caff48b43d3.pkl
Corresponding metadata points to file_state.r1.30c307f71e9c4e5bb70d0caff48b43d3.json and lineage_manifest.r1.30c307f71e9c4e5bb70d0caff48b43d3.json in that same isolated cache directory. All three files existed at read-only postfailure inspection. The isolated fixture root remains at C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-554\test_real_desktop_watcher_and_0\b0g2d_repo. No second baseline was run.

## ISOLATED_LIVE_SERVER_SETUP

NOT REACHED. The baseline assertion failed before CanonicalLiveServer construction. No in-process LIVE listener, service thread, mutation worker, watcher observer, Desktop process, or production RuntimeLeaseManager service was started by this test.

## DESKTOP_WATCHER_TRANSPORT_PROOF

NOT REACHED. Current source proves the route through submit_update_file and mutation_status, but this test produced no observed Desktop mutation.

## DESKTOP_COMMITTED_REVISION

NOT REACHED. Only the initial FULL baseline revision 1 was persisted.

## DESKTOP_INCREMENTAL_CANONICAL_STATE

NOT CAPTURED.

## FRESH_FULL_ORACLE_A

NOT RUN.

## MCP_PUBLIC_UPDATE_TRANSPORT_PROOF

NOT REACHED. Public MCP update_file handler was not invoked.

## MCP_COMMITTED_REVISION

NOT REACHED.

## MCP_ENGINE_REFRESH

NOT REACHED.

## MCP_INCREMENTAL_CANONICAL_STATE

NOT CAPTURED.

## FRESH_FULL_ORACLE_B

NOT RUN.

## FOUR_WAY_CANONICAL_COMPARISON

NOT RUN. The test's full 36-field B0G2C3 projection comparison remains in the new file; no four-way result can be claimed.

## FIRST_MISMATCH_IF_ANY

No canonical comparison occurred. The first failure is the exact initial validation assertion at new test line 56 for the required VALUE collision, shown above.

## CONSUMER_EDGE_PROPAGATION

Initial FULL graph only: consumer hard_edges={'pkg.__init__'}, soft_edges={'pkg.child'} (DIRECT_EVIDENCE from preserved snapshot). Propagation after editing pkg/__init__.py was not executed.

## REEXPORT_AND_CONSUMPTION_PROPAGATION

UNKNOWN; no incremental or oracle state captured.

## LINEAGE_AND_REFERENCE_PARITY

UNKNOWN; no incremental or oracle state captured.

## ANALYTICS_AND_CYCLES_PARITY

UNKNOWN; no incremental or oracle state captured.

## FRESHNESS_AND_COMPLETENESS_PARITY

UNKNOWN for incremental phases. Initial persisted snapshot loaded successfully with collisions_state=fresh and a trusted FileState baseline. No resync was initiated.

## PERSISTENCE_AND_FILESTATE_LINKAGE

For the initial FULL generation only: metadata revision=1, writer=desktop, state_id=20261012_124653; loaded state revision/state_id match metadata; FileStateManager baseline_status=trusted, revision=1, state_id=20261012_124653, four entries. Versioned engine/FileState/lineage manifest files exist. No LIVE commit or incremental generation exists for this run.

## ISOLATION_AND_THREAD_CLEANUP

The run used isolated_dirs and a temporary repository. It stopped before the isolated LIVE server context manager, so there was no service/mutation/watcher thread to clean up. Test finally cleared only the temporary root's MCP engine cache entries. There was no production endpoint creation or restart.

## TARGETED_TEST_RESULTS

First and only execution: .venv\Scripts\python.exe -m pytest -q -s tests/test_desktop_mcp_live_incremental_parity.py — 1 failed, 1 unrelated Authlib deprecation warning, in 5.76 s. No other targeted regressions were run after the fail gate. No full repository pytest.

## PY_COMPILE

PASS: .venv\Scripts\python.exe -m py_compile C:\Temp\Contextor_Repo\tests\test_desktop_mcp_live_incremental_parity.py.

## GIT_DIFF_CHECK

PASS: git diff --check reported no whitespace errors for tracked changes. The new file is untracked, so git diff --no-index --check -- /dev/null tests/test_desktop_mcp_live_incremental_parity.py was also run: no whitespace diagnostics (its exit code 1 denotes that the new file differs from /dev/null). Git emitted only an LF/CRLF warning. Its complete /dev/null diff follows.

## LIVE_REVISION_BEFORE_AFTER

Real Contextor_Repo LIVE: 358 before; 359 after the new test source was created. Contextor get_live_events(after_revision=358) returned one continuous desktop_watcher UPDATED event for C:\Temp\Contextor_Repo\tests\test_desktop_mcp_live_incremental_parity.py, revision 359. The pytest fixture full analysis targeted only the isolated temporary repository.

## WORKSPACE_SYNC_POSTCHECK

Contextor get_symbol_implementation fetched the new test function at canonical revision 359 with workspace_sync=verified and implementation_is_complete=true. This is source indexing evidence, not proof that separately running processes reimported code.

## RESYNC_REQUIRED

false in the real Contextor_Repo LIVE event response; continuity=continuous. No isolated LIVE mutation was reached.

## RESTART_REQUIRED

No restart is needed for this test-only change. No restart was performed.

## FINAL_VERDICT

B0G2D_HARNESS_BLOCKED. The exact auditor-specified fixture produces a real NAME_COLLISION validation result; the new harness rejects any validation result before it can capture the otherwise persisted FULL baseline or exercise watcher/MCP IPC. No production semantic difference or transport mismatch has been proved. Per the explicit fail gate, no comparator, fixture, or assertion was changed after this failure. STOP; await "proceduj".

## FULL_DIFFS

Full actual diff for C:\Temp\Contextor_Repo\tests\test_desktop_mcp_live_incremental_parity.py:

```diff
diff --git a/tests/test_desktop_mcp_live_incremental_parity.py b/tests/test_desktop_mcp_live_incremental_parity.py
new file mode 100644
index 0000000..81a8731
--- /dev/null
+++ b/tests/test_desktop_mcp_live_incremental_parity.py
@@ -0,0 +1,377 @@
+"""Real watcher and public MCP incremental updates against fresh FULL analysis."""
+
+from __future__ import annotations
+
+import copy
+import hashlib
+import json
+import pickle
+import threading
+import time
+from contextlib import contextmanager
+from pathlib import Path
+
+import pytest
+
+import test_desktop_mcp_canonical_parity as full_parity
+from contextor import mcp_server
+from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
+from contextor.core.analysis.state_manager import FileStateManager
+from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
+from contextor.core.live_state.runtime import (
+    _read_endpoint,
+    _repository_persister,
+    _repository_updater,
+)
+from contextor.core.live_state.store import read_metadata
+from contextor.core.live_state.watcher import DesktopLiveWatcher
+from contextor.core.paths import repo_cache_dir
+from contextor.core.repository_identity import ensure_repository_identity
+from contextor.mcp import runtime as mcp_runtime
+
+
+_INITIAL = {
+    "pkg/__init__.py": b"",
+    "pkg/child.py": b"VALUE = 1\n",
+    "consumer.py": b"from pkg import child\nVALUE = child.VALUE\n",
+    "unrelated.py": b"VALUE = 2\n",
+}
+_CHANGED_INIT = b"child = 123\n"
+
+
+def _source_bytes(root: Path) -> dict[str, bytes]:
+    return {relative: (root / relative).read_bytes() for relative in _INITIAL}
+
+
+def _assert_no_production_endpoint(root: Path) -> None:
+    assert _read_endpoint(root, strict=True) is None
+
+
+def _full_capture(root: Path, repo_id: str, expected_sources: dict[str, bytes]):
+    _assert_no_production_endpoint(root)
+    errors, analysis_result = run_full_analysis_exclusive(
+        root,
+        owner="desktop_analysis",
+    )
+    assert not errors
+    assert analysis_result is not None
+    assert _source_bytes(root) == expected_sources
+    _assert_no_production_endpoint(root)
+    return full_parity._capture_snapshot(
+        root,
+        expected_writer="desktop",
+        expected_repo_id=repo_id,
+        source_bytes=expected_sources,
+    )
+
+
+@contextmanager
+def _isolated_live_server(root: Path, baseline):
+    _assert_no_production_endpoint(root)
+    state = copy.deepcopy(baseline.state)
+    holder: dict[str, object] = {}
+    server = CanonicalLiveServer(
+        state,
+        revision=baseline.metadata.revision,
+        updater=_repository_updater(root, holder),
+        persister=_repository_persister(
+            root,
+            holder,
+            previous_state=state,
+        ),
+    )
+    service = threading.Thread(
+        target=server.serve_forever,
+        name="b0g2d-isolated-live-service",
+        daemon=True,
+    )
+    service.start()
+    client = LiveStateClient(server.endpoint)
+    try:
+        assert client.ping()["revision"] == baseline.metadata.revision
+        _assert_no_production_endpoint(root)
+        yield server, client
+    finally:
+        closed = server.close()
+        service.join(timeout=5.0)
+        assert closed, "isolated LIVE server failed to close"
+        assert not service.is_alive(), "isolated LIVE service thread leaked"
+        worker = server._mutation_coordinator._thread
+        assert worker is None or not worker.is_alive(), "mutation worker leaked"
+        _assert_no_production_endpoint(root)
+
+
+def _preserve_failure(tmp_path: Path, captures: dict[str, object]) -> Path:
+    evidence = tmp_path / "b0g2d_canonical_mismatch_evidence"
+    evidence.mkdir(exist_ok=True)
+    for label, capture in captures.items():
+        with (evidence / f"{label}.pickle").open("wb") as output:
+            pickle.dump(
+                {
+                    "state": capture.state,
+                    "metadata": capture.metadata,
+                    "file_states": capture.file_states,
+                    "file_state_payload": capture.file_state_payload,
+                    "source_bytes": capture.source_bytes,
+                },
+                output,
+                protocol=pickle.HIGHEST_PROTOCOL,
+            )
+    return evidence
+
+
+def _assert_equal_state(
+    left,
+    right,
+    *,
+    label: str,
+    tmp_path: Path,
+    captures: dict[str, object],
+) -> None:
+    left_projection = full_parity._state_projection(
+        left.state, normalize_report_timestamps=True
+    )
+    right_projection = full_parity._state_projection(
+        right.state, normalize_report_timestamps=True
+    )
+    difference = full_parity._first_difference(left_projection, right_projection)
+    if difference is not None:
+        path, left_value, right_value = difference
+        evidence = _preserve_failure(tmp_path, captures)
+        pytest.fail(
+            f"{label} canonical mismatch: first_field={path}; "
+            f"left={full_parity._short_repr(left_value)}; "
+            f"right={full_parity._short_repr(right_value)}; "
+            f"evidence={evidence}",
+            pytrace=False,
+        )
+
+
+def _assert_file_states(
+    left,
+    right,
+    *,
+    label: str,
+    tmp_path: Path,
+    captures: dict[str, object],
+) -> None:
+    left_projection = full_parity._project(left.file_states, "FileStateManager._state")
+    right_projection = full_parity._project(right.file_states, "FileStateManager._state")
+    difference = full_parity._first_difference(
+        left_projection, right_projection, "FileStateManager._state"
+    )
+    if difference is not None:
+        path, left_value, right_value = difference
+        evidence = _preserve_failure(tmp_path, captures)
+        pytest.fail(
+            f"{label} FileState mismatch: first_field={path}; "
+            f"left={full_parity._short_repr(left_value)}; "
+            f"right={full_parity._short_repr(right_value)}; "
+            f"evidence={evidence}",
+            pytrace=False,
+        )
+
+
+def _assert_generation(root: Path, capture, live_snapshot: dict) -> None:
+    metadata = read_metadata(repo_cache_dir(root))
+    assert metadata == capture.metadata
+    assert live_snapshot["status"] == "ok"
+    assert live_snapshot["revision"] == metadata.revision
+    assert live_snapshot["state"].revision == metadata.revision
+    assert live_snapshot["state"].state_id == metadata.state_id
+    assert getattr(live_snapshot["state"], "resync_required", False) is not True
+    assert capture.file_state_payload["_meta"] == {
+        "state_id": metadata.state_id,
+        "revision": metadata.revision,
+    }
+    manager = FileStateManager(str(repo_cache_dir(root)))
+    assert manager.baseline_status == "trusted"
+    assert manager.revision == metadata.revision
+    assert manager.state_id == metadata.state_id
+    assert full_parity._state_projection(live_snapshot["state"]) == (
+        full_parity._state_projection(capture.state)
+    )
+    for relative, content in capture.source_bytes.items():
+        recorded = capture.file_states[str((root / relative).resolve())]
+        assert recorded.sha256 == hashlib.sha256(content).hexdigest()
+
+
+def _assert_consumer_edges(state, *, changed: bool) -> None:
+    graph = state.dependency_graph
+    assert graph.hard_edges["consumer"] == {"pkg.__init__"}
+    assert graph.soft_edges["consumer"] == (set() if changed else {"pkg.child"})
+    assert graph.hard_edges["unrelated"] == set()
+    assert graph.soft_edges["unrelated"] == set()
+
+
+def _clear_isolated_mcp_cache(root: Path) -> None:
+    with mcp_runtime._engine_cache_transaction(root) as key:
+        for cache in (
+            mcp_runtime._live_engines,
+            mcp_runtime._live_engine_revisions,
+            mcp_runtime._live_engine_provenance,
+            mcp_runtime._live_sessions,
+            mcp_runtime._live_journal_revisions,
+        ):
+            cache.pop(key, None)
+
+
+def test_real_desktop_watcher_and_public_mcp_incremental_match_fresh_full(
+    tmp_path, monkeypatch, isolated_dirs
+):
+    root = (tmp_path / "b0g2d_repo").resolve()
+    root.mkdir()
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(tmp_path / "mcp-process-registry"),
+    )
+    for relative, content in _INITIAL.items():
+        target = root / relative
+        target.parent.mkdir(parents=True, exist_ok=True)
+        target.write_bytes(content)
+    identity, _ = ensure_repository_identity(root)
+    captures = {}
+    init = root / "pkg" / "__init__.py"
+
+    try:
+        baseline = _full_capture(root, identity.repo_id, dict(_INITIAL))
+        captures["initial_full"] = baseline
+        _assert_consumer_edges(baseline.state, changed=False)
+
+        with _isolated_live_server(root, baseline) as (server, client):
+            watcher = DesktopLiveWatcher(root, client, interval=0.01)
+            assert watcher._thread is None and watcher._observer is None
+            assert watcher._startup_pending == []
+            init.write_bytes(_CHANGED_INIT)
+            watcher._enqueue_path(init)
+            deadline = time.monotonic() + 10.0
+            reconciled = []
+            while time.monotonic() < deadline:
+                reconciled.extend(watcher.poll_once())
+                if reconciled == [str(init)]:
+                    break
+                time.sleep(0.01)
+            assert reconciled == [str(init)], f"watcher did not reconcile: {reconciled!r}"
+
+            jobs = list(server._mutation_coordinator._jobs.values())
+            assert len(jobs) == 1, "watcher submitted an unexpected number of updates"
+            job = jobs[0]
+            assert job.request["operation"] == "submit_update_file"
+            assert job.request["origin"] == "desktop_watcher"
+            status = client.mutation_status(job.job_id)
+            assert status["status"] == "ok"
+            assert status["accepted_revision"] == baseline.metadata.revision
+            assert status["state"] == "completed"
+            response = status["response"]
+            assert response["status"] == "ok"
+            assert response["revision"] == baseline.metadata.revision + 1
+            assert response["result"].status == "UPDATED"
+            desktop_affected = set(response["result"].affected_modules)
+            assert "consumer" in desktop_affected
+            assert "unrelated" not in desktop_affected
+            assert response["result"].graph_state == "fresh"
+            events = client.get_events(after_revision=baseline.metadata.revision)
+            assert events["status"] == "ok"
+            assert events["resync_required"] is False
+            assert len(events["events"]) == 1
+            assert events["events"][0]["origin"] == "desktop_watcher"
+            assert events["events"][0]["status"] == "UPDATED"
+            live_snapshot = client.snapshot()
+            desktop_incremental = full_parity._capture_snapshot(
+                root,
+                expected_writer="live-service",
+                expected_repo_id=identity.repo_id,
+                source_bytes=_source_bytes(root),
+            )
+            captures["desktop_incremental"] = desktop_incremental
+            _assert_generation(root, desktop_incremental, live_snapshot)
+            assert desktop_incremental.metadata.revision == baseline.metadata.revision + 1
+            _assert_consumer_edges(desktop_incremental.state, changed=True)
+            assert watcher._thread is None and watcher._observer is None
+
+        modified_sources = _source_bytes(root)
+        assert modified_sources["pkg/__init__.py"] == _CHANGED_INIT
+        oracle_a = _full_capture(root, identity.repo_id, modified_sources)
+        captures["fresh_full_a"] = oracle_a
+        _assert_equal_state(
+            desktop_incremental, oracle_a,
+            label="Desktop incremental vs fresh FULL A",
+            tmp_path=tmp_path, captures=captures,
+        )
+        _assert_file_states(
+            desktop_incremental, oracle_a,
+            label="Desktop incremental vs fresh FULL A",
+            tmp_path=tmp_path, captures=captures,
+        )
+        _assert_consumer_edges(oracle_a.state, changed=True)
+
+        init.write_bytes(b"")
+        baseline_two = _full_capture(root, identity.repo_id, dict(_INITIAL))
+        captures["restored_full"] = baseline_two
+        _assert_equal_state(
+            baseline, baseline_two,
+            label="restored initial FULL baseline",
+            tmp_path=tmp_path, captures=captures,
+        )
+        _assert_consumer_edges(baseline_two.state, changed=False)
+
+        with _isolated_live_server(root, baseline_two) as (server, client):
+            init.write_bytes(_CHANGED_INIT)
+            with monkeypatch.context() as scoped:
+                import contextor.core.live_state as live_state
+                scoped.setattr(live_state, "connect", lambda target: client if Path(target).resolve() == root else None)
+                public = json.loads(
+                    mcp_server.update_file.fn(
+                        repo_path=str(root),
+                        file_path=str(init),
+                        compact=False,
+                    )
+                )
+            assert public["status"] == "UPDATED", public
+            assert public["live_state_persisted"] is True
+            assert "consumer" in public["affected_modules"]["items"]
+            assert "unrelated" not in public["affected_modules"]["items"]
+            assert server._mutation_coordinator._jobs == {}
+            events = client.get_events(after_revision=baseline_two.metadata.revision)
+            assert events["status"] == "ok"
+            assert events["resync_required"] is False
+            assert len(events["events"]) == 1
+            assert events["events"][0]["origin"] == "mcp"
+            assert events["events"][0]["status"] == "UPDATED"
+            live_snapshot = client.snapshot()
+            mcp_incremental = full_parity._capture_snapshot(
+                root,
+                expected_writer="live-service",
+                expected_repo_id=identity.repo_id,
+                source_bytes=_source_bytes(root),
+            )
+            captures["mcp_incremental"] = mcp_incremental
+            assert mcp_incremental.metadata.revision == baseline_two.metadata.revision + 1
+            _assert_generation(root, mcp_incremental, live_snapshot)
+            _assert_consumer_edges(mcp_incremental.state, changed=True)
+            key = mcp_runtime._engine_cache_key(root)
+            assert mcp_runtime._live_engine_revisions[key] == mcp_incremental.metadata.revision
+            assert mcp_runtime._live_engines[key].state.revision == mcp_incremental.metadata.revision
+
+        oracle_b = _full_capture(root, identity.repo_id, modified_sources)
+        captures["fresh_full_b"] = oracle_b
+        for left_name, right_name in (
+            ("mcp_incremental", "fresh_full_b"),
+            ("desktop_incremental", "mcp_incremental"),
+            ("fresh_full_a", "fresh_full_b"),
+        ):
+            _assert_equal_state(
+                captures[left_name], captures[right_name],
+                label=f"{left_name} vs {right_name}",
+                tmp_path=tmp_path, captures=captures,
+            )
+        _assert_file_states(
+            mcp_incremental, oracle_b,
+            label="MCP incremental vs fresh FULL B",
+            tmp_path=tmp_path, captures=captures,
+        )
+        _assert_consumer_edges(oracle_b.state, changed=True)
+        assert _source_bytes(root) == modified_sources
+        _assert_no_production_endpoint(root)
+    finally:
+        _clear_isolated_mcp_cache(root)
```

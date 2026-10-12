"""Real watcher and public MCP incremental updates against fresh FULL analysis."""

from __future__ import annotations

import copy
import hashlib
import json
import pickle
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

import test_desktop_mcp_canonical_parity as full_parity
from contextor import mcp_server
from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
from contextor.core.analysis.state_manager import FileStateManager
from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
from contextor.core.live_state.runtime import (
    _read_endpoint,
    _repository_persister,
    _repository_updater,
)
from contextor.core.live_state.store import read_metadata
from contextor.core.live_state.watcher import DesktopLiveWatcher
from contextor.core.paths import repo_cache_dir
from contextor.core.repository_identity import ensure_repository_identity
from contextor.mcp import runtime as mcp_runtime


_INITIAL = {
    "pkg/__init__.py": b"",
    "pkg/child.py": b"VALUE = 1\n",
    "consumer.py": b"from pkg import child\nVALUE = child.VALUE\n",
    "unrelated.py": b"VALUE = 2\n",
}
_CHANGED_INIT = b"child = 123\n"


def _source_bytes(root: Path) -> dict[str, bytes]:
    return {relative: (root / relative).read_bytes() for relative in _INITIAL}


def _assert_no_production_endpoint(root: Path) -> None:
    assert _read_endpoint(root, strict=True) is None


def _full_capture(root: Path, repo_id: str, expected_sources: dict[str, bytes]):
    _assert_no_production_endpoint(root)
    errors, analysis_result = run_full_analysis_exclusive(
        root,
        owner="desktop_analysis",
    )
    assert not errors
    assert analysis_result is not None
    assert _source_bytes(root) == expected_sources
    _assert_no_production_endpoint(root)
    return full_parity._capture_snapshot(
        root,
        expected_writer="desktop",
        expected_repo_id=repo_id,
        source_bytes=expected_sources,
    )


@contextmanager
def _isolated_live_server(root: Path, baseline):
    _assert_no_production_endpoint(root)
    state = copy.deepcopy(baseline.state)
    holder: dict[str, object] = {}
    server = CanonicalLiveServer(
        state,
        revision=baseline.metadata.revision,
        updater=_repository_updater(root, holder),
        persister=_repository_persister(
            root,
            holder,
            previous_state=state,
        ),
    )
    service = threading.Thread(
        target=server.serve_forever,
        name="b0g2d-isolated-live-service",
        daemon=True,
    )
    service.start()
    client = LiveStateClient(server.endpoint)
    try:
        assert client.ping()["revision"] == baseline.metadata.revision
        _assert_no_production_endpoint(root)
        yield server, client
    finally:
        closed = server.close()
        service.join(timeout=5.0)
        assert closed, "isolated LIVE server failed to close"
        assert not service.is_alive(), "isolated LIVE service thread leaked"
        worker = server._mutation_coordinator._thread
        assert worker is None or not worker.is_alive(), "mutation worker leaked"
        _assert_no_production_endpoint(root)


def _preserve_failure(tmp_path: Path, captures: dict[str, object]) -> Path:
    evidence = tmp_path / "b0g2d_canonical_mismatch_evidence"
    evidence.mkdir(exist_ok=True)
    for label, capture in captures.items():
        with (evidence / f"{label}.pickle").open("wb") as output:
            pickle.dump(
                {
                    "state": capture.state,
                    "metadata": capture.metadata,
                    "file_states": capture.file_states,
                    "file_state_payload": capture.file_state_payload,
                    "source_bytes": capture.source_bytes,
                },
                output,
                protocol=pickle.HIGHEST_PROTOCOL,
            )
    return evidence


def _assert_equal_state(
    left,
    right,
    *,
    label: str,
    tmp_path: Path,
    captures: dict[str, object],
) -> None:
    left_projection = full_parity._state_projection(
        left.state, normalize_report_timestamps=True
    )
    right_projection = full_parity._state_projection(
        right.state, normalize_report_timestamps=True
    )
    difference = full_parity._first_difference(left_projection, right_projection)
    if difference is not None:
        path, left_value, right_value = difference
        evidence = _preserve_failure(tmp_path, captures)
        pytest.fail(
            f"{label} canonical mismatch: first_field={path}; "
            f"left={full_parity._short_repr(left_value)}; "
            f"right={full_parity._short_repr(right_value)}; "
            f"evidence={evidence}",
            pytrace=False,
        )


def _assert_file_states(
    left,
    right,
    *,
    label: str,
    tmp_path: Path,
    captures: dict[str, object],
) -> None:
    left_projection = full_parity._project(left.file_states, "FileStateManager._state")
    right_projection = full_parity._project(right.file_states, "FileStateManager._state")
    difference = full_parity._first_difference(
        left_projection, right_projection, "FileStateManager._state"
    )
    if difference is not None:
        path, left_value, right_value = difference
        evidence = _preserve_failure(tmp_path, captures)
        pytest.fail(
            f"{label} FileState mismatch: first_field={path}; "
            f"left={full_parity._short_repr(left_value)}; "
            f"right={full_parity._short_repr(right_value)}; "
            f"evidence={evidence}",
            pytrace=False,
        )


def _assert_generation(root: Path, capture, live_snapshot: dict) -> None:
    metadata = read_metadata(repo_cache_dir(root))
    assert metadata == capture.metadata
    assert live_snapshot["status"] == "ok"
    assert live_snapshot["revision"] == metadata.revision
    assert live_snapshot["state"].revision == metadata.revision
    assert live_snapshot["state"].state_id == metadata.state_id
    assert getattr(live_snapshot["state"], "resync_required", False) is not True
    assert capture.file_state_payload["_meta"] == {
        "state_id": metadata.state_id,
        "revision": metadata.revision,
    }
    manager = FileStateManager(str(repo_cache_dir(root)))
    assert manager.baseline_status == "trusted"
    assert manager.revision == metadata.revision
    assert manager.state_id == metadata.state_id
    assert full_parity._state_projection(live_snapshot["state"]) == (
        full_parity._state_projection(capture.state)
    )
    for relative, content in capture.source_bytes.items():
        recorded = capture.file_states[str((root / relative).resolve())]
        assert recorded.sha256 == hashlib.sha256(content).hexdigest()


def _assert_consumer_edges(state, *, changed: bool) -> None:
    graph = state.dependency_graph
    assert graph.hard_edges["consumer"] == {"pkg.__init__"}
    assert graph.soft_edges["consumer"] == (set() if changed else {"pkg.child"})
    assert graph.hard_edges["unrelated"] == set()
    assert graph.soft_edges["unrelated"] == set()


def _clear_isolated_mcp_cache(root: Path) -> None:
    with mcp_runtime._engine_cache_transaction(root) as key:
        for cache in (
            mcp_runtime._live_engines,
            mcp_runtime._live_engine_revisions,
            mcp_runtime._live_engine_provenance,
            mcp_runtime._live_sessions,
            mcp_runtime._live_journal_revisions,
        ):
            cache.pop(key, None)


def test_real_desktop_watcher_and_public_mcp_incremental_match_fresh_full(
    tmp_path, monkeypatch, isolated_dirs
):
    root = (tmp_path / "b0g2d_repo").resolve()
    root.mkdir()
    monkeypatch.setenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        str(tmp_path / "mcp-process-registry"),
    )
    for relative, content in _INITIAL.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    identity, _ = ensure_repository_identity(root)
    captures = {}
    init = root / "pkg" / "__init__.py"

    try:
        baseline = _full_capture(root, identity.repo_id, dict(_INITIAL))
        captures["initial_full"] = baseline
        _assert_consumer_edges(baseline.state, changed=False)

        with _isolated_live_server(root, baseline) as (server, client):
            watcher = DesktopLiveWatcher(root, client, interval=0.01)
            assert watcher._thread is None and watcher._observer is None
            assert watcher._startup_pending == []
            init.write_bytes(_CHANGED_INIT)
            watcher._enqueue_path(init)
            deadline = time.monotonic() + 10.0
            reconciled = []
            while time.monotonic() < deadline:
                reconciled.extend(watcher.poll_once())
                if reconciled == [str(init)]:
                    break
                time.sleep(0.01)
            assert reconciled == [str(init)], f"watcher did not reconcile: {reconciled!r}"

            jobs = list(server._mutation_coordinator._jobs.values())
            assert len(jobs) == 1, "watcher submitted an unexpected number of updates"
            job = jobs[0]
            assert job.request["operation"] == "submit_update_file"
            assert job.request["origin"] == "desktop_watcher"
            status = client.mutation_status(job.job_id)
            assert status["status"] == "ok"
            assert status["accepted_revision"] == baseline.metadata.revision
            assert status["state"] == "completed"
            response = status["response"]
            assert response["status"] == "ok"
            assert response["revision"] == baseline.metadata.revision + 1
            assert response["result"].status == "UPDATED"
            desktop_affected = set(response["result"].affected_modules)
            assert "consumer" in desktop_affected
            assert "unrelated" not in desktop_affected
            assert response["result"].graph_state == "fresh"
            events = client.get_events(after_revision=baseline.metadata.revision)
            assert events["status"] == "ok"
            assert events["resync_required"] is False
            assert len(events["events"]) == 1
            assert events["events"][0]["origin"] == "desktop_watcher"
            assert events["events"][0]["status"] == "UPDATED"
            live_snapshot = client.snapshot()
            desktop_incremental = full_parity._capture_snapshot(
                root,
                expected_writer="live-service",
                expected_repo_id=identity.repo_id,
                source_bytes=_source_bytes(root),
            )
            captures["desktop_incremental"] = desktop_incremental
            _assert_generation(root, desktop_incremental, live_snapshot)
            assert desktop_incremental.metadata.revision == baseline.metadata.revision + 1
            _assert_consumer_edges(desktop_incremental.state, changed=True)
            assert watcher._thread is None and watcher._observer is None

        modified_sources = _source_bytes(root)
        assert modified_sources["pkg/__init__.py"] == _CHANGED_INIT
        oracle_a = _full_capture(root, identity.repo_id, modified_sources)
        captures["fresh_full_a"] = oracle_a
        _assert_equal_state(
            desktop_incremental, oracle_a,
            label="Desktop incremental vs fresh FULL A",
            tmp_path=tmp_path, captures=captures,
        )
        _assert_file_states(
            desktop_incremental, oracle_a,
            label="Desktop incremental vs fresh FULL A",
            tmp_path=tmp_path, captures=captures,
        )
        _assert_consumer_edges(oracle_a.state, changed=True)

        init.write_bytes(b"")
        baseline_two = _full_capture(root, identity.repo_id, dict(_INITIAL))
        captures["restored_full"] = baseline_two
        _assert_equal_state(
            baseline, baseline_two,
            label="restored initial FULL baseline",
            tmp_path=tmp_path, captures=captures,
        )
        _assert_consumer_edges(baseline_two.state, changed=False)

        with _isolated_live_server(root, baseline_two) as (server, client):
            init.write_bytes(_CHANGED_INIT)
            with monkeypatch.context() as scoped:
                import contextor.core.live_state as live_state
                scoped.setattr(live_state, "connect", lambda target: client if Path(target).resolve() == root else None)
                public = json.loads(
                    mcp_server.update_file.fn(
                        repo_path=str(root),
                        file_path=str(init),
                        compact=False,
                    )
                )
            assert public["status"] == "UPDATED", public
            assert public["live_state_persisted"] is True
            assert "consumer" in public["affected_modules"]["items"]
            assert "unrelated" not in public["affected_modules"]["items"]
            assert server._mutation_coordinator._jobs == {}
            events = client.get_events(after_revision=baseline_two.metadata.revision)
            assert events["status"] == "ok"
            assert events["resync_required"] is False
            assert len(events["events"]) == 1
            assert events["events"][0]["origin"] == "mcp"
            assert events["events"][0]["status"] == "UPDATED"
            live_snapshot = client.snapshot()
            mcp_incremental = full_parity._capture_snapshot(
                root,
                expected_writer="live-service",
                expected_repo_id=identity.repo_id,
                source_bytes=_source_bytes(root),
            )
            captures["mcp_incremental"] = mcp_incremental
            assert mcp_incremental.metadata.revision == baseline_two.metadata.revision + 1
            _assert_generation(root, mcp_incremental, live_snapshot)
            _assert_consumer_edges(mcp_incremental.state, changed=True)
            key = mcp_runtime._engine_cache_key(root)
            assert mcp_runtime._live_engine_revisions[key] == mcp_incremental.metadata.revision
            assert mcp_runtime._live_engines[key].state.revision == mcp_incremental.metadata.revision

        oracle_b = _full_capture(root, identity.repo_id, modified_sources)
        captures["fresh_full_b"] = oracle_b
        for left_name, right_name in (
            ("mcp_incremental", "fresh_full_b"),
            ("desktop_incremental", "mcp_incremental"),
            ("fresh_full_a", "fresh_full_b"),
        ):
            _assert_equal_state(
                captures[left_name], captures[right_name],
                label=f"{left_name} vs {right_name}",
                tmp_path=tmp_path, captures=captures,
            )
        _assert_file_states(
            mcp_incremental, oracle_b,
            label="MCP incremental vs fresh FULL B",
            tmp_path=tmp_path, captures=captures,
        )
        _assert_consumer_edges(oracle_b.state, changed=True)
        assert _source_bytes(root) == modified_sources
        _assert_no_production_endpoint(root)
    finally:
        _clear_isolated_mcp_cache(root)

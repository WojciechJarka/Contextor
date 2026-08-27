"""
tests/test_full_analysis_coordination.py

Comprehensive test suite certifying the single-writer full-analysis coordinator:
- Multi-threaded / integration concurrency exclusion (max_active == 1)
- Multi-process isolation and different-repo concurrency
- Crash / dead-PID stale lock auto-recovery
- Exception release guarantees in finally
- Cancellation & timeout handling
- Serialized canonical publication sequence (Desktop R+1 -> MCP R+2)
"""

from __future__ import annotations

import multiprocessing
import os
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.core.analysis.full_analysis_coordinator import (
    FullAnalysisBusyError,
    FullAnalysisLease,
    acquire_full_analysis,
    release_full_analysis,
    run_full_analysis_exclusive,
)
from contextor.core.errors import AnalysisCancelled
from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient


def test_coordinator_lease_acquisition_and_release(tmp_path: Path):
    repo_dir = tmp_path / "repo1"
    repo_dir.mkdir()

    lease = acquire_full_analysis(repo_dir, owner="test_owner")
    assert isinstance(lease, FullAnalysisLease)
    assert lease.owner == "test_owner"
    assert Path(lease.lock_path).exists()

    release_full_analysis(lease)
    assert not Path(lease.lock_path).exists()


def test_max_active_full_analyses_and_serialized_execution(tmp_path: Path):
    """
    Requirement 10: Multi-threaded integration test proving max_active_full_analyses == 1
    and strict sequential execution order between Desktop and MCP.
    """
    repo_dir = tmp_path / "repo_concurrency"
    repo_dir.mkdir()

    active_count = 0
    max_active = 0
    active_lock = threading.Lock()

    execution_order = []

    desktop_started = threading.Event()
    desktop_can_finish = threading.Event()

    def fake_analysis(path, *, owner, **kwargs):
        nonlocal active_count, max_active
        with active_lock:
            active_count += 1
            if active_count > max_active:
                max_active = active_count
            execution_order.append(f"{owner}:start")

        if owner == "desktop_analysis":
            desktop_started.set()
            desktop_can_finish.wait(timeout=5.0)

        time.sleep(0.05)

        with active_lock:
            active_count -= 1
            execution_order.append(f"{owner}:end")
        return [], SimpleNamespace(status="ok")

    # Thread 1: Desktop analysis
    def run_desktop():
        run_full_analysis_exclusive(
            repo_dir,
            owner="desktop_analysis",
            analysis_fn=fake_analysis,
        )

    # Thread 2: MCP analysis
    def run_mcp():
        run_full_analysis_exclusive(
            repo_dir,
            owner="mcp_analysis",
            analysis_fn=fake_analysis,
        )

    t_desktop = threading.Thread(target=run_desktop)
    t_mcp = threading.Thread(target=run_mcp)

    t_desktop.start()
    assert desktop_started.wait(timeout=3.0), "Desktop analysis did not start"

    # Start MCP analysis while Desktop analysis is active
    t_mcp.start()
    time.sleep(0.2)

    # MCP should NOT have started inside fake_analysis yet
    with active_lock:
        assert max_active == 1
        assert "mcp_analysis:start" not in execution_order

    # Now allow Desktop to finish
    desktop_can_finish.set()

    t_desktop.join(timeout=3.0)
    t_mcp.join(timeout=3.0)

    assert max_active == 1
    assert execution_order == [
        "desktop_analysis:start",
        "desktop_analysis:end",
        "mcp_analysis:start",
        "mcp_analysis:end",
    ]


def _worker_acquire_and_hold(repo_path: str, owner: str, ready_event, release_event, result_queue):
    try:
        lease = acquire_full_analysis(repo_path, owner=owner, timeout=5.0)
        ready_event.set()
        release_event.wait(timeout=5.0)
        release_full_analysis(lease)
        result_queue.put({"status": "ok", "owner": owner})
    except Exception as exc:
        result_queue.put({"status": "error", "error": str(exc), "owner": owner})


def _worker_try_acquire(repo_path: str, owner: str, timeout: float, result_queue):
    try:
        lease = acquire_full_analysis(repo_path, owner=owner, timeout=timeout)
        release_full_analysis(lease)
        result_queue.put({"status": "ok", "owner": owner})
    except FullAnalysisBusyError:
        result_queue.put({"status": "busy", "owner": owner})
    except Exception as exc:
        result_queue.put({"status": "error", "error": str(exc), "owner": owner})


def test_cross_process_coordination_and_repo_isolation(tmp_path: Path):
    """
    Requirement 11: Cross-process test using multiprocessing.Process.
    Proves process A blocks process B on same repo, while process B2 on
    a different repo acquires concurrently without blocking.
    """
    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    repo1.mkdir()
    repo2.mkdir()

    ctx = multiprocessing.get_context("spawn")
    ready_a = ctx.Event()
    release_a = ctx.Event()
    results_a = ctx.Queue()
    results_b = ctx.Queue()
    results_b2 = ctx.Queue()

    # Process A: acquires repo1 and holds
    p_a = ctx.Process(
        target=_worker_acquire_and_hold,
        args=(str(repo1), "proc_a", ready_a, release_a, results_a),
    )
    p_a.start()

    try:
        assert ready_a.wait(timeout=5.0), "Process A failed to acquire repo1"

        # Process B: tries to acquire repo1 with short timeout -> should be busy / blocked
        p_b = ctx.Process(
            target=_worker_try_acquire,
            args=(str(repo1), "proc_b", 0.5, results_b),
        )
        p_b.start()
        p_b.join(timeout=3.0)

        res_b = results_b.get(timeout=2.0)
        assert res_b["status"] == "busy", f"Process B did not encounter busy state: {res_b}"

        # Process B2: tries to acquire repo2 (different repo) -> should succeed immediately!
        p_b2 = ctx.Process(
            target=_worker_try_acquire,
            args=(str(repo2), "proc_b2", 1.0, results_b2),
        )
        p_b2.start()
        p_b2.join(timeout=3.0)

        res_b2 = results_b2.get(timeout=2.0)
        assert res_b2["status"] == "ok", f"Process B2 failed on different repo: {res_b2}"

        # Release A
        release_a.set()
        p_a.join(timeout=3.0)

        res_a = results_a.get(timeout=2.0)
        assert res_a["status"] == "ok"
    finally:
        release_a.set()
        if p_a.is_alive():
            p_a.terminate()


def test_exception_in_analysis_releases_lease(tmp_path: Path):
    """
    Requirement 12a: Exception inside analysis releases lock in finally block.
    """
    repo_dir = tmp_path / "repo_exc"
    repo_dir.mkdir()

    def failing_analysis(path, **kwargs):
        raise ValueError("synthetic analysis failure")

    with pytest.raises(ValueError, match="synthetic analysis failure"):
        run_full_analysis_exclusive(
            repo_dir,
            owner="test_failing",
            analysis_fn=failing_analysis,
        )

    # Next attempt should succeed immediately without busy error
    executed = False
    def succeeding_analysis(path, **kwargs):
        nonlocal executed
        executed = True
        return [], SimpleNamespace(status="ok")

    run_full_analysis_exclusive(
        repo_dir,
        owner="test_succeeding",
        analysis_fn=succeeding_analysis,
        timeout=1.0,
    )
    assert executed is True


def test_dead_pid_stale_lock_recovery(tmp_path: Path):
    """
    Requirement 12b: Stale lock file from terminated/crashed PID is automatically recovered.
    """
    repo_dir = tmp_path / "repo_dead_pid"
    repo_dir.mkdir()

    from contextor.core.analysis.full_analysis_coordinator import _resolve_lock_path
    import json

    lock_file, key, repo_id = _resolve_lock_path(repo_dir)

    # Create a stale lock file with an impossible/dead PID (e.g. 99999999)
    stale_payload = {
        "pid": 99999999,
        "token": "stale_token_123",
        "owner": "crashed_process",
        "repo_id": repo_id,
        "timestamp": time.time() - 100,
    }
    lock_file.write_text(json.dumps(stale_payload), encoding="utf-8")
    assert lock_file.exists()

    # New acquisition should detect dead PID and recover seamlessly
    lease = acquire_full_analysis(repo_dir, owner="recovering_process", timeout=1.0)
    assert lease.owner == "recovering_process"
    assert lease.token != "stale_token_123"

    release_full_analysis(lease)
    assert not lock_file.exists()


def test_cancellation_during_wait(tmp_path: Path):
    """
    Test cancellation check aborts waiting with AnalysisCancelled.
    """
    repo_dir = tmp_path / "repo_cancel"
    repo_dir.mkdir()

    lease = acquire_full_analysis(repo_dir, owner="holder")

    cancelled = True
    with pytest.raises(AnalysisCancelled):
        acquire_full_analysis(
            repo_dir,
            owner="waiter",
            is_cancelled=lambda: cancelled,
            poll_interval=0.05,
            timeout=2.0,
        )

    release_full_analysis(lease)


def test_serialized_publication_sequence_desktop_then_mcp(tmp_path: Path):
    """
    Requirement 13: Simulate Desktop full analysis followed by MCP full analysis
    starting from same initial state, verifying sequential exact-successor revisions
    (R=10 -> R=11 -> R=12), zero non-monotonic errors, and zero duplicates.
    """
    repo_dir = tmp_path / "repo_pub_seq"
    repo_dir.mkdir()

    # Initialize live server at revision 10
    initial_state = SimpleNamespace(revision=10, modules={"init": 1})
    server = CanonicalLiveServer(state=initial_state, revision=10)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        # 1. Desktop Full Analysis (R=10 -> R=11)
        def desktop_analysis_step(path, **kwargs):
            cand = SimpleNamespace(revision=11, modules={"init": 1, "desktop": 1})
            res = client.publish(cand, origin="desktop_analysis")
            assert res["status"] == "ok"
            assert res["revision"] == 11
            return [], SimpleNamespace(live_publish_status="success", live_publish_revision=11)

        run_full_analysis_exclusive(
            repo_dir,
            owner="desktop_analysis",
            analysis_fn=desktop_analysis_step,
        )

        assert server._revision == 11
        assert client.ping()["revision"] == 11

        # 2. MCP Full Analysis (R=11 -> R=12)
        def mcp_analysis_step(path, **kwargs):
            # Reads fresh state at R=11 and produces candidate R=12
            cand = SimpleNamespace(revision=12, modules={"init": 1, "desktop": 1, "mcp": 1})
            res = client.publish(cand, origin="mcp_analysis")
            assert res["status"] == "ok"
            assert res["revision"] == 12
            return [], SimpleNamespace(live_publish_status="success", live_publish_revision=12)

        run_full_analysis_exclusive(
            repo_dir,
            owner="mcp_analysis",
            analysis_fn=mcp_analysis_step,
        )

        assert server._revision == 12
        assert client.ping()["revision"] == 12

        events = client.get_events(after_seq=0)["events"]
        assert len(events) == 2
        assert events[0]["canonical_revision"] == 11
        assert events[0]["origin"] == "desktop_analysis"
        assert events[1]["canonical_revision"] == 12
        assert events[1]["origin"] == "mcp_analysis"
    finally:
        server.close()
        thread.join(timeout=2)

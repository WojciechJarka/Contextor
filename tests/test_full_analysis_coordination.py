"""
tests/test_full_analysis_coordination.py

Complete test suite certifying the single-writer full-analysis coordinator:
- Lease held during publication (Requirement 5)
- OS file-lock cross-process exclusion and process-death auto-recovery (Requirement 11)
- MCP single publication root cause regression (Requirement 12)
- Serialized Desktop + MCP full analysis execution (Requirement 13)
- Non-reentrant in-process lock exclusion and timeout / cancellation guarantees
"""

from __future__ import annotations

import json
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
    _lease_metadata_path,
    _prepare_lock_fd,
    _resolve_lock_path,
    _try_lock_fd,
    _unlock_fd,
    acquire_full_analysis,
    release_full_analysis,
    run_full_analysis_exclusive,
)
from contextor.core.errors import AnalysisCancelled
from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
from contextor.mcp import analysis_jobs
from contextor.mcp import runtime as mcp_runtime


def test_coordinator_lease_acquisition_and_release(tmp_path: Path):
    repo_dir = tmp_path / "repo1"
    repo_dir.mkdir()

    lease = acquire_full_analysis(repo_dir, owner="test_owner")
    assert isinstance(lease, FullAnalysisLease)
    assert lease.owner == "test_owner"
    assert lease.lock_fd >= 0
    assert Path(lease.lock_path).exists()

    release_full_analysis(lease)


def test_normal_shutdown_releases_lease_for_next_desktop_instance(
    tmp_path: Path,
):
    """A clean owner shutdown leaves the next instance free to acquire."""
    repo_dir = tmp_path / "repo_normal_shutdown"
    repo_dir.mkdir()

    owner_a = acquire_full_analysis(repo_dir, owner="desktop_a")
    release_full_analysis(owner_a)

    owner_b = acquire_full_analysis(
        repo_dir,
        owner="desktop_b",
        timeout=0.5,
    )
    try:
        assert owner_b.owner == "desktop_b"
    finally:
        release_full_analysis(owner_b)


def test_lease_is_held_during_publication(tmp_path: Path, monkeypatch):
    """
    Requirement 5: Deterministic lifecycle order proving lease is held during publication:
    lease_acquired -> analysis_started -> analysis_finished -> publish_started -> publish_finished -> lease_released
    Forbidden: lease_released before publish_started
    """
    repo_dir = tmp_path / "repo_lifecycle"
    repo_dir.mkdir()

    event_log: list[str] = []
    log_lock = threading.Lock()

    def record(event: str):
        with log_lock:
            event_log.append(event)

    # Wrap acquire and release to log events
    from contextor.core.analysis import full_analysis_coordinator as fac

    orig_acquire = fac.acquire_full_analysis
    orig_release = fac.release_full_analysis

    def tracked_acquire(*args, **kwargs):
        record("lease_acquired")
        return orig_acquire(*args, **kwargs)

    def tracked_release(lease):
        record("lease_released")
        return orig_release(lease)

    monkeypatch.setattr(fac, "acquire_full_analysis", tracked_acquire)
    monkeypatch.setattr(fac, "release_full_analysis", tracked_release)

    # Injected analysis function that performs work and publication
    def tracked_analysis(path, *, owner, **kwargs):
        record("analysis_started")
        time.sleep(0.02)
        record("analysis_finished")

        record("publish_started")
        time.sleep(0.02)
        record("publish_finished")

        return [], SimpleNamespace(
            live_publish_status="success",
            live_publish_revision=11,
            live_publish_warning=None,
        )

    run_full_analysis_exclusive(
        repo_dir,
        owner="mcp_analysis",
        analysis_fn=tracked_analysis,
    )

    expected_order = [
        "lease_acquired",
        "analysis_started",
        "analysis_finished",
        "publish_started",
        "publish_finished",
        "lease_released",
    ]
    assert event_log == expected_order


def _worker_os_lock_hold(repo_path: str, owner: str, ready_event, result_queue, hold_seconds: float):
    """Worker process that acquires OS lock and holds it until killed or timeout."""
    try:
        lease = acquire_full_analysis(repo_path, owner=owner, timeout=5.0)
        result_queue.put({"status": "acquired", "owner": owner, "pid": os.getpid()})
        ready_event.set()
        time.sleep(hold_seconds)
        release_full_analysis(lease)
    except BaseException as exc:
        result_queue.put(
            {"status": "error", "owner": owner, "pid": os.getpid(), "error": repr(exc)}
        )
        ready_event.set()
        raise


def _worker_try_acquire(repo_path: str, owner: str, timeout: float, result_queue):
    """Worker process that attempts to acquire lease."""
    try:
        lease = acquire_full_analysis(repo_path, owner=owner, timeout=timeout)
        release_full_analysis(lease)
        result_queue.put({"status": "ok", "owner": owner})
    except FullAnalysisBusyError:
        result_queue.put({"status": "busy", "owner": owner})
    except Exception as exc:
        result_queue.put({"status": "error", "error": str(exc), "owner": owner})


def _worker_try_acquire_with_log(
    repo_path: str,
    owner: str,
    timeout: float | None,
    result_queue,
    active_owner_event=None,
):
    """Attempt a lease and return the owner diagnostic observed while waiting."""
    messages: list[str] = []

    def record(message: str):
        messages.append(message)
        if active_owner_event is not None and "valid active owner" in message:
            active_owner_event.set()

    try:
        lease = acquire_full_analysis(
            repo_path,
            owner=owner,
            timeout=timeout,
            poll_interval=0.05,
            log=record,
        )
        release_full_analysis(lease)
        result_queue.put({"status": "ok", "owner": owner, "messages": messages})
    except FullAnalysisBusyError:
        result_queue.put(
            {"status": "busy", "owner": owner, "messages": messages}
        )
    except Exception as exc:
        result_queue.put(
            {
                "status": "error",
                "error": str(exc),
                "owner": owner,
                "messages": messages,
            }
        )


def _worker_race_for_orphan_recovery(
    repo_path: str,
    owner: str,
    start_event,
    release_event,
    result_queue,
):
    """Compete for an orphaned lease while the winner holds it for the loser."""
    start_event.wait(timeout=5.0)
    try:
        lease = acquire_full_analysis(
            repo_path,
            owner=owner,
            timeout=1.0,
            poll_interval=0.05,
        )
        result_queue.put({"status": "acquired", "owner": owner})
        release_event.wait(timeout=5.0)
        release_full_analysis(lease)
    except FullAnalysisBusyError:
        result_queue.put({"status": "busy", "owner": owner})
    except Exception as exc:
        result_queue.put(
            {"status": "error", "owner": owner, "error": str(exc)}
        )


def test_cross_process_os_lock_and_process_death_recovery(tmp_path: Path, isolated_dirs):
    """
    Requirement 11: Cross-process exclusion and OS-held file lock auto-recovery on process termination.
    Proves:
    - Process A blocks Process B on same repo.
    - Process A terminated without release -> Process B automatically acquires without lock file unlinking.
    - Process C on different repo acquires concurrently.
    """
    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    repo1.mkdir()
    repo2.mkdir()

    ctx = multiprocessing.get_context("spawn")
    ready_a = ctx.Event()
    results_a = ctx.Queue()
    results_b1 = ctx.Queue()
    results_b2 = ctx.Queue()
    results_c = ctx.Queue()

    # 1. Process A acquires repo1
    p_a = ctx.Process(
        target=_worker_os_lock_hold,
        args=(str(repo1), "proc_a", ready_a, results_a, 15.0),
    )
    p_a.start()

    try:
        assert ready_a.wait(timeout=15.0), "Process A produced no acquisition diagnostic"
        res_a = results_a.get(timeout=2.0)
        assert res_a["status"] == "acquired", f"Process A failed to acquire repo1: {res_a}"

        # 2. Process B attempts repo1 while A is alive -> busy
        p_b1 = ctx.Process(
            target=_worker_try_acquire,
            args=(str(repo1), "proc_b1", 0.5, results_b1),
        )
        p_b1.start()
        p_b1.join(timeout=3.0)

        res_b1 = results_b1.get(timeout=2.0)
        assert res_b1["status"] == "busy", f"Process B1 was not blocked: {res_b1}"

        # 3. Process C attempts repo2 (different repo) concurrently -> succeeds immediately
        p_c = ctx.Process(
            target=_worker_try_acquire,
            args=(str(repo2), "proc_c", 1.0, results_c),
        )
        p_c.start()
        p_c.join(timeout=3.0)

        res_c = results_c.get(timeout=2.0)
        assert res_c["status"] == "ok", f"Process C on different repo failed: {res_c}"

        # 4. Terminate Process A WITHOUT clean release (simulates sudden process death/crash)
        p_a.terminate()
        p_a.join(timeout=3.0)

        # 5. Process B attempts repo1 now -> OS automatically unlocked, acquires without unlinking lock file!
        p_b2 = ctx.Process(
            target=_worker_try_acquire,
            args=(str(repo1), "proc_b2", 2.0, results_b2),
        )
        p_b2.start()
        p_b2.join(timeout=3.0)

        res_b2 = results_b2.get(timeout=2.0)
        assert res_b2["status"] == "ok", f"Process B2 failed to acquire after process death: {res_b2}"

        # Ensure lock file was NOT deleted (file existence is not ownership)
        lock_file, _, _ = _resolve_lock_path(repo1)
        assert lock_file.exists()
    finally:
        if p_a.is_alive():
            p_a.terminate()


def test_live_owner_is_reported_and_cannot_be_stolen(tmp_path: Path, isolated_dirs):
    """A live owner remains authoritative while a contender waits."""
    repo = tmp_path / "repo_live_owner"
    repo.mkdir()

    ctx = multiprocessing.get_context("spawn")
    ready_a = ctx.Event()
    results_a = ctx.Queue()
    results_b = ctx.Queue()
    p_a = ctx.Process(
        target=_worker_os_lock_hold,
        args=(str(repo), "live_owner", ready_a, results_a, 15.0),
    )
    p_a.start()

    try:
        assert ready_a.wait(timeout=15.0)
        assert results_a.get(timeout=2.0)["status"] == "acquired"

        p_b = ctx.Process(
            target=_worker_try_acquire_with_log,
            args=(str(repo), "contender", 0.5, results_b),
        )
        p_b.start()
        p_b.join(timeout=3.0)
        result_b = results_b.get(timeout=2.0)

        assert result_b["status"] == "busy"
        assert any(
            "valid active owner" in message and "live_owner" in message
            for message in result_b["messages"]
        ), result_b
    finally:
        if p_a.is_alive():
            p_a.terminate()
        p_a.join(timeout=3.0)


def test_live_owner_with_no_timeout_is_not_treated_as_unknown(
    tmp_path: Path,
    isolated_dirs,
):
    """A verified live owner may wait without an artificial unknown-owner deadline."""
    repo = tmp_path / "repo_live_owner_no_timeout"
    repo.mkdir()

    ctx = multiprocessing.get_context("spawn")
    ready_a = ctx.Event()
    results_a = ctx.Queue()
    results_b = ctx.Queue()
    active_owner_b = ctx.Event()
    p_a = ctx.Process(
        target=_worker_os_lock_hold,
        args=(str(repo), "live_owner", ready_a, results_a, 15.0),
    )
    p_b = None
    p_a.start()

    try:
        assert ready_a.wait(timeout=15.0)
        assert results_a.get(timeout=2.0)["status"] == "acquired"

        p_b = ctx.Process(
            target=_worker_try_acquire_with_log,
            args=(str(repo), "contender", None, results_b, active_owner_b),
        )
        p_b.start()
        assert active_owner_b.wait(timeout=3.0)

        p_a.terminate()
        p_a.join(timeout=3.0)

        result_b = results_b.get(timeout=3.0)
        assert result_b["status"] == "ok", result_b
        assert any(
            "valid active owner" in message and "live_owner" in message
            for message in result_b["messages"]
        ), result_b
    finally:
        if p_b is not None and p_b.is_alive():
            p_b.terminate()
        if p_b is not None:
            p_b.join(timeout=3.0)
        if p_a.is_alive():
            p_a.terminate()
        p_a.join(timeout=3.0)


def test_unknown_owner_metadata_has_bounded_failure(
    tmp_path: Path,
    monkeypatch,
):
    """An occupied lock with unreadable metadata cannot create an infinite wait."""
    from contextor.core.analysis import full_analysis_coordinator as fac

    monkeypatch.setattr(fac, "ORPHAN_RECOVERY_TIMEOUT_SECONDS", 0.2)
    repo = tmp_path / "repo_unknown_owner"
    repo.mkdir()
    lock_file, _, _ = _resolve_lock_path(repo)
    fd = _prepare_lock_fd(lock_file)
    assert _try_lock_fd(fd)

    try:
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, b"{invalid metadata")
        os.fsync(fd)
        _lease_metadata_path(lock_file).unlink(missing_ok=True)

        messages: list[str] = []
        started = time.monotonic()
        with pytest.raises(
            FullAnalysisBusyError,
            match="owner could not be verified",
        ):
            acquire_full_analysis(
                repo,
                owner="unknown_contender",
                timeout=None,
                poll_interval=0.02,
                log=messages.append,
            )

        assert time.monotonic() - started < 1.0
        assert any("owner could not be verified" in message for message in messages)
    finally:
        _unlock_fd(fd)


def test_legacy_owner_metadata_has_bounded_failure(
    tmp_path: Path,
    monkeypatch,
):
    """Legacy metadata without process identity is unknown, not silently live."""
    from contextor.core.analysis import full_analysis_coordinator as fac

    monkeypatch.setattr(fac, "ORPHAN_RECOVERY_TIMEOUT_SECONDS", 0.2)
    repo = tmp_path / "repo_legacy_owner"
    repo.mkdir()
    lock_file, _, _ = _resolve_lock_path(repo)
    fd = _prepare_lock_fd(lock_file)
    assert _try_lock_fd(fd)

    try:
        legacy_metadata = {
            "pid": os.getpid(),
            "token": "legacy-token",
            "owner": "legacy_holder",
            "repo_id": "legacy-repo",
            "timestamp": time.time(),
        }
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, json.dumps(legacy_metadata).encode("utf-8"))
        os.fsync(fd)
        _lease_metadata_path(lock_file).unlink(missing_ok=True)
        monkeypatch.setattr(fac, "_read_lease_metadata", lambda _fd: legacy_metadata)

        messages: list[str] = []
        with pytest.raises(
            FullAnalysisBusyError,
            match="owner could not be verified",
        ):
            acquire_full_analysis(
                repo,
                owner="legacy_contender",
                timeout=None,
                poll_interval=0.02,
                log=messages.append,
            )

        assert any("identity metadata unavailable" in message for message in messages)
    finally:
        _unlock_fd(fd)


def test_orphan_recovery_is_atomic_for_two_contenders(
    tmp_path: Path,
    isolated_dirs,
):
    """After owner death, exactly one simultaneous contender owns the lease."""
    repo = tmp_path / "repo_orphan_race"
    repo.mkdir()

    ctx = multiprocessing.get_context("spawn")
    ready_a = ctx.Event()
    results_a = ctx.Queue()
    p_a = ctx.Process(
        target=_worker_os_lock_hold,
        args=(str(repo), "orphan_owner", ready_a, results_a, 15.0),
    )
    p_a.start()

    start_event = ctx.Event()
    release_event = ctx.Event()
    results = ctx.Queue()
    contenders = [
        ctx.Process(
            target=_worker_race_for_orphan_recovery,
            args=(str(repo), f"contender_{index}", start_event, release_event, results),
        )
        for index in (1, 2)
    ]

    try:
        assert ready_a.wait(timeout=15.0)
        assert results_a.get(timeout=2.0)["status"] == "acquired"
        p_a.terminate()
        p_a.join(timeout=3.0)

        for contender in contenders:
            contender.start()
        start_event.set()

        observed = [results.get(timeout=3.0) for _ in contenders]
        assert sorted(item["status"] for item in observed) == [
            "acquired",
            "busy",
        ]
    finally:
        release_event.set()
        for contender in contenders:
            contender.join(timeout=3.0)
        if p_a.is_alive():
            p_a.terminate()
            p_a.join(timeout=3.0)


def test_mcp_single_publication_root_cause_regression(tmp_path: Path, monkeypatch):
    """The real MCP worker has one facade-owned LIVE publication path."""
    repo_dir = tmp_path / "repo_mcp_pub"
    repo_dir.mkdir()
    exclusive_calls: list[str] = []

    def fake_run_full_analysis_exclusive(_root, *, owner, **_kwargs):
        exclusive_calls.append(owner)
        return [], SimpleNamespace(
            skipped_python_files=[],
            live_publish_status="success",
            live_publish_revision=11,
            live_publish_warning=None,
        )

    monkeypatch.setattr(
        analysis_jobs,
        "run_full_analysis_exclusive",
        fake_run_full_analysis_exclusive,
    )
    outcome = __import__("asyncio").run(
        analysis_jobs._run_analysis_worker("project", repo_dir)
    )

    assert exclusive_calls == ["mcp_analysis"]
    assert outcome["live_publish_status"] == "success"
    assert outcome["live_publish_revision"] == 11
    assert outcome["live_publish_warning"] is None

    async def fake_worker(*_args, **_kwargs):
        return outcome

    def forbidden_second_publish(*_args, **_kwargs):
        raise AssertionError("outer MCP duplicate publication attempted")

    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: SimpleNamespace(state=SimpleNamespace(revision=11)),
    )
    monkeypatch.setattr(
        "contextor.core.live_state.connect_or_start",
        forbidden_second_publish,
    )
    mcp_runtime._live_engine_revisions.pop(str(repo_dir), None)
    job = {
        "job_id": "c" * 32,
        "repo_path": str(repo_dir),
        "operation": "project",
        "target": None,
        "exclude_paths": [],
        "status": "queued",
        "created_at": "2026-08-28T00:00:00Z",
        "started_at": None,
        "completed_at": None,
        "message": "Analysis accepted.",
        "error": None,
        "live_publish_status": "pending",
        "live_publish_revision": None,
        "live_publish_warning": None,
    }
    analysis_jobs._write_analysis_job(repo_dir, job)
    __import__("asyncio").run(
        analysis_jobs._execute_analysis_job(repo_dir, job, None, [])
    )

    final_job = analysis_jobs._read_analysis_job(repo_dir, job["job_id"])
    assert final_job is not None
    assert final_job["status"] == "completed"
    assert final_job["live_publish_status"] == "success"
    assert final_job["live_publish_revision"] == 11
    assert mcp_runtime._live_engine_revisions[str(repo_dir)] == 11


def test_serialized_desktop_and_mcp_coordination(tmp_path: Path, monkeypatch):
    """
    Requirement 13: Concurrency test proving serialized Desktop + MCP execution:
    - Desktop requests full analysis (R=10 -> R=11)
    - MCP requests full analysis while Desktop owns lease
    - Desktop completes, publishes R=11, releases lease
    - MCP acquires lease, performs complete hard reset, publishes R=12, releases lease
    - max_active == 1
    - publications == [("desktop_analysis", 11), ("mcp_analysis", 12)]
    """
    repo_dir = tmp_path / "repo_serialized"
    repo_dir.mkdir()

    initial_state = SimpleNamespace(revision=10, modules={"app": 1})
    server = CanonicalLiveServer(state=initial_state, revision=10)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    live_client = LiveStateClient(server.endpoint)

    from contextor.core import live_state
    monkeypatch.setattr(live_state, "connect", lambda _path: live_client)
    monkeypatch.setattr("contextor.core.live_state.connect", lambda _path: live_client)

    active_analyses = 0
    max_simultaneous = 0
    active_lock = threading.Lock()
    publications_observed: list[tuple[str, int]] = []

    desktop_holding = threading.Event()
    desktop_can_finish = threading.Event()

    def coordinated_analysis(path, *, owner, **kwargs):
        nonlocal active_analyses, max_simultaneous
        with active_lock:
            active_analyses += 1
            if active_analyses > max_simultaneous:
                max_simultaneous = active_analyses

        if owner == "desktop_analysis":
            desktop_holding.set()
            desktop_can_finish.wait(timeout=5.0)
            next_rev = 11
        else:
            next_rev = 12

        time.sleep(0.05)
        cand_state = SimpleNamespace(revision=next_rev, modules={"app": 1, owner: 1})
        pub_res = live_client.publish(cand_state, origin=owner)
        assert pub_res.get("status") == "ok"
        with active_lock:
            publications_observed.append((owner, pub_res["revision"]))
            active_analyses -= 1

        return [], SimpleNamespace(
            live_publish_status="success",
            live_publish_revision=pub_res["revision"],
        )

    t_desktop = threading.Thread(
        target=lambda: run_full_analysis_exclusive(
            repo_dir, owner="desktop_analysis", analysis_fn=coordinated_analysis
        )
    )
    t_mcp = threading.Thread(
        target=lambda: run_full_analysis_exclusive(
            repo_dir, owner="mcp_analysis", analysis_fn=coordinated_analysis
        )
    )

    try:
        t_desktop.start()
        assert desktop_holding.wait(timeout=3.0), "Desktop did not start analysis"

        # Start MCP while Desktop is holding lease
        t_mcp.start()
        time.sleep(0.1)

        with active_lock:
            assert max_simultaneous == 1
            assert len(publications_observed) == 0

        # Release Desktop
        desktop_can_finish.set()

        t_desktop.join(timeout=3.0)
        t_mcp.join(timeout=3.0)

        assert max_simultaneous == 1
        assert publications_observed == [
            ("desktop_analysis", 11),
            ("mcp_analysis", 12),
        ]
        assert server._revision == 12
        assert live_client.ping()["revision"] == 12
    finally:
        server.close()
        server_thread.join(timeout=2)


def test_in_process_non_reentrant_lock_exclusion(tmp_path: Path):
    """
    Requirement 8: Non-reentrant lock prevents recursive bypass by same thread.
    """
    repo_dir = tmp_path / "repo_non_reentrant"
    repo_dir.mkdir()

    lease1 = acquire_full_analysis(repo_dir, owner="outer", timeout=1.0)
    try:
        with pytest.raises(FullAnalysisBusyError):
            acquire_full_analysis(repo_dir, owner="inner_recursive", timeout=0.2)
    finally:
        release_full_analysis(lease1)


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


def test_exception_in_analysis_releases_lease(tmp_path: Path):
    repo = tmp_path / "repo_exception_release"
    repo.mkdir()

    def failing_analysis(path, **kwargs):
        raise RuntimeError("synthetic analysis failure")

    with pytest.raises(RuntimeError, match="synthetic analysis failure"):
        run_full_analysis_exclusive(
            repo,
            owner="failing_owner",
            analysis_fn=failing_analysis,
        )

    executed = False

    def succeeding_analysis(path, **kwargs):
        nonlocal executed
        executed = True
        return [], SimpleNamespace(
            live_publish_status="not_attempted",
            live_publish_revision=None,
        )

    run_full_analysis_exclusive(
        repo,
        owner="next_owner",
        analysis_fn=succeeding_analysis,
        timeout=1.0,
    )
    assert executed is True

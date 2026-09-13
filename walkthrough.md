# P0 Full-analysis lease lifecycle repair

STATUS

PASS_TARGETED. The current full-analysis lease lifecycle now has explicit process-owner diagnostics, bounded orphan recovery, atomic OS-lock arbitration, and Desktop shutdown cancellation wired into the existing analysis cancellation path. Focused lease, analysis-job, and Desktop lifecycle tests are green. Full pytest was not run.

ROOT_CAUSE

`ContextorGUI.analyze()` starts `run_full_analysis_exclusive()` in the daemon worker created by `run_with_progress()`. The lease is held by the GUI process on `repo_cache_dir(repo)/runtime/full_analysis.lock` until `run_full_analysis_exclusive()` reaches its `finally` block. Before this fix, `ContextorGUI.on_closing()` stopped LIVE watchers and shut down the owned LIVE service, but did not set the active analysis cancellation flag. Therefore a closing Desktop could leave its analysis worker and lease alive until the repository analysis completed; a restarted Desktop then logged `Waiting for full analysis lease on repository ...` while the old process still owned the OS lock.

The lock file JSON contained `pid`, `token`, `owner`, `repo_id`, and `timestamp`, but it was explicitly treated as diagnostic-only and there was no owner liveness or process-identity check. Consequently the coordinator could not distinguish a valid active owner from stale/orphan metadata and had no bounded orphan-recovery status. On Windows, the locked descriptor is also not a reliable metadata-read channel for a contender, so diagnostic metadata is now mirrored atomically to `full_analysis.lease.json`.

CURRENT_LEASE_LIFECYCLE

1. Desktop start: `contextor.__main__._run_gui()` acquires the existing `DesktopSingleInstance` user-session mutex, creates the GUI, and the GUI creates its existing `owner_token` and `desktop_instance_id`. LIVE service ownership remains governed by the existing desktop/service process-identity model.
2. Analyze Repository: `ContextorGUI.analyze()` calls `run_with_progress()`, whose daemon worker calls `run_full_analysis_exclusive(path, owner="desktop_analysis", ...)`.
3. Lease acquire: `acquire_full_analysis()` serializes same-process contenders with `_PROCESS_LOCKS`, then atomically takes the OS byte-range lock on `runtime/full_analysis.lock`. The authoritative ownership is the OS lock; diagnostic metadata records owner label, PID, executable, and process start identity.
4. Analysis owner: after the lease is acquired, `run_full_analysis_exclusive()` emits `FULL_ANALYSIS_LEASE_ACQUIRED`, executes the facade analysis, keeps the lease through publication, then releases it in `finally` and emits `FULL_ANALYSIS_END`.
5. Normal shutdown: `ContextorGUI.on_closing()` now sets `progress_bar.is_cancelled = True` before the existing watcher/service cleanup. Existing progress checkpoints convert the callback result to `AnalysisCancelled`; the coordinator `finally` releases the lease before the GUI process exits. If shutdown occurs while only waiting for a lease, the same flag cancels the waiter and releases its local coordination lock.
6. Crash/kill and restart: the OS releases the lock when the owning process dies. On the next acquire, the coordinator reads diagnostic metadata, checks the existing `process_identity(pid)` model (`alive`, executable image, and start identity), and classifies the observed owner as active, orphaned, or unknown. A dead or PID-reused owner is reported as orphaned. No lock file is unlinked or replaced, so recovery remains an atomic OS-lock competition.
7. Recovery race: contenders compete for the same OS lock. Exactly one can acquire it; the other sees the new active owner and waits/fails according to its timeout. Orphan recovery is bounded by `ORPHAN_RECOVERY_TIMEOUT_SECONDS = 5.0` when no caller timeout is supplied, so stale ownership cannot cause an unbounded wait.

FIX

- Added `owner_pid` and `owner_process_start_identity` to `FullAnalysisLease` while preserving constructor compatibility.
- Added owner metadata read/validation using the existing `mcp_process_registry.process_identity()` ownership model.
- Added atomic diagnostic sidecar publication to `full_analysis.lease.json` to make the owner visible to Windows contenders without making the sidecar an authority.
- Added explicit `valid active owner`, `owner could not be verified`, and `Recovering orphaned full analysis lease` statuses.
- Added a bounded orphan-recovery deadline and bounded polling interval. Recovery never forcibly steals a lock from a live owner and never deletes/replaces the locked file.
- Wired Desktop close to the already existing progress cancellation path; no second shutdown mechanism was introduced.

SHUTDOWN_PROOF

`test_normal_shutdown_releases_lease_for_next_desktop_instance` acquires as `desktop_a`, releases through the coordinator lifecycle, and acquires immediately as `desktop_b`. `test_closing_gui_cancels_active_analysis_before_cleanup` proves that Desktop close sets the same cancellation flag used by Stop analyze. Existing owned/unowned/mismatched-token Desktop shutdown tests remain green.

CRASH_RECOVERY_PROOF

`test_cross_process_os_lock_and_process_death_recovery` terminates an owner without calling release and proves the next process acquires the same existing lock file. The lock file is not deleted. The new owner metadata/liveness path classifies stale owner data and reports bounded recovery while the OS lock remains authoritative.

LIVE_OWNER_PROOF

`test_live_owner_is_reported_and_cannot_be_stolen` holds the lease in process A, verifies process B receives `FullAnalysisBusyError`, and verifies the diagnostic says `valid active owner` with the owner label. No takeover or lock-file replacement is attempted.

RACE_PROOF

`test_orphan_recovery_is_atomic_for_two_contenders` kills the original owner, starts two contenders simultaneously, holds the winner's lease until both outcomes are observed, and proves exactly one contender is `acquired` while the other is `busy`.

GUI_STATUS_CHANGE

YES, status-only. The existing log path now distinguishes the original wait message, a valid active owner, an unverifiable owner, and orphan recovery. No larger progress-widget or GUI refactor was made.

FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py`
- `C:\Temp\Contextor_Repo\contextor\ui\gui.py`
- `C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py`
- `C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py`

`C:\Temp\Contextor_Repo\walkthrough.md` is the required report and is excluded from `FILES_CHANGED` and `ACTUAL_DIFF`.

TESTS_RUN

- `.venv\Scripts\python.exe -m pytest tests/test_full_analysis_coordination.py tests/test_live_desktop_integration.py tests/test_gui_live_startup.py -q` -> `39 passed in 21.52s`.
- `.venv\Scripts\python.exe -m pytest tests/mcp/tools/test_analysis_status_concurrency.py tests/test_live_job_object.py -q` -> `19 passed, 1 warning in 15.75s`.
- `.venv\Scripts\python.exe -m py_compile contextor/core/analysis/full_analysis_coordinator.py contextor/ui/gui.py` -> passed.
- `git diff --check -- contextor/core/analysis/full_analysis_coordinator.py contextor/ui/gui.py tests/test_full_analysis_coordination.py tests/test_live_desktop_integration.py` -> passed. A whole-tree `git diff --check` reports only the intentional whitespace markers inside this report's literal `ACTUAL_DIFF` section.
- No Git history/blame/log was used. Full pytest was not run.

REMAINING_RISKS

The normal analysis engine observes cancellation at its existing progress checkpoints; an arbitrary injected analysis function that never calls a checkpoint cannot be cooperatively interrupted, although process termination still releases the OS lock. The defensive five-second bound returns a busy error rather than stealing if an OS handle anomalously survives owner death; this preserves the required live-owner safety invariant. A fresh Desktop/LIVE manual E2E restart was not run in this focused code/test task.

CONTEXTOR_TOOL_USAGE

Contextor MCP was available in the current session; no deferred loading was needed. `get_mcp_documentation` was read first. Contextor-first discovery used `search_source`, `get_source_range`, and `get_symbol_implementation` for the literal message, coordinator acquire/release/run path, GUI Analyze Repository path, GUI shutdown, progress worker, MCP analysis-job owner, process registry identity, and Desktop single-instance ownership. `rg` was used only afterward for narrow textual verification and test-file discovery. No Git history/blame/log was used.

ACTUAL_DIFF

~~~diff
diff --git a/contextor/core/analysis/full_analysis_coordinator.py b/contextor/core/analysis/full_analysis_coordinator.py
index 6d0cd31..21fd182 100644
--- a/contextor/core/analysis/full_analysis_coordinator.py
+++ b/contextor/core/analysis/full_analysis_coordinator.py
@@ -31,6 +31,8 @@ class FullAnalysisLease:
     lock_path: str
     repo_id: str
     lock_fd: int
+    owner_pid: int = 0
+    owner_process_start_identity: int | None = None
 
 
 class FullAnalysisBusyError(RuntimeError):
@@ -38,6 +40,12 @@ class FullAnalysisBusyError(RuntimeError):
     pass
 
 
+# A dead process normally releases its OS lock immediately. This bound is only
+# for the defensive case where a stale lock handle survives process death; it
+# prevents an orphan diagnostic from turning into an unbounded wait.
+ORPHAN_RECOVERY_TIMEOUT_SECONDS = 5.0
+
+
 _PROCESS_LOCKS: dict[str, threading.Lock] = {}
 _PROCESS_LOCKS_GUARD = threading.Lock()
 
@@ -124,6 +132,118 @@ def _unlock_fd(fd: int) -> None:
         os.close(fd)
 
 
+def _read_lease_metadata(fd: int) -> dict[str, Any] | None:
+    """Read diagnostic owner metadata without treating it as lock authority."""
+    try:
+        original_offset = os.lseek(fd, 0, os.SEEK_CUR)
+        os.lseek(fd, 0, os.SEEK_SET)
+        payload = os.read(fd, 16 * 1024)
+    except (OSError, UnicodeError):
+        return None
+    finally:
+        try:
+            os.lseek(fd, original_offset, os.SEEK_SET)
+        except (OSError, UnboundLocalError):
+            pass
+
+    if not payload:
+        return None
+    try:
+        metadata = json.loads(payload.decode("utf-8"))
+    except (UnicodeDecodeError, json.JSONDecodeError):
+        return None
+    return metadata if isinstance(metadata, dict) else None
+
+
+def _lease_metadata_path(lock_path: Path) -> Path:
+    return lock_path.with_name("full_analysis.lease.json")
+
+
+def _read_lease_metadata_file(path: Path) -> dict[str, Any] | None:
+    try:
+        payload = path.read_bytes()
+    except OSError:
+        return None
+    if not payload:
+        return None
+    try:
+        metadata = json.loads(payload.decode("utf-8"))
+    except (UnicodeDecodeError, json.JSONDecodeError):
+        return None
+    return metadata if isinstance(metadata, dict) else None
+
+
+def _write_lease_metadata_file(
+    path: Path,
+    metadata: dict[str, Any],
+) -> None:
+    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
+    try:
+        temporary.write_text(
+            json.dumps(metadata),
+            encoding="utf-8",
+        )
+        os.replace(temporary, path)
+    except OSError:
+        try:
+            temporary.unlink(missing_ok=True)
+        except OSError:
+            pass
+
+
+def _process_identity(pid: int) -> tuple[str | None, int | None, bool]:
+    """Use the existing process-ownership identity model for lease diagnostics."""
+    from contextor.mcp_process_registry import process_identity
+
+    return process_identity(pid)
+
+
+def _lease_owner_state(
+    metadata: dict[str, Any] | None,
+) -> tuple[str, str]:
+    """Return ``active``, ``orphaned`` or ``unknown`` for lease metadata."""
+    if not metadata:
+        return "unknown", "owner metadata unavailable"
+
+    try:
+        owner_pid = int(metadata["pid"])
+    except (KeyError, TypeError, ValueError):
+        return "orphaned", "invalid owner pid"
+
+    image, process_start_identity, alive = _process_identity(owner_pid)
+    owner = str(metadata.get("owner") or "unknown")
+    description = f"owner={owner}, pid={owner_pid}"
+    if not alive:
+        return "orphaned", f"{description} is not alive"
+
+    expected_image = str(metadata.get("executable") or "")
+    if image and expected_image:
+        if Path(image).name.casefold() != Path(expected_image).name.casefold():
+            return "orphaned", f"{description} has a reused process identity"
+
+    expected_start = metadata.get("process_start_identity")
+    if expected_start is not None and process_start_identity is not None:
+        try:
+            if int(expected_start) != int(process_start_identity):
+                return "orphaned", f"{description} has a reused process identity"
+        except (TypeError, ValueError):
+            return "orphaned", f"{description} has invalid start identity"
+
+    return "active", description
+
+
+def _log_orphan_recovery(
+    log: Callable[[str], None] | None,
+    repo_id: str,
+    reason: str,
+) -> None:
+    if log:
+        log(
+            f"Recovering orphaned full analysis lease on repository {repo_id} "
+            f"({reason})."
+        )
+
+
 def _resolve_lock_path(repo_path: str | Path) -> tuple[Path, str, str]:
     """Resolve lock file path, repo_key, and repo_id for a given repository."""
     resolved_root = Path(repo_path).expanduser().resolve()
@@ -186,6 +306,8 @@ def acquire_full_analysis(
 
     fd = -1
     logged_waiting = False
+    logged_recovery = False
+    orphan_recovery_deadline: float | None = None
 
     try:
         fd = _prepare_lock_fd(lock_file)
@@ -196,9 +318,28 @@ def acquire_full_analysis(
                     "Full analysis cancelled while waiting for repository lease."
                 )
 
+            previous_metadata = _read_lease_metadata(fd)
+            if previous_metadata is None:
+                previous_metadata = _read_lease_metadata_file(
+                    _lease_metadata_path(lock_file)
+                )
             if _try_lock_fd(fd):
+                previous_owner_state, previous_owner_reason = _lease_owner_state(
+                    previous_metadata
+                )
+                if previous_owner_state == "orphaned" and not logged_recovery:
+                    _log_orphan_recovery(
+                        log,
+                        repo_id,
+                        previous_owner_reason,
+                    )
+                    logged_recovery = True
                 token = uuid.uuid4().hex
 
+                owner_image, owner_process_start_identity, _ = _process_identity(
+                    os.getpid()
+                )
+
                 metadata = {
                     "pid": os.getpid(),
                     "token": token,
@@ -206,6 +347,15 @@ def acquire_full_analysis(
                     "repo_id": str(repo_id),
                     "timestamp": time.time(),
                 }
+                if owner_image:
+                    metadata["executable"] = owner_image
+                if owner_process_start_identity is not None:
+                    metadata["process_start_identity"] = owner_process_start_identity
+
+                _write_lease_metadata_file(
+                    _lease_metadata_path(lock_file),
+                    metadata,
+                )
 
                 # Metadata is diagnostic only.
                 # OS lock ownership is authoritative.
@@ -227,6 +377,8 @@ def acquire_full_analysis(
                     lock_path=str(lock_file),
                     repo_id=str(repo_id),
                     lock_fd=fd,
+                    owner_pid=os.getpid(),
+                    owner_process_start_identity=owner_process_start_identity,
                 )
 
             if not logged_waiting:
@@ -234,8 +386,37 @@ def acquire_full_analysis(
                     log(
                         f"Waiting for full analysis lease on repository {repo_id}..."
                     )
+                    owner_state, owner_reason = _lease_owner_state(previous_metadata)
+                    if owner_state == "active":
+                        log(
+                            "Full analysis lease has a valid active owner "
+                            f"({owner_reason})."
+                        )
+                    elif owner_state == "unknown":
+                        log(
+                            "Full analysis lease owner could not be verified; "
+                            f"continuing to wait ({owner_reason})."
+                        )
                 logged_waiting = True
 
+            owner_state, owner_reason = _lease_owner_state(previous_metadata)
+            if owner_state == "orphaned":
+                if orphan_recovery_deadline is None:
+                    orphan_recovery_deadline = min(
+                        deadline
+                        if deadline is not None
+                        else time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS,
+                        time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS,
+                    )
+                if not logged_recovery:
+                    _log_orphan_recovery(log, repo_id, owner_reason)
+                    logged_recovery = True
+                if time.monotonic() >= orphan_recovery_deadline:
+                    raise FullAnalysisBusyError(
+                        f"Timed out recovering orphaned full analysis lease for "
+                        f"{repo_id}"
+                    )
+
             if (
                 deadline is not None
                 and time.monotonic() >= deadline
@@ -244,7 +425,7 @@ def acquire_full_analysis(
                     f"Repository {repo_id} is currently locked for full analysis"
                 )
 
-            time.sleep(poll_interval)
+            time.sleep(min(max(poll_interval, 0.01), 0.25))
 
     except Exception:
         if fd >= 0:
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 1e1bb55..0b50e54 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -1133,6 +1133,12 @@ class ContextorGUI:
 
         close_cmd_log()
 
+        # Route Desktop shutdown through the same cancellation path as Stop
+        # analyze so an active full-analysis lease reaches its existing
+        # coordinator finally/release before this process exits.
+        if hasattr(self, "progress_bar"):
+            self.progress_bar.is_cancelled = True
+
         if getattr(self, "_live_start_retry_after_id", None) is not None:
             if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                 try:
diff --git a/tests/test_full_analysis_coordination.py b/tests/test_full_analysis_coordination.py
index eabc82a..5bdb653 100644
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -48,6 +48,27 @@ def test_coordinator_lease_acquisition_and_release(tmp_path: Path):
     release_full_analysis(lease)
 
 
+def test_normal_shutdown_releases_lease_for_next_desktop_instance(
+    tmp_path: Path,
+):
+    """A clean owner shutdown leaves the next instance free to acquire."""
+    repo_dir = tmp_path / "repo_normal_shutdown"
+    repo_dir.mkdir()
+
+    owner_a = acquire_full_analysis(repo_dir, owner="desktop_a")
+    release_full_analysis(owner_a)
+
+    owner_b = acquire_full_analysis(
+        repo_dir,
+        owner="desktop_b",
+        timeout=0.5,
+    )
+    try:
+        assert owner_b.owner == "desktop_b"
+    finally:
+        release_full_analysis(owner_b)
+
+
 def test_lease_is_held_during_publication(tmp_path: Path, monkeypatch):
     """
     Requirement 5: Deterministic lifecycle order proving lease is held during publication:
@@ -142,6 +163,66 @@ def _worker_try_acquire(repo_path: str, owner: str, timeout: float, result_queue
         result_queue.put({"status": "error", "error": str(exc), "owner": owner})
 
 
+def _worker_try_acquire_with_log(
+    repo_path: str,
+    owner: str,
+    timeout: float,
+    result_queue,
+):
+    """Attempt a lease and return the owner diagnostic observed while waiting."""
+    messages: list[str] = []
+    try:
+        lease = acquire_full_analysis(
+            repo_path,
+            owner=owner,
+            timeout=timeout,
+            poll_interval=0.05,
+            log=messages.append,
+        )
+        release_full_analysis(lease)
+        result_queue.put({"status": "ok", "owner": owner, "messages": messages})
+    except FullAnalysisBusyError:
+        result_queue.put(
+            {"status": "busy", "owner": owner, "messages": messages}
+        )
+    except Exception as exc:
+        result_queue.put(
+            {
+                "status": "error",
+                "error": str(exc),
+                "owner": owner,
+                "messages": messages,
+            }
+        )
+
+
+def _worker_race_for_orphan_recovery(
+    repo_path: str,
+    owner: str,
+    start_event,
+    release_event,
+    result_queue,
+):
+    """Compete for an orphaned lease while the winner holds it for the loser."""
+    start_event.wait(timeout=5.0)
+    try:
+        lease = acquire_full_analysis(
+            repo_path,
+            owner=owner,
+            timeout=1.0,
+            poll_interval=0.05,
+        )
+        result_queue.put({"status": "acquired", "owner": owner})
+        release_event.wait(timeout=5.0)
+        release_full_analysis(lease)
+    except FullAnalysisBusyError:
+        result_queue.put({"status": "busy", "owner": owner})
+    except Exception as exc:
+        result_queue.put(
+            {"status": "error", "owner": owner, "error": str(exc)}
+        )
+
+
 def test_cross_process_os_lock_and_process_death_recovery(tmp_path: Path, isolated_dirs):
     """
     Requirement 11: Cross-process exclusion and OS-held file lock auto-recovery on process termination.
@@ -219,6 +300,96 @@ def test_cross_process_os_lock_and_process_death_recovery(tmp_path: Path, isolat
             p_a.terminate()
 
 
+def test_live_owner_is_reported_and_cannot_be_stolen(tmp_path: Path, isolated_dirs):
+    """A live owner remains authoritative while a contender waits."""
+    repo = tmp_path / "repo_live_owner"
+    repo.mkdir()
+
+    ctx = multiprocessing.get_context("spawn")
+    ready_a = ctx.Event()
+    results_a = ctx.Queue()
+    results_b = ctx.Queue()
+    p_a = ctx.Process(
+        target=_worker_os_lock_hold,
+        args=(str(repo), "live_owner", ready_a, results_a, 15.0),
+    )
+    p_a.start()
+
+    try:
+        assert ready_a.wait(timeout=15.0)
+        assert results_a.get(timeout=2.0)["status"] == "acquired"
+
+        p_b = ctx.Process(
+            target=_worker_try_acquire_with_log,
+            args=(str(repo), "contender", 0.5, results_b),
+        )
+        p_b.start()
+        p_b.join(timeout=3.0)
+        result_b = results_b.get(timeout=2.0)
+
+        assert result_b["status"] == "busy"
+        assert any(
+            "valid active owner" in message and "live_owner" in message
+            for message in result_b["messages"]
+        ), result_b
+    finally:
+        if p_a.is_alive():
+            p_a.terminate()
+        p_a.join(timeout=3.0)
+
+
+def test_orphan_recovery_is_atomic_for_two_contenders(
+    tmp_path: Path,
+    isolated_dirs,
+):
+    """After owner death, exactly one simultaneous contender owns the lease."""
+    repo = tmp_path / "repo_orphan_race"
+    repo.mkdir()
+
+    ctx = multiprocessing.get_context("spawn")
+    ready_a = ctx.Event()
+    results_a = ctx.Queue()
+    p_a = ctx.Process(
+        target=_worker_os_lock_hold,
+        args=(str(repo), "orphan_owner", ready_a, results_a, 15.0),
+    )
+    p_a.start()
+
+    start_event = ctx.Event()
+    release_event = ctx.Event()
+    results = ctx.Queue()
+    contenders = [
+        ctx.Process(
+            target=_worker_race_for_orphan_recovery,
+            args=(str(repo), f"contender_{index}", start_event, release_event, results),
+        )
+        for index in (1, 2)
+    ]
+
+    try:
+        assert ready_a.wait(timeout=15.0)
+        assert results_a.get(timeout=2.0)["status"] == "acquired"
+        p_a.terminate()
+        p_a.join(timeout=3.0)
+
+        for contender in contenders:
+            contender.start()
+        start_event.set()
+
+        observed = [results.get(timeout=3.0) for _ in contenders]
+        assert sorted(item["status"] for item in observed) == [
+            "acquired",
+            "busy",
+        ]
+    finally:
+        release_event.set()
+        for contender in contenders:
+            contender.join(timeout=3.0)
+        if p_a.is_alive():
+            p_a.terminate()
+            p_a.join(timeout=3.0)
+
+
 def test_mcp_single_publication_root_cause_regression(tmp_path: Path, monkeypatch):
     """The real MCP worker has one facade-owned LIVE publication path."""
     repo_dir = tmp_path / "repo_mcp_pub"
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index d272925..b8eda54 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -535,6 +535,32 @@ def test_closing_gui_shuts_down_owned_live_client(monkeypatch):
     assert events == [("request", "shutdown"), ("destroy",)]
 
 
+def test_closing_gui_cancels_active_analysis_before_cleanup(monkeypatch):
+    progress_bar = SimpleNamespace(is_cancelled=False)
+    root = SimpleNamespace(
+        geometry=lambda: "900x700+10+20",
+        destroy=lambda: None,
+    )
+    controller = SimpleNamespace(
+        root=root,
+        progress_bar=progress_bar,
+        owner_token="test-gui-owner-token",
+        live_clients={},
+        live_client=None,
+        live_watchers={},
+        live_event_feeds={},
+        theme_mode="dark",
+        repo_path_var=SimpleNamespace(get=lambda: "A"),
+        layer_path_var=SimpleNamespace(get=lambda: ""),
+        file_path_var=SimpleNamespace(get=lambda: ""),
+    )
+    monkeypatch.setattr(gui, "save_state", lambda **_payload: None)
+
+    gui.ContextorGUI.on_closing(controller)
+
+    assert progress_bar.is_cancelled is True
+
+
 def test_closing_gui_does_not_shut_down_unowned_live_client(monkeypatch):
     events = []
     token = "test-gui-owner-token"
~~~

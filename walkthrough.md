# P0 full-analysis lease repair: two gap closures

STATUS

PASS_TARGETED. Both requested gaps are closed. The real Desktop shutdown path now waits, within a bounded limit, for the active analysis task body to finish and for `run_full_analysis_exclusive()` to execute its existing lease-release `finally`. An occupied OS lock with unverifiable owner metadata now has a bounded failure outcome instead of an indefinite wait. Full pytest was not run.

REAL_DESKTOP_SHUTDOWN_PROOF

`test_closing_gui_waits_for_active_analysis_lease_release` uses the real `ContextorGUI.analyze()` path, the real `run_with_progress()` worker, and the real `run_full_analysis_exclusive()` coordinator. A patched facade body holds the acquired lease until the real progress callback observes `progress_bar.is_cancelled`, then delays briefly before raising `AnalysisCancelled`. The test proves that `on_closing()` sets cancellation, waits for the task completion event, and only then destroys the root; no `release_full_analysis()` is used for Desktop owner A. A contender is blocked before shutdown and a `desktop_restart` contender acquires immediately after shutdown returns.

The implementation keeps the existing worker system. `run_with_progress()` returns an event set after the task body (including the coordinator `finally`) completes, before the terminal UI callback. `ContextorGUI.analyze()` stores that event, and `on_closing()` waits at most `FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS = 1.5`. If a custom task ignores cooperative cancellation, the worker remains daemonized and process termination remains the safe fallback for OS-lock release.

UNKNOWN_OWNER_BOUNDED_PROOF

`_lease_owner_state()` now treats missing/corrupt metadata, legacy metadata without executable identity, and unavailable process identity fields as `unknown`; only a verified current process identity is `active`. While the OS lock remains occupied, an unknown owner gets a deadline bounded by the caller timeout and `ORPHAN_RECOVERY_TIMEOUT_SECONDS` (5 seconds by default). On expiry, `acquire_full_analysis(timeout=None)` raises `FullAnalysisBusyError` with `owner could not be verified`. It never deletes, replaces, or forcibly unlocks the lock file.

`test_unknown_owner_metadata_has_bounded_failure` corrupts the lock metadata, removes the sidecar, holds the OS lock, and proves a `timeout=None` acquire fails within the configured bound. `test_legacy_owner_metadata_has_bounded_failure` supplies readable legacy metadata without process identity and proves the same bounded outcome. `test_live_owner_with_no_timeout_is_not_treated_as_unknown` confirms that a verified active owner remains protected even with `timeout=None`; the contender acquires only after the holder dies and the OS releases the lock. The existing orphan recovery race remains atomic because all contenders still compete on the same authoritative OS lock.

FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py`
- `C:\Temp\Contextor_Repo\contextor\ui\gui.py`
- `C:\Temp\Contextor_Repo\contextor\ui\progress_widget.py`
- `C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py`
- `C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py`

`C:\Temp\Contextor_Repo\walkthrough.md` is the required report and is excluded from `FILES_CHANGED` and `ACTUAL_DIFF`.

TESTS_RUN

- `.venv\Scripts\python.exe -m pytest tests/test_full_analysis_coordination.py tests/test_live_desktop_integration.py tests/test_gui_live_startup.py -q` -> `43 passed in 28.50s`.
- `.venv\Scripts\python.exe -m pytest tests/test_progress_widget.py -q` -> `9 passed in 1.16s`.
- `.venv\Scripts\python.exe -m py_compile contextor/core/analysis/full_analysis_coordinator.py contextor/ui/gui.py contextor/ui/progress_widget.py` -> passed.
- Scoped `git diff --check` for the five production/test files -> passed. A whole-tree check reports only intentional whitespace markers inside this report's literal unified diff.
- No Git history/blame/log was used. Full pytest was not run.

REMAINING_RISKS

The normal analysis engine and the focused integration fake observe cancellation through existing progress callbacks. An arbitrary task that never checks cancellation can consume the bounded 1.5-second shutdown wait, after which daemon-worker/process termination remains the safety fallback; no live OS lock is stolen. The default unknown-owner bound is 5 seconds, while caller-provided shorter timeouts win. A fresh manual Desktop/LIVE restart E2E was not run.

ACTUAL_DIFF

~~~diff
diff --git a/contextor/core/analysis/full_analysis_coordinator.py b/contextor/core/analysis/full_analysis_coordinator.py
index 21fd182..957ce5b 100644
--- a/contextor/core/analysis/full_analysis_coordinator.py
+++ b/contextor/core/analysis/full_analysis_coordinator.py
@@ -217,12 +217,17 @@ def _lease_owner_state(
         return "orphaned", f"{description} is not alive"
 
     expected_image = str(metadata.get("executable") or "")
-    if image and expected_image:
-        if Path(image).name.casefold() != Path(expected_image).name.casefold():
-            return "orphaned", f"{description} has a reused process identity"
+    if not expected_image:
+        return "unknown", f"{description} identity metadata unavailable"
+    if not image:
+        return "unknown", f"{description} executable identity unavailable"
+    if Path(image).name.casefold() != Path(expected_image).name.casefold():
+        return "orphaned", f"{description} has a reused process identity"
 
     expected_start = metadata.get("process_start_identity")
-    if expected_start is not None and process_start_identity is not None:
+    if expected_start is not None:
+        if process_start_identity is None:
+            return "unknown", f"{description} start identity unavailable"
         try:
             if int(expected_start) != int(process_start_identity):
                 return "orphaned", f"{description} has a reused process identity"
@@ -308,6 +313,7 @@ def acquire_full_analysis(
     logged_waiting = False
     logged_recovery = False
     orphan_recovery_deadline: float | None = None
+    unknown_owner_deadline: float | None = None
 
     try:
         fd = _prepare_lock_fd(lock_file)
@@ -401,6 +407,7 @@ def acquire_full_analysis(
 
             owner_state, owner_reason = _lease_owner_state(previous_metadata)
             if owner_state == "orphaned":
+                unknown_owner_deadline = None
                 if orphan_recovery_deadline is None:
                     orphan_recovery_deadline = min(
                         deadline
@@ -416,6 +423,23 @@ def acquire_full_analysis(
                         f"Timed out recovering orphaned full analysis lease for "
                         f"{repo_id}"
                     )
+            elif owner_state == "unknown":
+                orphan_recovery_deadline = None
+                if unknown_owner_deadline is None:
+                    unknown_owner_deadline = min(
+                        deadline
+                        if deadline is not None
+                        else time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS,
+                        time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS,
+                    )
+                if time.monotonic() >= unknown_owner_deadline:
+                    raise FullAnalysisBusyError(
+                        f"Timed out waiting because full analysis lease owner "
+                        f"could not be verified for {repo_id}"
+                    )
+            else:
+                orphan_recovery_deadline = None
+                unknown_owner_deadline = None
 
             if (
                 deadline is not None
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 0b50e54..c0aaec5 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -62,6 +62,7 @@ from contextor.ui.theme import (
 
 LIVE_START_MAX_ATTEMPTS = 4
 LIVE_START_RETRY_DELAYS_MS = (1000, 2000, 5000)
+FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS = 1.5
 
 class ContextorGUI:
     """
@@ -691,7 +692,7 @@ class ContextorGUI:
 
         self.progress_bar.is_cancelled = False
 
-        run_with_progress(
+        self._full_analysis_done = run_with_progress(
             self.root,
             self.progress_bar,
             task,
@@ -1139,6 +1140,13 @@ class ContextorGUI:
         if hasattr(self, "progress_bar"):
             self.progress_bar.is_cancelled = True
 
+        full_analysis_done = getattr(self, "_full_analysis_done", None)
+        if full_analysis_done is not None and not full_analysis_done.is_set():
+            # Wait only for the task body. The daemon worker is allowed to
+            # finish UI callbacks after this bound; process exit remains the
+            # safe fallback for a task that ignores cooperative cancellation.
+            full_analysis_done.wait(timeout=FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS)
+
         if getattr(self, "_live_start_retry_after_id", None) is not None:
             if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                 try:
diff --git a/contextor/ui/progress_widget.py b/contextor/ui/progress_widget.py
index efaf2e2..71eee7c 100644
--- a/contextor/ui/progress_widget.py
+++ b/contextor/ui/progress_widget.py
@@ -148,6 +148,9 @@ def run_with_progress(
 
     The task function can take a log_callback argument (optional),
     and a progress_callback argument (optional).
+
+    Returns an event set after the task body has completed, before any
+    queued terminal UI callback runs.
     """
 
     def set_buttons_state(state):
@@ -171,6 +174,7 @@ def run_with_progress(
         "total": 0,
         "filename": "",
     }
+    task_done = threading.Event()
 
     def refresh_eta():
         """Keep ETA alive while an opaque report/write stage is running."""
@@ -278,13 +282,16 @@ def run_with_progress(
             result = task(**kwargs)
         except AnalysisCancelled:
             # Expected outcome of pressing Stop - not a failure.
+            task_done.set()
             root.after(0, finish_cancelled)
         except Exception as exc:
             import traceback
 
             traceback.print_exc()
+            task_done.set()
             root.after(0, finish_error, exc)
         else:
+            task_done.set()
             root.after(0, finish_success, result)
 
     set_buttons_state("disabled")
@@ -305,3 +312,4 @@ def run_with_progress(
 
     thread = threading.Thread(target=worker, daemon=True)
     thread.start()
+    return task_done
diff --git a/tests/test_full_analysis_coordination.py b/tests/test_full_analysis_coordination.py
index 5bdb653..0e43d0e 100644
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -11,6 +11,7 @@ Complete test suite certifying the single-writer full-analysis coordinator:
 
 from __future__ import annotations
 
+import json
 import multiprocessing
 import os
 import threading
@@ -23,8 +24,11 @@ import pytest
 from contextor.core.analysis.full_analysis_coordinator import (
     FullAnalysisBusyError,
     FullAnalysisLease,
+    _lease_metadata_path,
+    _prepare_lock_fd,
     _resolve_lock_path,
     _try_lock_fd,
+    _unlock_fd,
     acquire_full_analysis,
     release_full_analysis,
     run_full_analysis_exclusive,
@@ -166,18 +170,25 @@ def _worker_try_acquire(repo_path: str, owner: str, timeout: float, result_queue
 def _worker_try_acquire_with_log(
     repo_path: str,
     owner: str,
-    timeout: float,
+    timeout: float | None,
     result_queue,
+    active_owner_event=None,
 ):
     """Attempt a lease and return the owner diagnostic observed while waiting."""
     messages: list[str] = []
+
+    def record(message: str):
+        messages.append(message)
+        if active_owner_event is not None and "valid active owner" in message:
+            active_owner_event.set()
+
     try:
         lease = acquire_full_analysis(
             repo_path,
             owner=owner,
             timeout=timeout,
             poll_interval=0.05,
-            log=messages.append,
+            log=record,
         )
         release_full_analysis(lease)
         result_queue.put({"status": "ok", "owner": owner, "messages": messages})
@@ -338,6 +349,144 @@ def test_live_owner_is_reported_and_cannot_be_stolen(tmp_path: Path, isolated_di
         p_a.join(timeout=3.0)
 
 
+def test_live_owner_with_no_timeout_is_not_treated_as_unknown(
+    tmp_path: Path,
+    isolated_dirs,
+):
+    """A verified live owner may wait without an artificial unknown-owner deadline."""
+    repo = tmp_path / "repo_live_owner_no_timeout"
+    repo.mkdir()
+
+    ctx = multiprocessing.get_context("spawn")
+    ready_a = ctx.Event()
+    results_a = ctx.Queue()
+    results_b = ctx.Queue()
+    active_owner_b = ctx.Event()
+    p_a = ctx.Process(
+        target=_worker_os_lock_hold,
+        args=(str(repo), "live_owner", ready_a, results_a, 15.0),
+    )
+    p_b = None
+    p_a.start()
+
+    try:
+        assert ready_a.wait(timeout=15.0)
+        assert results_a.get(timeout=2.0)["status"] == "acquired"
+
+        p_b = ctx.Process(
+            target=_worker_try_acquire_with_log,
+            args=(str(repo), "contender", None, results_b, active_owner_b),
+        )
+        p_b.start()
+        assert active_owner_b.wait(timeout=3.0)
+
+        p_a.terminate()
+        p_a.join(timeout=3.0)
+
+        result_b = results_b.get(timeout=3.0)
+        assert result_b["status"] == "ok", result_b
+        assert any(
+            "valid active owner" in message and "live_owner" in message
+            for message in result_b["messages"]
+        ), result_b
+    finally:
+        if p_b is not None and p_b.is_alive():
+            p_b.terminate()
+        if p_b is not None:
+            p_b.join(timeout=3.0)
+        if p_a.is_alive():
+            p_a.terminate()
+        p_a.join(timeout=3.0)
+
+
+def test_unknown_owner_metadata_has_bounded_failure(
+    tmp_path: Path,
+    monkeypatch,
+):
+    """An occupied lock with unreadable metadata cannot create an infinite wait."""
+    from contextor.core.analysis import full_analysis_coordinator as fac
+
+    monkeypatch.setattr(fac, "ORPHAN_RECOVERY_TIMEOUT_SECONDS", 0.2)
+    repo = tmp_path / "repo_unknown_owner"
+    repo.mkdir()
+    lock_file, _, _ = _resolve_lock_path(repo)
+    fd = _prepare_lock_fd(lock_file)
+    assert _try_lock_fd(fd)
+
+    try:
+        os.ftruncate(fd, 0)
+        os.lseek(fd, 0, os.SEEK_SET)
+        os.write(fd, b"{invalid metadata")
+        os.fsync(fd)
+        _lease_metadata_path(lock_file).unlink(missing_ok=True)
+
+        messages: list[str] = []
+        started = time.monotonic()
+        with pytest.raises(
+            FullAnalysisBusyError,
+            match="owner could not be verified",
+        ):
+            acquire_full_analysis(
+                repo,
+                owner="unknown_contender",
+                timeout=None,
+                poll_interval=0.02,
+                log=messages.append,
+            )
+
+        assert time.monotonic() - started < 1.0
+        assert any("owner could not be verified" in message for message in messages)
+    finally:
+        _unlock_fd(fd)
+
+
+def test_legacy_owner_metadata_has_bounded_failure(
+    tmp_path: Path,
+    monkeypatch,
+):
+    """Legacy metadata without process identity is unknown, not silently live."""
+    from contextor.core.analysis import full_analysis_coordinator as fac
+
+    monkeypatch.setattr(fac, "ORPHAN_RECOVERY_TIMEOUT_SECONDS", 0.2)
+    repo = tmp_path / "repo_legacy_owner"
+    repo.mkdir()
+    lock_file, _, _ = _resolve_lock_path(repo)
+    fd = _prepare_lock_fd(lock_file)
+    assert _try_lock_fd(fd)
+
+    try:
+        legacy_metadata = {
+            "pid": os.getpid(),
+            "token": "legacy-token",
+            "owner": "legacy_holder",
+            "repo_id": "legacy-repo",
+            "timestamp": time.time(),
+        }
+        os.ftruncate(fd, 0)
+        os.lseek(fd, 0, os.SEEK_SET)
+        os.write(fd, json.dumps(legacy_metadata).encode("utf-8"))
+        os.fsync(fd)
+        _lease_metadata_path(lock_file).unlink(missing_ok=True)
+        monkeypatch.setattr(fac, "_read_lease_metadata", lambda _fd: legacy_metadata)
+
+        messages: list[str] = []
+        with pytest.raises(
+            FullAnalysisBusyError,
+            match="owner could not be verified",
+        ):
+            acquire_full_analysis(
+                repo,
+                owner="legacy_contender",
+                timeout=None,
+                poll_interval=0.02,
+                log=messages.append,
+            )
+
+        assert any("identity metadata unavailable" in message for message in messages)
+    finally:
+        _unlock_fd(fd)
+
+
 def test_orphan_recovery_is_atomic_for_two_contenders(
     tmp_path: Path,
     isolated_dirs,
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index b8eda54..4f7976b 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -1,10 +1,18 @@
 """Desktop adapter tests for publishing and watching shared canonical LIVE state."""
 
+import threading
+import time
 from types import SimpleNamespace
 from unittest.mock import MagicMock
 
 import pytest
 
+from contextor.core.analysis.full_analysis_coordinator import (
+    FullAnalysisBusyError,
+    acquire_full_analysis,
+    release_full_analysis,
+)
+from contextor.core.errors import AnalysisCancelled
 from contextor.core.live_state.watcher import DesktopLiveWatcher
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.core.repository_identity import read_repository_identity
@@ -561,6 +569,108 @@ def test_closing_gui_cancels_active_analysis_before_cleanup(monkeypatch):
     assert progress_bar.is_cancelled is True
 
 
+def test_closing_gui_waits_for_active_analysis_lease_release(
+    tmp_path,
+    monkeypatch,
+):
+    """Desktop close cancels the real worker before the next owner acquires."""
+    import contextor.core.live_state as live_state
+
+    repo = tmp_path / "repo_shutdown_lease"
+    repo.mkdir()
+    analysis_started = threading.Event()
+    cancellation_observed = threading.Event()
+
+    class FakeRoot:
+        def __init__(self):
+            self.destroyed = False
+
+        def after(self, delay, callback, *args):
+            if delay == 0:
+                callback(*args)
+
+        def geometry(self):
+            return "900x700+10+20"
+
+        def destroy(self):
+            self.destroyed = True
+
+    class FakeProgress:
+        def __init__(self):
+            self.is_cancelled = False
+            self.indet = SimpleNamespace(
+                start=lambda *_args: None,
+                stop=lambda: None,
+            )
+            self.det = {}
+            self.flicker_label = SimpleNamespace(config=lambda **_kwargs: None)
+            self.time_label = SimpleNamespace(config=lambda **_kwargs: None)
+
+    def fake_analyze_project(_path, *, progress_callback=None, **_kwargs):
+        assert progress_callback is not None
+        analysis_started.set()
+        while progress_callback(0, 1, "module.py"):
+            time.sleep(0.01)
+        cancellation_observed.set()
+        time.sleep(0.15)
+        raise AnalysisCancelled("shutdown cancellation")
+
+    monkeypatch.setattr(live_state, "connect", lambda _path: None)
+    monkeypatch.setattr(
+        gui.ContextorFacade,
+        "analyze_project",
+        fake_analyze_project,
+    )
+    monkeypatch.setattr(gui, "close_cmd_log", lambda: None)
+    monkeypatch.setattr(gui, "save_state", lambda **_payload: None)
+
+    root = FakeRoot()
+    progress_bar = FakeProgress()
+    controller = SimpleNamespace(
+        root=root,
+        progress_bar=progress_bar,
+        log_box=None,
+        cpu_indicator=None,
+        stop_btn=None,
+        live_clients={},
+        live_client=None,
+        live_watchers={},
+        live_event_feeds={},
+        theme_mode="dark",
+        repo_path_var=SimpleNamespace(get=lambda: str(repo)),
+        layer_path_var=SimpleNamespace(get=lambda: ""),
+        file_path_var=SimpleNamespace(get=lambda: ""),
+        _busy_buttons=lambda: [],
+    )
+
+    gui.ContextorGUI.analyze(controller)
+    assert analysis_started.wait(timeout=2.0)
+
+    with pytest.raises(FullAnalysisBusyError):
+        acquire_full_analysis(
+            repo,
+            owner="contender_before_shutdown",
+            timeout=0.1,
+            poll_interval=0.01,
+        )
+
+    gui.ContextorGUI.on_closing(controller)
+
+    assert cancellation_observed.is_set()
+    assert controller._full_analysis_done.is_set()
+    assert root.destroyed is True
+
+    restarted_lease = acquire_full_analysis(
+        repo,
+        owner="desktop_restart",
+        timeout=0.5,
+    )
+    try:
+        assert restarted_lease.owner == "desktop_restart"
+    finally:
+        release_full_analysis(restarted_lease)
+
+
 def test_closing_gui_does_not_shut_down_unowned_live_client(monkeypatch):
     events = []
     token = "test-gui-owner-token"
~~~

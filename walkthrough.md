CPA_BACKEND_OWNER_O3H_RETRY_AND_VISIBLE_FAILURE

STATUS=PASS
HEAD=41d4340d6547bd2ccede76a6cd05c32bf4941c91

FILES_CHANGED:
- C:\Temp\Contextor_Repo\contextor\ui\gui.py
- C:\Temp\Contextor_Repo\tests\test_gui_backend_owner.py

LITERAL_IMPLEMENTATION_MATCH=YES
RETRY_MAX_ATTEMPTS=3
RETRY_DELAYS=0.5 seconds, 1.0 seconds
FOREIGN_OWNER_RETRY=NO
DUPLICATE_WORKER_SUPPRESSION=PASS; existing live-thread guard retained and covered by focused test
CLOSE_DURING_RETRY=PASS; state becomes aborted, no subsequent claim or terminal failure status
VISIBLE_FAILURE_CHANNEL=PASS; retry/failure/recovery published only through _set_live_status(category="MCP_CALL")
RECOVERY_VISIBLE=PASS; successful retry emits "Backend ownership restored."
CLAIM_CORE_UNCHANGED=YES; _claim_current_backend_for_desktop and _claim_backend_owner_on_startup unchanged
OUT_OF_SCOPE_PRODUCTION_SEMANTICS_UNCHANGED=YES; backend lifecycle, ownership schema, LIVE ownership, restart lifecycle, on_closing, autostart, and CLI untouched

TARGETED_TESTS=PASS
COMMAND=.\.venv\Scripts\python.exe -m pytest -q tests\test_gui_backend_owner.py tests\test_gui_backend_restart.py tests\test_gui_live_startup.py
RESULT=37 passed, 1 warning in 10.51s
WARNING=AuthlibDeprecationWarning from installed FastMCP/Authlib dependency; no test failures

CONTEXTOR_POST_EDIT=PASS
FETCHED=ContextorGUI.__init__; ContextorGUI._start_backend_owner_claim; ContextorGUI._claim_backend_owner_on_startup; ContextorGUI.on_closing
CANONICAL_STATE=fresh
WORKSPACE_SYNC=verified
CANONICAL_REVISION=1636
PROVENANCE=live
LIVE_CONTINUITY=continuous
RESYNC_REQUIRED=false
WATCHER_EVIDENCE=desktop_watcher UPDATED gui.py at revision 1634 and test_gui_backend_owner.py at revisions 1635-1636
POST_EDIT_SYNTAX_ERRORS=0
POST_EDIT_NAME_COLLISIONS=0
POST_EDIT_CYCLES=0

IMPLEMENTATION_RESULT=PASS; requested retry, visible failure, success, foreign-owner terminal, close-abort, duplicate-worker, and messagebox regression cases are covered
TESTS_RUN=ONLY the three requested targeted test files
FULL_REPOSITORY_ANALYSIS=NOT_RUN

FULL_DIFFS
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 98a0225..96634ed 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -39,6 +39,7 @@ from contextor.core.repository_identity import (
 from contextor.core.paths import prune_startup_caches
 from contextor.repo_generator import run_repo_generator
 from contextor.mcp_backend_control import (
+    BackendOwnerAlreadyClaimed,
     BackendOwnerInstanceRevoked,
     claim_backend_owner,
     get_backend_status,
@@ -78,6 +79,11 @@ from contextor.ui.theme import (
 LIVE_START_MAX_ATTEMPTS = 4
 LIVE_START_RETRY_DELAYS_MS = (1000, 2000, 5000)
 FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS = 1.5
+BACKEND_OWNER_CLAIM_MAX_ATTEMPTS = 3
+BACKEND_OWNER_CLAIM_RETRY_DELAYS_SECONDS = (
+    0.5,
+    1.0,
+)
 
 class ContextorGUI:
     """
@@ -122,6 +128,8 @@ class ContextorGUI:
         self.backend_owner_claim = None
         self._backend_owner_claim_error = None
         self._backend_owner_claim_thread = None
+        self._backend_owner_claim_state = "idle"
+        self._backend_owner_claim_attempt = 0
         self.live_client = None
         self.live_clients = {}
         self.live_watcher = None
@@ -243,10 +251,90 @@ class ContextorGUI:
             return
 
         def worker():
-            try:
-                self._claim_backend_owner_on_startup()
-            except Exception as exc:
-                self._backend_owner_claim_error = exc
+            self._backend_owner_claim_state = "claiming"
+            self._backend_owner_claim_attempt = 0
+
+            for attempt in range(
+                1,
+                BACKEND_OWNER_CLAIM_MAX_ATTEMPTS + 1,
+            ):
+                if getattr(self, "_closing", False):
+                    self._backend_owner_claim_state = "aborted"
+                    return
+
+                self._backend_owner_claim_attempt = attempt
+
+                try:
+                    claim = self._claim_backend_owner_on_startup()
+
+                except Exception as exc:
+                    self._backend_owner_claim_error = exc
+
+                    terminal = (
+                        isinstance(
+                            exc,
+                            BackendOwnerAlreadyClaimed,
+                        )
+                        or attempt
+                        >= BACKEND_OWNER_CLAIM_MAX_ATTEMPTS
+                    )
+
+                    if terminal:
+                        self._backend_owner_claim_state = "failed"
+
+                        self._set_live_status(
+                            f"Backend ownership failed: {exc}",
+                            category="MCP_CALL",
+                        )
+                        return
+
+                    self._backend_owner_claim_state = "retrying"
+
+                    self._set_live_status(
+                        (
+                            "Backend ownership unavailable; "
+                            f"retrying ({attempt + 1}/"
+                            f"{BACKEND_OWNER_CLAIM_MAX_ATTEMPTS})..."
+                        ),
+                        category="MCP_CALL",
+                    )
+
+                    delay = (
+                        BACKEND_OWNER_CLAIM_RETRY_DELAYS_SECONDS[
+                            attempt - 1
+                        ]
+                    )
+
+                    deadline = time.monotonic() + delay
+
+                    while time.monotonic() < deadline:
+                        if getattr(self, "_closing", False):
+                            self._backend_owner_claim_state = "aborted"
+                            return
+
+                        remaining = deadline - time.monotonic()
+
+                        time.sleep(
+                            min(
+                                0.05,
+                                max(0.0, remaining),
+                            )
+                        )
+
+                    self._backend_owner_claim_state = "claiming"
+                    continue
+
+                self.backend_owner_claim = claim
+                self._backend_owner_claim_error = None
+                self._backend_owner_claim_state = "claimed"
+
+                if attempt > 1:
+                    self._set_live_status(
+                        "Backend ownership restored.",
+                        category="MCP_CALL",
+                    )
+
+                return
 
         thread = threading.Thread(
             target=worker,
diff --git a/tests/test_gui_backend_owner.py b/tests/test_gui_backend_owner.py
index 18724c3..c15cc88 100644
--- a/tests/test_gui_backend_owner.py
+++ b/tests/test_gui_backend_owner.py
@@ -4,7 +4,10 @@ from types import SimpleNamespace
 
 import pytest
 
-from contextor.mcp_backend_control import BackendOwnerInstanceRevoked
+from contextor.mcp_backend_control import (
+    BackendOwnerAlreadyClaimed,
+    BackendOwnerInstanceRevoked,
+)
 from contextor.ui import gui
 
 
@@ -25,13 +28,20 @@ def _status(state, ready=False, record=None):
 
 
 def _controller():
+    status_calls = []
     controller = SimpleNamespace(
         desktop_instance_id="desktop-instance",
         backend_owner_token="backend-owner-token",
         backend_owner_claim=None,
         _backend_owner_claim_error=None,
         _backend_owner_claim_thread=None,
+        _backend_owner_claim_state="idle",
+        _backend_owner_claim_attempt=0,
         _closing=False,
+        _status_calls=status_calls,
+        _set_live_status=lambda *args, **kwargs: status_calls.append(
+            (args, kwargs)
+        ),
     )
     controller._claim_current_backend_for_desktop = lambda: (
         gui.ContextorGUI._claim_current_backend_for_desktop(controller)
@@ -39,6 +49,33 @@ def _controller():
     return controller
 
 
+def _fast_retry_clock(monkeypatch, controller=None):
+    clock = [0.0]
+    sleeps = []
+
+    def monotonic():
+        return clock[0]
+
+    def sleep(delay):
+        sleeps.append(delay)
+        if controller is not None:
+            controller._closing = True
+            clock[0] += 10.0
+        else:
+            clock[0] += delay
+
+    monkeypatch.setattr(gui.time, "monotonic", monotonic)
+    monkeypatch.setattr(gui.time, "sleep", sleep)
+    return clock, sleeps
+
+
+def _published_statuses(controller):
+    return [
+        (args[0], kwargs)
+        for args, kwargs in controller._status_calls
+    ]
+
+
 class _FakeVar:
     def __init__(self, value=""):
         self.value = value
@@ -98,6 +135,8 @@ def test_init_creates_separate_live_and_backend_owner_identities(monkeypatch):
     assert controller.backend_owner_claim is None
     assert controller._backend_owner_claim_error is None
     assert controller._backend_owner_claim_thread is None
+    assert controller._backend_owner_claim_state == "idle"
+    assert controller._backend_owner_claim_attempt == 0
 
 
 def test_claim_current_backend_uses_exact_desktop_owner_contract(monkeypatch):
@@ -289,9 +328,20 @@ def test_start_backend_owner_claim_runs_in_nonblocking_daemon_thread():
     assert not thread.is_alive()
 
 
-def test_start_backend_owner_claim_stores_worker_exception():
+def test_start_backend_owner_claim_stores_worker_exception(monkeypatch):
     controller = _controller()
     expected = RuntimeError("claim failed")
+    monkeypatch.setattr(gui, "BACKEND_OWNER_CLAIM_MAX_ATTEMPTS", 1)
+    monkeypatch.setattr(
+        gui.messagebox,
+        "showerror",
+        lambda *_args, **_kwargs: pytest.fail("worker must not show a messagebox"),
+    )
+    monkeypatch.setattr(
+        gui.messagebox,
+        "showinfo",
+        lambda *_args, **_kwargs: pytest.fail("worker must not show a messagebox"),
+    )
 
     def fail_claim():
         raise expected
@@ -303,6 +353,252 @@ def test_start_backend_owner_claim_stores_worker_exception():
     controller._backend_owner_claim_thread.join(timeout=1.0)
     assert controller._backend_owner_claim_thread.is_alive() is False
     assert controller._backend_owner_claim_error is expected
+    assert controller._backend_owner_claim_state == "failed"
+    assert controller._backend_owner_claim_attempt == 1
+    assert controller._status_calls == [
+        (("Backend ownership failed: claim failed",), {"category": "MCP_CALL"})
+    ]
+
+
+def test_owner_claim_first_attempt_success_has_no_retry_or_failure_status():
+    controller = _controller()
+    claim = SimpleNamespace(backend_instance_id="instance-1")
+    calls = []
+    controller._claim_backend_owner_on_startup = lambda: calls.append(1) or claim
+
+    gui.ContextorGUI._start_backend_owner_claim(controller)
+
+    thread = controller._backend_owner_claim_thread
+    thread.join(timeout=1.0)
+
+    assert not thread.is_alive()
+    assert calls == [1]
+    assert controller.backend_owner_claim is claim
+    assert controller._backend_owner_claim_state == "claimed"
+    assert controller._backend_owner_claim_attempt == 1
+    assert controller._backend_owner_claim_error is None
+    assert _published_statuses(controller) == []
+
+
+def test_owner_claim_transient_failure_then_success_retries_once(monkeypatch):
+    controller = _controller()
+    _, sleeps = _fast_retry_clock(monkeypatch)
+    temporary = RuntimeError("temporary")
+    claim = SimpleNamespace(backend_instance_id="instance-1")
+    call_times = []
+
+    def claim_on_startup():
+        call_times.append(gui.time.monotonic())
+        if len(call_times) == 1:
+            raise temporary
+        return claim
+
+    controller._claim_backend_owner_on_startup = claim_on_startup
+    gui.ContextorGUI._start_backend_owner_claim(controller)
+    thread = controller._backend_owner_claim_thread
+    thread.join(timeout=1.0)
+
+    assert not thread.is_alive()
+    assert len(call_times) == 2
+    assert call_times[1] - call_times[0] == pytest.approx(0.5)
+    assert controller.backend_owner_claim is claim
+    assert controller._backend_owner_claim_state == "claimed"
+    assert controller._backend_owner_claim_attempt == 2
+    assert controller._backend_owner_claim_error is None
+    assert _published_statuses(controller) == [
+        (
+            "Backend ownership unavailable; retrying (2/3)...",
+            {"category": "MCP_CALL"},
+        ),
+        (
+            "Backend ownership restored.",
+            {"category": "MCP_CALL"},
+        ),
+    ]
+    assert sum(sleeps) == pytest.approx(0.5)
+
+
+def test_owner_claim_two_failures_then_success_traverses_both_delays(monkeypatch):
+    controller = _controller()
+    _, sleeps = _fast_retry_clock(monkeypatch)
+    errors = [RuntimeError("temporary-1"), RuntimeError("temporary-2")]
+    claim = SimpleNamespace(backend_instance_id="instance-1")
+    call_times = []
+
+    def claim_on_startup():
+        call_times.append(gui.time.monotonic())
+        if len(call_times) <= 2:
+            raise errors[len(call_times) - 1]
+        return claim
+
+    controller._claim_backend_owner_on_startup = claim_on_startup
+    gui.ContextorGUI._start_backend_owner_claim(controller)
+    thread = controller._backend_owner_claim_thread
+    thread.join(timeout=1.0)
+
+    assert not thread.is_alive()
+    assert len(call_times) == 3
+    assert call_times[1] - call_times[0] == pytest.approx(0.5)
+    assert call_times[2] - call_times[1] == pytest.approx(1.0)
+    assert sum(sleeps) == pytest.approx(1.5)
+    assert controller.backend_owner_claim is claim
+    assert controller._backend_owner_claim_state == "claimed"
+    assert controller._backend_owner_claim_attempt == 3
+    assert controller._backend_owner_claim_error is None
+    assert _published_statuses(controller) == [
+        (
+            "Backend ownership unavailable; retrying (2/3)...",
+            {"category": "MCP_CALL"},
+        ),
+        (
+            "Backend ownership unavailable; retrying (3/3)...",
+            {"category": "MCP_CALL"},
+        ),
+        (
+            "Backend ownership restored.",
+            {"category": "MCP_CALL"},
+        ),
+    ]
+
+
+def test_owner_claim_three_failures_emits_one_terminal_failure(monkeypatch):
+    controller = _controller()
+    _, sleeps = _fast_retry_clock(monkeypatch)
+    errors = [
+        RuntimeError("temporary-1"),
+        RuntimeError("temporary-2"),
+        RuntimeError("final"),
+    ]
+    calls = []
+
+    def fail_claim():
+        calls.append(1)
+        raise errors[len(calls) - 1]
+
+    controller._claim_backend_owner_on_startup = fail_claim
+    gui.ContextorGUI._start_backend_owner_claim(controller)
+    thread = controller._backend_owner_claim_thread
+    thread.join(timeout=1.0)
+
+    assert not thread.is_alive()
+    assert calls == [1, 1, 1]
+    assert controller._backend_owner_claim_state == "failed"
+    assert controller._backend_owner_claim_attempt == 3
+    assert controller._backend_owner_claim_error is errors[-1]
+    assert _published_statuses(controller) == [
+        (
+            "Backend ownership unavailable; retrying (2/3)...",
+            {"category": "MCP_CALL"},
+        ),
+        (
+            "Backend ownership unavailable; retrying (3/3)...",
+            {"category": "MCP_CALL"},
+        ),
+        (
+            "Backend ownership failed: final",
+            {"category": "MCP_CALL"},
+        ),
+    ]
+    assert sum(sleeps) == pytest.approx(1.5)
+
+
+def test_foreign_owner_is_terminal_without_retry_or_messagebox(monkeypatch):
+    controller = _controller()
+    error = BackendOwnerAlreadyClaimed("foreign owner")
+    calls = []
+
+    def fail_claim():
+        calls.append(1)
+        raise error
+
+    def fail_messagebox(*_args, **_kwargs):
+        pytest.fail("owner worker must not show a messagebox")
+
+    controller._claim_backend_owner_on_startup = fail_claim
+    monkeypatch.setattr(gui.messagebox, "showerror", fail_messagebox)
+    monkeypatch.setattr(gui.messagebox, "showinfo", fail_messagebox)
+    monkeypatch.setattr(
+        gui.time,
+        "sleep",
+        lambda _delay: pytest.fail("foreign owner must not be retried"),
+    )
+
+    gui.ContextorGUI._start_backend_owner_claim(controller)
+    thread = controller._backend_owner_claim_thread
+    thread.join(timeout=1.0)
+
+    assert not thread.is_alive()
+    assert calls == [1]
+    assert controller._backend_owner_claim_state == "failed"
+    assert controller._backend_owner_claim_attempt == 1
+    assert controller._backend_owner_claim_error is error
+    assert _published_statuses(controller) == [
+        (
+            "Backend ownership failed: foreign owner",
+            {"category": "MCP_CALL"},
+        )
+    ]
+
+
+def test_closing_during_retry_delay_aborts_without_final_failure(monkeypatch):
+    controller = _controller()
+    _, sleeps = _fast_retry_clock(monkeypatch, controller=controller)
+    temporary = RuntimeError("temporary")
+    calls = []
+
+    def fail_claim():
+        calls.append(1)
+        raise temporary
+
+    controller._claim_backend_owner_on_startup = fail_claim
+    gui.ContextorGUI._start_backend_owner_claim(controller)
+    thread = controller._backend_owner_claim_thread
+    thread.join(timeout=1.0)
+
+    assert not thread.is_alive()
+    assert calls == [1]
+    assert sleeps
+    assert controller._backend_owner_claim_state == "aborted"
+    assert controller._backend_owner_claim_attempt == 1
+    assert controller._backend_owner_claim_error is temporary
+    assert _published_statuses(controller) == [
+        (
+            "Backend ownership unavailable; retrying (2/3)...",
+            {"category": "MCP_CALL"},
+        )
+    ]
+
+
+def test_duplicate_owner_worker_is_suppressed_while_first_is_alive():
+    controller = _controller()
+    entered = threading.Event()
+    release = threading.Event()
+    calls = []
+    claim = SimpleNamespace(backend_instance_id="instance-1")
+
+    def claim_on_startup():
+        calls.append(1)
+        entered.set()
+        release.wait(timeout=2.0)
+        return claim
+
+    controller._claim_backend_owner_on_startup = claim_on_startup
+    gui.ContextorGUI._start_backend_owner_claim(controller)
+    first_thread = controller._backend_owner_claim_thread
+
+    assert entered.wait(timeout=1.0)
+    gui.ContextorGUI._start_backend_owner_claim(controller)
+
+    assert controller._backend_owner_claim_thread is first_thread
+    assert first_thread.is_alive()
+    assert calls == [1]
+    release.set()
+    first_thread.join(timeout=1.0)
+
+    assert not first_thread.is_alive()
+    assert calls == [1]
+    assert controller.backend_owner_claim is claim
+    assert controller._backend_owner_claim_state == "claimed"
 
 
 def test_post_paint_starts_backend_claim_before_cleanup_and_live(monkeypatch, tmp_path):

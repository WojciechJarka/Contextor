# CPA_BACKEND_OWNER_O3_DESKTOP_OWNER_ADAPTER

STATUS=IMPLEMENTATION_PASS_TARGETED_TESTS
HEAD=161cc30073e785837ee1477565d6824abab9dae0

FILES_CHANGED:
- contextor/ui/gui.py
- tests/test_gui_backend_owner.py
- tests/test_gui_backend_restart.py
- tests/test_gui_live_startup.py

LITERAL_IMPLEMENTATION_MATCH=YES
DESKTOP_OWNER_IDENTITY=PASS
STARTUP_OWNER_ACQUIRE=PASS
REVOKED_INSTANCE_RELAUNCH=PASS
RESTART_OWNER_PRESERVATION=PASS
DESKTOP_CLOSE_OWNER_RELEASE=NO
DESKTOP_CLOSE_STOP_BACKEND=NO
LIVE_SHUTDOWN_SEMANTICS_UNCHANGED=YES
TARGETED_TESTS=PASS
CONTEXTOR_POST_EDIT=PASS
IMPLEMENTATION_RESULT=PASS_IMPLEMENTATION; DESKTOP_CLOSE_RUNTIME_CONFIRMATION_PENDING_DESKTOP_RESTART

DISCOVERY
- Pre-edit get_file_edit_context: contextor.ui.gui, canonical_state=fresh, workspace_sync=verified, canonical_revision=1628; syntax diagnostics checked_and_none.
- Pre-edit module blast radius: 45 artifacts; direct consumers included tests.test_gui_backend_restart, tests.test_gui_live_startup, and tests.test_live_desktop_integration. Module direct/downstream consumer evidence was read from canonical LIVE.
- Pre-edit artifact blast radius was queried for __init__, _start_post_paint_tasks, _restart_backend, and on_closing. Static artifact-consumer evidence identified tests.test_gui_live_startup and tests.test_live_desktop_integration for close/startup paths. These results are canonical static evidence and do not claim dynamic Python completeness.
- Pre-edit get_symbol_call_context was read for all four methods. It reports intra-module edges only. get_symbol_lineage for _restart_backend resolved complete at revision 1628; nested run_with_progress was a dynamic boundary and one surrounding call result was unresolved, so no broader caller claim is inferred from that lineage.
- contextor_fact_lineage documentation was considered. Its supported families are Contextor canonical fact pipelines (artifact_consumption, syntax_diagnostics, symbol_calls), not this Desktop backend-owner adapter; it was not used as application-code ownership evidence.
- Literal local source anchors at HEAD matched the prompt: control import block; adjacent owner_token/desktop_instance_id assignments; _start_post_paint_tasks closing guard; existing restart lifecycle through identity verification; on_closing boundary. test_gui_backend_owner.py did not exist at HEAD. No source drift was found.

IMPLEMENTATION
- Added BackendOwnerInstanceRevoked and claim_backend_owner to the existing mcp_backend_control import; did not import release_backend_owner.
- Kept owner_token as the LIVE token. Added an independent backend_owner_token, claim state/error/thread fields after desktop_instance_id.
- Added the exact desktop claim helper and startup acquisition flow. Revoked instances are only polled for normal self-termination; the replacement is then started and claimed by exact instance identity. This recovery path does not call stop_backend.
- Added the startup owner claim worker as a daemon thread; exceptions are stored in _backend_owner_claim_error and no Tk widget is accessed by that worker.
- Started the owner claim from _start_post_paint_tasks after the closing guard, before cache cleanup and LIVE startup.
- Restart now claims the verified replacement backend using Desktop identity/token, checks exact instance match, returns the claim with before/after status, and stores it on success. Claim exceptions go to existing on_error; no rollback or release was added.
- ContextorGUI.on_closing was not modified. The existing LIVE close path, including its LIVE claim/shutdown behavior, remains unchanged. The NO fields above refer specifically to the persistent backend owner claim and backend instance.
- Runtime confirmation of Desktop process exit and backend watchdog shutdown remains pending a later Desktop restart/close certification; this implementation turn did not restart Desktop or MCP.

TARGETED_TESTS
Command:
.\.venv\Scripts\python.exe -m pytest tests\test_gui_backend_owner.py tests\test_gui_backend_restart.py tests\test_gui_live_startup.py tests\test_live_desktop_integration.py -q

Final result: 55 passed, 1 AuthlibDeprecationWarning, 9.26s.
The initial run had 4 test-harness failures because the SimpleNamespace controller omitted the bound helper method; the fixture was corrected to call the production helper and the same exact targeted command then passed. No production change was made in response to those failures.
No full repository pytest suite was run.

CONTEXTOR_POST_EDIT
- All seven requested symbols were fetched after the edit: ContextorGUI.__init__, _claim_current_backend_for_desktop, _claim_backend_owner_on_startup, _start_backend_owner_claim, _start_post_paint_tasks, _restart_backend, and on_closing.
- Each fetch returned canonical_state=fresh and workspace_sync=verified at canonical_revision=1633.
- Desktop watcher update events: gui.py revision 1629; test_gui_backend_owner.py revisions 1630 and 1633; test_gui_backend_restart.py revision 1631; test_gui_live_startup.py revision 1632. The second owner-test event reflects the test-fixture correction.
- get_live_events(after_revision=1632): latest_revision=1633, continuity=continuous, resync_required=false.
- No manual update_file was called.
- git diff --check passed for the changed tracked source/test files.
- No test was added for on_closing source-string absence, per instruction.

EVIDENCE_CLASSIFICATION
DIRECT_EVIDENCE:
- Exact Contextor implementation fetches at revision 1633 with verified workspace sync.
- Watcher events and continuity/resync metadata listed above.
- Targeted pytest output: 55 passed.
CODE_PATH_PROVED:
- Startup owner claim and replacement relaunch are performed by the worker and public backend lifecycle APIs as specified.
- Restart claims only after readiness and identity verification; error propagation does not add another stop or rollback.
- on_closing has no backend owner release or backend stop change in this diff.
INFERENCE:
- No runtime Desktop-close behavior is claimed from source inspection alone.
UNKNOWN:
- Post-Desktop-restart runtime confirmation of owner-lost self-termination.

FILES_CHANGED=4 source/test files listed above (walkthrough.md is the required report and is excluded)
DIFFS=FULL_DIFFS_BELOW
TESTS_RUN=ONLY_THE_FOUR_TARGETED_FILES_ABOVE

FULL_DIFFS

### contextor/ui/gui.py

FULL_DIFF_BEGIN
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -39,6 +39,8 @@
 from contextor.core.paths import prune_startup_caches
 from contextor.repo_generator import run_repo_generator
 from contextor.mcp_backend_control import (
+    BackendOwnerInstanceRevoked,
+    claim_backend_owner,
     get_backend_status,
     start_backend,
     stop_backend,
@@ -116,6 +118,10 @@
         self.parser_win = None
         self.owner_token = uuid.uuid4().hex
         self.desktop_instance_id = uuid.uuid4().hex
+        self.backend_owner_token = uuid.uuid4().hex
+        self.backend_owner_claim = None
+        self._backend_owner_claim_error = None
+        self._backend_owner_claim_thread = None
         self.live_client = None
         self.live_clients = {}
         self.live_watcher = None
@@ -138,9 +144,123 @@
         self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
         self.root.after(50, self._start_post_paint_tasks)
 
+    def _claim_current_backend_for_desktop(self):
+        claim = claim_backend_owner(
+            host_owner_identity=self.desktop_instance_id,
+            host_kind="desktop",
+            owner_token=self.backend_owner_token,
+            probe_timeout=2.0,
+            lock_timeout=5.0,
+        )
+
+        self.backend_owner_claim = claim
+        self._backend_owner_claim_error = None
+
+        return claim
+
+    def _claim_backend_owner_on_startup(self):
+        status = start_backend(
+            timeout=20.0,
+            probe_timeout=2.0,
+        )
+
+        if (
+            not status.ready
+            or status.record is None
+        ):
+            raise RuntimeError(
+                "persistent MCP backend did not become authenticated and ready"
+            )
+
+        try:
+            claim = self._claim_current_backend_for_desktop()
+
+        except BackendOwnerInstanceRevoked:
+            deadline = time.monotonic() + 5.0
+
+            while time.monotonic() < deadline:
+                current = get_backend_status(
+                    probe_timeout=0.5,
+                )
+
+                if (
+                    current.state == "stopped"
+                    and current.ready is False
+                    and current.record is None
+                ):
+                    break
+
+                time.sleep(0.05)
+
+            else:
+                raise RuntimeError(
+                    "revoked persistent MCP backend did not self-terminate before timeout"
+                )
+
+            replacement = start_backend(
+                timeout=20.0,
+                probe_timeout=2.0,
+            )
+
+            if (
+                not replacement.ready
+                or replacement.record is None
+            ):
+                raise RuntimeError(
+                    "replacement persistent MCP backend did not become authenticated and ready"
+                )
+
+            claim = self._claim_current_backend_for_desktop()
+
+            if claim.backend_instance_id != replacement.record.instance_id:
+                raise RuntimeError(
+                    "Desktop backend owner claim does not match replacement backend instance"
+                )
+
+            return claim
+
+        if claim.backend_instance_id != status.record.instance_id:
+            raise RuntimeError(
+                "Desktop backend owner claim does not match active backend instance"
+            )
+
+        return claim
+
+    def _start_backend_owner_claim(self):
+        if getattr(self, "_closing", False):
+            return
+
+        current_thread = getattr(
+            self,
+            "_backend_owner_claim_thread",
+            None,
+        )
+
+        if (
+            current_thread is not None
+            and current_thread.is_alive()
+        ):
+            return
+
+        def worker():
+            try:
+                self._claim_backend_owner_on_startup()
+            except Exception as exc:
+                self._backend_owner_claim_error = exc
+
+        thread = threading.Thread(
+            target=worker,
+            name="contextor-backend-owner-claim",
+            daemon=True,
+        )
+
+        self._backend_owner_claim_thread = thread
+        thread.start()
+
     def _start_post_paint_tasks(self):
         if getattr(self, "_closing", False):
             return
+        self._start_backend_owner_claim()
         self._set_live_status("LIVE: initializing in background")
         def cleanup_worker():
             try:
@@ -741,10 +861,26 @@
                     "backend restart returned the previous backend process identity"
                 )
 
-            return before, after
+            new_owner_claim = claim_backend_owner(
+                host_owner_identity=self.desktop_instance_id,
+                host_kind="desktop",
+                owner_token=self.backend_owner_token,
+                probe_timeout=2.0,
+                lock_timeout=5.0,
+            )
+
+            if new_owner_claim.backend_instance_id != after.record.instance_id:
+                raise RuntimeError(
+                    "Desktop backend owner claim does not match restarted backend instance"
+                )
+
+            return before, after, new_owner_claim
 
         def on_success(result):
-            before, after = result
+            before, after, new_owner_claim = result
+
+            self.backend_owner_claim = new_owner_claim
+            self._backend_owner_claim_error = None
 
             old_pid = (
                 "none"

FULL_DIFF_END

### tests/test_gui_backend_owner.py

FULL_DIFF_BEGIN
--- a/tests/test_gui_backend_owner.py
+++ b/tests/test_gui_backend_owner.py
@@ -0,0 +1,331 @@
+import threading
+import time
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.mcp_backend_control import BackendOwnerInstanceRevoked
+from contextor.ui import gui
+
+
+def _record(instance_id, pid=100, creation_time=1000):
+    return SimpleNamespace(
+        instance_id=instance_id,
+        pid=pid,
+        creation_time=creation_time,
+    )
+
+
+def _status(state, ready=False, record=None):
+    return SimpleNamespace(
+        state=state,
+        ready=ready,
+        record=record,
+    )
+
+
+def _controller():
+    controller = SimpleNamespace(
+        desktop_instance_id="desktop-instance",
+        backend_owner_token="backend-owner-token",
+        backend_owner_claim=None,
+        _backend_owner_claim_error=None,
+        _backend_owner_claim_thread=None,
+        _closing=False,
+    )
+    controller._claim_current_backend_for_desktop = lambda: (
+        gui.ContextorGUI._claim_current_backend_for_desktop(controller)
+    )
+    return controller
+
+
+class _FakeVar:
+    def __init__(self, value=""):
+        self.value = value
+
+    def get(self):
+        return self.value
+
+    def trace_add(self, *_args):
+        return "trace-id"
+
+
+class _FakeRoot:
+    def title(self, *_args):
+        pass
+
+    def minsize(self, *_args):
+        pass
+
+    def geometry(self, *_args):
+        pass
+
+    def protocol(self, *_args):
+        pass
+
+    def after(self, *_args):
+        pass
+
+
+def test_init_creates_separate_live_and_backend_owner_identities(monkeypatch):
+    monkeypatch.setattr(
+        gui,
+        "load_state",
+        lambda: {
+            "gui_pos": "",
+            "theme": "light",
+            "repository": "",
+            "layer": "",
+            "python_file": "",
+        },
+    )
+    monkeypatch.setattr(gui.tk, "StringVar", _FakeVar)
+    monkeypatch.setattr(gui, "apply_theme", lambda *_args: None)
+    monkeypatch.setattr(gui.ContextorGUI, "_build_ui", lambda _self: None)
+
+    controller = gui.ContextorGUI(_FakeRoot())
+
+    assert controller.owner_token
+    assert controller.backend_owner_token
+    assert controller.desktop_instance_id
+    assert len(
+        {
+            controller.owner_token,
+            controller.backend_owner_token,
+            controller.desktop_instance_id,
+        }
+    ) == 3
+    assert controller.backend_owner_claim is None
+    assert controller._backend_owner_claim_error is None
+    assert controller._backend_owner_claim_thread is None
+
+
+def test_claim_current_backend_uses_exact_desktop_owner_contract(monkeypatch):
+    controller = _controller()
+    claim = SimpleNamespace(backend_instance_id="instance-1")
+    calls = []
+
+    def claim_backend_owner(**kwargs):
+        calls.append(kwargs)
+        return claim
+
+    monkeypatch.setattr(gui, "claim_backend_owner", claim_backend_owner)
+
+    result = gui.ContextorGUI._claim_current_backend_for_desktop(controller)
+
+    assert result is claim
+    assert controller.backend_owner_claim is claim
+    assert controller._backend_owner_claim_error is None
+    assert calls == [
+        {
+            "host_owner_identity": "desktop-instance",
+            "host_kind": "desktop",
+            "owner_token": "backend-owner-token",
+            "probe_timeout": 2.0,
+            "lock_timeout": 5.0,
+        }
+    ]
+
+
+def test_startup_claims_the_ready_backend_instance(monkeypatch):
+    controller = _controller()
+    status = _status("running", True, _record("instance-1"))
+    claim = SimpleNamespace(backend_instance_id="instance-1")
+    start_calls = []
+    claim_calls = []
+
+    monkeypatch.setattr(
+        gui,
+        "start_backend",
+        lambda **kwargs: start_calls.append(kwargs) or status,
+    )
+    monkeypatch.setattr(
+        gui,
+        "claim_backend_owner",
+        lambda **kwargs: claim_calls.append(kwargs) or claim,
+    )
+
+    result = gui.ContextorGUI._claim_backend_owner_on_startup(controller)
+
+    assert result is claim
+    assert controller.backend_owner_claim is claim
+    assert start_calls == [{"timeout": 20.0, "probe_timeout": 2.0}]
+    assert claim_calls == [
+        {
+            "host_owner_identity": "desktop-instance",
+            "host_kind": "desktop",
+            "owner_token": "backend-owner-token",
+            "probe_timeout": 2.0,
+            "lock_timeout": 5.0,
+        }
+    ]
+
+
+def test_startup_rejects_claim_for_another_instance(monkeypatch):
+    controller = _controller()
+    status = _status("running", True, _record("active-instance"))
+    claim = SimpleNamespace(backend_instance_id="different-instance")
+    monkeypatch.setattr(gui, "start_backend", lambda **_kwargs: status)
+    monkeypatch.setattr(gui, "claim_backend_owner", lambda **_kwargs: claim)
+
+    with pytest.raises(RuntimeError, match="active backend instance"):
+        gui.ContextorGUI._claim_backend_owner_on_startup(controller)
+
+
+def test_revoked_startup_waits_then_claims_replacement_without_stopping_old_backend(
+    monkeypatch,
+):
+    controller = _controller()
+    initial = _status("running", True, _record("old-instance"))
+    replacement = _status("running", True, _record("new-instance", 200, 2000))
+    stopped = _status("stopped", False, None)
+    replacement_claim = SimpleNamespace(backend_instance_id="new-instance")
+    starts = iter((initial, replacement))
+    start_calls = []
+    claim_calls = []
+    status_calls = []
+    stops = []
+
+    def start_backend(**kwargs):
+        start_calls.append(kwargs)
+        return next(starts)
+
+    def claim_backend_owner(**kwargs):
+        claim_calls.append(kwargs)
+        if len(claim_calls) == 1:
+            raise BackendOwnerInstanceRevoked("old instance is revoked")
+        return replacement_claim
+
+    monkeypatch.setattr(gui, "start_backend", start_backend)
+    monkeypatch.setattr(gui, "claim_backend_owner", claim_backend_owner)
+    monkeypatch.setattr(
+        gui,
+        "get_backend_status",
+        lambda **kwargs: status_calls.append(kwargs) or stopped,
+    )
+    monkeypatch.setattr(gui, "stop_backend", lambda **kwargs: stops.append(kwargs))
+    monkeypatch.setattr(gui.time, "monotonic", lambda: 0.0)
+    monkeypatch.setattr(gui.time, "sleep", lambda _seconds: None)
+
+    result = gui.ContextorGUI._claim_backend_owner_on_startup(controller)
+
+    assert result is replacement_claim
+    assert controller.backend_owner_claim is replacement_claim
+    assert start_calls == [
+        {"timeout": 20.0, "probe_timeout": 2.0},
+        {"timeout": 20.0, "probe_timeout": 2.0},
+    ]
+    assert status_calls == [{"probe_timeout": 0.5}]
+    assert len(claim_calls) == 2
+    assert all(
+        call
+        == {
+            "host_owner_identity": "desktop-instance",
+            "host_kind": "desktop",
+            "owner_token": "backend-owner-token",
+            "probe_timeout": 2.0,
+            "lock_timeout": 5.0,
+        }
+        for call in claim_calls
+    )
+    assert stops == []
+
+
+def test_revoked_startup_timeout_never_stops_backend(monkeypatch):
+    controller = _controller()
+    initial = _status("running", True, _record("old-instance"))
+    active = _status("running", True, _record("old-instance"))
+    clock = [0.0]
+    status_calls = []
+    stops = []
+
+    def get_status(**kwargs):
+        status_calls.append(kwargs)
+        clock[0] += 1.0
+        return active
+
+    monkeypatch.setattr(gui, "start_backend", lambda **_kwargs: initial)
+    monkeypatch.setattr(
+        gui,
+        "claim_backend_owner",
+        lambda **_kwargs: (_ for _ in ()).throw(
+            BackendOwnerInstanceRevoked("old instance is revoked")
+        ),
+    )
+    monkeypatch.setattr(gui, "get_backend_status", get_status)
+    monkeypatch.setattr(gui, "stop_backend", lambda **kwargs: stops.append(kwargs))
+    monkeypatch.setattr(gui.time, "monotonic", lambda: clock[0])
+    monkeypatch.setattr(gui.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds + 1.0))
+
+    with pytest.raises(RuntimeError, match="did not self-terminate before timeout"):
+        gui.ContextorGUI._claim_backend_owner_on_startup(controller)
+
+    assert status_calls
+    assert stops == []
+
+
+def test_start_backend_owner_claim_runs_in_nonblocking_daemon_thread():
+    controller = _controller()
+    entered = threading.Event()
+    release = threading.Event()
+
+    def claim_on_startup():
+        entered.set()
+        release.wait(timeout=2.0)
+
+    controller._claim_backend_owner_on_startup = claim_on_startup
+    started = time.monotonic()
+
+    gui.ContextorGUI._start_backend_owner_claim(controller)
+
+    assert time.monotonic() - started < 0.25
+    assert entered.wait(timeout=1.0)
+    thread = controller._backend_owner_claim_thread
+    assert thread.is_alive()
+    assert thread.daemon is True
+    assert thread.name == "contextor-backend-owner-claim"
+    release.set()
+    thread.join(timeout=1.0)
+    assert not thread.is_alive()
+
+
+def test_start_backend_owner_claim_stores_worker_exception():
+    controller = _controller()
+    expected = RuntimeError("claim failed")
+
+    def fail_claim():
+        raise expected
+
+    controller._claim_backend_owner_on_startup = fail_claim
+
+    gui.ContextorGUI._start_backend_owner_claim(controller)
+
+    controller._backend_owner_claim_thread.join(timeout=1.0)
+    assert controller._backend_owner_claim_thread.is_alive() is False
+    assert controller._backend_owner_claim_error is expected
+
+
+def test_post_paint_starts_backend_claim_before_cleanup_and_live(monkeypatch, tmp_path):
+    events = []
+    cleanup_done = threading.Event()
+    controller = SimpleNamespace(
+        _closing=False,
+        _start_backend_owner_claim=lambda: events.append("owner"),
+        _set_live_status=lambda _message: None,
+        _check_stale_excludes=lambda: events.append("stale-excludes"),
+        repo_path_var=SimpleNamespace(get=lambda: str(tmp_path)),
+        _start_live_watcher=lambda _path: events.append("live"),
+    )
+
+    def cleanup():
+        events.append("cache-cleanup")
+        cleanup_done.set()
+        return {"cache": {"errors": []}}
+
+    monkeypatch.setattr(gui, "prune_startup_caches", cleanup)
+
+    gui.ContextorGUI._start_post_paint_tasks(controller)
+
+    assert cleanup_done.wait(timeout=1.0)
+    assert events.index("owner") < events.index("cache-cleanup")
+    assert events.index("owner") < events.index("live")

FULL_DIFF_END

### tests/test_gui_backend_restart.py

FULL_DIFF_BEGIN
--- a/tests/test_gui_backend_restart.py
+++ b/tests/test_gui_backend_restart.py
@@ -30,6 +30,10 @@
         log_box=object(),
         cpu_indicator=object(),
         stop_btn=object(),
+        desktop_instance_id="desktop-instance",
+        backend_owner_token="backend-owner-token",
+        backend_owner_claim=None,
+        _backend_owner_claim_error=RuntimeError("previous claim error"),
         _busy_buttons=lambda: busy_buttons,
     )
     return controller, busy_buttons
@@ -66,6 +70,7 @@
     )
     events = []
     statuses = iter((before, stopped))
+    new_owner_claim = SimpleNamespace(backend_instance_id="new-instance")
 
     def get_status(*, probe_timeout):
         events.append(("status", probe_timeout))
@@ -78,9 +83,21 @@
         events.append(("start", timeout, probe_timeout))
         return after
 
+    def claim_backend_owner(**kwargs):
+        events.append(("claim", kwargs))
+        return new_owner_claim
+
     monkeypatch.setattr(gui, "get_backend_status", get_status)
     monkeypatch.setattr(gui, "stop_backend", stop_backend)
     monkeypatch.setattr(gui, "start_backend", start_backend)
+    monkeypatch.setattr(gui, "claim_backend_owner", claim_backend_owner)
+    release_calls = []
+    monkeypatch.setattr(
+        gui,
+        "release_backend_owner",
+        lambda *args, **kwargs: release_calls.append((args, kwargs)),
+        raising=False,
+    )
     captured = _capture_progress(monkeypatch)
     controller, busy_buttons = _controller()
     messages = []
@@ -99,15 +116,28 @@
 
     result = captured["task"]()
 
-    assert result == (before, after)
+    assert result == (before, after, new_owner_claim)
     assert events == [
         ("status", 2.0),
         ("stop", 5.0),
         ("status", 0.5),
         ("start", 20.0, 2.0),
+        (
+            "claim",
+            {
+                "host_owner_identity": "desktop-instance",
+                "host_kind": "desktop",
+                "owner_token": "backend-owner-token",
+                "probe_timeout": 2.0,
+                "lock_timeout": 5.0,
+            },
+        ),
     ]
 
     captured["on_success"](result)
+    assert controller.backend_owner_claim is new_owner_claim
+    assert controller._backend_owner_claim_error is None
+    assert release_calls == []
     assert len(messages) == 1
     assert "Old PID: 123" in messages[0][1]
     assert "New instance: new-instance" in messages[0][1]
@@ -188,6 +218,7 @@
     )
     statuses = iter((before, stopped))
     events = []
+    new_owner_claim = SimpleNamespace(backend_instance_id="fresh-instance")
 
     def get_status(*, probe_timeout):
         events.append(("status", probe_timeout))
@@ -196,14 +227,93 @@
     monkeypatch.setattr(gui, "get_backend_status", get_status)
     monkeypatch.setattr(gui, "stop_backend", lambda **_: events.append(("stop",)))
     monkeypatch.setattr(gui, "start_backend", lambda **_: after)
+    monkeypatch.setattr(
+        gui,
+        "claim_backend_owner",
+        lambda **kwargs: events.append(("claim", kwargs)) or new_owner_claim,
+    )
     captured = _capture_progress(monkeypatch)
     controller, _ = _controller()
 
     gui.ContextorGUI._restart_backend(controller)
     result = captured["task"]()
 
-    assert result == (before, after)
-    assert events == [("status", 2.0), ("stop",), ("status", 0.5)]
+    assert result == (before, after, new_owner_claim)
+    assert events == [
+        ("status", 2.0),
+        ("stop",),
+        ("status", 0.5),
+        (
+            "claim",
+            {
+                "host_owner_identity": "desktop-instance",
+                "host_kind": "desktop",
+                "owner_token": "backend-owner-token",
+                "probe_timeout": 2.0,
+                "lock_timeout": 5.0,
+            },
+        ),
+    ]
+
+
+def test_restart_owner_claim_mismatch_fails_without_rollback(monkeypatch):
+    before = _status("running", ready=True, record=_record("old", 123, 1000))
+    stopped = _status("stopped")
+    after = _status("running", ready=True, record=_record("new", 456, 2000))
+    statuses = iter((before, stopped))
+    stop_calls = []
+    errors = []
+    monkeypatch.setattr(gui, "get_backend_status", lambda **_: next(statuses))
+    monkeypatch.setattr(gui, "stop_backend", lambda **kwargs: stop_calls.append(kwargs))
+    monkeypatch.setattr(gui, "start_backend", lambda **_: after)
+    monkeypatch.setattr(
+        gui,
+        "claim_backend_owner",
+        lambda **_: SimpleNamespace(backend_instance_id="foreign-instance"),
+    )
+    captured = _capture_progress(monkeypatch)
+    controller, _ = _controller()
+    monkeypatch.setattr(gui.messagebox, "showerror", lambda *args: errors.append(args))
+
+    gui.ContextorGUI._restart_backend(controller)
+
+    with pytest.raises(RuntimeError, match="does not match restarted backend instance") as exc_info:
+        captured["task"]()
+    captured["on_error"](exc_info.value)
+
+    assert len(stop_calls) == 1
+    assert errors and "does not match restarted backend instance" in errors[0][1]
+
+
+def test_restart_owner_claim_failure_reaches_on_error_without_rollback(monkeypatch):
+    before = _status("running", ready=True, record=_record("old", 123, 1000))
+    stopped = _status("stopped")
+    after = _status("running", ready=True, record=_record("new", 456, 2000))
+    statuses = iter((before, stopped))
+    stop_calls = []
+    errors = []
+    claim_error = RuntimeError("owner claim denied")
+    monkeypatch.setattr(gui, "get_backend_status", lambda **_: next(statuses))
+    monkeypatch.setattr(gui, "stop_backend", lambda **kwargs: stop_calls.append(kwargs))
+    monkeypatch.setattr(gui, "start_backend", lambda **_: after)
+
+    def fail_claim(**_kwargs):
+        raise claim_error
+
+    monkeypatch.setattr(gui, "claim_backend_owner", fail_claim)
+    captured = _capture_progress(monkeypatch)
+    controller, _ = _controller()
+    monkeypatch.setattr(gui.messagebox, "showerror", lambda *args: errors.append(args))
+
+    gui.ContextorGUI._restart_backend(controller)
+
+    with pytest.raises(RuntimeError, match="owner claim denied") as exc_info:
+        captured["task"]()
+    captured["on_error"](exc_info.value)
+
+    assert exc_info.value is claim_error
+    assert len(stop_calls) == 1
+    assert errors and "owner claim denied" in errors[0][1]
 
 
 def test_restart_backend_button_is_in_shared_busy_buttons():

FULL_DIFF_END

### tests/test_gui_live_startup.py

FULL_DIFF_BEGIN
--- a/tests/test_gui_live_startup.py
+++ b/tests/test_gui_live_startup.py
@@ -81,6 +81,7 @@
         live_clients={},
         live_client=None,
         owner_token="test-owner-token",
+        _start_backend_owner_claim=MagicMock(),
         _live_start_retry_attempt=0,
         _live_start_retry_after_id=None,
         _closing=False,
@@ -218,6 +219,7 @@
     started = time.monotonic()
     ContextorGUI._start_post_paint_tasks(controller)
     assert time.monotonic() - started < 0.25
+    controller._start_backend_owner_claim.assert_called_once_with()
     assert entered.wait(timeout=2)
     assert thread_ids[0] != main_id
     allow.set()

FULL_DIFF_END

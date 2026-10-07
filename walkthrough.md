# CPA_GUI_RESTART_BACKEND_BUTTON_IMPLEMENTATION

STATUS=IMPLEMENTED_TARGETED_TESTS_PASS
HEAD=e9ab1c88bc9369efe9c85e46aa2b074e9b6de84d

## IMPLEMENTATION_RESULT

- Added `Restart Backend` immediately after `MCP Logs` in `ContextorGUI._setup_header`, using the shared `HeaderTooltipManager` and the specified tooltip.
- Added `ContextorGUI._restart_backend`; it delegates lifecycle work to `run_with_progress`, independently verifies the stopped state, requires authenticated readiness, and compares `(instance_id, pid, creation_time)` before reporting success.
- Added the restart button to `_busy_buttons`, so it participates in the existing mutual exclusion for long-running GUI actions.
- `start_backend`, `stop_backend`, backend ownership/schema, transport/auth, autostart, and `on_closing` were not changed.

## EVIDENCE

- DIRECT_EVIDENCE: Before edits, Contextor returned canonical revision 1604, `canonical_state=fresh`, `workspace_sync=verified` for `gui.py`, `mcp_backend_control.py`, and relevant existing test modules.
- CODE_PATH_PROVED: Contextor identified `_setup_header` as the toolbar owner; `_busy_buttons` callers were `_run_test_suite`, `analyze`, `analyze_layer`, and `analyze_single`. Existing `run_with_progress` starts a daemon worker and schedules terminal UI callbacks through `root.after`.
- DIRECT_EVIDENCE: After edits, `get_live_events(after_revision=1604)` returned `continuity=continuous`, `resync_required=false`, and `desktop_watcher` `UPDATED` events for `contextor/ui/gui.py` at revision 1605 and `tests/test_gui_backend_restart.py` at revision 1606.
- DIRECT_EVIDENCE: Contextor fetched `_setup_header`, `_busy_buttons`, and `_restart_backend` at canonical revision 1606 with `canonical_state=fresh`, `workspace_sync=verified`, and complete implementations.
- TARGETED_TEST_RESULT: 12 passed, 1 warning. The warning is the installed Authlib `authlib.jose` deprecation notice.
- No full repository pytest suite was run.

## TARGETED_TESTS

Command:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/test_gui_backend_restart.py tests/test_mcp_backend_control.py::test_status_without_record_is_stopped tests/test_mcp_backend_control.py::test_status_stale_record_never_probes_http tests/test_mcp_backend_control.py::test_status_live_owner_requires_authenticated_readiness tests/test_mcp_backend_control.py::test_start_returns_existing_ready_backend_without_spawn tests/test_mcp_backend_control.py::test_stop_without_record_is_idempotent tests/test_mcp_backend_control.py::test_windows_stop_uses_exact_backend_record_for_termination
```

New focused tests:

- `test_restart_runs_lifecycle_in_progress_task_and_confirms_new_identity`
- `test_restart_rejects_reused_complete_backend_identity`
- `test_restart_requires_independently_confirmed_stopped_state`
- `test_restart_requires_new_backend_to_be_authenticated_and_ready`
- `test_restart_starts_backend_when_initial_status_has_no_record`
- `test_restart_backend_button_is_in_shared_busy_buttons`

## FILES_CHANGED

- `contextor/ui/gui.py`
- `tests/test_gui_backend_restart.py`

The report file `walkthrough.md` is the required task report and is excluded from implementation-file diffs.

## FULL_DIFFS

### `contextor/ui/gui.py`

```diff
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index e551d69..3533ef2 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -38,6 +38,11 @@ from contextor.core.repository_identity import (
 )
 from contextor.core.paths import prune_startup_caches
 from contextor.repo_generator import run_repo_generator
+from contextor.mcp_backend_control import (
+    get_backend_status,
+    start_backend,
+    stop_backend,
+)
 from contextor.ui import theme
 from contextor.ui.exclude_check import check_stale_excludes
 from contextor.ui.exclude_gui import run_exclude_window
@@ -283,6 +288,14 @@ class ContextorGUI:
         )
         self.mcp_logs_btn.pack(side="left", padx=(PAD_SM, 0))
 
+        self.restart_backend_btn = ttk.Button(
+            title_frame,
+            text="Restart Backend",
+            style="Ghost.TButton",
+            command=self._restart_backend,
+        )
+        self.restart_backend_btn.pack(side="left", padx=(PAD_SM, 0))
+
         sub_label = ttk.Label(
             header, text="Static architecture analysis Â· Read-only mode", style="Sub.TLabel"
         )
@@ -302,6 +315,10 @@ class ContextorGUI:
             self.mcp_logs_btn,
             "Open the folder containing LIVE and MCP operation logs.",
         )
+        self.tooltip.bind_tooltip(
+            self.restart_backend_btn,
+            "Stop the current persistent MCP backend and start a fresh instance using the current code on disk.",
+        )
         self.tooltip.bind_tooltip(
             self.theme_btn,
             "Switch between light and dark appearance.",
@@ -660,8 +677,118 @@ class ContextorGUI:
             self.analyze_layer_btn,
             self.analyze_single_btn,
             self.test_suite_btn,
+            self.restart_backend_btn,
         ]
 
+    def _restart_backend(self):
+        """
+        Restart the persistent MCP backend without blocking the Tk main loop.
+        """
+
+        operation_title = "Restart Backend"
+
+        def _identity(status):
+            record = status.record
+            if record is None:
+                return None
+
+            return (
+                record.instance_id,
+                record.pid,
+                record.creation_time,
+            )
+
+        def task(log=None, progress_callback=None):
+            before = get_backend_status(
+                probe_timeout=2.0,
+            )
+            before_identity = _identity(before)
+
+            stop_backend(
+                timeout=5.0,
+            )
+
+            stopped = get_backend_status(
+                probe_timeout=0.5,
+            )
+
+            if (
+                stopped.state != "stopped"
+                or stopped.ready
+                or stopped.record is not None
+            ):
+                raise RuntimeError(
+                    "persistent MCP backend did not reach a confirmed stopped state"
+                )
+
+            after = start_backend(
+                timeout=20.0,
+                probe_timeout=2.0,
+            )
+
+            if not after.ready or after.record is None:
+                raise RuntimeError(
+                    "new persistent MCP backend did not become authenticated and ready"
+                )
+
+            after_identity = _identity(after)
+
+            if (
+                before_identity is not None
+                and after_identity == before_identity
+            ):
+                raise RuntimeError(
+                    "backend restart returned the previous backend process identity"
+                )
+
+            return before, after
+
+        def on_success(result):
+            before, after = result
+
+            old_pid = (
+                "none"
+                if before.record is None
+                else str(before.record.pid)
+            )
+            old_instance = (
+                "none"
+                if before.record is None
+                else before.record.instance_id
+            )
+
+            messagebox.showinfo(
+                "MCP backend restarted",
+                (
+                    "Persistent MCP backend restarted successfully.\n\n"
+                    f"Old PID: {old_pid}\n"
+                    f"Old instance: {old_instance}\n"
+                    f"New PID: {after.record.pid}\n"
+                    f"New instance: {after.record.instance_id}\n"
+                    f"Endpoint: {after.endpoint}"
+                ),
+            )
+
+        def on_error(exc):
+            messagebox.showerror(
+                operation_title,
+                f"Backend restart failed.\n\n{exc}",
+            )
+
+        self.progress_bar.is_cancelled = False
+
+        run_with_progress(
+            self.root,
+            self.progress_bar,
+            task,
+            on_success=on_success,
+            on_error=on_error,
+            buttons=self._busy_buttons(),
+            log_box=self.log_box,
+            cpu_indicator=self.cpu_indicator,
+            stop_button=self.stop_btn,
+        )
+
     def _run_test_suite(self):
         """
         Runs the selected Contextor test suite and reports the outcome.
```

### `tests/test_gui_backend_restart.py`

```diff
diff --git a/tests/test_gui_backend_restart.py b/tests/test_gui_backend_restart.py
new file mode 100644
index 0000000..b5243b1
--- /dev/null
+++ b/tests/test_gui_backend_restart.py
@@ -0,0 +1,224 @@
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.ui import gui
+
+
+def _record(instance_id, pid, creation_time):
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
+        endpoint="http://127.0.0.1:8765/mcp",
+    )
+
+
+def _controller():
+    busy_buttons = [object(), object(), object()]
+    controller = SimpleNamespace(
+        root=object(),
+        progress_bar=SimpleNamespace(is_cancelled=True),
+        log_box=object(),
+        cpu_indicator=object(),
+        stop_btn=object(),
+        _busy_buttons=lambda: busy_buttons,
+    )
+    return controller, busy_buttons
+
+
+def _capture_progress(monkeypatch):
+    captured = {}
+
+    def capture(root, progress_bar, task, **kwargs):
+        captured.update(
+            root=root,
+            progress_bar=progress_bar,
+            task=task,
+            **kwargs,
+        )
+
+    monkeypatch.setattr(gui, "run_with_progress", capture)
+    return captured
+
+
+def test_restart_runs_lifecycle_in_progress_task_and_confirms_new_identity(
+    monkeypatch,
+):
+    before = _status(
+        "ready",
+        ready=True,
+        record=_record("old-instance", 123, 1000),
+    )
+    stopped = _status("stopped")
+    after = _status(
+        "ready",
+        ready=True,
+        record=_record("new-instance", 123, 2000),
+    )
+    events = []
+    statuses = iter((before, stopped))
+
+    def get_status(*, probe_timeout):
+        events.append(("status", probe_timeout))
+        return next(statuses)
+
+    def stop_backend(*, timeout):
+        events.append(("stop", timeout))
+
+    def start_backend(*, timeout, probe_timeout):
+        events.append(("start", timeout, probe_timeout))
+        return after
+
+    monkeypatch.setattr(gui, "get_backend_status", get_status)
+    monkeypatch.setattr(gui, "stop_backend", stop_backend)
+    monkeypatch.setattr(gui, "start_backend", start_backend)
+    captured = _capture_progress(monkeypatch)
+    controller, busy_buttons = _controller()
+    messages = []
+    monkeypatch.setattr(gui.messagebox, "showinfo", lambda *args: messages.append(args))
+
+    gui.ContextorGUI._restart_backend(controller)
+
+    assert events == []
+    assert controller.progress_bar.is_cancelled is False
+    assert captured["root"] is controller.root
+    assert captured["progress_bar"] is controller.progress_bar
+    assert captured["buttons"] is busy_buttons
+    assert captured["log_box"] is controller.log_box
+    assert captured["cpu_indicator"] is controller.cpu_indicator
+    assert captured["stop_button"] is controller.stop_btn
+
+    result = captured["task"]()
+
+    assert result == (before, after)
+    assert events == [
+        ("status", 2.0),
+        ("stop", 5.0),
+        ("status", 0.5),
+        ("start", 20.0, 2.0),
+    ]
+
+    captured["on_success"](result)
+    assert len(messages) == 1
+    assert "Old PID: 123" in messages[0][1]
+    assert "New instance: new-instance" in messages[0][1]
+    assert "http://127.0.0.1:8765/mcp" in messages[0][1]
+
+
+def test_restart_rejects_reused_complete_backend_identity(monkeypatch):
+    old_record = _record("same-instance", 123, 1000)
+    before = _status("ready", ready=True, record=old_record)
+    after = _status(
+        "ready",
+        ready=True,
+        record=_record("same-instance", 123, 1000),
+    )
+    statuses = iter((before, _status("stopped")))
+    monkeypatch.setattr(gui, "get_backend_status", lambda **_: next(statuses))
+    monkeypatch.setattr(gui, "stop_backend", lambda **_: None)
+    monkeypatch.setattr(gui, "start_backend", lambda **_: after)
+    captured = _capture_progress(monkeypatch)
+    controller, _ = _controller()
+
+    gui.ContextorGUI._restart_backend(controller)
+
+    with pytest.raises(RuntimeError, match="previous backend process identity"):
+        captured["task"]()
+
+
+def test_restart_requires_independently_confirmed_stopped_state(monkeypatch):
+    before = _status("ready", ready=True, record=_record("old", 123, 1000))
+    not_stopped = _status("unready", record=None)
+    statuses = iter((before, not_stopped))
+    events = []
+    monkeypatch.setattr(gui, "get_backend_status", lambda **_: next(statuses))
+    monkeypatch.setattr(gui, "stop_backend", lambda **_: events.append("stop"))
+    monkeypatch.setattr(gui, "start_backend", lambda **_: events.append("start"))
+    captured = _capture_progress(monkeypatch)
+    controller, _ = _controller()
+
+    gui.ContextorGUI._restart_backend(controller)
+
+    with pytest.raises(RuntimeError, match="confirmed stopped state"):
+        captured["task"]()
+    assert events == ["stop"]
+
+
+def test_restart_requires_new_backend_to_be_authenticated_and_ready(monkeypatch):
+    before = _status("ready", ready=True, record=_record("old", 123, 1000))
+    stopped = _status("stopped")
+    unready = _status(
+        "unready",
+        ready=False,
+        record=_record("new", 456, 2000),
+    )
+    statuses = iter((before, stopped))
+    monkeypatch.setattr(gui, "get_backend_status", lambda **_: next(statuses))
+    monkeypatch.setattr(gui, "stop_backend", lambda **_: None)
+    monkeypatch.setattr(gui, "start_backend", lambda **_: unready)
+    captured = _capture_progress(monkeypatch)
+    controller, _ = _controller()
+    errors = []
+    monkeypatch.setattr(gui.messagebox, "showerror", lambda *args: errors.append(args))
+
+    gui.ContextorGUI._restart_backend(controller)
+
+    with pytest.raises(RuntimeError, match="authenticated and ready") as exc_info:
+        captured["task"]()
+    captured["on_error"](exc_info.value)
+    assert errors and "authenticated and ready" in errors[0][1]
+
+
+def test_restart_starts_backend_when_initial_status_has_no_record(monkeypatch):
+    before = _status("stopped", record=None)
+    stopped = _status("stopped", record=None)
+    after = _status(
+        "ready",
+        ready=True,
+        record=_record("fresh-instance", 456, 2000),
+    )
+    statuses = iter((before, stopped))
+    events = []
+
+    def get_status(*, probe_timeout):
+        events.append(("status", probe_timeout))
+        return next(statuses)
+
+    monkeypatch.setattr(gui, "get_backend_status", get_status)
+    monkeypatch.setattr(gui, "stop_backend", lambda **_: events.append(("stop",)))
+    monkeypatch.setattr(gui, "start_backend", lambda **_: after)
+    captured = _capture_progress(monkeypatch)
+    controller, _ = _controller()
+
+    gui.ContextorGUI._restart_backend(controller)
+    result = captured["task"]()
+
+    assert result == (before, after)
+    assert events == [("status", 2.0), ("stop",), ("status", 0.5)]
+
+
+def test_restart_backend_button_is_in_shared_busy_buttons():
+    controller = SimpleNamespace(
+        analyze_btn=object(),
+        analyze_layer_btn=object(),
+        analyze_single_btn=object(),
+        test_suite_btn=object(),
+        restart_backend_btn=object(),
+    )
+
+    assert gui.ContextorGUI._busy_buttons(controller) == [
+        controller.analyze_btn,
+        controller.analyze_layer_btn,
+        controller.analyze_single_btn,
+        controller.test_suite_btn,
+        controller.restart_backend_btn,
+    ]
```

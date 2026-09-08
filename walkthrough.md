FILES_CHANGED=
contextor/core/live_state/runtime.py
tests/test_live_state_ipc.py

TESTS_RUN=
.\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py::test_run_service_rejects_stop_and_return_before_ready tests/test_live_state_ipc.py::test_run_service_fails_closed_when_service_thread_raises_before_endpoint tests/test_live_state_ipc.py::test_run_service_fails_closed_when_service_thread_dies_before_ready tests/test_live_state_ipc.py::test_normal_service_shutdown_preserves_authority_event_chronology tests/test_live_state_ipc.py::test_endpoint_before_authority_replay_exposes_valid_pending_live_feed tests/test_live_state_ipc.py::test_startup_backfill_preserves_filestate_content_and_revision_parity
.\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py::test_connect_or_start_slow_healthy_startup (4 independent runs)
.\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py::test_startup_backfill_preserves_filestate_content_and_revision_parity tests/test_live_state_ipc.py::test_startup_backfill_failure_leaves_previous_generation_authoritative tests/test_live_state_ipc.py::test_real_service_process_starts_connects_and_stops tests/test_live_state_ipc.py::test_connect_or_start_ownership_when_spawning_new tests/test_live_state_ipc.py::test_legacy_endpoint_is_rejected_before_post_spawn_attach tests/test_live_state_ipc.py::test_connect_or_start_slow_healthy_startup tests/test_live_state_ipc.py::test_connect_or_start_dead_child_fast_failure tests/test_live_state_ipc.py::test_connect_or_start_true_startup_hang

TEST_RESULTS=
Requested six-test correction set: 6 passed, 1 warning, 19.05s.
Healthy-startup gate: 4/4 PASS with unchanged 2.0s budget; pytest durations 2.70s, 3.16s, 2.71s, 2.74s.
Previous focused startup/authority subset: 8 passed in 13.94s.

PYTEST_EXIT_CODE=0

ACTUAL_DIFF=
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 14403a5..ee946d6 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -1024,30 +1024,43 @@ def run_service(
     server_thread = None
     service_bootstrap_entered = threading.Event()
     service_terminated = threading.Event()
+    service_state_lock = threading.Lock()
     service_failure: list[BaseException] = []
+    service_ready_committed = False
     published_endpoint = None
     desktop_claim = None
     authority_emitter = None
     ownership_resolved = False
 
     def _raise_if_service_terminated(stage: str) -> None:
-        if service_failure:
+        with service_state_lock:
+            failure = service_failure[0] if service_failure else None
+            terminated = service_terminated.is_set()
+            ready_committed = service_ready_committed
+            stop_requested = bool(server is not None and server._stop.is_set())
+
+        if failure is not None:
             raise RuntimeError(
                 f"Canonical LIVE service thread failed during {stage}"
-            ) from service_failure[0]
-        if server is not None and service_terminated.is_set() and not server._stop.is_set():
+            ) from failure
+
+        if terminated and (not ready_committed or not stop_requested):
             raise RuntimeError(
                 f"Canonical LIVE service thread terminated unexpectedly during {stage}"
             )
 
     def _serve_service() -> None:
         service_bootstrap_entered.set()
+        failure: BaseException | None = None
         try:
             server.serve_forever()
         except BaseException as exc:
-            service_failure.append(exc)
+            failure = exc
         finally:
-            service_terminated.set()
+            with service_state_lock:
+                if failure is not None:
+                    service_failure.append(failure)
+                service_terminated.set()
 
     try:
         from contextor.core.runtime_trace import AuthorityEventEmitter
@@ -1192,16 +1205,31 @@ def run_service(
             )
             authority_emitter.replay_pending()
         _raise_if_service_terminated("authority event handoff")
-        if authority_emitter is not None:
-            authority_emitter.emit(
-                "RUNTIME_AUTHORITY_READY",
-                source="runtime",
-                service_instance_id=lease.service_instance_id,
-                lease_generation=lease.lease_generation,
-                status="READY",
-                decision="READY",
-                reason="endpoint, lease and authority identity parity verified",
-            )
+        # READY is the startup linearization point shared with service-thread
+        # termination. If termination acquires this lock first, startup fails
+        # and READY is never emitted. If this block wins, any later intentional
+        # stop belongs to the normal post-READY service lifetime.
+        with service_state_lock:
+            if service_failure:
+                raise RuntimeError(
+                    "Canonical LIVE service thread failed before authority readiness"
+                ) from service_failure[0]
+            if service_terminated.is_set():
+                raise RuntimeError(
+                    "Canonical LIVE service thread terminated before authority readiness"
+                )
+
+            if authority_emitter is not None:
+                authority_emitter.emit(
+                    "RUNTIME_AUTHORITY_READY",
+                    source="runtime",
+                    service_instance_id=lease.service_instance_id,
+                    lease_generation=lease.lease_generation,
+                    status="READY",
+                    decision="READY",
+                    reason="endpoint, lease and authority identity parity verified",
+                )
+            service_ready_committed = True
 
         if owner_pid is not None and owner_pid > 0:
             if sys.platform == "win32":
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index d795ba2..bbd57b4 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -496,11 +496,23 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
             self._revision = revision
             self.endpoint = SimpleNamespace(host="127.0.0.1", port=1, authkey_hex="00")
             self._stop = threading.Event()
+            self.activity_epoch = "startup-backfill-test"
+
         def serve_forever(self):
-            self._stop.set()
-            return None
+            if not self._stop.wait(timeout=5.0):
+                raise RuntimeError("StubServer did not receive post-READY shutdown")
+
+        def record_authority_event(self, event):
+            if event.get("event_type") == "RUNTIME_AUTHORITY_READY":
+                self._stop.set()
+            return {
+                "accepted": True,
+                "duplicate": False,
+                "activity_epoch": self.activity_epoch,
+            }
+
         def close(self):
-            return None
+            self._stop.set()
 
     monkeypatch.setattr(runtime, "CanonicalLiveServer", StubServer)
     import contextor.core.runtime_trace as runtime_trace
@@ -584,6 +596,29 @@ def _authority_event_types(logs_root):
     return records
 
 
+def test_run_service_rejects_stop_and_return_before_ready(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+    from contextor.core.paths import runtime_logs_dir
+
+    repo = _runtime_service_repo(tmp_path, monkeypatch)
+
+    class PrematureStoppingServer(CanonicalLiveServer):
+        def serve_forever(self):
+            self._stop.set()
+            return None
+
+    monkeypatch.setattr(runtime, "CanonicalLiveServer", PrematureStoppingServer)
+
+    with pytest.raises(
+        RuntimeError,
+        match="service thread terminated unexpectedly during pre-endpoint bootstrap",
+    ):
+        runtime.run_service(repo)
+
+    assert not endpoint_file(repo).exists()
+    assert "RUNTIME_AUTHORITY_READY" not in _authority_event_types(runtime_logs_dir())
+
+
 def test_run_service_fails_closed_when_service_thread_raises_before_endpoint(tmp_path, monkeypatch):
     import contextor.core.live_state.runtime as runtime
     from contextor.core.paths import runtime_logs_dir
@@ -659,6 +694,10 @@ def test_normal_service_shutdown_preserves_authority_event_chronology(tmp_path,
             break
         time.sleep(0.02)
     assert client is not None
+    deadline = time.monotonic() + 5.0
+    while time.monotonic() < deadline and "RUNTIME_AUTHORITY_READY" not in _authority_event_types(runtime_logs_dir()):
+        time.sleep(0.02)
+    assert "RUNTIME_AUTHORITY_READY" in _authority_event_types(runtime_logs_dir())
     assert client.request("shutdown").get("status") == "ok"
     service.join(timeout=5.0)
 
@@ -673,6 +712,7 @@ def test_endpoint_before_authority_replay_exposes_valid_pending_live_feed(tmp_pa
     import contextor.core.live_state.runtime as runtime
     import contextor.core.runtime_trace as runtime_trace
     from contextor import mcp_server
+    from contextor.core.paths import runtime_logs_dir
 
     repo = _runtime_service_repo(tmp_path, monkeypatch)
     replay_entered = threading.Event()
@@ -721,6 +761,11 @@ def test_endpoint_before_authority_replay_exposes_valid_pending_live_feed(tmp_pa
 
     client = runtime.connect(repo)
     assert client is not None
+    deadline = time.monotonic() + 5.0
+    while time.monotonic() < deadline and "RUNTIME_AUTHORITY_READY" not in _authority_event_types(runtime_logs_dir()):
+        completed = json.loads(mcp_server.get_live_events.fn(str(repo)))
+        time.sleep(0.02)
+    assert "RUNTIME_AUTHORITY_READY" in _authority_event_types(runtime_logs_dir())
     assert client.request("shutdown").get("status") == "ok"
     service.join(timeout=5.0)
     assert not service.is_alive()

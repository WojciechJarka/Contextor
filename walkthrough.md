FILES_CHANGED=
contextor/core/live_state/runtime.py
tests/test_live_state_ipc.py

ROOT_CAUSE=
The early service-loop optimization originally used a bare daemon thread. An exception from `CanonicalLiveServer.serve_forever()` could terminate that thread without reaching `run_service`, allowing endpoint publication and READY to continue. It also moved `RUNTIME_AUTHORITY_START` after endpoint bind/parity, which changed its meaning. The endpoint-before-replay window is client-visible, but the durable JSONL/sidecar remains the source of truth and the existing handoff is ordered/idempotent; the boundary test verifies a client receives a valid `get_live_events` response while delivery is pending, followed by unique authority projections after replay.

THREAD_FAILURE_CONTRACT=
`run_service` now owns explicit local service-thread state: entered, terminated, and captured `BaseException`. It waits for thread bootstrap entry, fails closed before endpoint publication, after endpoint/parity, after authority handoff, and after lifetime join when the service thread failed or exited without normal server stop. The original exception is preserved as the RuntimeError cause. `server.close()`/IPC shutdown sets the server stop event and is accepted as normal shutdown rather than a startup failure.

HANDOFF_READINESS_CONTRACT=
The listener service loop starts before the endpoint remains public. Endpoint publication still requires unchanged atomic write, exact endpoint/lease/generation fingerprint parity, and the server is already able to answer verified clients. `attach_live_sink`/`replay_pending` remains after that bind. No durable authority event is lost: it is committed first to JSONL plus sidecar pending index; replay preserves `(runtime_domain_id, sequence, event_id)` and `record_authority_event` deduplicates exactly that key. During the pending interval, `get_live_events` returns a contract-valid `status=ok` feed (`continuity=not_requested` when no cursor was requested); after release, the same feed exposes one unique projection of every replayed authority event.

EVENT_ORDERING=
For subprocess startup, `connect_or_start` records the truthful durable `RUNTIME_AUTHORITY_START` before admitting/spawning the child process, then passes `--authority-start-recorded` so the child does not duplicate it. Direct `run_service` retains its own early START emission. In both paths START precedes READY; the event no longer claims endpoint-ready completion.

TESTS_RUN=
1. .\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py::test_run_service_fails_closed_when_service_thread_raises_before_endpoint tests/test_live_state_ipc.py::test_run_service_fails_closed_when_service_thread_dies_before_ready tests/test_live_state_ipc.py::test_normal_service_shutdown_preserves_authority_event_chronology tests/test_live_state_ipc.py::test_endpoint_before_authority_replay_exposes_valid_pending_live_feed
2. .\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py::test_connect_or_start_slow_healthy_startup (four independent runs)
3. .\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py::test_startup_backfill_preserves_filestate_content_and_revision_parity tests/test_live_state_ipc.py::test_startup_backfill_failure_leaves_previous_generation_authoritative tests/test_live_state_ipc.py::test_real_service_process_starts_connects_and_stops tests/test_live_state_ipc.py::test_connect_or_start_ownership_when_spawning_new tests/test_live_state_ipc.py::test_legacy_endpoint_is_rejected_before_post_spawn_attach tests/test_live_state_ipc.py::test_connect_or_start_slow_healthy_startup tests/test_live_state_ipc.py::test_connect_or_start_dead_child_fast_failure tests/test_live_state_ipc.py::test_connect_or_start_true_startup_hang

TEST_RESULTS=
New thread-failure/normal-shutdown/handoff-boundary regressions: 4 passed, 1 existing FastMCP deprecation warning, in 15.93s.
Healthy-startup performance gate: PASS 4/4 with the unchanged 2.0s child bootstrap timeout; individual pytest durations 2.83s, 3.03s, 3.89s, 3.01s (the test's parent-visible child connection remained inside its 2.0s budget in every run).
Focused startup/authority/endpoint/failure subset: 8 passed in 14.08s.
PYTEST_EXIT_CODE=0

ACTUAL_DIFF=
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 7f234c4..14403a5 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -882,6 +882,20 @@ def connect_or_start(
         else:
             env["PYTHONPATH"] = pkg_root
 
+        from contextor.core.runtime_trace import AuthorityEventEmitter
+
+        AuthorityEventEmitter(
+            runtime_domain_id=domain.domain_id,
+            repo_id=identity.repo_id,
+            logs_root=domain.logs_root,
+        ).emit(
+            "RUNTIME_AUTHORITY_START",
+            source="runtime_startup_coordinator",
+            status="STARTING",
+            decision="START",
+            reason="authority service process spawn admitted",
+        )
+        cmd.append("--authority-start-recorded")
         proc = _spawn_runtime_subprocess(cmd, root, env)
         spawn_deadline = time.monotonic() + effective_startup_budget
         while time.monotonic() < spawn_deadline:
@@ -999,6 +1013,7 @@ def run_service(
     owner_token: str | None = None,
     desktop_instance_id: str | None = None,
     desktop_process_start_identity: str | None = None,
+    authority_start_recorded: bool = False,
 ) -> None:
     root = Path(repo_path).expanduser().resolve()
     identity = require_repository_identity(root)
@@ -1006,10 +1021,34 @@ def run_service(
     manager = None
     lease = None
     server = None
+    server_thread = None
+    service_bootstrap_entered = threading.Event()
+    service_terminated = threading.Event()
+    service_failure: list[BaseException] = []
     published_endpoint = None
     desktop_claim = None
     authority_emitter = None
     ownership_resolved = False
+
+    def _raise_if_service_terminated(stage: str) -> None:
+        if service_failure:
+            raise RuntimeError(
+                f"Canonical LIVE service thread failed during {stage}"
+            ) from service_failure[0]
+        if server is not None and service_terminated.is_set() and not server._stop.is_set():
+            raise RuntimeError(
+                f"Canonical LIVE service thread terminated unexpectedly during {stage}"
+            )
+
+    def _serve_service() -> None:
+        service_bootstrap_entered.set()
+        try:
+            server.serve_forever()
+        except BaseException as exc:
+            service_failure.append(exc)
+        finally:
+            service_terminated.set()
+
     try:
         from contextor.core.runtime_trace import AuthorityEventEmitter
 
@@ -1018,13 +1057,14 @@ def run_service(
             repo_id=identity.repo_id,
             logs_root=domain.logs_root,
         )
-        authority_emitter.emit(
-            "RUNTIME_AUTHORITY_START",
-            source="runtime",
-            status="STARTING",
-            decision="START",
-            reason="authority service bootstrap started",
-        )
+        if not authority_start_recorded:
+            authority_emitter.emit(
+                "RUNTIME_AUTHORITY_START",
+                source="runtime",
+                status="STARTING",
+                decision="START",
+                reason="authority service bootstrap started",
+            )
         manager = RuntimeLeaseManager(
             domain,
             liveness_verifier=AuthorityLivenessVerifier(domain),
@@ -1106,12 +1146,19 @@ def run_service(
                 ProcessIdentity(desktop_pid, desktop_start),
             ),
         )
-        if authority_emitter is not None and hasattr(server, "record_authority_event") and hasattr(server, "activity_epoch"):
-            authority_emitter.attach_live_sink(
-                server.record_authority_event,
-                handoff_epoch=server.activity_epoch,
-            )
-            authority_emitter.replay_pending()
+        # The listener is bound by CanonicalLiveServer construction, but it is
+        # not client-usable until its accept loop runs.  Start that loop before
+        # endpoint publication; the endpoint remains private until all durable
+        # authority bindings below are verified.
+        server_thread = threading.Thread(
+            target=_serve_service,
+            name="contextor-live-service",
+            daemon=True,
+        )
+        server_thread.start()
+        if not service_bootstrap_entered.wait(timeout=0.25):
+            raise RuntimeError("Canonical LIVE service thread did not enter bootstrap")
+        _raise_if_service_terminated("pre-endpoint bootstrap")
         published_endpoint = _authority_endpoint_from_server(
             server,
             identity,
@@ -1137,6 +1184,14 @@ def run_service(
             or current_record.endpoint_fingerprint != published_endpoint.fingerprint()
         ):
             raise RuntimeError("LIVE endpoint and RuntimeLease identity parity verification failed")
+        _raise_if_service_terminated("endpoint publication")
+        if authority_emitter is not None and hasattr(server, "record_authority_event") and hasattr(server, "activity_epoch"):
+            authority_emitter.attach_live_sink(
+                server.record_authority_event,
+                handoff_epoch=server.activity_epoch,
+            )
+            authority_emitter.replay_pending()
+        _raise_if_service_terminated("authority event handoff")
         if authority_emitter is not None:
             authority_emitter.emit(
                 "RUNTIME_AUTHORITY_READY",
@@ -1184,7 +1239,8 @@ def run_service(
                 name=f"contextor-live-watchdog-{owner_pid}",
                 daemon=True,
             ).start()
-        server.serve_forever()
+        server_thread.join()
+        _raise_if_service_terminated("service lifetime")
     except Exception as exc:
         if authority_emitter is not None:
             try:
@@ -1206,6 +1262,8 @@ def run_service(
             authority_emitter.detach_live_sink()
         if server is not None:
             server.close()
+        if server_thread is not None and server_thread.is_alive():
+            server_thread.join(timeout=1.0)
         if lease is not None:
             if published_endpoint is not None:
                 try:
@@ -1280,6 +1338,7 @@ def main() -> None:
     parser.add_argument("--owner-token", type=str, default=None)
     parser.add_argument("--desktop-instance-id", type=str, default=None)
     parser.add_argument("--desktop-process-start-identity", type=str, default=None)
+    parser.add_argument("--authority-start-recorded", action="store_true")
     args = parser.parse_args()
     run_service(
         args.repo,
@@ -1287,6 +1346,7 @@ def main() -> None:
         owner_token=args.owner_token,
         desktop_instance_id=args.desktop_instance_id,
         desktop_process_start_identity=args.desktop_process_start_identity,
+        authority_start_recorded=args.authority_start_recorded,
     )
 
 
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index 9f611c7..d795ba2 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -1,3 +1,4 @@
+import json
 import os
 import subprocess
 import sys
@@ -496,6 +497,7 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
             self.endpoint = SimpleNamespace(host="127.0.0.1", port=1, authkey_hex="00")
             self._stop = threading.Event()
         def serve_forever(self):
+            self._stop.set()
             return None
         def close(self):
             return None
@@ -561,6 +563,170 @@ def test_startup_backfill_failure_leaves_previous_generation_authoritative(tmp_p
     assert reloaded._state == before
 
 
+def _runtime_service_repo(tmp_path, monkeypatch):
+    from contextor.core.repository_identity import ensure_repository_identity
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    ensure_repository_identity(repo)
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
+    return repo
+
+
+def _authority_event_types(logs_root):
+    records = []
+    for path in logs_root.glob("contextor_runtime_*.jsonl"):
+        for line in path.read_text(encoding="utf-8").splitlines():
+            payload = json.loads(line)
+            if payload.get("_type") == "authority_event":
+                records.append(payload["event_type"])
+    return records
+
+
+def test_run_service_fails_closed_when_service_thread_raises_before_endpoint(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+    from contextor.core.paths import runtime_logs_dir
+
+    repo = _runtime_service_repo(tmp_path, monkeypatch)
+
+    class FailingServer(CanonicalLiveServer):
+        def serve_forever(self):
+            raise RuntimeError("synthetic service-thread startup failure")
+
+    monkeypatch.setattr(runtime, "CanonicalLiveServer", FailingServer)
+
+    with pytest.raises(RuntimeError, match="service thread failed during pre-endpoint bootstrap"):
+        runtime.run_service(repo)
+
+    assert not endpoint_file(repo).exists()
+    assert "RUNTIME_AUTHORITY_READY" not in _authority_event_types(runtime_logs_dir())
+
+
+def test_run_service_fails_closed_when_service_thread_dies_before_ready(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+    from contextor.core.paths import runtime_logs_dir
+
+    repo = _runtime_service_repo(tmp_path, monkeypatch)
+    release_failure = threading.Event()
+    failure_observed = threading.Event()
+    original_endpoint = runtime._authority_endpoint_from_server
+
+    class FailingServer(CanonicalLiveServer):
+        def serve_forever(self):
+            release_failure.wait(timeout=5.0)
+            try:
+                raise RuntimeError("synthetic service-thread pre-ready failure")
+            finally:
+                failure_observed.set()
+
+    def endpoint_then_release(*args, **kwargs):
+        endpoint = original_endpoint(*args, **kwargs)
+        release_failure.set()
+        assert failure_observed.wait(timeout=2.0)
+        return endpoint
+
+    monkeypatch.setattr(runtime, "CanonicalLiveServer", FailingServer)
+    monkeypatch.setattr(runtime, "_authority_endpoint_from_server", endpoint_then_release)
+
+    with pytest.raises(RuntimeError, match="service thread failed during endpoint publication"):
+        runtime.run_service(repo)
+
+    assert not endpoint_file(repo).exists()
+    assert "RUNTIME_AUTHORITY_READY" not in _authority_event_types(runtime_logs_dir())
+
+
+def test_normal_service_shutdown_preserves_authority_event_chronology(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+    from contextor.core.paths import runtime_logs_dir
+
+    repo = _runtime_service_repo(tmp_path, monkeypatch)
+    failures = []
+
+    def run():
+        try:
+            runtime.run_service(repo)
+        except BaseException as exc:
+            failures.append(exc)
+
+    service = threading.Thread(target=run, daemon=True)
+    service.start()
+    deadline = time.monotonic() + 5.0
+    client = None
+    while time.monotonic() < deadline:
+        client = runtime.connect(repo)
+        if client is not None:
+            break
+        time.sleep(0.02)
+    assert client is not None
+    assert client.request("shutdown").get("status") == "ok"
+    service.join(timeout=5.0)
+
+    assert not service.is_alive()
+    assert failures == []
+    assert not endpoint_file(repo).exists()
+    event_types = _authority_event_types(runtime_logs_dir())
+    assert event_types.index("RUNTIME_AUTHORITY_START") < event_types.index("RUNTIME_AUTHORITY_READY")
+
+
+def test_endpoint_before_authority_replay_exposes_valid_pending_live_feed(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+    import contextor.core.runtime_trace as runtime_trace
+    from contextor import mcp_server
+
+    repo = _runtime_service_repo(tmp_path, monkeypatch)
+    replay_entered = threading.Event()
+    release_replay = threading.Event()
+    failures = []
+    original_replay = runtime_trace.AuthorityEventEmitter.replay_pending
+
+    def gated_replay(self):
+        replay_entered.set()
+        assert release_replay.wait(timeout=5.0)
+        return original_replay(self)
+
+    def run():
+        try:
+            runtime.run_service(repo)
+        except BaseException as exc:
+            failures.append(exc)
+
+    monkeypatch.setattr(runtime_trace.AuthorityEventEmitter, "replay_pending", gated_replay)
+    service = threading.Thread(target=run, daemon=True)
+    service.start()
+    deadline = time.monotonic() + 5.0
+    while time.monotonic() < deadline and not (endpoint_file(repo).exists() and replay_entered.is_set()):
+        time.sleep(0.02)
+    assert endpoint_file(repo).exists()
+    assert replay_entered.is_set()
+
+    pending = json.loads(mcp_server.get_live_events.fn(str(repo)))
+    assert pending["status"] == "ok"
+    assert pending.get("continuity") in {None, "not_requested", "continuous"}
+
+    release_replay.set()
+    deadline = time.monotonic() + 5.0
+    completed = None
+    while time.monotonic() < deadline:
+        completed = json.loads(mcp_server.get_live_events.fn(str(repo)))
+        authority_events = [event for event in completed.get("events", []) if event.get("category") == "AUTHORITY"]
+        if authority_events:
+            break
+        time.sleep(0.02)
+    assert completed is not None
+    authority_events = [event for event in completed["events"] if event.get("category") == "AUTHORITY"]
+    keys = [(event["runtime_domain_id"], event["sequence"], event["event_id"]) for event in authority_events]
+    assert authority_events
+    assert len(keys) == len(set(keys))
+
+    client = runtime.connect(repo)
+    assert client is not None
+    assert client.request("shutdown").get("status") == "ok"
+    service.join(timeout=5.0)
+    assert not service.is_alive()
+    assert failures == []
+
+
 def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
     def update(state, file_path):
         state.files.append(file_path)

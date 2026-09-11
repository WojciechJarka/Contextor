STATUS=FIX_REQUIRED
PROJECT=Contextor
TASK=LIVE-O1 final certification only
BASE=4b507b65c07978ff15889c817a1bf80de034e67d
RUNTIME_RESTART_REQUIRED=YES
PRODUCTION_DIFF_UNCHANGED_FROM_PREVIOUS_CORRECTIVE=YES

CURRENT_OWNER_MAP
- IPC transport ownership: contextor/core/live_state/ipc.py::CanonicalLiveServer.serve_forever
- Service failure containment: contextor/core/live_state/runtime.py::run_service._serve_service
- Watcher recovery diagnostics: contextor/core/live_state/watcher.py::DesktopLiveWatcher._recover_client
- Trace header/key mapping: contextor/core/runtime_trace.py::_header_records and trace_event

CERTIFICATION_PROOFS
- Service fingerprint preparation failure: forced server.endpoint.fingerprint() failure; original synthetic serve_forever failure remains the RuntimeError cause through run_service.
- RECV diagnostic fail-open: recv transport failure plus trace_event failure still closes the connection and preserves the loop lifecycle.
- SEND diagnostic fail-open: response send transport failure plus trace_event failure still closes the connection and preserves the loop lifecycle.
- New proof command: .venv\\Scripts\\python.exe -m pytest -q tests/test_live_state_ipc.py::test_server_recv_and_send_trace_emitter_failure_are_fail_open tests/test_live_state_ipc.py::test_run_service_fingerprint_diagnostic_failure_does_not_mask_service_failure
- New proof result: 3 passed in 8.00s.

COMPLETE_CHANGED_FOCUSED_RESULTS
- tests/test_live_desktop_integration.py: 20 passed in 1.85s.
- tests/test_runtime_trace.py: 8 passed in 5.77s.
- tests/test_live_e2e_corrections.py: 15 passed, 1 warning in 53.47s.
- tests/test_live_state_ipc.py: 64 passed, 1 failed, 1 warning in 89.07s.
- Failing IPC node: test_connect_or_start_slow_healthy_startup timed out after its existing 2.0s cold-start budget only in the full file; it passed when rerun individually together with the other previously failed IPC node (2 passed in 6.53s).
- No full pytest run.

VERIFICATION
- Changed production modules compiled successfully with py_compile before final certification additions.
- Production/test diff was clean under git diff --check before embedding raw diffs; walkthrough raw-diff context can itself trigger whitespace diagnostics.
- No Desktop, LIVE, or MCP restart; no commit or push.

FILES_CHANGED
- contextor/core/live_state/ipc.py
- contextor/core/live_state/runtime.py
- contextor/core/live_state/watcher.py
- contextor/core/runtime_trace.py
- tests/test_live_desktop_integration.py
- tests/test_live_e2e_corrections.py
- tests/test_live_state_ipc.py
- tests/test_runtime_trace.py

FULL_DIFF
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index b48842c..1d1c584 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -651,21 +651,65 @@ class CanonicalLiveServer:
 
     def serve_forever(self) -> None:
         while not self._stop.is_set():
+            accept_started = time.monotonic()
             try:
                 connection = self._listener.accept()
-            except OSError:
+            except OSError as exc:
                 if self._stop.is_set():
                     break
+                _safe_trace_event(
+                    "LIVE", "LIVE_IPC_FAILURE", side="server",
+                    operation_or_request_type="accept", host=self.endpoint.host,
+                    port=self.endpoint.port, exception_class=type(exc).__name__,
+                    errno=getattr(exc, "errno", None),
+                    winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
+                    elapsed_ms=(time.monotonic() - accept_started) * 1000.0,
+                )
                 raise
+            request_type = "recv"
+            request_started = time.monotonic()
             try:
-                request = connection.recv()
-                response = self._dispatch(request)
-                connection.send(response)
-            except Exception as exc:
                 try:
-                    connection.send({"status": "error", "error": str(exc)})
-                except (EOFError, OSError):
-                    pass
+                    request = connection.recv()
+                except (OSError, EOFError, ConnectionError, TimeoutError) as exc:
+                    _safe_trace_event(
+                        "LIVE", "LIVE_IPC_FAILURE", side="server",
+                        operation_or_request_type="recv", host=self.endpoint.host,
+                        port=self.endpoint.port, exception_class=type(exc).__name__,
+                        errno=getattr(exc, "errno", None),
+                        winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
+                        elapsed_ms=(time.monotonic() - request_started) * 1000.0,
+                    )
+                    try:
+                        connection.send({"status": "error", "error": str(exc)})
+                    except (EOFError, OSError):
+                        pass
+                    continue
+                if isinstance(request, dict) and isinstance(request.get("operation"), str):
+                    request_type = request["operation"]
+                try:
+                    response = self._dispatch(request)
+                except Exception as exc:
+                    try:
+                        connection.send({"status": "error", "error": str(exc)})
+                    except (EOFError, OSError):
+                        pass
+                    continue
+                try:
+                    connection.send(response)
+                except (OSError, EOFError, ConnectionError, TimeoutError) as exc:
+                    _safe_trace_event(
+                        "LIVE", "LIVE_IPC_FAILURE", side="server",
+                        operation_or_request_type=(request_type if request_type != "recv" else "send"),
+                        host=self.endpoint.host, port=self.endpoint.port,
+                        exception_class=type(exc).__name__, errno=getattr(exc, "errno", None),
+                        winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
+                        elapsed_ms=(time.monotonic() - request_started) * 1000.0,
+                    )
+                    try:
+                        connection.send({"status": "error", "error": str(exc)})
+                    except (EOFError, OSError):
+                        pass
             finally:
                 connection.close()
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 0e9641f..3d9c0d4 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -1148,6 +1148,18 @@ def run_service(
             server.serve_forever()
         except BaseException as exc:
             failure = exc
+            try:
+                _safe_trace_event(
+                    "LIVE", "LIVE_SERVICE_THREAD_FAILURE",
+                    endpoint_fingerprint=server.endpoint.fingerprint(),
+                    service_pid=lease.service_pid if lease is not None else None,
+                    lease_generation=lease.lease_generation if lease is not None else None,
+                    service_instance_id=lease.service_instance_id if lease is not None else None,
+                    exception_class=type(exc).__name__, errno=getattr(exc, "errno", None),
+                    winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
+                )
+            except Exception:
+                pass
         finally:
             with service_state_lock:
                 if failure is not None:
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index d7e0c5c..50550eb 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -87,7 +87,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         if self.on_status is not None:
             self.on_status(message)
 
-    def _recover_client(self) -> LiveStateClient | None:
+    def _recover_client(self, trigger_exc: BaseException | None = None) -> LiveStateClient | None:
         """Attempt to reconnect or restart LIVE on genuine connection failure."""
         started = time.monotonic()
         prior_endpoint = getattr(self.client, "endpoint", None)
@@ -101,6 +101,10 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 prior_endpoint_fingerprint=(prior_endpoint.fingerprint() if prior_endpoint is not None else None),
                 prior_service_pid=getattr(prior_endpoint, "pid", None),
                 recovery_operation_id=recovery_operation_id,
+                exception_class=(type(trigger_exc).__name__ if trigger_exc is not None else None),
+                errno=(getattr(trigger_exc, "errno", None) if trigger_exc is not None else None),
+                winerror=(getattr(trigger_exc, "winerror", None) if trigger_exc is not None else None),
+                error=(str(trigger_exc)[:500] if trigger_exc is not None else None),
             )
         except Exception:
             recovery_operation_id = None
@@ -125,9 +129,9 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 trace_event(
                     "LIVE", "LIVE_WATCHER_RECOVERY_RESULT", op=recovery_operation_id,
                     result=(
-                        "reconnected_existing"
+                        "reconnected_same_endpoint"
                         if prior_endpoint is not None and new_endpoint == prior_endpoint
-                        else "started_new_owner"
+                        else "connected_changed_endpoint"
                     ),
                     new_endpoint_fingerprint=new_endpoint.fingerprint(),
                     new_service_pid=new_endpoint.pid,
@@ -265,7 +269,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         if snapshot is None:
             try:
                 snapshot = self.client.snapshot()
-            except (OSError, EOFError, TimeoutError, ConnectionError):
+            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                 return None
         manager = self._trusted_file_state(snapshot)
         if manager is None:
@@ -301,9 +305,9 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         ping_started = time.monotonic()
         try:
             status = self.client.ping()
-        except (OSError, EOFError, TimeoutError, ConnectionError):
+        except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
             self._emit("LIVE: connection lost; recovering...")
-            if self._recover_client() is None:
+            if self._recover_client(exc) is None:
                 raise
             status = self.client.ping()
         ping_ms = (time.monotonic() - ping_started) * 1000.0
@@ -330,7 +334,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
             current = self._scan()
             try:
                 snapshot = self.client.snapshot()
-            except (OSError, EOFError, TimeoutError, ConnectionError):
+            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                 self._emit("LIVE: startup resync baseline could not be verified")
                 return []
             if self._trusted_file_state(snapshot) is None:
@@ -417,7 +421,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                     trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), retry=True)
                 update_attempted = True
                 response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
-            except (OSError, EOFError, TimeoutError, ConnectionError):
+            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                 if update_attempted:
                     self._ambiguous_updates.add(path)
                     trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), exception="transport")
@@ -425,7 +429,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                     self._emit("LIVE: update outcome ambiguous; deferring revalidation")
                     continue
                 self._emit("LIVE: connection lost during update; recovering...")
-                if self._recover_client() is None:
+                if self._recover_client(exc) is None:
                     # Earlier candidates in this poll may already have received
                     # an acknowledged canonical response.  Preserve those
                     # per-path advances before surfacing the later pre-send
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 265aafa..a405684 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -1137,10 +1137,10 @@ def _append(record: dict[str, object], path: Path) -> None:
 def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str) -> list[dict[str, object]]:
     return [
         {"_type": "header", "schema": TRACE_SCHEMA, "purpose": "chronological Contextor Desktop/LIVE/MCP runtime diagnostics; one JSON object per line", "sid": sid, "started_at": started_at, "desktop_pid": desktop_pid, "file": file_name},
-        {"_type": "fields", "fields": {"ts": "UTC ISO-8601 milliseconds", "mono_ms": "host monotonic milliseconds", "sid": "desktop trace session", "pid": "process id", "tid": "thread id", "d": "domain", "ev": "event", "op": "operation correlation id", "repo": "repository", "path": "repository-relative path", "kind": "change kind", "tool": "MCP tool", "rev": "observed canonical revision", "rev0": "canonical revision before transition", "rev1": "canonical revision after transition", "candidate_rev": "rejected candidate canonical revision", "seq": "activity-journal sequence", "q": "GUI queue size", "count": "count", "bytes": "byte count", "wait_ms": "queue wait milliseconds", "elapsed_ms": "elapsed milliseconds", "scan_ms": "watcher scan milliseconds", "ping_ms": "watcher ping milliseconds", "status": "compact status", "err": "bounded error", "mtime_ns": "observed file mtime"}},
+        {"_type": "fields", "fields": {"ts": "UTC ISO-8601 milliseconds", "mono_ms": "host monotonic milliseconds", "sid": "desktop trace session", "pid": "process id", "tid": "thread id", "d": "domain", "ev": "event", "op": "operation correlation id", "repo": "repository", "path": "repository-relative path", "kind": "change kind", "tool": "MCP tool", "rev": "observed canonical revision", "rev0": "canonical revision before transition", "rev1": "canonical revision after transition", "candidate_rev": "rejected candidate canonical revision", "seq": "activity-journal sequence", "q": "GUI queue size", "count": "count", "bytes": "byte count", "wait_ms": "queue wait milliseconds", "elapsed_ms": "elapsed milliseconds", "scan_ms": "watcher scan milliseconds", "ping_ms": "watcher ping milliseconds", "status": "compact status", "err": "bounded error", "mtime_ns": "observed file mtime", "attempt": "connection attempt number", "attempts": "connection attempt budget", "attempts_used": "attempt count consumed", "retry_delay": "retry delay seconds", "runtime_domain_id": "runtime domain identity", "repo_id": "repository identity", "endpoint_fingerprint": "hashed endpoint identity", "service_pid": "LIVE service process id", "lease_generation": "LIVE lease generation", "service_instance_id": "LIVE service instance", "reason_code": "stable diagnostic reason", "exception_class": "exception class", "errno": "OS errno", "winerror": "Windows error", "error": "bounded error text", "pid_alive": "service PID liveness", "endpoint_changed": "endpoint identity changed", "process_alive": "service process liveness", "process_identity_matches": "process start identity matches", "endpoint_available": "endpoint metadata available", "endpoint_matches": "endpoint identity matches", "reason": "evidence-neutral reason", "result": "evidence-neutral result", "side": "IPC side", "operation_or_request_type": "IPC request or transport stage", "host": "IPC endpoint host", "port": "IPC endpoint port", "prior_endpoint_fingerprint": "previous hashed endpoint identity", "prior_service_pid": "previous LIVE service process id", "new_endpoint_fingerprint": "new hashed endpoint identity", "new_service_pid": "new LIVE service process id", "recovery_operation_id": "watcher recovery operation correlation id"}},
         {"_type": "domains", "domains": ["DESKTOP", "LIVE", "MCP", "GUI"], "reserved": ["OPS"], "ops_note": "Reserved for future repository-operation coordination; not implemented here."},
         {"_type": "revision_semantics", "rev": "observed authoritative canonical revision", "rev0": "authoritative canonical revision before transition", "rev1": "authoritative canonical revision after transition", "seq": "independent activity-journal sequence", "logger_rule": "The logger never calculates or increments canonical revision or activity sequence."},
-        {"_type": "events", "events": {"DESKTOP": ["SESSION_START", "SESSION_END"], "LIVE": ["FS_CHANGE_DETECTED", "WATCH_UPDATE_START", "WATCH_UPDATE_END", "WATCH_UPDATE_FAIL", "UPDATE_RECEIVED", "UPDATE_FAIL", "CLONE_END", "UPDATER_START", "UPDATER_END", "UPDATER_FAIL", "ENGINE_READY", "INCREMENTAL_END", "PERSIST_START", "SNAPSHOT_SAVE_END", "FILE_STATE_SAVE_END", "PERSIST_END", "CANONICAL_COMMIT", "UPDATE_PUBLISHED", "PUBLISH_RECEIVED", "CANONICAL_PUBLISH", "PUBLISH_FAIL", "ACTIVITY_APPEND", "SERVICE_START", "SERVICE_END"], "MCP": ["CALL_START", "IMPLEMENTATION_END", "DIAGNOSTICS_END", "TELEMETRY_END", "CALL_END", "CALL_FAIL"], "GUI": ["EVENT_BATCH_RECEIVED", "ACTIVITY_GAP", "STATUS_QUEUED", "STATUS_RENDERED"]}},
+        {"_type": "events", "events": {"DESKTOP": ["SESSION_START", "SESSION_END"], "LIVE": ["FS_CHANGE_DETECTED", "WATCH_UPDATE_START", "WATCH_UPDATE_END", "WATCH_UPDATE_FAIL", "UPDATE_RECEIVED", "UPDATE_FAIL", "CLONE_END", "UPDATER_START", "UPDATER_END", "UPDATER_FAIL", "ENGINE_READY", "INCREMENTAL_END", "PERSIST_START", "SNAPSHOT_SAVE_END", "FILE_STATE_SAVE_END", "PERSIST_END", "CANONICAL_COMMIT", "UPDATE_PUBLISHED", "PUBLISH_RECEIVED", "CANONICAL_PUBLISH", "PUBLISH_FAIL", "ACTIVITY_APPEND", "SERVICE_START", "SERVICE_END", "LIVE_CONNECT_ATTEMPT", "LIVE_CONNECT_REJECT", "LIVE_CONNECT_RESULT", "LIVE_LIVENESS_RESULT", "LIVE_WATCHER_RECOVERY_START", "LIVE_WATCHER_RECOVERY_RESULT", "LIVE_IPC_FAILURE", "LIVE_SERVICE_THREAD_FAILURE"], "MCP": ["CALL_START", "IMPLEMENTATION_END", "DIAGNOSTICS_END", "TELEMETRY_END", "CALL_END", "CALL_FAIL"], "GUI": ["EVENT_BATCH_RECEIVED", "ACTIVITY_GAP", "STATUS_QUEUED", "STATUS_RENDERED"]}},
     ]
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index 11e2d4e..e9d96ed 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -49,10 +49,54 @@ def test_watcher_recovery_emits_start_and_existing_result(tmp_path, monkeypatch)
     assert [event for _domain, event, _fields in events] == [
         "LIVE_WATCHER_RECOVERY_START", "LIVE_WATCHER_RECOVERY_RESULT"
     ]
-    assert events[1][2]["result"] == "reconnected_existing"
+    assert events[1][2]["result"] == "reconnected_same_endpoint"
     assert events[1][2]["new_endpoint_fingerprint"] == "endpoint-fingerprint"
 
 
+def test_watcher_recovery_records_trigger_and_changed_endpoint(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+
+    class Endpoint:
+        def __init__(self, pid, fingerprint):
+            self.pid = pid
+            self.lease_generation = 7
+            self._fingerprint = fingerprint
+        def fingerprint(self):
+            return self._fingerprint
+
+    initial = SimpleNamespace(endpoint=Endpoint(1234, "before"), snapshot=lambda: {"status": "ok", "state": None})
+    recovered = SimpleNamespace(endpoint=Endpoint(5678, "after"))
+    watcher = DesktopLiveWatcher(repo, initial)
+    events = []
+    import contextor.core.runtime_trace as trace
+    import contextor.core.live_state.runtime as runtime
+
+    failure = ConnectionRefusedError(10061, "refused")
+    monkeypatch.setattr(runtime, "connect_or_start", lambda *_args, **_kwargs: recovered)
+    monkeypatch.setattr(trace, "new_trace_operation", lambda _prefix: "wr-test")
+    monkeypatch.setattr(trace, "trace_event", lambda domain, event, **fields: events.append((domain, event, fields)))
+
+    assert watcher._recover_client(failure) is recovered
+    assert events[0][2]["exception_class"] == "ConnectionRefusedError"
+    assert events[0][2]["errno"] == 10061
+    assert events[0][2]["error"].endswith("refused")
+    assert events[1][2]["result"] == "connected_changed_endpoint"
+
+
+def test_watcher_trace_emitter_failure_is_fail_open(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    endpoint = SimpleNamespace(pid=1234, lease_generation=7, fingerprint=lambda: "endpoint")
+    watcher = DesktopLiveWatcher(repo, SimpleNamespace(endpoint=endpoint, snapshot=lambda: {"status": "ok", "state": None}))
+    import contextor.core.runtime_trace as trace
+    import contextor.core.live_state.runtime as runtime
+
+    monkeypatch.setattr(runtime, "connect_or_start", lambda *_args, **_kwargs: SimpleNamespace(endpoint=endpoint))
+    monkeypatch.setattr(trace, "trace_event", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace failed")))
+    assert watcher._recover_client(ConnectionRefusedError(10061, "refused")) is watcher.client
+
+
 def test_same_revision_startup_attaches_without_redundant_publish(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
     repo.mkdir()
@@ -620,7 +664,7 @@ def test_desktop_watcher_recovers_after_live_service_death(tmp_path):
 
     recovery_called = []
 
-    def mock_recover():
+    def mock_recover(_trigger_exc=None):
         recovery_called.append(True)
         watcher.client = recovered_client
         if watcher.on_reconnect:
@@ -666,7 +710,7 @@ def test_desktop_watcher_recovery_preserves_unowned_if_another_service_wins_race
         on_reconnect=lambda c: reconnected_clients.append(c),
     )
 
-    def mock_recover():
+    def mock_recover(_trigger_exc=None):
         watcher.client = external_client
         if watcher.on_reconnect:
             watcher.on_reconnect(external_client)
diff --git a/tests/test_live_e2e_corrections.py b/tests/test_live_e2e_corrections.py
index fa431a0..827e24d 100644
--- a/tests/test_live_e2e_corrections.py
+++ b/tests/test_live_e2e_corrections.py
@@ -436,8 +436,8 @@ def test_verified_client_transport_rejection_serializes_bounded_trace(
 
     endpoint = authoritative_live_client.endpoint
     trace_logs = tmp_path / "isolated-trace"
-    finish_desktop_trace_session()
     monkeypatch.setattr(trace, "runtime_logs_dir", lambda: trace_logs)
+    finish_desktop_trace_session()
     path = start_desktop_trace_session()
     assert path is not None
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index e359def..1d5ed40 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -70,6 +70,153 @@ def test_client_transport_failure_emits_one_bounded_trace_event(monkeypatch):
     assert "authkey" not in json.dumps(events[0]).lower()
 
 
+def test_server_accept_failure_emits_once_and_reraises(monkeypatch):
+    events = []
+    server = CanonicalLiveServer(SimpleNamespace(files=[]))
+
+    class Listener:
+        def accept(self):
+            raise OSError(10061, "refused")
+
+        def close(self):
+            pass
+
+    server._listener = Listener()
+    monkeypatch.setattr(ipc_module, "_safe_trace_event", lambda *_args, **kwargs: events.append(kwargs))
+    try:
+        with pytest.raises(OSError):
+            server.serve_forever()
+    finally:
+        server.close()
+
+    assert len(events) == 1
+    assert events[0]["side"] == "server"
+    assert events[0]["operation_or_request_type"] == "accept"
+
+
+def test_server_stopped_accept_path_emits_no_incident(monkeypatch):
+    events = []
+    server = CanonicalLiveServer(SimpleNamespace(files=[]))
+    monkeypatch.setattr(ipc_module, "_safe_trace_event", lambda *_args, **kwargs: events.append(kwargs))
+    class Listener:
+        def accept(self):
+            server._stop.set()
+            raise OSError(10061, "stopped")
+
+        def close(self):
+            pass
+    server._listener = Listener()
+    try:
+        server.serve_forever()
+    finally:
+        server.close()
+
+    assert events == []
+
+
+@pytest.mark.parametrize("failure", [OSError("dispatch"), TimeoutError("dispatch")])
+def test_server_dispatch_transport_shaped_error_is_not_ipc_failure(monkeypatch, failure):
+    events, sent = [], []
+    server = CanonicalLiveServer(SimpleNamespace(files=[]))
+    class Connection:
+        def recv(self): return {"operation": "ping"}
+        def send(self, value): sent.append(value)
+        def close(self): server._stop.set()
+    class Listener:
+        def accept(self): return Connection()
+        def close(self): pass
+    server._listener = Listener()
+    monkeypatch.setattr(server, "_dispatch", lambda _request: (_ for _ in ()).throw(failure))
+    monkeypatch.setattr(ipc_module, "_safe_trace_event", lambda *_args, **kwargs: events.append(kwargs))
+    server.serve_forever()
+    assert events == []
+    assert sent and sent[0]["status"] == "error"
+
+
+@pytest.mark.parametrize("stage", ["recv", "send"])
+def test_server_transport_boundary_emits_once(monkeypatch, stage):
+    events = []
+    server = CanonicalLiveServer(SimpleNamespace(files=[]))
+    class Connection:
+        closed = False
+        def recv(self):
+            if stage == "recv": raise ConnectionResetError("recv")
+            return {"operation": "ping"}
+        def send(self, _value):
+            if stage == "send": raise ConnectionResetError("send")
+        def close(self):
+            self.closed = True
+            server._stop.set()
+    class Listener:
+        connection = Connection()
+        def accept(self): return self.connection
+        def close(self): pass
+    listener = Listener()
+    server._listener = listener
+    monkeypatch.setattr(ipc_module, "_safe_trace_event", lambda *_args, **kwargs: events.append(kwargs))
+    server.serve_forever()
+    assert len(events) == 1 and events[0]["side"] == "server"
+    assert events[0]["operation_or_request_type"] == ("recv" if stage == "recv" else "ping")
+    assert listener.connection.closed is True
+
+
+def test_server_trace_emitter_failure_does_not_mask_transport_failure(monkeypatch):
+    import contextor.core.runtime_trace as trace
+    server = CanonicalLiveServer(SimpleNamespace(files=[]))
+    class Listener:
+        def accept(self):
+            raise OSError(10061, "refused")
+        def close(self):
+            pass
+    server._listener = Listener()
+    monkeypatch.setattr(trace, "trace_event", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace failed")))
+    with pytest.raises(OSError, match="refused"):
+        server.serve_forever()
+
+
+@pytest.mark.parametrize("stage", ["recv", "send"])
+def test_server_recv_and_send_trace_emitter_failure_are_fail_open(monkeypatch, stage):
+    import contextor.core.runtime_trace as trace
+
+    server = CanonicalLiveServer(SimpleNamespace(files=[]))
+
+    class Connection:
+        closed = False
+
+        def recv(self):
+            if stage == "recv":
+                raise ConnectionResetError("recv transport failure")
+            return {"operation": "ping"}
+
+        def send(self, _value):
+            if stage == "send":
+                raise ConnectionResetError("send transport failure")
+
+        def close(self):
+            self.closed = True
+            server._stop.set()
+
+    class Listener:
+        connection = Connection()
+
+        def accept(self):
+            return self.connection
+
+        def close(self):
+            pass
+
+    listener = Listener()
+    server._listener = listener
+    monkeypatch.setattr(
+        trace,
+        "trace_event",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace failed")),
+    )
+
+    server.serve_forever()
+    assert listener.connection.closed is True
+
+
 @pytest.fixture
 def live_server():
     server = CanonicalLiveServer(SimpleNamespace(files=[]))
@@ -644,18 +791,79 @@ def test_run_service_fails_closed_when_service_thread_raises_before_endpoint(tmp
     from contextor.core.paths import runtime_logs_dir
 
     repo = _runtime_service_repo(tmp_path, monkeypatch)
+    events = []
 
     class FailingServer(CanonicalLiveServer):
         def serve_forever(self):
             raise RuntimeError("synthetic service-thread startup failure")
 
     monkeypatch.setattr(runtime, "CanonicalLiveServer", FailingServer)
+    monkeypatch.setattr(
+        runtime, "_safe_trace_event",
+        lambda domain, event, **fields: events.append((domain, event, fields)),
+    )
 
-    with pytest.raises(RuntimeError, match="service thread failed during pre-endpoint bootstrap"):
+    with pytest.raises(RuntimeError, match="service thread failed during (pre-endpoint bootstrap|endpoint publication)"):
         runtime.run_service(repo)
 
     assert not endpoint_file(repo).exists()
     assert "RUNTIME_AUTHORITY_READY" not in _authority_event_types(runtime_logs_dir())
+    assert [(domain, event) for domain, event, _fields in events] == [
+        ("LIVE", "LIVE_SERVICE_THREAD_FAILURE")
+    ]
+    assert events[0][2]["exception_class"] == "RuntimeError"
+
+
+def test_run_service_trace_emitter_failure_does_not_mask_service_failure(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+
+    repo = _runtime_service_repo(tmp_path, monkeypatch)
+
+    class FailingServer(CanonicalLiveServer):
+        def serve_forever(self):
+            raise RuntimeError("synthetic service-thread startup failure")
+
+    monkeypatch.setattr(runtime, "CanonicalLiveServer", FailingServer)
+    monkeypatch.setattr(
+        runtime,
+        "_safe_trace_event",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace failed")),
+    )
+
+    with pytest.raises(RuntimeError, match="service thread failed during (pre-endpoint bootstrap|endpoint publication)"):
+        runtime.run_service(repo)
+    assert not endpoint_file(repo).exists()
+
+
+def test_run_service_fingerprint_diagnostic_failure_does_not_mask_service_failure(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+
+    repo = _runtime_service_repo(tmp_path, monkeypatch)
+    release_failure = threading.Event()
+    original_endpoint = runtime._authority_endpoint_from_server
+
+    class FailingServer(CanonicalLiveServer):
+        def serve_forever(self):
+            release_failure.wait(timeout=5.0)
+            raise RuntimeError("synthetic service-thread fingerprint failure")
+
+    def endpoint_then_poison_fingerprint(server, *args, **kwargs):
+        endpoint = original_endpoint(server, *args, **kwargs)
+        server.endpoint = SimpleNamespace(
+            fingerprint=lambda: (_ for _ in ()).throw(RuntimeError("fingerprint failed"))
+        )
+        release_failure.set()
+        return endpoint
+
+    monkeypatch.setattr(runtime, "CanonicalLiveServer", FailingServer)
+    monkeypatch.setattr(runtime, "_authority_endpoint_from_server", endpoint_then_poison_fingerprint)
+
+    with pytest.raises(RuntimeError, match="service thread failed during endpoint publication") as raised:
+        runtime.run_service(repo)
+
+    assert isinstance(raised.value.__cause__, RuntimeError)
+    assert str(raised.value.__cause__) == "synthetic service-thread fingerprint failure"
+    assert not endpoint_file(repo).exists()
 
 
 def test_run_service_fails_closed_when_service_thread_dies_before_ready(tmp_path, monkeypatch):
diff --git a/tests/test_runtime_trace.py b/tests/test_runtime_trace.py
index 27fb31f..6d83d8b 100644
--- a/tests/test_runtime_trace.py
+++ b/tests/test_runtime_trace.py
@@ -46,6 +46,9 @@ def test_desktop_trace_session_headers_and_finish(tmp_path, monkeypatch):
     assert trace.active_trace_path(force_refresh=True) is None
     assert not (tmp_path / "logs" / "contextor_runtime_active.json").exists()
     assert len(records[6]["err"]) == 500
+    fields, events = records[1]["fields"], records[4]["events"]["LIVE"]
+    assert {"attempt", "attempts", "attempts_used", "retry_delay", "runtime_domain_id", "repo_id", "endpoint_fingerprint", "service_pid", "lease_generation", "service_instance_id", "reason_code", "exception_class", "errno", "winerror", "error", "pid_alive", "endpoint_changed", "process_alive", "process_identity_matches", "endpoint_available", "endpoint_matches", "reason", "result", "side", "operation_or_request_type", "prior_endpoint_fingerprint", "prior_service_pid", "new_endpoint_fingerprint", "new_service_pid", "recovery_operation_id"} <= set(fields)
+    assert {"LIVE_CONNECT_ATTEMPT", "LIVE_CONNECT_REJECT", "LIVE_CONNECT_RESULT", "LIVE_LIVENESS_RESULT", "LIVE_WATCHER_RECOVERY_START", "LIVE_WATCHER_RECOVERY_RESULT", "LIVE_IPC_FAILURE", "LIVE_SERVICE_THREAD_FAILURE"} <= set(events)
 
 
 def test_default_trace_session_uses_external_runtime_logs_root(tmp_path, monkeypatch):

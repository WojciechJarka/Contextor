# LIVE-O1 — instrument intermittent LIVE owner/IPC reachability failures

BASE=fe87c92aa1be248c22b5601655bd3ce6dc7d93b8
STATUS=COMPLETE
RUNTIME_RESTART_REQUIRED=YES

## CURRENT_OWNER_MAP

- Existing-owner validation/retry: `contextor.core.live_state.runtime._verified_existing_client` and `connect_existing_with_status`.
- Fail-closed lease liveness: `AuthorityLivenessVerifier.verify`.
- Watcher reconnect/start: `DesktopLiveWatcher._recover_client`.
- IPC transport client boundary: `LiveStateClient.request`.
- Durable logger: `contextor.core.runtime_trace.trace_event`.

## TRACE_SESSION_ROOT_CAUSE

Repository `logs\\contextor_runtime_*.jsonl` was stale because runtime traces are intentionally published under `%APPDATA%\\Contextor\\logs` via `runtime_logs_dir()`, not the repository root. Fresh 2026-09-10/11 sessions and the active pointer were present there. Desktop startup already calls `start_desktop_trace_session()` once and calls `finish_desktop_trace_session()` in its matching finally block; no startup wiring change was needed.

## EVENT_MAP

- `LIVE_CONNECT_ATTEMPT`: each existing-owner retry; domain/repo, endpoint fingerprint, PID, generation and retry data.
- `LIVE_CONNECT_REJECT`: endpoint/schema/domain/process/authority/lease rejection, with bounded exception metadata where available.
- `LIVE_CONNECT_RESULT`: every final status with actual existing status and elapsed time.
- `LIVE_LIVENESS_RESULT`: exactly one event for each returned liveness result.
- `LIVE_WATCHER_RECOVERY_START` / `LIVE_WATCHER_RECOVERY_RESULT`: recovery correlation, endpoint transition, actual reconnect/new-owner/failure outcome.
- `LIVE_IPC_FAILURE`: one client-side authenticated IPC transport boundary event.
- `runtime_trace.trace_event` now serializes only the new explicitly allowlisted diagnostic fields. No secret-bearing fields are allowlisted.

## BEHAVIOR_EQUIVALENCE_EVIDENCE

No retry delay/count, timeout, lease policy, UNKNOWN/STALE decision, endpoint mutation, takeover condition, state transition, or MCP schema changed. Trace is best-effort through existing safe wrappers. The IPC transport catch re-raises the original exception after tracing; connection close remains in the existing finally path.

## FOCUSED_TESTS

- `pytest -q tests\\test_live_state_ipc.py::test_client_request_timeout_closes_connection tests\\test_live_state_ipc.py::test_client_transport_failure_emits_one_bounded_trace_event` — 2 passed.
- `pytest -q tests\\test_live_e2e_corrections.py::test_same_owner_identity_allows_transient_classification tests\\test_live_e2e_corrections.py::test_verified_client_transport_rejection_serializes_bounded_trace` — 2 passed.
- `pytest -q tests\\test_live_e2e_corrections.py::test_trace_failure_cannot_change_transient_connection_result` — 1 passed.
- `pytest -q tests\\test_live_authority_bootstrap.py::test_foreign_live_endpoint_blocks_stale_takeover tests\\test_runtime_trace.py::test_desktop_trace_session_headers_and_finish` — 2 passed.
- `pytest -q tests\\test_live_desktop_integration.py::test_watcher_recovery_emits_start_and_existing_result` — 1 passed.
- `python -m py_compile contextor\\core\\live_state\\runtime.py contextor\\core\\live_state\\watcher.py contextor\\core\\live_state\\ipc.py` — passed.
- `git diff --check` — passed.

## RUNTIME_TRACE_SERIALIZATION_EVIDENCE

An isolated `runtime_logs_dir` session was created in a test. An injected `ConnectionRefusedError` in authority-status verification preserved the existing `None` result and emitted JSONL `LIVE_CONNECT_REJECT` with `reason_code=AUTHORITY_STATUS_TRANSPORT_ERROR` and `exception_class=ConnectionRefusedError`. The event contained neither `authkey` nor `owner_token`.

## LIVE_CHECK

`get_live_events(limit=5)` returned `status=ok`, revision 616, and no resync requirement after the focused batches. Historical authority events retain the pre-existing fail-closed `UNKNOWN`/WinError 10061 incident evidence; this task did not mutate the running service or attempt a restart.

## FILES_CHANGED

- `contextor/core/live_state/runtime.py`
- `contextor/core/live_state/watcher.py`
- `contextor/core/live_state/ipc.py`
- `contextor/core/runtime_trace.py`
- `tests/test_live_e2e_corrections.py`
- `tests/test_live_state_ipc.py`
- `tests/test_live_desktop_integration.py`

## FULL_DIFF

```diff
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index d910e3f..b48842c 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -1104,5 +1104 @@ class LiveStateClient:
-        connection = Client(
-            self.endpoint.address,
-            family="AF_INET",
-            authkey=self.endpoint.authkey,
-        )
+        started = time.monotonic()
@@ -1110,11 +1106,28 @@ class LiveStateClient:
-            connection.send({"operation": operation, **payload})
-            import multiprocessing.connection as mpc
-            ready = mpc.wait([connection], timeout=timeout)
-            if not ready:
-                raise TimeoutError(
-                    "Canonical LIVE service did not respond within "
-                    f"{timeout:g}s for op={operation}"
-                )
-            response = connection.recv()
-        finally:
-            connection.close()
+            connection = Client(
+                self.endpoint.address,
+                family="AF_INET",
+                authkey=self.endpoint.authkey,
+            )
+            try:
+                connection.send({"operation": operation, **payload})
+                import multiprocessing.connection as mpc
+                ready = mpc.wait([connection], timeout=timeout)
+                if not ready:
+                    raise TimeoutError(
+                        "Canonical LIVE service did not respond within "
+                        f"{timeout:g}s for op={operation}"
+                    )
+                response = connection.recv()
+            finally:
+                connection.close()
+        except (OSError, EOFError, ConnectionError, TimeoutError) as exc:
+            _safe_trace_event(
+                "LIVE", "LIVE_IPC_FAILURE",
+                side="client", operation_or_request_type=operation,
+                host=getattr(self.endpoint, "host", self.endpoint.address[0]),
+                port=getattr(self.endpoint, "port", self.endpoint.address[1]),
+                exception_class=type(exc).__name__, errno=getattr(exc, "errno", None),
+                winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
+                elapsed_ms=(time.monotonic() - started) * 1000.0,
+            )
+            raise
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index ee946d6..0e9641f 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -70,0 +71,23 @@ def _safe_trace_event(domain: str, event: str, **fields) -> None:
+def _trace_exception_fields(exc: BaseException | None) -> dict[str, object]:
+    """Return bounded, non-secret transport diagnostics."""
+    if exc is None:
+        return {}
+    return {
+        "exception_class": type(exc).__name__,
+        "errno": getattr(exc, "errno", None),
+        "winerror": getattr(exc, "winerror", None),
+        "error": str(exc)[:500],
+    }
+
+
+def _trace_endpoint_fields(endpoint: LiveEndpoint | None) -> dict[str, object]:
+    if endpoint is None:
+        return {}
+    return {
+        "endpoint_fingerprint": endpoint.fingerprint(),
+        "service_pid": endpoint.pid,
+        "lease_generation": endpoint.lease_generation,
+        "service_instance_id": endpoint.service_instance_id,
+    }
+
+
@@ -357,0 +381,15 @@ class AuthorityLivenessVerifier:
+        def finish(result: LivenessResult, endpoint: LiveEndpoint | None = None, exc: BaseException | None = None) -> LivenessResult:
+            fields = {
+                "status": result.status.value,
+                "process_alive": result.process_alive,
+                "process_identity_matches": result.process_identity_matches,
+                "endpoint_available": result.endpoint_available,
+                "endpoint_matches": result.endpoint_matches,
+                "reason": result.reason,
+                "service_pid": lease.service_pid,
+                "lease_generation": lease.lease_generation,
+            }
+            fields.update(_trace_endpoint_fields(endpoint))
+            fields.update(_trace_exception_fields(exc))
+            _safe_trace_event("LIVE", "LIVE_LIVENESS_RESULT", **fields)
+            return result
@@ -361 +399 @@ class AuthorityLivenessVerifier:
-            return LivenessResult(
+            return finish(LivenessResult(
@@ -368 +406 @@ class AuthorityLivenessVerifier:
-            )
+            ), exc=exc)
@@ -381 +419 @@ class AuthorityLivenessVerifier:
-                return LivenessResult.stale(
+                return finish(LivenessResult.stale(
@@ -388,2 +426,2 @@ class AuthorityLivenessVerifier:
-                )
-            return LivenessResult(
+                ), endpoint)
+            return finish(LivenessResult(
@@ -396 +434 @@ class AuthorityLivenessVerifier:
-            )
+            ), endpoint)
@@ -414 +452 @@ class AuthorityLivenessVerifier:
-                return LivenessResult.stale(
+                return finish(LivenessResult.stale(
@@ -421 +459 @@ class AuthorityLivenessVerifier:
-                )
+                ), endpoint, exc)
@@ -423 +461 @@ class AuthorityLivenessVerifier:
-                return LivenessResult.stale(
+                return finish(LivenessResult.stale(
@@ -430,2 +468,2 @@ class AuthorityLivenessVerifier:
-                )
-            return LivenessResult(
+                ), endpoint, exc)
+            return finish(LivenessResult(
@@ -438 +476 @@ class AuthorityLivenessVerifier:
-            )
+            ), endpoint, exc)
@@ -443 +481 @@ class AuthorityLivenessVerifier:
-                return LivenessResult(
+                return finish(LivenessResult(
@@ -451,2 +489,2 @@ class AuthorityLivenessVerifier:
-                )
-            return LivenessResult(
+                ), endpoint)
+            return finish(LivenessResult(
@@ -460 +498 @@ class AuthorityLivenessVerifier:
-            )
+            ), endpoint)
@@ -462,2 +500,2 @@ class AuthorityLivenessVerifier:
-            return LivenessResult.live("exact process identity and authority status match")
-        return LivenessResult(
+            return finish(LivenessResult.live("exact process identity and authority status match"), endpoint)
+        return finish(LivenessResult(
@@ -470 +508 @@ class AuthorityLivenessVerifier:
-        )
+        ), endpoint)
@@ -481,0 +520,11 @@ def _verified_existing_client(
+    started = time.monotonic()
+
+    def reject(reason_code: str, endpoint: LiveEndpoint | None = None, exc: BaseException | None = None, **fields: object) -> None:
+        event_fields = {
+            "reason_code": reason_code,
+            "elapsed_ms": (time.monotonic() - started) * 1000.0,
+        }
+        event_fields.update(_trace_endpoint_fields(endpoint))
+        event_fields.update(fields)
+        event_fields.update(_trace_exception_fields(exc))
+        _safe_trace_event("LIVE", "LIVE_CONNECT_REJECT", **event_fields)
@@ -485,0 +535 @@ def _verified_existing_client(
+            reject("ENDPOINT_SCHEMA_INVALID", exc=exc)
@@ -486,0 +537 @@ def _verified_existing_client(
+        reject("ENDPOINT_SCHEMA_INVALID", exc=exc)
@@ -488 +539,5 @@ def _verified_existing_client(
-    if endpoint is None or not _endpoint_matches_domain(endpoint, domain):
+    if endpoint is None:
+        reject("ENDPOINT_MISSING")
+        return None
+    if not _endpoint_matches_domain(endpoint, domain):
+        reject("DOMAIN_MISMATCH", endpoint)
@@ -504 +559,2 @@ def _verified_existing_client(
-    except Exception:
+    except Exception as exc:
+        reject("LEASE_MISMATCH", endpoint, exc)
@@ -508 +564,2 @@ def _verified_existing_client(
-    except Exception:
+    except Exception as exc:
+        reject("PROCESS_IDENTITY_MISMATCH", endpoint, exc)
@@ -510,0 +568 @@ def _verified_existing_client(
+        reject("PROCESS_IDENTITY_MISMATCH", endpoint, pid_alive=bool(alive))
@@ -514 +572,2 @@ def _verified_existing_client(
-    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
+        reject("AUTHORITY_STATUS_TRANSPORT_ERROR", endpoint, exc, pid_alive=True)
@@ -516,0 +576 @@ def _verified_existing_client(
+        reject("AUTHORITY_STATUS_MISMATCH", endpoint, pid_alive=True)
@@ -521 +581,2 @@ def _verified_existing_client(
-    except Exception:
+    except Exception as exc:
+        reject("LEASE_MISMATCH", endpoint, exc, pid_alive=True)
@@ -523,0 +585 @@ def _verified_existing_client(
+        reject("LEASE_MISMATCH", endpoint, pid_alive=True)
@@ -534,0 +597 @@ def _verified_existing_client(
+        reject("LEASE_MISMATCH", endpoint, pid_alive=True)
@@ -600,0 +664,12 @@ def connect_existing_with_status(
+    started = time.monotonic()
+
+    def result(client: LiveStateClient | None, status: str, attempts_used: int, endpoint: LiveEndpoint | None = None) -> tuple[LiveStateClient | None, str]:
+        _safe_trace_event(
+            "LIVE", "LIVE_CONNECT_RESULT",
+            result=status,
+            attempts_used=attempts_used,
+            elapsed_ms=(time.monotonic() - started) * 1000.0,
+            **_trace_endpoint_fields(endpoint),
+        )
+        return client, status
+
@@ -604 +679 @@ def connect_existing_with_status(
-        return None, "endpoint_identity_unverified"
+        return result(None, "endpoint_identity_unverified", 0)
@@ -613 +688 @@ def connect_existing_with_status(
-        return None, "endpoint_identity_unverified"
+        return result(None, "endpoint_identity_unverified", 0)
@@ -615 +690 @@ def connect_existing_with_status(
-        return None, "no_live_service"
+        return result(None, "no_live_service", 0)
@@ -617 +692 @@ def connect_existing_with_status(
-        return None, "endpoint_identity_unverified"
+        return result(None, "endpoint_identity_unverified", 0, expected)
@@ -620,0 +696,9 @@ def connect_existing_with_status(
+        _safe_trace_event(
+            "LIVE", "LIVE_CONNECT_ATTEMPT",
+            attempt=attempt + 1,
+            attempts=total_attempts,
+            retry_delay=retry_delay,
+            runtime_domain_id=domain.domain_id,
+            repo_id=identity.repo_id,
+            **_trace_endpoint_fields(expected),
+        )
@@ -625,2 +709,6 @@ def connect_existing_with_status(
-                return None, "owner_identity_changed"
-            return client, "connected"
+                _safe_trace_event(
+                    "LIVE", "LIVE_CONNECT_REJECT", reason_code="ENDPOINT_CHANGED",
+                    endpoint_changed=True, **_trace_endpoint_fields(current or expected),
+                )
+                return result(None, "owner_identity_changed", attempt + 1, current or expected)
+            return result(client, "connected", attempt + 1, expected)
@@ -633 +721 @@ def connect_existing_with_status(
-        return None, "endpoint_identity_unverified"
+        return result(None, "endpoint_identity_unverified", total_attempts, expected)
@@ -635 +723,5 @@ def connect_existing_with_status(
-        return None, "owner_identity_changed"
+        _safe_trace_event(
+            "LIVE", "LIVE_CONNECT_REJECT", reason_code="ENDPOINT_CHANGED",
+            endpoint_changed=True, **_trace_endpoint_fields(endpoint or expected),
+        )
+        return result(None, "owner_identity_changed", total_attempts, endpoint or expected)
@@ -641,2 +733,2 @@ def connect_existing_with_status(
-        return None, "transient_connection_failure"
-    return None, "no_live_service"
+        return result(None, "transient_connection_failure", total_attempts, endpoint)
+    return result(None, "no_live_service", total_attempts, endpoint)
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 4de19ae..d7e0c5c 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -91,0 +92,15 @@ class DesktopLiveWatcher(_PollingLiveWorker):
+        started = time.monotonic()
+        prior_endpoint = getattr(self.client, "endpoint", None)
+        try:
+            from contextor.core.runtime_trace import new_trace_operation, trace_event
+
+            recovery_operation_id = new_trace_operation("wr")
+            trace_event(
+                "LIVE", "LIVE_WATCHER_RECOVERY_START", op=recovery_operation_id,
+                reason="connection_failure",
+                prior_endpoint_fingerprint=(prior_endpoint.fingerprint() if prior_endpoint is not None else None),
+                prior_service_pid=getattr(prior_endpoint, "pid", None),
+                recovery_operation_id=recovery_operation_id,
+            )
+        except Exception:
+            recovery_operation_id = None
@@ -105,0 +121,19 @@ class DesktopLiveWatcher(_PollingLiveWorker):
+            try:
+                from contextor.core.runtime_trace import trace_event
+
+                new_endpoint = new_client.endpoint
+                trace_event(
+                    "LIVE", "LIVE_WATCHER_RECOVERY_RESULT", op=recovery_operation_id,
+                    result=(
+                        "reconnected_existing"
+                        if prior_endpoint is not None and new_endpoint == prior_endpoint
+                        else "started_new_owner"
+                    ),
+                    new_endpoint_fingerprint=new_endpoint.fingerprint(),
+                    new_service_pid=new_endpoint.pid,
+                    lease_generation=new_endpoint.lease_generation,
+                    elapsed_ms=(time.monotonic() - started) * 1000.0,
+                    recovery_operation_id=recovery_operation_id,
+                )
+            except Exception:
+                pass
@@ -107,0 +142,13 @@ class DesktopLiveWatcher(_PollingLiveWorker):
+            try:
+                from contextor.core.runtime_trace import trace_event
+
+                trace_event(
+                    "LIVE", "LIVE_WATCHER_RECOVERY_RESULT", op=recovery_operation_id,
+                    result="failed",
+                    elapsed_ms=(time.monotonic() - started) * 1000.0,
+                    exception_class=type(exc).__name__, errno=getattr(exc, "errno", None),
+                    winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
+                    recovery_operation_id=recovery_operation_id,
+                )
+            except Exception:
+                pass
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 13e1b6c..265aafa 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -1272 +1272 @@ def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | No
-        key_map = {"repo": "repo", "path": "path", "kind": "kind", "tool": "tool", "q": "q", "count": "count", "bytes": "bytes", "wait_ms": "wait_ms", "elapsed_ms": "elapsed_ms", "scan_ms": "scan_ms", "ping_ms": "ping_ms", "status": "status", "err": "err", "mtime_ns": "mtime_ns", "category": "category", "operation": "operation", "first_seq": "first_seq", "last_seq": "last_seq", "candidate_rev": "candidate_rev"}
+        key_map = {"repo": "repo", "path": "path", "kind": "kind", "tool": "tool", "q": "q", "count": "count", "bytes": "bytes", "wait_ms": "wait_ms", "elapsed_ms": "elapsed_ms", "scan_ms": "scan_ms", "ping_ms": "ping_ms", "status": "status", "err": "err", "mtime_ns": "mtime_ns", "category": "category", "operation": "operation", "first_seq": "first_seq", "last_seq": "last_seq", "candidate_rev": "candidate_rev", "attempt": "attempt", "attempts": "attempts", "attempts_used": "attempts_used", "retry_delay": "retry_delay", "runtime_domain_id": "runtime_domain_id", "repo_id": "repo_id", "endpoint_fingerprint": "endpoint_fingerprint", "service_pid": "service_pid", "lease_generation": "lease_generation", "service_instance_id": "service_instance_id", "reason_code": "reason_code", "exception_class": "exception_class", "errno": "errno", "winerror": "winerror", "error": "error", "pid_alive": "pid_alive", "endpoint_changed": "endpoint_changed", "process_alive": "process_alive", "process_identity_matches": "process_identity_matches", "endpoint_available": "endpoint_available", "endpoint_matches": "endpoint_matches", "reason": "reason", "result": "result", "side": "side", "operation_or_request_type": "operation_or_request_type", "host": "host", "port": "port", "prior_endpoint_fingerprint": "prior_endpoint_fingerprint", "prior_service_pid": "prior_service_pid", "new_endpoint_fingerprint": "new_endpoint_fingerprint", "new_service_pid": "new_service_pid", "recovery_operation_id": "recovery_operation_id"}
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index 9f67dd2..11e2d4e 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -23,0 +24,32 @@ class _LiveIntegrationFakeVar:
+def test_watcher_recovery_emits_start_and_existing_result(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+
+    class Endpoint:
+        pid = 1234
+        lease_generation = 7
+
+        def fingerprint(self):
+            return "endpoint-fingerprint"
+
+    endpoint = Endpoint()
+    initial = SimpleNamespace(endpoint=endpoint, snapshot=lambda: {"status": "ok", "state": None})
+    recovered = SimpleNamespace(endpoint=endpoint)
+    watcher = DesktopLiveWatcher(repo, initial)
+    events = []
+    import contextor.core.runtime_trace as trace
+    import contextor.core.live_state.runtime as runtime
+
+    monkeypatch.setattr(runtime, "connect_or_start", lambda *_args, **_kwargs: recovered)
+    monkeypatch.setattr(trace, "new_trace_operation", lambda _prefix: "wr-test")
+    monkeypatch.setattr(trace, "trace_event", lambda domain, event, **fields: events.append((domain, event, fields)))
+
+    assert watcher._recover_client() is recovered
+
+    assert [event for _domain, event, _fields in events] == [
+        "LIVE_WATCHER_RECOVERY_START", "LIVE_WATCHER_RECOVERY_RESULT"
+    ]
+    assert events[1][2]["result"] == "reconnected_existing"
+    assert events[1][2]["new_endpoint_fingerprint"] == "endpoint-fingerprint"
+
+
diff --git a/tests/test_live_e2e_corrections.py b/tests/test_live_e2e_corrections.py
index 509faf9..fa431a0 100644
--- a/tests/test_live_e2e_corrections.py
+++ b/tests/test_live_e2e_corrections.py
@@ -430,0 +431,57 @@ def test_same_owner_identity_allows_transient_classification(
+def test_verified_client_transport_rejection_serializes_bounded_trace(
+    tmp_path, monkeypatch, authoritative_live_client
+):
+    from contextor.core.runtime_trace import finish_desktop_trace_session, start_desktop_trace_session
+    import contextor.core.runtime_trace as trace
+
+    endpoint = authoritative_live_client.endpoint
+    trace_logs = tmp_path / "isolated-trace"
+    finish_desktop_trace_session()
+    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: trace_logs)
+    path = start_desktop_trace_session()
+    assert path is not None
+
+    class RefusingClient:
+        def __init__(self, _endpoint):
+            pass
+
+        def authority_status(self):
+            raise ConnectionRefusedError(10061, "refused")
+
+    identity = live_runtime.read_repository_identity(tmp_path)
+    assert identity is not None
+    domain = live_runtime._production_domain(identity)
+    manager = live_runtime.RuntimeLeaseManager(domain)
+    monkeypatch.setattr(live_runtime, "LiveStateClient", RefusingClient)
+    try:
+        assert live_runtime._verified_existing_client(tmp_path, identity, domain, manager) is None
+    finally:
+        finish_desktop_trace_session()
+
+    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
+    event = next(item for item in records if item.get("ev") == "LIVE_CONNECT_REJECT")
+    assert event["reason_code"] == "AUTHORITY_STATUS_TRANSPORT_ERROR"
+    assert event["exception_class"] == "ConnectionRefusedError"
+    assert "winerror" not in event
+    assert "authkey" not in json.dumps(event).lower()
+    assert "owner_token" not in json.dumps(event).lower()
+
+
+def test_trace_failure_cannot_change_transient_connection_result(
+    tmp_path, monkeypatch, authoritative_live_client
+):
+    endpoint = authoritative_live_client.endpoint
+    monkeypatch.setattr(live_runtime, "_verified_existing_client", lambda *_args, **_kwargs: None)
+    monkeypatch.setattr(live_runtime, "_read_endpoint", lambda _root, **_kwargs: endpoint)
+    monkeypatch.setattr(live_runtime, "_is_pid_alive", lambda _pid: True)
+    monkeypatch.setattr(live_runtime.time, "sleep", lambda _delay: None)
+    import contextor.core.runtime_trace as trace
+
+    monkeypatch.setattr(trace, "trace_event", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("trace unavailable")))
+
+    client, status = live_runtime.connect_existing_with_status(tmp_path)
+
+    assert client is None
+    assert status == "transient_connection_failure"
+
+
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index 22af278..e359def 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -52,0 +53,20 @@ def test_client_request_timeout_closes_connection(monkeypatch):
+def test_client_transport_failure_emits_one_bounded_trace_event(monkeypatch):
+    events = []
+    endpoint = SimpleNamespace(
+        address=("127.0.0.1", 1), authkey=b"x", host="127.0.0.1", port=1
+    )
+    monkeypatch.setattr(
+        ipc_module, "Client", lambda *_args, **_kwargs: (_ for _ in ()).throw(ConnectionRefusedError(10061, "refused"))
+    )
+    monkeypatch.setattr(ipc_module, "_safe_trace_event", lambda *_args, **kwargs: events.append(kwargs))
+
+    with pytest.raises(ConnectionRefusedError):
+        LiveStateClient(endpoint).request("authority_status")
+
+    assert len(events) == 1
+    assert events[0]["side"] == "client"
+    assert events[0]["operation_or_request_type"] == "authority_status"
+    assert events[0]["exception_class"] == "ConnectionRefusedError"
+    assert "authkey" not in json.dumps(events[0]).lower()
+
+
```

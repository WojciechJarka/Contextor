STATUS=IMPLEMENTATION_PASS
HEAD=770e3c9ae9d1444a3eb0ba5a7da55fbf7801ef26

FILES_CHANGED:
- contextor/mcp_backend_control.py
- contextor/mcp_server.py
- tests/test_mcp_backend_owner.py
- tests/test_mcp_persistent_http_runner.py
- tests/test_mcp_shared_backend_server_mode.py

LITERAL_IMPLEMENTATION_MATCH=YES
The existing claim_backend_owner stale-owner branch, O2A controlled runner, and main persistent-backend dispatch matched the supplied anchors. Added only the requested O2B control-plane exception, owner evaluation/watchdog, runner lifecycle, and tests.

STALE_SAME_INSTANCE_POLICY=PASS
For the current backend_instance_id, MATCH with the same logical owner returns the current claim; MATCH with another logical owner raises BackendOwnerAlreadyClaimed; UNKNOWN raises BackendOwnerLivenessUnknown; STALE raises BackendOwnerInstanceRevoked before candidate creation or owner.json write. The focused stale test verifies owner.json bytes remain unchanged. A claim for an older backend_instance_id remains replaceable, and the existing regression still passes. The existing same-instance UNKNOWN test already covered fail-closed/no-write behavior.

OWNER_WATCH_STATE_MACHINE:
UNARMED + no claim or a claim for another backend instance -> remain unarmed.
UNARMED + exact current-instance MATCH -> pin that exact claim.
UNARMED + exact current-instance STALE -> revoke the instance.
UNARMED + UNKNOWN or BackendOwnerClaimError -> retry without revocation.
ARMED + exact pinned MATCH or UNKNOWN -> keep the pin and continue.
ARMED + stale exact pin, missing claim, or any exact claim replacement -> revoke the instance.
The watchdog polls every 0.75 seconds by default and does not use a heartbeat.

SELF_TERMINATE_MECHANISM=On proven revocation the watchdog sets server.should_exit=True; Uvicorn performs its normal shutdown. Production code does not cancel server.serve(), call shutdown directly, kill a process, or remove owner.json.
SERVE_TASK_CANCELLATION=NO
OWNER_CLAIM_REMOVED_ON_REVOKE=NO
FINALIZATION_ORDER=owner watchdog -> server.should_exit=True -> Uvicorn serve normal shutdown -> asyncio.run(_run()) returns -> _shutdown_cleanup() -> PersistentBackendLease.release()

EPHEMERAL_SELF_TERMINATE=PASS
A real FastMCP/Uvicorn server ran on an ephemeral localhost port. The patched evaluation returned non-revoked first and revoked only after server.started; the watchdog set should_exit, serve_task completed without cancellation, and the same port rebound successfully. Port 8765 was not used.

TARGETED_TESTS:
Command: .venv\Scripts\python.exe -m pytest -q tests/test_mcp_backend_owner.py tests/test_mcp_persistent_http_runner.py tests/test_mcp_shared_backend_server_mode.py
Result: 88 passed, 1 AuthlibDeprecationWarning. No other test modules or full suite were run.
git diff --check for the five implementation/test files before report generation: PASS.

CONTEXTOR_POST_EDIT:
Fetched BackendOwnerInstanceRevoked, claim_backend_owner, _evaluate_persistent_backend_owner, _watch_persistent_backend_owner, _run_persistent_http_server, and main. All six returned canonical_state=fresh and workspace_sync=verified at canonical_revision=1628.
LIVE events: revisions 1623-1628; all six were desktop_watcher UPDATED events covering both production files and all three changed test files.
continuity=continuous
resync_required=false

IMPLEMENTATION_RESULT=PASS

FULL_DIFFS
BEGIN_ACTUAL_DIFFS
diff --git a/contextor/mcp_backend_control.py b/contextor/mcp_backend_control.py
index 2df4ab9..69e9ecd 100644
--- a/contextor/mcp_backend_control.py
+++ b/contextor/mcp_backend_control.py
@@ -67,6 +67,10 @@ class BackendOwnerLivenessUnknown(BackendControlError):
     """The current backend host-owner process cannot be classified safely."""
 
 
+class BackendOwnerInstanceRevoked(BackendControlError):
+    """The current backend instance lost its exact lifecycle owner and must terminate."""
+
+
 @dataclass(
     frozen=True,
     slots=True,
@@ -301,6 +305,10 @@ def claim_backend_owner(
                 raise BackendOwnerLivenessUnknown(
                     "current backend host owner liveness is unknown"
                 )
+            if owner_state == "stale":
+                raise BackendOwnerInstanceRevoked(
+                    "backend instance lost its lifecycle owner and must be replaced"
+                )
             if owner_state != "stale":
                 raise BackendOwnerLivenessUnknown(
                     "current backend host owner state is invalid"
@@ -1089,6 +1097,7 @@ __all__ = [
     "BACKEND_SERVER_NAME",
     "BackendControlError",
     "BackendOwnerAlreadyClaimed",
+    "BackendOwnerInstanceRevoked",
     "BackendOwnerLivenessUnknown",
     "BackendStatus",
     "backend_control_lock_path",
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
index 6e7d342..06173d3 100644
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -193,7 +193,11 @@ from contextor.mcp_process_registry import (
     terminate_registered_process,
 )
 from contextor.mcp_backend_state import (
+    BackendHostOwnerClaim,
+    BackendOwnerClaimError,
     PersistentBackendLease,
+    classify_backend_owner_process,
+    read_backend_owner_claim,
 )
 from contextor.mcp.documentation import short_description
 from contextor.mcp.tools.get_artifact_blast_radius import (
@@ -982,6 +986,70 @@ def _register_server_root(
     )
 
 
+_PERSISTENT_BACKEND_OWNER_POLL_INTERVAL = 0.75
+
+
+def _evaluate_persistent_backend_owner(
+    *,
+    backend_instance_id: str,
+    pinned_claim: BackendHostOwnerClaim | None,
+) -> tuple[BackendHostOwnerClaim | None, bool]:
+    try:
+        current = read_backend_owner_claim()
+    except BackendOwnerClaimError:
+        return pinned_claim, False
+
+    if pinned_claim is None:
+        if (
+            current is None
+            or current.backend_instance_id != backend_instance_id
+        ):
+            return None, False
+
+        owner_state = classify_backend_owner_process(current)
+
+        if owner_state == "match":
+            return current, False
+
+        if owner_state == "stale":
+            return None, True
+
+        return None, False
+
+    if current != pinned_claim:
+        return pinned_claim, True
+
+    owner_state = classify_backend_owner_process(pinned_claim)
+
+    if owner_state == "stale":
+        return pinned_claim, True
+
+    return pinned_claim, False
+
+
+async def _watch_persistent_backend_owner(
+    server: uvicorn.Server,
+    *,
+    backend_instance_id: str,
+    poll_interval: float = _PERSISTENT_BACKEND_OWNER_POLL_INTERVAL,
+) -> None:
+    pinned_claim = None
+
+    while not server.should_exit:
+        pinned_claim, instance_revoked = (
+            _evaluate_persistent_backend_owner(
+                backend_instance_id=backend_instance_id,
+                pinned_claim=pinned_claim,
+            )
+        )
+
+        if instance_revoked:
+            server.should_exit = True
+            return
+
+        await asyncio.sleep(poll_interval)
+
+
 def _create_persistent_http_server(
     *,
     host: str,
@@ -1008,8 +1076,26 @@ def _create_persistent_http_server(
 
 async def _run_persistent_http_server(
     server: uvicorn.Server,
+    *,
+    backend_instance_id: str,
+    owner_poll_interval: float = _PERSISTENT_BACKEND_OWNER_POLL_INTERVAL,
 ) -> None:
-    await server.serve()
+    watchdog_task = asyncio.create_task(
+        _watch_persistent_backend_owner(
+            server,
+            backend_instance_id=backend_instance_id,
+            poll_interval=owner_poll_interval,
+        )
+    )
+
+    try:
+        await server.serve()
+    finally:
+        watchdog_task.cancel()
+        try:
+            await watchdog_task
+        except asyncio.CancelledError:
+            pass
 
 
 def main():
@@ -1143,7 +1229,8 @@ def main():
                     port=http_port,
                 )
                 await _run_persistent_http_server(
-                    server
+                    server,
+                    backend_instance_id=backend_lease.record.instance_id,
                 )
             elif transport in _HTTP_TRANSPORTS:
                 await mcp.run_http_async(
diff --git a/tests/test_mcp_backend_owner.py b/tests/test_mcp_backend_owner.py
index 63cc2c6..897b9b4 100644
--- a/tests/test_mcp_backend_owner.py
+++ b/tests/test_mcp_backend_owner.py
@@ -428,7 +428,7 @@ def test_claim_backend_owner_rejects_live_foreign_owner(
         ProcessIdentityProbe("alive", sys.executable, 333),
     ],
 )
-def test_claim_backend_owner_takes_over_stale_owner(
+def test_claim_backend_owner_revokes_same_instance_stale_owner_without_write(
     tmp_path,
     monkeypatch,
     probe_for_existing,
@@ -443,17 +443,20 @@ def test_claim_backend_owner_takes_over_stale_owner(
         return ProcessIdentityProbe("alive", sys.executable, 123456789)
 
     monkeypatch.setattr(state, "probe_process_identity", probe)
+    before = state.backend_owner_claim_path().read_bytes()
 
-    replacement = control.claim_backend_owner(
-        host_owner_identity="replacement-host",
-        host_kind="desktop",
-        owner_token="replacement-token",
-    )
+    with pytest.raises(
+        control.BackendOwnerInstanceRevoked,
+        match="backend instance lost its lifecycle owner and must be replaced",
+    ):
+        control.claim_backend_owner(
+            host_owner_identity="replacement-host",
+            host_kind="desktop",
+            owner_token="replacement-token",
+        )
 
-    assert replacement.backend_instance_id == record.instance_id
-    assert replacement.host_owner_identity == "replacement-host"
-    assert replacement != existing
-    assert state.read_backend_owner_claim() == replacement
+    assert existing.backend_instance_id == record.instance_id
+    assert state.backend_owner_claim_path().read_bytes() == before
 
 
 def test_claim_backend_owner_unknown_liveness_fails_without_write(
diff --git a/tests/test_mcp_persistent_http_runner.py b/tests/test_mcp_persistent_http_runner.py
index 8945c3d..f70e3e8 100644
--- a/tests/test_mcp_persistent_http_runner.py
+++ b/tests/test_mcp_persistent_http_runner.py
@@ -1,9 +1,14 @@
 import asyncio
 import socket
+from types import SimpleNamespace
 
 import pytest
 
 from contextor import mcp_server
+from contextor.mcp_backend_state import (
+    BackendHostOwnerClaim,
+    BackendOwnerClaimError,
+)
 
 
 def _configure_main(
@@ -76,6 +81,24 @@ def _configure_main(
     )
 
 
+def _owner_claim(
+    backend_instance_id="backend-current",
+    *,
+    owner_token="owner-token",
+):
+    return BackendHostOwnerClaim(
+        schema_version=1,
+        backend_instance_id=backend_instance_id,
+        host_owner_identity="host-owner",
+        host_kind="desktop",
+        host_pid=123,
+        host_executable="python.exe",
+        host_creation_time=456,
+        owner_token=owner_token,
+        claimed_at=1.0,
+    )
+
+
 def test_create_persistent_http_server_uses_exact_fastmcp_and_uvicorn_config(
     monkeypatch,
 ):
@@ -162,7 +185,8 @@ def test_run_persistent_http_server_awaits_serve_once():
 
     asyncio.run(
         mcp_server._run_persistent_http_server(
-            server
+            server,
+            backend_instance_id="backend-runner-test",
         )
     )
 
@@ -180,7 +204,8 @@ def test_run_persistent_http_server_propagates_serve_exception():
     ):
         asyncio.run(
             mcp_server._run_persistent_http_server(
-                FakeServer()
+                FakeServer(),
+                backend_instance_id="backend-runner-test",
             )
         )
 
@@ -197,8 +222,14 @@ def test_persistent_backend_main_uses_controlled_runner_and_finalizes_lease(
         role="persistent-backend",
         transport="streamable-http",
     )
+    backend_instance_id = "active-backend-instance"
 
     class FakeLease:
+        def __init__(self):
+            self.record = SimpleNamespace(
+                instance_id=backend_instance_id
+            )
+
         @classmethod
         def acquire(cls, **kwargs):
             events.append(
@@ -223,9 +254,14 @@ def test_persistent_backend_main_uses_controlled_runner_and_finalizes_lease(
         )
         return server
 
-    async def fake_run_server(actual_server):
+    async def fake_run_server(
+        actual_server,
+        *,
+        backend_instance_id,
+    ):
         assert actual_server is server
-        events.append(("serve",))
+        assert backend_instance_id == "active-backend-instance"
+        events.append(("serve", backend_instance_id))
 
     async def fail_http(**_kwargs):
         pytest.fail(
@@ -265,7 +301,7 @@ def test_persistent_backend_main_uses_controlled_runner_and_finalizes_lease(
 
     mcp_server.main()
 
-    assert events.index(("serve",)) < events.index(("shutdown",))
+    assert events.index(("serve", backend_instance_id)) < events.index(("shutdown",))
     assert events.index(("shutdown",)) < events.index(("lease_release",))
 
 
@@ -375,7 +411,187 @@ def test_stdio_main_keeps_fastmcp_runner(
     assert events.count(("stdio",)) == 1
 
 
-def test_persistent_http_server_exits_normally_and_releases_ephemeral_port():
+@pytest.mark.parametrize(
+    ("case", "expected_pinned", "expected_revoked"),
+    [
+        ("unarmed_no_claim", None, False),
+        ("unarmed_other_instance", None, False),
+        ("unarmed_match", "current", False),
+        ("unarmed_unknown", None, False),
+        ("unarmed_stale", None, True),
+        ("armed_match", "pinned", False),
+        ("armed_unknown", "pinned", False),
+        ("armed_stale", "pinned", True),
+        ("armed_missing", "pinned", True),
+        ("armed_replaced", "pinned", True),
+        ("unarmed_read_error", None, False),
+        ("armed_read_error", "pinned", False),
+    ],
+    ids=[
+        "unarmed-no-claim",
+        "unarmed-other-instance",
+        "unarmed-current-match",
+        "unarmed-current-unknown",
+        "unarmed-current-stale",
+        "armed-exact-match",
+        "armed-exact-unknown",
+        "armed-exact-stale",
+        "armed-claim-missing",
+        "armed-claim-replaced",
+        "unarmed-claim-read-error",
+        "armed-claim-read-error",
+    ],
+)
+def test_evaluate_persistent_backend_owner_state_machine(
+    case,
+    expected_pinned,
+    expected_revoked,
+    monkeypatch,
+):
+    pinned_claim = (
+        _owner_claim()
+        if expected_pinned == "pinned"
+        or case.startswith("armed_")
+        else None
+    )
+    if case in {
+        "unarmed_no_claim",
+        "armed_missing",
+        "unarmed_read_error",
+        "armed_read_error",
+    }:
+        current_claim = None
+    elif case == "unarmed_other_instance":
+        current_claim = _owner_claim("backend-other")
+    elif case == "armed_replaced":
+        current_claim = _owner_claim(owner_token="replacement-token")
+    elif case.startswith("armed_"):
+        current_claim = pinned_claim
+    else:
+        current_claim = _owner_claim()
+
+    owner_state = {
+        "unarmed_match": "match",
+        "unarmed_unknown": "unknown",
+        "unarmed_stale": "stale",
+        "armed_match": "match",
+        "armed_unknown": "unknown",
+        "armed_stale": "stale",
+    }.get(case)
+    classified_claims = []
+
+    def fake_read_claim():
+        if case in {"unarmed_read_error", "armed_read_error"}:
+            raise BackendOwnerClaimError("malformed owner claim")
+        return current_claim
+
+    def fake_classify(claim):
+        classified_claims.append(claim)
+        return owner_state
+
+    monkeypatch.setattr(
+        mcp_server,
+        "read_backend_owner_claim",
+        fake_read_claim,
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "classify_backend_owner_process",
+        fake_classify,
+    )
+
+    result = mcp_server._evaluate_persistent_backend_owner(
+        backend_instance_id="backend-current",
+        pinned_claim=pinned_claim,
+    )
+
+    expected_claim = {
+        "current": current_claim,
+        "pinned": pinned_claim,
+    }.get(expected_pinned)
+    assert result == (expected_claim, expected_revoked)
+
+    if case in {
+        "unarmed_no_claim",
+        "unarmed_other_instance",
+        "armed_missing",
+        "armed_replaced",
+        "unarmed_read_error",
+        "armed_read_error",
+    }:
+        assert classified_claims == []
+    else:
+        assert classified_claims == [
+            pinned_claim if case.startswith("armed_") else current_claim
+        ]
+
+
+def test_watchdog_revokes_server_without_cancelling_serve_task(monkeypatch):
+    class FakeServer:
+        should_exit = False
+
+    async def exercise_watchdog():
+        server = FakeServer()
+        serve_finished = asyncio.Event()
+
+        async def fake_serve():
+            await serve_finished.wait()
+
+        serve_task = asyncio.create_task(fake_serve())
+        await asyncio.sleep(0)
+
+        monkeypatch.setattr(
+            mcp_server,
+            "_evaluate_persistent_backend_owner",
+            lambda **_kwargs: (None, True),
+        )
+
+        await mcp_server._watch_persistent_backend_owner(
+            server,
+            backend_instance_id="backend-watchdog-test",
+            poll_interval=0.001,
+        )
+
+        assert server.should_exit is True
+        assert serve_task.cancelled() is False
+        serve_finished.set()
+        await serve_task
+
+    asyncio.run(exercise_watchdog())
+
+
+def test_watchdog_continues_polling_until_instance_is_revoked(monkeypatch):
+    class FakeServer:
+        should_exit = False
+
+    server = FakeServer()
+    calls = []
+
+    def evaluate(**_kwargs):
+        calls.append(None)
+        return None, len(calls) > 1
+
+    monkeypatch.setattr(
+        mcp_server,
+        "_evaluate_persistent_backend_owner",
+        evaluate,
+    )
+
+    asyncio.run(
+        mcp_server._watch_persistent_backend_owner(
+            server,
+            backend_instance_id="backend-watchdog-test",
+            poll_interval=0.001,
+        )
+    )
+
+    assert len(calls) == 2
+    assert server.should_exit is True
+
+
+def test_persistent_http_server_exits_normally_and_releases_ephemeral_port(
+    monkeypatch,
+):
     host = "127.0.0.1"
     with socket.socket() as probe:
         probe.bind((host, 0))
@@ -386,9 +602,15 @@ def test_persistent_http_server_exits_normally_and_releases_ephemeral_port():
             host=host,
             port=port,
         )
+        monkeypatch.setattr(
+            mcp_server,
+            "_evaluate_persistent_backend_owner",
+            lambda **_kwargs: (None, False),
+        )
         serve_task = asyncio.create_task(
             mcp_server._run_persistent_http_server(
-                server
+                server,
+                backend_instance_id="backend-runner-test",
             )
         )
 
@@ -430,3 +652,76 @@ def test_persistent_http_server_exits_normally_and_releases_ephemeral_port():
     with socket.socket() as rebound:
         rebound.bind((host, port))
         rebound.listen()
+
+
+def test_persistent_http_server_self_terminates_on_owner_revocation(
+    monkeypatch,
+):
+    host = "127.0.0.1"
+    with socket.socket() as probe:
+        probe.bind((host, 0))
+        port = probe.getsockname()[1]
+
+    async def exercise_server():
+        server = mcp_server._create_persistent_http_server(
+            host=host,
+            port=port,
+        )
+        evaluations = []
+
+        def evaluate(
+            *,
+            backend_instance_id,
+            pinned_claim,
+        ):
+            assert backend_instance_id == "backend-watchdog-test"
+            evaluations.append(server.started)
+            if len(evaluations) == 1 or not server.started:
+                return pinned_claim, False
+            return pinned_claim, True
+
+        monkeypatch.setattr(
+            mcp_server,
+            "_evaluate_persistent_backend_owner",
+            evaluate,
+        )
+        serve_task = asyncio.create_task(
+            mcp_server._run_persistent_http_server(
+                server,
+                backend_instance_id="backend-watchdog-test",
+                owner_poll_interval=0.01,
+            )
+        )
+
+        async def wait_until_started():
+            loop = asyncio.get_running_loop()
+            deadline = loop.time() + 10
+            while not server.started:
+                if serve_task.done():
+                    await serve_task
+                if loop.time() >= deadline:
+                    raise AssertionError(
+                        "Uvicorn server did not start before timeout"
+                    )
+                await asyncio.sleep(0.01)
+
+        await asyncio.wait_for(
+            wait_until_started(),
+            timeout=10,
+        )
+        done, _pending = await asyncio.wait(
+            {serve_task},
+            timeout=10,
+        )
+        assert serve_task in done
+        await serve_task
+        assert serve_task.cancelled() is False
+        assert server.should_exit is True
+        assert evaluations[0] is False
+        assert any(evaluations[1:])
+
+    asyncio.run(exercise_server())
+
+    with socket.socket() as rebound:
+        rebound.bind((host, port))
+        rebound.listen()
diff --git a/tests/test_mcp_shared_backend_server_mode.py b/tests/test_mcp_shared_backend_server_mode.py
index 2640243..395c4b4 100644
--- a/tests/test_mcp_shared_backend_server_mode.py
+++ b/tests/test_mcp_shared_backend_server_mode.py
@@ -585,7 +585,11 @@ def test_persistent_http_main_uses_shared_registry_without_root_registration(
         )
         return server
 
-    async def fake_run_server(actual_server):
+    async def fake_run_server(
+        actual_server,
+        *,
+        backend_instance_id,
+    ):
         assert actual_server is server
         record = read_backend_record()
         assert record is not None
@@ -595,10 +599,12 @@ def test_persistent_http_main_uses_shared_registry_without_root_registration(
         assert record.host == "127.0.0.1"
         assert record.port == 8765
         assert Path(record.process_registry) == registry.resolve()
+        assert backend_instance_id == record.instance_id
         events.append(
             (
                 "http",
                 actual_server,
+                backend_instance_id,
             )
         )
 
@@ -644,6 +650,7 @@ def test_persistent_http_main_uses_shared_registry_without_root_registration(
     assert len(http_events) == 1
 
     assert http_events[0][1] is server
+    assert http_events[0][2]
 
     create_events = [
         event
END_ACTUAL_DIFFS

FILES_CHANGED_NOTE:
walkthrough.md is the requested report and is not included in FILES_CHANGED or in its own diff. It contains the full raw diffs above.

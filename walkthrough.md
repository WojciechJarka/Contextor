TASK: CONTEXTOR_C38P1A_LIVE_PING_STRICT_READ_ONLY_GATE
MODE: FOCUSED IMPLEMENTATION
HEAD_BEFORE: 7cdea328a70a0e491d65eaa82bca9ad2ffb4396e
HEAD_AFTER: 8f677dbc882cd1f279b8d7bb60f49c677d8c3db5
GIT_STATUS: clean
GIT_NOTE: HEAD moved during report generation via an external Auto-commit: Cleanup and update. This agent did not invoke commit or other Git mutation. Complete task diffs below compare HEAD_BEFORE to HEAD_AFTER.

CONTEXTOR_DISCOVERY_COVERAGE:
DIRECT_EVIDENCE: Contextor fetched complete AST-bounded implementations of _verified_existing_client and connect from contextor/core/live_state/runtime.py at LIVE revision 568 with workspace_sync=verified. It found six intra-module call sites of _verified_existing_client and module consumers for runtime. The source branch invokes reconcile_endpoint_binding when active generation.endpoint_fingerprint is missing and other binding fields match. Final verification requires matching generation fingerprint.
CODE_PATH_PROVED: live.ping scope called contextor.core.live_state.connect(root); connect called _verified_existing_client with default behavior. The new keyword is forwarded by connect. Other callers retain the default True.
CONTRACT_PROVED: Strict False gates only reconciliation. Remaining endpoint/domain, lease/generation, process identity, authority status, and final lease checks remain. Missing generation binding causes None, mapped to unavailable by the scope.
INFERENCE: Isolated fake-manager tests prove branch behavior, not serving runtime adoption.
UNKNOWN: Serving MCP backend requires manual restart after auditor source approval.

IMPLEMENTATION:
- runtime.py: keyword-only reconcile_missing_endpoint_binding: bool = True on _verified_existing_client and connect; forwarded by connect; existing reconciliation call gated.
- live_ipc.py: live.ping calls connect(root, reconcile_missing_endpoint_binding=False).
- test_atomic_profiler_scopes.py: scope test requires False keyword and verifies connect/ping and unavailable behavior.
- test_live_authority_bootstrap.py: isolated tests prove default/strict forwarding, missing binding rejection without reconcile or generation metadata write, complete binding ping, and normal reconciliation. Existing split-binding reconciliation test passes.
No production LIVE state, publication, process restart, update_file, or FULL analysis was performed.

TARGETED_TEST_RESULTS: tests/test_atomic_profiler_scopes.py plus three selected tests in tests/test_live_authority_bootstrap.py: 15 passed in 2.51s after final source edit. No full repository pytest suite.
WATCHER_EVENTS: Continuous LIVE event history, resync_required=false. desktop_watcher UPDATED runtime.py at revisions 569 and 573, live_ipc.py at 570, test_atomic_profiler_scopes.py at 571, test_live_authority_bootstrap.py at 572. Revision 573 confirms final runtime edit.
WORKSPACE_SYNC: Contextor get_symbol_implementation preview resolved live_ipc.run_scope with workspace_sync=verified at revision 571 and runtime.connect with workspace_sync=verified at revision 573. Git diff --check before external auto-commit found no source/test whitespace error.
LIVE_REVISION_BEFORE_AFTER: 568 -> 573.
MCP_BACKEND_RESTART_REQUIRED=YES
MCP_BACKEND_RESTART_PERFORMED=NO
SERVING_RUNTIME_ADOPTION=PENDING
FINAL_VERDICT: C38P1A_SOURCE_PASS_PENDING_RUNTIME

FILES_CHANGED:
C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
C:\Temp\Contextor_Repo\contextor\core\profiling\scopes\live_ipc.py
C:\Temp\Contextor_Repo\tests\test_atomic_profiler_scopes.py
C:\Temp\Contextor_Repo\tests\test_live_authority_bootstrap.py

FULL_DIFFS (exact complete task diffs; walkthrough.md excluded):

FILE: C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 4952fe4..1904607 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -529,6 +529,7 @@ def _verified_existing_client(
     *,
     desktop_instance_id: str | None = None,
     owner_token: str | None = None,
+    reconcile_missing_endpoint_binding: bool = True,
 ) -> LiveStateClient | None:
     started = time.monotonic()
 
@@ -559,7 +560,8 @@ def _verified_existing_client(
         live = manager.read_live_lease()
         record = manager.read_generation()
         if (
-            live is not None
+            reconcile_missing_endpoint_binding
+            and live is not None
             and record.status == "active"
             and live.service_instance_id == endpoint.service_instance_id
             and live.lease_generation == endpoint.lease_generation
@@ -619,7 +621,11 @@ def _verified_existing_client(
     return client
 
 
-def connect(repo_path: str | Path) -> LiveStateClient | None:
+def connect(
+    repo_path: str | Path,
+    *,
+    reconcile_missing_endpoint_binding: bool = True,
+) -> LiveStateClient | None:
     root = Path(repo_path).resolve()
     identity = read_repository_identity(root)
     if identity is None:
@@ -630,7 +636,13 @@ def connect(repo_path: str | Path) -> LiveStateClient | None:
         liveness_verifier=AuthorityLivenessVerifier(domain),
     )
     try:
-        return _verified_existing_client(root, identity, domain, manager)
+        return _verified_existing_client(
+            root,
+            identity,
+            domain,
+            manager,
+            reconcile_missing_endpoint_binding=reconcile_missing_endpoint_binding,
+        )
     except EndpointSchemaError:
         return None
 

FILE: C:\Temp\Contextor_Repo\contextor\core\profiling\scopes\live_ipc.py
diff --git a/contextor/core/profiling/scopes/live_ipc.py b/contextor/core/profiling/scopes/live_ipc.py
index 928e685..85e89f9 100644
--- a/contextor/core/profiling/scopes/live_ipc.py
+++ b/contextor/core/profiling/scopes/live_ipc.py
@@ -9,7 +9,7 @@ PRESETS = ("connect", "ping")
 
 def run_scope(root: Path, recorder) -> dict[str, object]:
     with recorder.span("connect"):
-        client = connect(root)
+        client = connect(root, reconcile_missing_endpoint_binding=False)
     if client is None:
         return {"status": "unavailable", "reason": "live_authority_unavailable"}
     with recorder.span("ping"):

FILE: C:\Temp\Contextor_Repo\tests\test_atomic_profiler_scopes.py
diff --git a/tests/test_atomic_profiler_scopes.py b/tests/test_atomic_profiler_scopes.py
index 0fb2160..916a0c1 100644
--- a/tests/test_atomic_profiler_scopes.py
+++ b/tests/test_atomic_profiler_scopes.py
@@ -84,10 +84,15 @@ def test_reports_missing_and_invalid(tmp_path, monkeypatch):
 
 def test_live_uses_existing_connect_and_only_ping(tmp_path, monkeypatch):
     calls = []
-    monkeypatch.setattr(live_ipc, "connect", lambda root: calls.append("connect") or SimpleNamespace(
-        ping=lambda: calls.append("ping") or {"status": "ok", "revision": 2}))
+    def strict_connect(root, *, reconcile_missing_endpoint_binding):
+        assert reconcile_missing_endpoint_binding is False
+        calls.append("connect")
+        return SimpleNamespace(
+            ping=lambda: calls.append("ping") or {"status": "ok", "revision": 2}
+        )
+    monkeypatch.setattr(live_ipc, "connect", strict_connect)
     result = live_ipc.run_scope(tmp_path, _recorder("live.ping"))
     assert calls == ["connect", "ping"]
     assert result["observed_revision"] == 2
-    monkeypatch.setattr(live_ipc, "connect", lambda root: None)
+    monkeypatch.setattr(live_ipc, "connect", lambda root, *, reconcile_missing_endpoint_binding: None)
     assert live_ipc.run_scope(tmp_path, _recorder("live.ping"))["status"] == "unavailable"

FILE: C:\Temp\Contextor_Repo\tests\test_live_authority_bootstrap.py
diff --git a/tests/test_live_authority_bootstrap.py b/tests/test_live_authority_bootstrap.py
index 88404b3..706a8fb 100644
--- a/tests/test_live_authority_bootstrap.py
+++ b/tests/test_live_authority_bootstrap.py
@@ -5,6 +5,7 @@ import os
 import threading
 import time
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
@@ -34,6 +35,92 @@ from contextor.core.repository_identity import read_repository_identity
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 
 
+def test_connect_preserves_default_reconciliation_and_forwards_strict_opt_out(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+):
+    observed = []
+    monkeypatch.setattr(runtime_module, "read_repository_identity", lambda _: object())
+    monkeypatch.setattr(runtime_module, "_production_domain", lambda _: object())
+    monkeypatch.setattr(runtime_module, "RuntimeLeaseManager", lambda *a, **k: object())
+    monkeypatch.setattr(runtime_module, "AuthorityLivenessVerifier", lambda _: object())
+    def verified(*args, **kwargs):
+        observed.append(kwargs["reconcile_missing_endpoint_binding"])
+        return object()
+    monkeypatch.setattr(runtime_module, "_verified_existing_client", verified)
+    assert runtime_module.connect(tmp_path) is not None
+    assert runtime_module.connect(tmp_path, reconcile_missing_endpoint_binding=False) is not None
+    assert observed == [True, False]
+
+
+def test_verified_existing_read_only_rejects_missing_binding_without_generation_write(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+):
+    fingerprint = "fingerprint"
+    endpoint = SimpleNamespace(
+        service_instance_id="service", lease_generation=3, pid=123,
+        process_start_identity="start", owner_pid=None, owner_token=None,
+        fingerprint=lambda: fingerprint,
+    )
+    lease = SimpleNamespace(
+        service_instance_id="service", lease_generation=3, service_pid=123,
+        process_start_identity="start", endpoint_fingerprint=fingerprint,
+    )
+    record = SimpleNamespace(
+        status="active", endpoint_fingerprint=None,
+        last_service_instance_id="service", last_lease_generation=3,
+    )
+    generation_file = tmp_path / "generation.write"
+    reconciliations = []
+    class Manager:
+        def read_live_lease(self):
+            return lease
+        def read_generation(self):
+            return record
+        def reconcile_endpoint_binding(self, current_lease, current_fingerprint):
+            reconciliations.append((current_lease, current_fingerprint))
+            record.endpoint_fingerprint = current_fingerprint
+            generation_file.write_text("written")
+    class Client:
+        def __init__(self, endpoint, **kwargs):
+            self.endpoint = endpoint
+        def authority_status(self):
+            return {"status": "ok"}
+        def ping(self):
+            return {"status": "ok", "revision": 4}
+    monkeypatch.setattr(runtime_module, "_read_endpoint", lambda *a, **k: endpoint)
+    monkeypatch.setattr(runtime_module, "_endpoint_matches_domain", lambda *a: True)
+    monkeypatch.setattr(runtime_module, "_process_identity", lambda _: ("image", "start", True))
+    monkeypatch.setattr(runtime_module, "_status_matches_endpoint", lambda *a: True)
+    monkeypatch.setattr(runtime_module, "_safe_trace_event", lambda *a, **k: None)
+    monkeypatch.setattr(runtime_module, "LiveStateClient", Client)
+    manager = Manager()
+    strict = runtime_module._verified_existing_client(
+        tmp_path, object(), object(), manager,
+        reconcile_missing_endpoint_binding=False,
+    )
+    assert strict is None
+    assert reconciliations == []
+    assert not generation_file.exists()
+    assert record.endpoint_fingerprint is None
+
+    normal = runtime_module._verified_existing_client(tmp_path, object(), object(), manager)
+    assert normal is not None
+    assert normal.ping()["revision"] == 4
+    assert reconciliations == [(lease, fingerprint)]
+    assert generation_file.read_text() == "written"
+
+    reconciliations.clear()
+    generation_file.unlink()
+    complete = runtime_module._verified_existing_client(
+        tmp_path, object(), object(), manager,
+        reconcile_missing_endpoint_binding=False,
+    )
+    assert complete is not None
+    assert complete.ping()["status"] == "ok"
+    assert reconciliations == []
+    assert not generation_file.exists()
+
+
 def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str = "repo") -> Path:
     repo = tmp_path / name
     repo.mkdir()

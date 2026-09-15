# CPA10D_LIVE_MUTATION_ADMISSION_CORRELATION

STATUS=IMPLEMENTATION_PASS_RUNTIME_RESTART_PENDING

HEAD_BEFORE=9d7ab352aa2bb92c9b7abd6f6a151147fd916f99
HEAD_AFTER=9d7ab352aa2bb92c9b7abd6f6a151147fd916f99

FILES_CHANGED=
- contextor/core/live_state/ipc.py
- contextor/core/live_state/runtime.py
- contextor/core/analysis/full_analysis_coordinator.py
- contextor/core/runtime_trace.py
- tests/test_live_mutation_coordinator.py
- tests/test_full_analysis_coordination.py

IMPLEMENTATION=
- The serial FIFO coordinator now gives its executor authoritative job identity and revisions in a copied execution request.
- Queued update execution establishes one trace operation before guard acquisition.
- The repository mutation guard forwards only the required correlation fields into writer admission.
- Writer admission whitelists and emits those fields on both acquisition and release.
- The existing trace-event allowlist required the smallest compatibility correction to retain job/revision correlation fields; without it, the requested capture test fails because the trace helper silently drops those fields.
- No FIFO, watcher deduplication, writer priority/fairness/yield, public IPC schema, or persistence/commit semantics changed.

TESTS=
- PASS: `.venv\\Scripts\\python.exe -m py_compile contextor/core/live_state/ipc.py contextor/core/live_state/runtime.py contextor/core/analysis/full_analysis_coordinator.py contextor/core/runtime_trace.py tests/test_live_mutation_coordinator.py tests/test_full_analysis_coordination.py`
- PASS: 5 focused regression tests, including all four new coordinator/guard tests plus the admission trace-correlation test: `5 passed in 2.48s`.
- PASS: `tests/test_live_mutation_coordinator.py -q`: `24 passed in 9.22s`.
- INCOMPLETE: the required combined two-file pytest invocation was started after the change, but its longer run did not return a terminal result through the command interface before its execution limit. It must not be reported as a full-suite PASS. No failure was reported after the trace allowlist correction in the focused tests.

RUNTIME_RESTART_REQUIRED=YES
No LIVE/MCP restart was performed and no runtime freshness certification was attempted.

CONTEXTOR_FIRST_VERIFICATION=
- `get_file_edit_context` confirmed the three requested implementation modules at LIVE revision 1126 with fresh syntax diagnostics before edit.
- Post-edit `get_symbol_call_context` confirmed `acquire_full_analysis -> _canonical_writer_admission`, `run_service -> _repository_mutation_guard`, and the coordinator's bounded intra-module call context. Canonical state revision was 1127; the tool noted on-disk modification, as expected after the edit.

ACTUAL_DIFF=
```diff
diff --git a/contextor/core/analysis/full_analysis_coordinator.py b/contextor/core/analysis/full_analysis_coordinator.py
index 9ec05af..a39e9df 100644
--- a/contextor/core/analysis/full_analysis_coordinator.py
+++ b/contextor/core/analysis/full_analysis_coordinator.py
@@ -16,7 +16,7 @@ import time
 import uuid
 from dataclasses import dataclass
 from pathlib import Path
-from typing import Any, Callable
+from typing import Any, Callable, Mapping

 from contextor.core.errors import AnalysisCancelled
 from contextor.core.paths import repo_cache_dir, repo_key
@@ -52,6 +52,30 @@ _PROCESS_LOCKS_GUARD = threading.Lock()
 _ADMISSION_LOCKS: dict[str, threading.Lock] = {}
 _ADMISSION_LOCKS_GUARD = threading.Lock()

+_ADMISSION_TRACE_FIELD_NAMES = (
+    "op",
+    "path",
+    "job_id",
+    "idempotency_key",
+    "queue_order",
+    "accepted_revision",
+    "started_revision",
+    "origin",
+)
+
+
+def _select_admission_trace_fields(
+    fields: Mapping[str, Any] | None,
+) -> dict[str, Any]:
+    if fields is None:
+        return {}
+
+    return {
+        name: fields[name]
+        for name in _ADMISSION_TRACE_FIELD_NAMES
+        if name in fields and fields[name] is not None
+    }
+

 def _get_process_lock(
     repo_key_str: str,
@@ -105,7 +129,11 @@ def _canonical_writer_admission(
     deadline: float | None,
     poll_interval: float,
     is_cancelled: Callable[[], bool] | None,
+    admission_trace_fields: Mapping[str, Any] | None,
 ):
+    trace_fields = _select_admission_trace_fields(
+        admission_trace_fields
+    )
     process_lock = _get_admission_lock(key)
     started = time.monotonic()
     _acquire_process_lock_until(
@@ -148,6 +176,7 @@ def _canonical_writer_admission(
             owner=owner,
             writer_kind=writer_kind,
             wait_ms=(time.monotonic() - started) * 1000.0,
+            **trace_fields,
         )
         yield
     finally:
@@ -172,6 +201,7 @@ def _canonical_writer_admission(
                     repo_id=repo_id,
                     owner=owner,
                     writer_kind=writer_kind,
+                    **trace_fields,
                 )


@@ -386,6 +416,7 @@ def acquire_full_analysis(
     poll_interval: float = 0.25,
     is_cancelled: Callable[[], bool] | None = None,
     log: Callable[[str], None] | None = None,
+    admission_trace_fields: Mapping[str, Any] | None = None,
 ) -> FullAnalysisLease:
     """
     Acquire exclusive single-writer lease for full repository analysis.
@@ -416,6 +447,7 @@ def acquire_full_analysis(
         deadline=deadline,
         poll_interval=poll_interval,
         is_cancelled=is_cancelled,
+        admission_trace_fields=admission_trace_fields,
     ):
         _acquire_process_lock_until(
             proc_lock,
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 25a6ab4..fc93f23 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -263,9 +263,18 @@ class CanonicalMutationCoordinator:
                     continue
                 job.state = "running"
                 job.started_revision = int(self._revision_reader())
+                execution_request = dict(job.request)
+                execution_request.update(
+                    {
+                        "job_id": job.job_id,
+                        "queue_order": job.queue_order,
+                        "accepted_revision": job.accepted_revision,
+                        "started_revision": job.started_revision,
+                    }
+                )

             try:
-                response = self._executor(job.request)
+                response = self._executor(execution_request)
             except Exception as exc:
                 response = {
                     "status": "error",
@@ -1250,6 +1259,10 @@ class CanonicalLiveServer:
                 return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}

     def _execute_queued_update_file(self, request: dict[str, Any]) -> dict[str, Any]:
+        trace_op = _safe_trace_op(request, "u")
+        if trace_op is not None:
+            request = {**request, "trace_op": trace_op}
+
         if self._mutation_guard is None:
             return self._execute_update_file(request)
         with self._mutation_guard(request, self._stop):
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 5c32f64..31a46d2 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -1134,17 +1134,33 @@ def _repository_persister(root: Path, holder: dict[str, object] | None = None):

 def _repository_mutation_guard(root: Path):
     @contextlib.contextmanager
-    def guard(_request: Mapping[str, Any], stop_event: threading.Event):
+    def guard(request: Mapping[str, Any], stop_event: threading.Event):
         from contextor.core.analysis.full_analysis_coordinator import (
             acquire_full_analysis,
             release_full_analysis,
         )

+        origin = request.get("origin")
+        if origin is None:
+            origin = request.get("source")
+
+        admission_trace_fields = {
+            "op": request.get("trace_op"),
+            "path": request.get("file_path"),
+            "job_id": request.get("job_id"),
+            "idempotency_key": request.get("idempotency_key"),
+            "queue_order": request.get("queue_order"),
+            "accepted_revision": request.get("accepted_revision"),
+            "started_revision": request.get("started_revision"),
+            "origin": origin,
+        }
+
         lease = acquire_full_analysis(
             root,
             owner="live_mutation_worker",
             writer_kind="live_mutation",
             is_cancelled=stop_event.is_set,
+            admission_trace_fields=admission_trace_fields,
         )
         try:
             yield
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 7eac05f..c92a174 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -1359,6 +1359,11 @@ def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | No
         key_map.update(
             {
                 "origin": "origin",
+                "job_id": "job_id",
+                "idempotency_key": "idempotency_key",
+                "queue_order": "queue_order",
+                "accepted_revision": "accepted_revision",
+                "started_revision": "started_revision",
                 "diagnostic_kind": "diagnostic_kind",
                 "diagnostic_key": "diagnostic_key",
                 "collision_kind": "collision_kind",
diff --git a/tests/test_full_analysis_coordination.py b/tests/test_full_analysis_coordination.py
index babe10c..f0ad176 100644
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -67,6 +67,78 @@ def test_startup_publish_writer_kind_is_accepted(tmp_path: Path):
         acquire_full_analysis(repo, writer_kind="invalid")


+def test_live_mutation_admission_trace_fields_are_correlated_and_whitelisted(
+    tmp_path: Path,
+):
+    repo = tmp_path / "live_mutation_trace"
+    repo.mkdir()
+
+    supplied = {
+        "op": "u-test-op",
+        "path": "contextor/example.py",
+        "job_id": "mu-test",
+        "idempotency_key": "intent-test",
+        "queue_order": 7,
+        "accepted_revision": 41,
+        "started_revision": 42,
+        "origin": "desktop_watcher",
+        "repo_id": "forged-repo",
+        "owner": "forged-owner",
+        "writer_kind": "forged-kind",
+        "wait_ms": -1,
+        "unexpected": "must-not-leak",
+    }
+
+    with capture_trace_events() as events:
+        lease = acquire_full_analysis(
+            repo,
+            owner="live_mutation_worker",
+            writer_kind="live_mutation",
+            timeout=1.0,
+            admission_trace_fields=supplied,
+        )
+        release_full_analysis(lease)
+
+    admission_events = [
+        event
+        for event in events
+        if event.get("ev")
+        in {
+            "CANONICAL_WRITER_ADMISSION_ACQUIRED",
+            "CANONICAL_WRITER_ADMISSION_RELEASED",
+        }
+    ]
+
+    assert [event["ev"] for event in admission_events] == [
+        "CANONICAL_WRITER_ADMISSION_ACQUIRED",
+        "CANONICAL_WRITER_ADMISSION_RELEASED",
+    ]
+
+    expected_correlation = {
+        "op": "u-test-op",
+        "path": "contextor/example.py",
+        "job_id": "mu-test",
+        "idempotency_key": "intent-test",
+        "queue_order": 7,
+        "accepted_revision": 41,
+        "started_revision": 42,
+        "origin": "desktop_watcher",
+    }
+
+    for event in admission_events:
+        for key, value in expected_correlation.items():
+            assert event[key] == value
+
+        assert event["repo_id"] == lease.repo_id
+        assert event["owner"] == "live_mutation_worker"
+        assert event["writer_kind"] == "live_mutation"
+        assert "unexpected" not in event
+
+    acquired_event = admission_events[0]
+    assert acquired_event["wait_ms"] >= 0.0
+    assert acquired_event["wait_ms"] != -1
+
+
 def test_normal_shutdown_releases_lease_for_next_desktop_instance(
     tmp_path: Path,
 ):
diff --git a/tests/test_live_mutation_coordinator.py b/tests/test_live_mutation_coordinator.py
index 10e0460..f2829e0 100644
--- a/tests/test_live_mutation_coordinator.py
+++ b/tests/test_live_mutation_coordinator.py
@@ -220,12 +220,173 @@ def test_duplicate_idempotency_key_reuses_job_and_executes_once():
         release.set()
         terminal = _wait_for_coordinator_terminal(coordinator, first["job_id"])
         assert terminal["state"] == "completed"
-        assert executions == [{"file_path": "same.py", "idempotency_key": "intent-1"}]
+        assert executions == [
+            {
+                "file_path": "same.py",
+                "idempotency_key": "intent-1",
+                "job_id": first["job_id"],
+                "queue_order": first["queue_order"],
+                "accepted_revision": first["accepted_revision"],
+                "started_revision": 0,
+            }
+        ]
     finally:
         release.set()
         coordinator.close()


+def test_executor_receives_authoritative_job_identity_without_mutating_submitted_request():
+    executions = []
+    submitted_request = {
+        "file_path": "same.py",
+        "idempotency_key": "intent-authoritative",
+        "job_id": "forged-job",
+        "queue_order": 999,
+        "accepted_revision": 999,
+        "started_revision": 999,
+    }
+
+    def executor(request):
+        executions.append(request)
+        return {"status": "ok", "revision": 1}
+
+    coordinator = CanonicalMutationCoordinator(executor, lambda: 0)
+    try:
+        accepted = coordinator.submit(submitted_request)
+        terminal = _wait_for_coordinator_terminal(
+            coordinator,
+            accepted["job_id"],
+        )
+
+        assert terminal["state"] == "completed"
+        assert len(executions) == 1
+
+        execution_request = executions[0]
+        assert execution_request["file_path"] == "same.py"
+        assert execution_request["idempotency_key"] == "intent-authoritative"
+        assert execution_request["job_id"] == accepted["job_id"]
+        assert execution_request["queue_order"] == accepted["queue_order"]
+        assert (
+            execution_request["accepted_revision"]
+            == accepted["accepted_revision"]
+        )
+        assert execution_request["started_revision"] == 0
+
+        assert submitted_request == {
+            "file_path": "same.py",
+            "idempotency_key": "intent-authoritative",
+            "job_id": "forged-job",
+            "queue_order": 999,
+            "accepted_revision": 999,
+            "started_revision": 999,
+        }
+    finally:
+        coordinator.close()
+
+
+def test_queued_mutation_guard_receives_job_identity_and_trace_operation():
+    guarded_requests = []
+
+    @contextmanager
+    def mutation_guard(request, stop_event):
+        assert not stop_event.is_set()
+        guarded_requests.append(dict(request))
+        yield
+
+    def updater(state, path):
+        state.files.append(path)
+        return {"status": "UPDATED", "file_path": path}
+
+    server = CanonicalLiveServer(
+        SimpleNamespace(files=[], revision=0),
+        updater=updater,
+        mutation_guard=mutation_guard,
+    )
+
+    with _running_server(server) as client:
+        accepted = client.submit_update_file(
+            "guarded.py",
+            origin="desktop_watcher",
+            idempotency_key="guarded-intent",
+        )
+        terminal = _wait_for_terminal(
+            client,
+            accepted["job_id"],
+        )
+
+        assert terminal["state"] == "completed"
+        assert terminal["final_revision"] == 1
+
+    assert len(guarded_requests) == 1
+    guarded = guarded_requests[0]
+    assert guarded["file_path"] == "guarded.py"
+    assert guarded["origin"] == "desktop_watcher"
+    assert guarded["idempotency_key"] == "guarded-intent"
+    assert guarded["job_id"] == accepted["job_id"]
+    assert guarded["queue_order"] == accepted["queue_order"]
+    assert guarded["accepted_revision"] == accepted["accepted_revision"]
+    assert guarded["started_revision"] == 0
+    assert isinstance(guarded["trace_op"], str)
+    assert guarded["trace_op"]
+
+
+def test_repository_mutation_guard_forwards_exact_admission_trace_fields(
+    tmp_path,
+    monkeypatch,
+):
+    from contextor.core.analysis import full_analysis_coordinator as fac
+
+    acquired = []
+    released = []
+    lease = object()
+
+    def fake_acquire(repo_path, **kwargs):
+        acquired.append((repo_path, kwargs))
+        return lease
+
+    def fake_release(value):
+        released.append(value)
+
+    monkeypatch.setattr(fac, "acquire_full_analysis", fake_acquire)
+    monkeypatch.setattr(fac, "release_full_analysis", fake_release)
+
+    stop_event = threading.Event()
+    guard = _repository_mutation_guard(tmp_path)
+
+    request = {
+        "trace_op": "u-test-op",
+        "file_path": "contextor/example.py",
+        "job_id": "mu-test",
+        "idempotency_key": "intent-test",
+        "queue_order": 7,
+        "accepted_revision": 41,
+        "started_revision": 42,
+        "source": "desktop_watcher",
+    }
+
+    with guard(request, stop_event):
+        pass
+
+    assert len(acquired) == 1
+    repo_path, kwargs = acquired[0]
+    assert repo_path == tmp_path
+    assert kwargs["owner"] == "live_mutation_worker"
+    assert kwargs["writer_kind"] == "live_mutation"
+    assert callable(kwargs["is_cancelled"])
+    assert kwargs["is_cancelled"]() is False
+    assert kwargs["admission_trace_fields"] == {
+        "op": "u-test-op",
+        "path": "contextor/example.py",
+        "job_id": "mu-test",
+        "idempotency_key": "intent-test",
+        "queue_order": 7,
+        "accepted_revision": 41,
+        "started_revision": 42,
+        "origin": "desktop_watcher",
+    }
+    assert released == [lease]
+
+
 def test_different_idempotency_keys_for_same_path_create_distinct_jobs():
     executions = []
```

## CPA10D_TEST_CERTIFICATION_ONLY

- TERMINAL PASS: `.venv\\Scripts\\python.exe -m pytest tests/test_full_analysis_coordination.py -q` — `21 passed in 26.10s`.
- TERMINAL PASS: `.venv\\Scripts\\python.exe -m pytest tests/test_live_mutation_coordinator.py tests/test_full_analysis_coordination.py -q` — `45 passed in 26.54s`.
- The previous interface-limit qualification is superseded by the terminal combined PASS above.
- RUNTIME_RESTART_REQUIRED=YES. No LIVE/MCP restart and no runtime freshness certification were performed.

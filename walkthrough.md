# CPA10D_LIVE_MUTATION_ADMISSION_CORRELATION

STATUS=DISCOVERY_COMPLETE

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

## CPA10D_RUNTIME_CERTIFICATION

CPA10D_RUNTIME_CERTIFICATION=PASS
CPA10D_IMPLEMENTATION=PASS
CPA10_OVERALL=OPEN
RUNTIME_FRESHNESS=PASS

### Step 1 — authority freshness gate

- SERVICE_PID=10812
- SERVICE_START_TIME=2026-09-15 10:52:24 Europe/Warsaw (after required 2026-09-15 10:45:04 threshold)
- SERVICE_INSTANCE_ID=3d6dd4d61b364f0887b46f4267b6294e
- LEASE_GENERATION=70
- PROCESS_START_IDENTITY=134339359446469807
- PROTOCOL_VERSION=4 (equal to `LIVE_PROTOCOL_VERSION`)
- ENDPOINT_SCHEMA_VERSION=2 (equal to `LIVE_ENDPOINT_SCHEMA_VERSION`)
- ENDPOINT_FINGERPRINT=5adc7aa67b7e2c4f0cb9099aebbbcd889fad0681f16630103ec775830a83a662
- BASELINE_REVISION=1132
- BASELINE_ACTIVITY_EPOCH=35047e975b9f490aafb2c93e663a4091
- BASELINE_SEQ=11

Endpoint and `authority_status` agreed on PID, service instance, lease generation, process-start identity, and protocol/schema versions. The authority PID and instance remained unchanged during the controlled mutation.

### Step 2 — controlled queued mutation

- ACK: `status=accepted`, `job_id=mu-f185bdb1be6142cd89ca681ee43cf015`, `queue_order=1`, `accepted_revision=1132`
- mutation_status: `state=completed`, same `job_id`, same `queue_order`, same `accepted_revision`, `started_revision=1132`, `final_revision=1133`
- Correlation: `op=u-10812-1`; `path=C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\ipc.py`; `idempotency_key=cpa10d-cert-ca67eab210f7481ab0c6015d0828ea7c`; `origin=cpa10d_runtime_certification`
- ACQUIRED: exactly one event in `C:\\Users\\DafoO\\AppData\\Roaming\\Contextor\\logs\\contextor_runtime_20260915_085219_808_11296.jsonl`, at `2026-09-15T09:03:51.729+00:00`, `wait_ms=0.0`, with all correlation values above, `owner=live_mutation_worker`, `writer_kind=live_mutation`.
- RELEASED: exactly one event in the same trace file at `2026-09-15T09:03:51.774+00:00`, with the identical `op`, path, job ID, idempotency key, queue order, accepted/started revisions, origin, owner, and writer kind.
- LIVE event: exactly matching `trace_op=u-10812-1`, `operation=update_file`, `file_path=C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\ipc.py`, `status=UNCHANGED`, `canonical_revision=1133`, `seq=12`.
- Activity epoch remained `35047e975b9f490aafb2c93e663a4091`; no activity resync was required. Terminal `final_revision=1133` equals journal latest revision 1133 and is greater than baseline 1132.

The prescribed Step 2 script reached the controlled update but its process output was cut at the interface's 30-second cap before it could print. The mutation completed after approximately 33 seconds. A subsequent read-only validation asserted every required terminal, admission, journal, correlation, and authority condition. Its later JSON presentation failed only because `IncrementalUpdateResult` was not JSON-serializable; that occurred after all assertions had passed and does not change certification evidence.

FILES_CHANGED=NONE
DIFFS=NONE

## CPA10F_RUNTIME_PROFILE_CERTIFICATION

TOOL=contextor_profile_analysis
DOCUMENTATION_LOOKUP=Contextor MCP documentation returned controlled "Documentation identity mismatch" for this tool; the exposed Contextor MCP tool schema was then used directly.
REPO_PATH=C:\\Temp\\Contextor_Repo
OPERATION_ID=profile-2096-1
PROFILE_STATUS=ok
ABSOLUTE_WALL_AUTHORITATIVE=false
TOTAL_MS=82359.0
ANALYSIS_BODY_MS=81625.0
TOTAL_BEFORE_RELEASE_MS=82344.0
LEASE_WAIT_MS=172.0
STAGE_SUM_MS=81187.0
UNATTRIBUTED_ANALYSIS_MS=438.0

STAGE_ATTRIBUTION_KEYS=identity_and_setup,reports,canonical_materialization,live_publish (exactly four required wide stages)

### identity_and_setup

progress_setup_ms=0.0
repository_identity_ms=62.0
authoritative_state_resolution_ms=8141.0
cache_reset_ms=0.0
analysis_filters_and_index_progress_ms=0.0
component_sum_ms=8203.0
residual_ms=0.0
coverage_pct=100.0
dominant_component=authoritative_state_resolution
reason_code=authoritative_state_resolution_cost
critical_path_ms=8203.0
RECONSTRUCTION=8203.0+0.0=8203.0 (exact)

### reports

basic_report_preparation_ms=94.0
artifact_pipeline_ms=2578.0
sanity_check_ms=0.0
layer_reports_ms=312.0
git_state_ms=0.0
high_risk_writes_ms=0.0
global_report_write_ms=188.0
incremental_file_state_ms=187.0
finalization_ms=0.0
component_sum_ms=3359.0
residual_ms=16.0
coverage_pct=99.53
dominant_component=artifact_pipeline
reason_code=artifact_pipeline_cost
critical_path_ms=3375.0
RECONSTRUCTION=3359.0+16.0=3375.0 (exact)

### canonical_materialization

setup_and_imports_ms=0.0
topology_analytics_ms=125.0
collision_canonicalization_ms=141.0
artifact_consumption_ms=78.0
module_usage_reuse_ms=1047.0
canonical_validation_ms=31.0
lineage_materialization_ms=6266.0
lineage_query_indexes_ms=125.0
state_construction_ms=0.0
dependency_matrix_ms=94.0
shared_usage_clusters_ms=578.0
publish_preparation_ms=0.0
component_sum_ms=8485.0
residual_ms=0.0
coverage_pct=100.0
dominant_component=lineage_materialization
reason_code=lineage_reuse_gate_cost
critical_path_ms=8485.0
RECONSTRUCTION=8485.0+0.0=8485.0 (exact)
lineage_reason_code=lineage_reuse_gate_cost
lineage_elapsed_ms=6250.0
lineage_sources=397
reuse_sources=397
reresolve_sources=0
materialize_sources=0
reresolve_fallback_sources=0
reuse_gate_ms=3500.0
reresolve_calls_ms=0.0
materialize_calls_ms=0.0

### live_publish

connect_ms=31.0
publish_ms=11062.0
status_handling_ms=0.0
component_sum_ms=11093.0
residual_ms=0.0
coverage_pct=100.0
stage_status=success
dominant_component=publish
reason_code=live_publish_ipc_cost
critical_path_ms=11093.0
RECONSTRUCTION=11093.0+0.0=11093.0 (exact)

### Full current bottleneck ranking

RANK=1; STAGE=indexing; CRITICAL_PATH_MS=45562.0; SHARE_OF_ANALYSIS_PCT=55.82; REASON_CODE=cold_or_partial_cache_work; DOMINANT_COMPONENT=unavailable
RANK=2; STAGE=live_publish; CRITICAL_PATH_MS=11093.0; SHARE_OF_ANALYSIS_PCT=13.59; REASON_CODE=live_publish_ipc_cost; DOMINANT_COMPONENT=publish
RANK=3; STAGE=canonical_materialization; CRITICAL_PATH_MS=8485.0; SHARE_OF_ANALYSIS_PCT=10.4; REASON_CODE=lineage_reuse_gate_cost; DOMINANT_COMPONENT=lineage_materialization
RANK=4; STAGE=identity_and_setup; CRITICAL_PATH_MS=8203.0; SHARE_OF_ANALYSIS_PCT=10.05; REASON_CODE=authoritative_state_resolution_cost; DOMINANT_COMPONENT=authoritative_state_resolution
RANK=5; STAGE=persistence; CRITICAL_PATH_MS=3797.0; SHARE_OF_ANALYSIS_PCT=4.65; REASON_CODE=unattributed; DOMINANT_COMPONENT=unavailable

REMAINING_UNATTRIBUTED_STAGE=persistence
CRITICAL_PATH_MS=3797.0
RANK=5
MATERIALITY=persistence remains a material top-5 bottleneck; no attribution was attempted or inferred.

PERSISTENCE_MS=3797.0
PERSISTENCE_IN_TOP5=YES
PERSISTENCE_ATTRIBUTED=NO

AGGREGATE_WORKER_DIAGNOSTICS=source_parse_sum_ms=10967.0; cache_get_sum_ms=29574.0; lineage_extract_sum_ms=1142.0; lineage_extract_event_sum_ms=1142.0; timing_semantics=aggregate_file_task_not_critical_path

CONTRACT_CHECK=PASS — all four stage_attribution entries have reason_code != unattributed, dominant_component for positive stage time, component_sum_ms, residual_ms, coverage_pct, and rounding-safe reconstruction of stage critical_path_ms.
CPA10F_IMPLEMENTATION=PASS
CPA10F_RUNTIME_PROFILE_CERTIFICATION=PASS
PROFILE_TOP5_ATTRIBUTION=PARTIAL (persistence rank 5 remains reason_code=unattributed)
CPA10_OVERALL=OPEN
NO_RUNTIME_RESTART=YES
NO_ADDITIONAL_FULL_ANALYSIS=YES
NO_MANUAL_TRACE_PARSING=YES
NO_CUSTOM_PROFILER=YES

FILES_CHANGED=NONE
DIFFS=NONE



## CPA10F_PROFILE_STAGE_COMPONENT_ATTRIBUTION

STATUS=IMPLEMENTATION_COMPLETE_TESTS_PASS
HEAD_BEFORE=871c97117ec34d51bbaecb701d13763d093d8511
HEAD_AFTER=871c97117ec34d51bbaecb701d13763d093d8511
BASE_DRIFT=YES (HEAD differs from known CPA10D base 9d7ab352aa2bb92c9b7abd6f6a151147fd916f99; existing committed CPA10D state preserved)
FILES_CHANGED=7 (the exact seven files requested; walkthrough.md excluded)
PY_COMPILE=PASS
TESTS=PASS — 56 passed in 27.21s
PROFILE_RUN=NOT_RUN (explicitly forbidden in this task)
PROFILE_WORKER_RESTART_REQUIRED=NO
DESKTOP_RUNTIME_RESTART_REQUIRED=YES_BEFORE_DESKTOP_CERTIFICATION
MCP_SERVER_RESTART_REQUIRED=NO_FOR_PROFILE_EXECUTION

IMPLEMENTATION_SCOPE=Exact component attribution only; pipeline order/semantics, LIVE/persistence/revision semantics, public MCP parameters, FIFO/fairness, and watcher dedup unchanged.
ATTRIBUTION=identity_and_setup (5), reports (9), canonical_materialization (12), and live_publish (3) now emit critical_path_stage_component events. Profiler validates all required labels, computes component_sum_ms/residual_ms/coverage_pct, selects deterministic dominant component, and retains nested lineage reason evidence.
CONTEXTOR_FIRST_VERIFICATION=Completed after edits. trace_event resolved with workspace_sync=verified. build_analysis_profile, ContextorFacade.analyze_project, and execute_global_pipeline were resolved but returned status=stale_source/workspace_sync=out_of_sync because the edited files are ahead of canonical LIVE state; no analysis refresh was run because profile execution/restart were forbidden. analyze_project call-context returned canonical callees with the same expected stale-source advisory.

ACTUAL_DIFF=
```diff
warning: in the working copy of 'contextor/core/analysis/profile_analysis.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/api/facade.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/reporting_engine/pipeline.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/runtime_trace.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/mcp/docs/contextor_profile_analysis.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_profile_analysis.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_runtime_trace.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/analysis/profile_analysis.py b/contextor/core/analysis/profile_analysis.py
index 45f91a0..17f3e8f 100644
--- a/contextor/core/analysis/profile_analysis.py
+++ b/contextor/core/analysis/profile_analysis.py
@@ -28,6 +28,89 @@ _REQUIRED_SINGLE_EVENTS = (
     "FULL_ANALYSIS_LINEAGE_MATERIALIZATION",
 )
 
+_REQUIRED_STAGE_COMPONENTS = {
+    "identity_and_setup": (
+        "progress_setup",
+        "repository_identity",
+        "authoritative_state_resolution",
+        "cache_reset",
+        "analysis_filters_and_index_progress",
+    ),
+    "reports": (
+        "basic_report_preparation",
+        "artifact_pipeline",
+        "sanity_check",
+        "layer_reports",
+        "git_state",
+        "high_risk_writes",
+        "global_report_write",
+        "incremental_file_state",
+        "finalization",
+    ),
+    "canonical_materialization": (
+        "setup_and_imports",
+        "topology_analytics",
+        "collision_canonicalization",
+        "artifact_consumption",
+        "module_usage_reuse",
+        "canonical_validation",
+        "lineage_materialization",
+        "lineage_query_indexes",
+        "state_construction",
+        "dependency_matrix",
+        "shared_usage_clusters",
+        "publish_preparation",
+    ),
+    "live_publish": (
+        "connect",
+        "publish",
+        "status_handling",
+    ),
+}
+
+_COMPONENT_REASON_CODES = {
+    "identity_and_setup": {
+        "progress_setup": "identity_progress_setup_cost",
+        "repository_identity": "repository_identity_cost",
+        "authoritative_state_resolution": "authoritative_state_resolution_cost",
+        "cache_reset": "cache_reset_cost",
+        "analysis_filters_and_index_progress": "analysis_filter_setup_cost",
+        "__residual__": "identity_setup_residual_cost",
+    },
+    "reports": {
+        "basic_report_preparation": "report_basic_preparation_cost",
+        "artifact_pipeline": "artifact_pipeline_cost",
+        "sanity_check": "report_sanity_check_cost",
+        "layer_reports": "layer_report_generation_cost",
+        "git_state": "git_state_cost",
+        "high_risk_writes": "high_risk_report_write_cost",
+        "global_report_write": "global_report_write_cost",
+        "incremental_file_state": "incremental_file_state_cost",
+        "finalization": "report_finalization_cost",
+        "__residual__": "reports_residual_cost",
+    },
+    "canonical_materialization": {
+        "setup_and_imports": "canonical_setup_cost",
+        "topology_analytics": "topology_analytics_cost",
+        "collision_canonicalization": "collision_canonicalization_cost",
+        "artifact_consumption": "canonical_artifact_consumption_cost",
+        "module_usage_reuse": "module_usage_reuse_cost",
+        "canonical_validation": "canonical_validation_cost",
+        "lineage_query_indexes": "lineage_query_index_cost",
+        "state_construction": "canonical_state_construction_cost",
+        "dependency_matrix": "dependency_matrix_cost",
+        "shared_usage_clusters": "shared_usage_clusters_cost",
+        "publish_preparation": "canonical_publish_preparation_cost",
+        "__residual__": "canonical_materialization_residual_cost",
+    },
+    "live_publish": {
+        "connect": "live_connect_cost",
+        "publish": "live_publish_ipc_cost",
+        "status_handling": "live_publish_status_handling_cost",
+        "__residual__": "live_publish_residual_cost",
+    },
+}
+
 
 def _number(event: dict[str, object], field: str) -> float:
     value = event.get(field)
@@ -119,8 +202,7 @@ def _indexing_reason(
     return "unattributed", evidence
 
 
-def _canonical_materialization_reason(
-    stage_ms: float,
+def _lineage_materialization_reason(
     event: dict[str, object],
 ) -> tuple[str, dict[str, object]]:
     reuse_sources = _count(event, "reuse_sources")
@@ -159,12 +241,102 @@ def _canonical_materialization_reason(
         and materialize_sources == 0
         and fallback_sources == 0
         and reuse_gate_ms > 0.0
-        and stage_ms > 0.0
-        and lineage_elapsed_ms >= stage_ms * 0.5
+        and lineage_elapsed_ms > 0.0
     ):
         return "lineage_reuse_gate_cost", evidence
 
-    return "unattributed", evidence
+    return "lineage_other_cost", evidence
+
+
+def _stage_component_reason(
+    stage: str,
+    stage_ms: float,
+    component_events: dict[str, dict[str, object]],
+    *,
+    lineage_reason: str | None = None,
+    lineage_evidence: dict[str, object] | None = None,
+) -> tuple[str, dict[str, object]]:
+    ordered = _REQUIRED_STAGE_COMPONENTS[stage]
+    component_ms: dict[str, float] = {}
+
+    for component in ordered:
+        event = component_events[component]
+        if (
+            event.get("timing_semantics")
+            != "critical_path_stage_component"
+        ):
+            raise ValueError(
+                "FULL_ANALYSIS_STAGE_COMPONENT_END:"
+                f"{stage}:{component} has invalid timing_semantics"
+            )
+        component_ms[component] = _number(event, "elapsed_ms")
+
+    component_sum_ms = sum(component_ms.values())
+    residual_ms = max(0.0, stage_ms - component_sum_ms)
+
+    evidence: dict[str, object] = {
+        f"{component}_ms": _round_ms(component_ms[component])
+        for component in ordered
+    }
+    evidence["component_sum_ms"] = _round_ms(component_sum_ms)
+    evidence["residual_ms"] = _round_ms(residual_ms)
+    evidence["coverage_pct"] = (
+        round(
+            min(100.0, (component_sum_ms / stage_ms) * 100.0),
+            2,
+        )
+        if stage_ms > 0.0
+        else 100.0
+    )
+
+    final_status = component_events[ordered[-1]].get("status")
+    if isinstance(final_status, str) and final_status:
+        evidence["stage_status"] = final_status
+
+    if stage_ms == 0.0:
+        zero_reason = {
+            "identity_and_setup": "identity_setup_no_work",
+            "reports": "reports_no_work",
+            "canonical_materialization": "canonical_materialization_no_work",
+            "live_publish": "live_publish_not_attempted",
+        }
+        return zero_reason[stage], evidence
+
+    candidates = [
+        (component, component_ms[component])
+        for component in ordered
+    ]
+    candidates.append(("__residual__", residual_ms))
+    dominant_component, _ = max(
+        candidates,
+        key=lambda item: (
+            item[1],
+            -(
+                ordered.index(item[0])
+                if item[0] in ordered
+                else len(ordered)
+            ),
+        ),
+    )
+    evidence["dominant_component"] = dominant_component
+
+    if (
+        stage == "canonical_materialization"
+        and dominant_component == "lineage_materialization"
+    ):
+        if lineage_reason is None or lineage_evidence is None:
+            raise ValueError(
+                "canonical_materialization lineage attribution "
+                "requires lineage evidence"
+            )
+        evidence["lineage_reason_code"] = lineage_reason
+        evidence.update(lineage_evidence)
+        return lineage_reason, evidence
+
+    return (
+        _COMPONENT_REASON_CODES[stage][dominant_component],
+        evidence,
+    )
 
 
 def build_analysis_profile(
@@ -211,6 +383,34 @@ def build_analysis_profile(
         else:
             stage_events[stage] = matches[0]
 
+    stage_component_events: dict[
+        str,
+        dict[str, dict[str, object]],
+    ] = {}
+
+    for stage, components in _REQUIRED_STAGE_COMPONENTS.items():
+        collected: dict[str, dict[str, object]] = {}
+        for component in components:
+            matches = [
+                event
+                for event in scoped
+                if event.get("ev")
+                == "FULL_ANALYSIS_STAGE_COMPONENT_END"
+                and event.get("stage") == stage
+                and event.get("component") == component
+            ]
+            label = (
+                "FULL_ANALYSIS_STAGE_COMPONENT_END:"
+                f"{stage}:{component}"
+            )
+            if len(matches) > 1:
+                duplicates.append(label)
+            elif not matches:
+                missing.append(label)
+            else:
+                collected[component] = matches[0]
+        stage_component_events[stage] = collected
+
     if missing or duplicates:
         return _incomplete_profile(
             operation_id,
@@ -286,13 +486,35 @@ def build_analysis_profile(
             )
 
         index_reason, index_reason_evidence = _indexing_reason(index_event)
-        canonical_reason, canonical_reason_evidence = (
-            _canonical_materialization_reason(
-                stage_values["canonical_materialization"],
+        lineage_reason, lineage_reason_evidence = (
+            _lineage_materialization_reason(
                 lineage_materialization_event,
             )
         )
 
+        stage_attribution: dict[str, dict[str, object]] = {}
+
+        for stage in _REQUIRED_STAGE_COMPONENTS:
+            reason_code, evidence = _stage_component_reason(
+                stage,
+                stage_values[stage],
+                stage_component_events[stage],
+                lineage_reason=(
+                    lineage_reason
+                    if stage == "canonical_materialization"
+                    else None
+                ),
+                lineage_evidence=(
+                    lineage_reason_evidence
+                    if stage == "canonical_materialization"
+                    else None
+                ),
+            )
+            stage_attribution[stage] = {
+                "reason_code": reason_code,
+                **evidence,
+            }
+
         stage_breakdown = [
             {
                 "stage": stage,
@@ -317,9 +539,15 @@ def build_analysis_profile(
             if stage == "indexing":
                 reason_code = index_reason
                 reason_evidence = index_reason_evidence
-            elif stage == "canonical_materialization":
-                reason_code = canonical_reason
-                reason_evidence = canonical_reason_evidence
+            elif stage in stage_attribution:
+                reason_code = str(
+                    stage_attribution[stage]["reason_code"]
+                )
+                reason_evidence = {
+                    key: value
+                    for key, value in stage_attribution[stage].items()
+                    if key != "reason_code"
+                }
 
             share = (
                 (stage_values[stage] / analysis_ms) * 100.0
@@ -376,14 +604,15 @@ def build_analysis_profile(
                 ),
             },
             "stage_breakdown": stage_breakdown,
+            "stage_attribution": stage_attribution,
             "bottlenecks": bottlenecks,
             "indexing_evidence": {
                 "reason_code": index_reason,
                 **index_reason_evidence,
             },
             "lineage_materialization_evidence": {
-                "reason_code": canonical_reason,
-                **canonical_reason_evidence,
+                "reason_code": lineage_reason,
+                **lineage_reason_evidence,
             },
             "aggregate_worker_diagnostics": {
                 "timing_semantics": (
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 7720d22..980ad5c 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -589,18 +589,90 @@ class ContextorFacade:
                 result=f"stage={stage};elapsed_ms={elapsed_ms:.3f}",
             )
 
+        def emit_stage_component(
+            stage: str,
+            component: str,
+            elapsed_ms: float,
+            *,
+            status: str | None = None,
+        ) -> None:
+            trace_event(
+                "ANALYSIS",
+                "FULL_ANALYSIS_STAGE_COMPONENT_END",
+                stage=stage,
+                component=component,
+                operation=f"{stage}:{component}",
+                elapsed_ms=elapsed_ms,
+                timing_semantics="critical_path_stage_component",
+                status=status,
+                result=(
+                    f"stage={stage};component={component};"
+                    f"elapsed_ms={elapsed_ms:.3f}"
+                ),
+            )
+
+        def emit_stage_component_end(
+            stage: str,
+            component: str,
+            started: float,
+            *,
+            status: str | None = None,
+        ) -> float:
+            elapsed_ms = (time.monotonic() - started) * 1000.0
+            emit_stage_component(
+                stage,
+                component,
+                elapsed_ms,
+                status=status,
+            )
+            return elapsed_ms
+
         identity_and_setup_started = facade_started
+
+        component_started = time.monotonic()
         progress = _StagedProgress(progress_callback, total_stages=8, log=log)
         progress.begin("Initializing repository identity")
+        emit_stage_component_end(
+            "identity_and_setup",
+            "progress_setup",
+            component_started,
+        )
+
+        component_started = time.monotonic()
         registry = _initialize_repository_identity(path)
         path = str(registry.repo_path.resolve())
+        emit_stage_component_end(
+            "identity_and_setup",
+            "repository_identity",
+            component_started,
+        )
+
+        component_started = time.monotonic()
         previous_canonical_state = resolve_authoritative_repository_state(path)
+        emit_stage_component_end(
+            "identity_and_setup",
+            "authoritative_state_resolution",
+            component_started,
+        )
+
+        component_started = time.monotonic()
         reset_caches()
+        emit_stage_component_end(
+            "identity_and_setup",
+            "cache_reset",
+            component_started,
+        )
 
+        component_started = time.monotonic()
         if log:
             log("Starting directory indexing...")
         excludes, extra_dirs = _analysis_filters(path, additional_excludes)
         index_progress = progress.begin("Indexing repository files")
+        emit_stage_component_end(
+            "identity_and_setup",
+            "analysis_filters_and_index_progress",
+            component_started,
+        )
         emit_stage_end("identity_and_setup", identity_and_setup_started)
 
         indexing_started = time.monotonic()
@@ -717,6 +789,7 @@ class ContextorFacade:
             log(f"Generated additional reports for high risk layers: {high_risk_layers}")
 
         canonical_materialization_started = time.monotonic()
+        canonical_setup_started = canonical_materialization_started
         analysis_result = report_result.get("_analysis_result")
 
         progress.begin("Persisting canonical LIVE snapshot")
@@ -740,12 +813,25 @@ class ContextorFacade:
                 is_valid_shared_usage_clusters_handoff,
             )
 
+            emit_stage_component_end(
+                "canonical_materialization",
+                "setup_and_imports",
+                canonical_setup_started,
+            )
+
+            component_started = time.monotonic()
             graph = getattr(analysis_result, "graph", None)
             hard_edges = getattr(graph, "hard_edges", {}) if graph else {}
             soft_edges = getattr(graph, "soft_edges", {}) if graph else {}
             metrics = getattr(analysis_result, "metrics", {})
             topology_analytics = compute_topology_analytics(hard_edges, soft_edges, metrics) if hard_edges else {}
+            emit_stage_component_end(
+                "canonical_materialization",
+                "topology_analytics",
+                component_started,
+            )
 
+            component_started = time.monotonic()
             from contextor.core.analysis.incremental.materialization import _validate_collision_facts_dict
             cf = getattr(analysis_result, "collision_facts", None)
             mods = getattr(analysis_result, "modules", {})
@@ -757,10 +843,22 @@ class ContextorFacade:
             else:
                 canonical_collisions = []
                 collisions_state = "deferred"
+            emit_stage_component_end(
+                "canonical_materialization",
+                "collision_canonicalization",
+                component_started,
+            )
 
+            component_started = time.monotonic()
             raw_artifacts = getattr(analysis_result, "artifacts", {}) or {}
             canonical_consumption = build_canonical_artifact_consumption(raw_artifacts)
+            emit_stage_component_end(
+                "canonical_materialization",
+                "artifact_consumption",
+                component_started,
+            )
 
+            component_started = time.monotonic()
             from contextor.core.reference.module_usage_reuse import (
                 build_module_usage_baseline_with_reuse,
             )
@@ -772,7 +870,13 @@ class ContextorFacade:
                     file_state_manager,
                 )
             )
+            emit_stage_component_end(
+                "canonical_materialization",
+                "module_usage_reuse",
+                component_started,
+            )
 
+            component_started = time.monotonic()
             # Exact canonical coverage trust gate (no truthiness)
             consumption_valid = validate_canonical_artifact_consumption_coverage(
                 canonical_consumption,
@@ -781,6 +885,13 @@ class ContextorFacade:
             syntax_diagnostics_by_path, syntax_diagnostics_state = (
                 build_syntax_diagnostics_from_index(index)
             )
+            emit_stage_component_end(
+                "canonical_materialization",
+                "canonical_validation",
+                component_started,
+            )
+
+            component_started = time.monotonic()
             (
                 lineage_facts_by_source,
                 lineage_facts_state,
@@ -796,6 +907,12 @@ class ContextorFacade:
                     else None
                 ),
             )
+            emit_stage_component_end(
+                "canonical_materialization",
+                "lineage_materialization",
+                component_started,
+            )
+            component_started = time.monotonic()
             from contextor.core.lineage_query.index import (
                 build_lineage_query_indexes,
             )
@@ -810,7 +927,13 @@ class ContextorFacade:
                 if lineage_facts_state == "not_materialized"
                 else "fresh"
             )
+            emit_stage_component_end(
+                "canonical_materialization",
+                "lineage_query_indexes",
+                component_started,
+            )
 
+            component_started = time.monotonic()
             state = RepositoryAnalysisState(
                 modules=mods,
                 artifacts=raw_artifacts,
@@ -856,8 +979,14 @@ class ContextorFacade:
 
             if getattr(analysis_result, "resync_required", False):
                 state.resync_required = True
+            emit_stage_component_end(
+                "canonical_materialization",
+                "state_construction",
+                component_started,
+            )
 
             # Compute Dependency Matrix from canonical state (independent failure & graph trust)
+            component_started = time.monotonic()
             if dependency_matrix_inputs_are_fresh(state):
                 try:
                     _dm_candidate = compute_dependency_matrix_from_state(state)
@@ -868,8 +997,14 @@ class ContextorFacade:
                     state.dependency_matrix_state = "fresh"
             else:
                 state.dependency_matrix_state = "stale"
+            emit_stage_component_end(
+                "canonical_materialization",
+                "dependency_matrix",
+                component_started,
+            )
 
             # Compute Shared Usage Clusters from canonical state (independent failure & AC trust)
+            component_started = time.monotonic()
             if artifact_consumption_is_fresh(state):
                 raw_shared_usage_clusters = report_result.get(
                     "_raw_shared_usage_clusters"
@@ -893,7 +1028,13 @@ class ContextorFacade:
                         state.shared_usage_clusters_state = "fresh"
             else:
                 state.shared_usage_clusters_state = "stale"
+            emit_stage_component_end(
+                "canonical_materialization",
+                "shared_usage_clusters",
+                component_started,
+            )
 
+            component_started = time.monotonic()
             live_publish_status = "not_attempted"
             live_publish_revision = None
             live_publish_warning = None
@@ -903,6 +1044,11 @@ class ContextorFacade:
 
             cache_dir = str(repo_cache_dir(path))
             file_state_manager = report_result.get("_file_state_manager")
+            emit_stage_component_end(
+                "canonical_materialization",
+                "publish_preparation",
+                component_started,
+            )
 
             emit_stage_end(
                 "canonical_materialization", canonical_materialization_started
@@ -929,13 +1075,26 @@ class ContextorFacade:
             emit_stage_end("persistence", persistence_started)
 
             live_publish_started = time.monotonic()
+            connect_ms = 0.0
+            publish_ms = 0.0
+            status_handling_ms = 0.0
             if meta is not None:
                 from contextor.core.live_state import connect
 
+                client = None
                 try:
-                    client = connect(path)
+                    component_started = time.monotonic()
+                    try:
+                        client = connect(path)
+                    finally:
+                        connect_ms = (time.monotonic() - component_started) * 1000.0
                     if client is not None:
-                        published = client.publish(state, origin=origin)
+                        component_started = time.monotonic()
+                        try:
+                            published = client.publish(state, origin=origin)
+                        finally:
+                            publish_ms = (time.monotonic() - component_started) * 1000.0
+                        component_started = time.monotonic()
                         if (
                             isinstance(published, dict)
                             and published.get("status") == "ok"
@@ -950,25 +1109,90 @@ class ContextorFacade:
                             err = published.get("error") if isinstance(published, dict) else None
                             status_val = published.get("status") if isinstance(published, dict) else None
                             live_publish_warning = err or (f"LIVE service returned status '{status_val}'." if status_val else "Canonical LIVE service rejected publication.")
-                            if log:
-                                log(f"Warning: Failed to publish canonical state to live daemon: {live_publish_warning}")
+                        status_handling_ms = (time.monotonic() - component_started) * 1000.0
+                        if live_publish_status == "failed" and log:
+                            log(f"Warning: Failed to publish canonical state to live daemon: {live_publish_warning}")
                     else:
+                        component_started = time.monotonic()
                         live_publish_status = "not_attempted"
+                        status_handling_ms = (time.monotonic() - component_started) * 1000.0
                 except Exception as e:
+                    component_started = time.monotonic()
                     live_publish_status = "timed_out" if isinstance(e, TimeoutError) else "failed"
                     live_publish_revision = None
                     live_publish_warning = f"{type(e).__name__}: {e}"
+                    status_handling_ms = (time.monotonic() - component_started) * 1000.0
                     if log:
                         log(f"Warning: Failed to publish canonical state to live daemon: {live_publish_warning}")
 
+            emit_stage_component(
+                "live_publish",
+                "connect",
+                connect_ms,
+                status=live_publish_status,
+            )
+            emit_stage_component(
+                "live_publish",
+                "publish",
+                publish_ms,
+                status=live_publish_status,
+            )
+            emit_stage_component(
+                "live_publish",
+                "status_handling",
+                status_handling_ms,
+                status=live_publish_status,
+            )
             emit_stage_end("live_publish", live_publish_started)
 
         else:
+            emit_stage_component_end(
+                "canonical_materialization",
+                "setup_and_imports",
+                canonical_setup_started,
+            )
+            for component in (
+                "topology_analytics",
+                "collision_canonicalization",
+                "artifact_consumption",
+                "module_usage_reuse",
+                "canonical_validation",
+                "lineage_materialization",
+                "lineage_query_indexes",
+                "state_construction",
+                "dependency_matrix",
+                "shared_usage_clusters",
+                "publish_preparation",
+            ):
+                emit_stage_component(
+                    "canonical_materialization",
+                    component,
+                    0.0,
+                    status="skipped",
+                )
             emit_stage_end(
                 "canonical_materialization", canonical_materialization_started
             )
             skipped_stage_started = time.monotonic()
             emit_stage_end("persistence", skipped_stage_started)
+            emit_stage_component(
+                "live_publish",
+                "connect",
+                0.0,
+                status="not_attempted",
+            )
+            emit_stage_component(
+                "live_publish",
+                "publish",
+                0.0,
+                status="not_attempted",
+            )
+            emit_stage_component(
+                "live_publish",
+                "status_handling",
+                0.0,
+                status="not_attempted",
+            )
             emit_stage_end("live_publish", time.monotonic())
 
         finalize_started = time.monotonic()
diff --git a/contextor/core/reporting_engine/pipeline.py b/contextor/core/reporting_engine/pipeline.py
index a82e947..af166f0 100644
--- a/contextor/core/reporting_engine/pipeline.py
+++ b/contextor/core/reporting_engine/pipeline.py
@@ -20,10 +20,12 @@ It does not perform AST analysis or graph analysis itself.
 
 from __future__ import annotations
 
+import time
 from pathlib import Path
 
 from contextor.core.errors import checkpoint
 from contextor.core.program_log import log_program_event
+from contextor.core.runtime_trace import trace_event
 
 # ==========================================================
 # GLOBAL PIPELINE
@@ -66,6 +68,27 @@ def execute_global_pipeline(
     PersistentIdentityRegistry is the single authority for module
     and artifact identity.
     """
+    def emit_report_component_end(
+        component: str,
+        started: float,
+    ) -> float:
+        elapsed_ms = (time.monotonic() - started) * 1000.0
+        trace_event(
+            "ANALYSIS",
+            "FULL_ANALYSIS_STAGE_COMPONENT_END",
+            stage="reports",
+            component=component,
+            operation=f"reports:{component}",
+            elapsed_ms=elapsed_ms,
+            timing_semantics="critical_path_stage_component",
+            result=(
+                f"stage=reports;component={component};"
+                f"elapsed_ms={elapsed_ms:.3f}"
+            ),
+        )
+        return elapsed_ms
+
+    component_started = time.monotonic()
     log_program_event(
         "REPORT", "global pipeline start", repo=repo_name, modules=len(modules)
     )
@@ -206,6 +229,11 @@ def execute_global_pipeline(
         modules,
         precomputed=all_collisions,
     )
+    emit_report_component_end(
+        "basic_report_preparation",
+        component_started,
+    )
+    component_started = time.monotonic()
 
     artifact_bundle = build_artifact_pipeline(
         modules=modules,
@@ -229,6 +257,11 @@ def execute_global_pipeline(
     compact_structure_data = artifact_bundle.compact_structure_data
     graph_analytics_data = artifact_bundle.graph_analytics_data
     raw_shared_usage_clusters = artifact_bundle.raw_shared_usage_clusters
+    emit_report_component_end(
+        "artifact_pipeline",
+        component_started,
+    )
+    component_started = time.monotonic()
 
     # ------------------------------------------------------
     # SANITY CHECK
@@ -250,6 +283,11 @@ def execute_global_pipeline(
                 log(
                     f"[SANITY] {warning}"
                 )
+    emit_report_component_end(
+        "sanity_check",
+        component_started,
+    )
+    component_started = time.monotonic()
 
     # ------------------------------------------------------
     # LAYER REPORTS
@@ -366,6 +404,12 @@ def execute_global_pipeline(
                 ),
             )
 
+    emit_report_component_end(
+        "layer_reports",
+        component_started,
+    )
+    component_started = time.monotonic()
+
     # ------------------------------------------------------
     # GIT STATE
     # ------------------------------------------------------
@@ -389,6 +433,11 @@ def execute_global_pipeline(
     summary_data["git_changes"] = (
         git_section
     )
+    emit_report_component_end(
+        "git_state",
+        component_started,
+    )
+    component_started = time.monotonic()
 
     # ------------------------------------------------------
     # WRITE HIGH-RISK LAYER REPORTS
@@ -425,6 +474,11 @@ def execute_global_pipeline(
                 log=log,
                 layer_output_dir=layer_dir,
             )
+    emit_report_component_end(
+        "high_risk_writes",
+        component_started,
+    )
+    component_started = time.monotonic()
 
     # ------------------------------------------------------
     # GLOBAL REPORT PAYLOAD
@@ -471,6 +525,11 @@ def execute_global_pipeline(
             "All reports have been successfully "
             "generated and saved."
         )
+    emit_report_component_end(
+        "global_report_write",
+        component_started,
+    )
+    component_started = time.monotonic()
 
     # ------------------------------------------------------
     # INCREMENTAL CACHE
@@ -512,6 +571,11 @@ def execute_global_pipeline(
     state_mgr.save(
         datestamp or ""
     )
+    emit_report_component_end(
+        "incremental_file_state",
+        component_started,
+    )
+    component_started = time.monotonic()
 
     # ------------------------------------------------------
     # RETURNED FILE PATHS
@@ -599,6 +663,10 @@ def execute_global_pipeline(
         reports=7,
         layers=len(layer_index_data),
     )
+    emit_report_component_end(
+        "finalization",
+        component_started,
+    )
     return {
         "saved": True,
         "repo": repo_name,
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index c92a174..8fd5a2b 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -1174,6 +1174,7 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
             "execution_mode": "indexer execution mode",
             "timing_semantics": "timing interpretation contract",
             "stage": "full-analysis stage name",
+            "component": "non-overlapping full-analysis stage component name",
             "analysis_ms": "critical-path analysis body milliseconds; same interval as FULL_ANALYSIS_BODY_END.elapsed_ms",
             "total_before_release_ms": "overlapping critical-path total from coordinator start through analysis body end; includes lease wait; not additive",
             "total_ms": "critical-path full coordinator milliseconds including lease wait, analysis body, and lease release; not additive",
@@ -1206,6 +1207,7 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
         [
             "FULL_ANALYSIS_INDEX_EVIDENCE",
             "FULL_ANALYSIS_LINEAGE_MATERIALIZATION",
+            "FULL_ANALYSIS_STAGE_COMPONENT_END",
             "FULL_ANALYSIS_STAGE_END",
         ]
     )
@@ -1379,6 +1381,7 @@ def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | No
                 "execution_mode": "execution_mode",
                 "timing_semantics": "timing_semantics",
                 "stage": "stage",
+                "component": "component",
                 "analysis_ms": "analysis_ms",
                 "total_before_release_ms": "total_before_release_ms",
                 "total_ms": "total_ms",
diff --git a/contextor/mcp/docs/contextor_profile_analysis.json b/contextor/mcp/docs/contextor_profile_analysis.json
index fa717d2..7f4b893 100644
--- a/contextor/mcp/docs/contextor_profile_analysis.json
+++ b/contextor/mcp/docs/contextor_profile_analysis.json
@@ -1,11 +1,11 @@
 {
-  "version": "1.0.0",
+  "version": "1.1.0",
   "tool": "contextor_profile_analysis",
   "purpose": ["Run one repository-wide diagnostic profile through the real production full-analysis path and return a compact, deterministic breakdown of where the analysis spends time and which structured evidence explains known bottlenecks."],
   "parameters": ["repo_path (string, required): canonical repository root to profile.", "exclude_paths (array of strings or null, optional, default null): additional per-run repository-relative exclusions forwarded unchanged to the production full-analysis path."],
-  "behavior": ["1. The MCP coroutine launches a dedicated Contextor profile worker process so the MCP event loop does not execute the synchronous analysis body and the worker's normal full-analysis ProcessPool is isolated from the MCP server process.\n2. The runner attempts the existing canonical full-analysis writer with timeout=0.0; if another writer already owns the repository, status=busy with reason_code=full_analysis_busy is returned instead of waiting and contaminating the sample.\n3. Evidence is captured in memory from the existing runtime trace path under one scoped profile operation; the tool creates no second trace session and reads no JSONL.\n4. Bottleneck ranking uses only FULL_ANALYSIS_STAGE_END critical-path wall timings. Aggregate worker/file-task sums are reported separately and never participate in that ranking.\n5. Known reason codes are derived only from structured runtime evidence. Unknown causes remain unattributed rather than inferred."],
+  "behavior": ["1. The MCP coroutine launches a dedicated Contextor profile worker process so the MCP event loop does not execute the synchronous analysis body and the worker's normal full-analysis ProcessPool is isolated from the MCP server process.\n2. The runner attempts the existing canonical full-analysis writer with timeout=0.0; if another writer already owns the repository, status=busy with reason_code=full_analysis_busy is returned instead of waiting and contaminating the sample.\n3. Evidence is captured in memory from the existing runtime trace path under one scoped profile operation; the tool creates no second trace session and reads no JSONL.\n4. Bottleneck ranking uses only FULL_ANALYSIS_STAGE_END critical-path wall timings. Aggregate worker/file-task sums are reported separately and never participate in that ranking.\n5. The wide stages identity_and_setup, reports, canonical_materialization, and live_publish emit non-overlapping structured stage-component evidence; the profiler selects the dominant measured component or measured residual, while canonical lineage retains nested lineage attribution."],
   "freshness": ["The tool executes a real full repository analysis and therefore refreshes the same canonical analysis state and LIVE publication path as the normal production full-analysis owner when the run succeeds.", "The returned profile describes only the analysis executed by this call. It is not a historical profiler report and is not persisted as a separate profiling artifact."],
   "errors": ["A missing or non-directory repo_path returns an Error string before starting the profile runner.", "status=busy with reason_code=full_analysis_busy means another canonical full-analysis writer already owns the repository; retry later rather than treating the result as a performance sample.", "status=incomplete means required structured profile evidence was missing or duplicated.", "status=invalid_evidence means captured timing/evidence contracts were internally inconsistent.", "Unexpected production analysis failures propagate through the normal central MCP wrapper and are not converted into profiler guesses."],
-  "usage_notes": ["Use this tool to identify which analysis stages dominate and why, not to establish clean-machine absolute benchmark time. The response explicitly marks absolute_wall_authoritative=false because caller/runtime load can inflate wall duration.", "One run is normally sufficient for architectural diagnosis. Repeat only when confirming a specific optimization or investigating unstable evidence.", "Do not add aggregate source_parse_sum_ms, cache_get_sum_ms, or lineage_extract_sum_ms to critical-path stage durations; those values are aggregate file-task diagnostics and may exceed wall time under parallel execution."],
-  "examples": ["Call contextor_profile_analysis(repo_path=\"C:\\\\Temp\\\\Contextor_Repo\") and inspect bottlenecks first. A reason_code such as warm_cache_still_parses_source or lineage_reuse_gate_cost is evidence-backed; unattributed means the current structured signals do not justify a stronger causal claim."]
+  "usage_notes": ["Use this tool to identify which analysis stages dominate and why, not to establish clean-machine absolute benchmark time. The response explicitly marks absolute_wall_authoritative=false because caller/runtime load can inflate wall duration.", "One run is normally sufficient for architectural diagnosis. Repeat only when confirming a specific optimization or investigating unstable evidence.", "Do not add aggregate source_parse_sum_ms, cache_get_sum_ms, or lineage_extract_sum_ms to critical-path stage durations; those values are aggregate file-task diagnostics and may exceed wall time under parallel execution.", "stage_attribution returns component timings, component_sum_ms, residual_ms, coverage_pct, and dominant_component for identity_and_setup, reports, canonical_materialization, and live_publish.", "residual_ms is the critical-path portion of a stage not covered by named components and must not be heuristically allocated."] ,
+  "examples": ["Call contextor_profile_analysis(repo_path=\"C:\\\\Temp\\\\Contextor_Repo\") and inspect bottlenecks first. Evidence-backed reason_code examples include artifact_pipeline_cost, lineage_reuse_gate_cost, live_publish_ipc_cost, and repository_identity_cost."]
 }
diff --git a/tests/test_profile_analysis.py b/tests/test_profile_analysis.py
index 6d81b6a..265b86c 100644
--- a/tests/test_profile_analysis.py
+++ b/tests/test_profile_analysis.py
@@ -109,6 +109,59 @@ def _profile_events(operation_id: str = "profile-test"):
         }
         for stage, elapsed_ms in stage_ms.items()
     )
+    component_ms = {
+        "identity_and_setup": {
+            "progress_setup": 1.0,
+            "repository_identity": 8.0,
+            "authoritative_state_resolution": 5.0,
+            "cache_reset": 1.0,
+            "analysis_filters_and_index_progress": 4.0,
+        },
+        "reports": {
+            "basic_report_preparation": 20.0,
+            "artifact_pipeline": 80.0,
+            "sanity_check": 5.0,
+            "layer_reports": 30.0,
+            "git_state": 10.0,
+            "high_risk_writes": 10.0,
+            "global_report_write": 20.0,
+            "incremental_file_state": 20.0,
+            "finalization": 4.0,
+        },
+        "canonical_materialization": {
+            "setup_and_imports": 0.5,
+            "topology_analytics": 0.5,
+            "collision_canonicalization": 0.5,
+            "artifact_consumption": 0.5,
+            "module_usage_reuse": 0.5,
+            "canonical_validation": 0.5,
+            "lineage_materialization": 70.0,
+            "lineage_query_indexes": 0.5,
+            "state_construction": 0.5,
+            "dependency_matrix": 0.5,
+            "shared_usage_clusters": 0.5,
+            "publish_preparation": 0.5,
+        },
+        "live_publish": {
+            "connect": 5.0,
+            "publish": 25.0,
+            "status_handling": 2.0,
+        },
+    }
+    for stage, components in component_ms.items():
+        events.extend(
+            {
+                "d": "ANALYSIS",
+                "ev": "FULL_ANALYSIS_STAGE_COMPONENT_END",
+                "op": operation_id,
+                "stage": stage,
+                "component": component,
+                "elapsed_ms": elapsed_ms,
+                "timing_semantics": "critical_path_stage_component",
+                **({"status": "success"} if stage == "live_publish" else {}),
+            }
+            for component, elapsed_ms in components.items()
+        )
     return events
 
 
@@ -164,9 +217,25 @@ def test_profile_ranks_only_critical_path_and_attributes_known_causes():
         if item["stage"] == "canonical_materialization"
     )
     assert canonical["reason_code"] == "lineage_reuse_gate_cost"
+    assert canonical["evidence"]["dominant_component"] == "lineage_materialization"
+    assert canonical["evidence"]["lineage_reason_code"] == "lineage_reuse_gate_cost"
     assert canonical["evidence"]["lineage_elapsed_ms"] == 70.0
     assert canonical["evidence"]["reuse_gate_ms"] == 60.0
 
+    assert profile["stage_attribution"]["identity_and_setup"]["reason_code"] == (
+        "repository_identity_cost"
+    )
+    assert profile["stage_attribution"]["reports"]["reason_code"] == (
+        "artifact_pipeline_cost"
+    )
+    assert profile["stage_attribution"]["canonical_materialization"]["reason_code"] == (
+        "lineage_reuse_gate_cost"
+    )
+    live_attribution = profile["stage_attribution"]["live_publish"]
+    assert live_attribution["reason_code"] == "live_publish_ipc_cost"
+    assert live_attribution["publish_ms"] == 25.0
+    assert live_attribution["stage_status"] == "success"
+
     aggregate = profile["aggregate_worker_diagnostics"]
     assert aggregate["timing_semantics"] == (
         "aggregate_file_task_not_critical_path"
@@ -224,3 +293,42 @@ def test_profile_rejects_invalid_overlapping_coordinator_contract():
         profile["error"]
         == "total_before_release_ms cannot be shorter than analysis_ms"
     )
+
+
+def test_profile_fails_closed_when_stage_component_evidence_is_missing():
+    events = [
+        event
+        for event in _profile_events()
+        if not (
+            event["ev"] == "FULL_ANALYSIS_STAGE_COMPONENT_END"
+            and event["stage"] == "reports"
+            and event["component"] == "artifact_pipeline"
+        )
+    ]
+
+    profile = build_analysis_profile(events, operation_id="profile-test")
+
+    assert profile["status"] == "incomplete"
+    assert profile["missing"] == [
+        "FULL_ANALYSIS_STAGE_COMPONENT_END:reports:artifact_pipeline"
+    ]
+
+
+def test_profile_rejects_invalid_stage_component_timing_semantics():
+    events = _profile_events()
+    component = next(
+        event
+        for event in events
+        if event["ev"] == "FULL_ANALYSIS_STAGE_COMPONENT_END"
+        and event["stage"] == "reports"
+        and event["component"] == "artifact_pipeline"
+    )
+    component["timing_semantics"] = "aggregate"
+
+    profile = build_analysis_profile(events, operation_id="profile-test")
+
+    assert profile["status"] == "invalid_evidence"
+    assert profile["error"] == (
+        "FULL_ANALYSIS_STAGE_COMPONENT_END:reports:artifact_pipeline "
+        "has invalid timing_semantics"
+    )
diff --git a/tests/test_runtime_trace.py b/tests/test_runtime_trace.py
index c9e981f..576d1ea 100644
--- a/tests/test_runtime_trace.py
+++ b/tests/test_runtime_trace.py
@@ -75,7 +75,7 @@ def test_canonical_writer_analysis_trace_is_self_describing_and_durable():
     assert {"CANONICAL_WRITER_ADMISSION_ACQUIRED", "CANONICAL_WRITER_ADMISSION_RELEASED", "FULL_ANALYSIS_LEASE_ACQUIRED", "FULL_ANALYSIS_BODY_END", "FULL_ANALYSIS_END"} <= set(records[4]["events"]["ANALYSIS"])
     assert {
         "owner", "writer_kind", "execution_mode", "timing_semantics",
-        "stage", "analysis_ms", "total_before_release_ms", "total_ms",
+        "stage", "component", "analysis_ms", "total_before_release_ms", "total_ms",
         "file_tasks", "source_parse_calls", "source_parse_failures",
         "cache_get_calls", "cache_hits", "cache_misses", "lineage_cache_hits",
         "lineage_extract_calls", "source_parse_sum_ms", "cache_get_sum_ms",
@@ -88,6 +88,7 @@ def test_canonical_writer_analysis_trace_is_self_describing_and_durable():
     assert {
         "FULL_ANALYSIS_INDEX_EVIDENCE",
         "FULL_ANALYSIS_LINEAGE_MATERIALIZATION",
+        "FULL_ANALYSIS_STAGE_COMPONENT_END",
         "FULL_ANALYSIS_STAGE_END",
     } <= set(records[4]["events"]["ANALYSIS"])
     acquired = next(item for item in records if item.get("ev") == "CANONICAL_WRITER_ADMISSION_ACQUIRED")
@@ -108,8 +109,21 @@ def test_full_analysis_stage_evidence_is_structured_in_memory():
             timing_semantics="critical_path_stage",
             result="stage=indexing;elapsed_ms=12.500",
         )
+        trace.trace_event(
+            "ANALYSIS",
+            "FULL_ANALYSIS_STAGE_COMPONENT_END",
+            stage="reports",
+            component="artifact_pipeline",
+            operation="reports:artifact_pipeline",
+            elapsed_ms=7.5,
+            timing_semantics="critical_path_stage_component",
+            result=(
+                "stage=reports;component=artifact_pipeline;"
+                "elapsed_ms=7.500"
+            ),
+        )
 
-    assert len(events) == 1
+    assert len(events) == 2
     event = events[0]
     assert event["ev"] == "FULL_ANALYSIS_STAGE_END"
     assert event["stage"] == "indexing"
@@ -117,6 +131,12 @@ def test_full_analysis_stage_evidence_is_structured_in_memory():
     assert event["elapsed_ms"] == 12.5
     assert event["timing_semantics"] == "critical_path_stage"
     assert event["result"] == "stage=indexing;elapsed_ms=12.500"
+    component_event = events[1]
+    assert component_event["component"] == "artifact_pipeline"
+    assert component_event["elapsed_ms"] == 7.5
+    assert component_event["timing_semantics"] == (
+        "critical_path_stage_component"
+    )
 
 
 def test_diagnostic_trace_fields_and_structured_node_arrays_are_durable():

```


## CPA10F_PROFILE_ATTRIBUTION_GAP_DISCOVERY

STATUS=DISCOVERY_COMPLETE
FILES_CHANGED=NONE
DIFFS=NONE

Contextor-first evidence used `get_symbol_call_context`, `get_symbol_implementation`, `search_source`, and `get_source_range`; source was read only through Contextor tools. The four stage boundaries are all in `contextor/core/api/facade.py`, inside `ContextorFacade.analyze_project`.

### identity_and_setup

- START_BOUNDARY=`identity_and_setup_started = facade_started` (line 589).
- END_BOUNDARY=`emit_stage_end("identity_and_setup", identity_and_setup_started)` (line 604).
- DIRECT_CALLS_IN_EXECUTION_ORDER=`_StagedProgress(...)`; `progress.begin("Initializing repository identity")`; `_initialize_repository_identity(path)`; `path = str(registry.repo_path.resolve())`; `resolve_authoritative_repository_state(path)`; `reset_caches()`; `_analysis_filters(path, additional_excludes)`; `progress.begin("Indexing repository files")`.
- EXISTING_TRACE_EVENTS=only `FULL_ANALYSIS_STAGE_END(stage="identity_and_setup")` with stage `elapsed_ms`.
- UNINSTRUMENTED_CALLS=every listed subcall has no individual elapsed field in this stage.
- RETURN/STATUS_VALUES_AVAILABLE_FOR_EVIDENCE=registry; canonical state object; canonical path; excludes/extra_dirs; index progress callback.

### reports

- START_BOUNDARY=`reports_started = time.monotonic()` (line 688).
- END_BOUNDARY=`emit_stage_end("reports", reports_started)` (line 713).
- FILE=`contextor/core/api/facade.py`; owning execution call=`contextor.core.reporting_engine.pipeline::execute_global_pipeline`.
- DIRECT_CALLS_IN_EXECUTION_ORDER=`datetime.now().strftime`; `progress.begin("Generating architectural reports")`; `execute_global_pipeline(...)`; optional high-risk-layer log handling.
- EXISTING_TRACE_EVENTS=only `FULL_ANALYSIS_STAGE_END(stage="reports")` at facade level.
- UNINSTRUMENTED_CALLS=inside `execute_global_pipeline`, including collision/basic preparation, summary/structure/collision output, artifact pipeline, sanity check, layer slicing/execution, git state, high-risk writes, global writes, and FileStateManager population/save, have no facade stage sub-boundary exposed to profile analysis.
- RETURN/STATUS_VALUES_AVAILABLE_FOR_EVIDENCE=`report_result`, including `_analysis_result`, `_file_state_manager`, `_raw_shared_usage_clusters`, and `_artifact_data` later consumed by canonical materialization.

### canonical_materialization

- START_BOUNDARY=`canonical_materialization_started = time.monotonic()` (line 719).
- END_BOUNDARY=`emit_stage_end("canonical_materialization", canonical_materialization_started)` (line 905).
- FILE=`contextor/core/api/facade.py`.
- DIRECT_CALLS_IN_EXECUTION_ORDER=topology analytics; collision fact validation and canonical collision calculation; canonical artifact consumption; `build_module_usage_baseline_with_reuse`; consumption coverage validation; syntax diagnostics; `_materialize_full_analysis_lineage`; `build_lineage_query_indexes`; `RepositoryAnalysisState` construction; dependency matrix calculation; shared-usage-cluster handoff/compute; writer/origin/cache/file-state preparation.
- EXISTING_TRACE_EVENTS=stage end plus nested `FULL_ANALYSIS_LINEAGE_MATERIALIZATION` emitted by `_materialize_full_analysis_lineage`.
- NESTED_LINEAGE_FIELDS=`elapsed_ms`, `reuse_sources`, `reresolve_sources`, `materialize_sources`, `reresolve_fallback_sources`, `reuse_gate_ms`, `reresolve_calls_ms`, `materialize_calls_ms`, `lineage_sources`, anchors/flows/surfaces/descriptors.
- NESTED_LINEAGE_EXCLUDES=topology, collision canonicalization, consumption, module usage, coverage, diagnostics, query indexes, state construction, dependency matrix, clusters, and stage preparation; it therefore does not cover most of the canonical stage.
- RETURN/STATUS_VALUES_AVAILABLE_FOR_EVIDENCE=state family states, lineage state/version/indexes, matrix/cluster states, writer/origin/cache/file-state manager.

### live_publish

- START_BOUNDARY=`live_publish_started = time.monotonic()` (line 934).
- END_BOUNDARY=`emit_stage_end("live_publish", live_publish_started)` (line 965).
- DIRECT_CALLS_IN_EXECUTION_ORDER=`connect(path)`; if client exists, `client.publish(state, origin=origin)`; dictionary `status/revision/error` handling; timeout/general exception handling.
- RETURN/STATUS_VALUES_AVAILABLE_FOR_EVIDENCE=`live_publish_status` (`success`, `failed`, `not_attempted`, `timed_out`), revision, and warning.
- EXISTING_TRACE_EVENTS=facade stage end only. Existing structured elapsed data from `connect`/`publish` is not exposed to this facade stage as profile evidence.

### profile_analysis current attribution contract

- `_REQUIRED_SINGLE_EVENTS` requires the full-analysis facade end and one stage-end event per required stage; it validates stage completeness, not stage-specific attribution.
- Existing dedicated reason functions discovered: `_indexing_reason` and `_canonical_materialization_reason`.
- `_indexing_reason` returns `unattributed` unless parse failures, warm-cache exact conditions, or cache misses/lineage extraction conditions match.
- `_canonical_materialization_reason` returns `unattributed` unless materialization, re-resolution/fallback, or the lineage-reuse-gate threshold (`lineage_elapsed_ms >= stage_ms * 0.5`) matches.
- identity_and_setup, reports, and live_publish have no dedicated reason function and therefore their profile bottlenecks are `unattributed` by definition when selected.
- `runtime_trace.trace_event` currently allows the existing lineage nested fields and standard elapsed/stage/result fields. The profile evidence above contains no individual fields for the uninstrumented subphases; any distinct new measurement field would require a trace-event allowlist extension before it could be serialized.

### ATTRIBUTION_GAPS

- identity_and_setup: CPA10E=8,796 ms; visible evidence=stage elapsed only; uninstrumented=_StagedProgress, repository identity, canonical path resolution, authoritative-state resolve, cache reset, filters; owner=`contextor/core/api/facade.py`.
- reports: CPA10E=5,485 ms; visible evidence=stage elapsed only; uninstrumented=the actual `execute_global_pipeline` subphases listed above; owners=`contextor/core/api/facade.py`, `contextor/core/reporting_engine/pipeline.py`.
- canonical_materialization: CPA10E=24,281 ms; visible evidence=lineage nested timing fields (`lineage_elapsed_ms=6,344`, `reuse_gate_ms=3,594`, 397 reuse sources); uninstrumented=all non-lineage operations listed above; owner=`contextor/core/api/facade.py`.
- live_publish: CPA10E=9,266 ms; visible evidence=stage elapsed and final status/revision/warning only; uninstrumented=connect/publish response and exception subphases; owner=`contextor/core/api/facade.py` plus LIVE client implementation.

No solution, reason-code taxonomy, instrumentation, tests, profiler run, runtime restart, or production/test change was proposed or performed.

## CPA10E_FULL_ANALYSIS_PROFILE

STATUS=DISCOVERY_COMPLETE
FILES_CHANGED=NONE
DIFFS=NONE

Source: Contextor MCP `contextor_profile_analysis(repo_path="C:\\Temp\\Contextor_Repo")`; operation `profile-11132-1`; status `ok`. This is a diagnostic profile, not an authoritative absolute benchmark (`absolute_wall_authoritative=false`).

### Total wall time

- `total_ms=124,360`
- `total_before_release_ms=124,344`
- `lease_wait_ms=125`
- `analysis_body_ms=123,484`
- `stage_sum_ms=123,031`
- `unattributed_analysis_ms=453`

### FULL_ANALYSIS_STAGE_END critical-path durations

| stage | critical_path_ms |
|---|---:|
| identity_and_setup | 8,796 |
| indexing | 69,719 |
| reference_and_collision | 656 |
| graph | 110 |
| validation | 47 |
| metrics | 15 |
| reports | 5,485 |
| canonical_materialization | 24,281 |
| persistence | 4,656 |
| live_publish | 9,266 |
| finalize | 0 |

### Bottleneck ranking and structured evidence

1. `indexing`: 69,719 ms (56.46% of analysis); `reason_code=cold_or_partial_cache_work`.
   - `file_tasks=397`, `source_parse_calls=397`, `source_parse_failures=0`
   - `cache_get_calls=397`, `cache_hits=387`, `cache_misses=10`
   - `lineage_cache_hits=387`, `lineage_extract_calls=10`
2. `canonical_materialization`: 24,281 ms (19.66%); `reason_code=unattributed`.
   - `lineage_elapsed_ms=6,344`, `lineage_sources=397`, `reuse_sources=397`
   - `reresolve_sources=0`, `materialize_sources=0`, `reresolve_fallback_sources=0`
   - `reuse_gate_ms=3,594`, `reresolve_calls_ms=0`, `materialize_calls_ms=0`
3. `live_publish`: 9,266 ms (7.50%); `reason_code=unattributed`; no structured evidence returned.
4. `identity_and_setup`: 8,796 ms (7.12%); `reason_code=unattributed`; no structured evidence returned.
5. `reports`: 5,485 ms (4.44%); `reason_code=unattributed`; no structured evidence returned.

### Aggregate worker/file-task diagnostics — not critical path

`timing_semantics=aggregate_file_task_not_critical_path`.

- `source_parse_sum_ms=19,258`
- `cache_get_sum_ms=53,973`
- `lineage_extract_sum_ms=8,376`
- `lineage_extract_event_sum_ms=8,376`

These aggregate sums are intentionally not added to critical-path stage durations.

### Conclusion / stopping condition

The current profile proves that the dominant current critical-path stage is indexing, with `cold_or_partial_cache_work`; it does not attribute the other substantial stages listed above. It does **not** prove the source of a historical increase from approximately 16 s to approximately 44 s: no paired historical profile/baseline was provided by this single operation, and three material stages are explicitly `unattributed`.

Missing signals needed before any stronger causal claim: a comparable earlier profile and structured timing/reason evidence for canonical materialization, LIVE publication, identity/setup, and reports. No manual profiler, trace parsing, follow-up analysis, or optimization was performed.

## CPA10E_LIVE_MUTATION_33S_TRACE_DECOMPOSITION

TARGET_OP=u-10812-1
TARGET_JOB=mu-f185bdb1be6142cd89ca681ee43cf015
TARGET_PATH=C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\ipc.py

Contextor-first call-path evidence: `CanonicalLiveServer._execute_queued_update_file` directly calls `_execute_update_file`; `run_service` constructs both `_repository_mutation_guard` and `_repository_updater`; `_execute_update_file` has canonical clone, event, persistence, diagnostic, and commit call edges. Static context does not fully materialize the dynamic factory edge from the coordinator worker to the guard/updater, so that link is confirmed by the target-op runtime trace rather than inferred from source alone.

The literal first trace script supplied with this task had an unclosed final `print(` and raised `SyntaxError`; a minimally corrected read-only copy was used for the exact same trace selection. The second supplied PID-window reader returned exactly the same 15 target-op records and no records without that op.

### Trace timeline

Source: `C:\\Users\\DafoO\\AppData\\Roaming\\Contextor\\logs\\contextor_runtime_20260915_085219_808_11296.jsonl`, lines 419–433; PID 10812, TID 4884. Trace span: **32,796 ms**, 15 records.

| since first ms | event | measured event elapsed_ms |
|---:|---|---:|
| 0 | CANONICAL_WRITER_ADMISSION_ACQUIRED | — |
| 46 | CANONICAL_WRITER_ADMISSION_RELEASED | — |
| 46 | UPDATE_RECEIVED | — |
| 27,640 | CLONE_END | — |
| 27,640 | UPDATER_START | — |
| 28,000 | ENGINE_READY | 360 |
| 28,031 | INCREMENTAL_END (`UNCHANGED`) | 31 |
| 28,031 | UPDATER_END (`UNCHANGED`) | 391 |
| 28,046 | PERSIST_START | — |
| 32,781 | SNAPSHOT_SAVE_END | 4,735 |
| 32,796 | FILE_STATE_SAVE_END / PERSIST_END / CANONICAL_COMMIT / ACTIVITY_APPEND / UPDATE_PUBLISHED | 0 / — |

### Cost decomposition

1. QUEUE_TO_ADMISSION
   - START_EVENT=UNAVAILABLE
   - END_EVENT=CANONICAL_WRITER_ADMISSION_ACQUIRED
   - MEASURED_MS=UNAVAILABLE
   - EVIDENCE=no enqueue/worker-start trace boundary for this job
   - CONFIDENCE=UNAVAILABLE

2. ADMISSION_AND_LEASE_ACQUIRE
   - START_EVENT=CANONICAL_WRITER_ADMISSION_ACQUIRED
   - END_EVENT=CANONICAL_WRITER_ADMISSION_RELEASED
   - MEASURED_MS=46
   - EVIDENCE=target trace lines 419–420; acquisition `wait_ms=0.0`
   - CONFIDENCE=PROVEN

3. CANONICAL_STATE_CLONE
   - START_EVENT=UPDATE_RECEIVED
   - END_EVENT=CLONE_END
   - MEASURED_MS=27,594
   - EVIDENCE=target trace lines 421–422
   - CONFIDENCE=PROVEN

4. UPDATER_SETUP / ENGINE_READY
   - START_EVENT=UPDATER_START
   - END_EVENT=ENGINE_READY
   - MEASURED_MS=360
   - EVIDENCE=target lines 423–424; `ENGINE_READY.elapsed_ms=360`
   - CONFIDENCE=PROVEN

5. INCREMENTAL_PREPARATION
   - START_EVENT=ENGINE_READY
   - END_EVENT=INCREMENTAL_END
   - MEASURED_MS=31
   - EVIDENCE=target lines 424–425; `INCREMENTAL_END.elapsed_ms=31`, status `UNCHANGED`
   - CONFIDENCE=PROVEN

6. REFRESH_PLAN_EXECUTION
   - START_EVENT=UNAVAILABLE
   - END_EVENT=UNAVAILABLE
   - MEASURED_MS=UNAVAILABLE
   - EVIDENCE=no target-op trace boundary
   - CONFIDENCE=UNAVAILABLE

7. IDENTITY_REGISTRY_SYNC
   - START_EVENT=UNAVAILABLE
   - END_EVENT=UNAVAILABLE
   - MEASURED_MS=UNAVAILABLE
   - EVIDENCE=no target-op trace boundary
   - CONFIDENCE=UNAVAILABLE

8. LINEAGE
   - START_EVENT=UNAVAILABLE
   - END_EVENT=UNAVAILABLE
   - MEASURED_MS=UNAVAILABLE
   - EVIDENCE=no target-op trace boundary or lineage counters
   - CONFIDENCE=UNAVAILABLE

9. OTHER_INCREMENTAL_WORK
   - START_EVENT=UNAVAILABLE
   - END_EVENT=UNAVAILABLE
   - MEASURED_MS=UNAVAILABLE
   - EVIDENCE=the trace does not subdivide the 31 ms incremental segment
   - CONFIDENCE=UNAVAILABLE

10. PERSISTENCE
   - START_EVENT=PERSIST_START
   - END_EVENT=PERSIST_END
   - MEASURED_MS=4,750
   - EVIDENCE=lines 427–430; dominated by `SNAPSHOT_SAVE_END.elapsed_ms=4,735`, followed by 15 ms to FILE_STATE_SAVE_END
   - CONFIDENCE=PROVEN

11. COMMIT/PUBLISH
   - START_EVENT=CANONICAL_COMMIT
   - END_EVENT=UPDATE_PUBLISHED
   - MEASURED_MS=0 at trace monotonic-millisecond resolution
   - EVIDENCE=lines 431–433 share `mono_ms=6258671`
   - CONFIDENCE=PROVEN

12. UNATTRIBUTED_GAP
   - START_EVENT=UNAVAILABLE
   - END_EVENT=UNAVAILABLE
   - MEASURED_MS=UNAVAILABLE
   - EVIDENCE=all observed large gaps have explicit enclosing trace boundaries; the clone interior itself is not further decomposed
   - CONFIDENCE=UNAVAILABLE

### Required findings

- A. The approximately 33 s occurs **after** `CANONICAL_WRITER_ADMISSION_RELEASED`; release is at +46 ms, while the trace ends at +32,796 ms.
- B. ACQUIRED → RELEASED = **46 ms** (`wait_ms=0.0` on acquire).
- C. UPDATE_RECEIVED → CLONE_END = **27,594 ms**.
- D. UPDATER_START → ENGINE_READY = **360 ms**.
- E. ENGINE_READY → INCREMENTAL_END = **31 ms**.
- F. UPDATER_END → CANONICAL_COMMIT = **4,765 ms**; UPDATER_END → UPDATE_PUBLISHED = **4,765 ms**.
- G. Largest adjacent-event gap = **27,594 ms**, UPDATE_RECEIVED → CLONE_END.
- H. `DOMINANT_COST=CLONE`.
- I. Yes. `status=UNCHANGED` is emitted at INCREMENTAL_END, **27,625 ms** after UPDATE_RECEIVED; it follows the 27,594 ms clone segment.
- J. No. The wider PID=10812 selection for 09:03:45Z–09:04:30Z contains only these 15 records, all with `op=u-10812-1`; no op-less event explains either large gap.

FULL_ANALYSIS_44S_CAUSAL_LINK=NOT_SUPPORTED

There is no trace here from a specific full-analysis run waiting on this particular mutation/lease. Similar wall-clock magnitudes alone are not causal evidence.

FILES_CHANGED=NONE
DIFFS=NONE

## CPA10G_PERSISTENCE_STAGE_ATTRIBUTION

STATUS=IMPLEMENTATION_COMPLETE_TESTS_PASS
HEAD_BEFORE=15b8f4e5c930d5bab8fd7159d745fe2eeb1ef2da
HEAD_AFTER=15b8f4e5c930d5bab8fd7159d745fe2eeb1ef2da
FILES_CHANGED=4 (the exact requested production/test/docs files; walkthrough.md excluded)
PY_COMPILE=PASS
TESTS=PASS — 57 passed in 24.57s
PROFILE_RUN=NOT_RUN
PROFILE_WORKER_RESTART_REQUIRED=NO
MCP_SERVER_RESTART_REQUIRED=NO_FOR_PROFILE_EXECUTION
DESKTOP_RUNTIME_RESTART_REQUIRED=YES_BEFORE_DESKTOP_CERTIFICATION

IMPLEMENTATION_SCOPE=Persistence stage now has exactly three non-overlapping critical-path components: metadata_and_revision, file_state_payload, snapshot_save. Existing save/revision/snapshot semantics and operation order were preserved; no store.py telemetry or optimization was added.
PROFILE_CONTRACT=persistence is included in _REQUIRED_STAGE_COMPONENTS and _COMPONENT_REASON_CODES; existing _stage_component_reason and generic stage_attribution/bottleneck paths handle it without a persistence special case.
CONTEXTOR_FIRST_VERIFICATION=Contextor resolved ContextorFacade.analyze_project and _stage_component_reason with workspace_sync=verified. Call-context queries resolved analyze_project and build_analysis_profile with workspace_sync=verified; canonical revision 1152. No runtime profile was run.

ACTUAL_DIFF=
```diff
diff --git a/contextor/core/analysis/profile_analysis.py b/contextor/core/analysis/profile_analysis.py
index 17f3e8f..3566f44 100644
--- a/contextor/core/analysis/profile_analysis.py
+++ b/contextor/core/analysis/profile_analysis.py
@@ -61,6 +61,11 @@ _REQUIRED_STAGE_COMPONENTS = {
         "shared_usage_clusters",
         "publish_preparation",
     ),
+    "persistence": (
+        "metadata_and_revision",
+        "file_state_payload",
+        "snapshot_save",
+    ),
     "live_publish": (
         "connect",
         "publish",
@@ -103,6 +108,12 @@ _COMPONENT_REASON_CODES = {
         "publish_preparation": "canonical_publish_preparation_cost",
         "__residual__": "canonical_materialization_residual_cost",
     },
+    "persistence": {
+        "metadata_and_revision": "persistence_metadata_revision_cost",
+        "file_state_payload": "persistence_file_state_payload_cost",
+        "snapshot_save": "snapshot_save_cost",
+        "__residual__": "persistence_residual_cost",
+    },
     "live_publish": {
         "connect": "live_connect_cost",
         "publish": "live_publish_ipc_cost",
@@ -298,6 +309,7 @@ def _stage_component_reason(
             "identity_and_setup": "identity_setup_no_work",
             "reports": "reports_no_work",
             "canonical_materialization": "canonical_materialization_no_work",
+            "persistence": "persistence_no_work",
             "live_publish": "live_publish_not_attempted",
         }
         return zero_reason[stage], evidence
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 980ad5c..1feadcb 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -1054,13 +1054,36 @@ class ContextorFacade:
                 "canonical_materialization", canonical_materialization_started
             )
             persistence_started = time.monotonic()
+
+            component_started = time.monotonic()
             current_metadata = read_metadata(cache_dir)
-            target_revision = (current_metadata.revision if current_metadata else 0) + 1
+            target_revision = (
+                current_metadata.revision
+                if current_metadata
+                else 0
+            ) + 1
+            emit_stage_component_end(
+                "persistence",
+                "metadata_and_revision",
+                component_started,
+            )
+
+            component_started = time.monotonic()
             file_state_payload = (
-                file_state_manager.build_payload(datestamp or "", target_revision)
+                file_state_manager.build_payload(
+                    datestamp or "",
+                    target_revision,
+                )
                 if file_state_manager is not None
                 else None
             )
+            emit_stage_component_end(
+                "persistence",
+                "file_state_payload",
+                component_started,
+            )
+
+            component_started = time.monotonic()
             meta = save_engine_state(
                 state,
                 cache_dir,
@@ -1071,6 +1094,16 @@ class ContextorFacade:
                 exact_revision=target_revision,
                 file_state_payload=file_state_payload,
             )
+            emit_stage_component_end(
+                "persistence",
+                "snapshot_save",
+                component_started,
+                status=(
+                    "success"
+                    if meta is not None
+                    else "failed"
+                ),
+            )
 
             emit_stage_end("persistence", persistence_started)
 
@@ -1174,6 +1207,24 @@ class ContextorFacade:
                 "canonical_materialization", canonical_materialization_started
             )
             skipped_stage_started = time.monotonic()
+            emit_stage_component(
+                "persistence",
+                "metadata_and_revision",
+                0.0,
+                status="skipped",
+            )
+            emit_stage_component(
+                "persistence",
+                "file_state_payload",
+                0.0,
+                status="skipped",
+            )
+            emit_stage_component(
+                "persistence",
+                "snapshot_save",
+                0.0,
+                status="skipped",
+            )
             emit_stage_end("persistence", skipped_stage_started)
             emit_stage_component(
                 "live_publish",
diff --git a/contextor/mcp/docs/contextor_profile_analysis.json b/contextor/mcp/docs/contextor_profile_analysis.json
index 7f4b893..a71a1ac 100644
--- a/contextor/mcp/docs/contextor_profile_analysis.json
+++ b/contextor/mcp/docs/contextor_profile_analysis.json
@@ -1,11 +1,11 @@
 {
-  "version": "1.1.0",
+  "version": "1.2.0",
   "tool": "contextor_profile_analysis",
   "purpose": ["Run one repository-wide diagnostic profile through the real production full-analysis path and return a compact, deterministic breakdown of where the analysis spends time and which structured evidence explains known bottlenecks."],
   "parameters": ["repo_path (string, required): canonical repository root to profile.", "exclude_paths (array of strings or null, optional, default null): additional per-run repository-relative exclusions forwarded unchanged to the production full-analysis path."],
-  "behavior": ["1. The MCP coroutine launches a dedicated Contextor profile worker process so the MCP event loop does not execute the synchronous analysis body and the worker's normal full-analysis ProcessPool is isolated from the MCP server process.\n2. The runner attempts the existing canonical full-analysis writer with timeout=0.0; if another writer already owns the repository, status=busy with reason_code=full_analysis_busy is returned instead of waiting and contaminating the sample.\n3. Evidence is captured in memory from the existing runtime trace path under one scoped profile operation; the tool creates no second trace session and reads no JSONL.\n4. Bottleneck ranking uses only FULL_ANALYSIS_STAGE_END critical-path wall timings. Aggregate worker/file-task sums are reported separately and never participate in that ranking.\n5. The wide stages identity_and_setup, reports, canonical_materialization, and live_publish emit non-overlapping structured stage-component evidence; the profiler selects the dominant measured component or measured residual, while canonical lineage retains nested lineage attribution."],
+  "behavior": ["1. The MCP coroutine launches a dedicated Contextor profile worker process so the MCP event loop does not execute the synchronous analysis body and the worker's normal full-analysis ProcessPool is isolated from the MCP server process.\n2. The runner attempts the existing canonical full-analysis writer with timeout=0.0; if another writer already owns the repository, status=busy with reason_code=full_analysis_busy is returned instead of waiting and contaminating the sample.\n3. Evidence is captured in memory from the existing runtime trace path under one scoped profile operation; the tool creates no second trace session and reads no JSONL.\n4. Bottleneck ranking uses only FULL_ANALYSIS_STAGE_END critical-path wall timings. Aggregate worker/file-task sums are reported separately and never participate in that ranking.\n5. The wide stages identity_and_setup, reports, canonical_materialization, persistence, and live_publish emit non-overlapping structured stage-component evidence; the profiler selects the dominant measured component or measured residual, while canonical lineage retains nested lineage attribution."],
   "freshness": ["The tool executes a real full repository analysis and therefore refreshes the same canonical analysis state and LIVE publication path as the normal production full-analysis owner when the run succeeds.", "The returned profile describes only the analysis executed by this call. It is not a historical profiler report and is not persisted as a separate profiling artifact."],
   "errors": ["A missing or non-directory repo_path returns an Error string before starting the profile runner.", "status=busy with reason_code=full_analysis_busy means another canonical full-analysis writer already owns the repository; retry later rather than treating the result as a performance sample.", "status=incomplete means required structured profile evidence was missing or duplicated.", "status=invalid_evidence means captured timing/evidence contracts were internally inconsistent.", "Unexpected production analysis failures propagate through the normal central MCP wrapper and are not converted into profiler guesses."],
-  "usage_notes": ["Use this tool to identify which analysis stages dominate and why, not to establish clean-machine absolute benchmark time. The response explicitly marks absolute_wall_authoritative=false because caller/runtime load can inflate wall duration.", "One run is normally sufficient for architectural diagnosis. Repeat only when confirming a specific optimization or investigating unstable evidence.", "Do not add aggregate source_parse_sum_ms, cache_get_sum_ms, or lineage_extract_sum_ms to critical-path stage durations; those values are aggregate file-task diagnostics and may exceed wall time under parallel execution.", "stage_attribution returns component timings, component_sum_ms, residual_ms, coverage_pct, and dominant_component for identity_and_setup, reports, canonical_materialization, and live_publish.", "residual_ms is the critical-path portion of a stage not covered by named components and must not be heuristically allocated."] ,
-  "examples": ["Call contextor_profile_analysis(repo_path=\"C:\\\\Temp\\\\Contextor_Repo\") and inspect bottlenecks first. Evidence-backed reason_code examples include artifact_pipeline_cost, lineage_reuse_gate_cost, live_publish_ipc_cost, and repository_identity_cost."]
+  "usage_notes": ["Use this tool to identify which analysis stages dominate and why, not to establish clean-machine absolute benchmark time. The response explicitly marks absolute_wall_authoritative=false because caller/runtime load can inflate wall duration.", "One run is normally sufficient for architectural diagnosis. Repeat only when confirming a specific optimization or investigating unstable evidence.", "Do not add aggregate source_parse_sum_ms, cache_get_sum_ms, or lineage_extract_sum_ms to critical-path stage durations; those values are aggregate file-task diagnostics and may exceed wall time under parallel execution.", "stage_attribution returns component timings, component_sum_ms, residual_ms, coverage_pct, and dominant_component for identity_and_setup, reports, canonical_materialization, persistence, and live_publish.", "residual_ms is the critical-path portion of a stage not covered by named components and must not be heuristically allocated."],
+  "examples": ["Call contextor_profile_analysis(repo_path=\"C:\\\\Temp\\\\Contextor_Repo\") and inspect bottlenecks first. Evidence-backed reason_code examples include artifact_pipeline_cost, lineage_reuse_gate_cost, live_publish_ipc_cost, repository_identity_cost, and snapshot_save_cost."]
 }
diff --git a/tests/test_profile_analysis.py b/tests/test_profile_analysis.py
index 265b86c..7fb45ff 100644
--- a/tests/test_profile_analysis.py
+++ b/tests/test_profile_analysis.py
@@ -142,6 +142,11 @@ def _profile_events(operation_id: str = "profile-test"):
             "shared_usage_clusters": 0.5,
             "publish_preparation": 0.5,
         },
+        "persistence": {
+            "metadata_and_revision": 2.0,
+            "file_state_payload": 3.0,
+            "snapshot_save": 34.0,
+        },
         "live_publish": {
             "connect": 5.0,
             "publish": 25.0,
@@ -158,7 +163,15 @@ def _profile_events(operation_id: str = "profile-test"):
                 "component": component,
                 "elapsed_ms": elapsed_ms,
                 "timing_semantics": "critical_path_stage_component",
-                **({"status": "success"} if stage == "live_publish" else {}),
+                **(
+                    {"status": "success"}
+                    if stage == "live_publish"
+                    or (
+                        stage == "persistence"
+                        and component == "snapshot_save"
+                    )
+                    else {}
+                ),
             }
             for component, elapsed_ms in components.items()
         )
@@ -236,6 +249,16 @@ def test_profile_ranks_only_critical_path_and_attributes_known_causes():
     assert live_attribution["publish_ms"] == 25.0
     assert live_attribution["stage_status"] == "success"
 
+    persistence = profile["stage_attribution"]["persistence"]
+    assert persistence["reason_code"] == "snapshot_save_cost"
+    assert persistence["metadata_and_revision_ms"] == 2.0
+    assert persistence["file_state_payload_ms"] == 3.0
+    assert persistence["snapshot_save_ms"] == 34.0
+    assert persistence["component_sum_ms"] == 39.0
+    assert persistence["residual_ms"] == 1.0
+    assert persistence["dominant_component"] == "snapshot_save"
+    assert persistence["stage_status"] == "success"
+
     aggregate = profile["aggregate_worker_diagnostics"]
     assert aggregate["timing_semantics"] == (
         "aggregate_file_task_not_critical_path"
@@ -314,6 +337,25 @@ def test_profile_fails_closed_when_stage_component_evidence_is_missing():
     ]
 
 
+def test_profile_fails_closed_when_persistence_component_evidence_is_missing():
+    events = [
+        event
+        for event in _profile_events()
+        if not (
+            event["ev"] == "FULL_ANALYSIS_STAGE_COMPONENT_END"
+            and event["stage"] == "persistence"
+            and event["component"] == "snapshot_save"
+        )
+    ]
+
+    profile = build_analysis_profile(events, operation_id="profile-test")
+
+    assert profile["status"] == "incomplete"
+    assert profile["missing"] == [
+        "FULL_ANALYSIS_STAGE_COMPONENT_END:persistence:snapshot_save"
+    ]
+
+
 def test_profile_rejects_invalid_stage_component_timing_semantics():
     events = _profile_events()
     component = next(

```

FILES_CHANGED=NONE
DIFFS=NONE

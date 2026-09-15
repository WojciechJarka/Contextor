## CPA10K0G_AUTHORITY_RECOVERY_SHARED_TRACE_FALSE_POSITIVE_FIX

STATUS=IMPLEMENTATION_PASS_RUNTIME_CERTIFICATION_PENDING
TASK=CPA10K0G_AUTHORITY_RECOVERY_SHARED_TRACE_FALSE_POSITIVE_FIX
MODE=IMPLEMENT
REPO=C:\Temp\Contextor_Repo
HEAD=cecc4c543078dd6cbc31d2394da3a13ffd030328
PRE_EXISTING_WORKTREE=walkthrough.md was modified before this task by the preceding recovery investigation; it was replaced with this task report as required. Production and test files were unmodified before implementation.
SCOPE=Only contextor/core/runtime_trace.py and tests/test_runtime_authority_events.py were edited for this task. No project documentation matched the internal recovery-window terminology.

## DISCOVERY_AND_SOURCE_DRIFT

CONTEXTOR_DOCUMENTATION=READ; current MCP documentation was read before using get_file_edit_context, get_symbol_implementation, get_symbol_lineage, get_symbol_call_context, get_source_range, search_source and get_live_events.
CONTEXTOR_INITIAL_REVISION=1227
CONTEXTOR_INITIAL_FILE_CONTEXT=PASS; get_file_edit_context(contextor/core/runtime_trace.py, mode=minimal) resolved module_id=85/1, layer=adapter, risk_score=0.1536, direct_consumers=22, transitive_consumers=176, tests_covering=120, workspace/syntax diagnostics fresh and checked_and_none.
CONTEXTOR_TEST_CONTEXT=PASS; get_file_edit_context(tests/test_runtime_authority_events.py, mode=minimal) resolved module_id=347/2, layer=tests, syntax diagnostics fresh and checked_and_none.
SOURCE_DRIFT=PASS; local HEAD and current source matched the task's described implementation before editing. The exact function was contextor/core/runtime_trace.py:746-798 and contained the raw end-start rejection, whole-range stream.read, and reassignment of start/end for record offsets.
EXISTING_AUTHORITY_BOUND_TEST=PASS; Contextor search_source located tests/test_runtime_authority_events.py:313-323, which already asserted that a genuinely unindexed authority event over the configured bound fails closed.
DOCUMENT_REVIEW=PASS; search excluding walkthrough.md returned NO_PROJECT_DOC_MATCHES for _AUTHORITY_RECOVERY_WINDOW, raw trace-byte bound and equivalent terminology. No project documentation change was needed.

## CONTEXTOR_OWNER_AND_LINEAGE_EVIDENCE

CANONICAL_OWNER=Contextor MCP get_symbol_implementation resolved contextor.core.runtime_trace::AuthorityEventEmitter._recover_unindexed_range_locked as method, artifact_id=A3795/1, exact implementation lines 746-798 before edit.
CALL_CONTEXT=Contextor MCP get_symbol_call_context, canonical revision=1227, scope=intra_module, total_edges=4. Callers: AuthorityEventEmitter._recover_locked -> _recover_unindexed_range_locked at lines 734 and 740. Callees: AuthorityEvent.from_dict at line 773 and _authority_default_domain at line 774. No alternate owner or recovery path was introduced.
LINEAGE=Contextor MCP get_symbol_lineage resolved artifact A3795/1 with scope_state=available, metadata_consistent=true, lineage family=fresh, semantic_anchor_bindings_complete=true and explicit_named representation. The complete auto candidate was previewed because it was 149618 bytes; no lineage fallback or source reconstruction was used.
DIRECT_CONSUMERS_AND_TESTS=The file-edit context reported 22 direct consumers, 176 transitive consumers and 120 covering test modules. The requested focused test file is the direct regression owner for authority-event recovery behavior.

## IMPLEMENTATION

OWNER_EDITED=AuthorityEventEmitter._recover_unindexed_range_locked only.
CONTRACT_VERIFICATION=
1. Removed the pre-parse rejection based on raw end-start distance.
2. Replaced whole-tail stream.read/chunk.splitlines with incremental stream.readline(end - tail), bounded by the supplied snapshot end.
3. Every JSONL line in [start,end) is still checked for a complete newline, decoded and parsed; malformed, non-object and truncated records still raise AuthorityEventRecoveryError.
4. Non-authority records are skipped before budget accounting and contribute zero bytes.
5. Complete _type=authority_event records add len(line), the exact UTF-8 JSONL byte length including its newline, to authority_recovery_bytes.
6. Cumulative authority-event bytes over _AUTHORITY_RECOVERY_WINDOW raise AuthorityEventRecoveryError with authority-event-specific error text.
7. Existing schema, AuthorityEvent.from_dict, per-domain sequence, pending-index, delivery-conflict and sidecar update logic was preserved.
8. RecordIndex and high-water offsets use explicit record_start/record_end; the snapshot end variable is never reused for individual record offsets.
9. The final payload still sets durable_tail_offset=end and preserves domains.
10. Added a concise comment defining _AUTHORITY_RECOVERY_WINDOW as cumulative unindexed authority-event bytes, not shared runtime-trace bytes.

TEST_REGRESSIONS=
- Added rollover regression: one authority event, durable-tail capture, _AUTHORITY_RECOVERY_WINDOW=64, twenty normal trace_event diagnostic records with 128-byte reasons, unchanged sidecar tail, session rollover, successful new-emitter recovery, next sequence=previous+1, and intact diagnostic history in the old segment.
- Added same-segment regression with the same diagnostic-noise pressure and successful recovery by a second emitter on the active segment.
- Existing over-bound authority-event recovery test remains unchanged and continues to fail closed.
- Existing malformed/truncated-tail, crash-after-JSONL-before-sidecar, missing-segment, pending-index and identity/sequence tests remain in the focused suite.

## VALIDATION

FOCUSED_COMMAND=& .\\.venv\\Scripts\\python.exe -m py_compile contextor/core/runtime_trace.py tests/test_runtime_authority_events.py ; & .\\.venv\\Scripts\\python.exe -m pytest tests/test_runtime_authority_events.py -q
FOCUSED_RESULT=PASS; 40 passed in 26.07s
DIFF_CHECK=PASS; git diff --check returned no whitespace errors. Git emitted only the repository's existing LF-to-CRLF normalization warnings.
FULL_PYTEST=NOT_RUN; explicitly prohibited by task.
PRODUCTION_RECOVERY_EXPERIMENT=NOT_RUN; production logs were not mutated.

## POST_EDIT_CONTEXTOR_EVIDENCE

LIVE_EVENTS=PASS; get_live_events(after_revision=1227) reported continuous retention with resync_required=false and desktop_watcher UPDATED events at revision 1228 for contextor/core/runtime_trace.py and revision 1229 for tests/test_runtime_authority_events.py. Diagnostics summary was fresh with zero syntax errors, collisions and cycles.
LIVE_EVENTS_FOLLOWUP=PASS; get_live_events(after_revision=1229) reported revision 1230, continuous retention, resync_required=false and desktop_watcher update_file UNCHANGED for contextor/core/runtime_trace.py. This confirms no additional source mutation after the focused validation.
POST_EDIT_FILE_CONTEXT=PASS; get_file_edit_context returned live_revision=1230, syntax checked_and_none, fresh diagnostics and no warnings for contextor/core/runtime_trace.py.
POST_EDIT_IMPLEMENTATION=PASS; get_symbol_implementation returned the complete AST-bounded method at lines 746-804, canonical_revision=1230, workspace_sync=verified, canonical_state=fresh and advisory_warning=null.
RUNTIME_CERTIFICATION=DEFERRED; this implementation step did not restart Desktop or the MCP server and did not run production recovery. Synthetic focused tests are the implementation certification.
DESKTOP_RESTART_REQUIRED=YES; source module changed and an already-running Desktop process must be restarted before production runtime certification.
MCP_SERVER_RESTART_REQUIRED=YES; server/runtime source changed and an already-running MCP server must be restarted before production runtime certification.

FILES_CHANGED=
- contextor/core/runtime_trace.py
- tests/test_runtime_authority_events.py

ACTUAL_DIFF=FULL_DIFFS_BELOW; walkthrough.md is the report channel and is excluded from its own diff.

### FULL_DIFF: contextor/core/runtime_trace.py

```diff
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 8fd5a2b..bde50c7 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -748,50 +748,56 @@ class AuthorityEventEmitter:
             raise AuthorityEventRecoveryError("authority trace shrank below durable tail offset")
         if end == start:
             return payload
-        if end - start > _AUTHORITY_RECOVERY_WINDOW:
-            raise AuthorityEventRecoveryError("observability_recovery_required: unindexed trace range exceeds bound")
-        with path.open("rb") as stream:
-            stream.seek(start)
-            chunk = stream.read(end - start)
-        if not chunk.endswith(b"\\n"):
-            raise AuthorityEventRecoveryError("observability_recovery_required: truncated unindexed trace range")
         domains = dict(payload["domains"])
         tail = start
-        for line in chunk.splitlines(keepends=True):
-            start, end = tail, tail + len(line)
-            tail = end
-            try:
-                raw = json.loads(line.decode("utf-8"))
-            except (UnicodeDecodeError, ValueError, TypeError) as exc:
-                raise AuthorityEventRecoveryError("observability_recovery_required: malformed trace record") from exc
-            if not isinstance(raw, dict):
-                raise AuthorityEventRecoveryError("observability_recovery_required: trace record is not an object")
-            if raw.get("_type") != "authority_event":
-                continue
-            if raw.get("schema") != AUTHORITY_EVENT_SCHEMA:
-                raise AuthorityEventRecoveryError("observability_recovery_required: authority schema mismatch")
-            event = AuthorityEvent.from_dict({key: raw.get(key) for key in AuthorityEvent.__dataclass_fields__})
-            domain = dict(domains.get(event.runtime_domain_id) or _authority_default_domain(event.runtime_domain_id))
-            expected = int(domain["durable_high_water_sequence"]) + 1
-            if event.sequence != expected:
-                raise AuthorityEventRecoveryError("observability_recovery_required: authority sequence discontinuity")
-            index = RecordIndex(event.sequence, event.event_id, str(path.resolve()), start, end)
-            domain.update(durable_high_water_sequence=event.sequence, durable_high_water_event_id=event.event_id, durable_high_water_trace_path=str(path.resolve()), durable_high_water_offset=start, durable_high_water_end_offset=end)
-            pending = list(domain["pending_index"])
-            if len(pending) >= _AUTHORITY_PENDING_LIMIT:
-                raise AuthorityEventRecoveryError("observability_recovery_required: pending index retention exceeded")
-            pending.append(index.__dict__)
-            domain["pending_index"] = pending
-            if domain["pending_start_sequence"] is None:
-                domain["pending_start_sequence"] = int(domain["live_handoff_cursor"]) + 1
-            domain["pending_end_sequence"] = event.sequence
-            if event.event_type == "AUTHORITY_EVENT_DELIVERY_CONFLICT":
-                if event.request_type != "authority_delivery_conflict" or not isinstance(event.operation_id, str) or not event.operation_id or isinstance(event.queue_order, bool) or not isinstance(event.queue_order, int) or event.queue_order < 1:
-                    raise AuthorityEventRecoveryError("authority delivery conflict lacks exact machine identity")
-                marker = {"runtime_domain_id": event.runtime_domain_id, "sequence": event.queue_order, "event_id": event.operation_id}
-                if marker not in domain["delivery_conflicts"]:
-                    domain["delivery_conflicts"] = list(domain["delivery_conflicts"]) + [marker]
-            domains[event.runtime_domain_id] = domain
+        authority_recovery_bytes = 0
+        # The recovery window bounds cumulative unindexed authority-event bytes, not the shared runtime trace.
+        with path.open("rb") as stream:
+            stream.seek(start)
+            while tail < end:
+                record_start = tail
+                line = stream.readline(end - tail)
+                if not line:
+                    raise AuthorityEventRecoveryError("observability_recovery_required: truncated unindexed trace range")
+                record_end = record_start + len(line)
+                tail = record_end
+                if not line.endswith(b"\\n"):
+                    raise AuthorityEventRecoveryError("observability_recovery_required: truncated unindexed trace range")
+                try:
+                    raw = json.loads(line.decode("utf-8"))
+                except (UnicodeDecodeError, ValueError, TypeError) as exc:
+                    raise AuthorityEventRecoveryError("observability_recovery_required: malformed trace record") from exc
+                if not isinstance(raw, dict):
+                    raise AuthorityEventRecoveryError("observability_recovery_required: trace record is not an object")
+                if raw.get("_type") != "authority_event":
+                    continue
+                authority_recovery_bytes += len(line)
+                if authority_recovery_bytes > _AUTHORITY_RECOVERY_WINDOW:
+                    raise AuthorityEventRecoveryError("observability_recovery_required: authority event recovery exceeds bound")
+                if raw.get("schema") != AUTHORITY_EVENT_SCHEMA:
+                    raise AuthorityEventRecoveryError("observability_recovery_required: authority schema mismatch")
+                event = AuthorityEvent.from_dict({key: raw.get(key) for key in AuthorityEvent.__dataclass_fields__})
+                domain = dict(domains.get(event.runtime_domain_id) or _authority_default_domain(event.runtime_domain_id))
+                expected = int(domain["durable_high_water_sequence"]) + 1
+                if event.sequence != expected:
+                    raise AuthorityEventRecoveryError("observability_recovery_required: authority sequence discontinuity")
+                index = RecordIndex(event.sequence, event.event_id, str(path.resolve()), record_start, record_end)
+                domain.update(durable_high_water_sequence=event.sequence, durable_high_water_event_id=event.event_id, durable_high_water_trace_path=str(path.resolve()), durable_high_water_offset=record_start, durable_high_water_end_offset=record_end)
+                pending = list(domain["pending_index"])
+                if len(pending) >= _AUTHORITY_PENDING_LIMIT:
+                    raise AuthorityEventRecoveryError("observability_recovery_required: pending index retention exceeded")
+                pending.append(index.__dict__)
+                domain["pending_index"] = pending
+                if domain["pending_start_sequence"] is None:
+                    domain["pending_start_sequence"] = int(domain["live_handoff_cursor"]) + 1
+                domain["pending_end_sequence"] = event.sequence
+                if event.event_type == "AUTHORITY_EVENT_DELIVERY_CONFLICT":
+                    if event.request_type != "authority_delivery_conflict" or not isinstance(event.operation_id, str) or not event.operation_id or isinstance(event.queue_order, bool) or not isinstance(event.queue_order, int) or event.queue_order < 1:
+                        raise AuthorityEventRecoveryError("authority delivery conflict lacks exact machine identity")
+                    marker = {"runtime_domain_id": event.runtime_domain_id, "sequence": event.queue_order, "event_id": event.operation_id}
+                    if marker not in domain["delivery_conflicts"]:
+                        domain["delivery_conflicts"] = list(domain["delivery_conflicts"]) + [marker]
+                domains[event.runtime_domain_id] = domain
         payload = dict(payload)
         payload["durable_tail_offset"] = end
         payload["domains"] = domains
```

### FULL_DIFF: tests/test_runtime_authority_events.py

```diff
diff --git a/tests/test_runtime_authority_events.py b/tests/test_runtime_authority_events.py
index 52b21cb..328b3fc 100644
--- a/tests/test_runtime_authority_events.py
+++ b/tests/test_runtime_authority_events.py
@@ -192,6 +192,43 @@ def test_pending_event_from_previous_trace_segment_replays_after_rollover(trace_
     assert delivered[0]["timestamp"] == event.timestamp and old_path.exists()


+def test_diagnostic_noise_does_not_block_authority_recovery_after_rollover(trace_logs, monkeypatch):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    first = emitter.emit("FIRST")
+    old_path = emitter.log_path
+    durable_tail = _state(trace_logs)["durable_tail_offset"]
+    monkeypatch.setattr(trace, "_AUTHORITY_RECOVERY_WINDOW", 64)
+
+    for index in range(20):
+        trace.trace_event("DIAGNOSTIC", f"NOISE_{index}", reason="x" * 128)
+
+    assert _state(trace_logs)["durable_tail_offset"] == durable_tail
+    trace.finish_desktop_trace_session()
+    recovered = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+
+    assert recovered.log_path != old_path
+    assert recovered.emit("AFTER_RECOVERY").sequence == first.sequence + 1
+    diagnostics = [json.loads(line) for line in old_path.read_text(encoding="utf-8").splitlines() if json.loads(line).get("d") == "DIAGNOSTIC"]
+    assert [record["ev"] for record in diagnostics] == [f"NOISE_{index}" for index in range(20)]
+
+
+def test_diagnostic_noise_does_not_block_same_segment_authority_recovery(trace_logs, monkeypatch):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.emit("FIRST")
+    active_path = emitter.log_path
+    durable_tail = _state(trace_logs)["durable_tail_offset"]
+    monkeypatch.setattr(trace, "_AUTHORITY_RECOVERY_WINDOW", 64)
+
+    for index in range(20):
+        trace.trace_event("DIAGNOSTIC", f"NOISE_{index}", reason="x" * 128)
+
+    assert _state(trace_logs)["durable_tail_offset"] == durable_tail
+    recovered = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+
+    assert recovered.log_path == active_path
+    assert recovered.emit("AFTER_RECOVERY").sequence == 2
+
+
 def test_missing_old_pending_segment_fails_closed(trace_logs):
     first = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
     first.emit("PENDING")
```

NEXT_STEP=Wait for the user's `proceduj` command before any post-restart runtime certification. Do not manually restart Desktop or MCP.

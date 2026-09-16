# CPA10K4B_RUNTIME_TRACE_SAFE_DIAGNOSTIC_TAIL_RECOVERY

MODE=IMPLEMENT_EXACT_AUDITOR_DESIGN
REPO=C:\\Temp\\Contextor_Repo
SCOPE=current-task-only
IMPLEMENTATION_RESULT=PASS
PREVIOUS_STAGE=CPA10K4A2_WRITER_PASS_CLOSED
FULL_ANALYSIS=NOT_RUN
LIVE_MCP_RESTART=NOT_PERFORMED
UPDATE_FILE=NOT_USED
PROCESS_LIFECYCLE=NOT_CHANGED
PROCESS_LEAK_WORK=NOT_STARTED

## EXACT_ANCHORS_VERIFIED

Before edit, Contextor verified the current recovery and both physical writers at canonical revision 1278 with `workspace_sync=verified` and fresh syntax/collision/cycle diagnostics.

After edit, Contextor verified:

- `AuthorityEventEmitter._recover_unindexed_range_locked`: `get_symbol_implementation` status `resolved`, `workspace_sync=verified`, canonical revision 1280, lines 861-1127.
- `_append`: status `resolved`, `workspace_sync=verified`, canonical revision 1280, lines 1450-1515.
- `_append_authority_record_locked`: status `resolved`, `workspace_sync=verified`, canonical revision 1280, lines 550-631.
- Source ranges for the canonical constants/thread lock and `_TraceAppendFileLock` returned status `ok` with fresh diagnostics.
- Contextor reported no syntax errors, name collisions, cycles, or diagnostic attention.

## FILES_CHANGED

- `contextor/core/runtime_trace.py`
- `tests/test_runtime_authority_events.py`
- `walkthrough.md` report artifact only and excluded from production/test diff accounting

No writer, capture, session/pointer, process-lifecycle, or `tests/test_runtime_trace.py` changes were made in this step.

## RECOVERY_LOCK_ORDER

The exact recovery lock order is:

`existing process-local authority lock -> _AuthorityFileLock -> _trace_append_thread_lock -> _TraceAppendFileLock`

The replacement recovery method obtains `_trace_append_thread_lock` and then `_TraceAppendFileLock(_trace_append_lock_path(path))`. It obtains the locked physical file size, scans, and performs the optional final-tail truncate/fsync while the same extent lock is held.

No lock class was changed. No file-lock reentrancy was added. No append lock was moved to another layer.

## SAFE_REPAIR_BOUNDARY

The only repair path is:

- the scanned line is the final unterminated tail;
- its raw bytes begin exactly with `_DIAGNOSTIC_RECORD_PREFIX`;
- the stream is truncated at that record start;
- the stream is flushed and fsynced;
- recovery continues with the corrected `locked_end`.

The canonical prefix is exactly:

`_DIAGNOSTIC_RECORD_PREFIX = b'{"_record_kind":"diagnostic_event",'`

No prefix is reconstructed heuristically in recovery.

A complete LF-terminated line is always decoded and JSON-parsed before any authority/non-authority filtering. A malformed LF-terminated line therefore remains fatal even if it starts with the diagnostic prefix.

An unterminated tail without the exact diagnostic prefix remains fatal. No malformed-diagnostic `continue` path exists.

## FAIL_CLOSED_EVIDENCE

The preserved recovery behavior and new tests cover:

- unknown/truncated tail without the typed prefix: fails closed via `test_malformed_or_truncated_unindexed_tail_fails_closed`;
- complete LF-terminated typed diagnostic malformed JSON: fails closed with `malformed trace record`;
- complete malformed authority record: fails closed with `malformed trace record`;
- complete legacy unframed malformed record: fails closed with `malformed trace record`;
- valid authority event processing, schema/sequence/pending/conflict semantics, and existing diagnostic-noise recovery tests remain passing.

## LARGE_DIAGNOSTIC_EVIDENCE

`test_large_valid_diagnostic_range_does_not_hit_authority_recovery_bound` writes a valid diagnostic JSONL record larger than `_AUTHORITY_RECOVERY_WINDOW` and verifies that the next authority event recovers with the next sequence. The recovery byte bound remains applied only to authority records because the diagnostic record is valid JSON and has `_type != "authority_event"`.

## WRITER_UNCHANGED_EVIDENCE

The post-edit Contextor implementations of `_append` and `_append_authority_record_locked` match the closed CPA10K4A2 writer contract exactly:

- process-local writer serialization remains in both writers;
- `_append` still does not use `_AuthorityFileLock`;
- authority physical append still uses `_TraceAppendFileLock`;
- diagnostic timeout, prefix construction, `_active_fd` removal, `_rollback_append`, and both lock classes are unchanged.

The only production changes in this step are the canonical prefix constant and the exact recovery-method replacement.

## PY_COMPILE

Command:

`& .\\.venv\\Scripts\\python.exe -m py_compile contextor/core/runtime_trace.py`

Result: PASS

## TESTS

Authority test file:

`& .\\.venv\\Scripts\\python.exe -m pytest tests/test_runtime_authority_events.py -q`

Result: `45 passed in 15.26s`

Writer regression anchors:

`& .\\.venv\\Scripts\\python.exe -m pytest tests/test_runtime_trace.py::test_scoped_trace_capture_matches_durable_record tests/test_runtime_trace.py::test_multiprocess_append_is_valid_json -q`

Result: `2 passed in 3.93s`

No broad/full pytest suite was run.

## CERTIFICATION

FINAL_TYPED_DIAGNOSTIC_TAIL_REPAIRED=YES
COMPLETE_MALFORMED_TYPED_DIAGNOSTIC_FAILS_CLOSED=YES
MALFORMED_AUTHORITY_FAILS_CLOSED=YES
LEGACY_MALFORMED_RECORD_FAILS_CLOSED=YES
UNKNOWN_TRUNCATED_TAIL_FAILS_CLOSED=YES
RECOVERY_FILE_EXTENT_SERIALIZED=YES
SHARED_TRACE_OVER_1M_DIAGNOSTIC_RECOVERS=YES
WRITER_CONTRACT_UNCHANGED=YES
PY_COMPILE=PASS
FOCUSED_TESTS=PASS

## COMPLETE_DIFFS

The following is the complete current worktree diff for every production/test file in this task. `walkthrough.md` is excluded.

diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 34dd692..4f8dafd 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -34,6 +34,9 @@ _counter = 0
 _AUTHORITY_STATE_NAME = "authority_event_state.json"
 _TRACE_APPEND_LOCK_NAME = ".contextor_runtime_trace.append.lock"
 _DIAGNOSTIC_RECORD_KIND = "diagnostic_event"
+_DIAGNOSTIC_RECORD_PREFIX = (
+    b'{"_record_kind":"diagnostic_event",'
+)
 _DIAGNOSTIC_APPEND_LOCK_TIMEOUT = 0.25
 _AUTHORITY_RECOVERY_WINDOW = 1024 * 1024
 _AUTHORITY_APPEND_LOCATE_WINDOW = 1024 * 1024
@@ -855,65 +858,273 @@ class AuthorityEventEmitter:
             _write_authority_sidecar(self.sidecar_path, self.runtime_domain_id, state, payload)
         return state, payload
 
-    def _recover_unindexed_range_locked(self, path: Path, start: int, end: int, payload: dict[str, object]) -> dict[str, object]:
+    def _recover_unindexed_range_locked(
+        self,
+        path: Path,
+        start: int,
+        end: int,
+        payload: dict[str, object],
+    ) -> dict[str, object]:
         if end < start:
-            raise AuthorityEventRecoveryError("authority trace shrank below durable tail offset")
-        if end == start:
-            return payload
-        domains = dict(payload["domains"])
-        tail = start
-        authority_recovery_bytes = 0
-        # The recovery window bounds cumulative unindexed authority-event bytes, not the shared runtime trace.
-        with path.open("rb") as stream:
-            stream.seek(start)
-            while tail < end:
-                record_start = tail
-                line = stream.readline(end - tail)
-                if not line:
-                    raise AuthorityEventRecoveryError("observability_recovery_required: truncated unindexed trace range")
-                record_end = record_start + len(line)
-                tail = record_end
-                if not line.endswith(b"\n"):
-                    raise AuthorityEventRecoveryError("observability_recovery_required: truncated unindexed trace range")
+            raise AuthorityEventRecoveryError(
+                "authority trace shrank below durable tail offset"
+            )
+
+        with _trace_append_thread_lock:
+            with _TraceAppendFileLock(
+                _trace_append_lock_path(path)
+            ):
                 try:
-                    raw = json.loads(line.decode("utf-8"))
-                except (UnicodeDecodeError, ValueError, TypeError) as exc:
-                    raise AuthorityEventRecoveryError("observability_recovery_required: malformed trace record") from exc
-                if not isinstance(raw, dict):
-                    raise AuthorityEventRecoveryError("observability_recovery_required: trace record is not an object")
-                if raw.get("_type") != "authority_event":
-                    continue
-                authority_recovery_bytes += len(line)
-                if authority_recovery_bytes > _AUTHORITY_RECOVERY_WINDOW:
-                    raise AuthorityEventRecoveryError("observability_recovery_required: authority event recovery exceeds bound")
-                if raw.get("schema") != AUTHORITY_EVENT_SCHEMA:
-                    raise AuthorityEventRecoveryError("observability_recovery_required: authority schema mismatch")
-                event = AuthorityEvent.from_dict({key: raw.get(key) for key in AuthorityEvent.__dataclass_fields__})
-                domain = dict(domains.get(event.runtime_domain_id) or _authority_default_domain(event.runtime_domain_id))
-                expected = int(domain["durable_high_water_sequence"]) + 1
-                if event.sequence != expected:
-                    raise AuthorityEventRecoveryError("observability_recovery_required: authority sequence discontinuity")
-                index = RecordIndex(event.sequence, event.event_id, str(path.resolve()), record_start, record_end)
-                domain.update(durable_high_water_sequence=event.sequence, durable_high_water_event_id=event.event_id, durable_high_water_trace_path=str(path.resolve()), durable_high_water_offset=record_start, durable_high_water_end_offset=record_end)
-                pending = list(domain["pending_index"])
-                if len(pending) >= _AUTHORITY_PENDING_LIMIT:
-                    raise AuthorityEventRecoveryError("observability_recovery_required: pending index retention exceeded")
-                pending.append(index.__dict__)
-                domain["pending_index"] = pending
-                if domain["pending_start_sequence"] is None:
-                    domain["pending_start_sequence"] = int(domain["live_handoff_cursor"]) + 1
-                domain["pending_end_sequence"] = event.sequence
-                if event.event_type == "AUTHORITY_EVENT_DELIVERY_CONFLICT":
-                    if event.request_type != "authority_delivery_conflict" or not isinstance(event.operation_id, str) or not event.operation_id or isinstance(event.queue_order, bool) or not isinstance(event.queue_order, int) or event.queue_order < 1:
-                        raise AuthorityEventRecoveryError("authority delivery conflict lacks exact machine identity")
-                    marker = {"runtime_domain_id": event.runtime_domain_id, "sequence": event.queue_order, "event_id": event.operation_id}
-                    if marker not in domain["delivery_conflicts"]:
-                        domain["delivery_conflicts"] = list(domain["delivery_conflicts"]) + [marker]
-                domains[event.runtime_domain_id] = domain
-        payload = dict(payload)
-        payload["durable_tail_offset"] = end
-        payload["domains"] = domains
-        return payload
+                    locked_end = path.stat().st_size
+                except FileNotFoundError as exc:
+                    raise AuthorityEventRecoveryError(
+                        "observability_recovery_required: "
+                        "authority trace segment is missing"
+                    ) from exc
+
+                if locked_end < start:
+                    raise AuthorityEventRecoveryError(
+                        "authority trace shrank below durable tail offset"
+                    )
+                if locked_end == start:
+                    return payload
+
+                domains = dict(payload["domains"])
+                tail = start
+                authority_recovery_bytes = 0
+
+                with path.open("r+b") as stream:
+                    stream.seek(start)
+
+                    while tail < locked_end:
+                        record_start = tail
+                        line = stream.readline(
+                            locked_end - tail
+                        )
+
+                        if not line:
+                            raise AuthorityEventRecoveryError(
+                                "observability_recovery_required: "
+                                "truncated unindexed trace range"
+                            )
+
+                        record_end = record_start + len(line)
+                        tail = record_end
+
+                        if not line.endswith(b"\n"):
+                            if line.startswith(
+                                _DIAGNOSTIC_RECORD_PREFIX
+                            ):
+                                stream.seek(record_start)
+                                stream.truncate()
+                                stream.flush()
+                                os.fsync(stream.fileno())
+                                locked_end = record_start
+                                tail = record_start
+                                break
+
+                            raise AuthorityEventRecoveryError(
+                                "observability_recovery_required: "
+                                "truncated unindexed trace range"
+                            )
+
+                        try:
+                            raw = json.loads(
+                                line.decode("utf-8")
+                            )
+                        except (
+                            UnicodeDecodeError,
+                            ValueError,
+                            TypeError,
+                        ) as exc:
+                            raise AuthorityEventRecoveryError(
+                                "observability_recovery_required: "
+                                "malformed trace record"
+                            ) from exc
+
+                        if not isinstance(raw, dict):
+                            raise AuthorityEventRecoveryError(
+                                "observability_recovery_required: "
+                                "trace record is not an object"
+                            )
+
+                        if raw.get("_type") != "authority_event":
+                            continue
+
+                        authority_recovery_bytes += len(line)
+                        if (
+                            authority_recovery_bytes
+                            > _AUTHORITY_RECOVERY_WINDOW
+                        ):
+                            raise AuthorityEventRecoveryError(
+                                "observability_recovery_required: "
+                                "authority event recovery exceeds bound"
+                            )
+
+                        if (
+                            raw.get("schema")
+                            != AUTHORITY_EVENT_SCHEMA
+                        ):
+                            raise AuthorityEventRecoveryError(
+                                "observability_recovery_required: "
+                                "authority schema mismatch"
+                            )
+
+                        event = AuthorityEvent.from_dict(
+                            {
+                                key: raw.get(key)
+                                for key
+                                in AuthorityEvent.__dataclass_fields__
+                            }
+                        )
+
+                        domain = dict(
+                            domains.get(
+                                event.runtime_domain_id
+                            )
+                            or _authority_default_domain(
+                                event.runtime_domain_id
+                            )
+                        )
+
+                        expected = (
+                            int(
+                                domain[
+                                    "durable_high_water_sequence"
+                                ]
+                            )
+                            + 1
+                        )
+                        if event.sequence != expected:
+                            raise AuthorityEventRecoveryError(
+                                "observability_recovery_required: "
+                                "authority sequence discontinuity"
+                            )
+
+                        index = RecordIndex(
+                            event.sequence,
+                            event.event_id,
+                            str(path.resolve()),
+                            record_start,
+                            record_end,
+                        )
+
+                        domain.update(
+                            durable_high_water_sequence=(
+                                event.sequence
+                            ),
+                            durable_high_water_event_id=(
+                                event.event_id
+                            ),
+                            durable_high_water_trace_path=(
+                                str(path.resolve())
+                            ),
+                            durable_high_water_offset=(
+                                record_start
+                            ),
+                            durable_high_water_end_offset=(
+                                record_end
+                            ),
+                        )
+
+                        pending = list(
+                            domain["pending_index"]
+                        )
+                        if (
+                            len(pending)
+                            >= _AUTHORITY_PENDING_LIMIT
+                        ):
+                            raise AuthorityEventRecoveryError(
+                                "observability_recovery_required: "
+                                "pending index retention exceeded"
+                            )
+
+                        pending.append(index.__dict__)
+                        domain["pending_index"] = pending
+
+                        if (
+                            domain["pending_start_sequence"]
+                            is None
+                        ):
+                            domain[
+                                "pending_start_sequence"
+                            ] = (
+                                int(
+                                    domain[
+                                        "live_handoff_cursor"
+                                    ]
+                                )
+                                + 1
+                            )
+
+                        domain[
+                            "pending_end_sequence"
+                        ] = event.sequence
+
+                        if (
+                            event.event_type
+                            == "AUTHORITY_EVENT_DELIVERY_CONFLICT"
+                        ):
+                            if (
+                                event.request_type
+                                != "authority_delivery_conflict"
+                                or not isinstance(
+                                    event.operation_id,
+                                    str,
+                                )
+                                or not event.operation_id
+                                or isinstance(
+                                    event.queue_order,
+                                    bool,
+                                )
+                                or not isinstance(
+                                    event.queue_order,
+                                    int,
+                                )
+                                or event.queue_order < 1
+                            ):
+                                raise AuthorityEventRecoveryError(
+                                    "authority delivery conflict "
+                                    "lacks exact machine identity"
+                                )
+
+                            marker = {
+                                "runtime_domain_id": (
+                                    event.runtime_domain_id
+                                ),
+                                "sequence": (
+                                    event.queue_order
+                                ),
+                                "event_id": (
+                                    event.operation_id
+                                ),
+                            }
+
+                            if (
+                                marker
+                                not in domain[
+                                    "delivery_conflicts"
+                                ]
+                            ):
+                                domain[
+                                    "delivery_conflicts"
+                                ] = (
+                                    list(
+                                        domain[
+                                            "delivery_conflicts"
+                                        ]
+                                    )
+                                    + [marker]
+                                )
+
+                        domains[
+                            event.runtime_domain_id
+                        ] = domain
+
+                payload = dict(payload)
+                payload["durable_tail_offset"] = locked_end
+                payload["domains"] = domains
+                return payload
 
     def _event_from_record(self, record: Mapping[str, object]) -> AuthorityEvent:
         event_id = uuid.uuid4().hex
diff --git a/tests/test_runtime_authority_events.py b/tests/test_runtime_authority_events.py
index 328b3fc..b8820b6 100644
--- a/tests/test_runtime_authority_events.py
+++ b/tests/test_runtime_authority_events.py
@@ -135,6 +135,153 @@ def test_malformed_or_truncated_unindexed_tail_fails_closed(trace_logs):
         trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
 
 
+def test_truncated_typed_diagnostic_tail_is_repaired(trace_logs):
+    emitter = trace.AuthorityEventEmitter(
+        runtime_domain_id="domain-a",
+        logs_root=trace_logs,
+    )
+    first = emitter.emit("VALID")
+    path = emitter.log_path
+    before_tail = path.stat().st_size
+
+    with path.open("ab") as stream:
+        stream.write(
+            trace._DIAGNOSTIC_RECORD_PREFIX
+            + b'"ts":"incomplete"'
+        )
+
+    assert path.stat().st_size > before_tail
+
+    recovered = trace.AuthorityEventEmitter(
+        runtime_domain_id="domain-a",
+        logs_root=trace_logs,
+    )
+
+    assert path.stat().st_size == before_tail
+    assert (
+        _state(trace_logs)["durable_tail_offset"]
+        == before_tail
+    )
+    assert (
+        recovered.emit("AFTER_RECOVERY").sequence
+        == first.sequence + 1
+    )
+
+
+def test_complete_malformed_typed_diagnostic_still_fails_closed(
+    trace_logs,
+):
+    emitter = trace.AuthorityEventEmitter(
+        runtime_domain_id="domain-a",
+        logs_root=trace_logs,
+    )
+    emitter.emit("VALID")
+
+    with emitter.log_path.open("ab") as stream:
+        stream.write(
+            trace._DIAGNOSTIC_RECORD_PREFIX
+            + b'"ts":}\n'
+        )
+
+    with pytest.raises(
+        trace.AuthorityEventRecoveryError,
+        match="malformed trace record",
+    ):
+        trace.AuthorityEventEmitter(
+            runtime_domain_id="domain-a",
+            logs_root=trace_logs,
+        )
+
+
+def test_complete_malformed_authority_record_still_fails_closed(
+    trace_logs,
+):
+    emitter = trace.AuthorityEventEmitter(
+        runtime_domain_id="domain-a",
+        logs_root=trace_logs,
+    )
+    emitter.emit("VALID")
+
+    with emitter.log_path.open("ab") as stream:
+        stream.write(
+            b'{"_type":"authority_event","event_id":}\n'
+        )
+
+    with pytest.raises(
+        trace.AuthorityEventRecoveryError,
+        match="malformed trace record",
+    ):
+        trace.AuthorityEventEmitter(
+            runtime_domain_id="domain-a",
+            logs_root=trace_logs,
+        )
+
+
+def test_complete_legacy_unframed_malformed_record_still_fails_closed(
+    trace_logs,
+):
+    emitter = trace.AuthorityEventEmitter(
+        runtime_domain_id="domain-a",
+        logs_root=trace_logs,
+    )
+    emitter.emit("VALID")
+
+    with emitter.log_path.open("ab") as stream:
+        stream.write(
+            b'0022992,"status":"ok","bytes":1239}\n'
+        )
+
+    with pytest.raises(
+        trace.AuthorityEventRecoveryError,
+        match="malformed trace record",
+    ):
+        trace.AuthorityEventEmitter(
+            runtime_domain_id="domain-a",
+            logs_root=trace_logs,
+        )
+
+
+def test_large_valid_diagnostic_range_does_not_hit_authority_recovery_bound(
+    trace_logs,
+):
+    emitter = trace.AuthorityEventEmitter(
+        runtime_domain_id="domain-a",
+        logs_root=trace_logs,
+    )
+    first = emitter.emit("VALID")
+
+    diagnostic = {
+        "_record_kind": "diagnostic_event",
+        "d": "TEST",
+        "ev": "LARGE_DIAGNOSTIC",
+        "payload": "x" * (
+            trace._AUTHORITY_RECOVERY_WINDOW + 256
+        ),
+    }
+    encoded = (
+        json.dumps(
+            diagnostic,
+            separators=(",", ":"),
+        )
+        + "\n"
+    ).encode("utf-8")
+
+    assert len(encoded) > trace._AUTHORITY_RECOVERY_WINDOW
+
+    with emitter.log_path.open("ab") as stream:
+        stream.write(encoded)
+
+    recovered = trace.AuthorityEventEmitter(
+        runtime_domain_id="domain-a",
+        logs_root=trace_logs,
+    )
+
+    assert (
+        recovered.emit("AFTER_LARGE_DIAGNOSTIC").sequence
+        == first.sequence + 1
+    )
+
+
 def test_two_runtime_domains_have_independent_sequences(trace_logs):
     left = trace.AuthorityEventEmitter(runtime_domain_id="domain-left", logs_root=trace_logs)
     right = trace.AuthorityEventEmitter(runtime_domain_id="domain-right", logs_root=trace_logs)

## END_COMPLETE_DIFFS

## MUST_NOT_CHANGE_CONFIRMED

- `_append`, `_append_authority_record_locked`, `_AuthorityFileLock`, `_TraceAppendFileLock`, and `_trace_append_thread_lock` writer semantics.
- Diagnostic append timeout, marker value/order, active-fd removal, session/pointer lifecycle, and capture semantics.
- Process lifecycle, Desktop/LIVE/MCP shutdown, process-leak work, MCP docs, runtime storage, or existing corrupted production logs.
- Recovery redesign beyond the exact prefix-gated final-tail repair.
- Any complete malformed LF-terminated line.

DIFFS=COMPLETE_CURRENT_WORKTREE_DIFF_INCLUDED
STATUS=STOP_AND_WAIT_FOR_PROCEDUJ


TEST_RESULTS=
Targeted: 3 passed in 7.30s.
Requested suite: 209 passed, 1 warning in 149.31s (0:02:29).
PYTEST_EXIT_CODE=0
PYCOMPILE_EXIT_CODE=0
ACTUAL_DIFF=
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 32fb532..1e4f9ec 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -34,6 +34,7 @@ _last_pointer_check = 0.0
 _counter = 0
 _AUTHORITY_STATE_NAME = "authority_event_state.json"
 _AUTHORITY_RECOVERY_WINDOW = 1024 * 1024
+_AUTHORITY_APPEND_LOCATE_WINDOW = 1024 * 1024
 _AUTHORITY_PENDING_LIMIT = 10_000
 _authority_emitters: dict[tuple[str, str], "AuthorityEventEmitter"] = {}
 _authority_lock = threading.RLock()
@@ -190,6 +191,85 @@ def _record_index_from_payload(payload: Mapping[str, object]) -> RecordIndex:
     return RecordIndex(sequence, event_id, trace_path, offset, end_offset)
 
 
+def _validate_authority_domain_state(
+    owner_domain_id: str,
+    raw_state: Mapping[str, object],
+    *,
+    logs_root: Path,
+) -> dict[str, object]:
+    expected_keys = set(_authority_default_domain(owner_domain_id))
+    if set(raw_state) != expected_keys:
+        raise AuthorityEventRecoveryError("authority domain sidecar fields do not match schema")
+
+    state = dict(raw_state)
+    if state.get("runtime_domain_id") != owner_domain_id:
+        raise AuthorityEventRecoveryError("authority domain identity does not match sidecar key")
+
+    high = state.get("durable_high_water_sequence")
+    cursor = state.get("live_handoff_cursor")
+    if (
+        isinstance(high, bool) or not isinstance(high, int) or high < 0
+        or isinstance(cursor, bool) or not isinstance(cursor, int)
+        or cursor < 0 or cursor > high
+    ):
+        raise AuthorityEventRecoveryError("authority high-water/cursor is invalid")
+
+    high_id = state.get("durable_high_water_event_id")
+    high_path = state.get("durable_high_water_trace_path")
+    high_offset = state.get("durable_high_water_offset")
+    high_end = state.get("durable_high_water_end_offset")
+    if high == 0:
+        if any(value is not None for value in (high_id, high_path, high_offset, high_end)):
+            raise AuthorityEventRecoveryError("zero authority high-water has identity")
+    else:
+        index = _record_index_from_payload({"sequence": high, "event_id": high_id, "trace_path": high_path, "offset": high_offset, "end_offset": high_end})
+        event = _read_authority_record_at(_validated_segment_path(index.trace_path, logs_root), index.offset, index.end_offset)
+        if event.runtime_domain_id != owner_domain_id or event.sequence != high or event.event_id != high_id:
+            raise AuthorityEventRecoveryError("authority high-water record does not match sidecar")
+
+    pending_raw = state.get("pending_index")
+    if not isinstance(pending_raw, list) or len(pending_raw) > _AUTHORITY_PENDING_LIMIT:
+        raise AuthorityEventRecoveryError("authority pending index is invalid")
+    pending: list[RecordIndex] = []
+    for raw in pending_raw:
+        if not isinstance(raw, Mapping):
+            raise AuthorityEventRecoveryError("authority pending index entry is invalid")
+        pending.append(_record_index_from_payload(raw))
+
+    start, end = state.get("pending_start_sequence"), state.get("pending_end_sequence")
+    if (start is None) != (end is None):
+        raise AuthorityEventRecoveryError("authority pending range is incomplete")
+    if not pending:
+        if start is not None or end is not None:
+            raise AuthorityEventRecoveryError("authority empty pending index has range")
+    else:
+        expected_sequences = list(range(cursor + 1, high + 1))
+        actual_sequences = [item.sequence for item in pending]
+        if actual_sequences != expected_sequences or start != expected_sequences[0] or end != expected_sequences[-1]:
+            raise AuthorityEventRecoveryError("authority pending index contains a sequence hole")
+        for item in pending:
+            event = _read_authority_record_at(_validated_segment_path(item.trace_path, logs_root), item.offset, item.end_offset)
+            if event.runtime_domain_id != owner_domain_id or event.sequence != item.sequence or event.event_id != item.event_id:
+                raise AuthorityEventRecoveryError("authority pending record does not match sidecar")
+
+    conflicts = state.get("delivery_conflicts")
+    if not isinstance(conflicts, list) or len(conflicts) > _AUTHORITY_PENDING_LIMIT:
+        raise AuthorityEventRecoveryError("authority delivery conflict metadata is invalid")
+    pending_identities = {(owner_domain_id, item.sequence, item.event_id) for item in pending}
+    for marker in conflicts:
+        if not isinstance(marker, Mapping) or set(marker) != {"runtime_domain_id", "sequence", "event_id"}:
+            raise AuthorityEventRecoveryError("authority delivery conflict marker is invalid")
+        marker_domain, marker_sequence, marker_event_id = marker.get("runtime_domain_id"), marker.get("sequence"), marker.get("event_id")
+        if (
+            marker_domain != owner_domain_id or isinstance(marker_sequence, bool)
+            or not isinstance(marker_sequence, int) or marker_sequence < 1
+            or not isinstance(marker_event_id, str) or not marker_event_id
+            or (owner_domain_id, marker_sequence, marker_event_id) not in pending_identities
+        ):
+            raise AuthorityEventRecoveryError("authority delivery conflict marker does not match pending event")
+    return state
+
+
 def _validated_segment_path(value: str, logs_root: Path) -> Path:
     path = Path(value).resolve()
     if path.parent != logs_root.resolve() or path.suffix != ".jsonl":
@@ -216,7 +296,10 @@ def _read_authority_sidecar(path: Path, domain_id: str, logs_root: Path, trace_p
         upgraded["domains"] = payload["domains"]
         for domain in upgraded["domains"].values():
             if isinstance(domain, dict):
-                domain["durable_high_water_trace_path"] = old_path
+                high = domain.get("durable_high_water_sequence")
+                if isinstance(high, bool) or not isinstance(high, int) or high < 0:
+                    raise AuthorityEventRecoveryError("schema2 authority high-water is invalid")
+                domain["durable_high_water_trace_path"] = old_path if high > 0 else None
                 domain["pending_index"] = [dict(item, trace_path=old_path) for item in domain.get("pending_index", []) if isinstance(item, dict)]
                 domain["delivery_conflicts"] = []
         payload = upgraded
@@ -237,55 +320,16 @@ def _read_authority_sidecar(path: Path, domain_id: str, logs_root: Path, trace_p
     domains = payload.get("domains")
     if not isinstance(domains, dict):
         raise AuthorityEventRecoveryError("authority sidecar domains is invalid")
-    state = dict(_authority_default_domain(domain_id))
-    if domain_id in domains:
-        if not isinstance(domains[domain_id], dict) or set(domains[domain_id]) != set(state):
-            raise AuthorityEventRecoveryError("authority domain sidecar fields do not match schema")
-        state.update(domains[domain_id])
-    if state.get("runtime_domain_id") != domain_id:
-        raise AuthorityEventRecoveryError("authority sidecar belongs to another runtime domain")
-    for key in ("durable_high_water_sequence", "live_handoff_cursor"):
-        value = state.get(key)
-        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
-            raise AuthorityEventRecoveryError(f"invalid authority sidecar {key}")
-    high = int(state["durable_high_water_sequence"])
-    cursor = int(state["live_handoff_cursor"])
-    if cursor > high:
-        raise AuthorityEventRecoveryError("authority handoff cursor exceeds high-water")
-    high_id = state.get("durable_high_water_event_id")
-    high_path = state.get("durable_high_water_trace_path")
-    high_offset, high_end = state.get("durable_high_water_offset"), state.get("durable_high_water_end_offset")
-    if high == 0:
-        if any(value is not None for value in (high_id, high_path, high_offset, high_end)):
-            raise AuthorityEventRecoveryError("zero authority high-water has identity")
-    else:
-        if not isinstance(high_path, str) or not high_path:
-            raise AuthorityEventRecoveryError("authority high-water trace path is missing")
-        _record_index_from_payload({"sequence": high, "event_id": high_id, "trace_path": high_path, "offset": high_offset, "end_offset": high_end})
-        high_event = _read_authority_record_at(_validated_segment_path(high_path, logs_root), int(high_offset), int(high_end))
-        if high_event.sequence != high or high_event.event_id != high_id or high_event.runtime_domain_id != domain_id:
-            raise AuthorityEventRecoveryError("authority high-water record does not match sidecar")
-    pending_raw = state.get("pending_index")
-    if not isinstance(pending_raw, list) or len(pending_raw) > _AUTHORITY_PENDING_LIMIT:
-        raise AuthorityEventRecoveryError("authority pending index is invalid")
-    pending = [_record_index_from_payload(item) for item in pending_raw if isinstance(item, Mapping)]
-    start, end = state.get("pending_start_sequence"), state.get("pending_end_sequence")
-    if len(pending) != len(pending_raw) or any(a.sequence >= b.sequence for a, b in zip(pending, pending[1:])):
-        raise AuthorityEventRecoveryError("authority pending index ordering is invalid")
-    if (start is None) != (end is None) or (start is None and pending) or (start is not None and (not pending or pending[0].sequence != start or pending[-1].sequence != end or start != cursor + 1 or end > high)):
-        raise AuthorityEventRecoveryError("authority pending range is invalid")
-    for item in pending:
-        event = _read_authority_record_at(_validated_segment_path(item.trace_path, logs_root), item.offset, item.end_offset)
-        if event.sequence != item.sequence or event.event_id != item.event_id or event.runtime_domain_id != domain_id:
-            raise AuthorityEventRecoveryError("observability_recovery_required: pending record does not match sidecar")
-    conflicts = state.get("delivery_conflicts")
-    if not isinstance(conflicts, list) or len(conflicts) > _AUTHORITY_PENDING_LIMIT:
-        raise AuthorityEventRecoveryError("authority delivery conflict metadata is invalid")
-    for marker in conflicts:
-        if not isinstance(marker, Mapping) or set(marker) != {"runtime_domain_id", "sequence", "event_id"}:
-            raise AuthorityEventRecoveryError("authority delivery conflict marker is invalid")
-        if not isinstance(marker["runtime_domain_id"], str) or not marker["runtime_domain_id"] or isinstance(marker["sequence"], bool) or not isinstance(marker["sequence"], int) or marker["sequence"] < 1 or not isinstance(marker["event_id"], str) or not marker["event_id"]:
-            raise AuthorityEventRecoveryError("authority delivery conflict marker is invalid")
+    validated_domains: dict[str, object] = {}
+    for owner_domain_id, raw_domain in domains.items():
+        if not isinstance(owner_domain_id, str) or not owner_domain_id:
+            raise AuthorityEventRecoveryError("authority sidecar domain key is invalid")
+        if not isinstance(raw_domain, Mapping):
+            raise AuthorityEventRecoveryError("authority domain sidecar is invalid")
+        validated_domains[owner_domain_id] = _validate_authority_domain_state(owner_domain_id, raw_domain, logs_root=logs_root)
+    payload = dict(payload)
+    payload["domains"] = validated_domains
+    state = dict(validated_domains.get(domain_id) or _authority_default_domain(domain_id))
     return state, payload
 
 
@@ -323,13 +367,49 @@ def _authority_envelope(event: AuthorityEvent) -> dict[str, object]:
 
 
 def _append_authority_record_locked(path: Path, event: AuthorityEvent) -> RecordIndex:
-    line = json.dumps(_authority_envelope(event), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
-    with path.open("ab") as stream:
-        start = stream.tell()
-        stream.write(line.encode("utf-8"))
-        stream.flush()
-        os.fsync(stream.fileno())
-        end = stream.tell()
+    data = (
+        json.dumps(
+            _authority_envelope(event),
+            ensure_ascii=False,
+            sort_keys=True,
+            separators=(",", ":"),
+        )
+        + "\n"
+    ).encode("utf-8")
+    fd = os.open(
+        str(path),
+        os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0),
+        0o600,
+    )
+    try:
+        before = os.fstat(fd).st_size
+        written = os.write(fd, data)
+        if written != len(data):
+            raise AuthorityEventRecoveryError("short authority JSONL append")
+        os.fsync(fd)
+        end = os.fstat(fd).st_size
+    finally:
+        os.close(fd)
+    if end < before + written:
+        raise AuthorityEventRecoveryError("authority JSONL append size is inconsistent")
+    span = end - before
+    if span > max(_AUTHORITY_APPEND_LOCATE_WINDOW, written):
+        raise AuthorityEventRecoveryError(
+            "authority append location exceeds bounded interleaving window"
+        )
+    with path.open("rb") as stream:
+        stream.seek(before)
+        window = stream.read(span)
+    relative = window.find(data)
+    if relative < 0:
+        raise AuthorityEventRecoveryError("authority JSONL append cannot be located exactly")
+    if window.find(data, relative + 1) >= 0:
+        raise AuthorityEventRecoveryError("authority JSONL append identity is ambiguous")
+    start = before + relative
+    end = start + written
+    recovered = _read_authority_record_at(path, start, end)
+    if recovered.event_id != event.event_id or recovered.sequence != event.sequence or recovered.runtime_domain_id != event.runtime_domain_id:
+        raise AuthorityEventRecoveryError("authority JSONL append identity verification failed")
     return RecordIndex(event.sequence, event.event_id, str(path.resolve()), start, end)
 
 
@@ -429,7 +509,7 @@ class AuthorityEventEmitter:
         self.logs_root = (Path(logs_root) if logs_root is not None else runtime_logs_dir()).resolve()
         self.sidecar_path = authority_event_state_path(self.logs_root)
         self._lock_path = self.sidecar_path.with_name(f".{self.sidecar_path.name}.lock")
-        self.log_path = _ensure_runtime_trace_session().resolve()
+        self.log_path = _ensure_runtime_trace_session(logs_root=self.logs_root).resolve()
         if self.log_path.parent != self.logs_root or self.log_path.suffix != ".jsonl":
             raise AuthorityEventRecoveryError("authority trace session is outside runtime logs root")
         self.live_sink: Callable[[dict[str, object]], object] | None = None
@@ -446,7 +526,12 @@ class AuthorityEventEmitter:
         previous = _validated_segment_path(str(payload["active_trace_path"]), self.logs_root)
         tail = int(payload["durable_tail_offset"])
         if previous != self.log_path:
-            previous_size = previous.stat().st_size
+            try:
+                previous_size = previous.stat().st_size
+            except FileNotFoundError as exc:
+                raise AuthorityEventRecoveryError(
+                    "observability_recovery_required: authority trace segment is missing"
+                ) from exc
             payload = self._recover_unindexed_range_locked(previous, tail, previous_size, payload)
             payload["active_trace_path"] = str(self.log_path.resolve())
             payload["durable_tail_offset"] = self.log_path.stat().st_size
@@ -502,8 +587,8 @@ class AuthorityEventEmitter:
                 domain["pending_start_sequence"] = int(domain["live_handoff_cursor"]) + 1
             domain["pending_end_sequence"] = event.sequence
             if event.event_type == "AUTHORITY_EVENT_DELIVERY_CONFLICT":
-                if not event.operation_id or not isinstance(event.queue_order, int) or event.queue_order < 1:
-                    raise AuthorityEventRecoveryError("authority delivery conflict lacks machine identity")
+                if event.request_type != "authority_delivery_conflict" or not isinstance(event.operation_id, str) or not event.operation_id or isinstance(event.queue_order, bool) or not isinstance(event.queue_order, int) or event.queue_order < 1:
+                    raise AuthorityEventRecoveryError("authority delivery conflict lacks exact machine identity")
                 marker = {"runtime_domain_id": event.runtime_domain_id, "sequence": event.queue_order, "event_id": event.operation_id}
                 if marker not in domain["delivery_conflicts"]:
                     domain["delivery_conflicts"] = list(domain["delivery_conflicts"]) + [marker]
@@ -720,8 +805,31 @@ def emit_authority_event(event_type: str, *, runtime_domain_id: str, repo_id: st
     return pipeline.emit(event_type, repo_id=repo_id, runtime_domain_id=runtime_domain_id, **fields)
 
 
-def _pointer_path() -> Path:
-    return runtime_logs_dir() / _POINTER_NAME
+def _resolved_logs_root(logs_root: str | Path | None = None) -> Path:
+    return (Path(logs_root) if logs_root is not None else runtime_logs_dir()).resolve()
+
+
+def _pointer_path(logs_root: str | Path | None = None) -> Path:
+    return _resolved_logs_root(logs_root) / _POINTER_NAME
+
+
+def _active_trace_path_for_root(logs_root: Path) -> Path | None:
+    pointer = _pointer_path(logs_root)
+    try:
+        payload = json.loads(pointer.read_text(encoding="utf-8"))
+    except FileNotFoundError:
+        return None
+    except (OSError, ValueError, TypeError) as exc:
+        raise AuthorityEventRecoveryError(f"malformed runtime trace pointer: {pointer}") from exc
+    if not isinstance(payload, dict):
+        raise AuthorityEventRecoveryError("runtime trace pointer must be an object")
+    file_name = payload.get("file")
+    if not isinstance(file_name, str) or not file_name:
+        raise AuthorityEventRecoveryError("runtime trace pointer file is invalid")
+    candidate = (logs_root / file_name).resolve()
+    if candidate.parent != logs_root.resolve() or candidate.suffix != ".jsonl":
+        raise AuthorityEventRecoveryError("runtime trace pointer escapes logs_root")
+    return candidate if candidate.exists() else None
 
 
 def _now() -> tuple[str, str]:
@@ -830,10 +938,11 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
     ]
 
 
-def _open_runtime_trace_session() -> Path:
+def _open_runtime_trace_session(*, logs_root: str | Path | None = None) -> Path:
     """Open and publish the sole runtime-trace JSONL session."""
     global _active_meta, _active_path, _active_sid, _active_fd, _last_pointer_check
-    logs = runtime_logs_dir()
+    logs = _resolved_logs_root(logs_root)
+    production_logs = runtime_logs_dir().resolve()
     logs.mkdir(parents=True, exist_ok=True)
     started_at, stamp = _now()
     pid = os.getpid()
@@ -847,19 +956,24 @@ def _open_runtime_trace_session() -> Path:
         handle.flush()
         os.fsync(handle.fileno())
     pointer = {"schema": TRACE_SCHEMA, "sid": sid, "file": file_name, "desktop_pid": pid, "started_at": started_at}
-    atomic_write(_pointer_path(), json.dumps(pointer, ensure_ascii=False, separators=(",", ":")))
-    with _lock:
-        _active_meta, _active_path, _active_sid = pointer, path.resolve(), sid
-        _active_fd = None
-        _last_pointer_check = time.monotonic()
+    atomic_write(_pointer_path(logs), json.dumps(pointer, ensure_ascii=False, separators=(",", ":")))
+    if logs == production_logs:
+        with _lock:
+            _active_meta, _active_path, _active_sid = pointer, path.resolve(), sid
+            _active_fd = None
+            _last_pointer_check = time.monotonic()
     return path.resolve()
 
 
-def _ensure_runtime_trace_session() -> Path:
-    current = active_trace_path(force_refresh=True)
+def _ensure_runtime_trace_session(*, logs_root: str | Path | None = None) -> Path:
+    logs = _resolved_logs_root(logs_root)
+    current = active_trace_path(force_refresh=True) if logs == runtime_logs_dir().resolve() else _active_trace_path_for_root(logs)
     if current is not None:
+        current = current.resolve()
+        if current.parent != logs:
+            raise AuthorityEventRecoveryError("runtime trace session is outside requested logs_root")
         return current
-    return _open_runtime_trace_session()
+    return _open_runtime_trace_session(logs_root=logs)
 
 
 def start_desktop_trace_session() -> Path | None:

diff --git a/tests/test_runtime_authority_events.py b/tests/test_runtime_authority_events.py
index 096be9e..8eb8932 100644
--- a/tests/test_runtime_authority_events.py
+++ b/tests/test_runtime_authority_events.py
@@ -390,3 +390,104 @@ def test_filtered_get_events_latest_seq_is_never_used_as_feed_cursor():
     feed = DesktopLiveEventFeed(Client(), lambda *_args, **_kwargs: None, initial_seq=7)
     feed.replay_authority_events()
     assert feed._last_seq == 7
+
+
+def test_explicit_authority_logs_root_never_touches_production_runtime_logs(tmp_path, monkeypatch):
+    production, isolated = tmp_path / "production-logs", tmp_path / "isolated-logs"
+    production.mkdir(); isolated.mkdir()
+    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: production)
+    trace.finish_desktop_trace_session()
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="isolated-domain", logs_root=isolated)
+    emitter.emit("ISOLATED")
+    assert emitter.log_path.parent == isolated.resolve()
+    assert emitter.sidecar_path.parent == isolated.resolve()
+    assert (isolated / trace._POINTER_NAME).exists()
+    assert list(isolated.glob("contextor_runtime_*.jsonl"))
+    assert not list(production.glob("contextor_runtime_*.jsonl"))
+    assert not (production / "authority_event_state.json").exists()
+    assert not (production / trace._POINTER_NAME).exists()
+
+
+def test_authority_record_offset_survives_interleaved_runtime_trace_append(trace_logs, monkeypatch):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    real_write, injected = trace.os.write, False
+    def interleaved_write(fd, data):
+        nonlocal injected
+        if not injected and b'"_type":"authority_event"' in data:
+            injected = True
+            trace.trace_event("TEST", "INTERLEAVED")
+        return real_write(fd, data)
+    monkeypatch.setattr(trace.os, "write", interleaved_write)
+    event = emitter.emit("AUTHORITY")
+    state = _state(trace_logs)["domains"]["domain-a"]
+    recovered = trace._read_authority_record_at(emitter.log_path, state["durable_high_water_offset"], state["durable_high_water_end_offset"])
+    assert recovered.event_id == event.event_id
+    assert recovered.sequence == event.sequence
+    restarted = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    assert restarted.emit("NEXT").sequence == 2
+
+
+def test_recovered_conflict_with_wrong_request_type_fails_closed(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    domain = _state(trace_logs)["domains"]["domain-a"]
+    event = trace.AuthorityEvent(event_id="bad-conflict", timestamp="2026-01-01T00:00:00+00:00", sequence=domain["durable_high_water_sequence"] + 1, event_type="AUTHORITY_EVENT_DELIVERY_CONFLICT", runtime_domain_id="domain-a", operation_id="original-id", request_type="wrong", queue_order=1)
+    trace._append_authority_record_locked(emitter.log_path, event)
+    with pytest.raises(trace.AuthorityEventRecoveryError):
+        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+
+
+def test_pending_index_hole_fails_closed(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.emit("ONE"); emitter.emit("TWO"); emitter.emit("THREE")
+    sidecar = _state(trace_logs); domain = sidecar["domains"]["domain-a"]
+    domain["pending_index"] = [domain["pending_index"][0], domain["pending_index"][2]]
+    domain["pending_start_sequence"], domain["pending_end_sequence"] = 1, 3
+    (trace_logs / "authority_event_state.json").write_text(json.dumps(sidecar), encoding="utf-8")
+    with pytest.raises(trace.AuthorityEventRecoveryError):
+        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+
+
+def test_corrupt_foreign_domain_blocks_healthy_domain_emitter(trace_logs):
+    left = trace.AuthorityEventEmitter(runtime_domain_id="left", logs_root=trace_logs)
+    right = trace.AuthorityEventEmitter(runtime_domain_id="right", logs_root=trace_logs)
+    left.emit("LEFT"); right.emit("RIGHT")
+    sidecar = _state(trace_logs); sidecar["domains"]["right"]["live_handoff_cursor"] = 99
+    (trace_logs / "authority_event_state.json").write_text(json.dumps(sidecar), encoding="utf-8")
+    with pytest.raises(trace.AuthorityEventRecoveryError):
+        trace.AuthorityEventEmitter(runtime_domain_id="left", logs_root=trace_logs)
+
+
+def test_schema2_zero_highwater_upgrade_remains_valid(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    sidecar = _state(trace_logs)
+    sidecar_v2 = {"schema_version": 2, "trace_path": sidecar["active_trace_path"], "durable_tail_offset": sidecar["durable_tail_offset"], "domains": {"domain-a": {"runtime_domain_id": "domain-a", "durable_high_water_sequence": 0, "durable_high_water_event_id": None, "durable_high_water_offset": None, "durable_high_water_end_offset": None, "live_handoff_cursor": 0, "live_handoff_epoch": None, "pending_start_sequence": None, "pending_end_sequence": None, "pending_index": []}}}
+    emitter.sidecar_path.write_text(json.dumps(sidecar_v2), encoding="utf-8")
+    recovered = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    assert recovered.emit("FIRST").sequence == 1
+
+
+def test_append_location_bound_is_independent_from_recovery_window(
+    trace_logs,
+    monkeypatch,
+):
+    emitter = trace.AuthorityEventEmitter(
+        runtime_domain_id="domain-a",
+        logs_root=trace_logs,
+    )
+
+    monkeypatch.setattr(trace, "_AUTHORITY_RECOVERY_WINDOW", 64)
+
+    event = emitter.emit(
+        "AUTHORITY_WITH_RECOVERY_WINDOW_SMALLER_THAN_EVENT",
+        reason="x" * 256,
+    )
+
+    state = _state(trace_logs)["domains"]["domain-a"]
+    recovered = trace._read_authority_record_at(
+        emitter.log_path,
+        state["durable_high_water_offset"],
+        state["durable_high_water_end_offset"],
+    )
+
+    assert recovered.event_id == event.event_id
+    assert recovered.sequence == event.sequence


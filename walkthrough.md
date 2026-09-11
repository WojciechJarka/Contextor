STATUS=PASS

IMPLEMENTATION
- CanonicalLiveServer derives syntax, collision, and cycle changes exclusively from fresh committed before/after state after persistence and atomic commit.
- update_file journal events carry only canonical bounded diagnostic_changes ({total, truncated, items}; items limit 3); caller-supplied diagnostic_changes is discarded.
- DesktopLiveEventFeed presents diagnostic detail without changing existing SYNTAX_ERROR or RECOVERED base wording.
- Runtime trace records all committed diagnostic deltas with durable structured node arrays.

INVARIANTS
- Diagnostic computation remains owned by the existing incremental analysis state; watcher code only formats published evidence.
- Stale or deferred diagnostic families produce no delta.
- Journal projection deep-copies diagnostic_changes; trace emission is best effort and cannot affect commit.

DOC_CONTRACT
- get_live_events documents optional diagnostic_changes, its bounded shape, stable key, freshness gate, full runtime-trace evidence, and unchanged syntax fields.
- The file retains catalog-compatible version 1.0.0 because the allowed file set excludes the shared documentation index and loader requires every tool document to match that index version.

TEST_RESULTS
- py_compile: PASS
- Focused pytest command: PASS (completed successfully): tests/test_live_state_ipc.py tests/test_live_activity_status.py tests/test_runtime_trace.py tests/test_collisions_live_lifecycle.py tests/test_cycles_live_lifecycle.py tests/test_mcp_documentation.py tests/mcp/tools/test_public_mcp_docs_parity.py
- git diff --check: PASS.

FILES_CHANGED
- contextor/core/live_state/ipc.py
- contextor/core/runtime_trace.py
- contextor/core/live_state/watcher.py
- contextor/mcp/docs/get_live_events.json
- tests/test_live_state_ipc.py
- tests/test_live_activity_status.py
- tests/test_runtime_trace.py

PREEXISTING_WORKTREE_CHANGES
- walkthrough.md was already modified before this task.

COMPLETE FULL_DIFF
warning: in the working copy of 'contextor/core/live_state/ipc.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/live_state/watcher.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/runtime_trace.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/mcp/docs/get_live_events.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_activity_status.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_state_ipc.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_runtime_trace.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 1d1c584..ee7e50f 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -89,6 +89,7 @@ class LiveEndpoint:


 ACTIVITY_EVENT_RETENTION = 10_000
+_DIAGNOSTIC_JOURNAL_LIMIT = 3


 _MISSING_REVISION = object()
@@ -228,6 +229,222 @@ def _clone_state_for_update(state: Any) -> Any:
     return candidate


+def _state_value(state: Any, name: str, default: Any = None) -> Any:
+    """Read one canonical-state field without assuming an object shape."""
+    try:
+        if isinstance(state, Mapping):
+            return state.get(name, default)
+        return getattr(state, name, default)
+    except Exception:
+        return default
+
+
+def _family_is_fresh(state: Any, field_name: str) -> bool:
+    return _state_value(state, field_name) == "fresh"
+
+
+def _diagnostic_key_text(kind: str, parts: tuple[Any, ...]) -> str:
+    try:
+        return json.dumps(
+            [kind, *parts], ensure_ascii=False, separators=(",", ":"), sort_keys=True
+        )
+    except (TypeError, ValueError):
+        return ""
+
+
+def _valid_optional_int(value: Any) -> bool:
+    return value is None or (isinstance(value, int) and not isinstance(value, bool))
+
+
+def _syntax_diagnostic_map(state: Any) -> dict[str, dict[str, Any]] | None:
+    if not _family_is_fresh(state, "syntax_diagnostics_state"):
+        return None
+    facts = _state_value(state, "syntax_diagnostics_by_path")
+    if not isinstance(facts, Mapping):
+        return None
+
+    result: dict[str, dict[str, Any]] = {}
+    source_paths = sorted(path for path in facts if isinstance(path, str) and path)
+    for source_path in source_paths:
+        fact = facts.get(source_path)
+        if not isinstance(fact, Mapping) or fact.get("status") != "checked_with_errors":
+            continue
+        errors = fact.get("errors")
+        if not isinstance(errors, (list, tuple)):
+            continue
+        for error in errors:
+            if not isinstance(error, Mapping):
+                continue
+            message = error.get("message")
+            line_number = error.get("line_number")
+            column_number = error.get("column_number")
+            if (
+                not isinstance(message, str)
+                or not message
+                or not _valid_optional_int(line_number)
+                or not _valid_optional_int(column_number)
+            ):
+                continue
+            key = _diagnostic_key_text(
+                "syntax", (source_path, line_number, column_number)
+            )
+            if not key:
+                continue
+            candidate = {
+                "source_path": source_path,
+                "message": message,
+                "line_number": line_number,
+                "column_number": column_number,
+            }
+            existing = result.get(key)
+            if existing is None or candidate["message"] < existing["message"]:
+                result[key] = candidate
+    return result
+
+
+def _collision_diagnostic_map(state: Any) -> dict[str, dict[str, Any]] | None:
+    if not _family_is_fresh(state, "collisions_state"):
+        return None
+    collisions = _state_value(state, "collisions")
+    if not isinstance(collisions, (list, tuple)):
+        return None
+
+    result: dict[str, dict[str, Any]] = {}
+    for collision in collisions:
+        kind = _state_value(collision, "kind")
+        artifact_type = _state_value(collision, "artifact_type")
+        is_identical = _state_value(collision, "is_identical")
+        nodes = _state_value(collision, "nodes")
+        symbol_details = _state_value(collision, "symbol_details")
+        if (
+            not isinstance(kind, str)
+            or not kind
+            or not isinstance(artifact_type, str)
+            or not artifact_type
+            or type(is_identical) is not bool
+            or not isinstance(nodes, (list, tuple, set))
+            or not isinstance(symbol_details, (list, tuple))
+            or not symbol_details
+        ):
+            continue
+        if not all(isinstance(node, str) and node for node in nodes):
+            continue
+        normalized_nodes = sorted(set(nodes))
+        if not normalized_nodes:
+            continue
+
+        names: set[str] = set()
+        malformed = False
+        for detail in symbol_details:
+            if not isinstance(detail, Mapping):
+                malformed = True
+                break
+            name = detail.get("name")
+            if isinstance(name, str) and name:
+                names.add(name)
+            detail_type = detail.get("artifact_type")
+            if detail_type:
+                if not isinstance(detail_type, str) or detail_type != artifact_type:
+                    malformed = True
+                    break
+        if malformed or len(names) != 1:
+            continue
+        collision_symbol = next(iter(names))
+        key = _diagnostic_key_text(
+            "collision",
+            (kind, artifact_type, is_identical, collision_symbol, *normalized_nodes),
+        )
+        if not key:
+            continue
+        result.setdefault(
+            key,
+            {
+                "collision_kind": kind,
+                "collision_artifact_type": artifact_type,
+                "collision_symbol": collision_symbol,
+                "collision_is_identical": is_identical,
+                "collision_nodes": normalized_nodes,
+            },
+        )
+    return result
+
+
+def _cycle_diagnostic_map(state: Any) -> dict[str, dict[str, Any]] | None:
+    if not _family_is_fresh(state, "cycles_state"):
+        return None
+    cycles = _state_value(state, "cycles")
+    if not isinstance(cycles, (list, tuple)):
+        return None
+
+    result: dict[str, dict[str, Any]] = {}
+    for cycle in cycles:
+        if (
+            not isinstance(cycle, (list, tuple))
+            or len(cycle) < 2
+            or not all(isinstance(node, str) and node for node in cycle)
+            or cycle[0] != cycle[-1]
+        ):
+            continue
+        key = _diagnostic_key_text("cycle", tuple(cycle))
+        if key:
+            result.setdefault(key, {"cycle_nodes": list(cycle)})
+    return result
+
+
+def _build_diagnostic_delta(previous_state: Any, current_state: Any) -> list[dict[str, Any]]:
+    changes: list[dict[str, Any]] = []
+    families = (
+        ("syntax", _syntax_diagnostic_map),
+        ("collision", _collision_diagnostic_map),
+        ("cycle", _cycle_diagnostic_map),
+    )
+    for kind, normalizer in families:
+        previous = normalizer(previous_state)
+        current = normalizer(current_state)
+        if previous is None or current is None:
+            continue
+        for key in sorted(set(current) - set(previous)):
+            changes.append(
+                {"action": "ADDED", "diagnostic_kind": kind, "diagnostic_key": key, **current[key]}
+            )
+        for key in sorted(set(previous) - set(current)):
+            changes.append(
+                {"action": "RESOLVED", "diagnostic_kind": kind, "diagnostic_key": key, **previous[key]}
+            )
+    kind_rank = {"syntax": 0, "collision": 1, "cycle": 2}
+    action_rank = {"ADDED": 0, "RESOLVED": 1}
+    return sorted(
+        changes,
+        key=lambda item: (
+            kind_rank[item["diagnostic_kind"]],
+            action_rank[item["action"]],
+            item["diagnostic_key"],
+        ),
+    )
+
+
+def _bounded_diagnostic_payload(changes: list[dict[str, Any]]) -> dict[str, Any] | None:
+    if not changes:
+        return None
+    return {
+        "total": len(changes),
+        "truncated": len(changes) > _DIAGNOSTIC_JOURNAL_LIMIT,
+        "items": copy.deepcopy(changes[:_DIAGNOSTIC_JOURNAL_LIMIT]),
+    }
+
+
+def _diagnostic_trace_event_name(change: Mapping[str, Any]) -> str | None:
+    names = {
+        ("syntax", "ADDED"): "LIVE_DIAGNOSTIC_SYNTAX_ERROR",
+        ("syntax", "RESOLVED"): "LIVE_DIAGNOSTIC_SYNTAX_RECOVERED",
+        ("collision", "ADDED"): "LIVE_DIAGNOSTIC_COLLISION_ADDED",
+        ("collision", "RESOLVED"): "LIVE_DIAGNOSTIC_COLLISION_RESOLVED",
+        ("cycle", "ADDED"): "LIVE_DIAGNOSTIC_CYCLE_ADDED",
+        ("cycle", "RESOLVED"): "LIVE_DIAGNOSTIC_CYCLE_RESOLVED",
+    }
+    return names.get((change.get("diagnostic_kind"), change.get("action")))
+
+
 class CanonicalLiveServer:
     """In-RAM coordinator for one repository's shared LIVE state."""

@@ -380,6 +597,9 @@ class CanonicalLiveServer:
                     "truncated": total > 20,
                     "items": list(affected[:20]),
                 }
+            diagnostic_changes = request.get("diagnostic_changes")
+            if isinstance(diagnostic_changes, Mapping):
+                event["diagnostic_changes"] = copy.deepcopy(diagnostic_changes)
             if request.get("message") is not None:
                 event["message"] = str(request["message"])

@@ -963,13 +1183,66 @@ class CanonicalLiveServer:
                 self._revision = expected_revision
                 _safe_trace_event("LIVE", "CANONICAL_COMMIT", op=trace_op, path=file_path, rev_before=previous_revision, rev_after=expected_revision)

+                try:
+                    diagnostic_delta = _build_diagnostic_delta(
+                        previous_state, self._state
+                    )
+                except Exception:
+                    diagnostic_delta = []
+                diagnostic_payload = _bounded_diagnostic_payload(diagnostic_delta)
+                event_request = dict(request)
+                # Request payload is untrusted metadata: only the committed-state
+                # comparison may publish diagnostic evidence.
+                event_request.pop("diagnostic_changes", None)
+                if diagnostic_payload is not None:
+                    event_request["diagnostic_changes"] = diagnostic_payload
+
                 evt = self._record_event(
                     "update_file",
-                    request,
+                    event_request,
                     result,
                     category="LIVE_STATE",
                 )
                 _safe_trace_event("LIVE", "UPDATE_PUBLISHED", op=trace_op, path=file_path, rev=self._revision, seq=evt["seq"], status=getattr(result, "status", None))
+                origin = str(event_request.get("origin") or event_request.get("source") or "unknown")
+                trace_common = {
+                    "repo": self._authority_identity.get("root_path"),
+                    "repo_id": self._authority_identity.get("repo_id"),
+                    "origin": origin,
+                    "diagnostic_total": len(diagnostic_delta),
+                    "diagnostic_truncated": len(diagnostic_delta) > _DIAGNOSTIC_JOURNAL_LIMIT,
+                }
+                for change in diagnostic_delta:
+                    event_name = _diagnostic_trace_event_name(change)
+                    if event_name is None:
+                        continue
+                    trace_fields = {
+                        **trace_common,
+                        "diagnostic_kind": change["diagnostic_kind"],
+                        "diagnostic_key": change["diagnostic_key"],
+                    }
+                    if "source_path" in change:
+                        trace_fields["path"] = change["source_path"]
+                    if change["diagnostic_kind"] == "syntax":
+                        trace_fields.update(
+                            error=change["message"],
+                            line_number=change["line_number"],
+                            column_number=change["column_number"],
+                        )
+                    elif change["diagnostic_kind"] == "collision":
+                        for field in (
+                            "collision_kind",
+                            "collision_artifact_type",
+                            "collision_symbol",
+                            "collision_is_identical",
+                            "collision_nodes",
+                        ):
+                            trace_fields[field] = change[field]
+                    else:
+                        trace_fields["cycle_nodes"] = change["cycle_nodes"]
+                    _safe_trace_event(
+                        "LIVE", event_name, op=trace_op, rev=self._revision, **trace_fields
+                    )

                 return {
                     "status": "ok",
@@ -1079,9 +1352,9 @@ class CanonicalLiveServer:
                             "status": e["status"],
                             "file_path": e.get("file_path"),
                         }
-                        for name in ("error", "line_number", "column_number", "blast_radius_state", "affected_modules", "message"):
+                        for name in ("error", "line_number", "column_number", "blast_radius_state", "affected_modules", "diagnostic_changes", "message"):
                             if e.get(name) is not None:
-                                item[name] = e[name]
+                                item[name] = copy.deepcopy(e[name])
                         formatted_selected.append(item)
                     selected = formatted_selected

diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 8d18fe9..03ac60e 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -818,6 +818,76 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
             return domain, sequence, event_id
         return None

+    @staticmethod
+    def _diagnostic_detail(item: object) -> str | None:
+        if not isinstance(item, dict):
+            return None
+        action = item.get("action")
+        kind = item.get("diagnostic_kind")
+        if action not in {"ADDED", "RESOLVED"}:
+            return None
+        verb = "added" if action == "ADDED" else "resolved"
+        if kind == "syntax":
+            source_path = item.get("source_path")
+            line = item.get("line_number")
+            column = item.get("column_number")
+            if (
+                not isinstance(source_path, str)
+                or not source_path
+                or (line is not None and (not isinstance(line, int) or isinstance(line, bool)))
+                or (column is not None and (not isinstance(column, int) or isinstance(column, bool)))
+            ):
+                return None
+            return f"syntax error {verb}: {source_path}:{line}:{column}"
+        if kind == "collision":
+            symbol = item.get("collision_symbol")
+            nodes = item.get("collision_nodes")
+            if (
+                not isinstance(symbol, str)
+                or not symbol
+                or not isinstance(nodes, (list, tuple))
+                or not nodes
+                or not all(isinstance(node, str) and node for node in nodes)
+            ):
+                return None
+            return f"collision {verb}: {symbol} [{', '.join(nodes)}]"
+        if kind == "cycle":
+            nodes = item.get("cycle_nodes")
+            if (
+                not isinstance(nodes, (list, tuple))
+                or not nodes
+                or not all(isinstance(node, str) and node for node in nodes)
+            ):
+                return None
+            return f"cycle {verb}: {' -> '.join(nodes)}"
+        return None
+
+    @classmethod
+    def _format_diagnostic_payload(
+        cls, payload: object, *, suppress_syntax: bool = False
+    ) -> str | None:
+        if not isinstance(payload, dict):
+            return None
+        items = payload.get("items")
+        total = payload.get("total")
+        if (
+            not isinstance(items, (list, tuple))
+            or not isinstance(total, int)
+            or isinstance(total, bool)
+            or total < len(items)
+        ):
+            return None
+        details = []
+        for item in items:
+            if suppress_syntax and isinstance(item, dict) and item.get("diagnostic_kind") == "syntax":
+                continue
+            detail = cls._diagnostic_detail(item)
+            if detail is not None:
+                details.append(detail)
+        if total > len(items):
+            details.append(f"+{total - len(items)} more")
+        return "; ".join(details) if details else None
+
     def _message(self, event: dict) -> str | None:
         category = event.get("category", "LIVE_STATE")
         if category == "AUTHORITY":
@@ -854,14 +924,25 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
             rev = event.get("canonical_revision")
             rev_str = f" (rev {rev})" if rev is not None else ""
             status = event.get("status", "UPDATED")
+            diagnostic_payload = event.get("diagnostic_changes")
             if status == "SYNTAX_ERROR":
                 err = event.get("error", "syntax error")
                 line = event.get("line_number")
                 col = event.get("column_number")
                 pos = f" line {line}, column {col}" if line and col else ""
-                return f"[LIVE] Syntax error in {file_name}{pos}: {err}"
+                message = f"[LIVE] Syntax error in {file_name}{pos}: {err}"
             elif status == "RECOVERED":
-                return f"[LIVE] Syntax recovered in {file_name}{rev_str}"
+                message = f"[LIVE] Syntax recovered in {file_name}{rev_str}"
+            else:
+                message = None
+            if message is not None:
+                details = self._format_diagnostic_payload(
+                    diagnostic_payload, suppress_syntax=True
+                )
+                return f"{message}; {details}" if details else message
+            details = self._format_diagnostic_payload(diagnostic_payload)
+            if details:
+                return f"[LIVE] Diagnostics after {file_name} (rev {rev}): {details}"
             elif origin in {"desktop_watcher", "desktop"}:
                 return f"[LIVE] Watcher updated {file_name}{rev_str}"
             elif origin in {"mcp", "mcp_update"}:
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index a405684..51394e6 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -1053,6 +1053,12 @@ def _bounded(value: object) -> object:
     return str(value)[:_MAX_TEXT]


+def _bounded_string_list(value: object) -> object:
+    if not isinstance(value, (list, tuple)):
+        return _bounded(value)
+    return [_bounded(item) for item in value]
+
+
 def _read_pointer() -> tuple[dict[str, object], Path] | None:
     try:
         pointer = _pointer_path()
@@ -1135,13 +1141,41 @@ def _append(record: dict[str, object], path: Path) -> None:


 def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str) -> list[dict[str, object]]:
-    return [
+    records = [
         {"_type": "header", "schema": TRACE_SCHEMA, "purpose": "chronological Contextor Desktop/LIVE/MCP runtime diagnostics; one JSON object per line", "sid": sid, "started_at": started_at, "desktop_pid": desktop_pid, "file": file_name},
         {"_type": "fields", "fields": {"ts": "UTC ISO-8601 milliseconds", "mono_ms": "host monotonic milliseconds", "sid": "desktop trace session", "pid": "process id", "tid": "thread id", "d": "domain", "ev": "event", "op": "operation correlation id", "repo": "repository", "path": "repository-relative path", "kind": "change kind", "tool": "MCP tool", "rev": "observed canonical revision", "rev0": "canonical revision before transition", "rev1": "canonical revision after transition", "candidate_rev": "rejected candidate canonical revision", "seq": "activity-journal sequence", "q": "GUI queue size", "count": "count", "bytes": "byte count", "wait_ms": "queue wait milliseconds", "elapsed_ms": "elapsed milliseconds", "scan_ms": "watcher scan milliseconds", "ping_ms": "watcher ping milliseconds", "status": "compact status", "err": "bounded error", "mtime_ns": "observed file mtime", "attempt": "connection attempt number", "attempts": "connection attempt budget", "attempts_used": "attempt count consumed", "retry_delay": "retry delay seconds", "runtime_domain_id": "runtime domain identity", "repo_id": "repository identity", "endpoint_fingerprint": "hashed endpoint identity", "service_pid": "LIVE service process id", "lease_generation": "LIVE lease generation", "service_instance_id": "LIVE service instance", "reason_code": "stable diagnostic reason", "exception_class": "exception class", "errno": "OS errno", "winerror": "Windows error", "error": "bounded error text", "pid_alive": "service PID liveness", "endpoint_changed": "endpoint identity changed", "process_alive": "service process liveness", "process_identity_matches": "process start identity matches", "endpoint_available": "endpoint metadata available", "endpoint_matches": "endpoint identity matches", "reason": "evidence-neutral reason", "result": "evidence-neutral result", "side": "IPC side", "operation_or_request_type": "IPC request or transport stage", "host": "IPC endpoint host", "port": "IPC endpoint port", "prior_endpoint_fingerprint": "previous hashed endpoint identity", "prior_service_pid": "previous LIVE service process id", "new_endpoint_fingerprint": "new hashed endpoint identity", "new_service_pid": "new LIVE service process id", "recovery_operation_id": "watcher recovery operation correlation id"}},
         {"_type": "domains", "domains": ["DESKTOP", "LIVE", "MCP", "GUI"], "reserved": ["OPS"], "ops_note": "Reserved for future repository-operation coordination; not implemented here."},
         {"_type": "revision_semantics", "rev": "observed authoritative canonical revision", "rev0": "authoritative canonical revision before transition", "rev1": "authoritative canonical revision after transition", "seq": "independent activity-journal sequence", "logger_rule": "The logger never calculates or increments canonical revision or activity sequence."},
         {"_type": "events", "events": {"DESKTOP": ["SESSION_START", "SESSION_END"], "LIVE": ["FS_CHANGE_DETECTED", "WATCH_UPDATE_START", "WATCH_UPDATE_END", "WATCH_UPDATE_FAIL", "UPDATE_RECEIVED", "UPDATE_FAIL", "CLONE_END", "UPDATER_START", "UPDATER_END", "UPDATER_FAIL", "ENGINE_READY", "INCREMENTAL_END", "PERSIST_START", "SNAPSHOT_SAVE_END", "FILE_STATE_SAVE_END", "PERSIST_END", "CANONICAL_COMMIT", "UPDATE_PUBLISHED", "PUBLISH_RECEIVED", "CANONICAL_PUBLISH", "PUBLISH_FAIL", "ACTIVITY_APPEND", "SERVICE_START", "SERVICE_END", "LIVE_CONNECT_ATTEMPT", "LIVE_CONNECT_REJECT", "LIVE_CONNECT_RESULT", "LIVE_LIVENESS_RESULT", "LIVE_WATCHER_RECOVERY_START", "LIVE_WATCHER_RECOVERY_RESULT", "LIVE_IPC_FAILURE", "LIVE_SERVICE_THREAD_FAILURE"], "MCP": ["CALL_START", "IMPLEMENTATION_END", "DIAGNOSTICS_END", "TELEMETRY_END", "CALL_END", "CALL_FAIL"], "GUI": ["EVENT_BATCH_RECEIVED", "ACTIVITY_GAP", "STATUS_QUEUED", "STATUS_RENDERED"]}},
     ]
+    records[1]["fields"].update(
+        {
+            "origin": "LIVE update origin",
+            "diagnostic_kind": "canonical diagnostic family",
+            "diagnostic_key": "stable canonical diagnostic identity",
+            "collision_kind": "canonical collision kind",
+            "collision_artifact_type": "canonical collision artifact type",
+            "collision_symbol": "canonical collision symbol",
+            "collision_is_identical": "canonical collision identity flag",
+            "collision_nodes": "canonical collision modules",
+            "cycle_nodes": "canonical closed cycle",
+            "diagnostic_total": "committed diagnostic delta size",
+            "diagnostic_truncated": "journal diagnostic detail truncation",
+            "line_number": "syntax error line",
+            "column_number": "syntax error column",
+        }
+    )
+    records[4]["events"]["LIVE"].extend(
+        [
+            "LIVE_DIAGNOSTIC_SYNTAX_ERROR",
+            "LIVE_DIAGNOSTIC_SYNTAX_RECOVERED",
+            "LIVE_DIAGNOSTIC_COLLISION_ADDED",
+            "LIVE_DIAGNOSTIC_COLLISION_RESOLVED",
+            "LIVE_DIAGNOSTIC_CYCLE_ADDED",
+            "LIVE_DIAGNOSTIC_CYCLE_RESOLVED",
+        ]
+    )
+    return records


 def _open_runtime_trace_session(*, logs_root: str | Path | None = None) -> Path:
@@ -1270,10 +1304,32 @@ def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | No
             if value is not None:
                 record[key] = value
         key_map = {"repo": "repo", "path": "path", "kind": "kind", "tool": "tool", "q": "q", "count": "count", "bytes": "bytes", "wait_ms": "wait_ms", "elapsed_ms": "elapsed_ms", "scan_ms": "scan_ms", "ping_ms": "ping_ms", "status": "status", "err": "err", "mtime_ns": "mtime_ns", "category": "category", "operation": "operation", "first_seq": "first_seq", "last_seq": "last_seq", "candidate_rev": "candidate_rev", "attempt": "attempt", "attempts": "attempts", "attempts_used": "attempts_used", "retry_delay": "retry_delay", "runtime_domain_id": "runtime_domain_id", "repo_id": "repo_id", "endpoint_fingerprint": "endpoint_fingerprint", "service_pid": "service_pid", "lease_generation": "lease_generation", "service_instance_id": "service_instance_id", "reason_code": "reason_code", "exception_class": "exception_class", "errno": "errno", "winerror": "winerror", "error": "error", "pid_alive": "pid_alive", "endpoint_changed": "endpoint_changed", "process_alive": "process_alive", "process_identity_matches": "process_identity_matches", "endpoint_available": "endpoint_available", "endpoint_matches": "endpoint_matches", "reason": "reason", "result": "result", "side": "side", "operation_or_request_type": "operation_or_request_type", "host": "host", "port": "port", "prior_endpoint_fingerprint": "prior_endpoint_fingerprint", "prior_service_pid": "prior_service_pid", "new_endpoint_fingerprint": "new_endpoint_fingerprint", "new_service_pid": "new_service_pid", "recovery_operation_id": "recovery_operation_id"}
+        key_map.update(
+            {
+                "origin": "origin",
+                "diagnostic_kind": "diagnostic_kind",
+                "diagnostic_key": "diagnostic_key",
+                "collision_kind": "collision_kind",
+                "collision_artifact_type": "collision_artifact_type",
+                "collision_symbol": "collision_symbol",
+                "collision_is_identical": "collision_is_identical",
+                "collision_nodes": "collision_nodes",
+                "cycle_nodes": "cycle_nodes",
+                "diagnostic_total": "diagnostic_total",
+                "diagnostic_truncated": "diagnostic_truncated",
+                "line_number": "line_number",
+                "column_number": "column_number",
+            }
+        )
+        structured_list_fields = {"collision_nodes", "cycle_nodes"}
         for key, value in fields.items():
             target = key_map.get(key)
             if target is not None and value is not None:
-                record[target] = _bounded(value)
+                record[target] = (
+                    _bounded_string_list(value)
+                    if key in structured_list_fields
+                    else _bounded(value)
+                )
         _append(record, path)
     except Exception:
         pass
diff --git a/contextor/mcp/docs/get_live_events.json b/contextor/mcp/docs/get_live_events.json
index b05e1ef..f04cff8 100644
--- a/contextor/mcp/docs/get_live_events.json
+++ b/contextor/mcp/docs/get_live_events.json
@@ -10,7 +10,11 @@
     "limit (integer or null, optional, default 20): maximum retained events to return; pass null for all retained events."
   ],
   "behavior": [
-    "MCP cannot push unsolicited messages into an idle model; this bounded\nfeed is the reliable pull mechanism for continuous LIVE state.\nEvents are an ephemeral in-RAM notification feed retained in a shared journal\n(retaining the most recent 10,000 mixed activity records), not a persistent full history\nor append-only source of truth. The canonical LIVE state is authoritative.\nThe response exposes explicit continuity metadata: ``latest_revision`` (authoritative canonical revision),\n``earliest_retained_revision`` (or ``null`` if buffer empty), ``continuity``\n(``'not_requested'``, ``'continuous'``, or ``'gap'``), ``resync_required`` (boolean),\nand ``resync_reason`` (``'event_retention_gap'``, ``'revision_discontinuity'``, or ``null``).\nWhen ``after_revision`` is supplied, only canonical mutation events (publish and update_file) are returned;\nMCP tool calls and non-canonical activity events are excluded. When ``after_revision`` is omitted (null),\nthe most recent retained mixed activity events from the journal are returned with ``continuity='not_requested'``.\nThe sequence cursor (``after_seq``) is used internally by Desktop activity feeds and is not part of this public tool schema.\nWhen ``resync_required=true``, the caller cursor lost continuity with the retained event window;\nthe caller must perform a canonical state resync (e.g. query_canonical_projection or\nget_project_architecture) rather than assuming returned events represent a complete sequential delta.\n``limit=None`` returns all retained matching events within the journal window, not the full history.\n``truncated`` indicates truncation solely due to the requested ``limit``, not retention loss."
+    "MCP cannot push unsolicited messages into an idle model; this bounded\nfeed is the reliable pull mechanism for continuous LIVE state.\nEvents are an ephemeral in-RAM notification feed retained in a shared journal\n(retaining the most recent 10,000 mixed activity records), not a persistent full history\nor append-only source of truth. The canonical LIVE state is authoritative.\nThe response exposes explicit continuity metadata: ``latest_revision`` (authoritative canonical revision),\n``earliest_retained_revision`` (or ``null`` if buffer empty), ``continuity``\n(``'not_requested'``, ``'continuous'``, or ``'gap'``), ``resync_required`` (boolean),\nand ``resync_reason`` (``'event_retention_gap'``, ``'revision_discontinuity'``, or ``null``).\nWhen ``after_revision`` is supplied, only canonical mutation events (publish and update_file) are returned;\nMCP tool calls and non-canonical activity events are excluded. When ``after_revision`` is omitted (null),\nthe most recent retained mixed activity events from the journal are returned with ``continuity='not_requested'``.\nThe sequence cursor (``after_seq``) is used internally by Desktop activity feeds and is not part of this public tool schema.\nWhen ``resync_required=true``, the caller cursor lost continuity with the retained event window;\nthe caller must perform a canonical state resync (e.g. query_canonical_projection or\nget_project_architecture) rather than assuming returned events represent a complete sequential delta.\n``limit=None`` returns all retained matching events within the journal window, not the full history.\n``truncated`` indicates truncation solely due to the requested ``limit``, not retention loss.",
+    "Committed incremental ``update_file`` events may include optional post-commit ``diagnostic_changes`` evidence with exact bounded shape ``{total, truncated, items}``; ``items`` contains at most three deterministic details.",
+    "Each diagnostic item exposes ``action`` (``ADDED`` or ``RESOLVED``), ``diagnostic_kind`` (``syntax``, ``collision``, or ``cycle``), and a stable JSON-safe ``diagnostic_key``. Syntax items include ``source_path`` and ``line_number``/``column_number`` when attributable; collision items expose canonical structured collision fields; cycle items expose ``cycle_nodes``.",
+    "Diagnostic changes are emitted only when both before and after canonical diagnostic-family states are fresh. Their absence is not proof of zero diagnostics when a family is stale or deferred. Canonical state remains authoritative; the runtime JSONL trace carries the full committed diagnostic delta for operational evidence.",
+    "Existing syntax failure fields ``error``, ``line_number``, and ``column_number`` remain unchanged."
   ],
   "freshness": [],
   "errors": [
diff --git a/tests/test_live_activity_status.py b/tests/test_live_activity_status.py
index 7f9a9ab..9a09c32 100644
--- a/tests/test_live_activity_status.py
+++ b/tests/test_live_activity_status.py
@@ -179,6 +179,59 @@ def test_background_feed_has_single_poll_owner_and_no_duplicates(live_server_ins
         feed.stop()


+def test_desktop_feed_formats_committed_diagnostic_delta_without_replacing_syntax_message():
+    feed = DesktopLiveEventFeed(SimpleNamespace(), lambda *_args, **_kwargs: None)
+    event = {
+        "operation": "update_file",
+        "status": "SYNTAX_ERROR",
+        "file_path": "pkg/bad.py",
+        "canonical_revision": 12,
+        "error": "invalid syntax",
+        "line_number": 2,
+        "column_number": 3,
+        "diagnostic_changes": {
+            "total": 2,
+            "truncated": False,
+            "items": [
+                {"action": "ADDED", "diagnostic_kind": "syntax", "source_path": "pkg/bad.py", "line_number": 2, "column_number": 3},
+                {"action": "ADDED", "diagnostic_kind": "cycle", "cycle_nodes": ["pkg.a", "pkg.b", "pkg.a"]},
+            ],
+        },
+    }
+
+    message = feed._message(event)
+    assert message == (
+        "[LIVE] Syntax error in bad.py line 2, column 3: invalid syntax; "
+        "cycle added: pkg.a -> pkg.b -> pkg.a"
+    )
+
+
+def test_desktop_feed_formats_generic_diagnostic_delta_and_ignores_malformed_payload():
+    feed = DesktopLiveEventFeed(SimpleNamespace(), lambda *_args, **_kwargs: None)
+    event = {
+        "operation": "update_file",
+        "status": "UPDATED",
+        "file_path": "pkg/change.py",
+        "canonical_revision": 13,
+        "diagnostic_changes": {
+            "total": 4,
+            "truncated": True,
+            "items": [
+                {"action": "ADDED", "diagnostic_kind": "collision", "collision_symbol": "run", "collision_nodes": ["pkg.a", "pkg.b"]},
+                {"action": "RESOLVED", "diagnostic_kind": "cycle", "cycle_nodes": ["pkg.c", "pkg.c"]},
+                {"action": "unknown", "diagnostic_kind": "syntax"},
+            ],
+        },
+    }
+    assert feed._message(event) == (
+        "[LIVE] Diagnostics after change.py (rev 13): collision added: run [pkg.a, pkg.b]; "
+        "cycle resolved: pkg.c -> pkg.c; +1 more"
+    )
+    assert feed._message({**event, "diagnostic_changes": {"items": "bad", "total": 1}}) == (
+        "[LIVE] Watcher updated change.py (rev 13)"
+    )
+
+
 def test_explicit_inactive_repo_never_falls_through_to_other_active_repo(live_server_instance, monkeypatch, tmp_path):
     server_a, client_a = live_server_instance
     repo_a = tmp_path / "repo_a"
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index d47293c..9f00d3d 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -26,6 +26,110 @@ from contextor.core.paths import repo_cache_dir
 pytestmark = pytest.mark.live


+def _diagnostic_state(*, syntax=None, collisions=None, cycles=None, freshness="fresh"):
+    return SimpleNamespace(
+        revision=0,
+        syntax_diagnostics_state=freshness,
+        syntax_diagnostics_by_path={} if syntax is None else syntax,
+        collisions_state=freshness,
+        collisions=[] if collisions is None else collisions,
+        cycles_state=freshness,
+        cycles=[] if cycles is None else cycles,
+    )
+
+
+def test_diagnostic_delta_normalizes_fresh_canonical_families_only():
+    collision = SimpleNamespace(
+        kind="NAME_COLLISION",
+        artifact_type="function",
+        is_identical=False,
+        nodes=["pkg.b", "pkg.a", "pkg.a"],
+        symbol_details=[
+            {"name": "run", "artifact_type": "function"},
+            {"name": "run", "artifact_type": "function"},
+        ],
+    )
+    current = _diagnostic_state(
+        syntax={
+            "pkg/bad.py": {
+                "status": "checked_with_errors",
+                "errors": [
+                    {"message": "invalid syntax", "line_number": 2, "column_number": 4}
+                ],
+            }
+        },
+        collisions=[collision],
+        cycles=[["pkg.a", "pkg.b", "pkg.a"]],
+    )
+    delta = ipc_module._build_diagnostic_delta(_diagnostic_state(), current)
+
+    assert [(item["diagnostic_kind"], item["action"]) for item in delta] == [
+        ("syntax", "ADDED"),
+        ("collision", "ADDED"),
+        ("cycle", "ADDED"),
+    ]
+    assert delta[1]["collision_nodes"] == ["pkg.a", "pkg.b"]
+    assert delta[2]["cycle_nodes"] == ["pkg.a", "pkg.b", "pkg.a"]
+    assert ipc_module._build_diagnostic_delta(
+        _diagnostic_state(freshness="deferred"), current
+    ) == []
+
+
+def test_update_file_publishes_only_committed_bounded_diagnostic_delta(monkeypatch):
+    trace_events = []
+    monkeypatch.setattr(
+        ipc_module,
+        "_safe_trace_event",
+        lambda domain, event, **fields: trace_events.append((domain, event, fields)),
+    )
+    syntax_errors = {
+        f"pkg/bad_{index}.py": {
+            "status": "checked_with_errors",
+            "errors": [
+                {"message": f"bad syntax {index}", "line_number": index + 1, "column_number": 0}
+            ],
+        }
+        for index in range(4)
+    }
+    phases = [syntax_errors, {}]
+
+    def updater(state, _path):
+        state.syntax_diagnostics_by_path = phases.pop(0)
+        return SimpleNamespace(status="UPDATED", file_path="pkg/change.py")
+
+    server = CanonicalLiveServer(_diagnostic_state(), updater=updater)
+    added = server._dispatch(
+        {
+            "operation": "update_file",
+            "file_path": "pkg/change.py",
+            "origin": "desktop_watcher",
+            "diagnostic_changes": {"total": 99, "truncated": False, "items": []},
+        }
+    )
+    assert added["revision"] == 1
+    added_event = server._events[-1]
+    assert added_event["diagnostic_changes"]["total"] == 4
+    assert added_event["diagnostic_changes"]["truncated"] is True
+    assert len(added_event["diagnostic_changes"]["items"]) == 3
+
+    projected = server._dispatch({"operation": "get_events", "after_revision": 0})
+    projected["events"][0]["diagnostic_changes"]["items"][0]["message"] = "mutated"
+    assert server._events[-1]["diagnostic_changes"]["items"][0]["message"] != "mutated"
+
+    resolved = server._dispatch({"operation": "update_file", "file_path": "pkg/change.py"})
+    assert resolved["revision"] == 2
+    assert server._events[-1]["diagnostic_changes"]["total"] == 4
+    assert {event for _domain, event, _fields in trace_events} >= {
+        "LIVE_DIAGNOSTIC_SYNTAX_ERROR",
+        "LIVE_DIAGNOSTIC_SYNTAX_RECOVERED",
+    }
+    assert all(
+        fields["diagnostic_total"] == 4
+        for _domain, event, fields in trace_events
+        if event.startswith("LIVE_DIAGNOSTIC_")
+    )
+
+
 def test_client_request_timeout_closes_connection(monkeypatch):
     sent = []

diff --git a/tests/test_runtime_trace.py b/tests/test_runtime_trace.py
index 6d83d8b..80f7b99 100644
--- a/tests/test_runtime_trace.py
+++ b/tests/test_runtime_trace.py
@@ -51,6 +51,33 @@ def test_desktop_trace_session_headers_and_finish(tmp_path, monkeypatch):
     assert {"LIVE_CONNECT_ATTEMPT", "LIVE_CONNECT_REJECT", "LIVE_CONNECT_RESULT", "LIVE_LIVENESS_RESULT", "LIVE_WATCHER_RECOVERY_START", "LIVE_WATCHER_RECOVERY_RESULT", "LIVE_IPC_FAILURE", "LIVE_SERVICE_THREAD_FAILURE"} <= set(events)


+def test_diagnostic_trace_fields_and_structured_node_arrays_are_durable():
+    path = trace.start_desktop_trace_session()
+    trace.trace_event(
+        "LIVE",
+        "LIVE_DIAGNOSTIC_COLLISION_ADDED",
+        origin="desktop_watcher",
+        diagnostic_kind="collision",
+        diagnostic_key='["collision","run"]',
+        collision_kind="NAME_COLLISION",
+        collision_artifact_type="function",
+        collision_symbol="run",
+        collision_is_identical=False,
+        collision_nodes=["pkg.a", "pkg.b"],
+        diagnostic_total=4,
+        diagnostic_truncated=True,
+    )
+    trace.finish_desktop_trace_session()
+    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
+    fields = records[1]["fields"]
+    events = records[4]["events"]["LIVE"]
+    assert {"origin", "diagnostic_kind", "diagnostic_key", "collision_nodes", "cycle_nodes", "diagnostic_total", "diagnostic_truncated"} <= set(fields)
+    assert {"LIVE_DIAGNOSTIC_SYNTAX_ERROR", "LIVE_DIAGNOSTIC_SYNTAX_RECOVERED", "LIVE_DIAGNOSTIC_COLLISION_ADDED", "LIVE_DIAGNOSTIC_COLLISION_RESOLVED", "LIVE_DIAGNOSTIC_CYCLE_ADDED", "LIVE_DIAGNOSTIC_CYCLE_RESOLVED"} <= set(events)
+    record = next(item for item in records if item.get("ev") == "LIVE_DIAGNOSTIC_COLLISION_ADDED")
+    assert record["collision_nodes"] == ["pkg.a", "pkg.b"]
+    assert record["collision_is_identical"] is False
+
+
 def test_default_trace_session_uses_external_runtime_logs_root(tmp_path, monkeypatch):
     state = tmp_path / "user-state"
     monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(state))

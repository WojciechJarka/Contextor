# CONTEXTOR P1D3-WARN-4J — implementer report

## PREFLIGHT

- DIRECT_EVIDENCE: Initial/final HEAD `68381d98eef79d30038bf0acc6f905a8ef804263`; initial worktree clean.
- DIRECT_EVIDENCE: Contextor MCP pre-edit resolved `contextor.core.live_state.watcher` at revision 879 and reported 16 fresh structural DFS cycles.
- DIRECT_EVIDENCE: All nine specified SEARCH blocks occurred exactly once. The new test file was absent.

## EXACT SEARCH / REPLACE

- DIRECT_EVIDENCE: Applied only the nine architect-authored replacements in `watcher.py` and added the supplied test file with exact content.
- DIRECT_EVIDENCE: Literal new-file comparison passed. No event journal, structural graph, or validator files were changed.

## CURRENT GENERATION VALIDATION

- CODE_PATH_PROVED: The feed queries owner-installed warning projection only when the batch contains a current-revision `update_file` cycle `ADDED` diagnostic.
- CODE_PATH_PROVED: It validates status, binding, authority, revision, epoch, endpoint identity, graph digest, path counts, and partition before accepting model PASS paths.
- CONTRACT_PROVED: T04 rejects mismatched generation/identity and malformed counts or digest. T06 excludes older events from current-generation suppression.

## MODEL_PASS SUPPRESSION

- CONTRACT_PROVED: T01 suppresses only the model PASS cycle in a mixed owner-backed fixture; the UNKNOWN cycle warning remains. T02 suppresses both model PASS additions while retaining the basic watcher update message.
- CODE_PATH_PROVED: Only `cycle` + `ADDED` diagnostic items with an accepted exact path are omitted from presentation details.

## UNKNOWN / UNAVAILABLE FAIL-CLOSED

- CONTRACT_PROVED: T05 retains warnings on owner query timeout. T08 makes no projection query when no cycle addition is present.
- CODE_PATH_PROVED: Missing or invalid projection leaves `accepted_paths=None`, preserving normal diagnostic formatting.

## ORIGINAL EVENT IDENTITY

- CONTRACT_PROVED: T01 checks that the delivered event is the original object and unchanged. T07 retains a `RESOLVED` cycle message; T03 retains syntax error text. T09 checks no change to journal, activity sequence, cycles, or hard edges.

## NEW TEST RESULTS

- `& .\.venv\Scripts\python.exe -m py_compile contextor/core/live_state/watcher.py tests/test_cycle_semantics_desktop_live_event_warning_view.py` — PASS.
- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_desktop_live_event_warning_view.py` — 13 passed.

## FOCUSED REGRESSIONS

- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_live_activity_status.py tests/test_cycle_semantics_live_cycle_warning_query.py tests/test_cycle_semantics_desktop_warning_presentation.py tests/test_cycle_semantics_desktop_full_partial_activation.py` — 88 passed; one third-party Authlib deprecation warning.
- `git diff --check` and new-file `git diff --no-index --check` — no whitespace errors.

## POST-CHANGE MCP AUDIT

- DIRECT_EVIDENCE: An initial MCP read hit transient `Resource deadlock avoided` while watcher synchronization was underway. A later `get_module_context` call at revision 881 reported `canonical_state=fresh` and `workspace_sync=verified` for both changed files.
- DIRECT_EVIDENCE: Graph and cycles fresh; structural DFS cycle count stayed **16**. `cycle_semantics=stale`.
- UNKNOWN: Workspace sync does not establish active Desktop/backend loaded-code adoption.

## FILES_CHANGED

- `contextor/core/live_state/watcher.py`
- `tests/test_cycle_semantics_desktop_live_event_warning_view.py`

`walkthrough.md` overwritten as report only.

## FULL_DIFFS

### contextor/core/live_state/watcher.py

```diff
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index f0cb567..2717420 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -16,6 +16,16 @@ from watchdog.observers import Observer
 from watchdog.observers.polling import PollingObserver
 
 from .ipc import LiveStateClient
+from contextor.core.cycle_semantics.cycle_warning_projection import (
+    InstalledCycleWarningProjection,
+)
+from contextor.core.cycle_semantics.cycle_warning_transitions import (
+    _validated_states,
+)
+from contextor.core.cycle_semantics.live_cycle_warning_query import (
+    _AUTHORITY as _WARNING_AUTHORITY,
+    _BINDING as _WARNING_BINDING,
+)
 
 
 RECOVERY_DEFERRED = object()
@@ -1048,6 +1058,129 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
             return domain, sequence, event_id
         return None
 
+    def _accepted_cycle_paths_for_batch(
+        self,
+        response: object,
+    ) -> frozenset[tuple[str, ...]] | None:
+        """Trust only the owner projection for this event batch generation."""
+        if type(response) is not dict:
+            return None
+
+        revision = response.get("revision")
+        epoch = response.get("activity_epoch")
+        events = response.get("events")
+
+        if (
+            type(revision) is not int
+            or revision < 1
+            or type(epoch) is not str
+            or not epoch
+            or type(events) is not list
+        ):
+            return None
+
+        def has_current_cycle_addition(event: object) -> bool:
+            if (
+                type(event) is not dict
+                or event.get("operation") != "update_file"
+                or type(event.get("canonical_revision")) is not int
+                or event["canonical_revision"] != revision
+            ):
+                return False
+
+            changes = event.get("diagnostic_changes")
+            if type(changes) is not dict:
+                return False
+
+            items = changes.get("items")
+            return (
+                type(items) in (list, tuple)
+                and any(
+                    type(item) is dict
+                    and item.get("diagnostic_kind") == "cycle"
+                    and item.get("action") == "ADDED"
+                    for item in items
+                )
+            )
+
+        if not any(has_current_cycle_addition(event) for event in events):
+            return None
+
+        try:
+            report = self.client.get_installed_cycle_warning_projection()
+        except (
+            OSError, EOFError, ConnectionError, TimeoutError,
+            RuntimeError, AttributeError, TypeError, ValueError,
+        ):
+            return None
+
+        if (
+            type(report) is not dict
+            or report.get("status") != "ok"
+            or report.get("binding_state") != _WARNING_BINDING
+            or report.get("authority") != _WARNING_AUTHORITY
+            or type(report.get("revision")) is not int
+            or report["revision"] != revision
+            or report.get("activity_epoch") != epoch
+            or type(report.get("state_id")) is not str
+            or not report["state_id"]
+        ):
+            return None
+
+        endpoint = getattr(self.client, "endpoint", None)
+
+        for key in (
+            "repo_id",
+            "root_path",
+            "service_instance_id",
+            "process_start_identity",
+        ):
+            expected = getattr(endpoint, key, None)
+            if (
+                type(expected) is not str
+                or not expected
+                or report.get(key) != expected
+            ):
+                return None
+
+        digest = report.get("graph_sha256")
+        if (
+            type(digest) is not str
+            or len(digest) != 64
+            or any(char not in "0123456789abcdef" for char in digest)
+        ):
+            return None
+
+        structural = report.get("structural_paths")
+        accepted = report.get("model_pass_paths")
+        active = report.get("active_warning_paths")
+
+        for count_key, paths in (
+            ("structural_count", structural),
+            ("model_pass_count", accepted),
+            ("active_warning_count", active),
+        ):
+            if (
+                type(paths) is not tuple
+                or type(report.get(count_key)) is not int
+                or report[count_key] != len(paths)
+            ):
+                return None
+
+        projection = InstalledCycleWarningProjection(
+            status="FRESH",
+            reason=None,
+            revision=revision,
+            structural_paths=structural,
+            model_pass_paths=accepted,
+            active_warning_paths=active,
+        )
+
+        if _validated_states(projection) is None:
+            return None
+
+        return frozenset(accepted)
+
     @staticmethod
     def _diagnostic_detail(item: object) -> str | None:
         if not isinstance(item, dict):
@@ -1094,7 +1227,11 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
 
     @classmethod
     def _format_diagnostic_payload(
-        cls, payload: object, *, suppress_syntax: bool = False
+        cls,
+        payload: object,
+        *,
+        suppress_syntax: bool = False,
+        accepted_paths: frozenset[tuple[str, ...]] | None = None,
     ) -> str | None:
         if not isinstance(payload, dict):
             return None
@@ -1111,6 +1248,15 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
         for item in items:
             if suppress_syntax and isinstance(item, dict) and item.get("diagnostic_kind") == "syntax":
                 continue
+            if (
+                accepted_paths is not None
+                and type(item) is dict
+                and item.get("diagnostic_kind") == "cycle"
+                and item.get("action") == "ADDED"
+                and type(item.get("cycle_nodes")) in (list, tuple)
+                and tuple(item["cycle_nodes"]) in accepted_paths
+            ):
+                continue
             detail = cls._diagnostic_detail(item)
             if detail is not None:
                 details.append(detail)
@@ -1118,7 +1264,12 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
             details.append(f"+{total - len(items)} more")
         return "; ".join(details) if details else None
 
-    def _message(self, event: dict) -> str | None:
+    def _message(
+        self,
+        event: dict,
+        *,
+        accepted_paths: frozenset[tuple[str, ...]] | None = None,
+    ) -> str | None:
         category = event.get("category", "LIVE_STATE")
         if category == "AUTHORITY":
             event_type = str(event.get("event_type") or event.get("operation") or "AUTHORITY_EVENT")
@@ -1182,10 +1333,15 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
                 message = None
             if message is not None:
                 details = self._format_diagnostic_payload(
-                    diagnostic_payload, suppress_syntax=True
+                    diagnostic_payload,
+                    suppress_syntax=True,
+                    accepted_paths=accepted_paths,
                 )
                 return f"{message}; {details}" if details else message
-            details = self._format_diagnostic_payload(diagnostic_payload)
+            details = self._format_diagnostic_payload(
+                diagnostic_payload,
+                accepted_paths=accepted_paths,
+            )
             if details:
                 return f"[LIVE] Diagnostics after {file_name} (rev {rev}): {details}"
             elif origin in {"desktop_watcher", "desktop"}:
@@ -1274,6 +1430,9 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
                         pass
 
                 previous_cursor = self._last_seq
+                accepted_paths = self._accepted_cycle_paths_for_batch(
+                    response
+                )
 
                 for event in events:
                     seq = event.get("seq")
@@ -1283,7 +1442,25 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
                         continue
 
                     key = self._authority_key(event) if event.get("category") == "AUTHORITY" else None
-                    message = None if key is not None and key in self._replayed_authority_keys else self._message(event)
+                    event_revision = event.get("canonical_revision")
+                    current_generation = (
+                        accepted_paths is not None
+                        and type(event_revision) is int
+                        and type(response.get("revision")) is int
+                        and event_revision == response["revision"]
+                    )
+                    message = (
+                        None
+                        if key is not None and key in self._replayed_authority_keys
+                        else self._message(
+                            event,
+                            accepted_paths=(
+                                accepted_paths
+                                if current_generation
+                                else None
+                            ),
+                        )
+                    )
                     if message:
                         self._emit_status(message, event)
```

### tests/test_cycle_semantics_desktop_live_event_warning_view.py

```diff
diff --git a/tests/test_cycle_semantics_desktop_live_event_warning_view.py b/tests/test_cycle_semantics_desktop_live_event_warning_view.py
new file mode 100644
index 0000000..9222f6c
--- /dev/null
+++ b/tests/test_cycle_semantics_desktop_live_event_warning_view.py
@@ -0,0 +1,298 @@
+"""WARN-4J: Desktop LIVE feed suppresses only owner-proven cycle additions."""
+
+from __future__ import annotations
+
+import copy
+
+import pytest
+
+from contextor.core.live_state.watcher import DesktopLiveEventFeed
+from tests.test_cycle_semantics_live_installed_partial_claims import (
+    _fixture,
+    _owner,
+)
+from tests.test_original_worker_partial_scc_preparation import (
+    PASS_AND_UNKNOWN,
+    TWO_PASS,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _event(paths, revision, *, status="UPDATED", action="ADDED"):
+    return {
+        "seq": 1,
+        "category": "LIVE_STATE",
+        "operation": "update_file",
+        "origin": "desktop_watcher",
+        "status": status,
+        "file_path": "a.py",
+        "canonical_revision": revision,
+        "diagnostic_changes": {
+            "total": len(paths),
+            "truncated": False,
+            "items": [
+                {
+                    "action": action,
+                    "diagnostic_kind": "cycle",
+                    "cycle_nodes": list(path),
+                }
+                for path in paths
+            ],
+        },
+    }
+
+
+def _feed(client, server, event, *, report=None, report_error=None):
+    response = {
+        "status": "ok",
+        "revision": server._revision,
+        "activity_epoch": server._activity_epoch,
+        "events": [event],
+        "truncated": False,
+    }
+
+    received = []
+    reads = []
+
+    class Adapter:
+        endpoint = client.endpoint
+
+        def get_events(self, **_kwargs):
+            return response
+
+        def get_installed_cycle_warning_projection(self):
+            reads.append(1)
+            if report_error is not None:
+                raise report_error
+            if report is not None:
+                return report
+            return client.get_installed_cycle_warning_projection()
+
+    feed = DesktopLiveEventFeed(
+        Adapter(),
+        lambda message, event=None: received.append(
+            (message, event)
+        ),
+        initial_seq=0,
+    )
+    return feed, received, reads, response
+
+
+def test_t01_mixed_real_owner_suppresses_only_model_pass(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(
+        tmp_path, PASS_AND_UNKNOWN,
+    )
+
+    with _owner(state, metadata) as (server, client):
+        event = _event(state.cycles, metadata.revision)
+        original = copy.deepcopy(event)
+        feed, received, reads, response = _feed(
+            client, server, event,
+        )
+
+        feed.poll_once()
+
+        assert len(reads) == 1
+        assert len(received) == 1
+        message, delivered_event = received[0]
+
+        assert "cycle added: x -> y -> x" in message
+        assert "cycle added: a -> b -> a" not in message
+        assert delivered_event is event
+        assert event == original
+        assert len(state.cycles) == 2
+
+
+def test_t02_two_model_pass_cycles_are_both_suppressed(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        event = _event(state.cycles, metadata.revision)
+        feed, received, reads, response = _feed(
+            client, server, event,
+        )
+
+        feed.poll_once()
+
+        assert len(reads) == 1
+        assert received == [
+            (
+                f"[LIVE] Watcher updated a.py (rev {metadata.revision})",
+                event,
+            ),
+        ]
+
+
+def test_t03_syntax_error_message_survives_suppression(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        event = _event(
+            state.cycles,
+            metadata.revision,
+            status="SYNTAX_ERROR",
+        )
+        event.update({
+            "error": "invalid syntax",
+            "line_number": 2,
+            "column_number": 3,
+        })
+
+        feed, received, reads, response = _feed(
+            client, server, event,
+        )
+
+        feed.poll_once()
+
+        assert len(reads) == 1
+        assert received == [
+            (
+                "[LIVE] Syntax error in a.py line 2, "
+                "column 3: invalid syntax",
+                event,
+            ),
+        ]
+
+
+@pytest.mark.parametrize("mutation", [
+    {"revision": 999},
+    {"activity_epoch": "wrong-epoch"},
+    {"service_instance_id": "foreign-owner"},
+    {"model_pass_count": 0},
+    {"graph_sha256": "invalid"},
+])
+def test_t04_mismatched_generation_or_identity_preserves_warning(
+    tmp_path, isolated_dirs, mutation,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        report = client.get_installed_cycle_warning_projection()
+        report.update(mutation)
+        event = _event(state.cycles[:1], metadata.revision)
+        feed, received, reads, response = _feed(
+            client, server, event, report=report,
+        )
+
+        feed.poll_once()
+
+        assert len(reads) == 1
+        assert len(received) == 1
+        assert "cycle added: a -> b -> a" in received[0][0]
+
+
+def test_t05_unavailable_owner_preserves_original_warning(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        event = _event(state.cycles[:1], metadata.revision)
+        feed, received, reads, response = _feed(
+            client, server, event,
+            report_error=TimeoutError("synthetic timeout"),
+        )
+
+        feed.poll_once()
+
+        assert len(reads) == 1
+        assert "cycle added: a -> b -> a" in received[0][0]
+
+
+def test_t06_older_event_never_uses_latest_projection(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        event = _event(
+            state.cycles[:1], metadata.revision - 1,
+        )
+        feed, received, reads, response = _feed(
+            client, server, event,
+        )
+
+        feed.poll_once()
+
+        assert reads == []
+        assert "cycle added: a -> b -> a" in received[0][0]
+
+
+def test_t07_resolved_cycle_is_not_relabelled_as_model_acceptance(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        event = _event(
+            state.cycles[:1],
+            metadata.revision,
+            action="RESOLVED",
+        )
+        feed, received, reads, response = _feed(
+            client, server, event,
+        )
+
+        feed.poll_once()
+
+        assert reads == []
+        assert "cycle resolved: a -> b -> a" in received[0][0]
+
+
+def test_t08_no_cycle_addition_does_not_query_projection(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        event = _event([], metadata.revision)
+        feed, received, reads, response = _feed(
+            client, server, event,
+        )
+
+        feed.poll_once()
+
+        assert reads == []
+        assert len(received) == 1
+        assert received[0][1] is event
+
+
+def test_t09_current_warning_projection_does_not_change_journal(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(
+        tmp_path, PASS_AND_UNKNOWN,
+    )
+
+    with _owner(state, metadata) as (server, client):
+        event = _event(state.cycles, metadata.revision)
+        before = copy.deepcopy((
+            server._events,
+            server._activity_seq,
+            state.cycles,
+            state.dependency_graph.hard_edges,
+        ))
+
+        feed, received, reads, response = _feed(
+            client, server, event,
+        )
+
+        feed.poll_once()
+
+        assert len(reads) == 1
+        assert (
+            server._events,
+            server._activity_seq,
+            state.cycles,
+            state.dependency_graph.hard_edges,
+        ) == before
```

## CONTRACT_CONFLICTS

None observed in the literal anchors, compilation, or focused tests.

## REMAINING UNKNOWN

- UNKNOWN: Active Desktop/backend loaded-code adoption; no restart was performed.
- UNKNOWN: Global pytest result; prohibited in this stage.
- UNKNOWN: Semantic cycle family remains stale in MCP.

## FINAL IMPLEMENTER OBSERVATION

The literal WARN-4J change passed new and specified focused tests. Structural DFS cycle count remained 16. Architectural acceptance remains with ChatGPT. STOP after WARN-4J.

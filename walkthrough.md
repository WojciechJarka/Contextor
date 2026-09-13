# F2L D1O1 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/live_state/ipc.py`
- `tests/live_state/test_ipc_canonical_query.py`

## PROTOCOL_BUMP_PROOF

`LIVE_PROTOCOL_VERSION == 4` is asserted by the narrow-query transport test.

## NARROW_RESULT_PROOF

A 1,000,000-character state field is absent from the canonical-query response; only the handler result and revision are returned.

## SAME_REVISION_PROOF

The handler receives the identical in-memory state object under the server RLock, and the response returns the matching revision.

## NO_SNAPSHOT_PROOF

The dedicated client method emits exactly one `canonical_query` request and invokes neither snapshot nor a fallback operation.

## FAIL_CLOSED_PROOF

Missing state or handler, invalid query inputs, and handler failure return deterministic errors; failure detail is capped at 500 characters.

## CLIENT_OPERATION_PROOF

The client test records `canonical_query` with the supplied query kind and payload exactly.

## TESTS_RUN

```text
.\.venv\Scripts\python.exe -m pytest -q tests\live_state\test_ipc_canonical_query.py tests\live_state\test_runtime_domain.py tests\live_state\test_runtime_lease.py
47 passed in 11.35s
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/core/live_state/ipc.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 8ce23df..3c5b4c6 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -18,7 +18,7 @@ from typing import Any, Callable, Mapping
 from contextor.core.live_state.runtime_lease import ProcessIdentity
 
 
-LIVE_PROTOCOL_VERSION = 3
+LIVE_PROTOCOL_VERSION = 4
 LIVE_ENDPOINT_SCHEMA_VERSION = 2
 _AUTHORITY_FINGERPRINT_LIMIT = 10_000
 
@@ -678,6 +678,13 @@ class CanonicalLiveServer:
         revision: int | None = None,
         updater: Callable[[Any, str], Any] | None = None,
         persister: Callable[[Any, int], Any] | None = None,
+        canonical_query_handler: (
+            Callable[
+                [Any, str, Mapping[str, Any]],
+                Any,
+            ]
+            | None
+        ) = None,
         authkey: bytes | None = None,
         retention: int = ACTIVITY_EVENT_RETENTION,
         authority_identity: Mapping[str, Any] | None = None,
@@ -724,6 +731,9 @@ class CanonicalLiveServer:
         self._activity_epoch = uuid.uuid4().hex
         self._updater = updater
         self._persister = persister
+        self._canonical_query_handler = (
+            canonical_query_handler
+        )
         self._retention = retention
         self._events: list[dict[str, Any]] = []
         self._authority_event_fingerprints: OrderedDict[tuple[str, int, str], str] = OrderedDict()
@@ -1499,6 +1509,53 @@ class CanonicalLiveServer:
             return self._execute_publish(request)
 
         with self._lock:
+            if operation == "canonical_query":
+                if self._state is None:
+                    return {
+                        "status": "error",
+                        "error": "live_state_unavailable",
+                    }
+                if self._canonical_query_handler is None:
+                    return {
+                        "status": "error",
+                        "error": "canonical_query_unavailable",
+                    }
+
+                query_kind = request.get("query_kind")
+                if (
+                    not isinstance(query_kind, str)
+                    or not query_kind
+                ):
+                    return {
+                        "status": "error",
+                        "error": "invalid_query_kind",
+                    }
+
+                payload = request.get("payload", {})
+                if not isinstance(payload, Mapping):
+                    return {
+                        "status": "error",
+                        "error": "invalid_query_payload",
+                    }
+
+                try:
+                    result = self._canonical_query_handler(
+                        self._state,
+                        query_kind,
+                        dict(payload),
+                    )
+                except Exception as exc:
+                    return {
+                        "status": "error",
+                        "error": "canonical_query_failed",
+                        "detail": str(exc)[:500],
+                    }
+
+                return {
+                    "status": "ok",
+                    "revision": self._revision,
+                    "result": result,
+                }
             if operation == "ping":
                 return {
                     "status": "ok",
@@ -1775,6 +1832,22 @@ class LiveStateClient:
     def snapshot(self) -> dict[str, Any]:
         return self.request("snapshot")
 
+    def canonical_query(
+        self,
+        query_kind: str,
+        *,
+        payload: Mapping[str, Any] | None = None,
+    ) -> dict[str, Any]:
+        return self.request(
+            "canonical_query",
+            query_kind=query_kind,
+            payload=(
+                {}
+                if payload is None
+                else payload
+            ),
+        )
+
     def publish(
         self,
         state: Any,
warning: in the working copy of 'tests/live_state/test_ipc_canonical_query.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/live_state/test_ipc_canonical_query.py b/tests/live_state/test_ipc_canonical_query.py
new file mode 100644
index 0000000..301c900
--- /dev/null
+++ b/tests/live_state/test_ipc_canonical_query.py
@@ -0,0 +1,223 @@
+from types import SimpleNamespace
+
+from contextor.core.live_state.ipc import (
+    LIVE_PROTOCOL_VERSION,
+    CanonicalLiveServer,
+    LiveEndpoint,
+    LiveStateClient,
+)
+
+
+def test_canonical_query_returns_only_narrow_handler_result_from_same_revision():
+    state = SimpleNamespace(
+        revision=7,
+        bulk_blob="x" * 1_000_000,
+    )
+    observed = {}
+
+    def handler(current_state, query_kind, payload):
+        observed["state"] = current_state
+        observed["query_kind"] = query_kind
+        observed["payload"] = payload
+        return {
+            "target": "A17/2",
+            "facts": ["narrow"],
+        }
+
+    server = CanonicalLiveServer(
+        state,
+        revision=7,
+        canonical_query_handler=handler,
+    )
+    try:
+        result = server._dispatch(
+            {
+                "operation": "canonical_query",
+                "query_kind": "symbol_lineage",
+                "payload": {
+                    "symbol": "A17/2",
+                },
+            }
+        )
+    finally:
+        server.close()
+
+    assert LIVE_PROTOCOL_VERSION == 4
+    assert result == {
+        "status": "ok",
+        "revision": 7,
+        "result": {
+            "target": "A17/2",
+            "facts": ["narrow"],
+        },
+    }
+    assert observed["state"] is state
+    assert observed["query_kind"] == (
+        "symbol_lineage"
+    )
+    assert observed["payload"] == {
+        "symbol": "A17/2",
+    }
+    assert "state" not in result
+    assert "bulk_blob" not in repr(result)
+
+
+def test_canonical_query_fails_closed_when_unavailable_or_invalid():
+    state = SimpleNamespace(revision=3)
+
+    no_handler = CanonicalLiveServer(
+        state,
+        revision=3,
+    )
+    try:
+        assert no_handler._dispatch(
+            {
+                "operation": "canonical_query",
+                "query_kind": "symbol_lineage",
+            }
+        ) == {
+            "status": "error",
+            "error": "canonical_query_unavailable",
+        }
+
+        assert no_handler._dispatch(
+            {
+                "operation": "canonical_query",
+                "query_kind": "",
+            }
+        ) == {
+            "status": "error",
+            "error": "canonical_query_unavailable",
+        }
+    finally:
+        no_handler.close()
+
+    server = CanonicalLiveServer(
+        state,
+        revision=3,
+        canonical_query_handler=(
+            lambda *_args: {"ok": True}
+        ),
+    )
+    try:
+        assert server._dispatch(
+            {
+                "operation": "canonical_query",
+                "query_kind": "",
+            }
+        ) == {
+            "status": "error",
+            "error": "invalid_query_kind",
+        }
+        assert server._dispatch(
+            {
+                "operation": "canonical_query",
+                "query_kind": "symbol_lineage",
+                "payload": [],
+            }
+        ) == {
+            "status": "error",
+            "error": "invalid_query_payload",
+        }
+    finally:
+        server.close()
+
+    empty = CanonicalLiveServer(
+        None,
+        canonical_query_handler=(
+            lambda *_args: {"ok": True}
+        ),
+    )
+    try:
+        assert empty._dispatch(
+            {
+                "operation": "canonical_query",
+                "query_kind": "symbol_lineage",
+            }
+        ) == {
+            "status": "error",
+            "error": "live_state_unavailable",
+        }
+    finally:
+        empty.close()
+
+
+def test_canonical_query_handler_failure_is_bounded_and_does_not_expose_state():
+    state = SimpleNamespace(
+        revision=4,
+        secret_bulk="never-return-this",
+    )
+
+    def failing_handler(
+        _state,
+        _query_kind,
+        _payload,
+    ):
+        raise RuntimeError("q" * 1000)
+
+    server = CanonicalLiveServer(
+        state,
+        revision=4,
+        canonical_query_handler=failing_handler,
+    )
+    try:
+        result = server._dispatch(
+            {
+                "operation": "canonical_query",
+                "query_kind": "symbol_lineage",
+            }
+        )
+    finally:
+        server.close()
+
+    assert result["status"] == "error"
+    assert result["error"] == (
+        "canonical_query_failed"
+    )
+    assert len(result["detail"]) == 500
+    assert "state" not in result
+    assert "secret_bulk" not in repr(result)
+
+
+def test_live_state_client_canonical_query_uses_dedicated_operation_only():
+    client = LiveStateClient(
+        LiveEndpoint(
+            "127.0.0.1",
+            1,
+            "00" * 32,
+        )
+    )
+    observed = {}
+
+    def request(operation, **payload):
+        observed["operation"] = operation
+        observed["payload"] = payload
+        return {
+            "status": "ok",
+            "revision": 9,
+            "result": {"narrow": True},
+        }
+
+    client.request = request
+
+    result = client.canonical_query(
+        "symbol_lineage",
+        payload={
+            "symbol": "A17/2",
+        },
+    )
+
+    assert result == {
+        "status": "ok",
+        "revision": 9,
+        "result": {"narrow": True},
+    }
+    assert observed == {
+        "operation": "canonical_query",
+        "payload": {
+            "query_kind": "symbol_lineage",
+            "payload": {
+                "symbol": "A17/2",
+            },
+        },
+    }
```


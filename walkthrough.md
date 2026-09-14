# LIVEL1_CANONICAL_LIVE_PROVENANCE

## STATUS

SUCCESS. Implemented only canonical LIVE-state provenance semantics. No snapshot loader, lineage freshness/materialization, watcher, hydration, transport, or MCP tool behavior changed.

## FILES_CHANGED

- `contextor/core/live_state/ipc.py`
- `tests/live_state/test_ipc_canonical_query.py`
- `tests/live_state/test_runtime_canonical_query.py`

## FOCUSED_TESTS

The requested parent `.venv` path was absent; used the repository interpreter at `.venv\\Scripts\\python.exe`.

`& .\\.venv\\Scripts\\python.exe -m pytest -q tests\\live_state\\test_ipc_canonical_query.py tests\\live_state\\test_runtime_canonical_query.py tests\\analysis\\test_lineage_live_query.py tests\\mcp\\test_runtime_lineage_query.py`

`54 passed in 2.19s`

`git diff --check -- contextor/core/live_state/ipc.py tests/live_state/test_ipc_canonical_query.py tests/live_state/test_runtime_canonical_query.py` passed; only Git LF-to-CRLF warnings were emitted.

## CONTEXTOR_POST_EDIT_EVIDENCE

`contextor.core.live_state.ipc::CanonicalLiveServer._execute_publish` remains the canonical publish owner: after all revision gates it marks the candidate's provenance `live`, assigns `self._state`, sets `self._revision`, and records `CANONICAL_PUBLISH`.

`CanonicalLiveServer._dispatch` still passes exactly `self._state` to its canonical query handler under the server lock. `contextor.core.live_state.runtime::_repository_canonical_query_handler` then passes that same state directly to `query_live_symbol_lineage`.

## RUNTIME_RESTART_REQUIRED

YES. The active LIVE authority process still has the old `ipc.py` loaded. I did not restart it; live runtime output will not show `provenance=live` until the user manually restarts the authority/Desktop process.

## COMMIT_SHA

Not created.

## RAW_GIT_DIFFS

```diff
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 3c5b4c6..25a6ab4 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -436,6 +436,19 @@ def _bind_state_revision(state: Any, revision: int) -> bool:
     return getattr(state, "revision", None) == revision
+
+
+def _mark_live_state_provenance(state: Any) -> None:
+    """Mark state currently owned by CanonicalLiveServer as LIVE-authoritative."""
+    if state is None:
+        return
+    if isinstance(state, dict):
+        state["provenance"] = "live"
+        return
+    try:
+        setattr(state, "provenance", "live")
+    except (AttributeError, TypeError):
+        return
+
+
 def _clone_state_for_update(state: Any) -> Any:
     if state is None:
         raise ValueError("canonical state unavailable")
@@ -704,6 +717,7 @@ class CanonicalLiveServer:
             )
+
         self._state = state
+        _mark_live_state_provenance(self._state)
         state_rev = _extract_state_revision(state)
+
         if isinstance(state_rev, int) and state_rev >= 0:
@@ -1228,6 +1242,7 @@ class CanonicalLiveServer:
                         }
                     state_rev = expected_revision
+
+                _mark_live_state_provenance(state)
                 self._state = state
                 self._revision = state_rev
                 evt = self._record_event("publish", request, category="LIVE_STATE")
diff --git a/tests/live_state/test_ipc_canonical_query.py b/tests/live_state/test_ipc_canonical_query.py
index 301c900..294ebdf 100644
--- a/tests/live_state/test_ipc_canonical_query.py
+++ b/tests/live_state/test_ipc_canonical_query.py
@@ -221,3 +221,56 @@ def test_live_state_client_canonical_query_uses_dedicated_operation_only():
             },
         },
     }
+
+
+def test_publish_rebinds_snapshot_or_missing_provenance_to_live_before_serving():
+    initial = SimpleNamespace(revision=3)
+    server = CanonicalLiveServer(
+        initial,
+        revision=3,
+        canonical_query_handler=(
+            lambda current_state, _query_kind, _payload: current_state.provenance
+        ),
+    )
+    replacement = SimpleNamespace(revision=4, provenance="snapshot")
+    missing_provenance = SimpleNamespace(revision=5)
+    try:
+        published = server._dispatch(
+            {
+                "operation": "publish",
+                "state": replacement,
+                "origin": "desktop_analysis",
+            }
+        )
+        first_query = server._dispatch(
+            {
+                "operation": "canonical_query",
+                "query_kind": "symbol_lineage",
+                "payload": {},
+            }
+        )
+        republished = server._dispatch(
+            {
+                "operation": "publish",
+                "state": missing_provenance,
+                "origin": "desktop_analysis",
+            }
+        )
+        second_query = server._dispatch(
+            {
+                "operation": "canonical_query",
+                "query_kind": "symbol_lineage",
+                "payload": {},
+            }
+        )
+    finally:
+        server.close()
+
+    assert published["status"] == "ok"
+    assert published["revision"] == 4
+    assert replacement.provenance == "live"
+    assert first_query["result"] == "live"
+    assert republished["status"] == "ok"
+    assert republished["revision"] == 5
+    assert missing_provenance.provenance == "live"
+    assert second_query["result"] == "live"
diff --git a/tests/live_state/test_runtime_canonical_query.py b/tests/live_state/test_runtime_canonical_query.py
index 7310fe5..1b34f22 100644
--- a/tests/live_state/test_runtime_canonical_query.py
+++ b/tests/live_state/test_runtime_canonical_query.py
@@ -156,5 +156,6 @@ def test_repository_symbol_lineage_handler_runs_through_canonical_server_without
         "query": "A17/2",
         "sections": ("interface",),
     }
+    assert state.provenance == "live"
     assert "bulk_blob" not in repr(response)
     assert "state" not in response
```

# Walkthrough

## CONTEXTOR LIVE — activity_epoch propagation

### Verdict

```ini
VERDICT=STATIC_PASS
ROOT_CAUSE=CanonicalLiveServer owned one immutable activity epoch, but the read-only get_events dispatcher response omitted it.
EPOCH_OWNER=CanonicalLiveServer._activity_epoch (one value per server instance)
LOSS_POINT=CanonicalLiveServer._dispatch operation=get_events serialized response
IMPLEMENTATION=Added activity_epoch=self._activity_epoch to the existing get_events response; no new generation or mutation.
GET_EVENTS_IPC_ACTIVITY_EPOCH_PRESENT=PASS
GET_EVENTS_CLIENT_ACTIVITY_EPOCH_PRESENT=PASS
SAME_SERVER_EPOCH_STABLE=PASS
EPOCH_OWNER_SINGLE_SOURCE=PASS
FEED_EPOCH_RESET_CONTRACT=PASS
ACTIVITY_SEQ_SEMANTICS_UNCHANGED=PASS
REVISION_SEMANTICS_UNCHANGED=PASS
RESYNC_SEMANTICS_UNCHANGED=PASS
PUBLIC_MCP_CONTRACT_CHANGED=NO
DOCS_CHANGE=NO
```

### Contextor discovery

Contextor MCP resolved the current path as `CanonicalLiveServer._dispatch` in `contextor/core/live_state/ipc.py` → `LiveStateClient.get_events` in the same module → `DesktopLiveEventFeed.poll_once` in `contextor/core/live_state/watcher.py`. LIVE freshness was `fresh`, provenance `live`, canonical revision `5483`, and workspace sync `verified`. Source inspection confirmed the server already owned `_activity_epoch` and the feed already consumed `response.get("activity_epoch")`; only the serialized `get_events` response field was missing.

### Tests

Exact propagation regression (real server/dispatcher/client boundary and same-server stability):

```text
.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py -k "activity_epoch or isolation_preserves_existing_live_service"
1 passed, 46 deselected
```

The existing isolation regression was strengthened with an explicit non-empty epoch assertion.

Existing feed epoch/reset and same-epoch gap contract:

```text
.venv\Scripts\python.exe -m pytest -q tests/test_live_activity_status.py -k "activity_cursor_resets_on_daemon_epoch_change_without_false_gap or activity_gap_is_still_reported_for_real_missing_sequence_in_same_epoch"
2 passed, 35 deselected, 1 warning
```

The file currently collects **47 tests** (`pytest --collect-only -q tests/test_live_state_ipc.py`). The earlier run that emitted only 42 dots was incomplete and was not a result. A fresh complete run now passed all 47:

```text
.venv\Scripts\python.exe -m pytest -q tests/test_live_state_ipc.py
47 passed in 32.69s
```

No watcher-startup gate was needed because the production change is confined to read-only IPC serialization and the feed contract tests passed.

### Complete raw unified diff

```diff
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 4f2879f..25e3592 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -683,6 +683,7 @@ class CanonicalLiveServer:
 
                 return {
                     "status": "ok",
+                    "activity_epoch": self._activity_epoch,
                     "revision": self._revision,
                     "latest_revision": latest_revision,
                     "latest_seq": latest_seq,
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index d3714a7..f510e7a 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -830,6 +830,7 @@ def test_test_live_runtime_isolation_preserves_existing_live_service(
     pid_a = client_a.service_pid
     epoch_a = client_a.get_events().get("activity_epoch")
     try:
+        assert epoch_a
         assert client_a.ping()["status"] == "ok"
         assert endpoint_a.is_file()
```

```ini
FULL_SUITE_RUN_BY_AGENT=NO
FULL_SUITE_PENDING_USER_RUN=YES
FILES_CHANGED=contextor/core/live_state/ipc.py; tests/test_live_state_ipc.py
```

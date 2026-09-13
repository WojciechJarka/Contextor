# F2L D1O3 - LIVE canonical symbol-lineage handler

STATUS: PASS

FILES_CHANGED:
- contextor/core/live_state/runtime.py
- tests/live_state/test_runtime_canonical_query.py
- walkthrough.md (this report; its own diff intentionally excluded)

SERVER_WIRING_PROOF:
run_service() constructs CanonicalLiveServer with canonical_query_handler=_repository_canonical_query_handler immediately after persister.

SINGLE_QUERY_DISPATCH_PROOF:
The handler accepts only query_kind symbol_lineage and calls query_live_symbol_lineage exactly once with the supplied canonical state.

SECTION_NORMALIZATION_PROOF:
Transport list sections are converted to a tuple before the existing core query validates ordering, duplicates, and names.

SAME_STATE_PROOF:
The server-dispatch test passes the exact state object to the handler, returns the marker typed result, and retains outer IPC revision 12.

NO_SNAPSHOT_PROOF:
The handler neither snapshots nor builds an engine; the response contains only the narrow result and no state/bulk_blob.

UNKNOWN_KIND_FAIL_CLOSED_PROOF:
An unsupported query kind raises ValueError before the lineage query is reached. IPC maps handler failures to canonical_query_failed.

TYPED_RESULT_PROOF:
The server response result is the original LiveSymbolLineageQueryResult marker object, not a dictionary or JSON conversion.

TESTS_RUN:
- .\.venv\Scripts\python.exe -m pytest -q tests\live_state\test_runtime_canonical_query.py tests\live_state\test_ipc_canonical_query.py tests\analysis\test_lineage_live_query.py - 42 passed in 1.37s
- .\.venv\Scripts\python.exe -m py_compile contextor\core\live_state\runtime.py tests\live_state\test_runtime_canonical_query.py - passed
- git diff --check -- contextor/core/live_state/runtime.py tests/live_state/test_runtime_canonical_query.py - passed

RUNTIME_RESTART_REQUIRED: YES_BUT_DO_NOT_RESTART_YET.

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/core/live_state/runtime.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 111ef30..76c49b3 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -13,6 +13,9 @@ import time
 from pathlib import Path
 from typing import Any, Mapping

+from contextor.core.lineage_query.live_query import (
+    query_live_symbol_lineage,
+)
 from contextor.core.paths import repo_cache_dir
 from contextor.core.repository_identity import (
     read_repository_identity,
@@ -1030,6 +1033,35 @@ def connect_or_start(
             pass


+def _repository_canonical_query_handler(
+    state: object,
+    query_kind: str,
+    payload: Mapping[str, Any],
+):
+    if query_kind != "symbol_lineage":
+        raise ValueError(
+            f"Unsupported canonical query kind: {query_kind}"
+        )
+    if not isinstance(payload, Mapping):
+        raise TypeError("canonical query payload must be a mapping.")
+
+    query = payload.get("query")
+    if not isinstance(query, str):
+        raise TypeError("symbol_lineage query must be a string.")
+
+    raw_sections = payload.get("sections")
+    if not isinstance(raw_sections, (list, tuple)):
+        raise TypeError(
+            "symbol_lineage sections must be a list or tuple."
+        )
+
+    return query_live_symbol_lineage(
+        state,
+        query,
+        tuple(raw_sections),
+    )
+
+
 def _repository_updater(root: Path, holder: dict[str, object] | None = None):
     identity = require_repository_identity(root)
     cache = repo_cache_dir(root)
@@ -1271,6 +1303,9 @@ def run_service(
             revision=revision,
             updater=_repository_updater(root, adapter_holder),
             persister=_repository_persister(root, adapter_holder),
+            canonical_query_handler=(
+                _repository_canonical_query_handler
+            ),
             mutation_guard=_repository_mutation_guard(root),
             authority_identity=authority_identity,
             desktop_claim=desktop_claim,
warning: in the working copy of 'tests/live_state/test_runtime_canonical_query.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/live_state/test_runtime_canonical_query.py b/tests/live_state/test_runtime_canonical_query.py
new file mode 100644
index 0000000..7310fe5
--- /dev/null
+++ b/tests/live_state/test_runtime_canonical_query.py
@@ -0,0 +1,160 @@
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.live_state import runtime
+from contextor.core.live_state.ipc import (
+    CanonicalLiveServer,
+)
+from contextor.core.lineage_query.live_query import (
+    LiveSymbolLineageQueryResult,
+)
+from contextor.core.lineage_query.service import (
+    LineageTargetResolution,
+)
+
+
+def _marker_result():
+    return LiveSymbolLineageQueryResult(
+        resolution=LineageTargetResolution(
+            status="not_found",
+            query="A17/2",
+        ),
+        state_freshness={"canonical_revision": 12},
+    )
+
+
+def test_repository_canonical_query_handler_routes_symbol_lineage_once_and_normalizes_sections(
+    monkeypatch,
+):
+    state = SimpleNamespace(revision=12, bulk_blob="x" * 1_000_000)
+    marker = _marker_result()
+    observed = {}
+
+    def query_live_symbol_lineage(current_state, query, sections):
+        observed["state"] = current_state
+        observed["query"] = query
+        observed["sections"] = sections
+        return marker
+
+    monkeypatch.setattr(
+        runtime,
+        "query_live_symbol_lineage",
+        query_live_symbol_lineage,
+    )
+
+    result = runtime._repository_canonical_query_handler(
+        state,
+        "symbol_lineage",
+        {"query": "A17/2", "sections": ["state", "interface"]},
+    )
+
+    assert result is marker
+    assert observed == {
+        "state": state,
+        "query": "A17/2",
+        "sections": ("state", "interface"),
+    }
+
+
+def test_repository_canonical_query_handler_rejects_unknown_query_kind_before_lineage_query(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        runtime,
+        "query_live_symbol_lineage",
+        lambda *_args, **_kwargs: (
+            (_ for _ in ()).throw(
+                AssertionError("unknown query kind reached lineage query")
+            )
+        ),
+    )
+
+    with pytest.raises(
+        ValueError,
+        match="Unsupported canonical query kind: other",
+    ):
+        runtime._repository_canonical_query_handler(
+            SimpleNamespace(revision=1),
+            "other",
+            {},
+        )
+
+
+@pytest.mark.parametrize(
+    ("payload", "message"),
+    (
+        ({}, "symbol_lineage query must be a string."),
+        (
+            {"query": "A17/2"},
+            "symbol_lineage sections must be a list or tuple.",
+        ),
+        (
+            {"query": "A17/2", "sections": "state"},
+            "symbol_lineage sections must be a list or tuple.",
+        ),
+    ),
+)
+def test_repository_canonical_query_handler_validates_transport_payload(
+    payload,
+    message,
+):
+    with pytest.raises(TypeError, match=message):
+        runtime._repository_canonical_query_handler(
+            SimpleNamespace(revision=1),
+            "symbol_lineage",
+            payload,
+        )
+
+
+def test_repository_symbol_lineage_handler_runs_through_canonical_server_without_state_response(
+    monkeypatch,
+):
+    state = SimpleNamespace(revision=12, bulk_blob="do-not-return-state")
+    marker = _marker_result()
+    observed = {}
+
+    def query_live_symbol_lineage(current_state, query, sections):
+        observed["state"] = current_state
+        observed["query"] = query
+        observed["sections"] = sections
+        return marker
+
+    monkeypatch.setattr(
+        runtime,
+        "query_live_symbol_lineage",
+        query_live_symbol_lineage,
+    )
+    server = CanonicalLiveServer(
+        state,
+        revision=12,
+        canonical_query_handler=(
+            runtime._repository_canonical_query_handler
+        ),
+    )
+    try:
+        response = server._dispatch(
+            {
+                "operation": "canonical_query",
+                "query_kind": "symbol_lineage",
+                "payload": {
+                    "query": "A17/2",
+                    "sections": ["interface"],
+                },
+            }
+        )
+    finally:
+        server.close()
+
+    assert response == {
+        "status": "ok",
+        "revision": 12,
+        "result": marker,
+    }
+    assert observed == {
+        "state": state,
+        "query": "A17/2",
+        "sections": ("interface",),
+    }
+    assert "bulk_blob" not in repr(response)
+    assert "state" not in response
```

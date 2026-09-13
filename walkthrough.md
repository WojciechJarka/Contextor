# F2L D1O4 - MCP narrow LIVE symbol-lineage seam

STATUS: PASS

FILES_CHANGED:
- contextor/mcp/runtime.py
- tests/mcp/test_runtime_lineage_query.py
- walkthrough.md (report; its own diff excluded)

LIVE_ONLY_PROOF:
Uses only connect(root); absent authority returns canonical_live_unavailable with no snapshot/disk fallback.

SINGLE_CANONICAL_QUERY_PROOF:
After connect, exactly one canonical_query(symbol_lineage) is sent with query and list sections only.

NO_ENGINE_PROOF:
The new seam never calls get_or_init_engine or engine/registry hydration.

NO_SNAPSHOT_PROOF:
No client.snapshot() or client.ping() path exists.

NO_START_PROOF:
No connect_or_start invocation exists; unavailable LIVE fails closed.

REMOTE_ERROR_PROOF:
Non-empty server error codes are preserved and detail is bounded to 500 characters.

REVISION_MATCH_PROOF:
Outer revision must match typed freshness revision and selected metadata revision when selected facts exist.

INVALID_RESULT_PROOF:
Non-typed results and revision mismatches return canonical_query_response_invalid or canonical_query_revision_mismatch.

TESTS_RUN:
- pytest focused set: 46 passed in 2.40s
- py_compile: passed
- git diff --check: passed

RUNTIME_RESTART_REQUIRED: YES_BUT_DO_NOT_RESTART_YET.

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/mcp/runtime.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/runtime.py b/contextor/mcp/runtime.py
index 967b5eb..6a80e69 100644
--- a/contextor/mcp/runtime.py
+++ b/contextor/mcp/runtime.py
@@ -1,6 +1,12 @@
+from collections.abc import Mapping
+from dataclasses import dataclass
 from pathlib import Path
 from typing import Any

+from contextor.core.lineage_query.live_query import (
+    LiveSymbolLineageQueryResult,
+)
+

 _live_engines: dict[str, Any] = {}
 _live_engine_revisions: dict[str, int] = {}
@@ -9,6 +15,82 @@ _live_sessions: dict[str, str] = {}
 _live_journal_revisions: dict[str, int] = {}


+@dataclass(frozen=True)
+class LiveSymbolLineageTransportResult:
+    status: str
+    revision: int | None = None
+    result: LiveSymbolLineageQueryResult | None = None
+    error: str | None = None
+    detail: str | None = None
+
+
+def _bounded_live_query_detail(value: object) -> str | None:
+    if not isinstance(value, str):
+        return None
+    return value[:500]
+
+
+def query_live_symbol_lineage_narrow(
+    root: Path,
+    *,
+    query: str,
+    sections: tuple[str, ...],
+) -> LiveSymbolLineageTransportResult:
+    if not isinstance(root, Path):
+        raise TypeError("root must be a Path.")
+    if not isinstance(query, str):
+        raise TypeError("query must be a string.")
+    if not isinstance(sections, tuple):
+        raise TypeError("sections must be a tuple of section names.")
+    if any(not isinstance(section, str) or not section for section in sections):
+        raise ValueError("sections must contain non-empty strings.")
+
+    from contextor.core.live_state import connect
+    try:
+        client = connect(root)
+    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
+        return LiveSymbolLineageTransportResult(
+            status="error", error="canonical_live_transport_error",
+            detail=_bounded_live_query_detail(str(exc)),
+        )
+    if client is None:
+        return LiveSymbolLineageTransportResult(
+            status="unavailable", error="canonical_live_unavailable"
+        )
+    try:
+        response = client.canonical_query(
+            "symbol_lineage",
+            payload={"query": query, "sections": list(sections)},
+        )
+    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
+        return LiveSymbolLineageTransportResult(
+            status="error", error="canonical_query_transport_error",
+            detail=_bounded_live_query_detail(str(exc)),
+        )
+    if not isinstance(response, Mapping):
+        return LiveSymbolLineageTransportResult(
+            status="error", error="canonical_query_response_invalid"
+        )
+    if response.get("status") != "ok":
+        remote_error = response.get("error")
+        return LiveSymbolLineageTransportResult(
+            status="error",
+            error=remote_error if isinstance(remote_error, str) and remote_error else "canonical_query_failed",
+            detail=_bounded_live_query_detail(response.get("detail")),
+        )
+    revision = response.get("revision")
+    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
+        return LiveSymbolLineageTransportResult(status="error", error="canonical_query_response_invalid")
+    result = response.get("result")
+    if not isinstance(result, LiveSymbolLineageQueryResult):
+        return LiveSymbolLineageTransportResult(status="error", revision=revision, error="canonical_query_response_invalid")
+    if result.state_freshness.get("canonical_revision") != revision:
+        return LiveSymbolLineageTransportResult(status="error", revision=revision, error="canonical_query_revision_mismatch")
+    if result.selected is not None and result.selected.facts.metadata.revision != revision:
+        return LiveSymbolLineageTransportResult(status="error", revision=revision, error="canonical_query_revision_mismatch")
+    return LiveSymbolLineageTransportResult(status="ok", revision=revision, result=result)
+
+
 def publish_live_status(root: Path, message: str) -> None:
     try:
         from contextor.core.live_state import connect
warning: in the working copy of 'tests/mcp/test_runtime_lineage_query.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/mcp/test_runtime_lineage_query.py b/tests/mcp/test_runtime_lineage_query.py
new file mode 100644
index 0000000..76e309d
--- /dev/null
+++ b/tests/mcp/test_runtime_lineage_query.py
@@ -0,0 +1,59 @@
+from pathlib import Path
+
+import pytest
+
+import contextor.core.live_state as live_state
+from contextor.core.lineage_query.live_query import LiveSymbolLineageQueryResult
+from contextor.core.lineage_query.service import LineageTargetResolution
+from contextor.mcp import runtime
+
+
+def _result(revision=12):
+    return LiveSymbolLineageQueryResult(
+        resolution=LineageTargetResolution(status="not_found", query="A17/2"),
+        state_freshness={"canonical_revision": revision},
+    )
+
+
+class _Client:
+    def __init__(self, response): self.response, self.calls = response, []
+    def canonical_query(self, query_kind, *, payload=None):
+        self.calls.append((query_kind, payload)); return self.response
+    def snapshot(self): raise AssertionError("narrow query used snapshot")
+    def ping(self): raise AssertionError("narrow query used ping")
+
+
+def test_narrow_live_symbol_lineage_uses_one_canonical_query_without_snapshot_or_engine(monkeypatch):
+    marker = _result(); client = _Client({"status": "ok", "revision": 12, "result": marker})
+    monkeypatch.setattr(live_state, "connect", lambda _root: client)
+    monkeypatch.setattr(runtime, "get_or_init_engine", lambda *_: (_ for _ in ()).throw(AssertionError("engine")))
+    received = runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=("interface", "state"))
+    assert received.status == "ok" and received.result is marker
+    assert client.calls == [("symbol_lineage", {"query": "A17/2", "sections": ["interface", "state"]})]
+
+
+def test_narrow_live_symbol_lineage_unavailable_and_errors_fail_without_fallback(monkeypatch):
+    monkeypatch.setattr(live_state, "connect", lambda _: None)
+    result = runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=("interface",))
+    assert result.error == "canonical_live_unavailable"
+    client = _Client({"status": "error", "error": "canonical_query_failed", "detail": "x" * 1000})
+    monkeypatch.setattr(live_state, "connect", lambda _: client)
+    result = runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=("interface",))
+    assert result.error == "canonical_query_failed" and result.detail == "x" * 500
+
+
+def test_narrow_live_symbol_lineage_fails_closed_on_invalid_or_mismatched_response(monkeypatch):
+    monkeypatch.setattr(live_state, "connect", lambda _: _Client({"status": "ok", "revision": 13, "result": _result(12)}))
+    result = runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=("interface",))
+    assert result.error == "canonical_query_revision_mismatch" and result.revision == 13
+    monkeypatch.setattr(live_state, "connect", lambda _: _Client({"status": "ok", "revision": 12, "result": {}}))
+    result = runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=("interface",))
+    assert result.error == "canonical_query_response_invalid"
+
+
+def test_narrow_live_symbol_lineage_validates_before_connect(monkeypatch):
+    monkeypatch.setattr(live_state, "connect", lambda _: (_ for _ in ()).throw(AssertionError("connected")))
+    with pytest.raises(TypeError): runtime.query_live_symbol_lineage_narrow("C:/repo", query="A17/2", sections=("interface",))
+    with pytest.raises(TypeError): runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query=1, sections=("interface",))
+    with pytest.raises(TypeError): runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=["interface"])
+    with pytest.raises(ValueError): runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=("",))
```

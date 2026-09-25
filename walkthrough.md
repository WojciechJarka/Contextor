# CPA10M8C2CR_NARROW_CANONICAL_LIVE_DIAGNOSTICS_RETRY

STATUS=PASS

## Scope and implementation

FILES_CHANGED=
C:\Temp\Contextor_Repo\contextor\core\diagnostics_projection.py
C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
C:\Temp\Contextor_Repo\contextor\mcp\runtime.py
C:\Temp\Contextor_Repo\contextor\mcp\diagnostics.py
C:\Temp\Contextor_Repo\tests\mcp\test_live_diagnostics_narrow.py

LIVE_PRE_EDIT_REVISION=1421
LIVE_POST_EDIT_REVISION=1426

CORE_DIAGNOSTICS_PROJECTION_CREATED=YES
CANONICAL_QUERY_DIAGNOSTICS_SUMMARY_ADDED=YES
NARROW_LIVE_DIAGNOSTICS_QUERY_ADDED=YES
DIAGNOSTICS_SUMMARY_USES_CANONICAL_LIVE_FIRST=YES
LIVE_SUCCESS_BYPASSES_CACHE=YES
LIVE_UNAVAILABLE_CACHE_FALLBACK=YES
LIVE_ERROR_FAILS_CLOSED=YES

FULL_SNAPSHOT_USED=NO
GET_OR_INIT_ENGINE_USED=NO
ANALYZE_PROJECT_RUN_COUNT=0
UPDATE_FILE_CALLED=NO
FIX_DESIGNED_BY_AGENT=NO

## Evidence

PRE_EDIT_CONTEXTOR_GATE=PASS

Before editing, Contextor revision 1421 confirmed:

- `_repository_canonical_query_handler` accepted only `symbol_lineage`.
- `diagnostics_summary(root, state=None)` read `mcp_runtime._cached_engine(root)`.
- `query_live_symbol_lineage_narrow` connected through `contextor.core.live_state.connect` and called `client.canonical_query(...)`.
- Both requested new modules were absent from the canonical registry and from disk.
- Existing implementations for all required baseline symbols had `workspace_sync=verified`.

Contextor blast-radius evidence at revision 1421:

- `contextor.core.live_state.runtime`: 18 unique direct consumer modules and 121 downstream modules.
- `contextor.mcp.runtime`: 33 unique direct consumer modules and 50 downstream modules; `_cached_engine` was directly consumed by `contextor.mcp.diagnostics`.
- `contextor.mcp.diagnostics`: 7 unique direct consumer modules and 36 downstream modules. `diagnostics_summary` had 5 direct consumers; the removed local projection had one direct test consumer.
- `query_live_symbol_lineage_narrow` had two direct consumers: `contextor.mcp.tools.get_symbol_lineage` and `tests.mcp.test_runtime_lineage_query`.

The exact projection and regression-test files match the supplied attachment exactly after newline normalization. Static policy checks passed: the diagnostics module imports the core projection, contains no local `diagnostics_summary_for_state` definition, the diagnostics path has none of the forbidden calls, the narrow transport sends only `canonical_query("diagnostics_summary", payload={})`, and the existing `symbol_lineage` handler suffix is unchanged.

## LIVE watcher and freshness

Desktop watcher published the four production files:

- revision 1422: `contextor/core/diagnostics_projection.py` (`UPDATED`)
- revision 1423: `contextor/core/live_state/runtime.py` (`UPDATED`)
- revision 1424: `contextor/mcp/runtime.py` (`UPDATED`)
- revision 1425: `contextor/mcp/diagnostics.py` (`UPDATED`)
- revision 1426: `tests/mcp/test_live_diagnostics_narrow.py` (`UPDATED`)

At revision 1426, `get_file_edit_context` reported `workspace_sync=verified`, fresh syntax diagnostics, and no syntax errors for all five files. The new production module resolved as `contextor.core.diagnostics_projection`, module ID `416/1`.

The watcher briefly reported one duplicate-name collision after revision 1422 while the core projection and old MCP-local projection coexisted; revision 1425 reported that collision resolved after the local definition was removed. The final LIVE summary at revision 1426 reported syntax errors 0, name collisions 0, cycles 0, all fresh.

LIVE_NEW_MODULE_SYNC=verified
LIVE_WORKSPACE_SYNC=verified

## Validation

PY_COMPILE=PASS
TARGETED_TESTS=110 passed, 1 warning in 62.77s
FULL_SUITE_RUN=NO

The one warning was `AuthlibDeprecationWarning` emitted by `fastmcp` during `tests/test_live_state_ipc.py`.

## Runtime and change control

MCP_SERVER_RESTART_REQUIRED=YES
DESKTOP_RUNTIME_RESTART_REQUIRED=YES
CODEX_RESTART_REQUIRED=YES_FOR_MCP_RECONNECT
PROCESS_TERMINATION_PERFORMED=NO
RESTART_PERFORMED=NO
GIT_MUTATION_PERFORMED=NO

`config_jsons/config.toml` was already modified before this task and was not changed. `walkthrough.md` is the report-only file required by the workflow.

## FULL_DIFFS

### contextor/core/diagnostics_projection.py

```diff
diff --git a/contextor/core/diagnostics_projection.py b/contextor/core/diagnostics_projection.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/diagnostics_projection.py
@@ -0,0 +1,184 @@
+"""Pure diagnostic projections from canonical repository state."""
+
+from __future__ import annotations
+
+from typing import Any
+
+
+def _availability(
+    state: Any,
+    family: str,
+    values: Any,
+) -> str:
+    status = getattr(
+        state,
+        f"{family}_state",
+        None,
+    )
+
+    if values is None and status == "fresh":
+        return "unavailable"
+
+    if status in {
+        "fresh",
+        "stale",
+        "deferred",
+        "unavailable",
+    }:
+        return status
+
+    if values is None:
+        return "unavailable"
+
+    return "fresh"
+
+
+def diagnostics_summary_for_state(
+    state: Any,
+) -> dict[str, Any]:
+    """Return canonical diagnostic counts plus freshness."""
+
+    if state is None:
+        unavailable = {
+            "count": None,
+            "availability": "unavailable",
+        }
+
+        return {
+            "syntax_errors": dict(unavailable),
+            "name_collisions": {
+                "count": None,
+                "critical": None,
+                "warning": None,
+                "info": None,
+                "availability": "unavailable",
+            },
+            "cycles": dict(unavailable),
+            "attention_required": False,
+            "availability": {
+                "syntax_errors": "unavailable",
+                "name_collisions": "unavailable",
+                "cycles": "unavailable",
+            },
+        }
+
+    syntax_state = getattr(
+        state,
+        "syntax_diagnostics_state",
+        None,
+    )
+    syntax_facts = getattr(
+        state,
+        "syntax_diagnostics_by_path",
+        None,
+    )
+
+    if (
+        syntax_state == "fresh"
+        and isinstance(syntax_facts, dict)
+    ):
+        syntax_values = sum(
+            isinstance(fact, dict)
+            and fact.get("status")
+            == "checked_with_errors"
+            for fact in syntax_facts.values()
+        )
+        syntax_availability = "fresh"
+
+    elif syntax_state in {
+        "not_materialized",
+        "deferred",
+        "stale",
+        "unavailable",
+    }:
+        syntax_values = None
+        syntax_availability = syntax_state
+
+    else:
+        syntax_values = None
+        syntax_availability = "unavailable"
+
+    collisions = getattr(
+        state,
+        "collisions",
+        None,
+    )
+    cycles = getattr(
+        state,
+        "cycles",
+        None,
+    )
+
+    collision_availability = _availability(
+        state,
+        "collisions",
+        collisions,
+    )
+    cycle_availability = _availability(
+        state,
+        "cycles",
+        cycles,
+    )
+
+    if collision_availability != "fresh":
+        collision_count = None
+        critical = None
+        warning = None
+        info = None
+    else:
+        collision_count = len(
+            collisions or []
+        )
+        critical = None
+        warning = None
+        info = None
+
+    cycle_count = (
+        len(cycles)
+        if cycle_availability == "fresh"
+        else None
+    )
+
+    syntax_issue = (
+        syntax_values
+        if syntax_availability == "fresh"
+        else None
+    )
+
+    attention = any(
+        value is not None and value > 0
+        for value in (
+            syntax_issue,
+            collision_count,
+            cycle_count,
+        )
+    )
+
+    return {
+        "syntax_errors": {
+            "count": syntax_values,
+            "availability": syntax_availability,
+        },
+        "name_collisions": {
+            "count": collision_count,
+            "critical": critical,
+            "warning": warning,
+            "info": info,
+            "availability": collision_availability,
+        },
+        "cycles": {
+            "count": cycle_count,
+            "availability": cycle_availability,
+        },
+        "attention_required": bool(attention),
+        "availability": {
+            "syntax_errors": syntax_availability,
+            "name_collisions": collision_availability,
+            "cycles": cycle_availability,
+        },
+    }
+
+
+__all__ = [
+    "diagnostics_summary_for_state",
+]
```

### contextor/core/live_state/runtime.py

```diff
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index c613dcf..920f866 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -13,6 +13,9 @@ import time
 from pathlib import Path
 from typing import Any, Mapping
 
+from contextor.core.diagnostics_projection import (
+    diagnostics_summary_for_state,
+)
 from contextor.core.lineage_query.live_query import (
     query_live_symbol_lineage,
 )
@@ -1038,6 +1041,16 @@ def _repository_canonical_query_handler(
     query_kind: str,
     payload: Mapping[str, Any],
 ):
+    if query_kind == "diagnostics_summary":
+        if payload:
+            raise ValueError(
+                "diagnostics_summary query payload must be empty."
+            )
+
+        return diagnostics_summary_for_state(
+            state
+        )
+
     if query_kind != "symbol_lineage":
         raise ValueError(
             f"Unsupported canonical query kind: {query_kind}"
```

### contextor/mcp/runtime.py

```diff
diff --git a/contextor/mcp/runtime.py b/contextor/mcp/runtime.py
index 862923d..92cc969 100644
--- a/contextor/mcp/runtime.py
+++ b/contextor/mcp/runtime.py
@@ -28,12 +28,183 @@ class LiveSymbolLineageTransportResult:
     detail: str | None = None
 
 
+@dataclass(frozen=True)
+class LiveDiagnosticsSummaryTransportResult:
+    status: str
+    revision: int | None = None
+    summary: dict[str, Any] | None = None
+    error: str | None = None
+    detail: str | None = None
+
+
 def _bounded_live_query_detail(value: object) -> str | None:
     if not isinstance(value, str):
         return None
     return value[:500]
 
 
+def _valid_live_diagnostics_summary(
+    value: object,
+) -> bool:
+    if not isinstance(value, Mapping):
+        return False
+
+    availability = value.get(
+        "availability"
+    )
+
+    if not isinstance(
+        availability,
+        Mapping,
+    ):
+        return False
+
+    for family in (
+        "syntax_errors",
+        "name_collisions",
+        "cycles",
+    ):
+        if not isinstance(
+            value.get(family),
+            Mapping,
+        ):
+            return False
+
+        if family not in availability:
+            return False
+
+    return (
+        type(
+            value.get(
+                "attention_required"
+            )
+        )
+        is bool
+    )
+
+
+def query_live_diagnostics_summary_narrow(
+    root: Path,
+) -> LiveDiagnosticsSummaryTransportResult:
+    if not isinstance(root, Path):
+        raise TypeError(
+            "root must be a Path."
+        )
+
+    from contextor.core.live_state import connect
+
+    try:
+        client = connect(root)
+    except (
+        OSError,
+        EOFError,
+        ConnectionError,
+        TimeoutError,
+        RuntimeError,
+    ) as exc:
+        return LiveDiagnosticsSummaryTransportResult(
+            status="error",
+            error="canonical_live_transport_error",
+            detail=_bounded_live_query_detail(
+                str(exc)
+            ),
+        )
+
+    if client is None:
+        return LiveDiagnosticsSummaryTransportResult(
+            status="unavailable",
+            error="canonical_live_unavailable",
+        )
+
+    try:
+        response = client.canonical_query(
+            "diagnostics_summary",
+            payload={},
+        )
+    except (
+        OSError,
+        EOFError,
+        ConnectionError,
+        TimeoutError,
+        RuntimeError,
+    ) as exc:
+        return LiveDiagnosticsSummaryTransportResult(
+            status="error",
+            error="canonical_query_transport_error",
+            detail=_bounded_live_query_detail(
+                str(exc)
+            ),
+        )
+
+    if not isinstance(
+        response,
+        Mapping,
+    ):
+        return LiveDiagnosticsSummaryTransportResult(
+            status="error",
+            error="canonical_query_response_invalid",
+        )
+
+    if response.get("status") != "ok":
+        remote_error = response.get(
+            "error"
+        )
+
+        return LiveDiagnosticsSummaryTransportResult(
+            status="error",
+            error=(
+                remote_error
+                if (
+                    isinstance(
+                        remote_error,
+                        str,
+                    )
+                    and remote_error
+                )
+                else "canonical_query_failed"
+            ),
+            detail=_bounded_live_query_detail(
+                response.get("detail")
+            ),
+        )
+
+    revision = response.get(
+        "revision"
+    )
+
+    if (
+        isinstance(revision, bool)
+        or not isinstance(
+            revision,
+            int,
+        )
+        or revision < 0
+    ):
+        return LiveDiagnosticsSummaryTransportResult(
+            status="error",
+            error="canonical_query_response_invalid",
+        )
+
+    result = response.get(
+        "result"
+    )
+
+    if not _valid_live_diagnostics_summary(
+        result
+    ):
+        return LiveDiagnosticsSummaryTransportResult(
+            status="error",
+            revision=revision,
+            error="canonical_query_response_invalid",
+        )
+
+    return LiveDiagnosticsSummaryTransportResult(
+        status="ok",
+        revision=revision,
+        summary=dict(result),
+    )
+
+
 def query_live_symbol_lineage_narrow(
     root: Path,
     *,
```

### contextor/mcp/diagnostics.py

```diff
diff --git a/contextor/mcp/diagnostics.py b/contextor/mcp/diagnostics.py
index cc902b3..7ee0e0c 100644
--- a/contextor/mcp/diagnostics.py
+++ b/contextor/mcp/diagnostics.py
@@ -6,89 +6,14 @@ import json
 from pathlib import Path
 from typing import Any
 
+from contextor.core.diagnostics_projection import (
+    diagnostics_summary_for_state,
+)
 from contextor.mcp import runtime as mcp_runtime
 from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES, guard_large_output
 from contextor.core.analysis.state_manager import canonical_python_source_path
 
 
-def _availability(state: Any, family: str, values: Any) -> str:
-    status = getattr(state, f"{family}_state", None)
-    if values is None and status == "fresh":
-        return "unavailable"
-    if status in {"fresh", "stale", "deferred", "unavailable"}:
-        return status
-    if values is None:
-        return "unavailable"
-    return "fresh"
-
-
-def diagnostics_summary_for_state(state: Any) -> dict[str, Any]:
-    """Return counts plus freshness, never converting unavailable to zero."""
-    if state is None:
-        unavailable = {"count": None, "availability": "unavailable"}
-        return {
-            "syntax_errors": dict(unavailable),
-            "name_collisions": {
-                "count": None, "critical": None, "warning": None, "info": None,
-                "availability": "unavailable",
-            },
-            "cycles": dict(unavailable),
-            "attention_required": False,
-            "availability": {
-                "syntax_errors": "unavailable",
-                "name_collisions": "unavailable",
-                "cycles": "unavailable",
-            },
-        }
-
-    syntax_state = getattr(state, "syntax_diagnostics_state", None)
-    syntax_facts = getattr(state, "syntax_diagnostics_by_path", None)
-    if syntax_state == "fresh" and isinstance(syntax_facts, dict):
-        syntax_values = sum(
-            isinstance(fact, dict) and fact.get("status") == "checked_with_errors"
-            for fact in syntax_facts.values()
-        )
-        syntax_availability = "fresh"
-    elif syntax_state in {"not_materialized", "deferred", "stale", "unavailable"}:
-        syntax_values = None
-        syntax_availability = syntax_state
-    else:
-        syntax_values = None
-        syntax_availability = "unavailable"
-    collisions = getattr(state, "collisions", None)
-    cycles = getattr(state, "cycles", None)
-    collision_availability = _availability(state, "collisions", collisions)
-    cycle_availability = _availability(state, "cycles", cycles)
-    if collision_availability != "fresh":
-        collision_count = critical = warning = info = None
-    else:
-        collision_count = len(collisions or [])
-        critical = warning = info = None
-    cycle_count = len(cycles) if cycle_availability == "fresh" else None
-    syntax_issue = syntax_values if syntax_availability == "fresh" else None
-    attention = any(
-        value is not None and value > 0
-        for value in (syntax_issue, collision_count, cycle_count)
-    )
-    return {
-        "syntax_errors": {"count": syntax_values, "availability": syntax_availability},
-        "name_collisions": {
-            "count": collision_count,
-            "critical": critical,
-            "warning": warning,
-            "info": info,
-            "availability": collision_availability,
-        },
-        "cycles": {"count": cycle_count, "availability": cycle_availability},
-        "attention_required": bool(attention),
-        "availability": {
-            "syntax_errors": syntax_availability,
-            "name_collisions": collision_availability,
-            "cycles": cycle_availability,
-        },
-    }
-
-
 def syntax_diagnostics_for_path(
     state: Any,
     source_path: str,
@@ -158,12 +83,50 @@ def syntax_diagnostics_for_path(
     }
 
 
-def diagnostics_summary(root: Path, state: Any = None) -> dict[str, Any]:
-    if state is None:
-        engine = mcp_runtime._cached_engine(root)
-        state = getattr(engine, "state", None) if engine is not None else None
-    summary = diagnostics_summary_for_state(state)
-    return summary
+def diagnostics_summary(
+    root: Path,
+    state: Any = None,
+) -> dict[str, Any]:
+    if state is not None:
+        return diagnostics_summary_for_state(
+            state
+        )
+
+    live = (
+        mcp_runtime
+        .query_live_diagnostics_summary_narrow(
+            root
+        )
+    )
+
+    if (
+        live.status == "ok"
+        and live.summary is not None
+    ):
+        return live.summary
+
+    if live.status == "unavailable":
+        engine = (
+            mcp_runtime
+            ._cached_engine(root)
+        )
+        cached_state = (
+            getattr(
+                engine,
+                "state",
+                None,
+            )
+            if engine is not None
+            else None
+        )
+
+        return diagnostics_summary_for_state(
+            cached_state
+        )
+
+    return diagnostics_summary_for_state(
+        None
+    )
 
 
 def diagnostics_summary_for_completed_job(summary: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
```

### tests/mcp/test_live_diagnostics_narrow.py

```diff
diff --git a/tests/mcp/test_live_diagnostics_narrow.py b/tests/mcp/test_live_diagnostics_narrow.py
new file mode 100644
--- /dev/null
+++ b/tests/mcp/test_live_diagnostics_narrow.py
@@ -0,0 +1,399 @@
+from __future__ import annotations
+
+from pathlib import Path
+from types import SimpleNamespace
+
+import pytest
+
+import contextor.core.live_state as live_state
+from contextor.core.diagnostics_projection import (
+    diagnostics_summary_for_state,
+)
+from contextor.core.live_state.runtime import (
+    _repository_canonical_query_handler,
+)
+from contextor.mcp import diagnostics as mcp_diagnostics
+from contextor.mcp import runtime as mcp_runtime
+
+
+def _fresh_state():
+    return SimpleNamespace(
+        syntax_diagnostics_state="fresh",
+        syntax_diagnostics_by_path={
+            "a.py": {
+                "status": "checked_and_none",
+                "errors": [],
+            },
+            "b.py": {
+                "status": "checked_with_errors",
+                "errors": [
+                    {
+                        "message": "boom",
+                        "line_number": 1,
+                        "column_number": 1,
+                    }
+                ],
+            },
+        },
+        collisions_state="fresh",
+        collisions=[
+            {
+                "kind": "test",
+            }
+        ],
+        cycles_state="fresh",
+        cycles=[
+            [
+                "a",
+                "b",
+                "a",
+            ]
+        ],
+    )
+
+
+def _fresh_summary():
+    return {
+        "syntax_errors": {
+            "count": 1,
+            "availability": "fresh",
+        },
+        "name_collisions": {
+            "count": 1,
+            "critical": None,
+            "warning": None,
+            "info": None,
+            "availability": "fresh",
+        },
+        "cycles": {
+            "count": 1,
+            "availability": "fresh",
+        },
+        "attention_required": True,
+        "availability": {
+            "syntax_errors": "fresh",
+            "name_collisions": "fresh",
+            "cycles": "fresh",
+        },
+    }
+
+
+def test_core_projection_preserves_existing_summary_contract():
+    assert diagnostics_summary_for_state(
+        _fresh_state()
+    ) == _fresh_summary()
+
+
+def test_live_query_handler_returns_narrow_diagnostics_summary():
+    state = _fresh_state()
+
+    result = (
+        _repository_canonical_query_handler(
+            state,
+            "diagnostics_summary",
+            {},
+        )
+    )
+
+    assert result == _fresh_summary()
+
+
+def test_live_query_handler_rejects_nonempty_diagnostics_payload():
+    with pytest.raises(
+        ValueError,
+        match=(
+            "diagnostics_summary query "
+            "payload must be empty"
+        ),
+    ):
+        _repository_canonical_query_handler(
+            _fresh_state(),
+            "diagnostics_summary",
+            {
+                "unexpected": True,
+            },
+        )
+
+
+def test_narrow_live_diagnostics_query_uses_canonical_query(
+    monkeypatch,
+):
+    expected = _fresh_summary()
+    calls = []
+
+    class FakeClient:
+        def canonical_query(
+            self,
+            query_kind,
+            *,
+            payload,
+        ):
+            calls.append(
+                (
+                    query_kind,
+                    payload,
+                )
+            )
+
+            return {
+                "status": "ok",
+                "revision": 1421,
+                "result": expected,
+            }
+
+    monkeypatch.setattr(
+        live_state,
+        "connect",
+        lambda _root: FakeClient(),
+    )
+
+    result = (
+        mcp_runtime
+        .query_live_diagnostics_summary_narrow(
+            Path(
+                r"C:\Temp\Contextor_Repo"
+            )
+        )
+    )
+
+    assert result.status == "ok"
+    assert result.revision == 1421
+    assert result.summary == expected
+
+    assert calls == [
+        (
+            "diagnostics_summary",
+            {},
+        )
+    ]
+
+
+def test_narrow_live_diagnostics_query_reports_unavailable(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        live_state,
+        "connect",
+        lambda _root: None,
+    )
+
+    result = (
+        mcp_runtime
+        .query_live_diagnostics_summary_narrow(
+            Path(
+                r"C:\Temp\Contextor_Repo"
+            )
+        )
+    )
+
+    assert result.status == "unavailable"
+    assert (
+        result.error
+        == "canonical_live_unavailable"
+    )
+
+
+def test_narrow_live_diagnostics_query_rejects_malformed_result(
+    monkeypatch,
+):
+    class FakeClient:
+        def canonical_query(
+            self,
+            query_kind,
+            *,
+            payload,
+        ):
+            assert (
+                query_kind
+                == "diagnostics_summary"
+            )
+            assert payload == {}
+
+            return {
+                "status": "ok",
+                "revision": 1421,
+                "result": {
+                    "unexpected": True,
+                },
+            }
+
+    monkeypatch.setattr(
+        live_state,
+        "connect",
+        lambda _root: FakeClient(),
+    )
+
+    result = (
+        mcp_runtime
+        .query_live_diagnostics_summary_narrow(
+            Path(
+                r"C:\Temp\Contextor_Repo"
+            )
+        )
+    )
+
+    assert result.status == "error"
+    assert (
+        result.error
+        == "canonical_query_response_invalid"
+    )
+
+
+def test_diagnostics_summary_explicit_state_bypasses_live(
+    monkeypatch,
+):
+    def unexpected_live(_root):
+        raise AssertionError(
+            "LIVE query must not run "
+            "for explicit state"
+        )
+
+    monkeypatch.setattr(
+        mcp_runtime,
+        "query_live_diagnostics_summary_narrow",
+        unexpected_live,
+    )
+
+    assert mcp_diagnostics.diagnostics_summary(
+        Path(
+            r"C:\Temp\Contextor_Repo"
+        ),
+        state=_fresh_state(),
+    ) == _fresh_summary()
+
+
+def test_diagnostics_summary_prefers_canonical_live_over_cache(
+    monkeypatch,
+):
+    expected = _fresh_summary()
+
+    monkeypatch.setattr(
+        mcp_runtime,
+        "query_live_diagnostics_summary_narrow",
+        lambda _root: (
+            mcp_runtime
+            .LiveDiagnosticsSummaryTransportResult(
+                status="ok",
+                revision=1421,
+                summary=expected,
+            )
+        ),
+    )
+
+    def unexpected_cache(_root):
+        raise AssertionError(
+            "cached engine must not be "
+            "read after canonical LIVE success"
+        )
+
+    monkeypatch.setattr(
+        mcp_runtime,
+        "_cached_engine",
+        unexpected_cache,
+    )
+
+    assert mcp_diagnostics.diagnostics_summary(
+        Path(
+            r"C:\Temp\Contextor_Repo"
+        )
+    ) == expected
+
+
+def test_diagnostics_summary_falls_back_to_cache_only_when_live_unavailable(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        mcp_runtime,
+        "query_live_diagnostics_summary_narrow",
+        lambda _root: (
+            mcp_runtime
+            .LiveDiagnosticsSummaryTransportResult(
+                status="unavailable",
+                error=(
+                    "canonical_live_unavailable"
+                ),
+            )
+        ),
+    )
+
+    monkeypatch.setattr(
+        mcp_runtime,
+        "_cached_engine",
+        lambda _root: SimpleNamespace(
+            state=_fresh_state()
+        ),
+    )
+
+    assert mcp_diagnostics.diagnostics_summary(
+        Path(
+            r"C:\Temp\Contextor_Repo"
+        )
+    ) == _fresh_summary()
+
+
+def test_diagnostics_summary_transport_error_fails_closed_without_cache(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        mcp_runtime,
+        "query_live_diagnostics_summary_narrow",
+        lambda _root: (
+            mcp_runtime
+            .LiveDiagnosticsSummaryTransportResult(
+                status="error",
+                error=(
+                    "canonical_query_transport_error"
+                ),
+            )
+        ),
+    )
+
+    def unexpected_cache(_root):
+        raise AssertionError(
+            "transport error must not "
+            "fall back to cached engine"
+        )
+
+    monkeypatch.setattr(
+        mcp_runtime,
+        "_cached_engine",
+        unexpected_cache,
+    )
+
+    result = (
+        mcp_diagnostics
+        .diagnostics_summary(
+            Path(
+                r"C:\Temp\Contextor_Repo"
+            )
+        )
+    )
+
+    assert result[
+        "availability"
+    ] == {
+        "syntax_errors": "unavailable",
+        "name_collisions": "unavailable",
+        "cycles": "unavailable",
+    }
+
+    assert (
+        result["syntax_errors"]["count"]
+        is None
+    )
+    assert (
+        result["name_collisions"]["count"]
+        is None
+    )
+    assert (
+        result["cycles"]["count"]
+        is None
+    )
+
+
+def test_mcp_diagnostics_keeps_projection_binding():
+    assert (
+        mcp_diagnostics
+        .diagnostics_summary_for_state
+        is diagnostics_summary_for_state
+    )
```


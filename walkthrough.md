# D1P1 — get_symbol_lineage MCP adapter

STATUS: success

FILES_CHANGED:
- contextor/mcp/tools/get_symbol_lineage.py
- tests/mcp/tools/test_get_symbol_lineage.py

PLANNER_FIRST_PROOF: The adapter validates representation and output options, then calls plan_symbol_lineage_response before resolving the repository path or making the LIVE query. The parametrized invalid-presentation test makes any LIVE call fail and passes.

SINGLE_NARROW_QUERY_PROOF: The resolved path makes exactly one call to mcp_runtime.query_live_symbol_lineage_narrow with plan.candidate_sections. No engine, snapshot, registry, source, or direct connection path is used.

FETCH_SECTION_CANONICALIZATION_PROOF: The fetch test confirms canonical ("interface", "state") is sent to LIVE while the original public-order tuple ("state", "interface") is preserved for the renderer.

TRANSPORT_ERROR_PROOF: A non-ok D1O4 transport result is mapped to normal MCP error JSON preserving error, bounded detail, and canonical_revision, without renderer invocation.

SEMANTIC_STATUS_PROOF: unavailable, invalid, not_found, and ambiguous retain their distinct semantic statuses; non-resolved responses retain the core-provided state_freshness unchanged.

AMBIGUITY_PROOF: The ambiguous test asserts both exact candidates are returned in core order with no adapter-side selection.

RENDER_DELEGATION_PROOF: Resolved results pass selected facts, owner_names, state_freshness, mode, public requested sections, representation, and allow_large_output directly to render_symbol_lineage_response.

NO_ENGINE_PROOF: The no-engine test replaces get_or_init_engine with an assertion failure; the adapter resolves successfully through the narrow LIVE transport.

TESTS_RUN:
- .\.venv\Scripts\python.exe -m pytest -q tests\mcp\tools\test_get_symbol_lineage.py tests\mcp\test_runtime_lineage_query.py tests\mcp\test_lineage_response.py
  Result: 52 passed in 10.22s
- .\.venv\Scripts\python.exe -m py_compile contextor\mcp\tools\get_symbol_lineage.py tests\mcp\tools\test_get_symbol_lineage.py
  Result: passed
- git diff --check -- contextor/mcp/tools/get_symbol_lineage.py tests/mcp/tools/test_get_symbol_lineage.py
  Result: passed

## ACTUAL_DIFF

```diff
diff --git a/contextor/mcp/tools/get_symbol_lineage.py b/contextor/mcp/tools/get_symbol_lineage.py
new file mode 100644
index 0000000..7a1e171
--- /dev/null
+++ b/contextor/mcp/tools/get_symbol_lineage.py
@@ -0,0 +1,168 @@
+from __future__ import annotations
+
+import json
+from pathlib import Path
+
+from contextor.core.lineage_query.service import (
+    LineageTargetResolution,
+    ResolvedLineageTarget,
+)
+from contextor.mcp import representation as mcp_rep
+from contextor.mcp import runtime as mcp_runtime
+from contextor.mcp.lineage_response import (
+    plan_symbol_lineage_response,
+    render_symbol_lineage_response,
+)
+
+
+def _error(code: str, **details) -> str:
+    return json.dumps(
+        {"status": "error", "error": code, **details},
+        indent=2,
+        ensure_ascii=False,
+    )
+
+
+def _target_payload(target: ResolvedLineageTarget) -> dict:
+    return {
+        "artifact_id": target.artifact_id,
+        "qualified_name": target.qualified_name,
+        "module": target.module_name,
+        "symbol": target.symbol_name,
+        "resolution": target.resolution,
+    }
+
+
+def _resolution_response(
+    resolution: LineageTargetResolution,
+    *,
+    state_freshness: dict[str, object],
+    unavailable_reason: str | None = None,
+) -> str:
+    if resolution.status == "unavailable":
+        return json.dumps(
+            {
+                "status": "unavailable",
+                "symbol": resolution.query,
+                "reason": unavailable_reason,
+                "state_freshness": state_freshness,
+            },
+            indent=2,
+            ensure_ascii=False,
+        )
+    if resolution.status == "invalid":
+        return json.dumps(
+            {
+                "status": "invalid",
+                "error": "exact_symbol_required",
+                "symbol": resolution.query,
+                "expected": "active artifact ID or exact module::symbol identity",
+                "state_freshness": state_freshness,
+            },
+            indent=2,
+            ensure_ascii=False,
+        )
+    if resolution.status == "not_found":
+        return json.dumps(
+            {"status": "not_found", "symbol": resolution.query, "state_freshness": state_freshness},
+            indent=2,
+            ensure_ascii=False,
+        )
+    if resolution.status == "ambiguous":
+        return json.dumps(
+            {
+                "status": "ambiguous",
+                "symbol": resolution.query,
+                "candidates": [_target_payload(candidate) for candidate in resolution.candidates],
+                "state_freshness": state_freshness,
+            },
+            indent=2,
+            ensure_ascii=False,
+        )
+    return _error(
+        "canonical_lineage_resolution_invalid",
+        resolution_status=resolution.status,
+    )
+
+
+def get_symbol_lineage(
+    repo_path: str,
+    symbol: str,
+    mode: str = "auto",
+    sections: list[str] | None = None,
+    representation: str = "auto",
+    allow_large_output: bool = False,
+) -> str:
+    if not isinstance(repo_path, str):
+        return _error("invalid_repo_path", expected="string")
+    if not isinstance(symbol, str):
+        return _error(
+            "invalid_symbol",
+            expected="active artifact ID or exact module::symbol identity",
+        )
+    if sections is not None and not isinstance(sections, list):
+        return _error("invalid_sections", expected="list of section names or null")
+    if not isinstance(representation, str):
+        return _error(
+            "invalid_representation",
+            allowed=sorted(mcp_rep.ALLOWED_REPRESENTATIONS),
+        )
+    normalized_representation = representation.strip().lower()
+    if not mcp_rep.is_supported_representation(normalized_representation):
+        return _error(
+            "invalid_representation",
+            allowed=sorted(mcp_rep.ALLOWED_REPRESENTATIONS),
+        )
+    if not isinstance(allow_large_output, bool):
+        return _error("invalid_allow_large_output")
+
+    requested_sections = None if sections is None else tuple(sections)
+    try:
+        plan = plan_symbol_lineage_response(mode=mode, sections=requested_sections)
+    except (TypeError, ValueError) as exc:
+        return _error("invalid_request", message=str(exc))
+
+    root = Path(repo_path).expanduser().resolve()
+    if not root.is_dir():
+        return _error("repository_not_found", repo_path=str(root))
+
+    transport = mcp_runtime.query_live_symbol_lineage_narrow(
+        root,
+        query=symbol,
+        sections=plan.candidate_sections,
+    )
+    if transport.status != "ok":
+        details = {}
+        if transport.detail is not None:
+            details["detail"] = transport.detail
+        if transport.revision is not None:
+            details["canonical_revision"] = transport.revision
+        return _error(transport.error or "canonical_live_query_failed", **details)
+
+    result = transport.result
+    if result is None:
+        return _error("canonical_query_response_invalid")
+    resolution = result.resolution
+    if resolution.status != "resolved" or resolution.target is None:
+        return _resolution_response(
+            resolution,
+            state_freshness=result.state_freshness,
+            unavailable_reason=result.unavailable_reason,
+        )
+    if result.selected is None:
+        return _error(
+            "canonical_query_response_invalid",
+            message="Resolved lineage target returned no selected facts.",
+        )
+    try:
+        return render_symbol_lineage_response(
+            result.selected,
+            mode=plan.mode,
+            sections=requested_sections,
+            representation=normalized_representation,
+            owner_names=result.owner_names,
+            state_freshness=result.state_freshness,
+            allow_large_output=allow_large_output,
+        )
+    except (TypeError, ValueError) as exc:
+        return _error("lineage_response_failed", message=str(exc))

diff --git a/tests/mcp/tools/test_get_symbol_lineage.py b/tests/mcp/tools/test_get_symbol_lineage.py
new file mode 100644
index 0000000..e5fc4c7
--- /dev/null
+++ b/tests/mcp/tools/test_get_symbol_lineage.py
@@ -0,0 +1,111 @@
+import json
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.lineage_query.live_query import LiveSymbolLineageQueryResult
+from contextor.core.lineage_query.service import (
+    SYMBOL_LINEAGE_SECTION_ORDER,
+    LineageTargetResolution,
+    ResolvedLineageTarget,
+)
+from contextor.mcp import runtime as mcp_runtime
+from contextor.mcp.runtime import LiveSymbolLineageTransportResult
+from contextor.mcp.tools import get_symbol_lineage as tool
+
+
+def _freshness(revision=12):
+    return {"canonical_state": "fresh", "workspace_sync": "unverified", "canonical_revision": revision, "provenance": "live"}
+
+
+def _target(artifact_id="A17/2", qualified_name="pkg.mod::handler"):
+    module_name, symbol_name = qualified_name.split("::", 1)
+    return ResolvedLineageTarget(artifact_id=artifact_id, qualified_name=qualified_name, module_name=module_name, symbol_name=symbol_name, resolution="exact_id")
+
+
+def _transport_result(resolution, *, selected=None, owner_names=None, revision=12, unavailable_reason=None):
+    return LiveSymbolLineageTransportResult(
+        status="ok", revision=revision,
+        result=LiveSymbolLineageQueryResult(resolution=resolution, selected=selected, unavailable_reason=unavailable_reason, owner_names={} if owner_names is None else owner_names, state_freshness=_freshness(revision)),
+    )
+
+
+def test_get_symbol_lineage_auto_plans_before_one_narrow_query_and_delegates_render(tmp_path, monkeypatch):
+    marker, target, observed = SimpleNamespace(), _target(), {}
+    def narrow(root, *, query, sections):
+        observed["narrow"] = {"root": root, "query": query, "sections": sections}
+        return _transport_result(LineageTargetResolution(status="resolved", query="A17/2", target=target), selected=marker, owner_names={"A17/2": "pkg.mod::handler"})
+    def render(selected, **kwargs):
+        observed["render"] = {"selected": selected, **kwargs}
+        return '{"status":"resolved"}'
+    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", narrow)
+    monkeypatch.setattr(tool, "render_symbol_lineage_response", render)
+    result = tool.get_symbol_lineage(str(tmp_path), "A17/2", mode="auto", representation="named")
+    assert json.loads(result) == {"status": "resolved"}
+    assert observed["narrow"] == {"root": tmp_path.resolve(), "query": "A17/2", "sections": SYMBOL_LINEAGE_SECTION_ORDER}
+    assert observed["render"] == {"selected": marker, "mode": "auto", "sections": None, "representation": "named", "owner_names": {"A17/2": "pkg.mod::handler"}, "state_freshness": _freshness(), "allow_large_output": False}
+
+
+def test_get_symbol_lineage_fetch_sends_canonical_section_order_but_preserves_request_for_renderer(tmp_path, monkeypatch):
+    marker, target, observed = SimpleNamespace(), _target(), {}
+    def narrow(_root, *, query, sections):
+        observed["query"], observed["sections"] = query, sections
+        return _transport_result(LineageTargetResolution(status="resolved", query=query, target=target), selected=marker)
+    def render(_selected, **kwargs):
+        observed["render_sections"] = kwargs["sections"]
+        return '{"status":"resolved"}'
+    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", narrow)
+    monkeypatch.setattr(tool, "render_symbol_lineage_response", render)
+    result = tool.get_symbol_lineage(str(tmp_path), "pkg.mod::handler", mode="fetch", sections=["state", "interface"], representation="indexed", allow_large_output=True)
+    assert json.loads(result)["status"] == "resolved"
+    assert observed["sections"] == ("interface", "state")
+    assert observed["render_sections"] == ("state", "interface")
+
+
+@pytest.mark.parametrize(("kwargs", "error"), (({"mode": "bad"}, "invalid_request"), ({"mode": "fetch", "sections": None}, "invalid_request"), ({"mode": "auto", "sections": ["state"]}, "invalid_request"), ({"representation": "other"}, "invalid_representation"), ({"allow_large_output": 1}, "invalid_allow_large_output")))
+def test_get_symbol_lineage_invalid_presentation_request_never_queries_live(tmp_path, monkeypatch, kwargs, error):
+    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("invalid request queried LIVE")))
+    result = json.loads(tool.get_symbol_lineage(str(tmp_path), "A17/2", **kwargs))
+    assert result["status"] == "error"
+    assert result["error"] == error
+
+
+def test_get_symbol_lineage_maps_transport_failure_without_renderer(tmp_path, monkeypatch):
+    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: LiveSymbolLineageTransportResult(status="error", revision=15, error="canonical_query_transport_error", detail="transport-down"))
+    monkeypatch.setattr(tool, "render_symbol_lineage_response", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("transport failure rendered")))
+    result = json.loads(tool.get_symbol_lineage(str(tmp_path), "A17/2"))
+    assert result == {"status": "error", "error": "canonical_query_transport_error", "detail": "transport-down", "canonical_revision": 15}
+
+
+@pytest.mark.parametrize(("resolution", "expected_status"), ((LineageTargetResolution(status="invalid", query="handler"), "invalid"), (LineageTargetResolution(status="not_found", query="A404/1"), "not_found"), (LineageTargetResolution(status="unavailable", query="A17/2"), "unavailable")))
+def test_get_symbol_lineage_preserves_nonresolved_semantic_status_and_freshness(tmp_path, monkeypatch, resolution, expected_status):
+    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: _transport_result(resolution, unavailable_reason="lineage unavailable" if expected_status == "unavailable" else None))
+    monkeypatch.setattr(tool, "render_symbol_lineage_response", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unresolved target rendered")))
+    result = json.loads(tool.get_symbol_lineage(str(tmp_path), resolution.query))
+    assert result["status"] == expected_status
+    assert result["state_freshness"] == _freshness()
+
+
+def test_get_symbol_lineage_preserves_ambiguity_candidates_without_guessing(tmp_path, monkeypatch):
+    first, second = _target("A17/2", "pkg.mod::handler"), _target("A18/1", "pkg.mod::handler")
+    resolution = LineageTargetResolution(status="ambiguous", query="pkg.mod::handler", candidates=(first, second))
+    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: _transport_result(resolution))
+    result = json.loads(tool.get_symbol_lineage(str(tmp_path), "pkg.mod::handler"))
+    assert result["status"] == "ambiguous"
+    assert [candidate["artifact_id"] for candidate in result["candidates"]] == ["A17/2", "A18/1"]
+
+
+def test_get_symbol_lineage_rejects_resolved_result_without_selected_facts(tmp_path, monkeypatch):
+    target = _target()
+    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: _transport_result(LineageTargetResolution(status="resolved", query="A17/2", target=target), selected=None))
+    result = json.loads(tool.get_symbol_lineage(str(tmp_path), "A17/2"))
+    assert result["status"] == "error"
+    assert result["error"] == "canonical_query_response_invalid"
+
+
+def test_get_symbol_lineage_does_not_use_engine_path(tmp_path, monkeypatch):
+    target, marker = _target(), SimpleNamespace()
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("tool hydrated engine")))
+    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: _transport_result(LineageTargetResolution(status="resolved", query="A17/2", target=target), selected=marker))
+    monkeypatch.setattr(tool, "render_symbol_lineage_response", lambda *_args, **_kwargs: '{"status":"resolved"}')
+    assert json.loads(tool.get_symbol_lineage(str(tmp_path), "A17/2"))["status"] == "resolved"
```


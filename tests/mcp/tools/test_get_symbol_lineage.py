import json
from types import SimpleNamespace

import pytest

from contextor.core.lineage_query.live_query import LiveSymbolLineageQueryResult
from contextor.core.lineage_query.service import (
    SYMBOL_LINEAGE_SECTION_ORDER,
    LineageTargetResolution,
    ResolvedLineageTarget,
)
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.runtime import LiveSymbolLineageTransportResult
from contextor.mcp.tools import get_symbol_lineage as tool


def _freshness(revision=12):
    return {"canonical_state": "fresh", "workspace_sync": "unverified", "canonical_revision": revision, "provenance": "live"}


def _target(artifact_id="A17/2", qualified_name="pkg.mod::handler"):
    module_name, symbol_name = qualified_name.split("::", 1)
    return ResolvedLineageTarget(artifact_id=artifact_id, qualified_name=qualified_name, module_name=module_name, symbol_name=symbol_name, resolution="exact_id")


def _transport_result(resolution, *, selected=None, owner_names=None, revision=12, unavailable_reason=None):
    return LiveSymbolLineageTransportResult(
        status="ok", revision=revision,
        result=LiveSymbolLineageQueryResult(resolution=resolution, selected=selected, unavailable_reason=unavailable_reason, owner_names={} if owner_names is None else owner_names, state_freshness=_freshness(revision)),
    )


def test_get_symbol_lineage_auto_plans_before_one_narrow_query_and_delegates_render(tmp_path, monkeypatch):
    marker, target, observed = SimpleNamespace(), _target(), {}
    def narrow(root, *, query, sections):
        observed["narrow"] = {"root": root, "query": query, "sections": sections}
        return _transport_result(LineageTargetResolution(status="resolved", query="A17/2", target=target), selected=marker, owner_names={"A17/2": "pkg.mod::handler"})
    def render(selected, **kwargs):
        observed["render"] = {"selected": selected, **kwargs}
        return '{"status":"resolved"}'
    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", narrow)
    monkeypatch.setattr(tool, "render_symbol_lineage_response", render)
    result = tool.get_symbol_lineage(str(tmp_path), "A17/2", mode="auto", representation="named")
    assert json.loads(result) == {"status": "resolved"}
    assert observed["narrow"] == {"root": tmp_path.resolve(), "query": "A17/2", "sections": SYMBOL_LINEAGE_SECTION_ORDER}
    assert observed["render"] == {"selected": marker, "mode": "auto", "sections": None, "representation": "named", "owner_names": {"A17/2": "pkg.mod::handler"}, "state_freshness": _freshness(), "allow_large_output": False}


def test_get_symbol_lineage_fetch_sends_canonical_section_order_but_preserves_request_for_renderer(tmp_path, monkeypatch):
    marker, target, observed = SimpleNamespace(), _target(), {}
    def narrow(_root, *, query, sections):
        observed["query"], observed["sections"] = query, sections
        return _transport_result(LineageTargetResolution(status="resolved", query=query, target=target), selected=marker)
    def render(_selected, **kwargs):
        observed["render_sections"] = kwargs["sections"]
        return '{"status":"resolved"}'
    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", narrow)
    monkeypatch.setattr(tool, "render_symbol_lineage_response", render)
    result = tool.get_symbol_lineage(str(tmp_path), "pkg.mod::handler", mode="fetch", sections=["state", "interface"], representation="indexed", allow_large_output=True)
    assert json.loads(result)["status"] == "resolved"
    assert observed["sections"] == ("interface", "state")
    assert observed["render_sections"] == ("state", "interface")


@pytest.mark.parametrize(("kwargs", "error"), (({"mode": "bad"}, "invalid_request"), ({"mode": "fetch", "sections": None}, "invalid_request"), ({"mode": "auto", "sections": ["state"]}, "invalid_request"), ({"representation": "other"}, "invalid_representation"), ({"allow_large_output": 1}, "invalid_allow_large_output")))
def test_get_symbol_lineage_invalid_presentation_request_never_queries_live(tmp_path, monkeypatch, kwargs, error):
    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("invalid request queried LIVE")))
    result = json.loads(tool.get_symbol_lineage(str(tmp_path), "A17/2", **kwargs))
    assert result["status"] == "error"
    assert result["error"] == error


def test_get_symbol_lineage_maps_transport_failure_without_renderer(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: LiveSymbolLineageTransportResult(status="error", revision=15, error="canonical_query_transport_error", detail="transport-down"))
    monkeypatch.setattr(tool, "render_symbol_lineage_response", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("transport failure rendered")))
    result = json.loads(tool.get_symbol_lineage(str(tmp_path), "A17/2"))
    assert result == {"status": "error", "error": "canonical_query_transport_error", "detail": "transport-down", "canonical_revision": 15}


@pytest.mark.parametrize(("resolution", "expected_status"), ((LineageTargetResolution(status="invalid", query="handler"), "invalid"), (LineageTargetResolution(status="not_found", query="A404/1"), "not_found"), (LineageTargetResolution(status="unavailable", query="A17/2"), "unavailable")))
def test_get_symbol_lineage_preserves_nonresolved_semantic_status_and_freshness(tmp_path, monkeypatch, resolution, expected_status):
    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: _transport_result(resolution, unavailable_reason="lineage unavailable" if expected_status == "unavailable" else None))
    monkeypatch.setattr(tool, "render_symbol_lineage_response", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unresolved target rendered")))
    result = json.loads(tool.get_symbol_lineage(str(tmp_path), resolution.query))
    assert result["status"] == expected_status
    assert result["state_freshness"] == _freshness()


def test_get_symbol_lineage_preserves_ambiguity_candidates_without_guessing(tmp_path, monkeypatch):
    first, second = _target("A17/2", "pkg.mod::handler"), _target("A18/1", "pkg.mod::handler")
    resolution = LineageTargetResolution(status="ambiguous", query="pkg.mod::handler", candidates=(first, second))
    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: _transport_result(resolution))
    result = json.loads(tool.get_symbol_lineage(str(tmp_path), "pkg.mod::handler"))
    assert result["status"] == "ambiguous"
    assert [candidate["artifact_id"] for candidate in result["candidates"]] == ["A17/2", "A18/1"]


def test_get_symbol_lineage_rejects_resolved_result_without_selected_facts(tmp_path, monkeypatch):
    target = _target()
    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: _transport_result(LineageTargetResolution(status="resolved", query="A17/2", target=target), selected=None))
    result = json.loads(tool.get_symbol_lineage(str(tmp_path), "A17/2"))
    assert result["status"] == "error"
    assert result["error"] == "canonical_query_response_invalid"


def test_get_symbol_lineage_does_not_use_engine_path(tmp_path, monkeypatch):
    target, marker = _target(), SimpleNamespace()
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("tool hydrated engine")))
    monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: _transport_result(LineageTargetResolution(status="resolved", query="A17/2", target=target), selected=marker))
    monkeypatch.setattr(tool, "render_symbol_lineage_response", lambda *_args, **_kwargs: '{"status":"resolved"}')
    assert json.loads(tool.get_symbol_lineage(str(tmp_path), "A17/2"))["status"] == "resolved"

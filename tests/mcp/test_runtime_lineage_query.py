from pathlib import Path

import pytest

import contextor.core.live_state as live_state
from contextor.core.lineage_query.live_query import LiveSymbolLineageQueryResult
from contextor.core.lineage_query.service import LineageTargetResolution
from contextor.mcp import runtime


def _result(revision=12):
    return LiveSymbolLineageQueryResult(
        resolution=LineageTargetResolution(status="not_found", query="A17/2"),
        state_freshness={"canonical_revision": revision},
    )


class _Client:
    def __init__(self, response): self.response, self.calls = response, []
    def canonical_query(self, query_kind, *, payload=None):
        self.calls.append((query_kind, payload)); return self.response
    def snapshot(self): raise AssertionError("narrow query used snapshot")
    def ping(self): raise AssertionError("narrow query used ping")


def test_narrow_live_symbol_lineage_uses_one_canonical_query_without_snapshot_or_engine(monkeypatch):
    marker = _result(); client = _Client({"status": "ok", "revision": 12, "result": marker})
    monkeypatch.setattr(live_state, "connect", lambda _root: client)
    monkeypatch.setattr(runtime, "get_or_init_engine", lambda *_: (_ for _ in ()).throw(AssertionError("engine")))
    received = runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=("interface", "state"))
    assert received.status == "ok" and received.result is marker
    assert client.calls == [("symbol_lineage", {"query": "A17/2", "sections": ["interface", "state"]})]


def test_narrow_live_symbol_lineage_unavailable_and_errors_fail_without_fallback(monkeypatch):
    monkeypatch.setattr(live_state, "connect", lambda _: None)
    result = runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=("interface",))
    assert result.error == "canonical_live_unavailable"
    client = _Client({"status": "error", "error": "canonical_query_failed", "detail": "x" * 1000})
    monkeypatch.setattr(live_state, "connect", lambda _: client)
    result = runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=("interface",))
    assert result.error == "canonical_query_failed" and result.detail == "x" * 500


def test_narrow_live_symbol_lineage_fails_closed_on_invalid_or_mismatched_response(monkeypatch):
    monkeypatch.setattr(live_state, "connect", lambda _: _Client({"status": "ok", "revision": 13, "result": _result(12)}))
    result = runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=("interface",))
    assert result.error == "canonical_query_revision_mismatch" and result.revision == 13
    monkeypatch.setattr(live_state, "connect", lambda _: _Client({"status": "ok", "revision": 12, "result": {}}))
    result = runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=("interface",))
    assert result.error == "canonical_query_response_invalid"


def test_narrow_live_symbol_lineage_validates_before_connect(monkeypatch):
    monkeypatch.setattr(live_state, "connect", lambda _: (_ for _ in ()).throw(AssertionError("connected")))
    with pytest.raises(TypeError): runtime.query_live_symbol_lineage_narrow("C:/repo", query="A17/2", sections=("interface",))
    with pytest.raises(TypeError): runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query=1, sections=("interface",))
    with pytest.raises(TypeError): runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=["interface"])
    with pytest.raises(ValueError): runtime.query_live_symbol_lineage_narrow(Path("C:/repo"), query="A17/2", sections=("",))

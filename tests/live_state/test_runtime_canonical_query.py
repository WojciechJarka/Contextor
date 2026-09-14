from types import SimpleNamespace

import pytest

from contextor.core.live_state import runtime
from contextor.core.live_state.ipc import (
    CanonicalLiveServer,
)
from contextor.core.lineage_query.live_query import (
    LiveSymbolLineageQueryResult,
)
from contextor.core.lineage_query.service import (
    LineageTargetResolution,
)


def _marker_result():
    return LiveSymbolLineageQueryResult(
        resolution=LineageTargetResolution(
            status="not_found",
            query="A17/2",
        ),
        state_freshness={"canonical_revision": 12},
    )


def test_repository_canonical_query_handler_routes_symbol_lineage_once_and_normalizes_sections(
    monkeypatch,
):
    state = SimpleNamespace(revision=12, bulk_blob="x" * 1_000_000)
    marker = _marker_result()
    observed = {}

    def query_live_symbol_lineage(current_state, query, sections):
        observed["state"] = current_state
        observed["query"] = query
        observed["sections"] = sections
        return marker

    monkeypatch.setattr(
        runtime,
        "query_live_symbol_lineage",
        query_live_symbol_lineage,
    )

    result = runtime._repository_canonical_query_handler(
        state,
        "symbol_lineage",
        {"query": "A17/2", "sections": ["state", "interface"]},
    )

    assert result is marker
    assert observed == {
        "state": state,
        "query": "A17/2",
        "sections": ("state", "interface"),
    }


def test_repository_canonical_query_handler_rejects_unknown_query_kind_before_lineage_query(
    monkeypatch,
):
    monkeypatch.setattr(
        runtime,
        "query_live_symbol_lineage",
        lambda *_args, **_kwargs: (
            (_ for _ in ()).throw(
                AssertionError("unknown query kind reached lineage query")
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="Unsupported canonical query kind: other",
    ):
        runtime._repository_canonical_query_handler(
            SimpleNamespace(revision=1),
            "other",
            {},
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        ({}, "symbol_lineage query must be a string."),
        (
            {"query": "A17/2"},
            "symbol_lineage sections must be a list or tuple.",
        ),
        (
            {"query": "A17/2", "sections": "state"},
            "symbol_lineage sections must be a list or tuple.",
        ),
    ),
)
def test_repository_canonical_query_handler_validates_transport_payload(
    payload,
    message,
):
    with pytest.raises(TypeError, match=message):
        runtime._repository_canonical_query_handler(
            SimpleNamespace(revision=1),
            "symbol_lineage",
            payload,
        )


def test_repository_symbol_lineage_handler_runs_through_canonical_server_without_state_response(
    monkeypatch,
):
    state = SimpleNamespace(revision=12, bulk_blob="do-not-return-state")
    marker = _marker_result()
    observed = {}

    def query_live_symbol_lineage(current_state, query, sections):
        observed["state"] = current_state
        observed["query"] = query
        observed["sections"] = sections
        return marker

    monkeypatch.setattr(
        runtime,
        "query_live_symbol_lineage",
        query_live_symbol_lineage,
    )
    server = CanonicalLiveServer(
        state,
        revision=12,
        canonical_query_handler=(
            runtime._repository_canonical_query_handler
        ),
    )
    try:
        response = server._dispatch(
            {
                "operation": "canonical_query",
                "query_kind": "symbol_lineage",
                "payload": {
                    "query": "A17/2",
                    "sections": ["interface"],
                },
            }
        )
    finally:
        server.close()

    assert response == {
        "status": "ok",
        "revision": 12,
        "result": marker,
    }
    assert observed == {
        "state": state,
        "query": "A17/2",
        "sections": ("interface",),
    }
    assert state.provenance == "live"
    assert "bulk_blob" not in repr(response)
    assert "state" not in response

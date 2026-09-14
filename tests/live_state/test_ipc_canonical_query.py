from types import SimpleNamespace

from contextor.core.live_state.ipc import (
    LIVE_PROTOCOL_VERSION,
    CanonicalLiveServer,
    LiveEndpoint,
    LiveStateClient,
)


def test_canonical_query_returns_only_narrow_handler_result_from_same_revision():
    state = SimpleNamespace(
        revision=7,
        bulk_blob="x" * 1_000_000,
    )
    observed = {}

    def handler(current_state, query_kind, payload):
        observed["state"] = current_state
        observed["query_kind"] = query_kind
        observed["payload"] = payload
        return {
            "target": "A17/2",
            "facts": ["narrow"],
        }

    server = CanonicalLiveServer(
        state,
        revision=7,
        canonical_query_handler=handler,
    )
    try:
        result = server._dispatch(
            {
                "operation": "canonical_query",
                "query_kind": "symbol_lineage",
                "payload": {
                    "symbol": "A17/2",
                },
            }
        )
    finally:
        server.close()

    assert LIVE_PROTOCOL_VERSION == 4
    assert result == {
        "status": "ok",
        "revision": 7,
        "result": {
            "target": "A17/2",
            "facts": ["narrow"],
        },
    }
    assert observed["state"] is state
    assert observed["query_kind"] == (
        "symbol_lineage"
    )
    assert observed["payload"] == {
        "symbol": "A17/2",
    }
    assert "state" not in result
    assert "bulk_blob" not in repr(result)


def test_canonical_query_fails_closed_when_unavailable_or_invalid():
    state = SimpleNamespace(revision=3)

    no_handler = CanonicalLiveServer(
        state,
        revision=3,
    )
    try:
        assert no_handler._dispatch(
            {
                "operation": "canonical_query",
                "query_kind": "symbol_lineage",
            }
        ) == {
            "status": "error",
            "error": "canonical_query_unavailable",
        }

        assert no_handler._dispatch(
            {
                "operation": "canonical_query",
                "query_kind": "",
            }
        ) == {
            "status": "error",
            "error": "canonical_query_unavailable",
        }
    finally:
        no_handler.close()

    server = CanonicalLiveServer(
        state,
        revision=3,
        canonical_query_handler=(
            lambda *_args: {"ok": True}
        ),
    )
    try:
        assert server._dispatch(
            {
                "operation": "canonical_query",
                "query_kind": "",
            }
        ) == {
            "status": "error",
            "error": "invalid_query_kind",
        }
        assert server._dispatch(
            {
                "operation": "canonical_query",
                "query_kind": "symbol_lineage",
                "payload": [],
            }
        ) == {
            "status": "error",
            "error": "invalid_query_payload",
        }
    finally:
        server.close()

    empty = CanonicalLiveServer(
        None,
        canonical_query_handler=(
            lambda *_args: {"ok": True}
        ),
    )
    try:
        assert empty._dispatch(
            {
                "operation": "canonical_query",
                "query_kind": "symbol_lineage",
            }
        ) == {
            "status": "error",
            "error": "live_state_unavailable",
        }
    finally:
        empty.close()


def test_canonical_query_handler_failure_is_bounded_and_does_not_expose_state():
    state = SimpleNamespace(
        revision=4,
        secret_bulk="never-return-this",
    )

    def failing_handler(
        _state,
        _query_kind,
        _payload,
    ):
        raise RuntimeError("q" * 1000)

    server = CanonicalLiveServer(
        state,
        revision=4,
        canonical_query_handler=failing_handler,
    )
    try:
        result = server._dispatch(
            {
                "operation": "canonical_query",
                "query_kind": "symbol_lineage",
            }
        )
    finally:
        server.close()

    assert result["status"] == "error"
    assert result["error"] == (
        "canonical_query_failed"
    )
    assert len(result["detail"]) == 500
    assert "state" not in result
    assert "secret_bulk" not in repr(result)


def test_live_state_client_canonical_query_uses_dedicated_operation_only():
    client = LiveStateClient(
        LiveEndpoint(
            "127.0.0.1",
            1,
            "00" * 32,
        )
    )
    observed = {}

    def request(operation, **payload):
        observed["operation"] = operation
        observed["payload"] = payload
        return {
            "status": "ok",
            "revision": 9,
            "result": {"narrow": True},
        }

    client.request = request

    result = client.canonical_query(
        "symbol_lineage",
        payload={
            "symbol": "A17/2",
        },
    )

    assert result == {
        "status": "ok",
        "revision": 9,
        "result": {"narrow": True},
    }
    assert observed == {
        "operation": "canonical_query",
        "payload": {
            "query_kind": "symbol_lineage",
            "payload": {
                "symbol": "A17/2",
            },
        },
    }


def test_publish_rebinds_snapshot_or_missing_provenance_to_live_before_serving():
    initial = SimpleNamespace(revision=3)
    server = CanonicalLiveServer(
        initial,
        revision=3,
        canonical_query_handler=(
            lambda current_state, _query_kind, _payload: current_state.provenance
        ),
    )
    replacement = SimpleNamespace(revision=4, provenance="snapshot")
    missing_provenance = SimpleNamespace(revision=5)
    try:
        published = server._dispatch(
            {
                "operation": "publish",
                "state": replacement,
                "origin": "desktop_analysis",
            }
        )
        first_query = server._dispatch(
            {
                "operation": "canonical_query",
                "query_kind": "symbol_lineage",
                "payload": {},
            }
        )
        republished = server._dispatch(
            {
                "operation": "publish",
                "state": missing_provenance,
                "origin": "desktop_analysis",
            }
        )
        second_query = server._dispatch(
            {
                "operation": "canonical_query",
                "query_kind": "symbol_lineage",
                "payload": {},
            }
        )
    finally:
        server.close()

    assert published["status"] == "ok"
    assert published["revision"] == 4
    assert replacement.provenance == "live"
    assert first_query["result"] == "live"
    assert republished["status"] == "ok"
    assert republished["revision"] == 5
    assert missing_provenance.provenance == "live"
    assert second_query["result"] == "live"

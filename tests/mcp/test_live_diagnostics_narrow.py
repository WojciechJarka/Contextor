from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import contextor.core.live_state as live_state
from contextor.core.diagnostics_projection import (
    diagnostics_summary_for_state,
)
from contextor.core.live_state.runtime import (
    _repository_canonical_query_handler,
)
from contextor.mcp import diagnostics as mcp_diagnostics
from contextor.mcp import runtime as mcp_runtime


def _fresh_state():
    return SimpleNamespace(
        syntax_diagnostics_state="fresh",
        syntax_diagnostics_by_path={
            "a.py": {
                "status": "checked_and_none",
                "errors": [],
            },
            "b.py": {
                "status": "checked_with_errors",
                "errors": [
                    {
                        "message": "boom",
                        "line_number": 1,
                        "column_number": 1,
                    }
                ],
            },
        },
        collisions_state="fresh",
        collisions=[
            {
                "kind": "test",
            }
        ],
        cycles_state="fresh",
        cycles=[
            [
                "a",
                "b",
                "a",
            ]
        ],
    )


def _fresh_summary():
    return {
        "syntax_errors": {
            "count": 1,
            "availability": "fresh",
        },
        "name_collisions": {
            "count": 1,
            "critical": None,
            "warning": None,
            "info": None,
            "availability": "fresh",
        },
        "cycles": {
            "count": 1,
            "availability": "fresh",
        },
        "attention_required": True,
        "availability": {
            "syntax_errors": "fresh",
            "name_collisions": "fresh",
            "cycles": "fresh",
        },
    }


def test_core_projection_preserves_existing_summary_contract():
    assert diagnostics_summary_for_state(
        _fresh_state()
    ) == _fresh_summary()


def test_live_query_handler_returns_narrow_diagnostics_summary():
    state = _fresh_state()

    result = (
        _repository_canonical_query_handler(
            state,
            "diagnostics_summary",
            {},
        )
    )

    assert result == _fresh_summary()


def test_live_query_handler_rejects_nonempty_diagnostics_payload():
    with pytest.raises(
        ValueError,
        match=(
            "diagnostics_summary query "
            "payload must be empty"
        ),
    ):
        _repository_canonical_query_handler(
            _fresh_state(),
            "diagnostics_summary",
            {
                "unexpected": True,
            },
        )


def test_narrow_live_diagnostics_query_uses_canonical_query(
    monkeypatch,
):
    expected = _fresh_summary()
    calls = []

    class FakeClient:
        def canonical_query(
            self,
            query_kind,
            *,
            payload,
        ):
            calls.append(
                (
                    query_kind,
                    payload,
                )
            )

            return {
                "status": "ok",
                "revision": 1421,
                "result": expected,
            }

    monkeypatch.setattr(
        live_state,
        "connect",
        lambda _root: FakeClient(),
    )

    result = (
        mcp_runtime
        .query_live_diagnostics_summary_narrow(
            Path(
                r"C:\Temp\Contextor_Repo"
            )
        )
    )

    assert result.status == "ok"
    assert result.revision == 1421
    assert result.summary == expected

    assert calls == [
        (
            "diagnostics_summary",
            {},
        )
    ]


def test_narrow_live_diagnostics_query_reports_unavailable(
    monkeypatch,
):
    monkeypatch.setattr(
        live_state,
        "connect",
        lambda _root: None,
    )

    result = (
        mcp_runtime
        .query_live_diagnostics_summary_narrow(
            Path(
                r"C:\Temp\Contextor_Repo"
            )
        )
    )

    assert result.status == "unavailable"
    assert (
        result.error
        == "canonical_live_unavailable"
    )


def test_narrow_live_diagnostics_query_rejects_malformed_result(
    monkeypatch,
):
    class FakeClient:
        def canonical_query(
            self,
            query_kind,
            *,
            payload,
        ):
            assert (
                query_kind
                == "diagnostics_summary"
            )
            assert payload == {}

            return {
                "status": "ok",
                "revision": 1421,
                "result": {
                    "unexpected": True,
                },
            }

    monkeypatch.setattr(
        live_state,
        "connect",
        lambda _root: FakeClient(),
    )

    result = (
        mcp_runtime
        .query_live_diagnostics_summary_narrow(
            Path(
                r"C:\Temp\Contextor_Repo"
            )
        )
    )

    assert result.status == "error"
    assert (
        result.error
        == "canonical_query_response_invalid"
    )


def test_diagnostics_summary_explicit_state_bypasses_live(
    monkeypatch,
):
    def unexpected_live(_root):
        raise AssertionError(
            "LIVE query must not run "
            "for explicit state"
        )

    monkeypatch.setattr(
        mcp_runtime,
        "query_live_diagnostics_summary_narrow",
        unexpected_live,
    )

    assert mcp_diagnostics.diagnostics_summary(
        Path(
            r"C:\Temp\Contextor_Repo"
        ),
        state=_fresh_state(),
    ) == _fresh_summary()


def test_diagnostics_summary_prefers_canonical_live_over_cache(
    monkeypatch,
):
    expected = _fresh_summary()

    monkeypatch.setattr(
        mcp_runtime,
        "query_live_diagnostics_summary_narrow",
        lambda _root: (
            mcp_runtime
            .LiveDiagnosticsSummaryTransportResult(
                status="ok",
                revision=1421,
                summary=expected,
            )
        ),
    )

    def unexpected_cache(_root):
        raise AssertionError(
            "cached engine must not be "
            "read after canonical LIVE success"
        )

    monkeypatch.setattr(
        mcp_runtime,
        "_cached_engine",
        unexpected_cache,
    )

    assert mcp_diagnostics.diagnostics_summary(
        Path(
            r"C:\Temp\Contextor_Repo"
        )
    ) == expected


def test_diagnostics_summary_falls_back_to_cache_only_when_live_unavailable(
    monkeypatch,
):
    monkeypatch.setattr(
        mcp_runtime,
        "query_live_diagnostics_summary_narrow",
        lambda _root: (
            mcp_runtime
            .LiveDiagnosticsSummaryTransportResult(
                status="unavailable",
                error=(
                    "canonical_live_unavailable"
                ),
            )
        ),
    )

    monkeypatch.setattr(
        mcp_runtime,
        "_cached_engine",
        lambda _root: SimpleNamespace(
            state=_fresh_state()
        ),
    )

    assert mcp_diagnostics.diagnostics_summary(
        Path(
            r"C:\Temp\Contextor_Repo"
        )
    ) == _fresh_summary()


def test_diagnostics_summary_transport_error_fails_closed_without_cache(
    monkeypatch,
):
    monkeypatch.setattr(
        mcp_runtime,
        "query_live_diagnostics_summary_narrow",
        lambda _root: (
            mcp_runtime
            .LiveDiagnosticsSummaryTransportResult(
                status="error",
                error=(
                    "canonical_query_transport_error"
                ),
            )
        ),
    )

    def unexpected_cache(_root):
        raise AssertionError(
            "transport error must not "
            "fall back to cached engine"
        )

    monkeypatch.setattr(
        mcp_runtime,
        "_cached_engine",
        unexpected_cache,
    )

    result = (
        mcp_diagnostics
        .diagnostics_summary(
            Path(
                r"C:\Temp\Contextor_Repo"
            )
        )
    )

    assert result[
        "availability"
    ] == {
        "syntax_errors": "unavailable",
        "name_collisions": "unavailable",
        "cycles": "unavailable",
    }

    assert (
        result["syntax_errors"]["count"]
        is None
    )
    assert (
        result["name_collisions"]["count"]
        is None
    )
    assert (
        result["cycles"]["count"]
        is None
    )


def test_mcp_diagnostics_keeps_projection_binding():
    assert (
        mcp_diagnostics
        .diagnostics_summary_for_state
        is diagnostics_summary_for_state
    )

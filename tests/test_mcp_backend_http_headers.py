from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import contextor.mcp_backend_http_headers as backend_headers


def test_build_backend_http_headers_starts_or_reuses_ready_backend(
    monkeypatch,
) -> None:
    calls = []

    def fake_start_backend(
        *,
        timeout,
        probe_timeout,
    ):
        calls.append(
            (
                timeout,
                probe_timeout,
            )
        )
        return SimpleNamespace(ready=True)

    monkeypatch.setattr(
        backend_headers,
        "start_backend",
        fake_start_backend,
    )
    monkeypatch.setattr(
        backend_headers,
        "read_backend_token",
        lambda: "test-backend-token",
    )

    assert backend_headers.build_backend_http_headers() == {
        "Authorization": "Bearer test-backend-token",
    }
    assert calls == [
        (
            8.0,
            1.0,
        )
    ]


def test_build_backend_http_headers_rejects_unready_backend(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        backend_headers,
        "start_backend",
        lambda **_kwargs: SimpleNamespace(ready=False),
    )

    with pytest.raises(
        backend_headers.BackendHttpHeadersError,
        match="backend is not ready",
    ):
        backend_headers.build_backend_http_headers()


def test_build_backend_http_headers_rejects_missing_token(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        backend_headers,
        "start_backend",
        lambda **_kwargs: SimpleNamespace(ready=True),
    )
    monkeypatch.setattr(
        backend_headers,
        "read_backend_token",
        lambda: None,
    )

    with pytest.raises(
        backend_headers.BackendHttpHeadersError,
        match="bearer token is unavailable",
    ):
        backend_headers.build_backend_http_headers()


def test_main_emits_exact_json_header_map(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        backend_headers,
        "build_backend_http_headers",
        lambda: {
            "Authorization": "Bearer test-backend-token",
        },
    )

    assert backend_headers.main() == 0

    captured = capsys.readouterr()

    assert captured.err == ""
    assert captured.out == (
        '{"Authorization":"Bearer test-backend-token"}\n'
    )

    assert json.loads(captured.out) == {
        "Authorization": "Bearer test-backend-token",
    }


def test_main_failure_uses_stderr_and_keeps_stdout_empty(
    monkeypatch,
    capsys,
) -> None:
    def fail():
        raise backend_headers.BackendHttpHeadersError(
            "expected test failure"
        )

    monkeypatch.setattr(
        backend_headers,
        "build_backend_http_headers",
        fail,
    )

    assert backend_headers.main() == 1

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == (
        "[ERROR] expected test failure\n"
    )

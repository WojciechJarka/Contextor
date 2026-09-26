from __future__ import annotations

import json

import pytest

import contextor.mcp_backend_http_headers as backend_headers


def test_build_backend_http_headers_uses_credential_only(
    monkeypatch,
) -> None:
    calls = []

    def fake_get_or_create_backend_token():
        calls.append("token")
        return "test-backend-token"

    monkeypatch.setattr(
        backend_headers,
        "get_or_create_backend_token",
        fake_get_or_create_backend_token,
    )

    assert (
        backend_headers
        .build_backend_http_headers()
    ) == {
        "Authorization": (
            "Bearer test-backend-token"
        ),
    }

    assert calls == [
        "token"
    ]


def test_build_backend_http_headers_rejects_missing_token(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        backend_headers,
        "get_or_create_backend_token",
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
            "Authorization": (
                "Bearer test-backend-token"
            ),
        },
    )

    assert backend_headers.main() == 0

    captured = capsys.readouterr()

    assert captured.err == ""
    assert captured.out == (
        '{"Authorization":"Bearer test-backend-token"}\n'
    )

    assert json.loads(
        captured.out
    ) == {
        "Authorization": (
            "Bearer test-backend-token"
        ),
    }


def test_main_failure_uses_stderr_and_keeps_stdout_empty(
    monkeypatch,
    capsys,
) -> None:
    def fail():
        raise (
            backend_headers
            .BackendHttpHeadersError(
                "expected test failure"
            )
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


def test_helper_has_no_backend_lifecycle_import():
    assert not hasattr(
        backend_headers,
        "start_backend",
    )

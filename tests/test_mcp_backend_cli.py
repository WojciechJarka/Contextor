import json

import pytest

import contextor.__main__ as application
import contextor.cli as analysis_cli
import contextor.mcp_backend_cli as backend_cli
from contextor.mcp_backend_control import (
    BackendControlError,
    BackendStatus,
)


def test_backend_cli_start_emits_json_and_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        backend_cli,
        "start_backend",
        lambda: BackendStatus(
            state="running",
            ready=True,
            detail="ready",
            record=None,
        ),
    )

    result = backend_cli.main(["start"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert result == 0
    assert captured.err == ""
    assert payload == {
        "detail": "ready",
        "endpoint": None,
        "instance_id": None,
        "pid": None,
        "ready": True,
        "state": "running",
    }


def test_backend_cli_status_ready_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        backend_cli,
        "get_backend_status",
        lambda: BackendStatus(
            state="running",
            ready=True,
            detail="ready",
            record=None,
        ),
    )

    result = backend_cli.main(["status"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert result == 0
    assert captured.err == ""
    assert payload["ready"] is True


def test_backend_cli_status_not_ready_returns_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        backend_cli,
        "get_backend_status",
        lambda: BackendStatus(
            state="stopped",
            ready=False,
            detail="not running",
            record=None,
        ),
    )

    result = backend_cli.main(["status"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert result == 1
    assert captured.err == ""
    assert payload["ready"] is False
    assert payload["state"] == "stopped"


def test_backend_cli_stop_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        backend_cli,
        "stop_backend",
        lambda: BackendStatus(
            state="stopped",
            ready=False,
            detail="persistent backend stopped",
            record=None,
        ),
    )

    result = backend_cli.main(["stop"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert result == 0
    assert captured.err == ""
    assert payload["state"] == "stopped"


def test_backend_cli_control_error_is_stderr_and_exit_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_start() -> BackendStatus:
        raise BackendControlError("boom")

    monkeypatch.setattr(
        backend_cli,
        "start_backend",
        fail_start,
    )

    result = backend_cli.main(["start"])

    captured = capsys.readouterr()

    assert result == 1
    assert captured.out == ""
    assert "[ERROR] boom" in captured.err


def test_application_main_routes_backend_start_to_backend_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[str]] = []

    def fake_backend_main(
        argv: list[str] | None = None,
    ) -> int:
        captured.append(list(argv or []))
        return 17

    monkeypatch.setattr(
        backend_cli,
        "main",
        fake_backend_main,
    )
    monkeypatch.setattr(
        analysis_cli,
        "main",
        lambda argv=None: pytest.fail(
            "normal CLI must not handle backend start"
        ),
    )

    result = application.main(
        [
            "backend",
            "start",
        ]
    )

    assert result == 17
    assert captured == [["start"]]


def test_application_main_routes_backend_status_with_cli_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[str]] = []

    def fake_backend_main(
        argv: list[str] | None = None,
    ) -> int:
        captured.append(list(argv or []))
        return 19

    monkeypatch.setattr(
        backend_cli,
        "main",
        fake_backend_main,
    )
    monkeypatch.setattr(
        analysis_cli,
        "main",
        lambda argv=None: pytest.fail(
            "normal CLI must not handle backend status"
        ),
    )

    result = application.main(
        [
            "--cli",
            "backend",
            "status",
        ]
    )

    assert result == 19
    assert captured == [["status"]]


def test_application_main_preserves_bare_backend_as_repository_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[str]] = []

    def fake_analysis_main(
        argv: list[str] | None = None,
    ) -> int:
        captured.append(list(argv or []))
        return 23

    monkeypatch.setattr(
        analysis_cli,
        "main",
        fake_analysis_main,
    )
    monkeypatch.setattr(
        backend_cli,
        "main",
        lambda argv=None: pytest.fail(
            "bare backend must remain an analysis path"
        ),
    )

    result = application.main(
        ["backend"]
    )

    assert result == 23
    assert captured == [["backend"]]


def test_application_main_preserves_unrecognized_backend_suffix_for_normal_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[str]] = []

    def fake_analysis_main(
        argv: list[str] | None = None,
    ) -> int:
        captured.append(list(argv or []))
        return 29

    monkeypatch.setattr(
        analysis_cli,
        "main",
        fake_analysis_main,
    )
    monkeypatch.setattr(
        backend_cli,
        "main",
        lambda argv=None: pytest.fail(
            "unknown backend suffix must remain normal CLI input"
        ),
    )

    result = application.main(
        [
            "backend",
            "something-else",
        ]
    )

    assert result == 29
    assert captured == [
        [
            "backend",
            "something-else",
        ]
    ]


def test_backend_cli_does_not_expose_token_fields(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        backend_cli,
        "get_backend_status",
        lambda: BackendStatus(
            state="running",
            ready=True,
            detail="ready",
            record=None,
        ),
    )

    result = backend_cli.main(["status"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert result == 0
    assert set(payload) == {
        "state",
        "ready",
        "detail",
        "endpoint",
        "pid",
        "instance_id",
    }
    assert "token" not in payload
    assert "auth" not in payload
    assert "bearer" not in payload

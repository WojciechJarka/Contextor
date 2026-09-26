from __future__ import annotations

from pathlib import Path
import subprocess
from types import SimpleNamespace

import contextor.mcp_backend_autostart as autostart


def test_backend_autostart_command_uses_pythonw_launcher(
    monkeypatch,
    tmp_path,
) -> None:
    pythonw = (
        tmp_path
        / "Contextor Repo"
        / ".venv"
        / "Scripts"
        / "pythonw.exe"
    )

    pythonw.parent.mkdir(
        parents=True
    )
    pythonw.touch()

    monkeypatch.setattr(
        autostart,
        "_pythonw_path",
        lambda: pythonw,
    )

    assert (
        autostart
        .backend_autostart_command()
    ) == subprocess.list2cmdline(
        [
            str(pythonw),
            "-u",
            "-X",
            "utf8",
            "-m",
            "contextor.mcp_backend_autostart",
            "launch",
        ]
    )


def test_install_backend_autostart_is_verified(
    monkeypatch,
) -> None:
    state = {
        "value": None,
    }

    monkeypatch.setattr(
        autostart,
        "backend_autostart_command",
        lambda: "expected-command",
    )
    monkeypatch.setattr(
        autostart,
        "_read_run_value",
        lambda: state["value"],
    )

    def write(value):
        state["value"] = value

    monkeypatch.setattr(
        autostart,
        "_write_run_value",
        write,
    )

    status = (
        autostart
        .install_backend_autostart()
    )

    assert status.installed is True
    assert status.command_matches is True
    assert (
        status.configured_command
        == "expected-command"
    )


def test_remove_backend_autostart_is_verified(
    monkeypatch,
) -> None:
    state = {
        "value": "expected-command",
    }

    monkeypatch.setattr(
        autostart,
        "backend_autostart_command",
        lambda: "expected-command",
    )
    monkeypatch.setattr(
        autostart,
        "_read_run_value",
        lambda: state["value"],
    )

    def delete():
        existed = (
            state["value"]
            is not None
        )
        state["value"] = None
        return existed

    monkeypatch.setattr(
        autostart,
        "_delete_run_value",
        delete,
    )

    status = (
        autostart
        .remove_backend_autostart()
    )

    assert status.installed is False
    assert status.command_matches is False
    assert status.configured_command is None


def test_launch_backend_autostart_uses_existing_lifecycle(
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

        return SimpleNamespace(
            ready=True
        )

    monkeypatch.setattr(
        autostart,
        "start_backend",
        fake_start_backend,
    )

    assert (
        autostart
        .launch_backend_autostart()
        is True
    )

    assert calls == [
        (
            120.0,
            2.0,
        )
    ]


def test_launch_backend_autostart_failure_is_bounded(
    monkeypatch,
) -> None:
    def fail(**_kwargs):
        raise (
            autostart
            .BackendControlError(
                "expected failure"
            )
        )

    monkeypatch.setattr(
        autostart,
        "start_backend",
        fail,
    )

    assert (
        autostart
        .launch_backend_autostart()
        is False
    )


def test_launch_command_is_silent(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        autostart,
        "launch_backend_autostart",
        lambda: True,
    )

    assert (
        autostart.main(
            ["launch"]
        )
        == 0
    )

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == ""

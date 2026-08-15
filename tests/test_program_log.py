"""The optional CMD view must tail the process-wide desktop log."""

import io
from types import SimpleNamespace

import pytest

from contextor.core import program_log
from contextor.core import program_log_tail


def test_tee_stream_mirrors_stdout_and_program_log():
    original = io.StringIO()
    log = io.StringIO()
    stream = program_log._TeeStream(original, log)

    stream.write("whole program event\n")
    stream.flush()

    assert original.getvalue() == "whole program event\n"
    assert log.getvalue() == "whole program event\n"


def test_open_cmd_log_creates_only_one_visible_tail_process(monkeypatch, tmp_path):
    calls = []
    process = SimpleNamespace(poll=lambda: None)

    monkeypatch.setattr(program_log.sys, "platform", "win32")
    monkeypatch.setattr(program_log, "configure_program_log", lambda: tmp_path / "program.log")
    monkeypatch.setattr(program_log.subprocess, "CREATE_NEW_CONSOLE", 16, raising=False)
    monkeypatch.setattr(
        program_log.subprocess,
        "Popen",
        lambda arguments, **kwargs: calls.append((arguments, kwargs)) or process,
    )
    monkeypatch.setattr(program_log, "_CMD_PROCESS", None)

    assert program_log.open_cmd_log() is True
    assert program_log.open_cmd_log() is True

    assert len(calls) == 1
    arguments, kwargs = calls[0]
    assert arguments[:3] == ["cmd.exe", "/d", "/k"]
    assert "contextor.core.program_log_tail" in arguments[3]
    assert "powershell" not in arguments[3].lower()
    assert kwargs["creationflags"] == 16
    assert "stdout" not in kwargs
    assert "stderr" not in kwargs


def test_program_event_is_structured_and_low_volume(monkeypatch):
    log = io.StringIO()
    monkeypatch.setattr(program_log, "_HANDLE", log)

    program_log.log_program_event("GRAPH", "analytics complete", modules=12)

    output = log.getvalue()
    assert "[GRAPH] analytics complete" in output
    assert "modules=12" in output


def test_program_log_tail_prints_existing_lines(monkeypatch, tmp_path, capsys):
    path = tmp_path / "program.log"
    path.write_text("first\nsecond\n", encoding="utf-8")
    monkeypatch.setattr(
        program_log_tail.time,
        "sleep",
        lambda _interval: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    with pytest.raises(KeyboardInterrupt):
        program_log_tail.follow(path, initial_lines=1)

    assert capsys.readouterr().out == "second\n"

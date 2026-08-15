"""Desktop Git probes must never flash helper console windows on Windows."""

from types import SimpleNamespace

from contextor.core.analysis import git_context
from contextor.core.git import repo_state


def test_repo_state_git_process_is_hidden_on_windows(monkeypatch, tmp_path):
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(stdout="true\n")

    monkeypatch.setattr(repo_state.os, "name", "nt")
    monkeypatch.setattr(repo_state.subprocess, "CREATE_NO_WINDOW", 8, raising=False)
    monkeypatch.setattr(repo_state.subprocess, "run", fake_run)

    assert repo_state._run_git(["status"], str(tmp_path)) == "true"
    assert captured["creationflags"] == 8
    assert captured["startupinfo"].wShowWindow == repo_state.subprocess.SW_HIDE


def test_parallel_git_context_process_is_hidden_on_windows(monkeypatch, tmp_path):
    captured = {}

    class FakeProcess:
        pid = 123
        returncode = 0

        def communicate(self):
            return "value\n", ""

    def fake_popen(*args, **kwargs):
        captured.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(git_context.os, "name", "nt")
    monkeypatch.setattr(git_context.subprocess, "CREATE_NO_WINDOW", 8, raising=False)
    monkeypatch.setattr(git_context.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(git_context.shutil, "which", lambda _name: "git.exe")

    assert git_context._run_git(["status"], str(tmp_path)) == "value"
    assert captured["creationflags"] == 8
    assert captured["startupinfo"].wShowWindow == git_context.subprocess.SW_HIDE

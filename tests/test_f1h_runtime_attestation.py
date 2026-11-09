import builtins
import json
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from contextor.core.cycle_semantics import package_model
from contextor.core.runtime_trace import capture_trace_events
from contextor.ui import gui


def _attestation_event():
    with capture_trace_events() as events:
        gui._emit_f1h_runtime_attestation()
    matches = [
        event for event in events
        if event["ev"] == "F1H_LOADED_CODE_ATTESTATION"
    ]
    assert len(matches) == 1
    return matches[0], json.loads(matches[0]["result"])


def test_current_loaded_code_matches_both_typing_guard_forms_without_importing_pkg(
    monkeypatch,
):
    original_import = builtins.__import__
    attempted = []

    def guarded_import(name, *args, **kwargs):
        if name == "pkg" or name.startswith("pkg."):
            attempted.append(name)
            raise AssertionError("analyzed import was executed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    event, result = _attestation_event()

    assert event["d"] == "GUI"
    assert event["status"] == "MATCH"
    assert result["loaded_sha256"] == result["source_sha256"]
    assert len(result["loaded_sha256"]) == 64
    assert result["NAME"] == ["FROM", "UNMODELED_STATEMENT"]
    assert result["ATTRIBUTE"] == ["IMPORT", "UNMODELED_STATEMENT"]
    assert not attempted


def test_different_loaded_code_object_is_mismatch(monkeypatch):
    def substituted(*args, **kwargs):
        return ()

    monkeypatch.setattr(package_model, "_compile", substituted)
    event, result = _attestation_event()

    assert event["status"] == "MISMATCH"
    assert result["loaded_sha256"] != result["source_sha256"]


def test_source_read_failure_is_unavailable(monkeypatch):
    original_read = Path.read_bytes

    def failed_read(path):
        if path.name == "package_model.py":
            raise OSError("source unavailable")
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", failed_read)
    event, result = _attestation_event()

    assert event["status"] == "UNAVAILABLE"
    assert result["source_sha256"] is None


def test_post_paint_does_not_start_attestation_without_flag(monkeypatch, tmp_path):
    monkeypatch.delenv("CONTEXTOR_F1H_ATTEST", raising=False)
    attestation = Mock()
    cleanup_done = threading.Event()
    monkeypatch.setattr(gui, "_emit_f1h_runtime_attestation", attestation)
    monkeypatch.setattr(
        gui,
        "prune_startup_caches",
        lambda: cleanup_done.set() or {"cache": {"errors": []}},
    )
    controller = SimpleNamespace(
        _closing=False,
        _start_backend_owner_claim=Mock(),
        _set_live_status=Mock(),
        _check_stale_excludes=Mock(),
        repo_path_var=SimpleNamespace(get=lambda: str(tmp_path)),
        _start_live_watcher=Mock(),
    )

    gui.ContextorGUI._start_post_paint_tasks(controller)

    assert cleanup_done.wait(2)
    attestation.assert_not_called()

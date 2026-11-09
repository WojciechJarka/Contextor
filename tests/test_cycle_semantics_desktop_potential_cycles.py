"""Desktop soft-cycle presentation is bound to a verified LIVE generation."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from threading import Thread, get_ident
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from contextor.ui import gui
from contextor.ui.gui import ContextorGUI
from contextor.ui.cycle_warning_presentation import (
    format_soft_dependent_cycle_diagnostic,
    read_authenticated_soft_dependent_cycle_diagnostic,
)
from contextor.core.live_state.runtime import (
    _repository_canonical_query_handler,
)
from tests.test_cycle_semantics_desktop_warning_presentation import (
    _analysis_result,
)
from tests.test_cycle_semantics_live_installed_partial_claims import (
    _fixture,
    _owner,
)
from tests.test_original_worker_official_full_live_publication import (
    _official_live,
)
from tests.test_original_worker_partial_scc_preparation import TWO_PASS


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _witness_repo(root):
    (root / "pkg").mkdir(parents=True)
    (root / "a.py").write_text("import b\nvalue = 1\n", encoding="utf-8")
    (root / "b.py").write_text("import a\nvalue = 2\n", encoding="utf-8")
    (root / "x.py").write_text("import y\nvalue = 3\n", encoding="utf-8")
    (root / "y.py").write_text("import x\nvalue = 4\n", encoding="utf-8")
    (root / "pkg" / "__init__.py").write_text("pass\n", encoding="utf-8")
    (root / "pkg" / "a.py").write_text(
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    import pkg.b\n"
        "value = 1\n",
        encoding="utf-8",
    )
    (root / "pkg" / "b.py").write_text(
        "from pkg.a import value\n", encoding="utf-8",
    )


def _gui_controller(root, monkeypatch):
    controller = SimpleNamespace(
        repo_path_var=SimpleNamespace(get=lambda: str(root)),
        root=object(),
        progress_bar=SimpleNamespace(is_cancelled=False),
        log_box=None,
        cpu_indicator=None,
        stop_btn=None,
        _busy_buttons=lambda: (),
        _live_recovery_incident=lambda _path: None,
        _start_live_watcher=lambda *_args, **_kwargs: None,
    )

    def run_inline(root_widget, progress_bar, task, *, on_success, **_kwargs):
        outcome = []
        failure = []

        def run_worker():
            controller._analysis_worker_thread_id = get_ident()
            try:
                outcome.append(task())
            except BaseException as exc:
                failure.append(exc)

        worker = Thread(target=run_worker)
        worker.start()
        worker.join(timeout=120)
        assert not worker.is_alive()
        if failure:
            raise failure[0]
        outcome = outcome[0]
        on_success(outcome)
        return outcome

    monkeypatch.setattr(gui, "run_with_progress", run_inline)
    return controller


def _install_diagnostics_handler(server):
    server._canonical_query_handler = _repository_canonical_query_handler


def test_live_full_to_desktop_reports_potential_without_hard_cycle_warning(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = tmp_path / "repo"
    root.mkdir()
    _witness_repo(root)
    warning = MagicMock()
    info = MagicMock()
    monkeypatch.setattr(gui.messagebox, "showwarning", warning)
    monkeypatch.setattr(gui.messagebox, "showinfo", info)
    controller = _gui_controller(root, monkeypatch)
    main_thread_id = get_ident()

    with _official_live(root, monkeypatch) as (client, server, identity, _calls):
        _install_diagnostics_handler(server)
        ContextorGUI.analyze(controller)
        assert controller._analysis_worker_thread_id != main_thread_id
        errors, result = controller._full_analysis_done

        assert result.live_publish_status == "success"
        assert result.live_publish_revision == result.live_publish_expected_revision
        assert result.live_publish_service_instance_id == server.endpoint.service_instance_id
        assert identity.repo_id
        installed = client.snapshot()
        graph = installed["state"].dependency_graph
        assert "pkg.b" not in graph.hard_edges["pkg.a"]
        assert "pkg.a" in graph.hard_edges["pkg.b"]
        assert "pkg.b" in graph.soft_edges["pkg.a"]

        response = client.canonical_query("diagnostics_summary", payload={})
        assert response.get("status") == "ok", response
        summary = response["result"]
        diagnostic = summary["soft_dependent_potential_cycles"]
        assert response["revision"] == result.live_publish_revision
        assert diagnostic["availability"] == "fresh", {
            "diagnostic": diagnostic,
            "resync_required": getattr(installed["state"], "resync_required", None),
            "cycles_state": installed["state"].cycles_state,
            "hard": installed["state"].dependency_graph.hard_edges,
            "soft": installed["state"].dependency_graph.soft_edges,
        }
        assert diagnostic["count"] == 1
        assert diagnostic["components"][0]["members"] == ("pkg.a", "pkg.b")
        assert diagnostic["components"][0]["soft_only_internal_edges"] == (
            ("pkg.a", "pkg.b"),
        )

        report = client.get_installed_cycle_warning_projection()
        assert report["revision"] == response["revision"]
        assert report["model_pass_count"] > 0
        assert report["active_warning_count"] == 0
        assert ("pkg.a", "pkg.b", "pkg.a") not in report["structural_paths"]
        assert ("pkg.a", "pkg.b", "pkg.a") not in report["model_pass_paths"]
        assert not [error for error in errors if error.kind == "ArchitectureCycle"]
        warning.assert_called_once()
        message = warning.call_args.args[1]
        assert "POTENTIAL cycle involving uncertain dependencies" in message
        assert "pkg.a" in message and "pkg.b" in message
        assert "does not prove CPython will execute" in message
        info.assert_not_called()


def test_verified_control_reports_zero_and_keeps_healthy_success(tmp_path, isolated_dirs, monkeypatch):
    root = tmp_path / "control"
    root.mkdir()
    for name, source in TWO_PASS.items():
        (root / f"{name}.py").write_text(source, encoding="utf-8")
    warning = MagicMock()
    info = MagicMock()
    monkeypatch.setattr(gui.messagebox, "showwarning", warning)
    monkeypatch.setattr(gui.messagebox, "showinfo", info)
    controller = _gui_controller(root, monkeypatch)

    with _official_live(root, monkeypatch) as (client, _server, _identity, _calls):
        _install_diagnostics_handler(_server)
        ContextorGUI.analyze(controller)
        response = client.canonical_query("diagnostics_summary", payload={})
        assert response.get("status") == "ok", response
        summary = response["result"]
        diagnostic = summary["soft_dependent_potential_cycles"]
        assert diagnostic["availability"] == "fresh"
        assert diagnostic["count"] == 0
        assert "Repository is healthy!" in info.call_args.args[1]
        warning.assert_not_called()


def test_stale_or_mismatched_live_authority_is_not_verified_zero(
    tmp_path, isolated_dirs, monkeypatch,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, client):
        _install_diagnostics_handler(server)
        result = _analysis_result(metadata, server)
        monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: client)

        state.cycles_state = "stale"
        stale = read_authenticated_soft_dependent_cycle_diagnostic(result, str(root))
        assert stale["availability"] == "unavailable"
        assert stale["count"] is None
        state.cycles_state = "fresh"

        original_query = client.canonical_query
        monkeypatch.setattr(
            client,
            "canonical_query",
            lambda *args, **kwargs: dict(original_query(*args, **kwargs), revision=metadata.revision + 1),
        )
        mismatch = read_authenticated_soft_dependent_cycle_diagnostic(result, str(root))
        assert mismatch["availability"] == "unavailable"
        assert mismatch["count"] is None


def test_failed_publication_cannot_authorize_zero(tmp_path, monkeypatch):
    def forbidden(_root):
        pytest.fail("failed publication must be rejected before LIVE query")

    monkeypatch.setattr("contextor.core.live_state.connect", forbidden)
    diagnostic = read_authenticated_soft_dependent_cycle_diagnostic(
        SimpleNamespace(live_publish_status="failed"), str(tmp_path),
    )
    assert diagnostic["availability"] == "unavailable"
    assert diagnostic["count"] is None
    text = format_soft_dependent_cycle_diagnostic(diagnostic)
    assert "absence of potential cycles was not established" in text


def test_desktop_presentation_bounds_component_samples():
    diagnostic = {
        "availability": "fresh",
        "count": 1,
        "components": ({
            "members": tuple(f"module.{index}" for index in range(8)),
            "member_count": 5000,
            "soft_only_internal_edges": tuple(
                (f"module.{index}", f"module.{index + 1}")
                for index in range(8)
            ),
            "soft_only_internal_edge_count": 12000,
        },),
    }
    message = format_soft_dependent_cycle_diagnostic(diagnostic)
    assert "5000 modules" in message
    assert "showing 8 of 12000 edges" in message
    assert len(message) < 1500


def test_wrong_repository_identity_is_not_authorized(tmp_path, isolated_dirs, monkeypatch):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    wrong_root = tmp_path / "other"
    wrong_root.mkdir()
    with _owner(state, metadata) as (server, client):
        _install_diagnostics_handler(server)
        monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: client)
        diagnostic = read_authenticated_soft_dependent_cycle_diagnostic(
            _analysis_result(metadata, server), str(wrong_root),
        )
    assert diagnostic["availability"] == "unavailable"
    assert diagnostic["count"] is None


@pytest.mark.skipif(sys.version_info[:3] != (3, 15, 2), reason="fresh CPython 3.15.2 runtime oracle")
def test_end_to_end_behavior_in_fresh_cpython_process():
    repository = Path(__file__).resolve().parents[1]
    target = (
        "tests/test_cycle_semantics_desktop_potential_cycles.py::"
        "test_live_full_to_desktop_reports_potential_without_hard_cycle_warning"
    )
    script = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "import pytest; raise SystemExit(pytest.main(['-q', sys.argv[2]]))"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", script, str(repository), target],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

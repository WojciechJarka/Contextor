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
from contextor.core.reporting_engine.persistent_registry import (
    PersistentIdentityRegistry,
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
from tests.test_gui_live_startup import _make_analysis_controller


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


def _potential_only_repo(root):
    package = root / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("pass\n", encoding="utf-8")
    (package / "a.py").write_text(
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    import pkg.b\n"
        "value = 1\n",
        encoding="utf-8",
    )
    (package / "b.py").write_text(
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
        assert info.call_args.args[1] == (
            "No validation errors or soft-dependent potential cycles were "
            "detected in the verified static analysis. This does not prove "
            "Python runtime safety."
        )
        warning.assert_not_called()


def test_f1c_potential_only_live_desktop_has_no_hard_cycle_or_model_pass(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = tmp_path / "potential-only"
    root.mkdir()
    _potential_only_repo(root)
    warning = MagicMock()
    info = MagicMock()
    monkeypatch.setattr(gui.messagebox, "showwarning", warning)
    monkeypatch.setattr(gui.messagebox, "showinfo", info)
    controller = _gui_controller(root, monkeypatch)

    with _official_live(root, monkeypatch) as (client, server, identity, _calls):
        _install_diagnostics_handler(server)
        ContextorGUI.analyze(controller)
        errors, result = controller._full_analysis_done
        assert result.live_publish_status == "success"
        assert identity.repo_id

        installed = client.snapshot()
        graph = installed["state"].dependency_graph
        assert "pkg.b" not in graph.hard_edges.get("pkg.a", set())
        assert "pkg.a" in graph.hard_edges["pkg.b"]
        assert "pkg.b" in graph.soft_edges["pkg.a"]

        response = client.canonical_query("diagnostics_summary", payload={})
        assert response["status"] == "ok"
        diagnostic = response["result"]["soft_dependent_potential_cycles"]
        assert response["revision"] == result.live_publish_revision
        assert diagnostic["availability"] == "fresh"
        assert diagnostic["count"] == 1

        report = client.get_installed_cycle_warning_projection()
        assert report["revision"] == response["revision"]
        assert report["structural_paths"] == ()
        assert report["model_pass_paths"] == ()
        assert report["model_pass_count"] == 0
        assert not [error for error in errors if error.kind == "ArchitectureCycle"]
        warning.assert_called_once()
        assert "POTENTIAL cycle involving uncertain dependencies" in (
            warning.call_args.args[1]
        )
        assert "Repository is healthy!" not in warning.call_args.args[1]
        info.assert_not_called()


@pytest.mark.parametrize(
    "diagnostic,expected_dialog,expected_fragment",
    [
        pytest.param(
            {
                "availability": "fresh",
                "count": 1,
                "components": ({
                    "members": ("pkg.a", "pkg.b"),
                    "member_count": 2,
                    "soft_only_internal_edges": (("pkg.a", "pkg.b"),),
                    "soft_only_internal_edge_count": 1,
                },),
            },
            "warning",
            "POTENTIAL cycle involving uncertain dependencies",
            id="positive",
        ),
        pytest.param(
            {
                "availability": "fresh",
                "count": 0,
                "components": (),
            },
            "info",
            "No validation errors or soft-dependent potential cycles",
            id="verified-zero",
        ),
        pytest.param(
            {
                "availability": "unavailable",
                "count": None,
                "components": (),
            },
            "warning",
            "absence of potential cycles was not established",
            id="unavailable",
        ),
    ],
)
def test_cleared_recovery_presents_potential_diagnostic_honestly(
    tmp_path, monkeypatch, diagnostic, expected_dialog, expected_fragment,
):
    root = tmp_path / "recovery"
    root.mkdir()
    identity = PersistentIdentityRegistry(str(root))
    controller = _make_analysis_controller(root)
    ContextorGUI._request_full_analysis_recovery(
        controller, str(root), "previous recovery incident", queue_prompt=False,
    )
    certificate = {
        "certificate_id": "f1f-certificate",
        "incident_generation": 1,
        "repo_id": identity.repo_id,
        "root_path": str(root.resolve()),
        "state_id": "f1f-state",
        "revision": 7,
    }

    class RecoveryClient:
        def get_events(self, **_kwargs):
            return {"latest_seq": 0}

        def verify_recovery(self, generation):
            assert generation == 1
            return {"status": "ok", "certificate": certificate}

        def complete_recovery_verification(self, certificate_id, generation):
            return {
                "status": "ok",
                "released": True,
                "certificate_id": certificate_id,
                "incident_generation": generation,
            }

        def cancel_recovery_verification(self, *_args, **_kwargs):
            pytest.fail("valid recovery certificate must not be cancelled")

    client = RecoveryClient()
    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: client)
    monkeypatch.setattr(
        gui,
        "run_full_analysis_exclusive",
        lambda *_args, **_kwargs: (
            [], SimpleNamespace(live_publish_status="success"),
        ),
    )
    monkeypatch.setattr(
        "contextor.ui.cycle_warning_presentation.read_authenticated_soft_dependent_cycle_diagnostic",
        lambda *_args, **_kwargs: diagnostic,
    )
    monkeypatch.setattr(
        gui,
        "run_with_progress",
        lambda _root, _progress, task, *, on_success, **_kwargs: on_success(task()),
    )
    warning = MagicMock()
    info = MagicMock()
    monkeypatch.setattr(gui.messagebox, "showwarning", warning)
    monkeypatch.setattr(gui.messagebox, "showinfo", info)

    ContextorGUI.analyze(
        controller,
        recovery_repository=str(root),
        recovery_generation=1,
    )

    selected = warning if expected_dialog == "warning" else info
    selected.assert_called_once()
    other = info if expected_dialog == "warning" else warning
    other.assert_not_called()
    message = selected.call_args.args[1]
    assert expected_fragment in message
    if diagnostic["availability"] != "fresh":
        assert "No validation errors or soft-dependent potential cycles" not in message


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

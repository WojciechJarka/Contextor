"""Layer and single-file analysis must stay inside the selected GUI root."""

from types import SimpleNamespace

import pytest

from contextor.core.api.facade import ContextorFacade
from contextor.core.repository_identity import registry_meta_path
from contextor.ui import gui


@pytest.mark.parametrize("operation", ["layer", "single"])
def test_facade_rejects_target_outside_root_before_identity_creation(
    tmp_path, operation
):
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    outside_file = outside / "module.py"
    outside_file.write_text("VALUE = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside the repository root"):
        if operation == "layer":
            ContextorFacade.analyze_layer(str(repo), str(outside))
        else:
            ContextorFacade.analyze_single_file(str(outside_file), str(repo))

    assert registry_meta_path(repo) is None


@pytest.mark.parametrize("operation", ["layer", "single"])
def test_gui_warns_and_never_starts_out_of_root_analysis(
    tmp_path, monkeypatch, operation
):
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    outside_file = outside / "module.py"
    outside_file.write_text("VALUE = 1\n", encoding="utf-8")
    warnings = []
    started = []
    monkeypatch.setattr(
        gui.messagebox,
        "showwarning",
        lambda title, message: warnings.append((title, message)),
    )
    monkeypatch.setattr(
        gui,
        "run_with_progress",
        lambda *_args, **_kwargs: started.append("started"),
    )
    controller = SimpleNamespace(
        repo_path_var=SimpleNamespace(get=lambda: str(repo)),
        layer_path_var=SimpleNamespace(get=lambda: str(outside)),
        file_path_var=SimpleNamespace(get=lambda: str(outside_file)),
    )

    if operation == "layer":
        gui.ContextorGUI.analyze_layer(controller)
    else:
        gui.ContextorGUI.analyze_single(controller)

    assert started == []
    assert len(warnings) == 1
    assert "repository root" in warnings[0][1]

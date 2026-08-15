"""Repository identity must exist before any analysis pipeline starts."""

import json

import pytest

from contextor.core.api import facade
from contextor.core.api.facade import ContextorFacade
from contextor.core.repository_identity import registry_meta_path


EXPECTED_DICTIONARIES = {
    "module_slots.json",
    "artifact_slots.json",
    "module_recovery.json",
    "artifact_recovery.json",
    "output_references.json",
    "module_registry.json",
    "artifact_registry.json",
}


def _assert_complete_identity(repo):
    meta_path = registry_meta_path(repo)
    assert meta_path is not None
    registry_dir = meta_path.parent
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    assert meta["repo_id"].startswith("ctx_")
    assert meta["repo_name"] == repo.name
    assert meta["root_path"] == str(repo.resolve())
    assert registry_dir.name == f"{repo.name}__{meta['repo_id']}"
    assert not (repo / ".contextor").exists()
    assert EXPECTED_DICTIONARIES <= {path.name for path in registry_dir.glob("*.json")}
    return meta["repo_id"]


@pytest.mark.parametrize("entry_point", ["project", "layer", "single_file"])
def test_every_first_analysis_mode_persists_repo_identity_before_pipeline(
    tmp_path, monkeypatch, entry_point
):
    repo = tmp_path / "repo"
    layer = repo / "pkg"
    layer.mkdir(parents=True)
    target = layer / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")

    def stop_after_identity():
        raise RuntimeError("pipeline intentionally stopped")

    monkeypatch.setattr(facade, "reset_caches", stop_after_identity)

    with pytest.raises(RuntimeError, match="pipeline intentionally stopped"):
        if entry_point == "project":
            ContextorFacade.analyze_project(str(repo))
        elif entry_point == "layer":
            ContextorFacade.analyze_layer(str(repo), str(layer))
        else:
            ContextorFacade.analyze_single_file(str(target), str(repo))

    first_id = _assert_complete_identity(repo)
    registry = facade._initialize_repository_identity(repo)
    assert registry.repo_id == first_id


def test_successful_layer_analysis_keeps_root_identity_and_populates_dictionaries(
    sample_repo, isolated_dirs
):
    ContextorFacade.analyze_layer(
        str(sample_repo),
        str(sample_repo / "core"),
    )

    root_id = _assert_complete_identity(sample_repo)
    registry = facade._initialize_repository_identity(sample_repo)
    assert registry.repo_id == root_id
    registry_dir = registry_meta_path(sample_repo).parent
    modules = json.loads(
        (registry_dir / "module_registry.json").read_text(encoding="utf-8")
    )
    assert "core.alpha" in modules["path_to_id"]

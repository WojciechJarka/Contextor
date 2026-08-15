"""Fast single-file primitives reuse canonical state instead of reparsing."""

from contextor.core.reporting_engine.canonical_artifacts import (
    canonical_artifact_report,
)
from contextor.core.api.facade import ContextorFacade


def test_canonical_artifact_report_preserves_consumers_and_usage():
    projected = canonical_artifact_report({
        "pkg.model": {
            "symbols": {"classes": ["Model"]},
            "consumers": {
                "Model": {
                    "consumers": ["pkg.api"],
                    "usage": {"api_imports": ["pkg.api"]},
                }
            },
        }
    })

    assert projected["artifacts"]["pkg.model::Model"] == {
        "artifact_id": "pkg.model::Model",
        "definer_module": "pkg.model",
        "consumers": ["pkg.api"],
        "kind": "class",
    }
    assert projected["_usage_sidecar"]["pkg.model::Model"] == {
        "api_imports": ["pkg.api"]
    }


def test_single_file_reuses_snapshot_without_global_reanalysis(
    sample_repo, isolated_dirs, monkeypatch
):
    target = sample_repo / "core" / "alpha.py"
    ContextorFacade.analyze_project(str(sample_repo))

    def forbidden(*_args, **_kwargs):
        raise AssertionError("single-file fast path started global analysis")

    monkeypatch.setattr("contextor.core.api.facade.build_index", forbidden)
    monkeypatch.setattr("contextor.core.api.facade.get_cached_graph", forbidden)
    monkeypatch.setattr(
        "contextor.core.reporting_layer.artifact_usage_report.generate_artifact_usage_report",
        forbidden,
    )

    output = ContextorFacade.analyze_single_file(str(target), str(sample_repo))

    assert output.endswith("single_core.alpha.json")


def test_layer_reuses_snapshot_without_global_reanalysis(
    sample_repo, isolated_dirs, monkeypatch
):
    ContextorFacade.analyze_project(str(sample_repo))

    def forbidden(*_args, **_kwargs):
        raise AssertionError("layer warm path started global analysis")

    monkeypatch.setattr("contextor.core.api.facade.index_repository", forbidden)
    monkeypatch.setattr("contextor.core.api.facade.get_cached_graph", forbidden)
    monkeypatch.setattr(
        "contextor.core.api.facade.generate_artifact_usage_report", forbidden
    )

    pattern = ContextorFacade.analyze_layer(
        str(sample_repo), str(sample_repo / "core")
    )

    assert pattern.endswith(f"{sample_repo.name}_core_*.json")

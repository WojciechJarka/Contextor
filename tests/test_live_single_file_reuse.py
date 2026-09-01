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
        "contextor.core.api.facade.hydrate_repository_engine", forbidden
    )
    monkeypatch.setattr(
        "contextor.core.reporting_layer.artifact_usage_report.generate_artifact_usage_report",
        forbidden,
    )

    output = ContextorFacade.analyze_single_file(str(target), str(sample_repo))

    assert output.endswith("single_core.alpha.json")


def test_single_file_changed_target_falls_back_to_incremental_engine(
    sample_repo, isolated_dirs, monkeypatch
):
    import contextor.core.api.facade as facade_module

    target = sample_repo / "core" / "alpha.py"
    ContextorFacade.analyze_project(str(sample_repo))

    original_hydrate = facade_module.hydrate_repository_engine
    calls = 0

    def counted_hydrate(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_hydrate(*args, **kwargs)

    monkeypatch.setattr(facade_module, "hydrate_repository_engine", counted_hydrate)

    original_source = target.read_text(encoding="utf-8")
    target.write_text(
        original_source + "\n# changed after canonical seed\n",
        encoding="utf-8",
    )

    output = ContextorFacade.analyze_single_file(str(target), str(sample_repo))

    assert output.endswith("single_core.alpha.json")
    assert calls == 1


def test_single_file_resync_state_rejects_state_only_path(
    sample_repo, isolated_dirs, monkeypatch
):
    import contextor.core.api.facade as facade_module

    target = sample_repo / "core" / "alpha.py"
    ContextorFacade.analyze_project(str(sample_repo))

    resolved = facade_module.resolve_authoritative_repository_state(str(sample_repo))
    assert resolved is not None

    resolved.state.resync_required = True

    real_resolver = facade_module.resolve_authoritative_repository_state
    original_hydrate = facade_module.hydrate_repository_engine
    hydrate_calls = 0
    first_resolution = True

    def controlled_resolver(repo_path):
        nonlocal first_resolution
        if first_resolution:
            first_resolution = False
            return resolved
        return real_resolver(repo_path)

    def counted_hydrate(*args, **kwargs):
        nonlocal hydrate_calls
        hydrate_calls += 1
        return original_hydrate(*args, **kwargs)

    monkeypatch.setattr(
        facade_module,
        "resolve_authoritative_repository_state",
        controlled_resolver,
    )
    monkeypatch.setattr(facade_module, "hydrate_repository_engine", counted_hydrate)

    output = ContextorFacade.analyze_single_file(str(target), str(sample_repo))

    assert output.endswith("single_core.alpha.json")
    assert hydrate_calls == 1


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

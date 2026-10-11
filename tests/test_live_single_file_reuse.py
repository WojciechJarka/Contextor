"""Fast single-file primitives reuse canonical state instead of reparsing."""

from types import SimpleNamespace
from dataclasses import replace
from copy import copy
import threading

from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient

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


def test_single_file_reports_accepted_recovery_without_changing_string_return(
    sample_repo, isolated_dirs, monkeypatch
):
    import contextor.core.api.facade as facade_module

    target = sample_repo / "core" / "alpha.py"
    ContextorFacade.analyze_project(str(sample_repo))
    original_hydrate = facade_module.hydrate_repository_engine
    published = []

    def hydrate_with_client(root, **kwargs):
        hydrated = original_hydrate(root, **kwargs)
        client = SimpleNamespace(publish=lambda *_a, **_k: published.append(True) or {
            "status": "ok", "revision": 17,
            "resync_required": True, "warning": "release unverified",
        })
        return replace(hydrated, client=client)

    monkeypatch.setattr(facade_module, "hydrate_repository_engine", hydrate_with_client)
    target.write_text(
        target.read_text(encoding="utf-8").replace("MAX_ITEMS = 10", "MAX_ITEMS = 11"),
        encoding="utf-8",
    )
    publication = {}
    output = ContextorFacade.analyze_single_file(
        str(target), str(sample_repo), publication_result=publication,
    )

    assert isinstance(output, str)
    assert output.endswith("single_core.alpha.json")
    assert published == [True]
    assert publication == {
        "status": "recovery_required", "revision": 17,
        "warning": "release unverified",
    }


def test_scoped_single_file_publishes_to_real_live_server_under_writer_lease(
    sample_repo, isolated_dirs, monkeypatch
):
    import contextor.core.api.facade as facade_module
    from contextor.core.analysis import full_analysis_coordinator as coordinator

    target = sample_repo / "core" / "alpha.py"
    ContextorFacade.analyze_project(str(sample_repo))
    resolved = facade_module.resolve_authoritative_repository_state(str(sample_repo))
    assert resolved is not None
    initial_revision = max(0, int(getattr(resolved.state, "revision", 0)) - 1)
    initial_state = copy(resolved.state)
    initial_state.revision = initial_revision
    server = CanonicalLiveServer(state=initial_state, revision=initial_revision)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    client = LiveStateClient(server.endpoint)
    original_hydrate = facade_module.hydrate_repository_engine
    original_publish = client.publish
    observed = []

    def hydrate_with_server(root, **kwargs):
        hydrated = original_hydrate(root, **kwargs)
        return replace(hydrated, client=client)

    def publish_while_held(*args, **kwargs):
        observed.append("publish")
        try:
            coordinator.acquire_full_analysis(
                sample_repo, timeout=0.0, writer_kind="local_incremental"
            )
        except coordinator.FullAnalysisBusyError:
            observed.append("lease_held")
        else:
            pytest.fail("LIVE publication ran outside scoped lease")
        return original_publish(*args, **kwargs)

    import pytest
    monkeypatch.setattr(facade_module, "hydrate_repository_engine", hydrate_with_server)
    monkeypatch.setattr(client, "publish", publish_while_held)
    target.write_text(
        target.read_text(encoding="utf-8").replace("MAX_ITEMS = 10", "MAX_ITEMS = 12"),
        encoding="utf-8",
    )
    publication = {}
    try:
        output = ContextorFacade.analyze_single_file(
            str(target), str(sample_repo), publication_result=publication
        )
        assert output.endswith("single_core.alpha.json")
        assert observed == ["publish", "lease_held"]
        assert publication["status"] == "success", publication
        assert publication["revision"] == initial_revision + 1
    finally:
        client.request("shutdown")
        server_thread.join(timeout=5)


def test_scoped_single_file_reports_already_installed_ack_under_writer_lease(
    sample_repo,
    isolated_dirs,
    monkeypatch,
):
    import pytest
    import contextor.core.api.facade as facade_module
    from contextor.core.analysis import full_analysis_coordinator as coordinator

    target = sample_repo / "core" / "alpha.py"
    ContextorFacade.analyze_project(str(sample_repo))
    original_hydrate = facade_module.hydrate_repository_engine
    observed = []

    class AlreadyInstalledClient:
        def publish(
            self,
            state,
            *,
            origin="unknown",
            timeout=30.0,
            acknowledge_installed=False,
        ):
            try:
                probe_lease = coordinator.acquire_full_analysis(
                    sample_repo,
                    timeout=0.0,
                    writer_kind="local_incremental",
                )
            except coordinator.FullAnalysisBusyError:
                lease_held = True
            else:
                coordinator.release_full_analysis(probe_lease)
                lease_held = False
            revision = int(state.revision)
            observed.append(
                {
                    "origin": origin,
                    "timeout": timeout,
                    "acknowledge_installed": acknowledge_installed,
                    "lease_held": lease_held,
                    "revision": revision,
                }
            )
            return {
                "status": "ok",
                "revision": revision,
                "seq": 12,
                "source": "committed_snapshot",
                "already_installed": True,
                "origin_verified": False,
            }

    client = AlreadyInstalledClient()

    def hydrate_with_ack_client(root, **kwargs):
        hydrated = original_hydrate(root, **kwargs)
        assert hydrated is not None
        return replace(hydrated, client=client)

    monkeypatch.setattr(
        facade_module,
        "hydrate_repository_engine",
        hydrate_with_ack_client,
    )
    target.write_text(
        target.read_text(encoding="utf-8").replace(
            "MAX_ITEMS = 10",
            "MAX_ITEMS = 12",
        ),
        encoding="utf-8",
    )
    publication = {}

    output = ContextorFacade.analyze_single_file(
        str(target),
        str(sample_repo),
        publication_result=publication,
    )

    assert output.endswith("single_core.alpha.json")
    assert observed == [
        {
            "origin": "scoped_analysis",
            "timeout": 5.0,
            "acknowledge_installed": True,
            "lease_held": True,
            "revision": observed[0]["revision"],
        }
    ]
    assert publication["status"] == "success"
    assert publication["revision"] == observed[0]["revision"]
    assert publication["warning"] == (
        "LIVE generation was already installed; event origin is not verified."
    )


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

    def controlled_resolver(repo_path, **kwargs):
        nonlocal first_resolution
        if first_resolution:
            first_resolution = False
            return resolved
        return real_resolver(repo_path, **kwargs)

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

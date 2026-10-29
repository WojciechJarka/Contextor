"""Pure installed cycle warning projection over genuine isolated generations."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from contextor.core.cycle_semantics.cycle_warning_projection import (
    InstalledCycleWarningProjection,
    project_installed_cycle_warnings,
)
from contextor.core.cycle_semantics.partial_warning_eligibility import (
    _verified_installed_partial_model_pass_paths,
)
from contextor.core.api.facade import ContextorFacade
from tests.test_cycle_semantics_live_installed_partial_claims import (
    _fixture, _full, _owner, _persisted,
)
from tests.test_original_worker_partial_scc_preparation import (
    PASS_AND_HAZARD, PASS_AND_UNKNOWN, TWO_PASS, _repo,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _arguments(server, state, metadata, **changes):
    receipt = state.cycle_partial_source_publication
    values = {
        "canonical_revision": server._revision,
        "authority_identity": server._authority_identity,
        "activity_epoch": server._activity_epoch,
        "expected_revision": metadata.revision,
        "expected_state_id": metadata.state_id,
        "expected_repo_id": metadata.repo_id,
        "expected_root_path": metadata.root_path,
        "expected_graph_sha256": state.cycle_semantics.graph_sha256,
        "expected_claims_sha256": (
            receipt.claims_sha256 if receipt is not None else "0" * 64
        ),
        "expected_service_instance_id": server.endpoint.service_instance_id,
        "expected_process_start_identity": server.endpoint.process_start_identity,
    }
    return {**values, **changes}


def _project(server, state, metadata, **changes):
    with server._lock:
        return project_installed_cycle_warnings(
            state, **_arguments(server, state, metadata, **changes),
        )


def _paths(state):
    return tuple(tuple(path) for path in state.cycles)


def _assert_partition(result):
    assert type(result) is InstalledCycleWarningProjection
    assert result.status == "FRESH"
    structural = result.structural_paths
    accepted = result.model_pass_paths
    active = result.active_warning_paths
    assert set(accepted).isdisjoint(active)
    assert set(accepted) | set(active) == set(structural)
    assert len(accepted) + len(active) == len(structural)


@pytest.mark.parametrize("sources,expected_accepted", [
    (PASS_AND_UNKNOWN, 1),
    (PASS_AND_HAZARD, 1),
    (TWO_PASS, 2),
])
def test_t01_t02_t03_t19_t21_real_scc_partition(
    tmp_path, isolated_dirs, sources, expected_accepted,
):
    _, state, metadata = _fixture(tmp_path, sources)
    with _owner(state, metadata) as (server, _):
        result = _project(server, state, metadata)
        _assert_partition(result)
        assert result.structural_paths == _paths(state)
        assert len(result.structural_paths) == 2
        assert len(result.model_pass_paths) == expected_accepted
        assert len(result.active_warning_paths) == 2 - expected_accepted
        assert result.model_pass_paths[0] == tuple(state.cycles[0])
        if expected_accepted == 1:
            assert result.active_warning_paths == (tuple(state.cycles[1]),)


@pytest.mark.parametrize("mode", ["default", "preview", "v2"])
def test_t04_t05_t06_absent_partial_receipt_keeps_all_warnings(
    tmp_path, isolated_dirs, mode,
):
    if mode == "default":
        root = _repo(tmp_path, TWO_PASS)
        errors, result = ContextorFacade.analyze_project(str(root))
        assert isinstance(errors, list)
        assert result is not None
        assert not hasattr(result, "cycle_source_preparation_preview")
        state, metadata = _persisted(root)
    elif mode == "v2":
        root, state, metadata = _fixture(
            tmp_path, TWO_PASS, partial=False, complete=True,
        )
    else:
        root, state, metadata = _fixture(tmp_path, TWO_PASS, partial=False)
        assert state.cycle_source_publication is None
    assert root.exists()
    assert state.cycle_partial_source_publication is None
    with _owner(state, metadata) as (server, _):
        result = _project(server, state, metadata)
        _assert_partition(result)
        assert result.structural_paths == _paths(state)
        assert result.model_pass_paths == ()
        assert result.active_warning_paths == _paths(state)


@pytest.mark.parametrize("change", [
    {"expected_revision": 99},
    {"expected_service_instance_id": "foreign"},
    {"expected_process_start_identity": "foreign"},
    {"expected_repo_id": "foreign"},
    {"expected_state_id": "foreign"},
    {"expected_root_path": "foreign"},
    {"expected_graph_sha256": "0" * 64},
    {"expected_claims_sha256": "0" * 64},
])
def test_t07_t08_t09_t10_foreign_expected_generation_keeps_warnings(
    tmp_path, isolated_dirs, change,
):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, _):
        result = _project(server, state, metadata, **change)
        _assert_partition(result)
        assert result.model_pass_paths == ()
        assert result.active_warning_paths == _paths(state)
        assert state.cycle_partial_source_publication is not None


@pytest.mark.parametrize("mutation", ["missing", "classification", "digest"])
def test_t11_t22_invalid_partial_receipt_keeps_all_warnings(
    tmp_path, isolated_dirs, mutation,
):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, _):
        original = state.cycle_partial_source_publication
        if mutation == "missing":
            state.cycle_partial_source_publication = None
        elif mutation == "digest":
            state.cycle_partial_source_publication = replace(
                original, claims_sha256="0" * 64,
            )
        else:
            items = list(original.preparation.component_preparations)
            items[0] = replace(items[0], model_classification="FORGED")
            state.cycle_partial_source_publication = replace(
                original,
                preparation=replace(
                    original.preparation, component_preparations=tuple(items),
                ),
            )
        try:
            result = _project(server, state, metadata)
            _assert_partition(result)
            assert result.model_pass_paths == ()
            assert result.active_warning_paths == _paths(state)
        finally:
            state.cycle_partial_source_publication = original


def test_t12_newer_generation_without_receipt_restores_warnings(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, _):
        before = _project(server, state, metadata)
        assert before.active_warning_paths == ()
        _full(root, partial=False)
        newer, newer_metadata = _persisted(root)
        assert server._execute_publish({
            "state": newer, "origin": "isolated_test",
        })["status"] == "ok"
        after = _project(server, newer, newer_metadata)
        _assert_partition(after)
        assert after.structural_paths == before.structural_paths
        assert after.model_pass_paths == ()
        assert after.active_warning_paths == before.structural_paths


@pytest.mark.parametrize("mutation", ["stale", "resync"])
def test_t13_t14_unavailable_inventory_is_not_zero(
    tmp_path, isolated_dirs, mutation,
):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, _):
        if mutation == "stale":
            state.cycles_state = "stale"
        else:
            state.resync_required = True
        result = _project(server, state, metadata)
        assert result == InstalledCycleWarningProjection(
            status="UNAVAILABLE",
            reason="STRUCTURAL_CYCLE_INVENTORY_UNAVAILABLE",
            revision=None,
            structural_paths=None,
            model_pass_paths=None,
            active_warning_paths=None,
        )


@pytest.mark.parametrize("malformed", [
    ["a", "b", "a", "b", "a"],
    ["a", "b", "a"],
    ["a", "missing", "a"],
    ["a", "a"],
])
def test_t15_any_invalid_path_makes_inventory_unavailable(
    tmp_path, isolated_dirs, malformed,
):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, _):
        original = state.cycles
        try:
            state.cycles = [*original, malformed]
            result = _project(server, state, metadata)
            assert result.status == "UNAVAILABLE"
            assert result.structural_paths is None
            assert result.model_pass_paths is None
            assert result.active_warning_paths is None
        finally:
            state.cycles = original


def test_t16_empty_fresh_acyclic_inventory_is_available(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(
        tmp_path, {"a": "value = 1\n"}, partial=True,
    )
    with _owner(state, metadata) as (server, _):
        result = _project(server, state, metadata)
        _assert_partition(result)
        assert result.structural_paths == ()
        assert result.model_pass_paths == ()
        assert result.active_warning_paths == ()


def test_t17_t18_t23_repeated_projection_is_pure_and_agrees_with_eligibility(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, _):
        before = copy.deepcopy((
            state.dependency_graph.hard_edges,
            state.cycle_semantics.import_sites.topology.cyclic_components,
            state.cycles,
            state.cycle_partial_source_publication,
            server._events,
        ))
        first = _project(server, state, metadata)
        second = _project(server, state, metadata)
        assert first == second
        with server._lock:
            eligible = _verified_installed_partial_model_pass_paths(
                state, **_arguments(server, state, metadata),
            )
        assert frozenset(first.model_pass_paths) == eligible
        assert (
            state.dependency_graph.hard_edges,
            state.cycle_semantics.import_sites.topology.cyclic_components,
            state.cycles,
            state.cycle_partial_source_publication,
            server._events,
        ) == before


def test_t20_two_distinct_simple_paths_remain_in_canonical_order(
    tmp_path, isolated_dirs,
):
    sources = {
        "a": "import b\nimport c\nvalue = 1\n",
        "b": "import a\nvalue = 2\n",
        "c": "import a\nvalue = 3\n",
    }
    _, state, metadata = _fixture(tmp_path, sources)
    with _owner(state, metadata) as (server, _):
        original = state.cycles
        try:
            state.cycles = [["a", "c", "a"], ["a", "b", "a"]]
            result = _project(server, state, metadata)
            _assert_partition(result)
            assert result.structural_paths == (
                ("a", "c", "a"), ("a", "b", "a"),
            )
            assert result.model_pass_paths == result.structural_paths
            assert result.active_warning_paths == ()
        finally:
            state.cycles = original


def test_t24_projection_does_not_call_cycle_builder_or_warning_consumer(
    tmp_path, isolated_dirs, monkeypatch,
):
    _, state, metadata = _fixture(tmp_path)
    import contextor.core.validator.cycles as cycle_validator
    import contextor.core.diagnostics_projection as diagnostics
    def forbidden(*args, **kwargs):
        raise AssertionError("unrelated cycle or warning consumer invoked")
    monkeypatch.setattr(cycle_validator, "detect_cycles", forbidden, raising=False)
    monkeypatch.setattr(diagnostics, "diagnostics_summary_for_completed_job", forbidden, raising=False)
    with _owner(state, metadata) as (server, _):
        assert _project(server, state, metadata).status == "FRESH"

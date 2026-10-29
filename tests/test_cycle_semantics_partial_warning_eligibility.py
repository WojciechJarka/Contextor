"""Installed partial model-PASS paths remain separate from warning projection."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from contextor.core.cycle_semantics.partial_warning_eligibility import (
    _verified_installed_partial_model_pass_paths,
)
from contextor.core.cycle_semantics.warning_eligibility import (
    _verified_model_pass_cycle_paths,
)
from tests.test_cycle_semantics_live_installed_partial_claims import (
    _fixture, _full, _owner, _persisted,
)
from tests.test_original_worker_partial_scc_preparation import (
    PASS_AND_HAZARD, PASS_AND_UNKNOWN, TWO_PASS,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _expected(server, state, metadata):
    receipt = state.cycle_partial_source_publication
    return {
        "canonical_revision": server._revision,
        "authority_identity": server._authority_identity,
        "activity_epoch": server._activity_epoch,
        "expected_revision": metadata.revision,
        "expected_state_id": metadata.state_id,
        "expected_repo_id": metadata.repo_id,
        "expected_root_path": metadata.root_path,
        "expected_graph_sha256": state.cycle_semantics.graph_sha256,
        "expected_claims_sha256": receipt.claims_sha256,
        "expected_service_instance_id": server.endpoint.service_instance_id,
        "expected_process_start_identity": server.endpoint.process_start_identity,
    }


def _eligible(server, state, metadata, **changes):
    with server._lock:
        return _verified_installed_partial_model_pass_paths(
            state, **{**_expected(server, state, metadata), **changes},
        )


def _paths_for(state, members):
    return frozenset(
        tuple(path) for path in state.cycles
        if frozenset(path[:-1]) <= frozenset(members)
    )


@pytest.mark.parametrize("sources", [PASS_AND_UNKNOWN, PASS_AND_HAZARD, TWO_PASS])
def test_t01_t02_t03_t17_t24_individual_scc_eligibility(
    tmp_path, isolated_dirs, sources,
):
    _, state, metadata = _fixture(tmp_path, sources)
    with _owner(state, metadata) as (server, _):
        result = _eligible(server, state, metadata)
        assert _paths_for(state, ("a", "b")) <= result
        if sources is TWO_PASS:
            assert result == frozenset(tuple(path) for path in state.cycles)
        else:
            assert result == _paths_for(state, ("a", "b"))
            assert _paths_for(state, ("x", "y")).isdisjoint(result)
        assert type(result) is frozenset


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
def test_t04_t05_t06_t07_t08_invalid_identity(tmp_path, isolated_dirs, change):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, _):
        assert _eligible(server, state, metadata, **change) == frozenset()


@pytest.mark.parametrize("mutation", [
    "missing", "classification", "digest", "semantic", "cycles", "resync",
])
def test_t09_t11_t12_invalid_installed_receipt_or_family(
    tmp_path, isolated_dirs, mutation,
):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, _):
        expected = _expected(server, state, metadata)
        receipt = state.cycle_partial_source_publication
        if mutation == "missing":
            state.cycle_partial_source_publication = None
        elif mutation == "classification":
            items = list(receipt.preparation.component_preparations)
            items[0] = replace(items[0], model_classification="FORGED")
            state.cycle_partial_source_publication = replace(
                receipt, preparation=replace(
                    receipt.preparation, component_preparations=tuple(items),
                ),
            )
        elif mutation == "digest":
            state.cycle_partial_source_publication = replace(
                receipt, claims_sha256="0" * 64,
            )
        elif mutation == "semantic":
            state.cycle_semantics_state = "stale"
        elif mutation == "cycles":
            state.cycles_state = "stale"
        else:
            state.resync_required = True
        with server._lock:
            assert _verified_installed_partial_model_pass_paths(
                state, **expected,
            ) == frozenset()


def test_t10_t23_v2_only_cannot_establish_partial_eligibility(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS, partial=False, complete=True)
    with _owner(state, metadata) as (server, _):
        with server._lock:
            result = _verified_installed_partial_model_pass_paths(
                state,
                canonical_revision=server._revision,
                authority_identity=server._authority_identity,
                activity_epoch=server._activity_epoch,
                expected_revision=metadata.revision,
                expected_state_id=metadata.state_id,
                expected_repo_id=metadata.repo_id,
                expected_root_path=metadata.root_path,
                expected_graph_sha256=state.cycle_semantics.graph_sha256,
                expected_claims_sha256="0" * 64,
                expected_service_instance_id=server.endpoint.service_instance_id,
                expected_process_start_identity=server.endpoint.process_start_identity,
            )
            assert result == frozenset()
            assert _verified_model_pass_cycle_paths(
                state, expected_revision=metadata.revision,
                expected_state_id=metadata.state_id,
                expected_repo_id=metadata.repo_id,
                expected_root_path=metadata.root_path,
            )


@pytest.mark.parametrize("path", [
    ["a", "b", "a", "b", "a"],
    ["a", "b", "a"],
    ["a", "missing", "a"],
])
def test_t13_t14_t16_malformed_path_fails_entire_result(
    tmp_path, isolated_dirs, path,
):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, _):
        assert _eligible(server, state, metadata)
        state.cycles.append(path)
        assert _eligible(server, state, metadata) == frozenset()


def test_r1_t15a_genuine_full_self_import_has_no_cycle_or_receipt(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(
        tmp_path, {"a": "import a\n"}, partial=True,
    )
    assert "a" not in state.dependency_graph.hard_edges.get("a", ())
    assert state.cycle_semantics.import_sites.topology.cyclic_components == ()
    assert state.cycle_partial_source_publication is None
    assert state.cycles == []
    assert root.exists()
    with _owner(state, metadata) as (server, _):
        with server._lock:
            assert _verified_installed_partial_model_pass_paths(
                state,
                canonical_revision=server._revision,
                authority_identity=server._authority_identity,
                activity_epoch=server._activity_epoch,
                expected_revision=metadata.revision,
                expected_state_id=metadata.state_id,
                expected_repo_id=metadata.repo_id,
                expected_root_path=metadata.root_path,
                expected_graph_sha256=state.cycle_semantics.graph_sha256,
                expected_claims_sha256="0" * 64,
                expected_service_instance_id=server.endpoint.service_instance_id,
                expected_process_start_identity=server.endpoint.process_start_identity,
            ) == frozenset()


@pytest.mark.parametrize("path", [
    ["a", "a"],
    ["a", "a", "a"],
])
def test_r1_t15b_t15c_self_loop_paths_rejected_without_synthetic_receipt(
    tmp_path, isolated_dirs, path,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, _):
        assert _eligible(server, state, metadata)
        original = state.cycles
        try:
            state.cycles = [path]
            assert _eligible(server, state, metadata) == frozenset()
        finally:
            state.cycles = original
        assert _eligible(server, state, metadata)


def test_t18_two_distinct_paths_in_one_genuine_pass_scc(
    tmp_path, isolated_dirs,
):
    sources = {
        "a": "import b\nimport c\nvalue = 1\n",
        "b": "import a\nvalue = 2\n",
        "c": "import a\nvalue = 3\n",
    }
    _, state, metadata = _fixture(tmp_path, sources)
    with _owner(state, metadata) as (server, _):
        state.cycles = [["a", "b", "a"], ["a", "c", "a"]]
        assert _eligible(server, state, metadata) == frozenset({
            ("a", "b", "a"), ("a", "c", "a"),
        })


@pytest.mark.parametrize("mutation", ["absent", "stale", "malformed"])
def test_t19_missing_stale_or_malformed_paths(tmp_path, isolated_dirs, mutation):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, _):
        if mutation == "absent":
            state.cycles = None
        elif mutation == "stale":
            state.cycles_state = "stale"
        else:
            state.cycles = ["not a path"]
        assert _eligible(server, state, metadata) == frozenset()


def test_t20_t21_pure_and_deterministic(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, _):
        before = copy.deepcopy((
            state.dependency_graph.hard_edges,
            state.cycle_semantics.import_sites.topology.cyclic_components,
            state.cycles,
            state.cycle_partial_source_publication,
            server._activity_epoch,
            server._events,
        ))
        first = _eligible(server, state, metadata)
        assert first
        assert _eligible(server, state, metadata) == first
        after = (
            state.dependency_graph.hard_edges,
            state.cycle_semantics.import_sites.topology.cyclic_components,
            state.cycles,
            state.cycle_partial_source_publication,
            server._activity_epoch,
            server._events,
        )
        assert after == before


def test_t22_new_generation_removes_eligibility(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, _):
        old_expected = _expected(server, state, metadata)
        assert _eligible(server, state, metadata)
        _full(root, partial=False)
        newer, newer_metadata = _persisted(root)
        assert server._execute_publish({
            "state": newer, "origin": "isolated_test",
        })["status"] == "ok"
        with server._lock:
            assert _verified_installed_partial_model_pass_paths(
                server._state, **old_expected,
            ) == frozenset()
        assert newer_metadata.revision > metadata.revision

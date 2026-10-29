"""WARN-1: committed static model claims, never LIVE or runtime safety."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.cycle_semantics.generation_manifest import (
    prepare_cycle_source_manifest,
)
from contextor.core.cycle_semantics.warning_eligibility import (
    _verified_model_pass_cycle_paths,
)
from contextor.core.domain.graph import ProjectGraph
from contextor.core.live_state.store import load_snapshot, save_snapshot
from tests.test_cycle_semantics_evidence import (
    HAZARD,
    PAIR,
    PASS,
    _bound,
    _p1b_snapshots,
)


def _prepared_state(edges, sources, paths):
    index, snapshot, evidence = _bound(edges, sources)
    manifest = prepare_cycle_source_manifest(
        edges, index, snapshot, evidence, _p1b_snapshots(sources),
    )
    state = RepositoryAnalysisState(
        dependency_graph=ProjectGraph(
            hard_edges={name: set(targets) for name, targets in edges.items()},
            soft_edges={},
        ),
        cycles=[list(path) for path in paths],
        cycles_state="fresh",
        cycle_semantics=snapshot,
        cycle_semantics_state="fresh",
    )
    return state, manifest


def _committed(tmp_path, edges=PAIR, sources=PASS, paths=(("a", "b", "a"),)):
    state, manifest = _prepared_state(edges, sources, paths)
    assert manifest.source_manifest_sha256 is not None
    save_snapshot(
        state, tmp_path, "warn-state", exact_revision=1,
        file_state_payload={
            "_meta": {"state_id": "warn-state", "revision": 1},
            "files": {},
        },
        prepared_cycle_manifest=manifest,
    )
    loaded, metadata = load_snapshot(tmp_path, "warn-state")
    assert loaded.cycle_source_publication is not None
    expected = dict(
        expected_revision=metadata.revision,
        expected_state_id=metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=metadata.root_path,
    )
    return loaded, expected


def _eligible(state, expected):
    return _verified_model_pass_cycle_paths(state, **expected)


def test_t01_no_receipt(tmp_path):
    state, _ = _prepared_state(PAIR, PASS, (("a", "b", "a"),))
    assert _eligible(state, dict(
        expected_revision=1, expected_state_id="warn-state",
        expected_repo_id="", expected_root_path="",
    )) == frozenset()


def test_t02_committed_pass_claim_is_eligible(tmp_path):
    state, expected = _committed(tmp_path)
    assert _eligible(state, expected) == frozenset({("a", "b", "a")})
    assert state.cycles == [["a", "b", "a"]]


def test_t03_committed_hazard_is_not_eligible(tmp_path):
    state, expected = _committed(tmp_path, sources=HAZARD)
    assert _eligible(state, expected) == frozenset()


def test_t04_two_scc_pass_and_hazard(tmp_path):
    edges = {"a": {"b"}, "b": {"a"}, "x": {"y"}, "y": {"x"}}
    sources = {**PASS, "x": "import y\nvalue=1", "y": "from x import value"}
    paths = (("a", "b", "a"), ("x", "y", "x"))
    state, expected = _committed(tmp_path, edges, sources, paths)
    assert _eligible(state, expected) == frozenset({paths[0]})


def test_t05_all_paths_in_one_pass_scc(tmp_path):
    edges = {"a": {"b", "c"}, "b": {"a"}, "c": {"a"}}
    sources = {"a": "import b\nimport c", "b": "import a", "c": "import a"}
    paths = (("a", "b", "a"), ("a", "c", "a"))
    state, expected = _committed(tmp_path, edges, sources, paths)
    assert _eligible(state, expected) == frozenset(paths)


def test_t06_mixed_pass_indeterminate_has_no_committed_receipt(tmp_path):
    edges = {"a": {"b"}, "b": {"a"}, "x": {"y"}, "y": {"x"}}
    sources = {**PASS, "x": "import y\nimport unknown", "y": "import x"}
    state, manifest = _prepared_state(
        edges, sources, (("a", "b", "a"), ("x", "y", "x")),
    )
    assert manifest.components[0].model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    assert manifest.components[1].model_classification == "INDETERMINATE"
    assert manifest.source_manifest_sha256 is None
    assert _eligible(state, dict(
        expected_revision=1, expected_state_id="warn-state",
        expected_repo_id="", expected_root_path="",
    )) == frozenset()


@pytest.mark.parametrize("field,value", [
    ("expected_revision", 2), ("expected_state_id", "other"),
])
def test_t07_foreign_generation(tmp_path, field, value):
    state, expected = _committed(tmp_path)
    assert _eligible(state, {**expected, field: value}) == frozenset()


@pytest.mark.parametrize("field,value", [
    ("expected_repo_id", "other"), ("expected_root_path", "other"),
])
def test_t08_foreign_repository(tmp_path, field, value):
    state, expected = _committed(tmp_path)
    assert _eligible(state, {**expected, field: value}) == frozenset()


@pytest.mark.parametrize("mutation", ["graph_hash", "internal_edge"])
def test_t09_changed_graph_fails_closed(tmp_path, mutation):
    state, expected = _committed(tmp_path)
    if mutation == "graph_hash":
        receipt = state.cycle_source_publication
        state.cycle_source_publication = replace(
            receipt,
            prepared_manifest=replace(receipt.prepared_manifest, graph_sha256="0" * 64),
        )
    else:
        state.dependency_graph.hard_edges["a"].add("a")
    assert _eligible(state, expected) == frozenset()


@pytest.mark.parametrize("mutation", ["classification", "digest"])
def test_t10_forged_claim_fails_closed(tmp_path, mutation):
    state, expected = _committed(tmp_path)
    receipt = state.cycle_source_publication
    if mutation == "classification":
        component = replace(
            receipt.prepared_manifest.components[0],
            model_classification="MODEL_INTERNAL_EARLY_BINDING_HAZARD",
        )
        manifest = replace(receipt.prepared_manifest, components=(component,))
        state.cycle_source_publication = replace(receipt, prepared_manifest=manifest)
    else:
        state.cycle_source_publication = replace(receipt, model_claims_sha256="0" * 64)
    assert _eligible(state, expected) == frozenset()


@pytest.mark.parametrize("freshness", ["stale", "deferred"])
def test_t11_semantics_not_fresh(tmp_path, freshness):
    state, expected = _committed(tmp_path)
    state.cycle_semantics_state = freshness
    assert _eligible(state, expected) == frozenset()


@pytest.mark.parametrize("freshness", ["stale", "unavailable"])
def test_t12_cycles_not_fresh(tmp_path, freshness):
    state, expected = _committed(tmp_path)
    state.cycles_state = freshness
    assert _eligible(state, expected) == frozenset()


def test_t13_resync_required(tmp_path):
    state, expected = _committed(tmp_path)
    state.resync_required = True
    assert _eligible(state, expected) == frozenset()


@pytest.mark.parametrize("version", ["cycle-prepared-co-publication/1", "other"])
def test_t14_legacy_or_unsupported_receipt(tmp_path, version):
    state, expected = _committed(tmp_path)
    state.cycle_source_publication = replace(state.cycle_source_publication, version=version)
    assert _eligible(state, expected) == frozenset()


def test_t14_missing_manifest_in_typed_receipt_fails_closed(tmp_path):
    state, expected = _committed(tmp_path)
    state.cycle_source_publication = replace(
        state.cycle_source_publication, prepared_manifest=None,
    )
    assert _eligible(state, expected) == frozenset()


@pytest.mark.parametrize("path", [
    ["a", "b"], ["a", "b", "a", ""], ["a", "z", "a"],
    ["a", 2, "a"], "aba", ["a", "a"],
])
def test_t15_malformed_path_fails_closed(tmp_path, path):
    state, expected = _committed(tmp_path)
    state.cycles = [["a", "b", "a"], path]
    assert _eligible(state, expected) == frozenset()


def test_t16_self_loop_with_committed_pass(tmp_path):
    edges = {"a": {"a"}}
    sources = {"a": "import a"}
    state, expected = _committed(tmp_path, edges, sources, (("a", "a"),))
    assert _eligible(state, expected) == frozenset({("a", "a")})


def test_t17_structural_state_is_unchanged(tmp_path):
    state, expected = _committed(tmp_path)
    before = copy.deepcopy((state.dependency_graph.hard_edges, state.cycles,
                            state.cycle_semantics, state.cycle_source_publication))
    assert _eligible(state, expected) == frozenset({("a", "b", "a")})
    assert (state.dependency_graph.hard_edges, state.cycles,
            state.cycle_semantics, state.cycle_source_publication) == before


def test_t18_repeatable_without_state_mutation(tmp_path):
    state, expected = _committed(tmp_path)
    before = copy.deepcopy(state.__dict__)
    first = _eligible(state, expected)
    second = _eligible(state, expected)
    assert first == second == frozenset({("a", "b", "a")})
    assert state.__dict__ == before

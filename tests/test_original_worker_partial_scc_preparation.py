"""WARN-2A original-worker SCC preparation is not publication authority."""

from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, replace

import pytest

from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.cycle_semantics.materialization import materialize_cycle_semantics
from contextor.core.cycle_semantics.original_worker_preparation import (
    prepare_original_worker_cycle_manifest,
)
from contextor.core.cycle_semantics.warning_eligibility import (
    _verified_model_pass_cycle_paths,
)
from contextor.core.domain.graph import ProjectGraph
from contextor.core.graph.graph import build_graph
from contextor.core.live_state.store import load_snapshot, save_snapshot
from contextor.core.source import SourceSnapshot
from contextor.core.symbol_engine.indexer import index_repository


PASS_AND_UNKNOWN = {
    "a": "import b\nvalue = 1\n",
    "b": "import a\nvalue = 2\n",
    "x": "import y\n@unknown_decorator\ndef f():\n    pass\n",
    "y": "import x\n",
}
TWO_PASS = {
    **PASS_AND_UNKNOWN,
    "x": "import y\nvalue = 3\n",
}
PASS_AND_HAZARD = {
    **TWO_PASS,
    "x": "import y\nvalue = 3\n",
    "y": "from x import value\n",
}
SELECTED = frozenset({"a", "b", "x", "y"})


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _repo(tmp_path, sources):
    root = tmp_path / "repo"
    root.mkdir()
    for module, source in sources.items():
        (root / f"{module}.py").write_bytes(source.encode("utf-8"))
    return root


def _real_pipeline(root, selected=SELECTED):
    index = index_repository(
        str(root), source_capture_module_ids=selected,
    )
    graph = build_graph(index.modules)
    snapshot = materialize_cycle_semantics(
        root,
        graph.hard_edges,
        {name: module.path for name, module in index.modules.items()},
        index.source_fingerprints_by_module,
    )
    return index, graph, snapshot


def _prepare(index, graph, snapshot):
    return prepare_original_worker_cycle_manifest(index, graph.hard_edges, snapshot)


def test_t01_mixed_pass_unknown_preserves_independent_components(tmp_path, isolated_dirs):
    index, graph, snapshot = _real_pipeline(_repo(tmp_path, PASS_AND_UNKNOWN))
    assert index.original_worker_capture_status == "ALL_SELECTED_CAPTURED_NON_ATOMIC"
    result = _prepare(index, graph, snapshot)
    assert result.status == "UNAVAILABLE"
    assert result.reason == "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
    assert result.manifest is None
    assert result.source_modules == ()
    assert len(result.component_preparations) == 2
    assert tuple(item.members for item in result.component_preparations) == (
        ("a", "b"), ("x", "y"),
    )
    first, second = result.component_preparations
    assert (first.preparation_state, first.model_classification) == (
        "PREPARED_UNPUBLISHED", "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
    )
    assert (second.preparation_state, second.model_classification) == (
        "UNAVAILABLE", "INDETERMINATE",
    )


def test_t02_two_supported_sccs_keep_success_contract(tmp_path, isolated_dirs):
    index, graph, snapshot = _real_pipeline(_repo(tmp_path, TWO_PASS))
    result = _prepare(index, graph, snapshot)
    assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert result.reason is None
    assert result.manifest is not None
    assert result.manifest.source_manifest_sha256 is not None
    assert result.source_modules == ("a", "b", "x", "y")
    assert result.component_preparations == result.manifest.components
    assert all(item.preparation_state == "PREPARED_UNPUBLISHED"
               for item in result.component_preparations)


def test_t03_pass_and_hazard_are_distinct_prepared_claims(tmp_path, isolated_dirs):
    index, graph, snapshot = _real_pipeline(_repo(tmp_path, PASS_AND_HAZARD))
    result = _prepare(index, graph, snapshot)
    assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert result.manifest is not None
    assert result.component_preparations == result.manifest.components
    assert tuple(item.model_classification for item in result.component_preparations) == (
        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
    )


def test_t04_unavailable_original_capture_exposes_no_components(tmp_path, isolated_dirs):
    root = _repo(tmp_path, TWO_PASS)
    index, graph, snapshot = _real_pipeline(root, selected=None)
    result = _prepare(index, graph, snapshot)
    assert result.status == "UNAVAILABLE"
    assert result.reason == "BINDING_INDEX_CAPTURE_NOT_COMPLETE"
    assert result.component_preparations == ()


@pytest.mark.parametrize("mode", ["missing", "invalid"])
def test_t05_capture_binding_failure_exposes_no_partial_pass(
    tmp_path, isolated_dirs, mode,
):
    index, graph, snapshot = _real_pipeline(_repo(tmp_path, TWO_PASS))
    captures = dict(index.original_worker_source_snapshots)
    if mode == "missing":
        captures.pop("x")
    else:
        original = captures["x"]
        captures["x"] = SourceSnapshot(
            b"forged", original.source_fingerprint,
        )
    index = replace(index, original_worker_source_snapshots=captures)
    result = _prepare(index, graph, snapshot)
    assert result.status == "UNAVAILABLE"
    assert result.manifest is None
    assert result.component_preparations == ()


def test_t06_partial_components_do_not_create_receipt_or_eligibility(
    tmp_path, isolated_dirs,
):
    index, graph, snapshot = _real_pipeline(_repo(tmp_path, PASS_AND_UNKNOWN))
    result = _prepare(index, graph, snapshot)
    assert result.component_preparations[0].preparation_state == "PREPARED_UNPUBLISHED"
    assert result.manifest is None
    state = RepositoryAnalysisState(
        dependency_graph=ProjectGraph(
            hard_edges={name: set(targets) for name, targets in graph.hard_edges.items()},
            soft_edges={},
        ),
        cycles=[["a", "b", "a"], ["x", "y", "x"]],
        cycles_state="fresh",
        cycle_semantics=snapshot,
        cycle_semantics_state="fresh",
    )
    save_snapshot(
        state, tmp_path, "partial-state", exact_revision=1,
        file_state_payload={
            "_meta": {"state_id": "partial-state", "revision": 1},
            "files": {},
        },
        prepared_cycle_manifest=result.manifest,
    )
    loaded, metadata = load_snapshot(tmp_path, "partial-state")
    assert loaded.cycle_source_publication is None
    assert _verified_model_pass_cycle_paths(
        loaded,
        expected_revision=metadata.revision,
        expected_state_id=metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=metadata.root_path,
    ) == frozenset()


def test_t07_order_and_component_immutability(tmp_path, isolated_dirs):
    index, graph, snapshot = _real_pipeline(_repo(tmp_path, TWO_PASS))
    first = _prepare(index, graph, snapshot)
    second = _prepare(index, graph, snapshot)
    assert first == second
    assert tuple(item.members for item in first.component_preparations) == (
        ("a", "b"), ("x", "y"),
    )
    with pytest.raises(FrozenInstanceError):
        first.component_preparations[0].model_classification = "INDETERMINATE"


def test_t08_supplied_inputs_are_not_mutated(tmp_path, isolated_dirs):
    index, graph, snapshot = _real_pipeline(_repo(tmp_path, TWO_PASS))
    before = copy.deepcopy((
        index.source_fingerprints_by_module,
        index.original_worker_source_snapshots,
        index.original_worker_ast_modes,
        graph.hard_edges,
        snapshot,
    ))
    _prepare(index, graph, snapshot)
    after = (
        index.source_fingerprints_by_module,
        index.original_worker_source_snapshots,
        index.original_worker_ast_modes,
        graph.hard_edges,
        snapshot,
    )
    assert after == before

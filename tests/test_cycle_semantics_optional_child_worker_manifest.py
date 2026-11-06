"""P1D3B: optional worker bytes prepare an unpublished manifest."""

from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.cycle_semantics.generation_manifest import (
    MANIFEST_VERSION,
    OPTIONAL_MANIFEST_VERSION,
)
from contextor.core.cycle_semantics.materialization import (
    materialize_cycle_semantics,
)
from contextor.core.cycle_semantics.original_worker_preparation import (
    prepare_original_worker_cycle_manifest,
)
from contextor.core.cycle_semantics.original_worker_reindex_planning import (
    verify_original_worker_reindex,
)
from contextor.core.source import SourceSnapshot
from tests.test_cycle_semantics_optional_child_worker_capture import (
    _case as worker_case,
    FILES,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch, isolated_dirs):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _pipeline(tmp_path, *, files=None):
    if files is None:
        case = worker_case(tmp_path)
    else:
        case = worker_case(tmp_path, files=files)

    root, first, graph, plan, second, second_graph = case

    verified = verify_original_worker_reindex(
        plan,
        first,
        graph.hard_edges,
        second,
        second_graph.hard_edges,
    )
    assert verified.status == (
        "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
    )

    snapshot = materialize_cycle_semantics(
        root,
        second_graph.hard_edges,
        {
            name: module.path
            for name, module in second.modules.items()
        },
        second.source_fingerprints_by_module,
    )

    return second, second_graph.hard_edges, snapshot, plan


def _prepare(case, *, mode="OPTIONAL_NAMED_CHILDREN"):
    index, hard_edges, snapshot, _ = case
    return prepare_original_worker_cycle_manifest(
        index,
        hard_edges,
        snapshot,
        source_selection=mode,
    )


def test_real_worker_optional_preparation(tmp_path):
    case = _pipeline(tmp_path)
    index, hard, snapshot, plan = case

    assert "pkg.child" in plan.selected_module_ids
    assert "pkg.child" not in hard["pkg.a"]

    result = _prepare(case)

    assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert result.reason is None
    assert result.source_selection == "OPTIONAL_NAMED_CHILDREN"
    assert result.source_modules == tuple(
        sorted(plan.selected_module_ids)
    )

    manifest = result.manifest
    assert manifest is not None
    assert manifest.version == OPTIONAL_MANIFEST_VERSION
    assert manifest.source_selection == "OPTIONAL_NAMED_CHILDREN"
    assert manifest.authority == (
        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
    )
    assert manifest.source_manifest_sha256 is not None
    assert result.component_preparations == manifest.components
    assert "pkg.child" in (
        name
        for name, _, _
        in manifest.components[0].source_signatures
    )
    assert result == _prepare(case)


def test_default_mode_never_promotes_optional_evidence(tmp_path):
    case = _pipeline(tmp_path)

    result = prepare_original_worker_cycle_manifest(
        case[0],
        case[1],
        case[2],
    )

    assert result.source_selection == "HARD_ONLY"
    assert (
        result.manifest is None
        or result.manifest.version == MANIFEST_VERSION
    )
    assert (
        result.manifest is None
        or result.manifest.source_selection == "HARD_ONLY"
    )


def test_missing_optional_worker_capture_blocks_preparation(tmp_path):
    case = list(_pipeline(tmp_path))
    index = case[0]
    snapshots = dict(index.original_worker_source_snapshots)
    snapshots.pop("pkg.child")

    case[0] = replace(
        index,
        original_worker_source_snapshots=snapshots,
    )

    result = _prepare(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == (
        "BINDING_CLOSURE_CAPTURE_SET_MISMATCH"
    )
    assert result.manifest is None
    assert result.component_preparations == ()
    assert result.source_selection == "OPTIONAL_NAMED_CHILDREN"


def test_changed_worker_bytes_block_preparation(tmp_path):
    case = list(_pipeline(tmp_path))
    index = case[0]
    snapshots = dict(index.original_worker_source_snapshots)
    old = snapshots["pkg.child"]

    snapshots["pkg.child"] = SourceSnapshot(
        old.raw + b"# modified\n",
        old.source_fingerprint,
    )
    case[0] = replace(
        index,
        original_worker_source_snapshots=snapshots,
    )

    result = _prepare(case)

    assert result.status == "UNAVAILABLE"
    assert result.manifest is None
    assert result.reason == (
        "BINDING_CLOSURE_SOURCE_DIGEST_MISMATCH:pkg.child"
    )


def test_graph_mismatch_cannot_prepare_optional_manifest(tmp_path):
    case = list(_pipeline(tmp_path))
    case[2] = replace(
        case[2],
        graph_sha256="0" * 64,
    )

    result = _prepare(case)

    assert result.status == "UNAVAILABLE"
    assert result.manifest is None
    assert result.source_modules == ()


def test_two_independent_sccs_from_original_worker(tmp_path):
    case = _pipeline(
        tmp_path,
        files={
            **FILES,
            "pkg/x.py": "import pkg.y\n",
            "pkg/y.py": "import pkg.x\n",
        },
    )

    result = _prepare(case)

    assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert result.manifest is not None
    assert len(result.manifest.components) == 2
    assert result.component_preparations == result.manifest.components


def test_invalid_source_selection_rejected(tmp_path):
    case = _pipeline(tmp_path)
    result = _prepare(case, mode="UNKNOWN")

    assert result.status == "UNAVAILABLE"
    assert result.reason == "SOURCE_SELECTION_INVALID"
    assert result.manifest is None


def test_no_source_reread_during_optional_preparation(
    tmp_path, monkeypatch,
):
    case = _pipeline(tmp_path)

    def forbidden_read(self):
        raise AssertionError("filesystem source reread forbidden")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_bytes", forbidden_read)
        result = _prepare(case)

    assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert result.manifest is not None

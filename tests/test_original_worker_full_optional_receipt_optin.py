"""P1D3G2: official FULL opt-in for optional SCC co-publication."""

import copy

from dataclasses import replace

import pytest

import contextor.core.api.facade as facade_module
import contextor.core.analysis.state_manager as state_manager
import contextor.core.cycle_semantics.original_worker_preparation as preparation_module

from contextor.core.api.facade import ContextorFacade
from contextor.core.cycle_semantics.optional_scc_publication import (
    CanonicalOptionalSCCReceipt,
    verify_co_published_optional_scc_preparation,
)
from contextor.core.cycle_semantics.warning_eligibility import (
    _verified_model_pass_cycle_paths,
)
from tests.test_cycle_semantics_optional_child_full_preview import (
    _repo,
    _run,
)
from tests.test_cycle_semantics_optional_child_worker_capture import (
    FILES,
)
from tests.test_original_worker_full_receipt_optin import (
    _persisted,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _full(root, *, publication=False):
    return _run(
        root,
        cycle_source_preparation_preview=True,
        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
        cycle_optional_source_publication_opt_in=publication,
    )


def _verified(state, metadata):
    return verify_co_published_optional_scc_preparation(
        state,
        revision=metadata.revision,
        state_id=metadata.state_id,
        repo_id=metadata.repo_id,
        root_path=metadata.root_path,
    )


def test_t01_official_full_optional_receipt(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)

    result = _full(root, publication=True)
    state, metadata = _persisted(root)

    receipt = state.cycle_optional_source_publication
    preview = result.cycle_source_preparation_preview
    anchor = result.cycle_source_preparation_generation_anchor

    assert type(receipt) is CanonicalOptionalSCCReceipt
    assert receipt.preparation == preview
    assert receipt.preparation is not None
    assert preview.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"

    assert _verified(state, metadata)

    assert (
        receipt.revision,
        receipt.state_id,
        receipt.repo_id,
        receipt.root_path,
    ) == (
        metadata.revision,
        metadata.state_id,
        metadata.repo_id,
        metadata.root_path,
    )

    assert anchor.revision == metadata.revision
    assert anchor.state_id == metadata.state_id
    assert anchor.source_manifest_sha256 == (
        preview.manifest.source_manifest_sha256
    )

    assert state.cycle_source_publication is None
    assert state.cycle_partial_source_publication is None

    assert _verified_model_pass_cycle_paths(
        state,
        expected_revision=metadata.revision,
        expected_state_id=metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=metadata.root_path,
    ) == frozenset()


def test_t02_default_optional_preview_does_not_publish(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)

    result = _full(root)
    state, metadata = _persisted(root)

    assert result.cycle_source_preparation_preview.manifest is not None
    assert state.cycle_optional_source_publication is None
    assert not _verified(state, metadata)


@pytest.mark.parametrize(
    "value",
    [None, 0, 1, "true", []],
)
def test_t03_invalid_new_optin_precedes_index(
    tmp_path, isolated_dirs, monkeypatch, value,
):
    root = _repo(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("index must not start")

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        forbidden,
    )

    with pytest.raises(
        ValueError,
        match="cycle_optional_source_publication_opt_in must be bool",
    ):
        ContextorFacade.analyze_project(
            str(root),
            cycle_source_preparation_preview=True,
            cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
            cycle_optional_source_publication_opt_in=value,
        )


def test_t04_optional_publication_requires_preview(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("index must not start")

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        forbidden,
    )

    with pytest.raises(
        ValueError,
        match="requires.*preview",
    ):
        ContextorFacade.analyze_project(
            str(root),
            cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
            cycle_optional_source_publication_opt_in=True,
        )


def test_t05_optional_publication_requires_optional_mode(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("index must not start")

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        forbidden,
    )

    with pytest.raises(
        ValueError,
        match="requires.*cycle_source_selection",
    ):
        ContextorFacade.analyze_project(
            str(root),
            cycle_source_preparation_preview=True,
            cycle_optional_source_publication_opt_in=True,
        )


@pytest.mark.parametrize(
    "legacy_flag",
    [
        "cycle_source_publication_opt_in",
        "cycle_partial_source_publication_opt_in",
    ],
)
def test_t06_legacy_publication_remains_disallowed_in_optional_mode(
    tmp_path, isolated_dirs, monkeypatch, legacy_flag,
):
    root = _repo(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("index must not start")

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        forbidden,
    )

    with pytest.raises(
        ValueError,
        match="publication unsupported",
    ):
        ContextorFacade.analyze_project(
            str(root),
            cycle_source_preparation_preview=True,
            cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
            cycle_optional_source_publication_opt_in=True,
            **{legacy_flag: True},
        )


def test_t07_unavailable_preview_persists_without_receipt(
    tmp_path, isolated_dirs,
):
    files = {
        **FILES,
        "pkg/b.py": "value = 1\n",
    }
    root = _repo(tmp_path, files)

    result = _full(root, publication=True)
    state, metadata = _persisted(root)

    assert result.cycle_source_preparation_preview.status == "UNAVAILABLE"
    assert result.cycle_source_preparation_preview.reason == (
        "PLAN_NO_CYCLIC_COMPONENTS"
    )
    assert state.cycle_optional_source_publication is None
    assert not _verified(state, metadata)


def test_t08_source_drift_persists_without_receipt(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    original = facade_module.index_repository

    def drifted(*args, **kwargs):
        if kwargs.get("source_capture_module_ids") is not None:
            (root / "pkg" / "child.py").write_bytes(
                b"import pkg.helper\n# source drift\n"
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        drifted,
    )

    result = _full(root, publication=True)
    state, metadata = _persisted(root)

    assert result.cycle_source_preparation_preview.status == "UNAVAILABLE"
    assert result.cycle_source_preparation_preview.reason == (
        "VERIFY_REINDEX_SOURCE_CHANGED"
    )

    assert state.cycle_optional_source_publication is None
    assert not _verified(state, metadata)


def test_t09_forged_manifest_not_forwarded(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    original = preparation_module.prepare_original_worker_cycle_manifest

    def forged(*args, **kwargs):
        prepared = original(*args, **kwargs)

        if prepared.manifest is None:
            return prepared

        return replace(
            prepared,
            manifest=replace(
                prepared.manifest,
                source_manifest_sha256="0" * 64,
            ),
        )

    monkeypatch.setattr(
        preparation_module,
        "prepare_original_worker_cycle_manifest",
        forged,
    )

    result = _full(root, publication=True)
    state, metadata = _persisted(root)

    assert result.cycle_source_preparation_preview.manifest is not None
    assert state.cycle_optional_source_publication is None
    assert not _verified(state, metadata)


def test_t10_next_default_full_drops_optional_receipt(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)

    _full(root, publication=True)
    old_state, old_meta = _persisted(root)

    assert _verified(old_state, old_meta)

    _run(root)
    new_state, new_meta = _persisted(root)

    assert new_meta.revision > old_meta.revision
    assert new_state.cycle_optional_source_publication is None
    assert old_state.cycle_optional_source_publication is not None


def test_t11_exact_two_index_passes(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    original = facade_module.index_repository
    calls = []

    def tracked(*args, **kwargs):
        calls.append(
            kwargs.get("source_capture_module_ids")
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        tracked,
    )

    result = _full(root, publication=True)

    assert len(calls) == 2
    assert calls[0] is None
    assert calls[1] == frozenset(
        result.cycle_source_preparation_preview.source_modules
    )


def test_t12_forwards_exact_preview_object(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    original = state_manager.save_engine_state
    forwarded = []

    def tracked(*args, **kwargs):
        forwarded.append(
            kwargs.get("prepared_optional_scc_preparation")
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        state_manager,
        "save_engine_state",
        tracked,
    )

    result = _full(root, publication=True)

    assert len(forwarded) == 1
    assert forwarded[0] is result.cycle_source_preparation_preview


def test_t13_graph_and_structural_cycles_unchanged(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)

    _run(root)
    before, _ = _persisted(root)

    old_edges = copy.deepcopy(
        before.dependency_graph.hard_edges
    )
    old_cycles = copy.deepcopy(before.cycles)
    old_scc = copy.deepcopy(
        before.cycle_semantics.import_sites.topology.cyclic_components
    )

    _full(root, publication=True)
    after, _ = _persisted(root)

    assert after.dependency_graph.hard_edges == old_edges
    assert after.cycles == old_cycles
    assert (
        after.cycle_semantics.import_sites.topology.cyclic_components
        == old_scc
    )

"""P1D2I: explicitly publish prepared FULL claims with one generation."""

from __future__ import annotations

from dataclasses import replace

import pytest

import contextor.core.api.facade as facade_module
import contextor.core.cycle_semantics.original_worker_preparation as preparation_module

from contextor.core.analysis.process_pool_lifecycle import (
    terminate_active_process_pools,
)
from contextor.core.analysis.state_manager import (
    load_engine_state,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.cycle_semantics.publication_binding import (
    PUBLICATION_AUTHORITY,
    CanonicalCycleManifestReceipt,
    verify_co_published_cycle_manifest,
)
from contextor.core.live_state.store import read_metadata
from contextor.core.paths import repo_cache_dir

from tests.test_original_worker_full_preparation_optin import (
    _flat_repo,
    _package_repo,
)


@pytest.fixture(autouse=True)
def _inline_by_default(monkeypatch):
    monkeypatch.setenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL",
        "1",
    )


def _run(root, *, preview=False, publication=False):
    errors, result = ContextorFacade.analyze_project(
        str(root),
        cycle_source_preparation_preview=preview,
        cycle_source_publication_opt_in=publication,
    )
    assert result is not None
    assert isinstance(errors, list)
    return result


def _persisted(root):
    cache = repo_cache_dir(root)
    metadata = read_metadata(cache)

    assert metadata is not None

    state = load_engine_state(
        str(cache),
        metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=str(root.resolve()),
    )

    assert state is not None
    return state, metadata


def _assert_same_generation_receipt(state, metadata):
    receipt = state.cycle_source_publication

    assert isinstance(
        receipt,
        CanonicalCycleManifestReceipt,
    )
    assert receipt.authority == PUBLICATION_AUTHORITY
    assert receipt.revision == metadata.revision
    assert receipt.state_id == metadata.state_id
    assert receipt.repo_id == metadata.repo_id
    assert receipt.root_path == metadata.root_path

    assert verify_co_published_cycle_manifest(
        state,
        revision=metadata.revision,
        state_id=metadata.state_id,
        repo_id=metadata.repo_id,
        root_path=metadata.root_path,
    )

    return receipt


def test_p1d2i_t01_default_full_remains_receipt_free(
    tmp_path, isolated_dirs,
):
    root = _flat_repo(tmp_path)

    errors, result = ContextorFacade.analyze_project(
        str(root)
    )

    assert result is not None
    assert isinstance(errors, list)
    assert not hasattr(
        result,
        "cycle_source_preparation_preview",
    )

    state, metadata = _persisted(root)

    assert metadata.revision >= 1
    assert state.cycle_source_publication is None


def test_p1d2i_t02_preview_only_remains_unpublished(
    tmp_path, isolated_dirs,
):
    root = _flat_repo(tmp_path)
    result = _run(root, preview=True)

    preview = result.cycle_source_preparation_preview

    assert preview.status == (
        "PREPARED_UNPUBLISHED_NON_ATOMIC"
    )
    assert preview.manifest is not None

    state, _metadata = _persisted(root)

    assert state.cycle_source_publication is None


def test_p1d2i_t03_explicit_full_same_generation_receipt(
    tmp_path, isolated_dirs,
):
    root = _flat_repo(tmp_path)
    result = _run(
        root,
        preview=True,
        publication=True,
    )

    preview = result.cycle_source_preparation_preview

    assert preview.status == (
        "PREPARED_UNPUBLISHED_NON_ATOMIC"
    )
    assert preview.reason is None
    assert preview.manifest is not None
    assert preview.manifest.authority == (
        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
    )

    state, metadata = _persisted(root)

    assert state.cycle_semantics_state == "fresh"
    assert state.cycles_state == "fresh"

    receipt = _assert_same_generation_receipt(
        state,
        metadata,
    )

    assert receipt.prepared_manifest == preview.manifest
    assert receipt.prepared_manifest.graph_sha256 == (
        state.cycle_semantics.graph_sha256
    )
    assert receipt.prepared_manifest.components[0].members == (
        "a",
        "b",
    )

    assert (
        "cycle_source_preparation_preview"
        not in result.summary_data
    )
    assert not hasattr(
        state,
        "cycle_source_preparation_preview",
    )


def test_p1d2i_t04_publication_requires_preview(
    tmp_path, isolated_dirs,
):
    root = _flat_repo(tmp_path)

    with pytest.raises(
        ValueError,
        match="requires cycle_source_preparation_preview",
    ):
        _run(
            root,
            preview=False,
            publication=True,
        )

    assert read_metadata(repo_cache_dir(root)) is None


def test_p1d2i_t05_invalid_publication_argument_rejected(
    tmp_path, isolated_dirs,
):
    root = _flat_repo(tmp_path)

    for invalid in (None, 0, 1, "yes", [], {}):
        with pytest.raises(
            ValueError,
            match="cycle_source_publication_opt_in must be bool",
        ):
            ContextorFacade.analyze_project(
                str(root),
                cycle_source_preparation_preview=True,
                cycle_source_publication_opt_in=invalid,
            )

    assert read_metadata(repo_cache_dir(root)) is None


def test_p1d2i_t06_unsupported_package_not_published(
    tmp_path, isolated_dirs,
):
    root = _package_repo(tmp_path)

    result = _run(
        root,
        preview=True,
        publication=True,
    )

    preview = result.cycle_source_preparation_preview

    assert preview.status == "UNAVAILABLE"
    assert preview.reason == (
        "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
    )
    assert preview.manifest is None

    state, _metadata = _persisted(root)
    assert state.cycle_source_publication is None


def test_p1d2i_t07_acyclic_repository_not_published(
    tmp_path, isolated_dirs,
):
    root = _flat_repo(tmp_path)
    (root / "b.py").write_bytes(b"value = 2\n")

    result = _run(
        root,
        preview=True,
        publication=True,
    )

    preview = result.cycle_source_preparation_preview

    assert preview.status == "UNAVAILABLE"
    assert preview.reason == "PLAN_NO_CYCLIC_COMPONENTS"
    assert preview.manifest is None

    state, _metadata = _persisted(root)
    assert state.cycle_source_publication is None


def test_p1d2i_t08_second_pass_source_drift_not_published(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)
    original = facade_module.index_repository

    def drifted(*args, **kwargs):
        if kwargs.get("source_capture_module_ids") is not None:
            (root / "helper.py").write_bytes(
                b"value = 300\n"
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        drifted,
    )

    result = _run(
        root,
        preview=True,
        publication=True,
    )

    preview = result.cycle_source_preparation_preview

    assert preview.status == "UNAVAILABLE"
    assert preview.reason == "VERIFY_REINDEX_SOURCE_CHANGED"
    assert preview.manifest is None

    state, _metadata = _persisted(root)
    assert state.cycle_source_publication is None


def test_p1d2i_t09_invalid_manifest_rejects_store_commit(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)

    original = (
        preparation_module.prepare_original_worker_cycle_manifest
    )

    def forged(*args, **kwargs):
        result = original(*args, **kwargs)

        if result.manifest is None:
            return result

        return replace(
            result,
            manifest=replace(
                result.manifest,
                source_manifest_sha256="f" * 64,
            ),
        )

    monkeypatch.setattr(
        preparation_module,
        "prepare_original_worker_cycle_manifest",
        forged,
    )

    result = _run(
        root,
        preview=True,
        publication=True,
    )

    preview = result.cycle_source_preparation_preview

    assert preview.status == (
        "PREPARED_UNPUBLISHED_NON_ATOMIC"
    )
    assert preview.manifest is not None

    assert read_metadata(repo_cache_dir(root)) is None
    assert result.live_publish_status == "not_attempted"


def test_p1d2i_t10_next_full_without_optin_drops_receipt(
    tmp_path, isolated_dirs,
):
    root = _flat_repo(tmp_path)

    _run(
        root,
        preview=True,
        publication=True,
    )

    first_state, first_metadata = _persisted(root)

    first_receipt = _assert_same_generation_receipt(
        first_state,
        first_metadata,
    )

    _run(root)

    second_state, second_metadata = _persisted(root)

    assert second_metadata.revision == (
        first_metadata.revision + 1
    )
    assert second_state.cycle_source_publication is None
    assert first_state.cycle_source_publication == first_receipt


def test_p1d2i_t11_process_pool_explicit_publication(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)

    monkeypatch.delenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL",
        raising=False,
    )

    terminate_active_process_pools(timeout=1.0)

    try:
        result = _run(
            root,
            preview=True,
            publication=True,
        )

        preview = result.cycle_source_preparation_preview

        assert preview.status == (
            "PREPARED_UNPUBLISHED_NON_ATOMIC"
        )
        assert preview.manifest is not None

        state, metadata = _persisted(root)

        receipt = _assert_same_generation_receipt(
            state,
            metadata,
        )

        assert receipt.prepared_manifest == preview.manifest
        assert state.cycle_semantics_state == "fresh"

    finally:
        terminate_active_process_pools(timeout=1.0)

"""P1D3G1: store-owned optional SCC declarations, not safety."""

import pickle

from dataclasses import fields, replace

import pytest

import contextor.core.live_state.store as store_module

from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
)
from contextor.core.cycle_semantics.lifecycle import (
    invalidate_cycle_semantics,
)
from contextor.core.cycle_semantics.optional_scc_publication import (
    OPTIONAL_SCC_PUBLICATION_AUTHORITY,
    OPTIONAL_SCC_PUBLICATION_VERSION,
    CanonicalOptionalSCCReceipt,
    seal_optional_scc_preparation,
    verify_co_published_optional_scc_preparation,
)
from contextor.core.cycle_semantics.warning_eligibility import (
    _verified_model_pass_cycle_paths,
)
from contextor.core.live_state.store import (
    load_snapshot,
    read_metadata,
    save_snapshot,
)
from tests.test_cycle_semantics_optional_generation_verification import (
    _case,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _save(cache, state, origin, *, revision=1, preparation=None):
    state_id = f"optional-state-{revision}"

    return save_snapshot(
        state,
        cache,
        state_id,
        repo_id=origin.repo_id,
        root_path=origin.root_path,
        exact_revision=revision,
        file_state_payload={
            "_meta": {
                "state_id": state_id,
                "revision": revision,
            },
            "files": {},
        },
        prepared_optional_scc_preparation=preparation,
    )


def _load(cache, origin, revision=1):
    result = load_snapshot(
        cache,
        f"optional-state-{revision}",
        expected_repo_id=origin.repo_id,
        expected_root_path=origin.root_path,
    )

    assert result is not None
    return result


def _verify(state, metadata):
    return verify_co_published_optional_scc_preparation(
        state,
        revision=metadata.revision,
        state_id=metadata.state_id,
        repo_id=metadata.repo_id,
        root_path=metadata.root_path,
    )


def test_t01_canonical_writer_seals_and_loader_verifies(
    tmp_path, isolated_dirs,
):
    _, preparation, state, origin = _case(tmp_path)
    cache = tmp_path / "optional-store"

    metadata = _save(
        cache, state, origin, preparation=preparation,
    )
    loaded, loaded_metadata = _load(cache, origin)

    receipt = loaded.cycle_optional_source_publication

    assert type(receipt) is CanonicalOptionalSCCReceipt
    assert receipt.version == OPTIONAL_SCC_PUBLICATION_VERSION
    assert receipt.authority == OPTIONAL_SCC_PUBLICATION_AUTHORITY

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

    assert loaded_metadata == metadata
    assert receipt.preparation == preparation
    assert _verify(loaded, metadata)
    assert _verify(loaded, metadata)

    assert state.cycle_optional_source_publication is None


def test_t02_optional_receipt_does_not_create_legacy_receipts(
    tmp_path, isolated_dirs,
):
    _, preparation, state, origin = _case(tmp_path)
    cache = tmp_path / "optional-store"

    _save(cache, state, origin, preparation=preparation)
    loaded, metadata = _load(cache, origin)

    assert _verify(loaded, metadata)
    assert loaded.cycle_source_publication is None
    assert loaded.cycle_partial_source_publication is None

    assert _verified_model_pass_cycle_paths(
        loaded,
        expected_revision=metadata.revision,
        expected_state_id=metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=metadata.root_path,
    ) == frozenset()


def test_t03_default_store_has_no_optional_receipt(
    tmp_path, isolated_dirs,
):
    _, _, state, origin = _case(tmp_path)
    cache = tmp_path / "optional-store"

    _save(cache, state, origin)
    loaded, metadata = _load(cache, origin)

    assert loaded.cycle_optional_source_publication is None
    assert not _verify(loaded, metadata)

    assert "cycle_optional_source_publication" not in {
        field.name for field in fields(RepositoryAnalysisState)
    }


def test_t04_tampered_receipt_cleared_on_hydration(
    tmp_path, isolated_dirs,
):
    _, preparation, state, origin = _case(tmp_path)
    cache = tmp_path / "optional-store"

    metadata = _save(
        cache, state, origin, preparation=preparation,
    )

    path = cache / metadata.state_file
    payload = pickle.loads(path.read_bytes())
    stored = payload["state"]

    stored.cycle_optional_source_publication = replace(
        stored.cycle_optional_source_publication,
        claims_sha256="0" * 64,
    )

    path.write_bytes(pickle.dumps(payload))

    loaded, loaded_metadata = _load(cache, origin)

    assert loaded_metadata == metadata
    assert loaded.cycle_optional_source_publication is None
    assert loaded.cycles_state == "fresh"
    assert loaded.cycle_semantics is not None
    assert loaded.cycle_source_publication is None
    assert loaded.cycle_partial_source_publication is None


def test_t05_invalid_manifest_cannot_commit(
    tmp_path, isolated_dirs,
):
    _, preparation, state, origin = _case(tmp_path)
    cache = tmp_path / "optional-store"

    forged = replace(
        preparation,
        manifest=replace(
            preparation.manifest,
            source_manifest_sha256="0" * 64,
        ),
    )

    with pytest.raises((ValueError, TypeError)):
        _save(
            cache,
            state,
            origin,
            preparation=forged,
        )

    assert read_metadata(cache) is None


def test_t06_next_revision_without_optin_drops_receipt(
    tmp_path, isolated_dirs,
):
    _, preparation, state, origin = _case(tmp_path)
    cache = tmp_path / "optional-store"

    _save(cache, state, origin, preparation=preparation)
    previous, previous_metadata = _load(cache, origin)

    assert _verify(previous, previous_metadata)

    _save(
        cache,
        previous,
        origin,
        revision=2,
    )

    current, current_metadata = _load(
        cache, origin, revision=2,
    )

    assert current_metadata.revision == 2
    assert current.cycle_optional_source_publication is None
    assert previous.cycle_optional_source_publication is not None


def test_t07_cow_and_invalidation_clear_optional_receipt(
    tmp_path, isolated_dirs,
):
    _, preparation, state, origin = _case(tmp_path)
    cache = tmp_path / "optional-store"

    _save(cache, state, origin, preparation=preparation)
    loaded, metadata = _load(cache, origin)

    assert _verify(loaded, metadata)

    candidate = loaded.clone_for_update()

    assert candidate.cycle_optional_source_publication is None
    assert loaded.cycle_optional_source_publication is not None

    invalidate_cycle_semantics(loaded, "SOURCE_CHANGED")

    assert loaded.cycle_optional_source_publication is None
    assert loaded.cycle_semantics_state == "stale"


def test_t08_foreign_generation_identity_rejected(
    tmp_path, isolated_dirs,
):
    _, preparation, state, origin = _case(tmp_path)
    cache = tmp_path / "optional-store"

    _save(cache, state, origin, preparation=preparation)
    loaded, metadata = _load(cache, origin)

    assert _verify(loaded, metadata)

    assert not verify_co_published_optional_scc_preparation(
        loaded,
        revision=metadata.revision + 1,
        state_id=metadata.state_id,
        repo_id=metadata.repo_id,
        root_path=metadata.root_path,
    )

    assert not verify_co_published_optional_scc_preparation(
        loaded,
        revision=metadata.revision,
        state_id="foreign-state",
        repo_id=metadata.repo_id,
        root_path=metadata.root_path,
    )

    assert not verify_co_published_optional_scc_preparation(
        loaded,
        revision=metadata.revision,
        state_id=metadata.state_id,
        repo_id="foreign-repo",
        root_path=metadata.root_path,
    )


def test_t09_standalone_seal_is_not_durable(
    tmp_path, isolated_dirs,
):
    _, preparation, state, origin = _case(tmp_path)
    cache = tmp_path / "optional-store"

    receipt = seal_optional_scc_preparation(
        state,
        preparation,
        revision=origin.revision,
        state_id=origin.state_id,
        repo_id=origin.repo_id,
        root_path=origin.root_path,
    )

    assert type(receipt) is CanonicalOptionalSCCReceipt
    assert state.cycle_optional_source_publication is None
    assert read_metadata(cache) is None


def test_t10_failed_metadata_commit_preserves_previous(
    tmp_path, isolated_dirs, monkeypatch,
):
    _, preparation, state, origin = _case(tmp_path)
    cache = tmp_path / "optional-store"

    _save(cache, state, origin, preparation=preparation)
    previous, previous_metadata = _load(cache, origin)

    original_replace = store_module.os.replace

    def failing_replace(source, target):
        if target.name == "engine_state.meta.json":
            raise RuntimeError("synthetic metadata failure")
        return original_replace(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(
            store_module.os,
            "replace",
            failing_replace,
        )

        with pytest.raises(
            RuntimeError,
            match="synthetic metadata failure",
        ):
            _save(
                cache,
                previous,
                origin,
                revision=2,
                preparation=preparation,
            )

    assert read_metadata(cache) == previous_metadata

    reloaded, metadata = _load(cache, origin)

    assert metadata.revision == 1
    assert _verify(reloaded, metadata)


def test_t11_stale_canonical_semantics_cannot_seal(
    tmp_path, isolated_dirs,
):
    _, preparation, state, origin = _case(tmp_path)

    state.cycle_semantics_state = "stale"

    with pytest.raises(ValueError):
        seal_optional_scc_preparation(
            state,
            preparation,
            revision=origin.revision,
            state_id=origin.state_id,
            repo_id=origin.repo_id,
            root_path=origin.root_path,
        )

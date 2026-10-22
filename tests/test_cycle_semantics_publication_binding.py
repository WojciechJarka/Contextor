"""P1C1 durable co-publication gates; never runtime safety tests."""

from __future__ import annotations

import pickle
from dataclasses import replace

import pytest

from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
)
from contextor.core.cycle_semantics.generation_manifest import (
    prepare_cycle_source_manifest,
)
from contextor.core.cycle_semantics.lifecycle import (
    invalidate_cycle_semantics,
)
from contextor.core.cycle_semantics.publication_binding import (
    PUBLICATION_AUTHORITY,
    CanonicalCycleManifestReceipt,
    verify_co_published_cycle_manifest,
)
from contextor.core.domain.graph import ProjectGraph
from contextor.core.live_state.store import (
    load_snapshot,
    read_metadata,
    save_snapshot,
)
from tests.test_cycle_semantics_evidence import (
    PAIR,
    PASS,
    _bound,
    _p1b_snapshots,
)


def _case():
    index, snapshot, evidence = _bound(PAIR, PASS)
    prepared = prepare_cycle_source_manifest(
        PAIR,
        index,
        snapshot,
        evidence,
        _p1b_snapshots(PASS),
    )
    state = RepositoryAnalysisState(
        dependency_graph=ProjectGraph(
            hard_edges={key: set(value) for key, value in PAIR.items()},
            soft_edges={},
        ),
        cycle_semantics=snapshot,
        cycle_semantics_state="fresh",
        cycles_state="fresh",
    )
    return state, prepared


def _save(state, root, revision, prepared=None):
    return save_snapshot(
        state,
        root,
        "cycle-state",
        exact_revision=revision,
        file_state_payload={
            "_meta": {
                "state_id": "cycle-state",
                "revision": revision,
            },
            "files": {},
        },
        prepared_cycle_manifest=prepared,
    )


def test_p1c1_t01_receipt_is_committed_with_exact_generation(tmp_path):
    state, prepared = _case()
    metadata = _save(state, tmp_path, 1, prepared)
    loaded, loaded_metadata = load_snapshot(
        tmp_path, "cycle-state",
    )

    receipt = loaded.cycle_source_publication
    assert isinstance(receipt, CanonicalCycleManifestReceipt)
    assert receipt.authority == PUBLICATION_AUTHORITY
    assert receipt.revision == metadata.revision == 1
    assert receipt.state_id == metadata.state_id
    assert receipt.prepared_manifest == prepared
    assert len(receipt.model_claims_sha256) == 64
    assert loaded_metadata == metadata
    assert verify_co_published_cycle_manifest(
        loaded,
        revision=metadata.revision,
        state_id=metadata.state_id,
        repo_id=metadata.repo_id,
        root_path=metadata.root_path,
    )

    # Writer does not expose receipt on its original object.
    assert state.cycle_source_publication is None


def test_p1c1_t02_no_prepared_input_means_no_receipt(tmp_path):
    state, _ = _case()
    _save(state, tmp_path, 1)
    loaded, _ = load_snapshot(tmp_path, "cycle-state")
    assert loaded.cycle_source_publication is None


def test_p1c1_t03_incomplete_manifest_does_not_commit(tmp_path):
    state, prepared = _case()
    _save(state, tmp_path, 1, prepared)

    forged = replace(
        prepared,
        source_manifest_sha256="f" * 64,
    )
    with pytest.raises(ValueError):
        _save(state, tmp_path, 2, forged)

    assert read_metadata(tmp_path).revision == 1
    loaded, metadata = load_snapshot(
        tmp_path, "cycle-state",
    )
    assert metadata.revision == 1
    assert loaded.cycle_source_publication is not None


def test_p1c1_t04_new_revision_cannot_reuse_old_receipt(tmp_path):
    state, prepared = _case()
    _save(state, tmp_path, 1, prepared)
    old, _ = load_snapshot(tmp_path, "cycle-state")
    assert old.cycle_source_publication is not None

    _save(old, tmp_path, 2)
    loaded, metadata = load_snapshot(
        tmp_path, "cycle-state",
    )
    assert metadata.revision == 2
    assert loaded.cycle_source_publication is None


def test_p1c1_t05_failed_metadata_commit_preserves_previous(tmp_path, monkeypatch):
    import contextor.core.live_state.store as store

    state, prepared = _case()
    _save(state, tmp_path, 1, prepared)

    original_replace = store.os.replace

    def fail_metadata(source, target):
        if target.name == "engine_state.meta.json":
            raise RuntimeError("synthetic commit failure")
        return original_replace(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(store.os, "replace", fail_metadata)
        with pytest.raises(RuntimeError, match="synthetic commit failure"):
            _save(state, tmp_path, 2, prepared)

    loaded, metadata = load_snapshot(
        tmp_path, "cycle-state",
    )
    assert metadata.revision == 1
    assert loaded.cycle_source_publication.revision == 1


def test_p1c1_t06_foreign_revision_receipt_fails_closed(tmp_path):
    state, prepared = _case()
    metadata = _save(state, tmp_path, 1, prepared)

    state_file = tmp_path / metadata.state_file
    payload = pickle.loads(state_file.read_bytes())
    original = payload["state"].cycle_source_publication
    payload["state"].cycle_source_publication = replace(
        original,
        revision=999,
    )
    state_file.write_bytes(pickle.dumps(payload))

    loaded, loaded_metadata = load_snapshot(
        tmp_path, "cycle-state",
    )
    assert loaded_metadata.revision == 1
    assert loaded.cycle_source_publication is None


def test_p1c1_t07_cow_invalidates_without_mutating_previous():
    state, prepared = _case()
    state.revision = 1
    state.state_id = "cycle-state"

    from contextor.core.cycle_semantics.publication_binding import (
        seal_prepared_cycle_manifest,
    )

    state.cycle_source_publication = seal_prepared_cycle_manifest(
        state,
        prepared,
        revision=1,
        state_id="cycle-state",
        repo_id="",
        root_path="",
    )

    candidate = state.clone_for_update()
    assert candidate is not state
    assert candidate.cycle_source_publication is None
    assert state.cycle_source_publication is not None

    invalidate_cycle_semantics(
        state,
        "SOURCE_CHANGED",
    )
    assert state.cycle_source_publication is None
    assert state.cycle_semantics_state == "stale"


def test_p1c1_t08_classification_claim_has_distinct_digest(tmp_path):
    state, prepared = _case()
    metadata = _save(state, tmp_path, 1, prepared)
    loaded, _ = load_snapshot(tmp_path, "cycle-state")
    receipt = loaded.cycle_source_publication

    assert receipt.model_claims_sha256 != (
        prepared.source_manifest_sha256
    )

    tampered_claim = replace(
        prepared.components[0],
        model_classification=(
            "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
        ),
    )
    tampered_manifest = replace(
        prepared,
        components=(tampered_claim,),
    )
    loaded.cycle_source_publication = replace(
        receipt,
        prepared_manifest=tampered_manifest,
    )
    assert not verify_co_published_cycle_manifest(
        loaded,
        revision=metadata.revision,
        state_id=metadata.state_id,
        repo_id=metadata.repo_id,
        root_path=metadata.root_path,
    )


def test_p1c1_t09_partial_or_stale_state_cannot_seal(tmp_path):
    state, prepared = _case()
    state.cycle_semantics_state = "stale"
    with pytest.raises(ValueError):
        _save(state, tmp_path, 1, prepared)
    assert read_metadata(tmp_path) is None


def test_p1c1_t10_legacy_missing_receipt_is_unavailable():
    state, _ = _case()
    assert state.cycle_source_publication is None
    del state.__dict__["cycle_source_publication"]
    assert state.cycle_source_publication is None
    assert not verify_co_published_cycle_manifest(
        state,
        revision=1,
        state_id="cycle-state",
        repo_id="",
        root_path="",
    )

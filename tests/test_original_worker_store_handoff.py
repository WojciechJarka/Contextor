"""P1D2H: optional prepared-manifest handoff to canonical store."""

from __future__ import annotations

from dataclasses import replace

import pytest

import contextor.core.live_state as live_state

from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    load_engine_state,
    save_engine_state,
)
from contextor.core.cycle_semantics.publication_binding import (
    PUBLICATION_AUTHORITY,
    CanonicalCycleManifestReceipt,
    verify_co_published_cycle_manifest,
)
from contextor.core.live_state.store import read_metadata
from tests.test_cycle_semantics_publication_binding import _case


_STATE_ID = "cycle-state"
_REPO_ID = "p1d2h-fixture-repo"


def _save(root, state, revision, prepared=None):
    return save_engine_state(
        state,
        str(root),
        _STATE_ID,
        writer="desktop",
        repo_id=_REPO_ID,
        root_path=str(root.resolve()),
        exact_revision=revision,
        file_state_payload={
            "_meta": {
                "state_id": _STATE_ID,
                "revision": revision,
            },
            "files": {},
        },
        prepared_cycle_manifest=prepared,
    )


def _load(root):
    return load_engine_state(
        str(root),
        _STATE_ID,
        expected_repo_id=_REPO_ID,
        expected_root_path=str(root.resolve()),
    )


def test_p1d2h_t01_valid_manifest_sealed_in_same_generation(
    tmp_path,
):
    state, prepared = _case()

    metadata = _save(
        tmp_path,
        state,
        1,
        prepared,
    )

    assert metadata is not None
    assert metadata.revision == 1
    assert metadata.state_id == _STATE_ID
    assert metadata.repo_id == _REPO_ID
    assert metadata.root_path == str(tmp_path.resolve())

    loaded = _load(tmp_path)

    assert isinstance(loaded, RepositoryAnalysisState)
    assert loaded is not state

    receipt = loaded.cycle_source_publication

    assert isinstance(
        receipt,
        CanonicalCycleManifestReceipt,
    )
    assert receipt.authority == PUBLICATION_AUTHORITY
    assert receipt.revision == metadata.revision
    assert receipt.state_id == metadata.state_id
    assert receipt.repo_id == metadata.repo_id
    assert receipt.root_path == metadata.root_path
    assert receipt.prepared_manifest == prepared

    assert verify_co_published_cycle_manifest(
        loaded,
        revision=metadata.revision,
        state_id=metadata.state_id,
        repo_id=metadata.repo_id,
        root_path=metadata.root_path,
    )

    assert state.cycle_source_publication is None


def test_p1d2h_t02_default_save_does_not_create_receipt(
    tmp_path,
):
    state, _prepared = _case()

    metadata = _save(
        tmp_path,
        state,
        1,
    )

    assert metadata is not None
    assert metadata.revision == 1

    loaded = _load(tmp_path)

    assert loaded is not None
    assert loaded.cycle_source_publication is None
    assert state.cycle_source_publication is None


def test_p1d2h_t03_forged_manifest_cannot_commit(
    tmp_path,
):
    state, prepared = _case()

    forged = replace(
        prepared,
        source_manifest_sha256="f" * 64,
    )

    result = _save(
        tmp_path,
        state,
        1,
        forged,
    )

    assert result is None
    assert read_metadata(tmp_path) is None
    assert _load(tmp_path) is None
    assert state.cycle_source_publication is None


def test_p1d2h_t04_stale_semantics_cannot_commit_receipt(
    tmp_path,
):
    state, prepared = _case()

    state.cycle_semantics_state = "stale"

    result = _save(
        tmp_path,
        state,
        1,
        prepared,
    )

    assert result is None
    assert read_metadata(tmp_path) is None
    assert _load(tmp_path) is None
    assert state.cycle_source_publication is None


def test_p1d2h_t05_next_generation_drops_old_receipt(
    tmp_path,
):
    state, prepared = _case()

    first = _save(
        tmp_path,
        state,
        1,
        prepared,
    )
    assert first is not None

    old = _load(tmp_path)

    assert old is not None
    assert isinstance(
        old.cycle_source_publication,
        CanonicalCycleManifestReceipt,
    )

    second = _save(
        tmp_path,
        old,
        2,
    )

    assert second is not None
    assert second.revision == 2

    current = _load(tmp_path)

    assert current is not None
    assert current.revision == 2
    assert current.cycle_source_publication is None

    assert old.cycle_source_publication is not None


def test_p1d2h_t06_default_store_call_shape_unchanged(
    tmp_path, monkeypatch,
):
    observed = []
    marker = object()

    def observed_save(*args, **kwargs):
        observed.append((args, kwargs))
        return marker

    monkeypatch.setattr(
        live_state,
        "save_snapshot",
        observed_save,
    )

    state = RepositoryAnalysisState()

    result = save_engine_state(
        state,
        str(tmp_path),
        "probe-state",
    )

    assert result is marker
    assert len(observed) == 1

    args, kwargs = observed[0]

    assert args == (
        state,
        str(tmp_path),
        "probe-state",
    )

    assert "prepared_cycle_manifest" not in kwargs
    assert kwargs["writer"] == "unknown"
    assert kwargs["repo_id"] == ""
    assert kwargs["root_path"] == ""
    assert kwargs["exact_revision"] is None
    assert kwargs["file_state_payload"] is None


def test_p1d2h_t07_explicit_manifest_forwarded_unchanged(
    tmp_path, monkeypatch,
):
    state, prepared = _case()
    observed = []
    marker = object()

    def observed_save(*args, **kwargs):
        observed.append((args, kwargs))
        return marker

    monkeypatch.setattr(
        live_state,
        "save_snapshot",
        observed_save,
    )

    result = save_engine_state(
        state,
        str(tmp_path),
        _STATE_ID,
        prepared_cycle_manifest=prepared,
    )

    assert result is marker
    assert len(observed) == 1

    args, kwargs = observed[0]

    assert args == (
        state,
        str(tmp_path),
        _STATE_ID,
    )
    assert kwargs["prepared_cycle_manifest"] is prepared
    assert state.cycle_source_publication is None


def test_p1d2h_t08_invalid_graph_claim_cannot_commit(
    tmp_path,
):
    state, prepared = _case()

    forged = replace(
        prepared,
        graph_sha256="0" * 64,
    )

    result = _save(
        tmp_path,
        state,
        1,
        forged,
    )

    assert result is None
    assert read_metadata(tmp_path) is None
    assert _load(tmp_path) is None
    assert state.cycle_source_publication is None


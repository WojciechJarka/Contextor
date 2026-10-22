"""P1C2 in-process canonical publication integration gates.

Tests real durable snapshot and CanonicalLiveServer code paths.
No connection to the user's running MCP/LIVE service.
No source-origin authentication or runtime import safety.
"""

from __future__ import annotations

import pickle
from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace

import pytest

from contextor.core.cycle_semantics.publication_binding import (
    CanonicalCycleManifestReceipt,
    verify_co_published_cycle_manifest,
)
from contextor.core.live_state.ipc import CanonicalLiveServer
from contextor.core.live_state.store import (
    load_snapshot,
    locked_committed_snapshot,
    read_metadata,
)
from tests.test_cycle_semantics_full_integration import _run_full
from tests.test_cycle_semantics_publication_binding import (
    _case,
    _save,
)


pytestmark = pytest.mark.live


@contextmanager
def _server(
    cache_dir,
    *,
    state=None,
    revision=0,
    updater=None,
    persister=None,
):
    """Use the real server against an isolated committed store."""
    server = CanonicalLiveServer(
        state,
        revision=revision,
        updater=updater,
        persister=persister,
        committed_snapshot_reader=lambda: locked_committed_snapshot(
            cache_dir,
            expected_repo_id="",
            expected_root_path="",
        ),
    )
    try:
        yield server
    finally:
        server.close()


def _publish(server, candidate, *, acknowledge=False):
    return server._dispatch({
        "operation": "publish",
        "state": candidate,
        "origin": "p1c2_integration",
        "acknowledge_installed": acknowledge,
    })


def _assert_receipt(state, metadata):
    receipt = state.cycle_source_publication
    assert isinstance(receipt, CanonicalCycleManifestReceipt)
    assert receipt.revision == metadata.revision
    assert receipt.state_id == metadata.state_id
    assert verify_co_published_cycle_manifest(
        state,
        revision=metadata.revision,
        state_id=metadata.state_id,
        repo_id=metadata.repo_id,
        root_path=metadata.root_path,
    )
    return receipt


def test_p1c2_t01_real_full_does_not_invent_receipt(
    tmp_path, isolated_dirs, monkeypatch,
):
    """Current FULL has no authenticated prepared-manifest input."""
    monkeypatch.setenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL", "1"
    )

    root = tmp_path / "repo"
    package = root / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    (package / "a.py").write_text(
        "import pkg.b\ndef fa():\n    return 1\n",
        encoding="utf-8",
    )
    (package / "b.py").write_text(
        "import pkg.a\ndef fb():\n    return 2\n",
        encoding="utf-8",
    )

    state, _result = _run_full(root)

    assert state.cycle_semantics_state == "fresh"
    assert state.cycles_state == "fresh"
    assert state.cycles
    assert state.cycle_semantics is not None
    assert state.cycle_semantics.source_snapshot_binding == (
        "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    )

    # FULL does not supply P1C0 to the canonical writer yet.
    assert state.cycle_source_publication is None


def test_p1c2_t02_committed_store_to_live_install(tmp_path):
    state, prepared = _case()
    metadata = _save(state, tmp_path, 1, prepared)

    assert state.cycle_source_publication is None

    with _server(tmp_path) as server:
        answer = _publish(server, state)

        assert answer["status"] == "ok"
        assert answer["revision"] == 1
        assert answer["source"] == "committed_snapshot"

        active = server._dispatch({
            "operation": "snapshot",
        })
        assert active["status"] == "ok"
        assert active["revision"] == 1
        assert active["state"] is not state

        receipt = _assert_receipt(
            active["state"], metadata,
        )
        assert receipt.prepared_manifest == prepared

        assert server._events[-1]["operation"] == "publish"
        assert server._events[-1]["revision"] == 1


def test_p1c2_t03_incremental_commit_invalidates_receipt(
    tmp_path,
):
    state, prepared = _case()
    _save(state, tmp_path, 1, prepared)

    observed = []

    def updater(candidate, path):
        observed.append(candidate.cycle_source_publication)
        candidate.cycle_semantics_state = "stale"
        candidate.cycle_semantics_invalidation_reason = (
            "SOURCE_CHANGED"
        )
        return SimpleNamespace(
            status="UPDATED",
            file_path=path,
        )

    def persister(candidate, revision):
        assert candidate.cycle_source_publication is None
        _save(candidate, tmp_path, revision)

    with _server(
        tmp_path,
        updater=updater,
        persister=persister,
    ) as server:
        assert _publish(server, state)["status"] == "ok"

        previous = server._state
        assert previous.cycle_source_publication is not None

        changed = server._dispatch({
            "operation": "update_file",
            "file_path": "a.py",
            "origin": "desktop_watcher",
        })

        assert changed["status"] == "ok"
        assert changed["revision"] == 2
        assert observed == [None]

        current = server._state
        assert current is not previous
        assert current.revision == 2
        assert current.cycle_source_publication is None
        assert current.cycle_semantics_state == "stale"

        # COW must preserve the previous object.
        assert previous.revision == 1
        assert previous.cycle_source_publication is not None

    restored, metadata = load_snapshot(
        tmp_path, "cycle-state",
    )
    assert metadata.revision == 2
    assert restored.cycle_source_publication is None


def test_p1c2_t04_failed_incremental_persistence_rolls_back(
    tmp_path,
):
    state, prepared = _case()
    metadata = _save(state, tmp_path, 1, prepared)

    def updater(candidate, path):
        candidate.cycle_semantics_state = "stale"
        return SimpleNamespace(
            status="UPDATED",
            file_path=path,
        )

    def rejected_persistence(_candidate, _revision):
        raise RuntimeError("synthetic persistence failure")

    with _server(
        tmp_path,
        updater=updater,
        persister=rejected_persistence,
    ) as server:
        assert _publish(server, state)["status"] == "ok"

        original = server._state
        original_receipt = _assert_receipt(
            original, metadata,
        )
        original_event_count = len(server._events)

        failed = server._dispatch({
            "operation": "update_file",
            "file_path": "a.py",
            "origin": "desktop_watcher",
        })

        assert failed["status"] == "error"
        assert failed["error"] == (
            "canonical_persistence_failed"
        )
        assert failed["revision"] == 1
        assert server._revision == 1
        assert server._state is original
        assert server._state.cycle_source_publication == (
            original_receipt
        )
        assert len(server._events) == original_event_count

    restored, restored_metadata = load_snapshot(
        tmp_path, "cycle-state",
    )
    assert restored_metadata.revision == 1
    _assert_receipt(restored, restored_metadata)


def test_p1c2_t05_restart_from_committed_generation(
    tmp_path,
):
    state, prepared = _case()
    _save(state, tmp_path, 1, prepared)

    with _server(tmp_path) as first:
        assert _publish(first, state)["status"] == "ok"
        first_receipt = first._state.cycle_source_publication
        assert first_receipt is not None

    recovered, metadata = load_snapshot(
        tmp_path, "cycle-state",
    )
    _assert_receipt(recovered, metadata)

    with _server(
        tmp_path,
        state=recovered,
        revision=metadata.revision,
    ) as second:
        snapshot = second._dispatch({
            "operation": "snapshot",
        })

        assert snapshot["status"] == "ok"
        assert snapshot["revision"] == 1
        assert snapshot["state"].cycle_source_publication == (
            first_receipt
        )
        _assert_receipt(snapshot["state"], metadata)


def test_p1c2_t06_tampered_durable_receipt_is_not_installed(
    tmp_path,
):
    state, prepared = _case()
    metadata = _save(state, tmp_path, 1, prepared)

    payload_path = tmp_path / metadata.state_file
    payload = pickle.loads(payload_path.read_bytes())

    receipt = payload["state"].cycle_source_publication
    assert receipt is not None

    payload["state"].cycle_source_publication = replace(
        receipt,
        revision=999,
    )
    payload_path.write_bytes(pickle.dumps(payload))

    recovered, recovered_metadata = load_snapshot(
        tmp_path, "cycle-state",
    )
    assert recovered_metadata.revision == 1
    assert recovered.cycle_source_publication is None

    with _server(tmp_path) as server:
        answer = _publish(server, state)

        assert answer["status"] == "ok"
        assert answer["revision"] == 1
        assert server._state.cycle_source_publication is None

        # The server may install valid structural state.
        # It must not resurrect a rejected semantic receipt.
        assert server._state.cycle_semantics is not None


def test_p1c2_t07_failed_store_commit_cannot_publish_claim(
    tmp_path,
):
    state, prepared = _case()
    _save(state, tmp_path, 1, prepared)

    with _server(tmp_path) as server:
        assert _publish(server, state)["status"] == "ok"
        previous = server._state
        previous_receipt = previous.cycle_source_publication

        forged = replace(
            prepared,
            source_manifest_sha256="f" * 64,
        )

        with pytest.raises(ValueError):
            _save(state, tmp_path, 2, forged)

        assert read_metadata(tmp_path).revision == 1

        # Candidate is now revision 2, but the durable
        # authoritative generation remains revision 1.
        refused = _publish(server, state)

        assert refused["status"] == "error"
        assert refused["error"] == (
            "committed_publish_generation_mismatch"
        )
        assert server._revision == 1
        assert server._state is previous
        assert server._state.cycle_source_publication == (
            previous_receipt
        )


def test_p1c2_t08_idempotent_publish_does_not_reseal(
    tmp_path,
):
    state, prepared = _case()
    metadata = _save(state, tmp_path, 1, prepared)

    with _server(tmp_path) as server:
        assert _publish(server, state)["status"] == "ok"

        previous = server._state
        previous_receipt = _assert_receipt(
            previous, metadata,
        )
        previous_seq = server._activity_seq

        repeated = _publish(
            server,
            state,
            acknowledge=True,
        )

        assert repeated["status"] == "ok"
        assert repeated["already_installed"] is True
        assert repeated["revision"] == 1
        assert server._state is previous
        assert server._activity_seq == previous_seq
        assert server._state.cycle_source_publication == (
            previous_receipt
        )

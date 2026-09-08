import json
import os

import pytest

import contextor.core.runtime_trace as trace
from contextor.core.live_state.ipc import CanonicalLiveServer
from contextor.core.live_state.runtime_domain import RuntimeDomain
from contextor.core.live_state.runtime_lease import ProcessIdentity, RuntimeLeaseManager


@pytest.fixture
def trace_logs(tmp_path, monkeypatch):
    trace.finish_desktop_trace_session()
    trace._authority_emitters.clear()
    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: tmp_path)
    yield tmp_path
    trace.finish_desktop_trace_session()
    trace._authority_emitters.clear()


def _records(emitter):
    return [json.loads(line) for line in emitter.log_path.read_text(encoding="utf-8").splitlines()
            if json.loads(line).get("_type") == "authority_event"]


def _state(logs):
    return json.loads((logs / "authority_event_state.json").read_text(encoding="utf-8"))


def _lease_domain(tmp_path):
    context = tmp_path / "context"
    return RuntimeDomain.create(
        repo_id="repo",
        repo_root=tmp_path / "repo",
        mode="test",
        cache_root=context / "cache",
        logs_root=context / "logs",
        lock_root=context / "cache" / "runtime",
        ipc_endpoint_root=context / "cache" / "ipc",
        test_context_root=context,
        test_run_id="run",
        known_production_roots=(tmp_path / "production-cache", tmp_path / "production-logs"),
    )


def test_authority_events_share_runtime_trace_and_have_strict_envelope(trace_logs):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", repo_id="repo", logs_root=trace_logs)
    first = emitter.emit("RUNTIME_AUTHORITY_START", source="test")
    second = emitter.emit("RUNTIME_AUTHORITY_READY", source="test")
    records = _records(emitter)
    assert emitter.log_path.parent == trace_logs
    assert (first.sequence, second.sequence) == (1, 2)
    assert [item["event_id"] for item in records] == [first.event_id, second.event_id]
    assert all(item["_type"] == "authority_event" and item["schema"] == trace.AUTHORITY_EVENT_SCHEMA for item in records)


def test_jsonl_fsync_precedes_sidecar_high_water(trace_logs, monkeypatch):
    order = []
    original_fsync, original_write = trace.os.fsync, trace._write_authority_sidecar

    def fsync(fd):
        order.append("fsync")
        return original_fsync(fd)

    def write(*args, **kwargs):
        order.append("sidecar")
        return original_write(*args, **kwargs)

    monkeypatch.setattr(trace.os, "fsync", fsync)
    monkeypatch.setattr(trace, "_write_authority_sidecar", write)
    trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs).emit("TEST")
    assert order.index("fsync") < order.index("sidecar")


def test_crash_after_jsonl_before_sidecar_recovers_same_sequence(trace_logs, monkeypatch):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    original = trace._write_authority_sidecar
    monkeypatch.setattr(trace, "_write_authority_sidecar", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("crash")))
    with pytest.raises(OSError):
        emitter.emit("CRASH_POINT")
    monkeypatch.setattr(trace, "_write_authority_sidecar", original)
    recovered = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    assert recovered.emit("AFTER_RECOVERY").sequence == 2


def test_pending_replay_keeps_identity_and_requires_mapping_ack(trace_logs):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    event = emitter.emit("PENDING")
    emitter.attach_live_sink(lambda _event: True, handoff_epoch="epoch-a")
    assert emitter.replay_pending() == 0
    delivered = []
    emitter.attach_live_sink(lambda value: delivered.append(value) or {"accepted": True, "activity_epoch": "epoch-a"}, handoff_epoch="epoch-a")
    assert emitter.replay_pending() == 1
    assert delivered[0]["event_id"] == event.event_id
    assert _state(trace_logs)["domains"]["domain-a"]["live_handoff_cursor"] == 1


def test_server_duplicate_and_conflicting_identity(trace_logs):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    event = emitter.emit("EVENT")
    server = CanonicalLiveServer(None, revision=0, authority_identity={"runtime_domain_id": "domain-a"})
    try:
        assert server.record_authority_event(event.to_dict())["accepted"] is True
        assert server.record_authority_event(event.to_dict()) == {"accepted": True, "duplicate": True, "activity_epoch": server.activity_epoch}
        changed = event.to_dict()
        changed["status"] = "ALTERED"
        result = server.record_authority_event(changed)
        assert result["accepted"] is False and result["conflict"] is True
    finally:
        server.close()


def test_delivery_conflict_is_durable_once_without_recursive_delivery(trace_logs):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    emitter.attach_live_sink(lambda _event: {"accepted": False, "conflict": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
    emitter.emit("EVENT")
    assert [record["event_type"] for record in _records(emitter)] == ["EVENT", "AUTHORITY_EVENT_DELIVERY_CONFLICT"]


def test_malformed_or_truncated_unindexed_tail_fails_closed(trace_logs):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    emitter.emit("VALID")
    with emitter.log_path.open("ab") as stream:
        stream.write(b'{"event_id":"truncated"')
    with pytest.raises(trace.AuthorityEventRecoveryError):
        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)


def test_two_runtime_domains_have_independent_sequences(trace_logs):
    left = trace.AuthorityEventEmitter(runtime_domain_id="domain-left", logs_root=trace_logs)
    right = trace.AuthorityEventEmitter(runtime_domain_id="domain-right", logs_root=trace_logs)
    assert left.emit("LEFT").sequence == 1
    assert right.emit("RIGHT").sequence == 1
    assert left.emit("LEFT_AGAIN").sequence == 2


def test_runtimelease_emitter_actually_called_after_outer_lock_release(tmp_path):
    domain = _lease_domain(tmp_path)
    events = []
    manager = None

    def callback(event_type, **fields):
        events.append(event_type)
        manager.read_generation()

    manager = RuntimeLeaseManager(domain, process_identity=ProcessIdentity(os.getpid(), "test-start"), authority_event_emitter=callback)
    manager.acquire()
    assert {"RUNTIME_LEASE_ACQUIRE", "RUNTIME_LEASE_RESERVATION", "RUNTIME_LEASE_ACTIVATION"} <= set(events)


def test_runtimelease_bind_release_desktop_events_are_emitted_outside_lock(tmp_path):
    domain = _lease_domain(tmp_path)
    events = []
    manager = RuntimeLeaseManager(domain, process_identity=ProcessIdentity(os.getpid(), "test-start"), authority_event_emitter=lambda event_type, **fields: events.append(event_type))
    lease = manager.acquire()
    manager.bind_endpoint(lease, "endpoint")
    manager.claim_desktop(lease, "desktop", ProcessIdentity(os.getpid(), "desktop-start"))
    manager.release_desktop_claim(lease, "desktop", ProcessIdentity(os.getpid(), "desktop-start"))
    manager.release(lease)
    assert {"RUNTIME_ENDPOINT_BIND", "DESKTOP_CLAIM_ACQUIRE", "DESKTOP_CLAIM_RELEASE", "RUNTIME_LEASE_RELEASE"} <= set(events)


def test_trace_session_rollover_preserves_domain_sequence(trace_logs):
    first = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    event = first.emit("FIRST")
    old_path = first.log_path
    trace.finish_desktop_trace_session()
    second = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    assert second.log_path != old_path
    assert second.emit("SECOND").sequence == event.sequence + 1


def test_pending_event_from_previous_trace_segment_replays_after_rollover(trace_logs):
    first = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    event = first.emit("PENDING")
    old_path = first.log_path
    trace.finish_desktop_trace_session()
    second = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    delivered = []
    second.attach_live_sink(lambda value: delivered.append(value) or {"accepted": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
    assert second.replay_pending() == 1
    assert delivered[0]["event_id"] == event.event_id and delivered[0]["sequence"] == event.sequence
    assert delivered[0]["timestamp"] == event.timestamp and old_path.exists()


def test_missing_old_pending_segment_fails_closed(trace_logs):
    first = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    first.emit("PENDING")
    old_path = first.log_path
    trace.finish_desktop_trace_session()
    old_path.unlink()
    with pytest.raises(trace.AuthorityEventRecoveryError):
        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)


def test_quiet_domain_survives_other_domain_beyond_recovery_window(trace_logs, monkeypatch):
    first = trace.AuthorityEventEmitter(runtime_domain_id="quiet", logs_root=trace_logs)
    assert first.emit("QUIET").sequence == 1
    other = trace.AuthorityEventEmitter(runtime_domain_id="busy", logs_root=trace_logs)
    monkeypatch.setattr(trace, "_AUTHORITY_RECOVERY_WINDOW", 64)
    for index in range(20):
        other.emit(f"BUSY_{index}")
    assert first.emit("QUIET_NEXT").sequence == 2


def test_sidecar_cursor_ahead_of_highwater_fails_closed(trace_logs):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    emitter.emit("EVENT")
    sidecar = _state(trace_logs)
    sidecar["domains"]["domain-a"]["live_handoff_cursor"] = 2
    (trace_logs / "authority_event_state.json").write_text(json.dumps(sidecar), encoding="utf-8")
    with pytest.raises(trace.AuthorityEventRecoveryError):
        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)


def test_sidecar_broken_pending_range_fails_closed(trace_logs):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    emitter.emit("EVENT")
    sidecar = _state(trace_logs)
    sidecar["domains"]["domain-a"]["pending_end_sequence"] = None
    (trace_logs / "authority_event_state.json").write_text(json.dumps(sidecar), encoding="utf-8")
    with pytest.raises(trace.AuthorityEventRecoveryError):
        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)


def test_pending_index_over_limit_fails_closed(trace_logs, monkeypatch):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    emitter.emit("EVENT")
    sidecar = _state(trace_logs)
    sidecar["domains"]["domain-a"]["pending_index"] = sidecar["domains"]["domain-a"]["pending_index"] * 2
    monkeypatch.setattr(trace, "_AUTHORITY_PENDING_LIMIT", 1)
    (trace_logs / "authority_event_state.json").write_text(json.dumps(sidecar), encoding="utf-8")
    with pytest.raises(trace.AuthorityEventRecoveryError):
        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)


@pytest.mark.parametrize("ack", [lambda _event: None, lambda _event: True])
def test_none_or_truthy_nonmapping_sink_does_not_ack(trace_logs, ack):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    emitter.emit("EVENT")
    emitter.attach_live_sink(ack, handoff_epoch="epoch")
    assert emitter.replay_pending() == 0
    assert _state(trace_logs)["domains"]["domain-a"]["live_handoff_cursor"] == 0


def test_handoff_epoch_mismatch_does_not_ack(trace_logs):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    emitter.emit("EVENT")
    emitter.attach_live_sink(lambda _event: {"accepted": True, "activity_epoch": "foreign"}, handoff_epoch="attached")
    assert emitter.replay_pending() == 0


def test_conflict_dedupe_survives_emitter_restart(trace_logs):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    emitter.attach_live_sink(lambda _event: {"accepted": False, "conflict": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
    emitter.emit("EVENT")
    assert [x["event_type"] for x in _records(emitter)].count("AUTHORITY_EVENT_DELIVERY_CONFLICT") == 1
    restarted = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    restarted.attach_live_sink(lambda _event: {"accepted": False, "conflict": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
    restarted.replay_pending()
    assert [x["event_type"] for x in _records(restarted)].count("AUTHORITY_EVENT_DELIVERY_CONFLICT") == 1


def test_detached_sink_keeps_shutdown_event_pending(trace_logs):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    emitter.attach_live_sink(lambda _event: {"accepted": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
    emitter.detach_live_sink()
    emitter.emit("RUNTIME_SHUTDOWN")
    assert _state(trace_logs)["domains"]["domain-a"]["pending_start_sequence"] == 1


def test_pending_shutdown_replays_on_next_server_with_original_identity(trace_logs):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    event = emitter.emit("RUNTIME_SHUTDOWN")
    received = []
    restarted = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    restarted.attach_live_sink(lambda value: received.append(value) or {"accepted": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
    assert restarted.replay_pending() == 1
    assert received[0]["event_id"] == event.event_id


def test_unresolved_shutdown_not_reported_as_stopped():
    assert "UNRESOLVED" in __import__("contextor.core.live_state.runtime", fromlist=["run_service"]).__dict__.get("run_service").__code__.co_consts


def test_crash_after_authority_jsonl_fsync_then_trace_rollover_recovers_old_segment(trace_logs, monkeypatch):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    emitter.emit("FIRST")
    original = trace._write_authority_sidecar
    monkeypatch.setattr(trace, "_write_authority_sidecar", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("crash")))
    with pytest.raises(OSError):
        emitter.emit("CRASHED")
    monkeypatch.setattr(trace, "_write_authority_sidecar", original)
    old_path = emitter.log_path
    crashed = _records(emitter)[-1]
    trace.finish_desktop_trace_session()
    recovered = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    assert recovered.log_path != old_path
    assert recovered.emit("THIRD").sequence == 3
    pending = _state(trace_logs)["domains"]["domain-a"]["pending_index"]
    assert any(item["event_id"] == crashed["event_id"] and item["sequence"] == 2 and item["trace_path"] == str(old_path) for item in pending)


def test_old_segment_unindexed_range_over_recovery_bound_fails_closed(trace_logs, monkeypatch):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    original = trace._write_authority_sidecar
    monkeypatch.setattr(trace, "_write_authority_sidecar", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("crash")))
    with pytest.raises(OSError):
        emitter.emit("CRASHED", reason="x" * 500)
    monkeypatch.setattr(trace, "_write_authority_sidecar", original)
    trace.finish_desktop_trace_session()
    monkeypatch.setattr(trace, "_AUTHORITY_RECOVERY_WINDOW", 32)
    with pytest.raises(trace.AuthorityEventRecoveryError):
        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)


def test_authority_duplicate_remains_idempotent_after_projection_evicted():
    server = CanonicalLiveServer(None, revision=0, retention=2, authority_identity={"runtime_domain_id": "domain-a"})
    try:
        event = trace.AuthorityEvent("id", "2026-01-01T00:00:00+00:00", 1, "EVENT", runtime_domain_id="domain-a").to_dict()
        assert server.record_authority_event(event)["accepted"]
        for index in range(3):
            server._record_event("status", {"origin": "desktop", "status": str(index)})
        assert server.record_authority_event(event)["duplicate"] is True
    finally:
        server.close()


def test_authority_conflict_detected_after_projection_evicted():
    server = CanonicalLiveServer(None, revision=0, retention=2, authority_identity={"runtime_domain_id": "domain-a"})
    try:
        event = trace.AuthorityEvent("id", "2026-01-01T00:00:00+00:00", 1, "EVENT", runtime_domain_id="domain-a").to_dict()
        server.record_authority_event(event)
        for index in range(3):
            server._record_event("status", {"origin": "desktop", "status": str(index)})
        event["status"] = "changed"
        assert server.record_authority_event(event)["conflict"] is True
    finally:
        server.close()


def test_conflict_jsonl_fsync_crash_before_sidecar_dedupe_survives_restart(trace_logs, monkeypatch):
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    emitter.attach_live_sink(lambda _event: {"accepted": False, "conflict": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
    original, calls = trace._write_authority_sidecar, 0
    def crash_after_primary(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("crash")
        return original(*args, **kwargs)
    monkeypatch.setattr(trace, "_write_authority_sidecar", crash_after_primary)
    with pytest.raises(OSError):
        emitter.emit("EVENT")
    monkeypatch.setattr(trace, "_write_authority_sidecar", original)
    restarted = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
    restarted.attach_live_sink(lambda _event: {"accepted": False, "conflict": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
    restarted.replay_pending()
    assert [x["event_type"] for x in _records(restarted)].count("AUTHORITY_EVENT_DELIVERY_CONFLICT") == 1


def test_authority_startup_replay_does_not_skip_live_or_mcp_events():
    from contextor.core.live_state.watcher import DesktopLiveEventFeed
    events = [
        {"seq": 1, "category": "LIVE_STATE", "operation": "update_file", "origin": "desktop", "file_path": "a.py"},
        {"seq": 2, "category": "AUTHORITY", "runtime_domain_id": "d", "sequence": 1, "event_id": "a", "event_type": "AUTH", "status": "OK"},
        {"seq": 3, "category": "MCP_CALL", "tool": "x", "success": True},
        {"seq": 4, "category": "AUTHORITY", "runtime_domain_id": "d", "sequence": 2, "event_id": "b", "event_type": "AUTH", "status": "OK"},
    ]
    class Client:
        def get_events(self, **kwargs):
            chosen = [e for e in events if kwargs.get("category") is None or e["category"] == kwargs["category"]]
            return {"status": "ok", "events": chosen, "latest_seq": 4, "activity_epoch": "epoch", "truncated": False}
    shown = []
    feed = DesktopLiveEventFeed(Client(), lambda message, **kwargs: shown.append(message), initial_seq=0)
    feed.replay_authority_events()
    assert feed._last_seq == 0
    feed.poll_once()
    assert feed._last_seq == 4
    assert len([x for x in shown if "Authority" in x]) == 2
    assert any("MCP" in x for x in shown) and any("Watcher updated" in x for x in shown)


def test_filtered_get_events_latest_seq_is_never_used_as_feed_cursor():
    from contextor.core.live_state.watcher import DesktopLiveEventFeed
    class Client:
        def get_events(self, **kwargs):
            return {"status": "ok", "events": [], "latest_seq": 99, "activity_epoch": "epoch", "truncated": False}
    feed = DesktopLiveEventFeed(Client(), lambda *_args, **_kwargs: None, initial_seq=7)
    feed.replay_authority_events()
    assert feed._last_seq == 7

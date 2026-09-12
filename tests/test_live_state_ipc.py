import json
import os
import subprocess
import sys
import threading
import time
import multiprocessing.connection as mpc
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.core.live_state import (
    CanonicalLiveServer,
    DesktopLiveEventFeed,
    DesktopLiveWatcher,
    LiveStateClient,
)
from contextor.core.live_state.ipc import LIVE_PROTOCOL_VERSION
from contextor.core.live_state import ipc as ipc_module
from contextor.core.live_state.runtime import EndpointSchemaError, connect_or_start, endpoint_file
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.analysis.state_manager import FileStateManager
from contextor.core.paths import repo_cache_dir
from contextor.core.domain.validation import ValidationError


def _poll_until_reconciled(watcher, expected, timeout=10.0):
    deadline = time.monotonic() + timeout
    observed = []
    while time.monotonic() < deadline:
        observed.extend(watcher.poll_once())
        if observed == expected:
            return observed
        time.sleep(0.01)
    return observed

pytestmark = pytest.mark.live


def _diagnostic_state(*, syntax=None, collisions=None, cycles=None, freshness="fresh"):
    return SimpleNamespace(
        revision=0,
        syntax_diagnostics_state=freshness,
        syntax_diagnostics_by_path={} if syntax is None else syntax,
        collisions_state=freshness,
        collisions=[] if collisions is None else collisions,
        cycles_state=freshness,
        cycles=[] if cycles is None else cycles,
    )


def _collision_error():
    error = ValidationError(
        kind="NAME_COLLISION", message="collision", nodes=["pkg.b", "pkg.a"]
    )
    error.artifact_type = "function"
    error.is_identical = False
    error.symbol_details = [
        {"module": "pkg.a", "name": "target", "artifact_type": "function", "file_path": "pkg/a.py", "location": {}},
        {"module": "pkg.b", "name": "target", "artifact_type": "function", "file_path": "pkg/b.py", "location": {}},
    ]
    return error


def test_diagnostic_delta_normalizes_fresh_canonical_families_only():
    collision = _collision_error()
    current = _diagnostic_state(
        syntax={
            "pkg/bad.py": {
                "status": "checked_with_errors",
                "errors": [
                    {"message": "invalid syntax", "line_number": 2, "column_number": 4}
                ],
            }
        },
        collisions=[collision],
        cycles=[["pkg.a", "pkg.b", "pkg.a"]],
    )
    delta = ipc_module._build_diagnostic_delta(_diagnostic_state(), current)

    assert [(item["diagnostic_kind"], item["action"]) for item in delta] == [
        ("syntax", "ADDED"),
        ("collision", "ADDED"),
        ("cycle", "ADDED"),
    ]
    assert delta[1] == {
        "action": "ADDED",
        "diagnostic_kind": "collision",
        "diagnostic_key": json.dumps(
            ["collision", "NAME_COLLISION", "function", False, "target", "pkg.a", "pkg.b"],
            separators=(",", ":"), sort_keys=True,
        ),
        "collision_kind": "NAME_COLLISION",
        "collision_artifact_type": "function",
        "collision_symbol": "target",
        "collision_is_identical": False,
        "collision_nodes": ["pkg.a", "pkg.b"],
    }
    assert delta[2]["cycle_nodes"] == ["pkg.a", "pkg.b", "pkg.a"]
    assert ipc_module._build_diagnostic_delta(
        _diagnostic_state(freshness="deferred"), current
    ) == []


def test_committed_collision_and_cycle_lifecycles_publish_exact_added_and_resolved_payloads():
    collision = _collision_error()
    cycle = ["pkg.a", "pkg.b", "pkg.a"]
    phases = [([collision], []), ([], []), ([], [cycle]), ([], [])]

    def updater(state, _path):
        state.collisions, state.cycles = phases.pop(0)
        return SimpleNamespace(status="UPDATED", file_path="pkg/change.py")

    server = CanonicalLiveServer(_diagnostic_state(), updater=updater)
    events = []
    for _ in range(4):
        server._dispatch({"operation": "update_file", "file_path": "pkg/change.py"})
        events.append(server._events[-1]["diagnostic_changes"]["items"][0])

    collision_key = json.dumps(
        ["collision", "NAME_COLLISION", "function", False, "target", "pkg.a", "pkg.b"],
        separators=(",", ":"), sort_keys=True,
    )
    assert events[0] == {
        "action": "ADDED", "diagnostic_kind": "collision", "diagnostic_key": collision_key,
        "collision_kind": "NAME_COLLISION", "collision_artifact_type": "function",
        "collision_symbol": "target", "collision_is_identical": False,
        "collision_nodes": ["pkg.a", "pkg.b"],
    }
    assert events[1] == {**events[0], "action": "RESOLVED"}
    assert events[2] == {
        "action": "ADDED", "diagnostic_kind": "cycle",
        "diagnostic_key": json.dumps(["cycle", *cycle], separators=(",", ":"), sort_keys=True),
        "cycle_nodes": cycle,
    }
    assert events[3] == {**events[2], "action": "RESOLVED"}


@pytest.mark.parametrize("family", ["syntax", "collision", "cycle"])
@pytest.mark.parametrize("previous_freshness,current_freshness", [("deferred", "fresh"), ("fresh", "stale")])
def test_diagnostic_delta_fails_closed_when_either_family_side_is_not_fresh(
    family, previous_freshness, current_freshness
):
    previous = _diagnostic_state()
    current = _diagnostic_state()
    state_name = "syntax_diagnostics_state" if family == "syntax" else f"{family}s_state"
    setattr(previous, state_name, previous_freshness)
    setattr(current, state_name, current_freshness)
    current.syntax_diagnostics_by_path = {
        "pkg/bad.py": {"status": "checked_with_errors", "errors": [{"message": "bad", "line_number": 1, "column_number": 0}]}
    }
    current.collisions = [_collision_error()]
    current.cycles = [["pkg.a", "pkg.b", "pkg.a"]]
    assert not any(
        change["diagnostic_kind"] == family
        for change in ipc_module._build_diagnostic_delta(previous, current)
    )


def test_diagnostic_delta_skips_malformed_facts_and_orders_mixed_actions_deterministically():
    malformed = _collision_error()
    malformed.symbol_details = [{"name": "left", "artifact_type": "function"}, {"name": "right", "artifact_type": "function"}]
    bad_bool = _collision_error()
    bad_bool.is_identical = 0
    inconsistent = _collision_error()
    inconsistent.symbol_details[1]["artifact_type"] = "class"
    invalid_nodes = _collision_error()
    invalid_nodes.nodes = ["pkg.a", 4]
    malformed_current = _diagnostic_state(
        collisions=[malformed, bad_bool, inconsistent, invalid_nodes],
        cycles=[["pkg.a", "pkg.b"], ["pkg.a", 2, "pkg.a"], ["only"]],
    )
    assert ipc_module._build_diagnostic_delta(_diagnostic_state(), malformed_current) == []

    previous = _diagnostic_state(
        syntax={"z.py": {"status": "checked_with_errors", "errors": [{"message": "z", "line_number": 1, "column_number": 0}]}},
        collisions=[_collision_error()], cycles=[["pkg.z", "pkg.a", "pkg.z"]],
    )
    current = _diagnostic_state(
        syntax={"a.py": {"status": "checked_with_errors", "errors": [{"message": "a", "line_number": 1, "column_number": 0}]}},
        cycles=[["pkg.a", "pkg.b", "pkg.a"]],
    )
    delta = ipc_module._build_diagnostic_delta(previous, current)
    assert [(item["diagnostic_kind"], item["action"]) for item in delta] == [
        ("syntax", "ADDED"), ("syntax", "RESOLVED"),
        ("collision", "RESOLVED"),
        ("cycle", "ADDED"), ("cycle", "RESOLVED"),
    ]
    assert [item["diagnostic_key"] for item in delta[:2]] == sorted(
        item["diagnostic_key"] for item in delta[:2]
    )


def test_diagnostic_delta_skips_real_collision_without_symbol_details():
    collision = ValidationError(
        kind="NAME_COLLISION", message="collision", nodes=["pkg.b", "pkg.a"]
    )
    collision.artifact_type = "function"
    collision.is_identical = False
    current = _diagnostic_state(collisions=[collision])

    assert not any(
        change["diagnostic_kind"] == "collision"
        for change in ipc_module._build_diagnostic_delta(_diagnostic_state(), current)
    )


def test_diagnostic_delta_orders_same_kind_and_action_by_lexical_key():
    current = _diagnostic_state(
        syntax={
            "pkg/z.py": {"status": "checked_with_errors", "errors": [{"message": "z", "line_number": 1, "column_number": 0}]},
            "pkg/a.py": {"status": "checked_with_errors", "errors": [{"message": "a", "line_number": 1, "column_number": 0}]},
        }
    )
    changes = ipc_module._build_diagnostic_delta(_diagnostic_state(), current)

    assert [(change["diagnostic_kind"], change["action"]) for change in changes] == [
        ("syntax", "ADDED"), ("syntax", "ADDED")
    ]
    assert [change["diagnostic_key"] for change in changes] == sorted(
        change["diagnostic_key"] for change in changes
    )


def test_unchanged_fresh_diagnostics_do_not_add_a_journal_field():
    state = _diagnostic_state(
        syntax={"pkg/bad.py": {"status": "checked_with_errors", "errors": [{"message": "bad", "line_number": 1, "column_number": 0}]}},
        collisions=[_collision_error()], cycles=[["pkg.a", "pkg.b", "pkg.a"]],
    )
    server = CanonicalLiveServer(
        state, updater=lambda _state, _path: SimpleNamespace(status="UPDATED", file_path="pkg/change.py")
    )
    server._dispatch({"operation": "update_file", "file_path": "pkg/change.py"})
    assert "diagnostic_changes" not in server._events[-1]


def test_update_file_publishes_only_committed_bounded_diagnostic_delta(monkeypatch):
    trace_events = []
    monkeypatch.setattr(
        ipc_module,
        "_safe_trace_event",
        lambda domain, event, **fields: trace_events.append((domain, event, fields)),
    )
    syntax_errors = {
        f"pkg/bad_{index}.py": {
            "status": "checked_with_errors",
            "errors": [
                {"message": f"bad syntax {index}", "line_number": index + 1, "column_number": 0}
            ],
        }
        for index in range(4)
    }
    phases = [syntax_errors, {}]

    def updater(state, _path):
        state.syntax_diagnostics_by_path = phases.pop(0)
        return SimpleNamespace(status="UPDATED", file_path="pkg/change.py")

    server = CanonicalLiveServer(_diagnostic_state(), updater=updater)
    added = server._dispatch(
        {
            "operation": "update_file",
            "file_path": "pkg/change.py",
            "origin": "desktop_watcher",
            "diagnostic_changes": {"total": 99, "truncated": False, "items": []},
        }
    )
    assert added["revision"] == 1
    added_event = server._events[-1]
    assert added_event["diagnostic_changes"]["total"] == 4
    assert added_event["diagnostic_changes"]["truncated"] is True
    assert len(added_event["diagnostic_changes"]["items"]) == 3

    projected = server._dispatch({"operation": "get_events", "after_revision": 0})
    projected["events"][0]["diagnostic_changes"]["items"][0]["message"] = "mutated"
    assert server._events[-1]["diagnostic_changes"]["items"][0]["message"] != "mutated"

    resolved = server._dispatch({"operation": "update_file", "file_path": "pkg/change.py"})
    assert resolved["revision"] == 2
    assert server._events[-1]["diagnostic_changes"]["total"] == 4
    assert {event for _domain, event, _fields in trace_events} >= {
        "LIVE_DIAGNOSTIC_SYNTAX_ERROR",
        "LIVE_DIAGNOSTIC_SYNTAX_RECOVERED",
    }
    assert all(
        fields["diagnostic_total"] == 4
        for _domain, event, fields in trace_events
        if event.startswith("LIVE_DIAGNOSTIC_")
    )
    assert len([event for _domain, event, _fields in trace_events if event == "LIVE_DIAGNOSTIC_SYNTAX_ERROR"]) == 4
    assert len([event for _domain, event, _fields in trace_events if event == "LIVE_DIAGNOSTIC_SYNTAX_RECOVERED"]) == 4


def test_client_request_timeout_closes_connection(monkeypatch):
    sent = []

    class Connection:
        closed = False

        def send(self, payload):
            sent.append(payload)

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(ipc_module, "Client", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(mpc, "wait", lambda _connections, timeout: [])
    client = LiveStateClient(SimpleNamespace(address=("127.0.0.1", 1), authkey=b"x"))

    with pytest.raises(TimeoutError, match="0.01s.*op=ping"):
        client.request("ping", timeout=0.01)

    assert sent == [{"operation": "ping"}]
    assert connection.closed is True


def test_client_transport_failure_emits_one_bounded_trace_event(monkeypatch):
    events = []
    endpoint = SimpleNamespace(
        address=("127.0.0.1", 1), authkey=b"x", host="127.0.0.1", port=1
    )
    monkeypatch.setattr(
        ipc_module, "Client", lambda *_args, **_kwargs: (_ for _ in ()).throw(ConnectionRefusedError(10061, "refused"))
    )
    monkeypatch.setattr(ipc_module, "_safe_trace_event", lambda *_args, **kwargs: events.append(kwargs))

    with pytest.raises(ConnectionRefusedError):
        LiveStateClient(endpoint).request("authority_status")

    assert len(events) == 1
    assert events[0]["side"] == "client"
    assert events[0]["operation_or_request_type"] == "authority_status"
    assert events[0]["exception_class"] == "ConnectionRefusedError"
    assert "authkey" not in json.dumps(events[0]).lower()


def test_server_accept_failure_emits_once_and_reraises(monkeypatch):
    events = []
    server = CanonicalLiveServer(SimpleNamespace(files=[]))

    class Listener:
        def accept(self):
            raise OSError(10061, "refused")

        def close(self):
            pass

    server._listener = Listener()
    monkeypatch.setattr(ipc_module, "_safe_trace_event", lambda *_args, **kwargs: events.append(kwargs))
    try:
        with pytest.raises(OSError):
            server.serve_forever()
    finally:
        server.close()

    assert len(events) == 1
    assert events[0]["side"] == "server"
    assert events[0]["operation_or_request_type"] == "accept"


def test_server_stopped_accept_path_emits_no_incident(monkeypatch):
    events = []
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
    monkeypatch.setattr(ipc_module, "_safe_trace_event", lambda *_args, **kwargs: events.append(kwargs))
    class Listener:
        def accept(self):
            server._stop.set()
            raise OSError(10061, "stopped")

        def close(self):
            pass
    server._listener = Listener()
    try:
        server.serve_forever()
    finally:
        server.close()

    assert events == []


@pytest.mark.parametrize("failure", [OSError("dispatch"), TimeoutError("dispatch")])
def test_server_dispatch_transport_shaped_error_is_not_ipc_failure(monkeypatch, failure):
    events, sent = [], []
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
    class Connection:
        def recv(self): return {"operation": "ping"}
        def send(self, value): sent.append(value)
        def close(self): server._stop.set()
    class Listener:
        def accept(self): return Connection()
        def close(self): pass
    server._listener = Listener()
    monkeypatch.setattr(server, "_dispatch", lambda _request: (_ for _ in ()).throw(failure))
    monkeypatch.setattr(ipc_module, "_safe_trace_event", lambda *_args, **kwargs: events.append(kwargs))
    server.serve_forever()
    assert events == []
    assert sent and sent[0]["status"] == "error"


@pytest.mark.parametrize("stage", ["recv", "send"])
def test_server_transport_boundary_emits_once(monkeypatch, stage):
    events = []
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
    class Connection:
        closed = False
        def recv(self):
            if stage == "recv": raise ConnectionResetError("recv")
            return {"operation": "ping"}
        def send(self, _value):
            if stage == "send": raise ConnectionResetError("send")
        def close(self):
            self.closed = True
            server._stop.set()
    class Listener:
        connection = Connection()
        def accept(self): return self.connection
        def close(self): pass
    listener = Listener()
    server._listener = listener
    monkeypatch.setattr(ipc_module, "_safe_trace_event", lambda *_args, **kwargs: events.append(kwargs))
    server.serve_forever()
    assert len(events) == 1 and events[0]["side"] == "server"
    assert events[0]["operation_or_request_type"] == ("recv" if stage == "recv" else "ping")
    assert listener.connection.closed is True


def test_server_trace_emitter_failure_does_not_mask_transport_failure(monkeypatch):
    import contextor.core.runtime_trace as trace
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
    class Listener:
        def accept(self):
            raise OSError(10061, "refused")
        def close(self):
            pass
    server._listener = Listener()
    monkeypatch.setattr(trace, "trace_event", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace failed")))
    with pytest.raises(OSError, match="refused"):
        server.serve_forever()


@pytest.mark.parametrize("stage", ["recv", "send"])
def test_server_recv_and_send_trace_emitter_failure_are_fail_open(monkeypatch, stage):
    import contextor.core.runtime_trace as trace

    server = CanonicalLiveServer(SimpleNamespace(files=[]))

    class Connection:
        closed = False

        def recv(self):
            if stage == "recv":
                raise ConnectionResetError("recv transport failure")
            return {"operation": "ping"}

        def send(self, _value):
            if stage == "send":
                raise ConnectionResetError("send transport failure")

        def close(self):
            self.closed = True
            server._stop.set()

    class Listener:
        connection = Connection()

        def accept(self):
            return self.connection

        def close(self):
            pass

    listener = Listener()
    server._listener = listener
    monkeypatch.setattr(
        trace,
        "trace_event",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace failed")),
    )

    server.serve_forever()
    assert listener.connection.closed is True


@pytest.fixture
def live_server():
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, LiveStateClient(server.endpoint)
    server.close()
    thread.join(timeout=2)
    assert not thread.is_alive()


def test_two_clients_observe_one_in_ram_state_and_revision(live_server):
    server, first = live_server
    second = LiveStateClient(server.endpoint)

    assert first.ping() == {
        "status": "ok", "protocol_version": LIVE_PROTOCOL_VERSION,
        "revision": 0, "available": True,
    }
    assert first.publish(SimpleNamespace(files=["a.py"]))["revision"] == 1
    snap = second.snapshot()
    assert snap["status"] == "ok"
    assert snap["revision"] == 1
    assert snap["state"].files == ["a.py"]
    assert snap["state"].revision == 1


def test_authority_status_is_independent_from_desktop_claim_status():
    authority = {
        "repo_id": "repo-id",
        "root_path": "C:/repo",
        "runtime_domain_id": "domain-id",
        "service_instance_id": "service-id",
        "lease_generation": 7,
        "service_pid": os.getpid(),
        "process_start_identity": "service-start",
    }

    def broken_claim_reader():
        raise RuntimeError("desktop claim storage unavailable")

    server = CanonicalLiveServer(
        SimpleNamespace(files=[]),
        authority_identity=authority,
        desktop_claim_reader=broken_claim_reader,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    try:
        status = client.authority_status()
        assert status["status"] == "ok"
        assert status["repo_id"] == authority["repo_id"]
        assert status["runtime_domain_id"] == authority["runtime_domain_id"]
        assert status["service_instance_id"] == authority["service_instance_id"]
        assert status["lease_generation"] == authority["lease_generation"]
        assert status["service_pid"] == authority["service_pid"]
        assert status["process_start_identity"] == authority["process_start_identity"]
        assert "desktop_claim" not in status

        claim_status = client.desktop_claim_status()
        assert claim_status["status"] == "error"
        assert "desktop claim storage unavailable" in claim_status["error"]
    finally:
        server.close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def test_publish_trace_uses_authoritative_revision_and_rejections_are_nonfatal(monkeypatch):
    import contextor.core.runtime_trace as runtime_trace

    events = []
    monkeypatch.setattr(runtime_trace, "trace_event", lambda *args, **kwargs: events.append((args, kwargs)))
    server = CanonicalLiveServer(SimpleNamespace(files=[]), revision=4)

    accepted = server._dispatch({"operation": "publish", "state": SimpleNamespace(files=["x"])})
    assert accepted["status"] == "ok"
    canonical = next(kwargs for args, kwargs in events if args[1] == "CANONICAL_PUBLISH")
    assert canonical["rev_before"] == 4
    assert canonical["rev_after"] == 5

    rejected = server._dispatch({"operation": "publish", "state": SimpleNamespace(revision=3)})
    assert rejected["error"] == "non_monotonic_canonical_revision"
    assert any(args[1] == "PUBLISH_FAIL" and kwargs["candidate_rev"] == 3 for args, kwargs in events)


def test_publish_trace_operation_and_event_failures_do_not_break_canonical_commit(monkeypatch):
    import contextor.core.runtime_trace as runtime_trace

    def fail_operation(_prefix):
        raise RuntimeError("trace operation unavailable")

    def fail_event(*_args, **_kwargs):
        raise RuntimeError("trace sink unavailable")

    monkeypatch.setattr(runtime_trace, "new_trace_operation", fail_operation)
    monkeypatch.setattr(runtime_trace, "trace_event", fail_event)
    server = CanonicalLiveServer(SimpleNamespace(files=[]))

    response = server._dispatch({"operation": "publish", "state": SimpleNamespace(files=["x"])})
    assert response["status"] == "ok"
    assert response["revision"] == 1


def test_update_trace_failure_preserves_updater_exception(monkeypatch):
    import contextor.core.runtime_trace as runtime_trace

    monkeypatch.setattr(runtime_trace, "trace_event", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")))

    def failing_updater(_state, _path):
        raise RuntimeError("updater failure")

    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=failing_updater)
    with pytest.raises(RuntimeError, match="updater failure"):
        server._dispatch({"operation": "update_file", "file_path": "x.py"})
    assert server._revision == 0


def test_trace_context_enter_failure_is_fail_open(monkeypatch):
    import contextor.core.runtime_trace as runtime_trace

    class BrokenEnter:
        def __enter__(self):
            raise RuntimeError("trace enter failure")

        def __exit__(self, *_args):
            raise RuntimeError("trace exit failure")

    monkeypatch.setattr(runtime_trace, "trace_operation", lambda _op: BrokenEnter())
    executed = []

    def updater(state, path):
        executed.append(path)
        return {"ok": True}

    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=updater)
    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
    assert executed == ["x.py"]
    assert response["status"] == "ok"
    assert response["revision"] == 1


def test_trace_context_exit_failure_after_success_is_swallowed(monkeypatch):
    import contextor.core.runtime_trace as runtime_trace

    class BrokenExit:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            raise RuntimeError("trace exit failure")

    monkeypatch.setattr(runtime_trace, "trace_operation", lambda _op: BrokenExit())
    result = {"ok": True}
    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=lambda _state, _path: result)
    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
    assert response["status"] == "ok"
    assert response["result"] is result
    assert response["revision"] == 1


def test_trace_context_exit_failure_cannot_replace_updater_exception(monkeypatch):
    import contextor.core.runtime_trace as runtime_trace

    class BrokenExit:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            raise RuntimeError("trace cleanup failure")

    monkeypatch.setattr(runtime_trace, "trace_operation", lambda _op: BrokenExit())

    def updater(_state, _path):
        raise RuntimeError("authoritative updater failure")

    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=updater)
    with pytest.raises(RuntimeError, match="^authoritative updater failure$"):
        server._dispatch({"operation": "update_file", "file_path": "x.py"})
    assert server._revision == 0


def test_update_clone_failure_uses_update_fail_not_publish_fail(monkeypatch):
    import contextor.core.runtime_trace as runtime_trace

    events = []
    monkeypatch.setattr(runtime_trace, "trace_event", lambda *args, **kwargs: events.append((args, kwargs)))

    class Uncloneable:
        def __deepcopy__(self, _memo):
            raise RuntimeError("clone failure")

    server = CanonicalLiveServer(Uncloneable(), updater=lambda *_args: {"ok": True})
    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
    assert response["error"] == "canonical_state_clone_failed"
    assert any(args[1] == "UPDATE_FAIL" for args, _kwargs in events)
    assert not any(args[1] == "PUBLISH_FAIL" for args, _kwargs in events)


def test_persister_runs_after_validation_before_canonical_exposure():
    observed = []
    initial_state = SimpleNamespace(files=[])
    server = None

    def updater(state, _path):
        state.files.append("x")
        return {"status": "UPDATED"}

    def persister(state, revision):
        assert server._state is initial_state
        assert server._revision == 0
        assert server._activity_seq == 0
        observed.append((state, revision))

    server = CanonicalLiveServer(initial_state, updater=updater, persister=persister)
    response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
    assert response["revision"] == 1
    assert observed[0][1] == 1
    assert server._state is observed[0][0]
    assert server._activity_seq == 1


def test_persistence_conflict_fails_closed_without_live_event():
    from contextor.core.live_state.store import SnapshotRevisionConflict

    events = []
    import contextor.core.runtime_trace as runtime_trace
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(runtime_trace, "trace_event", lambda *args, **kwargs: events.append((args, kwargs)))
    try:
        initial = _diagnostic_state()
        def updater(state, _path):
            state.syntax_diagnostics_by_path = {
                "pkg/bad.py": {"status": "checked_with_errors", "errors": [{"message": "bad", "line_number": 1, "column_number": 0}]}
            }
            return SimpleNamespace(status="UPDATED", file_path="pkg/bad.py")
        def persister(_state, revision):
            raise SnapshotRevisionConflict(11, revision)
        server = CanonicalLiveServer(initial, updater=updater, persister=persister)
        response = server._dispatch({"operation": "update_file", "file_path": "x.py"})
        assert response["error"] == "canonical_persistence_revision_conflict"
        assert response["resync_required"] is True
        assert server._revision == 0
        assert server._state is initial
        assert server._activity_seq == 0
        assert not any(e[0][1] == "update_file" for e in server._events)
        assert not any(args[1].startswith("LIVE_DIAGNOSTIC_") for args, _kwargs in events)
    finally:
        monkeypatch.undo()


def test_real_repository_persister_disk_ahead_fails_closed(tmp_path, monkeypatch):
    from contextor.core.live_state.runtime import _repository_persister, _repository_updater
    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
    from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import ensure_repository_identity

    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "module.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    identity = ensure_repository_identity(repo)[0]
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    cache = repo_cache_dir(repo)
    state = RepositoryAnalysisState(modules={})
    state.revision = 1
    for _ in range(11):
        save_snapshot(state, cache, "sid", repo_id=identity.repo_id, root_path=identity.root_path)
    manager = FileStateManager(str(cache))
    manager.save("sid", revision=11)
    previous = state
    previous.revision = 10
    holder = {}
    server = CanonicalLiveServer(
        previous,
        revision=10,
        updater=_repository_updater(repo, holder),
        persister=_repository_persister(repo, holder),
    )
    response = server._dispatch({"operation": "update_file", "file_path": str(source)})
    assert response["error"] == "canonical_persistence_revision_conflict"
    assert response["resync_required"] is True
    assert response["revision"] == 10
    assert response["expected_revision"] == 11
    assert response["persisted_revision"] == 11
    assert server._revision == 10 and server._state is previous and server._activity_seq == 0
    assert read_metadata(cache).revision == 11
    assert FileStateManager(str(cache)).revision == 11
    loaded_state, loaded_metadata = load_snapshot(cache, "sid")
    assert loaded_metadata.revision == 11
    assert loaded_state.revision == 11
    assert read_metadata(cache).revision != 12
    assert loaded_metadata.revision != 12
    assert not any(event["operation"] == "update_file" for event in server._events)


def test_real_repository_adapter_two_successive_updates_are_exact_successors(tmp_path, monkeypatch):
    from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
    from contextor.core.live_state.runtime import _repository_persister, _repository_updater
    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import ensure_repository_identity

    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "module.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    ensure_repository_identity(repo)
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    cache = repo_cache_dir(repo)
    state = RepositoryAnalysisState(modules={})
    state.revision = 1
    identity = ensure_repository_identity(repo)[0]
    metadata = save_snapshot(
        state,
        cache,
        "sid",
        repo_id=identity.repo_id,
        root_path=identity.root_path,
    )
    manager = FileStateManager(str(cache))
    manager.save("sid", revision=metadata.revision)
    holder = {}
    server = CanonicalLiveServer(
        state,
        revision=metadata.revision,
        updater=_repository_updater(repo, holder),
        persister=_repository_persister(repo, holder),
    )

    for expected in (2, 3):
        response = server._dispatch({"operation": "update_file", "file_path": str(source)})
        assert response["revision"] == expected
        assert server._revision == expected
        assert server._state.revision == expected
        assert read_metadata(cache).revision == expected
        loaded_state, loaded_metadata = load_snapshot(cache, "sid")
        assert loaded_metadata.revision == expected
        assert loaded_state.revision == expected
        assert FileStateManager(str(cache)).revision == expected
        assert server._events[-1]["revision"] == expected


def test_persistence_trace_operation_is_propagated_across_successful_real_update(tmp_path, monkeypatch):
    from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
    from contextor.core.live_state.runtime import _repository_persister, _repository_updater
    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import ensure_repository_identity
    import contextor.core.runtime_trace as runtime_trace

    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "module.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    ensure_repository_identity(repo)
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    cache = repo_cache_dir(repo)
    state = RepositoryAnalysisState(modules={})
    state.revision = 1
    metadata = save_snapshot(state, cache, "sid")
    FileStateManager(str(cache)).save("sid", revision=metadata.revision)
    holder = {}
    captured = []
    monkeypatch.setattr(runtime_trace, "trace_event", lambda domain, event, **fields: captured.append((event, fields)))
    server = CanonicalLiveServer(
        state,
        revision=metadata.revision,
        updater=_repository_updater(repo, holder),
        persister=_repository_persister(repo, holder),
    )
    response = server._dispatch({"operation": "update_file", "file_path": str(source), "trace_op": "trace-real-1"})
    assert response["status"] == "ok"
    required = {
        "UPDATE_RECEIVED",
        "UPDATER_START",
        "UPDATER_END",
        "PERSIST_START",
        "SNAPSHOT_SAVE_END",
        "FILE_STATE_SAVE_END",
        "PERSIST_END",
        "CANONICAL_COMMIT",
        "UPDATE_PUBLISHED",
    }
    events = {event: fields for event, fields in captured}
    assert required <= events.keys()
    assert {events[event].get("op") for event in required} == {"trace-real-1"}
    monkeypatch.setattr(
        runtime_trace,
        "trace_event",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
    )
    monkeypatch.setattr(
        runtime_trace,
        "current_trace_operation",
        lambda: (_ for _ in ()).throw(RuntimeError("trace context unavailable")),
    )
    expected = server._revision + 1
    second = server._dispatch({"operation": "update_file", "file_path": str(source)})
    assert second["status"] == "ok"
    assert second["revision"] == expected
    assert server._revision == expected
    assert server._state.revision == expected
    persisted = read_metadata(cache)
    assert persisted.revision == expected
    loaded_state, loaded_metadata = load_snapshot(cache, "sid")
    assert loaded_metadata.revision == expected
    assert loaded_state.revision == expected
    assert FileStateManager(str(cache)).revision == expected


def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_path, monkeypatch):
    import contextor.core.live_state.runtime as runtime
    from contextor.core.analysis.state_manager import FileState, FileStateManager, RepositoryAnalysisState
    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import ensure_repository_identity

    repo = tmp_path / "repo"
    repo.mkdir()
    ensure_repository_identity(repo)
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    cache = repo_cache_dir(repo)
    state = RepositoryAnalysisState(modules={"a.py": SimpleNamespace()})
    state.revision = 1
    identity = ensure_repository_identity(repo)[0]
    metadata = save_snapshot(
        state,
        cache,
        "sid",
        repo_id=identity.repo_id,
        root_path=identity.root_path,
    )
    manager = FileStateManager(str(cache))
    manager._state = {
        "a.py": FileState(10, 3, "aaa"),
        "b.py": FileState(20, 4, "bbb"),
    }
    manager.save("sid", revision=metadata.revision)
    before = dict(manager._state)

    class StubServer:
        def __init__(self, state, revision, **_kwargs):
            self._state = state
            self._revision = revision
            self.endpoint = SimpleNamespace(host="127.0.0.1", port=1, authkey_hex="00")
            self._stop = threading.Event()
            self.activity_epoch = "startup-backfill-test"

        def serve_forever(self):
            if not self._stop.wait(timeout=5.0):
                raise RuntimeError("StubServer did not receive post-READY shutdown")

        def record_authority_event(self, event):
            if event.get("event_type") == "RUNTIME_AUTHORITY_READY":
                self._stop.set()
            return {
                "accepted": True,
                "duplicate": False,
                "activity_epoch": self.activity_epoch,
            }

        def close(self, **_kwargs):
            self._stop.set()
            return True

    monkeypatch.setattr(runtime, "CanonicalLiveServer", StubServer)
    import contextor.core.runtime_trace as runtime_trace
    monkeypatch.setattr(
        runtime_trace,
        "trace_event",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace sink unavailable")),
    )
    import contextor.core.analysis.incremental.materialization as materialization
    monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
    monkeypatch.setattr(materialization, "ensure_module_usages", lambda value: setattr(value, "module_usages", {"a.py": SimpleNamespace(symbol_calls_materialized=True, reference_evidence_materialized=True)}))
    runtime.run_service(repo)

    after = FileStateManager(str(cache))
    loaded_state, loaded_metadata = load_snapshot(cache, "sid")
    assert len(after._state) == len(before)
    assert after._state == before
    assert after.revision == metadata.revision + 1
    assert read_metadata(cache).revision == metadata.revision + 1
    assert loaded_metadata.revision == metadata.revision + 1
    assert loaded_state.revision == metadata.revision + 1


def test_startup_backfill_failure_leaves_previous_generation_authoritative(tmp_path, monkeypatch):
    import contextor.core.live_state.runtime as runtime
    from contextor.core.analysis.state_manager import FileState, FileStateManager, RepositoryAnalysisState
    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import ensure_repository_identity

    repo = tmp_path / "repo"
    repo.mkdir()
    identity = ensure_repository_identity(repo)[0]
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    cache = repo_cache_dir(repo)
    state = RepositoryAnalysisState(modules={"a.py": SimpleNamespace()})
    state.revision = 1
    metadata = save_snapshot(state, cache, "sid", repo_id=identity.repo_id, root_path=identity.root_path)
    manager = FileStateManager(str(cache))
    manager._state = {"a.py": FileState(10, 3, "aaa"), "b.py": FileState(20, 4, "bbb")}
    manager.save("sid", revision=metadata.revision)
    before = dict(manager._state)
    monkeypatch.setattr(runtime, "CanonicalLiveServer", lambda *_args, **_kwargs: None)
    import contextor.core.analysis.incremental.materialization as materialization
    monkeypatch.setattr(materialization, "module_usages_require_materialization", lambda _state: True)
    monkeypatch.setattr(materialization, "ensure_module_usages", lambda _state: None)
    import contextor.core.live_state.store as store
    original_replace = store.os.replace
    def fail_only_authoritative_metadata_commit(source, target):
        if Path(target).name == "engine_state.meta.json":
            raise RuntimeError("synthetic metadata commit failure")
        return original_replace(source, target)
    monkeypatch.setattr(store.os, "replace", fail_only_authoritative_metadata_commit)
    with pytest.raises(RuntimeError, match="synthetic metadata commit failure"):
        runtime.run_service(repo)
    assert read_metadata(cache).revision == metadata.revision
    assert load_snapshot(cache, "sid")[1].revision == metadata.revision
    reloaded = FileStateManager(str(cache))
    assert reloaded.revision == metadata.revision
    assert reloaded._state == before


def _runtime_service_repo(tmp_path, monkeypatch):
    from contextor.core.repository_identity import ensure_repository_identity

    repo = tmp_path / "repo"
    repo.mkdir()
    ensure_repository_identity(repo)
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
    return repo


def _authority_event_types(logs_root):
    records = []
    for path in logs_root.glob("contextor_runtime_*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            payload = json.loads(line)
            if payload.get("_type") == "authority_event":
                records.append(payload["event_type"])
    return records


def test_run_service_rejects_stop_and_return_before_ready(tmp_path, monkeypatch):
    import contextor.core.live_state.runtime as runtime
    from contextor.core.paths import runtime_logs_dir

    repo = _runtime_service_repo(tmp_path, monkeypatch)

    class PrematureStoppingServer(CanonicalLiveServer):
        def serve_forever(self):
            self._stop.set()
            return None

    monkeypatch.setattr(runtime, "CanonicalLiveServer", PrematureStoppingServer)

    with pytest.raises(
        RuntimeError,
        match="service thread terminated unexpectedly during pre-endpoint bootstrap",
    ):
        runtime.run_service(repo)

    assert not endpoint_file(repo).exists()
    assert "RUNTIME_AUTHORITY_READY" not in _authority_event_types(runtime_logs_dir())


def test_run_service_fails_closed_when_service_thread_raises_before_endpoint(tmp_path, monkeypatch):
    import contextor.core.live_state.runtime as runtime
    from contextor.core.paths import runtime_logs_dir

    repo = _runtime_service_repo(tmp_path, monkeypatch)
    events = []

    class FailingServer(CanonicalLiveServer):
        def serve_forever(self):
            raise RuntimeError("synthetic service-thread startup failure")

    monkeypatch.setattr(runtime, "CanonicalLiveServer", FailingServer)
    monkeypatch.setattr(
        runtime, "_safe_trace_event",
        lambda domain, event, **fields: events.append((domain, event, fields)),
    )

    with pytest.raises(RuntimeError, match="service thread failed during (pre-endpoint bootstrap|endpoint publication)"):
        runtime.run_service(repo)

    assert not endpoint_file(repo).exists()
    assert "RUNTIME_AUTHORITY_READY" not in _authority_event_types(runtime_logs_dir())
    assert [(domain, event) for domain, event, _fields in events] == [
        ("LIVE", "LIVE_SERVICE_THREAD_FAILURE")
    ]
    assert events[0][2]["exception_class"] == "RuntimeError"


def test_run_service_trace_emitter_failure_does_not_mask_service_failure(tmp_path, monkeypatch):
    import contextor.core.live_state.runtime as runtime

    repo = _runtime_service_repo(tmp_path, monkeypatch)

    class FailingServer(CanonicalLiveServer):
        def serve_forever(self):
            raise RuntimeError("synthetic service-thread startup failure")

    monkeypatch.setattr(runtime, "CanonicalLiveServer", FailingServer)
    monkeypatch.setattr(
        runtime,
        "_safe_trace_event",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("trace failed")),
    )

    with pytest.raises(RuntimeError, match="service thread failed during (pre-endpoint bootstrap|endpoint publication)"):
        runtime.run_service(repo)
    assert not endpoint_file(repo).exists()


def test_run_service_fingerprint_diagnostic_failure_does_not_mask_service_failure(tmp_path, monkeypatch):
    import contextor.core.live_state.runtime as runtime

    repo = _runtime_service_repo(tmp_path, monkeypatch)
    release_failure = threading.Event()
    original_endpoint = runtime._authority_endpoint_from_server

    class FailingServer(CanonicalLiveServer):
        def serve_forever(self):
            release_failure.wait(timeout=5.0)
            raise RuntimeError("synthetic service-thread fingerprint failure")

    def endpoint_then_poison_fingerprint(server, *args, **kwargs):
        endpoint = original_endpoint(server, *args, **kwargs)
        server.endpoint = SimpleNamespace(
            fingerprint=lambda: (_ for _ in ()).throw(RuntimeError("fingerprint failed"))
        )
        release_failure.set()
        return endpoint

    monkeypatch.setattr(runtime, "CanonicalLiveServer", FailingServer)
    monkeypatch.setattr(runtime, "_authority_endpoint_from_server", endpoint_then_poison_fingerprint)

    with pytest.raises(RuntimeError, match="service thread failed during endpoint publication") as raised:
        runtime.run_service(repo)

    assert isinstance(raised.value.__cause__, RuntimeError)
    assert str(raised.value.__cause__) == "synthetic service-thread fingerprint failure"
    assert not endpoint_file(repo).exists()


def test_run_service_fails_closed_when_service_thread_dies_before_ready(tmp_path, monkeypatch):
    import contextor.core.live_state.runtime as runtime
    from contextor.core.paths import runtime_logs_dir

    repo = _runtime_service_repo(tmp_path, monkeypatch)
    release_failure = threading.Event()
    failure_observed = threading.Event()
    original_endpoint = runtime._authority_endpoint_from_server

    class FailingServer(CanonicalLiveServer):
        def serve_forever(self):
            release_failure.wait(timeout=5.0)
            try:
                raise RuntimeError("synthetic service-thread pre-ready failure")
            finally:
                failure_observed.set()

    def endpoint_then_release(*args, **kwargs):
        endpoint = original_endpoint(*args, **kwargs)
        release_failure.set()
        assert failure_observed.wait(timeout=2.0)
        return endpoint

    monkeypatch.setattr(runtime, "CanonicalLiveServer", FailingServer)
    monkeypatch.setattr(runtime, "_authority_endpoint_from_server", endpoint_then_release)

    with pytest.raises(RuntimeError, match="service thread failed during endpoint publication"):
        runtime.run_service(repo)

    assert not endpoint_file(repo).exists()
    assert "RUNTIME_AUTHORITY_READY" not in _authority_event_types(runtime_logs_dir())


def test_normal_service_shutdown_preserves_authority_event_chronology(tmp_path, monkeypatch):
    import contextor.core.live_state.runtime as runtime
    from contextor.core.paths import runtime_logs_dir

    repo = _runtime_service_repo(tmp_path, monkeypatch)
    failures = []

    def run():
        try:
            runtime.run_service(repo)
        except BaseException as exc:
            failures.append(exc)

    service = threading.Thread(target=run, daemon=True)
    service.start()
    deadline = time.monotonic() + 5.0
    client = None
    while time.monotonic() < deadline:
        client = runtime.connect(repo)
        if client is not None:
            break
        time.sleep(0.02)
    assert client is not None
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and "RUNTIME_AUTHORITY_READY" not in _authority_event_types(runtime_logs_dir()):
        time.sleep(0.02)
    assert "RUNTIME_AUTHORITY_READY" in _authority_event_types(runtime_logs_dir())
    assert client.request("shutdown").get("status") == "ok"
    service.join(timeout=5.0)

    assert not service.is_alive()
    assert failures == []
    assert not endpoint_file(repo).exists()
    event_types = _authority_event_types(runtime_logs_dir())
    assert event_types.index("RUNTIME_AUTHORITY_START") < event_types.index("RUNTIME_AUTHORITY_READY")


def test_endpoint_before_authority_replay_exposes_valid_pending_live_feed(tmp_path, monkeypatch):
    import contextor.core.live_state.runtime as runtime
    import contextor.core.runtime_trace as runtime_trace
    from contextor import mcp_server
    from contextor.core.paths import runtime_logs_dir

    repo = _runtime_service_repo(tmp_path, monkeypatch)
    replay_entered = threading.Event()
    release_replay = threading.Event()
    failures = []
    original_replay = runtime_trace.AuthorityEventEmitter.replay_pending

    def gated_replay(self):
        replay_entered.set()
        assert release_replay.wait(timeout=5.0)
        return original_replay(self)

    def run():
        try:
            runtime.run_service(repo)
        except BaseException as exc:
            failures.append(exc)

    monkeypatch.setattr(runtime_trace.AuthorityEventEmitter, "replay_pending", gated_replay)
    service = threading.Thread(target=run, daemon=True)
    service.start()
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and not (endpoint_file(repo).exists() and replay_entered.is_set()):
        time.sleep(0.02)
    assert endpoint_file(repo).exists()
    assert replay_entered.is_set()

    pending = json.loads(mcp_server.get_live_events.fn(str(repo)))
    assert pending["status"] == "ok"
    assert pending.get("continuity") in {None, "not_requested", "continuous"}

    release_replay.set()
    deadline = time.monotonic() + 5.0
    completed = None
    while time.monotonic() < deadline:
        completed = json.loads(mcp_server.get_live_events.fn(str(repo)))
        authority_events = [event for event in completed.get("events", []) if event.get("category") == "AUTHORITY"]
        if authority_events:
            break
        time.sleep(0.02)
    assert completed is not None
    authority_events = [event for event in completed["events"] if event.get("category") == "AUTHORITY"]
    keys = [(event["runtime_domain_id"], event["sequence"], event["event_id"]) for event in authority_events]
    assert authority_events
    assert len(keys) == len(set(keys))

    client = runtime.connect(repo)
    assert client is not None
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and "RUNTIME_AUTHORITY_READY" not in _authority_event_types(runtime_logs_dir()):
        completed = json.loads(mcp_server.get_live_events.fn(str(repo)))
        time.sleep(0.02)
    assert "RUNTIME_AUTHORITY_READY" in _authority_event_types(runtime_logs_dir())
    assert client.request("shutdown").get("status") == "ok"
    service.join(timeout=5.0)
    assert not service.is_alive()
    assert failures == []


def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
    def update(state, file_path):
        state.files.append(file_path)
        return {"updated": file_path}

    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=update)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        writer = LiveStateClient(server.endpoint)
        reader = LiveStateClient(server.endpoint)
        response = writer.update_file("new.py")

        assert response["status"] == "ok"
        assert response["revision"] == 1
        assert reader.snapshot()["state"].files == ["new.py"]
    finally:
        server.close()
        thread.join(timeout=2)


def test_live_events_preserve_desktop_origin_and_syntax_diagnostic(live_server):
    server, client = live_server

    result = SimpleNamespace(
        status="SYNTAX_ERROR",
        file_path="broken.py",
        error="invalid syntax",
        line_number=2,
        column_number=9,
    )
    server._updater = lambda _state, _path: result
    response = client.update_file("broken.py", origin="desktop_watcher")
    events = client.get_events(after_revision=0, limit=20)

    assert response["revision"] == 1
    assert events["total"] == 1
    assert events["truncated"] is False
    assert events["events"] == [{
        "revision": 1,
        "operation": "update_file",
        "origin": "desktop_watcher",
        "status": "SYNTAX_ERROR",
        "file_path": "broken.py",
        "error": "invalid syntax",
        "line_number": 2,
        "column_number": 9,
    }]


def test_live_events_record_blast_radius_state_and_bounded_affected_modules(live_server):
    server, client = live_server

    modules = [f"mod_{i}" for i in range(25)]
    result = SimpleNamespace(
        status="UPDATED",
        file_path="provider.py",
        blast_radius_state="fresh",
        affected_modules=modules,
    )
    server._updater = lambda _state, _path: result
    response = client.update_file("provider.py", origin="desktop_watcher")
    events = client.get_events(after_revision=0, limit=20)

    assert response["revision"] == 1
    assert events["total"] == 1
    assert events["events"][0]["blast_radius_state"] == "fresh"
    assert events["events"][0]["affected_modules"] == {
        "total": 25,
        "truncated": True,
        "items": modules[:20],
    }



def test_desktop_event_feed_forwards_only_mcp_status_messages(live_server):
    _server, client = live_server
    statuses = []
    feed = DesktopLiveEventFeed(client, statuses.append)

    client.status("MCP: reading symbol demo", origin="mcp")
    client.status("desktop-only", origin="desktop_watcher")
    client.publish({"ready": True}, origin="mcp_analysis")
    feed.poll_once()

    assert statuses == [
        "MCP: reading symbol demo",
        "MCP: analysis published shared LIVE state (rev 1)",
    ]


def test_desktop_event_feed_background_worker_starts_and_stops(live_server):
    _server, client = live_server
    delivered = threading.Event()
    statuses = []

    def receive(message):
        statuses.append(message)
        delivered.set()

    feed = DesktopLiveEventFeed(client, receive, interval=0.01)
    try:
        feed.start()
        client.status("MCP: background status", origin="mcp")
        assert delivered.wait(timeout=1)
        assert statuses == ["MCP: background status"]
    finally:
        feed.stop()
    assert feed._thread is not None
    assert not feed._thread.is_alive()


def test_invalid_and_unavailable_operations_return_structured_errors():
    server = CanonicalLiveServer()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = LiveStateClient(server.endpoint)
        assert client.request("unknown")["error"] == "unknown_operation"
        assert client.update_file("x.py")["error"] == "live_state_unavailable"
    finally:
        server.close()
        thread.join(timeout=2)


def test_updater_failure_does_not_kill_the_service():
    def broken_update(_state, _file_path):
        raise ValueError("broken update")

    server = CanonicalLiveServer(SimpleNamespace(), updater=broken_update)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = LiveStateClient(server.endpoint)
        assert "broken update" in client.update_file("x.py")["error"]
        assert client.ping()["status"] == "ok"
        assert thread.is_alive()
    finally:
        server.close()
        thread.join(timeout=2)


def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tmp_path):
    updates = []
    statuses = []
    identity = PersistentIdentityRegistry(str(tmp_path))
    manager = FileStateManager(str(repo_cache_dir(tmp_path)))
    manager.save(identity.repo_id, revision=0)

    def update(state, file_path):
        updates.append(file_path)
        state.updates += 1
        manager.update_state(file_path)
        manager.save(identity.repo_id, revision=state.revision + 1)
        return SimpleNamespace(status="UPDATED", file_path=file_path)

    server_state = SimpleNamespace(updates=0, revision=0, state_id=identity.repo_id, modules={})
    server = CanonicalLiveServer(server_state, revision=0, updater=update)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    watcher = DesktopLiveWatcher(
        tmp_path, LiveStateClient(server.endpoint), on_status=statuses.append
    )
    target = tmp_path / "sample.py"
    try:
        target.write_text("value = 1\n", encoding="utf-8")
        watcher._enqueue_path(str(target))
        assert _poll_until_reconciled(watcher, [str(target)]) == [str(target)]

        target.write_text("value = 22\n", encoding="utf-8")
        watcher._enqueue_path(str(target))
        assert _poll_until_reconciled(watcher, [str(target)]) == [str(target)]

        target.unlink()
        watcher._enqueue_path(str(target))
        assert _poll_until_reconciled(watcher, [str(target)]) == [str(target)]
        snapshot = LiveStateClient(server.endpoint).snapshot()
        assert snapshot["revision"] == 3
        assert snapshot["state"].updates == 3
        assert updates == [str(target)] * 3
        assert statuses == [
            "Updating LIVE: sample.py", "LIVE update successful: sample.py",
            "Updating LIVE: sample.py", "LIVE update successful: sample.py",
            "Updating LIVE: sample.py", "LIVE update successful: sample.py",
        ]
    finally:
        server.close()
        thread.join(timeout=2)


def test_first_run_watcher_waits_for_initial_canonical_state(tmp_path):
    identity = PersistentIdentityRegistry(str(tmp_path))
    manager = FileStateManager(str(repo_cache_dir(tmp_path)))
    manager.save(identity.repo_id, revision=0)
    def update(state, path):
        state.last_path = path
        return SimpleNamespace(status="UPDATED", file_path=path)

    server = CanonicalLiveServer(None, revision=0, updater=update)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    statuses = []
    watcher = DesktopLiveWatcher(tmp_path, client, on_status=statuses.append)
    try:
        before_analysis = tmp_path / "before_analysis.py"
        before_analysis.write_text("value = 1\n", encoding="utf-8")
        watcher._enqueue_path(str(before_analysis))
        assert watcher.poll_once() == []
        assert client.ping() == {
            "status": "ok", "protocol_version": LIVE_PROTOCOL_VERSION,
            "revision": 0, "available": False,
        }
        assert statuses == ["LIVE: no snapshot; waiting for analysis"]

        manager.update_state(str(before_analysis))
        client.publish(SimpleNamespace(
            ready=True,
            revision=1,
            state_id=identity.repo_id,
            modules={"before_analysis": object()},
        ))
        manager.save(identity.repo_id, revision=1)
        after_analysis = tmp_path / "after_analysis.py"
        after_analysis.write_text("value = 2\n", encoding="utf-8")
        watcher._enqueue_path(str(after_analysis))
        response = _poll_until_reconciled(watcher, [str(before_analysis), str(after_analysis)])
        assert response == [str(before_analysis), str(after_analysis)]
    finally:
        server.close()
        thread.join(timeout=2)


def test_desktop_watcher_reports_syntax_location(tmp_path):
    identity = PersistentIdentityRegistry(str(tmp_path))
    manager = FileStateManager(str(repo_cache_dir(tmp_path)))
    manager.save(identity.repo_id, revision=0)
    statuses = []
    result = SimpleNamespace(
        status="SYNTAX_ERROR",
        file_path=str(tmp_path / "broken.py"),
        error="invalid syntax",
        line_number=2,
        column_number=7,
    )
    server = CanonicalLiveServer(SimpleNamespace(ready=True, revision=0, state_id=identity.repo_id, modules={}), revision=0, updater=lambda *_args: result)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    watcher = DesktopLiveWatcher(
        tmp_path, LiveStateClient(server.endpoint), on_status=statuses.append
    )
    try:
        target = tmp_path / "broken.py"
        target.write_text("def broken(:\n", encoding="utf-8")
        watcher._enqueue_path(str(target))
        assert watcher.poll_once() == [str(target)]
        assert statuses == [
            "Updating LIVE: broken.py",
            "LIVE syntax error: broken.py line 2, column 7: invalid syntax",
        ]
    finally:
        server.close()
        thread.join(timeout=2)


def test_real_service_process_starts_connects_and_stops(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    client = connect_or_start(repo)
    endpoint = endpoint_file(repo)
    try:
        assert client.ping()["status"] == "ok"
        assert endpoint.is_file()
    finally:
        client.request("shutdown")


def test_real_process_busy_update_does_not_spawn_second_live_owner(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
    client = connect_or_start(repo, owner_pid=os.getpid(), owner_token="busy-test")
    try:
        endpoint = endpoint_file(repo)
        payload = __import__("json").loads(endpoint.read_text(encoding="utf-8"))
        pid_a = int(payload["pid"])
        assert pid_a != os.getpid()
        assert client.service_pid == pid_a
        assert endpoint.exists()
        assert client.ping()["status"] == "ok"
    finally:
        client.request("shutdown")
        deadline = time.monotonic() + 5
        while endpoint.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not endpoint.exists()


def test_test_live_runtime_isolation_preserves_existing_live_service(
    tmp_path, monkeypatch
):
    """Independent real LIVE namespaces cannot replace or tear down each other."""

    cache = tmp_path / "cache"
    repo_a = tmp_path / "repo_a"
    repo_b = tmp_path / "repo_b"
    repo_a.mkdir()
    repo_b.mkdir()
    PersistentIdentityRegistry(str(repo_a))
    PersistentIdentityRegistry(str(repo_b))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    client_a = connect_or_start(
        repo_a, owner_pid=os.getpid(), owner_token="isolation-a"
    )
    endpoint_a = endpoint_file(repo_a)
    pid_a = client_a.service_pid
    epoch_a = client_a.get_events().get("activity_epoch")
    try:
        assert epoch_a
        assert client_a.ping()["status"] == "ok"
        assert endpoint_a.is_file()

        client_b = connect_or_start(
            repo_b, owner_pid=os.getpid(), owner_token="isolation-b"
        )
        endpoint_b = endpoint_file(repo_b)
        try:
            assert client_b.ping()["status"] == "ok"
            assert endpoint_b.is_file()
            assert endpoint_b != endpoint_a
            assert endpoint_b.parent != endpoint_a.parent
            assert client_b.service_pid != pid_a
        finally:
            client_b.request("shutdown")
            deadline = time.monotonic() + 5.0
            while endpoint_b.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            assert not endpoint_b.exists()

        assert endpoint_a.is_file()
        assert client_a.ping()["status"] == "ok"
        assert client_a.get_events().get("activity_epoch") == epoch_a
    finally:
        client_a.request("shutdown")
        deadline = time.monotonic() + 5.0
        while endpoint_a.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not endpoint_a.exists()


def test_connect_or_start_ownership_when_spawning_new(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    import os
    my_pid = os.getpid()
    client = connect_or_start(repo, owner_pid=my_pid, owner_token="new-owner-token")
    try:
        assert client.is_owner is False
        assert client.owner_token == "new-owner-token"
        assert client.owner_pid == my_pid
        assert client.service_pid is not None
        assert client.service_pid > 0
    finally:
        client.request("shutdown")


def test_owner_pid_match_without_owner_token_is_not_owner(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    # Calling connect_or_start without owner_token must NEVER grant is_owner=True
    client = connect_or_start(repo, owner_pid=os.getpid(), owner_token=None)
    try:
        assert client.is_owner is False
        assert client.owner_token is None
    finally:
        client.request("shutdown")


def test_legacy_token_only_endpoint_is_rejected_fail_closed(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    import json
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": 54321,
        "owner_token": "token-xyz",
        # Note: owner_pid is None
    }
    ep_file.write_text(json.dumps(payload), encoding="utf-8")

    try:
        with pytest.raises(EndpointSchemaError):
            connect_or_start(repo, owner_token="token-xyz")
    finally:
        server.close()
        thread.join(timeout=2)


def test_legacy_endpoint_is_rejected_before_post_spawn_attach(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    import json
    # Start a genuine server with PID 54321 and token "race-token"
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": 54321,
        "owner_token": "race-token",
    }
    ep_file.write_text(json.dumps(payload), encoding="utf-8")

    try:
        with pytest.raises(EndpointSchemaError):
            connect_or_start(repo, owner_token="race-token")
    finally:
        server.close()
        thread.join(timeout=2)


def test_connect_or_start_ownership_when_reconnecting_existing(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    first_client = connect_or_start(repo, owner_pid=os.getpid(), owner_token="first-token")
    try:
        # Second caller with a different owner_token connects to existing service
        second_client = connect_or_start(repo, owner_pid=99999999, owner_token="second-token")
        assert second_client.is_owner is False
        assert second_client.owner_token == "first-token"
        assert second_client.service_pid == first_client.service_pid
    finally:
        first_client.request("shutdown")


def test_connect_or_start_replaces_proven_orphan_with_dead_owner(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    # Spawn a service with owner_pid = 99999999 (which is dead)
    import subprocess
    import sys
    env = dict(os.environ)
    proc = subprocess.Popen(
        [sys.executable, "-m", "contextor.core.live_state.runtime", "--repo", str(repo), "--owner-pid", "99999999"],
        cwd=str(repo),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    from contextor.core.live_state.runtime import connect
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if connect(repo):
            break
        time.sleep(0.05)
    orphan_pid = proc.pid
    try:
        # connect_or_start detects owner 99999999 is dead -> stops orphan and spawns fresh owned runtime
        client = connect_or_start(repo, owner_pid=os.getpid(), owner_token="orphan-replacer")
        assert client.is_owner is False
        assert client.owner_token == "orphan-replacer"
        assert client.owner_pid == os.getpid()
        assert client.service_pid != orphan_pid
    finally:
        client.request("shutdown")
        try:
            proc.kill()
        except OSError:
            pass


def test_connect_or_start_rejects_legacy_endpoint_without_owner_pid(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    import json
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    legacy_payload = {
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": 54321,
        # Note: no owner_pid, no owner_token
    }
    ep_file.write_text(json.dumps(legacy_payload), encoding="utf-8")

    try:
        with pytest.raises(EndpointSchemaError):
            connect_or_start(repo, owner_pid=12345, owner_token="caller-token")
    finally:
        server.close()
        thread.join(timeout=2)


def test_terminate_pid_tree_kills_process_and_children(tmp_path):
    """Explicit process tree termination test proving _terminate_pid_tree behavior."""
    import subprocess
    import sys
    from contextor.core.live_state.runtime import _is_pid_alive, _terminate_pid_tree

    # Spawn a sleeping python process
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pid = proc.pid
    try:
        assert _is_pid_alive(pid) is True
        _terminate_pid_tree(pid)
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if not _is_pid_alive(pid):
                break
            time.sleep(0.05)
        assert _is_pid_alive(pid) is False
    finally:
        try:
            proc.kill()
        except OSError:
            pass


def test_endpoint_cleanup_does_not_delete_newer_pid_endpoint(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    client = connect_or_start(repo)
    ep_file = endpoint_file(repo)
    assert ep_file.is_file()

    # Simulate a newer service replacing the endpoint file with a new PID
    import json
    payload = json.loads(ep_file.read_text(encoding="utf-8"))
    payload["pid"] = 99999998
    ep_file.write_text(json.dumps(payload), encoding="utf-8")

    try:
        # Request shutdown of original client - its finally block must NOT unlink the newer endpoint!
        client.request("shutdown")
        time.sleep(0.3)
        assert ep_file.is_file()
    finally:
        try:
            ep_file.unlink()
        except OSError:
            pass


def test_owner_token_is_metadata_only_for_protocol_clients(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    token_a = "token-alpha-12345"
    token_b = "token-beta-67890"

    client_a = connect_or_start(repo, owner_pid=os.getpid(), owner_token=token_a)
    try:
        assert client_a.is_owner is False
        assert client_a.owner_token == token_a
        assert client_a.owner_pid == os.getpid()

        # Caller B connects with different token -> is_owner must be False
        client_b = connect_or_start(repo, owner_pid=os.getpid(), owner_token=token_b)
        assert client_b.is_owner is False
        assert client_b.owner_token == token_a
        assert client_b.service_pid == client_a.service_pid

        # Caller A reconnects with same token A -> protocol clients remain non-owners
        client_a_reconnected = connect_or_start(repo, owner_pid=os.getpid(), owner_token=token_a)
        assert client_a_reconnected.is_owner is False
        assert client_a_reconnected.owner_token == token_a
        assert client_a_reconnected.service_pid == client_a.service_pid
    finally:
        client_a.request("shutdown")


def test_owner_pid_reuse_or_mismatched_token_does_not_grant_ownership(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    token_original = "token-original-owner"
    token_recycled = "token-recycled-owner"

    client = connect_or_start(repo, owner_pid=os.getpid(), owner_token=token_original)
    try:
        # Simulate another process that coincidentally shares the same PID (or PID reuse)
        # but has a different owner_token
        recycled_client = connect_or_start(repo, owner_pid=os.getpid(), owner_token=token_recycled)
        assert recycled_client.is_owner is False
        assert recycled_client.owner_token == token_original
    finally:
        client.request("shutdown")


def test_concurrent_connect_or_start_creates_single_service(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    results = []
    barrier = threading.Barrier(3)

    def worker(idx):
        barrier.wait()
        token = f"worker-token-{idx}"
        client = connect_or_start(repo, owner_pid=os.getpid(), owner_token=token)
        results.append((token, client))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15.0)

    assert len(results) == 3
    # Exactly one client should be the owner, and all 3 must share the same service_pid
    service_pids = {client.service_pid for _, client in results}
    assert len(service_pids) == 1
    assert all(not client.is_owner for _, client in results)

    # Cleanup the service using any protocol client.
    results[0][1].request("shutdown")


def test_watchdog_terminates_runtime_when_owner_process_dies(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    from contextor.core.live_state.runtime import _is_pid_alive, connect

    # Spawn a short-lived parent process that starts the live runtime with its own PID
    script = (
        "import sys, os, time, subprocess; "
        f"repo = {repr(str(repo))}; "
        f"cache = {repr(str(cache))}; "
        "os.environ['CONTEXTOR_CACHE_DIR'] = cache; "
        "cmd = [sys.executable, '-m', 'contextor.core.live_state.runtime', '--repo', repo, '--owner-pid', str(os.getpid())]; "
        "proc = subprocess.Popen(cmd, cwd=repo, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
        "time.sleep(1.0); "
        "sys.exit(0)"
    )
    parent = subprocess.Popen([sys.executable, "-c", script])
    parent.wait(timeout=5)
    assert not _is_pid_alive(parent.pid)

    # Watchdog inside runtime.py should detect owner parent is dead and terminate itself within bounded time
    deadline = time.monotonic() + 5.0
    terminated = False
    while time.monotonic() < deadline:
        if connect(repo) is None:
            terminated = True
            break
        time.sleep(0.1)

    assert terminated is True


def test_watchdog_keeps_runtime_alive_while_owner_lives(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    # Spawn with our own current PID which stays alive
    client = connect_or_start(repo, owner_pid=os.getpid(), owner_token="test-alive")
    try:
        time.sleep(1.5)  # Longer than the 0.75s watchdog interval
        status = client.ping()
        assert status.get("status") == "ok"
    finally:
        client.request("shutdown")


def test_get_events_continuity_gap_detection_and_retention_contract():
    server = CanonicalLiveServer(state=None, revision=0, retention=100)

    # Case 1: Initial empty buffer
    r_empty_none = server._dispatch({"operation": "get_events", "after_revision": None})
    assert r_empty_none["status"] == "ok"
    assert r_empty_none["latest_revision"] == 0
    assert r_empty_none["earliest_retained_revision"] is None
    assert r_empty_none["continuity"] == "not_requested"
    assert r_empty_none["resync_required"] is False
    assert r_empty_none["resync_reason"] is None
    assert r_empty_none["events"] == []
    assert r_empty_none["total"] == 0
    assert r_empty_none["truncated"] is False

    # Empty buffer with after_revision == 0 (latest)
    r_empty_zero = server._dispatch({"operation": "get_events", "after_revision": 0})
    assert r_empty_zero["continuity"] == "continuous"
    assert r_empty_zero["resync_required"] is False
    assert r_empty_zero["resync_reason"] is None

    # Empty buffer with after_revision < latest_revision (simulating buffer cleared with latest=150)
    server_cleared = CanonicalLiveServer(state=None, revision=150)
    r_cleared_gap = server_cleared._dispatch({"operation": "get_events", "after_revision": 120})
    assert r_cleared_gap["latest_revision"] == 150
    assert r_cleared_gap["earliest_retained_revision"] is None
    assert r_cleared_gap["continuity"] == "gap"
    assert r_cleared_gap["resync_required"] is True
    assert r_cleared_gap["resync_reason"] == "event_retention_gap"

    # Populate 150 events to test retention cap (100) and eviction of 1..50
    for i in range(1, 151):
        server._revision += 1
        server._record_event(
            "update_file",
            {"origin": "desktop_watcher", "file_path": f"src/mod_{i}.py"},
            type(
                "Result",
                (),
                {
                    "status": "UPDATED",
                    "file_path": f"src/mod_{i}.py",
                    "affected_modules": [f"pkg.consumer_{j}" for j in range(30)],
                },
            )(),
        )

    assert len(server._events) == 100
    assert server._revision == 150
    assert server._events[0]["revision"] == 51
    assert server._events[-1]["revision"] == 150

    # 1. after_revision=None -> continuity="not_requested", resync_required=False
    r_none = server._dispatch({"operation": "get_events", "after_revision": None, "limit": 20})
    assert r_none["latest_revision"] == 150
    assert r_none["earliest_retained_revision"] == 51
    assert r_none["continuity"] == "not_requested"
    assert r_none["resync_required"] is False
    assert r_none["resync_reason"] is None
    assert len(r_none["events"]) == 20
    assert r_none["total"] == 100
    assert r_none["truncated"] is True

    # 2. after_revision=50 (earliest - 1) -> continuity="continuous", resync_required=False
    r_cont = server._dispatch({"operation": "get_events", "after_revision": 50, "limit": 20})
    assert r_cont["continuity"] == "continuous"
    assert r_cont["resync_required"] is False
    assert r_cont["resync_reason"] is None
    assert r_cont["events"][0]["revision"] == 51

    # 3. after_revision=20 (gap: events 21..50 evicted) -> continuity="gap", resync_required=True
    r_gap = server._dispatch({"operation": "get_events", "after_revision": 20, "limit": 20})
    assert r_gap["continuity"] == "gap"
    assert r_gap["resync_required"] is True
    assert r_gap["resync_reason"] == "event_retention_gap"
    assert r_gap["earliest_retained_revision"] == 51

    # 4. Same gap with limit=1 -> gap is still detected against buffer, not first slice
    r_gap_l1 = server._dispatch({"operation": "get_events", "after_revision": 20, "limit": 1})
    assert r_gap_l1["continuity"] == "gap"
    assert r_gap_l1["resync_required"] is True
    assert r_gap_l1["resync_reason"] == "event_retention_gap"
    assert len(r_gap_l1["events"]) == 1
    assert r_gap_l1["total"] == 100
    assert r_gap_l1["truncated"] is True

    # 5. after_revision=150 (latest) -> continuous, empty events
    r_uptodate = server._dispatch({"operation": "get_events", "after_revision": 150})
    assert r_uptodate["continuity"] == "continuous"
    assert r_uptodate["resync_required"] is False
    assert r_uptodate["resync_reason"] is None
    assert r_uptodate["events"] == []
    assert r_uptodate["total"] == 0
    assert r_uptodate["truncated"] is False

    # 8. after_revision > latest_revision (e.g. 155 > 150) -> gap + revision_discontinuity
    r_regr = server._dispatch({"operation": "get_events", "after_revision": 155})
    assert r_regr["continuity"] == "gap"
    assert r_regr["resync_required"] is True
    assert r_regr["resync_reason"] == "revision_discontinuity"

    # 10. limit=None -> returns all 100 retained events (max 100)
    r_all = server._dispatch({"operation": "get_events", "after_revision": None, "limit": None})
    assert len(r_all["events"]) == 100
    assert r_all["total"] == 100
    assert r_all["truncated"] is False

    # 11. affected_modules completeness disclosure preserved
    first_event = r_none["events"][0]
    assert first_event["affected_modules"]["total"] == 30
    assert first_event["affected_modules"]["truncated"] is True
    assert len(first_event["affected_modules"]["items"]) == 20

    # 12. Invalid non-integer or bool after_revision values return controlled error without exception
    for invalid_val in ["1", 1.5, True, False, [1], {"rev": 1}]:
        err_res = server._dispatch({"operation": "get_events", "after_revision": invalid_val})
        assert err_res == {"status": "error", "error": "invalid_after_revision"}

    # 13. Negative after_revision is a valid integer cursor (evaluated against retained window)
    r_neg = server._dispatch({"operation": "get_events", "after_revision": -1})
    assert r_neg["status"] == "ok"
    assert r_neg["continuity"] == "gap"
    assert r_neg["resync_required"] is True
    assert r_neg["resync_reason"] == "event_retention_gap"
    assert len(r_neg["events"]) == 20


def test_connect_or_start_slow_healthy_startup(tmp_path, monkeypatch):
    """Regression: Slow healthy startup where endpoint appears after normal connection timeout
    but within cold-start initialization budget.
    EXPECT:
    - Child process is NOT terminated prematurely.
    - connect_or_start succeeds.
    """
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    # Delay the real authority spawn; the authority itself still publishes the
    # complete endpoint schema only after lease acquisition and bind.
    from contextor.core.live_state import runtime as runtime_mod
    orig_spawn = runtime_mod._spawn_runtime_subprocess

    def mock_spawn(cmd, cwd, env):
        time.sleep(0.25)
        return orig_spawn(cmd, cwd, env)

    monkeypatch.setattr(runtime_mod, "_spawn_runtime_subprocess", mock_spawn)

    # Normal connect timeout is short (0.08s); allow a generous test-local
    # cold-start budget for the real authority process on slow machines.
    t0 = time.monotonic()
    client = runtime_mod.connect_or_start(
        repo,
        owner_token="delayed_token",
        timeout=0.08,
        cold_start_timeout=10.0,
    )
    elapsed = time.monotonic() - t0

    assert client is not None
    assert elapsed >= 0.20  # Verified it waited past 0.08s without killing the child
    status = client.ping()
    assert status.get("status") == "ok"
    client.request("shutdown")


def test_connect_or_start_dead_child_fast_failure(tmp_path, monkeypatch):
    """Regression: Dead child process fails fast with exit code rather than waiting for timeout.
    """
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    from contextor.core.live_state import runtime as runtime_mod
    orig_spawn = runtime_mod._spawn_runtime_subprocess
    poll_calls = 0

    # Mock subprocess that immediately exits with code 42
    def mock_spawn(cmd, cwd, env):
        nonlocal poll_calls
        exit_cmd = [sys.executable, "-c", "import sys; sys.exit(42)"]
        process = orig_spawn(exit_cmd, cwd, env)
        original_poll = process.poll

        def tracked_poll():
            nonlocal poll_calls
            poll_calls += 1
            return original_poll()

        process.poll = tracked_poll
        return process

    monkeypatch.setattr(runtime_mod, "_spawn_runtime_subprocess", mock_spawn)

    import pytest
    with pytest.raises(RuntimeError) as exc_info:
        runtime_mod.connect_or_start(
            repo,
            timeout=0.05,
            cold_start_timeout=10.0,
        )
    message = str(exc_info.value)
    assert poll_calls >= 1
    assert "exited prematurely with code 42" in message
    assert "startup and authority bootstrap timed out" not in message


def test_connect_or_start_true_startup_hang(tmp_path, monkeypatch):
    """Regression: True startup hang terminates child and raises TimeoutError upon hard cold_start_timeout.
    """
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    from contextor.core.live_state import runtime as runtime_mod
    orig_spawn = runtime_mod._spawn_runtime_subprocess

    spawned_pids = []

    # Mock subprocess that hangs (sleeps 30s) without publishing endpoint
    def mock_spawn(cmd, cwd, env):
        hang_cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
        proc = orig_spawn(hang_cmd, cwd, env)
        spawned_pids.append(proc.pid)
        return proc

    monkeypatch.setattr(runtime_mod, "_spawn_runtime_subprocess", mock_spawn)

    import pytest
    with pytest.raises(TimeoutError) as exc_info:
        runtime_mod.connect_or_start(
            repo,
            timeout=0.05,
            cold_start_timeout=0.25,
        )

    assert "timed out after 0.25s" in str(exc_info.value)
    assert len(spawned_pids) == 1
    child_pid = spawned_pids[0]

    # Verify child was killed by connect_or_start
    time.sleep(0.1)
    assert not runtime_mod._is_pid_alive(child_pid)

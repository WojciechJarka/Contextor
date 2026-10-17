from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from contextor.core.live_state.ipc import (
    LIVE_PROTOCOL_VERSION,
    LiveEndpoint,
)
from contextor.core.repository_identity import RepositoryIdentity
from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES
from contextor.mcp import cycle_diagnostics_runtime as C35_TEST_runtime


C35_TEST_C28_GRAPH = {
    "repo.__init__": ("repo.main",),
    "repo.main": ("repo.filters", "ui.__init__"),
    "repo.filters": ("ui.__init__",),
    "ui.__init__": ("ui.gui",),
    "ui.gui": ("repo.__init__",),
}

C35_TEST_C28_SOURCES = {
    "repo.__init__": "from repo.main import run_repo_generator\n",
    "repo.main": (
        "from repo.filters import FilterWindow\n"
        "from ui import theme\n"
        "\n"
        "def run_repo_generator(parent=None):\n"
        "    pass\n"
    ),
    "repo.filters": "from ui import theme\n",
    "ui.__init__": "from .gui import run\n",
    "ui.gui": (
        "from repo import run_repo_generator\n"
        "\n"
        "def run(*, single_instance=None):\n"
        "    pass\n"
    ),
}


def C35_TEST_module_path(root: Path, module_id: str) -> Path:
    return root.joinpath(*module_id.split(".")).with_suffix(".py")


def C35_TEST_write_sources(
    root: Path,
    sources: dict[str, str],
) -> dict[str, str]:
    module_paths = {}

    for module_id, source_text in sources.items():
        path = C35_TEST_module_path(root, module_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source_text, encoding="utf-8")
        module_paths[module_id] = str(path)

    return module_paths


def C35_TEST_state(
    hard_edges,
    module_paths,
    *,
    resync_required=False,
    cycles_state="fresh",
):
    return SimpleNamespace(
        resync_required=resync_required,
        cycles_state=cycles_state,
        dependency_graph=SimpleNamespace(hard_edges=hard_edges),
        modules={
            module_id: SimpleNamespace(path=path)
            for module_id, path in module_paths.items()
        },
    )


def C35_TEST_authority(endpoint, revision, **overrides):
    result = {
        "status": "ok",
        "protocol_version": LIVE_PROTOCOL_VERSION,
        "repo_id": endpoint.repo_id,
        "root_path": endpoint.root_path,
        "runtime_domain_id": endpoint.runtime_domain_id,
        "service_instance_id": endpoint.service_instance_id,
        "lease_generation": endpoint.lease_generation,
        "service_pid": endpoint.pid,
        "process_start_identity": endpoint.process_start_identity,
        "endpoint_fingerprint": endpoint.fingerprint(),
        "revision": revision,
    }
    result.update(overrides)
    return result


class C35_TEST_Harness:
    def __init__(self, monkeypatch):
        self.monkeypatch = monkeypatch
        self.operations = []
        self.client_is_owner_values = []
        self.identity_reads = []
        self.endpoint_reads = []
        self.authority_overrides = [{}, {}]
        self.ping_revisions = [None, None]
        self.event_epochs = ["c35-epoch", "c35-epoch"]
        self.event_overrides = [{}, {}]
        self.revision = 41
        self.client_count = 0

    def install(
        self,
        root: Path,
        state,
        *,
        revision=41,
        identity_repo_id="c35-repo",
        endpoint_repo_id=None,
        endpoint_root_path=None,
    ):
        self.root = root.resolve()
        self.revision = revision
        self.identity = RepositoryIdentity(
            repo_id=identity_repo_id,
            root_path=str(self.root),
            repo_name=self.root.name,
        )
        self.endpoint = LiveEndpoint(
            host="127.0.0.1",
            port=43123,
            authkey_hex="00",
            pid=9876,
            service_pid=9876,
            repo_id=(
                identity_repo_id
                if endpoint_repo_id is None
                else endpoint_repo_id
            ),
            root_path=(
                str(self.root)
                if endpoint_root_path is None
                else endpoint_root_path
            ),
            runtime_domain_id="c35-runtime-domain",
            service_instance_id="c35-service-instance",
            lease_generation=4,
            process_start_identity="c35-process-start",
        )
        self.snapshot = {
            "status": "ok",
            "revision": revision,
            "state": state,
        }

        def read_identity(root_path):
            self.identity_reads.append(Path(root_path).resolve())
            return self.identity

        def read_endpoint(root_path, *, strict=False):
            self.endpoint_reads.append((Path(root_path).resolve(), strict))
            return self.endpoint

        def make_client(endpoint, *, is_owner=False):
            self.client_is_owner_values.append(is_owner)
            self.client_count += 1
            harness = self

            class FakeClient:
                def __init__(self):
                    self.endpoint = endpoint
                    self.authority_index = 0
                    self.ping_index = 0
                    self.events_index = 0

                def authority_status(self):
                    harness.operations.append("authority_status")
                    index = self.authority_index
                    self.authority_index += 1
                    return C35_TEST_authority(
                        endpoint,
                        harness.revision,
                        **harness.authority_overrides[index],
                    )

                def ping(self):
                    harness.operations.append("ping")
                    index = self.ping_index
                    self.ping_index += 1
                    revision_value = harness.ping_revisions[index]
                    if revision_value is None:
                        revision_value = harness.revision
                    return {
                        "status": "ok",
                        "available": True,
                        "revision": revision_value,
                    }

                def snapshot(self):
                    harness.operations.append("snapshot")
                    return harness.snapshot

                def get_events(self, *, after_revision=None, limit=20):
                    harness.operations.append("get_events")
                    index = self.events_index
                    self.events_index += 1
                    result = {
                        "status": "ok",
                        "revision": harness.revision,
                        "latest_revision": harness.revision,
                        "activity_epoch": harness.event_epochs[index],
                        "continuity": "continuous",
                        "resync_required": False,
                        "after_revision": after_revision,
                        "limit": limit,
                    }
                    result.update(harness.event_overrides[index])
                    return result

            return FakeClient()

        self.monkeypatch.setattr(
            C35_TEST_runtime,
            "read_repository_identity",
            read_identity,
        )
        self.monkeypatch.setattr(
            C35_TEST_runtime,
            "_read_endpoint",
            read_endpoint,
        )
        self.monkeypatch.setattr(
            C35_TEST_runtime,
            "LiveStateClient",
            make_client,
        )


@pytest.fixture
def C35_TEST_harness(monkeypatch):
    return C35_TEST_Harness(monkeypatch)


def test_c35_no_cycles_valid_read_only_result(
    tmp_path,
    C35_TEST_harness,
):
    graph = {"acyclic.source": ("acyclic.target",)}
    module_paths = {
        "acyclic.source": str(tmp_path / "acyclic" / "source.py"),
        "acyclic.target": str(tmp_path / "acyclic" / "target.py"),
    }
    state = C35_TEST_state(graph, module_paths)
    C35_TEST_harness.install(tmp_path, state, revision=41)

    result = json.loads(
        C35_TEST_runtime.compute_live_cycle_diagnostics(str(tmp_path))
    )

    assert result["status"] == "computed_non_atomic"
    assert result["cycle_semantics"]["summary"]["cyclic_scc_total"] == 0
    assert result["cycle_semantics"]["runtime_execution_status"] == (
        "UNKNOWN_NOT_EVALUATED"
    )
    assert result["cycle_semantics"]["canonical_graph_revision"] == 41
    assert result["cycle_semantics"]["canonical_graph_revision_status"] == (
        "BRACKETED_IPC_REVISION_NOT_ATOMIC_SOURCE"
    )
    assert result["authority"]["source_snapshot_binding"] == (
        "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    )
    assert "SAFE" not in json.dumps(result)


def test_c35_real_synthetic_pipeline(
    tmp_path,
    C35_TEST_harness,
):
    module_paths = C35_TEST_write_sources(
        tmp_path,
        C35_TEST_C28_SOURCES,
    )
    state = C35_TEST_state(
        deepcopy(C35_TEST_C28_GRAPH),
        module_paths,
    )
    C35_TEST_harness.install(tmp_path, state, revision=42)
    before_modules = {
        name
        for name in sys.modules
        if name in {"repo", "ui"}
    }

    result = json.loads(
        C35_TEST_runtime.compute_live_cycle_diagnostics(str(tmp_path))
    )

    component = result["cycle_semantics"]["components"][0]
    assert result["status"] == "computed_non_atomic"
    assert result["cycle_semantics"]["summary"]["cyclic_scc_total"] == 1
    assert result["cycle_semantics"]["summary"]["conditional_witness_total"] == 2
    assert component["conditional_reexports"]["group_total"] == 1
    assert result["cycle_semantics"]["runtime_execution_status"] == (
        "UNKNOWN_NOT_EVALUATED"
    )
    assert result["authority"]["source_snapshot_binding"] == (
        "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    )
    assert {
        name
        for name in sys.modules
        if name in {"repo", "ui"}
    } == before_modules


def test_c35_never_claims_or_mutates_live(
    tmp_path,
    C35_TEST_harness,
):
    state = C35_TEST_state({}, {})
    C35_TEST_harness.install(tmp_path, state)

    result = json.loads(
        C35_TEST_runtime.compute_live_cycle_diagnostics(str(tmp_path))
    )

    assert result["status"] == "computed_non_atomic"
    assert C35_TEST_harness.client_is_owner_values == [False]
    assert C35_TEST_harness.operations == [
        "authority_status",
        "ping",
        "snapshot",
        "get_events",
        "ping",
        "authority_status",
        "get_events",
    ]
    assert set(C35_TEST_harness.operations) <= {
        "authority_status",
        "ping",
        "snapshot",
        "get_events",
    }
    assert C35_TEST_harness.identity_reads == [tmp_path.resolve()]
    assert C35_TEST_harness.endpoint_reads == [(tmp_path.resolve(), True)]
    assert not (tmp_path / ".contextor").exists()


def test_c35_revision_change_fails_closed(
    tmp_path,
    C35_TEST_harness,
):
    C35_TEST_harness.install(
        tmp_path,
        C35_TEST_state({}, {}),
        revision=43,
    )
    C35_TEST_harness.ping_revisions = [43, 44]

    result = json.loads(
        C35_TEST_runtime.compute_live_cycle_diagnostics(str(tmp_path))
    )

    assert result == {
        "status": "error",
        "error": "canonical_revision_transition",
    }
    assert "cycle_semantics" not in result


def test_c35_authority_change_fails_closed(
    tmp_path,
    C35_TEST_harness,
):
    C35_TEST_harness.install(
        tmp_path,
        C35_TEST_state({}, {}),
        revision=44,
    )
    C35_TEST_harness.authority_overrides = [
        {},
        {"service_instance_id": "changed-service"},
    ]

    result = json.loads(
        C35_TEST_runtime.compute_live_cycle_diagnostics(str(tmp_path))
    )

    assert result == {
        "status": "error",
        "error": "live_authority_transition",
    }
    assert "cycle_semantics" not in result


def test_c35_activity_epoch_change_fails_closed(
    tmp_path,
    C35_TEST_harness,
):
    C35_TEST_harness.install(
        tmp_path,
        C35_TEST_state({}, {}),
        revision=45,
    )
    C35_TEST_harness.event_epochs = ["first-epoch", "second-epoch"]

    result = json.loads(
        C35_TEST_runtime.compute_live_cycle_diagnostics(str(tmp_path))
    )

    assert result == {
        "status": "error",
        "error": "live_activity_epoch_transition",
    }
    assert "cycle_semantics" not in result


def test_c35_resync_or_stale_cycles_rejected(
    tmp_path,
    C35_TEST_harness,
):
    cases = (
        (True, "fresh", "canonical_resync_not_verified"),
        (False, "stale", "canonical_cycles_not_fresh"),
        (False, "deferred", "canonical_cycles_not_fresh"),
    )

    for index, (resync_required, cycles_state, expected_error) in enumerate(cases):
        root = tmp_path / str(index)
        root.mkdir()
        state = C35_TEST_state(
            {},
            {},
            resync_required=resync_required,
            cycles_state=cycles_state,
        )
        C35_TEST_harness.install(root, state, revision=46 + index)

        result = json.loads(
            C35_TEST_runtime.compute_live_cycle_diagnostics(str(root))
        )

        assert result == {"status": "error", "error": expected_error}
        assert "cycle_semantics" not in result


def test_c35_missing_source_is_partial_not_empty(
    tmp_path,
    C35_TEST_harness,
):
    graph = {
        "missing.module": ("present.module",),
        "present.module": ("missing.module",),
    }
    module_paths = C35_TEST_write_sources(
        tmp_path,
        {"present.module": "from missing.module import item\n"},
    )
    module_paths["missing.module"] = str(
        C35_TEST_module_path(tmp_path, "missing.module")
    )
    state = C35_TEST_state(graph, module_paths)
    C35_TEST_harness.install(tmp_path, state, revision=49)

    result = json.loads(
        C35_TEST_runtime.compute_live_cycle_diagnostics(str(tmp_path))
    )

    assert result["status"] == "partial_source_evidence"
    assert result["cycle_semantics"]["summary"]["cyclic_scc_total"] == 1
    assert result["cycle_semantics"]["summary"]["conditional_witness_total"] == 0
    assert result["source_cohort"]["issues"] == [
        {
            "module_id": "missing.module",
            "reason": "SOURCE_UNREADABLE",
        }
    ]
    assert result["cycle_semantics"]["runtime_execution_status"] == (
        "UNKNOWN_NOT_EVALUATED"
    )


def test_c35_repository_endpoint_mismatch(
    tmp_path,
    C35_TEST_harness,
):
    C35_TEST_harness.install(
        tmp_path,
        C35_TEST_state({}, {}),
        identity_repo_id="identity-repo",
        endpoint_repo_id="different-repo",
    )

    result = json.loads(
        C35_TEST_runtime.compute_live_cycle_diagnostics(str(tmp_path))
    )

    assert result == {
        "status": "error",
        "error": "live_endpoint_identity_mismatch",
    }
    assert C35_TEST_harness.client_count == 0
    assert C35_TEST_harness.operations == []


def test_c35_byte_guard_confirmation_required(
    tmp_path,
    C35_TEST_harness,
):
    module_count = 64
    padding = "x" * 96
    modules = [
        f"c35_large.segment_{index:03d}_{padding}"
        for index in range(module_count)
    ]
    graph = {
        module_id: (modules[(index + 1) % module_count],)
        for index, module_id in enumerate(modules)
    }
    module_paths = C35_TEST_write_sources(
        tmp_path,
        {module_id: "" for module_id in modules},
    )
    state = C35_TEST_state(graph, module_paths)
    C35_TEST_harness.install(tmp_path, state, revision=51)

    full_text = C35_TEST_runtime.compute_live_cycle_diagnostics(
        str(tmp_path),
        max_components=64,
        max_edges=64,
        max_groups=0,
        max_witnesses=0,
        allow_large_output=True,
    )
    full_payload = json.loads(full_text)
    serialized_bytes = len(full_text.encode("utf-8"))
    assert LARGE_OUTPUT_WARNING_BYTES == 15360
    assert serialized_bytes > LARGE_OUTPUT_WARNING_BYTES

    C35_TEST_harness.client_count = 0
    C35_TEST_harness.operations.clear()
    guarded_text = C35_TEST_runtime.compute_live_cycle_diagnostics(
        str(tmp_path),
        max_components=64,
        max_edges=64,
        max_groups=0,
        max_witnesses=0,
        allow_large_output=False,
    )
    guarded_payload = json.loads(guarded_text)

    assert guarded_payload["status"] == "confirmation_required"
    assert guarded_payload["estimated_output_bytes"] == serialized_bytes
    assert json.loads(full_text) == full_payload
    assert C35_TEST_runtime.compute_live_cycle_diagnostics(
        str(tmp_path),
        max_components=64,
        max_edges=64,
        max_groups=0,
        max_witnesses=0,
        allow_large_output=True,
    ) == full_text


def test_c35_parameter_validation(
    tmp_path,
    C35_TEST_harness,
):
    invalid_calls = (
        ({"max_components": True}, "invalid_max_components"),
        ({"max_edges": -1}, "invalid_max_edges"),
        ({"max_groups": False}, "invalid_max_groups"),
        ({"max_witnesses": 65}, "invalid_max_witnesses"),
        ({"max_searches": 0}, "invalid_max_searches"),
        ({"allow_large_output": 1}, "invalid_allow_large_output"),
    )

    for kwargs, expected_error in invalid_calls:
        result = json.loads(
            C35_TEST_runtime.compute_live_cycle_diagnostics(
                str(tmp_path),
                **kwargs,
            )
        )
        assert result == {"status": "error", "error": expected_error}

    assert C35_TEST_harness.client_count == 0


def test_c35_deterministic_fixed_snapshot_result(
    tmp_path,
    C35_TEST_harness,
):
    sources = {
        "c35_fixed.alpha": (
            "raise RuntimeError('fixture source must not execute')\n"
        ),
        "c35_fixed.beta": (
            "raise RuntimeError('fixture source must not execute')\n"
        ),
    }
    graph = {
        "c35_fixed.alpha": ("c35_fixed.beta",),
        "c35_fixed.beta": ("c35_fixed.alpha",),
    }
    module_paths = C35_TEST_write_sources(tmp_path, sources)
    state = C35_TEST_state(deepcopy(graph), module_paths)
    C35_TEST_harness.install(tmp_path, state, revision=52)
    graph_before = deepcopy(state.dependency_graph.hard_edges)
    snapshot_object = C35_TEST_harness.snapshot
    source_bytes_before = {
        module_id: Path(path).read_bytes()
        for module_id, path in module_paths.items()
    }

    first = C35_TEST_runtime.compute_live_cycle_diagnostics(str(tmp_path))
    second = C35_TEST_runtime.compute_live_cycle_diagnostics(str(tmp_path))

    assert json.loads(first) == json.loads(second)
    assert C35_TEST_harness.snapshot is snapshot_object
    assert state.dependency_graph.hard_edges == graph_before
    assert {
        module_id: Path(path).read_bytes()
        for module_id, path in module_paths.items()
    } == source_bytes_before
    assert all("fixture source must not execute" in source for source in sources.values())
    assert json.loads(first)["cycle_semantics"]["runtime_execution_status"] == (
        "UNKNOWN_NOT_EVALUATED"
    )


def test_c36r_absent_snapshot_resync_uses_verified_events(
    tmp_path,
    C35_TEST_harness,
):
    state = C35_TEST_state({}, {})
    delattr(state, "resync_required")

    C35_TEST_harness.install(tmp_path, state, revision=61)

    result = json.loads(
        C35_TEST_runtime.compute_live_cycle_diagnostics(
            str(tmp_path)
        )
    )

    assert result["status"] == "computed_non_atomic"
    assert result["authority"]["canonical_revision"] == 61
    assert result["cycle_semantics"][
        "runtime_execution_status"
    ] == "UNKNOWN_NOT_EVALUATED"
    assert C35_TEST_harness.operations == [
        "authority_status",
        "ping",
        "snapshot",
        "get_events",
        "ping",
        "authority_status",
        "get_events",
    ]


def test_c36r_explicit_false_snapshot_resync_allowed(
    tmp_path,
    C35_TEST_harness,
):
    state = C35_TEST_state(
        {},
        {},
        resync_required=False,
    )

    C35_TEST_harness.install(tmp_path, state, revision=62)

    result = json.loads(
        C35_TEST_runtime.compute_live_cycle_diagnostics(
            str(tmp_path)
        )
    )

    assert result["status"] == "computed_non_atomic"
    assert result["authority"]["canonical_revision"] == 62


def test_c36r_present_non_false_snapshot_resync_rejected(
    tmp_path,
    C35_TEST_harness,
):
    for index, value in enumerate((True, None, "false", 0)):
        root = tmp_path / str(index)
        root.mkdir()

        state = C35_TEST_state({}, {})
        state.resync_required = value

        C35_TEST_harness.install(
            root,
            state,
            revision=63 + index,
        )

        result = json.loads(
            C35_TEST_runtime.compute_live_cycle_diagnostics(
                str(root)
            )
        )

        assert result == {
            "status": "error",
            "error": "canonical_resync_not_verified",
        }
        assert "cycle_semantics" not in result


def test_c36r_absent_snapshot_resync_never_overrides_event_failure(
    tmp_path,
    C35_TEST_harness,
):
    state = C35_TEST_state({}, {})
    delattr(state, "resync_required")

    C35_TEST_harness.install(tmp_path, state, revision=67)

    C35_TEST_harness.event_overrides = [
        {"resync_required": True},
        {},
    ]

    result = json.loads(
        C35_TEST_runtime.compute_live_cycle_diagnostics(
            str(tmp_path)
        )
    )

    assert result == {
        "status": "error",
        "error": "live_event_continuity_unverified",
    }
    assert "cycle_semantics" not in result

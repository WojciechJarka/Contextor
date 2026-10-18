"""Real Desktop and MCP full-analysis canonical-state parity gate."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import pickle
import threading
import time
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from datetime import datetime
from enum import Enum
from pathlib import Path, PurePath
from types import SimpleNamespace
from uuid import uuid4

import pytest

from contextor import mcp_server
from contextor.core.analysis.state_manager import (
    FileState,
    FileStateManager,
    RepositoryAnalysisState,
    load_engine_state,
)
from contextor.core.api import facade
from contextor.core.cycle_semantics.contracts import fingerprint_hard_edges
from contextor.core.cycle_semantics.materialization import materialize_cycle_semantics
from contextor.core.domain.graph import ProjectGraph
from contextor.core.graph.resolver import TrieNode
from contextor.core.live_state import connect
from contextor.core.live_state.runtime import _read_endpoint
from contextor.core.live_state.store import read_metadata
from contextor.core.paths import repo_cache_dir
from contextor.core.repository_identity import (
    ensure_repository_identity,
    read_repository_identity,
)
from contextor.mcp import analysis_jobs
from contextor.ui import gui
from contextor.ui.gui import ContextorGUI


_FIXTURE_SOURCES = {
    "pkg/__init__.py": (
        "from .api import service as service\n"
        '__all__ = ["service"]\n'
    ),
    "pkg/api.py": "def service():\n    return 1\n",
    "pkg/runtime.py": "def run():\n    return 2\n",
    "consumer.py": (
        "from pkg import runtime as runtime_alias\n"
        "from pkg import service\n"
        "\n"
        "RESULT = service() + runtime_alias.run()\n"
    ),
    "other.py": (
        "from pkg.api import service as alias\n"
        "\n"
        "VALUE = alias()\n"
    ),
}


class _UnsupportedCanonicalValue(TypeError):
    def __init__(self, path: str, value: object):
        self.path = path
        self.value_type = type(value)
        super().__init__(
            f"Unsupported canonical value at {path}: "
            f"{type(value).__module__}.{type(value).__qualname__}"
        )


class _SnapshotCapture:
    def __init__(
        self,
        *,
        state: RepositoryAnalysisState,
        metadata: object,
        file_states: dict[str, FileState],
        file_state_payload: dict,
        source_bytes: dict[str, bytes],
        cache_dir: Path,
    ):
        self.state = state
        self.metadata = metadata
        self.file_states = file_states
        self.file_state_payload = file_state_payload
        self.source_bytes = source_bytes
        self.cache_dir = cache_dir


def _type_name(value: object) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _project(value: object, path: str) -> dict:
    """Return a deterministic, lossless structural projection or fail closed."""

    if isinstance(value, Enum):
        return {
            "kind": "enum",
            "type": _type_name(value),
            "value": _project(value.value, f"{path}.value"),
        }

    if isinstance(value, PurePath):
        return {"kind": "path", "type": _type_name(value), "value": str(value)}

    if isinstance(value, TrieNode):
        children = value.children
        if not isinstance(children, Mapping):
            raise _UnsupportedCanonicalValue(f"{path}.children", children)
        if any(not isinstance(name, str) for name in children):
            bad_name = next(name for name in children if not isinstance(name, str))
            raise _UnsupportedCanonicalValue(f"{path}.children[{bad_name!r}]", bad_name)
        return {
            "kind": "trie",
            "type": _type_name(value),
            "is_module": _project(value.is_module, f"{path}.is_module"),
            "full_name": _project(value.full_name, f"{path}.full_name"),
            "children": {
                name: _project(children[name], f"{path}.children[{name!r}]")
                for name in sorted(children)
            },
        }

    if is_dataclass(value) and not isinstance(value, type):
        return {
            "kind": "dataclass",
            "type": _type_name(value),
            "fields": {
                item.name: _project(getattr(value, item.name), f"{path}.{item.name}")
                for item in fields(value)
            },
        }

    if isinstance(value, Mapping):
        items = [
            (
                _project(key, f"{path}.<key>"),
                _project(item, f"{path}[{key!r}]"),
            )
            for key, item in value.items()
        ]
        items.sort(key=lambda pair: repr(pair[0]))
        return {"kind": "mapping", "type": _type_name(value), "items": items}

    if isinstance(value, (list, tuple)):
        return {
            "kind": "sequence",
            "type": _type_name(value),
            "items": [
                _project(item, f"{path}[{index}]")
                for index, item in enumerate(value)
            ],
        }

    if isinstance(value, (set, frozenset)):
        items = [_project(item, f"{path}{{item}}") for item in value]
        items.sort(key=repr)
        return {"kind": "set", "type": _type_name(value), "items": items}

    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        if isinstance(value, float):
            primitive_value = value.hex()
        elif isinstance(value, bytes):
            primitive_value = value.hex()
        else:
            primitive_value = value
        return {
            "kind": "primitive",
            "type": _type_name(value),
            "value": primitive_value,
        }

    raise _UnsupportedCanonicalValue(path, value)


def _first_difference(left: object, right: object, path: str = "state"):
    if type(left) is not type(right):
        return path, left, right
    if left == right:
        return None
    if not isinstance(left, dict):
        return path, left, right

    left_kind = left.get("kind")
    right_kind = right.get("kind")
    if left_kind != right_kind:
        return f"{path}.kind", left_kind, right_kind
    if left.get("type") != right.get("type"):
        return f"{path}.<type>", left.get("type"), right.get("type")

    if left_kind in {"dataclass", "trie"}:
        keys = tuple(left.keys())
        if keys != tuple(right.keys()):
            return f"{path}.<structure>", keys, tuple(right.keys())
        for name in left:
            if name in {"kind", "type"}:
                continue
            left_value = left[name]
            right_value = right[name]
            if isinstance(left_value, dict) and isinstance(right_value, dict):
                field_names = tuple(left_value.keys())
                if field_names != tuple(right_value.keys()):
                    return f"{path}.{name}.<fields>", field_names, tuple(right_value.keys())
                for field_name in left_value:
                    difference = _first_difference(
                        left_value[field_name],
                        right_value[field_name],
                        f"{path}.{field_name if name == 'fields' else name + '.' + field_name}",
                    )
                    if difference is not None:
                        return difference
            else:
                difference = _first_difference(
                    left_value, right_value, f"{path}.{name}"
                )
                if difference is not None:
                    return difference
        return None

    if left_kind == "mapping":
        left_items = left["items"]
        right_items = right["items"]
        if len(left_items) != len(right_items):
            return f"{path}.<key-count>", len(left_items), len(right_items)
        for (left_key, left_value), (right_key, right_value) in zip(left_items, right_items):
            if left_key != right_key:
                return f"{path}.<keys>", left_key, right_key
            difference = _first_difference(
                left_value,
                right_value,
                f"{path}[{_short_repr(left_key, 120)}]",
            )
            if difference is not None:
                return difference
        return None

    if left_kind in {"sequence", "set"}:
        left_items = left["items"]
        right_items = right["items"]
        if len(left_items) != len(right_items):
            return f"{path}.<length>", len(left_items), len(right_items)
        for index, (left_item, right_item) in enumerate(zip(left_items, right_items)):
            difference = _first_difference(
                left_item, right_item, f"{path}[{index}]"
            )
            if difference is not None:
                return difference
        return None

    if left_kind in {"primitive", "path"}:
        if left.get("value") != right.get("value"):
            return path, left.get("value"), right.get("value")
        return None

    if left_kind == "enum":
        return _first_difference(left["value"], right["value"], f"{path}.value")

    return path, left, right


def _short_repr(value: object, limit: int = 500) -> str:
    result = repr(value)
    return result if len(result) <= limit else result[: limit - 3] + "..."


def _preserve_mismatch_evidence(
    tmp_path: Path,
    desktop: _SnapshotCapture,
    mcp: _SnapshotCapture,
) -> Path:
    evidence_dir = tmp_path / "b0g2c_canonical_mismatch_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for label, capture in (("desktop", desktop), ("mcp", mcp)):
        payload = {
            "state": capture.state,
            "metadata": capture.metadata,
            "file_states": capture.file_states,
            "file_state_payload": capture.file_state_payload,
            "source_bytes": capture.source_bytes,
            "cache_dir": str(capture.cache_dir),
        }
        with (evidence_dir / f"{label}.pickle").open("wb") as output:
            pickle.dump(payload, output, protocol=pickle.HIGHEST_PROTOCOL)
    return evidence_dir


def _write_fixture(root: Path) -> dict[str, bytes]:
    source_bytes = {}
    for relative, source in _FIXTURE_SOURCES.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        encoded = source.encode("utf-8")
        target.write_bytes(encoded)
        source_bytes[relative] = encoded
    return source_bytes


def _assert_source_bytes(root: Path, expected: dict[str, bytes]) -> None:
    actual_files = {
        relative: (root / relative).read_bytes()
        for relative in expected
    }
    assert actual_files == expected, "fixture Python source bytes changed during analysis"


def _assert_no_live_endpoint(root: Path) -> None:
    endpoint = _read_endpoint(root, strict=True)
    assert endpoint is None, f"unexpected LIVE endpoint for test repository: {endpoint!r}"
    assert connect(root) is None, "temporary repository unexpectedly has a LIVE client"


def _generation_file(cache_dir: Path, name: str) -> Path:
    assert isinstance(name, str) and name, "snapshot metadata has an empty generation file link"
    raw = Path(name)
    candidate = raw if raw.is_absolute() else cache_dir / raw
    resolved = candidate.resolve()
    assert resolved.is_relative_to(cache_dir.resolve()), (
        f"snapshot generation file escaped isolated cache: {name!r}"
    )
    assert resolved.is_file(), f"snapshot generation file is missing: {resolved}"
    return resolved


def _capture_snapshot(
    root: Path,
    *,
    expected_writer: str,
    expected_repo_id: str,
    source_bytes: dict[str, bytes],
) -> _SnapshotCapture:
    cache_dir = repo_cache_dir(root)
    metadata = read_metadata(cache_dir)
    assert metadata is not None, "authoritative snapshot metadata is missing or invalid"
    assert metadata.writer == expected_writer
    assert metadata.repo_id == expected_repo_id
    assert metadata.root_path == str(root)
    assert metadata.state_id
    assert metadata.revision > 0

    state_path = _generation_file(cache_dir, metadata.state_file)
    file_state_path = _generation_file(cache_dir, metadata.file_state_file)
    if metadata.lineage_manifest_file:
        _generation_file(cache_dir, metadata.lineage_manifest_file)

    file_state_payload = json.loads(file_state_path.read_text(encoding="utf-8"))
    assert isinstance(file_state_payload, dict)
    assert isinstance(file_state_payload.get("_meta"), dict)
    assert file_state_payload["_meta"].get("state_id") == metadata.state_id
    assert file_state_payload["_meta"].get("revision") == metadata.revision

    loaded = load_engine_state(
        str(cache_dir),
        metadata.state_id,
        expected_repo_id=expected_repo_id,
        expected_root_path=str(root),
    )
    assert isinstance(loaded, RepositoryAnalysisState)
    assert loaded.revision == metadata.revision
    assert loaded.state_id == metadata.state_id
    assert getattr(loaded, "resync_required", False) is not True
    assert getattr(loaded, "provenance", None) == "snapshot"
    assert state_path.is_file()

    file_state_manager = FileStateManager(str(cache_dir))
    assert file_state_manager.baseline_status == "trusted"
    assert file_state_manager.state_id == metadata.state_id
    assert file_state_manager.revision == metadata.revision
    file_states = copy.deepcopy(file_state_manager._state)

    expected_paths = {
        str((root / relative).resolve())
        for relative in source_bytes
    }
    assert set(file_states) == expected_paths, (
        "FileState path coverage differs from fixture source coverage: "
        f"expected={sorted(expected_paths)!r}, actual={sorted(file_states)!r}"
    )
    for relative, content in source_bytes.items():
        path = str((root / relative).resolve())
        file_state = file_states[path]
        assert isinstance(file_state, FileState)
        assert file_state.sha256 == hashlib.sha256(content).hexdigest()
        assert file_state.size == len(content)

    state_copy = copy.deepcopy(loaded)
    state_copy_fields = tuple(item.name for item in fields(RepositoryAnalysisState))
    assert set(state_copy_fields) == set(vars(state_copy)) & set(state_copy_fields)

    return _SnapshotCapture(
        state=state_copy,
        metadata=copy.deepcopy(metadata),
        file_states=file_states,
        file_state_payload=copy.deepcopy(file_state_payload),
        source_bytes=copy.deepcopy(source_bytes),
        cache_dir=cache_dir,
    )


def _projected_string_member(
    projection: dict,
    key: str,
    path: str,
) -> dict:
    assert projection.get("kind") == "mapping", (
        f"Expected projected mapping at {path}"
    )
    key_projection = {
        "kind": "primitive",
        "type": "builtins.str",
        "value": key,
    }
    matches = [
        value
        for candidate_key, value in projection["items"]
        if candidate_key == key_projection
    ]
    assert len(matches) == 1, (
        f"Required canonical field missing or duplicated: {path}[{key!r}]"
    )
    return matches[0]


def _normalize_proved_report_timestamps(
    projection: dict,
) -> None:
    layer = projection["fields"]["layer_information"]
    summary = _projected_string_member(
        layer,
        "summary_data",
        "layer_information",
    )
    header = _projected_string_member(
        summary,
        "report_header",
        "layer_information.summary_data",
    )

    for parent, field_name, field_path in (
        (
            summary,
            "generated_at",
            "layer_information.summary_data.generated_at",
        ),
        (
            header,
            "generated_at",
            "layer_information.summary_data.report_header.generated_at",
        ),
    ):
        timestamp = _projected_string_member(
            parent,
            field_name,
            field_path,
        )
        assert timestamp.get("kind") == "primitive"
        assert timestamp.get("type") == "builtins.str"
        value = timestamp.get("value")
        assert isinstance(value, str)
        parsed = datetime.fromisoformat(value)
        assert parsed.isoformat() == value, (
            f"Invalid canonical report timestamp at {field_path}"
        )

        # Normalize only the comparative projection.
        # Never modify the captured canonical state.
        timestamp["value"] = "<operational-report-timestamp>"


def _state_projection(
    state: RepositoryAnalysisState,
    *,
    normalize_report_timestamps: bool = False,
) -> dict:
    assert type(state) is RepositoryAnalysisState
    declared_fields = tuple(
        item.name for item in fields(RepositoryAnalysisState)
    )
    projection = _project(
        state,
        "RepositoryAnalysisState",
    )
    assert projection["kind"] == "dataclass"
    assert tuple(projection["fields"]) == declared_fields

    if normalize_report_timestamps:
        _normalize_proved_report_timestamps(projection)

    return projection


def _assert_incremental_full_cycle_parity(
    initial_full: RepositoryAnalysisState,
    incremental: RepositoryAnalysisState,
    fresh_full: RepositoryAnalysisState,
    *,
    expected_invalidation_reason: str,
) -> None:
    """Compare current architecture and verify each semantic evidence generation."""
    initial_projection = _state_projection(initial_full, normalize_report_timestamps=True)
    incremental_projection = _state_projection(incremental, normalize_report_timestamps=True)
    fresh_projection = _state_projection(fresh_full, normalize_report_timestamps=True)
    semantic_fields = {
        "cycle_semantics",
        "cycle_semantics_state",
        "cycle_semantics_invalidation_reason",
    }
    for field in fields(RepositoryAnalysisState):
        name = field.name
        if name in semantic_fields:
            continue
        difference = _first_difference(
            incremental_projection["fields"][name],
            fresh_projection["fields"][name],
            f"state.{name}",
        )
        assert difference is None, f"Current canonical field mismatch: {difference!r}"

    initial_snapshot = initial_full.cycle_semantics
    incremental_snapshot = incremental.cycle_semantics
    fresh_snapshot = fresh_full.cycle_semantics
    assert initial_snapshot is not None, "Initial FULL semantic snapshot missing"
    assert incremental_snapshot is not None, "Historical incremental snapshot missing"
    assert fresh_snapshot is not None, "Fresh FULL semantic snapshot missing"
    assert initial_full.cycle_semantics_state == "fresh"
    assert initial_full.cycle_semantics_invalidation_reason is None
    assert incremental_projection["fields"]["cycle_semantics"] == (
        initial_projection["fields"]["cycle_semantics"]
    ), "Historical semantic snapshot changed"
    assert incremental.cycle_semantics_state == "stale", "Incremental evidence must remain stale"
    assert incremental.cycle_semantics_invalidation_reason == (
        expected_invalidation_reason
    ), "Wrong incremental semantic invalidation reason"
    assert fresh_full.cycle_semantics_state == "fresh"
    assert fresh_full.cycle_semantics_invalidation_reason is None

    before_sha = fingerprint_hard_edges(initial_full.dependency_graph.hard_edges)
    incremental_sha = fingerprint_hard_edges(incremental.dependency_graph.hard_edges)
    full_sha = fingerprint_hard_edges(fresh_full.dependency_graph.hard_edges)
    assert initial_snapshot.graph_sha256 == before_sha, "Initial snapshot graph identity mismatch"
    assert incremental_snapshot.graph_sha256 == before_sha, "Historical graph SHA was rewritten"
    assert incremental_sha == full_sha, "Current incremental hard graph differs from FULL"
    assert fresh_snapshot.graph_sha256 == full_sha, "Fresh FULL snapshot graph identity mismatch"


@pytest.mark.parametrize("fault,expected", [
    ("current_graph", "Current canonical field mismatch"),
    ("historical_snapshot", "Historical semantic snapshot changed"),
    ("false_fresh", "Incremental evidence must remain stale"),
    ("wrong_reason", "Wrong incremental semantic invalidation reason"),
    ("other_canonical_field", "Current canonical field mismatch"),
])
def test_incremental_full_cycle_parity_rejects_contract_violations(
    tmp_path, fault, expected
):
    source = tmp_path / "pkg.py"
    source.write_bytes(b"VALUE = 1\n")
    graph = ProjectGraph(hard_edges={"pkg": set()}, soft_edges={"pkg": set()})
    snapshot = materialize_cycle_semantics(
        tmp_path, graph.hard_edges, {"pkg": source},
        {"pkg": hashlib.sha256(source.read_bytes()).hexdigest()},
    )
    initial = _report_timestamp_state()
    initial.dependency_graph = graph
    initial.cycle_semantics = snapshot
    initial.cycle_semantics_state = "fresh"
    incremental = copy.deepcopy(initial)
    incremental.cycle_semantics_state = "stale"
    incremental.cycle_semantics_invalidation_reason = "SOURCE_CHANGED"
    fresh_full = copy.deepcopy(initial)

    if fault == "current_graph":
        incremental.dependency_graph = graph.with_module_edges("pkg", {"other"}, set())
    elif fault == "historical_snapshot":
        incremental.cycle_semantics = replace(
            snapshot, graph_sha256=fingerprint_hard_edges({"pkg": {"other"}}),
        )
    elif fault == "false_fresh":
        incremental.cycle_semantics_state = "fresh"
    elif fault == "wrong_reason":
        incremental.cycle_semantics_invalidation_reason = "SOURCE_DELETED"
    elif fault == "other_canonical_field":
        incremental.artifacts["unexpected"] = {}

    with pytest.raises(AssertionError, match=expected):
        _assert_incremental_full_cycle_parity(
            initial, incremental, fresh_full,
            expected_invalidation_reason="SOURCE_CHANGED",
        )


def _report_timestamp_state(
    summary_timestamp: object = "2026-10-12T12:09:48.838009",
    header_timestamp: object = "2026-10-12T12:09:48.623010",
) -> RepositoryAnalysisState:
    return RepositoryAnalysisState(
        layer_information={
            "summary_data": {
                "generated_at": summary_timestamp,
                "report_header": {
                    "generated_at": header_timestamp,
                },
            },
        },
    )


def test_report_timestamp_normalization_preserves_captured_state():
    desktop = _report_timestamp_state()
    mcp = _report_timestamp_state(
        "2026-10-12T12:09:50.608340",
        "2026-10-12T12:09:50.357250",
    )
    desktop_before = copy.deepcopy(vars(desktop))
    mcp_before = copy.deepcopy(vars(mcp))

    assert _state_projection(desktop) != _state_projection(mcp)
    assert _state_projection(
        desktop, normalize_report_timestamps=True
    ) == _state_projection(
        mcp, normalize_report_timestamps=True
    )
    assert vars(desktop) == desktop_before
    assert vars(mcp) == mcp_before


def test_report_timestamp_normalization_has_no_wildcard_exclusion():
    desktop = _report_timestamp_state()
    mcp = copy.deepcopy(desktop)
    desktop.layer_information["other"] = {"generated_at": "2026-10-12T12:00:00"}
    mcp.layer_information["other"] = {"generated_at": "2026-10-12T12:00:01"}

    assert _state_projection(
        desktop, normalize_report_timestamps=True
    ) != _state_projection(
        mcp, normalize_report_timestamps=True
    )


@pytest.mark.parametrize("missing_from", ["summary_data", "report_header"])
def test_report_timestamp_normalization_rejects_missing_timestamp(missing_from):
    state = _report_timestamp_state()
    target = state.layer_information["summary_data"]
    if missing_from == "report_header":
        target = target["report_header"]
    del target["generated_at"]

    with pytest.raises(AssertionError, match="missing or duplicated"):
        _state_projection(state, normalize_report_timestamps=True)


@pytest.mark.parametrize("field", ["summary_data", "report_header"])
@pytest.mark.parametrize("invalid", ["not-a-timestamp", 123])
def test_report_timestamp_normalization_rejects_invalid_timestamp(field, invalid):
    state = _report_timestamp_state()
    target = state.layer_information["summary_data"]
    if field == "report_header":
        target = target["report_header"]
    target["generated_at"] = invalid

    with pytest.raises((AssertionError, ValueError)):
        _state_projection(state, normalize_report_timestamps=True)


def test_report_timestamp_normalization_preserves_semantic_difference_and_fields():
    desktop = _report_timestamp_state()
    mcp = copy.deepcopy(desktop)
    mcp.artifacts["pkg.module"] = {"symbols": ["changed"]}

    desktop_projection = _state_projection(
        desktop, normalize_report_timestamps=True
    )
    mcp_projection = _state_projection(
        mcp, normalize_report_timestamps=True
    )
    declared_fields = {item.name for item in fields(RepositoryAnalysisState)}
    assert set(desktop_projection["fields"]) == declared_fields
    assert set(mcp_projection["fields"]) == declared_fields
    assert desktop_projection != mcp_projection


def _assert_file_state_parity(desktop: _SnapshotCapture, mcp: _SnapshotCapture) -> None:
    desktop_projection = _project(desktop.file_states, "FileStateManager._state")
    mcp_projection = _project(mcp.file_states, "FileStateManager._state")
    difference = _first_difference(desktop_projection, mcp_projection, "FileStateManager._state")
    if difference is not None:
        field_path, desktop_value, mcp_value = difference
        evidence_dir = _preserve_mismatch_evidence(
            desktop.cache_dir.parents[2],
            desktop,
            mcp,
        )
        pytest.fail(
            "FileState mismatch: "
            f"field={field_path}; desktop={_short_repr(desktop_value)}; "
            f"mcp={_short_repr(mcp_value)}; evidence={evidence_dir}",
            pytrace=False,
        )


def _capture_gui_full_run(root: Path, monkeypatch) -> dict:
    execution = {"logs": []}
    controller = ContextorGUI.__new__(ContextorGUI)
    controller.root = object()
    controller.repo_path_var = SimpleNamespace(get=lambda: str(root))
    controller.progress_bar = SimpleNamespace(is_cancelled=False)
    controller.log_box = object()
    controller.cpu_indicator = object()
    controller.stop_btn = object()
    controller._live_recovery_incident = lambda _path: None
    controller._busy_buttons = lambda: []

    def execute_real_task(_root, _progress_bar, task, **kwargs):
        execution["operation_name"] = kwargs.get("operation_name")
        execution["task"] = task
        outcome = task(
            log=lambda message: execution["logs"].append(str(message)),
            progress_callback=lambda *_args, **_kwargs: True,
        )
        execution["outcome"] = outcome
        return outcome

    monkeypatch.setattr(gui, "run_with_progress", execute_real_task)
    ContextorGUI.analyze(controller)
    assert execution.get("operation_name") == "Repository analysis"
    assert callable(execution.get("task"))
    errors, analysis_result = execution["outcome"]
    assert not errors, f"Desktop full analysis returned errors: {errors!r}"
    assert analysis_result is not None
    assert getattr(analysis_result, "live_publish_status", None) == "not_attempted"
    assert controller._full_analysis_done == execution["outcome"]
    execution["analysis_result"] = analysis_result
    execution["error_count"] = len(errors)
    return execution


def _run_real_mcp_project_job(root: Path) -> dict:
    started = json.loads(asyncio.run(mcp_server.analyze_project.fn(str(root))))
    assert started.get("job_id")
    assert started.get("operation") == "project"
    assert started.get("repo_path") == str(root)
    assert started.get("reused", False) is False, "MCP returned an unexpectedly reused job"
    job_id = started["job_id"]

    deadline = time.monotonic() + 120.0
    worker = None
    final_job = None
    while time.monotonic() < deadline:
        current = json.loads(mcp_server.get_analysis_status.fn(str(root), job_id))
        assert current.get("job_id") == job_id
        assert current.get("operation") == "project"
        with analysis_jobs._analysis_job_lock:
            current_worker = analysis_jobs._analysis_tasks.get(job_id)
        if current_worker is not None:
            worker = current_worker
        if current.get("status") not in {"queued", "running"}:
            final_job = current
            break
        remaining = max(0.0, deadline - time.monotonic())
        if worker is not None:
            worker.join(timeout=min(0.05, remaining))
        else:
            time.sleep(min(0.05, remaining))

    assert final_job is not None, f"MCP analysis job exceeded bounded deadline: {job_id}"
    if worker is not None:
        worker.join(timeout=5.0)
        assert not worker.is_alive(), f"MCP worker thread remained alive: {job_id}"
    with analysis_jobs._analysis_job_lock:
        assert job_id not in analysis_jobs._analysis_tasks
        assert str(root) not in analysis_jobs._analysis_jobs_by_repo

    assert final_job.get("status") == "completed", (
        f"MCP project job did not complete: {final_job!r}"
    )
    assert final_job.get("error") is None
    assert final_job.get("live_publish_status") == "not_attempted"
    assert final_job.get("live_publish_revision") is None
    assert final_job.get("owner_pid") in {None, os.getpid()}
    return {"started": started, "completed": final_job, "worker": worker}


def test_real_desktop_and_mcp_full_entrypoints_have_identical_canonical_state(
    tmp_path, monkeypatch, isolated_dirs
):
    root = (tmp_path / f"b0g2c_repo_{uuid4().hex}").resolve()
    root.mkdir()
    monkeypatch.setenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        str(tmp_path / "mcp-process-registry"),
    )
    source_bytes = _write_fixture(root)

    identity, _identity_directory = ensure_repository_identity(root)
    assert read_repository_identity(root) == identity
    assert identity.root_path == str(root)
    assert identity.repo_id.startswith("ctx_")
    _assert_no_live_endpoint(root)

    effective_filters = copy.deepcopy(facade._analysis_filters(str(root), None))
    excluded_paths, ignored_directories = effective_filters
    normalized_excludes = {
        str(item).replace("\\", "/").strip("/")
        for item in excluded_paths
    }
    for relative in source_bytes:
        normalized = relative.replace("\\", "/").strip("/")
        assert normalized not in normalized_excludes
        assert not any(
            normalized.startswith(excluded + "/")
            for excluded in normalized_excludes
        )
        first_component = normalized.split("/", 1)[0]
        assert first_component not in ignored_directories

    initial_source_bytes = copy.deepcopy(source_bytes)
    desktop_execution = _capture_gui_full_run(root, monkeypatch)
    _assert_source_bytes(root, initial_source_bytes)
    _assert_no_live_endpoint(root)
    desktop_capture = _capture_snapshot(
        root,
        expected_writer="desktop",
        expected_repo_id=identity.repo_id,
        source_bytes=initial_source_bytes,
    )
    desktop_projection_before_mcp = _state_projection(desktop_capture.state)

    assert facade._analysis_filters(str(root), None) == effective_filters
    _assert_no_live_endpoint(root)
    mcp_execution = _run_real_mcp_project_job(root)
    _assert_source_bytes(root, initial_source_bytes)
    _assert_no_live_endpoint(root)
    assert read_repository_identity(root) == identity
    assert facade._analysis_filters(str(root), None) == effective_filters
    mcp_capture = _capture_snapshot(
        root,
        expected_writer="mcp",
        expected_repo_id=identity.repo_id,
        source_bytes=initial_source_bytes,
    )

    assert mcp_capture.metadata.revision == desktop_capture.metadata.revision + 1
    assert mcp_capture.metadata.root_path == desktop_capture.metadata.root_path == str(root)
    assert mcp_capture.metadata.repo_id == desktop_capture.metadata.repo_id == identity.repo_id
    assert mcp_capture.metadata.schema_version == desktop_capture.metadata.schema_version
    assert mcp_capture.metadata.writer == "mcp"
    assert desktop_capture.metadata.writer == "desktop"
    assert mcp_capture.state.state_id == mcp_capture.metadata.state_id
    assert desktop_capture.state.state_id == desktop_capture.metadata.state_id
    assert mcp_capture.state.revision == mcp_capture.metadata.revision
    assert desktop_capture.state.revision == desktop_capture.metadata.revision
    assert getattr(mcp_capture.state, "provenance", None) == "snapshot"
    assert getattr(desktop_capture.state, "provenance", None) == "snapshot"
    assert getattr(mcp_capture.state, "resync_required", False) is not True
    assert getattr(desktop_capture.state, "resync_required", False) is not True

    desktop_projection_after_mcp = _state_projection(desktop_capture.state)
    mutation = _first_difference(
        desktop_projection_before_mcp,
        desktop_projection_after_mcp,
        "desktop_captured_state",
    )
    if mutation is not None:
        field_path, before, after = mutation
        evidence_dir = _preserve_mismatch_evidence(tmp_path, desktop_capture, mcp_capture)
        pytest.fail(
            "MCP run mutated the independently captured Desktop state: "
            f"field={field_path}; before={_short_repr(before)}; "
            f"after={_short_repr(after)}; evidence={evidence_dir}",
            pytrace=False,
        )

    try:
        desktop_projection = _state_projection(
            desktop_capture.state,
            normalize_report_timestamps=True,
        )
        mcp_projection = _state_projection(
            mcp_capture.state,
            normalize_report_timestamps=True,
        )
    except _UnsupportedCanonicalValue as exc:
        evidence_dir = _preserve_mismatch_evidence(tmp_path, desktop_capture, mcp_capture)
        pytest.fail(
            f"Canonical comparator stopped at unsupported value {exc}; "
            f"evidence={evidence_dir}",
            pytrace=False,
        )

    difference = _first_difference(desktop_projection, mcp_projection)
    if difference is not None:
        field_path, desktop_value, mcp_value = difference
        evidence_dir = _preserve_mismatch_evidence(tmp_path, desktop_capture, mcp_capture)
        pytest.fail(
            "Desktop/MCP canonical state mismatch: "
            f"first_field={field_path}; "
            f"desktop={_short_repr(desktop_value)}; "
            f"mcp={_short_repr(mcp_value)}; evidence={evidence_dir}",
            pytrace=False,
        )

    _assert_file_state_parity(desktop_capture, mcp_capture)
    assert desktop_capture.source_bytes == mcp_capture.source_bytes == initial_source_bytes
    assert desktop_execution["operation_name"] == "Repository analysis"
    assert desktop_execution["error_count"] == 0
    assert mcp_execution["completed"]["status"] == "completed"

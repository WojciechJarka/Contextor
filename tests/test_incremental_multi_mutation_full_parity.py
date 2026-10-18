"""Direct incremental mutation parity against a fresh FULL analysis."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

import pytest

from contextor.core.analysis.state_manager import (
    FileStateManager,
    RepositoryAnalysisState,
    load_engine_state,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.live_state.store import read_metadata
from contextor.core.paths import repo_cache_dir
from test_desktop_mcp_canonical_parity import (
    _assert_incremental_full_cycle_parity,
    _first_difference,
    _state_projection,
)


_COMMON_FIXTURE = {
    "alpha/__init__.py": b"",
    "alpha/api.py": b"def api_function():\n    return 1\n",
    "beta/__init__.py": b"",
    "beta/consumer.py": (
        b"from alpha.api import api_function\n"
        b"CONSUMER_RESULT = api_function()\n"
    ),
    "loose.py": b"LOOSE_VALUE = 0\n",
}

_REEXPORT_FIXTURE = {
    "alpha/__init__.py": b"from .api import api_function\n",
    "alpha/api.py": b"def api_function():\n    return 1\n",
    "beta/__init__.py": b"",
    "beta/consumer.py": (
        b"from alpha import api_function\n"
        b"CONSUMER_RESULT = api_function()\n"
    ),
    "loose.py": b"LOOSE_VALUE = 0\n",
}


def _write_sources(root: Path, sources: dict[str, bytes]) -> None:
    for relative, content in sources.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def _source_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*.py"))
    }


def _source_hashes(sources: dict[str, bytes]) -> dict[str, str]:
    return {
        relative: hashlib.sha256(content).hexdigest()
        for relative, content in sorted(sources.items())
    }


def _run_full_and_load(root: Path):
    errors, _result = ContextorFacade.analyze_project(str(root))
    assert not errors, f"FULL validation failed for isolated fixture {root}: {errors!r}"

    cache_dir = repo_cache_dir(root)
    metadata = read_metadata(cache_dir)
    assert metadata is not None, f"FULL did not persist snapshot metadata for {root}"
    state = load_engine_state(
        str(cache_dir),
        metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=str(root.resolve()),
    )
    assert isinstance(state, RepositoryAnalysisState)
    assert state.state_id == metadata.state_id
    assert state.revision == metadata.revision
    manager = FileStateManager(str(cache_dir))
    return state, manager._state.copy(), metadata


def _file_state_coverage(root: Path, file_states: dict[str, Any]) -> dict:
    source_paths = {
        str(path.resolve()): path
        for path in root.rglob("*.py")
    }
    tracked_paths = set(file_states)
    missing = sorted(set(source_paths) - tracked_paths)
    extra = sorted(tracked_paths - set(source_paths))
    digest_mismatches = []
    for absolute_path in sorted(set(source_paths) & tracked_paths):
        expected = hashlib.sha256(source_paths[absolute_path].read_bytes()).hexdigest()
        actual = getattr(file_states[absolute_path], "sha256", None)
        if actual != expected:
            digest_mismatches.append(
                {"path": absolute_path, "expected_sha256": expected, "actual_sha256": actual}
            )
    return {
        "expected_source_count": len(source_paths),
        "tracked_path_count": len(tracked_paths),
        "missing_paths": missing,
        "extra_paths": extra,
        "sha256_mismatches": digest_mismatches,
    }


def _freshness_markers(state: RepositoryAnalysisState) -> dict:
    values = vars(state)
    return {
        key: copy.deepcopy(value)
        for key, value in values.items()
        if key.endswith("_state") or key in {"module_parse_freshness", "resync_required"}
    }


def _capture_payload(
    *,
    state: RepositoryAnalysisState,
    file_states: dict[str, Any],
    metadata: Any,
    source_bytes: dict[str, bytes],
    root: Path,
) -> dict:
    return {
        "state": copy.deepcopy(state),
        "file_states": copy.deepcopy(file_states),
        "metadata": copy.deepcopy(metadata),
        "source_bytes": dict(source_bytes),
        "cache_dir": str(repo_cache_dir(root)),
        "root": str(root.resolve()),
    }


def _preserve_mismatch(
    tmp_path: Path,
    *,
    scenario_id: str,
    expected_status: str,
    actual_status: str | None,
    update_exception: str | None,
    target_module_id: str,
    initial_payload: dict,
    incremental_payload: dict,
    full_payload: dict,
    state_difference: tuple | None,
    incremental_file_coverage: dict,
    full_file_coverage: dict,
    mismatch_kind: str,
) -> Path:
    evidence_dir = tmp_path / f"b0g2d7a_{scenario_id.lower()}_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("initial_full.pickle", initial_payload),
        ("incremental.pickle", incremental_payload),
        ("fresh_full.pickle", full_payload),
    ):
        with (evidence_dir / name).open("wb") as output:
            pickle.dump(payload, output, protocol=pickle.HIGHEST_PROTOCOL)

    source_bytes = incremental_payload["source_bytes"]
    summary = {
        "scenario_id": scenario_id,
        "mismatch_kind": mismatch_kind,
        "expected_update_status": expected_status,
        "actual_update_status": actual_status,
        "update_exception": update_exception,
        "target_module_id": target_module_id,
        "initial_module_ids": sorted(initial_payload["state"].modules),
        "incremental_module_ids": sorted(incremental_payload["state"].modules),
        "fresh_full_module_ids": sorted(full_payload["state"].modules),
        "family_freshness_markers": {
            "initial": _freshness_markers(initial_payload["state"]),
            "incremental": _freshness_markers(incremental_payload["state"]),
            "fresh_full": _freshness_markers(full_payload["state"]),
        },
        "incremental_file_state_coverage": incremental_file_coverage,
        "fresh_full_file_state_coverage": full_file_coverage,
        "first_structural_difference": state_difference,
        "source_bytes_base64": {
            relative: base64.b64encode(content).decode("ascii")
            for relative, content in sorted(source_bytes.items())
        },
        "source_sha256": _source_hashes(source_bytes),
        "snapshot_metadata": {
            "initial_full": repr(initial_payload["metadata"]),
            "fresh_full": repr(full_payload["metadata"]),
        },
    }
    (evidence_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=repr) + "\n",
        encoding="utf-8",
    )
    return evidence_dir


def _run_mutation_case(
    tmp_path: Path,
    *,
    scenario_id: str,
    fixture: dict[str, bytes],
    mutation_path: str,
    mutation_bytes: bytes | None,
    expected_status: str,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write_sources(root, fixture)

    initial_state, initial_file_states, initial_metadata = _run_full_and_load(root)
    hydrated = hydrate_repository_engine(root)
    assert hydrated is not None, f"Could not hydrate FULL baseline for {scenario_id}: {root}"
    engine = hydrated.engine
    assert engine.state.state_id == initial_metadata.state_id
    assert engine.state.revision == initial_metadata.revision
    assert _state_projection(engine.state) == _state_projection(initial_state)

    initial_file_states = copy.deepcopy(engine.state_manager._state)
    initial_state = engine.state
    initial_source_bytes = _source_bytes(root)
    initial_payload = _capture_payload(
        state=initial_state,
        file_states=initial_file_states,
        metadata=initial_metadata,
        source_bytes=initial_source_bytes,
        root=root,
    )
    initial_coverage = _file_state_coverage(root, initial_file_states)
    assert not initial_coverage["missing_paths"]
    assert not initial_coverage["extra_paths"]
    assert not initial_coverage["sha256_mismatches"]

    target = root / mutation_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if mutation_bytes is None:
        target.unlink()
    else:
        target.write_bytes(mutation_bytes)

    actual_status = None
    update_exception = None
    try:
        result = engine.update_file(str(target.resolve()))
        actual_status = result.status
    except Exception as exc:
        update_exception = f"{type(exc).__module__}.{type(exc).__qualname__}: {exc}"

    incremental_state = copy.deepcopy(engine.state)
    incremental_file_states = copy.deepcopy(engine.state_manager._state)
    incremental_source_bytes = _source_bytes(root)
    incremental_payload = _capture_payload(
        state=incremental_state,
        file_states=incremental_file_states,
        metadata=initial_metadata,
        source_bytes=incremental_source_bytes,
        root=root,
    )
    incremental_projection = _state_projection(
        incremental_state,
        normalize_report_timestamps=True,
    )
    incremental_coverage = _file_state_coverage(root, incremental_file_states)

    fresh_state, fresh_file_states, fresh_metadata = _run_full_and_load(root)
    assert _source_bytes(root) == incremental_source_bytes, (
        f"fixture source bytes changed during fresh FULL for {scenario_id}"
    )
    full_payload = _capture_payload(
        state=fresh_state,
        file_states=fresh_file_states,
        metadata=fresh_metadata,
        source_bytes=incremental_source_bytes,
        root=root,
    )
    fresh_projection = _state_projection(
        fresh_state,
        normalize_report_timestamps=True,
    )
    state_difference = _first_difference(incremental_projection, fresh_projection)
    parity_error = None
    try:
        _assert_incremental_full_cycle_parity(
            initial_payload["state"], incremental_state, fresh_state,
            expected_invalidation_reason=(
                "SOURCE_DELETED" if mutation_bytes is None else "SOURCE_CHANGED"
            ),
        )
    except AssertionError as exc:
        parity_error = str(exc)
    full_coverage = _file_state_coverage(root, fresh_file_states)

    mismatch_kind = None
    if update_exception is not None:
        mismatch_kind = "UPDATE_EXCEPTION"
    elif actual_status != expected_status:
        mismatch_kind = "UPDATE_STATUS"
    elif parity_error is not None:
        mismatch_kind = "CANONICAL_STATE"
    elif any(
        incremental_coverage[key]
        for key in ("missing_paths", "extra_paths", "sha256_mismatches")
    ):
        mismatch_kind = "INCREMENTAL_FILESTATE"
    elif any(
        full_coverage[key]
        for key in ("missing_paths", "extra_paths", "sha256_mismatches")
    ):
        mismatch_kind = "FULL_FILESTATE"

    if mismatch_kind is not None:
        target_module_id = ".".join(Path(mutation_path).with_suffix("").parts)
        evidence_dir = _preserve_mismatch(
            tmp_path,
            scenario_id=scenario_id,
            expected_status=expected_status,
            actual_status=actual_status,
            update_exception=update_exception,
            target_module_id=target_module_id,
            initial_payload=initial_payload,
            incremental_payload=incremental_payload,
            full_payload=full_payload,
            state_difference=state_difference,
            incremental_file_coverage=incremental_coverage,
            full_file_coverage=full_coverage,
            mismatch_kind=mismatch_kind,
        )
        pytest.fail(
            f"{scenario_id} {mismatch_kind}: expected_status={expected_status!r}; "
            f"actual_status={actual_status!r}; update_exception={update_exception!r}; "
            f"first_difference={state_difference!r}; "
            f"parity_error={parity_error!r}; "
            f"incremental_file_coverage={incremental_coverage!r}; "
            f"fresh_full_file_coverage={full_coverage!r}; evidence={evidence_dir}"
        )

    if scenario_id == "F":
        source_sha = hashlib.sha256(incremental_source_bytes["loose.py"]).hexdigest()
        baseline_sha = hashlib.sha256(initial_source_bytes["loose.py"]).hexdigest()
        assert actual_status == "UNCHANGED"
        assert source_sha != baseline_sha
        assert incremental_state.cycle_semantics_state == "stale"
        assert incremental_state.cycle_semantics_invalidation_reason == "SOURCE_CHANGED"
        tracked_path = str((root / "loose.py").resolve())
        assert incremental_file_states[tracked_path].sha256 == source_sha
        assert incremental_state.module_usages_manifest["loose"]["sha256"] == source_sha


def test_case_a_new_architectural_layer_matches_fresh_full(tmp_path):
    _run_mutation_case(
        tmp_path,
        scenario_id="A",
        fixture=_COMMON_FIXTURE,
        mutation_path="gamma/__init__.py",
        mutation_bytes=b"GAMMA_VALUE = 7\n",
        expected_status="UPDATED",
    )


def test_case_b_module_deletion_matches_fresh_full(tmp_path):
    _run_mutation_case(
        tmp_path,
        scenario_id="B",
        fixture=_COMMON_FIXTURE,
        mutation_path="beta/consumer.py",
        mutation_bytes=None,
        expected_status="DELETED",
    )


def test_case_c_consumer_usage_change_matches_fresh_full(tmp_path):
    _run_mutation_case(
        tmp_path,
        scenario_id="C",
        fixture=_COMMON_FIXTURE,
        mutation_path="beta/consumer.py",
        mutation_bytes=(
            b"from alpha.api import api_function\n"
            b"CONSUMER_RESULT = api_function()\n"
            b"SECOND_RESULT = api_function()\n"
        ),
        expected_status="UPDATED",
    )


def test_case_d_symbol_addition_matches_fresh_full(tmp_path):
    _run_mutation_case(
        tmp_path,
        scenario_id="D",
        fixture=_COMMON_FIXTURE,
        mutation_path="alpha/api.py",
        mutation_bytes=(
            b"def api_function():\n"
            b"    return 1\n"
            b"\n"
            b"def added_function():\n"
            b"    return 2\n"
        ),
        expected_status="UPDATED",
    )


def test_case_e_reexport_retarget_matches_fresh_full(tmp_path):
    _run_mutation_case(
        tmp_path,
        scenario_id="E",
        fixture=_REEXPORT_FIXTURE,
        mutation_path="alpha/__init__.py",
        mutation_bytes=b"api_function = 7\n",
        expected_status="UPDATED",
    )


def test_case_f_semantic_noop_matches_fresh_full(tmp_path):
    _run_mutation_case(
        tmp_path,
        scenario_id="F",
        fixture=_COMMON_FIXTURE,
        mutation_path="loose.py",
        mutation_bytes=(
            b"LOOSE_VALUE = 0\n"
            b"# appended nonsemantic comment\n"
        ),
        expected_status="UNCHANGED",
    )

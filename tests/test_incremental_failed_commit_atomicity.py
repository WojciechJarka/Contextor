"""Direct incremental-engine failure atomicity regression gate."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.live_state.store import read_metadata
from contextor.core.paths import repo_cache_dir
from contextor.core.reporting_engine import debt
from test_desktop_mcp_canonical_parity import _first_difference, _project, _state_projection


_SOURCES = {
    "provider.py": "PROVIDER_VALUE = 1\n",
    "consumer.py": "from provider import PROVIDER_VALUE\nCONSUMED_VALUE = PROVIDER_VALUE\n",
}

_GRAPH_SOURCES = {
    "pkg/__init__.py": "",
    "pkg/child.py": "VALUE = 1\n",
    "consumer.py": "from pkg import child\nCONSUMED_VALUE = child.VALUE\n",
    "unrelated.py": "UNRELATED_VALUE = 2\n",
}


def _source_fingerprints(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*.py"))
    }


@dataclass
class _Baseline:
    root: Path
    engine: Any
    state_object: Any
    state_projection: dict
    file_states: dict
    manifest: dict
    registry_checkpoint: dict
    metadata: Any
    source_fingerprints: dict[str, str]


def _real_baseline(tmp_path: Path, sources: dict[str, str]) -> _Baseline:
    root = tmp_path / "repo"
    root.mkdir()
    for relative_path, content in sources.items():
        source_path = root / relative_path
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(content, encoding="utf-8")

    errors, _ = ContextorFacade.analyze_project(str(root))
    assert not errors, errors
    hydrated = hydrate_repository_engine(root)
    assert hydrated is not None
    engine = hydrated.engine
    metadata = read_metadata(repo_cache_dir(root))
    assert metadata is not None
    assert metadata.state_id == engine.state.state_id
    assert metadata.revision == engine.state.revision

    return _Baseline(
        root=root,
        engine=engine,
        state_object=engine.state,
        state_projection=_state_projection(engine.state),
        file_states=deepcopy(engine.state_manager._state),
        manifest=deepcopy(engine.state.module_usages_manifest),
        registry_checkpoint=engine.registry.create_checkpoint(),
        metadata=metadata,
        source_fingerprints=_source_fingerprints(root),
    )


def _difference(before: Any, after: Any, path: str) -> tuple | None:
    return _first_difference(_project(before, path), _project(after, path), path)


def _assert_failed_update_atomic(baseline: _Baseline, case: str, acknowledgement_calls: int) -> None:
    engine = baseline.engine
    state_difference = _first_difference(
        baseline.state_projection,
        _state_projection(engine.state),
    )
    file_state_difference = _difference(
        baseline.file_states,
        engine.state_manager._state,
        "FileStateManager._state",
    )
    manifest_difference = _difference(
        baseline.manifest,
        engine.state.module_usages_manifest,
        "module_usages_manifest",
    )
    registry_difference = _difference(
        baseline.registry_checkpoint,
        engine.registry.create_checkpoint(),
        "PersistentIdentityRegistry",
    )
    metadata_after = read_metadata(repo_cache_dir(baseline.root))
    metadata_difference = _difference(
        baseline.metadata,
        metadata_after,
        "persisted_generation_metadata",
    )
    evidence = {
        "case": case,
        "canonical_state_object_same": engine.state is baseline.state_object,
        "canonical_state_first_difference": state_difference,
        "file_state_first_difference": file_state_difference,
        "manifest_first_difference": manifest_difference,
        "registry_first_difference": registry_difference,
        "persisted_generation_first_difference": metadata_difference,
        "file_state_acknowledgement_calls": acknowledgement_calls,
        "source_fingerprints_before": baseline.source_fingerprints,
        "source_fingerprints_after": _source_fingerprints(baseline.root),
    }
    print(f"{case}_ATOMICITY_EVIDENCE={evidence!r}")
    assert engine.state is baseline.state_object, evidence
    assert state_difference is None, evidence
    assert file_state_difference is None, evidence
    assert manifest_difference is None, evidence
    assert registry_difference is None, evidence
    assert metadata_difference is None, evidence


def test_failed_updated_before_file_state_acknowledgement_is_atomic(tmp_path, monkeypatch):
    baseline = _real_baseline(tmp_path, _SOURCES)
    source = baseline.root / "provider.py"
    source.write_text("PROVIDER_VALUE = 1\nNEW_OWN_SYMBOL = 2\n", encoding="utf-8")
    calls = []

    def fail_before_acknowledgement(file_path):
        calls.append(file_path)
        raise RuntimeError("injected FileState acknowledgement failure")

    monkeypatch.setattr(baseline.engine.state_manager, "update_state", fail_before_acknowledgement)
    with pytest.raises(RuntimeError, match="injected FileState acknowledgement failure"):
        baseline.engine.update_file(str(source))
    assert calls == [str(source)]
    _assert_failed_update_atomic(baseline, "CASE_A", len(calls))


def test_failed_updated_missing_trusted_hash_is_atomic(tmp_path, monkeypatch):
    baseline = _real_baseline(tmp_path, _SOURCES)
    source = baseline.root / "provider.py"
    source.write_text("PROVIDER_VALUE = 1\nNEW_OWN_SYMBOL = 2\n", encoding="utf-8")
    update_state = baseline.engine.state_manager.update_state
    acknowledgements = []

    def acknowledge_then_continue(file_path):
        result = update_state(file_path)
        acknowledgements.append(file_path)
        return result

    monkeypatch.setattr(baseline.engine.state_manager, "update_state", acknowledge_then_continue)
    monkeypatch.setattr(baseline.engine.state_manager, "get_tracked_sha256", lambda file_path: "")
    with pytest.raises(RuntimeError, match="Missing trusted source SHA-256"):
        baseline.engine.update_file(str(source))
    assert acknowledgements == [str(source)]
    _assert_failed_update_atomic(baseline, "CASE_B", len(acknowledgements))


def test_failed_semantic_noop_acknowledgement_is_atomic(tmp_path, monkeypatch):
    baseline = _real_baseline(tmp_path, _SOURCES)
    source = baseline.root / "provider.py"
    source.write_text("# comment-only change\nPROVIDER_VALUE = 1\n", encoding="utf-8")
    update_state = baseline.engine.state_manager.update_state
    acknowledgements = []

    def acknowledge_then_continue(file_path):
        result = update_state(file_path)
        acknowledgements.append(file_path)
        return result

    monkeypatch.setattr(baseline.engine.state_manager, "update_state", acknowledge_then_continue)
    monkeypatch.setattr(baseline.engine.state_manager, "get_tracked_sha256", lambda file_path: "")
    with pytest.raises(RuntimeError, match="Missing trusted source SHA-256"):
        baseline.engine.update_file(str(source))
    assert acknowledgements == [str(source)]
    _assert_failed_update_atomic(baseline, "CASE_C", len(acknowledgements))


def test_failed_candidate_report_before_publication_is_atomic(tmp_path, monkeypatch):
    baseline = _real_baseline(tmp_path, _GRAPH_SOURCES)
    source = baseline.root / "pkg" / "__init__.py"
    source.write_text("child = 123\n", encoding="utf-8")
    update_state = baseline.engine.state_manager.update_state
    acknowledgements = []
    report_calls = []

    def observe_acknowledgement(file_path):
        acknowledgements.append(file_path)
        return update_state(file_path)

    def fail_candidate_report(*args, **kwargs):
        report_calls.append((args, kwargs))
        raise RuntimeError("injected RAM-only derived-report failure")

    monkeypatch.setattr(baseline.engine.state_manager, "update_state", observe_acknowledgement)
    monkeypatch.setattr(debt, "compute_debt", fail_candidate_report)
    with pytest.raises(RuntimeError, match="injected RAM-only derived-report failure"):
        baseline.engine.update_file(str(source))
    assert report_calls, "The candidate derived-report boundary was not reached"
    assert not acknowledgements, "FileState acknowledgement preceded candidate report failure"
    _assert_failed_update_atomic(baseline, "CASE_D", len(acknowledgements))

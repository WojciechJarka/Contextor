"""P1D2F: explicit FULL opt-in prepares evidence without publication."""

from __future__ import annotations

import pytest

import contextor.core.api.facade as facade_module
from contextor.core.analysis.state_manager import (
    load_engine_state,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.store import read_metadata
from contextor.core.paths import repo_cache_dir


@pytest.fixture(autouse=True)
def _inline_index(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _flat_repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_bytes(
        b"import b\nimport helper\nvalue = 1\n"
    )
    (root / "b.py").write_bytes(
        b"import a\nvalue = 2\n"
    )
    (root / "helper.py").write_bytes(
        b"value = 3\n"
    )
    (root / "unrelated.py").write_bytes(
        b"value = 999\n"
    )
    return root


def _package_repo(tmp_path):
    root = tmp_path / "repo"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_bytes(b"")
    (pkg / "a.py").write_bytes(
        b"import pkg.b\n"
        b"@unknown_decorator\n"
        b"def fa():\n"
        b"    return 1\n"
    )
    (pkg / "b.py").write_bytes(
        b"import pkg.a\n"
        b"def fb():\n"
        b"    return 2\n"
    )
    return root


def _full(root, *, preview=False):
    errors, result = ContextorFacade.analyze_project(
        str(root),
        cycle_source_preparation_preview=preview,
    )
    assert result is not None
    return errors, result


def _stored(root):
    cache = repo_cache_dir(root)
    metadata = read_metadata(cache)
    assert metadata is not None
    state = load_engine_state(
        str(cache),
        metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=str(root.resolve()),
    )
    assert state is not None
    return state


def test_p1d2f_t01_default_no_preview_no_second_index(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)
    original = facade_module.index_repository
    selections = []

    def observed(*args, **kwargs):
        selections.append(kwargs.get("source_capture_module_ids"))
        return original(*args, **kwargs)

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        observed,
    )

    _, result = ContextorFacade.analyze_project(str(root))

    assert result is not None
    assert selections == [None]
    assert not hasattr(
        result,
        "cycle_source_preparation_preview",
    )

    state = _stored(root)
    assert state.cycle_source_publication is None


def test_p1d2f_t02_flat_full_optin_prepared_only(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)
    original = facade_module.index_repository
    selections = []

    def observed(*args, **kwargs):
        selections.append(kwargs.get("source_capture_module_ids"))
        return original(*args, **kwargs)

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        observed,
    )

    _, result = _full(root, preview=True)

    assert len(selections) == 2
    assert selections[0] is None
    assert selections[1] == frozenset({
        "a", "b", "helper",
    })

    prepared = result.cycle_source_preparation_preview

    assert prepared.status == (
        "PREPARED_UNPUBLISHED_NON_ATOMIC"
    )
    assert prepared.reason is None
    assert prepared.source_modules == (
        "a", "b", "helper",
    )
    assert prepared.manifest is not None
    assert prepared.manifest.source_manifest_sha256 is not None
    assert prepared.manifest.authority == (
        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
    )
    assert prepared.manifest.components[0].members == (
        "a", "b",
    )

    assert (
        "cycle_source_preparation_preview"
        not in result.summary_data
    )

    state = _stored(root)
    assert state.cycle_source_publication is None
    assert state.cycle_semantics_state == "fresh"
    assert not hasattr(
        state,
        "cycle_source_preparation_preview",
    )


def test_p1d2f_t03_unsupported_package_full_fails_closed(
    tmp_path, isolated_dirs,
):
    root = _package_repo(tmp_path)
    _, result = _full(root, preview=True)

    prepared = result.cycle_source_preparation_preview

    assert prepared.status == "UNAVAILABLE"
    assert prepared.reason == (
        "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
    )
    assert prepared.manifest is None
    assert prepared.source_modules == ()

    state = _stored(root)
    assert state.cycle_source_publication is None
    assert state.cycle_semantics_state == "fresh"


def test_p1d2f_t04_no_cycles_skips_second_index(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)

    (root / "b.py").write_bytes(
        b"value = 2\n"
    )

    original = facade_module.index_repository
    selections = []

    def observed(*args, **kwargs):
        selections.append(kwargs.get("source_capture_module_ids"))
        return original(*args, **kwargs)

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        observed,
    )

    _, result = _full(root, preview=True)

    prepared = result.cycle_source_preparation_preview

    assert selections == [None]
    assert prepared.status == "UNAVAILABLE"
    assert prepared.reason == "PLAN_NO_CYCLIC_COMPONENTS"
    assert prepared.manifest is None

    state = _stored(root)
    assert state.cycle_source_publication is None


def test_p1d2f_t05_second_pass_source_drift_rejected(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)
    original = facade_module.index_repository

    def drifted(*args, **kwargs):
        if kwargs.get("source_capture_module_ids") is not None:
            (root / "helper.py").write_bytes(
                b"value = 300\n"
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        drifted,
    )

    _, result = _full(root, preview=True)

    prepared = result.cycle_source_preparation_preview

    assert prepared.status == "UNAVAILABLE"
    assert prepared.reason == (
        "VERIFY_REINDEX_SOURCE_CHANGED"
    )
    assert prepared.manifest is None
    assert prepared.source_modules == ()

    state = _stored(root)
    assert state.cycle_source_publication is None


def test_p1d2f_t06_second_pass_exception_fails_closed(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)
    original = facade_module.index_repository

    def failed(*args, **kwargs):
        if kwargs.get("source_capture_module_ids") is not None:
            raise RuntimeError("injected preview failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        failed,
    )

    _, result = _full(root, preview=True)

    prepared = result.cycle_source_preparation_preview

    assert prepared.status == "UNAVAILABLE"
    assert prepared.reason == (
        "PREVIEW_EXECUTION_ERROR:RuntimeError"
    )
    assert prepared.manifest is None

    state = _stored(root)
    assert state.cycle_source_publication is None


def test_p1d2f_t07_invalid_optin_argument_rejected(
    tmp_path, isolated_dirs,
):
    root = _flat_repo(tmp_path)

    for invalid in (None, 0, 1, "yes", [], {}):
        with pytest.raises(ValueError):
            ContextorFacade.analyze_project(
                str(root),
                cycle_source_preparation_preview=invalid,
            )


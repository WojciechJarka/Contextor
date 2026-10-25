"""P1D2G: complete semantic evidence gates FULL preview reindexing."""

from __future__ import annotations

from dataclasses import replace

import pytest

import contextor.core.api.facade as facade_module
import contextor.core.cycle_semantics.materialization as materialization_module

from contextor.core.analysis.process_pool_lifecycle import (
    terminate_active_process_pools,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.cycle_semantics.lifecycle import (
    classify_full_cycle_semantics,
)
from contextor.core.errors import AnalysisCancelled
from tests.test_original_worker_full_preparation_optin import (
    _flat_repo,
    _full,
    _stored,
)


@pytest.fixture(autouse=True)
def _inline_by_default(monkeypatch):
    monkeypatch.setenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL",
        "1",
    )


def test_p1d2g_t01_partial_but_fresh_skips_second_index(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)

    original_materialize = (
        materialization_module.materialize_cycle_semantics
    )
    original_index = facade_module.index_repository
    selections = []

    def partial_materialization(*args, **kwargs):
        snapshot = original_materialize(*args, **kwargs)

        assert snapshot.cyclic_modules == ("a", "b")

        partial = replace(
            snapshot,
            observed_source_fingerprints=(
                snapshot.observed_source_fingerprints[1:]
            ),
            source_issues=(
                ("a", "SOURCE_FILE_LIMIT"),
            ),
            coverage_status="PARTIAL_SOURCE_EVIDENCE",
        )

        assert classify_full_cycle_semantics(partial) == (
            "fresh",
            None,
        )

        return partial

    def observed_index(*args, **kwargs):
        selections.append(
            kwargs.get("source_capture_module_ids")
        )
        return original_index(*args, **kwargs)

    monkeypatch.setattr(
        materialization_module,
        "materialize_cycle_semantics",
        partial_materialization,
    )
    monkeypatch.setattr(
        facade_module,
        "index_repository",
        observed_index,
    )

    _, result = _full(root, preview=True)

    assert selections == [None]

    preview = result.cycle_source_preparation_preview

    assert preview.status == "UNAVAILABLE"
    assert preview.reason == (
        "CYCLE_SOURCE_EVIDENCE_INCOMPLETE"
    )
    assert preview.manifest is None
    assert preview.source_modules == ()

    state = _stored(root)

    assert state.cycle_semantics_state == "fresh"
    assert state.cycle_semantics is not None
    assert state.cycle_semantics.coverage_status == (
        "PARTIAL_SOURCE_EVIDENCE"
    )
    assert state.cycle_source_publication is None


def test_p1d2g_t02_deferred_semantics_skips_second_index(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)

    original_index = facade_module.index_repository
    selections = []

    def failed_materialization(*args, **kwargs):
        raise ValueError("synthetic semantic unavailability")

    def observed_index(*args, **kwargs):
        selections.append(
            kwargs.get("source_capture_module_ids")
        )
        return original_index(*args, **kwargs)

    monkeypatch.setattr(
        materialization_module,
        "materialize_cycle_semantics",
        failed_materialization,
    )
    monkeypatch.setattr(
        facade_module,
        "index_repository",
        observed_index,
    )

    _, result = _full(root, preview=True)

    assert selections == [None]

    preview = result.cycle_source_preparation_preview

    assert preview.status == "UNAVAILABLE"
    assert preview.reason == "CYCLE_SEMANTICS_NOT_FRESH"
    assert preview.manifest is None

    state = _stored(root)

    assert state.cycle_semantics is None
    assert state.cycle_semantics_state == "deferred"
    assert state.cycle_source_publication is None


def test_p1d2g_t03_second_pass_cancellation_propagates(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)

    original_index = facade_module.index_repository
    selections = []

    def cancelled_index(*args, **kwargs):
        selection = kwargs.get("source_capture_module_ids")
        selections.append(selection)

        if selection is not None:
            raise AnalysisCancelled()

        return original_index(*args, **kwargs)

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        cancelled_index,
    )

    with pytest.raises(AnalysisCancelled):
        _full(root, preview=True)

    assert selections == [
        None,
        frozenset({"a", "b", "helper"}),
    ]


def test_p1d2g_t04_real_process_pool_full_preview(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)

    monkeypatch.delenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL",
        raising=False,
    )

    terminate_active_process_pools(timeout=1.0)

    try:
        _, result = _full(root, preview=True)

        preview = result.cycle_source_preparation_preview

        assert preview.status == (
            "PREPARED_UNPUBLISHED_NON_ATOMIC"
        )
        assert preview.reason is None
        assert preview.manifest is not None
        assert preview.manifest.authority == (
            "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
        )
        assert preview.source_modules == (
            "a",
            "b",
            "helper",
        )

        state = _stored(root)

        assert state.cycle_semantics_state == "fresh"
        assert state.cycle_source_publication is None
        assert not hasattr(
            state,
            "cycle_source_preparation_preview",
        )

    finally:
        terminate_active_process_pools(timeout=1.0)


def test_p1d2g_t05_oversized_closure_skips_second_index(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _flat_repo(tmp_path)

    imports = [
        b"import b",
        b"import helper",
    ]

    for number in range(14):
        module_id = f"x{number}"

        (root / f"{module_id}.py").write_bytes(
            b"value = 1\n"
        )
        imports.append(
            f"import {module_id}".encode("ascii")
        )

    (root / "a.py").write_bytes(
        b"\n".join(imports) + b"\nvalue = 1\n"
    )

    original_index = facade_module.index_repository
    selections = []

    def observed_index(*args, **kwargs):
        selections.append(
            kwargs.get("source_capture_module_ids")
        )
        return original_index(*args, **kwargs)

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        observed_index,
    )

    _, result = _full(root, preview=True)

    preview = result.cycle_source_preparation_preview

    assert selections == [None]
    assert preview.status == "UNAVAILABLE"
    assert preview.reason == "PLAN_CLOSURE_MODULE_LIMIT"
    assert preview.manifest is None
    assert preview.source_modules == ()

    state = _stored(root)

    assert state.cycle_source_publication is None


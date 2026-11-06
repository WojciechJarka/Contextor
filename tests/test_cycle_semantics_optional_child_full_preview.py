"""P1D3D: official optional FULL preview is unpublished."""

from dataclasses import replace

import pytest

import contextor.core.api.facade as facade_module

from contextor.core.api.facade import ContextorFacade
from contextor.core.cycle_semantics.generation_manifest import (
    OPTIONAL_MANIFEST_VERSION,
)
from tests.cycle_semantics_lab import write_synthetic_repository
from tests.test_cycle_semantics_optional_child_worker_capture import (
    FILES,
)
from tests.test_original_worker_full_receipt_optin import (
    _persisted,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _repo(tmp_path, files=None):
    return write_synthetic_repository(
        tmp_path / "repo",
        FILES if files is None else files,
    )


def _run(root, **kwargs):
    errors, result = ContextorFacade.analyze_project(
        str(root), **kwargs
    )
    assert isinstance(errors, list)
    assert result is not None
    return result


def test_optional_full_preview_original_worker_manifest(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    original = facade_module.index_repository
    selections = []

    def tracked(*args, **kwargs):
        selections.append(
            kwargs.get("source_capture_module_ids")
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        facade_module, "index_repository", tracked
    )

    result = _run(
        root,
        cycle_source_preparation_preview=True,
        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
    )

    preview = result.cycle_source_preparation_preview

    assert preview.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert preview.reason is None
    assert preview.source_selection == "OPTIONAL_NAMED_CHILDREN"
    assert preview.manifest is not None
    assert preview.manifest.version == OPTIONAL_MANIFEST_VERSION
    assert preview.manifest.source_selection == (
        "OPTIONAL_NAMED_CHILDREN"
    )
    assert "pkg.child" in preview.source_modules
    assert selections == [
        None,
        frozenset(preview.source_modules),
    ]

    state, metadata = _persisted(root)

    assert metadata.revision >= 1
    assert "pkg.child" not in (
        state.dependency_graph.hard_edges["pkg.a"]
    )
    assert state.cycle_source_publication is None
    assert state.cycle_partial_source_publication is None
    assert not hasattr(
        state, "cycle_source_preparation_preview"
    )


@pytest.mark.parametrize(
    "value",
    [None, 0, True, "INVALID", []],
)
def test_invalid_source_selection_precedes_index(
    tmp_path, isolated_dirs, monkeypatch, value,
):
    root = _repo(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("index must not start")

    monkeypatch.setattr(
        facade_module, "index_repository", forbidden
    )

    with pytest.raises(
        ValueError, match="cycle_source_selection"
    ):
        ContextorFacade.analyze_project(
            str(root),
            cycle_source_preparation_preview=True,
            cycle_source_selection=value,
        )


def test_optional_mode_requires_preview(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("index must not start")

    monkeypatch.setattr(
        facade_module, "index_repository", forbidden
    )

    with pytest.raises(
        ValueError, match="requires.*preview"
    ):
        ContextorFacade.analyze_project(
            str(root),
            cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
        )


@pytest.mark.parametrize(
    "publication_arg",
    [
        "cycle_source_publication_opt_in",
        "cycle_partial_source_publication_opt_in",
    ],
)
def test_optional_publication_rejected_before_index(
    tmp_path, isolated_dirs, monkeypatch, publication_arg,
):
    root = _repo(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("index must not start")

    monkeypatch.setattr(
        facade_module, "index_repository", forbidden
    )

    with pytest.raises(
        ValueError, match="publication unsupported"
    ):
        ContextorFacade.analyze_project(
            str(root),
            cycle_source_preparation_preview=True,
            cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
            **{publication_arg: True},
        )


def test_optional_no_cycles_skips_second_index(
    tmp_path, isolated_dirs, monkeypatch,
):
    files = {
        **FILES,
        "pkg/b.py": "value = 1\n",
    }
    root = _repo(tmp_path, files)
    original = facade_module.index_repository
    selections = []

    def tracked(*args, **kwargs):
        selections.append(
            kwargs.get("source_capture_module_ids")
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        facade_module, "index_repository", tracked
    )

    result = _run(
        root,
        cycle_source_preparation_preview=True,
        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
    )

    preview = result.cycle_source_preparation_preview

    assert preview.status == "UNAVAILABLE"
    assert preview.reason == "PLAN_NO_CYCLIC_COMPONENTS"
    assert preview.manifest is None
    assert preview.source_selection == "OPTIONAL_NAMED_CHILDREN"
    assert selections == [None]


def test_optional_source_drift_fails_closed(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    original = facade_module.index_repository

    def drifted(*args, **kwargs):
        if kwargs.get("source_capture_module_ids") is not None:
            (root / "pkg" / "child.py").write_bytes(
                b"import pkg.helper\n# source drift\n"
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        facade_module, "index_repository", drifted
    )

    result = _run(
        root,
        cycle_source_preparation_preview=True,
        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
    )

    preview = result.cycle_source_preparation_preview

    assert preview.status == "UNAVAILABLE"
    assert preview.reason == "VERIFY_REINDEX_SOURCE_CHANGED"
    assert preview.manifest is None
    assert preview.source_selection == "OPTIONAL_NAMED_CHILDREN"

    state, _ = _persisted(root)
    assert state.cycle_source_publication is None
    assert state.cycle_partial_source_publication is None


def test_optional_import_graph_drift_fails_closed(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    original = facade_module.index_repository

    def drifted(*args, **kwargs):
        if kwargs.get("source_capture_module_ids") is not None:
            (root / "pkg" / "child.py").write_bytes(
                b"changed = True\n"
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        facade_module, "index_repository", drifted
    )

    result = _run(
        root,
        cycle_source_preparation_preview=True,
        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
    )

    preview = result.cycle_source_preparation_preview

    assert preview.status == "UNAVAILABLE"
    assert preview.reason == "VERIFY_REINDEX_GRAPH_CHANGED"
    assert preview.manifest is None
    assert preview.source_selection == "OPTIONAL_NAMED_CHILDREN"

    state, _ = _persisted(root)
    assert state.cycle_source_publication is None
    assert state.cycle_partial_source_publication is None


def test_legacy_default_source_selection_unchanged(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)

    result = _run(
        root,
        cycle_source_preparation_preview=True,
    )

    preview = result.cycle_source_preparation_preview

    assert preview.source_selection == "HARD_ONLY"
    assert (
        preview.manifest is None
        or preview.manifest.source_selection == "HARD_ONLY"
    )

    state, _ = _persisted(root)
    assert state.cycle_source_publication is None
    assert state.cycle_partial_source_publication is None

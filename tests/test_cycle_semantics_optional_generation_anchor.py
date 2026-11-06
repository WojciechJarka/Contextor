"""P1D3F1: optional generation labels remain ephemeral."""

from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.cycle_semantics.optional_generation_anchor import (
    OPTIONAL_GENERATION_ANCHOR_AUTHORITY,
    OPTIONAL_GENERATION_ANCHOR_VERSION,
    OptionalPreparedGenerationAnchor,
    make_optional_prepared_generation_anchor,
)
from tests.test_cycle_semantics_optional_child_full_preview import (
    _repo,
    _run,
)
from tests.test_original_worker_full_receipt_optin import (
    _persisted,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _optional(root):
    return _run(
        root,
        cycle_source_preparation_preview=True,
        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
    )


def test_official_full_returns_post_save_generation_anchor(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    result = _optional(root)
    preview = result.cycle_source_preparation_preview
    anchor = result.cycle_source_preparation_generation_anchor
    state, metadata = _persisted(root)

    assert type(anchor) is OptionalPreparedGenerationAnchor
    assert anchor.version == OPTIONAL_GENERATION_ANCHOR_VERSION
    assert anchor.authority == OPTIONAL_GENERATION_ANCHOR_AUTHORITY

    assert (
        anchor.revision,
        anchor.state_id,
        anchor.repo_id,
        anchor.root_path,
    ) == (
        metadata.revision,
        metadata.state_id,
        metadata.repo_id,
        metadata.root_path,
    )

    assert anchor.graph_sha256 == preview.manifest.graph_sha256
    assert anchor.source_manifest_sha256 == (
        preview.manifest.source_manifest_sha256
    )
    assert anchor.graph_sha256 == state.cycle_semantics.graph_sha256

    assert anchor == make_optional_prepared_generation_anchor(
        preview, metadata
    )

    assert state.cycle_source_publication is None
    assert state.cycle_partial_source_publication is None
    assert not hasattr(
        state, "cycle_source_preparation_generation_anchor"
    )
    assert not hasattr(
        state, "cycle_source_preparation_preview"
    )


def test_identical_sources_distinct_full_generations(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)

    first = _optional(root)
    first_anchor = first.cycle_source_preparation_generation_anchor
    first_manifest = (
        first.cycle_source_preparation_preview.manifest
    )

    second = _optional(root)
    second_anchor = second.cycle_source_preparation_generation_anchor
    second_manifest = (
        second.cycle_source_preparation_preview.manifest
    )

    assert second_anchor.revision > first_anchor.revision
    assert second_anchor.state_id == first_anchor.state_id
    assert second_anchor.repo_id == first_anchor.repo_id
    assert second_anchor.root_path == first_anchor.root_path

    assert (
        first_manifest.source_manifest_sha256
        == second_manifest.source_manifest_sha256
    )
    assert (
        first_anchor.source_manifest_sha256
        == second_anchor.source_manifest_sha256
    )
    assert first_anchor != second_anchor


def test_default_full_has_no_optional_anchor(
    tmp_path, isolated_dirs,
):
    result = _run(_repo(tmp_path))
    assert not hasattr(
        result, "cycle_source_preparation_generation_anchor"
    )


def test_hard_only_preview_has_no_optional_anchor(
    tmp_path, isolated_dirs,
):
    result = _run(
        _repo(tmp_path),
        cycle_source_preparation_preview=True,
    )
    assert not hasattr(
        result, "cycle_source_preparation_generation_anchor"
    )


def test_unavailable_optional_preview_has_no_anchor(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    (root / "pkg" / "b.py").write_bytes(b"value = 1\n")

    result = _optional(root)

    assert result.cycle_source_preparation_preview.status == (
        "UNAVAILABLE"
    )
    assert not hasattr(
        result, "cycle_source_preparation_generation_anchor"
    )


def test_forged_manifest_does_not_receive_anchor(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    result = _optional(root)
    preview = result.cycle_source_preparation_preview
    _, metadata = _persisted(root)

    forged = replace(
        preview,
        manifest=replace(
            preview.manifest,
            source_manifest_sha256="0" * 64,
        ),
    )

    assert make_optional_prepared_generation_anchor(
        forged, metadata
    ) is None


def test_wrong_source_domain_does_not_receive_anchor(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    result = _optional(root)
    preview = result.cycle_source_preparation_preview
    _, metadata = _persisted(root)

    forged = replace(
        preview,
        source_modules=("foreign",),
    )

    assert make_optional_prepared_generation_anchor(
        forged, metadata
    ) is None


def test_generation_anchor_does_not_reread_sources(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    result = _optional(root)
    preview = result.cycle_source_preparation_preview
    _, metadata = _persisted(root)

    def forbidden(self):
        raise AssertionError("filesystem reread forbidden")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_bytes", forbidden)
        anchor = make_optional_prepared_generation_anchor(
            preview, metadata
        )

    assert type(anchor) is OptionalPreparedGenerationAnchor

"""P1D3F3: local snapshot generation consistency without receipts."""

from copy import copy
from dataclasses import replace
from pathlib import Path

import pytest

import contextor.core.cycle_semantics.optional_store_generation as store_module

from contextor.core.cycle_semantics.optional_store_generation import (
    OPTIONAL_STORE_ASSESSMENT_AUTHORITY,
    OptionalStoredGenerationAssessment,
    assess_optional_stored_generation,
)
from contextor.core.paths import repo_cache_dir
from tests.test_cycle_semantics_optional_generation_anchor import (
    _optional,
)
from tests.test_cycle_semantics_optional_child_full_preview import (
    _repo,
)
from tests.test_original_worker_full_receipt_optin import (
    _persisted,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _case(tmp_path):
    root = _repo(tmp_path)
    result = _optional(root)

    return (
        root,
        result.cycle_source_preparation_generation_anchor,
        result.cycle_source_preparation_preview,
    )


def _assess(case):
    root, anchor, preparation = case

    return assess_optional_stored_generation(
        repo_cache_dir(root),
        anchor,
        preparation,
    )


def test_current_local_snapshot_matches(
    tmp_path, isolated_dirs,
):
    case = _case(tmp_path)
    root, anchor, preparation = case

    result = _assess(case)
    state, metadata = _persisted(root)

    assert type(result) is OptionalStoredGenerationAssessment
    assert result.status == "MATCHED_CURRENT_LOCAL_SNAPSHOT_NON_ATOMIC"
    assert result.reason is None
    assert result.authority == OPTIONAL_STORE_ASSESSMENT_AUTHORITY

    assert result.revision == metadata.revision
    assert result.state_id == metadata.state_id
    assert result.graph_sha256 == anchor.graph_sha256
    assert result.source_manifest_sha256 == (
        preparation.manifest.source_manifest_sha256
    )

    assert state.cycle_source_publication is None
    assert state.cycle_partial_source_publication is None

    assert result == _assess(case)


def test_old_anchor_rejected_after_new_full_even_with_same_digest(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)

    first = _optional(root)
    old_anchor = first.cycle_source_preparation_generation_anchor
    old_preparation = first.cycle_source_preparation_preview

    second = _optional(root)
    new_anchor = second.cycle_source_preparation_generation_anchor
    new_preparation = second.cycle_source_preparation_preview

    assert new_anchor.revision > old_anchor.revision
    assert (
        old_anchor.source_manifest_sha256
        == new_anchor.source_manifest_sha256
    )

    old = assess_optional_stored_generation(
        repo_cache_dir(root),
        old_anchor,
        old_preparation,
    )

    new = assess_optional_stored_generation(
        repo_cache_dir(root),
        new_anchor,
        new_preparation,
    )

    assert old.status == "UNAVAILABLE"
    assert old.reason == "STORE_GENERATION_NOT_CURRENT"

    assert new.status == "MATCHED_CURRENT_LOCAL_SNAPSHOT_NON_ATOMIC"


@pytest.mark.parametrize(
    "field,value",
    [
        ("revision", 999999),
        ("state_id", "foreign-state"),
        ("repo_id", "foreign-repo"),
        ("root_path", "foreign-root"),
    ],
)
def test_foreign_generation_rejected(
    tmp_path, isolated_dirs, field, value,
):
    case = list(_case(tmp_path))
    case[1] = replace(case[1], **{field: value})

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "STORE_GENERATION_NOT_CURRENT"


def test_missing_store_metadata_rejected(
    tmp_path, isolated_dirs, monkeypatch,
):
    case = _case(tmp_path)

    monkeypatch.setattr(
        store_module,
        "read_metadata",
        lambda _path: None,
    )

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "STORE_METADATA_UNAVAILABLE"


def test_missing_snapshot_rejected(
    tmp_path, isolated_dirs, monkeypatch,
):
    case = _case(tmp_path)

    monkeypatch.setattr(
        store_module,
        "load_snapshot",
        lambda *args, **kwargs: None,
    )

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "STORE_SNAPSHOT_UNAVAILABLE"


def test_loaded_metadata_mismatch_rejected(
    tmp_path, isolated_dirs, monkeypatch,
):
    case = _case(tmp_path)

    original = store_module.load_snapshot

    def mismatched(*args, **kwargs):
        loaded = original(*args, **kwargs)
        state, metadata = loaded

        return (
            state,
            replace(
                metadata,
                revision=metadata.revision + 1,
            ),
        )

    monkeypatch.setattr(
        store_module,
        "load_snapshot",
        mismatched,
    )

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "LOADED_METADATA_MISMATCH"


def test_observed_store_head_rollover_rejected(
    tmp_path, isolated_dirs, monkeypatch,
):
    case = _case(tmp_path)
    root = case[0]

    original = store_module.read_metadata
    initial = original(repo_cache_dir(root))
    calls = []

    def changed(_path):
        calls.append(1)

        if len(calls) == 1:
            return initial

        return replace(
            initial,
            revision=initial.revision + 1,
        )

    monkeypatch.setattr(
        store_module,
        "read_metadata",
        changed,
    )

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "STORE_HEAD_CHANGED"
    assert len(calls) == 2


def test_stale_loaded_generation_rejected(
    tmp_path, isolated_dirs, monkeypatch,
):
    case = _case(tmp_path)

    original = store_module.load_snapshot

    def stale(*args, **kwargs):
        loaded = original(*args, **kwargs)
        state, metadata = loaded

        changed = copy(state)
        changed.cycle_semantics_state = "stale"

        return changed, metadata

    monkeypatch.setattr(
        store_module,
        "load_snapshot",
        stale,
    )

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == (
        "GENERATION_CANONICAL_CYCLE_EVIDENCE_NOT_FRESH"
    )


def test_forged_manifest_digest_rejected(
    tmp_path, isolated_dirs,
):
    case = list(_case(tmp_path))
    preparation = case[2]

    case[2] = replace(
        preparation,
        manifest=replace(
            preparation.manifest,
            source_manifest_sha256="0" * 64,
        ),
    )

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == (
        "GENERATION_ANCHOR_METADATA_MISMATCH"
    )


def test_invalid_anchor_authority_rejected(
    tmp_path, isolated_dirs,
):
    case = list(_case(tmp_path))

    case[1] = replace(
        case[1],
        authority="FORGED_AUTHORITY",
    )

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "INVALID_ANCHOR_IDENTITY"


def test_assessment_does_not_reread_python_sources(
    tmp_path, isolated_dirs, monkeypatch,
):
    case = _case(tmp_path)

    original = Path.read_bytes

    def guarded(self):
        if self.suffix == ".py":
            raise AssertionError(
                "Python source reread forbidden"
            )

        return original(self)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_bytes", guarded)
        result = _assess(case)

    assert result.status == "MATCHED_CURRENT_LOCAL_SNAPSHOT_NON_ATOMIC"

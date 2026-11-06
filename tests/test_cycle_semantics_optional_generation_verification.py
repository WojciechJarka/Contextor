"""P1D3F2: independently compare supplied generation declarations."""

from copy import copy
from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.cycle_semantics.optional_generation_anchor import (
    OPTIONAL_GENERATION_ASSESSMENT_AUTHORITY,
    OptionalPreparedGenerationAssessment,
    assess_optional_prepared_generation,
)
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
    state, metadata = _persisted(root)

    return (
        result.cycle_source_preparation_generation_anchor,
        result.cycle_source_preparation_preview,
        state,
        metadata,
    )


def _assess(case):
    return assess_optional_prepared_generation(*case)


def test_real_persisted_generation_matches(tmp_path, isolated_dirs):
    case = _case(tmp_path)
    anchor, preview, state, metadata = case

    result = _assess(case)

    assert type(result) is OptionalPreparedGenerationAssessment
    assert result.status == "MATCHED_SUPPLIED_GENERATION_NON_ATOMIC"
    assert result.reason is None
    assert result.authority == OPTIONAL_GENERATION_ASSESSMENT_AUTHORITY
    assert result.revision == metadata.revision
    assert result.state_id == metadata.state_id
    assert result.graph_sha256 == anchor.graph_sha256
    assert result.source_manifest_sha256 == (
        preview.manifest.source_manifest_sha256
    )
    assert state.cycle_source_publication is None
    assert state.cycle_partial_source_publication is None
    assert result == _assess(case)


def test_old_anchor_rejected_after_new_full_even_same_digest(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)

    first = _optional(root)
    old_anchor = first.cycle_source_preparation_generation_anchor
    old_preview = first.cycle_source_preparation_preview

    second = _optional(root)
    new_anchor = second.cycle_source_preparation_generation_anchor
    new_preview = second.cycle_source_preparation_preview
    state, metadata = _persisted(root)

    assert new_anchor.revision > old_anchor.revision
    assert old_anchor.source_manifest_sha256 == (
        new_anchor.source_manifest_sha256
    )

    old = assess_optional_prepared_generation(
        old_anchor, old_preview, state, metadata,
    )
    new = assess_optional_prepared_generation(
        new_anchor, new_preview, state, metadata,
    )

    assert old.status == "UNAVAILABLE"
    assert old.reason == "ANCHOR_METADATA_MISMATCH"
    assert new.status == "MATCHED_SUPPLIED_GENERATION_NON_ATOMIC"


@pytest.mark.parametrize(
    "field,value",
    [
        ("revision", 999999),
        ("state_id", "foreign-state"),
        ("repo_id", "foreign-repo"),
        ("root_path", "foreign-root"),
    ],
)
def test_forged_anchor_identity_rejected(
    tmp_path, isolated_dirs, field, value,
):
    case = list(_case(tmp_path))
    case[0] = replace(case[0], **{field: value})

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "ANCHOR_METADATA_MISMATCH"


def test_modified_supplied_metadata_rejected(
    tmp_path, isolated_dirs,
):
    case = list(_case(tmp_path))
    case[3] = replace(
        case[3],
        revision=case[3].revision + 1,
    )

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "ANCHOR_METADATA_MISMATCH"


def test_state_generation_mismatch_rejected(
    tmp_path, isolated_dirs,
):
    case = list(_case(tmp_path))
    changed = copy(case[2])
    changed.state_id = "different-state"
    case[2] = changed

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "CANONICAL_GENERATION_IDENTITY_MISMATCH"


def test_stale_cycle_semantics_rejected(tmp_path, isolated_dirs):
    case = list(_case(tmp_path))
    changed = copy(case[2])
    changed.cycle_semantics_state = "stale"
    case[2] = changed

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "CANONICAL_CYCLE_EVIDENCE_NOT_FRESH"


def test_resync_required_rejected(tmp_path, isolated_dirs):
    case = list(_case(tmp_path))
    changed = copy(case[2])
    changed.resync_required = True
    case[2] = changed

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "CANONICAL_CYCLE_EVIDENCE_NOT_FRESH"


def test_modified_canonical_graph_rejected(
    tmp_path, isolated_dirs,
):
    case = list(_case(tmp_path))
    changed = copy(case[2])
    changed_graph = copy(changed.dependency_graph)
    changed_graph.hard_edges = {
        name: set(targets)
        for name, targets in changed_graph.hard_edges.items()
    }
    changed_graph.hard_edges["pkg.a"].add("pkg.helper")
    changed.dependency_graph = changed_graph
    case[2] = changed

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "OPTIONAL_DECLARATIONS_GENERATION_MISMATCH"


def test_changed_canonical_import_facts_rejected(
    tmp_path, isolated_dirs,
):
    case = list(_case(tmp_path))
    changed = copy(case[2])
    changed.modules = dict(changed.modules)

    module = changed.modules["pkg.a"]

    changed.modules["pkg.a"] = replace(
        module,
        imports=[
            item
            for item in module.imports
            if not item.is_from_import
        ],
    )
    case[2] = changed

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "OPTIONAL_DECLARATIONS_GENERATION_MISMATCH"


def test_forged_manifest_rejected(tmp_path, isolated_dirs):
    case = list(_case(tmp_path))
    preview = case[1]

    case[1] = replace(
        preview,
        manifest=replace(
            preview.manifest,
            source_manifest_sha256="0" * 64,
        ),
    )

    result = _assess(case)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "ANCHOR_METADATA_MISMATCH"


def test_validation_performs_no_source_reread(
    tmp_path, isolated_dirs, monkeypatch,
):
    case = _case(tmp_path)

    def forbidden(self):
        raise AssertionError("filesystem reread forbidden")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_bytes", forbidden)
        scoped.setattr(Path, "read_text", forbidden)
        result = _assess(case)

    assert result.status == "MATCHED_SUPPLIED_GENERATION_NON_ATOMIC"

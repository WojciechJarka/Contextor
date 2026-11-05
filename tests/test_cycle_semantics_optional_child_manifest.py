"""P1D3A: optional prepared manifests are not publication claims."""

from dataclasses import replace

import pytest

from contextor.core.cycle_semantics.generation_manifest import (
    MANIFEST_VERSION,
    OPTIONAL_MANIFEST_VERSION,
    prepare_cycle_source_manifest,
)
from contextor.core.cycle_semantics.publication_binding import (
    _validated_claim_digest,
)
from tests.test_cycle_semantics_optional_child_byte_replay import (
    _fixture,
)
from tests.test_cycle_semantics_optional_child_scenarios import FILES
from tests.test_cycle_semantics_evidence import (
    PAIR,
    PASS,
    _bound,
    _p1b_snapshots,
)


def _prepare(case):
    hard, index, snapshot, evidence, sources, imports, root, closures = case
    return prepare_cycle_source_manifest(
        hard,
        index,
        snapshot,
        evidence,
        sources,
        source_selection="OPTIONAL_NAMED_CHILDREN",
        indexed_imports_by_module=imports,
        package_root=root,
        source_closures=closures,
    )


def test_optional_manifest_prepared_only(tmp_path):
    case = _fixture(tmp_path)

    manifest = _prepare(case)

    assert manifest.version == OPTIONAL_MANIFEST_VERSION
    assert manifest.source_selection == "OPTIONAL_NAMED_CHILDREN"
    assert manifest.authority == "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
    assert len(manifest.source_manifest_sha256) == 64
    assert len(manifest.components) == 1
    assert manifest.components[0].preparation_state == (
        "PREPARED_UNPUBLISHED"
    )
    assert manifest.components[0].source_signatures == (
        case[3].components[0].source_signatures
    )
    assert manifest == _prepare(case)


def test_optional_child_missing_blocks_manifest(tmp_path):
    case = list(_fixture(tmp_path))
    case[4] = dict(case[4])
    case[4].pop("pkg.child")

    manifest = _prepare(case)

    assert manifest.version == OPTIONAL_MANIFEST_VERSION
    assert manifest.source_manifest_sha256 is None
    assert manifest.components[0].preparation_state == "UNAVAILABLE"
    assert manifest.components[0].model_classification == "INDETERMINATE"


def test_forged_optional_evidence_blocks_manifest(tmp_path):
    case = list(_fixture(tmp_path))
    case[3] = replace(
        case[3],
        source_manifest_fingerprint="0" * 64,
    )

    manifest = _prepare(case)

    assert manifest.source_manifest_sha256 is None
    assert manifest.components[0].preparation_state == "UNAVAILABLE"


def test_wrong_source_cohort_blocks_manifest(tmp_path):
    case = list(_fixture(tmp_path))
    case[7] = ()

    with pytest.raises(
        ValueError, match="OPTIONAL_MANIFEST_INPUT_INVALID"
    ):
        _prepare(case)


def test_unrelated_module_does_not_change_optional_manifest(tmp_path):
    first = _fixture(
        tmp_path / "first",
        files={**FILES, "pkg/unrelated.py": "value=1\n"},
    )
    second = _fixture(
        tmp_path / "second",
        files={**FILES, "pkg/unrelated.py": "value=2\n"},
    )

    a = _prepare(first)
    b = _prepare(second)

    assert a.source_manifest_sha256 is not None
    assert a.source_manifest_sha256 == b.source_manifest_sha256


def test_two_independent_sccs(tmp_path):
    case = _fixture(
        tmp_path,
        files={
            **FILES,
            "pkg/x.py": "import pkg.y\n",
            "pkg/y.py": "import pkg.x\n",
        },
    )

    manifest = _prepare(case)

    assert len(manifest.components) == 2
    assert all(
        component.preparation_state == "PREPARED_UNPUBLISHED"
        for component in manifest.components
    )
    assert manifest.source_manifest_sha256 is not None


def test_hard_only_manifest_preserves_previous_version():
    index, snapshot, evidence = _bound(PAIR, PASS)

    manifest = prepare_cycle_source_manifest(
        PAIR,
        index,
        snapshot,
        evidence,
        _p1b_snapshots(PASS),
    )

    assert manifest.version == MANIFEST_VERSION
    assert manifest.source_selection == "HARD_ONLY"
    assert manifest.source_manifest_sha256 is not None


def test_existing_publication_rejects_optional_manifest(tmp_path):
    manifest = _prepare(_fixture(tmp_path))

    with pytest.raises(
        ValueError, match="prepared manifest is incomplete or unsupported"
    ):
        _validated_claim_digest(None, manifest)

"""P1D3C: optional SCC declarations have no publication authority."""

from dataclasses import replace

import pytest

from contextor.core.cycle_semantics.generation_manifest import (
    MANIFEST_VERSION,
)
from contextor.core.cycle_semantics.original_worker_binding import (
    _select_original_worker_sources,
)
from contextor.core.cycle_semantics.partial_scc_claims import (
    OPTIONAL_PARTIAL_SCC_CLAIMS_VERSION,
    OPTIONAL_PARTIAL_SCC_CLAIMS_AUTHORITY,
    PreparedOptionalPartialSCCClaims,
    validate_optional_partial_scc_claims,
    validate_partial_scc_claims,
)
from tests.test_cycle_semantics_optional_child_worker_manifest import (
    _pipeline,
    _prepare,
)
from tests.test_cycle_semantics_optional_child_worker_capture import (
    FILES,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch, isolated_dirs):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _case(tmp_path, *, files=None):
    pipeline = _pipeline(tmp_path, files=files)
    index, hard_edges, snapshot, _ = pipeline
    preparation = _prepare(pipeline)

    _, _, package_root = _select_original_worker_sources(
        index,
        hard_edges,
        "OPTIONAL_NAMED_CHILDREN",
    )

    imports = {
        name: module.imports
        for name, module in index.modules.items()
    }

    return hard_edges, snapshot, preparation, imports, package_root


def _check(case):
    return validate_optional_partial_scc_claims(
        case[0],
        case[1],
        case[2],
        case[3],
        package_root=case[4],
    )


def test_optional_declarations_are_not_published(tmp_path):
    case = _case(tmp_path)
    result = _check(case)

    assert type(result) is PreparedOptionalPartialSCCClaims
    assert result.version == OPTIONAL_PARTIAL_SCC_CLAIMS_VERSION
    assert result.authority == OPTIONAL_PARTIAL_SCC_CLAIMS_AUTHORITY
    assert result.source_selection == "OPTIONAL_NAMED_CHILDREN"
    assert "pkg.child" in result.source_modules
    assert result.declared_manifest_sha256 == (
        case[2].manifest.source_manifest_sha256
    )
    assert result.components == case[2].component_preparations
    assert all(
        item.preparation_state == "PREPARED_UNPUBLISHED"
        for item in result.components
    )
    assert result == _check(case)


def test_legacy_validator_rejects_optional_preparation(tmp_path):
    case = _case(tmp_path)

    assert validate_partial_scc_claims(
        case[0], case[1], case[2]
    ) is None

    forged = replace(
        case[2],
        manifest=replace(
            case[2].manifest,
            version=MANIFEST_VERSION,
        ),
    )

    assert validate_partial_scc_claims(
        case[0], case[1], forged
    ) is None


def test_wrong_source_selection_rejected(tmp_path):
    case = list(_case(tmp_path))
    case[2] = replace(case[2], source_selection="HARD_ONLY")
    assert _check(case) is None


def test_wrong_manifest_version_or_mode_rejected(tmp_path):
    case = list(_case(tmp_path))
    original = case[2].manifest

    case[2] = replace(
        case[2],
        manifest=replace(
            original,
            version=MANIFEST_VERSION,
        ),
    )
    assert _check(case) is None

    case[2] = replace(
        case[2],
        manifest=replace(
            original,
            source_selection="HARD_ONLY",
        ),
    )
    assert _check(case) is None


def test_missing_optional_child_source_rejected(tmp_path):
    case = list(_case(tmp_path))

    case[2] = replace(
        case[2],
        source_modules=tuple(
            name
            for name in case[2].source_modules
            if name != "pkg.child"
        ),
    )

    assert _check(case) is None


def test_missing_optional_child_signature_rejected(tmp_path):
    case = list(_case(tmp_path))
    preparation = case[2]
    component = preparation.manifest.components[0]

    changed_component = replace(
        component,
        source_signatures=tuple(
            row
            for row in component.source_signatures
            if row[0] != "pkg.child"
        ),
    )

    changed_manifest = replace(
        preparation.manifest,
        components=(changed_component,),
    )

    case[2] = replace(
        preparation,
        manifest=changed_manifest,
        component_preparations=changed_manifest.components,
    )

    assert _check(case) is None


def test_changed_import_facts_invalidate_closure(tmp_path):
    case = list(_case(tmp_path))
    case[3] = dict(case[3])
    case[3]["pkg.a"] = []

    assert _check(case) is None


def test_changed_graph_identity_rejected(tmp_path):
    case = list(_case(tmp_path))
    case[1] = replace(
        case[1],
        graph_sha256="0" * 64,
    )

    assert _check(case) is None


def test_two_independent_sccs_preserved(tmp_path):
    case = _case(
        tmp_path,
        files={
            **FILES,
            "pkg/x.py": "import pkg.y\n",
            "pkg/y.py": "import pkg.x\n",
        },
    )

    result = _check(case)

    assert result is not None
    assert len(result.components) == 2
    assert tuple(
        item.members for item in result.components
    ) == tuple(
        item.members for item in case[2].component_preparations
    )


def test_incomplete_or_forged_manifest_hash_rejected(tmp_path):
    case = list(_case(tmp_path))
    case[2] = replace(
        case[2],
        manifest=replace(
            case[2].manifest,
            source_manifest_sha256=None,
        ),
    )

    assert _check(case) is None

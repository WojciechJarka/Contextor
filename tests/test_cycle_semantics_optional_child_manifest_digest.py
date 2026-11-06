"""P1D3E: v3 manifest digest replay, without source certification."""

from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.cycle_semantics.generation_manifest import (
    MANIFEST_VERSION,
    OPTIONAL_MANIFEST_VERSION,
    OptionalManifestEvidenceWitness,
    _digest,
    prepare_cycle_source_manifest,
    verify_prepared_optional_manifest_digest,
)
from contextor.core.cycle_semantics.publication_binding import (
    _validated_claim_digest,
)
from contextor.core.cycle_semantics.partial_scc_claims import (
    validate_optional_partial_scc_claims,
    validate_partial_scc_claims,
)
from tests.test_cycle_semantics_optional_child_byte_replay import (
    _fixture,
)
from tests.test_cycle_semantics_optional_child_manifest import (
    _prepare,
)
from tests.test_cycle_semantics_optional_child_partial_claims import (
    _case as real_case,
    _check,
)
from tests.test_cycle_semantics_optional_child_scenarios import (
    FILES,
)
from tests.test_cycle_semantics_evidence import (
    PAIR,
    PASS,
    _bound,
    _p1b_snapshots,
)
from tests.test_cycle_semantics_partial_scc_claims import (
    _case as legacy_case,
)
from tests.test_original_worker_partial_scc_preparation import (
    TWO_PASS,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch, isolated_dirs):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def test_optional_manifest_digest_replays(tmp_path):
    manifest = _prepare(_fixture(tmp_path))

    assert manifest.version == OPTIONAL_MANIFEST_VERSION
    assert type(manifest.optional_witness) is (
        OptionalManifestEvidenceWitness
    )
    assert verify_prepared_optional_manifest_digest(manifest)
    assert verify_prepared_optional_manifest_digest(manifest)


def test_valid_sha256_forgery_is_rejected(tmp_path):
    manifest = _prepare(_fixture(tmp_path))

    changed = replace(
        manifest,
        source_manifest_sha256="0" * 64,
    )

    assert not verify_prepared_optional_manifest_digest(changed)


def test_component_token_tampering_is_rejected(tmp_path):
    manifest = _prepare(_fixture(tmp_path))
    witness = manifest.optional_witness

    changed = replace(
        manifest,
        optional_witness=replace(
            witness,
            component_evidence_tokens=("0" * 64,),
        ),
    )

    assert not verify_prepared_optional_manifest_digest(changed)


def test_missing_witness_is_rejected(tmp_path):
    manifest = _prepare(_fixture(tmp_path))

    assert not verify_prepared_optional_manifest_digest(
        replace(manifest, optional_witness=None)
    )


def test_wrong_evidence_semantic_version_is_rejected(tmp_path):
    manifest = _prepare(_fixture(tmp_path))

    changed = replace(
        manifest,
        optional_witness=replace(
            manifest.optional_witness,
            evidence_semantic_version="cycle-semantics-evidence/3",
        ),
    )

    assert not verify_prepared_optional_manifest_digest(changed)


def test_forged_source_manifest_fails_even_with_rehashed_outer_digest(
    tmp_path,
):
    manifest = _prepare(_fixture(tmp_path))
    witness = replace(
        manifest.optional_witness,
        source_manifest_fingerprint="0" * 64,
    )

    accepted = {
        module: (raw, ast_hash)
        for component in manifest.components
        for module, raw, ast_hash in component.source_signatures
    }
    ordered = tuple(
        (name, *accepted[name])
        for name in sorted(accepted)
    )

    forged_hash = _digest((
        OPTIONAL_MANIFEST_VERSION,
        "OPTIONAL_NAMED_CHILDREN",
        witness.evidence_semantic_version,
        manifest.graph_sha256,
        witness.source_manifest_fingerprint,
        tuple((
            component.members,
            component.model_classification,
            component.model_kind,
            component.model_evidence_sha256,
            component.source_signatures,
            witness.component_evidence_tokens[position],
        ) for position, component in enumerate(manifest.components)),
        ordered,
    ))

    changed = replace(
        manifest,
        source_manifest_sha256=forged_hash,
        optional_witness=witness,
    )

    assert not verify_prepared_optional_manifest_digest(changed)


def test_modified_component_source_signature_rejected(tmp_path):
    manifest = _prepare(_fixture(tmp_path))
    component = manifest.components[0]

    changed_rows = list(component.source_signatures)
    name, _, ast_hash = changed_rows[0]
    changed_rows[0] = (name, "0" * 64, ast_hash)

    changed = replace(
        manifest,
        components=(
            replace(
                component,
                source_signatures=tuple(changed_rows),
            ),
        ),
    )

    assert not verify_prepared_optional_manifest_digest(changed)


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_classification", []),
        ("model_kind", {}),
    ],
)
def test_unhashable_component_model_fields_fail_closed(
    tmp_path, field, value,
):
    manifest = _prepare(_fixture(tmp_path))
    component = manifest.components[0]

    malformed = replace(
        manifest,
        components=(
            replace(component, **{field: value}),
        ),
    )

    assert (
        verify_prepared_optional_manifest_digest(malformed)
        is False
    )


def test_missing_optional_child_blocks_complete_digest(tmp_path):
    case = list(_fixture(tmp_path))
    case[4] = dict(case[4])
    case[4].pop("pkg.child")

    manifest = _prepare(case)

    assert manifest.source_manifest_sha256 is None
    assert manifest.optional_witness is None
    assert not verify_prepared_optional_manifest_digest(manifest)


def test_multiple_scc_component_token_order_is_bound(tmp_path):
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
    assert verify_prepared_optional_manifest_digest(manifest)

    witness = manifest.optional_witness

    changed = replace(
        manifest,
        optional_witness=replace(
            witness,
            component_evidence_tokens=tuple(
                reversed(witness.component_evidence_tokens)
            ),
        ),
    )

    assert not verify_prepared_optional_manifest_digest(changed)


def test_optional_claim_validator_rejects_forged_64_hex_digest(
    tmp_path,
):
    case = list(real_case(tmp_path))
    preparation = case[2]

    assert _check(case) is not None

    forged = replace(
        preparation.manifest,
        source_manifest_sha256="0" * 64,
    )
    case[2] = replace(preparation, manifest=forged)

    assert _check(case) is None


def test_optional_claim_validator_rejects_forged_witness(
    tmp_path,
):
    case = list(real_case(tmp_path))
    preparation = case[2]
    manifest = preparation.manifest

    forged = replace(
        manifest,
        optional_witness=replace(
            manifest.optional_witness,
            component_evidence_tokens=("0" * 64,),
        ),
    )
    case[2] = replace(preparation, manifest=forged)

    assert _check(case) is None


def test_legacy_hard_only_digest_and_no_witness():
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
    assert manifest.optional_witness is None
    assert manifest.source_manifest_sha256 is not None
    assert not verify_prepared_optional_manifest_digest(manifest)


def test_hard_only_publication_rejects_injected_optional_witness(
    tmp_path,
):
    edges, snapshot, preparation = legacy_case(
        tmp_path, TWO_PASS
    )

    witness = OptionalManifestEvidenceWitness(
        evidence_semantic_version="cycle-semantics-evidence/4",
        source_manifest_fingerprint="0" * 64,
        component_evidence_tokens=(
            "0" * 64,
            "0" * 64,
        ),
    )

    assert preparation.manifest is not None

    mutated_manifest = replace(
        preparation.manifest,
        optional_witness=witness,
    )
    mutated_preparation = replace(
        preparation,
        manifest=mutated_manifest,
    )

    assert validate_partial_scc_claims(
        edges,
        snapshot,
        mutated_preparation,
    ) is None

    with pytest.raises(
        ValueError,
        match="prepared manifest is incomplete or unsupported",
    ):
        _validated_claim_digest(None, mutated_manifest)


def test_optional_digest_replay_never_publishes(tmp_path):
    manifest = _prepare(_fixture(tmp_path))

    assert verify_prepared_optional_manifest_digest(manifest)

    with pytest.raises(ValueError):
        _validated_claim_digest(None, manifest)


def test_digest_replay_performs_no_filesystem_read(
    tmp_path, monkeypatch,
):
    manifest = _prepare(_fixture(tmp_path))

    def forbidden(self):
        raise AssertionError("source reread forbidden")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_bytes", forbidden)
        assert verify_prepared_optional_manifest_digest(manifest)

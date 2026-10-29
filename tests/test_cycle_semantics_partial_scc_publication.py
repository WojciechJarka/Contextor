"""Store-owned partial SCC receipts bind declarations, not runtime safety."""

from __future__ import annotations

import copy
import pickle
from dataclasses import fields, replace

import pytest

import contextor.core.live_state.store as store
from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.cycle_semantics.lifecycle import invalidate_cycle_semantics
from contextor.core.cycle_semantics.partial_scc_publication import (
    PARTIAL_SCC_PUBLICATION_AUTHORITY,
    PARTIAL_SCC_PUBLICATION_VERSION,
    CanonicalPartialSCCReceipt,
    seal_partial_scc_preparation,
    verify_co_published_partial_scc_preparation,
)
from contextor.core.cycle_semantics.publication_binding import (
    verify_co_published_cycle_manifest,
)
from contextor.core.cycle_semantics.warning_eligibility import (
    _verified_model_pass_cycle_paths,
)
from contextor.core.domain.graph import ProjectGraph
from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
from tests.test_original_worker_partial_scc_preparation import (
    PASS_AND_HAZARD,
    PASS_AND_UNKNOWN,
    TWO_PASS,
    _prepare,
    _real_pipeline,
    _repo,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _case(tmp_path, sources=PASS_AND_UNKNOWN):
    index, graph, snapshot = _real_pipeline(_repo(tmp_path, sources))
    preparation = _prepare(index, graph, snapshot)
    state = RepositoryAnalysisState(
        dependency_graph=ProjectGraph(
            hard_edges={name: set(targets) for name, targets in graph.hard_edges.items()},
            soft_edges={},
        ),
        cycles=[["a", "b", "a"], ["x", "y", "x"]],
        cycles_state="fresh",
        cycle_semantics=snapshot,
        cycle_semantics_state="fresh",
    )
    return state, preparation


def _save(state, root, revision=1, *, partial=None, manifest=None):
    return save_snapshot(
        state, root, "partial-state", exact_revision=revision,
        file_state_payload={
            "_meta": {"state_id": "partial-state", "revision": revision},
            "files": {},
        },
        prepared_partial_scc_preparation=partial,
        prepared_cycle_manifest=manifest,
    )


def _verify(state, metadata):
    return verify_co_published_partial_scc_preparation(
        state,
        revision=metadata.revision,
        state_id=metadata.state_id,
        repo_id=metadata.repo_id,
        root_path=metadata.root_path,
    )


def _tamper(root, metadata, mutate):
    path = root / metadata.state_file
    payload = pickle.loads(path.read_bytes())
    mutate(payload["state"])
    path.write_bytes(pickle.dumps(payload))


def test_t01_t02_real_mixed_receipt_survives_load(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path)
    assert preparation.status == "UNAVAILABLE"
    metadata = _save(state, tmp_path, partial=preparation)
    loaded, loaded_metadata = load_snapshot(tmp_path, "partial-state")
    receipt = loaded.cycle_partial_source_publication
    assert type(receipt) is CanonicalPartialSCCReceipt
    assert receipt.version == PARTIAL_SCC_PUBLICATION_VERSION
    assert receipt.authority == PARTIAL_SCC_PUBLICATION_AUTHORITY
    assert receipt.revision == metadata.revision == loaded_metadata.revision
    assert _verify(loaded, loaded_metadata)
    assert tuple(item.model_classification for item in receipt.preparation.component_preparations) == (
        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "INDETERMINATE",
    )
    assert state.cycle_partial_source_publication is None


def test_t03_partial_receipt_does_not_create_v2_or_warn1(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path)
    _save(state, tmp_path, partial=preparation)
    loaded, metadata = load_snapshot(tmp_path, "partial-state")
    assert loaded.cycle_source_publication is None
    assert _verify(loaded, metadata)
    assert _verified_model_pass_cycle_paths(
        loaded,
        expected_revision=metadata.revision,
        expected_state_id=metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=metadata.root_path,
    ) == frozenset()


def test_t04_complete_pass_hazard_partial_receipt(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path, PASS_AND_HAZARD)
    _save(state, tmp_path, partial=preparation)
    loaded, metadata = load_snapshot(tmp_path, "partial-state")
    assert _verify(loaded, metadata)
    assert tuple(item.model_classification for item in
                 loaded.cycle_partial_source_publication.preparation.component_preparations) == (
        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
    )


def test_t05_v2_and_partial_receipts_share_generation(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path, TWO_PASS)
    metadata = _save(state, tmp_path, partial=preparation, manifest=preparation.manifest)
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    assert loaded.cycle_source_publication is not None
    assert loaded.cycle_partial_source_publication is not None
    assert _verify(loaded, metadata)
    assert verify_co_published_cycle_manifest(
        loaded, revision=metadata.revision, state_id=metadata.state_id,
        repo_id=metadata.repo_id, root_path=metadata.root_path,
    )
    assert loaded.cycle_source_publication.revision == (
        loaded.cycle_partial_source_publication.revision
    )


def test_t06_next_revision_without_input_drops_partial_receipt(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path)
    _save(state, tmp_path, partial=preparation)
    old, _ = load_snapshot(tmp_path, "partial-state")
    _save(old, tmp_path, revision=2)
    loaded, metadata = load_snapshot(tmp_path, "partial-state")
    assert metadata.revision == 2
    assert loaded.cycle_partial_source_publication is None


def test_t07_invalidation_clears_receipt(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path)
    _save(state, tmp_path, partial=preparation)
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    invalidate_cycle_semantics(loaded, "SOURCE_CHANGED")
    assert loaded.cycle_partial_source_publication is None
    assert loaded.cycle_semantics_state == "stale"
    assert loaded.cycle_semantics is not None


def test_t08_cow_clears_receipt_without_mutating_previous(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path)
    _save(state, tmp_path, partial=preparation)
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    candidate = loaded.clone_for_update()
    assert candidate.cycle_partial_source_publication is None
    assert loaded.cycle_partial_source_publication is not None


@pytest.mark.parametrize("tamper", ["classification", "digest"])
def test_t09_t10_tamper_is_removed_on_hydration(tmp_path, isolated_dirs, tamper):
    state, preparation = _case(tmp_path)
    metadata = _save(state, tmp_path, partial=preparation)

    def mutate(stored):
        receipt = stored.cycle_partial_source_publication
        if tamper == "digest":
            stored.cycle_partial_source_publication = replace(
                receipt, claims_sha256="0" * 64,
            )
        else:
            original = receipt.preparation
            components = list(original.component_preparations)
            components[0] = replace(
                components[0], model_classification="MODEL_INTERNAL_EARLY_BINDING_HAZARD",
            )
            stored.cycle_partial_source_publication = replace(
                receipt,
                preparation=replace(original, component_preparations=tuple(components)),
            )

    _tamper(tmp_path, metadata, mutate)
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    assert loaded.cycle_partial_source_publication is None
    assert loaded.cycles == [["a", "b", "a"], ["x", "y", "x"]]


@pytest.mark.parametrize("identity", ["revision", "state_id", "repo_id", "root_path"])
def test_t11_foreign_identity_fails_closed(tmp_path, isolated_dirs, identity):
    state, preparation = _case(tmp_path)
    metadata = _save(state, tmp_path, partial=preparation)
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    arguments = dict(revision=metadata.revision, state_id=metadata.state_id,
                     repo_id=metadata.repo_id, root_path=metadata.root_path)
    arguments[identity] = 2 if identity == "revision" else "foreign"
    assert not verify_co_published_partial_scc_preparation(loaded, **arguments)


@pytest.mark.parametrize("mutation", ["graph", "internal_edge"])
def test_t12_changed_graph_fails_verification(tmp_path, isolated_dirs, mutation):
    state, preparation = _case(tmp_path)
    metadata = _save(state, tmp_path, partial=preparation)
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    if mutation == "graph":
        loaded.dependency_graph.hard_edges["a"].add("other")
    else:
        loaded.dependency_graph.hard_edges["a"].add("a")
    assert not _verify(loaded, metadata)


@pytest.mark.parametrize("mutation", ["semantic", "cycle", "resync"])
def test_t13_stale_family_or_resync_fails_closed(tmp_path, isolated_dirs, mutation):
    state, preparation = _case(tmp_path)
    metadata = _save(state, tmp_path, partial=preparation)
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    if mutation == "semantic":
        loaded.cycle_semantics_state = "stale"
    elif mutation == "cycle":
        loaded.cycles_state = "stale"
    else:
        loaded.resync_required = True
    assert not _verify(loaded, metadata)


def test_t14_absent_legacy_attribute_does_not_fabricate_receipt(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path)
    metadata = _save(state, tmp_path, partial=preparation)
    _tamper(tmp_path, metadata, lambda stored: stored.__dict__.pop(
        "cycle_partial_source_publication", None,
    ))
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    assert loaded.cycle_partial_source_publication is None


def test_t15_invalid_input_cannot_advance_metadata(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path)
    _save(state, tmp_path, partial=preparation)
    invalid = replace(preparation, reason="FORGED")
    with pytest.raises((ValueError, TypeError)):
        _save(state, tmp_path, revision=2, partial=invalid)
    assert read_metadata(tmp_path).revision == 1
    loaded, metadata = load_snapshot(tmp_path, "partial-state")
    assert _verify(loaded, metadata)


def test_t16_failed_metadata_commit_keeps_previous_generation(
    tmp_path, isolated_dirs, monkeypatch,
):
    state, preparation = _case(tmp_path)
    _save(state, tmp_path, partial=preparation)
    original_replace = store.os.replace

    def fail_metadata(source, target):
        if target.name == "engine_state.meta.json":
            raise RuntimeError("synthetic metadata failure")
        return original_replace(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(store.os, "replace", fail_metadata)
        with pytest.raises(RuntimeError, match="synthetic metadata failure"):
            _save(state, tmp_path, revision=2, partial=preparation)
    loaded, metadata = load_snapshot(tmp_path, "partial-state")
    assert metadata.revision == 1
    assert _verify(loaded, metadata)


def test_t17_standalone_seal_is_pure_and_not_durable(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path)
    state.revision = 1
    state.state_id = "partial-state"
    before = copy.deepcopy(state.__dict__)
    receipt = seal_partial_scc_preparation(
        state, preparation, revision=1, state_id="partial-state",
        repo_id="", root_path="",
    )
    assert type(receipt) is CanonicalPartialSCCReceipt
    assert state.__dict__ == before
    assert read_metadata(tmp_path) is None


def test_t18_ordinary_store_and_dataclass_contract_unchanged(tmp_path, isolated_dirs):
    state, _ = _case(tmp_path)
    field_names = {item.name for item in fields(RepositoryAnalysisState)}
    assert "cycle_partial_source_publication" not in field_names
    _save(state, tmp_path)
    loaded, metadata = load_snapshot(tmp_path, "partial-state")
    assert loaded.cycle_partial_source_publication is None
    assert metadata.revision == 1


def test_t19_repeat_verification_read_only(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path)
    metadata = _save(state, tmp_path, partial=preparation)
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    before = copy.deepcopy(loaded.__dict__)
    assert _verify(loaded, metadata) is True
    assert _verify(loaded, metadata) is True
    assert loaded.__dict__ == before


def test_t20_tampered_receipt_preserves_structural_diagnostics(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path)
    metadata = _save(state, tmp_path, partial=preparation)
    _tamper(tmp_path, metadata, lambda stored: setattr(
        stored,
        "cycle_partial_source_publication",
        replace(stored.cycle_partial_source_publication, claims_sha256="0" * 64),
    ))
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    assert loaded.cycle_partial_source_publication is None
    assert loaded.cycles_state == "fresh"
    assert loaded.cycles == [["a", "b", "a"], ["x", "y", "x"]]
    assert loaded.dependency_graph.hard_edges == state.dependency_graph.hard_edges


def _recursive_declaration(preparation, kind):
    recursive = []
    recursive.append(recursive)
    if kind == "source_modules":
        return replace(preparation, source_modules=recursive)
    components = list(preparation.component_preparations)
    components[1] = replace(components[1], model_kind=recursive)
    return replace(preparation, component_preparations=tuple(components))


@pytest.mark.parametrize("kind,sources", [
    ("source_modules", TWO_PASS),
    ("model_kind", PASS_AND_UNKNOWN),
])
def test_r1_t04_malformed_declaration_cannot_be_sealed(
    tmp_path, isolated_dirs, kind, sources,
):
    state, preparation = _case(tmp_path, sources)
    state.revision = 1
    state.state_id = "partial-state"
    malformed = _recursive_declaration(preparation, kind)
    with pytest.raises((ValueError, TypeError)):
        seal_partial_scc_preparation(
            state, malformed, revision=1, state_id="partial-state",
            repo_id="", root_path="",
        )
    assert state.cycle_partial_source_publication is None


@pytest.mark.parametrize("kind,sources", [
    ("source_modules", TWO_PASS),
    ("model_kind", PASS_AND_UNKNOWN),
])
def test_r1_t05_t06_t07_recursive_receipt_fails_verify_and_hydration(
    tmp_path, isolated_dirs, kind, sources,
):
    state, preparation = _case(tmp_path, sources)
    metadata = _save(state, tmp_path, partial=preparation)
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    receipt = loaded.cycle_partial_source_publication
    loaded.cycle_partial_source_publication = replace(
        receipt,
        preparation=_recursive_declaration(receipt.preparation, kind),
    )
    before_edges = copy.deepcopy(loaded.dependency_graph.hard_edges)
    before_cycles = copy.deepcopy(loaded.cycles)
    assert _verify(loaded, metadata) is False
    assert loaded.dependency_graph.hard_edges == before_edges
    assert loaded.cycles == before_cycles

    _tamper(tmp_path, metadata, lambda stored: setattr(
        stored,
        "cycle_partial_source_publication",
        replace(
            stored.cycle_partial_source_publication,
            preparation=_recursive_declaration(
                stored.cycle_partial_source_publication.preparation, kind,
            ),
        ),
    ))
    hydrated, _ = load_snapshot(tmp_path, "partial-state")
    assert hydrated.cycle_partial_source_publication is None
    assert hydrated.dependency_graph.hard_edges == before_edges
    assert hydrated.cycles == before_cycles
    assert hydrated.cycles_state == "fresh"


@pytest.mark.parametrize("sources", [PASS_AND_UNKNOWN, PASS_AND_HAZARD])
def test_r1_t08_valid_publication_survives_hydration(tmp_path, isolated_dirs, sources):
    state, preparation = _case(tmp_path, sources)
    metadata = _save(state, tmp_path, partial=preparation)
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    assert _verify(loaded, metadata)
    assert loaded.cycle_partial_source_publication.preparation == preparation


def test_r1_t09_t10_v2_coexistence_and_repeat_verification(tmp_path, isolated_dirs):
    state, preparation = _case(tmp_path, TWO_PASS)
    metadata = _save(state, tmp_path, partial=preparation, manifest=preparation.manifest)
    loaded, _ = load_snapshot(tmp_path, "partial-state")
    before = copy.deepcopy(loaded.__dict__)
    assert _verify(loaded, metadata) is True
    assert _verify(loaded, metadata) is True
    assert verify_co_published_cycle_manifest(
        loaded, revision=metadata.revision, state_id=metadata.state_id,
        repo_id=metadata.repo_id, root_path=metadata.root_path,
    )
    assert loaded.__dict__ == before

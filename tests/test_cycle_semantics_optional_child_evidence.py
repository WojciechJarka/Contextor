"""P1D2A: optional source evidence remains snapshot-only."""

import ast
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.source import ParsedSourceInput
from contextor.core.cycle_semantics.evidence import (
    EVIDENCE_SEMANTIC_VERSION,
    OPTIONAL_EVIDENCE_SEMANTIC_VERSION,
    assess_index_bound_scc_models,
    build_source_bound_cycle_evidence,
)
from tests.test_cycle_semantics_optional_child_scenarios import _case
from tests.test_cycle_semantics_evidence import _bound


def _inputs(tmp_path, case):
    parsed = {}
    source_text = {}
    for module, tree in case[1].items():
        path = (
            tmp_path / "repo"
            / Path(*module.split(".")).with_suffix(".py")
        )
        raw = path.read_bytes()
        parsed[module] = ParsedSourceInput(
            tree, hashlib.sha256(raw).hexdigest()
        )
        source_text[module] = raw.decode("utf-8")
    return parsed, source_text


def _build(case, parsed):
    graph, _, imports, package_root, closures = case
    return build_source_bound_cycle_evidence(
        graph.hard_edges,
        parsed,
        source_selection="OPTIONAL_NAMED_CHILDREN",
        indexed_imports_by_module=imports,
        package_root=package_root,
        source_closures=closures,
    )


def test_optional_identity_and_selected_sources(tmp_path):
    case = _case(tmp_path)
    parsed, _ = _inputs(tmp_path, case)

    evidence = _build(case, parsed)
    assert evidence.semantic_version == (
        OPTIONAL_EVIDENCE_SEMANTIC_VERSION
    )
    assert evidence.source_selection == "OPTIONAL_NAMED_CHILDREN"
    assert evidence.components[0].reachable_modules == (
        case[4][0].evidence_source_modules
    )
    assert "pkg.child" in evidence.components[0].reachable_modules
    assert evidence.scenarios.evidence_scope == (
        "OPTIONAL_NAMED_CHILDREN_SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
    )
    assert evidence == _build(case, parsed)


def test_optional_child_byte_identity_changes_token(tmp_path):
    case = _case(tmp_path)
    parsed, _ = _inputs(tmp_path, case)
    before = _build(case, parsed)

    raw = b"pass\nx = 1\n"
    changed = dict(parsed)
    changed["pkg.child"] = ParsedSourceInput(
        ast.parse(raw),
        hashlib.sha256(raw).hexdigest(),
    )

    after = _build(case, changed)
    assert (
        before.components[0].evidence_token
        != after.components[0].evidence_token
    )
    assert (
        before.graph_fingerprint
        == after.graph_fingerprint
    )


def test_old_hard_only_version_and_default(tmp_path):
    case = _case(tmp_path)
    parsed, _ = _inputs(tmp_path, case)
    graph = case[0]

    default = build_source_bound_cycle_evidence(
        graph.hard_edges, parsed
    )
    explicit = build_source_bound_cycle_evidence(
        graph.hard_edges, parsed,
        source_selection="HARD_ONLY",
    )

    assert default == explicit
    assert default.semantic_version == EVIDENCE_SEMANTIC_VERSION
    assert default.source_selection == "HARD_ONLY"


def test_invalid_cohort_rejected(tmp_path):
    case = _case(tmp_path)
    parsed, _ = _inputs(tmp_path, case)
    graph, _, imports, root, closures = case

    with pytest.raises(ValueError, match="OPTIONAL_COHORT"):
        build_source_bound_cycle_evidence(
            graph.hard_edges,
            parsed,
            source_selection="OPTIONAL_NAMED_CHILDREN",
            indexed_imports_by_module=imports,
            package_root=root,
            source_closures=(),
        )

    with pytest.raises(ValueError, match="HARD_ONLY_OPTIONAL"):
        build_source_bound_cycle_evidence(
            graph.hard_edges,
            parsed,
            indexed_imports_by_module=imports,
        )

    with pytest.raises(ValueError, match="SOURCE_SELECTION_INVALID"):
        build_source_bound_cycle_evidence(
            graph.hard_edges,
            parsed,
            source_selection="UNKNOWN",
        )


def test_indexed_import_fact_mismatch_rejected(tmp_path):
    case = _case(tmp_path)
    parsed, _ = _inputs(tmp_path, case)
    graph, _, imports, root, closures = case

    corrupted = dict(imports)
    corrupted["pkg.b"] = []

    with pytest.raises(
        ValueError, match="OPTIONAL_IMPORT_FACTS_MISMATCH:pkg.b"
    ):
        build_source_bound_cycle_evidence(
            graph.hard_edges,
            parsed,
            source_selection="OPTIONAL_NAMED_CHILDREN",
            indexed_imports_by_module=corrupted,
            package_root=root,
            source_closures=closures,
        )


def test_missing_selected_source_never_proves_pass(tmp_path):
    case = _case(tmp_path)
    parsed, _ = _inputs(tmp_path, case)
    parsed.pop("pkg.child")

    evidence = _build(case, parsed)
    assert evidence.components[0].classification == "INDETERMINATE"
    assert evidence.components[0].reason == "MISSING_OR_INVALID_SOURCE"
    assert "MISSING" in evidence.components[0].source_signatures[
        tuple(evidence.components[0].reachable_modules).index(
            "pkg.child"
        )
    ]


def test_legacy_verifier_rejects_optional_evidence(tmp_path):
    case = _case(tmp_path)
    parsed, sources = _inputs(tmp_path, case)
    graph = case[0]

    evidence = _build(case, parsed)
    index, snapshot, _ = _bound(graph.hard_edges, sources)

    result = assess_index_bound_scc_models(
        graph.hard_edges,
        index,
        snapshot,
        evidence,
    )
    assert all(
        row.evidence_state != "DECLARED_INPUTS_CONSISTENT"
        for row in result
    )
    assert all(
        row.reason == "EVIDENCE_SEMANTIC_VERSION_MISMATCH"
        for row in result
    )

    forged_version = replace(
        evidence,
        semantic_version=EVIDENCE_SEMANTIC_VERSION,
    )
    result = assess_index_bound_scc_models(
        graph.hard_edges,
        index,
        snapshot,
        forged_version,
    )
    assert all(
        row.reason
        == "SOURCE_SELECTION_UNSUPPORTED_BY_HARD_ONLY_VERIFIER"
        for row in result
    )

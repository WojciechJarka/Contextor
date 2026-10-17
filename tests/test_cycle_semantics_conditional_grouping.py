"""Conditional witnesses retain paths when grouped."""

import ast
import json
from dataclasses import asdict, replace
from hashlib import sha256

import pytest

from contextor.core.source import ParsedSourceInput
from contextor.core.cycle_semantics.edge_sites import (
    analyze_cyclic_import_sites,
)
from contextor.core.cycle_semantics.conditional_discovery import (
    discover_conditional_reexports,
)
from contextor.core.cycle_semantics.conditional_grouping import (
    group_conditional_reexports,
)


C31_FIXTURE_GRAPH = {
    "repo.__init__": ("repo.main",),
    "repo.main": ("repo.filters", "ui.__init__"),
    "repo.filters": ("ui.__init__",),
    "ui.__init__": ("ui.gui",),
    "ui.gui": ("repo.__init__",),
}

C31_FIXTURE_SOURCES = {
    "repo.__init__": (
        "from repo.main import run_repo_generator\n"
    ),
    "repo.main": (
        "from repo.filters import FilterWindow\n"
        "from ui import theme\n"
        "def run_repo_generator(parent=None):\n"
        "    pass\n"
    ),
    "repo.filters": "from ui import theme\n",
    "ui.__init__": "from .gui import run\n",
    "ui.gui": (
        "from repo import run_repo_generator\n"
        "def run():\n"
        "    pass\n"
    ),
}


def _discovery():
    parsed = {
        module: ParsedSourceInput(
            tree=ast.parse(source),
            source_fingerprint=sha256(
                source.encode("utf-8")
            ).hexdigest(),
        )
        for module, source in C31_FIXTURE_SOURCES.items()
    }

    sites = analyze_cyclic_import_sites(
        C31_FIXTURE_GRAPH,
        parsed,
    )

    return discover_conditional_reexports(
        sites,
        parsed,
        tuple(C31_FIXTURE_GRAPH),
    )


def test_c31_two_paths_one_group():
    report = group_conditional_reexports(
        _discovery()
    )

    assert report.group_count == 1
    assert report.witness_count == 2
    assert len(report.groups) == 1

    group = report.groups[0]

    assert group.package_initializer == "repo.__init__"
    assert group.provider == "repo.main"
    assert group.export_name == "run_repo_generator"
    assert group.closing_module == "ui.gui"
    assert group.witness_count == 2
    assert len(group.witnesses) == 2


def test_c31_source_order_preserved():
    report = group_conditional_reexports(
        _discovery()
    )

    group = report.groups[0]

    assert group.outgoing_import_sites == (
        (1, 0, "repo.filters"),
        (2, 0, "ui.__init__"),
    )

    assert all(
        item.assessment.runtime_execution_status
        == "UNKNOWN_NOT_EVALUATED"
        for item in group.witnesses
    )


def test_c31_original_full_paths_preserved():
    discovery = _discovery()
    grouped = group_conditional_reexports(
        discovery
    )

    original = {
        candidate.assessment.chain
        for candidate in discovery.candidates
    }

    retained = {
        candidate.assessment.chain
        for group in grouped.groups
        for candidate in group.witnesses
    }

    assert original == retained
    assert len(retained) == grouped.witness_count


def test_c31_group_never_certifies_runtime():
    report = group_conditional_reexports(
        _discovery()
    )

    assert report.runtime_execution_status == (
        "UNKNOWN_NOT_EVALUATED"
    )
    assert report.source_snapshot_binding == (
        "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    )

    for group in report.groups:
        assert group.runtime_execution_status == (
            "UNKNOWN_NOT_EVALUATED"
        )
        assert group.evidence_scope == (
            "SHARED_CONDITIONAL_SOURCE_ORDER_RELATIONSHIP"
        )


def test_c31_empty_input_is_not_safe():
    discovery = _discovery()

    empty = replace(
        discovery,
        candidates=(),
    )

    report = group_conditional_reexports(empty)

    assert report.group_count == 0
    assert report.witness_count == 0
    assert report.runtime_execution_status == (
        "UNKNOWN_NOT_EVALUATED"
    )


def test_c31_duplicate_witness_rejected():
    discovery = _discovery()

    duplicate = replace(
        discovery,
        candidates=(
            discovery.candidates
            + discovery.candidates[:1]
        ),
    )

    with pytest.raises(ValueError):
        group_conditional_reexports(
            duplicate
        )


def test_c31_invalid_witness_rejected():
    discovery = _discovery()

    candidate = discovery.candidates[0]

    broken = replace(
        candidate,
        assessment=replace(
            candidate.assessment,
            status="UNKNOWN",
        ),
    )

    modified = replace(
        discovery,
        candidates=(
            broken,
            *discovery.candidates[1:],
        ),
    )

    with pytest.raises(ValueError):
        group_conditional_reexports(
            modified
        )


def test_c31_authority_is_not_upgraded():
    discovery = _discovery()

    modified = replace(
        discovery,
        source_snapshot_binding="ATOMICALLY_VERIFIED",
    )

    with pytest.raises(ValueError):
        group_conditional_reexports(
            modified
        )


def test_c31_determinism_and_json():
    discovery = _discovery()

    before = asdict(discovery)

    first = group_conditional_reexports(
        discovery
    )

    second = group_conditional_reexports(
        discovery
    )

    assert first == second
    assert asdict(discovery) == before

    json.dumps(asdict(first))

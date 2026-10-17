import ast
import json
from dataclasses import asdict, replace
from hashlib import sha256

import pytest

from contextor.core.source import ParsedSourceInput
from contextor.core.cycle_semantics.edge_sites import (
    analyze_cyclic_import_sites,
)
from contextor.core.cycle_semantics.activation_view import (
    analyze_cycle_activation_view,
)
from contextor.core.cycle_semantics.conditional_discovery import (
    discover_conditional_reexports,
)
from contextor.core.cycle_semantics.public_projection import (
    project_cycle_semantics,
)


C32_FIXTURE_GRAPH = {
    "repo.__init__": ("repo.main",),
    "repo.main": ("repo.filters", "ui.__init__"),
    "repo.filters": ("ui.__init__",),
    "ui.__init__": ("ui.gui",),
    "ui.gui": ("repo.__init__",),
}

C32_FIXTURE_SOURCES = {
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


def _c32_inputs():
    parsed_sources = {
        module: ParsedSourceInput(
            tree=ast.parse(source),
            source_fingerprint=sha256(
                source.encode("utf-8")
            ).hexdigest(),
        )
        for module, source in C32_FIXTURE_SOURCES.items()
    }
    import_sites = analyze_cyclic_import_sites(
        C32_FIXTURE_GRAPH,
        parsed_sources,
    )
    discovery = discover_conditional_reexports(
        import_sites,
        parsed_sources,
        tuple(C32_FIXTURE_GRAPH),
    )
    return parsed_sources, import_sites, discovery


def test_c32_two_witnesses_one_group_public():
    _, import_sites, discovery = _c32_inputs()
    projected = project_cycle_semantics(
        import_sites,
        discovery,
    )

    assert projected["summary"]["cyclic_scc_total"] == 1
    assert projected["summary"]["conditional_group_total"] == 1
    assert projected["summary"]["conditional_witness_total"] == 2
    component = projected["components"][0]
    assert component["conditional_reexports"]["group_total"] == 1
    group = component["conditional_reexports"]["groups"][0]
    assert group["witness_total"] == 2
    original_chains = {
        candidate.assessment.chain
        for candidate in discovery.candidates
    }
    projected_chains = {
        tuple(witness["chain"])
        for witness in group["witnesses"]
    }
    assert len(original_chains) == 2
    assert projected_chains == original_chains


def test_c32_structural_cycle_survives_no_witness():
    _, import_sites, discovery = _c32_inputs()
    empty_discovery = replace(discovery, candidates=())
    projected = project_cycle_semantics(
        import_sites,
        empty_discovery,
    )

    assert projected["summary"]["cyclic_scc_total"] == 1
    assert len(projected["components"]) == 1
    component = projected["components"][0]
    assert component["structural_edge_count"] == len(
        import_sites.components[0].internal_edges
    )
    assert component["conditional_reexports"]["group_total"] == 0
    assert projected["summary"]["conditional_group_total"] == 0
    assert component["runtime_execution_status"] == (
        "UNKNOWN_NOT_EVALUATED"
    )


def test_c32_direct_and_non_direct_accounting():
    _, import_sites, discovery = _c32_inputs()
    activation = analyze_cycle_activation_view(import_sites)
    projected = project_cycle_semantics(
        import_sites,
        discovery,
        max_edges=64,
    )
    component = projected["components"][0]

    assert component["structural_edge_count"] == (
        component["direct_candidate_edge_count"]
        + component["non_direct_candidate_edge_count"]
    )
    assert component["matched_edge_count"] + component[
        "unresolved_edge_count"
    ] == component["structural_edge_count"]
    assert component["diagnostic_category"] in {
        "UNGUARDED_DIRECT_CYCLIC_SUBGRAPH",
        "ACYCLIC_DIRECT_SUBGRAPH_WITH_SINGLE_EDGE_CLOSURES",
        "ACYCLIC_DIRECT_SUBGRAPH_NO_SINGLE_EDGE_CLOSURE",
    }
    activation_classifications = {
        (edge.source, edge.target): edge.classification
        for edge in activation.components[0].edges
    }
    assert {
        (edge["source"], edge["target"]): edge[
            "activation_classification"
        ]
        for edge in component["edges"]["items"]
    } == activation_classifications


def test_c32_bounded_edge_projection():
    _, import_sites, discovery = _c32_inputs()
    projected = project_cycle_semantics(
        import_sites,
        discovery,
        max_edges=1,
    )
    edges = projected["components"][0]["edges"]

    assert edges["total"] == len(
        import_sites.components[0].internal_edges
    )
    assert edges["returned"] == 1
    assert edges["truncated"] is True
    edge = edges["items"][0]
    assert edge["source"]
    assert edge["target"]
    assert edge["activation_classification"]
    assert edge["lexical_site_count"] >= 1
    assert edge["lexical_sites"]


def test_c32_zero_detail_budget_preserves_counts():
    _, import_sites, discovery = _c32_inputs()
    projected = project_cycle_semantics(
        import_sites,
        discovery,
        max_edges=0,
        max_groups=0,
        max_witnesses=0,
    )
    component = projected["components"][0]

    assert projected["summary"]["cyclic_scc_total"] == 1
    assert projected["summary"]["conditional_group_total"] == 1
    assert projected["summary"]["conditional_witness_total"] == 2
    assert component["structural_edge_count"] == 6
    assert component["conditional_reexports"]["group_total"] == 1
    assert component["edges"]["items"] == []
    assert component["edges"]["truncated"] is True
    assert component["conditional_reexports"]["groups"] == []
    assert component["conditional_reexports"]["truncated"] is True

    component_limited = project_cycle_semantics(
        import_sites,
        discovery,
        max_components=0,
    )
    assert component_limited["components"] == []
    assert component_limited["summary"]["cyclic_scc_total"] == 1
    assert component_limited["summary"]["cyclic_scc_returned"] == 0
    assert component_limited["summary"]["components_truncated"] is True


def test_c32_witness_detail_truncation():
    _, import_sites, discovery = _c32_inputs()
    projected = project_cycle_semantics(
        import_sites,
        discovery,
        max_witnesses=1,
    )
    group = projected["components"][0][
        "conditional_reexports"
    ]["groups"][0]

    assert group["witness_total"] == 2
    assert group["witnesses_returned"] == 1
    assert group["witnesses_truncated"] is True
    assert len(group["witnesses"]) == 1


def test_c32_source_authority_not_upgraded():
    _, import_sites, discovery = _c32_inputs()
    projected = project_cycle_semantics(
        import_sites,
        discovery,
    )

    assert projected["source_snapshot_binding"] == (
        "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    )
    assert projected["canonical_graph_revision"] is None
    assert projected["canonical_graph_revision_status"] == (
        "CALLER_MUST_SUPPLY_AUTHORITY"
    )
    assert projected["runtime_execution_status"] == (
        "UNKNOWN_NOT_EVALUATED"
    )


def test_c32_rejects_foreign_graph_witness():
    _, _, discovery = _c32_inputs()
    foreign_sites = analyze_cyclic_import_sites(
        {
            "foreign.left": ("foreign.right",),
            "foreign.right": ("foreign.left",),
        },
        {},
    )

    with pytest.raises(ValueError):
        project_cycle_semantics(
            foreign_sites,
            discovery,
        )


def test_c32_limits_reject_invalid_values():
    _, import_sites, discovery = _c32_inputs()
    for name in (
        "max_components",
        "max_edges",
        "max_groups",
        "max_witnesses",
    ):
        for value in (-1, 65, True):
            with pytest.raises(ValueError):
                project_cycle_semantics(
                    import_sites,
                    discovery,
                    **{name: value},
                )


def test_c32_determinism_json_and_no_input_mutation():
    parsed_sources, import_sites, discovery = _c32_inputs()
    source_trees_before = {
        module: ast.dump(source.tree, include_attributes=True)
        for module, source in parsed_sources.items()
    }
    sites_before = asdict(import_sites)
    discovery_before = asdict(discovery)

    first = project_cycle_semantics(
        import_sites,
        discovery,
    )
    second = project_cycle_semantics(
        import_sites,
        discovery,
    )

    assert first == second
    json.dumps(first)
    assert asdict(import_sites) == sites_before
    assert asdict(discovery) == discovery_before
    assert {
        module: ast.dump(source.tree, include_attributes=True)
        for module, source in parsed_sources.items()
    } == source_trees_before
    assert first["runtime_execution_status"] == (
        "UNKNOWN_NOT_EVALUATED"
    )

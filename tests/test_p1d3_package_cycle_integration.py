"""P1D3-B/C package SCC evidence through real isolated index and store paths."""

from __future__ import annotations

import ast
import copy
from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.api.facade import ContextorFacade
from contextor.core.cycle_semantics.evidence import (
    _component_token,
    _digest,
    assess_index_bound_scc_models,
    build_source_bound_cycle_evidence,
)
from contextor.core.cycle_semantics.edge_sites import analyze_cyclic_import_sites
from contextor.core.cycle_semantics.generation_manifest import MANIFEST_VERSION
from contextor.core.cycle_semantics.initialization_model import ImportOrderAssessment
from contextor.core.cycle_semantics.materialization import materialize_cycle_semantics
from contextor.core.cycle_semantics.model_identity import (
    indexed_to_logical_module,
    logical_to_indexed_module,
)
from contextor.core.cycle_semantics.model_source_closure import compute_cycle_model_source_closures
from contextor.core.cycle_semantics.package_graph_consistency import (
    assess_package_graph_consistency,
)
from contextor.core.cycle_semantics.original_worker_preparation import prepare_original_worker_cycle_manifest
from contextor.core.cycle_semantics.original_worker_reindex_planning import plan_original_worker_reindex
from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
from contextor.core.cycle_semantics.publication_binding import (
    PUBLICATION_BINDING_VERSION,
    seal_prepared_cycle_manifest,
    verify_co_published_cycle_manifest,
)
from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
from contextor.core.cycle_semantics.source_proof import assess_scc_source_bytes
from contextor.core.cycle_semantics.typing_guard import recognize_typing_guard
from contextor.core.graph.graph import build_graph
from contextor.core.graph.resolver import (
    build_trie,
    detect_package_root,
)
from contextor.core.reference.shared import (
    materialize_reexport_facts_by_module,
)
from contextor.core.source import parse_source_snapshot, read_source_snapshot
from contextor.core.symbol_engine.indexer import index_repository
from tests.cycle_semantics_lab import run_synthetic_import, write_synthetic_repository
from tests.test_original_worker_full_receipt_optin import _persisted
from tests.test_original_worker_official_full_live_publication import _official_live


F1 = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": "import pkg.b\ndef fa():\n    return 1\n",
    "pkg/b.py": "import pkg.a\ndef fb():\n    return 2\n",
}
F2 = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": "from . import b\nvalue = 1\n",
    "pkg/b.py": "from . import a\nvalue = 2\n",
}
F3 = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": "import pkg.b\nvalue = 1\n",
    "pkg/b.py": "from pkg.a import value\n",
}
F4 = {
    **F3,
    "pkg/a.py": "value = 1\nimport pkg.b\n",
}

D1_FALSE = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": "if False:\n    import pkg.b\nvalue = 1\n",
    "pkg/b.py": "import pkg.a\n",
}
D1_TRUE_HAZARD = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": "if True:\n    import pkg.b\nvalue = 1\n",
    "pkg/b.py": "from pkg.a import value\n",
}
D1_FALSE_SAFE = {**D1_TRUE_HAZARD, "pkg/a.py": "if False:\n    import pkg.b\nvalue = 1\n"}
D1_CLASS_HAZARD = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": "class Loader:\n    import pkg.b\nvalue = 1\n",
    "pkg/b.py": "from pkg.a import value\n",
}
D1_CLASS_SAFE = {**D1_CLASS_HAZARD, "pkg/a.py": "value = 1\nclass Loader:\n    import pkg.b\n"}
D1_CLASS_LOCAL = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": "class Loader:\n    import pkg.b as local_child\n",
    "pkg/b.py": "from pkg.a import local_child\n",
}
D1_METHOD = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": "class Loader:\n    def load(self):\n        import pkg.b\nvalue = 1\n",
    "pkg/b.py": "from pkg.a import value\n",
}
D1_INITIALIZER_HAZARD = {
    "pkg/__init__.py": "if True:\n    import pkg.a\nvalue = 1\n",
    "pkg/a.py": "import pkg\nx = pkg.value\n",
}
D1_INITIALIZER_SAFE = {
    **D1_INITIALIZER_HAZARD,
    "pkg/__init__.py": "value = 1\nif True:\n    import pkg.a\n",
}

D2A_ACTIVE_CHAIN = {
    "pkg/__init__.py": (
        "from . import a\n"
    ),
    "pkg/a.py": (
        "from . import b\n"
    ),
    "pkg/b.py": (
        "from . import a\n"
    ),
}

D2A_INITIALIZER_HAZARD = {
    "pkg/__init__.py": (
        "from . import a\n"
        "value = 1\n"
    ),
    "pkg/a.py": (
        "import pkg\n"
        "x = pkg.value\n"
    ),
}

D2A_INITIALIZER_SAFE = {
    **D2A_INITIALIZER_HAZARD,
    "pkg/__init__.py": (
        "value = 1\n"
        "from . import a\n"
    ),
}

D2B_NAME_SAFE = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.b\n"
        "value = 1\n"
    ),
    "pkg/b.py": "from pkg.a import value\n",
}

D2B_ATTR_SAFE = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "import typing\n"
        "if typing.TYPE_CHECKING:\n"
        "    import pkg.b\n"
        "value = 1\n"
    ),
    "pkg/b.py": "from pkg.a import value\n",
}

D2B_ELSE_HAZARD = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    pass\n"
        "else:\n"
        "    import pkg.b\n"
        "value = 1\n"
    ),
    "pkg/b.py": "from pkg.a import value\n",
}

D2B_ELSE_SAFE = {
    **D2B_ELSE_HAZARD,
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "value = 1\n"
        "if TYPE_CHECKING:\n"
        "    pass\n"
        "else:\n"
        "    import pkg.b\n"
    ),
}

D2B2_MIXED_ACTIVE = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.b\n"
        "import pkg.b\n"
        "value = 1\n"
    ),
    "pkg/b.py": "from pkg.a import value\n",
}


@pytest.fixture(autouse=True)
def _inline(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _indexed(root):
    index = index_repository(str(root))
    graph = build_graph(index.modules)
    return index, graph


def _captured(root, index, graph):
    plan = plan_original_worker_reindex(index, graph.hard_edges)
    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
    captured = index_repository(str(root), source_capture_module_ids=plan.selected_module_ids)
    return plan, captured


def _snapshot(root, index, graph):
    return materialize_cycle_semantics(
        root, graph.hard_edges,
        {name: module.path for name, module in index.modules.items()},
        index.source_fingerprints_by_module,
    )


@pytest.mark.parametrize("fixture", [F1, F2])
def test_package_closure_and_prepared_v2(tmp_path, isolated_dirs, fixture):
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    index, graph = _indexed(root)
    closure = compute_cycle_model_source_closures(graph.hard_edges)
    assert len(closure) == 1
    assert closure[0].members == ("pkg.a", "pkg.b")
    assert closure[0].evidence_source_modules == (
        "pkg.__init__", "pkg.a", "pkg.b",
    )
    if fixture is F1:
        assert closure[0].implicit_initializer_modules == ("pkg.__init__",)
    plan, captured = _captured(root, index, graph)
    assert plan.selected_module_ids == frozenset(closure[0].evidence_source_modules)
    snapshot = _snapshot(root, index, graph)
    prepared = prepare_original_worker_cycle_manifest(captured, graph.hard_edges, snapshot)
    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert prepared.source_modules == closure[0].evidence_source_modules
    manifest = prepared.manifest
    assert manifest.version == MANIFEST_VERSION == "cycle-source-manifest/2"
    assert manifest.source_manifest_sha256 is not None
    component = manifest.components[0]
    assert component.model_kind == "REGULAR_PACKAGE"
    assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    assert len(component.model_evidence_sha256) == 64
    assert tuple(row[0] for row in component.source_signatures) == closure[0].evidence_source_modules
    for entry in ("pkg.a", "pkg.b"):
        assert run_synthetic_import(root, entry).returncode == 0


def test_identity_mapping_and_ambiguous_layout():
    assert indexed_to_logical_module("pkg.sub.__init__") == "pkg.sub"
    assert indexed_to_logical_module("pkg.a") == "pkg.a"
    assert logical_to_indexed_module("pkg", frozenset({"pkg.__init__"})) == "pkg.__init__"
    assert logical_to_indexed_module("pkg", frozenset({"pkg", "pkg.__init__"})) is None
    assert logical_to_indexed_module("external", frozenset({"pkg.a"})) is None


def test_initializer_hard_edges_reach_fixed_point():
    edges = {
        "pkg.a": {"pkg.b"},
        "pkg.b": {"pkg.a"},
        "pkg.__init__": {"pkg.sub.child"},
        "pkg.sub.__init__": set(),
        "pkg.sub.child": set(),
    }
    closure = compute_cycle_model_source_closures(edges)[0]
    assert closure.hard_reachable_modules == ("pkg.a", "pkg.b")
    assert closure.evidence_source_modules == (
        "pkg.__init__", "pkg.a", "pkg.b", "pkg.sub.__init__", "pkg.sub.child",
    )
    assert closure.implicit_initializer_modules == (
        "pkg.__init__", "pkg.sub.__init__",
    )


def test_early_hazard_and_safe_reordering(tmp_path, isolated_dirs):
    outcomes = []
    for name, fixture in (("hazard", F3), ("safe", F4)):
        root = write_synthetic_repository(tmp_path / name, fixture)
        index, graph = _indexed(root)
        _, captured = _captured(root, index, graph)
        parsed = {
            module: parse_source_snapshot(source, module)
            for module, source in captured.original_worker_source_snapshots.items()
        }
        evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
        scenario = evidence.scenarios.components[0]
        outcomes.append((graph.hard_edges, scenario.classification, evidence.components[0].evidence_token))
        prepared = prepare_original_worker_cycle_manifest(
            captured, graph.hard_edges, _snapshot(root, index, graph),
        )
        assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
        actual = run_synthetic_import(root, "pkg.a")
        if name == "hazard":
            assert scenario.classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
            assert actual.returncode != 0
            assert "ImportError" in actual.stderr
            assert "partially initialized module" in actual.stderr
        else:
            assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
            assert actual.returncode == 0
    assert outcomes[0][0] == outcomes[1][0]
    assert outcomes[0][2] != outcomes[1][2]


def test_unsupported_namespace_and_contradictory_graph(tmp_path, isolated_dirs):
    decorated = dict(F1)
    decorated["pkg/a.py"] = "import pkg.b\n@unknown_decorator\ndef fa():\n    return 1\n"
    for name, fixture in (("decorated", decorated), ("namespace", {
        "pkg/a.py": F1["pkg/a.py"], "pkg/b.py": F1["pkg/b.py"],
    })):
        root = write_synthetic_repository(tmp_path / name, fixture)
        index, graph = _indexed(root)
        _, captured = _captured(root, index, graph)
        result = prepare_original_worker_cycle_manifest(
            captured, graph.hard_edges, _snapshot(root, index, graph),
        )
        assert result.status == "UNAVAILABLE"
        assert result.manifest is None

    root = write_synthetic_repository(tmp_path / "contradictory", F1)
    index, graph = _indexed(root)
    broken = {name: set(targets) for name, targets in graph.hard_edges.items()}
    broken["pkg.a"].add("pkg.__init__")
    captured = index_repository(
        str(root), source_capture_module_ids=frozenset(index.modules),
    )
    trees = {
        name: parse_source_snapshot(snapshot, name).tree
        for name, snapshot in captured.original_worker_source_snapshots.items()
    }
    report = analyze_cycle_scenarios(broken, trees)
    assert len(report.components) == 1
    assert report.components[0].classification == "INDETERMINATE"
    assert report.components[0].reason == "GRAPH_SOURCE_IMPORT_MISMATCH"


@pytest.mark.parametrize("fixture", [F1, F3])
def test_p1b_replay_rejects_forged_event(tmp_path, isolated_dirs, fixture):
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    index, graph = _indexed(root)
    _, captured = _captured(root, index, graph)
    sources = captured.original_worker_source_snapshots
    parsed = {name: parse_source_snapshot(snapshot, name) for name, snapshot in sources.items()}
    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
    scenario = evidence.scenarios.components[0]
    assessment = scenario.entry_assessments[0]
    assert assessment.outcome in {"MODEL_PASS", "EARLY_BINDING_HAZARD"}
    forged_events = (replace(assessment.events[0], operation="FORGED"), *assessment.events[1:])
    forged_scenario = replace(scenario, entry_assessments=(
        replace(assessment, events=forged_events), *scenario.entry_assessments[1:],
    ))
    graph_items = tuple(
        (name, tuple(sorted(graph.hard_edges[name])))
        for name in evidence.components[0].reachable_modules
    )
    forged_component = replace(
        evidence.components[0],
        evidence_token=_component_token(
            scenario.members, graph_items,
            evidence.components[0].source_signatures, forged_scenario,
        ),
    )
    forged = replace(
        evidence,
        components=(forged_component,),
        scenarios=replace(evidence.scenarios, components=(forged_scenario,)),
    )
    snapshot = _snapshot(root, index, graph)
    p0 = assess_index_bound_scc_models(
        graph.hard_edges, captured.source_fingerprints_by_module, snapshot, forged,
    )
    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
    p1b = assess_scc_source_bytes(
        graph.hard_edges, captured.source_fingerprints_by_module,
        snapshot, forged, sources,
    )
    assert p1b[0].reason == "MODEL_REPLAY_MISMATCH"


def test_p0_rehashed_invalid_package_scope_is_rejected(
    tmp_path,
    isolated_dirs,
):
    root = write_synthetic_repository(
        tmp_path / "repo",
        F1,
    )

    index, graph = _indexed(root)
    _, captured = _captured(root, index, graph)

    parsed = {
        module: parse_source_snapshot(snapshot, module)
        for module, snapshot
        in captured.original_worker_source_snapshots.items()
    }

    evidence = build_source_bound_cycle_evidence(
        graph.hard_edges,
        parsed,
    )

    scenario = evidence.scenarios.components[0]

    assert scenario.model_kind == "REGULAR_PACKAGE"
    assert scenario.classification == (
        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    )

    assessment = scenario.entry_assessments[0]

    changed_assessment = replace(
        assessment,
        evidence_scope="RESTRICTED_FLAT_MODULE_MODEL",
    )

    changed_scenario = replace(
        scenario,
        entry_assessments=(
            changed_assessment,
            *scenario.entry_assessments[1:],
        ),
    )

    component = evidence.components[0]

    subgraph = tuple(
        (
            module,
            tuple(sorted(graph.hard_edges[module])),
        )
        for module in component.reachable_modules
    )

    changed_component = replace(
        component,
        evidence_token=_component_token(
            component.members,
            subgraph,
            component.source_signatures,
            changed_scenario,
        ),
    )

    changed_evidence = replace(
        evidence,
        scenarios=replace(
            evidence.scenarios,
            components=(changed_scenario,),
        ),
        components=(changed_component,),
    )

    result = assess_index_bound_scc_models(
        graph.hard_edges,
        captured.source_fingerprints_by_module,
        _snapshot(root, index, graph),
        changed_evidence,
    )

    assert result[0].model_classification == "INDETERMINATE"
    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
    assert result[0].reason == (
        "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS"
    )


def test_p0_rejects_package_assessment_disguised_as_flat(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", F1)
    index, graph = _indexed(root)
    _, captured = _captured(root, index, graph)
    parsed = {
        name: parse_source_snapshot(snapshot, name)
        for name, snapshot in captured.original_worker_source_snapshots.items()
    }
    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
    scenario = evidence.scenarios.components[0]
    fake = ImportOrderAssessment("pkg.a", "MODEL_PASS", None, None, ())
    changed = replace(scenario, entry_assessments=(fake, scenario.entry_assessments[1]))
    component = evidence.components[0]
    subgraph = tuple(
        (name, tuple(sorted(graph.hard_edges[name])))
        for name in component.reachable_modules
    )
    altered = replace(
        evidence,
        scenarios=replace(evidence.scenarios, components=(changed,)),
        components=(replace(component, evidence_token=_component_token(
            component.members, subgraph, component.source_signatures, changed,
        )),),
    )
    result = assess_index_bound_scc_models(
        graph.hard_edges, captured.source_fingerprints_by_module,
        _snapshot(root, index, graph), altered,
    )
    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
    assert result[0].reason == "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS"


def test_seventeen_selected_modules_fail_before_capture(tmp_path, isolated_dirs):
    sources = {"a.py": "import b\n" + "".join(
        f"import m{i:02d}\n" for i in range(15)
    ), "b.py": "import a\n"}
    sources.update({f"m{i:02d}.py": "pass\n" for i in range(15)})
    root = write_synthetic_repository(tmp_path / "repo", sources)
    index, graph = _indexed(root)
    plan = plan_original_worker_reindex(index, graph.hard_edges)
    assert plan.status == "UNAVAILABLE"
    assert plan.reason == "CLOSURE_MODULE_LIMIT"
    assert not plan.selected_module_ids


def test_flat_and_package_components_remain_independent(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", {
        **F1,
        "flat_a.py": "import flat_b\nvalue=1\n",
        "flat_b.py": "import flat_a\nvalue=2\n",
    })
    index, graph = _indexed(root)
    plan, captured = _captured(root, index, graph)
    assert plan.selected_module_ids == frozenset({
        "flat_a", "flat_b", "pkg.__init__", "pkg.a", "pkg.b",
    })
    parsed = {
        name: parse_source_snapshot(snapshot, name)
        for name, snapshot in captured.original_worker_source_snapshots.items()
    }
    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
    assert tuple(c.model_kind for c in evidence.scenarios.components) == (
        "FLAT_MODULE", "REGULAR_PACKAGE",
    )
    assert all(
        c.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        for c in evidence.scenarios.components
    )
    prepared = prepare_original_worker_cycle_manifest(
        captured, graph.hard_edges, _snapshot(root, index, graph),
    )
    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert tuple(c.model_kind for c in prepared.manifest.components) == (
        "FLAT_MODULE", "REGULAR_PACKAGE",
    )


def test_legacy_v1_receipt_read_only(tmp_path, isolated_dirs):
    sources = {"a.py": "import b\nvalue=1\n", "b.py": "import a\nvalue=2\n"}
    root = write_synthetic_repository(tmp_path / "repo", sources)
    _, result = ContextorFacade.analyze_project(
        str(root), cycle_source_preparation_preview=True,
        cycle_source_publication_opt_in=True,
    )
    assert result is not None
    state, metadata = _persisted(root)
    current = state.cycle_source_publication
    assert current.version == PUBLICATION_BINDING_VERSION
    manifest = current.prepared_manifest
    old_components = tuple(replace(c, model_evidence_sha256=None) for c in manifest.components)
    ordered_sources = tuple(sorted({row for c in old_components for row in c.source_signatures}))
    old_manifest_hash = _digest((
        "cycle-source-manifest/1", manifest.graph_sha256,
        tuple(c.members for c in old_components), ordered_sources,
    ))
    old_manifest = replace(
        manifest, components=old_components,
        version="cycle-source-manifest/1",
        source_manifest_sha256=old_manifest_hash,
    )
    old_claims = _digest((
        "cycle-prepared-co-publication/1", manifest.graph_sha256,
        old_manifest_hash,
        tuple((c.members, c.model_classification, c.source_signatures)
              for c in old_components),
    ))
    old_receipt = replace(
        current, prepared_manifest=old_manifest,
        model_claims_sha256=old_claims,
        version="cycle-prepared-co-publication/1",
    )
    legacy_state = copy.copy(state)
    legacy_state.cycle_source_publication = old_receipt
    identity = dict(
        revision=metadata.revision, state_id=metadata.state_id,
        repo_id=metadata.repo_id, root_path=metadata.root_path,
    )
    assert verify_co_published_cycle_manifest(legacy_state, **identity)
    legacy_state.cycle_source_publication = replace(old_receipt, version=PUBLICATION_BINDING_VERSION)
    assert not verify_co_published_cycle_manifest(legacy_state, **identity)
    legacy_state.cycle_source_publication = replace(old_receipt, prepared_manifest=manifest)
    assert not verify_co_published_cycle_manifest(legacy_state, **identity)
    with pytest.raises(ValueError):
        seal_prepared_cycle_manifest(state, old_manifest, **identity)


def test_fixture_writer_rejects_escaping_paths(tmp_path):
    root = tmp_path / "repo"
    for name in ("../out.py", "/absolute.py", "a.txt", "a//b.py", "a/./b.py"):
        with pytest.raises(ValueError):
            write_synthetic_repository(root, {name: "pass\n"})


@pytest.mark.live
def test_official_isolated_package_publication(tmp_path, isolated_dirs, monkeypatch):
    root = write_synthetic_repository(tmp_path / "repo", F1)
    with _official_live(root, monkeypatch) as (client, server, identity, calls):
        _, result = ContextorFacade.analyze_project(
            str(root), cycle_source_preparation_preview=True,
            cycle_source_publication_opt_in=True,
        )
        assert result is not None
        assert result.cycle_source_preparation_preview.status == (
            "PREPARED_UNPUBLISHED_NON_ATOMIC"
        )
        state, metadata = _persisted(root)
        receipt = state.cycle_source_publication
        assert receipt is not None
        assert receipt.version == PUBLICATION_BINDING_VERSION
        assert receipt.prepared_manifest.version == MANIFEST_VERSION
        assert receipt.prepared_manifest.components[0].model_kind == "REGULAR_PACKAGE"
        assert metadata.repo_id == identity.repo_id
        assert calls == [root.resolve()]
        assert result.live_publish_status == "success"
        assert result.live_publish_revision == metadata.revision
        verified = client.verify_installed_cycle_generation(
            expected_revision=metadata.revision,
            expected_state_id=metadata.state_id,
            expected_repo_id=metadata.repo_id,
            expected_root_path=metadata.root_path,
            expected_graph_sha256=state.cycle_semantics.graph_sha256,
        )
        assert verified["status"] == "ok"
        assert verified["service_instance_id"] == server.endpoint.service_instance_id
        assert verified["source_manifest_sha256"] == (
            receipt.prepared_manifest.source_manifest_sha256
        )
        altered = copy.copy(state)
        altered_manifest = replace(
            receipt.prepared_manifest,
            components=(replace(
                receipt.prepared_manifest.components[0],
                model_evidence_sha256="f" * 64,
            ),),
        )
        altered.cycle_source_publication = replace(
            receipt, prepared_manifest=altered_manifest,
        )
        assert not verify_co_published_cycle_manifest(
            altered, revision=metadata.revision,
            state_id=metadata.state_id, repo_id=metadata.repo_id,
            root_path=metadata.root_path,
        )


@pytest.mark.parametrize("fixture,classification,entry,success", [
    (D1_FALSE, "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "pkg.a", True),
    (D1_TRUE_HAZARD, "MODEL_INTERNAL_EARLY_BINDING_HAZARD", "pkg.a", False),
    (D1_FALSE_SAFE, "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "pkg.a", True),
    (D1_CLASS_HAZARD, "MODEL_INTERNAL_EARLY_BINDING_HAZARD", "pkg.a", False),
    (D1_CLASS_SAFE, "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "pkg.a", True),
    (D1_CLASS_LOCAL, "MODEL_INTERNAL_EARLY_BINDING_HAZARD", "pkg.a", False),
    (D1_METHOD, "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "pkg.a", True),
    (D1_INITIALIZER_HAZARD, "MODEL_INTERNAL_EARLY_BINDING_HAZARD", "pkg", False),
    (D1_INITIALIZER_SAFE, "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "pkg", True),
])
def test_p1d3_d1_integrated_model_and_cpython(
    tmp_path, isolated_dirs, fixture, classification, entry, success,
):
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    index, graph = _indexed(root)
    _, captured = _captured(root, index, graph)
    parsed = {
        name: parse_source_snapshot(snapshot, name)
        for name, snapshot in captured.original_worker_source_snapshots.items()
    }
    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
    scenario = evidence.scenarios.components[0]
    assert scenario.model_kind == "REGULAR_PACKAGE"
    assert scenario.classification == classification
    assert scenario.evidence_scope == "CLOSED_REGULAR_PACKAGE_FRESH_ENTRY_MODEL"
    assert all(
        item.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
        for item in scenario.entry_assessments
    )
    p0 = assess_index_bound_scc_models(
        graph.hard_edges, captured.source_fingerprints_by_module,
        _snapshot(root, index, graph), evidence,
    )
    if fixture is D1_CLASS_LOCAL:
        assert p0[0].evidence_state == "INCOMPLETE_EVIDENCE"
    else:
        assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
    p1b = assess_scc_source_bytes(
        graph.hard_edges, captured.source_fingerprints_by_module,
        _snapshot(root, index, graph), evidence,
        captured.original_worker_source_snapshots,
    )
    if fixture is D1_CLASS_LOCAL:
        assert p1b[0].bytes_state == "UNAVAILABLE"
    else:
        assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
    assert (run_synthetic_import(root, entry).returncode == 0) is success
    if fixture is D1_FALSE:
        assert "pkg.b" in graph.hard_edges["pkg.a"]
        assert not any(
            event.operation == "START_IMPORT" and event.target == "pkg.b"
            for assessment in scenario.entry_assessments
            if assessment.entry_module == "pkg.a"
            for event in assessment.events
        )
    if fixture is D1_METHOD:
        assert "pkg.b" in graph.hard_edges["pkg.a"]
        assert not any(
            event.operation == "START_IMPORT" and event.target == "pkg.b"
            for assessment in scenario.entry_assessments
            if assessment.entry_module == "pkg.a"
            for event in assessment.events
        )
    if fixture is D1_CLASS_LOCAL:
        assert any(
            event.operation == "EARLY_BINDING_HAZARD"
            and event.target == "pkg.a"
            and event.symbol == "local_child"
            for assessment in scenario.entry_assessments
            for event in assessment.events
        )
    if fixture is D1_INITIALIZER_HAZARD:
        assert set(scenario.members) == {"pkg.__init__", "pkg.a"}
        assert any(
            event.operation == "EARLY_BINDING_HAZARD"
            and event.target == "pkg"
            and event.symbol == "value"
            for assessment in scenario.entry_assessments
            for event in assessment.events
        )


def test_p1d3_d1_same_graph_changes_model_evidence(tmp_path, isolated_dirs):
    values = []
    for name, fixture in (("active", D1_TRUE_HAZARD), ("inactive", D1_FALSE_SAFE),
                          ("class_early", D1_CLASS_HAZARD), ("class_late", D1_CLASS_SAFE)):
        root = write_synthetic_repository(tmp_path / name, fixture)
        index, graph = _indexed(root)
        _, captured = _captured(root, index, graph)
        parsed = {
            module: parse_source_snapshot(snapshot, module)
            for module, snapshot in captured.original_worker_source_snapshots.items()
        }
        evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
        values.append((graph.hard_edges, evidence.components[0].evidence_token))
    assert values[0][0] == values[1][0]
    assert values[2][0] == values[3][0]
    assert values[0][1] != values[1][1]
    assert values[2][1] != values[3][1]


def test_p1d3_d1_original_worker_prepares_v2(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", D1_CLASS_SAFE)
    index, graph = _indexed(root)
    _, captured = _captured(root, index, graph)
    prepared = prepare_original_worker_cycle_manifest(
        captured, graph.hard_edges, _snapshot(root, index, graph),
    )
    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert prepared.source_modules == ("pkg.__init__", "pkg.a", "pkg.b")
    assert prepared.manifest.version == MANIFEST_VERSION
    assert prepared.manifest.components[0].model_kind == "REGULAR_PACKAGE"
    assert prepared.manifest.components[0].model_classification == (
        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    )


@pytest.mark.parametrize("condition", ["unknown_condition", "1"])
def test_p1d3_d1_unsupported_condition_no_manifest(
    tmp_path, isolated_dirs, condition,
):
    fixture = {**D1_TRUE_HAZARD,
               "pkg/a.py": f"if {condition}:\n    import pkg.b\nvalue = 1\n"}
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    index, graph = _indexed(root)
    _, captured = _captured(root, index, graph)
    prepared = prepare_original_worker_cycle_manifest(
        captured, graph.hard_edges, _snapshot(root, index, graph),
    )
    assert prepared.status == "UNAVAILABLE"
    assert prepared.manifest is None


def test_p1d3_d1_forged_class_event_fails_replay(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", D1_CLASS_SAFE)
    index, graph = _indexed(root)
    _, captured = _captured(root, index, graph)
    sources = captured.original_worker_source_snapshots
    parsed = {name: parse_source_snapshot(snapshot, name) for name, snapshot in sources.items()}
    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
    scenario = evidence.scenarios.components[0]
    assessment = next(
        item for item in scenario.entry_assessments
        if any(event.operation == "CLASS_LOCAL_IMPORT" for event in item.events)
    )
    event = next(event for event in assessment.events if event.operation == "CLASS_LOCAL_IMPORT")
    forged_assessment = replace(
        assessment,
        events=tuple(
            replace(item, operation="FORGED_CLASS_IMPORT") if item is event else item
            for item in assessment.events
        ),
    )
    forged_scenario = replace(
        scenario,
        entry_assessments=tuple(
            forged_assessment if item is assessment else item
            for item in scenario.entry_assessments
        ),
    )
    component = evidence.components[0]
    subgraph = tuple(
        (name, tuple(sorted(graph.hard_edges[name])))
        for name in component.reachable_modules
    )
    forged_component = replace(
        component,
        evidence_token=_component_token(
            component.members, subgraph,
            component.source_signatures, forged_scenario,
        ),
    )
    forged = replace(
        evidence,
        components=(forged_component,),
        scenarios=replace(evidence.scenarios, components=(forged_scenario,)),
    )
    snapshot = _snapshot(root, index, graph)
    p0 = assess_index_bound_scc_models(
        graph.hard_edges, captured.source_fingerprints_by_module,
        snapshot, forged,
    )
    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
    p1b = assess_scc_source_bytes(
        graph.hard_edges, captured.source_fingerprints_by_module,
        snapshot, forged, sources,
    )
    assert p1b[0].reason == "MODEL_REPLAY_MISMATCH"


@pytest.mark.live
def test_p1d3_d1_official_isolated_full_receipt(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = write_synthetic_repository(tmp_path / "repo", D1_CLASS_SAFE)
    with _official_live(root, monkeypatch) as (client, server, identity, calls):
        _, result = ContextorFacade.analyze_project(
            str(root), cycle_source_preparation_preview=True,
            cycle_source_publication_opt_in=True,
        )
        assert result.cycle_source_preparation_preview.status == (
            "PREPARED_UNPUBLISHED_NON_ATOMIC"
        )
        state, metadata = _persisted(root)
        receipt = state.cycle_source_publication
        assert receipt.version == PUBLICATION_BINDING_VERSION
        assert receipt.prepared_manifest.version == MANIFEST_VERSION
        assert receipt.prepared_manifest.components[0].model_classification == (
            "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        )
        assert verify_co_published_cycle_manifest(
            state, revision=metadata.revision,
            state_id=metadata.state_id, repo_id=metadata.repo_id,
            root_path=metadata.root_path,
        )
        assert result.live_publish_status == "success"
        assert calls == [root.resolve()]


def _d2a_canonical_index_graph(root):
    index = index_repository(str(root))

    facts = materialize_reexport_facts_by_module(
        index.modules,
        index.reference_facts_by_module,
    )

    trie = build_trie(index.modules.keys())

    package_root = detect_package_root(
        index.modules,
        trie,
    )

    graph = build_graph(
        index.modules,
        trie=trie,
        package_root=package_root,
        reexport_facts_by_module=facts,
    )

    return index, graph


def _d2a_source_evidence(root):
    index, graph = _d2a_canonical_index_graph(
        root
    )
    _, captured = _captured(root, index, graph)
    parsed = {
        module: parse_source_snapshot(snapshot, module)
        for module, snapshot in captured.original_worker_source_snapshots.items()
    }
    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
    snapshot = _snapshot(root, index, graph)
    return index, graph, captured, parsed, evidence, snapshot


def _assert_d2b2_inactive_no_hard_scc(
    tmp_path, fixture, expected, expected_branch,
):
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    index, graph = _d2a_canonical_index_graph(root)
    assert graph.hard_edges == {
        "pkg.__init__": set(),
        "pkg.a": set(),
        "pkg.b": {"pkg.a"},
    }
    assert graph.soft_edges == {
        "pkg.__init__": set(),
        "pkg.a": {"pkg.b"},
        "pkg.b": set(),
    }

    imports_b = [
        item for item in index.modules["pkg.a"].imports
        if item.module == "pkg.b" and not item.is_from_import
    ]
    assert len(imports_b) == 1
    assert imports_b[0].type_only is True
    assert imports_b[0].is_local is False
    typing_imports = [
        item for item in index.modules["pkg.a"].imports
        if item.module == "typing"
    ]
    assert len(typing_imports) == 1
    assert typing_imports[0].type_only is False
    assert typing_imports[0].is_from_import is (fixture is D2B_NAME_SAFE)

    source_snapshots = {
        module_id: read_source_snapshot(Path(root, module.path))
        for module_id, module in index.modules.items()
    }
    parsed = {
        module_id: parse_source_snapshot(snapshot, module_id)
        for module_id, snapshot in source_snapshots.items()
    }
    source_trees = {
        module_id: source.tree
        for module_id, source in parsed.items()
    }
    guard = recognize_typing_guard(
        source_trees["pkg.a"],
        frozenset(index.modules),
    )
    assert guard is not None

    site_report = analyze_cyclic_import_sites(graph.hard_edges, parsed)
    assert not any(
        {"pkg.a", "pkg.b"}.issubset(set(component.members))
        for component in site_report.components
    )
    scenarios = analyze_cycle_scenarios(graph.hard_edges, source_trees)
    assert scenarios.components == ()

    for entry, succeeds in expected.items():
        modeled = evaluate_package_import_order(source_trees, entry)
        actual = run_synthetic_import(root, entry)
        assert (modeled.outcome == "MODEL_PASS") is succeeds
        assert (actual.returncode == 0) is succeeds
        if entry == "pkg.a":
            assert any(
                event.operation == "TYPING_MARKER_IMPORT"
                for event in modeled.events
            )
            assert not any(
                event.operation == "START_IMPORT"
                and event.target == "pkg.b"
                for event in modeled.events
            )

    assert expected_branch == "BODY"
    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
    assert evidence.components == ()
    snapshot = _snapshot(root, index, graph)
    p0 = assess_index_bound_scc_models(
        graph.hard_edges,
        index.source_fingerprints_by_module,
        snapshot,
        evidence,
    )
    assert p0 == ()
    plan = plan_original_worker_reindex(index, graph.hard_edges)
    assert plan.status == "UNAVAILABLE"
    assert plan.reason == "NO_CYCLIC_COMPONENTS"
    prepared = prepare_original_worker_cycle_manifest(
        index, graph.hard_edges, snapshot,
    )
    assert prepared.manifest is None
    assert prepared.status != "PREPARED_UNPUBLISHED_NON_ATOMIC"


def test_p1d3_d2a_active_initializer_chain_verified(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", D2A_ACTIVE_CHAIN)
    index, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
    assert {name: set(targets) for name, targets in graph.hard_edges.items()} == {
        "pkg.__init__": {"pkg.a"},
        "pkg.a": {"pkg.__init__", "pkg.b"},
        "pkg.b": {"pkg.__init__"},
    }
    closure = compute_cycle_model_source_closures(graph.hard_edges)
    assert len(closure) == 1
    assert closure[0].members == ("pkg.__init__", "pkg.a", "pkg.b")
    assert closure[0].evidence_source_modules == closure[0].members
    assert assess_package_graph_consistency(
        graph.hard_edges,
        {name: source.tree for name, source in parsed.items()},
        closure[0].evidence_source_modules,
    ).status == "CONSISTENT"
    scenario = evidence.scenarios.components[0]
    assert scenario.model_kind == "REGULAR_PACKAGE"
    assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    assert scenario.coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
    assert len(scenario.entry_assessments) == 3
    assert all(item.outcome == "MODEL_PASS" for item in scenario.entry_assessments)
    p0 = assess_index_bound_scc_models(
        graph.hard_edges, captured.source_fingerprints_by_module,
        snapshot, evidence,
    )
    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
    p1b = assess_scc_source_bytes(
        graph.hard_edges, captured.source_fingerprints_by_module,
        snapshot, evidence, captured.original_worker_source_snapshots,
    )
    assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
    for entry in ("pkg", "pkg.a", "pkg.b"):
        assert run_synthetic_import(root, entry).returncode == 0


def test_p1d3_d2a_canonical_reexport_edge_rule(
    tmp_path,
    isolated_dirs,
):
    root = write_synthetic_repository(
        tmp_path / "repo",
        D2A_ACTIVE_CHAIN,
    )

    index, graph = _d2a_canonical_index_graph(
        root
    )

    trees = {
        module: ast.parse(
            (root / item.path).read_text(
                encoding="utf-8"
            )
        )
        for module, item in index.modules.items()
    }

    closure = compute_cycle_model_source_closures(
        graph.hard_edges
    )

    assert len(closure) == 1

    members = closure[0].evidence_source_modules

    assert assess_package_graph_consistency(
        graph.hard_edges,
        trees,
        members,
    ).status == "CONSISTENT"

    assert graph.hard_edges["pkg.__init__"] == {
        "pkg.a"
    }

    assert graph.hard_edges["pkg.a"] == {
        "pkg.__init__",
        "pkg.b",
    }

    assert graph.hard_edges["pkg.b"] == {
        "pkg.__init__"
    }

    with_extra = {
        name: set(targets)
        for name, targets in graph.hard_edges.items()
    }

    with_extra["pkg.b"].add("pkg.a")

    result_extra = assess_package_graph_consistency(
        with_extra,
        trees,
        members,
    )

    assert result_extra.status == "INDETERMINATE"
    assert result_extra.reason == (
        "GRAPH_SOURCE_IMPORT_MISMATCH"
    )

    with_missing = {
        name: set(targets)
        for name, targets in graph.hard_edges.items()
    }

    with_missing["pkg.a"].remove("pkg.b")

    result_missing = assess_package_graph_consistency(
        with_missing,
        trees,
        members,
    )

    assert result_missing.status == "INDETERMINATE"
    assert result_missing.reason == (
        "GRAPH_SOURCE_IMPORT_MISMATCH"
    )

    with_missing_initializer = {
        name: set(targets)
        for name, targets in graph.hard_edges.items()
    }

    with_missing_initializer[
        "pkg.__init__"
    ].remove("pkg.a")

    result_initializer = (
        assess_package_graph_consistency(
            with_missing_initializer,
            trees,
            members,
        )
    )

    assert result_initializer.status == (
        "INDETERMINATE"
    )

    assert result_initializer.reason == (
        "GRAPH_SOURCE_IMPORT_MISMATCH"
    )


def test_p1d3_d2a_nested_initializer_import_does_not_suppress_child(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(tmp_path / "repo", {
        "pkg/__init__.py": "if True:\n    from . import a\n",
        "pkg/a.py": "from . import b\n",
        "pkg/b.py": "from . import a\n",
    })
    index, graph = _d2a_canonical_index_graph(root)
    trees = {
        module: ast.parse((root / item.path).read_text(encoding="utf-8"))
        for module, item in index.modules.items()
    }
    closure = compute_cycle_model_source_closures(graph.hard_edges)
    assert len(closure) == 1
    assert "pkg.a" in graph.hard_edges["pkg.b"]
    assert assess_package_graph_consistency(
        graph.hard_edges, trees, closure[0].evidence_source_modules,
    ).status == "CONSISTENT"


def test_p1d3_d2a_initializer_reordering(tmp_path, isolated_dirs):
    records = []
    for name, fixture in (("hazard", D2A_INITIALIZER_HAZARD),
                          ("safe", D2A_INITIALIZER_SAFE)):
        root = write_synthetic_repository(tmp_path / name, fixture)
        _, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
        closure = compute_cycle_model_source_closures(graph.hard_edges)
        assert closure[0].members == ("pkg.__init__", "pkg.a")
        assert assess_package_graph_consistency(
            graph.hard_edges,
            {module: source.tree for module, source in parsed.items()},
            closure[0].evidence_source_modules,
        ).status == "CONSISTENT"
        scenario = evidence.scenarios.components[0]
        assert scenario.classification == (
            "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
            if name == "hazard"
            else "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        )
        p0 = assess_index_bound_scc_models(
            graph.hard_edges, captured.source_fingerprints_by_module,
            snapshot, evidence,
        )
        assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
        p1b = assess_scc_source_bytes(
            graph.hard_edges, captured.source_fingerprints_by_module,
            snapshot, evidence, captured.original_worker_source_snapshots,
        )
        assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
        for entry in ("pkg", "pkg.a"):
            actual = run_synthetic_import(root, entry)
            assert (actual.returncode == 0) is (name == "safe")
            if name == "hazard":
                assert "AttributeError" in actual.stderr
        if name == "hazard":
            assert any(
                event.operation == "EARLY_BINDING_HAZARD"
                and event.target == "pkg"
                and event.symbol == "value"
                for assessment in scenario.entry_assessments
                for event in assessment.events
            )
        records.append((graph.hard_edges, evidence.components[0].evidence_token))
    assert records[0][0] == records[1][0]
    assert records[0][1] != records[1][1]


@pytest.mark.parametrize("initializer", [
    "from . import a as alias\n",
    "from . import a, a\n",
    "from . import missing\n",
    "import os\nfrom . import a\n",
    "from . import a\na = 1\n",
    "if unknown:\n    from . import a\n",
    "try:\n    from . import a\nexcept ImportError:\n    pass\n",
    "from . import a\nexec('unexpected')\n",
    "def __getattr__(name):\n    return None\nfrom . import a\n",
    "from . import a\nclass C:\n    pass\n",
])
def test_p1d3_d2a_initializer_restrictions(tmp_path, isolated_dirs, initializer):
    root = write_synthetic_repository(tmp_path / "repo", {
        "pkg/__init__.py": initializer,
        "pkg/a.py": "import pkg\nvalue = 1\n",
    })
    index, graph = _d2a_canonical_index_graph(root)
    trees = {
        name: ast.parse((root / module.path).read_text(encoding="utf-8"))
        for name, module in index.modules.items()
    }
    scenario = analyze_cycle_scenarios(graph.hard_edges, trees)
    assert all(
        item.classification != "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        for item in scenario.components
    )
    closure = compute_cycle_model_source_closures(graph.hard_edges)
    if closure:
        consistency = assess_package_graph_consistency(
            graph.hard_edges, trees, closure[0].evidence_source_modules,
        )
        assert consistency.status == "INDETERMINATE"
    plan = plan_original_worker_reindex(index, graph.hard_edges)
    if plan.status == "READY_FOR_REINDEX_NON_ATOMIC":
        captured = index_repository(str(root), source_capture_module_ids=plan.selected_module_ids)
        prepared = prepare_original_worker_cycle_manifest(
            captured, graph.hard_edges, _snapshot(root, index, graph),
        )
        assert prepared.manifest is None


def test_p1d3_d2a_literal_initializer_branches(tmp_path, isolated_dirs):
    records = []
    for name, literal in (("active", "True"), ("inactive", "False")):
        root = write_synthetic_repository(tmp_path / name, {
            "pkg/__init__.py": f"if {literal}:\n    from . import a\n",
            "pkg/a.py": "import pkg\n",
        })
        index, graph = _d2a_canonical_index_graph(root)
        trees = {
            module: ast.parse((root / item.path).read_text(encoding="utf-8"))
            for module, item in index.modules.items()
        }
        assert graph.hard_edges["pkg.__init__"] == {"pkg.a"}
        closure = compute_cycle_model_source_closures(graph.hard_edges)
        assert assess_package_graph_consistency(
            graph.hard_edges, trees, closure[0].evidence_source_modules,
        ).status == "CONSISTENT"
        scenario = analyze_cycle_scenarios(graph.hard_edges, trees).components[0]
        assert scenario.model_kind == "REGULAR_PACKAGE"
        assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        entry = next(item for item in scenario.entry_assessments if item.entry_module == "pkg")
        starts_child = any(
            event.operation == "START_IMPORT" and event.target == "pkg.a"
            for event in entry.events
        )
        assert starts_child is (literal == "True")
        assert run_synthetic_import(root, "pkg").returncode == 0
        records.append(graph.hard_edges)
    assert records[0] == records[1]


def test_p1d3_d2a_rejects_forged_graph(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", D2A_ACTIVE_CHAIN)
    index, graph = _d2a_canonical_index_graph(root)
    altered = {name: set(targets) for name, targets in graph.hard_edges.items()}
    altered["pkg.a"].remove("pkg.b")
    trees = {
        module: ast.parse((root / item.path).read_text(encoding="utf-8"))
        for module, item in index.modules.items()
    }
    result = analyze_cycle_scenarios(altered, trees)
    assert all(
        component.classification != "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        for component in result.components
    )
    assert all(
        component.reason in {
            "GRAPH_SOURCE_IMPORT_MISMATCH", "AMBIGUOUS_PACKAGE_TARGET",
            "MISSING_INDEXED_TARGET", "MISSING_OR_INVALID_SOURCE",
        }
        for component in result.components
    )
    assert graph.hard_edges["pkg.a"] == {"pkg.__init__", "pkg.b"}


def test_p1d3_d2a_original_worker_prepares_v2(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", D2A_ACTIVE_CHAIN)
    _, graph, captured, _, _, snapshot = _d2a_source_evidence(root)
    prepared = prepare_original_worker_cycle_manifest(
        captured, graph.hard_edges, snapshot,
    )
    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert prepared.manifest.version == "cycle-source-manifest/2"
    component = prepared.manifest.components[0]
    assert component.model_kind == "REGULAR_PACKAGE"
    assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    assert tuple(row[0] for row in component.source_signatures) == (
        "pkg.__init__", "pkg.a", "pkg.b",
    )
    assert component.model_evidence_sha256


def test_p1d3_d2a_forged_event_rejected_by_p1b(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", D2A_ACTIVE_CHAIN)
    _, graph, captured, _, evidence, snapshot = _d2a_source_evidence(root)
    scenario = evidence.scenarios.components[0]
    assessment = scenario.entry_assessments[0]
    event = next(item for item in assessment.events if item.operation in {"FROM", "FROM_REENTRANT_CHILD"})
    forged_assessment = replace(
        assessment,
        events=tuple(
            replace(item, operation="FORGED_D2A_IMPORT") if item is event else item
            for item in assessment.events
        ),
    )
    forged_scenario = replace(
        scenario,
        entry_assessments=(forged_assessment, *scenario.entry_assessments[1:]),
    )
    component = evidence.components[0]
    subgraph = tuple(
        (name, tuple(sorted(graph.hard_edges[name])))
        for name in component.reachable_modules
    )
    forged_component = replace(
        component,
        evidence_token=_component_token(
            component.members, subgraph, component.source_signatures, forged_scenario,
        ),
    )
    forged = replace(
        evidence,
        components=(forged_component,),
        scenarios=replace(evidence.scenarios, components=(forged_scenario,)),
    )
    p0 = assess_index_bound_scc_models(
        graph.hard_edges, captured.source_fingerprints_by_module,
        snapshot, forged,
    )
    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
    p1b = assess_scc_source_bytes(
        graph.hard_edges, captured.source_fingerprints_by_module,
        snapshot, forged, captured.original_worker_source_snapshots,
    )
    assert p1b[0].reason == "MODEL_REPLAY_MISMATCH"


@pytest.mark.live
def test_p1d3_d2a_official_isolated_full_receipt(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = write_synthetic_repository(tmp_path / "repo", D2A_ACTIVE_CHAIN)
    with _official_live(root, monkeypatch) as (client, server, identity, calls):
        _, result = ContextorFacade.analyze_project(
            str(root), cycle_source_preparation_preview=True,
            cycle_source_publication_opt_in=True,
        )
        assert result.cycle_source_preparation_preview.status == (
            "PREPARED_UNPUBLISHED_NON_ATOMIC"
        ), result.cycle_source_preparation_preview.reason
        state, metadata = _persisted(root)
        receipt = state.cycle_source_publication
        assert receipt.version == PUBLICATION_BINDING_VERSION
        assert receipt.prepared_manifest.version == MANIFEST_VERSION
        component = receipt.prepared_manifest.components[0]
        assert component.model_kind == "REGULAR_PACKAGE"
        assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        assert verify_co_published_cycle_manifest(
            state, revision=metadata.revision,
            state_id=metadata.state_id, repo_id=metadata.repo_id,
            root_path=metadata.root_path,
        )
        assert result.live_publish_status == "success"
        assert calls == [root.resolve()]


def _assert_p1d3_d2b_supported_fixture(
    tmp_path, isolated_dirs, fixture, expected, expected_branch,
):
    if fixture is D2B_NAME_SAFE or fixture is D2B_ATTR_SAFE:
        _assert_d2b2_inactive_no_hard_scc(
            tmp_path,
            fixture,
            expected,
            expected_branch,
        )
        return

    root = write_synthetic_repository(tmp_path / "repo", fixture)
    index, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
    assert graph.hard_edges == {
        "pkg.__init__": set(),
        "pkg.a": {"pkg.b"},
        "pkg.b": {"pkg.a"},
    }
    assert all(
        not getattr(item, "type_only", False)
        for item in index.modules["pkg.a"].imports
    )
    assert any(
        item.module == "pkg.b" and not getattr(item, "type_only", False)
        for item in index.modules["pkg.a"].imports
    )
    site_report = analyze_cyclic_import_sites(graph.hard_edges, parsed)
    site_edge = next(
        edge
        for edge in site_report.components[0].internal_edges
        if edge.source == "pkg.a" and edge.target == "pkg.b"
    )
    assert site_edge.status == "LEXICAL_CANDIDATES"
    assert site_edge.sites[0].controls[0].kind == "IF"
    assert site_edge.sites[0].controls[0].branch == expected_branch
    assert set(evidence.scenarios.components[0].members) == {"pkg.a", "pkg.b"}
    scenario = evidence.scenarios.components[0]
    assert scenario.model_kind == "REGULAR_PACKAGE"
    assert scenario.coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
    if fixture is D2B_ELSE_HAZARD:
        assert scenario.classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
    else:
        assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    guard = recognize_typing_guard(
        parsed["pkg.a"].tree,
        frozenset(index.modules),
    )
    assert guard is not None
    assert any(
        event.operation == "TYPING_MARKER_IMPORT"
        and event.target == "typing"
        and event.symbol == "TYPE_CHECKING"
        for assessment in scenario.entry_assessments
        for event in assessment.events
    )
    assessment_a = next(
        item for item in scenario.entry_assessments
        if item.entry_module == "pkg.a"
    )
    starts_b = any(
        event.operation == "START_IMPORT" and event.target == "pkg.b"
        for event in assessment_a.events
    )
    assert starts_b is any(
        fixture is candidate
        for candidate in (D2B_ELSE_HAZARD, D2B_ELSE_SAFE)
    )
    for entry, succeeds in expected.items():
        actual = run_synthetic_import(root, entry)
        assert (actual.returncode == 0) is succeeds
        modeled = next(
            item for item in scenario.entry_assessments
            if item.entry_module == entry
        )
        assert (modeled.outcome == "MODEL_PASS") is succeeds
        if fixture is D2B_ELSE_HAZARD and entry == "pkg.a":
            assert "partially initialized module" in actual.stderr
    p0 = assess_index_bound_scc_models(
        graph.hard_edges, captured.source_fingerprints_by_module,
        snapshot, evidence,
    )
    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
    p1b = assess_scc_source_bytes(
        graph.hard_edges, captured.source_fingerprints_by_module,
        snapshot, evidence, captured.original_worker_source_snapshots,
    )
    assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"


def test_p1d3_d2b_name_guard_inactive(tmp_path, isolated_dirs):
    _assert_p1d3_d2b_supported_fixture(
        tmp_path, isolated_dirs, D2B_NAME_SAFE,
        {"pkg.a": True, "pkg.b": True}, "BODY",
    )


def test_p1d3_d2b_attribute_guard_inactive(tmp_path, isolated_dirs):
    _assert_p1d3_d2b_supported_fixture(
        tmp_path, isolated_dirs, D2B_ATTR_SAFE,
        {"pkg.a": True, "pkg.b": True}, "BODY",
    )


def test_p1d3_d2b_else_activates_import(tmp_path, isolated_dirs):
    _assert_p1d3_d2b_supported_fixture(
        tmp_path, isolated_dirs, D2B_ELSE_HAZARD,
        {"pkg.a": False, "pkg.b": True}, "ELSE",
    )


def test_p1d3_d2b_else_reordered_safe(tmp_path, isolated_dirs):
    _assert_p1d3_d2b_supported_fixture(
        tmp_path, isolated_dirs, D2B_ELSE_SAFE,
        {"pkg.a": True, "pkg.b": True}, "ELSE",
    )


@pytest.mark.parametrize("name,source,extra", [
    ("N01-no-marker", "if TYPE_CHECKING:\n    import pkg.b\n", {}),
    ("N02-assigned-before", "TYPE_CHECKING = True\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
    ("N03-assigned-after", "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\nTYPE_CHECKING = True\n", {}),
    ("N04-aliased-name", "from typing import TYPE_CHECKING as TC\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
    ("N05-aliased-module", "import typing as t\nif typing.TYPE_CHECKING:\n    import pkg.b\n", {}),
    ("N06-not", "from typing import TYPE_CHECKING\nif not TYPE_CHECKING:\n    import pkg.b\n", {}),
    ("N07-is-false", "from typing import TYPE_CHECKING\nif TYPE_CHECKING is False:\n    import pkg.b\n", {}),
    ("N08-equals-false", "import typing\nif typing.TYPE_CHECKING == False:\n    import pkg.b\n", {}),
    ("N09-function-marker", "def load():\n    from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
    ("N10-class-marker", "class C:\n    from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
    ("N11-attribute-reassigned", "import typing\ntyping.TYPE_CHECKING = True\nif typing.TYPE_CHECKING:\n    import pkg.b\n", {}),
    ("N12-shadow-import", "from typing import TYPE_CHECKING\nfrom other import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
    ("N13-local-typing-module", D2B_NAME_SAFE["pkg/a.py"], {"typing.py": "pass\n"}),
    ("N14-local-typing-package", D2B_NAME_SAFE["pkg/a.py"], {"typing/__init__.py": "pass\n"}),
    ("N15-marker-after-import", "import pkg.b\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    pass\n", {}),
    ("N16-marker-conditional", "if True:\n    from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
    ("N17-marker-duplicated", "from typing import TYPE_CHECKING\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
    ("N18-nested-guard", "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    if TYPE_CHECKING:\n        import pkg.b\n", {}),
])
def test_p1d3_d2b_unsupported_typing_guards(
    tmp_path, isolated_dirs, name, source, extra,
):
    fixture = {
        "pkg/__init__.py": "pass\n",
        "pkg/a.py": source,
        "pkg/b.py": "from pkg.a import value\n",
        **extra,
    }
    root = write_synthetic_repository(tmp_path / name, fixture)
    index, graph = _d2a_canonical_index_graph(root)
    trees = {
        module: ast.parse((root / item.path).read_text(encoding="utf-8"))
        for module, item in index.modules.items()
    }
    assert recognize_typing_guard(
        trees["pkg.a"], frozenset(index.modules),
    ) is None
    scenarios = analyze_cycle_scenarios(graph.hard_edges, trees)
    assert all(
        component.classification != "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        for component in scenarios.components
    )
    plan = plan_original_worker_reindex(index, graph.hard_edges)
    if plan.status == "READY_FOR_REINDEX_NON_ATOMIC":
        captured = index_repository(
            str(root), source_capture_module_ids=plan.selected_module_ids,
        )
        prepared = prepare_original_worker_cycle_manifest(
            captured, graph.hard_edges, _snapshot(root, index, graph),
        )
        assert (
            prepared.manifest is None
            or prepared.manifest.source_manifest_sha256 is None
        )


def test_p1d3_d2b_original_worker_prepares_v2(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", D2B_ELSE_SAFE)
    index, graph, captured, _, evidence, snapshot = _d2a_source_evidence(root)
    prepared = prepare_original_worker_cycle_manifest(
        captured, graph.hard_edges, snapshot,
    )
    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert prepared.manifest.version == "cycle-source-manifest/2"
    component = prepared.manifest.components[0]
    assert component.model_kind == "REGULAR_PACKAGE"
    assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    assert tuple(row[0] for row in component.source_signatures) == (
        "pkg.__init__", "pkg.a", "pkg.b",
    )
    assert component.model_evidence_sha256


def test_p1d3_d2b_forged_marker_event_rejected(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B_ELSE_SAFE)
    _, graph, captured, _, evidence, snapshot = _d2a_source_evidence(root)
    scenario = evidence.scenarios.components[0]
    assessment = next(
        item for item in scenario.entry_assessments
        if any(event.operation == "TYPING_MARKER_IMPORT" for event in item.events)
    )
    event = next(
        item for item in assessment.events
        if item.operation == "TYPING_MARKER_IMPORT"
    )
    forged_assessment = replace(
        assessment,
        events=tuple(
            replace(item, operation="FORGED_TYPING_MARKER_IMPORT")
            if item is event else item
            for item in assessment.events
        ),
    )
    forged_scenario = replace(
        scenario,
        entry_assessments=tuple(
            forged_assessment if item is assessment else item
            for item in scenario.entry_assessments
        ),
    )
    component = evidence.components[0]
    subgraph = tuple(
        (module, tuple(sorted(graph.hard_edges[module])))
        for module in component.reachable_modules
    )
    forged_component = replace(
        component,
        evidence_token=_component_token(
            component.members, subgraph,
            component.source_signatures, forged_scenario,
        ),
    )
    forged = replace(
        evidence,
        components=(forged_component,),
        scenarios=replace(evidence.scenarios, components=(forged_scenario,)),
    )
    p0 = assess_index_bound_scc_models(
        graph.hard_edges, captured.source_fingerprints_by_module,
        snapshot, forged,
    )
    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
    p1b = assess_scc_source_bytes(
        graph.hard_edges, captured.source_fingerprints_by_module,
        snapshot, forged, captured.original_worker_source_snapshots,
    )
    assert p1b[0].reason == "MODEL_REPLAY_MISMATCH"


@pytest.mark.live
def test_p1d3_d2b_official_isolated_full_receipt(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B_ELSE_SAFE)
    with _official_live(root, monkeypatch) as (client, server, identity, calls):
        _, result = ContextorFacade.analyze_project(
            str(root), cycle_source_preparation_preview=True,
            cycle_source_publication_opt_in=True,
        )
        assert result.cycle_source_preparation_preview.status == (
            "PREPARED_UNPUBLISHED_NON_ATOMIC"
        )
        state, metadata = _persisted(root)
        receipt = state.cycle_source_publication
        assert receipt.version == PUBLICATION_BINDING_VERSION
        assert receipt.prepared_manifest.version == MANIFEST_VERSION
        component = receipt.prepared_manifest.components[0]
        assert component.model_kind == "REGULAR_PACKAGE"
        assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        assert verify_co_published_cycle_manifest(
            state, revision=metadata.revision,
            state_id=metadata.state_id, repo_id=metadata.repo_id,
            root_path=metadata.root_path,
        )
        assert result.live_publish_status == "success"
        assert calls == [root.resolve()]


def test_p1d3_d2b_else_source_order_changes_evidence_token(
    tmp_path, isolated_dirs,
):
    hazard_root = write_synthetic_repository(
        tmp_path / "hazard", D2B_ELSE_HAZARD,
    )
    safe_root = write_synthetic_repository(
        tmp_path / "safe", D2B_ELSE_SAFE,
    )
    _, hazard_graph, _, _, hazard_evidence, _ = _d2a_source_evidence(
        hazard_root,
    )
    _, safe_graph, _, _, safe_evidence, _ = _d2a_source_evidence(
        safe_root,
    )
    assert hazard_graph.hard_edges == safe_graph.hard_edges
    assert hazard_evidence.components[0].evidence_token != (
        safe_evidence.components[0].evidence_token
    )


def test_p1d3_d2b2_active_import_dominates_type_only(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(
        tmp_path / "repo", D2B2_MIXED_ACTIVE,
    )
    index, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
    imports_b = [
        item for item in index.modules["pkg.a"].imports
        if item.module == "pkg.b" and not item.is_from_import
    ]
    assert len(imports_b) == 2
    assert [item.type_only for item in imports_b] == [True, False]
    assert graph.hard_edges["pkg.a"] == {"pkg.b"}
    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
    assert graph.soft_edges["pkg.a"] == {"pkg.b"}
    assert captured.original_worker_capture_status == (
        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
    )

    captured_reexport_facts = materialize_reexport_facts_by_module(
        captured.modules,
        captured.reference_facts_by_module,
    )
    captured_trie = build_trie(captured.modules.keys())
    captured_package_root = detect_package_root(
        captured.modules,
        captured_trie,
    )
    captured_graph = build_graph(
        captured.modules,
        trie=captured_trie,
        package_root=captured_package_root,
        reexport_facts_by_module=captured_reexport_facts,
    )
    assert captured_graph.hard_edges == graph.hard_edges
    assert captured_graph.soft_edges == graph.soft_edges
    assert captured.modules["pkg.a"].imports == index.modules["pkg.a"].imports

    scenario = evidence.scenarios.components[0]
    assert scenario.classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
    assert scenario.coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
    assessment_a = next(
        item for item in scenario.entry_assessments
        if item.entry_module == "pkg.a"
    )
    assessment_b = next(
        item for item in scenario.entry_assessments
        if item.entry_module == "pkg.b"
    )
    assert assessment_a.outcome == "EARLY_BINDING_HAZARD"
    assert assessment_b.outcome == "MODEL_PASS"
    actual_a = run_synthetic_import(root, "pkg.a")
    actual_b = run_synthetic_import(root, "pkg.b")
    assert actual_a.returncode != 0
    assert "partially initialized module" in actual_a.stderr
    assert actual_b.returncode == 0

    p0 = assess_index_bound_scc_models(
        graph.hard_edges,
        captured.source_fingerprints_by_module,
        snapshot,
        evidence,
    )
    assert len(p0) == 1
    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
    p1b = assess_scc_source_bytes(
        graph.hard_edges,
        captured.source_fingerprints_by_module,
        snapshot,
        evidence,
        captured.original_worker_source_snapshots,
    )
    assert len(p1b) == 1
    assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"


@pytest.mark.live
def test_p1d3_d2b2_dissolved_scc_does_not_publish_receipt(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
    with _official_live(root, monkeypatch):
        _, result = ContextorFacade.analyze_project(
            str(root), cycle_source_preparation_preview=True,
            cycle_source_publication_opt_in=True,
        )
        state, _ = _persisted(root)
        preview = result.cycle_source_preparation_preview
        assert preview is None or preview.manifest is None
        assert getattr(state, "cycle_source_publication", None) is None

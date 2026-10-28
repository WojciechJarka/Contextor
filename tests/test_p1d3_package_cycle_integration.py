"""P1D3-B/C package SCC evidence through real isolated index and store paths."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from contextor.core.api.facade import ContextorFacade
from contextor.core.cycle_semantics.evidence import (
    _component_token,
    _digest,
    assess_index_bound_scc_models,
    build_source_bound_cycle_evidence,
)
from contextor.core.cycle_semantics.generation_manifest import MANIFEST_VERSION
from contextor.core.cycle_semantics.initialization_model import ImportOrderAssessment
from contextor.core.cycle_semantics.materialization import materialize_cycle_semantics
from contextor.core.cycle_semantics.model_identity import (
    indexed_to_logical_module,
    logical_to_indexed_module,
)
from contextor.core.cycle_semantics.model_source_closure import compute_cycle_model_source_closures
from contextor.core.cycle_semantics.original_worker_preparation import prepare_original_worker_cycle_manifest
from contextor.core.cycle_semantics.original_worker_reindex_planning import plan_original_worker_reindex
from contextor.core.cycle_semantics.publication_binding import (
    PUBLICATION_BINDING_VERSION,
    seal_prepared_cycle_manifest,
    verify_co_published_cycle_manifest,
)
from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
from contextor.core.cycle_semantics.source_proof import assess_scc_source_bytes
from contextor.core.graph.graph import build_graph
from contextor.core.source import parse_source_snapshot
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

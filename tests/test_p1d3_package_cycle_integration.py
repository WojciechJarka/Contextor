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
    broken["pkg.a"].remove("pkg.b")
    trees = {
        name: parse_source_snapshot(
            index_repository(str(root), source_capture_module_ids=frozenset(index.modules))
            .original_worker_source_snapshots[name], name,
        ).tree
        for name in index.modules
    }
    report = analyze_cycle_scenarios(broken, trees)
    assert all(c.classification == "INDETERMINATE" for c in report.components)


def test_p1b_replay_rejects_forged_event(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", F3)
    index, graph = _indexed(root)
    _, captured = _captured(root, index, graph)
    sources = captured.original_worker_source_snapshots
    parsed = {name: parse_source_snapshot(snapshot, name) for name, snapshot in sources.items()}
    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
    scenario = evidence.scenarios.components[0]
    assessment = scenario.entry_assessments[0]
    assert assessment.outcome == "EARLY_BINDING_HAZARD"
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

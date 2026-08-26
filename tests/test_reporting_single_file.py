import pytest
from contextor.core.reporting_layer.reporting_single_file import generate_single_file_report

def test_single_file_report_header_and_node_id(tmp_path):
    ctx = {
        "module_id": "core.alpha", 
        "file_path": "test.py",
        "symbol_context": {
            "symbols": [],
            "all_symbols": [],
            "ecosystem": {},
            "references": {},
            "consumer_summary": {},
            "consumers": {
                "core.alpha::Engine": {"consumer_count": 5},
                "core.alpha::unused": {"consumer_count": 0}
            },
            "usage": {},
            "global_node_id": "core.alpha"
        },
        "export_context": {
            "exports": [], 
            "export_summary": {},
            "unused_candidates": []
        },
        "public_api": [],
        "symbol_activity": {},
        "activity_summary": {},
        "artifact_consumption": {},
        "api_surface": {},
        "import_users": {},
        "import_context": {
            "imports": [],
            "import_summary": {}
        },
        "architecture_context": {
            "graph_metrics": {},
            "cycles": []
        },
        "semantic_context": {
            "semantic_analysis": {}
        },
        "module_intent": {},
        "test_context": {}
    }
    
    header = {"schema_version": "1.0"}
    from contextor.core.reporting_engine.dictionary import IndexDictionary
    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        index_dict = IndexDictionary(registry)
        report = generate_single_file_report(ctx, module_count=10, report_header=header, index_dict=index_dict)
    
    assert report["report_header"]["data_source"] == "single_file"
    assert report["report_header"]["schema_version"] == "1.0"
    assert report["repository_context"]["artifact_count_in_module"] == 1
    assert isinstance(report["global_node_id"], str)


def test_single_file_report_uses_global_qualified_symbol_identities(tmp_path):
    ctx = {
        "module_id": "pkg.alpha",
        "file_path": "pkg/alpha.py",
        "symbol_context": {
            "symbols": {"classes": ["Engine"], "functions": [], "methods": [], "globals": []},
            "all_symbols": ["Engine"],
            "ecosystem": {"Engine": ["tests.test_alpha"]},
            "references": {},
            "consumer_summary": {"total_symbols": 1},
            "consumers": {"Engine": {"consumers": ["tests.test_alpha"], "usage": {"api_imports": ["tests.test_alpha"]}}},
            "usage": {"Engine": ["tests.test_alpha"]},
        },
        "export_context": {"exports": {"symbols": ["Engine"]}, "export_summary": {}, "unused_candidates": []},
        "public_api": ["Engine"],
        "symbol_activity": {},
        "activity_summary": {},
        "artifact_consumption": {
            "symbols": {
                "Engine": {
                    "import": {"modules": ["tests.test_alpha"], "evidence_type": "ast_import_statements"},
                    "risk_score": 0.2,
                }
            },
            "consumers": {},
        },
        "api_surface": {"surface": {"Engine": {"kind": "class"}}, "metadata": {}},
        "import_users": ["tests.test_alpha"],
        "import_context": {"imports": {"internal": [], "external": [], "local": [], "global": []}},
        "architecture_context": {"graph_metrics": {}, "cycles": [], "imported_by": ["tests.test_alpha"]},
        "semantic_context": {"semantic_analysis": {}},
        "module_intent": {},
        "test_context": {},
    }

    from contextor.core.reporting_engine.dictionary import IndexDictionary
    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry.get_module_id("pkg.alpha")
        registry.get_module_id("tests.test_alpha")
        index_dict = IndexDictionary(registry)
        report = generate_single_file_report(ctx, module_count=2, index_dict=index_dict)

    artifact_id = report["symbols"][0]
    assert registry.get_artifact_name(artifact_id) == "pkg.alpha::Engine"
    assert list(report["artifact_consumption"]["symbols"]) == [artifact_id]
    assert report["artifact_consumption"]["symbols"][artifact_id]["definer_module"] == report["module_id"]
    assert report["artifact_consumption"]["symbols"][artifact_id]["kind"] == "class"
    assert registry.get_module_id(None) is None


def test_single_file_report_does_not_register_report_categories_as_identities(tmp_path):
    ctx = {
        "module_id": "pkg.empty",
        "file_path": "pkg/empty.py",
        "symbol_context": {
            "symbols": {"classes": [], "functions": [], "methods": [], "globals": []},
            "all_symbols": [], "ecosystem": {}, "references": {}, "consumer_summary": {}, "consumers": {}, "usage": {},
        },
        "export_context": {"exports": {"symbols": [], "functions": [], "classes": [], "constants": [], "aliases": []}, "export_summary": {}, "unused_candidates": []},
        "public_api": [], "symbol_activity": {}, "activity_summary": {}, "artifact_consumption": {},
        "api_surface": {"surface": {}, "metadata": {"visibility": "internal"}},
        "import_users": [],
        "import_context": {"imports": {"internal": [], "external": ["pathlib"], "local": [], "global": ["pathlib"]}},
        "architecture_context": {"graph_metrics": {}, "cycles": []},
        "semantic_context": {"semantic_analysis": {"import_usage": {}, "mutability": {}}},
        "module_intent": {}, "test_context": {},
    }

    from contextor.core.reporting_engine.dictionary import IndexDictionary
    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        index_dict = IndexDictionary(registry)
        report = generate_single_file_report(ctx, module_count=1, index_dict=index_dict)

    registered = set(registry._state["artifact_registry"]["path_to_id"])
    assert registered.isdisjoint({"classes", "functions", "surface", "metadata", "import_usage", "mutability"})
    assert report["imports"]["external"] == ["pathlib"]


def test_grouped_api_surface_registers_real_symbols_only(tmp_path):
    ctx = {
        "module_id": "pkg.module",
        "file_path": "pkg/module.py",
        "symbol_context": {
            "symbols": {"classes": ["Engine"], "functions": ["run"], "methods": [], "globals": []},
            "all_symbols": ["Engine", "run"],
            "ecosystem": {}, "references": {}, "consumer_summary": {}, "consumers": {}, "usage": {},
        },
        "export_context": {"exports": {"symbols": []}, "export_summary": {}, "unused_candidates": []},
        "public_api": ["Engine", "run"], "symbol_activity": {}, "activity_summary": {},
        "artifact_consumption": {},
        "api_surface": {"surface": {
            "functions": {"run": {"kind": "function"}},
            "methods": {},
            "classes": {"Engine": {"kind": "class"}},
        }},
        "import_users": [], "import_context": {"imports": {}},
        "architecture_context": {"graph_metrics": {}, "cycles": []},
        "semantic_context": {"semantic_analysis": {}}, "module_intent": {}, "test_context": {},
    }

    from contextor.core.reporting_engine.dictionary import IndexDictionary
    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        report = generate_single_file_report(ctx, 1, index_dict=IndexDictionary(registry))

    registered = set(registry._state["artifact_registry"]["path_to_id"])
    assert "pkg.module::run" in registered
    assert "pkg.module::Engine" in registered
    assert "pkg.module::functions" not in registered
    assert "pkg.module::methods" not in registered
    assert "pkg.module::classes" not in registered
    assert len(report["api_surface"]) == 2


def test_single_file_report_exposes_imported_by_as_hard_dependents(tmp_path):
    ctx = {
        "module_id": "pkg.alpha", "file_path": "pkg/alpha.py",
        "symbol_context": {"symbols": {}, "all_symbols": [], "ecosystem": {}, "references": {}, "consumer_summary": {}, "consumers": {}, "usage": {}},
        "export_context": {"exports": {"symbols": []}, "export_summary": {}, "unused_candidates": []},
        "public_api": [], "symbol_activity": {}, "activity_summary": {}, "artifact_consumption": {}, "api_surface": {},
        "import_users": [], "import_context": {"imports": {}},
        "architecture_context": {"graph_metrics": {}, "cycles": [], "imported_by": ["tests.test_alpha"], "soft_imported_by": ["pkg.soft"]},
        "semantic_context": {"semantic_analysis": {}}, "module_intent": {}, "test_context": {},
    }

    from contextor.core.reporting_engine.dictionary import IndexDictionary
    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        index_dict = IndexDictionary(registry)
        report = generate_single_file_report(ctx, module_count=3, index_dict=index_dict)

    assert report["architecture"]["hard_dependents"] == [index_dict.get_module_id("tests.test_alpha")]
    assert report["architecture"]["soft_dependents"] == [index_dict.get_module_id("pkg.soft")]


def _setup_sample_repo_state(tmp_path):
    from contextor.core.api.facade import ContextorFacade
    from contextor.core.live_state.hydration import hydrate_repository_engine

    pkg = tmp_path / "pkg"
    pkg.mkdir(exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    alpha_code = "def compute(x):\n    return x + 1\ndef helper():\n    return 42\nclass Worker:\n    pass\n"
    (pkg / "alpha.py").write_text(alpha_code, encoding="utf-8")
    (pkg / "beta.py").write_text(
        "from pkg.alpha import compute, Worker\ndef execute():\n    w = Worker()\n    return compute(42)\n",
        encoding="utf-8",
    )
    (pkg / "gamma.py").write_text("def helper():\n    return 'gamma'\n", encoding="utf-8")

    ContextorFacade.analyze_project(str(tmp_path))
    hydrated = hydrate_repository_engine(str(tmp_path))
    real_state = hydrated.engine.state
    modules = real_state.modules
    graph = real_state.dependency_graph

    alpha_mod = modules["pkg.alpha"]
    file_path = str(pkg / "alpha.py")

    return modules, graph, real_state, alpha_mod, file_path, alpha_code


def test_symbol_context_canonical_backed_fields_match_legacy(tmp_path):
    from contextor.core.single_file.builders.layer0_builders import SymbolContextBuilder
    from contextor.core.single_file.builders.registry import ContextPayload, BuildState

    modules, graph, real_state, alpha_mod, file_path, alpha_code = _setup_sample_repo_state(tmp_path)

    legacy_payload = ContextPayload(
        file_path=file_path,
        module_id="pkg.alpha",
        modules=modules,
        root_path=str(tmp_path),
        module=alpha_mod,
        tree=alpha_mod.ast_tree,
        source=alpha_code,
        project_graph=graph,
        engine_state=None,
    )

    canonical_payload = ContextPayload(
        file_path=file_path,
        module_id="pkg.alpha",
        modules=modules,
        root_path=str(tmp_path),
        module=alpha_mod,
        tree=alpha_mod.ast_tree,
        source=alpha_code,
        project_graph=graph,
        engine_state=real_state,
    )

    builder = SymbolContextBuilder()
    legacy = builder.build(legacy_payload, BuildState())["symbol_context"]
    canonical = builder.build(canonical_payload, BuildState())["symbol_context"]

    assert canonical["symbols"] == legacy["symbols"]
    assert canonical["all_symbols"] == legacy["all_symbols"]
    assert canonical["usage"] == legacy["usage"]
    assert canonical["ecosystem"] == legacy["ecosystem"]
    assert canonical["references"] == legacy["references"]
    assert canonical["consumers"] == legacy["consumers"]
    assert canonical["consumer_summary"] == legacy["consumer_summary"]


def test_promoted_fields_bypass_legacy_extractors(tmp_path):
    from unittest.mock import patch
    from contextor.core.single_file.builders.layer0_builders import SymbolContextBuilder
    from contextor.core.single_file.builders.registry import ContextPayload, BuildState

    modules, graph, real_state, alpha_mod, file_path, alpha_code = _setup_sample_repo_state(tmp_path)

    canonical_payload = ContextPayload(
        file_path=file_path,
        module_id="pkg.alpha",
        modules=modules,
        root_path=str(tmp_path),
        module=alpha_mod,
        tree=alpha_mod.ast_tree,
        source=alpha_code,
        project_graph=graph,
        engine_state=real_state,
    )

    builder = SymbolContextBuilder()
    with (
        patch("contextor.core.symbol_engine.extract_file_symbols") as extract_symbols,
        patch("contextor.core.symbol_engine.find_symbol_usage") as find_usage,
        patch("contextor.core.symbol_engine.build_symbol_index") as build_index,
        patch("contextor.core.reference.engine.build_symbol_references", wraps=__import__("contextor.core.reference.engine", fromlist=["build_symbol_references"]).build_symbol_references) as spy_refs,
    ):
        result = builder.build(canonical_payload, BuildState())

        extract_symbols.assert_not_called()
        find_usage.assert_not_called()
        build_index.assert_not_called()
        spy_refs.assert_called_once()

    assert "compute" in result["symbol_context"]["all_symbols"]


def test_freshness_gating_regressions(tmp_path):
    from unittest.mock import patch
    from contextor.core.single_file.builders.layer0_builders import (
        SymbolContextBuilder,
        ArchitectureContextBuilder,
    )
    from contextor.core.single_file.builders.registry import ContextPayload, BuildState

    modules, graph, real_state, alpha_mod, file_path, alpha_code = _setup_sample_repo_state(tmp_path)

    # 1. Stale module parse -> extract_file_symbols must be called
    real_state.module_parse_freshness["pkg.alpha"] = {"state": "stale"}
    builder = SymbolContextBuilder()

    payload_stale_module = ContextPayload(
        file_path=file_path,
        module_id="pkg.alpha",
        modules=modules,
        root_path=str(tmp_path),
        module=alpha_mod,
        tree=alpha_mod.ast_tree,
        source=alpha_code,
        project_graph=graph,
        engine_state=real_state,
    )

    with patch("contextor.core.symbol_engine.extract_file_symbols") as mock_extract:
        mock_extract.return_value = {"classes": [], "functions": [], "methods": [], "globals": []}
        builder.build(payload_stale_module, BuildState())
        mock_extract.assert_called_once()

    # Reset module freshness to fresh
    real_state.module_parse_freshness.pop("pkg.alpha", None)

    # 2. Stale consumption -> find_symbol_usage must be called
    real_state.artifact_consumption_state = "stale"
    with patch("contextor.core.symbol_engine.find_symbol_usage") as mock_find:
        mock_find.return_value = {}
        builder.build(payload_stale_module, BuildState())
        mock_find.assert_called_once()

    # 3. Cycles: fresh vs stale
    arch_builder = ArchitectureContextBuilder()
    real_state.cycles_state = "fresh"
    real_state.cycles = [["pkg.alpha", "pkg.beta", "pkg.alpha"]]
    with patch("contextor.core.graph.cycles.detect_cycles") as mock_cycles:
        res_arch = arch_builder.build(payload_stale_module, BuildState())["architecture_context"]
        mock_cycles.assert_not_called()
        assert res_arch["cycles"] == [["pkg.alpha", "pkg.beta", "pkg.alpha"]]

    real_state.cycles_state = "stale"
    with patch("contextor.core.graph.cycles.detect_cycles") as mock_cycles:
        mock_cycles.return_value = []
        arch_builder.build(payload_stale_module, BuildState())
        mock_cycles.assert_called_once()

    # 4. Collisions: fresh vs stale
    real_state.collisions_state = "fresh"
    real_state.collisions = ["collision warning for pkg.alpha"]
    with patch("contextor.core.validator.collisions.validate_name_collisions") as mock_collisions:
        res_arch = arch_builder.build(payload_stale_module, BuildState())["architecture_context"]
        mock_collisions.assert_not_called()
        assert res_arch["name_collisions"] == ["collision warning for pkg.alpha"]

    real_state.collisions_state = "stale"
    with patch("contextor.core.validator.collisions.validate_name_collisions") as mock_collisions:
        mock_collisions.return_value = []
        arch_builder.build(payload_stale_module, BuildState())
        mock_collisions.assert_called_once()


def test_stale_other_module_disappears_from_ecosystem(tmp_path):
    from contextor.core.single_file.builders.layer0_builders import SymbolContextBuilder
    from contextor.core.single_file.builders.registry import ContextPayload, BuildState

    modules, graph, real_state, alpha_mod, file_path, alpha_code = _setup_sample_repo_state(tmp_path)

    canonical_payload = ContextPayload(
        file_path=file_path,
        module_id="pkg.alpha",
        modules=modules,
        root_path=str(tmp_path),
        module=alpha_mod,
        tree=alpha_mod.ast_tree,
        source=alpha_code,
        project_graph=graph,
        engine_state=real_state,
    )

    builder = SymbolContextBuilder()
    res1 = builder.build(canonical_payload, BuildState())["symbol_context"]
    assert sorted(res1["ecosystem"]["helper"]) == ["pkg.alpha", "pkg.gamma"]

    # Mark gamma stale
    real_state.module_parse_freshness["pkg.gamma"] = {"state": "stale"}
    res2 = builder.build(canonical_payload, BuildState())["symbol_context"]
    assert "pkg.gamma" not in res2["ecosystem"].get("helper", [])
    assert "pkg.alpha" in res2["ecosystem"]["helper"]


def test_global_report_cycles_must_not_override_stale_canonical_state(tmp_path):
    from unittest.mock import patch
    from contextor.core.single_file.builders.layer0_builders import ArchitectureContextBuilder
    from contextor.core.single_file.builders.registry import ContextPayload, BuildState

    modules, graph, real_state, alpha_mod, file_path, alpha_code = _setup_sample_repo_state(tmp_path)

    real_state.cycles_state = "stale"
    payload_stale_cycles = ContextPayload(
        file_path=file_path,
        module_id="pkg.alpha",
        modules=modules,
        root_path=str(tmp_path),
        module=alpha_mod,
        tree=alpha_mod.ast_tree,
        source=alpha_code,
        project_graph=graph,
        global_report={"cycles": [["FAKE", "STALE", "FAKE"]]},
        engine_state=real_state,
    )
    arch_builder = ArchitectureContextBuilder()
    with patch("contextor.core.graph.cycles.detect_cycles") as mock_cycles:
        mock_cycles.return_value = []
        arch_res = arch_builder.build(payload_stale_cycles, BuildState())["architecture_context"]
        mock_cycles.assert_called_once()
        assert arch_res["cycles"] == []


def test_collision_filter_parity(tmp_path):
    from types import SimpleNamespace
    from unittest.mock import patch
    from contextor.core.single_file.builders.layer0_builders import ArchitectureContextBuilder
    from contextor.core.single_file.builders.registry import ContextPayload, BuildState

    modules, graph, real_state, alpha_mod, file_path, alpha_code = _setup_sample_repo_state(tmp_path)

    canonical_payload = ContextPayload(
        file_path=file_path,
        module_id="pkg.alpha",
        modules=modules,
        root_path=str(tmp_path),
        module=alpha_mod,
        tree=alpha_mod.ast_tree,
        source=alpha_code,
        project_graph=graph,
        engine_state=real_state,
    )

    fake_collision = SimpleNamespace(nodes=["pkg/alpha", "other.module"], message="alpha collision")
    arch_builder = ArchitectureContextBuilder()

    real_state.collisions_state = "fresh"
    real_state.collisions = [fake_collision]
    canonical_collisions = arch_builder.build(canonical_payload, BuildState())["architecture_context"]["name_collisions"]
    assert canonical_collisions == ["alpha collision"]

    real_state.collisions_state = "stale"
    with patch("contextor.core.validator.collisions.validate_name_collisions") as mock_validate:
        mock_validate.return_value = [fake_collision]
        fallback_collisions = arch_builder.build(canonical_payload, BuildState())["architecture_context"]["name_collisions"]
        mock_validate.assert_called_once()
        assert fallback_collisions == ["alpha collision"]

    assert canonical_collisions == fallback_collisions

    # Path-form string collision
    real_state.collisions_state = "fresh"
    real_state.collisions = [
        "collision warning: pkg/alpha"
    ]
    res_path_str = arch_builder.build(canonical_payload, BuildState())["architecture_context"]
    assert res_path_str["name_collisions"] == [
        "collision warning: pkg/alpha"
    ]

    # Dotted string collision
    real_state.collisions = [
        "collision warning for pkg.alpha"
    ]
    res_dot_str = arch_builder.build(canonical_payload, BuildState())["architecture_context"]
    assert res_dot_str["name_collisions"] == [
        "collision warning for pkg.alpha"
    ]

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

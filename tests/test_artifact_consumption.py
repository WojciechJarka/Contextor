import pytest
from contextor.core.reporting_layer.artifact_consumption import (
    build_module_consumption,
    build_symbol_consumption,
)

def test_build_module_consumption_evidence_types():
    consumers = {
        "core.alpha::Engine": {
            "usage": {
                "direct_calls": ["ui.app"],
                "api_imports": ["core.beta"],
                "runtime_calls": ["scripts.runner"]
            }
        }
    }
    
    imports = {"internal": ["core.beta"]}
    imported_by = ["ui.app", "core.beta", "external.system"]
    public_api = ["core.alpha::Engine"]
    activity = {"live": 1, "live_callback": 0, "unused_internal": 0, "unused_public": 0}
    
    module_cons, coupling = build_module_consumption(
        consumers, imports, imported_by, public_api, activity, exposure={}
    )
    
    assert module_cons["direct"]["evidence_type"] == "ast_call_graph"
    assert module_cons["direct"]["modules"] == ["ui.app"]
    
    assert module_cons["import"]["evidence_type"] == "ast_import_statements"
    assert module_cons["import"]["modules"] == ["core.beta"]
    
    assert module_cons["runtime"]["evidence_type"] == "ast_dynamic_getattr"
    assert module_cons["runtime"]["modules"] == ["scripts.runner"]
    
    assert module_cons["transitive"]["evidence_type"] == "module_level_dependency"
    assert module_cons["transitive"]["modules"] == ["external.system"]

def test_build_symbol_consumption_evidence_types():
    symbols = ["core.alpha::Engine"]
    consumers = {
        "core.alpha::Engine": {
            "usage": {
                "direct_calls": ["ui.app"],
                "api_imports": ["core.beta"]
            }
        }
    }
    exposure = {
        "core.alpha::Engine": {
            "reflection": ["getattr(..., 'Engine')"],
            "serialization": [],
            "cli_exposure": True,
            "api_exposure": False,
        }
    }
    
    sym_cons = build_symbol_consumption(
        symbols, consumers, symbol_activity={}, exposure=exposure, module_transitive=["external.system"]
    )
    
    engine = sym_cons["core.alpha::Engine"]
    
    assert engine["direct"]["evidence_type"] == "ast_call_graph"
    assert engine["direct"]["modules"] == ["ui.app"]
    
    assert engine["blast_radius_modules"]["evidence_type"] == "module_level_dependency"
    assert engine["blast_radius_modules"]["modules"] == ["external.system"]
    
    assert engine["reflection"]["evidence_type"] == "regex_string_match_in_getattr"
    assert engine["reflection"]["matches"] == ["getattr(..., 'Engine')"]
    
    assert engine["cli_exposure"]["evidence_type"] == "ast_decorator_pattern"
    assert engine["cli_exposure"]["detected"] is True

import pytest
from contextor.core.reporting_layer.reporting_single_file import generate_single_file_report

def test_single_file_report_header_and_node_id(tmp_path):
    ctx = {
        "module_id": "core.alpha", 
        "file_path": "test.py",
        "symbol_context": {
            "symbols": [],
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

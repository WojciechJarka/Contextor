import os
import json
from contextor.core.reporting_engine.header import build_report_header
from contextor.core.reporting_engine.io_manager import write_layer_reports, write_global_reports, _save_index_dictionary_with_dedup

def test_build_report_header_fallback(tmp_path):
    header = build_report_header(str(tmp_path), "global")
    assert header["schema_version"] == "1.0"
    assert "generated_at" in header
    assert header["data_source"] == "global"
    assert header["commit_sha"] is None
    assert header["branch"] is None

def test_write_layer_reports(tmp_path, monkeypatch):
    layer_reports = {
        "summary": {"status": "ok", "layer_module_count": 5},
        "structure": {"hard_edges": []},
        "metrics": {"density": 0.5},
        "artifacts_compact": {"artifact_count": 10},
        "graph_analytics": {"fan_in": 1}
    }
    
    layer_output_dir = "integration_test_layer"
    
    def mock_resolve_report_path(path):
        return os.path.join(str(tmp_path), path)
        
    monkeypatch.setattr("contextor.core.reporting_engine.formatting.resolve_report_path", mock_resolve_report_path)
    
    write_layer_reports(
        repo_name="test_repo",
        layer_name="test_layer",
        layer_reports=layer_reports,
        log=None,
        datestamp="2026",
        layer_output_dir=layer_output_dir
    )
    
    # Verify files were created
    expected_dir = os.path.join(str(tmp_path), "output", layer_output_dir)
    assert os.path.isdir(expected_dir)
    
    summary_path = os.path.join(expected_dir, "test_repo_test_layer_summary_2026.json")
    assert os.path.isfile(summary_path)
    
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["status"] == "ok"
        assert data["layer_module_count"] == 5

def test_save_index_dictionary_with_dedup(tmp_path, monkeypatch):
    def mock_resolve_report_path(path):
        return os.path.join(str(tmp_path), path)
    monkeypatch.setattr("contextor.core.reporting_engine.formatting.resolve_report_path", mock_resolve_report_path)
    
    # Initial write
    dict1 = {"modules": {"A": 1}}
    path = os.path.join(str(tmp_path), "repo_index_dictionary_2026_01.json")
    _save_index_dictionary_with_dedup(dict1, path)
    assert os.path.exists(path)
    
    # Write identical dict
    dict2 = {"modules": {"A": 1}}
    path2 = os.path.join(str(tmp_path), "repo_index_dictionary_2026_02.json")
    _save_index_dictionary_with_dedup(dict2, path2)
    assert os.path.exists(path2)
    assert not os.path.exists(path) # Old one was deleted
    
    # Write different dict
    dict3 = {"modules": {"B": 2}}
    path3 = os.path.join(str(tmp_path), "repo_index_dictionary_2026_03.json")
    _save_index_dictionary_with_dedup(dict3, path3)
    assert os.path.exists(path3)
    
    # The previous one should be marked as outdated
    outdated_path = os.path.join(str(tmp_path), "repo_index_dictionary_2026_02_outdated.json")
    assert os.path.exists(outdated_path)

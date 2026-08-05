import os
import json
from contextor.core.reporting_engine.io_manager import (
    _build_report_header,
    save_layer_reports,
)

def test_build_report_header_fallback(tmp_path):
    header = _build_report_header(str(tmp_path), "global")
    assert header["schema_version"] == "1.0"
    assert "generated_at" in header
    assert header["data_source"] == "global"
    assert header["commit_sha"] is None
    assert header["branch"] is None

def test_save_layer_reports_integration(tmp_path, monkeypatch):
    # Prepare dummy data for save_layer_reports
    layer_reports = {
        "summary": {"status": "ok", "layer_module_count": 5},
        "structure": {"hard_edges": []},
        "metrics": {"density": 0.5},
        "artifacts": {"artifact_count": 10},
        "artifacts_compact": {"artifact_count": 10}
    }
    
    layer_output_dir = "integration_test_layer"
    
    def mock_resolve_report_path(path):
        return os.path.join(str(tmp_path), path)
        
    monkeypatch.setattr("contextor.core.reporting_engine.formatting.resolve_report_path", mock_resolve_report_path)
    
    result = save_layer_reports(
        repo_name="test_repo",
        layer_name="test_layer",
        layer_reports=layer_reports,
        log=None,
        datestamp="2026",
        layer_output_dir=layer_output_dir
    )
    
    assert result["layer"] == "test_layer"
    assert result["module_count"] == 5
    
    # Verify files were created
    expected_dir = os.path.join(str(tmp_path), "output", layer_output_dir)
    assert os.path.isdir(expected_dir)
    
    summary_path = os.path.join(expected_dir, "test_repo_test_layer_summary_2026.json")
    assert os.path.isfile(summary_path)
    
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["status"] == "ok"
        assert data["layer_module_count"] == 5

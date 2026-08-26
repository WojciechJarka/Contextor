import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from contextor.core.domain.module import Module
from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES
from contextor.mcp.tools.search_source import search_source


def _setup_mock_source_engine(tmp_path, monkeypatch, files: dict[str, str]):
    modules = {}
    for index, (relative, text) in enumerate(files.items(), 1):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        module_name = relative[:-3].replace("/", ".").replace("\\", ".")
        modules[module_name] = Module(str(index), relative, str(path), [])
    engine = SimpleNamespace(state=SimpleNamespace(modules=modules, artifacts={}, resync_required=False))
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(query_helpers, "module_truth_unavailable", lambda *_args: None)
    return engine


def test_search_source__legacy_search_term_still_works(tmp_path, monkeypatch):
    source = "def compute_value():\n    return 42\n"
    _setup_mock_source_engine(tmp_path, monkeypatch, {"pkg/sample.py": source})
    raw = search_source(str(tmp_path), search_term="compute_value")
    res = json.loads(raw)
    assert res["status"] == "ok"
    assert res["search_term"] == "compute_value"
    assert res["total_matches"] == 1
    assert res["matches"][0]["file_path"] == "pkg/sample.py"


def test_search_source__query_alias_matches_search_term(tmp_path, monkeypatch):
    source = "def compute_value():\n    return 42\n"
    _setup_mock_source_engine(tmp_path, monkeypatch, {"pkg/sample.py": source})
    raw_term = search_source(str(tmp_path), search_term="compute_value")
    raw_query = search_source(str(tmp_path), query="compute_value")
    assert json.loads(raw_term) == json.loads(raw_query)


def test_search_source__both_same_are_accepted(tmp_path, monkeypatch):
    source = "def compute_value():\n    return 42\n"
    _setup_mock_source_engine(tmp_path, monkeypatch, {"pkg/sample.py": source})
    raw = search_source(str(tmp_path), search_term="compute_value", query="compute_value")
    res = json.loads(raw)
    assert res["status"] == "ok"
    assert res["search_term"] == "compute_value"
    assert res["total_matches"] == 1


def test_search_source__both_different_fail_closed(tmp_path, monkeypatch):
    source = "def compute_value():\n    return 42\n"
    _setup_mock_source_engine(tmp_path, monkeypatch, {"pkg/sample.py": source})
    raw = search_source(str(tmp_path), search_term="compute_value", query="other_value")
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "search_term and query must match when both are provided."


def test_search_source__missing_both_fail_closed(tmp_path, monkeypatch):
    source = "def compute_value():\n    return 42\n"
    _setup_mock_source_engine(tmp_path, monkeypatch, {"pkg/sample.py": source})
    raw = search_source(str(tmp_path))
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "search_term or query is required."


def test_search_source__empty_query_matches_legacy_empty_search_term(tmp_path, monkeypatch):
    source = "def compute_value():\n    return 42\n"
    _setup_mock_source_engine(tmp_path, monkeypatch, {"pkg/sample.py": source})
    raw_term = search_source(str(tmp_path), search_term="")
    raw_query = search_source(str(tmp_path), query="")
    assert json.loads(raw_term) == json.loads(raw_query)
    assert json.loads(raw_query) == {"status": "error", "error": "invalid_search_term"}


def test_search_source__whitespace_query_matches_legacy_whitespace_search_term(tmp_path, monkeypatch):
    source = "def compute_value():\n    return   42\n"
    _setup_mock_source_engine(tmp_path, monkeypatch, {"pkg/sample.py": source})
    raw_term = search_source(str(tmp_path), search_term="   ")
    raw_query = search_source(str(tmp_path), query="   ")
    assert json.loads(raw_term) == json.loads(raw_query)
    res = json.loads(raw_query)
    assert res["status"] == "ok"
    assert res["total_matches"] == 2


def test_search_source__case_insensitive_alias_matches_legacy(tmp_path, monkeypatch):
    source = "VALUE = 'Needle'\n"
    _setup_mock_source_engine(tmp_path, monkeypatch, {"pkg/sample.py": source})
    raw_term = search_source(str(tmp_path), search_term="NEEDLE", case_sensitive=False)
    raw_query = search_source(str(tmp_path), query="NEEDLE", case_sensitive=False)
    assert json.loads(raw_term) == json.loads(raw_query)
    res = json.loads(raw_query)
    assert res["status"] == "ok"
    assert res["total_matches"] == 1


def test_search_source__case_sensitive_alias_matches_legacy(tmp_path, monkeypatch):
    source = "VALUE = 'Needle'\n"
    _setup_mock_source_engine(tmp_path, monkeypatch, {"pkg/sample.py": source})
    raw_term = search_source(str(tmp_path), search_term="NEEDLE", case_sensitive=True)
    raw_query = search_source(str(tmp_path), query="NEEDLE", case_sensitive=True)
    assert json.loads(raw_term) == json.loads(raw_query)
    res = json.loads(raw_query)
    assert res["status"] == "ok"
    assert res["total_matches"] == 0


def test_search_source__limit_default_contract_unchanged(tmp_path, monkeypatch):
    files = {f"pkg/file_{i}.py": f"VALUE_{i} = 'target'\n" for i in range(25)}
    _setup_mock_source_engine(tmp_path, monkeypatch, files)
    raw = search_source(str(tmp_path), query="target")
    res = json.loads(raw)
    assert res["status"] == "ok"
    assert res["total_matches"] == 25
    assert len(res["matches"]) == 20
    assert res["truncated"] is True


def test_search_source__limit_none_contract_unchanged(tmp_path, monkeypatch):
    files = {f"pkg/file_{i}.py": f"VALUE_{i} = 'target'\n" for i in range(25)}
    _setup_mock_source_engine(tmp_path, monkeypatch, files)
    raw = search_source(str(tmp_path), query="target", limit=None)
    res = json.loads(raw)
    assert res["status"] == "ok"
    assert res["total_matches"] == 25
    assert len(res["matches"]) == 25
    assert res["truncated"] is False


def test_search_source__legacy_positional_call_remains_valid(tmp_path, monkeypatch):
    source = "def compute_value():\n    return 42\n"
    _setup_mock_source_engine(tmp_path, monkeypatch, {"pkg/sample.py": source})
    # positional: repo_path, search_term, limit, case_sensitive, allow_large_output
    raw = search_source(str(tmp_path), "compute_value", 5, False, False)
    res = json.loads(raw)
    assert res["status"] == "ok"
    assert res["search_term"] == "compute_value"
    assert res["total_matches"] == 1


def test_search_source__output_guard_behavior_is_identical_for_query_alias(tmp_path, monkeypatch):
    # Repeat lines to exceed output guard threshold
    large_line = "TOKEN = 'target' * 100\n"
    files = {f"pkg/large_{i}.py": large_line * 20 for i in range(15)}
    _setup_mock_source_engine(tmp_path, monkeypatch, files)
    raw_term = search_source(str(tmp_path), search_term="target", limit=None, allow_large_output=False)
    raw_query = search_source(str(tmp_path), query="target", limit=None, allow_large_output=False)
    res_term = json.loads(raw_term)
    res_query = json.loads(raw_query)
    assert res_term == res_query
    assert res_query["status"] == "confirmation_required"
    assert res_query["estimated_output_bytes"] > LARGE_OUTPUT_WARNING_BYTES


def test_search_source__allow_large_output_behavior_is_identical_for_query_alias(tmp_path, monkeypatch):
    large_line = "TOKEN = 'target' * 100\n"
    files = {f"pkg/large_{i}.py": large_line * 20 for i in range(15)}
    _setup_mock_source_engine(tmp_path, monkeypatch, files)
    raw_term = search_source(str(tmp_path), search_term="target", limit=None, allow_large_output=True)
    raw_query = search_source(str(tmp_path), query="target", limit=None, allow_large_output=True)
    res_term = json.loads(raw_term)
    res_query = json.loads(raw_query)
    assert res_term == res_query
    assert res_query["status"] == "ok"
    assert res_query["total_matches"] > 0

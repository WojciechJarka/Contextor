import json
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.tools.search_artifacts import search_artifacts


def _setup_mock_search_engine(monkeypatch):
    class Registry:
        def get_module_id(self, module):
            mapping = {
                "pkg.a": "1/1",
                "pkg.b": "2/1",
                "pkg.helper_module": "3/1",
            }
            return mapping.get(module)

        def get_module_path(self, module_id):
            mapping = {
                "1/1": "pkg.a",
                "2/1": "pkg.b",
                "3/1": "pkg.helper_module",
            }
            return mapping.get(module_id)

    class Graph:
        hard_edges = {
            "pkg.a": {"pkg.b"},
            "pkg.helper_module": {"pkg.a"},
        }
        soft_edges = {}

    class State:
        modules = {
            "pkg.a": object(),
            "pkg.b": object(),
            "pkg.helper_module": object(),
        }
        artifacts = {
            "pkg.a": {
                "symbols": {
                    "functions": ["process_data", "run_job", "helper_func"],
                    "classes": ["DataProcessor"],
                    "methods": [],
                    "globals": [],
                },
                "consumers": {
                    "process_data": {"consumers": ["pkg.b"]},
                    "run_job": {"consumers": []},
                    "helper_func": {"consumers": ["pkg.helper_module"]},
                },
            },
            "pkg.b": {
                "symbols": {
                    "functions": ["process_datum", "consume_data"],
                    "classes": [],
                    "methods": [],
                    "globals": ["DEFAULT_CONFIG"],
                },
                "consumers": {},
            },
        }
        dependency_graph = Graph()

    class Engine:
        state = State()
        registry = Registry()

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: Engine())


def test_search_artifacts__legacy_search_term_still_works(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw = search_artifacts(repo_path=str(tmp_path), search_term="process_data")
    res = json.loads(raw)
    assert res["query"] == "process_data"
    assert res["match_count"] >= 1
    assert "pkg.a::process_data" in res["artifacts"]


def test_search_artifacts__query_alias_matches_search_term(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw_search_term = search_artifacts(repo_path=str(tmp_path), search_term="process_data")
    raw_query = search_artifacts(repo_path=str(tmp_path), query="process_data")
    assert json.loads(raw_search_term) == json.loads(raw_query)


def test_search_artifacts__both_same_are_accepted(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw = search_artifacts(
        repo_path=str(tmp_path),
        search_term="process_data",
        query="process_data",
    )
    res = json.loads(raw)
    assert res["query"] == "process_data"
    assert "pkg.a::process_data" in res["artifacts"]


def test_search_artifacts__both_different_fail_closed(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw = search_artifacts(
        repo_path=str(tmp_path),
        search_term="process_data",
        query="different_query",
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "search_term and query must match when both are provided."


def test_search_artifacts__missing_both_fail_closed(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw = search_artifacts(repo_path=str(tmp_path))
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "search_term or query is required."


def test_search_artifacts__empty_search_term_preserves_match_all(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw = search_artifacts(repo_path=str(tmp_path), search_term="")
    res = json.loads(raw)
    assert res["query"] == ""
    assert res["total_matches"] > 1
    assert len(res["artifacts"]) >= 1


def test_search_artifacts__empty_query_preserves_match_all(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw = search_artifacts(repo_path=str(tmp_path), query="")
    res = json.loads(raw)
    assert res["query"] == ""
    assert res["total_matches"] > 1
    assert len(res["artifacts"]) >= 1


def test_search_artifacts__both_empty_are_accepted_as_match_all(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw = search_artifacts(repo_path=str(tmp_path), search_term="", query="")
    res = json.loads(raw)
    assert res["query"] == ""
    assert res["total_matches"] > 1


def test_search_artifacts__whitespace_search_term_is_not_stripped(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw = search_artifacts(repo_path=str(tmp_path), search_term="   ")
    assert raw == "No live modules or artifacts found matching '   '."


def test_search_artifacts__whitespace_query_is_not_stripped(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw = search_artifacts(repo_path=str(tmp_path), query="   ")
    assert raw == "No live modules or artifacts found matching '   '."


def test_search_artifacts__whitespace_both_same_are_accepted(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw = search_artifacts(repo_path=str(tmp_path), search_term="   ", query="   ")
    assert raw == "No live modules or artifacts found matching '   '."


def test_search_artifacts__limit_default_remains_20(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw = search_artifacts(repo_path=str(tmp_path), query="")
    res = json.loads(raw)
    assert res["match_count"] <= 20


def test_search_artifacts__limit_none_remains_unbounded(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    raw = search_artifacts(repo_path=str(tmp_path), query="", limit=None)
    res = json.loads(raw)
    assert res["truncated"] is False
    assert res["match_count"] == res["total_matches"]


def test_search_artifacts__legacy_positional_call_remains_valid(tmp_path, monkeypatch):
    _setup_mock_search_engine(monkeypatch)
    # positional: repo_path, search_term, limit
    raw = search_artifacts(str(tmp_path), "process_data", 5)
    res = json.loads(raw)
    assert res["query"] == "process_data"
    assert "pkg.a::process_data" in res["artifacts"]

import ast
import importlib
import inspect
from pathlib import Path

from contextor import mcp_server
from contextor.mcp.documentation import load_documentation_index
from contextor.mcp.tools.get_artifact_blast_radius import get_artifact_blast_radius
from contextor.mcp.tools.get_artifacts_for_module import get_artifacts_for_module
from contextor.mcp.tools.lookup_artifact_by_symbol import lookup_artifact_by_symbol
from contextor.mcp.tools.search_artifacts import search_artifacts
from contextor.mcp.tools.search_source import search_source
from contextor.mcp.tools.get_source_range import get_source_range


_EXPECTED_ORDER = [
    "analyze_project", "analyze_layer", "analyze_single_file",
    "get_analysis_status", "get_live_events", "update_file",
    "get_project_architecture", "get_module_context",
    "get_artifact_blast_radius", "search_artifacts",
    "get_symbol_implementation", "get_file_edit_context",
    "get_layer_isolation", "get_report_diff", "describe_canonical_state",
    "query_canonical_projection", "extract_indexed_report_context",
    "lookup_index_entries", "get_artifacts_for_module",
    "lookup_artifact_by_symbol", "search_source", "get_source_range",
    "get_symbol_call_context", "get_name_collisions",
    "get_mcp_documentation",
]

_IMPLEMENTATIONS = {
    "get_artifact_blast_radius": get_artifact_blast_radius,
    "search_artifacts": search_artifacts,
    "search_source": search_source,
    "get_source_range": get_source_range,
    "get_artifacts_for_module": get_artifacts_for_module,
    "lookup_artifact_by_symbol": lookup_artifact_by_symbol,
}

_EXPECTED_SIGNATURES = {
    "get_artifact_blast_radius": "(repo_path: str, artifact_name: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, representation: str = 'named', artifact: str | None = None) -> str",
    "search_artifacts": "(repo_path: str, search_term: str | None = None, limit: int | None = 20, evidence_limit: int | None = 20, compact: bool = True, fields: list[str] | None = None, query: str | None = None) -> str",
    "search_source": "(repo_path: str, search_term: str | None = None, limit: int | None = 20, case_sensitive: bool = False, allow_large_output: bool = False, query: str | None = None) -> str",
    "get_source_range": "(repo_path: str, file_path: str, start_line: int, end_line: int, allow_large_output: bool = False) -> str",
    "get_artifacts_for_module": "(repo_path: str, module_name: str = '', include_consumers: bool = True, symbol_filter: str = '', limit: int | None = 50, evidence_limit: int | None = 20, compact: bool = True, fields: list[str] | None = None, representation: str = 'named', module: str | None = None) -> str",
    "lookup_artifact_by_symbol": "(repo_path: str, symbol_name: str = '', limit: int | None = 20, evidence_limit: int | None = 20, compact: bool = True, fields: list[str] | None = None, symbol: str | None = None) -> str",
}


def test_s2c_registration_order_bindings_signatures_and_descriptions():
    registered = mcp_server.mcp._tool_manager._tools
    descriptions = {
        entry["tool"]: entry["short_description"]
        for entry in load_documentation_index()["tools"]
    }

    assert list(registered) == _EXPECTED_ORDER
    for name in _IMPLEMENTATIONS:
        implementation = getattr(
            importlib.import_module(f"contextor.mcp.tools.{name}"), name
        )
        tool = registered[name]
        assert getattr(mcp_server, name) is tool
        assert tool.fn.__wrapped__ is implementation
        assert tool.fn.__module__ == f"contextor.mcp.tools.{name}"
        assert str(inspect.signature(tool.fn)) == _EXPECTED_SIGNATURES[name]
        assert tool.description == descriptions[name]


def test_s2c_ownership_import_graph_and_shared_helper_uniqueness():
    root = Path(__file__).parents[1]
    server_path = Path(mcp_server.__file__)
    server_tree = ast.parse(server_path.read_text(encoding="utf-8"))
    decorated = [
        node.name
        for node in server_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(ast.unparse(item).startswith("mcp.tool") for item in node.decorator_list)
    ]
    assert decorated == []
    assert set(_IMPLEMENTATIONS).isdisjoint(decorated)

    for name in _IMPLEMENTATIONS:
        path = root / "contextor" / "mcp" / "tools" / f"{name}.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            node.module for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert "contextor.mcp_server" not in imports
        assert not any(module.startswith("contextor.mcp.tools.") for module in imports)
        assert "FastMCP" not in source
        public_functions = [
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
        ]
        assert [node.name for node in public_functions] == [name]
        assert not public_functions[0].decorator_list

    helper_names = {
        "bounded_items", "read_registries", "canonical_symbol_consumers",
        "module_truth_unavailable", "canonical_symbol_catalog",
    }
    owners = {}
    for path in (root / "contextor" / "mcp").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in helper_names:
                    owners.setdefault(node.name, []).append(path)
    assert {name: len(paths) for name, paths in owners.items()} == {
        name: 1 for name in helper_names
    }


def test_s2c_has_no_registration_dependency_binding_or_report_io():
    root = Path(__file__).parents[1]
    server_tree = ast.parse(Path(mcp_server.__file__).read_text(encoding="utf-8"))
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
        and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr)
        in {"bind_engine_resolver", "set_analysis_engine"}
        for node in ast.walk(server_tree)
    )
    for name in _IMPLEMENTATIONS:
        source = (
            root / "contextor" / "mcp" / "tools" / f"{name}.py"
        ).read_text(encoding="utf-8")
        assert "resolve_output_dir" not in source
        assert "_get_canonical_report" not in source
        assert "json.load" not in source


def _setup_lookup_state(monkeypatch):
    import json
    from types import SimpleNamespace
    from contextor.core.analysis.state_manager import RepositoryAnalysisState
    from contextor.mcp import query_helpers, runtime as mcp_runtime

    state = RepositoryAnalysisState(
        artifacts={
            "pkg.mod_a": {
                "own_symbols": ["my_func", "ambig_symbol"],
                "symbols": {
                    "functions": ["my_func", "ambig_symbol"],
                },
                "consumers": {
                    "my_func": {
                        "consumer_count": {"total": 2},
                        "consumers": ["tests.test_1", "tests.test_2"],
                    }
                },
            },
            "pkg.mod_b": {
                "own_symbols": ["ambig_symbol"],
                "symbols": {
                    "functions": ["ambig_symbol"],
                },
            },
        },
        artifact_consumption={
            "pkg.mod_a::my_func": {
                "consumers": ["tests.test_1", "tests.test_2"],
                "channels": {"tests.test_1": ["direct_calls"], "tests.test_2": ["direct_calls"]},
            },
            "pkg.mod_a::ambig_symbol": {
                "consumers": [],
                "channels": {},
            },
            "pkg.mod_b::ambig_symbol": {
                "consumers": [],
                "channels": {},
            },
        },
        artifact_consumption_state="fresh",
    )
    art_path_to_id = {
        "pkg.mod_a::my_func": "A1/1",
        "pkg.mod_a::ambig_symbol": "A2/1",
        "pkg.mod_b::ambig_symbol": "A3/1",
    }
    art_id_to_path = {v: k for k, v in art_path_to_id.items()}
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: ({}, {}, art_path_to_id, art_id_to_path))
    return state


def test_lookup_artifact_by_symbol_legacy_symbol_name(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol_name="my_func",
    )
    res = json.loads(raw)
    assert res["query"] == "my_func"
    assert res["match_count"] == 1
    assert "A1/1" in res["artifacts"]
    assert res["artifacts"]["A1/1"]["full_name"] == "pkg.mod_a::my_func"


def test_lookup_artifact_by_symbol_alias_symbol(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="my_func",
    )
    res = json.loads(raw)
    assert res["query"] == "my_func"
    assert res["match_count"] == 1
    assert "A1/1" in res["artifacts"]
    assert res["artifacts"]["A1/1"]["full_name"] == "pkg.mod_a::my_func"


def test_lookup_artifact_by_symbol_substring_matching(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="my_",
    )
    res = json.loads(raw)
    assert res["query"] == "my_"
    assert res["match_count"] == 1
    assert "A1/1" in res["artifacts"]


def test_lookup_artifact_by_symbol_missing_both_returns_controlled_error(tmp_path):
    import json
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "symbol_name or symbol is required."


def test_lookup_artifact_by_symbol_not_found_uses_effective_symbol(tmp_path, monkeypatch):
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="missing_sym_completely_unrelated",
    )
    assert raw == "No current artifacts found matching 'missing_sym_completely_unrelated'."


def test_lookup_artifact_by_symbol_ambiguity_uses_effective_symbol(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="ambig_symbol",
    )
    res = json.loads(raw)
    assert res["error"] == "Ambiguous canonical symbol identity."
    assert res["query"] == "ambig_symbol"
    assert res["candidates"] == ["pkg.mod_a::ambig_symbol", "pkg.mod_b::ambig_symbol"]


def test_lookup_artifact_by_symbol_preserves_limit_and_compact_semantics(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="my_func",
        compact=False,
        evidence_limit=1,
    )
    res = json.loads(raw)
    entry = res["artifacts"]["A1/1"]
    assert entry["consumers"]["total"] == 2
    assert entry["consumers"]["truncated"] is True
    assert len(entry["consumers"]["items"]) == 1


def test_lookup_artifact_by_symbol_existing_match_limit_zero_does_not_call_resolver(tmp_path, monkeypatch):
    import json
    from contextor.mcp import query_helpers
    _setup_lookup_state(monkeypatch)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("resolve_artifact_identity should NOT have been called for an existing match!")

    monkeypatch.setattr(query_helpers, "resolve_artifact_identity", fail_if_called)

    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="my_func",
        limit=0,
    )
    res = json.loads(raw)
    assert res["query"] == "my_func"
    assert res["match_count"] == 0
    assert res["total_matches"] == 1
    assert res["truncated"] is True
    assert res["artifacts"] == {}


def test_lookup_artifact_by_symbol_substring_match_limit_zero_does_not_call_resolver(tmp_path, monkeypatch):
    import json
    from contextor.mcp import query_helpers
    _setup_lookup_state(monkeypatch)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("resolve_artifact_identity should NOT have been called for a substring match!")

    monkeypatch.setattr(query_helpers, "resolve_artifact_identity", fail_if_called)

    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="my_",
        limit=0,
    )
    res = json.loads(raw)
    assert res["query"] == "my_"
    assert res["match_count"] == 0
    assert res["total_matches"] == 1
    assert res["truncated"] is True
    assert res["artifacts"] == {}


def test_lookup_artifact_by_symbol_resolved_artifact_id_honors_limit_zero(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)

    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="A1/1",
        limit=0,
    )
    res = json.loads(raw)
    assert res["query"] == "A1/1"
    assert res["match_count"] == 0
    assert res["total_matches"] == 1
    assert res["truncated"] is True
    assert res["artifacts"] == {}


def test_lookup_artifact_by_symbol_exact_artifact_id(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="A1/1",
    )
    res = json.loads(raw)
    assert res["query"] == "A1/1"
    assert res["match_count"] == 1
    assert "A1/1" in res["artifacts"]
    assert res["artifacts"]["A1/1"]["full_name"] == "pkg.mod_a::my_func"
    assert res["artifacts"]["A1/1"]["consumers"]["total"] == 2


def test_lookup_artifact_by_symbol_exact_full_canonical_identity(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="pkg.mod_a::my_func",
    )
    res = json.loads(raw)
    assert res["query"] == "pkg.mod_a::my_func"
    assert res["match_count"] == 1
    assert "A1/1" in res["artifacts"]
    assert res["artifacts"]["A1/1"]["full_name"] == "pkg.mod_a::my_func"


def test_lookup_artifact_by_symbol_fuzzy_leaf_typo(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="my_fnc",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["query"] == "my_fnc"
    assert res["data_source"] == "active_artifact_registry"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["artifact"] == "pkg.mod_a::my_func"
    assert top["artifact_id"] == "A1/1"
    assert top["score"] >= 0.75
    assert "artifacts" not in res


def test_lookup_artifact_by_symbol_fuzzy_full_identity_typo(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="pkg.mod_a::my_fnc",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["query"] == "pkg.mod_a::my_fnc"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["artifact"] == "pkg.mod_a::my_func"
    assert top["artifact_id"] == "A1/1"


def test_lookup_artifact_by_symbol_fuzzy_never_auto_resolves(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="my_funcc",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "artifacts" not in res
    assert len(res["similar_candidates"]) > 0


def test_lookup_artifact_by_symbol_max_five_candidates(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    from contextor.core.analysis.state_manager import RepositoryAnalysisState
    from contextor.mcp import query_helpers, runtime as mcp_runtime

    state = RepositoryAnalysisState(
        artifacts={
            "pkg.mod": {
                "own_symbols": [f"func_{i}" for i in range(10)],
                "symbols": {
                    "functions": [f"func_{i}" for i in range(10)],
                },
            }
        },
        artifact_consumption={},
        artifact_consumption_state="fresh",
    )
    art_p2i = {f"pkg.mod::func_{i}": f"A{100+i}/1" for i in range(10)}
    art_i2p = {v: k for k, v in art_p2i.items()}

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: ({}, {}, art_p2i, art_i2p))

    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="func",
    )
    # Note: 'func' matches substring in existing search, so let's use a typo that does not substring match all
    raw_typo = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="fnc_",
    )
    res = json.loads(raw_typo)
    assert res["status"] == "not_found"
    assert len(res["similar_candidates"]) <= 5


def test_lookup_artifact_by_symbol_nonexistent_artifact_id_no_fuzzy(tmp_path, monkeypatch):
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="A9999/1",
    )
    assert raw == "No current artifacts found matching 'A9999/1'."


def test_lookup_artifact_by_symbol_stale_module_fails_closed(tmp_path, monkeypatch):
    import json
    from contextor.mcp import query_helpers
    _setup_lookup_state(monkeypatch)

    monkeypatch.setattr(
        query_helpers,
        "module_truth_unavailable",
        lambda _state, mod: {"status": "stale", "module": mod} if mod == "pkg.mod_a" else None,
    )

    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol="A1/1",
    )
    res = json.loads(raw)
    assert res["status"] == "stale"
    assert res["module"] == "pkg.mod_a"


def test_lookup_artifact_by_symbol_matching_both_symbol_name_and_symbol(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol_name="my_func",
        symbol="my_func",
    )
    res = json.loads(raw)
    assert res["query"] == "my_func"
    assert "A1/1" in res["artifacts"]
    assert res["artifacts"]["A1/1"]["full_name"] == "pkg.mod_a::my_func"


def test_lookup_artifact_by_symbol_conflicting_symbol_name_and_symbol_returns_error(tmp_path, monkeypatch):
    import json
    _setup_lookup_state(monkeypatch)
    raw = lookup_artifact_by_symbol(
        repo_path=str(tmp_path),
        symbol_name="my_func",
        symbol="different",
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "symbol_name and symbol must match when both are provided."


def _setup_module_artifacts_state(monkeypatch):
    from types import SimpleNamespace
    from contextor.core.analysis.state_manager import RepositoryAnalysisState
    from contextor.mcp import query_helpers, runtime as mcp_runtime

    module_obj = SimpleNamespace(module_id="10/1", path="pkg/mod_a.py", imports=[])
    state = RepositoryAnalysisState(
        modules={"pkg.mod_a": module_obj},
        artifacts={
            "pkg.mod_a": {
                "own_symbols": ["my_func", "extra_func"],
                "symbols": {
                    "functions": ["my_func", "extra_func"],
                },
                "consumers": {
                    "my_func": {
                        "consumer_count": {"total": 2},
                        "consumers": ["tests.test_1", "tests.test_2"],
                    },
                    "extra_func": {
                        "consumer_count": {"total": 1},
                        "consumers": ["tests.test_1"],
                    },
                },
            },
            "pkg.services.auth": {
                "own_symbols": ["login"],
                "symbols": {
                    "functions": ["login"],
                },
                "consumers": {
                    "login": {
                        "consumer_count": {"total": 1},
                        "consumers": ["tests.test_1"],
                    }
                },
            },
        },
        artifact_consumption={
            "pkg.mod_a::my_func": {
                "consumers": ["tests.test_1", "tests.test_2"],
                "channels": {"tests.test_1": ["direct_calls"], "tests.test_2": ["direct_calls"]},
            },
            "pkg.mod_a::extra_func": {
                "consumers": ["tests.test_1"],
                "channels": {"tests.test_1": ["direct_calls"]},
            },
            "pkg.services.auth::login": {
                "consumers": ["tests.test_1"],
                "channels": {"tests.test_1": ["direct_calls"]},
            },
        },
        artifact_consumption_state="fresh",
    )
    mod_path_to_id = {"pkg.mod_a": "10/1", "pkg.services.auth": "13/1"}
    mod_id_to_path = {v: k for k, v in mod_path_to_id.items()}
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: (mod_path_to_id, mod_id_to_path, {}, {}))
    return state


def test_get_artifacts_for_module_legacy_module_name(tmp_path, monkeypatch):
    import json
    _setup_module_artifacts_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "pkg.mod_a::my_func" in res["artifacts"]


def test_get_artifacts_for_module_alias_module(tmp_path, monkeypatch):
    import json
    _setup_module_artifacts_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "pkg.mod_a::my_func" in res["artifacts"]


def test_get_artifacts_for_module_matching_both(tmp_path, monkeypatch):
    import json
    _setup_module_artifacts_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
        module="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "pkg.mod_a::my_func" in res["artifacts"]


def test_get_artifacts_for_module_conflicting_alias_returns_error(tmp_path, monkeypatch):
    import json
    _setup_module_artifacts_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
        module="pkg.mod_b",
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "module_name and module must match when both are provided."


def test_get_artifacts_for_module_missing_both_returns_error(tmp_path):
    import json
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "module_name or module is required."


def test_get_artifacts_for_module_file_path_normalization(tmp_path, monkeypatch):
    import json
    _setup_module_artifacts_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg/mod_a.py",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "pkg.mod_a::my_func" in res["artifacts"]


def test_get_artifacts_for_module_preserves_limit_compact_and_representation(tmp_path, monkeypatch):
    import json
    _setup_module_artifacts_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg.mod_a",
        compact=False,
        limit=1,
        representation="named",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert res["artifact_count"] == 1
    assert res["truncated"] is True


def _setup_blast_radius_state(monkeypatch):
    from types import SimpleNamespace
    from contextor.core.analysis.state_manager import RepositoryAnalysisState
    from contextor.mcp import query_helpers, runtime as mcp_runtime

    state = RepositoryAnalysisState(
        artifacts={
            "pkg.mod_a": {
                "own_symbols": ["my_func"],
                "symbols": {
                    "functions": ["my_func"],
                },
                "consumers": {
                    "my_func": {
                        "consumer_count": {"total": 2},
                        "consumers": ["tests.test_1", "tests.test_2"],
                    }
                },
            },
        },
        artifact_consumption={
            "pkg.mod_a::my_func": {
                "consumers": ["tests.test_1", "tests.test_2"],
                "channels": {"tests.test_1": ["direct_calls"], "tests.test_2": ["direct_calls"]},
            }
        },
        artifact_consumption_state="fresh",
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: ({"pkg.mod_a": "M1"}, {"M1": "pkg.mod_a"}, {"pkg.mod_a::my_func": "A1"}, {"A1": "pkg.mod_a::my_func"}),
    )
    return state


def test_get_artifact_blast_radius_legacy_artifact_name(tmp_path, monkeypatch):
    import json
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact_name="pkg.mod_a::my_func",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.mod_a::my_func"


def test_get_artifact_blast_radius_alias_artifact(tmp_path, monkeypatch):
    import json
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="pkg.mod_a::my_func",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.mod_a::my_func"


def test_get_artifact_blast_radius_matching_both(tmp_path, monkeypatch):
    import json
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact_name="pkg.mod_a::my_func",
        artifact="pkg.mod_a::my_func",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.mod_a::my_func"


def test_get_artifact_blast_radius_conflicting_alias_returns_error(tmp_path, monkeypatch):
    import json
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact_name="pkg.mod_a::my_func",
        artifact="different",
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "artifact_name and artifact must match when both are provided."


def test_get_artifact_blast_radius_missing_both_returns_error(tmp_path):
    import json
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "artifact_name or artifact is required."


def test_get_artifact_blast_radius_module_redirect_preserves_structure_and_suggested_next_call(tmp_path, monkeypatch):
    import json
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["resolved_as"] == "module"
    assert res["module"] == "pkg.mod_a"
    assert res["module_id"] == "M1"
    assert res["suggested_next_tool"] == "get_module_context"
    assert res["suggested_next_call"] == {
        "tool": "get_module_context",
        "arguments": {"module": "pkg.mod_a"},
    }
    assert "artifact_candidates" in res
    assert res["artifact_candidates"]["total"] == 1


def test_get_artifact_blast_radius_regular_artifact_does_not_contain_module_redirect(tmp_path, monkeypatch):
    import json
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="pkg.mod_a::my_func",
    )
    res = json.loads(raw)
    assert "resolved_as" not in res
    assert "suggested_next_tool" not in res
    assert "suggested_next_call" not in res


def test_get_artifact_blast_radius_preserves_max_items_compact_and_representation(tmp_path, monkeypatch):
    import json
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="pkg.mod_a::my_func",
        compact=False,
        max_items=1,
        representation="named",
    )
    res = json.loads(raw)
    assert res["consumers"]["total"] == 2
    assert res["consumers"]["truncated"] is True
    assert len(res["consumers"]["items"]) == 1

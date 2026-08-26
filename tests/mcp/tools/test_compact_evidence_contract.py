import json
from pathlib import Path
import pytest

from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.tools.search_artifacts import search_artifacts
from contextor.mcp.tools.lookup_artifact_by_symbol import lookup_artifact_by_symbol
from contextor.mcp.tools.get_report_diff import get_report_diff
from contextor.mcp.tools.get_layer_isolation import get_layer_isolation
from contextor.mcp.tools.get_file_edit_context import get_file_edit_context
from contextor.mcp.tools.update_file import update_file, _semantic_diff_view


def _setup_mock_search_and_lookup_engine(monkeypatch):
    class Registry:
        def get_module_id(self, module):
            mapping = {
                "pkg.a": "1/1",
                "pkg.b": "2/1",
                "pkg.c": "3/1",
                "pkg.d": "4/1",
                "pkg.e": "5/1",
            }
            return mapping.get(module)

        def get_module_path(self, module_id):
            mapping = {
                "1/1": "pkg.a",
                "2/1": "pkg.b",
                "3/1": "pkg.c",
                "4/1": "pkg.d",
                "5/1": "pkg.e",
            }
            return mapping.get(module_id)

    class Graph:
        hard_edges = {
            "pkg.a": {"pkg.b", "pkg.c", "pkg.d", "pkg.e"},
            "pkg.b": {"pkg.a"},
            "pkg.c": {"pkg.a"},
            "pkg.d": {"pkg.a"},
            "pkg.e": {"pkg.a"},
        }
        soft_edges = {}

    class State:
        resync_required = False
        modules = {
            "pkg.a": object(),
            "pkg.b": object(),
            "pkg.c": object(),
            "pkg.d": object(),
            "pkg.e": object(),
        }
        artifacts = {
            "pkg.a": {
                "symbols": {
                    "functions": ["process_data"],
                    "classes": [],
                    "methods": [],
                    "globals": [],
                },
                "consumers": {
                    "process_data": {
                        "consumers": ["pkg.b", "pkg.c", "pkg.d", "pkg.e"]
                    }
                },
            },
            "pkg.b": {"symbols": {}, "consumers": {}},
            "pkg.c": {"symbols": {}, "consumers": {}},
            "pkg.d": {"symbols": {}, "consumers": {}},
            "pkg.e": {"symbols": {}, "consumers": {}},
        }
        dependency_graph = Graph()
        artifact_consumption_state = "fresh"

    class Engine:
        registry = Registry()
        state = State()

    engine = Engine()
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda root: engine)
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda root: (
            {"pkg.a": "1/1"},
            {"1/1": "pkg.a"},
            {"pkg.a::process_data": "A1/1"},
            {"A1/1": "pkg.a::process_data"},
        ),
    )
    return engine


def test_compact_evidence_contract__search_artifacts_nested_collections_include_evidence(tmp_path, monkeypatch):
    _setup_mock_search_and_lookup_engine(monkeypatch)

    # 1. Module dependencies inbound/outbound
    raw_mod = search_artifacts(str(tmp_path), search_term="pkg.a", compact=True)
    res_mod = json.loads(raw_mod)

    mod = res_mod["modules"]["pkg.a"]
    inbound = mod["dependencies_inbound"]
    assert "evidence" in inbound
    assert inbound["total"] == 4
    assert len(inbound["evidence"]) == 3
    assert inbound["truncated"] is True
    assert inbound["expand"] == {"compact": False, "evidence_limit": None}

    outbound = mod["dependencies_outbound"]
    assert "evidence" in outbound
    assert outbound["total"] == 4
    assert len(outbound["evidence"]) == 3
    assert outbound["truncated"] is True
    assert outbound["expand"] == {"compact": False, "evidence_limit": None}

    # 2. Artifact consumers
    raw_art = search_artifacts(str(tmp_path), search_term="process_data", compact=True)
    res_art = json.loads(raw_art)

    art = res_art["artifacts"]["pkg.a::process_data"]
    con = art["consumers"]
    assert "evidence" in con
    assert con["total"] == 4
    assert len(con["evidence"]) == 3
    assert con["truncated"] is True
    assert con["expand"] == {"compact": False, "evidence_limit": None}


def test_compact_evidence_contract__lookup_artifact_consumers_include_evidence(tmp_path, monkeypatch):
    _setup_mock_search_and_lookup_engine(monkeypatch)
    monkeypatch.setattr("contextor.mcp.tools.lookup_artifact_by_symbol.artifact_consumption_is_fresh", lambda state: True)
    monkeypatch.setattr(query_helpers, "canonical_symbol_consumers", lambda state, mod, sym: ["pkg.b", "pkg.c", "pkg.d", "pkg.e"])

    raw = lookup_artifact_by_symbol(str(tmp_path), symbol="process_data", compact=True)
    res = json.loads(raw)

    art = res["artifacts"]["A1/1"]
    con = art["consumers"]
    assert "evidence" in con
    assert con["total"] == 4
    assert len(con["evidence"]) == 3
    assert con["truncated"] is True
    assert con["expand"] == {"compact": False, "evidence_limit": None}


def test_compact_evidence_contract__report_diff_layers_include_evidence(tmp_path, monkeypatch):
    from contextor.mcp import report_helpers

    diff_file = tmp_path / "testrepo_report_diff.json"
    diff_payload = {
        "report_diff": {
            "layers": {
                "ui": {"diff": 1},
                "engine": {"diff": 2},
                "contract": {"diff": 3},
                "adapter": {"diff": 4},
            }
        }
    }
    diff_file.write_text(json.dumps(diff_payload), encoding="utf-8")
    monkeypatch.setattr(report_helpers, "get_canonical_report", lambda root, name: diff_file)

    raw = get_report_diff(str(tmp_path), compact=True)
    res = json.loads(raw)

    layers_col = res["report_diff"]["layers"]
    assert "evidence" in layers_col
    assert isinstance(layers_col["evidence"], dict)
    assert layers_col["total"] == 4
    assert len(layers_col["evidence"]) == 3
    assert layers_col["truncated"] is True
    assert layers_col["expand"] == {"compact": False, "max_items": None}
    assert list(layers_col["evidence"].keys()) == ["adapter", "contract", "engine"]


def test_compact_evidence_contract__layer_isolation_collections_include_evidence(tmp_path, monkeypatch):
    from contextor.mcp import report_helpers

    # adapter is rank 6, ui is rank 1 -> adapter calling ui is a violation
    ga_file = tmp_path / "testrepo_adapter_graph_analytics.json"
    ga_payload = {
        "module_count": 5,
        "modules": {
            "adapter.a": {"layer": "adapter"},
            "ui.b": {"layer": "ui"},
            "ui.c": {"layer": "ui"},
            "ui.d": {"layer": "ui"},
            "ui.e": {"layer": "ui"},
        },
        "module_dependency_matrix": {
            "M1": ["M2", "M3", "M4", "M5"],
        },
        "shared_usage_clusters": [
            {"cluster_id": 1, "modules": ["adapter.a"]},
            {"cluster_id": 2, "modules": ["adapter.a"]},
            {"cluster_id": 3, "modules": ["adapter.a"]},
            {"cluster_id": 4, "modules": ["adapter.a"]},
        ],
        "dependency_type_breakdown": {"hard": 4},
    }
    ga_file.write_text(json.dumps(ga_payload), encoding="utf-8")
    monkeypatch.setattr(report_helpers, "get_canonical_report", lambda root, name: ga_file)
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda root: (
            {"adapter.a": "M1", "ui.b": "M2", "ui.c": "M3", "ui.d": "M4", "ui.e": "M5"},
            {"M1": "adapter.a", "M2": "ui.b", "M3": "ui.c", "M4": "ui.d", "M5": "ui.e"},
            {},
            {},
        ),
    )

    raw = get_layer_isolation(str(tmp_path), layer_name="adapter", compact=True)
    res = json.loads(raw)

    clusters = res["clusters"]
    assert "evidence" in clusters
    assert clusters["total"] == 4
    assert len(clusters["evidence"]) == 3
    assert clusters["truncated"] is True
    assert clusters["expand"] == {"compact": False, "max_clusters": None}

    bv = res["boundary_violations"]
    assert "evidence" in bv
    assert bv["total"] == 4
    assert len(bv["evidence"]) == 3
    assert bv["truncated"] is True
    assert "evidence_scope" not in bv
    assert bv["expand"] == {"compact": False, "max_boundary_violations": None}


def test_compact_evidence_contract__layer_isolation_report_noncompact_shape_unchanged(tmp_path, monkeypatch):
    from contextor.mcp import report_helpers

    ga_file = tmp_path / "testrepo_adapter_graph_analytics.json"
    ga_payload = {
        "module_count": 5,
        "modules": {
            "adapter.a": {"layer": "adapter"},
            "ui.b": {"layer": "ui"},
            "ui.c": {"layer": "ui"},
            "ui.d": {"layer": "ui"},
            "ui.e": {"layer": "ui"},
        },
        "module_dependency_matrix": {
            "M1": ["M2", "M3", "M4", "M5"],
        },
        "shared_usage_clusters": [
            {"cluster_id": 1, "modules": ["adapter.a"]},
            {"cluster_id": 2, "modules": ["adapter.a"]},
        ],
        "dependency_type_breakdown": {"hard": 4},
    }
    ga_file.write_text(json.dumps(ga_payload), encoding="utf-8")
    monkeypatch.setattr(report_helpers, "get_canonical_report", lambda root, name: ga_file)
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda root: (
            {"adapter.a": "M1", "ui.b": "M2", "ui.c": "M3", "ui.d": "M4", "ui.e": "M5"},
            {"M1": "adapter.a", "M2": "ui.b", "M3": "ui.c", "M4": "ui.d", "M5": "ui.e"},
            {},
            {},
        ),
    )

    # 1. Non-compact
    raw_noncompact = get_layer_isolation(str(tmp_path), layer_name="adapter", compact=False)
    res_nc = json.loads(raw_noncompact)
    bv_nc = res_nc["boundary_violations"]
    assert bv_nc["total"] == 4
    assert bv_nc["truncated"] is False
    assert "items" in bv_nc
    assert len(bv_nc["items"]) == 4
    assert "evidence" not in bv_nc
    assert "evidence_scope" not in bv_nc
    assert "expand" not in bv_nc

    # 2. Compact
    raw_compact = get_layer_isolation(str(tmp_path), layer_name="adapter", compact=True, max_boundary_violations=2)
    res_c = json.loads(raw_compact)
    bv_c = res_c["boundary_violations"]
    assert bv_c["total"] == 4
    assert bv_c["truncated"] is True
    assert "evidence" in bv_c
    assert len(bv_c["evidence"]) == 2
    assert "items" not in bv_c
    assert "evidence_scope" not in bv_c
    assert bv_c["expand"] == {"compact": False, "max_boundary_violations": None}


def test_compact_evidence_contract__layer_isolation_live_fallback_preserves_evidence_scope(tmp_path, monkeypatch):
    from contextor.mcp import report_helpers

    class Graph:
        hard_edges = {
            "adapter.a": {"ui.b", "ui.c", "ui.d", "ui.e"}
        }
        soft_edges = {}

    class State:
        modules = {"adapter.a": object(), "ui.b": object(), "ui.c": object(), "ui.d": object(), "ui.e": object()}
        dependency_graph = Graph()

    class Engine:
        state = State()

    monkeypatch.setattr(report_helpers, "get_canonical_report", lambda root, name: None)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda root: Engine())

    # 1. Compact live fallback
    raw_c = get_layer_isolation(str(tmp_path), layer_name="adapter", compact=True)
    res_c = json.loads(raw_c)
    assert res_c["boundary_violations"]["evidence_scope"] == "cross_boundary_edges_not_policy_violations"
    assert "evidence" in res_c["boundary_violations"]

    # 2. Non-compact live fallback
    raw_nc = get_layer_isolation(str(tmp_path), layer_name="adapter", compact=False)
    res_nc = json.loads(raw_nc)
    assert res_nc["boundary_violations"]["evidence_scope"] == "cross_boundary_edges_not_policy_violations"
    assert "items" in res_nc["boundary_violations"]


def test_compact_evidence_contract__file_edit_context_collections_include_evidence(tmp_path, monkeypatch):
    class Graph:
        hard_edges = {
            "pkg.mod": {"pkg.dep1", "pkg.dep2", "pkg.dep3", "pkg.dep4"},
            "pkg.con1": {"pkg.mod"},
            "pkg.con2": {"pkg.mod"},
            "pkg.con3": {"pkg.mod"},
            "pkg.con4": {"pkg.mod"},
            "tests.test_1": {"pkg.mod"},
            "tests.test_2": {"pkg.mod"},
            "tests.test_3": {"pkg.mod"},
            "tests.test_4": {"pkg.mod"},
        }
        soft_edges = {}

    class State:
        resync_required = False
        modules = {
            "pkg.mod": object(),
            "pkg.dep1": object(), "pkg.dep2": object(), "pkg.dep3": object(), "pkg.dep4": object(),
            "pkg.con1": object(), "pkg.con2": object(), "pkg.con3": object(), "pkg.con4": object(),
            "tests.test_1": object(), "tests.test_2": object(), "tests.test_3": object(), "tests.test_4": object(),
        }
        artifacts = {
            "pkg.mod": {
                "symbols": {
                    "functions": ["f1", "f2", "f3", "f4"],
                    "classes": [],
                    "methods": [],
                    "globals": [],
                },
                "consumers": {},
            }
        }
        dependency_graph = Graph()
        cached_analytics = {}
        cached_analytics_state = "deferred"

    class Engine:
        state = State()

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda root: Engine())
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda root: (
            {}, {}, {}, {}
        ),
    )

    target_file = tmp_path / "pkg" / "mod.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("def f1(): pass\n", encoding="utf-8")

    raw = get_file_edit_context(str(tmp_path), file_path="pkg/mod.py", compact=True)
    res = json.loads(raw)

    pa = res["public_api"]
    assert "evidence" in pa
    assert isinstance(pa["evidence"], dict)
    assert pa["total"] == 4
    assert len(pa["evidence"]) == 3
    assert pa["truncated"] is True
    assert pa["expand"] == {"compact": False, "max_items": None}

    imp = res["imports"]
    assert "evidence" in imp
    assert imp["total"] == 4
    assert len(imp["evidence"]) == 3
    assert imp["truncated"] is True
    assert imp["expand"] == {"compact": False, "max_items": None}

    con = res["consumers"]
    assert "evidence" in con
    assert con["total"] == 8
    assert len(con["evidence"]) == 3
    assert con["truncated"] is True
    assert con["expand"] == {"compact": False, "max_items": None}

    tc = res["tests_covering"]
    assert "evidence" in tc
    assert tc["total"] == 4
    assert len(tc["evidence"]) == 3
    assert tc["truncated"] is True
    assert tc["expand"] == {"compact": False, "max_items": None}


def test_compact_evidence_contract__update_file_collections_include_evidence(tmp_path, monkeypatch):
    update_calls = []

    class UpdateRes:
        status = "UPDATED"
        file_path = str(tmp_path / "pkg" / "a.py")
        graph_state = "fresh"
        dependencies_state = "fresh"
        blast_radius_state = "fresh"
        local_metrics_state = "fresh"
        global_metrics_state = "fresh"
        artifact_consumption_state = "fresh"
        affected_modules = ["pkg.m1", "pkg.m2", "pkg.m3", "pkg.m4"]
        delta = None

    class Engine:
        state = type("State", (), {"artifacts": {}})()
        def update_file(self, path):
            update_calls.append(path)
            return UpdateRes()

    engine = Engine()
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda root: engine)
    monkeypatch.setattr("contextor.core.live_state.connect", lambda root: None)
    monkeypatch.setattr("contextor.mcp.tools.update_file._persist_live_engine", lambda root, eng: True)
    monkeypatch.setattr("contextor.mcp.tools.update_file._semantic_artifact_diff", lambda old, new: {
        "changed_symbol_count": 4,
        "body_change_count": 0,
        "body_only_changes_tracked": False,
        "symbols_added": ["s1", "s2", "s3", "s4"],
        "symbols_removed": [],
        "signatures_changed": {},
        "bodies_changed": [],
        "affected_symbols": ["s1", "s2", "s3", "s4"],
    })

    file_path = tmp_path / "pkg" / "a.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("x = 1\n", encoding="utf-8")

    raw = update_file(str(tmp_path), file_path="pkg/a.py", compact=True)
    res = json.loads(raw)

    assert len(update_calls) == 1, "update_file MUST NOT perform extra analysis/update calls"

    aff = res["affected_modules"]
    assert "evidence" in aff
    assert aff["total"] == 4
    assert len(aff["evidence"]) == 3
    assert aff["truncated"] is True
    assert "expand" not in aff

    diff = res["semantic_diff"]
    sym_added = diff["symbols_added"]
    assert "evidence" in sym_added
    assert sym_added["total"] == 4
    assert len(sym_added["evidence"]) == 3
    assert sym_added["truncated"] is True
    assert "expand" not in sym_added


def test_compact_evidence_contract__update_file_compact_does_not_advertise_mutating_expand():
    diff = {
        "symbols_added": ["s1", "s2", "s3", "s4"],
        "symbols_removed": ["r1", "r2", "r3", "r4"],
        "signatures_changed": {
            "k1": {"before": "b1", "after": "a1"},
            "k2": {"before": "b2", "after": "a2"},
            "k3": {"before": "b3", "after": "a3"},
            "k4": {"before": "b4", "after": "a4"},
        },
        "bodies_changed": ["b1", "b2", "b3", "b4"],
        "affected_symbols": ["a1", "a2", "a3", "a4"],
    }
    view = _semantic_diff_view(diff, max_items=10, compact=True)

    for key in ("symbols_added", "symbols_removed", "signatures_changed", "bodies_changed", "affected_symbols"):
        col = view[key]
        assert col["total"] == 4
        assert col["truncated"] is True
        assert len(col["evidence"]) == 3
        assert "expand" not in col


def test_compact_evidence_contract__zero_items_returns_empty_evidence_not_truncated():
    view = _semantic_diff_view({"symbols_added": []}, max_items=10, compact=True)
    col = view["symbols_added"]
    assert col["total"] == 0
    assert col["truncated"] is False
    assert col["evidence"] == []
    assert "expand" not in col


def test_compact_evidence_contract__one_item_returns_one_evidence_not_truncated():
    view = _semantic_diff_view({"symbols_added": ["sym1"]}, max_items=10, compact=True)
    col = view["symbols_added"]
    assert col["total"] == 1
    assert col["truncated"] is False
    assert col["evidence"] == ["sym1"]
    assert "expand" not in col


def test_compact_evidence_contract__three_items_returns_three_not_truncated():
    view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3"]}, max_items=10, compact=True)
    col = view["symbols_added"]
    assert col["total"] == 3
    assert col["truncated"] is False
    assert col["evidence"] == ["s1", "s2", "s3"]
    assert "expand" not in col


def test_compact_evidence_contract__four_items_returns_three_and_truncated():
    view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3", "s4"]}, max_items=10, compact=True)
    col = view["symbols_added"]
    assert col["total"] == 4
    assert col["truncated"] is True
    assert col["evidence"] == ["s1", "s2", "s3"]
    assert "expand" not in col


def test_compact_evidence_contract__explicit_limit_one_caps_evidence_at_one():
    view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3", "s4"]}, max_items=1, compact=True)
    col = view["symbols_added"]
    assert col["total"] == 4
    assert col["truncated"] is True
    assert col["evidence"] == ["s1"]
    assert len(col["evidence"]) == 1


def test_compact_evidence_contract__null_limit_still_caps_compact_evidence_at_three():
    view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3", "s4", "s5"]}, max_items=None, compact=True)
    col = view["symbols_added"]
    assert col["total"] == 5
    assert col["truncated"] is True
    assert len(col["evidence"]) == 3
    assert col["evidence"] == ["s1", "s2", "s3"]


def test_compact_evidence_contract__compact_false_preserves_existing_full_items_contract():
    view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3", "s4"]}, max_items=10, compact=False)
    col = view["symbols_added"]
    assert col["total"] == 4
    assert col["truncated"] is False
    assert "items" in col
    assert col["items"] == ["s1", "s2", "s3", "s4"]
    assert "evidence" not in col


def test_compact_evidence_contract__evidence_is_exact_prefix_of_full_collection():
    full_view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3", "s4"]}, max_items=10, compact=False)
    compact_view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3", "s4"]}, max_items=10, compact=True)
    assert compact_view["symbols_added"]["evidence"] == full_view["symbols_added"]["items"][:3]


def test_compact_evidence_contract__update_file_docs_require_noncompact_and_unbounded_for_complete_evidence():
    from contextor.mcp import documentation
    doc_path = documentation.DOCS_DIR / "update_file.json"
    doc = json.loads(doc_path.read_text(encoding="utf-8"))
    params_text = "\n".join(doc.get("parameters", []))

    assert "compact=false" in params_text
    assert "max_items=null" in params_text
    assert "compact=false and max_items=null" in params_text
    assert "compact=false or max_items=null" not in params_text

import ast
import json
from types import SimpleNamespace

import pytest

from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.tools import get_symbol_call_context as call_tool


_MODULE = "pkg.graph"
_ROOT = f"{_MODULE}::root"


def _edge(module, caller, callee, line=2):
    return (f"{module}::{caller}", f"{module}::{callee}", line, "direct")


def _install(
    monkeypatch,
    *,
    modules=None,
    registry=None,
):
    module_specs = modules or {
        _MODULE: {
            "edges": [_edge(_MODULE, "root", "callee")],
            "symbols": {"root", "callee"},
            "materialized": True,
            "stale": False,
        }
    }
    state = RepositoryAnalysisState(
        modules={module: object() for module in module_specs},
        artifacts={
            module: {"own_symbols": sorted(spec["symbols"])}
            for module, spec in module_specs.items()
        },
        module_usages={
            module: ModuleUsageFacts(
                symbol_calls=tuple(spec["edges"]),
                symbol_calls_materialized=spec.get("materialized", True),
            )
            for module, spec in module_specs.items()
        },
    )
    for module, spec in module_specs.items():
        if spec.get("stale"):
            state.module_parse_freshness[module] = {
                "state": "stale",
                "error": "invalid syntax",
                "line_number": 1,
            }
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: SimpleNamespace(state=state),
    )
    if registry is None:
        identities = sorted(
            f"{module}::{symbol}"
            for module, spec in module_specs.items()
            for symbol in spec["symbols"]
        )
        registry = {
            identity: f"A{index}/1"
            for index, identity in enumerate(identities, 1)
        }
    reads = {"count": 0}

    def read_registries(_root):
        reads["count"] += 1
        return ({}, {}, registry, {value: key for key, value in registry.items()})

    monkeypatch.setattr(query_helpers, "read_registries", read_registries)
    return state, registry, reads


def _call(symbol=_ROOT, **kwargs):
    return json.loads(
        call_tool.get_symbol_call_context(
            "C:/repo",
            symbol,
            representation=kwargs.pop("representation", "named"),
            **kwargs,
        )
    )


def test_get_symbol_call_context__uses_freshness_helper_without_ast_parse(monkeypatch):
    _install(monkeypatch)
    freshness_calls = []

    def target_local_freshness(*args, **kwargs):
        freshness_calls.append((args, kwargs))
        return {"workspace_sync": "verified"}

    monkeypatch.setattr(query_helpers, "build_state_freshness", target_local_freshness)
    monkeypatch.setattr(ast, "parse", lambda *_args, **_kwargs: pytest.fail("ast.parse"))

    result = _call(direction="callees")

    assert result["status"] == "ok"
    assert result["callees"]["items"]
    assert result["state_freshness"] == {"workspace_sync": "verified"}
    assert len(freshness_calls) == 1


def test_get_symbol_call_context__active_artifact_id_matches_canonical(monkeypatch):
    _state, registry, _reads = _install(monkeypatch)
    artifact_id = registry[_ROOT]

    canonical = _call(_ROOT, direction="callees")
    by_id = _call(artifact_id, direction="callees")

    assert by_id == canonical


def test_get_symbol_call_context__lowercase_artifact_id(monkeypatch):
    _state, registry, _reads = _install(monkeypatch)

    result = _call(registry[_ROOT].lower(), direction="callees")

    assert result["status"] == "ok"
    assert result["symbol"] == _ROOT


def test_get_symbol_call_context__missing_artifact_id_is_exact_not_found(monkeypatch):
    _install(monkeypatch)
    monkeypatch.setattr(call_tool, "_walk", lambda *_args: pytest.fail("BFS called"))

    result = _call("A999999/1")

    assert result == {
        "status": "not_found",
        "query": "A999999/1",
        "query_kind": "artifact_id",
        "similar_candidates": [],
    }


def test_get_symbol_call_context__missing_artifact_id_does_not_require_live_state(
    monkeypatch,
):
    _install(monkeypatch)
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda *_args: pytest.fail("LIVE engine accessed"),
    )
    monkeypatch.setattr(call_tool, "_walk", lambda *_args: pytest.fail("BFS called"))

    result = _call("A999999/1")

    assert result == {
        "status": "not_found",
        "query": "A999999/1",
        "query_kind": "artifact_id",
        "similar_candidates": [],
    }


def test_get_symbol_call_context__resolved_artifact_id_missing_module_never_fuzzy(
    monkeypatch,
):
    missing_identity = "pkg.missing::root"
    _state, _registry, reads = _install(
        monkeypatch,
        registry={
            _ROOT: "A1/1",
            missing_identity: "A2/1",
        },
    )
    real_resolver = query_helpers.resolve_artifact_identity
    resolver_calls = {"count": 0}

    def resolve_once(query, path_to_id, id_to_path):
        resolver_calls["count"] += 1
        if resolver_calls["count"] > 1:
            pytest.fail("fuzzy resolver called after exact artifact ID resolution")
        return real_resolver(query, path_to_id, id_to_path)

    monkeypatch.setattr(query_helpers, "resolve_artifact_identity", resolve_once)
    monkeypatch.setattr(call_tool, "_walk", lambda *_args: pytest.fail("BFS called"))

    result = _call("A2/1")

    assert result == {
        "status": "error",
        "error": "unknown_symbol",
        "symbol": missing_identity,
    }
    assert resolver_calls["count"] == 1
    assert reads["count"] == 1


def test_get_symbol_call_context__resolved_artifact_id_unknown_symbol_never_fuzzy(
    monkeypatch,
):
    unknown_identity = f"{_MODULE}::ghost"
    _state, _registry, reads = _install(
        monkeypatch,
        registry={
            _ROOT: "A1/1",
            f"{_MODULE}::callee": "A2/1",
            unknown_identity: "A3/1",
        },
    )
    real_resolver = query_helpers.resolve_artifact_identity
    resolver_calls = {"count": 0}

    def resolve_once(query, path_to_id, id_to_path):
        resolver_calls["count"] += 1
        if resolver_calls["count"] > 1:
            pytest.fail("fuzzy resolver called after exact artifact ID resolution")
        return real_resolver(query, path_to_id, id_to_path)

    monkeypatch.setattr(query_helpers, "resolve_artifact_identity", resolve_once)
    monkeypatch.setattr(call_tool, "_walk", lambda *_args: pytest.fail("BFS called"))

    result = _call("A3/1")

    assert result == {
        "status": "error",
        "error": "unknown_symbol",
        "symbol": unknown_identity,
    }
    assert resolver_calls["count"] == 1
    assert reads["count"] == 1


def test_get_symbol_call_context__plain_leaf_remains_rejected(monkeypatch):
    _install(monkeypatch)
    monkeypatch.setattr(
        query_helpers,
        "resolve_artifact_identity",
        lambda *_args: pytest.fail("resolver called"),
    )

    result = _call("root")

    assert result == {
        "status": "error",
        "error": "exact_qualified_symbol_required",
        "expected": "module::symbol",
    }


def test_get_symbol_call_context__canonical_success_uses_no_identity_resolver(monkeypatch):
    _state, _registry, reads = _install(monkeypatch)
    monkeypatch.setattr(
        query_helpers,
        "resolve_artifact_identity",
        lambda *_args: pytest.fail("resolver called"),
    )

    result = _call(_ROOT, direction="callees")

    assert result["status"] == "ok"
    assert reads["count"] == 1


def test_get_symbol_call_context__artifact_id_reuses_registry_snapshot(monkeypatch):
    _state, registry, reads = _install(monkeypatch)

    result = _call(registry[_ROOT], direction="callees", representation="auto")

    assert result["status"] == "ok"
    assert reads["count"] == 1


def test_get_symbol_call_context__qualified_typo_is_suggestion_only(monkeypatch):
    _install(monkeypatch)
    monkeypatch.setattr(call_tool, "_walk", lambda *_args: pytest.fail("BFS called"))

    result = _call(f"{_MODULE}::rooot")

    assert result["status"] == "error"
    assert result["error"] == "unknown_symbol"
    assert result["similar_candidates"]
    assert result["similar_candidates"][0]["artifact"] == _ROOT


def test_get_symbol_call_context__valid_module_typo_prefilters_before_ranking(monkeypatch):
    other = "pkg.other"
    modules = {
        _MODULE: {"edges": [], "symbols": {"root"}, "materialized": True},
        other: {"edges": [], "symbols": {"rooot"}, "materialized": True},
    }
    _install(monkeypatch, modules=modules)
    captured = {}
    real_resolver = query_helpers.resolve_artifact_identity

    def capture(query, path_to_id, id_to_path):
        captured["identities"] = set(path_to_id)
        return real_resolver(query, path_to_id, id_to_path)

    monkeypatch.setattr(query_helpers, "resolve_artifact_identity", capture)

    _call(f"{_MODULE}::rooot")

    assert captured["identities"] == {_ROOT}


def test_get_symbol_call_context__global_typo_scope_is_active_current_materialized_queryable(monkeypatch):
    modules = {
        "pkg.good": {"edges": [], "symbols": {"target"}, "materialized": True},
        "pkg.stale": {"edges": [], "symbols": {"target"}, "materialized": True, "stale": True},
        "pkg.unmaterialized": {"edges": [], "symbols": {"target"}, "materialized": False},
        "pkg.nonqueryable": {"edges": [], "symbols": set(), "materialized": True},
    }
    registry = {
        "pkg.good::target": "A1/1",
        "pkg.stale::target": "A2/1",
        "pkg.unmaterialized::target": "A3/1",
        "pkg.nonqueryable::target": "A4/1",
        "pkg.recovery::target": "A5/1",
    }
    _install(monkeypatch, modules=modules, registry=registry)
    captured = {}
    real_resolver = query_helpers.resolve_artifact_identity

    def capture(query, path_to_id, id_to_path):
        captured["identities"] = set(path_to_id)
        return real_resolver(query, path_to_id, id_to_path)

    monkeypatch.setattr(query_helpers, "resolve_artifact_identity", capture)
    monkeypatch.setattr(call_tool, "_walk", lambda *_args: pytest.fail("BFS called"))

    result = _call("pkg.god::target")

    assert result["status"] == "error"
    assert result["error"] == "unknown_symbol"
    assert captured["identities"] == {"pkg.good::target"}


def test_get_symbol_call_context__ambiguity_fails_closed_without_traversal(monkeypatch):
    _install(monkeypatch)
    monkeypatch.setattr(
        query_helpers,
        "resolve_artifact_identity",
        lambda *_args: {
            "status": "ambiguous",
            "resolution": "exact_leaf",
            "query": f"{_MODULE}::rooot",
            "candidates": [{"artifact": _ROOT, "artifact_id": "A1/1"}],
        },
    )
    monkeypatch.setattr(call_tool, "_walk", lambda *_args: pytest.fail("BFS called"))

    result = _call(f"{_MODULE}::rooot")

    assert result["status"] == "ambiguous"
    assert result["candidates"] == [{"artifact": _ROOT, "artifact_id": "A1/1"}]


def test_get_symbol_call_context__method_artifact_id_uses_normal_traversal(monkeypatch):
    method = f"{_MODULE}::Worker.run"
    finish = f"{_MODULE}::Worker.finish"
    modules = {
        _MODULE: {
            "edges": [(method, finish, 9, "direct")],
            "symbols": {"Worker.run", "Worker.finish"},
            "materialized": True,
        }
    }
    _state, registry, _reads = _install(monkeypatch, modules=modules)

    result = _call(registry[method], direction="callees")

    assert result["status"] == "ok"
    assert result["symbol"] == method
    assert result["callees"]["items"][0]["callee"] == finish


def test_get_symbol_call_context__zero_edge_artifact_id_is_successful(monkeypatch):
    modules = {
        _MODULE: {"edges": [], "symbols": {"root"}, "materialized": True}
    }
    _state, registry, _reads = _install(monkeypatch, modules=modules)

    result = _call(registry[_ROOT])

    assert result["status"] == "ok"
    assert result["total_edges"] == result["returned_edges"] == 0


def test_get_symbol_call_context__artifact_id_keeps_unmaterialized_gate(monkeypatch):
    modules = {
        _MODULE: {"edges": [], "symbols": {"root"}, "materialized": False}
    }
    _state, registry, _reads = _install(monkeypatch, modules=modules)

    result = _call(registry[_ROOT])

    assert result["error"] == "symbol_calls_unmaterialized"
    assert result["available"] is False


def test_get_symbol_call_context__artifact_id_keeps_stale_gate(monkeypatch):
    modules = {
        _MODULE: {
            "edges": [],
            "symbols": {"root"},
            "materialized": True,
            "stale": True,
        }
    }
    _state, registry, _reads = _install(monkeypatch, modules=modules)

    result = _call(registry[_ROOT])

    assert result["status"] == "stale"
    assert result["available"] is False


def test_get_symbol_call_context__named_force_boundary_51200_vs_51201(monkeypatch):
    _install(monkeypatch)

    def run(named_bytes):
        monkeypatch.setattr(
            call_tool.mcp_rep,
            "serialized_json_bytes",
            lambda candidate: named_bytes
            if candidate["representation"] == "named"
            else 100,
        )
        return _call(_ROOT, direction="callees", representation="named")

    assert run(51200)["representation"] == "named"
    blocked = run(51201)
    assert blocked["status"] == "error"
    assert blocked["error"] == "large_named_output_requires_indexed_representation"
    assert blocked["named_candidate_bytes"] == 51201
    assert blocked["retry"] == {"representation": "indexed"}


def test_get_symbol_call_context__auto_savings_boundary_511_vs_512(monkeypatch):
    _install(monkeypatch)

    def run(indexed_bytes):
        monkeypatch.setattr(
            call_tool.mcp_rep,
            "serialized_json_bytes",
            lambda candidate: 1000
            if candidate["representation"] == "named"
            else indexed_bytes,
        )
        return _call(_ROOT, direction="callees", representation="auto")

    assert run(489)["representation"] == "named"
    assert run(488)["representation"] == "indexed"


def _install_padded_shape(monkeypatch, padding):
    def shape(**kwargs):
        return {
            "status": "ok",
            "symbol": kwargs["symbol"],
            "module": kwargs["module"],
            "representation": kwargs["selected_representation"],
            "returned_edges": 0,
            "total_edges": 0,
            "padding": "x" * padding["value"],
        }

    monkeypatch.setattr(call_tool, "_shape", shape)


def _calibrate_selected_payload(monkeypatch, target_bytes):
    padding = {"value": max(0, target_bytes - 500)}
    _install_padded_shape(monkeypatch, padding)
    for _attempt in range(10):
        raw = call_tool.get_symbol_call_context(
            "C:/repo",
            _ROOT,
            representation="named",
            allow_large_output=True,
        )
        difference = target_bytes - len(raw.encode("utf-8"))
        if difference == 0:
            return raw
        padding["value"] += difference
    raise AssertionError(f"could not calibrate payload to {target_bytes} bytes")


def test_get_symbol_call_context__output_guard_boundary_15360_vs_15361(monkeypatch):
    _install(monkeypatch)
    raw_15360 = _calibrate_selected_payload(monkeypatch, 15360)

    allowed = _call(_ROOT, representation="named")

    assert len(raw_15360.encode("utf-8")) == 15360
    assert allowed["status"] == "ok"

    _calibrate_selected_payload(monkeypatch, 15361)
    blocked = _call(_ROOT, representation="named")

    assert blocked["status"] == "confirmation_required"
    assert blocked["estimated_output_bytes"] == 15361


def test_get_symbol_call_context__allow_large_output_approves_15361(monkeypatch):
    _install(monkeypatch)
    raw = _calibrate_selected_payload(monkeypatch, 15361)

    approved = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        representation="named",
        allow_large_output=True,
    )

    assert len(raw.encode("utf-8")) == 15361
    assert approved == raw


# ---------------------------------------------------------------------------
# R3B: Single-Shot Auto-Bounding Tests
# ---------------------------------------------------------------------------


def _install_large_graph(monkeypatch, edge_count=100, symbol_prefix="callee_with_a_long_symbol_name_"):
    edges = [
        _edge(_MODULE, "root", f"{symbol_prefix}{i:03d}", line=i + 1)
        for i in range(edge_count)
    ]
    symbols = {"root"} | {f"{symbol_prefix}{i:03d}" for i in range(edge_count)}
    modules = {
        _MODULE: {
            "edges": edges,
            "symbols": symbols,
            "materialized": True,
            "stale": False,
        }
    }
    return _install(monkeypatch, modules=modules)


def test_get_symbol_call_context__auto_bounded_named_is_exact_prefix(monkeypatch):
    _install_large_graph(monkeypatch, edge_count=100)

    raw_bounded = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="named",
        allow_large_output=False,
        max_items=None,
    )
    bounded = json.loads(raw_bounded)

    raw_full = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="named",
        allow_large_output=True,
        max_items=None,
    )
    full = json.loads(raw_full)

    assert bounded["status"] == "ok"
    assert bounded["representation"] == "named"
    assert "_output" in bounded
    output_meta = bounded["_output"]
    assert output_meta["auto_bounded"] is True
    assert output_meta["bounded_collection"] == "edges"
    assert output_meta["warning_threshold_bytes"] == 15360
    assert output_meta["full_output_bytes"] == len(raw_full.encode("utf-8"))
    assert output_meta["full_output_bytes"] > 15360
    assert output_meta["requested_count"] == 100
    assert 1 <= output_meta["returned_count"] < 100
    assert bounded["returned_edges"] == output_meta["returned_count"]

    # Exact deterministic prefix assertion
    returned_count = output_meta["returned_count"]
    assert bounded["callees"]["items"] == full["callees"]["items"][:returned_count]
    assert bounded["representation_decision"] == full["representation_decision"]
    assert len(raw_bounded.encode("utf-8")) <= 15360


def test_get_symbol_call_context__auto_bounded_indexed_is_exact_prefix(monkeypatch):
    _install_large_graph(monkeypatch, edge_count=150)

    raw_bounded = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="indexed",
        allow_large_output=False,
        max_items=None,
    )
    bounded = json.loads(raw_bounded)

    raw_full = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="indexed",
        allow_large_output=True,
        max_items=None,
    )
    full = json.loads(raw_full)

    assert bounded["status"] == "ok"
    assert bounded["representation"] == "indexed"
    assert "_output" in bounded
    output_meta = bounded["_output"]
    assert output_meta["auto_bounded"] is True
    assert output_meta["bounded_collection"] == "edges"
    assert output_meta["full_output_bytes"] == len(raw_full.encode("utf-8"))
    assert output_meta["requested_count"] == 150
    assert 1 <= output_meta["returned_count"] < 150

    returned_count = output_meta["returned_count"]
    assert bounded["callees"]["items"] == full["callees"]["items"][:returned_count]
    assert bounded["representation_decision"] == full["representation_decision"]
    assert len(raw_bounded.encode("utf-8")) <= 15360


def test_get_symbol_call_context__auto_representation_is_not_renegotiated_during_bounding(monkeypatch):
    _install_large_graph(monkeypatch, edge_count=150)

    raw_full = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="auto",
        allow_large_output=True,
        max_items=None,
    )
    full = json.loads(raw_full)
    assert len(raw_full.encode("utf-8")) > 15360

    raw_bounded = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="auto",
        allow_large_output=False,
        max_items=None,
    )
    bounded = json.loads(raw_bounded)

    assert bounded["status"] == "ok"
    assert bounded["representation"] == full["representation"]
    assert bounded["_output"]["auto_bounded"] is True
    assert bounded["representation_decision"] == full["representation_decision"]


def test_get_symbol_call_context__explicit_named_is_not_silently_changed_to_indexed_for_size(monkeypatch):
    _install_large_graph(monkeypatch, edge_count=100)

    raw_bounded = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="named",
        allow_large_output=False,
        max_items=None,
    )
    bounded = json.loads(raw_bounded)

    assert bounded["status"] == "ok"
    assert bounded["representation"] == "named"
    assert bounded["_output"]["auto_bounded"] is True


def test_get_symbol_call_context__explicit_named_hard_ceiling_precedes_auto_bounding(monkeypatch):
    # Setup graph where named candidate > 51200 bytes (e.g. 350 edges, named ~65 KB)
    _install_large_graph(monkeypatch, edge_count=350, symbol_prefix="callee_with_a_very_long_symbol_name_")

    raw_bounded = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="named",
        allow_large_output=False,
        max_items=None,
    )
    bounded = json.loads(raw_bounded)

    assert bounded["status"] == "error"
    assert bounded["error"] == "large_named_output_requires_indexed_representation"
    assert bounded["retry"] == {"representation": "indexed"}
    assert "_output" not in bounded

    approved = json.loads(call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="named",
        allow_large_output=True,
        max_items=None,
    ))
    assert approved["status"] == "error"
    assert approved["error"] == "large_named_output_requires_indexed_representation"


def test_get_symbol_call_context__auto_large_named_requires_indexed_identities(monkeypatch):
    _install_large_graph(monkeypatch, edge_count=350, symbol_prefix="callee_with_a_very_long_symbol_name_")
    original_read_registries = call_tool.query_helpers.read_registries

    def incomplete_registry(root):
        registries = list(original_read_registries(root))
        registries[2] = {}
        return tuple(registries)

    monkeypatch.setattr(call_tool.query_helpers, "read_registries", incomplete_registry)

    result = _call(
        _ROOT,
        direction="callees",
        representation="auto",
        max_items=None,
    )

    assert result["status"] == "error"
    assert result["error"] == "large_named_output_requires_indexed_identities"


def test_get_symbol_call_context__auto_bounded_full_output_bytes_matches_allow_large_original(monkeypatch):
    # Setup graph with long symbol names so 50 items exceed 15360 B
    _install_large_graph(
        monkeypatch,
        edge_count=90,
        symbol_prefix="callee_with_a_very_long_symbol_name_padding_to_exceed_fifteen_kib_" + ("x" * 250) + "_",
    )

    raw_bounded = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="named",
        allow_large_output=False,
        max_items=50,
    )
    bounded = json.loads(raw_bounded)

    raw_full = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="named",
        allow_large_output=True,
        max_items=50,
    )

    assert "_output" in bounded
    assert bounded["_output"]["requested_count"] == 50
    assert bounded["_output"]["full_output_bytes"] == len(raw_full.encode("utf-8"))



def test_get_symbol_call_context__auto_bounded_payload_never_exceeds_threshold(monkeypatch):
    _install_large_graph(monkeypatch, edge_count=200)

    for rep in ("named", "indexed", "auto"):
        for max_items in (20, 50, None):
            raw = call_tool.get_symbol_call_context(
                "C:/repo",
                _ROOT,
                direction="callees",
                representation=rep,
                allow_large_output=False,
                max_items=max_items,
            )
            assert len(raw.encode("utf-8")) <= 15360


def test_get_symbol_call_context__auto_bounding_reuses_existing_traversal_and_registry_snapshot(monkeypatch):
    _state, _registry, reads = _install_large_graph(monkeypatch, edge_count=100)

    walk_calls = {"count": 0}
    original_walk = call_tool._walk

    def tracking_walk(*args, **kwargs):
        walk_calls["count"] += 1
        return original_walk(*args, **kwargs)

    monkeypatch.setattr(call_tool, "_walk", tracking_walk)

    raw = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="both",
        representation="named",
        allow_large_output=False,
        max_items=None,
    )
    res = json.loads(raw)

    assert res["status"] == "ok"
    assert res["_output"]["auto_bounded"] is True
    # Registries read exactly once
    assert reads["count"] == 1
    # Direction="both" calls _walk exactly twice (once for callers, once for callees), 0 extra calls during binary search
    assert walk_calls["count"] == 2


def test_get_symbol_call_context__one_edge_too_large_still_requires_confirmation(monkeypatch):
    huge_callee = "callee_" + ("y" * 18000)
    edges = [_edge(_MODULE, "root", huge_callee, line=10)]
    symbols = {"root", huge_callee}
    modules = {
        _MODULE: {
            "edges": edges,
            "symbols": symbols,
            "materialized": True,
            "stale": False,
        }
    }
    _install(monkeypatch, modules=modules)

    raw = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="named",
        allow_large_output=False,
        max_items=None,
    )
    res = json.loads(raw)

    assert res["status"] == "confirmation_required"
    assert res["retry"] == {"allow_large_output": True}


def test_get_symbol_call_context__allow_large_output_returns_original_unbounded_selection(monkeypatch):
    _install_large_graph(monkeypatch, edge_count=100)

    raw = call_tool.get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        representation="named",
        allow_large_output=True,
        max_items=None,
    )
    res = json.loads(raw)

    assert res["status"] == "ok"
    assert "_output" not in res
    assert len(res["callees"]["items"]) == 100
    assert len(raw.encode("utf-8")) > 15360

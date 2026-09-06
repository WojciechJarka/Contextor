import json
import importlib
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from contextor.core.analysis.incremental import graph_ops
from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.domain.graph import ProjectGraph
from contextor.core.report_query import normalize_module_path_to_dotted
from contextor.mcp import query_helpers, representation as mcp_rep, runtime as mcp_runtime
from contextor.mcp.tools.get_artifact_blast_radius import get_artifact_blast_radius
from contextor.mcp.tools.get_module_blast_radius import get_module_blast_radius


class _LiveRegistry:
    def __init__(self, state):
        self._state = state
        self.read_transaction_count = 0

    @contextmanager
    def read_transaction(self):
        self.read_transaction_count += 1
        yield


def _registry_state():
    modules = {
        "pkg.mod": "10/1",
        "pkg.consumer": "11/1",
        "pkg.after": "12/1",
        "pkg.leaf": "13/1",
        "tests.consumer": "14/1",
        "pkg.dep": "15/1",
        "pkg.soft_after": "16/1",
    }
    artifacts = {
        "pkg.mod::alpha": "A100/1",
        "pkg.mod::beta": "A101/1",
        "pkg.mod::gamma": "A102/1",
    }
    return {
        "module_registry": {"path_to_id": modules, "id_to_path": {v: k for k, v in modules.items()}},
        "artifact_registry": {"path_to_id": artifacts, "id_to_path": {v: k for k, v in artifacts.items()}},
    }


def _fixture(monkeypatch):
    state = RepositoryAnalysisState(
        modules={
            name: SimpleNamespace(module_id=module_id, path=name.replace(".", "/") + ".py")
            for name, module_id in {
                "pkg.mod": "10/1",
                "pkg.consumer": "11/1",
                "pkg.after": "12/1",
                "pkg.leaf": "13/1",
                "tests.consumer": "14/1",
                "pkg.dep": "15/1",
                "pkg.soft_after": "16/1",
            }.items()
        },
        artifacts={
            "pkg.mod": {
                "own_symbols": ["alpha", "beta", "gamma"],
                "symbols": {
                    "functions": ["alpha", "beta", "gamma"],
                    "signatures": {"alpha": "def alpha()", "beta": "def beta()", "gamma": "def gamma()"},
                },
            }
        },
        artifact_consumption={
            "pkg.mod::alpha": {"consumers": ["pkg.consumer", "tests.consumer"], "channels": {}},
            "pkg.mod::beta": {"consumers": ["pkg.consumer"], "channels": {}},
            "pkg.mod::gamma": {"consumers": [], "channels": {}},
        },
        artifact_consumption_state="fresh",
        dependency_graph=ProjectGraph(
            hard_edges={
                "pkg.consumer": {"pkg.dep"},
                "pkg.after": {"pkg.consumer"},
                "pkg.leaf": {"pkg.after"},
                "tests.consumer": {"pkg.consumer"},
            },
            soft_edges={"pkg.soft_after": {"pkg.consumer"}},
        ),
        cached_analytics={
            "module_layers": {
                "pkg.mod": "engine",
                "pkg.consumer": "runtime",
                "pkg.after": "runtime",
                "pkg.leaf": "contract",
                "tests.consumer": "tests",
                "pkg.soft_after": "runtime",
            }
        },
        cached_analytics_state="fresh",
    )
    state.provenance = "live"
    registry = _LiveRegistry(_registry_state())
    engine = SimpleNamespace(state=state, provenance="live", registry=registry)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        query_helpers,
        "build_state_freshness",
        lambda *args, **kwargs: {
            "canonical_state": "fresh",
            "workspace_sync": "unverified",
            "canonical_revision": 7,
            "provenance": "live",
            "families": {"module": "fresh", "graph": "fresh", "artifact_consumption": "fresh"},
            "advisory_warning": None,
        },
    )
    return state, registry


def _decode_indexed(payload, registry_state):
    id_to_name = registry_state["module_registry"]["id_to_path"]
    sets = payload["sets"]
    index = payload["module_index"]

    def decode(ref):
        return sorted(id_to_name[index[ordinal]] for ordinal in sets[ref])

    layer_payload = payload.get("module_layers", {})
    layer_dictionary = layer_payload.get("dictionary", [])
    module_layers = {
        id_value: (
            layer_dictionary[layer_payload["codes"][ordinal]]
            if layer_payload["codes"][ordinal] is not None
            else None
        )
        for ordinal, id_value in enumerate(index)
    }

    def architecture_semantics(entry, direct):
        architecture = entry["architecture"]
        if not architecture.get("available"):
            return architecture
        definer_layer = architecture.get("definer_layer")
        same_module = [module for module in direct if module == payload["module"]]
        # The registry maps IDs to names; direct values are names, so look up
        # the layer by the reverse index position instead of by name.
        name_to_layer = {
            id_to_name[module_id]: layer
            for module_id, layer in module_layers.items()
            if module_id in id_to_name
        }
        same_layer = [module for module in direct if module != payload["module"] and name_to_layer.get(module) == definer_layer]
        tests = [module for module in direct if module != payload["module"] and name_to_layer.get(module) == "tests"]
        unknown = [module for module in direct if module != payload["module"] and name_to_layer.get(module) is None]
        cross = [
            {"module": module, "layer": name_to_layer[module]}
            for module in direct
            if module != payload["module"]
            and name_to_layer.get(module) not in (None, "tests", definer_layer)
        ]
        return {
            **architecture,
            "identity_partitions": {
                "same_module": same_module,
                "same_layer": same_layer,
                "cross_layer": cross,
                "tests": tests,
                "unknown": unknown,
            },
        }

    result = {}
    for artifact_id, entry in payload["artifacts"].items():
        downstream = entry["downstream_module_reachability"]
        direct = decode(entry["direct_set_ref"])
        downstream_items = decode(downstream["downstream_set_ref"]) if downstream.get("available") else None
        downstream_semantics = dict(downstream)
        if downstream_items is not None:
            downstream_semantics["items"] = downstream_items
            layers_by_name = {
                id_to_name[module_id]: layer
                for module_id, layer in module_layers.items()
                if module_id in id_to_name
            }
            production = [module for module in downstream_items if layers_by_name.get(module) not in (None, "tests")]
            tests = [module for module in downstream_items if layers_by_name.get(module) == "tests"]
            unknown = [module for module in downstream_items if layers_by_name.get(module) is None]
            downstream_semantics.update({
                "production_downstream_sample": {"total": len(production), "items": production, "truncated": False},
                "test_downstream_sample": {"total": len(tests), "items": tests, "truncated": False},
                "unknown_downstream_sample": {"total": len(unknown), "items": unknown, "truncated": False},
            })
        result[artifact_id] = {
            "symbol": entry["symbol"],
            "kind": entry["kind"],
            "signature": entry["signature"],
            "direct": direct,
            "architecture": architecture_semantics(entry, direct),
            "downstream": downstream_semantics,
        }
    aggregate = payload.get("aggregate")
    downstream_ref = aggregate.get("downstream_set_ref")
    return result, {
        "direct": decode(aggregate["direct_set_ref"]),
        "downstream": decode(downstream_ref) if downstream_ref is not None else None,
        "consumed": aggregate["consumed_artifact_ids"],
        "unconsumed": aggregate["unconsumed_artifact_ids"],
        "impact": aggregate["highest_impact_artifact_ids"],
        "downstream_state": {
            key: value
            for key, value in aggregate["unique_downstream_consumers"].items()
            if key != "set_ref"
        },
    }


def test_default_is_complete_and_one_registry_read_one_reverse_build(tmp_path, monkeypatch):
    _, registry = _fixture(monkeypatch)
    calls = 0
    closures = 0
    original_build = graph_ops.build_reverse_adjacency
    original_closure = graph_ops.calculate_affected_set_from_reverse

    def counted_build(*graphs):
        nonlocal calls
        calls += 1
        return original_build(*graphs)

    def counted_closure(*args):
        nonlocal closures
        closures += 1
        return original_closure(*args)

    monkeypatch.setattr(graph_ops, "build_reverse_adjacency", counted_build)
    monkeypatch.setattr(graph_ops, "calculate_affected_set_from_reverse", counted_closure)
    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod"))

    assert result["artifact_count_total"] == result["artifact_count_returned"] == 3
    assert len(result["artifacts"]) == 3
    assert result["aggregate"]["artifact_count_returned"] == 3
    assert calls == 1
    assert registry.read_transaction_count == 1
    assert closures == 2


def test_named_and_indexed_are_semantically_lossless(tmp_path, monkeypatch):
    _fixture(monkeypatch)
    named = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=False, representation="named"))
    indexed = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=True, representation="indexed"))
    decoded_artifacts, decoded_aggregate = _decode_indexed(indexed, _registry_state())

    assert indexed["schema"] == "module_blast_radius.lossless.v1"
    assert len(indexed["artifacts"]) == 3
    for artifact_id, expected in named["artifacts"].items():
        actual = decoded_artifacts[artifact_id]
        assert actual["symbol"] == expected["symbol"]
        assert actual["kind"] == expected["kind"]
        assert actual["signature"] == expected["signature"]
        assert actual["direct"] == expected["direct_consumers"]["items"]
        expected_architecture = expected["architecture"]
        assert actual["architecture"]["available"] == expected_architecture["available"]
        assert actual["architecture"]["identity_partitions"] == expected_architecture["identity_partitions"]
        expected_downstream = expected["downstream_module_reachability"]
        assert actual["downstream"]["available"] == expected_downstream["available"]
        assert actual["downstream"].get("items") == expected_downstream.get("items")
        for key in ("layer_classification_available", "production_downstream_count", "test_downstream_count", "unknown_layer_downstream_count"):
            assert actual["downstream"].get(key) == expected_downstream.get(key)
        if expected_downstream.get("layer_classification_available"):
            for key in ("production_downstream_sample", "test_downstream_sample", "unknown_downstream_sample"):
                assert actual["downstream"].get(key) == expected_downstream.get(key)
    assert decoded_aggregate["direct"] == named["aggregate"]["unique_direct_consumers"]["items"]
    assert decoded_aggregate["downstream"] == named["aggregate"]["unique_downstream_consumers"]["items"]
    assert decoded_aggregate["consumed"] == named["aggregate"]["consumed_artifact_ids"]
    assert decoded_aggregate["unconsumed"] == named["aggregate"]["unconsumed_artifact_ids"]
    assert decoded_aggregate["impact"] == named["aggregate"]["highest_impact_artifact_ids"]


def test_all_downstream_is_complete_and_aggregate_is_disjoint(tmp_path, monkeypatch):
    _fixture(monkeypatch)
    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
    direct = set(result["aggregate"]["unique_direct_consumers"]["items"])
    downstream = set(result["aggregate"]["unique_downstream_consumers"]["items"])
    assert "tests.consumer" in direct
    assert "tests.consumer" not in downstream
    assert direct.isdisjoint(downstream)
    assert all(not collection.get("truncated") for artifact in result["artifacts"].values() for collection in (
        [artifact["direct_consumers"], artifact["downstream_module_reachability"]]
        if artifact["downstream_module_reachability"].get("available") else [artifact["direct_consumers"]]
    ))


def test_highest_impact_order_is_deterministic(tmp_path, monkeypatch):
    _fixture(monkeypatch)
    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
    impact = result["aggregate"]["highest_impact_artifact_ids"]
    facts = result["artifacts"]
    expected = sorted(impact, key=lambda artifact_id: (
        -facts[artifact_id]["downstream_module_reachability"].get("total_downstream_count", 0),
        -facts[artifact_id]["direct_consumers"]["total"],
        facts[artifact_id]["full_name"],
    ))
    assert impact == expected


def test_fields_projection_keeps_aggregate_full_but_returned_count_zero(tmp_path, monkeypatch):
    state, _ = _fixture(monkeypatch)
    symbols = [f"symbol_{index}" for index in range(12)]
    state.artifacts["pkg.mod"] = {"own_symbols": symbols, "symbols": {"functions": symbols}}
    state.artifact_consumption = {f"pkg.mod::{symbol}": {"consumers": [], "channels": {}} for symbol in symbols}
    module_only = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["module", "artifact_count_returned"]))
    aggregate_only = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["aggregate"]))
    full = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["artifacts", "artifact_count_returned", "aggregate"], allow_large_output=True))
    assert module_only["artifact_count_returned"] == 0
    assert aggregate_only["aggregate"]["artifact_count_returned"] == 0
    assert full["artifact_count_returned"] == len(full["artifacts"]) == 12
    assert full["aggregate"]["artifact_count_returned"] == 12


def test_path_and_active_id_resolution_use_canonical_normalizer(tmp_path, monkeypatch):
    state, registry = _fixture(monkeypatch)
    target = "contextor.core.reporting_engine.graph_analytics"
    state.modules = {target: SimpleNamespace(module_id="10/1", path="contextor/core/reporting_engine/graph_analytics.py")}
    state.artifacts = {target: {"own_symbols": ["analyze"], "symbols": {"functions": ["analyze"], "signatures": {"analyze": "def analyze()"}}}}
    state.artifact_consumption = {f"{target}::analyze": {"consumers": [], "channels": {}}}
    registry._state = {
        "module_registry": {"path_to_id": {target: "10/1"}, "id_to_path": {"10/1": target}},
        "artifact_registry": {"path_to_id": {f"{target}::analyze": "A100/1"}, "id_to_path": {"A100/1": f"{target}::analyze"}},
    }
    variants = [target, "contextor/core/reporting_engine/graph_analytics.py", r"contextor\core\reporting_engine\graph_analytics.py", str(tmp_path / "contextor" / "core" / "reporting_engine" / "graph_analytics.py"), "10/1"]
    for variant in variants:
        result = json.loads(get_module_blast_radius(str(tmp_path), variant))
        assert result["module"] == target
        if variant != "10/1":
            assert normalize_module_path_to_dotted(variant, repo_root=str(tmp_path)) == target


def test_auto_returns_lossless_result_without_decision_envelope(tmp_path, monkeypatch):
    _fixture(monkeypatch)
    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=True, representation="auto"))
    assert result.get("status") != "representation_decision_required"
    assert result["artifact_count_returned"] == 3
    assert result.get("schema") == "module_blast_radius.lossless.v1"


def test_auto_does_not_size_without_identity_collection(tmp_path, monkeypatch):
    _fixture(monkeypatch)
    calls = 0
    original = mcp_rep.representation_size_stats

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(mcp_rep, "representation_size_stats", counted)
    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["module"], representation="auto"))
    assert result == {"module": "pkg.mod"}
    assert calls == 0


def test_explicit_named_guard_remains_functional(tmp_path, monkeypatch):
    state, _ = _fixture(monkeypatch)
    symbols = [f"symbol_{index}" for index in range(48)]
    state.artifacts["pkg.mod"] = {"own_symbols": symbols, "symbols": {"functions": symbols, "signatures": {symbol: "x" * 900 for symbol in symbols}}}
    state.artifact_consumption = {f"pkg.mod::{symbol}": {"consumers": [], "channels": {}} for symbol in symbols}
    confirmation = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=False, representation="named"))
    assert confirmation["status"] == "confirmation_required"


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda state: setattr(state, "artifact_consumption_state", "stale"), "error"),
        (lambda state: setattr(state, "dependency_graph", None), "missing_graph"),
        (lambda state: setattr(state, "cached_analytics_state", "deferred"), "stale_analytics"),
    ],
)
def test_fail_closed_family_availability(tmp_path, monkeypatch, mutate, expected):
    state, _ = _fixture(monkeypatch)
    mutate(state)
    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
    if expected == "error":
        assert result["status"] == "error" and result["available"] is False
    elif expected == "missing_graph":
        assert result["artifacts"]["A100/1"]["downstream_module_reachability"]["available"] is False
    else:
        assert result["artifacts"]["A100/1"]["architecture"]["available"] is False
        assert result["artifacts"]["A100/1"]["downstream_module_reachability"]["layer_classification_available"] is False


def test_indexed_zero_identity_output_has_no_representation_metadata(tmp_path, monkeypatch):
    state, _ = _fixture(monkeypatch)
    state.artifact_consumption = {f"pkg.mod::{symbol}": {"consumers": [], "channels": {}} for symbol in ("alpha", "beta", "gamma")}
    state.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})
    indexed = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="indexed"))
    assert "schema" not in indexed
    assert "representation" not in indexed
    assert "consumer_representation" not in indexed


def test_artifact_contract_semantics_remain_equal(tmp_path, monkeypatch):
    _fixture(monkeypatch)
    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
    for artifact_id, entry in result["artifacts"].items():
        expected = json.loads(get_artifact_blast_radius(str(tmp_path), artifact_name=artifact_id, compact=False, max_items=None))
        assert entry["artifact_id"] == expected["artifact_id"]
        assert entry["full_name"] == expected["artifact"]
        assert entry["direct_consumers"]["total"] == expected["consumers"]["total"]
        assert entry["direct_consumers"]["items"] == expected["consumers"]["items"]
        assert entry["evidence_scope"] == expected["evidence_scope"]
        assert entry["downstream_module_reachability"]["total_downstream_count"] == expected["downstream_module_reachability"]["total_downstream_count"]


def test_aggregate_missing_graph_state_survives_indexed_encoding(tmp_path, monkeypatch):
    state, _ = _fixture(monkeypatch)
    state.dependency_graph = None
    named = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
    indexed = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="indexed"))
    _, decoded = _decode_indexed(indexed, _registry_state())
    expected = named["aggregate"]["unique_downstream_consumers"]
    assert expected["available"] is False
    assert decoded["downstream"] is None
    assert decoded["downstream_state"]["available"] is False
    assert decoded["downstream_state"]["reason"] == expected["reason"]


def test_aggregate_stale_classification_state_survives_indexed_encoding(tmp_path, monkeypatch):
    state, _ = _fixture(monkeypatch)
    state.cached_analytics_state = "deferred"
    named = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="named"))
    indexed = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", representation="indexed"))
    _, decoded = _decode_indexed(indexed, _registry_state())
    expected = named["aggregate"]["unique_downstream_consumers"]
    assert expected["classification_available"] is False
    assert decoded["downstream_state"]["classification_available"] is False
    assert decoded["downstream_state"]["reason"] == expected["reason"]


def test_auto_compact_precedence_and_explicit_representation_precedence(tmp_path, monkeypatch):
    _fixture(monkeypatch)
    auto_compact = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=True, representation="auto"))
    auto_full = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=False, representation="auto", allow_large_output=True))
    named_compact = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=True, representation="named", allow_large_output=True))
    indexed_full = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=False, representation="indexed"))
    assert auto_compact.get("schema") == "module_blast_radius.lossless.v1"
    assert "schema" not in auto_full
    assert "schema" not in named_compact
    assert indexed_full.get("schema") == "module_blast_radius.lossless.v1"


def test_indexed_fields_attach_only_required_support_tables(tmp_path, monkeypatch):
    _fixture(monkeypatch)
    module_only = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["module"], representation="indexed"))
    aggregate_only = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["aggregate"], representation="indexed"))
    artifacts_only = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", fields=["artifacts"], representation="indexed"))
    assert "schema" not in module_only
    assert "module_index" not in module_only
    assert "sets" not in module_only
    for payload in (aggregate_only, artifacts_only):
        assert payload["schema"] == "module_blast_radius.lossless.v1"
        assert payload["module_index"]
        assert payload["sets"][0] == []


def test_auto_named_fallback_uses_named_guard_when_indexed_ids_are_missing(tmp_path, monkeypatch):
    state, registry = _fixture(monkeypatch)
    # Remove all consumer IDs from both canonical maps and live module state.
    for name in ("pkg.consumer", "tests.consumer", "pkg.after", "pkg.leaf", "pkg.dep", "pkg.soft_after"):
        state.modules.pop(name, None)
        registry._state["module_registry"]["path_to_id"].pop(name, None)
        registry._state["module_registry"]["id_to_path"] = {
            value: key for key, value in registry._state["module_registry"]["path_to_id"].items()
        }
    tool_module = importlib.import_module("contextor.mcp.tools.get_module_blast_radius")
    observed = {}

    def capture(serialized, **kwargs):
        observed.update(kwargs)
        return serialized

    monkeypatch.setattr(tool_module, "guard_large_output", capture)
    result = json.loads(get_module_blast_radius(str(tmp_path), "pkg.mod", compact=True, representation="auto"))
    assert "schema" not in result
    assert observed["reason"].startswith("Estimated module blast-radius")

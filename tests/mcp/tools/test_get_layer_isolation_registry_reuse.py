import json
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from contextor.mcp.tools import get_layer_isolation as layer_isolation_module


def _registry_state():
    return {
        "module_registry": {
            "path_to_id": {"pkg.layer": "1/1"},
            "id_to_path": {"1/1": "pkg.layer"},
        },
        "artifact_registry": {
            "path_to_id": {"pkg.layer::thing": "A1/1"},
            "id_to_path": {"A1/1": "pkg.layer::thing"},
        },
    }


class _Registry:
    def __init__(self, state):
        self._state = state
        self.read_transaction_calls = 0

    def read_transaction(self):
        self.read_transaction_calls += 1
        return nullcontext()


def _report(tmp_path):
    report = tmp_path / "repo_layer_graph_analytics.json"
    report.write_text(
        json.dumps(
            {
                "module_count": 1,
                "modules": {"pkg.layer": {"layer": "engine"}},
                "module_dependency_matrix": {"1/1": []},
                "shared_usage_clusters": [
                    {
                        "modules": ["1/1"],
                        "shared_artifact_keys": ["A1/1"],
                    }
                ],
                "dependency_type_breakdown": {"import": 1},
            }
        ),
        encoding="utf-8",
    )
    return report


def _call(tmp_path):
    return layer_isolation_module.get_layer_isolation(
        str(tmp_path), "layer", compact=False, max_clusters=8,
        max_boundary_violations=10,
    )


def test_dedicated_report_reuses_fresh_live_registry_with_exact_payload_parity(
    tmp_path, monkeypatch
):
    report = _report(tmp_path)
    state = _registry_state()
    baseline_maps = (
        state["module_registry"]["path_to_id"],
        state["module_registry"]["id_to_path"],
        state["artifact_registry"]["path_to_id"],
        state["artifact_registry"]["id_to_path"],
    )
    read_registries_calls = 0

    def read_registries(_root):
        nonlocal read_registries_calls
        read_registries_calls += 1
        return baseline_maps

    monkeypatch.setattr(
        layer_isolation_module.report_helpers,
        "get_canonical_report",
        lambda _root, _filename: report,
    )
    monkeypatch.setattr(layer_isolation_module.query_helpers, "read_registries", read_registries)
    monkeypatch.setattr(layer_isolation_module.mcp_runtime, "get_or_init_engine", lambda _root: None)
    baseline = _call(tmp_path)
    read_registries_calls = 0

    registry = _Registry(state)
    engine = SimpleNamespace(
        provenance="live",
        state=SimpleNamespace(),
        registry=registry,
    )
    engine_calls = 0

    def get_engine(_root):
        nonlocal engine_calls
        engine_calls += 1
        return engine

    monkeypatch.setattr(layer_isolation_module.mcp_runtime, "get_or_init_engine", get_engine)
    fresh = _call(tmp_path)

    assert json.loads(fresh) == json.loads(baseline)
    assert fresh == baseline
    assert engine_calls == 1
    assert registry.read_transaction_calls == 1
    assert read_registries_calls == 0


@pytest.mark.parametrize(
    "engine",
    [
        None,
        SimpleNamespace(provenance="snapshot", state=SimpleNamespace(), registry=_Registry(_registry_state())),
        SimpleNamespace(provenance="live", state=SimpleNamespace(resync_required=True), registry=_Registry(_registry_state())),
        SimpleNamespace(provenance="live", state=SimpleNamespace(), registry=None),
        SimpleNamespace(provenance="live", state=SimpleNamespace(), registry=SimpleNamespace(_state=_registry_state())),
    ],
)
def test_dedicated_report_falls_back_when_live_registry_is_not_usable(
    tmp_path, monkeypatch, engine
):
    report = _report(tmp_path)
    maps = _registry_state()
    fallback = (
        maps["module_registry"]["path_to_id"],
        maps["module_registry"]["id_to_path"],
        maps["artifact_registry"]["path_to_id"],
        maps["artifact_registry"]["id_to_path"],
    )
    calls = {"engine": 0, "registries": 0}

    def get_engine(_root):
        calls["engine"] += 1
        return engine

    def read_registries(_root):
        calls["registries"] += 1
        return fallback

    monkeypatch.setattr(layer_isolation_module.report_helpers, "get_canonical_report", lambda _root, _filename: report)
    monkeypatch.setattr(layer_isolation_module.mcp_runtime, "get_or_init_engine", get_engine)
    monkeypatch.setattr(layer_isolation_module.query_helpers, "read_registries", read_registries)

    result = json.loads(_call(tmp_path))

    assert result["module_count"] == 1
    assert calls == {"engine": 1, "registries": 1}


def test_dedicated_report_falls_back_when_live_acquisition_is_unavailable(
    tmp_path, monkeypatch
):
    report = _report(tmp_path)
    maps = _registry_state()
    fallback = ({}, maps["module_registry"]["id_to_path"], {}, maps["artifact_registry"]["id_to_path"])
    calls = {"engine": 0, "registries": 0}

    def get_engine(_root):
        calls["engine"] += 1
        raise OSError("LIVE unavailable")

    def read_registries(_root):
        calls["registries"] += 1
        return fallback

    monkeypatch.setattr(layer_isolation_module.report_helpers, "get_canonical_report", lambda _root, _filename: report)
    monkeypatch.setattr(layer_isolation_module.mcp_runtime, "get_or_init_engine", get_engine)
    monkeypatch.setattr(layer_isolation_module.query_helpers, "read_registries", read_registries)

    result = json.loads(_call(tmp_path))

    assert result["module_count"] == 1
    assert calls["engine"] == 1
    assert calls["registries"] == 1

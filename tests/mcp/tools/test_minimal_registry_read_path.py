import json
from types import SimpleNamespace

from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.domain.module import Module
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.tools.get_file_edit_context import get_file_edit_context


def test_read_transaction_has_no_commit_side_effects(tmp_path, monkeypatch):
    registry = PersistentIdentityRegistry(str(tmp_path))
    calls = {"write": 0, "fsync": 0, "replace": 0}
    monkeypatch.setattr(type(registry.transaction_file), "write_text", lambda original, *a, **k: calls.__setitem__("write", calls["write"] + 1) or original(*a, **k))
    monkeypatch.setattr("os.fsync", lambda _fd: calls.__setitem__("fsync", calls["fsync"] + 1))
    monkeypatch.setattr("os.replace", lambda *a: calls.__setitem__("replace", calls["replace"] + 1))

    with registry.read_transaction():
        assert registry._state["module_registry"]["path_to_id"] == {}

    assert calls == {"write": 0, "fsync": 0, "replace": 0}


def test_fresh_minimal_query_uses_one_read_transaction_and_no_discovery(tmp_path, monkeypatch):
    source = tmp_path / "pkg" / "module.py"
    source.parent.mkdir()
    source.write_text("x = 1\n", encoding="utf-8")
    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry._state["module_registry"]["path_to_id"] = {"pkg.module": "1/1"}
        registry._state["module_registry"]["id_to_path"] = {"1/1": "pkg.module"}

    module = Module(module_id="pkg.module", path="pkg/module.py", absolute_path=str(source), imports=[])
    state = RepositoryAnalysisState(modules={"pkg.module": module})
    state.dependency_graph = SimpleNamespace(hard_edges={}, soft_edges={})
    state.cached_analytics_state = "deferred"
    state.topology_metrics_state = "deferred"
    engine = SimpleNamespace(state=state)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    counts = {"read": 0, "write": 0, "discover": 0}
    original_read = PersistentIdentityRegistry.read_transaction
    original_write = PersistentIdentityRegistry.transaction
    monkeypatch.setattr(PersistentIdentityRegistry, "read_transaction", lambda self: counts.__setitem__("read", counts["read"] + 1) or original_read(self))
    monkeypatch.setattr(PersistentIdentityRegistry, "transaction", lambda self: counts.__setitem__("write", counts["write"] + 1) or original_write(self))
    monkeypatch.setattr("contextor.core.report_query.discover_module_paths", lambda *a: counts.__setitem__("discover", counts["discover"] + 1) or {})

    result = json.loads(get_file_edit_context(str(tmp_path), target="pkg.module", mode="minimal"))

    assert result["resolved_as"] == "module"
    assert result["file"] == "pkg/module.py"
    assert counts == {"read": 1, "write": 0, "discover": 0}

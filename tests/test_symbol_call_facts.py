import ast
from dataclasses import make_dataclass
from pathlib import Path
from unittest.mock import patch

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.incremental.materialization import ensure_module_usages
from contextor.core.analysis.state_manager import (
    FileStateManager,
    RepositoryAnalysisState,
    module_current_truth,
)
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.module import Module
from contextor.core.domain.usage_facts import ModuleUsageFacts, SymbolCallFact
from contextor.core.domain import usage_facts as usage_facts_module
from contextor.core.live_state import store as live_store
from contextor.core.live_state.store import load_snapshot, save_snapshot
from contextor.core.reference.engine import extract_module_usage_facts
from contextor.core.reference.visitor import SymbolReferenceVisitor
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def _edge(caller: str, callee: str, line: int) -> SymbolCallFact:
    return (caller, callee, line, "direct")


def _engine(tmp_path: Path) -> IncrementalAnalysisEngine:
    cache = tmp_path / "cache"
    cache.mkdir(exist_ok=True)
    return IncrementalAnalysisEngine(
        RepositoryAnalysisState(
            dependency_graph=ProjectGraph(hard_edges={}, soft_edges={})
        ),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache)),
        str(tmp_path),
    )


def test_graph_analytics_full_materialization_has_canonical_symbol_edges(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    original = repo / "contextor/core/reporting_engine/graph_analytics.py"
    path = tmp_path / "contextor/core/reporting_engine/graph_analytics.py"
    path.parent.mkdir(parents=True)
    path.write_text(original.read_text(encoding="utf-8"), encoding="utf-8")
    module_name = "contextor.core.reporting_engine.graph_analytics"
    state = RepositoryAnalysisState(
        modules={
            module_name: Module(
                module_id=module_name,
                path="contextor/core/reporting_engine/graph_analytics.py",
                absolute_path=str(path),
                imports=[],
            )
        }
    )
    cache = tmp_path / "cache"
    manager = FileStateManager(str(cache))
    engine = IncrementalAnalysisEngine(
        state, PersistentIdentityRegistry(str(tmp_path)), manager, str(tmp_path)
    )
    calls = set(engine.state.module_usages[module_name].symbol_calls)

    assert _edge(
        f"{module_name}::generate_graph_analytics_report",
        f"{module_name}::_compute_pagerank",
        1648,
    ) in calls
    assert _edge(
        f"{module_name}::_compute_pagerank",
        f"{module_name}::_normalized_edges",
        737,
    ) in calls
    assert _edge(
        f"{module_name}::compute_topology_analytics",
        f"{module_name}::_compute_pagerank",
        1930,
    ) in calls


def test_multiple_local_callers_and_callees_are_qualified():
    facts = extract_module_usage_facts(
        "sample",
        """
def left():
    shared()
    other()
def right():
    shared()
def shared():
    pass
def other():
    pass
""",
    )

    assert set(facts.symbol_calls) == {
        _edge("sample::left", "sample::shared", 3),
        _edge("sample::left", "sample::other", 4),
        _edge("sample::right", "sample::shared", 6),
    }


def test_method_owner_nested_and_module_level_semantics():
    facts = extract_module_usage_facts(
        "sample",
        """
def helper():
    pass
helper()
class Worker:
    def run(self):
        def nested():
            helper()
        self.finish()
    def finish(self):
        pass
""",
    )

    assert set(facts.symbol_calls) == {
        _edge("sample::Worker.run", "sample::Worker.finish", 9),
    }
    assert all(call[2] != 4 for call in facts.symbol_calls)
    assert all("nested" not in call[0] for call in facts.symbol_calls)


def test_nested_sync_and_async_bodies_are_not_outer_calls():
    facts = extract_module_usage_facts(
        "sample",
        """
def helper(): pass
def other(): pass
def outer():
    def nested():
        helper()
    async def nested_async():
        helper()
    other()
""",
    )

    assert facts.symbol_calls == (
        _edge("sample::outer", "sample::other", 9),
    )


def test_definition_time_calls_are_not_owned_by_new_function():
    facts = extract_module_usage_facts(
        "sample",
        """
def helper(): pass
def body_call(): pass
def decorate(value): return value
@decorate(helper())
def regular(x=helper(), *, y=helper()):
    body_call()
""",
    )

    assert facts.symbol_calls == (
        _edge("sample::regular", "sample::body_call", 7),
    )


def test_legacy_reference_context_remains_for_function_and_method():
    visitor = SymbolReferenceVisitor(
        target_symbols={"target"},
        current_module="sample",
        local_symbols={
            "run": "sample.run",
            "Worker.method": "sample.Worker.method",
        },
    )
    visitor.visit(
        ast.parse(
            """
def run():
    target()
class Worker:
    def method(self):
        target()
"""
        )
    )

    assert {(callee, context) for callee, _line, context in visitor.called} == {
        ("target", "run"),
        ("target", "method"),
    }


def test_unresolved_or_ambiguous_call_is_not_confirmed():
    facts = extract_module_usage_facts(
        "sample",
        """
class A:
    def ping(self): pass
class B:
    def ping(self): pass
def run(obj):
    obj.ping()
    missing()
""",
    )
    assert facts.symbol_calls == ()


def test_symbol_call_materialization_requires_successful_authoritative_extraction():
    missing = extract_module_usage_facts("sample", None)
    invalid = extract_module_usage_facts("sample", "def broken(:\n")
    valid_empty = extract_module_usage_facts("sample", "def empty():\n    pass\n")
    valid_edge = extract_module_usage_facts(
        "sample", "def caller():\n    callee()\ndef callee(): pass\n"
    )

    assert missing.symbol_calls_materialized is False
    assert invalid.symbol_calls_materialized is False
    assert valid_empty.symbol_calls == ()
    assert valid_empty.symbol_calls_materialized is True
    assert valid_edge.symbol_calls == (
        _edge("sample::caller", "sample::callee", 2),
    )
    assert valid_edge.symbol_calls_materialized is True


def test_incremental_replace_remove_delete_and_unrelated_preservation(tmp_path):
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text(
        "def a():\n    b()\n    c()\ndef b(): pass\ndef c(): pass\n",
        encoding="utf-8",
    )
    second.write_text("def x():\n    y()\ndef y(): pass\n", encoding="utf-8")
    engine = _engine(tmp_path)

    engine.update_file(str(first))
    engine.update_file(str(second))
    second_before = engine.state.module_usages["second"].symbol_calls
    assert len(engine.state.module_usages["first"].symbol_calls) == 2

    first.write_text(
        "def a():\n    c()\ndef b(): pass\ndef c(): pass\n",
        encoding="utf-8",
    )
    engine.update_file(str(first))
    assert engine.state.module_usages["first"].symbol_calls == (
        _edge("first::a", "first::c", 2),
    )
    assert engine.state.module_usages["second"].symbol_calls == second_before

    first.unlink()
    engine.update_file(str(first))
    assert "first" not in engine.state.module_usages
    assert engine.state.module_usages["second"].symbol_calls == second_before


def test_syntax_stale_is_not_current_and_recovery_matches_full_extraction(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text("def a():\n    b()\ndef b(): pass\n", encoding="utf-8")
    engine = _engine(tmp_path)
    engine.update_file(str(source))

    source.write_text("def a(:\n    b()\n", encoding="utf-8")
    result = engine.update_file(str(source))
    assert result.status == "SYNTAX_ERROR"
    assert module_current_truth(engine.state, "sample")["available"] is False

    recovered = "def a():\n    b()\n    c()\ndef b(): pass\ndef c(): pass\n"
    source.write_text(recovered, encoding="utf-8")
    engine.update_file(str(source))
    assert module_current_truth(engine.state, "sample")["available"] is True
    incremental_calls = engine.state.module_usages["sample"].symbol_calls
    assert incremental_calls == extract_module_usage_facts("sample", recovered).symbol_calls

    full_cache = tmp_path / "full_cache"
    full_engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(
            modules={
                "sample": Module(
                    module_id="sample",
                    path="sample.py",
                    absolute_path=str(source),
                    imports=[],
                )
            }
        ),
        PersistentIdentityRegistry(str(tmp_path / "full_registry")),
        FileStateManager(str(full_cache)),
        str(tmp_path),
    )
    assert full_engine.state.module_usages["sample"].symbol_calls == incremental_calls


def test_snapshot_roundtrip_and_artifact_consumption_contract(tmp_path):
    facts = extract_module_usage_facts(
        "sample", "def caller():\n    callee()\ndef callee(): pass\n"
    )
    state = RepositoryAnalysisState(module_usages={"sample": facts})
    save_snapshot(state, tmp_path / "snapshot", "calls")
    loaded, _ = load_snapshot(tmp_path / "snapshot", "calls")
    assert loaded.module_usages["sample"].symbol_calls == facts.symbol_calls

    source = tmp_path / "sample.py"
    source.write_text("def caller():\n    callee()\ndef callee(): pass\n", encoding="utf-8")
    engine = _engine(tmp_path)
    engine.update_file(str(source))
    assert engine.state.artifact_consumption["sample::callee"]["consumers"] == []


def test_legacy_pickled_usage_facts_get_empty_symbol_call_default():
    facts = ModuleUsageFacts()
    object.__delattr__(facts, "symbol_calls")

    assert facts.symbol_calls == ()
    assert facts.to_dict()["symbol_calls"] == []


def test_legacy_symbol_call_class_snapshot_migrates_to_primitive_tuples(
    tmp_path, monkeypatch
):
    legacy_type = make_dataclass(
        "SymbolCallFact",
        [("caller", str), ("callee", str), ("line", int), ("call_kind", str)],
        frozen=True,
    )
    legacy_type.__module__ = "contextor.core.domain.usage_facts"
    monkeypatch.setattr(usage_facts_module, "SymbolCallFact", legacy_type)
    legacy_fact = legacy_type("sample::caller", "sample::callee", 7, "direct")
    state = RepositoryAnalysisState(
        module_usages={
            "sample": ModuleUsageFacts(symbol_calls=(legacy_fact,))
        }
    )
    cache = tmp_path / "legacy"
    save_snapshot(state, cache, "legacy-calls")
    monkeypatch.setattr(
        usage_facts_module,
        "SymbolCallFact",
        SymbolCallFact,
    )

    loaded, _ = load_snapshot(cache, "legacy-calls")
    migrated = loaded.module_usages["sample"].symbol_calls

    assert migrated == (("sample::caller", "sample::callee", 7, "direct"),)
    assert all(type(item) is tuple for item in migrated)
    assert not any(
        isinstance(item, live_store._LegacySymbolCallFact)
        for item in migrated
    )

    current_cache = tmp_path / "current"
    save_snapshot(loaded, current_cache, "current-calls")
    reloaded, _ = load_snapshot(current_cache, "current-calls")
    assert reloaded.module_usages["sample"].symbol_calls == migrated
    assert all(
        type(item) is tuple
        for item in reloaded.module_usages["sample"].symbol_calls
    )


def test_unrelated_invalid_pickle_is_not_migrated(tmp_path):
    cache = tmp_path / "corrupt"
    save_snapshot(RepositoryAnalysisState(), cache, "corrupt")
    (cache / "engine_state.pkl").write_bytes(b"not a pickle")

    assert load_snapshot(cache, "corrupt") is None


def _legacy_usage_facts(**kwargs) -> ModuleUsageFacts:
    facts = ModuleUsageFacts(**kwargs)
    object.__delattr__(facts, "symbol_calls_materialized")
    assert facts.symbol_calls_materialized is False
    return facts


def test_legacy_existing_usage_is_backfilled_once_and_unrelated_is_preserved(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text(
        "def caller():\n    callee()\ndef callee():\n    pass\n",
        encoding="utf-8",
    )
    unrelated = ModuleUsageFacts(imports=("os",), symbol_calls=())
    state = RepositoryAnalysisState(
        modules={
            "sample": Module("sample", "sample.py", str(source), []),
        },
        module_usages={
            "sample": _legacy_usage_facts(imports=("legacy",)),
            "unrelated": unrelated,
        },
    )

    with patch(
        "contextor.core.reference.engine.extract_module_usage_facts",
        wraps=extract_module_usage_facts,
    ) as extract:
        ensure_module_usages(state)
        ensure_module_usages(state)

    assert extract.call_count == 1
    assert state.module_usages["sample"].symbol_calls == (
        _edge("sample::caller", "sample::callee", 2),
    )
    assert state.module_usages["sample"].symbol_calls_materialized is True
    assert state.module_usages["unrelated"] is unrelated


def test_materialized_empty_symbol_calls_survive_snapshot_without_rebuild(tmp_path):
    source = tmp_path / "empty.py"
    source.write_text("def empty():\n    pass\n", encoding="utf-8")
    state = RepositoryAnalysisState(
        modules={"empty": Module("empty", "empty.py", str(source), [])},
        module_usages={
            "empty": extract_module_usage_facts("empty", "def empty():\n    pass\n")
        },
    )
    cache = tmp_path / "snapshot-materialized"
    save_snapshot(state, cache, "materialized-empty")
    loaded, _ = load_snapshot(cache, "materialized-empty")

    with patch(
        "contextor.core.reference.engine.extract_module_usage_facts",
        wraps=extract_module_usage_facts,
    ) as extract:
        ensure_module_usages(loaded)

    assert extract.call_count == 0
    assert loaded.module_usages["empty"].symbol_calls == ()
    assert loaded.module_usages["empty"].symbol_calls_materialized is True


def test_incremental_create_and_update_mark_symbol_calls_materialized(tmp_path):
    source = tmp_path / "incremental.py"
    source.write_text("def caller():\n    callee()\ndef callee(): pass\n", encoding="utf-8")
    engine = _engine(tmp_path)
    engine.update_file(str(source))
    assert engine.state.module_usages["incremental"].symbol_calls_materialized is True

    source.write_text("def caller():\n    pass\n", encoding="utf-8")
    engine.update_file(str(source))
    facts = engine.state.module_usages["incremental"]
    assert facts.symbol_calls == ()
    assert facts.symbol_calls_materialized is True


def test_graph_analytics_legacy_usage_backfills_required_edges(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    original = repo / "contextor/core/reporting_engine/graph_analytics.py"
    path = tmp_path / "contextor/core/reporting_engine/graph_analytics.py"
    path.parent.mkdir(parents=True)
    path.write_text(original.read_text(encoding="utf-8"), encoding="utf-8")
    module_name = "contextor.core.reporting_engine.graph_analytics"
    unrelated = ModuleUsageFacts(imports=("os",))
    state = RepositoryAnalysisState(
        modules={
            module_name: Module(
                module_name,
                "contextor/core/reporting_engine/graph_analytics.py",
                str(path),
                [],
            )
        },
        module_usages={
            module_name: _legacy_usage_facts(),
            "unrelated": unrelated,
        },
    )

    ensure_module_usages(state)
    calls = set(state.module_usages[module_name].symbol_calls)

    assert _edge(f"{module_name}::generate_graph_analytics_report", f"{module_name}::_compute_pagerank", 1648) in calls
    assert _edge(f"{module_name}::_compute_pagerank", f"{module_name}::_normalized_edges", 737) in calls
    assert _edge(f"{module_name}::compute_topology_analytics", f"{module_name}::_compute_pagerank", 1930) in calls
    assert state.module_usages["unrelated"] is unrelated

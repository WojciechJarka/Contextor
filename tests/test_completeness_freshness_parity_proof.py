"""
tests/test_completeness_freshness_parity_proof.py

Stage 3C.2a — Execution Completeness, Freshness & Full-State Parity Proof Tests.
"""

from copy import deepcopy
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine, IncrementalUpdateResult
from contextor.core.analysis.incremental.preparation import prepare_source_update
from contextor.core.analysis.refresh_planner import RefreshPlanner, _find_dependent_consumers
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState, FileDelta
from contextor.core.analysis.incremental.plan_executor import _resolve_canonical_target_key
from contextor.core.api.facade import ContextorFacade
from contextor.core.domain.module import Module
from contextor.core.domain.refresh_plan import RefreshPlan
from contextor.core.domain.usage_facts import ModuleUsageFacts, UsageDelta
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.reference.engine import extract_module_usage_facts
from contextor.core.reporting_engine.graph_analytics import (
    _CALL_USAGE_CHANNELS,
    _IMPORT_USAGE_CHANNELS,
    _INHERITANCE_USAGE_CHANNELS,
    _usage_dependency_types,
)
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def _build_full_static_state(repo_dir: Path) -> RepositoryAnalysisState:
    """Canonical Oracle: builds fresh full static RepositoryAnalysisState via real production ContextorFacade."""
    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(repo_dir))
    assert not errors, errors

    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None

    return hydrated.engine.state


def _assert_full_parity(incremental_state: RepositoryAnalysisState, oracle_state: RepositoryAnalysisState):
    """Asserts full canonical parity across all plan-controlled families with exact channel sets."""
    # 1. Modules
    assert set(incremental_state.modules.keys()) == set(oracle_state.modules.keys())

    # 2. Definitions / Artifacts
    assert set(incremental_state.artifacts.keys()) == set(oracle_state.artifacts.keys())
    for mod_key, inc_art in incremental_state.artifacts.items():
        ora_art = oracle_state.artifacts[mod_key]
        assert inc_art.get("symbols") == ora_art.get("symbols")
        assert inc_art.get("own_symbols") == ora_art.get("own_symbols")

    # 3. ModuleUsageFacts
    assert set(incremental_state.module_usages.keys()) == set(oracle_state.module_usages.keys())
    for mod_name, inc_facts in incremental_state.module_usages.items():
        ora_facts = oracle_state.module_usages[mod_name]
        assert inc_facts.direct_calls == ora_facts.direct_calls
        assert inc_facts.qualified_refs == ora_facts.qualified_refs
        assert inc_facts.imports == ora_facts.imports
        assert inc_facts.aliases == ora_facts.aliases

    # 4. Artifact Consumption (exact target set, exact consumers, and exact channel sets)
    assert set(incremental_state.artifact_consumption.keys()) == set(oracle_state.artifact_consumption.keys())
    for target, ora_entry in oracle_state.artifact_consumption.items():
        inc_entry = incremental_state.artifact_consumption.get(target, {})
        assert sorted(inc_entry.get("consumers", [])) == sorted(ora_entry.get("consumers", []))
        inc_channels = inc_entry.get("channels", {})
        ora_channels = ora_entry.get("channels", {})
        assert set(inc_channels.keys()) == set(ora_channels.keys()), (
            f"Target '{target}' channel consumers mismatch: inc={inc_channels} vs ora={ora_channels}"
        )
        for consumer in ora_channels.keys():
            assert set(inc_channels[consumer]) == set(ora_channels[consumer]), (
                f"Target '{target}', Consumer '{consumer}' channel mismatch: "
                f"incremental={inc_channels.get(consumer)} vs full={ora_channels.get(consumer)}"
            )

    # 5. Dependency Graph
    if oracle_state.dependency_graph is not None:
        assert incremental_state.dependency_graph is not None
        assert incremental_state.dependency_graph.hard_edges == oracle_state.dependency_graph.hard_edges
        assert incremental_state.dependency_graph.soft_edges == oracle_state.dependency_graph.soft_edges

    # 6. Macro Graph Metrics
    if oracle_state.metrics is not None:
        assert incremental_state.metrics is not None
        assert incremental_state.metrics == oracle_state.metrics



def test_canonical_matrix_mapping_exact_and_negative_cases():
    """
    Proves _usage_dependency_types uses exact canonical channel identity,
    NOT substring heuristics.

    POSITIVE: All 7 canonical channels produce the correct dependency type.
    NEGATIVE: Non-canonical names that CONTAIN canonical substrings must NOT
              produce any dependency type (regression against fuzzy matching).
    """
    # POSITIVE CASES — exact canonical channel identity
    assert _usage_dependency_types({"direct_calls": ["x"]}) == {"call"}
    assert _usage_dependency_types({"runtime_calls": ["x"]}) == {"call"}
    assert _usage_dependency_types({"callback_calls": ["x"]}) == {"call"}
    assert _usage_dependency_types({"event_bindings": ["x"]}) == {"call"}
    assert _usage_dependency_types({"api_imports": ["x"]}) == {"import"}
    assert _usage_dependency_types({"qualified_refs": ["x"]}) == {"import"}
    assert _usage_dependency_types({"inheritance": ["x"]}) == {"inheritance"}

    # NEGATIVE CASES — non-canonical names with substrings of canonical names
    # Must produce empty set (no fuzzy matching allowed).
    negative_cases = [
        "event_metadata",       # contains "event"
        "qualified_name",       # contains "qualified"
        "runtime_note",         # contains "runtime"
        "callback_hint",        # contains "callback"
        "import_candidate",     # contains "import"
        "call_log",             # contains "call"
        "inheritance_map",      # contains "inherit"
        "api_import_meta",      # contains "api_import"
    ]
    for name in negative_cases:
        result = _usage_dependency_types({name: ["x"]})
        assert result == set(), (
            f"Non-canonical channel {name!r} must NOT produce a dependency type, "
            f"got {result!r}"
        )

    # FROZENSET CONSTANTS integrity check
    assert "direct_calls" in _CALL_USAGE_CHANNELS
    assert "runtime_calls" in _CALL_USAGE_CHANNELS
    assert "callback_calls" in _CALL_USAGE_CHANNELS
    assert "event_bindings" in _CALL_USAGE_CHANNELS
    assert "api_imports" in _IMPORT_USAGE_CHANNELS
    assert "qualified_refs" in _IMPORT_USAGE_CHANNELS
    assert "inheritance" in _INHERITANCE_USAGE_CHANNELS

    # EMPTY VALUES: channel with empty list/set must NOT produce dependency type
    assert _usage_dependency_types({"direct_calls": []}) == set()
    assert _usage_dependency_types({"direct_calls": None}) == set()

    # UNKNOWN CHANNEL: must produce empty set
    assert _usage_dependency_types({"totally_unknown": ["x"]}) == set()


def test_channel_parity_rejects_runtime_vs_direct_calls():
    """Regression test: proves parity assertion rejects runtime_calls vs direct_calls."""
    inc_state = RepositoryAnalysisState(
        modules={"a": Module("a", "a.py", "a.py", imports=[])},
        artifacts={"a": {"symbols": {"functions": ["foo"]}, "own_symbols": ["foo"]}},
        artifact_consumption={"a::foo": {"consumers": ["b"], "channels": {"b": ["runtime_calls"]}}},
    )
    ora_state = RepositoryAnalysisState(
        modules={"a": Module("a", "a.py", "a.py", imports=[])},
        artifacts={"a": {"symbols": {"functions": ["foo"]}, "own_symbols": ["foo"]}},
        artifact_consumption={"a::foo": {"consumers": ["b"], "channels": {"b": ["direct_calls"]}}},
    )
    with pytest.raises(AssertionError, match="channel mismatch"):
        _assert_full_parity(inc_state, ora_state)


def test_channel_parity_rejects_extra_channel():
    """Regression test: proves parity assertion rejects subset/superset channel mismatches."""
    inc_state = RepositoryAnalysisState(
        modules={"a": Module("a", "a.py", "a.py", imports=[])},
        artifacts={"a": {"symbols": {"functions": ["foo"]}, "own_symbols": ["foo"]}},
        artifact_consumption={"a::foo": {"consumers": ["b"], "channels": {"b": ["direct_calls", "api_imports"]}}},
    )
    ora_state = RepositoryAnalysisState(
        modules={"a": Module("a", "a.py", "a.py", imports=[])},
        artifacts={"a": {"symbols": {"functions": ["foo"]}, "own_symbols": ["foo"]}},
        artifact_consumption={"a::foo": {"consumers": ["b"], "channels": {"b": ["direct_calls"]}}},
    )
    with pytest.raises(AssertionError, match="channel mismatch"):
        _assert_full_parity(inc_state, ora_state)


def test_qualified_refs_contract_b_non_call_attribute_only(tmp_path):
    """
    Proves Contract B:
    - Fixture 1: target.foo() produces direct_calls, NOT qualified_refs (in facts, state, and oracle).
    - Fixture 2: ref = target.bar produces qualified_refs, NOT direct_calls (in facts, state, and oracle).
    """
    # Fixture 1: Invocation of target.foo() -> direct_calls only
    repo1 = tmp_path / "repo1"
    repo1.mkdir()
    f_target1 = repo1 / "target.py"
    f_target1.write_text("def foo(): pass\n", encoding="utf-8")

    f_consumer1 = repo1 / "consumer1.py"
    f_consumer1.write_text("import target\ntarget.foo()\n", encoding="utf-8")

    cache_dir1 = repo1 / "cache1"
    cache_dir1.mkdir()
    engine1 = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(repo1)),
        FileStateManager(str(cache_dir1)),
        str(repo1),
    )
    engine1.update_file(str(f_target1))
    res1 = engine1.update_file(str(f_consumer1))

    assert res1.artifact_consumption_state == "fresh"
    foo_channels = engine1.state.artifact_consumption["target::foo"]["channels"]["consumer1"]
    assert foo_channels == ["direct_calls"]
    assert "qualified_refs" not in foo_channels

    # Full analysis parity for Fixture 1
    oracle1 = _build_full_static_state(repo1)
    _assert_full_parity(engine1.state, oracle1)

    # Fixture 2: Non-call attribute access ref = target.bar -> qualified_refs only
    repo2 = tmp_path / "repo2"
    repo2.mkdir()
    f_target2 = repo2 / "target2.py"
    f_target2.write_text("def bar(): pass\n", encoding="utf-8")

    f_consumer2 = repo2 / "consumer2.py"
    f_consumer2.write_text("import target2\nref = target2.bar\n", encoding="utf-8")

    cache_dir2 = repo2 / "cache2"
    cache_dir2.mkdir()
    engine2 = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(repo2)),
        FileStateManager(str(cache_dir2)),
        str(repo2),
    )
    engine2.update_file(str(f_target2))
    res2 = engine2.update_file(str(f_consumer2))

    assert res2.artifact_consumption_state == "fresh"
    bar_channels = engine2.state.artifact_consumption["target2::bar"]["channels"]["consumer2"]
    assert bar_channels == ["qualified_refs"]
    assert "direct_calls" not in bar_channels

    # ModuleUsageFacts semantic distinction
    facts2 = engine2.state.module_usages["consumer2"]
    assert "target2.bar" in facts2.qualified_refs
    assert "target2.bar" not in facts2.direct_calls

    # Full analysis parity for Fixture 2
    oracle2 = _build_full_static_state(repo2)
    _assert_full_parity(engine2.state, oracle2)


def test_full_vs_incremental_qualified_refs_contract_b_exact_parity(tmp_path):
    """
    Proves exact parity between Full Analysis and Incremental for Contract B:
    - target::foo consumed via direct_calls
    - target::bar consumed via qualified_refs
    """
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo():\n    return 1\n\ndef bar():\n    return 2\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("import target\n\ntarget.foo()\nref = target.bar\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    res = engine.update_file(str(f_consumer))

    assert res.artifact_consumption_state == "fresh"
    assert engine.state.artifact_consumption["target::foo"]["channels"]["consumer"] == ["direct_calls"]
    assert engine.state.artifact_consumption["target::bar"]["channels"]["consumer"] == ["qualified_refs"]

    oracle = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle)


def test_runtime_calls_producer_and_canonical_parity(tmp_path):
    """
    Proves ModuleUsageFacts.runtime_calls extraction from reflection syntax
    and verifies that unresolved dynamic reflection does not invent arbitrary targets
    and produces 100% exact parity between Incremental and Full analysis.
    """
    source = "import math\ngetattr(math, 'sin')(1.0)\n"
    facts = extract_module_usage_facts("consumer", source)
    assert "sin" in facts.runtime_calls

    # Full and Incremental analysis parity with dynamic reflection
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("import target\ngetattr(target, 'foo')(1.0)\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    res = engine.update_file(str(f_consumer))

    assert res.artifact_consumption_state == "fresh"
    oracle = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle)


def test_natural_dotted_identity_ambiguity_helper():
    """
    Proves _resolve_canonical_target_key returns (None, 'ambiguous')
    when two canonical targets share the same dotted representation (e.g. pkg.a::B.foo and pkg.a.B::foo).
    Does NOT use monkeypatch.
    """
    candidate_artifacts = {
        "pkg.a": {"symbols": {"classes": ["B"], "functions": [], "methods": ["B.foo"], "globals": []}, "own_symbols": ["B", "B.foo"]},
        "pkg.a.B": {"symbols": {"classes": [], "functions": ["foo"], "methods": [], "globals": []}, "own_symbols": ["foo"]},
    }
    candidate_consumption = {
        "pkg.a::B.foo": {"consumers": [], "channels": {}},
        "pkg.a.B::foo": {"consumers": [], "channels": {}},
    }
    target, status = _resolve_canonical_target_key("pkg.a.B.foo", candidate_consumption, candidate_artifacts)
    assert target is None
    assert status == "ambiguous"


def test_natural_dotted_identity_ambiguity_transition_lifecycle(tmp_path):
    """
    Proves real natural dotted identity ambiguity during late provider update:
    STEP 1: pkg/a.py with class B: def foo(self): return 1 -> canonical pkg.a::B.foo
    STEP 2: consumer.py with import pkg.a; pkg.a.B.foo() -> uniquely bound to pkg.a::B.foo, fresh
    STEP 3 (LATE PROVIDER): pkg/a/B.py with def foo(): return 2 -> canonical pkg.a.B::foo
    Call ONLY update_file(pkg/a/B.py). NO consumer update.
    Verifies:
    - artifact_consumption_state == 'stale'
    - ambiguity detected in RAM backfill/recompute path
    - fail-closed sanitization: consumer slice removed from candidate, no arbitrary binding
    - consumer.py NOT reread from disk
    - COW: previous state was not mutated in place
    - unrelated entries preserved bit-for-bit
    """
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    sub_pkg = pkg_dir / "a"
    sub_pkg.mkdir()

    f_unrelated = tmp_path / "unrelated.py"
    f_unrelated.write_text("def ping(): return 'pong'\n", encoding="utf-8")

    f_unrelated_consumer = tmp_path / "unrelated_consumer.py"
    f_unrelated_consumer.write_text("import unrelated\nunrelated.ping()\n", encoding="utf-8")

    f_a = pkg_dir / "a.py"
    f_a.write_text("class B:\n    def foo(self):\n        return 1\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("import pkg.a\npkg.a.B.foo()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    # STEP 1 & 2: Setup initial unambiguous state with unrelated module
    engine.update_file(str(f_unrelated))
    engine.update_file(str(f_unrelated_consumer))
    engine.update_file(str(f_a))
    res1 = engine.update_file(str(f_consumer))

    assert res1.artifact_consumption_state == "fresh"
    assert "consumer" in engine.state.artifact_consumption.get("pkg.a::B.foo", {}).get("consumers", [])
    assert "unrelated_consumer" in engine.state.artifact_consumption.get("unrelated::ping", {}).get("consumers", [])

    old_consumption_ref = engine.state.artifact_consumption
    old_snapshot = deepcopy(old_consumption_ref)

    # STEP 3: LATE PROVIDER
    f_b = sub_pkg / "B.py"
    f_b.write_text("def foo():\n    return 2\n", encoding="utf-8")

    analyzed_modules = []
    original_extract = extract_module_usage_facts
    original_prepare = prepare_source_update
    consumer_path_resolved = f_consumer.resolve()

    def spy_extract(module_path, *args, **kwargs):
        analyzed_modules.append(module_path)
        return original_extract(module_path, *args, **kwargs)

    def guarded_prepare_source_update(file_path, module_path, *args, **kwargs):
        # Guard: consumer.py must NOT be reread from disk during late-provider update.
        # prepare_source_update is the authoritative production source-read boundary
        # (it calls path.read_text(encoding='utf-8') before any AST extraction).
        resolved = Path(file_path).resolve()
        if resolved == consumer_path_resolved:
            raise AssertionError(
                f"consumer.py was reread from disk via prepare_source_update "
                f"during late-provider RAM recompute (path={file_path})"
            )
        return original_prepare(
            file_path=file_path,
            module_path=module_path,
            *args,
            **kwargs,
        )

    with patch(
        "contextor.core.reference.engine.extract_module_usage_facts",
        side_effect=spy_extract,
    ), patch(
        "contextor.core.analysis.incremental.engine.prepare_source_update",
        side_effect=guarded_prepare_source_update,
    ):
        res2 = engine.update_file(str(f_b))

    # DISK NO-REREAD PROOF:
    # (a) extract_module_usage_facts spy: consumer was NOT re-extracted from source.
    assert "pkg.a.B" in analyzed_modules, "provider pkg.a.B must be analyzed"
    assert "consumer" not in analyzed_modules, "consumer must NOT be re-extracted from disk"
    # (b) prepare_source_update guard: consumer.py was not reopened by production boundary.
    # If consumer.py had been read, guarded_prepare_source_update would have raised AssertionError.

    # Assert fail-closed state
    assert res2.artifact_consumption_state == "stale"
    assert engine.state.artifact_consumption_state == "stale"

    # Assert fail-closed sanitization: ambiguous consumer is NOT bound to either target
    for target_key in ("pkg.a::B.foo", "pkg.a.B::foo"):
        entry = engine.state.artifact_consumption.get(target_key, {})
        assert "consumer" not in entry.get("consumers", [])
        assert "consumer" not in entry.get("channels", {})

    # Assert unrelated consumer entry is preserved bit-for-bit
    assert engine.state.artifact_consumption["unrelated::ping"]["consumers"] == ["unrelated_consumer"]
    assert engine.state.artifact_consumption["unrelated::ping"]["channels"] == {"unrelated_consumer": ["direct_calls"]}

    # Assert COW atomicity: old snapshot was NOT mutated in place
    assert old_consumption_ref == old_snapshot
    assert "consumer" in old_consumption_ref["pkg.a::B.foo"]["consumers"]


def test_natural_dotted_identity_ambiguity_consumer_last(tmp_path):
    """
    Proves natural dotted identity ambiguity during consumer ADD (when both providers already exist).
    Incremental engine fails closed to 'stale' without arbitrary binding.
    """
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    sub_pkg = pkg_dir / "a"
    sub_pkg.mkdir()

    f_a = pkg_dir / "a.py"
    f_a.write_text("class B:\n    def foo(self):\n        return 1\n", encoding="utf-8")

    f_b = sub_pkg / "B.py"
    f_b.write_text("def foo():\n    return 2\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("import pkg.a.B\npkg.a.B.foo()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_a))
    engine.update_file(str(f_b))
    res = engine.update_file(str(f_consumer))

    # Assert fail-closed state
    assert res.artifact_consumption_state == "stale"
    assert engine.state.artifact_consumption_state == "stale"

    # Assert no arbitrary consumer binding occurred
    for target_key in ("pkg.a::B.foo", "pkg.a.B::foo"):
        entry = engine.state.artifact_consumption.get(target_key, {})
        assert "consumer" not in entry.get("consumers", [])


def test_nested_callee_contract_b_regression(tmp_path):
    """
    Proves nested qualified call (e.g. pkg.target.foo()) produces direct_calls
    and does NOT produce accidental qualified_refs for callee subtree.
    """
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()

    f_target = pkg_dir / "target.py"
    f_target.write_text("def foo():\n    return 42\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("import pkg.target\npkg.target.foo()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    res = engine.update_file(str(f_consumer))

    assert res.artifact_consumption_state == "fresh"
    cons = engine.state.artifact_consumption
    assert cons["pkg.target::foo"]["consumers"] == ["consumer"]
    assert cons["pkg.target::foo"]["channels"]["consumer"] == ["direct_calls"]

    # Full analysis parity
    oracle = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle)


def test_event_callback_disjoint_contract_e1_callback_keyword(tmp_path):
    """
    Proves Contract E1 POSITIVE: register(callback=callback_fn)
    -> callback_calls, NOT event_bindings.
    100% exact parity between Incremental and Full Analysis.
    """
    f_target = tmp_path / "target.py"
    f_target.write_text(
        "def callback_fn():\n    return 1\n",
        encoding="utf-8",
    )
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text(
        "from target import callback_fn\n\n"
        "def register(callback=None):\n    pass\n\n"
        "register(callback=callback_fn)\n",
        encoding="utf-8",
    )
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    res = engine.update_file(str(f_consumer))

    assert res.artifact_consumption_state == "fresh"
    channels = engine.state.artifact_consumption["target::callback_fn"]["channels"]["consumer"]
    assert "callback_calls" in channels, "keyword callback must produce callback_calls"
    assert "event_bindings" not in channels, "keyword callback must NOT produce event_bindings"

    oracle = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle)


@pytest.mark.parametrize(
    "event_expression",
    [
        "e.subscribe('topic', event_fn)",
        "e.on(event_fn)",
        "e.bind('<Click>', event_fn)",
    ],
)
def test_event_callback_disjoint_contract_e1_all_event_forms(
    tmp_path,
    event_expression,
):
    """
    Proves Contract E1 for all event-binding forms:
    - e.subscribe('topic', event_fn) -> event_bindings, NOT callback_calls
    - e.on(event_fn)                 -> event_bindings, NOT callback_calls
    - e.bind('<Click>', event_fn)    -> event_bindings, NOT callback_calls
    Full == Incremental exact parity.
    """
    f_target = tmp_path / "target.py"
    f_target.write_text(
        "def event_fn():\n    return 2\n",
        encoding="utf-8",
    )
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text(
        "from target import event_fn\n\n"
        "class Emitter:\n"
        "    def subscribe(self, event, fn):\n        pass\n"
        "    def on(self, fn):\n        pass\n"
        "    def bind(self, event, fn):\n        pass\n\n"
        "e = Emitter()\n"
        f"{event_expression}\n",
        encoding="utf-8",
    )
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    res = engine.update_file(str(f_consumer))

    assert res.artifact_consumption_state == "fresh"
    channels = engine.state.artifact_consumption["target::event_fn"]["channels"]["consumer"]
    assert "event_bindings" in channels, (
        f"{event_expression!r} must produce event_bindings"
    )
    assert "callback_calls" not in channels, (
        f"{event_expression!r} must NOT produce callback_calls"
    )

    oracle = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle)


def test_provider_late_module_add_without_reread(tmp_path):
    """
    Proves late module addition triggers RAM-based backfill for existing consumer
    without rereading or reparsing the consumer file from disk.
    """
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from provider import foo\ndef use():\n    return foo()\n", encoding="utf-8")

    f_provider = tmp_path / "provider.py"
    f_provider.write_text("def foo():\n    return 42\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    # Update consumer first
    engine.update_file(str(f_consumer))

    # Real spy on extract_module_usage_facts
    analyzed_modules = []
    original_extract = extract_module_usage_facts

    def spy_extract(module_path, *args, **kwargs):
        analyzed_modules.append(module_path)
        return original_extract(module_path, *args, **kwargs)

    with patch("contextor.core.reference.engine.extract_module_usage_facts", side_effect=spy_extract):
        res = engine.update_file(str(f_provider))

    # Assert ONLY provider was parsed/extracted, consumer was NOT reread from disk
    assert "provider" in analyzed_modules
    assert "consumer" not in analyzed_modules

    assert res.artifact_consumption_state == "fresh"
    assert "consumer" in engine.state.artifact_consumption.get("provider::foo", {}).get("consumers", [])
    assert set(engine.state.artifact_consumption["provider::foo"]["channels"]["consumer"]) == {"api_imports", "direct_calls"}

    # Full analysis parity
    oracle = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle)


def test_find_dependent_consumers_selector_precision():
    """
    Proves _find_dependent_consumers selects only exact dependent consumers
    across all 8 canonical usage families and avoids false/over-broad recomputations.
    """
    families = [
        ("direct_calls", ModuleUsageFacts(direct_calls=("pkg.impl_a.foo",)), ModuleUsageFacts(direct_calls=("pkg.impl_b.foo",))),
        ("runtime_calls", ModuleUsageFacts(runtime_calls=("pkg.impl_a.foo",)), ModuleUsageFacts(runtime_calls=("pkg.impl_b.foo",))),
        ("qualified_refs", ModuleUsageFacts(qualified_refs=("pkg.impl_a.foo",)), ModuleUsageFacts(qualified_refs=("pkg.impl_b.foo",))),
        ("callback_calls", ModuleUsageFacts(callback_calls=("pkg.impl_a.foo",)), ModuleUsageFacts(callback_calls=("pkg.impl_b.foo",))),
        ("event_bindings", ModuleUsageFacts(event_bindings=("pkg.impl_a.foo",)), ModuleUsageFacts(event_bindings=("pkg.impl_b.foo",))),
        ("imports", ModuleUsageFacts(imports=("pkg.impl_a",)), ModuleUsageFacts(imports=("pkg.impl_b",))),
        ("inheritance_refs", ModuleUsageFacts(inheritance_refs=(("Base", "pkg.impl_a.Base"),)), ModuleUsageFacts(inheritance_refs=(("Base", "pkg.impl_b.Base"),))),
        ("aliases", ModuleUsageFacts(aliases=(("local_a", "pkg.impl_a.foo"),)), ModuleUsageFacts(aliases=(("local_b", "pkg.impl_b.foo"),))),
    ]

    for family_name, fact_a, fact_b in families:
        usages = {
            "consumer_a": fact_a,
            "consumer_b": fact_b,
            "consumer_c": ModuleUsageFacts(direct_calls=("unrelated.other",)),
        }
        selected = _find_dependent_consumers("pkg.impl_a", usages)
        assert selected == {"consumer_a"}, f"Failed exact selection for family {family_name}"


def test_reexport_retargeting_proof(tmp_path):
    """
    Proves re-export retargeting changes underlying canonical provider target:
    BEFORE: consumer bound to pkg.impl_a::foo_a
    AFTER: consumer NOT bound to pkg.impl_a::foo_a, and bound to pkg.impl_b::foo_b
    """
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()

    f_impl_a = pkg_dir / "impl_a.py"
    f_impl_a.write_text("def foo_a():\n    return 'a'\n", encoding="utf-8")

    f_impl_b = pkg_dir / "impl_b.py"
    f_impl_b.write_text("def foo_b():\n    return 'b'\n", encoding="utf-8")

    f_reexport = pkg_dir / "reexport.py"
    f_reexport.write_text("from pkg.impl_a import foo_a as foo\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from pkg.reexport import foo\nfoo()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_impl_a))
    engine.update_file(str(f_impl_b))
    engine.update_file(str(f_reexport))
    engine.update_file(str(f_consumer))

    # BEFORE: consumer bound to pkg.impl_a::foo_a
    assert "consumer" in engine.state.artifact_consumption.get("pkg.impl_a::foo_a", {}).get("consumers", [])
    assert "consumer" not in engine.state.artifact_consumption.get("pkg.impl_b::foo_b", {}).get("consumers", [])

    # Retarget re-export to pkg.impl_b
    f_reexport.write_text("from pkg.impl_b import foo_b as foo\n", encoding="utf-8")
    res = engine.update_file(str(f_reexport))

    assert res.artifact_consumption_state == "fresh"
    # AFTER: consumer NOT bound to pkg.impl_a::foo_a, and IS bound to pkg.impl_b::foo_b
    assert "consumer" not in engine.state.artifact_consumption.get("pkg.impl_a::foo_a", {}).get("consumers", [])
    assert "consumer" in engine.state.artifact_consumption.get("pkg.impl_b::foo_b", {}).get("consumers", [])


def test_full_static_channel_domain_all_six_channels_parity(tmp_path):
    """
    Proves exact Full vs Incremental parity across all 6 static channels:
    - api_imports
    - direct_calls
    - qualified_refs
    - callback_calls
    - event_bindings
    - inheritance
    """
    f_target = tmp_path / "target.py"
    f_target.write_text(
        "class Base:\n"
        "    pass\n\n"
        "def direct_fn():\n"
        "    return 1\n\n"
        "def qual_fn():\n"
        "    return 2\n\n"
        "def callback_fn():\n"
        "    return 3\n\n"
        "def event_fn():\n"
        "    return 4\n\n"
        "def import_only_fn():\n"
        "    return 5\n",
        encoding="utf-8",
    )

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text(
        "import target\n"
        "from target import Base, callback_fn, event_fn, import_only_fn\n\n"
        "class Derived(Base):\n"
        "    pass\n\n"
        "target.direct_fn()\n"
        "_ref = target.qual_fn\n\n"
        "def helper(callback=None):\n"
        "    pass\n\n"
        "helper(callback=callback_fn)\n\n"
        "class Emitter:\n"
        "    def subscribe(self, event, fn):\n"
        "        pass\n\n"
        "e = Emitter()\n"
        "e.subscribe('user_created', event_fn)\n",
        encoding="utf-8",
    )

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    res = engine.update_file(str(f_consumer))

    assert res.artifact_consumption_state == "fresh"

    # Verify channels in incremental
    cons = engine.state.artifact_consumption
    assert set(cons["target::Base"]["channels"]["consumer"]) == {"inheritance", "api_imports"}
    assert cons["target::direct_fn"]["channels"]["consumer"] == ["direct_calls"]
    assert cons["target::qual_fn"]["channels"]["consumer"] == ["qualified_refs"]
    assert set(cons["target::callback_fn"]["channels"]["consumer"]) == {"callback_calls", "api_imports"}
    assert set(cons["target::event_fn"]["channels"]["consumer"]) == {"event_bindings", "api_imports"}
    assert cons["target::import_only_fn"]["channels"]["consumer"] == ["api_imports"]

    # Full analysis parity
    oracle = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle)


def test_full_canonical_parity_import_and_graph(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_other = tmp_path / "other.py"
    f_other.write_text("def bar(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("import target\ntarget.foo()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    engine.update_file(str(f_other))
    engine.update_file(str(f_consumer))

    # Add second import
    f_consumer.write_text("import target\nimport other\ntarget.foo()\nother.bar()\n", encoding="utf-8")
    res = engine.update_file(str(f_consumer))

    assert res.graph_state == "fresh"
    assert res.dependencies_state == "fresh"
    assert res.blast_radius_state == "fresh"
    assert res.artifact_consumption_state == "fresh"

    oracle = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle)


def test_full_canonical_parity_module_add_and_delete(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    res_add = engine.update_file(str(f_consumer))

    assert res_add.graph_state == "fresh"
    assert res_add.artifact_consumption_state == "fresh"

    oracle_add = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle_add)

    # Delete target
    f_target.unlink()
    res_del = engine.update_file(str(f_target))

    assert res_del.graph_state == "fresh"
    assert res_del.artifact_consumption_state == "fresh"

    oracle_del = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle_del)


def test_true_order_independence_three_way_equality(tmp_path):
    """
    Proves true order independence and three-way equality:
    1. Real Full Analysis (ContextorFacade)
    2. Incremental Provider-First: update(provider) -> update(consumer)
    3. Incremental Consumer-First: update(consumer) -> update(provider) without calling update(consumer) again.
    """
    f_consumer = tmp_path / "a_consumer.py"
    f_consumer.write_text("from z_provider import foo\ndef use():\n    return foo()\n", encoding="utf-8")
    f_provider = tmp_path / "z_provider.py"
    f_provider.write_text("def foo():\n    return 1\n", encoding="utf-8")

    # 1. Real Full Analysis Oracle
    oracle_state = _build_full_static_state(tmp_path)
    assert oracle_state.artifact_consumption_state == "fresh"
    assert "a_consumer" in oracle_state.artifact_consumption.get("z_provider::foo", {}).get("consumers", [])

    # 2. Incremental Provider-First
    cache_dir_p = tmp_path / "cache_p"
    cache_dir_p.mkdir()
    engine_provider_first = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir_p)),
        str(tmp_path),
    )
    engine_provider_first.update_file(str(f_provider))
    res_p = engine_provider_first.update_file(str(f_consumer))
    assert res_p.artifact_consumption_state == "fresh"
    state_provider_first = engine_provider_first.state

    # 3. Incremental Consumer-First (consumer updated before provider exists)
    cache_dir_c = tmp_path / "cache_c"
    cache_dir_c.mkdir()
    engine_consumer_first = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir_c)),
        str(tmp_path),
    )
    res_c1 = engine_consumer_first.update_file(str(f_consumer))
    assert res_c1.artifact_consumption_state == "fresh"
    # Second update is provider ONLY (no manual second update of consumer)
    res_c2 = engine_consumer_first.update_file(str(f_provider))
    assert res_c2.artifact_consumption_state == "fresh"
    state_consumer_first = engine_consumer_first.state

    # 4. Three-Way Equality Verification
    _assert_full_parity(state_provider_first, oracle_state)
    _assert_full_parity(state_consumer_first, oracle_state)
    _assert_full_parity(state_consumer_first, state_provider_first)


def test_definition_add_backfill_without_reread(tmp_path):
    """
    Proves definition addition in an existing module triggers selective backfill
    for existing consumers without rereading the consumer source file from disk.
    Uses real spy on extract_module_usage_facts to prove consumer is never parsed during provider update.
    """
    f_provider = tmp_path / "provider.py"
    f_provider.write_text("def bar():\n    return 0\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from provider import foo\ndef use():\n    return foo()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_consumer))
    engine.update_file(str(f_provider))

    # consumer is not bound to provider::bar
    assert "consumer" not in engine.state.artifact_consumption.get("provider::bar", {}).get("consumers", [])

    # Modify provider: add def foo()
    f_provider.write_text("def bar():\n    return 0\ndef foo():\n    return 42\n", encoding="utf-8")

    # Real spy on source extraction boundary
    analyzed_modules = []
    original_extract = extract_module_usage_facts

    def spy_extract(module_path, *args, **kwargs):
        analyzed_modules.append(module_path)
        return original_extract(module_path, *args, **kwargs)

    with patch("contextor.core.reference.engine.extract_module_usage_facts", side_effect=spy_extract):
        res = engine.update_file(str(f_provider))

    # Assert ONLY provider was parsed/extracted, consumer was NOT reread from disk
    assert "provider" in analyzed_modules
    assert "consumer" not in analyzed_modules

    assert res.artifact_consumption_state == "fresh"
    assert "consumer" in engine.state.artifact_consumption.get("provider::foo", {}).get("consumers", [])
    assert set(engine.state.artifact_consumption["provider::foo"]["channels"]["consumer"]) == {"api_imports", "direct_calls"}

    # Full analysis parity
    oracle = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle)


def test_ambiguity_regression_real_backfill_path(tmp_path):
    """
    Proves that when a definition or provider update encounters ambiguity during backfill:
    1. The ambiguous candidate slice is rejected in transactional fashion.
    2. artifact_consumption_state fails closed to 'stale'.
    3. Failure is sticky and no arbitrary target is bound.
    """
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from pkg.impl_a import foo\nfoo()\n", encoding="utf-8")

    f_provider = pkg_dir / "impl_a.py"
    f_provider.write_text("def bar(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_consumer))
    engine.update_file(str(f_provider))

    # Now modify provider to add def foo(), but simulate ambiguity during resolution
    f_provider.write_text("def bar(): pass\ndef foo(): pass\n", encoding="utf-8")

    from contextor.core.analysis.incremental import plan_executor
    original_resolve = plan_executor._resolve_canonical_target_key

    def ambiguous_resolve(target, candidate_consumption, candidate_artifacts):
        if target and "foo" in target:
            return None, "ambiguous"
        return original_resolve(target, candidate_consumption, candidate_artifacts)

    with patch("contextor.core.analysis.incremental.plan_executor._resolve_canonical_target_key", side_effect=ambiguous_resolve):
        res = engine.update_file(str(f_provider))

    # Assert fail-closed state
    assert res.artifact_consumption_state == "stale"
    assert engine.state.artifact_consumption_state == "stale"

    # Assert no arbitrary binding occurred for consumer
    for target_key, entry in engine.state.artifact_consumption.items():
        assert "consumer" not in entry.get("consumers", [])


def test_unresolved_target_never_appears(tmp_path):
    """Proves unresolved external-like references remain legal and do not invent false relations."""
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("import external_pkg\nexternal_pkg.unknown_func()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    res = engine.update_file(str(f_consumer))
    assert res.artifact_consumption_state == "fresh"
    assert engine.state.artifact_consumption == {}


def test_provider_appears_without_requested_symbol(tmp_path):
    """Proves provider appearing without requested symbol does not falsely bind."""
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from provider import missing_func\nmissing_func()\n", encoding="utf-8")
    f_provider = tmp_path / "provider.py"
    f_provider.write_text("def actual_func(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_consumer))
    res = engine.update_file(str(f_provider))

    assert res.artifact_consumption_state == "fresh"
    assert engine.state.artifact_consumption.get("provider::actual_func", {}).get("consumers") == []


def test_unrelated_module_in_same_package_no_false_bind(tmp_path):
    """Proves adding pkg.impl_b does not bind references targeting pkg.impl_a."""
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from pkg.impl_a import foo\nfoo()\n", encoding="utf-8")

    f_impl_b = pkg_dir / "impl_b.py"
    f_impl_b.write_text("def foo(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_consumer))
    res = engine.update_file(str(f_impl_b))

    assert res.artifact_consumption_state == "fresh"
    assert engine.state.artifact_consumption.get("pkg.impl_b::foo", {}).get("consumers") == []


def test_cow_atomicity_on_provider_add(tmp_path):
    """Proves previous canonical state object is not mutated in-place when provider is added."""
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from provider import foo\nfoo()\n", encoding="utf-8")
    f_provider = tmp_path / "provider.py"
    f_provider.write_text("def foo(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_consumer))
    old_state_consumption = engine.state.artifact_consumption
    old_state_modules = engine.state.modules

    # Add provider
    engine.update_file(str(f_provider))

    # Assert old state was not mutated in place
    assert old_state_consumption == {}
    assert "provider" not in old_state_modules
    assert "provider::foo" in engine.state.artifact_consumption


def test_requires_resync_handling(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))

    # Mock RefreshPlanner to return requires_resync plan
    resync_plan = RefreshPlan(
        reparse_modules=(),
        recompute_modules=(),
        patch_families=("module_usages",),
        graph_recomputations=(),
        refresh_completeness="requires_resync",
        reason="Structural resync required",
    )
    with patch.object(RefreshPlanner, "plan_refresh", return_value=resync_plan):
        f_target.write_text("def foo(): pass\ndef bar(): pass\n", encoding="utf-8")
        res = engine.update_file(str(f_target))

        assert res.graph_state == "stale"
        assert res.dependencies_state == "stale"
        assert res.blast_radius_state == "deferred"
        assert res.artifact_consumption_state == "stale"
        assert res.shadow_plan.refresh_completeness == "requires_resync"


def test_runtime_unresolved_handling(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))

    # Plan with runtime_unresolved certainty but complete refresh
    runtime_plan = RefreshPlan(
        reparse_modules=(),
        recompute_modules=(),
        patch_families=("module_usages", "artifact_consumption"),
        graph_recomputations=(),
        refresh_completeness="complete",
        semantic_certainty="runtime_unresolved",
        reason="Dynamic reflection unresolved",
    )
    with patch.object(RefreshPlanner, "plan_refresh", return_value=runtime_plan):
        f_target.write_text("def foo(): pass\ndef dynamic_call(): pass\n", encoding="utf-8")
        res = engine.update_file(str(f_target))

        assert res.artifact_consumption_state == "fresh"
        assert res.shadow_plan.semantic_certainty == "runtime_unresolved"


def test_cow_atomicity_across_families(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    engine.update_file(str(f_consumer))

    old_modules = engine.state.modules
    old_artifacts = engine.state.artifacts
    old_usages = engine.state.module_usages
    old_consumption = engine.state.artifact_consumption
    old_entry = old_consumption.get("target::foo", {})
    old_consumers = list(old_entry.get("consumers", []))

    # Modify consumer
    f_consumer.write_text("def own_func(): pass\n", encoding="utf-8")
    engine.update_file(str(f_consumer))

    # Assert old retained references were not mutated
    assert "target" in old_modules
    assert "target" in old_artifacts
    assert "consumer" in old_usages
    assert old_entry.get("consumers") == old_consumers


def test_fail_closed_on_unsupported_plan_item(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))

    # Mock RefreshPlan with unsupported patch family
    bad_plan = MagicMock()
    bad_plan.reparse_modules = ()
    bad_plan.recompute_modules = ()
    bad_plan.patch_families = ("unsupported_future_family",)
    bad_plan.graph_recomputations = ()
    bad_plan.refresh_completeness = "complete"

    with patch.object(RefreshPlanner, "plan_refresh", return_value=bad_plan):
        f_target.write_text("def foo(): pass\ndef bar(): pass\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported patch family"):
            engine._apply_delta_and_commit(
                str(f_target),
                FileDelta(module_path="target"),
                UsageDelta(module_path="target"),
                bad_plan,
                [],
                {},
                ModuleUsageFacts(),
            )

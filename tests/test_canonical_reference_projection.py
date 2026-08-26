import ast
import builtins
import copy
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.reference.engine import (
    build_symbol_references,
    build_symbol_references_from_canonical,
    CanonicalReferenceEvidenceUnavailable,
)
from contextor.core.single_file.single_file_analysis import collect_all_contexts
from contextor.core.api.api_consumers import extract_api_consumers, summarize_api_consumers


@pytest.fixture
def multi_channel_repo():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pkg = root / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")

        provider_code = """
class BaseService:
    def base_method(self):
        pass

class Worker:
    def run(self):
        pass

def compute_sum(a, b):
    return a + b

def execute_callback(cb):
    pass

def on_custom_event(data):
    pass

GLOBAL_CONFIG = {"key": "val"}
UNUSED_PROVIDER_SYM = 42
"""
        (pkg / "provider.py").write_text(provider_code, encoding="utf-8")

        consumer_a_code = """
from pkg.provider import BaseService, Worker, compute_sum, execute_callback, on_custom_event, GLOBAL_CONFIG
import pkg.provider as p

class ConcreteService(BaseService):
    def handle(self):
        self.base_method()

def run_consumer_a():
    res = compute_sum(1, 2)
    def my_cb(): pass
    execute_callback(callback=my_cb)
    cfg = p.GLOBAL_CONFIG
"""
        (pkg / "consumer_a.py").write_text(consumer_a_code, encoding="utf-8")

        consumer_b_code = """
import pkg.provider as prov

class EventBroker:
    def bind(self, event_name, handler):
        pass

def setup_events():
    b = EventBroker()
    b.bind("action", prov.on_custom_event)
    w = prov.Worker()
    getattr(prov, "compute_sum")(10, 20)
"""
        (pkg / "consumer_b.py").write_text(consumer_b_code, encoding="utf-8")

        from contextor.core.graph.graph import build_graph

        ContextorFacade.analyze_project(td)
        hydrated = hydrate_repository_engine(td)
        state = hydrated.engine.state
        graph = build_graph(state.modules)

        yield td, state, graph


def test_golden_parity_matrix(multi_channel_repo):
    td, state, graph = multi_channel_repo
    symbols = [
        "BaseService",
        "Worker",
        "compute_sum",
        "execute_callback",
        "on_custom_event",
        "GLOBAL_CONFIG",
        "UNUSED_PROVIDER_SYM",
    ]

    legacy = build_symbol_references(
        state.modules,
        symbols,
        td,
        definer_module="pkg.provider",
    )

    current_modules = {
        m
        for m in state.modules
        if getattr(state, "artifacts", {}).get(m, {}).get("is_valid", True)
    }

    canonical = build_symbol_references_from_canonical(
        definer_module="pkg.provider",
        symbols=symbols,
        artifact_consumption=state.artifact_consumption,
        module_usages=state.module_usages,
        current_modules=current_modules,
    )

    # Explicit assertion that called_by_ambiguous is populated from consumer_b
    assert "pkg.consumer_b" in legacy["compute_sum"]["called_by_ambiguous"]
    assert len(legacy["compute_sum"]["called_by_ambiguous_detail"]) > 0
    assert canonical["compute_sum"]["called_by_ambiguous"] == legacy["compute_sum"]["called_by_ambiguous"]
    assert canonical["compute_sum"]["called_by_ambiguous_detail"] == legacy["compute_sum"]["called_by_ambiguous_detail"]

    assert canonical == legacy, f"Mismatch:\nCanonical: {canonical}\nLegacy: {legacy}"

    # Downstream consumers parity
    legacy_consumers = extract_api_consumers(symbols, legacy)
    canonical_consumers = extract_api_consumers(symbols, canonical)
    assert canonical_consumers == legacy_consumers

    assert summarize_api_consumers(canonical_consumers) == summarize_api_consumers(legacy_consumers)


def test_zero_io_and_zero_ast_parses_during_canonical_projection(multi_channel_repo):
    td, state, graph = multi_channel_repo
    symbols = [
        "BaseService",
        "Worker",
        "compute_sum",
        "execute_callback",
        "on_custom_event",
        "GLOBAL_CONFIG",
        "UNUSED_PROVIDER_SYM",
    ]

    current_consumers = set(state.module_usages.keys())

    original_open = builtins.open
    original_read_text = Path.read_text
    original_parse = ast.parse

    io_tracker = {"opens": 0, "read_text": 0, "parses": 0}

    def guarded_open(*args, **kwargs):
        io_tracker["opens"] += 1
        return original_open(*args, **kwargs)

    def guarded_read_text(*args, **kwargs):
        io_tracker["read_text"] += 1
        return original_read_text(*args, **kwargs)

    def guarded_parse(*args, **kwargs):
        io_tracker["parses"] += 1
        return original_parse(*args, **kwargs)

    with patch("builtins.open", side_effect=guarded_open), \
         patch("pathlib.Path.read_text", side_effect=guarded_read_text), \
         patch("ast.parse", side_effect=guarded_parse):

        canonical = build_symbol_references_from_canonical(
            definer_module="pkg.provider",
            symbols=symbols,
            artifact_consumption=state.artifact_consumption,
            module_usages=state.module_usages,
            current_modules=current_consumers,
        )

    assert io_tracker["opens"] == 0
    assert io_tracker["read_text"] == 0
    assert io_tracker["parses"] == 0
    assert "compute_sum" in canonical


def test_single_file_builder_uses_canonical_references(multi_channel_repo):
    td, state, graph = multi_channel_repo
    provider_file = str(Path(td) / "pkg" / "provider.py")

    with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references") as legacy_spy:
        res = collect_all_contexts(
            provider_file,
            state.modules,
            graph,
            root_path=td,
            engine_state=state,
        )
        assert not legacy_spy.called, "build_symbol_references should NOT have been called when canonical state is fresh"

    sym_ctx = res.get("symbol_context", {})
    assert "references" in sym_ctx
    assert "compute_sum" in sym_ctx["references"]
    assert "pkg.consumer_a" in sym_ctx["references"]["compute_sum"]["called_by"]


def test_fallback_when_artifact_consumption_deferred(multi_channel_repo):
    td, state, graph = multi_channel_repo
    provider_file = str(Path(td) / "pkg" / "provider.py")

    # Clone state with deferred consumption
    deferred_state = copy.copy(state)
    object.__setattr__(deferred_state, "artifact_consumption_state", "deferred")

    with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references", wraps=build_symbol_references) as legacy_spy:
        res = collect_all_contexts(
            provider_file,
            state.modules,
            graph,
            root_path=td,
            engine_state=deferred_state,
        )
        assert legacy_spy.called, "build_symbol_references MUST be called when artifact_consumption_state != 'fresh'"

    sym_ctx = res.get("symbol_context", {})
    assert "references" in sym_ctx
    assert "compute_sum" in sym_ctx["references"]


def test_fallback_when_consumer_is_not_current(multi_channel_repo):
    td, state, graph = multi_channel_repo
    symbols = ["compute_sum"]

    # Provide current_modules that excludes confirmed consumer pkg.consumer_a
    current_consumers = {"pkg.consumer_b"}

    with pytest.raises(CanonicalReferenceEvidenceUnavailable):
        build_symbol_references_from_canonical(
            definer_module="pkg.provider",
            symbols=symbols,
            artifact_consumption=state.artifact_consumption,
            module_usages=state.module_usages,
            current_modules=current_consumers,
        )


def test_fallback_when_consumer_facts_missing(multi_channel_repo):
    td, state, graph = multi_channel_repo
    symbols = ["compute_sum"]

    incomplete_usages = {
        k: v for k, v in state.module_usages.items() if k != "pkg.consumer_a"
    }

    with pytest.raises(CanonicalReferenceEvidenceUnavailable):
        build_symbol_references_from_canonical(
            definer_module="pkg.provider",
            symbols=symbols,
            artifact_consumption=state.artifact_consumption,
            module_usages=incomplete_usages,
            current_modules=set(state.module_usages.keys()),
        )


def test_visitor_instance_method_candidate_and_resolver_semantics():
    from contextor.core.reference.visitor import SymbolReferenceVisitor

    visitor = SymbolReferenceVisitor(
        target_symbols={"KnownClass.valid_method"},
        current_module="pkg.consumer",
    )
    visitor.instances["srv"] = "KnownClass"

    # Case A: Candidate matches an untargeted method
    candidate = visitor._instance_method_candidate("srv.untargeted_method")
    assert candidate == "KnownClass.untargeted_method"
    # Legacy resolver must return None because it is NOT in target_symbols
    assert visitor._resolve_instance_method("srv.untargeted_method") is None

    # Case B: Candidate matches a targeted method
    candidate_targeted = visitor._instance_method_candidate("srv.valid_method")
    assert candidate_targeted == "KnownClass.valid_method"
    # Legacy resolver returns the candidate because it IS in target_symbols
    assert visitor._resolve_instance_method("srv.valid_method") == "KnownClass.valid_method"


def test_old_snapshot_dict_unmaterialized_fails_closed(multi_channel_repo):
    from contextor.core.domain.usage_facts import ModuleUsageFacts

    td, state, graph = multi_channel_repo
    symbols = ["compute_sum"]

    legacy_dict = {
        "imports": ["pkg.provider"],
        "direct_calls": ["pkg.provider.compute_sum"],
        "runtime_calls": [],
        "callback_calls": [],
        "event_bindings": [],
        "inheritance_refs": [],
        "qualified_refs": [],
        "aliases": [],
        "symbol_calls": [],
        "symbol_calls_materialized": True,
        # Intentionally omitting reference_evidence and reference_evidence_materialized
    }

    old_facts = ModuleUsageFacts.from_dict(legacy_dict)
    assert old_facts.reference_evidence == ()
    assert old_facts.reference_evidence_materialized is False

    mock_usages = dict(state.module_usages)
    mock_usages["pkg.consumer_a"] = old_facts

    with pytest.raises(CanonicalReferenceEvidenceUnavailable) as exc_info:
        build_symbol_references_from_canonical(
            definer_module="pkg.provider",
            symbols=symbols,
            artifact_consumption=state.artifact_consumption,
            module_usages=mock_usages,
            current_modules=set(state.module_usages.keys()),
        )
    assert "Reference evidence not materialized" in str(exc_info.value)


def test_empty_current_evidence_is_distinguished_from_unmaterialized(multi_channel_repo):
    from contextor.core.domain.usage_facts import ModuleUsageFacts

    td, state, graph = multi_channel_repo
    symbols = ["compute_sum"]

    empty_materialized_facts = ModuleUsageFacts(
        imports=("pkg.provider",),
        direct_calls=(),
        runtime_calls=(),
        callback_calls=(),
        event_bindings=(),
        inheritance_refs=(),
        qualified_refs=(),
        aliases=(),
        symbol_calls=(),
        symbol_calls_materialized=True,
        reference_evidence=(),
        reference_evidence_materialized=True,
    )

    mock_usages = dict(state.module_usages)
    mock_usages["pkg.consumer_a"] = empty_materialized_facts

    # When materialized is True, it does NOT raise CanonicalReferenceEvidenceUnavailable
    res = build_symbol_references_from_canonical(
        definer_module="pkg.provider",
        symbols=symbols,
        artifact_consumption=state.artifact_consumption,
        module_usages=mock_usages,
        current_modules=set(state.module_usages.keys()),
    )
    assert "compute_sum" in res


def test_single_file_builder_fallback_on_unmaterialized_consumer_evidence(multi_channel_repo):
    from contextor.core.domain.usage_facts import ModuleUsageFacts

    td, state, graph = multi_channel_repo
    provider_file = str(Path(td) / "pkg" / "provider.py")

    unmaterialized_facts = ModuleUsageFacts(
        imports=("pkg.provider",),
        direct_calls=("pkg.provider.compute_sum",),
        runtime_calls=(),
        callback_calls=(),
        event_bindings=(),
        inheritance_refs=(),
        qualified_refs=(),
        aliases=(),
        symbol_calls=(),
        symbol_calls_materialized=True,
        reference_evidence=(),
        reference_evidence_materialized=False,
    )

    unmaterialized_state = copy.copy(state)
    mock_usages = dict(state.module_usages)
    mock_usages["pkg.consumer_a"] = unmaterialized_facts
    object.__setattr__(unmaterialized_state, "module_usages", mock_usages)

    with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references", wraps=build_symbol_references) as legacy_spy:
        res = collect_all_contexts(
            provider_file,
            state.modules,
            graph,
            root_path=td,
            engine_state=unmaterialized_state,
        )
        assert legacy_spy.called, "build_symbol_references MUST be called when consumer evidence is not materialized"

    sym_ctx = res.get("symbol_context", {})
    assert "references" in sym_ctx
    assert "compute_sum" in sym_ctx["references"]


def test_module_usage_facts_serialization_roundtrip_and_backward_compat():
    from contextor.core.domain.usage_facts import ModuleUsageFacts

    # 1. Roundtrip populated facts
    facts = ModuleUsageFacts(
        imports=("pkg.provider",),
        direct_calls=("pkg.provider.compute_sum",),
        reference_evidence=(
            ("pkg.provider.compute_sum", "direct_calls", "caller_func", 42),
        ),
        reference_evidence_materialized=True,
    )
    data = facts.to_dict()
    assert data["reference_evidence_materialized"] is True
    assert len(data["reference_evidence"]) == 1
    assert data["reference_evidence"][0]["line"] == 42

    restored = ModuleUsageFacts.from_dict(data)
    assert restored.reference_evidence == facts.reference_evidence
    assert restored.reference_evidence_materialized is True

    # 2. Roundtrip empty facts with materialized True
    empty_facts = ModuleUsageFacts(
        reference_evidence=(),
        reference_evidence_materialized=True,
    )
    empty_data = empty_facts.to_dict()
    assert empty_data["reference_evidence_materialized"] is True
    restored_empty = ModuleUsageFacts.from_dict(empty_data)
    assert restored_empty.reference_evidence == ()
    assert restored_empty.reference_evidence_materialized is True

    # 3. Old dict without reference_evidence_materialized
    old_data = {"imports": ["foo"]}
    old_restored = ModuleUsageFacts.from_dict(old_data)
    assert old_restored.reference_evidence == ()
    assert old_restored.reference_evidence_materialized is False

    # 4. Attribute fallback for objects restored without field in __dict__
    bare_obj = object.__new__(ModuleUsageFacts)
    assert bare_obj.reference_evidence == ()
    assert bare_obj.reference_evidence_materialized is False


def test_incremental_update_file_materializes_reference_evidence(multi_channel_repo):
    td, state, graph = multi_channel_repo

    hydrated = hydrate_repository_engine(td)
    engine = hydrated.engine

    # Check that initial analysis marked module_usages as materialized
    assert engine.state.module_usages["pkg.consumer_a"].reference_evidence_materialized is True

    # Update consumer_a.py on disk
    consumer_a_path = str(Path(td) / "pkg" / "consumer_a.py")
    updated_code = """
from pkg.provider import compute_sum

def run_updated():
    compute_sum(100, 200)
"""
    Path(consumer_a_path).write_text(updated_code, encoding="utf-8")
    engine.update_file(consumer_a_path)

    updated_facts = engine.state.module_usages["pkg.consumer_a"]
    assert updated_facts.reference_evidence_materialized is True
    assert any(ev[0].endswith("compute_sum") for ev in updated_facts.reference_evidence)


def test_unmaterialized_unconfirmed_current_module_forces_fallback(multi_channel_repo):
    from contextor.core.domain.usage_facts import ModuleUsageFacts

    td, state, graph = multi_channel_repo
    provider_file = str(Path(td) / "pkg" / "provider.py")

    # pkg.__init__ is current in repository, but not a confirmed consumer of provider
    unmaterialized_unrelated = ModuleUsageFacts(
        imports=(),
        direct_calls=(),
        runtime_calls=(),
        callback_calls=(),
        event_bindings=(),
        inheritance_refs=(),
        qualified_refs=(),
        aliases=(),
        symbol_calls=(),
        symbol_calls_materialized=True,
        reference_evidence=(),
        reference_evidence_materialized=False,
    )

    mutated_state = copy.copy(state)
    mock_usages = dict(state.module_usages)
    mock_usages["pkg.__init__"] = unmaterialized_unrelated
    object.__setattr__(mutated_state, "module_usages", mock_usages)

    with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references", wraps=build_symbol_references) as legacy_spy:
        res = collect_all_contexts(
            provider_file,
            state.modules,
            graph,
            root_path=td,
            engine_state=mutated_state,
        )
        assert legacy_spy.called, "build_symbol_references MUST be called when any current module evidence is unmaterialized"


def test_missing_usage_for_unconfirmed_current_module_forces_fallback(multi_channel_repo):
    td, state, graph = multi_channel_repo
    provider_file = str(Path(td) / "pkg" / "provider.py")

    # Remove pkg.__init__ (a current module not consuming provider) from module_usages
    mutated_state = copy.copy(state)
    mock_usages = {k: v for k, v in state.module_usages.items() if k != "pkg.__init__"}
    object.__setattr__(mutated_state, "module_usages", mock_usages)

    with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references", wraps=build_symbol_references) as legacy_spy:
        res = collect_all_contexts(
            provider_file,
            state.modules,
            graph,
            root_path=td,
            engine_state=mutated_state,
        )
        assert legacy_spy.called, "build_symbol_references MUST be called when a current module is missing module_usages"


def test_direct_projector_ambiguous_completeness(multi_channel_repo):
    from contextor.core.domain.usage_facts import ModuleUsageFacts

    td, state, graph = multi_channel_repo
    symbols = ["compute_sum"]

    current_modules = {"pkg.provider", "pkg.consumer_a", "pkg.unrelated"}

    # 1. Missing module_usages for unrelated current module
    incomplete_usages = dict(state.module_usages)
    incomplete_usages.pop("pkg.unrelated", None)

    with pytest.raises(CanonicalReferenceEvidenceUnavailable) as exc_info:
        build_symbol_references_from_canonical(
            definer_module="pkg.provider",
            symbols=symbols,
            artifact_consumption=state.artifact_consumption,
            module_usages=incomplete_usages,
            current_modules=current_modules,
        )
    assert "Missing module_usages for current module pkg.unrelated" in str(exc_info.value)

    # 2. Unmaterialized facts for unrelated current module
    unmaterialized_usages = dict(state.module_usages)
    unmaterialized_usages["pkg.unrelated"] = ModuleUsageFacts(
        reference_evidence=(),
        reference_evidence_materialized=False,
    )

    with pytest.raises(CanonicalReferenceEvidenceUnavailable) as exc_info:
        build_symbol_references_from_canonical(
            definer_module="pkg.provider",
            symbols=symbols,
            artifact_consumption=state.artifact_consumption,
            module_usages=unmaterialized_usages,
            current_modules=current_modules,
        )
    assert "Reference evidence not materialized for current module pkg.unrelated" in str(exc_info.value)

    # 3. Materialized empty facts for unrelated current module
    materialized_usages = dict(state.module_usages)
    materialized_usages["pkg.unrelated"] = ModuleUsageFacts(
        reference_evidence=(),
        reference_evidence_materialized=True,
    )

    res = build_symbol_references_from_canonical(
        definer_module="pkg.provider",
        symbols=symbols,
        artifact_consumption=state.artifact_consumption,
        module_usages=materialized_usages,
        current_modules=current_modules,
    )
    assert "compute_sum" in res

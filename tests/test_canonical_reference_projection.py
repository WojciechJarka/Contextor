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

        ContextorFacade.analyze_project(td)
        hydrated = hydrate_repository_engine(td)
        state = hydrated.engine.state

        yield td, state


def test_golden_parity_matrix(multi_channel_repo):
    td, state = multi_channel_repo
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

    current_consumers = {
        m
        for m in state.module_usages
        if getattr(state, "artifacts", {}).get(m, {}).get("is_valid", True)
    }

    canonical = build_symbol_references_from_canonical(
        definer_module="pkg.provider",
        symbols=symbols,
        artifact_consumption=state.artifact_consumption,
        module_usages=state.module_usages,
        current_modules=current_consumers,
    )

    assert canonical == legacy, f"Mismatch:\nCanonical: {canonical}\nLegacy: {legacy}"

    # Downstream consumers parity
    legacy_consumers = extract_api_consumers(symbols, legacy)
    canonical_consumers = extract_api_consumers(symbols, canonical)
    assert canonical_consumers == legacy_consumers

    assert summarize_api_consumers(canonical_consumers) == summarize_api_consumers(legacy_consumers)


def test_zero_io_and_zero_ast_parses_during_canonical_projection(multi_channel_repo):
    td, state = multi_channel_repo
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
    td, state = multi_channel_repo
    provider_file = str(Path(td) / "pkg" / "provider.py")

    with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references") as legacy_spy:
        res = collect_all_contexts(
            provider_file,
            state.modules,
            None,
            root_path=td,
            engine_state=state,
        )
        assert not legacy_spy.called, "build_symbol_references should NOT have been called when canonical state is fresh"

    sym_ctx = res.get("symbol_context", {})
    assert "references" in sym_ctx
    assert "compute_sum" in sym_ctx["references"]
    assert "pkg.consumer_a" in sym_ctx["references"]["compute_sum"]["called_by"]


def test_fallback_when_artifact_consumption_deferred(multi_channel_repo):
    td, state = multi_channel_repo
    provider_file = str(Path(td) / "pkg" / "provider.py")

    # Clone state with deferred consumption
    deferred_state = copy.copy(state)
    object.__setattr__(deferred_state, "artifact_consumption_state", "deferred")

    with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references", wraps=build_symbol_references) as legacy_spy:
        res = collect_all_contexts(
            provider_file,
            state.modules,
            None,
            root_path=td,
            engine_state=deferred_state,
        )
        assert legacy_spy.called, "build_symbol_references MUST be called when artifact_consumption_state != 'fresh'"

    sym_ctx = res.get("symbol_context", {})
    assert "references" in sym_ctx
    assert "compute_sum" in sym_ctx["references"]


def test_fallback_when_consumer_is_not_current(multi_channel_repo):
    td, state = multi_channel_repo
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
    td, state = multi_channel_repo
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

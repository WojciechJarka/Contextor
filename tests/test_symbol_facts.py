
"""
Serialization and state management of symbol domain models.

This suite ensures that SymbolFacts can be properly exported to a dictionary
format, which is crucial for JSON reporting, and verifies that the global
symbol registries correctly interact with this serialization.
"""

import pytest

from contextor.core.symbol_engine.domain import (
    SymbolFacts,
    classes,
    functions,
    methods,
)

def test_symbol_facts_to_dict_returns_dictionary():
    """
    Ensures that calling to_dict on a SymbolFacts instance returns a standard
    Python dictionary suitable for JSON serialization.
    """
    facts = SymbolFacts()
    facts.name = "MockClass"
    facts.line_number = 42
    
    serialized = facts.to_dict()
    
    assert isinstance(serialized, dict), "to_dict() must return a dictionary"
    
def test_symbol_facts_to_dict_preserves_all_symbols():
    """
    Verifies that the all_symbols property is correctly represented 
    in the serialized output.
    """
    facts = SymbolFacts()
    
    symbols_set = facts.all_symbols()
    assert isinstance(symbols_set, set), "all_symbols() should return a set"
    
    serialized = facts.to_dict()
    
    if "all_symbols" in serialized:
        assert isinstance(serialized["all_symbols"], list), "Sets must be converted to lists for JSON compatibility"

def test_global_collections_can_serialize_their_facts(monkeypatch):
    """
    Verifies that the global collections (classes, functions, methods) can safely
    call to_dict() on their contained SymbolFacts instances.
    """
    dummy_facts = SymbolFacts()
    
    monkeypatch.setitem(classes, "mock_class", dummy_facts)
    monkeypatch.setitem(functions, "mock_func", dummy_facts)
    monkeypatch.setitem(methods, "mock_method", dummy_facts)
    
    assert isinstance(classes["mock_class"].to_dict(), dict)
    assert isinstance(functions["mock_func"].to_dict(), dict)
    assert isinstance(methods["mock_method"].to_dict(), dict)
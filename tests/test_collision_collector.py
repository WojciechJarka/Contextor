"""Focused tests for public API collision symbol collection."""

import ast

from contextor.core.validator.collisions import PublicSymbolCollector


def test_collision_collector_ignores_classes_local_to_functions():
    tree = ast.parse(
        """
class PublicClient:
    pass

def factory():
    class LocalClient:
        pass
    return LocalClient

async def async_factory():
    class AsyncLocalClient:
        pass
    return AsyncLocalClient
"""
    )
    collector = PublicSymbolCollector("pkg.module")

    collector.visit(tree)

    classes = {
        symbol["name"]
        for symbol in collector.symbols
        if symbol["type"] == "class"
    }
    assert classes == {"PublicClient"}

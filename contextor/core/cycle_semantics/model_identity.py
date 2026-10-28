"""Identity translation within an explicitly indexed regular-package model."""

from __future__ import annotations


def indexed_to_logical_module(module_id: str) -> str:
    if module_id.endswith(".__init__"):
        return module_id.removesuffix(".__init__")
    return module_id


def logical_to_indexed_module(
    logical_name: str,
    indexed_ids: frozenset[str],
) -> str | None:
    initializer = logical_name + ".__init__"
    direct = logical_name in indexed_ids
    package = initializer in indexed_ids
    if direct and package:
        return None
    if direct:
        return logical_name
    if package:
        return initializer
    return None

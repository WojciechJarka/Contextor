"""Cheap report-compatible projection of artifacts already held in LIVE."""

from __future__ import annotations

from typing import Any


def canonical_artifact_report(
    module_artifacts: dict[str, Any],
) -> dict[str, Any]:
    """Project canonical per-module artifacts without reparsing repository files."""

    artifacts: dict[str, dict[str, Any]] = {}
    usage_sidecar: dict[str, dict[str, Any]] = {}
    for module_name, module_data in (module_artifacts or {}).items():
        if not isinstance(module_data, dict):
            continue
        consumers = module_data.get("consumers", {}) or {}
        if not isinstance(consumers, dict):
            continue
        for symbol, consumer_data in consumers.items():
            if not isinstance(consumer_data, dict):
                continue
            full_name = f"{module_name}::{symbol}"
            artifacts[full_name] = {
                "artifact_id": full_name,
                "definer_module": module_name,
                "consumers": list(consumer_data.get("consumers", []) or []),
                "kind": _symbol_kind(module_data.get("symbols", {}), str(symbol)),
            }
            usage = consumer_data.get("usage", {})
            if isinstance(usage, dict):
                usage_sidecar[full_name] = usage
    return {
        "artifacts": artifacts,
        "_usage_sidecar": usage_sidecar,
        "_module_artifacts": module_artifacts,
    }


def _symbol_kind(symbols: Any, symbol: str) -> str:
    if not isinstance(symbols, dict):
        return "unknown"
    for category, kind in (
        ("classes", "class"),
        ("functions", "function"),
        ("methods", "method"),
        ("globals", "global"),
    ):
        if symbol in (symbols.get(category, []) or []):
            return kind
    return "unknown"


__all__ = ["canonical_artifact_report"]

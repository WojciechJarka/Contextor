"""Normalize internal canonical LIVE objects into inert JSON-safe records."""

from __future__ import annotations

from typing import Any


def module_records(state: Any) -> list[dict[str, Any]]:
    records = []
    for module_name, module in getattr(state, "modules", {}).items():
        imports = list(getattr(module, "imports", []) or [])
        records.append(
            {
                "module_name": str(module_name),
                "module_id": str(getattr(module, "module_id", module_name)),
                "path": str(getattr(module, "path", "")),
                "import_count": len(imports),
                "imports": [
                    {
                        "module": getattr(item, "module", None),
                        "level": getattr(item, "level", 0),
                        "names": list(getattr(item, "names", []) or []),
                        "is_from_import": bool(getattr(item, "is_from_import", False)),
                        "is_local": bool(getattr(item, "is_local", False)),
                        "type_only": bool(getattr(item, "type_only", False)),
                    }
                    for item in imports
                ],
            }
        )
    return sorted(records, key=lambda item: item["module_name"])


def _artifact_kind(symbol: str, symbols: dict[str, Any]) -> str:
    categories = [
        kind
        for category, kind in (
            ("classes", "class"),
            ("functions", "function"),
            ("methods", "method"),
            ("globals", "global"),
        )
        if symbol in (symbols.get(category, []) or [])
    ]
    return categories[0] if len(categories) == 1 else "ambiguous"


def artifact_records(state: Any) -> list[dict[str, Any]]:
    records = []
    for module_name, raw in getattr(state, "artifacts", {}).items():
        symbols = raw.get("symbols", {}) or {}
        consumers_map = raw.get("consumers", {}) or {}
        for artifact_name in raw.get("own_symbols", []) or []:
            available = artifact_name in consumers_map
            consumer_record = consumers_map.get(artifact_name, {}) if available else {}
            signature = (symbols.get("signatures", {}) or {}).get(artifact_name) or None
            records.append(
                {
                    "artifact_name": str(artifact_name),
                    "full_name": f"{module_name}::{artifact_name}",
                    "module_name": str(module_name),
                    "kind": _artifact_kind(str(artifact_name), symbols),
                    "signature": signature,
                    "consumer_data_available": available,
                    "consumer_count": (
                        int((consumer_record.get("consumer_count", {}) or {}).get("total", 0))
                        if available else None
                    ),
                    "consumers": (
                        list(consumer_record.get("consumers", []) or []) if available else None
                    ),
                }
            )
    return sorted(records, key=lambda item: (item["module_name"], item["artifact_name"]))


def dependency_records(state: Any) -> list[dict[str, Any]]:
    graph = getattr(state, "dependency_graph", None)
    records = []
    for edge_type, edges in (
        ("hard", getattr(graph, "hard_edges", {}) if graph else {}),
        ("soft", getattr(graph, "soft_edges", {}) if graph else {}),
    ):
        for source, targets in edges.items():
            for target in targets:
                records.append({"source": str(source), "target": str(target), "edge_type": edge_type})
    return sorted(records, key=lambda item: (item["source"], item["target"], item["edge_type"]))


RECORD_BUILDERS = {
    "modules": module_records,
    "artifacts": artifact_records,
    "dependencies": dependency_records,
}

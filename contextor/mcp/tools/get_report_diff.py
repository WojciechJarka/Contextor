import json
from pathlib import Path

from contextor.mcp import query_helpers
from contextor.mcp import report_helpers


def get_report_diff(
    repo_path: str,
    max_items: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    diff_path = report_helpers.get_canonical_report(root, f"{repo_name}_report_diff.json")
    if not diff_path:
        return (
            f"No diff report found for '{repo_name}'. "
            "Run analyze_project at least twice (on different commits or code states) "
            "to generate a regression diff."
        )
    try:
        diff_data = json.loads(diff_path.read_text(encoding="utf-8"))
        report_diff = diff_data.get("report_diff", {})
        layers = report_diff.get("layers", {})
        layer_items, layer_total, layer_truncated = query_helpers.bounded_items(
            sorted(layers.items()), max_items
        )
        if compact:
            _ev_limit = 3 if max_items is None else min(3, max_items)
            layer_evidence = dict(list(layer_items)[:_ev_limit])
            layer_collection = {
                "total": layer_total,
                "truncated": layer_total > len(layer_evidence),
                "evidence": layer_evidence,
            }
            if layer_collection["truncated"]:
                layer_collection["expand"] = {"compact": False, "max_items": None}
        else:
            layer_collection = {"total": layer_total, "truncated": layer_truncated, "items": dict(layer_items)}
        diff_data["report_diff"] = {**report_diff, "layers": layer_collection}
        if fields is not None:
            allowed_fields = set(diff_data)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for get_report_diff",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            diff_data = {field: diff_data[field] for field in fields}
        return json.dumps(diff_data, indent=2)
    except Exception as e:
        return f"Error reading diff report: {e}"

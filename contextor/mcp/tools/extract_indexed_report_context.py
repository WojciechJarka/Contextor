import json
from pathlib import Path

from contextor.core import report_query
from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import report_helpers


def extract_indexed_report_context(
    repo_path: str,
    query: str,
    report_path: str = "",
    resolve_indices: bool = True,
    public_api_only: bool = False,
    max_items: int | None = 20,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    try:
        if report_path:
            selected_path = Path(report_path).expanduser()
            if not selected_path.is_absolute():
                selected_path = root / selected_path
            selected_path = selected_path.resolve()
        else:
            selected_path = report_helpers.get_canonical_report(
                root, f"{root.name}_artifacts_compact.json"
            )
        if not selected_path or not selected_path.is_file():
            return "Error: No indexed artifact report found. Run analysis or pass report_path."

        report = json.loads(selected_path.read_text(encoding="utf-8"))
        engine = mcp_runtime.get_or_init_engine(root)
        module_paths = None
        if engine:
            module_paths = {
                str(module_name): str(module.path)
                for module_name, module in engine.state.modules.items()
                if getattr(module, "path", None)
            }
        catalog = report_query.catalog_from_registry(str(root), module_paths=module_paths)
        if public_api_only:
            report = report_query.filter_public_artifact_report(report, catalog)
        result = report_query.query_indexed_report(
            report,
            query,
            catalog,
            repo_root=str(root),
            resolve_indices=resolve_indices,
        )
        artifact_entries = sorted(result.get("artifacts", {}).items())
        selected_entries, total_artifacts, artifacts_truncated = query_helpers.bounded_items(
            artifact_entries, max_items
        )
        result["artifacts"] = dict(selected_entries)
        result["artifact_count"] = len(selected_entries)
        result["total_artifact_count"] = total_artifacts
        result["truncated"] = artifacts_truncated
        result["data_source"] = str(selected_path)
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for extract_indexed_report_context",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error extracting indexed report context: {e}"

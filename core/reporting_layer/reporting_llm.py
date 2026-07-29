# -*- coding: utf-8 -*-

"""
repo_guardian/core/reporting_layer/reporting_llm.py

Generates an LLM-friendly Markdown summary of the module context
based on the `single_file_report`.
"""

import os
from datetime import datetime

def _format_api_surface(surface: dict) -> str:
    if not surface:
        return "No public API detected."

    lines = [
        "| Symbol | Type | Line | Signature | Consumers |",
        "|---|---|---|---|---|"
    ]
    for name, data in surface.items():
        kind = data.get("kind", "unknown")
        line_start = data.get("line_start", "?")
        signature = data.get("signature") or data.get("detailed_signature") or ""
        if signature:
            signature = f"`{signature}`"
        else:
            signature = "-"
        # In this simplified bundle, we skip consumer calculation details for brevity
        # but the symbol is listed clearly.
        lines.append(f"| `{name}` | {kind} | {line_start} | {signature} | _see single file JSON_ |")
    return "\n".join(lines)

def _format_git_context(git_ctx: dict) -> str:
    if not git_ctx or not git_ctx.get("last_modified"):
        return "No git data available."
    
    return (
        f"- **Last Modified:** {git_ctx.get('last_modified')} by {git_ctx.get('last_author')}\n"
        f"- **Commits (30d):** {git_ctx.get('commits_last_30d')} (Churn Score: {git_ctx.get('churn_score')})\n"
        f"- **Lines +/- (HEAD~1):** +{git_ctx.get('recent_changes', {}).get('lines_added')} / -{git_ctx.get('recent_changes', {}).get('lines_removed')}"
    )

def generate_llm_markdown(single_file_report: dict, output_path: str):
    """
    Transforms the JSON single file report into a Markdown context bundle.
    """
    directory = os.path.dirname(output_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    module_id = single_file_report.get("module", "unknown")
    llm_summary = single_file_report.get("llm_summary", {})
    
    purpose = llm_summary.get("purpose", "No module intent found.")
    api_surface = llm_summary.get("api_surface", {})
    guidance = llm_summary.get("ai_guidance", [])
    entry_chains = llm_summary.get("entry_chains", [])
    git_ctx = llm_summary.get("git_context", {})

    content = f"""# Module Context Bundle: `{module_id}`
Generated: {datetime.now().isoformat()}

## Module Intent
{purpose}

## AI Architectural Guidance
"""
    for hint in guidance:
        content += f"- {hint}\n"

    content += f"""
## Git Context
{_format_git_context(git_ctx)}

## Execution Chains (Entry points)
"""
    if entry_chains:
        for chain in entry_chains:
            content += f"- `{chain}`\n"
    else:
        content += "_No direct path from known entry points found._\n"

    content += f"""
## Public API Surface
{_format_api_surface(api_surface)}

## Dependencies & Impact
- **Direct Dependents:** {len(llm_summary.get("direct_dependents", []))}
- **Transitive Blast Radius:** {len(llm_summary.get("transitive_dependents", []))}
- **Impact Depth:** {llm_summary.get("impact_depth", 0)}

---
_Note: This is a compressed LLM bundle. Refer to `single_{module_id}.json` for full semantic and graph details._
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

__all__ = ["generate_llm_markdown"]

"""Fail-closed full-analysis reuse selection for canonical module usage facts."""

from pathlib import Path
from typing import Any

from contextor.core.analysis.state_manager import module_current_truth
from contextor.core.domain.usage_facts import (
    MODULE_USAGE_FACTS_SEMANTIC_VERSION,
    ModuleUsageFacts,
)
from contextor.core.reference.engine import extract_module_usage_facts


def _path(module: Any) -> str:
    return str(Path(module.absolute_path).resolve())


def build_module_usage_baseline_with_reuse(
    modules: dict[str, Any],
    previous_state: Any | None,
    current_file_state_manager: Any | None,
) -> tuple[dict[str, ModuleUsageFacts], dict[str, dict[str, str]]]:
    """Merge only independently proven current facts; otherwise extract per module.

    Global trust failure intentionally delegates the complete domain to the
    existing authoritative primitive, preserving its callers and semantics.
    """
    from contextor.core.reference.engine import _build_module_usage_baseline

    if (
        previous_state is None
        or current_file_state_manager is None
        or getattr(previous_state, "resync_required", False)
        or not isinstance(getattr(previous_state, "module_usages", None), dict)
        or not isinstance(getattr(previous_state, "module_usages_manifest", None), dict)
    ):
        facts = _build_module_usage_baseline(modules)
        return facts, _manifest_for(modules, facts, current_file_state_manager)

    previous_usages = previous_state.module_usages
    previous_manifest = previous_state.module_usages_manifest
    if (
        set(previous_usages) != set(previous_state.modules)
        or set(previous_manifest) != set(previous_state.modules)
        or any(
            not isinstance(entry, dict)
            or entry.get("semantic_version") != MODULE_USAGE_FACTS_SEMANTIC_VERSION
            for entry in previous_manifest.values()
        )
    ):
        facts = _build_module_usage_baseline(modules)
        return facts, _manifest_for(modules, facts, current_file_state_manager)

    facts: dict[str, ModuleUsageFacts] = {}
    manifest: dict[str, dict[str, str]] = {}
    for module_id, module in modules.items():
        source_path = _path(module)
        current = current_file_state_manager._state.get(source_path)
        old = previous_usages.get(module_id)
        entry = previous_manifest.get(module_id)
        truth = module_current_truth(previous_state, module_id)
        reusable = (
            isinstance(old, ModuleUsageFacts)
            and bool(getattr(old, "symbol_calls_materialized", False))
            and bool(getattr(old, "reference_evidence_materialized", False))
            and truth.get("available") is True
            and truth.get("state") == "fresh"
            and isinstance(entry, dict)
            and entry.get("semantic_version") == MODULE_USAGE_FACTS_SEMANTIC_VERSION
            and entry.get("path") == source_path
            and bool(current and current.sha256)
            and entry.get("sha256") == current.sha256
        )
        if not reusable:
            old = extract_module_usage_facts(module_id, module.ast_tree, imports=module.imports)
        facts[module_id] = old
        manifest[module_id] = {
            "module_id": module_id,
            "path": source_path,
            "sha256": current.sha256 if current else "",
            "semantic_version": MODULE_USAGE_FACTS_SEMANTIC_VERSION,
        }
    return facts, manifest


def _manifest_for(modules, facts, manager):
    return {
        module_id: {
            "module_id": module_id,
            "path": _path(module),
            "sha256": getattr(manager._state.get(_path(module)), "sha256", "") if manager else "",
            "semantic_version": MODULE_USAGE_FACTS_SEMANTIC_VERSION,
        }
        for module_id, module in modules.items()
    }

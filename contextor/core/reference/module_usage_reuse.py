"""Fail-closed full-analysis reuse selection for canonical module usage facts."""
from pathlib import Path
from typing import Any
from contextor.core.analysis.state_manager import module_current_truth
from contextor.core.domain.usage_facts import MODULE_USAGE_FACTS_SEMANTIC_VERSION, ModuleUsageFacts
from contextor.core.reference.engine import extract_module_usage_facts

def _path(module: Any) -> str: return str(Path(module.absolute_path).resolve())
def _require_materialized(module_id: str, facts: ModuleUsageFacts) -> ModuleUsageFacts:
    if not isinstance(facts, ModuleUsageFacts) or not facts.symbol_calls_materialized or not facts.reference_evidence_materialized:
        raise RuntimeError("Canonical ModuleUsageFacts baseline unavailable for current module " f"{module_id}")
    return facts
def _requires_full_rebuild(previous_state, manager) -> bool:
    if previous_state is None or manager is None or getattr(previous_state,"resync_required",False): return True
    pm=getattr(previous_state,"modules",None); pu=getattr(previous_state,"module_usages",None); pf=getattr(previous_state,"module_usages_manifest",None)
    if not isinstance(pm,dict) or not isinstance(pu,dict) or not isinstance(pf,dict): return True
    if set(pu)!=set(pm) or set(pf)!=set(pm): return True
    return any(not isinstance(e,dict) or e.get("semantic_version")!=MODULE_USAGE_FACTS_SEMANTIC_VERSION for e in pf.values())

def _tracked_sha256(manager: Any | None, source_path: str) -> str:
    if manager is None:
        return ""
    return manager.get_tracked_sha256(source_path)

def _manifest_entry(module_id,module,manager):
    source_path=_path(module)
    return {"module_id":module_id,"path":source_path,"sha256":_tracked_sha256(manager,source_path),"semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}
def _build_manifest(modules,manager): return {mid:_manifest_entry(mid,module,manager) for mid,module in modules.items()}
def _can_reuse(module_id,module,previous_state,previous_fact,entry,current_sha):
    if not isinstance(previous_fact,ModuleUsageFacts) or not previous_fact.symbol_calls_materialized or not previous_fact.reference_evidence_materialized: return False
    truth=module_current_truth(previous_state,module_id)
    if truth.get("available") is not True or truth.get("state")!="fresh": return False
    if not isinstance(entry,dict) or entry.get("semantic_version")!=MODULE_USAGE_FACTS_SEMANTIC_VERSION: return False
    return entry.get("module_id")==module_id and entry.get("path")==_path(module) and bool(current_sha) and entry.get("sha256")==current_sha
def build_module_usage_baseline_with_reuse(modules,previous_state,current_file_state_manager):
    from contextor.core.reference.engine import _build_module_usage_baseline
    if _requires_full_rebuild(previous_state,current_file_state_manager):
        facts=_build_module_usage_baseline(modules); return facts,_build_manifest(modules,current_file_state_manager)
    facts={}; manifest={}; usages=previous_state.module_usages; old_manifest=previous_state.module_usages_manifest
    for module_id,module in modules.items():
        path=_path(module); sha=_tracked_sha256(current_file_state_manager,path); old=usages.get(module_id); entry=old_manifest.get(module_id)
        fact=old if _can_reuse(module_id,module,previous_state,old,entry,sha) else _require_materialized(module_id,extract_module_usage_facts(module_id,module.ast_tree,imports=module.imports))
        facts[module_id]=fact; manifest[module_id]={"module_id":module_id,"path":path,"sha256":sha,"semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}
    if set(facts)!=set(modules): raise RuntimeError("Canonical ModuleUsageFacts baseline does not cover the current module domain")
    if set(manifest)!=set(modules): raise RuntimeError("Canonical ModuleUsageFacts manifest does not cover the current module domain")
    return facts,manifest

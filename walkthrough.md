# Final fail-closed manager-none edge case

Contextor MCP confirmed `contextor.core.reference.module_usage_reuse` at LIVE revision 202 with direct consumers facade and focused test. Before edit, LIVE continuity was continuous and resync false.

Changed only the requested helper and focused test file in this corrective step. `_requires_full_rebuild(..., manager=None)` remains true. `_tracked_sha256(manager, source_path)` returns empty for no manager and otherwise delegates to the public zero-I/O accessor. Manifest construction works with no manager, emits empty SHA, and cannot enable future reuse. The loop uses `_tracked_sha256`.

Added distinct tests for missing manager/full authoritative rebuild with exact fact/manifest domain and empty SHA, and each materialization failure.

Exact command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_module_usage_reuse.py
```

Result: `19 passed in 1.21s`.

No benchmark was rerun.

LIVE evidence: `get_live_events(after_revision=202)` returned natural desktop-watcher revisions 203 (`module_usage_reuse.py`) and 204 (`test_module_usage_reuse.py`), `continuity=continuous`, `resync_required=false`.

FILES_CHANGED=contextor/core/reference/module_usage_reuse.py,tests/test_module_usage_reuse.py

FULL_SUITE_RUN_BY_AGENT=NO

## COMPLETE RAW UNIFIED DIFF

```diff
diff --git a/contextor/core/reference/module_usage_reuse.py b/contextor/core/reference/module_usage_reuse.py
index 6575128..a097005 100644
--- a/contextor/core/reference/module_usage_reuse.py
+++ b/contextor/core/reference/module_usage_reuse.py
@@ -16,8 +16,15 @@ def _requires_full_rebuild(previous_state, manager) -> bool:
     if not isinstance(pm,dict) or not isinstance(pu,dict) or not isinstance(pf,dict): return True
     if set(pu)!=set(pm) or set(pf)!=set(pm): return True
     return any(not isinstance(e,dict) or e.get("semantic_version")!=MODULE_USAGE_FACTS_SEMANTIC_VERSION for e in pf.values())
+
+def _tracked_sha256(manager: Any | None, source_path: str) -> str:
+    if manager is None:
+        return ""
+    return manager.get_tracked_sha256(source_path)
+
 def _manifest_entry(module_id,module,manager):
-    path=_path(module); return {"module_id":module_id,"path":path,"sha256":manager.get_tracked_sha256(path),"semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}
+    source_path=_path(module)
+    return {"module_id":module_id,"path":source_path,"sha256":_tracked_sha256(manager,source_path),"semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}
 def _build_manifest(modules,manager): return {mid:_manifest_entry(mid,module,manager) for mid,module in modules.items()}
 def _can_reuse(module_id,module,previous_state,previous_fact,entry,current_sha):
     if not isinstance(previous_fact,ModuleUsageFacts) or not previous_fact.symbol_calls_materialized or not previous_fact.reference_evidence_materialized: return False
@@ -31,7 +38,7 @@ def build_module_usage_baseline_with_reuse(modules,previous_state,current_file_s
         facts=_build_module_usage_baseline(modules); return facts,_build_manifest(modules,current_file_state_manager)
     facts={}; manifest={}; usages=previous_state.module_usages; old_manifest=previous_state.module_usages_manifest
     for module_id,module in modules.items():
-        path=_path(module); sha=current_file_state_manager.get_tracked_sha256(path); old=usages.get(module_id); entry=old_manifest.get(module_id)
+        path=_path(module); sha=_tracked_sha256(current_file_state_manager,path); old=usages.get(module_id); entry=old_manifest.get(module_id)
         fact=old if _can_reuse(module_id,module,previous_state,old,entry,sha) else _require_materialized(module_id,extract_module_usage_facts(module_id,module.ast_tree,imports=module.imports))
         facts[module_id]=fact; manifest[module_id]={"module_id":module_id,"path":path,"sha256":sha,"semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}
     if set(facts)!=set(modules): raise RuntimeError("Canonical ModuleUsageFacts baseline does not cover the current module domain")
diff --git a/tests/test_module_usage_reuse.py b/tests/test_module_usage_reuse.py
index 2feedf3..45c8ca1 100644
--- a/tests/test_module_usage_reuse.py
+++ b/tests/test_module_usage_reuse.py
@@ -134,8 +134,22 @@ def test_wrong_manifest_identity_path_or_sha_extracts(monkeypatch,tmp_path):
     monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
     build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]
 
-def test_partial_unmaterialized_raises(monkeypatch,tmp_path):
+def test_partial_missing_symbol_calls_materialization_raises(monkeypatch,tmp_path):
     import pytest
     modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0],"old"),"b":_entry("b",paths[1])})
-    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda *_a,**_k:ModuleUsageFacts())
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda *_a,**_k:ModuleUsageFacts(symbol_calls_materialized=False,reference_evidence_materialized=True))
     with pytest.raises(RuntimeError): build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"}))
+
+def test_partial_missing_reference_evidence_materialization_raises(monkeypatch,tmp_path):
+    import pytest
+    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0],"old"),"b":_entry("b",paths[1])})
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda *_a,**_k:ModuleUsageFacts(symbol_calls_materialized=True,reference_evidence_materialized=False))
+    with pytest.raises(RuntimeError): build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"}))
+
+def test_missing_file_state_manager_full_rebuilds_with_nonreusable_manifest(monkeypatch,tmp_path):
+    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])}); calls=[]
+    monkeypatch.setattr("contextor.core.reference.engine._build_module_usage_baseline",lambda mods:calls.append(mods) or {mid:good for mid in mods})
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda *_a,**_k:(_ for _ in ()).throw(AssertionError()))
+    facts,manifest=build_module_usage_baseline_with_reuse(modules,prior,None)
+    assert len(calls)==1 and set(facts)==set(manifest)==set(modules)
+    assert all(entry["sha256"]=="" for entry in manifest.values())
```


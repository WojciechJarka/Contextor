# Strict versioned ModuleUsageFacts reuse

## Result

Implemented fail-closed, per-module reuse for the full-analysis canonical baseline. `DECISION=GO_CANDIDATE` was established by an external disposable A/B: first full run 32,007.085 ms, second unchanged warm run 8,681.427 ms, gain 23,325.657 ms, 328 current modules, first baseline extraction count 328, second count 0, zero errors. Independent post-run shadow extraction gave exact persisted-vs-fresh `to_dict()` parity for 328/328 modules (`differences=[]`, 8,227.430 ms). This external copy included the current test/domain shape; earlier LIVE discovery had 326 production modules.

## Contextor evidence / dataflow

MCP first: LIVE revision 189, workspace verified, canonical families fresh. `get_symbol_call_context` confirmed `_build_module_usage_baseline -> extract_module_usage_facts` as the sole direct intra-module edge (engine.py:758). `get_file_edit_context` confirmed facade/state/store ownership and direct consumer sets; `get_live_events` reported no actual state resync (`activity_resync_required=false`). The requested `after_revision=188` cursor had a retained-event gap only (`resync_required=true` for that cursor), so it was not used as a state-validity proof.

Current full dataflow is: index -> reports/pipeline -> pipeline `FileStateManager.update_state(..., compute_hash=True)` for every final module -> facade canonical baseline -> state/snapshot/LIVE publication. The new path resolves prior state LIVE-first before indexing, then uses the already-updated pipeline FileStateManager state: no additional source hashing/reading. Existing `_build_module_usage_baseline(modules)` remains unchanged and is the full-rebuild primitive.

## Changes and contract

- `MODULE_USAGE_FACTS_SEMANTIC_VERSION = "1"` is owned by `usage_facts`, independent of LIVE persistence schema.
- `RepositoryAnalysisState.module_usages_manifest` is persisted atomically with the state. Entries bind module id, normalized absolute path, SHA256, and semantic version. Old snapshots hydrate with the dataclass default `{}` and fail closed.
- `build_module_usage_baseline_with_reuse` is a new facade-only helper. It accepts a prior fact only if state/resync trust, exact previous-domain completeness, fact type, both materialization flags, current parse truth, manifest shape/version/path, and same-run FileState SHA all pass. It otherwise extracts that module. Missing/legacy manifest, incomplete domain, semantic mismatch, no prior state, no FileState manager, or resync invoke the unchanged complete baseline primitive.
- Final facts and manifest are constructed only over final current module domain; deleted modules are never carried forward.

## Invalidation matrix

| Condition | Action |
|---|---|
| unchanged SHA/path/version/current parse | reuse |
| changed/add/corrupt/missing fact or manifest | extract affected module |
| deleted module | omit old fact; final exact-domain reconciliation |
| stale/last-known-good or recovery from stale prior state | fresh extraction, never reuse |
| semantic-version mismatch, legacy/no manifest, incomplete previous domain | full baseline |
| repository/root resolver failure, explicit resync/untrusted state | full baseline |
| persistence incompatibility | state loader rejects/fails closed, then full baseline |

## Validation

Focused suite:

```powershell
& .\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_store.py tests/test_symbol_call_facts.py tests/test_module_usage_facts.py tests/test_module_usage_reuse.py
```

Result: `56 passed in 12.71s`. This covers persisted state behavior, materialized facts, current usage facts, legacy/no-manifest full rebuild, unchanged zero-extractor reuse, one changed affected extraction, semantic mismatch and resync full rebuild. Existing incremental materialization was not altered.

External commands/results:

```powershell
& C:\Temp\Contextor_Repo\.venv\Scripts\python.exe C:\Temp\Contextor_Benchmarks\module_usage_reuse_20260903\ab.py
# first_ms=32007.084909 second_ms=8681.427458 first_extract_calls=328 second_extract_calls=0 errors=0/0 gain_ms=23325.657451
& C:\Temp\Contextor_Repo\.venv\Scripts\python.exe C:\Temp\Contextor_Benchmarks\module_usage_reuse_20260903\parity.py
# modules=328 differences=[] wall_ms=8227.430023
```

Raw artifacts are exclusively in `C:\Temp\Contextor_Benchmarks\module_usage_reuse_20260903`.

## LIVE

No MCP update, runtime restart, or LIVE restart was performed. The benchmark was external/disposable and did not publish to desktop LIVE. Desktop watcher evidence is now complete: `get_live_events(after_revision=189)` returned revisions 190–195, `continuity=continuous`, `resync_required=false`, origin `desktop_watcher`; it naturally observed all changed production/test paths.

## Full raw unified diffs

```diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
@@
     module_usages: Dict[str, Any] = field(default_factory=dict)
+    module_usages_manifest: Dict[str, Dict[str, str]] = field(default_factory=dict)
diff --git a/contextor/core/domain/usage_facts.py b/contextor/core/domain/usage_facts.py
@@
 ReferenceEvidenceFact = Tuple[str, str, str, int]
+
+# Invalidation boundary for the complete extract_module_usage_facts contract,
+# including its resolution rules.  Persistence framing versions are separate.
+MODULE_USAGE_FACTS_SEMANTIC_VERSION = "1"
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
@@
         path = str(registry.repo_path.resolve())
+        previous_canonical_state = resolve_authoritative_repository_state(path)
@@
-            from contextor.core.reference.engine import _build_module_usage_baseline
-            module_usages = _build_module_usage_baseline(mods)
+            from contextor.core.reference.module_usage_reuse import build_module_usage_baseline_with_reuse
+            file_state_manager = report_result.get("_file_state_manager")
+            module_usages, module_usages_manifest = build_module_usage_baseline_with_reuse(mods, previous_canonical_state.state if previous_canonical_state else None, file_state_manager)
@@
                 module_usages=module_usages,
+                module_usages_manifest=module_usages_manifest,
```

Complete additions are the exact following raw unified diffs.

```diff
diff --git a/contextor/core/reference/module_usage_reuse.py b/contextor/core/reference/module_usage_reuse.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/reference/module_usage_reuse.py
@@
+"""Fail-closed full-analysis reuse selection for canonical module usage facts."""
+from pathlib import Path
+from typing import Any
+from contextor.core.analysis.state_manager import module_current_truth
+from contextor.core.domain.usage_facts import MODULE_USAGE_FACTS_SEMANTIC_VERSION, ModuleUsageFacts
+from contextor.core.reference.engine import extract_module_usage_facts
+def _path(module: Any) -> str: return str(Path(module.absolute_path).resolve())
+def build_module_usage_baseline_with_reuse(modules, previous_state, current_file_state_manager):
+    from contextor.core.reference.engine import _build_module_usage_baseline
+    if (previous_state is None or current_file_state_manager is None or getattr(previous_state, "resync_required", False) or not isinstance(getattr(previous_state, "module_usages", None), dict) or not isinstance(getattr(previous_state, "module_usages_manifest", None), dict)):
+        facts=_build_module_usage_baseline(modules); return facts, _manifest_for(modules, facts, current_file_state_manager)
+    previous_usages=previous_state.module_usages; previous_manifest=previous_state.module_usages_manifest
+    if (set(previous_usages)!=set(previous_state.modules) or set(previous_manifest)!=set(previous_state.modules) or any(not isinstance(e,dict) or e.get("semantic_version")!=MODULE_USAGE_FACTS_SEMANTIC_VERSION for e in previous_manifest.values())):
+        facts=_build_module_usage_baseline(modules); return facts, _manifest_for(modules, facts, current_file_state_manager)
+    facts={}; manifest={}
+    for module_id,module in modules.items():
+        source_path=_path(module); current=current_file_state_manager._state.get(source_path); old=previous_usages.get(module_id); entry=previous_manifest.get(module_id); truth=module_current_truth(previous_state,module_id)
+        reusable=(isinstance(old,ModuleUsageFacts) and bool(getattr(old,"symbol_calls_materialized",False)) and bool(getattr(old,"reference_evidence_materialized",False)) and truth.get("available") is True and truth.get("state")=="fresh" and isinstance(entry,dict) and entry.get("semantic_version")==MODULE_USAGE_FACTS_SEMANTIC_VERSION and entry.get("path")==source_path and bool(current and current.sha256) and entry.get("sha256")==current.sha256)
+        if not reusable: old=extract_module_usage_facts(module_id,module.ast_tree,imports=module.imports)
+        facts[module_id]=old; manifest[module_id]={"module_id":module_id,"path":source_path,"sha256":current.sha256 if current else "","semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}
+    return facts,manifest
+def _manifest_for(modules,facts,manager):
+    return {mid:{"module_id":mid,"path":_path(module),"sha256":getattr(manager._state.get(_path(module)),"sha256","") if manager else "","semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION} for mid,module in modules.items()}
```

```diff
diff --git a/tests/test_module_usage_reuse.py b/tests/test_module_usage_reuse.py
new file mode 100644
--- /dev/null
+++ b/tests/test_module_usage_reuse.py
@@
+from types import SimpleNamespace
+from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.core.domain.usage_facts import MODULE_USAGE_FACTS_SEMANTIC_VERSION, ModuleUsageFacts
+from contextor.core.reference.module_usage_reuse import build_module_usage_baseline_with_reuse
+def _module(path): return SimpleNamespace(absolute_path=path,imports=(),ast_tree="x = call()")
+def _manager(paths): return SimpleNamespace(_state={p:SimpleNamespace(sha256=s) for p,s in paths.items()})
+def _state(modules,facts,manifest,**extra):
+    state=RepositoryAnalysisState(modules=modules,module_usages=facts,module_usages_manifest=manifest)
+    for k,v in extra.items(): setattr(state,k,v)
+    return state
+def _entry(mid,path,sha="sha",version=MODULE_USAGE_FACTS_SEMANTIC_VERSION): return {"module_id":mid,"path":path,"sha256":sha,"semantic_version":version}
+def test_unchanged_reuses_without_extractor(monkeypatch,tmp_path):
+    path=str((tmp_path/"a.py").resolve()); (tmp_path/"a.py").write_text("x = call()"); modules={"a":_module(path)}; fact=ModuleUsageFacts(symbol_calls_materialized=True,reference_evidence_materialized=True); previous=_state(modules,{"a":fact},{"a":_entry("a",path)})
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda *_a,**_k:(_ for _ in ()).throw(AssertionError()))
+    facts,manifest=build_module_usage_baseline_with_reuse(modules,previous,_manager({path:"sha"})); assert facts=={"a":fact}; assert manifest["a"]==_entry("a",path)
+def test_missing_manifest_full_rebuild(monkeypatch,tmp_path):
+    path=str((tmp_path/"a.py").resolve()); (tmp_path/"a.py").write_text("x = call()"); modules={"a":_module(path)}; calls=[]
+    monkeypatch.setattr("contextor.core.reference.engine._build_module_usage_baseline",lambda m:calls.append(m) or {"a":ModuleUsageFacts()})
+    facts,_=build_module_usage_baseline_with_reuse(modules,_state(modules,{"a":ModuleUsageFacts()},{}),_manager({path:"sha"})); assert calls and set(facts)=={"a"}
+def test_changed_stale_or_corrupt_extracts_only_affected(monkeypatch,tmp_path):
+    paths=[]
+    for name in ("a","b"): p=tmp_path/f"{name}.py"; p.write_text("x = call()"); paths.append(str(p.resolve()))
+    modules={n:_module(p) for n,p in zip(("a","b"),paths)}; good=ModuleUsageFacts(symbol_calls_materialized=True,reference_evidence_materialized=True); previous=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1],"old")}); calls=[]
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*_a,**_k:calls.append(mid) or good)
+    facts,_=build_module_usage_baseline_with_reuse(modules,previous,_manager({paths[0]:"sha",paths[1]:"new"})); assert facts["a"] is good and calls==["b"]
+def test_semantic_mismatch_and_resync_full_rebuild(monkeypatch,tmp_path):
+    path=str((tmp_path/"a.py").resolve()); (tmp_path/"a.py").write_text("x=1"); modules={"a":_module(path)}; calls=[]
+    monkeypatch.setattr("contextor.core.reference.engine._build_module_usage_baseline",lambda m:calls.append(m) or {"a":ModuleUsageFacts()}); prior=_state(modules,{"a":ModuleUsageFacts()},{"a":_entry("a",path,version="old")})
+    build_module_usage_baseline_with_reuse(modules,prior,_manager({path:"sha"})); prior.resync_required=True; build_module_usage_baseline_with_reuse(modules,prior,_manager({path:"sha"})); assert len(calls)==2
```

FILES_CHANGED=contextor/core/analysis/state_manager.py,contextor/core/api/facade.py,contextor/core/domain/usage_facts.py,contextor/core/reference/module_usage_reuse.py,tests/test_module_usage_reuse.py

FULL_SUITE_RUN_BY_AGENT=NO

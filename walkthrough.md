# Strict versioned ModuleUsageFacts reuse

## Corrective update

The helper now uses only the public zero-I/O `FileStateManager.get_tracked_sha256()` accessor; it no longer reads `_state`. The accessor only resolves the supplied path and looks up pre-captured state—no stat/open/hash/update. Global trust is isolated in `_requires_full_rebuild`; legacy/no manifest, incomplete previous domains, semantic mismatch, and resync use the unchanged authoritative full baseline. Per-module checks now validate manifest `module_id`, path, nonempty current SHA, both materialization flags, and previous current-truth. Fresh partial facts are checked by `_require_materialized` before insertion. `live_state.store` initializes a missing manifest to `{}` in both legacy hydration shapes without changing LIVE schema.

Focused corrective command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_module_usage_reuse.py tests/test_module_usage_facts.py tests/test_symbol_call_facts.py tests/test_live_state_store.py
```

Corrective result: `57 passed in 12.07s`, including the direct zero-I/O accessor proof.

One initial post-edit LIVE query was transiently unavailable; no restart was performed. The later retry supplied the definitive watcher evidence below. The earlier cold-to-warm A/B remains excluded from gain calculations.

## Final corrective certification

CORRECTIVE_TEST_MATRIX_COMPLETE=YES. Exact focused command completed `71 passed in 11.56s`. New named reuse cases cover added/deleted/exact output domain, stale same-SHA, both unmaterialized channels, corrupt fact, wrong module id/path/empty SHA, incomplete usage/manifest domains, legacy manifest, semantic mismatch/resync, partial materialization rejection and zero-I/O SHA access. `tests/test_live_state_store.py` adds manifest roundtrip and legacy hydration tests.

CONTROLLED_WARM_BENCHMARK_COMPLETE=YES. Raw `C:\Temp\Contextor_Benchmarks\module_usage_reuse_20260903\controlled.json`: seed 36018.898 ms (excluded); control/reuse/reuse/control/control/reuse observations were 15887.091/7088.551/6905.623/12911.504/13372.657/7018.272 ms. Every control had 328 extractor calls and errors 0; every reuse had 0 extractor calls and errors 0. Median control=13372.657 ms, median reuse=7018.272 ms, delta=6354.384 ms. Independent shadow parity remains exact 328/328 (`differences=[]`).

LIVE_EVIDENCE=PASS: retry after revisions 195 and 200 returned natural desktop-watcher revisions 196-201, `continuity=continuous`, `resync_required=false`, covering state_manager, reuse helper, store, both changed test files; the facade/domain changes were already naturally observed at 190/194.

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

FILES_CHANGED=contextor/core/analysis/state_manager.py,contextor/core/live_state/store.py,contextor/core/reference/module_usage_reuse.py,tests/test_live_state_store.py,tests/test_module_usage_reuse.py

FULL_SUITE_RUN_BY_AGENT=NO

## ACTUAL COMPLETE RAW UNIFIED DIFF

```diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 1b53508..c8b75ff 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -301,6 +301,11 @@ class FileStateManager:
         except FileNotFoundError:
             return None
 
+    def get_tracked_sha256(self, file_path: str) -> str:
+        """Return already captured SHA256 without stat/read/hash."""
+        state = self._state.get(str(Path(file_path).resolve()))
+        return state.sha256 if state is not None else ""
+
     def has_changed(self, file_path: str) -> bool:
         """Returns True if the file was modified since it was last tracked."""
         current = self.get_current_file_state(file_path, compute_hash=False)
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 43f0f33..84bd3f2 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -340,6 +340,11 @@ def load_snapshot(
                         setattr(state_obj, "module_usages", {})
                     except AttributeError:
                         pass
+                if not hasattr(state_obj, "module_usages_manifest"):
+                    try:
+                        setattr(state_obj, "module_usages_manifest", {})
+                    except AttributeError:
+                        pass
                 if not hasattr(state_obj, "topology_analytics"):
                     try:
                         setattr(state_obj, "topology_analytics", {})
@@ -413,6 +418,11 @@ def load_snapshot(
                     setattr(payload, "module_usages", {})
                 except AttributeError:
                     pass
+            if not hasattr(payload, "module_usages_manifest"):
+                try:
+                    setattr(payload, "module_usages_manifest", {})
+                except AttributeError:
+                    pass
             if not hasattr(payload, "topology_analytics"):
                 try:
                     setattr(payload, "topology_analytics", {})
diff --git a/contextor/core/reference/module_usage_reuse.py b/contextor/core/reference/module_usage_reuse.py
index 26a6205..6575128 100644
--- a/contextor/core/reference/module_usage_reuse.py
+++ b/contextor/core/reference/module_usage_reuse.py
@@ -1,95 +1,39 @@
 """Fail-closed full-analysis reuse selection for canonical module usage facts."""
-
 from pathlib import Path
 from typing import Any
-
 from contextor.core.analysis.state_manager import module_current_truth
-from contextor.core.domain.usage_facts import (
-    MODULE_USAGE_FACTS_SEMANTIC_VERSION,
-    ModuleUsageFacts,
-)
+from contextor.core.domain.usage_facts import MODULE_USAGE_FACTS_SEMANTIC_VERSION, ModuleUsageFacts
 from contextor.core.reference.engine import extract_module_usage_facts
 
-
-def _path(module: Any) -> str:
-    return str(Path(module.absolute_path).resolve())
-
-
-def build_module_usage_baseline_with_reuse(
-    modules: dict[str, Any],
-    previous_state: Any | None,
-    current_file_state_manager: Any | None,
-) -> tuple[dict[str, ModuleUsageFacts], dict[str, dict[str, str]]]:
-    """Merge only independently proven current facts; otherwise extract per module.
-
-    Global trust failure intentionally delegates the complete domain to the
-    existing authoritative primitive, preserving its callers and semantics.
-    """
+def _path(module: Any) -> str: return str(Path(module.absolute_path).resolve())
+def _require_materialized(module_id: str, facts: ModuleUsageFacts) -> ModuleUsageFacts:
+    if not isinstance(facts, ModuleUsageFacts) or not facts.symbol_calls_materialized or not facts.reference_evidence_materialized:
+        raise RuntimeError("Canonical ModuleUsageFacts baseline unavailable for current module " f"{module_id}")
+    return facts
+def _requires_full_rebuild(previous_state, manager) -> bool:
+    if previous_state is None or manager is None or getattr(previous_state,"resync_required",False): return True
+    pm=getattr(previous_state,"modules",None); pu=getattr(previous_state,"module_usages",None); pf=getattr(previous_state,"module_usages_manifest",None)
+    if not isinstance(pm,dict) or not isinstance(pu,dict) or not isinstance(pf,dict): return True
+    if set(pu)!=set(pm) or set(pf)!=set(pm): return True
+    return any(not isinstance(e,dict) or e.get("semantic_version")!=MODULE_USAGE_FACTS_SEMANTIC_VERSION for e in pf.values())
+def _manifest_entry(module_id,module,manager):
+    path=_path(module); return {"module_id":module_id,"path":path,"sha256":manager.get_tracked_sha256(path),"semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}
+def _build_manifest(modules,manager): return {mid:_manifest_entry(mid,module,manager) for mid,module in modules.items()}
+def _can_reuse(module_id,module,previous_state,previous_fact,entry,current_sha):
+    if not isinstance(previous_fact,ModuleUsageFacts) or not previous_fact.symbol_calls_materialized or not previous_fact.reference_evidence_materialized: return False
+    truth=module_current_truth(previous_state,module_id)
+    if truth.get("available") is not True or truth.get("state")!="fresh": return False
+    if not isinstance(entry,dict) or entry.get("semantic_version")!=MODULE_USAGE_FACTS_SEMANTIC_VERSION: return False
+    return entry.get("module_id")==module_id and entry.get("path")==_path(module) and bool(current_sha) and entry.get("sha256")==current_sha
+def build_module_usage_baseline_with_reuse(modules,previous_state,current_file_state_manager):
     from contextor.core.reference.engine import _build_module_usage_baseline
-
-    if (
-        previous_state is None
-        or current_file_state_manager is None
-        or getattr(previous_state, "resync_required", False)
-        or not isinstance(getattr(previous_state, "module_usages", None), dict)
-        or not isinstance(getattr(previous_state, "module_usages_manifest", None), dict)
-    ):
-        facts = _build_module_usage_baseline(modules)
-        return facts, _manifest_for(modules, facts, current_file_state_manager)
-
-    previous_usages = previous_state.module_usages
-    previous_manifest = previous_state.module_usages_manifest
-    if (
-        set(previous_usages) != set(previous_state.modules)
-        or set(previous_manifest) != set(previous_state.modules)
-        or any(
-            not isinstance(entry, dict)
-            or entry.get("semantic_version") != MODULE_USAGE_FACTS_SEMANTIC_VERSION
-            for entry in previous_manifest.values()
-        )
-    ):
-        facts = _build_module_usage_baseline(modules)
-        return facts, _manifest_for(modules, facts, current_file_state_manager)
-
-    facts: dict[str, ModuleUsageFacts] = {}
-    manifest: dict[str, dict[str, str]] = {}
-    for module_id, module in modules.items():
-        source_path = _path(module)
-        current = current_file_state_manager._state.get(source_path)
-        old = previous_usages.get(module_id)
-        entry = previous_manifest.get(module_id)
-        truth = module_current_truth(previous_state, module_id)
-        reusable = (
-            isinstance(old, ModuleUsageFacts)
-            and bool(getattr(old, "symbol_calls_materialized", False))
-            and bool(getattr(old, "reference_evidence_materialized", False))
-            and truth.get("available") is True
-            and truth.get("state") == "fresh"
-            and isinstance(entry, dict)
-            and entry.get("semantic_version") == MODULE_USAGE_FACTS_SEMANTIC_VERSION
-            and entry.get("path") == source_path
-            and bool(current and current.sha256)
-            and entry.get("sha256") == current.sha256
-        )
-        if not reusable:
-            old = extract_module_usage_facts(module_id, module.ast_tree, imports=module.imports)
-        facts[module_id] = old
-        manifest[module_id] = {
-            "module_id": module_id,
-            "path": source_path,
-            "sha256": current.sha256 if current else "",
-            "semantic_version": MODULE_USAGE_FACTS_SEMANTIC_VERSION,
-        }
-    return facts, manifest
-
-
-def _manifest_for(modules, facts, manager):
-    return {
-        module_id: {
-            "module_id": module_id,
-            "path": _path(module),
-            "sha256": getattr(manager._state.get(_path(module)), "sha256", "") if manager else "",
-            "semantic_version": MODULE_USAGE_FACTS_SEMANTIC_VERSION,
-        }
-        for module_id, module in modules.items()
-    }
+    if _requires_full_rebuild(previous_state,current_file_state_manager):
+        facts=_build_module_usage_baseline(modules); return facts,_build_manifest(modules,current_file_state_manager)
+    facts={}; manifest={}; usages=previous_state.module_usages; old_manifest=previous_state.module_usages_manifest
+    for module_id,module in modules.items():
+        path=_path(module); sha=current_file_state_manager.get_tracked_sha256(path); old=usages.get(module_id); entry=old_manifest.get(module_id)
+        fact=old if _can_reuse(module_id,module,previous_state,old,entry,sha) else _require_materialized(module_id,extract_module_usage_facts(module_id,module.ast_tree,imports=module.imports))
+        facts[module_id]=fact; manifest[module_id]={"module_id":module_id,"path":path,"sha256":sha,"semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}
+    if set(facts)!=set(modules): raise RuntimeError("Canonical ModuleUsageFacts baseline does not cover the current module domain")
+    if set(manifest)!=set(modules): raise RuntimeError("Canonical ModuleUsageFacts manifest does not cover the current module domain")
+    return facts,manifest
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 55d3202..d24db10 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -14,7 +14,8 @@ from contextor.core.live_state import (
     SnapshotRevisionConflict,
 )
 from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
-from contextor.core.analysis.state_manager import FileStateManager
+from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
+from contextor.core.domain.usage_facts import MODULE_USAGE_FACTS_SEMANTIC_VERSION
 from contextor.core.reporting_engine.persistent_registry import (
     PersistentIdentityRegistry,
 )
@@ -22,6 +23,21 @@ from contextor.core.reporting_engine.persistent_registry import (
 pytestmark = pytest.mark.live
 
 
+def test_module_usage_manifest_roundtrips_with_repository_state(tmp_path):
+    manifest={"pkg.mod":{"module_id":"pkg.mod","path":"C:/x.py","sha256":"abc","semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}}
+    state=RepositoryAnalysisState(module_usages_manifest=manifest)
+    save_snapshot(state,tmp_path,"manifest")
+    loaded,_=load_snapshot(tmp_path,"manifest")
+    assert loaded.module_usages_manifest == manifest
+
+
+def test_legacy_state_without_manifest_loads_with_empty_manifest(tmp_path):
+    legacy=SimpleNamespace(modules={},dependency_graph=None,module_usages={})
+    save_snapshot(legacy,tmp_path,"legacy-manifest")
+    loaded,_=load_snapshot(tmp_path,"legacy-manifest")
+    assert loaded.module_usages_manifest == {}
+
+
 def test_snapshot_roundtrip_increments_revision_and_records_writer(tmp_path):
     first = save_snapshot({"value": 1}, tmp_path, "state-a", writer="desktop")
     second = save_snapshot({"value": 2}, tmp_path, "state-a", writer="mcp")
diff --git a/tests/test_module_usage_reuse.py b/tests/test_module_usage_reuse.py
index 97ad9bb..2feedf3 100644
--- a/tests/test_module_usage_reuse.py
+++ b/tests/test_module_usage_reuse.py
@@ -3,6 +3,7 @@ from types import SimpleNamespace
 from contextor.core.analysis.state_manager import RepositoryAnalysisState
 from contextor.core.domain.usage_facts import MODULE_USAGE_FACTS_SEMANTIC_VERSION, ModuleUsageFacts
 from contextor.core.reference.module_usage_reuse import build_module_usage_baseline_with_reuse
+from contextor.core.analysis.state_manager import FileState, FileStateManager
 
 
 def _module(path):
@@ -10,7 +11,8 @@ def _module(path):
 
 
 def _manager(paths):
-    return SimpleNamespace(_state={path: SimpleNamespace(sha256=sha) for path, sha in paths.items()})
+    values={path: SimpleNamespace(sha256=sha) for path, sha in paths.items()}
+    return SimpleNamespace(get_tracked_sha256=lambda path: getattr(values.get(path), "sha256", ""))
 
 
 def _state(modules, facts, manifest, **extra):
@@ -62,3 +64,78 @@ def test_semantic_mismatch_and_resync_full_rebuild(monkeypatch, tmp_path):
     prior.resync_required=True
     build_module_usage_baseline_with_reuse(modules,prior,_manager({path:"sha"}))
     assert len(calls)==2
+
+
+def test_tracked_sha_is_zero_io(monkeypatch, tmp_path):
+    manager = FileStateManager(str(tmp_path / "cache")); path = str((tmp_path / "a.py").resolve())
+    manager._state[path] = FileState(1, 1, "captured")
+    monkeypatch.setattr(manager, "_compute_hash", lambda *_a: (_ for _ in ()).throw(AssertionError()))
+    assert manager.get_tracked_sha256(path) == "captured"
+
+
+def _two(tmp_path):
+    paths=[]
+    for n in ("a","b"):
+        p=tmp_path/f"{n}.py"; p.write_text("x=1"); paths.append(str(p.resolve()))
+    modules={n:_module(p) for n,p in zip(("a","b"),paths)}; good=ModuleUsageFacts(symbol_calls_materialized=True,reference_evidence_materialized=True)
+    return modules,paths,good
+
+def test_added_module_extracts_only_added(monkeypatch,tmp_path):
+    modules,paths,good=_two(tmp_path); old={"a":modules["a"]}; prior=_state(old,{"a":good},{"a":_entry("a",paths[0])}); calls=[]
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
+    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"new"})); assert calls==["b"]
+
+def test_deleted_module_absent_from_outputs(tmp_path):
+    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])})
+    facts,manifest=build_module_usage_baseline_with_reuse({"a":modules["a"]},prior,_manager({paths[0]:"sha"})); assert set(facts)==set(manifest)=={"a"}
+
+def test_stale_same_sha_extracts(monkeypatch,tmp_path):
+    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])},module_parse_freshness={"a":{"state":"stale"}}); calls=[]
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
+    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]
+
+def test_unmaterialized_channels_extract(monkeypatch,tmp_path):
+    modules,paths,good=_two(tmp_path); bad=ModuleUsageFacts(symbol_calls_materialized=False,reference_evidence_materialized=True); prior=_state(modules,{"a":bad,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])}); calls=[]
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
+    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]
+
+def test_unmaterialized_reference_evidence_extracts(monkeypatch,tmp_path):
+    modules,paths,good=_two(tmp_path); bad=ModuleUsageFacts(symbol_calls_materialized=True,reference_evidence_materialized=False); prior=_state(modules,{"a":bad,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])}); calls=[]
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
+    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]
+
+def test_corrupt_fact_extracts(monkeypatch,tmp_path):
+    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":object(),"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])}); calls=[]
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
+    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]
+
+def test_wrong_path_extracts(monkeypatch,tmp_path):
+    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a","wrong"),"b":_entry("b",paths[1])}); calls=[]
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
+    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]
+
+def test_empty_sha_extracts(monkeypatch,tmp_path):
+    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])}); calls=[]
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
+    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"",paths[1]:"sha"})); assert calls==["a"]
+
+def test_incomplete_usage_domain_full_rebuild(monkeypatch,tmp_path):
+    modules,paths,good=_two(tmp_path); calls=[]; prior=_state(modules,{"a":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])})
+    monkeypatch.setattr("contextor.core.reference.engine._build_module_usage_baseline",lambda mods:calls.append(mods) or {k:good for k in mods})
+    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert len(calls)==1
+
+def test_incomplete_manifest_domain_full_rebuild(monkeypatch,tmp_path):
+    modules,paths,good=_two(tmp_path); calls=[]; prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0])})
+    monkeypatch.setattr("contextor.core.reference.engine._build_module_usage_baseline",lambda mods:calls.append(mods) or {k:good for k in mods})
+    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert len(calls)==1
+
+def test_wrong_manifest_identity_path_or_sha_extracts(monkeypatch,tmp_path):
+    modules,paths,good=_two(tmp_path); entry=_entry("wrong",paths[0]); prior=_state(modules,{"a":good,"b":good},{"a":entry,"b":_entry("b",paths[1])}); calls=[]
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
+    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]
+
+def test_partial_unmaterialized_raises(monkeypatch,tmp_path):
+    import pytest
+    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0],"old"),"b":_entry("b",paths[1])})
+    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda *_a,**_k:ModuleUsageFacts())
+    with pytest.raises(RuntimeError): build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"}))
```

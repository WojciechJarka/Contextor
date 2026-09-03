# Full usage-walk fusion — final report

Date: 2026-09-03  
Repository: `C:\Temp\Contextor_Repo`  
Benchmark root: `C:\Temp\Contextor_Benchmarks\full_usage_walk_fusion_20260903`

## Result

`PASS`

The six full `ast.walk(tree)` traversals in `contextor.core.reference.engine.extract_module_usage_facts` were fused into exactly one full-tree traversal per module. The public signature, `ModuleUsageFacts` schema, `SymbolReferenceVisitor`, `visitor.visit(tree)`, canonical identities, `symbol_calls`, `reference_evidence`, imports, aliases, sorting/deduplication, `None`/string/SyntaxError fallbacks, channel semantics, `_attribute_name`, and nested `ast.walk(node.func)` remain intact.

Exact old-vs-new parity passed for all 326 current canonical modules on an identical source snapshot/domain. Healthy warm full-analysis wall fell from `22,155.731` to `17,506.861 ms` (`-4,648.870 ms`, `-20.98%`). `_build_module_usage_baseline` fell from `15,917.523` to `8,764.803 ms` (`-44.94%`); extractor wall from `13,347.658` to `6,435.455 ms` (`-51.79%`); full-tree walks from 1,956 to 326 and `6,744.978` to `1,154.052 ms`.

## Contextor MCP architectural evidence

Contextor MCP was used before editing.

- Owner: `contextor.core.reference.engine::extract_module_usage_facts`, module ID `71/1`, kind `function`.
- Pre-edit freshness: `workspace_sync=verified`, canonical revision 182, provenance live; module/graph/topology/artifact-consumption/cycles/collisions fresh.
- Canonical direct intra-module call edge: `_build_module_usage_baseline -> extract_module_usage_facts` at old line 772.
- Static direct consumers (9, untruncated): `contextor.core.analysis.incremental.materialization`, `contextor.core.analysis.incremental.preparation`, `tests.test_cached_target_resolution`, `tests.test_canonical_reference_projection`, `tests.test_completeness_freshness_parity_proof`, `tests.test_incremental_artifact_consumption`, `tests.test_module_usage_facts`, `tests.test_parity_and_freshness_proof`, `tests.test_symbol_call_facts`.
- File edit context: 16 direct module consumers, 133 transitive consumers, risk 0.1891, 83 covering tests, zero layer-boundary violations.
- Dataflow: full analysis `_build_module_usage_baseline(modules)` calls the extractor once per current module AST/import list; results populate canonical `RepositoryAnalysisState.module_usages`, then persistence/LIVE and incremental/query consumers.
- Post-edit preview: lines 543-750, `workspace_sync=verified`, canonical revision 186, provenance live, all canonical families fresh, no warning.

Exact MCP calls:

```text
mcp__contextor__get_mcp_documentation(tools=[get_file_edit_context,get_symbol_call_context,get_symbol_implementation,get_live_events,search_source], sections=[purpose,parameters,behavior,freshness,usage_notes,examples])
mcp__contextor__get_file_edit_context(repo_path="C:\\Temp\\Contextor_Repo", target="contextor.core.reference.engine", mode="minimal", compact=true, max_items=30)
mcp__contextor__get_symbol_call_context(repo_path="C:\\Temp\\Contextor_Repo", symbol="contextor.core.reference.engine::extract_module_usage_facts", direction="both", depth=2, max_items=100, representation="named", allow_large_output=true)
mcp__contextor__get_symbol_implementation(repo_path="C:\\Temp\\Contextor_Repo", symbol="contextor.core.reference.engine::extract_module_usage_facts", mode="fetch", include=["implementation","static_context"])
mcp__contextor__search_artifacts(repo_path="C:\\Temp\\Contextor_Repo", search_term="extract_module_usage_facts", compact=false, limit=20, evidence_limit=50)
mcp__contextor__get_live_events(repo_path="C:\\Temp\\Contextor_Repo", after_revision=182, limit=20)
```

## Implementation and rationale

The original visitor-derived sets are initialized exactly as before. One full `ast.walk(tree)` now collects:

- `ast.Call`: direct `_attribute_name(node.func)`, constant-string runtime getattr, callback keyword values, bind/subscribe/on event argument, and `call_funcs`.
- `ast.ClassDef`: inheritance bases.
- `ast.Attribute`: qualified-reference candidates.

The existing nested `ast.walk(node.func)` is unchanged. After the single traversal, qualified candidates whose AST node identity belongs to `call_funcs` are excluded, then qualified-name strings are deduplicated and sorted exactly like the old `qual_refs` set. Final tuple construction and `symbol_calls`/`reference_evidence` logic are unchanged.

The focused test covers direct calls, runtime getattr, callbacks, events, inheritance, qualified refs, call-function exclusion, local symbol calls, reference evidence, and requires exactly one walk whose argument is the module root while preserving nested walks.

No compact facts, cache, persistence, canonical fields, API, MCP, or LIVE contracts changed.

## Exact parity evidence

Pre-edit capture:

```text
{"source": "live_service", "revision": 182, "module_count": 326, "elapsed_ms": 16657.51624800032}
```

The first comparison correctly returned `FAIL`: 171 modules differed because candidate `(node, qualified_name)` pairs did not yet deduplicate repeated qualified-name strings. Expected outputs were not changed. Production code was corrected to preserve the old set-based name deduplication, then the complete comparison was rerun.

Final raw result:

```text
{"old_revision": 182, "new_revision": 186, "old_module_count": 326, "new_module_count": 326, "same_domain": true, "identical_snapshot_hashes": true, "reconstructed_from_head": ["contextor.core.reference.engine", "tests.test_module_usage_facts"], "hash_mismatches": [], "differing_modules": [], "exact_parity": true, "elapsed_ms": 8603.928782002185}
```

Every module source SHA-256 had to match the pre-edit capture. The two edited files used original `HEAD` bytes whose hashes matched the captured old hashes; all other modules used matching disk bytes. Every serialized `ModuleUsageFacts.to_dict()` field compared exactly, 326/326 modules, zero differences.

```powershell
& 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe' -u 'C:\Temp\Contextor_Benchmarks\full_usage_walk_fusion_20260903\capture_usage.py' 'C:\Temp\Contextor_Benchmarks\full_usage_walk_fusion_20260903\old_usage.json'
& 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe' -u 'C:\Temp\Contextor_Benchmarks\full_usage_walk_fusion_20260903\compare_usage.py'
```

Artifacts: `old_usage.json`, `new_usage_same_snapshot.json`, `capture_usage.py`, `compare_usage.py` under the benchmark root.

## Focused tests

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q tests/test_module_usage_facts.py tests/test_symbol_call_facts.py tests/test_canonical_reference_projection.py
```

First run: `1 failed, 49 passed in 39.47s`. Only the new fixture's expected AST source line was 13 instead of actual 12; the fixture assertion was corrected. This was not a production parity difference and no old parity output changed.

Final raw result:

```text
..................................................                       [100%]
50 passed in 35.45s
```

Full pytest was not run.

## Healthy full-analysis benchmark

```powershell
$dest='C:\Temp\Contextor_Benchmarks\full_usage_walk_fusion_20260903\source'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
robocopy 'C:\Temp\Contextor_Repo' $dest /E /XD .git .venv output logs .pytest_cache __pycache__ /XF walkthrough.md *.pyc
& 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe' -u 'C:\Temp\Contextor_Benchmarks\full_usage_walk_fusion_20260903\profile_full.py'
```

Disposable source, isolated cache/state/output/registry, normal ProcessPool. LIVE connection returned no client only inside the harness.

Cold/warmup, separate:

```json
{"total_ms":33570.04235200293,"health":{"errors":0,"module_count":326,"result_present":true,"live_publish_status":"not_attempted"},"rows":{"parse_source":{"count":326,"wall_ms":2609.7229640727164},"nested_walk":{"count":56078,"wall_ms":807.7928034763318},"full_tree_walk":{"count":326,"wall_ms":1153.5442320891889},"extract_module_usage_facts":{"count":326,"wall_ms":6482.324788055848},"_build_module_usage_baseline":{"count":1,"wall_ms":9202.65983499121}}}
```

Accepted healthy warm seed:

```json
{"total_ms":17506.860578010674,"health":{"errors":0,"module_count":326,"result_present":true,"live_publish_status":"not_attempted"},"rows":{"parse_source":{"count":326,"wall_ms":2256.184863159433},"nested_walk":{"count":56078,"wall_ms":800.5766963033238},"full_tree_walk":{"count":326,"wall_ms":1154.0522027789848},"extract_module_usage_facts":{"count":326,"wall_ms":6435.454996040789},"_build_module_usage_baseline":{"count":1,"wall_ms":8764.802580000833}}}
```

| Metric | Before | After warm | Delta |
|---|---:|---:|---:|
| total wall | 22155.731 ms | 17506.861 ms | -4648.870 ms (-20.98%) |
| usage baseline | 15917.523 ms | 8764.803 ms | -7152.720 ms (-44.94%) |
| extractor | 13347.658 ms | 6435.455 ms | -6912.203 ms (-51.79%) |
| full-tree walks | 1956 / 6744.978 ms | 326 / 1154.052 ms | -1630 / -5590.926 ms |
| nested walks | 56090 / 875.828 ms | 56078 / 800.577 ms | algorithm retained; source changed |
| parse | 326 / 2282.081 ms | 326 / 2256.185 ms | count unchanged |

`full_tree_walk.count == module_count == 326`. Exact semantics come from the independent same-snapshot parity comparison.

Artifacts: `full_observation.json`, `profile_full.py`, disposable `source`, and isolated `runtime` under the benchmark root.

## LIVE evidence

No `update_file` call and no restart.

```text
revision=183 origin=desktop_watcher status=UPDATED   file=contextor/core/reference/engine.py
revision=184 origin=desktop_watcher status=UPDATED   file=tests/test_module_usage_facts.py
revision=185 origin=desktop_watcher status=UNCHANGED file=tests/test_module_usage_facts.py
revision=186 origin=desktop_watcher status=UPDATED   file=contextor/core/reference/engine.py
continuity=continuous
resync_required=false
resync_reason=null
latest_revision=186
```

Revision 185 followed a test-only expected-line correction with unchanged canonical structure. Final extractor freshness at revision 186 was verified.

## Exact textual verification

```powershell
rg -n "extract_module_usage_facts|symbol_calls_materialized|reference_evidence_materialized" tests contextor/core/reference/engine.py
rg -n "class ModuleUsageFacts|def to_dict" contextor/core/domain/usage_facts.py
Get-Content -LiteralPath tests/test_module_usage_facts.py | Select-Object -First 260
Get-Content -LiteralPath contextor/core/reference/engine.py | Select-Object -Skip 590 -First 170
git diff --check -- contextor/core/reference/engine.py tests/test_module_usage_facts.py
git diff -- contextor/core/reference/engine.py tests/test_module_usage_facts.py
```

`git diff --check` had no whitespace errors; only LF/CRLF advisory warnings.

## FILES_CHANGED

```text
contextor/core/reference/engine.py
tests/test_module_usage_facts.py
```

Walkthrough, logs and benchmark artifacts are excluded.

`FULL_SUITE_RUN_BY_AGENT=NO`

## COMPLETE raw unified diff

The complete raw unified diff of both changed production/test files follows.

```diff
diff --git a/contextor/core/reference/engine.py b/contextor/core/reference/engine.py
index 94c147e..0d9b1e3 100644
--- a/contextor/core/reference/engine.py
+++ b/contextor/core/reference/engine.py
@@ -618,33 +618,11 @@ def extract_module_usage_facts(
         for item in visitor.called
         if (item[0] if isinstance(item, tuple) else item) not in local_resolved_names
     )
-    for node in ast.walk(tree):
-        if isinstance(node, ast.Call):
-            from .resolution import _attribute_name
-            name = _attribute_name(node.func)
-            if name:
-                all_calls.add(name)
-
-    direct_calls = tuple(sorted(all_calls))
-
     dyn_calls = set(
         item[0] if isinstance(item, tuple) else item
         for item in visitor.called_ambiguous
         if (item[0] if isinstance(item, tuple) else item) not in local_resolved_names
     )
-    for node in ast.walk(tree):
-        if isinstance(node, ast.Call):
-            from .resolution import _attribute_name
-            name = _attribute_name(node.func)
-            if (
-                name == "getattr"
-                and len(node.args) >= 2
-                and isinstance(node.args[1], ast.Constant)
-                and isinstance(node.args[1].value, str)
-            ):
-                dyn_calls.add(node.args[1].value)
-
-    runtime_calls = tuple(sorted(dyn_calls))
     cb_set = set(
         item[0] if isinstance(item, tuple) else item
         for item in visitor.callback_called
@@ -654,38 +632,54 @@ def extract_module_usage_facts(
         for item in visitor.event_bound
     )
     callback_keys = {"command", "callback", "handler", "func", "on_click", "on_change", "on_submit"}
+    inh_set = set(
+        (item[0], item[1]) if len(item) >= 2 else (item[0], "")
+        for item in visitor.inherited
+    )
+    call_funcs = set()
+    qual_ref_candidates = set()
+    from .resolution import _attribute_name
+
     for node in ast.walk(tree):
         if isinstance(node, ast.Call):
-            from .resolution import _attribute_name
+            name = _attribute_name(node.func)
+            if name:
+                all_calls.add(name)
+            if (
+                name == "getattr"
+                and len(node.args) >= 2
+                and isinstance(node.args[1], ast.Constant)
+                and isinstance(node.args[1].value, str)
+            ):
+                dyn_calls.add(node.args[1].value)
             for kw in node.keywords:
                 if kw.arg in callback_keys:
-                    kn = _attribute_name(kw.value)
-                    if kn:
-                        cb_set.add(kn)
-            func_name = _attribute_name(node.func)
-            if func_name and func_name.rsplit(".", 1)[-1] in {"bind", "subscribe", "on"}:
+                    callback_name = _attribute_name(kw.value)
+                    if callback_name:
+                        cb_set.add(callback_name)
+            if name and name.rsplit(".", 1)[-1] in {"bind", "subscribe", "on"}:
                 if len(node.args) >= 1:
-                    arg_n = _attribute_name(node.args[-1])
-                    if arg_n:
-                        ev_set.add(arg_n)
+                    event_name = _attribute_name(node.args[-1])
+                    if event_name:
+                        ev_set.add(event_name)
+            for child in ast.walk(node.func):
+                if isinstance(child, ast.Attribute):
+                    call_funcs.add(child)
+        elif isinstance(node, ast.ClassDef):
+            for base in node.bases:
+                base_name = _attribute_name(base)
+                if base_name:
+                    inh_set.add((node.name, base_name))
+        elif isinstance(node, ast.Attribute):
+            qualified_name = _attribute_name(node)
+            if qualified_name and "." in qualified_name:
+                qual_ref_candidates.add((node, qualified_name))
 
+    direct_calls = tuple(sorted(all_calls))
+    runtime_calls = tuple(sorted(dyn_calls))
     callback_calls = tuple(sorted(cb_set))
     event_bindings = tuple(sorted(ev_set))
-
-    inh_set = set(
-        (item[0], item[1]) if len(item) >= 2 else (item[0], "")
-        for item in visitor.inherited
-    )
-    for node in ast.walk(tree):
-        if isinstance(node, ast.ClassDef):
-            from .resolution import _attribute_name
-            for base in node.bases:
-                b_name = _attribute_name(base)
-                if b_name:
-                    inh_set.add((node.name, b_name))
-
     inheritance_refs = tuple(sorted(inh_set))
-
     aliases = tuple(
         sorted(
             set(
@@ -695,23 +689,15 @@ def extract_module_usage_facts(
             )
         )
     )
-
-    call_funcs = set()
-    for node in ast.walk(tree):
-        if isinstance(node, ast.Call):
-            for child in ast.walk(node.func):
-                if isinstance(child, ast.Attribute):
-                    call_funcs.add(child)
-
-    qual_refs = set()
-    for node in ast.walk(tree):
-        if isinstance(node, ast.Attribute) and node not in call_funcs:
-            from .resolution import _attribute_name
-            name = _attribute_name(node)
-            if name and "." in name:
-                qual_refs.add(name)
-
-    qualified_refs = tuple(sorted(qual_refs))
+    qualified_refs = tuple(
+        sorted(
+            {
+                qualified_name
+                for node, qualified_name in qual_ref_candidates
+                if node not in call_funcs
+            }
+        )
+    )
 
     local_callees = {
         dotted: f"{module_path}::{local_name}"
```

```diff
diff --git a/tests/test_module_usage_facts.py b/tests/test_module_usage_facts.py
index 1c1e201..9cf6dbd 100644
--- a/tests/test_module_usage_facts.py
+++ b/tests/test_module_usage_facts.py
@@ -95,6 +95,57 @@ class Button(BaseWidget):
     assert "math.sqrt" in facts.direct_calls or "sqrt" in [a[0] for a in facts.aliases]
 
 
+def test_usage_extractor_fuses_full_tree_walk_without_changing_channels(monkeypatch):
+    tree = ast.parse(
+        '''
+import pkg.mod as pm
+
+class Child(pkg.Base):
+    def callback(self):
+        return pm.value
+
+    def callee(self):
+        return 1
+
+    def caller(self):
+        self.callee()
+        getattr(service, "run")
+        widget.configure(command=self.callback)
+        widget.bind("clicked", self.callback)
+        pm.api.call()
+'''
+    )
+    original_walk = ast.walk
+    walk_counts = {"full": 0, "nested": 0}
+
+    def tracked_walk(node):
+        if node is tree:
+            walk_counts["full"] += 1
+        else:
+            walk_counts["nested"] += 1
+        return original_walk(node)
+
+    monkeypatch.setattr(ast, "walk", tracked_walk)
+
+    facts = extract_module_usage_facts("sample", tree)
+
+    assert walk_counts["full"] == 1
+    assert walk_counts["nested"] > 0
+    assert "self.callee" in facts.direct_calls
+    assert "run" in facts.runtime_calls
+    assert "self.callback" in facts.callback_calls
+    assert "self.callback" in facts.event_bindings
+    assert ("Child", "pkg.Base") in facts.inheritance_refs
+    assert "pm.value" in facts.qualified_refs
+    assert "pm.api.call" not in facts.qualified_refs
+    assert "pm.api" not in facts.qualified_refs
+    assert facts.symbol_calls == (
+        ("sample::Child.caller", "sample::Child.callee", 12, "direct"),
+    )
+    assert facts.reference_evidence_materialized is True
+    assert facts.reference_evidence
+
+
 def test_full_cache_coverage_invariant(tmp_path):
     f1 = tmp_path / "mod_a.py"
     f1.write_text("x = 1\n", encoding="utf-8")
```

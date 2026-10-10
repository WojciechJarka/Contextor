# L32G_B1_PACKAGE_INIT_ALIAS_FAIL_CLOSED_FIX

## FILES_CHANGED_THIS_TASK

- `C:\Temp\Contextor_Repo\contextor\core\lineage_query\live_query.py`
- `C:\Temp\Contextor_Repo\tests\analysis\test_lineage_live_query.py`
- `C:\Temp\Contextor_Repo\walkthrough.md` (this report only; excluded from source/test diff accounting)

## CURRENT_SOURCE_VERIFICATION

DIRECT_EVIDENCE: Contextor returned the complete AST-bounded `query_live_symbol_lineage` implementation, source lines 480-762, with `implementation_is_complete=true`. The requested-module unavailable guard and resolved-target unavailable guard are present. The package-init guard was absent before this task and is now immediately after the requested-module guard.

DIRECT_EVIDENCE: Existing regression `test_live_lineage_rejects_untrusted_package_init_alias` was present. Before editing, only the report file was modified in the worktree; the source and test files had no local diff.

CONTEXTOR CONTRACT/BLAST RADIUS: Edit context identifies module `contextor.core.lineage_query.live_query`, seven direct and 124 transitive module consumers (sample bounded). Current lossless blast-radius projection reports 16 artifacts, 7 unique direct consumer modules, 117 unique downstream consumer modules. Call context reports 15 direct callee edges with no truncation. No additional lineage consumer requiring a source change was identified.

## PACKAGE_ALIAS_RED

Before patch:

```text
F
tests\analysis\test_lineage_live_query.py:1442:
AssertionError: assert 'resolved' == 'unavailable'
1 failed in 1.31s
```

## PACKAGE_ALIAS_GREEN

After patch, the original isolated regression passed: `1 passed in 0.63s`. The final complete lineage test file passed: `45 passed in 1.41s`.

The malformed package-init case now returns `resolution.status == "unavailable"`, `selected is None`, `owner_names == {}`, `state_freshness.canonical_state == "unavailable"`, and `state_freshness.families.module == "unavailable"`. The regression also snapshots and compares modules, parse freshness, re-export facts, and lineage facts to check no state mutation.

## TARGETED_REGRESSIONS

- Complete `tests/analysis/test_lineage_live_query.py`: 45 passed.
- Previous nine-file L32G-B gate: 257 passed, one existing Authlib deprecation warning.
- Previously selected eight LKG/snapshot/syntax/recovery tests: 8 passed, one existing Authlib deprecation warning.
- `git diff --check -- contextor/core/lineage_query/live_query.py tests/analysis/test_lineage_live_query.py`: exit 0; no whitespace errors.

The eight test nodes were located in source before execution:
`tests/test_live_e2e_corrections.py` (five nodes),
`tests/test_symbol_call_facts.py`,
`tests/test_syntax_diagnostics_full_analysis.py`, and
`tests/test_live_state_ipc.py`.

## VALID_FRESH_COMPATIBILITY

An explicit `module_parse_freshness["pkg.__init__"] = {"state": "fresh"}` still resolves `pkg::public_run` to `pkg.provider::run` and selects lineage facts. The targeted test passed.

## STALE_LKG_COMPATIBILITY

With `resync_required=False` and explicit `pkg.__init__` state `stale`, the alias still resolves and selected provider lineage facts remain available, preserving existing LKG selection. The test confirms the provider fact object is unchanged.

## UNRELATED_MODULE_ISOLATION

A malformed `unrelated.__init__` marker does not block direct query `pkg.mod::handler`; it resolves with selected facts and module freshness `fresh`.

A nested alias `pkg.sub::public_run` with malformed `pkg.sub.__init__` returns unavailable with no selected facts or owner names.

## PUBLIC_NO_SELECTED_FACTS

DIRECT_EVIDENCE: Both malformed top-level and nested package-init regressions pass with no selected facts or owner-name payload. Global resync alias test also returns unavailable with no selected facts; existing direct-query resync regression remains covered in the complete file.

## LIVE_REVISION_BEFORE_AFTER

Before edits: canonical LIVE revision 173; `get_live_events(after_revision=173)` showed continuous history and `resync_required=false`.

After edits: canonical LIVE revision 176. Watcher events were:
- revision 174, `desktop_watcher`, UPDATED `contextor/core/lineage_query/live_query.py`;
- revision 175, `desktop_watcher`, UPDATED `tests/analysis/test_lineage_live_query.py`;
- revision 176, `desktop_watcher`, UPDATED `tests/analysis/test_lineage_live_query.py` after the final assertion strengthening.

The final event query reports `continuity=continuous`, `resync_required=false`, and no gap.

## SOURCE_SYNC_VERIFICATION

Contextor's final complete symbol retrieval reports `workspace_sync=verified`, `canonical_state=fresh`, provenance `live`, canonical revision 176, and `implementation_is_complete=true`. Syntax diagnostics for the modified production file are `checked_and_none`, availability `fresh`. No MCP, Desktop, or LIVE restart was performed; no manual `update_file` call was made.

## FULL_DIFFS

### C:\Temp\Contextor_Repo\contextor\core\lineage_query\live_query.py

```diff
diff --git a/contextor/core/lineage_query/live_query.py b/contextor/core/lineage_query/live_query.py
index a7999b0..340db7e 100644
--- a/contextor/core/lineage_query/live_query.py
+++ b/contextor/core/lineage_query/live_query.py
@@ -525,6 +525,24 @@ def query_live_symbol_lineage(
                 ),
             )
 
+        package_init_module = f"{requested_module}.__init__"
+        modules = getattr(state, "modules", {})
+        if isinstance(modules, dict) and package_init_module in modules:
+            package_truth = module_current_truth(state, package_init_module)
+            if package_truth["state"] == "unavailable":
+                return LiveSymbolLineageQueryResult(
+                    resolution=LineageTargetResolution(
+                        status="unavailable",
+                        query=raw_query,
+                    ),
+                    unavailable_reason=package_truth["reason"],
+                    state_freshness=build_live_lineage_state_freshness(
+                        state,
+                        backend,
+                        target_module=package_init_module,
+                    ),
+                )
+
     try:
         canonical_query = backend.canonicalize_qualified_identity(
             raw_query
```

### C:\Temp\Contextor_Repo\tests\analysis\test_lineage_live_query.py

```diff
diff --git a/tests/analysis/test_lineage_live_query.py b/tests/analysis/test_lineage_live_query.py
index af08916..b7f98b1 100644
--- a/tests/analysis/test_lineage_live_query.py
+++ b/tests/analysis/test_lineage_live_query.py
@@ -1,3 +1,4 @@
+from copy import deepcopy
 from dataclasses import replace
 from types import SimpleNamespace
 from pathlib import Path
@@ -206,6 +207,32 @@ def _reexport_query_fixture(module_paths, reexport_facts, definitions):
     return state
 
 
+def _package_alias_fixture(package_name="pkg"):
+    package_init = f"{package_name}.__init__"
+    provider = f"{package_name}.provider"
+    return _reexport_query_fixture(
+        {
+            package_init: f"{package_name.replace('.', '/')}/__init__.py",
+            provider: f"{provider.replace('.', '/')}.py",
+        },
+        {
+            package_init: {
+                "exporter": package_name,
+                "explicit_all": ["public_run"],
+                "bindings": {"public_run": f"{provider}.run"},
+                "star_sources": [],
+            },
+            provider: {
+                "exporter": provider,
+                "explicit_all": None,
+                "bindings": {"run": f"{provider}.run"},
+                "star_sources": [],
+            },
+        },
+        {provider: (("A30/1", f"{provider}::run"),)},
+    )
+
+
 def test_live_target_catalog_resolves_artifact_id_only_through_owner_index(
     monkeypatch,
 ):
@@ -1414,34 +1441,126 @@ def test_live_lineage_rejects_untrusted_alias_or_origin(untrusted_module):
 
 
 def test_live_lineage_rejects_untrusted_package_init_alias():
-    state = _reexport_query_fixture(
-        {
-            "pkg.__init__": "pkg/__init__.py",
-            "pkg.provider": "pkg/provider.py",
-        },
+    state = _package_alias_fixture()
+    state.module_parse_freshness = {"pkg.__init__": {"state": "unknown"}}
+    modules = state.modules
+    freshness = state.module_parse_freshness
+    reexports = state.reexport_facts_by_module
+    lineage_facts = state.lineage_facts_by_source
+    provider_facts = lineage_facts["pkg/provider.py"]
+    canonical_snapshot = deepcopy(
         {
-            "pkg.__init__": {
-                "exporter": "pkg",
-                "explicit_all": ["public_run"],
-                "bindings": {"public_run": "pkg.provider.run"},
-                "star_sources": [],
-            },
-            "pkg.provider": {
-                "exporter": "pkg.provider",
-                "explicit_all": None,
-                "bindings": {"run": "pkg.provider.run"},
-                "star_sources": [],
-            },
-        },
-        {"pkg.provider": (("A30/1", "pkg.provider::run"),)},
+            "modules": state.modules,
+            "module_parse_freshness": state.module_parse_freshness,
+            "reexport_facts_by_module": state.reexport_facts_by_module,
+            "lineage_facts_by_source": state.lineage_facts_by_source,
+        }
     )
-    state.module_parse_freshness = {"pkg.__init__": {"state": "unknown"}}
 
     result = query_live_symbol_lineage(state, "pkg::public_run", ("interface",))
 
     assert result.resolution.status == "unavailable"
     assert result.selected is None
     assert result.owner_names == {}
+    assert result.state_freshness["canonical_state"] == "unavailable"
+    assert result.state_freshness["families"]["module"] == "unavailable"
+    assert state.modules is modules
+    assert state.module_parse_freshness is freshness
+    assert freshness["pkg.__init__"] == {"state": "unknown"}
+    assert state.reexport_facts_by_module is reexports
+    assert state.lineage_facts_by_source is lineage_facts
+    assert lineage_facts["pkg/provider.py"] is provider_facts
+    assert state.modules == canonical_snapshot["modules"]
+    assert state.module_parse_freshness == canonical_snapshot["module_parse_freshness"]
+    assert state.reexport_facts_by_module == canonical_snapshot["reexport_facts_by_module"]
+    assert state.lineage_facts_by_source == canonical_snapshot["lineage_facts_by_source"]
+
+
+def test_live_lineage_accepts_fresh_package_init_alias():
+    state = _package_alias_fixture()
+    state.module_parse_freshness = {
+        "pkg.__init__": {"state": "fresh"},
+    }
+
+    result = query_live_symbol_lineage(state, "pkg::public_run", ("interface",))
+
+    assert result.resolution.status == "resolved"
+    assert result.resolution.target is not None
+    assert result.resolution.target.qualified_name == "pkg.provider::run"
+    assert result.selected is not None
+
+
+def test_live_lineage_keeps_stale_package_init_lkg_alias_selection():
+    state = _package_alias_fixture()
+    state.resync_required = False
+    state.module_parse_freshness = {
+        "pkg.__init__": {"state": "stale", "error": "syntax failure"},
+    }
+    provider_facts = state.lineage_facts_by_source["pkg/provider.py"]
+
+    result = query_live_symbol_lineage(state, "pkg::public_run", ("interface",))
+
+    assert result.resolution.status == "resolved"
+    assert result.resolution.target is not None
+    assert result.resolution.target.qualified_name == "pkg.provider::run"
+    assert result.selected is not None
+    assert state.resync_required is False
+    assert state.lineage_facts_by_source["pkg/provider.py"] is provider_facts
+
+
+def test_live_lineage_unrelated_malformed_package_does_not_block_direct_module():
+    state, _backend = _fixture()
+    state.modules["unrelated.__init__"] = SimpleNamespace(
+        path="unrelated/__init__.py",
+    )
+    state.module_parse_freshness = {
+        "unrelated.__init__": {"state": "unknown"},
+    }
+
+    result = query_live_symbol_lineage(
+        state,
+        "pkg.mod::handler",
+        ("interface",),
+    )
+
+    assert result.resolution.status == "resolved"
+    assert result.selected is not None
+    assert result.state_freshness["families"]["module"] == "fresh"
+
+
+def test_live_lineage_nested_package_alias_checks_nested_init_freshness():
+    state = _package_alias_fixture("pkg.sub")
+    state.module_parse_freshness = {
+        "pkg.sub.__init__": {"state": "unknown"},
+    }
+
+    result = query_live_symbol_lineage(
+        state,
+        "pkg.sub::public_run",
+        ("interface",),
+    )
+
+    assert result.resolution.status == "unavailable"
+    assert result.selected is None
+    assert result.owner_names == {}
+    assert result.state_freshness["families"]["module"] == "unavailable"
+
+
+def test_live_lineage_package_alias_resync_is_fail_closed():
+    state = _package_alias_fixture()
+    state.resync_required = True
+    state.module_parse_freshness = {
+        "pkg.__init__": {"state": "unknown"},
+    }
+    original_facts = state.lineage_facts_by_source
+
+    result = query_live_symbol_lineage(state, "pkg::public_run", ("interface",))
+
+    assert result.resolution.status == "unavailable"
+    assert result.selected is None
+    assert result.owner_names == {}
+    assert result.state_freshness["canonical_state"] == "stale"
+    assert state.lineage_facts_by_source is original_facts
 
 
 def test_live_lineage_state_freshness_marks_resync_required():
```

## REMAINING_RISKS

No additional package-init alias bypass or consumer requiring a production edit was proven by the targeted test fixtures and Contextor call/blast-radius evidence.

Observed existing contract: a valid stale package-init marker is permitted to keep LKG selection. The final response freshness envelope is scoped to the resolved target module by the existing query code; this patch leaves that behavior unchanged.

## RESTART_REQUIRED

NONE. No runtime/server code requiring reload outside the watched file update was changed. No restart was performed.

## FINAL_VERDICT

PASS for the authorized focused patch and targeted regression gates. Malformed package-init freshness now blocks package alias resolution before facts are selected, while fresh aliases, stale LKG, direct unrelated queries, nested package checks, and global resync behavior are covered and passing.

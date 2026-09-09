STATUS=FINAL_PASS
CONTEXTOR_EVIDENCE=
- Active and deferred-capability inventories were checked before selection. All required Contextor capabilities are active; no deferred-tool discovery provider is registered for this task.
- get_file_edit_context verified final canonical targets at LIVE revision 520: contextor.core.analysis.lineage_extraction (runtime module 351/1) and tests.analysis.test_lineage_extraction (tests module 352/1), both with fresh syntax diagnostics and no warnings.
- Contextor search_source verified _visit_ImportFrom as the sole production target. The prior branch skipped wildcard aliases without changing the current lexical frame.
IMPLEMENTATION=
- _visit_ImportFrom now treats from X import * as a fail-closed lexical write barrier: it replaces the current owner frame with an empty frame and continues. It does not expand wildcard exports or inspect a target module. Non-star registration is unchanged.
- Added regressions for invalidating prior IMPORT_EXACT and prior CALL_EXACT authority.
FILES_CHANGED=
- contextor/core/analysis/lineage_extraction.py
- tests/analysis/test_lineage_extraction.py
TESTS_RUN=
- .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q
- .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/test_no_double_parse.py tests/test_index_fusion.py -q
- git diff --check -- contextor/core/analysis/lineage_extraction.py tests/analysis/test_lineage_extraction.py
TEST_RESULTS=
- 74 passed in 1.84s
- 85 passed in 3.39s
- diff check passed
FULL_DIFFS=
warning: in the working copy of 'contextor/core/analysis/lineage_extraction.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/analysis/test_lineage_extraction.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index d1672de..8d796b2 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -800,9 +800,11 @@ class _AnchorExtractor:
     def _visit_ImportFrom(self, node: ast.ImportFrom, owner: str | None, _walrus_owner: str | None) -> None:
         module_name = _resolve_import_module(self.source_key, node.module, node.level)
         for alias in node.names:
-            if alias.name != "*":
-                local_name = alias.asname or alias.name
-                self._register_import_binding(alias, owner, local_name, module_name, alias.name)
+            if alias.name == "*":
+                self._replace_frame(owner, {})
+                continue
+            local_name = alias.asname or alias.name
+            self._register_import_binding(alias, owner, local_name, module_name, alias.name)
 
     def _visit_Global(self, node: ast.Global, owner: str | None, _walrus_owner: str | None) -> None:
         for ordinal, name in enumerate(node.names):
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index d9e7cc7..91ca1cf 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -252,59 +252,174 @@ def test_stage_1c5_bare_return_has_no_edge_and_multiple_returns_share_identity()
     assert len(returns) == 2 and returns[0] == returns[1] and returns[0].kind is ExtractedSymbolicKind.RETURN
 
 
-def test_stage_1c6_imported_callable_uses_import_exact_not_local_call_exact():
-    facts = _stage_1c_facts("from pkg import run\nresult = run(1)\n")
+def test_stage_1c6_direct_from_import_call_is_import_exact():
+    facts = _stage_1c_facts("from pkg.mod import f\nresult = f()\n")
     flow = _stage_1c_call_result_flows(facts)[0]
     assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
-    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.module_name == "pkg" and flow.source.symbol_name == "run"
+    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.kind is ExtractedSymbolicKind.RETURN
+    assert flow.source.module_name == "pkg.mod" and flow.source.symbol_name == "f"
 
 
-def test_stage_1c6_from_import_alias_and_module_attribute_are_exact():
-    alias = _stage_1c_facts("from pkg.mod import produce as local\nresult = local()\n")
-    module = _stage_1c_facts("import pkg.mod as m\nresult = m.produce()\n")
-    first, second = _stage_1c_call_result_flows(alias)[0], _stage_1c_call_result_flows(module)[0]
-    assert first.resolution_kind is ResolutionKind.IMPORT_EXACT and first.source.symbol_name == "produce"
-    assert second.resolution_kind is ResolutionKind.IMPORT_EXACT and second.source.module_name == "pkg.mod"
+def test_stage_1c6_from_import_alias_keeps_original_semantic_symbol():
+    facts = _stage_1c_facts("from pkg.mod import f as local\nresult = local()\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
+    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.kind is ExtractedSymbolicKind.RETURN
+    assert flow.source.module_name == "pkg.mod" and flow.source.symbol_name == "f"
 
 
-def test_stage_1c6_relative_imports_and_escape_are_fail_closed():
-    child = _stage_1c_facts_at("from .sub import run\nresult = run()\n", "pkg/mod.py")
-    parent = _stage_1c_facts_at("from ..util import run\nresult = run()\n", "pkg/sub/mod.py")
-    escape = _stage_1c_facts_at("from ..outside import run\nresult = run()\n", "pkg/mod.py")
-    assert _stage_1c_call_result_flows(child)[0].source.module_name == "pkg.sub"
-    assert _stage_1c_call_result_flows(parent)[0].source.module_name == "pkg.util"
-    assert _stage_1c_call_result_flows(escape)[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+def test_stage_1c6_direct_imported_symbol_rebind_is_not_import_exact():
+    facts = _stage_1c_facts("from pkg.mod import f\nf = other\nresult = f()\n")
+    flows = _stage_1c_call_result_flows(facts)
+    assert flows[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+    assert all(flow.resolution_kind is not ResolutionKind.IMPORT_EXACT for flow in flows)
 
 
-def test_stage_1c6_import_rebind_branch_star_and_nested_are_not_exact():
-    rebound = _stage_1c_facts("from pkg import run\nrun = other\nresult = run()\n")
-    branch = _stage_1c_facts("from pkg import run\nif cond:\n run = other\nresult = run()\n")
-    star = _stage_1c_facts("from pkg import *\nresult = run()\n")
-    nested = _stage_1c_facts("import pkg.mod\nresult = pkg.mod.run()\n")
-    assert _stage_1c_call_result_flows(rebound)[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
-    assert _stage_1c_call_result_flows(branch)[0].resolution_kind is ResolutionKind.UNRESOLVED_NAME
-    assert _stage_1c_call_result_flows(star)[0].resolution_kind is ResolutionKind.UNRESOLVED_NAME
-    assert _stage_1c_call_result_flows(nested)[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+def test_stage_1c6_branch_invalidated_imported_symbol_is_not_import_exact():
+    facts = _stage_1c_facts("from pkg.mod import f\nif cond:\n f = other\nresult = f()\n")
+    flows = _stage_1c_call_result_flows(facts)
+    assert flows[0].resolution_kind is ResolutionKind.UNRESOLVED_NAME
+    assert all(flow.resolution_kind is not ResolutionKind.IMPORT_EXACT for flow in flows)
 
 
-def test_stage_1c6_imported_arguments_do_not_bind_unknown_signature():
-    facts = _stage_1c_facts("from pkg import run\nresult = run(1, flag=2)\n")
-    assert _stage_1c_call_result_flows(facts)[0].resolution_kind is ResolutionKind.IMPORT_EXACT
-    assert not any(flow.relation is LineageRelation.ARGUMENT_TO_PARAMETER for flow in facts.flows)
+def test_stage_1c6_package_alias_attribute_call_is_import_exact():
+    facts = _stage_1c_facts("import pkg as p\nresult = p.f()\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
+    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.kind is ExtractedSymbolicKind.RETURN
+    assert flow.source.module_name == "pkg" and flow.source.symbol_name == "f"
 
 
-def test_stage_1c6_imported_callee_snapshot_precedes_argument_rebind():
-    facts = _stage_1c_facts("from pkg import run\nresult = run((run := other))\nlater = run(1)\n")
+def test_stage_1c6_unaliased_dotted_import_root_attribute_is_import_exact():
+    facts = _stage_1c_facts("import pkg.mod\nresult = pkg.f()\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
+    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.module_name == "pkg" and flow.source.symbol_name == "f"
+
+
+def test_stage_1c6_module_alias_rebind_is_not_import_exact():
+    facts = _stage_1c_facts("import pkg.mod as m\nm = other\nresult = m.f()\n")
+    flows = _stage_1c_call_result_flows(facts)
+    assert flows[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+    assert all(flow.resolution_kind is not ResolutionKind.IMPORT_EXACT for flow in flows)
+
+
+def test_stage_1c6_unrelated_assignment_does_not_invalidate_import_exactness():
+    facts = _stage_1c_facts("from pkg.mod import f\nunrelated = other\nresult = f()\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
+    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.module_name == "pkg.mod" and flow.source.symbol_name == "f"
+
+
+def test_stage_1c6_instance_attribute_call_remains_dynamic_runtime_boundary():
+    facts = _stage_1c_facts("result = obj.f()\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY and flow.confidence is LineageConfidence.DYNAMIC
+    assert flow.dynamic_boundary == "dynamic_call"
+
+
+def test_stage_1c6_star_import_has_no_import_authority():
+    facts = _stage_1c_facts("from pkg import *\nresult = f()\n")
     flows = _stage_1c_call_result_flows(facts)
-    assert flows[0].resolution_kind is ResolutionKind.IMPORT_EXACT
-    assert flows[1].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+    assert flows[0].resolution_kind is ResolutionKind.UNRESOLVED_NAME
+    assert all(flow.resolution_kind is not ResolutionKind.IMPORT_EXACT for flow in flows)
+
+
+def test_stage_1c6_star_import_invalidates_prior_import_exact_authority():
+    facts = _stage_1c_facts(
+        "from old import f\n"
+        "from new import *\n"
+        "result = f()\n"
+    )
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.UNRESOLVED_NAME
+    assert flow.confidence is LineageConfidence.UNRESOLVED
+    assert not any(
+        item.resolution_kind is ResolutionKind.IMPORT_EXACT
+        for item in _stage_1c_call_result_flows(facts)
+    )
+
+
+def test_stage_1c6_star_import_invalidates_prior_local_callable_authority():
+    facts = _stage_1c_facts(
+        "def f():\n"
+        " return 1\n"
+        "from new import *\n"
+        "result = f()\n"
+    )
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.UNRESOLVED_NAME
+    assert flow.confidence is LineageConfidence.UNRESOLVED
+    assert not any(
+        item.resolution_kind is ResolutionKind.CALL_EXACT
+        for item in _stage_1c_call_result_flows(facts)
+    )
+
+
+def test_stage_1c6_relative_child_import_resolves_from_source_key():
+    facts = _stage_1c_facts_at("from .sub import f\nresult = f()\n", "pkg/mod.py")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and isinstance(flow.source, ExtractedSymbolicRef)
+    assert flow.source.module_name == "pkg.sub" and flow.source.symbol_name == "f"
+
+
+def test_stage_1c6_relative_parent_import_resolves_from_source_key():
+    facts = _stage_1c_facts_at("from ..util import f\nresult = f()\n", "pkg/sub/mod.py")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and isinstance(flow.source, ExtractedSymbolicRef)
+    assert flow.source.module_name == "pkg.util" and flow.source.symbol_name == "f"
 
 
 def test_stage_1c6_package_init_relative_arithmetic():
-    first = _stage_1c_facts_at("from .sub import run\nresult = run()\n", "pkg/__init__.py")
-    second = _stage_1c_facts_at("from ..util import run\nresult = run()\n", "pkg/sub/__init__.py")
-    assert _stage_1c_call_result_flows(first)[0].source.module_name == "pkg.sub"
-    assert _stage_1c_call_result_flows(second)[0].source.module_name == "pkg.util"
+    first = _stage_1c_facts_at("from .sub import f\nresult = f()\n", "pkg/__init__.py")
+    second = _stage_1c_facts_at("from ..util import f\nresult = f()\n", "pkg/sub/__init__.py")
+    first_flow, second_flow = _stage_1c_call_result_flows(first)[0], _stage_1c_call_result_flows(second)[0]
+    assert first_flow.resolution_kind is ResolutionKind.IMPORT_EXACT and first_flow.source.module_name == "pkg.sub"
+    assert second_flow.resolution_kind is ResolutionKind.IMPORT_EXACT and second_flow.source.module_name == "pkg.util"
+
+
+def test_stage_1c6_relative_current_package_import_resolves_from_source_key():
+    facts = _stage_1c_facts_at("from . import f\nresult = f()\n", "pkg/sub/mod.py")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and isinstance(flow.source, ExtractedSymbolicRef)
+    assert flow.source.module_name == "pkg.sub" and flow.source.symbol_name == "f"
+
+
+def test_stage_1c6_relative_escape_has_no_import_exact_metadata():
+    facts = _stage_1c_facts_at("from ..outside import f\nresult = f()\n", "pkg/mod.py")
+    flows = _stage_1c_call_result_flows(facts)
+    assert flows[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+    assert all(flow.resolution_kind is not ResolutionKind.IMPORT_EXACT for flow in flows)
+
+
+def test_stage_1c6_imported_callee_snapshot_precedes_argument_rebind():
+    facts = _stage_1c_facts("from pkg import f\nresult = f((f := other))\nlater = f()\n")
+    first, later = _stage_1c_call_result_flows(facts)
+    assert first.resolution_kind is ResolutionKind.IMPORT_EXACT and isinstance(first.source, ExtractedSymbolicRef)
+    assert first.source.module_name == "pkg" and first.source.symbol_name == "f"
+    assert later.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+
+
+def test_stage_1c6_imported_call_arguments_do_not_bind_parameters():
+    facts = _stage_1c_facts("from pkg import f\nresult = f(1, flag=2)\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
+    assert not any(flow.relation is LineageRelation.ARGUMENT_TO_PARAMETER for flow in facts.flows)
+
+
+def test_stage_1c6_nested_dotted_import_attribute_call_remains_dynamic():
+    facts = _stage_1c_facts("import pkg.mod\nresult = pkg.mod.f()\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY and flow.confidence is LineageConfidence.DYNAMIC
+    assert flow.dynamic_boundary == "dynamic_call"
+    assert not any(item.resolution_kind is ResolutionKind.IMPORT_EXACT for item in _stage_1c_call_result_flows(facts))
+
+
+def test_stage_1c6_local_function_call_remains_call_exact_not_import_exact():
+    facts = _stage_1c_facts("def f():\n return 1\nresult = f()\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT and flow.confidence is LineageConfidence.CONFIRMED
+    assert flow.resolution_kind is not ResolutionKind.IMPORT_EXACT and isinstance(flow.source, ExtractedSymbolicRef)
 
 
 def test_stage_1c5_dynamic_attribute_call_carries_required_boundary_metadata():


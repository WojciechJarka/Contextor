STATUS=FINAL_PASS
CONTEXTOR_PRE_EDIT=Fresh Contextor canonical context and clean base confirmed.
IMPLEMENTATION=Stage 1C.6 import exactness, relative arithmetic, rebind safety, callee snapshot, and fail-closed boundaries.
FILES_CHANGED=contextor/core/analysis/lineage_extraction.py; tests/analysis/test_lineage_extraction.py
TESTS_RUN=focused plus combined matrix and diff check.
TEST_RESULTS=60 focused passed; 71 combined passed; diff check passed.
FULL_DIFFS=
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 5d8578f..d1672de 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -149,6 +149,14 @@ def _module_name_from_source_key(source_key: str) -> str:
     module_name = source_key[:-3].replace("/", ".")
     return module_name[: -len(".__init__")] if module_name.endswith(".__init__") else module_name
 
+def _resolve_import_module(source_key: str, module_name: str | None, level: int) -> str | None:
+    if level == 0: return module_name
+    package_parts = source_key.split("/")[:-1]
+    if not package_parts or level > len(package_parts): return None
+    target_parts = list(package_parts[:len(package_parts) - (level - 1)])
+    if module_name: target_parts.extend(module_name.split("."))
+    return ".".join(target_parts) if target_parts else None
+
 
 @dataclass(frozen=True)
 class _ParameterInfo:
@@ -284,6 +292,12 @@ class _AnchorExtractor:
     def _import_frame(self, owner: str | None) -> dict[str, _ImportInfo]:
         return self._imports.setdefault(owner, {})
 
+    def _register_import_binding(self, alias: ast.alias, owner: str | None, local_name: str, module_name: str | None, symbol_name: str | None) -> None:
+        binding_id = self._add("import_binding", alias, local_name, owner)
+        if local_name in self._blocked_names(owner): return
+        self._frame(owner)[local_name] = ExtractedOccurrenceRef(binding_id)
+        if module_name is not None: self._import_frame(owner)[local_name] = _ImportInfo(module_name, symbol_name, binding_id)
+
     def _value(
         self,
         node: ast.AST,
@@ -309,6 +323,21 @@ class _AnchorExtractor:
         if current is None: return None
         return self._callables_by_anchor.get(current.local_id) or self._callables_by_binding.get(current.local_id)
 
+    def _current_import_info(self, owner: str | None, local_name: str) -> _ImportInfo | None:
+        current, info = self._frame(owner).get(local_name), self._import_frame(owner).get(local_name)
+        return info if current is not None and info is not None and current.local_id == info.binding_id else None
+
+    def _resolve_current_imported_callable(self, node: ast.Call, owner: str | None) -> ExtractedSymbolicRef | None:
+        if isinstance(node.func, ast.Name):
+            info = self._current_import_info(owner, node.func.id)
+            if info is None or info.symbol_name is None: return None
+            return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, info.module_name, info.symbol_name, info.binding_id)
+        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
+            info = self._current_import_info(owner, node.func.value.id)
+            if info is None or info.symbol_name is not None: return None
+            return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, info.module_name, node.func.attr, info.binding_id)
+        return None
+
     def _collect_call_arguments(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> tuple[_CallArgumentInfo, ...]:
         pending = [(arg, "starred" if isinstance(arg, ast.Starred) else "positional", None, index) for index, arg in enumerate(node.args)]
         pending += [(keyword.value, "double_starred" if keyword.arg is None else "keyword", keyword.arg, len(node.args) + index) for index, keyword in enumerate(node.keywords)]
@@ -459,6 +488,7 @@ class _AnchorExtractor:
     def _visit_Call(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> None:
         self._visit(node.func, owner, walrus_owner)
         callable_info = self._resolve_current_local_callable(node, owner)
+        imported_return = self._resolve_current_imported_callable(node, owner)
         callee_ref = self._frame(owner).get(node.func.id) if isinstance(node.func, ast.Name) else None
         call_site, call_result = self._occurrence("call_site", node), self._occurrence("call_result", node)
         arguments = self._collect_call_arguments(node, owner, walrus_owner)
@@ -466,6 +496,9 @@ class _AnchorExtractor:
             self._bind_call_arguments(arguments, callable_info)
             self._flow(source=self._return_symbolic(callable_info), target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
             return
+        if imported_return is not None:
+            self._flow(source=imported_return, target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=ResolutionKind.IMPORT_EXACT, confidence=LineageConfidence.CONFIRMED)
+            return
         if isinstance(node.func, ast.Name) and callee_ref is None:
             resolution_kind, confidence = ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED
             dynamic_boundary = None
@@ -762,17 +795,14 @@ class _AnchorExtractor:
     def _visit_Import(self, node: ast.Import, owner: str | None, _walrus_owner: str | None) -> None:
         for alias in node.names:
             local_name = alias.asname or alias.name.split(".", 1)[0]
-            binding_id = self._add("import_binding", alias, local_name, owner)
-            if local_name not in self._blocked_names(owner):
-                self._frame(owner)[local_name] = ExtractedOccurrenceRef(binding_id)
+            self._register_import_binding(alias, owner, local_name, alias.name if alias.asname is not None else alias.name.split(".", 1)[0], None)
 
     def _visit_ImportFrom(self, node: ast.ImportFrom, owner: str | None, _walrus_owner: str | None) -> None:
+        module_name = _resolve_import_module(self.source_key, node.module, node.level)
         for alias in node.names:
             if alias.name != "*":
                 local_name = alias.asname or alias.name
-                binding_id = self._add("import_binding", alias, local_name, owner)
-                if local_name not in self._blocked_names(owner):
-                    self._frame(owner)[local_name] = ExtractedOccurrenceRef(binding_id)
+                self._register_import_binding(alias, owner, local_name, module_name, alias.name)
 
     def _visit_Global(self, node: ast.Global, owner: str | None, _walrus_owner: str | None) -> None:
         for ordinal, name in enumerate(node.names):
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index b23b7f5..d9e7cc7 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -109,6 +109,10 @@ def _stage_1c_facts(source: str):
     return extract_lineage_source_facts(ast.parse(source), source_key="pkg.py", source_fingerprint=FINGERPRINT)
 
 
+def _stage_1c_facts_at(source: str, source_key: str):
+    return extract_lineage_source_facts(ast.parse(source), source_key=source_key, source_fingerprint=FINGERPRINT)
+
+
 def _stage_1c_named(facts, kind, name):
     return [item for item in facts.anchors if item.kind == kind and parse_local_occurrence_id(item.local_id)[3] == name]
 
@@ -248,11 +252,59 @@ def test_stage_1c5_bare_return_has_no_edge_and_multiple_returns_share_identity()
     assert len(returns) == 2 and returns[0] == returns[1] and returns[0].kind is ExtractedSymbolicKind.RETURN
 
 
-def test_stage_1c5_imported_callable_does_not_become_local_call_exact():
+def test_stage_1c6_imported_callable_uses_import_exact_not_local_call_exact():
     facts = _stage_1c_facts("from pkg import run\nresult = run(1)\n")
     flow = _stage_1c_call_result_flows(facts)[0]
-    assert not any(f.resolution_kind is ResolutionKind.IMPORT_EXACT for f in facts.flows)
-    assert flow.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY and flow.confidence is LineageConfidence.DYNAMIC and flow.dynamic_boundary == "dynamic_call"
+    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
+    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.module_name == "pkg" and flow.source.symbol_name == "run"
+
+
+def test_stage_1c6_from_import_alias_and_module_attribute_are_exact():
+    alias = _stage_1c_facts("from pkg.mod import produce as local\nresult = local()\n")
+    module = _stage_1c_facts("import pkg.mod as m\nresult = m.produce()\n")
+    first, second = _stage_1c_call_result_flows(alias)[0], _stage_1c_call_result_flows(module)[0]
+    assert first.resolution_kind is ResolutionKind.IMPORT_EXACT and first.source.symbol_name == "produce"
+    assert second.resolution_kind is ResolutionKind.IMPORT_EXACT and second.source.module_name == "pkg.mod"
+
+
+def test_stage_1c6_relative_imports_and_escape_are_fail_closed():
+    child = _stage_1c_facts_at("from .sub import run\nresult = run()\n", "pkg/mod.py")
+    parent = _stage_1c_facts_at("from ..util import run\nresult = run()\n", "pkg/sub/mod.py")
+    escape = _stage_1c_facts_at("from ..outside import run\nresult = run()\n", "pkg/mod.py")
+    assert _stage_1c_call_result_flows(child)[0].source.module_name == "pkg.sub"
+    assert _stage_1c_call_result_flows(parent)[0].source.module_name == "pkg.util"
+    assert _stage_1c_call_result_flows(escape)[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+
+
+def test_stage_1c6_import_rebind_branch_star_and_nested_are_not_exact():
+    rebound = _stage_1c_facts("from pkg import run\nrun = other\nresult = run()\n")
+    branch = _stage_1c_facts("from pkg import run\nif cond:\n run = other\nresult = run()\n")
+    star = _stage_1c_facts("from pkg import *\nresult = run()\n")
+    nested = _stage_1c_facts("import pkg.mod\nresult = pkg.mod.run()\n")
+    assert _stage_1c_call_result_flows(rebound)[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+    assert _stage_1c_call_result_flows(branch)[0].resolution_kind is ResolutionKind.UNRESOLVED_NAME
+    assert _stage_1c_call_result_flows(star)[0].resolution_kind is ResolutionKind.UNRESOLVED_NAME
+    assert _stage_1c_call_result_flows(nested)[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+
+
+def test_stage_1c6_imported_arguments_do_not_bind_unknown_signature():
+    facts = _stage_1c_facts("from pkg import run\nresult = run(1, flag=2)\n")
+    assert _stage_1c_call_result_flows(facts)[0].resolution_kind is ResolutionKind.IMPORT_EXACT
+    assert not any(flow.relation is LineageRelation.ARGUMENT_TO_PARAMETER for flow in facts.flows)
+
+
+def test_stage_1c6_imported_callee_snapshot_precedes_argument_rebind():
+    facts = _stage_1c_facts("from pkg import run\nresult = run((run := other))\nlater = run(1)\n")
+    flows = _stage_1c_call_result_flows(facts)
+    assert flows[0].resolution_kind is ResolutionKind.IMPORT_EXACT
+    assert flows[1].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+
+
+def test_stage_1c6_package_init_relative_arithmetic():
+    first = _stage_1c_facts_at("from .sub import run\nresult = run()\n", "pkg/__init__.py")
+    second = _stage_1c_facts_at("from ..util import run\nresult = run()\n", "pkg/sub/__init__.py")
+    assert _stage_1c_call_result_flows(first)[0].source.module_name == "pkg.sub"
+    assert _stage_1c_call_result_flows(second)[0].source.module_name == "pkg.util"
 
 
 def test_stage_1c5_dynamic_attribute_call_carries_required_boundary_metadata():


# Contexdiff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index fad439f..63c985a 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -54,6 +54,7 @@ from contextor.core.analysis.lineage_extraction_visitors import (
     visit_lambda,
     visit_module,
     visit_return,
+    visit_yield,
 )
 from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
 from contextor.core.domain.lineage_facts import (
@@ -148,6 +149,12 @@ class _AnchorExtractor:
     def _visit_Return(self, node: ast.Return, owner: str | None, walrus_owner: str | None) -> None:
         return visit_return(self.state, self.paths, self.module_name, node, owner, walrus_owner, value=self._value)
 
+    def _visit_Yield(self, node: ast.Yield, owner: str | None, walrus_owner: str | None) -> None:
+        return visit_yield(self.state, node, owner, walrus_owner, visit=self._visit)
+
+    def _visit_YieldFrom(self, node: ast.YieldFrom, owner: str | None, walrus_owner: str | None) -> None:
+        return visit_yield(self.state, node, owner, walrus_owner, visit=self._visit)
+
     def _visit_Call(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> None:
         return visit_call(self.state, self.paths, self.module_name, node, owner, walrus_owner, visit=self._visit, value=self._value)
 
diff --git a/contextor/core/analysis/lineage_extraction_state.py b/contextor/core/analysis/lineage_extraction_state.py
index 2f40cab..82449d6 100644
--- a/contextor/core/analysis/lineage_extraction_state.py
+++ b/contextor/core/analysis/lineage_extraction_state.py
@@ -21,6 +21,12 @@ class _CallableInfo:
     parameters: tuple[_ParameterInfo, ...]
 
 
+@dataclass(frozen=True)
+class _CallableReturnRecord:
+    node: ast.Return
+    callable_info: _CallableInfo | None
+
+
 @dataclass(frozen=True)
 class _ImportInfo:
     module_name: str
@@ -65,6 +71,9 @@ class LineageExtractionState:
     _callables_by_anchor: dict[str, _CallableInfo] = field(default_factory=dict)
     _callables_by_binding: dict[str, _CallableInfo] = field(default_factory=dict)
     _callable_values: dict[str, _CallableInfo] = field(default_factory=dict)
+    _return_records: dict[str, list[_CallableReturnRecord]] = field(default_factory=dict)
+    _callable_returns: dict[str, _CallableInfo] = field(default_factory=dict)
+    _generator_owners: set[str] = field(default_factory=set)
     _imports: dict[str | None, dict[str, _ImportInfo]] = field(default_factory=dict)
     _blocked: dict[str | None, set[str]] = field(default_factory=dict)
     _active_comprehensions: list[_ActiveComprehension] = field(default_factory=list)
@@ -106,6 +115,61 @@ class LineageExtractionState:
     def import_frame(self, owner: str | None) -> dict[str, _ImportInfo]:
         return self._imports.setdefault(owner, {})
 
+    def record_callable_return(
+        self,
+        owner: str | None,
+        node: ast.Return,
+        callable_info: _CallableInfo | None,
+    ) -> None:
+        if owner is None or self._owner_kind.get(owner) not in {
+            "function",
+            "async_function",
+            "lambda",
+        }:
+            return
+        self._return_records.setdefault(owner, []).append(
+            _CallableReturnRecord(node, callable_info)
+        )
+
+    def mark_generator(self, owner: str | None) -> None:
+        if owner is not None and self._owner_kind.get(owner) in {
+            "function",
+            "async_function",
+            "lambda",
+        }:
+            self._generator_owners.add(owner)
+
+    def finalize_function_callable_return(
+        self,
+        owner: str,
+        node: ast.FunctionDef | ast.AsyncFunctionDef,
+    ) -> None:
+        self._callable_returns.pop(owner, None)
+        records = self._return_records.get(owner, [])
+        if (
+            self._owner_kind.get(owner) == "function"
+            and owner not in self._generator_owners
+            and len(records) == 1
+            and node.body
+            and records[0].node is node.body[-1]
+            and records[0].callable_info is not None
+        ):
+            self._callable_returns[owner] = records[0].callable_info
+
+    def publish_lambda_callable_return(
+        self,
+        owner: str,
+        body_source: ExtractedOccurrenceRef,
+    ) -> None:
+        self._callable_returns.pop(owner, None)
+        callable_info = self._callable_values.get(body_source.local_id)
+        if (
+            self._owner_kind.get(owner) == "lambda"
+            and owner not in self._generator_owners
+            and callable_info is not None
+        ):
+            self._callable_returns[owner] = callable_info
+
     def register_owner(
         self,
         owner_id: str,
diff --git a/contextor/core/analysis/lineage_extraction_visitors.py b/contextor/core/analysis/lineage_extraction_visitors.py
index ae3bb54..64bdab9 100644
--- a/contextor/core/analysis/lineage_extraction_visitors.py
+++ b/contextor/core/analysis/lineage_extraction_visitors.py
@@ -143,6 +143,7 @@ def visit_function(
         )
     for child in node.body:
         visit(child, function_id, None)
+    state.finalize_function_callable_return(function_id, node)
     if node.name not in state.blocked_names(owner):
         state.frame(owner)[node.name] = ExtractedOccurrenceRef(
             function_id
@@ -214,6 +215,7 @@ def visit_lambda(
         resolution_kind=ResolutionKind.LEXICAL_EXACT,
         confidence=LineageConfidence.CONFIRMED,
     )
+    state.publish_lambda_callable_return(lambda_id, body_source)
     lambda_value = occurrence(
         state,
         paths,
@@ -233,15 +235,18 @@ def visit_return(
     *,
     value: ValueFn,
 ) -> None:
-    if node.value is None:
-        return
-    source = value(node.value, owner, walrus_owner)
+    source = value(node.value, owner, walrus_owner) if node.value is not None else None
+    returned_callable = (
+        state._callable_values.get(source.local_id)
+        if source is not None
+        else None
+    )
     callable_info = (
         state._callables_by_anchor.get(owner)
         if owner is not None
         else None
     )
-    if callable_info is not None:
+    if callable_info is not None and source is not None:
         emit_flow(
             state,
             paths,
@@ -252,6 +257,20 @@ def visit_return(
             resolution_kind=ResolutionKind.LEXICAL_EXACT,
             confidence=LineageConfidence.CONFIRMED,
         )
+    state.record_callable_return(owner, node, returned_callable)
+
+
+def visit_yield(
+    state: LineageExtractionState,
+    node: ast.Yield | ast.YieldFrom,
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    visit: VisitFn,
+) -> None:
+    state.mark_generator(owner)
+    if node.value is not None:
+        visit(node.value, owner, walrus_owner)
 
 
 def visit_call(
@@ -276,6 +295,14 @@ def visit_call(
         node,
         owner,
     )
+    if callable_info is None and isinstance(node.func, ast.Call):
+        inner_call_result = occurrence(
+            state,
+            paths,
+            "call_result",
+            node.func,
+        )
+        callable_info = state._callable_values.get(inner_call_result.local_id)
     callee_ref = (
         state.frame(owner).get(node.func.id)
         if isinstance(node.func, ast.Name)
@@ -319,6 +346,9 @@ def visit_call(
             resolution_kind=ResolutionKind.CALL_EXACT,
             confidence=LineageConfidence.CONFIRMED,
         )
+        returned_callable = state._callable_returns.get(callable_info.anchor_id)
+        if returned_callable is not None:
+            state._callable_values[call_result.local_id] = returned_callable
         return
     if imported_return is not None:
         emit_flow(
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index 8161990..1e37df0 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -1748,3 +1748,122 @@ def test_stage_1d2_factory_return_alias_is_not_newly_resolved():
     )
     flows = _stage_1c_call_result_flows(facts)
     assert flows[-1].resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+def _stage_1d3_final_call(facts):
+    return _stage_1c_call_result_flows(facts)[-1]
+
+
+def test_stage_1d3_a_factory_returned_local_callable_assigns_exactly():
+    facts = _stage_1c_facts(
+        "def factory():\n def f(): return 1\n return f\ng=factory()\nresult=g()\n"
+    )
+    flow = _stage_1d3_final_call(facts)
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
+    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name == "f"
+
+
+def test_stage_1d3_b_factory_returned_local_alias_assigns_exactly():
+    facts = _stage_1c_facts(
+        "def factory():\n def f(): return 1\n g=f\n return g\nh=factory()\nresult=h()\n"
+    )
+    flow = _stage_1d3_final_call(facts)
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
+    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name == "f"
+
+
+def test_stage_1d3_c_factory_returned_lambda_assigns_exactly():
+    facts = _stage_1c_facts("def factory():\n return lambda: 1\ng=factory()\nresult=g()\n")
+    flow = _stage_1d3_final_call(facts)
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
+    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name.startswith("lambda@")
+
+
+def test_stage_1d3_d_direct_factory_result_invocation_is_exact():
+    facts = _stage_1c_facts("def factory():\n def f(): return 1\n return f\nresult=factory()()\n")
+    flow = _stage_1d3_final_call(facts)
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
+    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name == "f"
+
+
+def test_stage_1d3_e_terminal_return_of_proven_call_result_propagates():
+    facts = _stage_1c_facts(
+        "def factory2():\n def factory1():\n  def f(): return 1\n  return f\n return factory1()\ng=factory2()\nresult=g()\n"
+    )
+    flow = _stage_1d3_final_call(facts)
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
+    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name == "f"
+
+
+def test_stage_1d3_f_terminal_return_after_other_statements_is_exact():
+    facts = _stage_1c_facts(
+        "def factory():\n marker=1\n def f(): return 1\n return f\ng=factory()\nresult=g()\n"
+    )
+    assert _stage_1d3_final_call(facts).resolution_kind is ResolutionKind.CALL_EXACT
+
+
+def test_stage_1d3_g_multiple_explicit_returns_fail_closed():
+    facts = _stage_1c_facts(
+        "def factory(flag):\n def f(): return 1\n if flag: return f\n return f\ng=factory(True)\nresult=g()\n"
+    )
+    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+def test_stage_1d3_h_conditional_only_return_fails_closed():
+    facts = _stage_1c_facts(
+        "def factory(flag):\n def f(): return 1\n if flag: return f\ng=factory(True)\nresult=g()\n"
+    )
+    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+def test_stage_1d3_i_mixed_callable_and_non_callable_returns_fail_closed():
+    facts = _stage_1c_facts(
+        "def factory(flag):\n def f(): return 1\n if flag: return f\n return 1\ng=factory(True)\nresult=g()\n"
+    )
+    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+def test_stage_1d3_j_async_factory_return_does_not_become_callable_value():
+    facts = _stage_1c_facts(
+        "async def factory():\n def f(): return 1\n return f\ng=factory()\nresult=g()\n"
+    )
+    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+def test_stage_1d3_k_generator_factory_return_does_not_become_callable_value():
+    facts = _stage_1c_facts(
+        "def factory():\n def f(): return 1\n yield 1\n return f\ng=factory()\nresult=g()\n"
+    )
+    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+@pytest.mark.parametrize(
+    "source",
+    (
+        "from pkg import factory\ng=factory()\nresult=g()\n",
+        "g=obj.factory()\nresult=g()\n",
+        "g=[factory][0]()\nresult=g()\n",
+        "g=getattr(obj, 'factory')()\nresult=g()\n",
+    ),
+)
+def test_stage_1d3_l_imported_attribute_container_and_reflection_fail_closed(source):
+    assert _stage_1d3_final_call(_stage_1c_facts(source)).resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+def test_stage_1d3_m_module_global_return_lookup_remains_unresolved():
+    facts = _stage_1c_facts(
+        "def f(): return 1\ndef factory(): return f\ng=factory()\nresult=g()\n"
+    )
+    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+def test_stage_1d3_n_closure_cell_callable_value_remains_unresolved():
+    facts = _stage_1c_facts(
+        "def outer():\n def f(): return 1\n def factory(): return f\n g=factory()\n return g()\n"
+    )
+    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+def test_stage_1d3_o_existing_local_callable_alias_remains_exact():
+    facts = _stage_1c_facts("def f(): return 1\ng=f\nresult=g()\n")
+    assert _stage_1d3_final_call(facts).resolution_kind is ResolutionKind.CALL_EXACT
```


# Contextor Stage 1D.4 — exact callback parameter registration + invocation lineage

STATUS: COMPLETE

## Result

Implemented context-preserving callback lineage without specializing the body call result. Parameter registration is keyed by exact parameter local ID plus callable owner; an invocation is emitted only while the current frame still holds that original anchor. Exact argument callable identity is retained from the existing `value(...)` result and composes into `CALLBACK_REGISTERS` only for a parameter that was lexically invoked.

The ordinary callback-body `CALL_RESULT` remains `DYNAMIC_RUNTIME_BOUNDARY`; no direct `f -> callback()` `CALL_EXACT` relation is introduced.

## Semantic evidence A–O

- A: complete `f anchor -> CALLBACK_REGISTERS -> apply::callback -> CALLBACK_INVOKES -> callback() call_site` path; callback result remains dynamic.
- B–E: keyword, lambda, 1D.2 alias, and 1D.3 returned callable registrations are exact.
- F: two caller anchors register independently to one parameter and one lexical invocation.
- G: non-callable input produces no registration while the lexical invocation remains.
- H: imported, attribute, reflection, and container sources produce no registration.
- I: rebinding replaces the frame occurrence, so neither callback relation is emitted.
- J: an uninvoked parameter produces neither callback relation.
- K: `*args` and `**kwargs` transfers produce no registration.
- L–M: async-function and lambda owners compose; no coroutine-return specialization was added.
- N: callback invocation arguments are not bound to the actual callback signature.
- O: existing local callable result remains `CALL_EXACT`; callback facts are additive.

## Verification

- `tests/analysis/test_lineage_extraction.py -q`: 161 passed.
- `tests/analysis/test_lineage_extraction_equivalence.py -q`: 2 passed; immutable oracle unchanged.
- Combined requested suite (`lineage`, equivalence, `test_no_double_parse`, `test_index_fusion`): 174 passed.
- `git diff --check`: passed (only Git CRLF advisory warnings).
- Contextor MCP pre-edit LIVE revision: 575. Desktop watcher published production edits at revisions 576–579 and test edit at 580. After LIVE restoration, `get_live_events(after_revision=575)` reports revision 581, `status=ok`, `continuity=continuous`, and `resync_required=false`.
- All three changed production modules are LIVE revision 581 with `syntax_diagnostics.status=checked_and_none`, availability `fresh`, no warnings, no cycles, and no collisions (0 for the state module; collision family fresh).
- The active facade still has exactly one `LineageExtractionState()` construction and exactly one dynamic `getattr(self, f"_visit_{type(node).__name__}", None)` dispatch. Textual verification found no `ast.walk` or `NodeVisitor` in the changed helpers; no helper imports the facade.
- Deferred layer evidence: the Contextor analysis layer reports 33 modules, fresh syntax/cycle diagnostics, no clusters, and pre-existing cross-boundary-edge evidence only (not policy violations).

## Files changed

- `contextor/core/analysis/lineage_extraction_state.py`
- `contextor/core/analysis/lineage_extraction_calls.py`
- `contextor/core/analysis/lineage_extraction_visitors.py`
- `tests/analysis/test_lineage_extraction.py`

## COMPLETE raw unified full diff relative to `0f172abad9d2ae3d34f58bf0ad2b646f7ed86d99`

```diff
diff --git a/contextor/core/analysis/lineage_extraction_calls.py b/contextor/core/analysis/lineage_extraction_calls.py
index 78a5d59..2eaaf36 100644
--- a/contextor/core/analysis/lineage_extraction_calls.py
+++ b/contextor/core/analysis/lineage_extraction_calls.py
@@ -48,13 +48,16 @@ def collect_call_arguments(state: LineageExtractionState, paths: dict[int, str],
     pending.sort(key=lambda item: (int(getattr(item[0], "lineno", 0) or 0), int(getattr(item[0], "col_offset", 0) or 0), item[3]))
     result = []
     for ordinal, (argument_node, kind, keyword_name, _source_ordinal) in enumerate(pending):
-        value(argument_node, owner, walrus_owner)
-        result.append(_CallArgumentInfo(occurrence(state, paths,"call_argument", argument_node, keyword_name if kind == "keyword" else None, ordinal=ordinal), argument_node, kind, keyword_name))
+        source = value(argument_node, owner, walrus_owner)
+        result.append(_CallArgumentInfo(occurrence(state, paths,"call_argument", argument_node, keyword_name if kind == "keyword" else None, ordinal=ordinal), source, argument_node, kind, keyword_name))
     return tuple(result)


 def emit_argument_to_parameter(state: LineageExtractionState, paths: dict[int, str], module_name: str, argument: _CallArgumentInfo, callable_info: _CallableInfo, parameter: _ParameterInfo) -> None:
     emit_flow(state, paths,source=argument.occurrence, target=parameter_symbolic(module_name,callable_info.name, parameter), relation=LineageRelation.ARGUMENT_TO_PARAMETER, node=argument.node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
+    actual_callable = state._callable_values.get(argument.source.local_id)
+    if parameter.local_id in state._callback_parameters and actual_callable is not None:
+        emit_flow(state, paths,source=ExtractedOccurrenceRef(actual_callable.anchor_id), target=parameter_symbolic(module_name,callable_info.name, parameter), relation=LineageRelation.CALLBACK_REGISTERS, node=argument.node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
 
 
 def bind_call_arguments(state: LineageExtractionState, paths: dict[int, str], module_name: str, arguments: tuple[_CallArgumentInfo, ...], callable_info: _CallableInfo) -> None:
@@ -106,6 +109,7 @@ def parameter_anchors(state: LineageExtractionState, paths: dict[int, str], modu
             local_id = add_anchor(state, paths,"parameter", parameter, parameter.arg, owner, ordinal=ordinal if kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD) else 0, local_kind=local_kind)
             state.declare_local(owner, parameter.arg)
             info = _ParameterInfo(local_id, parameter.arg, kind, ordinal if kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD) else 0)
+            state.register_parameter(owner, info)
             result.append((info, parameter))
     for ordinal, (info, parameter) in enumerate(result):
         emit_flow(state, paths,source=parameter_symbolic(module_name,callable_symbol_name, info), target=ExtractedOccurrenceRef(info.local_id), relation=LineageRelation.BINDS, node=parameter, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
diff --git a/contextor/core/analysis/lineage_extraction_state.py b/contextor/core/analysis/lineage_extraction_state.py
index 82449d6..3727043 100644
--- a/contextor/core/analysis/lineage_extraction_state.py
+++ b/contextor/core/analysis/lineage_extraction_state.py
@@ -46,6 +46,7 @@ class _ActiveComprehension:
 @dataclass(frozen=True)
 class _CallArgumentInfo:
     occurrence: ExtractedOccurrenceRef
+    source: ExtractedOccurrenceRef
     node: ast.AST
     kind: str
     keyword_name: str | None
@@ -71,6 +72,8 @@ class LineageExtractionState:
     _callables_by_anchor: dict[str, _CallableInfo] = field(default_factory=dict)
     _callables_by_binding: dict[str, _CallableInfo] = field(default_factory=dict)
     _callable_values: dict[str, _CallableInfo] = field(default_factory=dict)
+    _parameters_by_local_id: dict[str, tuple[str, _ParameterInfo]] = field(default_factory=dict)
+    _callback_parameters: set[str] = field(default_factory=set)
     _return_records: dict[str, list[_CallableReturnRecord]] = field(default_factory=dict)
     _callable_returns: dict[str, _CallableInfo] = field(default_factory=dict)
     _generator_owners: set[str] = field(default_factory=set)
@@ -115,6 +118,26 @@ class LineageExtractionState:
     def import_frame(self, owner: str | None) -> dict[str, _ImportInfo]:
         return self._imports.setdefault(owner, {})
 
+    def register_parameter(self, owner: str, parameter: _ParameterInfo) -> None:
+        candidate = (owner, parameter)
+        existing = self._parameters_by_local_id.get(parameter.local_id)
+        if existing is not None and existing != candidate:
+            raise ValueError(f"Conflicting lineage parameter registration: {parameter.local_id}")
+        self._parameters_by_local_id[parameter.local_id] = candidate
+
+    def current_parameter(
+        self,
+        owner: str | None,
+        occurrence: ExtractedOccurrenceRef | None,
+    ) -> _ParameterInfo | None:
+        if owner is None or occurrence is None:
+            return None
+        registered = self._parameters_by_local_id.get(occurrence.local_id)
+        return registered[1] if registered is not None and registered[0] == owner else None
+
+    def mark_callback_parameter(self, parameter: _ParameterInfo) -> None:
+        self._callback_parameters.add(parameter.local_id)
+
     def record_callable_return(
         self,
         owner: str | None,
diff --git a/contextor/core/analysis/lineage_extraction_visitors.py b/contextor/core/analysis/lineage_extraction_visitors.py
index 64bdab9..5d1b18f 100644
--- a/contextor/core/analysis/lineage_extraction_visitors.py
+++ b/contextor/core/analysis/lineage_extraction_visitors.py
@@ -18,6 +18,7 @@ from contextor.core.analysis.lineage_extraction_emit import (
     add_anchor,
     emit_flow,
     occurrence,
+    parameter_symbolic,
     return_symbolic,
 )
 from contextor.core.analysis.lineage_extraction_state import (
@@ -28,6 +29,7 @@ from contextor.core.domain.lineage_facts import (
     ExtractedOccurrenceRef,
     LineageConfidence,
     LineageRelation,
+    ParameterKind,
     ResolutionKind,
 )
 
@@ -320,6 +322,25 @@ def visit_call(
         "call_result",
         node,
     )
+    parameter = state.current_parameter(owner, callee_ref)
+    enclosing_callable = state._callables_by_anchor.get(owner) if owner is not None else None
+    if (
+        isinstance(node.func, ast.Name)
+        and parameter is not None
+        and enclosing_callable is not None
+        and parameter.kind not in (ParameterKind.VAR_POSITIONAL, ParameterKind.VAR_KEYWORD)
+    ):
+        state.mark_callback_parameter(parameter)
+        emit_flow(
+            state,
+            paths,
+            source=parameter_symbolic(module_name, enclosing_callable.name, parameter),
+            target=call_site,
+            relation=LineageRelation.CALLBACK_INVOKES,
+            node=node,
+            resolution_kind=ResolutionKind.LEXICAL_EXACT,
+            confidence=LineageConfidence.CONFIRMED,
+        )
     arguments = collect_call_arguments(
         state,
         paths,
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index 692ed4f..bcfe909 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -1915,3 +1915,111 @@ def test_stage_1d3_yield_from_marks_only_nested_callable_owner():
     flow = _stage_1d3_final_call(facts)
     assert flow.resolution_kind is ResolutionKind.CALL_EXACT
     assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name == "f"
+
+
+def _stage_1d4_flows(facts, relation):
+    return [flow for flow in facts.flows if flow.relation is relation]
+
+
+def test_stage_1d4_a_callback_path_is_composable_and_call_result_stays_dynamic():
+    source = "def apply(callback):\n return callback()\ndef f(): return 1\napply(f)\n"
+    tree = ast.parse(source)
+    callback_call = tree.body[0].body[0].value
+    paths, reason = lineage_extraction_module._index_ast_paths(tree, lineage_extraction_module.DEFAULT_LINEAGE_EXTRACTION_LIMITS)
+    assert reason is None and isinstance(callback_call, ast.Call)
+    facts = _stage_1c_facts(source)
+    callback = _stage_1c_named(facts, "parameter", "callback")[0]
+    function = _stage_1c_named(facts, "function", "f")[0]
+    registers = _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)
+    invokes = _stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)
+    assert len(registers) == len(invokes) == 1
+    assert registers[0].source == ExtractedOccurrenceRef(function.local_id)
+    assert isinstance(registers[0].target, ExtractedSymbolicRef) and registers[0].target.source_local_id == callback.local_id
+    assert isinstance(invokes[0].source, ExtractedSymbolicRef) and invokes[0].source.source_local_id == callback.local_id
+    assert invokes[0].target == ExtractedOccurrenceRef(build_local_occurrence_id("call_site", paths[id(callback_call)]))
+    callback_result = next(flow for flow in _stage_1c_call_result_flows(facts) if flow.evidence.start_line == 2)
+    assert callback_result.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+
+
+def test_stage_1d4_b_keyword_callback_registers_exactly():
+    facts = _stage_1c_facts("def apply(callback): callback()\ndef f(): pass\napply(callback=f)\n")
+    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)) == 1
+
+
+def test_stage_1d4_c_lambda_callback_registers_lambda_anchor():
+    facts = _stage_1c_facts("def apply(callback): callback()\napply(lambda: 1)\n")
+    flow = _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)[0]
+    assert flow.source == ExtractedOccurrenceRef(_stage_1c_named(facts, "lambda", None)[0].local_id)
+
+
+def test_stage_1d4_d_callable_alias_registers_original_anchor():
+    facts = _stage_1c_facts("def apply(callback): callback()\ndef f(): pass\ng=f\napply(g)\n")
+    flow = _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)[0]
+    assert flow.source == ExtractedOccurrenceRef(_stage_1c_named(facts, "function", "f")[0].local_id)
+
+
+def test_stage_1d4_e_returned_callable_registers_original_anchor():
+    facts = _stage_1c_facts("def apply(callback): callback()\ndef factory():\n def f(): pass\n return f\napply(factory())\n")
+    flow = _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)[0]
+    assert flow.source == ExtractedOccurrenceRef(_stage_1c_named(facts, "function", "f")[0].local_id)
+
+
+def test_stage_1d4_f_multiple_callers_register_independently_to_one_invocation():
+    facts = _stage_1c_facts("def apply(callback): callback()\ndef f(): pass\ndef g(): pass\napply(f)\napply(g)\n")
+    registers = _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)
+    assert {flow.source.local_id for flow in registers} == {item.local_id for item in _stage_1c_named(facts, "function", "f") + _stage_1c_named(facts, "function", "g")}
+    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)) == 1
+    assert next(flow for flow in _stage_1c_call_result_flows(facts) if flow.evidence.start_line == 1).resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+
+
+def test_stage_1d4_g_non_callable_argument_has_only_lexical_invocation():
+    facts = _stage_1c_facts("def apply(callback): callback()\napply(42)\n")
+    assert not _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)
+    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)) == 1
+
+
+@pytest.mark.parametrize("source", ("from pkg import f\ndef apply(callback): callback()\napply(f)\n", "def apply(callback): callback()\napply(obj.f)\n", "def apply(callback): callback()\napply([f][0])\n", "def apply(callback): callback()\napply(getattr(obj, 'f'))\n"))
+def test_stage_1d4_h_imported_attribute_reflection_and_container_callbacks_do_not_register(source):
+    assert not _stage_1d4_flows(_stage_1c_facts(source), LineageRelation.CALLBACK_REGISTERS)
+
+
+def test_stage_1d4_i_rebound_parameter_is_not_callback_invocation_or_registration():
+    facts = _stage_1c_facts("def apply(callback):\n callback=other\n callback()\ndef f(): pass\napply(f)\n")
+    assert not _stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)
+    assert not _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)
+
+
+def test_stage_1d4_j_uninvoked_parameter_does_not_register_callback():
+    facts = _stage_1c_facts("def store(callback): return 1\ndef f(): pass\nstore(f)\n")
+    assert not _stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)
+    assert not _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)
+
+
+def test_stage_1d4_k_starred_and_double_starred_arguments_do_not_register():
+    facts = _stage_1c_facts("def apply(callback): callback()\ndef f(): pass\napply(*[f])\napply(**{'callback': f})\n")
+    assert not _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)
+
+
+def test_stage_1d4_l_async_callback_owner_composes_without_coroutine_specialization():
+    facts = _stage_1c_facts("async def apply(callback): callback()\ndef f(): pass\napply(f)\n")
+    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)) == 1
+    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)) == 1
+
+
+def test_stage_1d4_m_lambda_callback_owner_composes():
+    facts = _stage_1c_facts("apply=lambda callback: callback()\ndef f(): pass\napply(f)\n")
+    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)) == 1
+    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)) == 1
+
+
+def test_stage_1d4_n_callback_arguments_are_not_bound_to_actual_callable_signature():
+    facts = _stage_1c_facts("def apply(callback): callback(1)\ndef f(value): pass\napply(f)\n")
+    invokes = _stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)
+    assert len(invokes) == 1
+    assert not [flow for flow in _stage_1d4_flows(facts, LineageRelation.ARGUMENT_TO_PARAMETER) if flow.evidence.start_line == 1]
+
+
+def test_stage_1d4_o_existing_callable_facts_remain_and_callback_relations_are_additive():
+    facts = _stage_1c_facts("def apply(callback): callback()\ndef f(): return 1\ng=f\napply(g)\nresult=g()\n")
+    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)) == 1
+    assert _stage_1c_call_result_flows(facts)[-1].resolution_kind is ResolutionKind.CALL_EXACT
```

# F2L D1H Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/domain/lineage_facts.py`
- `contextor/core/analysis/lineage_extraction_emit.py`
- `contextor/core/analysis/lineage_extraction_bindings.py`
- `contextor/core/analysis/lineage_extraction_calls.py`
- `contextor/core/analysis/lineage_extraction_control.py`
- `contextor/core/analysis/lineage_extraction_visitors.py`
- `contextor/core/analysis/lineage_materialization.py`
- `contextor/core/live_state/store.py`
- `tests/analysis/test_lineage_extraction.py`
- `tests/analysis/test_lineage_materialization.py`
- `tests/test_lineage_state_lifecycle.py`

`walkthrough.md` is deliberately excluded from ACTUAL_DIFF.

## FLOW_OWNER_CONTRACT

Extracted and materialized flows carry `owner_local_id`. Extraction supplies it at every production emission site; materialization and re-resolution only copy it. A materialized flow owner must identify an anchor in the same slice. With `flow_ownership_materialized=True`, no flow may lack an owner.

## EXACT_17_CALLSITE_PROOF

`rg "emit_flow\\(" contextor/core/analysis -g lineage_extraction_bindings.py -g lineage_extraction_calls.py -g lineage_extraction_control.py -g lineage_extraction_visitors.py` reported exactly 17 direct production callsites. Each explicitly supplies `owner_local_id=...`; the emitter has no default for that parameter.

## DEFAULT_OWNER_PROOF

The extraction regression asserts defaults belong to the defining outer owner, parameter binding belongs to the callable owner, and return flow belongs to that callable owner.

## CAPTURE_OWNER_PROOF

Capture finalization continues to resolve its lexical cell from the captured binding owner, while assigning the emitted CAPTURES flow to the consuming request owner. The extraction regression verifies the nested function owner.

## LEGACY_FAIL_CLOSED

The semantic version is unchanged. Snapshot hydration maps missing flow fields to `owner_local_id=None` and `flow_ownership_materialized=False`; it performs no source or AST work. Query, service, backend, index, MCP, and docs were not modified.

## TESTS_RUN

- `./.venv/Scripts/python.exe -m py_compile` for all eight changed production files: PASS.
- `./.venv/Scripts/python.exe -m pytest -q tests/analysis/test_lineage_extraction.py tests/analysis/test_lineage_materialization.py tests/test_lineage_state_lifecycle.py`: PASS — 252 passed in 10.56s.
- Direct production `emit_flow` callsite count: PASS — 17.
- `git diff --check` for all task files: PASS (only CRLF conversion warnings).

## ACTUAL_DIFF

### contextor/core/domain/lineage_facts.py

```diff
diff --git a/contextor/core/domain/lineage_facts.py b/contextor/core/domain/lineage_facts.py
index f736fe4..40d66cb 100644
--- a/contextor/core/domain/lineage_facts.py
+++ b/contextor/core/domain/lineage_facts.py
@@ -275,11 +275,14 @@ class ExtractedFlowFact:
     confidence: LineageConfidence
     dynamic_boundary: str | None = None
     provider: ProviderRef | None = None
+    owner_local_id: str | None = None

     def __post_init__(self) -> None:
         _require_token(self.local_id, "local_id")
         if not isinstance(self.source, (ExtractedOccurrenceRef, ExtractedSymbolicRef)) or not isinstance(self.target, (ExtractedOccurrenceRef, ExtractedSymbolicRef)):
             raise TypeError("Extracted flow endpoints must be extracted occurrence or symbolic references.")
+        if self.owner_local_id is not None:
+            _require_token(self.owner_local_id, "owner_local_id")
         _validate_confidence(self.resolution_kind, self.confidence)
         _validate_dynamic_boundary(self.resolution_kind, self.confidence, self.dynamic_boundary)
         _validate_provider(self.provider)
@@ -377,9 +380,12 @@ class MaterializedFlowFact:
     confidence: LineageConfidence
     dynamic_boundary: str | None = None
     provider: ProviderRef | None = None
+    owner_local_id: str | None = None

     def __post_init__(self) -> None:
         _require_token(self.local_id, "local_id")
+        if self.owner_local_id is not None:
+            _require_token(self.owner_local_id, "owner_local_id")
         _require_materialized_reference(self.source, "Materialized flow source")
         _require_materialized_reference(self.target, "Materialized flow target")
         if isinstance(self.source, MaterializedOccurrenceRef) and isinstance(self.target, MaterializedOccurrenceRef):
@@ -430,6 +436,7 @@ class SourceLineageManifest:
     resource_limit_reason: str | None = None
     semantic_anchor_bindings_materialized: bool = False
     anchor_ownership_materialized: bool = False
+    flow_ownership_materialized: bool = False

     def __post_init__(self) -> None:
         _require_token(self.source_key, "source_key")
@@ -443,6 +450,8 @@ class SourceLineageManifest:
             )
         if not isinstance(self.anchor_ownership_materialized, bool):
             raise TypeError("anchor_ownership_materialized must be boolean.")
+        if not isinstance(self.flow_ownership_materialized, bool):
+            raise TypeError("flow_ownership_materialized must be boolean.")
         _validate_source_status(self.status, self.resource_limit_reason)


@@ -526,6 +535,20 @@ class MaterializedLineageSourceFacts:
         for flow in self.flows:
             _require_slice_occurrence(flow.source, self.manifest)
             _require_slice_occurrence(flow.target, self.manifest)
+            if (
+                flow.owner_local_id is not None
+                and flow.owner_local_id not in anchor_ids
+            ):
+                raise ValueError(
+                    "Materialized flow owner must reference an anchor in its slice."
+                )
+            if (
+                self.manifest.flow_ownership_materialized
+                and flow.owner_local_id is None
+            ):
+                raise ValueError(
+                    "Materialized flow ownership is incomplete."
+                )
         for surface in self.surfaces:
             _require_slice_occurrence(surface.exposed, self.manifest)
         anchor_references = {anchor.reference for anchor in self.anchors}
```

### contextor/core/analysis/lineage_extraction_emit.py

```diff
diff --git a/contextor/core/analysis/lineage_extraction_emit.py b/contextor/core/analysis/lineage_extraction_emit.py
index 13a5433..8c5d160 100644
--- a/contextor/core/analysis/lineage_extraction_emit.py
+++ b/contextor/core/analysis/lineage_extraction_emit.py
@@ -31,11 +31,37 @@ def occurrence(state: LineageExtractionState, paths: dict[int, str], kind: str,
     return result


-def emit_flow(state: LineageExtractionState, paths: dict[int, str], *, source, target, relation: LineageRelation, node: ast.AST, resolution_kind: ResolutionKind, confidence: LineageConfidence, ordinal: int = 0, dynamic_boundary: str | None = None) -> None:
+def emit_flow(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    *,
+    source,
+    target,
+    relation: LineageRelation,
+    node: ast.AST,
+    resolution_kind: ResolutionKind,
+    confidence: LineageConfidence,
+    owner_local_id: str | None,
+    ordinal: int = 0,
+    dynamic_boundary: str | None = None,
+) -> None:
     local_id = f"flow:v1:{relation.value}:{paths[id(node)]}:i:{ordinal}"
-    if local_id in state._flow_ids: raise ValueError(f"Duplicate lineage flow id: {local_id}")
+    if local_id in state._flow_ids:
+        raise ValueError(f"Duplicate lineage flow id: {local_id}")
     state._flow_ids.add(local_id)
-    state.flows.append(ExtractedFlowFact(local_id, source, target, relation, _source_span(node), resolution_kind, confidence, dynamic_boundary=dynamic_boundary))
+    state.flows.append(
+        ExtractedFlowFact(
+            local_id,
+            source,
+            target,
+            relation,
+            _source_span(node),
+            resolution_kind,
+            confidence,
+            dynamic_boundary=dynamic_boundary,
+            owner_local_id=owner_local_id,
+        )
+    )


 def emit_surface(state: LineageExtractionState, paths: dict[int, str], *, kind: SurfaceKind, exposed, node: ast.AST, declared_name: str, resolution_kind: ResolutionKind, confidence: LineageConfidence, declaration_evidence: SurfaceDeclarationEvidence, ordinal: int = 0) -> None:
```

### contextor/core/analysis/lineage_extraction_bindings.py

```diff
diff --git a/contextor/core/analysis/lineage_extraction_bindings.py b/contextor/core/analysis/lineage_extraction_bindings.py
index f356ed5..1810739 100644
--- a/contextor/core/analysis/lineage_extraction_bindings.py
+++ b/contextor/core/analysis/lineage_extraction_bindings.py
@@ -62,6 +62,7 @@ def visit_name(
             node=node,
             resolution_kind=ResolutionKind.LEXICAL_EXACT,
             confidence=LineageConfidence.CONFIRMED,
+            owner_local_id=owner,
         )


@@ -98,6 +99,7 @@ def assign_target(
         node=target,
         resolution_kind=ResolutionKind.LEXICAL_EXACT,
         confidence=LineageConfidence.CONFIRMED,
+        owner_local_id=owner,
     )
     return binding

@@ -136,6 +138,7 @@ def runtime_bind_target(
             node=target,
             resolution_kind=ResolutionKind.LEXICAL_EXACT,
             confidence=LineageConfidence.CONFIRMED,
+            owner_local_id=owner,
         )
         return
     if isinstance(target, (ast.Tuple, ast.List)):
@@ -281,6 +284,7 @@ def visit_aug_assign(
             node=node.target,
             resolution_kind=ResolutionKind.LEXICAL_EXACT,
             confidence=LineageConfidence.CONFIRMED,
+            owner_local_id=owner,
         )
     value(node.value, owner, walrus_owner)
     binding = ExtractedOccurrenceRef(
@@ -376,16 +380,22 @@ def finalize_captures(
     for request in sorted(
         state._capture_requests.values(), key=lambda item: item.load.local_id
     ):
-        owner = state.resolve_capture_owner(request.owner, request.name)
-        if owner is None:
+        capture_owner = state.resolve_capture_owner(request.owner, request.name)
+        if capture_owner is None:
             continue
         emit_flow(
             state,
             paths,
-            source=ensure_lexical_cell(state, paths, owner, request.name),
+            source=ensure_lexical_cell(
+                state,
+                paths,
+                capture_owner,
+                request.name,
+            ),
             target=request.load,
             relation=LineageRelation.CAPTURES,
             node=request.node,
             resolution_kind=ResolutionKind.LEXICAL_EXACT,
             confidence=LineageConfidence.CONFIRMED,
+            owner_local_id=request.owner,
         )
```

### contextor/core/analysis/lineage_extraction_calls.py

```diff
diff --git a/contextor/core/analysis/lineage_extraction_calls.py b/contextor/core/analysis/lineage_extraction_calls.py
index 0e7c5bb..2606a1b 100644
--- a/contextor/core/analysis/lineage_extraction_calls.py
+++ b/contextor/core/analysis/lineage_extraction_calls.py
@@ -54,14 +54,14 @@ def collect_call_arguments(state: LineageExtractionState, paths: dict[int, str],
     return tuple(result)


-def emit_argument_to_parameter(state: LineageExtractionState, paths: dict[int, str], module_name: str, argument: _CallArgumentInfo, callable_info: _CallableInfo, parameter: _ParameterInfo) -> None:
-    emit_flow(state, paths,source=argument.occurrence, target=parameter_symbolic(module_name,callable_info.name, parameter), relation=LineageRelation.ARGUMENT_TO_PARAMETER, node=argument.node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
+def emit_argument_to_parameter(state: LineageExtractionState, paths: dict[int, str], module_name: str, argument: _CallArgumentInfo, callable_info: _CallableInfo, parameter: _ParameterInfo, *, owner_local_id: str | None) -> None:
+    emit_flow(state, paths,source=argument.occurrence, target=parameter_symbolic(module_name,callable_info.name, parameter), relation=LineageRelation.ARGUMENT_TO_PARAMETER, node=argument.node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED, owner_local_id=owner_local_id)
     actual_callable = state._callable_values.get(argument.source.local_id)
     if parameter.local_id in state._callback_parameters and actual_callable is not None:
-        emit_flow(state, paths,source=ExtractedOccurrenceRef(actual_callable.anchor_id), target=parameter_symbolic(module_name,callable_info.name, parameter), relation=LineageRelation.CALLBACK_REGISTERS, node=argument.node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
+        emit_flow(state, paths,source=ExtractedOccurrenceRef(actual_callable.anchor_id), target=parameter_symbolic(module_name,callable_info.name, parameter), relation=LineageRelation.CALLBACK_REGISTERS, node=argument.node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED, owner_local_id=owner_local_id)


-def bind_call_arguments(state: LineageExtractionState, paths: dict[int, str], module_name: str, arguments: tuple[_CallArgumentInfo, ...], callable_info: _CallableInfo) -> None:
+def bind_call_arguments(state: LineageExtractionState, paths: dict[int, str], module_name: str, arguments: tuple[_CallArgumentInfo, ...], callable_info: _CallableInfo, *, owner_local_id: str | None) -> None:
     fixed = tuple(p for p in callable_info.parameters if p.kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD))
     keywords = {p.name: p for p in callable_info.parameters if p.kind in (ParameterKind.POSITIONAL_OR_KEYWORD, ParameterKind.KEYWORD_ONLY)}
     vararg = next((p for p in callable_info.parameters if p.kind is ParameterKind.VAR_POSITIONAL), None)
@@ -73,14 +73,14 @@ def bind_call_arguments(state: LineageExtractionState, paths: dict[int, str], mo
         if argument.kind == "positional":
             if uncertain: continue
             if index < len(fixed):
-                parameter = fixed[index]; index += 1; consumed.add(parameter.local_id); emit_argument_to_parameter(state, paths, module_name,argument, callable_info, parameter)
-            elif vararg is not None: emit_argument_to_parameter(state, paths, module_name,argument, callable_info, vararg)
+                parameter = fixed[index]; index += 1; consumed.add(parameter.local_id); emit_argument_to_parameter(state, paths, module_name,argument, callable_info, parameter, owner_local_id=owner_local_id)
+            elif vararg is not None: emit_argument_to_parameter(state, paths, module_name,argument, callable_info, vararg, owner_local_id=owner_local_id)
             continue
         if argument.kind == "keyword" and argument.keyword_name is not None:
             parameter = keywords.get(argument.keyword_name)
             if parameter is not None and parameter.local_id not in consumed:
-                consumed.add(parameter.local_id); emit_argument_to_parameter(state, paths, module_name,argument, callable_info, parameter)
-            elif parameter is None and varkw is not None: emit_argument_to_parameter(state, paths, module_name,argument, callable_info, varkw)
+                consumed.add(parameter.local_id); emit_argument_to_parameter(state, paths, module_name,argument, callable_info, parameter, owner_local_id=owner_local_id)
+            elif parameter is None and varkw is not None: emit_argument_to_parameter(state, paths, module_name,argument, callable_info, varkw, owner_local_id=owner_local_id)

 def function_signature_evidence(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
     args = node.args
@@ -113,17 +113,17 @@ def parameter_anchors(state: LineageExtractionState, paths: dict[int, str], modu
             state.register_parameter(owner, info)
             result.append((info, parameter))
     for ordinal, (info, parameter) in enumerate(result):
-        emit_flow(state, paths,source=parameter_symbolic(module_name,callable_symbol_name, info), target=ExtractedOccurrenceRef(info.local_id), relation=LineageRelation.BINDS, node=parameter, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
+        emit_flow(state, paths,source=parameter_symbolic(module_name,callable_symbol_name, info), target=ExtractedOccurrenceRef(info.local_id), relation=LineageRelation.BINDS, node=parameter, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, owner_local_id=owner, ordinal=ordinal)
     return tuple(info for info, _parameter in result)


-def default_flows(state: LineageExtractionState, paths: dict[int, str], module_name: str, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, callable_symbol_name: str, parameters: tuple[_ParameterInfo, ...]) -> None:
+def default_flows(state: LineageExtractionState, paths: dict[int, str], module_name: str, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, callable_symbol_name: str, parameters: tuple[_ParameterInfo, ...], *, owner_local_id: str | None) -> None:
     positional_parameters = tuple(parameter for parameter in parameters if parameter.kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD))
     positional_defaults = tuple(node.args.defaults)
     if positional_defaults:
         for ordinal, (default, parameter) in enumerate(zip(positional_defaults, positional_parameters[-len(positional_defaults) :])):
-            emit_flow(state, paths,source=occurrence(state, paths,"expression_result", default), target=parameter_symbolic(module_name,callable_symbol_name, parameter), relation=LineageRelation.DEFAULTS_TO_PARAMETER, node=default, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
+            emit_flow(state, paths,source=occurrence(state, paths,"expression_result", default), target=parameter_symbolic(module_name,callable_symbol_name, parameter), relation=LineageRelation.DEFAULTS_TO_PARAMETER, node=default, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, owner_local_id=owner_local_id, ordinal=ordinal)
     kwonly_parameters = tuple(parameter for parameter in parameters if parameter.kind is ParameterKind.KEYWORD_ONLY)
     for ordinal, (default, parameter) in enumerate(zip(node.args.kw_defaults, kwonly_parameters)):
         if default is not None:
-            emit_flow(state, paths,source=occurrence(state, paths,"expression_result", default), target=parameter_symbolic(module_name,callable_symbol_name, parameter), relation=LineageRelation.DEFAULTS_TO_PARAMETER, node=default, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
+            emit_flow(state, paths,source=occurrence(state, paths,"expression_result", default), target=parameter_symbolic(module_name,callable_symbol_name, parameter), relation=LineageRelation.DEFAULTS_TO_PARAMETER, node=default, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, owner_local_id=owner_local_id, ordinal=ordinal)
```

### contextor/core/analysis/lineage_extraction_control.py

```diff
diff --git a/contextor/core/analysis/lineage_extraction_control.py b/contextor/core/analysis/lineage_extraction_control.py
index 61ba673..14050cb 100644
--- a/contextor/core/analysis/lineage_extraction_control.py
+++ b/contextor/core/analysis/lineage_extraction_control.py
@@ -122,7 +122,17 @@ def visit_except_handler(state: LineageExtractionState, paths: dict[int, str], n
             source = occurrence(state, paths, "runtime_bound_local", node, alias_name)
             state.frame(owner)[alias_name] = binding
             state.note_module_all_touch(owner, alias_name)
-            emit_flow(state, paths, source=source, target=binding, relation=LineageRelation.ASSIGNS, node=node, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
+            emit_flow(
+                state,
+                paths,
+                source=source,
+                target=binding,
+                relation=LineageRelation.ASSIGNS,
+                node=node,
+                resolution_kind=ResolutionKind.LEXICAL_EXACT,
+                confidence=LineageConfidence.CONFIRMED,
+                owner_local_id=owner,
+            )
     for child in node.body:
         visit(child, owner, walrus_owner)
     exit_frame = state.clone_frame(owner)
```

### contextor/core/analysis/lineage_extraction_visitors.py

```diff
diff --git a/contextor/core/analysis/lineage_extraction_visitors.py b/contextor/core/analysis/lineage_extraction_visitors.py
index 8a26c16..2d23ac1 100644
--- a/contextor/core/analysis/lineage_extraction_visitors.py
+++ b/contextor/core/analysis/lineage_extraction_visitors.py
@@ -137,6 +137,7 @@ def visit_function(
         node,
         node.name,
         parameters,
+        owner_local_id=owner,
     )
     callable_info = _CallableInfo(
         node.name,
@@ -202,6 +203,7 @@ def visit_lambda(
         node,
         callable_symbol_name,
         parameters,
+        owner_local_id=owner,
     )
     callable_info = _CallableInfo(
         callable_symbol_name,
@@ -224,6 +226,7 @@ def visit_lambda(
         node=node.body,
         resolution_kind=ResolutionKind.LEXICAL_EXACT,
         confidence=LineageConfidence.CONFIRMED,
+        owner_local_id=lambda_id,
     )
     state.publish_lambda_callable_return(lambda_id, body_source)
     lambda_value = occurrence(
@@ -266,6 +269,7 @@ def visit_return(
             node=node,
             resolution_kind=ResolutionKind.LEXICAL_EXACT,
             confidence=LineageConfidence.CONFIRMED,
+            owner_local_id=owner,
         )
     state.record_callable_return(owner, node, returned_callable)

@@ -350,6 +354,7 @@ def visit_call(
             node=node,
             resolution_kind=ResolutionKind.LEXICAL_EXACT,
             confidence=LineageConfidence.CONFIRMED,
+            owner_local_id=owner,
         )
     arguments = collect_call_arguments(
         state,
@@ -366,6 +371,7 @@ def visit_call(
             module_name,
             arguments,
             callable_info,
+            owner_local_id=owner,
         )
         emit_flow(
             state,
@@ -376,6 +382,7 @@ def visit_call(
             node=node,
             resolution_kind=ResolutionKind.CALL_EXACT,
             confidence=LineageConfidence.CONFIRMED,
+            owner_local_id=owner,
         )
         returned_callable = state._callable_returns.get(callable_info.anchor_id)
         if returned_callable is not None:
@@ -391,6 +398,7 @@ def visit_call(
             node=node,
             resolution_kind=ResolutionKind.IMPORT_EXACT,
             confidence=LineageConfidence.CONFIRMED,
+            owner_local_id=owner,
         )
         return
     if isinstance(node.func, ast.Name) and callee_ref is None:
@@ -411,6 +419,7 @@ def visit_call(
         resolution_kind=resolution_kind,
         confidence=confidence,
         dynamic_boundary=dynamic_boundary,
+        owner_local_id=owner,
     )
```

### contextor/core/analysis/lineage_materialization.py

```diff
diff --git a/contextor/core/analysis/lineage_materialization.py b/contextor/core/analysis/lineage_materialization.py
index 789b901..502b825 100644
--- a/contextor/core/analysis/lineage_materialization.py
+++ b/contextor/core/analysis/lineage_materialization.py
@@ -166,6 +166,7 @@ def materialize_lineage_source_facts(
             flow.confidence,
             flow.dynamic_boundary,
             flow.provider,
+            flow.owner_local_id,
         )
         for flow in extracted.flows
     ))
@@ -190,6 +191,10 @@ def materialize_lineage_source_facts(
         )
         for surface in extracted.surfaces
     ))
+    flow_ownership_materialized = all(
+        flow.owner_local_id is not None
+        for flow in extracted.flows
+    )
     manifest = SourceLineageManifest(
         extracted.source_key,
         extracted.source_fingerprint,
@@ -201,6 +206,7 @@ def materialize_lineage_source_facts(
         extracted.resource_limit_reason,
         semantic_anchor_bindings_materialized=True,
         anchor_ownership_materialized=True,
+        flow_ownership_materialized=flow_ownership_materialized,
     )
     return MaterializedLineageSourceFacts(
         manifest,
@@ -307,6 +313,7 @@ def reresolve_materialized_lineage_source_facts(
             flow.confidence,
             flow.dynamic_boundary,
             flow.provider,
+            flow.owner_local_id,
         )
         for flow in materialized.flows
     ))
```

### contextor/core/live_state/store.py

```diff
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 5915f47..b13fb03 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -157,6 +157,13 @@ def _revalidate_lineage_manifest(manifest: Any) -> SourceLineageManifest:
                 False,
             )
         ),
+        flow_ownership_materialized=bool(
+            getattr(
+                manifest,
+                "flow_ownership_materialized",
+                False,
+            )
+        ),
     )
     if rebuilt.semantic_version != LINEAGE_FACTS_SEMANTIC_VERSION:
         raise pickle.UnpicklingError(
@@ -191,6 +198,7 @@ def _revalidate_lineage_flow(flow: Any) -> MaterializedFlowFact:
         target=_revalidate_lineage_endpoint(flow.target),
         evidence=_revalidate_lineage_span(flow.evidence),
         provider=_revalidate_lineage_provider(flow.provider),
+        owner_local_id=getattr(flow, "owner_local_id", None),
     )
```

### tests/analysis/test_lineage_extraction.py

```diff
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index de2207e..b98527a 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -2190,3 +2190,51 @@ def test_stage_1e1_reading_all_subscript_preserves_exact_literal_authority():
     assert surface.declared_name == "a"
     assert surface.kind is SurfaceKind.EXPORT
     assert surface.confidence is LineageConfidence.CONFIRMED
+
+
+def test_flow_lexical_owner_separates_outer_and_nested_function_scopes():
+    facts = _stage_1c_facts(
+        "def outer(value):\n"
+        " x = value\n"
+        " def inner():\n"
+        "  y = x\n"
+        "  return y\n"
+        " result = inner()\n"
+        " return result\n"
+    )
+    outer = _stage_1c_named(facts, "function", "outer")[0]
+    inner = _stage_1c_named(facts, "function", "inner")[0]
+    outer_assign = next(flow for flow in facts.flows if flow.relation is LineageRelation.ASSIGNS and flow.evidence.start_line == 2)
+    inner_assign = next(flow for flow in facts.flows if flow.relation is LineageRelation.ASSIGNS and flow.evidence.start_line == 4)
+    inner_return = next(flow for flow in facts.flows if flow.relation is LineageRelation.RETURNS and flow.evidence.start_line == 5)
+    outer_call = next(flow for flow in facts.flows if flow.relation is LineageRelation.CALL_RESULT and flow.evidence.start_line == 6)
+    outer_return = next(flow for flow in facts.flows if flow.relation is LineageRelation.RETURNS and flow.evidence.start_line == 7)
+    assert outer_assign.owner_local_id == outer.local_id
+    assert inner_assign.owner_local_id == inner.local_id
+    assert inner_return.owner_local_id == inner.local_id
+    assert outer_call.owner_local_id == outer.local_id
+    assert outer_return.owner_local_id == outer.local_id
+
+
+def test_flow_lexical_owner_assigns_defaults_to_defining_scope():
+    facts = _stage_1c_facts("seed = 1\ndef outer(value=seed):\n return value\n")
+    module = next(anchor for anchor in facts.anchors if anchor.kind == "module")
+    outer = _stage_1c_named(facts, "function", "outer")[0]
+    default_flow = next(flow for flow in facts.flows if flow.relation is LineageRelation.DEFAULTS_TO_PARAMETER)
+    parameter_bind = next(flow for flow in facts.flows if flow.relation is LineageRelation.BINDS and isinstance(flow.target, ExtractedOccurrenceRef) and parse_local_occurrence_id(flow.target.local_id)[0] == "parameter_poskw")
+    return_flow = next(flow for flow in facts.flows if flow.relation is LineageRelation.RETURNS)
+    assert default_flow.owner_local_id == module.local_id
+    assert parameter_bind.owner_local_id == outer.local_id
+    assert return_flow.owner_local_id == outer.local_id
+
+
+def test_flow_lexical_owner_assigns_capture_to_consuming_scope():
+    facts = _stage_1c_facts(
+        "def outer(x):\n"
+        " def inner():\n"
+        "  return x\n"
+        " return inner\n"
+    )
+    inner = _stage_1c_named(facts, "function", "inner")[0]
+    capture = next(flow for flow in facts.flows if flow.relation is LineageRelation.CAPTURES)
+    assert capture.owner_local_id == inner.local_id
```

### tests/analysis/test_lineage_materialization.py

```diff
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
index 5006541..d0c3568 100644
--- a/tests/analysis/test_lineage_materialization.py
+++ b/tests/analysis/test_lineage_materialization.py
@@ -22,6 +22,7 @@ from contextor.core.domain.lineage_facts import (
     LineageRelation,
     LINEAGE_FACTS_SEMANTIC_VERSION,
     MaterializedAnchorFact,
+    MaterializedFlowFact,
     MaterializedLineageSourceFacts,
     MaterializedOccurrenceRef,
     MaterializedSymbolicRef,
@@ -62,9 +63,14 @@ def test_materializer_is_deterministic_and_preserves_local_anchors_and_flows():
         anchors=(ExtractedAnchorFact("anchor", "binding", span),),
         flows=(
             ExtractedFlowFact(
-                "flow", ExtractedOccurrenceRef("anchor"), ExtractedOccurrenceRef("use"),
-                LineageRelation.ASSIGNS, span, ResolutionKind.LEXICAL_EXACT,
+                "flow",
+                ExtractedOccurrenceRef("anchor"),
+                ExtractedOccurrenceRef("use"),
+                LineageRelation.ASSIGNS,
+                span,
+                ResolutionKind.LEXICAL_EXACT,
                 LineageConfidence.CONFIRMED,
+                owner_local_id="anchor",
             ),
         ),
     )
@@ -76,6 +82,8 @@ def test_materializer_is_deterministic_and_preserves_local_anchors_and_flows():
         "pkg/mod.py", "sha256:test", "anchor"
     )
     assert first.flows[0].resolution_kind is ResolutionKind.LEXICAL_EXACT
+    assert first.flows[0].owner_local_id == "anchor"
+    assert first.manifest.flow_ownership_materialized is True


 def test_materialized_slice_rejects_missing_or_cyclic_anchor_owner():
@@ -156,6 +164,93 @@ def test_materialized_slice_rejects_missing_or_cyclic_anchor_owner():
         )


+def test_materialized_flow_ownership_rejects_missing_or_foreign_owner():
+    span = SourceSpan(1, 0, 1, 1)
+    source_key = "pkg.py"
+    fingerprint = "f" * 64
+    owner = MaterializedOccurrenceRef(source_key, fingerprint, "owner")
+    value = MaterializedOccurrenceRef(source_key, fingerprint, "value")
+    manifest = SourceLineageManifest(
+        source_key,
+        fingerprint,
+        LINEAGE_FACTS_SEMANTIC_VERSION,
+        LineageFamilyStatus.FRESH,
+        1,
+        1,
+        0,
+        semantic_anchor_bindings_materialized=True,
+        anchor_ownership_materialized=True,
+        flow_ownership_materialized=True,
+    )
+    anchors = (MaterializedAnchorFact("owner", owner, "function", span),)
+    with pytest.raises(ValueError, match="ownership is incomplete"):
+        MaterializedLineageSourceFacts(
+            manifest=manifest,
+            anchors=anchors,
+            flows=(
+                MaterializedFlowFact(
+                    "flow",
+                    owner,
+                    value,
+                    LineageRelation.ASSIGNS,
+                    span,
+                    ResolutionKind.LEXICAL_EXACT,
+                    LineageConfidence.CONFIRMED,
+                ),
+            ),
+        )
+    with pytest.raises(ValueError, match="owner must reference"):
+        MaterializedLineageSourceFacts(
+            manifest=manifest,
+            anchors=anchors,
+            flows=(
+                MaterializedFlowFact(
+                    "flow",
+                    owner,
+                    value,
+                    LineageRelation.ASSIGNS,
+                    span,
+                    ResolutionKind.LEXICAL_EXACT,
+                    LineageConfidence.CONFIRMED,
+                    owner_local_id="missing",
+                ),
+            ),
+        )
+
+
+def test_reresolution_preserves_materialized_flow_ownership():
+    span = SourceSpan(1, 0, 1, 1)
+    facts = _facts(
+        anchors=(ExtractedAnchorFact("owner", "function", span),),
+        flows=(
+            ExtractedFlowFact(
+                "flow",
+                ExtractedOccurrenceRef("owner"),
+                ExtractedSymbolicRef(
+                    ExtractedSymbolicKind.DEFINITION,
+                    "pkg.mod",
+                    "target",
+                ),
+                LineageRelation.BINDS,
+                span,
+                ResolutionKind.LEXICAL_EXACT,
+                LineageConfidence.CONFIRMED,
+                owner_local_id="owner",
+            ),
+        ),
+    )
+    initial = materialize_lineage_source_facts(
+        facts,
+        _context(artifacts={"pkg.mod::target": "A1/1"}),
+    )
+    rerun = reresolve_materialized_lineage_source_facts(
+        initial,
+        _context(artifacts={"pkg.mod::target": "A1/2"}),
+    )
+    assert initial.manifest.flow_ownership_materialized is True
+    assert rerun.manifest.flow_ownership_materialized is True
+    assert rerun.flows[0].owner_local_id == "owner"
+
 def test_materializer_builds_and_reresolves_exact_semantic_anchor_bindings():
     span = SourceSpan(1, 0, 1, 1)
     module_anchor = "occ:v1:module:root:i:0:n:pkg"
```

### tests/test_lineage_state_lifecycle.py

```diff
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index 14fd07e..a4cd611 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -72,6 +72,7 @@ def _lineage_slice() -> MaterializedLineageSourceFacts:
             1,
             semantic_anchor_bindings_materialized=True,
             anchor_ownership_materialized=True,
+            flow_ownership_materialized=True,
         ),
         anchors=(
             MaterializedAnchorFact(
@@ -90,6 +91,7 @@ def _lineage_slice() -> MaterializedLineageSourceFacts:
                 span,
                 ResolutionKind.CALL_EXACT,
                 LineageConfidence.CONFIRMED,
+                owner_local_id="anchor",
             ),
         ),
         surfaces=(
@@ -197,6 +199,8 @@ def test_snapshot_round_trip_preserves_lineage_endpoint_types_and_metadata(
     assert loaded_slice.surfaces[0].provider == ProviderRef("fixture", "1")
     assert loaded_slice.surfaces[0].dynamic_boundary == "runtime-registration"
     assert loaded_slice.semantic_anchors == source_slice.semantic_anchors
+    assert loaded_slice.flows[0].owner_local_id == "anchor"
+    assert loaded_slice.manifest.flow_ownership_materialized is True
     assert loaded.lineage_query_index_state == "fresh"
     assert loaded.lineage_owner_source_index

@@ -1354,6 +1358,7 @@ def test_fresh_process_hydrates_materialized_symbolic_lineage_without_analysis(
         "symbolic-flow", symbolic, SemanticEndpoint("A1"), LineageRelation.RETURNS,
         SourceSpan(2, 0, 2, 1), ResolutionKind.IMPORT_EXACT,
         LineageConfidence.CONFIRMED,
+        owner_local_id="anchor",
     )
     source = replace(
         source,
@@ -1396,3 +1401,32 @@ print(json.dumps({"source": hydrated.source, "lineage": len(state.lineage_facts_
     )
     assert completed.returncode == 0, completed.stderr
     assert json.loads(completed.stdout) == {"source": "snapshot", "lineage": 1}
+
+
+def test_snapshot_legacy_flow_ownership_fails_closed(tmp_path):
+    source_slice = _lineage_slice()
+    object.__delattr__(
+        source_slice.manifest,
+        "flow_ownership_materialized",
+    )
+    for flow in source_slice.flows:
+        object.__delattr__(flow, "owner_local_id")
+
+    state = RepositoryAnalysisState(
+        lineage_facts_by_source={"pkg.py": source_slice},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+    )
+
+    save_snapshot(state, tmp_path, "legacy-flow-ownership")
+    loaded, _ = load_snapshot(
+        tmp_path,
+        expected_state_id="legacy-flow-ownership",
+    )
+
+    loaded_slice = loaded.lineage_facts_by_source["pkg.py"]
+    assert loaded_slice.manifest.flow_ownership_materialized is False
+    assert all(
+        flow.owner_local_id is None
+        for flow in loaded_slice.flows
+    )
```

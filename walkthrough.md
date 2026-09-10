STATUS=COMPLETE

TASK=Contextor Stage 1D.2 - exact local callable alias propagation
BASE=eb94d60b8b660fa0bb1ab88b3c3f9032506470be

IMPLEMENTATION
- `visit_name` now publishes `_CallableInfo` from the current lexical source occurrence only: first `_callables_by_anchor[source.local_id]`, then `_callables_by_binding[source.local_id]`.
- The published value is keyed by the transient `name_load.local_id`; existing `assign_target()` then carries it to the new current binding. No relation, schema, state family, call-result path, callback path, or import path changed.

SEMANTIC_EVIDENCE
- A: `def f; g=f; g()` resolves CALL_EXACT with symbolic source `f`.
- B: `async def f; g=f; g()` resolves CALL_EXACT with symbolic source `f`.
- C: nested `def f; g=f; return g()` resolves CALL_EXACT with symbolic source `f`.
- D: `def f; g=f; h=g; h()` resolves CALL_EXACT with symbolic source `f`.
- E: `f=lambda; g=f; g()` remains CALL_EXACT with the existing lambda symbolic source.
- F: rebind `g=42` after `g=f` has no CALL_EXACT.
- G: divergent branch bindings (`g=f` / `g=lambda`) have no CALL_EXACT.
- H: branch ambiguity after `g=f` and conditional `g=42` has no CALL_EXACT.
- I: `from pkg import f; g=f; g()` has no new CALL_EXACT.
- J: `g=factory()` has no returned-callable CALL_EXACT propagation.

TESTS
- `.venv\\Scripts\\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q` -> 123 passed in 2.45s.
- `.venv\\Scripts\\python.exe -m pytest tests/analysis/test_lineage_extraction_equivalence.py -q` -> 2 passed in 0.57s.
- `.venv\\Scripts\\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/analysis/test_lineage_extraction_equivalence.py tests/test_no_double_parse.py tests/test_index_fusion.py -q` -> 136 passed in 4.20s.
- `git diff --check` -> passed (only Git LF-to-CRLF warnings).

LIVE_CONTEXTOR_EVIDENCE
- Pre-edit LIVE revision=566, activity epoch `a5694974dc3c4cdab05b6720d6b0d74f`, resync_required=false.
- Desktop watcher published revision 567 for `contextor/core/analysis/lineage_extraction_bindings.py` and revision 568 for `tests/analysis/test_lineage_extraction.py`; both status=UPDATED, resync_required=false.
- Post-edit `get_file_edit_context` for the production module: canonical_state=fresh, workspace_sync=verified, provenance=live, canonical_revision=568; syntax status=checked_and_none with 0 errors; cycles and collisions families=fresh and both counts=0.
- `get_name_collisions` for the production module: availability=fresh, total=0.
- `get_layer_isolation` for `contextor.core.analysis`: LIVE canonical graph; diagnostics syntax_errors=0, name_collisions=0, cycles=0.
- Textual architecture verification: exactly one facade dynamic dispatch (`lineage_extraction.py:123`); exactly one facade `LineageExtractionState()` construction (`lineage_extraction.py:73`); no helper-to-facade import back-edge in `lineage_extraction_*.py`.

FILES_CHANGED
- `contextor/core/analysis/lineage_extraction_bindings.py`
- `tests/analysis/test_lineage_extraction.py`

FULL_DIFF
```diff
diff --git a/contextor/core/analysis/lineage_extraction_bindings.py b/contextor/core/analysis/lineage_extraction_bindings.py
index 1637a61..2868b56 100644
--- a/contextor/core/analysis/lineage_extraction_bindings.py
+++ b/contextor/core/analysis/lineage_extraction_bindings.py
@@ -44,6 +44,12 @@ def visit_name(
             ):
                 state.request_capture(load, node, owner, node.id)
             return
+        callable_info = (
+            state._callables_by_anchor.get(source.local_id)
+            or state._callables_by_binding.get(source.local_id)
+        )
+        if callable_info is not None:
+            state._callable_values[load.local_id] = callable_info
         emit_flow(
             state,
             paths,
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index a633c9b..8161990 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -1674,3 +1674,77 @@ def test_stage_1d1_declaration_producers_block_outer_capture(statement):
         + "\\n return inner\\n"
     )
     assert not _stage_1d_capture_flows(facts)
+
+
+def test_stage_1d2_local_function_assignment_alias_resolves_call_exactly():
+    facts = _stage_1c_facts("def f():\\n return 1\\ng=f\\nresult=g()\\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
+    assert isinstance(flow.source, ExtractedSymbolicRef)
+    assert flow.source.symbol_name == "f"
+
+
+def test_stage_1d2_async_function_assignment_alias_resolves_call_exactly():
+    facts = _stage_1c_facts("async def f():\\n return 1\\ng=f\\nresult=g()\\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
+    assert isinstance(flow.source, ExtractedSymbolicRef)
+    assert flow.source.symbol_name == "f"
+
+
+def test_stage_1d2_nested_function_assignment_alias_resolves_call_exactly():
+    facts = _stage_1c_facts(
+        "def outer():\\n def f(): return 1\\n g=f\\n return g()\\n"
+    )
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
+    assert isinstance(flow.source, ExtractedSymbolicRef)
+    assert flow.source.symbol_name == "f"
+
+
+def test_stage_1d2_chained_local_function_alias_resolves_call_exactly():
+    facts = _stage_1c_facts("def f():\\n return 1\\ng=f\\nh=g\\nresult=h()\\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
+    assert isinstance(flow.source, ExtractedSymbolicRef)
+    assert flow.source.symbol_name == "f"
+
+
+def test_stage_1d2_lambda_assignment_alias_remains_call_exact():
+    facts = _stage_1c_facts("f=lambda:1\\ng=f\\nresult=g()\\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
+    assert isinstance(flow.source, ExtractedSymbolicRef)
+    assert flow.source.symbol_name.startswith("lambda@")
+
+
+def test_stage_1d2_rebound_alias_loses_local_callable_authority():
+    facts = _stage_1c_facts("def f():\\n return 1\\ng=f\\ng=42\\nresult=g()\\n")
+    assert _stage_1c_call_result_flows(facts)[0].resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+def test_stage_1d2_divergent_alias_bindings_fail_closed():
+    facts = _stage_1c_facts(
+        "def f():\\n return 1\\nif flag:\\n g=f\\nelse:\\n g=lambda:2\\nresult=g()\\n"
+    )
+    assert _stage_1c_call_result_flows(facts)[0].resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+def test_stage_1d2_branch_ambiguity_does_not_restore_prior_alias():
+    facts = _stage_1c_facts(
+        "def f():\\n return 1\\ng=f\\nif flag:\\n g=42\\nresult=g()\\n"
+    )
+    assert _stage_1c_call_result_flows(facts)[0].resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+def test_stage_1d2_imported_callable_alias_is_not_newly_resolved():
+    facts = _stage_1c_facts("from pkg import f\\ng=f\\nresult=g()\\n")
+    assert _stage_1c_call_result_flows(facts)[0].resolution_kind is not ResolutionKind.CALL_EXACT
+
+
+def test_stage_1d2_factory_return_alias_is_not_newly_resolved():
+    facts = _stage_1c_facts(
+        "def f():\\n return 1\\ndef factory():\\n return f\\ng=factory()\\nresult=g()\\n"
+    )
+    flows = _stage_1c_call_result_flows(facts)
+    assert flows[-1].resolution_kind is not ResolutionKind.CALL_EXACT
```

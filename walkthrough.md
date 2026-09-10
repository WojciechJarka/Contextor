STATUS=FINAL_PASS

IMPLEMENTATION=Applied only the requested callback type annotations in lineage_extraction_calls.py; no bodies, imports, adapters or other files changed.

TEST_RESULTS=.venv\\Scripts\\python.exe -m pytest tests/analysis/test_lineage_extraction_equivalence.py tests/analysis/test_lineage_extraction.py tests/test_no_double_parse.py tests/test_index_fusion.py -q: 110 passed in 4.10s. git diff --check -- contextor/core/analysis/lineage_extraction_calls.py: PASS.

FILES_CHANGED=contextor/core/analysis/lineage_extraction_calls.py; walkthrough.md.

FULL_DIFFS=
diff --git a/contextor/core/analysis/lineage_extraction_calls.py b/contextor/core/analysis/lineage_extraction_calls.py
index d3973c8..29120d8 100644
--- a/contextor/core/analysis/lineage_extraction_calls.py
+++ b/contextor/core/analysis/lineage_extraction_calls.py
@@ -41,7 +41,7 @@ def resolve_current_imported_callable(state: LineageExtractionState, node: ast.C
     return None
 
 
-def collect_call_arguments(state: LineageExtractionState, paths: dict[int, str], node: ast.Call, owner: str | None, walrus_owner: str | None, *, value) -> tuple[_CallArgumentInfo, ...]:
+def collect_call_arguments(state: LineageExtractionState, paths: dict[int, str], node: ast.Call, owner: str | None, walrus_owner: str | None, *, value: ValueFn) -> tuple[_CallArgumentInfo, ...]:
     pending = [(arg, "starred" if isinstance(arg, ast.Starred) else "positional", None, index) for index, arg in enumerate(node.args)]
     pending += [(keyword.value, "double_starred" if keyword.arg is None else "keyword", keyword.arg, len(node.args) + index) for index, keyword in enumerate(node.keywords)]
     pending.sort(key=lambda item: (int(getattr(item[0], "lineno", 0) or 0), int(getattr(item[0], "col_offset", 0) or 0), item[3]))
@@ -77,7 +77,7 @@ def bind_call_arguments(state: LineageExtractionState, paths: dict[int, str], mo
                 consumed.add(parameter.local_id); emit_argument_to_parameter(state, paths, module_name,argument, callable_info, parameter)
             elif parameter is None and varkw is not None: emit_argument_to_parameter(state, paths, module_name,argument, callable_info, varkw)
 
-def function_signature_evidence(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, owner: str | None, walrus_owner: str | None, *, visit) -> None:
+def function_signature_evidence(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
     args = node.args
     for default in args.defaults:
         visit(default, owner, walrus_owner)

## GET_SYMBOL_IMPLEMENTATION_MCP_INPUT_BOUNDARY_ERGONOMICS_RESUME

STATUS=SUCCESS
FILES_CHANGED=contextor/mcp_server.py; contextor/mcp/docs/get_symbol_implementation.json; tests/mcp/test_get_symbol_implementation_input_boundary.py; tests/test_mcp_documentation.py
PY_COMPILE=PASS
BOUNDARY_TESTS=80 passed, 1 warning in 7.86s
DOCUMENTATION_TESTS=PASS (included in BOUNDARY_TESTS)
GIT_DIFF_CHECK=PASS

UNKNOWN_ARGUMENT_DOCS=PASS
UNKNOWN_ARGUMENT_FUZZY=PASS
MISSING_REQUIRED_ARGUMENT_DOCS=PASS
FAST_MCP_TYPE_VALIDATION_DOCS=PASS
OTHER_TOOLS_UNCHANGED=PASS
NON_PYDANTIC_TOOLERROR_RERAISED=PASS
NON_PUBLIC_VALIDATION_LOCATION_NOT_MISCLASSIFIED=PASS

FAST_MCP_2_12_4_VERIFICATION=
FunctionTool.run validates via TypeAdapter.validate_python;
ToolManager.call_tool wraps non-ToolError exceptions as ToolError from original exception;
middleware receives ToolError and inspects __cause__.

MCP_SERVER_RESTART_REQUIRED=YES
DESKTOP_LIVE_RESTART_REQUIRED=NO

ACTUAL_DIFF=
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
@@
+from fastmcp.exceptions import ToolError
+from fastmcp.server.middleware import Middleware, MiddlewareContext
+from fastmcp.tools.tool import ToolResult
+from pydantic_core import ValidationError as PydanticCoreValidationError
+from contextor.mcp import query_helpers
@@
+from contextor.mcp.tools.get_symbol_implementation import (
+    _parameter_contract_response as _get_symbol_implementation_parameter_contract_response,
+    get_symbol_implementation as _get_symbol_implementation_impl,
+)
@@
+_GET_SYMBOL_IMPLEMENTATION_ARGUMENTS = (
+    "repo_path", "symbol", "file_paths", "mode", "include", "methods",
+    "member_limit", "file_path",
+)
+_GET_SYMBOL_IMPLEMENTATION_ARGUMENT_SET = frozenset(
+    _GET_SYMBOL_IMPLEMENTATION_ARGUMENTS
+)
+_GET_SYMBOL_IMPLEMENTATION_REQUIRED_ARGUMENTS = ("repo_path", "symbol")
+
+# _get_symbol_implementation_boundary_result builds the canonical
+# parameter_contract_error ToolResult.
+# _get_symbol_implementation_validation_parameters rejects empty and
+# non-public Pydantic validation locations.
+# _GetSymbolImplementationInputBoundaryMiddleware intercepts only
+# get_symbol_implementation: unknown/missing inputs are handled before
+# FastMCP; only ToolError caused by PydanticCoreValidationError is mapped.
+mcp.add_middleware(_GetSymbolImplementationInputBoundaryMiddleware())

diff --git a/contextor/mcp/docs/get_symbol_implementation.json b/contextor/mcp/docs/get_symbol_implementation.json
@@
-    "Caller parameter names are exactly repo_path, symbol, file_paths, mode, include, methods, member_limit, and file_path. Do not invent additional argument names. Unknown argument names are rejected by the MCP/FastMCP input boundary before the Python tool body can produce its documentation fallback.",
+    "Caller parameter names are exactly repo_path, symbol, file_paths, mode, include, methods, member_limit, and file_path. Do not invent additional argument names. A dedicated MCP input-boundary middleware intercepts unknown argument names before FastMCP function validation and returns the complete canonical documentation plus parameter_contract_error. Missing required arguments receive the same pre-validation documentation fallback. FastMCP/Pydantic input-schema validation failures attributable exclusively to documented get_symbol_implementation parameters are recognized through the ToolError cause chain and converted to the same documentation response. Unrelated ToolError or validation failures are re-raised and are never misclassified as caller parameter errors.",
@@
+    "Unknown MCP argument names, missing required arguments, and documented-parameter input-schema/type validation failures return the complete canonical tool documentation plus parameter_contract_error at the MCP/FastMCP execution boundary."

diff --git a/tests/mcp/test_get_symbol_implementation_input_boundary.py b/tests/mcp/test_get_symbol_implementation_input_boundary.py
new file mode 100644
@@
+Dedicated focused test module covering unknown arguments, typo candidates,
+missing required arguments, FastMCP type validation, other-tool passthrough,
+non-Pydantic ToolError re-raise, and non-public validation-location rejection.

diff --git a/tests/test_mcp_documentation.py b/tests/test_mcp_documentation.py
@@
+    assert "dedicated MCP input-boundary middleware" in serialized
+    assert "Missing required arguments receive the same" in serialized
+    assert "ToolError cause chain" in serialized
+    assert "Unrelated ToolError or validation failures are re-raised" in serialized

## CPA10I_REFERENCE_FUSION_FINAL_TEST_MIGRATION_RESUME

STATUS=SUCCESS
FILES_CHANGED=tests/test_reference_fusion_integration.py
PY_COMPILE=PASS
REGRESSION_SELECTION=226 passed in 13.77s
GIT_DIFF_CHECK=PASS

WARM_REFERENCE_HIT_AST_PARSE_CALLS=0
LEGACY_MIGRATION_PARSE_CALLS=1
SCHEMA_MIGRATION_PARSE_CALLS=1
POST_MIGRATION_WARM_PARSE_CALLS=0
STALE_PARSE_SOURCE_WITH_FINGERPRINT_MONKEYPATCHES_REMAINING=0

ACTUAL_DIFF=
diff --git a/tests/test_reference_fusion_integration.py b/tests/test_reference_fusion_integration.py
@@
-def test_warm_reference_hit_parses_once_for_lineage_and_zero_reference_extraction(
+def test_warm_reference_hit_skips_ast_parse_and_reference_extraction(
@@
-    original_parse = indexer.parse_source_with_fingerprint
-    monkeypatch.setattr(indexer, "parse_source_with_fingerprint", lambda path: (parse_calls.append(path) or original_parse(path)))
+    monkeypatch.setattr(
+        indexer, "parse_source_snapshot",
+        lambda snapshot, path: (parse_calls.append(path) or (_ for _ in ()).throw(AssertionError("unexpected warm AST parse"))),
+    )
@@
-    assert len(parse_calls) == 1
+    assert parse_calls == []
@@
-    original_parse = indexer.parse_source_with_fingerprint
+    original_parse = indexer.parse_source_snapshot
@@
-        "parse_source_with_fingerprint",
-        lambda path: (calls.append(path) or original_parse(path)),
+        "parse_source_snapshot",
+        lambda snapshot, path: (calls.append(path) or original_parse(snapshot, path)),
@@
-    assert len(calls) == 1
+    assert calls == []

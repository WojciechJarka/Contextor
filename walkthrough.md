# F2L D1P2 — public registration and documentation

STATUS: success

TEST_RESULT: 28 passed, 1 third-party FastMCP deprecation warning.

FILES_CHANGED:
- tests/test_mcp_documentation.py

PUBLIC_SIGNATURE_PROOF: The public signature assertion now uses inspect.signature(tool.fn, eval_str=True). This resolves the adapter's intentional postponed annotations before comparison, preserving the exact public D1P1 parameter contract without changing the adapter, MCP registration, production, or documentation files.

TESTS_RUN:
- .\.venv\Scripts\python.exe -m pytest -q tests\test_mcp_documentation.py tests\mcp\tools\test_public_mcp_docs_parity.py tests\mcp\tools\test_get_symbol_lineage.py
  Result: 28 passed, 1 warning in 6.50s
- .\.venv\Scripts\python.exe -m py_compile tests\test_mcp_documentation.py
  Result: passed
- git diff --check -- tests/test_mcp_documentation.py
  Result: passed

## ACTUAL_DIFF

```diff
diff --git a/tests/test_mcp_documentation.py b/tests/test_mcp_documentation.py
index cf32bb2..52d93bc 100644
--- a/tests/test_mcp_documentation.py
+++ b/tests/test_mcp_documentation.py
@@ -190,7 +190,7 @@ def test_get_symbol_lineage_is_registered_with_documented_public_signature():
             "progressive disclosure."
         )
     )
-    assert str(inspect.signature(tool.fn)) == (
+    assert str(inspect.signature(tool.fn, eval_str=True)) == (
         "(repo_path: str, symbol: str, mode: str = 'auto', "
         "sections: list[str] | None = None, "
         "representation: str = 'auto', "
```


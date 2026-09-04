# F2F0 correction

DECISION=PASS

MCP_RESTART_REQUIRED=YES

LIVE_RESTART_REQUIRED=NO

RUNTIME_CERTIFICATION_NOT_YET_PERFORMED=YES

FULL_SUITE_RUN_BY_AGENT=NO

Contextor LIVE call-graph evidence at revision 214 for `contextor.mcp.tools.get_symbol_call_context::get_symbol_call_context` returned 32/32 intra-module callee edges (depth 3). The executable local callees are `_error`, `_identity`, `_known_symbols_for_module`, `_ordered_union`, `_queryable_artifact_registry`, `_shape`, `_textual_miss_response`, and `_walk`; none reconstructs or materializes source-derived call facts.

Contextor source evidence for the runtime binding `mcp_runtime.get_or_init_engine` shows only LIVE snapshot retrieval or persisted-state hydration and engine construction. It does not call `ensure_module_usages`, `extract_module_usage_facts`, `SymbolReferenceVisitor`, analysis, or AST/source call-fact production. No reconstruction/materialization callable is reachable from the query path; a fake monkeypatch target would not test executable behavior.

The focused tests now accurately state executable behavior: materialized call facts do not invoke `ast.parse`; the target-local `build_state_freshness` helper remains allowed without `ast.parse`.

Documentation contract validator: `tests/mcp/tools/test_public_mcp_docs_parity.py`, which checks documentation/index parity against registered MCP tools via `documentation.query_documentation()`.

Command:

```text
.venv\Scripts\python.exe -m pytest -q tests/test_get_symbol_call_context.py::test_query_does_not_parse_materialized_call_facts tests/mcp/tools/test_get_symbol_call_context.py::test_get_symbol_call_context__uses_freshness_helper_without_ast_parse tests/mcp/tools/test_public_mcp_docs_parity.py
```

Result:

```text
6 passed, 1 warning in 4.03s
```

`git diff --check` passed. The warning is FastMCP/Authlib deprecation only. No unrelated suite was run.

FILES_CHANGED:

```text
tests/test_get_symbol_call_context.py
tests/mcp/tools/test_get_symbol_call_context.py
```

No production or docs file changed in this correction. Their preceding accepted F2F0 changes remain in the worktree. The existing runtime log was untouched. The walkthrough diff is omitted.

## COMPLETE RAW UNIFIED DIFFS

```diff
diff --git a/tests/test_get_symbol_call_context.py b/tests/test_get_symbol_call_context.py
--- a/tests/test_get_symbol_call_context.py
+++ b/tests/test_get_symbol_call_context.py
@@ -188 +188 @@
-def test_query_does_not_parse_or_reconstruct_calls(monkeypatch):
+def test_query_does_not_parse_materialized_call_facts(monkeypatch):
```

```diff
diff --git a/tests/mcp/tools/test_get_symbol_call_context.py b/tests/mcp/tools/test_get_symbol_call_context.py
--- a/tests/mcp/tools/test_get_symbol_call_context.py
+++ b/tests/mcp/tools/test_get_symbol_call_context.py
@@ -93 +93 @@
-def test_get_symbol_call_context__uses_freshness_helper_without_call_reconstruction(monkeypatch):
+def test_get_symbol_call_context__uses_freshness_helper_without_ast_parse(monkeypatch):
```

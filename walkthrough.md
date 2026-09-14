# MCPD1_CONTENT_ONLY_TRANSPORT

## STATUS

SUCCESS. The central FastMCP registration now passes `output_schema=None`; JSON-as-string tool payload semantics are unchanged. No LIVE code, diagnostics, representation, output guard, telemetry, individual tool annotations, or documentation changed.

## FILES_CHANGED

- `contextor/mcp_server.py`
- `tests/test_mcp_transport_output.py`
- `walkthrough.md` (this report)

## IMPLEMENTATION

`contextor.mcp_server::register_mcp_tool` now registers through:

```python
return mcp.tool(name=tool_name, description=desc, output_schema=None)(wrapped)
```

The pre-existing `_instrument_mcp_tool(func, tool_name)` call remains immediately before registration. The synthetic regression test registers a `-> str` JSON tool through that real central function, asserts `registered.output_schema is None`, runs it, asserts `ToolResult.structured_content is None`, asserts one text content item, validates JSON status, and unconditionally removes the synthetic tool in `finally`.

## TESTS

```
& .\.venv\Scripts\python.exe -m pytest -q \
  tests\test_mcp_transport_output.py \
  tests\test_mcp_diagnostics.py::test_wrapper_injects_health_for_analytical_not_found \
  tests\test_mcp_diagnostics.py::test_wrapper_applies_shared_guard_after_diagnostics_injection \
  tests\test_mcp_diagnostics.py::test_wrapper_retry_guidance_matches_tool_signature \
  tests\test_mcp_diagnostics.py::test_registered_name_collision_tool_and_shared_summary_wrapper \
  tests\test_live_activity_status.py::test_all_28_registered_mcp_tools_telemetry_against_fastmcp_registry
```

Result: **6 passed** in 11.81s. One pre-existing third-party Authlib deprecation warning from FastMCP dependency loading. `py_compile` passed for both changed Python files; `git diff --check` passed.

## DOCS_REVIEW

`DOCS_CHANGED=NO`. Focused search of `contextor/mcp/docs` found no explicit `structuredContent`, `outputSchema`, or `output_schema` contract.

## CONTEXTOR_FLOW_VERIFY

Contextor `get_symbol_call_context` confirms the existing direct edge:

```
contextor.mcp_server::register_mcp_tool
  -> contextor.mcp_server::_instrument_mcp_tool
```

No parallel registration path was introduced by this edit. Contextor correctly marks source implementations as `stale_source` / `workspace_sync=out_of_sync` because the local file changed after canonical revision 1090. No analysis was run merely to refresh it.

## COMMIT_SHA

`be39ec9538d1e08248a457c9722f8fc881938120` (existing HEAD; no commit created).

## RUNTIME_RESTART_REQUIRED

YES. Reload/restart the active Contextor MCP process before a real wire/model-context verification. Desktop/LIVE authority restart is not required by this change.

## DIFFS

### contextor/mcp_server.py

```diff
@@
-    return mcp.tool(name=tool_name, description=desc)(wrapped)
+    return mcp.tool(name=tool_name, description=desc, output_schema=None)(wrapped)
```

### tests/test_mcp_transport_output.py

```python
import asyncio
import json

from fastmcp.tools.tool import ToolResult

from contextor.mcp_server import mcp, register_mcp_tool


def test_registered_string_tool_emits_content_without_structured_content():
    name = "synthetic_transport_output"

    def synthetic_transport_output() -> str:
        return json.dumps({"status": "synthetic_ok"})

    registered = register_mcp_tool(
        synthetic_transport_output,
        name=name,
        description="Synthetic transport-output regression tool.",
    )
    try:
        assert registered.output_schema is None
        result = asyncio.run(registered.run({}))
        assert isinstance(result, ToolResult)
        assert result.structured_content is None
        assert len(result.content) == 1
        assert json.loads(result.content[0].text)["status"] == "synthetic_ok"
    finally:
        mcp.remove_tool(name)
```

Awaiting `proceduj`.

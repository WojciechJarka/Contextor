# S2A CORRECTION - SHARED MCP RUNTIME OWNER

## SUMMARY

The temporary registration-time engine injection was removed. `contextor.mcp.runtime` now owns the engine resolver and both mutable runtime maps. All production consumers in `mcp_server.py` resolve engines through that owner.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\mcp\runtime.py` (created)
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\query_canonical_projection.py`
- `C:\Temp\Contextor_Repo\contextor\mcp_server.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_split_s2a.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py`
- focused tests whose monkeypatch targets moved from the former owner to `contextor.mcp.runtime`

## IMPLEMENTATION

- moved `get_or_init_engine`, `_live_engines` and `_live_engine_revisions` as one dependency closure to `contextor.mcp.runtime`;
- preserved resolver hydration, LIVE connection, revision and persistence logic;
- changed `query_canonical_projection` to import the runtime owner directly;
- changed every production resolver consumer in `mcp_server.py` to call `mcp_runtime.get_or_init_engine`;
- removed `bind_engine_resolver`, the injected callable global and registration-time binding;
- retained FastMCP registration, public signatures, schemas and order.

SINGLE_RUNTIME_STATE_OWNER: true

BIND_ENGINE_RESOLVER_EXISTS: false

REGISTRATION_DEPENDENCY_BINDING: false

PUBLIC_CONTRACT_CHANGED: false

## TARGETED_TESTS

Command:

    .venv\Scripts\python.exe -m pytest -q --disable-warnings tests/test_mcp_incremental_hydration.py tests/test_mcp_split_s2a.py tests/test_canonical_state_contract.py::test_mcp_describe_and_query_tools_share_the_contract tests/test_canonical_state_contract.py::test_mcp_projection_returns_structured_unavailable_state tests/test_live_e2e_corrections.py::test_canonical_projections_reject_stale_module_facts tests/test_mcp_regressions.py::test_file_edit_context_live_revision_lifecycle

Result: 10 passed, 0 failed, 1 warning in 16.04s.

Syntax verification:

    .venv\Scripts\python.exe -m py_compile contextor/mcp_server.py contextor/mcp/runtime.py contextor/mcp/tools/query_canonical_projection.py

Result: passed.

## CONTEXTOR_POST_CHANGE_AUDIT

- pre-change Contextor evidence identified the exact resolver closure: the two runtime maps, LIVE connect/ping/snapshot hydration, persistent-state hydration and revision tracking;
- source verification confirms no `bind_engine_resolver`, registration binding or private resolver compatibility alias remains;
- post-change Contextor query returned `owner_identity_changed`; therefore its current canonical graph has not incorporated the new `contextor.mcp.runtime` module and still reports the previous graph;
- code and targeted structural tests prove the intended dependency direction, but architectural visibility requires the current Contextor LIVE owner to reconnect/re-index after restart.

## FINAL_VERDICT

S2A_ARCHITECTURE_CLOSED

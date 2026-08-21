# MCP SERVER SPLIT - STAGE S2D

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\mcp_server.py`
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\get_project_architecture.py` (created)
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\get_module_context.py` (created)
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\get_file_edit_context.py` (created)
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\get_symbol_implementation.py` (created)
- `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_split_s2d.py` (created)

## DEPENDENCY_CLOSURE

- `get_project_architecture`: `mcp_runtime`, `query_helpers`, `module_current_truth`; local `_stale_module_truths`.
- `get_module_context`: `mcp_runtime`, `query_helpers`, local imports from `contextor.core.report_query`; no moved private helper.
- `get_file_edit_context`: `mcp_runtime`, `query_helpers`, existing core graph/rule imports; local `_static_test_reachability`.
- `get_symbol_implementation`: `mcp_runtime`, `query_helpers`, `read_source` and `SourceError`; its seven AST/source helpers.

## HELPER_OWNERSHIP

- `_stale_module_truths` moved to the sole production consumer `get_project_architecture.py`.
- `_static_test_reachability` moved to the sole production consumer `get_file_edit_context.py`.
- `_resolve_symbol_source_paths`, `_symbol_signature`, `_ast_symbol_candidates`, `_module_path_for_source`, `_symbol_static_context`, `_json_size`, `_symbol_preview` moved with their sole public owner `get_symbol_implementation.py`.
- No private compatibility aliases remain in `mcp_server.py`; the direct test binding now imports the real helper owner.

## TOOLS_MOVED

- `get_project_architecture`
- `get_module_context`
- `get_file_edit_context`
- `get_symbol_implementation`

`TOOLS_MOVED_THIS_STAGE=4`  
`TOTAL_TOOLS_MOVED=17`  
`TOOLS_REMAINING_IN_MONOLITH=4`

AST-normalized comparison against the pre-move `HEAD:contextor/mcp_server.py`, ignoring only FastMCP decorators, returned `True` for all four implementation bodies and all moved helpers.

## SSOT_INVARIANTS

- Canonical architecture/module/file-edit bodies were moved unchanged.
- No output report resolver, `resolve_output_dir`, `_get_canonical_report`, or `json.load` exists in the four new modules.
- Existing freshness, exact module-layer coverage, parse-truth gating, dependency evidence, availability, provenance, totals and truncation paths are unchanged.
- `GENERATED_REPORT_SSOT_REINTRODUCED=false`
- `PUBLIC_CONTRACT_CHANGED=false`
- `TOOL_BODY_SEMANTIC_CHANGES=0`

## SYMBOL_SOURCE_CONTRACT

Explicit repository-bounded file resolution, Contextor source reader, AST candidate selection, ambiguity refusal, preview/fetch selection, signatures, method extraction, static context and response-size semantics moved unchanged.

## FILE_EDIT_CONTEXT_CONTRACT

Canonical module/artifact/dependency context and static test reachability moved unchanged. The test-reachability helper has one production owner; its focused regression remains passing.

## TEST_BINDINGS_MIGRATED

`tests/test_mcp_regressions.py::test_test_reachability_finds_direct_alias_and_reexport_paths` now imports `_static_test_reachability` from its real owner. No private bridge was retained.

## IMPORT_GRAPH

`mcp_server -> tools/* -> mcp runtime/query_helpers/core`

- `TOOL_TO_SERVER_IMPORTS=0`
- `TOOL_TO_TOOL_IMPORTS=0`
- `REGISTRATION_DEPENDENCY_BINDING=false`
- `DUPLICATE_HELPERS=0`

## REGISTRATION_PARITY

Structural regression confirms exact 21-tool names/order, direct `.fn` owners, signatures and centralized short descriptions. All four functions are plain undecorated implementations with no public docstrings or registration side effects.

## TARGETED_TEST_RESULT

Focused contracts plus S2D structure:

```text
18 passed, 57 deselected, 1 warning in 20.82s
```

Post-import cleanup structural recheck:

```text
3 passed, 1 warning in 3.43s
```

The warning is the external FastMCP/Authlib deprecation warning.

## CONTEXTOR_POST_CHANGE_AUDIT

- Source-bounded Contextor resolution confirms all four implementations exist completely in their new files with no public docstrings.
- Desktop watcher revision `1030` classified the monolith update as `UNCHANGED`; revision `1032` materialized the new S2D structural test.
- Four new production tool modules were not present in canonical module context after their creation.
- Subsequent LIVE checks returned `transient_connection_failure`, then `owner_identity_changed`; therefore current implementations/consumers/blast radius cannot be certified from hydrated canonical state.
- Textual and AST checks prove no old definitions, duplicate helper paths, report fallback, reverse imports, or registration binding in source.

## LIVE_NEW_MODULE_EVIDENCE

`get_module_context` returned “not found in the project graph” for each of:

- `contextor.mcp.tools.get_project_architecture`
- `contextor.mcp.tools.get_module_context`
- `contextor.mcp.tools.get_file_edit_context`
- `contextor.mcp.tools.get_symbol_implementation`

No Full Analysis or manual `update_file` was used. This is an unresolved LIVE incremental materialization/owner-state failure, not masked by a workaround.

## FINAL_VERDICT

`MCP_SPLIT_S2D_FIX_REQUIRED`

The code move and targeted contracts pass, but the mandatory LIVE new-module invariant and final canonical architectural audit are not closed.

RESTART OBU

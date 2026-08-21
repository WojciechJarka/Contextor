# MCP SERVER SPLIT - STAGE S2C

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py` (created)
- `C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py`
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\get_artifact_blast_radius.py` (created)
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\search_artifacts.py` (created)
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\get_artifacts_for_module.py` (created)
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\lookup_artifact_by_symbol.py` (created)
- `C:\Temp\Contextor_Repo\contextor\mcp_server.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py`
- `C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_split_s2a.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_split_s2b.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_split_s2c.py` (created)
- `C:\Temp\Contextor_Repo\walkthrough.md`

## DEPENDENCY_CLOSURE

All four implementations depend on canonical `RepositoryAnalysisState` obtained through `contextor.mcp.runtime.get_or_init_engine`.

Shared closure confirmed before the move:

- bounded collection projection;
- persistent registry identity lookup;
- per-module parse freshness projection;
- canonical own-symbol domain projection;
- canonical artifact-consumption lookup and freshness gate.

`get_artifact_blast_radius` additionally uses core affected-set calculation, indexed identity resolution and public-API ranking. `search_artifacts` reads canonical artifacts/modules and dependency graph. `lookup_artifact_by_symbol` directly gates optional consumer evidence with `artifact_consumption_is_fresh`.

## SHARED_HELPER_OWNERSHIP

`contextor.mcp.query_helpers` is the single owner of:

- `bounded_items`;
- `read_registries`;
- `module_truth_unavailable`;
- `canonical_symbol_catalog`;
- `canonical_symbol_consumers`.

Contextor reports 8 production consumers for this shared module. `analysis_jobs` and remaining monolith tools import the real owner directly. There are no copied implementations or private compatibility bridges in `mcp_server.py`.

## TOOLS_MOVED

- `get_artifact_blast_radius` -> `contextor.mcp.tools.get_artifact_blast_radius`
- `search_artifacts` -> `contextor.mcp.tools.search_artifacts`
- `get_artifacts_for_module` -> `contextor.mcp.tools.get_artifacts_for_module`
- `lookup_artifact_by_symbol` -> `contextor.mcp.tools.lookup_artifact_by_symbol`

Each module has one plain public function, no FastMCP instance/decorator, registration side effect, server import or tool-to-tool import.

AST-normalized comparison against the pre-move monolith returned `True` for all four complete implementation bodies after normalizing only shared-helper ownership references.

## SSOT_INVARIANTS

- Runtime facts remain canonical RAM projections.
- No output resolver, report parser, `json.load`, output `read_text` or report fallback exists in the four modules.
- Parse-stale modules remain fail-closed through the shared authoritative truth projection.
- `own_symbols` remains the exact canonical artifact domain.
- Empty canonical consumer sets remain authoritative.
- Ambiguous exact textual leaves remain fail-closed.
- Consumer evidence retains independent artifact-consumption freshness semantics.
- Provenance, totals, truncation and compact/full payload shaping are unchanged.

## TEST_BINDINGS_MIGRATED

Registry/helper tests now patch `contextor.mcp.query_helpers`, the actual production owner. No private aliases were retained for tests.

## IMPORT_GRAPH

```text
mcp_server / central registration
-> contextor.mcp.tools.<tool>
-> contextor.mcp.runtime + contextor.mcp.query_helpers
-> authoritative core
```

Structural regression proves zero tool-to-server imports, zero tool-to-tool imports, one owner per shared helper, no FastMCP side effects and no registration dependency binding.

## REGISTRATION_PARITY

- Exact 21-tool names/order preserved.
- Each `mcp_server.<tool>.fn` points directly to its new module implementation in a fresh runtime import.
- Exact signatures, defaults and annotations preserved.
- Generated FastMCP parameter schemas remain unchanged from those signatures.
- Short descriptions remain sourced from the centralized documentation index.
- Monolith retains exactly 8 decorated public implementations.

## TARGETED_TEST_RESULT

Final targeted scope: S2C structure plus canonical empty/stale consumers, parse freshness, own-symbol domain, ambiguity, report-free operation, stale registry identities, zero-consumer signatures, bounded evidence, artifact search, architecture/downstream blast radius and parse-stale global search.

Result: **21 passed, 0 failed, 1 external Authlib deprecation warning**.

Cumulative moved-tool count assertions touched by S2C: **2 passed, 0 failed**.

`py_compile`: PASS for all moved/shared modules and affected tests.

`git diff --check`: PASS; only Git CRLF conversion notices.

## CONTEXTOR_POST_CHANGE_AUDIT

- All four new implementation modules resolve in canonical Contextor state with one public API each and 2 static consumers each.
- `contextor.mcp.query_helpers` resolves with 5 public helpers, 8 consumers and 13 bounded test paths.
- Canonical ownership identifies the new implementations, not `mcp_server`.
- AST/static audit finds no old implementations, duplicate helper definitions, forbidden imports, mutable injected state or registration binding.
- Blast radius remains confined to MCP registration, shared query projections and tests that patched the former owner.
- Scope leakage: none detected.

## LIVE_NEW_MODULE_EVIDENCE

Persistent canonical metadata after desktop-watcher processing:

```text
revision=1016
writer=live-service
state_id=20260821_114217
```

Without a new completed Full Analysis, canonical modules, artifacts and dependency-graph nodes are present for:

- `contextor.mcp.query_helpers`
- `contextor.mcp.tools.get_artifact_blast_radius`
- `contextor.mcp.tools.search_artifacts`
- `contextor.mcp.tools.get_artifacts_for_module`
- `contextor.mcp.tools.lookup_artifact_by_symbol`

Contextor module projections independently resolve all five at canonical module IDs `252/2` through `256/1`. This confirms incremental materialization rather than masking with the still-running unrelated project job.

The LIVE endpoint became unreachable during the unrelated project job started in the preceding runtime task, so journal retrieval currently reports owner identity change. Canonical persistence and Contextor module projections remain available; S2C did not alter LIVE ownership code.

## INVARIANTS

```text
TOOLS_MOVED_THIS_STAGE=4
TOTAL_TOOLS_MOVED=13
TOOLS_REMAINING_IN_MONOLITH=8
TOOL_TO_SERVER_IMPORTS=0
TOOL_TO_TOOL_IMPORTS=0
REGISTRATION_DEPENDENCY_BINDING=false
DUPLICATE_SHARED_HELPERS=0
GENERATED_REPORT_SSOT_REINTRODUCED=false
PUBLIC_CONTRACT_CHANGED=false
TOOL_BODY_SEMANTIC_CHANGES=0
```

## FINAL_VERDICT

`MCP_SPLIT_S2C_PASS`

`RESTART OBU`

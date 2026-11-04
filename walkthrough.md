# CONTEXTOR PY315-COMPAT-D2B-R2 — active-code adoption gate

## PREFLIGHT

DIRECT_EVIDENCE: repository root `C:\Temp\Contextor_Repo`; HEAD `5453a94a9d39c65a49da918ed07f038db7853f12` (commit time 2026-11-04 13:12:39 +01:00). Worktree was clean before this report; the prior D2B changes are now in HEAD. Canonical interpreter `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` reports CPython 3.15.2 AMD64. No pytest, source edit, restart, update_file, process termination or FULL analysis performed.

## CURRENT_SOURCE_IDENTITY

Current HEAD contains D2B and R1 source. On-disk last-write times for changed modules were 12:41–13:00 local (indexer 13:00); backend/Desktop/LIVE process starts were 11:36 local. Git HEAD and disk timestamps identify source chronology but do not alone prove loaded-code adoption. Repository-root identity was supplied to Contextor MCP and resolved; exact internal repository ID was not exposed by queried projections.

## MCP_DISCOVERY

Contextor MCP queried first. `get_module_context` for `full_analysis_coordinator`, `facade`, and `analysis_jobs`: LIVE revision 980, canonical_state=fresh, workspace_sync=verified, graph/cycles fresh, **cycle_semantics=stale**, advisory null. `get_live_events(after_revision=979)` confirms latest revision 980 and current warning view fresh with 16 structural paths and 16 active warnings. This warning view is distinct from stale cycle-semantic evidence. No MCP mutation call made.

## RUNTIME_CODE_OWNERSHIP

Read-only Windows process inventory, with command-line role classification but no secret output:

| Role | Actual PID | Parent redirector PID | Actual executable | Start |
|---|---:|---:|---|---|
| MCP `-m contextor.mcp_main` | 11876 | 12384 | `C:\Python315\python.exe` | 2026-11-04 11:36:25 local |
| Desktop GUI | 10564 | 6480 | `C:\Python315\python.exe` | 2026-11-04 11:36:32 local |
| LIVE `-m contextor.core.live_state.runtime` | 12660 | 11660 | `C:\Python315\python.exe` | 2026-11-04 11:36:39 local |

Source chain: `contextor/mcp_main.py::main` imports `mcp_server`; `mcp_server.py:182` imports `contextor.core.analysis.process_pool_lifecycle`, which executes `contextor/core/__init__.py`; that package initializer imports `core/symbol_engine/indexer.py`. `mcp_server.py:234` also imports the analyze_project tool, which imports `mcp.analysis_jobs`; `analysis_jobs.py:11-12` imports `full_analysis_coordinator` and `facade` at module load. Hence the backend process necessarily loaded indexer and analysis dispatch code at startup. Facade FULL calls materialization, scenarios and cycle models through their module imports when used; exact per-process `sys.modules` contents for every listed D2B module were not inspected. Spawned ProcessPool workers may load new source independently, but parent FULL logic and cache/model ownership are not wholly delegated to fresh workers.

## LOADED_CODE_ADOPTION

CODE_PATH_PROVED: backend indexer import occurred as part of startup before D2B source edits. The backend actual process PID 11876 has remained alive. Python import caching means later `workspace_sync=verified` cannot replace its already loaded indexer module. At minimum, current indexer cache-integrity code adoption in the active backend is **not established** and its prior loaded implementation is expected to remain. Desktop and LIVE loaded-code identity for each requested module is UNKNOWN; no claim is made from timestamps alone.

## RELOAD_SAFETY_GATE

**RUNTIME_RELOAD_REQUIRED.** The MCP FULL path uses `asyncio.to_thread(run)` in `contextor/mcp/analysis_jobs.py:311`, then calls `run_full_analysis_exclusive` in that same backend process. A new thread does not reload already imported Python modules. The supported owner-safe backend replacement is the Desktop `Restart Backend` operation in `contextor/ui/gui.py:951-1015`: it reads exact backend identity, calls `stop_backend`, verifies stopped state, starts a new authenticated backend, checks identity changed, and reclaims Desktop ownership. `contextor/mcp_backend_control.py:1011+` uses backend record/creation-time identity and confirms exit. This procedure was identified, **not executed**. PID-only termination and taskkill were not used.

## FULL_ANALYSIS_CONTRACT

`contextor/mcp/tools/analyze_project.py` submits a project job to `analysis_jobs`; `_run_analysis_worker` uses the existing backend thread, calls `run_full_analysis_exclusive(owner="mcp_analysis")`; coordinator obtains exclusive repository lease then invokes `ContextorFacade.analyze_project`. `facade.py:818-852` materializes and classifies cycle-semantic evidence; `facade.py:1488-1535` uses publication receipt logic to install committed state into LIVE and records success/pending/failure. A standalone analysis without this publication path would not meet R2.

## FULL_EXECUTION_GATE

A. Current source execution: **FAIL/UNKNOWN** for active backend indexer, because startup import predates D2B edits and no supported fresh-code guarantee exists. C. CPython 3.15.2: confirmed. D. Exact internal repo ID: not independently confirmed. B/E/F/G: not fully certified after A failed. Per R2 fail-closed rule, **no FULL was launched**. No extra backend or LIVE authority created.

## FULL_EXECUTION_RESULT

NOT_EXECUTED — stopped before FULL at reload safety gate. FULL count in this task: 0.

## LIVE_PUBLICATION_RECEIPT

NOT_APPLICABLE — no FULL, no new publication receipt. Existing LIVE revision 980 is from watcher updates, not this task's FULL.

## CANONICAL_SEMANTIC_FRESHNESS

Preflight: canonical_state=fresh and workspace_sync=verified for queried modules; `cycle_semantics_state=stale` separately. No post-FULL readback possible. Exact current `cycle_semantics_invalidation_reason` was not exposed by read-only MCP query; source path `incremental/engine.py:975-988` and `cycle_semantics/lifecycle.py:95-153` identifies `SOURCE_CHANGED` as the expected source-update invalidation path, not a direct state-field observation.

## SOURCE_AND_GRAPH_INVARIANTS

No source edit or graph mutation in R2. Existing LIVE warning projection reports 16 structural paths, matching prior baseline. No new hard dependency edge was introduced by this task. Fresh cycle-semantic source-fingerprint bindings were not regenerated.

## WARNING_ELIGIBILITY

Current installed warning view: 16 structural, 0 MODEL_PASS, 16 active warning paths. This is a static installed-warning partition; stale cycle-semantic family prevents new semantic acceptance. No unsupported lazy import was submitted to FULL, and no fresh model claim was generated in R2.

## PROCESS_HEALTH_BEFORE_AFTER

Before and after read-only inventories showed the same actual MCP/Desktop/LIVE PIDs and parent redirectors listed above. No process was started or terminated by this task. A comprehensive orphan-worker census was not required after the early stop and was not claimed.

## FILES_CHANGED

`walkthrough.md` only.

## FULL_DIFFS

ACTUAL_DIFF=DIFFS=NONE for source, tests, launchers, dependencies and configuration. `walkthrough.md` is the report and excluded from source/test diff requirement.

## REMAINING_UNKNOWN

Exact loaded `sys.modules` contents in Desktop/LIVE and each analysis worker; internal repository ID; active FULL lease status; current state-field invalidation reason; fresh semantic evidence after supported backend replacement and authorized FULL; publication receipt. These are downstream gates, not grounds to bypass the reload stop.

## FINAL_VERDICT

**BLOCKED_PY315_D2B_RUNTIME_RELOAD_REQUIRED**

The supported MCP FULL would run in a backend process that loaded indexer before D2B edits. Stop before FULL and before any restart.

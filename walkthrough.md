# L32D_REMAINING_FRESHNESS_BOUNDARY_AUDIT

## CURRENT_HEAD

`78fe915166c92ff44079d7c5d0ef52f5d8b7ae0e` (`main`, 2026-10-09 20:54:11 +02:00). `git status --short` was empty. The inspected source files matched HEAD (`git diff --exit-code` clean).

## RUNTIME_IDENTITY

| Component | Directly observed identity | Endpoint / relation |
|---|---|---|
| MCP backend | PID 7220; `C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe -u -m contextor.mcp_main`; started 2026-10-09 20:56:13 Europe/Warsaw | Owns listener `127.0.0.1:8765`; parent PID 11600 (`C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`), whose parent is Desktop GUI PID 2684. |
| LIVE authority | Endpoint metadata: PID 7048, `127.0.0.1:59858`, service instance `9f9fa783c97848fca0073f7103a1490a`, lease generation 10, owner PID 2684; endpoint listener is PID 7048 | PID 7048 started 2026-10-09 17:33:50 Europe/Warsaw; parent PID 9040, whose parent is Desktop GUI PID 2684. This process predates the L32C source edit and is reported separately from the MCP backend. |
| Desktop owner | PID 2684, `C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe C:\Temp\Contextor_Repo\main.py --gui`; started 17:33:47 Europe/Warsaw | Parent of the LIVE launcher and MCP launcher. |

The `materialization.py` source last-write time was 2026-10-09 19:58:39 Europe/Warsaw; the MCP backend started afterward, at 20:56:13. The endpoint file and OS listener agree for the LIVE authority. No restart or process mutation was performed.

## L32C_RUNTIME_CERTIFICATION

**L32C_RUNTIME=PASS (source/process evidence; no loaded-function-object introspection).**

Contextor MCP returned the complete current `ensure_cached_analytics` implementation at `contextor/core/analysis/incremental/materialization.py:164-208`; its source response reports `workspace_sync=verified`, revision 139, provenance `live`. The implementation calls `dependency_matrix_inputs_are_fresh`; that predicate rejects `resync_required`, requires genuinely fresh artifact consumption, and requires a non-null graph with a `hard_edges` dict. The correction is therefore present in current source and the MCP process started after the source modification. I did not inspect an imported Python function object's `__code__` inside PID 7220, so this is not direct in-process code introspection.

Direct `get_project_architecture` MCP response:

- `canonical_revision=139`
- `provenance=live`
- `canonical_state=fresh`
- `resync_required=false`
- `workspace_sync=unverified` **exactly as returned**
- `module_count=427`, `parse_stale_modules={}`
- reported module, graph, topology, artifact-consumption, cycles, collisions, and lineage families are all `fresh`

The same response's persisted report bundle references older analysis HEAD `99f9f0a…`; that report snapshot is not current-source certification. Current-source identity is established by Git HEAD and the MCP symbol fetch. Symbol-fetch `workspace_sync=verified` applies to that exact source target and does not replace the project-overlay value `unverified`.

Evidence labels: process/listener and MCP payload are **DIRECT_EVIDENCE**; source-to-consumer paths below are **CODE_PATH_PROVED**; that PID 7220 is the process serving the Contextor tool connection is a process/endpoint correlation, not introspection of its loaded function objects.

## GRAPH_AUTHORITY_ANALYSIS

`ProjectGraph` documents `hard_edges: dict[str, set[str]]` (`contextor/core/domain/graph.py:10-18`), while `RepositoryAnalysisState.dependency_graph` is typed `Any` (`contextor/core/analysis/state_manager.py:89`). The stricter `dependency_matrix_inputs_are_fresh` (`state_manager.py:686-707`) checks `resync_required`, artifact-consumption freshness, graph presence, and `hard_edges` being a dict. `ensure_topology_analytics` and `ensure_cycles` do not call this predicate or equivalent authority checks.

Both materializers return early for a fresh marker; topology returns for fresh populated analytics, and cycles preserves any fresh state, including empty. Both preserve an exact `stale` marker. For any other marker they only require `dependency_graph is not None`; they use `getattr(..., "hard_edges", {}) or {}` and set the family marker to `fresh` after computation. Neither checks `resync_required`, source/module freshness, graph type, or edge-map structure before certifying.

This is publicly reachable. `get_project_architecture` calls `_live_state_overlay`; the overlay gets the engine and calls `diagnostics_summary(root, state)` before independently building a freshness envelope. `get_or_init_engine` obtains a LIVE snapshot without a resync filter and constructs `IncrementalAnalysisEngine`; its constructor unconditionally calls `materialize_incremental_state`. The snapshot IPC returns the state and revision without a resync gate. Thus a resync-required state can enter these materializers, and the public architecture response can carry `canonical_state=stale` alongside fresh family/diagnostic output.

For a parse-stale module without a lost-resync condition, graph-derived facts can describe retained last-known-good canonical truth. `module_current_truth` explicitly labels that provenance `last_known_good`, and `get_project_architecture` includes `parse_stale_modules` plus an advisory warning. This is not the same as proving current disk truth; by itself it is an explicitly surfaced stale-source/LKG condition. `resync_required=true` is different: the derived graph is not certified authoritative, yet topology/cycles can still be labeled fresh.

Topology consumers `get_module_context` and `get_file_edit_context` reject `resync_required` before returning their normal projections and use exact `topology_metrics_state == "fresh"` checks. The public `get_project_architecture` path does not reject resync and exposes a cycles diagnostic summary plus raw family labels.

## TOPOLOGY_AND_CYCLES_RECOMPUTATION_MATRIX

| Condition | Current behavior | Assessment |
|---|---|---|
| `resync_required=True`, existing fresh payload | Fresh payload is preserved without checking graph authority. | **PROVED_DEFECT**: stale canonical envelope can accompany fresh family/diagnostic output. |
| `resync_required=True`, deferred marker, non-null graph | Recomputes and writes `fresh`; no resync gate. | **PROVED_DEFECT**, directly reproduced on an isolated object. |
| Falsey malformed `hard_edges=[]` | `or {}` converts it to an empty map; topology/cycle computation succeeds and marks fresh. `dependency_matrix_inputs_are_fresh` would reject the same shape. | **PROVED_DEFECT**, directly reproduced. Store save/load has no graph-specific shape validation (`git grep` found no `dependency_graph` handling in `store.py`); no persisted malformed-graph roundtrip was executed. |
| Truthy malformed graph | Exceptions from the compute path are caught; for deferred markers the observed code leaves them non-fresh. Some malformed dict/value shapes may still be iterable and are not validated. | **UNKNOWN** for untested truthy malformed shapes; graph authority is not established by existence. |
| Exact stale marker | Returns without recompute and retains stale payload/marker. | Fail-closed for that marker. |
| Missing/`None`/unknown/list/dict marker, trusted valid graph, successful computation | Missing/`None` becomes deferred; other non-stale values fall through. A successful recomputation replaces the marker with `fresh`. | Legitimate recomputation; not marker-only promotion when the graph is authoritative. |
| Valid graph with parse-stale source | May derive fresh analytics from last-known-good graph; aggregate source/canonical status is stale and identifies LKG facts. | Explicit LKG semantics, not a proof of current disk freshness. |

## PUBLIC_MARKER_RESPONSE_CONTRACT

`build_state_freshness` sets aggregate `canonical_state=stale` when `resync_required` is true, but directly copies topology, artifact-consumption, cycles, collisions, and lineage markers into `families` (`query_helpers.py:345-347,443-451`). It does not validate their type or vocabulary. `get_project_architecture` serializes this envelope with `json.dumps`.

Documentation describes these fields as per-family freshness flags/states. It explicitly enumerates `get_name_collisions.availability` as `fresh|stale|deferred|unavailable`, and `get_file_edit_context.syntax_diagnostics.availability` as `fresh|not_materialized|deferred|stale|unavailable`; it does not publish a complete enum for every `state_freshness.families` key. A list/dict marker is therefore emitted as JSON-valid list/dict, but it is not a scalar freshness flag and violates the documented field shape. Unknown strings, bools, integers, lists, and dicts are not normalized by `build_state_freshness`.

L32A guards remain effective in the diagnostics-specific projection: `_availability` accepts only the four string statuses and returns `unavailable` otherwise; syntax status also checks `isinstance(str)`. `get_name_collisions` normalizes malformed availability before its fresh/nonfresh branch. These guards prevent malformed markers from becoming fresh in those branches and avoid list/dict membership `TypeError` there.

They do not close the resync boundary:

- `diagnostics_summary_for_state` counts cycles whenever `cycles_state == "fresh"`; it does not check `resync_required`.
- `ensure_collisions` has no resync gate, and `get_name_collisions` has no resync gate. With complete collision facts, a fresh collision marker remains fresh during engine materialization; the public tool can then return collision facts with `availability="fresh"` while canonical state requires resync.
- `lookup_artifact_by_symbol` rejects a resync-required engine before projecting results. If consumption is unavailable for another reason, it returns `consumers.available=false` and a reason, but echoes the raw marker in `consumers.state`; the response does not report consumer facts as available. The nested `state` field's client contract is not separately documented.

The `get_symbol_lineage` public path has a separate, directly confirmed resync gap. Its docs say resync fails closed, but `query_live_symbol_lineage` builds a target catalog and selected facts without rejecting `state.resync_required`; the state freshness helper merely sets `canonical_state=stale`. IPC dispatch invokes the handler without a resync gate. The isolated query below resolved and returned selected facts while reporting stale canonical state and fresh lineage/index families. This is a proved public freshness-boundary defect, not a malformed-marker defect.

**PUBLIC_MARKERS=PROVED_DEFECT.**

## LINEAGE_INDEX_PUBLIC_REACHABILITY

`RepositoryStateLineageBackend.__init__` validates lineage source mapping but does not inspect the query-index marker (`backend.py:66-87`). `metadata()` performs `query_index_state not in {"not_materialized", "fresh", "stale"}` (`backend.py:151-162`); a list/dict raises `TypeError` at this membership test. The canonical query IPC catches handler exceptions and returns `canonical_query_failed`; it does not terminate the service.

For supported hydration, `_normalize_lineage_query_index_state` ignores the stored query-index marker and rebuilds both indexes from lineage facts, then sets `fresh` or `not_materialized` (`store.py:441-466`; called within `load_snapshot` at 2122 and 2271). `ensure_lineage_query_index` likewise rebuilds non-fresh/inconsistent indexes and writes an allowed status (`materialization.py:15-46`). Incremental/full-analysis writers use `fresh`/`not_materialized` states. The public `get_symbol_lineage` path uses the already-running LIVE owner's state and has no public argument that can set this marker; normal snapshot hydration and supported producers normalize/write it.

Therefore **LINEAGE_INDEX=NOT_PUBLICLY_REACHABLE** for an unhashable list/dict query-index marker through the supported public MCP inputs. Direct internal Python state construction/mutation can reach the `TypeError`; it is not evidence of a public MCP input defect. This verdict does not close the separate resync bug described above.

## ISOLATED_PROBE_RESULTS

1. **Graph probe (synthetic in-memory state only):** `resync_required=True`, deferred topology/cycles markers, and `hard_edges=[]`, `soft_edges=[]` produced `topology_metrics_state="fresh"`, `cycles_state="fresh"`, empty computed facts, and `diagnostics_summary.cycles={count:0, availability:"fresh"}`. A separate `build_state_freshness` call on the same synthetic condition returned `canonical_state="stale"`, with topology and cycles still `fresh`.
2. **Public marker-shape probe (synthetic state only):** list, dict, unknown-string, and bool family markers passed through `build_state_freshness`; `json.dumps` succeeded and preserved those wrong-shaped values in `families`.
3. **Lineage resync probe (existing in-memory fixture; no pytest):** `query_live_symbol_lineage(..., "A17/2", ("interface",))` with `resync_required=True` returned `resolution="resolved"`, selected facts present, `canonical_state="stale"`, and lineage/index families `fresh`.
4. The cycle detector's empty-graph hash cache entry already existed with matching hash and empty result; its last-write time was 18:54:02 Europe/Warsaw, before the probe. The detector returned that cache entry, so no cache write occurred. Post-probe Git status and source diff remained clean. No active LIVE state or snapshot was modified.

The first lineage probe invocation stopped before query because the fixture return arity was unpacked incorrectly; the corrected isolated invocation produced the result above.

## EXACT_SOURCE_PATHS_AND_LINES

- `contextor/core/analysis/incremental/materialization.py:15-46,121-208,211-245,314-357,548-569`
- `contextor/core/analysis/incremental/engine.py:92-104,453-463,780-791,981-1002`
- `contextor/core/analysis/state_manager.py:89-98,227-243,667-707`
- `contextor/core/domain/graph.py:10-18`
- `contextor/core/reporting_engine/graph_analytics.py:2024-2091`
- `contextor/core/graph/cycles.py:47-110,157-273`
- `contextor/mcp/runtime.py:210-268,311-419`
- `contextor/mcp/query_helpers.py:302-483`
- `contextor/core/diagnostics_projection.py:8-29,32-175`
- `contextor/mcp/tools/get_project_architecture.py:162-237,277-369`
- `contextor/mcp/tools/get_module_context.py:185-208,289-337`
- `contextor/mcp/tools/get_file_edit_context.py:232-328,454-477`
- `contextor/mcp/tools/get_name_collisions.py:73-247`
- `contextor/mcp/tools/lookup_artifact_by_symbol.py:10-225`
- `contextor/core/lineage_query/backend.py:63-178`
- `contextor/core/lineage_query/live_query.py:229-282,338-428,471-685`
- `contextor/mcp/tools/get_symbol_lineage.py:105-191`
- `contextor/core/live_state/runtime.py:1045-1081`
- `contextor/core/live_state/ipc.py:2171-2216,2241-2242`
- `contextor/core/live_state/store.py:441-466,1926-2371` (query-index normalizer call sites at 2122 and 2271)
- `contextor/core/live_state/hydration.py:29-112`
- Existing regressions read: `tests/test_topology_bootstrap_and_consumer_truth.py:346-429`; `tests/test_cycles_live_lifecycle.py:103-149,423-458`; `tests/test_mcp_diagnostics.py:41-126`; `tests/analysis/test_lineage_query_backend.py:233-257`; `tests/analysis/test_lineage_live_query.py:1343-1410`.

Existing graph tests cover valid deferred recomputation, exact stale preservation, and compute exceptions, but not resync-required or malformed graph shape. The lineage resync test checks only the stale freshness envelope, not whether selected facts are still returned. Backend tests cover valid, stale, and not-materialized index markers, not list/dict markers. No pytest suite was run.

## UNRESOLVED_GAPS

- `L32C_RUNTIME` is source/process certified; no direct loaded-code-object inspection was performed. The separate LIVE authority PID 7048 predates the source edit; the MCP backend PID 7220 is post-edit.
- The probe establishes a concrete false-fresh graph case; it does not exhaust all truthy malformed edge-map/value shapes. Those shapes lack validation, and their outcomes vary between caught compute errors and successful iteration.
- `state_freshness.families` has no fully enumerated per-family public enum in the retrieved documentation. Raw JSON type leakage is proved, but the documentation does not define behavior for every unknown string/status.
- Query-index list/dict input is not publicly reachable via supported writers/hydration, but direct internal Python callers can still trigger the metadata `TypeError`.
- No pytest execution was requested or performed. Existing regression assertions were read only.

## FILES_CHANGED=NONE

No source, test, or documentation files changed. `walkthrough.md` is the required task report and is excluded from the changed-source list.

## ACTUAL_DIFF=NONE

## FINAL_VERDICT

- `L32C_RUNTIME=PASS` — process/source evidence confirms the MCP backend started after the source edit and Contextor returned the verified corrected implementation; no direct imported-function introspection.
- `GRAPH_TRUST=PROVED_DEFECT` — topology/cycles can be certified fresh when resync is required; a falsey invalid graph is silently converted to empty and certified fresh.
- `PUBLIC_MARKERS=PROVED_DEFECT` — malformed markers pass raw into the public family envelope, and resync-required cycles/collisions/lineage paths can still expose fresh labels or selected facts.
- `LINEAGE_INDEX=NOT_PUBLICLY_REACHABLE` — unhashable marker TypeError exists for direct internal state, but supported snapshot hydration and marker writers normalize it before public query access.
- `OVERALL_L32=PARTIAL` — final pass is blocked by the proved graph and public resync freshness defects; the current observed LIVE state itself is revision 139, fresh, and not resync-required.

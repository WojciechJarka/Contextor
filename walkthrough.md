# CONTEXTOR_C16_P15_EXTERNAL_IMPORT_EFFECTS_F1D

## PREFLIGHT

- Read `C:\Users\DafoO\.codex\AGENTS.md` and the F1D attachment. Initial HEAD `30749cfcd2aeed6d699d6aaff7ea4a51e45cb643`; worktree contained only the prior `walkthrough.md` report modification. No pre-existing source/test changes were overwritten.
- Contextor MCP documentation was read before use. Contextor `get_file_edit_context` resolved all three production owners at canonical revision 1167, `workspace_sync=verified`, with fresh graph/topology/cycles and stale cycle semantics. `get_symbol_lineage` resolved the SCC and diagnostics projection identities; large lineage requests were narrowed rather than assumed complete. Source inspection then verified exact anchors, callers, tests, and LIVE/MCP query path.
- DIRECT_EVIDENCE: existing hard-only SCC implementation, `diagnostics_summary_for_state`, warning-aware projection, `contextor/core/live_state/runtime.py` canonical query, `contextor/core/live_state/ipc.py` locked warning overlay, and `contextor/mcp/runtime.py` narrow transport. `contextor_fact_lineage` does not cover the graph/diagnostics family in its documented v1 scope.

## EXACT_ALGORITHM

- New pure `analyze_soft_dependent_potential_cycles(H,S)` validates and copies the two input edge maps, builds `U=H union S`, then reuses iterative `analyze_import_cycle_topology(U)`. For each cyclic SCC, it emits every internal edge present in S and absent in H, sorted and deduplicated, only when at least one such edge exists. Components and member identities inherit deterministic sorting from the SCC owner. No graph input is mutated and no simple cycles are enumerated.
- The traversal and storage are linear in the graph size before deterministic sorting; the existing SCC owner sorts nodes/adjacency/output, so the strict worst-case bound is O((V+E) log(V+E)), not a literal unsorted O(V+E). The requested linear graph-analysis target is met in traversal count but not in asymptotic sorting cost. This is reported as a precision limit rather than silently claiming strict O(V+E).
- Output scope is `RESTRICTED_HARD_UNION_SOFT_IMPORT_GRAPH_POTENTIAL_ONLY`, with component count, sorted members, sorted soft-only internal edges, and `SOFT_DEPENDENT_POTENTIAL_CYCLE`. It is graph potential, never CPython execution evidence.

## GENERALITY_ARGUMENT

- The algorithm depends only on graph adjacency and SCC membership. In a strongly connected component, every internal edge has a return path and therefore can participate in a directed cycle. The soft-only set difference identifies exactly the uncertainty relevant to this boundary. It has no module-name, package-layout, typing, dataclass, or Contextor-specific branch.
- The indexer, resolver, `build_graph`, canonical hard-edge `detect_cycles`, structural SCC classification, receipts, MODEL_PASS admission, and warning-report schema were left unchanged.

## PRODUCTION_DIFF

- `scc.py`: additive immutable potential-component/result contracts and union-graph analysis.
- `diagnostics_projection.py`: additive `soft_dependent_potential_cycles` diagnostic. Fresh only when canonical state explicitly has `resync_required=False`, `cycles_state=fresh`, and available hard/soft graph maps; stale/missing authority returns count/components `None`, never fresh zero. Existing `cycles.count` remains untouched.
- `live_warning_diagnostics_summary.py`: the validated hard-cycle receipt still projects accepted/active hard paths, while `attention_required` also considers a fresh independent potential-component count. The potential field is carried through unchanged.
- Relevant MCP documentation describes the additive diagnostic and its runtime-safety limit.

## PROVED_INVARIANTS

- A — CODE_PATH_PROVED within the restricted graph: existing iterative SCC enumerates every cyclic SCC of U; the per-component set comprehension visits every S target for every member and includes it exactly when internal and absent from H. Sorted set construction prevents duplicate evidence. The proof assumes explicit finite graph mappings accepted by the existing SCC contract.
- B — CODE_PATH_PROVED: H is copied into `hard`; U is a distinct mapping; no assignment reaches canonical `graph.hard_edges`. Tests compare inputs before/after and retain an empty hard-cycle result for hard A→B / soft B→A.
- C — CONTRACT_PROVED for these changed paths: result kind and scope say POTENTIAL and `runtime_execution_proven=False`; neither receipts nor MODEL_PASS consumers read this result. No runtime safety claim follows.
- D — CODE_PATH_PROVED: warning overlay creates `dict(summary)`, replaces only `cycles` warning fields, retains the independent field, and includes its fresh count in attention. A focused accepted-two-hard-cycles receipt test leaves `active_warning_count=0` and `attention_required=True` with injected independent uncertainty.
- E — CODE_PATH_PROVED for changed paths: canonical `detect_cycles(graph.hard_edges)`, stored `cycles`, structural warning paths/count, and receipt eligibility are unchanged. Focused warning-partition regressions passed; MCP structural count remained 16 after edits.
- F — CODE_PATH_PROVED for the projection gate: absent graph, non-fresh cycles generation, unknown resync authority, and explicit resync yield unavailable/stale with count `None`. A fresh zero is emitted only after checking the canonical graph and its generation proxy. This does not prove filesystem source bytes or runtime adoption; MCP source sync is audited separately.

## CPYTHON_DIFFERENTIAL

- Independent CPython 3.15.2 subprocess test indexes one synthetic repository unchanged across both environments. `pkg.a` contains a lexical `TYPE_CHECKING` guard with `import pkg.b`; `pkg.b` imports `pkg.a.value` before assignment. The union graph reports one potential SCC with soft-only `pkg.a→pkg.b`, while the hard graph has no cycle.
- Normal stdlib typing resolution exits successfully; external `typing.py` outside the indexed repository with `TYPE_CHECKING=True` is resolved first and yields an `ImportError` from the partially initialized `pkg.a`. The same diagnostic remains POTENTIAL in both environments. The CPython outcome supports the F1C counterexample but does not convert a potential graph component into an executable-cycle verdict generally.

## TARGETED_TEST_RESULTS

- 80 passed: new SCC/CPython differential tests, narrow MCP diagnostics tests, warning-aware diagnostics tests, existing SCC tests, external-import authority tests, and affected cycle-warning projection tests. No full suite.
- Both changed MCP documentation JSON files parsed successfully. `git diff --check` found no whitespace errors (Git emitted only Windows line-ending conversion notices).
- Existing narrow-summary equality expectations were changed only to include the new field as `unavailable` for fixtures that provide no graph or explicit resync authority; this is the independently justified fail-closed value, not an adjusted PASS expectation.

## LIVE_MCP_DIAGNOSTIC_REACHABILITY

- Source path: `diagnostics_summary_for_state` → `runtime._repository_canonical_query_handler` → locked `ipc` warning-aware overlay → `mcp.runtime.query_live_diagnostics_summary_narrow` → MCP diagnostics payload. The narrow transport validates required legacy families but permits additive fields. Focused transport test confirms the new field survives that path.
- The already-running MCP process's own Contextor diagnostic envelope at revision 1175 still showed the legacy fields, so runtime adoption of newly loaded core code is UNKNOWN. No restart was performed. This is not certification of current user-visible Desktop presentation.

## PRESERVED_GRAPH_AND_RECEIPT_CONTRACTS

- No edit to indexer, resolver, graph builder, `detect_cycles`, canonical hard SCC, source manifests, receipt generation, or warning-report strict `_PROJECTION_FIELDS`. Potential components are absent from `structural_paths`, `model_pass_paths`, and `active_warning_paths` by construction.

## HARDCODING_AUDIT

- Production logic uses only H/S adjacency and canonical freshness flags. Synthetic package names appear only in independent tests. No typing/stdlib allowlist, repository-shape exception, or unproved MODEL_PASS was added.

## REMAINING_INTEGRATION_GAPS

- Current LIVE process adoption of the new summary shape and Desktop rendering are not verified. Desktop may not display the additive diagnostic; complete user-visible coverage cannot be claimed. A controlled process reload/runtime verification and presentation decision belong to a later authorized stage.
- The graph authority is restricted and source/environment dependent; the diagnostic cannot certify that CPython will or will not execute any particular soft edge. Strict O(V+E) complexity is not claimed because deterministic sorting is used by the existing SCC implementation.

## MCP_POST_CHANGE_AUDIT

- Contextor MCP at revision 1175 reported `workspace_sync=verified`, `syntax_diagnostics=checked_and_none`, fresh graph/topology/cycles, and no advisory warnings for all three edited production sources. `cycle_semantics=stale` was preserved as stale, not represented as fresh.
- Structural diagnostic count remained 16 before and after. Hard/soft graph-producing files were unchanged; no unexpected structural-cycle change is evidenced. The MCP response is source/graph evidence, not process adoption or runtime safety. A transient revision-1174 unverified source-generation response was rechecked; revision 1175 verified all targets.

## FILES_CHANGED

- `contextor/core/cycle_semantics/scc.py`
- `contextor/core/diagnostics_projection.py`
- `contextor/core/cycle_semantics/live_warning_diagnostics_summary.py`
- `contextor/mcp/docs/get_analysis_status.json`
- `contextor/mcp/docs/get_project_architecture.json`
- `tests/test_soft_dependent_potential_cycles.py` (new)
- `tests/mcp/test_live_diagnostics_narrow.py`
- `tests/test_cycle_semantics_live_warning_diagnostics_summary.py`

`walkthrough.md` is the required report and excluded from this inventory under AGENTS.md.

## FULL_DIFFS

Actual complete production, documentation, and test diffs follow. The new untracked test is represented as a `/dev/null` addition.

```diff
diff --git a/contextor/core/cycle_semantics/live_warning_diagnostics_summary.py b/contextor/core/cycle_semantics/live_warning_diagnostics_summary.py
index b8aa88a..1caf029 100644
--- a/contextor/core/cycle_semantics/live_warning_diagnostics_summary.py
+++ b/contextor/core/cycle_semantics/live_warning_diagnostics_summary.py
@@ -120,6 +120,7 @@ def project_locked_warning_diagnostics_summary(
         cycles = summary.get("cycles")
         syntax = summary.get("syntax_errors")
         collisions = summary.get("name_collisions")
+        potential = summary.get("soft_dependent_potential_cycles")
 
         if (
             type(cycles) is not dict
@@ -182,6 +183,8 @@ def project_locked_warning_diagnostics_summary(
                 syntax["count"],
                 collisions["count"],
                 active_count,
+                potential.get("count") if type(potential) is dict
+                and potential.get("availability") == "fresh" else None,
             )
         )
         return result
diff --git a/contextor/core/cycle_semantics/scc.py b/contextor/core/cycle_semantics/scc.py
index e9daf4d..1a7c6dc 100644
--- a/contextor/core/cycle_semantics/scc.py
+++ b/contextor/core/cycle_semantics/scc.py
@@ -25,6 +25,20 @@ class ImportCycleTopology:
     evidence_scope: str = "STRUCTURAL_HARD_IMPORT_GRAPH"
 
 
+@dataclass(frozen=True)
+class SoftDependentPotentialComponent:
+    members: tuple[str, ...]
+    soft_only_internal_edges: tuple[tuple[str, str], ...]
+    kind: str = "SOFT_DEPENDENT_POTENTIAL_CYCLE"
+
+
+@dataclass(frozen=True)
+class SoftDependentPotentialCycles:
+    component_count: int
+    components: tuple[SoftDependentPotentialComponent, ...]
+    evidence_scope: str = "RESTRICTED_HARD_UNION_SOFT_IMPORT_GRAPH_POTENTIAL_ONLY"
+
+
 def analyze_import_cycle_topology(
     hard_edges: Mapping[
         str,
@@ -129,3 +143,54 @@ def analyze_import_cycle_topology(
         total_scc_count=all_scc_count,
         cyclic_components=tuple(sorted(cyclic, key=lambda item: item.members)),
     )
+
+
+def analyze_soft_dependent_potential_cycles(
+    hard_edges: Mapping[str, set[str] | frozenset[str] | list[str] | tuple[str, ...]],
+    soft_edges: Mapping[str, set[str] | frozenset[str] | list[str] | tuple[str, ...]],
+) -> SoftDependentPotentialCycles:
+    """Find cyclic union components containing internal soft-only edges.
+
+    The result describes graph potential, not import execution. Both inputs
+    remain unchanged and the canonical hard-only topology remains separate.
+    """
+    if not isinstance(hard_edges, Mapping) or not isinstance(soft_edges, Mapping):
+        raise TypeError("hard_edges and soft_edges must be mappings")
+
+    union: dict[str, set[str]] = {}
+    hard: dict[str, set[str]] = {}
+    for edge_map, normalized_map in ((hard_edges, hard), (soft_edges, None)):
+        for source, targets in edge_map.items():
+            if not isinstance(source, str) or not source:
+                raise ValueError("invalid source module")
+            if not isinstance(targets, (set, frozenset, tuple, list)):
+                raise TypeError("targets must be an explicit collection")
+            normalized: set[str] = set()
+            for target in targets:
+                if not isinstance(target, str) or not target:
+                    raise ValueError("invalid target module")
+                normalized.add(target)
+            union.setdefault(source, set()).update(normalized)
+            if normalized_map is not None:
+                normalized_map[source] = normalized
+
+    topology = analyze_import_cycle_topology(union)
+    components: list[SoftDependentPotentialComponent] = []
+    for component in topology.cyclic_components:
+        members = set(component.members)
+        soft_only = tuple(sorted({
+            (source, target)
+            for source in component.members
+            for target in soft_edges.get(source, ())
+            if target in members and target not in hard.get(source, ())
+        }))
+        if soft_only:
+            components.append(SoftDependentPotentialComponent(
+                members=component.members,
+                soft_only_internal_edges=soft_only,
+            ))
+
+    return SoftDependentPotentialCycles(
+        component_count=len(components),
+        components=tuple(components),
+    )
diff --git a/contextor/core/diagnostics_projection.py b/contextor/core/diagnostics_projection.py
index ca3990d..5aa92cc 100644
--- a/contextor/core/diagnostics_projection.py
+++ b/contextor/core/diagnostics_projection.py
@@ -4,10 +4,61 @@ from __future__ import annotations
 
 from typing import Any
 
+from collections.abc import Mapping
+
+from contextor.core.cycle_semantics.scc import (
+    analyze_soft_dependent_potential_cycles,
+)
+
 
 _CYCLE_COUNT_SEMANTICS = (
     "DFS_BACK_EDGE_PATHS_DEDUP_ROTATION_NOT_ALL_SIMPLE_CYCLES"
 )
+_POTENTIAL_CYCLE_SCOPE = (
+    "RESTRICTED_HARD_UNION_SOFT_IMPORT_GRAPH_POTENTIAL_ONLY"
+)
+
+
+def _soft_dependent_cycle_diagnostic(state: Any) -> dict[str, Any]:
+    unavailable = {
+        "count": None,
+        "components": None,
+        "availability": "unavailable",
+        "evidence_scope": _POTENTIAL_CYCLE_SCOPE,
+        "runtime_execution_proven": False,
+    }
+    if state is None:
+        return unavailable
+    if getattr(state, "resync_required", None) is True:
+        return {**unavailable, "availability": "stale"}
+    if getattr(state, "resync_required", None) is not False:
+        return unavailable
+    cycle_state = getattr(state, "cycles_state", None)
+    if cycle_state != "fresh":
+        availability = cycle_state if cycle_state in {
+            "stale", "deferred", "unavailable",
+        } else "unavailable"
+        return {**unavailable, "availability": availability}
+    graph = getattr(state, "dependency_graph", None)
+    hard = getattr(graph, "hard_edges", None)
+    soft = getattr(graph, "soft_edges", None)
+    if not isinstance(hard, Mapping) or not isinstance(soft, Mapping):
+        return unavailable
+    try:
+        result = analyze_soft_dependent_potential_cycles(hard, soft)
+    except (TypeError, ValueError):
+        return unavailable
+    return {
+        "count": result.component_count,
+        "components": tuple({
+            "kind": component.kind,
+            "members": component.members,
+            "soft_only_internal_edges": component.soft_only_internal_edges,
+        } for component in result.components),
+        "availability": "fresh",
+        "evidence_scope": result.evidence_scope,
+        "runtime_execution_proven": False,
+    }
 
 
 def _availability(
@@ -40,6 +91,7 @@ def diagnostics_summary_for_state(
     """Return canonical diagnostic counts plus freshness."""
 
     if state is None:
+        potential = _soft_dependent_cycle_diagnostic(None)
         unavailable = {
             "count": None,
             "availability": "unavailable",
@@ -59,15 +111,18 @@ def diagnostics_summary_for_state(
                 "availability": "unavailable",
             },
             "cycles": unavailable_cycles,
+            "soft_dependent_potential_cycles": potential,
             "attention_required": False,
             "availability": {
                 "syntax_errors": "unavailable",
                 "name_collisions": "unavailable",
                 "cycles": "unavailable",
+                "soft_dependent_potential_cycles": potential["availability"],
             },
         }
 
     if getattr(state, "resync_required", False):
+        potential = _soft_dependent_cycle_diagnostic(state)
         unavailable = {
             "count": None,
             "availability": "stale",
@@ -86,11 +141,13 @@ def diagnostics_summary_for_state(
                 "availability": "stale",
             },
             "cycles": unavailable_cycles,
+            "soft_dependent_potential_cycles": potential,
             "attention_required": False,
             "availability": {
                 "syntax_errors": "stale",
                 "name_collisions": "stale",
                 "cycles": "stale",
+                "soft_dependent_potential_cycles": potential["availability"],
             },
         }
 
@@ -170,6 +227,7 @@ def diagnostics_summary_for_state(
         if cycle_availability == "fresh"
         else None
     )
+    potential = _soft_dependent_cycle_diagnostic(state)
 
     syntax_issue = (
         syntax_values
@@ -183,6 +241,7 @@ def diagnostics_summary_for_state(
             syntax_issue,
             collision_count,
             cycle_count,
+            potential["count"],
         )
     )
 
@@ -203,11 +262,13 @@ def diagnostics_summary_for_state(
             "availability": cycle_availability,
             "count_semantics": _CYCLE_COUNT_SEMANTICS,
         },
+        "soft_dependent_potential_cycles": potential,
         "attention_required": bool(attention),
         "availability": {
             "syntax_errors": syntax_availability,
             "name_collisions": collision_availability,
             "cycles": cycle_availability,
+            "soft_dependent_potential_cycles": potential["availability"],
         },
     }
 
diff --git a/contextor/mcp/docs/get_analysis_status.json b/contextor/mcp/docs/get_analysis_status.json
index 7e36d8e..afb0d54 100644
--- a/contextor/mcp/docs/get_analysis_status.json
+++ b/contextor/mcp/docs/get_analysis_status.json
@@ -17,7 +17,7 @@
     "For an explicit completed job with live_publish_status=pending_verification and saved publication correlation, this read-only tool reconnects to the existing verified LIVE authority with endpoint reconciliation disabled and verifies service instance and process start identity. If the mutation job ID was lost, it verifies the canonical generation key against the authority repository identity and performs a read-only lookup in the existing mutation coordinator. A recovered job ID is durably saved; only its exact receipt can resolve publication status. It never submits a publication, update, or FULL analysis.",
     "Publication acceptance is not success. A completed analysis may retain pending_verification until the exact mutation job is verified. Replaced authority yields unverified_authority_changed; missing/evicted job remains pending. Matching LIVE revision alone cannot certify the publication. Historical timed_out jobs without exact correlation are not promoted.",
     "Every job also exposes durable LIVE publication state. Project jobs move\nfrom ``live_publish_status='pending'`` to ``success``, ``recovery_required``,\n``pending_verification`` or ``failed``; an analysis failure before publication reports\n``not_attempted``. ``success`` requires an exact completed mutation receipt\nfor the requested generation on the verified service. ``recovery_required``\nmeans the generation was installed but LIVE health needs recovery verification.\nOnly these verified installed outcomes expose ``live_publish_revision``.\nA missing receipt remains ``pending_verification``; replaced authority yields\n``unverified_authority_changed``. Layer and single-file jobs report\n``not_applicable`` because their shared facade updates canonical state\nincrementally rather than publishing a new global baseline here.",
-    "Where diagnostics_summary.cycles is exposed, its count is the number of unique normalized DFS back-edge paths after rotational deduplication, not the SCC count, cyclic-module count, cyclic-edge count, runtime failure count, or exhaustive number of simple cycles. diagnostics_attention_required retains its structural diagnostic meaning."
+    "Where diagnostics_summary.cycles is exposed, its count is the number of unique normalized DFS back-edge paths after rotational deduplication, not the SCC count, cyclic-module count, cyclic-edge count, runtime failure count, or exhaustive number of simple cycles. The additive soft_dependent_potential_cycles field describes cyclic SCCs in the restricted hard/soft union graph with internal soft-only edges; it does not prove CPython execution. Its count is unavailable rather than zero when graph authority is insufficient. diagnostics_attention_required can include this independent potential-cycle signal."
   ],
   "errors": [
     "Explicit ``job_id`` bypasses active job ambiguity detection. When ``job_id`` is omitted and multiple active jobs exist, ``status: 'ambiguous_job'`` is returned.\nTerminal states are ``completed``, ``failed`` and ``interrupted``. A job\nleft running by a previous MCP server process is marked ``interrupted``\nrather than remaining permanently ambiguous. A queued/running job owned by the current MCP process is also reconciled to `interrupted` with `error='worker_not_active'` when its in-memory worker is no longer alive. If persistence of the reconciled interrupted state fails, the current call still returns the interrupted state and reports the persistence failure in `message` instead of returning stale queued/running status.",
diff --git a/contextor/mcp/docs/get_project_architecture.json b/contextor/mcp/docs/get_project_architecture.json
index 91161e5..84c6ca3 100644
--- a/contextor/mcp/docs/get_project_architecture.json
+++ b/contextor/mcp/docs/get_project_architecture.json
@@ -31,7 +31,8 @@
     "live_state.state_freshness.families.cycle_semantics independently describes current canonical semantic evidence as fresh, stale, deferred, or unavailable; structural cycles remain a separate family. Fresh requires positive canonical generation coherence and a SHA-256 match with the current in-memory hard dependency graph.",
     "The cycle_semantics family does not reread analyzed Python source or rerun semantic AST analysis. Historical FULL report freshness never proves current LIVE freshness.",
     "diagnostics_summary.cycles.count is the number of unique normalized DFS back-edge paths after rotational deduplication. It is not the number of SCCs, cyclic modules, cyclic edges, runtime failures, or every possible simple cycle. Those measurements can differ; for example, 16 DFS paths can belong to 2 cyclic SCCs containing 33 modules.",
-    "diagnostics_attention_required retains its existing structural meaning and may be true when structural cycles exist. direct_candidate_attention_required is a separate semantic signal and does not establish Python initialization failure or runtime safety."
+    "diagnostics_summary.soft_dependent_potential_cycles is an additive restricted-graph diagnostic over hard_edges union soft_edges. Fresh results report cyclic SCC members and internal soft-only edges; they indicate potential cycles, not proven CPython execution. Missing or stale graph authority yields an unavailable/stale count rather than zero. Existing diagnostics_summary.cycles.count still counts hard-only DFS paths.",
+    "diagnostics_attention_required may be true for hard structural cycles or fresh soft-dependent potential cycles. A hard-cycle model-acceptance receipt does not suppress the independent potential-cycle signal. direct_candidate_attention_required is a separate semantic signal and does not establish Python initialization failure or runtime safety."
   ],
   "errors": [
     "unsupported_fields: one or more requested fields are not global project report sections.",
diff --git a/tests/mcp/test_live_diagnostics_narrow.py b/tests/mcp/test_live_diagnostics_narrow.py
index 8f74c06..4956326 100644
--- a/tests/mcp/test_live_diagnostics_narrow.py
+++ b/tests/mcp/test_live_diagnostics_narrow.py
@@ -71,11 +71,19 @@ def _fresh_summary():
             "availability": "fresh",
             "count_semantics": "DFS_BACK_EDGE_PATHS_DEDUP_ROTATION_NOT_ALL_SIMPLE_CYCLES",
         },
+        "soft_dependent_potential_cycles": {
+            "count": None,
+            "components": None,
+            "availability": "unavailable",
+            "evidence_scope": "RESTRICTED_HARD_UNION_SOFT_IMPORT_GRAPH_POTENTIAL_ONLY",
+            "runtime_execution_proven": False,
+        },
         "attention_required": True,
         "availability": {
             "syntax_errors": "fresh",
             "name_collisions": "fresh",
             "cycles": "fresh",
+            "soft_dependent_potential_cycles": "unavailable",
         },
     }
 
@@ -377,6 +385,7 @@ def test_diagnostics_summary_transport_error_fails_closed_without_cache(
         "syntax_errors": "unavailable",
         "name_collisions": "unavailable",
         "cycles": "unavailable",
+        "soft_dependent_potential_cycles": "unavailable",
     }
 
     assert (
diff --git a/tests/test_cycle_semantics_live_warning_diagnostics_summary.py b/tests/test_cycle_semantics_live_warning_diagnostics_summary.py
index 0bab1ec..07ca16a 100644
--- a/tests/test_cycle_semantics_live_warning_diagnostics_summary.py
+++ b/tests/test_cycle_semantics_live_warning_diagnostics_summary.py
@@ -289,9 +289,43 @@ def test_t14_narrow_mcp_transport_uses_owner_summary(
         assert result.summary["cycles"]["count"] == 2
         assert result.summary["cycles"]["model_pass_count"] == 2
         assert result.summary["cycles"]["active_warning_count"] == 0
+        assert "soft_dependent_potential_cycles" in result.summary
         assert result.summary["attention_required"] is False
 
 
+def test_soft_uncertainty_survives_accepted_hard_cycle_receipt(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        with server._lock:
+            raw = diagnostics_summary_for_state(state)
+            report = server._owner_cycle_warning_report_locked()
+            raw["soft_dependent_potential_cycles"] = {
+                "count": 1,
+                "components": ({
+                    "kind": "SOFT_DEPENDENT_POTENTIAL_CYCLE",
+                    "members": ("independent.a", "independent.b"),
+                    "soft_only_internal_edges": (("independent.b", "independent.a"),),
+                },),
+                "availability": "fresh",
+                "evidence_scope": "RESTRICTED_HARD_UNION_SOFT_IMPORT_GRAPH_POTENTIAL_ONLY",
+                "runtime_execution_proven": False,
+            }
+            result = project_locked_warning_diagnostics_summary(
+                raw, report,
+                canonical_revision=server._revision,
+                activity_epoch=server._activity_epoch,
+                authority_identity=server._authority_identity,
+            )
+
+        assert result["cycles"]["active_warning_count"] == 0
+        assert result["cycles"]["model_pass_count"] == 2
+        assert result["soft_dependent_potential_cycles"] == raw["soft_dependent_potential_cycles"]
+        assert result["attention_required"] is True
+
+
 def test_t15_repeated_query_is_read_only(
     tmp_path, isolated_dirs,
 ):
diff --git a/tests/test_soft_dependent_potential_cycles.py b/tests/test_soft_dependent_potential_cycles.py
new file mode 100644
index 0000000..368f308
--- /dev/null
+++ b/tests/test_soft_dependent_potential_cycles.py
@@ -0,0 +1,117 @@
+"""Potential union-graph cycles remain separate from hard-cycle evidence."""
+
+from types import SimpleNamespace
+import subprocess
+import sys
+
+import pytest
+
+from contextor.core.cycle_semantics.scc import (
+    analyze_import_cycle_topology,
+    analyze_soft_dependent_potential_cycles,
+)
+from contextor.core.diagnostics_projection import diagnostics_summary_for_state
+from contextor.core.symbol_engine.indexer import index_repository
+from contextor.core.graph.graph import build_graph
+
+
+def test_soft_edge_closes_cycle_without_changing_hard_graph():
+    hard = {"a": {"b"}, "b": set()}
+    soft = {"b": {"a"}}
+    before = ({key: set(value) for key, value in hard.items()},
+              {key: set(value) for key, value in soft.items()})
+    result = analyze_soft_dependent_potential_cycles(hard, soft)
+
+    assert analyze_import_cycle_topology(hard).cyclic_components == ()
+    assert result.component_count == 1
+    assert result.components[0].members == ("a", "b")
+    assert result.components[0].soft_only_internal_edges == (("b", "a"),)
+    assert (hard, soft) == before
+
+
+def test_soft_internal_evidence_is_complete_and_deduplicated():
+    hard = {"a": {"b"}, "b": {"a"}}
+    soft = {"a": ["b", "b"], "b": ["b", "b"]}
+    result = analyze_soft_dependent_potential_cycles(hard, soft)
+    assert len(analyze_import_cycle_topology(hard).cyclic_components) == 1
+    assert result.component_count == 1
+    assert result.components[0].soft_only_internal_edges == (("b", "b"),)
+
+
+def test_acyclic_soft_edge_and_duplicate_hard_edge_do_not_create_potential():
+    assert analyze_soft_dependent_potential_cycles(
+        {"a": {"b"}}, {"b": {"c"}}
+    ).component_count == 0
+    assert analyze_soft_dependent_potential_cycles(
+        {"a": {"b"}, "b": {"a"}}, {"a": {"b"}}
+    ).component_count == 0
+
+
+def test_freshness_gate_never_asserts_zero_for_missing_or_stale_graph():
+    state = SimpleNamespace(
+        resync_required=False, cycles_state="fresh", cycles=[],
+        collisions_state="fresh", collisions=[],
+        syntax_diagnostics_state="fresh", syntax_diagnostics_by_path={},
+        dependency_graph=SimpleNamespace(
+            hard_edges={"a": {"b"}}, soft_edges={"b": {"a"}},
+        ),
+    )
+    fresh = diagnostics_summary_for_state(state)
+    assert fresh["soft_dependent_potential_cycles"]["count"] == 1
+    assert fresh["soft_dependent_potential_cycles"]["availability"] == "fresh"
+    assert fresh["soft_dependent_potential_cycles"]["runtime_execution_proven"] is False
+    state.cycles_state = "stale"
+    stale = diagnostics_summary_for_state(state)["soft_dependent_potential_cycles"]
+    assert stale["count"] is None and stale["availability"] == "stale"
+    state.cycles_state = "fresh"
+    state.dependency_graph = None
+    missing = diagnostics_summary_for_state(state)["soft_dependent_potential_cycles"]
+    assert missing["count"] is None and missing["availability"] == "unavailable"
+
+
+@pytest.mark.skipif(sys.version_info[:3] != (3, 15, 2), reason="CPython 3.15.2 oracle")
+def test_same_repository_has_potential_graph_cycle_in_both_import_environments(
+    tmp_path, monkeypatch,
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    repo = tmp_path / "repo"
+    package = repo / "pkg"
+    package.mkdir(parents=True)
+    (package / "__init__.py").write_bytes(b"pass\n")
+    (package / "a.py").write_bytes(
+        b"from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
+        b"    import pkg.b\nvalue = 1\n"
+    )
+    (package / "b.py").write_bytes(b"from pkg.a import value\n")
+    external = tmp_path / "external"
+    external.mkdir()
+    (external / "typing.py").write_bytes(b"TYPE_CHECKING = True\n")
+
+    indexed = index_repository(str(repo))
+    graph = build_graph(indexed.modules)
+    result = analyze_soft_dependent_potential_cycles(
+        graph.hard_edges, graph.soft_edges,
+    )
+    assert result.component_count == 1
+    assert result.components[0].members == ("pkg.a", "pkg.b")
+    assert result.components[0].soft_only_internal_edges == (("pkg.a", "pkg.b"),)
+
+    code = (
+        "import sys; sys.path.insert(0, sys.argv[1]); "
+        "sys.path.insert(0, sys.argv[2]) if len(sys.argv) > 2 else None; "
+        "import typing; print(typing.__file__, flush=True); import pkg.a"
+    )
+    normal = subprocess.run(
+        [sys.executable, "-I", "-S", "-c", code, str(repo)],
+        capture_output=True, text=True, check=False,
+    )
+    overridden = subprocess.run(
+        [sys.executable, "-I", "-S", "-c", code, str(repo), str(external)],
+        capture_output=True, text=True, check=False,
+    )
+    assert normal.returncode == 0
+    assert "typing.py" in normal.stdout
+    assert str(external) not in normal.stdout
+    assert overridden.returncode != 0
+    assert str(external / "typing.py") in overridden.stdout
+    assert "partially initialized module 'pkg.a'" in overridden.stderr
```

## FINAL_VERDICT

SOURCE/TEST PASS, RUNTIME ADOPTION AND DESKTOP PRESENTATION UNVERIFIED. The scoped structural uncertainty diagnostic is implemented and passes focused validation. No global FINAL PASS is claimed. STOP for auditor review.

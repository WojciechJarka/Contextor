# get_dataflow_lineage v1 implementation

LINEAGE_ARCHITECTURE=PURE_PROJECTION
NEW_CANONICAL_FACTS=NONE
QUERY_TIME_SOURCE_AST=NO

PUBLIC_SIGNATURE=get_dataflow_lineage(repo_path: str, family: str, direction: str = "both", depth: int = 3) -> str
REGISTERED_TOOL_COUNT=27

ARTIFACT_CONSUMPTION_FRESH=Implemented. The full-analysis builder branch and incremental consumer-slice update branch project into canonical RepositoryAnalysisState.artifact_consumption only when artifact_consumption_is_fresh(state) and resync_required is false.
ARTIFACT_CONSUMPTION_STALE=Implemented. Stale or incomplete coverage retains the family/state contract nodes, stops freshness-dependent persistence/hydration/projection edges, and returns status=stale or partial with an explicit gap; no consumer payload is fabricated.
ARTIFACT_CONSUMPTION_BRANCHES=FULL raw_artifact_consumer_facts -> build_canonical_artifact_consumption -> family anchor/state; INCREMENTAL module_usage_facts -> _rebuild_consumer_slice -> family anchor/state. Confirmed projections are get_artifact_blast_radius and get_module_blast_radius.

SYNTAX_DIAGNOSTICS_FRESH=Implemented. Family-wide syntax_diagnostics_state=fresh gates the canonical syntax map; full RepositoryIndex parse/skipped and incremental prepared-source commit branches are projected, then persisted/hydrated and exposed through get_file_edit_context.
SYNTAX_DIAGNOSTICS_STALE=Implemented. Deferred, not_materialized, or stale state returns status=unavailable or stale, retains owner/state nodes, and reports an explicit downstream gap; it never turns missing facts into errors=[].
SYNTAX_BRANCHES=FULL repository_index_parse_results -> build_syntax_diagnostics_from_index -> canonical state; INCREMENTAL prepared_source_update -> IncrementalAnalysisEngine._commit_syntax_candidate -> canonical state.

SYMBOL_CALLS_COMPLETE=Implemented. The lifecycle uses extract_module_usage_facts, ModuleUsageFacts/module_usages[*].symbol_calls, snapshot persistence/hydration, and get_symbol_call_context without symbol-level BFS.
SYMBOL_CALLS_PARTIAL=Implemented. Incomplete module coverage returns status=partial and one aggregate unresolved coverage gap; it does not emit one unresolved record per module.
SYMBOL_CALLS_COVERAGE=Top-level bounded summary: canonical_module_count, symbol_calls_materialized_count, reference_evidence_materialized_count, missing_symbol_calls_materialization_count, missing_reference_evidence_count, and stale_module_count.

CONFIDENCE_VALUES=confirmed
STRUCTURAL_EDGES_EMITTED=NO
UNRESOLVED_EXPLICIT=Yes. Identity-resolution gaps, stale/deferred/unavailable family gaps, resync gaps, and one aggregate symbol-call coverage gap are deterministic and explicit. Unknown is not empty; unavailable is not no edge.

DIRECTION_DEPTH_CONTRACT=Anchor family:<family> is always retained. upstream follows reverse directed edges, downstream follows forward directed edges, both is the union; depth is positive edge hops from the anchor and is bounded to 4. Freshness is evaluated before traversal filtering.
DETERMINISTIC_OUTPUT=Nodes sorted by (type,id), edges by (source,target,type), projections and unresolved records sorted deterministically. No representation parameter was added.
ACTIVE_ID_RESOLUTION=Active registry snapshot is read through the LIVE registry read transaction when available, otherwise the active persisted registry maps are used. Artifact IDs are attached dynamically; missing active identities keep stable qualified names with unresolved gaps. No IDs or recovery identities are allocated.
HARDCODED_ARTIFACT_IDS=NO
HARDCODED_SOURCE_LINES=NO

SOURCE_READS=NONE by lineage query; canonical state hydration/registry reads only.
AST_PARSES=NONE
REPORT_READS=NONE
REPOSITORY_SCANS=NONE
INTERNAL_MCP_TOOL_CALLS=NONE

DOCS=Added contextor/mcp/docs/get_dataflow_lineage.json and the docs index entry. The document describes family-level architectural lineage, confirmed-only edges, partial/unresolved semantics, no query-time source/AST work, and the boundary with module blast, symbol call context, and symbol implementation. No mutual blast-radius cross-reference was added.
TESTS=Dedicated tests/mcp/tools/test_get_dataflow_lineage.py added; centralized registration/docs parity and 26->27 count contracts updated. Focused result: 112 passed, 1 warning. git diff --check for implementation files (excluding walkthrough and telemetry log): PASS. Ruff was not available in the repository virtualenv.
DECISION=READY_FOR_RUNTIME_CERTIFICATION

MCP_RESTART_REQUIRED=YES
LIVE_RESTART_REQUIRED=NO
RUNTIME_CERTIFICATION_PENDING=YES
FULL_SUITE_RUN_BY_AGENT=NO

FILES_CHANGED=
- contextor/mcp/tools/get_dataflow_lineage.py
- contextor/mcp/docs/get_dataflow_lineage.json
- contextor/mcp/docs/index.json
- contextor/mcp/docs/get_module_blast_radius.json (corrected the pre-existing empty-string runtime default in the docs parity contract)
- contextor/mcp_server.py
- tests/mcp/tools/test_get_dataflow_lineage.py
- tests/test_live_activity_status.py
- tests/test_mcp_diagnostics.py
- tests/test_mcp_documentation.py
- tests/test_mcp_split_s2a.py
- tests/test_mcp_split_s2b.py
- tests/test_mcp_split_s2c.py
- tests/test_mcp_split_s2d.py
- tests/test_mcp_split_s2e.py

TELEMETRY_NOTE=Contextor's tracked runtime telemetry log was appended during MCP discovery/tests; it is not an implementation change and is excluded from the raw implementation diff below. An attempted restore was blocked by the active log writer.

COMPLETE_RAW_UNIFIED_DIFF_EXCLUDING_WALKTHROUGH_MD=

```diff
diff --git a/contextor/mcp/docs/get_module_blast_radius.json b/contextor/mcp/docs/get_module_blast_radius.json
index 13edd07..bbcef7a 100644
--- a/contextor/mcp/docs/get_module_blast_radius.json
+++ b/contextor/mcp/docs/get_module_blast_radius.json
@@ -6,7 +6,7 @@
   ],
   "parameters": [
     "repo_path (string, required): canonical repository root.",
-    "module (string, required): canonical dotted module name, repository-relative or absolute Python path, or active module ID.",
+    "module (string, default \"\"): canonical dotted module name, repository-relative or absolute Python path, or active module ID.",
     "compact (boolean, default true): select the complete_compact serialization policy; this never bounds or samples artifacts, consumers, or downstream identities. With representation=auto, false selects readable_named and true permits indexed negotiation.",
     "fields (array of strings or null, default null): optional top-level projection. Allowed values are module, module_id, artifact_count_total, artifact_count_returned, artifacts, aggregate, data_source, and state_freshness. Projection can intentionally omit semantic collections, but does not change facts used for aggregate calculation.",
     "representation (string, default auto): lossless repeated-module encoding: auto, named, or indexed. Auto chooses the smaller complete candidate without an interaction envelope.",
diff --git a/contextor/mcp/docs/index.json b/contextor/mcp/docs/index.json
index 0d18799..7ea1060 100644
--- a/contextor/mcp/docs/index.json
+++ b/contextor/mcp/docs/index.json
@@ -128,6 +128,11 @@
       "filename": "get_module_blast_radius.json",
       "short_description": "Return the complete lossless per-artifact and aggregate blast-radius projection for one module from fresh canonical state."
     },
+    {
+      "tool": "get_dataflow_lineage",
+      "filename": "get_dataflow_lineage.json",
+      "short_description": "Return the bounded confirmed architectural lifecycle of one canonical data family from canonical/LIVE state, without runtime dataflow reconstruction."
+    },
     {
       "tool": "get_mcp_documentation",
       "filename": "get_mcp_documentation.json",
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
index 91bb87c..0a87acb 100644
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -185,6 +185,9 @@ from contextor.mcp.tools.get_artifact_blast_radius import (
 from contextor.mcp.tools.get_module_blast_radius import (
     get_module_blast_radius as _get_module_blast_radius_impl,
 )
+from contextor.mcp.tools.get_dataflow_lineage import (
+    get_dataflow_lineage as _get_dataflow_lineage_impl,
+)
 from contextor.mcp.tools.get_name_collisions import (
     get_name_collisions as _get_name_collisions_impl,
 )
@@ -516,6 +519,7 @@ REGISTERED_MCP_TOOL_NAMES: tuple[str, ...] = (
     "get_name_collisions",
     "get_mcp_documentation",
     "get_module_blast_radius",
+    "get_dataflow_lineage",
 )
 
 
@@ -561,6 +565,7 @@ get_symbol_call_context = register_mcp_tool(_get_symbol_call_context_impl, name=
 get_name_collisions = register_mcp_tool(_get_name_collisions_impl, name="get_name_collisions")
 get_mcp_documentation = register_mcp_tool(_get_mcp_documentation_impl, name="get_mcp_documentation")
 get_module_blast_radius = register_mcp_tool(_get_module_blast_radius_impl, name="get_module_blast_radius")
+get_dataflow_lineage = register_mcp_tool(_get_dataflow_lineage_impl, name="get_dataflow_lineage")
 
 
 def main():
diff --git a/tests/test_live_activity_status.py b/tests/test_live_activity_status.py
index 1db6d0c..379ced9 100644
--- a/tests/test_live_activity_status.py
+++ b/tests/test_live_activity_status.py
@@ -16,7 +16,7 @@ Covers all concrete correctness and evidence requirements:
 13. Central MCP wrapper read-only success
 14. Central MCP wrapper failure re-raise & logging
 15. MCP analyze_project wrapper & canonical publication separation
-16. All 26 registered FastMCP tools coverage & registry synchronization
+16. All 27 registered FastMCP tools coverage & registry synchronization
 17. Real server-to-GUI burst ordering, zero dropped events & zero duplicates
 18. Desktop vs MCP full analysis publication equivalence
 """
@@ -664,10 +664,10 @@ def test_mcp_analyze_project_wrapper_and_canonical_publish_equivalence(live_serv
     assert events[1]["canonical_revision"] == 2
 
 
-def test_all_26_registered_mcp_tools_telemetry_against_fastmcp_registry(monkeypatch):
+def test_all_27_registered_mcp_tools_telemetry_against_fastmcp_registry(monkeypatch):
     fastmcp_tool_names = set(mcp._tool_manager._tools.keys())
     assert set(REGISTERED_MCP_TOOL_NAMES) == fastmcp_tool_names
-    assert len(REGISTERED_MCP_TOOL_NAMES) == 26
+    assert len(REGISTERED_MCP_TOOL_NAMES) == 27
 
     calls_emitted = []
 
diff --git a/tests/test_mcp_diagnostics.py b/tests/test_mcp_diagnostics.py
index 5e90b37..3f1aef5 100644
--- a/tests/test_mcp_diagnostics.py
+++ b/tests/test_mcp_diagnostics.py
@@ -321,4 +321,4 @@ def test_cheap_filters_run_before_severity_and_severity_filter_survives(tmp_path
 
 def test_registered_name_collision_tool_and_shared_summary_wrapper():
     assert "get_name_collisions" in mcp_server.REGISTERED_MCP_TOOL_NAMES
-    assert len(mcp_server.REGISTERED_MCP_TOOL_NAMES) == 26
+    assert len(mcp_server.REGISTERED_MCP_TOOL_NAMES) == 27
diff --git a/tests/test_mcp_documentation.py b/tests/test_mcp_documentation.py
index d367a95..5512ce5 100644
--- a/tests/test_mcp_documentation.py
+++ b/tests/test_mcp_documentation.py
@@ -72,7 +72,7 @@ def test_documentation_default_returns_only_index(monkeypatch):
     result = json.loads(mcp_server.get_mcp_documentation.fn())
 
     assert result["version"]
-    assert len(result["tools"]) == 26
+    assert len(result["tools"]) == 27
     assert loaded == [documentation.INDEX_PATH]
 
 
diff --git a/tests/test_mcp_split_s2a.py b/tests/test_mcp_split_s2a.py
index 63619f3..a113bca 100644
--- a/tests/test_mcp_split_s2a.py
+++ b/tests/test_mcp_split_s2a.py
@@ -46,6 +46,7 @@ _EXPECTED_ORDER = [
     "get_name_collisions",
     "get_mcp_documentation",
     "get_module_blast_radius",
+    "get_dataflow_lineage",
 ]
 
 _IMPLEMENTATIONS = {
diff --git a/tests/test_mcp_split_s2b.py b/tests/test_mcp_split_s2b.py
index 04d4d35..8dc7033 100644
--- a/tests/test_mcp_split_s2b.py
+++ b/tests/test_mcp_split_s2b.py
@@ -27,7 +27,7 @@ _EXPECTED_ORDER = [
     "lookup_index_entries", "get_artifacts_for_module",
     "lookup_artifact_by_symbol", "search_source", "get_source_range",
     "get_symbol_call_context", "get_name_collisions", "get_mcp_documentation",
-    "get_module_blast_radius",
+    "get_module_blast_radius", "get_dataflow_lineage",
 ]
 
 _IMPLEMENTATIONS = {
diff --git a/tests/test_mcp_split_s2c.py b/tests/test_mcp_split_s2c.py
index 7eade3f..4b87815 100644
--- a/tests/test_mcp_split_s2c.py
+++ b/tests/test_mcp_split_s2c.py
@@ -25,6 +25,7 @@ _EXPECTED_ORDER = [
     "lookup_artifact_by_symbol", "search_source", "get_source_range",
     "get_symbol_call_context", "get_name_collisions",
     "get_mcp_documentation", "get_module_blast_radius",
+    "get_dataflow_lineage",
 ]
 
 _IMPLEMENTATIONS = {
diff --git a/tests/test_mcp_split_s2d.py b/tests/test_mcp_split_s2d.py
index 85c4519..c232f87 100644
--- a/tests/test_mcp_split_s2d.py
+++ b/tests/test_mcp_split_s2d.py
@@ -22,7 +22,7 @@ _EXPECTED_ORDER = [
     "lookup_index_entries", "get_artifacts_for_module",
     "lookup_artifact_by_symbol", "search_source", "get_source_range",
     "get_symbol_call_context", "get_name_collisions", "get_mcp_documentation",
-    "get_module_blast_radius",
+    "get_module_blast_radius", "get_dataflow_lineage",
 ]
 
 _IMPLEMENTATIONS = {
diff --git a/tests/test_mcp_split_s2e.py b/tests/test_mcp_split_s2e.py
index 195bb43..2219397 100644
--- a/tests/test_mcp_split_s2e.py
+++ b/tests/test_mcp_split_s2e.py
@@ -23,7 +23,7 @@ _EXPECTED_ORDER = [
     "lookup_index_entries", "get_artifacts_for_module",
     "lookup_artifact_by_symbol", "search_source", "get_source_range",
     "get_symbol_call_context", "get_name_collisions", "get_mcp_documentation",
-    "get_module_blast_radius",
+    "get_module_blast_radius", "get_dataflow_lineage",
 ]
 
 _IMPLEMENTATIONS = {

diff --git a/contextor/mcp/tools/get_dataflow_lineage.py b/contextor/mcp/tools/get_dataflow_lineage.py
new file mode 100644
--- /dev/null
+++ b/contextor/mcp/tools/get_dataflow_lineage.py
@@ -0,0 +1,855 @@
+import json
+from pathlib import Path
+from typing import Any
+
+from contextor.core.analysis.state_manager import (
+    artifact_consumption_is_fresh,
+    module_current_truth,
+)
+from contextor.core.report_query import registry_maps_from_state
+from contextor.mcp import query_helpers
+from contextor.mcp import runtime as mcp_runtime
+from contextor.mcp.output_guard import guard_large_output
+
+
+_FAMILIES = ("artifact_consumption", "syntax_diagnostics", "symbol_calls")
+_DIRECTIONS = ("upstream", "downstream", "both")
+_MAX_DEPTH = 4
+_STORE_ID = "store:live_snapshot"
+_UNAVAILABLE_EDGE_TYPES = {"READS", "UPDATES", "PERSISTS", "HYDRATES", "PROJECTS", "EXPOSES"}
+
+
+def _symbol(module: str, name: str) -> str:
+    return f"{module}::{name}"
+
+
+_SPECS: dict[str, dict[str, Any]] = {
+    "artifact_consumption": {
+        "state_field": "artifact_consumption",
+        "state_state_field": "artifact_consumption_state",
+        "branches": (
+            {
+                "input": "raw_artifact_consumer_facts",
+                "producer": _symbol(
+                    "contextor.core.analysis.state_manager",
+                    "build_canonical_artifact_consumption",
+                ),
+                "branch": "full",
+                "input_kind": "indexed_artifact_consumer_facts",
+            },
+            {
+                "input": "module_usage_facts",
+                "producer": _symbol(
+                    "contextor.core.analysis.incremental.plan_executor",
+                    "_rebuild_consumer_slice",
+                ),
+                "branch": "incremental",
+                "input_kind": "canonical_module_usage_facts",
+            },
+        ),
+        "updates": (
+            _symbol(
+                "contextor.core.analysis.incremental.plan_executor",
+                "_rebuild_consumer_slice",
+            ),
+        ),
+        "materializers": (
+            _symbol(
+                "contextor.core.analysis.state_manager",
+                "build_canonical_artifact_consumption",
+            ),
+        ),
+        "projections": (
+            (
+                "get_artifact_blast_radius",
+                _symbol(
+                    "contextor.mcp.tools.get_artifact_blast_radius",
+                    "get_artifact_blast_radius",
+                ),
+            ),
+            (
+                "get_module_blast_radius",
+                _symbol(
+                    "contextor.mcp.tools.get_module_blast_radius",
+                    "get_module_blast_radius",
+                ),
+            ),
+        ),
+    },
+    "syntax_diagnostics": {
+        "state_field": "syntax_diagnostics_by_path",
+        "state_state_field": "syntax_diagnostics_state",
+        "branches": (
+            {
+                "input": "repository_index_parse_results",
+                "producer": _symbol(
+                    "contextor.core.analysis.state_manager",
+                    "build_syntax_diagnostics_from_index",
+                ),
+                "branch": "full",
+                "input_kind": "repository_index_parse_and_skipped_facts",
+            },
+            {
+                "input": "prepared_source_update",
+                "producer": _symbol(
+                    "contextor.core.analysis.incremental.engine",
+                    "IncrementalAnalysisEngine._commit_syntax_candidate",
+                ),
+                "branch": "incremental",
+                "input_kind": "prepared_incremental_syntax_candidate",
+            },
+        ),
+        "updates": (
+            _symbol(
+                "contextor.core.analysis.incremental.engine",
+                "IncrementalAnalysisEngine._commit_syntax_candidate",
+            ),
+        ),
+        "materializers": (
+            _symbol(
+                "contextor.core.analysis.state_manager",
+                "build_syntax_diagnostics_from_index",
+            ),
+        ),
+        "projections": (
+            (
+                "get_file_edit_context",
+                _symbol(
+                    "contextor.mcp.tools.get_file_edit_context",
+                    "get_file_edit_context",
+                ),
+            ),
+        ),
+    },
+    "symbol_calls": {
+        "state_field": "module_usages[*].symbol_calls",
+        "state_state_field": "module_usages[*].symbol_calls_materialized",
+        "branches": (
+            {
+                "input": "reference_extraction_facts",
+                "producer": _symbol(
+                    "contextor.core.reference.engine",
+                    "extract_module_usage_facts",
+                ),
+                "branch": "extraction",
+                "input_kind": "canonical_reference_extraction_input",
+                "output": "module_usage_facts",
+            },
+            {
+                "input": "full_baseline_reuse",
+                "producer": _symbol(
+                    "contextor.core.reference.module_usage_reuse",
+                    "build_module_usage_baseline_with_reuse",
+                ),
+                "branch": "full_baseline_reuse",
+                "input_kind": "current_module_usage_or_extraction_facts",
+            },
+            {
+                "input": "incremental_prepared_usage",
+                "producer": _symbol(
+                    "contextor.core.analysis.incremental.preparation",
+                    "prepare_source_update",
+                ),
+                "branch": "incremental_prepared_usage",
+                "input_kind": "prepared_incremental_ast_usage_delta",
+            },
+            {
+                "input": "materialization_backfill",
+                "producer": _symbol(
+                    "contextor.core.analysis.incremental.materialization",
+                    "ensure_module_usages",
+                ),
+                "branch": "ensure_module_usages_backfill",
+                "input_kind": "missing_or_unmaterialized_module_usage_facts",
+            },
+        ),
+        "updates": (
+            _symbol(
+                "contextor.core.analysis.incremental.preparation",
+                "prepare_source_update",
+            ),
+            _symbol(
+                "contextor.core.analysis.incremental.materialization",
+                "ensure_module_usages",
+            ),
+        ),
+        "materializers": (
+            _symbol(
+                "contextor.core.reference.module_usage_reuse",
+                "build_module_usage_baseline_with_reuse",
+            ),
+        ),
+        "projections": (
+            (
+                "get_symbol_call_context",
+                _symbol(
+                    "contextor.mcp.tools.get_symbol_call_context",
+                    "get_symbol_call_context",
+                ),
+            ),
+        ),
+    },
+}
+
+
+def _state_id(spec: dict[str, Any]) -> str:
+    return f"state:RepositoryAnalysisState.{spec['state_field']}"
+
+
+def _data_family_id(name: str) -> str:
+    return f"data_family:{name}"
+
+
+def _add_node(nodes: dict[str, dict[str, Any]], node: dict[str, Any]) -> str:
+    node_id = str(node["id"])
+    nodes.setdefault(node_id, node)
+    return node_id
+
+
+def _add_data_family_node(
+    nodes: dict[str, dict[str, Any]],
+    name: str,
+    *,
+    anchor: bool = False,
+) -> str:
+    node_id = f"family:{name}" if anchor else _data_family_id(name)
+    return _add_node(
+        nodes,
+        {
+            "id": node_id,
+            "type": "data_family",
+            "name": name,
+            **({"role": "anchor"} if anchor else {}),
+        },
+    )
+
+
+def _add_symbol_node(
+    nodes: dict[str, dict[str, Any]],
+    qualified_name: str,
+    artifact_path_to_id: dict[str, Any],
+    module_path_to_id: dict[str, Any],
+    identity_gaps: dict[str, dict[str, Any]],
+) -> str:
+    active_id = artifact_path_to_id.get(qualified_name)
+    module_name = qualified_name.split("::", 1)[0]
+    if active_id:
+        node_id = f"symbol:{active_id}"
+    else:
+        node_id = f"symbol:{qualified_name}"
+        identity_gaps.setdefault(
+            node_id,
+            {
+                "from": node_id,
+                "to": None,
+                "expected_edge": "ACTIVE_ID_RESOLUTION",
+                "status": "unresolved",
+                "reason": "Active artifact identity unavailable; stable qualified name retained.",
+                "kind": "identity_resolution",
+                "qualified_name": qualified_name,
+            },
+        )
+    node: dict[str, Any] = {
+        "id": node_id,
+        "type": "symbol",
+        "name": qualified_name,
+        "qualified_name": qualified_name,
+        "module": module_name,
+    }
+    if active_id:
+        node["artifact_id"] = str(active_id)
+    module_id = module_path_to_id.get(module_name)
+    if module_id:
+        node["module_id"] = str(module_id)
+    _add_node(nodes, node)
+    return node_id
+
+
+def _add_state_node(nodes: dict[str, dict[str, Any]], spec: dict[str, Any]) -> str:
+    state_id = _state_id(spec)
+    _add_node(
+        nodes,
+        {
+            "id": state_id,
+            "type": "canonical_state_field",
+            "name": spec["state_field"],
+            "state_owner": "RepositoryAnalysisState",
+            "state_field": spec["state_field"],
+            "family_state_field": spec["state_state_field"],
+        },
+    )
+    return state_id
+
+
+def _add_tool_node(nodes: dict[str, dict[str, Any]], tool_name: str) -> str:
+    return _add_node(
+        nodes,
+        {
+            "id": f"tool:{tool_name}",
+            "type": "public_projection",
+            "name": tool_name,
+            "tool": tool_name,
+        },
+    )
+
+
+def _evidence(kind: str, **values: Any) -> dict[str, Any]:
+    result = {"kind": kind}
+    result.update({key: value for key, value in values.items() if value is not None})
+    return result
+
+
+def _add_edge(
+    edges: dict[tuple[str, str, str], dict[str, Any]],
+    source: str,
+    target: str,
+    edge_type: str,
+    evidence: dict[str, Any],
+    *,
+    via: str | None = None,
+) -> None:
+    edge = {
+        "source": source,
+        "target": target,
+        "type": edge_type,
+        "confidence": "confirmed",
+        "evidence": evidence,
+    }
+    if via is not None:
+        edge["via"] = via
+    edges.setdefault((source, target, edge_type), edge)
+
+
+def _read_registry_maps(root: Path, engine: Any) -> tuple[dict, dict, dict, dict]:
+    registry = getattr(engine, "registry", None)
+    read_transaction = getattr(registry, "read_transaction", None)
+    if (
+        (
+            getattr(engine, "provenance", None) == "live"
+            or getattr(getattr(engine, "state", None), "provenance", None) == "live"
+        )
+        and registry is not None
+        and callable(read_transaction)
+        and hasattr(registry, "_state")
+    ):
+        try:
+            with read_transaction():
+                return registry_maps_from_state(registry._state)
+        except Exception:
+            pass
+    try:
+        return query_helpers.read_registries(root)
+    except Exception:
+        return {}, {}, {}, {}
+
+
+def _build_contract(
+    family: str,
+    spec: dict[str, Any],
+    registry_maps: tuple[dict, dict, dict, dict],
+) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str, str], dict[str, Any]], dict[str, dict[str, Any]]]:
+    module_path_to_id, _module_id_to_path, artifact_path_to_id, _artifact_id_to_path = registry_maps
+    nodes: dict[str, dict[str, Any]] = {}
+    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
+    identity_gaps: dict[str, dict[str, Any]] = {}
+
+    anchor_id = _add_data_family_node(nodes, family, anchor=True)
+    state_id = _add_state_node(nodes, spec)
+    _add_node(
+        nodes,
+        {
+            "id": _STORE_ID,
+            "type": "persistence_store",
+            "name": "live_snapshot",
+            "store": "live_snapshot",
+        },
+    )
+
+    for branch in spec["branches"]:
+        input_id = _add_data_family_node(nodes, branch["input"])
+        producer_id = _add_symbol_node(
+            nodes,
+            branch["producer"],
+            artifact_path_to_id,
+            module_path_to_id,
+            identity_gaps,
+        )
+        _add_edge(
+            edges,
+            input_id,
+            producer_id,
+            "READS",
+            _evidence(
+                branch["input_kind"],
+                qualified_symbol=branch["producer"],
+                branch=branch["branch"],
+            ),
+        )
+        _add_edge(
+            edges,
+            producer_id,
+            anchor_id,
+            "PRODUCES",
+            _evidence(
+                "explicit_producer",
+                qualified_symbol=branch["producer"],
+                branch=branch["branch"],
+            ),
+        )
+        if branch.get("output"):
+            output_id = _add_data_family_node(nodes, branch["output"])
+            _add_edge(
+                edges,
+                producer_id,
+                output_id,
+                "PRODUCES",
+                _evidence(
+                    "explicit_materialized_fact_output",
+                    qualified_symbol=branch["producer"],
+                    branch=branch["branch"],
+                ),
+            )
+            _add_edge(
+                edges,
+                output_id,
+                anchor_id,
+                "TRANSFORMS",
+                _evidence(
+                    "named_field_projection",
+                    field="symbol_calls",
+                    branch=branch["branch"],
+                ),
+                via=branch["producer"],
+            )
+
+    # The family anchor is the canonical fact collection entering its state field.
+    _add_edge(
+        edges,
+        anchor_id,
+        state_id,
+        "MATERIALIZES",
+        _evidence(
+            "canonical_state_field",
+            canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
+        ),
+    )
+
+    for materializer in spec["materializers"]:
+        materializer_id = _add_symbol_node(
+            nodes,
+            materializer,
+            artifact_path_to_id,
+            module_path_to_id,
+            identity_gaps,
+        )
+        _add_edge(
+            edges,
+            materializer_id,
+            state_id,
+            "MATERIALIZES",
+            _evidence(
+                "canonical_builder_assignment",
+                qualified_symbol=materializer,
+                canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
+            ),
+        )
+
+    for updater in spec["updates"]:
+        updater_id = _add_symbol_node(
+            nodes,
+            updater,
+            artifact_path_to_id,
+            module_path_to_id,
+            identity_gaps,
+        )
+        _add_edge(
+            edges,
+            updater_id,
+            state_id,
+            "UPDATES",
+            _evidence(
+                "incremental_candidate_commit",
+                qualified_symbol=updater,
+                canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
+            ),
+        )
+
+    persistence_via = _symbol("contextor.core.analysis.state_manager", "save_engine_state")
+    _add_edge(
+        edges,
+        state_id,
+        _STORE_ID,
+        "PERSISTS",
+        _evidence(
+            "complete_engine_snapshot",
+            canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
+        ),
+        via=persistence_via,
+    )
+    hydration_via = _symbol(
+        "contextor.core.live_state.hydration", "hydrate_repository_engine"
+    )
+    _add_edge(
+        edges,
+        _STORE_ID,
+        state_id,
+        "HYDRATES",
+        _evidence(
+            "complete_engine_snapshot_load",
+            canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
+        ),
+        via=hydration_via,
+    )
+
+    for tool_name, projection in spec["projections"]:
+        tool_id = _add_tool_node(nodes, tool_name)
+        projection_id = _add_symbol_node(
+            nodes,
+            projection,
+            artifact_path_to_id,
+            module_path_to_id,
+            identity_gaps,
+        )
+        _add_edge(
+            edges,
+            state_id,
+            projection_id,
+            "READS",
+            _evidence(
+                "canonical_projection_read",
+                qualified_symbol=projection,
+                canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
+            ),
+        )
+        _add_edge(
+            edges,
+            state_id,
+            tool_id,
+            "PROJECTS",
+            _evidence(
+                "public_projection",
+                qualified_symbol=projection,
+                canonical_state_field=f"RepositoryAnalysisState.{spec['state_field']}",
+            ),
+        )
+        _add_edge(
+            edges,
+            projection_id,
+            tool_id,
+            "EXPOSES",
+            _evidence(
+                "explicit_mcp_registration",
+                qualified_symbol=projection,
+                registration_owner="contextor.mcp_server::register_mcp_tool",
+            ),
+        )
+
+    return nodes, edges, identity_gaps
+
+
+def _symbol_flag(value: Any, name: str) -> bool:
+    if isinstance(value, dict):
+        return bool(value.get(name, False))
+    return bool(getattr(value, name, False))
+
+
+def _coverage(state: Any) -> dict[str, int]:
+    modules = getattr(state, "modules", {}) or {}
+    usages = getattr(state, "module_usages", {}) or {}
+    module_names = sorted(str(name) for name in modules) if isinstance(modules, dict) else []
+    canonical_module_count = len(module_names)
+    calls_count = 0
+    evidence_count = 0
+    stale_module_count = 0
+    for module_name in module_names:
+        usage = usages.get(module_name) if isinstance(usages, dict) else None
+        calls_count += int(_symbol_flag(usage, "symbol_calls_materialized"))
+        evidence_count += int(_symbol_flag(usage, "reference_evidence_materialized"))
+        if not module_current_truth(state, module_name)["available"]:
+            stale_module_count += 1
+    return {
+        "canonical_module_count": canonical_module_count,
+        "symbol_calls_materialized_count": calls_count,
+        "reference_evidence_materialized_count": evidence_count,
+        "missing_symbol_calls_materialization_count": canonical_module_count - calls_count,
+        "missing_reference_evidence_count": canonical_module_count - evidence_count,
+        "stale_module_count": stale_module_count,
+    }
+
+
+def _fallback_freshness(state: Any, engine: Any) -> dict[str, Any]:
+    provenance = getattr(state, "provenance", None) or getattr(engine, "provenance", None) or "snapshot"
+    revision = getattr(state, "revision", None)
+    if revision is None:
+        revision = getattr(engine, "revision", None)
+    return {
+        "canonical_state": "stale" if getattr(state, "resync_required", False) else "fresh",
+        "workspace_sync": "unverified",
+        "canonical_revision": revision,
+        "provenance": provenance,
+        "families": {},
+        "advisory_warning": None,
+    }
+
+
+def _freshness(root: Path, state: Any, engine: Any, family: str, family_state: str, coverage: dict[str, int] | None) -> dict[str, Any]:
+    try:
+        result = query_helpers.build_state_freshness(root, state, engine=engine)
+    except Exception:
+        result = _fallback_freshness(state, engine)
+    result = dict(result)
+    result["resync_required"] = bool(getattr(state, "resync_required", False))
+    families = dict(result.get("families") or {})
+    families[family] = family_state
+    if coverage is not None:
+        families["module_usages"] = (
+            "fresh"
+            if not any(
+                coverage[name] > 0
+                for name in (
+                    "missing_symbol_calls_materialization_count",
+                    "missing_reference_evidence_count",
+                    "stale_module_count",
+                )
+            )
+            else "partial"
+        )
+    result["families"] = families
+    return result
+
+
+def _family_gate(family: str, state: Any) -> tuple[str, dict[str, int] | None, str | None]:
+    if family == "artifact_consumption":
+        state_value = str(getattr(state, "artifact_consumption_state", "deferred"))
+        if getattr(state, "resync_required", False):
+            return "unavailable", None, "Canonical LIVE state requires resync."
+        if artifact_consumption_is_fresh(state):
+            return "fresh", None, None
+        status = "stale" if state_value == "stale" else "partial"
+        return status, None, f"artifact_consumption is not fresh or has incomplete canonical coverage (state={state_value})."
+    if family == "syntax_diagnostics":
+        state_value = str(getattr(state, "syntax_diagnostics_state", "not_materialized"))
+        facts = getattr(state, "syntax_diagnostics_by_path", None)
+        if getattr(state, "resync_required", False):
+            return "unavailable", None, "Canonical LIVE state requires resync."
+        if state_value == "fresh" and isinstance(facts, dict):
+            return "fresh", None, None
+        status = "stale" if state_value == "stale" else "unavailable"
+        return status, None, f"syntax_diagnostics is not queryable as a fresh canonical family (state={state_value})."
+    coverage = _coverage(state)
+    if getattr(state, "resync_required", False):
+        return "unavailable", coverage, "Canonical LIVE state requires resync."
+    incomplete = any(
+        coverage[name] > 0
+        for name in (
+            "missing_symbol_calls_materialization_count",
+            "missing_reference_evidence_count",
+            "stale_module_count",
+        )
+    )
+    if incomplete:
+        return "partial", coverage, "Canonical module_usages coverage is incomplete."
+    return "fresh", coverage, None
+
+
+def _gap(
+    *,
+    source: str | None,
+    target: str | None,
+    expected_edge: str,
+    status: str,
+    reason: str,
+    **values: Any,
+) -> dict[str, Any]:
+    result: dict[str, Any] = {
+        "from": source,
+        "to": target,
+        "expected_edge": expected_edge,
+        "status": status,
+        "reason": reason,
+    }
+    result.update(values)
+    return result
+
+
+def _reachable(
+    anchor_id: str,
+    edges: dict[tuple[str, str, str], dict[str, Any]],
+    direction: str,
+    depth: int,
+) -> tuple[set[str], set[tuple[str, str, str]]]:
+    nodes = {anchor_id}
+    selected_edges: set[tuple[str, str, str]] = set()
+    frontier = {anchor_id}
+    for _ in range(depth):
+        next_frontier: set[str] = set()
+        for key, edge in edges.items():
+            source = edge["source"]
+            target = edge["target"]
+            can_downstream = direction in {"downstream", "both"} and source in frontier
+            can_upstream = direction in {"upstream", "both"} and target in frontier
+            if can_downstream:
+                selected_edges.add(key)
+                if target not in nodes:
+                    next_frontier.add(target)
+                nodes.add(target)
+            if can_upstream:
+                selected_edges.add(key)
+                if source not in nodes:
+                    next_frontier.add(source)
+                nodes.add(source)
+        frontier = next_frontier
+        if not frontier:
+            break
+    return nodes, selected_edges
+
+
+def _serialize(result: dict[str, Any], edge_count: int) -> str:
+    serialized = json.dumps(result, indent=2, ensure_ascii=False)
+    return guard_large_output(
+        serialized,
+        allow_large_output=False,
+        requested_count=edge_count,
+        reason="The lineage projection exceeds the recommended context size.",
+        retry_instruction="Reduce depth/direction or use the same bounded lineage request after the state is narrowed.",
+    )
+
+
+def _error(status: str, **values: Any) -> str:
+    payload = {"status": status}
+    payload.update(values)
+    return json.dumps(payload, indent=2, ensure_ascii=False)
+
+
+def get_dataflow_lineage(
+    repo_path: str,
+    family: str,
+    direction: str = "both",
+    depth: int = 3,
+) -> str:
+    if not isinstance(family, str) or family not in _FAMILIES:
+        return _error("invalid_family", allowed=list(_FAMILIES), family=family)
+    if direction not in _DIRECTIONS:
+        return _error("invalid_direction", allowed=list(_DIRECTIONS), direction=direction)
+    if isinstance(depth, bool) or not isinstance(depth, int) or not 1 <= depth <= _MAX_DEPTH:
+        return _error("invalid_depth", minimum=1, maximum=_MAX_DEPTH, depth=depth)
+
+    root = Path(repo_path).expanduser().resolve()
+    spec = _SPECS[family]
+    anchor_id = f"family:{family}"
+    state_id = _state_id(spec)
+    try:
+        engine = mcp_runtime.get_or_init_engine(root)
+    except Exception as exc:
+        return _error("unavailable", reason="canonical_live_state_unavailable", detail=str(exc))
+
+    state = getattr(engine, "state", None) if engine is not None else None
+    registry_maps = _read_registry_maps(root, engine) if engine is not None else ({}, {}, {}, {})
+    nodes, all_edges, identity_gaps = _build_contract(family, spec, registry_maps)
+
+    coverage: dict[str, int] | None = None
+    if state is None:
+        gate_status, coverage, gate_reason = "unavailable", None, "No usable canonical engine state was available."
+    else:
+        gate_status, coverage, gate_reason = _family_gate(family, state)
+
+    freshness = _freshness(
+        root,
+        state,
+        engine,
+        family,
+        "unavailable" if state is None else gate_status,
+        coverage,
+    )
+    provenance = freshness.get("provenance")
+    data_source = "live_canonical_state" if provenance == "live" else "snapshot_canonical_state"
+
+    edges = all_edges
+    if gate_status in {"unavailable", "stale"} or (
+        family == "artifact_consumption" and gate_status == "partial"
+    ):
+        edges = {
+            key: edge
+            for key, edge in all_edges.items()
+            if edge["type"] not in _UNAVAILABLE_EDGE_TYPES
+        }
+
+    unresolved = list(identity_gaps.values())
+    if gate_reason is not None and not (coverage is not None and gate_status == "partial"):
+        unresolved.append(
+            _gap(
+                source=anchor_id,
+                target=state_id,
+                expected_edge="CURRENT_CANONICAL_FAMILY_DATA",
+                status=(
+                    "stale"
+                    if gate_status == "stale"
+                    else "unavailable"
+                    if gate_status == "unavailable"
+                    else "partial"
+                    if gate_status == "partial"
+                    else "unresolved"
+                ),
+                reason=gate_reason,
+                family_state=freshness["families"].get(family),
+                **({"coverage": coverage} if coverage is not None else {}),
+            )
+        )
+    if coverage is not None and gate_status == "partial":
+        unresolved.append(
+            _gap(
+                source=anchor_id,
+                target=state_id,
+                expected_edge="COMPLETE_SYMBOL_CALLS_COVERAGE",
+                status="partial",
+                reason="Some canonical modules lack materialized symbol-call or reference-evidence facts.",
+                coverage=coverage,
+            )
+        )
+
+    reachable_nodes, selected_edges = _reachable(anchor_id, edges, direction, depth)
+    reachable_nodes.add(anchor_id)
+    selected_nodes = [
+        node for node in nodes.values() if node["id"] in reachable_nodes
+    ]
+    selected_edges_list = [
+        edge for key, edge in edges.items() if key in selected_edges
+    ]
+    selected_nodes.sort(key=lambda item: (item["type"], item["id"]))
+    selected_edges_list.sort(key=lambda item: (item["source"], item["target"], item["type"]))
+    selected_node_ids = {item["id"] for item in selected_nodes}
+    unresolved = [
+        item
+        for item in unresolved
+        if item.get("kind") != "identity_resolution" or item.get("from") in selected_node_ids
+    ]
+    unresolved.sort(
+        key=lambda item: (
+            str(item.get("from") or ""),
+            str(item.get("to") or ""),
+            str(item.get("expected_edge") or ""),
+            str(item.get("status") or ""),
+            str(item.get("kind") or ""),
+        )
+    )
+    projections = sorted(
+        node["id"]
+        for node in selected_nodes
+        if node["type"] == "public_projection"
+    )
+    result: dict[str, Any] = {
+        "status": "unavailable" if state is None else gate_status if gate_status != "fresh" else "ok",
+        "family": family,
+        "owner": [state_id],
+        "entry_points": [anchor_id],
+        "nodes": selected_nodes,
+        "edges": selected_edges_list,
+        "public_projections": projections,
+        "unresolved": unresolved,
+        "freshness": freshness,
+        "data_source": data_source,
+    }
+    if coverage is not None:
+        result["coverage"] = coverage
+    return _serialize(result, len(selected_edges_list))
+
diff --git a/contextor/mcp/docs/get_dataflow_lineage.json b/contextor/mcp/docs/get_dataflow_lineage.json
new file mode 100644
--- /dev/null
+++ b/contextor/mcp/docs/get_dataflow_lineage.json
@@ -0,0 +1,41 @@
+{
+  "version": "1.0.0",
+  "tool": "get_dataflow_lineage",
+  "purpose": [
+    "Return the confirmed architectural lifecycle of one canonical data family as a bounded directed projection over canonical/LIVE state."
+  ],
+  "parameters": [
+    "repo_path (string, required): canonical repository root.",
+    "family (string, required): one v1 family: artifact_consumption, syntax_diagnostics, or symbol_calls.",
+    "direction (string, default both): traversal relative to the family anchor; allowed values are upstream, downstream, or both.",
+    "depth (integer, default 3): positive edge-hop depth from family:<family>; maximum 4; booleans are invalid."
+  ],
+  "behavior": [
+    "The anchor is always family:<family>; upstream follows confirmed edges toward producers and owners, downstream follows edges toward canonical state, persistence, hydration, consumers, and public projections, and both is their union.",
+    "This is family-level architectural lineage only. V1 has no path, module, or symbol scope and does not return symbol caller/callee neighborhoods or module blast-radius payloads.",
+    "Only confidence=confirmed edges are emitted. Unsupported or unproven data semantics are represented as explicit unresolved gaps rather than structural or inferred edges.",
+    "The projection uses declarative family contracts plus active canonical identities. It performs no query-time repository scan, source/AST reconstruction, report read, or internal MCP-tool call, and it does not reconstruct runtime value flow, taint, objects, variables, or dynamic dispatch.",
+    "Active artifact and module IDs are attached when present in the current canonical registry. If an active artifact identity is unavailable, the stable qualified symbol name remains and an identity-resolution gap is reported; no ID is allocated and recovery identities are not used.",
+    "The lineage complements get_module_blast_radius breadth and get_symbol_call_context symbol neighborhoods. Use get_symbol_implementation for exact owner or transformer implementation drilldown."
+  ],
+  "freshness": [
+    "Every response includes canonical_revision, provenance, resync_required, canonical_state, and family freshness. Provenance is explicitly live or snapshot.",
+    "artifact_consumption requires artifact_consumption_is_fresh, exact canonical coverage, and resync_required=false. Stale or incomplete consumption stops freshness-dependent downstream edges and never fabricates consumers.",
+    "syntax_diagnostics requires syntax_diagnostics_state=fresh and a canonical fact map for the family. The contract is family-wide and does not validate a requested path.",
+    "symbol_calls reports bounded canonical_module_count, symbol_calls_materialized_count, reference_evidence_materialized_count, missing_symbol_calls_materialization_count, and missing_reference_evidence_count. Incomplete coverage returns partial with one aggregate gap; it does not emit one gap per module.",
+    "resync_required=true fails closed for current canonical data edges with status unavailable or stale and an explicit gap. Unknown is not empty and unavailable is not no edge."
+  ],
+  "errors": [
+    "Invalid family, direction, or depth returns a controlled diagnostic.",
+    "Missing canonical state, stale/deferred/not_materialized family facts, incomplete symbol-call coverage, resync, and missing active identities remain explicit through status and unresolved fields; the tool never converts those conditions into empty-success lineage."
+  ],
+  "usage_notes": [
+    "Start with the default direction=both and depth=3. Use depth=1 or direction=upstream/downstream for a compact lifecycle slice; depth is always measured from the family anchor.",
+    "A partial or unavailable response is actionable: inspect freshness and the single or bounded unresolved gap before treating the returned confirmed edges as complete."
+  ],
+  "examples": [
+    "get_dataflow_lineage(repo_path, family=\"artifact_consumption\", direction=\"both\", depth=3)",
+    "get_dataflow_lineage(repo_path, family=\"symbol_calls\", direction=\"downstream\", depth=2)"
+  ]
+}
+
diff --git a/tests/mcp/tools/test_get_dataflow_lineage.py b/tests/mcp/tools/test_get_dataflow_lineage.py
new file mode 100644
--- /dev/null
+++ b/tests/mcp/tools/test_get_dataflow_lineage.py
@@ -0,0 +1,430 @@
+import ast
+import inspect
+import json
+from contextlib import nullcontext
+from types import SimpleNamespace
+
+from contextor import mcp_server
+from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.mcp import query_helpers, runtime as mcp_runtime
+from contextor.mcp.documentation import load_tool_document
+from contextor.mcp.tools.get_dataflow_lineage import get_dataflow_lineage
+
+
+_SYMBOLS = {
+    "contextor.core.analysis.state_manager::build_canonical_artifact_consumption": "A901/1",
+    "contextor.core.analysis.incremental.plan_executor::_rebuild_consumer_slice": "A902/1",
+    "contextor.core.analysis.state_manager::build_syntax_diagnostics_from_index": "A903/1",
+    "contextor.core.analysis.incremental.engine::IncrementalAnalysisEngine._commit_syntax_candidate": "A904/1",
+    "contextor.core.reference.engine::extract_module_usage_facts": "A905/1",
+    "contextor.core.reference.module_usage_reuse::build_module_usage_baseline_with_reuse": "A906/1",
+    "contextor.core.analysis.incremental.preparation::prepare_source_update": "A907/1",
+    "contextor.core.analysis.incremental.materialization::ensure_module_usages": "A908/1",
+    "contextor.mcp.tools.get_artifact_blast_radius::get_artifact_blast_radius": "A909/1",
+    "contextor.mcp.tools.get_module_blast_radius::get_module_blast_radius": "A910/1",
+    "contextor.mcp.tools.get_file_edit_context::get_file_edit_context": "A911/1",
+    "contextor.mcp.tools.get_symbol_call_context::get_symbol_call_context": "A912/1",
+}
+_MODULES = {
+    name.split("::", 1)[0]: f"{index}/1"
+    for index, name in enumerate(sorted(_SYMBOLS), start=100)
+}
+
+
+class _LiveRegistry:
+    def __init__(self, artifact_path_to_id):
+        self._state = {
+            "module_registry": {
+                "path_to_id": _MODULES,
+                "id_to_path": {value: key for key, value in _MODULES.items()},
+            },
+            "artifact_registry": {
+                "path_to_id": artifact_path_to_id,
+                "id_to_path": {
+                    value: key for key, value in artifact_path_to_id.items()
+                },
+            },
+        }
+
+    def read_transaction(self):
+        return nullcontext()
+
+
+def _state(*, artifact_state="fresh", syntax_state="fresh", usages=None, resync=False):
+    modules = {
+        "pkg.alpha": SimpleNamespace(path="pkg/alpha.py", module_id="100/1"),
+        "pkg.beta": SimpleNamespace(path="pkg/beta.py", module_id="101/1"),
+    }
+    artifacts = {
+        "pkg.alpha": {
+            "own_symbols": ["alpha"],
+            "symbols": {"functions": ["alpha"]},
+        },
+        "pkg.beta": {
+            "own_symbols": ["beta"],
+            "symbols": {"functions": ["beta"]},
+        },
+    }
+    consumption = {
+        "pkg.alpha::alpha": {
+            "consumers": ["pkg.beta"],
+            "channels": {"pkg.beta": ["direct_calls"]},
+        },
+        "pkg.beta::beta": {"consumers": [], "channels": {}},
+    }
+    default_usages = {
+        module: SimpleNamespace(
+            symbol_calls=("caller", "callee", 3, "direct"),
+            symbol_calls_materialized=True,
+            reference_evidence=("target", "direct_calls", "caller", 3),
+            reference_evidence_materialized=True,
+        )
+        for module in modules
+    }
+    state = RepositoryAnalysisState(
+        modules=modules,
+        artifacts=artifacts,
+        artifact_consumption=consumption,
+        artifact_consumption_state=artifact_state,
+        syntax_diagnostics_by_path={
+            "pkg/alpha.py": {"status": "checked_and_none", "errors": []}
+        },
+        syntax_diagnostics_state=syntax_state,
+        module_usages=usages if usages is not None else default_usages,
+        module_parse_freshness={},
+    )
+    state.provenance = "live"
+    state.revision = 17
+    state.state_id = "state-17"
+    state.resync_required = resync
+    return state
+
+
+def _install(monkeypatch, tmp_path, state, *, active_ids=True):
+    artifact_ids = _SYMBOLS if active_ids else {}
+    registry = _LiveRegistry(artifact_ids)
+    engine = SimpleNamespace(
+        state=state,
+        registry=registry,
+        provenance="live",
+        revision=state.revision,
+    )
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(
+        query_helpers,
+        "read_registries",
+        lambda _root: (
+            _MODULES,
+            {value: key for key, value in _MODULES.items()},
+            artifact_ids,
+            {value: key for key, value in artifact_ids.items()},
+        ),
+    )
+    return engine
+
+
+def _load(raw):
+    return json.loads(raw)
+
+
+def _edge(result, edge_type, source=None, target=None):
+    return [
+        edge
+        for edge in result["edges"]
+        if edge["type"] == edge_type
+        and (source is None or edge["source"] == source)
+        and (target is None or edge["target"] == target)
+    ]
+
+
+def test_artifact_consumption_fresh_contains_both_branches_and_projections(tmp_path, monkeypatch):
+    state = _state()
+    _install(monkeypatch, tmp_path, state)
+
+    result = _load(
+        get_dataflow_lineage(
+            str(tmp_path), "artifact_consumption", direction="both", depth=4
+        )
+    )
+
+    assert result["status"] == "ok"
+    assert result["owner"] == ["state:RepositoryAnalysisState.artifact_consumption"]
+    assert result["freshness"]["families"]["artifact_consumption"] == "fresh"
+    assert {
+        "data_family:raw_artifact_consumer_facts",
+        "data_family:module_usage_facts",
+    } <= {node["id"] for node in result["nodes"]}
+    qualified = {node.get("qualified_name") for node in result["nodes"]}
+    assert "contextor.core.analysis.state_manager::build_canonical_artifact_consumption" in qualified
+    assert "contextor.core.analysis.incremental.plan_executor::_rebuild_consumer_slice" in qualified
+    assert _edge(result, "PERSISTS")
+    assert _edge(result, "HYDRATES")
+    assert {"tool:get_artifact_blast_radius", "tool:get_module_blast_radius"} <= set(
+        result["public_projections"]
+    )
+    assert all(edge["confidence"] == "confirmed" for edge in result["edges"])
+    assert not any(edge["confidence"] == "structural" for edge in result["edges"])
+
+
+def test_artifact_consumption_stale_stops_downstream_and_reports_gap(tmp_path, monkeypatch):
+    state = _state(artifact_state="stale")
+    _install(monkeypatch, tmp_path, state)
+
+    result = _load(get_dataflow_lineage(str(tmp_path), "artifact_consumption"))
+
+    assert result["status"] == "stale"
+    assert result["nodes"]
+    assert not _edge(result, "PERSISTS")
+    assert not _edge(result, "PROJECTS")
+    assert any(
+        gap["status"] == "stale" and gap["expected_edge"] == "CURRENT_CANONICAL_FAMILY_DATA"
+        for gap in result["unresolved"]
+    )
+    assert not any("consumers" in node for node in result["nodes"])
+
+
+def test_artifact_consumption_incomplete_is_partial_without_downstream_edges(tmp_path, monkeypatch):
+    state = _state()
+    state.artifact_consumption.pop("pkg.beta::beta")
+    _install(monkeypatch, tmp_path, state)
+
+    result = _load(get_dataflow_lineage(str(tmp_path), "artifact_consumption"))
+
+    assert result["status"] == "partial"
+    assert not _edge(result, "PERSISTS")
+    assert not _edge(result, "PROJECTS")
+    assert any(gap["status"] == "partial" for gap in result["unresolved"])
+
+
+def test_syntax_diagnostics_fresh_contains_full_incremental_and_file_projection(
+    tmp_path, monkeypatch
+):
+    state = _state()
+    _install(monkeypatch, tmp_path, state)
+
+    result = _load(get_dataflow_lineage(str(tmp_path), "syntax_diagnostics"))
+
+    assert result["status"] == "ok"
+    assert {
+        "data_family:repository_index_parse_results",
+        "data_family:prepared_source_update",
+    } <= {node["id"] for node in result["nodes"]}
+    qualified = {node.get("qualified_name") for node in result["nodes"]}
+    assert "contextor.core.analysis.state_manager::build_syntax_diagnostics_from_index" in qualified
+    assert "contextor.core.analysis.incremental.engine::IncrementalAnalysisEngine._commit_syntax_candidate" in qualified
+    assert result["public_projections"] == ["tool:get_file_edit_context"]
+    assert _edge(result, "PERSISTS") and _edge(result, "HYDRATES")
+
+
+def test_syntax_diagnostics_deferred_keeps_owner_and_reports_unavailable_downstream(
+    tmp_path, monkeypatch
+):
+    state = _state(syntax_state="deferred")
+    _install(monkeypatch, tmp_path, state)
+
+    result = _load(get_dataflow_lineage(str(tmp_path), "syntax_diagnostics"))
+
+    assert result["status"] == "unavailable"
+    assert "state:RepositoryAnalysisState.syntax_diagnostics_by_path" in {
+        node["id"] for node in result["nodes"]
+    }
+    assert not _edge(result, "PROJECTS")
+    assert any(gap["status"] == "unavailable" for gap in result["unresolved"])
+    assert result["freshness"]["families"]["syntax_diagnostics"] == "unavailable"
+
+
+def test_syntax_diagnostics_stale_is_not_empty_success(tmp_path, monkeypatch):
+    state = _state(syntax_state="stale")
+    _install(monkeypatch, tmp_path, state)
+
+    result = _load(get_dataflow_lineage(str(tmp_path), "syntax_diagnostics"))
+
+    assert result["status"] == "stale"
+    assert not _edge(result, "PROJECTS")
+    assert any(gap["status"] == "stale" for gap in result["unresolved"])
+
+
+def test_symbol_calls_complete_reports_coverage_and_three_update_branches(tmp_path, monkeypatch):
+    state = _state()
+    _install(monkeypatch, tmp_path, state)
+
+    result = _load(get_dataflow_lineage(str(tmp_path), "symbol_calls"))
+
+    assert result["status"] == "ok"
+    assert result["coverage"] == {
+        "canonical_module_count": 2,
+        "symbol_calls_materialized_count": 2,
+        "reference_evidence_materialized_count": 2,
+        "missing_symbol_calls_materialization_count": 0,
+        "missing_reference_evidence_count": 0,
+        "stale_module_count": 0,
+    }
+    qualified = {node.get("qualified_name") for node in result["nodes"]}
+    assert "contextor.core.reference.engine::extract_module_usage_facts" in qualified
+    assert "contextor.core.reference.module_usage_reuse::build_module_usage_baseline_with_reuse" in qualified
+    assert "contextor.core.analysis.incremental.preparation::prepare_source_update" in qualified
+    assert "contextor.core.analysis.incremental.materialization::ensure_module_usages" in qualified
+    assert result["public_projections"] == ["tool:get_symbol_call_context"]
+    assert _edge(result, "PERSISTS") and _edge(result, "HYDRATES")
+
+
+def test_symbol_calls_partial_uses_one_aggregate_coverage_gap(tmp_path, monkeypatch):
+    usages = {
+        "pkg.alpha": SimpleNamespace(
+            symbol_calls_materialized=True,
+            reference_evidence_materialized=True,
+        ),
+        "pkg.beta": SimpleNamespace(
+            symbol_calls_materialized=False,
+            reference_evidence_materialized=False,
+        ),
+    }
+    state = _state(usages=usages)
+    _install(monkeypatch, tmp_path, state)
+
+    result = _load(get_dataflow_lineage(str(tmp_path), "symbol_calls"))
+
+    assert result["status"] == "partial"
+    assert result["coverage"]["missing_symbol_calls_materialization_count"] == 1
+    assert result["coverage"]["missing_reference_evidence_count"] == 1
+    coverage_gaps = [
+        gap
+        for gap in result["unresolved"]
+        if gap["expected_edge"] == "COMPLETE_SYMBOL_CALLS_COVERAGE"
+    ]
+    assert len(coverage_gaps) == 1
+    assert len(result["unresolved"]) == 1
+
+
+def test_resync_fails_closed_without_confirmed_downstream_data_edges(tmp_path, monkeypatch):
+    state = _state(resync=True)
+    _install(monkeypatch, tmp_path, state)
+
+    result = _load(get_dataflow_lineage(str(tmp_path), "artifact_consumption"))
+
+    assert result["status"] == "unavailable"
+    assert result["freshness"]["resync_required"] is True
+    assert not _edge(result, "PERSISTS")
+    assert not _edge(result, "PROJECTS")
+    assert all(edge["confidence"] == "confirmed" for edge in result["edges"])
+    assert any(gap["status"] == "unavailable" for gap in result["unresolved"])
+
+
+def test_direction_and_depth_are_relative_to_family_anchor(tmp_path, monkeypatch):
+    state = _state()
+    _install(monkeypatch, tmp_path, state)
+
+    upstream = _load(
+        get_dataflow_lineage(str(tmp_path), "artifact_consumption", "upstream", 1)
+    )
+    downstream = _load(
+        get_dataflow_lineage(str(tmp_path), "artifact_consumption", "downstream", 1)
+    )
+    shallow = _load(
+        get_dataflow_lineage(str(tmp_path), "artifact_consumption", "both", 1)
+    )
+
+    assert upstream["entry_points"] == ["family:artifact_consumption"]
+    assert _edge(upstream, "PRODUCES")
+    assert not _edge(upstream, "MATERIALIZES")
+    assert _edge(downstream, "MATERIALIZES")
+    assert not _edge(downstream, "PRODUCES")
+    assert _edge(shallow, "PRODUCES") and _edge(shallow, "MATERIALIZES")
+    assert all(
+        edge["source"] == "family:artifact_consumption"
+        or edge["target"] == "family:artifact_consumption"
+        for edge in shallow["edges"]
+    )
+
+
+def test_output_is_deterministic_and_identity_resolution_is_dynamic(tmp_path, monkeypatch):
+    state = _state()
+    _install(monkeypatch, tmp_path, state)
+
+    first = get_dataflow_lineage(str(tmp_path), "symbol_calls", depth=4)
+    second = get_dataflow_lineage(str(tmp_path), "symbol_calls", depth=4)
+    assert first == second
+    result = _load(first)
+    assert result["nodes"] == sorted(result["nodes"], key=lambda node: (node["type"], node["id"]))
+    assert result["edges"] == sorted(
+        result["edges"],
+        key=lambda edge: (edge["source"], edge["target"], edge["type"]),
+    )
+    assert any(
+        node.get("artifact_id") == "A905/1"
+        for node in result["nodes"]
+        if node.get("qualified_name") == "contextor.core.reference.engine::extract_module_usage_facts"
+    )
+
+    _install(monkeypatch, tmp_path, state, active_ids=False)
+    without_ids = _load(get_dataflow_lineage(str(tmp_path), "symbol_calls", depth=4))
+    extractor = next(
+        node
+        for node in without_ids["nodes"]
+        if node.get("qualified_name") == "contextor.core.reference.engine::extract_module_usage_facts"
+    )
+    assert "artifact_id" not in extractor
+    assert any(
+        gap.get("kind") == "identity_resolution"
+        and gap.get("qualified_name") == extractor["qualified_name"]
+        for gap in without_ids["unresolved"]
+    )
+
+
+def test_query_time_does_not_parse_or_call_other_mcp_tools(tmp_path, monkeypatch):
+    state = _state()
+    _install(monkeypatch, tmp_path, state)
+    monkeypatch.setattr(
+        query_helpers,
+        "build_state_freshness",
+        lambda *_args, **_kwargs: {
+            "canonical_state": "fresh",
+            "workspace_sync": "unverified",
+            "canonical_revision": 17,
+            "provenance": "live",
+            "families": {},
+            "advisory_warning": None,
+        },
+    )
+    monkeypatch.setattr(ast, "parse", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("AST parse")))
+    monkeypatch.setattr(
+        mcp_server,
+        "get_module_blast_radius",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("MCP call")),
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "get_artifact_blast_radius",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("MCP call")),
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "get_symbol_call_context",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("MCP call")),
+    )
+
+    result = _load(get_dataflow_lineage(str(tmp_path), "artifact_consumption"))
+    assert result["status"] == "ok"
+
+
+def test_signature_docs_registration_and_public_contract_parity():
+    tool = mcp_server.mcp._tool_manager._tools["get_dataflow_lineage"]
+    assert set(inspect.signature(tool.fn).parameters) == {
+        "repo_path",
+        "family",
+        "direction",
+        "depth",
+    }
+    assert str(inspect.signature(tool.fn)) == (
+        "(repo_path: str, family: str, direction: str = 'both', depth: int = 3) -> str"
+    )
+    assert list(mcp_server.REGISTERED_MCP_TOOL_NAMES)[-1] == "get_dataflow_lineage"
+    document = load_tool_document("get_dataflow_lineage")
+    assert document["tool"] == "get_dataflow_lineage"
+    assert any(entry.startswith("family (string, required)") for entry in document["parameters"])
+    source = inspect.getsource(get_dataflow_lineage)
+    assert "ast.parse" not in source
+    assert "get_module_blast_radius(" not in source
+    assert "get_artifact_blast_radius(" not in source
+    assert "get_symbol_call_context(" not in source
+
```

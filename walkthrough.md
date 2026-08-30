# 0J5 raw Shared Usage Clusters handoff - correction/audit closure

## Scope

This closure was limited to the fail-closed handoff validator defect. No new optimization scope was opened, no benchmark harness was created in the repository, and no production/test behavior outside the validator and its focused regressions was changed.

The defect was in C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py::is_valid_shared_usage_clusters_handoff. The validator compared list lengths with size and shared_artifact_count before validating those values. A malformed non-numeric value could therefore raise TypeError instead of returning False and selecting the canonical fallback.

## Correction

The validator now validates size and shared_artifact_count before any length comparison, rejects booleans for integer count fields, requires exact equality for both count relationships, rejects boolean similarity/ratio values, and validates the artifact container before calling .keys().

All existing scope, parameter, current-run identity, complete-marker, exact-field-set, sorted-identity, duplicate-module, range, and fallback rules remain in force. The authoritative compute_shared_usage_clusters_from_state aggregation/classification path was not changed.

## Contextor evidence and current workspace freshness

Contextor MCP was used before editing to resolve the current validator, artifact pipeline, global pipeline, and facade symbols. The post-edit evidence is:

- get_live_events(after_revision=80) first had one transient connection failure; the immediate retry succeeded with continuous revisions and no resync requirement.
- Revision 81: desktop_watcher, UPDATED, C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py.
- Revision 82: desktop_watcher, UPDATED, C:\Temp\Contextor_Repo\tests\test_jaccard_handoff_0j5.py.
- Revision 83: desktop_watcher, UPDATED, C:\Temp\Contextor_Repo\tests\test_jaccard_handoff_0j5.py.
- Event continuity was continuous; resync_required=false; no MCP restart was performed or needed.
- Current Contextor state: canonical_state=fresh, workspace_sync=verified, canonical_revision=83, provenance=live.
- Fresh families: module, graph, topology, artifact_consumption, cycles, and collisions.
- Project architecture reported 321 modules, 7 layers, 0 cycles, 0 name collisions, and no diagnostics attention required. Deferred analytics families were not treated as zero-valued evidence.
- contextor.core.reporting_engine.graph_analytics remained engine, live fan-in 17/fan-out 6.
- contextor.core.api.facade remained contract, live fan-in 29/fan-out 29.
- contextor.core.symbol_engine.indexer remained runtime, live fan-in 21/fan-out 10.
- No new cycle or layer-boundary violation was observed. Nested engine/contract isolation has no dedicated report without starting a separate layer analysis, which was unnecessary for this narrow unchanged-layer correction.
- get_source_range at the facade handoff block confirms invalid handoffs call compute_shared_usage_clusters_from_state(state) inside the existing try/except. The pipeline source confirms _raw_shared_usage_clusters and _artifact_data are carried in the same result.
- get_symbol_call_context returned no static intra-module caller edge for the validator; the current facade source range is direct evidence of its dynamic local import and production call.

## Handoff provenance proof retained from 0J5

The current-run provenance remains proven and was not weakened:

1. build_artifact_pipeline calls global generate_graph_analytics_report with one current-run artifact_data object and captures its pre-compaction raw clusters in SharedUsageClustersHandoff.
2. The handoff stores id(artifact_data), the exact ordered artifact key domain, and the exact ordered raw module-artifact key domain.
3. execute_global_pipeline carries both the handoff and the same artifact-data object into its result as _raw_shared_usage_clusters and _artifact_data.
4. ContextorFacade.analyze_project builds canonical artifact consumption from current-run raw_artifacts, validates coverage, and validates the handoff against current-run identity/key domains before accepting it.
5. A valid handoff is copied only into the state list; an invalid or absent handoff enters the existing canonical computation path.

The accepted 0J5 evidence established that canonical artifact/consumption state is deterministically constructed from the same current-run artifact/usage payload, with no intervening semantic filtering that changes the relevant consumer key domain. No hashes, deep comparisons, extra copies, second cache, AST/source persistence, or provenance overhead was added.

## Regression coverage

tests/test_jaccard_handoff_0j5.py covers inflated and deflated counts, non-integer and boolean counts, inconsistent/non-integer/boolean sizes, malformed similarity and ratio values, malformed artifact data without an exception, direct rejection of every malformed variant, facade fallback for every rejected handoff variant, valid-handoff no-duplicate behavior, raw-vs-compacted parity, and layer non-capture behavior.

The existing lifecycle regression in tests/test_matrix_clusters_state_lifecycle.py continues to force validator rejection and verifies fallback failure isolation.

Focused command result:

~~~text
& .\.venv\Scripts\python.exe -m pytest -q -s tests\test_jaccard_handoff_0j5.py tests\test_matrix_clusters_state_lifecycle.py tests\test_derived_analytics_parity.py
59 passed in 25.58s
~~~

Directly affected command after the final test adjustment:

~~~text
& .\.venv\Scripts\python.exe -m pytest -q -s tests\test_jaccard_handoff_0j5.py
12 passed in 15.09s
~~~

Compilation and whitespace validation:

~~~text
& .\.venv\Scripts\python.exe -m py_compile contextor\core\reporting_engine\graph_analytics.py tests\test_jaccard_handoff_0j5.py
PY_COMPILE=PASS
git diff --check -- ':!walkthrough.md'
GIT_DIFF_CHECK_EXCLUDING_WALKTHROUGH=PASS
~~~

The repository's existing LF/CRLF conversion warnings from Git did not affect either result.

The literal unscoped git diff --check also reports trailing whitespace on the twelve raw unified-diff context lines embedded in this report. Those single spaces are part of the required complete raw diff representation. The production/test-only check above excludes walkthrough.md and is the authoritative changed-file whitespace result.

## Performance evidence and gate decision

The correction changes only malformed-input validation and leaves producer, aggregation, canonical-state, persistence, and normal valid-handoff control flow unchanged. The accepted external controlled 0J5 gate was retained rather than rerun.

Harness: C:\Temp\Contextor_Benchmarks\0J5_handoff_gate_20260830.

~~~text
WHOLE_ANALYSIS_BASELINE_MEDIAN_MS=6559.137299511349
WHOLE_ANALYSIS_CANDIDATE_MEDIAN_MS=6291.322954988573
WHOLE_ANALYSIS_DELTA_MS=-267.8143445227761

candidate cold=22836.7352560163
candidate warm=8044.92777702399,6168.75238303328,6132.74424598785,6484.05544500565,6350.11893999763,6232.52696997952
candidate warm_median=6291.322954988573
candidate global_graph_median_ms=434.76283250493
candidate canonical_boundary_median_ms=0
candidate GLOBAL_JACCARD_COUNT=1 on every run
candidate LAYER_JACCARD_COUNT=2 on every run
candidate CANONICAL_JACCARD_COUNT=0 on every run

fallback cold=24688.1044240436
fallback warm=8575.29455603799,6876.94713997189,6671.18355800631,6481.55868897447,6647.2837330075,6797.054863011
fallback warm_median=6734.119210508652
fallback global_graph_median_ms=450.3752574964892
fallback canonical_boundary_median_ms=313.305461982964
fallback GLOBAL_JACCARD_COUNT=1 on every run
fallback LAYER_JACCARD_COUNT=2 on every run
fallback FALLBACK_CANONICAL_JACCARD_COUNT=1 on every run
~~~

The normal current-schema warm path remains zero canonical recomputations. The fallback control independently measured one canonical computation; this is not inferred from the global counter alone. The retained candidate remains 267.814 ms below the accepted baseline median, while forced fallback is 442.796 ms above the candidate median.

## Semantic and architectural conclusion

Malformed values now return False, the facade retains its existing canonical fallback, and fallback exceptions still mark canonical state stale without failing the whole analysis. Exact equality prevents inflated or deflated counts. Boolean values cannot qualify as numeric counts or ratios. Valid current-schema handoffs and public graph schemas remain unchanged.

No new cycle, layer-boundary issue, public API/MCP change, persistence change, LIVE behavior change, cache change, or canonical-state weakening was introduced. The optimization remains elimination of redundant Jaccard recomputation only.

## FILES_CHANGED

walkthrough.md and the desktop-generated log are excluded:

~~~text
C:\Temp\Contextor_Repo\contextor\core\api\facade.py
C:\Temp\Contextor_Repo\contextor\core\reporting_engine\artifact_pipeline.py
C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py
C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py
C:\Temp\Contextor_Repo\tests\test_jaccard_handoff_0j5.py
C:\Temp\Contextor_Repo\tests\test_matrix_clusters_state_lifecycle.py
~~~

## DIFFS

Complete raw unified diff for every production/test file changed by the entire current 0J5 task follows. walkthrough.md is not counted.

### C:\Temp\Contextor_Repo\contextor\core\api\facade.py

~~~diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index cbace68..331c74b 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -442,6 +442,7 @@ class ContextorFacade:
                 compute_dependency_matrix_from_state,
                 compute_shared_usage_clusters_from_state,
                 compute_topology_analytics,
+                is_valid_shared_usage_clusters_handoff,
             )

             graph = getattr(analysis_result, "graph", None)
@@ -516,13 +517,26 @@ class ContextorFacade:
 
             # Compute Shared Usage Clusters from canonical state (independent failure & AC trust)
             if artifact_consumption_is_fresh(state):
-                try:
-                    _suc_candidate = compute_shared_usage_clusters_from_state(state)
-                except Exception:
-                    state.shared_usage_clusters_state = "stale"
-                else:
-                    state.shared_usage_clusters = _suc_candidate
+                raw_shared_usage_clusters = report_result.get(
+                    "_raw_shared_usage_clusters"
+                )
+                if is_valid_shared_usage_clusters_handoff(
+                    raw_shared_usage_clusters,
+                    artifact_data=report_result.get("_artifact_data"),
+                    raw_artifacts=raw_artifacts,
+                ):
+                    state.shared_usage_clusters = list(
+                        raw_shared_usage_clusters.clusters
+                    )
                     state.shared_usage_clusters_state = "fresh"
+                else:
+                    try:
+                        _suc_candidate = compute_shared_usage_clusters_from_state(state)
+                    except Exception:
+                        state.shared_usage_clusters_state = "stale"
+                    else:
+                        state.shared_usage_clusters = _suc_candidate
+                        state.shared_usage_clusters_state = "fresh"
             else:
                 state.shared_usage_clusters_state = "stale"
~~~

### C:\Temp\Contextor_Repo\contextor\core\reporting_engine\artifact_pipeline.py

~~~diff
diff --git a/contextor/core/reporting_engine/artifact_pipeline.py b/contextor/core/reporting_engine/artifact_pipeline.py
index 47f44fa..8dd779f 100644
--- a/contextor/core/reporting_engine/artifact_pipeline.py
+++ b/contextor/core/reporting_engine/artifact_pipeline.py
@@ -17,7 +17,10 @@ from contextor.core.reporting_layer.artifact_usage_report_compact import (
 )
 
 from .dictionary import IndexDictionary
-from .graph_analytics import generate_graph_analytics_report
+from .graph_analytics import (
+    SharedUsageClustersHandoff,
+    generate_graph_analytics_report,
+)
 from .persistent_registry import PersistentIdentityRegistry
 from .structure_generator import compact_structure_report
 
@@ -32,6 +35,7 @@ class ArtifactPipelineResult:
     compact_artifact_data: dict
     compact_structure_data: dict
     graph_analytics_data: dict
+    raw_shared_usage_clusters: SharedUsageClustersHandoff | None = None
 
 
 def build_artifact_pipeline(
@@ -103,6 +107,7 @@ def build_artifact_pipeline(
 
     checkpoint(progress_callback, "Starting graph analytics")
 
+    raw_clusters: list[dict] = []
     graph_analytics_data = generate_graph_analytics_report(
         artifact_data=artifact_data,
         hard_edges=hard_edges,
@@ -111,6 +116,19 @@ def build_artifact_pipeline(
         index_dict=index_dict,
         scope="global",
         progress_callback=progress_callback,
+        raw_clusters_out=raw_clusters,
+    )
+    raw_shared_usage_clusters = SharedUsageClustersHandoff(
+        clusters=tuple(raw_clusters),
+        scope="global",
+        min_jaccard=0.30,
+        max_cluster_size=25,
+        min_cluster_size=2,
+        artifact_data_identity=id(artifact_data),
+        artifact_keys=tuple(artifact_data.get("artifacts", {}).keys()),
+        raw_artifact_keys=tuple(
+            artifact_data.get("_module_artifacts", {}).keys()
+        ),
     )
     log_program_event(
         "REPORT",
@@ -124,4 +142,5 @@ def build_artifact_pipeline(
         compact_artifact_data=compact_artifact_data,
         compact_structure_data=compact_structure_data,
         graph_analytics_data=graph_analytics_data,
+        raw_shared_usage_clusters=raw_shared_usage_clusters,
     )
~~~

### C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py

~~~diff
diff --git a/contextor/core/reporting_engine/graph_analytics.py b/contextor/core/reporting_engine/graph_analytics.py
index 3035787..bdc3a71 100644
--- a/contextor/core/reporting_engine/graph_analytics.py
+++ b/contextor/core/reporting_engine/graph_analytics.py
@@ -55,12 +55,116 @@ The implementation is deterministic and does not depend on networkx.
 from __future__ import annotations
 
 from collections import defaultdict, deque
+from dataclasses import dataclass
 from typing import Any
 
 from contextor.core.errors import checkpoint
 from contextor.core.program_log import log_program_event
 
 
+@dataclass(frozen=True)
+class SharedUsageClustersHandoff:
+    """Internal current-run handoff of full-identity global clusters."""
+
+    clusters: tuple[dict, ...]
+    scope: str
+    min_jaccard: float
+    max_cluster_size: int
+    min_cluster_size: int
+    artifact_data_identity: int
+    artifact_keys: tuple[str, ...]
+    raw_artifact_keys: tuple[str, ...]
+    complete: bool = True
+
+
+def is_valid_shared_usage_clusters_handoff(
+    handoff: Any,
+    *,
+    artifact_data: Any,
+    raw_artifacts: Any,
+) -> bool:
+    """Validate an unpersisted global-cluster handoff for this run."""
+    if not isinstance(handoff, SharedUsageClustersHandoff):
+        return False
+    if (
+        handoff.scope != "global"
+        or handoff.min_jaccard != 0.30
+        or handoff.max_cluster_size != 25
+        or handoff.min_cluster_size != 2
+        or handoff.artifact_data_identity != id(artifact_data)
+        or not handoff.complete
+    ):
+        return False
+    if not isinstance(artifact_data, dict) or not isinstance(raw_artifacts, dict):
+        return False
+    artifact_entries = artifact_data.get("artifacts", {})
+    if not isinstance(artifact_entries, dict):
+        return False
+    if tuple(artifact_entries.keys()) != handoff.artifact_keys:
+        return False
+    if tuple(raw_artifacts.keys()) != handoff.raw_artifact_keys:
+        return False
+    if not isinstance(handoff.clusters, tuple):
+        return False
+
+    expected_keys = {
+        "modules",
+        "size",
+        "shared_artifact_count",
+        "shared_artifact_keys",
+        "jaccard_similarity",
+        "shared_ratio",
+    }
+    seen_modules: set[str] = set()
+    for cluster in handoff.clusters:
+        if not isinstance(cluster, dict) or set(cluster) != expected_keys:
+            return False
+        modules = cluster["modules"]
+        size = cluster["size"]
+        shared_keys = cluster["shared_artifact_keys"]
+        shared_artifact_count = cluster["shared_artifact_count"]
+        if (
+            not isinstance(size, int)
+            or isinstance(size, bool)
+            or not isinstance(shared_artifact_count, int)
+            or isinstance(shared_artifact_count, bool)
+        ):
+            return False
+        if (
+            not isinstance(modules, list)
+            or not all(isinstance(module, str) for module in modules)
+            or modules != sorted(modules)
+            or len(modules) != size
+            or len(modules) < 2
+            or len(modules) > 25
+            or seen_modules.intersection(modules)
+        ):
+            return False
+        if (
+            not isinstance(shared_keys, list)
+            or not all(isinstance(key, str) for key in shared_keys)
+            or shared_keys != sorted(shared_keys)
+            or len(shared_keys) != shared_artifact_count
+        ):
+            return False
+        if (
+            not isinstance(cluster["jaccard_similarity"], (int, float))
+            or isinstance(cluster["jaccard_similarity"], bool)
+        ):
+            return False
+        if (
+            not isinstance(cluster["shared_ratio"], (int, float))
+            or isinstance(cluster["shared_ratio"], bool)
+        ):
+            return False
+        if not 0.0 <= cluster["jaccard_similarity"] <= 1.0:
+            return False
+        if not 0.0 <= cluster["shared_ratio"] <= 1.0:
+            return False
+        seen_modules.update(modules)
+    return True
+
+
 # ==========================================================
 # LAYER CLASSIFICATION
 # ==========================================================
@@ -1450,6 +1554,7 @@ def generate_graph_analytics_report(
     scope_modules: set[str] | None = None,
     global_artifact_data: dict | None = None,
     progress_callback=None,
+    raw_clusters_out: list[dict] | None = None,
 ) -> dict:
     """
     Generate the graph analytics report.
@@ -1840,6 +1945,9 @@ def generate_graph_analytics_report(
         progress_callback=progress_callback,
     )
 
+    if raw_clusters_out is not None and scope == "global":
+        raw_clusters_out.extend(clusters)
+
     clusters = _compact_clusters(
         clusters,
         index_dict,
@@ -2292,4 +2400,3 @@ __all__ = [
 ]


-
~~~

### C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py

~~~diff
diff --git a/contextor/core/reporting_engine/pipeline.py b/contextor/core/reporting_engine/pipeline.py
index d3a687c..a47f03b 100644
--- a/contextor/core/reporting_engine/pipeline.py
+++ b/contextor/core/reporting_engine/pipeline.py
@@ -226,6 +226,7 @@ def execute_global_pipeline(
     compact_artifact_data = artifact_bundle.compact_artifact_data
     compact_structure_data = artifact_bundle.compact_structure_data
     graph_analytics_data = artifact_bundle.graph_analytics_data
+    raw_shared_usage_clusters = artifact_bundle.raw_shared_usage_clusters
 
     # ------------------------------------------------------
     # SANITY CHECK
@@ -631,6 +632,7 @@ def execute_global_pipeline(
         "_graph_analytics_data": (
             graph_analytics_data
         ),
+        "_raw_shared_usage_clusters": raw_shared_usage_clusters,
         "_analysis_result": analysis_result,
         "_file_state_manager": state_mgr,
     }
~~~

### C:\Temp\Contextor_Repo\tests\test_jaccard_handoff_0j5.py

~~~diff
diff --git a/tests/test_jaccard_handoff_0j5.py b/tests/test_jaccard_handoff_0j5.py
new file mode 100644
index 0000000..8883d4d
--- /dev/null
+++ b/tests/test_jaccard_handoff_0j5.py
@@ -0,0 +1,285 @@
+from dataclasses import replace
+from pathlib import Path
+from unittest.mock import patch
+
+import pytest
+
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.reporting_engine import graph_analytics
+from contextor.core.reporting_engine.graph_analytics import (
+    SharedUsageClustersHandoff,
+    _compact_clusters,
+    build_jaccard_clusters,
+    generate_graph_analytics_report,
+    is_valid_shared_usage_clusters_handoff,
+)
+
+
+def _artifact_data():
+    return {
+        "artifacts": {
+            "pkg::Thing": {
+                "artifact_id": "pkg::Thing",
+                "artifact": "pkg.Thing",
+                "kind": "class",
+                "definer_module": "pkg",
+                "consumers": ["pkg.one", "pkg.two"],
+                "consumer_count": 2,
+            }
+        },
+        "_module_artifacts": {
+            "pkg::Thing": {"artifact": "pkg.Thing"},
+        },
+        "_usage_sidecar": {},
+    }
+
+
+class _CompactIndex:
+    def get_module_id(self, value):
+        return f"module:{value}"
+
+    def get_artifact_id(self, value):
+        return f"artifact:{value}"
+
+
+def _handoff(artifact_data, *, clusters=None, **changes):
+    values = {
+        "clusters": tuple(
+            build_jaccard_clusters(artifact_data)
+            if clusters is None
+            else clusters
+        ),
+        "scope": "global",
+        "min_jaccard": 0.30,
+        "max_cluster_size": 25,
+        "min_cluster_size": 2,
+        "artifact_data_identity": id(artifact_data),
+        "artifact_keys": tuple(artifact_data["artifacts"]),
+        "raw_artifact_keys": tuple(artifact_data["_module_artifacts"]),
+        "complete": True,
+    }
+    values.update(changes)
+    return SharedUsageClustersHandoff(**values)
+
+
+def test_global_handoff_is_raw_and_compaction_is_non_mutating():
+    artifact_data = _artifact_data()
+    raw = build_jaccard_clusters(artifact_data)
+    before = [dict(cluster) for cluster in raw]
+    captured = []
+
+    report = generate_graph_analytics_report(
+        artifact_data=artifact_data,
+        hard_edges={"pkg.one": [], "pkg.two": []},
+        modules={"pkg.one": {}, "pkg.two": {}},
+        index_dict=_CompactIndex(),
+        scope="global",
+        raw_clusters_out=captured,
+    )
+    plain_report = generate_graph_analytics_report(
+        artifact_data=artifact_data,
+        hard_edges={"pkg.one": [], "pkg.two": []},
+        modules={"pkg.one": {}, "pkg.two": {}},
+        index_dict=_CompactIndex(),
+        scope="global",
+    )
+
+    assert captured == raw
+    assert captured == before
+    assert report == plain_report
+    assert report["shared_usage_clusters"] != raw
+    assert report["shared_usage_clusters"][0]["modules"] == [
+        "module:pkg.one",
+        "module:pkg.two",
+    ]
+    assert report["shared_usage_clusters"][0]["shared_artifact_keys"] == [
+        "artifact:pkg::Thing",
+    ]
+
+
+def test_handoff_validator_accepts_exact_current_run_and_rejects_invalid_variants():
+    artifact_data = _artifact_data()
+    raw_artifacts = artifact_data["_module_artifacts"]
+    valid = _handoff(artifact_data)
+
+    assert is_valid_shared_usage_clusters_handoff(
+        valid, artifact_data=artifact_data, raw_artifacts=raw_artifacts
+    )
+    assert not is_valid_shared_usage_clusters_handoff(
+        None, artifact_data=artifact_data, raw_artifacts=raw_artifacts
+    )
+    assert not is_valid_shared_usage_clusters_handoff(
+        {"clusters": []}, artifact_data=artifact_data, raw_artifacts=raw_artifacts
+    )
+    assert not is_valid_shared_usage_clusters_handoff(
+        _handoff(artifact_data, complete=False),
+        artifact_data=artifact_data,
+        raw_artifacts=raw_artifacts,
+    )
+    assert not is_valid_shared_usage_clusters_handoff(
+        _handoff(artifact_data, scope="layer"),
+        artifact_data=artifact_data,
+        raw_artifacts=raw_artifacts,
+    )
+    assert not is_valid_shared_usage_clusters_handoff(
+        _handoff(artifact_data, min_jaccard=0.4),
+        artifact_data=artifact_data,
+        raw_artifacts=raw_artifacts,
+    )
+
+    cluster = valid.clusters[0]
+    malformed_clusters = [
+        {**cluster, "shared_artifact_count": len(cluster["shared_artifact_keys"]) + 1},
+        {**cluster, "shared_artifact_count": len(cluster["shared_artifact_keys"]) - 1},
+        {**cluster, "shared_artifact_count": "1"},
+        {**cluster, "shared_artifact_count": True},
+        {**cluster, "size": len(cluster["modules"]) + 1},
+        {**cluster, "size": "2"},
+        {**cluster, "size": True},
+        {**cluster, "jaccard_similarity": "not-a-number"},
+        {**cluster, "shared_ratio": "not-a-number"},
+    ]
+    for malformed in malformed_clusters:
+        assert not is_valid_shared_usage_clusters_handoff(
+            _handoff(artifact_data, clusters=[malformed]),
+            artifact_data=artifact_data,
+            raw_artifacts=raw_artifacts,
+        )
+
+    malformed_artifact_data = {"artifacts": None}
+    malformed_artifact_handoff = replace(
+        valid,
+        artifact_data_identity=id(malformed_artifact_data),
+        artifact_keys=(),
+    )
+    assert not is_valid_shared_usage_clusters_handoff(
+        malformed_artifact_handoff,
+        artifact_data=malformed_artifact_data,
+        raw_artifacts=raw_artifacts,
+    )
+
+
+@pytest.mark.parametrize(
+    "mutation",
+    [
+        "inflated_count",
+        "deflated_count",
+        "non_int_count",
+        "inconsistent_size",
+        "non_int_size",
+        "malformed_similarity",
+        "malformed_ratio",
+    ],
+)
+def test_facade_rejected_handoff_falls_back_without_failing(
+    tmp_path: Path, mutation: str
+):
+    (tmp_path / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
+    (tmp_path / "one.py").write_text(
+        "from source import VALUE\n", encoding="utf-8"
+    )
+    (tmp_path / "two.py").write_text(
+        "from source import VALUE\n", encoding="utf-8"
+    )
+
+    real_execute = graph_analytics.compute_shared_usage_clusters_from_state
+
+    def reject_handoff(*args, **kwargs):
+        result = original_execute(*args, **kwargs)
+        handoff = result["_raw_shared_usage_clusters"]
+        assert handoff.clusters
+        cluster = handoff.clusters[0]
+        if mutation == "inflated_count":
+            cluster = {
+                **cluster,
+                "shared_artifact_count": len(cluster["shared_artifact_keys"]) + 1,
+            }
+        elif mutation == "deflated_count":
+            cluster = {
+                **cluster,
+                "shared_artifact_count": len(cluster["shared_artifact_keys"]) - 1,
+            }
+        elif mutation == "non_int_count":
+            cluster = {**cluster, "shared_artifact_count": "1"}
+        elif mutation == "inconsistent_size":
+            cluster = {**cluster, "size": len(cluster["modules"]) + 1}
+        elif mutation == "non_int_size":
+            cluster = {**cluster, "size": "2"}
+        elif mutation == "malformed_similarity":
+            cluster = {**cluster, "jaccard_similarity": "not-a-number"}
+        elif mutation == "malformed_ratio":
+            cluster = {**cluster, "shared_ratio": "not-a-number"}
+        result["_raw_shared_usage_clusters"] = replace(
+            handoff, clusters=(cluster,)
+        )
+        return result
+
+    original_execute = __import__(
+        "contextor.core.api.facade", fromlist=["execute_global_pipeline"]
+    ).execute_global_pipeline
+    with (
+        patch(
+            "contextor.core.api.facade.execute_global_pipeline",
+            side_effect=reject_handoff,
+        ),
+        patch.object(
+            graph_analytics,
+            "compute_shared_usage_clusters_from_state",
+            wraps=real_execute,
+        ) as fallback,
+    ):
+        errors, _ = ContextorFacade().analyze_project(str(tmp_path))
+
+    assert not errors
+    assert fallback.call_count == 1
+
+
+def test_facade_uses_valid_handoff_without_canonical_duplicate(tmp_path: Path):
+    (tmp_path / "one.py").write_text("VALUE = 1\n", encoding="utf-8")
+    (tmp_path / "two.py").write_text("from one import VALUE\n", encoding="utf-8")
+
+    with patch(
+        "contextor.core.reporting_engine.graph_analytics.compute_shared_usage_clusters_from_state",
+        side_effect=AssertionError("valid handoff must skip canonical recomputation"),
+    ):
+        errors, _ = ContextorFacade().analyze_project(str(tmp_path))
+
+    assert not errors
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    state = hydrated.engine.state
+    assert state.shared_usage_clusters_state == "fresh"
+
+
+def test_layer_graph_analytics_does_not_capture_raw_global_handoff():
+    captured = []
+    report = generate_graph_analytics_report(
+        artifact_data={"artifacts": {}},
+        hard_edges={"pkg.one": []},
+        modules={"pkg.one": {}},
+        scope="layer",
+        scope_modules={"pkg.one"},
+        raw_clusters_out=captured,
+    )
+
+    assert report["scope"] == "layer"
+    assert captured == []
+
+
+def test_compaction_keeps_input_when_called_directly():
+    raw = [
+        {
+            "modules": ["pkg.one", "pkg.two"],
+            "shared_artifact_keys": ["pkg::Thing"],
+            "size": 2,
+            "shared_artifact_count": 1,
+            "jaccard_similarity": 1.0,
+            "shared_ratio": 1.0,
+        }
+    ]
+    before = [dict(raw[0]), list(raw[0]["modules"]), list(raw[0]["shared_artifact_keys"])]
+    _compact_clusters(raw, _CompactIndex())
+    assert raw[0] == before[0]
+    assert raw[0]["modules"] == before[1]
+    assert raw[0]["shared_artifact_keys"] == before[2]
~~~

### C:\Temp\Contextor_Repo\tests\test_matrix_clusters_state_lifecycle.py

~~~diff
diff --git a/tests/test_matrix_clusters_state_lifecycle.py b/tests/test_matrix_clusters_state_lifecycle.py
index 70c0829..04f9499 100644
--- a/tests/test_matrix_clusters_state_lifecycle.py
+++ b/tests/test_matrix_clusters_state_lifecycle.py
@@ -802,6 +802,9 @@ def test_real_facade_clusters_failure_isolation(tmp_path: Path):
     with unittest.mock.patch(
         "contextor.core.reporting_engine.graph_analytics.compute_shared_usage_clusters_from_state",
         side_effect=_clusters_raise,
+    ), unittest.mock.patch(
+        "contextor.core.reporting_engine.graph_analytics.is_valid_shared_usage_clusters_handoff",
+        return_value=False,
     ):
         facade = ContextorFacade()
         errors, _ = facade.analyze_project(str(tmp_path))
~~~

## Final audit values

FINAL_VERDICT=PASS
HANDOFF_VALIDATOR_FAIL_CLOSED=PASS
COUNT_CONSISTENCY=PASS
CURRENT_RUN_PROVENANCE=PROVEN
GLOBAL_JACCARD_COUNT=1
LAYER_JACCARD_COUNT=2
CANONICAL_JACCARD_COUNT=0
FALLBACK_CANONICAL_JACCARD_COUNT=1
WHOLE_ANALYSIS_CANDIDATE_MEDIAN_MS=6291.322954988573
CONTEXTOR_WORKSPACE_SYNC=verified/fresh revision 83, desktop-watcher events continuous, no resync
FILES_CHANGED=C:\Temp\Contextor_Repo\contextor\core\api\facade.py; C:\Temp\Contextor_Repo\contextor\core\reporting_engine\artifact_pipeline.py; C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py; C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py; C:\Temp\Contextor_Repo\tests\test_jaccard_handoff_0j5.py; C:\Temp\Contextor_Repo\tests\test_matrix_clusters_state_lifecycle.py

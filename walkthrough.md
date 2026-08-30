# 0J5 raw Shared Usage Clusters handoff - final validator hardening closure

## Scope and verdict basis

This closure was limited to final fail-closed validator hardening. No performance benchmark was rerun, no provenance/clustering/pipeline ownership design was reopened, and no public report, persistence, LIVE, API, MCP, or fallback architecture was changed.

The two requested defects were concrete:

1. is_valid_shared_usage_clusters_handoff accepted duplicate module IDs inside one cluster because it only checked cross-cluster reuse through seen_modules.intersection(modules).
2. It accepted any truthy complete value, including 1 and nonempty strings, instead of the exact boolean True required by the producer contract.

The validator also had one equivalent concrete shape defect: duplicate shared_artifact_keys could pass when shared_artifact_count was adjusted to the duplicated list length. Contextor evidence for build_jaccard_clusters shows producer-side consumer and shared-artifact identities are deduplicated through sets, so this was corrected with a bounded per-cluster uniqueness check.

## Production correction

Owner: C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py::is_valid_shared_usage_clusters_handoff

The validator now:

- requires handoff.complete is True;
- rejects duplicate module IDs within a cluster with len(set(modules)) != len(modules);
- retains the existing cross-cluster duplicate rejection through seen_modules.intersection(modules);
- rejects duplicate shared artifact IDs within a cluster with len(set(shared_keys)) != len(shared_keys);
- retains all earlier exact count, type, bool, ordering, field-set, range, scope, parameter, identity, artifact-key-domain, raw-key-domain, complete-marker, and malformed-container checks.

These checks are bounded by the already materialized handoff lists. No AST/source traversal, producer change, canonical recomputation, or derived current-run module-domain structure was added.

## Review of other possible fail-open shapes

Contextor MCP resolved the current producer and validator at canonical revision 83 before the correction and at revision 86 after it.

build_jaccard_clusters constructs module identities from _artifact_consumers. Contextor returned the exact implementation: _artifact_consumers filters non-empty strings and returns sorted(set(...)). Shared artifact IDs are built from a set comprehension and sorted. Therefore duplicate modules or shared keys are contrary to the producer contract and are concrete validator defects; both are now rejected.

The producer's module-domain membership is not recomputed by the validator. The handoff is an unpersisted current-run object and already binds artifact_data by object identity plus the exact ordered artifact and raw-artifact key domains. Rebuilding the full consumer-module domain would rewalk the complete artifact payload on every normal warm analysis and would violate this closure's no-expensive-derived-structure and no-performance-change constraints. No additional speculative or semantically redundant domain check was added. The bounded duplicate checks are the concrete shape checks required here.

No other equivalent concrete exception or permissive-shape path was found in the current validator after the review. Type checks precede all len, set, sort, intersection, and numeric range operations. The exact field set prevents omitted or extra fields; current-run identity and ordered key-domain checks prevent stale or unrelated handoffs.

## Focused regressions

tests/test_jaccard_handoff_0j5.py now proves:

- duplicate module IDs inside one cluster are rejected;
- a module repeated in a second cluster remains rejected;
- complete=1, complete="true", and complete=None are rejected;
- complete=True remains accepted;
- duplicate shared artifact keys are rejected;
- all newly rejected handoffs select the existing canonical fallback and complete analysis without errors.

The existing 0J5 valid-handoff path and the lifecycle failure-isolation regression remain covered. The facade-level fallback test parameterizes all newly rejected forms and asserts the canonical computation is called once.

## Commands and results

Focused validator/handoff tests:

~~~text
& .\.venv\Scripts\python.exe -m pytest -q -s tests\test_jaccard_handoff_0j5.py
18 passed in 24.02s
~~~

Directly relevant canonical lifecycle test:

~~~text
& .\.venv\Scripts\python.exe -m pytest -q -s tests\test_matrix_clusters_state_lifecycle.py::test_real_facade_clusters_failure_isolation
1 passed in 2.10s
~~~

Changed-file compilation and whitespace validation:

~~~text
& .\.venv\Scripts\python.exe -m py_compile contextor\core\reporting_engine\graph_analytics.py tests\test_jaccard_handoff_0j5.py
PY_COMPILE=PASS
git diff --check -- ':!walkthrough.md'
GIT_DIFF_CHECK_EXCLUDING_WALKTHROUGH=PASS
~~~

The unscoped git diff --check necessarily reports trailing whitespace on embedded raw unified-diff context lines in walkthrough.md; those spaces are part of the required complete raw diff. The changed production/test-only check above passes. Git's LF/CRLF conversion warnings are non-failing.

## Retained performance evidence

The requested controlled performance benchmark was not rerun. The valid normal handoff producer, global/layer call structure, canonical gate, and aggregation path are unchanged; this correction adds only bounded constant-time validation checks over already materialized cluster lists.

Retained accepted external gate:

~~~text
HARNESS=C:\Temp\Contextor_Benchmarks\0J5_handoff_gate_20260830
WHOLE_ANALYSIS_BASELINE_MEDIAN_MS=6559.137299511349
WHOLE_ANALYSIS_CANDIDATE_MEDIAN_MS=6291.322954988573
WHOLE_ANALYSIS_DELTA_MS=-267.8143445227761
GLOBAL_JACCARD_COUNT=1
LAYER_JACCARD_COUNT=2
CANONICAL_JACCARD_COUNT=0
FALLBACK_CANONICAL_JACCARD_COUNT=1
~~~

Retained raw candidate timings, one cold and six warm observations:

~~~text
cold=22836.7352560163
warm=8044.92777702399,6168.75238303328,6132.74424598785,6484.05544500565,6350.11893999763,6232.52696997952
warm_median=6291.322954988573
~~~

Retained raw forced-fallback timings:

~~~text
cold=24688.1044240436
warm=8575.29455603799,6876.94713997189,6671.18355800631,6481.55868897447,6647.2837330075,6797.054863011
warm_median=6734.119210508652
~~~

The accepted candidate remains 267.814 ms below baseline. The fallback control remains independently measured at one canonical computation and 442.796 ms above the candidate median. No claim of fallback=0 is inferred from the worker/global counter.

## Contextor post-change freshness and architecture

Post-edit Contextor LIVE evidence:

- revision 84: desktop_watcher UPDATED graph_analytics.py;
- revision 85: desktop_watcher UPDATED test_jaccard_handoff_0j5.py;
- revision 86: desktop_watcher UPDATED test_jaccard_handoff_0j5.py;
- continuity=continuous;
- resync_required=false;
- activity epoch remained continuous;
- no MCP restart was performed or required.

Post-change Contextor architecture at revision 86:

- canonical_state=fresh;
- workspace_sync=verified;
- provenance=live;
- fresh module, graph, topology, artifact_consumption, cycles, and collisions families;
- project module_count=321 and layer_count=7;
- cycles=0 and name_collisions=0;
- diagnostics attention_required=false;
- graph_analytics remained layer engine, fan_in=17, fan_out=6;
- api.facade remained layer contract, fan_in=29, fan_out=29;
- symbol_engine.indexer remained layer runtime, fan_in=21, fan_out=10.

The correction stays inside graph_analytics and adds no cross-module dependency. No new cycle or layer violation was reported. Nested layer isolation has no dedicated report without starting a separate analysis; global fresh architecture and the unchanged dependency topology were sufficient for this narrow closure.

## Current-run provenance

CURRENT_RUN_PROVENANCE remains PROVEN from accepted 0J5 evidence. build_artifact_pipeline captures raw global clusters from the exact current-run artifact_data object; execute_global_pipeline carries that handoff and the same artifact_data; ContextorFacade validates object identity and ordered artifact/raw-artifact key domains before accepting it. Canonical artifact consumption is derived from the same current-run raw artifact payload. The canonical compute function remains the fallback authority.

## FILES_CHANGED

The complete current 0J5 task file set is:

~~~text
C:\Temp\Contextor_Repo\contextor\core\api\facade.py
C:\Temp\Contextor_Repo\contextor\core\reporting_engine\artifact_pipeline.py
C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py
C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py
C:\Temp\Contextor_Repo\tests\test_jaccard_handoff_0j5.py
C:\Temp\Contextor_Repo\tests\test_matrix_clusters_state_lifecycle.py
~~~

The desktop-generated log and walkthrough.md are excluded from task FILES_CHANGED.

## DIFFS

Complete raw unified diff for every production/test file changed by the entire 0J5 task is below. The diff base is the accepted pre-0J5 commit 9cb56e6; it includes the accepted handoff implementation plus this final validator correction. The log and walkthrough.md are excluded.

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
diff --git a/contextor/core/reporting_engine/graph_analytics.py b/contextor/core/reporting_engine/graph_analytics.py
index 3035787..4906fe5 100644
--- a/contextor/core/reporting_engine/graph_analytics.py
+++ b/contextor/core/reporting_engine/graph_analytics.py
@@ -55,12 +55,118 @@ The implementation is deterministic and does not depend on networkx.
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
+        or handoff.complete is not True
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
+            or len(set(modules)) != len(modules)
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
+            or len(set(shared_keys)) != len(shared_keys)
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
@@ -1450,6 +1556,7 @@ def generate_graph_analytics_report(
     scope_modules: set[str] | None = None,
     global_artifact_data: dict | None = None,
     progress_callback=None,
+    raw_clusters_out: list[dict] | None = None,
 ) -> dict:
     """
     Generate the graph analytics report.
@@ -1840,6 +1947,9 @@ def generate_graph_analytics_report(
         progress_callback=progress_callback,
     )
 
+    if raw_clusters_out is not None and scope == "global":
+        raw_clusters_out.extend(clusters)
+
     clusters = _compact_clusters(
         clusters,
         index_dict,
@@ -2291,5 +2401,3 @@ __all__ = [
     "_compute_export_degrees",
 ]
 
-
-
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
diff --git a/tests/test_jaccard_handoff_0j5.py b/tests/test_jaccard_handoff_0j5.py
new file mode 100644
index 0000000..41ae439
--- /dev/null
+++ b/tests/test_jaccard_handoff_0j5.py
@@ -0,0 +1,355 @@
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
+    for complete in (1, "true", None):
+        assert not is_valid_shared_usage_clusters_handoff(
+            replace(valid, complete=complete),
+            artifact_data=artifact_data,
+            raw_artifacts=raw_artifacts,
+        )
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
+        {
+            **cluster,
+            "shared_artifact_count": 2,
+            "shared_artifact_keys": [
+                cluster["shared_artifact_keys"][0],
+                cluster["shared_artifact_keys"][0],
+            ],
+        },
+        {
+            **cluster,
+            "modules": [cluster["modules"][0], cluster["modules"][0]],
+        },
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
+    second_cluster = {
+        **cluster,
+        "modules": sorted([cluster["modules"][0], "zzzz_extra"]),
+        "size": 2,
+    }
+    assert not is_valid_shared_usage_clusters_handoff(
+        _handoff(artifact_data, clusters=[cluster, second_cluster]),
+        artifact_data=artifact_data,
+        raw_artifacts=raw_artifacts,
+    )
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
+        "intra_cluster_duplicate",
+        "cross_cluster_duplicate",
+        "complete_one",
+        "complete_string",
+        "complete_none",
+        "duplicate_shared_key",
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
+        elif mutation == "intra_cluster_duplicate":
+            cluster = {
+                **cluster,
+                "modules": [cluster["modules"][0], cluster["modules"][0]],
+            }
+        elif mutation == "cross_cluster_duplicate":
+            second_cluster = {
+                **cluster,
+                "modules": sorted([cluster["modules"][0], "zzzz_extra"]),
+                "size": 2,
+            }
+            result["_raw_shared_usage_clusters"] = replace(
+                handoff, clusters=(cluster, second_cluster)
+            )
+            return result
+        elif mutation == "complete_one":
+            result["_raw_shared_usage_clusters"] = replace(
+                handoff, complete=1
+            )
+            return result
+        elif mutation == "complete_string":
+            result["_raw_shared_usage_clusters"] = replace(
+                handoff, complete="true"
+            )
+            return result
+        elif mutation == "complete_none":
+            result["_raw_shared_usage_clusters"] = replace(
+                handoff, complete=None
+            )
+            return result
+        elif mutation == "duplicate_shared_key":
+            key = cluster["shared_artifact_keys"][0]
+            cluster = {
+                **cluster,
+                "shared_artifact_keys": [key, key],
+                "shared_artifact_count": 2,
+            }
+        result["_raw_shared_usage_clusters"] = replace(handoff, clusters=(cluster,))
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
INTRA_CLUSTER_DUPLICATES_REJECTED=PASS
CROSS_CLUSTER_DUPLICATES_REJECTED=PASS
COMPLETE_MARKER_EXACT=PASS
HANDOFF_VALIDATOR_FAIL_CLOSED=PASS
CURRENT_RUN_PROVENANCE=PROVEN
GLOBAL_JACCARD_COUNT=1
LAYER_JACCARD_COUNT=2
CANONICAL_JACCARD_COUNT=0
FALLBACK_CANONICAL_JACCARD_COUNT=1
WHOLE_ANALYSIS_CANDIDATE_MEDIAN_MS=6291.322954988573
CONTEXTOR_WORKSPACE_SYNC=verified/fresh revision 86, desktop-watcher events continuous, no resync
FILES_CHANGED=C:\Temp\Contextor_Repo\contextor\core\api\facade.py; C:\Temp\Contextor_Repo\contextor\core\reporting_engine\artifact_pipeline.py; C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py; C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py; C:\Temp\Contextor_Repo\tests\test_jaccard_handoff_0j5.py; C:\Temp\Contextor_Repo\tests\test_matrix_clusters_state_lifecycle.py

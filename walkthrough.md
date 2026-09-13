# F2L D1F Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/index.py`
- `contextor/core/analysis/state_manager.py`
- `contextor/core/analysis/incremental/plan_executor.py`
- `contextor/core/api/facade.py`
- `contextor/core/analysis/incremental/engine.py`
- `contextor/core/analysis/incremental/materialization.py`
- `contextor/core/live_state/store.py`
- `contextor/core/lineage_query/backend.py`
- `contextor/core/lineage_query/service.py`
- `tests/analysis/test_lineage_query_backend.py`
- `tests/analysis/test_lineage_query_service.py`
- `tests/test_full_analysis_lineage_materialization.py`
- `tests/test_lineage_state_lifecycle.py`

`walkthrough.md` is deliberately excluded from ACTUAL_DIFF.

## RAM_INDEX_CONTRACT

The state stores two RAM-only mappings: canonical semantic-owner ID to sorted source keys, and source key to sorted owner IDs. The index holds only identities and source keys; it does not duplicate flows, surfaces, anchors, or source text. Query readiness is represented by `lineage_query_index_state`; semantic-anchor completeness is stored with the lifecycle result.

## FULL_ANALYSIS_WIRING

Full analysis materializes lineage first, then builds both index mappings before constructing the published `RepositoryAnalysisState`. The full-analysis regression asserts a fresh index and validates an active artifact owner-to-source binding.

## INCREMENTAL_WIRING

Candidate state carries the index fields. Incremental lineage materialization rebuilds or patches the mappings after source updates/deletions; syntax invalidation removes the affected source from the index. The lifecycle regressions cover modify, delete, parse-error invalidation, and owner identity resynchronization.

## HYDRATION_WIRING

Snapshot hydration normalizes the index after existing lineage/symbol normalization. Missing legacy fields rebuild from hydrated materialized facts; malformed index input fails as an unpickling error. No query endpoint builds or repairs the index.

## PROOF_NO_QUERY_TIME_BUILD

Backend owner lookup reads the prebuilt owner-to-source mapping and is tested while `source_keys` and `get_source` are patched to fail. Backend metadata is likewise tested with source enumeration blocked. The direct-lineage service test patches `source_keys` to fail and still returns facts. Query-time code does not call `build_lineage_query_indexes`.

## TESTS_RUN

- `./.venv/Scripts/python.exe -m py_compile` for all nine changed production modules: PASS.
- `./.venv/Scripts/python.exe -m pytest -q tests/analysis/test_lineage_query_backend.py tests/analysis/test_lineage_query_service.py tests/test_full_analysis_lineage_materialization.py tests/test_lineage_state_lifecycle.py`: PASS — 72 passed in 7.58s.
- Scoped `git diff --check` for tracked task files and `git diff --no-index --check /dev/null` for the added index module: PASS (only CRLF conversion warnings).

## ACTUAL_DIFF

### contextor/core/lineage_query/index.py

```diff
diff --git a/contextor/core/lineage_query/index.py b/contextor/core/lineage_query/index.py
new file mode 100644
index 0000000..01482d7
--- /dev/null
+++ b/contextor/core/lineage_query/index.py
@@ -0,0 +1,112 @@
+from __future__ import annotations
+
+from collections.abc import Mapping
+
+from contextor.core.domain.lineage_facts import (
+    MaterializedLineageSourceFacts,
+    SemanticEndpoint,
+)
+
+
+def lineage_owner_ids_for_source(
+    source: MaterializedLineageSourceFacts,
+) -> tuple[str, ...]:
+    if not isinstance(source, MaterializedLineageSourceFacts):
+        raise TypeError("source must be MaterializedLineageSourceFacts.")
+
+    owners = {binding.owner_id for binding in source.semantic_anchors}
+    for flow in source.flows:
+        if isinstance(flow.source, SemanticEndpoint):
+            owners.add(flow.source.owner_id)
+        if isinstance(flow.target, SemanticEndpoint):
+            owners.add(flow.target.owner_id)
+    for surface in source.surfaces:
+        if isinstance(surface.exposed, SemanticEndpoint):
+            owners.add(surface.exposed.owner_id)
+    return tuple(sorted(owners))
+
+
+def semantic_anchor_bindings_complete(
+    sources: Mapping[str, MaterializedLineageSourceFacts],
+) -> bool:
+    return all(
+        source.manifest.semantic_anchor_bindings_materialized
+        for source in sources.values()
+    )
+
+
+def build_lineage_query_indexes(
+    sources: Mapping[str, MaterializedLineageSourceFacts],
+) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]], bool]:
+    if not isinstance(sources, Mapping):
+        raise TypeError("sources must be a mapping.")
+
+    owner_sources: dict[str, set[str]] = {}
+    source_owners: dict[str, tuple[str, ...]] = {}
+    for source_key in sorted(sources):
+        source = sources[source_key]
+        if not isinstance(source_key, str) or not source_key:
+            raise ValueError("lineage source key must be a non-empty string.")
+        if not isinstance(source, MaterializedLineageSourceFacts):
+            raise TypeError("lineage source value has invalid type.")
+        if source.manifest.source_key != source_key:
+            raise ValueError("lineage mapping key does not match source manifest.")
+
+        owners = lineage_owner_ids_for_source(source)
+        source_owners[source_key] = owners
+        for owner_id in owners:
+            owner_sources.setdefault(owner_id, set()).add(source_key)
+
+    return (
+        {
+            owner_id: tuple(sorted(source_keys))
+            for owner_id, source_keys in sorted(owner_sources.items())
+        },
+        dict(sorted(source_owners.items())),
+        semantic_anchor_bindings_complete(sources),
+    )
+
+
+def patch_lineage_query_indexes(
+    owner_source_index: Mapping[str, tuple[str, ...]],
+    source_owner_index: Mapping[str, tuple[str, ...]],
+    *,
+    source_key: str,
+    source: MaterializedLineageSourceFacts | None,
+) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
+    if not isinstance(source_key, str) or not source_key:
+        raise ValueError("source_key must be a non-empty string.")
+
+    owner_sources = {
+        str(owner_id): set(source_keys)
+        for owner_id, source_keys in owner_source_index.items()
+    }
+    source_owners = {
+        str(key): tuple(owners)
+        for key, owners in source_owner_index.items()
+    }
+    for owner_id in source_owners.pop(source_key, ()):
+        current = owner_sources.get(owner_id)
+        if current is None:
+            continue
+        current.discard(source_key)
+        if not current:
+            owner_sources.pop(owner_id, None)
+
+    if source is not None:
+        if not isinstance(source, MaterializedLineageSourceFacts):
+            raise TypeError("source must be MaterializedLineageSourceFacts or None.")
+        if source.manifest.source_key != source_key:
+            raise ValueError("source_key does not match source manifest.")
+        owners = lineage_owner_ids_for_source(source)
+        source_owners[source_key] = owners
+        for owner_id in owners:
+            owner_sources.setdefault(owner_id, set()).add(source_key)
+
+    return (
+        {
+            owner_id: tuple(sorted(source_keys))
+            for owner_id, source_keys in sorted(owner_sources.items())
+        },
+        dict(sorted(source_owners.items())),
+    )
```
### contextor/core/analysis/state_manager.py

```diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index a1fcfcd..197ebf8 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -98,6 +98,10 @@ class RepositoryAnalysisState:
     lineage_facts_by_source: Dict[str, MaterializedLineageSourceFacts] = field(default_factory=dict)
     lineage_facts_state: str = "not_materialized"
     lineage_facts_semantic_version: str | None = None
+    lineage_owner_source_index: Dict[str, tuple[str, ...]] = field(default_factory=dict)
+    lineage_source_owner_index: Dict[str, tuple[str, ...]] = field(default_factory=dict)
+    lineage_query_index_state: str = "not_materialized"
+    lineage_semantic_anchor_bindings_complete: bool = False
     topology_analytics: Dict[str, Any] = field(default_factory=dict)
     topology_metrics_state: str = "deferred"
     cached_analytics: Dict[str, Any] = field(default_factory=dict)
```

### contextor/core/analysis/incremental/plan_executor.py

```diff
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 86948a6..a45710b 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -48,6 +48,10 @@ class CandidateState:
     lineage_facts_by_source: Dict[str, MaterializedLineageSourceFacts]
     lineage_facts_state: str
     lineage_facts_semantic_version: str | None
+    lineage_owner_source_index: Dict[str, tuple[str, ...]]
+    lineage_source_owner_index: Dict[str, tuple[str, ...]]
+    lineage_query_index_state: str
+    lineage_semantic_anchor_bindings_complete: bool
     artifact_consumption: Dict[str, Any]
     dependency_graph: Optional[ProjectGraph]
     trie: Any
@@ -262,6 +266,20 @@ def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
             "lineage_facts_semantic_version",
             None,
         ),
+        lineage_owner_source_index=dict(
+            getattr(state, "lineage_owner_source_index", {}) or {}
+        ),
+        lineage_source_owner_index=dict(
+            getattr(state, "lineage_source_owner_index", {}) or {}
+        ),
+        lineage_query_index_state=getattr(
+            state,
+            "lineage_query_index_state",
+            "not_materialized",
+        ),
+        lineage_semantic_anchor_bindings_complete=bool(
+            getattr(state, "lineage_semantic_anchor_bindings_complete", False)
+        ),
         artifact_consumption=dict(state.artifact_consumption or {}),
         dependency_graph=state.dependency_graph,
         trie=state.trie,
```

### contextor/core/api/facade.py

```diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 279fd3b..37777c1 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -690,6 +690,20 @@ class ContextorFacade:
                 mods,
                 raw_artifacts,
             )
+            from contextor.core.lineage_query.index import (
+                build_lineage_query_indexes,
+            )
+
+            (
+                lineage_owner_source_index,
+                lineage_source_owner_index,
+                lineage_semantic_anchor_bindings_complete,
+            ) = build_lineage_query_indexes(lineage_facts_by_source)
+            lineage_query_index_state = (
+                "not_materialized"
+                if lineage_facts_state == "not_materialized"
+                else "fresh"
+            )

             state = RepositoryAnalysisState(
                 modules=mods,
@@ -706,6 +720,14 @@ class ContextorFacade:
                 lineage_facts_by_source=lineage_facts_by_source,
                 lineage_facts_state=lineage_facts_state,
                 lineage_facts_semantic_version=lineage_facts_semantic_version,
+                lineage_owner_source_index=lineage_owner_source_index,
+                lineage_source_owner_index=lineage_source_owner_index,
+                lineage_query_index_state=lineage_query_index_state,
+                lineage_semantic_anchor_bindings_complete=(
+                    lineage_semantic_anchor_bindings_complete
+                    if lineage_query_index_state == "fresh"
+                    else False
+                ),
                 metrics=metrics,
                 topology_analytics=topology_analytics,
                 topology_metrics_state="fresh",
```

### contextor/core/analysis/incremental/engine.py

```diff
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index c0ed5b6..097d471 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -122,6 +122,9 @@ class IncrementalAnalysisEngine:
                 LINEAGE_FACTS_SEMANTIC_VERSION,
                 LineageFamilyStatus,
             )
+            from contextor.core.lineage_query.index import (
+                build_lineage_query_indexes,
+            )

             candidate.lineage_facts_by_source.pop(source_path, None)
             if candidate.lineage_facts_state == LineageFamilyStatus.NOT_MATERIALIZED.value:
@@ -130,6 +133,19 @@ class IncrementalAnalysisEngine:
             else:
                 candidate.lineage_facts_state = LineageFamilyStatus.STALE.value
                 candidate.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION
+            (
+                candidate.lineage_owner_source_index,
+                candidate.lineage_source_owner_index,
+                candidate.lineage_semantic_anchor_bindings_complete,
+            ) = build_lineage_query_indexes(candidate.lineage_facts_by_source)
+            candidate.lineage_query_index_state = (
+                "not_materialized"
+                if candidate.lineage_facts_state
+                == LineageFamilyStatus.NOT_MATERIALIZED.value
+                else "fresh"
+            )
+            if candidate.lineage_query_index_state != "fresh":
+                candidate.lineage_semantic_anchor_bindings_complete = False
         elif extracted_lineage_facts is not None:
             with self.registry.read_transaction():
                 self._update_candidate_lineage_slice(
@@ -162,6 +178,12 @@ class IncrementalAnalysisEngine:
         self.state.lineage_facts_semantic_version = (
             candidate.lineage_facts_semantic_version
         )
+        self.state.lineage_owner_source_index = candidate.lineage_owner_source_index
+        self.state.lineage_source_owner_index = candidate.lineage_source_owner_index
+        self.state.lineage_query_index_state = candidate.lineage_query_index_state
+        self.state.lineage_semantic_anchor_bindings_complete = (
+            candidate.lineage_semantic_anchor_bindings_complete
+        )

     def _update_candidate_lineage_slice(
         self,
@@ -303,6 +325,43 @@ class IncrementalAnalysisEngine:
         else:
             candidate.lineage_facts_state = LineageFamilyStatus.FRESH.value

+        from contextor.core.lineage_query.index import (
+            build_lineage_query_indexes,
+            patch_lineage_query_indexes,
+            semantic_anchor_bindings_complete,
+        )
+
+        if rematerialize_all or candidate.lineage_query_index_state != "fresh":
+            (
+                candidate.lineage_owner_source_index,
+                candidate.lineage_source_owner_index,
+                candidate.lineage_semantic_anchor_bindings_complete,
+            ) = build_lineage_query_indexes(lineage_by_source)
+        else:
+            (
+                candidate.lineage_owner_source_index,
+                candidate.lineage_source_owner_index,
+            ) = patch_lineage_query_indexes(
+                candidate.lineage_owner_source_index,
+                candidate.lineage_source_owner_index,
+                source_key=source_path,
+                source=(
+                    None if delete else lineage_by_source.get(source_path)
+                ),
+            )
+            candidate.lineage_semantic_anchor_bindings_complete = (
+                semantic_anchor_bindings_complete(lineage_by_source)
+            )
+
+        candidate.lineage_query_index_state = (
+            "not_materialized"
+            if candidate.lineage_facts_state
+            == LineageFamilyStatus.NOT_MATERIALIZED.value
+            else "fresh"
+        )
+        if candidate.lineage_query_index_state != "fresh":
+            candidate.lineage_semantic_anchor_bindings_complete = False
+
     def update_file(self, file_path: str) -> IncrementalUpdateResult:
         """
         Updates the canonical state incrementally for a single changed file.
@@ -697,6 +756,12 @@ class IncrementalAnalysisEngine:
         self.state.lineage_facts_semantic_version = (
             candidate.lineage_facts_semantic_version
         )
+        self.state.lineage_owner_source_index = candidate.lineage_owner_source_index
+        self.state.lineage_source_owner_index = candidate.lineage_source_owner_index
+        self.state.lineage_query_index_state = candidate.lineage_query_index_state
+        self.state.lineage_semantic_anchor_bindings_complete = (
+            candidate.lineage_semantic_anchor_bindings_complete
+        )
         self.state.trie = candidate.trie
         self.state.package_root = candidate.package_root
```

### contextor/core/analysis/incremental/materialization.py

```diff
diff --git a/contextor/core/analysis/incremental/materialization.py b/contextor/core/analysis/incremental/materialization.py
index 2750523..5a72dff 100644
--- a/contextor/core/analysis/incremental/materialization.py
+++ b/contextor/core/analysis/incremental/materialization.py
@@ -12,6 +12,40 @@ from typing import Optional, Any
 from contextor.core.analysis.state_manager import RepositoryAnalysisState


+def ensure_lineage_query_index(state: RepositoryAnalysisState) -> None:
+    """Ensure the RAM lineage access index exists without source work."""
+    from contextor.core.lineage_query.index import build_lineage_query_indexes
+
+    family_state = getattr(state, "lineage_facts_state", "not_materialized")
+    sources = getattr(state, "lineage_facts_by_source", {}) or {}
+    if family_state == "not_materialized":
+        state.lineage_owner_source_index = {}
+        state.lineage_source_owner_index = {}
+        state.lineage_query_index_state = "not_materialized"
+        state.lineage_semantic_anchor_bindings_complete = False
+        return
+    if (
+        getattr(state, "lineage_query_index_state", None) == "fresh"
+        and isinstance(getattr(state, "lineage_owner_source_index", None), dict)
+        and isinstance(getattr(state, "lineage_source_owner_index", None), dict)
+    ):
+        return
+    try:
+        owner_source_index, source_owner_index, anchor_complete = (
+            build_lineage_query_indexes(sources)
+        )
+    except (TypeError, ValueError):
+        state.lineage_owner_source_index = {}
+        state.lineage_source_owner_index = {}
+        state.lineage_query_index_state = "stale"
+        state.lineage_semantic_anchor_bindings_complete = False
+        return
+    state.lineage_owner_source_index = owner_source_index
+    state.lineage_source_owner_index = source_owner_index
+    state.lineage_query_index_state = "fresh"
+    state.lineage_semantic_anchor_bindings_complete = anchor_complete
+
+
 def module_usages_require_materialization(state: RepositoryAnalysisState) -> bool:
     """Return whether a missing or legacy usage slice needs canonical extraction."""
     usages = getattr(state, "module_usages", None)
@@ -509,6 +543,7 @@ def materialize_incremental_state(state: RepositoryAnalysisState) -> None:
     6. ensure_collisions (RAM-only)
     7. ensure_dependency_matrix (RAM-only, after artifact_consumption is resolved)
     8. ensure_shared_usage_clusters (RAM-only, after artifact_consumption is resolved)
+    9. ensure_lineage_query_index (RAM-only access index over canonical lineage)
     """
     ensure_artifact_consumption(state)
     ensure_module_usages(state)
@@ -518,3 +553,4 @@ def materialize_incremental_state(state: RepositoryAnalysisState) -> None:
     ensure_collisions(state)
     ensure_dependency_matrix(state)
     ensure_shared_usage_clusters(state)
+    ensure_lineage_query_index(state)
```

### contextor/core/live_state/store.py

```diff
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 74f258d..28fed1f 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -352,6 +352,34 @@ def _normalize_lineage_facts_state(state: Any) -> Any:
         ) from exc


+def _normalize_lineage_query_index_state(state: Any) -> Any:
+    """Rebuild the derived index during hydration, never during a query."""
+    if state is None or isinstance(state, dict) or not hasattr(state, "__dict__"):
+        return state
+    from contextor.core.lineage_query.index import build_lineage_query_indexes
+
+    family_state = getattr(state, "lineage_facts_state", "not_materialized")
+    sources = getattr(state, "lineage_facts_by_source", {}) or {}
+    if family_state == "not_materialized":
+        state.lineage_owner_source_index = {}
+        state.lineage_source_owner_index = {}
+        state.lineage_query_index_state = "not_materialized"
+        state.lineage_semantic_anchor_bindings_complete = False
+        return state
+    try:
+        (
+            state.lineage_owner_source_index,
+            state.lineage_source_owner_index,
+            state.lineage_semantic_anchor_bindings_complete,
+        ) = build_lineage_query_indexes(sources)
+    except (TypeError, ValueError) as exc:
+        raise pickle.UnpicklingError(
+            "Invalid canonical lineage query index inputs."
+        ) from exc
+    state.lineage_query_index_state = "fresh"
+    return state
+
+
 @dataclass(frozen=True)
 class LiveStateMetadata:
     schema_version: str = LIVE_STATE_SCHEMA_VERSION
@@ -580,8 +608,10 @@ def load_snapshot(
             )
             if embedded_metadata.revision != metadata.revision:
                 return None
-            state_obj = _normalize_lineage_facts_state(
-                _normalize_symbol_call_facts(payload["state"])
+            state_obj = _normalize_lineage_query_index_state(
+                _normalize_lineage_facts_state(
+                    _normalize_symbol_call_facts(payload["state"])
+                )
             )
             state_revision = (
                 state_obj.get("revision") if isinstance(state_obj, dict)
@@ -688,8 +718,10 @@ def load_snapshot(
                     except AttributeError:
                         pass
             return state_obj, metadata
-        payload = _normalize_lineage_facts_state(
-            _normalize_symbol_call_facts(payload)
+        payload = _normalize_lineage_query_index_state(
+            _normalize_lineage_facts_state(
+                _normalize_symbol_call_facts(payload)
+            )
         )
         if payload is not None and hasattr(payload, "__dict__"):
             if not hasattr(payload, "module_usages"):
```

### contextor/core/lineage_query/backend.py

```diff
diff --git a/contextor/core/lineage_query/backend.py b/contextor/core/lineage_query/backend.py
index 8cae93f..e0e5a5b 100644
--- a/contextor/core/lineage_query/backend.py
+++ b/contextor/core/lineage_query/backend.py
@@ -22,6 +22,7 @@ class LineageBackendMetadata:
     family_state: str
     semantic_version: str | None
     source_count: int
+    query_index_state: str
     semantic_anchor_bindings_complete: bool


@@ -106,13 +107,15 @@ class RepositoryStateLineageBackend:
                 "Canonical lineage semantic version must be a non-empty string or None."
             )

-        semantic_anchor_bindings_complete = (
-            family_state == LineageFamilyStatus.FRESH.value
-            and all(
-                self.get_source(source_key)
-                .manifest.semantic_anchor_bindings_materialized
-                for source_key in self.source_keys()
-            )
+        query_index_state = getattr(
+            self._state,
+            "lineage_query_index_state",
+            "not_materialized",
+        )
+        if query_index_state not in {"not_materialized", "fresh", "stale"}:
+            raise ValueError("Canonical lineage query index state is invalid.")
+        semantic_anchor_bindings_complete = bool(
+            getattr(self._state, "lineage_semantic_anchor_bindings_complete", False)
         )
         return LineageBackendMetadata(
             revision=raw_revision,
@@ -120,7 +123,12 @@ class RepositoryStateLineageBackend:
             family_state=family_state,
             semantic_version=semantic_version,
             source_count=len(self._sources),
-            semantic_anchor_bindings_complete=semantic_anchor_bindings_complete,
+            query_index_state=query_index_state,
+            semantic_anchor_bindings_complete=(
+                semantic_anchor_bindings_complete
+                if query_index_state == "fresh"
+                else False
+            ),
         )

     def source_keys(self) -> tuple[str, ...]:
@@ -156,33 +164,18 @@ class RepositoryStateLineageBackend:
         if not isinstance(owner_id, str) or not owner_id:
             raise ValueError("owner_id must be a non-empty string.")

-        matches: list[str] = []
-        for source_key in self.source_keys():
-            source = self.get_source(source_key)
-            assert source is not None
-            flow_match = any(
-                (
-                    isinstance(flow.source, SemanticEndpoint)
-                    and flow.source.owner_id == owner_id
-                )
-                or (
-                    isinstance(flow.target, SemanticEndpoint)
-                    and flow.target.owner_id == owner_id
-                )
-                for flow in source.flows
-            )
-            surface_match = any(
-                isinstance(surface.exposed, SemanticEndpoint)
-                and surface.exposed.owner_id == owner_id
-                for surface in source.surfaces
-            )
-            anchor_match = any(
-                binding.owner_id == owner_id
-                for binding in source.semantic_anchors
-            )
-            if flow_match or surface_match or anchor_match:
-                matches.append(source_key)
-        return tuple(matches)
+        if getattr(self._state, "lineage_query_index_state", "not_materialized") != "fresh":
+            raise ValueError("Canonical lineage query index is unavailable or stale.")
+        raw_index = getattr(self._state, "lineage_owner_source_index", {})
+        if not isinstance(raw_index, Mapping):
+            raise TypeError("lineage_owner_source_index must be a mapping.")
+        source_keys = raw_index.get(owner_id, ())
+        if not isinstance(source_keys, tuple) or any(
+            not isinstance(source_key, str) or not source_key
+            for source_key in source_keys
+        ):
+            raise TypeError("lineage_owner_source_index contains invalid source keys.")
+        return source_keys

     def iter_sources(
         self,
```

### contextor/core/lineage_query/service.py

```diff
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
index 660f10c..ba8c258 100644
--- a/contextor/core/lineage_query/service.py
+++ b/contextor/core/lineage_query/service.py
@@ -67,6 +67,7 @@ class DirectLineageFacts:
     def complete(self) -> bool:
         return (
             self.metadata.family_state == "fresh"
+            and self.metadata.query_index_state == "fresh"
             and self.metadata.semantic_anchor_bindings_complete
         )
```

### tests/analysis/test_lineage_query_backend.py

```diff
diff --git a/tests/analysis/test_lineage_query_backend.py b/tests/analysis/test_lineage_query_backend.py
index c44686e..8d524df 100644
--- a/tests/analysis/test_lineage_query_backend.py
+++ b/tests/analysis/test_lineage_query_backend.py
@@ -39,6 +39,10 @@ def _state():
             provenance="live",
             lineage_facts_state="fresh",
             lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+            lineage_owner_source_index={},
+            lineage_source_owner_index={"pkg/a.py": (), "pkg/b.py": ()},
+            lineage_query_index_state="fresh",
+            lineage_semantic_anchor_bindings_complete=True,
             lineage_facts_by_source={
                 "pkg/b.py": source_b,
                 "pkg/a.py": source_a,
@@ -60,6 +64,7 @@ def test_repository_state_backend_exposes_canonical_metadata():
         family_state="fresh",
         semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
         source_count=2,
+        query_index_state="fresh",
         semantic_anchor_bindings_complete=True,
     )

@@ -88,6 +93,7 @@ def test_repository_state_backend_defaults_to_not_materialized():
         family_state="not_materialized",
         semantic_version=None,
         source_count=0,
+        query_index_state="not_materialized",
         semantic_anchor_bindings_complete=False,
     )
     assert backend.source_keys() == ()
@@ -135,3 +141,48 @@ def test_repository_state_backend_rejects_string_as_source_collection():

     with pytest.raises(TypeError, match="iterable of source-key strings"):
         backend.iter_sources("pkg/a.py")
+
+
+def test_owner_lookup_reads_only_prebuilt_index(monkeypatch):
+    state, _, _ = _state()
+    state.lineage_owner_source_index = {"A17/2": ("pkg/a.py",)}
+    backend = RepositoryStateLineageBackend(state)
+    monkeypatch.setattr(
+        backend,
+        "source_keys",
+        lambda: (_ for _ in ()).throw(AssertionError("repo scan")),
+    )
+    monkeypatch.setattr(
+        backend,
+        "get_source",
+        lambda _key: (_ for _ in ()).throw(AssertionError("slice read")),
+    )
+
+    assert backend.source_keys_for_owner("A17/2") == ("pkg/a.py",)
+
+
+def test_metadata_does_not_scan_sources(monkeypatch):
+    state, _, _ = _state()
+    backend = RepositoryStateLineageBackend(state)
+    monkeypatch.setattr(
+        backend,
+        "source_keys",
+        lambda: (_ for _ in ()).throw(AssertionError("repo scan")),
+    )
+    monkeypatch.setattr(
+        backend,
+        "get_source",
+        lambda _key: (_ for _ in ()).throw(AssertionError("slice read")),
+    )
+
+    assert backend.metadata().query_index_state == "fresh"
+
+
+@pytest.mark.parametrize("index_state", ["stale", "not_materialized"])
+def test_owner_lookup_fails_closed_without_fresh_index(index_state):
+    state, _, _ = _state()
+    state.lineage_query_index_state = index_state
+    backend = RepositoryStateLineageBackend(state)
+
+    with pytest.raises(ValueError, match="unavailable or stale"):
+        backend.source_keys_for_owner("A17/2")
```

### tests/analysis/test_lineage_query_service.py

```diff
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
index b1d8155..6561f92 100644
--- a/tests/analysis/test_lineage_query_service.py
+++ b/tests/analysis/test_lineage_query_service.py
@@ -26,6 +26,7 @@ from contextor.core.lineage_query import (
     RepositoryStateLineageBackend,
     ResolvedLineageTarget,
 )
+from contextor.core.lineage_query.index import build_lineage_query_indexes
 from contextor.core.report_query import IndexCatalog


@@ -300,16 +301,24 @@ def _direct_service(*, family_state="fresh"):
         ),
     )

+    sources = {
+        "pkg/b.py": source_b,
+        "pkg/a.py": source_a,
+    }
+    owner_source_index, source_owner_index, anchor_complete = (
+        build_lineage_query_indexes(sources)
+    )
     backend = RepositoryStateLineageBackend(
         SimpleNamespace(
             revision=21,
             provenance="live",
             lineage_facts_state=family_state,
             lineage_facts_semantic_version="1",
-            lineage_facts_by_source={
-                "pkg/b.py": source_b,
-                "pkg/a.py": source_a,
-            },
+            lineage_facts_by_source=sources,
+            lineage_owner_source_index=owner_source_index,
+            lineage_source_owner_index=source_owner_index,
+            lineage_query_index_state="fresh",
+            lineage_semantic_anchor_bindings_complete=anchor_complete,
         )
     )
     service = LineageQueryService(
@@ -420,11 +429,19 @@ def test_direct_facts_seed_ordinary_symbol_from_semantic_anchor_binding():
         surfaces=(surface,),
         semantic_anchors=(binding,),
     )
+    sources = {source_key: source}
+    owner_source_index, source_owner_index, anchor_complete = (
+        build_lineage_query_indexes(sources)
+    )
     backend = RepositoryStateLineageBackend(
         SimpleNamespace(
             lineage_facts_state="fresh",
             lineage_facts_semantic_version="1",
-            lineage_facts_by_source={source_key: source},
+            lineage_facts_by_source=sources,
+            lineage_owner_source_index=owner_source_index,
+            lineage_source_owner_index=source_owner_index,
+            lineage_query_index_state="fresh",
+            lineage_semantic_anchor_bindings_complete=anchor_complete,
         )
     )
     service = LineageQueryService(
@@ -454,9 +471,24 @@ def test_direct_facts_are_incomplete_when_fresh_slice_lacks_anchor_materializati
         "semantic_anchor_bindings_materialized",
         False,
     )
+    backend._state.lineage_semantic_anchor_bindings_complete = False

     result = service.direct_facts(target)

     assert result.metadata.family_state == "fresh"
     assert result.metadata.semantic_anchor_bindings_complete is False
     assert result.complete is False
+
+
+def test_direct_facts_never_enumerates_repo_wide_source_keys(monkeypatch):
+    service, backend, target, _ = _direct_service()
+    monkeypatch.setattr(
+        backend,
+        "source_keys",
+        lambda: (_ for _ in ()).throw(AssertionError("repo scan")),
+    )
+
+    result = service.direct_facts(target)
+
+    assert result.incoming
+    assert result.outgoing
```

### tests/test_full_analysis_lineage_materialization.py

```diff
diff --git a/tests/test_full_analysis_lineage_materialization.py b/tests/test_full_analysis_lineage_materialization.py
index 5d84ec3..722864e 100644
--- a/tests/test_full_analysis_lineage_materialization.py
+++ b/tests/test_full_analysis_lineage_materialization.py
@@ -183,6 +183,7 @@ def test_real_full_analysis_installs_current_lineage_without_second_extraction(t
     state = captured_states[0]
     assert state.lineage_facts_state == "fresh"
     assert state.lineage_facts_semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
+    assert state.lineage_query_index_state == "fresh"
     assert set(state.lineage_facts_by_source) == {"consumer.py", "provider.py"}
     assert all(
         source_key == source_slice.manifest.source_key
@@ -193,6 +194,8 @@ def test_real_full_analysis_installs_current_lineage_without_second_extraction(t
         provider_target_id = registry._state["artifact_registry"]["path_to_id"]["provider::target"]
     assert state.lineage_facts_by_source["provider.py"].surfaces[0].exposed == SemanticEndpoint(provider_target_id)
     assert state.lineage_facts_by_source["consumer.py"].surfaces[0].exposed == SemanticEndpoint(provider_target_id)
+    assert provider_target_id in state.lineage_owner_source_index
+    assert "provider.py" in state.lineage_owner_source_index[provider_target_id]


 def test_exact_surface_materialization_uses_symbolic_targets_and_preserves_external_boundary():
```

### tests/test_lineage_state_lifecycle.py

```diff
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index b1ffd80..bdc4968 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -130,6 +130,10 @@ def _persist_corrupted_lineage_slice(
         lineage_facts_state="fresh",
         lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
     )
+    object.__delattr__(state, "lineage_owner_source_index")
+    object.__delattr__(state, "lineage_source_owner_index")
+    object.__delattr__(state, "lineage_query_index_state")
+    object.__delattr__(state, "lineage_semantic_anchor_bindings_complete")
     save_snapshot(state, tmp_path, state_id)
     return load_snapshot(tmp_path, expected_state_id=state_id)

@@ -192,6 +196,8 @@ def test_snapshot_round_trip_preserves_lineage_endpoint_types_and_metadata(
     assert loaded_slice.surfaces[0].provider == ProviderRef("fixture", "1")
     assert loaded_slice.surfaces[0].dynamic_boundary == "runtime-registration"
     assert loaded_slice.semantic_anchors == source_slice.semantic_anchors
+    assert loaded.lineage_query_index_state == "fresh"
+    assert loaded.lineage_owner_source_index


 def test_snapshot_legacy_semantic_anchor_fields_fail_closed(tmp_path):
@@ -217,6 +223,7 @@ def test_snapshot_legacy_semantic_anchor_fields_fail_closed(tmp_path):

     assert loaded_slice.manifest.semantic_anchor_bindings_materialized is False
     assert loaded_slice.semantic_anchors == ()
+    assert loaded.lineage_query_index_state == "fresh"


 @pytest.mark.parametrize(
@@ -701,6 +708,8 @@ def test_incremental_lineage_modify_replaces_only_changed_candidate_slice(tmp_pa
     assert candidate.lineage_facts_by_source["other.py"] is other
     assert candidate.lineage_facts_state == "fresh"
     assert candidate.lineage_facts_semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
+    assert candidate.lineage_query_index_state == "fresh"
+    assert "pkg.py" in candidate.lineage_source_owner_index


 def test_incremental_lineage_delete_removes_only_deleted_slice(tmp_path):
@@ -729,6 +738,8 @@ def test_incremental_lineage_delete_removes_only_deleted_slice(tmp_path):

     assert candidate.lineage_facts_by_source == {"other.py": other}
     assert candidate.lineage_facts_state == "fresh"
+    assert candidate.lineage_query_index_state == "fresh"
+    assert "pkg.py" not in candidate.lineage_source_owner_index


 def test_lineage_only_noop_commit_replaces_slice_and_parse_error_invalidates_it(tmp_path):
@@ -767,6 +778,8 @@ def test_lineage_only_noop_commit_replaces_slice_and_parse_error_invalidates_it(
     assert state.lineage_facts_by_source["other.py"] is other
     assert state.lineage_facts_state == "stale"
     assert state.lineage_facts_semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
+    assert state.lineage_query_index_state == "fresh"
+    assert "pkg.py" not in state.lineage_source_owner_index

     engine._commit_syntax_candidate(
         source_path="pkg.py",
@@ -1170,6 +1183,8 @@ def test_identity_sync_generation_change_rematerializes_against_current_owner_id
     assert consumer_surface.exposed == SemanticEndpoint("A:provider/2")
     assert consumer_surface.exposed != SemanticEndpoint("A:provider/1")
     assert registry._state["artifact_registry"]["path_to_id"]["provider::target"] == "A:provider/2"
+    assert "A:provider/1" not in state.lineage_owner_source_index
+    assert "A:provider/2" in state.lineage_owner_source_index


 def test_identity_sync_revalidation_failure_rolls_back_registry_and_canonical_state(
```

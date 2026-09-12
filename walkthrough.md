# Antigravity Walkthrough

STATUS

PASS_TARGETED. The incremental canonical lineage blocker is fixed. Targeted implementation and regression tests are green; full pytest and the external F2L-READY LIVE rerun were intentionally not run.

ROOT_CAUSE_CONFIRMATION

Contextor discovery confirmed that `_apply_delta_and_commit` performed identity registry synchronization and then called `_update_candidate_lineage_slice` only for the changed/deleted source. Untouched materialized slices therefore retained old `SemanticEndpoint.owner_id` values after active-owner changes.

A deterministic A-only repair is not possible from the existing materialized representation: `SemanticEndpoint` retains only `owner_id` and `slot`, while the symbolic kind, module name, symbol name, and source-local id needed to reconstruct `MaterializedSymbolicRef` are discarded when materialization strengthens a reference.

IMPLEMENTATION_STRATEGY=C

Retain the already-produced immutable `ExtractedLineageSourceFacts` per source in canonical analysis state, carry it through Copy-on-Write candidates, and rematerialize all retained slices after the final registry view is established.

WHY_THIS_STRATEGY

Strategy A cannot demote an invalid endpoint without guessing discarded symbolic fields. Strategy B was unavailable because extracted lineage existed only transiently in `RepositoryIndex`/prepared source updates and was not retained in `RepositoryAnalysisState` or `CandidateState`. Strategy C adds only that minimal retained materialization input; it does not scan, parse, or re-extract untouched sources.

CANONICAL_LIFECYCLE_CHANGE

- Full analysis stores `index.lineage_facts_by_source` as `lineage_extracted_facts_by_source` alongside the materialized slices.
- Candidate preparation copies the retained extracted map. Changed sources replace their extracted entry; deleted sources remove it.
- During `identity_sync_required`, registry sync and all retained-slice rematerialization run inside the existing registry transaction before canonical candidate publication.
- Rematerialization resolves every endpoint against the post-sync active module/artifact maps and keeps `interface_descriptors={}` unchanged.
- If a fresh-looking state contains materialized slices with no retained extracted input during an identity resync, the candidate is marked STALE fail-closed instead of publishing a false FRESH result.
- Snapshot normalization accepts legacy states without retained extracted facts as an empty map, validates new retained entries, and preserves the existing no-source-work hydration contract.

FULL_VS_INCREMENTAL_PARITY_PROOF

The deletion parity test compares lineage family state, semantic version, source-key set, full materialized source slices, manifests, anchors, flows, surfaces, endpoint types, owner ids, slots, and symbolic references against fresh full materialization of the same final repository state. The incremental consumer slice equals the fresh full slice and its former provider endpoint is a `MaterializedSymbolicRef`.

The owner-introduction test starts with the untouched consumer symbolic boundary, adds the exact provider owner, and proves incremental rematerialization strengthens it to the same `SemanticEndpoint` produced by full analysis. The retained consumer object is used directly; extraction is guarded to fail if invoked.

OWNER_DELETION_PROOF

After provider deletion, the provider slice and retained provider extracted facts are removed. The untouched consumer is rematerialized against an active registry with no provider artifact, so its exact reference becomes symbolic and the old provider owner id cannot remain in any fresh semantic endpoint.

OWNER_INTRODUCTION_PROOF

When the provider is introduced, only the provider extracted facts are supplied to the incremental commit. The retained untouched consumer is rematerialized against the newly active `provider::target` owner and reaches the same semantic endpoint as full analysis.

GENERATION_ID_PROOF

A focused lifecycle test changes the active owner generation from `A:provider/1` to `A:provider/2`. Rematerialization uses the finalized active registry id and produces `SemanticEndpoint("A:provider/2")`; the old id is not treated as current merely because the canonical owner name is unchanged.

ATOMICITY_PROOF

The retained-slice rematerialization runs within the existing registry write transaction. A focused failure injected while rematerializing the untouched consumer leaves canonical modules, artifacts, extracted facts, materialized facts, registry active mappings, and state-manager acknowledgement unchanged. The existing `test_identity_sync_materializes_against_new_ids_and_rolls_back_on_failure` also remains green.

INVARIANTS_PRESERVED

- No source scan, AST parse, or lineage extraction is added for untouched sources.
- `MaterializedOccurrenceRef` remains slice-local.
- `MaterializedSymbolicRef` remains the symbolic boundary.
- `SemanticEndpoint` is produced only from active registry owner mappings and the existing slot contract.
- `interface_descriptors={}`, Gate2/D1 freshness presentation, query tools, and build-state freshness were not changed.
- Manifest source key/fingerprint validation and fail-closed missing-owner validation remain in place.
- COW publication occurs only after registry and lineage work succeeds.

FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py`
- `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py`
- `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py`
- `C:\Temp\Contextor_Repo\contextor\core\api\facade.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py`
- `C:\Temp\Contextor_Repo\tests\test_full_analysis_lineage_materialization.py`
- `C:\Temp\Contextor_Repo\tests\test_lineage_state_lifecycle.py`

`walkthrough.md` is intentionally excluded from this list and from ACTUAL_DIFF.

TESTS_RUN

- `& '.\\.venv\\Scripts\\python.exe' -m pytest tests/test_lineage_state_lifecycle.py tests/test_full_analysis_lineage_materialization.py tests/analysis/test_lineage_materialization.py -q` -> 45 passed.
- `& '.\\.venv\\Scripts\\python.exe' -m pytest tests/test_completeness_freshness_parity_proof.py -q` -> 31 passed.
- `git diff --check` on the seven task files (with walkthrough.md excluded from the embedded raw-diff report) -> passed.
- No full pytest was run, per task gate.

BEHAVIORAL_PROOF

The final incremental lineage map is rebuilt from retained extracted facts only, not from untouched source files. Full-analysis and incremental outputs agree for provider deletion and provider introduction. Invalid old-generation endpoints are replaced using the active owner domain, and any lifecycle repair failure prevents both registry and canonical publication.

REMAINING_RISKS

Legacy snapshots that contain materialized lineage but predate retained extracted facts cannot be losslessly rematerialized after an identity change; the implementation marks such a candidate STALE rather than guessing. A full pytest and the Desktop/LIVE F2L-READY certification rerun remain for the user’s next gate.

CONTEXTOR_TOOL_USAGE

Contextor MCP was active immediately; deferred-tool loading was not needed. Architectural discovery was first and used `get_mcp_documentation`, `get_artifacts_for_module`, `search_source`, and `get_symbol_implementation` for the incremental engine, lineage materializer, state/candidate ownership, facade, and persistent registry. Git/textual inspection was used only afterward for focused verification.

ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/core/analysis/incremental/engine.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/analysis/incremental/plan_executor.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/analysis/state_manager.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/api/facade.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/live_state/store.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_full_analysis_lineage_materialization.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_lineage_state_lifecycle.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index 6b7f02f..9dcf625 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -124,6 +124,7 @@ class IncrementalAnalysisEngine:
             )
 
             candidate.lineage_facts_by_source.pop(source_path, None)
+            candidate.lineage_extracted_facts_by_source.pop(source_path, None)
             if candidate.lineage_facts_state == LineageFamilyStatus.NOT_MATERIALIZED.value:
                 candidate.lineage_facts_state = LineageFamilyStatus.NOT_MATERIALIZED.value
                 candidate.lineage_facts_semantic_version = None
@@ -157,6 +158,9 @@ class IncrementalAnalysisEngine:
         self.state.syntax_diagnostics_by_path = candidate.syntax_diagnostics_by_path
         self.state.syntax_diagnostics_state = candidate.syntax_diagnostics_state
         self.state.module_parse_freshness = candidate.module_parse_freshness
+        self.state.lineage_extracted_facts_by_source = (
+            candidate.lineage_extracted_facts_by_source
+        )
         self.state.lineage_facts_by_source = candidate.lineage_facts_by_source
         self.state.lineage_facts_state = candidate.lineage_facts_state
         self.state.lineage_facts_semantic_version = (
@@ -170,8 +174,9 @@ class IncrementalAnalysisEngine:
         source_path: str,
         extracted_lineage_facts: Any | None = None,
         delete: bool = False,
+        rematerialize_all: bool = False,
     ) -> None:
-        """Install or remove exactly one source-keyed lineage slice on a COW candidate."""
+        """Install/remove lineage and optionally rebuild all retained slices."""
         from contextor.core.analysis.lineage_materialization import (
             LineageResolutionContext,
             materialize_lineage_source_facts,
@@ -188,10 +193,12 @@ class IncrementalAnalysisEngine:
             Path(str(module.path)).as_posix()
             for module in candidate.modules.values()
         }
+        extracted_by_source = candidate.lineage_extracted_facts_by_source
         lineage_by_source = candidate.lineage_facts_by_source
 
         if delete:
             lineage_by_source.pop(source_path, None)
+            extracted_by_source.pop(source_path, None)
             candidate.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION
         else:
             if extracted_lineage_facts is None:
@@ -200,7 +207,26 @@ class IncrementalAnalysisEngine:
                 raise ValueError("Extracted lineage source key does not match incremental source.")
             if source_path not in eligible_source_keys:
                 raise ValueError("Incremental lineage source is outside the active candidate.")
+            extracted_by_source[source_path] = extracted_lineage_facts
+
+        foreign_extracted_keys = set(extracted_by_source) - eligible_source_keys
+        if foreign_extracted_keys:
+            raise ValueError(
+                "Extracted lineage contains sources outside the active candidate: "
+                f"{sorted(foreign_extracted_keys)!r}"
+            )
+        for source_key, extracted in extracted_by_source.items():
+            if extracted.source_key != source_key:
+                raise ValueError(
+                    "Extracted lineage mapping key does not match its source key."
+                )
 
+        source_keys_to_materialize = (
+            tuple(sorted(extracted_by_source))
+            if rematerialize_all
+            else (() if delete else (source_path,))
+        )
+        if source_keys_to_materialize:
             active_module_names = set(candidate.modules)
             active_artifact_names = collect_qualified_artifact_identities(
                 candidate.artifacts
@@ -234,21 +260,29 @@ class IncrementalAnalysisEngine:
                 ),
                 interface_descriptors={},
             )
-            materialized = materialize_lineage_source_facts(
-                extracted_lineage_facts,
-                resolution,
-            )
-            if (
-                materialized.manifest.source_key != extracted_lineage_facts.source_key
-                or materialized.manifest.source_fingerprint
-                != extracted_lineage_facts.source_fingerprint
-            ):
-                raise ValueError(
-                    "Materialized lineage manifest does not match extracted source."
+            for source_key in source_keys_to_materialize:
+                extracted = extracted_by_source[source_key]
+                materialized = materialize_lineage_source_facts(
+                    extracted,
+                    resolution,
                 )
-            lineage_by_source[source_path] = materialized
+                if (
+                    materialized.manifest.source_key != extracted.source_key
+                    or materialized.manifest.source_fingerprint
+                    != extracted.source_fingerprint
+                ):
+                    raise ValueError(
+                        "Materialized lineage manifest does not match extracted source."
+                    )
+                lineage_by_source[source_key] = materialized
             candidate.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION
 
+        unrebuildable_source_keys = (
+            set(lineage_by_source) - set(extracted_by_source)
+            if rematerialize_all
+            else set()
+        )
+
         foreign_source_keys = set(lineage_by_source) - eligible_source_keys
         if foreign_source_keys:
             raise ValueError(
@@ -258,6 +292,8 @@ class IncrementalAnalysisEngine:
         missing_source_keys = eligible_source_keys - set(lineage_by_source)
         if getattr(self.state, "resync_required", False):
             candidate.lineage_facts_state = LineageFamilyStatus.STALE.value
+        elif unrebuildable_source_keys:
+            candidate.lineage_facts_state = LineageFamilyStatus.STALE.value
         elif missing_source_keys:
             candidate.lineage_facts_state = (
                 LineageFamilyStatus.STALE.value
@@ -610,6 +646,7 @@ class IncrementalAnalysisEngine:
                         source_path=syntax_source_path or "",
                         extracted_lineage_facts=extracted_lineage_facts,
                         delete=bool(getattr(delta, "is_deleted", False)),
+                        rematerialize_all=True,
                     )
             except Exception:
                 # A failed write transaction leaves no persisted commit; reload its
@@ -670,6 +707,9 @@ class IncrementalAnalysisEngine:
             # certify it fresh again.
             self.state.resync_required = True
         self.state.module_usages = candidate.module_usages
+        self.state.lineage_extracted_facts_by_source = (
+            candidate.lineage_extracted_facts_by_source
+        )
         self.state.lineage_facts_by_source = candidate.lineage_facts_by_source
         self.state.lineage_facts_state = candidate.lineage_facts_state
         self.state.lineage_facts_semantic_version = (
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 86948a6..2a10648 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -21,7 +21,10 @@ from contextor.core.analysis.state_manager import (
     validate_canonical_artifact_consumption_coverage,
 )
 from contextor.core.domain.graph import ProjectGraph
-from contextor.core.domain.lineage_facts import MaterializedLineageSourceFacts
+from contextor.core.domain.lineage_facts import (
+    ExtractedLineageSourceFacts,
+    MaterializedLineageSourceFacts,
+)
 from contextor.core.domain.module import Module
 from contextor.core.domain.refresh_plan import RefreshPlan
 from contextor.core.domain.usage_facts import ModuleUsageFacts
@@ -45,6 +48,7 @@ class CandidateState:
     syntax_diagnostics_by_path: Dict[str, Dict[str, Any]]
     syntax_diagnostics_state: str
     module_usages: Dict[str, Any]
+    lineage_extracted_facts_by_source: Dict[str, ExtractedLineageSourceFacts]
     lineage_facts_by_source: Dict[str, MaterializedLineageSourceFacts]
     lineage_facts_state: str
     lineage_facts_semantic_version: str | None
@@ -250,6 +254,9 @@ def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
         syntax_diagnostics_by_path=dict(getattr(state, "syntax_diagnostics_by_path", {}) or {}),
         syntax_diagnostics_state=getattr(state, "syntax_diagnostics_state", "not_materialized"),
         module_usages=dict(getattr(state, "module_usages", {}) or {}),
+        lineage_extracted_facts_by_source=dict(
+            getattr(state, "lineage_extracted_facts_by_source", {}) or {}
+        ),
         lineage_facts_by_source=dict(
             getattr(state, "lineage_facts_by_source", {}) or {}
         ),
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index a1fcfcd..fb9648d 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -4,7 +4,10 @@ from dataclasses import dataclass, field
 from typing import Dict, Any, Optional
 from pathlib import Path
 
-from contextor.core.domain.lineage_facts import MaterializedLineageSourceFacts
+from contextor.core.domain.lineage_facts import (
+    ExtractedLineageSourceFacts,
+    MaterializedLineageSourceFacts,
+)
 
 
 @dataclass
@@ -95,6 +98,9 @@ class RepositoryAnalysisState:
     syntax_diagnostics_state: str = "not_materialized"
     module_usages: Dict[str, Any] = field(default_factory=dict)
     module_usages_manifest: Dict[str, Dict[str, str]] = field(default_factory=dict)
+    lineage_extracted_facts_by_source: Dict[str, ExtractedLineageSourceFacts] = field(
+        default_factory=dict
+    )
     lineage_facts_by_source: Dict[str, MaterializedLineageSourceFacts] = field(default_factory=dict)
     lineage_facts_state: str = "not_materialized"
     lineage_facts_semantic_version: str | None = None
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 279fd3b..f607248 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -703,6 +703,9 @@ class ContextorFacade:
                 syntax_diagnostics_state=syntax_diagnostics_state,
                 module_usages=module_usages,
                 module_usages_manifest=module_usages_manifest,
+                lineage_extracted_facts_by_source=dict(
+                    getattr(index, "lineage_facts_by_source", {}) or {}
+                ),
                 lineage_facts_by_source=lineage_facts_by_source,
                 lineage_facts_state=lineage_facts_state,
                 lineage_facts_semantic_version=lineage_facts_semantic_version,
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 7cc6578..fa7d9b4 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -14,6 +14,7 @@ from typing import Any
 
 from contextor.core.domain.lineage_facts import (
     LINEAGE_FACTS_SEMANTIC_VERSION,
+    ExtractedLineageSourceFacts,
     LineageConfidence,
     LineageFamilyStatus,
     LineageRelation,
@@ -239,12 +240,15 @@ def _normalize_lineage_facts_state(state: Any) -> Any:
     try:
         if not hasattr(state, "lineage_facts_by_source"):
             state.lineage_facts_by_source = {}
+        if not hasattr(state, "lineage_extracted_facts_by_source"):
+            state.lineage_extracted_facts_by_source = {}
         if not hasattr(state, "lineage_facts_state"):
             state.lineage_facts_state = "not_materialized"
         if not hasattr(state, "lineage_facts_semantic_version"):
             state.lineage_facts_semantic_version = None
 
         raw_mapping = state.lineage_facts_by_source
+        raw_extracted_mapping = state.lineage_extracted_facts_by_source
         raw_family_state = state.lineage_facts_state
         raw_version = state.lineage_facts_semantic_version
 
@@ -252,6 +256,10 @@ def _normalize_lineage_facts_state(state: Any) -> Any:
             raise pickle.UnpicklingError(
                 "Lineage source mapping must be a dict."
             )
+        if not isinstance(raw_extracted_mapping, dict):
+            raise pickle.UnpicklingError(
+                "Extracted lineage source mapping must be a dict."
+            )
         if not isinstance(raw_family_state, str):
             raise pickle.UnpicklingError(
                 "Lineage family state must be a string."
@@ -278,6 +286,10 @@ def _normalize_lineage_facts_state(state: Any) -> Any:
                 raise pickle.UnpicklingError(
                     "Not-materialized lineage cannot have a semantic version."
                 )
+            if raw_extracted_mapping:
+                raise pickle.UnpicklingError(
+                    "Not-materialized lineage cannot retain extracted source facts."
+                )
         elif raw_version != LINEAGE_FACTS_SEMANTIC_VERSION:
             raise pickle.UnpicklingError(
                 "Materialized lineage requires the current semantic version."
@@ -296,7 +308,24 @@ def _normalize_lineage_facts_state(state: Any) -> Any:
                 )
             normalized[source_key] = rebuilt
 
+        extracted_normalized: dict[str, ExtractedLineageSourceFacts] = {}
+        for source_key, extracted in raw_extracted_mapping.items():
+            if not isinstance(source_key, str) or not source_key:
+                raise pickle.UnpicklingError(
+                    "Extracted lineage source key must be a non-empty string."
+                )
+            if not isinstance(extracted, ExtractedLineageSourceFacts):
+                raise pickle.UnpicklingError(
+                    "Invalid extracted lineage source facts."
+                )
+            if extracted.source_key != source_key:
+                raise pickle.UnpicklingError(
+                    "Extracted lineage mapping key does not match source_key."
+                )
+            extracted_normalized[source_key] = extracted
+
         state.lineage_facts_by_source = normalized
+        state.lineage_extracted_facts_by_source = extracted_normalized
         state.lineage_facts_state = family_status.value
         state.lineage_facts_semantic_version = raw_version
         return state
diff --git a/tests/test_full_analysis_lineage_materialization.py b/tests/test_full_analysis_lineage_materialization.py
index 5d84ec3..e3d8985 100644
--- a/tests/test_full_analysis_lineage_materialization.py
+++ b/tests/test_full_analysis_lineage_materialization.py
@@ -183,6 +183,7 @@ def test_real_full_analysis_installs_current_lineage_without_second_extraction(t
     state = captured_states[0]
     assert state.lineage_facts_state == "fresh"
     assert state.lineage_facts_semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
+    assert set(state.lineage_extracted_facts_by_source) == {"consumer.py", "provider.py"}
     assert set(state.lineage_facts_by_source) == {"consumer.py", "provider.py"}
     assert all(
         source_key == source_slice.manifest.source_key
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index 2991b56..b804803 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -14,6 +14,7 @@ import pytest
 
 from contextor.core.analysis.incremental.engine import IncrementalAnalysisEngine
 from contextor.core.analysis.incremental.plan_executor import _prepare_candidate_state
+from contextor.core.api.facade import _materialize_full_analysis_lineage
 from contextor.core.analysis.lineage_extraction import extract_lineage_source_facts
 from contextor.core.analysis.lineage_materialization import (
     LineageResolutionContext,
@@ -448,6 +449,69 @@ class _LineageRegistry:
             artifact_paths.setdefault(name, f"A:{name}")
 
 
+class _LifecycleRegistry(_LineageRegistry):
+    """Small transactional registry model with explicit active generations."""
+
+    def __init__(self, module_ids, artifact_ids):
+        super().__init__(module_ids, artifact_ids)
+        self._ids_by_name = {
+            **dict(module_ids),
+            **dict(artifact_ids),
+        }
+
+    def sync_with_workspace(self, modules, artifacts):
+        self._state["module_registry"]["path_to_id"] = {
+            name: self._ids_by_name[name]
+            for name in sorted(modules)
+            if name in self._ids_by_name
+        }
+        self._state["module_registry"]["id_to_path"] = {
+            owner_id: name
+            for name, owner_id in self._state["module_registry"]["path_to_id"].items()
+        }
+        self._state["artifact_registry"]["path_to_id"] = {
+            name: self._ids_by_name[name]
+            for name in sorted(artifacts)
+            if name in self._ids_by_name
+        }
+        self._state["artifact_registry"]["id_to_path"] = {
+            owner_id: name
+            for name, owner_id in self._state["artifact_registry"]["path_to_id"].items()
+        }
+
+
+def _cross_source_facts():
+    provider_source = "def target():\n    return 1\n__all__ = ['target']\n"
+    consumer_source = (
+        "from provider import target as exported\n"
+        "__all__ = ['exported']\n"
+        "value = exported()\n"
+    )
+    return {
+        "provider.py": _extracted("provider.py", provider_source),
+        "consumer.py": _extracted("consumer.py", consumer_source),
+    }
+
+
+def _lineage_state_for_facts(facts, registry, modules, artifacts):
+    index = SimpleNamespace(
+        modules=modules,
+        lineage_facts_by_source=facts,
+        skipped=[],
+    )
+    materialized, family_state, semantic_version = _materialize_full_analysis_lineage(
+        index, registry, modules, artifacts
+    )
+    return RepositoryAnalysisState(
+        modules=modules,
+        artifacts=artifacts,
+        lineage_extracted_facts_by_source=dict(facts),
+        lineage_facts_by_source=materialized,
+        lineage_facts_state=family_state,
+        lineage_facts_semantic_version=semantic_version,
+    )
+
+
 def _module(name: str) -> Module:
     return Module(
         module_id=name,
@@ -767,6 +831,291 @@ def test_identity_sync_materializes_against_new_ids_and_rolls_back_on_failure(
     assert failed_acknowledged == []
     assert "pkg" not in failing_registry._state["module_registry"]["path_to_id"]
 
+
+def test_identity_sync_owner_deletion_matches_fresh_full_materialization_without_reextracting_untouched_consumer(
+    tmp_path,
+    monkeypatch,
+):
+    facts = _cross_source_facts()
+    modules = {name: _module(name) for name in ("provider", "consumer")}
+    artifacts = {
+        "provider": {"own_symbols": {"target"}},
+        "consumer": {"own_symbols": set()},
+    }
+    registry = _LifecycleRegistry(
+        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
+        {"provider::target": "A:provider/1"},
+    )
+    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
+    old_consumer_facts = state.lineage_extracted_facts_by_source["consumer.py"]
+    candidate = _prepare_candidate_state(state)
+    candidate.modules = {"consumer": modules["consumer"]}
+    candidate.artifacts = {"consumer": artifacts["consumer"]}
+    outcome = SimpleNamespace(
+        identity_sync_required=True,
+        candidate_state=candidate,
+        affected_modules=set(),
+        blast_radius_complete=True,
+        execution_trace={},
+        all_modules={"consumer"},
+        current_artifacts=set(),
+    )
+    monkeypatch.setattr(
+        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
+        lambda **_kwargs: outcome,
+    )
+    monkeypatch.setattr(
+        "contextor.core.analysis.lineage_extraction.extract_lineage_source_facts",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(
+            AssertionError("untouched consumer was re-extracted")
+        ),
+    )
+    engine, _ = _lineage_engine(state, registry, tmp_path)
+
+    engine._apply_delta_and_commit(
+        str(tmp_path / "provider.py"),
+        SimpleNamespace(is_deleted=True),
+        None,
+        SimpleNamespace(),
+        [],
+        {},
+        None,
+        syntax_source_path="provider.py",
+    )
+
+    full_registry = _LifecycleRegistry(
+        {"consumer": "M:consumer/1"},
+        {},
+    )
+    expected, expected_state, expected_version = _materialize_full_analysis_lineage(
+        SimpleNamespace(
+            modules={"consumer": modules["consumer"]},
+            lineage_facts_by_source={"consumer.py": facts["consumer.py"]},
+            skipped=[],
+        ),
+        full_registry,
+        {"consumer": modules["consumer"]},
+        {"consumer": artifacts["consumer"]},
+    )
+
+    assert state.lineage_facts_state == expected_state == "fresh"
+    assert state.lineage_facts_semantic_version == expected_version
+    assert set(state.lineage_facts_by_source) == {"consumer.py"}
+    assert state.lineage_facts_by_source == expected
+    assert state.lineage_extracted_facts_by_source == {
+        "consumer.py": old_consumer_facts
+    }
+    exposed = state.lineage_facts_by_source["consumer.py"].surfaces[0].exposed
+    assert isinstance(exposed, MaterializedSymbolicRef)
+    assert exposed.module_name == "provider"
+    assert not any(
+        isinstance(endpoint, SemanticEndpoint)
+        and endpoint.owner_id == "A:provider/1"
+        for source_slice in state.lineage_facts_by_source.values()
+        for fact in (*source_slice.flows, *source_slice.surfaces)
+        for endpoint in (getattr(fact, "source", None), getattr(fact, "target", None), getattr(fact, "exposed", None))
+    )
+
+
+def test_identity_sync_owner_introduction_promotes_retained_untouched_consumer_to_full_parity(
+    tmp_path,
+    monkeypatch,
+):
+    facts = _cross_source_facts()
+    consumer_modules = {"consumer": _module("consumer")}
+    consumer_artifacts = {"consumer": {"own_symbols": set()}}
+    registry = _LifecycleRegistry({"consumer": "M:consumer/1"}, {})
+    registry._ids_by_name.update(
+        {"provider": "M:provider/1", "provider::target": "A:provider/1"}
+    )
+    state = _lineage_state_for_facts(
+        {"consumer.py": facts["consumer.py"]},
+        registry,
+        consumer_modules,
+        consumer_artifacts,
+    )
+    candidate = _prepare_candidate_state(state)
+    modules = {name: _module(name) for name in ("provider", "consumer")}
+    artifacts = {
+        "provider": {"own_symbols": {"target"}},
+        "consumer": {"own_symbols": set()},
+    }
+    candidate.modules = modules
+    candidate.artifacts = artifacts
+    outcome = SimpleNamespace(
+        identity_sync_required=True,
+        candidate_state=candidate,
+        affected_modules=set(),
+        blast_radius_complete=True,
+        execution_trace={},
+        all_modules=set(modules),
+        current_artifacts={"provider::target"},
+    )
+    monkeypatch.setattr(
+        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
+        lambda **_kwargs: outcome,
+    )
+    monkeypatch.setattr(
+        "contextor.core.analysis.lineage_extraction.extract_lineage_source_facts",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(
+            AssertionError("untouched consumer was re-extracted")
+        ),
+    )
+    engine, _ = _lineage_engine(state, registry, tmp_path)
+
+    engine._apply_delta_and_commit(
+        str(tmp_path / "provider.py"),
+        SimpleNamespace(is_deleted=False),
+        None,
+        SimpleNamespace(),
+        [],
+        {},
+        None,
+        extracted_lineage_facts=facts["provider.py"],
+        syntax_source_path="provider.py",
+    )
+
+    expected_registry = _LifecycleRegistry(
+        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
+        {"provider::target": "A:provider/1"},
+    )
+    expected, expected_state, expected_version = _materialize_full_analysis_lineage(
+        SimpleNamespace(
+            modules=modules,
+            lineage_facts_by_source=facts,
+            skipped=[],
+        ),
+        expected_registry,
+        modules,
+        artifacts,
+    )
+
+    assert state.lineage_facts_state == expected_state == "fresh"
+    assert state.lineage_facts_semantic_version == expected_version
+    assert set(state.lineage_facts_by_source) == {"provider.py", "consumer.py"}
+    assert state.lineage_facts_by_source == expected
+    assert state.lineage_facts_by_source["consumer.py"].surfaces[0].exposed == SemanticEndpoint(
+        "A:provider/1"
+    )
+
+
+def test_identity_sync_generation_change_rematerializes_against_current_owner_id(
+    tmp_path,
+    monkeypatch,
+):
+    facts = _cross_source_facts()
+    modules = {name: _module(name) for name in ("provider", "consumer")}
+    artifacts = {
+        "provider": {"own_symbols": {"target"}},
+        "consumer": {"own_symbols": set()},
+    }
+    registry = _LifecycleRegistry(
+        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
+        {"provider::target": "A:provider/1"},
+    )
+    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
+    registry._ids_by_name["provider::target"] = "A:provider/2"
+    candidate = _prepare_candidate_state(state)
+    outcome = SimpleNamespace(
+        identity_sync_required=True,
+        candidate_state=candidate,
+        affected_modules=set(),
+        blast_radius_complete=True,
+        execution_trace={},
+        all_modules=set(modules),
+        current_artifacts={"provider::target"},
+    )
+    monkeypatch.setattr(
+        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
+        lambda **_kwargs: outcome,
+    )
+    engine, _ = _lineage_engine(state, registry, tmp_path)
+
+    engine._apply_delta_and_commit(
+        str(tmp_path / "provider.py"),
+        SimpleNamespace(is_deleted=False),
+        None,
+        SimpleNamespace(),
+        [],
+        {},
+        None,
+        extracted_lineage_facts=facts["provider.py"],
+        syntax_source_path="provider.py",
+    )
+
+    consumer_surface = state.lineage_facts_by_source["consumer.py"].surfaces[0]
+    assert consumer_surface.exposed == SemanticEndpoint("A:provider/2")
+    assert consumer_surface.exposed != SemanticEndpoint("A:provider/1")
+    assert registry._state["artifact_registry"]["path_to_id"]["provider::target"] == "A:provider/2"
+
+
+def test_identity_sync_revalidation_failure_rolls_back_registry_and_canonical_state(
+    tmp_path,
+    monkeypatch,
+):
+    facts = _cross_source_facts()
+    modules = {name: _module(name) for name in ("provider", "consumer")}
+    artifacts = {
+        "provider": {"own_symbols": {"target"}},
+        "consumer": {"own_symbols": set()},
+    }
+    registry = _LifecycleRegistry(
+        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
+        {"provider::target": "A:provider/1"},
+    )
+    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
+    original_modules = dict(state.modules)
+    original_artifacts = dict(state.artifacts)
+    original_lineage = dict(state.lineage_facts_by_source)
+    original_extracted = dict(state.lineage_extracted_facts_by_source)
+    candidate = _prepare_candidate_state(state)
+    candidate.modules = {"consumer": modules["consumer"]}
+    candidate.artifacts = {"consumer": artifacts["consumer"]}
+    outcome = SimpleNamespace(
+        identity_sync_required=True,
+        candidate_state=candidate,
+        affected_modules=set(),
+        blast_radius_complete=True,
+        execution_trace={},
+        all_modules={"consumer"},
+        current_artifacts=set(),
+    )
+    monkeypatch.setattr(
+        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
+        lambda **_kwargs: outcome,
+    )
+
+    def fail_on_untouched_consumer(extracted, _resolution):
+        if extracted.source_key == "consumer.py":
+            raise ValueError("consumer rematerialization failed")
+        raise AssertionError("deleted provider should not be rematerialized")
+
+    monkeypatch.setattr(
+        "contextor.core.analysis.lineage_materialization.materialize_lineage_source_facts",
+        fail_on_untouched_consumer,
+    )
+    engine, acknowledged = _lineage_engine(state, registry, tmp_path)
+
+    with pytest.raises(ValueError, match="consumer rematerialization failed"):
+        engine._apply_delta_and_commit(
+            str(tmp_path / "provider.py"),
+            SimpleNamespace(is_deleted=True),
+            None,
+            SimpleNamespace(),
+            [],
+            {},
+            None,
+            syntax_source_path="provider.py",
+        )
+
+    assert state.modules == original_modules
+    assert state.artifacts == original_artifacts
+    assert state.lineage_facts_by_source == original_lineage
+    assert state.lineage_extracted_facts_by_source == original_extracted
+    assert registry._state["module_registry"]["path_to_id"]["provider"] == "M:provider/1"
+    assert registry._state["artifact_registry"]["path_to_id"]["provider::target"] == "A:provider/1"
+    assert acknowledged == []
+
 def test_fresh_process_hydrates_materialized_symbolic_lineage_without_analysis(
     tmp_path,
     monkeypatch,

```

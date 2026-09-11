STATUS=PASS (focused implementation gate only; Desktop/LIVE E2E remains user-owned)

IMPLEMENTATION=
- Added IncrementalAnalysisEngine._update_candidate_lineage_slice: one COW candidate lineage-slice owner for ADD/MODIFY/DELETE.
- ADD/MODIFY reuses LineageResolutionContext and materialize_lineage_source_facts with only active candidate modules/artifacts and active registry path_to_id maps. Missing active IDs fail closed; no get_module_id/get_artifact_id call is made by lineage materialization.
- The helper validates extracted source key plus materialized manifest source key/fingerprint, changes exactly one source key, rejects foreign keys, and recomputes lineage family state (stale/deferred/resource_limit/fresh) with resync_required fail-closed behavior.
- Regular ADD/MODIFY/DELETE obtains the COW candidate before registry work. Identity synchronization and lineage materialization execute in the same registry write transaction; non-sync paths use read_transaction.
- A failed write-path materialization reloads the registry through the existing read transaction before re-raising, leaving no candidate publication or FileStateManager acknowledgement.
- plan.is_empty now still installs the freshly extracted lineage slice through the existing syntax COW commit. Parse/extraction errors remove only the changed source slice, preserve unrelated slices, and mark lineage stale.
- Existing MaterializedSymbolicRef cold-start regression was preserved unchanged.

ATOMICITY_EVIDENCE=
- Canonical self.state.lineage_* fields are written only after lineage candidate materialization/validation and registry transaction success.
- Failure test proves no canonical lineage publication, no FileStateManager acknowledgement, and no uncommitted registry module identity remains visible after materialization failure.
- Candidate-map tests prove replacement/removal touches only the named source slice and retains unrelated slice object identity.

TESTS=
- .\\.venv\\Scripts\\python.exe -m pytest -q tests/test_lineage_state_lifecycle.py tests/test_refresh_plan_execution.py tests/test_no_double_parse.py
  RESULT=33 passed in 25.10s
- .\\.venv\\Scripts\\python.exe -m py_compile contextor/core/analysis/incremental/engine.py tests/test_lineage_state_lifecycle.py
  RESULT=exit 0
- git diff --check -- contextor/core/analysis/incremental/engine.py tests/test_lineage_state_lifecycle.py
  RESULT=exit 0

USER_E2E_REQUIRED=
Manual Desktop watcher/LIVE ADD, MODIFY, DELETE, and rename-as-delete-plus-add certification remains required. No analyze_project, Desktop, LIVE restart, or update_file command was run.

FILES_CHANGED=
- contextor/core/analysis/incremental/engine.py
- tests/test_lineage_state_lifecycle.py
walkthrough.md is the authorized report and is excluded. contextor/core/live_state/store.py was pre-existing unrelated worktree state and was not modified.

ACTUAL_DIFF=
- Engine: source-local incremental lineage materialization, COW state recomputation, transaction ordering/rollback reload, no-op-plan install, and error invalidation.
- Tests: COW modify/delete preservation, no-op install, failure invalidation/recovery, resource limit, key/fingerprint/identity fail-closed behavior, write-transaction rollback, and preservation of the existing cold-start symbolic-reference regression.

COMPLETE_RAW_UNIFIED_FULL_DIFF=
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index b2ddd88..540d818 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -112,9 +112,21 @@ class IncrementalAnalysisEngine:
         mark_parse_error: tuple[str | None, int | None, int | None] | None = None,
         clear_parse_module: str | None = None,
         degrade_syntax_family: bool = False,
+        extracted_lineage_facts: Any | None = None,
+        invalidate_lineage: bool = False,
     ) -> None:
-        """Commit syntax and parse-freshness changes through a COW candidate."""
+        """Commit syntax, parse-freshness, and lineage changes through one COW candidate."""
         candidate = _prepare_candidate_state(self.state)
+        if invalidate_lineage:
+            candidate.lineage_facts_by_source.pop(source_path, None)
+            candidate.lineage_facts_state = "stale"
+        elif extracted_lineage_facts is not None:
+            with self.registry.read_transaction():
+                self._update_candidate_lineage_slice(
+                    candidate,
+                    source_path=source_path,
+                    extracted_lineage_facts=extracted_lineage_facts,
+                )
         if remove_syntax_fact:
             candidate.syntax_diagnostics_by_path.pop(source_path, None)
         elif syntax_fact is not None:
@@ -135,6 +147,130 @@ class IncrementalAnalysisEngine:
         self.state.syntax_diagnostics_by_path = candidate.syntax_diagnostics_by_path
         self.state.syntax_diagnostics_state = candidate.syntax_diagnostics_state
         self.state.module_parse_freshness = candidate.module_parse_freshness
+        self.state.lineage_facts_by_source = candidate.lineage_facts_by_source
+        self.state.lineage_facts_state = candidate.lineage_facts_state
+        self.state.lineage_facts_semantic_version = (
+            candidate.lineage_facts_semantic_version
+        )
+
+    def _update_candidate_lineage_slice(
+        self,
+        candidate: Any,
+        *,
+        source_path: str,
+        extracted_lineage_facts: Any | None = None,
+        delete: bool = False,
+    ) -> None:
+        """Install or remove exactly one source-keyed lineage slice on a COW candidate."""
+        from contextor.core.analysis.lineage_materialization import (
+            LineageResolutionContext,
+            materialize_lineage_source_facts,
+        )
+        from contextor.core.domain.lineage_facts import (
+            LINEAGE_FACTS_SEMANTIC_VERSION,
+            LineageFamilyStatus,
+        )
+        from contextor.core.reporting_layer.artifact_usage_report import (
+            collect_qualified_artifact_identities,
+        )
+
+        eligible_source_keys = {
+            Path(str(module.path)).as_posix()
+            for module in candidate.modules.values()
+        }
+        lineage_by_source = candidate.lineage_facts_by_source
+
+        if delete:
+            lineage_by_source.pop(source_path, None)
+            candidate.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION
+        else:
+            if extracted_lineage_facts is None:
+                raise ValueError("Successful incremental lineage update requires extracted facts.")
+            if extracted_lineage_facts.source_key != source_path:
+                raise ValueError("Extracted lineage source key does not match incremental source.")
+            if source_path not in eligible_source_keys:
+                raise ValueError("Incremental lineage source is outside the active candidate.")
+
+            active_module_names = set(candidate.modules)
+            active_artifact_names = collect_qualified_artifact_identities(
+                candidate.artifacts
+            )
+            module_registry = self.registry._state["module_registry"]["path_to_id"]
+            artifact_registry = self.registry._state["artifact_registry"]["path_to_id"]
+            active_module_ids = {
+                name: module_registry[name]
+                for name in sorted(active_module_names)
+                if name in module_registry
+            }
+            active_artifact_ids = {
+                name: artifact_registry[name]
+                for name in sorted(active_artifact_names)
+                if name in artifact_registry
+            }
+            missing_module_ids = active_module_names - set(active_module_ids)
+            missing_artifact_ids = active_artifact_names - set(active_artifact_ids)
+            if missing_module_ids or missing_artifact_ids:
+                raise ValueError(
+                    "Finalized identity registry is missing active lineage owners: "
+                    f"modules={sorted(missing_module_ids)!r}, "
+                    f"artifacts={sorted(missing_artifact_ids)!r}"
+                )
+
+            resolution = LineageResolutionContext(
+                active_module_ids=active_module_ids,
+                active_artifact_ids=active_artifact_ids,
+                active_owner_ids=frozenset(
+                    (*active_module_ids.values(), *active_artifact_ids.values())
+                ),
+                interface_descriptors={},
+            )
+            materialized = materialize_lineage_source_facts(
+                extracted_lineage_facts,
+                resolution,
+            )
+            if (
+                materialized.manifest.source_key != extracted_lineage_facts.source_key
+                or materialized.manifest.source_fingerprint
+                != extracted_lineage_facts.source_fingerprint
+            ):
+                raise ValueError(
+                    "Materialized lineage manifest does not match extracted source."
+                )
+            lineage_by_source[source_path] = materialized
+            candidate.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION
+
+        foreign_source_keys = set(lineage_by_source) - eligible_source_keys
+        if foreign_source_keys:
+            raise ValueError(
+                "Materialized lineage contains sources outside the active candidate: "
+                f"{sorted(foreign_source_keys)!r}"
+            )
+        missing_source_keys = eligible_source_keys - set(lineage_by_source)
+        if getattr(self.state, "resync_required", False):
+            candidate.lineage_facts_state = LineageFamilyStatus.STALE.value
+        elif missing_source_keys:
+            candidate.lineage_facts_state = (
+                LineageFamilyStatus.STALE.value
+                if candidate.lineage_facts_state == LineageFamilyStatus.STALE.value
+                else LineageFamilyStatus.DEFERRED.value
+            )
+        elif any(
+            item.manifest.status is LineageFamilyStatus.STALE
+            for item in lineage_by_source.values()
+        ):
+            candidate.lineage_facts_state = LineageFamilyStatus.STALE.value
+        elif any(
+            item.manifest.status is LineageFamilyStatus.DEFERRED
+            for item in lineage_by_source.values()
+        ):
+            candidate.lineage_facts_state = LineageFamilyStatus.DEFERRED.value
+        elif any(
+            item.manifest.status is LineageFamilyStatus.RESOURCE_LIMIT
+            for item in lineage_by_source.values()
+        ):
+            candidate.lineage_facts_state = LineageFamilyStatus.RESOURCE_LIMIT.value
+        else:
+            candidate.lineage_facts_state = LineageFamilyStatus.FRESH.value

     def update_file(self, file_path: str) -> IncrementalUpdateResult:
         """
@@ -265,6 +401,7 @@ class IncrementalAnalysisEngine:
                     ),
                     clear_parse_module=module_path,
                     degrade_syntax_family=prep.error_status != "SYNTAX_ERROR",
+                    invalidate_lineage=True,
                 )
                 return IncrementalUpdateResult(
                     status=prep.error_status,
@@ -305,6 +442,7 @@ class IncrementalAnalysisEngine:
                     source_path=source_path,
                     syntax_fact=checked_and_none,
                     clear_parse_module=module_path,
+                    extracted_lineage_facts=prep.extracted_lineage_facts,
                 )
                 self.state_manager.update_state(file_path)
                 return IncrementalUpdateResult(
@@ -335,6 +473,7 @@ class IncrementalAnalysisEngine:
             affected_set, blast_radius_complete, execution_trace = self._apply_delta_and_commit(
                 file_path, delta, usage_delta, plan, new_imports, new_artifacts, new_usage,
                 new_collision_facts=new_collision_facts,
+                extracted_lineage_facts=prep.extracted_lineage_facts,
                 syntax_source_path=source_path,
                 syntax_fact=checked_and_none,
                 clear_parse_module=module_path,
@@ -423,6 +562,7 @@ class IncrementalAnalysisEngine:
         mod_artifacts: dict,
         new_usage: Any,
         new_collision_facts: Optional[List[Dict[str, Any]]] = None,
+        extracted_lineage_facts: Any | None = None,
         syntax_source_path: str | None = None,
         syntax_fact: Dict[str, Any] | None = None,
         remove_syntax_fact: bool = False,
@@ -445,13 +585,40 @@ class IncrementalAnalysisEngine:
             new_collision_facts=new_collision_facts,
         )

-        # Persistent Identity Registry Commit
+        candidate = outcome.candidate_state
+
+        # Persistent identity sync and lineage materialization share one registry view.
         if outcome.identity_sync_required:
-            with self.registry.transaction():
-                self.registry.sync_with_workspace(outcome.all_modules, outcome.current_artifacts)
+            try:
+                with self.registry.transaction():
+                    self.registry.sync_with_workspace(
+                        outcome.all_modules,
+                        outcome.current_artifacts,
+                    )
+                    self._update_candidate_lineage_slice(
+                        candidate,
+                        source_path=syntax_source_path or "",
+                        extracted_lineage_facts=extracted_lineage_facts,
+                        delete=bool(getattr(delta, "is_deleted", False)),
+                    )
+            except Exception:
+                # A failed write transaction leaves no persisted commit; reload its
+                # in-memory view before exposing the registry again.
+                with self.registry.read_transaction():
+                    pass
+                raise
+        elif extracted_lineage_facts is not None or bool(
+            getattr(delta, "is_deleted", False)
+        ):
+            with self.registry.read_transaction():
+                self._update_candidate_lineage_slice(
+                    candidate,
+                    source_path=syntax_source_path or "",
+                    extracted_lineage_facts=extracted_lineage_facts,
+                    delete=bool(getattr(delta, "is_deleted", False)),
+                )

         # Canonical State Publication
-        candidate = outcome.candidate_state
         if remove_syntax_fact and syntax_source_path is not None:
             candidate.syntax_diagnostics_by_path.pop(syntax_source_path, None)
         elif syntax_fact is not None and syntax_source_path is not None:
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index 2b59120..89b8b26 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -1,3 +1,12 @@
+import ast
+import hashlib
+import json
+import os
+import subprocess
+import sys
+from contextlib import contextmanager
+from copy import deepcopy
+from dataclasses import replace
 from pathlib import Path
 from types import SimpleNamespace

@@ -5,9 +14,15 @@ import pytest

 from contextor.core.analysis.incremental.engine import IncrementalAnalysisEngine
 from contextor.core.analysis.incremental.plan_executor import _prepare_candidate_state
+from contextor.core.analysis.lineage_extraction import extract_lineage_source_facts
+from contextor.core.analysis.lineage_materialization import (
+    LineageResolutionContext,
+    materialize_lineage_source_facts,
+)
 from contextor.core.analysis.state_manager import RepositoryAnalysisState
 from contextor.core.domain.graph import ProjectGraph
 from contextor.core.domain.lineage_facts import (
+    ExtractedSymbolicKind,
     LINEAGE_FACTS_SEMANTIC_VERSION,
     LineageConfidence,
     LineageFamilyStatus,
@@ -16,6 +31,7 @@ from contextor.core.domain.lineage_facts import (
     MaterializedFlowFact,
     MaterializedLineageSourceFacts,
     MaterializedOccurrenceRef,
+    MaterializedSymbolicRef,
     MaterializedSurfaceFact,
     ProviderRef,
     ResolutionKind,
@@ -398,3 +414,401 @@ def test_incremental_commit_publishes_lineage_candidate_fields(
     assert state.lineage_facts_by_source == {"pkg.py": source_slice}
     assert state.lineage_facts_state == "fresh"
     assert state.lineage_facts_semantic_version == "1"
+
+
+class _LineageRegistry:
+    def __init__(self, module_ids=None, artifact_ids=None):
+        self._persisted = {
+            "module_registry": {"path_to_id": dict(module_ids or {})},
+            "artifact_registry": {"path_to_id": dict(artifact_ids or {})},
+        }
+        self._state = deepcopy(self._persisted)
+
+    @contextmanager
+    def transaction(self):
+        self._state = deepcopy(self._persisted)
+        try:
+            yield
+        except Exception:
+            raise
+        else:
+            self._persisted = deepcopy(self._state)
+
+    @contextmanager
+    def read_transaction(self):
+        self._state = deepcopy(self._persisted)
+        yield
+
+    def sync_with_workspace(self, modules, artifacts):
+        module_paths = self._state["module_registry"]["path_to_id"]
+        artifact_paths = self._state["artifact_registry"]["path_to_id"]
+        for name in sorted(modules):
+            module_paths.setdefault(name, f"M:{name}")
+        for name in sorted(artifacts):
+            artifact_paths.setdefault(name, f"A:{name}")
+
+
+def _module(name: str) -> Module:
+    return Module(
+        module_id=name,
+        path=f"{name}.py",
+        absolute_path=f"/{name}.py",
+        imports=[],
+    )
+
+
+def _extracted(source_key: str, source: str = "value = 1\n"):
+    return extract_lineage_source_facts(
+        ast.parse(source),
+        source_key=source_key,
+        source_fingerprint=hashlib.sha256(source.encode("utf-8")).hexdigest(),
+    )
+
+
+def _lineage_engine(state, registry, tmp_path):
+    acknowledged = []
+    engine = object.__new__(IncrementalAnalysisEngine)
+    engine.state = state
+    engine.registry = registry
+    engine.root_path = Path(tmp_path)
+    engine.state_manager = SimpleNamespace(update_state=acknowledged.append)
+    return engine, acknowledged
+
+
+def _slice_for(source_key: str) -> MaterializedLineageSourceFacts:
+    return materialize_lineage_source_facts(
+        _extracted(source_key),
+        LineageResolutionContext({}, {}, frozenset(), {}),
+    )
+
+
+def test_incremental_lineage_modify_replaces_only_changed_candidate_slice(tmp_path):
+    old_pkg = _slice_for("pkg.py")
+    other = _slice_for("other.py")
+    state = RepositoryAnalysisState(
+        modules={"pkg": _module("pkg"), "other": _module("other")},
+        artifacts={"pkg": {"own_symbols": set()}, "other": {"own_symbols": set()}},
+        lineage_facts_by_source={"pkg.py": old_pkg, "other.py": other},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+    )
+    engine, _ = _lineage_engine(
+        state,
+        _LineageRegistry({"pkg": "M:pkg", "other": "M:other"}),
+        tmp_path,
+    )
+    candidate = _prepare_candidate_state(state)
+
+    with engine.registry.read_transaction():
+        engine._update_candidate_lineage_slice(
+            candidate,
+            source_path="pkg.py",
+            extracted_lineage_facts=_extracted("pkg.py", "changed = 2\n"),
+        )
+
+    assert candidate.lineage_facts_by_source["pkg.py"] is not old_pkg
+    assert candidate.lineage_facts_by_source["other.py"] is other
+    assert candidate.lineage_facts_state == "fresh"
+    assert candidate.lineage_facts_semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
+
+
+def test_incremental_lineage_delete_removes_only_deleted_slice(tmp_path):
+    pkg = _slice_for("pkg.py")
+    other = _slice_for("other.py")
+    state = RepositoryAnalysisState(
+        modules={"other": _module("other")},
+        artifacts={"other": {"own_symbols": set()}},
+        lineage_facts_by_source={"pkg.py": pkg, "other.py": other},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+    )
+    engine, _ = _lineage_engine(
+        state,
+        _LineageRegistry({"other": "M:other"}),
+        tmp_path,
+    )
+    candidate = _prepare_candidate_state(state)
+
+    with engine.registry.read_transaction():
+        engine._update_candidate_lineage_slice(
+            candidate,
+            source_path="pkg.py",
+            delete=True,
+        )
+
+    assert candidate.lineage_facts_by_source == {"other.py": other}
+    assert candidate.lineage_facts_state == "fresh"
+
+
+def test_lineage_only_noop_commit_replaces_slice_and_parse_error_invalidates_it(tmp_path):
+    old_pkg = _slice_for("pkg.py")
+    other = _slice_for("other.py")
+    state = RepositoryAnalysisState(
+        modules={"pkg": _module("pkg"), "other": _module("other")},
+        artifacts={"pkg": {"own_symbols": set()}, "other": {"own_symbols": set()}},
+        lineage_facts_by_source={"pkg.py": old_pkg, "other.py": other},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+    )
+    engine, acknowledged = _lineage_engine(
+        state,
+        _LineageRegistry({"pkg": "M:pkg", "other": "M:other"}),
+        tmp_path,
+    )
+
+    engine._commit_syntax_candidate(
+        source_path="pkg.py",
+        syntax_fact={"status": "checked_and_none", "errors": []},
+        extracted_lineage_facts=_extracted("pkg.py", "lineage_only = 3\n"),
+    )
+    assert state.lineage_facts_by_source["pkg.py"] is not old_pkg
+    assert state.lineage_facts_by_source["other.py"] is other
+    assert state.lineage_facts_state == "fresh"
+    assert acknowledged == []
+
+    engine._commit_syntax_candidate(
+        source_path="pkg.py",
+        mark_parse_error=("broken", 1, 1),
+        clear_parse_module="pkg",
+        invalidate_lineage=True,
+    )
+    assert "pkg.py" not in state.lineage_facts_by_source
+    assert state.lineage_facts_by_source["other.py"] is other
+    assert state.lineage_facts_state == "stale"
+    assert state.lineage_facts_semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
+
+    engine._commit_syntax_candidate(
+        source_path="pkg.py",
+        syntax_fact={"status": "checked_and_none", "errors": []},
+        extracted_lineage_facts=_extracted("pkg.py", "recovered = 4\n"),
+    )
+    assert state.lineage_facts_state == "fresh"
+    assert set(state.lineage_facts_by_source) == {"pkg.py", "other.py"}
+
+
+def test_incremental_lineage_resource_limit_and_source_key_mismatch_fail_closed(tmp_path):
+    state = RepositoryAnalysisState(
+        modules={"pkg": _module("pkg")},
+        artifacts={"pkg": {"own_symbols": set()}},
+    )
+    engine, _ = _lineage_engine(
+        state,
+        _LineageRegistry({"pkg": "M:pkg"}),
+        tmp_path,
+    )
+    limited = replace(
+        _extracted("pkg.py"),
+        status=LineageFamilyStatus.RESOURCE_LIMIT,
+        resource_limit_reason="limit",
+    )
+    candidate = _prepare_candidate_state(state)
+    with engine.registry.read_transaction():
+        engine._update_candidate_lineage_slice(
+            candidate,
+            source_path="pkg.py",
+            extracted_lineage_facts=limited,
+        )
+    assert candidate.lineage_facts_state == "resource_limit"
+
+    before = dict(candidate.lineage_facts_by_source)
+    with engine.registry.read_transaction(), pytest.raises(ValueError, match="source key"):
+        engine._update_candidate_lineage_slice(
+            candidate,
+            source_path="pkg.py",
+            extracted_lineage_facts=_extracted("wrong.py"),
+        )
+    assert candidate.lineage_facts_by_source == before
+
+
+def test_incremental_lineage_missing_identity_and_manifest_mismatch_fail_closed(
+    tmp_path,
+    monkeypatch,
+):
+    state = RepositoryAnalysisState(
+        modules={"pkg": _module("pkg")},
+        artifacts={"pkg": {"own_symbols": set()}},
+    )
+    engine, _ = _lineage_engine(state, _LineageRegistry(), tmp_path)
+    candidate = _prepare_candidate_state(state)
+    engine.registry.get_module_id = lambda *_args: (_ for _ in ()).throw(
+        AssertionError("lineage must not allocate module identities")
+    )
+    engine.registry.get_artifact_id = lambda *_args: (_ for _ in ()).throw(
+        AssertionError("lineage must not allocate artifact identities")
+    )
+    with engine.registry.read_transaction(), pytest.raises(ValueError, match="missing active"):
+        engine._update_candidate_lineage_slice(
+            candidate,
+            source_path="pkg.py",
+            extracted_lineage_facts=_extracted("pkg.py"),
+        )
+    assert candidate.lineage_facts_by_source == {}
+
+    engine.registry = _LineageRegistry({"pkg": "M:pkg"})
+    mismatched = materialize_lineage_source_facts(
+        _extracted("pkg.py", "different = 2\n"),
+        LineageResolutionContext({"pkg": "M:pkg"}, {}, frozenset({"M:pkg"}), {}),
+    )
+    monkeypatch.setattr(
+        "contextor.core.analysis.lineage_materialization.materialize_lineage_source_facts",
+        lambda *_args: mismatched,
+    )
+    with engine.registry.read_transaction(), pytest.raises(ValueError, match="manifest"):
+        engine._update_candidate_lineage_slice(
+            candidate,
+            source_path="pkg.py",
+            extracted_lineage_facts=_extracted("pkg.py"),
+        )
+    assert candidate.lineage_facts_by_source == {}
+
+
+def test_identity_sync_materializes_against_new_ids_and_rolls_back_on_failure(
+    tmp_path,
+    monkeypatch,
+):
+    state = RepositoryAnalysisState()
+    candidate = _prepare_candidate_state(state)
+    candidate.modules = {"pkg": _module("pkg")}
+    candidate.artifacts = {"pkg": {"own_symbols": {"target"}}}
+    outcome = SimpleNamespace(
+        identity_sync_required=True,
+        candidate_state=candidate,
+        affected_modules=set(),
+        blast_radius_complete=True,
+        execution_trace={},
+        all_modules={"pkg"},
+        current_artifacts={"pkg::target"},
+    )
+    monkeypatch.setattr(
+        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
+        lambda **_kwargs: outcome,
+    )
+    registry = _LineageRegistry()
+    engine, acknowledged = _lineage_engine(state, registry, tmp_path)
+    extracted = _extracted(
+        "pkg.py",
+        "def target():\n    return 1\n__all__ = ['target']\n",
+    )
+
+    engine._apply_delta_and_commit(
+        str(tmp_path / "pkg.py"),
+        SimpleNamespace(is_deleted=False),
+        None,
+        SimpleNamespace(),
+        [],
+        {},
+        None,
+        extracted_lineage_facts=extracted,
+        syntax_source_path="pkg.py",
+    )
+    assert state.lineage_facts_state == "fresh"
+    assert state.lineage_facts_by_source["pkg.py"].surfaces[0].exposed == SemanticEndpoint(
+        "A:pkg::target"
+    )
+    assert acknowledged == [str(tmp_path / "pkg.py")]
+
+    failed_state = RepositoryAnalysisState()
+    failed_candidate = _prepare_candidate_state(failed_state)
+    failed_candidate.modules = {"pkg": _module("pkg")}
+    failed_candidate.artifacts = {"pkg": {"own_symbols": set()}}
+    failed_outcome = SimpleNamespace(
+        identity_sync_required=True,
+        candidate_state=failed_candidate,
+        affected_modules=set(),
+        blast_radius_complete=True,
+        execution_trace={},
+        all_modules={"pkg"},
+        current_artifacts=set(),
+    )
+    monkeypatch.setattr(
+        "contextor.core.analysis.incremental.engine.execute_refresh_plan",
+        lambda **_kwargs: failed_outcome,
+    )
+    failing_registry = _LineageRegistry()
+    failing_engine, failed_acknowledged = _lineage_engine(
+        failed_state,
+        failing_registry,
+        tmp_path,
+    )
+    monkeypatch.setattr(
+        "contextor.core.analysis.lineage_materialization.materialize_lineage_source_facts",
+        lambda *_args: (_ for _ in ()).throw(ValueError("materialize failed")),
+    )
+
+    with pytest.raises(ValueError, match="materialize failed"):
+        failing_engine._apply_delta_and_commit(
+            str(tmp_path / "pkg.py"),
+            SimpleNamespace(is_deleted=False),
+            None,
+            SimpleNamespace(),
+            [],
+            {},
+            None,
+            extracted_lineage_facts=_extracted("pkg.py"),
+            syntax_source_path="pkg.py",
+        )
+    assert failed_state.lineage_facts_by_source == {}
+    assert failed_acknowledged == []
+    assert "pkg" not in failing_registry._state["module_registry"]["path_to_id"]
+
+def test_fresh_process_hydrates_materialized_symbolic_lineage_without_analysis(
+    tmp_path,
+    monkeypatch,
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    cache_root = tmp_path / "cache"
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+    identity, _ = ensure_repository_identity(repo)
+    cache = repo_cache_dir(repo)
+
+    source = _lineage_slice()
+    symbolic = MaterializedSymbolicRef(
+        "pkg.py", "fingerprint", ExtractedSymbolicKind.PUBLIC_TARGET, "external", "target"
+    )
+    symbolic_flow = MaterializedFlowFact(
+        "symbolic-flow", symbolic, SemanticEndpoint("A1"), LineageRelation.RETURNS,
+        SourceSpan(2, 0, 2, 1), ResolutionKind.IMPORT_EXACT,
+        LineageConfidence.CONFIRMED,
+    )
+    source = replace(
+        source,
+        manifest=replace(source.manifest, flow_count=2),
+        flows=source.flows + (symbolic_flow,),
+    )
+    state = RepositoryAnalysisState(
+        modules={"pkg": Module(module_id="pkg", path="pkg.py", absolute_path=str(repo / "missing.py"), imports=[])},
+        dependency_graph=ProjectGraph(hard_edges={"pkg": set()}, soft_edges={"pkg": set()}),
+        lineage_facts_by_source={"pkg.py": source},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+    )
+    save_snapshot(
+        state, cache, "cold-lineage", repo_id=identity.repo_id, root_path=identity.root_path
+    )
+
+    child = """
+import ast
+import json
+import contextor.core.live_state.runtime as runtime
+from contextor.core.live_state.hydration import hydrate_repository_engine
+runtime.connect = lambda _root: None
+ast.parse = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("source parse"))
+hydrated = hydrate_repository_engine(r'''%s''')
+assert hydrated is not None
+state = hydrated.engine.state
+assert state.lineage_facts_state == "fresh"
+assert state.lineage_facts_semantic_version == "1"
+assert len(state.lineage_facts_by_source) == 1
+assert any(type(flow.source).__name__ == "MaterializedSymbolicRef" for flow in state.lineage_facts_by_source["pkg.py"].flows)
+print(json.dumps({"source": hydrated.source, "lineage": len(state.lineage_facts_by_source)}))
+""" % repo
+    env = os.environ.copy()
+    env["CONTEXTOR_CACHE_DIR"] = str(cache_root)
+    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1]) + os.pathsep + env.get("PYTHONPATH", "")
+    completed = subprocess.run(
+        [sys.executable, "-c", child],
+        cwd=str(repo), env=env, text=True, capture_output=True, check=False,
+    )
+    assert completed.returncode == 0, completed.stderr
+    assert json.loads(completed.stdout) == {"source": "snapshot", "lineage": 1}

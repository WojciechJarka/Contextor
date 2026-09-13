# P0 PERF-L3a — bounded incremental phase tracing

STATUS: success

FILES_CHANGED:
- `contextor/core/analysis/incremental/engine.py`
- `tests/test_incremental_phase_trace.py`

TRACE_EVENT_ORDER_PROOF:
- Both normal and deletion paths emit `INCREMENTAL_APPLY_START` immediately before `_apply_delta_and_commit`.
- `_apply_delta_and_commit` emits `INCREMENTAL_EXECUTE_PLAN_START`, then either `INCREMENTAL_EXECUTE_PLAN_END` or `INCREMENTAL_EXECUTE_PLAN_FAIL`.
- Identity path order is registry start/end, then lineage start/end or lineage fail, then file-state start/end only after successful publication.

IDENTITY_SYNC_VISIBILITY_PROOF:
- `INCREMENTAL_EXECUTE_PLAN_END` records whether identity sync is required, executed patch families, recompute count, and graph count.
- In the identity branch, `INCREMENTAL_REGISTRY_SYNC_START` records candidate artifact count; `INCREMENTAL_REGISTRY_SYNC_END` records the bounded post-sync missing count/list before lineage begins.

MISSING_AFTER_SYNC_DIAGNOSTIC_PROOF:
- The probe computes only `outcome.current_artifacts - registry.path_to_id`; it allocates, retries, raises, and mutates nothing.
- Focused test deliberately leaves `pkg::missing` absent and proves `count=1` with `missing_after_sync=pkg::missing`, while the mutation path continues normally.

NON_IDENTITY_VISIBILITY_PROOF:
- The non-identity branch emits `INCREMENTAL_REGISTRY_SYNC_SKIP`, brackets lineage, and reports `rematerialize_all=false`; it never emits identity-sync start/end events.

FAILURE_PROPAGATION_PROOF:
- A lineage `ValueError("owner-failure")` produces `INCREMENTAL_LINEAGE_FAIL`, propagates unchanged, and prevents FileState acknowledgement. Existing registry transaction/reload semantics remain intact.

ZERO_SEMANTIC_CHANGE_PROOF:
- No scheduler, lease, registry, persistence, planner, lineage, clone, or runtime-trace-header code changed.
- Existing calls and arguments are unchanged; probes use the already best-effort `trace_event` and current mutation trace-operation context.

TESTS_RUN:
- `\.venv\Scripts\python.exe -m pytest -q tests\test_incremental_phase_trace.py tests\test_refresh_plan_execution.py tests\test_refresh_planner.py` — PASS (9 tests).
- Fallback because `tests\test_incremental.py` does not exist: `\.venv\Scripts\python.exe -m pytest -q tests\test_incremental_phase_trace.py tests\test_incremental_equivalence.py tests\test_refresh_planner.py` — PASS (15 tests).
- `\.venv\Scripts\python.exe -m py_compile contextor\core\analysis\incremental\engine.py tests\test_incremental_phase_trace.py` — PASS.
- `git diff --check -- contextor/core/analysis/incremental/engine.py tests/test_incremental_phase_trace.py` — PASS (only Git LF/CRLF warnings).

ACTUAL_DIFF:

```diff
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index bbeef57..2b3d9bc 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -1,4 +1,5 @@
 import threading
+import time
 from dataclasses import dataclass, field
 from pathlib import Path
 from typing import Optional, List, Set, Dict, Iterable, Tuple, Any
@@
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+from contextor.core.runtime_trace import trace_event
@@
+def _trace_incremental_phase(
+    event: str,
+    *,
+    started: float | None = None,
+    **fields: object,
+) -> None:
+    payload = dict(fields)
+    if started is not None:
+        payload["elapsed_ms"] = (
+            time.monotonic() - started
+        ) * 1000.0
+    trace_event("LIVE", event, **payload)
+
@@ deletion update path
+                _trace_incremental_phase(
+                    "INCREMENTAL_APPLY_START",
+                    result=(
+                        f"artifacts_added={len(delta.artifacts_added)};"
+                        f"artifacts_removed={len(delta.artifacts_removed)};"
+                        f"artifacts_changed={len(delta.artifacts_changed)};"
+                        f"patch_families={','.join(plan.patch_families)}"
+                    ),
+                )
@@ normal update path
+            _trace_incremental_phase(
+                "INCREMENTAL_APPLY_START",
+                result=(
+                    f"artifacts_added={len(delta.artifacts_added)};"
+                    f"artifacts_removed={len(delta.artifacts_removed)};"
+                    f"artifacts_changed={len(delta.artifacts_changed)};"
+                    f"patch_families={','.join(plan.patch_families)}"
+                ),
+            )
@@ _apply_delta_and_commit
-        outcome = execute_refresh_plan(...)
+        execute_started = time.monotonic()
+        _trace_incremental_phase("INCREMENTAL_EXECUTE_PLAN_START")
+        try:
+            outcome = execute_refresh_plan(
+                state=self.state, delta=delta, usage_delta=usage_delta,
+                plan=plan, new_imports=new_imports,
+                new_artifacts=mod_artifacts, new_usage=new_usage,
+                root_path=self.root_path, file_path=file_path,
+                new_collision_facts=new_collision_facts,
+            )
+        except Exception as exc:
+            _trace_incremental_phase(
+                "INCREMENTAL_EXECUTE_PLAN_FAIL", started=execute_started,
+                error=str(exc),
+            )
+            raise
+        _trace_incremental_phase(
+            "INCREMENTAL_EXECUTE_PLAN_END", started=execute_started,
+            result=(
+                f"identity_sync_required={outcome.identity_sync_required};"
+                f"patch_families={','.join(outcome.execution_trace.get('patch_families', ()))};"
+                f"recompute_count={len(outcome.execution_trace.get('recompute_modules', ()))};"
+                f"graph_count={len(outcome.execution_trace.get('graph_recomputations', ()))}"
+            ),
+        )
@@ identity branch
+                    registry_started = time.monotonic()
+                    _trace_incremental_phase(
+                        "INCREMENTAL_REGISTRY_SYNC_START",
+                        count=len(outcome.current_artifacts),
+                    )
+                    try:
+                        self.registry.sync_with_workspace(
+                            outcome.all_modules, outcome.current_artifacts,
+                        )
+                    except Exception as exc:
+                        _trace_incremental_phase(
+                            "INCREMENTAL_REGISTRY_SYNC_FAIL",
+                            started=registry_started, error=str(exc),
+                        )
+                        raise
+                    missing_after_sync = sorted(
+                        outcome.current_artifacts - set(
+                            self.registry._state["artifact_registry"]["path_to_id"]
+                        )
+                    )
+                    _trace_incremental_phase(
+                        "INCREMENTAL_REGISTRY_SYNC_END",
+                        started=registry_started, count=len(missing_after_sync),
+                        result="missing_after_sync=" + ",".join(missing_after_sync[:5]),
+                    )
+                    lineage_started = time.monotonic()
+                    _trace_incremental_phase(
+                        "INCREMENTAL_LINEAGE_START", result="rematerialize_all=true",
+                    )
+                    try:
+                        self._update_candidate_lineage_slice(
+                            candidate, source_path=syntax_source_path or "",
+                            extracted_lineage_facts=extracted_lineage_facts,
+                            delete=bool(getattr(delta, "is_deleted", False)),
+                            rematerialize_all=True,
+                        )
+                    except Exception as exc:
+                        _trace_incremental_phase(
+                            "INCREMENTAL_LINEAGE_FAIL", started=lineage_started,
+                            error=str(exc),
+                        )
+                        raise
+                    _trace_incremental_phase(
+                        "INCREMENTAL_LINEAGE_END", started=lineage_started,
+                        result="rematerialize_all=true",
+                    )
@@ non-identity lineage branch
+            _trace_incremental_phase(
+                "INCREMENTAL_REGISTRY_SYNC_SKIP",
+                result="identity_sync_required=false",
+            )
+            with self.registry.read_transaction():
+                lineage_started = time.monotonic()
+                _trace_incremental_phase(
+                    "INCREMENTAL_LINEAGE_START", result="rematerialize_all=false",
+                )
+                try:
+                    self._update_candidate_lineage_slice(
+                        candidate, source_path=syntax_source_path or "",
+                        extracted_lineage_facts=extracted_lineage_facts,
+                        delete=bool(getattr(delta, "is_deleted", False)),
+                    )
+                except Exception as exc:
+                    _trace_incremental_phase(
+                        "INCREMENTAL_LINEAGE_FAIL", started=lineage_started,
+                        error=str(exc),
+                    )
+                    raise
+                _trace_incremental_phase(
+                    "INCREMENTAL_LINEAGE_END", started=lineage_started,
+                    result="rematerialize_all=false",
+                )
@@ file-state acknowledgement
+        file_state_started = time.monotonic()
+        _trace_incremental_phase("INCREMENTAL_FILE_STATE_START")
         self.state_manager.update_state(file_path)
+        _trace_incremental_phase(
+            "INCREMENTAL_FILE_STATE_END", started=file_state_started,
+        )
diff --git a/tests/test_incremental_phase_trace.py b/tests/test_incremental_phase_trace.py
new file mode 100644
--- /dev/null
+++ b/tests/test_incremental_phase_trace.py
@@
+from contextlib import contextmanager
+from importlib import import_module
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.analysis.state_manager import FileDelta, RepositoryAnalysisState
+
+engine_module = import_module("contextor.core.analysis.incremental.engine")
+
+class FakeRegistry:
+    def __init__(self, *, omit=None):
+        self.omit = omit
+        self._state = {"artifact_registry": {"path_to_id": {}}}
+    @contextmanager
+    def transaction(self):
+        yield
+    @contextmanager
+    def read_transaction(self):
+        yield
+    def sync_with_workspace(self, _modules, artifacts):
+        for artifact in artifacts:
+            if artifact != self.omit:
+                self._state["artifact_registry"]["path_to_id"][artifact] = "A1/1"
+
+class FakeStateManager:
+    def __init__(self): self.paths = []
+    def update_state(self, path): self.paths.append(path)
+
+def _candidate():
+    return SimpleNamespace(
+        modules={}, artifacts={}, module_parse_freshness={},
+        syntax_diagnostics_by_path={}, syntax_diagnostics_state="fresh",
+        dependency_graph=None, metrics={}, topology_analytics={},
+        cached_analytics={}, dependency_matrix={}, dependency_matrix_state="deferred",
+        shared_usage_clusters=[], shared_usage_clusters_state="deferred",
+        topology_metrics_state="deferred", cached_analytics_state="deferred",
+        cycles=[], cycles_state="deferred", collision_facts={}, collisions=[],
+        collisions_state="deferred", artifact_consumption={},
+        artifact_consumption_state="stale", module_usages={},
+        lineage_facts_by_source={}, lineage_facts_state="fresh",
+        lineage_facts_semantic_version="1", lineage_owner_source_index={},
+        lineage_source_owner_index={}, lineage_query_index_state="fresh",
+        lineage_semantic_anchor_bindings_complete=True, trie=None, package_root="",
+    )
+
+def _engine(registry):
+    engine = engine_module.IncrementalAnalysisEngine.__new__(engine_module.IncrementalAnalysisEngine)
+    engine.state = RepositoryAnalysisState()
+    engine.state.resync_required = False
+    engine.registry = registry
+    engine.state_manager = FakeStateManager()
+    engine.root_path = None
+    return engine
+
+def _outcome(candidate, *, identity_sync_required, artifacts=None):
+    return SimpleNamespace(
+        candidate_state=candidate, affected_modules=set(), blast_radius_complete=False,
+        execution_trace={"patch_families": ("definitions",), "recompute_modules": (), "graph_recomputations": ()},
+        identity_sync_required=identity_sync_required, all_modules=set(),
+        current_artifacts=set() if artifacts is None else set(artifacts),
+    )
+
+def _capture(monkeypatch):
+    events = []
+    monkeypatch.setattr(engine_module, "trace_event", lambda _domain, event, **fields: events.append((event, fields)))
+    return events
+
+def _run(engine, delta, *, extracted_lineage_facts="facts"):
+    return engine._apply_delta_and_commit(
+        "target.py", delta, None, SimpleNamespace(), [], {}, None,
+        extracted_lineage_facts=extracted_lineage_facts, syntax_source_path="target.py",
+        syntax_fact={"status": "checked_and_none"}, clear_parse_module="target",
+    )
+
+def _names(events): return [event for event, _fields in events]
+
+def test_identity_sync_success_emits_order_and_no_missing_owners(monkeypatch):
+    events = _capture(monkeypatch); registry = FakeRegistry(); engine = _engine(registry); candidate = _candidate()
+    monkeypatch.setattr(engine_module, "execute_refresh_plan", lambda **_kwargs: _outcome(candidate, identity_sync_required=True, artifacts={"pkg::new"}))
+    lineage_calls = []; engine._update_candidate_lineage_slice = lambda *_args, **kwargs: lineage_calls.append(kwargs)
+    _run(engine, FileDelta(module_path="target"))
+    assert _names(events) == ["INCREMENTAL_EXECUTE_PLAN_START", "INCREMENTAL_EXECUTE_PLAN_END", "INCREMENTAL_REGISTRY_SYNC_START", "INCREMENTAL_REGISTRY_SYNC_END", "INCREMENTAL_LINEAGE_START", "INCREMENTAL_LINEAGE_END", "INCREMENTAL_FILE_STATE_START", "INCREMENTAL_FILE_STATE_END"]
+    assert events[3][1]["count"] == 0
+    assert lineage_calls == [{"source_path": "target.py", "extracted_lineage_facts": "facts", "delete": False, "rematerialize_all": True}]
+
+def test_identity_sync_lineage_failure_propagates_without_file_state(monkeypatch):
+    events = _capture(monkeypatch); engine = _engine(FakeRegistry()); candidate = _candidate()
+    monkeypatch.setattr(engine_module, "execute_refresh_plan", lambda **_kwargs: _outcome(candidate, identity_sync_required=True, artifacts={"pkg::new"}))
+    def fail_lineage(*_args, **_kwargs): raise ValueError("owner-failure")
+    engine._update_candidate_lineage_slice = fail_lineage
+    with pytest.raises(ValueError, match="owner-failure"): _run(engine, FileDelta(module_path="target"))
+    assert _names(events) == ["INCREMENTAL_EXECUTE_PLAN_START", "INCREMENTAL_EXECUTE_PLAN_END", "INCREMENTAL_REGISTRY_SYNC_START", "INCREMENTAL_REGISTRY_SYNC_END", "INCREMENTAL_LINEAGE_START", "INCREMENTAL_LINEAGE_FAIL"]
+    assert events[-1][1]["error"] == "owner-failure"
+    assert engine.state_manager.paths == []
+
+def test_non_identity_path_emits_skip_and_default_lineage_scope(monkeypatch):
+    events = _capture(monkeypatch); engine = _engine(FakeRegistry()); candidate = _candidate()
+    monkeypatch.setattr(engine_module, "execute_refresh_plan", lambda **_kwargs: _outcome(candidate, identity_sync_required=False))
+    lineage_calls = []; engine._update_candidate_lineage_slice = lambda *_args, **kwargs: lineage_calls.append(kwargs)
+    _run(engine, FileDelta(module_path="target"))
+    names = _names(events)
+    assert "INCREMENTAL_REGISTRY_SYNC_SKIP" in names
+    assert "INCREMENTAL_REGISTRY_SYNC_START" not in names and "INCREMENTAL_REGISTRY_SYNC_END" not in names
+    assert lineage_calls == [{"source_path": "target.py", "extracted_lineage_facts": "facts", "delete": False}]
+    assert names[-2:] == ["INCREMENTAL_FILE_STATE_START", "INCREMENTAL_FILE_STATE_END"]
+
+def test_registry_diagnostic_gap_is_observed_without_repair_or_raise(monkeypatch):
+    events = _capture(monkeypatch); missing = "pkg::missing"; engine = _engine(FakeRegistry(omit=missing)); candidate = _candidate()
+    monkeypatch.setattr(engine_module, "execute_refresh_plan", lambda **_kwargs: _outcome(candidate, identity_sync_required=True, artifacts={missing}))
+    engine._update_candidate_lineage_slice = lambda *_args, **_kwargs: None
+    _run(engine, FileDelta(module_path="target"))
+    registry_end = next(fields for event, fields in events if event == "INCREMENTAL_REGISTRY_SYNC_END")
+    assert registry_end["count"] == 1
+    assert registry_end["result"] == "missing_after_sync=pkg::missing"
+    assert missing not in engine.registry._state["artifact_registry"]["path_to_id"]
```

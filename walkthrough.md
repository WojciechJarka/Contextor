CANONICAL_QUERY_OWNER=RepositoryAnalysisState.syntax_diagnostics_by_path keyed by canonical repo-relative Python path; syntax_diagnostics_state gates all MCP projections

STATE_DIAGNOSTICS_SUMMARY=PASS; diagnostics_summary_for_state counts checked_with_errors facts only when syntax_diagnostics_state=fresh, returns count=0 for fresh all-clear, and returns count=null with explicit not_materialized/deferred/stale/unavailable availability otherwise; completed-job skipped_python_files remains historical and separate

VALID_FILE_PROJECTION=PASS; get_file_edit_context exposes syntax_diagnostics.status=checked_and_none, availability=fresh, materialized=true, errors=[], total=0, truncated=false

SYNTAX_ERROR_PROJECTION=PASS; get_file_edit_context exposes checked_with_errors with bounded structured errors containing message, line_number, column_number, total, and truncated

STALE_STRUCTURAL_BEHAVIOR=PASS; module_truth_unavailable remains fail-closed and carries current syntax_diagnostics projection without promoting stale structural facts

NOT_MATERIALIZED_BEHAVIOR=PASS; explicit availability=not_materialized, materialized=false, errors=null

DEFERRED_BEHAVIOR=PASS; explicit availability=deferred, materialized=false, errors=null

INVALID_NEW_FILE_BEHAVIOR=UNCHANGED; existing target-resolution contract remains module/catalog based; no module identity is invented and the limitation is documented

COMPACT_FULL_FIELDS_BOUNDING=PASS; syntax diagnostics obey compact=true three-item bound, compact=false max_items bound, total/truncated metadata, and top-level fields projection

QUERY_TIME_SOURCE_READS_ADDED=0
QUERY_TIME_AST_PARSES_ADDED=0
PUBLIC_CONTRACT_CHANGED=YES; new top-level syntax_diagnostics projection on get_file_edit_context success and structural fail-closed responses
DOCS_UPDATED=contextor/mcp/docs/get_file_edit_context.json
GET_ANALYSIS_STATUS_DOCS_CHANGED=NO; existing wording already distinguishes historical analysis_coverage/skipped_python_files from current state
TESTS=PASS; focused diagnostics/projection/docs-contract runs: 50 passed (diagnostics + compact/docs contracts), then 37 passed (diagnostics + projection + architecture/docs contracts); one existing AuthlibDeprecationWarning; git diff --check=PASS
MCP_RESTART_REQUIRED=YES
LIVE_RUNTIME_RESTART_REQUIRED=NO
RUNTIME_CERTIFICATION_PENDING=YES

FILES_CHANGED=
- contextor/mcp/diagnostics.py
- contextor/mcp/tools/get_file_edit_context.py
- contextor/mcp/docs/get_file_edit_context.json
- tests/test_mcp_diagnostics.py
- tests/mcp/tools/test_get_file_edit_context_syntax.py

COMPLETE_RAW_UNIFIED_DIFFS=
diff --git a/contextor/mcp/diagnostics.py b/contextor/mcp/diagnostics.py
index 00ccde0..ec68eed 100644
--- a/contextor/mcp/diagnostics.py
+++ b/contextor/mcp/diagnostics.py
@@ -8,6 +8,7 @@ from typing import Any

 from contextor.mcp import runtime as mcp_runtime
 from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES, guard_large_output
+from contextor.core.analysis.state_manager import canonical_python_source_path


 def _availability(state: Any, family: str, values: Any) -> str:
@@ -40,8 +41,20 @@ def diagnostics_summary_for_state(state: Any) -> dict[str, Any]:
             },
         }

-    syntax_values = None
-    syntax_availability = "unavailable"
+    syntax_state = getattr(state, "syntax_diagnostics_state", None)
+    syntax_facts = getattr(state, "syntax_diagnostics_by_path", None)
+    if syntax_state == "fresh" and isinstance(syntax_facts, dict):
+        syntax_values = sum(
+            isinstance(fact, dict) and fact.get("status") == "checked_with_errors"
+            for fact in syntax_facts.values()
+        )
+        syntax_availability = "fresh"
+    elif syntax_state in {"not_materialized", "deferred", "stale", "unavailable"}:
+        syntax_values = None
+        syntax_availability = syntax_state
+    else:
+        syntax_values = None
+        syntax_availability = "unavailable"
     collisions = getattr(state, "collisions", None)
     cycles = getattr(state, "cycles", None)
     collision_availability = _availability(state, "collisions", collisions)
@@ -76,6 +89,75 @@ def diagnostics_summary_for_state(state: Any) -> dict[str, Any]:
     }


+def syntax_diagnostics_for_path(
+    state: Any,
+    source_path: str,
+    *,
+    max_items: int | None = 30,
+    compact: bool = True,
+) -> dict[str, Any]:
+    """Project one canonical syntax fact without reading or parsing source."""
+    canonical_path = canonical_python_source_path(source_path)
+    if canonical_path is None:
+        return {
+            "status": "unavailable",
+            "availability": "unavailable",
+            "materialized": False,
+            "errors": None,
+        }
+
+    family_state = getattr(state, "syntax_diagnostics_state", None)
+    facts = getattr(state, "syntax_diagnostics_by_path", None)
+    if family_state != "fresh" or not isinstance(facts, dict):
+        return {
+            "status": "unavailable",
+            "availability": family_state if family_state in {"not_materialized", "deferred", "stale", "unavailable"} else "unavailable",
+            "materialized": False,
+            "source_path": canonical_path,
+            "errors": None,
+        }
+
+    fact = facts.get(canonical_path)
+    if not isinstance(fact, dict) or fact.get("status") not in {"checked_and_none", "checked_with_errors"}:
+        return {
+            "status": "unavailable",
+            "availability": "unavailable",
+            "materialized": False,
+            "source_path": canonical_path,
+            "errors": None,
+        }
+
+    status = fact["status"]
+    if status == "checked_and_none":
+        return {
+            "status": status,
+            "availability": "fresh",
+            "materialized": True,
+            "source_path": canonical_path,
+            "errors": [],
+            "total": 0,
+            "truncated": False,
+        }
+
+    errors = fact.get("errors")
+    if not isinstance(errors, list):
+        errors = []
+    bound = 3 if compact else max_items
+    if bound is None:
+        bounded_errors = list(errors)
+    else:
+        bounded_errors = errors[:max(0, bound)]
+    return {
+        "status": status,
+        "availability": "fresh",
+        "materialized": True,
+        "source_path": canonical_path,
+        "errors": bounded_errors,
+        "total": len(errors),
+        "truncated": len(bounded_errors) < len(errors),
+    }
+
+
 def diagnostics_summary(root: Path, state: Any = None) -> dict[str, Any]:
     if state is None:
         engine = mcp_runtime._live_engines.get(str(root))
diff --git a/contextor/mcp/docs/get_file_edit_context.json b/contextor/mcp/docs/get_file_edit_context.json
index b2b3a16..f661462 100644
--- a/contextor/mcp/docs/get_file_edit_context.json
+++ b/contextor/mcp/docs/get_file_edit_context.json
@@ -17,7 +17,11 @@
     "1. mode=null (default): Combines LIVE module, API boundary, direct/transitive consumers, and covering tests. When compact=True, emits collection counts and truncated flags; when compact=False, emits bounded item lists up to max_items.",
     "2. mode='minimal': Returns an ultra-lightweight in-memory pre-edit decision projection (direct and transitive consumer counts, risk metrics, and covering test sample) without reading file bodies from disk.",
     "3. Consumer semantics: direct_count measures unique modules directly importing the target; transitive_count measures all unique modules reachable via reverse dependency traversal.",
-    "4. Exposes stale or unavailable canonical truth explicitly. Does not dump whole source files."
+    "4. Exposes stale or unavailable canonical truth explicitly. Does not dump whole source files.",
+    "5. syntax_diagnostics is a bounded projection of the canonical LIVE fact for the target's repository-relative Python source path. It is materialized only when syntax_diagnostics_state is fresh; checked_and_none returns materialized=true and errors=[], while checked_with_errors returns structured message, line_number, and column_number entries with total/truncated bounds.",
+    "6. When syntax_diagnostics_state is not_materialized, deferred, stale, unavailable, or the target has no canonical fact, syntax_diagnostics reports materialized=false, explicit availability, and errors=null; it never fabricates an empty success. A stale structural module response remains fail-closed but includes the current canonical syntax_diagnostics projection when available.",
+    "7. syntax_diagnostics is projected from canonical state only. This tool does not parse source or reread source for syntax diagnostics at query time.",
+    "8. A syntax fact for a path without a canonical module identity remains outside the existing get_file_edit_context target-resolution contract; this tool does not invent a module identity or broaden that input contract."
   ],
   "freshness": [
     "The response includes a ``state_freshness`` envelope scoped to the queried target file or module.",
@@ -25,7 +29,8 @@
     "- DOUBLE WARNING: When ``workspace_sync`` is ``out_of_sync``, a warning message is also added to the top-level ``warnings`` array in the response so legacy consumers see it.",
     "- ``canonical_revision``: Revision of the canonical state used to answer this query.",
     "- ``provenance``: ``live`` or ``snapshot``.",
-    "- ``advisory_warning``: Warning message when out of sync or if the last analysis job was interrupted/failed."
+    "- ``advisory_warning``: Warning message when out of sync or if the last analysis job was interrupted/failed.",
+    "- ``syntax_diagnostics.availability``: ``fresh`` means the current canonical syntax family was materialized for the target; ``not_materialized``, ``deferred``, ``stale``, or ``unavailable`` are explicit non-success states. ``syntax_diagnostics.errors=[]`` is emitted only for a materialized ``checked_and_none`` fact."
   ],
   "errors": [],
   "usage_notes": [
diff --git a/contextor/mcp/tools/get_file_edit_context.py b/contextor/mcp/tools/get_file_edit_context.py
index d4c2255..675e896 100644
--- a/contextor/mcp/tools/get_file_edit_context.py
+++ b/contextor/mcp/tools/get_file_edit_context.py
@@ -2,6 +2,7 @@ import json
 from pathlib import Path

 from contextor.mcp import query_helpers
+from contextor.mcp.diagnostics import syntax_diagnostics_for_path
 from contextor.mcp import runtime as mcp_runtime


@@ -234,6 +235,9 @@ def get_file_edit_context(
                 )
             unavailable = query_helpers.module_truth_unavailable(engine.state, module_name)
             if unavailable:
+                unavailable["syntax_diagnostics"] = syntax_diagnostics_for_path(
+                    engine.state, file_path_resolved, max_items=max_items, compact=compact
+                )
                 return json.dumps(unavailable, indent=2)
             live_graph = getattr(engine.state, "dependency_graph", None)
             if live_graph is None:
@@ -395,6 +399,9 @@ def get_file_edit_context(
                     "live_revision": live_revision,
                     "layer": layer,
                     "risk_score": risk_score,
+                    "syntax_diagnostics": syntax_diagnostics_for_path(
+                        engine.state, file_path_resolved, max_items=max_items, compact=compact
+                    ),
                     "layer_guard": layer_guard,
                     "consumers": {
                         "direct_count": len(direct_consumers),
@@ -437,6 +444,7 @@ def get_file_edit_context(
     module_name = ".".join(parts)
     effective_file_or_target = query_input
     target_kind = "module"
+    file_path_resolved = (catalog.module_paths or {}).get(module_name) or rel_path.as_posix()

     engine = mcp_runtime.get_or_init_engine(root)
     if not engine or getattr(engine.state, "resync_required", False):
@@ -446,6 +454,9 @@ def get_file_edit_context(
         state = engine.state
         unavailable = query_helpers.module_truth_unavailable(state, module_name)
         if unavailable:
+            unavailable["syntax_diagnostics"] = syntax_diagnostics_for_path(
+                state, file_path_resolved, max_items=max_items, compact=compact
+            )
             return json.dumps(unavailable, indent=2)
         state_metrics = getattr(state, "metrics", {}) or {}
         candidate_metrics = state_metrics.get(module_name, {}) if isinstance(state_metrics, dict) else {}
@@ -582,6 +593,9 @@ def get_file_edit_context(
             "layer": mod_info.get("layer", "unknown"),
             "entrypoint": mod_info.get("entrypoint", False),
             "risk_score": risk_score,
+            "syntax_diagnostics": syntax_diagnostics_for_path(
+                state, file_path_resolved, max_items=max_items, compact=compact
+            ),
             "dependency_data_source": dependency_data_source,
             "artifact_data_source": artifact_data_source,
             "state_freshness": state_freshness,
diff --git a/tests/test_mcp_diagnostics.py b/tests/test_mcp_diagnostics.py
index 81ae0d9..0cea02e 100644
--- a/tests/test_mcp_diagnostics.py
+++ b/tests/test_mcp_diagnostics.py
@@ -66,6 +66,49 @@ def test_attention_required_tracks_each_available_family():
     assert diagnostics_summary_for_state(SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[["a", "b", "a"]]))["attention_required"] is True


+def test_current_syntax_summary_counts_only_materialized_error_facts():
+    state = SimpleNamespace(
+        syntax_diagnostics_state="fresh",
+        syntax_diagnostics_by_path={
+            "valid.py": {"status": "checked_and_none", "errors": []},
+            "broken.py": {"status": "checked_with_errors", "errors": [{"message": "bad"}]},
+            "other.py": {"status": "checked_with_errors", "errors": [{"message": "bad"}]},
+        },
+        collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[],
+    )
+
+    summary = diagnostics_summary_for_state(state)
+
+    assert summary["syntax_errors"] == {"count": 2, "availability": "fresh"}
+    assert summary["attention_required"] is True
+
+
+def test_current_syntax_summary_materialized_zero_is_not_unavailable():
+    state = SimpleNamespace(
+        syntax_diagnostics_state="fresh",
+        syntax_diagnostics_by_path={"valid.py": {"status": "checked_and_none", "errors": []}},
+        collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[],
+    )
+
+    summary = diagnostics_summary_for_state(state)
+
+    assert summary["syntax_errors"] == {"count": 0, "availability": "fresh"}
+    assert summary["attention_required"] is False
+
+
+def test_current_syntax_summary_unmaterialized_families_never_fabricate_zero():
+    for family_state in ("not_materialized", "deferred"):
+        state = SimpleNamespace(
+            syntax_diagnostics_state=family_state,
+            syntax_diagnostics_by_path={},
+            collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[],
+        )
+
+        summary = diagnostics_summary_for_state(state)
+
+        assert summary["syntax_errors"] == {"count": None, "availability": family_state}
+
+
 def test_historical_job_does_not_promote_global_syntax_freshness(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
     repo.mkdir()


diff --git a/tests/mcp/tools/test_get_file_edit_context_syntax.py b/tests/mcp/tools/test_get_file_edit_context_syntax.py
new file mode 100644
index 0000000..5d7d73f
--- /dev/null
+++ b/tests/mcp/tools/test_get_file_edit_context_syntax.py
@@ -0,0 +1,139 @@
+import json
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.report_query import IndexCatalog
+from contextor.mcp import query_helpers
+from contextor.mcp import runtime as mcp_runtime
+from contextor.mcp.tools.get_file_edit_context import get_file_edit_context
+
+
+class _Graph:
+    hard_edges = {}
+    soft_edges = {}
+
+
+def _state(*, family_state="fresh", fact=None, stale=False):
+    return SimpleNamespace(
+        resync_required=False,
+        modules={"pkg.module": SimpleNamespace(path="pkg/module.py")},
+        artifacts={"pkg.module": {"symbols": {"functions": [], "classes": [], "methods": [], "globals": []}}},
+        dependency_graph=_Graph(),
+        metrics={},
+        cached_analytics={},
+        cached_analytics_state="deferred",
+        topology_analytics={},
+        topology_metrics_state="deferred",
+        syntax_diagnostics_state=family_state,
+        syntax_diagnostics_by_path={"pkg/module.py": fact} if fact is not None else {},
+        module_parse_freshness={"pkg.module": {"state": "stale"}} if stale else {},
+    )
+
+
+@pytest.fixture
+def harness(monkeypatch, tmp_path):
+    monkeypatch.setattr(
+        query_helpers,
+        "read_registries",
+        lambda _root: ({"pkg.module": "1/1"}, {"1/1": "pkg.module"}, {}, {}),
+    )
+    monkeypatch.setattr(
+        "contextor.core.report_query.catalog_from_registry",
+        lambda _root: IndexCatalog(
+            modules={"1/1": "pkg.module"},
+            artifacts={},
+            module_paths={"pkg.module": "pkg/module.py"},
+        ),
+    )
+    monkeypatch.setattr(
+        "contextor.core.report_query.resolve_index_query",
+        lambda _query, _catalog, repo_root=None: {
+            "matches": [{"kind": "module", "name": "pkg.module", "id": "1/1"}]
+        },
+    )
+    monkeypatch.setattr(query_helpers, "build_state_freshness", lambda *args, **kwargs: {"workspace_sync": "verified"})
+    harness = SimpleNamespace(root=tmp_path, state=None)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=harness.state))
+    return harness
+
+
+def _install_state(monkeypatch, harness, state):
+    harness.state = state
+    monkeypatch.setattr(query_helpers, "module_truth_unavailable", lambda _state, _module: (
+        {"status": "stale", "available": False, "module": "pkg.module"}
+        if state.module_parse_freshness else None
+    ))
+
+
+def test_valid_canonical_fact_is_projected_without_query_parse_or_source_read(monkeypatch, harness):
+    state = _state(fact={"status": "checked_and_none", "errors": []})
+    _install_state(monkeypatch, harness, state)
+    with monkeypatch.context() as blocker:
+        blocker.setattr("contextor.core.source.ast.parse", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("query must not parse")))
+        blocker.setattr("pathlib.Path.read_text", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("query must not read source")))
+        result = json.loads(get_file_edit_context(str(harness.root), file_path="pkg/module.py", fields=["syntax_diagnostics"]))
+
+    assert result["syntax_diagnostics"] == {
+        "status": "checked_and_none",
+        "availability": "fresh",
+        "materialized": True,
+        "source_path": "pkg/module.py",
+        "errors": [],
+        "total": 0,
+        "truncated": False,
+    }
+
+
+def test_syntax_error_survives_structural_fail_closed_response(monkeypatch, harness):
+    state = _state(
+        fact={
+            "status": "checked_with_errors",
+            "errors": [{"message": "invalid syntax", "line_number": 3, "column_number": 7}],
+        },
+        stale=True,
+    )
+    _install_state(monkeypatch, harness, state)
+    with monkeypatch.context() as blocker:
+        blocker.setattr("contextor.core.source.ast.parse", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("query must not parse")))
+        result = json.loads(get_file_edit_context(str(harness.root), file_path="pkg/module.py"))
+
+    assert result["status"] == "stale"
+    assert result["syntax_diagnostics"]["status"] == "checked_with_errors"
+    assert result["syntax_diagnostics"]["errors"] == [{
+        "message": "invalid syntax", "line_number": 3, "column_number": 7
+    }]
+    assert result["syntax_diagnostics"]["availability"] == "fresh"
+
+
+@pytest.mark.parametrize("family_state", ["not_materialized", "deferred"])
+def test_unavailable_syntax_family_never_fabricates_empty_errors(monkeypatch, harness, family_state):
+    state = _state(family_state=family_state)
+    _install_state(monkeypatch, harness, state)
+
+    result = json.loads(get_file_edit_context(str(harness.root), file_path="pkg/module.py"))
+
+    assert result["syntax_diagnostics"]["status"] == "unavailable"
+    assert result["syntax_diagnostics"]["availability"] == family_state
+    assert result["syntax_diagnostics"]["materialized"] is False
+    assert result["syntax_diagnostics"]["errors"] is None
+
+
+def test_syntax_projection_obeys_compact_full_and_bounded_fields(monkeypatch, harness):
+    state = _state(
+        fact={
+            "status": "checked_with_errors",
+            "errors": [{"message": f"e{i}", "line_number": i, "column_number": 1} for i in range(5)],
+        }
+    )
+    _install_state(monkeypatch, harness, state)
+
+    compact = json.loads(get_file_edit_context(str(harness.root), file_path="pkg/module.py", compact=True))
+    full = json.loads(get_file_edit_context(str(harness.root), file_path="pkg/module.py", compact=False, max_items=4))
+
+    assert len(compact["syntax_diagnostics"]["errors"]) == 3
+    assert compact["syntax_diagnostics"]["total"] == 5
+    assert compact["syntax_diagnostics"]["truncated"] is True
+    assert len(full["syntax_diagnostics"]["errors"]) == 4
+    assert full["syntax_diagnostics"]["total"] == 5
+    assert full["syntax_diagnostics"]["truncated"] is True

FULL_SUITE_RUN_BY_AGENT=NO

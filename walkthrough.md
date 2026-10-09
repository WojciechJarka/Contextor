# L29/L30 targeted contract hardening

## CURRENT_HEAD
eacdd668aba63b2255770127e75b889866ba28fd. Before edits, only walkthrough.md was modified from the preceding audit; exact three source anchors matched the supplied instructions. Contextor discovery: LIVE revision 121; the existing artifact_consumption TRANSFORMS edge incorrectly reported field=symbol_calls. get_file_edit_context found the MCP tool's direct consumers as contextor.mcp_server and tests.mcp.tools.test_contextor_fact_lineage. Public MCP documentation and contract tests were reviewed; documentation does not specify the erroneous field values, so no documentation edit was required.

## FILES_CHANGED
- contextor/mcp/tools/contextor_fact_lineage.py
- tests/mcp/tools/test_contextor_fact_lineage.py
- tests/test_completeness_freshness_parity_proof.py

walkthrough.md is this task report and is excluded from FILES_CHANGED.

## FULL_DIFFS
Exact git diff against CURRENT_HEAD for every file in FILES_CHANGED follows:

```diff
diff --git a/contextor/mcp/tools/contextor_fact_lineage.py b/contextor/mcp/tools/contextor_fact_lineage.py
index c2a4ad9..86a98c7 100644
--- a/contextor/mcp/tools/contextor_fact_lineage.py
+++ b/contextor/mcp/tools/contextor_fact_lineage.py
@@ -27,6 +27,7 @@ def _symbol(module: str, name: str) -> str:
 _SPECS: dict[str, dict[str, Any]] = {
     "artifact_consumption": {
         "state_field": "artifact_consumption",
+        "projection_field": "artifact_consumption",
         "state_state_field": "artifact_consumption_state",
         "branches": (
             {
@@ -96,6 +97,7 @@ _SPECS: dict[str, dict[str, Any]] = {
     },
     "syntax_diagnostics": {
         "state_field": "syntax_diagnostics_by_path",
+        "projection_field": "syntax_diagnostics_by_path",
         "state_state_field": "syntax_diagnostics_state",
         "branches": (
             {
@@ -151,6 +153,7 @@ _SPECS: dict[str, dict[str, Any]] = {
     },
     "symbol_calls": {
         "state_field": "module_usages[*].symbol_calls",
+        "projection_field": "symbol_calls",
         "state_state_field": "module_usages[*].symbol_calls_materialized",
         "branches": (
             {
@@ -451,7 +454,7 @@ def _build_contract(
                 "TRANSFORMS",
                 _evidence(
                     "named_field_projection",
-                    field="symbol_calls",
+                    field=spec["projection_field"],
                     branch=branch["branch"],
                 ),
                 via=branch["producer"],
diff --git a/tests/mcp/tools/test_contextor_fact_lineage.py b/tests/mcp/tools/test_contextor_fact_lineage.py
index b366507..fdfeddb 100644
--- a/tests/mcp/tools/test_contextor_fact_lineage.py
+++ b/tests/mcp/tools/test_contextor_fact_lineage.py
@@ -597,6 +597,29 @@ def test_confirmed_state_writers_match_real_owners_and_staging_chains(
     assert _edge(syntax, "MATERIALIZES", source=syntax_installer, target=syntax_state)
     assert _edge(syntax, "UPDATES", source=syntax_updater, target=syntax_state)
 
+    for result, expected_field in (
+        (artifact, "artifact_consumption"),
+        (syntax, "syntax_diagnostics_by_path"),
+        (symbols, "symbol_calls"),
+    ):
+        projection_edges = [
+            edge
+            for edge in result["edges"]
+            if edge["type"] == "TRANSFORMS"
+            and edge["evidence"]["kind"] == "named_field_projection"
+        ]
+        assert projection_edges
+        assert all(
+            edge["evidence"]["field"] == expected_field
+            for edge in projection_edges
+        )
+    for result in (artifact, syntax):
+        assert not any(
+            edge["type"] == "TRANSFORMS"
+            and edge["evidence"].get("field") == "symbol_calls"
+            for edge in result["edges"]
+        )
+
     for result in (artifact, symbols, syntax):
         assert all(edge["confidence"] == "confirmed" for edge in result["edges"])
         _assert_all_references_resolve(result)
diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index ebda63e..f251be9 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -27,7 +27,10 @@ from contextor.core.domain.refresh_plan import RefreshPlan
 from contextor.core.domain.usage_facts import ModuleUsageFacts, UsageDelta
 from contextor.core.live_state.hydration import hydrate_repository_engine
 from contextor.core.lineage_query.live_query import query_live_symbol_lineage
-from contextor.core.reference.engine import extract_module_usage_facts
+from contextor.core.reference.engine import (
+    build_symbol_references_from_canonical,
+    extract_module_usage_facts,
+)
 from contextor.core.reporting_engine.graph_analytics import (
     _CALL_USAGE_CHANNELS,
     _IMPORT_USAGE_CHANNELS,
@@ -2425,6 +2428,70 @@ def test_fail_closed_on_unsupported_plan_item(tmp_path):
             )
 
 
+def test_star_import_removal_clears_reference_evidence_and_consumption(
+    tmp_path, monkeypatch
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    provider = tmp_path / "a.py"
+    reexporter = tmp_path / "b.py"
+    consumer = tmp_path / "c.py"
+    provider.write_text("def imported():\n    pass\n", encoding="utf-8")
+    reexporter.write_text(
+        'from a import imported\n__all__ = ["imported"]\n',
+        encoding="utf-8",
+    )
+    consumer.write_text("from b import *\n", encoding="utf-8")
+
+    errors, _ = ContextorFacade().analyze_project(str(tmp_path))
+    assert not errors, errors
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    engine = hydrated.engine
+
+    before_facts = engine.state.module_usages["c"]
+    assert before_facts.reference_evidence_materialized is True
+    star_evidence = tuple(
+        item
+        for item in before_facts.reference_evidence
+        if item[0] == "b.*" and item[1] == "api_imports"
+    )
+    assert star_evidence
+    before_entry = engine.state.artifact_consumption["a::imported"]
+    assert "c" in before_entry["consumers"]
+    assert "api_imports" in before_entry["channels"]["c"]
+    unrelated_consumers = set(before_entry["consumers"]) - {"c"}
+    assert "b" in unrelated_consumers
+
+    replacement = "VALUE = 1\n"
+    consumer.write_text(replacement, encoding="utf-8")
+    result = engine.update_file(str(consumer))
+    assert result.status == "UPDATED"
+
+    after_facts = engine.state.module_usages["c"]
+    assert after_facts.reference_evidence_materialized is True
+    assert not set(star_evidence).intersection(after_facts.reference_evidence)
+    assert after_facts.reference_evidence == extract_module_usage_facts(
+        "c", replacement
+    ).reference_evidence
+    after_entry = engine.state.artifact_consumption["a::imported"]
+    assert "c" not in after_entry["consumers"]
+    assert "c" not in after_entry["channels"]
+    assert unrelated_consumers <= set(after_entry["consumers"])
+
+    references = build_symbol_references_from_canonical(
+        definer_module="a",
+        symbols=["imported"],
+        artifact_consumption=engine.state.artifact_consumption,
+        module_usages=engine.state.module_usages,
+        current_modules=set(engine.state.modules),
+    )
+    assert "c" not in references["imported"]["imported_from"]
+
+    oracle = _build_full_static_state(tmp_path)
+    _assert_full_parity(engine.state, oracle)
+    assert after_facts.reference_evidence == oracle.module_usages["c"].reference_evidence
+
+
 def test_star_import_visibility_changes_match_full_oracle(tmp_path, monkeypatch):
     monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
     provider = tmp_path / "a.py"
```

## L29_REMOVAL_BEFORE_AFTER
DIRECT TEST EVIDENCE (new exact node passed): before edit, c's reference_evidence is materialized and contains b.* / api_imports, while a::imported lists c with api_imports. After replacing only c.py with VALUE = 1 and a successful real update_file (UPDATED), c's evidence remains materialized, old star evidence is absent, and its exact tuple equals independent extraction of the new source. c is removed from a::imported consumers/channels; unrelated consumer b remains. Canonical reference projection no longer reports c as an importer.

## L29_FULL_ORACLE_PARITY
DIRECT TEST EVIDENCE: independent full analysis of the isolated temporary a.py/b.py/c.py fixture matched the incremental state under the existing _assert_full_parity helper. c's exact reference_evidence also matched the oracle. No full analysis of the Contextor repository was run.

## L30_PROJECTION_FIELD_MATRIX
- artifact_consumption -> artifact_consumption
- syntax_diagnostics -> syntax_diagnostics_by_path
- symbol_calls -> symbol_calls

The existing staging regression now checks every named_field_projection TRANSFORMS edge for each queried family and excludes symbol_calls from artifact_consumption and syntax_diagnostics. Edge identities, directions, producers, state fields, branch definitions, schema, freshness and installation ownership were preserved. This corrects MCP evidence metadata; it does not make the three fact domains equal.

## TARGETED_TEST_RESULTS
Exact nodes: 2 passed, 1 external AuthlibDeprecationWarning, 11.02s.
Command: .venv/Scripts/python.exe -m pytest -q tests/test_completeness_freshness_parity_proof.py::test_star_import_removal_clears_reference_evidence_and_consumption tests/mcp/tools/test_contextor_fact_lineage.py::test_confirmed_state_writers_match_real_owners_and_staging_chains

Focused three-file gate: 89 passed, 1 external AuthlibDeprecationWarning, 142.67s.
Command: .venv/Scripts/python.exe -m pytest -q tests/mcp/tools/test_contextor_fact_lineage.py tests/test_completeness_freshness_parity_proof.py tests/test_canonical_reference_projection.py

No repository-wide pytest suite was run. git diff --check reported no whitespace errors (only Git's LF/CRLF advisory).

## REGRESSION_FAILURES
NONE in the exact-node and focused three-file gates.

## MCP_RESTART_REQUIREMENT
MANUAL_MCP_BACKEND_RESTART_REQUIRED=YES before LIVE runtime certification, because contextor_fact_lineage.py is MCP server implementation code. No Desktop/LIVE/MCP restart was performed. The pre-edit LIVE revision 121 is discovery evidence, not post-edit runtime certification. No manual update_file was invoked.

## FINAL_VERDICT
PASS for the scoped source/test contract and targeted tests. LIVE MCP behavior remains uncertified until a separate authorized manual backend restart and fresh runtime check. No canonical extraction, materialization, watcher, persistence, or authority code changed.

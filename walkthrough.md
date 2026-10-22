# CONTEXTOR_CYCLE_PROOF_P0_EVIDENCE_HARDENING

## TASK
Applied only the auditor-supplied P0 evidence hardening patch. No algorithm redesign, warning-policy change, FULL analysis, full pytest suite, update_file or restart.

## HEAD_BEFORE
82c9ea4b8cfceefcfca04a06800faaaca0f7e415. Git working tree was clean before this task. Exact source anchors and the end of T16 matched the supplied patch.

## HEAD_AFTER
82c9ea4b8cfceefcfca04a06800faaaca0f7e415. No commit made.

## FILES_CHANGED
- contextor/core/cycle_semantics/evidence.py
- tests/test_cycle_semantics_evidence.py
walkthrough.md is the required report, excluded from source/test/docs changes.

## EXACT_IMPLEMENTATION
Added the exact auditor-provided check immediately after snapshot internal-edge identity: matched_edge_count must equal structural internal-edge count, unresolved_edge_count must be zero, and every internal edge must have status LEXICAL_CANDIDATES with nonempty sites. Failure returns INDETERMINATE / INCOMPLETE_EVIDENCE / UNRESOLVED_CYCLIC_IMPORT_SITES. Added the exact per-entry evidence_scope equality to RESTRICTED_FLAT_MODULE_MODEL before any positive model classification or internal hazard retention. Added auditor-provided T17 and T18 test bodies without changing other tests or the public SCCModelEvidenceAssessment contract.

## T17_RESULTS
Exact command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_evidence.py::test_p0_t17_lexical_import_evidence_required tests/test_cycle_semantics_evidence.py::test_p0_t18_entry_model_scope_must_match
T17: all 3 parametrized cases PASS: truly unresolved, unresolved with spoofed counts, and empty sites under LEXICAL_CANDIDATES. Combined exact command result: 5 passed in 1.15s, exit code 0.

## T18_RESULTS
T18: both parametrized cases PASS: positive MODEL_PASS and modeled EARLY_BINDING_HAZARD with altered entry evidence_scope each fail closed as INDETERMINATE / INCOMPLETE_EVIDENCE / INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS. Included in exact 5/5 result above.

## FOCUSED_TEST_RESULTS
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_initialization_model.py
Actual result: 76 passed in 3.04s, exit code 0. git diff --check: exit code 0; Git emitted only LF/CRLF conversion notices. No full repository suite.

## LIVE_REVISION_BEFORE_AFTER
Before: canonical revision 629, resync_required=false. After: revision 631, resync_required=false. Cycle-semantics family is stale following source edits, while module/graph/topology/cycle structural families report fresh. This is expected lifecycle invalidation, not runtime-safety evidence. Aggregate architecture workspace_sync remains unverified by its own scope.

## WATCHER_EVENTS
get_live_events(after_revision=629): revision 630, operation=update_file, origin=desktop_watcher, status=UPDATED, path=contextor/core/cycle_semantics/evidence.py, blast_radius_state=fresh, affected modules evidence and its test. get_live_events(after_revision=630): revision 631, operation=update_file, origin=desktop_watcher, status=UPDATED, path=tests/test_cycle_semantics_evidence.py, blast_radius_state=deferred. Both event queries returned continuity=continuous and resync_required=false. No manual update_file call.

## WORKSPACE_SYNC
At canonical revision 631, Contextor get_artifact_blast_radius on assess_index_bound_scc_models reports target module workspace_sync=verified and confirmed test consumer. Contextor get_module_context on tests.test_cycle_semantics_evidence reports workspace_sync=verified. A concurrent first post-edit blast-radius call returned [Errno 36] Resource deadlock avoided; the sequential retry succeeded. These checks verify canonical source adoption, not that the MCP serving Python process imported the modified module.

## RESTART_REQUIREMENTS
No restart performed. This pure evidence module has no confirmed production MCP consumer in Contextor blast radius; the new assessor's confirmed consumer is the focused test module. An already-running Python process that had imported evidence.py would require reload/restart to execute edited code; actual remote sys.modules was not inspected. No separate LIVE service restart is indicated by this test/isolated-module patch.

## FULL_DIFFS
Complete actual unified diff for both task-changed files follows.

```diff
diff --git a/contextor/core/cycle_semantics/evidence.py b/contextor/core/cycle_semantics/evidence.py
index b3aaa66..0f12362 100644
--- a/contextor/core/cycle_semantics/evidence.py
+++ b/contextor/core/cycle_semantics/evidence.py
@@ -168,6 +168,20 @@ def assess_index_bound_scc_models(
         if site_edges != structural.internal_edges:
             outputs.append(result(members, "SNAPSHOT_INTERNAL_EDGES_MISMATCH"))
             continue
+        site_component = snapshot.import_sites.components[position]
+        if (
+            site_component.matched_edge_count != len(structural.internal_edges)
+            or site_component.unresolved_edge_count != 0
+            or any(
+                edge.status != "LEXICAL_CANDIDATES" or not edge.sites
+                for edge in site_component.internal_edges
+            )
+        ):
+            outputs.append(result(
+                members, "UNRESOLVED_CYCLIC_IMPORT_SITES",
+                state="INCOMPLETE_EVIDENCE",
+            ))
+            continue
         if (
             evidence.classification != scenario.classification
             or evidence.coverage != scenario.coverage
@@ -245,6 +259,8 @@ def assess_index_bound_scc_models(
             or any(not isinstance(a, ImportOrderAssessment)
                    for a in scenario.entry_assessments)
             or tuple(a.entry_module for a in scenario.entry_assessments) != members
+            or any(a.evidence_scope != "RESTRICTED_FLAT_MODULE_MODEL"
+                   for a in scenario.entry_assessments)
             or any(a.outcome == "UNKNOWN" for a in scenario.entry_assessments)
         ):
             outputs.append(result(
diff --git a/tests/test_cycle_semantics_evidence.py b/tests/test_cycle_semantics_evidence.py
index bedc757..fa5718b 100644
--- a/tests/test_cycle_semantics_evidence.py
+++ b/tests/test_cycle_semantics_evidence.py
@@ -348,3 +348,87 @@ def test_p0_t16_no_warning_suppression_or_public_api_change():
     }
     assert not any("SAFE" in value or "warning" in value.lower()
                    for value in asdict(result[0]).values() if isinstance(value, str))
+
+
+@pytest.mark.parametrize(
+    "mode",
+    (
+        "unresolved",
+        "unresolved_spoofed_counts",
+        "empty_sites",
+    ),
+)
+def test_p0_t17_lexical_import_evidence_required(mode):
+    _, index, snapshot, evidence = _one()
+    site_report = snapshot.import_sites
+    component = site_report.components[0]
+    original_edge = component.internal_edges[0]
+
+    changed_edge = replace(
+        original_edge,
+        status=(
+            "LEXICAL_CANDIDATES"
+            if mode == "empty_sites"
+            else "NO_MATCHING_LEXICAL_SITE"
+        ),
+        sites=(),
+    )
+
+    if mode == "unresolved":
+        matched = component.matched_edge_count - 1
+        unresolved = component.unresolved_edge_count + 1
+    else:
+        matched = component.matched_edge_count
+        unresolved = component.unresolved_edge_count
+
+    changed_component = replace(
+        component,
+        internal_edges=(
+            changed_edge,
+            *component.internal_edges[1:],
+        ),
+        matched_edge_count=matched,
+        unresolved_edge_count=unresolved,
+    )
+
+    changed_snapshot = replace(
+        snapshot,
+        import_sites=replace(
+            site_report,
+            components=(changed_component,),
+        ),
+    )
+
+    result = assess(PAIR, index, changed_snapshot, evidence)
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
+    assert result[0].reason == "UNRESOLVED_CYCLIC_IMPORT_SITES"
+
+
+@pytest.mark.parametrize("sources", (PASS, HAZARD))
+def test_p0_t18_entry_model_scope_must_match(sources):
+    _, index, snapshot, evidence = _one(sources=sources)
+    scenario = evidence.scenarios.components[0]
+    changed_entry = replace(
+        scenario.entry_assessments[0],
+        evidence_scope="UNVERIFIED_EXECUTION_MODEL",
+    )
+    changed_scenario = replace(
+        scenario,
+        entry_assessments=(
+            changed_entry,
+            *scenario.entry_assessments[1:],
+        ),
+    )
+    changed_evidence = replace(
+        evidence,
+        scenarios=replace(
+            evidence.scenarios,
+            components=(changed_scenario,),
+        ),
+    )
+
+    result = assess(PAIR, index, snapshot, changed_evidence)
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
+    assert result[0].reason == "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS"
```

## FINAL_VERDICT
PASS for the exact auditor-supplied P0 hardening patch and all required focused gates. The result remains SNAPSHOT_MODEL_ONLY_NOT_LIVE_CERTIFIED; no runtime SAFE or warning-suppression claim is made.

# CONTEXTOR C16-B03-P1D2B-R1

## FILES_CHANGED

- tests/test_cycle_semantics_optional_child_byte_replay.py

walkthrough.md was overwritten as report. No production file changed.

## TARGETED_TESTS

- Corrected test alone: 1 passed.
- Same four P1D2B modules: 104 passed, 0 failed.
- CPython 3.15.2 via .venv, -B -q -rs -p no:cacheprovider, --basetemp=C:\Temp\Contextor_C16_P1D2B_R1_pytest_tmp outside repo.
- No full suite.

## MCP_AUDIT

Local HEAD ee56b0908b663e30604143f921617d3ec2de9c52. At canonical revision 1012, changed test and unchanged source_proof module both canonical_state=fresh, workspace_sync=verified, advisory_warning=null. Structural DFS path count 16. cycle_semantics remains stale. Indexed source freshness does not prove loaded backend adoption. No FULL, update_file, restart or commit.

## FULL_DIFFS

```diff
diff --git a/tests/test_cycle_semantics_optional_child_byte_replay.py b/tests/test_cycle_semantics_optional_child_byte_replay.py
index 801aeca..0b16915 100644
--- a/tests/test_cycle_semantics_optional_child_byte_replay.py
+++ b/tests/test_cycle_semantics_optional_child_byte_replay.py
@@ -185,17 +185,46 @@ def test_legacy_evidence_cannot_enter_optional_replay(tmp_path):
 
 def test_snapshot_lexical_evidence_must_match_bytes(tmp_path):
     case = list(_fixture(tmp_path))
+
+    original_sites = case[2].import_sites
+    component = original_sites.components[0]
+
+    assert component.internal_edges
+    assert component.internal_edges[0].sites
+
+    forged_edge = replace(
+        component.internal_edges[0],
+        sites=(),
+    )
+
+    forged_component = replace(
+        component,
+        internal_edges=(
+            forged_edge,
+            *component.internal_edges[1:],
+        ),
+    )
+
+    forged_sites = replace(
+        original_sites,
+        components=(
+            forged_component,
+            *original_sites.components[1:],
+        ),
+    )
+
     case[2] = replace(
         case[2],
-        import_sites=analyze_cyclic_import_sites(
-            {}, {},
-        ),
+        import_sites=forged_sites,
     )
 
     result = _verify(case)
+
     assert result[0].reason == (
-        "OPTIONAL_GRAPH_OR_TOPOLOGY_MISMATCH"
+        "OPTIONAL_LEXICAL_EVIDENCE_MISMATCH"
     )
+    assert result[0].bytes_state == "EVIDENCE_MISMATCH"
+    assert result[0].model_classification == "INDETERMINATE"
 
 
 def test_wrong_import_facts_fail_closed(tmp_path):
```

## FINAL_VERDICT

PASS

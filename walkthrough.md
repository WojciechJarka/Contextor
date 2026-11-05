# CONTEXTOR C16-B03-P1D2B-R2

## FILES_CHANGED

- contextor/core/cycle_semantics/evidence.py
- contextor/core/cycle_semantics/source_proof.py
- tests/test_cycle_semantics_optional_child_byte_replay.py

walkthrough.md was overwritten as the report. Initial local HEAD dc5e6e3c9ad4d68f9338b5259db945dcf4f8cc1d matched the supplied base; worktree was clean.

## TARGETED_TESTS

The four specified modules passed: 106 passed, 0 failed. CPython 3.15.2 via .venv, -B -q -rs -p no:cacheprovider, external --basetemp C:\Temp\Contextor_C16_P1D2B_R2_pytest_tmp. No full suite. Git diff --check for changed source/test files passed.

## MCP_POST_CHANGE_AUDIT

At canonical revision 1014, evidence and source_proof were canonical_state=fresh, workspace_sync=verified; the test module was temporarily out_of_sync while watcher indexing was in progress. Final test module query at revision 1016: canonical_state=fresh, workspace_sync=verified, advisory_warning=null. Structural DFS path count remains 16; cycle_semantics remains stale. Indexed source freshness does not prove loaded backend adoption. No FULL, update_file, restart, dependency install or manual commit.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/evidence.py b/contextor/core/cycle_semantics/evidence.py
index 5a5a59a..608d60e 100644
--- a/contextor/core/cycle_semantics/evidence.py
+++ b/contextor/core/cycle_semantics/evidence.py
@@ -697,9 +697,21 @@ def build_source_bound_cycle_evidence(
     )
     graph_fingerprint = _digest(graph_items)
 
+    if source_selection == "OPTIONAL_NAMED_CHILDREN":
+        selected_modules = {
+            module
+            for closure in closures
+            for module in closure.evidence_source_modules
+        }
+        manifest_names = sorted(
+            selected_modules.intersection(signatures)
+        )
+    else:
+        manifest_names = sorted(signatures)
+
     source_manifest = tuple(
         (name, *signatures[name])
-        for name in sorted(signatures)
+        for name in manifest_names
     )
 
     components: list[ComponentSourceEvidence] = []
diff --git a/contextor/core/cycle_semantics/source_proof.py b/contextor/core/cycle_semantics/source_proof.py
index 61eb75c..dd6bae3 100644
--- a/contextor/core/cycle_semantics/source_proof.py
+++ b/contextor/core/cycle_semantics/source_proof.py
@@ -496,11 +496,7 @@ def assess_optional_scc_source_bytes(
     ):
         return reject("OPTIONAL_MODEL_REPLAY_UNAVAILABLE")
 
-    if (
-        replay.scenarios != source_evidence.scenarios
-        or len(replay.components) != len(source_evidence.components)
-        or replay.components != source_evidence.components
-    ):
+    if replay != source_evidence:
         return reject(
             "OPTIONAL_MODEL_OR_TOKEN_REPLAY_MISMATCH",
             "EVIDENCE_MISMATCH",
diff --git a/tests/test_cycle_semantics_optional_child_byte_replay.py b/tests/test_cycle_semantics_optional_child_byte_replay.py
index 0b16915..dd2ea7c 100644
--- a/tests/test_cycle_semantics_optional_child_byte_replay.py
+++ b/tests/test_cycle_semantics_optional_child_byte_replay.py
@@ -19,15 +19,18 @@ from contextor.core.cycle_semantics.source_proof import (
     assess_optional_scc_source_bytes,
     assess_scc_source_bytes,
 )
-from tests.test_cycle_semantics_optional_child_scenarios import _case
+from tests.test_cycle_semantics_optional_child_scenarios import (
+    FILES,
+    _case,
+)
 from tests.test_cycle_semantics_optional_child_evidence import (
     _inputs,
     _build,
 )
 
 
-def _fixture(tmp_path):
-    case = _case(tmp_path)
+def _fixture(tmp_path, *, files=None):
+    case = _case(tmp_path, files=files)
     parsed, _ = _inputs(tmp_path, case)
     graph, _, imports, root, closures = case
     evidence = _build(case, parsed)
@@ -251,3 +254,63 @@ def test_existing_byte_verifier_still_rejects_optional(tmp_path):
         row.bytes_state != "BYTE_AST_CONSISTENT_NON_ATOMIC"
         for row in result
     )
+
+
+def test_forged_global_source_manifest_fingerprint_rejected(tmp_path):
+    case = list(_fixture(tmp_path))
+    evidence = case[3]
+
+    case[3] = replace(
+        evidence,
+        source_manifest_fingerprint="0" * 64,
+    )
+
+    result = _verify(case)
+
+    assert len(result) == 1
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].bytes_state == "EVIDENCE_MISMATCH"
+    assert result[0].reason == (
+        "OPTIONAL_MODEL_OR_TOKEN_REPLAY_MISMATCH"
+    )
+
+
+def test_unrelated_source_does_not_change_optional_manifest(tmp_path):
+    first = _fixture(
+        tmp_path / "first",
+        files={
+            **FILES,
+            "pkg/unrelated.py": "value = 1\n",
+        },
+    )
+
+    second = _fixture(
+        tmp_path / "second",
+        files={
+            **FILES,
+            "pkg/unrelated.py": "value = 2\n",
+        },
+    )
+
+    assert "pkg.unrelated" in first[1]
+    assert "pkg.unrelated" in second[1]
+
+    assert "pkg.unrelated" not in first[4]
+    assert "pkg.unrelated" not in second[4]
+
+    assert _verify(first)[0].bytes_state == (
+        "BYTE_AST_CONSISTENT_NON_ATOMIC"
+    )
+    assert _verify(second)[0].bytes_state == (
+        "BYTE_AST_CONSISTENT_NON_ATOMIC"
+    )
+
+    assert (
+        first[3].source_manifest_fingerprint
+        == second[3].source_manifest_fingerprint
+    )
+
+    assert (
+        first[3].components[0].evidence_token
+        == second[3].components[0].evidence_token
+    )
```

## FINAL_VERDICT

PASS

The supplied optional source manifest integrity patch and focused tests passed. No manifest, claim or publication integration was performed.

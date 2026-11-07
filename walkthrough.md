# C16-B03-P1D3G18-P2-P7

## HEAD_BEFORE_AFTER

`6c90d2749e4d625bcd855eed2f272ffac68e65d1` before and after. Initial worktree clean; no commit or push.

## FILES_CHANGED

- `contextor/core/cycle_semantics/namespace_source_binding.py`
- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_namespace_source_binding.py`
- `tests/test_cycle_semantics_namespace_path_model.py`
- `tests/test_cycle_semantics_namespace_bound_model.py`

`walkthrough.md` was overwritten as the report.

## CPYTHON_IDENTITY

Active repository `.venv\Scripts\python.exe`: CPython 3.15.2. No interpreter switch.

## FIVE_LIMIT_REMOVAL_CONTRACT

DIRECT_EVIDENCE: Removed `_MAX_SOURCES`, `_MAX_SOURCE_BYTES`, `_MAX_TOTAL_BYTES`, `_MAX_INVENTORY_FILES` and their binder acceptance guards. Removed `len(indexed_sources)>256` from the conditional model. Exact source-domain equality, module/path identity, duplicate rejection, SHA-256 comparison, namespace resolver, finder assumption, restricted AST rejection, operation budget and conditional authority were not edited. Source search found none of the five removed guard expressions in the two production files. No new input-size threshold was added.

## TARGETED_TEST_RESULTS

Six specified modules: **206 passed in 25.01s**, exit code 0. `git diff --check` exited 0. The 16,385-file test ran once as part of this subset.

## THRESHOLD_CROSSING_TESTS

CONTRACT_PROVED by passing new tests: a >2 MiB source with valid fingerprint binds; 308 source bindings pass; 17 sources of 2 MiB each exceed 32 MiB and bind; 16,385 inventory files bind; the conditional model and source-bound wrapper accept a synthetic 308-module cohort and return only `CONDITIONAL_MODEL_PASS` with their non-runtime authority strings.

## NEGATIVE_SAFETY_TESTS

CONTRACT_PROVED by passing assertions: a 308-source cohort missing one snapshot returns `SOURCE_INDEX_DOMAIN_MISMATCH` without digest; a >2 MiB source with forged expected SHA-256 returns `SOURCE_FINGERPRINT_MISMATCH` without digest. Existing targeted negative tests for path identity, shadowing, alternate loaders, finder uncertainty and unsupported model behavior also passed. The replaced M12 changes only the obsolete byte-budget expectation.

## FULL_PRODUCTION_SOURCE_BINDING_REPLAY

DIRECT_EVIDENCE: On canonical revision 1102, used all 308 indexed physical production `.py` files with exact module IDs, repo-relative paths, current bytes and FileState-matching SHA-256; total bytes 3,429,693, zero fingerprint mismatches. Indexed SCC entry `contextor.core.api.facade`, `standard_finder_assumed=True`. The binder now returns `SOURCE_BOUND_CONDITIONAL`, reason null, digest present and four selected path-chain sources. The source-bound wrapper then returns `UNKNOWN / RESTRICTED_MODEL_UNKNOWN`; nested model assessment is UNKNOWN with first target `contextor.__main__` and zero events. The next blocker is in the existing restricted model; this task does not classify its exact AST cause. The prior D7 `SOURCE_BINDING_INPUT_INVALID` size refusal is gone. Successful conditional binding is not actual runtime finder proof.

## REAL_SCC_REPLAY

DIRECT_EVIDENCE: Canonical hard_edges contain 626 indexed modules including tests; physical production inventory 308; optional SCC1 44 members/202 selected sources, SCC2 9 members/222 selected sources. All 222 selected source bytes in their union match FileState. SCC1: 607 external records, four namespace records, `OPAQUE_EXECUTION_POSSIBLE`. SCC2: 725 external records, four namespace records, same gate. Both retain consistency and scenario `INDETERMINATE / NAMESPACE_IMPORT_RESOLUTION_UNMODELED`, coverage NONE and zero entry assessments. Structural DFS cycles remain 16; no real SCC MODEL_PASS claim.

## SOURCE_BINDING

DIRECT_EVIDENCE: Snapshot metadata and metadata-selected FileState agree on revision 1102 and state_id `20261106_195021`, repo_id `ctx_8efc50d8`, root `C:\Temp\Contextor_Repo`. Full-production 308/308 and selected union 222/222 SHA-256 comparisons passed. No source was executed; replay parsed AST and invoked only restricted model functions.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP for all five modified modules returned revision 1102, canonical_state fresh, workspace_sync verified, advisory warning null, syntax errors 0, structural DFS cycles 16, active warning count 16, model_pass_count 0 and cycle_semantics stale. No FULL, update_file or restart was performed.

## REMAINING_AUTHORITY_GAPS

The supplied inventory is not authenticated `sys.path`, `sys.meta_path`, `sys.modules` or loader state. The full-production model result remains UNKNOWN at `contextor.__main__`; real SCC namespace and external execution uncertainty remains. Active runtime adoption of changed source was not certified. No warning-policy change or optional /3 receipt occurred.

## FULL_DIFFS

Complete actual Git diff of all five changed production/test files follows.

```diff
diff --git a/contextor/core/cycle_semantics/namespace_source_binding.py b/contextor/core/cycle_semantics/namespace_source_binding.py
index 1dc0750..5fd7220 100644
--- a/contextor/core/cycle_semantics/namespace_source_binding.py
+++ b/contextor/core/cycle_semantics/namespace_source_binding.py
@@ -21,11 +21,6 @@ from .namespace_path_model import (
 )
 
 
-_MAX_SOURCES = 256
-_MAX_SOURCE_BYTES = 2 * 1024 * 1024
-_MAX_TOTAL_BYTES = 32 * 1024 * 1024
-_MAX_INVENTORY_FILES = 16384
-
 _AUTHORITY = (
     "CALLER_SUPPLIED_INDEXED_SOURCE_BYTES_"
     "NOT_RUNTIME_OR_LIVE_CERTIFIED"
@@ -92,18 +87,11 @@ def bind_indexed_namespace_resolution(
     if (
         type(bindings) is not tuple
         or not bindings
-        or len(bindings) > _MAX_SOURCES
         or not isinstance(indexed_fingerprints, Mapping)
         or not isinstance(source_snapshots, Mapping)
     ):
         return reject("SOURCE_BINDING_INPUT_INVALID")
 
-    if (
-        sum(len(root.files) for root in roots)
-        > _MAX_INVENTORY_FILES
-    ):
-        return reject("INVENTORY_FILE_LIMIT")
-
     root_by_id = {}
 
     for root in roots:
@@ -182,7 +170,6 @@ def bind_indexed_namespace_resolution(
         return reject("INVENTORY_SOURCE_BINDING_MISMATCH")
 
     signatures = {}
-    retained_bytes = 0
 
     for module_id in sorted(required_ids):
         snapshot = source_snapshots[module_id]
@@ -201,14 +188,6 @@ def bind_indexed_namespace_resolution(
         ):
             return reject("SOURCE_SNAPSHOT_SHAPE_INVALID")
 
-        if len(snapshot.raw) > _MAX_SOURCE_BYTES:
-            return reject("SOURCE_BYTE_LIMIT")
-
-        retained_bytes += len(snapshot.raw)
-
-        if retained_bytes > _MAX_TOTAL_BYTES:
-            return reject("SOURCE_TOTAL_BYTE_LIMIT")
-
         actual_sha = hashlib.sha256(snapshot.raw).hexdigest()
 
         if (
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 8722d49..dad4f7c 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -1704,7 +1704,6 @@ def evaluate_conditional_namespace_import_order(
 
     if (
         not indexed_sources
-        or len(indexed_sources) > 256
         or any(
             type(module_id) is not str
             or not isinstance(tree, ast.Module)
diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
index a120041..0326078 100644
--- a/tests/test_cycle_semantics_namespace_bound_model.py
+++ b/tests/test_cycle_semantics_namespace_bound_model.py
@@ -310,3 +310,64 @@ def test_p6_deterministic_digest_and_outcome():
         first.source_evidence_sha256
         == second.source_evidence_sha256
     )
+
+
+def test_p7_source_bound_308_module_cohort():
+    names = tuple(
+        f"ns.m{index:05d}"
+        for index in range(308)
+    )
+
+    roots = (
+        SearchPortion(
+            "root",
+            frozenset(
+                name.replace(".", "/") + ".py"
+                for name in names
+            ),
+        ),
+    )
+
+    bindings = tuple(
+        IndexedSourcePath(
+            name,
+            "root",
+            name.replace(".", "/") + ".py",
+        )
+        for name in names
+    )
+
+    raw = b"pass\n"
+    digest = hashlib.sha256(raw).hexdigest()
+    snapshot = SourceSnapshot(raw, digest)
+
+    fingerprints = {
+        name: digest
+        for name in names
+    }
+
+    snapshots = {
+        name: snapshot
+        for name in names
+    }
+
+    result = evaluate_source_bound_conditional_namespace_import_order(
+        roots,
+        bindings,
+        fingerprints,
+        snapshots,
+        "ns.m00000",
+        standard_finder_assumed=True,
+    )
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.reason is None
+    assert result.source_evidence_sha256 is not None
+    assert result.conditional_assessment is not None
+    assert result.conditional_assessment.outcome == (
+        "CONDITIONAL_MODEL_PASS"
+    )
+    assert result.authority == (
+        "SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_"
+        "NOT_RUNTIME_OR_LIVE_PROOF"
+    )
diff --git a/tests/test_cycle_semantics_namespace_path_model.py b/tests/test_cycle_semantics_namespace_path_model.py
index f747ab9..d955939 100644
--- a/tests/test_cycle_semantics_namespace_path_model.py
+++ b/tests/test_cycle_semantics_namespace_path_model.py
@@ -595,3 +595,37 @@ def test_g18_p2_p5_deterministic_and_ast_immutable():
         )
         for name, tree in sources.items()
     }
+
+
+def test_g18_p2_p7_conditional_model_accepts_308_sources():
+    sources = {
+        f"ns.m{index:05d}": ast.parse("pass\n")
+        for index in range(308)
+    }
+
+    portions = (
+        SearchPortion(
+            "root",
+            frozenset(
+                f"ns/m{index:05d}.py"
+                for index in range(308)
+            ),
+        ),
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.m00000",
+        portions,
+    )
+
+    assert len(sources) == 308
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.reason is None
+    assert result.namespace_parents == ("ns",)
+    assert result.model_assessment is not None
+    assert result.model_assessment.outcome == "MODEL_PASS"
+    assert result.authority == (
+        "CONDITIONAL_ORDERED_INVENTORY_AND_AST_"
+        "NOT_RUNTIME_OR_LIVE_PROOF"
+    )
diff --git a/tests/test_cycle_semantics_namespace_source_binding.py b/tests/test_cycle_semantics_namespace_source_binding.py
index da5c3e5..b6b2572 100644
--- a/tests/test_cycle_semantics_namespace_source_binding.py
+++ b/tests/test_cycle_semantics_namespace_source_binding.py
@@ -239,10 +239,10 @@ def test_m11_inventory_order_changes_digest():
     assert first.evidence_sha256 != second.evidence_sha256
 
 
-def test_m12_source_byte_budget_fails_closed():
+def test_m12_source_over_old_byte_limit_is_bound():
     roots, rows, hashes, snapshots = _base()
 
-    oversized = b"x" * (2 * 1024 * 1024 + 1)
+    oversized = b"#" * (2 * 1024 * 1024 + 1)
     digest = hashlib.sha256(oversized).hexdigest()
 
     snapshots["pkg.ns.child"] = SourceSnapshot(
@@ -253,8 +253,11 @@ def test_m12_source_byte_budget_fails_closed():
 
     result = _bind(roots, rows, hashes, snapshots)
 
-    assert result.reason == "SOURCE_BYTE_LIMIT"
-    assert result.evidence_sha256 is None
+    assert result.status == "SOURCE_BOUND_CONDITIONAL"
+    assert result.reason is None
+    assert result.evidence_sha256 is not None
+    assert len(result.evidence_sha256) == 64
+    assert result.selected_sources[-1][2] == digest
 
 
 def test_m13_deterministic_without_live_authority():
@@ -319,3 +322,144 @@ def test_m15_indexed_shadowing_source_still_blocks_child():
     assert result.resolution is not None
     assert result.resolution.steps[-1].kind == "MODULE_FILE"
     assert result.resolution.steps[-1].source == "root:pkg/ns.py"
+
+
+def _p7_inventory(count, *, raw=b"pass\n"):
+    names = tuple(
+        f"ns.m{index:05d}"
+        for index in range(count)
+    )
+
+    paths = tuple(
+        name.replace(".", "/") + ".py"
+        for name in names
+    )
+
+    roots = (
+        SearchPortion(
+            "root",
+            frozenset(paths),
+        ),
+    )
+
+    bindings = tuple(
+        IndexedSourcePath(
+            name,
+            "root",
+            path,
+        )
+        for name, path in zip(names, paths)
+    )
+
+    digest = hashlib.sha256(raw).hexdigest()
+    snapshot = SourceSnapshot(raw, digest)
+
+    fingerprints = {
+        name: digest
+        for name in names
+    }
+
+    snapshots = {
+        name: snapshot
+        for name in names
+    }
+
+    return (
+        roots,
+        bindings,
+        fingerprints,
+        snapshots,
+    )
+
+
+def test_p7_308_indexed_sources_are_bound():
+    args = _p7_inventory(308)
+
+    result = _bind(
+        *args,
+        requested="ns.m00000",
+    )
+
+    assert result.status == "SOURCE_BOUND_CONDITIONAL"
+    assert result.reason is None
+    assert result.evidence_sha256 is not None
+    assert len(args[1]) == 308
+
+
+def test_p7_total_source_size_above_32_mib_is_bound():
+    raw = b"#" * (2 * 1024 * 1024)
+
+    args = _p7_inventory(
+        17,
+        raw=raw,
+    )
+
+    assert 17 * len(raw) > 32 * 1024 * 1024
+
+    result = _bind(
+        *args,
+        requested="ns.m00000",
+    )
+
+    assert result.status == "SOURCE_BOUND_CONDITIONAL"
+    assert result.reason is None
+    assert result.evidence_sha256 is not None
+
+
+def test_p7_inventory_above_16384_files_is_bound():
+    args = _p7_inventory(16385)
+
+    assert len(args[0][0].files) == 16385
+    assert len(args[1]) == 16385
+
+    result = _bind(
+        *args,
+        requested="ns.m00000",
+    )
+
+    assert result.status == "SOURCE_BOUND_CONDITIONAL"
+    assert result.reason is None
+    assert result.evidence_sha256 is not None
+
+
+def test_p7_large_cohort_still_rejects_missing_source():
+    roots, bindings, fingerprints, snapshots = (
+        _p7_inventory(308)
+    )
+
+    del snapshots["ns.m00307"]
+
+    result = _bind(
+        roots,
+        bindings,
+        fingerprints,
+        snapshots,
+        requested="ns.m00000",
+    )
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "SOURCE_INDEX_DOMAIN_MISMATCH"
+    assert result.evidence_sha256 is None
+
+
+def test_p7_large_source_still_checks_fingerprint():
+    roots, bindings, fingerprints, snapshots = (
+        _p7_inventory(
+            1,
+            raw=b"#" * (2 * 1024 * 1024 + 1),
+        )
+    )
+
+    fingerprints["ns.m00000"] = "0" * 64
+
+    result = _bind(
+        roots,
+        bindings,
+        fingerprints,
+        snapshots,
+        requested="ns.m00000",
+    )
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"
+    assert result.evidence_sha256 is None
```

## FINAL_VERDICT

PASS — five specified input-size thresholds removed, 206 targeted tests passed, full 308-source binding passed, real SCCs remain INDETERMINATE and structural cycles remain 16.

# TASK
P1D1B_FINAL_COLLISION_AND_CACHE_REGRESSION_FIX — exact auditor-supplied patch only.

# HEAD_BEFORE
eeb38c307a716698ab719cc542a572ec7981fadd; clean working tree. Exact source/test anchors matched.

# HEAD_AFTER
eeb38c307a716698ab719cc542a572ec7981fadd; uncommitted.

# FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\core\cycle_semantics\selective_worker_capture.py
- C:\Temp\Contextor_Repo\tests\test_cycle_semantics_selective_worker_capture.py

# COLLISION_ROOT_CAUSE
DIRECT_EVIDENCE: pre-edit Contextor get_name_collisions at canonical revision 658 reported exactly two IDENTICAL_DEFINITION_DUPLICATE variable warnings between selective_source_replay and selective_worker_capture: DEFAULT_MAX_SOURCE_BYTES and DEFAULT_MAX_CLOSURE_BYTES. Both had identical public definitions. No global collision-policy change was warranted.

# EXACT_FIX
Changed only the two P1D1B constants to private, module-specific _DEFAULT_WORKER_CAPTURE_SOURCE_BYTES and _DEFAULT_WORKER_CAPTURE_CLOSURE_BYTES and their default-argument references. T02 now forbids parse_source_snapshot and requires exactly CACHE_SHA256_EQUIVALENT. T17 uses the actual extract_module_collision_facts and compute_collisions_from_facts implementations on both module ASTs and requires no collision. Indexer, graph, LIVE, MCP, process pool, P1D0 and existing tests were untouched.

# T01_T17_RESULTS
DIRECT_EVIDENCE: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_selective_worker_capture.py => 17 passed in 9.46s.

# WARM_CACHE_PROOF
DIRECT_EVIDENCE: T02 monkeypatches worker_indexer.parse_source_snapshot to raise if called, then verifies all returned ast_modes equal CACHE_SHA256_EQUIVALENT. The test passed. It proves the tested warm-cache path did not call fresh parsing; cache equivalence remains hash-validated, not original FULL byte identity.

# COLLISION_REGRESSION_PROOF
DIRECT_EVIDENCE: T17 parsed both current files into AST, extracted actual module collision facts, and compute_collisions_from_facts returned []. The focused collision test passed; this does not substitute for LIVE evidence, which is given below.

# FOCUSED_NON_REGRESSION
DIRECT_EVIDENCE: .\.venv\Scripts\python.exe -m pytest -q tests/test_indexer_worker_source_capture.py tests/test_cycle_semantics_selective_source_replay.py tests/test_canonical_collision_code_parity.py tests/test_collisions_live_lifecycle.py => 54 passed, 1 third-party AuthlibDeprecationWarning in 37.91s. No full suite.

# LIVE_REVISION_BEFORE_AFTER
658 → 660; Contextor get_live_events(after_revision=658): continuity=continuous, resync_required=false, total=2, truncated=false.

# WATCHER_EVENTS
DIRECT_EVIDENCE: revision 659 desktop_watcher update_file UPDATED for selective_worker_capture.py; revision 660 desktop_watcher update_file UPDATED for test_cycle_semantics_selective_worker_capture.py. No manual update_file, FULL analysis, or restart.

# COLLISION_RESOLUTION_EVIDENCE
DIRECT_EVIDENCE: revision 659 diagnostic_changes total=2, truncated=false, with explicit RESOLVED collision entries for DEFAULT_MAX_CLOSURE_BYTES and DEFAULT_MAX_SOURCE_BYTES, each IDENTICAL_DEFINITION_DUPLICATE between selective_source_replay and selective_worker_capture. Post-edit Contextor get_name_collisions(collision_type=IDENTICAL_DEFINITION_DUPLICATE): matched=0, details=[], current total collisions=2 (other kinds). Collision family is fresh. This directly confirms canonical resolution; it is not inferred merely from the rename.

# WORKSPACE_SYNC
Post-edit Contextor get_module_context: both changed files canonical_state=fresh, workspace_sync=verified, advisory_warning=null at revision 660. The cycle_semantics family remains separately stale and is not certified by this fix.

# RUNTIME_ADOPTION_LIMITATION
Fresh Python test processes executed the updated code. LIVE watcher and workspace_sync certify canonical source adoption. They do not prove loaded-code adoption in already-running Desktop/MCP/LIVE processes. P1D1B remains a worker second-pass byte contract, not original FULL source, LIVE generation, atomic transaction, or SAFE certificate.

# RESTART_REQUIREMENTS
No automatic restart. Already-running processes may need manual reload/restart if they must import the changed module; runtime adoption was not certified. Executor timeout policy remains outside scope.

# WHITESPACE_CHECK
py_compile passed for both files; git diff --check passed. Git produced only LF-to-CRLF future working-copy warnings.

# FULL_DIFFS

## contextor/core/cycle_semantics/selective_worker_capture.py

```diff
diff --git a/contextor/core/cycle_semantics/selective_worker_capture.py b/contextor/core/cycle_semantics/selective_worker_capture.py
index 007a454..b6e3135 100644
--- a/contextor/core/cycle_semantics/selective_worker_capture.py
+++ b/contextor/core/cycle_semantics/selective_worker_capture.py
@@ -30,8 +30,8 @@ WORKER_CAPTURE_AUTHORITY = (
     "_NOT_ATOMIC_NOT_LIVE_CERTIFIED"
 )
 
-DEFAULT_MAX_SOURCE_BYTES = 2 * 1024 * 1024
-DEFAULT_MAX_CLOSURE_BYTES = 32 * 1024 * 1024
+_DEFAULT_WORKER_CAPTURE_SOURCE_BYTES = 2 * 1024 * 1024
+_DEFAULT_WORKER_CAPTURE_CLOSURE_BYTES = 32 * 1024 * 1024
 
 _SUCCESS = (
     "WORKER_SECOND_PASS_BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
@@ -276,8 +276,8 @@ def iter_selective_scc_worker_captures(
     hard_edges: Mapping[str, object],
     index: RepositoryIndex,
     *,
-    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
-    max_closure_bytes: int = DEFAULT_MAX_CLOSURE_BYTES,
+    max_source_bytes: int = _DEFAULT_WORKER_CAPTURE_SOURCE_BYTES,
+    max_closure_bytes: int = _DEFAULT_WORKER_CAPTURE_CLOSURE_BYTES,
     executor: Executor | None = None,
 ) -> Iterator[SCCWorkerCapture]:
     """Replay only reachable cyclic SCC closures.
```

## tests/test_cycle_semantics_selective_worker_capture.py

```diff
diff --git a/tests/test_cycle_semantics_selective_worker_capture.py b/tests/test_cycle_semantics_selective_worker_capture.py
index 874fdf8..a135f09 100644
--- a/tests/test_cycle_semantics_selective_worker_capture.py
+++ b/tests/test_cycle_semantics_selective_worker_capture.py
@@ -2,8 +2,10 @@
 
 from __future__ import annotations
 
+import ast
 import hashlib
 from dataclasses import replace
+from pathlib import Path
 
 import pytest
 
@@ -14,10 +16,18 @@ from contextor.core.analysis.process_pool_lifecycle import (
 from contextor.core.cycle_semantics import (
     selective_worker_capture as capture,
 )
+from contextor.core.cycle_semantics import (
+    selective_source_replay,
+)
 from contextor.core.graph.graph import build_graph
+from contextor.core.symbol_engine import indexer as worker_indexer
 from contextor.core.symbol_engine.indexer import (
     index_repository,
 )
+from contextor.core.validator.collisions import (
+    compute_collisions_from_facts,
+    extract_module_collision_facts,
+)
 
 
 @pytest.fixture(autouse=True)
@@ -99,18 +109,28 @@ def test_p1d1b_t01_only_scc_closure_replayed(
 
 
 def test_p1d1b_t02_warm_cache_mode_is_explicit(
-    tmp_path, isolated_dirs,
+    tmp_path, isolated_dirs, monkeypatch,
 ):
     root = _repo(tmp_path)
     index, edges = _analyze(root)
 
+    def forbidden_parse(*args, **kwargs):
+        raise AssertionError(
+            "warm-cache worker reparsed source"
+        )
+
+    monkeypatch.setattr(
+        worker_indexer,
+        "parse_source_snapshot",
+        forbidden_parse,
+    )
+
     (item,) = _results(root, index, edges)
 
     _assert_complete(item, index)
-    assert set(dict(item.ast_modes).values()).issubset({
+    assert set(dict(item.ast_modes).values()) == {
         "CACHE_SHA256_EQUIVALENT",
-        "PARSED_FROM_WORKER_READ",
-    })
+    }
 
 
 def test_p1d1b_t03_real_process_pool_capture(
@@ -432,3 +452,26 @@ def test_p1d1b_t16_worker_module_identity_fails_closed(
         "WORKER_IDENTITY_MISMATCH:"
     )
     assert item.source_snapshots == {}
+
+
+def test_p1d1b_t17_no_public_definition_collision_with_p1d0():
+    modules = {
+        "selective_source_replay": selective_source_replay,
+        "selective_worker_capture": capture,
+    }
+
+    facts = {}
+
+    for module_id, module in modules.items():
+        path = Path(module.__file__).resolve()
+        tree = ast.parse(
+            path.read_text(encoding="utf-8"),
+            filename=str(path),
+        )
+        facts[module_id] = extract_module_collision_facts(
+            tree,
+            module_id,
+            str(path),
+        )
+
+    assert compute_collisions_from_facts(facts) == []
```

# FINAL_VERDICT
FINAL PASS for the exact approved fix: all targeted tests passed, both canonical collisions were explicitly resolved and are absent from current LIVE diagnostics, and both changed files are workspace_sync=verified. Existing-process loaded-code adoption is not claimed.
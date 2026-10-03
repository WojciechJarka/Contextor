STATUS=PASS
FILES_CHANGED=tests/test_collisions_live_lifecycle.py

FULL_DIFFS=
```diff
diff --git a/tests/test_collisions_live_lifecycle.py b/tests/test_collisions_live_lifecycle.py
index 428a695..23e72b2 100644
--- a/tests/test_collisions_live_lifecycle.py
+++ b/tests/test_collisions_live_lifecycle.py
@@ -577,7 +577,7 @@ def test_historical_patch_families_ordering_preserved():
     )
 
 
-def test_missing_ast_snapshot_report_parity():
+def test_missing_ast_snapshot_report_parity(isolated_dirs):
     """Snapshot report retains valid collisions from parseable modules when 1 module has missing AST."""
     from contextor.core.domain.graph import ProjectGraph
     from contextor.core.reporting_engine.pipeline import execute_global_pipeline
```

PY_COMPILE=PASS
TARGETED_TESTS=PASS
TARGETED_TEST_COUNT=1
TARGETED_FAILURES=NONE
TARGETED_COMMAND=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_collisions_live_lifecycle.py::test_missing_ast_snapshot_report_parity

TEST_USES_ISOLATED_DIRS=YES
PRODUCTION_OUTPUT_PATH_USED_BY_TEST=NO
PRODUCTION_FILES_CHANGED=NO
ATOMIC_WRITE_CHANGED=NO
RESOLVE_REPORT_PATH_CHANGED=NO

FAMILY_D_FAILURE_TARGETED_VALIDATED=YES

CONTEXTOR_REVISION=1451
WORKSPACE_SYNC=verified
CANONICAL_STATE=fresh

FULL_SUITE_RUN=NO
ANALYZE_PROJECT_RUN_COUNT=0
UPDATE_FILE_CALLED=NO
RESTART_PERFORMED=NO
PROCESS_TERMINATION_PERFORMED=NO
FIX_DESIGNED_BY_AGENT=NO
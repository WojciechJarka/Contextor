STATUS=PASS
FILES_CHANGED=tests/test_process_pool_lifecycle.py

FULL_DIFFS=
```diff
diff --git a/tests/test_process_pool_lifecycle.py b/tests/test_process_pool_lifecycle.py
index fba84ae..6bc5ef5 100644
--- a/tests/test_process_pool_lifecycle.py
+++ b/tests/test_process_pool_lifecycle.py
@@ -60,6 +60,19 @@ class _FakeExecutor:
         )
 
 
+@pytest.fixture(autouse=True)
+def _isolate_process_pool_registry():
+    lifecycle.terminate_active_process_pools(
+        timeout=0.05,
+    )
+    try:
+        yield
+    finally:
+        lifecycle.terminate_active_process_pools(
+            timeout=0.05,
+        )
+
+
 def test_managed_process_pool_registry_is_process_local():
     assert lifecycle.active_process_pool_count() == 0
```

PY_COMPILE=PASS
TARGETED_TESTS=PASS
TARGETED_TEST_COUNT=8
TARGETED_FAILURES=NONE
TARGETED_COMMAND=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_process_pool_lifecycle.py::test_managed_process_pool_registry_is_process_local tests/test_process_pool_lifecycle.py::test_mcp_managed_pool_worker_is_durably_registered tests/test_process_pool_lifecycle.py::test_force_shutdown_terminates_then_kills_survivors tests/test_process_pool_lifecycle.py::test_real_process_pool_workers_are_force_terminated tests/test_process_pool_lifecycle.py::test_desktop_close_force_terminates_process_local_pools tests/test_process_pool_lifecycle.py::test_reusable_process_pool_preserves_generation_between_leases tests/test_process_pool_lifecycle.py::test_reusable_process_pool_exception_invalidates_generation tests/test_process_pool_lifecycle.py::test_reusable_process_pool_rotates_when_registry_scope_changes

TEST_BOUNDARY_REGISTRY_ISOLATION=YES
REUSABLE_POOL_PERSISTS_WITHIN_TEST=YES
REUSABLE_EXCEPTION_INVALIDATION_PRESERVED=YES
REGISTRY_SCOPE_ROTATION_PRESERVED=YES
PRODUCTION_FILES_CHANGED=NO

FAMILY_B_3_FAILURES_TARGETED_VALIDATED=YES

CONTEXTOR_REVISION=1448
WORKSPACE_SYNC=verified
CANONICAL_STATE=fresh

FULL_SUITE_RUN=NO
ANALYZE_PROJECT_RUN_COUNT=0
UPDATE_FILE_CALLED=NO
RESTART_PERFORMED=NO
PROCESS_TERMINATION_PERFORMED=TEST_OWNED_POOLS_ONLY
FIX_DESIGNED_BY_AGENT=NO
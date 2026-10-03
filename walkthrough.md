STATUS=FAIL
FILES_CHANGED=tests/test_live_desktop_integration.py
FULL_DIFFS=
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index 805bcd8..05487f7 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -578,6 +578,7 @@ def test_inactive_repository_callbacks_do_not_overwrite_selected_live_state(
     controller = SimpleNamespace(
         repo_path_var=SimpleNamespace(get=lambda: str(first)),
         _selected_live_repo_path=str(first),
+        repo_id_var=_LiveIntegrationFakeVar(),
         live_watcher=None,
         live_event_feed=None,
         live_watchers={},
TARGETED_TESTS=PASS
TARGETED_TEST_COUNT=7
TARGETED_FAILURES=NONE
WORKSPACE_SYNC=out_of_sync
CANONICAL_STATE=fresh
CANONICAL_REVISION=1442
CURRENT_GUI_STAGE_VALIDATED=NO
FULL_SUITE_LAST_RESULT=16_FAILED_2686_PASSED_1_SKIPPED
FULL_SUITE_FAILURES_NOT_FIXED=YES
ANALYZE_PROJECT_RUN_COUNT=0
UPDATE_FILE_CALLED=NO
RESTART_PERFORMED=NO
FIX_DESIGNED_BY_AGENT=NO

STATUS=IMPLEMENTED_NOT_TESTED
FILES_CHANGED=contextor/ui/gui.py;tests/test_gui_live_startup.py;tests/test_live_desktop_integration.py
FULL_DIFFS=
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 393b070..e551d69 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -100,6 +100,11 @@ class ContextorGUI:
         self.file_path_var = tk.StringVar(
             value=self.state.get("python_file", "").replace("\\", "/")
         )
+        self._selected_live_repo_path = self.repo_path_var.get()
+        self._repo_path_trace_id = self.repo_path_var.trace_add(
+            "write",
+            self._sync_selected_live_repository_path,
+        )
 
         self.exclude_win = None
         self.repo_builder_win = None
@@ -546,11 +551,17 @@ class ContextorGUI:
         if hasattr(self, "progress_bar"):
             self.progress_bar.is_cancelled = True
 
-    def _is_selected_live_repository(self, path):
+    def _sync_selected_live_repository_path(self, *_args):
         repo_path_var = getattr(self, "repo_path_var", None)
         if repo_path_var is None or not hasattr(repo_path_var, "get"):
+            self._selected_live_repo_path = ""
+            return
+        self._selected_live_repo_path = repo_path_var.get()
+
+    def _is_selected_live_repository(self, path):
+        if not hasattr(self, "_selected_live_repo_path"):
             return True
-        selected = repo_path_var.get()
+        selected = self._selected_live_repo_path
         if not selected:
             return False
         try:
@@ -573,6 +584,7 @@ class ContextorGUI:
         if directory:
             directory = directory.replace("\\", "/")
             self.repo_path_var.set(directory)
+            self._selected_live_repo_path = directory
             self.layer_path_var.set("")
             save_state(repository=directory)
             ContextorGUI._discard_pending_live_statuses(self)
diff --git a/tests/test_gui_live_startup.py b/tests/test_gui_live_startup.py
index bbeb0ac..b987789 100644
--- a/tests/test_gui_live_startup.py
+++ b/tests/test_gui_live_startup.py
@@ -89,6 +89,7 @@ def _make_controller(repo_path, root=None):
         _live_start_threads={},
         repo_id_var=_GuiFakeVar("Repo ID: unregistered"),
         repo_path_var=_GuiFakeVar(str(repo_path)),
+        _selected_live_repo_path=str(repo_path),
         layer_path_var=_GuiFakeVar(""),
         file_path_var=_GuiFakeVar(""),
         theme_mode="light",
@@ -99,6 +100,24 @@ def _make_controller(repo_path, root=None):
     return controller
 
 
+def test_selected_live_repository_predicate_does_not_read_tk_variable(tmp_path):
+    selected = tmp_path / "selected"
+    other = tmp_path / "other"
+    selected.mkdir()
+    other.mkdir()
+
+    def forbidden_get():
+        raise AssertionError("worker predicate must not read Tk/StringVar")
+
+    controller = SimpleNamespace(
+        _selected_live_repo_path=str(selected),
+        repo_path_var=SimpleNamespace(get=forbidden_get),
+    )
+
+    assert ContextorGUI._is_selected_live_repository(controller, str(selected)) is True
+    assert ContextorGUI._is_selected_live_repository(controller, str(other)) is False
+
+
 def _wait_for_live_start(controller, timeout=5.0):
     deadline = time.monotonic() + timeout
     while time.monotonic() < deadline:
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index 3caad31..805bcd8 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -422,6 +422,7 @@ def test_browse_repository_switches_live_to_selected_registered_repo(
 
     controller = SimpleNamespace(
         repo_path_var=_LiveIntegrationFakeVar(),
+        _selected_live_repo_path=str(first),
         layer_path_var=_LiveIntegrationFakeVar(),
         _live_status_queue=status_queue,
         _set_live_status=lambda message: events.append(
@@ -442,6 +443,7 @@ def test_browse_repository_switches_live_to_selected_registered_repo(
 
     selected = str(second).replace("\\", "/")
     assert controller.repo_path_var.value == selected
+    assert controller._selected_live_repo_path == selected
     assert controller.layer_path_var.value == ""
     assert status_queue.empty()
     assert events == [
@@ -575,6 +577,7 @@ def test_inactive_repository_callbacks_do_not_overwrite_selected_live_state(
 
     controller = SimpleNamespace(
         repo_path_var=SimpleNamespace(get=lambda: str(first)),
+        _selected_live_repo_path=str(first),
         live_watcher=None,
         live_event_feed=None,
         live_watchers={},
THREAD_SAFE_ACTIVE_REPO_SNAPSHOT=YES
BACKGROUND_TK_STRINGVAR_READ=NO
CONTEXTOR_REVISION=1442
WORKSPACE_SYNC=verified
CANONICAL_STATE=fresh
TESTS_RUN=NO
FULL_SUITE_RUN=NO
ANALYZE_PROJECT_RUN_COUNT=0
UPDATE_FILE_CALLED=NO
RESTART_PERFORMED=NO
FIX_DESIGNED_BY_AGENT=NO
NEXT_STEP=Wait for proceduj before validation.

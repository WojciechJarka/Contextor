STATUS=IMPLEMENTED_NOT_TESTED
FILES_CHANGED=contextor/ui/gui.py;tests/test_gui_live_startup.py;tests/test_live_desktop_integration.py
FULL_DIFFS=
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index eb5b708..393b070 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -546,6 +546,28 @@ class ContextorGUI:
         if hasattr(self, "progress_bar"):
             self.progress_bar.is_cancelled = True
 
+    def _is_selected_live_repository(self, path):
+        repo_path_var = getattr(self, "repo_path_var", None)
+        if repo_path_var is None or not hasattr(repo_path_var, "get"):
+            return True
+        selected = repo_path_var.get()
+        if not selected:
+            return False
+        try:
+            return Path(selected).expanduser().resolve() == Path(path).expanduser().resolve()
+        except Exception:
+            return str(selected).replace("\\", "/") == str(path).replace("\\", "/")
+
+    def _discard_pending_live_statuses(self):
+        queue = getattr(self, "_live_status_queue", None)
+        if queue is None:
+            return
+        while True:
+            try:
+                queue.get_nowait()
+            except Empty:
+                return
+
     def browse_repository(self):
         directory = filedialog.askdirectory()
         if directory:
@@ -553,6 +575,8 @@ class ContextorGUI:
             self.repo_path_var.set(directory)
             self.layer_path_var.set("")
             save_state(repository=directory)
+            ContextorGUI._discard_pending_live_statuses(self)
+            self._set_live_status(f"LIVE: switching to {Path(directory).name}")
             self._start_live_watcher(directory)
 
     def browse_layer(self):
@@ -879,10 +903,12 @@ class ContextorGUI:
         try:
             identity = ContextorGUI._refresh_repo_identity(self, path)
         except RepositoryIdentityError as exc:
-            self._set_live_status(f"LIVE identity error: {exc}")
+            if ContextorGUI._is_selected_live_repository(self, path):
+                self._set_live_status(f"LIVE identity error: {exc}")
             return
         if identity is None:
-            self._set_live_status("LIVE: repository not registered; run an analysis")
+            if ContextorGUI._is_selected_live_repository(self, path):
+                self._set_live_status("LIVE: repository not registered; run an analysis")
             return
         watchers = getattr(self, "live_watchers", None)
         if watchers is None:
@@ -896,8 +922,15 @@ class ContextorGUI:
 
         existing_watcher = watchers.get(identity.repo_id)
         if existing_watcher is not None:
-            self.live_watcher = existing_watcher
-            self.live_event_feed = feeds.get(identity.repo_id)
+            existing_client = clients.get(identity.repo_id)
+            if ContextorGUI._is_selected_live_repository(self, path):
+                self.live_watcher = existing_watcher
+                self.live_event_feed = feeds.get(identity.repo_id)
+                if existing_client is not None:
+                    self.live_client = existing_client
+                self._set_live_status(
+                    f"[{identity.repo_name}] LIVE: shared state attached; watcher active"
+                )
             if getattr(self, "_live_start_retry_after_id", None) is not None:
                 if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                     try:
@@ -921,10 +954,11 @@ class ContextorGUI:
             if "client_kind" in parameters:
                 connect_kwargs["client_kind"] = "desktop"
             client = connect_or_start(path, **connect_kwargs)
+            clients[identity.repo_id] = client
             if getattr(self, "_closing", False):
                 return
-            self.live_client = client
-            clients[identity.repo_id] = client
+            if ContextorGUI._is_selected_live_repository(self, path):
+                self.live_client = client
             cache = migrate_legacy_snapshot(path)
             if getattr(self, "_live_start_retry_after_id", None) is not None:
                 if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
@@ -937,7 +971,8 @@ class ContextorGUI:
         except SecondDesktopActive as exc:
             self._live_start_retry_attempt = 0
             self._live_start_retry_after_id = None
-            self._set_live_status(f"LIVE: {exc}")
+            if ContextorGUI._is_selected_live_repository(self, path):
+                self._set_live_status(f"LIVE: {exc}")
             return
         except (OSError, EOFError, RuntimeError, TimeoutError, RepositoryIdentityError) as exc:
             if getattr(self, "_closing", False):
@@ -947,9 +982,10 @@ class ContextorGUI:
             if current_attempt < LIVE_START_MAX_ATTEMPTS:
                 delay_idx = min(current_attempt - 1, len(LIVE_START_RETRY_DELAYS_MS) - 1)
                 delay_ms = LIVE_START_RETRY_DELAYS_MS[delay_idx]
-                self._set_live_status(
-                    f"LIVE connection delayed; retrying ({current_attempt + 1}/{LIVE_START_MAX_ATTEMPTS})..."
-                )
+                if ContextorGUI._is_selected_live_repository(self, path):
+                    self._set_live_status(
+                        f"LIVE connection delayed; retrying ({current_attempt + 1}/{LIVE_START_MAX_ATTEMPTS})..."
+                    )
                 if hasattr(self, "root") and hasattr(self.root, "after"):
                     self._live_start_retry_after_id = self.root.after(
                         delay_ms, lambda: ContextorGUI._start_live_watcher(self, path, initial_seq=initial_seq)
@@ -957,7 +993,8 @@ class ContextorGUI:
                 return
             self._live_start_retry_attempt = 0
             self._live_start_retry_after_id = None
-            self._set_live_status(f"LIVE connection error: {exc}")
+            if ContextorGUI._is_selected_live_repository(self, path):
+                self._set_live_status(f"LIVE connection error: {exc}")
             return
 
         from contextor.core.analysis.state_manager import load_engine_state
@@ -976,9 +1013,11 @@ class ContextorGUI:
             state_id = getattr(state, "state_id", None)
             if state_revision is not None and live_revision == int(state_revision):
                 if state_id and getattr(live_state, "state_id", None) == state_id:
-                    self._set_live_status("LIVE: shared state attached; watcher active")
+                    if ContextorGUI._is_selected_live_repository(self, path):
+                        self._set_live_status("LIVE: shared state attached; watcher active")
                 else:
-                    self._set_live_status("LIVE: generation conflict; analysis required")
+                    if ContextorGUI._is_selected_live_repository(self, path):
+                        self._set_live_status("LIVE: generation conflict; analysis required")
                     return
             else:
                 startup_lease = None
@@ -991,9 +1030,10 @@ class ContextorGUI:
                         poll_interval=0.01,
                     )
                 except FullAnalysisBusyError:
-                    self._set_live_status(
-                        "LIVE: canonical writer busy; cache publish skipped"
-                    )
+                    if ContextorGUI._is_selected_live_repository(self, path):
+                        self._set_live_status(
+                            "LIVE: canonical writer busy; cache publish skipped"
+                        )
                 else:
                     try:
                         published = client.publish(
@@ -1006,22 +1046,34 @@ class ContextorGUI:
                         isinstance(published, dict)
                         and published.get("status") == "ok"
                     ):
-                        self._set_live_status(
-                            "LIVE: shared state published; watcher active"
-                        )
+                        if ContextorGUI._is_selected_live_repository(self, path):
+                            self._set_live_status(
+                                "LIVE: shared state published; watcher active"
+                            )
                     else:
-                        self._set_live_status(
-                            "LIVE: shared state attach failed; analysis required"
-                        )
+                        if ContextorGUI._is_selected_live_repository(self, path):
+                            self._set_live_status(
+                                "LIVE: shared state attach failed; analysis required"
+                            )
         else:
-            self._set_live_status("LIVE: no snapshot; waiting for analysis")
+            if ContextorGUI._is_selected_live_repository(self, path):
+                self._set_live_status("LIVE: no snapshot; waiting for analysis")
         existing_watcher = watchers.get(identity.repo_id)
         if existing_watcher is not None:
-            self.live_watcher = existing_watcher
-            self.live_event_feed = feeds.get(identity.repo_id)
+            existing_client = clients.get(identity.repo_id)
+            if ContextorGUI._is_selected_live_repository(self, path):
+                self.live_watcher = existing_watcher
+                self.live_event_feed = feeds.get(identity.repo_id)
+                if existing_client is not None:
+                    self.live_client = existing_client
+                self._set_live_status(
+                    f"[{identity.repo_name}] LIVE: shared state attached; watcher active"
+                )
             return
 
         def status_callback(message, event=None, name=identity.repo_name):
+            if not ContextorGUI._is_selected_live_repository(self, path):
+                return
             if event is None and (message.startswith("LIVE update successful:") or message.startswith("Updating LIVE:")):
                 return
             cat = event.get("category", "LIVE_STATE") if isinstance(event, dict) else "LIVE_STATE"
@@ -1036,8 +1088,9 @@ class ContextorGUI:
             self._set_live_status(msg, category=cat, event=event)
 
         def on_reconnect(new_client):
-            self.live_client = new_client
             self.live_clients[identity.repo_id] = new_client
+            if ContextorGUI._is_selected_live_repository(self, path):
+                self.live_client = new_client
             feed = feeds.get(identity.repo_id)
             if feed is not None:
                 feed.client = new_client
@@ -1052,7 +1105,7 @@ class ContextorGUI:
 
         if getattr(self, "_closing", False):
             return
-        self.live_watcher = DesktopLiveWatcher(
+        watcher = DesktopLiveWatcher(
             path,
             client,
             owner_pid=os.getpid(),
@@ -1076,14 +1129,16 @@ class ContextorGUI:
                 status_callback,
             )
 
-        self.live_event_feed = feed
-        watchers[identity.repo_id] = self.live_watcher
+        watchers[identity.repo_id] = watcher
         feeds[identity.repo_id] = feed
+        if ContextorGUI._is_selected_live_repository(self, path):
+            self.live_watcher = watcher
+            self.live_event_feed = feed
         if hasattr(feed, "replay_authority_events"):
             feed.replay_authority_events()
         if getattr(self, "_closing", False):
             return
-        self.live_watcher.start()
+        watcher.start()
         feed.start()
 
     def _refresh_repo_identity(self, path):
diff --git a/tests/test_gui_live_startup.py b/tests/test_gui_live_startup.py
index ee08f52..bbeb0ac 100644
--- a/tests/test_gui_live_startup.py
+++ b/tests/test_gui_live_startup.py
@@ -518,6 +518,38 @@ def test_duplicate_watcher_prevented(tmp_path, monkeypatch):
     assert controller._live_start_retry_attempt == 0
 
 
+def test_reselecting_existing_watcher_restores_client_feed_and_status(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    registry = PersistentIdentityRegistry(str(repo))
+    controller = _make_controller(repo)
+    existing_watcher = SimpleNamespace()
+    existing_client = SimpleNamespace(name="existing-client")
+    existing_feed = SimpleNamespace(client=existing_client)
+    controller.live_watchers[registry.repo_id] = existing_watcher
+    controller.live_event_feeds[registry.repo_id] = existing_feed
+    controller.live_clients[registry.repo_id] = existing_client
+    controller.live_watcher = SimpleNamespace(name="stale-watcher")
+    controller.live_event_feed = SimpleNamespace(name="stale-feed")
+    controller.live_client = SimpleNamespace(name="stale-client")
+    connect_calls = []
+    monkeypatch.setattr(
+        gui,
+        "connect_or_start",
+        lambda *args, **kwargs: connect_calls.append((args, kwargs)),
+    )
+
+    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
+
+    assert connect_calls == []
+    assert controller.live_client is existing_client
+    assert controller.live_watcher is existing_watcher
+    assert controller.live_event_feed is existing_feed
+    assert controller._statuses == [
+        f"[{repo.name}] LIVE: shared state attached; watcher active"
+    ]
+
+
 def test_shutdown_cancels_pending_retry(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
     repo.mkdir()
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index 7f9c18b..3caad31 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -416,22 +416,39 @@ def test_browse_repository_switches_live_to_selected_registered_repo(
     second.mkdir()
     PersistentIdentityRegistry(str(first))
     second_registry = PersistentIdentityRegistry(str(second))
-    calls = []
+    status_queue = gui.Queue()
+    status_queue.put({"message": "stale LIVE status"})
+    events = []
 
     controller = SimpleNamespace(
         repo_path_var=_LiveIntegrationFakeVar(),
         layer_path_var=_LiveIntegrationFakeVar(),
-        _start_live_watcher=lambda path: calls.append(path),
+        _live_status_queue=status_queue,
+        _set_live_status=lambda message: events.append(
+            ("status", message, status_queue.qsize())
+        ),
+        _start_live_watcher=lambda path: events.append(
+            ("start", path, status_queue.qsize())
+        ),
     )
     monkeypatch.setattr(gui.filedialog, "askdirectory", lambda: str(second))
-    monkeypatch.setattr(gui, "save_state", lambda **payload: calls.append(payload))
+    monkeypatch.setattr(
+        gui,
+        "save_state",
+        lambda **payload: events.append(("save", payload)),
+    )
 
     gui.ContextorGUI.browse_repository(controller)
 
     selected = str(second).replace("\\", "/")
     assert controller.repo_path_var.value == selected
     assert controller.layer_path_var.value == ""
-    assert calls == [{"repository": selected}, selected]
+    assert status_queue.empty()
+    assert events == [
+        ("save", {"repository": selected}),
+        ("status", f"LIVE: switching to {second.name}", 0),
+        ("start", selected, 0),
+    ]
     assert second_registry.repo_id != read_repository_identity(first).repo_id
 
 
@@ -497,6 +514,106 @@ def test_switching_repositories_keeps_previous_watcher_active(tmp_path, monkeypa
     assert len([event for event in events if event[0] == "start"]) == 2
 
 
+def test_inactive_repository_callbacks_do_not_overwrite_selected_live_state(
+    tmp_path, monkeypatch
+):
+    first = tmp_path / "first"
+    second = tmp_path / "second"
+    first.mkdir()
+    second.mkdir()
+    first_registry = PersistentIdentityRegistry(str(first))
+    second_registry = PersistentIdentityRegistry(str(second))
+    statuses = []
+    clients_by_path = {}
+    watchers_by_path = {}
+    feeds_by_path = {}
+
+    class Client:
+        def __init__(self, root):
+            self.root = str(root)
+
+    class Watcher:
+        def __init__(
+            self, root, client, *, on_status=None, on_reconnect=None, **_kwargs
+        ):
+            self.root = str(root)
+            self.client = client
+            self.on_status = on_status
+            self.on_reconnect = on_reconnect
+            watchers_by_path[self.root] = self
+
+        def start(self):
+            pass
+
+        def stop(self):
+            pass
+
+    class EventFeed:
+        def __init__(self, client, on_status, **_kwargs):
+            self.client = client
+            self.on_status = on_status
+            feeds_by_path[client.root] = self
+
+        def start(self):
+            pass
+
+        def stop(self):
+            pass
+
+    monkeypatch.setattr(
+        gui,
+        "connect_or_start",
+        lambda root, **_kwargs: clients_by_path.setdefault(str(root), Client(root)),
+    )
+    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
+    monkeypatch.setattr(gui, "DesktopLiveEventFeed", EventFeed)
+    monkeypatch.setattr(gui, "migrate_legacy_snapshot", lambda root: str(root))
+    monkeypatch.setattr(
+        "contextor.core.analysis.state_manager.load_engine_state",
+        lambda *_args, **_kwargs: None,
+    )
+
+    controller = SimpleNamespace(
+        repo_path_var=SimpleNamespace(get=lambda: str(first)),
+        live_watcher=None,
+        live_event_feed=None,
+        live_watchers={},
+        live_event_feeds={},
+        live_clients={},
+        live_client=None,
+        _set_live_status=lambda message, **_kwargs: statuses.append(message),
+    )
+
+    gui.ContextorGUI._start_live_watcher_blocking(controller, str(first))
+    first_client = controller.live_clients[first_registry.repo_id]
+    first_watcher = controller.live_watchers[first_registry.repo_id]
+    first_feed = controller.live_event_feeds[first_registry.repo_id]
+    statuses.clear()
+    gui.ContextorGUI._start_live_watcher_blocking(controller, str(second))
+    second_watcher = controller.live_watchers[second_registry.repo_id]
+    second_feed = controller.live_event_feeds[second_registry.repo_id]
+
+    assert statuses == []
+    assert controller.live_client is first_client
+    assert controller.live_watcher is first_watcher
+    assert controller.live_event_feed is first_feed
+    assert controller.live_clients[second_registry.repo_id] is clients_by_path[str(second)]
+
+    statuses.clear()
+    second_watcher.on_status("inactive callback", event={"category": "LIVE_STATE"})
+    assert statuses == []
+    first_watcher.on_status("selected callback", event={"category": "LIVE_STATE"})
+    assert statuses == [f"[{first.name}] selected callback"]
+
+    replacement_client = Client(second)
+    second_watcher.on_reconnect(replacement_client)
+    assert controller.live_clients[second_registry.repo_id] is replacement_client
+    assert second_feed.client is replacement_client
+    assert controller.live_client is first_client
+    assert controller.live_watcher is first_watcher
+    assert controller.live_event_feed is first_feed
+
+
 def test_closing_gui_stops_every_repository_watcher_and_feed(monkeypatch):
     stopped = []
 
IMPLEMENTED_CONTRACT=YES; A-F covered by focused regressions; G remains covered by existing test_switching_repositories_keeps_previous_watcher_active; tests intentionally not executed
CONTEXTOR_REVISION_BEFORE_EDIT=1432
CONTEXTOR_REVISION_AFTER_EDIT=1439
CONTEXTOR_CANONICAL_STATE=fresh
CONTEXTOR_WORKSPACE_SYNC=verified
CONTEXTOR_DIAGNOSTICS=syntax_errors:0/fresh;name_collisions:0/fresh;cycles:0/fresh
CONTEXTOR_DESKTOP_WATCHER_EVENTS=1433:gui.py:UPDATED;1434:gui.py:UNCHANGED;1435:test_gui_live_startup.py:UPDATED;1436:test_live_desktop_integration.py:UPDATED;1437:test_live_desktop_integration.py:UPDATED;1438:gui.py:UPDATED;1439:test_live_desktop_integration.py:UPDATED
CONTEXTOR_HELPER_CALL_CONTEXT=_discard_pending_live_statuses called by browse_repository; _is_selected_live_repository called at 15 sites in _start_live_watcher_blocking
TESTS_RUN=NO
FULL_SUITE_RUN=NO
ANALYZE_PROJECT_RUN_COUNT=0
UPDATE_FILE_CALLED=NO
RESTART_PERFORMED=NO
FIX_DESIGNED_BY_AGENT=NO
NEXT_STEP=Wait for proceduj before validation.

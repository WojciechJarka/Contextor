# L32H2G2E — current task

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
- C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py
- C:\Temp\Contextor_Repo\contextor\ui\gui.py
- C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py
- C:\Temp\Contextor_Repo\tests\test_live_activity_status.py

C:\Temp\Contextor_Repo\walkthrough.md is the report only.

## SOURCE_GATE

DIRECT_EVIDENCE: Before edits, Contextor fetched complete AST implementations of CanonicalLiveServer._execute_committed_publish, DesktopLiveEventFeed._message, and ContextorGUI._set_live_status with workspace_sync=verified and canonical_state=fresh at LIVE revision 308. Source/test files were clean; only walkthrough.md was modified. Exact patch anchors matched.

## RED_RESULTS

Five expected RED failures before production edits: both real IPC spoofing cases failed at event["origin_verified"] with KeyError; both watcher cases attributed unverified claims to MCP/Desktop analysis; GUI projected claimed mcp_analysis as source and lacked claimed_source/origin_verified. No fixture failure. Command: .venv Python pytest -q on the three new test nodes; 5 failed as intended.

## COMMITTED_PUBLISH_EVENT_PROVENANCE

CODE_PATH_PROVED: Successful committed snapshot publish now emits origin_verified=False alongside all prior event keys and values. No change to ACK, validation, memory-only publish, sequence, or snapshot publication.

## WATCHER_UNVERIFIED_ORIGIN_PRESENTATION

CONTRACT_PROVED: DesktopLiveEventFeed._message renders each unverified publish as `[LIVE] Committed state installed (rev 2); publisher identity unverified`. The existing AUTHORITY/MCP_CALL branches and historical publish routing remain intact.

## GUI_UNVERIFIED_SOURCE_PROJECTION

CONTRACT_PROVED: For publish with origin_verified=False, last_live_state.source is `unverified`; claimed_source retains raw claim and origin_verified is False. Revision, status and timestamp retain their prior values. Other events retain the original dictionary shape.

## REAL_IPC_SPOOFED_ORIGIN

CONTRACT_PROVED by spawned-process tests: mcp_analysis and desktop_analysis are accepted as raw origin claims while a legitimate writer holds full_analysis.lock; child cannot acquire writer lease. The emitted event preserves the claim but explicitly marks it unverified. LIVE state and committed snapshot match revision 2/state_id sid. Snapshot metadata and FileStateManager revision remain unchanged by publish.

## HISTORICAL_EVENT_COMPATIBILITY

CONTRACT_PROVED: Historical publish events lacking origin_verified still render the prior origin-specific watcher message and retain the previous GUI last_live_state dictionary shape.

## UPDATE_FILE_ATTRIBUTION_COMPATIBILITY

CONTRACT_PROVED: update_file event with origin_verified=False still projects desktop_watcher as source and preserves watcher update wording.

## G2D_ACK_COMPATIBILITY

CONTRACT_PROVED by existing targeted tests: already_installed ACK remains origin_verified=False in response and adds no event; real IPC owner ACK and default no-ACK paths pass.

## DUPLICATE_REJECTION_COMPATIBILITY

CONTRACT_PROVED by existing durable tests: default duplicate rejection remains non_monotonic_canonical_revision and event-free. Catch-up publish regressions pass.

## TARGETED_GREEN_RESULTS

- tests/test_durable_verified_publish.py + tests/test_live_activity_status.py: 76 passed.
- tests/test_live_state_ipc.py + tests/test_gui_live_startup.py: 132 passed.
- Total targeted: 208 passed, 0 failed. One dependency deprecation warning in each run.
- py_compile: all five modified Python files passed.
- git diff --check scoped to all five changed source/test files: passed. Running it across the report itself flags two context blank lines inside the embedded literal diff; the source/test diffs have no whitespace errors.
- No full repository pytest suite run.

## SOURCE_SYNC

DIRECT_EVIDENCE: Post-edit Contextor complete AST source returned workspace_sync=verified and canonical_state=fresh for all three changed production owners at revision 313. No truncation. cycles availability fresh/count 0. Desktop watcher emitted one UPDATED event for each changed source/test file: revisions 309-313.

## LIVE_REVISION_BEFORE_AFTER

Before edit 308, after edit 313, same activity epoch 3f604c8dd0194e9db86bff2e1bc1c6f4; get_live_events(after_revision=308) returned five sequential desktop_watcher events, continuity=continuous, resync_required=false.

## RESTART_REQUIRED

YES for serving MCP/LIVE/Desktop processes to import changed Python code. No restart performed. Fresh Contextor indexing and pytest subprocesses do not certify existing process reload.

## REMAINING_TRUST_BOUNDARY

The raw origin string remains unauthenticated caller input. The event records committed LIVE state installation, not verified canonical writer identity. This task changes provenance labeling and presentation only; no writer admission protocol change.

## FULL_DIFFS_FOR_ALL_CHANGED_FILES

diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 5e3b69f..2b57458 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -1441,6 +1441,7 @@ class CanonicalLiveServer:
                         "operation": "publish",
                         "source": source,
                         "origin": source,
+                        "origin_verified": False,
                         "canonical_revision": committed_revision,
                         "revision": committed_revision,
                         "status": "PUBLISHED",
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 5d24349..f0cb567 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -1134,6 +1134,21 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
                 return f"[MCP] {tool} (failed: {err})"
             return f"[MCP] {tool}"
 
+        if (
+            event.get("operation") == "publish"
+            and event.get("origin_verified") is False
+        ):
+            revision = event.get("canonical_revision")
+            suffix = (
+                f" (rev {revision})"
+                if revision is not None
+                else ""
+            )
+            return (
+                "[LIVE] Committed state installed"
+                f"{suffix}; publisher identity unverified"
+            )
+
         origin = event.get("origin") or event.get("source")
         if origin not in {"mcp", "mcp_analysis", "desktop_analysis", "desktop_watcher", "desktop"}:
             return None
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 10367ba..16d138c 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -1539,13 +1539,27 @@ class ContextorGUI:
         )
 
         if canonical_operation:
+            claimed_source = event.get("source") or event.get("origin")
+            unverified_publish = (
+                event.get("operation") == "publish"
+                and event.get("origin_verified") is False
+            )
+
             self.last_live_state = {
                 "revision": event.get("canonical_revision"),
                 "status": event.get("status"),
                 "timestamp": event.get("timestamp"),
-                "source": event.get("source") or event.get("origin"),
+                "source": (
+                    "unverified"
+                    if unverified_publish
+                    else claimed_source
+                ),
             }
 
+            if unverified_publish:
+                self.last_live_state["claimed_source"] = claimed_source
+                self.last_live_state["origin_verified"] = False
+
         item = {
             "formatted": formatted,
             "category": category,
diff --git a/tests/test_durable_verified_publish.py b/tests/test_durable_verified_publish.py
index 325c64b..9cf6305 100644
--- a/tests/test_durable_verified_publish.py
+++ b/tests/test_durable_verified_publish.py
@@ -31,7 +31,9 @@ def _hold_snapshot_lock(lock_path, ready, release):
         _release_lock(fd)
 
 
-def _raw_publish_without_writer_lease(repo_path, endpoint, response_queue):
+def _raw_publish_without_writer_lease(
+    repo_path, endpoint, response_queue, origin="unleased_raw_ipc"
+):
     from contextor.core.analysis.full_analysis_lease import (
         FullAnalysisBusyError,
         acquire_full_analysis,
@@ -49,12 +51,91 @@ def _raw_publish_without_writer_lease(repo_path, endpoint, response_queue):
         lease_denied = False
     response = LiveStateClient(endpoint).publish(
         SimpleNamespace(state_id="sid", revision=2),
-        origin="unleased_raw_ipc",
+        origin=origin,
         timeout=10.0,
     )
     response_queue.put((lease_denied, response))
 
 
+@pytest.mark.parametrize("claimed_origin", ["mcp_analysis", "desktop_analysis"])
+def test_raw_ipc_publish_origin_is_explicitly_unverified(
+    durable_harness, claimed_origin
+):
+    from contextor.core.analysis.full_analysis_lease import (
+        acquire_full_analysis,
+        release_full_analysis,
+    )
+    from contextor.core.analysis.state_manager import FileStateManager
+
+    durable_harness.commit(1)
+    initial = load_snapshot(
+        durable_harness.cache,
+        expected_repo_id=durable_harness.identity.repo_id,
+        expected_root_path=durable_harness.identity.root_path,
+    )
+    server = durable_harness.server(state=initial[0], revision=1)
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    lease = acquire_full_analysis(
+        durable_harness.repo, owner="legitimate-full-writer", timeout=5.0
+    )
+    try:
+        _, committed = durable_harness.commit(2, value="owner-generation")
+        metadata_before = read_metadata(durable_harness.cache)
+        context = get_context("spawn")
+        response_queue = context.Queue()
+        raw = context.Process(
+            target=_raw_publish_without_writer_lease,
+            args=(
+                str(durable_harness.repo), server.endpoint, response_queue,
+                claimed_origin,
+            ),
+        )
+        raw.start()
+        try:
+            lease_denied, response = response_queue.get(timeout=12.0)
+            raw.join(5.0)
+        finally:
+            if raw.is_alive():
+                raw.terminate()
+                raw.join(5.0)
+
+        assert raw.exitcode == 0
+        assert lease_denied is True
+        assert response == {
+            "status": "ok", "revision": 2, "seq": 1,
+            "source": "committed_snapshot",
+        }
+        assert server._state.state_id == committed.state_id
+        assert server._state.revision == committed.revision == 2
+        assert server._state.value == "owner-generation"
+        assert len(server._events) == 1
+        event = server._events[0]
+        assert event["source"] == event["origin"] == claimed_origin
+        assert event["category"] == "LIVE_STATE"
+        assert event["operation"] == "publish"
+        assert event["status"] == "PUBLISHED"
+        assert event["canonical_revision"] == event["revision"] == 2
+        assert event["seq"] == 1
+        assert event["timestamp"]
+        assert event["origin_verified"] is False
+        disk = load_snapshot(
+            durable_harness.cache,
+            expected_repo_id=durable_harness.identity.repo_id,
+            expected_root_path=durable_harness.identity.root_path,
+        )
+        assert disk[1] == metadata_before
+        assert disk[0].state_id == committed.state_id
+        assert disk[0].revision == 2
+        assert FileStateManager(str(durable_harness.cache)).revision == 2
+        assert read_metadata(durable_harness.cache) == metadata_before
+    finally:
+        release_full_analysis(lease)
+        server.close()
+        thread.join(5.0)
+    assert not thread.is_alive()
+
+
 @pytest.fixture
 def durable_harness(tmp_path):
     repo = tmp_path / "repo"
diff --git a/tests/test_live_activity_status.py b/tests/test_live_activity_status.py
index 112cdd3..2f5f948 100644
--- a/tests/test_live_activity_status.py
+++ b/tests/test_live_activity_status.py
@@ -209,6 +209,89 @@ def test_desktop_feed_formats_committed_diagnostic_delta_without_replacing_synta
     )
 
 
+@pytest.mark.parametrize("claimed_origin", ["mcp_analysis", "desktop_analysis"])
+def test_feed_does_not_attribute_unverified_committed_publish(claimed_origin):
+    feed = DesktopLiveEventFeed(
+        SimpleNamespace(), lambda *_args, **_kwargs: None, initial_seq=0
+    )
+    event = {
+        "category": "LIVE_STATE", "operation": "publish",
+        "origin": claimed_origin, "source": claimed_origin,
+        "origin_verified": False, "canonical_revision": 2,
+        "status": "PUBLISHED",
+    }
+    assert feed._message(event) == (
+        "[LIVE] Committed state installed (rev 2); publisher identity unverified"
+    )
+    historical = dict(event)
+    del historical["origin_verified"]
+    expected_historical = (
+        "MCP: analysis published shared LIVE state (rev 2)"
+        if claimed_origin == "mcp_analysis"
+        else "[LIVE] Desktop analysis published shared LIVE state (rev 2)"
+    )
+    assert feed._message(historical) == expected_historical
+
+
+def test_gui_projects_unverified_publish_and_preserves_update_attribution():
+    controller = SimpleNamespace(
+        live_status_var=_FakeVar(),
+        _live_status_queue=queue.Queue(),
+        _live_status_draining=False,
+        last_live_state=None,
+    )
+    event = {
+        "category": "LIVE_STATE", "operation": "publish",
+        "source": "mcp_analysis", "origin": "mcp_analysis",
+        "origin_verified": False, "canonical_revision": 2,
+        "status": "PUBLISHED", "timestamp": "2026-01-01T12:00:00+00:00",
+    }
+    gui.ContextorGUI._set_live_status(
+        controller, "[LIVE] Committed state installed", event=event
+    )
+    assert controller.last_live_state == {
+        "revision": 2,
+        "status": "PUBLISHED",
+        "timestamp": "2026-01-01T12:00:00+00:00",
+        "source": "unverified",
+        "claimed_source": "mcp_analysis",
+        "origin_verified": False,
+    }
+
+    historical = dict(event)
+    del historical["origin_verified"]
+    gui.ContextorGUI._set_live_status(
+        controller, "[LIVE] Historical publish", event=historical
+    )
+    assert controller.last_live_state == {
+        "revision": 2,
+        "status": "PUBLISHED",
+        "timestamp": "2026-01-01T12:00:00+00:00",
+        "source": "mcp_analysis",
+    }
+
+    update = {
+        **event, "operation": "update_file", "source": "desktop_watcher",
+        "origin": "desktop_watcher", "status": "UPDATED",
+        "canonical_revision": 3,
+    }
+    gui.ContextorGUI._set_live_status(
+        controller, "[LIVE] Watcher updated file", event=update
+    )
+    assert controller.last_live_state == {
+        "revision": 3,
+        "status": "UPDATED",
+        "timestamp": "2026-01-01T12:00:00+00:00",
+        "source": "desktop_watcher",
+    }
+    feed = DesktopLiveEventFeed(
+        SimpleNamespace(), lambda *_args, **_kwargs: None, initial_seq=0
+    )
+    assert feed._message({**update, "file_path": "pkg/change.py"}) == (
+        "[LIVE] Watcher updated change.py (rev 3)"
+    )
+
+
 def test_desktop_feed_formats_generic_diagnostic_delta_and_ignores_malformed_payload():
     feed = DesktopLiveEventFeed(SimpleNamespace(), lambda *_args, **_kwargs: None, initial_seq=0)
     event = {

## FINAL_VERDICT

L32H2G2E_TARGETED_PASS


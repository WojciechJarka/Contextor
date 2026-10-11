# L32H2G2D_OPT_IN_ALREADY_INSTALLED_ACK

## FILES_CHANGED_THIS_TASK

Changed production and test files:

- C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
- C:\Temp\Contextor_Repo\contextor\core\api\facade.py
- C:\Temp\Contextor_Repo\contextor\ui\gui.py
- C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py
- C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py
- C:\Temp\Contextor_Repo\tests\test_live_single_file_reuse.py
- C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py
- C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py

This report is the only additional changed file and is excluded from source/test FILES_CHANGED.

## SOURCE_GATE

Contextor MCP was queried first, including current tool discovery and the deferred source/lineage-capable tools. Pre-edit canonical source was at LIVE revision 301 and reported workspace_sync=verified for the IPC and facade symbols. Exact current anchors matched the auditor-supplied patch.

Post-edit Contextor evidence at revision 306:
- CanonicalLiveServer._execute_committed_publish: complete AST-bounded implementation, no partial source; workspace_sync=verified.
- LiveStateClient.publish: complete AST-bounded implementation; workspace_sync=verified.
- ContextorFacade._analyze_single_file_uncoordinated: complete AST-bounded implementation; workspace_sync=verified.
- ContextorFacade.analyze_project: signature and exact post-edit publication range 1135-1193 fetched; workspace_sync=verified. Full method fetch returned confirmation_required due its 32 KiB estimated size, so the full method was not represented as retrieved. The changed response path itself was fetched as a complete exact range.
- ContextorGUI._start_live_watcher_blocking: complete exact canonical source range, lines 1641-1969; signature fetch reports workspace_sync=verified.
- GUI post-edit publish/status range 1790-1852 fetched in full and matches the local changed anchor.
No preview or truncated range was treated as a complete implementation. Search was used only to confirm exact local anchors.

Planned changes were recorded in walkthrough.md before source editing. No unapproved source or test paths appear in the final worktree status.

## RED_RESULTS

Before production changes, the focused regression command produced 6 expected failures and 6 passes:
- Expected failures: exact installed ACK server response; real IPC owner ACK; opt-in client request payload; full facade caller; scoped facade caller; GUI startup caller.
- The six parameterized nonmatching/unavailable-generation rejection cases already passed.
The failing cases demonstrated the missing opt-in behavior: duplicate publish was rejected or the caller/client did not send the ACK field.

## SERVER_OPT_IN_ACK

The supplied exact condition was added inside the existing committed-revision duplicate branch, after existing committed-snapshot and candidate generation identity validation.

For acknowledge_installed=True only, the server returns an ACK when:
- committed_revision equals previous_revision;
- current LIVE RAM state exists;
- current LIVE RAM state_id equals committed snapshot state_id;
- current LIVE RAM revision equals committed revision.

Response fields: status=ok, revision, existing activity seq, source=committed_snapshot, already_installed=True, origin_verified=False. Otherwise the original non_monotonic_canonical_revision error is returned. Default behavior remains rejection.

The ACK returns before event construction, activity-sequence advancement, LIVE state assignment, revision assignment, or persistence. It does not replace or rewrite event origin.

## CLIENT_DEFAULT_COMPATIBILITY

LiveStateClient.publish now has keyword-only acknowledge_installed=False. With the default, it executes the original request call with only state, origin, and timeout. With opt-in true, it adds acknowledge_installed=True. LiveStateClient.request and IPC authentication were not changed.

## COMMITTED_GENERATION_VALIDATION

All previous checks remain before the new duplicate ACK branch:
- candidate revision and state_id are required and validated;
- committed snapshot must exist and contain valid revision/state_id metadata;
- committed snapshot object's identity and revision must match metadata;
- request candidate identity must match the committed snapshot.
Catch-up publication for a newer committed generation remains on the original path. Default duplicate rejection remains covered by the existing durable publish tests.

## LIVE_RAM_IDENTITY_VALIDATION

The ACK additionally validates current RAM state identity and revision against the committed snapshot. Regression cases reject:
- wrong request state_id;
- uncommitted candidate revision;
- LIVE state_id mismatch;
- LIVE revision mismatch;
- candidate older than LIVE;
- missing committed snapshot.
All six rejection parameters passed in both the pre-edit gate and the final targeted suite.

## NO_EVENT_OR_DURABLE_MUTATION

The server branch returns before event creation and all canonical assignment. Tests verify unchanged RAM state, revision, event list, activity sequence, durable snapshot metadata, snapshot identity/revision, and FileStateManager revision. The real IPC front-run test also verifies the persisted event retains its original raw publisher origin; the ACK does not rewrite it or append another event.

## RAW_FRONT_RUN_OWNER_ACK

The new deterministic real-IPC regression retains the legitimate writer lease while a raw client front-runs the already committed generation. The owner then opts in and receives the server-validated already_installed ACK. The test verifies one original publish event remains, its origin is unchanged, and LIVE RAM, snapshot, metadata, and FileState identities/revisions agree.

The pre-existing real IPC raw-front-run reachability test remains and passes. This task does not authenticate the raw request or resolve event-origin spoofing.

## ORIGIN_UNVERIFIED_SEMANTICS

The ACK explicitly reports origin_verified=False. Full and scoped facade results preserve status=success and the returned revision when the ACK has no resync_required flag, while reporting the warning:
LIVE generation was already installed; event origin is not verified.

If resync_required=True, the existing recovery_required branch takes precedence. GUI startup displays:
LIVE: shared generation already installed; event origin unverified
and does not schedule recovery for the validated ACK without resync_required.

## FULL_SCOPED_GUI_CALLER_RESULTS

The confirmed production callers opt in:
- full project analysis: client.publish(state, origin=origin, acknowledge_installed=True);
- scoped single-file analysis: hydrated.client.publish(analysis_state, origin="scoped_analysis", timeout=5.0, acknowledge_installed=True);
- GUI startup publish: client.publish(state, origin="desktop_analysis", acknowledge_installed=True).

Focused caller regressions verify that the full/scoped/startup writer lease remains held during its synchronous publication request. GUI startup releases its lease at the same existing boundary and does not enter recovery for a validated ACK.

## EXISTING_DUPLICATE_CONTRACT

The complete tests/test_durable_verified_publish.py file passed, including strict default duplicate rejection, committed-generation catch-up after a prior publish failure, cross-process snapshot-store locking, and no extra durable write by publish. The client default payload test confirms exact backward-compatible request fields. Existing recovery-required and timeout interpretations also passed their selected tests.

## TARGETED_GREEN_RESULTS

RED-to-GREEN focused gate: 12 passed, 1 existing Authlib deprecation warning.

Combined selected targeted gate: 51 passed, 1 existing Authlib deprecation warning. It covered:
- all tests in test_durable_verified_publish.py;
- all tests in test_live_single_file_reuse.py;
- full/scoped writer lease and single-publication coordination;
- GUI accepted-degraded, rejected/recovery, publication-error, and new already-installed startup behavior;
- MCP timeout, failed publication, and accepted recovery status;
- client timeout and default/opt-in payload;
- queued update idempotency propagation;
- LIVE owner direct update visibility.

No full repository pytest was run.

py_compile passed for all eight changed production/test files using .venv Python. git diff --check passed for all eight; Git emitted only its LF-to-CRLF working-copy normalization warnings.

## SOURCE_SYNC

Post-edit Contextor source evidence is fresh and synchronized at canonical revision 306. Contextor reports canonical_state=fresh, provenance=live, workspace_sync=verified for the fetched production symbols, syntax errors 0, cycles.count=0, and resync_required=false.

LIVE revision advanced 301→306. get_live_events(after_revision=301) reported continuous history and five desktop_watcher updates at revisions 302-306 (the three production files plus two test files). A follow-up query after 306 reported continuity=continuous, revision=306, no resync, and no newer events. No Contextor update_file call or process restart was performed.

## LIVE_REVISION_BEFORE_AFTER

Before edit: revision 301, canonical state fresh, resync_required=false.
After edit: revision 306, canonical state fresh, resync_required=false, event continuity continuous. Latest activity sequence reported 1537.

## FULL_DIFFS_FOR_ALL_CHANGED_FILES

The complete unabridged Git diff for every changed production and test file follows. walkthrough.md is excluded from this source/test diff by instruction.

diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index a07c178..d41b17a 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -1147,7 +1147,11 @@ class ContextorFacade:
                     if client is not None:
                         component_started = time.monotonic()
                         try:
-                            published = client.publish(state, origin=origin)
+                            published = client.publish(
+                                state,
+                                origin=origin,
+                                acknowledge_installed=True,
+                            )
                         finally:
                             publish_ms = (time.monotonic() - component_started) * 1000.0
                         component_started = time.monotonic()
@@ -1165,7 +1169,12 @@ class ContextorFacade:
                                 )
                             else:
                                 live_publish_status = "success"
-                                live_publish_warning = None
+                                live_publish_warning = (
+                                    "LIVE generation was already installed; "
+                                    "event origin is not verified."
+                                    if published.get("already_installed") is True
+                                    else None
+                                )
                         else:
                             live_publish_status = "failed"
                             live_publish_revision = None
@@ -1691,6 +1700,7 @@ class ContextorFacade:
                         analysis_state,
                         origin="scoped_analysis",
                         timeout=5.0,
+                        acknowledge_installed=True,
                     )
                     if isinstance(published, dict) and published.get("status") == "ok":
                         if published.get("resync_required") is True:
@@ -1698,7 +1708,12 @@ class ContextorFacade:
                             warning = published.get("warning") or "LIVE recovery verification required."
                         else:
                             status = "success"
-                            warning = None
+                            warning = (
+                                "LIVE generation was already installed; "
+                                "event origin is not verified."
+                                if published.get("already_installed") is True
+                                else None
+                            )
                         revision = int(published["revision"]) if published.get("revision") is not None else None
                     else:
                         status = "failed"
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index ca89f1f..5e3b69f 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -1404,6 +1404,23 @@ class CanonicalLiveServer:
                         }
 
                     if committed_revision <= previous_revision:
+                        if (
+                            request.get("acknowledge_installed") is True
+                            and committed_revision == previous_revision
+                            and self._state is not None
+                            and getattr(self._state, "state_id", None)
+                            == committed_state_id
+                            and getattr(self._state, "revision", None)
+                            == committed_revision
+                        ):
+                            return {
+                                "status": "ok",
+                                "revision": committed_revision,
+                                "seq": self._activity_seq,
+                                "source": "committed_snapshot",
+                                "already_installed": True,
+                                "origin_verified": False,
+                            }
                         return {
                             "status": "error",
                             "error": "non_monotonic_canonical_revision",
@@ -2559,7 +2576,16 @@ class LiveStateClient:
         *,
         origin: str = "unknown",
         timeout: float = 30.0,
+        acknowledge_installed: bool = False,
     ) -> dict[str, Any]:
+        if acknowledge_installed:
+            return self.request(
+                "publish",
+                timeout=timeout,
+                state=state,
+                origin=origin,
+                acknowledge_installed=True,
+            )
         return self.request(
             "publish", timeout=timeout, state=state, origin=origin
         )
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 2b1ebbd..10367ba 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -1796,6 +1796,7 @@ class ContextorGUI:
                         published = client.publish(
                             state,
                             origin="desktop_analysis",
+                            acknowledge_installed=True,
                         )
                     finally:
                         release_full_analysis(startup_lease)
@@ -1825,9 +1826,15 @@ class ContextorGUI:
                         and published.get("status") == "ok"
                     ):
                         if ContextorGUI._is_selected_live_repository(self, path):
-                            self._set_live_status(
-                                "LIVE: shared state published; watcher active"
-                            )
+                            if published.get("already_installed") is True:
+                                self._set_live_status(
+                                    "LIVE: shared generation already installed; "
+                                    "event origin unverified"
+                                )
+                            else:
+                                self._set_live_status(
+                                    "LIVE: shared state published; watcher active"
+                                )
                     else:
                         if ContextorGUI._is_selected_live_repository(self, path):
                             self._set_live_status(
diff --git a/tests/test_durable_verified_publish.py b/tests/test_durable_verified_publish.py
index 1825161..325c64b 100644
--- a/tests/test_durable_verified_publish.py
+++ b/tests/test_durable_verified_publish.py
@@ -191,6 +191,124 @@ def test_r3_r5_r8_r9_r15_rejections_leave_live_and_event_unchanged(durable_harne
     _assert_unchanged(server, latest)
 
 
+def test_opt_in_ack_confirms_exact_installed_generation_without_mutation(
+    durable_harness,
+):
+    from contextor.core.analysis.state_manager import FileStateManager
+
+    committed_state, committed_metadata = durable_harness.commit(
+        1, value="committed"
+    )
+    server = durable_harness.server(
+        state=committed_state,
+        revision=committed_metadata.revision,
+    )
+    before_server = _unchanged(server)
+    before_disk, before_disk_metadata = load_snapshot(
+        durable_harness.cache,
+        expected_repo_id=durable_harness.identity.repo_id,
+        expected_root_path=durable_harness.identity.root_path,
+    )
+    before_metadata = read_metadata(durable_harness.cache)
+    before_file_state_revision = FileStateManager(
+        str(durable_harness.cache)
+    ).revision
+
+    response = _publish(
+        server,
+        1,
+        acknowledge_installed=True,
+    )
+
+    assert response == {
+        "status": "ok",
+        "revision": 1,
+        "seq": before_server[2],
+        "source": "committed_snapshot",
+        "already_installed": True,
+        "origin_verified": False,
+    }
+    _assert_unchanged(server, before_server)
+    assert server._state is committed_state
+
+    after_disk, after_disk_metadata = load_snapshot(
+        durable_harness.cache,
+        expected_repo_id=durable_harness.identity.repo_id,
+        expected_root_path=durable_harness.identity.root_path,
+    )
+    assert after_disk_metadata == before_disk_metadata
+    assert after_disk_metadata == before_metadata
+    assert after_disk.state_id == before_disk.state_id == "sid"
+    assert after_disk.revision == before_disk.revision == 1
+    assert read_metadata(durable_harness.cache) == before_metadata
+    assert FileStateManager(str(durable_harness.cache)).revision == (
+        before_file_state_revision
+    )
+
+
+@pytest.mark.parametrize(
+    ("case", "expected_error"),
+    [
+        ("wrong_candidate_state_id", "committed_publish_generation_mismatch"),
+        ("uncommitted_candidate_revision", "committed_publish_generation_mismatch"),
+        ("live_state_id_mismatch", "non_monotonic_canonical_revision"),
+        ("live_revision_mismatch", "non_monotonic_canonical_revision"),
+        ("older_than_live", "non_monotonic_canonical_revision"),
+        ("committed_snapshot_missing", "committed_snapshot_unavailable"),
+    ],
+)
+def test_opt_in_ack_rejects_nonmatching_or_unavailable_generation(
+    durable_harness,
+    case,
+    expected_error,
+):
+    committed_state, committed_metadata = durable_harness.commit(1)
+    if case == "committed_snapshot_missing":
+        @contextmanager
+        def unavailable_reader():
+            yield None
+
+        server = durable_harness.server(
+            state=committed_state,
+            revision=1,
+            custom_reader=unavailable_reader,
+        )
+    elif case == "older_than_live":
+        server = durable_harness.server(
+            state=SimpleNamespace(state_id="sid", revision=2),
+            revision=2,
+        )
+    else:
+        server = durable_harness.server(
+            state=committed_state,
+            revision=committed_metadata.revision,
+        )
+
+    candidate_revision = 1
+    candidate_state_id = "sid"
+    if case == "wrong_candidate_state_id":
+        candidate_state_id = "wrong"
+    elif case == "uncommitted_candidate_revision":
+        candidate_revision = 2
+    elif case == "live_state_id_mismatch":
+        server._state = SimpleNamespace(state_id="wrong", revision=1)
+    elif case == "live_revision_mismatch":
+        server._state = SimpleNamespace(state_id="sid", revision=0)
+
+    before = _unchanged(server)
+    response = _publish(
+        server,
+        candidate_revision,
+        state_id=candidate_state_id,
+        acknowledge_installed=True,
+    )
+
+    assert response["status"] == "error"
+    assert response["error"] == expected_error
+    assert response.get("already_installed") is not True
+    _assert_unchanged(server, before)
+
+
 def test_raw_ipc_publish_front_runs_lease_owner_same_committed_generation(
     durable_harness,
 ):
@@ -297,6 +415,114 @@ def test_raw_ipc_publish_front_runs_lease_owner_same_committed_generation(
     assert not thread.is_alive()
 
 
+def test_raw_ipc_front_run_gets_validated_owner_already_installed_ack(
+    durable_harness,
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
+    server = durable_harness.server(
+        state=initial[0],
+        revision=initial[1].revision,
+    )
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    lease = acquire_full_analysis(
+        durable_harness.repo,
+        owner="legitimate-full-writer",
+        timeout=5.0,
+    )
+    try:
+        candidate, committed = durable_harness.commit(
+            2, value="owner-generation"
+        )
+        context = get_context("spawn")
+        response_queue = context.Queue()
+        raw = context.Process(
+            target=_raw_publish_without_writer_lease,
+            args=(str(durable_harness.repo), server.endpoint, response_queue),
+        )
+        raw.start()
+        try:
+            lease_denied, raw_response = response_queue.get(timeout=12.0)
+            raw.join(5.0)
+        finally:
+            if raw.is_alive():
+                raw.terminate()
+                raw.join(5.0)
+
+        assert raw.exitcode == 0
+        assert lease_denied is True
+        assert raw_response == {
+            "status": "ok",
+            "revision": 2,
+            "seq": 1,
+            "source": "committed_snapshot",
+        }
+        before_owner_ack = _unchanged(server)
+        disk_before_ack = load_snapshot(
+            durable_harness.cache,
+            expected_repo_id=durable_harness.identity.repo_id,
+            expected_root_path=durable_harness.identity.root_path,
+        )
+        metadata_before_ack = read_metadata(durable_harness.cache)
+        file_state_revision_before_ack = FileStateManager(
+            str(durable_harness.cache)
+        ).revision
+
+        owner_response = client.publish(
+            candidate,
+            origin="legitimate_full_writer",
+            timeout=10.0,
+            acknowledge_installed=True,
+        )
+
+        assert owner_response == {
+            "status": "ok",
+            "revision": 2,
+            "seq": 1,
+            "source": "committed_snapshot",
+            "already_installed": True,
+            "origin_verified": False,
+        }
+        _assert_unchanged(server, before_owner_ack)
+        assert server._state.state_id == committed.state_id == "sid"
+        assert server._state.revision == committed.revision == 2
+        assert server._state.value == "owner-generation"
+        assert len(server._events) == 1
+        assert server._events[0]["origin"] == "unleased_raw_ipc"
+        assert server._events[0]["canonical_revision"] == 2
+
+        disk_after_ack = load_snapshot(
+            durable_harness.cache,
+            expected_repo_id=durable_harness.identity.repo_id,
+            expected_root_path=durable_harness.identity.root_path,
+        )
+        assert disk_after_ack[1] == disk_before_ack[1] == metadata_before_ack
+        assert disk_after_ack[0].state_id == server._state.state_id
+        assert disk_after_ack[0].revision == server._state.revision == 2
+        assert FileStateManager(str(durable_harness.cache)).revision == (
+            file_state_revision_before_ack
+        )
+        assert server._activity_seq == 1
+        assert len(server._events) == 1
+    finally:
+        release_full_analysis(lease)
+        server.close()
+        thread.join(5.0)
+    assert not thread.is_alive()
+
+
 def test_r4_r12_r29_durable_catch_up_after_earlier_publish_failure(durable_harness):
     durable_harness.commit(1)
     failed = durable_harness.server(
diff --git a/tests/test_full_analysis_coordination.py b/tests/test_full_analysis_coordination.py
index 6fe12ac..55b04a2 100644
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -645,6 +645,82 @@ def test_lease_is_held_during_publication(tmp_path: Path, monkeypatch):
     assert event_log == expected_order
 
 
+def test_full_facade_acknowledges_already_installed_under_writer_lease(
+    tmp_path: Path,
+    isolated_dirs,
+    monkeypatch,
+):
+    import contextor.core.live_state as live_state_module
+
+    from contextor.core.analysis.state_manager import AnalysisResult
+
+    repo = tmp_path / "full_ack_repo"
+    repo.mkdir()
+    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
+    observed = []
+
+    class AlreadyInstalledClient:
+        def publish(
+            self,
+            state,
+            *,
+            origin="unknown",
+            acknowledge_installed=False,
+        ):
+            try:
+                probe_lease = acquire_full_analysis(
+                    repo,
+                    owner="nested-publish-probe",
+                    timeout=0.0,
+                )
+            except FullAnalysisBusyError:
+                lease_held = True
+            else:
+                release_full_analysis(probe_lease)
+                lease_held = False
+            revision = int(state.revision)
+            observed.append(
+                {
+                    "origin": origin,
+                    "acknowledge_installed": acknowledge_installed,
+                    "lease_held": lease_held,
+                    "revision": revision,
+                }
+            )
+            return {
+                "status": "ok",
+                "revision": revision,
+                "seq": 9,
+                "source": "committed_snapshot",
+                "already_installed": True,
+                "origin_verified": False,
+            }
+
+    client = AlreadyInstalledClient()
+    monkeypatch.setattr(
+        live_state_module,
+        "connect",
+        lambda _root: client,
+    )
+
+    errors, analysis_result = run_full_analysis_exclusive(
+        repo,
+        owner="mcp_analysis",
+    )
+
+    assert isinstance(errors, list)
+    assert isinstance(analysis_result, AnalysisResult)
+    assert len(observed) == 1
+    assert observed[0]["origin"] == "mcp_analysis"
+    assert observed[0]["acknowledge_installed"] is True
+    assert observed[0]["lease_held"] is True
+    assert analysis_result.live_publish_status == "success"
+    assert analysis_result.live_publish_revision == observed[0]["revision"]
+    assert analysis_result.live_publish_warning == (
+        "LIVE generation was already installed; event origin is not verified."
+    )
+
+
 def test_profile_operation_scopes_full_analysis_coordinator_evidence(tmp_path: Path):
     repo_dir = tmp_path / "repo_profile_trace"
     repo_dir.mkdir()
diff --git a/tests/test_gui_live_startup.py b/tests/test_gui_live_startup.py
index 784d696..9c4eaa6 100644
--- a/tests/test_gui_live_startup.py
+++ b/tests/test_gui_live_startup.py
@@ -256,7 +256,13 @@ def test_initial_success(tmp_path, monkeypatch):
     controller = _make_controller(repo, root)
 
     class Client:
-        def publish(self, state, *, origin="unknown"):
+        def publish(
+            self,
+            state,
+            *,
+            origin="unknown",
+            acknowledge_installed=False,
+        ):
             return {"status": "ok"}
 
     watcher_instances = []
@@ -350,7 +356,13 @@ def test_timeout_then_success(tmp_path, monkeypatch):
     controller = _make_controller(repo, root)
 
     class Client:
-        def publish(self, state, *, origin="unknown"):
+        def publish(
+            self,
+            state,
+            *,
+            origin="unknown",
+            acknowledge_installed=False,
+        ):
             return {"status": "ok"}
 
     watcher_instances = []
@@ -425,7 +437,13 @@ def test_late_service_connection(tmp_path, monkeypatch):
     connect_calls = []
 
     class Client:
-        def publish(self, state, *, origin="unknown"):
+        def publish(
+            self,
+            state,
+            *,
+            origin="unknown",
+            acknowledge_installed=False,
+        ):
             return {"status": "ok"}
 
     def mock_connect_or_start(path, *, owner_pid=None, owner_token=None):
@@ -1537,3 +1555,107 @@ def test_startup_publication_error_recovery_classification(
         assert expected_reason in ask.call_args.args[1]
         assert next(iter(root.scheduled.values()))[0] == 100
     controller.analyze.assert_not_called()
+
+
+def test_startup_already_installed_ack_keeps_lease_and_skips_recovery(
+    tmp_path,
+    monkeypatch,
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    root = MockTkRoot()
+    controller = _bind_recovery_prompt(_make_controller(repo, root))
+    loaded = SimpleNamespace(revision=7, state_id="loaded-generation")
+    remote = SimpleNamespace(revision=6, state_id="remote-generation")
+    events = []
+    publish_calls = []
+    lease = object()
+    response = {
+        "status": "ok",
+        "revision": 7,
+        "seq": 12,
+        "source": "committed_snapshot",
+        "already_installed": True,
+        "origin_verified": False,
+    }
+
+    class Client:
+        def snapshot(self):
+            return {"state": remote, "revision": 6}
+
+        def publish(
+            self,
+            state,
+            *,
+            origin="unknown",
+            acknowledge_installed=False,
+        ):
+            events.append("publish")
+            publish_calls.append(
+                {
+                    "state": state,
+                    "origin": origin,
+                    "acknowledge_installed": acknowledge_installed,
+                }
+            )
+            return response
+
+    class Watcher:
+        def __init__(self, *_args, **_kwargs):
+            pass
+
+        def start(self):
+            pass
+
+    class Feed:
+        def __init__(self, *_args, **_kwargs):
+            pass
+
+        def start(self):
+            pass
+
+    def acquire(*_args, **_kwargs):
+        events.append("lease_acquired")
+        return lease
+
+    def release(value):
+        assert value is lease
+        events.append("lease_released")
+
+    monkeypatch.setattr(gui, "connect_or_start", lambda *_a, **_k: Client())
+    monkeypatch.setattr(
+        gui,
+        "migrate_legacy_snapshot",
+        lambda *_a: tmp_path / "cache",
+    )
+    monkeypatch.setattr(gui, "acquire_full_analysis", acquire)
+    monkeypatch.setattr(gui, "release_full_analysis", release)
+    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
+    monkeypatch.setattr(gui, "DesktopLiveEventFeed", Feed)
+    monkeypatch.setattr(
+        "contextor.core.analysis.state_manager.load_engine_state",
+        lambda *_a, **_k: loaded,
+    )
+
+    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
+
+    assert events == ["lease_acquired", "publish", "lease_released"]
+    assert publish_calls == [
+        {
+            "state": loaded,
+            "origin": "desktop_analysis",
+            "acknowledge_installed": True,
+        }
+    ]
+    assert (
+        "LIVE: shared generation already installed; event origin unverified"
+        in controller._statuses
+    )
+    assert "LIVE: shared state published; watcher active" not in (
+        controller._statuses
+    )
+    assert controller._live_recovery_queue.qsize() == 0
+    assert controller._live_recovery_prompt_pending == set()
+    assert root.scheduled == {}
+    controller.analyze.assert_not_called()
diff --git a/tests/test_live_single_file_reuse.py b/tests/test_live_single_file_reuse.py
index 5080572..6bf9448 100644
--- a/tests/test_live_single_file_reuse.py
+++ b/tests/test_live_single_file_reuse.py
@@ -186,6 +186,103 @@ def test_scoped_single_file_publishes_to_real_live_server_under_writer_lease(
         server_thread.join(timeout=5)
 
 
+def test_scoped_single_file_reports_already_installed_ack_under_writer_lease(
+    sample_repo,
+    isolated_dirs,
+    monkeypatch,
+):
+    import pytest
+    import contextor.core.api.facade as facade_module
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+
+    target = sample_repo / "core" / "alpha.py"
+    ContextorFacade.analyze_project(str(sample_repo))
+    original_hydrate = facade_module.hydrate_repository_engine
+    observed = []
+
+    class AlreadyInstalledClient:
+        def publish(
+            self,
+            state,
+            *,
+            origin="unknown",
+            timeout=30.0,
+            acknowledge_installed=False,
+        ):
+            try:
+                probe_lease = coordinator.acquire_full_analysis(
+                    sample_repo,
+                    timeout=0.0,
+                    writer_kind="local_incremental",
+                )
+            except coordinator.FullAnalysisBusyError:
+                lease_held = True
+            else:
+                coordinator.release_full_analysis(probe_lease)
+                lease_held = False
+            revision = int(state.revision)
+            observed.append(
+                {
+                    "origin": origin,
+                    "timeout": timeout,
+                    "acknowledge_installed": acknowledge_installed,
+                    "lease_held": lease_held,
+                    "revision": revision,
+                }
+            )
+            return {
+                "status": "ok",
+                "revision": revision,
+                "seq": 12,
+                "source": "committed_snapshot",
+                "already_installed": True,
+                "origin_verified": False,
+            }
+
+    client = AlreadyInstalledClient()
+
+    def hydrate_with_ack_client(root, **kwargs):
+        hydrated = original_hydrate(root, **kwargs)
+        assert hydrated is not None
+        return replace(hydrated, client=client)
+
+    monkeypatch.setattr(
+        facade_module,
+        "hydrate_repository_engine",
+        hydrate_with_ack_client,
+    )
+    target.write_text(
+        target.read_text(encoding="utf-8").replace(
+            "MAX_ITEMS = 10",
+            "MAX_ITEMS = 12",
+        ),
+        encoding="utf-8",
+    )
+    publication = {}
+
+    output = ContextorFacade.analyze_single_file(
+        str(target),
+        str(sample_repo),
+        publication_result=publication,
+    )
+
+    assert output.endswith("single_core.alpha.json")
+    assert observed == [
+        {
+            "origin": "scoped_analysis",
+            "timeout": 5.0,
+            "acknowledge_installed": True,
+            "lease_held": True,
+            "revision": observed[0]["revision"],
+        }
+    ]
+    assert publication["status"] == "success"
+    assert publication["revision"] == observed[0]["revision"]
+    assert publication["warning"] == (
+        "LIVE generation was already installed; event origin is not verified."
+    )
+
+
 def test_single_file_resync_state_rejects_state_only_path(
     sample_repo, isolated_dirs, monkeypatch
 ):
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index ee0aa92..89bf9e3 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -400,6 +400,49 @@ def test_client_request_timeout_closes_connection(monkeypatch):
     assert connection.closed is True
 
 
+def test_publish_default_payload_is_unchanged_and_opt_in_adds_ack_flag(
+    monkeypatch,
+):
+    client = LiveStateClient(
+        SimpleNamespace(address=("127.0.0.1", 1), authkey=b"x")
+    )
+    state = SimpleNamespace(state_id="sid", revision=2)
+    requests = []
+
+    def capture_request(operation, **kwargs):
+        requests.append((operation, kwargs))
+        return {"status": "ok"}
+
+    monkeypatch.setattr(client, "request", capture_request)
+
+    assert client.publish(
+        state,
+        origin="owner",
+        timeout=4.0,
+    ) == {"status": "ok"}
+    assert client.publish(
+        state,
+        origin="owner",
+        timeout=4.0,
+        acknowledge_installed=True,
+    ) == {"status": "ok"}
+    assert requests == [
+        (
+            "publish",
+            {"timeout": 4.0, "state": state, "origin": "owner"},
+        ),
+        (
+            "publish",
+            {
+                "timeout": 4.0,
+                "state": state,
+                "origin": "owner",
+                "acknowledge_installed": True,
+            },
+        ),
+    ]
+
+
 def test_client_transport_failure_emits_one_bounded_trace_event(monkeypatch):
     events = []
     endpoint = SimpleNamespace(

## RESTART_REQUIRED

No MCP, LIVE, or Desktop process was restarted. The changed IPC server/client, facade, and GUI code is source-synchronized, but this work does not certify that already-running serving processes imported the changes. Restart/reload is required before claiming serving-process behavior; no runtime reload is claimed here.

## REMAINING_ORIGIN_AUTHORIZATION_RISK

The opt-in ACK reconciles an already-installed committed generation and explicitly marks its event origin unverified. Raw publish remains reachable without canonical-writer authentication, and an origin string remains caller-supplied. This patch does not establish publisher ownership or prevent origin spoofing.

## FINAL_VERDICT

Focused code/test gate passed: L32H2G2D_TARGETED_PASS.
This is not an L32H final pass and is not serving-process runtime certification.
L32H2G2D_TARGETED_PASS

# CPA10K6D2_WATCHER_TRUSTED_MANAGER_TEST_FIXTURES

STATUS=PASS

FULL_SUITE_INPUT=
User-run full repository suite: `5 failed, 2588 passed, 1 warning in 760.09s`. The five failures were AttributeError at `batch_manager.get_current_file_state(...)` because test fixtures supplied `object()` or partial `SimpleNamespace` manager surfaces.

ROOT_CAUSE=
The production watcher contract correctly requires a trusted manager with `get_current_file_state(path, compute_hash=...)` for existing-file mutation identity capture. Five test fixtures still modeled the pre-contract partial manager surface. The correction is test-only: each existing-file fixture now delegates current-state reads to a real `FileStateManager` rooted at `repo_cache_dir(repo)`. The watchdog `_make_watcher` fixture retains its existing custom `has_changed()` and `tracked_paths()` behavior.

PRODUCTION_CHANGE_REQUIRED=NO

FILES_CHANGED=
- C:\Temp\Contextor_Repo\tests\test_live_activity_status.py
- C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py
- C:\Temp\Contextor_Repo\tests\test_live_watcher_watchdog.py
- C:\Temp\Contextor_Repo\walkthrough.md

FIXTURE_CORRECTIONS=
- `test_live_activity_status.py::test_desktop_watcher_and_mcp_update_file_single_event_semantics`: added a real `FileStateManager` current-state delegate while retaining the existing `has_changed`, `tracked_paths`, revision, and state-id fixture semantics.
- `test_live_desktop_integration.py::test_desktop_watcher_recovers_after_live_service_death`: replaced the incompatible `object()` trusted-manager fixture with a real `FileStateManager`.
- `test_live_desktop_integration.py::test_desktop_watcher_syntax_error_does_not_trigger_recovery`: replaced the incompatible `object()` trusted-manager fixture with a real `FileStateManager`.
- `test_live_watcher_watchdog.py::_make_watcher`: added a real bound `get_current_file_state` delegate while retaining the helper's custom `has_changed()` and `tracked_paths()` behavior; this fixes all existing-file callers using the helper.
- `test_live_watcher_watchdog.py::test_syntax_error_and_recovery_contract_survives_watchdog_adapter`: added the same real current-state delegate while retaining its custom tracked-path behavior.
- The deletion-only override in `test_delete_event_routes_missing_path_as_delete_candidate` was inspected and intentionally left unchanged because its path is absent before candidate processing and therefore does not execute existing-file SHA capture.

FIVE_ORIGINAL_FAILURES=
- `tests/test_live_activity_status.py::test_desktop_watcher_and_mcp_update_file_single_event_semantics`: PASS.
- `tests/test_live_desktop_integration.py::test_desktop_watcher_recovers_after_live_service_death`: PASS.
- `tests/test_live_desktop_integration.py::test_desktop_watcher_syntax_error_does_not_trigger_recovery`: PASS.
- `tests/test_live_watcher_watchdog.py::test_event_path_routes_through_queued_client_submission`: PASS.
- `tests/test_live_watcher_watchdog.py::test_syntax_error_and_recovery_contract_survives_watchdog_adapter`: PASS.
- Combined exact-node invocation: `5 passed, 1 warning`.

AFFECTED_MODULE_TESTS=
- `tests/test_live_activity_status.py`: `47 passed, 1 warning`.
- `tests/test_live_desktop_integration.py`: `24 passed`.
- `tests/test_live_watcher_watchdog.py`: `11 passed`.

ADDITIONAL_INCOMPATIBLE_FIXTURES_FOUND=
NO. All additional `_trusted_file_state` overrides in the three allowed modules were inspected. The only remaining partial fixture is deletion-only and cannot reach the existing-file mutation-identity read; changing it would broaden or alter its deletion semantics.

TARGETED_TESTS=
- Five exact failing nodeids: `5 passed, 1 warning`.
- Complete affected modules: `47 passed, 1 warning`; `24 passed`; `11 passed`.
- No unrelated modules were run.

FULL_SUITE_RUN=NO

MCP_SERVER_RESTART_REQUIRED=NO

DESKTOP_RUNTIME_RESTART_REQUIRED=NO
No production code or runtime behavior changed; no restart was performed or required.

CONTEXTOR_FIRST_DISCOVERY=
- Before editing, Contextor resolved the three allowed modules as `tests.test_live_activity_status` (`180/1`), `tests.test_live_desktop_integration` (`202/1`), and `tests.test_live_watcher_watchdog` (`366/2`), all with fresh syntax diagnostics and no errors.
- Contextor resolved all five failing test symbols and `_make_watcher` exactly. `_make_watcher` was confirmed to have ten direct callers, including the queued-submission and deletion tests.
- Module blast-radius queries confirmed the test-module scope; large payloads were bounded by Contextor's confirmation guard rather than truncated or replaced with grep-based architecture inference.

POST_EDIT_CONTEXTOR=
- The three test modules remained fresh with zero syntax errors, zero name collisions, and zero cycles in post-edit `get_file_edit_context` results.
- Post-edit `_make_watcher` call context retained the same ten callers and no callees were added; its canonical lineage remained resolved and metadata-consistent.
- Contextor reported `workspace_sync=out_of_sync` only for the modified watchdog source file in the narrow call-context envelope, with the advisory that disk changed after the canonical revision; canonical graph, lineage, and module diagnostics remained available. This is expected for the un-reloaded test edit and was not treated as an architectural regression.

SEMANTIC_PRESERVATION=
- Activity-status test still exercises single-event Desktop watcher/MCP semantics.
- Desktop integration tests still exercise service recovery/reconnect and syntax-error-without-recovery behavior.
- Watchdog tests still exercise queued client submission metadata and the `SYNTAX_ERROR -> RECOVERED` contract.
- No assertion was removed, no existing path was converted to deletion, no sleep was added, and no production fallback or AttributeError catch was introduced.

FULL_DIFFS=

## C:\Temp\Contextor_Repo\tests\test_live_activity_status.py

```diff
diff --git a/tests/test_live_activity_status.py b/tests/test_live_activity_status.py
index 71dfc9e..112cdd3 100644
--- a/tests/test_live_activity_status.py
+++ b/tests/test_live_activity_status.py
@@ -39,6 +39,8 @@ from contextor.core.live_state import (
     LiveStateClient,
 )
 from contextor.core.live_state.ipc import ACTIVITY_EVENT_RETENTION
+from contextor.core.analysis.state_manager import FileStateManager
+from contextor.core.paths import repo_cache_dir
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.mcp import runtime as mcp_runtime
 from contextor.mcp_server import (
@@ -694,9 +696,11 @@ def test_desktop_watcher_and_mcp_update_file_single_event_semantics(tmp_path):
         client,
         on_status=lambda msg: gui_status_callback(msg, event=None),
     )
+    manager = FileStateManager(str(repo_cache_dir(repo)))
     watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(
         has_changed=lambda _path: True,
         tracked_paths=lambda: set(),
+        get_current_file_state=manager.get_current_file_state,
         revision=1,
         state_id="sid",
     )
```

## C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py

```diff
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index 713991e..7f9c18b 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -12,8 +12,10 @@ from contextor.core.analysis.full_analysis_coordinator import (
     acquire_full_analysis,
     release_full_analysis,
 )
+from contextor.core.analysis.state_manager import FileStateManager
 from contextor.core.errors import AnalysisCancelled
 from contextor.core.live_state.watcher import DesktopLiveWatcher
+from contextor.core.paths import repo_cache_dir
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.core.repository_identity import read_repository_identity
 from contextor.ui import gui
@@ -872,7 +874,8 @@ def test_desktop_watcher_recovers_after_live_service_death(tmp_path):
         return recovered_client

     watcher._recover_client = mock_recover
-    watcher._trusted_file_state = lambda _snapshot: object()
+    manager = FileStateManager(str(repo_cache_dir(repo)))
+    watcher._trusted_file_state = lambda _snapshot: manager
     watcher._candidate_requires_update = lambda *_args: True

     # Simulate watchdog delivery for the changed path.
@@ -962,7 +965,8 @@ def test_desktop_watcher_syntax_error_does_not_trigger_recovery(tmp_path):
     )
     watcher._recover_client = lambda: recovery_called.append(True)
     watcher._candidate_requires_update = lambda *_args: True
-    watcher._trusted_file_state = lambda _snapshot: object()
+    manager = FileStateManager(str(repo_cache_dir(repo)))
+    watcher._trusted_file_state = lambda _snapshot: manager

     status_messages = []
     watcher.on_status = lambda msg: status_messages.append(msg)
```

## C:\Temp\Contextor_Repo\tests\test_live_watcher_watchdog.py

```diff
diff --git a/tests/test_live_watcher_watchdog.py b/tests/test_live_watcher_watchdog.py
index 9eeeabc..1ecb2f2 100644
--- a/tests/test_live_watcher_watchdog.py
+++ b/tests/test_live_watcher_watchdog.py
@@ -6,7 +6,9 @@ from types import SimpleNamespace

 import pytest

+from contextor.core.analysis.state_manager import FileStateManager
 from contextor.core.live_state import CanonicalLiveServer, DesktopLiveWatcher, LiveStateClient
+from contextor.core.paths import repo_cache_dir
 import contextor.core.live_state.watcher as watcher_module


@@ -60,9 +62,11 @@ def _make_watcher(tmp_path, *, result_status: str = "UPDATED"):
     watcher = DesktopLiveWatcher(repo, client, interval=0)
     watcher._startup_requires_resync = False
     watcher._startup_pending = []
+    manager = FileStateManager(str(repo_cache_dir(repo)))
     watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(
         has_changed=lambda _path: True,
         tracked_paths=lambda: {item[0] for item in updates},
+        get_current_file_state=manager.get_current_file_state,
         revision=1,
         state_id="sid",
     )
@@ -218,9 +222,11 @@ def test_syntax_error_and_recovery_contract_survives_watchdog_adapter(tmp_path):
     )
     watcher._startup_requires_resync = False
     watcher._startup_pending = []
+    manager = FileStateManager(str(repo_cache_dir(repo)))
     watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(
         has_changed=lambda _path: True,
         tracked_paths=lambda: {str(target.resolve())},
+        get_current_file_state=manager.get_current_file_state,
         revision=0,
         state_id="sid",
     )
```

The three FULL_DIFF sections above are complete diffs for every source/test file changed in this correction. `walkthrough.md` is the required report artifact and is excluded from its own diff.

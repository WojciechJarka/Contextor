STATUS=FINAL_PASS
HEAD_BEFORE=e8857b342bf48f815e570146572e3bb8672d8f2c
HEAD_AFTER=e8857b342bf48f815e570146572e3bb8672d8f2c
LIVE_REVISION_BEFORE=1349
LIVE_REVISION_AFTER=1353

FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\mcp_backend_cli.py
- C:\Temp\Contextor_Repo\contextor\__main__.py
- C:\Temp\Contextor_Repo\tests\test_mcp_backend_cli.py
walkthrough.md is report-only and excluded from diff accounting. No protected file changed.

SOURCE_VALIDATION
DIRECT_EVIDENCE:
- Current HEAD before and after implementation is e8857b342bf48f815e570146572e3bb8672d8f2c, matching the certified G2B1 handoff HEAD.
- Fresh Contextor source for contextor.__main__::main was workspace_sync=verified at LIVE revision 1349 before editing. The exact requested SEARCH block occurred exactly once: SEARCH_ANCHOR_COUNT=1.
- The literal patch was applied once. Existing contextor.cli.main and mcp_backend_control lifecycle APIs were unchanged.
- Read-only git status/diff shows only the three allowed source/test files and walkthrough.md. Protected files contextor/cli.py, contextor/mcp_backend_control.py, contextor/mcp_backend_state.py, contextor/mcp_backend_secret.py, and contextor/mcp_server.py have no diff.
CODE_PATH_PROVED:
- contextor.__main__.main keeps GUI routing first, strips --cli, routes only backend start/status/stop to the backend CLI, and delegates all other input to contextor.cli.main.
- contextor.mcp_backend_cli delegates lifecycle operations to get_backend_status, start_backend, and stop_backend from the existing contextor.mcp_backend_control owner.
CONTRACT_PROVED:
- The new CLI serializes BackendStatus.to_dict(), catches BackendControlError, and does not read or expose the backend token.
- The exact ten supplied tests cover JSON/status/error behavior, all three command routes, --cli handling, bare backend path compatibility, unrecognized suffix compatibility, and token-field absence.
INFERENCE:
- None required for the implementation verdict.
UNKNOWN:
- None material to the contracted behavior; no real backend was started.

IMPLEMENTATION_RESULT
BACKEND_CLI_IMPLEMENTED=YES
BACKEND_START_ROUTE_IMPLEMENTED=YES
BACKEND_STATUS_ROUTE_IMPLEMENTED=YES
BACKEND_STOP_ROUTE_IMPLEMENTED=YES
BARE_BACKEND_PATH_COMPATIBILITY_PRESERVED=YES
TOKEN_EXPOSED_BY_CLI=NO
REAL_BACKEND_STARTED=NO
CODEX_CONFIG_CHANGED=NO

ROUTING_CONTRACT
GUI routing remains first. The application intercepts exactly the backend start, backend status, and backend stop prefixes after removing --cli. Bare backend and unrecognized backend suffixes continue to contextor.cli.main.

CLI_OUTPUT_CONTRACT
The CLI emits JSON from BackendStatus.to_dict(), whose public keys are state, ready, detail, endpoint, pid, and instance_id. BackendControlError is emitted to stderr with the [ERROR] prefix and return code 1. Status returns 0 when ready and 1 when not ready.

TEST_RESULTS
- py_compile contextor\mcp_backend_cli.py contextor\__main__.py tests\test_mcp_backend_cli.py: PASS.
- pytest -q tests/test_mcp_backend_cli.py: PASS, 10 passed, 1 Authlib deprecation warning.
- pytest -q tests/test_mcp_backend_control.py: PASS, 20 passed, 1 Authlib deprecation warning.
TARGETED_TESTS=PASS
FULL_SUITE_RUN=NO

CONTEXTOR_VERIFICATION
- After four bounded get_live_events attempts spaced 5, 10, and 10 seconds, no desktop_watcher event appeared and __main__.py remained out_of_sync. No further event polling or update_file call was made.
- The contract-authorized full repository analysis recovery completed successfully and published LIVE revision 1352; analysis_coverage reported zero skipped Python files.
- Fresh post-recovery and post-test get_file_edit_context projections report workspace_sync=verified at revision 1353 for all three changed source/test files:
  - contextor/mcp_backend_cli.py
  - contextor/__main__.py
  - tests/test_mcp_backend_cli.py
- Each changed file reports syntax_errors=0, name_collisions=0, and cycles=0 with fresh availability.
- Direct fresh get_name_collisions reports availability=fresh, total=0, conflicting=0, identical=0.
- No real backend start occurred.

WORKSPACE_SYNC=verified/3 files at LIVE revision 1353
NAME_COLLISIONS=0/fresh direct projection
SYNTAX_ERRORS=0/fresh
CYCLES=0/fresh

MCP_SERVER_RESTART_REQUIRED=NO
GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO

FULL_DIFFS

FILE=C:\Temp\Contextor_Repo\contextor\mcp_backend_cli.py
diff --git a/contextor/mcp_backend_cli.py b/contextor/mcp_backend_cli.py
new file mode 100644
index 0000000..416461a
--- /dev/null
+++ b/contextor/mcp_backend_cli.py
@@ -0,0 +1,94 @@
+"""Command-line control for the persistent Contextor MCP backend."""
+
+from __future__ import annotations
+
+import argparse
+import json
+import sys
+
+from contextor.mcp_backend_control import (
+    BackendControlError,
+    BackendStatus,
+    get_backend_status,
+    start_backend,
+    stop_backend,
+)
+
+
+def _build_parser() -> argparse.ArgumentParser:
+    parser = argparse.ArgumentParser(
+        prog="contextor backend",
+        description=(
+            "Control the persistent local Contextor MCP backend."
+        ),
+    )
+
+    subparsers = parser.add_subparsers(
+        dest="command",
+        required=True,
+    )
+
+    subparsers.add_parser(
+        "start",
+        help=(
+            "Start the persistent backend or reuse an "
+            "already-ready instance."
+        ),
+    )
+
+    subparsers.add_parser(
+        "status",
+        help="Report authenticated backend readiness.",
+    )
+
+    subparsers.add_parser(
+        "stop",
+        help="Stop the identity-verified persistent backend.",
+    )
+
+    return parser
+
+
+def _emit_status(
+    status: BackendStatus,
+) -> None:
+    print(
+        json.dumps(
+            status.to_dict(),
+            sort_keys=True,
+        )
+    )
+
+
+def main(
+    argv: list[str] | None = None,
+) -> int:
+    args = _build_parser().parse_args(argv)
+
+    try:
+        if args.command == "start":
+            status = start_backend()
+
+        elif args.command == "status":
+            status = get_backend_status()
+
+        else:
+            status = stop_backend()
+
+    except BackendControlError as exc:
+        print(
+            f"[ERROR] {exc}",
+            file=sys.stderr,
+        )
+        return 1
+
+    _emit_status(status)
+
+    if args.command == "status":
+        return 0 if status.ready else 1
+
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())

FILE=C:\Temp\Contextor_Repo\contextor\__main__.py
diff --git a/contextor/__main__.py b/contextor/__main__.py
index 633b963..aa441f3 100644
--- a/contextor/__main__.py
+++ b/contextor/__main__.py
@@ -85,11 +85,37 @@ def main(argv: list[str] | None = None) -> int:
     if "--gui" in argv:
         return _run_gui()
 
-    from contextor.cli import main as cli_main
-
     # '--cli' is accepted for symmetry with '--gui' and documentation,
     # but CLI is the default mode.
-    return cli_main([arg for arg in argv if arg != "--cli"])
+    cli_argv = [
+        arg
+        for arg in argv
+        if arg != "--cli"
+    ]
+
+    if (
+        len(cli_argv) >= 2
+        and cli_argv[0] == "backend"
+        and cli_argv[1]
+        in {
+            "start",
+            "status",
+            "stop",
+        }
+    ):
+        from contextor.mcp_backend_cli import (
+            main as backend_cli_main,
+        )
+
+        return backend_cli_main(
+            cli_argv[1:]
+        )
+
+    from contextor.cli import main as cli_main
+
+    return cli_main(
+        cli_argv
+    )
 
 
 # ============================================================

FILE=C:\Temp\Contextor_Repo\tests\test_mcp_backend_cli.py
diff --git a/tests/test_mcp_backend_cli.py b/tests/test_mcp_backend_cli.py
new file mode 100644
index 0000000..4996244
--- /dev/null
+++ b/tests/test_mcp_backend_cli.py
@@ -0,0 +1,318 @@
+import json
+
+import pytest
+
+import contextor.__main__ as application
+import contextor.cli as analysis_cli
+import contextor.mcp_backend_cli as backend_cli
+from contextor.mcp_backend_control import (
+    BackendControlError,
+    BackendStatus,
+)
+
+
+def test_backend_cli_start_emits_json_and_returns_zero(
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.setattr(
+        backend_cli,
+        "start_backend",
+        lambda: BackendStatus(
+            state="running",
+            ready=True,
+            detail="ready",
+            record=None,
+        ),
+    )
+
+    result = backend_cli.main(["start"])
+
+    captured = capsys.readouterr()
+    payload = json.loads(captured.out)
+
+    assert result == 0
+    assert captured.err == ""
+    assert payload == {
+        "detail": "ready",
+        "endpoint": None,
+        "instance_id": None,
+        "pid": None,
+        "ready": True,
+        "state": "running",
+    }
+
+
+def test_backend_cli_status_ready_returns_zero(
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.setattr(
+        backend_cli,
+        "get_backend_status",
+        lambda: BackendStatus(
+            state="running",
+            ready=True,
+            detail="ready",
+            record=None,
+        ),
+    )
+
+    result = backend_cli.main(["status"])
+
+    captured = capsys.readouterr()
+    payload = json.loads(captured.out)
+
+    assert result == 0
+    assert captured.err == ""
+    assert payload["ready"] is True
+
+
+def test_backend_cli_status_not_ready_returns_one(
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.setattr(
+        backend_cli,
+        "get_backend_status",
+        lambda: BackendStatus(
+            state="stopped",
+            ready=False,
+            detail="not running",
+            record=None,
+        ),
+    )
+
+    result = backend_cli.main(["status"])
+
+    captured = capsys.readouterr()
+    payload = json.loads(captured.out)
+
+    assert result == 1
+    assert captured.err == ""
+    assert payload["ready"] is False
+    assert payload["state"] == "stopped"
+
+
+def test_backend_cli_stop_returns_zero(
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.setattr(
+        backend_cli,
+        "stop_backend",
+        lambda: BackendStatus(
+            state="stopped",
+            ready=False,
+            detail="persistent backend stopped",
+            record=None,
+        ),
+    )
+
+    result = backend_cli.main(["stop"])
+
+    captured = capsys.readouterr()
+    payload = json.loads(captured.out)
+
+    assert result == 0
+    assert captured.err == ""
+    assert payload["state"] == "stopped"
+
+
+def test_backend_cli_control_error_is_stderr_and_exit_one(
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    def fail_start() -> BackendStatus:
+        raise BackendControlError("boom")
+
+    monkeypatch.setattr(
+        backend_cli,
+        "start_backend",
+        fail_start,
+    )
+
+    result = backend_cli.main(["start"])
+
+    captured = capsys.readouterr()
+
+    assert result == 1
+    assert captured.out == ""
+    assert "[ERROR] boom" in captured.err
+
+
+def test_application_main_routes_backend_start_to_backend_cli(
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    captured: list[list[str]] = []
+
+    def fake_backend_main(
+        argv: list[str] | None = None,
+    ) -> int:
+        captured.append(list(argv or []))
+        return 17
+
+    monkeypatch.setattr(
+        backend_cli,
+        "main",
+        fake_backend_main,
+    )
+    monkeypatch.setattr(
+        analysis_cli,
+        "main",
+        lambda argv=None: pytest.fail(
+            "normal CLI must not handle backend start"
+        ),
+    )
+
+    result = application.main(
+        [
+            "backend",
+            "start",
+        ]
+    )
+
+    assert result == 17
+    assert captured == [["start"]]
+
+
+def test_application_main_routes_backend_status_with_cli_flag(
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    captured: list[list[str]] = []
+
+    def fake_backend_main(
+        argv: list[str] | None = None,
+    ) -> int:
+        captured.append(list(argv or []))
+        return 19
+
+    monkeypatch.setattr(
+        backend_cli,
+        "main",
+        fake_backend_main,
+    )
+    monkeypatch.setattr(
+        analysis_cli,
+        "main",
+        lambda argv=None: pytest.fail(
+            "normal CLI must not handle backend status"
+        ),
+    )
+
+    result = application.main(
+        [
+            "--cli",
+            "backend",
+            "status",
+        ]
+    )
+
+    assert result == 19
+    assert captured == [["status"]]
+
+
+def test_application_main_preserves_bare_backend_as_repository_path(
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    captured: list[list[str]] = []
+
+    def fake_analysis_main(
+        argv: list[str] | None = None,
+    ) -> int:
+        captured.append(list(argv or []))
+        return 23
+
+    monkeypatch.setattr(
+        analysis_cli,
+        "main",
+        fake_analysis_main,
+    )
+    monkeypatch.setattr(
+        backend_cli,
+        "main",
+        lambda argv=None: pytest.fail(
+            "bare backend must remain an analysis path"
+        ),
+    )
+
+    result = application.main(
+        ["backend"]
+    )
+
+    assert result == 23
+    assert captured == [["backend"]]
+
+
+def test_application_main_preserves_unrecognized_backend_suffix_for_normal_cli(
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    captured: list[list[str]] = []
+
+    def fake_analysis_main(
+        argv: list[str] | None = None,
+    ) -> int:
+        captured.append(list(argv or []))
+        return 29
+
+    monkeypatch.setattr(
+        analysis_cli,
+        "main",
+        fake_analysis_main,
+    )
+    monkeypatch.setattr(
+        backend_cli,
+        "main",
+        lambda argv=None: pytest.fail(
+            "unknown backend suffix must remain normal CLI input"
+        ),
+    )
+
+    result = application.main(
+        [
+            "backend",
+            "something-else",
+        ]
+    )
+
+    assert result == 29
+    assert captured == [
+        [
+            "backend",
+            "something-else",
+        ]
+    ]
+
+
+def test_backend_cli_does_not_expose_token_fields(
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.setattr(
+        backend_cli,
+        "get_backend_status",
+        lambda: BackendStatus(
+            state="running",
+            ready=True,
+            detail="ready",
+            record=None,
+        ),
+    )
+
+    result = backend_cli.main(["status"])
+
+    captured = capsys.readouterr()
+    payload = json.loads(captured.out)
+
+    assert result == 0
+    assert set(payload) == {
+        "state",
+        "ready",
+        "detail",
+        "endpoint",
+        "pid",
+        "instance_id",
+    }
+    assert "token" not in payload
+    assert "auth" not in payload
+    assert "bearer" not in payload
warning: in the working copy of 'tests/test_mcp_backend_cli.py', LF will be replaced by CRLF the next time Git touches it

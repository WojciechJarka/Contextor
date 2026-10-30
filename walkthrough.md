# CONTEXTOR PY315-R4F-1

## PREFLIGHT

Contextor MCP module discovery first: `tests.test_mcp_job_tree_isolated_windows`, canonical revision 939, `workspace_sync=verified` before edit. HEAD `dff0f6364d8ad509d0645c3d27c2e828738d9328`; worktree clean. Exact anchor counts: `def _read_pid(path):` = 1; existing `def test_isolated_backend_job_kills_unregistered_child_and_grandchild_but_not_live_or_unrelated(` = 1. Neither existing function changed.

## EXACT_TEST_IMPLEMENTATION

Appended the exact supplied `test_venv_redirector_only_termination_closes_backend_job_tree` at lines 280-468 of `tests/test_mcp_job_tree_isolated_windows.py`. Production source unchanged. Test launches a private venv redirector, confirms distinct actual owner, captures creation-bound identities, terminates redirector only, asserts owner/child/grandchild gone while breakaway LIVE analogue and unrelated sentinel survive, then cleans private processes.

## REDIRECTOR_PID_AND_CREATION

The test captured and asserted a live creation-bound redirector identity internally. Its PID and creation number are **not emitted** by the exact supplied test. An external observation attempt read the actual owner PID 11288, but CIM returned no parent PID before the short test completed. Therefore numerical redirector PID/creation for this test is UNKNOWN; it would be incorrect to substitute R4E's separate probe value.

## ACTUAL_OWNER_PID_AND_CREATION

Direct external observation during an additional targeted run: actual owner PID 6416, `creation_time=134378748411564920`, state ALIVE, base Python image. In the first targeted run the owner PID artifact was 2964; in the regression run it was 15128. These runs must not be conflated.

## CHILD_AND_GRANDCHILD_IDENTITIES

Same externally observed targeted run: child PID 11428, creation 134378748413677800; grandchild PID 6412, creation 134378748415786168. Both ALIVE at capture. The exact test subsequently asserted both gone after redirector termination. Separate regression run artifacts: child 8632, grandchild 2820; their creation numbers were not recorded.

## REDIRECTOR_TERMINATION_RESULT

CONTRACT_PROVED by passing test assertion: `terminate_or_confirm_registered_process(identities["redirector"])` returned true. Numerical redirector identity was retained by the test but not printed. No production process was targeted.

## OWNER_AND_TREE_EXIT_RESULT

CONTRACT_PROVED by passing test assertions: after redirector-only identity-bound termination and `redirector.wait(timeout=8)`, actual owner, child and grandchild were confirmed gone using the captured creation identities. This directly exercises the missing R4E boundary in an isolated test.

## LIVE_ANALOGUE_SURVIVAL

Same observed run: LIVE analogue PID 4100, creation 134378748417974748, ALIVE at capture. Passing test asserts it remained ALIVE after redirector termination. Cleanup then terminated it by identity.

## SENTINEL_SURVIVAL

Same observed run: unrelated sentinel PID 7644, creation 134378748410702877, ALIVE at capture. Passing test asserts it remained ALIVE after redirector termination. Cleanup then terminated it. Regression run sentinel artifact PID 1236.

## PRIVATE_PROCESS_CLEANUP

Both targeted and regression pytest processes exited 0. Test `finally` confirms each captured owner/child/grandchild/LIVE/redirector identity resolved; sentinel Popen was waited. No `private redirector probe cleanup unresolved` failure occurred. No existing Contextor, Codex, Antigravity, Desktop or production LIVE process was terminated.

## TARGETED_TEST_RESULTS

- Compile `tests/test_mcp_job_tree_isolated_windows.py`: PASS.
- New test first: `1 passed, 2 deselected`.
- Required regression subset: `13 passed`.
- Additional identical new-test run for numerical creation identities: `1 passed, 2 deselected`.
- Final additional run attempted external redirector parent observation: `1 passed, 2 deselected`; parent number remained unavailable. No full pytest.

## MCP_POST_CHANGE_AUDIT

First read after edit: canonical revision 939, `workspace_sync=out_of_sync`. Subsequent Contextor MCP module read: revision 940, `workspace_sync=verified`, export degree 11. `get_symbol_implementation` resolved the new test at lines 280-468 with revision 940 and `workspace_sync=verified`. No `update_file` or restart.

## FILES_CHANGED

`tests/test_mcp_job_tree_isolated_windows.py` only. `walkthrough.md` overwritten as report.

## FULL_DIFFS

Full actual diff:

```diff
diff --git a/tests/test_mcp_job_tree_isolated_windows.py b/tests/test_mcp_job_tree_isolated_windows.py
index b63a4bb..e645e4c 100644
--- a/tests/test_mcp_job_tree_isolated_windows.py
+++ b/tests/test_mcp_job_tree_isolated_windows.py
@@ -276,3 +276,194 @@ def test_isolated_backend_job_kills_unregistered_child_and_grandchild_but_not_li
         if unresolved:
             pytest.fail(f"isolated test-owned processes unresolved: {unresolved}")
 
+
+def test_venv_redirector_only_termination_closes_backend_job_tree(
+    tmp_path: Path,
+):
+    """Prove cleanup behavior when only the venv launcher is terminated."""
+    repo_root = Path(__file__).resolve().parents[1]
+    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
+
+    assert venv_python.is_file()
+
+    for name, code in (
+        ("leaf.py", LEAF_CODE),
+        ("child.py", CHILD_CODE),
+        ("owner.py", OWNER_CODE),
+    ):
+        (tmp_path / name).write_text(code, encoding="utf-8")
+
+    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
+    env = os.environ.copy()
+    env["PYTHONPATH"] = os.pathsep.join(
+        filter(None, (str(repo_root), env.get("PYTHONPATH", "")))
+    )
+
+    sentinel = subprocess.Popen(
+        [
+            sys._base_executable,
+            str(tmp_path / "leaf.py"),
+            str(tmp_path / "sentinel.pid"),
+        ],
+        stdin=subprocess.DEVNULL,
+        stdout=subprocess.DEVNULL,
+        stderr=subprocess.DEVNULL,
+        creationflags=flags,
+    )
+
+    redirector = None
+    identities = {}
+    try:
+        redirector = subprocess.Popen(
+            [
+                str(venv_python),
+                str(tmp_path / "owner.py"),
+                str(tmp_path),
+            ],
+            cwd=str(repo_root),
+            env=env,
+            stdin=subprocess.DEVNULL,
+            stdout=subprocess.DEVNULL,
+            stderr=subprocess.PIPE,
+            creationflags=flags,
+        )
+
+        identities["redirector"] = _identity_record(redirector.pid)
+
+        assert _wait_until(
+            lambda: (
+                (tmp_path / "ready.json").is_file()
+                or redirector.poll() is not None
+            )
+        ), "venv redirector readiness timeout"
+
+        if redirector.poll() is not None:
+            detail = redirector.stderr.read().decode(
+                "utf-8", errors="replace"
+            )
+            pytest.fail(
+                f"venv redirector exited before readiness: {detail}"
+            )
+
+        info = json.loads(
+            (tmp_path / "ready.json").read_text(encoding="utf-8")
+        )
+
+        assert redirector.pid != info["owner"], (
+            "expected a distinct Windows venv redirector PID"
+        )
+
+        assert _wait_until(
+            lambda: (tmp_path / "child.json").is_file()
+        )
+        assert _wait_until(
+            lambda: (tmp_path / "grandchild.pid").is_file()
+        )
+        assert _wait_until(
+            lambda: (tmp_path / "live.pid").is_file()
+        )
+        assert _wait_until(
+            lambda: (tmp_path / "sentinel.pid").is_file()
+        )
+
+        child_info = json.loads(
+            (tmp_path / "child.json").read_text(encoding="utf-8")
+        )
+
+        assert child_info["pid"] == info["child"]
+        assert child_info["grandchild_pid"] == info["grandchild"]
+        assert _read_pid(tmp_path / "grandchild.pid") == info["grandchild"]
+        assert _read_pid(tmp_path / "live.pid") == info["live"]
+        assert _read_pid(tmp_path / "sentinel.pid") == sentinel.pid
+
+        for key, pid in (
+            ("actual_owner", info["owner"]),
+            ("child", info["child"]),
+            ("grandchild", info["grandchild"]),
+            ("live", info["live"]),
+            ("sentinel", sentinel.pid),
+        ):
+            identities[key] = _identity_record(pid)
+
+        assert all(
+            _recorded_identity_alive(record)
+            for record in identities.values()
+        )
+
+        assert registry.terminate_or_confirm_registered_process(
+            identities["redirector"]
+        ), "identity-bound redirector termination was not confirmed"
+
+        redirector.wait(timeout=8)
+
+        assert _wait_until(
+            lambda: (
+                _recorded_identity_gone(identities["actual_owner"])
+                and _recorded_identity_gone(identities["child"])
+                and _recorded_identity_gone(identities["grandchild"])
+            ),
+            timeout=8,
+        ), (
+            "terminating the venv redirector left the actual "
+            "backend Job owner or its descendants alive"
+        )
+
+        assert _recorded_identity_alive(
+            identities["live"]
+        ), "redirector termination killed the breakaway LIVE analogue"
+
+        assert _recorded_identity_alive(
+            identities["sentinel"]
+        ), "redirector termination killed the unrelated sentinel"
+
+    finally:
+        unresolved = []
+
+        for key in (
+            "actual_owner",
+            "child",
+            "grandchild",
+            "live",
+        ):
+            record = identities.get(key)
+            if record is not None:
+                if not registry.terminate_or_confirm_registered_process(
+                    record
+                ):
+                    unresolved.append(key)
+
+        if redirector is not None:
+            record = identities.get("redirector")
+            if record is not None:
+                if not registry.terminate_or_confirm_registered_process(
+                    record
+                ):
+                    unresolved.append("redirector")
+
+            try:
+                redirector.wait(timeout=5)
+            except subprocess.TimeoutExpired:
+                if redirector.poll() is None:
+                    redirector.terminate()
+                try:
+                    redirector.wait(timeout=5)
+                except subprocess.TimeoutExpired:
+                    unresolved.append("redirector_wait")
+
+            if redirector.stderr is not None:
+                redirector.stderr.close()
+
+        if sentinel.poll() is None:
+            sentinel.terminate()
+
+        try:
+            sentinel.wait(timeout=5)
+        except subprocess.TimeoutExpired:
+            sentinel.kill()
+            sentinel.wait(timeout=5)
+
+        if unresolved:
+            pytest.fail(
+                f"private redirector probe cleanup unresolved: {unresolved}"
+            )
+
```

## REMAINING_UNKNOWN

Numerical PID and creation time of redirector in these exact pytest runs were not externally emitted. Production backend startup and host-owned MCP tree coverage remain untested here.

## FINAL_VERDICT

`PASS_REDIRECTOR_CLEANUP_HOST_OWNED_GATE_OPEN` for the isolated redirector termination boundary. This verdict does not close host-owned tree parity or production restart gates.


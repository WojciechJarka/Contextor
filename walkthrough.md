# P5-M07-I2-T1 — CPython function identity baseline

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was used first. `evaluate_package_import_order` resolves to `contextor/core/cycle_semantics/package_model.py:1154-2284`, canonical LIVE revision 1295, source fresh, `workspace_sync=verified`; `cycle_semantics=stale`.
- DIRECT_EVIDENCE: HEAD `56cda86dbeb9d37b53c57ecd52f5f0302af4cf15`; initial status ` M walkthrough.md` only. The report was already modified by the preceding stage and has been overwritten as required. No other pre-existing changes.
- DIRECT_EVIDENCE: Active backend venv executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`; it reports CPython `3.15.2` (`tags/v3.15.2:5e58eaa`).
- DIRECT_EVIDENCE: `tests/test_cycle_semantics_function_identity_cpython.py` did not exist before editing. M07-I1 anchors remain in `execution/calls.py:8-35` and `package_model.py:1882-1889,2163-2171`; no production code was edited.

## FILES_CHANGED

- Added `tests/test_cycle_semantics_function_identity_cpython.py` with the exact requested seven-case CPython baseline. Its complete diff appears below.
- Overwrote `walkthrough.md`, the required report. No production or existing test file changed.

## CPYTHON_BASELINE_MATRIX

DIRECT_EVIDENCE: Each listed observation is established by the test's exact keyed assertion against JSON emitted from an isolated `sys.executable -I -B` subprocess. All cases passed under CPython 3.15.2. A dash means that field was not asserted in that case.

| Case | Success | `pkg.old` | `pkg.new` | `g is f` | Error |
|---|---:|---:|---:|---:|---|
| direct-call | true | true | false | — | — |
| alias-call | true | true | false | true | — |
| alias-survives-rebinding | true | true | false | false | — |
| old-alias-survives-redefinition | true | true | false | false | — |
| new-definition-call | true | false | true | false | — |
| noncallable-rebinding | false | false | false | — | `TypeError` |
| foreign-function-cpython-control | true | true | false | — | — |

The assertions are in `tests/test_cycle_semantics_function_identity_cpython.py:22-70,161-169`; the runner's observed fields are defined at `:72-105`. The foreign-call case establishes CPython behavior only and does not authorize changing Contextor's foreign-call UNKNOWN boundary.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_function_identity_cpython.py -rs` → `7 passed in 4.74s`.
- DIRECT_EVIDENCE: `git diff --check` exited 0; its only output was Git's existing line-ending advisory for `walkthrough.md`. No full suite was run.
- DIRECT_EVIDENCE: Final source status before report rewrite: ` M walkthrough.md`, `?? tests/test_cycle_semantics_function_identity_cpython.py`. No Git index/history mutation.
- DIRECT_EVIDENCE: Contextor MCP returned `file_not_in_canonical_scope` for the new test file. Its canonical freshness is therefore UNKNOWN; the pre-existing canonical revision was 1295. No FULL, `update_file`, or restart was performed.

## MODEL_PARITY_STATUS

- UNKNOWN: These tests establish CPython function identity, aliasing, rebinding, redefinition, import-effect, and noncallable-call behavior only. They do not exercise `evaluate_package_import_order` or establish model parity. The model's old alias-call UNKNOWN test remains unchanged at `tests/test_cycle_semantics_package_model_async_alias.py:235-242`.
- DIRECT_EVIDENCE: The tests inspect `sys.modules` and package namespace identity inside an isolated interpreter; neither model events nor MODEL_PASS enter these assertions (`tests/test_cycle_semantics_function_identity_cpython.py:72-105,161-169`).

## FULL_DIFFS

Complete actual new-file diff (`/dev/null` → `tests/test_cycle_semantics_function_identity_cpython.py`):

```diff
--- /dev/null
+++ b/tests/test_cycle_semantics_function_identity_cpython.py
@@ -0,0 +1,169 @@
+import json
+import subprocess
+import sys
+import tempfile
+from pathlib import Path
+
+import pytest
+
+
+OLD = """\
+def f():
+    import pkg.old
+"""
+
+NEW = """\
+def f():
+    import pkg.new
+"""
+
+
+CASES = [
+    pytest.param(
+        OLD + "\nf()\n",
+        None,
+        {"ok": True, "old": True, "new": False},
+        id="direct-call",
+    ),
+    pytest.param(
+        OLD + "\ng = f\ng()\n",
+        None,
+        {"ok": True, "old": True, "new": False,
+         "alias_is_current": True},
+        id="alias-call",
+    ),
+    pytest.param(
+        OLD + "\ng = f\nf = None\ng()\n",
+        None,
+        {"ok": True, "old": True, "new": False,
+         "alias_is_current": False},
+        id="alias-survives-rebinding",
+    ),
+    pytest.param(
+        OLD + "\ng = f\n" + NEW + "\ng()\n",
+        None,
+        {"ok": True, "old": True, "new": False,
+         "alias_is_current": False},
+        id="old-alias-survives-redefinition",
+    ),
+    pytest.param(
+        OLD + "\ng = f\n" + NEW + "\nf()\n",
+        None,
+        {"ok": True, "old": False, "new": True,
+         "alias_is_current": False},
+        id="new-definition-call",
+    ),
+    pytest.param(
+        OLD + "\ng = f\ng = None\ng()\n",
+        None,
+        {"ok": False, "old": False, "new": False,
+         "error": "TypeError"},
+        id="noncallable-rebinding",
+    ),
+    pytest.param(
+        OLD,
+        "from pkg import f\nf()\n",
+        {"ok": True, "old": True, "new": False},
+        id="foreign-function-cpython-control",
+    ),
+]
+
+
+RUNNER = """\
+import importlib
+import json
+import sys
+
+sys.path.insert(0, sys.argv[1])
+
+ok = True
+error = None
+
+try:
+    importlib.import_module(sys.argv[2])
+except Exception as exc:
+    ok = False
+    error = type(exc).__name__
+
+pkg = sys.modules.get("pkg")
+
+alias_is_current = None
+
+if pkg is not None:
+    namespace = vars(pkg)
+    if "g" in namespace and "f" in namespace:
+        alias_is_current = namespace["g"] is namespace["f"]
+
+print(json.dumps({
+    "ok": ok,
+    "error": error,
+    "old": "pkg.old" in sys.modules,
+    "new": "pkg.new" in sys.modules,
+    "alias_is_current": alias_is_current,
+}))
+"""
+
+
+@pytest.mark.parametrize(
+    "package_source,consumer_source,expected",
+    CASES,
+)
+def test_restricted_function_identity_cpython(
+    package_source,
+    consumer_source,
+    expected,
+):
+    with tempfile.TemporaryDirectory() as directory:
+        root = Path(directory)
+        package = root / "pkg"
+        package.mkdir()
+
+        (package / "__init__.py").write_text(
+            package_source,
+            encoding="utf-8",
+        )
+        (package / "old.py").write_text(
+            "pass\n",
+            encoding="utf-8",
+        )
+        (package / "new.py").write_text(
+            "pass\n",
+            encoding="utf-8",
+        )
+
+        entry = "pkg"
+
+        if consumer_source is not None:
+            (root / "consumer.py").write_text(
+                consumer_source,
+                encoding="utf-8",
+            )
+            entry = "consumer"
+
+        process = subprocess.run(
+            [
+                sys.executable,
+                "-I",
+                "-B",
+                "-c",
+                RUNNER,
+                str(root),
+                entry,
+            ],
+            text=True,
+            capture_output=True,
+            timeout=20,
+            check=False,
+        )
+
+        assert process.returncode == 0, process.stderr
+
+        observed = json.loads(process.stdout)
+
+        for key, value in expected.items():
+            assert observed[key] == value, (
+                key,
+                expected,
+                observed,
+                process.stderr,
+            )
```

## FINAL_VERDICT

- CONTRACT_PROVED: The requested CPython-only baseline was added exactly and all seven isolated scenarios passed. This stage does not certify Contextor model parity, runtime adoption, or cycle-semantic freshness. Stop after this baseline.

# CONTEXTOR P1D3-WARN-5O — CPython namespace cycle parity

## PREFLIGHT

DIRECT_EVIDENCE: HEAD `7a2c0830d49dfe359fc88f9588e07828b1aae6cc`. Target test file absent before edit. Pre-existing changes to `tests/test_cycle_semantics_namespace_source_binding.py` and `walkthrough.md` preserved. Contextor MCP `get_module_context` for package_model first: revision 908, workspace_sync verified, graph/cycles fresh, cycle_semantics stale, structural_count 16.

## INTERPRETER_DISCOVERY

The exact architect-authored 410-line test module was added without production changes. Its `_interpreter` probes each candidate with isolated CPython `sys.version_info` and `sys.implementation.name`. `py -0p` is unavailable because the Windows launcher is not installed/accessible; `Get-Command` found no additional matching executable or CONTEXTOR_PYTHON_3_* override.

## EXACT_PYTHON_VERSIONS_AND_EXECUTABLES

CPython 3.10.9: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, verified. CPython 3.11, 3.12, 3.13, 3.14 and 3.15: no interpreter verified by the exact test's discovery contract.

## COVERED_VERSIONS

3.10: all 15 namespace entry scenarios plus the pre-3.15 lazy syntax negative passed.

## NOT_COVERED_VERSIONS

3.11–3.14: 16 skipped cases each. 3.15: 17 skipped cases. All marked NOT_COVERED, not PASS.

## VERSION_MATRIX_RESULTS

Command: `& .\.venv\Scripts\python.exe -m py_compile tests/test_cycle_semantics_namespace_cycle_parity.py` — PASS.
Command: `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_namespace_cycle_parity.py` — 18 passed, 81 skipped, 1 failed. The only failure is the required `COVERAGE_INCOMPLETE` gate listing 3.11, 3.12, 3.13, 3.14, 3.15. The module collected 100 cases as specified. No available interpreter produced a contradictory semantic result; CONTRACT_CONFLICT=NONE.

## PYTHON_315_LAZY_IMPORT_CONTRACT

UNKNOWN / NOT_COVERED: 3.15 unavailable. The lazy and eager 3.15 tests were skipped. No 3.15 parity claim.

## REGULAR_MODEL_UNKNOWN_PARITY

Both unchanged restricted regular-package model UNKNOWN cases passed on the current test Python. This is model contract parity only, not runtime safety.

## TARGETED_REGRESSIONS

`& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_namespace_pep420_contract.py tests/test_cycle_semantics_namespace_path_model.py tests/test_cycle_semantics_namespace_source_binding.py` — 35 passed. Pre-existing namespace_source_binding.py test modification remained untouched. `git diff --check` passed for tracked changes; the new-file diff below has no whitespace errors.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: `get_module_context` for the new test module returned `not_found` in active module registry; registration/workspace_sync for it are UNKNOWN. No manual update_file. Bounded `get_live_events(after_revision=908,limit=1)`: status ok, revision/latest_revision 908, activity_epoch `d08a5a93184d473f8bc124596f4a44c9`, resync_required false, no new canonical events. Cycle warning view: structural_count 16, model_pass_count 0, active_warning_count 16. Earlier module context: graph/cycles fresh, cycle_semantics stale. No loaded-code adoption claimed.

## FILES_CHANGED

`tests/test_cycle_semantics_namespace_cycle_parity.py` (new). `walkthrough.md` overwritten as required report; its self-diff excluded. Existing prior test modification is not part of this task.

## FULL_DIFFS

Complete actual diff of the new test file:

```diff
diff --git a/tests/test_cycle_semantics_namespace_cycle_parity.py b/tests/test_cycle_semantics_namespace_cycle_parity.py
new file mode 100644
index 0000000..f3416a6
--- /dev/null
+++ b/tests/test_cycle_semantics_namespace_cycle_parity.py
@@ -0,0 +1,410 @@
+"""Cross-version CPython namespace-cycle execution contracts.
+
+Python 3.10–3.15 are independent execution targets.
+Missing interpreters are NOT_COVERED, never PASS.
+No LIVE runtime safety or warning suppression is certified.
+"""
+
+from __future__ import annotations
+
+import ast
+import functools
+import json
+import os
+from pathlib import Path
+import shutil
+import subprocess
+import sys
+
+import pytest
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+
+VERSIONS = (10, 11, 12, 13, 14, 15)
+
+_SAFE_NESTED = {
+    "ctxpkg/__init__.py": "pass\n",
+    "ctxpkg/ns/a.py": "value=1\nimport ctxpkg.ns.b\n",
+    "ctxpkg/ns/b.py": "from ctxpkg.ns.a import value\nx=value\n",
+}
+
+_HAZARD_NESTED = {
+    "ctxpkg/__init__.py": "pass\n",
+    "ctxpkg/ns/a.py": "import ctxpkg.ns.b\nvalue=1\n",
+    "ctxpkg/ns/b.py": "from ctxpkg.ns.a import value\nx=value\n",
+}
+
+_SAFE_TOP = {
+    "ctxns/a.py": "value=1\nimport ctxns.b\n",
+    "ctxns/b.py": "from ctxns.a import value\nx=value\n",
+}
+
+_HAZARD_ATTRIBUTE = {
+    "ctxns/a.py": "import ctxns.b\nvalue=1\n",
+    "ctxns/b.py": "import ctxns.a\nx=ctxns.a.value\n",
+}
+
+_CLASS_EAGER = {
+    "ctxns/a.py": (
+        "class C:\n"
+        "    import ctxns.b\n"
+        "value=1\n"
+    ),
+    "ctxns/b.py": "from ctxns.a import value\nx=value\n",
+}
+
+_FUNCTION_DEFERRED = {
+    "ctxns/a.py": (
+        "def load():\n"
+        "    import ctxns.b\n"
+        "value=1\n"
+    ),
+    "ctxns/b.py": "import ctxns.a\nx=ctxns.a.value\n",
+}
+
+_TWO_PORTIONS = (
+    {"ctxns/a.py": "value=1\nimport ctxns.b\n"},
+    {"ctxns/b.py": "from ctxns.a import value\nx=value\n"},
+)
+
+_SHADOWED = (
+    _SAFE_TOP,
+    {"ctxns/__init__.py": "value=99\n"},
+)
+
+CASES = (
+    ("nested_safe_a", (_SAFE_NESTED,), "ctxpkg.ns.a", None),
+    ("nested_safe_b", (_SAFE_NESTED,), "ctxpkg.ns.b", None),
+    ("nested_hazard_a", (_HAZARD_NESTED,), "ctxpkg.ns.a", "ImportError"),
+    ("nested_hazard_b", (_HAZARD_NESTED,), "ctxpkg.ns.b", None),
+    ("top_safe_a", (_SAFE_TOP,), "ctxns.a", None),
+    ("top_safe_b", (_SAFE_TOP,), "ctxns.b", None),
+    ("two_portions_a", _TWO_PORTIONS, "ctxns.a", None),
+    ("two_portions_b", _TWO_PORTIONS, "ctxns.b", None),
+    (
+        "parent_attribute_hazard_a",
+        (_HAZARD_ATTRIBUTE,),
+        "ctxns.a",
+        "AttributeError",
+    ),
+    (
+        "parent_attribute_hazard_b",
+        (_HAZARD_ATTRIBUTE,),
+        "ctxns.b",
+        None,
+    ),
+    ("class_eager_a", (_CLASS_EAGER,), "ctxns.a", "ImportError"),
+    ("class_eager_b", (_CLASS_EAGER,), "ctxns.b", None),
+    ("function_deferred_a", (_FUNCTION_DEFERRED,), "ctxns.a", None),
+    ("function_deferred_b", (_FUNCTION_DEFERRED,), "ctxns.b", None),
+    (
+        "regular_package_shadows_namespace",
+        _SHADOWED,
+        "ctxns.a",
+        "ModuleNotFoundError",
+    ),
+)
+
+
+@functools.lru_cache(maxsize=None)
+def _interpreter(minor):
+    """Locate and verify an actual CPython interpreter version."""
+    candidates = []
+
+    override = os.environ.get(
+        "CONTEXTOR_PYTHON_3_" + str(minor)
+    )
+    if override:
+        candidates.append((override,))
+
+    if sys.version_info[:2] == (3, minor):
+        candidates.append((sys.executable,))
+
+    direct = shutil.which("python3." + str(minor))
+    if direct:
+        candidates.append((direct,))
+
+    launcher = shutil.which("py")
+    if launcher:
+        candidates.append((launcher, "-3." + str(minor)))
+
+    for command in candidates:
+        try:
+            result = subprocess.run(
+                command + (
+                    "-I",
+                    "-B",
+                    "-c",
+                    (
+                        "import sys\n"
+                        "print('%s.%s' % sys.version_info[:2])\n"
+                        "print(sys.implementation.name)\n"
+                    ),
+                ),
+                capture_output=True,
+                text=True,
+                timeout=5,
+                check=False,
+            )
+        except (OSError, subprocess.TimeoutExpired):
+            continue
+
+        lines = result.stdout.strip().splitlines()
+
+        if (
+            result.returncode == 0
+            and lines == ["3." + str(minor), "cpython"]
+        ):
+            return command
+
+    return None
+
+
+def _require(minor):
+    interpreter = _interpreter(minor)
+    if interpreter is None:
+        pytest.skip(
+            "NOT_COVERED: CPython 3." + str(minor)
+            + " interpreter unavailable"
+        )
+    return interpreter
+
+
+def _execute(
+    tmp_path,
+    interpreter,
+    portions,
+    entry,
+    *,
+    suffix="",
+    script_extra="",
+    minor=None,
+):
+    paths = []
+
+    for number, files in enumerate(portions):
+        root = tmp_path / ("portion_" + str(number) + suffix)
+        paths.append(str(root))
+
+        for relative, body in files.items():
+            target = root / relative
+            target.parent.mkdir(parents=True, exist_ok=True)
+            target.write_text(body, encoding="utf-8")
+
+    script = (
+        "import importlib, json, sys\n"
+        "sys.path[:0] = json.loads(sys.argv[1])\n"
+        "module = importlib.import_module(sys.argv[2])\n"
+        + script_extra
+    )
+
+    flags = ("-I", "-B")
+    if minor == 15:
+        flags += ("-X", "lazy_imports=normal")
+
+    return subprocess.run(
+        interpreter
+        + flags
+        + (
+            "-c",
+            script,
+            json.dumps(paths),
+            entry,
+        ),
+        capture_output=True,
+        text=True,
+        timeout=10,
+        check=False,
+    )
+
+
+@pytest.mark.parametrize("minor", VERSIONS)
+@pytest.mark.parametrize(
+    "scenario,portions,entry,error",
+    CASES,
+    ids=[case[0] for case in CASES],
+)
+def test_namespace_cycle_entry_matrix(
+    tmp_path,
+    minor,
+    scenario,
+    portions,
+    entry,
+    error,
+):
+    interpreter = _require(minor)
+
+    result = _execute(
+        tmp_path,
+        interpreter,
+        portions,
+        entry,
+        minor=minor,
+    )
+
+    if error is None:
+        assert result.returncode == 0, (
+            minor,
+            scenario,
+            result.stderr,
+        )
+    else:
+        assert result.returncode != 0, (
+            minor,
+            scenario,
+        )
+        assert result.stderr.strip().splitlines()[-1].startswith(
+            error + ":"
+        ), (
+            minor,
+            scenario,
+            result.stderr,
+        )
+
+
+@pytest.mark.parametrize(
+    "sources,entry",
+    (
+        (
+            {
+                "ctxns.a": _SAFE_TOP["ctxns/a.py"],
+                "ctxns.b": _SAFE_TOP["ctxns/b.py"],
+            },
+            "ctxns.a",
+        ),
+        (
+            {
+                "ctxpkg.__init__": "pass",
+                "ctxpkg.ns.a": _HAZARD_NESTED[
+                    "ctxpkg/ns/a.py"
+                ],
+                "ctxpkg.ns.b": _HAZARD_NESTED[
+                    "ctxpkg/ns/b.py"
+                ],
+            },
+            "ctxpkg.ns.a",
+        ),
+    ),
+)
+def test_restricted_regular_model_remains_unknown(
+    sources,
+    entry,
+):
+    assessment = evaluate_package_import_order(
+        {
+            name: ast.parse(body)
+            for name, body in sources.items()
+        },
+        entry,
+    )
+
+    assert assessment.outcome == "UNKNOWN"
+    assert assessment.events == ()
+
+
+@pytest.mark.parametrize("minor", VERSIONS[:-1])
+def test_lazy_import_syntax_before_315(tmp_path, minor):
+    interpreter = _require(minor)
+
+    portions = (
+        {
+            "ctxns/a.py": (
+                "lazy import ctxns.b\n"
+                "value=1\n"
+            ),
+            "ctxns/b.py": "pass\n",
+        },
+    )
+
+    result = _execute(
+        tmp_path,
+        interpreter,
+        portions,
+        "ctxns.a",
+        minor=minor,
+    )
+
+    assert result.returncode != 0
+    assert result.stderr.strip().splitlines()[-1].startswith(
+        "SyntaxError:"
+    ), result.stderr
+
+
+def test_315_lazy_import_defers_cycle(tmp_path):
+    interpreter = _require(15)
+
+    portions = (
+        {
+            "ctxns/a.py": (
+                "lazy import ctxns.b\n"
+                "value=1\n"
+            ),
+            "ctxns/b.py": (
+                "from ctxns.a import value\n"
+                "x=value\n"
+            ),
+        },
+    )
+
+    result = _execute(
+        tmp_path,
+        interpreter,
+        portions,
+        "ctxns.a",
+        minor=15,
+        script_extra=(
+            "assert 'ctxns.b' not in sys.modules\n"
+            "assert module.ctxns.b.x == 1\n"
+            "assert 'ctxns.b' in sys.modules\n"
+        ),
+    )
+
+    assert result.returncode == 0, result.stderr
+
+
+def test_315_eager_import_still_has_hazard(tmp_path):
+    interpreter = _require(15)
+
+    portions = (
+        {
+            "ctxns/a.py": (
+                "import ctxns.b\n"
+                "value=1\n"
+            ),
+            "ctxns/b.py": (
+                "from ctxns.a import value\n"
+                "x=value\n"
+            ),
+        },
+    )
+
+    result = _execute(
+        tmp_path,
+        interpreter,
+        portions,
+        "ctxns.a",
+        minor=15,
+    )
+
+    assert result.returncode != 0
+    assert result.stderr.strip().splitlines()[-1].startswith(
+        "ImportError:"
+    ), result.stderr
+
+
+def test_required_interpreter_coverage_gate():
+    missing = [
+        "3." + str(minor)
+        for minor in VERSIONS
+        if _interpreter(minor) is None
+    ]
+
+    if missing:
+        pytest.fail(
+            "COVERAGE_INCOMPLETE: missing CPython interpreters: "
+            + ", ".join(missing)
+            + "; skipped cases are NOT_COVERED, not PASS"
+        )
```

## REMAINING_UNKNOWN

Python 3.11–3.15 execution results; 3.15 lazy import behavior; new-file canonical registry/workspace synchronization; active loaded-code adoption. No runtime import safety or warning suppression is certified.

## FINAL_VERDICT

PARTIAL_COVERAGE. Exact implementation and available 3.10 tests passed; required complete cross-version coverage gate failed because five interpreters are absent. STOP after WARN-5O.
